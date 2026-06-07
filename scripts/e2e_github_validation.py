#!/usr/bin/env python3
"""Manual end-to-end validation against a real GitHub repository.

Runs the full InterPipeD agent pipeline (PM → Worker → Tester → Architect →
PullRequest) and verifies the branch, commit, and pull request exist on GitHub.

This script performs real git and GitHub API operations. Do not use in CI.

Required environment variables:
  GITHUB_APP_ID
  GITHUB_PRIVATE_KEY  (or GITHUB_PRIVATE_KEY_PATH)
  GITHUB_INSTALLATION_ID
  GITHUB_REPOSITORY   (owner/repo target repository)

Optional:
  GITHUB_BASE_BRANCH              (default: main)
  INTERPIPED_E2E_TIMEOUT_SECONDS  (default: 180)

Usage:
  export GITHUB_APP_ID=...
  export GITHUB_PRIVATE_KEY="$(cat path/to/app.pem)"
  export GITHUB_INSTALLATION_ID=...
  export GITHUB_REPOSITORY=owner/repo
  python scripts/e2e_github_validation.py
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from interpiped.agents.architect import ArchitectAgent
from interpiped.agents.pm import PMAgent
from interpiped.agents.pull_request import PullRequestAgent
from interpiped.agents.tester import TesterAgent
from interpiped.agents.worker import WorkerAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas
from interpiped.github.github_app import GitHubService, GitHubServiceError


@dataclass
class ValidationResult:
    task_id: str
    branch_name: str
    commit_sha: str
    pr_url: str
    pr_number: int


def _load_private_key() -> str:
    key_path = os.environ.get("GITHUB_PRIVATE_KEY_PATH")
    if key_path:
        return Path(key_path).read_text(encoding="utf-8")
    key = os.environ.get("GITHUB_PRIVATE_KEY", "")
    if not key:
        raise SystemExit("GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH is required")
    return key.replace("\\n", "\n")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def _build_github_service() -> GitHubService:
    return GitHubService(
        app_id=int(_require_env("GITHUB_APP_ID")),
        private_key=_load_private_key(),
        installation_id=int(_require_env("GITHUB_INSTALLATION_ID")),
    )


def verify_on_github(
    github: GitHubService,
    repository: str,
    branch_name: str,
    commit_sha: str,
    pr_number: int,
) -> None:
    """Confirm branch, commit, and pull request exist via the GitHub API."""
    client = github._get_github_client()
    repo = client.get_repo(repository)

    branch = repo.get_branch(branch_name)
    if branch.commit.sha != commit_sha:
        raise RuntimeError(
            f"branch {branch_name} tip is {branch.commit.sha}, expected {commit_sha}"
        )

    commit = repo.get_commit(commit_sha)
    if commit.sha != commit_sha:
        raise RuntimeError(f"commit {commit_sha} not found")

    pr = repo.get_pull(pr_number)
    if pr.head.ref != branch_name:
        raise RuntimeError(
            f"pull request #{pr_number} head is {pr.head.ref}, expected {branch_name}"
        )
    if pr.html_url is None:
        raise RuntimeError(f"pull request #{pr_number} has no html_url")


async def run_pipeline(
    github: GitHubService,
    repository: str,
    base_branch: str,
    timeout_seconds: float,
) -> ValidationResult:
    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    issue_title = f"interpiped-e2e-{run_id}"
    issue_description = (
        "Automated InterPipeD end-to-end validation run. "
        f"Run ID: {run_id}. Safe to close after review."
    )

    token = github.get_installation_token()
    os.environ["INTERPIPED_GITHUB_TOKEN"] = token

    bus = InMemoryEventBus()
    await bus.start()

    pm = PMAgent("pm-e2e", bus)
    worker = WorkerAgent("worker-e2e", bus)
    tester = TesterAgent("tester-e2e", bus)
    architect = ArchitectAgent("architect-e2e", bus)
    pr_agent = PullRequestAgent("pr-e2e", bus, github, base_branch=base_branch)

    await pm.start()
    await worker.start()
    await tester.start()
    await architect.start()
    await pr_agent.start()

    commits: dict[str, str] = {}
    failures: list[str] = []
    first_pr = asyncio.Event()
    first_pr_event: schemas.PullRequestCreated | None = None

    async def on_task_completed(event: schemas.TaskCompleted) -> None:
        if getattr(event, "event_type", None) == "TaskCompleted":
            commits[event.task_id] = event.commit_sha

    async def on_pr_created(event: schemas.PullRequestCreated) -> None:
        nonlocal first_pr_event
        if getattr(event, "event_type", None) == "PullRequestCreated" and first_pr_event is None:
            first_pr_event = event
            first_pr.set()

    async def on_task_failed(event: schemas.TaskFailed) -> None:
        if getattr(event, "event_type", None) == "TaskFailed":
            failures.append(f"TaskFailed[{event.task_id}]: {event.reason}")

    async def on_pr_failed(event: schemas.PullRequestFailed) -> None:
        if getattr(event, "event_type", None) == "PullRequestFailed":
            failures.append(f"PullRequestFailed[{event.task_id}]: {event.reason}")

    await bus.subscribe("TaskCompleted", on_task_completed)
    await bus.subscribe("PullRequestCreated", on_pr_created)
    await bus.subscribe("TaskFailed", on_task_failed)
    await bus.subscribe("PullRequestFailed", on_pr_failed)

    issue = schemas.IssueCreated(
        issue_number=int(run_id[-6:]),
        repository=repository,
        title=issue_title,
        description=issue_description,
        source="e2e-github-validation",
    )
    print(f"Issue context: title={issue_title!r} repository={repository}")
    await bus.publish(issue)

    try:
        await asyncio.wait_for(first_pr.wait(), timeout=timeout_seconds)
    except TimeoutError as exc:
        raise RuntimeError(
            f"timed out after {timeout_seconds}s waiting for PullRequestCreated; "
            f"failures={failures or 'none'}"
        ) from exc

    if first_pr_event is None:
        raise RuntimeError(f"no PullRequestCreated event; failures={failures!r}")

    commit_sha = commits.get(first_pr_event.task_id)
    if not commit_sha:
        raise RuntimeError(f"no TaskCompleted commit for task {first_pr_event.task_id!r}")

    result = ValidationResult(
        task_id=first_pr_event.task_id,
        branch_name=first_pr_event.head,
        commit_sha=commit_sha,
        pr_url=first_pr_event.pr_url,
        pr_number=first_pr_event.pr_number,
    )

    verify_on_github(
        github,
        repository=repository,
        branch_name=result.branch_name,
        commit_sha=result.commit_sha,
        pr_number=result.pr_number,
    )

    await pm.stop()
    await worker.stop()
    await tester.stop()
    await architect.stop()
    await pr_agent.stop()
    await bus.stop()

    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="Target repository as owner/repo (default: GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--base-branch",
        default=os.environ.get("GITHUB_BASE_BRANCH", "main"),
        help="Base branch for pull requests (default: main)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("INTERPIPED_E2E_TIMEOUT_SECONDS", "180")),
        help="Seconds to wait for pipeline completion (default: 180)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.repository:
        print("GITHUB_REPOSITORY or --repository is required", file=sys.stderr)
        return 1

    if "/" not in args.repository:
        print("repository must be owner/repo", file=sys.stderr)
        return 1

    try:
        github = _build_github_service()
        result = asyncio.run(
            run_pipeline(
                github=github,
                repository=args.repository,
                base_branch=args.base_branch,
                timeout_seconds=args.timeout,
            )
        )
    except (GitHubServiceError, RuntimeError, SystemExit) as exc:
        print(f"E2E validation failed: {exc}", file=sys.stderr)
        return 1

    print("InterPipeD E2E validation: SUCCESS")
    print(f"branch: {result.branch_name}")
    print(f"commit: {result.commit_sha}")
    print(f"pull request url: {result.pr_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

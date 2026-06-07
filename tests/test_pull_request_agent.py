import asyncio
from types import SimpleNamespace

import pytest

from interpiped.agents.pull_request import PullRequestAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas
from interpiped.github.github_app import GitHubServiceError


class FakeGitHub:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.raise_error = False

    def create_pull_request(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_error:
            raise GitHubServiceError("failed to create pull request: boom")
        return SimpleNamespace(
            number=42,
            html_url="https://github.com/org/repo/pull/42",
        )


@pytest.mark.asyncio
async def test_pull_request_created_on_approval() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    fake_github = FakeGitHub()
    agent = PullRequestAgent("pr-agent", bus, fake_github)  # type: ignore[arg-type]
    await agent.start()

    created = asyncio.Event()
    captured: list[schemas.PullRequestCreated] = []

    async def on_created(e: schemas.PullRequestCreated) -> None:
        if getattr(e, "event_type", None) == "PullRequestCreated":
            captured.append(e)
            created.set()

    await bus.subscribe("PullRequestCreated", on_created)

    task = schemas.TaskCreated(
        task_id="auth-models",
        issue_number=1,
        repository="org/repo",
        branch_name="task/auth-models",
        title="Add auth models",
        description="Implement user models",
        source="pm",
    )
    await bus.publish(task)
    await bus.publish(
        schemas.ArchitectureApproved(task_id="auth-models", reviewer="architect", source="architect")
    )

    await asyncio.wait_for(created.wait(), timeout=1.0)

    assert len(fake_github.calls) == 1
    call = fake_github.calls[0]
    assert call["repository_full_name"] == "org/repo"
    assert call["head"] == "task/auth-models"
    assert call["base"] == "main"
    assert call["title"] == "Add auth models"
    assert call["body"] == "Implement user models"

    assert len(captured) == 1
    pr_event = captured[0]
    assert pr_event.task_id == "auth-models"
    assert pr_event.pr_number == 42
    assert pr_event.pr_url == "https://github.com/org/repo/pull/42"

    await agent.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_pull_request_failed_on_github_error() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    fake_github = FakeGitHub()
    fake_github.raise_error = True
    agent = PullRequestAgent("pr-agent", bus, fake_github)  # type: ignore[arg-type]
    await agent.start()

    failed = asyncio.Event()

    async def on_failed(e: schemas.PullRequestFailed) -> None:
        if getattr(e, "event_type", None) == "PullRequestFailed":
            failed.set()

    await bus.subscribe("PullRequestFailed", on_failed)

    await bus.publish(
        schemas.TaskCreated(
            task_id="t1",
            issue_number=1,
            repository="org/repo",
            branch_name="task/t1",
            title="Task",
            description="desc",
            source="pm",
        )
    )
    await bus.publish(schemas.ArchitectureApproved(task_id="t1", reviewer="architect", source="architect"))

    await asyncio.wait_for(failed.wait(), timeout=1.0)

    await agent.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_pull_request_failed_without_task_context() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    fake_github = FakeGitHub()
    agent = PullRequestAgent("pr-agent", bus, fake_github)  # type: ignore[arg-type]
    await agent.start()

    failed = asyncio.Event()

    async def on_failed(e: schemas.PullRequestFailed) -> None:
        if getattr(e, "event_type", None) == "PullRequestFailed":
            failed.set()

    await bus.subscribe("PullRequestFailed", on_failed)

    await bus.publish(schemas.ArchitectureApproved(task_id="unknown", reviewer="architect", source="architect"))

    await asyncio.wait_for(failed.wait(), timeout=1.0)
    assert len(fake_github.calls) == 0

    await agent.stop()
    await bus.stop()

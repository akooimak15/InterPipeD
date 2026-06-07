from __future__ import annotations

import asyncio
import logging

from interpiped.agents.base import BaseAgent
from interpiped.events import schemas
from interpiped.github.github_app import GitHubService, GitHubServiceError

log = logging.getLogger(__name__)


class PullRequestAgent(BaseAgent):
    """Opens a GitHub pull request when architecture review approves a task."""

    def __init__(
        self,
        name: str,
        bus,
        github: GitHubService,
        base_branch: str = "main",
    ) -> None:
        super().__init__(name, bus)
        self.github = github
        self.base_branch = base_branch
        self._started = False
        self._task_context: dict[str, schemas.TaskCreated] = {}

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.subscribe("TaskCreated", self._cache_task_context)
        await self.bus.subscribe("ArchitectureApproved", self.handle_event)
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def _cache_task_context(self, event: schemas.TaskCreated) -> None:
        if getattr(event, "event_type", None) != "TaskCreated":
            return
        task_id = getattr(event, "task_id", None)
        if task_id:
            self._task_context[task_id] = event

    async def handle_event(self, event: schemas.ArchitectureApproved) -> None:
        if getattr(event, "event_type", None) != "ArchitectureApproved":
            return

        task_id = getattr(event, "task_id", None)
        if not task_id:
            await self._publish_failed("", "missing task_id")
            return

        ctx = self._task_context.get(task_id)
        if ctx is None:
            await self._publish_failed(task_id, "task context not found")
            return

        await asyncio.sleep(0)

        try:
            pr = self.github.create_pull_request(
                repository_full_name=ctx.repository,
                head=ctx.branch_name,
                base=self.base_branch,
                title=ctx.title,
                body=ctx.description,
            )
            created = schemas.PullRequestCreated(
                task_id=task_id,
                repository=ctx.repository,
                pr_number=pr.number,
                pr_url=pr.html_url,
                head=ctx.branch_name,
                base=self.base_branch,
                source=self.name,
            )
            await self.bus.publish(created)
        except GitHubServiceError as exc:
            log.exception("pull request creation failed for task %s", task_id)
            await self._publish_failed(task_id, str(exc))
        except Exception as exc:
            log.exception("unexpected error creating PR for task %s", task_id)
            await self._publish_failed(task_id, str(exc))
        finally:
            await asyncio.sleep(0)

    async def _publish_failed(self, task_id: str, reason: str) -> None:
        failed = schemas.PullRequestFailed(
            task_id=task_id,
            reason=reason,
            source=self.name,
        )
        await self.bus.publish(failed)

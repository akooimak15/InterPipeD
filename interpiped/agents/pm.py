from __future__ import annotations

import asyncio
from typing import List

from interpiped.agents.base import BaseAgent
from interpiped.events import schemas


def _slugify(title: str) -> str:
    # simple deterministic slug: lowercase, keep alnum and dash
    import re

    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "task"


def decompose_issue_to_tasks(title: str) -> List[str]:
    """Deterministic decomposition of an issue title into task slugs.

    Default strategy: create -models, -service, -api variants from slug.
    """
    base = _slugify(title)
    return [f"{base}-models", f"{base}-service", f"{base}-api"]


class PMAgent(BaseAgent):
    """Project Manager agent: converts IssueCreated into TaskCreated events."""

    def __init__(self, name: str, bus) -> None:
        super().__init__(name, bus)
        self._started = False
        # track created tasks and retry counts
        self._task_map: dict[str, schemas.TaskCreated] = {}
        self._retry_counts: dict[str, int] = {}

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.subscribe("IssueCreated", self.handle_event)
        await self.bus.subscribe("TaskFailed", self.handle_task_failed)
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def handle_event(self, event: schemas.IssueCreated) -> None:
        if getattr(event, "event_type", None) != "IssueCreated":
            return

        tasks = decompose_issue_to_tasks(event.title)
        for t in tasks:
            task_event = schemas.TaskCreated(
                task_id=t,
                issue_number=event.issue_number,
                repository=event.repository,
                branch_name=f"task/{t}",
                title=event.title,
                description=event.description,
                priority="normal",
                source=self.name,
            )
            # store task context for potential retries
            self._task_map[t] = task_event
            # small delay to allow concurrent handlers to attach in tests
            await asyncio.sleep(0)
            await self.bus.publish(task_event)

    async def handle_task_failed(self, event: schemas.TaskFailed) -> None:
        if getattr(event, "event_type", None) != "TaskFailed":
            return

        task_id = event.task_id
        # increment retry count
        cnt = self._retry_counts.get(task_id, 0) + 1
        self._retry_counts[task_id] = cnt

        if cnt < 3:
            # publish RetryRequested with context from stored TaskCreated if available
            task_ctx = self._task_map.get(task_id)
            retry = schemas.RetryRequested(
                task_id=task_id,
                retry_count=cnt,
                reason=event.reason,
                repository=getattr(task_ctx, "repository", None) if task_ctx else None,
                branch_name=getattr(task_ctx, "branch_name", None) if task_ctx else None,
                title=getattr(task_ctx, "title", None) if task_ctx else None,
                description=getattr(task_ctx, "description", None) if task_ctx else None,
                source=self.name,
            )
            await asyncio.sleep(0)
            await self.bus.publish(retry)
        else:
            perm = schemas.PermanentFailure(
                task_id=task_id,
                reason=event.reason,
                source=self.name,
            )
            await asyncio.sleep(0)
            await self.bus.publish(perm)

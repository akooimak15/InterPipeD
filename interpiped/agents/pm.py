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

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.subscribe("IssueCreated", self.handle_event)
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
            # small delay to allow concurrent handlers to attach in tests
            await asyncio.sleep(0)
            await self.bus.publish(task_event)

from __future__ import annotations

import asyncio
from typing import Any

from interpiped.agents.base import BaseAgent
from interpiped.events import schemas


class WorkerAgent(BaseAgent):
    """Example worker agent that listens for TaskCreated and emits TaskCompleted."""

    def __init__(self, name: str, bus):
        super().__init__(name, bus)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.subscribe("TaskCreated", self.handle_event)
        self._started = True

    async def stop(self) -> None:
        # InMemoryEventBus does not currently support unsubscribe; noop for now
        self._started = False

    async def handle_event(self, event: Event) -> None:
        # Simple example: when a TaskCreated arrives, produce a TaskCompleted
        if getattr(event, "event_type", None) != "TaskCreated":
            return

        # Simulate some async work
        await asyncio.sleep(0)

        task_id = getattr(event, "task_id", "unknown-task")
        commit_sha = "deadbeef"  # placeholder for scaffold
        files_modified = ["README.md"]

        completed = schemas.TaskCompleted(
            task_id=task_id,
            commit_sha=commit_sha,
            files_modified=files_modified,
            source=self.name,
            event_type="TaskCompleted",
            repository=getattr(event, "repository", ""),
            issue_number=getattr(event, "issue_number", None),
            title=getattr(event, "title", ""),
            description=getattr(event, "description", ""),
            branch_name=getattr(event, "branch_name", ""),
        )

        await self.bus.publish(completed)

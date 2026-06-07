from __future__ import annotations

import asyncio
from typing import List

from interpiped.agents.base import BaseAgent
from interpiped.events import schemas


class TesterAgent(BaseAgent):
    """TesterAgent validates TaskCompleted events and emits TestPassed/TestFailed.

    Deterministic rules (v0.1):
    - PASS if commit_sha is not empty and files_modified length > 0
    - FAIL otherwise, with named failure reasons
    """

    def __init__(self, name: str, bus) -> None:
        super().__init__(name, bus)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.subscribe("TaskCompleted", self.handle_event)
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def handle_event(self, event: schemas.TaskCompleted) -> None:
        # ensure correct event type
        if getattr(event, "event_type", None) != "TaskCompleted":
            return

        # evaluate rules
        failures: List[str] = []
        if not getattr(event, "commit_sha", ""):
            failures.append("missing_commit")
        if not getattr(event, "files_modified", None):
            failures.append("no_files_modified")

        # simulate validation duration
        await asyncio.sleep(0)

        if failures:
            failed = schemas.TestFailed(
                task_id=getattr(event, "task_id", ""),
                failed_tests=failures,
                duration_ms=10,
                source=self.name,
            )
            await self.bus.publish(failed)
        else:
            passed = schemas.TestPassed(
                task_id=getattr(event, "task_id", ""),
                test_count=1,
                duration_ms=10,
                source=self.name,
            )
            await self.bus.publish(passed)

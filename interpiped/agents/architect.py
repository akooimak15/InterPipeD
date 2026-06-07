from __future__ import annotations

import asyncio
from typing import Optional

from interpiped.agents.base import BaseAgent
from interpiped.events import schemas


class ArchitectAgent(BaseAgent):
    """ArchitectAgent reviews TestPassed events and emits approval or rejection.

    Rules (v0.1):
    - APPROVE if task_id non-empty and test_count > 0
    - REJECT otherwise, with reason 'invalid_test_results'
    """

    def __init__(self, name: str, bus) -> None:
        super().__init__(name, bus)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await self.bus.subscribe("TestPassed", self.handle_event)
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def handle_event(self, event: schemas.TestPassed) -> None:
        if getattr(event, "event_type", None) != "TestPassed":
            return

        task_id: Optional[str] = getattr(event, "task_id", None)
        test_count: int = getattr(event, "test_count", 0)

        await asyncio.sleep(0)

        if task_id and test_count > 0:
            approved = schemas.ArchitectureApproved(
                task_id=task_id,
                reviewer=self.name,
                source=self.name,
            )
            await self.bus.publish(approved)
        else:
            rejected = schemas.ArchitectureRejected(
                task_id=task_id or "",
                reviewer=self.name,
                reason="invalid_test_results",
                source=self.name,
            )
            await self.bus.publish(rejected)

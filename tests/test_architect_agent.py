import asyncio

import pytest

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.agents.architect import ArchitectAgent
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_architect_approve_and_reject() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    architect = ArchitectAgent("arch-test", bus)
    await architect.start()

    approved = asyncio.Event()
    rejected = asyncio.Event()

    async def on_approved(e: schemas.ArchitectureApproved) -> None:
        if getattr(e, "event_type", None) == "ArchitectureApproved":
            approved.set()

    async def on_rejected(e: schemas.ArchitectureRejected) -> None:
        if getattr(e, "event_type", None) == "ArchitectureRejected":
            rejected.set()

    await bus.subscribe("ArchitectureApproved", on_approved)
    await bus.subscribe("ArchitectureRejected", on_rejected)

    # approve
    await bus.publish(schemas.TestPassed(task_id="t1", test_count=3, duration_ms=10, source="tester"))
    await asyncio.wait_for(approved.wait(), timeout=1.0)

    # reject
    await bus.publish(schemas.TestPassed(task_id="", test_count=0, duration_ms=10, source="tester"))
    await asyncio.wait_for(rejected.wait(), timeout=1.0)

    await architect.stop()
    await bus.stop()

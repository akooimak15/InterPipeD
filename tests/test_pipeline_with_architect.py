import asyncio

import pytest

from interpiped.agents.pm import PMAgent
from interpiped.agents.worker import WorkerAgent
from interpiped.agents.tester import TesterAgent
from interpiped.agents.architect import ArchitectAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_pipeline_includes_architect() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    pm = PMAgent("pm-1", bus)
    worker = WorkerAgent("worker-1", bus)
    tester = TesterAgent("tester-1", bus)
    architect = ArchitectAgent("architect-1", bus)

    await pm.start()
    await worker.start()
    await tester.start()
    await architect.start()

    seen = asyncio.Event()

    async def on_approved(e: schemas.ArchitectureApproved) -> None:
        if getattr(e, "event_type", None) == "ArchitectureApproved":
            seen.set()

    await bus.subscribe("ArchitectureApproved", on_approved)

    issue = schemas.IssueCreated(issue_number=202, repository="repo", title="Create auth", description="desc", source="user")
    await bus.publish(issue)

    await asyncio.wait_for(seen.wait(), timeout=2.0)

    await pm.stop()
    await worker.stop()
    await tester.stop()
    await architect.stop()
    await bus.stop()

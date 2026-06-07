import asyncio

import pytest

from interpiped.agents.pm import PMAgent
from interpiped.agents.worker import WorkerAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_full_pipeline_issue_to_task_to_completed() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    pm = PMAgent("pm-1", bus)
    worker = WorkerAgent("worker-1", bus)

    await pm.start()
    await worker.start()

    seen = asyncio.Event()

    async def on_completed(e: schemas.TaskCompleted) -> None:
        if getattr(e, "event_type", None) == "TaskCompleted":
            seen.set()

    await bus.subscribe("TaskCompleted", on_completed)

    issue = schemas.IssueCreated(issue_number=1, repository="repo", title="Create authentication system", description="desc", source="user")
    await bus.publish(issue)

    await asyncio.wait_for(seen.wait(), timeout=2.0)

    await pm.stop()
    await worker.stop()
    await bus.stop()

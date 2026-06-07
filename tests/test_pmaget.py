import asyncio

import pytest

from interpiped.agents.pm import PMAgent, decompose_issue_to_tasks
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas


def test_decompose_issue_to_tasks_basic() -> None:
    tasks = decompose_issue_to_tasks("Create authentication system")
    assert tasks == ["create-authentication-system-models", "create-authentication-system-service", "create-authentication-system-api"]


@pytest.mark.asyncio
async def test_pmaget_emits_taskcreated_events() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    pm = PMAgent("pm-1", bus)
    await pm.start()

    seen = []
    ev = asyncio.Event()

    async def on_task(e: schemas.TaskCreated) -> None:
        seen.append(e.task_id)
        if len(seen) >= 3:
            ev.set()

    await bus.subscribe("TaskCreated", on_task)

    issue = schemas.IssueCreated(issue_number=42, repository="repo", title="Create auth", description="desc", source="user")
    await bus.publish(issue)

    await asyncio.wait_for(ev.wait(), timeout=1.0)

    assert len(seen) == 3

    await pm.stop()
    await bus.stop()

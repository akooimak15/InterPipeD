import asyncio

import pytest

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.agents.pm import PMAgent
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_pmaget_retries_and_permanent_failure() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    pm = PMAgent("pm-test", bus)
    await pm.start()

    # create initial TaskCreated so PMAgent stores context
    task = schemas.TaskCreated(
        task_id="t1",
        issue_number=1,
        repository="repo",
        branch_name="task/t1",
        title="T1",
        description="d",
        source="pm",
    )
    await bus.publish(task)

    seen_retry = asyncio.Event()
    seen_perm = asyncio.Event()

    async def on_retry(e: schemas.RetryRequested) -> None:
        seen_retry.set()

    async def on_perm(e: schemas.PermanentFailure) -> None:
        seen_perm.set()

    await bus.subscribe("RetryRequested", on_retry)
    await bus.subscribe("PermanentFailure", on_perm)

    # first failure -> retry requested
    await bus.publish(schemas.TaskFailed(task_id="t1", reason="r", error_type="E", source="worker"))
    await asyncio.wait_for(seen_retry.wait(), timeout=1.0)

    # second failure -> retry requested
    seen_retry.clear()
    await bus.publish(schemas.TaskFailed(task_id="t1", reason="r2", error_type="E", source="worker"))
    await asyncio.wait_for(seen_retry.wait(), timeout=1.0)

    # third failure -> permanent
    await bus.publish(schemas.TaskFailed(task_id="t1", reason="r3", error_type="E", source="worker"))
    await asyncio.wait_for(seen_perm.wait(), timeout=1.0)

    await pm.stop()
    await bus.stop()

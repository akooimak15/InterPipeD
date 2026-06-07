import asyncio

import pytest

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.agents.tester import TesterAgent
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_tester_pass_and_fail() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    tester = TesterAgent("tester-test", bus)
    await tester.start()

    passed = asyncio.Event()
    failed = asyncio.Event()

    async def on_pass(e: schemas.TestPassed) -> None:
        if getattr(e, "event_type", None) == "TestPassed":
            passed.set()

    async def on_fail(e: schemas.TestFailed) -> None:
        if getattr(e, "event_type", None) == "TestFailed":
            failed.set()

    await bus.subscribe("TestPassed", on_pass)
    await bus.subscribe("TestFailed", on_fail)

    # PASS case
    await bus.publish(schemas.TaskCompleted(task_id="t1", commit_sha="abc", files_modified=["a.py"], source="worker"))
    await asyncio.wait_for(passed.wait(), timeout=1.0)

    # FAIL case
    await bus.publish(schemas.TaskCompleted(task_id="t2", commit_sha="", files_modified=[], source="worker"))
    await asyncio.wait_for(failed.wait(), timeout=1.0)

    await tester.stop()
    await bus.stop()

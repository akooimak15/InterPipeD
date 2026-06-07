import asyncio

import pytest

from interpiped.agents.worker import WorkerAgent
from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events.models import Event


@pytest.mark.asyncio
async def test_worker_reacts_and_publishes() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    worker = WorkerAgent("worker-test", bus)
    await worker.start()

    seen = asyncio.Event()

    async def on_completed(e: Event) -> None:
        if e.event_type == "TaskCompleted":
            assert e.source == "worker-test"
            seen.set()

    await bus.subscribe("TaskCompleted", on_completed)

    await bus.publish(Event(event_type="TaskCreated", source="pm-1"))

    await asyncio.wait_for(seen.wait(), timeout=1.0)

    await worker.stop()
    await bus.stop()

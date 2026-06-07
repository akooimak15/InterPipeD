import asyncio

import pytest

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events import schemas


@pytest.mark.asyncio
async def test_inmemory_event_bus_dispatches_handlers() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    seen = asyncio.Event()

    async def handler(e: schemas.BaseEvent) -> None:
        assert getattr(e, "event_type") == "TestEvent"
        seen.set()

    await bus.subscribe("TestEvent", handler)

    await bus.publish(schemas.BaseEvent(event_type="TestEvent", source="test"))

    # wait for handler to be invoked
    await asyncio.wait_for(seen.wait(), timeout=1.0)

    await bus.stop()

"""Lightweight smoke test runner for environments without pytest/pip.

This script runs basic checks for InMemoryEventBus and WorkerAgent
without external test frameworks.
"""
import asyncio
import sys

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events.models import Event
from interpiped.agents.worker import WorkerAgent


async def test_event_bus() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    seen = asyncio.Event()

    async def handler(e: Event) -> None:
        assert e.event_type == "SmokeEvent"
        seen.set()

    await bus.subscribe("SmokeEvent", handler)
    await bus.publish(Event(event_type="SmokeEvent", source="smoke"))
    await asyncio.wait_for(seen.wait(), timeout=1.0)
    await bus.stop()


async def test_worker_agent() -> None:
    bus = InMemoryEventBus()
    await bus.start()

    worker = WorkerAgent("worker-smoke", bus)
    await worker.start()

    seen = asyncio.Event()

    async def on_completed(e: Event) -> None:
        if e.event_type == "TaskCompleted":
            assert e.source == "worker-smoke"
            seen.set()

    await bus.subscribe("TaskCompleted", on_completed)
    await bus.publish(Event(event_type="TaskCreated", source="pm-smoke"))

    await asyncio.wait_for(seen.wait(), timeout=1.0)

    await worker.stop()
    await bus.stop()


async def main() -> int:
    try:
        await test_event_bus()
        print("[ok] event_bus")
        await test_worker_agent()
        print("[ok] worker_agent")
    except Exception as e:
        print("[FAIL]", e)
        return 2
    return 0


if __name__ == "__main__":
    res = asyncio.run(main())
    sys.exit(res)

from __future__ import annotations

import logging

from fastapi import FastAPI

from interpiped.core.event_bus import InMemoryEventBus
from interpiped.events.models import Event
from interpiped.agents.worker import WorkerAgent

log = logging.getLogger(__name__)

app = FastAPI(title="InterPipeD API")

# Instantiate an in-memory bus and a sample worker for the demo scaffold
bus = InMemoryEventBus()
worker = WorkerAgent("worker-1", bus)


@app.on_event("startup")
async def startup() -> None:
    await bus.start()
    try:
        await worker.start()
    except Exception:
        log.exception("worker start failed")


@app.on_event("shutdown")
async def shutdown() -> None:
    try:
        await worker.stop()
    except Exception:
        log.exception("worker stop failed")
    await bus.stop()


@app.post("/events")
async def post_event(event: Event) -> dict:
    """Publish an event into the system."""
    await bus.publish(event)
    return {"status": "accepted", "event_id": str(event.event_id)}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

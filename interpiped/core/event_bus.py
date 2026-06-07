from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Any

Handler = Callable[[Any], Awaitable[None]]

log = logging.getLogger(__name__)


class EventBus:
    """EventBus interface."""

    async def publish(self, event: Event) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def subscribe(self, event_type: str, handler: Handler) -> None:  # pragma: no cover
        raise NotImplementedError

    async def start(self) -> None:  # pragma: no cover
        raise NotImplementedError

    async def stop(self) -> None:  # pragma: no cover
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    """A simple in-memory event bus suitable for testing and small deployments.

    - Handlers are called in their own tasks.
    - A background dispatcher serializes event dequeuing.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._handlers: Dict[str, List[Handler]] = {}
        self._task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run())
        log.info("InMemoryEventBus started")

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            await self._queue.put(None)  # type: ignore[arg-type]
            await self._task
        log.info("InMemoryEventBus stopped")

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    async def subscribe(self, event_type: str, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def _run(self) -> None:
        while not self._stopping:
            event = await self._queue.get()
            # sentinel to stop
            if event is None:  # type: ignore[comparison-overlap]
                break

            handlers = self._handlers.get(event.event_type, [])
            if not handlers:
                continue

            for h in handlers:
                # dispatch each handler concurrently
                asyncio.create_task(self._safe_invoke(h, event))

    async def _safe_invoke(self, handler: Handler, event: Event) -> None:
        try:
            await handler(event)
        except Exception:
            log.exception("Error in event handler for %s", event.event_type)

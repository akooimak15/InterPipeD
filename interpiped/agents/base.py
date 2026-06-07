from __future__ import annotations

import abc

from interpiped.core.event_bus import EventBus
from interpiped.events.models import Event


class BaseAgent(abc.ABC):
    """Abstract base class for agents.

    Agents should be small, testable components that subscribe to events
    and optionally publish new events.
    """

    def __init__(self, name: str, bus: EventBus):
        self.name = name
        self.bus = bus
        self._running = False

    @abc.abstractmethod
    async def start(self) -> None:
        """Prepare agent, subscribe to event bus."""

    @abc.abstractmethod
    async def stop(self) -> None:
        """Cleanup and stop agent."""

    @abc.abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Handle a single event delivered by the EventBus."""

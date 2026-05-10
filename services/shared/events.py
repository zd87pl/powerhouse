"""
Event Bus — async pub/sub coordination between agents.

All services communicate through typed events. No direct coupling.
An agent publishes an event; any number of agents subscribe.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Event:
    """A typed event flowing through the bus."""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"  # agent or service that emitted this
    priority: EventPriority = EventPriority.NORMAL
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str | None = None  # for tracing chains of events

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "source": self.source,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            event_type=d["event_type"],
            payload=d.get("payload", {}),
            source=d.get("source", "unknown"),
            priority=EventPriority(d.get("priority", "normal")),
            timestamp=d.get("timestamp", ""),
            correlation_id=d.get("correlation_id"),
        )


# Type alias for subscriber callbacks
Subscriber = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    In-process async event bus.

    Usage:
        bus = EventBus()

        @bus.on("deploy.complete")
        async def on_deploy(event: Event):
            await notify_slack(event.payload["url"])

        await bus.emit(Event(event_type="deploy.complete", payload={"url": "..."}))
    """

    def __init__(self):
        self._subscribers: dict[str, list[Subscriber]] = {}
        self._history: list[Event] = []  # keep last N for replay/debug
        self._max_history = 1000

    def on(self, event_type: str):
        """Decorator: subscribe to an event type."""

        def decorator(fn: Subscriber) -> Subscriber:
            self.subscribe(event_type, fn)
            return fn

        return decorator

    def subscribe(self, event_type: str, fn: Subscriber) -> None:
        """Register a subscriber for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(fn)
        logger.debug("Subscribed %s → %s", fn.__name__, event_type)

    def unsubscribe(self, event_type: str, fn: Subscriber) -> None:
        """Remove a subscriber."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                s for s in self._subscribers[event_type] if s != fn
            ]

    async def emit(self, event: Event) -> None:
        """Publish an event to all subscribers. Non-blocking per subscriber."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        subscribers = self._subscribers.get(event.event_type, [])
        if not subscribers:
            logger.debug("No subscribers for event: %s", event.event_type)
            return

        # Fire all subscribers concurrently, collect results
        tasks = [fn(event) for fn in subscribers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for fn, result in zip(subscribers, results):
            if isinstance(result, Exception):
                logger.error(
                    "Subscriber %s failed for event %s: %s",
                    fn.__name__,
                    event.event_type,
                    result,
                )

    async def emit_nowait(self, event: Event) -> None:
        """Fire-and-forget: emit without waiting for subscribers."""
        asyncio.create_task(self.emit(event))

    def get_history(
        self, event_type: str | None = None, limit: int = 50
    ) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    @property
    def subscriber_count(self) -> int:
        return sum(len(subs) for subs in self._subscribers.values())

    def clear(self) -> None:
        """Reset all subscriptions and history."""
        self._subscribers.clear()
        self._history.clear()


# Global singleton
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus

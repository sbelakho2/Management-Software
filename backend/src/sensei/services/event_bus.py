"""
Domain Event Bus (#383, #430).

A lightweight, in-process event bus for decoupling domain services.
Handlers are registered by event type and invoked synchronously (sync)
or asynchronously (async) when events are published.

Usage:
    from sensei.services.event_bus import event_bus, DomainEvent

    @dataclass
    class OrderPlaced(DomainEvent):
        order_id: str

    # Register handler
    event_bus.subscribe(OrderPlaced, handle_order_placed)

    # Publish event
    await event_bus.publish(OrderPlaced(order_id="123"))
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Type, TypeVar
from uuid import uuid4

logger = logging.getLogger(__name__)

E = TypeVar("E", bound="DomainEvent")

Handler = Callable[[Any], Coroutine[Any, Any, None]] | Callable[[Any], None]


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str | None = None


class EventBus:
    """In-process domain event bus.

    Supports both sync and async handlers. Handlers are invoked in
    registration order. Errors in one handler do not prevent others
    from executing.
    """

    def __init__(self) -> None:
        self._handlers: dict[Type[DomainEvent], list[Handler]] = defaultdict(list)
        self._global_handlers: list[Handler] = []
        self._published_count: int = 0

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def subscribe(self, event_type: Type[E], handler: Handler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type.__name__)

    def subscribe_all(self, handler: Handler) -> None:
        """Register a handler that receives ALL events."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: Type[E], handler: Handler) -> None:
        """Remove a handler."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers."""
        event_type = type(event)
        handlers = list(self._handlers.get(event_type, [])) + list(self._global_handlers)

        if not handlers:
            logger.debug("No handlers for %s", event_type.__name__)
            return

        self._published_count += 1
        logger.debug(
            "Publishing %s (id=%s) to %d handler(s)",
            event_type.__name__,
            event.event_id,
            len(handlers),
        )

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "Handler %s failed for event %s (id=%s)",
                    handler.__name__,
                    event_type.__name__,
                    event.event_id,
                )

    def publish_sync(self, event: DomainEvent) -> None:
        """Publish an event synchronously (only invokes sync handlers)."""
        event_type = type(event)
        handlers = list(self._handlers.get(event_type, [])) + list(self._global_handlers)

        self._published_count += 1
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    logger.warning(
                        "Async handler %s skipped in sync publish for %s",
                        handler.__name__,
                        event_type.__name__,
                    )
            except Exception:
                logger.exception(
                    "Handler %s failed for event %s (id=%s)",
                    handler.__name__,
                    event_type.__name__,
                    event.event_id,
                )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict[str, Any]:
        """Return bus statistics."""
        return {
            "registered_event_types": len(self._handlers),
            "total_handlers": sum(len(h) for h in self._handlers.values()) + len(self._global_handlers),
            "published_count": self._published_count,
        }

    def clear(self) -> None:
        """Remove all handlers (useful for testing)."""
        self._handlers.clear()
        self._global_handlers.clear()
        self._published_count = 0


# Module-level singleton
event_bus = EventBus()

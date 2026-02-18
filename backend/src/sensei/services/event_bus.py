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
from uuid import UUID
from uuid import uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)

E = TypeVar("E", bound="DomainEvent")

Handler = Callable[[Any], Coroutine[Any, Any, None]] | Callable[[Any], None]


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str | None = None


class EventBus(PersistentServiceMixin):
    """In-process domain event bus.

    Supports both sync and async handlers. Handlers are invoked in
    registration order. Errors in one handler do not prevent others
    from executing.
    """

    SERVICE_NAME = "event_bus"

    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

    def __init__(self) -> None:
        self._handlers: dict[Type[DomainEvent], list[Handler]] = defaultdict(list)
        self._global_handlers: list[Handler] = []
        self._published_count: int = 0
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        stats = await self.load_state(self._DEFAULT_TENANT_ID, "stats")
        if stats and "published_count" in stats:
            self._published_count = int(stats["published_count"])
        self._state_loaded = True

    async def persist_all(self) -> None:
        await self.save_state(
            self._DEFAULT_TENANT_ID,
            "stats",
            {"published_count": self._published_count},
        )

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    def _maybe_persist_sync(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.persist_all())

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
        await self._ensure_loaded()
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

        await self.persist_all()

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

        self._maybe_persist_sync()

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

    async def get_stats_async(self) -> dict[str, Any]:
        await self._ensure_loaded()
        return self.stats

    def clear(self) -> None:
        """Remove all handlers (useful for testing)."""
        self._handlers.clear()
        self._global_handlers.clear()
        self._published_count = 0
        self._state_loaded = True


# Module-level singleton
event_bus = EventBus()


def get_event_bus() -> EventBus:
    return event_bus

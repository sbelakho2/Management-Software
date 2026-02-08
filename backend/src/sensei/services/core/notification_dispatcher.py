"""
Notification Dispatcher.

Routes generated notifications to the appropriate delivery channels:
- IN_APP → persists to in-memory store + optional WebSocket broadcast
- EMAIL → sends via EmailService
- PUSH / SMS → logged as undeliverable (future channels)

This module bridges the gap between notification_triggers (which generates
notifications) and the actual delivery mechanisms.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


@dataclass
class DeliveryResult:
    """Result of a single notification delivery attempt."""

    notification_id: str
    channel: str
    success: bool
    error: str | None = None
    delivered_at: datetime | None = None


@dataclass
class DispatchSummary:
    """Summary of a dispatch batch."""

    total: int = 0
    delivered: int = 0
    failed: int = 0
    by_channel: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    results: list[DeliveryResult] = field(default_factory=list)


class NotificationDispatcher(PersistentServiceMixin):
    """Routes notifications to delivery channels.

    Usage::

        from sensei.services.core.notification_triggers import (
            NotificationTriggersJobRunner,
        )

        dispatcher = NotificationDispatcher(email_service=email_svc)
        runner = NotificationTriggersJobRunner(
            on_notification=dispatcher.dispatch,
        )
    """

    SERVICE_NAME = "notification_dispatcher"

    def __init__(
        self,
        *,
        email_service: Any | None = None,
        websocket_broadcast: Callable[[dict[str, Any]], None] | None = None,
        max_in_app_buffer: int = 10_000,
    ) -> None:
        self._email_service = email_service
        self._ws_broadcast = websocket_broadcast
        self._max_in_app_buffer = max_in_app_buffer

        # In-app notification store (keyed by recipient_id)
        self._in_app: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._delivery_log: list[DeliveryResult] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dispatch(self, notification: Any) -> list[DeliveryResult]:
        """Dispatch a single notification to all its channels.

        *notification* should be a ``GeneratedNotification`` (or any object
        with the same attributes).
        """
        results: list[DeliveryResult] = []

        channels: list[str] = [
            ch.value if hasattr(ch, "value") else str(ch)
            for ch in getattr(notification, "channels", ["in_app"])
        ]

        for channel in channels:
            result = self._deliver_to_channel(notification, channel)
            results.append(result)
            self._delivery_log.append(result)

        return results

    def dispatch_batch(
        self, notifications: list[Any]
    ) -> DispatchSummary:
        """Dispatch a list of notifications and return a summary."""
        summary = DispatchSummary()
        for n in notifications:
            results = self.dispatch(n)
            summary.total += 1
            for r in results:
                summary.by_channel[r.channel] += 1
                if r.success:
                    summary.delivered += 1
                else:
                    summary.failed += 1
                summary.results.append(r)
        return summary

    # ------------------------------------------------------------------
    # In-app notification store
    # ------------------------------------------------------------------

    def get_in_app_notifications(
        self,
        recipient_id: str,
        *,
        limit: int = 50,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve in-app notifications for a user."""
        items = self._in_app.get(recipient_id, [])
        if unread_only:
            items = [i for i in items if not i.get("read")]
        return items[:limit]

    def mark_read(self, recipient_id: str, notification_id: str) -> bool:
        """Mark an in-app notification as read."""
        for item in self._in_app.get(recipient_id, []):
            if item["id"] == notification_id:
                item["read"] = True
                item["read_at"] = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def get_unread_count(self, recipient_id: str) -> int:
        """Return unread count for a recipient."""
        return sum(
            1
            for n in self._in_app.get(recipient_id, [])
            if not n.get("read")
        )

    def get_delivery_log(self, *, limit: int = 100) -> list[DeliveryResult]:
        """Return recent delivery log entries."""
        return self._delivery_log[-limit:]

    # ------------------------------------------------------------------
    # Channel handlers
    # ------------------------------------------------------------------

    def _deliver_to_channel(
        self, notification: Any, channel: str
    ) -> DeliveryResult:
        handler = {
            "in_app": self._deliver_in_app,
            "email": self._deliver_email,
            "push": self._deliver_push,
            "sms": self._deliver_sms,
        }.get(channel, self._deliver_unknown)

        try:
            handler(notification)
            return DeliveryResult(
                notification_id=notification.id,
                channel=channel,
                success=True,
                delivered_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.exception(
                "Failed to deliver notification %s via %s",
                notification.id,
                channel,
            )
            return DeliveryResult(
                notification_id=notification.id,
                channel=channel,
                success=False,
                error=str(exc),
            )

    def _deliver_in_app(self, notification: Any) -> None:
        """Persist in-app notification and broadcast via WebSocket."""
        recipient_id = str(notification.recipient_id) if notification.recipient_id else "__global__"
        payload = {
            "id": notification.id,
            "type": notification.trigger_type.value
            if hasattr(notification.trigger_type, "value")
            else str(notification.trigger_type),
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority.value
            if hasattr(notification.priority, "value")
            else str(notification.priority),
            "entity_type": notification.entity_type,
            "entity_id": notification.entity_id,
            "action_url": notification.action_url,
            "generated_at": notification.generated_at.isoformat()
            if notification.generated_at
            else None,
            "read": False,
        }

        # Store
        bucket = self._in_app[recipient_id]
        bucket.insert(0, payload)
        if len(bucket) > self._max_in_app_buffer:
            self._in_app[recipient_id] = bucket[: self._max_in_app_buffer]

        # Broadcast
        if self._ws_broadcast:
            try:
                self._ws_broadcast(
                    {
                        "event": "notification",
                        "recipient_id": recipient_id,
                        "payload": payload,
                    }
                )
            except Exception:
                logger.warning(
                    "WebSocket broadcast failed for notification %s",
                    notification.id,
                )

        logger.debug("In-app notification stored for %s", recipient_id)

    def _deliver_email(self, notification: Any) -> None:
        """Send notification via email."""
        if self._email_service is None:
            logger.warning(
                "Email service not configured; skipping email delivery "
                "for notification %s",
                notification.id,
            )
            return

        recipient_email = getattr(notification, "extra_data", {}).get("email")
        if not recipient_email:
            logger.info(
                "No email address for notification %s; skipping email",
                notification.id,
            )
            return

        self._email_service.send_notification_email(
            to_email=recipient_email,
            subject=notification.title,
            message=notification.message,
            action_url=notification.action_url,
        )
        logger.info(
            "Email sent for notification %s to %s",
            notification.id,
            recipient_email,
        )

    def _deliver_push(self, notification: Any) -> None:
        """Push notification (stub — future implementation)."""
        logger.info(
            "Push delivery not implemented; notification %s logged only",
            notification.id,
        )

    def _deliver_sms(self, notification: Any) -> None:
        """SMS notification (stub — future implementation)."""
        logger.info(
            "SMS delivery not implemented; notification %s logged only",
            notification.id,
        )

    def _deliver_unknown(self, notification: Any) -> None:
        """Unknown channel handler."""
        logger.warning(
            "Unknown channel for notification %s", notification.id
        )

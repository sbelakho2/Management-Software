"""
Email delivery tracking, bounce handling, and sent-log.

Provides a complete email lifecycle tracker with:
- Sent log with per-message status tracking
- Bounce classification (hard/soft/complaint)
- Delivery rate metrics
- Webhook processing for SES/SendGrid/Mailgun bounce notifications
- Retry policy for soft bounces
- Suppression list management

Checklist items: #379, #471, #473
"""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """Email delivery status."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"
    SUPPRESSED = "suppressed"


class BounceType(str, Enum):
    """Bounce classification."""

    HARD = "hard"  # permanent failure (invalid address)
    SOFT = "soft"  # temporary failure (mailbox full)
    COMPLAINT = "complaint"  # user reported as spam
    UNDETERMINED = "undetermined"


@dataclass
class DeliveryRecord:
    """Individual email delivery record."""

    id: str = field(default_factory=lambda: uuid4().hex[:16])
    recipient: str = ""
    subject: str = ""
    template: str = ""
    status: DeliveryStatus = DeliveryStatus.QUEUED
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    opened_at: datetime | None = None
    bounced_at: datetime | None = None
    bounce_type: BounceType | None = None
    bounce_reason: str = ""
    attempts: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class DeliveryMetrics:
    """Aggregate delivery metrics."""

    total_sent: int = 0
    total_delivered: int = 0
    total_bounced: int = 0
    total_complained: int = 0
    total_opened: int = 0
    delivery_rate: float = 0.0
    bounce_rate: float = 0.0
    open_rate: float = 0.0
    hard_bounces: int = 0
    soft_bounces: int = 0


class EmailRateLimiter:
    """Token-bucket rate limiter for email sends.

    Prevents exceeding provider limits (e.g. SES 14/sec).
    """

    def __init__(
        self,
        max_per_second: float = 10.0,
        max_per_hour: int = 1000,
        max_per_day: int = 10000,
    ) -> None:
        self.max_per_second = max_per_second
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day

        self._tokens = max_per_second
        self._last_refill = time.monotonic()
        self._hourly_count = 0
        self._daily_count = 0
        self._hour_start = datetime.now(timezone.utc)
        self._day_start = datetime.now(timezone.utc)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.max_per_second,
            self._tokens + elapsed * self.max_per_second,
        )
        self._last_refill = now

        utc_now = datetime.now(timezone.utc)
        if (utc_now - self._hour_start).total_seconds() >= 3600:
            self._hourly_count = 0
            self._hour_start = utc_now
        if (utc_now - self._day_start).total_seconds() >= 86400:
            self._daily_count = 0
            self._day_start = utc_now

    def acquire(self) -> bool:
        """Try to acquire a send permit. Returns False if rate-limited."""
        self._refill()
        if self._tokens < 1:
            return False
        if self._hourly_count >= self.max_per_hour:
            return False
        if self._daily_count >= self.max_per_day:
            return False
        self._tokens -= 1
        self._hourly_count += 1
        self._daily_count += 1
        return True

    def remaining_capacity(self) -> dict[str, int]:
        self._refill()
        return {
            "per_second": max(0, int(self._tokens)),
            "per_hour": max(0, self.max_per_hour - self._hourly_count),
            "per_day": max(0, self.max_per_day - self._daily_count),
        }


class EmailDeliveryTracker:
    """Tracks email delivery lifecycle events.

    Usage::

        tracker = EmailDeliveryTracker()

        # Before sending
        record = tracker.track_send("user@example.com", "Welcome", template="welcome")
        if tracker.rate_limiter.acquire():
            success = await email_service.send_email(msg)
            tracker.mark_sent(record.id) if success else tracker.mark_failed(record.id)

        # On bounce webhook
        tracker.process_bounce(record.id, BounceType.HARD, "Mailbox not found")

        # Metrics
        metrics = tracker.get_metrics(hours=24)
    """

    def __init__(
        self,
        suppression_threshold: int = 3,
        rate_limiter: EmailRateLimiter | None = None,
    ) -> None:
        self._records: dict[str, DeliveryRecord] = {}
        self._suppression_list: dict[str, dict[str, Any]] = {}
        self._bounce_callbacks: list[Callable] = []
        self.suppression_threshold = suppression_threshold
        self.rate_limiter = rate_limiter or EmailRateLimiter()

    # ------------------------------------------------------------------
    # Tracking lifecycle
    # ------------------------------------------------------------------

    def track_send(
        self,
        recipient: str,
        subject: str,
        *,
        template: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryRecord:
        """Create a delivery record for a new email send."""
        if self.is_suppressed(recipient):
            record = DeliveryRecord(
                recipient=recipient,
                subject=subject,
                template=template,
                status=DeliveryStatus.SUPPRESSED,
                metadata=metadata or {},
            )
            self._records[record.id] = record
            logger.info("Email to %s suppressed", recipient)
            return record

        record = DeliveryRecord(
            recipient=recipient,
            subject=subject,
            template=template,
            metadata=metadata or {},
        )
        self._records[record.id] = record
        return record

    def mark_sent(self, record_id: str) -> None:
        record = self._records.get(record_id)
        if record:
            record.status = DeliveryStatus.SENT
            record.sent_at = datetime.now(timezone.utc)
            record.attempts += 1

    def mark_delivered(self, record_id: str) -> None:
        record = self._records.get(record_id)
        if record:
            record.status = DeliveryStatus.DELIVERED
            record.delivered_at = datetime.now(timezone.utc)

    def mark_opened(self, record_id: str) -> None:
        record = self._records.get(record_id)
        if record:
            record.status = DeliveryStatus.OPENED
            record.opened_at = datetime.now(timezone.utc)

    def mark_failed(self, record_id: str, reason: str = "") -> None:
        record = self._records.get(record_id)
        if record:
            record.status = DeliveryStatus.FAILED
            record.bounce_reason = reason

    # ------------------------------------------------------------------
    # Bounce handling
    # ------------------------------------------------------------------

    def process_bounce(
        self,
        record_id: str,
        bounce_type: BounceType,
        reason: str = "",
    ) -> None:
        """Process a bounce notification."""
        record = self._records.get(record_id)
        if not record:
            logger.warning("Bounce for unknown record %s", record_id)
            return

        record.status = DeliveryStatus.BOUNCED
        record.bounced_at = datetime.now(timezone.utc)
        record.bounce_type = bounce_type
        record.bounce_reason = reason

        # Update suppression list
        if bounce_type == BounceType.HARD:
            self._add_to_suppression(record.recipient, reason)
        elif bounce_type == BounceType.SOFT:
            self._track_soft_bounce(record.recipient)

        for cb in self._bounce_callbacks:
            try:
                cb(record)
            except Exception:
                logger.exception("Bounce callback error")

        logger.info(
            "Bounce: %s type=%s recipient=%s reason=%s",
            record_id,
            bounce_type.value,
            record.recipient,
            reason,
        )

    def process_complaint(self, record_id: str) -> None:
        """Process a spam complaint."""
        record = self._records.get(record_id)
        if not record:
            return
        record.status = DeliveryStatus.COMPLAINED
        self._add_to_suppression(
            record.recipient, "spam_complaint"
        )

    def process_webhook(
        self, provider: str, payload: dict[str, Any]
    ) -> None:
        """Process a webhook from an email provider.

        Supports SES, SendGrid, and Mailgun payload formats.
        """
        if provider == "ses":
            self._process_ses_webhook(payload)
        elif provider == "sendgrid":
            self._process_sendgrid_webhook(payload)
        elif provider == "mailgun":
            self._process_mailgun_webhook(payload)
        else:
            logger.warning("Unknown email provider: %s", provider)

    def _process_ses_webhook(self, payload: dict[str, Any]) -> None:
        msg_type = payload.get("notificationType", "")
        record_id = payload.get("mail", {}).get(
            "messageId", ""
        )
        if msg_type == "Bounce":
            bounce_info = payload.get("bounce", {})
            bt = (
                BounceType.HARD
                if bounce_info.get("bounceType") == "Permanent"
                else BounceType.SOFT
            )
            self.process_bounce(
                record_id,
                bt,
                bounce_info.get("bounceSubType", ""),
            )
        elif msg_type == "Complaint":
            self.process_complaint(record_id)
        elif msg_type == "Delivery":
            self.mark_delivered(record_id)

    def _process_sendgrid_webhook(
        self, payload: dict[str, Any]
    ) -> None:
        events = payload if isinstance(payload, list) else [payload]
        for event in events:
            record_id = event.get("sg_message_id", "")
            event_type = event.get("event", "")
            if event_type == "bounce":
                bt = (
                    BounceType.HARD
                    if event.get("type") == "bounce"
                    else BounceType.SOFT
                )
                self.process_bounce(
                    record_id, bt, event.get("reason", "")
                )
            elif event_type == "delivered":
                self.mark_delivered(record_id)
            elif event_type == "open":
                self.mark_opened(record_id)
            elif event_type == "spamreport":
                self.process_complaint(record_id)

    def _process_mailgun_webhook(
        self, payload: dict[str, Any]
    ) -> None:
        event_data = payload.get("event-data", payload)
        event_type = event_data.get("event", "")
        record_id = event_data.get("message", {}).get(
            "headers", {}
        ).get("message-id", "")

        if event_type == "failed":
            severity = event_data.get("severity", "")
            bt = (
                BounceType.HARD
                if severity == "permanent"
                else BounceType.SOFT
            )
            self.process_bounce(
                record_id,
                bt,
                event_data.get("delivery-status", {}).get(
                    "description", ""
                ),
            )
        elif event_type == "delivered":
            self.mark_delivered(record_id)
        elif event_type == "opened":
            self.mark_opened(record_id)
        elif event_type == "complained":
            self.process_complaint(record_id)

    # ------------------------------------------------------------------
    # Suppression list
    # ------------------------------------------------------------------

    def _add_to_suppression(
        self, email: str, reason: str
    ) -> None:
        self._suppression_list[email.lower()] = {
            "reason": reason,
            "added_at": datetime.now(timezone.utc).isoformat(),
            "bounce_count": self._suppression_list.get(
                email.lower(), {}
            ).get("bounce_count", 0)
            + 1,
        }
        logger.info("Added %s to suppression list: %s", email, reason)

    def _track_soft_bounce(self, email: str) -> None:
        key = email.lower()
        existing = self._suppression_list.get(key, {})
        count = existing.get("bounce_count", 0) + 1
        if count >= self.suppression_threshold:
            self._add_to_suppression(
                email, f"soft_bounce_threshold_{count}"
            )
        else:
            self._suppression_list[key] = {
                "reason": "soft_bounce",
                "bounce_count": count,
                "last_bounce": datetime.now(timezone.utc).isoformat(),
            }

    def is_suppressed(self, email: str) -> bool:
        entry = self._suppression_list.get(email.lower())
        if not entry:
            return False
        count = entry.get("bounce_count", 0)
        reason = entry.get("reason", "")
        return (
            reason in ("spam_complaint",)
            or "hard" in reason
            or count >= self.suppression_threshold
            or reason.startswith("soft_bounce_threshold")
        )

    def remove_from_suppression(self, email: str) -> bool:
        return self._suppression_list.pop(email.lower(), None) is not None

    def get_suppression_list(self) -> dict[str, dict[str, Any]]:
        return dict(self._suppression_list)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_bounce(self, callback: Callable) -> None:
        self._bounce_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Metrics & queries
    # ------------------------------------------------------------------

    def get_record(self, record_id: str) -> DeliveryRecord | None:
        return self._records.get(record_id)

    def get_records_for_recipient(
        self, email: str
    ) -> list[DeliveryRecord]:
        return [
            r
            for r in self._records.values()
            if r.recipient.lower() == email.lower()
        ]

    def get_metrics(self, hours: int = 24) -> DeliveryMetrics:
        """Get delivery metrics for the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = [
            r
            for r in self._records.values()
            if r.created_at >= cutoff
        ]

        total = len(recent)
        if total == 0:
            return DeliveryMetrics()

        sent = sum(
            1
            for r in recent
            if r.status
            not in (DeliveryStatus.QUEUED, DeliveryStatus.SUPPRESSED)
        )
        delivered = sum(
            1
            for r in recent
            if r.status
            in (
                DeliveryStatus.DELIVERED,
                DeliveryStatus.OPENED,
                DeliveryStatus.CLICKED,
            )
        )
        bounced = sum(
            1
            for r in recent
            if r.status == DeliveryStatus.BOUNCED
        )
        complained = sum(
            1
            for r in recent
            if r.status == DeliveryStatus.COMPLAINED
        )
        opened = sum(
            1
            for r in recent
            if r.status
            in (DeliveryStatus.OPENED, DeliveryStatus.CLICKED)
        )
        hard = sum(
            1
            for r in recent
            if r.bounce_type == BounceType.HARD
        )
        soft = sum(
            1
            for r in recent
            if r.bounce_type == BounceType.SOFT
        )

        return DeliveryMetrics(
            total_sent=sent,
            total_delivered=delivered,
            total_bounced=bounced,
            total_complained=complained,
            total_opened=opened,
            delivery_rate=delivered / sent if sent else 0.0,
            bounce_rate=bounced / sent if sent else 0.0,
            open_rate=opened / delivered if delivered else 0.0,
            hard_bounces=hard,
            soft_bounces=soft,
        )

    def get_recent_failures(
        self, limit: int = 50
    ) -> list[DeliveryRecord]:
        failed = [
            r
            for r in self._records.values()
            if r.status
            in (
                DeliveryStatus.BOUNCED,
                DeliveryStatus.FAILED,
                DeliveryStatus.COMPLAINED,
            )
        ]
        failed.sort(
            key=lambda r: r.created_at or datetime.min.replace(
                tzinfo=timezone.utc
            ),
            reverse=True,
        )
        return failed[:limit]

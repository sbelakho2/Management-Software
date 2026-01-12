"""Security Logging & Audit (Development Plan 21.8 — Cybersecurity).

Implements:
- Security Event Dashboard: aggregated security events with severity classification.
- Threat Detection: anomaly scoring and alert generation for suspicious patterns.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class EventSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EventCategory(str, Enum):
    AUTH_FAILURE = "auth_failure"
    AUTH_SUCCESS = "auth_success"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_ACCESS = "data_access"
    NETWORK = "network"
    POLICY_VIOLATION = "policy_violation"
    SYSTEM = "system"


class AlertStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


_SECOPS_ROLES: set[str] = {"admin", "secops", "gm", "ceo"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SecurityEvent:
    id: UUID
    timestamp: datetime
    category: EventCategory
    severity: EventSeverity
    source_ip: str | None
    user_id: UUID | None
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatAlert:
    id: UUID
    title: str
    description: str
    severity: EventSeverity
    status: AlertStatus
    related_event_ids: list[UUID]
    anomaly_score: float
    created_at: datetime
    updated_at: datetime


class SecurityLoggingService:
    """In-memory security event collection & threat detection."""

    def __init__(self) -> None:
        self._events: dict[UUID, SecurityEvent] = {}
        self._alerts: dict[UUID, ThreatAlert] = {}

        # For anomaly detection: track auth failures per user within rolling window.
        self._auth_failures_by_user: dict[UUID, list[datetime]] = defaultdict(list)

    # ---- RBAC ----

    def can_view(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_SECOPS_ROLES)) > 0

    # ---- Event Logging ----

    def log_event(
        self,
        *,
        category: EventCategory,
        severity: EventSeverity,
        description: str,
        source_ip: str | None = None,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            id=uuid4(),
            timestamp=_utcnow(),
            category=category,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            description=description,
            metadata=metadata or {},
        )
        self._events[event.id] = event

        # Feed anomaly detection.
        if category == EventCategory.AUTH_FAILURE and user_id:
            self._auth_failures_by_user[user_id].append(event.timestamp)
            self._check_brute_force(user_id, event)

        return event

    def list_events(
        self,
        *,
        actor_roles: Iterable[str],
        category: EventCategory | None = None,
        severity: EventSeverity | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view security events")

        result = list(self._events.values())

        if category:
            result = [e for e in result if e.category == category]
        if severity:
            result = [e for e in result if e.severity == severity]
        if since:
            result = [e for e in result if e.timestamp >= since]

        result.sort(key=lambda e: e.timestamp, reverse=True)
        return result[:limit]

    def get_event_counts_by_severity(
        self,
        *,
        actor_roles: Iterable[str],
        since: datetime | None = None,
    ) -> dict[str, int]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view security events")

        counts: dict[str, int] = {s.value: 0 for s in EventSeverity}
        for event in self._events.values():
            if since and event.timestamp < since:
                continue
            counts[event.severity.value] += 1
        return counts

    # ---- Threat Detection ----

    def _check_brute_force(self, user_id: UUID, event: SecurityEvent) -> None:
        """Detect brute-force attempts (5+ failures in 5 minutes)."""
        window_start = _utcnow() - timedelta(minutes=5)
        timestamps = self._auth_failures_by_user[user_id]
        recent = [ts for ts in timestamps if ts >= window_start]
        self._auth_failures_by_user[user_id] = recent

        if len(recent) >= 5:
            # Check if alert already exists for this user.
            existing = [
                a
                for a in self._alerts.values()
                if a.status in (AlertStatus.OPEN, AlertStatus.INVESTIGATING)
                and event.id not in a.related_event_ids
                and any(eid in a.related_event_ids for eid in [e.id for e in self._events.values() if e.user_id == user_id])
            ]
            if existing:
                # Append to existing alert.
                alert = existing[0]
                alert.related_event_ids.append(event.id)
                alert.anomaly_score = min(alert.anomaly_score + 0.1, 1.0)
                alert.updated_at = _utcnow()
            else:
                # Create new alert.
                alert = ThreatAlert(
                    id=uuid4(),
                    title="Possible brute-force attack",
                    description=f"Multiple auth failures for user {user_id}",
                    severity=EventSeverity.HIGH,
                    status=AlertStatus.OPEN,
                    related_event_ids=[event.id],
                    anomaly_score=0.7,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                self._alerts[alert.id] = alert

    def list_alerts(
        self,
        *,
        actor_roles: Iterable[str],
        status: AlertStatus | None = None,
    ) -> list[ThreatAlert]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view threat alerts")

        result = list(self._alerts.values())
        if status:
            result = [a for a in result if a.status == status]
        result.sort(key=lambda a: a.created_at, reverse=True)
        return result

    def update_alert_status(
        self,
        alert_id: UUID,
        *,
        status: AlertStatus,
        actor_roles: Iterable[str],
    ) -> ThreatAlert:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to update threat alerts")
        if alert_id not in self._alerts:
            raise KeyError("Alert not found")

        alert = self._alerts[alert_id]
        alert.status = status
        alert.updated_at = _utcnow()
        return alert

    def compute_risk_score(
        self,
        *,
        actor_roles: Iterable[str],
        window_hours: int = 24,
    ) -> float:
        """Compute overall risk score 0.0-1.0 based on recent events."""
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view security risk")

        since = _utcnow() - timedelta(hours=window_hours)
        counts = self.get_event_counts_by_severity(actor_roles=actor_roles, since=since)

        # Weighted score.
        weights = {
            EventSeverity.CRITICAL.value: 0.5,
            EventSeverity.HIGH.value: 0.3,
            EventSeverity.MEDIUM.value: 0.15,
            EventSeverity.LOW.value: 0.05,
            EventSeverity.INFO.value: 0.0,
        }

        score = 0.0
        for sev, count in counts.items():
            score += min(count * weights.get(sev, 0), 1.0)

        return min(score, 1.0)

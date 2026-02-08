"""
Alerting rules engine for critical service failures.

Defines alert rules, severity levels, escalation chains,
and notification routing. Integrates with notification_dispatcher
for multi-channel delivery.

Checklist item: #423
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels (aligned with PagerDuty/OpsGenie)."""

    CRITICAL = "critical"  # Immediate response required
    HIGH = "high"  # Response within 15 min
    MEDIUM = "medium"  # Response within 1 hour
    LOW = "low"  # Next business day
    INFO = "info"  # Informational only


class AlertStatus(str, Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class AlertRule:
    """Defines when an alert should fire."""

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    name: str = ""
    description: str = ""
    severity: AlertSeverity = AlertSeverity.MEDIUM
    service: str = ""  # service name to monitor
    condition: str = ""  # human-readable condition description
    check_fn: Callable[[], bool] | None = None  # returns True if alert should fire
    cooldown_minutes: int = 15  # minimum time between re-fires
    enabled: bool = True
    notify_channels: list[str] = field(
        default_factory=lambda: ["in_app", "email"]
    )
    notify_roles: list[str] = field(
        default_factory=lambda: ["admin"]
    )
    tags: list[str] = field(default_factory=list)


@dataclass
class Alert:
    """An active alert instance."""

    id: str = field(default_factory=lambda: uuid4().hex[:16])
    rule_id: str = ""
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.MEDIUM
    service: str = ""
    status: AlertStatus = AlertStatus.FIRING
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    fired_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class AlertingService:
    """Central alerting service for critical failures.

    Usage::

        alerting = AlertingService()

        # Register rules
        alerting.register_rule(AlertRule(
            name="Database Connection Pool Exhausted",
            severity=AlertSeverity.CRITICAL,
            service="database",
            condition="connection_pool_utilization > 90%",
            check_fn=lambda: db_pool.utilization() > 0.9,
            cooldown_minutes=5,
        ))

        # Evaluate all rules
        new_alerts = alerting.evaluate_all()

        # Or fire manually
        alerting.fire(
            rule_name="Celery Queue Depth",
            severity=AlertSeverity.HIGH,
            message="Queue depth exceeded 10000",
            details={"queue": "default", "depth": 12345},
        )

        # Acknowledge / resolve
        alerting.acknowledge(alert_id, user_id="ops-1")
        alerting.resolve(alert_id, user_id="ops-1")
    """

    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._alerts: dict[str, Alert] = {}
        self._last_fired: dict[str, datetime] = {}  # rule_id → last fire time
        self._silenced: dict[str, datetime] = {}  # rule_id → silence until
        self._on_alert_callbacks: list[Callable[[Alert], None]] = []
        self._history: list[Alert] = []

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def register_rule(self, rule: AlertRule) -> str:
        """Register an alert rule. Returns rule ID."""
        self._rules[rule.id] = rule
        logger.info("Registered alert rule: %s (%s)", rule.name, rule.id)
        return rule.id

    def remove_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def get_rules(self) -> list[AlertRule]:
        return list(self._rules.values())

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_all(self) -> list[Alert]:
        """Evaluate all enabled rules and fire alerts for violations."""
        new_alerts: list[Alert] = []
        now = datetime.now(timezone.utc)

        for rule in self._rules.values():
            if not rule.enabled or not rule.check_fn:
                continue

            # Check cooldown
            last = self._last_fired.get(rule.id)
            if last and (now - last) < timedelta(minutes=rule.cooldown_minutes):
                continue

            # Check silence
            silence_until = self._silenced.get(rule.id)
            if silence_until and now < silence_until:
                continue

            try:
                should_fire = rule.check_fn()
            except Exception:
                logger.exception("Alert rule check failed: %s", rule.name)
                should_fire = True  # Err on side of alerting

            if should_fire:
                alert = self.fire(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Alert rule triggered: {rule.condition}",
                    details={"rule_id": rule.id, "service": rule.service},
                    _rule_id=rule.id,
                )
                new_alerts.append(alert)

        return new_alerts

    def fire(
        self,
        rule_name: str,
        severity: AlertSeverity,
        message: str,
        details: dict[str, Any] | None = None,
        service: str = "",
        *,
        _rule_id: str = "",
    ) -> Alert:
        """Manually fire an alert."""
        alert = Alert(
            rule_id=_rule_id,
            rule_name=rule_name,
            severity=severity,
            service=service,
            message=message,
            details=details or {},
        )
        self._alerts[alert.id] = alert
        if _rule_id:
            self._last_fired[_rule_id] = alert.fired_at

        for cb in self._on_alert_callbacks:
            try:
                cb(alert)
            except Exception:
                logger.exception("Alert callback error")

        logger.warning(
            "ALERT [%s] %s: %s",
            severity.value.upper(),
            rule_name,
            message,
        )
        return alert

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def acknowledge(
        self, alert_id: str, user_id: str = ""
    ) -> bool:
        alert = self._alerts.get(alert_id)
        if not alert or alert.status != AlertStatus.FIRING:
            return False
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id
        return True

    def resolve(
        self, alert_id: str, user_id: str = ""
    ) -> bool:
        alert = self._alerts.get(alert_id)
        if not alert or alert.status == AlertStatus.RESOLVED:
            return False
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = user_id
        self._history.append(alert)
        return True

    def silence_rule(
        self, rule_id: str, duration_minutes: int = 60
    ) -> None:
        """Silence a rule for a specified duration."""
        self._silenced[rule_id] = datetime.now(
            timezone.utc
        ) + timedelta(minutes=duration_minutes)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_alerts(
        self,
        severity: AlertSeverity | None = None,
        service: str | None = None,
    ) -> list[Alert]:
        result = [
            a
            for a in self._alerts.values()
            if a.status in (AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED)
        ]
        if severity:
            result = [a for a in result if a.severity == severity]
        if service:
            result = [a for a in result if a.service == service]
        result.sort(
            key=lambda a: (
                list(AlertSeverity).index(a.severity),
                a.fired_at,
            )
        )
        return result

    def get_alert_history(
        self, limit: int = 100
    ) -> list[Alert]:
        return sorted(
            self._history, key=lambda a: a.fired_at, reverse=True
        )[:limit]

    def get_stats(self) -> dict[str, Any]:
        active = self.get_active_alerts()
        by_severity = defaultdict(int)
        for a in active:
            by_severity[a.severity.value] += 1
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(
                1 for r in self._rules.values() if r.enabled
            ),
            "active_alerts": len(active),
            "by_severity": dict(by_severity),
            "total_resolved": len(self._history),
            "silenced_rules": sum(
                1
                for rid, until in self._silenced.items()
                if until > datetime.now(timezone.utc)
            ),
        }

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_alert(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback to be called when an alert fires."""
        self._on_alert_callbacks.append(callback)


# ------------------------------------------------------------------
# Pre-built rule templates
# ------------------------------------------------------------------

def create_standard_rules() -> list[AlertRule]:
    """Return a set of standard alert rules (check_fn must be wired)."""
    return [
        AlertRule(
            name="Database Connection Pool Exhausted",
            severity=AlertSeverity.CRITICAL,
            service="database",
            condition="pool_utilization > 90%",
            cooldown_minutes=5,
            notify_channels=["email", "push", "in_app"],
        ),
        AlertRule(
            name="Redis Connection Failed",
            severity=AlertSeverity.CRITICAL,
            service="redis",
            condition="redis_ping_failed",
            cooldown_minutes=2,
            notify_channels=["email", "push", "in_app"],
        ),
        AlertRule(
            name="Celery Worker Queue Depth High",
            severity=AlertSeverity.HIGH,
            service="celery",
            condition="queue_depth > 10000",
            cooldown_minutes=10,
        ),
        AlertRule(
            name="API Error Rate High",
            severity=AlertSeverity.HIGH,
            service="api",
            condition="5xx_rate > 5% in 5min",
            cooldown_minutes=10,
        ),
        AlertRule(
            name="Disk Usage Critical",
            severity=AlertSeverity.HIGH,
            service="infrastructure",
            condition="disk_usage > 90%",
            cooldown_minutes=30,
        ),
        AlertRule(
            name="Email Bounce Rate High",
            severity=AlertSeverity.MEDIUM,
            service="email",
            condition="bounce_rate > 10% in 1hr",
            cooldown_minutes=60,
        ),
        AlertRule(
            name="AI Model Inference Latency",
            severity=AlertSeverity.MEDIUM,
            service="ai",
            condition="p95_latency > 5s",
            cooldown_minutes=15,
        ),
        AlertRule(
            name="Backup Job Failed",
            severity=AlertSeverity.HIGH,
            service="backup",
            condition="last_backup_failed",
            cooldown_minutes=30,
        ),
    ]

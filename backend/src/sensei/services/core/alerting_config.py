"""Alerting Configuration Service.

Provides alert rule management, notification routing, 
silencing, and alert grouping functionality.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Any
import uuid
import re
from uuid import UUID

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class AlertSeverity(Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status."""

    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    ACKNOWLEDGED = "acknowledged"


class NotificationChannel(Enum):
    """Notification channel types."""

    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    TEAMS = "teams"
    OPSGENIE = "opsgenie"


class ComparisonOperator(Enum):
    """Comparison operators for alert conditions."""

    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "neq"


class AggregationFunction(Enum):
    """Aggregation functions for metrics."""

    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    RATE = "rate"
    P50 = "p50"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


@dataclass
class ThresholdCondition:
    """Threshold condition for alerts."""

    metric: str = ""
    aggregation: AggregationFunction = AggregationFunction.AVG
    operator: ComparisonOperator = ComparisonOperator.GREATER_THAN
    threshold: float = 0.0
    duration_seconds: int = 60  # Condition must hold for this duration
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class NotificationTarget:
    """Target for notifications."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    address: str = ""  # Email, webhook URL, Slack channel, etc.
    config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class NotificationRoute:
    """Routing rule for notifications."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    match_labels: dict[str, str] = field(default_factory=dict)
    match_severity: Optional[AlertSeverity] = None
    target_ids: list[str] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    group_wait_seconds: int = 30
    group_interval_seconds: int = 300
    repeat_interval_seconds: int = 3600
    is_active: bool = True


@dataclass
class AlertRule:
    """Alert rule definition."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    conditions: list[ThresholdCondition] = field(default_factory=list)
    severity: AlertSeverity = AlertSeverity.MEDIUM
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_by: str = ""
    evaluation_interval_seconds: int = 60
    for_duration_seconds: int = 0  # Alert must fire for this long
    route_ids: list[str] = field(default_factory=list)
    runbook_url: str = ""
    dashboard_url: str = ""


@dataclass
class Alert:
    """An active alert instance."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    rule_name: str = ""
    status: AlertStatus = AlertStatus.FIRING
    severity: AlertSeverity = AlertSeverity.MEDIUM
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    value: float = 0.0  # The value that triggered the alert
    threshold: float = 0.0
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: str = ""
    fingerprint: str = ""  # Unique identifier for grouping
    notification_sent: bool = False
    silence_id: Optional[str] = None


@dataclass
class Silence:
    """Alert silence/mute rule."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    comment: str = ""
    created_by: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    starts_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ends_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1)
    )
    matchers: dict[str, str] = field(default_factory=dict)  # Label matchers
    is_active: bool = True


@dataclass
class AlertGroup:
    """Group of related alerts."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    group_key: str = ""  # Key for grouping (e.g., service:api)
    labels: dict[str, str] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)  # Alert IDs
    status: AlertStatus = AlertStatus.FIRING
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_notification_at: Optional[datetime] = None


@dataclass
class AlertHistory:
    """History entry for an alert."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event: str = ""  # fired, resolved, acknowledged, silenced, etc.
    details: dict[str, Any] = field(default_factory=dict)


# Default alert rules
DEFAULT_RULES: list[dict] = [
    {
        "name": "High CPU Usage",
        "description": "CPU usage exceeds 80% for 5 minutes",
        "conditions": [
            ThresholdCondition(
                metric="cpu_usage_percent",
                aggregation=AggregationFunction.AVG,
                operator=ComparisonOperator.GREATER_THAN,
                threshold=80.0,
                duration_seconds=300,
            )
        ],
        "severity": AlertSeverity.HIGH,
        "labels": {"category": "infrastructure", "resource": "cpu"},
        "annotations": {
            "summary": "High CPU usage detected",
            "description": "CPU usage is above 80% for 5 minutes",
        },
    },
    {
        "name": "High Memory Usage",
        "description": "Memory usage exceeds 90%",
        "conditions": [
            ThresholdCondition(
                metric="memory_usage_percent",
                aggregation=AggregationFunction.AVG,
                operator=ComparisonOperator.GREATER_THAN,
                threshold=90.0,
                duration_seconds=120,
            )
        ],
        "severity": AlertSeverity.HIGH,
        "labels": {"category": "infrastructure", "resource": "memory"},
    },
    {
        "name": "High Error Rate",
        "description": "Error rate exceeds 5%",
        "conditions": [
            ThresholdCondition(
                metric="http_error_rate",
                aggregation=AggregationFunction.RATE,
                operator=ComparisonOperator.GREATER_THAN,
                threshold=5.0,
                duration_seconds=60,
            )
        ],
        "severity": AlertSeverity.CRITICAL,
        "labels": {"category": "application", "resource": "http"},
    },
    {
        "name": "High Response Latency",
        "description": "P95 response latency exceeds 500ms",
        "conditions": [
            ThresholdCondition(
                metric="http_response_time_ms",
                aggregation=AggregationFunction.P95,
                operator=ComparisonOperator.GREATER_THAN,
                threshold=500.0,
                duration_seconds=120,
            )
        ],
        "severity": AlertSeverity.MEDIUM,
        "labels": {"category": "performance", "resource": "latency"},
    },
    {
        "name": "Database Connection Pool Low",
        "description": "Available database connections below 10%",
        "conditions": [
            ThresholdCondition(
                metric="db_connection_pool_available_percent",
                aggregation=AggregationFunction.AVG,
                operator=ComparisonOperator.LESS_THAN,
                threshold=10.0,
                duration_seconds=60,
            )
        ],
        "severity": AlertSeverity.HIGH,
        "labels": {"category": "database", "resource": "connections"},
    },
    {
        "name": "Disk Space Low",
        "description": "Disk space below 15%",
        "conditions": [
            ThresholdCondition(
                metric="disk_free_percent",
                aggregation=AggregationFunction.MIN,
                operator=ComparisonOperator.LESS_THAN,
                threshold=15.0,
                duration_seconds=300,
            )
        ],
        "severity": AlertSeverity.MEDIUM,
        "labels": {"category": "infrastructure", "resource": "disk"},
    },
]

# Default notification targets
DEFAULT_TARGETS: list[dict] = [
    {
        "name": "On-Call PagerDuty",
        "channel": NotificationChannel.PAGERDUTY,
        "address": "oncall-service-key",
        "config": {"priority": "high"},
    },
    {
        "name": "Ops Slack Channel",
        "channel": NotificationChannel.SLACK,
        "address": "#ops-alerts",
        "config": {"mention_users": ["@oncall"]},
    },
    {
        "name": "Engineering Email",
        "channel": NotificationChannel.EMAIL,
        "address": "engineering@example.com",
    },
]


class AlertingConfigService(PersistentServiceMixin):
    """Service for managing alerting configuration."""

    SERVICE_NAME = "alerting_config"

    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

    def __init__(self) -> None:
        """Initialize the service."""
        self._rules: dict[str, AlertRule] = {}
        self._alerts: dict[str, Alert] = {}
        self._silences: dict[str, Silence] = {}
        self._targets: dict[str, NotificationTarget] = {}
        self._routes: dict[str, NotificationRoute] = {}
        self._groups: dict[str, AlertGroup] = {}
        self._history: list[AlertHistory] = []
        self._initialize_defaults()
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        state = await self.load_state(self._DEFAULT_TENANT_ID, "state")
        if not state:
            self._state_loaded = True
            return

        self._rules = {
            rule_id: decode_dataclass(rule, AlertRule)
            for rule_id, rule in state.get("rules", {}).items()
        }
        self._alerts = {
            alert_id: decode_dataclass(alert, Alert)
            for alert_id, alert in state.get("alerts", {}).items()
        }
        self._silences = {
            silence_id: decode_dataclass(silence, Silence)
            for silence_id, silence in state.get("silences", {}).items()
        }
        self._targets = {
            target_id: decode_dataclass(target, NotificationTarget)
            for target_id, target in state.get("targets", {}).items()
        }
        self._routes = {
            route_id: decode_dataclass(route, NotificationRoute)
            for route_id, route in state.get("routes", {}).items()
        }
        self._groups = {
            group_id: decode_dataclass(group, AlertGroup)
            for group_id, group in state.get("groups", {}).items()
        }
        self._history = [
            decode_dataclass(entry, AlertHistory)
            for entry in state.get("history", [])
        ]
        self._state_loaded = True

    async def persist_all(self) -> None:
        state = {
            "rules": {rule_id: encode_dataclass(rule) for rule_id, rule in self._rules.items()},
            "alerts": {alert_id: encode_dataclass(alert) for alert_id, alert in self._alerts.items()},
            "silences": {silence_id: encode_dataclass(silence) for silence_id, silence in self._silences.items()},
            "targets": {target_id: encode_dataclass(target) for target_id, target in self._targets.items()},
            "routes": {route_id: encode_dataclass(route) for route_id, route in self._routes.items()},
            "groups": {group_id: encode_dataclass(group) for group_id, group in self._groups.items()},
            "history": [encode_dataclass(entry) for entry in self._history],
        }
        await self.save_state(self._DEFAULT_TENANT_ID, "state", state)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    def _initialize_defaults(self) -> None:
        """Initialize default configuration."""
        # Create default targets
        for target_data in DEFAULT_TARGETS:
            target = NotificationTarget(
                name=target_data["name"],
                channel=target_data["channel"],
                address=target_data["address"],
                config=target_data.get("config", {}),
            )
            self._targets[target.id] = target

        # Create default routes
        target_ids = list(self._targets.keys())

        # Critical alerts -> PagerDuty
        pagerduty_targets = [
            t.id for t in self._targets.values()
            if t.channel == NotificationChannel.PAGERDUTY
        ]
        if pagerduty_targets:
            critical_route = NotificationRoute(
                name="Critical to PagerDuty",
                match_severity=AlertSeverity.CRITICAL,
                target_ids=pagerduty_targets,
                group_wait_seconds=10,
                group_interval_seconds=60,
            )
            self._routes[critical_route.id] = critical_route

        # High alerts -> Slack
        slack_targets = [
            t.id for t in self._targets.values()
            if t.channel == NotificationChannel.SLACK
        ]
        if slack_targets:
            high_route = NotificationRoute(
                name="High to Slack",
                match_severity=AlertSeverity.HIGH,
                target_ids=slack_targets,
                group_wait_seconds=30,
            )
            self._routes[high_route.id] = high_route

        # All alerts -> Email (catch-all)
        email_targets = [
            t.id for t in self._targets.values()
            if t.channel == NotificationChannel.EMAIL
        ]
        if email_targets:
            default_route = NotificationRoute(
                name="Default Email Route",
                target_ids=email_targets,
                group_wait_seconds=60,
                group_interval_seconds=600,
            )
            self._routes[default_route.id] = default_route

        # Create default rules
        for rule_data in DEFAULT_RULES:
            rule = AlertRule(
                name=rule_data["name"],
                description=rule_data["description"],
                conditions=rule_data["conditions"],
                severity=rule_data["severity"],
                labels=rule_data["labels"],
                annotations=rule_data.get("annotations", {}),
            )
            self._rules[rule.id] = rule

    # ========================================
    # Rule Management
    # ========================================

    def create_rule(
        self,
        name: str,
        conditions: list[ThresholdCondition],
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        description: str = "",
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        created_by: str = "",
        evaluation_interval_seconds: int = 60,
        for_duration_seconds: int = 0,
        route_ids: Optional[list[str]] = None,
        runbook_url: str = "",
        dashboard_url: str = "",
    ) -> AlertRule:
        """Create a new alert rule."""
        rule = AlertRule(
            name=name,
            description=description,
            conditions=conditions,
            severity=severity,
            labels=labels or {},
            annotations=annotations or {},
            created_by=created_by,
            evaluation_interval_seconds=evaluation_interval_seconds,
            for_duration_seconds=for_duration_seconds,
            route_ids=route_ids or [],
            runbook_url=runbook_url,
            dashboard_url=dashboard_url,
        )
        self._rules[rule.id] = rule
        return rule

    async def create_rule_async(self, *args: Any, **kwargs: Any) -> AlertRule:
        await self._ensure_loaded()
        rule = self.create_rule(*args, **kwargs)
        await self.persist_all()
        return rule

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> list[AlertRule]:
        """Get all rules."""
        return list(self._rules.values())

    def get_active_rules(self) -> list[AlertRule]:
        """Get active rules."""
        return [r for r in self._rules.values() if r.is_active]

    def get_rules_by_severity(self, severity: AlertSeverity) -> list[AlertRule]:
        """Get rules by severity."""
        return [r for r in self._rules.values() if r.severity == severity]

    def get_rules_by_label(self, key: str, value: str) -> list[AlertRule]:
        """Get rules matching a label."""
        return [
            r for r in self._rules.values()
            if r.labels.get(key) == value
        ]

    def update_rule(
        self,
        rule_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        conditions: Optional[list[ThresholdCondition]] = None,
        severity: Optional[AlertSeverity] = None,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        is_active: Optional[bool] = None,
        evaluation_interval_seconds: Optional[int] = None,
        route_ids: Optional[list[str]] = None,
        runbook_url: Optional[str] = None,
        dashboard_url: Optional[str] = None,
    ) -> Optional[AlertRule]:
        """Update a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        if name is not None:
            rule.name = name
        if description is not None:
            rule.description = description
        if conditions is not None:
            rule.conditions = conditions
        if severity is not None:
            rule.severity = severity
        if labels is not None:
            rule.labels = labels
        if annotations is not None:
            rule.annotations = annotations
        if is_active is not None:
            rule.is_active = is_active
        if evaluation_interval_seconds is not None:
            rule.evaluation_interval_seconds = evaluation_interval_seconds
        if route_ids is not None:
            rule.route_ids = route_ids
        if runbook_url is not None:
            rule.runbook_url = runbook_url
        if dashboard_url is not None:
            rule.dashboard_url = dashboard_url

        rule.updated_at = datetime.now(timezone.utc)
        return rule

    async def update_rule_async(self, *args: Any, **kwargs: Any) -> Optional[AlertRule]:
        await self._ensure_loaded()
        rule = self.update_rule(*args, **kwargs)
        await self.persist_all()
        return rule

    def enable_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Enable a rule."""
        return self.update_rule(rule_id, is_active=True)

    def disable_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Disable a rule."""
        return self.update_rule(rule_id, is_active=False)

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    async def delete_rule_async(self, rule_id: str) -> bool:
        await self._ensure_loaded()
        deleted = self.delete_rule(rule_id)
        await self.persist_all()
        return deleted

    # ========================================
    # Notification Target Management
    # ========================================

    def create_target(
        self,
        name: str,
        channel: NotificationChannel,
        address: str,
        config: Optional[dict[str, Any]] = None,
    ) -> NotificationTarget:
        """Create a notification target."""
        target = NotificationTarget(
            name=name,
            channel=channel,
            address=address,
            config=config or {},
        )
        self._targets[target.id] = target
        return target

    async def create_target_async(self, *args: Any, **kwargs: Any) -> NotificationTarget:
        await self._ensure_loaded()
        target = self.create_target(*args, **kwargs)
        await self.persist_all()
        return target

    def get_target(self, target_id: str) -> Optional[NotificationTarget]:
        """Get a target by ID."""
        return self._targets.get(target_id)

    def get_all_targets(self) -> list[NotificationTarget]:
        """Get all targets."""
        return list(self._targets.values())

    def get_targets_by_channel(
        self, channel: NotificationChannel
    ) -> list[NotificationTarget]:
        """Get targets by channel."""
        return [t for t in self._targets.values() if t.channel == channel]

    def update_target(
        self,
        target_id: str,
        name: Optional[str] = None,
        address: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[NotificationTarget]:
        """Update a target."""
        target = self._targets.get(target_id)
        if not target:
            return None

        if name is not None:
            target.name = name
        if address is not None:
            target.address = address
        if config is not None:
            target.config = config
        if is_active is not None:
            target.is_active = is_active

        return target

    async def update_target_async(self, *args: Any, **kwargs: Any) -> Optional[NotificationTarget]:
        await self._ensure_loaded()
        target = self.update_target(*args, **kwargs)
        await self.persist_all()
        return target

    def delete_target(self, target_id: str) -> bool:
        """Delete a target."""
        if target_id in self._targets:
            del self._targets[target_id]
            return True
        return False

    async def delete_target_async(self, target_id: str) -> bool:
        await self._ensure_loaded()
        deleted = self.delete_target(target_id)
        await self.persist_all()
        return deleted

    # ========================================
    # Notification Route Management
    # ========================================

    def create_route(
        self,
        name: str,
        target_ids: list[str],
        match_labels: Optional[dict[str, str]] = None,
        match_severity: Optional[AlertSeverity] = None,
        group_by: Optional[list[str]] = None,
        group_wait_seconds: int = 30,
        group_interval_seconds: int = 300,
        repeat_interval_seconds: int = 3600,
    ) -> NotificationRoute:
        """Create a notification route."""
        route = NotificationRoute(
            name=name,
            match_labels=match_labels or {},
            match_severity=match_severity,
            target_ids=target_ids,
            group_by=group_by or [],
            group_wait_seconds=group_wait_seconds,
            group_interval_seconds=group_interval_seconds,
            repeat_interval_seconds=repeat_interval_seconds,
        )
        self._routes[route.id] = route
        return route

    async def create_route_async(self, *args: Any, **kwargs: Any) -> NotificationRoute:
        await self._ensure_loaded()
        route = self.create_route(*args, **kwargs)
        await self.persist_all()
        return route

    def get_route(self, route_id: str) -> Optional[NotificationRoute]:
        """Get a route by ID."""
        return self._routes.get(route_id)

    def get_all_routes(self) -> list[NotificationRoute]:
        """Get all routes."""
        return list(self._routes.values())

    def get_matching_routes(
        self,
        labels: dict[str, str],
        severity: AlertSeverity,
    ) -> list[NotificationRoute]:
        """Get routes matching labels and severity."""
        matching = []
        for route in self._routes.values():
            if not route.is_active:
                continue

            # Check severity match
            if route.match_severity and route.match_severity != severity:
                continue

            # Check label matches
            label_match = True
            for key, value in route.match_labels.items():
                if labels.get(key) != value:
                    label_match = False
                    break

            if label_match:
                matching.append(route)

        return matching

    def update_route(
        self,
        route_id: str,
        name: Optional[str] = None,
        target_ids: Optional[list[str]] = None,
        match_labels: Optional[dict[str, str]] = None,
        match_severity: Optional[AlertSeverity] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[NotificationRoute]:
        """Update a route."""
        route = self._routes.get(route_id)
        if not route:
            return None

        if name is not None:
            route.name = name
        if target_ids is not None:
            route.target_ids = target_ids
        if match_labels is not None:
            route.match_labels = match_labels
        if match_severity is not None:
            route.match_severity = match_severity
        if is_active is not None:
            route.is_active = is_active

        return route

    async def update_route_async(self, *args: Any, **kwargs: Any) -> Optional[NotificationRoute]:
        await self._ensure_loaded()
        route = self.update_route(*args, **kwargs)
        await self.persist_all()
        return route

    def delete_route(self, route_id: str) -> bool:
        """Delete a route."""
        if route_id in self._routes:
            del self._routes[route_id]
            return True
        return False

    async def delete_route_async(self, route_id: str) -> bool:
        await self._ensure_loaded()
        deleted = self.delete_route(route_id)
        await self.persist_all()
        return deleted

    # ========================================
    # Alert Management
    # ========================================

    def _generate_fingerprint(
        self,
        rule_id: str,
        labels: dict[str, str],
    ) -> str:
        """Generate a fingerprint for alert deduplication."""
        sorted_labels = sorted(labels.items())
        label_str = ",".join(f"{k}={v}" for k, v in sorted_labels)
        return f"{rule_id}:{label_str}"

    def fire_alert(
        self,
        rule_id: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
    ) -> Optional[Alert]:
        """Fire an alert for a rule."""
        rule = self._rules.get(rule_id)
        if not rule or not rule.is_active:
            return None

        merged_labels = {**rule.labels, **(labels or {})}
        fingerprint = self._generate_fingerprint(rule_id, merged_labels)

        # Check if alert already exists
        existing = next(
            (a for a in self._alerts.values()
             if a.fingerprint == fingerprint and a.status == AlertStatus.FIRING),
            None
        )
        if existing:
            return existing

        # Check if silenced
        silence_id = self._check_silences(merged_labels)

        alert = Alert(
            rule_id=rule_id,
            rule_name=rule.name,
            status=AlertStatus.SILENCED if silence_id else AlertStatus.FIRING,
            severity=rule.severity,
            labels=merged_labels,
            annotations={**rule.annotations, **(annotations or {})},
            value=value,
            threshold=rule.conditions[0].threshold if rule.conditions else 0,
            fingerprint=fingerprint,
            silence_id=silence_id,
        )
        self._alerts[alert.id] = alert

        # Record history
        self._record_history(alert.id, "fired", {
            "value": value,
            "threshold": alert.threshold,
        })

        return alert

    async def fire_alert_async(self, *args: Any, **kwargs: Any) -> Optional[Alert]:
        await self._ensure_loaded()
        alert = self.fire_alert(*args, **kwargs)
        await self.persist_all()
        return alert

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def get_all_alerts(self) -> list[Alert]:
        """Get all alerts."""
        return list(self._alerts.values())

    def get_firing_alerts(self) -> list[Alert]:
        """Get firing alerts."""
        return [a for a in self._alerts.values() if a.status == AlertStatus.FIRING]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        """Get alerts by severity."""
        return [a for a in self._alerts.values() if a.severity == severity]

    def get_alerts_by_rule(self, rule_id: str) -> list[Alert]:
        """Get alerts by rule."""
        return [a for a in self._alerts.values() if a.rule_id == rule_id]

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by

        self._record_history(alert_id, "acknowledged", {
            "by": acknowledged_by,
        })

        return alert

    async def acknowledge_alert_async(self, *args: Any, **kwargs: Any) -> Optional[Alert]:
        await self._ensure_loaded()
        alert = self.acknowledge_alert(*args, **kwargs)
        await self.persist_all()
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)

        self._record_history(alert_id, "resolved", {})

        return alert

    async def resolve_alert_async(self, alert_id: str) -> Optional[Alert]:
        await self._ensure_loaded()
        alert = self.resolve_alert(alert_id)
        await self.persist_all()
        return alert

    def silence_alert(
        self,
        alert_id: str,
        silence_id: str,
    ) -> Optional[Alert]:
        """Apply a silence to an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.SILENCED
        alert.silence_id = silence_id

        self._record_history(alert_id, "silenced", {
            "silence_id": silence_id,
        })

        return alert

    async def silence_alert_async(self, *args: Any, **kwargs: Any) -> Optional[Alert]:
        await self._ensure_loaded()
        alert = self.silence_alert(*args, **kwargs)
        await self.persist_all()
        return alert

    # ========================================
    # Silence Management
    # ========================================

    def _check_silences(self, labels: dict[str, str]) -> Optional[str]:
        """Check if labels match any active silence."""
        now = datetime.now(timezone.utc)
        for silence in self._silences.values():
            if not silence.is_active:
                continue
            if silence.starts_at > now or silence.ends_at < now:
                continue

            # Check if all matchers match
            all_match = True
            for key, pattern in silence.matchers.items():
                if key not in labels:
                    all_match = False
                    break
                if not re.match(pattern, labels[key]):
                    all_match = False
                    break

            if all_match:
                return silence.id

        return None

    def create_silence(
        self,
        matchers: dict[str, str],
        starts_at: Optional[datetime] = None,
        ends_at: Optional[datetime] = None,
        duration_hours: int = 1,
        name: str = "",
        comment: str = "",
        created_by: str = "",
    ) -> Silence:
        """Create a silence."""
        now = datetime.now(timezone.utc)
        start = starts_at or now
        end = ends_at or (start + timedelta(hours=duration_hours))

        silence = Silence(
            name=name,
            comment=comment,
            created_by=created_by,
            starts_at=start,
            ends_at=end,
            matchers=matchers,
        )
        self._silences[silence.id] = silence
        return silence

    async def create_silence_async(self, *args: Any, **kwargs: Any) -> Silence:
        await self._ensure_loaded()
        silence = self.create_silence(*args, **kwargs)
        await self.persist_all()
        return silence

    def get_silence(self, silence_id: str) -> Optional[Silence]:
        """Get a silence by ID."""
        return self._silences.get(silence_id)

    def get_all_silences(self) -> list[Silence]:
        """Get all silences."""
        return list(self._silences.values())

    def get_active_silences(self) -> list[Silence]:
        """Get active silences."""
        now = datetime.now(timezone.utc)
        return [
            s for s in self._silences.values()
            if s.is_active and s.starts_at <= now <= s.ends_at
        ]

    def expire_silence(self, silence_id: str) -> Optional[Silence]:
        """Expire a silence early."""
        silence = self._silences.get(silence_id)
        if not silence:
            return None

        silence.ends_at = datetime.now(timezone.utc)
        return silence

    async def expire_silence_async(self, silence_id: str) -> Optional[Silence]:
        await self._ensure_loaded()
        silence = self.expire_silence(silence_id)
        await self.persist_all()
        return silence

    def delete_silence(self, silence_id: str) -> bool:
        """Delete a silence."""
        if silence_id in self._silences:
            del self._silences[silence_id]
            return True
        return False

    async def delete_silence_async(self, silence_id: str) -> bool:
        await self._ensure_loaded()
        deleted = self.delete_silence(silence_id)
        await self.persist_all()
        return deleted

    # ========================================
    # Alert Grouping
    # ========================================

    def get_group_key(
        self,
        labels: dict[str, str],
        group_by: list[str],
    ) -> str:
        """Generate a group key from labels."""
        if not group_by:
            return "default"
        parts = [f"{k}={labels.get(k, '')}" for k in sorted(group_by)]
        return ",".join(parts)

    def group_alerts(
        self,
        alerts: list[Alert],
        group_by: list[str],
    ) -> list[AlertGroup]:
        """Group alerts by specified labels."""
        groups: dict[str, AlertGroup] = {}

        for alert in alerts:
            key = self.get_group_key(alert.labels, group_by)

            if key not in groups:
                group_labels = {k: alert.labels.get(k, "") for k in group_by}
                groups[key] = AlertGroup(
                    group_key=key,
                    labels=group_labels,
                )
                self._groups[groups[key].id] = groups[key]

            groups[key].alerts.append(alert.id)

        return list(groups.values())

    def get_alert_groups(self) -> list[AlertGroup]:
        """Get all alert groups."""
        return list(self._groups.values())

    # ========================================
    # History
    # ========================================

    def _record_history(
        self,
        alert_id: str,
        event: str,
        details: dict[str, Any],
    ) -> None:
        """Record an event in history."""
        entry = AlertHistory(
            alert_id=alert_id,
            event=event,
            details=details,
        )
        self._history.append(entry)

    def get_alert_history(self, alert_id: str) -> list[AlertHistory]:
        """Get history for an alert."""
        return [h for h in self._history if h.alert_id == alert_id]

    def get_recent_history(self, limit: int = 100) -> list[AlertHistory]:
        """Get recent history entries."""
        sorted_history = sorted(
            self._history,
            key=lambda h: h.timestamp,
            reverse=True,
        )
        return sorted_history[:limit]

    # ========================================
    # Validation
    # ========================================

    def validate_rule(self, rule: AlertRule) -> dict[str, Any]:
        """Validate an alert rule."""
        errors: list[str] = []
        warnings: list[str] = []

        if not rule.name:
            errors.append("Rule name is required")

        if not rule.conditions:
            errors.append("At least one condition is required")

        for i, condition in enumerate(rule.conditions):
            if not condition.metric:
                errors.append(f"Condition {i+1}: metric is required")
            if condition.duration_seconds < 0:
                errors.append(f"Condition {i+1}: duration must be positive")

        if rule.evaluation_interval_seconds < 10:
            warnings.append("Evaluation interval below 10s may cause high load")

        if not rule.route_ids:
            warnings.append("No notification routes configured")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def validate_target(self, target: NotificationTarget) -> dict[str, Any]:
        """Validate a notification target."""
        errors: list[str] = []
        warnings: list[str] = []

        if not target.name:
            errors.append("Target name is required")

        if not target.address:
            errors.append("Target address is required")

        if target.channel == NotificationChannel.EMAIL:
            if "@" not in target.address:
                errors.append("Invalid email address format")

        if target.channel == NotificationChannel.WEBHOOK:
            if not target.address.startswith(("http://", "https://")):
                errors.append("Webhook URL must start with http:// or https://")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ========================================
    # Summary
    # ========================================

    def get_summary(self) -> dict[str, Any]:
        """Get alerting summary."""
        rules = self.get_all_rules()
        alerts = self.get_all_alerts()
        silences = self.get_all_silences()
        targets = self.get_all_targets()
        routes = self.get_all_routes()

        by_severity: dict[str, int] = {}
        for alert in alerts:
            sev = alert.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

        by_status: dict[str, int] = {}
        for alert in alerts:
            status = alert.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_rules": len(rules),
            "active_rules": len([r for r in rules if r.is_active]),
            "total_alerts": len(alerts),
            "firing_alerts": len(self.get_firing_alerts()),
            "total_silences": len(silences),
            "active_silences": len(self.get_active_silences()),
            "total_targets": len(targets),
            "total_routes": len(routes),
            "alerts_by_severity": by_severity,
            "alerts_by_status": by_status,
        }

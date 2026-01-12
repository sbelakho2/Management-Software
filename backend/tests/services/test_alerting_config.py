"""Tests for Alerting Configuration Service.

Tests alert rules, notification targets, routes, silences,
and alert management.
"""

import pytest
from datetime import datetime, timezone, timedelta

from sensei.services.core.alerting_config import (
    AlertingConfigService,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
    NotificationTarget,
    NotificationRoute,
    Silence,
    AlertGroup,
    ThresholdCondition,
    ComparisonOperator,
    AggregationFunction,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service() -> AlertingConfigService:
    """Create a fresh AlertingConfigService instance."""
    return AlertingConfigService()


@pytest.fixture
def sample_condition() -> ThresholdCondition:
    """Create a sample threshold condition."""
    return ThresholdCondition(
        metric="cpu_usage",
        aggregation=AggregationFunction.AVG,
        operator=ComparisonOperator.GREATER_THAN,
        threshold=80.0,
        duration_seconds=300,
    )


@pytest.fixture
def sample_rule(
    service: AlertingConfigService,
    sample_condition: ThresholdCondition,
) -> AlertRule:
    """Create a sample alert rule."""
    return service.create_rule(
        name="Test Rule",
        conditions=[sample_condition],
        severity=AlertSeverity.HIGH,
        description="A test alert rule",
        labels={"service": "api", "env": "production"},
        created_by="user-123",
    )


@pytest.fixture
def sample_target(service: AlertingConfigService) -> NotificationTarget:
    """Create a sample notification target."""
    return service.create_target(
        name="Test Target",
        channel=NotificationChannel.SLACK,
        address="#test-alerts",
    )


@pytest.fixture
def sample_route(
    service: AlertingConfigService,
    sample_target: NotificationTarget,
) -> NotificationRoute:
    """Create a sample notification route."""
    return service.create_route(
        name="Test Route",
        target_ids=[sample_target.id],
        match_severity=AlertSeverity.HIGH,
    )


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Test enum values."""

    def test_alert_severities(self) -> None:
        """Verify all severities exist."""
        expected = {"critical", "high", "medium", "low", "info"}
        actual = {s.value for s in AlertSeverity}
        assert actual == expected

    def test_alert_statuses(self) -> None:
        """Verify all statuses exist."""
        expected = {"firing", "resolved", "silenced", "acknowledged"}
        actual = {s.value for s in AlertStatus}
        assert actual == expected

    def test_notification_channels(self) -> None:
        """Verify all channels exist."""
        expected = {
            "email", "sms", "slack", "pagerduty",
            "webhook", "teams", "opsgenie",
        }
        actual = {c.value for c in NotificationChannel}
        assert actual == expected

    def test_comparison_operators(self) -> None:
        """Verify all operators exist."""
        expected = {"gt", "gte", "lt", "lte", "eq", "neq"}
        actual = {o.value for o in ComparisonOperator}
        assert actual == expected

    def test_aggregation_functions(self) -> None:
        """Verify all aggregations exist."""
        expected = {
            "avg", "sum", "min", "max", "count",
            "rate", "p50", "p90", "p95", "p99",
        }
        actual = {a.value for a in AggregationFunction}
        assert actual == expected


# ============================================================
# Rule Management Tests
# ============================================================


class TestRuleManagement:
    """Test alert rule management."""

    def test_default_rules_loaded(self, service: AlertingConfigService) -> None:
        """Test that default rules are loaded."""
        rules = service.get_all_rules()
        assert len(rules) >= 6  # We defined 6 default rules

    def test_create_rule(
        self,
        service: AlertingConfigService,
        sample_condition: ThresholdCondition,
    ) -> None:
        """Test creating a rule."""
        rule = service.create_rule(
            name="New Rule",
            conditions=[sample_condition],
            severity=AlertSeverity.CRITICAL,
            description="Test description",
        )

        assert rule.name == "New Rule"
        assert rule.severity == AlertSeverity.CRITICAL
        assert rule.is_active is True

    def test_get_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting a rule."""
        retrieved = service.get_rule(sample_rule.id)
        assert retrieved is not None
        assert retrieved.id == sample_rule.id

    def test_get_rule_nonexistent(self, service: AlertingConfigService) -> None:
        """Test getting non-existent rule."""
        rule = service.get_rule("nonexistent")
        assert rule is None

    def test_get_all_rules(self, service: AlertingConfigService) -> None:
        """Test getting all rules."""
        rules = service.get_all_rules()
        assert len(rules) >= 6

    def test_get_active_rules(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting active rules."""
        active = service.get_active_rules()
        assert sample_rule.id in [r.id for r in active]

    def test_get_rules_by_severity(self, service: AlertingConfigService) -> None:
        """Test getting rules by severity."""
        critical = service.get_rules_by_severity(AlertSeverity.CRITICAL)
        assert len(critical) >= 1

    def test_get_rules_by_label(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting rules by label."""
        api_rules = service.get_rules_by_label("service", "api")
        assert sample_rule.id in [r.id for r in api_rules]

    def test_update_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test updating a rule."""
        updated = service.update_rule(
            sample_rule.id,
            name="Updated Rule Name",
            description="Updated description",
            severity=AlertSeverity.CRITICAL,
        )

        assert updated is not None
        assert updated.name == "Updated Rule Name"
        assert updated.severity == AlertSeverity.CRITICAL

    def test_update_rule_nonexistent(self, service: AlertingConfigService) -> None:
        """Test updating non-existent rule."""
        result = service.update_rule("nonexistent", name="Test")
        assert result is None

    def test_enable_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test enabling a rule."""
        service.disable_rule(sample_rule.id)
        updated = service.enable_rule(sample_rule.id)

        assert updated is not None
        assert updated.is_active is True

    def test_disable_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test disabling a rule."""
        updated = service.disable_rule(sample_rule.id)

        assert updated is not None
        assert updated.is_active is False

    def test_delete_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test deleting a rule."""
        result = service.delete_rule(sample_rule.id)
        assert result is True
        assert service.get_rule(sample_rule.id) is None

    def test_delete_rule_nonexistent(self, service: AlertingConfigService) -> None:
        """Test deleting non-existent rule."""
        result = service.delete_rule("nonexistent")
        assert result is False


# ============================================================
# Notification Target Tests
# ============================================================


class TestNotificationTargets:
    """Test notification target management."""

    def test_default_targets_loaded(self, service: AlertingConfigService) -> None:
        """Test that default targets are loaded."""
        targets = service.get_all_targets()
        assert len(targets) >= 3  # We defined 3 default targets

    def test_create_target(self, service: AlertingConfigService) -> None:
        """Test creating a target."""
        target = service.create_target(
            name="New Target",
            channel=NotificationChannel.EMAIL,
            address="test@example.com",
        )

        assert target.name == "New Target"
        assert target.channel == NotificationChannel.EMAIL
        assert target.address == "test@example.com"

    def test_create_target_with_config(self, service: AlertingConfigService) -> None:
        """Test creating target with config."""
        target = service.create_target(
            name="Webhook Target",
            channel=NotificationChannel.WEBHOOK,
            address="https://example.com/webhook",
            config={"headers": {"Authorization": "Bearer token"}},
        )

        assert target.config["headers"]["Authorization"] == "Bearer token"

    def test_get_target(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test getting a target."""
        retrieved = service.get_target(sample_target.id)
        assert retrieved is not None
        assert retrieved.id == sample_target.id

    def test_get_target_nonexistent(self, service: AlertingConfigService) -> None:
        """Test getting non-existent target."""
        target = service.get_target("nonexistent")
        assert target is None

    def test_get_targets_by_channel(self, service: AlertingConfigService) -> None:
        """Test getting targets by channel."""
        email_targets = service.get_targets_by_channel(NotificationChannel.EMAIL)
        assert len(email_targets) >= 1

    def test_update_target(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test updating a target."""
        updated = service.update_target(
            sample_target.id,
            name="Updated Target",
            address="#new-channel",
        )

        assert updated is not None
        assert updated.name == "Updated Target"
        assert updated.address == "#new-channel"

    def test_delete_target(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test deleting a target."""
        result = service.delete_target(sample_target.id)
        assert result is True
        assert service.get_target(sample_target.id) is None


# ============================================================
# Notification Route Tests
# ============================================================


class TestNotificationRoutes:
    """Test notification route management."""

    def test_default_routes_loaded(self, service: AlertingConfigService) -> None:
        """Test that default routes are loaded."""
        routes = service.get_all_routes()
        assert len(routes) >= 3  # Critical, High, Default

    def test_create_route(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test creating a route."""
        route = service.create_route(
            name="Custom Route",
            target_ids=[sample_target.id],
            match_severity=AlertSeverity.CRITICAL,
        )

        assert route.name == "Custom Route"
        assert sample_target.id in route.target_ids

    def test_create_route_with_labels(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test creating route with label matchers."""
        route = service.create_route(
            name="Label Route",
            target_ids=[sample_target.id],
            match_labels={"service": "api", "env": "production"},
        )

        assert route.match_labels["service"] == "api"

    def test_get_route(
        self,
        service: AlertingConfigService,
        sample_route: NotificationRoute,
    ) -> None:
        """Test getting a route."""
        retrieved = service.get_route(sample_route.id)
        assert retrieved is not None
        assert retrieved.id == sample_route.id

    def test_get_matching_routes_by_severity(
        self,
        service: AlertingConfigService,
        sample_route: NotificationRoute,
    ) -> None:
        """Test getting routes matching severity."""
        matching = service.get_matching_routes(
            labels={},
            severity=AlertSeverity.HIGH,
        )
        assert sample_route.id in [r.id for r in matching]

    def test_get_matching_routes_by_labels(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test getting routes matching labels."""
        route = service.create_route(
            name="API Route",
            target_ids=[sample_target.id],
            match_labels={"service": "api"},
        )

        matching = service.get_matching_routes(
            labels={"service": "api", "env": "prod"},
            severity=AlertSeverity.MEDIUM,
        )
        assert route.id in [r.id for r in matching]

    def test_get_matching_routes_no_match(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test that non-matching labels don't return route."""
        route = service.create_route(
            name="Specific Route",
            target_ids=[sample_target.id],
            match_labels={"service": "database"},
        )

        matching = service.get_matching_routes(
            labels={"service": "api"},
            severity=AlertSeverity.MEDIUM,
        )
        assert route.id not in [r.id for r in matching]

    def test_update_route(
        self,
        service: AlertingConfigService,
        sample_route: NotificationRoute,
    ) -> None:
        """Test updating a route."""
        updated = service.update_route(
            sample_route.id,
            name="Updated Route",
            match_severity=AlertSeverity.CRITICAL,
        )

        assert updated is not None
        assert updated.name == "Updated Route"
        assert updated.match_severity == AlertSeverity.CRITICAL

    def test_delete_route(
        self,
        service: AlertingConfigService,
        sample_route: NotificationRoute,
    ) -> None:
        """Test deleting a route."""
        result = service.delete_route(sample_route.id)
        assert result is True
        assert service.get_route(sample_route.id) is None


# ============================================================
# Alert Management Tests
# ============================================================


class TestAlertManagement:
    """Test alert management."""

    def test_fire_alert(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test firing an alert."""
        alert = service.fire_alert(
            rule_id=sample_rule.id,
            value=95.0,
        )

        assert alert is not None
        assert alert.status == AlertStatus.FIRING
        assert alert.value == 95.0
        assert alert.rule_id == sample_rule.id

    def test_fire_alert_inherits_labels(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that alert inherits rule labels."""
        alert = service.fire_alert(sample_rule.id, 90.0)

        assert alert.labels["service"] == "api"
        assert alert.labels["env"] == "production"

    def test_fire_alert_adds_labels(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that additional labels are merged."""
        alert = service.fire_alert(
            sample_rule.id,
            90.0,
            labels={"instance": "server-1"},
        )

        assert alert.labels["instance"] == "server-1"
        assert alert.labels["service"] == "api"  # Original label preserved

    def test_fire_alert_deduplicates(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that duplicate alerts are deduplicated."""
        alert1 = service.fire_alert(sample_rule.id, 90.0)
        alert2 = service.fire_alert(sample_rule.id, 95.0)

        # Same fingerprint, so should return existing alert
        assert alert1.id == alert2.id

    def test_fire_alert_disabled_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test firing alert on disabled rule."""
        service.disable_rule(sample_rule.id)
        alert = service.fire_alert(sample_rule.id, 90.0)
        assert alert is None

    def test_get_alert(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting an alert."""
        created = service.fire_alert(sample_rule.id, 90.0)
        retrieved = service.get_alert(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_firing_alerts(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting firing alerts."""
        service.fire_alert(sample_rule.id, 90.0)

        firing = service.get_firing_alerts()
        assert len(firing) >= 1

    def test_get_alerts_by_severity(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting alerts by severity."""
        service.fire_alert(sample_rule.id, 90.0)  # HIGH severity

        high_alerts = service.get_alerts_by_severity(AlertSeverity.HIGH)
        assert len(high_alerts) >= 1

    def test_get_alerts_by_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting alerts by rule."""
        service.fire_alert(sample_rule.id, 90.0)

        rule_alerts = service.get_alerts_by_rule(sample_rule.id)
        assert len(rule_alerts) >= 1

    def test_acknowledge_alert(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test acknowledging an alert."""
        alert = service.fire_alert(sample_rule.id, 90.0)
        updated = service.acknowledge_alert(alert.id, "user-123")

        assert updated is not None
        assert updated.status == AlertStatus.ACKNOWLEDGED
        assert updated.acknowledged_by == "user-123"
        assert updated.acknowledged_at is not None

    def test_resolve_alert(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test resolving an alert."""
        alert = service.fire_alert(sample_rule.id, 90.0)
        updated = service.resolve_alert(alert.id)

        assert updated is not None
        assert updated.status == AlertStatus.RESOLVED
        assert updated.resolved_at is not None

    def test_silence_alert(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test silencing an alert."""
        alert = service.fire_alert(sample_rule.id, 90.0)
        silence = service.create_silence(matchers={"service": "api"})

        updated = service.silence_alert(alert.id, silence.id)

        assert updated is not None
        assert updated.status == AlertStatus.SILENCED
        assert updated.silence_id == silence.id


# ============================================================
# Silence Management Tests
# ============================================================


class TestSilenceManagement:
    """Test silence management."""

    def test_create_silence(self, service: AlertingConfigService) -> None:
        """Test creating a silence."""
        silence = service.create_silence(
            matchers={"service": "api"},
            duration_hours=2,
            name="Maintenance",
            comment="Scheduled maintenance",
            created_by="user-123",
        )

        assert silence.matchers["service"] == "api"
        assert silence.name == "Maintenance"
        assert silence.created_by == "user-123"

    def test_create_silence_with_dates(self, service: AlertingConfigService) -> None:
        """Test creating silence with explicit dates."""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=1)
        end = now + timedelta(hours=3)

        silence = service.create_silence(
            matchers={"env": "staging"},
            starts_at=start,
            ends_at=end,
        )

        assert silence.starts_at == start
        assert silence.ends_at == end

    def test_get_silence(self, service: AlertingConfigService) -> None:
        """Test getting a silence."""
        created = service.create_silence(matchers={"test": "true"})
        retrieved = service.get_silence(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_all_silences(self, service: AlertingConfigService) -> None:
        """Test getting all silences."""
        service.create_silence(matchers={"s1": "v1"})
        service.create_silence(matchers={"s2": "v2"})

        silences = service.get_all_silences()
        assert len(silences) >= 2

    def test_get_active_silences(self, service: AlertingConfigService) -> None:
        """Test getting active silences."""
        # Create active silence
        service.create_silence(
            matchers={"active": "true"},
            duration_hours=1,
        )

        # Create expired silence
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        service.create_silence(
            matchers={"expired": "true"},
            starts_at=past,
            ends_at=past + timedelta(hours=1),
        )

        active = service.get_active_silences()
        matchers_list = [s.matchers for s in active]
        assert any("active" in m for m in matchers_list)

    def test_expire_silence(self, service: AlertingConfigService) -> None:
        """Test expiring a silence early."""
        silence = service.create_silence(
            matchers={"test": "true"},
            duration_hours=24,
        )

        updated = service.expire_silence(silence.id)

        assert updated is not None
        assert updated.ends_at <= datetime.now(timezone.utc) + timedelta(seconds=1)

    def test_delete_silence(self, service: AlertingConfigService) -> None:
        """Test deleting a silence."""
        silence = service.create_silence(matchers={"test": "true"})
        result = service.delete_silence(silence.id)

        assert result is True
        assert service.get_silence(silence.id) is None

    def test_alert_fired_while_silenced(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that alert is silenced when matching silence exists."""
        # Create silence matching rule labels
        service.create_silence(matchers={"service": "api"})

        # Fire alert
        alert = service.fire_alert(sample_rule.id, 90.0)

        assert alert.status == AlertStatus.SILENCED
        assert alert.silence_id is not None


# ============================================================
# Alert Grouping Tests
# ============================================================


class TestAlertGrouping:
    """Test alert grouping."""

    def test_get_group_key(self, service: AlertingConfigService) -> None:
        """Test generating group key."""
        labels = {"service": "api", "env": "prod", "instance": "i-123"}
        key = service.get_group_key(labels, ["service", "env"])

        assert key == "env=prod,service=api"

    def test_get_group_key_empty_group_by(
        self, service: AlertingConfigService
    ) -> None:
        """Test group key with no group_by."""
        key = service.get_group_key({"service": "api"}, [])
        assert key == "default"

    def test_group_alerts(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test grouping alerts."""
        # Create multiple alerts with different labels
        alert1 = service.fire_alert(
            sample_rule.id, 90.0,
            labels={"instance": "i-1"},
        )
        # Force new fingerprint by resolving and creating new
        service.resolve_alert(alert1.id)

        alert2 = service.fire_alert(
            sample_rule.id, 95.0,
            labels={"instance": "i-2"},
        )

        alerts = [alert1, alert2]
        groups = service.group_alerts(alerts, ["service"])

        assert len(groups) == 1  # Same service
        assert len(groups[0].alerts) == 2


# ============================================================
# History Tests
# ============================================================


class TestHistory:
    """Test alert history."""

    def test_alert_fired_records_history(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that firing alert records history."""
        alert = service.fire_alert(sample_rule.id, 90.0)
        history = service.get_alert_history(alert.id)

        assert len(history) >= 1
        assert history[0].event == "fired"

    def test_alert_acknowledged_records_history(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that acknowledging records history."""
        alert = service.fire_alert(sample_rule.id, 90.0)
        service.acknowledge_alert(alert.id, "user-123")

        history = service.get_alert_history(alert.id)
        events = [h.event for h in history]

        assert "acknowledged" in events

    def test_alert_resolved_records_history(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test that resolving records history."""
        alert = service.fire_alert(sample_rule.id, 90.0)
        service.resolve_alert(alert.id)

        history = service.get_alert_history(alert.id)
        events = [h.event for h in history]

        assert "resolved" in events

    def test_get_recent_history(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting recent history."""
        for i in range(5):
            alert = service.fire_alert(
                sample_rule.id, 90.0 + i,
                labels={"instance": f"i-{i}"},
            )
            service.resolve_alert(alert.id)

        history = service.get_recent_history(limit=10)
        assert len(history) == 10  # 5 fired + 5 resolved


# ============================================================
# Validation Tests
# ============================================================


class TestValidation:
    """Test validation functionality."""

    def test_validate_valid_rule(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test validating a valid rule."""
        result = service.validate_rule(sample_rule)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_rule_missing_name(self, service: AlertingConfigService) -> None:
        """Test validating rule without name."""
        rule = AlertRule(conditions=[ThresholdCondition(metric="test")])
        result = service.validate_rule(rule)

        assert result["is_valid"] is False
        assert any("name" in e.lower() for e in result["errors"])

    def test_validate_rule_no_conditions(self, service: AlertingConfigService) -> None:
        """Test validating rule without conditions."""
        rule = AlertRule(name="Test")
        result = service.validate_rule(rule)

        assert result["is_valid"] is False
        assert any("condition" in e.lower() for e in result["errors"])

    def test_validate_rule_missing_metric(self, service: AlertingConfigService) -> None:
        """Test validating rule with missing metric."""
        rule = AlertRule(
            name="Test",
            conditions=[ThresholdCondition()],  # No metric
        )
        result = service.validate_rule(rule)

        assert result["is_valid"] is False
        assert any("metric" in e.lower() for e in result["errors"])

    def test_validate_rule_warnings(self, service: AlertingConfigService) -> None:
        """Test validation warnings."""
        rule = AlertRule(
            name="Test",
            conditions=[ThresholdCondition(metric="test")],
            evaluation_interval_seconds=5,  # Too low
        )
        result = service.validate_rule(rule)

        assert len(result["warnings"]) >= 1

    def test_validate_valid_target(
        self,
        service: AlertingConfigService,
        sample_target: NotificationTarget,
    ) -> None:
        """Test validating a valid target."""
        result = service.validate_target(sample_target)
        assert result["is_valid"] is True

    def test_validate_target_invalid_email(
        self, service: AlertingConfigService
    ) -> None:
        """Test validating invalid email target."""
        target = NotificationTarget(
            name="Bad Email",
            channel=NotificationChannel.EMAIL,
            address="not-an-email",
        )
        result = service.validate_target(target)

        assert result["is_valid"] is False
        assert any("email" in e.lower() for e in result["errors"])

    def test_validate_target_invalid_webhook(
        self, service: AlertingConfigService
    ) -> None:
        """Test validating invalid webhook target."""
        target = NotificationTarget(
            name="Bad Webhook",
            channel=NotificationChannel.WEBHOOK,
            address="not-a-url",
        )
        result = service.validate_target(target)

        assert result["is_valid"] is False
        assert any("url" in e.lower() for e in result["errors"])


# ============================================================
# Summary Tests
# ============================================================


class TestSummary:
    """Test summary functionality."""

    def test_get_summary(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test getting summary."""
        service.fire_alert(sample_rule.id, 90.0)

        summary = service.get_summary()

        assert "total_rules" in summary
        assert "active_rules" in summary
        assert "total_alerts" in summary
        assert "firing_alerts" in summary
        assert "total_silences" in summary
        assert "total_targets" in summary
        assert "total_routes" in summary
        assert "alerts_by_severity" in summary
        assert "alerts_by_status" in summary

    def test_summary_counts(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test summary counts are accurate."""
        # Fire and acknowledge an alert
        alert = service.fire_alert(sample_rule.id, 90.0)
        service.acknowledge_alert(alert.id, "user-1")

        # Create a silence
        service.create_silence(matchers={"test": "true"})

        summary = service.get_summary()

        assert summary["total_rules"] >= 7  # 6 default + 1 sample
        assert summary["total_alerts"] >= 1
        assert summary["total_silences"] >= 1


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests."""

    def test_full_alerting_workflow(
        self,
        service: AlertingConfigService,
    ) -> None:
        """Test complete alerting workflow."""
        # Create target
        target = service.create_target(
            name="Team Slack",
            channel=NotificationChannel.SLACK,
            address="#team-alerts",
        )

        # Create route
        route = service.create_route(
            name="Team Route",
            target_ids=[target.id],
            match_labels={"team": "backend"},
            group_by=["service"],
        )

        # Create rule
        rule = service.create_rule(
            name="API Error Rate",
            conditions=[
                ThresholdCondition(
                    metric="error_rate",
                    operator=ComparisonOperator.GREATER_THAN,
                    threshold=1.0,
                )
            ],
            severity=AlertSeverity.HIGH,
            labels={"team": "backend", "service": "api"},
            route_ids=[route.id],
        )

        # Fire alert
        alert = service.fire_alert(
            rule.id,
            value=2.5,
        )

        assert alert is not None
        assert alert.status == AlertStatus.FIRING

        # Get matching routes
        routes = service.get_matching_routes(
            alert.labels,
            alert.severity,
        )
        assert len(routes) >= 1

        # Acknowledge
        service.acknowledge_alert(alert.id, "oncall-engineer")
        assert service.get_alert(alert.id).status == AlertStatus.ACKNOWLEDGED

        # Resolve
        service.resolve_alert(alert.id)
        assert service.get_alert(alert.id).status == AlertStatus.RESOLVED

        # Check history
        history = service.get_alert_history(alert.id)
        assert len(history) == 3  # fired, acknowledged, resolved

    def test_silence_workflow(
        self,
        service: AlertingConfigService,
        sample_rule: AlertRule,
    ) -> None:
        """Test silence workflow."""
        # Create silence for maintenance
        silence = service.create_silence(
            matchers={"service": "api"},
            duration_hours=2,
            name="API Maintenance",
            comment="Scheduled maintenance window",
            created_by="ops-team",
        )

        # Fire alert - should be silenced
        alert = service.fire_alert(sample_rule.id, 95.0)
        assert alert.status == AlertStatus.SILENCED

        # Expire silence
        service.expire_silence(silence.id)

        # New alerts should not be silenced
        # First resolve the existing one
        service.resolve_alert(alert.id)

        # Fire new alert with different fingerprint
        alert2 = service.fire_alert(
            sample_rule.id,
            value=96.0,
            labels={"instance": "new-instance"},
        )
        assert alert2.status == AlertStatus.FIRING

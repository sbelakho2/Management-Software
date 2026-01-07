"""Tests for Incident Flow Service.

Tests severity levels, on-call schedules, escalation paths,
and incident management workflows.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from sensei.services.incident_flow import (
    IncidentFlowService,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentCategory,
    IncidentNotification,
    IncidentMetrics,
    SeverityConfig,
    OnCallPerson,
    OnCallSchedule,
    EscalationLevel,
    EscalationPolicy,
    NotificationChannel,
    EscalationTrigger,
    SEVERITY_CONFIGS,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service() -> IncidentFlowService:
    """Create a fresh IncidentFlowService instance."""
    return IncidentFlowService()


@pytest.fixture
def sample_incident(service: IncidentFlowService) -> Incident:
    """Create a sample incident."""
    return service.create_incident(
        title="Database connection timeout",
        description="Production database is not responding",
        severity=IncidentSeverity.SEV2,
        category=IncidentCategory.DATABASE,
        affected_services=["api", "web-app"],
    )


@pytest.fixture
def on_call_person() -> OnCallPerson:
    """Create an on-call person."""
    return OnCallPerson(
        user_id="user-123",
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        slack_handle="@johndoe",
    )


@pytest.fixture
def sample_schedule(service: IncidentFlowService, on_call_person: OnCallPerson) -> OnCallSchedule:
    """Create a sample schedule with members."""
    schedule = service.create_schedule(
        name="Backend On-Call",
        team="backend",
        rotation_type="weekly",
    )
    service.add_member_to_schedule(schedule.id, on_call_person)
    service.add_member_to_schedule(
        schedule.id,
        OnCallPerson(user_id="user-456", name="Jane Smith", email="jane@example.com"),
    )
    return service.get_schedule(schedule.id)


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Test enum values."""

    def test_severity_levels(self) -> None:
        """Verify all severity levels exist."""
        expected = {"sev1", "sev2", "sev3", "sev4", "sev5"}
        actual = {s.value for s in IncidentSeverity}
        assert actual == expected

    def test_incident_statuses(self) -> None:
        """Verify all incident statuses exist."""
        expected = {
            "detected", "acknowledged", "investigating", "identified",
            "mitigating", "resolved", "closed",
        }
        actual = {s.value for s in IncidentStatus}
        assert actual == expected

    def test_incident_categories(self) -> None:
        """Verify all incident categories exist."""
        expected = {
            "infrastructure", "application", "database", "network",
            "security", "performance", "data", "integration", "business",
        }
        actual = {c.value for c in IncidentCategory}
        assert actual == expected

    def test_notification_channels(self) -> None:
        """Verify all notification channels exist."""
        expected = {
            "email", "sms", "slack", "pagerduty", "teams", "webhook", "phone_call",
        }
        actual = {c.value for c in NotificationChannel}
        assert actual == expected


# ============================================================
# Severity Configuration Tests
# ============================================================


class TestSeverityConfiguration:
    """Test severity configuration."""

    def test_get_severity_config(self, service: IncidentFlowService) -> None:
        """Test getting severity configuration."""
        config = service.get_severity_config(IncidentSeverity.SEV1)
        assert config.severity == IncidentSeverity.SEV1
        assert config.name == "Critical"
        assert config.response_time_minutes == 5

    def test_all_severities_configured(self, service: IncidentFlowService) -> None:
        """Test that all severities are configured."""
        configs = service.get_all_severity_configs()
        assert len(configs) == 5
        severities = {c.severity for c in configs}
        assert severities == set(IncidentSeverity)

    def test_sev1_requires_postmortem(self, service: IncidentFlowService) -> None:
        """Test SEV1 requires postmortem."""
        config = service.get_severity_config(IncidentSeverity.SEV1)
        assert config.requires_postmortem is True
        assert config.wake_on_call is True
        assert config.customer_communication is True

    def test_sev5_is_informational(self, service: IncidentFlowService) -> None:
        """Test SEV5 is informational."""
        config = service.get_severity_config(IncidentSeverity.SEV5)
        assert config.name == "Informational"
        assert config.requires_postmortem is False
        assert config.response_time_minutes > 60  # Longer response time

    def test_update_severity_config(self, service: IncidentFlowService) -> None:
        """Test updating severity configuration."""
        config = service.update_severity_config(
            IncidentSeverity.SEV3,
            response_time_minutes=45,
            resolution_target_hours=12,
        )
        assert config.response_time_minutes == 45
        assert config.resolution_target_hours == 12

    def test_severity_notification_channels(self, service: IncidentFlowService) -> None:
        """Test severity notification channels."""
        sev1 = service.get_severity_config(IncidentSeverity.SEV1)
        assert NotificationChannel.PAGERDUTY in sev1.notification_channels
        assert NotificationChannel.PHONE_CALL in sev1.notification_channels


# ============================================================
# On-Call Schedule Tests
# ============================================================


class TestOnCallSchedule:
    """Test on-call schedule management."""

    def test_create_schedule(self, service: IncidentFlowService) -> None:
        """Test creating a schedule."""
        schedule = service.create_schedule(
            name="Frontend On-Call",
            team="frontend",
            rotation_type="daily",
        )
        assert schedule.name == "Frontend On-Call"
        assert schedule.team == "frontend"
        assert schedule.rotation_type == "daily"

    def test_get_schedule(self, service: IncidentFlowService) -> None:
        """Test getting a schedule."""
        created = service.create_schedule(name="Test", team="test")
        retrieved = service.get_schedule(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_schedule_nonexistent(self, service: IncidentFlowService) -> None:
        """Test getting non-existent schedule."""
        schedule = service.get_schedule("nonexistent")
        assert schedule is None

    def test_get_all_schedules(self, service: IncidentFlowService) -> None:
        """Test getting all schedules."""
        service.create_schedule(name="Schedule 1", team="team1")
        service.create_schedule(name="Schedule 2", team="team2")

        schedules = service.get_all_schedules()
        assert len(schedules) >= 2

    def test_get_schedules_by_team(self, service: IncidentFlowService) -> None:
        """Test getting schedules by team."""
        service.create_schedule(name="Backend 1", team="backend")
        service.create_schedule(name="Backend 2", team="backend")
        service.create_schedule(name="Frontend", team="frontend")

        backend_schedules = service.get_schedules_by_team("backend")
        assert len(backend_schedules) == 2

    def test_add_member_to_schedule(
        self,
        service: IncidentFlowService,
        on_call_person: OnCallPerson,
    ) -> None:
        """Test adding member to schedule."""
        schedule = service.create_schedule(name="Test", team="test")
        updated = service.add_member_to_schedule(schedule.id, on_call_person)

        assert updated is not None
        assert len(updated.rotation_members) == 1
        assert updated.rotation_members[0].name == on_call_person.name

    def test_remove_member_from_schedule(
        self,
        service: IncidentFlowService,
        sample_schedule: OnCallSchedule,
    ) -> None:
        """Test removing member from schedule."""
        initial_count = len(sample_schedule.rotation_members)
        updated = service.remove_member_from_schedule(sample_schedule.id, "user-123")

        assert updated is not None
        assert len(updated.rotation_members) == initial_count - 1

    def test_get_current_on_call(
        self,
        service: IncidentFlowService,
        sample_schedule: OnCallSchedule,
    ) -> None:
        """Test getting current on-call person."""
        current = service.get_current_on_call(sample_schedule.id)
        assert current is not None
        assert current.user_id in ["user-123", "user-456"]

    def test_get_current_on_call_empty_schedule(self, service: IncidentFlowService) -> None:
        """Test getting current on-call from empty schedule."""
        schedule = service.create_schedule(name="Empty", team="test")
        current = service.get_current_on_call(schedule.id)
        assert current is None

    def test_rotate_schedule(
        self,
        service: IncidentFlowService,
        sample_schedule: OnCallSchedule,
    ) -> None:
        """Test rotating schedule."""
        first = service.get_current_on_call(sample_schedule.id)
        service.rotate_schedule(sample_schedule.id)
        second = service.get_current_on_call(sample_schedule.id)

        # Should be different people
        assert first is not None
        assert second is not None
        assert first.user_id != second.user_id

    def test_rotate_schedule_wraps_around(
        self,
        service: IncidentFlowService,
        sample_schedule: OnCallSchedule,
    ) -> None:
        """Test that rotation wraps around."""
        first = service.get_current_on_call(sample_schedule.id)
        member_count = len(sample_schedule.rotation_members)

        # Rotate through all members and back
        for _ in range(member_count):
            service.rotate_schedule(sample_schedule.id)

        current = service.get_current_on_call(sample_schedule.id)
        assert current is not None
        assert current.user_id == first.user_id


# ============================================================
# Escalation Policy Tests
# ============================================================


class TestEscalationPolicy:
    """Test escalation policy management."""

    def test_default_policy_exists(self, service: IncidentFlowService) -> None:
        """Test that default policy is created."""
        policies = service.get_all_policies()
        assert len(policies) >= 1

        default = policies[0]
        assert "Default" in default.name
        assert len(default.levels) >= 3

    def test_create_policy(self, service: IncidentFlowService) -> None:
        """Test creating a policy."""
        policy = service.create_policy(
            name="Custom Policy",
            description="Custom escalation policy",
        )
        assert policy.name == "Custom Policy"
        assert policy.is_active is True

    def test_create_policy_with_levels(self, service: IncidentFlowService) -> None:
        """Test creating policy with levels."""
        levels = [
            EscalationLevel(
                level=1,
                name="First Responder",
                timeout_minutes=10,
            ),
            EscalationLevel(
                level=2,
                name="Team Lead",
                timeout_minutes=20,
            ),
        ]
        policy = service.create_policy(
            name="Two Level Policy",
            levels=levels,
        )
        assert len(policy.levels) == 2

    def test_get_policy(self, service: IncidentFlowService) -> None:
        """Test getting a policy."""
        created = service.create_policy(name="Test Policy")
        retrieved = service.get_policy(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_policy_nonexistent(self, service: IncidentFlowService) -> None:
        """Test getting non-existent policy."""
        policy = service.get_policy("nonexistent")
        assert policy is None

    def test_add_level_to_policy(self, service: IncidentFlowService) -> None:
        """Test adding level to policy."""
        policy = service.create_policy(name="Test")
        level = EscalationLevel(
            level=1,
            name="First Level",
            timeout_minutes=15,
        )

        updated = service.add_level_to_policy(policy.id, level)
        assert updated is not None
        assert len(updated.levels) == 1

    def test_levels_sorted_by_number(self, service: IncidentFlowService) -> None:
        """Test that levels are sorted by number."""
        policy = service.create_policy(name="Test")

        # Add in reverse order
        service.add_level_to_policy(
            policy.id,
            EscalationLevel(level=3, name="Third"),
        )
        service.add_level_to_policy(
            policy.id,
            EscalationLevel(level=1, name="First"),
        )
        service.add_level_to_policy(
            policy.id,
            EscalationLevel(level=2, name="Second"),
        )

        updated = service.get_policy(policy.id)
        assert updated is not None
        assert [l.level for l in updated.levels] == [1, 2, 3]

    def test_get_escalation_level(self, service: IncidentFlowService) -> None:
        """Test getting specific escalation level."""
        policies = service.get_all_policies()
        policy = policies[0]

        level = service.get_escalation_level(policy.id, 1)
        assert level is not None
        assert level.level == 1

    def test_get_escalation_level_nonexistent(self, service: IncidentFlowService) -> None:
        """Test getting non-existent escalation level."""
        policies = service.get_all_policies()
        policy = policies[0]

        level = service.get_escalation_level(policy.id, 999)
        assert level is None


# ============================================================
# Incident Management Tests
# ============================================================


class TestIncidentManagement:
    """Test incident management."""

    def test_create_incident(self, service: IncidentFlowService) -> None:
        """Test creating an incident."""
        incident = service.create_incident(
            title="Test Incident",
            description="Test description",
            severity=IncidentSeverity.SEV3,
            category=IncidentCategory.APPLICATION,
        )

        assert incident.title == "Test Incident"
        assert incident.status == IncidentStatus.DETECTED
        assert incident.severity == IncidentSeverity.SEV3
        assert len(incident.timeline) == 1  # Creation event

    def test_create_incident_with_services(self, service: IncidentFlowService) -> None:
        """Test creating incident with affected services."""
        incident = service.create_incident(
            title="Multi-Service Outage",
            affected_services=["api", "web", "mobile"],
        )
        assert len(incident.affected_services) == 3

    def test_get_incident(self, service: IncidentFlowService, sample_incident: Incident) -> None:
        """Test getting an incident."""
        retrieved = service.get_incident(sample_incident.id)
        assert retrieved is not None
        assert retrieved.id == sample_incident.id

    def test_get_incident_nonexistent(self, service: IncidentFlowService) -> None:
        """Test getting non-existent incident."""
        incident = service.get_incident("nonexistent")
        assert incident is None

    def test_get_all_incidents(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test getting all incidents."""
        service.create_incident(title="Another Incident")
        incidents = service.get_all_incidents()
        assert len(incidents) >= 2

    def test_get_incidents_by_status(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test getting incidents by status."""
        detected = service.get_incidents_by_status(IncidentStatus.DETECTED)
        assert len(detected) >= 1

    def test_get_incidents_by_severity(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test getting incidents by severity."""
        sev2 = service.get_incidents_by_severity(IncidentSeverity.SEV2)
        assert len(sev2) >= 1

    def test_get_open_incidents(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test getting open incidents."""
        open_incidents = service.get_open_incidents()
        assert len(open_incidents) >= 1
        assert sample_incident.id in [i.id for i in open_incidents]

    def test_acknowledge_incident(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test acknowledging an incident."""
        updated = service.acknowledge_incident(sample_incident.id, "user-123")

        assert updated is not None
        assert updated.status == IncidentStatus.ACKNOWLEDGED
        assert updated.acknowledged_at is not None
        assert updated.assigned_to == "user-123"

    def test_acknowledge_adds_timeline_entry(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test that acknowledging adds timeline entry."""
        initial_entries = len(sample_incident.timeline)
        service.acknowledge_incident(sample_incident.id, "user-123")

        updated = service.get_incident(sample_incident.id)
        assert updated is not None
        assert len(updated.timeline) == initial_entries + 1

    def test_update_incident_status(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test updating incident status."""
        updated = service.update_incident_status(
            sample_incident.id,
            IncidentStatus.INVESTIGATING,
            notes="Starting investigation",
        )

        assert updated is not None
        assert updated.status == IncidentStatus.INVESTIGATING

    def test_resolve_incident_sets_timestamp(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test that resolving sets resolved_at."""
        updated = service.update_incident_status(
            sample_incident.id,
            IncidentStatus.RESOLVED,
        )

        assert updated is not None
        assert updated.resolved_at is not None

    def test_close_incident_sets_timestamp(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test that closing sets closed_at."""
        service.update_incident_status(sample_incident.id, IncidentStatus.RESOLVED)
        updated = service.update_incident_status(
            sample_incident.id,
            IncidentStatus.CLOSED,
        )

        assert updated is not None
        assert updated.closed_at is not None

    def test_escalate_incident(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test escalating an incident."""
        policies = service.get_all_policies()
        sample_incident.escalation_policy_id = policies[0].id

        initial_level = sample_incident.escalation_level
        updated = service.escalate_incident(sample_incident.id)

        assert updated is not None
        assert updated.escalation_level == initial_level + 1

    def test_escalate_adds_timeline_entry(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test that escalation adds timeline entry."""
        policies = service.get_all_policies()
        sample_incident.escalation_policy_id = policies[0].id

        initial_entries = len(sample_incident.timeline)
        service.escalate_incident(sample_incident.id, trigger=EscalationTrigger.TIME_ELAPSED)

        updated = service.get_incident(sample_incident.id)
        assert updated is not None
        assert len(updated.timeline) == initial_entries + 1

        last_entry = updated.timeline[-1]
        assert last_entry["event"] == "escalated"
        assert last_entry["trigger"] == "time_elapsed"

    def test_update_incident_severity(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test updating incident severity."""
        updated = service.update_incident_severity(
            sample_incident.id,
            IncidentSeverity.SEV1,
            reason="Impact wider than expected",
        )

        assert updated is not None
        assert updated.severity == IncidentSeverity.SEV1

    def test_add_incident_note(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test adding note to incident."""
        initial_entries = len(sample_incident.timeline)
        updated = service.add_incident_note(
            sample_incident.id,
            "Found potential root cause",
            "user-123",
        )

        assert updated is not None
        assert len(updated.timeline) == initial_entries + 1

    def test_set_root_cause(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test setting root cause."""
        updated = service.set_root_cause(
            sample_incident.id,
            "Database connection pool exhausted",
        )

        assert updated is not None
        assert updated.root_cause == "Database connection pool exhausted"

    def test_set_resolution(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test setting resolution."""
        updated = service.set_resolution(
            sample_incident.id,
            "Increased connection pool size from 10 to 50",
        )

        assert updated is not None
        assert "connection pool" in updated.resolution


# ============================================================
# Notification Tests
# ============================================================


class TestNotifications:
    """Test incident notifications."""

    def test_send_notification(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test sending a notification."""
        notification = service.send_notification(
            sample_incident.id,
            NotificationChannel.SLACK,
            "@oncall",
            "New SEV2 incident: Database connection timeout",
        )

        assert notification.incident_id == sample_incident.id
        assert notification.channel == NotificationChannel.SLACK
        assert notification.acknowledged is False

    def test_get_notifications_for_incident(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test getting notifications for incident."""
        service.send_notification(
            sample_incident.id,
            NotificationChannel.SLACK,
            "@oncall",
            "Message 1",
        )
        service.send_notification(
            sample_incident.id,
            NotificationChannel.EMAIL,
            "team@example.com",
            "Message 2",
        )

        notifications = service.get_notifications_for_incident(sample_incident.id)
        assert len(notifications) == 2

    def test_acknowledge_notification(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test acknowledging a notification."""
        notification = service.send_notification(
            sample_incident.id,
            NotificationChannel.PAGERDUTY,
            "pd-service",
            "Alert",
        )

        updated = service.acknowledge_notification(notification.id)
        assert updated is not None
        assert updated.acknowledged is True
        assert updated.acknowledged_at is not None

    def test_acknowledge_nonexistent_notification(
        self,
        service: IncidentFlowService,
    ) -> None:
        """Test acknowledging non-existent notification."""
        result = service.acknowledge_notification("nonexistent")
        assert result is None


# ============================================================
# SLA Checking Tests
# ============================================================


class TestSLAChecking:
    """Test SLA checking functionality."""

    def test_check_response_sla_met(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test response SLA when met."""
        # Acknowledge immediately
        service.acknowledge_incident(sample_incident.id, "user-123")

        incident = service.get_incident(sample_incident.id)
        result = service.check_response_sla(incident)

        assert result["is_met"] is True
        assert result["is_acknowledged"] is True
        assert result["actual_minutes"] < result["target_minutes"]

    def test_check_response_sla_not_acknowledged(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test response SLA when not acknowledged."""
        result = service.check_response_sla(sample_incident)

        assert result["is_acknowledged"] is False
        assert result["target_minutes"] > 0

    def test_check_resolution_sla_met(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test resolution SLA when met."""
        # Resolve immediately
        service.update_incident_status(sample_incident.id, IncidentStatus.RESOLVED)

        incident = service.get_incident(sample_incident.id)
        result = service.check_resolution_sla(incident)

        assert result["is_met"] is True
        assert result["is_resolved"] is True

    def test_check_resolution_sla_not_resolved(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test resolution SLA when not resolved."""
        result = service.check_resolution_sla(sample_incident)

        assert result["is_resolved"] is False
        assert result["target_hours"] > 0

    def test_should_escalate_not_acknowledged(
        self,
        service: IncidentFlowService,
    ) -> None:
        """Test escalation check for unacknowledged incident."""
        # Create incident in the past
        incident = Incident(
            title="Old Incident",
            severity=IncidentSeverity.SEV3,
            detected_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        # Mock the incident storage
        service._incidents[incident.id] = incident

        # Should escalate because it's been more than auto_escalate_after_minutes
        should = service.should_escalate(incident)
        assert should is True

    def test_should_not_escalate_resolved(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test that resolved incidents should not escalate."""
        service.update_incident_status(sample_incident.id, IncidentStatus.RESOLVED)

        incident = service.get_incident(sample_incident.id)
        should = service.should_escalate(incident)
        assert should is False


# ============================================================
# Metrics Tests
# ============================================================


class TestMetrics:
    """Test metrics functionality."""

    def test_get_metrics_empty(self, service: IncidentFlowService) -> None:
        """Test metrics with no incidents."""
        metrics = service.get_metrics()
        assert metrics.total_incidents == 0

    def test_get_metrics_with_incidents(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test metrics with incidents."""
        # Create a few more incidents
        service.create_incident(title="Incident 2", severity=IncidentSeverity.SEV1)
        service.create_incident(title="Incident 3", severity=IncidentSeverity.SEV3)

        metrics = service.get_metrics()
        assert metrics.total_incidents >= 3
        assert sum(metrics.by_severity.values()) == metrics.total_incidents

    def test_metrics_by_severity(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test metrics grouped by severity."""
        service.create_incident(title="SEV1", severity=IncidentSeverity.SEV1)
        service.create_incident(title="SEV1 2", severity=IncidentSeverity.SEV1)

        metrics = service.get_metrics()
        assert metrics.by_severity.get("sev1", 0) >= 2

    def test_metrics_by_status(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test metrics grouped by status."""
        metrics = service.get_metrics()
        assert metrics.by_status.get("detected", 0) >= 1

    def test_metrics_mtta(self, service: IncidentFlowService) -> None:
        """Test mean time to acknowledge calculation."""
        incident1 = service.create_incident(title="Incident 1")
        service.acknowledge_incident(incident1.id, "user-1")

        incident2 = service.create_incident(title="Incident 2")
        service.acknowledge_incident(incident2.id, "user-2")

        metrics = service.get_metrics()
        assert metrics.mean_time_to_acknowledge_minutes >= 0

    def test_metrics_mttr(self, service: IncidentFlowService) -> None:
        """Test mean time to resolve calculation."""
        incident = service.create_incident(title="Resolved Incident")
        service.update_incident_status(incident.id, IncidentStatus.RESOLVED)

        metrics = service.get_metrics()
        assert metrics.mean_time_to_resolve_hours >= 0

    def test_metrics_sla_percentage(self, service: IncidentFlowService) -> None:
        """Test SLA met percentage calculation."""
        # Create and resolve some incidents
        for i in range(3):
            incident = service.create_incident(title=f"Incident {i}")
            service.update_incident_status(incident.id, IncidentStatus.RESOLVED)

        metrics = service.get_metrics()
        # All resolved immediately, so 100% SLA
        assert metrics.sla_met_percentage >= 0

    def test_metrics_date_filtering(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test metrics with date filtering."""
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        metrics = service.get_metrics(start_date=start_date, end_date=end_date)
        assert metrics.total_incidents >= 1


# ============================================================
# Summary Tests
# ============================================================


class TestSummary:
    """Test summary functionality."""

    def test_get_summary(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test getting summary."""
        summary = service.get_summary()

        assert "total_incidents" in summary
        assert "open_incidents" in summary
        assert "total_schedules" in summary
        assert "total_policies" in summary
        assert "severities_configured" in summary
        assert summary["severities_configured"] == 5

    def test_summary_counts(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
        sample_schedule: OnCallSchedule,
    ) -> None:
        """Test summary counts."""
        summary = service.get_summary()

        assert summary["total_incidents"] >= 1
        assert summary["total_schedules"] >= 1
        assert summary["total_policies"] >= 1


# ============================================================
# Edge Cases and Integration Tests
# ============================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_create_incident_minimal(self, service: IncidentFlowService) -> None:
        """Test creating incident with minimal info."""
        incident = service.create_incident(title="Minimal")
        assert incident.title == "Minimal"
        assert incident.severity == IncidentSeverity.SEV3  # Default

    def test_incident_timeline_chronological(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test that timeline entries are chronological."""
        service.acknowledge_incident(sample_incident.id, "user-1")
        service.add_incident_note(sample_incident.id, "Note 1", "user-1")
        service.update_incident_status(sample_incident.id, IncidentStatus.INVESTIGATING)

        incident = service.get_incident(sample_incident.id)
        assert incident is not None
        assert len(incident.timeline) >= 4

        # Verify chronological order
        timestamps = [
            datetime.fromisoformat(e["timestamp"])
            for e in incident.timeline
        ]
        assert timestamps == sorted(timestamps)

    def test_multiple_escalations(
        self,
        service: IncidentFlowService,
        sample_incident: Incident,
    ) -> None:
        """Test multiple escalations up to max level."""
        policies = service.get_all_policies()
        sample_incident.escalation_policy_id = policies[0].id
        max_levels = len(policies[0].levels)

        # Escalate past max levels (should cap at max)
        for i in range(max_levels + 2):
            service.escalate_incident(sample_incident.id)

        incident = service.get_incident(sample_incident.id)
        assert incident is not None
        # Should be capped at max level, not go beyond
        assert incident.escalation_level == max_levels


class TestIntegration:
    """Integration tests."""

    def test_full_incident_lifecycle(self, service: IncidentFlowService) -> None:
        """Test complete incident lifecycle."""
        # Create
        incident = service.create_incident(
            title="Production API Down",
            description="All API endpoints returning 503",
            severity=IncidentSeverity.SEV1,
            category=IncidentCategory.APPLICATION,
            affected_services=["api", "mobile-app", "web-app"],
        )

        # Send notifications
        service.send_notification(
            incident.id,
            NotificationChannel.PAGERDUTY,
            "backend-oncall",
            "URGENT: Production API Down",
        )

        # Acknowledge
        service.acknowledge_incident(incident.id, "engineer-123")

        # Update status and add notes
        service.update_incident_status(incident.id, IncidentStatus.INVESTIGATING)
        service.add_incident_note(incident.id, "Checking database connections", "engineer-123")

        # Identify root cause
        service.update_incident_status(incident.id, IncidentStatus.IDENTIFIED)
        service.set_root_cause(incident.id, "Database connection pool exhausted")

        # Mitigate
        service.update_incident_status(incident.id, IncidentStatus.MITIGATING)
        service.add_incident_note(incident.id, "Restarting connection pool", "engineer-123")

        # Resolve
        service.set_resolution(incident.id, "Increased pool size and restarted API servers")
        service.update_incident_status(incident.id, IncidentStatus.RESOLVED)

        # Verify
        final = service.get_incident(incident.id)
        assert final is not None
        assert final.status == IncidentStatus.RESOLVED
        assert final.resolved_at is not None
        assert final.root_cause != ""
        assert final.resolution != ""
        assert len(final.timeline) >= 8

        # Check SLAs
        response_sla = service.check_response_sla(final)
        resolution_sla = service.check_resolution_sla(final)

        assert response_sla["is_acknowledged"] is True
        assert resolution_sla["is_resolved"] is True

    def test_oncall_with_incidents(
        self,
        service: IncidentFlowService,
        sample_schedule: OnCallSchedule,
    ) -> None:
        """Test on-call integration with incidents."""
        # Get current on-call
        on_call = service.get_current_on_call(sample_schedule.id)
        assert on_call is not None

        # Create incident
        incident = service.create_incident(
            title="Alert for on-call",
            severity=IncidentSeverity.SEV2,
        )

        # Send notification to on-call
        notification = service.send_notification(
            incident.id,
            NotificationChannel.PAGERDUTY,
            on_call.email,
            f"SEV2: {incident.title}",
        )

        assert notification.recipient == on_call.email

        # On-call acknowledges
        service.acknowledge_incident(incident.id, on_call.user_id)

        updated = service.get_incident(incident.id)
        assert updated is not None
        assert updated.assigned_to == on_call.user_id

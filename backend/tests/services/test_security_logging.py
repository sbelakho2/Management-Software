"""Tests for Security Logging & Audit service."""

from __future__ import annotations

from datetime import timedelta, timezone, datetime
from uuid import uuid4

import pytest

from sensei.services.security_logging import (
    AlertStatus,
    EventCategory,
    EventSeverity,
    SecurityEvent,
    SecurityLoggingService,
    ThreatAlert,
)


@pytest.fixture
def svc() -> SecurityLoggingService:
    return SecurityLoggingService()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ADMIN_ROLES = ("admin",)
SECOPS_ROLES = ("secops",)
VIEWER_ROLES = ("viewer",)


class TestSecurityEvents:
    def test_log_and_list_events(self, svc: SecurityLoggingService) -> None:
        event = svc.log_event(
            category=EventCategory.AUTH_SUCCESS,
            severity=EventSeverity.INFO,
            description="User logged in",
            user_id=uuid4(),
        )

        assert isinstance(event, SecurityEvent)

        events = svc.list_events(actor_roles=ADMIN_ROLES)
        assert len(events) == 1

    def test_filter_by_category_and_severity(self, svc: SecurityLoggingService) -> None:
        svc.log_event(
            category=EventCategory.AUTH_SUCCESS,
            severity=EventSeverity.INFO,
            description="Login",
        )
        svc.log_event(
            category=EventCategory.AUTH_FAILURE,
            severity=EventSeverity.MEDIUM,
            description="Failed login",
        )
        svc.log_event(
            category=EventCategory.PRIVILEGE_ESCALATION,
            severity=EventSeverity.CRITICAL,
            description="Privilege escalation detected",
        )

        auth_fail = svc.list_events(
            actor_roles=ADMIN_ROLES, category=EventCategory.AUTH_FAILURE
        )
        assert len(auth_fail) == 1

        critical = svc.list_events(actor_roles=ADMIN_ROLES, severity=EventSeverity.CRITICAL)
        assert len(critical) == 1

    def test_event_counts_by_severity(self, svc: SecurityLoggingService) -> None:
        svc.log_event(
            category=EventCategory.SYSTEM,
            severity=EventSeverity.INFO,
            description="System start",
        )
        svc.log_event(
            category=EventCategory.NETWORK,
            severity=EventSeverity.HIGH,
            description="Suspicious traffic",
        )
        svc.log_event(
            category=EventCategory.DATA_ACCESS,
            severity=EventSeverity.HIGH,
            description="Bulk data export",
        )

        counts = svc.get_event_counts_by_severity(actor_roles=SECOPS_ROLES)
        assert counts["info"] == 1
        assert counts["high"] == 2

    def test_view_requires_role(self, svc: SecurityLoggingService) -> None:
        svc.log_event(
            category=EventCategory.AUTH_SUCCESS,
            severity=EventSeverity.INFO,
            description="Test",
        )

        with pytest.raises(PermissionError):
            svc.list_events(actor_roles=VIEWER_ROLES)


class TestThreatDetection:
    def test_brute_force_detection(self, svc: SecurityLoggingService) -> None:
        user_id = uuid4()

        # Log 5 auth failures quickly.
        for i in range(5):
            svc.log_event(
                category=EventCategory.AUTH_FAILURE,
                severity=EventSeverity.MEDIUM,
                description=f"Failed login attempt {i + 1}",
                user_id=user_id,
            )

        alerts = svc.list_alerts(actor_roles=ADMIN_ROLES, status=AlertStatus.OPEN)
        assert len(alerts) >= 1
        assert alerts[0].title == "Possible brute-force attack"

    def test_alert_status_update(self, svc: SecurityLoggingService) -> None:
        user_id = uuid4()
        for _ in range(5):
            svc.log_event(
                category=EventCategory.AUTH_FAILURE,
                severity=EventSeverity.MEDIUM,
                description="Failed",
                user_id=user_id,
            )

        alerts = svc.list_alerts(actor_roles=ADMIN_ROLES)
        assert len(alerts) == 1

        updated = svc.update_alert_status(
            alerts[0].id, status=AlertStatus.INVESTIGATING, actor_roles=ADMIN_ROLES
        )
        assert updated.status == AlertStatus.INVESTIGATING

    def test_risk_score_weighted(self, svc: SecurityLoggingService) -> None:
        # No events = 0 score.
        score0 = svc.compute_risk_score(actor_roles=ADMIN_ROLES)
        assert score0 == 0.0

        # Critical event bumps score.
        svc.log_event(
            category=EventCategory.PRIVILEGE_ESCALATION,
            severity=EventSeverity.CRITICAL,
            description="Escalation",
        )
        score1 = svc.compute_risk_score(actor_roles=ADMIN_ROLES)
        assert score1 > 0.0

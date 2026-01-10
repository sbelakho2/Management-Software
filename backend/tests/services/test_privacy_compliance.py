from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.privacy_compliance import (
    PrivacyComplianceService,
    AttendanceEventType,
    DataCategory,
)


def test_attendance_self_view_allowed() -> None:
    svc = PrivacyComplianceService()
    emp = uuid4()

    ev = svc.record_attendance(
        employee_id=emp,
        event_type=AttendanceEventType.CLOCK_IN,
        source="badge_reader",
        timestamp=datetime.now(timezone.utc),
    )

    # Self can view own attendance.
    rows = svc.list_attendance(
        employee_id=emp,
        actor_roles={"operator"},
        actor_employee_id=emp,
    )
    assert [r.id for r in rows] == [ev.id]


def test_attendance_peer_view_denied() -> None:
    svc = PrivacyComplianceService()
    emp = uuid4()
    other = uuid4()

    svc.record_attendance(
        employee_id=emp,
        event_type=AttendanceEventType.CLOCK_OUT,
        source="terminal",
    )

    with pytest.raises(PermissionError):
        svc.list_attendance(
            employee_id=emp,
            actor_roles={"operator"},
            actor_employee_id=other,
        )


def test_performance_masking_for_peers() -> None:
    svc = PrivacyComplianceService()
    emp = uuid4()
    peer = uuid4()

    svc.store_performance_metrics(
        emp,
        {"oee": 0.85, "_rank_department": 3},
    )

    # HR can see full data.
    full = svc.get_performance_metrics(emp, actor_roles={"hr"}, actor_employee_id=None)
    assert "_rank_department" in full

    # Self limited (no rank).
    limited = svc.get_performance_metrics(emp, actor_roles={"viewer"}, actor_employee_id=emp)
    assert "oee" in limited
    assert "_rank_department" not in limited

    # Peer gets masked.
    masked = svc.get_performance_metrics(emp, actor_roles={"viewer"}, actor_employee_id=peer)
    assert masked == {"masked": True}


def test_retention_policy_crud_and_cleanup() -> None:
    svc = PrivacyComplianceService()
    hr_user = uuid4()
    emp = uuid4()

    policy = svc.create_retention_policy(
        category=DataCategory.ATTENDANCE,
        retention_days=30,
        description="Attendance logs retained for 30 days",
        actor_user_id=hr_user,
        actor_roles={"hr"},
    )
    assert policy.retention_days == 30

    # Record old attendance.
    old_ts = datetime.now(timezone.utc) - timedelta(days=60)
    svc.record_attendance(
        employee_id=emp,
        event_type=AttendanceEventType.CLOCK_IN,
        source="badge",
        timestamp=old_ts,
    )
    svc.record_attendance(
        employee_id=emp,
        event_type=AttendanceEventType.CLOCK_OUT,
        source="badge",
        timestamp=datetime.now(timezone.utc),
    )

    runs = svc.run_retention_cleanup(as_of=date.today(), actor_roles={"admin"})
    assert len(runs) == 1
    assert runs[0].records_deleted == 1

    remaining = svc.list_attendance(
        employee_id=emp,
        actor_roles={"hr"},
        actor_employee_id=None,
    )
    assert len(remaining) == 1


def test_retention_write_requires_role() -> None:
    svc = PrivacyComplianceService()

    with pytest.raises(PermissionError):
        svc.create_retention_policy(
            category=DataCategory.PERSONAL,
            retention_days=365,
            description="Test",
            actor_user_id=uuid4(),
            actor_roles={"supervisor"},
        )

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from sensei.services.hr.staffing_roster import (
    StaffingRosterService,
    ShiftType,
    AbsenceType,
    AbsenceStatus,
    RiskSeverity,
)


def test_shift_and_roster_requires_write_role() -> None:
    svc = StaffingRosterService()
    with pytest.raises(PermissionError):
        svc.create_shift(
            name="Morning",
            shift_type=ShiftType.MORNING,
            start_time="06:00",
            end_time="14:00",
            actor_roles={"viewer"},
        )

    shift = svc.create_shift(
        name="Morning",
        shift_type=ShiftType.MORNING,
        start_time="06:00",
        end_time="14:00",
        actor_roles={"supervisor"},
    )

    with pytest.raises(PermissionError):
        svc.assign_slot(
            shift_id=shift.id,
            roster_date=date(2026, 1, 10),
            employee_id=uuid4(),
            actor_user_id=uuid4(),
            actor_roles={"viewer"},
        )


def test_absence_approval_flow() -> None:
    svc = StaffingRosterService()
    emp = uuid4()
    hr_user = uuid4()

    absence = svc.record_absence(
        employee_id=emp,
        absence_type=AbsenceType.VACATION,
        start_date=date(2026, 1, 15),
        end_date=date(2026, 1, 20),
        actor_user_id=hr_user,
        actor_roles={"hr"},
        reason="Family trip",
    )
    assert absence.status == AbsenceStatus.REQUESTED

    approved = svc.decide_absence(
        absence.id,
        approved=True,
        actor_user_id=hr_user,
        actor_roles={"gm"},
    )
    assert approved.status == AbsenceStatus.APPROVED

    # Approved absence visible on get_absent_employees_on
    absent = svc.get_absent_employees_on(on_date=date(2026, 1, 17))
    assert emp in absent


def test_skill_coverage_risk_single_point_of_failure() -> None:
    svc = StaffingRosterService()
    emp1, emp2 = uuid4(), uuid4()
    supervisor_user = uuid4()

    shift = svc.create_shift(
        name="Day",
        shift_type=ShiftType.MORNING,
        start_time="07:00",
        end_time="15:00",
        actor_roles={"ops"},
        station_ids=["CNC-01"],
    )

    svc.set_station_skill_requirements("CNC-01", ["cnc_machining"])
    svc.set_employee_skills(emp1, ["cnc_machining"])
    svc.set_employee_skills(emp2, ["cnc_machining"])

    svc.assign_slot(
        shift_id=shift.id,
        roster_date=date(2026, 1, 10),
        employee_id=emp1,
        actor_user_id=supervisor_user,
        actor_roles={"supervisor"},
    )
    svc.assign_slot(
        shift_id=shift.id,
        roster_date=date(2026, 1, 10),
        employee_id=emp2,
        actor_user_id=supervisor_user,
        actor_roles={"supervisor"},
    )

    # With both present, no risk (≥2).
    risks = svc.compute_coverage_risks(
        roster_date=date(2026, 1, 10),
        actor_roles={"supervisor"},
        minimum_required=2,
    )
    assert risks == []

    # Add absence for emp1 → only emp2 remains → HIGH risk.
    svc.record_absence(
        employee_id=emp1,
        absence_type=AbsenceType.SICK,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 10),
        actor_user_id=supervisor_user,
        actor_roles={"supervisor"},
        auto_approve=True,
    )

    risks2 = svc.compute_coverage_risks(
        roster_date=date(2026, 1, 10),
        actor_roles={"supervisor"},
        minimum_required=2,
    )
    assert len(risks2) == 1
    assert risks2[0].severity == RiskSeverity.HIGH
    assert risks2[0].available_count == 1


def test_coverage_risk_critical_when_zero() -> None:
    svc = StaffingRosterService()
    emp = uuid4()
    supervisor_user = uuid4()

    shift = svc.create_shift(
        name="Night",
        shift_type=ShiftType.NIGHT,
        start_time="22:00",
        end_time="06:00",
        actor_roles={"ops"},
        station_ids=["WELD-01"],
    )

    svc.set_station_skill_requirements("WELD-01", ["welding"])
    svc.set_employee_skills(emp, ["welding"])

    svc.assign_slot(
        shift_id=shift.id,
        roster_date=date(2026, 1, 11),
        employee_id=emp,
        actor_user_id=supervisor_user,
        actor_roles={"supervisor"},
    )
    svc.record_absence(
        employee_id=emp,
        absence_type=AbsenceType.TRAINING,
        start_date=date(2026, 1, 11),
        end_date=date(2026, 1, 11),
        actor_user_id=supervisor_user,
        actor_roles={"supervisor"},
        auto_approve=True,
    )

    risks = svc.compute_coverage_risks(
        roster_date=date(2026, 1, 11),
        actor_roles={"gm"},
        minimum_required=1,
    )
    assert len(risks) == 1
    assert risks[0].severity == RiskSeverity.CRITICAL
    assert risks[0].available_count == 0


def test_view_permission_enforcement() -> None:
    svc = StaffingRosterService()
    svc.create_shift(
        name="Flex",
        shift_type=ShiftType.FLEX,
        start_time="09:00",
        end_time="17:00",
        actor_roles={"admin"},
    )

    with pytest.raises(PermissionError):
        svc.list_shifts(actor_roles={"viewer"})

    shifts = svc.list_shifts(actor_roles={"exec"})
    assert len(shifts) == 1

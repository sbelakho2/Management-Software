from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from sensei.services.payroll_labor_costing import (
    AttendanceEventType,
    PayrollLaborCostingService,
    TimecardStatus,
    VarianceStatus,
)


def _dt(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


class TestPayrollLaborCosting:
    def test_timecard_validation_and_export_includes_only_validated(self):
        service = PayrollLaborCostingService()
        day = date(2026, 1, 5)

        # Unvalidated timecard should not appear
        service.record_attendance_event(
            employee_id="emp-1",
            occurred_at=_dt(2026, 1, 5, 8, 0),
            event_type=AttendanceEventType.CLOCK_IN,
        )
        service.record_attendance_event(
            employee_id="emp-1",
            occurred_at=_dt(2026, 1, 5, 16, 0),
            event_type=AttendanceEventType.CLOCK_OUT,
        )
        service.build_timecard(employee_id="emp-1", day=day)

        csv_text = service.export_pay_period_csv(period_start=day, period_end=day)
        assert csv_text == ""

        # Validate and export
        tc = service.validate_timecard(
            employee_id="emp-1",
            day=day,
            validator_id="mgr-1",
            actor_roles=["supervisor"],
            validated_at=_dt(2026, 1, 6, 9, 0),
        )
        assert tc.status == TimecardStatus.VALIDATED
        assert tc.hours_worked == 8.0

        csv_text = service.export_pay_period_csv(period_start=day, period_end=day)
        assert "record_type" in csv_text
        assert "attendance" in csv_text
        assert "emp-1" in csv_text
        assert "8.0" in csv_text

    def test_breaks_reduce_worked_time(self):
        service = PayrollLaborCostingService()
        day = date(2026, 1, 7)

        service.record_attendance_event(
            employee_id="emp-2",
            occurred_at=_dt(2026, 1, 7, 8, 0),
            event_type=AttendanceEventType.CLOCK_IN,
        )
        service.record_attendance_event(
            employee_id="emp-2",
            occurred_at=_dt(2026, 1, 7, 12, 0),
            event_type=AttendanceEventType.BREAK_START,
        )
        service.record_attendance_event(
            employee_id="emp-2",
            occurred_at=_dt(2026, 1, 7, 12, 30),
            event_type=AttendanceEventType.BREAK_END,
        )
        service.record_attendance_event(
            employee_id="emp-2",
            occurred_at=_dt(2026, 1, 7, 16, 0),
            event_type=AttendanceEventType.CLOCK_OUT,
        )

        tc = service.build_timecard(employee_id="emp-2", day=day)
        assert tc.minutes_break == 30
        assert tc.hours_worked == 7.5

    def test_overtime_and_absence_approval_flow_affects_export(self):
        service = PayrollLaborCostingService()
        day = date(2026, 1, 8)

        service.record_attendance_event(
            employee_id="emp-3",
            occurred_at=_dt(2026, 1, 8, 8, 0),
            event_type=AttendanceEventType.CLOCK_IN,
        )
        service.record_attendance_event(
            employee_id="emp-3",
            occurred_at=_dt(2026, 1, 8, 16, 0),
            event_type=AttendanceEventType.CLOCK_OUT,
        )
        service.build_timecard(employee_id="emp-3", day=day)
        service.validate_timecard(
            employee_id="emp-3",
            day=day,
            validator_id="mgr-1",
            actor_roles=["ops"],
            validated_at=_dt(2026, 1, 8, 17, 0),
        )

        ot = service.submit_overtime_request(
            employee_id="emp-3",
            day=day,
            hours=2.0,
            reason="Rush order",
            requested_by="emp-3",
            requested_at=_dt(2026, 1, 8, 15, 0),
        )
        absence = service.submit_absence_request(
            employee_id="emp-3",
            day=day,
            hours=1.0,
            code="SICK",
            reason="Doctor",
            requested_by="emp-3",
            requested_at=_dt(2026, 1, 8, 7, 30),
        )

        ot2 = service.decide_variance_request(
            request_id=ot.id,
            approve=True,
            decided_by="mgr-1",
            actor_roles=["supervisor"],
            decided_at=_dt(2026, 1, 8, 18, 0),
        )
        abs2 = service.decide_variance_request(
            request_id=absence.id,
            approve=True,
            decided_by="mgr-1",
            actor_roles=["supervisor"],
            decided_at=_dt(2026, 1, 8, 18, 0),
        )
        assert ot2.status == VarianceStatus.APPROVED
        assert abs2.status == VarianceStatus.APPROVED

        rows = service.export_pay_period_rows(period_start=day, period_end=day)
        attendance_rows = [r for r in rows if r["record_type"] == "attendance"]
        assert len(attendance_rows) == 1
        assert attendance_rows[0]["overtime_hours"] == 2.0
        assert attendance_rows[0]["absence_code"] == "SICK"
        assert attendance_rows[0]["absence_hours"] == 1.0

    def test_direct_labor_booking_requires_cost_center_mapping_or_explicit(self):
        service = PayrollLaborCostingService()

        with pytest.raises(ValueError):
            service.record_labor_booking(
                employee_id="emp-4",
                station_id="st-1",
                started_at=_dt(2026, 1, 9, 8, 0),
                ended_at=_dt(2026, 1, 9, 9, 0),
                work_order_id="wo-1",
            )

        service.set_station_cost_center(
            station_id="st-1",
            cost_center="CC-100",
            actor_roles=["finance"],
        )

        booking = service.record_labor_booking(
            employee_id="emp-4",
            station_id="st-1",
            started_at=_dt(2026, 1, 9, 8, 0),
            ended_at=_dt(2026, 1, 9, 9, 30),
            work_order_id="wo-1",
            operation_id="op-10",
        )
        assert booking.cost_center == "CC-100"
        assert booking.hours == 1.5

        rows = service.export_pay_period_rows(
            period_start=date(2026, 1, 9), period_end=date(2026, 1, 9)
        )
        labor_rows = [r for r in rows if r["record_type"] == "labor_booking"]
        assert len(labor_rows) == 1
        assert labor_rows[0]["cost_center"] == "CC-100"

    def test_approver_role_required_for_validation_and_decisions(self):
        service = PayrollLaborCostingService()
        day = date(2026, 1, 10)

        service.record_attendance_event(
            employee_id="emp-5",
            occurred_at=_dt(2026, 1, 10, 8, 0),
            event_type=AttendanceEventType.CLOCK_IN,
        )
        service.record_attendance_event(
            employee_id="emp-5",
            occurred_at=_dt(2026, 1, 10, 16, 0),
            event_type=AttendanceEventType.CLOCK_OUT,
        )
        service.build_timecard(employee_id="emp-5", day=day)

        with pytest.raises(PermissionError):
            service.validate_timecard(
                employee_id="emp-5",
                day=day,
                validator_id="emp-5",
                actor_roles=["operator"],
            )

        vr = service.submit_overtime_request(
            employee_id="emp-5",
            day=day,
            hours=1.0,
            reason="Need to finish",
            requested_by="emp-5",
        )

        with pytest.raises(PermissionError):
            service.decide_variance_request(
                request_id=vr.id,
                approve=True,
                decided_by="emp-5",
                actor_roles=["operator"],
            )

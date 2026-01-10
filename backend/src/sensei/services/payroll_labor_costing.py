"""Payroll & Labor Costing (ERP Sync) service.

Implements the 21.7 development plan item:
- Time & Attendance Export: validated daily timecards suitable for monthly payroll.
- Direct Labor Booking: operator station time linked to cost centers/work orders.
- Overtime/Absence Approval: lightweight approval workflow with budget-impact metadata.

This module is intentionally in-memory and pure-Python to match other service modules.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class AttendanceEventType(str, Enum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    BREAK_START = "break_start"
    BREAK_END = "break_end"


class TimecardStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"


class VarianceType(str, Enum):
    OVERTIME = "overtime"
    ABSENCE = "absence"


class VarianceStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"


@dataclass(frozen=True)
class AttendanceEvent:
    id: UUID
    employee_id: str
    occurred_at: datetime
    event_type: AttendanceEventType
    source: str
    terminal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Timecard:
    id: UUID
    employee_id: str
    day: date
    minutes_worked: int
    minutes_break: int
    status: TimecardStatus = TimecardStatus.DRAFT
    validated_at: datetime | None = None
    validated_by: str | None = None

    @property
    def hours_worked(self) -> float:
        return round(self.minutes_worked / 60.0, 2)

    @property
    def break_hours(self) -> float:
        return round(self.minutes_break / 60.0, 2)


@dataclass(frozen=True)
class VarianceRequest:
    id: UUID
    employee_id: str
    day: date
    variance_type: VarianceType
    hours: float
    code: str | None
    reason: str
    requested_at: datetime
    requested_by: str
    status: VarianceStatus = VarianceStatus.PENDING
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_note: str | None = None


@dataclass(frozen=True)
class LaborBooking:
    id: UUID
    employee_id: str
    station_id: str
    started_at: datetime
    ended_at: datetime
    minutes: int
    cost_center: str
    work_order_id: str | None = None
    operation_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def hours(self) -> float:
        return round(self.minutes / 60.0, 2)


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


_APPROVER_ROLES: set[str] = {
    "admin",
    "gm",
    "exec",
    "ops",
    "supervisor",
    "team_lead",
    "hr",
    "finance",
    "accountant",
}

_FINANCE_WRITE_ROLES: set[str] = {"admin", "finance", "accountant", "gm", "exec"}


class PayrollLaborCostingService:
    """In-memory payroll exports, labor booking, and variance approvals."""

    def __init__(self, *, erp_service: Any | None = None):
        self._events: list[AttendanceEvent] = []
        self._timecards: dict[tuple[str, date], Timecard] = {}
        self._variances: dict[UUID, VarianceRequest] = {}
        self._labor_bookings: dict[UUID, LaborBooking] = {}

        # Optional mappings used for COGS attribution
        self._station_cost_centers: dict[str, str] = {}
        self._employee_hourly_rates: dict[str, float] = {}

        # Optional outbound sync integration
        self._erp_service = erp_service

    # ---------------------------------------------------------------------
    # Attendance capture + validation
    # ---------------------------------------------------------------------

    def record_attendance_event(
        self,
        *,
        employee_id: str,
        occurred_at: datetime,
        event_type: AttendanceEventType,
        source: str = "terminal_scan",
        terminal_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AttendanceEvent:
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        event = AttendanceEvent(
            id=uuid4(),
            employee_id=employee_id,
            occurred_at=occurred_at,
            event_type=event_type,
            source=source,
            terminal_id=terminal_id,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def build_timecard(self, *, employee_id: str, day: date) -> Timecard:
        events = [
            e
            for e in self._events
            if e.employee_id == employee_id and e.occurred_at.date() == day
        ]
        events.sort(key=lambda e: e.occurred_at)

        if not events:
            tc = Timecard(
                id=uuid4(),
                employee_id=employee_id,
                day=day,
                minutes_worked=0,
                minutes_break=0,
            )
            self._timecards[(employee_id, day)] = tc
            return tc

        # We compute:
        # - work minutes between CLOCK_IN -> CLOCK_OUT minus any break segments
        # - break minutes between BREAK_START -> BREAK_END
        clock_in: datetime | None = None
        clock_out: datetime | None = None
        break_start: datetime | None = None
        break_minutes = 0

        for e in events:
            if e.event_type == AttendanceEventType.CLOCK_IN:
                clock_in = e.occurred_at
            elif e.event_type == AttendanceEventType.CLOCK_OUT:
                clock_out = e.occurred_at
            elif e.event_type == AttendanceEventType.BREAK_START:
                break_start = e.occurred_at
            elif e.event_type == AttendanceEventType.BREAK_END:
                if break_start is not None:
                    delta = e.occurred_at - break_start
                    break_minutes += max(0, int(delta.total_seconds() // 60))
                break_start = None

        if clock_in is None or clock_out is None or clock_out < clock_in:
            raise ValueError("Invalid attendance events: missing or misordered clock in/out")

        total_minutes = int((clock_out - clock_in).total_seconds() // 60)
        worked_minutes = max(0, total_minutes - break_minutes)

        tc = Timecard(
            id=self._timecards.get((employee_id, day), Timecard(uuid4(), employee_id, day, 0, 0)).id,
            employee_id=employee_id,
            day=day,
            minutes_worked=worked_minutes,
            minutes_break=break_minutes,
        )
        self._timecards[(employee_id, day)] = tc
        return tc

    def validate_timecard(
        self,
        *,
        employee_id: str,
        day: date,
        validator_id: str,
        actor_roles: Iterable[str],
        validated_at: datetime | None = None,
    ) -> Timecard:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_APPROVER_ROLES):
            raise PermissionError("Approver role required")

        tc = self._timecards.get((employee_id, day))
        if tc is None:
            tc = self.build_timecard(employee_id=employee_id, day=day)

        tc.status = TimecardStatus.VALIDATED
        tc.validated_at = validated_at or datetime.now(timezone.utc)
        tc.validated_by = validator_id
        return tc

    def get_timecard(self, *, employee_id: str, day: date) -> Timecard | None:
        return self._timecards.get((employee_id, day))

    # ---------------------------------------------------------------------
    # Overtime / Absence approvals
    # ---------------------------------------------------------------------

    def submit_overtime_request(
        self,
        *,
        employee_id: str,
        day: date,
        hours: float,
        reason: str,
        requested_by: str,
        requested_at: datetime | None = None,
    ) -> VarianceRequest:
        if hours <= 0:
            raise ValueError("hours must be > 0")
        vr = VarianceRequest(
            id=uuid4(),
            employee_id=employee_id,
            day=day,
            variance_type=VarianceType.OVERTIME,
            hours=float(hours),
            code=None,
            reason=reason,
            requested_at=requested_at or datetime.now(timezone.utc),
            requested_by=requested_by,
        )
        self._variances[vr.id] = vr
        return vr

    def submit_absence_request(
        self,
        *,
        employee_id: str,
        day: date,
        hours: float,
        code: str,
        reason: str,
        requested_by: str,
        requested_at: datetime | None = None,
    ) -> VarianceRequest:
        if hours <= 0:
            raise ValueError("hours must be > 0")
        if not code.strip():
            raise ValueError("code is required")
        vr = VarianceRequest(
            id=uuid4(),
            employee_id=employee_id,
            day=day,
            variance_type=VarianceType.ABSENCE,
            hours=float(hours),
            code=code.strip(),
            reason=reason,
            requested_at=requested_at or datetime.now(timezone.utc),
            requested_by=requested_by,
        )
        self._variances[vr.id] = vr
        return vr

    def decide_variance_request(
        self,
        *,
        request_id: UUID,
        approve: bool,
        decided_by: str,
        actor_roles: Iterable[str],
        decided_at: datetime | None = None,
        decision_note: str | None = None,
    ) -> VarianceRequest:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_APPROVER_ROLES):
            raise PermissionError("Approver role required")

        vr = self._variances.get(request_id)
        if vr is None:
            raise KeyError("Variance request not found")

        if vr.status != VarianceStatus.PENDING:
            return vr

        updated = VarianceRequest(
            id=vr.id,
            employee_id=vr.employee_id,
            day=vr.day,
            variance_type=vr.variance_type,
            hours=vr.hours,
            code=vr.code,
            reason=vr.reason,
            requested_at=vr.requested_at,
            requested_by=vr.requested_by,
            status=VarianceStatus.APPROVED if approve else VarianceStatus.REJECTED,
            decided_at=decided_at or datetime.now(timezone.utc),
            decided_by=decided_by,
            decision_note=decision_note,
        )
        self._variances[request_id] = updated
        return updated

    def list_variances(
        self,
        *,
        employee_id: str | None = None,
        day: date | None = None,
        status: VarianceStatus | None = None,
    ) -> list[VarianceRequest]:
        items = list(self._variances.values())
        if employee_id is not None:
            items = [v for v in items if v.employee_id == employee_id]
        if day is not None:
            items = [v for v in items if v.day == day]
        if status is not None:
            items = [v for v in items if v.status == status]
        items.sort(key=lambda v: (v.day, v.requested_at))
        return items

    # ---------------------------------------------------------------------
    # Direct labor booking
    # ---------------------------------------------------------------------

    def set_station_cost_center(
        self,
        *,
        station_id: str,
        cost_center: str,
        actor_roles: Iterable[str],
    ) -> None:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_FINANCE_WRITE_ROLES.union({"ops"})):
            raise PermissionError("Finance/Ops/Admin role required")
        if not cost_center.strip():
            raise ValueError("cost_center is required")
        self._station_cost_centers[station_id] = cost_center.strip()

    def record_labor_booking(
        self,
        *,
        employee_id: str,
        station_id: str,
        started_at: datetime,
        ended_at: datetime,
        work_order_id: str | None = None,
        operation_id: str | None = None,
        cost_center: str | None = None,
    ) -> LaborBooking:
        if started_at.tzinfo is None or ended_at.tzinfo is None:
            raise ValueError("started_at/ended_at must be timezone-aware")
        if ended_at <= started_at:
            raise ValueError("ended_at must be after started_at")

        minutes = int((ended_at - started_at).total_seconds() // 60)
        if minutes <= 0:
            raise ValueError("Booking must be at least 1 minute")

        resolved_cost_center = (
            cost_center.strip()
            if cost_center and cost_center.strip()
            else self._station_cost_centers.get(station_id)
        )
        if not resolved_cost_center:
            raise ValueError("No cost center provided/mapped for station")

        booking = LaborBooking(
            id=uuid4(),
            employee_id=employee_id,
            station_id=station_id,
            started_at=started_at,
            ended_at=ended_at,
            minutes=minutes,
            cost_center=resolved_cost_center,
            work_order_id=work_order_id,
            operation_id=operation_id,
        )
        self._labor_bookings[booking.id] = booking
        return booking

    def list_labor_bookings(
        self,
        *,
        employee_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[LaborBooking]:
        items = list(self._labor_bookings.values())
        if employee_id is not None:
            items = [b for b in items if b.employee_id == employee_id]
        if start is not None:
            items = [b for b in items if b.ended_at >= start]
        if end is not None:
            items = [b for b in items if b.started_at <= end]
        items.sort(key=lambda b: b.started_at)
        return items

    # ---------------------------------------------------------------------
    # Rates + export
    # ---------------------------------------------------------------------

    def set_employee_hourly_rate(
        self,
        *,
        employee_id: str,
        hourly_rate: float,
        actor_roles: Iterable[str],
    ) -> None:
        roles = _norm_roles(actor_roles)
        if not roles.intersection(_FINANCE_WRITE_ROLES.union({"hr"})):
            raise PermissionError("Finance/HR/Admin role required")
        if hourly_rate <= 0:
            raise ValueError("hourly_rate must be > 0")
        self._employee_hourly_rates[employee_id] = float(hourly_rate)

    def _approved_variances_for_day(
        self, *, employee_id: str, day: date
    ) -> tuple[float, list[tuple[str, float]]]:
        overtime_hours = 0.0
        absences: list[tuple[str, float]] = []
        for v in self._variances.values():
            if v.employee_id != employee_id or v.day != day:
                continue
            if v.status != VarianceStatus.APPROVED:
                continue
            if v.variance_type == VarianceType.OVERTIME:
                overtime_hours += v.hours
            elif v.variance_type == VarianceType.ABSENCE:
                absences.append((v.code or "absence", v.hours))
        return round(overtime_hours, 2), absences

    def export_pay_period_rows(
        self, *, period_start: date, period_end: date
    ) -> list[dict[str, Any]]:
        if period_end < period_start:
            raise ValueError("period_end must be >= period_start")

        rows: list[dict[str, Any]] = []

        # Attendance exports: validated timecards only
        for (employee_id, day), tc in sorted(self._timecards.items(), key=lambda x: (x[0][0], x[0][1])):
            if day < period_start or day > period_end:
                continue
            if tc.status != TimecardStatus.VALIDATED:
                continue

            overtime_hours, absences = self._approved_variances_for_day(
                employee_id=employee_id, day=day
            )
            # For export, we include the first absence code (if any) for the day.
            absence_code = absences[0][0] if absences else ""
            absence_hours = absences[0][1] if absences else 0.0

            rows.append(
                {
                    "record_type": "attendance",
                    "employee_id": employee_id,
                    "date": day.isoformat(),
                    "hours_worked": tc.hours_worked,
                    "break_hours": tc.break_hours,
                    "overtime_hours": overtime_hours,
                    "absence_code": absence_code,
                    "absence_hours": round(absence_hours, 2),
                    "validated_by": tc.validated_by or "",
                    "validated_at": tc.validated_at.isoformat() if tc.validated_at else "",
                }
            )

        # Direct labor booking exports
        period_start_dt = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
        period_end_dt = datetime.combine(period_end, time.max, tzinfo=timezone.utc)
        for booking in self.list_labor_bookings(start=period_start_dt, end=period_end_dt):
            rows.append(
                {
                    "record_type": "labor_booking",
                    "employee_id": booking.employee_id,
                    "date": booking.started_at.date().isoformat(),
                    "hours": booking.hours,
                    "cost_center": booking.cost_center,
                    "station_id": booking.station_id,
                    "work_order_id": booking.work_order_id or "",
                    "operation_id": booking.operation_id or "",
                    "started_at": booking.started_at.isoformat(),
                    "ended_at": booking.ended_at.isoformat(),
                }
            )

        return rows

    def export_pay_period_csv(self, *, period_start: date, period_end: date) -> str:
        rows = self.export_pay_period_rows(period_start=period_start, period_end=period_end)
        if not rows:
            return ""

        # Stable header order
        fieldnames = list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()

    def sync_pay_period_to_erp(self, *, period_start: date, period_end: date) -> list[Any]:
        """Create outbound sync records via ERPIntegrationService (if configured)."""
        if self._erp_service is None:
            raise RuntimeError("ERP service not configured")

        rows = self.export_pay_period_rows(period_start=period_start, period_end=period_end)
        sync_records: list[Any] = []
        for row in rows:
            labor_id = f"labor_{row['record_type']}_{row['employee_id']}_{row['date']}_{uuid4().hex[:8]}"
            sync_records.append(self._erp_service.sync_employee_labor(labor_id, row))
        return sync_records

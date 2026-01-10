"""Leave Management Service (Development Plan 22.6 HRIS).

Implements:
- Accrual Policies: define leave types with accrual rates, caps, carry-over rules.
- Holiday Calendars: site/region-specific public holidays.
- Leave Requests: request/approve/reject workflow with balance tracking.
- Payroll Impact Export: export approved leave for payroll processing.

This module is intentionally in-memory and pure-Python to match other services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


# ---------------------- Enums ----------------------


class LeaveType(str, Enum):
    """Standard leave categories."""

    ANNUAL = "annual"
    SICK = "sick"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    BEREAVEMENT = "bereavement"
    UNPAID = "unpaid"
    TRAINING = "training"
    COMPENSATORY = "compensatory"
    OTHER = "other"


class AccrualFrequency(str, Enum):
    """How often leave accrues."""

    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    ANNUAL_GRANT = "annual_grant"


class LeaveRequestStatus(str, Enum):
    """Leave request lifecycle states."""

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# ---------------------- RBAC ----------------------


_HR_WRITE_ROLES: set[str] = {"admin", "hr", "gm"}
_HR_READ_ROLES: set[str] = {"admin", "hr", "gm", "exec", "ceo", "finance", "supervisor"}
_APPROVE_ROLES: set[str] = {"admin", "hr", "gm", "supervisor"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------- Data Models ----------------------


@dataclass
class AuditEvent:
    """Audit trail entry."""

    id: UUID
    actor_id: str
    actor_roles: frozenset[str]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccrualPolicy:
    """Defines how leave accrues for a leave type."""

    id: UUID
    leave_type: LeaveType
    name: str
    accrual_frequency: AccrualFrequency
    accrual_rate: Decimal  # days per period
    max_balance: Decimal  # cap on accumulation
    carry_over_cap: Decimal  # max days that roll over to next year
    min_tenure_months: int  # minimum employment before accrual starts
    requires_documentation: bool  # e.g., sick leave may require doctor note
    paid: bool  # whether this leave type is paid
    site_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class HolidayCalendar:
    """Site/region-specific holiday calendar."""

    id: UUID
    name: str
    year: int
    region: str  # e.g., "MA" for Morocco, "TN" for Tunisia, "WY" for Wyoming
    site_id: str | None = None
    holidays: list["PublicHoliday"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class PublicHoliday:
    """A single public holiday."""

    date: date
    name: str
    half_day: bool = False  # True if only half day off


@dataclass
class LeaveBalance:
    """Employee's current leave balance for a specific type."""

    id: UUID
    employee_id: UUID
    leave_type: LeaveType
    policy_id: UUID
    year: int
    accrued: Decimal  # total accrued this year
    used: Decimal  # total used this year
    carried_over: Decimal  # from previous year
    adjusted: Decimal  # manual adjustments (positive or negative)
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def available(self) -> Decimal:
        """Calculate available balance."""
        return self.accrued + self.carried_over + self.adjusted - self.used


@dataclass
class LeaveRequest:
    """An employee leave request."""

    id: UUID
    employee_id: UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_requested: Decimal
    status: LeaveRequestStatus
    reason: str = ""
    documentation_url: str | None = None
    half_day_start: bool = False  # start is afternoon only
    half_day_end: bool = False  # end is morning only
    submitted_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    correlation_id: str = ""


@dataclass
class PayrollLeaveExport:
    """Record of leave exported for payroll processing."""

    id: UUID
    export_date: date
    period_start: date
    period_end: date
    employee_ids: list[UUID]
    records: list["PayrollLeaveRecord"]
    exported_by: str
    correlation_id: str
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class PayrollLeaveRecord:
    """Single employee leave record for payroll."""

    employee_id: UUID
    leave_type: LeaveType
    paid: bool
    days: Decimal
    start_date: date
    end_date: date
    request_id: UUID


# ---------------------- Service ----------------------


class LeaveManagementService:
    """In-memory leave management service with RBAC."""

    def __init__(self) -> None:
        self._policies: dict[UUID, AccrualPolicy] = {}
        self._calendars: dict[UUID, HolidayCalendar] = {}
        self._balances: dict[UUID, LeaveBalance] = {}
        self._requests: dict[UUID, LeaveRequest] = {}
        self._exports: dict[UUID, PayrollLeaveExport] = {}
        self._audit: list[AuditEvent] = []

    # ---------------------- Audit ----------------------

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: set[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit.append(
            AuditEvent(
                id=uuid4(),
                actor_id=actor_id,
                actor_roles=frozenset(actor_roles),
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                timestamp=_utcnow(),
                metadata=metadata or {},
            )
        )

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return list(self._audit)

    # ---------------------- Accrual Policies ----------------------

    def create_accrual_policy(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        leave_type: LeaveType,
        name: str,
        accrual_frequency: AccrualFrequency,
        accrual_rate: Decimal,
        max_balance: Decimal = Decimal("999"),
        carry_over_cap: Decimal = Decimal("0"),
        min_tenure_months: int = 0,
        requires_documentation: bool = False,
        paid: bool = True,
        site_id: str | None = None,
    ) -> AccrualPolicy:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not name or not name.strip():
            raise ValueError("Policy name required")
        if accrual_rate < 0:
            raise ValueError("accrual_rate must be >= 0")
        if max_balance < 0:
            raise ValueError("max_balance must be >= 0")

        policy = AccrualPolicy(
            id=uuid4(),
            leave_type=leave_type,
            name=name.strip(),
            accrual_frequency=accrual_frequency,
            accrual_rate=Decimal(str(accrual_rate)),
            max_balance=Decimal(str(max_balance)),
            carry_over_cap=Decimal(str(carry_over_cap)),
            min_tenure_months=min_tenure_months,
            requires_documentation=requires_documentation,
            paid=paid,
            site_id=site_id,
        )

        self._policies[policy.id] = policy
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.policy.create",
            entity_type="accrual_policy",
            entity_id=str(policy.id),
            correlation_id=correlation_id,
            metadata={"leave_type": leave_type.value, "name": name},
        )
        return policy

    def list_policies(
        self,
        *,
        actor_roles: Iterable[str],
        leave_type: LeaveType | None = None,
        site_id: str | None = None,
    ) -> list[AccrualPolicy]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        policies = list(self._policies.values())
        if leave_type:
            policies = [p for p in policies if p.leave_type == leave_type]
        if site_id:
            policies = [p for p in policies if p.site_id == site_id or p.site_id is None]
        return policies

    def get_policy(
        self, *, actor_roles: Iterable[str], policy_id: UUID
    ) -> AccrualPolicy | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return self._policies.get(policy_id)

    # ---------------------- Holiday Calendars ----------------------

    def create_holiday_calendar(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        name: str,
        year: int,
        region: str,
        holidays: list[PublicHoliday],
        site_id: str | None = None,
    ) -> HolidayCalendar:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not name or not name.strip():
            raise ValueError("Calendar name required")
        if not region or not region.strip():
            raise ValueError("Region required")
        if year < 2000 or year > 2100:
            raise ValueError("Invalid year")

        calendar = HolidayCalendar(
            id=uuid4(),
            name=name.strip(),
            year=year,
            region=region.strip().upper(),
            site_id=site_id,
            holidays=list(holidays),
        )

        self._calendars[calendar.id] = calendar
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.calendar.create",
            entity_type="holiday_calendar",
            entity_id=str(calendar.id),
            correlation_id=correlation_id,
            metadata={"year": year, "region": region, "holiday_count": len(holidays)},
        )
        return calendar

    def list_calendars(
        self,
        *,
        actor_roles: Iterable[str],
        year: int | None = None,
        region: str | None = None,
    ) -> list[HolidayCalendar]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        calendars = list(self._calendars.values())
        if year:
            calendars = [c for c in calendars if c.year == year]
        if region:
            r = region.strip().upper()
            calendars = [c for c in calendars if c.region == r]
        return calendars

    def is_holiday(
        self,
        *,
        actor_roles: Iterable[str],
        check_date: date,
        region: str,
        site_id: str | None = None,
    ) -> tuple[bool, str | None]:
        """Check if a date is a holiday. Returns (is_holiday, holiday_name)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        r = region.strip().upper()
        calendars = [
            c for c in self._calendars.values()
            if c.year == check_date.year and c.region == r
            and (site_id is None or c.site_id == site_id or c.site_id is None)
        ]

        for cal in calendars:
            for h in cal.holidays:
                if h.date == check_date:
                    return (True, h.name)
        return (False, None)

    # ---------------------- Leave Balances ----------------------

    def initialize_balance(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        employee_id: UUID,
        leave_type: LeaveType,
        policy_id: UUID,
        year: int,
        carried_over: Decimal = Decimal("0"),
    ) -> LeaveBalance:
        """Initialize a leave balance for an employee for a given year."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        policy = self._policies.get(policy_id)
        if not policy:
            raise ValueError("Policy not found")

        # Check for existing balance
        for bal in self._balances.values():
            if (
                bal.employee_id == employee_id
                and bal.leave_type == leave_type
                and bal.year == year
            ):
                raise ValueError("Balance already exists for this employee/type/year")

        balance = LeaveBalance(
            id=uuid4(),
            employee_id=employee_id,
            leave_type=leave_type,
            policy_id=policy_id,
            year=year,
            accrued=Decimal("0"),
            used=Decimal("0"),
            carried_over=min(Decimal(str(carried_over)), policy.carry_over_cap) if policy.carry_over_cap > 0 else Decimal(str(carried_over)),
            adjusted=Decimal("0"),
        )

        self._balances[balance.id] = balance
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.balance.init",
            entity_type="leave_balance",
            entity_id=str(balance.id),
            correlation_id=correlation_id,
            metadata={"employee_id": str(employee_id), "year": year},
        )
        return balance

    def accrue_leave(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        balance_id: UUID,
        amount: Decimal,
    ) -> LeaveBalance:
        """Add accrued leave to a balance."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        balance = self._balances.get(balance_id)
        if not balance:
            raise ValueError("Balance not found")

        policy = self._policies.get(balance.policy_id)
        new_accrued = balance.accrued + Decimal(str(amount))

        # Cap at max balance
        if policy and policy.max_balance > 0:
            total_after = new_accrued + balance.carried_over + balance.adjusted - balance.used
            if total_after > policy.max_balance:
                new_accrued = policy.max_balance - balance.carried_over - balance.adjusted + balance.used

        balance.accrued = new_accrued
        balance.updated_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.balance.accrue",
            entity_type="leave_balance",
            entity_id=str(balance_id),
            correlation_id=correlation_id,
            metadata={"amount": str(amount), "new_accrued": str(new_accrued)},
        )
        return balance

    def adjust_balance(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        balance_id: UUID,
        adjustment: Decimal,
        reason: str,
    ) -> LeaveBalance:
        """Manual adjustment to balance (positive or negative)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not reason or not reason.strip():
            raise ValueError("Adjustment reason required")

        balance = self._balances.get(balance_id)
        if not balance:
            raise ValueError("Balance not found")

        balance.adjusted = balance.adjusted + Decimal(str(adjustment))
        balance.updated_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.balance.adjust",
            entity_type="leave_balance",
            entity_id=str(balance_id),
            correlation_id=correlation_id,
            metadata={"adjustment": str(adjustment), "reason": reason},
        )
        return balance

    def _get_balance_internal(
        self,
        *,
        employee_id: UUID,
        leave_type: LeaveType,
        year: int,
    ) -> LeaveBalance | None:
        """Internal balance lookup without RBAC check."""
        for bal in self._balances.values():
            if (
                bal.employee_id == employee_id
                and bal.leave_type == leave_type
                and bal.year == year
            ):
                return bal
        return None

    def get_balance(
        self,
        *,
        actor_roles: Iterable[str],
        employee_id: UUID,
        leave_type: LeaveType,
        year: int,
    ) -> LeaveBalance | None:
        """Get balance for a specific employee/type/year."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        return self._get_balance_internal(
            employee_id=employee_id,
            leave_type=leave_type,
            year=year,
        )

    def list_balances(
        self,
        *,
        actor_roles: Iterable[str],
        employee_id: UUID | None = None,
        year: int | None = None,
    ) -> list[LeaveBalance]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        balances = list(self._balances.values())
        if employee_id:
            balances = [b for b in balances if b.employee_id == employee_id]
        if year:
            balances = [b for b in balances if b.year == year]
        return balances

    # ---------------------- Leave Requests ----------------------

    def create_leave_request(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        employee_id: UUID,
        leave_type: LeaveType,
        start_date: date,
        end_date: date,
        reason: str = "",
        documentation_url: str | None = None,
        half_day_start: bool = False,
        half_day_end: bool = False,
    ) -> LeaveRequest:
        """Create a new leave request (any authenticated user for self)."""
        # Anyone can create their own request, HR can create for others
        roles = _norm_roles(actor_roles)

        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")

        # Calculate days requested
        days = self._calculate_leave_days(
            start_date, end_date, half_day_start, half_day_end
        )

        request = LeaveRequest(
            id=uuid4(),
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=days,
            status=LeaveRequestStatus.DRAFT,
            reason=reason,
            documentation_url=documentation_url,
            half_day_start=half_day_start,
            half_day_end=half_day_end,
            created_by=actor_id,
            correlation_id=correlation_id,
        )

        self._requests[request.id] = request
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.request.create",
            entity_type="leave_request",
            entity_id=str(request.id),
            correlation_id=correlation_id,
            metadata={"employee_id": str(employee_id), "days": str(days)},
        )
        return request

    def _calculate_leave_days(
        self,
        start_date: date,
        end_date: date,
        half_day_start: bool,
        half_day_end: bool,
    ) -> Decimal:
        """Calculate number of leave days (excluding weekends)."""
        days = Decimal("0")
        current = start_date
        while current <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current.weekday() < 5:
                if current == start_date and half_day_start:
                    days += Decimal("0.5")
                elif current == end_date and half_day_end:
                    days += Decimal("0.5")
                else:
                    days += Decimal("1")
            current += timedelta(days=1)
        return days

    def submit_leave_request(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        request_id: UUID,
    ) -> LeaveRequest:
        """Submit a draft request for approval."""
        roles = _norm_roles(actor_roles)

        request = self._requests.get(request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status != LeaveRequestStatus.DRAFT:
            raise ValueError("Only draft requests can be submitted")

        # Check balance (internal lookup, no RBAC - user can check own balance)
        balance = self._get_balance_internal(
            employee_id=request.employee_id,
            leave_type=request.leave_type,
            year=request.start_date.year,
        )
        if balance and balance.available < request.days_requested:
            raise ValueError(
                f"Insufficient balance: {balance.available} available, "
                f"{request.days_requested} requested"
            )

        request.status = LeaveRequestStatus.PENDING
        request.submitted_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.request.submit",
            entity_type="leave_request",
            entity_id=str(request_id),
            correlation_id=correlation_id,
        )
        return request

    def approve_leave_request(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        request_id: UUID,
        notes: str = "",
    ) -> LeaveRequest:
        """Approve a pending leave request."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _APPROVE_ROLES, "Approval role required")

        request = self._requests.get(request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status != LeaveRequestStatus.PENDING:
            raise ValueError("Only pending requests can be approved")

        # Deduct from balance (internal lookup - approver already RBAC checked)
        balance = self._get_balance_internal(
            employee_id=request.employee_id,
            leave_type=request.leave_type,
            year=request.start_date.year,
        )
        if balance:
            balance.used = balance.used + request.days_requested
            balance.updated_at = _utcnow()

        request.status = LeaveRequestStatus.APPROVED
        request.reviewed_by = actor_id
        request.reviewed_at = _utcnow()
        request.review_notes = notes

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.request.approve",
            entity_type="leave_request",
            entity_id=str(request_id),
            correlation_id=correlation_id,
        )
        return request

    def reject_leave_request(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        request_id: UUID,
        reason: str,
    ) -> LeaveRequest:
        """Reject a pending leave request."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _APPROVE_ROLES, "Approval role required")

        if not reason or not reason.strip():
            raise ValueError("Rejection reason required")

        request = self._requests.get(request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status != LeaveRequestStatus.PENDING:
            raise ValueError("Only pending requests can be rejected")

        request.status = LeaveRequestStatus.REJECTED
        request.reviewed_by = actor_id
        request.reviewed_at = _utcnow()
        request.review_notes = reason

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.request.reject",
            entity_type="leave_request",
            entity_id=str(request_id),
            correlation_id=correlation_id,
            metadata={"reason": reason},
        )
        return request

    def cancel_leave_request(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        request_id: UUID,
    ) -> LeaveRequest:
        """Cancel a request (employee or HR)."""
        roles = _norm_roles(actor_roles)

        request = self._requests.get(request_id)
        if not request:
            raise ValueError("Request not found")

        if request.status not in (
            LeaveRequestStatus.DRAFT,
            LeaveRequestStatus.PENDING,
            LeaveRequestStatus.APPROVED,
        ):
            raise ValueError("Cannot cancel request in current status")

        # If approved, restore balance (internal lookup - cancellation action already validated)
        if request.status == LeaveRequestStatus.APPROVED:
            balance = self._get_balance_internal(
                employee_id=request.employee_id,
                leave_type=request.leave_type,
                year=request.start_date.year,
            )
            if balance:
                balance.used = balance.used - request.days_requested
                balance.updated_at = _utcnow()

        request.status = LeaveRequestStatus.CANCELLED

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.request.cancel",
            entity_type="leave_request",
            entity_id=str(request_id),
            correlation_id=correlation_id,
        )
        return request
    def list_requests(
        self,
        *,
        actor_roles: Iterable[str],
        employee_id: UUID | None = None,
        status: LeaveRequestStatus | None = None,
        start_from: date | None = None,
        start_to: date | None = None,
    ) -> list[LeaveRequest]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        requests = list(self._requests.values())
        if employee_id:
            requests = [r for r in requests if r.employee_id == employee_id]
        if status:
            requests = [r for r in requests if r.status == status]
        if start_from:
            requests = [r for r in requests if r.start_date >= start_from]
        if start_to:
            requests = [r for r in requests if r.start_date <= start_to]
        return requests

    def get_request(
        self, *, actor_roles: Iterable[str], request_id: UUID
    ) -> LeaveRequest | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return self._requests.get(request_id)

    # ---------------------- Payroll Export ----------------------

    def export_for_payroll(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        period_start: date,
        period_end: date,
    ) -> PayrollLeaveExport:
        """Export approved leave for payroll processing."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        # Find all approved requests in the period
        approved = [
            r for r in self._requests.values()
            if r.status == LeaveRequestStatus.APPROVED
            and r.start_date <= period_end
            and r.end_date >= period_start
        ]

        records: list[PayrollLeaveRecord] = []
        employee_ids: set[UUID] = set()

        for req in approved:
            policy = None
            for bal in self._balances.values():
                if (
                    bal.employee_id == req.employee_id
                    and bal.leave_type == req.leave_type
                ):
                    policy = self._policies.get(bal.policy_id)
                    break

            records.append(
                PayrollLeaveRecord(
                    employee_id=req.employee_id,
                    leave_type=req.leave_type,
                    paid=policy.paid if policy else True,
                    days=req.days_requested,
                    start_date=req.start_date,
                    end_date=req.end_date,
                    request_id=req.id,
                )
            )
            employee_ids.add(req.employee_id)

        export = PayrollLeaveExport(
            id=uuid4(),
            export_date=date.today(),
            period_start=period_start,
            period_end=period_end,
            employee_ids=list(employee_ids),
            records=records,
            exported_by=actor_id,
            correlation_id=correlation_id,
        )

        self._exports[export.id] = export
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.payroll.export",
            entity_type="payroll_export",
            entity_id=str(export.id),
            correlation_id=correlation_id,
            metadata={
                "period": f"{period_start} to {period_end}",
                "record_count": len(records),
            },
        )
        return export

    def list_exports(
        self, *, actor_roles: Iterable[str]
    ) -> list[PayrollLeaveExport]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return list(self._exports.values())

    # ---------------------- Year-End Processing ----------------------

    def carry_over_balances(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        from_year: int,
        to_year: int,
        employee_ids: list[UUID] | None = None,
    ) -> list[LeaveBalance]:
        """Carry over balances from one year to the next."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        created: list[LeaveBalance] = []
        from_balances = [
            b for b in self._balances.values()
            if b.year == from_year
            and (employee_ids is None or b.employee_id in employee_ids)
        ]

        for bal in from_balances:
            policy = self._policies.get(bal.policy_id)
            if not policy:
                continue

            carry_over = min(bal.available, policy.carry_over_cap) if policy.carry_over_cap > 0 else Decimal("0")
            if carry_over <= 0:
                continue

            # Check if already exists
            existing = self.get_balance(
                actor_roles=actor_roles,
                employee_id=bal.employee_id,
                leave_type=bal.leave_type,
                year=to_year,
            )
            if existing:
                continue

            new_bal = self.initialize_balance(
                actor_id=actor_id,
                actor_roles=actor_roles,
                correlation_id=correlation_id,
                employee_id=bal.employee_id,
                leave_type=bal.leave_type,
                policy_id=bal.policy_id,
                year=to_year,
                carried_over=carry_over,
            )
            created.append(new_bal)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="leave.balance.carryover",
            entity_type="leave_balance",
            entity_id=f"{from_year}->{to_year}",
            correlation_id=correlation_id,
            metadata={"count": len(created)},
        )
        return created

"""Tests for Leave Management service (22.6 HRIS).

Covers:
- Accrual policies
- Holiday calendars
- Leave balances
- Leave requests (create/submit/approve/reject/cancel)
- Payroll export
- Year-end carry-over
- RBAC enforcement
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.leave_management import (
    AccrualFrequency,
    LeaveManagementService,
    LeaveRequestStatus,
    LeaveType,
    PublicHoliday,
)


# ---------------------- Fixtures ----------------------


@pytest.fixture
def svc() -> LeaveManagementService:
    return LeaveManagementService()


@pytest.fixture
def svc_with_policy(svc: LeaveManagementService) -> LeaveManagementService:
    svc.create_accrual_policy(
        actor_id="hr1",
        actor_roles=["hr"],
        correlation_id="setup",
        leave_type=LeaveType.ANNUAL,
        name="Standard Annual Leave",
        accrual_frequency=AccrualFrequency.MONTHLY,
        accrual_rate=Decimal("1.67"),  # ~20 days/year
        max_balance=Decimal("30"),
        carry_over_cap=Decimal("5"),
    )
    return svc


# ---------------------- RBAC Tests ----------------------


class TestRBAC:
    def test_unauthorized_policy_create(self, svc: LeaveManagementService):
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.create_accrual_policy(
                actor_id="op",
                actor_roles=["operator"],
                correlation_id="c1",
                leave_type=LeaveType.ANNUAL,
                name="Test",
                accrual_frequency=AccrualFrequency.MONTHLY,
                accrual_rate=Decimal("1"),
            )

    def test_unauthorized_policy_list(self, svc: LeaveManagementService):
        with pytest.raises(PermissionError, match="HR read role required"):
            svc.list_policies(actor_roles=["operator"])

    def test_unauthorized_approval(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        request = svc.create_leave_request(
            actor_id="emp",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 3),
        )
        svc.submit_leave_request(
            actor_id="emp",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )

        with pytest.raises(PermissionError, match="Approval role required"):
            svc.approve_leave_request(
                actor_id="op",
                actor_roles=["operator"],
                correlation_id="c5",
                request_id=request.id,
            )

    def test_hr_roles_can_write(self, svc: LeaveManagementService):
        for i, role in enumerate(["admin", "hr", "gm"]):
            policy = svc.create_accrual_policy(
                actor_id=f"u{i}",
                actor_roles=[role],
                correlation_id=f"c{i}",
                leave_type=LeaveType.ANNUAL,
                name=f"Policy {i}",
                accrual_frequency=AccrualFrequency.MONTHLY,
                accrual_rate=Decimal("1"),
            )
            assert policy is not None


# ---------------------- Accrual Policy Tests ----------------------


class TestAccrualPolicies:
    def test_create_policy(self, svc: LeaveManagementService):
        policy = svc.create_accrual_policy(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            leave_type=LeaveType.ANNUAL,
            name="Standard Annual",
            accrual_frequency=AccrualFrequency.MONTHLY,
            accrual_rate=Decimal("1.67"),
            max_balance=Decimal("30"),
            carry_over_cap=Decimal("5"),
            min_tenure_months=3,
        )

        assert policy.name == "Standard Annual"
        assert policy.accrual_rate == Decimal("1.67")
        assert policy.max_balance == Decimal("30")
        assert policy.carry_over_cap == Decimal("5")
        assert policy.min_tenure_months == 3
        assert policy.paid is True

    def test_create_policy_validation(self, svc: LeaveManagementService):
        roles = ["hr"]

        # Empty name
        with pytest.raises(ValueError, match="Policy name required"):
            svc.create_accrual_policy(
                actor_id="hr1",
                actor_roles=roles,
                correlation_id="c1",
                leave_type=LeaveType.ANNUAL,
                name="",
                accrual_frequency=AccrualFrequency.MONTHLY,
                accrual_rate=Decimal("1"),
            )

        # Negative rate
        with pytest.raises(ValueError, match="accrual_rate must be >= 0"):
            svc.create_accrual_policy(
                actor_id="hr1",
                actor_roles=roles,
                correlation_id="c1",
                leave_type=LeaveType.ANNUAL,
                name="Test",
                accrual_frequency=AccrualFrequency.MONTHLY,
                accrual_rate=Decimal("-1"),
            )

    def test_list_policies_by_type(self, svc: LeaveManagementService):
        svc.create_accrual_policy(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            leave_type=LeaveType.ANNUAL,
            name="Annual",
            accrual_frequency=AccrualFrequency.MONTHLY,
            accrual_rate=Decimal("1"),
        )
        svc.create_accrual_policy(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            leave_type=LeaveType.SICK,
            name="Sick",
            accrual_frequency=AccrualFrequency.ANNUAL_GRANT,
            accrual_rate=Decimal("10"),
        )

        annual = svc.list_policies(actor_roles=["hr"], leave_type=LeaveType.ANNUAL)
        assert len(annual) == 1
        assert annual[0].name == "Annual"


# ---------------------- Holiday Calendar Tests ----------------------


class TestHolidayCalendars:
    def test_create_calendar(self, svc: LeaveManagementService):
        holidays = [
            PublicHoliday(date=date(2026, 1, 1), name="New Year"),
            PublicHoliday(date=date(2026, 7, 4), name="Independence Day"),
            PublicHoliday(date=date(2026, 12, 25), name="Christmas"),
        ]

        cal = svc.create_holiday_calendar(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            name="US 2026",
            year=2026,
            region="US",
            holidays=holidays,
        )

        assert cal.year == 2026
        assert cal.region == "US"
        assert len(cal.holidays) == 3

    def test_is_holiday(self, svc: LeaveManagementService):
        holidays = [PublicHoliday(date=date(2026, 1, 1), name="New Year")]
        svc.create_holiday_calendar(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            name="MA 2026",
            year=2026,
            region="MA",
            holidays=holidays,
        )

        is_hol, name = svc.is_holiday(
            actor_roles=["hr"], check_date=date(2026, 1, 1), region="MA"
        )
        assert is_hol is True
        assert name == "New Year"

        is_hol2, _ = svc.is_holiday(
            actor_roles=["hr"], check_date=date(2026, 1, 2), region="MA"
        )
        assert is_hol2 is False


# ---------------------- Leave Balance Tests ----------------------


class TestLeaveBalances:
    def test_initialize_balance(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )

        assert balance.employee_id == emp_id
        assert balance.leave_type == LeaveType.ANNUAL
        assert balance.year == 2026
        assert balance.accrued == Decimal("0")
        assert balance.available == Decimal("0")

    def test_initialize_balance_with_carryover(
        self, svc_with_policy: LeaveManagementService
    ):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
            carried_over=Decimal("10"),  # but cap is 5
        )

        # Should be capped at carry_over_cap
        assert balance.carried_over == Decimal("5")

    def test_duplicate_balance_fails(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )

        with pytest.raises(ValueError, match="Balance already exists"):
            svc.initialize_balance(
                actor_id="hr1",
                actor_roles=["hr"],
                correlation_id="c2",
                employee_id=emp_id,
                leave_type=LeaveType.ANNUAL,
                policy_id=policy.id,
                year=2026,
            )

    def test_accrue_leave(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )

        updated = svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("1.67"),
        )

        assert updated.accrued == Decimal("1.67")
        assert updated.available == Decimal("1.67")

    def test_accrue_caps_at_max(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )

        # Accrue more than max (30)
        updated = svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("50"),
        )

        assert updated.available <= policy.max_balance

    def test_adjust_balance(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )

        updated = svc.adjust_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            adjustment=Decimal("3"),
            reason="Manager bonus leave",
        )

        assert updated.adjusted == Decimal("3")
        assert updated.available == Decimal("3")

    def test_adjust_requires_reason(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )

        with pytest.raises(ValueError, match="Adjustment reason required"):
            svc.adjust_balance(
                actor_id="hr1",
                actor_roles=["hr"],
                correlation_id="c2",
                balance_id=balance.id,
                adjustment=Decimal("3"),
                reason="",
            )


# ---------------------- Leave Request Tests ----------------------


class TestLeaveRequests:
    def test_create_and_submit_request(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        # Monday to Wednesday (3 weekdays)
        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),  # Monday
            end_date=date(2026, 7, 8),  # Wednesday
            reason="Vacation",
        )

        assert request.status == LeaveRequestStatus.DRAFT
        assert request.days_requested == Decimal("3")

        submitted = svc.submit_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )

        assert submitted.status == LeaveRequestStatus.PENDING
        assert submitted.submitted_at is not None

    def test_request_insufficient_balance(
        self, svc_with_policy: LeaveManagementService
    ):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("2"),  # Only 2 days
        )

        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 10),  # 5 weekdays
        )

        with pytest.raises(ValueError, match="Insufficient balance"):
            svc.submit_leave_request(
                actor_id="emp1",
                actor_roles=["operator"],
                correlation_id="c4",
                request_id=request.id,
            )

    def test_approve_request_deducts_balance(
        self, svc_with_policy: LeaveManagementService
    ):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 8),
        )
        svc.submit_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )

        approved = svc.approve_leave_request(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c5",
            request_id=request.id,
            notes="Approved",
        )

        assert approved.status == LeaveRequestStatus.APPROVED

        updated_balance = svc.get_balance(
            actor_roles=["hr"],
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            year=2026,
        )
        assert updated_balance.used == Decimal("3")
        assert updated_balance.available == Decimal("17")

    def test_reject_request(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 8),
        )
        svc.submit_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )

        rejected = svc.reject_leave_request(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c5",
            request_id=request.id,
            reason="Busy period",
        )

        assert rejected.status == LeaveRequestStatus.REJECTED
        assert rejected.review_notes == "Busy period"

    def test_reject_requires_reason(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 8),
        )
        svc.submit_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )

        with pytest.raises(ValueError, match="Rejection reason required"):
            svc.reject_leave_request(
                actor_id="hr1",
                actor_roles=["hr"],
                correlation_id="c5",
                request_id=request.id,
                reason="",
            )

    def test_cancel_approved_restores_balance(
        self, svc_with_policy: LeaveManagementService
    ):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 8),
        )
        svc.submit_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )
        svc.approve_leave_request(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c5",
            request_id=request.id,
        )

        # Cancel
        cancelled = svc.cancel_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c6",
            request_id=request.id,
        )

        assert cancelled.status == LeaveRequestStatus.CANCELLED

        updated_balance = svc.get_balance(
            actor_roles=["hr"],
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            year=2026,
        )
        assert updated_balance.used == Decimal("0")
        assert updated_balance.available == Decimal("20")

    def test_half_day_calculation(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        # Monday afternoon to Wednesday morning
        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),  # Monday
            end_date=date(2026, 7, 8),  # Wednesday
            half_day_start=True,
            half_day_end=True,
        )

        # 0.5 + 1 + 0.5 = 2
        assert request.days_requested == Decimal("2")


# ---------------------- Payroll Export Tests ----------------------


class TestPayrollExport:
    def test_export_approved_leave(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        balance = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2026,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance.id,
            amount=Decimal("20"),
        )

        request = svc.create_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c3",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 8),
        )
        svc.submit_leave_request(
            actor_id="emp1",
            actor_roles=["operator"],
            correlation_id="c4",
            request_id=request.id,
        )
        svc.approve_leave_request(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c5",
            request_id=request.id,
        )

        export = svc.export_for_payroll(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c6",
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
        )

        assert len(export.records) == 1
        assert export.records[0].employee_id == emp_id
        assert export.records[0].days == Decimal("3")
        assert export.records[0].paid is True


# ---------------------- Year-End Carry-Over Tests ----------------------


class TestCarryOver:
    def test_carry_over_balances(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        policy = svc.list_policies(actor_roles=["hr"])[0]
        emp_id = uuid4()

        # 2025 balance with remaining leave
        balance_2025 = svc.initialize_balance(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            policy_id=policy.id,
            year=2025,
        )
        svc.accrue_leave(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            balance_id=balance_2025.id,
            amount=Decimal("20"),
        )
        # Use 12 days - 8 remaining
        bal = svc.get_balance(
            actor_roles=["hr"],
            employee_id=emp_id,
            leave_type=LeaveType.ANNUAL,
            year=2025,
        )
        bal.used = Decimal("12")  # Direct mutation for test

        created = svc.carry_over_balances(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c3",
            from_year=2025,
            to_year=2026,
        )

        assert len(created) == 1
        assert created[0].year == 2026
        # Policy carry_over_cap is 5, so capped at 5
        assert created[0].carried_over == Decimal("5")


# ---------------------- Audit Tests ----------------------


class TestAudit:
    def test_audit_events_logged(self, svc_with_policy: LeaveManagementService):
        svc = svc_with_policy
        
        audits = svc.list_audit_events(actor_roles=["hr"])
        # One from fixture policy creation
        assert len(audits) >= 1
        assert audits[0].action == "leave.policy.create"

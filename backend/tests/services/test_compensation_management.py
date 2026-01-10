"""Tests for Compensation Management service.

Covers Section 22.6 HRIS:
- Pay bands
- Compensation records
- Change workflow with SoD
- RBAC enforcement
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.compensation_management import (
    ChangeReason,
    ChangeStatus,
    CompensationManagementService,
    CompensationType,
)


@pytest.fixture
def svc() -> CompensationManagementService:
    return CompensationManagementService()


# ---------------------- RBAC Tests ----------------------


class TestRBAC:
    def test_unauthorized_pay_band_create(self, svc):
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.create_pay_band(
                actor_id="u1",
                actor_roles=["operator"],
                correlation_id="c1",
                grade="A",
                level=1,
                min_amount=Decimal("30000"),
                mid_amount=Decimal("40000"),
                max_amount=Decimal("50000"),
            )

    def test_unauthorized_compensation_set(self, svc):
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.set_compensation(
                actor_id="u1",
                actor_roles=["operator"],
                correlation_id="c1",
                employee_id=uuid4(),
                amount=Decimal("50000"),
            )

    def test_unauthorized_history_view(self, svc):
        emp_id = uuid4()
        # First set up compensation with HR role
        svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("50000"),
        )

        with pytest.raises(PermissionError, match="Salary view role required"):
            svc.get_compensation_history(
                actor_id="u1",
                actor_roles=["gm"],  # GM can read HR, but not salary details
                employee_id=emp_id,
            )

    def test_hr_roles_can_write(self, svc):
        for role in ["admin", "hr", "ceo"]:
            band = svc.create_pay_band(
                actor_id=f"user-{role}",
                actor_roles=[role],
                correlation_id=f"c-{role}",
                grade=f"Grade-{role}",
                level=1,
                min_amount=Decimal("30000"),
                mid_amount=Decimal("40000"),
                max_amount=Decimal("50000"),
            )
            assert band is not None


# ---------------------- Pay Band Tests ----------------------


class TestPayBands:
    def test_create_pay_band(self, svc):
        band = svc.create_pay_band(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            grade="Engineer",
            level=2,
            min_amount=Decimal("60000"),
            mid_amount=Decimal("75000"),
            max_amount=Decimal("90000"),
            currency="USD",
        )

        assert band.grade == "Engineer"
        assert band.level == 2
        assert band.min_amount == Decimal("60000")
        assert band.mid_amount == Decimal("75000")
        assert band.max_amount == Decimal("90000")
        assert band.currency == "USD"

    def test_pay_band_validation(self, svc):
        roles = ["hr"]

        # Empty grade
        with pytest.raises(ValueError, match="grade required"):
            svc.create_pay_band(
                actor_id="hr",
                actor_roles=roles,
                correlation_id="c1",
                grade="",
                level=1,
                min_amount=Decimal("30000"),
                mid_amount=Decimal("40000"),
                max_amount=Decimal("50000"),
            )

        # Invalid level
        with pytest.raises(ValueError, match="level must be >= 1"):
            svc.create_pay_band(
                actor_id="hr",
                actor_roles=roles,
                correlation_id="c1",
                grade="A",
                level=0,
                min_amount=Decimal("30000"),
                mid_amount=Decimal("40000"),
                max_amount=Decimal("50000"),
            )

        # Mid less than min
        with pytest.raises(ValueError, match="mid_amount must be >= min_amount"):
            svc.create_pay_band(
                actor_id="hr",
                actor_roles=roles,
                correlation_id="c1",
                grade="A",
                level=1,
                min_amount=Decimal("40000"),
                mid_amount=Decimal("30000"),
                max_amount=Decimal("50000"),
            )

    def test_list_pay_bands_by_grade(self, svc):
        roles = ["hr"]
        svc.create_pay_band(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c1",
            grade="Engineer",
            level=1,
            min_amount=Decimal("50000"),
            mid_amount=Decimal("60000"),
            max_amount=Decimal("70000"),
        )
        svc.create_pay_band(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c2",
            grade="Engineer",
            level=2,
            min_amount=Decimal("70000"),
            mid_amount=Decimal("85000"),
            max_amount=Decimal("100000"),
        )
        svc.create_pay_band(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c3",
            grade="Manager",
            level=1,
            min_amount=Decimal("80000"),
            mid_amount=Decimal("100000"),
            max_amount=Decimal("120000"),
        )

        eng_bands = svc.list_pay_bands(actor_roles=roles, grade="Engineer")
        assert len(eng_bands) == 2
        assert all(b.grade == "Engineer" for b in eng_bands)


# ---------------------- Compensation Record Tests ----------------------


class TestCompensationRecords:
    def test_set_compensation(self, svc):
        emp_id = uuid4()
        record = svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("65000"),
            compensation_type=CompensationType.SALARY,
            currency="EUR",
            reason=ChangeReason.NEW_HIRE,
        )

        assert record.employee_id == emp_id
        assert record.amount == Decimal("65000")
        assert record.compensation_type == CompensationType.SALARY
        assert record.reason == ChangeReason.NEW_HIRE

    def test_set_compensation_with_band_validation(self, svc):
        roles = ["hr"]
        band = svc.create_pay_band(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c1",
            grade="Engineer",
            level=1,
            min_amount=Decimal("50000"),
            mid_amount=Decimal("60000"),
            max_amount=Decimal("70000"),
        )

        emp_id = uuid4()

        # Amount within band - should succeed
        record = svc.set_compensation(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c2",
            employee_id=emp_id,
            amount=Decimal("55000"),
            pay_band_id=band.id,
        )
        assert record.pay_band_id == band.id

    def test_set_compensation_outside_band_fails(self, svc):
        roles = ["hr"]
        band = svc.create_pay_band(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c1",
            grade="Engineer",
            level=1,
            min_amount=Decimal("50000"),
            mid_amount=Decimal("60000"),
            max_amount=Decimal("70000"),
        )

        with pytest.raises(ValueError, match="within band range"):
            svc.set_compensation(
                actor_id="hr",
                actor_roles=roles,
                correlation_id="c2",
                employee_id=uuid4(),
                amount=Decimal("80000"),  # Above max
                pay_band_id=band.id,
            )

    def test_compensation_history(self, svc):
        roles = ["hr"]
        emp_id = uuid4()

        # Initial salary
        svc.set_compensation(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("50000"),
            effective_date=date(2024, 1, 1),
            reason=ChangeReason.NEW_HIRE,
        )

        # Raise
        svc.set_compensation(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c2",
            employee_id=emp_id,
            amount=Decimal("55000"),
            effective_date=date(2025, 1, 1),
            reason=ChangeReason.MERIT,
        )

        history = svc.get_compensation_history(
            actor_id="hr",
            actor_roles=["finance"],  # Finance can see salary
            employee_id=emp_id,
        )
        assert len(history) == 2
        assert history[0].amount == Decimal("50000")
        assert history[0].end_date == date(2025, 1, 1)
        assert history[1].amount == Decimal("55000")
        assert history[1].end_date is None

    def test_salary_masking(self, svc):
        emp_id = uuid4()
        svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("100000"),
        )

        # GMs can read HR info but get masked salaries
        masked = svc.get_current_compensation(
            actor_id="gm",
            actor_roles=["gm"],
            employee_id=emp_id,
            mask_amount=True,
        )
        assert masked.amount == Decimal("0")
        assert masked.notes == "[MASKED]"

        # Finance can see actual amount
        unmasked = svc.get_current_compensation(
            actor_id="fin",
            actor_roles=["finance"],
            employee_id=emp_id,
            mask_amount=True,
        )
        assert unmasked.amount == Decimal("100000")


# ---------------------- Change Workflow Tests ----------------------


class TestChangeWorkflow:
    def test_propose_change(self, svc):
        emp_id = uuid4()
        svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("50000"),
        )

        change = svc.propose_change(
            actor_id="hr-person",
            actor_roles=["hr"],
            correlation_id="c2",
            employee_id=emp_id,
            proposed_amount=Decimal("55000"),
            reason=ChangeReason.MERIT,
            justification="Excellent performance review",
        )

        assert change.status == ChangeStatus.PENDING_APPROVAL
        assert change.proposed_amount == Decimal("55000")
        assert change.proposed_by == "hr-person"

    def test_propose_requires_justification(self, svc):
        with pytest.raises(ValueError, match="justification required"):
            svc.propose_change(
                actor_id="hr",
                actor_roles=["hr"],
                correlation_id="c1",
                employee_id=uuid4(),
                proposed_amount=Decimal("50000"),
                justification="",
            )

    def test_approve_change(self, svc):
        emp_id = uuid4()
        svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("50000"),
        )

        change = svc.propose_change(
            actor_id="hr-person",
            actor_roles=["hr"],
            correlation_id="c2",
            employee_id=emp_id,
            proposed_amount=Decimal("55000"),
            reason=ChangeReason.PROMOTION,
            justification="Promoted to Senior",
        )

        # Different person approves (SoD)
        approved = svc.approve_change(
            actor_id="ceo",
            actor_roles=["ceo"],
            correlation_id="c3",
            change_id=change.id,
        )

        assert approved.status == ChangeStatus.APPROVED
        assert approved.approved_by == "ceo"

        # Check compensation was updated
        current = svc.get_current_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            employee_id=emp_id,
        )
        assert current.amount == Decimal("55000")

    def test_sod_enforcement(self, svc):
        """Proposer cannot approve their own change."""
        emp_id = uuid4()
        svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("50000"),
        )

        change = svc.propose_change(
            actor_id="same-person",
            actor_roles=["hr"],
            correlation_id="c2",
            employee_id=emp_id,
            proposed_amount=Decimal("55000"),
            justification="Self-proposed raise",
        )

        with pytest.raises(PermissionError, match="Segregation of Duties"):
            svc.approve_change(
                actor_id="same-person",  # Same as proposer
                actor_roles=["ceo"],
                correlation_id="c3",
                change_id=change.id,
            )

    def test_reject_change(self, svc):
        change = svc.propose_change(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=uuid4(),
            proposed_amount=Decimal("100000"),
            justification="Big raise request",
        )

        rejected = svc.reject_change(
            actor_id="ceo",
            actor_roles=["ceo"],
            correlation_id="c2",
            change_id=change.id,
            reason="Budget constraints",
        )

        assert rejected.status == ChangeStatus.REJECTED
        assert rejected.rejection_reason == "Budget constraints"

    def test_reject_requires_reason(self, svc):
        change = svc.propose_change(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=uuid4(),
            proposed_amount=Decimal("50000"),
            justification="Test",
        )

        with pytest.raises(ValueError, match="rejection reason required"):
            svc.reject_change(
                actor_id="ceo",
                actor_roles=["ceo"],
                correlation_id="c2",
                change_id=change.id,
                reason="",
            )

    def test_list_pending_changes(self, svc):
        for i in range(3):
            svc.propose_change(
                actor_id="hr",
                actor_roles=["hr"],
                correlation_id=f"c-{i}",
                employee_id=uuid4(),
                proposed_amount=Decimal("50000") + i * 1000,
                justification=f"Change {i}",
            )

        pending = svc.list_pending_changes(actor_roles=["hr"])
        assert len(pending) == 3


# ---------------------- Export Tests ----------------------


class TestExport:
    def test_export_payroll_rates(self, svc):
        roles = ["hr"]
        for i in range(3):
            svc.set_compensation(
                actor_id="hr",
                actor_roles=roles,
                correlation_id=f"c-{i}",
                employee_id=uuid4(),
                amount=Decimal("50000") + i * 10000,
            )

        export = svc.export_payroll_rates(
            actor_id="fin",
            actor_roles=["finance"],
            correlation_id="exp-1",
        )

        assert len(export) == 3
        assert all("employee_id" in e for e in export)
        assert all("amount" in e for e in export)


# ---------------------- Audit Tests ----------------------


class TestAudit:
    def test_audit_trail(self, svc):
        emp_id = uuid4()
        svc.set_compensation(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            employee_id=emp_id,
            amount=Decimal("50000"),
        )

        change = svc.propose_change(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            employee_id=emp_id,
            proposed_amount=Decimal("55000"),
            justification="Annual review",
        )

        svc.approve_change(
            actor_id="ceo",
            actor_roles=["ceo"],
            correlation_id="c3",
            change_id=change.id,
        )

        audits = svc.list_audit_events(actor_roles=["auditor"])
        actions = [a.action for a in audits]
        assert "comp.record.set" in actions
        assert "comp.change.propose" in actions
        assert "comp.change.approve" in actions

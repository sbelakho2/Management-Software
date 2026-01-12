"""Tests for HR Case Management service.

Covers Section 22.6 HRIS:
- Case lifecycle (open, assign, close, archive)
- Notes and evidence with access logging
- Actions/outcomes
- Retention policy enforcement
- RBAC and PII controls
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from sensei.services.hr.hr_case_management import (
    ActionType,
    CasePriority,
    CaseStatus,
    CaseType,
    HRCaseManagementService,
)


@pytest.fixture
def svc() -> HRCaseManagementService:
    return HRCaseManagementService()


# ---------------------- RBAC Tests ----------------------


class TestRBAC:
    def test_unauthorized_open_case(self, svc):
        with pytest.raises(PermissionError, match="HR case role required"):
            svc.open_case(
                actor_id="u1",
                actor_roles=["operator"],
                correlation_id="c1",
                case_type=CaseType.GENERAL,
                subject_employee_id=uuid4(),
                title="Test",
                description="Test case",
            )

    def test_unauthorized_view_case(self, svc):
        # First create a case
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test case",
        )

        with pytest.raises(PermissionError, match="HR case view role required"):
            svc.get_case(
                actor_id="u1",
                actor_roles=["gm"],  # GM cannot view HR cases
                case_id=case.id,
            )

    def test_unauthorized_audit_access(self, svc):
        with pytest.raises(PermissionError, match="HR case audit role required"):
            svc.list_audit_events(actor_roles=["hr"])

    def test_only_admin_can_purge(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test case",
        )

        svc.close_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            reason="Completed",
        )

        # Manually archive for testing
        svc.update_case_status(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c3",
            case_id=case.id,
            status=CaseStatus.ARCHIVED,
        )

        with pytest.raises(PermissionError, match="Only admin can purge"):
            svc.purge_archived_data(
                actor_id="hr",
                actor_roles=["hr"],
                correlation_id="c4",
                case_id=case.id,
            )

    def test_hr_roles_can_manage(self, svc):
        for role in ["admin", "hr", "ceo"]:
            case = svc.open_case(
                actor_id=f"user-{role}",
                actor_roles=[role],
                correlation_id=f"c-{role}",
                case_type=CaseType.GENERAL,
                subject_employee_id=uuid4(),
                title=f"Case by {role}",
                description="Test",
            )
            assert case is not None


# ---------------------- Case Lifecycle Tests ----------------------


class TestCaseLifecycle:
    def test_open_case(self, svc):
        emp_id = uuid4()
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,
            subject_employee_id=emp_id,
            title="Performance Issue",
            description="Repeated tardiness",
            priority=CasePriority.HIGH,
        )

        assert case.case_number.startswith("HR-")
        assert case.case_type == CaseType.DISCIPLINARY
        assert case.subject_employee_id == emp_id
        assert case.status == CaseStatus.OPEN
        assert case.priority == CasePriority.HIGH
        assert case.opened_by == "hr"

    def test_case_validation(self, svc):
        roles = ["hr"]

        with pytest.raises(ValueError, match="title required"):
            svc.open_case(
                actor_id="hr",
                actor_roles=roles,
                correlation_id="c1",
                case_type=CaseType.GENERAL,
                subject_employee_id=uuid4(),
                title="",
                description="Test",
            )

        with pytest.raises(ValueError, match="description required"):
            svc.open_case(
                actor_id="hr",
                actor_roles=roles,
                correlation_id="c1",
                case_type=CaseType.GENERAL,
                subject_employee_id=uuid4(),
                title="Test",
                description="",
            )

    def test_assign_case(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.INVESTIGATION,
            subject_employee_id=uuid4(),
            title="Investigation",
            description="Needs assignment",
        )

        assigned = svc.assign_case(
            actor_id="hr-mgr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            assigned_to="investigator-1",
        )

        assert assigned.assigned_to == "investigator-1"
        assert assigned.status == CaseStatus.IN_PROGRESS

    def test_close_case(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GRIEVANCE,
            subject_employee_id=uuid4(),
            title="Grievance",
            description="Employee complaint",
        )

        closed = svc.close_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            reason="Resolved through mediation",
        )

        assert closed.status == CaseStatus.CLOSED
        assert closed.closed_by == "hr"
        assert closed.closure_reason == "Resolved through mediation"
        assert closed.retention_until is not None

    def test_close_requires_reason(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test",
        )

        with pytest.raises(ValueError, match="closure reason required"):
            svc.close_case(
                actor_id="hr",
                actor_roles=["hr"],
                correlation_id="c2",
                case_id=case.id,
                reason="",
            )

    def test_list_cases_excludes_archived(self, svc):
        roles = ["hr"]

        c1 = svc.open_case(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Case 1",
            description="Active",
        )

        c2 = svc.open_case(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c2",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Case 2",
            description="To archive",
        )

        svc.close_case(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c3",
            case_id=c2.id,
            reason="Done",
        )

        svc.update_case_status(
            actor_id="hr",
            actor_roles=roles,
            correlation_id="c4",
            case_id=c2.id,
            status=CaseStatus.ARCHIVED,
        )

        cases = svc.list_cases(actor_roles=roles)
        assert len(cases) == 1
        assert cases[0].id == c1.id

        cases_all = svc.list_cases(actor_roles=roles, include_archived=True)
        assert len(cases_all) == 2


# ---------------------- Notes Tests ----------------------


class TestNotes:
    def test_add_note(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test",
        )

        note = svc.add_note(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            content="Meeting held with employee",
            is_confidential=True,
        )

        assert note.case_id == case.id
        assert note.content == "Meeting held with employee"
        assert note.is_confidential is True

    def test_list_notes(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test",
        )

        for i in range(3):
            svc.add_note(
                actor_id="hr",
                actor_roles=["hr"],
                correlation_id=f"c-{i}",
                case_id=case.id,
                content=f"Note {i}",
            )

        notes = svc.list_notes(actor_roles=["hr"], case_id=case.id)
        assert len(notes) == 3


# ---------------------- Evidence Tests ----------------------


class TestEvidence:
    def test_add_evidence(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.INVESTIGATION,
            subject_employee_id=uuid4(),
            title="Investigation",
            description="Test",
        )

        evidence = svc.add_evidence(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            filename="email_thread.pdf",
            content_type="application/pdf",
            storage_path="/secure/cases/HR-000001/email_thread.pdf",
            description="Relevant email communications",
            file_hash="sha256:abc123",
        )

        assert evidence.filename == "email_thread.pdf"
        assert evidence.file_hash == "sha256:abc123"

    def test_evidence_access_logged(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test",
        )

        svc.add_evidence(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            filename="doc.pdf",
            content_type="application/pdf",
            storage_path="/path/doc.pdf",
        )

        # Access evidence list
        svc.list_evidence(
            actor_id="legal",
            actor_roles=["legal"],
            case_id=case.id,
        )

        # Check audit trail
        audits = svc.list_audit_events(actor_roles=["auditor"])
        view_events = [a for a in audits if a.action == "hr_case.view_evidence"]
        assert len(view_events) == 1
        assert view_events[0].actor_id == "legal"


# ---------------------- Actions Tests ----------------------


class TestActions:
    def test_record_action(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,
            subject_employee_id=uuid4(),
            title="Disciplinary",
            description="Test",
        )

        action = svc.record_action(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            action_type=ActionType.WRITTEN_WARNING,
            description="Written warning issued for policy violation",
            effective_date=date.today(),
        )

        assert action.action_type == ActionType.WRITTEN_WARNING
        assert action.case_id == case.id

    def test_list_actions(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,
            subject_employee_id=uuid4(),
            title="Test",
            description="Test",
        )

        svc.record_action(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            action_type=ActionType.VERBAL_WARNING,
            description="First warning",
        )

        svc.record_action(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c3",
            case_id=case.id,
            action_type=ActionType.WRITTEN_WARNING,
            description="Second warning",
        )

        actions = svc.list_actions(actor_roles=["hr"], case_id=case.id)
        assert len(actions) == 2


# ---------------------- Retention Tests ----------------------


class TestRetention:
    def test_retention_date_set_on_close(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,  # 7 year retention
            subject_employee_id=uuid4(),
            title="Test",
            description="Test",
        )

        closed = svc.close_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            reason="Resolved",
        )

        expected_retention = date.today() + timedelta(days=7 * 365)
        assert closed.retention_until == expected_retention

    def test_archive_expired_cases(self, svc):
        # Create and close case
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="Old case",
            description="Test",
        )

        closed = svc.close_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            reason="Done",
        )

        # Manually set retention to past date for testing
        expired = svc._cases[case.id]
        from sensei.services.hr.hr_case_management import HRCase

        past_retention = HRCase(
            id=expired.id,
            case_number=expired.case_number,
            case_type=expired.case_type,
            subject_employee_id=expired.subject_employee_id,
            priority=expired.priority,
            status=expired.status,
            title=expired.title,
            description=expired.description,
            opened_by=expired.opened_by,
            opened_at=expired.opened_at,
            assigned_to=expired.assigned_to,
            closed_by=expired.closed_by,
            closed_at=expired.closed_at,
            closure_reason=expired.closure_reason,
            retention_until=date.today() - timedelta(days=1),  # Expired yesterday
            metadata=expired.metadata,
        )
        svc._cases[case.id] = past_retention

        # Run archive
        archived = svc.archive_expired_cases(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c3",
        )

        assert case.id in archived
        assert svc._cases[case.id].status == CaseStatus.ARCHIVED

    def test_purge_archived_case(self, svc):
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.GENERAL,
            subject_employee_id=uuid4(),
            title="To purge",
            description="Test",
        )

        svc.add_note(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            content="Test note",
        )

        svc.add_evidence(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c3",
            case_id=case.id,
            filename="test.pdf",
            content_type="application/pdf",
            storage_path="/path/test.pdf",
        )

        svc.close_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c4",
            case_id=case.id,
            reason="Done",
        )

        svc.update_case_status(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c5",
            case_id=case.id,
            status=CaseStatus.ARCHIVED,
        )

        # Purge
        result = svc.purge_archived_data(
            actor_id="admin",
            actor_roles=["admin"],
            correlation_id="c6",
            case_id=case.id,
        )

        assert result is True
        assert case.id not in svc._cases
        assert all(n.case_id != case.id for n in svc._notes.values())
        assert all(e.case_id != case.id for e in svc._evidence.values())


# ---------------------- Audit Tests ----------------------


class TestAudit:
    def test_audit_trail(self, svc):
        emp_id = uuid4()
        case = svc.open_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c1",
            case_type=CaseType.DISCIPLINARY,
            subject_employee_id=emp_id,
            title="Audit test",
            description="Test",
        )

        svc.get_case(
            actor_id="ceo",
            actor_roles=["ceo"],
            case_id=case.id,
        )

        svc.add_note(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c2",
            case_id=case.id,
            content="Note",
        )

        svc.close_case(
            actor_id="hr",
            actor_roles=["hr"],
            correlation_id="c3",
            case_id=case.id,
            reason="Done",
        )

        audits = svc.list_audit_events(actor_roles=["auditor"])
        actions = [a.action for a in audits]
        assert "hr_case.open" in actions
        assert "hr_case.view" in actions
        assert "hr_case.add_note" in actions
        assert "hr_case.close" in actions

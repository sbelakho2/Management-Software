"""Tests for Recruiting/ATS-lite service (22.6 HRIS).

Covers:
- Job requisitions
- Candidate pipeline
- Interviews
- Offer letters
- RBAC and PII controls
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.hr.recruiting import (
    CandidateStatus,
    InterviewResult,
    InterviewType,
    OfferStatus,
    RecruitingService,
    RequisitionStatus,
)


# ---------------------- Fixtures ----------------------


@pytest.fixture
def svc() -> RecruitingService:
    return RecruitingService()


@pytest.fixture
def svc_with_open_req(svc: RecruitingService) -> RecruitingService:
    """Service with an open requisition."""
    req = svc.create_requisition(
        actor_id="hr1",
        actor_roles=["hr"],
        correlation_id="setup",
        title="Software Engineer",
        department="Engineering",
        location="Remote",
        headcount=2,
    )
    svc.submit_requisition(
        actor_id="hr1",
        actor_roles=["hr"],
        correlation_id="setup",
        requisition_id=req.id,
    )
    svc.approve_requisition(
        actor_id="exec1",
        actor_roles=["exec"],
        correlation_id="setup",
        requisition_id=req.id,
    )
    svc.open_requisition(
        actor_id="hr1",
        actor_roles=["hr"],
        correlation_id="setup",
        requisition_id=req.id,
    )
    return svc


# ---------------------- RBAC Tests ----------------------


class TestRBAC:
    def test_unauthorized_requisition_create(self, svc: RecruitingService):
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.create_requisition(
                actor_id="op",
                actor_roles=["operator"],
                correlation_id="c1",
                title="Test",
                department="Test",
                location="Test",
            )

    def test_unauthorized_requisition_approve(self, svc: RecruitingService):
        req = svc.create_requisition(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            title="Test",
            department="Test",
            location="Test",
        )
        svc.submit_requisition(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            requisition_id=req.id,
        )

        with pytest.raises(PermissionError, match="Approval role required"):
            svc.approve_requisition(
                actor_id="op",
                actor_roles=["supervisor"],  # supervisor can't approve reqs
                correlation_id="c3",
                requisition_id=req.id,
            )

    def test_unauthorized_pii_access(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
        )

        # Supervisor can list but not see PII
        candidates = svc.list_candidates(
            actor_roles=["supervisor"], requisition_id=req.id
        )
        assert len(candidates) == 1
        assert "****" in candidates[0].email  # Masked

        # Requesting PII without role should fail
        with pytest.raises(PermissionError, match="PII access role required"):
            svc.list_candidates(
                actor_roles=["supervisor"], requisition_id=req.id, include_pii=True
            )


# ---------------------- Requisition Tests ----------------------


class TestRequisitions:
    def test_create_requisition(self, svc: RecruitingService):
        req = svc.create_requisition(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            title="Software Engineer",
            department="Engineering",
            location="Remote",
            headcount=2,
            min_salary=Decimal("50000"),
            max_salary=Decimal("80000"),
            currency="EUR",
            skills=["Python", "SQL"],
        )

        assert req.title == "Software Engineer"
        assert req.department == "Engineering"
        assert req.status == RequisitionStatus.DRAFT
        assert req.headcount == 2
        assert req.min_salary == Decimal("50000")
        assert "Python" in req.skills

    def test_requisition_workflow(self, svc: RecruitingService):
        req = svc.create_requisition(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            title="Product Manager",
            department="Product",
            location="NYC",
        )
        assert req.status == RequisitionStatus.DRAFT

        # Submit
        req = svc.submit_requisition(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            requisition_id=req.id,
        )
        assert req.status == RequisitionStatus.PENDING_APPROVAL

        # Approve
        req = svc.approve_requisition(
            actor_id="ceo1",
            actor_roles=["ceo"],
            correlation_id="c3",
            requisition_id=req.id,
        )
        assert req.status == RequisitionStatus.APPROVED
        assert req.approved_by == "ceo1"

        # Open
        req = svc.open_requisition(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c4",
            requisition_id=req.id,
        )
        assert req.status == RequisitionStatus.OPEN

    def test_requisition_validation(self, svc: RecruitingService):
        with pytest.raises(ValueError, match="Title required"):
            svc.create_requisition(
                actor_id="hr1",
                actor_roles=["hr"],
                correlation_id="c1",
                title="",
                department="Test",
                location="Test",
            )

        with pytest.raises(ValueError, match="Headcount must be >= 1"):
            svc.create_requisition(
                actor_id="hr1",
                actor_roles=["hr"],
                correlation_id="c1",
                title="Test",
                department="Test",
                location="Test",
                headcount=0,
            )


# ---------------------- Candidate Tests ----------------------


class TestCandidates:
    def test_add_candidate(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="+1987654321",
            source="LinkedIn",
            years_experience=5,
            skills=["Python", "Django"],
        )

        assert candidate.first_name == "Jane"
        assert candidate.status == CandidateStatus.NEW
        assert candidate.source == "LinkedIn"

    def test_candidate_pipeline_advancement(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Bob",
            last_name="Johnson",
            email="bob@example.com",
        )
        assert candidate.status == CandidateStatus.NEW

        # Advance through pipeline
        candidate = svc.advance_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            new_status=CandidateStatus.SCREENING,
        )
        assert candidate.status == CandidateStatus.SCREENING

        candidate = svc.advance_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c3",
            candidate_id=candidate.id,
            new_status=CandidateStatus.INTERVIEW,
        )
        assert candidate.status == CandidateStatus.INTERVIEW

    def test_reject_candidate(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Alice",
            last_name="Brown",
            email="alice@example.com",
        )

        candidate = svc.reject_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            reason="Not enough experience",
        )

        assert candidate.status == CandidateStatus.REJECTED
        assert candidate.rejection_reason == "Not enough experience"

    def test_pii_masking(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
        )

        # Without PII flag (masked)
        candidates = svc.list_candidates(actor_roles=["hr"], requisition_id=req.id)
        assert "****" in candidates[0].email
        assert candidates[0].resume_url is None

        # With PII flag (full)
        candidates_pii = svc.list_candidates(
            actor_roles=["hr"], requisition_id=req.id, include_pii=True
        )
        assert candidates_pii[0].email == "john.doe@example.com"


# ---------------------- Interview Tests ----------------------


class TestInterviews:
    def test_schedule_interview(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Test",
            last_name="Candidate",
            email="test@example.com",
        )

        interview = svc.schedule_interview(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            interview_type=InterviewType.PHONE,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
            duration_minutes=30,
            interviewer_ids=[uuid4()],
        )

        assert interview.interview_type == InterviewType.PHONE
        assert interview.result == InterviewResult.PENDING
        assert interview.duration_minutes == 30

        # Candidate should be moved to interview
        updated = svc.get_candidate(actor_roles=["hr"], candidate_id=candidate.id)
        assert updated.status == CandidateStatus.INTERVIEW

    def test_complete_interview(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Test",
            last_name="Candidate",
            email="test@example.com",
        )

        interview = svc.schedule_interview(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            interview_type=InterviewType.TECHNICAL,
            scheduled_at=datetime.now(timezone.utc),
        )

        completed = svc.complete_interview(
            actor_id="interviewer1",
            actor_roles=["hr"],
            correlation_id="c3",
            interview_id=interview.id,
            result=InterviewResult.STRONG_PASS,
            feedback="Great technical skills, excellent communication",
            scores={"technical": 5, "communication": 4},
        )

        assert completed.result == InterviewResult.STRONG_PASS
        assert completed.completed_at is not None
        assert completed.scores["technical"] == 5


# ---------------------- Offer Tests ----------------------


class TestOffers:
    def test_create_and_approve_offer(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Test",
            last_name="Hire",
            email="hire@example.com",
        )

        offer = svc.create_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            base_salary=Decimal("75000"),
            currency="EUR",
            bonus_percent=Decimal("10"),
            start_date=date(2026, 3, 1),
            department="Engineering",
        )

        assert offer.status == OfferStatus.DRAFT
        assert offer.base_salary == Decimal("75000")

        # Candidate should be in offer stage
        updated = svc.get_candidate(actor_roles=["hr"], candidate_id=candidate.id)
        assert updated.status == CandidateStatus.OFFER

        # Approve
        offer = svc.approve_offer(
            actor_id="exec1",
            actor_roles=["exec"],
            correlation_id="c3",
            offer_id=offer.id,
        )
        assert offer.status == OfferStatus.APPROVED

    def test_offer_acceptance_flow(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="New",
            last_name="Hire",
            email="newhire@example.com",
        )

        offer = svc.create_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            base_salary=Decimal("60000"),
        )

        svc.approve_offer(
            actor_id="exec1",
            actor_roles=["exec"],
            correlation_id="c3",
            offer_id=offer.id,
        )

        offer = svc.send_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c4",
            offer_id=offer.id,
        )
        assert offer.status == OfferStatus.SENT
        assert offer.sent_at is not None

        # Accept
        offer = svc.record_offer_response(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c5",
            offer_id=offer.id,
            accepted=True,
        )
        assert offer.status == OfferStatus.ACCEPTED

        # Candidate should be hired
        candidate = svc.get_candidate(actor_roles=["hr"], candidate_id=candidate.id)
        assert candidate.status == CandidateStatus.HIRED

    def test_offer_decline(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Maybe",
            last_name="Hire",
            email="maybe@example.com",
        )

        offer = svc.create_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            base_salary=Decimal("50000"),
        )
        svc.approve_offer(
            actor_id="exec1",
            actor_roles=["exec"],
            correlation_id="c3",
            offer_id=offer.id,
        )
        svc.send_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c4",
            offer_id=offer.id,
        )

        # Decline
        offer = svc.record_offer_response(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c5",
            offer_id=offer.id,
            accepted=False,
            decline_reason="Accepted another offer",
        )

        assert offer.status == OfferStatus.DECLINED
        assert offer.decline_reason == "Accepted another offer"

    def test_offer_salary_masking(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]

        candidate = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Test",
            last_name="Offer",
            email="offer@example.com",
        )

        svc.create_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=candidate.id,
            base_salary=Decimal("100000"),
            bonus_percent=Decimal("15"),
        )

        # Without salary flag (masked)
        offers = svc.list_offers(actor_roles=["supervisor"], candidate_id=candidate.id)
        assert offers[0].base_salary == Decimal("0")
        assert offers[0].bonus_percent is None

        # With salary flag (full)
        offers_full = svc.list_offers(
            actor_roles=["hr"], candidate_id=candidate.id, include_salary=True
        )
        assert offers_full[0].base_salary == Decimal("100000")

    def test_requisition_filled_on_hire(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req
        req = svc.list_requisitions(actor_roles=["hr"])[0]
        # headcount is 2

        # Hire first candidate
        c1 = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c1",
            requisition_id=req.id,
            first_name="Hire",
            last_name="One",
            email="hire1@example.com",
        )
        o1 = svc.create_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c2",
            candidate_id=c1.id,
            base_salary=Decimal("50000"),
        )
        svc.approve_offer(actor_id="exec1", actor_roles=["exec"], correlation_id="c3", offer_id=o1.id)
        svc.send_offer(actor_id="hr1", actor_roles=["hr"], correlation_id="c4", offer_id=o1.id)
        svc.record_offer_response(
            actor_id="hr1", actor_roles=["hr"], correlation_id="c5", offer_id=o1.id, accepted=True
        )

        req = svc.get_requisition(actor_roles=["hr"], requisition_id=req.id)
        assert req.status == RequisitionStatus.OPEN  # Still open, need 2

        # Hire second candidate
        c2 = svc.add_candidate(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c6",
            requisition_id=req.id,
            first_name="Hire",
            last_name="Two",
            email="hire2@example.com",
        )
        o2 = svc.create_offer(
            actor_id="hr1",
            actor_roles=["hr"],
            correlation_id="c7",
            candidate_id=c2.id,
            base_salary=Decimal("55000"),
        )
        svc.approve_offer(actor_id="exec1", actor_roles=["exec"], correlation_id="c8", offer_id=o2.id)
        svc.send_offer(actor_id="hr1", actor_roles=["hr"], correlation_id="c9", offer_id=o2.id)
        svc.record_offer_response(
            actor_id="hr1", actor_roles=["hr"], correlation_id="c10", offer_id=o2.id, accepted=True
        )

        req = svc.get_requisition(actor_roles=["hr"], requisition_id=req.id)
        assert req.status == RequisitionStatus.FILLED


# ---------------------- Audit Tests ----------------------


class TestAudit:
    def test_audit_trail(self, svc_with_open_req: RecruitingService):
        svc = svc_with_open_req

        audits = svc.list_audit_events(actor_roles=["hr"])
        # Should have events from fixture setup
        assert len(audits) >= 4  # create, submit, approve, open
        assert any(a.action == "recruiting.requisition.create" for a in audits)
        assert any(a.action == "recruiting.requisition.approve" for a in audits)

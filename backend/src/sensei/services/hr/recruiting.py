"""Recruiting / ATS-lite Service (Development Plan 22.6 HRIS).

Implements:
- Requisitions: job requisitions with approval workflow.
- Candidate Pipeline: track candidates through hiring stages.
- Interviews: schedule and record interview feedback.
- Offer Letters: generate and track offer acceptance with PII controls.

State is persisted via the service_state table for DB-backed continuity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


# ---------------------- Enums ----------------------


class RequisitionStatus(str, Enum):
    """Job requisition lifecycle states."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    OPEN = "open"
    ON_HOLD = "on_hold"
    FILLED = "filled"
    CANCELLED = "cancelled"


class CandidateStatus(str, Enum):
    """Candidate pipeline stages."""

    NEW = "new"
    SCREENING = "screening"
    PHONE_SCREEN = "phone_screen"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    REFERENCE_CHECK = "reference_check"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class InterviewType(str, Enum):
    """Types of interviews."""

    PHONE = "phone"
    VIDEO = "video"
    ONSITE = "onsite"
    TECHNICAL = "technical"
    PANEL = "panel"
    FINAL = "final"


class InterviewResult(str, Enum):
    """Interview outcome."""

    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"
    STRONG_PASS = "strong_pass"
    NEEDS_DISCUSSION = "needs_discussion"


class OfferStatus(str, Enum):
    """Offer letter status."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    RESCINDED = "rescinded"


# ---------------------- RBAC ----------------------


_HR_WRITE_ROLES: set[str] = {"admin", "hr", "gm"}
_HR_READ_ROLES: set[str] = {"admin", "hr", "gm", "exec", "ceo", "supervisor", "hiring_manager"}
_APPROVE_ROLES: set[str] = {"admin", "hr", "gm", "exec", "ceo"}
_PII_ACCESS_ROLES: set[str] = {"admin", "hr"}  # Restricted PII access


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mask_pii(value: str, visible_chars: int = 4) -> str:
    """Mask PII data, showing only last N characters."""
    if not value or len(value) <= visible_chars:
        return "****"
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _encode_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _decode_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _encode_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _encode_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _encode_audit_event(event: "AuditEvent") -> dict[str, Any]:
    return {
        "id": str(event.id),
        "actor_id": event.actor_id,
        "actor_roles": list(event.actor_roles),
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "correlation_id": event.correlation_id,
        "timestamp": event.timestamp.isoformat(),
        "metadata": event.metadata,
    }


def _decode_audit_event(data: dict[str, Any]) -> "AuditEvent":
    return AuditEvent(
        id=UUID(data["id"]),
        actor_id=data["actor_id"],
        actor_roles=frozenset(data.get("actor_roles", [])),
        action=data["action"],
        entity_type=data["entity_type"],
        entity_id=data["entity_id"],
        correlation_id=data.get("correlation_id", ""),
        timestamp=datetime.fromisoformat(data["timestamp"]),
        metadata=data.get("metadata", {}) or {},
    )


def _encode_requisition(req: "JobRequisition") -> dict[str, Any]:
    return {
        "id": str(req.id),
        "title": req.title,
        "department": req.department,
        "location": req.location,
        "employment_type": req.employment_type,
        "status": req.status.value,
        "headcount": req.headcount,
        "hiring_manager_id": str(req.hiring_manager_id) if req.hiring_manager_id else None,
        "min_salary": _encode_decimal(req.min_salary),
        "max_salary": _encode_decimal(req.max_salary),
        "currency": req.currency,
        "job_description": req.job_description,
        "requirements": req.requirements,
        "skills": req.skills,
        "target_start_date": _encode_date(req.target_start_date),
        "approved_by": req.approved_by,
        "approved_at": _encode_datetime(req.approved_at),
        "created_at": req.created_at.isoformat(),
        "created_by": req.created_by,
        "correlation_id": req.correlation_id,
        "metadata": req.metadata,
    }


def _decode_requisition(data: dict[str, Any]) -> "JobRequisition":
    return JobRequisition(
        id=UUID(data["id"]),
        title=data["title"],
        department=data["department"],
        location=data["location"],
        employment_type=data.get("employment_type", "full-time"),
        status=RequisitionStatus(data["status"]),
        headcount=int(data.get("headcount", 1)),
        hiring_manager_id=UUID(data["hiring_manager_id"]) if data.get("hiring_manager_id") else None,
        min_salary=_decode_decimal(data.get("min_salary")),
        max_salary=_decode_decimal(data.get("max_salary")),
        currency=data.get("currency", "EUR"),
        job_description=data.get("job_description", ""),
        requirements=data.get("requirements", []) or [],
        skills=data.get("skills", []) or [],
        target_start_date=_decode_date(data.get("target_start_date")),
        approved_by=data.get("approved_by"),
        approved_at=_decode_datetime(data.get("approved_at")),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        correlation_id=data.get("correlation_id", ""),
        metadata=data.get("metadata", {}) or {},
    )


def _encode_candidate(candidate: "Candidate") -> dict[str, Any]:
    return {
        "id": str(candidate.id),
        "requisition_id": str(candidate.requisition_id),
        "status": candidate.status.value,
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "source": candidate.source,
        "resume_url": candidate.resume_url,
        "cover_letter_url": candidate.cover_letter_url,
        "linkedin_url": candidate.linkedin_url,
        "current_company": candidate.current_company,
        "current_title": candidate.current_title,
        "years_experience": candidate.years_experience,
        "skills": candidate.skills,
        "notes": candidate.notes,
        "rating": candidate.rating,
        "rejection_reason": candidate.rejection_reason,
        "created_at": candidate.created_at.isoformat(),
        "created_by": candidate.created_by,
        "correlation_id": candidate.correlation_id,
    }


def _decode_candidate(data: dict[str, Any]) -> "Candidate":
    return Candidate(
        id=UUID(data["id"]),
        requisition_id=UUID(data["requisition_id"]),
        status=CandidateStatus(data["status"]),
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        source=data.get("source", ""),
        resume_url=data.get("resume_url"),
        cover_letter_url=data.get("cover_letter_url"),
        linkedin_url=data.get("linkedin_url"),
        current_company=data.get("current_company", ""),
        current_title=data.get("current_title", ""),
        years_experience=int(data.get("years_experience", 0)),
        skills=data.get("skills", []) or [],
        notes=data.get("notes", ""),
        rating=int(data.get("rating", 0)),
        rejection_reason=data.get("rejection_reason", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        correlation_id=data.get("correlation_id", ""),
    )


def _encode_interview(interview: "Interview") -> dict[str, Any]:
    return {
        "id": str(interview.id),
        "candidate_id": str(interview.candidate_id),
        "requisition_id": str(interview.requisition_id),
        "interview_type": interview.interview_type.value,
        "scheduled_at": interview.scheduled_at.isoformat(),
        "duration_minutes": interview.duration_minutes,
        "location": interview.location,
        "interviewer_ids": [str(iid) for iid in interview.interviewer_ids],
        "result": interview.result.value,
        "feedback": interview.feedback,
        "scores": interview.scores,
        "completed_at": _encode_datetime(interview.completed_at),
        "created_at": interview.created_at.isoformat(),
        "created_by": interview.created_by,
        "correlation_id": interview.correlation_id,
    }


def _decode_interview(data: dict[str, Any]) -> "Interview":
    return Interview(
        id=UUID(data["id"]),
        candidate_id=UUID(data["candidate_id"]),
        requisition_id=UUID(data["requisition_id"]),
        interview_type=InterviewType(data["interview_type"]),
        scheduled_at=datetime.fromisoformat(data["scheduled_at"]),
        duration_minutes=int(data.get("duration_minutes", 60)),
        location=data.get("location", ""),
        interviewer_ids=[UUID(iid) for iid in data.get("interviewer_ids", [])],
        result=InterviewResult(data.get("result", InterviewResult.PENDING.value)),
        feedback=data.get("feedback", ""),
        scores=data.get("scores", {}) or {},
        completed_at=_decode_datetime(data.get("completed_at")),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        correlation_id=data.get("correlation_id", ""),
    )


def _encode_offer(offer: "OfferLetter") -> dict[str, Any]:
    return {
        "id": str(offer.id),
        "candidate_id": str(offer.candidate_id),
        "requisition_id": str(offer.requisition_id),
        "status": offer.status.value,
        "base_salary": _encode_decimal(offer.base_salary),
        "currency": offer.currency,
        "bonus_percent": _encode_decimal(offer.bonus_percent),
        "equity_shares": offer.equity_shares,
        "start_date": _encode_date(offer.start_date),
        "employment_type": offer.employment_type,
        "reporting_to": offer.reporting_to,
        "department": offer.department,
        "valid_until": _encode_date(offer.valid_until),
        "approved_by": offer.approved_by,
        "approved_at": _encode_datetime(offer.approved_at),
        "sent_at": _encode_datetime(offer.sent_at),
        "response_at": _encode_datetime(offer.response_at),
        "decline_reason": offer.decline_reason,
        "created_at": offer.created_at.isoformat(),
        "created_by": offer.created_by,
        "correlation_id": offer.correlation_id,
    }


def _decode_offer(data: dict[str, Any]) -> "OfferLetter":
    return OfferLetter(
        id=UUID(data["id"]),
        candidate_id=UUID(data["candidate_id"]),
        requisition_id=UUID(data["requisition_id"]),
        status=OfferStatus(data["status"]),
        base_salary=Decimal(data.get("base_salary", "0")),
        currency=data.get("currency", "EUR"),
        bonus_percent=_decode_decimal(data.get("bonus_percent")),
        equity_shares=data.get("equity_shares"),
        start_date=_decode_date(data.get("start_date")),
        employment_type=data.get("employment_type", "full-time"),
        reporting_to=data.get("reporting_to", ""),
        department=data.get("department", ""),
        valid_until=_decode_date(data.get("valid_until")),
        approved_by=data.get("approved_by"),
        approved_at=_decode_datetime(data.get("approved_at")),
        sent_at=_decode_datetime(data.get("sent_at")),
        response_at=_decode_datetime(data.get("response_at")),
        decline_reason=data.get("decline_reason", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        correlation_id=data.get("correlation_id", ""),
    )


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
class JobRequisition:
    """A job opening request."""

    id: UUID
    title: str
    department: str
    location: str
    employment_type: str  # full-time, part-time, contract
    status: RequisitionStatus
    headcount: int
    hiring_manager_id: UUID | None = None
    min_salary: Decimal | None = None
    max_salary: Decimal | None = None
    currency: str = "EUR"
    job_description: str = ""
    requirements: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    target_start_date: date | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Candidate:
    """A job candidate (PII-sensitive)."""

    id: UUID
    requisition_id: UUID
    status: CandidateStatus
    # PII fields
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    # Non-PII
    source: str = ""  # where they applied from
    resume_url: str | None = None
    cover_letter_url: str | None = None
    linkedin_url: str | None = None
    current_company: str = ""
    current_title: str = ""
    years_experience: int = 0
    skills: list[str] = field(default_factory=list)
    notes: str = ""
    rating: int = 0  # 1-5 stars
    rejection_reason: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    correlation_id: str = ""

    def masked(self) -> "Candidate":
        """Return a copy with PII masked."""
        return Candidate(
            id=self.id,
            requisition_id=self.requisition_id,
            status=self.status,
            first_name=_mask_pii(self.first_name, 1),
            last_name=_mask_pii(self.last_name, 1),
            email=_mask_pii(self.email, 4),
            phone=_mask_pii(self.phone, 4),
            source=self.source,
            resume_url=None,  # Hide URL
            cover_letter_url=None,
            linkedin_url=None,
            current_company=self.current_company,
            current_title=self.current_title,
            years_experience=self.years_experience,
            skills=self.skills,
            notes=self.notes,
            rating=self.rating,
            rejection_reason=self.rejection_reason,
            created_at=self.created_at,
            created_by=self.created_by,
            correlation_id=self.correlation_id,
        )


@dataclass
class Interview:
    """A scheduled interview."""

    id: UUID
    candidate_id: UUID
    requisition_id: UUID
    interview_type: InterviewType
    scheduled_at: datetime
    duration_minutes: int = 60
    location: str = ""  # room or video link
    interviewer_ids: list[UUID] = field(default_factory=list)
    result: InterviewResult = InterviewResult.PENDING
    feedback: str = ""
    scores: dict[str, int] = field(default_factory=dict)  # category -> score
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    correlation_id: str = ""


@dataclass
class OfferLetter:
    """An offer letter for a candidate."""

    id: UUID
    candidate_id: UUID
    requisition_id: UUID
    status: OfferStatus
    # Compensation (PII-sensitive)
    base_salary: Decimal
    currency: str = "EUR"
    bonus_percent: Decimal | None = None
    equity_shares: int | None = None
    # Terms
    start_date: date | None = None
    employment_type: str = "full-time"
    reporting_to: str = ""
    department: str = ""
    # Workflow
    valid_until: date | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    response_at: datetime | None = None
    decline_reason: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    correlation_id: str = ""

    def masked(self) -> "OfferLetter":
        """Return a copy with salary masked."""
        return OfferLetter(
            id=self.id,
            candidate_id=self.candidate_id,
            requisition_id=self.requisition_id,
            status=self.status,
            base_salary=Decimal("0"),  # Masked
            currency=self.currency,
            bonus_percent=None,
            equity_shares=None,
            start_date=self.start_date,
            employment_type=self.employment_type,
            reporting_to=self.reporting_to,
            department=self.department,
            valid_until=self.valid_until,
            approved_by=self.approved_by,
            approved_at=self.approved_at,
            sent_at=self.sent_at,
            response_at=self.response_at,
            decline_reason=self.decline_reason,
            created_at=self.created_at,
            created_by=self.created_by,
            correlation_id=self.correlation_id,
        )


# ---------------------- Service ----------------------


class RecruitingService(PersistentServiceMixin):
    """In-memory recruiting/ATS service with RBAC and PII controls."""

    SERVICE_NAME = "recruiting"

    def __init__(self) -> None:
        self._requisitions: dict[UUID, JobRequisition] = {}
        self._candidates: dict[UUID, Candidate] = {}
        self._interviews: dict[UUID, Interview] = {}
        self._offers: dict[UUID, OfferLetter] = {}
        self._audit: list[AuditEvent] = []
        self._state_loaded = False

    async def load_from_db(self) -> None:
        """Hydrate service state from the service_state table."""
        if self._state_loaded:
            return

        requisitions_data = await self.load_state(_DEFAULT_TENANT_ID, "requisitions") or {}
        candidates_data = await self.load_state(_DEFAULT_TENANT_ID, "candidates") or {}
        interviews_data = await self.load_state(_DEFAULT_TENANT_ID, "interviews") or {}
        offers_data = await self.load_state(_DEFAULT_TENANT_ID, "offers") or {}
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []

        self._requisitions = {UUID(rid): _decode_requisition(r) for rid, r in requisitions_data.items()}
        self._candidates = {UUID(cid): _decode_candidate(c) for cid, c in candidates_data.items()}
        self._interviews = {UUID(iid): _decode_interview(i) for iid, i in interviews_data.items()}
        self._offers = {UUID(oid): _decode_offer(o) for oid, o in offers_data.items()}
        self._audit = [_decode_audit_event(a) for a in audit_data]

        self._state_loaded = True

    async def persist_all(self) -> None:
        """Persist all service state to the service_state table."""
        requisitions_data = {str(rid): _encode_requisition(r) for rid, r in self._requisitions.items()}
        candidates_data = {str(cid): _encode_candidate(c) for cid, c in self._candidates.items()}
        interviews_data = {str(iid): _encode_interview(i) for iid, i in self._interviews.items()}
        offers_data = {str(oid): _encode_offer(o) for oid, o in self._offers.items()}
        audit_data = [_encode_audit_event(a) for a in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "requisitions", requisitions_data)
        await self.save_state(_DEFAULT_TENANT_ID, "candidates", candidates_data)
        await self.save_state(_DEFAULT_TENANT_ID, "interviews", interviews_data)
        await self.save_state(_DEFAULT_TENANT_ID, "offers", offers_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

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

    # ---------------------- Requisitions ----------------------

    def create_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        title: str,
        department: str,
        location: str,
        employment_type: str = "full-time",
        headcount: int = 1,
        hiring_manager_id: UUID | None = None,
        min_salary: Decimal | None = None,
        max_salary: Decimal | None = None,
        currency: str = "EUR",
        job_description: str = "",
        requirements: list[str] | None = None,
        skills: list[str] | None = None,
        target_start_date: date | None = None,
    ) -> JobRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not title or not title.strip():
            raise ValueError("Title required")
        if not department or not department.strip():
            raise ValueError("Department required")
        if headcount < 1:
            raise ValueError("Headcount must be >= 1")

        req = JobRequisition(
            id=uuid4(),
            title=title.strip(),
            department=department.strip(),
            location=location.strip(),
            employment_type=employment_type,
            status=RequisitionStatus.DRAFT,
            headcount=headcount,
            hiring_manager_id=hiring_manager_id,
            min_salary=Decimal(str(min_salary)) if min_salary else None,
            max_salary=Decimal(str(max_salary)) if max_salary else None,
            currency=currency.upper(),
            job_description=job_description,
            requirements=requirements or [],
            skills=skills or [],
            target_start_date=target_start_date,
            created_by=actor_id,
            correlation_id=correlation_id,
        )

        self._requisitions[req.id] = req
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.requisition.create",
            entity_type="requisition",
            entity_id=str(req.id),
            correlation_id=correlation_id,
            metadata={"title": title, "department": department},
        )
        return req

    def submit_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        requisition_id: UUID,
    ) -> JobRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        req = self._requisitions.get(requisition_id)
        if not req:
            raise ValueError("Requisition not found")
        if req.status != RequisitionStatus.DRAFT:
            raise ValueError("Only draft requisitions can be submitted")

        req.status = RequisitionStatus.PENDING_APPROVAL

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.requisition.submit",
            entity_type="requisition",
            entity_id=str(requisition_id),
            correlation_id=correlation_id,
        )
        return req

    def approve_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        requisition_id: UUID,
    ) -> JobRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _APPROVE_ROLES, "Approval role required")

        req = self._requisitions.get(requisition_id)
        if not req:
            raise ValueError("Requisition not found")
        if req.status != RequisitionStatus.PENDING_APPROVAL:
            raise ValueError("Only pending requisitions can be approved")

        req.status = RequisitionStatus.APPROVED
        req.approved_by = actor_id
        req.approved_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.requisition.approve",
            entity_type="requisition",
            entity_id=str(requisition_id),
            correlation_id=correlation_id,
        )
        return req

    def open_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        requisition_id: UUID,
    ) -> JobRequisition:
        """Open a requisition for applications."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        req = self._requisitions.get(requisition_id)
        if not req:
            raise ValueError("Requisition not found")
        if req.status != RequisitionStatus.APPROVED:
            raise ValueError("Only approved requisitions can be opened")

        req.status = RequisitionStatus.OPEN

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.requisition.open",
            entity_type="requisition",
            entity_id=str(requisition_id),
            correlation_id=correlation_id,
        )
        return req

    def list_requisitions(
        self,
        *,
        actor_roles: Iterable[str],
        status: RequisitionStatus | None = None,
        department: str | None = None,
    ) -> list[JobRequisition]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        reqs = list(self._requisitions.values())
        if status:
            reqs = [r for r in reqs if r.status == status]
        if department:
            reqs = [r for r in reqs if r.department == department]
        return reqs

    def get_requisition(
        self, *, actor_roles: Iterable[str], requisition_id: UUID
    ) -> JobRequisition | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return self._requisitions.get(requisition_id)

    # ---------------------- Candidates ----------------------

    def add_candidate(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        requisition_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        source: str = "",
        resume_url: str | None = None,
        current_company: str = "",
        current_title: str = "",
        years_experience: int = 0,
        skills: list[str] | None = None,
    ) -> Candidate:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        req = self._requisitions.get(requisition_id)
        if not req:
            raise ValueError("Requisition not found")
        if req.status != RequisitionStatus.OPEN:
            raise ValueError("Requisition is not open")

        if not first_name or not first_name.strip():
            raise ValueError("First name required")
        if not last_name or not last_name.strip():
            raise ValueError("Last name required")
        if not email or not email.strip():
            raise ValueError("Email required")

        candidate = Candidate(
            id=uuid4(),
            requisition_id=requisition_id,
            status=CandidateStatus.NEW,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email.strip().lower(),
            phone=phone.strip(),
            source=source,
            resume_url=resume_url,
            current_company=current_company,
            current_title=current_title,
            years_experience=years_experience,
            skills=skills or [],
            created_by=actor_id,
            correlation_id=correlation_id,
        )

        self._candidates[candidate.id] = candidate
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.candidate.add",
            entity_type="candidate",
            entity_id=str(candidate.id),
            correlation_id=correlation_id,
            metadata={"requisition_id": str(requisition_id)},
        )
        return candidate

    def advance_candidate(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        candidate_id: UUID,
        new_status: CandidateStatus,
    ) -> Candidate:
        """Move candidate to a new pipeline stage."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")

        if candidate.status in (CandidateStatus.HIRED, CandidateStatus.REJECTED, CandidateStatus.WITHDRAWN):
            raise ValueError(f"Cannot advance from {candidate.status.value} status")

        old_status = candidate.status
        candidate.status = new_status

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.candidate.advance",
            entity_type="candidate",
            entity_id=str(candidate_id),
            correlation_id=correlation_id,
            metadata={"from": old_status.value, "to": new_status.value},
        )
        return candidate

    def reject_candidate(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        candidate_id: UUID,
        reason: str,
    ) -> Candidate:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not reason or not reason.strip():
            raise ValueError("Rejection reason required")

        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")

        candidate.status = CandidateStatus.REJECTED
        candidate.rejection_reason = reason

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.candidate.reject",
            entity_type="candidate",
            entity_id=str(candidate_id),
            correlation_id=correlation_id,
            metadata={"reason": reason},
        )
        return candidate

    def list_candidates(
        self,
        *,
        actor_roles: Iterable[str],
        requisition_id: UUID | None = None,
        status: CandidateStatus | None = None,
        include_pii: bool = False,
    ) -> list[Candidate]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        candidates = list(self._candidates.values())
        if requisition_id:
            candidates = [c for c in candidates if c.requisition_id == requisition_id]
        if status:
            candidates = [c for c in candidates if c.status == status]

        # PII masking if not authorized
        if include_pii:
            _require_any(roles, _PII_ACCESS_ROLES, "PII access role required")
            return candidates
        return [c.masked() for c in candidates]

    def get_candidate(
        self,
        *,
        actor_roles: Iterable[str],
        candidate_id: UUID,
        include_pii: bool = False,
    ) -> Candidate | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return None

        if include_pii:
            _require_any(roles, _PII_ACCESS_ROLES, "PII access role required")
            return candidate
        return candidate.masked()

    # ---------------------- Interviews ----------------------

    def schedule_interview(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        candidate_id: UUID,
        interview_type: InterviewType,
        scheduled_at: datetime,
        duration_minutes: int = 60,
        location: str = "",
        interviewer_ids: list[UUID] | None = None,
    ) -> Interview:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")

        interview = Interview(
            id=uuid4(),
            candidate_id=candidate_id,
            requisition_id=candidate.requisition_id,
            interview_type=interview_type,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            location=location,
            interviewer_ids=interviewer_ids or [],
            created_by=actor_id,
            correlation_id=correlation_id,
        )

        self._interviews[interview.id] = interview

        # Advance candidate to interview if not already
        if candidate.status in (CandidateStatus.NEW, CandidateStatus.SCREENING, CandidateStatus.PHONE_SCREEN):
            candidate.status = CandidateStatus.INTERVIEW

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.interview.schedule",
            entity_type="interview",
            entity_id=str(interview.id),
            correlation_id=correlation_id,
            metadata={"type": interview_type.value, "candidate_id": str(candidate_id)},
        )
        return interview

    def complete_interview(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        interview_id: UUID,
        result: InterviewResult,
        feedback: str = "",
        scores: dict[str, int] | None = None,
    ) -> Interview:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        interview = self._interviews.get(interview_id)
        if not interview:
            raise ValueError("Interview not found")
        if interview.result != InterviewResult.PENDING:
            raise ValueError("Interview already completed")

        interview.result = result
        interview.feedback = feedback
        interview.scores = scores or {}
        interview.completed_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.interview.complete",
            entity_type="interview",
            entity_id=str(interview_id),
            correlation_id=correlation_id,
            metadata={"result": result.value},
        )
        return interview

    def list_interviews(
        self,
        *,
        actor_roles: Iterable[str],
        candidate_id: UUID | None = None,
        requisition_id: UUID | None = None,
    ) -> list[Interview]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        interviews = list(self._interviews.values())
        if candidate_id:
            interviews = [i for i in interviews if i.candidate_id == candidate_id]
        if requisition_id:
            interviews = [i for i in interviews if i.requisition_id == requisition_id]
        return interviews

    # ---------------------- Offers ----------------------

    def create_offer(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        candidate_id: UUID,
        base_salary: Decimal,
        currency: str = "EUR",
        bonus_percent: Decimal | None = None,
        equity_shares: int | None = None,
        start_date: date | None = None,
        employment_type: str = "full-time",
        reporting_to: str = "",
        department: str = "",
        valid_until: date | None = None,
    ) -> OfferLetter:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise ValueError("Candidate not found")

        if base_salary <= 0:
            raise ValueError("Base salary must be > 0")

        offer = OfferLetter(
            id=uuid4(),
            candidate_id=candidate_id,
            requisition_id=candidate.requisition_id,
            status=OfferStatus.DRAFT,
            base_salary=Decimal(str(base_salary)),
            currency=currency.upper(),
            bonus_percent=Decimal(str(bonus_percent)) if bonus_percent else None,
            equity_shares=equity_shares,
            start_date=start_date,
            employment_type=employment_type,
            reporting_to=reporting_to,
            department=department,
            valid_until=valid_until,
            created_by=actor_id,
            correlation_id=correlation_id,
        )

        self._offers[offer.id] = offer

        # Advance candidate to offer stage
        candidate.status = CandidateStatus.OFFER

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.offer.create",
            entity_type="offer",
            entity_id=str(offer.id),
            correlation_id=correlation_id,
            metadata={"candidate_id": str(candidate_id)},
        )
        return offer

    def approve_offer(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        offer_id: UUID,
    ) -> OfferLetter:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _APPROVE_ROLES, "Approval role required")

        offer = self._offers.get(offer_id)
        if not offer:
            raise ValueError("Offer not found")
        if offer.status != OfferStatus.DRAFT:
            raise ValueError("Only draft offers can be approved")

        offer.status = OfferStatus.APPROVED
        offer.approved_by = actor_id
        offer.approved_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.offer.approve",
            entity_type="offer",
            entity_id=str(offer_id),
            correlation_id=correlation_id,
        )
        return offer

    def send_offer(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        offer_id: UUID,
    ) -> OfferLetter:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        offer = self._offers.get(offer_id)
        if not offer:
            raise ValueError("Offer not found")
        if offer.status != OfferStatus.APPROVED:
            raise ValueError("Only approved offers can be sent")

        offer.status = OfferStatus.SENT
        offer.sent_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.offer.send",
            entity_type="offer",
            entity_id=str(offer_id),
            correlation_id=correlation_id,
        )
        return offer

    def record_offer_response(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        offer_id: UUID,
        accepted: bool,
        decline_reason: str = "",
    ) -> OfferLetter:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        offer = self._offers.get(offer_id)
        if not offer:
            raise ValueError("Offer not found")
        if offer.status != OfferStatus.SENT:
            raise ValueError("Only sent offers can have responses recorded")

        if accepted:
            offer.status = OfferStatus.ACCEPTED
            # Mark candidate as hired
            candidate = self._candidates.get(offer.candidate_id)
            if candidate:
                candidate.status = CandidateStatus.HIRED
                # Mark requisition as filled if headcount reached
                req = self._requisitions.get(offer.requisition_id)
                if req:
                    hired_count = sum(
                        1 for c in self._candidates.values()
                        if c.requisition_id == req.id and c.status == CandidateStatus.HIRED
                    )
                    if hired_count >= req.headcount:
                        req.status = RequisitionStatus.FILLED
        else:
            offer.status = OfferStatus.DECLINED
            offer.decline_reason = decline_reason

        offer.response_at = _utcnow()

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="recruiting.offer.response",
            entity_type="offer",
            entity_id=str(offer_id),
            correlation_id=correlation_id,
            metadata={"accepted": accepted},
        )
        return offer

    def list_offers(
        self,
        *,
        actor_roles: Iterable[str],
        candidate_id: UUID | None = None,
        requisition_id: UUID | None = None,
        include_salary: bool = False,
    ) -> list[OfferLetter]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        offers = list(self._offers.values())
        if candidate_id:
            offers = [o for o in offers if o.candidate_id == candidate_id]
        if requisition_id:
            offers = [o for o in offers if o.requisition_id == requisition_id]

        if include_salary:
            _require_any(roles, _PII_ACCESS_ROLES, "PII access role required")
            return offers
        return [o.masked() for o in offers]

    def get_offer(
        self,
        *,
        actor_roles: Iterable[str],
        offer_id: UUID,
        include_salary: bool = False,
    ) -> OfferLetter | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        offer = self._offers.get(offer_id)
        if not offer:
            return None

        if include_salary:
            _require_any(roles, _PII_ACCESS_ROLES, "PII access role required")
            return offer
        return offer.masked()

    # ---------------------- Async DB-backed wrappers ----------------------

    async def list_audit_events_async(self, **kwargs: Any) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(**kwargs)

    async def create_requisition_async(self, **kwargs: Any) -> JobRequisition:
        await self._ensure_loaded()
        req = self.create_requisition(**kwargs)
        await self.persist_all()
        return req

    async def submit_requisition_async(self, **kwargs: Any) -> JobRequisition:
        await self._ensure_loaded()
        req = self.submit_requisition(**kwargs)
        await self.persist_all()
        return req

    async def approve_requisition_async(self, **kwargs: Any) -> JobRequisition:
        await self._ensure_loaded()
        req = self.approve_requisition(**kwargs)
        await self.persist_all()
        return req

    async def open_requisition_async(self, **kwargs: Any) -> JobRequisition:
        await self._ensure_loaded()
        req = self.open_requisition(**kwargs)
        await self.persist_all()
        return req

    async def list_requisitions_async(self, **kwargs: Any) -> list[JobRequisition]:
        await self._ensure_loaded()
        return self.list_requisitions(**kwargs)

    async def get_requisition_async(self, **kwargs: Any) -> JobRequisition | None:
        await self._ensure_loaded()
        return self.get_requisition(**kwargs)

    async def add_candidate_async(self, **kwargs: Any) -> Candidate:
        await self._ensure_loaded()
        candidate = self.add_candidate(**kwargs)
        await self.persist_all()
        return candidate

    async def advance_candidate_async(self, **kwargs: Any) -> Candidate:
        await self._ensure_loaded()
        candidate = self.advance_candidate(**kwargs)
        await self.persist_all()
        return candidate

    async def reject_candidate_async(self, **kwargs: Any) -> Candidate:
        await self._ensure_loaded()
        candidate = self.reject_candidate(**kwargs)
        await self.persist_all()
        return candidate

    async def list_candidates_async(self, **kwargs: Any) -> list[Candidate]:
        await self._ensure_loaded()
        return self.list_candidates(**kwargs)

    async def get_candidate_async(self, **kwargs: Any) -> Candidate | None:
        await self._ensure_loaded()
        return self.get_candidate(**kwargs)

    async def schedule_interview_async(self, **kwargs: Any) -> Interview:
        await self._ensure_loaded()
        interview = self.schedule_interview(**kwargs)
        await self.persist_all()
        return interview

    async def complete_interview_async(self, **kwargs: Any) -> Interview:
        await self._ensure_loaded()
        interview = self.complete_interview(**kwargs)
        await self.persist_all()
        return interview

    async def list_interviews_async(self, **kwargs: Any) -> list[Interview]:
        await self._ensure_loaded()
        return self.list_interviews(**kwargs)

    async def create_offer_async(self, **kwargs: Any) -> OfferLetter:
        await self._ensure_loaded()
        offer = self.create_offer(**kwargs)
        await self.persist_all()
        return offer

    async def approve_offer_async(self, **kwargs: Any) -> OfferLetter:
        await self._ensure_loaded()
        offer = self.approve_offer(**kwargs)
        await self.persist_all()
        return offer

    async def send_offer_async(self, **kwargs: Any) -> OfferLetter:
        await self._ensure_loaded()
        offer = self.send_offer(**kwargs)
        await self.persist_all()
        return offer

    async def record_offer_response_async(self, **kwargs: Any) -> OfferLetter:
        await self._ensure_loaded()
        offer = self.record_offer_response(**kwargs)
        await self.persist_all()
        return offer

    async def list_offers_async(self, **kwargs: Any) -> list[OfferLetter]:
        await self._ensure_loaded()
        return self.list_offers(**kwargs)

    async def get_offer_async(self, **kwargs: Any) -> OfferLetter | None:
        await self._ensure_loaded()
        return self.get_offer(**kwargs)

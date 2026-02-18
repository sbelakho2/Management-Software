"""HR Case Management (Development Plan 22.6).

Implements:
- Case Types: disciplinary, grievance, investigation, accommodation, general.
- Restricted Access: strict PII controls with need-to-know RBAC.
- Evidence Handling: secure attachment storage with access logging.
- Retention Policy: automated cleanup per legal retention schedules.

This module is in-memory and pure-Python to match other services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class CaseType(str, Enum):
    DISCIPLINARY = "disciplinary"
    GRIEVANCE = "grievance"
    INVESTIGATION = "investigation"
    ACCOMMODATION = "accommodation"
    GENERAL = "general"


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    VERBAL_WARNING = "verbal_warning"
    WRITTEN_WARNING = "written_warning"
    FINAL_WARNING = "final_warning"
    SUSPENSION = "suspension"
    TERMINATION = "termination"
    MEDIATION = "mediation"
    TRAINING = "training"
    ACCOMMODATION_GRANTED = "accommodation_granted"
    ACCOMMODATION_DENIED = "accommodation_denied"
    NO_ACTION = "no_action"
    OTHER = "other"


# RBAC: very restrictive for HR cases
_HR_CASE_ROLES: set[str] = {"admin", "hr", "ceo"}
_HR_CASE_VIEW_ROLES: set[str] = {"admin", "hr", "ceo", "legal"}
_HR_CASE_AUDIT_ROLES: set[str] = {"admin", "ceo", "legal", "auditor"}
_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

# Retention periods by case type (days)
_RETENTION_DAYS: dict[CaseType, int] = {
    CaseType.DISCIPLINARY: 7 * 365,  # 7 years
    CaseType.GRIEVANCE: 5 * 365,  # 5 years
    CaseType.INVESTIGATION: 7 * 365,  # 7 years
    CaseType.ACCOMMODATION: 3 * 365,  # 3 years
    CaseType.GENERAL: 2 * 365,  # 2 years
}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseEvidence:
    """Evidence attachment for an HR case."""

    id: UUID
    case_id: UUID
    filename: str
    content_type: str
    storage_path: str
    uploaded_by: str
    uploaded_at: datetime
    description: str = ""
    file_hash: str = ""
    is_confidential: bool = True


@dataclass(frozen=True)
class CaseNote:
    """Internal note on an HR case."""

    id: UUID
    case_id: UUID
    content: str
    created_by: str
    created_at: datetime
    is_confidential: bool = True


@dataclass(frozen=True)
class CaseAction:
    """Outcome action for an HR case."""

    id: UUID
    case_id: UUID
    action_type: ActionType
    description: str
    effective_date: date
    created_by: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HRCase:
    """HR case record with PII controls."""

    id: UUID
    case_number: str
    case_type: CaseType
    subject_employee_id: UUID
    priority: CasePriority
    status: CaseStatus
    title: str
    description: str
    opened_by: str
    opened_at: datetime
    assigned_to: str | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    closure_reason: str = ""
    retention_until: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HRCaseManagementService(PersistentServiceMixin):
    """In-memory HR case management service with PII controls."""

    SERVICE_NAME = "hr_case_management"

    def __init__(self) -> None:
        self._cases: dict[UUID, HRCase] = {}
        self._notes: dict[UUID, CaseNote] = {}
        self._evidence: dict[UUID, CaseEvidence] = {}
        self._actions: dict[UUID, CaseAction] = {}
        self._audit: list[AuditEvent] = []
        self._case_counter: int = 0
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        cases_data = await self.load_state(_DEFAULT_TENANT_ID, "cases") or {}
        notes_data = await self.load_state(_DEFAULT_TENANT_ID, "notes") or {}
        evidence_data = await self.load_state(_DEFAULT_TENANT_ID, "evidence") or {}
        actions_data = await self.load_state(_DEFAULT_TENANT_ID, "actions") or {}
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []
        counter_data = await self.load_state(_DEFAULT_TENANT_ID, "case_counter") or {}

        self._cases = {UUID(cid): decode_dataclass(case, HRCase) for cid, case in cases_data.items()}
        self._notes = {UUID(nid): decode_dataclass(note, CaseNote) for nid, note in notes_data.items()}
        self._evidence = {UUID(eid): decode_dataclass(ev, CaseEvidence) for eid, ev in evidence_data.items()}
        self._actions = {UUID(aid): decode_dataclass(action, CaseAction) for aid, action in actions_data.items()}
        self._audit = [decode_dataclass(ev, AuditEvent) for ev in audit_data]
        self._case_counter = int(counter_data.get("value", 0)) if isinstance(counter_data, dict) else 0
        self._state_loaded = True

    async def persist_all(self) -> None:
        cases_data = {str(cid): encode_dataclass(case) for cid, case in self._cases.items()}
        notes_data = {str(nid): encode_dataclass(note) for nid, note in self._notes.items()}
        evidence_data = {str(eid): encode_dataclass(ev) for eid, ev in self._evidence.items()}
        actions_data = {str(aid): encode_dataclass(action) for aid, action in self._actions.items()}
        audit_data = [encode_dataclass(ev) for ev in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "cases", cases_data)
        await self.save_state(_DEFAULT_TENANT_ID, "notes", notes_data)
        await self.save_state(_DEFAULT_TENANT_ID, "evidence", evidence_data)
        await self.save_state(_DEFAULT_TENANT_ID, "actions", actions_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)
        await self.save_state(_DEFAULT_TENANT_ID, "case_counter", {"value": self._case_counter})

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _next_case_number(self) -> str:
        self._case_counter += 1
        return f"HR-{self._case_counter:06d}"

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ev = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(ev)

    # ----------------------------------------------------------------
    # Audit API
    # ----------------------------------------------------------------

    def list_audit_events(
        self,
        *,
        actor_roles: Iterable[str],
        case_id: UUID | None = None,
    ) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_AUDIT_ROLES, "HR case audit role required")

        if case_id:
            return [
                e
                for e in self._audit
                if e.entity_id == str(case_id)
                or e.metadata.get("case_id") == str(case_id)
            ]
        return list(self._audit)

    async def list_audit_events_async(self, **kwargs: Any) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(**kwargs)

    # ----------------------------------------------------------------
    # Case Management
    # ----------------------------------------------------------------

    def open_case(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_type: CaseType,
        subject_employee_id: UUID,
        title: str,
        description: str,
        priority: CasePriority = CasePriority.MEDIUM,
        assigned_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HRCase:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        if not title or not title.strip():
            raise ValueError("title required")
        if not description or not description.strip():
            raise ValueError("description required")

        case_number = self._next_case_number()

        case = HRCase(
            id=uuid4(),
            case_number=case_number,
            case_type=case_type,
            subject_employee_id=subject_employee_id,
            priority=priority,
            status=CaseStatus.OPEN,
            title=title.strip(),
            description=description.strip(),
            opened_by=actor_id,
            opened_at=_utcnow(),
            assigned_to=assigned_to,
            metadata=metadata or {},
        )
        self._cases[case.id] = case

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.open",
            entity_type="hr_case",
            entity_id=str(case.id),
            correlation_id=correlation_id,
            metadata={
                "case_number": case_number,
                "case_type": case_type.value,
                "subject_employee_id": str(subject_employee_id),
            },
        )

        return case

    async def open_case_async(self, **kwargs: Any) -> HRCase:
        await self._ensure_loaded()
        case = self.open_case(**kwargs)
        await self.persist_all()
        return case

    def get_case(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        case_id: UUID,
    ) -> HRCase | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_VIEW_ROLES, "HR case view role required")

        case = self._cases.get(case_id)
        if case:
            # Log access for PII audit
            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="hr_case.view",
                entity_type="hr_case",
                entity_id=str(case_id),
                correlation_id=f"view-{case_id}",
            )
        return case

    async def get_case_async(self, **kwargs: Any) -> HRCase | None:
        await self._ensure_loaded()
        return self.get_case(**kwargs)

    def list_cases(
        self,
        *,
        actor_roles: Iterable[str],
        case_type: CaseType | None = None,
        status: CaseStatus | None = None,
        assigned_to: str | None = None,
        include_archived: bool = False,
    ) -> list[HRCase]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_VIEW_ROLES, "HR case view role required")

        result = []
        for case in self._cases.values():
            if not include_archived and case.status == CaseStatus.ARCHIVED:
                continue
            if case_type and case.case_type != case_type:
                continue
            if status and case.status != status:
                continue
            if assigned_to and case.assigned_to != assigned_to:
                continue
            result.append(case)

        return sorted(result, key=lambda c: c.opened_at, reverse=True)

    async def list_cases_async(self, **kwargs: Any) -> list[HRCase]:
        await self._ensure_loaded()
        return self.list_cases(**kwargs)

    def update_case_status(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
        status: CaseStatus,
    ) -> HRCase:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status == CaseStatus.ARCHIVED:
            raise ValueError("Cannot modify archived case")

        updated = HRCase(
            id=case.id,
            case_number=case.case_number,
            case_type=case.case_type,
            subject_employee_id=case.subject_employee_id,
            priority=case.priority,
            status=status,
            title=case.title,
            description=case.description,
            opened_by=case.opened_by,
            opened_at=case.opened_at,
            assigned_to=case.assigned_to,
            closed_by=case.closed_by,
            closed_at=case.closed_at,
            closure_reason=case.closure_reason,
            retention_until=case.retention_until,
            metadata=case.metadata,
        )
        self._cases[case.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.update_status",
            entity_type="hr_case",
            entity_id=str(case_id),
            correlation_id=correlation_id,
            metadata={"old_status": case.status.value, "new_status": status.value},
        )

        return updated

    async def update_case_status_async(self, **kwargs: Any) -> HRCase:
        await self._ensure_loaded()
        case = self.update_case_status(**kwargs)
        await self.persist_all()
        return case

    def assign_case(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
        assigned_to: str,
    ) -> HRCase:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status == CaseStatus.ARCHIVED:
            raise ValueError("Cannot modify archived case")

        updated = HRCase(
            id=case.id,
            case_number=case.case_number,
            case_type=case.case_type,
            subject_employee_id=case.subject_employee_id,
            priority=case.priority,
            status=CaseStatus.IN_PROGRESS if case.status == CaseStatus.OPEN else case.status,
            title=case.title,
            description=case.description,
            opened_by=case.opened_by,
            opened_at=case.opened_at,
            assigned_to=assigned_to,
            closed_by=case.closed_by,
            closed_at=case.closed_at,
            closure_reason=case.closure_reason,
            retention_until=case.retention_until,
            metadata=case.metadata,
        )
        self._cases[case.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.assign",
            entity_type="hr_case",
            entity_id=str(case_id),
            correlation_id=correlation_id,
            metadata={"assigned_to": assigned_to},
        )

        return updated

    async def assign_case_async(self, **kwargs: Any) -> HRCase:
        await self._ensure_loaded()
        case = self.assign_case(**kwargs)
        await self.persist_all()
        return case

    def close_case(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
        reason: str,
    ) -> HRCase:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status == CaseStatus.CLOSED:
            raise ValueError("Case already closed")
        if case.status == CaseStatus.ARCHIVED:
            raise ValueError("Cannot modify archived case")
        if not reason or not reason.strip():
            raise ValueError("closure reason required")

        # Calculate retention date
        retention_days = _RETENTION_DAYS.get(case.case_type, 2 * 365)
        retention_until = date.today() + timedelta(days=retention_days)

        closed = HRCase(
            id=case.id,
            case_number=case.case_number,
            case_type=case.case_type,
            subject_employee_id=case.subject_employee_id,
            priority=case.priority,
            status=CaseStatus.CLOSED,
            title=case.title,
            description=case.description,
            opened_by=case.opened_by,
            opened_at=case.opened_at,
            assigned_to=case.assigned_to,
            closed_by=actor_id,
            closed_at=_utcnow(),
            closure_reason=reason.strip(),
            retention_until=retention_until,
            metadata=case.metadata,
        )
        self._cases[case.id] = closed

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.close",
            entity_type="hr_case",
            entity_id=str(case_id),
            correlation_id=correlation_id,
            metadata={
                "reason": reason,
                "retention_until": retention_until.isoformat(),
            },
        )

        return closed

    async def close_case_async(self, **kwargs: Any) -> HRCase:
        await self._ensure_loaded()
        case = self.close_case(**kwargs)
        await self.persist_all()
        return case

    # ----------------------------------------------------------------
    # Notes
    # ----------------------------------------------------------------

    def add_note(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
        content: str,
        is_confidential: bool = True,
    ) -> CaseNote:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status == CaseStatus.ARCHIVED:
            raise ValueError("Cannot modify archived case")
        if not content or not content.strip():
            raise ValueError("content required")

        note = CaseNote(
            id=uuid4(),
            case_id=case_id,
            content=content.strip(),
            created_by=actor_id,
            created_at=_utcnow(),
            is_confidential=is_confidential,
        )
        self._notes[note.id] = note

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.add_note",
            entity_type="case_note",
            entity_id=str(note.id),
            correlation_id=correlation_id,
            metadata={"case_id": str(case_id)},
        )

        return note

    async def add_note_async(self, **kwargs: Any) -> CaseNote:
        await self._ensure_loaded()
        note = self.add_note(**kwargs)
        await self.persist_all()
        return note

    def list_notes(
        self,
        *,
        actor_roles: Iterable[str],
        case_id: UUID,
    ) -> list[CaseNote]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_VIEW_ROLES, "HR case view role required")

        notes = [n for n in self._notes.values() if n.case_id == case_id]
        return sorted(notes, key=lambda n: n.created_at)

    async def list_notes_async(self, **kwargs: Any) -> list[CaseNote]:
        await self._ensure_loaded()
        return self.list_notes(**kwargs)

    # ----------------------------------------------------------------
    # Evidence
    # ----------------------------------------------------------------

    def add_evidence(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
        filename: str,
        content_type: str,
        storage_path: str,
        description: str = "",
        file_hash: str = "",
    ) -> CaseEvidence:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status == CaseStatus.ARCHIVED:
            raise ValueError("Cannot modify archived case")
        if not filename or not filename.strip():
            raise ValueError("filename required")

        evidence = CaseEvidence(
            id=uuid4(),
            case_id=case_id,
            filename=filename.strip(),
            content_type=content_type,
            storage_path=storage_path,
            uploaded_by=actor_id,
            uploaded_at=_utcnow(),
            description=description,
            file_hash=file_hash,
        )
        self._evidence[evidence.id] = evidence

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.add_evidence",
            entity_type="case_evidence",
            entity_id=str(evidence.id),
            correlation_id=correlation_id,
            metadata={
                "case_id": str(case_id),
                "filename": filename,
                "file_hash": file_hash,
            },
        )

        return evidence

    async def add_evidence_async(self, **kwargs: Any) -> CaseEvidence:
        await self._ensure_loaded()
        evidence = self.add_evidence(**kwargs)
        await self.persist_all()
        return evidence

    def list_evidence(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        case_id: UUID,
    ) -> list[CaseEvidence]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_VIEW_ROLES, "HR case view role required")

        # Log access for PII audit
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.view_evidence",
            entity_type="case_evidence",
            entity_id=f"list-{case_id}",
            correlation_id=f"evidence-access-{case_id}",
            metadata={"case_id": str(case_id)},
        )

        evidence = [e for e in self._evidence.values() if e.case_id == case_id]
        return sorted(evidence, key=lambda e: e.uploaded_at)

    async def list_evidence_async(self, **kwargs: Any) -> list[CaseEvidence]:
        await self._ensure_loaded()
        return self.list_evidence(**kwargs)

    # ----------------------------------------------------------------
    # Actions / Outcomes
    # ----------------------------------------------------------------

    def record_action(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
        action_type: ActionType,
        description: str,
        effective_date: date | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CaseAction:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status == CaseStatus.ARCHIVED:
            raise ValueError("Cannot modify archived case")
        if not description or not description.strip():
            raise ValueError("description required")

        action = CaseAction(
            id=uuid4(),
            case_id=case_id,
            action_type=action_type,
            description=description.strip(),
            effective_date=effective_date or date.today(),
            created_by=actor_id,
            created_at=_utcnow(),
            metadata=metadata or {},
        )
        self._actions[action.id] = action

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.record_action",
            entity_type="case_action",
            entity_id=str(action.id),
            correlation_id=correlation_id,
            metadata={
                "case_id": str(case_id),
                "action_type": action_type.value,
            },
        )

        return action

    async def record_action_async(self, **kwargs: Any) -> CaseAction:
        await self._ensure_loaded()
        action = self.record_action(**kwargs)
        await self.persist_all()
        return action

    def list_actions(
        self,
        *,
        actor_roles: Iterable[str],
        case_id: UUID,
    ) -> list[CaseAction]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_VIEW_ROLES, "HR case view role required")

        actions = [a for a in self._actions.values() if a.case_id == case_id]
        return sorted(actions, key=lambda a: a.effective_date)

    async def list_actions_async(self, **kwargs: Any) -> list[CaseAction]:
        await self._ensure_loaded()
        return self.list_actions(**kwargs)

    # ----------------------------------------------------------------
    # Retention / Archival
    # ----------------------------------------------------------------

    def archive_expired_cases(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
    ) -> list[UUID]:
        """Archive cases past retention period."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_CASE_ROLES, "HR case role required")

        today = date.today()
        archived_ids = []

        for case in list(self._cases.values()):
            if case.status != CaseStatus.CLOSED:
                continue
            if not case.retention_until:
                continue
            if case.retention_until > today:
                continue

            # Archive the case
            archived = HRCase(
                id=case.id,
                case_number=case.case_number,
                case_type=case.case_type,
                subject_employee_id=case.subject_employee_id,
                priority=case.priority,
                status=CaseStatus.ARCHIVED,
                title=case.title,
                description=case.description,
                opened_by=case.opened_by,
                opened_at=case.opened_at,
                assigned_to=case.assigned_to,
                closed_by=case.closed_by,
                closed_at=case.closed_at,
                closure_reason=case.closure_reason,
                retention_until=case.retention_until,
                metadata=case.metadata,
            )
            self._cases[case.id] = archived
            archived_ids.append(case.id)

            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="hr_case.archive",
                entity_type="hr_case",
                entity_id=str(case.id),
                correlation_id=correlation_id,
                metadata={"retention_until": case.retention_until.isoformat()},
            )

        return archived_ids

    async def archive_expired_cases_async(self, **kwargs: Any) -> list[UUID]:
        await self._ensure_loaded()
        archived = self.archive_expired_cases(**kwargs)
        await self.persist_all()
        return archived

    def purge_archived_data(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        case_id: UUID,
    ) -> bool:
        """Permanently delete archived case data (for legal compliance)."""
        roles = _norm_roles(actor_roles)
        # Only admin can purge
        if "admin" not in roles:
            raise PermissionError("Only admin can purge case data")

        case = self._cases.get(case_id)
        if not case:
            raise ValueError("case_id not found")
        if case.status != CaseStatus.ARCHIVED:
            raise ValueError("Can only purge archived cases")

        # Delete all related data
        notes_to_delete = [n.id for n in self._notes.values() if n.case_id == case_id]
        for nid in notes_to_delete:
            del self._notes[nid]

        evidence_to_delete = [e.id for e in self._evidence.values() if e.case_id == case_id]
        for eid in evidence_to_delete:
            del self._evidence[eid]

        actions_to_delete = [a.id for a in self._actions.values() if a.case_id == case_id]
        for aid in actions_to_delete:
            del self._actions[aid]

        del self._cases[case_id]

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="hr_case.purge",
            entity_type="hr_case",
            entity_id=str(case_id),
            correlation_id=correlation_id,
            metadata={
                "notes_deleted": len(notes_to_delete),
                "evidence_deleted": len(evidence_to_delete),
                "actions_deleted": len(actions_to_delete),
            },
        )

        return True

    async def purge_archived_data_async(self, **kwargs: Any) -> bool:
        await self._ensure_loaded()
        result = self.purge_archived_data(**kwargs)
        await self.persist_all()
        return result

"""Employee Lifecycle & Records Service (Development Plan 21.7).

Implements:
- Employee Profile: central hub for contact info, skills, and org placement.
- Onboarding/Offboarding Workflows: automated checklists (IT, Safety, HR) and
  offboarding steps (exit interview, equipment recovery).
- Digital Personnel File: secure-ish metadata store for personnel documents with
  role-based masking and PII access logging.

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Iterable, overload
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass
from sensei.services.core.common_thread import get_common_thread_service
from sensei.services.event_bus import event_bus
from sensei.services.domain_events import EmployeeOnboardedEvent

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.pii_controls import (
    PIIControlsService,
    PIICategory,
    SensitivityLevel,
    MaskingType,
    ConsentType,
    PIIAccessType,
)


class EmploymentStatus(str, Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    OFFBOARDING = "offboarding"
    TERMINATED = "terminated"


class ChecklistType(str, Enum):
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"


class ChecklistStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ChecklistCategory(str, Enum):
    IT = "it"
    SAFETY = "safety"
    HR = "hr"
    SECURITY = "security"


class PersonnelDocumentType(str, Enum):
    CONTRACT = "contract"
    GOVERNMENT_ID = "government_id"
    DISCIPLINARY_RECORD = "disciplinary_record"


_PRIVILEGED_PII_ROLES: set[str] = {"admin", "hr", "gm", "exec", "ceo"}
_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _require_tzaware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("All datetimes must be timezone-aware")


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


@dataclass(frozen=True)
class EmployeeProfile:
    employee_id: UUID
    created_at: datetime
    created_by: UUID

    # Identity (not all systems will map 1:1 with auth `User`)
    user_id: UUID | None = None
    first_name: str = ""
    last_name: str = ""

    # Contact info (PII)
    email: str | None = None
    phone: str | None = None

    # Org placement
    department: str | None = None
    job_title: str | None = None
    site_id: str | None = None
    manager_employee_id: UUID | None = None
    cost_center_code: str | None = None

    # Skills (links to Training Matrix / skills catalog by code)
    skill_codes: list[str] = field(default_factory=list)

    status: EmploymentStatus = EmploymentStatus.ONBOARDING

    updated_at: datetime | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True)
class ChecklistItem:
    id: UUID
    category: ChecklistCategory
    title: str
    description: str

    completed: bool = False
    completed_at: datetime | None = None
    completed_by: UUID | None = None

    evidence_attachment_ids: list[UUID] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class EmployeeChecklist:
    id: UUID
    employee_id: UUID
    checklist_type: ChecklistType

    created_at: datetime
    created_by: UUID

    status: ChecklistStatus = ChecklistStatus.NOT_STARTED
    items: list[ChecklistItem] = field(default_factory=list)

    updated_at: datetime | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True)
class PersonnelDocument:
    id: UUID
    employee_id: UUID
    document_type: PersonnelDocumentType

    filename: str
    storage_key: str

    uploaded_at: datetime
    uploaded_by: UUID

    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class EmployeeLifecycleService(PersistentServiceMixin):
    """Lean HR lifecycle service for profiles, checklists, and personnel files."""

    SERVICE_NAME = "employee_lifecycle"

    def __init__(self, *, pii: PIIControlsService | None = None) -> None:
        self._profiles: dict[UUID, EmployeeProfile] = {}
        self._checklists: dict[UUID, EmployeeChecklist] = {}
        self._documents: dict[UUID, PersonnelDocument] = {}

        self._pii = pii or PIIControlsService()
        self._employee_subject_ids: dict[UUID, UUID] = {}
        self._state_loaded = False

        # PII field definitions for this module (used for masking/audit)
        self._field_employee_email_id: UUID = self._pii.create_field_definition(
            name="Employee Email",
            table="employee_profiles",
            column="email",
            category=PIICategory.EMAIL,
            sensitivity=SensitivityLevel.HIGH,
            description="Employee email address",
            detection_pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            masking_type=MaskingType.PARTIAL,
            retention_days=None,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION, ConsentType.PROCESSING],
            is_searchable=True,
            is_exportable=True,
        ).id

        self._field_employee_phone_id: UUID = self._pii.create_field_definition(
            name="Employee Phone",
            table="employee_profiles",
            column="phone",
            category=PIICategory.PHONE,
            sensitivity=SensitivityLevel.MEDIUM,
            description="Employee phone number",
            detection_pattern=r"\+?[\d\s\-\(\)]{10,}",
            masking_type=MaskingType.PARTIAL,
            retention_days=None,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
            is_searchable=False,
            is_exportable=True,
        ).id

        self._field_personnel_filename_id: UUID = self._pii.create_field_definition(
            name="Personnel Document Filename",
            table="employee_personnel_documents",
            column="filename",
            category=PIICategory.EMPLOYMENT,
            sensitivity=SensitivityLevel.HIGH,
            description="Personnel document filename (may include personal identifiers)",
            detection_pattern=None,
            masking_type=MaskingType.PARTIAL,
            retention_days=None,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
            is_searchable=False,
            is_exportable=False,
        ).id

        self._field_personnel_notes_id: UUID = self._pii.create_field_definition(
            name="Personnel Document Notes",
            table="employee_personnel_documents",
            column="notes",
            category=PIICategory.EMPLOYMENT,
            sensitivity=SensitivityLevel.HIGH,
            description="HR notes about a personnel document",
            detection_pattern=None,
            masking_type=MaskingType.FULL,
            retention_days=None,
            requires_consent=True,
            consent_types=[ConsentType.PROCESSING],
            is_searchable=False,
            is_exportable=False,
        ).id

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        profiles_data = await self.load_state(_DEFAULT_TENANT_ID, "profiles") or {}
        checklists_data = await self.load_state(_DEFAULT_TENANT_ID, "checklists") or {}
        documents_data = await self.load_state(_DEFAULT_TENANT_ID, "documents") or {}
        subject_ids_data = await self.load_state(_DEFAULT_TENANT_ID, "subject_ids") or {}

        self._profiles = {
            UUID(pid): decode_dataclass(profile, EmployeeProfile)
            for pid, profile in profiles_data.items()
        }
        self._checklists = {
            UUID(cid): decode_dataclass(checklist, EmployeeChecklist)
            for cid, checklist in checklists_data.items()
        }
        self._documents = {
            UUID(did): decode_dataclass(doc, PersonnelDocument)
            for did, doc in documents_data.items()
        }
        self._employee_subject_ids = {
            UUID(eid): UUID(sid)
            for eid, sid in subject_ids_data.items()
        }
        self._state_loaded = True

    async def persist_all(self) -> None:
        profiles_data = {str(pid): encode_dataclass(profile) for pid, profile in self._profiles.items()}
        checklists_data = {str(cid): encode_dataclass(checklist) for cid, checklist in self._checklists.items()}
        documents_data = {str(did): encode_dataclass(doc) for did, doc in self._documents.items()}
        subject_ids_data = {str(eid): str(sid) for eid, sid in self._employee_subject_ids.items()}

        await self.save_state(_DEFAULT_TENANT_ID, "profiles", profiles_data)
        await self.save_state(_DEFAULT_TENANT_ID, "checklists", checklists_data)
        await self.save_state(_DEFAULT_TENANT_ID, "documents", documents_data)
        await self.save_state(_DEFAULT_TENANT_ID, "subject_ids", subject_ids_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def can_view_pii(self, *, actor_roles: Iterable[str]) -> bool:
        roles = _norm_roles(actor_roles)
        return len(roles.intersection(_PRIVILEGED_PII_ROLES)) > 0

    def _require_hr_write(self, *, actor_roles: Iterable[str]) -> None:
        roles = _norm_roles(actor_roles)
        if not roles.intersection({"admin", "hr"}):
            raise PermissionError("HR/Admin role required")

    def _get_or_register_subject(self, employee_id: UUID) -> UUID:
        existing = self._employee_subject_ids.get(employee_id)
        if existing is not None:
            return existing

        subject = self._pii.register_subject(
            external_id=str(employee_id),
            subject_type="employee",
            email=None,
        )
        self._employee_subject_ids[employee_id] = subject.id
        return subject.id

    # ------------------------------------------------------------------
    # Employee profiles
    # ------------------------------------------------------------------

    def upsert_employee_profile(
        self,
        *,
        employee_id: UUID,
        actor_id: UUID,
        actor_roles: Iterable[str],
        created_at: datetime | None = None,
        user_id: UUID | None = None,
        first_name: str = "",
        last_name: str = "",
        email: str | None = None,
        phone: str | None = None,
        department: str | None = None,
        job_title: str | None = None,
        site_id: str | None = None,
        manager_employee_id: UUID | None = None,
        cost_center_code: str | None = None,
        skill_codes: list[str] | None = None,
        status: EmploymentStatus | None = None,
        now: datetime | None = None,
    ) -> EmployeeProfile:
        # HR profile creation/editing is typically restricted.
        self._require_hr_write(actor_roles=actor_roles)

        at = created_at or datetime.now(timezone.utc)
        _require_tzaware(at)
        updated_at = now or datetime.now(timezone.utc)
        _require_tzaware(updated_at)

        existing = self._profiles.get(employee_id)
        if existing is None:
            profile = EmployeeProfile(
                employee_id=employee_id,
                created_at=at,
                created_by=actor_id,
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                department=department,
                job_title=job_title,
                site_id=site_id,
                manager_employee_id=manager_employee_id,
                cost_center_code=cost_center_code,
                skill_codes=list(skill_codes or []),
                status=status or EmploymentStatus.ONBOARDING,
                updated_at=updated_at,
                updated_by=actor_id,
            )
            self._profiles[employee_id] = profile
            self._get_or_register_subject(employee_id)

            # Publish domain event — feeds single data thread
            event_bus.publish_sync(EmployeeOnboardedEvent(
                employee_id=str(employee_id),
                department=department or "",
                position=job_title or "",
            ))

            return profile

        updated = replace(
            existing,
            user_id=user_id if user_id is not None else existing.user_id,
            first_name=first_name if first_name != "" else existing.first_name,
            last_name=last_name if last_name != "" else existing.last_name,
            email=email if email is not None else existing.email,
            phone=phone if phone is not None else existing.phone,
            department=department if department is not None else existing.department,
            job_title=job_title if job_title is not None else existing.job_title,
            site_id=site_id if site_id is not None else existing.site_id,
            manager_employee_id=(
                manager_employee_id
                if manager_employee_id is not None
                else existing.manager_employee_id
            ),
            cost_center_code=(
                cost_center_code if cost_center_code is not None else existing.cost_center_code
            ),
            skill_codes=list(skill_codes) if skill_codes is not None else list(existing.skill_codes),
            status=status if status is not None else existing.status,
            updated_at=updated_at,
            updated_by=actor_id,
        )
        self._profiles[employee_id] = updated
        self._get_or_register_subject(employee_id)
        return updated

    async def upsert_employee_profile_async(
        self,
        *,
        reasoning_id: str | None = None,
        db: AsyncSession | None = None,
        **kwargs: Any,
    ) -> EmployeeProfile:
        await self._ensure_loaded()
        profile = self.upsert_employee_profile(**kwargs)
        await self.persist_all()
        if db is not None and reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="employee",
                entity_id=profile.employee_id,
                reasoning_id=reasoning_id,
                created_by_id=kwargs.get("actor_id"),
                source="employee_lifecycle",
            )
        return profile

    async def _get_employee_profile_async(
        self,
        employee_id: UUID,
        *,
        actor_id: UUID,
        actor_roles: Iterable[str],
        db: AsyncSession,
        purpose: str = "profile_view",
    ) -> EmployeeProfile | None:
        profile = self._profiles.get(employee_id)
        if profile is None:
            return None

        subject_id = self._get_or_register_subject(employee_id)

        if self.can_view_pii(actor_roles=actor_roles):
            # Log access to the contact fields if present.
            if profile.email:
                await self._pii.log_access(
                    db=db,
                    subject_id=subject_id,
                    user_id=actor_id,
                    field_id=self._field_employee_email_id,
                    access_type=PIIAccessType.VIEW,
                    purpose=purpose,
                    data_snapshot=profile.email,
                )
            if profile.phone:
                await self._pii.log_access(
                    db=db,
                    subject_id=subject_id,
                    user_id=actor_id,
                    field_id=self._field_employee_phone_id,
                    access_type=PIIAccessType.VIEW,
                    purpose=purpose,
                    data_snapshot=profile.phone,
                )
            return profile

        # Non-privileged viewers get masked PII.
        masked_email = (
            await self._pii.mask_value(profile.email, field_id=self._field_employee_email_id, db=db)
            if profile.email
            else None
        )
        masked_phone = (
            await self._pii.mask_value(profile.phone, field_id=self._field_employee_phone_id, db=db)
            if profile.phone
            else None
        )
        return replace(profile, email=masked_email, phone=masked_phone)

    @overload
    def get_employee_profile(
        self,
        employee_id: UUID,
        *,
        actor_id: UUID,
        actor_roles: Iterable[str],
        db: AsyncSession,
        purpose: str = "profile_view",
    ) -> Awaitable[EmployeeProfile | None]: ...

    @overload
    def get_employee_profile(
        self,
        employee_id: UUID,
        *,
        actor_id: UUID,
        actor_roles: Iterable[str],
        db: None = None,
        purpose: str = "profile_view",
    ) -> EmployeeProfile | None: ...

    def get_employee_profile(
        self,
        employee_id: UUID,
        *,
        actor_id: UUID,
        actor_roles: Iterable[str],
        db: AsyncSession | None = None,
        purpose: str = "profile_view",
    ) -> EmployeeProfile | None | Awaitable[EmployeeProfile | None]:
        if db is not None:
            return self._get_employee_profile_async(
                employee_id,
                actor_id=actor_id,
                actor_roles=actor_roles,
                db=db,
                purpose=purpose,
            )

        profile = self._profiles.get(employee_id)
        if profile is None:
            return None

        if self.can_view_pii(actor_roles=actor_roles):
            return profile

        masked_email: str | None = None
        masked_phone: str | None = None
        if profile.email:
            masked = self._pii.mask_value(profile.email, field_id=self._field_employee_email_id)
            masked_email = masked._get_value() if hasattr(masked, "_get_value") else masked
        if profile.phone:
            masked = self._pii.mask_value(profile.phone, field_id=self._field_employee_phone_id)
            masked_phone = masked._get_value() if hasattr(masked, "_get_value") else masked

        return replace(profile, email=masked_email, phone=masked_phone)

    async def get_employee_profile_async(
        self,
        *,
        employee_id: UUID,
        actor_id: UUID,
        actor_roles: Iterable[str],
        db: AsyncSession | None = None,
        purpose: str = "profile_view",
    ) -> EmployeeProfile | None:
        await self._ensure_loaded()
        if db is not None:
            return await self._get_employee_profile_async(
                employee_id,
                actor_id=actor_id,
                actor_roles=actor_roles,
                db=db,
                purpose=purpose,
            )
        return self.get_employee_profile(
            employee_id,
            actor_id=actor_id,
            actor_roles=actor_roles,
            db=None,
            purpose=purpose,
        )

    # ------------------------------------------------------------------
    # Onboarding / Offboarding checklists
    # ------------------------------------------------------------------

    def create_checklist(
        self,
        *,
        employee_id: UUID,
        checklist_type: ChecklistType,
        created_by: UUID,
        created_at: datetime | None = None,
    ) -> EmployeeChecklist:
        at = created_at or datetime.now(timezone.utc)
        _require_tzaware(at)

        checklist_id = uuid4()
        items = self._default_checklist_items(checklist_type)

        checklist = EmployeeChecklist(
            id=checklist_id,
            employee_id=employee_id,
            checklist_type=checklist_type,
            created_at=at,
            created_by=created_by,
            status=ChecklistStatus.NOT_STARTED,
            items=items,
            updated_at=at,
            updated_by=created_by,
        )
        self._checklists[checklist.id] = checklist
        return checklist

    async def create_checklist_async(self, **kwargs: Any) -> EmployeeChecklist:
        await self._ensure_loaded()
        checklist = self.create_checklist(**kwargs)
        await self.persist_all()
        return checklist

    def _default_checklist_items(self, checklist_type: ChecklistType) -> list[ChecklistItem]:
        if checklist_type == ChecklistType.ONBOARDING:
            template = [
                (ChecklistCategory.HR, "Collect required documents", "Collect contract/ID and required HR forms"),
                (ChecklistCategory.IT, "Provision accounts", "Create email/SSO account and assign baseline roles"),
                (ChecklistCategory.SAFETY, "Safety induction", "Complete safety induction and PPE issuance"),
                (ChecklistCategory.SAFETY, "LOTO awareness", "Confirm lockout/tagout awareness training scheduled"),
                (ChecklistCategory.IT, "Device assignment", "Assign badge/terminal access and any devices"),
            ]
        else:
            template = [
                (ChecklistCategory.HR, "Exit interview", "Conduct structured exit interview"),
                (ChecklistCategory.IT, "Disable accounts", "Disable SSO/email/VPN accounts and revoke tokens"),
                (ChecklistCategory.SECURITY, "Recover badge", "Recover badge and revoke physical access"),
                (ChecklistCategory.IT, "Recover equipment", "Recover laptop/tablet/keys and confirm wipe if needed"),
                (ChecklistCategory.HR, "Final paperwork", "Collect final acknowledgements and documentation"),
            ]

        return [
            ChecklistItem(
                id=uuid4(),
                category=cat,
                title=title,
                description=desc,
            )
            for cat, title, desc in template
        ]

    def get_checklist(self, checklist_id: UUID) -> EmployeeChecklist | None:
        return self._checklists.get(checklist_id)

    async def get_checklist_async(self, *, checklist_id: UUID) -> EmployeeChecklist | None:
        await self._ensure_loaded()
        return self.get_checklist(checklist_id)

    def list_checklists(self, *, employee_id: UUID | None = None) -> list[EmployeeChecklist]:
        checklists = list(self._checklists.values())
        if employee_id is not None:
            checklists = [c for c in checklists if c.employee_id == employee_id]
        checklists.sort(key=lambda c: c.created_at, reverse=True)
        return checklists

    async def list_checklists_async(
        self, *, employee_id: UUID | None = None
    ) -> list[EmployeeChecklist]:
        await self._ensure_loaded()
        return self.list_checklists(employee_id=employee_id)

    def complete_checklist_item(
        self,
        checklist_id: UUID,
        item_id: UUID,
        *,
        actor_id: UUID,
        completed_at: datetime | None = None,
        notes: str = "",
        evidence_attachment_ids: list[UUID] | None = None,
    ) -> EmployeeChecklist:
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            raise ValueError("checklist not found")

        at = completed_at or datetime.now(timezone.utc)
        _require_tzaware(at)

        updated_items: list[ChecklistItem] = []
        found = False
        for item in checklist.items:
            if item.id != item_id:
                updated_items.append(item)
                continue

            found = True
            updated_items.append(
                replace(
                    item,
                    completed=True,
                    completed_at=at,
                    completed_by=actor_id,
                    notes=(notes or "").strip(),
                    evidence_attachment_ids=list(evidence_attachment_ids or item.evidence_attachment_ids),
                )
            )

        if not found:
            raise ValueError("checklist item not found")

        new_status = self._compute_checklist_status(updated_items)
        updated = replace(
            checklist,
            items=updated_items,
            status=new_status,
            updated_at=at,
            updated_by=actor_id,
        )
        self._checklists[checklist_id] = updated
        return updated

    async def complete_checklist_item_async(self, **kwargs: Any) -> EmployeeChecklist:
        await self._ensure_loaded()
        checklist = self.complete_checklist_item(**kwargs)
        await self.persist_all()
        return checklist

    def _compute_checklist_status(self, items: list[ChecklistItem]) -> ChecklistStatus:
        if not items:
            return ChecklistStatus.COMPLETED
        completed_count = sum(1 for i in items if i.completed)
        if completed_count == 0:
            return ChecklistStatus.NOT_STARTED
        if completed_count == len(items):
            return ChecklistStatus.COMPLETED
        return ChecklistStatus.IN_PROGRESS

    # ------------------------------------------------------------------
    # Personnel file
    # ------------------------------------------------------------------

    def add_personnel_document(
        self,
        *,
        employee_id: UUID,
        document_type: PersonnelDocumentType,
        filename: str,
        storage_key: str,
        uploaded_by: UUID,
        actor_roles: Iterable[str],
        uploaded_at: datetime | None = None,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> PersonnelDocument:
        self._require_hr_write(actor_roles=actor_roles)

        if not filename.strip():
            raise ValueError("filename is required")
        if not storage_key.strip():
            raise ValueError("storage_key is required")

        at = uploaded_at or datetime.now(timezone.utc)
        _require_tzaware(at)

        doc = PersonnelDocument(
            id=uuid4(),
            employee_id=employee_id,
            document_type=document_type,
            filename=filename.strip(),
            storage_key=storage_key.strip(),
            uploaded_at=at,
            uploaded_by=uploaded_by,
            notes=(notes or "").strip(),
            metadata=dict(metadata or {}),
        )
        self._documents[doc.id] = doc
        self._get_or_register_subject(employee_id)
        return doc

    async def add_personnel_document_async(self, **kwargs: Any) -> PersonnelDocument:
        await self._ensure_loaded()
        doc = self.add_personnel_document(**kwargs)
        await self.persist_all()
        return doc

    def list_personnel_documents(
        self,
        *,
        employee_id: UUID,
        actor_id: UUID,
        actor_roles: Iterable[str],
        purpose: str = "personnel_file_view",
    ) -> list[PersonnelDocument]:
        docs = [d for d in self._documents.values() if d.employee_id == employee_id]
        docs.sort(key=lambda d: d.uploaded_at, reverse=True)

        subject_id = self._get_or_register_subject(employee_id)

        if self.can_view_pii(actor_roles=actor_roles):
            for d in docs:
                # Log that the viewer accessed the personnel file doc metadata.
                self._pii.log_access(
                    subject_id=subject_id,
                    user_id=actor_id,
                    field_id=self._field_personnel_filename_id,
                    access_type=PIIAccessType.VIEW,
                    purpose=purpose,
                    data_snapshot=d.filename,
                )
                if d.notes:
                    self._pii.log_access(
                        subject_id=subject_id,
                        user_id=actor_id,
                        field_id=self._field_personnel_notes_id,
                        access_type=PIIAccessType.VIEW,
                        purpose=purpose,
                        data_snapshot=d.notes,
                    )
            return docs

        # Non-privileged viewers get redacted storage keys + masked filename/notes.
        redacted: list[PersonnelDocument] = []
        for d in docs:
            masked_filename = self._pii.mask_value(d.filename, field_id=self._field_personnel_filename_id)
            masked_notes = self._pii.mask_value(d.notes, field_id=self._field_personnel_notes_id) if d.notes else None
            filename_value = masked_filename._get_value() if hasattr(masked_filename, "_get_value") else masked_filename
            notes_value = masked_notes._get_value() if (masked_notes and hasattr(masked_notes, "_get_value")) else (masked_notes or "")
            redacted.append(
                replace(
                    d,
                    filename=filename_value,
                    storage_key="",
                    notes=notes_value,
                )
            )
        return redacted

    async def list_personnel_documents_async(self, **kwargs: Any) -> list[PersonnelDocument]:
        await self._ensure_loaded()
        return self.list_personnel_documents(**kwargs)

    def get_pii_access_logs_for_employee(
        self,
        *,
        employee_id: UUID,
        limit: int = 100,
    ) -> list[Any]:
        subject_id = self._get_or_register_subject(employee_id)
        logs_awaitable = self._pii.get_access_logs(subject_id=subject_id)
        logs = logs_awaitable._get_value() if hasattr(logs_awaitable, "_get_value") else logs_awaitable
        return list(logs)[:limit]

    async def get_pii_access_logs_for_employee_async(self, **kwargs: Any) -> list[Any]:
        await self._ensure_loaded()
        return self.get_pii_access_logs_for_employee(**kwargs)

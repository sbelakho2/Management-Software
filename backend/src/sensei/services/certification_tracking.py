"""Multi-Standard Certification Tracking (Development Plan 21.7).

Implements:
- Universal Cert Registry: track ISO/IATF/AS9100/customer-specific certifications per employee.
- Auto-Renewal Workflows: system-driven nudges for recertification 60 days before expiration.
- Certification Evidence: secure-ish metadata storage for certificates and external assessments,
  with role-based masking and PII access logging.

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.pii_controls import (
    PIIControlsService,
    PIICategory,
    SensitivityLevel,
    MaskingType,
    ConsentType,
    PIIAccessType,
)


class CertificationStandard(str, Enum):
    ISO_9001 = "iso_9001"
    IATF_16949 = "iatf_16949"
    AS9100 = "as9100"
    ISO_14001 = "iso_14001"
    ISO_45001 = "iso_45001"
    CUSTOMER_SPECIFIC = "customer_specific"
    OTHER = "other"


class CertificationStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


_PRIVILEGED_CERT_ROLES: set[str] = {"admin", "hr", "gm", "exec", "ceo", "quality"}
_CERT_WRITE_ROLES: set[str] = {"admin", "hr", "gm", "quality"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CertificationRecord:
    id: UUID
    employee_id: UUID

    standard: CertificationStandard
    name: str
    issuer: str | None

    issued_on: date | None
    expires_on: date | None

    status: CertificationStatus

    created_at: datetime
    created_by: UUID

    updated_at: datetime | None = None
    updated_by: UUID | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CertificationEvidence:
    id: UUID
    certification_id: UUID
    employee_id: UUID

    filename: str
    storage_key: str

    uploaded_at: datetime
    uploaded_by: UUID

    sha256: str | None = None
    mime_type: str | None = None

    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecertificationNudge:
    id: UUID
    certification_id: UUID
    employee_id: UUID

    due_on: date
    expires_on: date
    lead_days: int

    created_at: datetime

    last_sent_at: datetime | None = None
    send_count: int = 0


class CertificationTrackingService:
    """In-memory certification registry + renewal nudges + evidence metadata."""

    def __init__(self, *, pii: PIIControlsService | None = None) -> None:
        self._certs: dict[UUID, CertificationRecord] = {}
        self._evidence: dict[UUID, CertificationEvidence] = {}
        self._nudges: dict[UUID, RecertificationNudge] = {}

        self._pii = pii or PIIControlsService()
        self._employee_subject_ids: dict[UUID, UUID] = {}

        # PII field definitions for evidence metadata.
        self._field_evidence_filename_id: UUID = self._pii.create_field_definition(
            name="Certification Evidence Filename",
            table="employee_certification_evidence",
            column="filename",
            category=PIICategory.EMPLOYMENT,
            sensitivity=SensitivityLevel.HIGH,
            description="Filename for a certification evidence file (may contain personal identifiers)",
            detection_pattern=None,
            masking_type=MaskingType.PARTIAL,
            retention_days=None,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
            is_searchable=False,
            is_exportable=False,
        ).id

        self._field_evidence_notes_id: UUID = self._pii.create_field_definition(
            name="Certification Evidence Notes",
            table="employee_certification_evidence",
            column="notes",
            category=PIICategory.EMPLOYMENT,
            sensitivity=SensitivityLevel.HIGH,
            description="Notes about certification evidence (may include personal or performance details)",
            detection_pattern=None,
            masking_type=MaskingType.PARTIAL,
            retention_days=None,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
            is_searchable=False,
            is_exportable=False,
        ).id

        # Lightweight event capture for KPI hooks / audit.
        self.events: list[dict[str, Any]] = []

    def _ensure_employee_subject_id(self, employee_id: UUID) -> UUID:
        subject_id = self._employee_subject_ids.get(employee_id)
        if subject_id is not None:
            return subject_id

        subject = self._pii.register_subject(
            external_id=str(employee_id),
            subject_type="employee",
            email=None,
        )
        self._employee_subject_ids[employee_id] = subject.id
        return subject.id

    # ---- RBAC helpers ----

    def can_view_employee(
        self,
        *,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None,
        target_employee_id: UUID,
    ) -> bool:
        roles = _norm_roles(actor_roles)
        if actor_employee_id is not None and actor_employee_id == target_employee_id:
            return True
        return len(roles.intersection(_PRIVILEGED_CERT_ROLES)) > 0

    def can_write(self, *, actor_roles: Iterable[str]) -> bool:
        roles = _norm_roles(actor_roles)
        return len(roles.intersection(_CERT_WRITE_ROLES)) > 0

    # ---- Registry ----

    def add_certification(
        self,
        *,
        employee_id: UUID,
        standard: CertificationStandard,
        name: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        issuer: str | None = None,
        issued_on: date | None = None,
        expires_on: date | None = None,
        status: CertificationStatus = CertificationStatus.ACTIVE,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> CertificationRecord:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to add certifications")

        cert_id = uuid4()
        created_at = now or _utcnow()
        record = CertificationRecord(
            id=cert_id,
            employee_id=employee_id,
            standard=standard,
            name=name.strip(),
            issuer=issuer.strip() if issuer else None,
            issued_on=issued_on,
            expires_on=expires_on,
            status=status,
            created_at=created_at,
            created_by=actor_user_id,
            metadata=dict(metadata or {}),
        )
        self._certs[cert_id] = record
        return record

    def update_certification(
        self,
        cert_id: UUID,
        *,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        standard: CertificationStandard | None = None,
        name: str | None = None,
        issuer: str | None = None,
        issued_on: date | None = None,
        expires_on: date | None = None,
        status: CertificationStatus | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> CertificationRecord:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to update certifications")
        if cert_id not in self._certs:
            raise KeyError("Certification not found")

        current = self._certs[cert_id]
        updated = replace(
            current,
            standard=standard or current.standard,
            name=(name.strip() if name is not None else current.name),
            issuer=(issuer.strip() if issuer is not None else current.issuer),
            issued_on=issued_on if issued_on is not None else current.issued_on,
            expires_on=expires_on if expires_on is not None else current.expires_on,
            status=status or current.status,
            metadata=dict(metadata) if metadata is not None else current.metadata,
            updated_at=now or _utcnow(),
            updated_by=actor_user_id,
        )
        self._certs[cert_id] = updated
        return updated

    def list_certifications(
        self,
        *,
        employee_id: UUID,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None,
        include_inactive: bool = True,
        as_of: date | None = None,
    ) -> list[CertificationRecord]:
        if not self.can_view_employee(
            actor_roles=actor_roles,
            actor_employee_id=actor_employee_id,
            target_employee_id=employee_id,
        ):
            raise PermissionError("Not permitted to view certifications")

        # Opportunistically update expired statuses when requested.
        if as_of is not None:
            self.expire_due_certifications(as_of=as_of)

        records = [c for c in self._certs.values() if c.employee_id == employee_id]
        if not include_inactive:
            records = [c for c in records if c.status == CertificationStatus.ACTIVE]
        records.sort(key=lambda r: (r.expires_on or date.max, r.name.lower()))
        return records

    def expire_due_certifications(self, *, as_of: date) -> list[UUID]:
        expired_ids: list[UUID] = []
        for cert_id, record in list(self._certs.items()):
            if record.expires_on is None:
                continue
            if record.status != CertificationStatus.ACTIVE:
                continue
            if record.expires_on < as_of:
                self._certs[cert_id] = replace(record, status=CertificationStatus.EXPIRED)
                expired_ids.append(cert_id)
                self.events.append(
                    {
                        "event_name": "certification.expired",
                        "created_at": _utcnow().isoformat(),
                        "payload": {
                            "employee_id": str(record.employee_id),
                            "certification_id": str(cert_id),
                            "expires_on": record.expires_on.isoformat(),
                        },
                    }
                )
        return expired_ids

    def renew_certification(
        self,
        cert_id: UUID,
        *,
        new_expires_on: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        now: datetime | None = None,
    ) -> CertificationRecord:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to renew certifications")
        if cert_id not in self._certs:
            raise KeyError("Certification not found")

        record = self._certs[cert_id]
        updated = replace(
            record,
            expires_on=new_expires_on,
            status=CertificationStatus.ACTIVE,
            updated_at=now or _utcnow(),
            updated_by=actor_user_id,
        )
        self._certs[cert_id] = updated
        self.events.append(
            {
                "event_name": "certification.renewed",
                "created_at": (now or _utcnow()).isoformat(),
                "payload": {
                    "employee_id": str(record.employee_id),
                    "certification_id": str(cert_id),
                    "new_expiry": new_expires_on.isoformat(),
                },
            }
        )
        return updated

    # ---- Evidence ----

    def add_evidence(
        self,
        *,
        certification_id: UUID,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        filename: str,
        storage_key: str,
        sha256: str | None = None,
        mime_type: str | None = None,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> CertificationEvidence:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to add certification evidence")
        if certification_id not in self._certs:
            raise KeyError("Certification not found")

        cert = self._certs[certification_id]
        ev_id = uuid4()
        uploaded_at = now or _utcnow()
        evidence = CertificationEvidence(
            id=ev_id,
            certification_id=certification_id,
            employee_id=cert.employee_id,
            filename=filename,
            storage_key=storage_key,
            uploaded_at=uploaded_at,
            uploaded_by=actor_user_id,
            sha256=sha256,
            mime_type=mime_type,
            notes=notes,
            metadata=dict(metadata or {}),
        )
        self._evidence[ev_id] = evidence
        return evidence

    async def _list_evidence_async(
        self,
        *,
        certification_id: UUID,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None,
        actor_user_id: UUID,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        if certification_id not in self._certs:
            raise KeyError("Certification not found")
        cert = self._certs[certification_id]

        if not self.can_view_employee(
            actor_roles=actor_roles,
            actor_employee_id=actor_employee_id,
            target_employee_id=cert.employee_id,
        ):
            raise PermissionError("Not permitted to view certification evidence")

        roles = _norm_roles(actor_roles)
        privileged = (
            len(roles.intersection(_PRIVILEGED_CERT_ROLES)) > 0
            or (actor_employee_id is not None and actor_employee_id == cert.employee_id)
        )

        results: list[dict[str, Any]] = []
        for ev in sorted(
            [e for e in self._evidence.values() if e.certification_id == certification_id],
            key=lambda e: e.uploaded_at,
        ):
            filename = ev.filename
            notes = ev.notes
            storage_key = ev.storage_key

            if privileged:
                # Audit privileged access to potentially sensitive metadata.
                subject_id = self._ensure_employee_subject_id(cert.employee_id)
                await self._pii.log_access(
                    db=db,
                    subject_id=subject_id,
                    user_id=actor_user_id,
                    field_id=self._field_evidence_filename_id,
                    access_type=PIIAccessType.VIEW,
                    purpose="View certification evidence filename",
                    data_snapshot=ev.filename,
                )
                if notes:
                    await self._pii.log_access(
                        db=db,
                        subject_id=subject_id,
                        user_id=actor_user_id,
                        field_id=self._field_evidence_notes_id,
                        access_type=PIIAccessType.VIEW,
                        purpose="View certification evidence notes",
                        data_snapshot=ev.notes,
                    )
            else:
                filename = await self._pii.mask_value(filename, field_id=self._field_evidence_filename_id, db=db)
                notes = await self._pii.mask_value(notes, field_id=self._field_evidence_notes_id, db=db) if notes else ""
                storage_key = "***"

            results.append(
                {
                    "id": ev.id,
                    "certification_id": ev.certification_id,
                    "employee_id": ev.employee_id,
                    "filename": filename,
                    "storage_key": storage_key,
                    "uploaded_at": ev.uploaded_at,
                    "uploaded_by": ev.uploaded_by,
                    "sha256": ev.sha256,
                    "mime_type": ev.mime_type,
                    "notes": notes,
                    "metadata": dict(ev.metadata),
                }
            )
        return results

    async def list_evidence(
        self,
        *,
        certification_id: UUID,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None,
        actor_user_id: UUID,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        if db is not None:
            return await self._list_evidence_async(
                certification_id=certification_id,
                actor_roles=actor_roles,
                actor_employee_id=actor_employee_id,
                actor_user_id=actor_user_id,
                db=db,
            )
        if certification_id not in self._certs:
            raise KeyError("Certification not found")
        cert = self._certs[certification_id]

        if not self.can_view_employee(
            actor_roles=actor_roles,
            actor_employee_id=actor_employee_id,
            target_employee_id=cert.employee_id,
        ):
            raise PermissionError("Not permitted to view certification evidence")

        roles = _norm_roles(actor_roles)
        privileged = (
            len(roles.intersection(_PRIVILEGED_CERT_ROLES)) > 0
            or (actor_employee_id is not None and actor_employee_id == cert.employee_id)
        )

        results: list[dict[str, Any]] = []
        for ev in sorted(
            [e for e in self._evidence.values() if e.certification_id == certification_id],
            key=lambda e: e.uploaded_at,
        ):
            filename = ev.filename
            notes = ev.notes
            storage_key = ev.storage_key

            if not privileged:
                masked_filename = self._pii.mask_value(filename, field_id=self._field_evidence_filename_id)
                masked_notes = self._pii.mask_value(notes, field_id=self._field_evidence_notes_id) if notes else ""
                filename_result = masked_filename._get_value() if hasattr(masked_filename, "_get_value") else masked_filename
                filename = str(filename_result)
                notes_result = masked_notes._get_value() if hasattr(masked_notes, "_get_value") else masked_notes
                notes = str(notes_result) if notes_result else ""
                storage_key = "***"

            results.append(
                {
                    "id": ev.id,
                    "certification_id": ev.certification_id,
                    "employee_id": ev.employee_id,
                    "filename": filename,
                    "storage_key": storage_key,
                    "uploaded_at": ev.uploaded_at,
                    "uploaded_by": ev.uploaded_by,
                    "sha256": ev.sha256,
                    "mime_type": ev.mime_type,
                    "notes": notes,
                    "metadata": dict(ev.metadata),
                }
            )
        return results

    async def get_pii_access_logs(self, db: AsyncSession) -> list[dict[str, Any]]:
        logs = await self._pii.get_access_logs(db=db)
        return [l.to_dict() for l in logs]

    def get_pii_access_logs_sync(self) -> list[dict[str, Any]]:
        logs = self._pii.get_access_logs()
        return [l.to_dict() for l in logs]

    # ---- Renewal nudges ----

    def generate_recertification_nudges(
        self,
        *,
        as_of: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        lead_days: int = 60,
    ) -> list[RecertificationNudge]:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to generate renewal nudges")
        if lead_days <= 0:
            raise ValueError("lead_days must be positive")

        created: list[RecertificationNudge] = []
        for cert in self._certs.values():
            if cert.status != CertificationStatus.ACTIVE:
                continue
            if cert.expires_on is None:
                continue

            days_until = (cert.expires_on - as_of).days
            if days_until > lead_days:
                continue
            if days_until < 0:
                continue

            due_on = cert.expires_on - timedelta(days=lead_days)
            # Idempotency: don't duplicate nudges for same cert+due_on.
            already = next(
                (
                    n
                    for n in self._nudges.values()
                    if n.certification_id == cert.id and n.due_on == due_on and n.lead_days == lead_days
                ),
                None,
            )
            if already is not None:
                continue

            nudge = RecertificationNudge(
                id=uuid4(),
                certification_id=cert.id,
                employee_id=cert.employee_id,
                due_on=due_on,
                expires_on=cert.expires_on,
                lead_days=lead_days,
                created_at=_utcnow(),
            )
            self._nudges[nudge.id] = nudge
            created.append(nudge)

        created.sort(key=lambda n: (n.expires_on, n.employee_id))
        return created

    def list_recertification_nudges(
        self,
        *,
        employee_id: UUID | None,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None,
        include_sent: bool = True,
    ) -> list[RecertificationNudge]:
        if employee_id is not None and not self.can_view_employee(
            actor_roles=actor_roles,
            actor_employee_id=actor_employee_id,
            target_employee_id=employee_id,
        ):
            raise PermissionError("Not permitted to view renewal nudges")

        nudges = list(self._nudges.values())
        if employee_id is not None:
            nudges = [n for n in nudges if n.employee_id == employee_id]
        if not include_sent:
            nudges = [n for n in nudges if n.send_count == 0]
        nudges.sort(key=lambda n: (n.expires_on, n.employee_id))
        return nudges

    def mark_nudge_sent(
        self,
        nudge_id: UUID,
        *,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        now: datetime | None = None,
    ) -> RecertificationNudge:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to mark nudges sent")
        if nudge_id not in self._nudges:
            raise KeyError("Nudge not found")

        n = self._nudges[nudge_id]
        updated = replace(
            n,
            last_sent_at=now or _utcnow(),
            send_count=n.send_count + 1,
        )
        self._nudges[nudge_id] = updated
        return updated

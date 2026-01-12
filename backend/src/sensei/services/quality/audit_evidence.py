"""Audit & Regulatory Evidence Packs (Development Plan 21.9).

Implements:
- One-Click Audit Package: bundle procedures, approvals, training, calibration certs.
- Evidence Integrity: digital signing/hashing of critical audit records.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class EvidenceType(str, Enum):
    PROCEDURE = "procedure"
    APPROVAL = "approval"
    TRAINING_RECORD = "training_record"
    CALIBRATION_CERT = "calibration_cert"
    INSPECTION_REPORT = "inspection_report"
    NC_DISPOSITION = "nc_disposition"


class PackageStatus(str, Enum):
    DRAFT = "draft"
    SEALED = "sealed"
    EXPORTED = "exported"


_AUDIT_ADMIN_ROLES: set[str] = {"admin", "quality", "gm", "exec", "ceo", "auditor"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_hash(data: bytes) -> str:
    """SHA-256 hash of data, returned as hex."""
    return hashlib.sha256(data).hexdigest()


def _sign_data(data: bytes, secret_key: bytes) -> str:
    """HMAC-SHA256 signature."""
    return hmac.new(secret_key, data, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    id: UUID
    evidence_type: EvidenceType
    title: str
    content: dict[str, Any]
    content_hash: str
    created_at: datetime
    created_by: UUID


@dataclass
class AuditPackage:
    id: UUID
    name: str
    description: str
    status: PackageStatus
    evidence_ids: list[UUID]
    package_hash: str | None
    signature: str | None
    created_at: datetime
    created_by: UUID
    sealed_at: datetime | None = None


class AuditEvidenceService:
    """In-memory audit evidence packing service."""

    def __init__(self, signing_key: bytes | None = None) -> None:
        self._evidence: dict[UUID, EvidenceRecord] = {}
        self._packages: dict[UUID, AuditPackage] = {}
        self._signing_key = signing_key or b"sensei-default-signing-key"

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_AUDIT_ADMIN_ROLES)) > 0

    # ---- Evidence Records ----

    def create_evidence(
        self,
        *,
        evidence_type: EvidenceType,
        title: str,
        content: dict[str, Any],
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> EvidenceRecord:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create evidence records")

        content_bytes = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        content_hash = _compute_hash(content_bytes)

        record = EvidenceRecord(
            id=uuid4(),
            evidence_type=evidence_type,
            title=title.strip(),
            content=content,
            content_hash=content_hash,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._evidence[record.id] = record
        return record

    def list_evidence(
        self,
        *,
        actor_roles: Iterable[str],
        evidence_type: EvidenceType | None = None,
    ) -> list[EvidenceRecord]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view evidence records")

        result = list(self._evidence.values())
        if evidence_type:
            result = [e for e in result if e.evidence_type == evidence_type]
        result.sort(key=lambda e: e.created_at, reverse=True)
        return result

    def verify_evidence_integrity(
        self,
        evidence_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> bool:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to verify evidence")
        if evidence_id not in self._evidence:
            raise KeyError("Evidence not found")

        record = self._evidence[evidence_id]
        content_bytes = json.dumps(record.content, sort_keys=True, default=str).encode("utf-8")
        computed = _compute_hash(content_bytes)
        return computed == record.content_hash

    # ---- Audit Packages ----

    def create_package(
        self,
        *,
        name: str,
        description: str,
        evidence_ids: list[UUID],
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> AuditPackage:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create audit packages")

        for eid in evidence_ids:
            if eid not in self._evidence:
                raise KeyError(f"Evidence {eid} not found")

        package = AuditPackage(
            id=uuid4(),
            name=name.strip(),
            description=description,
            status=PackageStatus.DRAFT,
            evidence_ids=list(evidence_ids),
            package_hash=None,
            signature=None,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._packages[package.id] = package
        return package

    def add_evidence_to_package(
        self,
        package_id: UUID,
        evidence_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> AuditPackage:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to modify audit packages")
        if package_id not in self._packages:
            raise KeyError("Package not found")
        if evidence_id not in self._evidence:
            raise KeyError("Evidence not found")

        package = self._packages[package_id]
        if package.status != PackageStatus.DRAFT:
            raise ValueError("Cannot modify sealed package")

        if evidence_id not in package.evidence_ids:
            package.evidence_ids.append(evidence_id)

        return package

    def seal_package(
        self,
        package_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> AuditPackage:
        """Seal the package with hash and signature."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to seal audit packages")
        if package_id not in self._packages:
            raise KeyError("Package not found")

        package = self._packages[package_id]
        if package.status != PackageStatus.DRAFT:
            raise ValueError("Package already sealed")

        # Build combined hash of all evidence hashes.
        evidence_hashes = sorted(
            self._evidence[eid].content_hash for eid in package.evidence_ids
        )
        combined = "|".join(evidence_hashes)
        combined_bytes = combined.encode("utf-8")
        package_hash = _compute_hash(combined_bytes)

        # Sign the hash.
        signature = _sign_data(package_hash.encode("utf-8"), self._signing_key)

        package.package_hash = package_hash
        package.signature = signature
        package.status = PackageStatus.SEALED
        package.sealed_at = _utcnow()

        return package

    def verify_package_integrity(
        self,
        package_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> dict[str, bool]:
        """Verify package hash and signature."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to verify packages")
        if package_id not in self._packages:
            raise KeyError("Package not found")

        package = self._packages[package_id]
        if package.status == PackageStatus.DRAFT:
            raise ValueError("Package not sealed")

        # Recompute hash.
        evidence_hashes = sorted(
            self._evidence[eid].content_hash for eid in package.evidence_ids
        )
        combined = "|".join(evidence_hashes)
        combined_bytes = combined.encode("utf-8")
        computed_hash = _compute_hash(combined_bytes)

        hash_valid = computed_hash == package.package_hash

        # Verify signature.
        expected_sig = _sign_data(computed_hash.encode("utf-8"), self._signing_key)
        sig_valid = hmac.compare_digest(expected_sig, package.signature or "")

        return {"hash_valid": hash_valid, "signature_valid": sig_valid}

    def list_packages(
        self,
        *,
        actor_roles: Iterable[str],
        status: PackageStatus | None = None,
    ) -> list[AuditPackage]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view audit packages")

        result = list(self._packages.values())
        if status:
            result = [p for p in result if p.status == status]
        result.sort(key=lambda p: p.created_at, reverse=True)
        return result

    def export_package(
        self,
        package_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> dict[str, Any]:
        """Export package as a portable dict (JSON-serializable)."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to export packages")
        if package_id not in self._packages:
            raise KeyError("Package not found")

        package = self._packages[package_id]
        if package.status == PackageStatus.DRAFT:
            raise ValueError("Cannot export draft package")

        evidence_list = [
            {
                "id": str(self._evidence[eid].id),
                "type": self._evidence[eid].evidence_type.value,
                "title": self._evidence[eid].title,
                "content": self._evidence[eid].content,
                "content_hash": self._evidence[eid].content_hash,
            }
            for eid in package.evidence_ids
        ]

        package.status = PackageStatus.EXPORTED

        return {
            "package_id": str(package.id),
            "name": package.name,
            "description": package.description,
            "package_hash": package.package_hash,
            "signature": package.signature,
            "sealed_at": package.sealed_at.isoformat() if package.sealed_at else None,
            "evidence": evidence_list,
        }

"""Tests for Audit & Regulatory Evidence Packs service."""

from __future__ import annotations

from uuid import uuid4

import pytest

from sensei.services.audit_evidence import (
    AuditEvidenceService,
    AuditPackage,
    EvidenceRecord,
    EvidenceType,
    PackageStatus,
)


@pytest.fixture
def svc() -> AuditEvidenceService:
    return AuditEvidenceService(signing_key=b"test-signing-key")


ADMIN_ROLES = ("admin",)
QUALITY_ROLES = ("quality",)
AUDITOR_ROLES = ("auditor",)
VIEWER_ROLES = ("viewer",)


class TestEvidenceRecords:
    def test_create_evidence_requires_role(self, svc: AuditEvidenceService) -> None:
        with pytest.raises(PermissionError):
            svc.create_evidence(
                evidence_type=EvidenceType.PROCEDURE,
                title="SOP-001",
                content={"version": "1.0", "steps": ["a", "b"]},
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

        record = svc.create_evidence(
            evidence_type=EvidenceType.TRAINING_RECORD,
            title="Training - Safety 101",
            content={"employee_id": "E001", "completed": True},
            actor_user_id=uuid4(),
            actor_roles=QUALITY_ROLES,
        )

        assert isinstance(record, EvidenceRecord)
        assert record.content_hash is not None

    def test_verify_integrity(self, svc: AuditEvidenceService) -> None:
        record = svc.create_evidence(
            evidence_type=EvidenceType.CALIBRATION_CERT,
            title="CMM Calibration",
            content={"equipment_id": "CMM-01", "calibrated_by": "Lab A"},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        is_valid = svc.verify_evidence_integrity(record.id, actor_roles=ADMIN_ROLES)
        assert is_valid is True


class TestAuditPackages:
    def test_create_and_seal_package(self, svc: AuditEvidenceService) -> None:
        e1 = svc.create_evidence(
            evidence_type=EvidenceType.PROCEDURE,
            title="SOP-001",
            content={"text": "procedure"},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        e2 = svc.create_evidence(
            evidence_type=EvidenceType.APPROVAL,
            title="Approval-001",
            content={"approved_by": "Manager"},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        package = svc.create_package(
            name="ISO Audit Q1",
            description="Q1 audit evidence",
            evidence_ids=[e1.id, e2.id],
            actor_user_id=uuid4(),
            actor_roles=AUDITOR_ROLES,
        )

        assert isinstance(package, AuditPackage)
        assert package.status == PackageStatus.DRAFT

        sealed = svc.seal_package(package.id, actor_roles=ADMIN_ROLES)
        assert sealed.status == PackageStatus.SEALED
        assert sealed.package_hash is not None
        assert sealed.signature is not None

    def test_cannot_modify_sealed_package(self, svc: AuditEvidenceService) -> None:
        e1 = svc.create_evidence(
            evidence_type=EvidenceType.PROCEDURE,
            title="SOP",
            content={"x": 1},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        package = svc.create_package(
            name="Test",
            description="Test",
            evidence_ids=[e1.id],
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.seal_package(package.id, actor_roles=ADMIN_ROLES)

        e2 = svc.create_evidence(
            evidence_type=EvidenceType.APPROVAL,
            title="New",
            content={"y": 2},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        with pytest.raises(ValueError, match="sealed"):
            svc.add_evidence_to_package(package.id, e2.id, actor_roles=ADMIN_ROLES)

    def test_verify_package_integrity(self, svc: AuditEvidenceService) -> None:
        e1 = svc.create_evidence(
            evidence_type=EvidenceType.INSPECTION_REPORT,
            title="Inspection",
            content={"result": "pass"},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        package = svc.create_package(
            name="Inspection Pack",
            description="Audit",
            evidence_ids=[e1.id],
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.seal_package(package.id, actor_roles=ADMIN_ROLES)

        result = svc.verify_package_integrity(package.id, actor_roles=ADMIN_ROLES)
        assert result["hash_valid"] is True
        assert result["signature_valid"] is True

    def test_export_package(self, svc: AuditEvidenceService) -> None:
        e1 = svc.create_evidence(
            evidence_type=EvidenceType.NC_DISPOSITION,
            title="NC-001",
            content={"disposition": "rework"},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        package = svc.create_package(
            name="NC Pack",
            description="Non-conformance",
            evidence_ids=[e1.id],
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.seal_package(package.id, actor_roles=ADMIN_ROLES)

        export = svc.export_package(package.id, actor_roles=ADMIN_ROLES)
        assert "package_id" in export
        assert "evidence" in export
        assert len(export["evidence"]) == 1
        assert export["evidence"][0]["type"] == "nc_disposition"

        # Status should be exported.
        assert svc._packages[package.id].status == PackageStatus.EXPORTED


class TestRoleEnforcement:
    def test_list_requires_role(self, svc: AuditEvidenceService) -> None:
        svc.create_evidence(
            evidence_type=EvidenceType.PROCEDURE,
            title="SOP",
            content={},
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        with pytest.raises(PermissionError):
            svc.list_evidence(actor_roles=VIEWER_ROLES)

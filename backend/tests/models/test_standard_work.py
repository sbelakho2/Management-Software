"""
Tests for Standard Work models.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from sensei.models.standard_work import (
    StandardWork,
    StandardWorkType,
    StandardWorkStatus,
    StandardWorkVersion,
)


class TestStandardWorkModel:
    """Test cases for StandardWork model."""

    def test_standard_work_creation_basic(self):
        """Test basic standard work document creation."""
        sw = StandardWork(
            document_number="SW-001",
            title="Assembly Procedure",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.DRAFT,
            version=1,
        )

        assert sw.document_number == "SW-001"
        assert sw.title == "Assembly Procedure"
        assert sw.document_type == StandardWorkType.WORK_INSTRUCTION
        assert sw.status == StandardWorkStatus.DRAFT
        assert sw.version == 1

    def test_standard_work_creation_full(self):
        """Test standard work with all fields."""
        sw = StandardWork(
            document_number="SW-002",
            title="CNC Setup Procedure",
            description="Complete setup procedure for CNC milling",
            document_type=StandardWorkType.STANDARD_OPERATING_PROCEDURE,
            status=StandardWorkStatus.APPROVED,
            version=3,
            revision_code="C",
            approved_by_id=2,
            approved_at=datetime.utcnow(),
            effective_date=date.today(),
            product_id=5,
            station_id=10,
            requires_training=True,
            training_duration_minutes=60,
        )

        assert sw.document_type == StandardWorkType.STANDARD_OPERATING_PROCEDURE
        assert sw.status == StandardWorkStatus.APPROVED
        assert sw.version == 3
        assert sw.revision_code == "C"
        assert sw.requires_training is True
        assert sw.training_duration_minutes == 60

    def test_standard_work_type_values(self):
        """Test all standard work type values."""
        for sw_type in StandardWorkType:
            sw = StandardWork(
                document_number=f"SW-{sw_type.value}",
                title=f"Test {sw_type.value}",
                document_type=sw_type,
            )
            assert sw.document_type == sw_type

    def test_standard_work_status_values(self):
        """Test all status values."""
        for status in StandardWorkStatus:
            sw = StandardWork(
                document_number=f"SW-{status.value}",
                title=f"Test {status.value}",
                document_type=StandardWorkType.WORK_INSTRUCTION,
                status=status,
            )
            assert sw.status == status

    def test_standard_work_is_current(self):
        """Test is_current property (approved status)."""
        sw_approved = StandardWork(
            document_number="SW-APPROVED",
            title="Approved SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.APPROVED,
        )

        sw_draft = StandardWork(
            document_number="SW-DRAFT",
            title="Draft SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.DRAFT,
        )

        sw_obsolete = StandardWork(
            document_number="SW-OBSOLETE",
            title="Obsolete SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.OBSOLETE,
        )

        assert sw_approved.is_current is True
        assert sw_draft.is_current is False
        assert sw_obsolete.is_current is False

    def test_standard_work_is_expired(self):
        """Test is_expired property."""
        sw_expired = StandardWork(
            document_number="SW-EXPIRED",
            title="Expired SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.APPROVED,
            expiration_date=date.today() - timedelta(days=10),
        )

        sw_future = StandardWork(
            document_number="SW-FUTURE",
            title="Future SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.APPROVED,
            expiration_date=date.today() + timedelta(days=30),
        )

        sw_no_expiry = StandardWork(
            document_number="SW-NOEXP",
            title="No Expiry SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.APPROVED,
        )

        assert sw_expired.is_expired is True
        assert sw_future.is_expired is False
        assert sw_no_expiry.is_expired is False

    def test_standard_work_needs_review(self):
        """Test needs_review property."""
        sw_needs_review = StandardWork(
            document_number="SW-REVIEW",
            title="Needs Review SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            review_date=date.today() - timedelta(days=1),
        )

        sw_not_due = StandardWork(
            document_number="SW-NOTDUE",
            title="Not Due SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            review_date=date.today() + timedelta(days=30),
        )

        sw_no_review = StandardWork(
            document_number="SW-NOREVIEW",
            title="No Review SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        )

        assert sw_needs_review.needs_review is True
        assert sw_not_due.needs_review is False
        assert sw_no_review.needs_review is False

    def test_standard_work_step_count(self):
        """Test step_count property."""
        sw_with_steps = StandardWork(
            document_number="SW-STEPS",
            title="With Steps SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            content_json={
                "steps": [
                    {"sequence": 1, "instruction": "Step 1"},
                    {"sequence": 2, "instruction": "Step 2"},
                    {"sequence": 3, "instruction": "Step 3"},
                ]
            },
        )

        sw_no_steps = StandardWork(
            document_number="SW-NOSTEPS",
            title="No Steps SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            content_json={},
        )

        sw_null_content = StandardWork(
            document_number="SW-NULL",
            title="Null Content SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        )

        assert sw_with_steps.step_count == 3
        assert sw_no_steps.step_count == 0
        assert sw_null_content.step_count == 0

    def test_standard_work_full_document_id(self):
        """Test full_document_id property."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            revision_code="B",
        )

        assert sw.full_document_id == "SW-001-RevB"

    def test_standard_work_can_submit_for_approval(self):
        """Test can_submit_for_approval method."""
        sw_draft = StandardWork(
            document_number="SW-DRAFT",
            title="Draft SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.DRAFT,
        )

        sw_pending = StandardWork(
            document_number="SW-PENDING",
            title="Pending SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.PENDING_APPROVAL,
        )

        assert sw_draft.can_submit_for_approval() is True
        assert sw_pending.can_submit_for_approval() is False

    def test_standard_work_can_approve(self):
        """Test can_approve method."""
        sw_pending = StandardWork(
            document_number="SW-PENDING",
            title="Pending SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.PENDING_APPROVAL,
        )

        sw_draft = StandardWork(
            document_number="SW-DRAFT",
            title="Draft SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            status=StandardWorkStatus.DRAFT,
        )

        assert sw_pending.can_approve() is True
        assert sw_draft.can_approve() is False

    def test_standard_work_create_new_version(self):
        """Test create_new_version method."""
        sw = StandardWork(
            document_number="SW-001",
            title="Original SW",
            description="Original description",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            version=1,
            revision_code="A",
            status=StandardWorkStatus.APPROVED,
            product_id=5,
            station_id=10,
            content_json={"steps": [{"sequence": 1, "instruction": "Step 1"}]},
        )
        sw.id = 1

        new_version = sw.create_new_version()

        assert new_version.document_number == "SW-001"
        assert new_version.version == 2
        assert new_version.revision_code == "B"
        assert new_version.status == StandardWorkStatus.DRAFT
        assert new_version.previous_version_id == 1
        assert new_version.product_id == 5
        assert new_version.station_id == 10

    def test_standard_work_repr(self):
        """Test string representation."""
        sw = StandardWork(
            document_number="SW-TEST",
            title="Test SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        )
        sw.id = 1

        assert "StandardWork" in repr(sw)
        assert "SW-TEST" in repr(sw)


class TestStandardWorkVersionModel:
    """Test cases for StandardWorkVersion model."""

    def test_version_creation(self):
        """Test version snapshot creation."""
        version = StandardWorkVersion(
            standard_work_id=1,
            version=2,
            revision_code="B",
            content_json={"steps": [{"sequence": 1, "instruction": "Step 1"}]},
            change_summary="Updated step 1",
            created_by_id=3,
        )

        assert version.standard_work_id == 1
        assert version.version == 2
        assert version.revision_code == "B"
        assert version.created_by_id == 3
        assert version.change_summary == "Updated step 1"

    def test_version_repr(self):
        """Test string representation."""
        version = StandardWorkVersion(
            standard_work_id=1,
            version=3,
            revision_code="C",
            created_by_id=1,
        )

        assert "StandardWorkVersion" in repr(version)


class TestStandardWorkRelationships:
    """Test Standard Work relationships."""

    def test_standard_work_has_versions_list(self):
        """Test that standard work has versions list."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        )
        assert hasattr(sw, 'versions')

    def test_standard_work_has_product_relationship(self):
        """Test that standard work has product relationship."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        )
        assert hasattr(sw, 'product')

    def test_standard_work_has_station_relationship(self):
        """Test that standard work has station relationship."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
        )
        assert hasattr(sw, 'station')


class TestStandardWorkValidation:
    """Test validation constraints."""

    def test_explicit_version_is_one(self):
        """Test explicit version is 1."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            version=1,
        )
        assert sw.version == 1

    def test_explicit_revision_code_is_a(self):
        """Test explicit revision code is A."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            revision_code="A",
        )
        assert sw.revision_code == "A"

    def test_explicit_requires_training_is_true(self):
        """Test explicit requires_training is True."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            requires_training=True,
        )
        assert sw.requires_training is True

    def test_explicit_training_duration_is_30(self):
        """Test explicit training_duration_minutes is 30."""
        sw = StandardWork(
            document_number="SW-001",
            title="Test",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            training_duration_minutes=30,
        )
        assert sw.training_duration_minutes == 30


class TestStandardWorkEdgeCases:
    """Test edge cases for Standard Work models."""

    def test_standard_work_with_content_json(self):
        """Test standard work with complex content JSON."""
        content = {
            "steps": [
                {
                    "sequence": 1,
                    "instruction": "Prepare workspace",
                    "estimated_time_seconds": 30,
                    "safety_notes": "Wear gloves",
                    "quality_checkpoints": ["Check cleanliness"],
                    "tools_required": ["Cleaning cloth"],
                    "critical": False,
                },
                {
                    "sequence": 2,
                    "instruction": "Insert component",
                    "estimated_time_seconds": 60,
                    "critical": True,
                },
            ],
            "safety_warnings": ["Always wear safety glasses"],
            "required_ppe": ["Safety glasses", "Gloves"],
            "required_tools": ["Torque wrench"],
        }

        sw = StandardWork(
            document_number="SW-COMPLEX",
            title="Complex SW",
            document_type=StandardWorkType.WORK_INSTRUCTION,
            content_json=content,
        )

        assert sw.step_count == 2
        assert sw.content_json["steps"][1]["critical"] is True

    def test_version_with_large_content(self):
        """Test version with large content snapshot."""
        large_content = {
            "steps": [{"sequence": i, "instruction": f"Step {i}"} for i in range(100)]
        }

        version = StandardWorkVersion(
            standard_work_id=1,
            version=1,
            revision_code="A",
            content_json=large_content,
            created_by_id=1,
        )

        assert version.content_json is not None
        assert len(version.content_json["steps"]) == 100

    def test_multiple_versions(self):
        """Test creating multiple versions."""
        versions = []
        for i in range(1, 6):
            rev_code = chr(ord("A") + i - 1)
            version = StandardWorkVersion(
                standard_work_id=1,
                version=i,
                revision_code=rev_code,
                created_by_id=1,
            )
            versions.append(version)

        assert len(versions) == 5
        assert versions[0].revision_code == "A"
        assert versions[4].revision_code == "E"

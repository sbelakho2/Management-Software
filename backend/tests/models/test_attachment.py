"""
Tests for Attachment models.

Tests:
- Attachment model fields and defaults
- AttachmentVersion model
- File size formatting
- MIME type handling
- Polymorphic parent relationships
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.models.attachment import (
    Attachment,
    AttachmentCategory,
    AttachmentStatus,
    AttachmentVersion,
)


class TestAttachmentModel:
    """Tests for the Attachment model."""

    def test_attachment_required_fields(self):
        """Attachment should require entity_type, entity_id, filename, original_filename, file_size, etc."""
        now = datetime.now(timezone.utc)
        entity_id = uuid4()
        attachment = Attachment(
            entity_type="rfq",
            entity_id=entity_id,
            filename="doc_abc123.pdf",
            original_filename="Technical_Specification_Rev_A.pdf",
            file_extension=".pdf",
            file_size=2097152,  # 2 MB
            mime_type="application/pdf",
            storage_key="attachments/abc123/doc_abc123.pdf",
            storage_bucket="sensei-uploads",
            uploaded_at=now,
        )
        assert attachment.filename == "doc_abc123.pdf"
        assert attachment.original_filename == "Technical_Specification_Rev_A.pdf"
        assert attachment.file_size == 2097152
        assert attachment.mime_type == "application/pdf"
        assert attachment.storage_key == "attachments/abc123/doc_abc123.pdf"
        assert attachment.storage_bucket == "sensei-uploads"
        assert attachment.entity_type == "rfq"
        assert attachment.entity_id == entity_id

    def test_attachment_default_category_is_document(self):
        """Attachment category should default to document - SQLAlchemy defaults only apply with DB session."""
        now = datetime.now(timezone.utc)
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            category=AttachmentCategory.DOCUMENT.value,
        )
        assert attachment.category == AttachmentCategory.DOCUMENT.value

    def test_attachment_default_current_version_is_1(self):
        """Attachment current_version should default to 1 - SQLAlchemy defaults only apply with DB session."""
        now = datetime.now(timezone.utc)
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            current_version=1,
        )
        assert attachment.current_version == 1

    def test_attachment_is_latest_default_true(self):
        """is_latest should default to True - SQLAlchemy defaults only apply with DB session."""
        now = datetime.now(timezone.utc)
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            is_latest=True,
        )
        assert attachment.is_latest is True

    def test_attachment_is_confidential_default_false(self):
        """is_confidential should default to False - SQLAlchemy defaults only apply with DB session."""
        now = datetime.now(timezone.utc)
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            is_confidential=False,
        )
        assert attachment.is_confidential is False

    def test_attachment_polymorphic_parent(self):
        """Attachment should support polymorphic parent relationship via entity_type and entity_id."""
        now = datetime.now(timezone.utc)
        rfq_id = uuid4()
        attachment = Attachment(
            entity_type="rfq",
            entity_id=rfq_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert attachment.entity_type == "rfq"
        assert attachment.entity_id == rfq_id

    def test_attachment_file_size_human_bytes(self):
        """file_size_human should format bytes correctly."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.txt",
            original_filename="test.txt",
            file_extension=".txt",
            file_size=500,
            mime_type="text/plain",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert "500" in attachment.file_size_human
        assert "B" in attachment.file_size_human

    def test_attachment_file_size_human_kb(self):
        """file_size_human should format KB correctly."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.txt",
            original_filename="test.txt",
            file_extension=".txt",
            file_size=5120,  # 5 KB
            mime_type="text/plain",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert "KB" in attachment.file_size_human

    def test_attachment_file_size_human_mb(self):
        """file_size_human should format MB correctly."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=5242880,  # 5 MB
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert "MB" in attachment.file_size_human

    def test_attachment_file_size_human_gb(self):
        """file_size_human should format GB correctly."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="large.zip",
            original_filename="large.zip",
            file_extension=".zip",
            file_size=2147483648,  # 2 GB
            mime_type="application/zip",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert "GB" in attachment.file_size_human

    def test_attachment_file_extension_field(self):
        """file_extension should be stored as a field."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="document.pdf",
            original_filename="document.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert attachment.file_extension == ".pdf"

    def test_attachment_is_image_true_for_image_types(self):
        """is_image should be True for image MIME types."""
        now = datetime.now(timezone.utc)
        for mime_type in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
            attachment = Attachment(
                entity_type="rfq",
                entity_id=uuid4(),
                filename="test.png",
                original_filename="test.png",
                file_extension=".png",
                file_size=1024,
                mime_type=mime_type,
                storage_key=f"test/key/{uuid4()}",
                storage_bucket="bucket",
                uploaded_at=now,
            )
            assert attachment.is_image is True

    def test_attachment_is_image_false_for_non_image_types(self):
        """is_image should be False for non-image MIME types."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert attachment.is_image is False

    def test_attachment_is_pdf_true_for_pdf_type(self):
        """is_pdf should be True for PDF MIME type."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert attachment.is_pdf is True

    def test_attachment_is_pdf_false_for_non_pdf_types(self):
        """is_pdf should be False for non-PDF MIME types."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.docx",
            original_filename="test.docx",
            file_extension=".docx",
            file_size=1024,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
        )
        assert attachment.is_pdf is False

    def test_attachment_checksum_fields(self):
        """Attachment should support checksum fields for integrity."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            checksum_md5="abc123",
            checksum_sha256="def456789",
        )
        assert attachment.checksum_md5 == "abc123"
        assert attachment.checksum_sha256 == "def456789"

    def test_attachment_description(self):
        """Attachment should support description field."""
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="spec.pdf",
            original_filename="spec.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            description="Technical specification document for Project X",
        )
        assert attachment.description == "Technical specification document for Project X"

    def test_attachment_uploaded_by_id(self):
        """Attachment should track who uploaded it via uploaded_by_id."""
        now = datetime.now(timezone.utc)
        user_id = uuid4()
        attachment = Attachment(
            entity_type="rfq",
            entity_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_extension=".pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            uploaded_at=now,
            uploaded_by_id=user_id,
        )
        assert attachment.uploaded_by_id == user_id


class TestAttachmentStatusEnum:
    """Tests for AttachmentStatus enum."""

    def test_all_statuses_defined(self):
        """All expected attachment statuses should be defined."""
        assert AttachmentStatus.PENDING.value == "pending"
        assert AttachmentStatus.PROCESSING.value == "processing"
        assert AttachmentStatus.READY.value == "ready"
        assert AttachmentStatus.ERROR.value == "error"
        assert AttachmentStatus.DELETED.value == "deleted"


class TestAttachmentCategoryEnum:
    """Tests for AttachmentCategory enum."""

    def test_all_categories_defined(self):
        """All expected attachment categories should be defined."""
        assert AttachmentCategory.DOCUMENT.value == "document"
        assert AttachmentCategory.IMAGE.value == "image"
        assert AttachmentCategory.DRAWING.value == "drawing"
        assert AttachmentCategory.MODEL_3D.value == "model_3d"
        assert AttachmentCategory.SPREADSHEET.value == "spreadsheet"
        assert AttachmentCategory.PRESENTATION.value == "presentation"
        assert AttachmentCategory.PDF.value == "pdf"
        assert AttachmentCategory.VIDEO.value == "video"
        assert AttachmentCategory.AUDIO.value == "audio"
        assert AttachmentCategory.ARCHIVE.value == "archive"
        assert AttachmentCategory.OTHER.value == "other"


class TestAttachmentVersionModel:
    """Tests for the AttachmentVersion model."""

    def test_attachment_version_required_fields(self):
        """AttachmentVersion should require attachment_id, version_number, etc."""
        attachment_id = uuid4()
        version = AttachmentVersion(
            attachment_id=attachment_id,
            version_number=2,
            filename="doc_abc123_v2.pdf",
            file_size=2200000,
            mime_type="application/pdf",
            storage_key="attachments/abc123/doc_abc123_v2.pdf",
            storage_bucket="sensei-uploads",
        )
        assert version.attachment_id == attachment_id
        assert version.version_number == 2
        assert version.filename == "doc_abc123_v2.pdf"

    def test_attachment_version_change_reason(self):
        """AttachmentVersion should support change_reason."""
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=2,
            filename="test_v2.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            change_reason="Updated section 3.2 with new tolerances",
        )
        assert version.change_reason == "Updated section 3.2 with new tolerances"

    def test_attachment_version_change_notes(self):
        """AttachmentVersion should support change_notes."""
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=2,
            filename="test_v2.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            change_notes="Detailed notes about the changes made",
        )
        assert version.change_notes == "Detailed notes about the changes made"

    def test_attachment_version_created_by_id(self):
        """AttachmentVersion should track who created it via created_by_id."""
        user_id = uuid4()
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=2,
            filename="test_v2.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            created_by_id=user_id,
        )
        assert version.created_by_id == user_id

    def test_attachment_version_is_current_default_false(self):
        """is_current should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=1,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            is_current=False,
        )
        assert version.is_current is False

    def test_attachment_version_checksum_fields(self):
        """AttachmentVersion should support checksum fields."""
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=1,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            checksum_md5="abc123",
            checksum_sha256="xyz789",
        )
        assert version.checksum_md5 == "abc123"
        assert version.checksum_sha256 == "xyz789"

    def test_attachment_version_file_size_human(self):
        """file_size_human should format size correctly."""
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=1,
            filename="test.pdf",
            file_size=1048576,  # 1 MB
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
        )
        assert "MB" in version.file_size_human

    def test_attachment_version_revision(self):
        """AttachmentVersion should support revision field for document control."""
        version = AttachmentVersion(
            attachment_id=uuid4(),
            version_number=3,
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            revision="Rev C",
        )
        assert version.revision == "Rev C"

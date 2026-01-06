"""Tests for Attachment API endpoints.

Full test coverage for attachment operations:
- Attachment CRUD
- Version management
- Entity-based queries
- Soft delete and restore
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.attachments import (
    AttachmentCreate,
    AttachmentUpdate,
    create_attachment_metadata,
    get_attachment,
    list_attachments,
    update_attachment,
    delete_attachment,
    restore_attachment,
    list_versions,
    get_version,
    get_entity_attachments,
    get_my_uploads,
    get_recent_attachments,
    get_attachments_by_category,
    get_confidential_attachments,
)
from sensei.api.exceptions import NotFoundError, ConflictError
from sensei.models.attachment import (
    Attachment,
    AttachmentVersion,
    AttachmentCategory,
)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


# =============================================================================
# Attachment CRUD Tests
# =============================================================================


class TestAttachmentCRUD:
    """Tests for attachment CRUD operations."""

    @pytest.fixture
    def sample_attachment_data(self):
        """Sample attachment data."""
        return {
            "id": uuid4(),
            "entity_type": "rfq",
            "entity_id": uuid4(),
            "filename": "document.pdf",
            "original_filename": "document.pdf",
            "file_extension": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1024,
            "storage_bucket": "attachments",
            "storage_key": "rfq/abc123/document.pdf",
            "category": AttachmentCategory.PDF.value,
            "title": "RFQ Document",
            "description": "Attachment for RFQ",
            "current_version": 1,
            "is_latest": True,
            "document_number": "DOC-001",
            "revision": "A",
            "uploaded_by_id": uuid4(),
            "uploaded_at": datetime.now(timezone.utc),
            "is_confidential": False,
            "access_level": None,
            "scan_status": "ready",
            "scanned_at": None,
            "checksum_md5": "abc123",
            "checksum_sha256": "xyz789",
            "has_preview": False,
            "preview_storage_key": None,
            "has_thumbnail": False,
            "thumbnail_storage_key": None,
            "tags": ["rfq", "important"],
            "custom_metadata": None,
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def create_mock_attachment(self, data: dict, **overrides) -> MagicMock:
        """Create a mock attachment."""
        attachment = MagicMock(spec=Attachment)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(attachment, key, value)
        # Computed properties
        attachment.file_size_human = "1.0 KB"
        attachment.is_image = False
        attachment.is_pdf = True
        return attachment

    @pytest.mark.asyncio
    async def test_create_attachment_metadata(self, mock_db, mock_user, sample_attachment_data):
        """Test creating attachment metadata."""
        async def mock_refresh(obj):
            for key, value in sample_attachment_data.items():
                # Skip computed properties
                if key not in ("file_size_human", "is_image", "is_pdf"):
                    setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = AttachmentCreate(
            entity_type="rfq",
            entity_id=sample_attachment_data["entity_id"],
            filename="document.pdf",
            title="RFQ Document",
        )
        result = await create_attachment_metadata(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message

    @pytest.mark.asyncio
    async def test_get_attachment(self, mock_db, mock_user, sample_attachment_data):
        """Test getting an attachment."""
        attachment = self.create_mock_attachment(sample_attachment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = attachment
        mock_db.execute.return_value = mock_result

        result = await get_attachment(sample_attachment_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.filename == "document.pdf"

    @pytest.mark.asyncio
    async def test_get_attachment_not_found(self, mock_db, mock_user):
        """Test getting non-existent attachment."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_attachment(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_attachments(self, mock_db, mock_user, sample_attachment_data):
        """Test listing attachments."""
        attachments = [self.create_mock_attachment(sample_attachment_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = attachments
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_attachments(
            mock_db,
            mock_user,
            entity_type=None,
            entity_id=None,
            category=None,
            is_confidential=None,
            search=None,
            include_deleted=False,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_list_attachments_filtered(self, mock_db, mock_user, sample_attachment_data):
        """Test listing attachments with filters."""
        attachments = [self.create_mock_attachment(sample_attachment_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = attachments
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_attachments(
            mock_db,
            mock_user,
            entity_type="rfq",
            entity_id=sample_attachment_data["entity_id"],
            category=AttachmentCategory.PDF,
            is_confidential=False,
            search="document",
            include_deleted=False,
            page=1,
            page_size=20,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_attachment(self, mock_db, mock_user, sample_attachment_data):
        """Test updating attachment metadata."""
        attachment = self.create_mock_attachment(sample_attachment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = attachment
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Title"

        mock_db.refresh = mock_refresh

        data = AttachmentUpdate(title="Updated Title")
        result = await update_attachment(
            sample_attachment_data["id"],
            data,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_delete_attachment_soft(self, mock_db, mock_user, sample_attachment_data):
        """Test soft deleting an attachment."""
        attachment = self.create_mock_attachment(sample_attachment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = attachment
        mock_db.execute.return_value = mock_result

        result = await delete_attachment(
            sample_attachment_data["id"],
            mock_db,
            mock_user,
            hard_delete=False,
        )

        assert result.success is True
        assert "deleted" in result.message.lower()

    @pytest.mark.asyncio
    async def test_delete_attachment_hard(self, mock_db, mock_user, sample_attachment_data):
        """Test hard deleting an attachment."""
        attachment = self.create_mock_attachment(sample_attachment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = attachment
        mock_db.execute.return_value = mock_result

        result = await delete_attachment(
            sample_attachment_data["id"],
            mock_db,
            mock_user,
            hard_delete=True,
        )

        assert result.success is True
        mock_db.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_already_deleted(self, mock_db, mock_user, sample_attachment_data):
        """Test deleting already deleted attachment."""
        attachment = self.create_mock_attachment(sample_attachment_data, is_deleted=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = attachment
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await delete_attachment(
                sample_attachment_data["id"],
                mock_db,
                mock_user,
                hard_delete=False,
            )

    @pytest.mark.asyncio
    async def test_restore_attachment(self, mock_db, mock_user, sample_attachment_data):
        """Test restoring a soft-deleted attachment."""
        attachment = self.create_mock_attachment(sample_attachment_data, is_deleted=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = attachment
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await restore_attachment(sample_attachment_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "restored" in result.message.lower()


# =============================================================================
# Version Tests
# =============================================================================


class TestAttachmentVersions:
    """Tests for attachment version management."""

    @pytest.fixture
    def sample_version_data(self):
        """Sample version data."""
        return {
            "id": uuid4(),
            "attachment_id": uuid4(),
            "version_number": 1,
            "filename": "document.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "storage_bucket": "attachments",
            "storage_key": "rfq/abc123/v1/document.pdf",
            "checksum_md5": "abc123",
            "checksum_sha256": "xyz789",
            "created_by_id": uuid4(),
            "change_reason": "Initial upload",
            "change_notes": None,
            "revision": "A",
            "is_current": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def sample_attachment_data(self):
        """Sample attachment data."""
        return {
            "id": uuid4(),
            "entity_type": "rfq",
            "entity_id": uuid4(),
            "filename": "document.pdf",
            "current_version": 2,
        }

    def create_mock_version(self, data: dict, **overrides) -> MagicMock:
        """Create a mock version."""
        version = MagicMock(spec=AttachmentVersion)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(version, key, value)
        version.file_size_human = "1.0 KB"
        return version

    def create_mock_attachment(self, data: dict) -> MagicMock:
        """Create a mock attachment."""
        attachment = MagicMock(spec=Attachment)
        for key, value in data.items():
            setattr(attachment, key, value)
        return attachment

    @pytest.mark.asyncio
    async def test_list_versions(self, mock_db, mock_user, sample_attachment_data, sample_version_data):
        """Test listing attachment versions."""
        attachment = self.create_mock_attachment(sample_attachment_data)
        versions = [self.create_mock_version(sample_version_data)]

        mock_attach_result = MagicMock()
        mock_attach_result.scalar_one_or_none.return_value = attachment
        mock_versions_result = MagicMock()
        mock_versions_result.scalars.return_value.all.return_value = versions
        mock_db.execute.side_effect = [mock_attach_result, mock_versions_result]

        result = await list_versions(sample_attachment_data["id"], mock_db, mock_user)

        assert result.success is True
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_list_versions_not_found(self, mock_db, mock_user):
        """Test listing versions for non-existent attachment."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await list_versions(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_version(self, mock_db, mock_user, sample_version_data):
        """Test getting a specific version."""
        version = self.create_mock_version(sample_version_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = version
        mock_db.execute.return_value = mock_result

        result = await get_version(
            sample_version_data["attachment_id"],
            1,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert result.data.version_number == 1

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, mock_db, mock_user):
        """Test getting non-existent version."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_version(uuid4(), 99, mock_db, mock_user)


# =============================================================================
# Query Tests
# =============================================================================


class TestAttachmentQueries:
    """Tests for attachment query endpoints."""

    @pytest.fixture
    def sample_attachment_data(self):
        """Sample attachment data."""
        return {
            "id": uuid4(),
            "entity_type": "rfq",
            "entity_id": uuid4(),
            "filename": "document.pdf",
            "original_filename": "document.pdf",
            "file_extension": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1024,
            "storage_bucket": "attachments",
            "storage_key": "rfq/abc123/document.pdf",
            "category": AttachmentCategory.PDF.value,
            "title": "RFQ Document",
            "description": None,
            "current_version": 1,
            "is_latest": True,
            "document_number": None,
            "revision": None,
            "uploaded_by_id": uuid4(),
            "uploaded_at": datetime.now(timezone.utc),
            "is_confidential": False,
            "access_level": None,
            "scan_status": None,
            "scanned_at": None,
            "checksum_md5": None,
            "checksum_sha256": None,
            "has_preview": False,
            "preview_storage_key": None,
            "has_thumbnail": False,
            "thumbnail_storage_key": None,
            "tags": None,
            "custom_metadata": None,
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def create_mock_attachment(self, data: dict, **overrides) -> MagicMock:
        """Create a mock attachment."""
        attachment = MagicMock(spec=Attachment)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(attachment, key, value)
        attachment.file_size_human = "1.0 KB"
        attachment.is_image = False
        attachment.is_pdf = True
        return attachment

    @pytest.mark.asyncio
    async def test_get_entity_attachments(self, mock_db, mock_user, sample_attachment_data):
        """Test getting attachments for an entity."""
        attachments = [self.create_mock_attachment(sample_attachment_data)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = attachments
        mock_db.execute.return_value = mock_result

        result = await get_entity_attachments(
            "rfq",
            sample_attachment_data["entity_id"],
            mock_db,
            mock_user,
            category=None,
            include_deleted=False,
        )

        assert result.success is True
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_get_my_uploads(self, mock_db, mock_user, sample_attachment_data):
        """Test getting user's uploads."""
        attachments = [self.create_mock_attachment(sample_attachment_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = attachments
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_my_uploads(
            mock_db,
            mock_user,
            category=None,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_recent_attachments(self, mock_db, mock_user, sample_attachment_data):
        """Test getting recent attachments."""
        attachments = [self.create_mock_attachment(sample_attachment_data)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = attachments
        mock_db.execute.return_value = mock_result

        result = await get_recent_attachments(mock_db, mock_user, limit=10)

        assert result.success is True
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_get_attachments_by_category(self, mock_db, mock_user):
        """Test getting attachment counts by category."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("pdf", 5),
            ("image", 3),
            ("document", 2),
        ]
        mock_db.execute.return_value = mock_result

        result = await get_attachments_by_category(mock_db, mock_user)

        assert result.success is True
        assert result.data["pdf"] == 5

    @pytest.mark.asyncio
    async def test_get_confidential_attachments(self, mock_db, mock_user, sample_attachment_data):
        """Test getting confidential attachments."""
        attachments = [
            self.create_mock_attachment(sample_attachment_data, is_confidential=True)
        ]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = attachments
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_confidential_attachments(
            mock_db,
            mock_user,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

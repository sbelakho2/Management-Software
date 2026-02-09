"""
Attachment and versioning models.

Implements:
- Attachment: File attachment with polymorphic relationship
- AttachmentVersion: Version history for attachments
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.user import User


class AttachmentCategory(str, Enum):
    """Category of attachment."""
    
    DOCUMENT = "document"
    IMAGE = "image"
    DRAWING = "drawing"
    MODEL_3D = "model_3d"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    PDF = "pdf"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"


class AttachmentStatus(str, Enum):
    """Status of attachment processing."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class Attachment(Base, TimestampMixin):
    """
    File attachment with polymorphic relationship.
    
    Can be attached to any entity type (RFQ, Quote, A3, etc.).
    Supports versioning for document control.
    """
    
    __tablename__ = "attachments"
    
    # Polymorphic relationship
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # File Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    
    # Storage
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    
    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AttachmentCategory.DOCUMENT.value,
        index=True,
    )
    
    # Metadata
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Versioning
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Document control
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    revision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Upload information
    uploaded_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # Security
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Virus scan
    scan_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Checksum for integrity
    checksum_md5: Mapped[str | None] = mapped_column(String(32), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Preview
    has_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preview_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Thumbnail
    has_thumbnail: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Custom metadata
    custom_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    uploaded_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[uploaded_by_id],
    )
    deleted_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[deleted_by_id],
    )
    
    versions: Mapped[list["AttachmentVersion"]] = relationship(
        "AttachmentVersion",
        back_populates="attachment",
        cascade="all, delete-orphan",
        order_by="desc(AttachmentVersion.version_number)",
        lazy="select",
    )
    
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('rfq', 'quote', 'a3', 'contact', 'account', 'work_order', "
            "'inspection', 'ncr', 'capa', 'invoice', 'purchase_order', 'asset', "
            "'training', 'employee', 'knowledge_pack', 'ticket', 'project', 'general')",
            name="ck_attachments_entity_type_valid",
        ),
        Index("ix_attachments_entity", entity_type, entity_id),
        Index("ix_attachments_entity_category", entity_type, entity_id, category),
        Index(
            "ix_attachments_active",
            entity_type,
            entity_id,
            postgresql_where=(is_deleted == False),  # noqa: E712
        ),
    )
    
    @property
    def file_size_human(self) -> str:
        """Get human-readable file size."""
        size: float = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    @property
    def is_image(self) -> bool:
        """Check if attachment is an image."""
        return self.category == AttachmentCategory.IMAGE.value or self.mime_type.startswith(
            "image/"
        )
    
    @property
    def is_pdf(self) -> bool:
        """Check if attachment is a PDF."""
        return self.mime_type == "application/pdf"


class AttachmentVersion(Base, TimestampMixin):
    """
    Version history for an attachment.
    
    Preserves previous versions for audit and rollback.
    """
    
    __tablename__ = "attachment_versions"
    
    attachment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("attachments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Version
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # File Information (snapshot)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Storage
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    
    # Checksums
    checksum_md5: Mapped[str | None] = mapped_column(String(32), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Who created this version
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Change information
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Revision (document control)
    revision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Is this version the current one?
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    attachment: Mapped["Attachment"] = relationship(
        "Attachment",
        back_populates="versions",
    )
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        Index(
            "ix_attachment_versions_attachment_version",
            attachment_id,
            version_number.desc(),
        ),
        Index(
            "ix_attachment_versions_current",
            attachment_id,
            postgresql_where=(is_current == True),  # noqa: E712
        ),
    )
    
    @property
    def file_size_human(self) -> str:
        """Get human-readable file size."""
        size: float = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

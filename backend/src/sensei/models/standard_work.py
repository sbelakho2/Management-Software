"""
Standard Work models for document management and version control.

Standard Work documents define the standard procedures for
performing operations at work stations.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Any
from uuid import UUID as PyUUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.work_center import Station
    from sensei.models.product import Product
    from sensei.models.user import User
    from sensei.models.quality import CAPA


class StandardWorkStatus(enum.Enum):
    """Status of a standard work document."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    OBSOLETE = "obsolete"


class StandardWorkType(enum.Enum):
    """Type of standard work document."""

    WORK_INSTRUCTION = "work_instruction"
    STANDARD_OPERATING_PROCEDURE = "sop"
    CONTROL_PLAN = "control_plan"
    INSPECTION_INSTRUCTION = "inspection_instruction"
    SETUP_INSTRUCTION = "setup_instruction"
    SAFETY_PROCEDURE = "safety_procedure"
    QUALITY_ALERT = "quality_alert"


class StandardWork(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Standard Work document with version control.

    Documents define standard procedures for performing operations
    and are linked to products and stations.
    """

    __tablename__ = "standard_works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Document identification
    document_number: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Version control
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision_code: Mapped[str] = mapped_column(
        String(10), nullable=False, default="A"
    )  # A, B, C, etc.

    # Document type and classification
    document_type: Mapped[StandardWorkType] = mapped_column(
        Enum(StandardWorkType),
        nullable=False,
        default=StandardWorkType.WORK_INSTRUCTION,
    )

    # Status
    status: Mapped[StandardWorkStatus] = mapped_column(
        Enum(StandardWorkStatus),
        nullable=False,
        default=StandardWorkStatus.DRAFT,
        index=True,
    )

    # Linkages
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )
    station_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=True, index=True
    )

    # Content (JSON structure for steps)
    content_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    """
    Content structure:
    {
        "steps": [
            {
                "sequence": 1,
                "instruction": "Step description...",
                "image_attachment_id": 123,
                "estimated_time_seconds": 30,
                "safety_notes": "PPE required",
                "quality_checkpoints": ["Check dimension A", "Verify torque"],
                "tools_required": ["Torque wrench", "Caliper"],
                "critical": true
            },
            ...
        ],
        "safety_warnings": ["Always wear safety glasses"],
        "required_ppe": ["Safety glasses", "Gloves"],
        "required_tools": ["Torque wrench"],
        "revision_notes": "Added safety checkpoint in step 3"
    }
    """

    # Dates
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Approval tracking
    submitted_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Change tracking
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("standard_works.id"), nullable=True
    )

    # Training linkage
    requires_training: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    training_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )

    # Relationships
    product: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="standard_works"
    )
    station: Mapped[Optional["Station"]] = relationship(
        "Station", back_populates="standard_works"
    )
    submitted_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[submitted_by_id]
    )
    approved_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    previous_version: Mapped[Optional["StandardWork"]] = relationship(
        "StandardWork", remote_side=[id], foreign_keys=[previous_version_id]
    )
    versions: Mapped[list["StandardWorkVersion"]] = relationship(
        "StandardWorkVersion",
        back_populates="standard_work",
        cascade="all, delete-orphan",
        order_by="StandardWorkVersion.version.desc()",
    )
    linked_capas: Mapped[list["CAPA"]] = relationship(
        "CAPA", back_populates="linked_standard_work"
    )

    __table_args__ = (
        UniqueConstraint(
            "document_number", "version", name="uq_standard_work_doc_version"
        ),
        CheckConstraint("version > 0", name="ck_standard_work_version_positive"),
        CheckConstraint(
            "training_duration_minutes >= 0",
            name="ck_standard_work_training_nonnegative",
        ),
    )

    def __repr__(self) -> str:
        return f"<StandardWork(id={self.id}, doc='{self.document_number}', v{self.version})>"

    @property
    def full_document_id(self) -> str:
        """Return full document identifier with version."""
        return f"{self.document_number}-Rev{self.revision_code}"

    @property
    def is_current(self) -> bool:
        """Check if this is the current approved version."""
        return self.status == StandardWorkStatus.APPROVED

    @property
    def is_expired(self) -> bool:
        """Check if document has expired."""
        if self.expiration_date:
            return date.today() > self.expiration_date
        return False

    @property
    def needs_review(self) -> bool:
        """Check if document needs periodic review."""
        if self.review_date:
            return date.today() >= self.review_date
        return False

    @property
    def step_count(self) -> int:
        """Count of steps in the document."""
        if self.content_json and "steps" in self.content_json:
            return len(self.content_json["steps"])
        return 0

    def can_submit_for_approval(self) -> bool:
        """Check if document can be submitted for approval."""
        return self.status == StandardWorkStatus.DRAFT

    def can_approve(self) -> bool:
        """Check if document can be approved."""
        return self.status == StandardWorkStatus.PENDING_APPROVAL

    def create_new_version(self) -> "StandardWork":
        """Create a new draft version of this document."""
        new_rev = chr(ord(self.revision_code) + 1) if self.revision_code else "B"
        return StandardWork(
            document_number=self.document_number,
            title=self.title,
            description=self.description,
            version=self.version + 1,
            revision_code=new_rev,
            document_type=self.document_type,
            status=StandardWorkStatus.DRAFT,
            product_id=self.product_id,
            station_id=self.station_id,
            content_json=self.content_json.copy() if self.content_json else None,
            requires_training=self.requires_training,
            training_duration_minutes=self.training_duration_minutes,
            previous_version_id=self.id,
        )


class StandardWorkVersion(Base, TimestampMixin):
    """
    Immutable version history for standard work documents.

    Captures the state of a document at each version.
    """

    __tablename__ = "standard_work_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Reference to standard work
    standard_work_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("standard_works.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # Snapshot of content
    content_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Authorship
    created_by_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    standard_work: Mapped["StandardWork"] = relationship(
        "StandardWork", back_populates="versions"
    )
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint(
            "standard_work_id", "version", name="uq_sw_version_doc_version"
        ),
        CheckConstraint("version > 0", name="ck_sw_version_positive"),
    )

    def __repr__(self) -> str:
        return f"<StandardWorkVersion(sw_id={self.standard_work_id}, v{self.version})>"

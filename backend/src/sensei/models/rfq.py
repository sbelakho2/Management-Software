"""
RFQ (Request for Quotation) models.

Implements:
- RFQ: Customer request for quotation
- RFQQuestion: Clarification questions during RFQ processing
- RFQAttachment: Files attached to an RFQ
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.account import Account, Contact
    from sensei.models.opportunity import Opportunity
    from sensei.models.qualification import Qualification
    from sensei.models.quote import Quote
    from sensei.models.user import User


class RFQStatus(str, Enum):
    """RFQ workflow states."""
    
    DRAFT = "draft"
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    QUESTIONS_PENDING = "questions_pending"
    QUALIFYING = "qualifying"
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"
    QUOTING = "quoting"
    QUOTED = "quoted"
    WON = "won"
    LOST = "lost"
    NO_BID = "no_bid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RFQPriority(str, Enum):
    """RFQ priority levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RFQSource(str, Enum):
    """How the RFQ was received."""
    
    EMAIL = "email"
    PORTAL = "portal"
    PHONE = "phone"
    IN_PERSON = "in_person"
    TRADE_SHOW = "trade_show"
    WEBSITE = "website"
    REFERRAL = "referral"


class RFQ(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Request for Quotation record.
    
    Captures customer requests and tracks them through the qualification
    and quotation process.
    """
    
    __tablename__ = "rfqs"
    
    # Identification
    rfq_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    customer_rfq_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Basic Information
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Related Entities
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Status and Workflow
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RFQStatus.RECEIVED.value,
        index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Priority and Source
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RFQPriority.MEDIUM.value,
        index=True,
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Dates
    received_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    customer_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    quoted_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decision_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Part/Product Information
    part_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    part_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    part_revision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    drawing_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Quantity and Pricing
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    
    # Quantity breaks for volume pricing
    quantity_breaks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Technical Specifications
    material_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_grade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    finish_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    tolerance_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Processes
    primary_process: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_processes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Quality Requirements
    quality_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    certifications_required: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    inspection_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Delivery
    delivery_terms: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_time_required: Mapped[int | None] = mapped_column(Integer, nullable=True)  # days
    
    # Packaging
    packaging_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Qualification Results
    is_qualified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qualification_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    qualification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    no_bid_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Win/Loss
    is_won: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    win_loss_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    competitor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Assignment
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Notes
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="rfqs",
        foreign_keys=[account_id],
    )
    contact: Mapped["Contact | None"] = relationship("Contact")
    opportunity: Mapped["Opportunity | None"] = relationship(
        "Opportunity",
        back_populates="rfqs",
    )
    assigned_to: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
    )
    competitor: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[competitor_id],
    )
    
    questions: Mapped[list["RFQQuestion"]] = relationship(
        "RFQQuestion",
        back_populates="rfq",
        cascade="all, delete-orphan",
        order_by="RFQQuestion.created_at",
        lazy="dynamic",
    )
    
    attachments: Mapped[list["RFQAttachment"]] = relationship(
        "RFQAttachment",
        back_populates="rfq",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    qualifications: Mapped[list["Qualification"]] = relationship(
        "Qualification",
        back_populates="rfq",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    quotes: Mapped[list["Quote"]] = relationship(
        "Quote",
        back_populates="rfq",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_rfqs_account_status", account_id, status),
        Index("ix_rfqs_status_due", status, due_date),
        Index("ix_rfqs_assigned_status", assigned_to_id, status),
        Index(
            "ix_rfqs_open",
            status,
            postgresql_where=(status.notin_(["won", "lost", "no_bid", "cancelled", "expired"])),
        ),
    )
    
    @property
    def is_open(self) -> bool:
        """Check if RFQ is still open."""
        closed_statuses = [
            RFQStatus.WON.value,
            RFQStatus.LOST.value,
            RFQStatus.NO_BID.value,
            RFQStatus.CANCELLED.value,
            RFQStatus.EXPIRED.value,
        ]
        return self.status not in closed_statuses
    
    @property
    def has_unanswered_questions(self) -> bool:
        """Check if there are unanswered clarification questions."""
        # This requires loading questions, use with caution
        return any(not q.is_answered for q in self.questions)
    
    @property
    def days_until_due(self) -> int | None:
        """Calculate days until due date."""
        if self.due_date is None:
            return None
        from datetime import timezone as tz
        delta = self.due_date - datetime.now(tz.utc)
        return delta.days


class QuestionStatus(str, Enum):
    """Status of a clarification question."""
    
    DRAFT = "draft"
    SENT = "sent"
    ANSWERED = "answered"
    CLOSED = "closed"


class RFQQuestion(Base, TimestampMixin):
    """
    Clarification question for an RFQ.
    
    Tracks questions sent to customers and their responses.
    """
    
    __tablename__ = "rfq_questions"
    
    rfq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Question Details
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=QuestionStatus.DRAFT.value,
    )
    
    # Response
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    answered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Tracking
    asked_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Is this question critical (blocks quoting)?
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Notes
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="questions")
    asked_by: Mapped["User | None"] = relationship("User")
    
    __table_args__ = (
        Index("ix_rfq_questions_rfq_status", rfq_id, status),
    )
    
    @property
    def is_answered(self) -> bool:
        """Check if question has been answered."""
        return self.status in [QuestionStatus.ANSWERED.value, QuestionStatus.CLOSED.value]


class RFQAttachmentType(str, Enum):
    """Type of RFQ attachment."""
    
    DRAWING = "drawing"
    SPECIFICATION = "specification"
    MODEL_3D = "model_3d"
    DATASHEET = "datasheet"
    QUALITY_DOC = "quality_doc"
    EMAIL = "email"
    OTHER = "other"


class RFQAttachment(Base, TimestampMixin):
    """
    File attachment for an RFQ.
    
    Stores metadata about files stored in object storage.
    """
    
    __tablename__ = "rfq_attachments"
    
    rfq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # File Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Storage
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Classification
    attachment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RFQAttachmentType.OTHER.value,
    )
    
    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Uploaded by
    uploaded_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Customer provided?
    is_customer_provided: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Virus scan status
    scan_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="attachments")
    uploaded_by: Mapped["User | None"] = relationship("User")
    
    __table_args__ = (
        Index("ix_rfq_attachments_rfq_type", rfq_id, attachment_type),
    )
    
    @property
    def file_size_human(self) -> str:
        """Get human-readable file size."""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

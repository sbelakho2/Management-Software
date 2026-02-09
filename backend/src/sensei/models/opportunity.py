"""
Opportunity model for sales pipeline management.

Implements:
- Opportunity: Sales deal tracking with stages and probability
- OpportunityNote: Activity and communication log
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
    from sensei.models.quote import Quote
    from sensei.models.rfq import RFQ
    from sensei.models.user import User


class OpportunityStage(str, Enum):
    """Sales pipeline stages."""
    
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    VALUE_PROPOSITION = "value_proposition"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OpportunityType(str, Enum):
    """Type of opportunity."""
    
    NEW_BUSINESS = "new_business"
    EXISTING_BUSINESS = "existing_business"
    RENEWAL = "renewal"
    UPSELL = "upsell"
    CROSS_SELL = "cross_sell"


class OpportunitySource(str, Enum):
    """Lead source for the opportunity."""
    
    WEBSITE = "website"
    REFERRAL = "referral"
    TRADE_SHOW = "trade_show"
    COLD_CALL = "cold_call"
    INBOUND = "inbound"
    PARTNER = "partner"
    EXISTING_CUSTOMER = "existing_customer"
    RFQ = "rfq"
    OTHER = "other"


class Opportunity(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Sales opportunity/deal record.
    
    Tracks the full sales cycle from lead to closed deal.
    Integrates with RFQ workflow for manufacturing opportunities.
    """
    
    __tablename__ = "opportunities"
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Related Account and Contact
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    primary_contact_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Pipeline Stage
    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OpportunityStage.PROSPECTING.value,
        index=True,
    )
    previous_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stage_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Classification
    opportunity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OpportunityType.NEW_BUSINESS.value,
    )
    lead_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Financials
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    probability: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )  # 0-100%
    weighted_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    
    # Quantities
    expected_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_annual_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Dates
    close_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    expected_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_close_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Win/Loss Information
    is_won: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    competitor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Forecasting
    forecast_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_in_forecast: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Product/Service Information
    product_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Manufacturing Specifics
    part_numbers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    processes_required: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    materials: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Campaign/Partner tracking
    campaign_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    partner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Priority and Score
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
    )
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Next Steps
    next_step: Mapped[str | None] = mapped_column(String(500), nullable=True)
    next_step_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="opportunities",
        foreign_keys=[account_id],
    )
    primary_contact: Mapped["Contact | None"] = relationship(
        "Contact",
        foreign_keys=[primary_contact_id],
    )
    competitor: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[competitor_id],
    )
    partner: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[partner_id],
    )
    
    rfqs: Mapped[list["RFQ"]] = relationship(
        "RFQ",
        back_populates="opportunity",
        lazy="select",
    )
    
    quotes: Mapped[list["Quote"]] = relationship(
        "Quote",
        back_populates="opportunity",
        lazy="select",
    )
    
    notes: Mapped[list["OpportunityNote"]] = relationship(
        "OpportunityNote",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        order_by="desc(OpportunityNote.created_at)",
        lazy="select",
    )
    
    __table_args__ = (
        Index("ix_opportunities_account_stage", account_id, stage),
        Index("ix_opportunities_stage_close_date", stage, close_date),
        Index("ix_opportunities_owner_stage", "owner_id", stage),
        Index(
            "ix_opportunities_open",
            stage,
            postgresql_where=(stage.notin_(["closed_won", "closed_lost"])),
        ),
    )
    
    def calculate_weighted_amount(self) -> Decimal | None:
        """Calculate weighted amount based on probability."""
        if self.amount is None:
            return None
        return Decimal(str(self.amount)) * Decimal(str(self.probability)) / 100
    
    @property
    def is_open(self) -> bool:
        """Check if opportunity is still open."""
        return self.stage not in [
            OpportunityStage.CLOSED_WON.value,
            OpportunityStage.CLOSED_LOST.value,
        ]
    
    @property
    def is_closed(self) -> bool:
        """Check if opportunity is closed."""
        return not self.is_open
    
    @property
    def days_in_stage(self) -> int | None:
        """Calculate days in current stage."""
        if self.stage_changed_at is None:
            return None
        from datetime import timezone as tz
        delta = datetime.now(tz.utc) - self.stage_changed_at
        return delta.days


class NoteType(str, Enum):
    """Type of opportunity note."""
    
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"
    STATUS_CHANGE = "status_change"
    SYSTEM = "system"


class OpportunityNote(Base, TimestampMixin):
    """
    Activity log entry for an opportunity.
    
    Records all interactions, status changes, and notes.
    """
    
    __tablename__ = "opportunity_notes"
    
    opportunity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Note Content
    note_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=NoteType.NOTE.value,
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Author
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Related Contact (if this was an interaction with a contact)
    contact_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Activity Details
    activity_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # For status change notes
    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Is this an internal note (not visible to customers)?
    is_internal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Is this note pinned to the top?
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Attachments metadata
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="notes",
    )
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    contact: Mapped["Contact | None"] = relationship("Contact")
    
    __table_args__ = (
        Index("ix_opportunity_notes_opp_type", "opportunity_id", "note_type"),
        Index("ix_opportunity_notes_created", "opportunity_id", "created_at"),
    )

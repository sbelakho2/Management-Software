"""
Quote models for pricing and quotation management.

Implements:
- Quote: Customer-facing quotation
- QuoteVersion: Version control for quotes
- QuoteLineItem: Individual priced items
- SupplierQuote: Quotes received from suppliers
- SupplierQuoteItem: Individual items from supplier quotes
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.account import Account
    from sensei.models.opportunity import Opportunity
    from sensei.models.rfq import RFQ
    from sensei.models.user import User
    from sensei.models.quoting_helper import QuoteActual


class QuoteStatus(str, Enum):
    """Quote workflow states."""
    
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REVISED = "revised"


class ApprovalStatus(str, Enum):
    """Approval workflow states."""
    
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LineItemType(str, Enum):
    """Type of quote line item."""
    
    PRODUCT = "product"
    SERVICE = "service"
    TOOLING = "tooling"
    NRE = "nre"
    FREIGHT = "freight"
    OTHER = "other"


class VersionStatus(str, Enum):
    """Status of quote version."""
    
    DRAFT = "draft"
    FINAL = "final"
    SUBMITTED = "submitted"
    SUPERSEDED = "superseded"


class SupplierQuoteStatus(str, Enum):
    """Status of supplier quote."""
    
    PENDING = "pending"
    REQUESTED = "requested"
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    SELECTED = "selected"
    NOT_SELECTED = "not_selected"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quote(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Customer quotation.
    
    The main quote entity that tracks the full quotation lifecycle.
    Supports versioning, approval workflows, and margin tracking.
    """
    
    __tablename__ = "quotes"
    
    # Identification
    quote_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Related Entities
    rfq_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic Information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=QuoteStatus.DRAFT.value,
        index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Current Version
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        default=Decimal("1.0"),
        nullable=False,
    )
    
    # Totals (denormalized for performance)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0"),
        nullable=False,
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0"),
        nullable=False,
    )
    discount_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0"),
        nullable=False,
    )
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0"),
        nullable=False,
    )
    
    # Cost and Margin (internal, not shown to customer)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    target_margin: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    actual_margin: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Dates
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Approval
    approval_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ApprovalStatus.NOT_REQUIRED.value,
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )
    approved_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Terms
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warranty_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Terms and Conditions
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Notes
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Rejection
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # PDF Generation
    pdf_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # AI/Semantic Search
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    
    # Relationships
    rfq: Mapped["RFQ | None"] = relationship("RFQ", back_populates="quotes")
    opportunity: Mapped["Opportunity | None"] = relationship(
        "Opportunity",
        back_populates="quotes",
    )
    account: Mapped["Account"] = relationship("Account")
    approved_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by_id],
    )
    
    versions: Mapped[list["QuoteVersion"]] = relationship(
        "QuoteVersion",
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="desc(QuoteVersion.version_number)",
        lazy="dynamic",
    )
    
    line_items: Mapped[list["QuoteLineItem"]] = relationship(
        "QuoteLineItem",
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteLineItem.line_number",
        lazy="selectin",
    )
    
    actuals: Mapped["QuoteActual | None"] = relationship(
        "QuoteActual",
        back_populates="quote",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_quotes_account_status", account_id, status),
        Index("ix_quotes_status_valid", status, valid_until),
        Index(
            "ix_quotes_open",
            status,
            postgresql_where=(status.notin_(["accepted", "rejected", "expired", "cancelled"])),
        ),
        Index("ix_quotes_embedding", "embedding", postgresql_using="ivfflat"),
    )
    
    def calculate_totals(self) -> None:
        """Calculate quote totals from line items."""
        subtotal = Decimal("0")
        total_cost = Decimal("0")
        
        for item in self.line_items:
            if item.line_total:
                subtotal += item.line_total
            if item.cost_total:
                total_cost += item.cost_total
        
        self.subtotal = subtotal
        self.total_cost = total_cost
        
        # Apply discount
        if self.discount_percentage:
            self.discount_amount = subtotal * self.discount_percentage / 100
        
        after_discount = subtotal - self.discount_amount
        
        # Apply tax
        if self.tax_rate:
            self.tax_amount = after_discount * self.tax_rate / 100
        
        self.total = after_discount + self.tax_amount
        
        # Calculate margin
        if total_cost > 0:
            self.actual_margin = ((self.total - total_cost) / self.total) * 100
    
    @property
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        if self.valid_until is None:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.valid_until

    @property
    def is_valid(self) -> bool:
        """Check if quote is currently valid (not past valid_until)."""
        override = getattr(self, "_is_valid_override", None)
        if override is not None:
            return bool(override)
        if self.valid_until is None:
            return True
        from datetime import timezone as tz
        return datetime.now(tz.utc) <= self.valid_until

    @is_valid.setter
    def is_valid(self, value: bool) -> None:
        self._is_valid_override = bool(value)
    
    @property
    def is_open(self) -> bool:
        """Check if quote is still open."""
        closed_statuses = [
            QuoteStatus.ACCEPTED.value,
            QuoteStatus.REJECTED.value,
            QuoteStatus.EXPIRED.value,
            QuoteStatus.CANCELLED.value,
        ]
        return self.status not in closed_statuses


class QuoteVersion(Base, TimestampMixin):
    """
    Version snapshot of a quote.
    
    Preserves the state of a quote at a point in time for audit and comparison.
    """
    
    __tablename__ = "quote_versions"
    
    quote_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Version status
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Version status
    
    # Snapshot of quote data
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Change tracking
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Brief summary of changes
    change_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Who created this version?
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # PDF for this version
    pdf_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships
    quote: Mapped["Quote"] = relationship("Quote", back_populates="versions")
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    
    __table_args__ = (
        UniqueConstraint("quote_id", "version_number", name="uq_quote_version"),
        Index("ix_quote_versions_quote_version", quote_id, version_number.desc()),
    )


class QuoteLineItem(Base, TimestampMixin):
    """
    Individual line item in a quote.
    
    Represents a priced item with quantity, unit price, and totals.
    """
    
    __tablename__ = "quote_line_items"
    
    quote_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Line number for ordering
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Item Details
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)  # SKU identifier
    part_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Product name
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Quantity
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="EA", nullable=False)
    
    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Discount at line level
    discount_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0"),
        nullable=False,
    )
    
    # Cost (internal)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    cost_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # NRE (Non-Recurring Engineering) costs
    nre_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    tooling_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Quantity Breaks
    quantity_breaks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Example: [{"qty": 100, "price": 10.50}, {"qty": 500, "price": 9.00}]
    
    # Lead Time
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Is this line included in the quote?
    is_included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Is this an optional item?
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    quote: Mapped["Quote"] = relationship("Quote", back_populates="line_items")
    
    __table_args__ = (
        UniqueConstraint("quote_id", "line_number", name="uq_quote_line_number"),
        Index("ix_quote_line_items_quote_line", quote_id, line_number),
    )
    
    def calculate_totals(self) -> None:
        """Calculate line totals."""
        gross_total = self.quantity * self.unit_price
        
        if self.discount_percentage:
            self.discount_amount = gross_total * self.discount_percentage / 100
        
        self.line_total = gross_total - self.discount_amount
        
        if self.unit_cost:
            self.cost_total = self.quantity * self.unit_cost
            if self.line_total > 0:
                self.margin_percentage = (
                    (self.line_total - self.cost_total) / self.line_total
                ) * 100


class SupplierQuote(Base, TimestampMixin, AuditMixin):
    """
    Quote received from a supplier.
    
    Tracks supplier pricing for cost estimation.
    """
    
    __tablename__ = "supplier_quotes"
    
    # Identification
    supplier_quote_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    internal_reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Supplier
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Related RFQ (if applicable)
    rfq_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SupplierQuoteStatus.REQUESTED.value,
        index=True,
    )
    
    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    
    # Totals
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Dates
    requested_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    received_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Terms
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_order_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Evaluation
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 stars
    evaluation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # PDF storage
    pdf_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships
    supplier: Mapped["Account"] = relationship(
        "Account",
        back_populates="supplier_quotes",
    )
    rfq: Mapped["RFQ | None"] = relationship("RFQ")
    
    items: Mapped[list["SupplierQuoteItem"]] = relationship(
        "SupplierQuoteItem",
        back_populates="supplier_quote",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    __table_args__ = (
        Index("ix_supplier_quotes_supplier_status", supplier_id, status),
        Index("ix_supplier_quotes_rfq", rfq_id),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if supplier quote has expired."""
        if self.valid_until is None:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.valid_until


class SupplierQuoteItem(Base, TimestampMixin):
    """
    Individual item in a supplier quote.
    """
    
    __tablename__ = "supplier_quote_items"
    
    supplier_quote_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("supplier_quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Line number
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Item Details
    part_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_part_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Quantity and Pricing
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="EA", nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Additional costs
    tooling_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    setup_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Quantity breaks
    quantity_breaks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Lead time for this item
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    supplier_quote: Mapped["SupplierQuote"] = relationship(
        "SupplierQuote",
        back_populates="items",
    )
    
    __table_args__ = (
        UniqueConstraint(
            "supplier_quote_id",
            "line_number",
            name="uq_supplier_quote_line",
        ),
    )

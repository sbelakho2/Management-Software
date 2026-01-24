from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional
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
    from sensei.models.rfq import RFQ
    from sensei.models.user import User
    from sensei.models.quote import Quote
    from sensei.models.account import Account


class DisciplineType(str, Enum):
    """Engineering disciplines for work packets."""
    
    EE = "ee"
    EMBEDDED = "embedded"
    ME = "me"
    MFGE = "mfge"
    QE = "qe"
    PURCHASING = "purchasing"


class WorkPacketStatus(str, Enum):
    """Status of a work packet."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    DONE_WITH_RISKS = "done_with_risks"
    BLOCKED = "blocked"
    WAIVED = "waived"


class WorkPacket(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Work packet for a specific discipline to contribute to an RFQ/Quote.
    """
    
    __tablename__ = "work_packets"
    
    rfq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    discipline: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=WorkPacketStatus.PENDING.value,
    )
    
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Structured Outputs (Discipline specific)
    # Examples:
    # EE: needs_xray, fine_pitch_min_mm, dfm_findings[], test_recommendation
    # Embedded: programming_minutes_per_unit, fixture_needed, customer_provides_fw
    outputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Attachments specifically for this packet
    attachments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Notes and logs
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocker_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    rfq: Mapped["RFQ"] = relationship("RFQ")
    owner: Mapped["User | None"] = relationship("User", foreign_keys="[WorkPacket.owner_id]")
    
    __table_args__ = (
        Index("ix_work_packets_rfq_discipline", rfq_id, discipline, unique=True),
    )


class PCBSpec(Base, TimestampMixin, AuditMixin):
    """
    Technical specifications for PCB fabrication.
    """
    
    __tablename__ = "pcb_specs"
    
    rfq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    layers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish: Mapped[str | None] = mapped_column(String(100), nullable=True)
    thickness_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    size_x_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    size_y_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    impedance_req: Mapped[bool] = mapped_column(Boolean, default=False)
    copper_weight_oz: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_trace_width_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    min_hole_size_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    
    rfq: Mapped["RFQ"] = relationship("RFQ")


class RFQPackageVersion(Base, TimestampMixin, AuditMixin):
    """
    Immutable version of an RFQ file package.
    """
    
    __tablename__ = "rfq_package_versions"
    
    rfq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Files metadata
    # List of {filename, checksum, storage_key, type}
    files: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Extracted metadata at this version
    extracted_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    
    rfq: Mapped["RFQ"] = relationship("RFQ")
    
    __table_args__ = (
        Index("ix_rfq_pkg_rfq_ver", rfq_id, version_number, unique=True),
    )


class RateCard(Base, TimestampMixin, AuditMixin):
    """
    Standard rates for labor, overhead, and NRE.
    """
    
    __tablename__ = "rate_cards"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Rates (USD or MAD)
    labor_rate_hourly: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    smt_placement_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)  # price per placement
    setup_charge: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    
    # Default multipliers
    default_yield_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("1.02")
    )
    scrap_rate_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("1.01")
    )
    
    # Specific rules / formulas
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class QuoteActual(Base, TimestampMixin):
    """
    Comparison of quoted vs actual costs after production.
    """
    
    __tablename__ = "quote_actuals"
    
    quote_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Material
    quoted_material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    actual_material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    
    # Labor
    quoted_labor_minutes: Mapped[int] = mapped_column(Integer)
    actual_labor_minutes: Mapped[int] = mapped_column(Integer)
    
    # Yield
    quoted_yield: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    actual_yield: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    
    # Variance Analysis
    variance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_categories: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    quote: Mapped["Quote"] = relationship("Quote")

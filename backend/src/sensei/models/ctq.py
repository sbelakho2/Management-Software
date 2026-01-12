"""
CTQ (Critical to Quality) models for quality management.

Implements:
- CTQ: Critical quality characteristic definition
- CTQMeasurement: Actual measurements against CTQ specifications
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.rfq import RFQ
    from sensei.models.user import User


class CTQCategory(str, Enum):
    """Category of CTQ characteristic."""
    
    DIMENSIONAL = "dimensional"
    SURFACE = "surface"
    MATERIAL = "material"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    VISUAL = "visual"
    FUNCTIONAL = "functional"
    ENVIRONMENTAL = "environmental"
    OTHER = "other"


class CTQPriority(str, Enum):
    """Priority/criticality of CTQ."""
    
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class CTQStatus(str, Enum):
    """Status of CTQ definition."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    OBSOLETE = "obsolete"


class MeasurementResult(str, Enum):
    """Result of a CTQ measurement."""
    
    PASS = "pass"
    FAIL = "fail"
    MARGINAL = "marginal"
    NOT_MEASURED = "not_measured"


class CTQ(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Critical to Quality characteristic.
    
    Defines quality requirements that must be met for a part/product.
    Captures specifications, tolerances, and measurement methods.
    """
    
    __tablename__ = "ctqs"
    
    # Related RFQ/Part
    rfq_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Identification
    ctq_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Part Information
    part_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    drawing_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operation_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CTQCategory.DIMENSIONAL.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CTQPriority.MAJOR.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CTQStatus.DRAFT.value,
        index=True,
    )
    
    # Specification
    nominal_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(50), default="mm", nullable=False)
    
    # Tolerances
    upper_spec_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    lower_spec_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    tolerance_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g., "bilateral", "unilateral_plus", "unilateral_minus"
    
    # GD&T (Geometric Dimensioning and Tolerancing)
    gdt_symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gdt_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    datum_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Statistical Process Control
    target_cpk: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_ppk: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Measurement Method
    measurement_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurement_equipment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gauge_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gauge_r_and_r: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Control Method
    control_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    reaction_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Customer Requirements
    customer_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_specification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_customer_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Approval
    approved_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    rfq: Mapped["RFQ | None"] = relationship("RFQ")
    approved_by: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by_id])
    
    measurements: Mapped[list["CTQMeasurement"]] = relationship(
        "CTQMeasurement",
        back_populates="ctq",
        cascade="all, delete-orphan",
        order_by="desc(CTQMeasurement.measured_at)",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_ctqs_part_category", part_number, category),
        Index("ix_ctqs_rfq_priority", rfq_id, priority),
    )
    
    @property
    def tolerance_range(self) -> Decimal | None:
        """Calculate total tolerance range."""
        if self.upper_spec_limit is not None and self.lower_spec_limit is not None:
            return self.upper_spec_limit - self.lower_spec_limit
        return None
    
    def is_value_in_spec(self, value: Decimal) -> bool:
        """Check if a value is within specification limits."""
        if self.upper_spec_limit is not None and value > self.upper_spec_limit:
            return False
        if self.lower_spec_limit is not None and value < self.lower_spec_limit:
            return False
        return True


class CTQMeasurement(Base, TimestampMixin):
    """
    Measurement record for a CTQ characteristic.
    
    Captures actual measurement data against CTQ specifications.
    """
    
    __tablename__ = "ctq_measurements"
    
    ctq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ctqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Measurement Identification
    measurement_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sample_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Measured Value
    measured_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    
    # Deviation from nominal
    deviation: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    
    # Result
    result: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MeasurementResult.NOT_MEASURED.value,
        index=True,
    )
    
    # When and Who
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    measured_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Equipment Used
    equipment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    calibration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Environmental Conditions
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    humidity: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # If failed, what action was taken?
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g., "accept", "reject", "rework", "scrap", "use_as_is"
    
    # Attachments (photos, reports)
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    ctq: Mapped["CTQ"] = relationship("CTQ", back_populates="measurements")
    measured_by: Mapped["User | None"] = relationship("User", foreign_keys=[measured_by_id])
    
    __table_args__ = (
        Index("ix_ctq_measurements_ctq_date", ctq_id, measured_at.desc()),
        Index("ix_ctq_measurements_ctq_result", ctq_id, result),
        Index("ix_ctq_measurements_batch", batch_number),
    )
    
    def calculate_deviation(self, nominal: Decimal) -> None:
        """Calculate deviation from nominal value."""
        self.deviation = self.measured_value - nominal
    
    def determine_result(self, ctq: "CTQ") -> None:
        """Determine pass/fail result based on CTQ limits."""
        if ctq.upper_spec_limit is not None and self.measured_value > ctq.upper_spec_limit:
            self.result = MeasurementResult.FAIL.value
        elif ctq.lower_spec_limit is not None and self.measured_value < ctq.lower_spec_limit:
            self.result = MeasurementResult.FAIL.value
        else:
            self.result = MeasurementResult.PASS.value
            
            # Check for marginal (within 10% of limits)
            if ctq.tolerance_range:
                margin = ctq.tolerance_range * Decimal("0.1")
                if ctq.upper_spec_limit and (
                    ctq.upper_spec_limit - self.measured_value
                ) < margin:
                    self.result = MeasurementResult.MARGINAL.value
                elif ctq.lower_spec_limit and (
                    self.measured_value - ctq.lower_spec_limit
                ) < margin:
                    self.result = MeasurementResult.MARGINAL.value

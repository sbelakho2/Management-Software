"""
Quality Management models for NC/CAPA tracking.

Non-Conformance (NC) and Corrective/Preventive Action (CAPA)
management with 8D reporting integration.
"""

import enum
from datetime import datetime, date, timezone
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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin
from sensei.core.time import utcnow_naive

if TYPE_CHECKING:
    from sensei.models.work_center import Station
    from sensei.models.product import Product
    from sensei.models.work_order import WorkOrder
    from sensei.models.user import User
    from sensei.models.a3 import A3
    from sensei.models.standard_work import StandardWork
    from sensei.models.attachment import Attachment


class NCType(enum.Enum):
    """Type of non-conformance."""

    MATERIAL = "material"
    PROCESS = "process"
    PRODUCT = "product"
    DOCUMENTATION = "documentation"
    SUPPLIER = "supplier"
    CUSTOMER_RETURN = "customer_return"
    PACKAGING = "packaging"
    HANDLING = "handling"


class NCSource(enum.Enum):
    """Source/detection point of non-conformance."""

    INCOMING_INSPECTION = "incoming_inspection"
    IN_PROCESS = "in_process"
    FINAL_INSPECTION = "final_inspection"
    CUSTOMER_COMPLAINT = "customer_complaint"
    AUDIT = "audit"
    SUPPLIER_NOTIFICATION = "supplier_notification"
    INTERNAL_AUDIT = "internal_audit"
    OPERATOR_DETECTION = "operator_detection"


class NCSeverity(enum.Enum):
    """Severity of non-conformance."""

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class NCStatus(enum.Enum):
    """Status of non-conformance."""

    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    PENDING_DISPOSITION = "pending_disposition"
    DISPOSITIONED = "dispositioned"
    CLOSED = "closed"
    ESCALATED_TO_CAPA = "escalated_to_capa"


class NCDisposition(enum.Enum):
    """Disposition decision for non-conformance."""

    USE_AS_IS = "use_as_is"
    REWORK = "rework"
    REPAIR = "repair"
    SCRAP = "scrap"
    RETURN_TO_SUPPLIER = "return_to_supplier"
    CONCESSION = "concession"
    SORT = "sort"
    DOWNGRADE = "downgrade"


class RootCauseCategory(enum.Enum):
    """Root cause categories (5M+E)."""

    HUMAN_ERROR = "human_error"  # Man
    EQUIPMENT = "equipment"  # Machine
    MATERIAL = "material"  # Material
    METHOD = "method"  # Method
    MEASUREMENT = "measurement"  # Measurement
    ENVIRONMENT = "environment"  # Environment


class CAPAType(enum.Enum):
    """Type of CAPA."""

    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    BOTH = "both"


class CAPASourceType(enum.Enum):
    """Source/trigger for CAPA."""

    NON_CONFORMANCE = "non_conformance"
    CUSTOMER_COMPLAINT = "customer_complaint"
    AUDIT_FINDING = "audit_finding"
    ANDON_RECURRENCE = "andon_recurrence"
    MANAGEMENT_REVIEW = "management_review"
    TREND_ANALYSIS = "trend_analysis"
    RISK_ASSESSMENT = "risk_assessment"


class CAPAStatus(enum.Enum):
    """Status of CAPA."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"  # Alias for active states
    INVESTIGATING = "investigating"
    IMPLEMENTING = "implementing"
    VERIFICATION = "verification"  # Alias for verifying
    VERIFYING = "verifying"
    EFFECTIVENESS_CHECK = "effectiveness_check"  # Effectiveness review stage
    EFFECTIVE = "effective"
    CLOSED = "closed"
    INEFFECTIVE = "ineffective"
    ON_HOLD = "on_hold"


class CAPAPriority(enum.Enum):
    """Priority level for CAPA."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationStatus(enum.Enum):
    """Status of verification check."""

    PENDING = "pending"
    VERIFIED = "verified"  # Alias for passed
    PASSED = "passed"
    REJECTED = "rejected"  # Alias for failed
    FAILED = "failed"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


class EffectivenessStatus(enum.Enum):
    """Status of effectiveness check."""

    PENDING = "pending"
    EFFECTIVE = "effective"
    PARTIALLY_EFFECTIVE = "partially_effective"
    INEFFECTIVE = "ineffective"


class CAPAActionType(enum.Enum):
    """Type of CAPA action."""

    CONTAINMENT = "containment"
    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    VERIFICATION = "verification"


class CAPAActionStatus(enum.Enum):
    """Status of CAPA action."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class InspectionType(enum.Enum):
    """Type of quality inspection."""

    INCOMING = "incoming"
    IN_PROCESS = "in_process"
    FINAL = "final"
    PATROL = "patrol"
    FIRST_ARTICLE = "first_article"
    AUDIT = "audit"


class InspectionResult(enum.Enum):
    """Overall inspection result."""

    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"
    PENDING = "pending"


class NonConformance(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Non-Conformance record for quality issues.

    Tracks defects, dispositions, and links to CAPA.
    """

    __tablename__ = "non_conformances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # NC identification
    nc_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Classification
    nc_type: Mapped[NCType] = mapped_column(
        Enum(NCType), nullable=False, index=True
    )
    source: Mapped[NCSource] = mapped_column(
        Enum(NCSource), nullable=False, index=True
    )
    severity: Mapped[NCSeverity] = mapped_column(
        Enum(NCSeverity), nullable=False, default=NCSeverity.MINOR, index=True
    )

    # Location and context
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )
    work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True, index=True
    )
    station_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=True, index=True
    )
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Quantity and impact
    quantity_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quantity_inspected: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Description
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    specification_requirement: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    actual_condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Root cause (quick capture)
    root_cause_category: Mapped[Optional[RootCauseCategory]] = mapped_column(
        Enum(RootCauseCategory), nullable=True
    )
    root_cause_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Detection
    detected_by_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive
    )

    # Status
    status: Mapped[NCStatus] = mapped_column(
        Enum(NCStatus),
        nullable=False,
        default=NCStatus.OPEN,
        index=True,
    )

    # Investigation assignment
    investigator_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    investigation_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    investigation_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    investigation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Disposition
    disposition: Mapped[Optional[NCDisposition]] = mapped_column(
        Enum(NCDisposition), nullable=True
    )
    disposition_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    disposition_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    disposition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disposition_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Containment actions
    containment_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    containment_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    containment_verified_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Cost impact
    cost_impact: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    scrap_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    rework_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    rework_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Customer notification
    customer_notified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    customer_notification_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    customer_notification_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Closure
    closed_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closure_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # CAPA linkage
    capa_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("capas.id", use_alter=True, name="fk_non_conformances_capa_id"), nullable=True
    )

    # Supplier info (for supplier NCs)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier_po_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    product: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="non_conformances"
    )
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="non_conformances"
    )
    station: Mapped[Optional["Station"]] = relationship(
        "Station", back_populates="non_conformances"
    )
    detected_by: Mapped["User"] = relationship(
        "User", foreign_keys=[detected_by_id]
    )
    investigator: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[investigator_id]
    )
    disposition_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[disposition_by_id]
    )
    containment_verified_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[containment_verified_by_id]
    )
    closed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[closed_by_id]
    )
    capa: Mapped[Optional["CAPA"]] = relationship(
        "CAPA", foreign_keys=[capa_id]
    )

    __table_args__ = (
        CheckConstraint(
            "quantity_affected > 0",
            name="ck_nc_quantity_affected_positive",
        ),
        CheckConstraint(
            "cost_impact IS NULL OR cost_impact >= 0",
            name="ck_nc_cost_impact_nonnegative",
        ),
    )

    def __repr__(self) -> str:
        return f"<NonConformance(id={self.id}, number='{self.nc_number}', severity={self.severity.value})>"

    @property
    def is_open(self) -> bool:
        """Check if NC is still open."""
        return self.status not in [NCStatus.CLOSED, NCStatus.ESCALATED_TO_CAPA]

    @property
    def requires_capa(self) -> bool:
        """Check if NC severity requires CAPA."""
        return self.severity == NCSeverity.CRITICAL

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost impact."""
        return (self.cost_impact or Decimal("0")) + (self.scrap_cost or Decimal("0")) + (self.rework_cost or Decimal("0"))

    @property
    def age_days(self) -> int:
        """Calculate age of NC in days."""
        end = self.closed_at or utcnow_naive()
        delta = end - self.detected_at
        return delta.days


class CAPAStateHistory(Base, TimestampMixin):
    """
    Audit trail for CAPA state transitions.
    
    Required for ISO/AS compliance.
    """

    __tablename__ = "capa_state_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    capa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("capas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[CAPAStatus] = mapped_column(Enum(CAPAStatus), nullable=False)
    to_status: Mapped[CAPAStatus] = mapped_column(Enum(CAPAStatus), nullable=False)
    changed_by_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    capa: Mapped["CAPA"] = relationship("CAPA", back_populates="state_history")
    changed_by: Mapped["User"] = relationship("User")


class CAPA(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Corrective and Preventive Action record.

    Links to A3 problem-solving and Standard Work updates.
    """

    __tablename__ = "capas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # CAPA identification
    capa_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Classification
    capa_type: Mapped[CAPAType] = mapped_column(
        Enum(CAPAType), nullable=False, default=CAPAType.CORRECTIVE
    )
    source_type: Mapped[CAPASourceType] = mapped_column(
        Enum(CAPASourceType), nullable=False, index=True
    )
    priority: Mapped[CAPAPriority] = mapped_column(
        Enum(CAPAPriority), nullable=False, default=CAPAPriority.MEDIUM, index=True
    )

    # Problem description
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    status: Mapped[CAPAStatus] = mapped_column(
        Enum(CAPAStatus),
        nullable=False,
        default=CAPAStatus.OPEN,
        index=True,
    )

    # Owner and dates
    owner_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    target_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Root cause analysis
    root_cause_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause_category: Mapped[Optional[RootCauseCategory]] = mapped_column(
        Enum(RootCauseCategory), nullable=True
    )
    five_why_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    """
    5-Why structure:
    {
        "problem": "...",
        "whys": [
            {"why": "...", "answer": "..."},
            {"why": "...", "answer": "..."},
            ...
        ],
        "root_cause": "..."
    }
    """

    # Action summaries
    containment_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrective_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preventive_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Verification
    verification_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus),
        nullable=False,
        default=VerificationStatus.PENDING,
    )
    verified_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Effectiveness
    effectiveness_check_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effectiveness_status: Mapped[EffectivenessStatus] = mapped_column(
        Enum(EffectivenessStatus),
        nullable=False,
        default=EffectivenessStatus.PENDING,
    )
    effectiveness_checked_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    effectiveness_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Closure
    closed_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closure_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Linked records
    source_nc_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("non_conformances.id", use_alter=True, name="fk_capas_source_nc_id"), nullable=True
    )
    linked_a3_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("a3s.id"), nullable=True
    )
    linked_standard_work_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("standard_works.id"), nullable=True
    )

    # Cost tracking
    estimated_cost_savings: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    actual_cost_savings: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    implementation_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    # Team
    team_members: Mapped[Optional[list[int]]] = mapped_column(
        JSONB, nullable=True
    )  # Array of user IDs

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    verified_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[verified_by_id]
    )
    effectiveness_checked_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[effectiveness_checked_by_id]
    )
    closed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[closed_by_id]
    )
    source_non_conformance: Mapped[Optional["NonConformance"]] = relationship(
        "NonConformance", foreign_keys=[source_nc_id]
    )
    linked_a3: Mapped[Optional["A3"]] = relationship(
        "A3", foreign_keys=[linked_a3_id]
    )
    linked_standard_work: Mapped[Optional["StandardWork"]] = relationship(
        "StandardWork", back_populates="linked_capas", foreign_keys=[linked_standard_work_id]
    )
    state_history: Mapped[list["CAPAStateHistory"]] = relationship(
        "CAPAStateHistory",
        back_populates="capa",
        cascade="all, delete-orphan",
        order_by="CAPAStateHistory.created_at.desc()",
    )
    actions: Mapped[list["CAPAAction"]] = relationship(
        "CAPAAction",
        back_populates="capa",
        cascade="all, delete-orphan",
        order_by="CAPAAction.due_date",
    )

    def __repr__(self) -> str:
        return f"<CAPA(id={self.id}, number='{self.capa_number}', status={self.status.value})>"

    @property
    def is_open(self) -> bool:
        """Check if CAPA is still open."""
        return self.status not in [CAPAStatus.CLOSED, CAPAStatus.EFFECTIVE]

    @property
    def age_days(self) -> int:
        """Calculate age of CAPA in days."""
        end = self.closed_at or utcnow_naive()
        delta = end - self.opened_at
        return delta.days

    @property
    def is_overdue(self) -> bool:
        """Check if CAPA is overdue."""
        if self.is_open and self.due_date:
            return date.today() > self.due_date
        return False

    @property
    def open_actions_count(self) -> int:
        """Count of open actions."""
        return sum(
            1 for a in self.actions
            if a.status in [CAPAActionStatus.OPEN, CAPAActionStatus.IN_PROGRESS]
        )

    @property
    def overdue_actions_count(self) -> int:
        """Count of overdue actions."""
        return sum(1 for a in self.actions if a.is_overdue)

    @property
    def can_verify(self) -> bool:
        """Check if CAPA can be verified."""
        # All corrective actions must be complete
        for action in self.actions:
            if action.action_type == CAPAActionType.CORRECTIVE:
                if action.status != CAPAActionStatus.COMPLETED:
                    return False
        return True

    @property
    def can_close(self) -> bool:
        """Check if CAPA can be closed."""
        if self.verification_status != VerificationStatus.PASSED:
            return False
        if self.effectiveness_status not in [
            EffectivenessStatus.EFFECTIVE,
            EffectivenessStatus.PARTIALLY_EFFECTIVE,
        ]:
            return False
        return True


class CAPAAction(Base, TimestampMixin, AuditMixin):
    """
    Individual action item within a CAPA.
    """

    __tablename__ = "capa_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # CAPA reference
    capa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("capas.id"), nullable=False, index=True
    )

    # Action details
    action_type: Mapped[CAPAActionType] = mapped_column(
        Enum(CAPAActionType), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Assignment
    owner_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Status
    status: Mapped[CAPAActionStatus] = mapped_column(
        Enum(CAPAActionStatus),
        nullable=False,
        default=CAPAActionStatus.OPEN,
        index=True,
    )

    # Completion
    completion_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Verification
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    capa: Mapped["CAPA"] = relationship("CAPA", back_populates="actions")
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    verified_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[verified_by_id]
    )

    def __repr__(self) -> str:
        return f"<CAPAAction(capa_id={self.capa_id}, type={self.action_type.value})>"

    @property
    def is_overdue(self) -> bool:
        """Check if action is overdue."""
        if self.status in [CAPAActionStatus.COMPLETED, CAPAActionStatus.CANCELLED]:
            return False
        return date.today() > self.due_date

    @property
    def days_until_due(self) -> int:
        """Days until due date (negative if overdue)."""
        delta = self.due_date - date.today()
        return delta.days


class InspectionPlan(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Quality inspection plan for products/stations.

    Defines inspection checkpoints and sampling rules.
    """

    __tablename__ = "inspection_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Plan identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scope
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )
    station_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=True, index=True
    )

    # Inspection type and frequency
    inspection_type: Mapped[InspectionType] = mapped_column(
        Enum(InspectionType), nullable=False
    )
    frequency: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "Every lot", "First article", "Daily"

    # Sampling plan (AQL-based)
    sampling_plan: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    """
    Sampling plan structure:
    {
        "type": "AQL",
        "aql": 1.0,
        "inspection_level": "II",
        "sample_sizes": {
            "2-8": 2,
            "9-15": 3,
            ...
        },
        "accept_reject": {
            "2": {"accept": 0, "reject": 1},
            ...
        }
    }
    """

    # Checkpoints (measurement requirements)
    checkpoints_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=[],
    )
    """
    Checkpoints structure:
    [
        {
            "sequence": 1,
            "characteristic": "Dimension A",
            "specification": "10.0 ± 0.1 mm",
            "nominal": 10.0,
            "tolerance_plus": 0.1,
            "tolerance_minus": 0.1,
            "measurement_method": "Caliper",
            "gauge_id": "CAL-001",
            "is_critical": true
        },
        ...
    ]
    """

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    product: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="inspection_plans"
    )
    station: Mapped[Optional["Station"]] = relationship(
        "Station", back_populates="inspection_plans"
    )
    records: Mapped[list["InspectionRecord"]] = relationship(
        "InspectionRecord", back_populates="inspection_plan"
    )

    def __repr__(self) -> str:
        return f"<InspectionPlan(id={self.id}, name='{self.name}')>"

    @property
    def checkpoint_count(self) -> int:
        """Number of checkpoints in plan."""
        return len(self.checkpoints_json)

    @property
    def critical_checkpoint_count(self) -> int:
        """Number of critical checkpoints."""
        return sum(
            1 for cp in self.checkpoints_json if cp.get("is_critical", False)
        )


class InspectionRecord(Base, TimestampMixin, AuditMixin):
    """
    Individual inspection result record.
    """

    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Plan reference
    inspection_plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inspection_plans.id"), nullable=False, index=True
    )

    # Work order / lot
    work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True, index=True
    )
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Sample info
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_ids: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)

    # Inspector
    inspected_by_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive
    )

    # Results
    overall_result: Mapped[InspectionResult] = mapped_column(
        Enum(InspectionResult), nullable=False, index=True
    )
    measurements_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=[],
    )
    """
    Measurements structure:
    [
        {
            "checkpoint_sequence": 1,
            "values": [10.05, 9.98, 10.02],  # Per sample
            "pass_count": 3,
            "fail_count": 0,
            "result": "pass"
        },
        ...
    ]
    """

    # Defects found
    defects_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defect_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # NC linkage
    nc_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("non_conformances.id"), nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    inspection_plan: Mapped["InspectionPlan"] = relationship(
        "InspectionPlan", back_populates="records"
    )
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="inspection_records"
    )
    inspected_by: Mapped["User"] = relationship("User", foreign_keys=[inspected_by_id])

    __table_args__ = (
        CheckConstraint(
            "sample_size > 0",
            name="ck_inspection_record_sample_size_positive",
        ),
        CheckConstraint(
            "defects_found >= 0",
            name="ck_inspection_record_defects_nonnegative",
        ),
    )

    def __repr__(self) -> str:
        return f"<InspectionRecord(id={self.id}, result={self.overall_result.value})>"

    @property
    def pass_rate(self) -> Decimal:
        """Calculate pass rate for measurements."""
        total = len(self.measurements_json)
        if total == 0:
            return Decimal("100")
        passed = sum(1 for m in self.measurements_json if m.get("result") == "pass")
        return Decimal(passed) / Decimal(total) * 100

    @property
    def is_pass(self) -> bool:
        """Check if overall result is pass."""
        return self.overall_result == InspectionResult.PASS

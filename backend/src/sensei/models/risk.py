"""
Risk management models.

Implements:
- Risk: Risk register entry
- RiskMitigation: Mitigation actions for risks
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.rfq import RFQ
    from sensei.models.user import User


class RiskCategory(str, Enum):
    """Category of risk."""
    
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    SUPPLY_CHAIN = "supply_chain"
    QUALITY = "quality"
    SCHEDULE = "schedule"
    RESOURCE = "resource"
    REGULATORY = "regulatory"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    OTHER = "other"


class RiskStatus(str, Enum):
    """Status of a risk."""
    
    IDENTIFIED = "identified"
    ANALYZING = "analyzing"
    MITIGATING = "mitigating"
    MONITORING = "monitoring"
    CLOSED = "closed"
    OCCURRED = "occurred"
    ACCEPTED = "accepted"


class RiskSeverity(str, Enum):
    """Severity/Impact level."""
    
    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class RiskLikelihood(str, Enum):
    """Probability of occurrence."""
    
    RARE = "rare"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    ALMOST_CERTAIN = "almost_certain"


class Risk(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Risk register entry.
    
    Tracks identified risks, their assessment, and mitigation status.
    Uses a standard risk matrix for scoring.
    """
    
    __tablename__ = "risks"
    
    # Identification
    risk_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Related Entity (polymorphic reference)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Direct RFQ relationship for common case
    rfq_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RiskCategory.TECHNICAL.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RiskStatus.IDENTIFIED.value,
        index=True,
    )
    
    # Risk Assessment - Inherent (before mitigation)
    inherent_likelihood: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RiskLikelihood.POSSIBLE.value,
    )
    inherent_severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RiskSeverity.MODERATE.value,
    )
    inherent_likelihood_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )  # 1-5
    inherent_severity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )  # 1-5
    inherent_risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=9,
    )  # likelihood * severity
    
    # Risk Assessment - Residual (after mitigation)
    residual_likelihood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    residual_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    residual_likelihood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_severity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Financial Impact
    potential_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    
    # Schedule Impact
    potential_delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Causes and Effects
    root_causes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    potential_effects: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Triggers
    risk_triggers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    early_warning_signs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Response Strategy
    response_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "avoid", "mitigate", "transfer", "accept"
    response_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    contingency_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Assignment
    risk_owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Dates
    identified_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    target_resolution_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_resolution_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    
    # If risk occurred
    occurred_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    rfq: Mapped["RFQ | None"] = relationship("RFQ")
    risk_owner: Mapped["User | None"] = relationship("User", foreign_keys=[risk_owner_id])
    
    mitigations: Mapped[list["RiskMitigation"]] = relationship(
        "RiskMitigation",
        back_populates="risk",
        cascade="all, delete-orphan",
        order_by="RiskMitigation.created_at",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_risks_category_status", category, status),
        Index("ix_risks_score", inherent_risk_score.desc()),
        Index("ix_risks_owner_status", risk_owner_id, status),
        Index(
            "ix_risks_open",
            status,
            postgresql_where=(status.notin_(["closed", "occurred", "accepted"])),
        ),
    )
    
    def calculate_risk_scores(self) -> None:
        """Calculate risk scores from likelihood and severity."""
        # Map text values to numeric scores
        likelihood_map = {
            RiskLikelihood.RARE.value: 1,
            RiskLikelihood.UNLIKELY.value: 2,
            RiskLikelihood.POSSIBLE.value: 3,
            RiskLikelihood.LIKELY.value: 4,
            RiskLikelihood.ALMOST_CERTAIN.value: 5,
        }
        severity_map = {
            RiskSeverity.NEGLIGIBLE.value: 1,
            RiskSeverity.MINOR.value: 2,
            RiskSeverity.MODERATE.value: 3,
            RiskSeverity.MAJOR.value: 4,
            RiskSeverity.CRITICAL.value: 5,
        }
        
        self.inherent_likelihood_score = likelihood_map.get(self.inherent_likelihood, 3)
        self.inherent_severity_score = severity_map.get(self.inherent_severity, 3)
        self.inherent_risk_score = (
            self.inherent_likelihood_score * self.inherent_severity_score
        )
        
        if self.residual_likelihood and self.residual_severity:
            self.residual_likelihood_score = likelihood_map.get(
                self.residual_likelihood, 3
            )
            self.residual_severity_score = severity_map.get(self.residual_severity, 3)
            self.residual_risk_score = (
                self.residual_likelihood_score * self.residual_severity_score
            )
    
    @property
    def risk_level(self) -> str:
        """Get risk level category based on score."""
        score = self.residual_risk_score or self.inherent_risk_score
        if score >= 20:
            return "critical"
        elif score >= 12:
            return "high"
        elif score >= 6:
            return "medium"
        else:
            return "low"
    
    @property
    def is_open(self) -> bool:
        """Check if risk is still open."""
        closed_statuses = [
            RiskStatus.CLOSED.value,
            RiskStatus.OCCURRED.value,
            RiskStatus.ACCEPTED.value,
        ]
        return self.status not in closed_statuses


class MitigationStatus(str, Enum):
    """Status of a mitigation action."""
    
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class RiskMitigation(Base, TimestampMixin, AuditMixin):
    """
    Mitigation action for a risk.
    
    Tracks actions taken to reduce risk likelihood or impact.
    """
    
    __tablename__ = "risk_mitigations"
    
    risk_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("risks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Action Details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Type of mitigation
    mitigation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "preventive", "detective", "corrective"
    
    # Target
    reduces_likelihood: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reduces_severity: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Expected reduction
    expected_likelihood_reduction: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # Points reduction
    expected_severity_reduction: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MitigationStatus.PLANNED.value,
        index=True,
    )
    
    # Priority
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    
    # Dates
    planned_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    planned_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Assignment
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Cost
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    
    # Effectiveness
    effectiveness_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # 1-5
    effectiveness_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Completion
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Evidence
    evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    risk: Mapped["Risk"] = relationship("Risk", back_populates="mitigations")
    assigned_to: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to_id])
    
    __table_args__ = (
        Index("ix_risk_mitigations_risk_status", risk_id, status),
        Index("ix_risk_mitigations_assigned", assigned_to_id, status),
    )
    
    @property
    def is_complete(self) -> bool:
        """Check if mitigation is complete."""
        return self.status == MitigationStatus.COMPLETED.value
    
    @property
    def is_overdue(self) -> bool:
        """Check if mitigation is overdue."""
        if self.planned_end_date is None:
            return False
        if self.status == MitigationStatus.COMPLETED.value:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.planned_end_date

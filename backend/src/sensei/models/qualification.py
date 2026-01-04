"""
Qualification models for RFQ evaluation.

Implements:
- Qualification: Overall qualification assessment for an RFQ
- QualificationCriterion: Configurable criteria for evaluation
- QualificationScore: Individual score for each criterion
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

from sensei.models.base import AuditMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.rfq import RFQ
    from sensei.models.user import User


class QualificationResult(str, Enum):
    """Overall qualification result."""
    
    PENDING = "pending"
    QUALIFIED = "qualified"
    CONDITIONALLY_QUALIFIED = "conditionally_qualified"
    NOT_QUALIFIED = "not_qualified"
    NEEDS_REVIEW = "needs_review"


class CriterionCategory(str, Enum):
    """Category of qualification criterion."""
    
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    CAPACITY = "capacity"
    QUALITY = "quality"
    STRATEGIC = "strategic"
    RISK = "risk"
    SUPPLY_CHAIN = "supply_chain"


class QualificationStatus(str, Enum):
    """Status of qualification process."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QualificationDecision(str, Enum):
    """Decision from qualification."""
    
    PENDING = "pending"
    GO = "go"
    NO_GO = "no_go"
    CONDITIONAL = "conditional"


class CriterionType(str, Enum):
    """Type of qualification criterion."""
    
    SCORED = "scored"
    PASS_FAIL = "pass_fail"
    INFORMATIONAL = "informational"


class ScoreValue(str, Enum):
    """Traffic light score value."""
    
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    NOT_ASSESSED = "not_assessed"


class Qualification(Base, TimestampMixin, AuditMixin):
    """
    Qualification assessment for an RFQ.
    
    Aggregates individual criterion scores to determine if
    an RFQ should be quoted.
    """
    
    __tablename__ = "qualifications"
    
    # Related RFQ
    rfq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Qualification Version
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Result
    result: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=QualificationResult.PENDING.value,
        index=True,
    )
    
    # Scores
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_possible_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    percentage_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Thresholds
    pass_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("70.00"),
        nullable=False,
    )
    conditional_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("50.00"),
        nullable=False,
    )
    
    # Category Scores (aggregated)
    category_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Flags
    has_blockers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocker_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Recommendations
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Review
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Approval
    is_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approved_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Completion
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="qualifications")
    reviewed_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[reviewed_by_id],
    )
    approved_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by_id],
    )
    
    scores: Mapped[list["QualificationScore"]] = relationship(
        "QualificationScore",
        back_populates="qualification",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    __table_args__ = (
        Index("ix_qualifications_rfq_version", rfq_id, version),
        UniqueConstraint("rfq_id", "version", name="uq_qualification_rfq_version"),
    )
    
    def calculate_scores(self) -> None:
        """Calculate total and percentage scores from individual scores."""
        if not self.scores:
            return
        
        total = Decimal("0")
        max_possible = Decimal("0")
        category_totals: dict[str, dict[str, Decimal]] = {}
        
        for score in self.scores:
            if score.score is not None and score.weight is not None:
                weighted_score = score.score * score.weight
                total += weighted_score
                max_possible += score.max_score * score.weight
                
                cat = score.criterion.category if score.criterion else "other"
                if cat not in category_totals:
                    category_totals[cat] = {"score": Decimal("0"), "max": Decimal("0")}
                category_totals[cat]["score"] += weighted_score
                category_totals[cat]["max"] += score.max_score * score.weight
        
        self.total_score = total
        self.max_possible_score = max_possible
        if max_possible > 0:
            self.percentage_score = (total / max_possible) * 100
        
        # Calculate category percentages
        self.category_scores = {
            cat: float((scores["score"] / scores["max"]) * 100) if scores["max"] > 0 else 0
            for cat, scores in category_totals.items()
        }
    
    def determine_result(self) -> None:
        """Determine qualification result based on scores and blockers."""
        if self.has_blockers:
            self.result = QualificationResult.NOT_QUALIFIED.value
            return
        
        if self.percentage_score is None:
            self.result = QualificationResult.PENDING.value
            return
        
        if self.percentage_score >= self.pass_threshold:
            self.result = QualificationResult.QUALIFIED.value
        elif self.percentage_score >= self.conditional_threshold:
            self.result = QualificationResult.CONDITIONALLY_QUALIFIED.value
        else:
            self.result = QualificationResult.NOT_QUALIFIED.value


class QualificationCriterion(Base, TimestampMixin):
    """
    Configurable qualification criterion.
    
    Defines what factors are evaluated during qualification.
    Can be customized per customer, product type, or globally.
    """
    
    __tablename__ = "qualification_criteria"
    
    # Identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Category
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CriterionCategory.TECHNICAL.value,
        index=True,
    )
    
    # Scoring
    max_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("10.00"),
        nullable=False,
    )
    default_weight: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("1.00"),
        nullable=False,
    )
    
    # Scoring guidance
    scoring_guide: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Example: {"0": "Not capable", "5": "Partially capable", "10": "Fully capable"}
    
    # Is this criterion a blocker if score is below threshold?
    is_blocker: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocker_threshold: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Is this criterion required for all qualifications?
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Is this criterion active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Display order
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Applicability conditions (e.g., only for certain process types)
    applicability: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    scores: Mapped[list["QualificationScore"]] = relationship(
        "QualificationScore",
        back_populates="criterion",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_qualification_criteria_category_order", category, display_order),
    )


class QualificationScore(Base, TimestampMixin):
    """
    Individual score for a qualification criterion.
    
    Records the evaluation of one criterion for one qualification.
    """
    
    __tablename__ = "qualification_scores"
    
    # Parent qualification
    qualification_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qualifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Criterion being scored
    criterion_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("qualification_criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Score
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("10.00"),
        nullable=False,
    )
    weight: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("1.00"),
        nullable=False,
    )
    
    # Is this a blocker at this score?
    is_blocker_triggered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Justification
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Who scored this?
    scored_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    scored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Auto-scored by system?
    is_auto_scored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_score_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Relationships
    qualification: Mapped["Qualification"] = relationship(
        "Qualification",
        back_populates="scores",
    )
    criterion: Mapped["QualificationCriterion"] = relationship(
        "QualificationCriterion",
        back_populates="scores",
    )
    scored_by: Mapped["User | None"] = relationship("User", foreign_keys=[scored_by_id])
    
    __table_args__ = (
        UniqueConstraint(
            "qualification_id",
            "criterion_id",
            name="uq_qualification_score_criterion",
        ),
        Index("ix_qualification_scores_qual_criterion", qualification_id, criterion_id),
    )
    
    @property
    def weighted_score(self) -> Decimal | None:
        """Calculate weighted score."""
        if self.score is None:
            return None
        return self.score * self.weight
    
    @property
    def percentage(self) -> Decimal | None:
        """Calculate percentage of max score."""
        if self.score is None:
            return None
        if self.max_score == 0:
            return Decimal("0")
        return (self.score / self.max_score) * 100

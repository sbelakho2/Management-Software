"""
A3 Problem Solving models.

Implements:
- A3: A3 problem-solving document
- A3Section: Individual sections of an A3
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.user import User


class A3Type(str, Enum):
    """Type of A3 document."""
    
    PROBLEM_SOLVING = "problem_solving"
    PROPOSAL = "proposal"
    STATUS_REPORT = "status_report"
    STRATEGY = "strategy"


class A3Status(str, Enum):
    """Status of A3 document."""
    
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class A3SectionType(str, Enum):
    """Standard A3 sections."""
    
    # Problem Solving A3
    BACKGROUND = "background"
    CURRENT_CONDITION = "current_condition"
    GOAL = "goal"
    ROOT_CAUSE = "root_cause"
    COUNTERMEASURES = "countermeasures"
    IMPLEMENTATION_PLAN = "implementation_plan"
    FOLLOW_UP = "follow_up"
    
    # Proposal A3
    PROBLEM_STATEMENT = "problem_statement"
    ANALYSIS = "analysis"
    PROPOSED_SOLUTION = "proposed_solution"
    COST_BENEFIT = "cost_benefit"
    TIMELINE = "timeline"
    RISKS = "risks"
    
    # Custom
    CUSTOM = "custom"


class A3(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    A3 problem-solving document.
    
    The A3 is a structured problem-solving approach used in Lean/TPS.
    Named after the A3 paper size (11x17 inches) traditionally used.
    """
    
    __tablename__ = "a3s"
    
    # Identification
    a3_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Type and Status
    a3_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=A3Type.PROBLEM_SOLVING.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=A3Status.DRAFT.value,
        index=True,
    )
    
    # Related Entity (polymorphic reference)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Ownership
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sponsor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    coach_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Team Members
    team_members: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # List of user IDs
    
    # Dates
    started_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    target_completion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    actual_completion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Review and Approval
    last_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Progress
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Version Control
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # PDF storage
    pdf_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Department/Area
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Priority
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    
    # Summary (for quick view)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Lessons Learned
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Yokoten (horizontal deployment) tracking
    is_yokoten_candidate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    yokoten_areas: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id])
    sponsor: Mapped["User | None"] = relationship("User", foreign_keys=[sponsor_id])
    coach: Mapped["User | None"] = relationship("User", foreign_keys=[coach_id])
    approved_by: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by_id])
    
    sections: Mapped[list["A3Section"]] = relationship(
        "A3Section",
        back_populates="a3",
        cascade="all, delete-orphan",
        order_by="A3Section.section_order",
        lazy="selectin",
    )
    
    __table_args__ = (
        Index("ix_a3s_type_status", a3_type, status),
        Index("ix_a3s_author_status", author_id, status),
        Index("ix_a3s_department", department),
        Index(
            "ix_a3s_open",
            status,
            postgresql_where=(status.notin_(["closed", "cancelled"])),
        ),
    )
    
    def update_progress(self) -> None:
        """Calculate progress based on section completion."""
        if not self.sections:
            self.progress_percentage = 0
            return
        
        total_sections = len(self.sections)
        completed_sections = sum(1 for s in self.sections if s.is_complete)
        
        self.progress_percentage = int((completed_sections / total_sections) * 100)
    
    @property
    def is_open(self) -> bool:
        """Check if A3 is still open."""
        return self.status not in [A3Status.CLOSED.value, A3Status.CANCELLED.value]
    
    @property
    def is_overdue(self) -> bool:
        """Check if A3 is overdue."""
        if self.target_completion_date is None:
            return False
        if not self.is_open:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.target_completion_date


class A3Section(Base, TimestampMixin):
    """
    Individual section of an A3 document.
    
    Each A3 consists of multiple sections following a structured template.
    """
    
    __tablename__ = "a3_sections"
    
    a3_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("a3s.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Section Identification
    section_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=A3SectionType.CUSTOM.value,
    )
    section_name: Mapped[str] = mapped_column(String(100), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Content
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Structured Content (for forms/diagrams)
    structured_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Can contain:
    # - 5 Whys analysis
    # - Fishbone diagram data
    # - Action items
    # - Metrics/KPIs
    # - Gantt chart data
    
    # Completion
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Guidance text for this section
    guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Attachments
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Comments/Feedback
    comments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Version
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Relationships
    a3: Mapped["A3"] = relationship("A3", back_populates="sections")
    completed_by: Mapped["User | None"] = relationship("User")
    
    __table_args__ = (
        UniqueConstraint("a3_id", "section_order", name="uq_a3_section_order"),
        Index("ix_a3_sections_a3_order", a3_id, section_order),
    )


# Default section templates for different A3 types
A3_SECTION_TEMPLATES = {
    A3Type.PROBLEM_SOLVING.value: [
        {
            "type": A3SectionType.BACKGROUND.value,
            "name": "Background",
            "guidance": "Provide context. Why is this problem important? What business need does it address?",
        },
        {
            "type": A3SectionType.CURRENT_CONDITION.value,
            "name": "Current Condition",
            "guidance": "Describe the current state. Use data and facts. What is actually happening?",
        },
        {
            "type": A3SectionType.GOAL.value,
            "name": "Goal/Target Condition",
            "guidance": "What specific, measurable outcome do you want to achieve? By when?",
        },
        {
            "type": A3SectionType.ROOT_CAUSE.value,
            "name": "Root Cause Analysis",
            "guidance": "Use 5 Whys, Fishbone, or other tools. What is the real cause of the problem?",
        },
        {
            "type": A3SectionType.COUNTERMEASURES.value,
            "name": "Countermeasures",
            "guidance": "What specific actions will address the root cause? Who, what, when?",
        },
        {
            "type": A3SectionType.IMPLEMENTATION_PLAN.value,
            "name": "Implementation Plan",
            "guidance": "Timeline, resources, responsibilities. How will you implement?",
        },
        {
            "type": A3SectionType.FOLLOW_UP.value,
            "name": "Follow-Up",
            "guidance": "How will you verify results? What metrics will you track?",
        },
    ],
    A3Type.PROPOSAL.value: [
        {
            "type": A3SectionType.BACKGROUND.value,
            "name": "Background",
            "guidance": "Context and business case for the proposal.",
        },
        {
            "type": A3SectionType.PROBLEM_STATEMENT.value,
            "name": "Problem/Opportunity",
            "guidance": "What problem are you solving or opportunity are you addressing?",
        },
        {
            "type": A3SectionType.ANALYSIS.value,
            "name": "Analysis",
            "guidance": "Data and analysis supporting your proposal.",
        },
        {
            "type": A3SectionType.PROPOSED_SOLUTION.value,
            "name": "Proposed Solution",
            "guidance": "Your recommended approach. Why this solution?",
        },
        {
            "type": A3SectionType.COST_BENEFIT.value,
            "name": "Cost/Benefit Analysis",
            "guidance": "Investment required and expected return.",
        },
        {
            "type": A3SectionType.TIMELINE.value,
            "name": "Timeline",
            "guidance": "Implementation schedule and milestones.",
        },
        {
            "type": A3SectionType.RISKS.value,
            "name": "Risks and Mitigation",
            "guidance": "Potential risks and how you will address them.",
        },
    ],
}

"""
Learning Engine models for Sensei teaching functionality.

Implements:
- LearningUnit: Individual learning content (lessons, concepts)
- LearningModule: Grouping of related learning units
- UserLearningProgress: User's progress through learning content
- LearningAssessment: Quizzes and assessments
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
    from sensei.models.user import User


class LearningCategory(str, Enum):
    """Category of learning content."""
    
    TPS = "tps"  # Toyota Production System
    LEAN = "lean"
    QUALITY = "quality"
    SAFETY = "safety"
    PROCESS = "process"
    TOOL = "tool"
    CONCEPT = "concept"
    BEST_PRACTICE = "best_practice"
    STANDARD = "standard"
    PROCEDURE = "procedure"


class ContentType(str, Enum):
    """Type of learning content."""
    
    TEXT = "text"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    INTERACTIVE = "interactive"
    QUIZ = "quiz"
    EXERCISE = "exercise"
    CASE_STUDY = "case_study"


class DifficultyLevel(str, Enum):
    """Difficulty level of content."""
    
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningModule(Base, TimestampMixin, AuditMixin):
    """
    Learning module - a collection of related learning units.
    
    Modules organize learning content into structured courses or paths.
    """
    
    __tablename__ = "learning_modules"
    
    # Identification
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=LearningCategory.TPS.value,
        index=True,
    )
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DifficultyLevel.BEGINNER.value,
    )
    
    # Content
    learning_objectives: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    prerequisites: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # List of module codes that should be completed first
    
    # Duration
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Ordering
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Thumbnail
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    units: Mapped[list["LearningUnit"]] = relationship(
        "LearningUnit",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="LearningUnit.unit_order",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_learning_modules_category_order", category, display_order),
        Index(
            "ix_learning_modules_published",
            is_published,
            postgresql_where=(is_published == True),  # noqa: E712
        ),
    )
    
    @property
    def unit_count(self) -> int:
        """Get number of units in this module."""
        return len(list(self.units))


class LearningUnit(Base, TimestampMixin, AuditMixin):
    """
    Individual learning unit - a single lesson or concept.
    
    The atomic unit of learning content in the Sensei teaching system.
    """
    
    __tablename__ = "learning_units"
    
    # Module relationship
    module_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_modules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Identification
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=LearningCategory.TPS.value,
        index=True,
    )
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ContentType.TEXT.value,
    )
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DifficultyLevel.BEGINNER.value,
    )
    
    # Content
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_rich: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Rich content structure for interactive content
    
    # Media
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Key Points
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Examples
    examples: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Anti-patterns (what NOT to do)
    anti_patterns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Related Concepts
    related_units: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # List of unit codes
    
    # Context - when is this relevant?
    triggers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Conditions that should trigger showing this content
    # e.g., ["rfq.qualification_score < 50", "user.role == 'new'"]
    
    # Duration
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Ordering within module
    unit_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Version
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Japanese term (for TPS concepts)
    japanese_term: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pronunciation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Source reference
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    module: Mapped["LearningModule | None"] = relationship(
        "LearningModule",
        back_populates="units",
    )
    
    progress_records: Mapped[list["UserLearningProgress"]] = relationship(
        "UserLearningProgress",
        back_populates="unit",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    assessments: Mapped[list["LearningAssessment"]] = relationship(
        "LearningAssessment",
        back_populates="unit",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_learning_units_module_order", module_id, unit_order),
        Index("ix_learning_units_category", category),
        Index(
            "ix_learning_units_published",
            is_published,
            postgresql_where=(is_published == True),  # noqa: E712
        ),
    )


class ProgressStatus(str, Enum):
    """Status of learning progress."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"


class UserLearningProgress(Base, TimestampMixin):
    """
    User's progress through a learning unit.
    
    Tracks completion, time spent, and performance.
    """
    
    __tablename__ = "user_learning_progress"
    
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProgressStatus.NOT_STARTED.value,
        index=True,
    )
    
    # Progress
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Dates
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Time Tracking
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Assessment Results
    best_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    last_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Bookmarks and Notes
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Review scheduling (spaced repetition)
    next_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ease_factor: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    # For spaced repetition algorithm
    
    # Position tracking (for resuming)
    last_position: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"section": 2, "timestamp": 125.5} for video
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    unit: Mapped["LearningUnit"] = relationship(
        "LearningUnit",
        back_populates="progress_records",
    )
    
    __table_args__ = (
        UniqueConstraint("user_id", "unit_id", name="uq_user_learning_progress"),
        Index("ix_user_learning_progress_user_status", user_id, status),
        Index("ix_user_learning_progress_review", user_id, next_review_date),
    )
    
    @property
    def is_completed(self) -> bool:
        """Check if unit is completed."""
        return self.status == ProgressStatus.COMPLETED.value
    
    @property
    def time_spent_formatted(self) -> str:
        """Get formatted time spent."""
        hours, remainder = divmod(self.time_spent_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        elif minutes:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class LearningAssessment(Base, TimestampMixin, AuditMixin):
    """
    Quiz or assessment for a learning unit.
    
    Contains questions and tracks user attempts.
    """
    
    __tablename__ = "learning_assessments"
    
    unit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Identification
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Questions
    questions: Mapped[list] = mapped_column(JSONB, nullable=False)
    # [
    #   {
    #     "id": "q1",
    #     "type": "multiple_choice",
    #     "question": "What is...?",
    #     "options": ["A", "B", "C", "D"],
    #     "correct_answer": "B",
    #     "explanation": "Because...",
    #     "points": 10
    #   },
    #   ...
    # ]
    
    # Passing criteria
    passing_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("70.00"),
        nullable=False,
    )
    max_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("100.00"),
        nullable=False,
    )
    
    # Settings
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_correct_answers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    unit: Mapped["LearningUnit | None"] = relationship(
        "LearningUnit",
        back_populates="assessments",
    )
    
    __table_args__ = (
        Index("ix_learning_assessments_unit", unit_id),
    )
    
    @property
    def question_count(self) -> int:
        """Get number of questions."""
        return len(self.questions) if self.questions else 0

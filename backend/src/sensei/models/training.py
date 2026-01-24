"""
Training and Skills models for competency management.

Skills define competencies required for stations/products.
Training tracks user certification and recertification.
"""

import enum
from datetime import datetime, date
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

if TYPE_CHECKING:
    from sensei.models.work_center import Station
    from sensei.models.product import Product
    from sensei.models.user import User


class SkillCategory(enum.Enum):
    """Category of skill."""

    TECHNICAL = "technical"
    QUALITY = "quality"
    SAFETY = "safety"
    LEADERSHIP = "leadership"
    EQUIPMENT = "equipment"
    PROCESS = "process"
    REGULATORY = "regulatory"
    SOFT_SKILLS = "soft_skills"


class TrainingType(enum.Enum):
    """Type of training delivery."""

    CLASSROOM = "classroom"
    ON_THE_JOB = "on_the_job"
    E_LEARNING = "e_learning"
    CERTIFICATION_EXAM = "certification_exam"
    RECERTIFICATION = "recertification"
    MENTORING = "mentoring"
    WORKSHOP = "workshop"
    SIMULATION = "simulation"


class TrainingStatus(enum.Enum):
    """Status of a training event."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class EnrollmentStatus(enum.Enum):
    """Status of a training enrollment."""

    ENROLLED = "enrolled"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class AttendanceStatus(enum.Enum):
    """Attendance status for training."""

    PENDING = "pending"
    ATTENDED = "attended"
    PARTIAL = "partial"
    ABSENT = "absent"
    EXCUSED = "excused"


class CertificationStatus(enum.Enum):
    """Status of user skill certification."""

    NOT_CERTIFIED = "not_certified"
    IN_TRAINING = "in_training"
    CERTIFIED = "certified"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class Skill(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Skill definition in the competency taxonomy.

    Skills can be required for stations, products, or roles.
    """

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    skill_category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory), nullable=False, default=SkillCategory.TECHNICAL
    )

    # Proficiency levels (JSON array)
    proficiency_levels: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=["Awareness", "Basic", "Proficient", "Expert", "Trainer"],
    )
    """
    Default levels:
    - Awareness: Basic understanding
    - Basic: Can perform with guidance
    - Proficient: Can perform independently
    - Expert: Can troubleshoot and optimize
    - Trainer: Can teach others
    """

    # Minimum level typically required
    minimum_required_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )  # Index into proficiency_levels (0-based)

    # Criticality
    is_safety_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_quality_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Recertification
    requires_recertification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    recertification_interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=365
    )

    # Training requirements
    initial_training_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("8.0")
    )
    recertification_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("2.0")
    )

    # Relationships
    requirements: Mapped[list["SkillRequirement"]] = relationship(
        "SkillRequirement", back_populates="skill", cascade="all, delete-orphan"
    )
    user_skills: Mapped[list["UserSkill"]] = relationship(
        "UserSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    trainings: Mapped[list["Training"]] = relationship(
        "Training", back_populates="skill"
    )

    __table_args__ = (
        CheckConstraint(
            "recertification_interval_days >= 0",
            name="ck_skill_recert_interval_nonnegative",
        ),
        CheckConstraint(
            "initial_training_hours >= 0",
            name="ck_skill_initial_hours_nonnegative",
        ),
        CheckConstraint(
            "minimum_required_level >= 0",
            name="ck_skill_min_level_nonnegative",
        ),
    )

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, code='{self.code}', name='{self.name}')>"

    @property
    def level_count(self) -> int:
        """Number of proficiency levels."""
        return len(self.proficiency_levels)

    def get_level_name(self, level_index: int) -> Optional[str]:
        """Get proficiency level name by index."""
        if 0 <= level_index < len(self.proficiency_levels):
            return self.proficiency_levels[level_index]
        return None


class SkillRequirement(Base, TimestampMixin, AuditMixin):
    """
    Skill requirement linking skills to stations or products.

    Defines what skills are needed and at what level.
    """

    __tablename__ = "skill_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Skill reference
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False, index=True
    )

    # Target (at least one must be set)
    station_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=True, index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )

    # Requirement details
    minimum_proficiency_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )  # Index into skill's proficiency_levels
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    skill: Mapped["Skill"] = relationship("Skill", back_populates="requirements")
    station: Mapped[Optional["Station"]] = relationship(
        "Station", back_populates="skill_requirements"
    )
    product: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="skill_requirements"
    )

    __table_args__ = (
        CheckConstraint(
            "(station_id IS NOT NULL) OR (product_id IS NOT NULL)",
            name="ck_skill_req_has_target",
        ),
        CheckConstraint(
            "minimum_proficiency_level >= 0",
            name="ck_skill_req_level_nonnegative",
        ),
        UniqueConstraint(
            "skill_id", "station_id", "product_id",
            name="uq_skill_requirement_target"
        ),
    )

    def __repr__(self) -> str:
        target = f"station={self.station_id}" if self.station_id else f"product={self.product_id}"
        return f"<SkillRequirement(skill_id={self.skill_id}, {target})>"


class Training(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Training event or course.

    Scheduled training sessions for skill development.
    """

    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Skill linkage
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False, index=True
    )

    # Training details
    training_type: Mapped[TrainingType] = mapped_column(
        Enum(TrainingType), nullable=False, default=TrainingType.CLASSROOM
    )
    duration_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("8.0")
    )
    max_participants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Scheduling
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    scheduled_end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[TrainingStatus] = mapped_column(
        Enum(TrainingStatus),
        nullable=False,
        default=TrainingStatus.SCHEDULED,
        index=True,
    )

    # Trainer
    trainer_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    external_trainer_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Certification info
    provides_certification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    certification_level_granted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )  # Level index

    # Cost tracking
    cost_per_person: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Materials/content reference
    materials_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    syllabus: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    skill: Mapped["Skill"] = relationship("Skill", back_populates="trainings")
    trainer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[trainer_id])
    participants: Mapped[list["TrainingParticipant"]] = relationship(
        "TrainingParticipant",
        back_populates="training",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "duration_hours > 0", name="ck_training_duration_positive"
        ),
        CheckConstraint(
            "max_participants IS NULL OR max_participants > 0",
            name="ck_training_max_participants_positive",
        ),
    )

    def __repr__(self) -> str:
        return f"<Training(id={self.id}, name='{self.name}', status={self.status.value})>"

    @property
    def enrolled_count(self) -> int:
        """Count of enrolled participants."""
        return sum(
            1 for p in self.participants
            if p.enrollment_status in [EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
        )

    @property
    def has_capacity(self) -> bool:
        """Check if training has capacity for more participants."""
        if self.max_participants is None:
            return True
        return self.enrolled_count < self.max_participants

    @property
    def is_upcoming(self) -> bool:
        """Check if training is in the future."""
        if self.scheduled_date:
            return self.scheduled_date > date.today()
        return False


class TrainingParticipant(Base, TimestampMixin, AuditMixin):
    """
    Training participant enrollment and completion record.
    """

    __tablename__ = "training_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Training and user reference
    training_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trainings.id"), nullable=False, index=True
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Status
    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus),
        nullable=False,
        default=EnrollmentStatus.ENROLLED,
        index=True,
    )
    attendance_status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus),
        nullable=False,
        default=AttendanceStatus.PENDING,
    )

    # Results
    score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # 0-100
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Certification issued
    certificate_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    certificate_issued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    training: Mapped["Training"] = relationship(
        "Training", back_populates="participants"
    )
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint(
            "training_id", "user_id", name="uq_training_participant_user"
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_training_participant_score_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<TrainingParticipant(training_id={self.training_id}, user_id={self.user_id})>"


class UserSkill(Base, TimestampMixin, AuditMixin):
    """
    User competency and certification record.

    Tracks user proficiency levels and certification status per skill.
    """

    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # User and skill reference
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False, index=True
    )

    # Proficiency
    proficiency_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Index into skill's proficiency_levels

    # Certification status
    certification_status: Mapped[CertificationStatus] = mapped_column(
        Enum(CertificationStatus),
        nullable=False,
        default=CertificationStatus.NOT_CERTIFIED,
        index=True,
    )

    # Certification dates
    certified_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_recertification_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )

    # Certification authority
    certified_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    certificate_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Assessment history
    assessment_scores: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )
    """
    Assessment history structure:
    [
        {
            "date": "2024-01-15",
            "score": 85,
            "type": "practical",
            "assessor_id": 123,
            "notes": "..."
        },
        ...
    ]
    """

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    skill: Mapped["Skill"] = relationship("Skill", back_populates="user_skills")
    certified_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[certified_by_id]
    )

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
        CheckConstraint(
            "proficiency_level >= 0", name="ck_user_skill_level_nonnegative"
        ),
    )

    def __repr__(self) -> str:
        return f"<UserSkill(user_id={self.user_id}, skill_id={self.skill_id}, status={self.certification_status.value})>"

    @property
    def is_certified(self) -> bool:
        """Check if user is currently certified."""
        return self.certification_status == CertificationStatus.CERTIFIED

    @property
    def is_expired(self) -> bool:
        """Check if certification has expired."""
        if self.expiration_date:
            return date.today() > self.expiration_date
        return False

    @property
    def days_until_expiration(self) -> Optional[int]:
        """Days until certification expires."""
        if self.expiration_date:
            delta = self.expiration_date - date.today()
            return delta.days
        return None

    @property
    def needs_recertification_soon(self) -> bool:
        """Check if recertification is needed within 30 days."""
        days = self.days_until_expiration
        if days is not None:
            return 0 < days <= 30
        return False


class LessonDifficulty(enum.Enum):
    """Difficulty level of a lesson."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Lesson(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Training lesson for the ML-based recommendation system.

    Lessons are individual learning units that can be recommended
    to users based on their role, skills, and learning history.
    """

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Identification
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Content metadata
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    target_roles: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    skills_taught: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)

    # Requirements and flags
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compliance_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Difficulty and duration
    difficulty: Mapped[Optional[LessonDifficulty]] = mapped_column(
        Enum(LessonDifficulty), nullable=True, default=LessonDifficulty.INTERMEDIATE
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Rating (calculated from completions)
    average_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # 0.00 to 5.00
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Content reference (URL or internal content ID)
    content_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Related skill (optional)
    skill_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    skill: Mapped[Optional["Skill"]] = relationship("Skill")
    completions: Mapped[list["LessonCompletion"]] = relationship(
        "LessonCompletion", back_populates="lesson", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, title='{self.title}')>"


class LessonCompletion(Base, TimestampMixin, AuditMixin):
    """
    Record of a user completing a lesson.

    Tracks completion status, ratings, and feedback for the
    ML recommendation system's collaborative filtering.
    """

    __tablename__ = "lesson_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # User and lesson references
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )

    # Completion tracking
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # User feedback
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Progress tracking
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_spent_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="completions")

    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_completion_user_lesson"),
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_lesson_completion_rating"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_lesson_completion_progress"),
    )

    def __repr__(self) -> str:
        return f"<LessonCompletion(user_id={self.user_id}, lesson_id={self.lesson_id}, completed={self.completed})>"

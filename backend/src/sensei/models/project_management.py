"""
Project Management Models - Taiga-like Task Management System.

A comprehensive project/task management system that extends and integrates with
all Sensei OS modules. Addresses known Taiga shortcomings:
- Real-time collaboration with WebSocket support
- Deep integration with manufacturing workflows
- AI-powered task recommendations
- Comprehensive audit trails
- Role-based visibility and permissions
- Mobile-first design support
- Offline capability support
"""

from datetime import datetime, date
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.user import User


# =============================================================================
# ENUMS
# =============================================================================


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class ProjectType(str, Enum):
    """Type of project."""
    STANDARD = "standard"
    SCRUM = "scrum"
    KANBAN = "kanban"
    HYBRID = "hybrid"
    NPI = "npi"  # New Product Introduction
    KAIZEN = "kaizen"  # Continuous Improvement
    A3 = "a3"  # A3 Problem Solving
    MAINTENANCE = "maintenance"


class SprintStatus(str, Enum):
    """Sprint status."""
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UserStoryStatus(str, Enum):
    """User story status."""
    NEW = "new"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    READY_FOR_TEST = "ready_for_test"
    DONE = "done"
    ARCHIVED = "archived"


class EpicStatus(str, Enum):
    """Epic status."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CLOSED = "closed"


class IssueType(str, Enum):
    """Issue types for tracking bugs and improvements."""
    BUG = "bug"
    IMPROVEMENT = "improvement"
    TASK = "task"
    QUESTION = "question"
    INCIDENT = "incident"
    NCR = "ncr"  # Non-Conformance Report
    SAFETY = "safety"


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    WISHLIST = "wishlist"
    MINOR = "minor"
    NORMAL = "normal"
    IMPORTANT = "important"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    """Issue status."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    READY_FOR_TEST = "ready_for_test"
    CLOSED = "closed"
    REJECTED = "rejected"
    POSTPONED = "postponed"


class IssuePriority(str, Enum):
    """Issue priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MilestoneType(str, Enum):
    """Milestone type."""
    SPRINT = "sprint"
    RELEASE = "release"
    PHASE_GATE = "phase_gate"
    DEADLINE = "deadline"
    AUDIT = "audit"
    CERTIFICATION = "certification"


class WikiPageType(str, Enum):
    """Wiki page types."""
    DOCUMENTATION = "documentation"
    STANDARD_WORK = "standard_work"
    PROCESS = "process"
    REFERENCE = "reference"
    TEMPLATE = "template"
    MEETING_NOTES = "meeting_notes"


class BoardType(str, Enum):
    """Board visualization types."""
    KANBAN = "kanban"
    SCRUM = "scrum"
    SWIMLANE = "swimlane"
    TIMELINE = "timeline"
    CALENDAR = "calendar"


# =============================================================================
# PROJECT MODEL
# =============================================================================


class Project(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Project container for organizing work.
    
    Projects can be associated with various Sensei OS entities:
    - RFQs/Quotes (sales projects)
    - Work Orders (production projects)
    - A3 Problem Reports (improvement projects)
    - NPI programs (engineering projects)
    - Maintenance programs (TPM projects)
    """
    
    __tablename__ = "projects"
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Project Type and Status
    project_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProjectType.STANDARD.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProjectStatus.PLANNING.value,
        index=True,
    )
    
    # Ownership
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Visibility & Privacy
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Schedule
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#3b82f6", nullable=False)
    
    # Settings
    default_story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    sprint_duration_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    use_story_points: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    use_time_tracking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_watchers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_wiki: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_issues: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_sprints: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Custom Statuses (JSON arrays of status definitions)
    custom_user_story_statuses: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    custom_task_statuses: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    custom_issue_statuses: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    # Integration Links
    related_rfq_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("work_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_a3_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("a3s.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Metadata
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Statistics (cached, updated by triggers/workers)
    total_user_stories: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_user_stories: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_story_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_story_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[owner_id],
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    epics: Mapped[list["Epic"]] = relationship(
        "Epic",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    user_stories: Mapped[list["UserStory"]] = relationship(
        "UserStory",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    sprints: Mapped[list["Sprint"]] = relationship(
        "Sprint",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    wiki_pages: Mapped[list["WikiPage"]] = relationship(
        "WikiPage",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        "ProjectMilestone",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_projects_owner_status", owner_id, status),
        Index("ix_projects_type_status", project_type, status),
    )
    
    @property
    def progress_percentage(self) -> float:
        """Calculate project progress as percentage."""
        if self.use_story_points and self.total_story_points > 0:
            return (self.completed_story_points / self.total_story_points) * 100
        elif self.total_user_stories > 0:
            return (self.completed_user_stories / self.total_user_stories) * 100
        return 0.0
    
    @property
    def is_on_track(self) -> bool:
        """Check if project is on track for deadline."""
        if not self.target_end_date:
            return True
        if self.status == ProjectStatus.COMPLETED.value:
            return True
        
        from datetime import date as dt_date
        today = dt_date.today()
        if today > self.target_end_date:
            return False
        
        # Calculate expected progress
        if self.start_date:
            total_days = (self.target_end_date - self.start_date).days
            elapsed_days = (today - self.start_date).days
            if total_days > 0:
                expected_progress = (elapsed_days / total_days) * 100
                return self.progress_percentage >= expected_progress * 0.9  # 10% buffer
        return True


class ProjectMember(Base, TimestampMixin):
    """
    Project membership with role.
    """
    
    __tablename__ = "project_members"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    
    # Role in project
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="member",
    )  # admin, member, viewer, guest
    
    # Permissions
    can_edit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_comment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_invite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Notifications
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User")


# =============================================================================
# EPIC MODEL
# =============================================================================


class Epic(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Epic: Large body of work that can be broken into smaller user stories.
    
    Epics provide high-level grouping and can span multiple sprints.
    """
    
    __tablename__ = "epics"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Reference
    ref: Mapped[int] = mapped_column(Integer, nullable=False)  # Project-specific reference number
    
    # Basic Information
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=EpicStatus.NEW.value,
        index=True,
    )
    
    # Color for visual identification
    color: Mapped[str] = mapped_column(String(7), default="#8b5cf6", nullable=False)
    
    # Assignment
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Tags
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Watchers
    watchers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Custom attributes
    custom_attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="epics")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    user_stories: Mapped[list["UserStory"]] = relationship(
        "UserStory",
        back_populates="epic",
    )
    
    __table_args__ = (
        UniqueConstraint("project_id", "ref", name="uq_epic_project_ref"),
        Index("ix_epics_project_status", project_id, status),
    )
    
    @property
    def progress(self) -> float:
        """Calculate epic progress."""
        if not self.user_stories:
            return 0.0
        total = len(self.user_stories)
        done = sum(1 for us in self.user_stories if us.status == UserStoryStatus.DONE.value)
        return (done / total) * 100 if total > 0 else 0.0


# =============================================================================
# USER STORY MODEL
# =============================================================================


class UserStory(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    User Story: A unit of work from the user's perspective.
    
    Follows the format: "As a [role], I want [feature] so that [benefit]"
    Can contain multiple subtasks.
    """
    
    __tablename__ = "user_stories"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Reference
    ref: Mapped[int] = mapped_column(Integer, nullable=False)  # Project-specific reference number
    
    # Epic (optional grouping)
    epic_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("epics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Sprint (optional assignment)
    sprint_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Milestone
    milestone_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Basic Information
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # User Story Format
    as_a: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Role
    i_want: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Feature
    so_that: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Benefit
    
    # Acceptance Criteria (checklist format)
    acceptance_criteria: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{"id": "1", "text": "Criterion 1", "checked": false}, ...]
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserStoryStatus.NEW.value,
        index=True,
    )
    
    # Assignment
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_users: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Estimation
    story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Priority
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0-100, higher = more important
    
    # Ordering (for backlog/sprint)
    backlog_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sprint_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kanban_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Due date
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Progress
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocked_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Time tracking
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Tags
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Watchers
    watchers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Custom attributes
    custom_attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Sensei OS Integration
    related_work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("work_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_ctq_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ctqs.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="user_stories")
    epic: Mapped[Optional["Epic"]] = relationship("Epic", back_populates="user_stories")
    sprint: Mapped[Optional["Sprint"]] = relationship("Sprint", back_populates="user_stories")
    milestone: Mapped[Optional["ProjectMilestone"]] = relationship("ProjectMilestone", back_populates="user_stories")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    subtasks: Mapped[list["Subtask"]] = relationship(
        "Subtask",
        back_populates="user_story",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["StoryComment"]] = relationship(
        "StoryComment",
        back_populates="user_story",
        cascade="all, delete-orphan",
        order_by="StoryComment.created_at",
    )
    history: Mapped[list["StoryHistory"]] = relationship(
        "StoryHistory",
        back_populates="user_story",
        cascade="all, delete-orphan",
        order_by="StoryHistory.created_at.desc()",
    )
    
    __table_args__ = (
        UniqueConstraint("project_id", "ref", name="uq_user_story_project_ref"),
        Index("ix_user_stories_project_status", project_id, status),
        Index("ix_user_stories_sprint", sprint_id),
        Index("ix_user_stories_epic", epic_id),
        Index("ix_user_stories_owner", owner_id),
    )
    
    @property
    def subtask_progress(self) -> tuple[int, int]:
        """Get subtask completion progress (completed, total)."""
        if not self.subtasks:
            return (0, 0)
        total = len(self.subtasks)
        completed = sum(1 for st in self.subtasks if st.is_closed)
        return (completed, total)
    
    @property
    def acceptance_criteria_progress(self) -> tuple[int, int]:
        """Get acceptance criteria progress (checked, total)."""
        if not self.acceptance_criteria:
            return (0, 0)
        total = len(self.acceptance_criteria)
        checked = sum(1 for ac in self.acceptance_criteria if ac.get("checked", False))
        return (checked, total)


class Subtask(Base, TimestampMixin, AuditMixin):
    """
    Subtask within a user story.
    
    Represents a specific piece of work that needs to be done
    to complete the parent user story.
    """
    
    __tablename__ = "subtasks"
    
    user_story_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Reference
    ref: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Basic Information
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Assignment
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="open", index=True, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Time tracking
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Due date
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    user_story: Mapped["UserStory"] = relationship("UserStory", back_populates="subtasks")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    
    __table_args__ = (
        UniqueConstraint("user_story_id", "ref", name="uq_subtask_story_ref"),
    )


class StoryComment(Base, TimestampMixin):
    """
    Comment on a user story.
    """
    
    __tablename__ = "story_comments"
    
    user_story_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Mentions
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    # Edited
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user_story: Mapped["UserStory"] = relationship("UserStory", back_populates="comments")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])


class StoryHistory(Base, TimestampMixin):
    """
    History entry for user story changes.
    """
    
    __tablename__ = "story_history"
    
    user_story_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Change details
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Comment (optional explanation)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user_story: Mapped["UserStory"] = relationship("UserStory", back_populates="history")
    user: Mapped[Optional["User"]] = relationship("User")


# =============================================================================
# SPRINT MODEL
# =============================================================================


class Sprint(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Sprint: Time-boxed iteration for completing user stories.
    """
    
    __tablename__ = "sprints"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SprintStatus.PLANNED.value,
        index=True,
    )
    
    # Schedule
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Goals
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Retrospective
    retrospective_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Velocity (story points completed)
    planned_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Order
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Closed flag
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="sprints")
    user_stories: Mapped[list["UserStory"]] = relationship(
        "UserStory",
        back_populates="sprint",
    )
    
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_sprint_project_slug"),
        Index("ix_sprints_project_status", project_id, status),
    )
    
    @property
    def velocity(self) -> int:
        """Get sprint velocity (completed story points)."""
        return self.completed_points
    
    @property
    def progress(self) -> float:
        """Calculate sprint progress."""
        if self.planned_points <= 0:
            return 0.0
        return (self.completed_points / self.planned_points) * 100


# =============================================================================
# ISSUE MODEL
# =============================================================================


class Issue(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Issue: Bug, improvement, or other tracked item.
    
    Separate from user stories, issues are typically used for:
    - Bug reports
    - Technical debt
    - Improvement suggestions
    - NCRs (Non-Conformance Reports)
    - Safety incidents
    """
    
    __tablename__ = "issues"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Reference
    ref: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Milestone
    milestone_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Basic Information
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Classification
    issue_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IssueType.BUG.value,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IssueSeverity.NORMAL.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IssuePriority.NORMAL.value,
        index=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IssueStatus.NEW.value,
        index=True,
    )
    
    # Assignment
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Due date
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    finished_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Tags
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Watchers
    watchers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Custom attributes
    custom_attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Sensei OS Integration
    related_nc_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("non_conformances.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_capa_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("capas.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="issues")
    milestone: Mapped[Optional["ProjectMilestone"]] = relationship("ProjectMilestone", back_populates="issues")
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    comments: Mapped[list["IssueComment"]] = relationship(
        "IssueComment",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="IssueComment.created_at",
    )
    
    __table_args__ = (
        UniqueConstraint("project_id", "ref", name="uq_issue_project_ref"),
        Index("ix_issues_project_status", project_id, status),
        Index("ix_issues_assigned", assigned_to_id),
    )


class IssueComment(Base, TimestampMixin):
    """
    Comment on an issue.
    """
    
    __tablename__ = "issue_comments"
    
    issue_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Mentions
    mentions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    # Edited
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    issue: Mapped["Issue"] = relationship("Issue", back_populates="comments")
    author: Mapped[Optional["User"]] = relationship("User")


# =============================================================================
# MILESTONE MODEL
# =============================================================================


class ProjectMilestone(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Milestone: A significant point or event in a project.
    
    Can represent sprints, releases, phase gates, or deadlines.
    """
    
    __tablename__ = "milestones"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Type
    milestone_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MilestoneType.DEADLINE.value,
    )
    
    # Schedule
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Status
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Statistics
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    closed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="milestones")
    user_stories: Mapped[list["UserStory"]] = relationship(
        "UserStory",
        back_populates="milestone",
    )
    issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="milestone",
    )
    
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_milestone_project_slug"),
        Index("ix_milestones_project_due", project_id, due_date),
    )
    
    @property
    def progress(self) -> float:
        """Calculate milestone progress."""
        if self.total_items <= 0:
            return 0.0
        return (self.closed_items / self.total_items) * 100


# =============================================================================
# WIKI MODEL
# =============================================================================


class WikiPage(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Wiki page for project documentation.
    """
    
    __tablename__ = "wiki_pages"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic Information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    # Type
    page_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=WikiPageType.DOCUMENTATION.value,
    )
    
    # Hierarchy
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wiki_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Owner
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Version tracking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Watchers
    watchers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="wiki_pages")
    parent: Mapped[Optional["WikiPage"]] = relationship(
        "WikiPage",
        remote_side="WikiPage.id",
        backref="children",
    )
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_wiki_page_project_slug"),
    )


# =============================================================================
# ACTIVITY TIMELINE MODEL
# =============================================================================


class ProjectActivity(Base, TimestampMixin):
    """
    Activity log for project-related events.
    
    Provides a timeline of all activities in a project for
    transparency and audit purposes.
    """
    
    __tablename__ = "project_activities"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Activity details
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g., "create_story", "update_issue", "close_sprint", "add_comment"
    
    # Entity reference
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    entity_ref: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For readable references
    
    # Summary
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Details (JSON with full change data)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project")
    user: Mapped[Optional["User"]] = relationship("User")
    
    __table_args__ = (
        Index("ix_project_activities_project_created", project_id, "created_at"),
    )


# =============================================================================
# BOARD VIEW MODEL
# =============================================================================


class BoardView(Base, TimestampMixin):
    """
    Saved board view configuration.
    
    Allows users to save custom board views with filters and layout.
    """
    
    __tablename__ = "board_views"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Board type
    board_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=BoardType.KANBAN.value,
    )
    
    # Configuration
    filters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    columns: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    swimlanes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Default flag
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project")
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("ix_board_views_project_user", project_id, user_id),
    )


# =============================================================================
# SEQUENCE MODEL
# =============================================================================


class ProjectSequence(Base):
    """
    Project-specific sequences for reference numbers.
    
    Used to prevent collisions and ensure contiguous numbering
    for epics, user stories, and issues within a project.
    """
    
    __tablename__ = "project_sequences"
    
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        primary_key=True,
    )  # epic, user_story, issue
    
    last_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationship
    project: Mapped["Project"] = relationship("Project")

"""
Task and Notification models.

Implements:
- Task: Action items and to-dos
- TaskComment: Discussion on tasks
- Notification: User notifications
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.user import User


class TaskStatus(str, Enum):
    """Task workflow states."""
    
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    """Type of task."""
    
    ACTION = "action"
    FOLLOW_UP = "follow_up"
    REVIEW = "review"
    APPROVAL = "approval"
    CALL = "call"
    MEETING = "meeting"
    DOCUMENT = "document"
    OTHER = "other"


class Task(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Task/action item.
    
    General-purpose task management for tracking work items.
    Can be linked to any entity (RFQ, Quote, Risk, etc.).
    """
    
    __tablename__ = "tasks"
    
    # Basic Information
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Classification
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TaskType.ACTION.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TaskStatus.TODO.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TaskPriority.MEDIUM.value,
        index=True,
    )
    
    # Related Entity (polymorphic reference)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Assignment
    assignee_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Dates
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Time Tracking
    estimated_hours: Mapped[float | None] = mapped_column(nullable=True)
    actual_hours: Mapped[float | None] = mapped_column(nullable=True)
    
    # Progress
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Blocked
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_by_task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Recurring
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # e.g., "daily", "weekly", "monthly", "weekly:mon,wed,fri"
    parent_task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Reminders
    reminder_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Checklist
    checklist: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # [{"id": "1", "text": "Item 1", "checked": false}, ...]
    
    # Attachments
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    assignee: Mapped["User | None"] = relationship(
        "User",
        back_populates="tasks_assigned",
        foreign_keys=[assignee_id],
    )
    creator: Mapped["User | None"] = relationship(
        "User",
        back_populates="tasks_created",
        foreign_keys=[created_by_id],
    )
    blocked_by: Mapped["Task | None"] = relationship(
        "Task",
        remote_side="Task.id",
        foreign_keys=[blocked_by_task_id],
    )
    parent_task: Mapped["Task | None"] = relationship(
        "Task",
        remote_side="Task.id",
        foreign_keys=[parent_task_id],
        backref="subtasks",
    )
    
    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskComment.created_at",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_tasks_assignee_status", assignee_id, status),
        Index("ix_tasks_status_due", status, due_date),
        Index("ix_tasks_related", related_entity_type, related_entity_id),
        Index(
            "ix_tasks_open",
            status,
            postgresql_where=(status.notin_(["done", "cancelled"])),
        ),
    )
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if self.due_date is None:
            return False
        if self.status in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.due_date
    
    @property
    def is_open(self) -> bool:
        """Check if task is still open."""
        return self.status not in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]
    
    @property
    def checklist_progress(self) -> tuple[int, int]:
        """Get checklist progress (completed, total)."""
        if not self.checklist:
            return (0, 0)
        total = len(self.checklist)
        completed = sum(1 for item in self.checklist if item.get("checked", False))
        return (completed, total)


class TaskComment(Base, TimestampMixin):
    """
    Comment on a task.
    """
    
    __tablename__ = "task_comments"
    
    task_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Author
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Is this a status change note?
    is_status_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Edited
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Mentions
    mentions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Attachments
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id])
    
    __table_args__ = (
        Index("ix_task_comments_task_created", "task_id", "created_at"),
    )


class NotificationType(str, Enum):
    """Type of notification."""
    
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE = "task_due"
    TASK_OVERDUE = "task_overdue"
    TASK_COMPLETED = "task_completed"
    TASK_COMMENT = "task_comment"
    
    RFQ_RECEIVED = "rfq_received"
    RFQ_DUE = "rfq_due"
    RFQ_ASSIGNED = "rfq_assigned"
    RFQ_STATUS_CHANGE = "rfq_status_change"
    
    QUOTE_APPROVAL_NEEDED = "quote_approval_needed"
    QUOTE_APPROVED = "quote_approved"
    QUOTE_REJECTED = "quote_rejected"
    QUOTE_SENT = "quote_sent"
    QUOTE_VIEWED = "quote_viewed"
    
    MENTION = "mention"
    SYSTEM = "system"
    REMINDER = "reminder"
    ANNOUNCEMENT = "announcement"


class NotificationPriority(str, Enum):
    """Priority of notification."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Status of notification delivery."""
    
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    """Channel for notification delivery."""
    
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class Notification(Base, TimestampMixin):
    """
    User notification.
    
    Tracks notifications sent to users through various channels.
    """
    
    __tablename__ = "notifications"
    
    # Recipient
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Content
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Priority
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=NotificationPriority.NORMAL.value,
    )
    
    # Related Entity
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    
    # Action URL
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Delivery Channels
    channels_sent: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # ["in_app", "email", "push"]
    
    # Email delivery
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Push delivery
    push_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Extra data
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Sender (for system notifications, this might be null)
    sender_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[user_id],
    )
    sender: Mapped["User | None"] = relationship("User", foreign_keys=[sender_id])
    
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index(
            "ix_notifications_unread",
            "user_id",
            postgresql_where=text("is_read = false"),
        ),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if self.expires_at is None:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.expires_at

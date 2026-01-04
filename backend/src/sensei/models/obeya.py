"""
Obeya (Big Room) models for visual management.

Implements:
- ObeyaItem: Visual management board items
- ObeyaComment: Discussion thread on items
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.user import User


class ObeyaCategory(str, Enum):
    """Category of Obeya item."""
    
    ISSUE = "issue"
    ACTION = "action"
    RISK = "risk"
    DECISION = "decision"
    MILESTONE = "milestone"
    KPI = "kpi"
    ESCALATION = "escalation"
    INFORMATION = "information"
    LESSON_LEARNED = "lesson_learned"
    METRICS = "metrics"
    SCHEDULE = "schedule"
    QUALITY = "quality"
    COST = "cost"
    SAFETY = "safety"
    MORALE = "morale"
    DELIVERY = "delivery"
    STRATEGY = "strategy"


class ObeyaStatus(str, Enum):
    """Status of Obeya item."""
    
    NEW = "new"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ObeyaPriority(str, Enum):
    """Priority of Obeya item."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ObeyaBoard(str, Enum):
    """Board type for Obeya room."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    PROJECT = "project"
    STRATEGIC = "strategic"
    QUALITY = "quality"
    SAFETY = "safety"
    IMPROVEMENT = "improvement"


class ObeyaItemStatus(str, Enum):
    """Status of Obeya item."""
    
    ACTIVE = "active"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class ObeyaItemType(str, Enum):
    """Type of Obeya item."""
    
    KPI = "kpi"
    METRIC = "metric"
    MILESTONE = "milestone"
    ISSUE = "issue"
    ACTION = "action"
    DECISION = "decision"
    RISK = "risk"
    OPPORTUNITY = "opportunity"


class ObeyaItem(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Obeya visual management item.
    
    Represents a card on the Obeya board (big room visual management).
    Used for daily/weekly standups, issue tracking, and visual management.
    """
    
    __tablename__ = "obeya_items"
    
    # Board and Position
    board: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ObeyaBoard.DAILY.value,
        index=True,
    )
    column: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ObeyaCategory.ACTION.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ObeyaStatus.NEW.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ObeyaPriority.MEDIUM.value,
        index=True,
    )
    
    # Color coding for visual management
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # e.g., "red", "yellow", "green", "blue"
    
    # Related Entity (polymorphic reference)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Assignment
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Dates
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    target_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # For issues
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # For decisions
    decision_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # For KPIs
    kpi_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kpi_actual: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kpi_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kpi_trend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "improving", "stable", "declining"
    
    # Escalation
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    escalated_to_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Days tracking
    days_open: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_overdue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Attachments and Links
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    links: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Meeting Reference
    meeting_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    meeting_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Relationships
    assigned_to: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
    )
    escalated_to: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[escalated_to_id],
    )
    
    comments: Mapped[list["ObeyaComment"]] = relationship(
        "ObeyaComment",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ObeyaComment.created_at",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_obeya_items_board_category", board, category),
        Index("ix_obeya_items_status_priority", status, priority),
        Index("ix_obeya_items_assigned_status", assigned_to_id, status),
        Index("ix_obeya_items_board_position", board, column, position),
        Index(
            "ix_obeya_items_open",
            status,
            postgresql_where=(status.notin_(["completed", "cancelled"])),
        ),
    )
    
    def update_days_tracking(self) -> None:
        """Update days open and overdue counters."""
        from datetime import timezone as tz
        
        now = datetime.now(tz.utc)
        
        if self.status in [ObeyaStatus.COMPLETED.value, ObeyaStatus.CANCELLED.value]:
            return
        
        self.days_open = (now - self.created_at).days
        
        if self.due_date and now > self.due_date:
            self.days_overdue = (now - self.due_date).days
        else:
            self.days_overdue = 0
    
    @property
    def is_overdue(self) -> bool:
        """Check if item is overdue."""
        if self.due_date is None:
            return False
        if self.status in [ObeyaStatus.COMPLETED.value, ObeyaStatus.CANCELLED.value]:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.due_date
    
    @property
    def is_open(self) -> bool:
        """Check if item is still open."""
        return self.status not in [
            ObeyaStatus.COMPLETED.value,
            ObeyaStatus.CANCELLED.value,
        ]


class ObeyaComment(Base, TimestampMixin):
    """
    Comment/discussion on an Obeya item.
    """
    
    __tablename__ = "obeya_comments"
    
    item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("obeya_items.id", ondelete="CASCADE"),
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
    
    # Reply to another comment
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("obeya_comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    
    # Is this a status change note?
    is_status_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Is this comment pinned?
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Edited
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Mentions
    mentions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # List of user IDs mentioned
    
    # Attachments
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    item: Mapped["ObeyaItem"] = relationship("ObeyaItem", back_populates="comments")
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id])
    parent: Mapped["ObeyaComment | None"] = relationship(
        "ObeyaComment",
        remote_side="ObeyaComment.id",
        backref="replies",
    )
    
    __table_args__ = (
        Index("ix_obeya_comments_item_created", "item_id", "created_at"),
    )

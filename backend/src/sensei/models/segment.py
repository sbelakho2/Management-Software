"""Segment Views SQLAlchemy models.

Models for saved filter segments and sharing:
- Segment: Saved filter configurations per module
- SegmentShare: Sharing records between users
- SegmentUsage: Usage analytics tracking
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class SegmentModule(str, Enum):
    """Modules that support segmentation."""
    RFQ = "rfq"
    QUOTE = "quote"
    OPPORTUNITY = "opportunity"
    QUALIFICATION = "qualification"
    WORK_ORDER = "work_order"
    KANBAN = "kanban"
    ANDON = "andon"
    A3 = "a3"
    CAPA = "capa"
    TRAINING = "training"
    AUDIT = "audit"
    PRODUCT = "product"
    CUSTOMER = "customer"


class SegmentVisibility(str, Enum):
    """Segment visibility levels."""
    PRIVATE = "private"
    TEAM = "team"
    DEPARTMENT = "department"
    ORGANIZATION = "organization"


class Segment(Base, TimestampMixin):
    """Saved segment (filter set) model.
    
    Represents a saved filter configuration that can be applied
    to list views in various modules.
    """
    
    __tablename__ = "segments"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="private",
    )
    
    # Filter configuration stored as JSONB
    filter_groups: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    columns: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    sort_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Display options
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # State flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_smart: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Team/department scoping
    team_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    shares: Mapped[list["SegmentShare"]] = relationship(
        "SegmentShare",
        back_populates="segment",
        cascade="all, delete-orphan",
    )
    usage_records: Mapped[list["SegmentUsage"]] = relationship(
        "SegmentUsage",
        back_populates="segment",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Segment(id={self.id}, name={self.name!r}, module={self.module})>"


class SegmentShare(Base, TimestampMixin):
    """Segment share record model.
    
    Tracks who has access to view or edit shared segments.
    """
    
    __tablename__ = "segment_shares"
    
    segment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shared_with_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    segment: Mapped["Segment"] = relationship(
        "Segment",
        back_populates="shares",
    )
    shared_by: Mapped["User"] = relationship("User", foreign_keys=[shared_by_id])
    shared_with: Mapped["User"] = relationship("User", foreign_keys=[shared_with_id])
    
    def __repr__(self) -> str:
        return f"<SegmentShare(segment={self.segment_id}, with={self.shared_with_id})>"


class SegmentUsage(Base):
    """Segment usage analytics model.
    
    Tracks when segments are used for analytics and
    popular segment recommendations.
    """
    
    __tablename__ = "segment_usage"
    
    segment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    segment: Mapped["Segment"] = relationship(
        "Segment",
        back_populates="usage_records",
    )
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<SegmentUsage(segment={self.segment_id}, user={self.user_id})>"

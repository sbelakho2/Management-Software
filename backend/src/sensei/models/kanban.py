"""
Kanban System models for visual work management.

Implements digital Kanban boards with WIP limits
and pull system signals.
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
    from sensei.models.work_center import WorkCenter
    from sensei.models.work_order import WorkOrder
    from sensei.models.product import Product
    from sensei.models.user import User


class BoardType(enum.Enum):
    """Type of Kanban board."""

    PRODUCTION = "production"
    MATERIAL = "material"
    ENGINEERING = "engineering"
    MAINTENANCE = "maintenance"
    PROJECT = "project"
    IMPROVEMENT = "improvement"


class CardType(enum.Enum):
    """Type of Kanban card."""

    WORK_ORDER = "work_order"
    MATERIAL_REPLENISHMENT = "material_replenishment"
    ENGINEERING_REQUEST = "engineering_request"
    MAINTENANCE_REQUEST = "maintenance_request"
    TASK = "task"
    IMPROVEMENT = "improvement"


class CardStatus(enum.Enum):
    """Status of a Kanban card."""

    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class CardPriority(enum.Enum):
    """Priority level for Kanban cards."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class KanbanBoard(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Digital Kanban board configuration.

    Defines columns, WIP limits, and board settings.
    """

    __tablename__ = "kanban_boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Board identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Board type
    board_type: Mapped[BoardType] = mapped_column(
        Enum(BoardType), nullable=False, default=BoardType.PRODUCTION
    )

    # Work center linkage
    work_center_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_centers.id"), nullable=True, index=True
    )

    # Global WIP limit
    wip_limit_global: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Column configuration (JSON)
    columns_config_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=[
            {"name": "Backlog", "order": 0, "wip_limit": None, "color": "#e0e0e0"},
            {"name": "Ready", "order": 1, "wip_limit": 10, "color": "#bbdefb"},
            {"name": "In Progress", "order": 2, "wip_limit": 5, "color": "#fff9c4"},
            {"name": "Review", "order": 3, "wip_limit": 3, "color": "#c8e6c9"},
            {"name": "Done", "order": 4, "wip_limit": None, "color": "#81c784"},
        ],
    )
    """
    Column config structure:
    [
        {
            "name": "Backlog",
            "order": 0,
            "wip_limit": null,
            "color": "#e0e0e0",
            "is_done_column": false,
            "is_start_column": false
        },
        ...
    ]
    """

    # Swimlane configuration (optional)
    swimlanes_config_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )
    """
    Swimlane config structure:
    [
        {"name": "Expedite", "order": 0, "wip_limit": 1},
        {"name": "Standard", "order": 1, "wip_limit": null},
        {"name": "Low Priority", "order": 2, "wip_limit": null}
    ]
    """

    # Active flag
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    work_center: Mapped[Optional["WorkCenter"]] = relationship(
        "WorkCenter", back_populates="kanban_boards"
    )
    cards: Mapped[list["KanbanCard"]] = relationship(
        "KanbanCard", back_populates="board", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "wip_limit_global IS NULL OR wip_limit_global > 0",
            name="ck_kanban_board_wip_positive",
        ),
    )

    def __repr__(self) -> str:
        return f"<KanbanBoard(id={self.id}, name='{self.name}', type={self.board_type.value})>"

    @property
    def column_names(self) -> list[str]:
        """Get ordered list of column names."""
        sorted_cols = sorted(self.columns_config_json, key=lambda x: x.get("order", 0))
        return [col["name"] for col in sorted_cols]

    @property
    def first_column(self) -> str:
        """Get name of first column."""
        return self.column_names[0] if self.column_names else "Backlog"

    @property
    def last_column(self) -> str:
        """Get name of last column."""
        return self.column_names[-1] if self.column_names else "Done"

    def get_column_wip_limit(self, column_name: str) -> Optional[int]:
        """Get WIP limit for a specific column."""
        for col in self.columns_config_json:
            if col["name"] == column_name:
                return col.get("wip_limit")
        return None

    def get_column_card_count(self, column_name: str) -> int:
        """Count active cards in a column."""
        return sum(
            1 for card in self.cards
            if card.column_name == column_name and card.status == CardStatus.ACTIVE
        )

    def is_column_at_limit(self, column_name: str) -> bool:
        """Check if column is at WIP limit."""
        limit = self.get_column_wip_limit(column_name)
        if limit is None:
            return False
        return self.get_column_card_count(column_name) >= limit

    @property
    def total_active_cards(self) -> int:
        """Count of all active cards on board."""
        return sum(
            1 for card in self.cards if card.status == CardStatus.ACTIVE
        )

    @property
    def is_at_global_limit(self) -> bool:
        """Check if board is at global WIP limit."""
        if self.wip_limit_global is None:
            return False
        return self.total_active_cards >= self.wip_limit_global


class KanbanCard(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Digital Kanban card.

    Represents work items on a Kanban board.
    """

    __tablename__ = "kanban_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Card identification
    card_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Board and position
    board_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kanban_boards.id"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    swimlane_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Card type and classification
    card_type: Mapped[CardType] = mapped_column(
        Enum(CardType), nullable=False, default=CardType.TASK
    )
    priority: Mapped[CardPriority] = mapped_column(
        Enum(CardPriority), nullable=False, default=CardPriority.NORMAL, index=True
    )

    # Status
    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus),
        nullable=False,
        default=CardStatus.ACTIVE,
        index=True,
    )
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Linkages
    work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True, index=True
    )
    product_id: Mapped[Optional[PyUUID]] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )

    # Quantity (for material/production cards)
    quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )

    # Assignment
    assigned_to_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    # Dates
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Cycle time tracking
    cycle_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # When entered first work column
    cycle_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # When entered done column

    # Size/effort estimation
    story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    actual_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True
    )

    # Tags (JSON array of strings)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)

    # WIP limit override (GM approval)
    wip_limit_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    wip_limit_override_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    wip_limit_override_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    board: Mapped["KanbanBoard"] = relationship("KanbanBoard", back_populates="cards")
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="kanban_cards"
    )
    product: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="kanban_cards"
    )
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to_id]
    )
    wip_limit_override_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[wip_limit_override_by_id]
    )
    history: Mapped[list["KanbanCardHistory"]] = relationship(
        "KanbanCardHistory",
        back_populates="card",
        cascade="all, delete-orphan",
        order_by="KanbanCardHistory.changed_at.desc()",
    )

    __table_args__ = (
        UniqueConstraint("board_id", "card_number", name="uq_kanban_card_number"),
        CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_kanban_card_quantity_positive",
        ),
        CheckConstraint(
            "story_points IS NULL OR story_points > 0",
            name="ck_kanban_card_story_points_positive",
        ),
    )

    def __repr__(self) -> str:
        return f"<KanbanCard(id={self.id}, number='{self.card_number}', column='{self.column_name}')>"

    @property
    def is_active(self) -> bool:
        """Check if card is active."""
        return self.status == CardStatus.ACTIVE

    @property
    def is_blocked(self) -> bool:
        """Check if card is blocked."""
        return self.status == CardStatus.BLOCKED

    @property
    def is_completed(self) -> bool:
        """Check if card is completed."""
        return self.status == CardStatus.COMPLETED

    @property
    def is_overdue(self) -> bool:
        """Check if card is overdue."""
        if self.due_date and not self.is_completed:
            return date.today() > self.due_date
        return False

    @property
    def lead_time_days(self) -> Optional[int]:
        """Calculate lead time (created to completed)."""
        if self.completed_at:
            delta = self.completed_at - self.created_at
            return delta.days
        return None

    @property
    def cycle_time_days(self) -> Optional[float]:
        """Calculate cycle time (started to completed)."""
        if self.cycle_started_at and self.cycle_completed_at:
            delta = self.cycle_completed_at - self.cycle_started_at
            return delta.total_seconds() / (24 * 3600)
        return None

    @property
    def age_days(self) -> int:
        """Calculate card age in days."""
        if self.completed_at:
            delta = self.completed_at - self.created_at
        else:
            delta = datetime.now(timezone.utc).replace(tzinfo=None) - self.created_at
        return delta.days

    @property
    def time_in_column_hours(self) -> Optional[float]:
        """Calculate time in current column."""
        # Get last column change from history
        for h in self.history:
            if h.field_name == "column_name":
                delta = datetime.now(timezone.utc).replace(tzinfo=None) - h.changed_at
                return delta.total_seconds() / 3600
        # If no history, use creation time
        delta = datetime.now(timezone.utc).replace(tzinfo=None) - self.created_at
        return delta.total_seconds() / 3600


class KanbanCardHistory(Base, TimestampMixin):
    """
    History of changes to Kanban cards.

    Tracks column moves and other changes for metrics.
    """

    __tablename__ = "kanban_card_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Card reference
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kanban_cards.id"), nullable=False, index=True
    )

    # Change details
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive, index=True
    )
    changed_by_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    card: Mapped["KanbanCard"] = relationship(
        "KanbanCard", back_populates="history"
    )
    changed_by: Mapped["User"] = relationship("User", foreign_keys=[changed_by_id])

    def __repr__(self) -> str:
        return f"<KanbanCardHistory(card_id={self.card_id}, field='{self.field_name}')>"


class KanbanMetrics(Base, TimestampMixin):
    """
    Aggregated Kanban metrics for reporting.

    Captures daily snapshots of board performance.
    """

    __tablename__ = "kanban_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Board and date
    board_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kanban_boards.id"), nullable=False, index=True
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Throughput
    cards_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    story_points_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # WIP
    wip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Cycle time (average for completed cards)
    avg_cycle_time_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    avg_lead_time_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Age
    avg_card_age_days: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    max_card_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Column-level snapshots (JSON)
    column_snapshots: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    """
    Column snapshots structure:
    {
        "Backlog": {"count": 10, "blocked": 0},
        "In Progress": {"count": 5, "blocked": 1},
        ...
    }
    """

    __table_args__ = (
        UniqueConstraint("board_id", "metric_date", name="uq_kanban_metrics_date"),
    )

    def __repr__(self) -> str:
        return f"<KanbanMetrics(board_id={self.board_id}, date={self.metric_date})>"

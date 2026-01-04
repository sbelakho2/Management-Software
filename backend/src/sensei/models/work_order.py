"""
Work Order models for production scheduling and tracking.

Work Orders represent production jobs with their operations
and progress tracking.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.work_center import WorkCenter, Station
    from sensei.models.product import Product, Routing
    from sensei.models.user import User
    from sensei.models.andon import AndonEvent
    from sensei.models.kanban import KanbanCard
    from sensei.models.quality import NonConformance, InspectionRecord


class WorkOrderStatus(enum.Enum):
    """Status of a work order."""

    DRAFT = "draft"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class WorkOrderPriority(enum.Enum):
    """Priority levels for work orders."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class OperationStatus(enum.Enum):
    """Status of a work order operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"


class HoldReason(enum.Enum):
    """Reasons for putting a work order on hold."""

    MATERIAL_SHORTAGE = "material_shortage"
    EQUIPMENT_BREAKDOWN = "equipment_breakdown"
    QUALITY_ISSUE = "quality_issue"
    ENGINEERING_CHANGE = "engineering_change"
    CUSTOMER_REQUEST = "customer_request"
    CAPACITY_CONSTRAINT = "capacity_constraint"
    OTHER = "other"


class WorkOrder(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Production work order for manufacturing a product.

    Tracks quantities, scheduling, and progress through operations.
    """

    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Work order identification
    work_order_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    external_reference: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Customer PO, etc.

    # Product reference
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )

    # Quantities
    quantity_ordered: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
    quantity_completed: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    quantity_scrapped: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    quantity_in_progress: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )

    # Priority and status
    priority: Mapped[WorkOrderPriority] = mapped_column(
        Enum(WorkOrderPriority),
        nullable=False,
        default=WorkOrderPriority.NORMAL,
        index=True,
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus),
        nullable=False,
        default=WorkOrderStatus.DRAFT,
        index=True,
    )

    # Hold information
    hold_reason: Mapped[Optional[HoldReason]] = mapped_column(
        Enum(HoldReason), nullable=True
    )
    hold_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    held_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    held_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Scheduling
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Current location
    work_center_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_centers.id"), nullable=True, index=True
    )
    current_station_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=True, index=True
    )
    current_operation_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Batch/lot tracking
    lot_number: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    batch_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", back_populates="work_orders"
    )
    work_center: Mapped[Optional["WorkCenter"]] = relationship(
        "WorkCenter", back_populates="work_orders"
    )
    current_station: Mapped[Optional["Station"]] = relationship(
        "Station", foreign_keys=[current_station_id]
    )
    held_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[held_by_id]
    )
    operations: Mapped[list["WorkOrderOperation"]] = relationship(
        "WorkOrderOperation",
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderOperation.sequence",
    )
    andon_events: Mapped[list["AndonEvent"]] = relationship(
        "AndonEvent", back_populates="work_order"
    )
    kanban_cards: Mapped[list["KanbanCard"]] = relationship(
        "KanbanCard", back_populates="work_order"
    )
    non_conformances: Mapped[list["NonConformance"]] = relationship(
        "NonConformance", back_populates="work_order"
    )
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(
        "InspectionRecord", back_populates="work_order"
    )

    __table_args__ = (
        CheckConstraint(
            "quantity_ordered > 0", name="ck_wo_quantity_ordered_positive"
        ),
        CheckConstraint(
            "quantity_completed >= 0", name="ck_wo_quantity_completed_nonnegative"
        ),
        CheckConstraint(
            "quantity_scrapped >= 0", name="ck_wo_quantity_scrapped_nonnegative"
        ),
        CheckConstraint(
            "quantity_completed + quantity_scrapped <= quantity_ordered",
            name="ck_wo_quantity_not_exceed_ordered",
        ),
    )

    def __repr__(self) -> str:
        return f"<WorkOrder(id={self.id}, number='{self.work_order_number}', status={self.status.value})>"

    @property
    def quantity_remaining(self) -> Decimal:
        """Calculate remaining quantity to complete."""
        return self.quantity_ordered - self.quantity_completed - self.quantity_scrapped

    @property
    def completion_percentage(self) -> Decimal:
        """Calculate completion percentage."""
        if self.quantity_ordered == 0:
            return Decimal("0")
        return (self.quantity_completed / self.quantity_ordered) * 100

    @property
    def yield_percentage(self) -> Decimal:
        """Calculate yield (good parts / total processed)."""
        total = self.quantity_completed + self.quantity_scrapped
        if total == 0:
            return Decimal("100")
        return (self.quantity_completed / total) * 100

    @property
    def is_late(self) -> bool:
        """Check if work order is late (past scheduled end and not complete)."""
        if self.scheduled_end and self.status not in [
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.CANCELLED,
            WorkOrderStatus.CLOSED,
        ]:
            return datetime.utcnow() > self.scheduled_end
        return False

    @property
    def is_on_hold(self) -> bool:
        """Check if work order is on hold."""
        return self.status == WorkOrderStatus.ON_HOLD

    def can_start(self) -> bool:
        """Check if work order can be started."""
        return self.status == WorkOrderStatus.RELEASED

    def can_complete(self) -> bool:
        """Check if work order can be completed."""
        if self.status != WorkOrderStatus.IN_PROGRESS:
            return False
        # All operations must be completed or skipped
        for op in self.operations:
            if op.status not in [OperationStatus.COMPLETED, OperationStatus.SKIPPED]:
                return False
        return True


class WorkOrderOperation(Base, TimestampMixin, AuditMixin):
    """
    Individual operation within a work order.

    Tracks progress and completion of each routing step.
    """

    __tablename__ = "work_order_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Work order and routing reference
    work_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=False, index=True
    )
    routing_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("routings.id"), nullable=True, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # Operation details (copied from routing for immutability)
    operation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=False, index=True
    )

    # Standard times (copied from routing)
    standard_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    setup_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Status
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus),
        nullable=False,
        default=OperationStatus.PENDING,
        index=True,
    )
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quantities
    quantity_completed: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    quantity_scrapped: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_setup_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Operator assignment
    operator_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship(
        "WorkOrder", back_populates="operations"
    )
    routing: Mapped[Optional["Routing"]] = relationship(
        "Routing", back_populates="work_order_operations"
    )
    station: Mapped["Station"] = relationship(
        "Station", back_populates="work_order_operations"
    )
    operator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[operator_id])

    __table_args__ = (
        UniqueConstraint(
            "work_order_id", "sequence", name="uq_wo_operation_sequence"
        ),
        CheckConstraint("sequence > 0", name="ck_wo_op_sequence_positive"),
        CheckConstraint(
            "quantity_completed >= 0", name="ck_wo_op_qty_completed_nonnegative"
        ),
        CheckConstraint(
            "quantity_scrapped >= 0", name="ck_wo_op_qty_scrapped_nonnegative"
        ),
    )

    def __repr__(self) -> str:
        return f"<WorkOrderOperation(wo_id={self.work_order_id}, seq={self.sequence}, status={self.status.value})>"

    @property
    def efficiency(self) -> Optional[Decimal]:
        """Calculate efficiency (standard time / actual time)."""
        if not self.actual_time_seconds or self.actual_time_seconds == 0:
            return None
        return Decimal(self.standard_time_seconds) / Decimal(self.actual_time_seconds) * 100

    @property
    def elapsed_time_seconds(self) -> Optional[int]:
        """Calculate elapsed time from start to now or completion."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.utcnow()
        return int((end - self.started_at).total_seconds())

    @property
    def is_active(self) -> bool:
        """Check if operation is currently active."""
        return self.status == OperationStatus.IN_PROGRESS

    @property
    def is_blocked(self) -> bool:
        """Check if operation is blocked."""
        return self.status == OperationStatus.BLOCKED

    def can_start(self) -> bool:
        """Check if operation can be started."""
        return self.status == OperationStatus.PENDING

    def can_complete(self) -> bool:
        """Check if operation can be completed."""
        return self.status == OperationStatus.IN_PROGRESS

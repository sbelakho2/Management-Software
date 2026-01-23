"""
Work Center and Station models for production floor management.

Work Centers represent logical production areas containing multiple stations.
Stations are individual work points where operations are performed.
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
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.account import Account
    from sensei.models.user import User
    from sensei.models.standard_work import StandardWork
    from sensei.models.andon import AndonEvent
    from sensei.models.kanban import KanbanBoard
    from sensei.models.work_order import WorkOrder, WorkOrderOperation
    from sensei.models.production import ProductionCell
    from sensei.models.quality import NonConformance, InspectionPlan


class WorkCenterStatus(enum.Enum):
    """Status of a work center."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class StationType(enum.Enum):
    """Type of work station."""

    ASSEMBLY = "assembly"
    MACHINING = "machining"
    INSPECTION = "inspection"
    PACKAGING = "packaging"
    TESTING = "testing"
    REWORK = "rework"
    WELDING = "welding"
    PAINTING = "painting"
    CLEANING = "cleaning"
    MATERIAL_HANDLING = "material_handling"


class StationStatus(enum.Enum):
    """Status of a work station."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    BREAKDOWN = "breakdown"
    CHANGEOVER = "changeover"


class WorkCenter(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Production work center representing a logical production area.

    A work center contains multiple stations and is used for capacity
    planning, scheduling, and performance tracking.
    """

    __tablename__ = "work_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Capacity and efficiency
    capacity_units: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="units/hour"
    )
    capacity_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    efficiency_target: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("85.00")
    )

    # Status
    status: Mapped[WorkCenterStatus] = mapped_column(
        Enum(WorkCenterStatus),
        nullable=False,
        default=WorkCenterStatus.ACTIVE,
        index=True,
    )

    # Foreign keys
    account_id: Mapped[Optional[PyUUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, index=True
    )

    # Relationships
    account: Mapped[Optional["Account"]] = relationship(
        "Account", back_populates="work_centers"
    )
    stations: Mapped[list["Station"]] = relationship(
        "Station", back_populates="work_center", cascade="all, delete-orphan"
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="work_center"
    )
    kanban_boards: Mapped[list["KanbanBoard"]] = relationship(
        "KanbanBoard", back_populates="work_center"
    )
    production_cells: Mapped[list["ProductionCell"]] = relationship(
        "ProductionCell", back_populates="work_center"
    )

    __table_args__ = (
        CheckConstraint(
            "efficiency_target >= 0 AND efficiency_target <= 100",
            name="ck_work_center_efficiency_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<WorkCenter(id={self.id}, code='{self.code}', name='{self.name}')>"

    @property
    def active_stations_count(self) -> int:
        """Count of active stations in this work center."""
        return sum(
            1 for s in self.stations if s.status == StationStatus.ACTIVE
        )

    @property
    def is_operational(self) -> bool:
        """Check if work center is operational."""
        return self.status == WorkCenterStatus.ACTIVE


class Station(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Individual work station within a work center.

    Stations are where actual work operations are performed.
    Each station has defined cycle times and takt times.
    """

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Station type
    station_type: Mapped[StationType] = mapped_column(
        Enum(StationType), nullable=False, default=StationType.ASSEMBLY
    )

    # Time standards (in seconds)
    takt_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    cycle_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    setup_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Status
    status: Mapped[StationStatus] = mapped_column(
        Enum(StationStatus),
        nullable=False,
        default=StationStatus.ACTIVE,
        index=True,
    )

    # Andon SLA configuration (in minutes)
    yellow_ack_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    red_ack_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    resolution_target_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )

    # Foreign keys
    work_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_centers.id"), nullable=False, index=True
    )
    production_cell_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("production_cells.id"), nullable=True, index=True
    )

    # Relationships
    work_center: Mapped["WorkCenter"] = relationship(
        "WorkCenter", back_populates="stations"
    )
    production_cell: Mapped[Optional["ProductionCell"]] = relationship(
        "ProductionCell", back_populates="stations"
    )
    standard_works: Mapped[list["StandardWork"]] = relationship(
        "StandardWork", back_populates="station"
    )
    andon_events: Mapped[list["AndonEvent"]] = relationship(
        "AndonEvent", back_populates="station"
    )
    work_order_operations: Mapped[list["WorkOrderOperation"]] = relationship(
        "WorkOrderOperation", back_populates="station"
    )
    routings: Mapped[list["Routing"]] = relationship(
        "Routing", back_populates="station"
    )
    skill_requirements: Mapped[list["SkillRequirement"]] = relationship(
        "SkillRequirement", back_populates="station"
    )
    non_conformances: Mapped[list["NonConformance"]] = relationship(
        "NonConformance", back_populates="station"
    )
    inspection_plans: Mapped[list["InspectionPlan"]] = relationship(
        "InspectionPlan", back_populates="station"
    )

    __table_args__ = (
        UniqueConstraint(
            "work_center_id", "code", name="uq_station_work_center_code"
        ),
        CheckConstraint("takt_time_seconds > 0", name="ck_station_takt_positive"),
        CheckConstraint("cycle_time_seconds > 0", name="ck_station_cycle_positive"),
        CheckConstraint("setup_time_seconds >= 0", name="ck_station_setup_nonnegative"),
        CheckConstraint(
            "yellow_ack_minutes > 0", name="ck_station_yellow_ack_positive"
        ),
        CheckConstraint("red_ack_minutes > 0", name="ck_station_red_ack_positive"),
    )

    def __repr__(self) -> str:
        return f"<Station(id={self.id}, code='{self.code}', type={self.station_type.value})>"

    @property
    def efficiency_ratio(self) -> Decimal:
        """Calculate efficiency ratio (takt / cycle)."""
        if self.cycle_time_seconds == 0:
            return Decimal("0")
        return Decimal(self.takt_time_seconds) / Decimal(self.cycle_time_seconds)

    @property
    def is_bottleneck(self) -> bool:
        """Check if station is a bottleneck (cycle > takt)."""
        return self.cycle_time_seconds > self.takt_time_seconds

    @property
    def is_available(self) -> bool:
        """Check if station is available for work."""
        return self.status == StationStatus.ACTIVE


# Import at module level to avoid circular imports - these will be defined in other modules
# The TYPE_CHECKING block handles the type hints
from sensei.models.product import Routing
from sensei.models.training import SkillRequirement

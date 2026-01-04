"""
Production Cell models for shop floor organization.

Production cells are logical groupings of stations
with performance tracking.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.work_center import WorkCenter, Station


class CellType(enum.Enum):
    """Type of production cell layout."""

    U_CELL = "u_cell"
    LINE = "line"
    JOB_SHOP = "job_shop"
    BATCH = "batch"
    FLOW = "flow"
    MIXED = "mixed"


class CellStatus(enum.Enum):
    """Status of a production cell."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    RECONFIGURING = "reconfiguring"


class ShiftNumber(enum.Enum):
    """Shift identifiers."""

    SHIFT_1 = "shift_1"
    SHIFT_2 = "shift_2"
    SHIFT_3 = "shift_3"


class ProductionCell(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Production cell - logical grouping of work stations.

    Used for capacity planning and performance tracking.
    """

    __tablename__ = "production_cells"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Cell identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Work center linkage
    work_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("work_centers.id"), nullable=False, index=True
    )

    # Cell configuration
    cell_type: Mapped[CellType] = mapped_column(
        Enum(CellType), nullable=False, default=CellType.U_CELL
    )
    status: Mapped[CellStatus] = mapped_column(
        Enum(CellStatus),
        nullable=False,
        default=CellStatus.ACTIVE,
        index=True,
    )

    # Time standards
    takt_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    target_cycle_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )

    # Capacity
    target_output_per_shift: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    shift_duration_hours: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("8.0")
    )
    planned_efficiency: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("85.00")
    )

    # Current state (updated in real-time)
    current_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_efficiency_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    current_oee_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # Operator staffing
    min_operators: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    standard_operators: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_operators: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_operators: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    work_center: Mapped["WorkCenter"] = relationship(
        "WorkCenter", back_populates="production_cells"
    )
    stations: Mapped[list["Station"]] = relationship(
        "Station", back_populates="production_cell"
    )
    performance_records: Mapped[list["CellPerformance"]] = relationship(
        "CellPerformance",
        back_populates="cell",
        cascade="all, delete-orphan",
        order_by="CellPerformance.shift_date.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "takt_time_seconds > 0",
            name="ck_cell_takt_positive",
        ),
        CheckConstraint(
            "target_output_per_shift >= 0",
            name="ck_cell_target_output_nonnegative",
        ),
        CheckConstraint(
            "min_operators > 0 AND standard_operators >= min_operators AND max_operators >= standard_operators",
            name="ck_cell_operator_range",
        ),
        CheckConstraint(
            "planned_efficiency > 0 AND planned_efficiency <= 100",
            name="ck_cell_efficiency_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<ProductionCell(id={self.id}, code='{self.code}', type={self.cell_type.value})>"

    @property
    def station_count(self) -> int:
        """Number of stations in cell."""
        return len(self.stations)

    @property
    def is_operational(self) -> bool:
        """Check if cell is operational."""
        return self.status == CellStatus.ACTIVE

    @property
    def is_understaffed(self) -> bool:
        """Check if cell is understaffed."""
        return self.current_operators < self.min_operators

    @property
    def output_vs_target_percentage(self) -> Decimal:
        """Calculate output vs target percentage."""
        if self.target_output_per_shift == 0:
            return Decimal("0")
        return (Decimal(self.current_output) / Decimal(self.target_output_per_shift)) * 100

    @property
    def theoretical_capacity_per_shift(self) -> int:
        """Calculate theoretical capacity based on takt time."""
        if self.takt_time_seconds == 0:
            return 0
        shift_seconds = int(self.shift_duration_hours * 3600)
        return int(shift_seconds / self.takt_time_seconds)


class CellPerformance(Base, TimestampMixin, AuditMixin):
    """
    Shift-level performance record for production cells.

    Captures OEE and other metrics per shift.
    """

    __tablename__ = "cell_performances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Cell and shift
    cell_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("production_cells.id"), nullable=False, index=True
    )
    shift_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shift_number: Mapped[ShiftNumber] = mapped_column(
        Enum(ShiftNumber), nullable=False, index=True
    )

    # Output
    planned_output: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_output: Mapped[int] = mapped_column(Integer, nullable=False)
    good_output: Mapped[int] = mapped_column(Integer, nullable=False)
    rework_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scrap_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Time
    planned_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    operating_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    downtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changeover_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Downtime breakdown
    unplanned_downtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    planned_downtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # OEE Components
    availability_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    performance_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    quality_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    oee_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )

    # Efficiency
    efficiency_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )

    # Staffing
    operator_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    labor_hours: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("0")
    )
    units_per_labor_hour: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Issues
    andon_events_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_issues_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issues_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    cell: Mapped["ProductionCell"] = relationship(
        "ProductionCell", back_populates="performance_records"
    )

    __table_args__ = (
        UniqueConstraint(
            "cell_id", "shift_date", "shift_number",
            name="uq_cell_performance_shift"
        ),
        CheckConstraint(
            "actual_output >= 0",
            name="ck_cell_perf_actual_output_nonnegative",
        ),
        CheckConstraint(
            "oee_percentage >= 0 AND oee_percentage <= 100",
            name="ck_cell_perf_oee_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<CellPerformance(cell_id={self.cell_id}, date={self.shift_date}, OEE={self.oee_percentage}%)>"

    @classmethod
    def calculate_oee(
        cls,
        planned_time: int,
        operating_time: int,
        actual_output: int,
        good_output: int,
        ideal_cycle_time_seconds: int,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Calculate OEE components.

        Returns: (availability, performance, quality, oee)
        """
        # Availability = Operating Time / Planned Time
        if planned_time == 0:
            availability = Decimal("0")
        else:
            availability = (Decimal(operating_time) / Decimal(planned_time)) * 100

        # Performance = (Ideal Cycle Time × Actual Output) / Operating Time
        if operating_time == 0:
            performance = Decimal("0")
        else:
            ideal_time = Decimal(ideal_cycle_time_seconds) * Decimal(actual_output)
            operating_seconds = Decimal(operating_time * 60)
            performance = (ideal_time / operating_seconds) * 100

        # Quality = Good Output / Actual Output
        if actual_output == 0:
            quality = Decimal("100")
        else:
            quality = (Decimal(good_output) / Decimal(actual_output)) * 100

        # OEE = Availability × Performance × Quality
        oee = (availability * performance * quality) / Decimal("10000")

        return (
            min(availability, Decimal("100")),
            min(performance, Decimal("100")),
            min(quality, Decimal("100")),
            min(oee, Decimal("100")),
        )

    @property
    def output_target_ratio(self) -> Decimal:
        """Ratio of actual to planned output."""
        if self.planned_output == 0:
            return Decimal("0")
        return (Decimal(self.actual_output) / Decimal(self.planned_output)) * 100

    @property
    def scrap_rate(self) -> Decimal:
        """Scrap rate percentage."""
        if self.actual_output == 0:
            return Decimal("0")
        return (Decimal(self.scrap_output) / Decimal(self.actual_output)) * 100

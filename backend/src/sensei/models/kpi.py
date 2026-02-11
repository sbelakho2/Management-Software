"""
KPI Models — persistent database-backed KPI definitions, values, and dashboards.

Replaces the in-memory dict storage in KPIService with proper ORM tables.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Enums (mirroring the dataclass enums in kpi_metrics.py)
# ---------------------------------------------------------------------------

class KPICategoryDB(str, enum.Enum):
    """KPI category for classification."""
    RFQ = "rfq"
    QUOTING = "quoting"
    PRODUCTION = "production"
    QUALITY = "quality"
    DELIVERY = "delivery"
    FINANCE = "finance"
    CUSTOMER = "customer"
    SAFETY = "safety"
    LEAN = "lean"
    STRATEGIC = "strategic"
    CUSTOM = "custom"


class KPIUnitDB(str, enum.Enum):
    """Unit of measurement for a KPI."""
    PERCENTAGE = "percentage"
    COUNT = "count"
    CURRENCY = "currency"
    HOURS = "hours"
    DAYS = "days"
    RATIO = "ratio"
    SCORE = "score"
    CUSTOM = "custom"


class KPIDirectionDB(str, enum.Enum):
    """Whether higher or lower values are desirable."""
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    TARGET_IS_BEST = "target_is_best"


class KPIStatusDB(str, enum.Enum):
    """Status of a KPI value relative to its target."""
    ON_TARGET = "on_target"
    WARNING = "warning"
    CRITICAL = "critical"
    NO_DATA = "no_data"


# ---------------------------------------------------------------------------
# KPI Definition
# ---------------------------------------------------------------------------

class KPIDefinitionRow(Base, TimestampMixin):
    """Persistent KPI definition."""

    __tablename__ = "kpi_definitions"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[KPICategoryDB] = mapped_column(
        Enum(KPICategoryDB), nullable=False, default=KPICategoryDB.CUSTOM, index=True,
    )
    unit: Mapped[KPIUnitDB] = mapped_column(
        Enum(KPIUnitDB), nullable=False, default=KPIUnitDB.COUNT,
    )
    direction: Mapped[KPIDirectionDB] = mapped_column(
        Enum(KPIDirectionDB), nullable=False, default=KPIDirectionDB.HIGHER_IS_BETTER,
    )

    # Data source config (stored as JSONB for flexibility)
    data_source: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Calculation
    formula: Mapped[str] = mapped_column(Text, nullable=False, default="")
    component_kpis: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    # Threshold config
    threshold_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_warning: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    threshold_critical: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    threshold_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Display
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    display_format: Mapped[str] = mapped_column(String(50), nullable=False, default="")

    # Metadata
    owner_role: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    custom_calculator: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    values: Mapped[list["KPIValueRow"]] = relationship(
        "KPIValueRow", back_populates="definition", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_kpi_definitions_active", "is_active", "category"),
    )


# ---------------------------------------------------------------------------
# KPI Value
# ---------------------------------------------------------------------------

class KPIValueRow(Base, TimestampMixin):
    """A single recorded KPI value at a point in time."""

    __tablename__ = "kpi_values"

    kpi_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("kpi_definitions.id"),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[KPIStatusDB] = mapped_column(
        Enum(KPIStatusDB), nullable=False, default=KPIStatusDB.NO_DATA,
    )

    # Dimensional breakdown (e.g. {"customer_segment": "automotive"})
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relationship
    definition: Mapped[Optional["KPIDefinitionRow"]] = relationship(
        "KPIDefinitionRow",
        back_populates="values",
        foreign_keys=[kpi_id],
        primaryjoin="KPIValueRow.kpi_id == KPIDefinitionRow.id",
    )

    __table_args__ = (
        Index("ix_kpi_values_kpi_ts", "kpi_id", "recorded_at"),
    )


# ---------------------------------------------------------------------------
# KPI Dashboard
# ---------------------------------------------------------------------------

class KPIDashboardRow(Base, TimestampMixin):
    """A dashboard grouping multiple KPIs."""

    __tablename__ = "kpi_dashboards"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    kpi_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    layout: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    default_time_range: Mapped[str] = mapped_column(String(30), nullable=False, default="last_30_days")
    dimension_filters: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

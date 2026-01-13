"""
Analytics Warehouse models.
"""

from datetime import datetime, date
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    Boolean,
    Integer,
    Date,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin


class DailySnapshot(Base, TimestampMixin, AuditMixin):
    """
    Daily snapshot of system state for analytics.
    """
    __tablename__ = "daily_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DimensionSchema(Base, TimestampMixin, AuditMixin):
    """
    Schema definition for an analytics dimension.
    """
    __tablename__ = "analytics_dimension_schemas"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    dim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    key_column: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_columns: Mapped[list] = mapped_column(JSON, nullable=False)


class FactSchema(Base, TimestampMixin, AuditMixin):
    """
    Schema definition for an analytics fact.
    """
    __tablename__ = "analytics_fact_schemas"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension_keys: Mapped[list] = mapped_column(JSON, nullable=False)
    measure_columns: Mapped[list] = mapped_column(JSON, nullable=False)


class ExportedRecord(Base, TimestampMixin):
    """
    A single record exported to the analytics warehouse.
    """
    __tablename__ = "analytics_exported_records"

    snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("daily_snapshots.id", ondelete="CASCADE"), nullable=False)
    fact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    snapshot: Mapped["DailySnapshot"] = relationship("DailySnapshot")

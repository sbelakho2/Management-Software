from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sensei.models.base import Base, TimestampMixin

class ConditionReading(Base):
    """
    Sensor readings for equipment condition monitoring.
    High-volume table intended for partitioning.
    """
    __tablename__ = "condition_readings"
    
    # In partitioned tables, the partition key must be part of the primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, index=True
    )
    
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=False, index=True
    )
    
    # Sensor data
    temperature: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    vibration: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    pressure: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    current: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    noise: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    operating_hours: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    __table_args__ = (
        {"postgresql_partition_by": "RANGE (timestamp)"},
    )

class MaintenanceRecord(Base, TimestampMixin):
    """
    Historical maintenance records for equipment.
    Used for MTBF/MTTR and ML training.
    """
    __tablename__ = "maintenance_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=False, index=True
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False) # repair, breakdown, preventive
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    duration_hours: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

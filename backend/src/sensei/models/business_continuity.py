"""
Business Continuity and Disaster Recovery models.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    Boolean,
    Integer,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin


class QueuedEvent(Base, TimestampMixin):
    """
    Offline event queued for synchronization.
    """
    __tablename__ = "queued_events"

    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    conflict_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    resolution_strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class CriticalityRule(Base, TimestampMixin, AuditMixin):
    """
    Rule defining how to handle conflicts for an entity type.
    """
    __tablename__ = "dr_criticality_rules"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    resolution_strategy: Mapped[str] = mapped_column(String(50), nullable=False)


class RTORPOConfig(Base, TimestampMixin, AuditMixin):
    """
    RTO/RPO targets and validation status.
    """
    __tablename__ = "dr_rto_rpo_configs"

    rto_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    rpo_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


class RestoreRehearsal(Base, TimestampMixin, AuditMixin):
    """
    Record of a restore rehearsal.
    """
    __tablename__ = "dr_restore_rehearsals"

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="scheduled")
    rto_achieved_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rpo_achieved_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

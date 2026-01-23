"""
Andon System models for real-time production issue management.

The Andon system enables workers to signal problems,
triggering the Stop-Call-Wait workflow.
"""

import enum
from datetime import datetime, timezone
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
from sensei.core.time import utcnow_naive
from sensei.core.enums import Severity as AndonSeverity, WorkflowStatus as AndonStatus

if TYPE_CHECKING:
    from sensei.models.work_center import Station
    from sensei.models.product import Product
    from sensei.models.work_order import WorkOrder
    from sensei.models.user import User
    from sensei.models.a3 import A3
    from sensei.models.attachment import Attachment


class AndonType(enum.Enum):
    """Type of Andon event."""

    QUALITY = "quality"
    EQUIPMENT = "equipment"
    MATERIAL = "material"
    SAFETY = "safety"
    PROCESS = "process"
    INFORMATION = "information"
    SUPPORT = "support"


class EscalationLevel(enum.Enum):
    """Escalation level for Andon."""

    NONE = "none"
    LEVEL_1 = "level_1"  # Team lead/supervisor
    LEVEL_2 = "level_2"  # Manager
    LEVEL_3 = "level_3"  # GM/Director


class ResponseStatus(enum.Enum):
    """Response status for escalations."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DELEGATED = "delegated"
    NO_RESPONSE = "no_response"


class AndonEvent(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Andon event record for production issues.

    Implements Stop-Call-Wait workflow with escalation.
    """

    __tablename__ = "andon_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Event identification
    event_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Classification
    andon_type: Mapped[AndonType] = mapped_column(
        Enum(AndonType), nullable=False, index=True
    )
    severity: Mapped[AndonSeverity] = mapped_column(
        Enum(AndonSeverity), nullable=False, default=AndonSeverity.YELLOW, index=True
    )

    # Location and context
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=False, index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )
    work_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True, index=True
    )

    # Issue details
    symptom: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affected_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Photo/evidence
    photo_attachment_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attachments.id"), nullable=True
    )

    # Status tracking
    status: Mapped[AndonStatus] = mapped_column(
        Enum(AndonStatus),
        nullable=False,
        default=AndonStatus.OPEN,
        index=True,
    )
    escalation_level: Mapped[EscalationLevel] = mapped_column(
        Enum(EscalationLevel),
        nullable=False,
        default=EscalationLevel.NONE,
    )

    # Reporting
    reported_by_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive
    )

    # Acknowledgement
    acknowledged_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Resolution
    resolved_by_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # A3 escalation
    escalated_to_a3_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("a3s.id"), nullable=True
    )

    # Impact tracking
    downtime_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_cost_impact: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    # Root cause (quick capture)
    root_cause_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    root_cause_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Recurrence tracking
    is_recurrence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    related_event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("andon_events.id"), nullable=True
    )
    recurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    station: Mapped["Station"] = relationship(
        "Station", back_populates="andon_events"
    )
    product: Mapped[Optional["Product"]] = relationship(
        "Product", back_populates="andon_events"
    )
    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="andon_events"
    )
    photo_attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment", foreign_keys=[photo_attachment_id]
    )
    reported_by: Mapped["User"] = relationship(
        "User", foreign_keys=[reported_by_id]
    )
    acknowledged_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[acknowledged_by_id]
    )
    resolved_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[resolved_by_id]
    )
    escalated_to_a3: Mapped[Optional["A3"]] = relationship(
        "A3", foreign_keys=[escalated_to_a3_id]
    )
    related_event: Mapped[Optional["AndonEvent"]] = relationship(
        "AndonEvent", remote_side=[id], foreign_keys=[related_event_id]
    )
    escalations: Mapped[list["AndonEscalation"]] = relationship(
        "AndonEscalation",
        back_populates="andon_event",
        cascade="all, delete-orphan",
        order_by="AndonEscalation.escalated_at",
    )

    __table_args__ = (
        CheckConstraint(
            "downtime_minutes IS NULL OR downtime_minutes >= 0",
            name="ck_andon_downtime_nonnegative",
        ),
        CheckConstraint(
            "recurrence_count >= 0",
            name="ck_andon_recurrence_nonnegative",
        ),
    )

    def __repr__(self) -> str:
        return f"<AndonEvent(id={self.id}, number='{self.event_number}', severity={self.severity.value})>"

    @property
    def is_open(self) -> bool:
        """Check if Andon is still open."""
        return self.status in [
            AndonStatus.OPEN,
            AndonStatus.ACKNOWLEDGED,
            AndonStatus.IN_PROGRESS,
        ]

    @property
    def is_critical(self) -> bool:
        """Check if this is a critical (red) Andon."""
        return self.severity == AndonSeverity.RED

    @property
    def response_time_minutes(self) -> Optional[int]:
        """Calculate response time (time to acknowledgement)."""
        if self.acknowledged_at:
            delta = self.acknowledged_at - self.reported_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def resolution_time_minutes(self) -> Optional[int]:
        """Calculate total resolution time."""
        if self.resolved_at:
            delta = self.resolved_at - self.reported_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def elapsed_time_minutes(self) -> int:
        """Calculate elapsed time from report to now."""
        end = self.resolved_at or datetime.now(timezone.utc).replace(tzinfo=None)
        delta = end - self.reported_at
        return int(delta.total_seconds() / 60)

    @property
    def needs_escalation(self) -> bool:
        """Check if Andon needs escalation based on elapsed time."""
        if self.status == AndonStatus.RESOLVED:
            return False
        # Check against station SLA
        if hasattr(self, 'station') and self.station:
            if self.severity == AndonSeverity.RED:
                return self.elapsed_time_minutes > self.station.red_ack_minutes
            else:
                return self.elapsed_time_minutes > self.station.yellow_ack_minutes
        return False


class AndonEscalation(Base, TimestampMixin):
    """
    Escalation record for Andon events.

    Tracks each escalation level and response.
    """

    __tablename__ = "andon_escalations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Andon reference
    andon_event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("andon_events.id"), nullable=False, index=True
    )

    # Escalation details
    escalation_level: Mapped[EscalationLevel] = mapped_column(
        Enum(EscalationLevel), nullable=False
    )
    escalated_to_user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow_naive
    )

    # Response tracking
    response_status: Mapped[ResponseStatus] = mapped_column(
        Enum(ResponseStatus),
        nullable=False,
        default=ResponseStatus.PENDING,
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    response_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Delegation
    delegated_to_user_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    andon_event: Mapped["AndonEvent"] = relationship(
        "AndonEvent", back_populates="escalations"
    )
    escalated_to_user: Mapped["User"] = relationship(
        "User", foreign_keys=[escalated_to_user_id]
    )
    delegated_to_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[delegated_to_user_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "andon_event_id", "escalation_level",
            name="uq_andon_escalation_level"
        ),
    )

    def __repr__(self) -> str:
        return f"<AndonEscalation(andon_id={self.andon_event_id}, level={self.escalation_level.value})>"

    @property
    def response_time_minutes(self) -> Optional[int]:
        """Calculate response time for this escalation."""
        if self.responded_at:
            delta = self.responded_at - self.escalated_at
            return int(delta.total_seconds() / 60)
        return None


class AndonRecurrencePattern(Base, TimestampMixin, AuditMixin):
    """
    Tracks patterns of recurring Andon events.

    Used for auto-escalation to A3 on recurrence.
    """

    __tablename__ = "andon_recurrence_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Pattern identification
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=False, index=True
    )
    andon_type: Mapped[AndonType] = mapped_column(
        Enum(AndonType), nullable=False, index=True
    )
    symptom_pattern: Mapped[str] = mapped_column(String(255), nullable=False)

    # Occurrence tracking
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_occurrence_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_occurrence_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    # Escalation threshold
    escalation_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    escalated_to_a3: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    a3_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("a3s.id"), nullable=True
    )

    # Relationships
    station: Mapped["Station"] = relationship("Station")
    a3: Mapped[Optional["A3"]] = relationship("A3")

    __table_args__ = (
        UniqueConstraint(
            "station_id", "andon_type", "symptom_pattern",
            name="uq_andon_recurrence_pattern"
        ),
        CheckConstraint(
            "occurrence_count > 0",
            name="ck_andon_pattern_occurrence_positive",
        ),
        CheckConstraint(
            "escalation_threshold > 0",
            name="ck_andon_pattern_threshold_positive",
        ),
    )

    def __repr__(self) -> str:
        return f"<AndonRecurrencePattern(station={self.station_id}, type={self.andon_type.value})>"

    @property
    def should_escalate(self) -> bool:
        """Check if pattern has reached escalation threshold."""
        return self.occurrence_count >= self.escalation_threshold and not self.escalated_to_a3

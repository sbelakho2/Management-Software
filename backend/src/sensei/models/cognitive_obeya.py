"""
Cognitive Obeya models for AI-driven visual management.
"""

from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sensei.models.base import Base, TimestampMixin
from sensei.core.enums import MetricStatus, MetricCategory, DepartmentType, Severity as AlertSeverity

class MetricRecord(Base, TimestampMixin):
    """Database model for a metric measurement."""
    __tablename__ = "obeya_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[MetricCategory] = mapped_column(Enum(MetricCategory), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    target: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[MetricStatus] = mapped_column(Enum(MetricStatus), nullable=False)

class CausalLinkRecord(Base, TimestampMixin):
    """Database model for a causal relationship."""
    __tablename__ = "obeya_causal_links"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # type: ignore[assignment]
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    impact_value: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="")

class TrendWarningRecord(Base, TimestampMixin):
    """Database model for a predictive trend warning."""
    __tablename__ = "obeya_trend_warnings"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # type: ignore[assignment]
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_status: Mapped[MetricStatus] = mapped_column(Enum(MetricStatus), nullable=False)
    predicted_status: Mapped[MetricStatus] = mapped_column(Enum(MetricStatus), nullable=False)
    days_to_breach: Mapped[int] = mapped_column(Integer, nullable=False)
    trend_values: Mapped[list] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="")

class SiloAlertRecord(Base, TimestampMixin):
    """Database model for a silo-busting alert."""
    __tablename__ = "obeya_silo_alerts"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # type: ignore[assignment]
    source_department: Mapped[DepartmentType] = mapped_column(Enum(DepartmentType), nullable=False)
    affected_department: Mapped[DepartmentType] = mapped_column(Enum(DepartmentType), nullable=False)
    source_event: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_impact: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    owners_notified: Mapped[list] = mapped_column(JSONB, default=list)
    resolution_status: Mapped[str] = mapped_column(String(50), default="open")

class ResourceRebalanceRecord(Base, TimestampMixin):
    """Database model for a resource rebalancing suggestion."""
    __tablename__ = "obeya_rebalance_suggestions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # type: ignore[assignment]
    source_work_center: Mapped[str] = mapped_column(String(100), nullable=False)
    target_work_center: Mapped[str] = mapped_column(String(100), nullable=False)
    operator_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    skill_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_improvement: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

class HeijunkaSuggestionRecord(Base, TimestampMixin):
    """Database model for a Heijunka suggestion."""
    __tablename__ = "obeya_heijunka_suggestions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)  # type: ignore[assignment]
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    current_mix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    suggested_mix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    mura_reduction: Mapped[float] = mapped_column(Float, nullable=False)
    volume_variance_before: Mapped[float] = mapped_column(Float, nullable=False)
    volume_variance_after: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

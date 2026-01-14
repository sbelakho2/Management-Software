"""
TPS (Toyota Production System) models for coaching and gamification.
"""

from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sensei.models.base import Base, TimestampMixin
from sensei.core.enums import WorkflowStatus as AndonStatus, JidokaAction

class PDCACycleRecord(Base, TimestampMixin):
    """Database model for a PDCA cycle."""
    __tablename__ = "tps_pdca_cycles"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    current_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    phase_statuses: Mapped[dict] = mapped_column(JSONB, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)
    team_members: Mapped[list] = mapped_column(JSONB, default=list)
    target_completion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_completion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artifacts: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)

class KataSessionRecord(Base, TimestampMixin):
    """Database model for a Kata session."""
    __tablename__ = "tps_kata_sessions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    challenge: Mapped[str] = mapped_column(Text, nullable=False)
    current_step: Mapped[str] = mapped_column(String(50), nullable=False)
    current_condition: Mapped[str] = mapped_column(Text, nullable=False)
    target_condition: Mapped[str] = mapped_column(Text, default="")
    obstacles: Mapped[list] = mapped_column(JSONB, default=list)
    experiments: Mapped[list] = mapped_column(JSONB, default=list)
    learnings: Mapped[list] = mapped_column(JSONB, default=list)
    coach_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

class MudaDetectionRecord(Base, TimestampMixin):
    """Database model for Muda detection."""
    __tablename__ = "tps_muda_detections"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    muda_type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_impact: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    severity: Mapped[int] = mapped_column(Integer, default=3)
    suggested_countermeasure: Mapped[str] = mapped_column(Text, default="")

class TPSAndonEventRecord(Base, TimestampMixin):
    """Database model for TPS Teacher Andon events."""
    __tablename__ = "tps_andon_events"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AndonStatus] = mapped_column(Enum(AndonStatus), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responder: Mapped[str | None] = mapped_column(String(100), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    countermeasure: Mapped[str | None] = mapped_column(Text, nullable=True)

class JidokaResponseRecord(Base, TimestampMixin):
    """Database model for Jidoka system responses."""
    __tablename__ = "tps_jidoka_responses"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[JidokaAction] = mapped_column(Enum(JidokaAction), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    affected_process: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_impact: Mapped[str] = mapped_column(String(255), nullable=False)

class UserTPSStats(Base, TimestampMixin):
    """Database model for User TPS stats and gamification."""
    __tablename__ = "tps_user_stats"
    
    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    achievements: Mapped[list] = mapped_column(JSONB, default=list)
    belt_level: Mapped[str] = mapped_column(String(50), default="White Belt")

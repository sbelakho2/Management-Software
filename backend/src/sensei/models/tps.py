"""
TPS (Toyota Production System) models for coaching and gamification.
"""

from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sensei.models.base import Base, TimestampMixin

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

class UserTPSStats(Base, TimestampMixin):
    """Database model for User TPS stats and gamification."""
    __tablename__ = "tps_user_stats"
    
    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    achievements: Mapped[list] = mapped_column(JSONB, default=list)
    belt_level: Mapped[str] = mapped_column(String(50), default="White Belt")

"""
Admin models for system configuration and management.
"""

from sqlalchemy import String, Boolean, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sensei.models.base import Base, TimestampMixin

class AdminGate(Base, TimestampMixin):
    """System configuration gate model."""
    __tablename__ = "admin_gates"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phase: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_approvers: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="active") # active, inactive
    order: Mapped[int] = mapped_column(Integer, default=0)
    bypass_roles: Mapped[list] = mapped_column(JSONB, default=list)
    conditions: Mapped[list] = mapped_column(JSONB, default=list)

class ApprovalWorkflow(Base, TimestampMixin):
    """Approval workflow configuration model."""
    __tablename__ = "approval_workflows"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False) # quote, etc.
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    threshold_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    required_roles: Mapped[list] = mapped_column(JSONB, default=list)
    sequence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    timeout_hours: Mapped[int] = mapped_column(Integer, default=24)
    auto_escalate: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_roles: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Template(Base, TimestampMixin):
    """System template model (A3, Obeya, Email, etc.)."""
    __tablename__ = "templates"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False) # a3, obeya, email, report
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    variables: Mapped[list] = mapped_column(JSONB, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

class LearningCadence(Base, TimestampMixin):
    """Learning frequency and requirement model."""
    __tablename__ = "learning_cadences"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), nullable=False) # daily, weekly, monthly, quarterly
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    target_roles: Mapped[list] = mapped_column(JSONB, default=list)
    topics: Mapped[list] = mapped_column(JSONB, default=list)
    reminder_days_before: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class FeatureFlag(Base, TimestampMixin):
    """System feature flag model."""
    __tablename__ = "feature_flags"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=100)
    target_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    requires_restart: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str] = mapped_column(String(50), default="feature") # feature, experiment, killswitch

"""
Strategic Control Plane models for CEO insights and governance.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sensei.models.base import Base, TimestampMixin
from sensei.core.enums import QuerySecurityLevel, EmployeeRiskType

class NL2SQLQueryRecord(Base, TimestampMixin):
    """Database model for a natural language to SQL query."""
    __tablename__ = "strategic_nl2sql_queries"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    natural_language: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    tables_used: Mapped[list] = mapped_column(JSONB, default=list)
    security_level: Mapped[QuerySecurityLevel] = mapped_column(Enum(QuerySecurityLevel), nullable=False)
    executed_by_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

class EmployeeRiskAssessmentRecord(Base, TimestampMixin):
    """Database model for employee risk assessment."""
    __tablename__ = "strategic_employee_risks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    risk_type: Mapped[EmployeeRiskType] = mapped_column(Enum(EmployeeRiskType), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    mitigation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ScenarioResultRecord(Base, TimestampMixin):
    """Database model for production scenario modeling results."""
    __tablename__ = "strategic_scenario_results"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    kpi_impacts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VarianceAlertRecord(Base, TimestampMixin):
    """Database model for COGS/Cost variance alerts."""
    __tablename__ = "strategic_variance_alerts"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    quote_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actual_cogs: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cogs: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_pct: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    work_order_ids: Mapped[list] = mapped_column(JSONB, default=list)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

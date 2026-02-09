from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
    UniqueConstraint,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from sensei.models.base import Base, TimestampMixin, AuditMixin

if TYPE_CHECKING:
    from sensei.models.user import User
    from sensei.models.product import Product


class BOMComponent(Base, TimestampMixin, AuditMixin):
    """
    Bill of Materials component link.
    """
    __tablename__ = "mrp_bom_components"

    parent_product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    component_product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    
    quantity_per: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    scrap_factor: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    parent_product: Mapped["Product"] = relationship("Product", foreign_keys=[parent_product_id])
    component_product: Mapped["Product"] = relationship("Product", foreign_keys=[component_product_id])
    __table_args__ = (UniqueConstraint("parent_product_id", "component_product_id", name="uq_bom_component"),)


class MRPDemand(Base, TimestampMixin, AuditMixin):
    """
    Demand entry for MRP calculation.
    """
    __tablename__ = "mrp_demands"

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    required_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    demand_type: Mapped[str] = mapped_column(String(50), nullable=False) # sales_order, forecast, safety_stock, work_order
    
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g. SO number
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship("Product")


class MRPSuggestion(Base, TimestampMixin, AuditMixin):
    """
    Suggested action from MRP run.
    """
    __tablename__ = "mrp_suggestions"

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    requirement_type: Mapped[str] = mapped_column(String(20), nullable=False) # buy, build
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    needed_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False) # pending, approved, rejected, released, cancelled
    
    source_demands: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])


class MRPRun(Base, TimestampMixin):
    """
    History of MRP runs.
    """
    __tablename__ = "mrp_runs"

    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planning_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    suggestions_count: Mapped[int] = mapped_column(Integer, default=0)
    shortages_count: Mapped[int] = mapped_column(Integer, default=0)
    
    executed_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    executed_by: Mapped["User"] = relationship("User")


class MPSPlan(Base, TimestampMixin, AuditMixin):
    """
    Master Production Schedule plan.
    """
    __tablename__ = "mps_plans"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    lines: Mapped[list["MPSPlanLine"]] = relationship(
        "MPSPlanLine", back_populates="plan", cascade="all, delete-orphan"
    )


class MPSPlanLine(Base, TimestampMixin, AuditMixin):
    """
    MPS bucket line.
    """
    __tablename__ = "mps_plan_lines"

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("mps_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    plan: Mapped["MPSPlan"] = relationship("MPSPlan", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")

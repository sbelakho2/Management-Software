from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.work_center import Station, WorkCenter
    from sensei.models.user import User
    from sensei.models.account import Account


class Asset(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    An asset in the maintenance registry.
    """
    __tablename__ = "maintenance_assets"

    asset_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False) # machine, tooling, gauge, etc.
    status: Mapped[str] = mapped_column(String(50), default="operational", nullable=False)
    criticality: Mapped[str] = mapped_column(String(5), default="B", nullable=False) # A, B, C
    
    location_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    work_center_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("work_centers.id"), nullable=True)
    station_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("stations.id"), nullable=True)
    parent_asset_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=True)
    
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    installation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    warranty_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_life_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    replacement_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    
    meter_reading: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    meter_unit: Mapped[str] = mapped_column(String(20), default="cycles", nullable=False) # cycles, hours, units
    operating_hours: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    
    last_pm_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_pm_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    work_center: Mapped[Optional["WorkCenter"]] = relationship("WorkCenter")
    station: Mapped[Optional["Station"]] = relationship("Station")
    parent_asset: Mapped[Optional["Asset"]] = relationship("Asset", remote_side="Asset.id", backref="child_assets")
    pm_schedules: Mapped[list["PMSchedule"]] = relationship("PMSchedule", back_populates="asset", cascade="all, delete-orphan")
    work_orders: Mapped[list["MaintenanceWorkOrder"]] = relationship("MaintenanceWorkOrder", back_populates="asset", cascade="all, delete-orphan")


class PMSchedule(Base, TimestampMixin, AuditMixin):
    """
    A preventive maintenance schedule.
    """
    __tablename__ = "pm_schedules"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    frequency_type: Mapped[str] = mapped_column(String(20), default="calendar", nullable=False) # calendar, meter, usage
    frequency_value: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    frequency_unit: Mapped[str] = mapped_column(String(20), default="days", nullable=False) # days, weeks, months, cycles, hours
    
    estimated_duration_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("1"), nullable=False)
    work_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    checklist_items: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    required_skills: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    safety_requirements: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    spare_parts_required: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    
    last_completed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_due: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="pm_schedules")


class MaintenanceWorkOrder(Base, TimestampMixin, AuditMixin):
    """
    A maintenance work order.
    """
    __tablename__ = "maintenance_work_orders"

    work_order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    work_order_type: Mapped[str] = mapped_column(String(20), nullable=False) # preventive, corrective, predictive, emergency, project
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, open, in_progress, on_hold, completed, cancelled
    
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False) # 1-10
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pm_schedule_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("pm_schedules.id"), nullable=True)
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    actual_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    checklist_completed: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    approval_status: Mapped[str] = mapped_column(String(20), default="not_required", nullable=False) # not_required, pending, approved, rejected
    approval_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="work_orders")
    pm_schedule: Mapped[Optional["PMSchedule"]] = relationship("PMSchedule")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    labor_entries: Mapped[list["MaintenanceLaborEntry"]] = relationship("MaintenanceLaborEntry", back_populates="work_order", cascade="all, delete-orphan")
    parts_used: Mapped[list["MaintenancePartUsed"]] = relationship("MaintenancePartUsed", back_populates="work_order", cascade="all, delete-orphan")


class MaintenanceLaborEntry(Base, TimestampMixin):
    """
    Labor recorded against a work order.
    """
    __tablename__ = "maintenance_labor_entries"

    work_order_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    technician_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    work_order: Mapped["MaintenanceWorkOrder"] = relationship("MaintenanceWorkOrder", back_populates="labor_entries")
    technician: Mapped["User"] = relationship("User")


class MaintenancePartUsed(Base, TimestampMixin):
    """
    Spare parts used in a work order.
    """
    __tablename__ = "maintenance_parts_used"

    work_order_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    part_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_spare_parts.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    work_order: Mapped["MaintenanceWorkOrder"] = relationship("MaintenanceWorkOrder", overlaps="parts_used")
    part: Mapped["SparePart"] = relationship("SparePart")


class SparePart(Base, TimestampMixin, AuditMixin):
    """
    A spare part for maintenance.
    """
    __tablename__ = "maintenance_spare_parts"

    part_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    max_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    location_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    vendor_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    last_ordered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    vendor: Mapped[Optional["Account"]] = relationship("Account")


class DowntimeEvent(Base, TimestampMixin):
    """
    A downtime event for OEE tracking.
    """
    __tablename__ = "maintenance_downtime_events"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False) # breakdown, changeover, planned_maintenance, etc.
    reason_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_work_orders.id"), nullable=True)
    recorded_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispute_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship("Asset")
    work_order: Mapped[Optional["MaintenanceWorkOrder"]] = relationship("MaintenanceWorkOrder")
    recorded_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[recorded_by_id])
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_id])


class FailureRecord(Base, TimestampMixin):
    """
    A failure record for MTBF/MTTR calculation.
    """
    __tablename__ = "maintenance_failure_records"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    failure_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    repair_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    time_to_repair_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    time_between_failures_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    
    failure_mode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_work_orders.id"), nullable=True)

    asset: Mapped["Asset"] = relationship("Asset")
    work_order: Mapped[Optional["MaintenanceWorkOrder"]] = relationship("MaintenanceWorkOrder")


class ConditionReading(Base):
    """
    Sensor readings for equipment condition monitoring.
    High-volume table intended for partitioning.
    """
    __tablename__ = "condition_readings"
    
    # In partitioned tables, the partition key must be part of the primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # type: ignore[assignment]
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
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
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


class LOTOProcedure(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Lockout/Tagout (LOTO) procedure for an asset.
    """
    __tablename__ = "maintenance_loto_procedures"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, inactive
    requires_verification: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    asset: Mapped["Asset"] = relationship("Asset")
    energy_sources: Mapped[list["LOTOEnergySource"]] = relationship(
        "LOTOEnergySource", back_populates="procedure", cascade="all, delete-orphan"
    )
    locks: Mapped[list["LOTOLock"]] = relationship(
        "LOTOLock", back_populates="procedure", cascade="all, delete-orphan"
    )


class LOTOEnergySource(Base, TimestampMixin):
    """
    Energy isolation points for a LOTO procedure.
    """
    __tablename__ = "maintenance_loto_energy_sources"

    procedure_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_loto_procedures.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False) # electric, hydraulic, pneumatic, mechanical, thermal, chemical, other
    isolation_point: Mapped[str] = mapped_column(String(255), nullable=False)
    lock_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_steps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    procedure: Mapped["LOTOProcedure"] = relationship("LOTOProcedure", back_populates="energy_sources")


class LOTOLock(Base, TimestampMixin, AuditMixin):
    """
    Active or historical LOTO lock record.
    """
    __tablename__ = "maintenance_loto_locks"

    procedure_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_loto_procedures.id"), nullable=False, index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_work_orders.id"), nullable=True, index=True)

    lock_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, released, cancelled, expired
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    applied_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    verification_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    procedure: Mapped["LOTOProcedure"] = relationship("LOTOProcedure", back_populates="locks")
    asset: Mapped["Asset"] = relationship("Asset")
    work_order: Mapped[Optional["MaintenanceWorkOrder"]] = relationship("MaintenanceWorkOrder")
    applied_by: Mapped["User"] = relationship("User", foreign_keys=[applied_by_id])
    released_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[released_by_id])
    verified_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by_id])


class ToolItem(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Tool crib inventory item.
    """
    __tablename__ = "maintenance_tool_items"

    tool_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False) # available, checked_out, maintenance, retired
    location_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    min_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    life_limit_cycles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    life_used_cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calibration_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    checkouts: Mapped[list["ToolCheckout"]] = relationship(
        "ToolCheckout", back_populates="tool", cascade="all, delete-orphan"
    )


class ToolCheckout(Base, TimestampMixin, AuditMixin):
    """
    Tool checkout/return record.
    """
    __tablename__ = "maintenance_tool_checkouts"

    tool_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_tool_items.id"), nullable=False, index=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_work_orders.id"), nullable=True, index=True)
    checked_out_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    checked_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    condition_out: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    condition_in: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tool: Mapped["ToolItem"] = relationship("ToolItem", back_populates="checkouts")
    work_order: Mapped[Optional["MaintenanceWorkOrder"]] = relationship("MaintenanceWorkOrder")
    checked_out_by: Mapped["User"] = relationship("User", foreign_keys=[checked_out_by_id])
    returned_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[returned_by_id])


class AssetWarranty(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Warranty coverage for a maintenance asset.
    """
    __tablename__ = "maintenance_asset_warranties"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    warranty_type: Mapped[str] = mapped_column(String(50), nullable=False) # manufacturer, extended, service
    provider_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vendor_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(50), default="parts_labor", nullable=False) # parts, labor, parts_labor, full
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, expired, void
    terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claim_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    asset: Mapped["Asset"] = relationship("Asset")
    vendor: Mapped[Optional["Account"]] = relationship("Account")
    claims: Mapped[list["WarrantyClaim"]] = relationship(
        "WarrantyClaim", back_populates="warranty", cascade="all, delete-orphan"
    )


class WarrantyClaim(Base, TimestampMixin, AuditMixin):
    """
    Warranty claim for an asset warranty.
    """
    __tablename__ = "maintenance_warranty_claims"

    warranty_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_asset_warranties.id"), nullable=False, index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_work_orders.id"), nullable=True, index=True)

    claim_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="submitted", nullable=False) # submitted, approved, denied, reimbursed, closed
    claim_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    approved_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    warranty: Mapped["AssetWarranty"] = relationship("AssetWarranty", back_populates="claims")
    asset: Mapped["Asset"] = relationship("Asset")
    work_order: Mapped[Optional["MaintenanceWorkOrder"]] = relationship("MaintenanceWorkOrder")


class FieldReturn(Base, TimestampMixin, AuditMixin):
    """
    Field return / warranty analysis record.
    """
    __tablename__ = "maintenance_field_returns"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("maintenance_assets.id"), nullable=False, index=True)
    warranty_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_asset_warranties.id"), nullable=True)
    claim_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("maintenance_warranty_claims.id"), nullable=True)
    customer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)

    return_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False) # received, investigating, analyzed, closed
    failure_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    defect_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    failure_mode: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost_impact: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship("Asset")
    warranty: Mapped[Optional["AssetWarranty"]] = relationship("AssetWarranty")
    claim: Mapped[Optional["WarrantyClaim"]] = relationship("WarrantyClaim")
    customer: Mapped[Optional["Account"]] = relationship("Account")


class MaintenanceBudget(Base, TimestampMixin, AuditMixin):
    """
    Maintenance budget tracking by period.
    """
    __tablename__ = "maintenance_budgets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    variance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="MAD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

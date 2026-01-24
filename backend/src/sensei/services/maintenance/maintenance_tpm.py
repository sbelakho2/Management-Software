"""
Maintenance & Asset Reliability (TPM Layer) Service.

Provides:
- Asset Register with Parent-Child relationships
- Criticality ranking (A/B/C) and risk-based maintenance
- Preventive Maintenance (PM) scheduling
- MTBF/MTTR calculations
- Downtime tracking and OEE computations
- Spare parts management
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from decimal import Decimal
import logging
import statistics

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class AssetType(str, Enum):
    """Types of assets."""
    MACHINE = "machine"
    TOOLING = "tooling"
    GAUGE = "gauge"
    FIXTURE = "fixture"
    JIG = "jig"
    CONVEYOR = "conveyor"
    ROBOT = "robot"
    CNC = "cnc"
    PRESS = "press"
    OVEN = "oven"
    TEST_EQUIPMENT = "test_equipment"
    UTILITY = "utility"


class AssetStatus(str, Enum):
    """Asset operational status."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    UNDER_MAINTENANCE = "under_maintenance"
    DECOMMISSIONED = "decommissioned"
    IN_STORAGE = "in_storage"


class Criticality(str, Enum):
    """Asset criticality ranking."""
    A = "A"  # Critical - immediate impact on production
    B = "B"  # Important - can affect production within hours
    C = "C"  # Low - backup available or minimal impact


class PMFrequencyType(str, Enum):
    """PM frequency types."""
    CALENDAR = "calendar"  # Time-based (days, weeks, months)
    METER = "meter"  # Cycle/meter-based
    USAGE = "usage"  # Hours of operation


class PMStatus(str, Enum):
    """PM task status."""
    SCHEDULED = "scheduled"
    OVERDUE = "overdue"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkOrderType(str, Enum):
    """Maintenance work order types."""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    PREDICTIVE = "predictive"
    EMERGENCY = "emergency"
    PROJECT = "project"


class WorkOrderStatus(str, Enum):
    """Work order status."""
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DowntimeCategory(str, Enum):
    """Downtime categories for Pareto analysis."""
    BREAKDOWN = "breakdown"
    CHANGEOVER = "changeover"
    PLANNED_MAINTENANCE = "planned_maintenance"
    UNPLANNED_MAINTENANCE = "unplanned_maintenance"
    IDLING = "idling"
    MINOR_STOPS = "minor_stops"
    QUALITY_LOSS = "quality_loss"
    MATERIAL_SHORTAGE = "material_shortage"
    OPERATOR_UNAVAILABLE = "operator_unavailable"
    OTHER = "other"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class Asset:
    """An asset in the maintenance registry."""
    id: str
    asset_number: str
    name: str
    asset_type: AssetType
    status: AssetStatus = AssetStatus.OPERATIONAL
    criticality: Criticality = Criticality.B
    location_id: str | None = None
    work_center_id: str | None = None
    parent_asset_id: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    purchase_date: datetime | None = None
    installation_date: datetime | None = None
    warranty_expiry: datetime | None = None
    expected_life_years: int | None = None
    replacement_cost: Decimal | None = None
    meter_reading: Decimal = Decimal("0")
    meter_unit: str = "cycles"  # cycles, hours, units
    operating_hours: Decimal = Decimal("0")
    last_pm_date: datetime | None = None
    next_pm_date: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PMSchedule:
    """A preventive maintenance schedule."""
    id: str
    asset_id: str
    name: str
    description: str | None = None
    frequency_type: PMFrequencyType = PMFrequencyType.CALENDAR
    frequency_value: int = 30  # Days, cycles, or hours
    frequency_unit: str = "days"  # days, weeks, months, cycles, hours
    estimated_duration_hours: Decimal = Decimal("1")
    work_instructions: str | None = None
    checklist_items: list[dict[str, Any]] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    safety_requirements: list[str] = field(default_factory=list)
    spare_parts: list[dict[str, Any]] = field(default_factory=list)
    last_completed: datetime | None = None
    next_due: datetime | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MaintenanceWorkOrder:
    """A maintenance work order."""
    id: str
    work_order_number: str
    asset_id: str
    work_order_type: WorkOrderType
    status: WorkOrderStatus = WorkOrderStatus.DRAFT
    priority: int = 5  # 1-10, higher = more urgent
    description: str | None = None
    pm_schedule_id: str | None = None
    assigned_to: str | None = None
    estimated_hours: Decimal = Decimal("0")
    actual_hours: Decimal = Decimal("0")
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    checklist_completed: list[dict[str, Any]] = field(default_factory=list)
    parts_used: list[dict[str, Any]] = field(default_factory=list)
    labor_entries: list[dict[str, Any]] = field(default_factory=list)
    findings: str | None = None
    root_cause: str | None = None
    corrective_action: str | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DowntimeEvent:
    """A downtime event for OEE tracking."""
    id: str
    asset_id: str
    category: DowntimeCategory
    reason_code: str | None = None
    description: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    duration_minutes: Decimal = Decimal("0")
    work_order_id: str | None = None
    shift_id: str | None = None
    recorded_by: str | None = None
    verified: bool = False
    verified_by: str | None = None
    disputed: bool = False
    dispute_reason: str | None = None


@dataclass
class OEEMetrics:
    """OEE metrics for a time period."""
    asset_id: str
    period_start: datetime
    period_end: datetime
    planned_production_time: Decimal = Decimal("0")  # Minutes
    actual_run_time: Decimal = Decimal("0")  # Minutes
    total_count: int = 0
    good_count: int = 0
    defect_count: int = 0
    ideal_cycle_time: Decimal = Decimal("0")  # Minutes per unit
    availability: Decimal = Decimal("0")  # %
    performance: Decimal = Decimal("0")  # %
    quality: Decimal = Decimal("0")  # %
    oee: Decimal = Decimal("0")  # %


@dataclass
class SparePart:
    """A spare part for maintenance."""
    id: str
    part_number: str
    name: str
    description: str | None = None
    quantity_on_hand: Decimal = Decimal("0")
    min_quantity: Decimal = Decimal("0")
    max_quantity: Decimal = Decimal("0")
    reorder_point: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    location_id: str | None = None
    lead_time_days: int = 0
    applicable_assets: list[str] = field(default_factory=list)
    vendor_id: str | None = None
    last_ordered: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FailureRecord:
    """A failure record for MTBF/MTTR calculation."""
    id: str
    asset_id: str
    failure_date: datetime
    repair_date: datetime | None = None
    time_to_repair_hours: Decimal | None = None
    time_between_failures_hours: Decimal | None = None
    failure_mode: str | None = None
    root_cause: str | None = None
    work_order_id: str | None = None


# =============================================================================
# MAINTENANCE SERVICE
# =============================================================================


class MaintenanceService:
    """
    Maintenance & Asset Reliability (TPM Layer) Service.
    
    Provides:
    - Asset registry management
    - PM scheduling and execution
    - Downtime tracking
    - OEE calculations
    - MTBF/MTTR metrics
    - Spare parts management
    """
    
    def __init__(self):
        # Storage
        self._assets: dict[str, Asset] = {}
        self._pm_schedules: dict[str, PMSchedule] = {}
        self._work_orders: dict[str, MaintenanceWorkOrder] = {}
        self._downtime_events: list[DowntimeEvent] = []
        self._spare_parts: dict[str, SparePart] = {}
        self._failure_records: list[FailureRecord] = []
        
        # Sequences
        self._asset_sequence: int = 1
        self._wo_sequence: int = 1
    
    # =========================================================================
    # ASSET MANAGEMENT
    # =========================================================================
    
    def create_asset(
        self,
        name: str,
        asset_type: AssetType,
        asset_number: str | None = None,
        criticality: Criticality = Criticality.B,
        location_id: str | None = None,
        work_center_id: str | None = None,
        parent_asset_id: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        serial_number: str | None = None,
        purchase_date: datetime | None = None,
        installation_date: datetime | None = None,
        warranty_expiry: datetime | None = None,
        expected_life_years: int | None = None,
        replacement_cost: Decimal | None = None,
    ) -> Asset:
        """Create a new asset."""
        asset_id = str(uuid4())
        
        if not asset_number:
            asset_number = f"AST-{str(self._asset_sequence).zfill(5)}"
            self._asset_sequence += 1
        
        asset = Asset(
            id=asset_id,
            asset_number=asset_number,
            name=name,
            asset_type=asset_type,
            criticality=criticality,
            location_id=location_id,
            work_center_id=work_center_id,
            parent_asset_id=parent_asset_id,
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            purchase_date=purchase_date,
            installation_date=installation_date,
            warranty_expiry=warranty_expiry,
            expected_life_years=expected_life_years,
            replacement_cost=replacement_cost,
        )
        
        self._assets[asset_id] = asset
        logger.info(f"Created asset: {asset_number} - {name}")
        return asset
    
    def get_asset(self, asset_id: str) -> Asset | None:
        """Get an asset by ID."""
        return self._assets.get(asset_id)
    
    def get_asset_by_number(self, asset_number: str) -> Asset | None:
        """Get an asset by asset number."""
        for asset in self._assets.values():
            if asset.asset_number == asset_number:
                return asset
        return None
    
    def get_assets(
        self,
        asset_type: AssetType | None = None,
        criticality: Criticality | None = None,
        status: AssetStatus | None = None,
        location_id: str | None = None,
        work_center_id: str | None = None,
    ) -> list[Asset]:
        """Get assets with optional filtering."""
        assets = list(self._assets.values())
        
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        
        if criticality:
            assets = [a for a in assets if a.criticality == criticality]
        
        if status:
            assets = [a for a in assets if a.status == status]
        
        if location_id:
            assets = [a for a in assets if a.location_id == location_id]
        
        if work_center_id:
            assets = [a for a in assets if a.work_center_id == work_center_id]
        
        return assets
    
    def get_child_assets(self, parent_asset_id: str) -> list[Asset]:
        """Get all child assets of a parent."""
        return [a for a in self._assets.values() if a.parent_asset_id == parent_asset_id]
    
    def update_asset_status(
        self,
        asset_id: str,
        status: AssetStatus,
        reason: str | None = None,
    ) -> Asset | None:
        """Update asset status."""
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        
        old_status = asset.status
        asset.status = status
        asset.updated_at = datetime.now(timezone.utc)
        
        # Auto-record downtime when going to DOWN status
        if status == AssetStatus.DOWN and old_status == AssetStatus.OPERATIONAL:
            self.record_downtime_start(
                asset_id=asset_id,
                category=DowntimeCategory.BREAKDOWN,
                description=reason,
            )
        
        return asset
    
    def update_meter_reading(
        self,
        asset_id: str,
        reading: Decimal,
    ) -> Asset | None:
        """Update asset meter reading."""
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        
        asset.meter_reading = reading
        asset.updated_at = datetime.now(timezone.utc)
        
        # Check if any PM is due based on meter
        self._check_meter_based_pm(asset)
        
        return asset
    
    def update_operating_hours(
        self,
        asset_id: str,
        hours: Decimal,
    ) -> Asset | None:
        """Update asset operating hours."""
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        
        asset.operating_hours = hours
        asset.updated_at = datetime.now(timezone.utc)
        
        return asset
    
    def _check_meter_based_pm(self, asset: Asset) -> None:
        """Check and trigger meter-based PMs."""
        schedules = [s for s in self._pm_schedules.values() 
                    if s.asset_id == asset.id and 
                    s.frequency_type == PMFrequencyType.METER and
                    s.is_active]
        
        for schedule in schedules:
            if schedule.last_completed:
                # Calculate next due based on last meter reading
                # This is simplified - real implementation would track meter at last PM
                pass
    
    # =========================================================================
    # PM SCHEDULE MANAGEMENT
    # =========================================================================
    
    def create_pm_schedule(
        self,
        asset_id: str,
        name: str,
        frequency_type: PMFrequencyType,
        frequency_value: int,
        frequency_unit: str = "days",
        description: str | None = None,
        estimated_duration_hours: Decimal = Decimal("1"),
        work_instructions: str | None = None,
        checklist_items: list[dict[str, Any]] | None = None,
        required_skills: list[str] | None = None,
        safety_requirements: list[str] | None = None,
        spare_parts: list[dict[str, Any]] | None = None,
    ) -> PMSchedule:
        """Create a PM schedule for an asset."""
        schedule_id = str(uuid4())
        
        # Calculate first due date
        now = datetime.now(timezone.utc)
        if frequency_type == PMFrequencyType.CALENDAR:
            if frequency_unit == "days":
                next_due = now + timedelta(days=frequency_value)
            elif frequency_unit == "weeks":
                next_due = now + timedelta(weeks=frequency_value)
            elif frequency_unit == "months":
                next_due = now + timedelta(days=frequency_value * 30)
            else:
                next_due = now + timedelta(days=frequency_value)
        else:
            next_due = None  # Meter/usage-based - no calendar due date
        
        schedule = PMSchedule(
            id=schedule_id,
            asset_id=asset_id,
            name=name,
            description=description,
            frequency_type=frequency_type,
            frequency_value=frequency_value,
            frequency_unit=frequency_unit,
            estimated_duration_hours=estimated_duration_hours,
            work_instructions=work_instructions,
            checklist_items=checklist_items or [],
            required_skills=required_skills or [],
            safety_requirements=safety_requirements or [],
            spare_parts=spare_parts or [],
            next_due=next_due,
        )
        
        self._pm_schedules[schedule_id] = schedule
        
        # Update asset next PM date
        asset = self._assets.get(asset_id)
        if asset and next_due:
            if not asset.next_pm_date or next_due < asset.next_pm_date:
                asset.next_pm_date = next_due
        
        logger.info(f"Created PM schedule: {name} for asset {asset_id}")
        return schedule
    
    def get_pm_schedule(self, schedule_id: str) -> PMSchedule | None:
        """Get a PM schedule by ID."""
        return self._pm_schedules.get(schedule_id)
    
    def get_pm_schedules(
        self,
        asset_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[PMSchedule]:
        """Get PM schedules with optional filtering."""
        schedules = list(self._pm_schedules.values())
        
        if asset_id:
            schedules = [s for s in schedules if s.asset_id == asset_id]
        
        if is_active is not None:
            schedules = [s for s in schedules if s.is_active == is_active]
        
        return schedules
    
    def get_overdue_pms(self) -> list[PMSchedule]:
        """Get all overdue PM schedules."""
        now = datetime.now(timezone.utc)
        return [
            s for s in self._pm_schedules.values()
            if s.is_active and s.next_due and s.next_due < now
        ]
    
    def get_upcoming_pms(self, days_ahead: int = 7) -> list[PMSchedule]:
        """Get PMs due within the specified days."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days_ahead)
        
        return [
            s for s in self._pm_schedules.values()
            if s.is_active and s.next_due and now <= s.next_due <= future
        ]
    
    def complete_pm(
        self,
        schedule_id: str,
        completed_by: str,
        actual_duration_hours: Decimal,
        findings: str | None = None,
    ) -> PMSchedule | None:
        """Mark a PM as completed and reschedule."""
        schedule = self._pm_schedules.get(schedule_id)
        if not schedule:
            return None
        
        now = datetime.now(timezone.utc)
        schedule.last_completed = now
        
        # Calculate next due date
        if schedule.frequency_type == PMFrequencyType.CALENDAR:
            if schedule.frequency_unit == "days":
                schedule.next_due = now + timedelta(days=schedule.frequency_value)
            elif schedule.frequency_unit == "weeks":
                schedule.next_due = now + timedelta(weeks=schedule.frequency_value)
            elif schedule.frequency_unit == "months":
                schedule.next_due = now + timedelta(days=schedule.frequency_value * 30)
        
        # Update asset
        asset = self._assets.get(schedule.asset_id)
        if asset:
            asset.last_pm_date = now
            asset.next_pm_date = schedule.next_due
        
        return schedule
    
    # =========================================================================
    # WORK ORDER MANAGEMENT
    # =========================================================================
    
    def create_work_order(
        self,
        asset_id: str,
        work_order_type: WorkOrderType,
        description: str | None = None,
        priority: int = 5,
        pm_schedule_id: str | None = None,
        assigned_to: str | None = None,
        estimated_hours: Decimal = Decimal("0"),
        scheduled_start: datetime | None = None,
        scheduled_end: datetime | None = None,
        created_by: str | None = None,
    ) -> MaintenanceWorkOrder:
        """Create a maintenance work order."""
        wo_id = str(uuid4())
        wo_number = f"MWO-{str(self._wo_sequence).zfill(6)}"
        self._wo_sequence += 1
        
        work_order = MaintenanceWorkOrder(
            id=wo_id,
            work_order_number=wo_number,
            asset_id=asset_id,
            work_order_type=work_order_type,
            priority=priority,
            description=description,
            pm_schedule_id=pm_schedule_id,
            assigned_to=assigned_to,
            estimated_hours=estimated_hours,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            created_by=created_by,
        )
        
        self._work_orders[wo_id] = work_order
        logger.info(f"Created work order: {wo_number}")
        return work_order
    
    def create_pm_work_order(self, pm_schedule_id: str) -> MaintenanceWorkOrder | None:
        """Create a work order from a PM schedule."""
        schedule = self._pm_schedules.get(pm_schedule_id)
        if not schedule:
            return None
        
        return self.create_work_order(
            asset_id=schedule.asset_id,
            work_order_type=WorkOrderType.PREVENTIVE,
            description=schedule.description or f"PM: {schedule.name}",
            pm_schedule_id=pm_schedule_id,
            estimated_hours=schedule.estimated_duration_hours,
        )
    
    def get_work_order(self, wo_id: str) -> MaintenanceWorkOrder | None:
        """Get a work order by ID."""
        return self._work_orders.get(wo_id)
    
    def get_work_orders(
        self,
        asset_id: str | None = None,
        status: WorkOrderStatus | None = None,
        work_order_type: WorkOrderType | None = None,
        assigned_to: str | None = None,
    ) -> list[MaintenanceWorkOrder]:
        """Get work orders with optional filtering."""
        work_orders = list(self._work_orders.values())
        
        if asset_id:
            work_orders = [w for w in work_orders if w.asset_id == asset_id]
        
        if status:
            work_orders = [w for w in work_orders if w.status == status]
        
        if work_order_type:
            work_orders = [w for w in work_orders if w.work_order_type == work_order_type]
        
        if assigned_to:
            work_orders = [w for w in work_orders if w.assigned_to == assigned_to]
        
        return work_orders
    
    def update_work_order_status(
        self,
        wo_id: str,
        status: WorkOrderStatus,
    ) -> MaintenanceWorkOrder | None:
        """Update work order status."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            return None
        
        now = datetime.now(timezone.utc)
        
        if status == WorkOrderStatus.IN_PROGRESS and not wo.actual_start:
            wo.actual_start = now
            # Update asset status
            asset = self._assets.get(wo.asset_id)
            if asset:
                asset.status = AssetStatus.UNDER_MAINTENANCE
        
        elif status == WorkOrderStatus.COMPLETED:
            wo.actual_end = now
            # Calculate actual hours
            if wo.actual_start:
                duration = (now - wo.actual_start).total_seconds() / 3600
                wo.actual_hours = Decimal(str(round(duration, 2)))
            
            # Complete PM if linked
            if wo.pm_schedule_id:
                self.complete_pm(
                    wo.pm_schedule_id,
                    completed_by=wo.assigned_to or "system",
                    actual_duration_hours=wo.actual_hours,
                    findings=wo.findings,
                )
            
            # Update asset status
            asset = self._assets.get(wo.asset_id)
            if asset:
                asset.status = AssetStatus.OPERATIONAL
        
        wo.status = status
        wo.updated_at = now
        
        return wo
    
    def add_labor_entry(
        self,
        wo_id: str,
        technician_id: str,
        hours: Decimal,
        description: str | None = None,
    ) -> MaintenanceWorkOrder | None:
        """Add a labor entry to a work order."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            return None
        
        entry = {
            "technician_id": technician_id,
            "hours": float(hours),
            "description": description,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        
        wo.labor_entries.append(entry)
        wo.updated_at = datetime.now(timezone.utc)
        
        return wo
    
    def add_parts_used(
        self,
        wo_id: str,
        part_id: str,
        quantity: Decimal,
    ) -> MaintenanceWorkOrder | None:
        """Add parts used to a work order."""
        wo = self._work_orders.get(wo_id)
        if not wo:
            return None
        
        entry = {
            "part_id": part_id,
            "quantity": float(quantity),
            "used_at": datetime.now(timezone.utc).isoformat(),
        }
        
        wo.parts_used.append(entry)
        wo.updated_at = datetime.now(timezone.utc)
        
        # Update spare part inventory
        spare_part = self._spare_parts.get(part_id)
        if spare_part:
            spare_part.quantity_on_hand -= quantity
        
        return wo
    
    # =========================================================================
    # DOWNTIME & OEE
    # =========================================================================
    
    def record_downtime_start(
        self,
        asset_id: str,
        category: DowntimeCategory,
        reason_code: str | None = None,
        description: str | None = None,
        recorded_by: str | None = None,
    ) -> DowntimeEvent:
        """Record the start of a downtime event."""
        event = DowntimeEvent(
            id=str(uuid4()),
            asset_id=asset_id,
            category=category,
            reason_code=reason_code,
            description=description,
            recorded_by=recorded_by,
        )
        
        self._downtime_events.append(event)
        
        # Update asset status
        asset = self._assets.get(asset_id)
        if asset and category == DowntimeCategory.BREAKDOWN:
            asset.status = AssetStatus.DOWN
        
        return event
    
    def record_downtime_end(
        self,
        event_id: str,
        work_order_id: str | None = None,
    ) -> DowntimeEvent | None:
        """Record the end of a downtime event."""
        event = None
        for e in self._downtime_events:
            if e.id == event_id:
                event = e
                break
        
        if not event:
            return None
        
        now = datetime.now(timezone.utc)
        event.end_time = now
        event.duration_minutes = Decimal(str(
            (now - event.start_time).total_seconds() / 60
        ))
        event.work_order_id = work_order_id
        
        # Record failure for MTBF
        if event.category == DowntimeCategory.BREAKDOWN:
            self._record_failure(event)
        
        # Update asset status
        asset = self._assets.get(event.asset_id)
        if asset:
            asset.status = AssetStatus.OPERATIONAL
        
        return event
    
    def _record_failure(self, downtime_event: DowntimeEvent) -> None:
        """Record a failure for MTBF calculation."""
        asset_id = downtime_event.asset_id
        
        # Find previous failure for this asset
        previous_failures = [
            f for f in self._failure_records
            if f.asset_id == asset_id
        ]
        previous_failures.sort(key=lambda f: f.failure_date, reverse=True)
        
        tbf_hours = None
        if previous_failures:
            last_failure = previous_failures[0]
            if last_failure.repair_date:
                time_between = (downtime_event.start_time - last_failure.repair_date)
                tbf_hours = Decimal(str(time_between.total_seconds() / 3600))
        
        ttr_hours = None
        if downtime_event.end_time:
            repair_time = (downtime_event.end_time - downtime_event.start_time)
            ttr_hours = Decimal(str(repair_time.total_seconds() / 3600))
        
        failure = FailureRecord(
            id=str(uuid4()),
            asset_id=asset_id,
            failure_date=downtime_event.start_time,
            repair_date=downtime_event.end_time,
            time_to_repair_hours=ttr_hours,
            time_between_failures_hours=tbf_hours,
            failure_mode=downtime_event.reason_code,
            root_cause=downtime_event.description,
            work_order_id=downtime_event.work_order_id,
        )
        
        self._failure_records.append(failure)
    
    def get_downtime_events(
        self,
        asset_id: str | None = None,
        category: DowntimeCategory | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[DowntimeEvent]:
        """Get downtime events with optional filtering."""
        events = self._downtime_events
        
        if asset_id:
            events = [e for e in events if e.asset_id == asset_id]
        
        if category:
            events = [e for e in events if e.category == category]
        
        if start_date:
            events = [e for e in events if e.start_time >= start_date]
        
        if end_date:
            events = [e for e in events if e.start_time <= end_date]
        
        return events
    
    def verify_downtime(
        self,
        event_id: str,
        verified_by: str,
        corrected_category: DowntimeCategory | None = None,
        corrected_duration: Decimal | None = None,
    ) -> DowntimeEvent | None:
        """Verify/audit a downtime entry."""
        event = None
        for e in self._downtime_events:
            if e.id == event_id:
                event = e
                break
        
        if not event:
            return None
        
        event.verified = True
        event.verified_by = verified_by
        
        if corrected_category:
            event.category = corrected_category
        
        if corrected_duration is not None:
            event.duration_minutes = corrected_duration
        
        return event
    
    def dispute_downtime(
        self,
        event_id: str,
        reason: str,
    ) -> DowntimeEvent | None:
        """Mark a downtime entry as disputed."""
        event = None
        for e in self._downtime_events:
            if e.id == event_id:
                event = e
                break
        
        if not event:
            return None
        
        event.disputed = True
        event.dispute_reason = reason
        
        return event
    
    def calculate_oee(
        self,
        asset_id: str,
        period_start: datetime,
        period_end: datetime,
        planned_production_time: Decimal,
        ideal_cycle_time: Decimal,
        total_count: int,
        good_count: int,
    ) -> OEEMetrics:
        """Calculate OEE for an asset over a time period."""
        # Get downtime for period
        downtime_events = self.get_downtime_events(
            asset_id=asset_id,
            start_date=period_start,
            end_date=period_end,
        )
        
        total_downtime = sum(
            float(e.duration_minutes) for e in downtime_events
            if e.end_time is not None
        )
        
        # Availability = (Planned Time - Downtime) / Planned Time
        run_time = float(planned_production_time) - total_downtime
        if float(planned_production_time) > 0:
            availability = Decimal(str(run_time / float(planned_production_time) * 100))
        else:
            availability = Decimal("0")
        
        # Performance = (Ideal Cycle Time × Total Count) / Run Time
        if run_time > 0:
            theoretical_time = float(ideal_cycle_time) * total_count
            performance = Decimal(str(theoretical_time / run_time * 100))
        else:
            performance = Decimal("0")
        
        # Quality = Good Count / Total Count
        if total_count > 0:
            quality = Decimal(str(good_count / total_count * 100))
        else:
            quality = Decimal("0")
        
        # OEE = Availability × Performance × Quality
        oee = (availability * performance * quality) / Decimal("10000")
        
        return OEEMetrics(
            asset_id=asset_id,
            period_start=period_start,
            period_end=period_end,
            planned_production_time=planned_production_time,
            actual_run_time=Decimal(str(run_time)),
            total_count=total_count,
            good_count=good_count,
            defect_count=total_count - good_count,
            ideal_cycle_time=ideal_cycle_time,
            availability=availability.quantize(Decimal("0.01")),
            performance=min(performance, Decimal("100")).quantize(Decimal("0.01")),
            quality=quality.quantize(Decimal("0.01")),
            oee=oee.quantize(Decimal("0.01")),
        )
    
    # =========================================================================
    # MTBF / MTTR
    # =========================================================================
    
    def calculate_mtbf(self, asset_id: str) -> Decimal | None:
        """Calculate Mean Time Between Failures for an asset."""
        failures = [
            f for f in self._failure_records
            if f.asset_id == asset_id and f.time_between_failures_hours is not None
        ]
        
        if not failures:
            return None
        
        tbf_values = [float(f.time_between_failures_hours) for f in failures if f.time_between_failures_hours is not None]
        if not tbf_values:
            return None
        mtbf = statistics.mean(tbf_values)
        
        return Decimal(str(round(mtbf, 2)))
    
    def calculate_mttr(self, asset_id: str) -> Decimal | None:
        """Calculate Mean Time To Repair for an asset."""
        failures = [
            f for f in self._failure_records
            if f.asset_id == asset_id and f.time_to_repair_hours is not None
        ]
        
        if not failures:
            return None
        
        ttr_values = [float(f.time_to_repair_hours) for f in failures if f.time_to_repair_hours is not None]
        if not ttr_values:
            return None
        mttr = statistics.mean(ttr_values)
        
        return Decimal(str(round(mttr, 2)))
    
    def get_asset_reliability_metrics(self, asset_id: str) -> dict[str, Any]:
        """Get comprehensive reliability metrics for an asset."""
        asset = self._assets.get(asset_id)
        if not asset:
            return {"error": "Asset not found"}
        
        mtbf = self.calculate_mtbf(asset_id)
        mttr = self.calculate_mttr(asset_id)
        
        # Calculate availability from MTBF and MTTR
        availability = None
        if mtbf is not None and mttr is not None and (mtbf + mttr) > 0:
            availability = Decimal(str(float(mtbf) / (float(mtbf) + float(mttr)) * 100))
        
        failure_count = len([
            f for f in self._failure_records
            if f.asset_id == asset_id
        ])
        
        return {
            "asset_id": asset_id,
            "asset_number": asset.asset_number,
            "mtbf_hours": float(mtbf) if mtbf else None,
            "mttr_hours": float(mttr) if mttr else None,
            "calculated_availability": float(availability.quantize(Decimal("0.01"))) if availability else None,
            "failure_count": failure_count,
            "operating_hours": float(asset.operating_hours),
            "last_pm_date": asset.last_pm_date.isoformat() if asset.last_pm_date else None,
            "next_pm_date": asset.next_pm_date.isoformat() if asset.next_pm_date else None,
        }
    
    # =========================================================================
    # SPARE PARTS MANAGEMENT
    # =========================================================================
    
    def create_spare_part(
        self,
        part_number: str,
        name: str,
        description: str | None = None,
        min_quantity: Decimal = Decimal("0"),
        max_quantity: Decimal = Decimal("0"),
        reorder_point: Decimal = Decimal("0"),
        unit_cost: Decimal = Decimal("0"),
        location_id: str | None = None,
        lead_time_days: int = 0,
        applicable_assets: list[str] | None = None,
        vendor_id: str | None = None,
    ) -> SparePart:
        """Create a spare part record."""
        part_id = str(uuid4())
        
        part = SparePart(
            id=part_id,
            part_number=part_number,
            name=name,
            description=description,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            reorder_point=reorder_point,
            unit_cost=unit_cost,
            location_id=location_id,
            lead_time_days=lead_time_days,
            applicable_assets=applicable_assets or [],
            vendor_id=vendor_id,
        )
        
        self._spare_parts[part_id] = part
        return part
    
    def get_spare_part(self, part_id: str) -> SparePart | None:
        """Get a spare part by ID."""
        return self._spare_parts.get(part_id)
    
    def get_spare_parts(
        self,
        below_reorder: bool = False,
        for_asset_id: str | None = None,
    ) -> list[SparePart]:
        """Get spare parts with optional filtering."""
        parts = list(self._spare_parts.values())
        
        if below_reorder:
            parts = [p for p in parts if p.quantity_on_hand <= p.reorder_point]
        
        if for_asset_id:
            parts = [p for p in parts if for_asset_id in p.applicable_assets]
        
        return parts
    
    def adjust_spare_part_quantity(
        self,
        part_id: str,
        quantity_change: Decimal,
        reason: str | None = None,
    ) -> SparePart | None:
        """Adjust spare part quantity."""
        part = self._spare_parts.get(part_id)
        if not part:
            return None
        
        part.quantity_on_hand += quantity_change
        return part
    
    def reserve_parts_for_pm(
        self,
        pm_schedule_id: str,
    ) -> list[dict[str, Any]]:
        """Reserve spare parts for an upcoming PM."""
        schedule = self._pm_schedules.get(pm_schedule_id)
        if not schedule:
            return []
        
        reservations = []
        for part_info in schedule.spare_parts:
            part_id = part_info.get("part_id")
            if part_id is None:
                continue
            part_id_str = str(part_id)
            quantity = Decimal(str(part_info.get("quantity", 0)))
            
            part = self._spare_parts.get(part_id_str)
            if part and part.quantity_on_hand >= quantity:
                reservations.append({
                    "part_id": part_id,
                    "part_number": part.part_number,
                    "quantity_reserved": float(quantity),
                    "available": True,
                })
            else:
                reservations.append({
                    "part_id": part_id,
                    "quantity_needed": float(quantity),
                    "quantity_available": float(part.quantity_on_hand) if part else 0,
                    "available": False,
                })
        
        return reservations
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> dict[str, Any]:
        """Get maintenance statistics."""
        assets = list(self._assets.values())
        work_orders = list(self._work_orders.values())
        
        return {
            "total_assets": len(assets),
            "assets_by_status": {
                status.value: len([a for a in assets if a.status == status])
                for status in AssetStatus
            },
            "assets_by_criticality": {
                crit.value: len([a for a in assets if a.criticality == crit])
                for crit in Criticality
            },
            "total_pm_schedules": len(self._pm_schedules),
            "active_pm_schedules": len([s for s in self._pm_schedules.values() if s.is_active]),
            "overdue_pms": len(self.get_overdue_pms()),
            "total_work_orders": len(work_orders),
            "work_orders_by_status": {
                status.value: len([w for w in work_orders if w.status == status])
                for status in WorkOrderStatus
            },
            "total_downtime_events": len(self._downtime_events),
            "total_spare_parts": len(self._spare_parts),
            "parts_below_reorder": len(self.get_spare_parts(below_reorder=True)),
        }


# =============================================================================
# SINGLETON
# =============================================================================


_maintenance_service: MaintenanceService | None = None


def get_maintenance_service() -> MaintenanceService:
    """Get the maintenance service singleton."""
    global _maintenance_service
    if _maintenance_service is None:
        _maintenance_service = MaintenanceService()
    return _maintenance_service


def create_maintenance_service() -> MaintenanceService:
    """Factory function to create a Maintenance service (for testing)."""
    return MaintenanceService()

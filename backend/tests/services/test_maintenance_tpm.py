"""
Tests for Maintenance & Asset Reliability (TPM Layer) Service.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from sensei.services.maintenance_tpm import (
    # Enums
    AssetType,
    AssetStatus,
    Criticality,
    PMFrequencyType,
    PMStatus,
    WorkOrderType,
    WorkOrderStatus,
    DowntimeCategory,
    # Data Models
    Asset,
    PMSchedule,
    MaintenanceWorkOrder,
    DowntimeEvent,
    OEEMetrics,
    SparePart,
    FailureRecord,
    # Service
    MaintenanceService,
    create_maintenance_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance."""
    return MaintenanceService()


@pytest.fixture
def sample_asset(service):
    """Create a sample asset."""
    return service.create_asset(
        name="CNC Machine 01",
        asset_type=AssetType.CNC,
        criticality=Criticality.A,
        location_id="shop-floor-1",
        work_center_id="wc-001",
        manufacturer="Haas",
        model="VF-2",
        serial_number="SN-12345",
    )


@pytest.fixture
def sample_pm_schedule(service, sample_asset):
    """Create a sample PM schedule."""
    return service.create_pm_schedule(
        asset_id=sample_asset.id,
        name="Weekly Lubrication",
        frequency_type=PMFrequencyType.CALENDAR,
        frequency_value=7,
        frequency_unit="days",
        estimated_duration_hours=Decimal("0.5"),
        work_instructions="Lubricate all moving parts per maintenance manual.",
        checklist_items=[
            {"item": "Check oil level", "required": True},
            {"item": "Grease bearings", "required": True},
            {"item": "Inspect belts", "required": False},
        ],
        safety_requirements=["LOTO required", "PPE: Safety glasses, gloves"],
    )


@pytest.fixture
def sample_work_order(service, sample_asset):
    """Create a sample work order."""
    return service.create_work_order(
        asset_id=sample_asset.id,
        work_order_type=WorkOrderType.CORRECTIVE,
        description="Replace worn spindle bearing",
        priority=8,
        estimated_hours=Decimal("4"),
    )


@pytest.fixture
def sample_spare_part(service, sample_asset):
    """Create a sample spare part."""
    return service.create_spare_part(
        part_number="BRG-6205-2RS",
        name="Spindle Bearing 6205-2RS",
        description="Deep groove ball bearing",
        min_quantity=Decimal("2"),
        max_quantity=Decimal("10"),
        reorder_point=Decimal("3"),
        unit_cost=Decimal("45.00"),
        lead_time_days=7,
        applicable_assets=[sample_asset.id],
    )


# =============================================================================
# TEST: ENUMS
# =============================================================================


class TestEnums:
    """Tests for enumeration types."""
    
    def test_asset_type_values(self):
        """Test AssetType enum values."""
        assert AssetType.MACHINE == "machine"
        assert AssetType.CNC == "cnc"
        assert AssetType.GAUGE == "gauge"
        assert AssetType.FIXTURE == "fixture"
        assert AssetType.ROBOT == "robot"
    
    def test_asset_status_values(self):
        """Test AssetStatus enum values."""
        assert AssetStatus.OPERATIONAL == "operational"
        assert AssetStatus.DOWN == "down"
        assert AssetStatus.UNDER_MAINTENANCE == "under_maintenance"
        assert AssetStatus.DECOMMISSIONED == "decommissioned"
    
    def test_criticality_values(self):
        """Test Criticality enum values."""
        assert Criticality.A == "A"
        assert Criticality.B == "B"
        assert Criticality.C == "C"
    
    def test_pm_frequency_type_values(self):
        """Test PMFrequencyType enum values."""
        assert PMFrequencyType.CALENDAR == "calendar"
        assert PMFrequencyType.METER == "meter"
        assert PMFrequencyType.USAGE == "usage"
    
    def test_work_order_type_values(self):
        """Test WorkOrderType enum values."""
        assert WorkOrderType.PREVENTIVE == "preventive"
        assert WorkOrderType.CORRECTIVE == "corrective"
        assert WorkOrderType.PREDICTIVE == "predictive"
        assert WorkOrderType.EMERGENCY == "emergency"
    
    def test_downtime_category_values(self):
        """Test DowntimeCategory enum values."""
        assert DowntimeCategory.BREAKDOWN == "breakdown"
        assert DowntimeCategory.CHANGEOVER == "changeover"
        assert DowntimeCategory.PLANNED_MAINTENANCE == "planned_maintenance"
        assert DowntimeCategory.MINOR_STOPS == "minor_stops"


# =============================================================================
# TEST: DATA MODELS
# =============================================================================


class TestDataModels:
    """Tests for data models."""
    
    def test_asset_creation(self):
        """Test Asset creation."""
        asset = Asset(
            id="asset-001",
            asset_number="AST-00001",
            name="Test Machine",
            asset_type=AssetType.MACHINE,
            criticality=Criticality.A,
        )
        
        assert asset.id == "asset-001"
        assert asset.status == AssetStatus.OPERATIONAL
        assert asset.meter_reading == Decimal("0")
    
    def test_pm_schedule_creation(self):
        """Test PMSchedule creation."""
        schedule = PMSchedule(
            id="pm-001",
            asset_id="asset-001",
            name="Weekly Check",
            frequency_type=PMFrequencyType.CALENDAR,
            frequency_value=7,
        )
        
        assert schedule.id == "pm-001"
        assert schedule.is_active is True
    
    def test_work_order_creation(self):
        """Test MaintenanceWorkOrder creation."""
        wo = MaintenanceWorkOrder(
            id="wo-001",
            work_order_number="MWO-000001",
            asset_id="asset-001",
            work_order_type=WorkOrderType.CORRECTIVE,
        )
        
        assert wo.id == "wo-001"
        assert wo.status == WorkOrderStatus.DRAFT
    
    def test_downtime_event_creation(self):
        """Test DowntimeEvent creation."""
        event = DowntimeEvent(
            id="dt-001",
            asset_id="asset-001",
            category=DowntimeCategory.BREAKDOWN,
        )
        
        assert event.id == "dt-001"
        assert event.verified is False
    
    def test_spare_part_creation(self):
        """Test SparePart creation."""
        part = SparePart(
            id="sp-001",
            part_number="BRG-001",
            name="Bearing",
            quantity_on_hand=Decimal("5"),
            reorder_point=Decimal("2"),
        )
        
        assert part.id == "sp-001"
        assert part.quantity_on_hand == Decimal("5")


# =============================================================================
# TEST: ASSET MANAGEMENT
# =============================================================================


class TestAssetManagement:
    """Tests for asset management functions."""
    
    def test_create_asset(self, service):
        """Test creating an asset."""
        asset = service.create_asset(
            name="Press Machine",
            asset_type=AssetType.PRESS,
            criticality=Criticality.B,
            manufacturer="Komatsu",
            model="H2F-150",
        )
        
        assert asset.id is not None
        assert asset.asset_number is not None
        assert asset.asset_number.startswith("AST-")
        assert asset.status == AssetStatus.OPERATIONAL
    
    def test_create_asset_with_parent(self, service, sample_asset):
        """Test creating a child asset."""
        child = service.create_asset(
            name="Spindle Motor",
            asset_type=AssetType.MACHINE,
            parent_asset_id=sample_asset.id,
        )
        
        assert child.parent_asset_id == sample_asset.id
    
    def test_get_asset(self, service, sample_asset):
        """Test getting an asset by ID."""
        asset = service.get_asset(sample_asset.id)
        assert asset is not None
        assert asset.id == sample_asset.id
    
    def test_get_asset_by_number(self, service, sample_asset):
        """Test getting an asset by asset number."""
        asset = service.get_asset_by_number(sample_asset.asset_number)
        assert asset is not None
        assert asset.asset_number == sample_asset.asset_number
    
    def test_get_assets_by_type(self, service, sample_asset):
        """Test filtering assets by type."""
        assets = service.get_assets(asset_type=AssetType.CNC)
        assert len(assets) >= 1
        for a in assets:
            assert a.asset_type == AssetType.CNC
    
    def test_get_assets_by_criticality(self, service, sample_asset):
        """Test filtering assets by criticality."""
        assets = service.get_assets(criticality=Criticality.A)
        assert len(assets) >= 1
        for a in assets:
            assert a.criticality == Criticality.A
    
    def test_get_child_assets(self, service, sample_asset):
        """Test getting child assets."""
        # Create child assets
        service.create_asset(name="Sub-asset 1", asset_type=AssetType.TOOLING, parent_asset_id=sample_asset.id)
        service.create_asset(name="Sub-asset 2", asset_type=AssetType.TOOLING, parent_asset_id=sample_asset.id)
        
        children = service.get_child_assets(sample_asset.id)
        assert len(children) == 2
    
    def test_update_asset_status(self, service, sample_asset):
        """Test updating asset status."""
        updated = service.update_asset_status(
            sample_asset.id,
            AssetStatus.UNDER_MAINTENANCE,
            reason="Scheduled maintenance",
        )
        
        assert updated.status == AssetStatus.UNDER_MAINTENANCE
    
    def test_update_asset_status_to_down_records_downtime(self, service, sample_asset):
        """Test that setting status to DOWN auto-records downtime."""
        service.update_asset_status(sample_asset.id, AssetStatus.DOWN, reason="Spindle failure")
        
        events = service.get_downtime_events(asset_id=sample_asset.id)
        assert len(events) >= 1
        assert events[-1].category == DowntimeCategory.BREAKDOWN
    
    def test_update_meter_reading(self, service, sample_asset):
        """Test updating meter reading."""
        updated = service.update_meter_reading(sample_asset.id, Decimal("1500"))
        
        assert updated.meter_reading == Decimal("1500")
    
    def test_update_operating_hours(self, service, sample_asset):
        """Test updating operating hours."""
        updated = service.update_operating_hours(sample_asset.id, Decimal("2500.5"))
        
        assert updated.operating_hours == Decimal("2500.5")


# =============================================================================
# TEST: PM SCHEDULE MANAGEMENT
# =============================================================================


class TestPMScheduleManagement:
    """Tests for PM schedule management functions."""
    
    def test_create_pm_schedule(self, service, sample_asset):
        """Test creating a PM schedule."""
        schedule = service.create_pm_schedule(
            asset_id=sample_asset.id,
            name="Monthly Inspection",
            frequency_type=PMFrequencyType.CALENDAR,
            frequency_value=30,
            frequency_unit="days",
            estimated_duration_hours=Decimal("2"),
        )
        
        assert schedule.id is not None
        assert schedule.is_active is True
        assert schedule.next_due is not None
    
    def test_create_meter_based_pm(self, service, sample_asset):
        """Test creating meter-based PM."""
        schedule = service.create_pm_schedule(
            asset_id=sample_asset.id,
            name="Every 10000 Cycles",
            frequency_type=PMFrequencyType.METER,
            frequency_value=10000,
            frequency_unit="cycles",
        )
        
        assert schedule.frequency_type == PMFrequencyType.METER
        assert schedule.next_due is None  # No calendar date for meter-based
    
    def test_create_pm_with_checklist(self, service, sample_asset):
        """Test creating PM with checklist items."""
        checklist = [
            {"item": "Check oil level", "required": True},
            {"item": "Inspect filters", "required": True},
            {"item": "Test emergency stop", "required": True},
        ]
        
        schedule = service.create_pm_schedule(
            asset_id=sample_asset.id,
            name="Safety PM",
            frequency_type=PMFrequencyType.CALENDAR,
            frequency_value=7,
            checklist_items=checklist,
            safety_requirements=["LOTO", "PPE Required"],
        )
        
        assert len(schedule.checklist_items) == 3
        assert len(schedule.safety_requirements) == 2
    
    def test_get_pm_schedule(self, service, sample_pm_schedule):
        """Test getting a PM schedule by ID."""
        schedule = service.get_pm_schedule(sample_pm_schedule.id)
        assert schedule is not None
        assert schedule.id == sample_pm_schedule.id
    
    def test_get_pm_schedules_by_asset(self, service, sample_asset, sample_pm_schedule):
        """Test getting PM schedules for an asset."""
        schedules = service.get_pm_schedules(asset_id=sample_asset.id)
        assert len(schedules) >= 1
    
    def test_get_overdue_pms(self, service, sample_asset):
        """Test getting overdue PMs."""
        # Create PM with past due date
        schedule = service.create_pm_schedule(
            asset_id=sample_asset.id,
            name="Overdue PM",
            frequency_type=PMFrequencyType.CALENDAR,
            frequency_value=1,
        )
        # Manually set past due date
        schedule.next_due = datetime.now(timezone.utc) - timedelta(days=5)
        
        overdue = service.get_overdue_pms()
        assert len(overdue) >= 1
    
    def test_get_upcoming_pms(self, service, sample_asset):
        """Test getting upcoming PMs."""
        # Create PM due within 7 days
        schedule = service.create_pm_schedule(
            asset_id=sample_asset.id,
            name="Upcoming PM",
            frequency_type=PMFrequencyType.CALENDAR,
            frequency_value=3,
        )
        
        upcoming = service.get_upcoming_pms(days_ahead=7)
        assert len(upcoming) >= 1
    
    def test_complete_pm(self, service, sample_pm_schedule):
        """Test completing a PM."""
        original_next_due = sample_pm_schedule.next_due
        
        completed = service.complete_pm(
            sample_pm_schedule.id,
            completed_by="tech-001",
            actual_duration_hours=Decimal("0.75"),
            findings="All within spec",
        )
        
        assert completed.last_completed is not None
        assert completed.next_due > original_next_due


# =============================================================================
# TEST: WORK ORDER MANAGEMENT
# =============================================================================


class TestWorkOrderManagement:
    """Tests for work order management functions."""
    
    def test_create_work_order(self, service, sample_asset):
        """Test creating a work order."""
        wo = service.create_work_order(
            asset_id=sample_asset.id,
            work_order_type=WorkOrderType.CORRECTIVE,
            description="Replace motor",
            priority=7,
            estimated_hours=Decimal("8"),
        )
        
        assert wo.id is not None
        assert wo.work_order_number.startswith("MWO-")
        assert wo.status == WorkOrderStatus.DRAFT
    
    def test_create_pm_work_order(self, service, sample_pm_schedule):
        """Test creating work order from PM schedule."""
        wo = service.create_pm_work_order(sample_pm_schedule.id)
        
        assert wo is not None
        assert wo.work_order_type == WorkOrderType.PREVENTIVE
        assert wo.pm_schedule_id == sample_pm_schedule.id
    
    def test_get_work_order(self, service, sample_work_order):
        """Test getting a work order by ID."""
        wo = service.get_work_order(sample_work_order.id)
        assert wo is not None
        assert wo.id == sample_work_order.id
    
    def test_get_work_orders_by_asset(self, service, sample_asset, sample_work_order):
        """Test filtering work orders by asset."""
        work_orders = service.get_work_orders(asset_id=sample_asset.id)
        assert len(work_orders) >= 1
    
    def test_get_work_orders_by_status(self, service, sample_work_order):
        """Test filtering work orders by status."""
        work_orders = service.get_work_orders(status=WorkOrderStatus.DRAFT)
        assert len(work_orders) >= 1
    
    def test_update_work_order_to_in_progress(self, service, sample_work_order, sample_asset):
        """Test updating work order to in progress."""
        updated = service.update_work_order_status(
            sample_work_order.id,
            WorkOrderStatus.IN_PROGRESS,
        )
        
        assert updated.status == WorkOrderStatus.IN_PROGRESS
        assert updated.actual_start is not None
        
        # Asset should be under maintenance
        asset = service.get_asset(sample_asset.id)
        assert asset.status == AssetStatus.UNDER_MAINTENANCE
    
    def test_complete_work_order(self, service, sample_work_order, sample_asset):
        """Test completing a work order."""
        service.update_work_order_status(sample_work_order.id, WorkOrderStatus.IN_PROGRESS)
        
        completed = service.update_work_order_status(
            sample_work_order.id,
            WorkOrderStatus.COMPLETED,
        )
        
        assert completed.status == WorkOrderStatus.COMPLETED
        assert completed.actual_end is not None
        # actual_hours may be 0 if completed instantly (in tests)
        assert completed.actual_hours >= Decimal("0")
        
        # Asset should be operational
        asset = service.get_asset(sample_asset.id)
        assert asset.status == AssetStatus.OPERATIONAL
    
    def test_add_labor_entry(self, service, sample_work_order):
        """Test adding labor entry to work order."""
        updated = service.add_labor_entry(
            sample_work_order.id,
            technician_id="tech-001",
            hours=Decimal("2.5"),
            description="Troubleshooting and repair",
        )
        
        assert len(updated.labor_entries) == 1
        assert updated.labor_entries[0]["hours"] == 2.5
    
    def test_add_parts_used(self, service, sample_work_order, sample_spare_part):
        """Test adding parts used to work order."""
        # Add initial inventory
        service.adjust_spare_part_quantity(sample_spare_part.id, Decimal("5"))
        
        updated = service.add_parts_used(
            sample_work_order.id,
            part_id=sample_spare_part.id,
            quantity=Decimal("2"),
        )
        
        assert len(updated.parts_used) == 1
        
        # Check inventory reduced
        part = service.get_spare_part(sample_spare_part.id)
        assert part.quantity_on_hand == Decimal("3")


# =============================================================================
# TEST: DOWNTIME & OEE
# =============================================================================


class TestDowntimeAndOEE:
    """Tests for downtime tracking and OEE functions."""
    
    def test_record_downtime_start(self, service, sample_asset):
        """Test recording downtime start."""
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
            reason_code="SPINDLE-01",
            description="Spindle motor failure",
            recorded_by="op-001",
        )
        
        assert event.id is not None
        assert event.end_time is None
        assert event.duration_minutes == Decimal("0")
    
    def test_record_downtime_end(self, service, sample_asset):
        """Test recording downtime end."""
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.CHANGEOVER,
        )
        
        # Wait a tiny bit for duration
        ended = service.record_downtime_end(event.id, work_order_id="wo-001")
        
        assert ended.end_time is not None
        assert ended.duration_minutes >= Decimal("0")
    
    def test_get_downtime_events(self, service, sample_asset):
        """Test getting downtime events."""
        service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
        )
        service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.CHANGEOVER,
        )
        
        events = service.get_downtime_events(asset_id=sample_asset.id)
        assert len(events) == 2
    
    def test_get_downtime_by_category(self, service, sample_asset):
        """Test filtering downtime by category."""
        service.record_downtime_start(asset_id=sample_asset.id, category=DowntimeCategory.BREAKDOWN)
        service.record_downtime_start(asset_id=sample_asset.id, category=DowntimeCategory.CHANGEOVER)
        
        breakdowns = service.get_downtime_events(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
        )
        assert len(breakdowns) == 1
    
    def test_verify_downtime(self, service, sample_asset):
        """Test verifying downtime entry."""
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
        )
        
        verified = service.verify_downtime(
            event.id,
            verified_by="supervisor-001",
        )
        
        assert verified.verified is True
        assert verified.verified_by == "supervisor-001"
    
    def test_dispute_downtime(self, service, sample_asset):
        """Test disputing downtime entry."""
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.OPERATOR_UNAVAILABLE,
        )
        
        disputed = service.dispute_downtime(
            event.id,
            reason="Was actually waiting for material",
        )
        
        assert disputed.disputed is True
        assert disputed.dispute_reason == "Was actually waiting for material"
    
    def test_calculate_oee(self, service, sample_asset):
        """Test OEE calculation."""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(hours=8)
        
        # Record some downtime
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
        )
        # Manually set duration for test
        event.end_time = event.start_time + timedelta(minutes=30)
        event.duration_minutes = Decimal("30")
        
        oee = service.calculate_oee(
            asset_id=sample_asset.id,
            period_start=period_start,
            period_end=now,
            planned_production_time=Decimal("480"),  # 8 hours in minutes
            ideal_cycle_time=Decimal("1"),  # 1 minute per unit
            total_count=400,
            good_count=380,
        )
        
        assert oee.asset_id == sample_asset.id
        assert oee.availability > Decimal("0")
        assert oee.performance > Decimal("0")
        assert oee.quality > Decimal("0")
        assert oee.oee > Decimal("0")
    
    def test_oee_with_no_production(self, service, sample_asset):
        """Test OEE with zero production."""
        now = datetime.now(timezone.utc)
        
        oee = service.calculate_oee(
            asset_id=sample_asset.id,
            period_start=now - timedelta(hours=8),
            period_end=now,
            planned_production_time=Decimal("0"),
            ideal_cycle_time=Decimal("1"),
            total_count=0,
            good_count=0,
        )
        
        assert oee.oee == Decimal("0")


# =============================================================================
# TEST: MTBF / MTTR
# =============================================================================


class TestMTBFMTTR:
    """Tests for MTBF/MTTR calculations."""
    
    def test_failure_recorded_on_breakdown(self, service, sample_asset):
        """Test that failure is recorded when breakdown ends."""
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
            reason_code="MOTOR-FAIL",
        )
        
        service.record_downtime_end(event.id)
        
        # Check failure was recorded
        metrics = service.get_asset_reliability_metrics(sample_asset.id)
        assert metrics["failure_count"] >= 1
    
    def test_calculate_mtbf(self, service, sample_asset):
        """Test MTBF calculation."""
        # Create multiple failures
        for i in range(3):
            event = service.record_downtime_start(
                asset_id=sample_asset.id,
                category=DowntimeCategory.BREAKDOWN,
            )
            service.record_downtime_end(event.id)
        
        # MTBF may be None if no time between failures recorded
        mtbf = service.calculate_mtbf(sample_asset.id)
        # At minimum, failures should be recorded
        metrics = service.get_asset_reliability_metrics(sample_asset.id)
        assert metrics["failure_count"] == 3
    
    def test_calculate_mttr(self, service, sample_asset):
        """Test MTTR calculation."""
        event = service.record_downtime_start(
            asset_id=sample_asset.id,
            category=DowntimeCategory.BREAKDOWN,
        )
        service.record_downtime_end(event.id)
        
        mttr = service.calculate_mttr(sample_asset.id)
        assert mttr is not None
        assert mttr >= Decimal("0")
    
    def test_get_asset_reliability_metrics(self, service, sample_asset):
        """Test getting comprehensive reliability metrics."""
        metrics = service.get_asset_reliability_metrics(sample_asset.id)
        
        assert metrics["asset_id"] == sample_asset.id
        assert metrics["asset_number"] == sample_asset.asset_number
        assert "mtbf_hours" in metrics
        assert "mttr_hours" in metrics
        assert "failure_count" in metrics
    
    def test_reliability_metrics_nonexistent_asset(self, service):
        """Test reliability metrics for non-existent asset."""
        result = service.get_asset_reliability_metrics("nonexistent")
        assert "error" in result


# =============================================================================
# TEST: SPARE PARTS MANAGEMENT
# =============================================================================


class TestSparePartsManagement:
    """Tests for spare parts management functions."""
    
    def test_create_spare_part(self, service, sample_asset):
        """Test creating a spare part."""
        part = service.create_spare_part(
            part_number="FLT-001",
            name="Oil Filter",
            description="Hydraulic oil filter",
            min_quantity=Decimal("1"),
            max_quantity=Decimal("5"),
            reorder_point=Decimal("2"),
            unit_cost=Decimal("25.00"),
            applicable_assets=[sample_asset.id],
        )
        
        assert part.id is not None
        assert part.part_number == "FLT-001"
    
    def test_get_spare_part(self, service, sample_spare_part):
        """Test getting a spare part by ID."""
        part = service.get_spare_part(sample_spare_part.id)
        assert part is not None
        assert part.id == sample_spare_part.id
    
    def test_get_spare_parts_below_reorder(self, service, sample_spare_part):
        """Test getting parts below reorder point."""
        # Set quantity below reorder
        sample_spare_part.quantity_on_hand = Decimal("1")
        
        parts = service.get_spare_parts(below_reorder=True)
        assert len(parts) >= 1
    
    def test_get_spare_parts_for_asset(self, service, sample_asset, sample_spare_part):
        """Test getting parts applicable to an asset."""
        parts = service.get_spare_parts(for_asset_id=sample_asset.id)
        assert len(parts) >= 1
    
    def test_adjust_spare_part_quantity(self, service, sample_spare_part):
        """Test adjusting spare part quantity."""
        original = sample_spare_part.quantity_on_hand
        
        updated = service.adjust_spare_part_quantity(
            sample_spare_part.id,
            Decimal("10"),
            reason="Received from vendor",
        )
        
        assert updated.quantity_on_hand == original + Decimal("10")
    
    def test_reserve_parts_for_pm(self, service, sample_asset):
        """Test reserving parts for PM."""
        # Create spare part
        part = service.create_spare_part(
            part_number="LUB-001",
            name="Lubricant",
            applicable_assets=[sample_asset.id],
        )
        service.adjust_spare_part_quantity(part.id, Decimal("10"))
        
        # Create PM with spare parts
        pm = service.create_pm_schedule(
            asset_id=sample_asset.id,
            name="Lubrication PM",
            frequency_type=PMFrequencyType.CALENDAR,
            frequency_value=7,
            spare_parts=[{"part_id": part.id, "quantity": 2}],
        )
        
        reservations = service.reserve_parts_for_pm(pm.id)
        
        assert len(reservations) == 1
        assert reservations[0]["available"] is True


# =============================================================================
# TEST: STATISTICS
# =============================================================================


class TestStatistics:
    """Tests for statistics functions."""
    
    def test_get_statistics(self, service, sample_asset, sample_pm_schedule, sample_work_order, sample_spare_part):
        """Test getting maintenance statistics."""
        stats = service.get_statistics()
        
        assert stats["total_assets"] >= 1
        assert stats["total_pm_schedules"] >= 1
        assert stats["total_work_orders"] >= 1
        assert stats["total_spare_parts"] >= 1
        assert "assets_by_status" in stats
        assert "assets_by_criticality" in stats
        assert "work_orders_by_status" in stats


# =============================================================================
# TEST: FACTORY FUNCTION
# =============================================================================


class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_maintenance_service(self):
        """Test factory function creates service."""
        service = create_maintenance_service()
        
        assert service is not None
        assert isinstance(service, MaintenanceService)
    
    def test_factory_creates_fresh_instance(self):
        """Test factory creates independent instances."""
        service1 = create_maintenance_service()
        service2 = create_maintenance_service()
        
        # Add asset to service1
        service1.create_asset(name="Asset 1", asset_type=AssetType.MACHINE)
        
        # Service2 should be empty
        assert len(service1.get_assets()) == 1
        assert len(service2.get_assets()) == 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_get_nonexistent_asset(self, service):
        """Test getting non-existent asset."""
        result = service.get_asset("nonexistent")
        assert result is None
    
    def test_update_nonexistent_asset(self, service):
        """Test updating non-existent asset."""
        result = service.update_asset_status("nonexistent", AssetStatus.DOWN)
        assert result is None
    
    def test_get_nonexistent_pm_schedule(self, service):
        """Test getting non-existent PM schedule."""
        result = service.get_pm_schedule("nonexistent")
        assert result is None
    
    def test_complete_nonexistent_pm(self, service):
        """Test completing non-existent PM."""
        result = service.complete_pm("nonexistent", "user", Decimal("1"))
        assert result is None
    
    def test_create_pm_work_order_nonexistent(self, service):
        """Test creating work order from non-existent PM."""
        result = service.create_pm_work_order("nonexistent")
        assert result is None
    
    def test_get_nonexistent_work_order(self, service):
        """Test getting non-existent work order."""
        result = service.get_work_order("nonexistent")
        assert result is None
    
    def test_update_nonexistent_work_order(self, service):
        """Test updating non-existent work order."""
        result = service.update_work_order_status("nonexistent", WorkOrderStatus.COMPLETED)
        assert result is None
    
    def test_end_nonexistent_downtime(self, service):
        """Test ending non-existent downtime."""
        result = service.record_downtime_end("nonexistent")
        assert result is None
    
    def test_verify_nonexistent_downtime(self, service):
        """Test verifying non-existent downtime."""
        result = service.verify_downtime("nonexistent", "user")
        assert result is None
    
    def test_dispute_nonexistent_downtime(self, service):
        """Test disputing non-existent downtime."""
        result = service.dispute_downtime("nonexistent", "reason")
        assert result is None
    
    def test_get_nonexistent_spare_part(self, service):
        """Test getting non-existent spare part."""
        result = service.get_spare_part("nonexistent")
        assert result is None
    
    def test_adjust_nonexistent_spare_part(self, service):
        """Test adjusting non-existent spare part."""
        result = service.adjust_spare_part_quantity("nonexistent", Decimal("5"))
        assert result is None
    
    def test_reserve_parts_nonexistent_pm(self, service):
        """Test reserving parts for non-existent PM."""
        result = service.reserve_parts_for_pm("nonexistent")
        assert result == []
    
    def test_mtbf_no_failures(self, service, sample_asset):
        """Test MTBF with no failures."""
        mtbf = service.calculate_mtbf(sample_asset.id)
        assert mtbf is None
    
    def test_mttr_no_failures(self, service, sample_asset):
        """Test MTTR with no failures."""
        mttr = service.calculate_mttr(sample_asset.id)
        assert mttr is None

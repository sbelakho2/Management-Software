"""
Tests for Work Center and Station models.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from sensei.models.work_center import (
    WorkCenter,
    WorkCenterStatus,
    Station,
    StationType,
    StationStatus,
)


class TestWorkCenterModel:
    """Test cases for WorkCenter model."""

    def test_work_center_creation_basic(self):
        """Test basic work center creation with required fields."""
        work_center = WorkCenter(
            name="Assembly Line 1",
            code="ASM-001",
            status=WorkCenterStatus.ACTIVE,
            efficiency_target=Decimal("85.00"),
        )

        assert work_center.name == "Assembly Line 1"
        assert work_center.code == "ASM-001"
        assert work_center.status == WorkCenterStatus.ACTIVE
        assert work_center.efficiency_target == Decimal("85.00")

    def test_work_center_creation_full(self):
        """Test work center creation with all fields."""
        work_center = WorkCenter(
            name="Machining Center",
            code="MCH-001",
            description="Primary machining work center",
            location="Building A, Floor 2",
            capacity_units="units/hour",
            capacity_value=Decimal("50.0000"),
            efficiency_target=Decimal("90.00"),
            status=WorkCenterStatus.ACTIVE,
        )

        assert work_center.name == "Machining Center"
        assert work_center.code == "MCH-001"
        assert work_center.description == "Primary machining work center"
        assert work_center.location == "Building A, Floor 2"
        assert work_center.capacity_units == "units/hour"
        assert work_center.capacity_value == Decimal("50.0000")
        assert work_center.efficiency_target == Decimal("90.00")

    def test_work_center_status_values(self):
        """Test all valid status values."""
        for status in WorkCenterStatus:
            work_center = WorkCenter(
                name=f"WC {status.value}",
                code=f"WC-{status.value[:3].upper()}",
                status=status,
            )
            assert work_center.status == status

    def test_work_center_is_operational_property(self):
        """Test is_operational property."""
        wc_active = WorkCenter(
            name="Active WC",
            code="ACT-001",
            status=WorkCenterStatus.ACTIVE,
        )
        wc_inactive = WorkCenter(
            name="Inactive WC",
            code="INA-001",
            status=WorkCenterStatus.INACTIVE,
        )
        wc_maintenance = WorkCenter(
            name="Maintenance WC",
            code="MNT-001",
            status=WorkCenterStatus.MAINTENANCE,
        )

        assert wc_active.is_operational is True
        assert wc_inactive.is_operational is False
        assert wc_maintenance.is_operational is False

    def test_work_center_repr(self):
        """Test string representation."""
        work_center = WorkCenter(
            name="Test WC",
            code="TST-001",
        )
        work_center.id = 1

        assert "WorkCenter" in repr(work_center)
        assert "TST-001" in repr(work_center)


class TestStationModel:
    """Test cases for Station model."""

    def test_station_creation_basic(self):
        """Test basic station creation."""
        station = Station(
            name="Assembly Station 1",
            code="STN-001",
            work_center_id=1,
            station_type=StationType.ASSEMBLY,
            status=StationStatus.ACTIVE,
            takt_time_seconds=60,
            cycle_time_seconds=60,
        )

        assert station.name == "Assembly Station 1"
        assert station.code == "STN-001"
        assert station.station_type == StationType.ASSEMBLY
        assert station.status == StationStatus.ACTIVE
        assert station.takt_time_seconds == 60
        assert station.cycle_time_seconds == 60

    def test_station_creation_full(self):
        """Test station creation with all fields."""
        station = Station(
            name="CNC Machine 1",
            code="CNC-001",
            description="5-axis CNC machining center",
            station_type=StationType.MACHINING,
            takt_time_seconds=120,
            cycle_time_seconds=110,
            setup_time_seconds=600,
            status=StationStatus.ACTIVE,
            yellow_ack_minutes=10,
            red_ack_minutes=5,
            resolution_target_minutes=60,
            work_center_id=1,
        )

        assert station.name == "CNC Machine 1"
        assert station.station_type == StationType.MACHINING
        assert station.takt_time_seconds == 120
        assert station.cycle_time_seconds == 110
        assert station.setup_time_seconds == 600
        assert station.yellow_ack_minutes == 10
        assert station.red_ack_minutes == 5
        assert station.resolution_target_minutes == 60

    def test_station_type_values(self):
        """Test all valid station type values."""
        for stype in StationType:
            station = Station(
                name=f"Station {stype.value}",
                code=f"STN-{stype.value[:3].upper()}",
                station_type=stype,
                work_center_id=1,
            )
            assert station.station_type == stype

    def test_station_status_values(self):
        """Test all valid station status values."""
        for status in StationStatus:
            station = Station(
                name=f"Station {status.value}",
                code=f"STN-{status.value[:3].upper()}",
                status=status,
                work_center_id=1,
            )
            assert station.status == status

    def test_station_efficiency_ratio(self):
        """Test efficiency ratio calculation."""
        # Takt = Cycle (balanced)
        station_balanced = Station(
            name="Balanced",
            code="BAL-001",
            takt_time_seconds=60,
            cycle_time_seconds=60,
            work_center_id=1,
        )
        assert station_balanced.efficiency_ratio == Decimal("1")

        # Faster than takt
        station_fast = Station(
            name="Fast",
            code="FST-001",
            takt_time_seconds=60,
            cycle_time_seconds=50,
            work_center_id=1,
        )
        assert station_fast.efficiency_ratio == Decimal("1.2")

        # Slower than takt (bottleneck)
        station_slow = Station(
            name="Slow",
            code="SLW-001",
            takt_time_seconds=60,
            cycle_time_seconds=80,
            work_center_id=1,
        )
        assert station_slow.efficiency_ratio == Decimal("0.75")

    def test_station_is_bottleneck(self):
        """Test bottleneck detection."""
        station_ok = Station(
            name="OK",
            code="OK-001",
            takt_time_seconds=60,
            cycle_time_seconds=55,
            work_center_id=1,
        )
        assert station_ok.is_bottleneck is False

        station_bottleneck = Station(
            name="Bottleneck",
            code="BTN-001",
            takt_time_seconds=60,
            cycle_time_seconds=75,
            work_center_id=1,
        )
        assert station_bottleneck.is_bottleneck is True

    def test_station_is_available(self):
        """Test availability check."""
        station_active = Station(
            name="Active",
            code="ACT-001",
            status=StationStatus.ACTIVE,
            work_center_id=1,
        )
        station_breakdown = Station(
            name="Breakdown",
            code="BRK-001",
            status=StationStatus.BREAKDOWN,
            work_center_id=1,
        )

        assert station_active.is_available is True
        assert station_breakdown.is_available is False

    def test_station_repr(self):
        """Test string representation."""
        station = Station(
            name="Test Station",
            code="TST-001",
            station_type=StationType.INSPECTION,
            work_center_id=1,
        )
        station.id = 1

        assert "Station" in repr(station)
        assert "TST-001" in repr(station)
        assert "inspection" in repr(station)


class TestWorkCenterStationRelationship:
    """Test Work Center - Station relationships."""

    def test_work_center_has_stations_list(self):
        """Test that work center has stations list attribute."""
        work_center = WorkCenter(
            name="Test WC",
            code="WC-001",
        )
        # Relationship should be initialized
        assert hasattr(work_center, 'stations')

    def test_station_has_work_center_reference(self):
        """Test that station references work center."""
        station = Station(
            name="Test Station",
            code="STN-001",
            work_center_id=1,
        )
        assert station.work_center_id == 1
        assert hasattr(station, 'work_center')


class TestWorkCenterValidation:
    """Test Work Center validation constraints."""

    def test_efficiency_target_explicit(self):
        """Test explicit efficiency target."""
        work_center = WorkCenter(
            name="Default WC",
            code="DEF-001",
            efficiency_target=Decimal("85.00"),
        )
        assert work_center.efficiency_target == Decimal("85.00")

    def test_efficiency_target_custom(self):
        """Test custom efficiency target."""
        work_center = WorkCenter(
            name="High Efficiency WC",
            code="HE-001",
            efficiency_target=Decimal("95.00"),
        )
        assert work_center.efficiency_target == Decimal("95.00")


class TestStationValidation:
    """Test Station validation constraints."""

    def test_takt_time_explicit(self):
        """Test explicit takt time."""
        station = Station(
            name="Default Station",
            code="DEF-001",
            work_center_id=1,
            takt_time_seconds=60,
        )
        assert station.takt_time_seconds == 60

    def test_setup_time_explicit(self):
        """Test explicit setup time is zero."""
        station = Station(
            name="No Setup Station",
            code="NS-001",
            work_center_id=1,
            setup_time_seconds=0,
        )
        assert station.setup_time_seconds == 0

    def test_andon_sla_explicit(self):
        """Test explicit Andon SLA values."""
        station = Station(
            name="Default SLA Station",
            code="SLA-001",
            work_center_id=1,
            yellow_ack_minutes=5,
            red_ack_minutes=2,
            resolution_target_minutes=30,
        )
        assert station.yellow_ack_minutes == 5
        assert station.red_ack_minutes == 2
        assert station.resolution_target_minutes == 30

    def test_andon_sla_custom(self):
        """Test custom Andon SLA values."""
        station = Station(
            name="Custom SLA Station",
            code="CSL-001",
            work_center_id=1,
            yellow_ack_minutes=15,
            red_ack_minutes=3,
            resolution_target_minutes=45,
        )
        assert station.yellow_ack_minutes == 15
        assert station.red_ack_minutes == 3
        assert station.resolution_target_minutes == 45


class TestWorkCenterEdgeCases:
    """Test edge cases for Work Center model."""

    def test_work_center_with_empty_description(self):
        """Test work center with None description."""
        work_center = WorkCenter(
            name="No Description WC",
            code="ND-001",
            description=None,
        )
        assert work_center.description is None

    def test_work_center_with_zero_capacity(self):
        """Test work center with zero capacity value."""
        work_center = WorkCenter(
            name="Zero Capacity WC",
            code="ZC-001",
            capacity_value=Decimal("0.0000"),
        )
        assert work_center.capacity_value == Decimal("0.0000")


class TestStationEdgeCases:
    """Test edge cases for Station model."""

    def test_station_zero_cycle_time_efficiency(self):
        """Test efficiency calculation with zero cycle time."""
        station = Station(
            name="Zero Cycle",
            code="ZC-001",
            takt_time_seconds=60,
            cycle_time_seconds=0,  # Edge case
            work_center_id=1,
        )
        # Should handle division by zero gracefully
        assert station.efficiency_ratio == Decimal("0")

    def test_station_very_long_times(self):
        """Test station with very long cycle times."""
        station = Station(
            name="Long Cycle",
            code="LC-001",
            takt_time_seconds=3600,  # 1 hour
            cycle_time_seconds=3600,
            setup_time_seconds=7200,  # 2 hours
            work_center_id=1,
        )
        assert station.takt_time_seconds == 3600
        assert station.setup_time_seconds == 7200

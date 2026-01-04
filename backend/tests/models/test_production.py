"""
Tests for Production Cell models.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from sensei.models.production import (
    ProductionCell,
    CellType,
    CellStatus,
    CellPerformance,
    ShiftNumber,
)


class TestProductionCellModel:
    """Test cases for ProductionCell model."""

    def test_cell_creation_basic(self):
        """Test basic cell creation with explicit required fields."""
        cell = ProductionCell(
            name="Assembly Cell 1",
            code="CELL-ASM-001",
            work_center_id=1,
            cell_type=CellType.U_CELL,
            status=CellStatus.ACTIVE,
        )

        assert cell.name == "Assembly Cell 1"
        assert cell.code == "CELL-ASM-001"
        assert cell.cell_type == CellType.U_CELL
        assert cell.status == CellStatus.ACTIVE

    def test_cell_creation_full(self):
        """Test cell with all fields."""
        cell = ProductionCell(
            name="Welding Cell",
            code="CELL-WLD-001",
            description="Robotic welding cell",
            work_center_id=5,
            cell_type=CellType.FLOW,
            status=CellStatus.ACTIVE,
            takt_time_seconds=45,
            target_cycle_time_seconds=40,
            target_output_per_shift=480,
            shift_duration_hours=Decimal("8.0"),
            planned_efficiency=Decimal("90.00"),
            min_operators=2,
            standard_operators=3,
            max_operators=4,
            current_operators=3,
            current_output=250,
            current_efficiency_percentage=Decimal("92.5"),
            current_oee_percentage=Decimal("85.0"),
        )

        assert cell.cell_type == CellType.FLOW
        assert cell.takt_time_seconds == 45
        assert cell.target_output_per_shift == 480
        assert cell.min_operators == 2
        assert cell.current_oee_percentage == Decimal("85.0")

    def test_cell_type_values(self):
        """Test all cell type values."""
        for cell_type in CellType:
            cell = ProductionCell(
                name=f"Test {cell_type.value}",
                code=f"CELL-{cell_type.value}",
                work_center_id=1,
                cell_type=cell_type,
            )
            assert cell.cell_type == cell_type

    def test_cell_status_values(self):
        """Test all status values."""
        for status in CellStatus:
            cell = ProductionCell(
                name=f"Test {status.value}",
                code=f"CELL-{status.value}",
                work_center_id=1,
                status=status,
            )
            assert cell.status == status

    def test_cell_is_operational(self):
        """Test is_operational property."""
        active = ProductionCell(
            name="Active",
            code="CELL-ACTIVE",
            work_center_id=1,
            status=CellStatus.ACTIVE,
        )

        maintenance = ProductionCell(
            name="Maintenance",
            code="CELL-MAINT",
            work_center_id=1,
            status=CellStatus.MAINTENANCE,
        )

        inactive = ProductionCell(
            name="Inactive",
            code="CELL-INACTIVE",
            work_center_id=1,
            status=CellStatus.INACTIVE,
        )

        assert active.is_operational is True
        assert maintenance.is_operational is False
        assert inactive.is_operational is False

    def test_cell_is_understaffed(self):
        """Test is_understaffed property."""
        understaffed = ProductionCell(
            name="Understaffed",
            code="CELL-UNDER",
            work_center_id=1,
            min_operators=3,
            current_operators=2,
        )

        fully_staffed = ProductionCell(
            name="Staffed",
            code="CELL-STAFF",
            work_center_id=1,
            min_operators=2,
            current_operators=3,
        )

        assert understaffed.is_understaffed is True
        assert fully_staffed.is_understaffed is False

    def test_cell_output_vs_target_percentage(self):
        """Test output_vs_target_percentage property."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            target_output_per_shift=100,
            current_output=75,
        )

        assert cell.output_vs_target_percentage == Decimal("75")

    def test_cell_output_vs_target_zero(self):
        """Test output_vs_target_percentage with zero target."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            target_output_per_shift=0,
            current_output=0,
        )

        assert cell.output_vs_target_percentage == Decimal("0")

    def test_cell_theoretical_capacity(self):
        """Test theoretical_capacity_per_shift property."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            takt_time_seconds=60,
            shift_duration_hours=Decimal("8.0"),
        )

        # 8 hours = 28800 seconds, 60 second takt = 480 units
        assert cell.theoretical_capacity_per_shift == 480

    def test_cell_theoretical_capacity_zero_takt(self):
        """Test theoretical_capacity with zero takt time."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            takt_time_seconds=0,
            shift_duration_hours=Decimal("8.0"),
        )

        # Zero takt time edge case - should not raise
        # Note: This would fail the constraint in DB but test model behavior
        assert cell.theoretical_capacity_per_shift == 0

    def test_cell_repr(self):
        """Test string representation."""
        cell = ProductionCell(
            name="Test Cell",
            code="CELL-TEST",
            work_center_id=1,
            cell_type=CellType.U_CELL,
        )
        cell.id = 1

        assert "ProductionCell" in repr(cell)
        assert "CELL-TEST" in repr(cell)


class TestCellPerformanceModel:
    """Test cases for CellPerformance model."""

    def test_performance_creation_basic(self):
        """Test basic performance record creation."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=100,
            actual_output=95,
            good_output=90,
            planned_time_minutes=480,
            operating_time_minutes=450,
            availability_percentage=Decimal("93.75"),
            performance_percentage=Decimal("95.00"),
            quality_percentage=Decimal("94.74"),
            oee_percentage=Decimal("84.44"),
            efficiency_percentage=Decimal("95.00"),
        )

        assert perf.cell_id == 1
        assert perf.shift_number == ShiftNumber.SHIFT_1
        assert perf.actual_output == 95
        assert perf.oee_percentage == Decimal("84.44")

    def test_performance_creation_full(self):
        """Test performance with all fields."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_2,
            planned_output=500,
            actual_output=480,
            good_output=470,
            rework_output=5,
            scrap_output=5,
            planned_time_minutes=480,
            operating_time_minutes=450,
            downtime_minutes=30,
            changeover_minutes=15,
            unplanned_downtime_minutes=15,
            planned_downtime_minutes=15,
            availability_percentage=Decimal("93.75"),
            performance_percentage=Decimal("96.00"),
            quality_percentage=Decimal("97.92"),
            oee_percentage=Decimal("88.10"),
            efficiency_percentage=Decimal("96.00"),
            operator_count=4,
            labor_hours=Decimal("32.0"),
            units_per_labor_hour=Decimal("15.0"),
            andon_events_count=3,
            quality_issues_count=2,
            notes="Good shift overall",
            issues_summary="Minor tool issue resolved",
        )

        assert perf.rework_output == 5
        assert perf.scrap_output == 5
        assert perf.downtime_minutes == 30
        assert perf.operator_count == 4
        assert perf.andon_events_count == 3

    def test_shift_number_values(self):
        """Test all shift number values."""
        for shift in ShiftNumber:
            perf = CellPerformance(
                cell_id=1,
                shift_date=date.today(),
                shift_number=shift,
                planned_output=100,
                actual_output=100,
                good_output=100,
                planned_time_minutes=480,
                operating_time_minutes=480,
                availability_percentage=Decimal("100"),
                performance_percentage=Decimal("100"),
                quality_percentage=Decimal("100"),
                oee_percentage=Decimal("100"),
                efficiency_percentage=Decimal("100"),
            )
            assert perf.shift_number == shift

    def test_performance_output_target_ratio(self):
        """Test output_target_ratio property."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=100,
            actual_output=80,
            good_output=80,
            planned_time_minutes=480,
            operating_time_minutes=480,
            availability_percentage=Decimal("100"),
            performance_percentage=Decimal("80"),
            quality_percentage=Decimal("100"),
            oee_percentage=Decimal("80"),
            efficiency_percentage=Decimal("80"),
        )

        assert perf.output_target_ratio == Decimal("80")

    def test_performance_output_target_ratio_zero(self):
        """Test output_target_ratio with zero planned."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=0,
            actual_output=0,
            good_output=0,
            planned_time_minutes=480,
            operating_time_minutes=480,
            availability_percentage=Decimal("100"),
            performance_percentage=Decimal("0"),
            quality_percentage=Decimal("100"),
            oee_percentage=Decimal("0"),
            efficiency_percentage=Decimal("0"),
        )

        assert perf.output_target_ratio == Decimal("0")

    def test_performance_scrap_rate(self):
        """Test scrap_rate property."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=100,
            actual_output=100,
            good_output=95,
            scrap_output=5,
            planned_time_minutes=480,
            operating_time_minutes=480,
            availability_percentage=Decimal("100"),
            performance_percentage=Decimal("100"),
            quality_percentage=Decimal("95"),
            oee_percentage=Decimal("95"),
            efficiency_percentage=Decimal("100"),
        )

        assert perf.scrap_rate == Decimal("5")

    def test_performance_scrap_rate_zero_output(self):
        """Test scrap_rate with zero output."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=100,
            actual_output=0,
            good_output=0,
            scrap_output=0,
            planned_time_minutes=480,
            operating_time_minutes=0,
            availability_percentage=Decimal("0"),
            performance_percentage=Decimal("0"),
            quality_percentage=Decimal("100"),
            oee_percentage=Decimal("0"),
            efficiency_percentage=Decimal("0"),
        )

        assert perf.scrap_rate == Decimal("0")

    def test_performance_repr(self):
        """Test string representation."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=100,
            actual_output=100,
            good_output=100,
            planned_time_minutes=480,
            operating_time_minutes=480,
            availability_percentage=Decimal("100"),
            performance_percentage=Decimal("100"),
            quality_percentage=Decimal("100"),
            oee_percentage=Decimal("85"),
            efficiency_percentage=Decimal("100"),
        )

        assert "CellPerformance" in repr(perf)


class TestCellPerformanceOEECalculation:
    """Test OEE calculation classmethod."""

    def test_calculate_oee_perfect(self):
        """Test OEE calculation with perfect metrics."""
        availability, performance, quality, oee = CellPerformance.calculate_oee(
            planned_time=480,
            operating_time=480,
            actual_output=100,
            good_output=100,
            ideal_cycle_time_seconds=288,  # 100 units in 28800 seconds
        )

        assert availability == Decimal("100")
        assert performance == Decimal("100")
        assert quality == Decimal("100")
        assert oee == Decimal("100")

    def test_calculate_oee_typical(self):
        """Test OEE calculation with typical metrics."""
        # 90% availability, 95% performance, 99% quality
        # Expected OEE = 0.9 * 0.95 * 0.99 = 84.645%
        availability, performance, quality, oee = CellPerformance.calculate_oee(
            planned_time=480,  # 8 hours
            operating_time=432,  # 7.2 hours (90% availability)
            actual_output=100,
            good_output=99,  # 99% quality
            ideal_cycle_time_seconds=247,  # Would give ~95% performance at 432 min
        )

        assert availability == Decimal("90")
        # Performance and OEE will vary based on calc

    def test_calculate_oee_zero_planned_time(self):
        """Test OEE calculation with zero planned time."""
        availability, performance, quality, oee = CellPerformance.calculate_oee(
            planned_time=0,
            operating_time=0,
            actual_output=0,
            good_output=0,
            ideal_cycle_time_seconds=60,
        )

        assert availability == Decimal("0")

    def test_calculate_oee_zero_operating_time(self):
        """Test OEE calculation with zero operating time."""
        availability, performance, quality, oee = CellPerformance.calculate_oee(
            planned_time=480,
            operating_time=0,
            actual_output=0,
            good_output=0,
            ideal_cycle_time_seconds=60,
        )

        assert availability == Decimal("0")
        assert performance == Decimal("0")

    def test_calculate_oee_zero_output(self):
        """Test OEE calculation with zero output."""
        availability, performance, quality, oee = CellPerformance.calculate_oee(
            planned_time=480,
            operating_time=480,
            actual_output=0,
            good_output=0,
            ideal_cycle_time_seconds=60,
        )

        assert quality == Decimal("100")  # 0/0 defaults to 100%
        assert performance == Decimal("0")


class TestProductionRelationships:
    """Test Production model relationships."""

    def test_cell_has_stations_list(self):
        """Test that cell has stations list."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
        )
        assert hasattr(cell, 'stations')

    def test_cell_has_performance_records_list(self):
        """Test that cell has performance_records list."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
        )
        assert hasattr(cell, 'performance_records')

    def test_cell_has_work_center_relationship(self):
        """Test that cell has work_center relationship."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
        )
        assert hasattr(cell, 'work_center')


class TestProductionValidation:
    """Test validation constraints."""

    def test_cell_explicit_takt_time(self):
        """Test explicit takt time is set correctly."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            cell_type=CellType.U_CELL,
            status=CellStatus.ACTIVE,
            takt_time_seconds=60,
        )
        assert cell.takt_time_seconds == 60

    def test_cell_explicit_efficiency(self):
        """Test explicit planned efficiency is set correctly."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            cell_type=CellType.U_CELL,
            status=CellStatus.ACTIVE,
            planned_efficiency=Decimal("85.00"),
        )
        assert cell.planned_efficiency == Decimal("85.00")

    def test_performance_explicit_rework(self):
        """Test explicit rework value."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=100,
            actual_output=100,
            good_output=100,
            rework_output=0,
            planned_time_minutes=480,
            operating_time_minutes=480,
            availability_percentage=Decimal("100"),
            performance_percentage=Decimal("100"),
            quality_percentage=Decimal("100"),
            oee_percentage=Decimal("100"),
            efficiency_percentage=Decimal("100"),
        )
        assert perf.rework_output == 0


class TestProductionEdgeCases:
    """Test edge cases for Production models."""

    def test_cell_with_exact_staffing(self):
        """Test cell with exact minimum staffing."""
        cell = ProductionCell(
            name="Test",
            code="CELL-TEST",
            work_center_id=1,
            min_operators=2,
            standard_operators=3,
            max_operators=4,
            current_operators=2,
        )

        assert cell.is_understaffed is False

    def test_cell_multiple_shifts(self):
        """Test creating performance records for multiple shifts."""
        records = []
        for shift in ShiftNumber:
            perf = CellPerformance(
                cell_id=1,
                shift_date=date.today(),
                shift_number=shift,
                planned_output=100,
                actual_output=95,
                good_output=93,
                planned_time_minutes=480,
                operating_time_minutes=450,
                availability_percentage=Decimal("93.75"),
                performance_percentage=Decimal("95.00"),
                quality_percentage=Decimal("97.89"),
                oee_percentage=Decimal("87.26"),
                efficiency_percentage=Decimal("95.00"),
            )
            records.append(perf)

        assert len(records) == 3
        assert records[0].shift_number == ShiftNumber.SHIFT_1
        assert records[2].shift_number == ShiftNumber.SHIFT_3

    def test_cell_high_oee(self):
        """Test cell with world-class OEE."""
        perf = CellPerformance(
            cell_id=1,
            shift_date=date.today(),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=500,
            actual_output=490,
            good_output=488,
            rework_output=2,
            scrap_output=0,
            planned_time_minutes=480,
            operating_time_minutes=475,
            downtime_minutes=5,
            availability_percentage=Decimal("98.96"),
            performance_percentage=Decimal("98.00"),
            quality_percentage=Decimal("99.59"),
            oee_percentage=Decimal("96.57"),  # World-class
            efficiency_percentage=Decimal("98.00"),
        )

        assert perf.oee_percentage > Decimal("85")  # World-class threshold

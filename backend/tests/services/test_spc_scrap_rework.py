"""Tests for SPC & Scrap/Rework Accounting Service (Development Plan 22.7)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.spc_scrap_rework import (
    SPCScrapReworkService,
    ControlChartType,
    ViolationType,
    ScrapReason,
    ReworkReason,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> SPCScrapReworkService:
    return SPCScrapReworkService()


@pytest.fixture
def quality_roles() -> set[str]:
    return {"quality"}


@pytest.fixture
def finance_roles() -> set[str]:
    return {"finance"}


@pytest.fixture
def reader_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def norole() -> set[str]:
    return {"guest"}


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_create_chart_requires_quality_role(
        self, svc: SPCScrapReworkService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Quality write role required"):
            svc.create_control_chart(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                name="Test Chart",
                chart_type=ControlChartType.XBAR_R,
                characteristic="Length",
                station_id="STATION-A",
            )

    def test_record_scrap_requires_quality_role(
        self, svc: SPCScrapReworkService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Quality write role required"):
            svc.record_scrap(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                work_order_id="WO-001",
                product_id="PROD-001",
                lot_number="LOT-001",
                quantity=5,
                unit="pcs",
                reason=ScrapReason.PROCESS_ERROR,
                reason_detail="Failed inspection",
                station_id="STATION-A",
            )

    def test_post_scrap_to_gl_requires_finance_role(
        self, svc: SPCScrapReworkService, quality_roles: set[str], reader_roles: set[str]
    ) -> None:
        record = svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.PROCESS_ERROR,
            reason_detail="Failed inspection",
            station_id="STATION-A",
            material_cost=Decimal("100"),
        )

        with pytest.raises(PermissionError, match="Finance role required"):
            svc.post_scrap_to_gl(
                actor_id="auditor1",
                actor_roles=reader_roles,
                correlation_id="cor-2",
                scrap_id=record.id,
            )

    def test_reader_can_list_charts(
        self, svc: SPCScrapReworkService, quality_roles: set[str], reader_roles: set[str]
    ) -> None:
        svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
        )

        charts = svc.list_control_charts(actor_roles=reader_roles)
        assert len(charts) == 1


# ============================================================
# Control Chart Tests
# ============================================================


class TestControlCharts:
    def test_create_control_chart(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Shaft Diameter",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Diameter",
            station_id="STATION-A",
            product_id="SHAFT-001",
            subgroup_size=5,
            ucl=10.05,
            lcl=9.95,
            center_line=10.0,
            usl=10.1,
            lsl=9.9,
            target=10.0,
        )

        assert chart.name == "Shaft Diameter"
        assert chart.chart_type == ControlChartType.XBAR_R
        assert chart.ucl == 10.05
        assert chart.lcl == 9.95

    def test_list_charts_by_station(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Chart A",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
        )
        svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            name="Chart B",
            chart_type=ControlChartType.P_CHART,
            characteristic="Defects",
            station_id="STATION-B",
        )

        charts = svc.list_control_charts(
            actor_roles=quality_roles, station_id="STATION-A"
        )
        assert len(charts) == 1
        assert charts[0].name == "Chart A"


# ============================================================
# SPC Measurement Tests
# ============================================================


class TestSPCMeasurement:
    def test_record_measurement(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
            ucl=10.1,
            lcl=9.9,
            center_line=10.0,
        )

        point, violation = svc.record_measurement(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            chart_id=chart.id,
            value=10.0,
            lot_number="LOT-001",
        )

        assert point.value == 10.0
        assert point.lot_number == "LOT-001"
        assert violation is None  # In control

    def test_detect_ucl_violation(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
            ucl=10.1,
            lcl=9.9,
            center_line=10.0,
        )

        point, violation = svc.record_measurement(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            chart_id=chart.id,
            value=10.2,  # Above UCL
        )

        assert violation is not None
        assert violation.violation_type == ViolationType.ABOVE_UCL

    def test_detect_lcl_violation(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
            ucl=10.1,
            lcl=9.9,
            center_line=10.0,
        )

        point, violation = svc.record_measurement(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            chart_id=chart.id,
            value=9.8,  # Below LCL
        )

        assert violation is not None
        assert violation.violation_type == ViolationType.BELOW_LCL

    def test_detect_trend_violation(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
            ucl=20.0,
            lcl=0.0,
            center_line=10.0,
        )

        # Record 6 increasing values that CROSS center line (avoids RUN violation)
        # Values: 8, 9, 10, 11, 12, 13 - strictly increasing and crossing center at 10.0
        for i, val in enumerate([8.0, 9.0, 10.0, 11.0, 12.0, 13.0]):
            pt, v = svc.record_measurement(
                actor_id="operator1",
                actor_roles=quality_roles,
                correlation_id=f"cor-{i+2}",
                chart_id=chart.id,
                value=val,
            )
            # First 6 points should not yet trigger trend
            if i < 5:
                assert v is None, f"Point {i+1} should not violate: value={val}"

        # 7th point continues trend => triggers TREND
        point, violation = svc.record_measurement(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-8",
            chart_id=chart.id,
            value=14.0,
        )

        assert violation is not None, "7th consecutive increasing point should trigger TREND"
        assert violation.violation_type == ViolationType.TREND

    def test_get_chart_data(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
        )

        for i in range(5):
            svc.record_measurement(
                actor_id="operator1",
                actor_roles=quality_roles,
                correlation_id=f"cor-{i+2}",
                chart_id=chart.id,
                value=10.0 + i * 0.01,
            )

        data = svc.get_chart_data(actor_roles=quality_roles, chart_id=chart.id)
        assert len(data) == 5

    def test_calculate_process_capability(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
            usl=10.5,
            lsl=9.5,
        )

        # Record data with known distribution
        values = [10.0, 10.1, 9.9, 10.05, 9.95, 10.02, 9.98, 10.03, 9.97, 10.0]
        for i, val in enumerate(values):
            svc.record_measurement(
                actor_id="operator1",
                actor_roles=quality_roles,
                correlation_id=f"cor-{i+2}",
                chart_id=chart.id,
                value=val,
            )

        capability = svc.calculate_process_capability(
            actor_roles=quality_roles, chart_id=chart.id
        )

        assert "cp" in capability
        assert "cpk" in capability
        assert capability["sample_size"] == 10


# ============================================================
# Scrap Recording Tests
# ============================================================


class TestScrapRecording:
    def test_record_scrap_basic(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        record = svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.PROCESS_ERROR,
            reason_detail="Parts burned during heat treatment",
            station_id="STATION-A",
            material_cost=Decimal("100.00"),
            labor_cost=Decimal("25.00"),
            overhead_cost=Decimal("10.00"),
        )

        assert record.quantity == 5
        assert record.reason == ScrapReason.PROCESS_ERROR
        assert record.total_cost == Decimal("135.00")
        assert not record.gl_posted

    def test_record_scrap_requires_detail(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="reason_detail required"):
            svc.record_scrap(
                actor_id="quality1",
                actor_roles=quality_roles,
                correlation_id="cor-1",
                work_order_id="WO-001",
                product_id="PROD-001",
                lot_number="LOT-001",
                quantity=5,
                unit="pcs",
                reason=ScrapReason.PROCESS_ERROR,
                reason_detail="",  # Empty
                station_id="STATION-A",
            )

    def test_post_scrap_to_gl(
        self, svc: SPCScrapReworkService, quality_roles: set[str], finance_roles: set[str]
    ) -> None:
        record = svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.MATERIAL_DEFECT,
            reason_detail="Raw material had inclusions",
            station_id="STATION-A",
            material_cost=Decimal("200.00"),
        )

        posted = svc.post_scrap_to_gl(
            actor_id="accountant1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            scrap_id=record.id,
        )

        assert posted.gl_posted is True

    def test_cannot_double_post_scrap(
        self, svc: SPCScrapReworkService, quality_roles: set[str], finance_roles: set[str]
    ) -> None:
        record = svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.EQUIPMENT_MALFUNCTION,
            reason_detail="Machine overheated",
            station_id="STATION-A",
            material_cost=Decimal("150.00"),
        )

        svc.post_scrap_to_gl(
            actor_id="accountant1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            scrap_id=record.id,
        )

        with pytest.raises(ValueError, match="Already posted"):
            svc.post_scrap_to_gl(
                actor_id="accountant1",
                actor_roles=finance_roles,
                correlation_id="cor-3",
                scrap_id=record.id,
            )


# ============================================================
# Rework Recording Tests
# ============================================================


class TestReworkRecording:
    def test_record_rework_basic(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        record = svc.record_rework(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=10,
            unit="pcs",
            reason=ReworkReason.DIMENSIONAL_OOS,
            reason_detail="Holes drilled 0.5mm undersized",
            station_id="STATION-A",
            rework_instructions="Re-drill holes to correct size",
        )

        assert record.quantity == 10
        assert record.reason == ReworkReason.DIMENSIONAL_OOS
        assert record.completed_at is None

    def test_complete_rework(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        record = svc.record_rework(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=10,
            unit="pcs",
            reason=ReworkReason.COSMETIC_DEFECT,
            reason_detail="Scratches on surface",
            station_id="STATION-A",
        )

        completed = svc.complete_rework(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            rework_id=record.id,
            labor_hours=Decimal("2.5"),
            labor_cost=Decimal("75.00"),
            material_cost=Decimal("10.00"),
        )

        assert completed.completed_at is not None
        assert completed.labor_hours == Decimal("2.5")
        assert completed.total_cost == Decimal("85.00")

    def test_post_rework_to_gl(
        self, svc: SPCScrapReworkService, quality_roles: set[str], finance_roles: set[str]
    ) -> None:
        record = svc.record_rework(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ReworkReason.INCORRECT_ASSEMBLY,
            reason_detail="Components assembled backwards",
            station_id="STATION-A",
        )

        svc.complete_rework(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            rework_id=record.id,
            labor_hours=Decimal("1.0"),
            labor_cost=Decimal("30.00"),
        )

        posted = svc.post_rework_to_gl(
            actor_id="accountant1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            rework_id=record.id,
        )

        assert posted.gl_posted is True

    def test_cannot_post_incomplete_rework(
        self, svc: SPCScrapReworkService, quality_roles: set[str], finance_roles: set[str]
    ) -> None:
        record = svc.record_rework(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ReworkReason.SURFACE_FINISH,
            reason_detail="Surface too rough",
            station_id="STATION-A",
        )

        with pytest.raises(ValueError, match="not completed"):
            svc.post_rework_to_gl(
                actor_id="accountant1",
                actor_roles=finance_roles,
                correlation_id="cor-2",
                rework_id=record.id,
            )


# ============================================================
# COPQ Reporting Tests
# ============================================================


class TestCOPQReporting:
    def test_get_copq_summary(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        # Record some scrap
        svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.PROCESS_ERROR,
            reason_detail="Test scrap 1",
            station_id="STATION-A",
            material_cost=Decimal("100.00"),
        )
        svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            work_order_id="WO-002",
            product_id="PROD-002",
            lot_number="LOT-002",
            quantity=3,
            unit="pcs",
            reason=ScrapReason.MATERIAL_DEFECT,
            reason_detail="Test scrap 2",
            station_id="STATION-B",
            material_cost=Decimal("75.00"),
        )

        # Record and complete rework
        rework = svc.record_rework(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-3",
            work_order_id="WO-003",
            product_id="PROD-001",
            lot_number="LOT-003",
            quantity=10,
            unit="pcs",
            reason=ReworkReason.DIMENSIONAL_OOS,
            reason_detail="Test rework",
            station_id="STATION-A",
        )
        svc.complete_rework(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-4",
            rework_id=rework.id,
            labor_hours=Decimal("2.0"),
            labor_cost=Decimal("50.00"),
        )

        summary = svc.get_copq_summary(
            actor_roles=quality_roles,
            start_date=start,
            end_date=end,
        )

        assert summary.scrap_count == 2
        assert summary.rework_count == 1
        assert summary.total_scrap_cost == Decimal("175.00")
        assert summary.total_rework_cost == Decimal("50.00")
        assert summary.total_copq == Decimal("225.00")
        assert len(summary.by_station) == 2
        assert len(summary.by_product) == 2

    def test_list_scrap_records_by_station(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.PROCESS_ERROR,
            reason_detail="Test",
            station_id="STATION-A",
        )
        svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            work_order_id="WO-002",
            product_id="PROD-002",
            lot_number="LOT-002",
            quantity=3,
            unit="pcs",
            reason=ScrapReason.MATERIAL_DEFECT,
            reason_detail="Test",
            station_id="STATION-B",
        )

        records = svc.list_scrap_records(
            actor_roles=quality_roles, station_id="STATION-A"
        )
        assert len(records) == 1


# ============================================================
# Audit Tests
# ============================================================


class TestAudit:
    def test_audit_trail_for_spc_operations(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        chart = svc.create_control_chart(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            name="Test Chart",
            chart_type=ControlChartType.XBAR_R,
            characteristic="Length",
            station_id="STATION-A",
            ucl=10.1,
            lcl=9.9,
        )

        svc.record_measurement(
            actor_id="operator1",
            actor_roles=quality_roles,
            correlation_id="cor-2",
            chart_id=chart.id,
            value=10.5,  # Violation
        )

        events = svc.list_audit_events(actor_roles=quality_roles)

        actions = [e.action for e in events]
        assert "spc.chart.create" in actions
        assert "spc.measurement.record" in actions
        assert "spc.violation.detected" in actions

    def test_audit_trail_for_scrap_rework(
        self, svc: SPCScrapReworkService, quality_roles: set[str], finance_roles: set[str]
    ) -> None:
        scrap = svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=5,
            unit="pcs",
            reason=ScrapReason.PROCESS_ERROR,
            reason_detail="Test",
            station_id="STATION-A",
            material_cost=Decimal("100"),
        )

        svc.post_scrap_to_gl(
            actor_id="accountant1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            scrap_id=scrap.id,
        )

        events = svc.list_audit_events(actor_roles=quality_roles)

        actions = [e.action for e in events]
        assert "scrap.record" in actions
        assert "scrap.gl_post" in actions

    def test_audit_includes_correlation_id(
        self, svc: SPCScrapReworkService, quality_roles: set[str]
    ) -> None:
        svc.record_scrap(
            actor_id="quality1",
            actor_roles=quality_roles,
            correlation_id="trace-scrap999",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            quantity=1,
            unit="pcs",
            reason=ScrapReason.OTHER,
            reason_detail="Test",
            station_id="STATION-A",
        )

        events = svc.list_audit_events(actor_roles=quality_roles)

        assert any(e.correlation_id == "trace-scrap999" for e in events)

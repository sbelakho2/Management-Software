from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sensei.services.ops.ceo_control_plane import CEOControlPlaneService
from sensei.services.finance.cost_accounting import CostAccountingService
from sensei.services.finance.financial_operational_feedback import (
    FinancialOperationalFeedbackService,
    ReconciliationIssueType,
)
from sensei.services.finance.payroll_labor_costing import PayrollLaborCostingService


def _dt(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


OPS = {"ops"}
FINANCE = {"finance"}


def test_reconcile_skips_unknown_cost_center_and_records_issue() -> None:
    payroll = PayrollLaborCostingService()
    costs = CostAccountingService()

    costs.register_work_order(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c0",
        work_order_id="WO-1",
        finished_sku="FG-1",
        planned_quantity=Decimal("1"),
        currency="EUR",
    )

    payroll.set_station_cost_center(station_id="st-1", cost_center="CC-100", actor_roles=["finance"])

    # Force an explicit, unknown cost center
    payroll.record_labor_booking(
        employee_id="emp-1",
        station_id="st-1",
        started_at=_dt(2026, 1, 11, 8, 0),
        ended_at=_dt(2026, 1, 11, 10, 0),
        work_order_id="WO-1",
        cost_center="CC-999",
    )

    report = FinancialOperationalFeedbackService.reconcile_labor_bookings(
        payroll=payroll,
        cost_accounting=costs,
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c1",
        allowed_cost_centers={"CC-100"},
        default_hourly_rate=Decimal("10"),
    )

    assert report.total_bookings_seen == 1
    assert report.bookings_ingested == 0
    assert any(i.issue_type == ReconciliationIssueType.UNKNOWN_COST_CENTER for i in report.issues)


def test_reconcile_ingests_labor_with_employee_rate_and_updates_work_order_costs() -> None:
    payroll = PayrollLaborCostingService()
    costs = CostAccountingService()

    costs.register_work_order(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c0",
        work_order_id="WO-1",
        finished_sku="FG-1",
        planned_quantity=Decimal("1"),
        currency="EUR",
    )

    payroll.set_station_cost_center(station_id="st-1", cost_center="CC-100", actor_roles=["finance"])
    payroll.set_employee_hourly_rate(employee_id="emp-1", hourly_rate=50.0, actor_roles=["finance"])

    payroll.record_labor_booking(
        employee_id="emp-1",
        station_id="st-1",
        started_at=_dt(2026, 1, 11, 8, 0),
        ended_at=_dt(2026, 1, 11, 10, 0),
        work_order_id="WO-1",
        operation_id="OP-10",
    )

    report = FinancialOperationalFeedbackService.reconcile_labor_bookings(
        payroll=payroll,
        cost_accounting=costs,
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c1",
        allowed_cost_centers={"CC-100"},
        default_hourly_rate=Decimal("10"),
    )

    assert report.total_bookings_seen == 1
    assert report.bookings_ingested == 1

    st = costs.get_work_order(actor_roles=FINANCE, work_order_id="WO-1")
    assert st is not None
    assert st.actual_labor_cost == Decimal("100.00")


def test_variance_alert_triggered_when_actual_cogs_exceeds_threshold() -> None:
    payroll = PayrollLaborCostingService()
    costs = CostAccountingService()
    ceo = CEOControlPlaneService()

    costs.register_work_order(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c0",
        work_order_id="WO-1",
        finished_sku="FG-1",
        planned_quantity=Decimal("1"),
        currency="EUR",
    )

    payroll.set_station_cost_center(station_id="st-1", cost_center="CC-100", actor_roles=["finance"])
    payroll.set_employee_hourly_rate(employee_id="emp-1", hourly_rate=50.0, actor_roles=["finance"])

    payroll.record_labor_booking(
        employee_id="emp-1",
        station_id="st-1",
        started_at=_dt(2026, 1, 11, 8, 0),
        ended_at=_dt(2026, 1, 11, 10, 0),
        work_order_id="WO-1",
    )

    FinancialOperationalFeedbackService.reconcile_labor_bookings(
        payroll=payroll,
        cost_accounting=costs,
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c1",
        allowed_cost_centers={"CC-100"},
        default_hourly_rate=Decimal("10"),
    )

    svc = FinancialOperationalFeedbackService(ceo_control_plane=ceo)

    # Estimated 90, actual 100 => ~11.11% overrun => alert
    result = svc.evaluate_quote_cogs_variance_and_alert(
        role="ceo",
        quote_id="Q-1",
        estimated_cogs=Decimal("90.00"),
        cost_accounting=costs,
        actor_roles=FINANCE,
        work_order_ids=["WO-1"],
        threshold_pct=Decimal("0.10"),
        correlation_id="corr-1",
    )

    assert result is not None
    assert result.actual_cogs == Decimal("100.00")
    assert result.estimated_cogs == Decimal("90.00")
    assert float(result.deviation_pct) > 0.10

    alerts = ceo.list_variance_alerts("ceo")
    assert len(alerts) == 1
    assert alerts[0].quote_id == "Q-1"
    assert alerts[0].correlation_id == "corr-1"
    assert alerts[0].actual_cogs == 100.0

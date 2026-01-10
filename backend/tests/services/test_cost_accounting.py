from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sensei.services.accounting_ledger import AccountingLedgerService, AccountType
from sensei.services.cost_accounting import CostAccountingService, CostAccountingConfig


FINANCE = {"finance"}
OPS = {"ops"}
AUDIT = {"auditor"}


def _setup_minimal_coa(ledger: AccountingLedgerService) -> None:
    # Inventory/cost accounts used by CostAccountingConfig defaults
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="1200",
        name="WIP",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="1300",
        name="Finished Goods Inventory",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="5100",
        name="Material Variance",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="5200",
        name="Labor Variance",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="5300",
        name="Overhead Variance",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="6000",
        name="COGS",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )


def test_wip_rollup_from_material_labor_overhead():
    svc = CostAccountingService()

    svc.set_standard_cost(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c1",
        sku="FG-1",
        currency="EUR",
        effective_date=date(2026, 1, 1),
        material_unit_cost=Decimal("10"),
        labor_unit_cost=Decimal("5"),
        overhead_unit_cost=Decimal("2"),
    )

    svc.register_work_order(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c2",
        work_order_id="WO-1",
        finished_sku="FG-1",
        planned_quantity=Decimal("1"),
        currency="EUR",
    )

    svc.record_material_issue(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c3",
        work_order_id="WO-1",
        sku="RM-1",
        quantity=Decimal("1"),
        unit_cost=Decimal("11"),
    )
    svc.record_labor_booking(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c4",
        work_order_id="WO-1",
        hours=Decimal("0.5"),
        hourly_rate=Decimal("10"),
        operation_id="OP-10",
    )
    svc.record_overhead(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c5",
        work_order_id="WO-1",
        amount=Decimal("2"),
    )

    rows = svc.wip_valuation(actor_roles=AUDIT)
    assert len(rows) == 1
    assert rows[0].work_order_id == "WO-1"
    assert rows[0].wip_actual_cost == Decimal("18.00")  # 11 + 5 + 2


def test_completion_posts_variances_to_gl_and_creates_fg_inventory():
    ledger = AccountingLedgerService()
    _setup_minimal_coa(ledger)

    svc = CostAccountingService(config=CostAccountingConfig(base_currency="EUR"), ledger=ledger)

    svc.set_standard_cost(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c1",
        sku="FG-1",
        currency="EUR",
        effective_date=date(2026, 1, 1),
        material_unit_cost=Decimal("10"),
        labor_unit_cost=Decimal("5"),
        overhead_unit_cost=Decimal("2"),
    )

    svc.register_work_order(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c2",
        work_order_id="WO-1",
        finished_sku="FG-1",
        planned_quantity=Decimal("1"),
        currency="EUR",
    )

    # Actual costs: 18 (unfavorable variance vs standard 17)
    svc.record_material_issue(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c3",
        work_order_id="WO-1",
        sku="RM-1",
        quantity=Decimal("1"),
        unit_cost=Decimal("11"),
    )
    svc.record_labor_booking(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c4",
        work_order_id="WO-1",
        hours=Decimal("0.5"),
        hourly_rate=Decimal("10"),
    )
    svc.record_overhead(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c5",
        work_order_id="WO-1",
        amount=Decimal("2"),
    )

    receipt, variances = svc.receive_completion(
        actor_id="fin1",
        actor_roles=FINANCE,
        correlation_id="c6",
        work_order_id="WO-1",
        quantity_completed=Decimal("1"),
    )

    assert receipt.work_order_id == "WO-1"
    assert variances.total == Decimal("1.00")

    tb = {r.account_code: r for r in ledger.trial_balance(actor_roles=FINANCE, as_of=date(2026, 1, 10))}

    # FG inventory at standard 17
    assert tb["1300"].debit == Decimal("17.00")

    # WIP credited at actual 18 (asset credits show as credit)
    assert tb["1200"].credit == Decimal("18.00")

    # Total variance net debit 1
    variance_net = tb["5100"].debit - tb["5100"].credit + tb["5200"].debit - tb["5200"].credit + tb["5300"].debit - tb["5300"].credit
    assert variance_net == Decimal("1.00")


def test_cogs_and_margin_reporting():
    ledger = AccountingLedgerService()
    _setup_minimal_coa(ledger)

    svc = CostAccountingService(config=CostAccountingConfig(base_currency="EUR"), ledger=ledger)

    svc.set_standard_cost(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c1",
        sku="FG-1",
        currency="EUR",
        effective_date=date(2026, 1, 1),
        material_unit_cost=Decimal("10"),
        labor_unit_cost=Decimal("5"),
        overhead_unit_cost=Decimal("2"),
    )

    svc.register_work_order(
        actor_id="u1",
        actor_roles=OPS,
        correlation_id="c2",
        work_order_id="WO-1",
        finished_sku="FG-1",
        planned_quantity=Decimal("1"),
        currency="EUR",
    )

    svc.record_material_issue(actor_id="u1", actor_roles=OPS, correlation_id="c3", work_order_id="WO-1", sku="RM-1", quantity=Decimal("1"), unit_cost=Decimal("10"))
    svc.record_labor_booking(actor_id="u1", actor_roles=OPS, correlation_id="c4", work_order_id="WO-1", hours=Decimal("0.5"), hourly_rate=Decimal("10"))
    svc.record_overhead(actor_id="u1", actor_roles=OPS, correlation_id="c5", work_order_id="WO-1", amount=Decimal("2"))

    svc.receive_completion(actor_id="fin1", actor_roles=FINANCE, correlation_id="c6", work_order_id="WO-1", quantity_completed=Decimal("1"))

    # Ship at revenue 50
    svc.ship(
        actor_id="ship1",
        actor_roles={"shipping", "finance"},
        correlation_id="c7",
        customer_id="cust-1",
        sku="FG-1",
        quantity_shipped=Decimal("1"),
        revenue_total=Decimal("50"),
        currency="EUR",
        reference="INV-1",
    )

    rows = svc.margin_report(actor_roles=FINANCE, start=date(2026, 1, 1), end=date(2026, 1, 31))
    assert len(rows) == 1
    assert rows[0].revenue == Decimal("50.00")
    assert rows[0].cogs == Decimal("17.00")
    assert rows[0].margin == Decimal("33.00")

    tb = {r.account_code: r for r in ledger.trial_balance(actor_roles=FINANCE, as_of=date(2026, 1, 31))}
    assert tb["6000"].debit == Decimal("17.00")
    # Net FG inventory after completion+shipment is zero
    assert tb["1300"].debit == Decimal("0.00")
    assert tb["1300"].credit == Decimal("0.00")

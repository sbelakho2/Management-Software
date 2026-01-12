from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sensei.services.finance.accounting_ledger import AccountingLedgerService, AccountType
from sensei.services.finance.accounts_receivable import (
    AccountsReceivableService,
    ARConfig,
    SalesOrderLine,
)


FINANCE = {"finance"}
SALES = {"sales"}
VIEWER = {"auditor"}


def _approved_quote(**overrides):
    q = {
        "id": "q-1",
        "account_id": "cust-1",
        "currency": "EUR",
        "total": "100.00",
        "current_version": 1,
        "status": "sent",
        "approval_status": "approved",
    }
    q.update(overrides)
    return q


def test_quote_requires_approval_for_sales_order():
    ar = AccountsReceivableService()

    quote = _approved_quote(approval_status="pending")
    with pytest.raises(ValueError, match="Quote must be approved"):
        ar.create_sales_order_from_quote(
            actor_id="u1",
            actor_roles=SALES,
            correlation_id="c1",
            quote=quote,
            lines=[SalesOrderLine(sku="SKU", description="Item", quantity=Decimal("1"), unit_price=Decimal("10"))],
        )


def test_credit_limit_blocks_sales_order_approval():
    ar = AccountsReceivableService()
    ar.set_credit_profile(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c1",
        account_id="cust-1",
        credit_limit=Decimal("50"),
        currency="EUR",
    )

    so = ar.create_sales_order_from_quote(
        actor_id="u2",
        actor_roles=SALES,
        correlation_id="c2",
        quote=_approved_quote(),
        lines=[SalesOrderLine(sku="SKU", description="Item", quantity=Decimal("1"), unit_price=Decimal("100"))],
    )

    with pytest.raises(ValueError, match="Credit limit exceeded"):
        ar.approve_sales_order(actor_id="u3", actor_roles=FINANCE, correlation_id="c3", sales_order_id=so.id)


def test_credit_limit_override_requires_reason_and_allows_approval():
    ar = AccountsReceivableService()
    ar.set_credit_profile(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c1",
        account_id="cust-1",
        credit_limit=Decimal("50"),
        currency="EUR",
    )

    so = ar.create_sales_order_from_quote(
        actor_id="u2",
        actor_roles=SALES,
        correlation_id="c2",
        quote=_approved_quote(),
        lines=[SalesOrderLine(sku="SKU", description="Item", quantity=Decimal("1"), unit_price=Decimal("100"))],
    )

    with pytest.raises(ValueError, match="override_reason required"):
        ar.approve_sales_order(
            actor_id="fin1",
            actor_roles=FINANCE,
            correlation_id="c3",
            sales_order_id=so.id,
            override_credit=True,
        )

    approved = ar.approve_sales_order(
        actor_id="fin1",
        actor_roles=FINANCE,
        correlation_id="c4",
        sales_order_id=so.id,
        override_credit=True,
        override_reason="Strategic customer; approved by finance",
    )
    assert approved.status.value == "approved"
    assert approved.metadata.get("credit_override") is True


def test_end_to_end_invoice_payment_and_aging_and_gl_postings():
    ledger = AccountingLedgerService()

    # Minimal chart of accounts expected by ARConfig defaults
    ledger.upsert_account(
        actor_id="u1",
        actor_roles={"finance"},
        correlation_id="c0",
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles={"finance"},
        correlation_id="c0",
        code="1100",
        name="Accounts Receivable",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles={"finance"},
        correlation_id="c0",
        code="4000",
        name="Revenue",
        account_type=AccountType.REVENUE,
        currency="EUR",
    )

    ar = AccountsReceivableService(config=ARConfig(base_currency="EUR"), ledger=ledger)

    so = ar.create_sales_order_from_quote(
        actor_id="sales1",
        actor_roles=SALES,
        correlation_id="c1",
        quote=_approved_quote(total="100.00"),
        lines=[SalesOrderLine(sku="SKU", description="Item", quantity=Decimal("2"), unit_price=Decimal("50"))],
        payment_terms_days=30,
    )

    ar.approve_sales_order(actor_id="fin1", actor_roles=FINANCE, correlation_id="c2", sales_order_id=so.id)
    ar.release_sales_order(actor_id="fin1", actor_roles=FINANCE, correlation_id="c3", sales_order_id=so.id)

    inv = ar.create_invoice_from_sales_order(
        actor_id="fin1",
        actor_roles=FINANCE,
        correlation_id="c4",
        sales_order_id=so.id,
        issue_date=date(2026, 1, 1),
    )

    assert inv.total == Decimal("100.00")
    assert ar.invoice_balance(actor_roles=VIEWER, invoice_id=inv.id) == Decimal("100.00")

    # Aging should place it in overdue bucket as-of Mar 15 (past due > 30 days)
    aging = ar.ar_aging(actor_roles=VIEWER, as_of=date(2026, 3, 15), account_id="cust-1")
    assert aging["31_60"] == Decimal("100.00")

    pay = ar.record_payment(
        actor_id="fin1",
        actor_roles=FINANCE,
        correlation_id="c5",
        account_id="cust-1",
        currency="EUR",
        amount=Decimal("100.00"),
        reference="bank-123",
    )

    assert pay.amount == Decimal("100.00")
    assert ar.invoice_balance(actor_roles=VIEWER, invoice_id=inv.id) == Decimal("0.00")

    # GL sanity: revenue should be credited 100, cash debited 100
    tb_rows = ledger.trial_balance(actor_roles={"finance"}, as_of=date(2026, 3, 15))
    by_code = {r.account_code: r for r in tb_rows}

    assert by_code["4000"].credit == Decimal("100.00")
    assert by_code["1000"].debit == Decimal("100.00")
    # AR nets to zero after invoice+receipt
    assert by_code["1100"].debit == Decimal("0.00")
    assert by_code["1100"].credit == Decimal("0.00")

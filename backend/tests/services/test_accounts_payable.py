from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from sensei.services.accounting_ledger import AccountingLedgerService, AccountType
from sensei.services.accounts_payable import (
    AccountsPayableService,
    APConfig,
    PRLine,
    ReceiptLine,
    SupplierInvoiceLine,
)


FINANCE = {"finance"}
BUYER = {"buyer"}
AUDIT = {"auditor"}


def _setup_minimal_coa(ledger: AccountingLedgerService) -> None:
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="2000",
        name="Accounts Payable",
        account_type=AccountType.LIABILITY,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="u1",
        actor_roles=FINANCE,
        correlation_id="c0",
        code="5000",
        name="Expense",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )


def test_pr_must_be_approved_before_po_creation():
    ap = AccountsPayableService()

    pr = ap.create_requisition(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c1",
        requested_by="req1",
        currency="EUR",
        supplier_id="sup-1",
        cost_center="CC-1",
        lines=[PRLine(sku="MAT", description="Material", quantity=Decimal("10"), unit_price=Decimal("2"))],
    )

    with pytest.raises(ValueError, match="PR must be approved"):
        ap.create_po_from_requisition(
            actor_id="buyer1",
            actor_roles=BUYER,
            correlation_id="c2",
            pr_id=pr.id,
        )

    ap.submit_requisition(actor_id="buyer1", actor_roles=BUYER, correlation_id="c3", pr_id=pr.id)
    ap.approve_requisition(actor_id="fin1", actor_roles=FINANCE, correlation_id="c4", pr_id=pr.id)

    po = ap.create_po_from_requisition(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c5",
        pr_id=pr.id,
    )

    ap.approve_po(actor_id="fin1", actor_roles=FINANCE, correlation_id="c6", po_id=po.id)
    ap.send_po(actor_id="buyer1", actor_roles=BUYER, correlation_id="c7", po_id=po.id)

    assert po.supplier_id == "sup-1"
    assert po.total == Decimal("20.00")


def test_three_way_match_blocks_invoice_without_override():
    ap = AccountsPayableService()

    pr = ap.create_requisition(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c1",
        requested_by="req1",
        currency="EUR",
        supplier_id="sup-1",
        cost_center="CC-1",
        lines=[PRLine(sku="MAT", description="Material", quantity=Decimal("10"), unit_price=Decimal("2"))],
    )
    ap.submit_requisition(actor_id="buyer1", actor_roles=BUYER, correlation_id="c2", pr_id=pr.id)
    ap.approve_requisition(actor_id="fin1", actor_roles=FINANCE, correlation_id="c3", pr_id=pr.id)
    po = ap.create_po_from_requisition(actor_id="buyer1", actor_roles=BUYER, correlation_id="c4", pr_id=pr.id)
    ap.approve_po(actor_id="fin1", actor_roles=FINANCE, correlation_id="c5", po_id=po.id)
    ap.send_po(actor_id="buyer1", actor_roles=BUYER, correlation_id="c6", po_id=po.id)

    # Receive only 5 units
    ap.receive_goods(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c7",
        po_id=po.id,
        lines=[ReceiptLine(sku="MAT", quantity_received=Decimal("5"))],
    )

    inv = ap.create_supplier_invoice(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c8",
        supplier_id="sup-1",
        supplier_invoice_number="INV-1",
        invoice_date=date(2026, 1, 1),
        currency="EUR",
        due_date=None,
        po_id=po.id,
        lines=[SupplierInvoiceLine(sku="MAT", description="Material", quantity=Decimal("10"), unit_price=Decimal("2"))],
    )
    ap.submit_supplier_invoice(actor_id="buyer1", actor_roles=BUYER, correlation_id="c9", invoice_id=inv.id)

    with pytest.raises(ValueError, match="3-way match failed"):
        ap.approve_supplier_invoice(actor_id="fin1", actor_roles=FINANCE, correlation_id="c10", invoice_id=inv.id)

    with pytest.raises(ValueError, match="exception_override_reason required"):
        ap.approve_supplier_invoice(
            actor_id="fin1",
            actor_roles=FINANCE,
            correlation_id="c11",
            invoice_id=inv.id,
            allow_exceptions=True,
        )

    approved = ap.approve_supplier_invoice(
        actor_id="fin1",
        actor_roles=FINANCE,
        correlation_id="c12",
        invoice_id=inv.id,
        allow_exceptions=True,
        exception_override_reason="Urgent shipment; accept partial receipt timing",
    )

    assert approved.metadata.get("three_way_match_override") is True


def test_invoice_post_and_payment_run_post_to_gl():
    ledger = AccountingLedgerService()
    _setup_minimal_coa(ledger)

    ap = AccountsPayableService(config=APConfig(base_currency="EUR"), ledger=ledger)

    pr = ap.create_requisition(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c1",
        requested_by="req1",
        currency="EUR",
        supplier_id="sup-1",
        cost_center="CC-1",
        lines=[PRLine(sku="MAT", description="Material", quantity=Decimal("10"), unit_price=Decimal("2"))],
    )
    ap.submit_requisition(actor_id="buyer1", actor_roles=BUYER, correlation_id="c2", pr_id=pr.id)
    ap.approve_requisition(actor_id="fin1", actor_roles=FINANCE, correlation_id="c3", pr_id=pr.id)
    po = ap.create_po_from_requisition(actor_id="buyer1", actor_roles=BUYER, correlation_id="c4", pr_id=pr.id)
    ap.approve_po(actor_id="fin1", actor_roles=FINANCE, correlation_id="c5", po_id=po.id)
    ap.send_po(actor_id="buyer1", actor_roles=BUYER, correlation_id="c6", po_id=po.id)
    ap.receive_goods(actor_id="buyer1", actor_roles=BUYER, correlation_id="c7", po_id=po.id, lines=[ReceiptLine(sku="MAT", quantity_received=Decimal("10"))])

    inv = ap.create_supplier_invoice(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c8",
        supplier_id="sup-1",
        supplier_invoice_number="INV-1",
        invoice_date=date(2026, 1, 1),
        currency="EUR",
        due_date=None,
        po_id=po.id,
        lines=[SupplierInvoiceLine(sku="MAT", description="Material", quantity=Decimal("10"), unit_price=Decimal("2"))],
    )

    ap.submit_supplier_invoice(actor_id="buyer1", actor_roles=BUYER, correlation_id="c9", invoice_id=inv.id)
    ap.approve_supplier_invoice(actor_id="fin1", actor_roles=FINANCE, correlation_id="c10", invoice_id=inv.id)
    ap.post_supplier_invoice(actor_id="fin1", actor_roles=FINANCE, correlation_id="c11", invoice_id=inv.id)

    payrun = ap.create_payment_run(
        actor_id="buyer1",
        actor_roles=BUYER,
        correlation_id="c12",
        invoice_ids=[inv.id],
        currency="EUR",
    )
    ap.approve_payment_run(actor_id="fin1", actor_roles=FINANCE, correlation_id="c13", payrun_id=payrun.id)
    ap.execute_payment_run(actor_id="fin1", actor_roles=FINANCE, correlation_id="c14", payrun_id=payrun.id, reference="bank-file-1")

    tb_rows = ledger.trial_balance(actor_roles=FINANCE, as_of=date(2026, 1, 10))
    by_code = {r.account_code: r for r in tb_rows}

    # Expense debited, cash credited, AP nets to zero after invoice+payment
    assert by_code["5000"].debit == Decimal("20.00")
    assert by_code["1000"].credit == Decimal("20.00")
    assert by_code["2000"].debit == Decimal("0.00")
    assert by_code["2000"].credit == Decimal("0.00")

    # Read RBAC sanity
    assert ap.get_supplier_invoice(actor_roles=AUDIT, invoice_id=inv.id) is not None

"""
ERP Integration Service.

Provides integration points with external ERP systems.
Manages data synchronization, transaction mapping, and
error handling for bi-directional ERP communication.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sensei.models.accounts_receivable import SalesOrder, CustomerInvoice, SalesOrderLine, CustomerInvoiceLine
from sensei.models.accounts_payable import PurchaseOrder, SupplierInvoice, POLine, SupplierInvoiceLine
from sensei.models.finance import JournalEntry, JournalLine, GLAccount
from sensei.models.product import Product
from sensei.services.event_bus import event_bus
from sensei.services.domain_events import InvoiceCreatedEvent

class ERPIntegrationService:
    """
    Handles automated workflows between different ERP modules.
    """

    @staticmethod
    async def create_invoice_from_so(db: AsyncSession, so_id: UUID) -> CustomerInvoice:
        """Create a customer invoice from a sales order."""
        result = await db.execute(
            select(SalesOrder).where(SalesOrder.id == so_id).options(selectinload(SalesOrder.lines))
        )
        so = result.scalar_one()
        
        # Compute due date from payment terms (default Net-30)
        payment_term_days = getattr(so, "payment_term_days", None) or 30
        due = date.today() + timedelta(days=payment_term_days)

        invoice = CustomerInvoice(
            account_id=so.account_id,
            currency=so.currency,
            issued_at=datetime.now(timezone.utc),
            due_date=due,
            sales_order_id=so.id,
            status="draft"
        )
        db.add(invoice)
        await db.flush() # Get invoice ID
        
        for line in so.lines:
            inv_line = CustomerInvoiceLine(
                invoice_id=invoice.id,
                sku=line.sku,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price
            )
            db.add(inv_line)
        
        so.status = "closed"

        # Publish domain event — feeds single data thread + analytics
        total = sum(float(line.quantity * line.unit_price) for line in so.lines)
        await event_bus.publish(InvoiceCreatedEvent(
            invoice_id=str(invoice.id),
            invoice_type="receivable",
            amount=total,
            currency=so.currency or "USD",
            counterparty=str(so.account_id) if so.account_id else "",
        ))

        return invoice

    @staticmethod
    async def post_invoice_to_gl(db: AsyncSession, invoice_id: UUID, ar_account_code: str, revenue_account_code: str):
        """Post a customer invoice to the General Ledger."""
        from sensei.services.finance.gl_posting import _get_fx_rate, _get_base_currency

        result = await db.execute(
            select(CustomerInvoice).where(CustomerInvoice.id == invoice_id).options(selectinload(CustomerInvoice.lines))
        )
        invoice = result.scalar_one()
        
        total_amount = sum(line.quantity * line.unit_price for line in invoice.lines)

        # H3 fix: convert to base currency using FX rate
        base_currency = await _get_base_currency(db)
        today = date.today()
        fx_rate = await _get_fx_rate(db, invoice.currency, base_currency, today)
        amount_base = total_amount * fx_rate
        
        entry = JournalEntry(
            reference=f"INV-{invoice.invoice_number}",
            entry_date=today,
            description=f"Sales Invoice {invoice.invoice_number}",
            status="posted"
        )
        db.add(entry)
        await db.flush()
        
        # Debit A/R
        ar_acc = await db.scalar(select(GLAccount).where(GLAccount.account_code == ar_account_code))
        if ar_acc is None:
            raise ValueError(f"GL Account not found: {ar_account_code}")
        debit_line = JournalLine(
            entry_id=entry.id,
            account_id=ar_acc.id,
            debit=total_amount,
            credit=Decimal("0"),
            currency=invoice.currency,
            amount_base=amount_base,
        )
        db.add(debit_line)
        
        # Credit Revenue
        rev_acc = await db.scalar(select(GLAccount).where(GLAccount.account_code == revenue_account_code))
        if rev_acc is None:
            raise ValueError(f"GL Account not found: {revenue_account_code}")
        credit_line = JournalLine(
            entry_id=entry.id,
            account_id=rev_acc.id,
            debit=Decimal("0"),
            credit=total_amount,
            currency=invoice.currency,
            amount_base=-amount_base,
        )
        db.add(credit_line)
        
        invoice.status = "posted"
        await db.flush()

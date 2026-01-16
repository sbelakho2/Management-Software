from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sensei.models.accounts_receivable import SalesOrder, CustomerInvoice, SalesOrderLine, CustomerInvoiceLine
from sensei.models.accounts_payable import PurchaseOrder, SupplierInvoice, POLine, SupplierInvoiceLine
from sensei.models.finance import JournalEntry, JournalLine, GLAccount
from sensei.models.inventory import StockMove, InventoryLevel
from sensei.models.product import Product

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
        
        invoice = CustomerInvoice(
            account_id=so.account_id,
            currency=so.currency,
            issued_at=datetime.utcnow(),
            due_date=date.today(), # Should be based on payment terms
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
        return invoice

    @staticmethod
    async def post_invoice_to_gl(db: AsyncSession, invoice_id: UUID, ar_account_code: str, revenue_account_code: str):
        """Post a customer invoice to the General Ledger."""
        result = await db.execute(
            select(CustomerInvoice).where(CustomerInvoice.id == invoice_id).options(selectinload(CustomerInvoice.lines))
        )
        invoice = result.scalar_one()
        
        total_amount = sum(line.quantity * line.unit_price for line in invoice.lines)
        
        entry = JournalEntry(
            reference=f"INV-{invoice.invoice_number}",
            entry_date=date.today(),
            description=f"Sales Invoice {invoice.invoice_number}",
            status="posted"
        )
        db.add(entry)
        await db.flush()
        
        # Debit A/R
        ar_acc = await db.scalar(select(GLAccount).where(GLAccount.account_code == ar_account_code))
        debit_line = JournalLine(
            entry_id=entry.id,
            account_id=ar_acc.id,
            debit=total_amount,
            credit=Decimal("0"),
            currency=invoice.currency,
            amount_base=total_amount # Simplified
        )
        db.add(debit_line)
        
        # Credit Revenue
        rev_acc = await db.scalar(select(GLAccount).where(GLAccount.account_code == revenue_account_code))
        credit_line = JournalLine(
            entry_id=entry.id,
            account_id=rev_acc.id,
            debit=Decimal("0"),
            credit=total_amount,
            currency=invoice.currency,
            amount_base=total_amount
        )
        db.add(credit_line)
        
        invoice.status = "posted"
        await db.commit()

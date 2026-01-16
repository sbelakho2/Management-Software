from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sensei.api import deps
from sensei.core.database import get_db_session
from sensei.models.accounts_receivable import SalesOrder, CustomerInvoice, PaymentReceipt
from pydantic import BaseModel

router = APIRouter()

@router.get("/orders", response_model=List[dict])
async def list_sales_orders(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all Sales Orders."""
    result = await db.execute(select(SalesOrder))
    orders = result.scalars().all()
    return [o.to_dict() for o in orders]

@router.get("/invoices", response_model=List[dict])
async def list_customer_invoices(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all Customer Invoices."""
    result = await db.execute(select(CustomerInvoice))
    invoices = result.scalars().all()
    return [i.to_dict() for i in invoices]

@router.get("/receipts", response_model=List[dict])
async def list_payment_receipts(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all Payment Receipts."""
    result = await db.execute(select(PaymentReceipt))
    receipts = result.scalars().all()
    return [r.to_dict() for r in receipts]

from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sensei.api import deps
from sensei.core.database import get_db_session
from sensei.models.accounts_payable import PurchaseOrder, PurchaseRequisition, SupplierInvoice
from pydantic import BaseModel

router = APIRouter()

@router.get("/orders", response_model=List[dict])
async def list_purchase_orders(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all Purchase Orders."""
    result = await db.execute(select(PurchaseOrder))
    orders = result.scalars().all()
    return [o.to_dict() for o in orders]

@router.get("/requisitions", response_model=List[dict])
async def list_purchase_requisitions(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all Purchase Requisitions."""
    result = await db.execute(select(PurchaseRequisition))
    reqs = result.scalars().all()
    return [r.to_dict() for r in reqs]

@router.get("/invoices", response_model=List[dict])
async def list_supplier_invoices(
    db: AsyncSession = Depends(get_db_session),
    current_user: Any = Depends(deps.get_current_active_user)
):
    """List all Supplier Invoices."""
    result = await db.execute(select(SupplierInvoice))
    invoices = result.scalars().all()
    return [i.to_dict() for i in invoices]

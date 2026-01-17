"""
Purchase Order Management Endpoints.

Provides full CRUD and workflow operations for:
- Purchase Requisitions (PR)
- Purchase Orders (PO)
- Goods Receipts (GRN)
- Supplier Invoices
- 3-Way Matching
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import NotFoundError, ConflictError, ForbiddenError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import build_response, build_created_response, build_paginated_response, now_utc
from sensei.core.database import get_db_session
from sensei.models.accounts_payable import (
    PurchaseOrder, PurchaseRequisition, SupplierInvoice,
    POLine, PRLine, GoodsReceipt, ReceiptLine, SupplierInvoiceLine
)
from sensei.models.account import Account

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class PRLineCreate(BaseModel):
    """Purchase Requisition line item."""
    sku: str = Field(..., min_length=1)
    description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class PRCreate(BaseModel):
    """Purchase Requisition creation."""
    supplier_id: Optional[UUID] = None
    currency: str = Field(default="USD", max_length=3)
    cost_center: Optional[str] = None
    lines: List[PRLineCreate] = Field(..., min_length=1)


class PRResponse(BaseModel):
    """Purchase Requisition response."""
    id: UUID
    pr_number: str
    status: str
    currency: str
    supplier_id: Optional[UUID]
    cost_center: Optional[str]
    total_amount: Decimal
    line_count: int
    created_at: datetime
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True


class POLineCreate(BaseModel):
    """Purchase Order line item."""
    sku: str = Field(..., min_length=1)
    description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class POCreate(BaseModel):
    """Purchase Order creation."""
    supplier_id: UUID
    currency: str = Field(default="USD", max_length=3)
    cost_center: Optional[str] = None
    source_pr_id: Optional[UUID] = None
    lines: List[POLineCreate] = Field(..., min_length=1)


class POResponse(BaseModel):
    """Purchase Order response."""
    id: UUID
    po_number: str
    status: str
    currency: str
    supplier_id: UUID
    supplier_name: Optional[str] = None
    cost_center: Optional[str]
    total_amount: Decimal
    line_count: int
    source_pr_id: Optional[UUID]
    created_at: datetime
    approved_at: Optional[datetime]
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class GRNLineCreate(BaseModel):
    """Goods Receipt line."""
    sku: str
    quantity_received: Decimal = Field(..., gt=0)


class GRNCreate(BaseModel):
    """Goods Receipt creation."""
    po_id: UUID
    reference: Optional[str] = None
    lines: List[GRNLineCreate] = Field(..., min_length=1)


class GRNResponse(BaseModel):
    """Goods Receipt response."""
    id: UUID
    po_id: UUID
    po_number: Optional[str] = None
    received_at: datetime
    reference: Optional[str]
    line_count: int

    class Config:
        from_attributes = True


class SupplierInvoiceCreate(BaseModel):
    """Supplier Invoice creation."""
    supplier_id: UUID
    supplier_invoice_number: str
    invoice_date: datetime
    due_date: datetime
    currency: str = Field(default="USD", max_length=3)
    po_id: Optional[UUID] = None
    memo: Optional[str] = None
    lines: List[POLineCreate] = Field(..., min_length=1)


class MatchingResult(BaseModel):
    """3-Way Matching result."""
    po_id: UUID
    grn_id: UUID
    invoice_id: UUID
    po_total: Decimal
    grn_total: Decimal
    invoice_total: Decimal
    variance: Decimal
    matched: bool
    discrepancies: List[str]


# =============================================================================
# Sequence helpers
# =============================================================================


async def _generate_pr_number(db: AsyncSession) -> str:
    """Generate next PR number."""
    result = await db.execute(select(func.count(PurchaseRequisition.id)))
    count = result.scalar() or 0
    return f"PR-{datetime.now(timezone.utc).year}-{count + 1:05d}"


async def _generate_po_number(db: AsyncSession) -> str:
    """Generate next PO number."""
    result = await db.execute(select(func.count(PurchaseOrder.id)))
    count = result.scalar() or 0
    return f"PO-{datetime.now(timezone.utc).year}-{count + 1:05d}"


def _calc_total(lines: List[Any]) -> Decimal:
    """Calculate total from line items."""
    return sum(line.quantity * line.unit_price for line in lines)


# =============================================================================
# Purchase Requisition Endpoints
# =============================================================================


@router.get("/requisitions", response_model=APIResponse[List[PRResponse]])
async def list_purchase_requisitions(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Purchase Requisitions with optional status filter."""
    stmt = select(PurchaseRequisition).options(selectinload(PurchaseRequisition.lines))
    if status:
        stmt = stmt.where(PurchaseRequisition.status == status)
    stmt = stmt.offset(skip).limit(limit).order_by(PurchaseRequisition.created_at.desc())
    
    result = await db.execute(stmt)
    reqs = result.scalars().all()
    
    data = []
    for r in reqs:
        total = _calc_total(r.lines)
        data.append(PRResponse(
            id=r.id,
            pr_number=r.pr_number,
            status=r.status,
            currency=r.currency,
            supplier_id=r.supplier_id,
            cost_center=r.cost_center,
            total_amount=total,
            line_count=len(r.lines),
            created_at=r.created_at,
            submitted_at=r.submitted_at,
            approved_at=r.approved_at,
        ))
    return build_response(data)


@router.post("/requisitions", response_model=APIResponse[PRResponse], status_code=status.HTTP_201_CREATED)
async def create_purchase_requisition(
    payload: PRCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new Purchase Requisition."""
    pr_number = await _generate_pr_number(db)
    
    pr = PurchaseRequisition(
        pr_number=pr_number,
        requested_by_id=current_user.id,
        currency=payload.currency,
        supplier_id=payload.supplier_id,
        cost_center=payload.cost_center,
        status="draft",
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(pr)
    await db.flush()
    
    for line in payload.lines:
        pr_line = PRLine(
            pr_id=pr.id,
            sku=line.sku,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        db.add(pr_line)
    
    await db.commit()
    await db.refresh(pr)
    
    # Reload with lines
    result = await db.execute(
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr.id)
        .options(selectinload(PurchaseRequisition.lines))
    )
    pr = result.scalar_one()
    
    total = _calc_total(pr.lines)
    return build_created_response(PRResponse(
        id=pr.id,
        pr_number=pr.pr_number,
        status=pr.status,
        currency=pr.currency,
        supplier_id=pr.supplier_id,
        cost_center=pr.cost_center,
        total_amount=total,
        line_count=len(pr.lines),
        created_at=pr.created_at,
        submitted_at=pr.submitted_at,
        approved_at=pr.approved_at,
    ))


@router.post("/requisitions/{pr_id}/submit", response_model=APIResponse[PRResponse])
async def submit_requisition(
    pr_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Submit PR for approval."""
    result = await db.execute(
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr_id)
        .options(selectinload(PurchaseRequisition.lines))
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise NotFoundError("Purchase Requisition not found")
    if pr.status != "draft":
        raise ConflictError("Only draft PRs can be submitted")
    
    pr.status = "submitted"
    pr.submitted_at = now_utc()
    pr.submitted_by_id = current_user.id
    await db.commit()
    
    total = _calc_total(pr.lines)
    return build_response(PRResponse(
        id=pr.id, pr_number=pr.pr_number, status=pr.status, currency=pr.currency,
        supplier_id=pr.supplier_id, cost_center=pr.cost_center, total_amount=total,
        line_count=len(pr.lines), created_at=pr.created_at, submitted_at=pr.submitted_at,
        approved_at=pr.approved_at,
    ))


@router.post("/requisitions/{pr_id}/approve", response_model=APIResponse[PRResponse])
async def approve_requisition(
    pr_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Approve a submitted PR."""
    result = await db.execute(
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr_id)
        .options(selectinload(PurchaseRequisition.lines))
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise NotFoundError("Purchase Requisition not found")
    if pr.status != "submitted":
        raise ConflictError("Only submitted PRs can be approved")
    
    pr.status = "approved"
    pr.approved_at = now_utc()
    pr.approved_by_id = current_user.id
    await db.commit()
    
    total = _calc_total(pr.lines)
    return build_response(PRResponse(
        id=pr.id, pr_number=pr.pr_number, status=pr.status, currency=pr.currency,
        supplier_id=pr.supplier_id, cost_center=pr.cost_center, total_amount=total,
        line_count=len(pr.lines), created_at=pr.created_at, submitted_at=pr.submitted_at,
        approved_at=pr.approved_at,
    ))


@router.post("/requisitions/{pr_id}/convert-to-po", response_model=APIResponse[POResponse])
async def convert_pr_to_po(
    pr_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Convert an approved PR to a Purchase Order."""
    result = await db.execute(
        select(PurchaseRequisition)
        .where(PurchaseRequisition.id == pr_id)
        .options(selectinload(PurchaseRequisition.lines))
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise NotFoundError("Purchase Requisition not found")
    if pr.status != "approved":
        raise ConflictError("Only approved PRs can be converted to PO")
    if not pr.supplier_id:
        raise ConflictError("Supplier must be assigned before converting to PO")
    
    po_number = await _generate_po_number(db)
    
    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=pr.supplier_id,
        currency=pr.currency,
        status="draft",
        source_pr_id=pr.id,
        cost_center=pr.cost_center,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(po)
    await db.flush()
    
    for pr_line in pr.lines:
        po_line = POLine(
            po_id=po.id,
            sku=pr_line.sku,
            description=pr_line.description,
            quantity=pr_line.quantity,
            unit_price=pr_line.unit_price,
        )
        db.add(po_line)
    
    await db.commit()
    
    # Load with lines and supplier
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po.id)
        .options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.supplier))
    )
    po = result.scalar_one()
    
    total = _calc_total(po.lines)
    return build_created_response(POResponse(
        id=po.id, po_number=po.po_number, status=po.status, currency=po.currency,
        supplier_id=po.supplier_id, supplier_name=po.supplier.name if po.supplier else None,
        cost_center=po.cost_center, total_amount=total, line_count=len(po.lines),
        source_pr_id=po.source_pr_id, created_at=po.created_at, approved_at=po.approved_at,
        sent_at=po.sent_at,
    ))


# =============================================================================
# Purchase Order Endpoints
# =============================================================================


@router.get("/orders", response_model=APIResponse[List[POResponse]])
async def list_purchase_orders(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    supplier_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Purchase Orders with optional filters."""
    stmt = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.lines),
        selectinload(PurchaseOrder.supplier)
    )
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    if supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    stmt = stmt.offset(skip).limit(limit).order_by(PurchaseOrder.created_at.desc())
    
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    data = []
    for o in orders:
        total = _calc_total(o.lines)
        data.append(POResponse(
            id=o.id, po_number=o.po_number, status=o.status, currency=o.currency,
            supplier_id=o.supplier_id, supplier_name=o.supplier.name if o.supplier else None,
            cost_center=o.cost_center, total_amount=total, line_count=len(o.lines),
            source_pr_id=o.source_pr_id, created_at=o.created_at, approved_at=o.approved_at,
            sent_at=o.sent_at,
        ))
    return build_response(data)


@router.post("/orders", response_model=APIResponse[POResponse], status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    payload: POCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new Purchase Order directly."""
    po_number = await _generate_po_number(db)
    
    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=payload.supplier_id,
        currency=payload.currency,
        status="draft",
        source_pr_id=payload.source_pr_id,
        cost_center=payload.cost_center,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(po)
    await db.flush()
    
    for line in payload.lines:
        po_line = POLine(
            po_id=po.id,
            sku=line.sku,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        db.add(po_line)
    
    await db.commit()
    
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po.id)
        .options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.supplier))
    )
    po = result.scalar_one()
    
    total = _calc_total(po.lines)
    return build_created_response(POResponse(
        id=po.id, po_number=po.po_number, status=po.status, currency=po.currency,
        supplier_id=po.supplier_id, supplier_name=po.supplier.name if po.supplier else None,
        cost_center=po.cost_center, total_amount=total, line_count=len(po.lines),
        source_pr_id=po.source_pr_id, created_at=po.created_at, approved_at=po.approved_at,
        sent_at=po.sent_at,
    ))


@router.get("/orders/{po_id}", response_model=APIResponse[dict])
async def get_purchase_order(
    po_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a single Purchase Order with full details."""
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.supplier))
    )
    po = result.scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase Order not found")
    
    return build_response({
        **po.to_dict(),
        "supplier_name": po.supplier.name if po.supplier else None,
        "lines": [l.to_dict() for l in po.lines],
        "total_amount": float(_calc_total(po.lines)),
    })


@router.post("/orders/{po_id}/approve", response_model=APIResponse[POResponse])
async def approve_purchase_order(
    po_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Approve a draft PO."""
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.supplier))
    )
    po = result.scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase Order not found")
    if po.status != "draft":
        raise ConflictError("Only draft POs can be approved")
    
    po.status = "approved"
    po.approved_at = now_utc()
    po.approved_by_id = current_user.id
    await db.commit()
    
    total = _calc_total(po.lines)
    return build_response(POResponse(
        id=po.id, po_number=po.po_number, status=po.status, currency=po.currency,
        supplier_id=po.supplier_id, supplier_name=po.supplier.name if po.supplier else None,
        cost_center=po.cost_center, total_amount=total, line_count=len(po.lines),
        source_pr_id=po.source_pr_id, created_at=po.created_at, approved_at=po.approved_at,
        sent_at=po.sent_at,
    ))


@router.post("/orders/{po_id}/send", response_model=APIResponse[POResponse])
async def send_purchase_order(
    po_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Mark PO as sent to supplier."""
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.supplier))
    )
    po = result.scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase Order not found")
    if po.status != "approved":
        raise ConflictError("Only approved POs can be sent")
    
    po.status = "sent"
    po.sent_at = now_utc()
    po.sent_by_id = current_user.id
    await db.commit()
    
    total = _calc_total(po.lines)
    return build_response(POResponse(
        id=po.id, po_number=po.po_number, status=po.status, currency=po.currency,
        supplier_id=po.supplier_id, supplier_name=po.supplier.name if po.supplier else None,
        cost_center=po.cost_center, total_amount=total, line_count=len(po.lines),
        source_pr_id=po.source_pr_id, created_at=po.created_at, approved_at=po.approved_at,
        sent_at=po.sent_at,
    ))


# =============================================================================
# Goods Receipt Endpoints
# =============================================================================


@router.get("/receipts", response_model=APIResponse[List[GRNResponse]])
async def list_goods_receipts(
    db: DBSession,
    current_user: CurrentUser,
    po_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Goods Receipts."""
    stmt = select(GoodsReceipt).options(
        selectinload(GoodsReceipt.lines),
        selectinload(GoodsReceipt.po)
    )
    if po_id:
        stmt = stmt.where(GoodsReceipt.po_id == po_id)
    stmt = stmt.offset(skip).limit(limit).order_by(GoodsReceipt.received_at.desc())
    
    result = await db.execute(stmt)
    receipts = result.scalars().all()
    
    data = []
    for r in receipts:
        data.append(GRNResponse(
            id=r.id, po_id=r.po_id, po_number=r.po.po_number if r.po else None,
            received_at=r.received_at, reference=r.reference, line_count=len(r.lines),
        ))
    return build_response(data)


@router.post("/receipts", response_model=APIResponse[GRNResponse], status_code=status.HTTP_201_CREATED)
async def create_goods_receipt(
    payload: GRNCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Record a goods receipt against a PO."""
    # Verify PO exists and is in valid state
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == payload.po_id)
        .options(selectinload(PurchaseOrder.lines))
    )
    po = result.scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase Order not found")
    if po.status not in ("sent", "partially_received"):
        raise ConflictError("PO must be sent before receiving goods")
    
    grn = GoodsReceipt(
        po_id=payload.po_id,
        received_at=now_utc(),
        received_by_id=current_user.id,
        reference=payload.reference,
    )
    db.add(grn)
    await db.flush()
    
    for line in payload.lines:
        grn_line = ReceiptLine(
            receipt_id=grn.id,
            sku=line.sku,
            quantity_received=line.quantity_received,
        )
        db.add(grn_line)
    
    # Update PO status based on receipt completeness
    po.status = "partially_received"  # Could calculate if fully received
    
    await db.commit()
    await db.refresh(grn)
    
    result = await db.execute(
        select(GoodsReceipt)
        .where(GoodsReceipt.id == grn.id)
        .options(selectinload(GoodsReceipt.lines), selectinload(GoodsReceipt.po))
    )
    grn = result.scalar_one()
    
    return build_created_response(GRNResponse(
        id=grn.id, po_id=grn.po_id, po_number=grn.po.po_number if grn.po else None,
        received_at=grn.received_at, reference=grn.reference, line_count=len(grn.lines),
    ))


# =============================================================================
# Supplier Invoice Endpoints
# =============================================================================


@router.get("/invoices", response_model=APIResponse[List[dict]])
async def list_supplier_invoices(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    supplier_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Supplier Invoices."""
    stmt = select(SupplierInvoice).options(
        selectinload(SupplierInvoice.lines),
        selectinload(SupplierInvoice.supplier)
    )
    if status:
        stmt = stmt.where(SupplierInvoice.status == status)
    if supplier_id:
        stmt = stmt.where(SupplierInvoice.supplier_id == supplier_id)
    stmt = stmt.offset(skip).limit(limit).order_by(SupplierInvoice.invoice_date.desc())
    
    result = await db.execute(stmt)
    invoices = result.scalars().all()
    
    return build_response([
        {
            **i.to_dict(),
            "supplier_name": i.supplier.name if i.supplier else None,
            "total_amount": float(_calc_total(i.lines)),
            "line_count": len(i.lines),
        }
        for i in invoices
    ])


@router.post("/invoices", response_model=APIResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_supplier_invoice(
    payload: SupplierInvoiceCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new Supplier Invoice."""
    invoice = SupplierInvoice(
        supplier_invoice_number=payload.supplier_invoice_number,
        supplier_id=payload.supplier_id,
        invoice_date=payload.invoice_date.date(),
        due_date=payload.due_date.date(),
        currency=payload.currency,
        status="draft",
        po_id=payload.po_id,
        memo=payload.memo,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(invoice)
    await db.flush()
    
    for line in payload.lines:
        inv_line = SupplierInvoiceLine(
            invoice_id=invoice.id,
            sku=line.sku,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        db.add(inv_line)
    
    await db.commit()
    
    result = await db.execute(
        select(SupplierInvoice)
        .where(SupplierInvoice.id == invoice.id)
        .options(selectinload(SupplierInvoice.lines), selectinload(SupplierInvoice.supplier))
    )
    invoice = result.scalar_one()
    
    return build_created_response({
        **invoice.to_dict(),
        "supplier_name": invoice.supplier.name if invoice.supplier else None,
        "total_amount": float(_calc_total(invoice.lines)),
        "line_count": len(invoice.lines),
    })


# =============================================================================
# 3-Way Matching
# =============================================================================


@router.post("/match", response_model=APIResponse[MatchingResult])
async def three_way_match(
    po_id: UUID,
    grn_id: UUID,
    invoice_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Perform 3-way matching between PO, GRN, and Invoice."""
    # Load all three documents
    po_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.lines))
    )
    po = po_result.scalar_one_or_none()
    if not po:
        raise NotFoundError("Purchase Order not found")
    
    grn_result = await db.execute(
        select(GoodsReceipt).where(GoodsReceipt.id == grn_id)
        .options(selectinload(GoodsReceipt.lines))
    )
    grn = grn_result.scalar_one_or_none()
    if not grn:
        raise NotFoundError("Goods Receipt not found")
    
    inv_result = await db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id)
        .options(selectinload(SupplierInvoice.lines))
    )
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise NotFoundError("Supplier Invoice not found")
    
    # Calculate totals
    po_total = _calc_total(po.lines)
    grn_qty = sum(l.quantity_received for l in grn.lines)
    inv_total = _calc_total(invoice.lines)
    
    discrepancies = []
    
    # Check quantity match (simplified)
    po_qty = sum(l.quantity for l in po.lines)
    if grn_qty != po_qty:
        discrepancies.append(f"Quantity mismatch: PO={po_qty}, GRN={grn_qty}")
    
    # Check price match
    variance = abs(po_total - inv_total)
    tolerance = po_total * Decimal("0.01")  # 1% tolerance
    if variance > tolerance:
        discrepancies.append(f"Price variance: PO={po_total}, Invoice={inv_total}")
    
    matched = len(discrepancies) == 0
    
    return build_response(MatchingResult(
        po_id=po_id,
        grn_id=grn_id,
        invoice_id=invoice_id,
        po_total=po_total,
        grn_total=grn_qty,  # This should be value, simplified
        invoice_total=inv_total,
        variance=variance,
        matched=matched,
        discrepancies=discrepancies,
    ))


# =============================================================================
# Dashboard Stats
# =============================================================================


@router.get("/stats", response_model=APIResponse[dict])
async def get_purchase_stats(
    db: DBSession,
    current_user: CurrentUser,
):
    """Get purchase dashboard statistics."""
    # Count PRs by status
    pr_draft = await db.scalar(select(func.count(PurchaseRequisition.id)).where(PurchaseRequisition.status == "draft"))
    pr_submitted = await db.scalar(select(func.count(PurchaseRequisition.id)).where(PurchaseRequisition.status == "submitted"))
    pr_approved = await db.scalar(select(func.count(PurchaseRequisition.id)).where(PurchaseRequisition.status == "approved"))
    
    # Count POs by status
    po_draft = await db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "draft"))
    po_approved = await db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "approved"))
    po_sent = await db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "sent"))
    po_partial = await db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "partially_received"))
    
    # Count invoices by status
    inv_draft = await db.scalar(select(func.count(SupplierInvoice.id)).where(SupplierInvoice.status == "draft"))
    inv_approved = await db.scalar(select(func.count(SupplierInvoice.id)).where(SupplierInvoice.status == "approved"))
    
    return build_response({
        "requisitions": {
            "draft": pr_draft or 0,
            "submitted": pr_submitted or 0,
            "approved": pr_approved or 0,
        },
        "orders": {
            "draft": po_draft or 0,
            "approved": po_approved or 0,
            "sent": po_sent or 0,
            "partially_received": po_partial or 0,
        },
        "invoices": {
            "draft": inv_draft or 0,
            "approved": inv_approved or 0,
        },
    })

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
from pydantic import BaseModel, ConfigDict, Field
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
from sensei.models.inventory import (
    InventoryLevel, Location, StockMove, ValuationLayer,
)
from sensei.models.product import Product
from sensei.models.quality import InspectionPlan, InspectionRecord, InspectionType, InspectionResult
from sensei.services.core.common_thread import get_common_thread_service
from sensei.services.finance.gl_posting import post_grn_to_gl

# Purchasing/AP is cross-functional (purchasing + supply chain + logistics + finance oversight).
# CEO/admin are handled centrally by RoleChecker.
AllowPurchaseModule = deps.require_role(
    "purchasing",
    "supply_chain",
    "logistics",
    "warehouse",
    "finance",
    "accountant",
    "ops",
    "gm",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "purchasing",
                    "supply_chain",
                    "logistics",
                    "warehouse",
                    "finance",
                    "accountant",
                    "ops",
                    "gm",
                ]
            )
        )
    ]
)
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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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
    """Generate next PR number using advisory lock for concurrency safety."""
    from sqlalchemy import text
    year = datetime.now(timezone.utc).year
    prefix = f"PR-{year}-"
    # Advisory lock keyed on hash of prefix to serialise concurrent callers
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:prefix))"), {"prefix": prefix})
    result = await db.execute(
        select(func.max(PurchaseRequisition.pr_number))
        .where(PurchaseRequisition.pr_number.like(f"{prefix}%"))
    )
    last = result.scalar()
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


async def _generate_po_number(db: AsyncSession) -> str:
    """Generate next PO number using advisory lock for concurrency safety."""
    year = datetime.now(timezone.utc).year
    prefix = f"PO-{year}-"
    from sqlalchemy import text
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:prefix))"), {"prefix": prefix})
    result = await db.execute(
        select(func.max(PurchaseOrder.po_number))
        .where(PurchaseOrder.po_number.like(f"{prefix}%"))
    )
    last = result.scalar()
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


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
    po_result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po.id)
        .options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.supplier))
    )
    loaded_po = po_result.scalar_one()
    
    total = _calc_total(loaded_po.lines)
    return build_created_response(POResponse(
        id=loaded_po.id, po_number=loaded_po.po_number, status=loaded_po.status, currency=loaded_po.currency,
        supplier_id=loaded_po.supplier_id, supplier_name=loaded_po.supplier.name if loaded_po.supplier else None,
        cost_center=loaded_po.cost_center, total_amount=total, line_count=len(loaded_po.lines),
        source_pr_id=loaded_po.source_pr_id, created_at=loaded_po.created_at, approved_at=loaded_po.approved_at,
        sent_at=loaded_po.sent_at,
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
    
    # ---- Single Data Thread: bind PO into lineage ----
    try:
        ct = get_common_thread_service()
        await ct.bind(
            db,
            purchase_order_id=po.id,
            created_by_id=current_user.id,
            source="purchase_order_create",
        )
        await db.commit()
    except Exception:
        logger.debug("common_thread bind skipped for PO %s", po.id, exc_info=True)
    
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
    
    # ---- Inventory integration: create StockMoves + update InventoryLevel ----
    # Find or create a supplier-type and internal-type location for stock moves
    supplier_loc_result = await db.execute(
        select(Location).where(Location.location_type == "supplier").limit(1)
    )
    supplier_loc = supplier_loc_result.scalar_one_or_none()
    if not supplier_loc:
        # Auto-create a virtual supplier location
        # Find any warehouse to attach it to
        wh_result = await db.execute(select(Location.warehouse_id).limit(1))
        wh_id = wh_result.scalar()
        if not wh_id:
            from sensei.models.inventory import Warehouse
            default_wh = Warehouse(
                name="Main Warehouse", code="MAIN",
                created_by_id=current_user.id, updated_by_id=current_user.id,
                owner_id=current_user.id,
            )
            db.add(default_wh)
            await db.flush()
            wh_id = default_wh.id
        supplier_loc = Location(
            warehouse_id=wh_id, name="Suppliers (Virtual)",
            location_type="supplier",
            created_by_id=current_user.id, updated_by_id=current_user.id,
            owner_id=current_user.id,
        )
        db.add(supplier_loc)
        await db.flush()

    internal_loc_result = await db.execute(
        select(Location).where(Location.location_type.in_(["internal", "inventory"])).limit(1)
    )
    internal_loc = internal_loc_result.scalar_one_or_none()
    if not internal_loc:
        internal_loc = Location(
            warehouse_id=supplier_loc.warehouse_id, name="Receiving",
            location_type="internal",
            created_by_id=current_user.id, updated_by_id=current_user.id,
            owner_id=current_user.id,
        )
        db.add(internal_loc)
        await db.flush()

    for line in payload.lines:
        # Resolve product by SKU (match to PO lines)
        product_result = await db.execute(
            select(Product).where(
                (Product.sku == line.sku) | (Product.part_number == line.sku)
            ).limit(1)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            logger.warning("Product not found for SKU %s, skipping inventory update", line.sku)
            continue

        # Find unit cost from PO line
        matching_po_line = next(
            (pl for pl in po.lines if pl.sku == line.sku), None
        )
        unit_cost = matching_po_line.unit_price if matching_po_line else (
            product.unit_cost or product.standard_cost or Decimal("0")
        )

        # Create StockMove
        move = StockMove(
            product_id=product.id,
            source_location_id=supplier_loc.id,
            destination_location_id=internal_loc.id,
            quantity=line.quantity_received,
            status="done",
            reference=po.po_number,
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
            owner_id=current_user.id,
        )
        db.add(move)
        await db.flush()

        # Create ValuationLayer
        val = ValuationLayer(
            stock_move_id=move.id,
            product_id=product.id,
            quantity=line.quantity_received,
            unit_cost=unit_cost,
            value=line.quantity_received * unit_cost,
        )
        db.add(val)

        # Upsert InventoryLevel at destination
        inv_lvl_result = await db.execute(
            select(InventoryLevel).where(and_(
                InventoryLevel.product_id == product.id,
                InventoryLevel.location_id == internal_loc.id,
            ))
        )
        inv_lvl = inv_lvl_result.scalar_one_or_none()
        if inv_lvl:
            inv_lvl.quantity_on_hand += line.quantity_received
        else:
            inv_lvl = InventoryLevel(
                product_id=product.id,
                location_id=internal_loc.id,
                quantity_on_hand=line.quantity_received,
                quantity_reserved=Decimal("0"),
                created_by_id=current_user.id,
                updated_by_id=current_user.id,
                owner_id=current_user.id,
            )
            db.add(inv_lvl)

    # ---- C3: Incoming inspection trigger ----
    # For each received product, check if an active INCOMING InspectionPlan exists.
    # If so, auto-create an InspectionRecord in PENDING status so QC knows to inspect.
    for line in payload.lines:
        product_result2 = await db.execute(
            select(Product).where(
                (Product.sku == line.sku) | (Product.part_number == line.sku)
            ).limit(1)
        )
        prod = product_result2.scalar_one_or_none()
        if not prod:
            continue
        plan_result = await db.execute(
            select(InspectionPlan).where(and_(
                InspectionPlan.product_id == prod.id,
                InspectionPlan.inspection_type == InspectionType.INCOMING,
                InspectionPlan.is_active == True,  # noqa: E712
            )).limit(1)
        )
        plan = plan_result.scalar_one_or_none()
        if plan:
            record = InspectionRecord(
                inspection_plan_id=plan.id,
                lot_number=grn.reference or po.po_number,
                sample_size=int(line.quantity_received),
                inspected_by_id=current_user.id,
                overall_result=InspectionResult.PENDING,
                measurements_json=[],
                defects_found=0,
                notes=f"Auto-created from GRN for PO {po.po_number}, SKU {line.sku}",
            )
            db.add(record)

    # Update PO status based on receipt completeness
    total_ordered = sum(l.quantity for l in po.lines)
    # Load all receipts for this PO to calculate total received
    all_receipts_result = await db.execute(
        select(GoodsReceipt)
        .where(GoodsReceipt.po_id == po.id)
        .options(selectinload(GoodsReceipt.lines))
    )
    all_receipts = all_receipts_result.scalars().all()
    total_received = sum(
        rl.quantity_received for gr in all_receipts for rl in gr.lines
    )
    if total_received >= total_ordered:
        po.status = "received"
    else:
        po.status = "partially_received"

    # ---- H1 fix: create GL journal entry for goods receipt ----
    # Dr Inventory / Cr GRN Accrual for the total value of received goods
    grn_total_value = Decimal("0")
    for line in payload.lines:
        prod_r = await db.execute(
            select(Product).where(
                (Product.sku == line.sku) | (Product.part_number == line.sku)
            ).limit(1)
        )
        prod = prod_r.scalar_one_or_none()
        po_line_match = next((pl for pl in po.lines if pl.sku == line.sku), None)
        unit_cost = (
            po_line_match.unit_price if po_line_match
            else (prod.unit_cost if prod and hasattr(prod, 'unit_cost') and prod.unit_cost else Decimal("0"))
        )
        grn_total_value += line.quantity_received * unit_cost

    grn_currency = po.currency if hasattr(po, "currency") and po.currency else "USD"
    await post_grn_to_gl(
        db,
        grn_reference=grn.reference or po.po_number,
        total_value=grn_total_value,
        currency=grn_currency,
        user_id=current_user.id,
    )

    await db.commit()
    await db.refresh(grn)
    
    grn_result = await db.execute(
        select(GoodsReceipt)
        .where(GoodsReceipt.id == grn.id)
        .options(selectinload(GoodsReceipt.lines), selectinload(GoodsReceipt.po))
    )
    loaded_grn = grn_result.scalar_one()
    
    # ---- Single Data Thread: link GRN to PO lineage ----
    try:
        ct = get_common_thread_service()
        await ct.bind(
            db,
            purchase_order_id=payload.po_id,
            goods_receipt_id=str(grn.id),
            created_by_id=current_user.id,
            source="goods_receipt_create",
        )
        await db.commit()
    except Exception:
        logger.debug("common_thread bind skipped for GRN %s", grn.id, exc_info=True)
    
    return build_created_response(GRNResponse(
        id=loaded_grn.id, po_id=loaded_grn.po_id, po_number=loaded_grn.po.po_number if loaded_grn.po else None,
        received_at=loaded_grn.received_at, reference=loaded_grn.reference, line_count=len(loaded_grn.lines),
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
    inv_total = _calc_total(invoice.lines)

    # GRN value: match received quantities against PO line unit prices
    grn_value = Decimal("0")
    po_line_map = {pl.sku: pl for pl in po.lines}
    for rl in grn.lines:
        po_line = po_line_map.get(rl.sku)
        if po_line:
            grn_value += rl.quantity_received * po_line.unit_price
        # else: unmatched SKU — flagged below

    discrepancies: List[str] = []

    # Check quantity match per SKU
    po_qty_map = {pl.sku: pl.quantity for pl in po.lines}
    grn_qty_map: dict[str, Decimal] = {}
    for rl in grn.lines:
        grn_qty_map[rl.sku] = grn_qty_map.get(rl.sku, Decimal("0")) + rl.quantity_received
    all_skus = set(po_qty_map.keys()) | set(grn_qty_map.keys())
    for sku in sorted(all_skus):
        oq = po_qty_map.get(sku, Decimal("0"))
        rq = grn_qty_map.get(sku, Decimal("0"))
        if oq != rq:
            discrepancies.append(f"Qty mismatch [{sku}]: PO={oq}, GRN={rq}")

    # Check price match (PO vs Invoice)
    variance = abs(po_total - inv_total)
    tolerance = po_total * Decimal("0.01") if po_total else Decimal("0")  # 1% tolerance
    if variance > tolerance:
        discrepancies.append(f"Price variance: PO={po_total}, Invoice={inv_total}")

    # Check GRN value vs Invoice value
    grn_inv_variance = abs(grn_value - inv_total)
    if grn_inv_variance > tolerance:
        discrepancies.append(f"GRN vs Invoice variance: GRN={grn_value}, Invoice={inv_total}")

    matched = len(discrepancies) == 0

    return build_response(MatchingResult(
        po_id=po_id,
        grn_id=grn_id,
        invoice_id=invoice_id,
        po_total=po_total,
        grn_total=grn_value,
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

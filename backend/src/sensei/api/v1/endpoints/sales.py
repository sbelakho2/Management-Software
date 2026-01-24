"""
Sales Order Management Endpoints.

Provides full CRUD and workflow operations for:
- Sales Orders (SO)
- Customer Invoices
- Payment Receipts
- Credit Management
- Quote-to-Order Conversion
"""

import logging
from datetime import datetime, date, timezone, timedelta
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
from sensei.models.accounts_receivable import (
    SalesOrder, SalesOrderLine, CustomerInvoice, CustomerInvoiceLine,
    PaymentReceipt, PaymentAllocation, CustomerCreditProfile
)
from sensei.models.quote import Quote, QuoteLineItem, QuoteStatus
from sensei.models.account import Account

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Schemas
# =============================================================================


class SOLineCreate(BaseModel):
    """Sales Order line item."""
    sku: str = Field(..., min_length=1)
    description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class SOCreate(BaseModel):
    """Sales Order creation."""
    account_id: UUID
    currency: str = Field(default="USD", max_length=3)
    payment_terms_days: int = Field(default=30, ge=0)
    source_quote_id: Optional[UUID] = None
    lines: List[SOLineCreate] = Field(..., min_length=1)


class SOResponse(BaseModel):
    """Sales Order response."""
    id: UUID
    so_number: str
    status: str
    currency: str
    account_id: UUID
    account_name: Optional[str] = None
    total_amount: Decimal
    line_count: int
    payment_terms_days: int
    source_quote_id: Optional[UUID]
    created_at: datetime
    approved_at: Optional[datetime]
    released_at: Optional[datetime]

    class Config:
        from_attributes = True


class InvoiceLineCreate(BaseModel):
    """Customer Invoice line."""
    sku: str
    description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class InvoiceCreate(BaseModel):
    """Customer Invoice creation."""
    account_id: UUID
    currency: str = Field(default="USD", max_length=3)
    due_date: datetime
    sales_order_id: Optional[UUID] = None
    memo: Optional[str] = None
    is_credit_memo: bool = False
    lines: List[InvoiceLineCreate] = Field(..., min_length=1)


class InvoiceResponse(BaseModel):
    """Customer Invoice response."""
    id: UUID
    invoice_number: str
    status: str
    currency: str
    account_id: UUID
    account_name: Optional[str] = None
    total_amount: Decimal
    line_count: int
    issued_at: datetime
    due_date: date
    is_credit_memo: bool
    disputed: bool
    sales_order_id: Optional[UUID]

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    """Payment receipt creation."""
    account_id: UUID
    currency: str = Field(default="USD", max_length=3)
    amount: Decimal = Field(..., gt=0)
    reference: Optional[str] = None
    notes: Optional[str] = None
    invoice_allocations: Optional[List[dict]] = None  # [{invoice_id, amount}]


class PaymentResponse(BaseModel):
    """Payment receipt response."""
    id: UUID
    account_id: UUID
    account_name: Optional[str] = None
    currency: str
    amount: Decimal
    status: str
    received_at: datetime
    reference: Optional[str]

    class Config:
        from_attributes = True


class CreditCheckResult(BaseModel):
    """Credit check result."""
    account_id: UUID
    account_name: str
    credit_limit: Decimal
    current_balance: Decimal
    available_credit: Decimal
    is_on_hold: bool
    hold_reason: Optional[str]
    can_proceed: bool
    order_amount: Decimal


class QuoteConversionResult(BaseModel):
    """Result of quote-to-order conversion."""
    sales_order_id: UUID
    so_number: str
    quote_id: UUID
    quote_number: str
    converted_at: datetime


# =============================================================================
# Sequence helpers
# =============================================================================


async def _generate_so_number(db: AsyncSession) -> str:
    """Generate next SO number."""
    result = await db.execute(select(func.count(SalesOrder.id)))
    count = result.scalar() or 0
    return f"SO-{datetime.now(timezone.utc).year}-{count + 1:05d}"


async def _generate_invoice_number(db: AsyncSession) -> str:
    """Generate next Invoice number."""
    result = await db.execute(select(func.count(CustomerInvoice.id)))
    count = result.scalar() or 0
    return f"INV-{datetime.now(timezone.utc).year}-{count + 1:05d}"


def _calc_total(lines: List[Any]) -> Decimal:
    """Calculate total from line items."""
    return sum(line.quantity * line.unit_price for line in lines)


# =============================================================================
# Credit Management
# =============================================================================


@router.get("/credit-check/{account_id}", response_model=APIResponse[CreditCheckResult])
async def check_customer_credit(
    account_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    order_amount: Decimal = Query(..., gt=0),
):
    """Check if customer has sufficient credit for an order."""
    # Get account
    account_result = await db.execute(
        select(Account).where(Account.id == account_id)
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise NotFoundError("Account not found")
    
    # Get credit profile
    profile_result = await db.execute(
        select(CustomerCreditProfile).where(CustomerCreditProfile.account_id == account_id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # Calculate outstanding balance
    outstanding_result = await db.execute(
        select(func.coalesce(func.sum(CustomerInvoice.id), Decimal("0")))
        .where(and_(
            CustomerInvoice.account_id == account_id,
            CustomerInvoice.status == "issued"
        ))
    )
    # Simplified - in reality would sum invoice totals minus payments
    outstanding = Decimal("0")
    
    credit_limit = profile.credit_limit if profile else Decimal("0")
    available = credit_limit - outstanding
    is_on_hold = profile.is_on_credit_hold if profile else False
    
    can_proceed = not is_on_hold and (available >= order_amount or credit_limit == Decimal("0"))
    
    return build_response(CreditCheckResult(
        account_id=account_id,
        account_name=account.name,
        credit_limit=credit_limit,
        current_balance=outstanding,
        available_credit=available,
        is_on_hold=is_on_hold,
        hold_reason=profile.hold_reason if profile else None,
        can_proceed=can_proceed,
        order_amount=order_amount,
    ))


# =============================================================================
# Sales Order Endpoints
# =============================================================================


@router.get("/orders", response_model=APIResponse[List[SOResponse]])
async def list_sales_orders(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    account_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Sales Orders with optional filters."""
    stmt = select(SalesOrder).options(
        selectinload(SalesOrder.lines),
        selectinload(SalesOrder.account)
    )
    if status:
        stmt = stmt.where(SalesOrder.status == status)
    if account_id:
        stmt = stmt.where(SalesOrder.account_id == account_id)
    stmt = stmt.offset(skip).limit(limit).order_by(SalesOrder.created_at.desc())
    
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    data = []
    for o in orders:
        total = _calc_total(o.lines)
        data.append(SOResponse(
            id=o.id, so_number=o.so_number, status=o.status, currency=o.currency,
            account_id=o.account_id, account_name=o.account.name if o.account else None,
            total_amount=total, line_count=len(o.lines), payment_terms_days=o.payment_terms_days,
            source_quote_id=o.source_quote_id, created_at=o.created_at, approved_at=o.approved_at,
            released_at=o.released_at,
        ))
    return build_response(data)


@router.post("/orders", response_model=APIResponse[SOResponse], status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    payload: SOCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new Sales Order."""
    so_number = await _generate_so_number(db)
    
    so = SalesOrder(
        so_number=so_number,
        account_id=payload.account_id,
        currency=payload.currency,
        status="draft",
        payment_terms_days=payload.payment_terms_days,
        source_quote_id=payload.source_quote_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(so)
    await db.flush()
    
    for line in payload.lines:
        so_line = SalesOrderLine(
            so_id=so.id,
            sku=line.sku,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        db.add(so_line)
    
    await db.commit()
    
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == so.id)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.account))
    )
    so = result.scalar_one()
    
    total = _calc_total(so.lines)
    return build_created_response(SOResponse(
        id=so.id, so_number=so.so_number, status=so.status, currency=so.currency,
        account_id=so.account_id, account_name=so.account.name if so.account else None,
        total_amount=total, line_count=len(so.lines), payment_terms_days=so.payment_terms_days,
        source_quote_id=so.source_quote_id, created_at=so.created_at, approved_at=so.approved_at,
        released_at=so.released_at,
    ))


@router.get("/orders/{so_id}", response_model=APIResponse[dict])
async def get_sales_order(
    so_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get a single Sales Order with full details."""
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == so_id)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.account))
    )
    so = result.scalar_one_or_none()
    if not so:
        raise NotFoundError("Sales Order not found")
    
    return build_response({
        **so.to_dict(),
        "account_name": so.account.name if so.account else None,
        "lines": [l.to_dict() for l in so.lines],
        "total_amount": float(_calc_total(so.lines)),
    })


@router.post("/orders/{so_id}/approve", response_model=APIResponse[SOResponse])
async def approve_sales_order(
    so_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Approve a draft SO."""
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == so_id)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.account))
    )
    so = result.scalar_one_or_none()
    if not so:
        raise NotFoundError("Sales Order not found")
    if so.status != "draft":
        raise ConflictError("Only draft SOs can be approved")
    
    so.status = "approved"
    so.approved_at = now_utc()
    so.approved_by_id = current_user.id
    await db.commit()
    
    total = _calc_total(so.lines)
    return build_response(SOResponse(
        id=so.id, so_number=so.so_number, status=so.status, currency=so.currency,
        account_id=so.account_id, account_name=so.account.name if so.account else None,
        total_amount=total, line_count=len(so.lines), payment_terms_days=so.payment_terms_days,
        source_quote_id=so.source_quote_id, created_at=so.created_at, approved_at=so.approved_at,
        released_at=so.released_at,
    ))


@router.post("/orders/{so_id}/release", response_model=APIResponse[SOResponse])
async def release_sales_order(
    so_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Release an approved SO to production/fulfillment."""
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == so_id)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.account))
    )
    so = result.scalar_one_or_none()
    if not so:
        raise NotFoundError("Sales Order not found")
    if so.status != "approved":
        raise ConflictError("Only approved SOs can be released")
    
    so.status = "released"
    so.released_at = now_utc()
    so.released_by_id = current_user.id
    await db.commit()
    
    total = _calc_total(so.lines)
    return build_response(SOResponse(
        id=so.id, so_number=so.so_number, status=so.status, currency=so.currency,
        account_id=so.account_id, account_name=so.account.name if so.account else None,
        total_amount=total, line_count=len(so.lines), payment_terms_days=so.payment_terms_days,
        source_quote_id=so.source_quote_id, created_at=so.created_at, approved_at=so.approved_at,
        released_at=so.released_at,
    ))


# =============================================================================
# Quote to Order Conversion
# =============================================================================


@router.post("/convert-quote/{quote_id}", response_model=APIResponse[QuoteConversionResult])
async def convert_quote_to_order(
    quote_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Convert an accepted quote to a Sales Order."""
    # Load quote with line items
    result = await db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.line_items))
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise NotFoundError("Quote not found")
    if quote.status != QuoteStatus.ACCEPTED.value:
        raise ConflictError("Only accepted quotes can be converted to orders")
    
    # Generate SO number
    so_number = await _generate_so_number(db)
    
    # Create Sales Order from Quote
    so = SalesOrder(
        so_number=so_number,
        account_id=quote.account_id,
        currency=quote.currency,
        status="draft",
        payment_terms_days=30,  # Could read from quote.payment_terms
        source_quote_id=quote.id,
        source_quote_version=quote.current_version,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(so)
    await db.flush()
    
    # Copy line items
    for quote_line in quote.line_items:
        so_line = SalesOrderLine(
            so_id=so.id,
            sku=quote_line.sku or quote_line.product_name or "ITEM",
            description=quote_line.description or quote_line.product_name or "",
            quantity=quote_line.quantity,
            unit_price=quote_line.unit_price,
        )
        db.add(so_line)
    
    await db.commit()
    
    return build_created_response(QuoteConversionResult(
        sales_order_id=so.id,
        so_number=so.so_number,
        quote_id=quote.id,
        quote_number=quote.quote_number,
        converted_at=now_utc(),
    ))


# =============================================================================
# Customer Invoice Endpoints
# =============================================================================


@router.get("/invoices", response_model=APIResponse[List[InvoiceResponse]])
async def list_customer_invoices(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    account_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Customer Invoices."""
    stmt = select(CustomerInvoice).options(
        selectinload(CustomerInvoice.lines),
        selectinload(CustomerInvoice.account)
    )
    if status:
        stmt = stmt.where(CustomerInvoice.status == status)
    if account_id:
        stmt = stmt.where(CustomerInvoice.account_id == account_id)
    stmt = stmt.offset(skip).limit(limit).order_by(CustomerInvoice.issued_at.desc())
    
    result = await db.execute(stmt)
    invoices = result.scalars().all()
    
    data = []
    for i in invoices:
        total = _calc_total(i.lines)
        data.append(InvoiceResponse(
            id=i.id, invoice_number=i.invoice_number, status=i.status, currency=i.currency,
            account_id=i.account_id, account_name=i.account.name if i.account else None,
            total_amount=total, line_count=len(i.lines), issued_at=i.issued_at, due_date=i.due_date,
            is_credit_memo=i.is_credit_memo, disputed=i.disputed, sales_order_id=i.sales_order_id,
        ))
    return build_response(data)


@router.post("/invoices", response_model=APIResponse[InvoiceResponse], status_code=status.HTTP_201_CREATED)
async def create_customer_invoice(
    payload: InvoiceCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new Customer Invoice."""
    invoice_number = await _generate_invoice_number(db)
    
    invoice = CustomerInvoice(
        invoice_number=invoice_number,
        account_id=payload.account_id,
        currency=payload.currency,
        status="issued",
        issued_at=now_utc(),
        due_date=payload.due_date.date(),
        sales_order_id=payload.sales_order_id,
        memo=payload.memo,
        is_credit_memo=payload.is_credit_memo,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(invoice)
    await db.flush()
    
    for line in payload.lines:
        inv_line = CustomerInvoiceLine(
            invoice_id=invoice.id,
            sku=line.sku,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )
        db.add(inv_line)
    
    await db.commit()
    
    result = await db.execute(
        select(CustomerInvoice)
        .where(CustomerInvoice.id == invoice.id)
        .options(selectinload(CustomerInvoice.lines), selectinload(CustomerInvoice.account))
    )
    invoice = result.scalar_one()
    
    total = _calc_total(invoice.lines)
    return build_created_response(InvoiceResponse(
        id=invoice.id, invoice_number=invoice.invoice_number, status=invoice.status, currency=invoice.currency,
        account_id=invoice.account_id, account_name=invoice.account.name if invoice.account else None,
        total_amount=total, line_count=len(invoice.lines), issued_at=invoice.issued_at, due_date=invoice.due_date,
        is_credit_memo=invoice.is_credit_memo, disputed=invoice.disputed, sales_order_id=invoice.sales_order_id,
    ))


@router.post("/invoices/from-so/{so_id}", response_model=APIResponse[InvoiceResponse])
async def create_invoice_from_sales_order(
    so_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a Customer Invoice from a Sales Order."""
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == so_id)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.account))
    )
    so = result.scalar_one_or_none()
    if not so:
        raise NotFoundError("Sales Order not found")
    if so.status not in ("released", "closed"):
        raise ConflictError("Can only invoice released or closed orders")
    
    invoice_number = await _generate_invoice_number(db)
    due_date = (datetime.now(timezone.utc) + timedelta(days=so.payment_terms_days)).date()
    
    invoice = CustomerInvoice(
        invoice_number=invoice_number,
        account_id=so.account_id,
        currency=so.currency,
        status="issued",
        issued_at=now_utc(),
        due_date=due_date,
        sales_order_id=so.id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        owner_id=current_user.id,
    )
    db.add(invoice)
    await db.flush()
    
    for so_line in so.lines:
        inv_line = CustomerInvoiceLine(
            invoice_id=invoice.id,
            sku=so_line.sku,
            description=so_line.description,
            quantity=so_line.quantity,
            unit_price=so_line.unit_price,
        )
        db.add(inv_line)
    
    await db.commit()
    
    inv_result = await db.execute(
        select(CustomerInvoice)
        .where(CustomerInvoice.id == invoice.id)
        .options(selectinload(CustomerInvoice.lines), selectinload(CustomerInvoice.account))
    )
    loaded_invoice = inv_result.scalar_one()
    
    total = _calc_total(loaded_invoice.lines)
    return build_created_response(InvoiceResponse(
        id=loaded_invoice.id, invoice_number=loaded_invoice.invoice_number, status=loaded_invoice.status, currency=loaded_invoice.currency,
        account_id=loaded_invoice.account_id, account_name=loaded_invoice.account.name if loaded_invoice.account else None,
        total_amount=total, line_count=len(loaded_invoice.lines), issued_at=loaded_invoice.issued_at, due_date=loaded_invoice.due_date,
        is_credit_memo=loaded_invoice.is_credit_memo, disputed=loaded_invoice.disputed, sales_order_id=loaded_invoice.sales_order_id,
    ))


# =============================================================================
# Payment Receipt Endpoints
# =============================================================================


@router.get("/receipts", response_model=APIResponse[List[PaymentResponse]])
async def list_payment_receipts(
    db: DBSession,
    current_user: CurrentUser,
    account_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all Payment Receipts."""
    stmt = select(PaymentReceipt).options(selectinload(PaymentReceipt.account))
    if account_id:
        stmt = stmt.where(PaymentReceipt.account_id == account_id)
    stmt = stmt.offset(skip).limit(limit).order_by(PaymentReceipt.received_at.desc())
    
    result = await db.execute(stmt)
    receipts = result.scalars().all()
    
    return build_response([
        PaymentResponse(
            id=r.id, account_id=r.account_id, account_name=r.account.name if r.account else None,
            currency=r.currency, amount=r.amount, status=r.status, received_at=r.received_at,
            reference=r.reference,
        )
        for r in receipts
    ])


@router.post("/receipts", response_model=APIResponse[PaymentResponse], status_code=status.HTTP_201_CREATED)
async def create_payment_receipt(
    payload: PaymentCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Record a customer payment."""
    receipt = PaymentReceipt(
        account_id=payload.account_id,
        received_at=now_utc(),
        received_by_id=current_user.id,
        currency=payload.currency,
        amount=payload.amount,
        status="posted",
        reference=payload.reference,
        notes=payload.notes,
    )
    db.add(receipt)
    await db.flush()
    
    # Create allocations if provided
    if payload.invoice_allocations:
        for alloc in payload.invoice_allocations:
            allocation = PaymentAllocation(
                receipt_id=receipt.id,
                invoice_id=alloc["invoice_id"],
                amount=Decimal(str(alloc["amount"])),
            )
            db.add(allocation)
    
    await db.commit()
    
    result = await db.execute(
        select(PaymentReceipt)
        .where(PaymentReceipt.id == receipt.id)
        .options(selectinload(PaymentReceipt.account))
    )
    receipt = result.scalar_one()
    
    return build_created_response(PaymentResponse(
        id=receipt.id, account_id=receipt.account_id, account_name=receipt.account.name if receipt.account else None,
        currency=receipt.currency, amount=receipt.amount, status=receipt.status, received_at=receipt.received_at,
        reference=receipt.reference,
    ))


# =============================================================================
# Dashboard Stats
# =============================================================================


@router.get("/stats", response_model=APIResponse[dict])
async def get_sales_stats(
    db: DBSession,
    current_user: CurrentUser,
):
    """Get sales dashboard statistics."""
    # Count SOs by status
    so_draft = await db.scalar(select(func.count(SalesOrder.id)).where(SalesOrder.status == "draft"))
    so_approved = await db.scalar(select(func.count(SalesOrder.id)).where(SalesOrder.status == "approved"))
    so_released = await db.scalar(select(func.count(SalesOrder.id)).where(SalesOrder.status == "released"))
    
    # Count invoices
    inv_issued = await db.scalar(select(func.count(CustomerInvoice.id)).where(CustomerInvoice.status == "issued"))
    inv_paid = await db.scalar(select(func.count(CustomerInvoice.id)).where(CustomerInvoice.status == "paid"))
    
    # Count overdue invoices
    today = date.today()
    inv_overdue = await db.scalar(
        select(func.count(CustomerInvoice.id)).where(and_(
            CustomerInvoice.status == "issued",
            CustomerInvoice.due_date < today
        ))
    )
    
    return build_response({
        "orders": {
            "draft": so_draft or 0,
            "approved": so_approved or 0,
            "released": so_released or 0,
        },
        "invoices": {
            "issued": inv_issued or 0,
            "paid": inv_paid or 0,
            "overdue": inv_overdue or 0,
        },
    })

"""
RFQ (Request for Quotation) Management Endpoints

Provides full CRUD and workflow operations for RFQs:
- RFQ lifecycle management
- Question/Answer tracking
- Qualification integration
- Quote generation workflow
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, ForbiddenError, NotFoundError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_paginated_response,
    build_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    now_utc,
    parse_sort_param,
)
from sensei.models.rfq import (
    RFQ,
    RFQStatus,
    RFQPriority,
    RFQSource,
    RFQQuestion,
    QuestionStatus,
)


router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class RFQBase(BaseModel):
    """Base RFQ fields."""
    
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    customer_rfq_number: Optional[str] = Field(None, max_length=100)
    
    account_id: UUID
    contact_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    
    priority: str = Field(default=RFQPriority.MEDIUM.value)
    source: Optional[str] = None
    
    # Dates
    due_date: Optional[datetime] = None
    customer_deadline: Optional[datetime] = None
    
    # Part/Product Information
    part_number: Optional[str] = Field(None, max_length=100)
    part_name: Optional[str] = Field(None, max_length=255)
    part_revision: Optional[str] = Field(None, max_length=50)
    drawing_number: Optional[str] = Field(None, max_length=100)
    
    # Quantity and Pricing
    quantity: Optional[int] = None
    annual_volume: Optional[int] = None
    target_price: Optional[Decimal] = None
    currency: str = Field(default="MAD", max_length=3)
    
    # Technical Specifications
    material_spec: Optional[str] = None
    material_grade: Optional[str] = Field(None, max_length=100)
    finish_requirements: Optional[str] = None
    tolerance_requirements: Optional[str] = None
    
    # Processes
    primary_process: Optional[str] = Field(None, max_length=100)
    secondary_processes: Optional[list] = None
    
    # Quality Requirements
    quality_requirements: Optional[str] = None
    certifications_required: Optional[list] = None
    inspection_requirements: Optional[str] = None
    
    # Delivery
    delivery_terms: Optional[str] = Field(None, max_length=50)
    delivery_location: Optional[str] = Field(None, max_length=255)
    lead_time_required: Optional[int] = None
    
    # Packaging
    packaging_requirements: Optional[str] = None
    
    # Notes
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    
    # Custom Fields
    custom_fields: Optional[dict] = None
    tags: Optional[list] = None


class RFQCreate(RFQBase):
    """RFQ creation request."""
    pass


class RFQUpdate(BaseModel):
    """RFQ update request."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    customer_rfq_number: Optional[str] = Field(None, max_length=100)
    
    contact_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    
    status: Optional[str] = None
    priority: Optional[str] = None
    source: Optional[str] = None
    
    # Dates
    due_date: Optional[datetime] = None
    customer_deadline: Optional[datetime] = None
    
    # Part/Product Information
    part_number: Optional[str] = Field(None, max_length=100)
    part_name: Optional[str] = Field(None, max_length=255)
    part_revision: Optional[str] = Field(None, max_length=50)
    drawing_number: Optional[str] = Field(None, max_length=100)
    
    # Quantity and Pricing
    quantity: Optional[int] = None
    annual_volume: Optional[int] = None
    target_price: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=3)
    
    # Technical Specifications
    material_spec: Optional[str] = None
    material_grade: Optional[str] = Field(None, max_length=100)
    finish_requirements: Optional[str] = None
    tolerance_requirements: Optional[str] = None
    
    # Processes
    primary_process: Optional[str] = Field(None, max_length=100)
    secondary_processes: Optional[list] = None
    
    # Quality Requirements
    quality_requirements: Optional[str] = None
    certifications_required: Optional[list] = None
    inspection_requirements: Optional[str] = None
    
    # Delivery
    delivery_terms: Optional[str] = Field(None, max_length=50)
    delivery_location: Optional[str] = Field(None, max_length=255)
    lead_time_required: Optional[int] = None
    
    # Packaging
    packaging_requirements: Optional[str] = None
    
    # Assignment
    assigned_to_id: Optional[UUID] = None
    
    # Qualification
    is_qualified: Optional[bool] = None
    qualification_score: Optional[Decimal] = None
    qualification_notes: Optional[str] = None
    no_bid_reason: Optional[str] = Field(None, max_length=255)
    
    # Win/Loss
    is_won: Optional[bool] = None
    win_loss_reason: Optional[str] = Field(None, max_length=255)
    competitor_id: Optional[UUID] = None
    
    # Notes
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    
    # Custom Fields
    custom_fields: Optional[dict] = None
    tags: Optional[list] = None


class RFQResponse(BaseModel):
    """Full RFQ response."""
    
    id: UUID
    rfq_number: str
    customer_rfq_number: Optional[str]
    revision: int
    
    title: str
    description: Optional[str]
    
    account_id: UUID
    contact_id: Optional[UUID]
    opportunity_id: Optional[UUID]
    
    status: str
    priority: str
    source: Optional[str]
    
    is_open: bool
    
    # Dates
    received_date: datetime
    due_date: Optional[datetime]
    customer_deadline: Optional[datetime]
    quoted_date: Optional[datetime]
    decision_date: Optional[datetime]
    
    days_until_due: Optional[int]
    
    # Part/Product Information
    part_number: Optional[str]
    part_name: Optional[str]
    part_revision: Optional[str]
    drawing_number: Optional[str]
    
    # Quantity and Pricing
    quantity: Optional[int]
    annual_volume: Optional[int]
    target_price: Optional[Decimal]
    currency: str
    
    # Technical Specifications
    material_spec: Optional[str]
    material_grade: Optional[str]
    finish_requirements: Optional[str]
    tolerance_requirements: Optional[str]
    
    # Processes
    primary_process: Optional[str]
    secondary_processes: Optional[list]
    
    # Quality Requirements
    quality_requirements: Optional[str]
    certifications_required: Optional[list]
    inspection_requirements: Optional[str]
    
    # Delivery
    delivery_terms: Optional[str]
    delivery_location: Optional[str]
    lead_time_required: Optional[int]
    
    # Packaging
    packaging_requirements: Optional[str]
    
    # Assignment
    assigned_to_id: Optional[UUID]
    
    # Qualification
    is_qualified: Optional[bool]
    qualification_score: Optional[Decimal]
    qualification_notes: Optional[str]
    no_bid_reason: Optional[str]
    
    # Win/Loss
    is_won: Optional[bool]
    win_loss_reason: Optional[str]
    competitor_id: Optional[UUID]
    
    # Notes
    internal_notes: Optional[str]
    customer_notes: Optional[str]
    
    # Custom Fields
    custom_fields: Optional[dict]
    tags: Optional[list]
    
    # Counts
    question_count: int = 0
    quote_count: int = 0
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class RFQListResponse(BaseModel):
    """Simplified RFQ for list views."""
    
    id: UUID
    rfq_number: str
    customer_rfq_number: Optional[str]
    title: str
    account_id: UUID
    status: str
    priority: str
    is_open: bool
    received_date: datetime
    due_date: Optional[datetime]
    days_until_due: Optional[int]
    part_number: Optional[str]
    quantity: Optional[int]
    assigned_to_id: Optional[UUID]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    """Base question fields."""
    
    question: str = Field(..., min_length=1)
    category: Optional[str] = Field(None, max_length=50)


class QuestionCreate(QuestionBase):
    """Question creation request."""
    pass


class QuestionUpdate(BaseModel):
    """Question update request."""
    
    question: Optional[str] = None
    answer: Optional[str] = None
    status: Optional[str] = None


class QuestionResponse(BaseModel):
    """Question response."""
    
    id: UUID
    rfq_id: UUID
    question: str
    answer: Optional[str]
    status: str
    category: Optional[str]
    asked_at: Optional[datetime]
    answered_at: Optional[datetime]
    asked_by_id: Optional[UUID]
    answered_by_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Helper Functions
# =============================================================================


def rfq_to_response(rfq: RFQ) -> RFQResponse:
    """Convert RFQ model to response."""
    return RFQResponse(
        id=rfq.id,
        rfq_number=rfq.rfq_number,
        customer_rfq_number=rfq.customer_rfq_number,
        revision=rfq.revision,
        title=rfq.title,
        description=rfq.description,
        account_id=rfq.account_id,
        contact_id=rfq.contact_id,
        opportunity_id=rfq.opportunity_id,
        status=rfq.status,
        priority=rfq.priority,
        source=rfq.source,
        is_open=rfq.is_open,
        received_date=rfq.received_date,
        due_date=rfq.due_date,
        customer_deadline=rfq.customer_deadline,
        quoted_date=rfq.quoted_date,
        decision_date=rfq.decision_date,
        days_until_due=rfq.days_until_due,
        part_number=rfq.part_number,
        part_name=rfq.part_name,
        part_revision=rfq.part_revision,
        drawing_number=rfq.drawing_number,
        quantity=rfq.quantity,
        annual_volume=rfq.annual_volume,
        target_price=rfq.target_price,
        currency=rfq.currency,
        material_spec=rfq.material_spec,
        material_grade=rfq.material_grade,
        finish_requirements=rfq.finish_requirements,
        tolerance_requirements=rfq.tolerance_requirements,
        primary_process=rfq.primary_process,
        secondary_processes=rfq.secondary_processes,
        quality_requirements=rfq.quality_requirements,
        certifications_required=rfq.certifications_required,
        inspection_requirements=rfq.inspection_requirements,
        delivery_terms=rfq.delivery_terms,
        delivery_location=rfq.delivery_location,
        lead_time_required=rfq.lead_time_required,
        packaging_requirements=rfq.packaging_requirements,
        assigned_to_id=rfq.assigned_to_id,
        is_qualified=rfq.is_qualified,
        qualification_score=rfq.qualification_score,
        qualification_notes=rfq.qualification_notes,
        no_bid_reason=rfq.no_bid_reason,
        is_won=rfq.is_won,
        win_loss_reason=rfq.win_loss_reason,
        competitor_id=rfq.competitor_id,
        internal_notes=rfq.internal_notes,
        customer_notes=rfq.customer_notes,
        custom_fields=rfq.custom_fields,
        tags=rfq.tags,
        question_count=len(rfq.questions.all()) if hasattr(rfq.questions, 'all') else 0,
        quote_count=len(rfq.quotes.all()) if hasattr(rfq.quotes, 'all') else 0,
        created_at=rfq.created_at,
        updated_at=rfq.updated_at,
        created_by_id=rfq.created_by_id,
    )


def rfq_to_list_response(rfq: RFQ) -> RFQListResponse:
    """Convert RFQ model to list response."""
    return RFQListResponse(
        id=rfq.id,
        rfq_number=rfq.rfq_number,
        customer_rfq_number=rfq.customer_rfq_number,
        title=rfq.title,
        account_id=rfq.account_id,
        status=rfq.status,
        priority=rfq.priority,
        is_open=rfq.is_open,
        received_date=rfq.received_date,
        due_date=rfq.due_date,
        days_until_due=rfq.days_until_due,
        part_number=rfq.part_number,
        quantity=rfq.quantity,
        assigned_to_id=rfq.assigned_to_id,
        created_at=rfq.created_at,
    )


def question_to_response(question: RFQQuestion) -> QuestionResponse:
    """Convert question model to response."""
    return QuestionResponse(
        id=question.id,
        rfq_id=question.rfq_id,
        question=question.question,
        answer=question.answer,
        status=question.status,
        category=question.category,
        asked_at=question.asked_at,
        answered_at=question.answered_at,
        asked_by_id=question.asked_by_id,
        answered_by_id=question.answered_by_id,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


async def generate_rfq_number(db: DBSession) -> str:
    """Generate unique RFQ number."""
    year = datetime.now().year
    prefix = f"RFQ-{year}-"
    
    # Find the highest existing number for this year
    result = await db.execute(
        select(func.max(RFQ.rfq_number))
        .where(RFQ.rfq_number.like(f"{prefix}%"))
    )
    last_number = result.scalar()
    
    if last_number:
        # Extract the sequence number and increment
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1
    
    return f"{prefix}{seq:05d}"


# =============================================================================
# RFQ CRUD Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse)
async def list_rfqs(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    account_id: Optional[UUID] = Query(default=None),
    assigned_to_id: Optional[UUID] = Query(default=None),
    is_open: Optional[bool] = Query(default=None),
    sort: str = Query(default="-received_date"),
    include_deleted: bool = Query(default=False),
):
    """
    List RFQs with filtering, sorting, and pagination.
    """
    # Build query
    query = select(RFQ)
    count_query = select(func.count(RFQ.id))
    
    # Soft delete filter
    if not include_deleted:
        query = query.where(RFQ.deleted_at.is_(None))
        count_query = count_query.where(RFQ.deleted_at.is_(None))
    
    # Search filter
    if search:
        search_filter = or_(
            RFQ.rfq_number.ilike(f"%{search}%"),
            RFQ.customer_rfq_number.ilike(f"%{search}%"),
            RFQ.title.ilike(f"%{search}%"),
            RFQ.part_number.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Status filter
    if status:
        query = query.where(RFQ.status == status)
        count_query = count_query.where(RFQ.status == status)
    
    # Priority filter
    if priority:
        query = query.where(RFQ.priority == priority)
        count_query = count_query.where(RFQ.priority == priority)
    
    # Account filter
    if account_id:
        query = query.where(RFQ.account_id == account_id)
        count_query = count_query.where(RFQ.account_id == account_id)
    
    # Assigned to filter
    if assigned_to_id:
        query = query.where(RFQ.assigned_to_id == assigned_to_id)
        count_query = count_query.where(RFQ.assigned_to_id == assigned_to_id)
    
    # Open status filter
    if is_open is not None:
        closed_statuses = [
            RFQStatus.WON.value,
            RFQStatus.LOST.value,
            RFQStatus.NO_BID.value,
            RFQStatus.CANCELLED.value,
            RFQStatus.EXPIRED.value,
        ]
        if is_open:
            query = query.where(RFQ.status.notin_(closed_statuses))
            count_query = count_query.where(RFQ.status.notin_(closed_statuses))
        else:
            query = query.where(RFQ.status.in_(closed_statuses))
            count_query = count_query.where(RFQ.status.in_(closed_statuses))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_orders = parse_sort_param(sort)
    for sort_order in sort_orders:
        if hasattr(RFQ, sort_order.field):
            column = getattr(RFQ, sort_order.field)
            query = query.order_by(column.desc() if sort_order.direction == "desc" else column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    rfqs = result.scalars().all()
    
    # Convert to response
    items = [rfq_to_list_response(r) for r in rfqs]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_rfq(
    rfq_data: RFQCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new RFQ.
    """
    # Generate RFQ number
    rfq_number = await generate_rfq_number(db)
    
    # Create RFQ
    rfq_dict = rfq_data.model_dump(exclude_unset=True)
    
    rfq = RFQ(
        **rfq_dict,
        rfq_number=rfq_number,
        status=RFQStatus.RECEIVED.value,
        received_date=now_utc(),
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    
    db.add(rfq)
    await db.commit()
    await db.refresh(rfq)
    
    return build_created_response(
        data=rfq_to_response(rfq),
        resource_name="RFQ",
    )


@router.get("/{rfq_id}", response_model=APIResponse)
async def get_rfq(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
):
    """
    Get a specific RFQ by ID.
    """
    query = select(RFQ).where(RFQ.id == rfq_id)
    
    if not include_deleted:
        query = query.where(RFQ.deleted_at.is_(None))
    
    result = await db.execute(query)
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    return build_response(data=rfq_to_response(rfq))


@router.patch("/{rfq_id}", response_model=APIResponse)
async def update_rfq(
    rfq_id: UUID,
    rfq_data: RFQUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update an RFQ.
    """
    result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    # Track status change
    update_dict = rfq_data.model_dump(exclude_unset=True)
    
    if "status" in update_dict and update_dict["status"] != rfq.status:
        rfq.previous_status = rfq.status
        rfq.status_changed_at = now_utc()
    
    # Apply updates
    for field, value in update_dict.items():
        setattr(rfq, field, value)
    
    rfq.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(rfq)
    
    return build_updated_response(
        data=rfq_to_response(rfq),
        resource_name="RFQ",
    )


@router.delete("/{rfq_id}", response_model=APIResponse)
async def delete_rfq(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
):
    """
    Delete an RFQ (soft delete by default).
    """
    result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id)
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    if rfq.deleted_at and not hard_delete:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    if hard_delete:
        if not current_user.is_superuser:
            raise ForbiddenError(message="Only administrators can permanently delete RFQs")
        await db.delete(rfq)
    else:
        rfq.deleted_at = now_utc()
        rfq.deleted_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="RFQ")


# =============================================================================
# RFQ Status/Workflow Endpoints
# =============================================================================


@router.post("/{rfq_id}/submit-quote", response_model=APIResponse)
async def mark_rfq_quoted(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Mark RFQ as quoted (quote has been sent).
    """
    result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    rfq.previous_status = rfq.status
    rfq.status = RFQStatus.QUOTED.value
    rfq.status_changed_at = now_utc()
    rfq.quoted_date = now_utc()
    rfq.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(rfq)
    
    return build_response(
        data=rfq_to_response(rfq),
        message="RFQ marked as quoted",
    )


@router.post("/{rfq_id}/win", response_model=APIResponse)
async def mark_rfq_won(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    win_reason: Optional[str] = Query(default=None, max_length=255),
):
    """
    Mark RFQ as won.
    """
    result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    rfq.previous_status = rfq.status
    rfq.status = RFQStatus.WON.value
    rfq.status_changed_at = now_utc()
    rfq.decision_date = now_utc()
    rfq.is_won = True
    rfq.win_loss_reason = win_reason
    rfq.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(rfq)
    
    return build_response(
        data=rfq_to_response(rfq),
        message="RFQ marked as won",
    )


@router.post("/{rfq_id}/lose", response_model=APIResponse)
async def mark_rfq_lost(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    loss_reason: Optional[str] = Query(default=None, max_length=255),
    competitor_id: Optional[UUID] = Query(default=None),
):
    """
    Mark RFQ as lost.
    """
    result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    rfq.previous_status = rfq.status
    rfq.status = RFQStatus.LOST.value
    rfq.status_changed_at = now_utc()
    rfq.decision_date = now_utc()
    rfq.is_won = False
    rfq.win_loss_reason = loss_reason
    rfq.competitor_id = competitor_id
    rfq.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(rfq)
    
    return build_response(
        data=rfq_to_response(rfq),
        message="RFQ marked as lost",
    )


@router.post("/{rfq_id}/no-bid", response_model=APIResponse)
async def mark_rfq_no_bid(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    reason: str = Query(..., max_length=255),
):
    """
    Mark RFQ as no-bid (declining to quote).
    """
    result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    rfq.previous_status = rfq.status
    rfq.status = RFQStatus.NO_BID.value
    rfq.status_changed_at = now_utc()
    rfq.no_bid_reason = reason
    rfq.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(rfq)
    
    return build_response(
        data=rfq_to_response(rfq),
        message="RFQ marked as no-bid",
    )


# =============================================================================
# RFQ Question Endpoints
# =============================================================================


@router.get("/{rfq_id}/questions", response_model=APIResponse)
async def list_rfq_questions(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    List all questions for an RFQ.
    """
    # Verify RFQ exists
    rfq_result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = rfq_result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    # Get questions
    result = await db.execute(
        select(RFQQuestion)
        .where(RFQQuestion.rfq_id == rfq_id)
        .order_by(RFQQuestion.created_at)
    )
    questions = result.scalars().all()
    
    return build_response(
        data=[question_to_response(q) for q in questions],
    )


@router.post("/{rfq_id}/questions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_rfq_question(
    rfq_id: UUID,
    question_data: QuestionCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Add a clarification question to an RFQ.
    """
    # Verify RFQ exists
    rfq_result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = rfq_result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    # Create question
    question = RFQQuestion(
        rfq_id=rfq_id,
        question=question_data.question,
        category=question_data.category,
        status=QuestionStatus.DRAFT.value,
        asked_by_id=current_user.id,
    )
    
    db.add(question)
    
    # Update RFQ status if needed
    if rfq.status == RFQStatus.RECEIVED.value:
        rfq.previous_status = rfq.status
        rfq.status = RFQStatus.QUESTIONS_PENDING.value
        rfq.status_changed_at = now_utc()
    
    await db.commit()
    await db.refresh(question)
    
    return build_created_response(
        data=question_to_response(question),
        resource_name="Question",
    )


@router.patch("/{rfq_id}/questions/{question_id}", response_model=APIResponse)
async def update_rfq_question(
    rfq_id: UUID,
    question_id: UUID,
    question_data: QuestionUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a question (add answer, change status).
    """
    result = await db.execute(
        select(RFQQuestion).where(
            RFQQuestion.id == question_id,
            RFQQuestion.rfq_id == rfq_id,
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise NotFoundError(resource="Question", identifier=str(question_id))
    
    update_dict = question_data.model_dump(exclude_unset=True)
    
    # Handle answer
    if "answer" in update_dict and update_dict["answer"]:
        question.answer = update_dict["answer"]
        question.answered_at = now_utc()
        question.answered_by_id = current_user.id
        question.status = QuestionStatus.ANSWERED.value
    
    # Handle status
    if "status" in update_dict:
        question.status = update_dict["status"]
    
    # Handle question text
    if "question" in update_dict:
        question.question = update_dict["question"]
    
    await db.commit()
    await db.refresh(question)
    
    return build_updated_response(
        data=question_to_response(question),
        resource_name="Question",
    )


@router.delete("/{rfq_id}/questions/{question_id}", response_model=APIResponse)
async def delete_rfq_question(
    rfq_id: UUID,
    question_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Delete a question from an RFQ.
    """
    result = await db.execute(
        select(RFQQuestion).where(
            RFQQuestion.id == question_id,
            RFQQuestion.rfq_id == rfq_id,
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise NotFoundError(resource="Question", identifier=str(question_id))
    
    await db.delete(question)
    await db.commit()
    
    return build_deleted_response(resource_name="Question")


# =============================================================================
# RFQ Statistics
# =============================================================================


@router.get("/{rfq_id}/stats", response_model=APIResponse)
async def get_rfq_stats(
    rfq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Get statistics for an RFQ.
    """
    result = await db.execute(
        select(RFQ).where(
            RFQ.id == rfq_id,
            RFQ.deleted_at.is_(None),
        )
    )
    rfq = result.scalar_one_or_none()
    
    if not rfq:
        raise NotFoundError(resource="RFQ", identifier=str(rfq_id))
    
    # Count questions
    questions = rfq.questions.all() if hasattr(rfq.questions, 'all') else []
    answered_count = sum(1 for q in questions if q.status == QuestionStatus.ANSWERED.value)
    
    # Count quotes
    quotes = rfq.quotes.all() if hasattr(rfq.quotes, 'all') else []
    
    stats = {
        "rfq_id": str(rfq.id),
        "rfq_number": rfq.rfq_number,
        "status": rfq.status,
        "is_open": rfq.is_open,
        "days_until_due": rfq.days_until_due,
        "questions": {
            "total": len(questions),
            "answered": answered_count,
            "pending": len(questions) - answered_count,
        },
        "quotes": {
            "total": len(quotes),
        },
        "qualification": {
            "is_qualified": rfq.is_qualified,
            "score": float(rfq.qualification_score) if rfq.qualification_score else None,
        },
    }
    
    return build_response(data=stats)

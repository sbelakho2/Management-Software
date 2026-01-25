"""
Opportunity Management Endpoints

Provides full CRUD and workflow operations for Sales Opportunities:
- Pipeline stage management
- Probability and forecasting
- Activity/Note tracking
- RFQ and Quote linking
"""

import inspect
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, ForbiddenError, NotFoundError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_paginated_response,
    build_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    maybe_await,
    now_utc,
    parse_sort_param,
)
from sensei.models.opportunity import (
    Opportunity,
    OpportunityStage,
    OpportunityType,
    OpportunitySource,
    OpportunityNote,
    NoteType,
)


AllowPipelineModule = deps.require_role(
    "sales",
    "sales_engineer",
    "estimator",
    "purchasing",
    "supply_chain",
    "engineering",
    "finance",
    "accountant",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "sales",
                    "sales_engineer",
                    "estimator",
                    "purchasing",
                    "supply_chain",
                    "engineering",
                    "finance",
                    "accountant",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)


# =============================================================================
# Schemas
# =============================================================================


class OpportunityBase(BaseModel):
    """Base opportunity fields."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    account_id: UUID
    primary_contact_id: Optional[UUID] = None
    
    stage: str = Field(default=OpportunityStage.PROSPECTING.value)
    opportunity_type: Optional[str] = None
    lead_source: Optional[str] = None
    
    amount: Optional[Decimal] = None
    currency: str = Field(default="MAD", max_length=3)
    probability: Optional[int] = Field(default=None, ge=0, le=100)
    
    close_date: Optional[date] = None
    
    
    custom_fields: Optional[dict] = None
    tags: Optional[list] = None


class OpportunityCreate(OpportunityBase):
    """Opportunity creation request."""
    pass


class OpportunityUpdate(BaseModel):
    """Opportunity update request."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    
    primary_contact_id: Optional[UUID] = None
    
    stage: Optional[str] = None
    opportunity_type: Optional[str] = None
    lead_source: Optional[str] = None
    
    amount: Optional[Decimal] = None
    currency: Optional[str] = Field(None, max_length=3)
    probability: Optional[int] = Field(None, ge=0, le=100)
    
    close_date: Optional[date] = None
    actual_close_date: Optional[date] = None
    
    is_closed: Optional[bool] = None
    is_won: Optional[bool] = None
    close_reason: Optional[str] = Field(None, max_length=255)
    competitor_id: Optional[UUID] = None
    
    
    next_step: Optional[str] = None
    next_step_date: Optional[date] = None
    
    
    forecast_category: Optional[str] = Field(None, max_length=50)
    
    custom_fields: Optional[dict] = None
    tags: Optional[list] = None


class OpportunityResponse(BaseModel):
    """Full opportunity response."""
    
    id: UUID
    opportunity_number: str
    
    name: str
    description: Optional[str]
    
    account_id: UUID
    primary_contact_id: Optional[UUID]
    
    stage: str
    opportunity_type: Optional[str]
    lead_source: Optional[str]
    
    amount: Optional[Decimal]
    currency: str
    probability: Optional[int]
    weighted_amount: Optional[Decimal]
    
    close_date: Optional[date]
    actual_close_date: Optional[date]
    
    is_closed: bool
    is_won: Optional[bool]
    close_reason: Optional[str]
    competitor_id: Optional[UUID]
    
    
    next_step: Optional[str]
    next_step_date: Optional[date]
    
    
    forecast_category: Optional[str]
    
    custom_fields: Optional[dict]
    tags: Optional[list]
    
    # Counts
    note_count: int = 0
    rfq_count: int = 0
    quote_count: int = 0
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class OpportunityListResponse(BaseModel):
    """Simplified opportunity for list views."""
    
    id: UUID
    opportunity_number: str
    name: str
    account_id: UUID
    stage: str
    amount: Optional[Decimal]
    currency: str
    probability: Optional[int]
    weighted_amount: Optional[Decimal]
    close_date: Optional[date]
    is_closed: bool
    is_won: Optional[bool]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NoteBase(BaseModel):
    """Base note fields."""
    
    content: str = Field(..., min_length=1)
    note_type: str = Field(default=NoteType.NOTE.value)


class NoteCreate(NoteBase):
    """Note creation request."""
    pass


class NoteUpdate(BaseModel):
    """Note update request."""
    
    content: Optional[str] = None
    note_type: Optional[str] = None


class NoteResponse(BaseModel):
    """Note response."""
    
    id: UUID
    opportunity_id: UUID
    content: str
    note_type: str
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class StageChangeRequest(BaseModel):
    """Request to change opportunity stage."""
    
    stage: str
    notes: Optional[str] = None


class CloseWonRequest(BaseModel):
    """Request to close opportunity as won."""
    
    actual_close_date: Optional[date] = None
    notes: Optional[str] = None


class CloseLostRequest(BaseModel):
    """Request to close opportunity as lost."""
    
    actual_close_date: Optional[date] = None
    close_reason: str = Field(..., max_length=255)
    competitor_id: Optional[UUID] = None
    notes: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def opportunity_to_response(opp: Opportunity) -> OpportunityResponse:
    """Convert opportunity model to response."""
    return OpportunityResponse(
        id=opp.id,
        opportunity_number=opp.opportunity_number,
        name=opp.name,
        description=opp.description,
        account_id=opp.account_id,
        primary_contact_id=opp.primary_contact_id,
        stage=opp.stage,
        opportunity_type=opp.opportunity_type,
        lead_source=opp.lead_source,
        amount=opp.amount,
        currency=opp.currency,
        probability=opp.probability,
        weighted_amount=opp.weighted_amount,
        close_date=opp.close_date,
        actual_close_date=opp.actual_close_date,
        is_closed=opp.is_closed,
        is_won=opp.is_won,
        close_reason=opp.close_reason,
        competitor_id=opp.competitor_id,
        next_step=opp.next_step,
        next_step_date=opp.next_step_date,
        forecast_category=opp.forecast_category,
        custom_fields=opp.custom_fields,
        tags=opp.tags,
        note_count=len(opp.notes.all()) if hasattr(opp.notes, 'all') else 0,
        rfq_count=len(opp.rfqs.all()) if hasattr(opp.rfqs, 'all') else 0,
        quote_count=len(opp.quotes.all()) if hasattr(opp.quotes, 'all') else 0,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
        created_by_id=opp.created_by_id,
    )


def opportunity_to_list_response(opp: Opportunity) -> OpportunityListResponse:
    """Convert opportunity model to list response."""
    return OpportunityListResponse(
        id=opp.id,
        opportunity_number=opp.opportunity_number,
        name=opp.name,
        account_id=opp.account_id,
        stage=opp.stage,
        amount=opp.amount,
        currency=opp.currency,
        probability=opp.probability,
        weighted_amount=opp.weighted_amount,
        close_date=opp.close_date,
        is_closed=opp.is_closed,
        is_won=opp.is_won,
        created_at=opp.created_at,
    )


def note_to_response(note: OpportunityNote) -> NoteResponse:
    """Convert note model to response."""
    return NoteResponse(
        id=note.id,
        opportunity_id=note.opportunity_id,
        content=note.content,
        note_type=note.note_type,
        created_at=note.created_at,
        updated_at=note.updated_at,
        created_by_id=note.created_by_id,
    )


async def generate_opportunity_number(db: DBSession) -> str:
    """Generate unique opportunity number."""
    year = datetime.now().year
    prefix = f"OPP-{year}-"
    
    # Find the highest existing number for this year
    result = await db.execute(
        select(func.max(Opportunity.opportunity_number))
        .where(Opportunity.opportunity_number.like(f"{prefix}%"))
    )
    last_number = result.scalar()
    
    if last_number:
        # Extract the sequence number and increment
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1
    
    return f"{prefix}{seq:05d}"


# Stage probability mapping
STAGE_PROBABILITIES = {
    OpportunityStage.PROSPECTING.value: 10,
    OpportunityStage.QUALIFICATION.value: 20,
    OpportunityStage.NEEDS_ANALYSIS.value: 40,
    OpportunityStage.VALUE_PROPOSITION.value: 50,
    OpportunityStage.PROPOSAL.value: 60,
    OpportunityStage.NEGOTIATION.value: 80,
    OpportunityStage.CLOSED_WON.value: 100,
    OpportunityStage.CLOSED_LOST.value: 0,
}


# =============================================================================
# Opportunity CRUD Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse)
async def list_opportunities(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=100),
    stage: Optional[str] = Query(default=None),
    account_id: Optional[UUID] = Query(default=None),
    assigned_to_id: Optional[UUID] = Query(default=None),
    is_closed: Optional[bool] = Query(default=None),
    is_won: Optional[bool] = Query(default=None),
    min_amount: Optional[Decimal] = Query(default=None),
    max_amount: Optional[Decimal] = Query(default=None),
    close_date_before: Optional[date] = Query(default=None),
    close_date_after: Optional[date] = Query(default=None),
    sort: str = Query(default="-created_at"),
    include_deleted: bool = Query(default=False),
):
    """
    List opportunities with filtering, sorting, and pagination.
    """
    # Build query
    query = select(Opportunity)
    count_query = select(func.count(Opportunity.id))
    
    # Soft delete filter
    if not include_deleted:
        query = query.where(Opportunity.deleted_at.is_(None))
        count_query = count_query.where(Opportunity.deleted_at.is_(None))
    
    # Search filter
    if search:
        search_filter = or_(
            Opportunity.opportunity_number.ilike(f"%{search}%"),
            Opportunity.name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Stage filter
    if stage:
        query = query.where(Opportunity.stage == stage)
        count_query = count_query.where(Opportunity.stage == stage)
    
    # Account filter
    if account_id:
        query = query.where(Opportunity.account_id == account_id)
        count_query = count_query.where(Opportunity.account_id == account_id)
    
    # Assigned to filter
    if assigned_to_id:
        query = query.where(Opportunity.owner_id == assigned_to_id)
        count_query = count_query.where(Opportunity.owner_id == assigned_to_id)
    
    # Closed filter (use stage comparison since is_closed is a computed property)
    if is_closed is not None:
        closed_stages = [OpportunityStage.CLOSED_WON.value, OpportunityStage.CLOSED_LOST.value]
        if is_closed:
            query = query.where(Opportunity.stage.in_(closed_stages))
            count_query = count_query.where(Opportunity.stage.in_(closed_stages))
        else:
            query = query.where(Opportunity.stage.notin_(closed_stages))
            count_query = count_query.where(Opportunity.stage.notin_(closed_stages))
    
    # Won filter
    if is_won is not None:
        query = query.where(Opportunity.is_won == is_won)
        count_query = count_query.where(Opportunity.is_won == is_won)
    
    # Amount filters
    if min_amount is not None:
        query = query.where(Opportunity.amount >= min_amount)
        count_query = count_query.where(Opportunity.amount >= min_amount)
    
    if max_amount is not None:
        query = query.where(Opportunity.amount <= max_amount)
        count_query = count_query.where(Opportunity.amount <= max_amount)
    
    # Expected close date filters
    if close_date_before:
        query = query.where(Opportunity.close_date <= close_date_before)
        count_query = count_query.where(Opportunity.close_date <= close_date_before)
    
    if close_date_after:
        query = query.where(Opportunity.close_date >= close_date_after)
        count_query = count_query.where(Opportunity.close_date >= close_date_after)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_orders = parse_sort_param(sort)
    for sort_order in sort_orders:
        if hasattr(Opportunity, sort_order.field):
            column = getattr(Opportunity, sort_order.field)
            query = query.order_by(column.desc() if sort_order.direction == "desc" else column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    opportunities = result.scalars().all()
    
    # Convert to response
    items = [opportunity_to_list_response(o) for o in opportunities]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    opp_data: OpportunityCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Create a new opportunity.
    """
    # Generate opportunity number
    opp_number = await generate_opportunity_number(db)
    
    # Create opportunity
    opp_dict = opp_data.model_dump(exclude_unset=True)
    
    # Set defaults for fields that have server-side defaults but need Python-side values
    if "stage" not in opp_dict:
        opp_dict["stage"] = OpportunityStage.PROSPECTING.value
    if "currency" not in opp_dict:
        opp_dict["currency"] = "MAD"
    
    # Set default probability based on stage if not provided
    if opp_dict.get("probability") is None:
        opp_dict["probability"] = STAGE_PROBABILITIES.get(
            opp_dict.get("stage", OpportunityStage.PROSPECTING.value), 10
        )
    
    opp = Opportunity(
        **opp_dict,
        opportunity_number=opp_number,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    
    # Calculate weighted amount
    opp.calculate_weighted_amount()
    
    await maybe_await(db.add(opp))
    await db.commit()
    await db.refresh(opp)
    
    return build_created_response(
        data=opportunity_to_response(opp),
        resource_name="Opportunity",
    )


@router.get("/{opportunity_id}", response_model=APIResponse)
async def get_opportunity(
    opportunity_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
):
    """
    Get a specific opportunity by ID.
    """
    query = select(Opportunity).where(Opportunity.id == opportunity_id)
    
    if not include_deleted:
        query = query.where(Opportunity.deleted_at.is_(None))
    
    result = await db.execute(query)
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    return build_response(data=opportunity_to_response(opp))


@router.patch("/{opportunity_id}", response_model=APIResponse)
async def update_opportunity(
    opportunity_id: UUID,
    opp_data: OpportunityUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update an opportunity.
    """
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    # Apply updates
    update_dict = opp_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(opp, field, value)
    
    # Recalculate weighted amount if amount or probability changed
    if "amount" in update_dict or "probability" in update_dict:
        opp.calculate_weighted_amount()
    
    opp.updated_by_id = current_user.id
    
    await db.commit()
    await db.refresh(opp)
    
    return build_updated_response(
        data=opportunity_to_response(opp),
        resource_name="Opportunity",
    )


@router.delete("/{opportunity_id}", response_model=APIResponse)
async def delete_opportunity(
    opportunity_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
):
    """
    Delete an opportunity (soft delete by default).
    """
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    if opp.deleted_at and not hard_delete:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    if hard_delete:
        if not current_user.is_superuser:
            raise ForbiddenError(message="Only administrators can permanently delete opportunities")
        await db.delete(opp)
    else:
        opp.deleted_at = now_utc()
        opp.deleted_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Opportunity")


# =============================================================================
# Opportunity Stage/Workflow Endpoints
# =============================================================================


@router.post("/{opportunity_id}/change-stage", response_model=APIResponse)
async def change_opportunity_stage(
    opportunity_id: UUID,
    request: StageChangeRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Change opportunity stage with optional notes.
    """
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    if opp.is_closed:
        raise ConflictError(message="Cannot change stage of a closed opportunity")
    
    # Validate stage
    try:
        new_stage = OpportunityStage(request.stage)
    except ValueError:
        raise ConflictError(message=f"Invalid stage: {request.stage}")
    
    old_stage = opp.stage
    opp.stage = new_stage.value
    
    # Update probability based on stage
    opp.probability = STAGE_PROBABILITIES.get(new_stage.value, opp.probability)
    opp.calculate_weighted_amount()
    
    # Handle closed stages
    if new_stage == OpportunityStage.CLOSED_WON:
        opp.is_won = True
        opp.actual_close_date = datetime.combine(date.today(), datetime.min.time())
    elif new_stage == OpportunityStage.CLOSED_LOST:
        opp.is_won = False
        opp.actual_close_date = datetime.combine(date.today(), datetime.min.time())
    
    opp.updated_by_id = current_user.id
    
    # Add note if provided
    if request.notes:
        note = OpportunityNote(
            opportunity_id=opportunity_id,
            content=f"Stage changed from {old_stage} to {new_stage.value}: {request.notes}",
            note_type=NoteType.STATUS_CHANGE.value,
            created_by_id=current_user.id,
        )
        await maybe_await(db.add(note))
    
    await db.commit()
    await db.refresh(opp)
    
    return build_response(
        data=opportunity_to_response(opp),
        message=f"Stage changed to {new_stage.value}",
    )


@router.post("/{opportunity_id}/close-won", response_model=APIResponse)
async def close_opportunity_won(
    opportunity_id: UUID,
    request: CloseWonRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Close opportunity as won.
    """
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    if opp.is_closed:
        raise ConflictError(message="Opportunity is already closed")
    
    opp.stage = OpportunityStage.CLOSED_WON.value
    opp.is_won = True
    opp.is_closed = True
    opp.is_open = False
    opp.probability = 100
    opp.actual_close_date = datetime.combine(request.actual_close_date or date.today(), datetime.min.time())
    opp.calculate_weighted_amount()
    opp.updated_by_id = current_user.id
    
    # Add note if provided
    if request.notes:
        note = OpportunityNote(
            opportunity_id=opportunity_id,
            content=f"Closed Won: {request.notes}",
            note_type=NoteType.STATUS_CHANGE.value,
            created_by_id=current_user.id,
        )
        await maybe_await(db.add(note))
    
    await db.commit()
    await db.refresh(opp)
    
    return build_response(
        data=opportunity_to_response(opp),
        message="Opportunity closed as won",
    )


@router.post("/{opportunity_id}/close-lost", response_model=APIResponse)
async def close_opportunity_lost(
    opportunity_id: UUID,
    request: CloseLostRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Close opportunity as lost.
    """
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    if opp.is_closed:
        raise ConflictError(message="Opportunity is already closed")
    
    opp.stage = OpportunityStage.CLOSED_LOST.value
    opp.is_won = False
    opp.is_closed = True
    opp.is_open = False
    opp.probability = 0
    opp.actual_close_date = datetime.combine(request.actual_close_date or date.today(), datetime.min.time())
    opp.close_reason = request.close_reason
    opp.competitor_id = request.competitor_id
    opp.calculate_weighted_amount()
    opp.updated_by_id = current_user.id
    
    # Add note
    note_content = f"Closed Lost: {request.close_reason}"
    if request.competitor_id:
        note_content += f" (Competitor: {request.competitor_id})"
    if request.notes:
        note_content += f" - {request.notes}"
    
    note = OpportunityNote(
        opportunity_id=opportunity_id,
        content=note_content,
        note_type=NoteType.STATUS_CHANGE.value,
        created_by_id=current_user.id,
    )
    await maybe_await(db.add(note))
    
    await db.commit()
    await db.refresh(opp)
    
    return build_response(
        data=opportunity_to_response(opp),
        message="Opportunity closed as lost",
    )


@router.post("/{opportunity_id}/reopen", response_model=APIResponse)
async def reopen_opportunity(
    opportunity_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    stage: Optional[str] = Query(default=None),
):
    """
    Reopen a closed opportunity.
    """
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    if not opp.is_closed:
        raise ConflictError(message="Opportunity is not closed")
    
    # Determine new stage
    if stage:
        try:
            new_stage = OpportunityStage(stage)
        except ValueError:
            raise ConflictError(message=f"Invalid stage: {stage}")
    else:
        new_stage = OpportunityStage.NEGOTIATION  # Default to negotiation
    
    opp.stage = new_stage.value
    opp.is_won = None
    opp.is_closed = False
    opp.is_open = True
    opp.actual_close_date = None
    opp.probability = STAGE_PROBABILITIES.get(new_stage.value, 50)
    opp.calculate_weighted_amount()
    opp.updated_by_id = current_user.id
    
    # Add note
    note = OpportunityNote(
        opportunity_id=opportunity_id,
        content=f"Reopened to stage: {new_stage.value}",
        note_type=NoteType.STATUS_CHANGE.value,
        created_by_id=current_user.id,
    )
    await maybe_await(db.add(note))
    
    await db.commit()
    await db.refresh(opp)
    
    return build_response(
        data=opportunity_to_response(opp),
        message="Opportunity reopened",
    )


# =============================================================================
# Opportunity Notes Endpoints
# =============================================================================


@router.get("/{opportunity_id}/notes", response_model=APIResponse)
async def list_opportunity_notes(
    opportunity_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    note_type: Optional[str] = Query(default=None),
):
    """
    List all notes for an opportunity.
    """
    # Verify opportunity exists
    opp_result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = opp_result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    # Build query
    query = (
        select(OpportunityNote)
        .where(OpportunityNote.opportunity_id == opportunity_id)
        .order_by(OpportunityNote.created_at.desc())
    )
    
    if note_type:
        query = query.where(OpportunityNote.note_type == note_type)
    
    result = await db.execute(query)
    notes = result.scalars().all()
    
    return build_response(
        data=[note_to_response(n) for n in notes],
    )


@router.post("/{opportunity_id}/notes", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_opportunity_note(
    opportunity_id: UUID,
    note_data: NoteCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Add a note to an opportunity.
    """
    # Verify opportunity exists
    opp_result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    opp = opp_result.scalar_one_or_none()
    
    if not opp:
        raise NotFoundError(resource="Opportunity", identifier=str(opportunity_id))
    
    # Create note
    note = OpportunityNote(
        opportunity_id=opportunity_id,
        content=note_data.content,
        note_type=note_data.note_type,
        created_by_id=current_user.id,
    )
    
    await maybe_await(db.add(note))
    await db.commit()
    await db.refresh(note)
    
    return build_created_response(
        data=note_to_response(note),
        resource_name="Note",
    )


@router.patch("/{opportunity_id}/notes/{note_id}", response_model=APIResponse)
async def update_opportunity_note(
    opportunity_id: UUID,
    note_id: UUID,
    note_data: NoteUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Update a note.
    """
    result = await db.execute(
        select(OpportunityNote).where(
            OpportunityNote.id == note_id,
            OpportunityNote.opportunity_id == opportunity_id,
        )
    )
    note = result.scalar_one_or_none()
    
    if not note:
        raise NotFoundError(resource="Note", identifier=str(note_id))
    
    # Update fields
    update_dict = note_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(note, field, value)
    
    await db.commit()
    await db.refresh(note)
    
    return build_updated_response(
        data=note_to_response(note),
        resource_name="Note",
    )


@router.delete("/{opportunity_id}/notes/{note_id}", response_model=APIResponse)
async def delete_opportunity_note(
    opportunity_id: UUID,
    note_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    Delete a note from an opportunity.
    """
    result = await db.execute(
        select(OpportunityNote).where(
            OpportunityNote.id == note_id,
            OpportunityNote.opportunity_id == opportunity_id,
        )
    )
    note = result.scalar_one_or_none()
    
    if not note:
        raise NotFoundError(resource="Note", identifier=str(note_id))
    
    await db.delete(note)
    await db.commit()
    
    return build_deleted_response(resource_name="Note")


# =============================================================================
# Pipeline and Forecasting
# =============================================================================


@router.get("/pipeline/summary", response_model=APIResponse)
async def get_pipeline_summary(
    db: DBSession,
    current_user: CurrentUser,
    account_id: Optional[UUID] = Query(default=None),
    assigned_to_id: Optional[UUID] = Query(default=None),
):
    """
    Get pipeline summary by stage.
    """
    # Base query - only open opportunities (not closed)
    closed_stages = [OpportunityStage.CLOSED_WON.value, OpportunityStage.CLOSED_LOST.value]
    base_filter: list[Any] = [
        Opportunity.deleted_at.is_(None),
        Opportunity.stage.notin_(closed_stages),
    ]
    
    if account_id:
        base_filter.append(Opportunity.account_id == account_id)
    
    if assigned_to_id:
        base_filter.append(Opportunity.owner_id == assigned_to_id)
    
    # Get summary by stage
    result = await db.execute(
        select(
            Opportunity.stage,
            func.count(Opportunity.id).label("opp_count"),
            func.sum(Opportunity.amount).label("total_amount"),
            func.sum(Opportunity.weighted_amount).label("weighted_amount"),
        )
        .where(*base_filter)
        .group_by(Opportunity.stage)
    )
    rows = result.all()
    
    # Build response
    stages = {}
    total_count = 0
    total_amount = Decimal("0")
    total_weighted = Decimal("0")
    
    for row in rows:
        row_count = int(row.opp_count) if row.opp_count else 0
        row_total = Decimal(str(row.total_amount)) if row.total_amount else Decimal("0")
        row_weighted = Decimal(str(row.weighted_amount)) if row.weighted_amount else Decimal("0")
        
        stage_data = {
            "count": row_count,
            "total_amount": float(row_total),
            "weighted_amount": float(row_weighted),
        }
        stages[row.stage] = stage_data
        total_count += row_count
        total_amount += row_total
        total_weighted += row_weighted
    
    summary = {
        "stages": stages,
        "totals": {
            "count": total_count,
            "total_amount": float(total_amount),
            "weighted_amount": float(total_weighted),
        },
    }
    
    return build_response(data=summary)


@router.get("/pipeline/forecast", response_model=APIResponse)
async def get_forecast(
    db: DBSession,
    current_user: CurrentUser,
    period_start: date = Query(...),
    period_end: date = Query(...),
    account_id: Optional[UUID] = Query(default=None),
    assigned_to_id: Optional[UUID] = Query(default=None),
):
    """
    Get forecast for a period.
    """
    # Base filter - open opportunities with expected close in period
    closed_stages = [OpportunityStage.CLOSED_WON.value, OpportunityStage.CLOSED_LOST.value]
    base_filter: list[Any] = [
        Opportunity.deleted_at.is_(None),
        Opportunity.stage.notin_(closed_stages),
        Opportunity.close_date >= period_start,
        Opportunity.close_date <= period_end,
    ]
    
    if account_id:
        base_filter.append(Opportunity.account_id == account_id)
    
    if assigned_to_id:
        base_filter.append(Opportunity.owner_id == assigned_to_id)
    
    # Get opportunities
    result = await db.execute(
        select(Opportunity).where(*base_filter)
    )
    opportunities = result.scalars().all()
    
    # Calculate totals by probability bands
    commit_count = 0
    commit_amount = Decimal("0")
    best_case_count = 0
    best_case_amount = Decimal("0")
    pipeline_count = 0
    pipeline_amount = Decimal("0")
    
    for opp in opportunities:
        prob = opp.probability or 0
        amount = opp.amount or Decimal("0")
        
        pipeline_count += 1
        pipeline_amount += amount
        
        if prob >= 50:
            best_case_count += 1
            best_case_amount += amount
        
        if prob >= 80:
            commit_count += 1
            commit_amount += amount
    
    forecast = {
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "commit": {
            "count": commit_count,
            "amount": float(commit_amount),
        },
        "best_case": {
            "count": best_case_count,
            "amount": float(best_case_amount),
        },
        "pipeline": {
            "count": pipeline_count,
            "amount": float(pipeline_amount),
        },
        "weighted_pipeline": sum(
            float(o.weighted_amount or 0) for o in opportunities
        ),
    }
    
    return build_response(data=forecast)

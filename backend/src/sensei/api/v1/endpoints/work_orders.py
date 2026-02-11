"""Work Orders API endpoints.

Provides CRUD operations for work orders and their operations,
supporting production scheduling and tracking.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Header
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, func, or_, and_, ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.api.deps import get_current_user, get_db
from sensei.api.exceptions import NotFoundError, ConflictError, BadRequestError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import build_response, build_paginated_response, build_created_response, build_updated_response, build_deleted_response
from sensei.models.user import User
from sensei.models.work_order import (
    WorkOrder,
    WorkOrderOperation,
    WorkOrderStatus,
    WorkOrderPriority,
    OperationStatus,
    HoldReason,
)
from sensei.models.quote import Quote
from sensei.services.core.common_thread import get_common_thread_service
from sensei.services.production.jidoka_error_proofing import JidokaErrorProofingService
from sensei.services.core.data_lineage import get_data_lineage_service
from sensei.services.finance.gl_posting import post_wo_completion_to_gl


logger = logging.getLogger(__name__)

from sensei.api import deps

AllowWorkOrdersModule = deps.require_role(
    "ops",
    "supervisor",
    "team_lead",
    "operator",
    "quality",
    "engineering",
    "maintenance",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "ops",
                    "supervisor",
                    "team_lead",
                    "operator",
                    "quality",
                    "engineering",
                    "maintenance",
                ]
            )
        )
    ]
)

# Type aliases for dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# =============================================================================
# Pydantic Schemas
# =============================================================================


class WorkOrderCreate(BaseModel):
    """Schema for creating a work order."""
    
    work_order_number: str = Field(..., min_length=1, max_length=50)
    external_reference: Optional[str] = Field(None, max_length=100)
    quote_id: Optional[UUID] = None
    product_id: UUID
    quantity_ordered: Decimal = Field(..., gt=0)
    priority: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    work_center_id: Optional[int] = Field(None, gt=0)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    lot_number: Optional[str] = Field(None, max_length=50)
    batch_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    production_notes: Optional[str] = None
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v is None:
            return v
        valid = [p.value for p in WorkOrderPriority]
        if v not in valid:
            raise ValueError(f"Invalid priority. Must be one of: {valid}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        valid = [s.value for s in WorkOrderStatus]
        if v not in valid:
            raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v

class WorkOrderUpdate(BaseModel):
    """Schema for updating a work order."""
    
    work_order_number: Optional[str] = Field(None, min_length=1, max_length=50)
    external_reference: Optional[str] = Field(None, max_length=100)
    quantity_ordered: Optional[Decimal] = Field(None, gt=0)
    priority: Optional[str] = None
    status: Optional[str] = None
    work_center_id: Optional[int] = Field(None, gt=0)
    current_station_id: Optional[int] = Field(None, gt=0)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    lot_number: Optional[str] = Field(None, max_length=50)
    batch_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    production_notes: Optional[str] = None
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v is None:
            return v
        valid = [p.value for p in WorkOrderPriority]
        if v not in valid:
            raise ValueError(f"Invalid priority. Must be one of: {valid}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        valid = [s.value for s in WorkOrderStatus]
        if v not in valid:
            raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class WorkOrderHold(BaseModel):
    """Schema for putting a work order on hold."""
    
    reason: str
    notes: Optional[str] = None
    
    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v):
        valid = [r.value for r in HoldReason]
        if v not in valid:
            raise ValueError(f"Invalid hold reason. Must be one of: {valid}")
        return v


class WorkOrderRelease(BaseModel):
    """Schema for releasing a work order from draft."""
    
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class WorkOrderOperationResponse(BaseModel):
    """Response schema for work order operations."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    work_order_id: int
    routing_id: Optional[int]
    sequence: int
    operation_name: str
    station_id: int
    standard_time_seconds: int
    setup_time_seconds: int
    status: str
    blocked_reason: Optional[str]
    quantity_completed: Decimal
    quantity_scrapped: Decimal
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    actual_time_seconds: Optional[int]
    actual_setup_seconds: Optional[int]
    operator_id: Optional[str]
    notes: Optional[str]
    efficiency: Optional[Decimal]
    elapsed_time_seconds: Optional[int]
    is_active: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    


class WorkOrderResponse(BaseModel):
    """Response schema for work orders."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    work_order_number: str
    external_reference: Optional[str]
    product_id: UUID
    quantity_ordered: Decimal
    quantity_completed: Decimal
    quantity_scrapped: Decimal
    quantity_in_progress: Decimal
    quantity_remaining: Decimal
    completion_percentage: Decimal
    yield_percentage: Decimal
    priority: str
    status: str
    hold_reason: Optional[str]
    hold_notes: Optional[str]
    held_at: Optional[datetime]
    held_by_id: Optional[str]
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    work_center_id: Optional[int]
    current_station_id: Optional[int]
    current_operation_sequence: Optional[int]
    lot_number: Optional[str]
    batch_id: Optional[str]
    notes: Optional[str]
    production_notes: Optional[str]
    jidoka_suggestions: Optional[list["JidokaSuggestionResponse"]] = None
    is_late: bool
    is_on_hold: bool
    operation_count: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str]
    updated_by_id: Optional[str]
    


class JidokaSuggestionResponse(BaseModel):
    """Deterministic poka-yoke suggestions derived from NCR/NC patterns."""

    title: str
    rationale: str
    actions: list[str]
    related_non_conformance_ids: list[int]
    confidence: float


class WorkOrderListResponse(BaseModel):
    """Response schema for work order list items."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    work_order_number: str
    external_reference: Optional[str]
    product_id: UUID
    quantity_ordered: Decimal
    quantity_completed: Decimal
    completion_percentage: Decimal
    priority: str
    status: str
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    work_center_id: Optional[int]
    is_late: bool
    is_on_hold: bool
    created_at: datetime
    


class WorkOrderStatsResponse(BaseModel):
    """Response schema for work order statistics."""
    
    total_work_orders: int
    draft_count: int
    released_count: int
    in_progress_count: int
    on_hold_count: int
    completed_count: int
    cancelled_count: int
    late_count: int
    total_quantity_ordered: Decimal
    total_quantity_completed: Decimal
    average_completion_percentage: Decimal


class OperationCreate(BaseModel):
    """Schema for creating a work order operation."""
    
    routing_id: Optional[int] = Field(None, gt=0)
    sequence: int = Field(..., gt=0)
    operation_name: str = Field(..., min_length=1, max_length=255)
    station_id: int = Field(..., gt=0)
    standard_time_seconds: int = Field(default=60, ge=0)
    setup_time_seconds: int = Field(default=0, ge=0)
    notes: Optional[str] = None


class OperationUpdate(BaseModel):
    """Schema for updating a work order operation."""
    
    operation_name: Optional[str] = Field(None, min_length=1, max_length=255)
    station_id: Optional[int] = Field(None, gt=0)
    standard_time_seconds: Optional[int] = Field(None, ge=0)
    setup_time_seconds: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    blocked_reason: Optional[str] = None
    quantity_completed: Optional[Decimal] = Field(None, ge=0)
    quantity_scrapped: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        valid = [s.value for s in OperationStatus]
        if v not in valid:
            raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class OperationStart(BaseModel):
    """Schema for starting an operation."""
    
    operator_id: Optional[str] = None


class OperationComplete(BaseModel):
    """Schema for completing an operation."""
    
    quantity_completed: Decimal = Field(..., ge=0)
    quantity_scrapped: Decimal = Field(default=Decimal("0"), ge=0)
    actual_time_seconds: Optional[int] = Field(None, ge=0)
    actual_setup_seconds: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


# =============================================================================
# Conversion Functions
# =============================================================================


def operation_to_response(operation: WorkOrderOperation) -> WorkOrderOperationResponse:
    """Convert WorkOrderOperation model to response schema."""
    status_value = operation.status.value if isinstance(operation.status, OperationStatus) else operation.status
    operator_id = str(operation.operator_id) if operation.operator_id else None
    
    return WorkOrderOperationResponse(
        id=operation.id,
        work_order_id=operation.work_order_id,
        routing_id=operation.routing_id,
        sequence=operation.sequence,
        operation_name=operation.operation_name,
        station_id=operation.station_id,
        standard_time_seconds=operation.standard_time_seconds,
        setup_time_seconds=operation.setup_time_seconds,
        status=status_value,
        blocked_reason=operation.blocked_reason,
        quantity_completed=operation.quantity_completed,
        quantity_scrapped=operation.quantity_scrapped,
        started_at=operation.started_at,
        completed_at=operation.completed_at,
        actual_time_seconds=operation.actual_time_seconds,
        actual_setup_seconds=operation.actual_setup_seconds,
        operator_id=operator_id,
        notes=operation.notes,
        efficiency=operation.efficiency,
        elapsed_time_seconds=operation.elapsed_time_seconds,
        is_active=operation.is_active,
        is_blocked=operation.is_blocked,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


def work_order_to_response(work_order: WorkOrder) -> WorkOrderResponse:
    """Convert WorkOrder model to response schema."""
    status_value = work_order.status.value if isinstance(work_order.status, WorkOrderStatus) else work_order.status
    priority_value = work_order.priority.value if isinstance(work_order.priority, WorkOrderPriority) else work_order.priority
    hold_reason_value = work_order.hold_reason.value if work_order.hold_reason and isinstance(work_order.hold_reason, HoldReason) else work_order.hold_reason
    
    return WorkOrderResponse(
        id=work_order.id,
        work_order_number=work_order.work_order_number,
        external_reference=work_order.external_reference,
        product_id=work_order.product_id,
        quantity_ordered=work_order.quantity_ordered,
        quantity_completed=work_order.quantity_completed,
        quantity_scrapped=work_order.quantity_scrapped,
        quantity_in_progress=work_order.quantity_in_progress,
        quantity_remaining=work_order.quantity_remaining,
        completion_percentage=work_order.completion_percentage,
        yield_percentage=work_order.yield_percentage,
        priority=priority_value,
        status=status_value,
        hold_reason=hold_reason_value,
        hold_notes=work_order.hold_notes,
        held_at=work_order.held_at,
        held_by_id=str(work_order.held_by_id) if work_order.held_by_id else None,
        scheduled_start=work_order.scheduled_start,
        scheduled_end=work_order.scheduled_end,
        actual_start=work_order.actual_start,
        actual_end=work_order.actual_end,
        work_center_id=work_order.work_center_id,
        current_station_id=work_order.current_station_id,
        current_operation_sequence=work_order.current_operation_sequence,
        lot_number=work_order.lot_number,
        batch_id=work_order.batch_id,
        notes=work_order.notes,
        production_notes=work_order.production_notes,
        is_late=work_order.is_late,
        is_on_hold=work_order.is_on_hold,
        operation_count=len(work_order.operations) if work_order.operations else 0,
        created_at=work_order.created_at,
        updated_at=work_order.updated_at,
        created_by_id=str(work_order.created_by_id) if work_order.created_by_id else None,
        updated_by_id=str(work_order.updated_by_id) if work_order.updated_by_id else None,
    )


def work_order_to_list_response(work_order: WorkOrder) -> WorkOrderListResponse:
    """Convert WorkOrder model to list response schema."""
    status_value = work_order.status.value if isinstance(work_order.status, WorkOrderStatus) else work_order.status
    priority_value = work_order.priority.value if isinstance(work_order.priority, WorkOrderPriority) else work_order.priority
    
    return WorkOrderListResponse(
        id=work_order.id,
        work_order_number=work_order.work_order_number,
        external_reference=work_order.external_reference,
        product_id=work_order.product_id,
        quantity_ordered=work_order.quantity_ordered,
        quantity_completed=work_order.quantity_completed,
        completion_percentage=work_order.completion_percentage,
        priority=priority_value,
        status=status_value,
        scheduled_start=work_order.scheduled_start,
        scheduled_end=work_order.scheduled_end,
        work_center_id=work_order.work_center_id,
        is_late=work_order.is_late,
        is_on_hold=work_order.is_on_hold,
        created_at=work_order.created_at,
    )


# =============================================================================
# Work Order Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse[WorkOrderListResponse])
async def list_work_orders(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    work_center_id: Optional[int] = Query(None, description="Filter by work center"),
    product_id: Optional[int] = Query(None, description="Filter by product"),
    is_late: Optional[bool] = Query(None, description="Filter by late status"),
    search: Optional[str] = Query(None, description="Search in work order number, lot number, external reference"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
) -> PaginatedResponse[WorkOrderListResponse]:
    """
    List work orders with filtering and pagination.
    """
    # Base query
    query = select(WorkOrder).options(selectinload(WorkOrder.operations))
    count_query = select(func.count(WorkOrder.id))
    
    # Soft delete filter
    if not include_deleted:
        query = query.where(WorkOrder.deleted_at.is_(None))
        count_query = count_query.where(WorkOrder.deleted_at.is_(None))
    
    # Status filter
    if status:
        try:
            status_enum = WorkOrderStatus(status)
            query = query.where(WorkOrder.status == status_enum)
            count_query = count_query.where(WorkOrder.status == status_enum)
        except ValueError:
            raise BadRequestError(f"Invalid status: {status}")
    
    # Priority filter
    if priority:
        try:
            priority_enum = WorkOrderPriority(priority)
            query = query.where(WorkOrder.priority == priority_enum)
            count_query = count_query.where(WorkOrder.priority == priority_enum)
        except ValueError:
            raise BadRequestError(f"Invalid priority: {priority}")
    
    # Work center filter
    if work_center_id:
        query = query.where(WorkOrder.work_center_id == work_center_id)
        count_query = count_query.where(WorkOrder.work_center_id == work_center_id)
    
    # Product filter
    if product_id:
        query = query.where(WorkOrder.product_id == product_id)
        count_query = count_query.where(WorkOrder.product_id == product_id)
    
    # Search filter
    if search:
        search_filter = or_(
            WorkOrder.work_order_number.ilike(f"%{search}%"),
            WorkOrder.lot_number.ilike(f"%{search}%"),
            WorkOrder.external_reference.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Sorting
    sort_column = getattr(WorkOrder, sort_by, WorkOrder.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    wo_result = await db.execute(query)
    work_orders: list[WorkOrder] = list(wo_result.scalars().all())
    
    # Filter for late work orders after fetching if needed
    if is_late is not None:
        work_orders = [wo for wo in work_orders if wo.is_late == is_late]
        # Recalculate total for late filter (approximation)
        if is_late:
            total = len([wo for wo in work_orders if wo.is_late])
    
    # Convert to response
    items = [work_order_to_list_response(wo) for wo in work_orders]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse[WorkOrderResponse], status_code=201)
async def create_work_order(
    data: WorkOrderCreate,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[WorkOrderResponse]:
    """
    Create a new work order.
    """
    # Check for duplicate work order number
    existing = await db.execute(
        select(WorkOrder).where(
            WorkOrder.work_order_number == data.work_order_number,
            WorkOrder.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Work order with number '{data.work_order_number}' already exists")
    
    # Parse enums
    priority_enum = WorkOrderPriority(data.priority) if data.priority else WorkOrderPriority.NORMAL
    status_enum = WorkOrderStatus(data.status) if data.status else WorkOrderStatus.DRAFT
    
    # Create work order
    work_order = WorkOrder(
        work_order_number=data.work_order_number,
        external_reference=data.external_reference,
        product_id=data.product_id,
        quantity_ordered=data.quantity_ordered,
        priority=priority_enum,
        status=status_enum,
        work_center_id=data.work_center_id,
        scheduled_start=data.scheduled_start,
        scheduled_end=data.scheduled_end,
        lot_number=data.lot_number,
        batch_id=data.batch_id,
        notes=data.notes,
        production_notes=data.production_notes,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    
    db.add(work_order)
    await db.commit()
    await db.refresh(work_order)

    # Best-effort: capture lineage links + bind common thread + stamp reasoning (do not block work order creation).
    try:
        await get_data_lineage_service().capture_work_order_created(
            db,
            work_order_id=work_order.id,
            product_id=work_order.product_id,
            created_by_id=getattr(current_user, "id", None),
            reasoning_id=x_reasoning_id,
        )

        # Optional: bind to Quote (and implicitly RFQ if quote has rfq_id)
        if data.quote_id is not None:
            rfq_id: str | None = None
            q = await db.get(Quote, data.quote_id)
            if q is not None and q.rfq_id is not None:
                rfq_id = str(q.rfq_id)

            await get_common_thread_service().bind(
                db,
                rfq_id=rfq_id,
                quote_id=str(data.quote_id),
                work_order_id=str(work_order.id),
                created_by_id=getattr(current_user, "id", None),
                reasoning_id=x_reasoning_id,
                source="work_order_create",
            )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="work_order",
                entity_id=str(work_order.id),
                reasoning_id=x_reasoning_id,
                created_by_id=getattr(current_user, "id", None),
                source="work_order_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to capture work order lineage/common-thread")
    
    # Initialize operations list for response
    work_order.operations = []
    
    return build_created_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.get("/stats", response_model=APIResponse[WorkOrderStatsResponse])
async def get_work_order_stats(
    db: DBSession,
    current_user: CurrentUser,
    work_center_id: Optional[int] = Query(None, description="Filter by work center"),
) -> APIResponse[WorkOrderStatsResponse]:
    """
    Get work order statistics.
    """
    # Base filters
    base_filter: ColumnElement[bool] = WorkOrder.deleted_at.is_(None)
    if work_center_id:
        base_filter = and_(base_filter, WorkOrder.work_center_id == work_center_id)
    
    # Total count
    total_result = await db.execute(
        select(func.count(WorkOrder.id)).where(base_filter)
    )
    total_work_orders = total_result.scalar() or 0
    
    # Status counts
    status_counts = {}
    for status in WorkOrderStatus:
        result = await db.execute(
            select(func.count(WorkOrder.id)).where(
                base_filter,
                WorkOrder.status == status,
            )
        )
        status_counts[status.value] = result.scalar() or 0
    
    # Quantity aggregates
    qty_result = await db.execute(
        select(
            func.coalesce(func.sum(WorkOrder.quantity_ordered), 0),
            func.coalesce(func.sum(WorkOrder.quantity_completed), 0),
        ).where(base_filter)
    )
    qty_row = qty_result.one()
    total_ordered = qty_row[0] or Decimal("0")
    total_completed = qty_row[1] or Decimal("0")
    
    # Average completion
    avg_completion = Decimal("0")
    if total_ordered > 0:
        avg_completion = (total_completed / total_ordered) * 100
    
    # Late count - need to fetch and count in Python due to dynamic property
    late_query = select(WorkOrder).where(
        base_filter,
        WorkOrder.status.in_([
            WorkOrderStatus.RELEASED,
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.ON_HOLD,
        ]),
        WorkOrder.scheduled_end.isnot(None),
    )
    late_result = await db.execute(late_query)
    late_work_orders = late_result.scalars().all()
    late_count = sum(1 for wo in late_work_orders if wo.is_late)
    
    stats = WorkOrderStatsResponse(
        total_work_orders=total_work_orders,
        draft_count=status_counts.get("draft", 0),
        released_count=status_counts.get("released", 0),
        in_progress_count=status_counts.get("in_progress", 0),
        on_hold_count=status_counts.get("on_hold", 0),
        completed_count=status_counts.get("completed", 0),
        cancelled_count=status_counts.get("cancelled", 0),
        late_count=late_count,
        total_quantity_ordered=total_ordered,
        total_quantity_completed=total_completed,
        average_completion_percentage=round(avg_completion, 2),
    )
    
    return build_response(data=stats)


@router.get("/{work_order_id}", response_model=APIResponse[WorkOrderResponse])
async def get_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
) -> APIResponse[WorkOrderResponse]:
    """
    Get a work order by ID.
    """
    query = select(WorkOrder).where(WorkOrder.id == work_order_id).options(
        selectinload(WorkOrder.operations)
    )
    
    if not include_deleted:
        query = query.where(WorkOrder.deleted_at.is_(None))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    return build_response(data=work_order_to_response(work_order))


@router.patch("/{work_order_id}", response_model=APIResponse[WorkOrderResponse])
async def update_work_order(
    work_order_id: int,
    data: WorkOrderUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Update a work order.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    # Check for duplicate work order number
    if data.work_order_number and data.work_order_number != work_order.work_order_number:
        existing = await db.execute(
            select(WorkOrder).where(
                WorkOrder.work_order_number == data.work_order_number,
                WorkOrder.id != work_order_id,
                WorkOrder.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Work order with number '{data.work_order_number}' already exists")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "priority" and value:
            setattr(work_order, field, WorkOrderPriority(value))
        elif field == "status" and value:
            setattr(work_order, field, WorkOrderStatus(value))
        else:
            setattr(work_order, field, value)
    
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.delete("/{work_order_id}", response_model=APIResponse)
async def delete_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(False, description="Permanently delete the record"),
) -> APIResponse:
    """
    Delete a work order (soft delete by default).
    """
    query = select(WorkOrder).where(WorkOrder.id == work_order_id)
    
    if not hard_delete:
        query = query.where(WorkOrder.deleted_at.is_(None))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if hard_delete:
        await db.delete(work_order)
    else:
        work_order.deleted_at = datetime.now(timezone.utc)
        work_order.updated_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Work order")


@router.post("/{work_order_id}/restore", response_model=APIResponse[WorkOrderResponse])
async def restore_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Restore a soft-deleted work order.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.isnot(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Deleted work order with ID {work_order_id} not found")
    
    work_order.deleted_at = None
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


# =============================================================================
# Work Order Status Transition Endpoints
# =============================================================================


@router.post("/{work_order_id}/release", response_model=APIResponse[WorkOrderResponse])
async def release_work_order(
    work_order_id: int,
    data: WorkOrderRelease,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Release a work order from draft status.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if work_order.status != WorkOrderStatus.DRAFT:
        raise BadRequestError(f"Cannot release work order in status '{work_order.status.value}'. Must be in 'draft' status.")
    
    work_order.status = WorkOrderStatus.RELEASED
    if data.scheduled_start:
        work_order.scheduled_start = data.scheduled_start
    if data.scheduled_end:
        work_order.scheduled_end = data.scheduled_end
    
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)

    response_data = work_order_to_response(work_order)
    try:
        svc = JidokaErrorProofingService()
        suggestions = await svc.suggest_for_work_order_release(db, work_order_id=work_order.id)
        response_data = response_data.model_copy(
            update={
                "jidoka_suggestions": [
                    JidokaSuggestionResponse(
                        title=s.title,
                        rationale=s.rationale,
                        actions=s.actions,
                        related_non_conformance_ids=s.related_non_conformance_ids,
                        confidence=s.confidence,
                    )
                    for s in suggestions
                ]
            }
        )
    except Exception:
        # Jidoka suggestions should never block release.
        logger.exception("Failed to generate Jidoka suggestions for work order %s", work_order_id)

    return build_updated_response(
        data=response_data,
        resource_name="Work order",
    )


@router.post("/{work_order_id}/start", response_model=APIResponse[WorkOrderResponse])
async def start_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Start a work order (move to in-progress).
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if not work_order.can_start():
        raise BadRequestError(f"Cannot start work order in status '{work_order.status.value}'. Must be in 'released' status.")
    
    work_order.status = WorkOrderStatus.IN_PROGRESS
    work_order.actual_start = datetime.now(timezone.utc)
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.post("/{work_order_id}/hold", response_model=APIResponse[WorkOrderResponse])
async def hold_work_order(
    work_order_id: int,
    data: WorkOrderHold,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Put a work order on hold.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if work_order.status in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED, WorkOrderStatus.CLOSED]:
        raise BadRequestError(f"Cannot put work order on hold in status '{work_order.status.value}'")
    
    work_order.status = WorkOrderStatus.ON_HOLD
    work_order.hold_reason = HoldReason(data.reason)
    work_order.hold_notes = data.notes
    work_order.held_at = datetime.now(timezone.utc)
    work_order.held_by_id = current_user.id
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.post("/{work_order_id}/resume", response_model=APIResponse[WorkOrderResponse])
async def resume_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Resume a work order that was on hold.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if work_order.status != WorkOrderStatus.ON_HOLD:
        raise BadRequestError(f"Cannot resume work order in status '{work_order.status.value}'. Must be on hold.")
    
    # Resume to in-progress if it was previously started, otherwise to released
    if work_order.actual_start:
        work_order.status = WorkOrderStatus.IN_PROGRESS
    else:
        work_order.status = WorkOrderStatus.RELEASED
    
    work_order.hold_reason = None
    work_order.hold_notes = None
    work_order.held_at = None
    work_order.held_by_id = None
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.post("/{work_order_id}/complete", response_model=APIResponse[WorkOrderResponse])
async def complete_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Complete a work order.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if not work_order.can_complete():
        raise BadRequestError("Cannot complete work order. Ensure it is in progress and all operations are completed.")
    
    work_order.status = WorkOrderStatus.COMPLETED
    work_order.actual_end = datetime.now(timezone.utc)
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)

    # H1 fix: create GL entries for WO completion — Dr FG Inventory / Cr WIP
    try:
        from sensei.models.product import Product
        prod_result = await db.execute(
            select(Product).where(Product.id == work_order.product_id)
        )
        product = prod_result.scalar_one_or_none()
        unit_cost = (
            product.standard_cost or product.unit_cost or Decimal("0")
        ) if product else Decimal("0")
        total_cost = unit_cost * work_order.quantity_completed
        if total_cost > 0:
            await post_wo_completion_to_gl(
                db,
                work_order_id=work_order.id,
                total_cost=total_cost,
                currency="USD",
                user_id=current_user.id,
            )
    except Exception:
        logger.warning("GL posting for WO %s completion skipped", work_order_id, exc_info=True)

    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.post("/{work_order_id}/cancel", response_model=APIResponse[WorkOrderResponse])
async def cancel_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Cancel a work order.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if work_order.status in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED]:
        raise BadRequestError(f"Cannot cancel work order in status '{work_order.status.value}'")
    
    work_order.status = WorkOrderStatus.CANCELLED
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


@router.post("/{work_order_id}/close", response_model=APIResponse[WorkOrderResponse])
async def close_work_order(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderResponse]:
    """
    Close a completed or cancelled work order.
    """
    query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    ).options(selectinload(WorkOrder.operations))
    
    result = await db.execute(query)
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    if work_order.status not in [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]:
        raise BadRequestError(f"Cannot close work order in status '{work_order.status.value}'. Must be completed or cancelled.")
    
    work_order.status = WorkOrderStatus.CLOSED
    work_order.updated_by_id = current_user.id
    work_order.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(work_order)
    
    return build_updated_response(
        data=work_order_to_response(work_order),
        resource_name="Work order",
    )


# =============================================================================
# Work Order Operations Endpoints
# =============================================================================


@router.get("/{work_order_id}/operations", response_model=PaginatedResponse[WorkOrderOperationResponse])
async def list_operations(
    work_order_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> PaginatedResponse[WorkOrderOperationResponse]:
    """
    List operations for a work order.
    """
    # Verify work order exists
    wo_query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    )
    wo_result = await db.execute(wo_query)
    if not wo_result.scalar_one_or_none():
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    # Build query
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.work_order_id == work_order_id
    )
    count_query = select(func.count(WorkOrderOperation.id)).where(
        WorkOrderOperation.work_order_id == work_order_id
    )
    
    # Status filter
    if status:
        try:
            status_enum = OperationStatus(status)
            query = query.where(WorkOrderOperation.status == status_enum)
            count_query = count_query.where(WorkOrderOperation.status == status_enum)
        except ValueError:
            raise BadRequestError(f"Invalid status: {status}")
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Sorting and pagination
    query = query.order_by(WorkOrderOperation.sequence.asc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    ops_result = await db.execute(query)
    operations: list[WorkOrderOperation] = list(ops_result.scalars().all())
    
    # Convert to response
    items = [operation_to_response(op) for op in operations]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/{work_order_id}/operations", response_model=APIResponse[WorkOrderOperationResponse], status_code=201)
async def create_operation(
    work_order_id: int,
    data: OperationCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Add an operation to a work order.
    """
    # Verify work order exists
    wo_query = select(WorkOrder).where(
        WorkOrder.id == work_order_id,
        WorkOrder.deleted_at.is_(None),
    )
    wo_result = await db.execute(wo_query)
    work_order = wo_result.scalar_one_or_none()
    if not work_order:
        raise NotFoundError(f"Work order with ID {work_order_id} not found")
    
    # Check for duplicate sequence
    existing = await db.execute(
        select(WorkOrderOperation).where(
            WorkOrderOperation.work_order_id == work_order_id,
            WorkOrderOperation.sequence == data.sequence,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Operation with sequence {data.sequence} already exists for this work order")
    
    # Create operation
    operation = WorkOrderOperation(
        work_order_id=work_order_id,
        routing_id=data.routing_id,
        sequence=data.sequence,
        operation_name=data.operation_name,
        station_id=data.station_id,
        standard_time_seconds=data.standard_time_seconds,
        setup_time_seconds=data.setup_time_seconds,
        notes=data.notes,
        status=OperationStatus.PENDING,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    
    db.add(operation)
    await db.commit()
    await db.refresh(operation)
    
    return build_created_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )


@router.get("/{work_order_id}/operations/{operation_id}", response_model=APIResponse[WorkOrderOperationResponse])
async def get_operation(
    work_order_id: int,
    operation_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Get a specific operation from a work order.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    return build_response(data=operation_to_response(operation))


@router.patch("/{work_order_id}/operations/{operation_id}", response_model=APIResponse[WorkOrderOperationResponse])
async def update_operation(
    work_order_id: int,
    operation_id: int,
    data: OperationUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Update a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(operation, field, OperationStatus(value))
        else:
            setattr(operation, field, value)
    
    operation.updated_by_id = current_user.id
    operation.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(operation)
    
    return build_updated_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )


@router.delete("/{work_order_id}/operations/{operation_id}", response_model=APIResponse)
async def delete_operation(
    work_order_id: int,
    operation_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Delete a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    await db.delete(operation)
    await db.commit()
    
    return build_deleted_response(resource_name="Operation")


@router.post("/{work_order_id}/operations/{operation_id}/start", response_model=APIResponse[WorkOrderOperationResponse])
async def start_operation(
    work_order_id: int,
    operation_id: int,
    data: OperationStart,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Start a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    if not operation.can_start():
        raise BadRequestError(f"Cannot start operation in status '{operation.status.value}'. Must be pending.")
    
    operation.status = OperationStatus.IN_PROGRESS
    operation.started_at = datetime.now(timezone.utc)
    if data.operator_id:
        from uuid import UUID as PyUUID
        operation.operator_id = PyUUID(data.operator_id)
    operation.updated_by_id = current_user.id
    operation.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(operation)
    
    return build_updated_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )


@router.post("/{work_order_id}/operations/{operation_id}/complete", response_model=APIResponse[WorkOrderOperationResponse])
async def complete_operation(
    work_order_id: int,
    operation_id: int,
    data: OperationComplete,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Complete a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    if not operation.can_complete():
        raise BadRequestError(f"Cannot complete operation in status '{operation.status.value}'. Must be in progress.")
    
    operation.status = OperationStatus.COMPLETED
    operation.completed_at = datetime.now(timezone.utc)
    operation.quantity_completed = data.quantity_completed
    operation.quantity_scrapped = data.quantity_scrapped
    if data.actual_time_seconds is not None:
        operation.actual_time_seconds = data.actual_time_seconds
    else:
        # Calculate from started_at if available
        if operation.started_at:
            elapsed = (datetime.now(timezone.utc) - operation.started_at).total_seconds()
            operation.actual_time_seconds = int(elapsed)
    if data.actual_setup_seconds is not None:
        operation.actual_setup_seconds = data.actual_setup_seconds
    if data.notes:
        operation.notes = data.notes
    operation.updated_by_id = current_user.id
    operation.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(operation)
    
    return build_updated_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )


@router.post("/{work_order_id}/operations/{operation_id}/block", response_model=APIResponse[WorkOrderOperationResponse])
async def block_operation(
    work_order_id: int,
    operation_id: int,
    db: DBSession,
    current_user: CurrentUser,
    reason: str = Query(..., description="Reason for blocking"),
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Block a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    if operation.status in [OperationStatus.COMPLETED, OperationStatus.SKIPPED]:
        raise BadRequestError(f"Cannot block operation in status '{operation.status.value}'")
    
    operation.status = OperationStatus.BLOCKED
    operation.blocked_reason = reason
    operation.updated_by_id = current_user.id
    operation.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(operation)
    
    return build_updated_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )


@router.post("/{work_order_id}/operations/{operation_id}/unblock", response_model=APIResponse[WorkOrderOperationResponse])
async def unblock_operation(
    work_order_id: int,
    operation_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Unblock a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    if operation.status != OperationStatus.BLOCKED:
        raise BadRequestError(f"Cannot unblock operation in status '{operation.status.value}'. Must be blocked.")
    
    # Return to pending or in-progress based on whether it was started
    if operation.started_at:
        operation.status = OperationStatus.IN_PROGRESS
    else:
        operation.status = OperationStatus.PENDING
    
    operation.blocked_reason = None
    operation.updated_by_id = current_user.id
    operation.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(operation)
    
    return build_updated_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )


@router.post("/{work_order_id}/operations/{operation_id}/skip", response_model=APIResponse[WorkOrderOperationResponse])
async def skip_operation(
    work_order_id: int,
    operation_id: int,
    db: DBSession,
    current_user: CurrentUser,
    reason: str = Query(..., description="Reason for skipping"),
) -> APIResponse[WorkOrderOperationResponse]:
    """
    Skip a work order operation.
    """
    query = select(WorkOrderOperation).where(
        WorkOrderOperation.id == operation_id,
        WorkOrderOperation.work_order_id == work_order_id,
    )
    
    result = await db.execute(query)
    operation = result.scalar_one_or_none()
    
    if not operation:
        raise NotFoundError(f"Operation with ID {operation_id} not found in work order {work_order_id}")
    
    if operation.status in [OperationStatus.COMPLETED, OperationStatus.SKIPPED]:
        raise BadRequestError(f"Cannot skip operation in status '{operation.status.value}'")
    
    operation.status = OperationStatus.SKIPPED
    operation.notes = f"Skipped: {reason}" if reason else "Skipped"
    operation.updated_by_id = current_user.id
    operation.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(operation)
    
    return build_updated_response(
        data=operation_to_response(operation),
        resource_name="Operation",
    )

"""Obeya (Big Room) Visual Management API endpoints.

Provides comprehensive API for managing Obeya visual management boards:
- Obeya item CRUD operations
- Item workflow (start, block, unblock, complete, cancel)
- Item escalation
- Comments and discussions
- Query endpoints (by board, overdue, assigned)
"""

from __future__ import annotations

import inspect
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select

from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.utils import (
    APIResponse,
    PaginatedResponse,
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_response,
    build_updated_response,
)
from sensei.models.obeya import (
    ObeyaItem,
    ObeyaComment,
    ObeyaBoard,
    ObeyaCategory,
    ObeyaStatus,
    ObeyaPriority,
)
from sensei.models.learning import UserLearningProgress, ProgressStatus
from sensei.models.quote import Quote


router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ObeyaItemCreate(BaseModel):
    """Schema for creating an Obeya item."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    board: ObeyaBoard = Field(default=ObeyaBoard.DAILY)
    column: Optional[str] = None
    position: int = Field(default=0)
    category: ObeyaCategory = Field(default=ObeyaCategory.ACTION)
    priority: ObeyaPriority = Field(default=ObeyaPriority.MEDIUM)
    color: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    kpi_target: Optional[str] = None
    kpi_unit: Optional[str] = None
    tags: Optional[list] = None
    meeting_date: Optional[datetime] = None
    meeting_type: Optional[str] = None
    notes: Optional[str] = None


class ObeyaItemUpdate(BaseModel):
    """Schema for updating an Obeya item."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    board: Optional[ObeyaBoard] = None
    column: Optional[str] = None
    position: Optional[int] = None
    category: Optional[ObeyaCategory] = None
    priority: Optional[ObeyaPriority] = None
    color: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    resolution: Optional[str] = None
    decision_outcome: Optional[str] = None
    decision_rationale: Optional[str] = None
    kpi_target: Optional[str] = None
    kpi_actual: Optional[str] = None
    kpi_unit: Optional[str] = None
    kpi_trend: Optional[str] = None
    tags: Optional[list] = None
    meeting_date: Optional[datetime] = None
    meeting_type: Optional[str] = None
    notes: Optional[str] = None


class ObeyaItemResolve(BaseModel):
    """Schema for resolving an Obeya item."""

    resolution: str


class SQDCPSafetyMetric(BaseModel):
    incidents: int = 0
    days_since_last_incident: int = 0
    near_misses: int = 0
    training_completion: float = 0.0
    status: str = "green"


class SQDCPQualityMetric(BaseModel):
    first_pass_yield: float = 0.0
    defect_rate: float = 0.0
    customer_complaints: int = 0
    ncr_open: int = 0
    status: str = "green"


class SQDCPDeliveryMetric(BaseModel):
    on_time_delivery: float = 0.0
    lead_time_days: float = 0.0
    schedule_adherence: float = 0.0
    backlog_items: int = 0
    status: str = "green"


class SQDCPCostMetric(BaseModel):
    variance_percent: float = 0.0
    cost_savings: float = 0.0
    waste_reduction: float = 0.0
    budget_utilization: float = 0.0
    status: str = "green"


class SQDCPPeopleMetric(BaseModel):
    morale_score: float = 0.0
    training_hours: float = 0.0
    attendance_rate: float = 0.0
    active_improvements: int = 0
    status: str = "green"


class SQDCPMetricsResponse(BaseModel):
    safety: SQDCPSafetyMetric
    quality: SQDCPQualityMetric
    delivery: SQDCPDeliveryMetric
    cost: SQDCPCostMetric
    people: SQDCPPeopleMetric


class ObeyaItemResponse(BaseModel):
    """Schema for Obeya item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str] = None
    board: str
    column: Optional[str] = None
    position: int
    category: str
    status: str
    priority: str
    color: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    resolution: Optional[str] = None
    decision_outcome: Optional[str] = None
    decision_rationale: Optional[str] = None
    kpi_target: Optional[str] = None
    kpi_actual: Optional[str] = None
    kpi_unit: Optional[str] = None
    kpi_trend: Optional[str] = None
    is_escalated: bool
    escalated_to_id: Optional[UUID] = None
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    days_open: Optional[int] = None
    days_overdue: Optional[int] = None
    attachments: Optional[list] = None
    links: Optional[list] = None
    tags: Optional[list] = None
    meeting_date: Optional[datetime] = None
    meeting_type: Optional[str] = None
    notes: Optional[str] = None
    is_overdue: bool
    is_open: bool
    created_at: datetime
    updated_at: datetime


class EscalationData(BaseModel):
    """Schema for item escalation."""

    escalated_to_id: UUID
    escalation_reason: Optional[str] = None


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    content: str = Field(..., min_length=1)
    parent_id: Optional[UUID] = None
    mentions: Optional[list] = None
    attachments: Optional[list] = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    content: Optional[str] = Field(default=None, min_length=1)
    is_pinned: Optional[bool] = None


class CommentResponse(BaseModel):
    """Schema for comment response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    author_id: Optional[UUID] = None
    content: str
    parent_id: Optional[UUID] = None
    is_status_change: bool
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    is_pinned: bool
    is_edited: bool
    edited_at: Optional[datetime] = None
    mentions: Optional[list] = None
    attachments: Optional[list] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Obeya Item CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=APIResponse[ObeyaItemResponse],
    status_code=201,
    summary="Create Obeya item",
    description="Create a new item on the Obeya board.",
)
async def create_obeya_item(
    data: ObeyaItemCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    item = ObeyaItem(
        title=data.title,
        description=data.description,
        board=(
            data.board.value
            if isinstance(data.board, ObeyaBoard)
            else data.board
        ),
        column=data.column,
        position=data.position,
        category=(
            data.category.value
            if isinstance(data.category, ObeyaCategory)
            else data.category
        ),
        status=ObeyaStatus.NEW.value,
        priority=(
            data.priority.value
            if isinstance(data.priority, ObeyaPriority)
            else data.priority
        ),
        color=data.color,
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
        assigned_to_id=data.assigned_to_id,
        due_date=data.due_date,
        target_date=data.target_date,
        kpi_target=data.kpi_target,
        kpi_unit=data.kpi_unit,
        tags=data.tags or [],
        meeting_date=data.meeting_date,
        meeting_type=data.meeting_type,
        notes=data.notes,
        created_by_id=current_user.id,
        owner_id=data.assigned_to_id or current_user.id,
    )

    db.add(item)
    await db.flush()
    await db.refresh(item)

    return build_created_response(
        data=ObeyaItemResponse.model_validate(item),
        resource_name="Obeya item",
    )


@router.get(
    "/{item_id}",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Get Obeya item",
    description="Get an Obeya item by ID.",
)
async def get_obeya_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Obeya item retrieved successfully",
    )


@router.get(
    "",
    response_model=PaginatedResponse[ObeyaItemResponse],
    summary="List Obeya items",
    description="List Obeya items with filtering and pagination.",
)
async def list_obeya_items(
    db: DBSession,
    current_user: CurrentUser,
    board: Optional[ObeyaBoard] = Query(default=None),
    category: Optional[ObeyaCategory] = Query(default=None),
    status: Optional[ObeyaStatus] = Query(default=None),
    priority: Optional[ObeyaPriority] = Query(default=None),
    assigned_to_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ObeyaItemResponse]:
    base_conditions: list[Any] = [ObeyaItem.deleted_at.is_(None)]

    if board and isinstance(board, ObeyaBoard):
        base_conditions.append(ObeyaItem.board == board.value)
    if category and isinstance(category, ObeyaCategory):
        base_conditions.append(ObeyaItem.category == category.value)
    if status and isinstance(status, ObeyaStatus):
        base_conditions.append(ObeyaItem.status == status.value)
    if priority and isinstance(priority, ObeyaPriority):
        base_conditions.append(ObeyaItem.priority == priority.value)
    if assigned_to_id:
        base_conditions.append(ObeyaItem.assigned_to_id == assigned_to_id)
    if search:
        search_filter = or_(
            ObeyaItem.title.ilike(f"%{search}%"),
            ObeyaItem.description.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    # Count total
    count_stmt = select(func.count(ObeyaItem.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Fetch data with pagination
    offset = (page - 1) * page_size
    data_stmt = (
        select(ObeyaItem)
        .where(and_(*base_conditions))
        .order_by(
            ObeyaItem.priority.desc(),
            ObeyaItem.position.asc(),
            ObeyaItem.created_at.desc(),
        )
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    items = data_result.scalars().all()

    item_list = [ObeyaItemResponse.model_validate(i) for i in items]

    return build_paginated_response(
        data=item_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{item_id}",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Update Obeya item",
    description="Update an Obeya item's details.",
)
async def update_obeya_item(
    item_id: UUID,
    data: ObeyaItemUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle enum values
    if "board" in update_data and update_data["board"]:
        if isinstance(update_data["board"], ObeyaBoard):
            update_data["board"] = update_data["board"].value
    if "category" in update_data and update_data["category"]:
        if isinstance(update_data["category"], ObeyaCategory):
            update_data["category"] = update_data["category"].value
    if "priority" in update_data and update_data["priority"]:
        if isinstance(update_data["priority"], ObeyaPriority):
            update_data["priority"] = update_data["priority"].value

    for key, value in update_data.items():
        setattr(item, key, value)

    item.updated_by_id = current_user.id
    item.update_days_tracking()

    await db.flush()
    await db.refresh(item)

    return build_updated_response(
        data=ObeyaItemResponse.model_validate(item),
        resource_name="Obeya item",
    )


@router.delete(
    "/{item_id}",
    response_model=APIResponse,
    summary="Delete Obeya item",
    description="Soft delete an Obeya item.",
)
async def delete_obeya_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    item.deleted_at = datetime.now(timezone.utc)
    item.deleted_by_id = current_user.id
    await db.flush()

    return build_deleted_response(resource_name="Obeya item")


# =============================================================================
# Obeya Item Workflow Endpoints
# =============================================================================


@router.post(
    "/{item_id}/start",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Start item",
    description="Move item to in progress status.",
)
async def start_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status not in [ObeyaStatus.NEW.value, ObeyaStatus.WAITING.value]:
        raise ConflictError("Item must be in 'new' or 'waiting' status to start")

    item.status = ObeyaStatus.IN_PROGRESS.value
    item.updated_by_id = current_user.id
    item.update_days_tracking()

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item started",
    )


@router.post(
    "/{item_id}/block",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Block item",
    description="Mark item as blocked.",
)
async def block_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    blocked_reason: Optional[str] = Query(default=None),
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status in [ObeyaStatus.COMPLETED.value, ObeyaStatus.CANCELLED.value]:
        raise ConflictError("Cannot block completed or cancelled item")

    item.status = ObeyaStatus.BLOCKED.value
    item.blocked_reason = blocked_reason
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item blocked",
    )


@router.post(
    "/{item_id}/unblock",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Unblock item",
    description="Remove blocked status from item.",
)
async def unblock_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status != ObeyaStatus.BLOCKED.value:
        raise ConflictError("Item is not blocked")

    item.status = ObeyaStatus.IN_PROGRESS.value
    item.blocked_reason = None
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item unblocked",
    )


@router.post(
    "/{item_id}/wait",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Set waiting",
    description="Set item to waiting status.",
)
async def set_waiting(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status in [ObeyaStatus.COMPLETED.value, ObeyaStatus.CANCELLED.value]:
        raise ConflictError("Cannot set waiting on completed or cancelled item")

    item.status = ObeyaStatus.WAITING.value
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item set to waiting",
    )


@router.post(
    "/{item_id}/complete",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Complete item",
    description="Mark item as completed.",
)
async def complete_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    resolution: Optional[str] = Query(default=None),
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status == ObeyaStatus.COMPLETED.value:
        raise ConflictError("Item is already completed")

    item.status = ObeyaStatus.COMPLETED.value
    item.completed_at = datetime.now(timezone.utc)
    if resolution:
        item.resolution = resolution
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item completed",
    )


@router.post(
    "/{item_id}/cancel",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Cancel item",
    description="Cancel an Obeya item.",
)
async def cancel_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status == ObeyaStatus.CANCELLED.value:
        raise ConflictError("Item is already cancelled")

    item.status = ObeyaStatus.CANCELLED.value
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item cancelled",
    )


@router.post(
    "/{item_id}/escalate",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Escalate item",
    description="Escalate an item to a manager or other user.",
)
async def escalate_item(
    item_id: UUID,
    data: EscalationData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if item.status in [ObeyaStatus.COMPLETED.value, ObeyaStatus.CANCELLED.value]:
        raise ConflictError("Cannot escalate completed or cancelled item")

    item.is_escalated = True
    item.escalated_to_id = data.escalated_to_id
    item.escalated_at = datetime.now(timezone.utc)
    item.escalation_reason = data.escalation_reason
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item escalated",
    )


@router.post(
    "/{item_id}/de-escalate",
    response_model=APIResponse[ObeyaItemResponse],
    summary="De-escalate item",
    description="Remove escalation from an item.",
)
async def deescalate_item(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    if not item.is_escalated:
        raise ConflictError("Item is not escalated")

    item.is_escalated = False
    item.escalated_to_id = None
    item.escalated_at = None
    item.escalation_reason = None
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item de-escalated",
    )


@router.post(
    "/{item_id}/resolve",
    response_model=APIResponse[ObeyaItemResponse],
    summary="Resolve item",
    description="Resolve an Obeya item with a resolution description.",
)
async def resolve_item(
    item_id: UUID,
    data: ObeyaItemResolve,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ObeyaItemResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    item.status = ObeyaStatus.COMPLETED.value
    item.resolution = data.resolution
    item.completed_at = datetime.now(timezone.utc)
    item.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(item)

    return build_response(
        data=ObeyaItemResponse.model_validate(item),
        message="Item resolved",
    )


@router.get(
    "/sqdcp-metrics",
    response_model=APIResponse[SQDCPMetricsResponse],
    summary="Get SQDCP metrics",
    description="Get summarized SQDCP metrics for the Obeya board.",
)
async def get_sqdcp_metrics(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SQDCPMetricsResponse]:
    def _parse_float(value: str | None) -> float | None:
        if value is None:
            return None
        match = re.search(r"-?\d+(\.\d+)?", value.replace(",", ""))
        return float(match.group(0)) if match else None

    def _status_high_is_good(value: float, green: float, yellow: float) -> str:
        if value >= green:
            return "green"
        if value >= yellow:
            return "yellow"
        return "red"

    def _status_low_is_good(value: float, green: float, yellow: float) -> str:
        if value <= green:
            return "green"
        if value <= yellow:
            return "yellow"
        return "red"

    # Safety metrics
    safety_incidents = await db.scalar(
        select(func.count(ObeyaItem.id)).where(
            and_(
                ObeyaItem.category == ObeyaCategory.SAFETY.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    ) or 0

    last_incident_at = await db.scalar(
        select(func.max(ObeyaItem.created_at)).where(
            and_(
                ObeyaItem.category == ObeyaCategory.SAFETY.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    )

    days_since_last_incident = 0
    if last_incident_at:
        days_since_last_incident = (datetime.now(timezone.utc) - last_incident_at).days

    near_misses = await db.scalar(
        select(func.count(ObeyaItem.id)).where(
            and_(
                ObeyaItem.category == ObeyaCategory.SAFETY.value,
                ObeyaItem.priority == ObeyaPriority.LOW.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    ) or 0

    progress_total = await db.scalar(select(func.count(UserLearningProgress.id))) or 0
    progress_completed = await db.scalar(
        select(func.count(UserLearningProgress.id)).where(
            UserLearningProgress.status == ProgressStatus.COMPLETED.value
        )
    ) or 0
    training_completion = (progress_completed / progress_total * 100) if progress_total else 0.0

    # Quality metrics
    quality_items = await db.execute(
        select(ObeyaItem.title, ObeyaItem.kpi_actual, ObeyaItem.kpi_unit, ObeyaItem.status).where(
            and_(
                ObeyaItem.category == ObeyaCategory.QUALITY.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    )
    quality_items = quality_items.all()
    yield_values = []
    defect_values = []
    for title, actual, unit, status in quality_items:
        parsed = _parse_float(actual)
        if parsed is None:
            continue
        title_lower = (title or "").lower()
        if "yield" in title_lower:
            yield_values.append(parsed)
        if "defect" in title_lower or "scrap" in title_lower:
            defect_values.append(parsed)

    first_pass_yield = sum(yield_values) / len(yield_values) if yield_values else 0.0
    defect_rate = sum(defect_values) / len(defect_values) if defect_values else 0.0
    ncr_open = sum(1 for _, _, _, status in quality_items if status != ObeyaStatus.COMPLETED.value)

    # Delivery metrics
    delivery_items = await db.execute(
        select(ObeyaItem.title, ObeyaItem.kpi_actual, ObeyaItem.kpi_unit, ObeyaItem.status).where(
            and_(
                ObeyaItem.category == ObeyaCategory.DELIVERY.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    )
    delivery_items = delivery_items.all()
    on_time_values = []
    schedule_values = []
    for title, actual, unit, status in delivery_items:
        parsed = _parse_float(actual)
        if parsed is None:
            continue
        title_lower = (title or "").lower()
        if "on time" in title_lower or "otd" in title_lower:
            on_time_values.append(parsed)
        if "schedule" in title_lower or "adherence" in title_lower:
            schedule_values.append(parsed)

    on_time_delivery = sum(on_time_values) / len(on_time_values) if on_time_values else 0.0
    schedule_adherence = sum(schedule_values) / len(schedule_values) if schedule_values else 0.0
    backlog_items = sum(1 for _, _, _, status in delivery_items if status != ObeyaStatus.COMPLETED.value)

    lead_time_days = await db.scalar(select(func.avg(Quote.lead_time_days))) or 0.0

    # Cost metrics
    cost_items = await db.execute(
        select(ObeyaItem.title, ObeyaItem.kpi_actual, ObeyaItem.kpi_unit).where(
            and_(
                ObeyaItem.category == ObeyaCategory.COST.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    )
    cost_items = cost_items.all()
    variance_values = []
    savings_values = []
    for title, actual, unit in cost_items:
        parsed = _parse_float(actual)
        if parsed is None:
            continue
        title_lower = (title or "").lower()
        if "variance" in title_lower:
            variance_values.append(parsed)
        if "savings" in title_lower or "saving" in title_lower:
            savings_values.append(parsed)

    variance_percent = sum(variance_values) / len(variance_values) if variance_values else 0.0
    cost_savings = sum(savings_values) if savings_values else 0.0

    # People metrics
    morale_items = await db.execute(
        select(ObeyaItem.kpi_actual).where(
            and_(
                ObeyaItem.category == ObeyaCategory.MORALE.value,
                ObeyaItem.deleted_at.is_(None),
            )
        )
    )
    morale_values = [
        value for (value,) in morale_items.all()
        if _parse_float(value) is not None
    ]
    morale_scores = [_parse_float(value) for value in morale_values if _parse_float(value) is not None]
    morale_score = sum(morale_scores) / len(morale_scores) if morale_scores else 0.0

    training_hours = (await db.scalar(select(func.sum(UserLearningProgress.time_spent_seconds))) or 0) / 3600
    active_improvements = await db.scalar(
        select(func.count(ObeyaItem.id)).where(
            and_(
                ObeyaItem.category == ObeyaCategory.ACTION.value,
                ObeyaItem.status.in_([
                    ObeyaStatus.NEW.value,
                    ObeyaStatus.IN_PROGRESS.value,
                    ObeyaStatus.BLOCKED.value,
                    ObeyaStatus.WAITING.value,
                ]),
                ObeyaItem.deleted_at.is_(None),
            )
        )
    ) or 0

    return build_response(
        data=SQDCPMetricsResponse(
            safety=SQDCPSafetyMetric(
                incidents=safety_incidents,
                days_since_last_incident=days_since_last_incident,
                near_misses=near_misses,
                training_completion=round(training_completion, 1),
                status=_status_low_is_good(safety_incidents, green=0, yellow=2),
            ),
            quality=SQDCPQualityMetric(
                first_pass_yield=round(first_pass_yield, 1),
                defect_rate=round(defect_rate, 2),
                customer_complaints=0,
                ncr_open=ncr_open,
                status=_status_high_is_good(first_pass_yield, green=95, yellow=90),
            ),
            delivery=SQDCPDeliveryMetric(
                on_time_delivery=round(on_time_delivery, 1),
                lead_time_days=round(float(lead_time_days), 1) if lead_time_days else 0.0,
                schedule_adherence=round(schedule_adherence, 1),
                backlog_items=backlog_items,
                status=_status_high_is_good(on_time_delivery, green=95, yellow=90),
            ),
            cost=SQDCPCostMetric(
                variance_percent=round(variance_percent, 2),
                cost_savings=round(cost_savings, 2),
                waste_reduction=0.0,
                budget_utilization=0.0,
                status=_status_low_is_good(abs(variance_percent), green=2.0, yellow=5.0),
            ),
            people=SQDCPPeopleMetric(
                morale_score=round(morale_score, 1),
                training_hours=round(training_hours, 1),
                attendance_rate=0.0,
                active_improvements=active_improvements,
                status=_status_high_is_good(morale_score, green=4.0, yellow=3.0),
            ),
        )
    )


# =============================================================================
# Comment Endpoints
# =============================================================================


@router.post(
    "/{item_id}/comments",
    response_model=APIResponse[CommentResponse],
    status_code=201,
    summary="Add comment",
    description="Add a comment to an Obeya item.",
)
async def add_comment(
    item_id: UUID,
    data: CommentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CommentResponse]:
    stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    comment = ObeyaComment(
        item_id=item_id,
        author_id=current_user.id,
        content=data.content,
        parent_id=data.parent_id,
        mentions=data.mentions,
        attachments=data.attachments,
    )

    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    return build_created_response(
        data=CommentResponse.model_validate(comment),
        resource_name="Comment",
    )


@router.get(
    "/{item_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
    summary="List comments",
    description="List comments on an Obeya item.",
)
async def list_comments(
    item_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CommentResponse]:
    # Check item exists
    item_stmt = select(ObeyaItem).where(
        and_(ObeyaItem.id == item_id, ObeyaItem.deleted_at.is_(None))
    )
    item_result = await db.execute(item_stmt)
    item = item_result.scalar_one_or_none()
    if not item:
        raise NotFoundError(f"Obeya item {item_id} not found")

    base_conditions = [ObeyaComment.item_id == item_id]

    count_stmt = select(func.count(ObeyaComment.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(ObeyaComment)
        .where(and_(*base_conditions))
        .order_by(ObeyaComment.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    comments = data_result.scalars().all()

    items = [CommentResponse.model_validate(c) for c in comments]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{item_id}/comments/{comment_id}",
    response_model=APIResponse[CommentResponse],
    summary="Update comment",
    description="Update a comment.",
)
async def update_comment(
    item_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CommentResponse]:
    stmt = select(ObeyaComment).where(
        and_(
            ObeyaComment.id == comment_id,
            ObeyaComment.item_id == item_id,
        )
    )
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()

    if not comment:
        raise NotFoundError(f"Comment {comment_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    if "content" in update_data:
        comment.is_edited = True
        comment.edited_at = datetime.now(timezone.utc)

    for key, value in update_data.items():
        setattr(comment, key, value)

    await db.flush()
    await db.refresh(comment)

    return build_updated_response(
        data=CommentResponse.model_validate(comment),
        resource_name="Comment",
    )


@router.delete(
    "/{item_id}/comments/{comment_id}",
    response_model=APIResponse,
    summary="Delete comment",
    description="Delete a comment.",
)
async def delete_comment(
    item_id: UUID,
    comment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(ObeyaComment).where(
        and_(
            ObeyaComment.id == comment_id,
            ObeyaComment.item_id == item_id,
        )
    )
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()

    if not comment:
        raise NotFoundError(f"Comment {comment_id} not found")

    await db.delete(comment)
    await db.flush()

    return build_deleted_response(resource_name="Comment")


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get(
    "/board/{board}",
    response_model=PaginatedResponse[ObeyaItemResponse],
    summary="Get board items",
    description="Get all items for a specific board.",
)
async def get_board_items(
    board: ObeyaBoard,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse[ObeyaItemResponse]:
    board_value = board.value if isinstance(board, ObeyaBoard) else board
    base_conditions = [
        ObeyaItem.deleted_at.is_(None),
        ObeyaItem.board == board_value,
    ]

    count_stmt = select(func.count(ObeyaItem.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(ObeyaItem)
        .where(and_(*base_conditions))
        .order_by(ObeyaItem.column.asc(), ObeyaItem.position.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    items = data_result.scalars().all()

    item_list = [ObeyaItemResponse.model_validate(i) for i in items]

    return build_paginated_response(
        data=item_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/overdue",
    response_model=PaginatedResponse[ObeyaItemResponse],
    summary="Get overdue items",
    description="Get all overdue Obeya items.",
)
async def get_overdue_items(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ObeyaItemResponse]:
    now = datetime.now(timezone.utc)
    base_conditions = [
        ObeyaItem.deleted_at.is_(None),
        ObeyaItem.due_date < now,
        ObeyaItem.status.notin_([
            ObeyaStatus.COMPLETED.value,
            ObeyaStatus.CANCELLED.value,
        ]),
    ]

    count_stmt = select(func.count(ObeyaItem.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(ObeyaItem)
        .where(and_(*base_conditions))
        .order_by(ObeyaItem.due_date.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    items = data_result.scalars().all()

    item_list = [ObeyaItemResponse.model_validate(i) for i in items]

    return build_paginated_response(
        data=item_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/my-items",
    response_model=PaginatedResponse[ObeyaItemResponse],
    summary="Get my items",
    description="Get items assigned to the current user.",
)
async def get_my_items(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ObeyaItemResponse]:
    base_conditions = [
        ObeyaItem.deleted_at.is_(None),
        ObeyaItem.assigned_to_id == current_user.id,
        ObeyaItem.status.notin_([
            ObeyaStatus.COMPLETED.value,
            ObeyaStatus.CANCELLED.value,
        ]),
    ]

    count_stmt = select(func.count(ObeyaItem.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(ObeyaItem)
        .where(and_(*base_conditions))
        .order_by(ObeyaItem.priority.desc(), ObeyaItem.due_date.asc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    items = data_result.scalars().all()

    item_list = [ObeyaItemResponse.model_validate(i) for i in items]

    return build_paginated_response(
        data=item_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/escalated",
    response_model=PaginatedResponse[ObeyaItemResponse],
    summary="Get escalated items",
    description="Get all escalated items.",
)
async def get_escalated_items(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ObeyaItemResponse]:
    base_conditions = [
        ObeyaItem.deleted_at.is_(None),
        ObeyaItem.is_escalated.is_(True),
        ObeyaItem.status.notin_([
            ObeyaStatus.COMPLETED.value,
            ObeyaStatus.CANCELLED.value,
        ]),
    ]

    count_stmt = select(func.count(ObeyaItem.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(ObeyaItem)
        .where(and_(*base_conditions))
        .order_by(ObeyaItem.escalated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    items = data_result.scalars().all()

    item_list = [ObeyaItemResponse.model_validate(i) for i in items]

    return build_paginated_response(
        data=item_list,
        total=total,
        page=page,
        page_size=page_size,
    )

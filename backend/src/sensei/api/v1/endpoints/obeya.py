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
from datetime import datetime, timezone
from typing import Optional
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

    maybe_awaitable = db.add(item)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
    base_conditions = [ObeyaItem.is_deleted == False]

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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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

    maybe_awaitable = db.add(comment)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable
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
        and_(ObeyaItem.id == item_id, ObeyaItem.is_deleted == False)
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
        ObeyaItem.is_deleted == False,
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
        ObeyaItem.is_deleted == False,
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
        ObeyaItem.is_deleted == False,
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
        ObeyaItem.is_deleted == False,
        ObeyaItem.is_escalated == True,
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

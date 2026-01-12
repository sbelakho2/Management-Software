"""Kanban System Endpoints.

Provides CRUD and workflow operations for:
- Kanban Boards (configuration, columns, WIP limits)
- Kanban Cards (work items, movement, blocking)
- Card History (audit trail)
- Kanban Metrics (throughput, cycle time, WIP)

Implements digital Kanban boards with visual management
and pull system principles.
"""

from __future__ import annotations

from datetime import datetime, timedelta, date, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload

from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_response,
    build_updated_response,
)
from sensei.models.kanban import (
    KanbanBoard,
    BoardType,
    KanbanCard,
    CardType,
    CardStatus,
    CardPriority,
    KanbanCardHistory,
    KanbanMetrics,
)

router = APIRouter()


# =============================================================================
# Utility helpers
# =============================================================================


def _now_utc() -> datetime:
    """Get current UTC datetime (naive) for consistency with model timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Enum parsing helpers
# =============================================================================


def _parse_enum(enum_cls: Any, value: Any, field_name: str):
    if value is None or isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            valid = [e.value for e in enum_cls]
            raise ValueError(f"Invalid {field_name}. Must be one of: {valid}")
    return value


# =============================================================================
# Board Schemas
# =============================================================================


class ColumnConfig(BaseModel):
    """Column configuration for a Kanban board."""

    name: str = Field(..., max_length=100)
    order: int = Field(default=0, ge=0)
    wip_limit: Optional[int] = Field(default=None, ge=1)
    color: Optional[str] = Field(default="#e0e0e0", max_length=20)
    is_done_column: bool = Field(default=False)
    is_start_column: bool = Field(default=False)


class SwimlaneConfig(BaseModel):
    """Swimlane configuration for a Kanban board."""

    name: str = Field(..., max_length=100)
    order: int = Field(default=0, ge=0)
    wip_limit: Optional[int] = Field(default=None, ge=1)


class KanbanBoardCreate(BaseModel):
    """Schema for creating a Kanban board."""

    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None)
    board_type: str = Field(default="production")
    work_center_id: Optional[int] = Field(default=None)
    wip_limit_global: Optional[int] = Field(default=None, ge=1)
    columns_config: Optional[list[ColumnConfig]] = Field(default=None)
    swimlanes_config: Optional[list[SwimlaneConfig]] = Field(default=None)
    is_active: bool = Field(default=True)

    @field_validator("board_type")
    @classmethod
    def validate_board_type(cls, v: str) -> str:
        _parse_enum(BoardType, v, "board_type")
        return v


class KanbanBoardUpdate(BaseModel):
    """Schema for updating a Kanban board."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None)
    board_type: Optional[str] = Field(default=None)
    work_center_id: Optional[int] = Field(default=None)
    wip_limit_global: Optional[int] = Field(default=None, ge=1)
    columns_config: Optional[list[ColumnConfig]] = Field(default=None)
    swimlanes_config: Optional[list[SwimlaneConfig]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    @field_validator("board_type")
    @classmethod
    def validate_board_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(BoardType, v, "board_type")
        return v


class KanbanBoardResponse(BaseModel):
    """Schema for Kanban board response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    board_type: str
    work_center_id: Optional[int]
    wip_limit_global: Optional[int]
    columns_config: list[dict[str, Any]]
    swimlanes_config: Optional[list[dict[str, Any]]]
    is_active: bool
    total_active_cards: int
    is_at_global_limit: bool
    column_names: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, board: KanbanBoard) -> "KanbanBoardResponse":
        return cls(
            id=board.id,
            name=board.name,
            code=board.code,
            description=board.description,
            board_type=board.board_type.value,
            work_center_id=board.work_center_id,
            wip_limit_global=board.wip_limit_global,
            columns_config=board.columns_config_json,
            swimlanes_config=board.swimlanes_config_json,
            is_active=board.is_active,
            total_active_cards=board.total_active_cards,
            is_at_global_limit=board.is_at_global_limit,
            column_names=board.column_names,
            created_at=board.created_at,
            updated_at=board.updated_at,
        )


# =============================================================================
# Card Schemas
# =============================================================================


class KanbanCardCreate(BaseModel):
    """Schema for creating a Kanban card."""

    card_number: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    board_id: int
    column_name: str = Field(..., max_length=100)
    swimlane_name: Optional[str] = Field(default=None, max_length=100)
    position: int = Field(default=0, ge=0)
    card_type: str = Field(default="task")
    priority: str = Field(default="normal")
    work_order_id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    assigned_to_id: Optional[UUID] = Field(default=None)
    due_date: Optional[date] = Field(default=None)
    story_points: Optional[int] = Field(default=None, gt=0)
    estimated_hours: Optional[Decimal] = Field(default=None, gt=0)
    tags: Optional[list[str]] = Field(default=None)

    @field_validator("card_type")
    @classmethod
    def validate_card_type(cls, v: str) -> str:
        _parse_enum(CardType, v, "card_type")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        _parse_enum(CardPriority, v, "priority")
        return v


class KanbanCardUpdate(BaseModel):
    """Schema for updating a Kanban card."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    swimlane_name: Optional[str] = Field(default=None, max_length=100)
    position: Optional[int] = Field(default=None, ge=0)
    card_type: Optional[str] = Field(default=None)
    priority: Optional[str] = Field(default=None)
    work_order_id: Optional[int] = Field(default=None)
    product_id: Optional[int] = Field(default=None)
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    assigned_to_id: Optional[UUID] = Field(default=None)
    due_date: Optional[date] = Field(default=None)
    story_points: Optional[int] = Field(default=None, gt=0)
    estimated_hours: Optional[Decimal] = Field(default=None, gt=0)
    actual_hours: Optional[Decimal] = Field(default=None, gt=0)
    tags: Optional[list[str]] = Field(default=None)

    @field_validator("card_type")
    @classmethod
    def validate_card_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(CardType, v, "card_type")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(CardPriority, v, "priority")
        return v


class KanbanCardMoveRequest(BaseModel):
    """Schema for moving a card to a different column."""

    column_name: str = Field(..., max_length=100)
    position: Optional[int] = Field(default=None, ge=0)
    swimlane_name: Optional[str] = Field(default=None, max_length=100)


class KanbanCardBlockRequest(BaseModel):
    """Schema for blocking a card."""

    blocked_reason: str = Field(..., min_length=1)


class KanbanCardUnblockRequest(BaseModel):
    """Schema for unblocking a card."""

    notes: Optional[str] = Field(default=None)


class WIPOverrideRequest(BaseModel):
    """Schema for WIP limit override request."""

    reason: str = Field(..., min_length=1)


class KanbanCardResponse(BaseModel):
    """Schema for Kanban card response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    card_number: str
    title: str
    description: Optional[str]
    board_id: int
    column_name: str
    swimlane_name: Optional[str]
    position: int
    card_type: str
    priority: str
    status: str
    blocked_reason: Optional[str]
    work_order_id: Optional[int]
    product_id: Optional[int]
    quantity: Optional[Decimal]
    assigned_to_id: Optional[UUID]
    due_date: Optional[date]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cycle_started_at: Optional[datetime]
    cycle_completed_at: Optional[datetime]
    story_points: Optional[int]
    estimated_hours: Optional[Decimal]
    actual_hours: Optional[Decimal]
    tags: Optional[list[str]]
    wip_limit_override: bool
    wip_limit_override_reason: Optional[str]
    is_active: bool
    is_blocked: bool
    is_completed: bool
    is_overdue: bool
    lead_time_days: Optional[int]
    cycle_time_days: Optional[float]
    age_days: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, card: KanbanCard) -> "KanbanCardResponse":
        return cls(
            id=card.id,
            card_number=card.card_number,
            title=card.title,
            description=card.description,
            board_id=card.board_id,
            column_name=card.column_name,
            swimlane_name=card.swimlane_name,
            position=card.position,
            card_type=card.card_type.value,
            priority=card.priority.value,
            status=card.status.value,
            blocked_reason=card.blocked_reason,
            work_order_id=card.work_order_id,
            product_id=card.product_id,
            quantity=card.quantity,
            assigned_to_id=card.assigned_to_id,
            due_date=card.due_date,
            started_at=card.started_at,
            completed_at=card.completed_at,
            cycle_started_at=card.cycle_started_at,
            cycle_completed_at=card.cycle_completed_at,
            story_points=card.story_points,
            estimated_hours=card.estimated_hours,
            actual_hours=card.actual_hours,
            tags=card.tags,
            wip_limit_override=card.wip_limit_override,
            wip_limit_override_reason=card.wip_limit_override_reason,
            is_active=card.is_active,
            is_blocked=card.is_blocked,
            is_completed=card.is_completed,
            is_overdue=card.is_overdue,
            lead_time_days=card.lead_time_days,
            cycle_time_days=card.cycle_time_days,
            age_days=card.age_days,
            created_at=card.created_at,
            updated_at=card.updated_at,
        )


# =============================================================================
# History Schema
# =============================================================================


class KanbanCardHistoryResponse(BaseModel):
    """Schema for card history response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_at: datetime
    changed_by_id: UUID

    @classmethod
    def from_model(cls, history: KanbanCardHistory) -> "KanbanCardHistoryResponse":
        return cls(
            id=history.id,
            card_id=history.card_id,
            field_name=history.field_name,
            old_value=history.old_value,
            new_value=history.new_value,
            changed_at=history.changed_at,
            changed_by_id=history.changed_by_id,
        )


# =============================================================================
# Metrics Schemas
# =============================================================================


class KanbanMetricsResponse(BaseModel):
    """Schema for Kanban metrics response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    metric_date: date
    cards_completed: int
    story_points_completed: int
    wip_count: int
    blocked_count: int
    avg_cycle_time_hours: Optional[Decimal]
    avg_lead_time_hours: Optional[Decimal]
    avg_card_age_days: Optional[Decimal]
    max_card_age_days: Optional[int]
    column_snapshots: Optional[dict[str, Any]]

    @classmethod
    def from_model(cls, metrics: KanbanMetrics) -> "KanbanMetricsResponse":
        return cls(
            id=metrics.id,
            board_id=metrics.board_id,
            metric_date=metrics.metric_date,
            cards_completed=metrics.cards_completed,
            story_points_completed=metrics.story_points_completed,
            wip_count=metrics.wip_count,
            blocked_count=metrics.blocked_count,
            avg_cycle_time_hours=metrics.avg_cycle_time_hours,
            avg_lead_time_hours=metrics.avg_lead_time_hours,
            avg_card_age_days=metrics.avg_card_age_days,
            max_card_age_days=metrics.max_card_age_days,
            column_snapshots=metrics.column_snapshots,
        )


class BoardStatsResponse(BaseModel):
    """Schema for board statistics response."""

    board_id: int
    board_name: str
    total_cards: int
    active_cards: int
    blocked_cards: int
    completed_cards: int
    overdue_cards: int
    avg_lead_time_days: Optional[float]
    avg_cycle_time_days: Optional[float]
    throughput_30_days: int
    column_stats: dict[str, dict[str, Any]]
    wip_status: dict[str, bool]


# =============================================================================
# Board Endpoints
# =============================================================================


@router.get("/boards", response_model=PaginatedResponse[KanbanBoardResponse])
async def list_kanban_boards(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    board_type: Optional[str] = Query(default=None),
    work_center_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> PaginatedResponse[KanbanBoardResponse]:
    """List Kanban boards with optional filters."""
    query = select(KanbanBoard).where(KanbanBoard.deleted_at.is_(None))

    if board_type and isinstance(board_type, str):
        query = query.where(KanbanBoard.board_type == BoardType(board_type))

    if work_center_id is not None and isinstance(work_center_id, int):
        query = query.where(KanbanBoard.work_center_id == work_center_id)

    if is_active is not None and isinstance(is_active, bool):
        query = query.where(KanbanBoard.is_active == is_active)

    if search and isinstance(search, str):
        search_filter = or_(
            KanbanBoard.name.ilike(f"%{search}%"),
            KanbanBoard.code.ilike(f"%{search}%"),
            KanbanBoard.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(KanbanBoard.name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    boards = result.scalars().all()

    return build_paginated_response(
        data=[KanbanBoardResponse.from_model(b) for b in boards],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/boards", response_model=APIResponse[KanbanBoardResponse], status_code=201)
async def create_kanban_board(
    data: KanbanBoardCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanBoardResponse]:
    """Create a new Kanban board."""
    # Check for duplicate code
    if data.code:
        existing = (
            await db.execute(
                select(KanbanBoard).where(
                    KanbanBoard.code == data.code,
                    KanbanBoard.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Board with code '{data.code}' already exists")

    board = KanbanBoard(
        name=data.name,
        code=data.code,
        description=data.description,
        board_type=BoardType(data.board_type),
        work_center_id=data.work_center_id,
        wip_limit_global=data.wip_limit_global,
        is_active=data.is_active,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    if data.columns_config:
        board.columns_config_json = [c.model_dump() for c in data.columns_config]

    if data.swimlanes_config:
        board.swimlanes_config_json = [s.model_dump() for s in data.swimlanes_config]

    db.add(board)
    await db.commit()
    await db.refresh(board)

    return build_created_response(KanbanBoardResponse.from_model(board), "Kanban board")


@router.get("/boards/{board_id}", response_model=APIResponse[KanbanBoardResponse])
async def get_kanban_board(
    board_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanBoardResponse]:
    """Get a Kanban board by ID."""
    board = (
        await db.execute(
            select(KanbanBoard).where(
                KanbanBoard.id == board_id,
                KanbanBoard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not board:
        raise NotFoundError("Kanban board", board_id)
    return build_response(KanbanBoardResponse.from_model(board))


@router.put("/boards/{board_id}", response_model=APIResponse[KanbanBoardResponse])
async def update_kanban_board(
    board_id: int,
    data: KanbanBoardUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanBoardResponse]:
    """Update a Kanban board."""
    board = (
        await db.execute(
            select(KanbanBoard).where(
                KanbanBoard.id == board_id,
                KanbanBoard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not board:
        raise NotFoundError("Kanban board", board_id)

    # Check for code conflict
    if data.code and data.code != board.code:
        existing = (
            await db.execute(
                select(KanbanBoard).where(
                    KanbanBoard.code == data.code,
                    KanbanBoard.id != board_id,
                    KanbanBoard.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Board with code '{data.code}' already exists")

    update_data = data.model_dump(exclude_unset=True)

    if "board_type" in update_data:
        update_data["board_type"] = BoardType(update_data["board_type"])

    if "columns_config" in update_data:
        update_data["columns_config_json"] = [
            c.model_dump() if isinstance(c, ColumnConfig) else c
            for c in update_data.pop("columns_config")
        ]

    if "swimlanes_config" in update_data:
        update_data["swimlanes_config_json"] = [
            s.model_dump() if isinstance(s, SwimlaneConfig) else s
            for s in update_data.pop("swimlanes_config")
        ]

    for key, value in update_data.items():
        setattr(board, key, value)

    board.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(board)

    return build_updated_response(KanbanBoardResponse.from_model(board), "Kanban board")


@router.delete("/boards/{board_id}", response_model=APIResponse)
async def delete_kanban_board(
    board_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    """Soft delete a Kanban board."""
    board = (
        await db.execute(
            select(KanbanBoard).where(
                KanbanBoard.id == board_id,
                KanbanBoard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not board:
        raise NotFoundError("Kanban board", board_id)

    board.deleted_at = _now_utc()
    board.updated_by_id = current_user.id
    await db.commit()

    return build_deleted_response("Kanban board")


# =============================================================================
# Card Endpoints
# =============================================================================


@router.get("/cards", response_model=PaginatedResponse[KanbanCardResponse])
async def list_kanban_cards(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    board_id: Optional[int] = Query(default=None),
    column_name: Optional[str] = Query(default=None),
    card_type: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    assigned_to_id: Optional[UUID] = Query(default=None),
    is_blocked: Optional[bool] = Query(default=None),
    is_overdue: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> PaginatedResponse[KanbanCardResponse]:
    """List Kanban cards with optional filters."""
    query = select(KanbanCard).where(KanbanCard.deleted_at.is_(None))

    if board_id is not None and isinstance(board_id, int):
        query = query.where(KanbanCard.board_id == board_id)

    if column_name and isinstance(column_name, str):
        query = query.where(KanbanCard.column_name == column_name)

    if card_type and isinstance(card_type, str):
        query = query.where(KanbanCard.card_type == CardType(card_type))

    if priority and isinstance(priority, str):
        query = query.where(KanbanCard.priority == CardPriority(priority))

    if status and isinstance(status, str):
        query = query.where(KanbanCard.status == CardStatus(status))

    if assigned_to_id is not None and isinstance(assigned_to_id, UUID):
        query = query.where(KanbanCard.assigned_to_id == assigned_to_id)

    if is_blocked is True:
        query = query.where(KanbanCard.status == CardStatus.BLOCKED)
    elif is_blocked is False:
        query = query.where(KanbanCard.status != CardStatus.BLOCKED)

    if is_overdue is True:
        today = date.today()
        query = query.where(
            and_(
                KanbanCard.due_date < today,
                KanbanCard.status != CardStatus.COMPLETED,
            )
        )

    if search and isinstance(search, str):
        search_filter = or_(
            KanbanCard.card_number.ilike(f"%{search}%"),
            KanbanCard.title.ilike(f"%{search}%"),
            KanbanCard.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(KanbanCard.priority.desc(), KanbanCard.position)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    cards = result.scalars().all()

    return build_paginated_response(
        data=[KanbanCardResponse.from_model(c) for c in cards],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/cards", response_model=APIResponse[KanbanCardResponse], status_code=201)
async def create_kanban_card(
    data: KanbanCardCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Create a new Kanban card."""
    # Check board exists
    board = (
        await db.execute(
            select(KanbanBoard).where(
                KanbanBoard.id == data.board_id,
                KanbanBoard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not board:
        raise NotFoundError("Kanban board", data.board_id)

    # Check for duplicate card number on board
    existing = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.board_id == data.board_id,
                KanbanCard.card_number == data.card_number,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"Card '{data.card_number}' already exists on board"
        )

    # Check column WIP limit
    if board.is_column_at_limit(data.column_name):
        raise ConflictError(
            f"Column '{data.column_name}' is at WIP limit"
        )

    # Check global WIP limit
    if board.is_at_global_limit:
        raise ConflictError("Board is at global WIP limit")

    now = _now_utc()
    card = KanbanCard(
        card_number=data.card_number,
        title=data.title,
        description=data.description,
        board_id=data.board_id,
        column_name=data.column_name,
        swimlane_name=data.swimlane_name,
        position=data.position,
        card_type=CardType(data.card_type),
        priority=CardPriority(data.priority),
        work_order_id=data.work_order_id,
        product_id=data.product_id,
        quantity=data.quantity,
        assigned_to_id=data.assigned_to_id,
        due_date=data.due_date,
        story_points=data.story_points,
        estimated_hours=data.estimated_hours,
        tags=data.tags,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    # If column is not backlog, mark cycle started
    if data.column_name not in ["Backlog", board.first_column]:
        card.cycle_started_at = now
        card.started_at = now

    db.add(card)
    await db.commit()
    await db.refresh(card)

    return build_created_response(KanbanCardResponse.from_model(card), "Kanban card")


@router.get("/cards/{card_id}", response_model=APIResponse[KanbanCardResponse])
async def get_kanban_card(
    card_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Get a Kanban card by ID."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)
    return build_response(KanbanCardResponse.from_model(card))


@router.put("/cards/{card_id}", response_model=APIResponse[KanbanCardResponse])
async def update_kanban_card(
    card_id: int,
    data: KanbanCardUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Update a Kanban card."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    update_data = data.model_dump(exclude_unset=True)

    if "card_type" in update_data:
        update_data["card_type"] = CardType(update_data["card_type"])

    if "priority" in update_data:
        old_priority = card.priority.value
        new_priority = update_data["priority"]
        update_data["priority"] = CardPriority(new_priority)
        # Record history
        history = KanbanCardHistory(
            card_id=card.id,
            field_name="priority",
            old_value=old_priority,
            new_value=new_priority,
            changed_at=_now_utc(),
            changed_by_id=current_user.id,
        )
        db.add(history)

    for key, value in update_data.items():
        setattr(card, key, value)

    card.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(card)

    return build_updated_response(KanbanCardResponse.from_model(card), "Kanban card")


@router.delete("/cards/{card_id}", response_model=APIResponse)
async def delete_kanban_card(
    card_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    """Soft delete a Kanban card."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    card.deleted_at = _now_utc()
    card.updated_by_id = current_user.id
    await db.commit()

    return build_deleted_response("Kanban card")


# =============================================================================
# Card Workflow Endpoints
# =============================================================================


@router.post("/cards/{card_id}/move", response_model=APIResponse[KanbanCardResponse])
async def move_kanban_card(
    card_id: int,
    data: KanbanCardMoveRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Move a Kanban card to a different column."""
    card = (
        await db.execute(
            select(KanbanCard)
            .options(selectinload(KanbanCard.board))
            .where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    if card.status == CardStatus.COMPLETED:
        raise ConflictError("Cannot move a completed card")

    if card.status == CardStatus.CANCELLED:
        raise ConflictError("Cannot move a cancelled card")

    board = card.board
    old_column = card.column_name
    new_column = data.column_name

    # Check if destination column is at WIP limit
    if old_column != new_column:
        if board.is_column_at_limit(new_column) and not card.wip_limit_override:
            raise ConflictError(
                f"Column '{new_column}' is at WIP limit"
            )

    now = _now_utc()

    # Record history
    history = KanbanCardHistory(
        card_id=card.id,
        field_name="column_name",
        old_value=old_column,
        new_value=new_column,
        changed_at=now,
        changed_by_id=current_user.id,
    )
    db.add(history)

    # Update cycle times
    if old_column == board.first_column and new_column != board.first_column:
        # Started work
        if not card.cycle_started_at:
            card.cycle_started_at = now
        if not card.started_at:
            card.started_at = now

    if new_column == board.last_column and old_column != board.last_column:
        # Completed work
        card.cycle_completed_at = now
        card.completed_at = now
        card.status = CardStatus.COMPLETED

    card.column_name = new_column
    if data.position is not None:
        card.position = data.position
    if data.swimlane_name is not None:
        card.swimlane_name = data.swimlane_name
    card.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(card)

    return build_response(KanbanCardResponse.from_model(card))


@router.post("/cards/{card_id}/block", response_model=APIResponse[KanbanCardResponse])
async def block_kanban_card(
    card_id: int,
    data: KanbanCardBlockRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Block a Kanban card."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    if card.status != CardStatus.ACTIVE:
        raise ConflictError(f"Cannot block card in status: {card.status.value}")

    now = _now_utc()
    old_status = card.status.value

    card.status = CardStatus.BLOCKED
    card.blocked_reason = data.blocked_reason
    card.updated_by_id = current_user.id

    history = KanbanCardHistory(
        card_id=card.id,
        field_name="status",
        old_value=old_status,
        new_value=CardStatus.BLOCKED.value,
        changed_at=now,
        changed_by_id=current_user.id,
    )
    db.add(history)

    await db.commit()
    await db.refresh(card)

    return build_response(KanbanCardResponse.from_model(card))


@router.post("/cards/{card_id}/unblock", response_model=APIResponse[KanbanCardResponse])
async def unblock_kanban_card(
    card_id: int,
    data: KanbanCardUnblockRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Unblock a Kanban card."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    if card.status != CardStatus.BLOCKED:
        raise ConflictError("Card is not blocked")

    now = _now_utc()
    old_status = card.status.value

    card.status = CardStatus.ACTIVE
    card.blocked_reason = None
    card.updated_by_id = current_user.id

    history = KanbanCardHistory(
        card_id=card.id,
        field_name="status",
        old_value=old_status,
        new_value=CardStatus.ACTIVE.value,
        changed_at=now,
        changed_by_id=current_user.id,
    )
    db.add(history)

    await db.commit()
    await db.refresh(card)

    return build_response(KanbanCardResponse.from_model(card))


@router.post("/cards/{card_id}/complete", response_model=APIResponse[KanbanCardResponse])
async def complete_kanban_card(
    card_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Mark a Kanban card as completed."""
    card = (
        await db.execute(
            select(KanbanCard)
            .options(selectinload(KanbanCard.board))
            .where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    if card.status == CardStatus.COMPLETED:
        raise ConflictError("Card is already completed")

    if card.status == CardStatus.CANCELLED:
        raise ConflictError("Cannot complete a cancelled card")

    now = _now_utc()
    old_status = card.status.value

    card.status = CardStatus.COMPLETED
    card.completed_at = now
    if not card.cycle_completed_at:
        card.cycle_completed_at = now
    card.column_name = card.board.last_column
    card.updated_by_id = current_user.id

    history = KanbanCardHistory(
        card_id=card.id,
        field_name="status",
        old_value=old_status,
        new_value=CardStatus.COMPLETED.value,
        changed_at=now,
        changed_by_id=current_user.id,
    )
    db.add(history)

    await db.commit()
    await db.refresh(card)

    return build_response(KanbanCardResponse.from_model(card))


@router.post("/cards/{card_id}/cancel", response_model=APIResponse[KanbanCardResponse])
async def cancel_kanban_card(
    card_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Cancel a Kanban card."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    if card.status == CardStatus.COMPLETED:
        raise ConflictError("Cannot cancel a completed card")

    if card.status == CardStatus.CANCELLED:
        raise ConflictError("Card is already cancelled")

    now = _now_utc()
    old_status = card.status.value

    card.status = CardStatus.CANCELLED
    card.updated_by_id = current_user.id

    history = KanbanCardHistory(
        card_id=card.id,
        field_name="status",
        old_value=old_status,
        new_value=CardStatus.CANCELLED.value,
        changed_at=now,
        changed_by_id=current_user.id,
    )
    db.add(history)

    await db.commit()
    await db.refresh(card)

    return build_response(KanbanCardResponse.from_model(card))


@router.post("/cards/{card_id}/wip-override", response_model=APIResponse[KanbanCardResponse])
async def override_wip_limit(
    card_id: int,
    data: WIPOverrideRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[KanbanCardResponse]:
    """Request WIP limit override for a card (GM approval)."""
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    card.wip_limit_override = True
    card.wip_limit_override_by_id = current_user.id
    card.wip_limit_override_reason = data.reason
    card.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(card)

    return build_response(KanbanCardResponse.from_model(card))


# =============================================================================
# Card History Endpoints
# =============================================================================


@router.get("/cards/{card_id}/history", response_model=PaginatedResponse[KanbanCardHistoryResponse])
async def list_card_history(
    card_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[KanbanCardHistoryResponse]:
    """List history for a Kanban card."""
    # Verify card exists
    card = (
        await db.execute(
            select(KanbanCard).where(
                KanbanCard.id == card_id,
                KanbanCard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not card:
        raise NotFoundError("Kanban card", card_id)

    query = select(KanbanCardHistory).where(KanbanCardHistory.card_id == card_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(KanbanCardHistory.changed_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    history = result.scalars().all()

    return build_paginated_response(
        data=[KanbanCardHistoryResponse.from_model(h) for h in history],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Metrics Endpoints
# =============================================================================


@router.get("/boards/{board_id}/metrics", response_model=PaginatedResponse[KanbanMetricsResponse])
async def list_board_metrics(
    board_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
) -> PaginatedResponse[KanbanMetricsResponse]:
    """List metrics for a Kanban board."""
    # Verify board exists
    board = (
        await db.execute(
            select(KanbanBoard).where(
                KanbanBoard.id == board_id,
                KanbanBoard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not board:
        raise NotFoundError("Kanban board", board_id)

    query = select(KanbanMetrics).where(KanbanMetrics.board_id == board_id)

    if start_date:
        query = query.where(KanbanMetrics.metric_date >= start_date)

    if end_date:
        query = query.where(KanbanMetrics.metric_date <= end_date)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(KanbanMetrics.metric_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    metrics = result.scalars().all()

    return build_paginated_response(
        data=[KanbanMetricsResponse.from_model(m) for m in metrics],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/boards/{board_id}/stats", response_model=APIResponse[BoardStatsResponse])
async def get_board_stats(
    board_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[BoardStatsResponse]:
    """Get current statistics for a Kanban board."""
    board = (
        await db.execute(
            select(KanbanBoard)
            .options(selectinload(KanbanBoard.cards))
            .where(
                KanbanBoard.id == board_id,
                KanbanBoard.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not board:
        raise NotFoundError("Kanban board", board_id)

    # Get cards (not deleted)
    cards = [c for c in board.cards if c.deleted_at is None]
    today = date.today()
    thirty_days_ago = _now_utc() - timedelta(days=30)

    # Calculate stats
    total_cards = len(cards)
    active_cards = sum(1 for c in cards if c.status == CardStatus.ACTIVE)
    blocked_cards = sum(1 for c in cards if c.status == CardStatus.BLOCKED)
    completed_cards = sum(1 for c in cards if c.status == CardStatus.COMPLETED)
    overdue_cards = sum(
        1 for c in cards
        if c.due_date and c.due_date < today and c.status != CardStatus.COMPLETED
    )

    # Throughput (completed in last 30 days)
    throughput = sum(
        1 for c in cards
        if c.completed_at and c.completed_at >= thirty_days_ago
    )

    # Average lead time for completed cards
    lead_times = [c.lead_time_days for c in cards if c.lead_time_days is not None]
    avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else None

    # Average cycle time for completed cards
    cycle_times = [c.cycle_time_days for c in cards if c.cycle_time_days is not None]
    avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else None

    # Column stats
    column_stats = {}
    wip_status = {}
    for col_config in board.columns_config_json:
        col_name = col_config["name"]
        col_cards = [c for c in cards if c.column_name == col_name and c.status == CardStatus.ACTIVE]
        wip_limit = col_config.get("wip_limit")
        column_stats[col_name] = {
            "count": len(col_cards),
            "blocked": sum(1 for c in col_cards if c.status == CardStatus.BLOCKED),
            "wip_limit": wip_limit,
        }
        wip_status[col_name] = wip_limit is not None and len(col_cards) >= wip_limit

    stats = BoardStatsResponse(
        board_id=board.id,
        board_name=board.name,
        total_cards=total_cards,
        active_cards=active_cards,
        blocked_cards=blocked_cards,
        completed_cards=completed_cards,
        overdue_cards=overdue_cards,
        avg_lead_time_days=avg_lead_time,
        avg_cycle_time_days=avg_cycle_time,
        throughput_30_days=throughput,
        column_stats=column_stats,
        wip_status=wip_status,
    )

    return build_response(stats)

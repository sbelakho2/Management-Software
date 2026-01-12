"""Tests for Kanban API endpoints."""

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.v1.endpoints.kanban import (
    # Board endpoints
    list_kanban_boards,
    create_kanban_board,
    get_kanban_board,
    update_kanban_board,
    delete_kanban_board,
    # Card endpoints
    list_kanban_cards,
    create_kanban_card,
    get_kanban_card,
    update_kanban_card,
    delete_kanban_card,
    # Card workflow endpoints
    move_kanban_card,
    block_kanban_card,
    unblock_kanban_card,
    complete_kanban_card,
    cancel_kanban_card,
    override_wip_limit,
    # History endpoints
    list_card_history,
    # Metrics endpoints
    list_board_metrics,
    get_board_stats,
    # Schemas
    KanbanBoardCreate,
    KanbanBoardUpdate,
    KanbanCardCreate,
    KanbanCardUpdate,
    KanbanCardMoveRequest,
    KanbanCardBlockRequest,
    KanbanCardUnblockRequest,
    WIPOverrideRequest,
    ColumnConfig,
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


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


_NOT_SET = object()  # Sentinel for distinguishing None from unset


def make_result(
    scalar_one_or_none=_NOT_SET,
    scalars_all=_NOT_SET,
    scalar=_NOT_SET,
):
    """Create a mock result object."""
    result = MagicMock()
    if scalar_one_or_none is not _NOT_SET:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    if scalars_all is not _NOT_SET:
        scalars_result = MagicMock()
        scalars_result.all.return_value = scalars_all
        result.scalars.return_value = scalars_result
    if scalar is not _NOT_SET:
        result.scalar.return_value = scalar
    return result


def make_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def make_user():
    """Create a mock current user."""
    user = MagicMock()
    user.id = uuid4()
    return user


# =============================================================================
# Board CRUD Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_board_crud():
    """Test Kanban board CRUD operations."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Create a mock board
    board = MagicMock(spec=KanbanBoard)
    board.id = 1
    board.name = "Production Board"
    board.code = "PROD-001"
    board.description = "Main production Kanban"
    board.board_type = BoardType.PRODUCTION
    board.work_center_id = 10
    board.wip_limit_global = 20
    board.columns_config_json = [
        {"name": "Backlog", "order": 0, "wip_limit": None},
        {"name": "In Progress", "order": 1, "wip_limit": 5},
        {"name": "Done", "order": 2, "wip_limit": None},
    ]
    board.swimlanes_config_json = None
    board.is_active = True
    board.deleted_at = None
    board.created_at = now
    board.updated_at = now
    board.cards = []
    board.total_active_cards = 0
    board.is_at_global_limit = False
    board.column_names = ["Backlog", "In Progress", "Done"]
    board.first_column = "Backlog"
    board.last_column = "Done"

    # Test list boards
    db.execute.side_effect = [
        make_result(scalar=2),  # count query
        make_result(scalars_all=[board]),  # main query
    ]
    page = await list_kanban_boards(db, current_user, page=1, page_size=20)
    assert page.pagination.total_items == 2

    # Test create board
    db.execute.side_effect = None
    db.execute.return_value = make_result(scalar_one_or_none=None)

    def capture_add(obj: Any):
        obj.id = board.id
        obj.created_at = now
        obj.updated_at = now
        obj.cards = []  # Set cards to empty list for computed properties

    db.add.side_effect = capture_add
    
    # Mock refresh to return the board with computed properties
    async def mock_refresh(obj):
        # Copy properties from mock board to the real object
        obj.cards = []  # Ensure cards is initialized
    
    db.refresh = mock_refresh

    resp = await create_kanban_board(
        KanbanBoardCreate(
            name="Production Board",
            code="PROD-001",
            description="Main production Kanban",
            board_type="production",
            work_center_id=10,
            wip_limit_global=20,
            columns_config=[
                ColumnConfig(name="Backlog", order=0),
                ColumnConfig(name="In Progress", order=1, wip_limit=5),
                ColumnConfig(name="Done", order=2),
            ],
        ),
        db,
        current_user,
    )
    assert resp.data.name == "Production Board"

    db.add.side_effect = None

    # Test duplicate code conflict
    db.execute.return_value = make_result(scalar_one_or_none=board)
    with pytest.raises(ConflictError):
        await create_kanban_board(
            KanbanBoardCreate(name="Another Board", code="PROD-001"),
            db,
            current_user,
        )

    # Test get board
    db.execute.return_value = make_result(scalar_one_or_none=board)
    resp = await get_kanban_board(1, db, current_user)
    assert resp.data.id == 1
    assert resp.data.name == "Production Board"

    # Test get board not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_kanban_board(999, db, current_user)

    # Test update board
    db.execute.side_effect = [
        make_result(scalar_one_or_none=board),  # get board
        make_result(scalar_one_or_none=None),  # code check
    ]
    resp = await update_kanban_board(
        1,
        KanbanBoardUpdate(name="Updated Board", wip_limit_global=30),
        db,
        current_user,
    )
    assert resp.success is True

    # Test delete board
    db.execute.side_effect = None
    db.execute.return_value = make_result(scalar_one_or_none=board)
    resp = await delete_kanban_board(1, db, current_user)
    assert resp.success is True

    # Test delete not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await delete_kanban_board(999, db, current_user)


# =============================================================================
# Card CRUD Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_card_crud():
    """Test Kanban card CRUD operations."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_id = uuid4()

    # Mock board
    board = MagicMock(spec=KanbanBoard)
    board.id = 1
    board.name = "Production Board"
    board.first_column = "Backlog"
    board.last_column = "Done"
    board.deleted_at = None
    board.is_column_at_limit = MagicMock(return_value=False)
    board.is_at_global_limit = False

    # Mock card
    card = MagicMock(spec=KanbanCard)
    card.id = 1
    card.card_number = "KAN-001"
    card.title = "Implement feature"
    card.description = "New feature implementation"
    card.board_id = 1
    card.column_name = "Backlog"
    card.swimlane_name = None
    card.position = 0
    card.card_type = CardType.TASK
    card.priority = CardPriority.NORMAL
    card.status = CardStatus.ACTIVE
    card.blocked_reason = None
    card.work_order_id = None
    card.product_id = None
    card.quantity = None
    card.assigned_to_id = user_id
    card.due_date = date.today() + timedelta(days=7)
    card.started_at = None
    card.completed_at = None
    card.cycle_started_at = None
    card.cycle_completed_at = None
    card.story_points = 5
    card.estimated_hours = Decimal("8.0")
    card.actual_hours = None
    card.tags = ["feature", "priority"]
    card.wip_limit_override = False
    card.wip_limit_override_reason = None
    card.deleted_at = None
    card.created_at = now
    card.updated_at = now
    card.board = board
    card.is_active = True
    card.is_blocked = False
    card.is_completed = False
    card.is_overdue = False
    card.lead_time_days = None
    card.cycle_time_days = None
    card.age_days = 0

    # Test list cards
    db.execute.side_effect = [
        make_result(scalar=1),  # count
        make_result(scalars_all=[card]),  # main query
    ]
    page = await list_kanban_cards(db, current_user, page=1, page_size=20, board_id=1)
    assert page.pagination.total_items == 1

    db.execute.side_effect = None

    # Test create card
    db.execute.side_effect = [
        make_result(scalar_one_or_none=board),  # get board
        make_result(scalar_one_or_none=None),  # duplicate check
    ]

    def capture_card(obj: Any):
        obj.id = card.id
        obj.created_at = now
        obj.updated_at = now
        obj.status = CardStatus.ACTIVE
        obj.wip_limit_override = False

    db.add.side_effect = capture_card

    resp = await create_kanban_card(
        KanbanCardCreate(
            card_number="KAN-001",
            title="Implement feature",
            description="New feature implementation",
            board_id=1,
            column_name="Backlog",
            card_type="task",
            priority="normal",
            assigned_to_id=user_id,
            due_date=date.today() + timedelta(days=7),
            story_points=5,
            estimated_hours=Decimal("8.0"),
            tags=["feature", "priority"],
        ),
        db,
        current_user,
    )
    assert resp.data.card_number == "KAN-001"

    db.add.side_effect = None
    db.execute.side_effect = None

    # Test board not found on create
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await create_kanban_card(
            KanbanCardCreate(
                card_number="KAN-002",
                title="Another",
                board_id=999,
                column_name="Backlog",
            ),
            db,
            current_user,
        )

    # Test duplicate card number
    db.execute.side_effect = [
        make_result(scalar_one_or_none=board),  # board found
        make_result(scalar_one_or_none=card),  # duplicate found
    ]
    with pytest.raises(ConflictError):
        await create_kanban_card(
            KanbanCardCreate(
                card_number="KAN-001",
                title="Duplicate",
                board_id=1,
                column_name="Backlog",
            ),
            db,
            current_user,
        )

    # Test column at WIP limit
    board.is_column_at_limit = MagicMock(return_value=True)
    db.execute.side_effect = [
        make_result(scalar_one_or_none=board),
        make_result(scalar_one_or_none=None),
    ]
    with pytest.raises(ConflictError):
        await create_kanban_card(
            KanbanCardCreate(
                card_number="KAN-003",
                title="WIP limited",
                board_id=1,
                column_name="In Progress",
            ),
            db,
            current_user,
        )
    board.is_column_at_limit = MagicMock(return_value=False)

    # Test get card
    db.execute.side_effect = None
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await get_kanban_card(1, db, current_user)
    assert resp.data.id == 1

    # Test get card not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_kanban_card(999, db, current_user)

    # Test update card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await update_kanban_card(
        1,
        KanbanCardUpdate(title="Updated title", story_points=8),
        db,
        current_user,
    )
    assert resp.success is True

    # Test delete card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await delete_kanban_card(1, db, current_user)
    assert resp.success is True

    # Test delete card not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await delete_kanban_card(999, db, current_user)


# =============================================================================
# Card Workflow Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_card_workflow():
    """Test Kanban card workflow operations."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Mock board
    board = MagicMock(spec=KanbanBoard)
    board.id = 1
    board.first_column = "Backlog"
    board.last_column = "Done"
    board.is_column_at_limit = MagicMock(return_value=False)

    # Mock card
    card = MagicMock(spec=KanbanCard)
    card.id = 1
    card.card_number = "KAN-001"
    card.title = "Test Card"
    card.description = None
    card.board_id = 1
    card.column_name = "Backlog"
    card.swimlane_name = None
    card.position = 0
    card.card_type = CardType.TASK
    card.priority = CardPriority.NORMAL
    card.status = CardStatus.ACTIVE
    card.blocked_reason = None
    card.work_order_id = None
    card.product_id = None
    card.quantity = None
    card.assigned_to_id = None
    card.due_date = None
    card.started_at = None
    card.completed_at = None
    card.cycle_started_at = None
    card.cycle_completed_at = None
    card.story_points = None
    card.estimated_hours = None
    card.actual_hours = None
    card.tags = None
    card.wip_limit_override = False
    card.wip_limit_override_reason = None
    card.deleted_at = None
    card.created_at = now
    card.updated_at = now
    card.board = board
    card.is_active = True
    card.is_blocked = False
    card.is_completed = False
    card.is_overdue = False
    card.lead_time_days = None
    card.cycle_time_days = None
    card.age_days = 0

    # Test move card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await move_kanban_card(
        1,
        KanbanCardMoveRequest(column_name="In Progress", position=0),
        db,
        current_user,
    )
    assert resp.data.id == 1

    # Test move completed card fails
    card.status = CardStatus.COMPLETED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await move_kanban_card(
            1,
            KanbanCardMoveRequest(column_name="Done"),
            db,
            current_user,
        )
    card.status = CardStatus.ACTIVE

    # Test move cancelled card fails
    card.status = CardStatus.CANCELLED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await move_kanban_card(
            1,
            KanbanCardMoveRequest(column_name="Done"),
            db,
            current_user,
        )
    card.status = CardStatus.ACTIVE

    # Test move to WIP limited column
    board.is_column_at_limit = MagicMock(return_value=True)
    card.column_name = "Backlog"
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await move_kanban_card(
            1,
            KanbanCardMoveRequest(column_name="In Progress"),
            db,
            current_user,
        )
    board.is_column_at_limit = MagicMock(return_value=False)

    # Test block card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await block_kanban_card(
        1,
        KanbanCardBlockRequest(blocked_reason="Waiting for parts"),
        db,
        current_user,
    )
    assert resp.data.id == 1

    # Test block non-active card fails
    card.status = CardStatus.BLOCKED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await block_kanban_card(
            1,
            KanbanCardBlockRequest(blocked_reason="Another reason"),
            db,
            current_user,
        )
    card.status = CardStatus.BLOCKED

    # Test unblock card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await unblock_kanban_card(
        1,
        KanbanCardUnblockRequest(notes="Parts arrived"),
        db,
        current_user,
    )
    assert resp.data.id == 1

    # Test unblock non-blocked card fails
    card.status = CardStatus.ACTIVE
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await unblock_kanban_card(
            1,
            KanbanCardUnblockRequest(),
            db,
            current_user,
        )

    # Test complete card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await complete_kanban_card(1, db, current_user)
    assert resp.data.id == 1

    # Test complete already completed card fails
    card.status = CardStatus.COMPLETED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await complete_kanban_card(1, db, current_user)
    card.status = CardStatus.ACTIVE

    # Test complete cancelled card fails
    card.status = CardStatus.CANCELLED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await complete_kanban_card(1, db, current_user)
    card.status = CardStatus.ACTIVE

    # Test cancel card
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await cancel_kanban_card(1, db, current_user)
    assert resp.data.id == 1

    # Test cancel completed card fails
    card.status = CardStatus.COMPLETED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await cancel_kanban_card(1, db, current_user)
    card.status = CardStatus.ACTIVE

    # Test cancel already cancelled card fails
    card.status = CardStatus.CANCELLED
    db.execute.return_value = make_result(scalar_one_or_none=card)
    with pytest.raises(ConflictError):
        await cancel_kanban_card(1, db, current_user)
    card.status = CardStatus.ACTIVE

    # Test WIP override
    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await override_wip_limit(
        1,
        WIPOverrideRequest(reason="GM approved for urgent work"),
        db,
        current_user,
    )
    assert resp.data.id == 1


# =============================================================================
# Card History Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_card_history():
    """Test Kanban card history operations."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_id = uuid4()

    # Mock card
    card = MagicMock(spec=KanbanCard)
    card.id = 1
    card.deleted_at = None

    # Mock history
    history = MagicMock(spec=KanbanCardHistory)
    history.id = 1
    history.card_id = 1
    history.field_name = "column_name"
    history.old_value = "Backlog"
    history.new_value = "In Progress"
    history.changed_at = now
    history.changed_by_id = user_id

    # Test list history
    db.execute.side_effect = [
        make_result(scalar_one_or_none=card),  # card exists
        make_result(scalar=1),  # count
        make_result(scalars_all=[history]),  # main query
    ]
    page = await list_card_history(1, db, current_user, page=1, page_size=20)
    assert page.pagination.total_items == 1
    assert page.data[0].field_name == "column_name"

    # Test card not found
    db.execute.side_effect = None
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await list_card_history(999, db, current_user)


# =============================================================================
# Metrics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_board_metrics():
    """Test Kanban board metrics operations."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()

    # Mock board
    board = MagicMock(spec=KanbanBoard)
    board.id = 1
    board.name = "Production Board"
    board.deleted_at = None
    board.columns_config_json = [
        {"name": "Backlog", "order": 0, "wip_limit": None},
        {"name": "In Progress", "order": 1, "wip_limit": 5},
        {"name": "Done", "order": 2, "wip_limit": None},
    ]
    board.cards = []

    # Mock metrics
    metrics = MagicMock(spec=KanbanMetrics)
    metrics.id = 1
    metrics.board_id = 1
    metrics.metric_date = today
    metrics.cards_completed = 5
    metrics.story_points_completed = 13
    metrics.wip_count = 8
    metrics.blocked_count = 1
    metrics.avg_cycle_time_hours = Decimal("24.5")
    metrics.avg_lead_time_hours = Decimal("72.0")
    metrics.avg_card_age_days = Decimal("3.5")
    metrics.max_card_age_days = 7
    metrics.column_snapshots = {
        "Backlog": {"count": 10, "blocked": 0},
        "In Progress": {"count": 5, "blocked": 1},
        "Done": {"count": 20, "blocked": 0},
    }

    # Test list metrics
    db.execute.side_effect = [
        make_result(scalar_one_or_none=board),  # board exists
        make_result(scalar=5),  # count
        make_result(scalars_all=[metrics]),  # main query
    ]
    page = await list_board_metrics(
        1,
        db,
        current_user,
        page=1,
        page_size=20,
        start_date=today - timedelta(days=30),
    )
    assert page.pagination.total_items == 5
    assert page.data[0].cards_completed == 5

    # Test board not found
    db.execute.side_effect = None
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await list_board_metrics(999, db, current_user)


@pytest.mark.asyncio
async def test_kanban_board_stats():
    """Test Kanban board stats endpoint."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()

    # Create mock cards with different statuses
    active_card = MagicMock(spec=KanbanCard)
    active_card.status = CardStatus.ACTIVE
    active_card.column_name = "In Progress"
    active_card.due_date = None
    active_card.completed_at = None
    active_card.lead_time_days = None
    active_card.cycle_time_days = None
    active_card.deleted_at = None

    blocked_card = MagicMock(spec=KanbanCard)
    blocked_card.status = CardStatus.BLOCKED
    blocked_card.column_name = "In Progress"
    blocked_card.due_date = None
    blocked_card.completed_at = None
    blocked_card.lead_time_days = None
    blocked_card.cycle_time_days = None
    blocked_card.deleted_at = None

    completed_card = MagicMock(spec=KanbanCard)
    completed_card.status = CardStatus.COMPLETED
    completed_card.column_name = "Done"
    completed_card.due_date = None
    completed_card.completed_at = now
    completed_card.lead_time_days = 5
    completed_card.cycle_time_days = 2.5
    completed_card.deleted_at = None

    overdue_card = MagicMock(spec=KanbanCard)
    overdue_card.status = CardStatus.ACTIVE
    overdue_card.column_name = "Backlog"
    overdue_card.due_date = today - timedelta(days=1)
    overdue_card.completed_at = None
    overdue_card.lead_time_days = None
    overdue_card.cycle_time_days = None
    overdue_card.deleted_at = None

    # Mock board
    board = MagicMock(spec=KanbanBoard)
    board.id = 1
    board.name = "Production Board"
    board.deleted_at = None
    board.columns_config_json = [
        {"name": "Backlog", "order": 0, "wip_limit": None},
        {"name": "In Progress", "order": 1, "wip_limit": 5},
        {"name": "Done", "order": 2, "wip_limit": None},
    ]
    board.cards = [active_card, blocked_card, completed_card, overdue_card]

    db.execute.return_value = make_result(scalar_one_or_none=board)
    resp = await get_board_stats(1, db, current_user)

    assert resp.data.board_id == 1
    assert resp.data.total_cards == 4
    assert resp.data.active_cards == 2
    assert resp.data.blocked_cards == 1
    assert resp.data.completed_cards == 1
    assert resp.data.overdue_cards == 1

    # Test board not found
    db.execute.return_value = make_result(scalar_one_or_none=None)
    with pytest.raises(NotFoundError):
        await get_board_stats(999, db, current_user)


# =============================================================================
# Filter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_list_filters():
    """Test list endpoints with various filters."""
    db = make_db()
    current_user = make_user()
    user_id = uuid4()

    # Test board filters
    db.execute.side_effect = [
        make_result(scalar=0),
        make_result(scalars_all=[]),
    ]
    page = await list_kanban_boards(
        db,
        current_user,
        page=1,
        page_size=20,
        board_type="production",
        work_center_id=10,
        is_active=True,
        search="test",
    )
    assert page.pagination.total_items == 0

    # Test card filters
    db.execute.side_effect = [
        make_result(scalar=0),
        make_result(scalars_all=[]),
    ]
    page = await list_kanban_cards(
        db,
        current_user,
        page=1,
        page_size=20,
        board_id=1,
        column_name="In Progress",
        card_type="task",
        priority="high",
        status="active",
        assigned_to_id=user_id,
        is_blocked=False,
        is_overdue=True,
        search="feature",
    )
    assert page.pagination.total_items == 0


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
async def test_kanban_card_computed_properties():
    """Test card computed properties in response."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()

    # Mock card with all computed properties
    card = MagicMock(spec=KanbanCard)
    card.id = 1
    card.card_number = "KAN-001"
    card.title = "Test Card"
    card.description = None
    card.board_id = 1
    card.column_name = "Done"
    card.swimlane_name = None
    card.position = 0
    card.card_type = CardType.TASK
    card.priority = CardPriority.HIGH
    card.status = CardStatus.COMPLETED
    card.blocked_reason = None
    card.work_order_id = None
    card.product_id = None
    card.quantity = None
    card.assigned_to_id = None
    card.due_date = today - timedelta(days=1)  # Overdue
    card.started_at = now - timedelta(hours=48)
    card.completed_at = now
    card.cycle_started_at = now - timedelta(hours=48)
    card.cycle_completed_at = now
    card.story_points = 5
    card.estimated_hours = Decimal("8.0")
    card.actual_hours = Decimal("10.0")
    card.tags = ["done"]
    card.wip_limit_override = False
    card.wip_limit_override_reason = None
    card.deleted_at = None
    card.created_at = now - timedelta(days=3)
    card.updated_at = now
    card.is_active = False
    card.is_blocked = False
    card.is_completed = True
    card.is_overdue = False  # Not overdue because completed
    card.lead_time_days = 3
    card.cycle_time_days = 2.0
    card.age_days = 3

    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await get_kanban_card(1, db, current_user)

    assert resp.data.is_completed is True
    assert resp.data.lead_time_days == 3
    assert resp.data.cycle_time_days == 2.0
    assert resp.data.age_days == 3


@pytest.mark.asyncio
async def test_kanban_card_move_to_done_completes():
    """Test that moving card to done column sets completion."""
    db = make_db()
    current_user = make_user()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Mock board
    board = MagicMock(spec=KanbanBoard)
    board.id = 1
    board.first_column = "Backlog"
    board.last_column = "Done"
    board.is_column_at_limit = MagicMock(return_value=False)

    # Mock card
    card = MagicMock(spec=KanbanCard)
    card.id = 1
    card.card_number = "KAN-001"
    card.title = "Test Card"
    card.description = None
    card.board_id = 1
    card.column_name = "In Progress"
    card.swimlane_name = None
    card.position = 0
    card.card_type = CardType.TASK
    card.priority = CardPriority.NORMAL
    card.status = CardStatus.ACTIVE
    card.blocked_reason = None
    card.work_order_id = None
    card.product_id = None
    card.quantity = None
    card.assigned_to_id = None
    card.due_date = None
    card.started_at = now - timedelta(hours=24)
    card.completed_at = None
    card.cycle_started_at = now - timedelta(hours=24)
    card.cycle_completed_at = None
    card.story_points = None
    card.estimated_hours = None
    card.actual_hours = None
    card.tags = None
    card.wip_limit_override = False
    card.wip_limit_override_reason = None
    card.deleted_at = None
    card.created_at = now
    card.updated_at = now
    card.board = board
    card.is_active = True
    card.is_blocked = False
    card.is_completed = False
    card.is_overdue = False
    card.lead_time_days = None
    card.cycle_time_days = None
    card.age_days = 0

    db.execute.return_value = make_result(scalar_one_or_none=card)
    resp = await move_kanban_card(
        1,
        KanbanCardMoveRequest(column_name="Done"),
        db,
        current_user,
    )
    assert resp.data.id == 1
    # Card should be set to completed when moved to done column
    assert card.status == CardStatus.COMPLETED

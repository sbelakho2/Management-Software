"""Tests for Obeya API endpoints.

Full test coverage for Obeya visual management board operations:
- Item CRUD operations
- Item workflow (start, block, unblock, complete, cancel, escalate)
- Comment operations
- Query endpoints
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.obeya import (
    ObeyaItemCreate,
    ObeyaItemUpdate,
    EscalationData,
    CommentCreate,
    CommentUpdate,
    create_obeya_item,
    get_obeya_item,
    list_obeya_items,
    update_obeya_item,
    delete_obeya_item,
    start_item,
    block_item,
    unblock_item,
    set_waiting,
    complete_item,
    cancel_item,
    escalate_item,
    deescalate_item,
    add_comment,
    list_comments,
    update_comment,
    delete_comment,
    get_board_items,
    get_overdue_items,
    get_my_items,
    get_escalated_items,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.obeya import (
    ObeyaItem,
    ObeyaComment,
    ObeyaBoard,
    ObeyaCategory,
    ObeyaStatus,
    ObeyaPriority,
)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def sample_item_data():
    """Sample item data for tests."""
    return {
        "id": uuid4(),
        "title": "Test Obeya Item",
        "description": "Test description",
        "board": ObeyaBoard.DAILY.value,
        "column": "todo",
        "position": 1,
        "category": ObeyaCategory.ACTION.value,
        "status": ObeyaStatus.NEW.value,
        "priority": ObeyaPriority.HIGH.value,
        "color": "#FF5733",
        "related_entity_type": None,
        "related_entity_id": None,
        "assigned_to_id": None,
        "due_date": datetime.now(timezone.utc) + timedelta(days=7),
        "target_date": None,
        "completed_at": None,
        "blocked_reason": None,
        "resolution": None,
        "decision_outcome": None,
        "decision_rationale": None,
        "kpi_target": "100",
        "kpi_actual": None,
        "kpi_unit": "%",
        "kpi_trend": None,
        "is_escalated": False,
        "escalated_to_id": None,
        "escalated_at": None,
        "escalation_reason": None,
        "days_open": 0,
        "days_overdue": None,
        "attachments": [],
        "links": [],
        "tags": ["test"],
        "meeting_date": None,
        "meeting_type": None,
        "notes": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": None,
        "deleted_by_id": None,
        "created_by_id": uuid4(),
        "updated_by_id": None,
        "owner_id": None,
    }


def create_mock_item(data: dict, **overrides) -> MagicMock:
    """Create a mock ObeyaItem."""
    item = MagicMock(spec=ObeyaItem)
    merged = {**data, **overrides}
    for key, value in merged.items():
        setattr(item, key, value)

    # Handle computed properties
    status = merged.get("status", ObeyaStatus.NEW.value)
    open_statuses = [
        ObeyaStatus.NEW.value,
        ObeyaStatus.IN_PROGRESS.value,
        ObeyaStatus.BLOCKED.value,
        ObeyaStatus.WAITING.value,
    ]
    item.is_open = status in open_statuses

    due = merged.get("due_date")
    if due and status in open_statuses and due < datetime.now(timezone.utc):
        item.is_overdue = True
    else:
        item.is_overdue = False

    return item


# =============================================================================
# Test Item CRUD
# =============================================================================


class TestObeyaItemCRUD:
    """Tests for Obeya item CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_obeya_item(self, mock_db, mock_user, sample_item_data):
        """Test creating an Obeya item."""
        data = ObeyaItemCreate(
            title="New Obeya Item",
            description="Test description",
            board=ObeyaBoard.DAILY,
            category=ObeyaCategory.ACTION,
            priority=ObeyaPriority.HIGH,
            kpi_target="100",
            kpi_unit="%",
        )

        async def mock_refresh(obj):
            for key, value in sample_item_data.items():
                if key not in ("is_overdue", "is_open"):
                    setattr(obj, key, value)
            obj.title = "New Obeya Item"
            # Note: is_open and is_overdue are computed properties, cannot set

        mock_db.refresh = mock_refresh

        result = await create_obeya_item(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_obeya_item(self, mock_db, mock_user, sample_item_data):
        """Test getting an Obeya item by ID."""
        item = create_mock_item(sample_item_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        result = await get_obeya_item(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.title == "Test Obeya Item"

    @pytest.mark.asyncio
    async def test_get_obeya_item_not_found(self, mock_db, mock_user):
        """Test getting non-existent Obeya item."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_obeya_item(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_obeya_items(self, mock_db, mock_user, sample_item_data):
        """Test listing Obeya items."""
        items = [create_mock_item(sample_item_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = items
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_obeya_items(
            mock_db,
            mock_user,
            board=None,
            category=None,
            status=None,
            priority=None,
            assigned_to_id=None,
            search=None,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_list_obeya_items_with_filters(self, mock_db, mock_user, sample_item_data):
        """Test listing Obeya items with filters."""
        items = [create_mock_item(sample_item_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = items
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_obeya_items(
            mock_db,
            mock_user,
            board=ObeyaBoard.DAILY,
            category=ObeyaCategory.ACTION,
            status=ObeyaStatus.NEW,
            priority=ObeyaPriority.HIGH,
            assigned_to_id=None,
            search="test",
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_update_obeya_item(self, mock_db, mock_user, sample_item_data):
        """Test updating an Obeya item."""
        item = create_mock_item(sample_item_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Item"

        mock_db.refresh = mock_refresh

        data = ObeyaItemUpdate(title="Updated Item")
        result = await update_obeya_item(sample_item_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_update_obeya_item_not_found(self, mock_db, mock_user):
        """Test updating non-existent Obeya item."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = ObeyaItemUpdate(title="Updated")
        with pytest.raises(NotFoundError):
            await update_obeya_item(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_delete_obeya_item(self, mock_db, mock_user, sample_item_data):
        """Test deleting an Obeya item."""
        item = create_mock_item(sample_item_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        result = await delete_obeya_item(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "deleted" in result.message.lower()
        mock_db.flush.assert_called_once()


# =============================================================================
# Test Item Workflow
# =============================================================================


class TestObeyaItemWorkflow:
    """Tests for Obeya item workflow operations."""

    @pytest.mark.asyncio
    async def test_start_item(self, mock_db, mock_user, sample_item_data):
        """Test starting an item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.NEW.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await start_item(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "started" in result.message.lower()

    @pytest.mark.asyncio
    async def test_start_item_already_in_progress(self, mock_db, mock_user, sample_item_data):
        """Test starting an item that's already in progress."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.COMPLETED.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await start_item(sample_item_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_block_item(self, mock_db, mock_user, sample_item_data):
        """Test blocking an item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await block_item(
            sample_item_data["id"],
            mock_db,
            mock_user,
            blocked_reason="Waiting for approval",
        )

        assert result.success is True
        assert "blocked" in result.message.lower()

    @pytest.mark.asyncio
    async def test_block_completed_item(self, mock_db, mock_user, sample_item_data):
        """Test blocking a completed item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.COMPLETED.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await block_item(sample_item_data["id"], mock_db, mock_user, blocked_reason=None)

    @pytest.mark.asyncio
    async def test_unblock_item(self, mock_db, mock_user, sample_item_data):
        """Test unblocking an item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.BLOCKED.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await unblock_item(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "unblocked" in result.message.lower()

    @pytest.mark.asyncio
    async def test_unblock_not_blocked_item(self, mock_db, mock_user, sample_item_data):
        """Test unblocking an item that's not blocked."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await unblock_item(sample_item_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_set_waiting(self, mock_db, mock_user, sample_item_data):
        """Test setting item to waiting."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await set_waiting(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "waiting" in result.message.lower()

    @pytest.mark.asyncio
    async def test_complete_item(self, mock_db, mock_user, sample_item_data):
        """Test completing an item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await complete_item(
            sample_item_data["id"],
            mock_db,
            mock_user,
            resolution="Task completed successfully",
        )

        assert result.success is True
        assert "completed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_complete_already_completed(self, mock_db, mock_user, sample_item_data):
        """Test completing an already completed item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.COMPLETED.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await complete_item(sample_item_data["id"], mock_db, mock_user, resolution=None)

    @pytest.mark.asyncio
    async def test_cancel_item(self, mock_db, mock_user, sample_item_data):
        """Test cancelling an item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await cancel_item(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "cancelled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_escalate_item(self, mock_db, mock_user, sample_item_data):
        """Test escalating an item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        manager_id = uuid4()
        data = EscalationData(
            escalated_to_id=manager_id,
            escalation_reason="Needs management review",
        )
        result = await escalate_item(sample_item_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "escalated" in result.message.lower()

    @pytest.mark.asyncio
    async def test_escalate_completed_item(self, mock_db, mock_user, sample_item_data):
        """Test escalating a completed item."""
        item = create_mock_item(sample_item_data, status=ObeyaStatus.COMPLETED.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        data = EscalationData(escalated_to_id=uuid4())
        with pytest.raises(ConflictError):
            await escalate_item(sample_item_data["id"], data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_deescalate_item(self, mock_db, mock_user, sample_item_data):
        """Test de-escalating an item."""
        item = create_mock_item(sample_item_data, is_escalated=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await deescalate_item(sample_item_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "de-escalated" in result.message.lower()

    @pytest.mark.asyncio
    async def test_deescalate_not_escalated(self, mock_db, mock_user, sample_item_data):
        """Test de-escalating a non-escalated item."""
        item = create_mock_item(sample_item_data, is_escalated=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await deescalate_item(sample_item_data["id"], mock_db, mock_user)


# =============================================================================
# Test Comments
# =============================================================================


class TestObeyaComments:
    """Tests for Obeya comment operations."""

    @pytest.fixture
    def sample_comment_data(self, sample_item_data):
        """Sample comment data."""
        return {
            "id": uuid4(),
            "item_id": sample_item_data["id"],
            "author_id": uuid4(),
            "content": "Test comment",
            "parent_id": None,
            "is_status_change": False,
            "old_status": None,
            "new_status": None,
            "is_pinned": False,
            "is_edited": False,
            "edited_at": None,
            "mentions": [],
            "attachments": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def create_mock_comment(self, data: dict, **overrides) -> MagicMock:
        """Create a mock comment."""
        comment = MagicMock(spec=ObeyaComment)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(comment, key, value)
        return comment

    @pytest.mark.asyncio
    async def test_add_comment(self, mock_db, mock_user, sample_item_data, sample_comment_data):
        """Test adding a comment."""
        item = create_mock_item(sample_item_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            for key, value in sample_comment_data.items():
                setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = CommentCreate(content="Test comment")
        result = await add_comment(sample_item_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_comment_item_not_found(self, mock_db, mock_user):
        """Test adding comment to non-existent item."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = CommentCreate(content="Test comment")
        with pytest.raises(NotFoundError):
            await add_comment(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_comments(self, mock_db, mock_user, sample_item_data, sample_comment_data):
        """Test listing comments."""
        item = create_mock_item(sample_item_data)
        comments = [self.create_mock_comment(sample_comment_data)]

        mock_item_result = MagicMock()
        mock_item_result.scalar_one_or_none.return_value = item
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = comments
        mock_db.execute.side_effect = [mock_item_result, mock_count_result, mock_data_result]

        result = await list_comments(
            sample_item_data["id"],
            mock_db,
            mock_user,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_update_comment(self, mock_db, mock_user, sample_item_data, sample_comment_data):
        """Test updating a comment."""
        comment = self.create_mock_comment(sample_comment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = comment
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.content = "Updated content"
            obj.is_edited = True

        mock_db.refresh = mock_refresh

        data = CommentUpdate(content="Updated content")
        result = await update_comment(
            sample_item_data["id"],
            sample_comment_data["id"],
            data,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_update_comment_not_found(self, mock_db, mock_user, sample_item_data):
        """Test updating non-existent comment."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = CommentUpdate(content="Updated")
        with pytest.raises(NotFoundError):
            await update_comment(sample_item_data["id"], uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_delete_comment(self, mock_db, mock_user, sample_item_data, sample_comment_data):
        """Test deleting a comment."""
        comment = self.create_mock_comment(sample_comment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = comment
        mock_db.execute.return_value = mock_result

        result = await delete_comment(
            sample_item_data["id"],
            sample_comment_data["id"],
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "deleted" in result.message.lower()
        mock_db.delete.assert_called_once()


# =============================================================================
# Test Queries
# =============================================================================


class TestObeyaQueries:
    """Tests for Obeya query endpoints."""

    @pytest.mark.asyncio
    async def test_get_board_items(self, mock_db, mock_user, sample_item_data):
        """Test getting items by board."""
        items = [create_mock_item(sample_item_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = items
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_board_items(
            ObeyaBoard.DAILY,
            mock_db,
            mock_user,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_overdue_items(self, mock_db, mock_user, sample_item_data):
        """Test getting overdue items."""
        items = [create_mock_item(sample_item_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = items
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_overdue_items(mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_my_items(self, mock_db, mock_user, sample_item_data):
        """Test getting items assigned to current user."""
        items = [create_mock_item(sample_item_data, assigned_to_id=mock_user.id)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = items
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_my_items(mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_escalated_items(self, mock_db, mock_user, sample_item_data):
        """Test getting escalated items."""
        items = [create_mock_item(sample_item_data, is_escalated=True)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = items
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_escalated_items(mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert result.pagination.total_items == 1

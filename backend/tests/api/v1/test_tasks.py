"""Tests for Task API endpoints.

Full test coverage for task management operations:
- Task CRUD operations
- Task workflow (start, block, unblock, review, complete, cancel, reopen)
- Checklist management
- Time tracking
- Comment operations
- Query endpoints
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.tasks import (
    TaskCreate,
    TaskUpdate,
    ChecklistItem,
    TimeEntry,
    CommentCreate,
    CommentUpdate,
    create_task,
    get_task,
    list_tasks,
    update_task,
    delete_task,
    start_task,
    block_task,
    unblock_task,
    submit_for_review,
    complete_task,
    cancel_task,
    reopen_task,
    update_checklist,
    toggle_checklist_item,
    log_time,
    add_comment,
    list_comments,
    update_comment,
    delete_comment,
    get_my_tasks,
    get_overdue_tasks,
    get_tasks_created_by_me,
    get_blocked_tasks,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.task import (
    Task,
    TaskComment,
    TaskStatus,
    TaskPriority,
    TaskType,
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
    # AsyncSession.add() is sync; keep it sync to avoid un-awaited coroutine warnings.
    db.add = MagicMock()
    return db


@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "id": uuid4(),
        "title": "Test Task",
        "description": "Test description",
        "task_type": TaskType.ACTION.value,
        "status": TaskStatus.TODO.value,
        "priority": TaskPriority.HIGH.value,
        "related_entity_type": None,
        "related_entity_id": None,
        "assignee_id": None,
        "created_by_id": uuid4(),
        "due_date": datetime.now(timezone.utc) + timedelta(days=7),
        "start_date": None,
        "completed_at": None,
        "estimated_hours": 8.0,
        "actual_hours": None,
        "progress_percentage": 0,
        "blocked_reason": None,
        "blocked_by_task_id": None,
        "is_recurring": False,
        "recurrence_pattern": None,
        "parent_task_id": None,
        "reminder_date": None,
        "reminder_sent": False,
        "checklist": [
            {"id": "1", "text": "Item 1", "checked": False},
            {"id": "2", "text": "Item 2", "checked": True},
        ],
        "attachments": [],
        "tags": ["test"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": None,
        "deleted_by_id": None,
        "updated_by_id": None,
    }


def create_mock_task(data: dict, **overrides) -> MagicMock:
    """Create a mock Task."""
    task = MagicMock(spec=Task)
    merged = {**data, **overrides}
    for key, value in merged.items():
        setattr(task, key, value)

    # Handle computed properties
    status = merged.get("status", TaskStatus.TODO.value)
    open_statuses = [
        TaskStatus.TODO.value,
        TaskStatus.IN_PROGRESS.value,
        TaskStatus.BLOCKED.value,
        TaskStatus.IN_REVIEW.value,
    ]
    task.is_open = status in open_statuses

    due = merged.get("due_date")
    if due and status in open_statuses and due < datetime.now(timezone.utc):
        task.is_overdue = True
    else:
        task.is_overdue = False

    return task


# =============================================================================
# Test Task CRUD
# =============================================================================


class TestTaskCRUD:
    """Tests for Task CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_task(self, mock_db, mock_user, sample_task_data):
        """Test creating a task."""
        data = TaskCreate(
            title="New Task",
            description="Test description",
            task_type=TaskType.ACTION,
            priority=TaskPriority.HIGH,
            estimated_hours=8.0,
        )

        async def mock_refresh(obj):
            for key, value in sample_task_data.items():
                if key not in ("is_overdue", "is_open"):
                    setattr(obj, key, value)
            obj.title = "New Task"

        mock_db.refresh = mock_refresh

        result = await create_task(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task(self, mock_db, mock_user, sample_task_data):
        """Test getting a task by ID."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        result = await get_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.title == "Test Task"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, mock_db, mock_user):
        """Test getting non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_task(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_tasks(self, mock_db, mock_user, sample_task_data):
        """Test listing tasks."""
        tasks = [create_mock_task(sample_task_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = tasks
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_tasks(
            mock_db,
            mock_user,
            status=None,
            priority=None,
            task_type=None,
            assignee_id=None,
            related_entity_type=None,
            related_entity_id=None,
            search=None,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, mock_db, mock_user, sample_task_data):
        """Test listing tasks with filters."""
        tasks = [create_mock_task(sample_task_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = tasks
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_tasks(
            mock_db,
            mock_user,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            task_type=TaskType.ACTION,
            assignee_id=None,
            related_entity_type=None,
            related_entity_id=None,
            search="test",
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_update_task(self, mock_db, mock_user, sample_task_data):
        """Test updating a task."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Task"

        mock_db.refresh = mock_refresh

        data = TaskUpdate(title="Updated Task")
        result = await update_task(sample_task_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, mock_db, mock_user):
        """Test updating non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = TaskUpdate(title="Updated")
        with pytest.raises(NotFoundError):
            await update_task(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_delete_task(self, mock_db, mock_user, sample_task_data):
        """Test deleting a task."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        result = await delete_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "deleted" in result.message.lower()
        mock_db.flush.assert_called_once()


# =============================================================================
# Test Task Workflow
# =============================================================================


class TestTaskWorkflow:
    """Tests for Task workflow operations."""

    @pytest.mark.asyncio
    async def test_start_task(self, mock_db, mock_user, sample_task_data):
        """Test starting a task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.TODO.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await start_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "started" in result.message.lower()

    @pytest.mark.asyncio
    async def test_start_task_invalid_status(self, mock_db, mock_user, sample_task_data):
        """Test starting a task not in todo status."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await start_task(sample_task_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_block_task(self, mock_db, mock_user, sample_task_data):
        """Test blocking a task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await block_task(
            sample_task_data["id"],
            mock_db,
            mock_user,
            reason="Waiting for input",
            blocked_by_task_id=None,
        )

        assert result.success is True
        assert "blocked" in result.message.lower()

    @pytest.mark.asyncio
    async def test_block_completed_task(self, mock_db, mock_user, sample_task_data):
        """Test blocking a completed task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.DONE.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await block_task(
                sample_task_data["id"],
                mock_db,
                mock_user,
                reason=None,
                blocked_by_task_id=None,
            )

    @pytest.mark.asyncio
    async def test_unblock_task(self, mock_db, mock_user, sample_task_data):
        """Test unblocking a task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.BLOCKED.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await unblock_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "unblocked" in result.message.lower()

    @pytest.mark.asyncio
    async def test_unblock_not_blocked_task(self, mock_db, mock_user, sample_task_data):
        """Test unblocking a non-blocked task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await unblock_task(sample_task_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_submit_for_review(self, mock_db, mock_user, sample_task_data):
        """Test submitting task for review."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await submit_for_review(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "review" in result.message.lower()

    @pytest.mark.asyncio
    async def test_submit_for_review_invalid_status(self, mock_db, mock_user, sample_task_data):
        """Test submitting task not in progress."""
        task = create_mock_task(sample_task_data, status=TaskStatus.TODO.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await submit_for_review(sample_task_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_complete_task(self, mock_db, mock_user, sample_task_data):
        """Test completing a task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await complete_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "completed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_complete_already_completed(self, mock_db, mock_user, sample_task_data):
        """Test completing an already completed task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.DONE.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await complete_task(sample_task_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_cancel_task(self, mock_db, mock_user, sample_task_data):
        """Test cancelling a task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await cancel_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "cancelled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reopen_task(self, mock_db, mock_user, sample_task_data):
        """Test reopening a completed task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.DONE.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await reopen_task(sample_task_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "reopened" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reopen_open_task(self, mock_db, mock_user, sample_task_data):
        """Test reopening an already open task."""
        task = create_mock_task(sample_task_data, status=TaskStatus.IN_PROGRESS.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await reopen_task(sample_task_data["id"], mock_db, mock_user)


# =============================================================================
# Test Checklist
# =============================================================================


class TestChecklist:
    """Tests for checklist operations."""

    @pytest.mark.asyncio
    async def test_update_checklist(self, mock_db, mock_user, sample_task_data):
        """Test updating checklist."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        checklist = [
            ChecklistItem(id="1", text="New Item 1", checked=False),
            ChecklistItem(id="2", text="New Item 2", checked=True),
        ]
        result = await update_checklist(
            sample_task_data["id"],
            checklist,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_toggle_checklist_item(self, mock_db, mock_user, sample_task_data):
        """Test toggling a checklist item."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await toggle_checklist_item(
            sample_task_data["id"],
            "1",
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "toggled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_toggle_checklist_item_not_found(self, mock_db, mock_user, sample_task_data):
        """Test toggling non-existent checklist item."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await toggle_checklist_item(
                sample_task_data["id"],
                "999",
                mock_db,
                mock_user,
            )


# =============================================================================
# Test Time Tracking
# =============================================================================


class TestTimeTracking:
    """Tests for time tracking."""

    @pytest.mark.asyncio
    async def test_log_time(self, mock_db, mock_user, sample_task_data):
        """Test logging time."""
        task = create_mock_task(sample_task_data, actual_hours=0.0)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        entry = TimeEntry(hours=2.5, notes="Development work")
        result = await log_time(sample_task_data["id"], entry, mock_db, mock_user)

        assert result.success is True
        assert "2.5" in result.message


# =============================================================================
# Test Comments
# =============================================================================


class TestTaskComments:
    """Tests for task comment operations."""

    @pytest.fixture
    def sample_comment_data(self, sample_task_data):
        """Sample comment data."""
        return {
            "id": uuid4(),
            "task_id": sample_task_data["id"],
            "author_id": uuid4(),
            "content": "Test comment",
            "is_status_change": False,
            "old_status": None,
            "new_status": None,
            "is_edited": False,
            "edited_at": None,
            "mentions": [],
            "attachments": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def create_mock_comment(self, data: dict, **overrides) -> MagicMock:
        """Create a mock comment."""
        comment = MagicMock(spec=TaskComment)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(comment, key, value)
        return comment

    @pytest.mark.asyncio
    async def test_add_comment(self, mock_db, mock_user, sample_task_data, sample_comment_data):
        """Test adding a comment."""
        task = create_mock_task(sample_task_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            for key, value in sample_comment_data.items():
                setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = CommentCreate(content="Test comment")
        result = await add_comment(sample_task_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_comment_task_not_found(self, mock_db, mock_user):
        """Test adding comment to non-existent task."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = CommentCreate(content="Test comment")
        with pytest.raises(NotFoundError):
            await add_comment(uuid4(), data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_comments(self, mock_db, mock_user, sample_task_data, sample_comment_data):
        """Test listing comments."""
        task = create_mock_task(sample_task_data)
        comments = [self.create_mock_comment(sample_comment_data)]

        mock_task_result = MagicMock()
        mock_task_result.scalar_one_or_none.return_value = task
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = comments
        mock_db.execute.side_effect = [mock_task_result, mock_count_result, mock_data_result]

        result = await list_comments(
            sample_task_data["id"],
            mock_db,
            mock_user,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_update_comment(self, mock_db, mock_user, sample_task_data, sample_comment_data):
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
            sample_task_data["id"],
            sample_comment_data["id"],
            data,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_delete_comment(self, mock_db, mock_user, sample_task_data, sample_comment_data):
        """Test deleting a comment."""
        comment = self.create_mock_comment(sample_comment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = comment
        mock_db.execute.return_value = mock_result

        result = await delete_comment(
            sample_task_data["id"],
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


class TestTaskQueries:
    """Tests for task query endpoints."""

    @pytest.mark.asyncio
    async def test_get_my_tasks(self, mock_db, mock_user, sample_task_data):
        """Test getting tasks assigned to current user."""
        tasks = [create_mock_task(sample_task_data, assignee_id=mock_user.id)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = tasks
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_my_tasks(
            mock_db,
            mock_user,
            include_completed=False,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_overdue_tasks(self, mock_db, mock_user, sample_task_data):
        """Test getting overdue tasks."""
        tasks = [create_mock_task(sample_task_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = tasks
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_overdue_tasks(mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_tasks_created_by_me(self, mock_db, mock_user, sample_task_data):
        """Test getting tasks created by current user."""
        tasks = [create_mock_task(sample_task_data, created_by_id=mock_user.id)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = tasks
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_tasks_created_by_me(mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_blocked_tasks(self, mock_db, mock_user, sample_task_data):
        """Test getting blocked tasks."""
        tasks = [create_mock_task(sample_task_data, status=TaskStatus.BLOCKED.value)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = tasks
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_blocked_tasks(mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert result.pagination.total_items == 1

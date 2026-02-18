"""Task Management API endpoints.

Provides comprehensive API for managing tasks and action items:
- Task CRUD operations
- Task workflow (start, block, unblock, review, complete, cancel)
- Task comments
- Checklist management
- Time tracking
- Query endpoints (my tasks, overdue, by assignee)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select

from sensei.api.deps import CurrentUser, DBSession, RoleChecker
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.utils import (
    APIResponse,
    PaginatedResponse,
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_response,
    build_updated_response,
    escape_like_pattern,
)
from sensei.models.task import (
    Task,
    TaskComment,
    TaskStatus,
    TaskPriority,
    TaskType,
)


router = APIRouter(
    dependencies=[Depends(RoleChecker(["admin", "ceo", "gm", "exec", "ops", "quality", "engineering", "supervisor", "team_lead", "operator"]))],
)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ChecklistItem(BaseModel):
    """Schema for a checklist item."""

    id: str
    text: str
    checked: bool = False


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: TaskType = Field(default=TaskType.ACTION)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    checklist: Optional[list[ChecklistItem]] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    reminder_date: Optional[datetime] = None
    tags: Optional[list] = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    progress_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    reminder_date: Optional[datetime] = None
    tags: Optional[list] = None


class TaskBulkUpdate(BaseModel):
    """Schema for bulk updating tasks."""

    ids: list[UUID]
    updates: TaskUpdate


class TaskMove(BaseModel):
    """Schema for moving a task."""

    column: str
    position: int


class TaskBulkDelete(BaseModel):
    """Schema for bulk deleting tasks."""

    ids: list[UUID]


class TaskResponse(BaseModel):
    """Schema for task response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str] = None
    task_type: str
    status: str
    priority: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    created_by_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    progress_percentage: int
    blocked_reason: Optional[str] = None
    blocked_by_task_id: Optional[UUID] = None
    is_recurring: bool
    recurrence_pattern: Optional[str] = None
    parent_task_id: Optional[UUID] = None
    reminder_date: Optional[datetime] = None
    reminder_sent: bool
    checklist: Optional[list] = None
    attachments: Optional[list] = None
    tags: Optional[list] = None
    is_overdue: bool
    is_open: bool
    created_at: datetime
    updated_at: datetime


class TimeEntry(BaseModel):
    """Schema for logging time."""

    hours: float = Field(..., gt=0)
    notes: Optional[str] = None


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    content: str = Field(..., min_length=1)
    mentions: Optional[list] = None
    attachments: Optional[list] = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    content: Optional[str] = Field(default=None, min_length=1)


class CommentResponse(BaseModel):
    """Schema for comment response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    author_id: Optional[UUID] = None
    content: str
    is_status_change: bool
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    is_edited: bool
    edited_at: Optional[datetime] = None
    mentions: Optional[list] = None
    attachments: Optional[list] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Task CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=APIResponse[TaskResponse],
    status_code=201,
    summary="Create task",
    description="Create a new task.",
)
async def create_task(
    data: TaskCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    task = Task(
        title=data.title,
        description=data.description,
        task_type=(
            data.task_type.value
            if isinstance(data.task_type, TaskType)
            else data.task_type
        ),
        status=TaskStatus.TODO.value,
        priority=(
            data.priority.value
            if isinstance(data.priority, TaskPriority)
            else data.priority
        ),
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
        assignee_id=data.assignee_id,
        created_by_id=current_user.id,
        due_date=data.due_date,
        start_date=data.start_date,
        estimated_hours=data.estimated_hours,
        checklist=[c.model_dump() for c in data.checklist] if data.checklist else None,
        is_recurring=data.is_recurring,
        recurrence_pattern=data.recurrence_pattern,
        reminder_date=data.reminder_date,
        tags=data.tags or [],
    )

    db.add(task)
    await db.flush()
    await db.refresh(task)

    return build_created_response(
        data=TaskResponse.model_validate(task),
        resource_name="Task",
    )


@router.get(
    "/{task_id}",
    response_model=APIResponse[TaskResponse],
    summary="Get task",
    description="Get a task by ID.",
)
async def get_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task retrieved successfully",
    )


@router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    summary="List tasks",
    description="List tasks with filtering and pagination.",
)
async def list_tasks(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[TaskStatus] = Query(default=None),
    priority: Optional[TaskPriority] = Query(default=None),
    task_type: Optional[TaskType] = Query(default=None),
    assignee_id: Optional[UUID] = Query(default=None),
    related_entity_type: Optional[str] = Query(default=None),
    related_entity_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:
    base_conditions: list[Any] = [Task.deleted_at.is_(None)]

    if status and isinstance(status, TaskStatus):
        base_conditions.append(Task.status == status.value)
    if priority and isinstance(priority, TaskPriority):
        base_conditions.append(Task.priority == priority.value)
    if task_type and isinstance(task_type, TaskType):
        base_conditions.append(Task.task_type == task_type.value)
    if assignee_id:
        base_conditions.append(Task.assignee_id == assignee_id)
    if related_entity_type:
        base_conditions.append(Task.related_entity_type == related_entity_type)
    if related_entity_id:
        base_conditions.append(Task.related_entity_id == related_entity_id)
    if search:
        escaped_search = escape_like_pattern(search)
        search_filter = or_(
            Task.title.ilike(f"%{escaped_search}%"),
            Task.description.ilike(f"%{escaped_search}%"),
        )
        base_conditions.append(search_filter)

    count_stmt = select(func.count(Task.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Task)
        .where(and_(*base_conditions))
        .order_by(Task.priority.desc(), Task.due_date.asc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    tasks = data_result.scalars().all()

    task_list = [TaskResponse.model_validate(t) for t in tasks]

    return build_paginated_response(
        data=task_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{task_id}",
    response_model=APIResponse[TaskResponse],
    summary="Update task",
    description="Update a task's details.",
)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    if "task_type" in update_data and update_data["task_type"]:
        if isinstance(update_data["task_type"], TaskType):
            update_data["task_type"] = update_data["task_type"].value
    if "priority" in update_data and update_data["priority"]:
        if isinstance(update_data["priority"], TaskPriority):
            update_data["priority"] = update_data["priority"].value

    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_updated_response(
        data=TaskResponse.model_validate(task),
        resource_name="Task",
    )


@router.delete(
    "/{task_id}",
    response_model=APIResponse,
    summary="Delete task",
    description="Soft delete a task.",
)
async def delete_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    task.deleted_at = datetime.now(timezone.utc)
    task.deleted_by_id = current_user.id
    await db.flush()

    return build_deleted_response(resource_name="Task")


# =============================================================================
# Task Workflow Endpoints
# =============================================================================


@router.post(
    "/{task_id}/start",
    response_model=APIResponse[TaskResponse],
    summary="Start task",
    description="Move task to in progress status.",
)
async def start_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status != TaskStatus.TODO.value:
        raise ConflictError("Task must be in 'todo' status to start")

    task.status = TaskStatus.IN_PROGRESS.value
    if not task.start_date:
        task.start_date = datetime.now(timezone.utc)
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task started",
    )


@router.post(
    "/{task_id}/block",
    response_model=APIResponse[TaskResponse],
    summary="Block task",
    description="Mark task as blocked.",
)
async def block_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    reason: Optional[str] = Query(default=None),
    blocked_by_task_id: Optional[UUID] = Query(default=None),
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]:
        raise ConflictError("Cannot block completed or cancelled task")

    task.status = TaskStatus.BLOCKED.value
    task.blocked_reason = reason
    task.blocked_by_task_id = blocked_by_task_id
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task blocked",
    )


@router.post(
    "/{task_id}/unblock",
    response_model=APIResponse[TaskResponse],
    summary="Unblock task",
    description="Remove blocked status from task.",
)
async def unblock_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status != TaskStatus.BLOCKED.value:
        raise ConflictError("Task is not blocked")

    task.status = TaskStatus.IN_PROGRESS.value
    task.blocked_reason = None
    task.blocked_by_task_id = None
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task unblocked",
    )


@router.post(
    "/{task_id}/review",
    response_model=APIResponse[TaskResponse],
    summary="Submit for review",
    description="Submit task for review.",
)
async def submit_for_review(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status != TaskStatus.IN_PROGRESS.value:
        raise ConflictError("Task must be in progress to submit for review")

    task.status = TaskStatus.IN_REVIEW.value
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task submitted for review",
    )


@router.post(
    "/{task_id}/complete",
    response_model=APIResponse[TaskResponse],
    summary="Complete task",
    description="Mark task as completed.",
)
async def complete_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status == TaskStatus.DONE.value:
        raise ConflictError("Task is already completed")

    task.status = TaskStatus.DONE.value
    task.completed_at = datetime.now(timezone.utc)
    task.progress_percentage = 100
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task completed",
    )


@router.post(
    "/{task_id}/cancel",
    response_model=APIResponse[TaskResponse],
    summary="Cancel task",
    description="Cancel a task.",
)
async def cancel_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status == TaskStatus.CANCELLED.value:
        raise ConflictError("Task is already cancelled")

    task.status = TaskStatus.CANCELLED.value
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task cancelled",
    )


@router.post(
    "/{task_id}/reopen",
    response_model=APIResponse[TaskResponse],
    summary="Reopen task",
    description="Reopen a completed or cancelled task.",
)
async def reopen_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if task.status not in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]:
        raise ConflictError("Only completed or cancelled tasks can be reopened")

    task.status = TaskStatus.TODO.value
    task.completed_at = None
    task.progress_percentage = 0
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task reopened",
    )


# =============================================================================
# Checklist Endpoints
# =============================================================================


@router.put(
    "/{task_id}/checklist",
    response_model=APIResponse[TaskResponse],
    summary="Update checklist",
    description="Update task checklist.",
)
async def update_checklist(
    task_id: UUID,
    checklist: list[ChecklistItem],
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    task.checklist = [item.model_dump() for item in checklist]
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_updated_response(
        data=TaskResponse.model_validate(task),
        resource_name="Checklist",
    )


@router.patch(
    "/{task_id}/checklist/{item_id}",
    response_model=APIResponse[TaskResponse],
    summary="Toggle checklist item",
    description="Toggle checked status of a checklist item.",
)
async def toggle_checklist_item(
    task_id: UUID,
    item_id: str,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    if not task.checklist:
        raise NotFoundError(f"Checklist item {item_id} not found")

    item_found = False
    updated_checklist = []
    for item in task.checklist:
        if item.get("id") == item_id:
            item["checked"] = not item.get("checked", False)
            item_found = True
        updated_checklist.append(item)

    if not item_found:
        raise NotFoundError(f"Checklist item {item_id} not found")

    task.checklist = updated_checklist
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Checklist item toggled",
    )


# =============================================================================
# Time Tracking Endpoints
# =============================================================================


@router.post(
    "/{task_id}/log-time",
    response_model=APIResponse[TaskResponse],
    summary="Log time",
    description="Log time spent on task.",
)
async def log_time(
    task_id: UUID,
    entry: TimeEntry,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    current_hours = task.actual_hours or 0.0
    task.actual_hours = current_hours + entry.hours
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message=f"Logged {entry.hours} hours",
    )


# =============================================================================
# Comment Endpoints
# =============================================================================


@router.post(
    "/{task_id}/comments",
    response_model=APIResponse[CommentResponse],
    status_code=201,
    summary="Add comment",
    description="Add a comment to a task.",
)
async def add_comment(
    task_id: UUID,
    data: CommentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CommentResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    comment = TaskComment(
        task_id=task_id,
        author_id=current_user.id,
        content=data.content,
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
    "/{task_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
    summary="List comments",
    description="List comments on a task.",
)
async def list_comments(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CommentResponse]:
    task_stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    task_result = await db.execute(task_stmt)
    task = task_result.scalar_one_or_none()
    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    base_conditions: list[Any] = [TaskComment.task_id == task_id]

    count_stmt = select(func.count(TaskComment.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(TaskComment)
        .where(and_(*base_conditions))
        .order_by(TaskComment.created_at.asc())
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
    "/{task_id}/comments/{comment_id}",
    response_model=APIResponse[CommentResponse],
    summary="Update comment",
    description="Update a comment.",
)
async def update_comment(
    task_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CommentResponse]:
    stmt = select(TaskComment).where(
        and_(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
        )
    )
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()

    if not comment:
        raise NotFoundError(f"Comment {comment_id} not found")

    if data.content:
        comment.content = data.content
        comment.is_edited = True
        comment.edited_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(comment)

    return build_updated_response(
        data=CommentResponse.model_validate(comment),
        resource_name="Comment",
    )


@router.delete(
    "/{task_id}/comments/{comment_id}",
    response_model=APIResponse,
    summary="Delete comment",
    description="Delete a comment.",
)
async def delete_comment(
    task_id: UUID,
    comment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(TaskComment).where(
        and_(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
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
    "/my-tasks",
    response_model=PaginatedResponse[TaskResponse],
    summary="Get my tasks",
    description="Get tasks assigned to the current user.",
)
async def get_my_tasks(
    db: DBSession,
    current_user: CurrentUser,
    include_completed: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:
    base_conditions: list[Any] = [
        Task.deleted_at.is_(None),
        Task.assignee_id == current_user.id,
    ]

    if not include_completed:
        base_conditions.append(
            Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])
        )

    count_stmt = select(func.count(Task.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Task)
        .where(and_(*base_conditions))
        .order_by(Task.priority.desc(), Task.due_date.asc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    tasks = data_result.scalars().all()

    task_list = [TaskResponse.model_validate(t) for t in tasks]

    return build_paginated_response(
        data=task_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/overdue",
    response_model=PaginatedResponse[TaskResponse],
    summary="Get overdue tasks",
    description="Get all overdue tasks.",
)
async def get_overdue_tasks(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:
    now = datetime.now(timezone.utc)
    base_conditions: list[Any] = [
        Task.deleted_at.is_(None),
        Task.due_date < now,
        Task.status.notin_([TaskStatus.DONE.value, TaskStatus.CANCELLED.value]),
    ]

    count_stmt = select(func.count(Task.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Task)
        .where(and_(*base_conditions))
        .order_by(Task.due_date.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    tasks = data_result.scalars().all()

    task_list = [TaskResponse.model_validate(t) for t in tasks]

    return build_paginated_response(
        data=task_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/created-by-me",
    response_model=PaginatedResponse[TaskResponse],
    summary="Get tasks created by me",
    description="Get tasks created by the current user.",
)
async def get_tasks_created_by_me(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:
    base_conditions: list[Any] = [
        Task.deleted_at.is_(None),
        Task.created_by_id == current_user.id,
    ]

    count_stmt = select(func.count(Task.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Task)
        .where(and_(*base_conditions))
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    tasks = data_result.scalars().all()

    task_list = [TaskResponse.model_validate(t) for t in tasks]

    return build_paginated_response(
        data=task_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/blocked",
    response_model=PaginatedResponse[TaskResponse],
    summary="Get blocked tasks",
    description="Get all blocked tasks.",
)
async def get_blocked_tasks(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:
    base_conditions: list[Any] = [
        Task.deleted_at.is_(None),
        Task.status == TaskStatus.BLOCKED.value,
    ]

    count_stmt = select(func.count(Task.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Task)
        .where(and_(*base_conditions))
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    tasks = data_result.scalars().all()

    task_list = [TaskResponse.model_validate(t) for t in tasks]

    return build_paginated_response(
        data=task_list,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{task_id}/duplicate",
    response_model=APIResponse[TaskResponse],
    summary="Duplicate task",
    description="Create a copy of an existing task.",
)
async def duplicate_task(
    task_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    original = result.scalar_one_or_none()

    if not original:
        raise NotFoundError(f"Task {task_id} not found")

    new_task = Task(
        title=f"Copy of {original.title}",
        description=original.description,
        task_type=original.task_type,
        status=TaskStatus.OPEN.value,
        priority=original.priority,
        related_entity_type=original.related_entity_type,
        related_entity_id=original.related_entity_id,
        assignee_id=original.assignee_id,
        due_date=original.due_date,
        start_date=original.start_date,
        estimated_hours=original.estimated_hours,
        checklist=original.checklist,
        tags=original.tags,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    db.add(new_task)
    await db.flush()
    await db.refresh(new_task)

    return build_created_response(
        data=TaskResponse.model_validate(new_task),
        resource_name="Task",
    )


@router.post(
    "/{task_id}/move",
    response_model=APIResponse[TaskResponse],
    summary="Move task",
    description="Move task to a different column/position.",
)
async def move_task(
    task_id: UUID,
    data: TaskMove,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TaskResponse]:
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError(f"Task {task_id} not found")

    # In a real implementation, we would update positions of other tasks too.
    # For now, just update the column and position.
    task.status = data.column  # In Kanban boards, status usually represents the column
    task.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(task)

    return build_response(
        data=TaskResponse.model_validate(task),
        message="Task moved",
    )


@router.patch(
    "/bulk",
    response_model=APIResponse[list[TaskResponse]],
    summary="Bulk update tasks",
    description="Update multiple tasks at once.",
)
async def bulk_update_tasks(
    data: TaskBulkUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[TaskResponse]]:
    stmt = select(Task).where(
        and_(Task.id.in_(data.ids), Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    update_data = data.updates.model_dump(exclude_unset=True)
    updated_tasks = []

    for task in tasks:
        for field, value in update_data.items():
            setattr(task, field, value)
        task.updated_by_id = current_user.id
        updated_tasks.append(task)

    await db.flush()
    for task in updated_tasks:
        await db.refresh(task)

    return build_updated_response(
        data=[TaskResponse.model_validate(t) for t in updated_tasks],
        resource_name="Tasks",
    )


@router.delete(
    "/bulk",
    response_model=APIResponse[dict],
    summary="Bulk delete tasks",
    description="Delete multiple tasks at once.",
)
async def bulk_delete_tasks(
    data: TaskBulkDelete,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[dict]:
    stmt = select(Task).where(
        and_(Task.id.in_(data.ids), Task.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    for task in tasks:
        task.deleted_at = datetime.now(timezone.utc)
        task.deleted_by_id = current_user.id

    await db.flush()

    return build_deleted_response(resource_name="Tasks")

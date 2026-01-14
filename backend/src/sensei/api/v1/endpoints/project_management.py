"""Project Management (Taiga-like) Endpoints.

Implements CRUD operations for:
- Projects + membership
- Epics
- Sprints
- User stories
- Subtasks
- Story comments

Designed to integrate with broader Sensei OS modules (RFQs, Work Orders, A3, CTQ).
"""

from __future__ import annotations

from datetime import datetime, date, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, ForbiddenError, NotFoundError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_updated_response,
    slugify,
)
from sensei.models.project_management import (
    Epic,
    EpicStatus,
    Issue,
    IssueComment,
    IssuePriority,
    IssueSeverity,
    IssueStatus,
    IssueType,
    ProjectMilestone,
    MilestoneType,
    Project,
    ProjectActivity,
    ProjectMember,
    ProjectSequence,
    ProjectStatus,
    ProjectType,
    Sprint,
    SprintStatus,
    StoryComment,
    Subtask,
    WikiPage,
    WikiPageType,
    UserStory,
    UserStoryStatus,
)

router = APIRouter()


# =============================================================================
# Small helpers
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def _user_id(user: CurrentUser) -> Optional[UUID]:
    return getattr(user, "id", None)


def _is_superuser(user: CurrentUser) -> bool:
    return bool(getattr(user, "is_superuser", False))


async def _get_project_member(db: DBSession, project_id: UUID, user_id: Optional[UUID]) -> Optional[ProjectMember]:
    if not user_id:
        return None
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _require_project_access(
    db: DBSession,
    project: Project,
    user: CurrentUser,
    *,
    permission: str,
) -> Optional[ProjectMember]:
    """Enforce project privacy + membership permissions.

    permission: read | comment | edit | invite | delete
    Returns the ProjectMember row (if any) for downstream permission checks.
    """

    if _is_superuser(user):
        return None

    uid = _user_id(user)
    if uid and project.owner_id == uid:
        # Owner always allowed.
        return await _get_project_member(db, project.id, uid)

    member = await _get_project_member(db, project.id, uid)

    # Privacy gate
    if project.is_private and member is None:
        raise ForbiddenError("Access denied: project is private")

    # Permission gates for writes
    if permission in {"read"}:
        return member

    if member is None:
        raise ForbiddenError("Access denied: project membership required")

    if permission in {"comment"}:
        if not member.can_comment:
            raise ForbiddenError("Access denied: commenting not permitted")
        return member

    if permission in {"edit"}:
        if not member.can_edit:
            raise ForbiddenError("Access denied: editing not permitted")
        return member

    if permission in {"invite"}:
        if not member.can_invite:
            raise ForbiddenError("Access denied: inviting not permitted")
        return member

    if permission in {"delete"}:
        if not member.can_delete:
            raise ForbiddenError("Access denied: deletion not permitted")
        return member

    raise ForbiddenError("Access denied")


async def _log_activity(
    db: DBSession,
    *,
    project_id: UUID,
    user: CurrentUser,
    activity_type: str,
    entity_type: str,
    entity_id: UUID,
    entity_ref: Optional[int] = None,
    summary: str,
    details: Optional[dict] = None,
) -> None:
    db.add(
        ProjectActivity(
            project_id=project_id,
            user_id=_user_id(user),
            activity_type=activity_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_ref=entity_ref,
            summary=summary[:500],
            details=details,
        )
    )


async def _get_project_or_404(db: DBSession, project_id: UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    return project


async def _get_next_project_ref(db: DBSession, project_id: UUID, entity_type: str) -> int:
    """Get next reference number using project sequences with row-level locking."""
    # Try to get existing sequence
    stmt = select(ProjectSequence).where(
        ProjectSequence.project_id == project_id,
        ProjectSequence.entity_type == entity_type
    ).with_for_update()
    
    result = await db.execute(stmt)
    seq = result.scalar_one_or_none()
    
    if seq is None:
        # Fallback to MAX(ref) + 1 if sequence doesn't exist, then create it
        # This handles existing projects before sequences were added
        model_map = {
            "user_story": UserStory,
            "epic": Epic,
            "issue": Issue
        }
        model_cls = model_map.get(entity_type)
        if not model_cls:
            raise ValueError(f"Invalid entity type for sequence: {entity_type}")
            
        try:
            async with db.begin_nested():
                max_stmt = select(func.max(model_cls.ref)).where(model_cls.project_id == project_id)
                max_ref = (await db.execute(max_stmt)).scalar() or 0
                
                seq = ProjectSequence(
                    project_id=project_id,
                    entity_type=entity_type,
                    last_value=max_ref + 1
                )
                db.add(seq)
                await db.flush()
            return seq.last_value
        except IntegrityError:
            # Handle race condition: someone else created it.
            # Re-fetch with lock.
            result = await db.execute(stmt)
            seq = result.scalar_one()
    
    seq.last_value += 1
    return seq.last_value


async def _next_story_ref(db: DBSession, user_story_id: UUID) -> int:
    """Get next subtask reference number with locking on the parent UserStory."""
    # Lock the parent user story to serialize subtask creation
    await db.execute(
        select(UserStory.id).where(UserStory.id == user_story_id).with_for_update()
    )
    
    result = await db.execute(
        select(func.max(Subtask.ref)).where(Subtask.user_story_id == user_story_id)
    )
    max_ref = result.scalar()
    return int(max_ref or 0) + 1


async def _update_project_stats(db: DBSession, project_id: UUID) -> None:
    """Update cached statistics for a project."""
    # Count user stories
    story_stats_stmt = select(
        func.count(UserStory.id).label("total"),
        func.count(UserStory.id).filter(UserStory.status == UserStoryStatus.DONE.value).label("completed"),
        func.sum(UserStory.story_points).label("total_points"),
        func.sum(UserStory.story_points).filter(UserStory.status == UserStoryStatus.DONE.value).label("completed_points"),
    ).where(UserStory.project_id == project_id, UserStory.deleted_at.is_(None))
    
    story_stats = (await db.execute(story_stats_stmt)).one()
    
    # Count issues
    issue_stats_stmt = select(
        func.count(Issue.id).label("total"),
        func.count(Issue.id).filter(Issue.status != IssueStatus.CLOSED.value).label("open"),
    ).where(Issue.project_id == project_id, Issue.deleted_at.is_(None))
    
    issue_stats = (await db.execute(issue_stats_stmt)).one()
    
    # Update project
    await db.execute(
        update(Project)
        .where(Project.id == project_id)
        .values(
            total_user_stories=story_stats.total or 0,
            completed_user_stories=story_stats.completed or 0,
            total_story_points=int(story_stats.total_points or 0),
            completed_story_points=int(story_stats.completed_points or 0),
            total_issues=issue_stats.total or 0,
            open_issues=issue_stats.open or 0,
            updated_at=_now_utc()
        )
    )
    # No commit here, usually called within another transaction


async def _update_sprint_stats(db: DBSession, sprint_id: UUID) -> None:
    """Update cached statistics for a sprint."""
    stats_stmt = select(
        func.sum(UserStory.story_points).label("planned"),
        func.sum(UserStory.story_points).filter(UserStory.status == UserStoryStatus.DONE.value).label("completed"),
    ).where(UserStory.sprint_id == sprint_id, UserStory.deleted_at.is_(None))
    
    stats = (await db.execute(stats_stmt)).one()
    
    await db.execute(
        update(Sprint)
        .where(Sprint.id == sprint_id)
        .values(
            planned_points=int(stats.planned or 0),
            completed_points=int(stats.completed or 0),
            updated_at=_now_utc()
        )
    )


async def _update_milestone_stats(db: DBSession, milestone_id: UUID) -> None:
    """Update cached statistics for a milestone."""
    # Count stories
    story_stats_stmt = select(
        func.count(UserStory.id).label("total"),
        func.count(UserStory.id).filter(UserStory.status == UserStoryStatus.DONE.value).label("completed"),
    ).where(UserStory.milestone_id == milestone_id, UserStory.deleted_at.is_(None))
    
    story_stats = (await db.execute(story_stats_stmt)).one()
    
    # Count issues
    issue_stats_stmt = select(
        func.count(Issue.id).label("total"),
        func.count(Issue.id).filter(Issue.status == IssueStatus.CLOSED.value).label("closed"),
    ).where(Issue.milestone_id == milestone_id, Issue.deleted_at.is_(None))
    
    issue_stats = (await db.execute(issue_stats_stmt)).one()
    
    total = (story_stats.total or 0) + (issue_stats.total or 0)
    closed = (story_stats.completed or 0) + (issue_stats.closed or 0)
    
    await db.execute(
        update(ProjectMilestone)
        .where(ProjectMilestone.id == milestone_id)
        .values(
            total_items=total,
            closed_items=closed,
            updated_at=_now_utc()
        )
    )


class ProjectActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: Optional[UUID]
    activity_type: str
    entity_type: str
    entity_id: UUID
    entity_ref: Optional[int]
    summary: str
    details: Optional[dict]
    created_at: datetime

    @classmethod
    def from_model(cls, activity: ProjectActivity) -> "ProjectActivityResponse":
        return cls(
            id=activity.id,
            project_id=activity.project_id,
            user_id=activity.user_id,
            activity_type=activity.activity_type,
            entity_type=activity.entity_type,
            entity_id=activity.entity_id,
            entity_ref=activity.entity_ref,
            summary=activity.summary,
            details=activity.details,
            created_at=activity.created_at,
        )


# =============================================================================
# Project schemas
# =============================================================================


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    project_type: str = Field(default=ProjectType.STANDARD.value)
    status: str = Field(default=ProjectStatus.PLANNING.value)
    is_private: bool = Field(default=False)
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    color: str = Field(default="#3b82f6", max_length=7)
    use_story_points: bool = True
    use_time_tracking: bool = True
    enable_wiki: bool = True
    enable_issues: bool = True
    enable_sprints: bool = True
    custom_user_story_statuses: Optional[list] = None
    custom_task_statuses: Optional[list] = None
    custom_issue_statuses: Optional[list] = None

    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v: str) -> str:
        _parse_enum(ProjectType, v, "project_type")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        _parse_enum(ProjectStatus, v, "status")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    project_type: Optional[str] = None
    status: Optional[str] = None
    is_private: Optional[bool] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    color: Optional[str] = Field(default=None, max_length=7)
    use_story_points: Optional[bool] = None
    use_time_tracking: Optional[bool] = None
    enable_wiki: Optional[bool] = None
    enable_issues: Optional[bool] = None
    enable_sprints: Optional[bool] = None
    custom_user_story_statuses: Optional[list] = None
    custom_task_statuses: Optional[list] = None
    custom_issue_statuses: Optional[list] = None

    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(ProjectType, v, "project_type")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(ProjectStatus, v, "status")
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    project_type: str
    status: str
    owner_id: Optional[UUID]
    is_private: bool
    start_date: Optional[date]
    target_end_date: Optional[date]
    color: str
    use_story_points: bool
    use_time_tracking: bool
    enable_wiki: bool
    enable_issues: bool
    enable_sprints: bool
    custom_user_story_statuses: Optional[list]
    custom_task_statuses: Optional[list]
    custom_issue_statuses: Optional[list]
    total_user_stories: int
    completed_user_stories: int
    total_story_points: int
    completed_story_points: int
    total_issues: int
    open_issues: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, project: Project) -> "ProjectResponse":
        return cls(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            project_type=project.project_type,
            status=project.status,
            owner_id=project.owner_id,
            is_private=project.is_private,
            start_date=project.start_date,
            target_end_date=project.target_end_date,
            color=project.color,
            use_story_points=project.use_story_points,
            use_time_tracking=project.use_time_tracking,
            enable_wiki=project.enable_wiki,
            enable_issues=project.enable_issues,
            enable_sprints=project.enable_sprints,
            custom_user_story_statuses=project.custom_user_story_statuses,
            custom_task_statuses=project.custom_task_statuses,
            custom_issue_statuses=project.custom_issue_statuses,
            total_user_stories=project.total_user_stories,
            completed_user_stories=project.completed_user_stories,
            total_story_points=project.total_story_points,
            completed_story_points=project.completed_story_points,
            total_issues=project.total_issues,
            open_issues=project.open_issues,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectMemberCreate(BaseModel):
    user_id: UUID
    role: str = Field(default="member", max_length=50)
    can_edit: bool = True
    can_comment: bool = True
    can_invite: bool = False
    can_delete: bool = False


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    user_id: UUID
    role: str
    can_edit: bool
    can_comment: bool
    can_invite: bool
    can_delete: bool
    created_at: datetime


# =============================================================================
# Epic schemas
# =============================================================================


class EpicCreate(BaseModel):
    project_id: UUID
    subject: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = Field(default=EpicStatus.NEW.value)
    owner_id: Optional[UUID] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        _parse_enum(EpicStatus, v, "status")
        return v


class EpicUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[UUID] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(EpicStatus, v, "status")
        return v


class EpicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    ref: int
    subject: str
    description: Optional[str]
    status: str
    owner_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, epic: Epic) -> "EpicResponse":
        return cls(
            id=epic.id,
            project_id=epic.project_id,
            ref=epic.ref,
            subject=epic.subject,
            description=epic.description,
            status=epic.status,
            owner_id=epic.owner_id,
            created_at=epic.created_at,
            updated_at=epic.updated_at,
        )


# =============================================================================
# Sprint schemas
# =============================================================================


class SprintCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    status: str = Field(default=SprintStatus.PLANNED.value)
    start_date: date
    end_date: date

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        _parse_enum(SprintStatus, v, "status")
        return v


class SprintUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(SprintStatus, v, "status")
        return v


class SprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    status: str
    start_date: Optional[date]
    end_date: Optional[date]
    planned_points: int
    completed_points: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, sprint: Sprint) -> "SprintResponse":
        return cls(
            id=sprint.id,
            project_id=sprint.project_id,
            name=sprint.name,
            status=sprint.status,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            planned_points=sprint.planned_points,
            completed_points=sprint.completed_points,
            created_at=sprint.created_at,
            updated_at=sprint.updated_at,
        )


# =============================================================================
# User story schemas
# =============================================================================


class UserStoryCreate(BaseModel):
    project_id: UUID
    subject: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = Field(default=UserStoryStatus.NEW.value)
    epic_id: Optional[UUID] = None
    sprint_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    priority: int = Field(default=50, ge=0, le=100)
    story_points: Optional[int] = None
    estimated_hours: Optional[float] = None
    tags: Optional[list[str]] = None
    attachments: Optional[list[dict]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        _parse_enum(UserStoryStatus, v, "status")
        return v


class UserStoryUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    epic_id: Optional[UUID] = None
    sprint_id: Optional[UUID] = None
    milestone_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    priority: Optional[int] = Field(default=None, ge=0, le=100)
    story_points: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    tags: Optional[list[str]] = None
    attachments: Optional[list[dict]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(UserStoryStatus, v, "status")
        return v


class UserStoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    ref: int
    subject: str
    description: Optional[str]
    status: str
    epic_id: Optional[UUID]
    sprint_id: Optional[UUID]
    milestone_id: Optional[UUID]
    owner_id: Optional[UUID]
    priority: int
    story_points: Optional[int]
    estimated_hours: Optional[float]
    actual_hours: float
    tags: Optional[list]
    attachments: Optional[list]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, story: UserStory) -> "UserStoryResponse":
        return cls(
            id=story.id,
            project_id=story.project_id,
            ref=story.ref,
            subject=story.subject,
            description=story.description,
            status=story.status,
            epic_id=story.epic_id,
            sprint_id=story.sprint_id,
            milestone_id=story.milestone_id,
            owner_id=story.owner_id,
            priority=story.priority,
            story_points=story.story_points,
            estimated_hours=story.estimated_hours,
            actual_hours=story.actual_hours,
            tags=story.tags,
            attachments=story.attachments,
            created_at=story.created_at,
            updated_at=story.updated_at,
        )


# =============================================================================
# Subtask schemas
# =============================================================================


class SubtaskCreate(BaseModel):
    user_story_id: UUID
    subject: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[date] = None
    status: str = Field(default="open")


class SubtaskUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    is_closed: Optional[bool] = None


class SubtaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_story_id: UUID
    ref: int
    subject: str
    description: Optional[str]
    assigned_to_id: Optional[UUID]
    status: str
    is_closed: bool
    due_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, subtask: Subtask) -> "SubtaskResponse":
        return cls(
            id=subtask.id,
            user_story_id=subtask.user_story_id,
            ref=subtask.ref,
            subject=subtask.subject,
            description=subtask.description,
            assigned_to_id=subtask.assigned_to_id,
            status=subtask.status,
            is_closed=subtask.is_closed,
            due_date=subtask.due_date,
            created_at=subtask.created_at,
            updated_at=subtask.updated_at,
        )


# =============================================================================
# Story comments schemas
# =============================================================================


class StoryCommentCreate(BaseModel):
    user_story_id: UUID
    content: str = Field(..., min_length=1)


class StoryCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_story_id: UUID
    author_id: Optional[UUID]
    content: str
    created_at: datetime


# =============================================================================
# Issue schemas
# =============================================================================


class IssueCreate(BaseModel):
    project_id: UUID
    subject: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    issue_type: str = Field(default=IssueType.BUG.value)
    severity: str = Field(default=IssueSeverity.NORMAL.value)
    priority: str = Field(default=IssuePriority.NORMAL.value)
    status: str = Field(default=IssueStatus.NEW.value)
    milestone_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[date] = None
    tags: Optional[list[str]] = None

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v: str) -> str:
        _parse_enum(IssueType, v, "issue_type")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        _parse_enum(IssueSeverity, v, "severity")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        _parse_enum(IssuePriority, v, "priority")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        _parse_enum(IssueStatus, v, "status")
        return v


class IssueUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    issue_type: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    milestone_id: Optional[UUID] = None
    assigned_to_id: Optional[UUID] = None
    due_date: Optional[date] = None
    finished_date: Optional[date] = None
    order: Optional[int] = None
    tags: Optional[list[str]] = None

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(IssueType, v, "issue_type")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(IssueSeverity, v, "severity")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(IssuePriority, v, "priority")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(IssueStatus, v, "status")
        return v


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    ref: int
    milestone_id: Optional[UUID]
    subject: str
    description: Optional[str]
    issue_type: str
    severity: str
    priority: str
    status: str
    owner_id: Optional[UUID]
    assigned_to_id: Optional[UUID]
    due_date: Optional[date]
    finished_date: Optional[date]
    order: int
    tags: Optional[list]
    watchers: Optional[list]
    attachments: Optional[list]
    custom_attributes: Optional[dict]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, issue: Issue) -> "IssueResponse":
        return cls(
            id=issue.id,
            project_id=issue.project_id,
            ref=issue.ref,
            milestone_id=issue.milestone_id,
            subject=issue.subject,
            description=issue.description,
            issue_type=issue.issue_type,
            severity=issue.severity,
            priority=issue.priority,
            status=issue.status,
            owner_id=issue.owner_id,
            assigned_to_id=issue.assigned_to_id,
            due_date=issue.due_date,
            finished_date=issue.finished_date,
            order=issue.order,
            tags=issue.tags,
            watchers=issue.watchers,
            attachments=issue.attachments,
            custom_attributes=issue.custom_attributes,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )


class IssueCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    mentions: Optional[list] = None
    attachments: Optional[list] = None


class IssueCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_id: UUID
    author_id: Optional[UUID]
    content: str
    mentions: Optional[list]
    attachments: Optional[list]
    is_edited: bool
    edited_at: Optional[datetime]
    created_at: datetime


# =============================================================================
# ProjectMilestone schemas
# =============================================================================


class ProjectMilestoneCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    milestone_type: str = Field(default=MilestoneType.DEADLINE.value)
    due_date: date
    order: int = 0

    @field_validator("milestone_type")
    @classmethod
    def validate_milestone_type(cls, v: str) -> str:
        _parse_enum(MilestoneType, v, "milestone_type")
        return v


class ProjectMilestoneUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    milestone_type: Optional[str] = None
    due_date: Optional[date] = None
    order: Optional[int] = None
    is_closed: Optional[bool] = None

    @field_validator("milestone_type")
    @classmethod
    def validate_milestone_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(MilestoneType, v, "milestone_type")
        return v


class ProjectMilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    slug: str
    description: Optional[str]
    milestone_type: str
    due_date: date
    is_closed: bool
    closed_at: Optional[datetime]
    order: int
    total_items: int
    closed_items: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, milestone: ProjectMilestone) -> "ProjectMilestoneResponse":
        return cls(
            id=milestone.id,
            project_id=milestone.project_id,
            name=milestone.name,
            slug=milestone.slug,
            description=milestone.description,
            milestone_type=milestone.milestone_type,
            due_date=milestone.due_date,
            is_closed=milestone.is_closed,
            closed_at=milestone.closed_at,
            order=milestone.order,
            total_items=milestone.total_items,
            closed_items=milestone.closed_items,
            created_at=milestone.created_at,
            updated_at=milestone.updated_at,
        )


# =============================================================================
# Wiki schemas
# =============================================================================


class WikiPageCreate(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(default="")
    page_type: str = Field(default=WikiPageType.DOCUMENTATION.value)
    parent_id: Optional[UUID] = None
    order: int = 0

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: str) -> str:
        _parse_enum(WikiPageType, v, "page_type")
        return v


class WikiPageUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = None
    page_type: Optional[str] = None
    parent_id: Optional[UUID] = None
    order: Optional[int] = None

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            _parse_enum(WikiPageType, v, "page_type")
        return v


class WikiPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    slug: str
    content: str
    page_type: str
    parent_id: Optional[UUID]
    order: int
    owner_id: Optional[UUID]
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, page: WikiPage) -> "WikiPageResponse":
        return cls(
            id=page.id,
            project_id=page.project_id,
            title=page.title,
            slug=page.slug,
            content=page.content,
            page_type=page.page_type,
            parent_id=page.parent_id,
            order=page.order,
            owner_id=page.owner_id,
            version=page.version,
            created_at=page.created_at,
            updated_at=page.updated_at,
        )


# =============================================================================
# Projects
# =============================================================================


@router.post("/projects", response_model=APIResponse)
async def create_project(payload: ProjectCreate, db: DBSession, user: CurrentUser):
    slug = payload.slug or slugify(payload.name)
    if not slug:
        raise ConflictError("Project slug could not be generated")

    existing = await db.execute(
        select(Project).where(Project.slug == slug, Project.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Project slug already exists")

    project = Project(
        name=payload.name,
        slug=slug,
        description=payload.description,
        project_type=payload.project_type,
        status=payload.status,
        owner_id=getattr(user, "id", None),
        is_private=payload.is_private,
        start_date=payload.start_date,
        target_end_date=payload.target_end_date,
        color=payload.color,
        use_story_points=payload.use_story_points,
        use_time_tracking=payload.use_time_tracking,
        enable_wiki=payload.enable_wiki,
        enable_issues=payload.enable_issues,
        enable_sprints=payload.enable_sprints,
        custom_user_story_statuses=payload.custom_user_story_statuses or [
            {"id": "new", "name": "New", "color": "#94a3b8", "is_closed": false},
            {"id": "ready", "name": "Ready", "color": "#3b82f6", "is_closed": false},
            {"id": "in_progress", "name": "In Progress", "color": "#8b5cf6", "is_closed": false},
            {"id": "ready_for_test", "name": "Ready for Test", "color": "#f59e0b", "is_closed": false},
            {"id": "done", "name": "Done", "color": "#10b981", "is_closed": true}
        ],
        custom_task_statuses=payload.custom_task_statuses or [
            {"id": "open", "name": "Open", "color": "#94a3b8", "is_closed": false},
            {"id": "in_progress", "name": "In Progress", "color": "#3b82f6", "is_closed": false},
            {"id": "completed", "name": "Completed", "color": "#10b981", "is_closed": true}
        ],
        custom_issue_statuses=payload.custom_issue_statuses or [
            {"id": "new", "name": "New", "color": "#ef4444", "is_closed": false},
            {"id": "in_progress", "name": "In Progress", "color": "#8b5cf6", "is_closed": false},
            {"id": "ready_for_test", "name": "Ready for Test", "color": "#f59e0b", "is_closed": false},
            {"id": "closed", "name": "Closed", "color": "#10b981", "is_closed": true},
            {"id": "rejected", "name": "Rejected", "color": "#64748b", "is_closed": true}
        ],
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )

    db.add(project)
    try:
        await db.flush()

        # Ensure the creator is also a project admin member (needed for private projects).
        uid = _user_id(user)
        if uid is not None:
            db.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=uid,
                    role="admin",
                    can_edit=True,
                    can_comment=True,
                    can_invite=True,
                    can_delete=True,
                )
            )

        await _log_activity(
            db,
            project_id=project.id,
            user=user,
            activity_type="create_project",
            entity_type="project",
            entity_id=project.id,
            summary=f"Created project {project.name}",
        )

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Project could not be created (constraint violation)")

    await db.refresh(project)
    return build_created_response(ProjectResponse.from_model(project), resource_name="Project")


@router.get("/projects", response_model=PaginatedResponse)
async def list_projects(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search by name/slug"),
):
    uid = _user_id(user)

    stmt = (
        select(Project)
        .outerjoin(
            ProjectMember,
            (ProjectMember.project_id == Project.id)
            & (ProjectMember.user_id == uid),
        )
        .where(Project.deleted_at.is_(None))
    )
    count_stmt = (
        select(func.count(func.distinct(Project.id)))
        .select_from(Project)
        .outerjoin(
            ProjectMember,
            (ProjectMember.project_id == Project.id)
            & (ProjectMember.user_id == uid),
        )
        .where(Project.deleted_at.is_(None))
    )

    # Privacy filter: public projects visible to all; private only to owner or members.
    if not _is_superuser(user):
        stmt = stmt.where(
            (Project.is_private.is_(False))
            | (Project.owner_id == uid)
            | (ProjectMember.user_id.is_not(None))
        )
        count_stmt = count_stmt.where(
            (Project.is_private.is_(False))
            | (Project.owner_id == uid)
            | (ProjectMember.user_id.is_not(None))
        )

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Project.name.ilike(like)) | (Project.slug.ilike(like)))
        count_stmt = count_stmt.where((Project.name.ilike(like)) | (Project.slug.ilike(like)))

    total = int((await db.execute(count_stmt)).scalar_one())
    # For PostgreSQL DISTINCT ON, ORDER BY must start with the DISTINCT ON columns
    if db.get_bind().dialect.name == "postgresql":
        stmt = (
            stmt.distinct(Project.id)
            .order_by(Project.id, Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    else:
        stmt = (
            stmt.distinct()
            .order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

    rows = (await db.execute(stmt)).scalars().all()
    data = [ProjectResponse.from_model(p) for p in rows]
    return build_paginated_response(data=data, page=page, page_size=page_size, total=total)


@router.get("/projects/{project_id}", response_model=APIResponse)
async def get_project(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    return APIResponse(success=True, message=None, data=ProjectResponse.from_model(project))


@router.patch("/projects/{project_id}", response_model=APIResponse)
async def update_project(project_id: UUID, payload: ProjectUpdate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)

    await _require_project_access(db, project, user, permission="edit")

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.project_type is not None:
        project.project_type = payload.project_type
    if payload.status is not None:
        project.status = payload.status
    if payload.is_private is not None:
        project.is_private = payload.is_private
    if payload.start_date is not None:
        project.start_date = payload.start_date
    if payload.target_end_date is not None:
        project.target_end_date = payload.target_end_date
    if payload.color is not None:
        project.color = payload.color
    if payload.use_story_points is not None:
        project.use_story_points = payload.use_story_points
    if payload.use_time_tracking is not None:
        project.use_time_tracking = payload.use_time_tracking
    if payload.enable_wiki is not None:
        project.enable_wiki = payload.enable_wiki
    if payload.enable_issues is not None:
        project.enable_issues = payload.enable_issues
    if payload.enable_sprints is not None:
        project.enable_sprints = payload.enable_sprints
    if payload.custom_user_story_statuses is not None:
        project.custom_user_story_statuses = payload.custom_user_story_statuses
    if payload.custom_task_statuses is not None:
        project.custom_task_statuses = payload.custom_task_statuses
    if payload.custom_issue_statuses is not None:
        project.custom_issue_statuses = payload.custom_issue_statuses

    project.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=project.id,
        user=user,
        activity_type="update_project",
        entity_type="project",
        entity_id=project.id,
        summary=f"Updated project {project.name}",
    )

    await db.commit()
    await db.refresh(project)
    return build_updated_response(ProjectResponse.from_model(project), resource_name="Project")


@router.delete("/projects/{project_id}", response_model=APIResponse)
async def delete_project(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)

    await _require_project_access(db, project, user, permission="delete")

    project.deleted_at = _now_utc()
    project.deleted_by_id = getattr(user, "id", None)
    project.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=project.id,
        user=user,
        activity_type="delete_project",
        entity_type="project",
        entity_id=project.id,
        summary=f"Deleted project {project.name}",
    )
    await db.commit()
    return build_deleted_response(resource_name="Project")


@router.get("/projects/{project_id}/activities", response_model=PaginatedResponse)
async def list_project_activities(
    project_id: UUID,
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")

    stmt = select(ProjectActivity).where(ProjectActivity.project_id == project_id).order_by(ProjectActivity.created_at.desc())
    count_stmt = select(func.count(ProjectActivity.id)).where(ProjectActivity.project_id == project_id)

    total = int((await db.execute(count_stmt)).scalar_one())
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    
    data = [ProjectActivityResponse.from_model(a) for a in rows]
    return build_paginated_response(data=data, page=page, page_size=page_size, total=total)


# =============================================================================
# Project membership
# =============================================================================


@router.post("/projects/{project_id}/members", response_model=APIResponse)
async def add_project_member(project_id: UUID, payload: ProjectMemberCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="invite")

    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == payload.user_id,
        )
    )
    member = existing.scalar_one_or_none()

    if member is None:
        member = ProjectMember(
            project_id=project_id,
            user_id=payload.user_id,
            role=payload.role,
            can_edit=payload.can_edit,
            can_comment=payload.can_comment,
            can_invite=payload.can_invite,
            can_delete=payload.can_delete,
        )
        db.add(member)
    else:
        member.role = payload.role
        member.can_edit = payload.can_edit
        member.can_comment = payload.can_comment
        member.can_invite = payload.can_invite
        member.can_delete = payload.can_delete

    await _log_activity(
        db,
        project_id=project_id,
        user=user,
        activity_type="upsert_member",
        entity_type="project_member",
        entity_id=project_id,
        summary=f"Updated membership for user {payload.user_id}",
        details={"member_user_id": str(payload.user_id), "role": payload.role},
    )

    await db.commit()
    return build_created_response(ProjectMemberResponse.model_validate(member), resource_name="Project member")


@router.get("/projects/{project_id}/members", response_model=APIResponse)
async def list_project_members(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id)))
        .scalars()
        .all()
    )
    data = [ProjectMemberResponse.model_validate(m) for m in rows]
    return APIResponse(success=True, message=None, data=data)


@router.delete("/projects/{project_id}/members/{user_id}", response_model=APIResponse)
async def remove_project_member(project_id: UUID, user_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="delete")
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("ProjectMember", f"{project_id}:{user_id}")

    await db.delete(member)

    await _log_activity(
        db,
        project_id=project_id,
        user=user,
        activity_type="remove_member",
        entity_type="project_member",
        entity_id=project_id,
        summary=f"Removed member {user_id}",
        details={"member_user_id": str(user_id)},
    )

    await db.commit()
    return build_deleted_response(resource_name="Project member")


# =============================================================================
# Epics
# =============================================================================


@router.post("/epics", response_model=APIResponse)
async def create_epic(payload: EpicCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, payload.project_id)
    await _require_project_access(db, project, user, permission="edit")
    ref = await _get_next_project_ref(db, payload.project_id, "epic")

    epic = Epic(
        project_id=payload.project_id,
        ref=ref,
        subject=payload.subject,
        description=payload.description,
        status=payload.status,
        owner_id=payload.owner_id,
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )

    db.add(epic)

    await db.flush()

    await _log_activity(
        db,
        project_id=payload.project_id,
        user=user,
        activity_type="create_epic",
        entity_type="epic",
        entity_id=epic.id,
        entity_ref=ref,
        summary=f"Created epic EP-{ref}: {epic.subject}",
    )

    await db.commit()
    await db.refresh(epic)
    return build_created_response(EpicResponse.from_model(epic), resource_name="Epic")


@router.get("/epics", response_model=APIResponse)
async def list_epics_by_query(project_id: UUID, db: DBSession, user: CurrentUser):
    """List epics for a project by query parameter."""
    # Kept for backwards compatibility; prefer /projects/{project_id}/epics
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(select(Epic).where(Epic.project_id == project_id, Epic.deleted_at.is_(None)).order_by(Epic.ref.asc())))
        .scalars()
        .all()
    )
    data = [EpicResponse.from_model(e) for e in rows]
    return APIResponse(success=True, message=None, data=data)


@router.get("/projects/{project_id}/epics", response_model=APIResponse)
async def list_epics(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(select(Epic).where(Epic.project_id == project_id, Epic.deleted_at.is_(None)).order_by(Epic.ref.asc())))
        .scalars()
        .all()
    )
    data = [EpicResponse.from_model(e) for e in rows]
    return APIResponse(success=True, message=None, data=data)


@router.patch("/epics/{epic_id}", response_model=APIResponse)
async def update_epic(epic_id: UUID, payload: EpicUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Epic).where(Epic.id == epic_id, Epic.deleted_at.is_(None)))
    epic = result.scalar_one_or_none()
    if not epic:
        raise NotFoundError("Epic", str(epic_id))

    project = await _get_project_or_404(db, epic.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.subject is not None:
        epic.subject = payload.subject
    if payload.description is not None:
        epic.description = payload.description
    if payload.status is not None:
        epic.status = payload.status
    if payload.owner_id is not None:
        epic.owner_id = payload.owner_id

    epic.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=epic.project_id,
        user=user,
        activity_type="update_epic",
        entity_type="epic",
        entity_id=epic.id,
        entity_ref=epic.ref,
        summary=f"Updated epic EP-{epic.ref}: {epic.subject}",
    )
    await db.commit()
    await db.refresh(epic)
    return build_updated_response(EpicResponse.from_model(epic), resource_name="Epic")


@router.delete("/epics/{epic_id}", response_model=APIResponse)
async def delete_epic(epic_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Epic).where(Epic.id == epic_id, Epic.deleted_at.is_(None)))
    epic = result.scalar_one_or_none()
    if not epic:
        raise NotFoundError("Epic", str(epic_id))

    project = await _get_project_or_404(db, epic.project_id)
    await _require_project_access(db, project, user, permission="delete")

    epic.deleted_at = _now_utc()
    epic.deleted_by_id = getattr(user, "id", None)
    epic.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=epic.project_id,
        user=user,
        activity_type="delete_epic",
        entity_type="epic",
        entity_id=epic.id,
        entity_ref=epic.ref,
        summary=f"Deleted epic EP-{epic.ref}: {epic.subject}",
    )
    await db.commit()
    return build_deleted_response(resource_name="Epic")


# =============================================================================
# Sprints
# =============================================================================


@router.post("/sprints", response_model=APIResponse)
async def create_sprint(payload: SprintCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, payload.project_id)
    await _require_project_access(db, project, user, permission="edit")

    sprint = Sprint(
        project_id=payload.project_id,
        name=payload.name,
        slug=slugify(payload.name),
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )

    db.add(sprint)

    await db.flush()

    await _log_activity(
        db,
        project_id=payload.project_id,
        user=user,
        activity_type="create_sprint",
        entity_type="sprint",
        entity_id=sprint.id,
        summary=f"Created sprint: {sprint.name}",
    )
    await db.commit()
    await db.refresh(sprint)
    return build_created_response(SprintResponse.from_model(sprint), resource_name="Sprint")


@router.get("/sprints", response_model=APIResponse)
async def list_sprints_by_query(project_id: UUID, db: DBSession, user: CurrentUser):
    """List sprints for a project by query parameter."""
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(select(Sprint).where(Sprint.project_id == project_id, Sprint.deleted_at.is_(None)).order_by(Sprint.created_at.desc())))
        .scalars()
        .all()
    )
    data = [SprintResponse.from_model(s) for s in rows]
    return APIResponse(success=True, message=None, data=data)


@router.get("/projects/{project_id}/sprints", response_model=APIResponse)
async def list_sprints(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(select(Sprint).where(Sprint.project_id == project_id, Sprint.deleted_at.is_(None)).order_by(Sprint.created_at.desc())))
        .scalars()
        .all()
    )
    data = [SprintResponse.from_model(s) for s in rows]
    return APIResponse(success=True, message=None, data=data)


@router.patch("/sprints/{sprint_id}", response_model=APIResponse)
async def update_sprint(sprint_id: UUID, payload: SprintUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Sprint).where(Sprint.id == sprint_id, Sprint.deleted_at.is_(None)))
    sprint = result.scalar_one_or_none()
    if not sprint:
        raise NotFoundError("Sprint", str(sprint_id))

    project = await _get_project_or_404(db, sprint.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.name is not None:
        sprint.name = payload.name
    if payload.status is not None:
        sprint.status = payload.status
    if payload.start_date is not None:
        sprint.start_date = payload.start_date
    if payload.end_date is not None:
        sprint.end_date = payload.end_date

    sprint.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=sprint.project_id,
        user=user,
        activity_type="update_sprint",
        entity_type="sprint",
        entity_id=sprint.id,
        summary=f"Updated sprint: {sprint.name}",
    )
    await db.commit()
    await db.refresh(sprint)
    return build_updated_response(SprintResponse.from_model(sprint), resource_name="Sprint")


@router.delete("/sprints/{sprint_id}", response_model=APIResponse)
async def delete_sprint(sprint_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Sprint).where(Sprint.id == sprint_id, Sprint.deleted_at.is_(None)))
    sprint = result.scalar_one_or_none()
    if not sprint:
        raise NotFoundError("Sprint", str(sprint_id))

    project = await _get_project_or_404(db, sprint.project_id)
    await _require_project_access(db, project, user, permission="delete")

    sprint.deleted_at = _now_utc()
    sprint.deleted_by_id = getattr(user, "id", None)
    sprint.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=sprint.project_id,
        user=user,
        activity_type="delete_sprint",
        entity_type="sprint",
        entity_id=sprint.id,
        summary=f"Deleted sprint: {sprint.name}",
    )
    await db.commit()
    return build_deleted_response(resource_name="Sprint")


# =============================================================================
# User stories
# =============================================================================


@router.post("/user-stories", response_model=APIResponse)
async def create_user_story(payload: UserStoryCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, payload.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.epic_id is not None:
        epic_result = await db.execute(
            select(Epic).where(
                Epic.id == payload.epic_id,
                Epic.project_id == payload.project_id,
                Epic.deleted_at.is_(None),
            )
        )
        if epic_result.scalar_one_or_none() is None:
            raise NotFoundError("Epic", str(payload.epic_id))

    if payload.sprint_id is not None:
        sprint_result = await db.execute(
            select(Sprint).where(
                Sprint.id == payload.sprint_id,
                Sprint.project_id == payload.project_id,
                Sprint.deleted_at.is_(None),
            )
        )
        if sprint_result.scalar_one_or_none() is None:
            raise NotFoundError("Sprint", str(payload.sprint_id))

    ref = await _get_next_project_ref(db, payload.project_id, "user_story")
    story = UserStory(
        project_id=payload.project_id,
        ref=ref,
        subject=payload.subject,
        description=payload.description,
        status=payload.status,
        epic_id=payload.epic_id,
        sprint_id=payload.sprint_id,
        milestone_id=payload.milestone_id,
        owner_id=payload.owner_id,
        priority=payload.priority,
        story_points=payload.story_points,
        estimated_hours=payload.estimated_hours,
        tags=payload.tags,
        attachments=payload.attachments,
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )

    db.add(story)

    await db.flush()

    await _log_activity(
        db,
        project_id=payload.project_id,
        user=user,
        activity_type="create_user_story",
        entity_type="user_story",
        entity_id=story.id,
        entity_ref=ref,
        summary=f"Created story US-{ref}: {story.subject}",
    )
    await _update_project_stats(db, payload.project_id)
    if story.sprint_id:
        await _update_sprint_stats(db, story.sprint_id)
    if story.milestone_id:
        await _update_milestone_stats(db, story.milestone_id)
    
    await db.commit()
    await db.refresh(story)
    return build_created_response(UserStoryResponse.from_model(story), resource_name="User story")


@router.get("/user-stories", response_model=APIResponse)
async def list_user_stories_by_query(project_id: UUID, db: DBSession, user: CurrentUser):
    """List user stories for a project by query parameter."""
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(
            select(UserStory)
            .where(UserStory.project_id == project_id, UserStory.deleted_at.is_(None))
            .order_by(UserStory.ref.asc())
        ))
        .scalars()
        .all()
    )
    data = [UserStoryResponse.from_model(s) for s in rows]
    return APIResponse(success=True, message=None, data=data)


@router.get("/projects/{project_id}/user-stories", response_model=APIResponse)
async def list_user_stories(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")
    rows = (
        (await db.execute(
            select(UserStory)
            .where(UserStory.project_id == project_id, UserStory.deleted_at.is_(None))
            .order_by(UserStory.ref.asc())
        ))
        .scalars()
        .all()
    )
    data = [UserStoryResponse.from_model(s) for s in rows]
    return APIResponse(success=True, message=None, data=data)


@router.get("/my-work", response_model=APIResponse)
async def get_my_work(db: DBSession, user: CurrentUser):
    """Get assigned user stories and issues for the current user."""
    user_id = getattr(user, "id", None)
    if not user_id:
        return APIResponse(success=True, data={"stories": [], "issues": []})

    # Assigned User Stories (Owner or Assigned)
    # Filter out completed/archived to keep "my-work" actionable
    story_stmt = (
        select(UserStory)
        .where(
            (UserStory.owner_id == user_id) | (UserStory.assigned_users.contains([str(user_id)])),
            UserStory.deleted_at.is_(None),
            UserStory.status != UserStoryStatus.DONE.value,
            UserStory.status != UserStoryStatus.ARCHIVED.value
        )
        .order_by(UserStory.priority.desc(), UserStory.updated_at.desc())
        .limit(50)
    )
    stories = (await db.execute(story_stmt)).scalars().all()

    # Assigned Issues
    issue_stmt = (
        select(Issue)
        .where(
            (Issue.assigned_to_id == user_id) | (Issue.owner_id == user_id),
            Issue.deleted_at.is_(None),
            Issue.status != IssueStatus.CLOSED.value,
            Issue.status != IssueStatus.REJECTED.value
        )
        .order_by(Issue.updated_at.desc())
        .limit(50)
    )
    issues = (await db.execute(issue_stmt)).scalars().all()

    return APIResponse(
        success=True,
        data={
            "stories": [UserStoryResponse.from_model(s) for s in stories],
            "issues": [IssueResponse.from_model(i) for i in issues],
        },
    )


@router.patch("/user-stories/{story_id}", response_model=APIResponse)
async def update_user_story(story_id: UUID, payload: UserStoryUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(UserStory).where(UserStory.id == story_id, UserStory.deleted_at.is_(None)))
    story = result.scalar_one_or_none()
    if not story:
        raise NotFoundError("UserStory", str(story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.epic_id is not None:
        epic_result = await db.execute(
            select(Epic).where(
                Epic.id == payload.epic_id,
                Epic.project_id == story.project_id,
                Epic.deleted_at.is_(None),
            )
        )
        if epic_result.scalar_one_or_none() is None:
            raise NotFoundError("Epic", str(payload.epic_id))

    if payload.sprint_id is not None:
        sprint_result = await db.execute(
            select(Sprint).where(
                Sprint.id == payload.sprint_id,
                Sprint.project_id == story.project_id,
                Sprint.deleted_at.is_(None),
            )
        )
        if sprint_result.scalar_one_or_none() is None:
            raise NotFoundError("Sprint", str(payload.sprint_id))

    old_sprint_id = story.sprint_id
    old_milestone_id = story.milestone_id

    if payload.subject is not None:
        story.subject = payload.subject
    if payload.description is not None:
        story.description = payload.description
    if payload.status is not None:
        story.status = payload.status
    if payload.epic_id is not None:
        story.epic_id = payload.epic_id
    if payload.sprint_id is not None:
        story.sprint_id = payload.sprint_id
    if payload.milestone_id is not None:
        story.milestone_id = payload.milestone_id
    if payload.owner_id is not None:
        story.owner_id = payload.owner_id
    if payload.priority is not None:
        story.priority = payload.priority
    if payload.story_points is not None:
        story.story_points = payload.story_points
    if payload.estimated_hours is not None:
        story.estimated_hours = payload.estimated_hours
    if payload.actual_hours is not None:
        story.actual_hours = payload.actual_hours
    if payload.tags is not None:
        story.tags = payload.tags
    if payload.attachments is not None:
        story.attachments = payload.attachments

    story.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=story.project_id,
        user=user,
        activity_type="update_user_story",
        entity_type="user_story",
        entity_id=story.id,
        entity_ref=story.ref,
        summary=f"Updated story US-{story.ref}: {story.subject}",
    )
    await _update_project_stats(db, story.project_id)
    if old_sprint_id:
        await _update_sprint_stats(db, old_sprint_id)
    if story.sprint_id and story.sprint_id != old_sprint_id:
        await _update_sprint_stats(db, story.sprint_id)
    
    if old_milestone_id:
        await _update_milestone_stats(db, old_milestone_id)
    if story.milestone_id and story.milestone_id != old_milestone_id:
        await _update_milestone_stats(db, story.milestone_id)
    
    await db.commit()
    await db.refresh(story)
    return build_updated_response(UserStoryResponse.from_model(story), resource_name="User story")


@router.delete("/user-stories/{story_id}", response_model=APIResponse)
async def delete_user_story(story_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(UserStory).where(UserStory.id == story_id, UserStory.deleted_at.is_(None)))
    story = result.scalar_one_or_none()
    if not story:
        raise NotFoundError("UserStory", str(story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="delete")

    story.deleted_at = _now_utc()
    story.deleted_by_id = getattr(user, "id", None)
    story.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=story.project_id,
        user=user,
        activity_type="delete_user_story",
        entity_type="user_story",
        entity_id=story.id,
        entity_ref=story.ref,
        summary=f"Deleted story US-{story.ref}: {story.subject}",
    )
    await _update_project_stats(db, story.project_id)
    if story.sprint_id:
        await _update_sprint_stats(db, story.sprint_id)
    if story.milestone_id:
        await _update_milestone_stats(db, story.milestone_id)
    
    await db.commit()
    return build_deleted_response(resource_name="User story")


# =============================================================================
# Subtasks
# =============================================================================


@router.post("/subtasks", response_model=APIResponse)
async def create_subtask(payload: SubtaskCreate, db: DBSession, user: CurrentUser):
    # Ensure story exists
    result = await db.execute(select(UserStory).where(UserStory.id == payload.user_story_id, UserStory.deleted_at.is_(None)))
    story = result.scalar_one_or_none()
    if not story:
        raise NotFoundError("UserStory", str(payload.user_story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="edit")

    ref = await _next_story_ref(db, payload.user_story_id)

    # Determine is_closed from custom_task_statuses
    is_closed = False
    if project.custom_task_statuses:
        for s in project.custom_task_statuses:
            if s.get("id") == payload.status:
                is_closed = s.get("is_closed", False)
                break

    subtask = Subtask(
        user_story_id=payload.user_story_id,
        ref=ref,
        subject=payload.subject,
        description=payload.description,
        assigned_to_id=payload.assigned_to_id,
        due_date=payload.due_date,
        status=payload.status,
        is_closed=is_closed,
        closed_at=_now_utc() if is_closed else None,
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )

    db.add(subtask)

    await db.flush()

    await _log_activity(
        db,
        project_id=story.project_id,
        user=user,
        activity_type="create_subtask",
        entity_type="subtask",
        entity_id=subtask.id,
        entity_ref=ref,
        summary=f"Created subtask ST-{ref}: {subtask.subject}",
        details={"user_story_id": str(story.id), "user_story_ref": story.ref},
    )
    await db.commit()
    await db.refresh(subtask)
    return build_created_response(SubtaskResponse.from_model(subtask), resource_name="Subtask")


@router.get("/user-stories/{story_id}/subtasks", response_model=APIResponse)
async def list_subtasks(story_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(UserStory).where(UserStory.id == story_id, UserStory.deleted_at.is_(None)))
    story = result.scalar_one_or_none()
    if story is None:
        raise NotFoundError("UserStory", str(story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="read")

    rows = (
        (await db.execute(select(Subtask).where(Subtask.user_story_id == story_id).order_by(Subtask.ref.asc())))
        .scalars()
        .all()
    )
    data = [SubtaskResponse.from_model(st) for st in rows]
    return APIResponse(success=True, message=None, data=data)


@router.patch("/subtasks/{subtask_id}", response_model=APIResponse)
async def update_subtask(subtask_id: UUID, payload: SubtaskUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Subtask).where(Subtask.id == subtask_id))
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise NotFoundError("Subtask", str(subtask_id))

    story_result = await db.execute(select(UserStory).where(UserStory.id == subtask.user_story_id, UserStory.deleted_at.is_(None)))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise NotFoundError("UserStory", str(subtask.user_story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.subject is not None:
        subtask.subject = payload.subject
    if payload.description is not None:
        subtask.description = payload.description
    if payload.assigned_to_id is not None:
        subtask.assigned_to_id = payload.assigned_to_id
    if payload.due_date is not None:
        subtask.due_date = payload.due_date
    
    if payload.status is not None:
        subtask.status = payload.status
        # Determine is_closed from custom_task_statuses
        is_closed = False
        if project.custom_task_statuses:
            for s in project.custom_task_statuses:
                if s.get("id") == payload.status:
                    is_closed = s.get("is_closed", False)
                    break
        subtask.is_closed = is_closed
        subtask.closed_at = _now_utc() if is_closed else None
    elif payload.is_closed is not None:
        subtask.is_closed = payload.is_closed
        subtask.closed_at = _now_utc() if payload.is_closed else None
        # If toggling via is_closed, try to pick a reasonable status
        if project.custom_task_statuses:
            for s in project.custom_task_statuses:
                if s.get("is_closed", False) == payload.is_closed:
                    subtask.status = s.get("id")
                    break

    subtask.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=story.project_id,
        user=user,
        activity_type="update_subtask",
        entity_type="subtask",
        entity_id=subtask.id,
        entity_ref=subtask.ref,
        summary=f"Updated subtask ST-{subtask.ref}: {subtask.subject}",
        details={"user_story_id": str(story.id), "user_story_ref": story.ref},
    )
    await db.commit()
    await db.refresh(subtask)
    return build_updated_response(SubtaskResponse.from_model(subtask), resource_name="Subtask")


@router.delete("/subtasks/{subtask_id}", response_model=APIResponse)
async def delete_subtask(subtask_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Subtask).where(Subtask.id == subtask_id))
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise NotFoundError("Subtask", str(subtask_id))

    story_result = await db.execute(select(UserStory).where(UserStory.id == subtask.user_story_id, UserStory.deleted_at.is_(None)))
    story = story_result.scalar_one_or_none()
    if story is None:
        raise NotFoundError("UserStory", str(subtask.user_story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="delete")

    await _log_activity(
        db,
        project_id=story.project_id,
        user=user,
        activity_type="delete_subtask",
        entity_type="subtask",
        entity_id=subtask.id,
        entity_ref=subtask.ref,
        summary=f"Deleted subtask ST-{subtask.ref}: {subtask.subject}",
        details={"user_story_id": str(story.id), "user_story_ref": story.ref},
    )

    await db.delete(subtask)
    await db.commit()
    return build_deleted_response(resource_name="Subtask")


# =============================================================================
# Story comments
# =============================================================================


@router.post("/story-comments", response_model=APIResponse)
async def create_story_comment(payload: StoryCommentCreate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(UserStory).where(UserStory.id == payload.user_story_id, UserStory.deleted_at.is_(None)))
    story = result.scalar_one_or_none()
    if story is None:
        raise NotFoundError("UserStory", str(payload.user_story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="comment")

    comment = StoryComment(
        user_story_id=payload.user_story_id,
        author_id=getattr(user, "id", None),
        content=payload.content,
    )
    db.add(comment)

    await db.flush()

    await _log_activity(
        db,
        project_id=story.project_id,
        user=user,
        activity_type="create_story_comment",
        entity_type="story_comment",
        entity_id=comment.id,
        summary=f"Commented on story US-{story.ref}",
        details={"user_story_id": str(story.id), "user_story_ref": story.ref},
    )
    await db.commit()
    await db.refresh(comment)
    return build_created_response(StoryCommentResponse.model_validate(comment), resource_name="Story comment")


@router.get("/user-stories/{story_id}/story-comments", response_model=APIResponse)
async def list_story_comments(story_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(UserStory).where(UserStory.id == story_id, UserStory.deleted_at.is_(None)))
    story = result.scalar_one_or_none()
    if story is None:
        raise NotFoundError("UserStory", str(story_id))

    project = await _get_project_or_404(db, story.project_id)
    await _require_project_access(db, project, user, permission="read")

    rows = (
        (await db.execute(select(StoryComment).where(StoryComment.user_story_id == story_id).order_by(StoryComment.created_at.asc())))
        .scalars()
        .all()
    )
    data = [StoryCommentResponse.model_validate(c) for c in rows]
    return APIResponse(success=True, message=None, data=data)


# =============================================================================
# Milestones
# =============================================================================


@router.post("/milestones", response_model=APIResponse)
async def create_milestone(payload: ProjectMilestoneCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, payload.project_id)
    await _require_project_access(db, project, user, permission="edit")

    slug = slugify(payload.name)
    if not slug:
        raise ConflictError("ProjectMilestone slug could not be generated")

    existing = await db.execute(
        select(ProjectMilestone).where(
            ProjectMilestone.project_id == payload.project_id,
            ProjectMilestone.slug == slug,
            ProjectMilestone.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("ProjectMilestone slug already exists")

    milestone = ProjectMilestone(
        project_id=payload.project_id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        milestone_type=payload.milestone_type,
        due_date=payload.due_date,
        order=payload.order,
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )
    db.add(milestone)

    await db.flush()

    await _log_activity(
        db,
        project_id=payload.project_id,
        user=user,
        activity_type="create_milestone",
        entity_type="milestone",
        entity_id=milestone.id,
        summary=f"Created milestone: {milestone.name}",
    )

    await db.commit()
    await db.refresh(milestone)
    return build_created_response(ProjectMilestoneResponse.from_model(milestone), resource_name="ProjectMilestone")


@router.get("/projects/{project_id}/milestones", response_model=APIResponse)
async def list_milestones(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")

    rows = (
        (
            await db.execute(
                select(ProjectMilestone)
                .where(ProjectMilestone.project_id == project_id, ProjectMilestone.deleted_at.is_(None))
                .order_by(ProjectMilestone.due_date.asc(), ProjectMilestone.order.asc())
            )
        )
        .scalars()
        .all()
    )
    data = [ProjectMilestoneResponse.from_model(m) for m in rows]
    return APIResponse(success=True, message=None, data=data)


@router.patch("/milestones/{milestone_id}", response_model=APIResponse)
async def update_milestone(milestone_id: UUID, payload: ProjectMilestoneUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(ProjectMilestone).where(ProjectMilestone.id == milestone_id, ProjectMilestone.deleted_at.is_(None)))
    milestone = result.scalar_one_or_none()
    if milestone is None:
        raise NotFoundError("ProjectMilestone", str(milestone_id))

    project = await _get_project_or_404(db, milestone.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.name is not None:
        new_slug = slugify(payload.name)
        if not new_slug:
            raise ConflictError("ProjectMilestone slug could not be generated")
        if new_slug != milestone.slug:
            existing = await db.execute(
                select(ProjectMilestone).where(
                    ProjectMilestone.project_id == milestone.project_id,
                    ProjectMilestone.slug == new_slug,
                    ProjectMilestone.id != milestone.id,
                    ProjectMilestone.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError("ProjectMilestone slug already exists")
        milestone.name = payload.name
        milestone.slug = new_slug

    if payload.description is not None:
        milestone.description = payload.description
    if payload.milestone_type is not None:
        milestone.milestone_type = payload.milestone_type
    if payload.due_date is not None:
        milestone.due_date = payload.due_date
    if payload.order is not None:
        milestone.order = payload.order
    if payload.is_closed is not None:
        milestone.is_closed = payload.is_closed
        milestone.closed_at = _now_utc() if payload.is_closed else None

    milestone.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=milestone.project_id,
        user=user,
        activity_type="update_milestone",
        entity_type="milestone",
        entity_id=milestone.id,
        summary=f"Updated milestone: {milestone.name}",
    )

    await db.commit()
    await db.refresh(milestone)
    return build_updated_response(ProjectMilestoneResponse.from_model(milestone), resource_name="ProjectMilestone")


@router.delete("/milestones/{milestone_id}", response_model=APIResponse)
async def delete_milestone(milestone_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(ProjectMilestone).where(ProjectMilestone.id == milestone_id, ProjectMilestone.deleted_at.is_(None)))
    milestone = result.scalar_one_or_none()
    if milestone is None:
        raise NotFoundError("ProjectMilestone", str(milestone_id))

    project = await _get_project_or_404(db, milestone.project_id)
    await _require_project_access(db, project, user, permission="delete")

    milestone.deleted_at = _now_utc()
    milestone.deleted_by_id = getattr(user, "id", None)
    milestone.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=milestone.project_id,
        user=user,
        activity_type="delete_milestone",
        entity_type="milestone",
        entity_id=milestone.id,
        summary=f"Deleted milestone: {milestone.name}",
    )

    await db.commit()
    return build_deleted_response(resource_name="ProjectMilestone")


# =============================================================================
# Issues
# =============================================================================


@router.post("/issues", response_model=APIResponse)
async def create_issue(payload: IssueCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, payload.project_id)
    await _require_project_access(db, project, user, permission="edit")

    if payload.milestone_id is not None:
        milestone_result = await db.execute(
            select(ProjectMilestone).where(
                ProjectMilestone.id == payload.milestone_id,
                ProjectMilestone.project_id == payload.project_id,
                ProjectMilestone.deleted_at.is_(None),
            )
        )
        if milestone_result.scalar_one_or_none() is None:
            raise NotFoundError("ProjectMilestone", str(payload.milestone_id))

    ref = await _get_next_project_ref(db, payload.project_id, "issue")
    issue = Issue(
        project_id=payload.project_id,
        ref=ref,
        milestone_id=payload.milestone_id,
        subject=payload.subject,
        description=payload.description,
        issue_type=payload.issue_type,
        severity=payload.severity,
        priority=payload.priority,
        status=payload.status,
        owner_id=getattr(user, "id", None),
        assigned_to_id=payload.assigned_to_id,
        due_date=payload.due_date,
        tags=payload.tags,
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )
    db.add(issue)

    await db.flush()

    await _log_activity(
        db,
        project_id=payload.project_id,
        user=user,
        activity_type="create_issue",
        entity_type="issue",
        entity_id=issue.id,
        entity_ref=ref,
        summary=f"Created issue IS-{ref}: {issue.subject}",
    )
    await _update_project_stats(db, payload.project_id)
    if issue.milestone_id:
        await _update_milestone_stats(db, issue.milestone_id)
    
    await db.commit()
    await db.refresh(issue)
    return build_created_response(IssueResponse.from_model(issue), resource_name="Issue")


@router.get("/projects/{project_id}/issues", response_model=APIResponse)
async def list_issues(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")

    rows = (
        (
            await db.execute(
                select(Issue)
                .where(Issue.project_id == project_id, Issue.deleted_at.is_(None))
                .order_by(Issue.ref.asc())
            )
        )
        .scalars()
        .all()
    )
    data = [IssueResponse.from_model(i) for i in rows]
    return APIResponse(success=True, message=None, data=data)


@router.patch("/issues/{issue_id}", response_model=APIResponse)
async def update_issue(issue_id: UUID, payload: IssueUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Issue).where(Issue.id == issue_id, Issue.deleted_at.is_(None)))
    issue = result.scalar_one_or_none()
    if issue is None:
        raise NotFoundError("Issue", str(issue_id))

    project = await _get_project_or_404(db, issue.project_id)
    await _require_project_access(db, project, user, permission="edit")

    old_milestone_id = issue.milestone_id

    if payload.milestone_id is not None:
        milestone_result = await db.execute(
            select(ProjectMilestone).where(
                ProjectMilestone.id == payload.milestone_id,
                ProjectMilestone.project_id == issue.project_id,
                ProjectMilestone.deleted_at.is_(None),
            )
        )
        if milestone_result.scalar_one_or_none() is None:
            raise NotFoundError("ProjectMilestone", str(payload.milestone_id))
        issue.milestone_id = payload.milestone_id

    if payload.subject is not None:
        issue.subject = payload.subject
    if payload.description is not None:
        issue.description = payload.description
    if payload.issue_type is not None:
        issue.issue_type = payload.issue_type
    if payload.severity is not None:
        issue.severity = payload.severity
    if payload.priority is not None:
        issue.priority = payload.priority
    if payload.status is not None:
        issue.status = payload.status
    if payload.assigned_to_id is not None:
        issue.assigned_to_id = payload.assigned_to_id
    if payload.due_date is not None:
        issue.due_date = payload.due_date
    if payload.finished_date is not None:
        issue.finished_date = payload.finished_date
    if payload.order is not None:
        issue.order = payload.order
    if payload.tags is not None:
        issue.tags = payload.tags

    issue.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=issue.project_id,
        user=user,
        activity_type="update_issue",
        entity_type="issue",
        entity_id=issue.id,
        entity_ref=issue.ref,
        summary=f"Updated issue IS-{issue.ref}: {issue.subject}",
    )

    await _update_project_stats(db, issue.project_id)
    if old_milestone_id:
        await _update_milestone_stats(db, old_milestone_id)
    if issue.milestone_id and issue.milestone_id != old_milestone_id:
        await _update_milestone_stats(db, issue.milestone_id)
    
    await db.commit()
    await db.refresh(issue)
    return build_updated_response(IssueResponse.from_model(issue), resource_name="Issue")


@router.delete("/issues/{issue_id}", response_model=APIResponse)
async def delete_issue(issue_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Issue).where(Issue.id == issue_id, Issue.deleted_at.is_(None)))
    issue = result.scalar_one_or_none()
    if issue is None:
        raise NotFoundError("Issue", str(issue_id))

    project = await _get_project_or_404(db, issue.project_id)
    await _require_project_access(db, project, user, permission="delete")

    issue.deleted_at = _now_utc()
    issue.deleted_by_id = getattr(user, "id", None)
    issue.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=issue.project_id,
        user=user,
        activity_type="delete_issue",
        entity_type="issue",
        entity_id=issue.id,
        entity_ref=issue.ref,
        summary=f"Deleted issue IS-{issue.ref}: {issue.subject}",
    )

    await _update_project_stats(db, issue.project_id)
    if issue.milestone_id:
        await _update_milestone_stats(db, issue.milestone_id)
    
    await db.commit()
    return build_deleted_response(resource_name="Issue")


@router.post("/issues/{issue_id}/comments", response_model=APIResponse)
async def create_issue_comment(issue_id: UUID, payload: IssueCommentCreate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Issue).where(Issue.id == issue_id, Issue.deleted_at.is_(None)))
    issue = result.scalar_one_or_none()
    if issue is None:
        raise NotFoundError("Issue", str(issue_id))

    project = await _get_project_or_404(db, issue.project_id)
    await _require_project_access(db, project, user, permission="comment")

    comment = IssueComment(
        issue_id=issue_id,
        author_id=getattr(user, "id", None),
        content=payload.content,
        mentions=payload.mentions,
        attachments=payload.attachments,
    )
    db.add(comment)

    await db.flush()

    await _log_activity(
        db,
        project_id=issue.project_id,
        user=user,
        activity_type="create_issue_comment",
        entity_type="issue_comment",
        entity_id=comment.id,
        summary=f"Commented on issue IS-{issue.ref}",
        details={"issue_id": str(issue.id), "issue_ref": issue.ref},
    )

    await db.commit()
    await db.refresh(comment)
    return build_created_response(IssueCommentResponse.model_validate(comment), resource_name="Issue comment")


@router.get("/issues/{issue_id}/comments", response_model=APIResponse)
async def list_issue_comments(issue_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(Issue).where(Issue.id == issue_id, Issue.deleted_at.is_(None)))
    issue = result.scalar_one_or_none()
    if issue is None:
        raise NotFoundError("Issue", str(issue_id))

    project = await _get_project_or_404(db, issue.project_id)
    await _require_project_access(db, project, user, permission="read")

    rows = (
        (
            await db.execute(
                select(IssueComment)
                .where(IssueComment.issue_id == issue_id)
                .order_by(IssueComment.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    data = [IssueCommentResponse.model_validate(c) for c in rows]
    return APIResponse(success=True, message=None, data=data)


# =============================================================================
# Wiki pages
# =============================================================================


@router.post("/wiki-pages", response_model=APIResponse)
async def create_wiki_page(payload: WikiPageCreate, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, payload.project_id)
    await _require_project_access(db, project, user, permission="edit")

    slug = slugify(payload.title)
    if not slug:
        raise ConflictError("Wiki page slug could not be generated")

    existing = await db.execute(
        select(WikiPage).where(
            WikiPage.project_id == payload.project_id,
            WikiPage.slug == slug,
            WikiPage.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Wiki page slug already exists")

    if payload.parent_id is not None:
        parent_result = await db.execute(
            select(WikiPage).where(
                WikiPage.id == payload.parent_id,
                WikiPage.project_id == payload.project_id,
                WikiPage.deleted_at.is_(None),
            )
        )
        if parent_result.scalar_one_or_none() is None:
            raise NotFoundError("WikiPage", str(payload.parent_id))

    page = WikiPage(
        project_id=payload.project_id,
        title=payload.title,
        slug=slug,
        content=payload.content,
        page_type=payload.page_type,
        parent_id=payload.parent_id,
        order=payload.order,
        owner_id=getattr(user, "id", None),
        created_by_id=getattr(user, "id", None),
        updated_by_id=getattr(user, "id", None),
    )
    db.add(page)

    await db.flush()

    await _log_activity(
        db,
        project_id=payload.project_id,
        user=user,
        activity_type="create_wiki_page",
        entity_type="wiki_page",
        entity_id=page.id,
        summary=f"Created wiki page: {page.title}",
    )

    await db.commit()
    await db.refresh(page)
    return build_created_response(WikiPageResponse.from_model(page), resource_name="Wiki page")


@router.get("/projects/{project_id}/wiki-pages", response_model=APIResponse)
async def list_wiki_pages(project_id: UUID, db: DBSession, user: CurrentUser):
    project = await _get_project_or_404(db, project_id)
    await _require_project_access(db, project, user, permission="read")

    rows = (
        (
            await db.execute(
                select(WikiPage)
                .where(WikiPage.project_id == project_id, WikiPage.deleted_at.is_(None))
                .order_by(WikiPage.order.asc(), WikiPage.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    data = [WikiPageResponse.from_model(p) for p in rows]
    return APIResponse(success=True, message=None, data=data)


@router.patch("/wiki-pages/{page_id}", response_model=APIResponse)
async def update_wiki_page(page_id: UUID, payload: WikiPageUpdate, db: DBSession, user: CurrentUser):
    result = await db.execute(select(WikiPage).where(WikiPage.id == page_id, WikiPage.deleted_at.is_(None)))
    page = result.scalar_one_or_none()
    if page is None:
        raise NotFoundError("WikiPage", str(page_id))

    project = await _get_project_or_404(db, page.project_id)
    await _require_project_access(db, project, user, permission="edit")

    bump_version = False

    if payload.title is not None:
        new_slug = slugify(payload.title)
        if not new_slug:
            raise ConflictError("Wiki page slug could not be generated")
        if new_slug != page.slug:
            existing = await db.execute(
                select(WikiPage).where(
                    WikiPage.project_id == page.project_id,
                    WikiPage.slug == new_slug,
                    WikiPage.id != page.id,
                    WikiPage.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError("Wiki page slug already exists")
        page.title = payload.title
        page.slug = new_slug
        bump_version = True

    if payload.content is not None:
        page.content = payload.content
        bump_version = True

    if payload.page_type is not None:
        page.page_type = payload.page_type
        bump_version = True

    if payload.parent_id is not None:
        parent_result = await db.execute(
            select(WikiPage).where(
                WikiPage.id == payload.parent_id,
                WikiPage.project_id == page.project_id,
                WikiPage.deleted_at.is_(None),
            )
        )
        if parent_result.scalar_one_or_none() is None:
            raise NotFoundError("WikiPage", str(payload.parent_id))
        page.parent_id = payload.parent_id

    if payload.order is not None:
        page.order = payload.order

    if bump_version:
        page.version = int(page.version or 1) + 1

    page.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=page.project_id,
        user=user,
        activity_type="update_wiki_page",
        entity_type="wiki_page",
        entity_id=page.id,
        summary=f"Updated wiki page: {page.title}",
    )

    await db.commit()
    await db.refresh(page)
    return build_updated_response(WikiPageResponse.from_model(page), resource_name="Wiki page")


@router.delete("/wiki-pages/{page_id}", response_model=APIResponse)
async def delete_wiki_page(page_id: UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(select(WikiPage).where(WikiPage.id == page_id, WikiPage.deleted_at.is_(None)))
    page = result.scalar_one_or_none()
    if page is None:
        raise NotFoundError("WikiPage", str(page_id))

    project = await _get_project_or_404(db, page.project_id)
    await _require_project_access(db, project, user, permission="delete")

    page.deleted_at = _now_utc()
    page.deleted_by_id = getattr(user, "id", None)
    page.updated_by_id = getattr(user, "id", None)

    await _log_activity(
        db,
        project_id=page.project_id,
        user=user,
        activity_type="delete_wiki_page",
        entity_type="wiki_page",
        entity_id=page.id,
        summary=f"Deleted wiki page: {page.title}",
    )

    await db.commit()
    return build_deleted_response(resource_name="Wiki page")

"""
Audit Log API endpoints.

Provides read-only access to audit trails with:
- Comprehensive filtering
- Entity-based queries
- User activity tracking
- Export capabilities
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import DBSession, CurrentUser, RoleChecker
from sensei.api.exceptions import NotFoundError, ForbiddenError
from sensei.api.utils import (
    build_response,
    build_paginated_response,
    APIResponse,
    PaginatedResponse,
)
from sensei.models.audit_log import AuditLog, AuditAction


router = APIRouter(
    dependencies=[Depends(RoleChecker(["admin", "auditor", "gm", "exec"]))],
)


# =============================================================================
# Schemas
# =============================================================================


class AuditLogResponse(BaseModel):
    """Response schema for an audit log entry."""

    id: UUID
    created_at: datetime
    entity_type: str
    entity_id: UUID
    action: str
    user_id: UUID | None
    user_email: str | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    old_values: dict | None
    new_values: dict | None
    changed_fields: list[str] | None
    description: str | None
    extra_data: dict | None
    old_status: str | None
    new_status: str | None

    model_config = ConfigDict(from_attributes=True)


class AuditSummary(BaseModel):
    """Summary statistics for audit logs."""

    total_entries: int
    actions_by_type: dict[str, int]
    entities_by_type: dict[str, int]
    top_users: list[dict[str, Any]]
    recent_activity_count: int


# =============================================================================
# Audit Log Endpoints
# =============================================================================


@router.get("/{log_id}", response_model=None)
async def get_audit_log(
    log_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[dict[str, Any]]:
    """Get a specific audit log entry."""
    query = select(AuditLog).where(AuditLog.id == log_id)
    result = await db.execute(query)
    log = result.scalar_one_or_none()

    if not log:
        raise NotFoundError("Audit log entry")

    return build_response(
        data=AuditLogResponse.model_validate(log),
        message="Audit log entry retrieved successfully",
    )


@router.get("", response_model=None)
async def list_audit_logs(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    action: AuditAction | None = Query(None, description="Filter by action type"),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter to date"),
    search: str | None = Query(None, description="Search in description/user email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    List audit log entries with filtering.
    
    Supports filtering by entity, action type, user, and date range.
    """
    conditions = []

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)

    if action:
        conditions.append(AuditLog.action == action.value)

    if user_id:
        conditions.append(AuditLog.user_id == user_id)

    if start_date:
        conditions.append(AuditLog.created_at >= start_date)

    if end_date:
        conditions.append(AuditLog.created_at <= end_date)

    if search:
        search_filter = or_(
            AuditLog.description.ilike(f"%{search}%"),
            AuditLog.user_email.ilike(f"%{search}%"),
            AuditLog.entity_type.ilike(f"%{search}%"),
        )
        conditions.append(search_filter)

    # Count
    count_query = select(func.count(AuditLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if conditions:
        data_query = data_query.where(and_(*conditions))
    data_query = data_query.offset((page - 1) * page_size).limit(page_size)
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=None)
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    action: AuditAction | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get the complete audit trail for a specific entity.
    
    Shows all changes made to the entity over time.
    """
    conditions = [
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id,
    ]

    if action:
        conditions.append(AuditLog.action == action.value)

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/user/{user_id}", response_model=None)
async def get_user_audit_trail(
    user_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    action: AuditAction | None = Query(None),
    entity_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get audit trail for a specific user.
    
    Shows all actions performed by the user.
    """
    conditions = [AuditLog.user_id == user_id]

    if action:
        conditions.append(AuditLog.action == action.value)

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/my-activity", response_model=None)
async def get_my_activity(
    db: DBSession,
    current_user: CurrentUser,
    action: AuditAction | None = Query(None),
    entity_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get audit trail for the current user.
    
    Shows all actions performed by the logged-in user.
    """
    conditions = [AuditLog.user_id == current_user.id]

    if action:
        conditions.append(AuditLog.action == action.value)

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/actions/{action_type}", response_model=None)
async def get_logs_by_action(
    action_type: AuditAction,
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get audit logs filtered by action type.
    
    Useful for tracking specific types of operations (creates, deletes, etc.).
    """
    conditions = [AuditLog.action == action_type.value]

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    if start_date:
        conditions.append(AuditLog.created_at >= start_date)

    if end_date:
        conditions.append(AuditLog.created_at <= end_date)

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/status-changes", response_model=None)
async def get_status_changes(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str | None = Query(None),
    old_status: str | None = Query(None),
    new_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get audit logs for status changes.
    
    Tracks status transitions for workflow analysis.
    """
    conditions = [AuditLog.action == AuditAction.STATUS_CHANGE.value]

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    if old_status:
        conditions.append(AuditLog.old_status == old_status)

    if new_status:
        conditions.append(AuditLog.new_status == new_status)

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=None)
async def get_audit_summary(
    db: DBSession,
    current_user: CurrentUser,
    days: int = Query(7, ge=1, le=365, description="Number of days to include"),
) -> APIResponse[dict[str, Any]]:
    """
    Get summary statistics for audit logs.
    
    Provides an overview of system activity.
    """
    from datetime import timedelta

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Total count
    total_query = select(func.count(AuditLog.id)).where(
        AuditLog.created_at >= cutoff_date
    )
    total_result = await db.execute(total_query)
    total_entries = total_result.scalar_one()

    # Actions by type
    actions_query = (
        select(AuditLog.action, func.count(AuditLog.id).label("count"))
        .where(AuditLog.created_at >= cutoff_date)
        .group_by(AuditLog.action)
    )
    actions_result = await db.execute(actions_query)
    actions_by_type = {row[0]: row[1] for row in actions_result.all()}

    # Entities by type
    entities_query = (
        select(AuditLog.entity_type, func.count(AuditLog.id).label("count"))
        .where(AuditLog.created_at >= cutoff_date)
        .group_by(AuditLog.entity_type)
    )
    entities_result = await db.execute(entities_query)
    entities_by_type = {row[0]: row[1] for row in entities_result.all()}

    # Top users
    users_query = (
        select(
            AuditLog.user_id,
            AuditLog.user_email,
            func.count(AuditLog.id).label("count"),
        )
        .where(
            and_(
                AuditLog.created_at >= cutoff_date,
                AuditLog.user_id.isnot(None),
            )
        )
        .group_by(AuditLog.user_id, AuditLog.user_email)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    users_result = await db.execute(users_query)
    top_users = [
        {"user_id": str(row[0]), "email": row[1], "count": row[2]}
        for row in users_result.all()
    ]

    # Recent activity (last 24 hours)
    recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_query = select(func.count(AuditLog.id)).where(
        AuditLog.created_at >= recent_cutoff
    )
    recent_result = await db.execute(recent_query)
    recent_activity = recent_result.scalar_one()

    summary = AuditSummary(
        total_entries=total_entries,
        actions_by_type=actions_by_type,
        entities_by_type=entities_by_type,
        top_users=top_users,
        recent_activity_count=recent_activity,
    )

    return build_response(
        data=summary,
        message=f"Audit summary for last {days} days",
    )


@router.get("/recent", response_model=None)
async def get_recent_activity(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
) -> APIResponse[dict[str, Any]]:
    """
    Get the most recent audit log entries.
    
    Quick view of latest system activity.
    """
    query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return build_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        message=f"Found {len(logs)} recent audit log entries",
    )


@router.get("/security", response_model=None)
async def get_security_events(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get security-related audit events.
    
    Includes logins, logouts, failed logins, password changes, and permission changes.
    """
    security_actions = [
        AuditAction.LOGIN.value,
        AuditAction.LOGOUT.value,
        AuditAction.FAILED_LOGIN.value,
        AuditAction.PASSWORD_CHANGE.value,
        AuditAction.PERMISSION_CHANGE.value,
    ]

    conditions = [AuditLog.action.in_(security_actions)]

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/deletions", response_model=None)
async def get_deletion_events(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str | None = Query(None),
    include_soft_deletes: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[dict[str, Any]]:
    """
    Get deletion events.
    
    Useful for data recovery and compliance auditing.
    """
    delete_actions = [AuditAction.DELETE.value]
    if include_soft_deletes:
        delete_actions.append(AuditAction.SOFT_DELETE.value)

    conditions: list[Any] = [AuditLog.action.in_(delete_actions)]

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)

    # Count
    count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(AuditLog)
        .where(and_(*conditions))
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    logs = data_result.scalars().all()

    return build_paginated_response(
        data=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )

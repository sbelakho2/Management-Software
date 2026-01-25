"""A3 Problem Solving Endpoints.

Provides CRUD and workflow operations for:
- A3 documents (problem solving, proposals, status reports)
- A3 sections (structured content)

Implements A3 problem-solving methodology following Lean/TPS principles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.core.storage import generate_presigned_url
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_response,
    build_updated_response,
    escape_like_pattern,
)
from sensei.models.a3 import (
    A3,
    A3Section,
    A3Type,
    A3Status,
    A3Priority,
    A3SectionType,
    A3_SECTION_TEMPLATES,
)
from sensei.services.ops.a3_reasoning_gates import (
    GateSeverity,
    build_gate_payload,
    evaluate_a3_section_update,
)

AllowA3Module = deps.require_role(
    "ops",
    "quality",
    "supervisor",
    "team_lead",
    "engineering",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "ops",
                    "quality",
                    "supervisor",
                    "team_lead",
                    "engineering",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)


# =============================================================================
# Utility helpers
# =============================================================================


def _now_utc() -> datetime:
    """Get current UTC datetime for consistency with model timestamps."""
    from datetime import timezone
    return datetime.now(timezone.utc)


def _parse_enum(enum_cls: Any, value: Any, field_name: str):
    """Parse string value to enum."""
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
# A3 Schemas
# =============================================================================


class A3Create(BaseModel):
    """Schema for creating an A3 document."""

    a3_number: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    a3_type: A3Type = A3Type.PROBLEM_SOLVING
    related_entity_type: Optional[str] = Field(default=None, max_length=50)
    related_entity_id: Optional[UUID] = None
    sponsor_id: Optional[UUID] = None
    coach_id: Optional[UUID] = None
    team_members: Optional[list[UUID]] = None
    target_completion_date: Optional[datetime] = None
    department: Optional[str] = Field(default=None, max_length=100)
    area: Optional[str] = Field(default=None, max_length=100)
    priority: A3Priority = A3Priority.MEDIUM
    summary: Optional[str] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    create_default_sections: bool = True

    @field_validator("a3_type", mode="before")
    @classmethod
    def validate_a3_type(cls, v):
        return _parse_enum(A3Type, v, "a3_type")

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v):
        return _parse_enum(A3Priority, v, "priority")


class A3Update(BaseModel):
    """Schema for updating an A3 document."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sponsor_id: Optional[UUID] = None
    coach_id: Optional[UUID] = None
    team_members: Optional[list[UUID]] = None
    target_completion_date: Optional[datetime] = None
    department: Optional[str] = Field(default=None, max_length=100)
    area: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[A3Priority] = None
    summary: Optional[str] = None
    tags: Optional[list[str]] = None
    is_yokoten_candidate: Optional[bool] = None
    yokoten_areas: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    lessons_learned: Optional[str] = None

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v):
        return _parse_enum(A3Priority, v, "priority")


class A3SectionResponse(BaseModel):
    """Response schema for A3 section."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    a3_id: UUID
    section_type: str
    section_name: str
    section_order: int
    content: Optional[str]
    structured_content: Optional[dict[str, Any]]
    is_complete: bool
    completed_at: Optional[datetime]
    completed_by_id: Optional[UUID]
    guidance: Optional[str]
    attachments: Optional[list[Any]]
    comments: Optional[list[Any]]
    version: int
    created_at: datetime
    updated_at: datetime


class A3Response(BaseModel):
    """Response schema for A3 document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    a3_number: str
    title: str
    a3_type: str
    status: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[UUID]
    author_id: Optional[UUID]
    sponsor_id: Optional[UUID]
    coach_id: Optional[UUID]
    team_members: Optional[list[UUID]]
    started_date: Optional[datetime]
    target_completion_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    last_review_date: Optional[datetime]
    review_notes: Optional[str]
    approved_by_id: Optional[UUID]
    approved_date: Optional[datetime]
    progress_percentage: int
    version: int
    department: Optional[str]
    area: Optional[str]
    priority: str
    summary: Optional[str]
    lessons_learned: Optional[str]
    is_yokoten_candidate: bool
    yokoten_areas: Optional[list[str]]
    tags: Optional[list[str]]
    custom_fields: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    is_open: Optional[bool] = None
    is_overdue: Optional[bool] = None
    sections: Optional[list[A3SectionResponse]] = None


class A3ReviewData(BaseModel):
    """Data for reviewing an A3."""

    review_notes: Optional[str] = None


class A3ApprovalData(BaseModel):
    """Data for approving an A3."""

    notes: Optional[str] = None


# =============================================================================
# A3 Section Schemas
# =============================================================================


class SectionCreate(BaseModel):
    """Schema for creating an A3 section."""

    section_type: A3SectionType = A3SectionType.CUSTOM
    section_name: str = Field(..., min_length=1, max_length=100)
    content: Optional[str] = None
    structured_content: Optional[dict[str, Any]] = None
    guidance: Optional[str] = None

    @field_validator("section_type", mode="before")
    @classmethod
    def validate_section_type(cls, v):
        return _parse_enum(A3SectionType, v, "section_type")


class SectionUpdate(BaseModel):
    """Schema for updating an A3 section."""

    section_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    content: Optional[str] = None
    structured_content: Optional[dict[str, Any]] = None
    guidance: Optional[str] = None
    attachments: Optional[list[Any]] = None


class SectionComplete(BaseModel):
    """Schema for marking a section complete."""

    notes: Optional[str] = None


class SectionComment(BaseModel):
    """Schema for adding a comment to a section."""

    comment: str = Field(..., min_length=1)


# =============================================================================
# A3 CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=APIResponse[A3Response],
    status_code=201,
    summary="Create A3 document",
    description="Create a new A3 problem-solving document.",
)
async def create_a3(
    data: A3Create,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    # Check for duplicate a3_number
    stmt = select(A3).where(
        and_(
            A3.a3_number == data.a3_number,
            A3.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"A3 with number '{data.a3_number}' already exists")

    a3 = A3(
        a3_number=data.a3_number,
        title=data.title,
        a3_type=data.a3_type.value if isinstance(data.a3_type, A3Type) else data.a3_type,
        status=A3Status.DRAFT.value,
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
        author_id=current_user.id,
        sponsor_id=data.sponsor_id,
        coach_id=data.coach_id,
        team_members=data.team_members,
        target_completion_date=data.target_completion_date,
        department=data.department,
        area=data.area,
        priority=data.priority.value if isinstance(data.priority, A3Priority) else data.priority,
        summary=data.summary,
        tags=data.tags,
        custom_fields=data.custom_fields,
        created_by_id=current_user.id,
    )
    db.add(a3)
    await db.flush()
    await db.refresh(a3)

    # Create default sections if requested
    if data.create_default_sections:
        a3_type_value = data.a3_type.value if isinstance(data.a3_type, A3Type) else data.a3_type
        templates = A3_SECTION_TEMPLATES.get(a3_type_value, [])
        for idx, template in enumerate(templates):
            section = A3Section(
                a3_id=a3.id,
                section_type=template["type"],
                section_name=template["name"],
                section_order=idx + 1,
                guidance=template.get("guidance"),
            )
            db.add(section)
        await db.flush()
        await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_created_response(data=response, resource_name="A3 document")


@router.get(
    "/{a3_id}",
    response_model=APIResponse[A3Response],
    summary="Get A3 document",
    description="Get an A3 document by ID.",
)
async def get_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response)


@router.get(
    "",
    response_model=PaginatedResponse[A3Response],
    summary="List A3 documents",
    description="List A3 documents with filtering and pagination.",
)
async def list_a3s(
    db: DBSession,
    current_user: CurrentUser,
    a3_type: Optional[A3Type] = Query(default=None),
    status: Optional[A3Status] = Query(default=None),
    priority: Optional[A3Priority] = Query(default=None),
    author_id: Optional[UUID] = Query(default=None),
    department: Optional[str] = Query(default=None),
    is_open: Optional[bool] = Query(default=None),
    is_overdue: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[A3Response]:
    base_conditions: list[Any] = [A3.deleted_at.is_(None)]

    if a3_type and isinstance(a3_type, A3Type):
        base_conditions.append(A3.a3_type == a3_type.value)
    if status and isinstance(status, A3Status):
        base_conditions.append(A3.status == status.value)
    if priority and isinstance(priority, A3Priority):
        base_conditions.append(A3.priority == priority.value)
    if author_id is not None and isinstance(author_id, UUID):
        base_conditions.append(A3.author_id == author_id)
    if department and isinstance(department, str):
        base_conditions.append(A3.department == department)
    if is_open is True:
        base_conditions.append(
            A3.status.notin_([A3Status.CLOSED.value, A3Status.CANCELLED.value])
        )
    elif is_open is False:
        base_conditions.append(
            A3.status.in_([A3Status.CLOSED.value, A3Status.CANCELLED.value])
        )
    if is_overdue is True:
        from datetime import timezone
        base_conditions.append(A3.target_completion_date < datetime.now(timezone.utc))
        base_conditions.append(
            A3.status.notin_([A3Status.CLOSED.value, A3Status.CANCELLED.value])
        )
    if search and isinstance(search, str):
        escaped_search = escape_like_pattern(search)
        search_filter = or_(
            A3.title.ilike(f"%{escaped_search}%"),
            A3.a3_number.ilike(f"%{escaped_search}%"),
            A3.summary.ilike(f"%{escaped_search}%"),
        )
        base_conditions.append(search_filter)

    count_stmt = select(func.count(A3.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(A3)
        .where(and_(*base_conditions))
        .options(selectinload(A3.sections))
        .order_by(A3.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    a3s = data_result.scalars().all()

    items = []
    for a3 in a3s:
        response = A3Response.model_validate(a3)
        response.is_open = a3.is_open
        response.is_overdue = a3.is_overdue
        if a3.sections:
            response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{a3_id}",
    response_model=APIResponse[A3Response],
    summary="Update A3 document",
    description="Update an A3 document.",
)
async def update_a3(
    a3_id: UUID,
    data: A3Update,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "priority" and isinstance(value, A3Priority):
            value = value.value
        setattr(a3, field, value)

    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_updated_response(response, "A3 document")


@router.delete(
    "/{a3_id}",
    response_model=APIResponse[None],
    summary="Delete A3 document",
    description="Soft delete an A3 document.",
)
async def delete_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    a3.deleted_at = _now_utc()
    a3.deleted_by_id = current_user.id
    await db.flush()

    return build_deleted_response("A3 document")


# =============================================================================
# A3 Workflow Endpoints
# =============================================================================


@router.post(
    "/{a3_id}/start",
    response_model=APIResponse[A3Response],
    summary="Start A3",
    description="Start working on an A3 (move from draft to in progress).",
)
async def start_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status != A3Status.DRAFT.value:
        raise ConflictError(f"Cannot start A3 in '{a3.status}' status")

    a3.status = A3Status.IN_PROGRESS.value
    a3.started_date = _now_utc()
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 started")


@router.post(
    "/{a3_id}/submit-for-review",
    response_model=APIResponse[A3Response],
    summary="Submit for review",
    description="Submit A3 for review.",
)
async def submit_for_review(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status not in [A3Status.DRAFT.value, A3Status.IN_PROGRESS.value]:
        raise ConflictError(f"Cannot submit A3 in '{a3.status}' status for review")

    a3.status = A3Status.REVIEW.value
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 submitted for review")


@router.post(
    "/{a3_id}/submit",
    response_model=APIResponse[A3Response],
    summary="Submit A3 (frontend alias)",
    description="Frontend compatibility endpoint for submitting an A3.",
)
async def submit_a3_alias(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    """Alias for submit_for_review."""
    return await submit_for_review(a3_id=a3_id, db=db, current_user=current_user)


@router.get(
    "/{a3_id}/export",
    response_model=APIResponse[dict],
    summary="Export A3",
    description="Export A3 to PDF/Excel.",
)
async def export_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    format: str = Query(default="pdf"),
) -> APIResponse[dict]:
    """Export A3 data."""
    if format.lower() != "pdf":
        raise ConflictError("Only PDF export is supported at this time")

    stmt = select(A3).where(and_(A3.id == a3_id, A3.deleted_at.is_(None)))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if not a3.pdf_storage_key:
        raise ConflictError("A3 PDF export is not available yet")

    url = generate_presigned_url(a3.pdf_storage_key)
    if not url:
        raise ConflictError("Failed to generate export URL")

    return build_response(
        data={"url": url},
        message="A3 export ready",
    )


@router.post(
    "/{a3_id}/review",
    response_model=APIResponse[A3Response],
    summary="Review A3",
    description="Add review notes to an A3.",
)
async def review_a3(
    a3_id: UUID,
    data: A3ReviewData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    a3.last_review_date = _now_utc()
    a3.review_notes = data.review_notes
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 reviewed")


@router.post(
    "/{a3_id}/approve",
    response_model=APIResponse[A3Response],
    summary="Approve A3",
    description="Approve an A3 document.",
)
async def approve_a3(
    a3_id: UUID,
    data: A3ApprovalData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status != A3Status.REVIEW.value:
        raise ConflictError(f"Cannot approve A3 in '{a3.status}' status")

    a3.status = A3Status.APPROVED.value
    a3.approved_by_id = current_user.id
    a3.approved_date = _now_utc()
    if data.notes:
        a3.review_notes = data.notes
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 approved")


@router.post(
    "/{a3_id}/reject",
    response_model=APIResponse[A3Response],
    summary="Reject A3",
    description="Reject A3 and return to in progress.",
)
async def reject_a3(
    a3_id: UUID,
    data: A3ReviewData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status != A3Status.REVIEW.value:
        raise ConflictError(f"Cannot reject A3 in '{a3.status}' status")

    a3.status = A3Status.IN_PROGRESS.value
    a3.last_review_date = _now_utc()
    a3.review_notes = data.review_notes
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 returned for revision")


@router.post(
    "/{a3_id}/implement",
    response_model=APIResponse[A3Response],
    summary="Mark as implemented",
    description="Mark approved A3 as implemented.",
)
async def implement_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status != A3Status.APPROVED.value:
        raise ConflictError(f"Cannot implement A3 in '{a3.status}' status")

    a3.status = A3Status.IMPLEMENTED.value
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 implemented")


@router.post(
    "/{a3_id}/close",
    response_model=APIResponse[A3Response],
    summary="Close A3",
    description="Close an A3 document.",
)
async def close_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status in [A3Status.CLOSED.value, A3Status.CANCELLED.value]:
        raise ConflictError(f"A3 is already '{a3.status}'")

    a3.status = A3Status.CLOSED.value
    a3.actual_completion_date = _now_utc()
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 closed")


@router.post(
    "/{a3_id}/cancel",
    response_model=APIResponse[A3Response],
    summary="Cancel A3",
    description="Cancel an A3 document.",
)
async def cancel_a3(
    a3_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    if a3.status in [A3Status.CLOSED.value, A3Status.CANCELLED.value]:
        raise ConflictError(f"A3 is already '{a3.status}'")

    a3.status = A3Status.CANCELLED.value
    a3.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(a3)

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response, "A3 cancelled")


# =============================================================================
# A3 Section Endpoints
# =============================================================================


@router.post(
    "/{a3_id}/sections",
    response_model=APIResponse[A3SectionResponse],
    status_code=201,
    summary="Add section",
    description="Add a new section to an A3.",
)
async def add_section(
    a3_id: UUID,
    data: SectionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3SectionResponse]:
    # Check A3 exists
    a3_stmt = select(A3).where(
        and_(A3.id == a3_id, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    a3_result = await db.execute(a3_stmt)
    a3 = a3_result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 {a3_id} not found")

    # Calculate next order
    max_order = max((s.section_order for s in a3.sections), default=0)

    section = A3Section(
        a3_id=a3_id,
        section_type=(
            data.section_type.value
            if isinstance(data.section_type, A3SectionType)
            else data.section_type
        ),
        section_name=data.section_name,
        section_order=max_order + 1,
        content=data.content,
        structured_content=data.structured_content,
        guidance=data.guidance,
    )
    db.add(section)
    await db.flush()
    await db.refresh(section)

    return build_created_response(
        data=A3SectionResponse.model_validate(section),
        resource_name="A3 section"
    )


@router.patch(
    "/{a3_id}/sections/{section_id}",
    response_model=APIResponse[A3SectionResponse],
    summary="Update section",
    description="Update an A3 section.",
)
async def update_section(
    a3_id: UUID,
    section_id: UUID,
    data: SectionUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3SectionResponse]:
    stmt = select(A3Section).where(
        and_(
            A3Section.id == section_id,
            A3Section.a3_id == a3_id,
        )
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if not section:
        raise NotFoundError(f"Section {section_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)

    issues = evaluate_a3_section_update(
        section_type=section.section_type,
        content=section.content,
        structured_content=section.structured_content,
    )
    if issues:
        gate_payload = build_gate_payload(issues)

        # Persist warnings so the UI can surface them.
        # NOTE: A3Section.structured_content is JSONB, so we can safely attach metadata.
        structured = section.structured_content
        if structured is None:
            structured = {}
        if not isinstance(structured, dict):
            structured = {"_value": structured}
        structured["_reasoning_gate"] = gate_payload
        section.structured_content = structured

        if any(i.severity == GateSeverity.BLOCK for i in issues):
            raise ConflictError(
                "A3 section update blocked by TPS reasoning gates",
                details=gate_payload,
            )

    section.version += 1
    await db.flush()
    await db.refresh(section)

    response_message = "A3 section updated successfully"
    if issues:
        response_message = "A3 section updated successfully (with reasoning warnings)"

    return build_response(
        A3SectionResponse.model_validate(section),
        response_message,
    )


@router.post(
    "/{a3_id}/sections/{section_id}/complete",
    response_model=APIResponse[A3SectionResponse],
    summary="Complete section",
    description="Mark an A3 section as complete.",
)
async def complete_section(
    a3_id: UUID,
    section_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3SectionResponse]:
    stmt = select(A3Section).where(
        and_(
            A3Section.id == section_id,
            A3Section.a3_id == a3_id,
        )
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if not section:
        raise NotFoundError(f"Section {section_id} not found")

    section.is_complete = True
    section.completed_at = _now_utc()
    section.completed_by_id = current_user.id
    await db.flush()
    await db.refresh(section)

    # Update A3 progress
    a3_stmt = select(A3).where(A3.id == a3_id).options(selectinload(A3.sections))
    a3_result = await db.execute(a3_stmt)
    a3 = a3_result.scalar_one_or_none()
    if a3:
        a3.update_progress()
        await db.flush()

    return build_response(
        A3SectionResponse.model_validate(section),
        "Section completed"
    )


@router.post(
    "/{a3_id}/sections/{section_id}/reopen",
    response_model=APIResponse[A3SectionResponse],
    summary="Reopen section",
    description="Reopen a completed A3 section.",
)
async def reopen_section(
    a3_id: UUID,
    section_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3SectionResponse]:
    stmt = select(A3Section).where(
        and_(
            A3Section.id == section_id,
            A3Section.a3_id == a3_id,
        )
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if not section:
        raise NotFoundError(f"Section {section_id} not found")

    section.is_complete = False
    section.completed_at = None
    section.completed_by_id = None
    await db.flush()
    await db.refresh(section)

    # Update A3 progress
    a3_stmt = select(A3).where(A3.id == a3_id).options(selectinload(A3.sections))
    a3_result = await db.execute(a3_stmt)
    a3 = a3_result.scalar_one_or_none()
    if a3:
        a3.update_progress()
        await db.flush()

    return build_response(
        A3SectionResponse.model_validate(section),
        "Section reopened"
    )


@router.post(
    "/{a3_id}/sections/{section_id}/comment",
    response_model=APIResponse[A3SectionResponse],
    summary="Add comment",
    description="Add a comment to an A3 section.",
)
async def add_section_comment(
    a3_id: UUID,
    section_id: UUID,
    data: SectionComment,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3SectionResponse]:
    stmt = select(A3Section).where(
        and_(
            A3Section.id == section_id,
            A3Section.a3_id == a3_id,
        )
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if not section:
        raise NotFoundError(f"Section {section_id} not found")

    comment_entry = {
        "user_id": str(current_user.id),
        "comment": data.comment,
        "timestamp": _now_utc().isoformat(),
    }

    if section.comments is None:
        section.comments = []
    section.comments = section.comments + [comment_entry]

    await db.flush()
    await db.refresh(section)

    return build_response(
        A3SectionResponse.model_validate(section),
        "Comment added"
    )


@router.delete(
    "/{a3_id}/sections/{section_id}",
    response_model=APIResponse[None],
    summary="Delete section",
    description="Delete an A3 section.",
)
async def delete_section(
    a3_id: UUID,
    section_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(A3Section).where(
        and_(
            A3Section.id == section_id,
            A3Section.a3_id == a3_id,
        )
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if not section:
        raise NotFoundError(f"Section {section_id} not found")

    await db.delete(section)
    await db.flush()

    # Update A3 progress
    a3_stmt = select(A3).where(A3.id == a3_id).options(selectinload(A3.sections))
    a3_result = await db.execute(a3_stmt)
    a3 = a3_result.scalar_one_or_none()
    if a3:
        a3.update_progress()
        await db.flush()

    return build_deleted_response("A3 section")


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get(
    "/by-number/{a3_number}",
    response_model=APIResponse[A3Response],
    summary="Get A3 by number",
    description="Get an A3 by its document number.",
)
async def get_a3_by_number(
    a3_number: str,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[A3Response]:
    stmt = select(A3).where(
        and_(A3.a3_number == a3_number, A3.deleted_at.is_(None))
    ).options(selectinload(A3.sections))
    result = await db.execute(stmt)
    a3 = result.scalar_one_or_none()
    if not a3:
        raise NotFoundError(f"A3 with number '{a3_number}' not found")

    response = A3Response.model_validate(a3)
    response.is_open = a3.is_open
    response.is_overdue = a3.is_overdue
    if a3.sections:
        response.sections = [A3SectionResponse.model_validate(s) for s in a3.sections]

    return build_response(response)


@router.get(
    "/my-a3s",
    response_model=PaginatedResponse[A3Response],
    summary="Get my A3s",
    description="Get A3s authored by or assigned to the current user.",
)
async def get_my_a3s(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[A3Response]:
    base_conditions: list[Any] = [
        A3.deleted_at.is_(None),
        or_(
            A3.author_id == current_user.id,
            A3.sponsor_id == current_user.id,
            A3.coach_id == current_user.id,
        ),
    ]

    count_stmt = select(func.count(A3.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(A3)
        .where(and_(*base_conditions))
        .options(selectinload(A3.sections))
        .order_by(A3.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    a3s = data_result.scalars().all()

    items = []
    for a3 in a3s:
        response = A3Response.model_validate(a3)
        response.is_open = a3.is_open
        response.is_overdue = a3.is_overdue
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/pending-review",
    response_model=PaginatedResponse[A3Response],
    summary="Get A3s pending review",
    description="Get A3s that are in review status.",
)
async def get_pending_review(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[A3Response]:
    base_conditions: list[Any] = [
        A3.deleted_at.is_(None),
        A3.status == A3Status.REVIEW.value,
    ]

    count_stmt = select(func.count(A3.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(A3)
        .where(and_(*base_conditions))
        .options(selectinload(A3.sections))
        .order_by(A3.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    a3s = data_result.scalars().all()

    items = []
    for a3 in a3s:
        response = A3Response.model_validate(a3)
        response.is_open = a3.is_open
        response.is_overdue = a3.is_overdue
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )

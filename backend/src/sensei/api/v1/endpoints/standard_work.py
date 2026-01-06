"""Standard Work Endpoints.

Provides CRUD and workflow operations for:
- Standard Work Documents (create, update, version, approve)
- Standard Work Versions (immutable history)
- Document lifecycle management (draft, submit, approve, supersede)

Implements standard work document control following lean manufacturing principles.
"""

from __future__ import annotations

from datetime import datetime, date
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
from sensei.models.standard_work import (
    StandardWork,
    StandardWorkStatus,
    StandardWorkType,
    StandardWorkVersion,
)

router = APIRouter()


# =============================================================================
# Utility helpers
# =============================================================================


def _now_utc() -> datetime:
    """Get current UTC datetime (naive) for consistency with model timestamps."""
    return datetime.utcnow()


def _today() -> date:
    """Get current date for date comparisons."""
    return date.today()


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
# Standard Work Document Schemas
# =============================================================================


class StandardWorkBase(BaseModel):
    document_number: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    document_type: StandardWorkType = StandardWorkType.WORK_INSTRUCTION
    product_id: Optional[int] = Field(default=None, gt=0)
    station_id: Optional[int] = Field(default=None, gt=0)
    content_json: Optional[dict[str, Any]] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    review_date: Optional[date] = None
    requires_training: bool = True
    training_duration_minutes: int = Field(default=30, ge=0)

    @field_validator("document_type", mode="before")
    @classmethod
    def validate_document_type(cls, v):
        return _parse_enum(StandardWorkType, v, "document_type")


class StandardWorkCreate(StandardWorkBase):
    pass


class StandardWorkUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    document_type: Optional[StandardWorkType] = None
    product_id: Optional[int] = Field(default=None, gt=0)
    station_id: Optional[int] = Field(default=None, gt=0)
    content_json: Optional[dict[str, Any]] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    review_date: Optional[date] = None
    requires_training: Optional[bool] = None
    training_duration_minutes: Optional[int] = Field(default=None, ge=0)
    change_summary: Optional[str] = None

    @field_validator("document_type", mode="before")
    @classmethod
    def validate_document_type(cls, v):
        return _parse_enum(StandardWorkType, v, "document_type")


class StandardWorkSubmit(BaseModel):
    notes: Optional[str] = None


class StandardWorkApprove(BaseModel):
    approval_notes: Optional[str] = None


class StandardWorkReject(BaseModel):
    rejection_notes: str = Field(..., min_length=1)


class StandardWorkRevise(BaseModel):
    change_summary: Optional[str] = None


class ContentStep(BaseModel):
    sequence: int = Field(..., ge=1)
    instruction: str = Field(..., min_length=1)
    image_attachment_id: Optional[int] = None
    estimated_time_seconds: Optional[int] = Field(default=None, ge=0)
    safety_notes: Optional[str] = None
    quality_checkpoints: Optional[list[str]] = None
    tools_required: Optional[list[str]] = None
    critical: bool = False


class ContentUpdate(BaseModel):
    steps: Optional[list[ContentStep]] = None
    safety_warnings: Optional[list[str]] = None
    required_ppe: Optional[list[str]] = None
    required_tools: Optional[list[str]] = None
    revision_notes: Optional[str] = None


# =============================================================================
# Standard Work Response Schemas
# =============================================================================


class StandardWorkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_number: str
    title: str
    description: Optional[str]
    version: int
    revision_code: str
    document_type: StandardWorkType
    status: StandardWorkStatus
    product_id: Optional[int]
    station_id: Optional[int]
    content_json: Optional[dict[str, Any]]
    effective_date: Optional[date]
    expiration_date: Optional[date]
    review_date: Optional[date]
    submitted_by_id: Optional[UUID]
    submitted_at: Optional[datetime]
    approved_by_id: Optional[UUID]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    change_summary: Optional[str]
    previous_version_id: Optional[int]
    requires_training: bool
    training_duration_minutes: int
    created_at: datetime
    updated_at: datetime
    # Computed properties (will be set from model)
    full_document_id: Optional[str] = None
    is_current: Optional[bool] = None
    is_expired: Optional[bool] = None
    needs_review: Optional[bool] = None
    step_count: Optional[int] = None


class StandardWorkVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    standard_work_id: int
    version: int
    revision_code: str
    content_json: Optional[dict[str, Any]]
    change_summary: Optional[str]
    created_by_id: UUID
    created_at: datetime


# =============================================================================
# Standard Work CRUD Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=APIResponse[StandardWorkResponse],
    status_code=201,
    summary="Create standard work document",
    description="Create a new standard work document in draft status.",
)
async def create_standard_work(
    data: StandardWorkCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    # Check for duplicate document number + version
    stmt = select(StandardWork).where(
        and_(
            StandardWork.document_number == data.document_number,
            StandardWork.version == 1,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"Standard work document '{data.document_number}' version 1 already exists"
        )

    # Create the document
    standard_work = StandardWork(
        document_number=data.document_number,
        title=data.title,
        description=data.description,
        version=1,
        revision_code="A",
        document_type=data.document_type,
        status=StandardWorkStatus.DRAFT,
        product_id=data.product_id,
        station_id=data.station_id,
        content_json=data.content_json,
        effective_date=data.effective_date,
        expiration_date=data.expiration_date,
        review_date=data.review_date,
        requires_training=data.requires_training,
        training_duration_minutes=data.training_duration_minutes,
        created_by_id=current_user.id,
    )
    db.add(standard_work)
    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_created_response(data=response, resource_name="Standard work document")


@router.get(
    "/{standard_work_id}",
    response_model=APIResponse[StandardWorkResponse],
    summary="Get standard work document",
    description="Get a standard work document by ID.",
)
async def get_standard_work(
    standard_work_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_response(response)


@router.get(
    "/",
    response_model=PaginatedResponse[StandardWorkResponse],
    summary="List standard work documents",
    description="List standard work documents with filtering and pagination.",
)
async def list_standard_works(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[StandardWorkStatus] = Query(default=None),
    document_type: Optional[StandardWorkType] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    station_id: Optional[int] = Query(default=None),
    needs_review: Optional[bool] = Query(default=None),
    is_expired: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkResponse]:
    # Build base query
    base_conditions = [StandardWork.is_deleted == False]

    # Apply filters
    if status and isinstance(status, StandardWorkStatus):
        base_conditions.append(StandardWork.status == status)
    if document_type and isinstance(document_type, StandardWorkType):
        base_conditions.append(StandardWork.document_type == document_type)
    if product_id is not None and isinstance(product_id, int):
        base_conditions.append(StandardWork.product_id == product_id)
    if station_id is not None and isinstance(station_id, int):
        base_conditions.append(StandardWork.station_id == station_id)
    if search and isinstance(search, str):
        search_filter = or_(
            StandardWork.document_number.ilike(f"%{search}%"),
            StandardWork.title.ilike(f"%{search}%"),
            StandardWork.description.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    # Date-based filters (computed at query time)
    today = _today()
    if needs_review is True:
        base_conditions.append(StandardWork.review_date <= today)
    elif needs_review is False:
        base_conditions.append(
            or_(
                StandardWork.review_date == None,
                StandardWork.review_date > today,
            )
        )
    if is_expired is True:
        base_conditions.append(StandardWork.expiration_date < today)
    elif is_expired is False:
        base_conditions.append(
            or_(
                StandardWork.expiration_date == None,
                StandardWork.expiration_date >= today,
            )
        )

    # Count query
    count_stmt = select(func.count(StandardWork.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWork)
        .where(and_(*base_conditions))
        .order_by(StandardWork.document_number, StandardWork.version.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    standard_works = data_result.scalars().all()

    # Build response items with computed properties
    items = []
    for sw in standard_works:
        response = StandardWorkResponse.model_validate(sw)
        response.full_document_id = sw.full_document_id
        response.is_current = sw.is_current
        response.is_expired = sw.is_expired
        response.needs_review = sw.needs_review
        response.step_count = sw.step_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{standard_work_id}",
    response_model=APIResponse[StandardWorkResponse],
    summary="Update standard work document",
    description="Update a standard work document. Only draft documents can be edited.",
)
async def update_standard_work(
    standard_work_id: int,
    data: StandardWorkUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    # Only drafts can be edited
    if standard_work.status != StandardWorkStatus.DRAFT:
        raise ConflictError(
            f"Cannot edit document in '{standard_work.status.value}' status. "
            "Only draft documents can be edited."
        )

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(standard_work, field, value)

    standard_work.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_updated_response(response, "Standard work document updated")


@router.delete(
    "/{standard_work_id}",
    response_model=APIResponse[None],
    summary="Delete standard work document",
    description="Soft delete a standard work document.",
)
async def delete_standard_work(
    standard_work_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    # Soft delete
    standard_work.is_deleted = True
    standard_work.deleted_at = _now_utc()
    standard_work.deleted_by_id = current_user.id
    await db.flush()

    return build_deleted_response("Standard work document deleted")


# =============================================================================
# Standard Work Workflow Endpoints
# =============================================================================


@router.post(
    "/{standard_work_id}/submit",
    response_model=APIResponse[StandardWorkResponse],
    summary="Submit for approval",
    description="Submit a draft standard work document for approval.",
)
async def submit_for_approval(
    standard_work_id: int,
    data: StandardWorkSubmit,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    if not standard_work.can_submit_for_approval():
        raise ConflictError(
            f"Cannot submit document in '{standard_work.status.value}' status for approval"
        )

    standard_work.status = StandardWorkStatus.PENDING_APPROVAL
    standard_work.submitted_by_id = current_user.id
    standard_work.submitted_at = _now_utc()
    standard_work.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_response(response, "Standard work document submitted for approval")


@router.post(
    "/{standard_work_id}/approve",
    response_model=APIResponse[StandardWorkResponse],
    summary="Approve document",
    description="Approve a pending standard work document.",
)
async def approve_standard_work(
    standard_work_id: int,
    data: StandardWorkApprove,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    if not standard_work.can_approve():
        raise ConflictError(
            f"Cannot approve document in '{standard_work.status.value}' status"
        )

    # Supersede previous approved versions
    prev_stmt = select(StandardWork).where(
        and_(
            StandardWork.document_number == standard_work.document_number,
            StandardWork.status == StandardWorkStatus.APPROVED,
            StandardWork.id != standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    prev_result = await db.execute(prev_stmt)
    previous_versions = prev_result.scalars().all()
    for prev in previous_versions:
        prev.status = StandardWorkStatus.SUPERSEDED
        prev.updated_by_id = current_user.id

    # Approve current document
    standard_work.status = StandardWorkStatus.APPROVED
    standard_work.approved_by_id = current_user.id
    standard_work.approved_at = _now_utc()
    standard_work.approval_notes = data.approval_notes
    standard_work.updated_by_id = current_user.id

    # Create version snapshot
    version = StandardWorkVersion(
        standard_work_id=standard_work.id,
        version=standard_work.version,
        revision_code=standard_work.revision_code,
        content_json=standard_work.content_json,
        change_summary=standard_work.change_summary,
        created_by_id=current_user.id,
    )
    db.add(version)

    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_response(response, "Standard work document approved")


@router.post(
    "/{standard_work_id}/reject",
    response_model=APIResponse[StandardWorkResponse],
    summary="Reject document",
    description="Reject a pending standard work document back to draft.",
)
async def reject_standard_work(
    standard_work_id: int,
    data: StandardWorkReject,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    if standard_work.status != StandardWorkStatus.PENDING_APPROVAL:
        raise ConflictError(
            f"Cannot reject document in '{standard_work.status.value}' status. "
            "Only pending approval documents can be rejected."
        )

    standard_work.status = StandardWorkStatus.DRAFT
    standard_work.approval_notes = f"REJECTED: {data.rejection_notes}"
    standard_work.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_response(response, "Standard work document rejected")


@router.post(
    "/{standard_work_id}/revise",
    response_model=APIResponse[StandardWorkResponse],
    summary="Create new revision",
    description="Create a new draft revision of an approved standard work document.",
)
async def create_revision(
    standard_work_id: int,
    data: StandardWorkRevise,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    if standard_work.status != StandardWorkStatus.APPROVED:
        raise ConflictError(
            f"Cannot revise document in '{standard_work.status.value}' status. "
            "Only approved documents can be revised."
        )

    # Check if a draft revision already exists
    draft_stmt = select(StandardWork).where(
        and_(
            StandardWork.document_number == standard_work.document_number,
            StandardWork.status == StandardWorkStatus.DRAFT,
            StandardWork.is_deleted == False,
        )
    )
    draft_result = await db.execute(draft_stmt)
    existing_draft = draft_result.scalar_one_or_none()
    if existing_draft:
        raise ConflictError(
            f"A draft revision already exists for document '{standard_work.document_number}'"
        )

    # Create new version
    new_work = standard_work.create_new_version()
    new_work.change_summary = data.change_summary
    new_work.created_by_id = current_user.id
    db.add(new_work)
    await db.flush()
    await db.refresh(new_work)

    response = StandardWorkResponse.model_validate(new_work)
    response.full_document_id = new_work.full_document_id
    response.is_current = new_work.is_current
    response.is_expired = new_work.is_expired
    response.needs_review = new_work.needs_review
    response.step_count = new_work.step_count

    return build_created_response(data=response, resource_name="New revision")


@router.post(
    "/{standard_work_id}/obsolete",
    response_model=APIResponse[StandardWorkResponse],
    summary="Mark as obsolete",
    description="Mark a standard work document as obsolete.",
)
async def mark_obsolete(
    standard_work_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    if standard_work.status in (StandardWorkStatus.OBSOLETE, StandardWorkStatus.DRAFT):
        raise ConflictError(
            f"Cannot mark document in '{standard_work.status.value}' status as obsolete"
        )

    standard_work.status = StandardWorkStatus.OBSOLETE
    standard_work.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_response(response, "Standard work document marked as obsolete")


# =============================================================================
# Standard Work Content Endpoints
# =============================================================================


@router.patch(
    "/{standard_work_id}/content",
    response_model=APIResponse[StandardWorkResponse],
    summary="Update document content",
    description="Update the content (steps, safety info, etc.) of a draft document.",
)
async def update_content(
    standard_work_id: int,
    data: ContentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkResponse]:
    stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    result = await db.execute(stmt)
    standard_work = result.scalar_one_or_none()
    if not standard_work:
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    if standard_work.status != StandardWorkStatus.DRAFT:
        raise ConflictError(
            f"Cannot update content of document in '{standard_work.status.value}' status"
        )

    # Build content update
    content = standard_work.content_json or {}
    update_data = data.model_dump(exclude_unset=True)

    if "steps" in update_data and update_data["steps"] is not None:
        content["steps"] = [step.model_dump() for step in data.steps]
    for key in ["safety_warnings", "required_ppe", "required_tools", "revision_notes"]:
        if key in update_data:
            content[key] = update_data[key]

    standard_work.content_json = content
    standard_work.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(standard_work)

    response = StandardWorkResponse.model_validate(standard_work)
    response.full_document_id = standard_work.full_document_id
    response.is_current = standard_work.is_current
    response.is_expired = standard_work.is_expired
    response.needs_review = standard_work.needs_review
    response.step_count = standard_work.step_count

    return build_updated_response(response, "Document content updated")


# =============================================================================
# Standard Work Version Endpoints
# =============================================================================


@router.get(
    "/{standard_work_id}/versions",
    response_model=PaginatedResponse[StandardWorkVersionResponse],
    summary="List document versions",
    description="List all version snapshots for a standard work document.",
)
async def list_versions(
    standard_work_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkVersionResponse]:
    # Verify document exists
    check_stmt = select(StandardWork).where(
        and_(
            StandardWork.id == standard_work_id,
            StandardWork.is_deleted == False,
        )
    )
    check_result = await db.execute(check_stmt)
    if not check_result.scalar_one_or_none():
        raise NotFoundError(f"Standard work document {standard_work_id} not found")

    # Count query
    count_stmt = select(func.count(StandardWorkVersion.id)).where(
        StandardWorkVersion.standard_work_id == standard_work_id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWorkVersion)
        .where(StandardWorkVersion.standard_work_id == standard_work_id)
        .order_by(StandardWorkVersion.version.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    versions = data_result.scalars().all()

    items = [StandardWorkVersionResponse.model_validate(v) for v in versions]
    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{standard_work_id}/versions/{version_number}",
    response_model=APIResponse[StandardWorkVersionResponse],
    summary="Get specific version",
    description="Get a specific version snapshot of a standard work document.",
)
async def get_version(
    standard_work_id: int,
    version_number: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StandardWorkVersionResponse]:
    stmt = select(StandardWorkVersion).where(
        and_(
            StandardWorkVersion.standard_work_id == standard_work_id,
            StandardWorkVersion.version == version_number,
        )
    )
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise NotFoundError(
            f"Version {version_number} not found for document {standard_work_id}"
        )

    response = StandardWorkVersionResponse.model_validate(version)
    return build_response(response)


# =============================================================================
# Standard Work Query Endpoints
# =============================================================================


@router.get(
    "/by-document-number/{document_number}",
    response_model=PaginatedResponse[StandardWorkResponse],
    summary="Get by document number",
    description="Get all versions of a document by its document number.",
)
async def get_by_document_number(
    document_number: str,
    db: DBSession,
    current_user: CurrentUser,
    include_all_versions: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkResponse]:
    base_conditions = [
        StandardWork.document_number == document_number,
        StandardWork.is_deleted == False,
    ]

    if not include_all_versions:
        # Only return the current/latest version
        base_conditions.append(StandardWork.status == StandardWorkStatus.APPROVED)

    # Count query
    count_stmt = select(func.count(StandardWork.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWork)
        .where(and_(*base_conditions))
        .order_by(StandardWork.version.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    standard_works = data_result.scalars().all()

    items = []
    for sw in standard_works:
        response = StandardWorkResponse.model_validate(sw)
        response.full_document_id = sw.full_document_id
        response.is_current = sw.is_current
        response.is_expired = sw.is_expired
        response.needs_review = sw.needs_review
        response.step_count = sw.step_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/by-station/{station_id}",
    response_model=PaginatedResponse[StandardWorkResponse],
    summary="Get by station",
    description="Get all approved standard work documents for a station.",
)
async def get_by_station(
    station_id: int,
    db: DBSession,
    current_user: CurrentUser,
    document_type: Optional[StandardWorkType] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkResponse]:
    base_conditions = [
        StandardWork.station_id == station_id,
        StandardWork.status == StandardWorkStatus.APPROVED,
        StandardWork.is_deleted == False,
    ]

    if document_type and isinstance(document_type, StandardWorkType):
        base_conditions.append(StandardWork.document_type == document_type)

    # Count query
    count_stmt = select(func.count(StandardWork.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWork)
        .where(and_(*base_conditions))
        .order_by(StandardWork.document_number)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    standard_works = data_result.scalars().all()

    items = []
    for sw in standard_works:
        response = StandardWorkResponse.model_validate(sw)
        response.full_document_id = sw.full_document_id
        response.is_current = sw.is_current
        response.is_expired = sw.is_expired
        response.needs_review = sw.needs_review
        response.step_count = sw.step_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/by-product/{product_id}",
    response_model=PaginatedResponse[StandardWorkResponse],
    summary="Get by product",
    description="Get all approved standard work documents for a product.",
)
async def get_by_product(
    product_id: int,
    db: DBSession,
    current_user: CurrentUser,
    document_type: Optional[StandardWorkType] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkResponse]:
    base_conditions = [
        StandardWork.product_id == product_id,
        StandardWork.status == StandardWorkStatus.APPROVED,
        StandardWork.is_deleted == False,
    ]

    if document_type and isinstance(document_type, StandardWorkType):
        base_conditions.append(StandardWork.document_type == document_type)

    # Count query
    count_stmt = select(func.count(StandardWork.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWork)
        .where(and_(*base_conditions))
        .order_by(StandardWork.document_number)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    standard_works = data_result.scalars().all()

    items = []
    for sw in standard_works:
        response = StandardWorkResponse.model_validate(sw)
        response.full_document_id = sw.full_document_id
        response.is_current = sw.is_current
        response.is_expired = sw.is_expired
        response.needs_review = sw.needs_review
        response.step_count = sw.step_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/pending-review",
    response_model=PaginatedResponse[StandardWorkResponse],
    summary="Get documents pending review",
    description="Get all approved standard work documents that need periodic review.",
)
async def get_pending_review(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkResponse]:
    today = _today()
    base_conditions = [
        StandardWork.status == StandardWorkStatus.APPROVED,
        StandardWork.review_date <= today,
        StandardWork.is_deleted == False,
    ]

    # Count query
    count_stmt = select(func.count(StandardWork.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWork)
        .where(and_(*base_conditions))
        .order_by(StandardWork.review_date)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    standard_works = data_result.scalars().all()

    items = []
    for sw in standard_works:
        response = StandardWorkResponse.model_validate(sw)
        response.full_document_id = sw.full_document_id
        response.is_current = sw.is_current
        response.is_expired = sw.is_expired
        response.needs_review = sw.needs_review
        response.step_count = sw.step_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/expired",
    response_model=PaginatedResponse[StandardWorkResponse],
    summary="Get expired documents",
    description="Get all standard work documents that have passed their expiration date.",
)
async def get_expired(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[StandardWorkResponse]:
    today = _today()
    base_conditions = [
        StandardWork.expiration_date < today,
        StandardWork.is_deleted == False,
    ]

    # Count query
    count_stmt = select(func.count(StandardWork.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Data query
    offset = (page - 1) * page_size
    data_stmt = (
        select(StandardWork)
        .where(and_(*base_conditions))
        .order_by(StandardWork.expiration_date)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    standard_works = data_result.scalars().all()

    items = []
    for sw in standard_works:
        response = StandardWorkResponse.model_validate(sw)
        response.full_document_id = sw.full_document_id
        response.is_current = sw.is_current
        response.is_expired = sw.is_expired
        response.needs_review = sw.needs_review
        response.step_count = sw.step_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )

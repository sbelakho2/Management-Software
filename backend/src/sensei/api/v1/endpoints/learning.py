"""Learning Engine API endpoints.

Provides comprehensive API for managing learning content and progress:
- Learning Module CRUD
- Learning Unit CRUD
- User Progress tracking
- Assessment management
- Learning Path management
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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
from sensei.models.learning import (
    LearningModule,
    LearningUnit,
    UserLearningProgress,
    LearningAssessment,
    LearningPath,
    LearningCategory,
    ContentType,
    DifficultyLevel,
    LearningStatus,
    ProgressStatus,
)


router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ModuleCreate(BaseModel):
    """Schema for creating a learning module."""

    code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: LearningCategory = Field(default=LearningCategory.TPS)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.BEGINNER)
    learning_objectives: Optional[list] = None
    prerequisites: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[list] = None


class ModuleUpdate(BaseModel):
    """Schema for updating a learning module."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[LearningCategory] = None
    difficulty: Optional[DifficultyLevel] = None
    learning_objectives: Optional[list] = None
    prerequisites: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    display_order: Optional[int] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[list] = None


class ModuleResponse(BaseModel):
    """Schema for module response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    title: str
    description: Optional[str] = None
    category: str
    difficulty: str
    learning_objectives: Optional[list] = None
    prerequisites: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    is_published: bool
    published_at: Optional[datetime] = None
    display_order: int
    thumbnail_url: Optional[str] = None
    tags: Optional[list] = None
    created_at: datetime
    updated_at: datetime


class UnitCreate(BaseModel):
    """Schema for creating a learning unit."""

    code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = None
    description: Optional[str] = None
    module_id: Optional[UUID] = None
    category: LearningCategory = Field(default=LearningCategory.TPS)
    content_type: ContentType = Field(default=ContentType.TEXT)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.BEGINNER)
    content: Optional[str] = None
    content_rich: Optional[dict] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    document_url: Optional[str] = None
    key_points: Optional[list] = None
    examples: Optional[list] = None
    anti_patterns: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    japanese_term: Optional[str] = None
    pronunciation: Optional[str] = None
    tags: Optional[list] = None


class UnitUpdate(BaseModel):
    """Schema for updating a learning unit."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subtitle: Optional[str] = None
    description: Optional[str] = None
    module_id: Optional[UUID] = None
    category: Optional[LearningCategory] = None
    content_type: Optional[ContentType] = None
    difficulty: Optional[DifficultyLevel] = None
    content: Optional[str] = None
    content_rich: Optional[dict] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    document_url: Optional[str] = None
    key_points: Optional[list] = None
    examples: Optional[list] = None
    anti_patterns: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    unit_order: Optional[int] = None
    japanese_term: Optional[str] = None
    pronunciation: Optional[str] = None
    tags: Optional[list] = None


class UnitResponse(BaseModel):
    """Schema for unit response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    module_id: Optional[UUID] = None
    category: str
    content_type: str
    difficulty: str
    content: Optional[str] = None
    content_rich: Optional[dict] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    document_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    key_points: Optional[list] = None
    examples: Optional[list] = None
    anti_patterns: Optional[list] = None
    related_units: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    unit_order: int
    is_published: bool
    published_at: Optional[datetime] = None
    version: int
    japanese_term: Optional[str] = None
    pronunciation: Optional[str] = None
    source_reference: Optional[str] = None
    tags: Optional[list] = None
    created_at: datetime
    updated_at: datetime


class ProgressUpdate(BaseModel):
    """Schema for updating progress."""

    progress_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    time_spent_seconds: Optional[int] = Field(default=None, ge=0)
    user_notes: Optional[str] = None
    bookmarked: Optional[bool] = None
    last_position: Optional[dict] = None


class ProgressResponse(BaseModel):
    """Schema for progress response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    unit_id: UUID
    status: str
    progress_percentage: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    time_spent_seconds: int
    best_score: Optional[Decimal] = None
    last_score: Optional[Decimal] = None
    attempts: int
    bookmarked: bool
    user_notes: Optional[str] = None
    next_review_date: Optional[datetime] = None
    last_position: Optional[dict] = None
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class AssessmentCreate(BaseModel):
    """Schema for creating an assessment."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    unit_id: Optional[UUID] = None
    questions: list
    passing_score: Decimal = Field(default=Decimal("70.00"))
    max_score: Decimal = Field(default=Decimal("100.00"))
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    shuffle_questions: bool = False
    show_correct_answers: bool = True


class AssessmentUpdate(BaseModel):
    """Schema for updating an assessment."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    questions: Optional[list] = None
    passing_score: Optional[Decimal] = None
    max_score: Optional[Decimal] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    shuffle_questions: Optional[bool] = None
    show_correct_answers: Optional[bool] = None


class AssessmentResponse(BaseModel):
    """Schema for assessment response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str] = None
    unit_id: Optional[UUID] = None
    questions: list
    passing_score: Decimal
    max_score: Decimal
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    shuffle_questions: bool
    show_correct_answers: bool
    is_published: bool
    question_count: int
    created_at: datetime
    updated_at: datetime


class PathCreate(BaseModel):
    """Schema for creating a learning path."""

    path_code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.BEGINNER)
    is_certification_path: bool = False
    estimated_hours: Optional[float] = None
    prerequisites: Optional[list] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[list] = None


class PathUpdate(BaseModel):
    """Schema for updating a learning path."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    is_certification_path: Optional[bool] = None
    estimated_hours: Optional[float] = None
    prerequisites: Optional[list] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[list] = None


class PathResponse(BaseModel):
    """Schema for path response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    path_code: str
    title: str
    description: Optional[str] = None
    difficulty: str
    status: str
    is_active: bool
    is_certification_path: bool
    estimated_hours: Optional[float] = None
    prerequisites: Optional[list] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[list] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Learning Module Endpoints
# =============================================================================


@router.post(
    "/modules",
    response_model=APIResponse[ModuleResponse],
    status_code=201,
    summary="Create learning module",
    description="Create a new learning module.",
)
async def create_module(
    data: ModuleCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ModuleResponse]:
    # Check for duplicate code
    stmt = select(LearningModule).where(LearningModule.code == data.code)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"Module with code '{data.code}' already exists")

    module = LearningModule(
        code=data.code,
        title=data.title,
        description=data.description,
        category=(
            data.category.value
            if isinstance(data.category, LearningCategory)
            else data.category
        ),
        difficulty=(
            data.difficulty.value
            if isinstance(data.difficulty, DifficultyLevel)
            else data.difficulty
        ),
        learning_objectives=data.learning_objectives,
        prerequisites=data.prerequisites,
        estimated_duration_minutes=data.estimated_duration_minutes,
        thumbnail_url=data.thumbnail_url,
        tags=data.tags or [],
        created_by_id=current_user.id,
    )

    db.add(module)
    await db.flush()
    await db.refresh(module)

    return build_created_response(
        data=ModuleResponse.model_validate(module),
        resource_name="Learning module",
    )


@router.get(
    "/modules/{module_id}",
    response_model=APIResponse[ModuleResponse],
    summary="Get learning module",
    description="Get a learning module by ID.",
)
async def get_module(
    module_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ModuleResponse]:
    stmt = select(LearningModule).where(LearningModule.id == module_id)
    result = await db.execute(stmt)
    module = result.scalar_one_or_none()

    if not module:
        raise NotFoundError(f"Learning module {module_id} not found")

    return build_response(
        data=ModuleResponse.model_validate(module),
        message="Learning module retrieved successfully",
    )


@router.get(
    "/modules",
    response_model=PaginatedResponse[ModuleResponse],
    summary="List learning modules",
    description="List learning modules with filtering.",
)
async def list_modules(
    db: DBSession,
    current_user: CurrentUser,
    category: Optional[LearningCategory] = Query(default=None),
    difficulty: Optional[DifficultyLevel] = Query(default=None),
    published_only: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ModuleResponse]:
    base_conditions = []

    if category and isinstance(category, LearningCategory):
        base_conditions.append(LearningModule.category == category.value)
    if difficulty and isinstance(difficulty, DifficultyLevel):
        base_conditions.append(LearningModule.difficulty == difficulty.value)
    if published_only:
        base_conditions.append(LearningModule.is_published == True)
    if search:
        search_filter = or_(
            LearningModule.title.ilike(f"%{search}%"),
            LearningModule.description.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    where_clause = and_(*base_conditions) if base_conditions else True
    count_stmt = select(func.count(LearningModule.id)).where(where_clause)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(LearningModule)
        .where(where_clause)
        .order_by(LearningModule.display_order.asc(), LearningModule.title.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    modules = data_result.scalars().all()

    items = [ModuleResponse.model_validate(m) for m in modules]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/modules/{module_id}",
    response_model=APIResponse[ModuleResponse],
    summary="Update learning module",
    description="Update a learning module.",
)
async def update_module(
    module_id: UUID,
    data: ModuleUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ModuleResponse]:
    stmt = select(LearningModule).where(LearningModule.id == module_id)
    result = await db.execute(stmt)
    module = result.scalar_one_or_none()

    if not module:
        raise NotFoundError(f"Learning module {module_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    if "category" in update_data and update_data["category"]:
        if isinstance(update_data["category"], LearningCategory):
            update_data["category"] = update_data["category"].value
    if "difficulty" in update_data and update_data["difficulty"]:
        if isinstance(update_data["difficulty"], DifficultyLevel):
            update_data["difficulty"] = update_data["difficulty"].value

    for key, value in update_data.items():
        setattr(module, key, value)

    module.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(module)

    return build_updated_response(
        data=ModuleResponse.model_validate(module),
        resource_name="Learning module",
    )


@router.post(
    "/modules/{module_id}/publish",
    response_model=APIResponse[ModuleResponse],
    summary="Publish module",
    description="Publish a learning module.",
)
async def publish_module(
    module_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ModuleResponse]:
    stmt = select(LearningModule).where(LearningModule.id == module_id)
    result = await db.execute(stmt)
    module = result.scalar_one_or_none()

    if not module:
        raise NotFoundError(f"Learning module {module_id} not found")

    if module.is_published:
        raise ConflictError("Module is already published")

    module.is_published = True
    module.published_at = datetime.now(timezone.utc)
    module.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(module)

    return build_response(
        data=ModuleResponse.model_validate(module),
        message="Module published",
    )


@router.delete(
    "/modules/{module_id}",
    response_model=APIResponse,
    summary="Delete learning module",
    description="Delete a learning module.",
)
async def delete_module(
    module_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(LearningModule).where(LearningModule.id == module_id)
    result = await db.execute(stmt)
    module = result.scalar_one_or_none()

    if not module:
        raise NotFoundError(f"Learning module {module_id} not found")

    await db.delete(module)
    await db.flush()

    return build_deleted_response(resource_name="Learning module")


# =============================================================================
# Learning Unit Endpoints
# =============================================================================


@router.post(
    "/units",
    response_model=APIResponse[UnitResponse],
    status_code=201,
    summary="Create learning unit",
    description="Create a new learning unit.",
)
async def create_unit(
    data: UnitCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[UnitResponse]:
    # Check for duplicate code
    stmt = select(LearningUnit).where(LearningUnit.code == data.code)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"Unit with code '{data.code}' already exists")

    unit = LearningUnit(
        code=data.code,
        title=data.title,
        subtitle=data.subtitle,
        description=data.description,
        module_id=data.module_id,
        category=(
            data.category.value
            if isinstance(data.category, LearningCategory)
            else data.category
        ),
        content_type=(
            data.content_type.value
            if isinstance(data.content_type, ContentType)
            else data.content_type
        ),
        difficulty=(
            data.difficulty.value
            if isinstance(data.difficulty, DifficultyLevel)
            else data.difficulty
        ),
        content=data.content,
        content_rich=data.content_rich,
        video_url=data.video_url,
        audio_url=data.audio_url,
        document_url=data.document_url,
        key_points=data.key_points,
        examples=data.examples,
        anti_patterns=data.anti_patterns,
        estimated_duration_minutes=data.estimated_duration_minutes,
        japanese_term=data.japanese_term,
        pronunciation=data.pronunciation,
        tags=data.tags or [],
        created_by_id=current_user.id,
    )

    db.add(unit)
    await db.flush()
    await db.refresh(unit)

    return build_created_response(
        data=UnitResponse.model_validate(unit),
        resource_name="Learning unit",
    )


@router.get(
    "/units/{unit_id}",
    response_model=APIResponse[UnitResponse],
    summary="Get learning unit",
    description="Get a learning unit by ID.",
)
async def get_unit(
    unit_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[UnitResponse]:
    stmt = select(LearningUnit).where(LearningUnit.id == unit_id)
    result = await db.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        raise NotFoundError(f"Learning unit {unit_id} not found")

    return build_response(
        data=UnitResponse.model_validate(unit),
        message="Learning unit retrieved successfully",
    )


@router.get(
    "/units",
    response_model=PaginatedResponse[UnitResponse],
    summary="List learning units",
    description="List learning units with filtering.",
)
async def list_units(
    db: DBSession,
    current_user: CurrentUser,
    module_id: Optional[UUID] = Query(default=None),
    category: Optional[LearningCategory] = Query(default=None),
    content_type: Optional[ContentType] = Query(default=None),
    difficulty: Optional[DifficultyLevel] = Query(default=None),
    published_only: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[UnitResponse]:
    base_conditions = []

    if module_id:
        base_conditions.append(LearningUnit.module_id == module_id)
    if category and isinstance(category, LearningCategory):
        base_conditions.append(LearningUnit.category == category.value)
    if content_type and isinstance(content_type, ContentType):
        base_conditions.append(LearningUnit.content_type == content_type.value)
    if difficulty and isinstance(difficulty, DifficultyLevel):
        base_conditions.append(LearningUnit.difficulty == difficulty.value)
    if published_only:
        base_conditions.append(LearningUnit.is_published == True)
    if search:
        search_filter = or_(
            LearningUnit.title.ilike(f"%{search}%"),
            LearningUnit.description.ilike(f"%{search}%"),
            LearningUnit.content.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    where_clause = and_(*base_conditions) if base_conditions else True
    count_stmt = select(func.count(LearningUnit.id)).where(where_clause)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(LearningUnit)
        .where(where_clause)
        .order_by(LearningUnit.unit_order.asc(), LearningUnit.title.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    units = data_result.scalars().all()

    items = [UnitResponse.model_validate(u) for u in units]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/units/{unit_id}",
    response_model=APIResponse[UnitResponse],
    summary="Update learning unit",
    description="Update a learning unit.",
)
async def update_unit(
    unit_id: UUID,
    data: UnitUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[UnitResponse]:
    stmt = select(LearningUnit).where(LearningUnit.id == unit_id)
    result = await db.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        raise NotFoundError(f"Learning unit {unit_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    if "category" in update_data and update_data["category"]:
        if isinstance(update_data["category"], LearningCategory):
            update_data["category"] = update_data["category"].value
    if "content_type" in update_data and update_data["content_type"]:
        if isinstance(update_data["content_type"], ContentType):
            update_data["content_type"] = update_data["content_type"].value
    if "difficulty" in update_data and update_data["difficulty"]:
        if isinstance(update_data["difficulty"], DifficultyLevel):
            update_data["difficulty"] = update_data["difficulty"].value

    for key, value in update_data.items():
        setattr(unit, key, value)

    unit.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(unit)

    return build_updated_response(
        data=UnitResponse.model_validate(unit),
        resource_name="Learning unit",
    )


@router.post(
    "/units/{unit_id}/publish",
    response_model=APIResponse[UnitResponse],
    summary="Publish unit",
    description="Publish a learning unit.",
)
async def publish_unit(
    unit_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[UnitResponse]:
    stmt = select(LearningUnit).where(LearningUnit.id == unit_id)
    result = await db.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        raise NotFoundError(f"Learning unit {unit_id} not found")

    if unit.is_published:
        raise ConflictError("Unit is already published")

    unit.is_published = True
    unit.published_at = datetime.now(timezone.utc)
    unit.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(unit)

    return build_response(
        data=UnitResponse.model_validate(unit),
        message="Unit published",
    )


@router.delete(
    "/units/{unit_id}",
    response_model=APIResponse,
    summary="Delete learning unit",
    description="Delete a learning unit.",
)
async def delete_unit(
    unit_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(LearningUnit).where(LearningUnit.id == unit_id)
    result = await db.execute(stmt)
    unit = result.scalar_one_or_none()

    if not unit:
        raise NotFoundError(f"Learning unit {unit_id} not found")

    await db.delete(unit)
    await db.flush()

    return build_deleted_response(resource_name="Learning unit")


# =============================================================================
# User Progress Endpoints
# =============================================================================


@router.get(
    "/progress/my-progress",
    response_model=PaginatedResponse[ProgressResponse],
    summary="Get my progress",
    description="Get current user's learning progress.",
)
async def get_my_progress(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[ProgressStatus] = Query(default=None),
    bookmarked_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ProgressResponse]:
    base_conditions = [UserLearningProgress.user_id == current_user.id]

    if status and isinstance(status, ProgressStatus):
        base_conditions.append(UserLearningProgress.status == status.value)
    if bookmarked_only:
        base_conditions.append(UserLearningProgress.bookmarked == True)

    count_stmt = select(func.count(UserLearningProgress.id)).where(
        and_(*base_conditions)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(UserLearningProgress)
        .where(and_(*base_conditions))
        .order_by(UserLearningProgress.last_accessed_at.desc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    progress_list = data_result.scalars().all()

    items = [ProgressResponse.model_validate(p) for p in progress_list]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/progress/{unit_id}",
    response_model=APIResponse[ProgressResponse],
    summary="Get progress for unit",
    description="Get current user's progress for a specific unit.",
)
async def get_unit_progress(
    unit_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProgressResponse]:
    stmt = select(UserLearningProgress).where(
        and_(
            UserLearningProgress.user_id == current_user.id,
            UserLearningProgress.unit_id == unit_id,
        )
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress:
        raise NotFoundError(f"No progress found for unit {unit_id}")

    return build_response(
        data=ProgressResponse.model_validate(progress),
        message="Progress retrieved successfully",
    )


@router.post(
    "/progress/{unit_id}/start",
    response_model=APIResponse[ProgressResponse],
    status_code=201,
    summary="Start learning unit",
    description="Start learning a unit, creating progress record.",
)
async def start_unit(
    unit_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProgressResponse]:
    # Check unit exists
    unit_stmt = select(LearningUnit).where(LearningUnit.id == unit_id)
    unit_result = await db.execute(unit_stmt)
    unit = unit_result.scalar_one_or_none()
    if not unit:
        raise NotFoundError(f"Learning unit {unit_id} not found")

    # Check for existing progress
    stmt = select(UserLearningProgress).where(
        and_(
            UserLearningProgress.user_id == current_user.id,
            UserLearningProgress.unit_id == unit_id,
        )
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if progress:
        # Update last accessed
        progress.last_accessed_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(progress)
        return build_response(
            data=ProgressResponse.model_validate(progress),
            message="Progress resumed",
        )

    # Create new progress
    progress = UserLearningProgress(
        user_id=current_user.id,
        unit_id=unit_id,
        status=ProgressStatus.IN_PROGRESS.value,
        started_at=datetime.now(timezone.utc),
        last_accessed_at=datetime.now(timezone.utc),
    )

    db.add(progress)
    await db.flush()
    await db.refresh(progress)

    return build_created_response(
        data=ProgressResponse.model_validate(progress),
        resource_name="Progress",
    )


@router.patch(
    "/progress/{unit_id}",
    response_model=APIResponse[ProgressResponse],
    summary="Update progress",
    description="Update learning progress for a unit.",
)
async def update_progress(
    unit_id: UUID,
    data: ProgressUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProgressResponse]:
    stmt = select(UserLearningProgress).where(
        and_(
            UserLearningProgress.user_id == current_user.id,
            UserLearningProgress.unit_id == unit_id,
        )
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress:
        raise NotFoundError(f"No progress found for unit {unit_id}")

    update_data = data.model_dump(exclude_unset=True)

    if "time_spent_seconds" in update_data:
        progress.time_spent_seconds = (
            progress.time_spent_seconds + update_data.pop("time_spent_seconds")
        )

    for key, value in update_data.items():
        setattr(progress, key, value)

    progress.last_accessed_at = datetime.now(timezone.utc)

    if progress.progress_percentage == 100:
        progress.status = ProgressStatus.COMPLETED.value
        if not progress.completed_at:
            progress.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(progress)

    return build_updated_response(
        data=ProgressResponse.model_validate(progress),
        resource_name="Progress",
    )


@router.post(
    "/progress/{unit_id}/complete",
    response_model=APIResponse[ProgressResponse],
    summary="Complete unit",
    description="Mark a learning unit as completed.",
)
async def complete_unit(
    unit_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProgressResponse]:
    stmt = select(UserLearningProgress).where(
        and_(
            UserLearningProgress.user_id == current_user.id,
            UserLearningProgress.unit_id == unit_id,
        )
    )
    result = await db.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress:
        raise NotFoundError(f"No progress found for unit {unit_id}")

    if progress.status == ProgressStatus.COMPLETED.value:
        raise ConflictError("Unit is already completed")

    progress.status = ProgressStatus.COMPLETED.value
    progress.progress_percentage = 100
    progress.completed_at = datetime.now(timezone.utc)
    progress.last_accessed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(progress)

    return build_response(
        data=ProgressResponse.model_validate(progress),
        message="Unit completed",
    )


# =============================================================================
# Assessment Endpoints
# =============================================================================


@router.post(
    "/assessments",
    response_model=APIResponse[AssessmentResponse],
    status_code=201,
    summary="Create assessment",
    description="Create a new learning assessment.",
)
async def create_assessment(
    data: AssessmentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AssessmentResponse]:
    assessment = LearningAssessment(
        title=data.title,
        description=data.description,
        unit_id=data.unit_id,
        questions=data.questions,
        passing_score=data.passing_score,
        max_score=data.max_score,
        time_limit_minutes=data.time_limit_minutes,
        max_attempts=data.max_attempts,
        shuffle_questions=data.shuffle_questions,
        show_correct_answers=data.show_correct_answers,
        created_by_id=current_user.id,
    )

    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)

    return build_created_response(
        data=AssessmentResponse.model_validate(assessment),
        resource_name="Assessment",
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=APIResponse[AssessmentResponse],
    summary="Get assessment",
    description="Get an assessment by ID.",
)
async def get_assessment(
    assessment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AssessmentResponse]:
    stmt = select(LearningAssessment).where(LearningAssessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")

    return build_response(
        data=AssessmentResponse.model_validate(assessment),
        message="Assessment retrieved successfully",
    )


@router.patch(
    "/assessments/{assessment_id}",
    response_model=APIResponse[AssessmentResponse],
    summary="Update assessment",
    description="Update an assessment.",
)
async def update_assessment(
    assessment_id: UUID,
    data: AssessmentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AssessmentResponse]:
    stmt = select(LearningAssessment).where(LearningAssessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(assessment, key, value)

    assessment.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(assessment)

    return build_updated_response(
        data=AssessmentResponse.model_validate(assessment),
        resource_name="Assessment",
    )


@router.delete(
    "/assessments/{assessment_id}",
    response_model=APIResponse,
    summary="Delete assessment",
    description="Delete an assessment.",
)
async def delete_assessment(
    assessment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(LearningAssessment).where(LearningAssessment.id == assessment_id)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")

    await db.delete(assessment)
    await db.flush()

    return build_deleted_response(resource_name="Assessment")


# =============================================================================
# Learning Path Endpoints
# =============================================================================


@router.post(
    "/paths",
    response_model=APIResponse[PathResponse],
    status_code=201,
    summary="Create learning path",
    description="Create a new learning path.",
)
async def create_path(
    data: PathCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[PathResponse]:
    # Check for duplicate code
    stmt = select(LearningPath).where(LearningPath.path_code == data.path_code)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"Path with code '{data.path_code}' already exists")

    path = LearningPath(
        path_code=data.path_code,
        title=data.title,
        description=data.description,
        difficulty=(
            data.difficulty.value
            if isinstance(data.difficulty, DifficultyLevel)
            else data.difficulty
        ),
        is_certification_path=data.is_certification_path,
        estimated_hours=data.estimated_hours,
        prerequisites=data.prerequisites or [],
        thumbnail_url=data.thumbnail_url,
        tags=data.tags or [],
        created_by_id=current_user.id,
    )

    db.add(path)
    await db.flush()
    await db.refresh(path)

    return build_created_response(
        data=PathResponse.model_validate(path),
        resource_name="Learning path",
    )


@router.get(
    "/paths/{path_id}",
    response_model=APIResponse[PathResponse],
    summary="Get learning path",
    description="Get a learning path by ID.",
)
async def get_path(
    path_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[PathResponse]:
    stmt = select(LearningPath).where(LearningPath.id == path_id)
    result = await db.execute(stmt)
    path = result.scalar_one_or_none()

    if not path:
        raise NotFoundError(f"Learning path {path_id} not found")

    return build_response(
        data=PathResponse.model_validate(path),
        message="Learning path retrieved successfully",
    )


@router.get(
    "/paths",
    response_model=PaginatedResponse[PathResponse],
    summary="List learning paths",
    description="List learning paths.",
)
async def list_paths(
    db: DBSession,
    current_user: CurrentUser,
    difficulty: Optional[DifficultyLevel] = Query(default=None),
    certification_only: bool = Query(default=False),
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[PathResponse]:
    base_conditions = []

    if difficulty and isinstance(difficulty, DifficultyLevel):
        base_conditions.append(LearningPath.difficulty == difficulty.value)
    if certification_only:
        base_conditions.append(LearningPath.is_certification_path == True)
    if active_only:
        base_conditions.append(LearningPath.is_active == True)

    where_clause = and_(*base_conditions) if base_conditions else True
    count_stmt = select(func.count(LearningPath.id)).where(where_clause)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(LearningPath)
        .where(where_clause)
        .order_by(LearningPath.title.asc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    paths = data_result.scalars().all()

    items = [PathResponse.model_validate(p) for p in paths]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/paths/{path_id}",
    response_model=APIResponse[PathResponse],
    summary="Update learning path",
    description="Update a learning path.",
)
async def update_path(
    path_id: UUID,
    data: PathUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[PathResponse]:
    stmt = select(LearningPath).where(LearningPath.id == path_id)
    result = await db.execute(stmt)
    path = result.scalar_one_or_none()

    if not path:
        raise NotFoundError(f"Learning path {path_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    if "difficulty" in update_data and update_data["difficulty"]:
        if isinstance(update_data["difficulty"], DifficultyLevel):
            update_data["difficulty"] = update_data["difficulty"].value

    for key, value in update_data.items():
        setattr(path, key, value)

    path.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(path)

    return build_updated_response(
        data=PathResponse.model_validate(path),
        resource_name="Learning path",
    )


@router.delete(
    "/paths/{path_id}",
    response_model=APIResponse,
    summary="Delete learning path",
    description="Delete a learning path.",
)
async def delete_path(
    path_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(LearningPath).where(LearningPath.id == path_id)
    result = await db.execute(stmt)
    path = result.scalar_one_or_none()

    if not path:
        raise NotFoundError(f"Learning path {path_id} not found")

    await db.delete(path)
    await db.flush()

    return build_deleted_response(resource_name="Learning path")

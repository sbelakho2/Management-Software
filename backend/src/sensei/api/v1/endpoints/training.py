"""Training & Skills Endpoints.

Provides CRUD and workflow operations for:
- Skills (competency definitions)
- Skill Requirements (skills needed for stations/products)
- Trainings (training events and courses)
- Training Participants (enrollments and completions)
- User Skills (user competencies and certifications)

Implements competency management following lean manufacturing principles.
"""

from __future__ import annotations

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Header
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload

from sensei.api import deps
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
from sensei.models.training import (
    Skill,
    SkillCategory,
    SkillRequirement,
    Training,
    TrainingType,
    TrainingStatus,
    TrainingParticipant,
    EnrollmentStatus,
    AttendanceStatus,
    UserSkill,
    CertificationStatus,
)

from sensei.services.core.data_lineage import get_data_lineage_service
from sensei.services.core.common_thread import get_common_thread_service

AllowTrainingModule = deps.require_role("hr", "supervisor", "team_lead", "operator")  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[Depends(deps.RoleChecker(["hr", "supervisor", "team_lead", "operator"]))]
)


# =============================================================================
# Utility helpers
# =============================================================================


def _now_utc() -> datetime:
    """Get current UTC datetime (naive) for consistency with model timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
# Skill Schemas
# =============================================================================


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    skill_category: SkillCategory = SkillCategory.TECHNICAL
    proficiency_levels: list[str] = Field(
        default=["Awareness", "Basic", "Proficient", "Expert", "Trainer"]
    )
    minimum_required_level: int = Field(default=2, ge=0)
    is_safety_critical: bool = False
    is_quality_critical: bool = False
    requires_recertification: bool = True
    recertification_interval_days: int = Field(default=365, ge=0)
    initial_training_hours: Decimal = Field(default=Decimal("8.0"), ge=0)
    recertification_hours: Decimal = Field(default=Decimal("2.0"), ge=0)

    @field_validator("skill_category", mode="before")
    @classmethod
    def validate_skill_category(cls, v):
        return _parse_enum(SkillCategory, v, "skill_category")


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    skill_category: Optional[SkillCategory] = None
    proficiency_levels: Optional[list[str]] = None
    minimum_required_level: Optional[int] = Field(default=None, ge=0)
    is_safety_critical: Optional[bool] = None
    is_quality_critical: Optional[bool] = None
    requires_recertification: Optional[bool] = None
    recertification_interval_days: Optional[int] = Field(default=None, ge=0)
    initial_training_hours: Optional[Decimal] = Field(default=None, ge=0)
    recertification_hours: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator("skill_category", mode="before")
    @classmethod
    def validate_skill_category(cls, v):
        return _parse_enum(SkillCategory, v, "skill_category")


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: Optional[str]
    skill_category: SkillCategory
    proficiency_levels: list[str]
    minimum_required_level: int
    is_safety_critical: bool
    is_quality_critical: bool
    requires_recertification: bool
    recertification_interval_days: int
    initial_training_hours: Decimal
    recertification_hours: Decimal
    created_at: datetime
    updated_at: datetime
    level_count: Optional[int] = None


# =============================================================================
# Skill Requirement Schemas
# =============================================================================


class SkillRequirementBase(BaseModel):
    skill_id: int = Field(..., gt=0)
    station_id: Optional[int] = Field(default=None, gt=0)
    product_id: Optional[int] = Field(default=None, gt=0)
    minimum_proficiency_level: int = Field(default=2, ge=0)
    is_mandatory: bool = True
    notes: Optional[str] = None


class SkillRequirementCreate(SkillRequirementBase):
    pass


class SkillRequirementUpdate(BaseModel):
    minimum_proficiency_level: Optional[int] = Field(default=None, ge=0)
    is_mandatory: Optional[bool] = None
    notes: Optional[str] = None


class SkillRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    station_id: Optional[int]
    product_id: Optional[int]
    minimum_proficiency_level: int
    is_mandatory: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Training Schemas
# =============================================================================


class TrainingBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    skill_id: int = Field(..., gt=0)
    training_type: TrainingType = TrainingType.CLASSROOM
    duration_hours: Decimal = Field(default=Decimal("8.0"), gt=0)
    max_participants: Optional[int] = Field(default=None, gt=0)
    scheduled_date: Optional[date] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    location: Optional[str] = Field(default=None, max_length=255)
    trainer_id: Optional[UUID] = None
    external_trainer_name: Optional[str] = Field(default=None, max_length=255)
    provides_certification: bool = True
    certification_level_granted: int = Field(default=2, ge=0)
    cost_per_person: Optional[Decimal] = Field(default=None, ge=0)
    materials_url: Optional[str] = Field(default=None, max_length=500)
    syllabus: Optional[dict[str, Any]] = None
    notes: Optional[str] = None

    @field_validator("training_type", mode="before")
    @classmethod
    def validate_training_type(cls, v):
        return _parse_enum(TrainingType, v, "training_type")


class TrainingCreate(TrainingBase):
    pass


class TrainingUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    training_type: Optional[TrainingType] = None
    duration_hours: Optional[Decimal] = Field(default=None, gt=0)
    max_participants: Optional[int] = Field(default=None, gt=0)
    scheduled_date: Optional[date] = None
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None
    location: Optional[str] = Field(default=None, max_length=255)
    trainer_id: Optional[UUID] = None
    external_trainer_name: Optional[str] = Field(default=None, max_length=255)
    provides_certification: Optional[bool] = None
    certification_level_granted: Optional[int] = Field(default=None, ge=0)
    cost_per_person: Optional[Decimal] = Field(default=None, ge=0)
    materials_url: Optional[str] = Field(default=None, max_length=500)
    syllabus: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    status: Optional[TrainingStatus] = None

    @field_validator("training_type", mode="before")
    @classmethod
    def validate_training_type(cls, v):
        return _parse_enum(TrainingType, v, "training_type")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        return _parse_enum(TrainingStatus, v, "status")


class TrainingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    skill_id: int
    training_type: TrainingType
    duration_hours: Decimal
    max_participants: Optional[int]
    scheduled_date: Optional[date]
    scheduled_start_time: Optional[datetime]
    scheduled_end_time: Optional[datetime]
    location: Optional[str]
    status: TrainingStatus
    trainer_id: Optional[UUID]
    external_trainer_name: Optional[str]
    provides_certification: bool
    certification_level_granted: int
    cost_per_person: Optional[Decimal]
    materials_url: Optional[str]
    syllabus: Optional[dict[str, Any]]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    enrolled_count: Optional[int] = None
    has_capacity: Optional[bool] = None
    is_upcoming: Optional[bool] = None


# =============================================================================
# Training Participant Schemas
# =============================================================================


class ParticipantEnroll(BaseModel):
    user_id: UUID
    notes: Optional[str] = None


class ParticipantUpdate(BaseModel):
    enrollment_status: Optional[EnrollmentStatus] = None
    attendance_status: Optional[AttendanceStatus] = None
    score: Optional[Decimal] = Field(default=None, ge=0, le=100)
    passed: Optional[bool] = None
    notes: Optional[str] = None
    manager_notes: Optional[str] = None

    @field_validator("enrollment_status", mode="before")
    @classmethod
    def validate_enrollment_status(cls, v):
        return _parse_enum(EnrollmentStatus, v, "enrollment_status")

    @field_validator("attendance_status", mode="before")
    @classmethod
    def validate_attendance_status(cls, v):
        return _parse_enum(AttendanceStatus, v, "attendance_status")


class ParticipantComplete(BaseModel):
    score: Optional[Decimal] = Field(default=None, ge=0, le=100)
    passed: bool = True
    notes: Optional[str] = None
    certificate_number: Optional[str] = Field(default=None, max_length=100)


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    training_id: int
    user_id: UUID
    enrollment_status: EnrollmentStatus
    attendance_status: AttendanceStatus
    score: Optional[Decimal]
    passed: Optional[bool]
    completed_at: Optional[datetime]
    certificate_number: Optional[str]
    certificate_issued_at: Optional[datetime]
    notes: Optional[str]
    manager_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# User Skill Schemas
# =============================================================================


class UserSkillCreate(BaseModel):
    user_id: UUID
    skill_id: int = Field(..., gt=0)
    proficiency_level: int = Field(default=0, ge=0)
    notes: Optional[str] = None


class UserSkillUpdate(BaseModel):
    proficiency_level: Optional[int] = Field(default=None, ge=0)
    certification_status: Optional[CertificationStatus] = None
    notes: Optional[str] = None

    @field_validator("certification_status", mode="before")
    @classmethod
    def validate_certification_status(cls, v):
        return _parse_enum(CertificationStatus, v, "certification_status")


class UserSkillCertify(BaseModel):
    proficiency_level: int = Field(..., ge=0)
    expiration_date: Optional[date] = None
    certificate_number: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None


class UserSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    skill_id: int
    proficiency_level: int
    certification_status: CertificationStatus
    certified_date: Optional[date]
    expiration_date: Optional[date]
    last_recertification_date: Optional[date]
    certified_by_id: Optional[UUID]
    certificate_number: Optional[str]
    assessment_scores: Optional[list[dict[str, Any]]]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_certified: Optional[bool] = None
    is_expired: Optional[bool] = None
    days_until_expiration: Optional[int] = None
    needs_recertification_soon: Optional[bool] = None


# =============================================================================
# Skill CRUD Endpoints
# =============================================================================


@router.post(
    "/skills",
    response_model=APIResponse[SkillResponse],
    status_code=201,
    summary="Create skill",
    description="Create a new skill definition.",
)
async def create_skill(
    data: SkillCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SkillResponse]:
    # Check for duplicate code
    stmt = select(Skill).where(
        and_(
            Skill.code == data.code,
            Skill.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"Skill with code '{data.code}' already exists")

    skill = Skill(
        name=data.name,
        code=data.code,
        description=data.description,
        skill_category=data.skill_category,
        proficiency_levels=data.proficiency_levels,
        minimum_required_level=data.minimum_required_level,
        is_safety_critical=data.is_safety_critical,
        is_quality_critical=data.is_quality_critical,
        requires_recertification=data.requires_recertification,
        recertification_interval_days=data.recertification_interval_days,
        initial_training_hours=data.initial_training_hours,
        recertification_hours=data.recertification_hours,
        created_by_id=current_user.id,
    )
    db.add(skill)
    await db.flush()
    await db.refresh(skill)

    response = SkillResponse.model_validate(skill)
    response.level_count = skill.level_count
    return build_created_response(data=response, resource_name="Skill")


@router.get(
    "/skills/{skill_id}",
    response_model=APIResponse[SkillResponse],
    summary="Get skill",
    description="Get a skill by ID.",
)
async def get_skill(
    skill_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SkillResponse]:
    stmt = select(Skill).where(
        and_(Skill.id == skill_id, Skill.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found")

    response = SkillResponse.model_validate(skill)
    response.level_count = skill.level_count
    return build_response(response)


@router.get(
    "/skills",
    response_model=PaginatedResponse[SkillResponse],
    summary="List skills",
    description="List skills with filtering and pagination.",
)
async def list_skills(
    db: DBSession,
    current_user: CurrentUser,
    category: Optional[SkillCategory] = Query(default=None),
    is_safety_critical: Optional[bool] = Query(default=None),
    is_quality_critical: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[SkillResponse]:
    base_conditions: list[Any] = [Skill.deleted_at.is_(None)]

    if category and isinstance(category, SkillCategory):
        base_conditions.append(Skill.skill_category == category)
    if is_safety_critical is not None:
        base_conditions.append(Skill.is_safety_critical == is_safety_critical)
    if is_quality_critical is not None:
        base_conditions.append(Skill.is_quality_critical == is_quality_critical)
    if search and isinstance(search, str):
        search_filter = or_(
            Skill.name.ilike(f"%{search}%"),
            Skill.code.ilike(f"%{search}%"),
            Skill.description.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    count_stmt = select(func.count(Skill.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Skill)
        .where(and_(*base_conditions))
        .order_by(Skill.name)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    skills = data_result.scalars().all()

    items = []
    for skill in skills:
        response = SkillResponse.model_validate(skill)
        response.level_count = skill.level_count
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/skills/{skill_id}",
    response_model=APIResponse[SkillResponse],
    summary="Update skill",
    description="Update a skill definition.",
)
async def update_skill(
    skill_id: int,
    data: SkillUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SkillResponse]:
    stmt = select(Skill).where(
        and_(Skill.id == skill_id, Skill.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(skill, field, value)

    skill.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(skill)

    response = SkillResponse.model_validate(skill)
    response.level_count = skill.level_count
    return build_updated_response(response, "Skill")


@router.delete(
    "/skills/{skill_id}",
    response_model=APIResponse[None],
    summary="Delete skill",
    description="Soft delete a skill.",
)
async def delete_skill(
    skill_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(Skill).where(
        and_(Skill.id == skill_id, Skill.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found")

    skill.deleted_at = _now_utc()
    skill.deleted_by_id = current_user.id
    # Note: is_deleted is a read-only property derived from deleted_at
    await db.flush()

    return build_deleted_response("Skill")


# =============================================================================
# Skill Requirement Endpoints
# =============================================================================


@router.post(
    "/skill-requirements",
    response_model=APIResponse[SkillRequirementResponse],
    status_code=201,
    summary="Create skill requirement",
    description="Create a skill requirement for a station or product.",
)
async def create_skill_requirement(
    data: SkillRequirementCreate,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[SkillRequirementResponse]:
    # Validate at least one target is set
    if data.station_id is None and data.product_id is None:
        raise ConflictError("Either station_id or product_id must be specified")

    # Check skill exists
    skill_stmt = select(Skill).where(
        and_(Skill.id == data.skill_id, Skill.deleted_at.is_(None))
    )
    skill_result = await db.execute(skill_stmt)
    if not skill_result.scalar_one_or_none():
        raise NotFoundError(f"Skill {data.skill_id} not found")

    # Check for duplicate
    dup_stmt = select(SkillRequirement).where(
        and_(
            SkillRequirement.skill_id == data.skill_id,
            SkillRequirement.station_id == data.station_id,
            SkillRequirement.product_id == data.product_id,
        )
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise ConflictError("Skill requirement already exists for this target")

    requirement = SkillRequirement(
        skill_id=data.skill_id,
        station_id=data.station_id,
        product_id=data.product_id,
        minimum_proficiency_level=data.minimum_proficiency_level,
        is_mandatory=data.is_mandatory,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(requirement)
    await db.flush()
    await db.refresh(requirement)

    # Persist primary write first; lineage is best-effort enrichment.
    await db.commit()

    # Best-effort: capture lineage links (do not block requirement creation).
    try:
        await get_data_lineage_service().capture_skill_requirement_created(
            db,
            requirement_id=requirement.id,
            skill_id=requirement.skill_id,
            station_id=requirement.station_id,
            product_id=requirement.product_id,
            created_by_id=current_user.id,
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="skill_requirement",
                entity_id=str(requirement.id),
                reasoning_id=x_reasoning_id,
                created_by_id=current_user.id,
                source="skill_requirement_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()

    return build_created_response(
        data=SkillRequirementResponse.model_validate(requirement),
        resource_name="Skill requirement"
    )


@router.get(
    "/skill-requirements",
    response_model=PaginatedResponse[SkillRequirementResponse],
    summary="List skill requirements",
    description="List skill requirements with filtering.",
)
async def list_skill_requirements(
    db: DBSession,
    current_user: CurrentUser,
    skill_id: Optional[int] = Query(default=None),
    station_id: Optional[int] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    is_mandatory: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[SkillRequirementResponse]:
    base_conditions: list[Any] = []

    if skill_id is not None and isinstance(skill_id, int):
        base_conditions.append(SkillRequirement.skill_id == skill_id)
    if station_id is not None and isinstance(station_id, int):
        base_conditions.append(SkillRequirement.station_id == station_id)
    if product_id is not None and isinstance(product_id, int):
        base_conditions.append(SkillRequirement.product_id == product_id)
    if is_mandatory is not None:
        base_conditions.append(SkillRequirement.is_mandatory == is_mandatory)

    if base_conditions:
        where_clause = and_(*base_conditions)
    else:
        where_clause = SkillRequirement.id.isnot(None)  # Always true condition

    count_stmt = select(func.count(SkillRequirement.id)).where(where_clause)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(SkillRequirement)
        .where(where_clause)
        .order_by(SkillRequirement.skill_id, SkillRequirement.id)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    requirements = data_result.scalars().all()

    items = [SkillRequirementResponse.model_validate(r) for r in requirements]
    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/skill-requirements/{requirement_id}",
    response_model=APIResponse[None],
    summary="Delete skill requirement",
    description="Delete a skill requirement.",
)
async def delete_skill_requirement(
    requirement_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(SkillRequirement).where(SkillRequirement.id == requirement_id)
    result = await db.execute(stmt)
    requirement = result.scalar_one_or_none()
    if not requirement:
        raise NotFoundError(f"Skill requirement {requirement_id} not found")

    await db.delete(requirement)
    await db.flush()

    return build_deleted_response("Skill requirement")


# =============================================================================
# Training CRUD Endpoints
# =============================================================================


@router.post(
    "/trainings",
    response_model=APIResponse[TrainingResponse],
    status_code=201,
    summary="Create training",
    description="Create a new training event.",
)
async def create_training(
    data: TrainingCreate,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[TrainingResponse]:
    # Check skill exists
    skill_stmt = select(Skill).where(
        and_(Skill.id == data.skill_id, Skill.deleted_at.is_(None))
    )
    skill_result = await db.execute(skill_stmt)
    if not skill_result.scalar_one_or_none():
        raise NotFoundError(f"Skill {data.skill_id} not found")

    training = Training(
        name=data.name,
        code=data.code,
        description=data.description,
        skill_id=data.skill_id,
        training_type=data.training_type,
        duration_hours=data.duration_hours,
        max_participants=data.max_participants,
        scheduled_date=data.scheduled_date,
        scheduled_start_time=data.scheduled_start_time,
        scheduled_end_time=data.scheduled_end_time,
        location=data.location,
        status=TrainingStatus.SCHEDULED,
        trainer_id=data.trainer_id,
        external_trainer_name=data.external_trainer_name,
        provides_certification=data.provides_certification,
        certification_level_granted=data.certification_level_granted,
        cost_per_person=data.cost_per_person,
        materials_url=data.materials_url,
        syllabus=data.syllabus,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(training)
    await db.flush()
    await db.refresh(training)

    # Persist primary write first; lineage is best-effort enrichment.
    await db.commit()

    # Best-effort: capture lineage links (do not block training creation).
    try:
        await get_data_lineage_service().capture_training_created(
            db,
            training_id=training.id,
            skill_id=training.skill_id,
            created_by_id=current_user.id,
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="training",
                entity_id=str(training.id),
                reasoning_id=x_reasoning_id,
                created_by_id=current_user.id,
                source="training_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()

    response = TrainingResponse.model_validate(training)
    response.enrolled_count = training.enrolled_count
    response.has_capacity = training.has_capacity
    response.is_upcoming = training.is_upcoming
    return build_created_response(data=response, resource_name="Training")


@router.get(
    "/trainings/{training_id}",
    response_model=APIResponse[TrainingResponse],
    summary="Get training",
    description="Get a training by ID.",
)
async def get_training(
    training_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TrainingResponse]:
    stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    ).options(selectinload(Training.participants))
    result = await db.execute(stmt)
    training = result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    response = TrainingResponse.model_validate(training)
    response.enrolled_count = training.enrolled_count
    response.has_capacity = training.has_capacity
    response.is_upcoming = training.is_upcoming
    return build_response(response)


@router.get(
    "/trainings",
    response_model=PaginatedResponse[TrainingResponse],
    summary="List trainings",
    description="List trainings with filtering and pagination.",
)
async def list_trainings(
    db: DBSession,
    current_user: CurrentUser,
    skill_id: Optional[int] = Query(default=None),
    training_type: Optional[TrainingType] = Query(default=None),
    status: Optional[TrainingStatus] = Query(default=None),
    trainer_id: Optional[UUID] = Query(default=None),
    upcoming_only: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TrainingResponse]:
    base_conditions: list[Any] = [Training.deleted_at.is_(None)]

    if skill_id is not None and isinstance(skill_id, int):
        base_conditions.append(Training.skill_id == skill_id)
    if training_type and isinstance(training_type, TrainingType):
        base_conditions.append(Training.training_type == training_type)
    if status and isinstance(status, TrainingStatus):
        base_conditions.append(Training.status == status)
    if trainer_id is not None and isinstance(trainer_id, UUID):
        base_conditions.append(Training.trainer_id == trainer_id)
    if upcoming_only is True:
        base_conditions.append(Training.scheduled_date > _today())
    if search and isinstance(search, str):
        search_filter = or_(
            Training.name.ilike(f"%{search}%"),
            Training.code.ilike(f"%{search}%"),
            Training.description.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    count_stmt = select(func.count(Training.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Training)
        .where(and_(*base_conditions))
        .options(selectinload(Training.participants))
        .order_by(Training.scheduled_date.desc().nullslast(), Training.name)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    trainings = data_result.scalars().all()

    items = []
    for training in trainings:
        response = TrainingResponse.model_validate(training)
        response.enrolled_count = training.enrolled_count
        response.has_capacity = training.has_capacity
        response.is_upcoming = training.is_upcoming
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/trainings/{training_id}",
    response_model=APIResponse[TrainingResponse],
    summary="Update training",
    description="Update a training event.",
)
async def update_training(
    training_id: int,
    data: TrainingUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TrainingResponse]:
    stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    ).options(selectinload(Training.participants))
    result = await db.execute(stmt)
    training = result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(training, field, value)

    training.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(training)

    response = TrainingResponse.model_validate(training)
    response.enrolled_count = training.enrolled_count
    response.has_capacity = training.has_capacity
    response.is_upcoming = training.is_upcoming
    return build_updated_response(response, "Training")


@router.delete(
    "/trainings/{training_id}",
    response_model=APIResponse[None],
    summary="Delete training",
    description="Soft delete a training.",
)
async def delete_training(
    training_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    training = result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    training.deleted_at = _now_utc()
    training.deleted_by_id = current_user.id
    # Note: is_deleted is a read-only property derived from deleted_at
    await db.flush()

    return build_deleted_response("Training")


# =============================================================================
# Training Status Workflow Endpoints
# =============================================================================


@router.post(
    "/trainings/{training_id}/start",
    response_model=APIResponse[TrainingResponse],
    summary="Start training",
    description="Mark training as in progress.",
)
async def start_training(
    training_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TrainingResponse]:
    stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    ).options(selectinload(Training.participants))
    result = await db.execute(stmt)
    training = result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    if training.status != TrainingStatus.SCHEDULED:
        raise ConflictError(
            f"Cannot start training in '{training.status.value}' status"
        )

    training.status = TrainingStatus.IN_PROGRESS
    training.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(training)

    response = TrainingResponse.model_validate(training)
    response.enrolled_count = training.enrolled_count
    response.has_capacity = training.has_capacity
    response.is_upcoming = training.is_upcoming
    return build_response(response, "Training started")


@router.post(
    "/trainings/{training_id}/complete",
    response_model=APIResponse[TrainingResponse],
    summary="Complete training",
    description="Mark training as completed.",
)
async def complete_training(
    training_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TrainingResponse]:
    stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    ).options(selectinload(Training.participants))
    result = await db.execute(stmt)
    training = result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    if training.status not in [TrainingStatus.SCHEDULED, TrainingStatus.IN_PROGRESS]:
        raise ConflictError(
            f"Cannot complete training in '{training.status.value}' status"
        )

    training.status = TrainingStatus.COMPLETED
    training.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(training)

    response = TrainingResponse.model_validate(training)
    response.enrolled_count = training.enrolled_count
    response.has_capacity = training.has_capacity
    response.is_upcoming = training.is_upcoming
    return build_response(response, "Training completed")


@router.post(
    "/trainings/{training_id}/cancel",
    response_model=APIResponse[TrainingResponse],
    summary="Cancel training",
    description="Cancel a training event.",
)
async def cancel_training(
    training_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TrainingResponse]:
    stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    ).options(selectinload(Training.participants))
    result = await db.execute(stmt)
    training = result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    if training.status == TrainingStatus.COMPLETED:
        raise ConflictError("Cannot cancel a completed training")

    training.status = TrainingStatus.CANCELLED
    training.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(training)

    response = TrainingResponse.model_validate(training)
    response.enrolled_count = training.enrolled_count
    response.has_capacity = training.has_capacity
    response.is_upcoming = training.is_upcoming
    return build_response(response, "Training cancelled")


# =============================================================================
# Training Participant Endpoints
# =============================================================================


@router.post(
    "/trainings/{training_id}/participants",
    response_model=APIResponse[ParticipantResponse],
    status_code=201,
    summary="Enroll participant",
    description="Enroll a user in a training.",
)
async def enroll_participant(
    training_id: int,
    data: ParticipantEnroll,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[ParticipantResponse]:
    # Check training exists
    training_stmt = select(Training).where(
        and_(Training.id == training_id, Training.deleted_at.is_(None))
    ).options(selectinload(Training.participants))
    training_result = await db.execute(training_stmt)
    training = training_result.scalar_one_or_none()
    if not training:
        raise NotFoundError(f"Training {training_id} not found")

    # Check if already enrolled
    dup_stmt = select(TrainingParticipant).where(
        and_(
            TrainingParticipant.training_id == training_id,
            TrainingParticipant.user_id == data.user_id,
        )
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise ConflictError("User is already enrolled in this training")

    # Check capacity
    enrollment_status = EnrollmentStatus.ENROLLED
    if not training.has_capacity:
        enrollment_status = EnrollmentStatus.WAITLISTED

    participant = TrainingParticipant(
        training_id=training_id,
        user_id=data.user_id,
        enrollment_status=enrollment_status,
        attendance_status=AttendanceStatus.PENDING,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(participant)
    await db.flush()
    await db.refresh(participant)

    # Persist primary write first; lineage is best-effort enrichment.
    await db.commit()

    # Best-effort: capture lineage links (do not block enrollment).
    try:
        await get_data_lineage_service().capture_training_participant_enrolled(
            db,
            training_id=training_id,
            participant_id=participant.id,
            user_id=participant.user_id,
            created_by_id=current_user.id,
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="training_participant",
                entity_id=str(participant.id),
                reasoning_id=x_reasoning_id,
                created_by_id=current_user.id,
                source="training_enroll",
            )

        await db.commit()
    except Exception:
        await db.rollback()

    status_msg = "enrolled" if enrollment_status == EnrollmentStatus.ENROLLED else "waitlisted"
    return build_response(
        data=ParticipantResponse.model_validate(participant),
        message=f"Participant {status_msg}"
    )


@router.get(
    "/trainings/{training_id}/participants",
    response_model=PaginatedResponse[ParticipantResponse],
    summary="List participants",
    description="List participants for a training.",
)
async def list_participants(
    training_id: int,
    db: DBSession,
    current_user: CurrentUser,
    enrollment_status: Optional[EnrollmentStatus] = Query(default=None),
    attendance_status: Optional[AttendanceStatus] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ParticipantResponse]:
    base_conditions: list[Any] = [TrainingParticipant.training_id == training_id]

    if enrollment_status and isinstance(enrollment_status, EnrollmentStatus):
        base_conditions.append(TrainingParticipant.enrollment_status == enrollment_status)
    if attendance_status and isinstance(attendance_status, AttendanceStatus):
        base_conditions.append(TrainingParticipant.attendance_status == attendance_status)

    count_stmt = select(func.count(TrainingParticipant.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(TrainingParticipant)
        .where(and_(*base_conditions))
        .order_by(TrainingParticipant.created_at)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    participants = data_result.scalars().all()

    items = [ParticipantResponse.model_validate(p) for p in participants]
    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/trainings/{training_id}/participants/{participant_id}",
    response_model=APIResponse[ParticipantResponse],
    summary="Update participant",
    description="Update a training participant record.",
)
async def update_participant(
    training_id: int,
    participant_id: int,
    data: ParticipantUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ParticipantResponse]:
    stmt = select(TrainingParticipant).where(
        and_(
            TrainingParticipant.id == participant_id,
            TrainingParticipant.training_id == training_id,
        )
    )
    result = await db.execute(stmt)
    participant = result.scalar_one_or_none()
    if not participant:
        raise NotFoundError(f"Participant {participant_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(participant, field, value)

    participant.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(participant)

    return build_updated_response(
        ParticipantResponse.model_validate(participant),
        "Participant"
    )


@router.post(
    "/trainings/{training_id}/participants/{participant_id}/complete",
    response_model=APIResponse[ParticipantResponse],
    summary="Complete participation",
    description="Mark participant as having completed training.",
)
async def complete_participation(
    training_id: int,
    participant_id: int,
    data: ParticipantComplete,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ParticipantResponse]:
    stmt = select(TrainingParticipant).where(
        and_(
            TrainingParticipant.id == participant_id,
            TrainingParticipant.training_id == training_id,
        )
    )
    result = await db.execute(stmt)
    participant = result.scalar_one_or_none()
    if not participant:
        raise NotFoundError(f"Participant {participant_id} not found")

    participant.enrollment_status = EnrollmentStatus.COMPLETED
    participant.attendance_status = AttendanceStatus.ATTENDED
    participant.score = data.score
    participant.passed = data.passed
    participant.completed_at = _now_utc()
    participant.notes = data.notes or participant.notes
    if data.certificate_number:
        participant.certificate_number = data.certificate_number
        participant.certificate_issued_at = _now_utc()
    participant.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(participant)

    return build_response(
        ParticipantResponse.model_validate(participant),
        "Participation completed"
    )


@router.delete(
    "/trainings/{training_id}/participants/{participant_id}",
    response_model=APIResponse[None],
    summary="Remove participant",
    description="Remove a participant from a training.",
)
async def remove_participant(
    training_id: int,
    participant_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(TrainingParticipant).where(
        and_(
            TrainingParticipant.id == participant_id,
            TrainingParticipant.training_id == training_id,
        )
    )
    result = await db.execute(stmt)
    participant = result.scalar_one_or_none()
    if not participant:
        raise NotFoundError(f"Participant {participant_id} not found")

    await db.delete(participant)
    await db.flush()

    return build_deleted_response("Participant")


# =============================================================================
# User Skill Endpoints
# =============================================================================


@router.post(
    "/user-skills",
    response_model=APIResponse[UserSkillResponse],
    status_code=201,
    summary="Create user skill",
    description="Create a user skill record.",
)
async def create_user_skill(
    data: UserSkillCreate,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[UserSkillResponse]:
    # Check skill exists
    skill_stmt = select(Skill).where(
        and_(Skill.id == data.skill_id, Skill.deleted_at.is_(None))
    )
    skill_result = await db.execute(skill_stmt)
    if not skill_result.scalar_one_or_none():
        raise NotFoundError(f"Skill {data.skill_id} not found")

    # Check for duplicate
    dup_stmt = select(UserSkill).where(
        and_(
            UserSkill.user_id == data.user_id,
            UserSkill.skill_id == data.skill_id,
        )
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise ConflictError("User skill record already exists")

    user_skill = UserSkill(
        user_id=data.user_id,
        skill_id=data.skill_id,
        proficiency_level=data.proficiency_level,
        certification_status=CertificationStatus.NOT_CERTIFIED,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(user_skill)
    await db.flush()
    await db.refresh(user_skill)

    # Persist primary write first; lineage is best-effort enrichment.
    await db.commit()

    # Best-effort: capture lineage links (do not block user-skill creation).
    try:
        await get_data_lineage_service().capture_user_skill_created(
            db,
            user_skill_id=user_skill.id,
            user_id=user_skill.user_id,
            skill_id=user_skill.skill_id,
            created_by_id=current_user.id,
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="user_skill",
                entity_id=str(user_skill.id),
                reasoning_id=x_reasoning_id,
                created_by_id=current_user.id,
                source="user_skill_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()

    response = UserSkillResponse.model_validate(user_skill)
    response.is_certified = user_skill.is_certified
    response.is_expired = user_skill.is_expired
    response.days_until_expiration = user_skill.days_until_expiration
    response.needs_recertification_soon = user_skill.needs_recertification_soon
    return build_created_response(data=response, resource_name="User skill")


@router.get(
    "/user-skills",
    response_model=PaginatedResponse[UserSkillResponse],
    summary="List user skills",
    description="List user skills with filtering.",
)
async def list_user_skills(
    db: DBSession,
    current_user: CurrentUser,
    user_id: Optional[UUID] = Query(default=None),
    skill_id: Optional[int] = Query(default=None),
    certification_status: Optional[CertificationStatus] = Query(default=None),
    expiring_soon: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[UserSkillResponse]:
    base_conditions: list[Any] = []

    if user_id is not None and isinstance(user_id, UUID):
        base_conditions.append(UserSkill.user_id == user_id)
    if skill_id is not None and isinstance(skill_id, int):
        base_conditions.append(UserSkill.skill_id == skill_id)
    if certification_status and isinstance(certification_status, CertificationStatus):
        base_conditions.append(UserSkill.certification_status == certification_status)

    # Expiring soon filter
    if expiring_soon is True:
        threshold = _today()
        thirty_days = date.fromordinal(threshold.toordinal() + 30)
        base_conditions.append(UserSkill.expiration_date <= thirty_days)
        base_conditions.append(UserSkill.expiration_date > threshold)

    if base_conditions:
        where_clause = and_(*base_conditions)
    else:
        where_clause = UserSkill.id.isnot(None)  # Always true condition

    count_stmt = select(func.count(UserSkill.id)).where(where_clause)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(UserSkill)
        .where(where_clause)
        .order_by(UserSkill.user_id, UserSkill.skill_id)
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    user_skills = data_result.scalars().all()

    items = []
    for us in user_skills:
        response = UserSkillResponse.model_validate(us)
        response.is_certified = us.is_certified
        response.is_expired = us.is_expired
        response.days_until_expiration = us.days_until_expiration
        response.needs_recertification_soon = us.needs_recertification_soon
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/user-skills/{user_skill_id}",
    response_model=APIResponse[UserSkillResponse],
    summary="Update user skill",
    description="Update a user skill record.",
)
async def update_user_skill(
    user_skill_id: int,
    data: UserSkillUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[UserSkillResponse]:
    stmt = select(UserSkill).where(UserSkill.id == user_skill_id)
    result = await db.execute(stmt)
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise NotFoundError(f"User skill {user_skill_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_skill, field, value)

    user_skill.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(user_skill)

    response = UserSkillResponse.model_validate(user_skill)
    response.is_certified = user_skill.is_certified
    response.is_expired = user_skill.is_expired
    response.days_until_expiration = user_skill.days_until_expiration
    response.needs_recertification_soon = user_skill.needs_recertification_soon
    return build_updated_response(response, "User skill")


@router.post(
    "/user-skills/{user_skill_id}/certify",
    response_model=APIResponse[UserSkillResponse],
    summary="Certify user skill",
    description="Certify a user for a skill.",
)
async def certify_user_skill(
    user_skill_id: int,
    data: UserSkillCertify,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[UserSkillResponse]:
    stmt = select(UserSkill).where(UserSkill.id == user_skill_id)
    result = await db.execute(stmt)
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise NotFoundError(f"User skill {user_skill_id} not found")

    user_skill.proficiency_level = data.proficiency_level
    user_skill.certification_status = CertificationStatus.CERTIFIED
    user_skill.certified_date = _today()
    user_skill.expiration_date = data.expiration_date
    user_skill.certified_by_id = current_user.id
    user_skill.certificate_number = data.certificate_number
    user_skill.notes = data.notes or user_skill.notes
    user_skill.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(user_skill)

    # Persist primary write first; reasoning is best-effort enrichment.
    await db.commit()

    # Best-effort: record reasoning (lineage already links user+skill to user_skill).
    try:
        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="user_skill",
                entity_id=str(user_skill.id),
                reasoning_id=x_reasoning_id,
                created_by_id=current_user.id,
                source="user_skill_certify",
            )
            await db.commit()
    except Exception:
        await db.rollback()

    response = UserSkillResponse.model_validate(user_skill)
    response.is_certified = user_skill.is_certified
    response.is_expired = user_skill.is_expired
    response.days_until_expiration = user_skill.days_until_expiration
    response.needs_recertification_soon = user_skill.needs_recertification_soon
    return build_response(response, "User certified for skill")


@router.post(
    "/user-skills/{user_skill_id}/revoke",
    response_model=APIResponse[UserSkillResponse],
    summary="Revoke certification",
    description="Revoke a user's certification for a skill.",
)
async def revoke_certification(
    user_skill_id: int,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[UserSkillResponse]:
    stmt = select(UserSkill).where(UserSkill.id == user_skill_id)
    result = await db.execute(stmt)
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise NotFoundError(f"User skill {user_skill_id} not found")

    if user_skill.certification_status != CertificationStatus.CERTIFIED:
        raise ConflictError(
            f"Cannot revoke certification in '{user_skill.certification_status.value}' status"
        )

    user_skill.certification_status = CertificationStatus.REVOKED
    user_skill.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(user_skill)

    # Persist primary write first; reasoning is best-effort enrichment.
    await db.commit()

    try:
        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="user_skill",
                entity_id=str(user_skill.id),
                reasoning_id=x_reasoning_id,
                created_by_id=current_user.id,
                source="user_skill_revoke",
            )
            await db.commit()
    except Exception:
        await db.rollback()

    response = UserSkillResponse.model_validate(user_skill)
    response.is_certified = user_skill.is_certified
    response.is_expired = user_skill.is_expired
    response.days_until_expiration = user_skill.days_until_expiration
    response.needs_recertification_soon = user_skill.needs_recertification_soon
    return build_response(response, "Certification revoked")


@router.delete(
    "/user-skills/{user_skill_id}",
    response_model=APIResponse[None],
    summary="Delete user skill",
    description="Delete a user skill record.",
)
async def delete_user_skill(
    user_skill_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(UserSkill).where(UserSkill.id == user_skill_id)
    result = await db.execute(stmt)
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise NotFoundError(f"User skill {user_skill_id} not found")

    await db.delete(user_skill)
    await db.flush()

    return build_deleted_response("User skill")

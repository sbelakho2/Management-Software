"""Risk Management API endpoints.

Provides comprehensive API for managing risks and mitigations:
- Risk CRUD operations
- Risk workflow (analyze, mitigate, close, accept, record occurrence)
- Risk mitigations (add, update, complete, delete)
- Query endpoints (by number, high priority, open risks)
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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
)
from sensei.models.risk import (
    Risk,
    RiskMitigation,
    RiskCategory,
    RiskStatus,
    RiskSeverity,
    RiskLikelihood,
    MitigationStatus,
)


router = APIRouter(
    dependencies=[Depends(RoleChecker(["admin", "ceo", "gm", "exec", "ops", "quality", "engineering", "sales", "finance", "auditor"]))],
)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class RiskCreate(BaseModel):
    """Schema for creating a risk."""

    risk_number: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    category: RiskCategory = Field(default=RiskCategory.TECHNICAL)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    rfq_id: Optional[UUID] = None
    inherent_likelihood: RiskLikelihood = Field(default=RiskLikelihood.POSSIBLE)
    inherent_severity: RiskSeverity = Field(default=RiskSeverity.MODERATE)
    potential_cost: Optional[Decimal] = None
    currency: str = Field(default="MAD", max_length=3)
    potential_delay_days: Optional[int] = None
    root_causes: Optional[list] = None
    potential_effects: Optional[list] = None
    risk_triggers: Optional[list] = None
    early_warning_signs: Optional[list] = None
    response_strategy: Optional[str] = None
    response_plan: Optional[str] = None
    contingency_plan: Optional[str] = None
    risk_owner_id: Optional[UUID] = None
    identified_date: Optional[datetime] = None
    target_resolution_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[list] = None


class RiskUpdate(BaseModel):
    """Schema for updating a risk."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[RiskCategory] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    rfq_id: Optional[UUID] = None
    inherent_likelihood: Optional[RiskLikelihood] = None
    inherent_severity: Optional[RiskSeverity] = None
    residual_likelihood: Optional[RiskLikelihood] = None
    residual_severity: Optional[RiskSeverity] = None
    potential_cost: Optional[Decimal] = None
    currency: Optional[str] = None
    potential_delay_days: Optional[int] = None
    root_causes: Optional[list] = None
    potential_effects: Optional[list] = None
    risk_triggers: Optional[list] = None
    early_warning_signs: Optional[list] = None
    response_strategy: Optional[str] = None
    response_plan: Optional[str] = None
    contingency_plan: Optional[str] = None
    risk_owner_id: Optional[UUID] = None
    target_resolution_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    notes: Optional[str] = None
    tags: Optional[list] = None


class RiskResponse(BaseModel):
    """Schema for risk response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    risk_number: str
    title: str
    description: str
    category: str
    status: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    rfq_id: Optional[UUID] = None
    inherent_likelihood: str
    inherent_severity: str
    inherent_likelihood_score: int
    inherent_severity_score: int
    inherent_risk_score: int
    residual_likelihood: Optional[str] = None
    residual_severity: Optional[str] = None
    residual_likelihood_score: Optional[int] = None
    residual_severity_score: Optional[int] = None
    residual_risk_score: Optional[int] = None
    potential_cost: Optional[Decimal] = None
    currency: str
    potential_delay_days: Optional[int] = None
    root_causes: Optional[list] = None
    potential_effects: Optional[list] = None
    risk_triggers: Optional[list] = None
    early_warning_signs: Optional[list] = None
    response_strategy: Optional[str] = None
    response_plan: Optional[str] = None
    contingency_plan: Optional[str] = None
    risk_owner_id: Optional[UUID] = None
    identified_date: datetime
    target_resolution_date: Optional[datetime] = None
    actual_resolution_date: Optional[datetime] = None
    last_review_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    occurred_date: Optional[datetime] = None
    actual_impact: Optional[str] = None
    actual_cost: Optional[Decimal] = None
    lessons_learned: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list] = None
    risk_level: str
    is_open: bool
    created_at: datetime
    updated_at: datetime


class ResidualAssessmentData(BaseModel):
    """Schema for residual risk assessment."""

    residual_likelihood: RiskLikelihood
    residual_severity: RiskSeverity


class OccurrenceData(BaseModel):
    """Schema for recording risk occurrence."""

    occurred_date: Optional[datetime] = None
    actual_impact: Optional[str] = None
    actual_cost: Optional[Decimal] = None
    lessons_learned: Optional[str] = None


class MitigationCreate(BaseModel):
    """Schema for creating a mitigation."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    mitigation_type: Optional[str] = None
    reduces_likelihood: bool = Field(default=True)
    reduces_severity: bool = Field(default=False)
    expected_likelihood_reduction: Optional[int] = None
    expected_severity_reduction: Optional[int] = None
    priority: str = Field(default="medium")
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    assigned_to_id: Optional[UUID] = None
    estimated_cost: Optional[Decimal] = None
    currency: str = Field(default="MAD")
    notes: Optional[str] = None


class MitigationUpdate(BaseModel):
    """Schema for updating a mitigation."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    mitigation_type: Optional[str] = None
    reduces_likelihood: Optional[bool] = None
    reduces_severity: Optional[bool] = None
    expected_likelihood_reduction: Optional[int] = None
    expected_severity_reduction: Optional[int] = None
    status: Optional[MitigationStatus] = None
    priority: Optional[str] = None
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    assigned_to_id: Optional[UUID] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    currency: Optional[str] = None
    completion_percentage: Optional[int] = None
    completion_notes: Optional[str] = None
    effectiveness_rating: Optional[int] = None
    effectiveness_notes: Optional[str] = None
    evidence: Optional[list] = None
    notes: Optional[str] = None


class MitigationResponse(BaseModel):
    """Schema for mitigation response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    risk_id: UUID
    title: str
    description: str
    mitigation_type: Optional[str] = None
    reduces_likelihood: bool
    reduces_severity: bool
    expected_likelihood_reduction: Optional[int] = None
    expected_severity_reduction: Optional[int] = None
    status: str
    priority: str
    planned_start_date: Optional[datetime] = None
    planned_end_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    assigned_to_id: Optional[UUID] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    currency: str
    effectiveness_rating: Optional[int] = None
    effectiveness_notes: Optional[str] = None
    completion_percentage: int
    completion_notes: Optional[str] = None
    evidence: Optional[list] = None
    notes: Optional[str] = None
    is_complete: bool
    is_overdue: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Risk CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=APIResponse[RiskResponse],
    status_code=201,
    summary="Create risk",
    description="Create a new risk entry in the risk register.",
)
async def create_risk(
    data: RiskCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    # Check for duplicate risk_number
    stmt = select(Risk).where(
        and_(
            Risk.risk_number == data.risk_number,
            Risk.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"Risk with number '{data.risk_number}' already exists")

    risk = Risk(
        risk_number=data.risk_number,
        title=data.title,
        description=data.description,
        category=(
            data.category.value
            if isinstance(data.category, RiskCategory)
            else data.category
        ),
        status=RiskStatus.IDENTIFIED.value,
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
        rfq_id=data.rfq_id,
        inherent_likelihood=(
            data.inherent_likelihood.value
            if isinstance(data.inherent_likelihood, RiskLikelihood)
            else data.inherent_likelihood
        ),
        inherent_severity=(
            data.inherent_severity.value
            if isinstance(data.inherent_severity, RiskSeverity)
            else data.inherent_severity
        ),
        potential_cost=data.potential_cost,
        currency=data.currency,
        potential_delay_days=data.potential_delay_days,
        root_causes=data.root_causes,
        potential_effects=data.potential_effects,
        risk_triggers=data.risk_triggers,
        early_warning_signs=data.early_warning_signs,
        response_strategy=data.response_strategy,
        response_plan=data.response_plan,
        contingency_plan=data.contingency_plan,
        risk_owner_id=data.risk_owner_id,
        identified_date=data.identified_date or datetime.now(timezone.utc),
        target_resolution_date=data.target_resolution_date,
        next_review_date=data.next_review_date,
        notes=data.notes,
        tags=data.tags or [],
        created_by_id=current_user.id,
        owner_id=data.risk_owner_id or current_user.id,
    )

    # Calculate scores
    risk.calculate_risk_scores()

    db.add(risk)
    await db.flush()
    await db.refresh(risk)

    return build_created_response(
        data=RiskResponse.model_validate(risk),
        resource_name="Risk",
    )


@router.get(
    "/{risk_id}",
    response_model=APIResponse[RiskResponse],
    summary="Get risk",
    description="Get a risk by ID.",
)
async def get_risk(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk retrieved successfully",
    )


@router.get(
    "",
    response_model=PaginatedResponse[RiskResponse],
    summary="List risks",
    description="List risks with filtering and pagination.",
)
async def list_risks(
    db: DBSession,
    current_user: CurrentUser,
    category: Optional[RiskCategory] = Query(default=None),
    status: Optional[RiskStatus] = Query(default=None),
    min_score: Optional[int] = Query(default=None, ge=1, le=25),
    risk_owner_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[RiskResponse]:
    base_conditions: list[Any] = [Risk.deleted_at.is_(None)]

    if category and isinstance(category, RiskCategory):
        base_conditions.append(Risk.category == category.value)
    if status and isinstance(status, RiskStatus):
        base_conditions.append(Risk.status == status.value)
    if min_score:
        base_conditions.append(Risk.inherent_risk_score >= min_score)
    if risk_owner_id:
        base_conditions.append(Risk.risk_owner_id == risk_owner_id)
    if search:
        search_filter = or_(
            Risk.title.ilike(f"%{search}%"),
            Risk.description.ilike(f"%{search}%"),
            Risk.risk_number.ilike(f"%{search}%"),
        )
        base_conditions.append(search_filter)

    # Count total
    count_stmt = select(func.count(Risk.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Fetch data with pagination
    offset = (page - 1) * page_size
    data_stmt = (
        select(Risk)
        .where(and_(*base_conditions))
        .order_by(Risk.inherent_risk_score.desc(), Risk.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    risks = data_result.scalars().all()

    items = [RiskResponse.model_validate(r) for r in risks]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{risk_id}",
    response_model=APIResponse[RiskResponse],
    summary="Update risk",
    description="Update a risk's details.",
)
async def update_risk(
    risk_id: UUID,
    data: RiskUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle enum values
    if "category" in update_data and update_data["category"]:
        if isinstance(update_data["category"], RiskCategory):
            update_data["category"] = update_data["category"].value
    if "inherent_likelihood" in update_data and update_data["inherent_likelihood"]:
        if isinstance(update_data["inherent_likelihood"], RiskLikelihood):
            update_data["inherent_likelihood"] = update_data["inherent_likelihood"].value
    if "inherent_severity" in update_data and update_data["inherent_severity"]:
        if isinstance(update_data["inherent_severity"], RiskSeverity):
            update_data["inherent_severity"] = update_data["inherent_severity"].value
    if "residual_likelihood" in update_data and update_data["residual_likelihood"]:
        if isinstance(update_data["residual_likelihood"], RiskLikelihood):
            update_data["residual_likelihood"] = update_data["residual_likelihood"].value
    if "residual_severity" in update_data and update_data["residual_severity"]:
        if isinstance(update_data["residual_severity"], RiskSeverity):
            update_data["residual_severity"] = update_data["residual_severity"].value

    for key, value in update_data.items():
        setattr(risk, key, value)

    risk.updated_by_id = current_user.id
    risk.calculate_risk_scores()

    await db.flush()
    await db.refresh(risk)

    return build_updated_response(
        data=RiskResponse.model_validate(risk),
        resource_name="Risk",
    )


@router.delete(
    "/{risk_id}",
    response_model=APIResponse,
    summary="Delete risk",
    description="Soft delete a risk.",
)
async def delete_risk(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    risk.deleted_at = datetime.now(timezone.utc)
    risk.deleted_by_id = current_user.id
    await db.flush()

    return build_deleted_response(resource_name="Risk")


# =============================================================================
# Risk Workflow Endpoints
# =============================================================================


@router.post(
    "/{risk_id}/analyze",
    response_model=APIResponse[RiskResponse],
    summary="Start analysis",
    description="Move risk to analyzing status.",
)
async def analyze_risk(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    if risk.status != RiskStatus.IDENTIFIED.value:
        raise ConflictError("Risk must be in 'identified' status to analyze")

    risk.status = RiskStatus.ANALYZING.value
    risk.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk analysis started",
    )


@router.post(
    "/{risk_id}/mitigate",
    response_model=APIResponse[RiskResponse],
    summary="Start mitigation",
    description="Move risk to mitigating status.",
)
async def start_mitigation(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    valid_statuses = [RiskStatus.IDENTIFIED.value, RiskStatus.ANALYZING.value]
    if risk.status not in valid_statuses:
        raise ConflictError("Risk must be in 'identified' or 'analyzing' status to mitigate")

    risk.status = RiskStatus.MITIGATING.value
    risk.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk mitigation started",
    )


@router.post(
    "/{risk_id}/monitor",
    response_model=APIResponse[RiskResponse],
    summary="Move to monitoring",
    description="Move risk to monitoring status after mitigation.",
)
async def monitor_risk(
    risk_id: UUID,
    data: ResidualAssessmentData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    if risk.status != RiskStatus.MITIGATING.value:
        raise ConflictError("Risk must be in 'mitigating' status to move to monitoring")

    risk.status = RiskStatus.MONITORING.value
    risk.residual_likelihood = (
        data.residual_likelihood.value
        if isinstance(data.residual_likelihood, RiskLikelihood)
        else data.residual_likelihood
    )
    risk.residual_severity = (
        data.residual_severity.value
        if isinstance(data.residual_severity, RiskSeverity)
        else data.residual_severity
    )
    risk.last_review_date = datetime.now(timezone.utc)
    risk.updated_by_id = current_user.id
    risk.calculate_risk_scores()

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk moved to monitoring",
    )


@router.post(
    "/{risk_id}/close",
    response_model=APIResponse[RiskResponse],
    summary="Close risk",
    description="Close a risk that is no longer relevant.",
)
async def close_risk(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    if risk.status in [RiskStatus.CLOSED.value, RiskStatus.OCCURRED.value]:
        raise ConflictError(f"Risk is already in '{risk.status}' status")

    risk.status = RiskStatus.CLOSED.value
    risk.actual_resolution_date = datetime.now(timezone.utc)
    risk.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk closed",
    )


@router.post(
    "/{risk_id}/accept",
    response_model=APIResponse[RiskResponse],
    summary="Accept risk",
    description="Accept a risk without further mitigation.",
)
async def accept_risk(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    if risk.status in [RiskStatus.CLOSED.value, RiskStatus.OCCURRED.value]:
        raise ConflictError(f"Risk is already in '{risk.status}' status")

    risk.status = RiskStatus.ACCEPTED.value
    risk.actual_resolution_date = datetime.now(timezone.utc)
    risk.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk accepted",
    )


@router.post(
    "/{risk_id}/occurred",
    response_model=APIResponse[RiskResponse],
    summary="Record occurrence",
    description="Record that a risk has occurred.",
)
async def record_occurrence(
    risk_id: UUID,
    data: OccurrenceData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    if risk.status == RiskStatus.CLOSED.value:
        raise ConflictError("Cannot record occurrence for closed risk")

    risk.status = RiskStatus.OCCURRED.value
    risk.occurred_date = data.occurred_date or datetime.now(timezone.utc)
    risk.actual_impact = data.actual_impact
    risk.actual_cost = data.actual_cost
    risk.lessons_learned = data.lessons_learned
    risk.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk occurrence recorded",
    )


@router.post(
    "/{risk_id}/review",
    response_model=APIResponse[RiskResponse],
    summary="Record review",
    description="Record a review of the risk.",
)
async def record_review(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    next_review_date: Optional[datetime] = Query(default=None),
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    risk.last_review_date = datetime.now(timezone.utc)
    if next_review_date:
        risk.next_review_date = next_review_date
    risk.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(risk)

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk review recorded",
    )


# =============================================================================
# Risk Mitigation Endpoints
# =============================================================================


@router.post(
    "/{risk_id}/mitigations",
    response_model=APIResponse[MitigationResponse],
    status_code=201,
    summary="Add mitigation",
    description="Add a mitigation action to a risk.",
)
async def add_mitigation(
    risk_id: UUID,
    data: MitigationCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MitigationResponse]:
    stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    mitigation = RiskMitigation(
        risk_id=risk_id,
        title=data.title,
        description=data.description,
        mitigation_type=data.mitigation_type,
        reduces_likelihood=data.reduces_likelihood,
        reduces_severity=data.reduces_severity,
        expected_likelihood_reduction=data.expected_likelihood_reduction,
        expected_severity_reduction=data.expected_severity_reduction,
        status=MitigationStatus.PLANNED.value,
        priority=data.priority,
        planned_start_date=data.planned_start_date,
        planned_end_date=data.planned_end_date,
        assigned_to_id=data.assigned_to_id,
        estimated_cost=data.estimated_cost,
        currency=data.currency,
        notes=data.notes,
        created_by_id=current_user.id,
        owner_id=data.assigned_to_id or current_user.id,
    )

    db.add(mitigation)
    await db.flush()
    await db.refresh(mitigation)

    return build_created_response(
        data=MitigationResponse.model_validate(mitigation),
        resource_name="Mitigation",
    )


@router.get(
    "/{risk_id}/mitigations",
    response_model=PaginatedResponse[MitigationResponse],
    summary="List mitigations",
    description="List mitigations for a risk.",
)
async def list_mitigations(
    risk_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[MitigationStatus] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[MitigationResponse]:
    # Check risk exists
    risk_stmt = select(Risk).where(
        and_(Risk.id == risk_id, Risk.deleted_at.is_(None))
    )
    risk_result = await db.execute(risk_stmt)
    risk = risk_result.scalar_one_or_none()
    if not risk:
        raise NotFoundError(f"Risk {risk_id} not found")

    base_conditions: list[Any] = [RiskMitigation.risk_id == risk_id]

    if status and isinstance(status, MitigationStatus):
        base_conditions.append(RiskMitigation.status == status.value)

    count_stmt = select(func.count(RiskMitigation.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(RiskMitigation)
        .where(and_(*base_conditions))
        .order_by(RiskMitigation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    mitigations = data_result.scalars().all()

    items = [MitigationResponse.model_validate(m) for m in mitigations]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{risk_id}/mitigations/{mitigation_id}",
    response_model=APIResponse[MitigationResponse],
    summary="Get mitigation",
    description="Get a specific mitigation.",
)
async def get_mitigation(
    risk_id: UUID,
    mitigation_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MitigationResponse]:
    stmt = select(RiskMitigation).where(
        and_(
            RiskMitigation.id == mitigation_id,
            RiskMitigation.risk_id == risk_id,
        )
    )
    result = await db.execute(stmt)
    mitigation = result.scalar_one_or_none()

    if not mitigation:
        raise NotFoundError(f"Mitigation {mitigation_id} not found")

    return build_response(
        data=MitigationResponse.model_validate(mitigation),
        message="Mitigation retrieved successfully",
    )


@router.patch(
    "/{risk_id}/mitigations/{mitigation_id}",
    response_model=APIResponse[MitigationResponse],
    summary="Update mitigation",
    description="Update a mitigation action.",
)
async def update_mitigation(
    risk_id: UUID,
    mitigation_id: UUID,
    data: MitigationUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MitigationResponse]:
    stmt = select(RiskMitigation).where(
        and_(
            RiskMitigation.id == mitigation_id,
            RiskMitigation.risk_id == risk_id,
        )
    )
    result = await db.execute(stmt)
    mitigation = result.scalar_one_or_none()

    if not mitigation:
        raise NotFoundError(f"Mitigation {mitigation_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle enum values
    if "status" in update_data and update_data["status"]:
        if isinstance(update_data["status"], MitigationStatus):
            update_data["status"] = update_data["status"].value

    for key, value in update_data.items():
        setattr(mitigation, key, value)

    mitigation.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(mitigation)

    return build_updated_response(
        data=MitigationResponse.model_validate(mitigation),
        resource_name="Mitigation",
    )


@router.post(
    "/{risk_id}/mitigations/{mitigation_id}/complete",
    response_model=APIResponse[MitigationResponse],
    summary="Complete mitigation",
    description="Mark a mitigation as completed.",
)
async def complete_mitigation(
    risk_id: UUID,
    mitigation_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    effectiveness_rating: Optional[int] = Query(default=None, ge=1, le=5),
    effectiveness_notes: Optional[str] = Query(default=None),
) -> APIResponse[MitigationResponse]:
    stmt = select(RiskMitigation).where(
        and_(
            RiskMitigation.id == mitigation_id,
            RiskMitigation.risk_id == risk_id,
        )
    )
    result = await db.execute(stmt)
    mitigation = result.scalar_one_or_none()

    if not mitigation:
        raise NotFoundError(f"Mitigation {mitigation_id} not found")

    if mitigation.status == MitigationStatus.COMPLETED.value:
        raise ConflictError("Mitigation is already completed")

    mitigation.status = MitigationStatus.COMPLETED.value
    mitigation.completion_percentage = 100
    mitigation.actual_end_date = datetime.now(timezone.utc)
    if effectiveness_rating:
        mitigation.effectiveness_rating = effectiveness_rating
    if effectiveness_notes:
        mitigation.effectiveness_notes = effectiveness_notes
    mitigation.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(mitigation)

    return build_response(
        data=MitigationResponse.model_validate(mitigation),
        message="Mitigation completed",
    )


@router.delete(
    "/{risk_id}/mitigations/{mitigation_id}",
    response_model=APIResponse,
    summary="Delete mitigation",
    description="Delete a mitigation action.",
)
async def delete_mitigation(
    risk_id: UUID,
    mitigation_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse:
    stmt = select(RiskMitigation).where(
        and_(
            RiskMitigation.id == mitigation_id,
            RiskMitigation.risk_id == risk_id,
        )
    )
    result = await db.execute(stmt)
    mitigation = result.scalar_one_or_none()

    if not mitigation:
        raise NotFoundError(f"Mitigation {mitigation_id} not found")

    await db.delete(mitigation)
    await db.flush()

    return build_deleted_response(resource_name="Mitigation")


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get(
    "/by-number/{risk_number}",
    response_model=APIResponse[RiskResponse],
    summary="Get risk by number",
    description="Get a risk by its document number.",
)
async def get_risk_by_number(
    risk_number: str,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RiskResponse]:
    stmt = select(Risk).where(
        and_(Risk.risk_number == risk_number, Risk.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    risk = result.scalar_one_or_none()

    if not risk:
        raise NotFoundError(f"Risk with number '{risk_number}' not found")

    return build_response(
        data=RiskResponse.model_validate(risk),
        message="Risk retrieved successfully",
    )


@router.get(
    "/high-priority",
    response_model=PaginatedResponse[RiskResponse],
    summary="Get high priority risks",
    description="Get risks with high or critical risk scores (>=12).",
)
async def get_high_priority_risks(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[RiskResponse]:
    base_conditions: list[Any] = [
        Risk.deleted_at.is_(None),
        Risk.inherent_risk_score >= 12,
        Risk.status.notin_([
            RiskStatus.CLOSED.value,
            RiskStatus.OCCURRED.value,
            RiskStatus.ACCEPTED.value,
        ]),
    ]

    count_stmt = select(func.count(Risk.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Risk)
        .where(and_(*base_conditions))
        .order_by(Risk.inherent_risk_score.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    risks = data_result.scalars().all()

    items = [RiskResponse.model_validate(r) for r in risks]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/open",
    response_model=PaginatedResponse[RiskResponse],
    summary="Get open risks",
    description="Get all open (non-closed) risks.",
)
async def get_open_risks(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[RiskResponse]:
    base_conditions: list[Any] = [
        Risk.deleted_at.is_(None),
        Risk.status.notin_([
            RiskStatus.CLOSED.value,
            RiskStatus.OCCURRED.value,
            RiskStatus.ACCEPTED.value,
        ]),
    ]

    count_stmt = select(func.count(Risk.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Risk)
        .where(and_(*base_conditions))
        .order_by(Risk.inherent_risk_score.desc(), Risk.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    risks = data_result.scalars().all()

    items = [RiskResponse.model_validate(r) for r in risks]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/needs-review",
    response_model=PaginatedResponse[RiskResponse],
    summary="Get risks needing review",
    description="Get risks due for review.",
)
async def get_risks_needing_review(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[RiskResponse]:
    now = datetime.now(timezone.utc)
    base_conditions: list[Any] = [
        Risk.deleted_at.is_(None),
        Risk.status.notin_([
            RiskStatus.CLOSED.value,
            RiskStatus.OCCURRED.value,
            RiskStatus.ACCEPTED.value,
        ]),
        or_(
            Risk.next_review_date <= now,
            Risk.next_review_date == None,
        ),
    ]

    count_stmt = select(func.count(Risk.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(Risk)
        .where(and_(*base_conditions))
        .order_by(Risk.next_review_date.asc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    risks = data_result.scalars().all()

    items = [RiskResponse.model_validate(r) for r in risks]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )

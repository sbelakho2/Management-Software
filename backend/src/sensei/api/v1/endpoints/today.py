"""
Today Screen (Manager GPS) API endpoints.

Provides API endpoints for the Today Screen dashboard, including:
- Priority management (top 3 selection)
- Risk tracking
- Commitment management
- Abnormality tracking
- Micro-drill questions
- Full dashboard data aggregation
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.services.ops.today_screen import (
    TodayScreenService,
    TodayScreenData,
    Priority,
    Risk,
    Commitment,
    Abnormality,
    MicroDrill,
    LSWChecklistSummary,
    QuickMetric,
    RiskCategory,
    AbnormalityType,
    CommitmentType,
    PriorityLevel,
    LSWChecklistStatus,
    get_today_screen_service,
)

router = APIRouter(prefix="/today", tags=["today-screen"])


# ============================================================================
# Schemas
# ============================================================================


class PriorityCreateSchema(BaseModel):
    """Schema for creating a priority."""

    entity_type: str = Field(..., description="Type of entity (quote, rfq, task, etc.)")
    entity_id: UUID = Field(..., description="ID of the entity")
    title: str = Field(..., min_length=1, max_length=500)
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    description: str | None = None
    due_date: date | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None


class PriorityResponseSchema(BaseModel):
    """Schema for priority response."""

    id: UUID
    title: str
    description: str | None
    entity_type: str
    entity_id: UUID
    priority_level: PriorityLevel
    due_date: date | None
    owner_id: UUID | None
    owner_name: str | None
    is_user_selected: bool
    rank: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SetTopPrioritiesSchema(BaseModel):
    """Schema for setting top 3 priorities."""

    priority_ids: list[UUID] = Field(..., max_length=3, description="List of priority IDs (max 3)")


class RiskCreateSchema(BaseModel):
    """Schema for creating a risk."""

    title: str = Field(..., min_length=1, max_length=500)
    category: RiskCategory
    severity: int = Field(..., ge=1, le=10)
    probability: int = Field(..., ge=1, le=10)
    description: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    mitigation: str | None = None
    due_date: date | None = None


class RiskResponseSchema(BaseModel):
    """Schema for risk response."""

    id: UUID
    title: str
    description: str | None
    category: RiskCategory
    severity: int
    probability: int
    risk_score: int
    entity_type: str | None
    entity_id: UUID | None
    owner_id: UUID | None
    owner_name: str | None
    mitigation: str | None
    due_date: date | None
    status: str

    model_config = {"from_attributes": True}


class CommitmentCreateSchema(BaseModel):
    """Schema for creating a commitment."""

    title: str = Field(..., min_length=1, max_length=500)
    commitment_type: CommitmentType
    due_date: date
    description: str | None = None
    due_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    entity_type: str | None = None
    entity_id: UUID | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    customer_name: str | None = None


class CommitmentResponseSchema(BaseModel):
    """Schema for commitment response."""

    id: UUID
    title: str
    description: str | None
    commitment_type: CommitmentType
    entity_type: str | None
    entity_id: UUID | None
    due_date: date
    due_time: str | None
    owner_id: UUID | None
    owner_name: str | None
    customer_name: str | None
    is_completed: bool
    is_overdue: bool

    model_config = {"from_attributes": True}


class AbnormalityCreateSchema(BaseModel):
    """Schema for creating an abnormality."""

    title: str = Field(..., min_length=1, max_length=500)
    abnormality_type: AbnormalityType
    entity_type: str
    entity_id: UUID
    days_stale: int = Field(0, ge=0)
    description: str | None = None
    severity: PriorityLevel = PriorityLevel.MEDIUM
    owner_id: UUID | None = None
    owner_name: str | None = None
    suggested_action: str | None = None


class AbnormalityResponseSchema(BaseModel):
    """Schema for abnormality response."""

    id: UUID
    title: str
    description: str | None
    abnormality_type: AbnormalityType
    entity_type: str
    entity_id: UUID
    detected_at: datetime
    days_stale: int
    severity: PriorityLevel
    owner_id: UUID | None
    owner_name: str | None
    suggested_action: str | None

    model_config = {"from_attributes": True}


class MicroDrillCreateSchema(BaseModel):
    """Schema for creating a micro-drill."""

    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=100)
    difficulty: int = Field(3, ge=1, le=5)
    hint: str | None = None
    context_entity_type: str | None = None
    context_entity_id: UUID | None = None


class MicroDrillResponseSchema(BaseModel):
    """Schema for micro-drill response."""

    id: UUID
    question: str
    answer: str
    hint: str | None
    category: str
    difficulty: int
    context_entity_type: str | None
    context_entity_id: UUID | None

    model_config = {"from_attributes": True}


class DrillCompletionSchema(BaseModel):
    """Schema for completing a drill."""

    correct: bool


class DrillCompletionResultSchema(BaseModel):
    """Schema for drill completion result."""

    streak: int
    total_completed: int
    accuracy: float


class DrillProgressSchema(BaseModel):
    """Schema for drill progress."""

    drills_completed_today: int
    streak: int
    total_completed: int
    accuracy: float


class LSWChecklistSummarySchema(BaseModel):
    """Schema for LSW checklist summary."""

    daily_status: LSWChecklistStatus
    daily_total: int
    daily_completed: int
    weekly_status: LSWChecklistStatus
    weekly_total: int
    weekly_completed: int
    monthly_status: LSWChecklistStatus
    monthly_total: int
    monthly_completed: int
    overdue_count: int
    next_due_item: str | None

    model_config = {"from_attributes": True}


class QuickMetricSchema(BaseModel):
    """Schema for quick metric."""

    id: str
    name: str
    value: float | int | str
    unit: str | None
    trend: str
    trend_value: float | None
    status: str
    target: float | None
    link: str | None

    model_config = {"from_attributes": True}


class RisksByCategorySchema(BaseModel):
    """Schema for risks grouped by category."""

    category: RiskCategory
    risks: list[RiskResponseSchema]
    count: int


class TodayScreenDataSchema(BaseModel):
    """Schema for complete today screen data."""

    user_id: UUID
    user_name: str
    current_date: date
    greeting: str

    top_priorities: list[PriorityResponseSchema]
    unselected_priorities: list[PriorityResponseSchema]

    top_risks: dict[str, list[RiskResponseSchema]]
    total_risk_count: int
    critical_risk_count: int

    todays_commitments: list[CommitmentResponseSchema]
    tomorrows_commitments: list[CommitmentResponseSchema]
    overdue_commitments: list[CommitmentResponseSchema]

    abnormalities: list[AbnormalityResponseSchema]
    abnormality_counts: dict[str, int]

    todays_micro_drills: list[MicroDrillResponseSchema]
    drills_completed_today: int
    drill_streak: int

    lsw_summary: LSWChecklistSummarySchema
    quick_metrics: list[QuickMetricSchema]

    generated_at: datetime
    cache_valid_until: datetime | None


# ============================================================================
# Helper Functions
# ============================================================================


def _priority_to_response(priority: Priority) -> PriorityResponseSchema:
    """Convert Priority to response schema."""
    return PriorityResponseSchema(
        id=priority.id,
        title=priority.title,
        description=priority.description,
        entity_type=priority.entity_type,
        entity_id=priority.entity_id,
        priority_level=priority.priority_level,
        due_date=priority.due_date,
        owner_id=priority.owner_id,
        owner_name=priority.owner_name,
        is_user_selected=priority.is_user_selected,
        rank=priority.rank,
        created_at=priority.created_at,
    )


def _risk_to_response(risk: Risk) -> RiskResponseSchema:
    """Convert Risk to response schema."""
    return RiskResponseSchema(
        id=risk.id,
        title=risk.title,
        description=risk.description,
        category=risk.category,
        severity=risk.severity,
        probability=risk.probability,
        risk_score=risk.risk_score,
        entity_type=risk.entity_type,
        entity_id=risk.entity_id,
        owner_id=risk.owner_id,
        owner_name=risk.owner_name,
        mitigation=risk.mitigation,
        due_date=risk.due_date,
        status=risk.status,
    )


def _commitment_to_response(commitment: Commitment) -> CommitmentResponseSchema:
    """Convert Commitment to response schema."""
    return CommitmentResponseSchema(
        id=commitment.id,
        title=commitment.title,
        description=commitment.description,
        commitment_type=commitment.commitment_type,
        entity_type=commitment.entity_type,
        entity_id=commitment.entity_id,
        due_date=commitment.due_date,
        due_time=commitment.due_time,
        owner_id=commitment.owner_id,
        owner_name=commitment.owner_name,
        customer_name=commitment.customer_name,
        is_completed=commitment.is_completed,
        is_overdue=commitment.is_overdue,
    )


def _abnormality_to_response(abnormality: Abnormality) -> AbnormalityResponseSchema:
    """Convert Abnormality to response schema."""
    return AbnormalityResponseSchema(
        id=abnormality.id,
        title=abnormality.title,
        description=abnormality.description,
        abnormality_type=abnormality.abnormality_type,
        entity_type=abnormality.entity_type,
        entity_id=abnormality.entity_id,
        detected_at=abnormality.detected_at,
        days_stale=abnormality.days_stale,
        severity=abnormality.severity,
        owner_id=abnormality.owner_id,
        owner_name=abnormality.owner_name,
        suggested_action=abnormality.suggested_action,
    )


def _drill_to_response(drill: MicroDrill) -> MicroDrillResponseSchema:
    """Convert MicroDrill to response schema."""
    return MicroDrillResponseSchema(
        id=drill.id,
        question=drill.question,
        answer=drill.answer,
        hint=drill.hint,
        category=drill.category,
        difficulty=drill.difficulty,
        context_entity_type=drill.context_entity_type,
        context_entity_id=drill.context_entity_id,
    )


# ============================================================================
# Priority Endpoints
# ============================================================================


@router.get(
    "/priorities/{user_id}",
    response_model=list[PriorityResponseSchema],
    summary="Get user priorities",
)
async def get_user_priorities(
    user_id: UUID,
    include_selected: bool = True,
    include_unselected: bool = True,
) -> list[PriorityResponseSchema]:
    """Get all priorities for a user."""
    service = get_today_screen_service()
    priorities = service.get_user_priorities(
        user_id=user_id,
        include_selected=include_selected,
        include_unselected=include_unselected,
    )
    return [_priority_to_response(p) for p in priorities]


@router.post(
    "/priorities/{user_id}",
    response_model=PriorityResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a priority",
)
async def add_priority(
    user_id: UUID,
    data: PriorityCreateSchema,
) -> PriorityResponseSchema:
    """Add a new priority for a user."""
    service = get_today_screen_service()
    priority = service.add_priority(
        user_id=user_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        title=data.title,
        priority_level=data.priority_level,
        description=data.description,
        due_date=data.due_date,
        owner_id=data.owner_id,
        owner_name=data.owner_name,
    )
    return _priority_to_response(priority)


@router.post(
    "/priorities/{user_id}/top",
    response_model=list[PriorityResponseSchema],
    summary="Set top 3 priorities",
)
async def set_top_priorities(
    user_id: UUID,
    data: SetTopPrioritiesSchema,
) -> list[PriorityResponseSchema]:
    """Set the user's top 3 priorities (max 3)."""
    service = get_today_screen_service()
    try:
        priorities = service.set_top_priorities(
            user_id=user_id,
            priority_ids=data.priority_ids,
        )
        return [_priority_to_response(p) for p in priorities]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.delete(
    "/priorities/{user_id}/{priority_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a priority",
)
async def remove_priority(user_id: UUID, priority_id: UUID) -> None:
    """Remove a priority."""
    service = get_today_screen_service()
    if not service.remove_priority(user_id, priority_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Priority not found"},
        )


# ============================================================================
# Risk Endpoints
# ============================================================================


@router.get(
    "/risks",
    response_model=list[RiskResponseSchema],
    summary="Get all risks",
)
async def get_risks(
    category: RiskCategory | None = None,
    top_n: int | None = None,
) -> list[RiskResponseSchema]:
    """Get risks, optionally filtered by category."""
    service = get_today_screen_service()
    
    if category is not None or top_n is not None:
        risks_by_cat = service.get_risks_by_category(category=category, top_n=top_n)
        result = []
        for cat_risks in risks_by_cat.values():
            result.extend(cat_risks)
        return [_risk_to_response(r) for r in result]
    else:
        return [_risk_to_response(r) for r in service.get_top_risks(top_n=100)]


@router.get(
    "/risks/by-category",
    response_model=list[RisksByCategorySchema],
    summary="Get risks grouped by category",
)
async def get_risks_by_category(
    top_n: int | None = None,
) -> list[RisksByCategorySchema]:
    """Get risks grouped by category."""
    service = get_today_screen_service()
    risks_by_cat = service.get_risks_by_category(top_n=top_n)
    
    return [
        RisksByCategorySchema(
            category=cat,
            risks=[_risk_to_response(r) for r in risks],
            count=len(risks),
        )
        for cat, risks in risks_by_cat.items()
    ]


@router.get(
    "/risks/top",
    response_model=list[RiskResponseSchema],
    summary="Get top risks",
)
async def get_top_risks(
    top_n: int = Query(5, ge=1, le=50),
) -> list[RiskResponseSchema]:
    """Get top N risks by risk score."""
    service = get_today_screen_service()
    risks = service.get_top_risks(top_n=top_n)
    return [_risk_to_response(r) for r in risks]


@router.post(
    "/risks",
    response_model=RiskResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a risk",
)
async def add_risk(data: RiskCreateSchema) -> RiskResponseSchema:
    """Add a new risk."""
    service = get_today_screen_service()
    risk = service.add_risk(
        title=data.title,
        category=data.category,
        severity=data.severity,
        probability=data.probability,
        description=data.description,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        owner_id=data.owner_id,
        owner_name=data.owner_name,
        mitigation=data.mitigation,
        due_date=data.due_date,
    )
    return _risk_to_response(risk)


# ============================================================================
# Commitment Endpoints
# ============================================================================


@router.get(
    "/commitments",
    response_model=list[CommitmentResponseSchema],
    summary="Get commitments",
)
async def get_commitments(
    user_id: UUID | None = None,
    target_date: date | None = None,
    include_overdue: bool = True,
    include_completed: bool = False,
) -> list[CommitmentResponseSchema]:
    """Get commitments with optional filtering."""
    service = get_today_screen_service()
    commitments = service.get_commitments(
        user_id=user_id,
        target_date=target_date,
        include_overdue=include_overdue,
        include_completed=include_completed,
    )
    return [_commitment_to_response(c) for c in commitments]


@router.post(
    "/commitments",
    response_model=CommitmentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a commitment",
)
async def add_commitment(data: CommitmentCreateSchema) -> CommitmentResponseSchema:
    """Add a new commitment."""
    service = get_today_screen_service()
    commitment = service.add_commitment(
        title=data.title,
        commitment_type=data.commitment_type,
        due_date=data.due_date,
        description=data.description,
        due_time=data.due_time,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        owner_id=data.owner_id,
        owner_name=data.owner_name,
        customer_name=data.customer_name,
    )
    return _commitment_to_response(commitment)


@router.post(
    "/commitments/{commitment_id}/complete",
    response_model=CommitmentResponseSchema,
    summary="Complete a commitment",
)
async def complete_commitment(commitment_id: UUID) -> CommitmentResponseSchema:
    """Mark a commitment as completed."""
    service = get_today_screen_service()
    commitment = service.complete_commitment(commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Commitment not found"},
        )
    return _commitment_to_response(commitment)


# ============================================================================
# Abnormality Endpoints
# ============================================================================


@router.get(
    "/abnormalities",
    response_model=list[AbnormalityResponseSchema],
    summary="Get abnormalities",
)
async def get_abnormalities(
    user_id: UUID | None = None,
    abnormality_type: AbnormalityType | None = None,
    severity: PriorityLevel | None = None,
) -> list[AbnormalityResponseSchema]:
    """Get abnormalities with optional filtering."""
    service = get_today_screen_service()
    abnormalities = service.get_abnormalities(
        user_id=user_id,
        abnormality_type=abnormality_type,
        severity=severity,
    )
    return [_abnormality_to_response(a) for a in abnormalities]


@router.get(
    "/abnormalities/counts",
    response_model=dict[str, int],
    summary="Get abnormality counts by type",
)
async def get_abnormality_counts() -> dict[str, int]:
    """Get counts of abnormalities by type."""
    service = get_today_screen_service()
    counts = service.get_abnormality_counts()
    return {atype.value: count for atype, count in counts.items()}


@router.post(
    "/abnormalities",
    response_model=AbnormalityResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add an abnormality",
)
async def add_abnormality(data: AbnormalityCreateSchema) -> AbnormalityResponseSchema:
    """Add a new abnormality."""
    service = get_today_screen_service()
    abnormality = service.add_abnormality(
        title=data.title,
        abnormality_type=data.abnormality_type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        days_stale=data.days_stale,
        description=data.description,
        severity=data.severity,
        owner_id=data.owner_id,
        owner_name=data.owner_name,
        suggested_action=data.suggested_action,
    )
    return _abnormality_to_response(abnormality)


@router.delete(
    "/abnormalities/{abnormality_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Resolve an abnormality",
)
async def resolve_abnormality(abnormality_id: UUID) -> None:
    """Resolve (remove) an abnormality."""
    service = get_today_screen_service()
    if not service.resolve_abnormality(abnormality_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Abnormality not found"},
        )


# ============================================================================
# Micro-Drill Endpoints
# ============================================================================


@router.get(
    "/drills/{user_id}",
    response_model=list[MicroDrillResponseSchema],
    summary="Get today's drills",
)
async def get_todays_drills(
    user_id: UUID,
    count: int = Query(3, ge=1, le=10),
) -> list[MicroDrillResponseSchema]:
    """Get micro-drill questions for today."""
    service = get_today_screen_service()
    drills = service.get_todays_drills(user_id, count=count)
    return [_drill_to_response(d) for d in drills]


@router.post(
    "/drills",
    response_model=MicroDrillResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a micro-drill",
)
async def add_micro_drill(data: MicroDrillCreateSchema) -> MicroDrillResponseSchema:
    """Add a new micro-drill question."""
    service = get_today_screen_service()
    drill = service.add_micro_drill(
        question=data.question,
        answer=data.answer,
        category=data.category,
        difficulty=data.difficulty,
        hint=data.hint,
        context_entity_type=data.context_entity_type,
        context_entity_id=data.context_entity_id,
    )
    return _drill_to_response(drill)


@router.post(
    "/drills/{user_id}/{drill_id}/complete",
    response_model=DrillCompletionResultSchema,
    summary="Complete a drill",
)
async def complete_drill(
    user_id: UUID,
    drill_id: UUID,
    data: DrillCompletionSchema,
) -> DrillCompletionResultSchema:
    """Record drill completion."""
    service = get_today_screen_service()
    result = service.complete_drill(user_id, drill_id, correct=data.correct)
    return DrillCompletionResultSchema(
        streak=result["streak"],
        total_completed=result["total_completed"],
        accuracy=result["accuracy"],
    )


@router.get(
    "/drills/{user_id}/progress",
    response_model=DrillProgressSchema,
    summary="Get drill progress",
)
async def get_drill_progress(user_id: UUID) -> DrillProgressSchema:
    """Get user's drill progress."""
    service = get_today_screen_service()
    progress = service.get_drill_progress(user_id)
    return DrillProgressSchema(
        drills_completed_today=progress["drills_completed_today"],
        streak=progress["streak"],
        total_completed=progress["total_completed"],
        accuracy=progress["accuracy"],
    )


# ============================================================================
# LSW Summary Endpoint
# ============================================================================


@router.get(
    "/lsw/{user_id}",
    response_model=LSWChecklistSummarySchema,
    summary="Get LSW checklist summary",
)
async def get_lsw_summary(user_id: UUID) -> LSWChecklistSummarySchema:
    """Get LSW checklist summary for a user."""
    service = get_today_screen_service()
    summary = service.get_lsw_summary(user_id)
    return LSWChecklistSummarySchema(
        daily_status=summary.daily_status,
        daily_total=summary.daily_total,
        daily_completed=summary.daily_completed,
        weekly_status=summary.weekly_status,
        weekly_total=summary.weekly_total,
        weekly_completed=summary.weekly_completed,
        monthly_status=summary.monthly_status,
        monthly_total=summary.monthly_total,
        monthly_completed=summary.monthly_completed,
        overdue_count=summary.overdue_count,
        next_due_item=summary.next_due_item,
    )


# ============================================================================
# Quick Metrics Endpoint
# ============================================================================


@router.get(
    "/metrics/{user_id}",
    response_model=list[QuickMetricSchema],
    summary="Get quick metrics",
)
async def get_quick_metrics(user_id: UUID) -> list[QuickMetricSchema]:
    """Get quick metrics for the Today screen."""
    service = get_today_screen_service()
    metrics = service.get_quick_metrics(user_id)
    return [
        QuickMetricSchema(
            id=m.id,
            name=m.name,
            value=m.value,
            unit=m.unit,
            trend=m.trend,
            trend_value=m.trend_value,
            status=m.status,
            target=m.target,
            link=m.link,
        )
        for m in metrics
    ]


# ============================================================================
# Full Today Screen Endpoint
# ============================================================================


@router.get(
    "/screen/{user_id}",
    response_model=TodayScreenDataSchema,
    summary="Get full today screen data",
)
async def get_today_screen(
    user_id: UUID,
    user_name: str | None = Query(None),
) -> TodayScreenDataSchema:
    """Get complete Today screen data for a user."""
    service = get_today_screen_service()
    normalized_user_name = (user_name or "").strip() or "User"
    screen = service.get_today_screen(user_id, normalized_user_name)

    return TodayScreenDataSchema(
        user_id=screen.user_id,
        user_name=screen.user_name,
        current_date=screen.current_date,
        greeting=screen.greeting,
        top_priorities=[_priority_to_response(p) for p in screen.top_priorities],
        unselected_priorities=[_priority_to_response(p) for p in screen.unselected_priorities],
        top_risks={
            cat.value: [_risk_to_response(r) for r in risks]
            for cat, risks in screen.top_risks.items()
        },
        total_risk_count=screen.total_risk_count,
        critical_risk_count=screen.critical_risk_count,
        todays_commitments=[_commitment_to_response(c) for c in screen.todays_commitments],
        tomorrows_commitments=[_commitment_to_response(c) for c in screen.tomorrows_commitments],
        overdue_commitments=[_commitment_to_response(c) for c in screen.overdue_commitments],
        abnormalities=[_abnormality_to_response(a) for a in screen.abnormalities],
        abnormality_counts={
            atype.value: count for atype, count in screen.abnormality_counts.items()
        },
        todays_micro_drills=[_drill_to_response(d) for d in screen.todays_micro_drills],
        drills_completed_today=screen.drills_completed_today,
        drill_streak=screen.drill_streak,
        lsw_summary=LSWChecklistSummarySchema(
            daily_status=screen.lsw_summary.daily_status,
            daily_total=screen.lsw_summary.daily_total,
            daily_completed=screen.lsw_summary.daily_completed,
            weekly_status=screen.lsw_summary.weekly_status,
            weekly_total=screen.lsw_summary.weekly_total,
            weekly_completed=screen.lsw_summary.weekly_completed,
            monthly_status=screen.lsw_summary.monthly_status,
            monthly_total=screen.lsw_summary.monthly_total,
            monthly_completed=screen.lsw_summary.monthly_completed,
            overdue_count=screen.lsw_summary.overdue_count,
            next_due_item=screen.lsw_summary.next_due_item,
        ),
        quick_metrics=[
            QuickMetricSchema(
                id=m.id,
                name=m.name,
                value=m.value,
                unit=m.unit,
                trend=m.trend,
                trend_value=m.trend_value,
                status=m.status,
                target=m.target,
                link=m.link,
            )
            for m in screen.quick_metrics
        ],
        generated_at=screen.generated_at,
        cache_valid_until=screen.cache_valid_until,
    )


# ============================================================================
# Metadata Endpoints
# ============================================================================


@router.get(
    "/meta/risk-categories",
    response_model=list[str],
    summary="Get risk categories",
)
async def get_risk_categories() -> list[str]:
    """Get all available risk categories."""
    return [cat.value for cat in RiskCategory]


@router.get(
    "/meta/abnormality-types",
    response_model=list[str],
    summary="Get abnormality types",
)
async def get_abnormality_types() -> list[str]:
    """Get all available abnormality types."""
    return [atype.value for atype in AbnormalityType]


@router.get(
    "/meta/commitment-types",
    response_model=list[str],
    summary="Get commitment types",
)
async def get_commitment_types() -> list[str]:
    """Get all available commitment types."""
    return [ctype.value for ctype in CommitmentType]


@router.get(
    "/meta/priority-levels",
    response_model=list[str],
    summary="Get priority levels",
)
async def get_priority_levels() -> list[str]:
    """Get all available priority levels."""
    return [level.value for level in PriorityLevel]


@router.get(
    "/meta/lsw-statuses",
    response_model=list[str],
    summary="Get LSW checklist statuses",
)
async def get_lsw_statuses() -> list[str]:
    """Get all available LSW checklist statuses."""
    return [status.value for status in LSWChecklistStatus]

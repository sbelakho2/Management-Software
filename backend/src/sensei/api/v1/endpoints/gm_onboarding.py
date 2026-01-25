"""
GM Onboarding API Endpoints

Provides endpoints for GM Day-1 onboarding,
including progress tracking, dashboard tour, and first actions.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sensei.core.config import settings
from sensei.services.ops.gm_onboarding import (
    GMOnboardingService,
    OnboardingProgress,
    OnboardingStatus,
    OnboardingStep,
    OnboardingStepType,
    get_gm_onboarding_service,
)


def _deny_production() -> None:
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


router = APIRouter(tags=["gm-onboarding"], dependencies=[Depends(_deny_production)])


# =============================================================================
# Schemas
# =============================================================================


class OnboardingStepResponse(BaseModel):
    """Response for an onboarding step."""
    
    id: str
    step_type: str
    title: str
    description: str
    order: int
    status: str
    required: bool
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_spent_seconds: int = 0
    is_complete: bool
    can_skip: bool
    
    @classmethod
    def from_step(cls, step: OnboardingStep) -> "OnboardingStepResponse":
        """Create response from step."""
        return cls(
            id=step.id,
            step_type=step.step_type.value,
            title=step.title,
            description=step.description,
            order=step.order,
            status=step.status.value,
            required=step.required,
            started_at=step.started_at,
            completed_at=step.completed_at,
            time_spent_seconds=step.time_spent_seconds,
            is_complete=step.is_complete,
            can_skip=step.can_skip,
        )


class OnboardingProgressResponse(BaseModel):
    """Response for onboarding progress."""
    
    user_id: str
    user_name: str
    role: str
    status: str
    steps: list[OnboardingStepResponse]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    completion_percentage: float
    estimated_remaining_minutes: int
    current_step_index: int
    
    @classmethod
    def from_progress(cls, progress: OnboardingProgress) -> "OnboardingProgressResponse":
        """Create response from progress."""
        return cls(
            user_id=progress.user_id,
            user_name=progress.user_name,
            role=progress.role,
            status=progress.status.value,
            steps=[OnboardingStepResponse.from_step(s) for s in progress.steps],
            started_at=progress.started_at,
            completed_at=progress.completed_at,
            last_activity=progress.last_activity,
            completion_percentage=progress.completion_percentage,
            estimated_remaining_minutes=progress.estimated_remaining_minutes,
            current_step_index=progress.current_step_index,
        )


class TourSpotResponse(BaseModel):
    """Response for a dashboard tour spot."""
    
    id: str
    element_selector: str
    title: str
    description: str
    order: int
    position: str
    highlight: bool
    action: Optional[str] = None
    action_label: Optional[str] = None


class KeyMetricResponse(BaseModel):
    """Response for a key metric."""
    
    id: str
    name: str
    description: str
    current_value: Any
    target_value: Optional[Any] = None
    unit: str
    trend: str
    importance: str


class FirstActionResponse(BaseModel):
    """Response for a first action."""
    
    id: str
    title: str
    description: str
    priority: int
    completed: bool
    url: str
    icon: str
    category: str
    estimated_minutes: int


class ChecklistItemResponse(BaseModel):
    """Response for a checklist item."""
    
    id: str
    title: str
    description: str
    completed: bool
    action_url: Optional[str] = None
    action_label: Optional[str] = None


class StartOnboardingRequest(BaseModel):
    """Request to start onboarding."""
    
    user_id: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1)
    role: str = Field(default="GM")


class CompleteStepRequest(BaseModel):
    """Request to complete a step."""
    
    data: Optional[dict[str, Any]] = None


class OnboardingSummaryResponse(BaseModel):
    """Summary of onboarding progress."""
    
    status: str
    has_started: bool
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    completion_percentage: float = 0.0
    current_step: Optional[str] = None
    steps_completed: int = 0
    steps_remaining: int = 0
    estimated_remaining_minutes: int = 0


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/start",
    response_model=OnboardingProgressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start onboarding",
    description="Start the Day-1 onboarding flow for a new GM",
)
async def start_onboarding(
    request: StartOnboardingRequest,
) -> OnboardingProgressResponse:
    """Start onboarding for a new user."""
    service = get_gm_onboarding_service()
    
    progress = service.start_onboarding(
        user_id=request.user_id,
        user_name=request.user_name,
        role=request.role,
    )
    
    return OnboardingProgressResponse.from_progress(progress)


@router.get(
    "/progress/{user_id}",
    response_model=OnboardingProgressResponse,
    summary="Get onboarding progress",
    description="Get the current onboarding progress for a user",
)
async def get_progress(user_id: str) -> OnboardingProgressResponse:
    """Get onboarding progress for a user."""
    service = get_gm_onboarding_service()
    
    progress = service.get_progress(user_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No onboarding found for user {user_id}",
        )
    
    return OnboardingProgressResponse.from_progress(progress)


@router.get(
    "/summary/{user_id}",
    response_model=OnboardingSummaryResponse,
    summary="Get onboarding summary",
    description="Get a summary of onboarding progress",
)
async def get_summary(user_id: str) -> OnboardingSummaryResponse:
    """Get onboarding summary for a user."""
    service = get_gm_onboarding_service()
    
    summary = service.get_onboarding_summary(user_id)
    return OnboardingSummaryResponse(**summary)


@router.post(
    "/steps/{user_id}/{step_id}/start",
    response_model=OnboardingStepResponse,
    summary="Start a step",
    description="Mark an onboarding step as started",
)
async def start_step(
    user_id: str,
    step_id: str,
) -> OnboardingStepResponse:
    """Start an onboarding step."""
    service = get_gm_onboarding_service()
    
    step = service.start_step(user_id, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {step_id} not found for user {user_id}",
        )
    
    return OnboardingStepResponse.from_step(step)


@router.post(
    "/steps/{user_id}/{step_id}/complete",
    response_model=OnboardingStepResponse,
    summary="Complete a step",
    description="Mark an onboarding step as completed",
)
async def complete_step(
    user_id: str,
    step_id: str,
    request: CompleteStepRequest,
) -> OnboardingStepResponse:
    """Complete an onboarding step."""
    service = get_gm_onboarding_service()
    
    step = service.complete_step(user_id, step_id, data=request.data)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {step_id} not found for user {user_id}",
        )
    
    return OnboardingStepResponse.from_step(step)


@router.post(
    "/steps/{user_id}/{step_id}/skip",
    response_model=OnboardingStepResponse,
    summary="Skip a step",
    description="Skip an optional onboarding step",
)
async def skip_step(
    user_id: str,
    step_id: str,
) -> OnboardingStepResponse:
    """Skip an optional onboarding step."""
    service = get_gm_onboarding_service()
    
    step = service.skip_step(user_id, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot skip step {step_id} (required or not found)",
        )
    
    return OnboardingStepResponse.from_step(step)


@router.get(
    "/tour",
    response_model=list[TourSpotResponse],
    summary="Get dashboard tour",
    description="Get the dashboard tour spots",
)
async def get_dashboard_tour() -> list[TourSpotResponse]:
    """Get dashboard tour spots."""
    service = get_gm_onboarding_service()
    
    spots = service.get_dashboard_tour()
    return [
        TourSpotResponse(
            id=s.id,
            element_selector=s.element_selector,
            title=s.title,
            description=s.description,
            order=s.order,
            position=s.position,
            highlight=s.highlight,
            action=s.action,
            action_label=s.action_label,
        )
        for s in spots
    ]


@router.get(
    "/metrics/{user_id}",
    response_model=list[KeyMetricResponse],
    summary="Get key metrics",
    description="Get key metrics for GM onboarding",
)
async def get_key_metrics(user_id: str) -> list[KeyMetricResponse]:
    """Get key metrics for onboarding."""
    service = get_gm_onboarding_service()
    
    metrics = service.get_key_metrics(user_id)
    return [
        KeyMetricResponse(
            id=m.id,
            name=m.name,
            description=m.description,
            current_value=m.current_value,
            target_value=m.target_value,
            unit=m.unit,
            trend=m.trend,
            importance=m.importance,
        )
        for m in metrics
    ]


@router.get(
    "/first-actions/{user_id}",
    response_model=list[FirstActionResponse],
    summary="Get first actions",
    description="Get recommended first actions for new GM",
)
async def get_first_actions(user_id: str) -> list[FirstActionResponse]:
    """Get recommended first actions."""
    service = get_gm_onboarding_service()
    
    actions = service.get_first_actions(user_id)
    return [
        FirstActionResponse(
            id=a.id,
            title=a.title,
            description=a.description,
            priority=a.priority,
            completed=a.completed,
            url=a.url,
            icon=a.icon,
            category=a.category,
            estimated_minutes=a.estimated_minutes,
        )
        for a in actions
    ]


@router.post(
    "/first-actions/{user_id}/{action_id}/complete",
    response_model=FirstActionResponse,
    summary="Complete first action",
    description="Mark a first action as completed",
)
async def complete_first_action(
    user_id: str,
    action_id: str,
) -> FirstActionResponse:
    """Mark a first action as completed."""
    service = get_gm_onboarding_service()
    
    action = service.complete_first_action(user_id, action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found",
        )
    
    return FirstActionResponse(
        id=action.id,
        title=action.title,
        description=action.description,
        priority=action.priority,
        completed=action.completed,
        url=action.url,
        icon=action.icon,
        category=action.category,
        estimated_minutes=action.estimated_minutes,
    )


@router.get(
    "/workflow-checklist",
    response_model=list[ChecklistItemResponse],
    summary="Get workflow checklist",
    description="Get the daily workflow checklist for GM",
)
async def get_workflow_checklist() -> list[ChecklistItemResponse]:
    """Get daily workflow checklist."""
    service = get_gm_onboarding_service()
    
    items = service.get_workflow_checklist()
    return [
        ChecklistItemResponse(
            id=item.id,
            title=item.title,
            description=item.description,
            completed=item.completed,
            action_url=item.action_url,
            action_label=item.action_label,
        )
        for item in items
    ]


@router.delete(
    "/reset/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset onboarding",
    description="Reset onboarding for a user (for testing/re-onboarding)",
)
async def reset_onboarding(user_id: str) -> None:
    """Reset onboarding for a user."""
    service = get_gm_onboarding_service()
    
    result = service.reset_onboarding(user_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No onboarding found for user {user_id}",
        )

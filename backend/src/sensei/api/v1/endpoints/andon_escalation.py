"""
Andon A3 Escalation API Endpoints.

Provides REST endpoints for auto-escalating recurring Andon events to A3 documents.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.services.andon_a3_escalation import (
    AndonA3EscalationService,
    RecurrencePattern,
    RecurrenceThresholds,
    A3Template,
    RecurrencePatternType,
    A3EscalationReason,
)


router = APIRouter(prefix="/andon-escalation", tags=["Andon A3 Escalation"])


# =============================================================================
# Request Schemas
# =============================================================================


class AndonEventInput(BaseModel):
    """Input schema for Andon event data."""
    
    id: int = Field(..., description="Event ID")
    station_id: int | None = Field(None, description="Station ID")
    andon_type: str | None = Field(None, description="Andon type (quality, equipment, etc.)")
    symptom: str | None = Field(None, description="Symptom description")
    status: str | None = Field(None, description="Event status")
    reported_at: datetime | None = Field(None, description="When the event was reported")
    downtime_minutes: int | None = Field(None, description="Downtime in minutes")
    estimated_cost_impact: float | None = Field(None, description="Estimated cost impact")
    product_id: int | None = Field(None, description="Associated product ID")
    escalated_to_a3_id: str | None = Field(None, description="ID of linked A3 document")


class StationInput(BaseModel):
    """Input schema for station data."""
    
    id: int = Field(..., description="Station ID")
    name: str = Field(..., description="Station name")


class ProductInput(BaseModel):
    """Input schema for product data."""
    
    id: int = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")


class A3Input(BaseModel):
    """Input schema for existing A3 data."""
    
    id: str = Field(..., description="A3 ID")
    title: str | None = Field(None, description="A3 title")


class CheckEscalationsRequest(BaseModel):
    """Request to check for escalations."""
    
    andon_events: list[AndonEventInput] = Field(..., description="List of Andon events to analyze")
    stations: list[StationInput] | None = Field(None, description="Station lookup data")
    products: list[ProductInput] | None = Field(None, description="Product lookup data")
    existing_a3s: list[A3Input] | None = Field(None, description="Existing A3 documents")
    reference_date: datetime | None = Field(None, description="Reference date for analysis")


class DetectPatternsRequest(BaseModel):
    """Request to detect recurrence patterns."""
    
    andon_events: list[AndonEventInput] = Field(..., description="List of Andon events")
    pattern_type: str = Field(
        default="station_type_symptom",
        description="Pattern type to detect",
    )
    reference_date: datetime | None = Field(None, description="Reference date")
    include_resolved: bool = Field(True, description="Include resolved events")


class LinkEventsRequest(BaseModel):
    """Request to link events to an A3."""
    
    event_ids: list[int] = Field(..., description="Event IDs to link")
    a3_id: str = Field(..., description="A3 document ID")
    andon_events: list[AndonEventInput] = Field(..., description="Full list of Andon events")


class ThresholdsUpdateRequest(BaseModel):
    """Request to update thresholds."""
    
    occurrence_count: int | None = Field(None, ge=1, description="Occurrence count threshold")
    time_window_days: int | None = Field(None, ge=1, description="Time window in days")
    downtime_threshold_minutes: int | None = Field(None, ge=1, description="Downtime threshold")
    cost_threshold: float | None = Field(None, ge=0, description="Cost threshold")


class PatternSummaryRequest(BaseModel):
    """Request to get pattern summary."""
    
    andon_events: list[AndonEventInput] = Field(..., description="List of Andon events")
    reference_date: datetime | None = Field(None, description="Reference date")


class GenerateA3Request(BaseModel):
    """Request to generate A3 template for a pattern."""
    
    pattern: "RecurrencePatternInput" = Field(..., description="Pattern to generate A3 for")
    author_id: str | None = Field(None, description="Optional author ID")


class RecurrencePatternInput(BaseModel):
    """Input schema for a recurrence pattern."""
    
    pattern_type: str = Field(..., description="Pattern type")
    station_id: int | None = Field(None, description="Station ID")
    station_name: str | None = Field(None, description="Station name")
    andon_type: str | None = Field(None, description="Andon type")
    symptom: str | None = Field(None, description="Symptom")
    product_id: int | None = Field(None, description="Product ID")
    product_name: str | None = Field(None, description="Product name")
    event_ids: list[int] = Field(default_factory=list, description="Related event IDs")
    event_count: int = Field(default=0, description="Number of events")
    first_occurrence: datetime | None = Field(None, description="First occurrence")
    last_occurrence: datetime | None = Field(None, description="Last occurrence")
    total_downtime_minutes: int = Field(default=0, description="Total downtime")
    total_cost_impact: float = Field(default=0.0, description="Total cost impact")
    should_escalate: bool = Field(default=False, description="Should escalate")
    escalation_reason: str | None = Field(None, description="Escalation reason")
    existing_a3_id: str | None = Field(None, description="Existing A3 ID if linked")


# Update forward reference
GenerateA3Request.model_rebuild()


# =============================================================================
# Response Schemas
# =============================================================================


class RecurrencePatternResponse(BaseModel):
    """Response schema for a recurrence pattern."""
    
    pattern_type: str
    station_id: int | None = None
    station_name: str | None = None
    andon_type: str | None = None
    symptom: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    event_ids: list[int] = []
    event_count: int = 0
    first_occurrence: datetime | None = None
    last_occurrence: datetime | None = None
    total_downtime_minutes: int = 0
    total_cost_impact: float = 0.0
    should_escalate: bool = False
    escalation_reason: str | None = None
    existing_a3_id: str | None = None


class A3TemplateResponse(BaseModel):
    """Response schema for A3 template."""
    
    title: str
    problem_statement: str
    background: str
    current_condition: str
    goal: str
    author_id: str | None = None
    department: str | None = None
    area: str | None = None
    priority: str = "high"
    related_andon_ids: list[int] = []
    tags: list[str] = []


class EscalationResultResponse(BaseModel):
    """Response schema for escalation check result."""
    
    patterns_detected: list[RecurrencePatternResponse]
    patterns_to_escalate: list[RecurrencePatternResponse]
    a3s_to_create: list[A3TemplateResponse]
    total_patterns: int
    escalation_count: int
    analysis_window_start: datetime | None = None
    analysis_window_end: datetime | None = None


class ThresholdsResponse(BaseModel):
    """Response schema for thresholds."""
    
    occurrence_count: int
    time_window_days: int
    downtime_threshold_minutes: int
    cost_threshold: float


class LinkedEventResponse(BaseModel):
    """Response for a linked event."""
    
    id: int
    escalated_to_a3_id: str
    status: str
    is_recurrence: bool
    recurrence_count: int


class LinkEventsResponse(BaseModel):
    """Response for link events operation."""
    
    linked_events: list[LinkedEventResponse]
    count: int


class PatternSummaryResponse(BaseModel):
    """Response schema for pattern summary."""
    
    total_patterns: int
    requiring_escalation: int
    already_escalated: int
    pending_escalation: int
    by_reason: dict[str, int]
    top_recurring: list[dict]
    thresholds: ThresholdsResponse


class PatternTypesResponse(BaseModel):
    """Response for available pattern types."""
    
    pattern_types: list[dict[str, str]]


class EscalationReasonsResponse(BaseModel):
    """Response for escalation reasons."""
    
    reasons: list[dict[str, str]]


# =============================================================================
# Service Dependency
# =============================================================================


def get_service() -> AndonA3EscalationService:
    """Get Andon A3 Escalation service instance."""
    return AndonA3EscalationService()


# =============================================================================
# Helper Functions
# =============================================================================


def _pattern_to_response(pattern: RecurrencePattern) -> RecurrencePatternResponse:
    """Convert service pattern to response schema."""
    return RecurrencePatternResponse(
        pattern_type=pattern.pattern_type.value,
        station_id=pattern.station_id,
        station_name=pattern.station_name,
        andon_type=pattern.andon_type,
        symptom=pattern.symptom,
        product_id=pattern.product_id,
        product_name=pattern.product_name,
        event_ids=pattern.event_ids,
        event_count=pattern.event_count,
        first_occurrence=pattern.first_occurrence,
        last_occurrence=pattern.last_occurrence,
        total_downtime_minutes=pattern.total_downtime_minutes,
        total_cost_impact=pattern.total_cost_impact,
        should_escalate=pattern.should_escalate,
        escalation_reason=pattern.escalation_reason.value if pattern.escalation_reason else None,
        existing_a3_id=str(pattern.existing_a3_id) if pattern.existing_a3_id else None,
    )


def _template_to_response(template: A3Template) -> A3TemplateResponse:
    """Convert service template to response schema."""
    return A3TemplateResponse(
        title=template.title,
        problem_statement=template.problem_statement,
        background=template.background,
        current_condition=template.current_condition,
        goal=template.goal,
        author_id=str(template.author_id) if template.author_id else None,
        department=template.department,
        area=template.area,
        priority=template.priority,
        related_andon_ids=template.related_andon_ids,
        tags=template.tags,
    )


def _pattern_type_from_string(value: str) -> RecurrencePatternType:
    """Convert string to pattern type enum."""
    mapping = {
        "station_type_symptom": RecurrencePatternType.STATION_TYPE_SYMPTOM,
        "station_type": RecurrencePatternType.STATION_TYPE,
        "symptom": RecurrencePatternType.SYMPTOM_ONLY,
        "product_type": RecurrencePatternType.PRODUCT_TYPE,
    }
    if value not in mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pattern type: {value}. Valid types: {list(mapping.keys())}",
        )
    return mapping[value]


def _input_to_pattern(input_data: RecurrencePatternInput) -> RecurrencePattern:
    """Convert input to service pattern."""
    return RecurrencePattern(
        pattern_type=_pattern_type_from_string(input_data.pattern_type),
        station_id=input_data.station_id,
        station_name=input_data.station_name,
        andon_type=input_data.andon_type,
        symptom=input_data.symptom,
        product_id=input_data.product_id,
        product_name=input_data.product_name,
        event_ids=input_data.event_ids,
        event_count=input_data.event_count,
        first_occurrence=input_data.first_occurrence,
        last_occurrence=input_data.last_occurrence,
        total_downtime_minutes=input_data.total_downtime_minutes,
        total_cost_impact=input_data.total_cost_impact,
        should_escalate=input_data.should_escalate,
        escalation_reason=A3EscalationReason(input_data.escalation_reason) if input_data.escalation_reason else None,
        existing_a3_id=UUID(input_data.existing_a3_id) if input_data.existing_a3_id else None,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/check",
    response_model=EscalationResultResponse,
    summary="Check for Escalations",
    description="Analyze Andon events and check for patterns requiring A3 escalation.",
)
def check_for_escalations(
    request: CheckEscalationsRequest,
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> EscalationResultResponse:
    """Check Andon events for patterns requiring A3 escalation."""
    # Convert inputs to dicts
    events = [e.model_dump() for e in request.andon_events]
    stations = [s.model_dump() for s in (request.stations or [])]
    products = [p.model_dump() for p in (request.products or [])]
    existing_a3s = [a.model_dump() for a in (request.existing_a3s or [])]
    
    result = service.check_for_escalations(
        andon_events=events,
        stations=stations,
        products=products,
        existing_a3s=existing_a3s,
        reference_date=request.reference_date,
    )
    
    return EscalationResultResponse(
        patterns_detected=[_pattern_to_response(p) for p in result.patterns_detected],
        patterns_to_escalate=[_pattern_to_response(p) for p in result.patterns_to_escalate],
        a3s_to_create=[_template_to_response(t) for t in result.a3s_to_create],
        total_patterns=result.total_patterns,
        escalation_count=result.escalation_count,
        analysis_window_start=result.analysis_window_start,
        analysis_window_end=result.analysis_window_end,
    )


@router.post(
    "/patterns",
    response_model=list[RecurrencePatternResponse],
    summary="Detect Recurrence Patterns",
    description="Detect recurrence patterns in Andon events.",
)
def detect_patterns(
    request: DetectPatternsRequest,
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> list[RecurrencePatternResponse]:
    """Detect recurrence patterns in Andon events."""
    events = [e.model_dump() for e in request.andon_events]
    pattern_type = _pattern_type_from_string(request.pattern_type)
    
    patterns = service.detect_recurrence_patterns(
        andon_events=events,
        pattern_type=pattern_type,
        reference_date=request.reference_date,
        include_resolved=request.include_resolved,
    )
    
    return [_pattern_to_response(p) for p in patterns]


@router.post(
    "/summary",
    response_model=PatternSummaryResponse,
    summary="Get Pattern Summary",
    description="Get a summary of recurrence patterns for dashboard display.",
)
def get_pattern_summary(
    request: PatternSummaryRequest,
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> PatternSummaryResponse:
    """Get summary of recurrence patterns."""
    events = [e.model_dump() for e in request.andon_events]
    
    summary = service.get_pattern_summary(
        andon_events=events,
        reference_date=request.reference_date,
    )
    
    return PatternSummaryResponse(
        total_patterns=summary["total_patterns"],
        requiring_escalation=summary["requiring_escalation"],
        already_escalated=summary["already_escalated"],
        pending_escalation=summary["pending_escalation"],
        by_reason=summary["by_reason"],
        top_recurring=summary["top_recurring"],
        thresholds=ThresholdsResponse(**summary["thresholds"]),
    )


@router.post(
    "/generate-a3",
    response_model=A3TemplateResponse,
    summary="Generate A3 Template",
    description="Generate an A3 template from a recurrence pattern.",
)
def generate_a3_template(
    request: GenerateA3Request,
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> A3TemplateResponse:
    """Generate A3 template for a pattern."""
    pattern = _input_to_pattern(request.pattern)
    author_id = UUID(request.author_id) if request.author_id else None
    
    template = service.generate_a3_for_pattern(pattern, author_id=author_id)
    
    return _template_to_response(template)


@router.post(
    "/link-events",
    response_model=LinkEventsResponse,
    summary="Link Events to A3",
    description="Link Andon events to an A3 document.",
)
def link_events_to_a3(
    request: LinkEventsRequest,
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> LinkEventsResponse:
    """Link Andon events to an A3."""
    events = [e.model_dump() for e in request.andon_events]
    
    try:
        a3_id = UUID(request.a3_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid A3 ID format: {request.a3_id}. Must be a valid UUID.",
        )
    
    updated = service.link_events_to_a3(
        event_ids=request.event_ids,
        a3_id=a3_id,
        andon_events=events,
    )
    
    linked = [
        LinkedEventResponse(
            id=e["id"],
            escalated_to_a3_id=e["escalated_to_a3_id"],
            status=e["status"],
            is_recurrence=e["is_recurrence"],
            recurrence_count=e["recurrence_count"],
        )
        for e in updated
    ]
    
    return LinkEventsResponse(
        linked_events=linked,
        count=len(linked),
    )


@router.get(
    "/thresholds",
    response_model=ThresholdsResponse,
    summary="Get Thresholds",
    description="Get current escalation thresholds.",
)
def get_thresholds(
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> ThresholdsResponse:
    """Get current threshold configuration."""
    thresholds = service.get_thresholds()
    return ThresholdsResponse(
        occurrence_count=thresholds.occurrence_count,
        time_window_days=thresholds.time_window_days,
        downtime_threshold_minutes=thresholds.downtime_threshold_minutes,
        cost_threshold=thresholds.cost_threshold,
    )


@router.put(
    "/thresholds",
    response_model=ThresholdsResponse,
    summary="Update Thresholds",
    description="Update escalation thresholds.",
)
def update_thresholds(
    request: ThresholdsUpdateRequest,
    service: Annotated[AndonA3EscalationService, Depends(get_service)],
) -> ThresholdsResponse:
    """Update threshold configuration."""
    result = service.set_thresholds(
        occurrence_count=request.occurrence_count,
        time_window_days=request.time_window_days,
        downtime_threshold_minutes=request.downtime_threshold_minutes,
        cost_threshold=request.cost_threshold,
    )
    return ThresholdsResponse(
        occurrence_count=result.occurrence_count,
        time_window_days=result.time_window_days,
        downtime_threshold_minutes=result.downtime_threshold_minutes,
        cost_threshold=result.cost_threshold,
    )


@router.get(
    "/pattern-types",
    response_model=PatternTypesResponse,
    summary="Get Pattern Types",
    description="Get available pattern types for recurrence detection.",
)
def get_pattern_types() -> PatternTypesResponse:
    """Get available pattern types."""
    return PatternTypesResponse(
        pattern_types=[
            {
                "value": RecurrencePatternType.STATION_TYPE_SYMPTOM.value,
                "name": "Station + Type + Symptom",
                "description": "Match by station, andon type, and symptom (most specific)",
            },
            {
                "value": RecurrencePatternType.STATION_TYPE.value,
                "name": "Station + Type",
                "description": "Match by station and andon type only",
            },
            {
                "value": RecurrencePatternType.SYMPTOM_ONLY.value,
                "name": "Symptom Only",
                "description": "Match by symptom across all stations",
            },
            {
                "value": RecurrencePatternType.PRODUCT_TYPE.value,
                "name": "Product + Type",
                "description": "Match by product and andon type",
            },
        ]
    )


@router.get(
    "/escalation-reasons",
    response_model=EscalationReasonsResponse,
    summary="Get Escalation Reasons",
    description="Get available escalation reason types.",
)
def get_escalation_reasons() -> EscalationReasonsResponse:
    """Get available escalation reasons."""
    return EscalationReasonsResponse(
        reasons=[
            {
                "value": A3EscalationReason.RECURRENCE_THRESHOLD.value,
                "name": "Recurrence Threshold",
                "description": "Occurrence count exceeded threshold",
            },
            {
                "value": A3EscalationReason.SEVERITY_CRITICAL.value,
                "name": "Critical Severity",
                "description": "Event has critical severity level",
            },
            {
                "value": A3EscalationReason.MANUAL_ESCALATION.value,
                "name": "Manual Escalation",
                "description": "User manually escalated to A3",
            },
            {
                "value": A3EscalationReason.DOWNTIME_THRESHOLD.value,
                "name": "Downtime Threshold",
                "description": "Cumulative downtime exceeded threshold",
            },
            {
                "value": A3EscalationReason.COST_THRESHOLD.value,
                "name": "Cost Threshold",
                "description": "Cumulative cost impact exceeded threshold",
            },
        ]
    )

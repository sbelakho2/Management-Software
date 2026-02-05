"""
Stale Detection API endpoints.

Provides endpoints for detecting stale entities across the system.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from sensei.api import deps
from sensei.services.stale_detection import (
    EntityType,
    StaleSeverity,
    StaleReason,
    StaleDetectionService,
    StaleDetectionJobRunner,
)

router = APIRouter(dependencies=[Depends(deps.get_current_active_user)])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class StaleThresholdResponse(BaseModel):
    """Response model for stale threshold configuration."""
    
    days_until_stale: int = Field(..., description="Days of inactivity before marking as stale")
    severity_escalation_days: int = Field(..., description="Days between severity escalations")
    reason: str = Field(..., description="Default stale reason for this threshold")


class StaleEntityResponse(BaseModel):
    """Response model for a detected stale entity."""
    
    entity_id: UUID = Field(..., description="UUID of the stale entity")
    entity_type: str = Field(..., description="Type of entity (opportunity, rfq, task)")
    entity_name: str = Field(..., description="Human-readable name/identifier")
    reason: str = Field(..., description="Why it's considered stale")
    severity: str = Field(..., description="Severity level (low, medium, high, critical)")
    days_stale: int = Field(..., description="Number of days entity has been stale")
    last_activity_at: datetime = Field(..., description="When the entity was last updated")
    status: str = Field(..., description="Current status of the entity")
    owner_id: UUID | None = Field(None, description="UUID of the entity owner")
    owner_name: str | None = Field(None, description="Name of the owner")
    account_name: str | None = Field(None, description="Associated account name")
    suggested_action: str | None = Field(None, description="Recommended action to take")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class StaleDetectionResultResponse(BaseModel):
    """Response model for stale detection scan results."""
    
    scanned_at: datetime = Field(..., description="When the scan was performed")
    entity_type: str = Field(..., description="Type of entities scanned")
    total_scanned: int = Field(..., description="Total number of entities examined")
    stale_count: int = Field(..., description="Number of stale entities found")
    critical_count: int = Field(..., description="Number of critical severity stale entities")
    high_count: int = Field(..., description="Number of high severity stale entities")
    stale_entities: list[StaleEntityResponse] = Field(..., description="List of stale entities")
    thresholds_used: dict[str, dict[str, Any]] = Field(..., description="Thresholds used for detection")
    scan_duration_ms: float = Field(..., description="Scan duration in milliseconds")


class StaleDetectionRequest(BaseModel):
    """Request model for running stale detection on provided data."""
    
    entities: list[dict[str, Any]] = Field(
        ...,
        description="List of entity data dicts with id, status, updated_at, etc."
    )
    reference_time: datetime | None = Field(
        None,
        description="Point in time to compare against (default: now)"
    )


class FullScanSummaryResponse(BaseModel):
    """Response model for full scan summary."""
    
    scanned_at: str | None = Field(None, description="When the scan was performed")
    total_scanned: int = Field(..., description="Total entities scanned across all types")
    total_stale: int = Field(..., description="Total stale entities found")
    total_critical: int = Field(..., description="Total critical severity entities")
    total_high: int = Field(..., description="Total high severity entities")
    requires_immediate_attention: int = Field(..., description="Count requiring immediate action")
    by_entity_type: dict[str, dict[str, Any]] = Field(..., description="Breakdown by entity type")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/thresholds", response_model=dict[str, dict[str, StaleThresholdResponse]])
async def get_all_thresholds():
    """
    Get all stale detection thresholds for all entity types.
    
    Returns configured thresholds for opportunities, RFQs, and tasks.
    """
    service = StaleDetectionService()
    
    def format_thresholds(thresholds):
        return {
            status: StaleThresholdResponse(
                days_until_stale=t.days_until_stale,
                severity_escalation_days=t.severity_escalation_days,
                reason=t.reason.value,
            )
            for status, t in thresholds.items()
        }
    
    return {
        "opportunity": format_thresholds(service.get_thresholds(EntityType.OPPORTUNITY)),
        "rfq": format_thresholds(service.get_thresholds(EntityType.RFQ)),
        "task": format_thresholds(service.get_thresholds(EntityType.TASK)),
    }


@router.get("/thresholds/{entity_type}", response_model=dict[str, StaleThresholdResponse])
async def get_thresholds_for_entity_type(entity_type: str):
    """
    Get stale detection thresholds for a specific entity type.
    
    Args:
        entity_type: One of 'opportunity', 'rfq', or 'task'
    
    Returns:
        Dict mapping status to threshold configuration
    """
    try:
        et = EntityType(entity_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type: {entity_type}. Must be one of: opportunity, rfq, task"
        )
    
    service = StaleDetectionService()
    thresholds = service.get_thresholds(et)
    
    return {
        status: StaleThresholdResponse(
            days_until_stale=t.days_until_stale,
            severity_escalation_days=t.severity_escalation_days,
            reason=t.reason.value,
        )
        for status, t in thresholds.items()
    }


@router.post("/detect/opportunities", response_model=StaleDetectionResultResponse)
async def detect_stale_opportunities(request: StaleDetectionRequest):
    """
    Detect stale opportunities from provided data.
    
    This endpoint allows detection on any provided opportunity data.
    Each entity should have at minimum: id, stage/status, updated_at.
    
    Optional fields: owner_id, owner_name, account_name, next_step, next_step_date
    """
    service = StaleDetectionService()
    result = service.detect_stale_opportunities(
        request.entities,
        request.reference_time,
    )
    
    return StaleDetectionResultResponse(
        scanned_at=result.scanned_at,
        entity_type=result.entity_type.value,
        total_scanned=result.total_scanned,
        stale_count=result.stale_count,
        critical_count=result.critical_count,
        high_count=result.high_count,
        stale_entities=[
            StaleEntityResponse(
                entity_id=e.entity_id,
                entity_type=e.entity_type.value,
                entity_name=e.entity_name,
                reason=e.reason.value,
                severity=e.severity.value,
                days_stale=e.days_stale,
                last_activity_at=e.last_activity_at,
                status=e.status,
                owner_id=e.owner_id,
                owner_name=e.owner_name,
                account_name=e.account_name,
                suggested_action=e.suggested_action,
                metadata=e.metadata,
            )
            for e in result.stale_entities
        ],
        thresholds_used=result.thresholds_used,
        scan_duration_ms=result.scan_duration_ms,
    )


@router.post("/detect/rfqs", response_model=StaleDetectionResultResponse)
async def detect_stale_rfqs(request: StaleDetectionRequest):
    """
    Detect stale RFQs from provided data.
    
    This endpoint allows detection on any provided RFQ data.
    Each entity should have at minimum: id, status, updated_at.
    
    Optional fields: rfq_number, owner_id, owner_name, account_name, due_date
    """
    service = StaleDetectionService()
    result = service.detect_stale_rfqs(
        request.entities,
        request.reference_time,
    )
    
    return StaleDetectionResultResponse(
        scanned_at=result.scanned_at,
        entity_type=result.entity_type.value,
        total_scanned=result.total_scanned,
        stale_count=result.stale_count,
        critical_count=result.critical_count,
        high_count=result.high_count,
        stale_entities=[
            StaleEntityResponse(
                entity_id=e.entity_id,
                entity_type=e.entity_type.value,
                entity_name=e.entity_name,
                reason=e.reason.value,
                severity=e.severity.value,
                days_stale=e.days_stale,
                last_activity_at=e.last_activity_at,
                status=e.status,
                owner_id=e.owner_id,
                owner_name=e.owner_name,
                account_name=e.account_name,
                suggested_action=e.suggested_action,
                metadata=e.metadata,
            )
            for e in result.stale_entities
        ],
        thresholds_used=result.thresholds_used,
        scan_duration_ms=result.scan_duration_ms,
    )


@router.post("/detect/tasks", response_model=StaleDetectionResultResponse)
async def detect_stale_tasks(request: StaleDetectionRequest):
    """
    Detect stale tasks from provided data.
    
    This endpoint allows detection on any provided task data.
    Each entity should have at minimum: id, status, updated_at.
    
    Optional fields: title, assignee_id, assignee_name, due_date
    """
    service = StaleDetectionService()
    result = service.detect_stale_tasks(
        request.entities,
        request.reference_time,
    )
    
    return StaleDetectionResultResponse(
        scanned_at=result.scanned_at,
        entity_type=result.entity_type.value,
        total_scanned=result.total_scanned,
        stale_count=result.stale_count,
        critical_count=result.critical_count,
        high_count=result.high_count,
        stale_entities=[
            StaleEntityResponse(
                entity_id=e.entity_id,
                entity_type=e.entity_type.value,
                entity_name=e.entity_name,
                reason=e.reason.value,
                severity=e.severity.value,
                days_stale=e.days_stale,
                last_activity_at=e.last_activity_at,
                status=e.status,
                owner_id=e.owner_id,
                owner_name=e.owner_name,
                account_name=e.account_name,
                suggested_action=e.suggested_action,
                metadata=e.metadata,
            )
            for e in result.stale_entities
        ],
        thresholds_used=result.thresholds_used,
        scan_duration_ms=result.scan_duration_ms,
    )


class FullScanRequest(BaseModel):
    """Request model for running a full scan across all entity types."""
    
    opportunities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of opportunity data"
    )
    rfqs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of RFQ data"
    )
    tasks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of task data"
    )
    reference_time: datetime | None = Field(
        None,
        description="Point in time to compare against (default: now)"
    )


@router.post("/detect/full-scan", response_model=FullScanSummaryResponse)
async def run_full_scan(request: FullScanRequest):
    """
    Run stale detection across all entity types and get a summary.
    
    This is the primary endpoint for scheduled stale detection jobs.
    Provides aggregated results across opportunities, RFQs, and tasks.
    """
    runner = StaleDetectionJobRunner()
    
    results = await runner.run_full_scan(
        opportunities=request.opportunities,
        rfqs=request.rfqs,
        tasks=request.tasks,
        reference_time=request.reference_time,
        create_follow_up_tasks=False,  # Don't create tasks via API
        send_notifications=False,  # Don't send notifications via API
    )
    
    summary = runner.get_summary(results)
    
    return FullScanSummaryResponse(**summary)


@router.get("/severity-levels", response_model=list[dict[str, str]])
async def get_severity_levels():
    """
    Get all available severity levels with descriptions.
    """
    return [
        {"value": StaleSeverity.LOW.value, "label": "Low", "description": "Just became stale - warning level"},
        {"value": StaleSeverity.MEDIUM.value, "label": "Medium", "description": "Been stale for a while"},
        {"value": StaleSeverity.HIGH.value, "label": "High", "description": "Critical - needs attention"},
        {"value": StaleSeverity.CRITICAL.value, "label": "Critical", "description": "Escalation needed immediately"},
    ]


@router.get("/stale-reasons", response_model=list[dict[str, str]])
async def get_stale_reasons():
    """
    Get all available stale reasons with descriptions.
    """
    return [
        {"value": StaleReason.NO_ACTIVITY.value, "label": "No Activity", "description": "No updates for too long"},
        {"value": StaleReason.STUCK_IN_STATUS.value, "label": "Stuck in Status", "description": "Stuck in current status too long"},
        {"value": StaleReason.OVERDUE.value, "label": "Overdue", "description": "Past due date"},
        {"value": StaleReason.NO_NEXT_STEP.value, "label": "No Next Step", "description": "Missing next step definition"},
        {"value": StaleReason.NEXT_STEP_OVERDUE.value, "label": "Next Step Overdue", "description": "Next step date has passed"},
        {"value": StaleReason.WAITING_TOO_LONG.value, "label": "Waiting Too Long", "description": "Waiting on external input too long"},
    ]


@router.get("/entity-types", response_model=list[dict[str, str]])
async def get_entity_types():
    """
    Get all entity types that support stale detection.
    """
    return [
        {"value": EntityType.OPPORTUNITY.value, "label": "Opportunity", "description": "Sales opportunities"},
        {"value": EntityType.RFQ.value, "label": "RFQ", "description": "Requests for quotation"},
        {"value": EntityType.TASK.value, "label": "Task", "description": "Tasks and action items"},
    ]

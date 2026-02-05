"""
RFQ Time Tracking API Endpoints.

Provides REST API for time-on-task tracking for RFQ intake and quote approval.
Implements session-based time tracking with pause/resume capability,
real-time performance monitoring, and analytics.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.api import deps
from sensei.core.config import settings
from sensei.services.sales.rfq_time_tracking import (
    RFQTimeTrackingService,
    TaskType,
    TaskSessionStatus,
    PerformanceLevel,
    TaskTarget,
    get_rfq_time_tracking_service,
)


router = APIRouter(
    dependencies=[
        Depends(deps.get_current_active_user),
    ]
)


# ===== Request/Response Schemas =====


class StartSessionRequest(BaseModel):
    """Request to start a task session."""
    
    task_type: str = Field(..., description="Type of task (rfq_intake, quote_approval, etc.)")
    entity_id: str = Field(..., description="ID of the entity (RFQ, Quote, etc.)")
    user_id: str = Field(..., description="ID of the user")
    notes: str | None = Field(None, description="Optional notes")
    metadata: dict | None = Field(None, description="Optional metadata")


class PauseSessionRequest(BaseModel):
    """Request to pause a session."""
    
    reason: str | None = Field(None, description="Reason for pausing")


class CompleteSessionRequest(BaseModel):
    """Request to complete a session."""
    
    notes: str | None = Field(None, description="Completion notes")


class AbandonSessionRequest(BaseModel):
    """Request to abandon a session."""
    
    reason: str | None = Field(None, description="Reason for abandoning")


class SetTargetRequest(BaseModel):
    """Request to set a task target."""
    
    task_type: str = Field(..., description="Type of task")
    target_seconds: int = Field(..., gt=0, description="Target time in seconds")
    warning_threshold_pct: float = Field(0.8, ge=0, le=1, description="Warning threshold percentage")
    critical_threshold_pct: float = Field(1.0, ge=0, le=2, description="Critical threshold percentage")
    max_threshold_pct: float = Field(1.2, ge=0, le=3, description="Max threshold percentage")


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge an alert."""
    
    user_id: str = Field(..., description="ID of user acknowledging")


class PauseResponse(BaseModel):
    """Pause record response."""
    
    paused_at: str
    resumed_at: str | None
    reason: str | None
    pause_duration_seconds: int


class SessionResponse(BaseModel):
    """Task session response."""
    
    id: str
    task_type: str
    entity_id: str
    user_id: str
    status: str
    started_at: str
    pauses: list[PauseResponse]
    completed_at: str | None
    total_pause_seconds: int
    active_elapsed_seconds: int
    is_currently_paused: bool
    notes: str | None
    metadata: dict


class SessionStatusResponse(BaseModel):
    """Session status check response."""
    
    session_id: str
    task_type: str
    status: str
    elapsed_seconds: int
    elapsed_formatted: str
    is_paused: bool
    pause_count: int
    total_pause_seconds: int
    target_seconds: int | None = None
    target_formatted: str | None = None
    remaining_seconds: int | None = None
    remaining_formatted: str | None = None
    percentage_used: float | None = None
    performance_level: str | None = None


class AlertResponse(BaseModel):
    """Time alert response."""
    
    id: str
    session_id: str
    task_type: str
    alert_type: str
    threshold_seconds: int
    elapsed_seconds: int
    created_at: str
    message: str
    acknowledged: bool
    acknowledged_at: str | None
    acknowledged_by: str | None


class TargetResponse(BaseModel):
    """Task target response."""
    
    task_type: str
    target_seconds: int
    warning_seconds: int
    critical_seconds: int
    max_seconds: int


class PerformanceStatsResponse(BaseModel):
    """Performance statistics response."""
    
    task_type: str
    period_start: str
    period_end: str
    total_sessions: int
    completed_sessions: int
    abandoned_sessions: int
    average_duration_seconds: float
    median_duration_seconds: float
    min_duration_seconds: int
    max_duration_seconds: int
    p90_duration_seconds: int
    target_seconds: int
    sessions_under_target: int
    sessions_over_target: int
    target_compliance_rate: float


class UserEfficiencyResponse(BaseModel):
    """User efficiency response."""
    
    user_id: str
    period_start: str
    period_end: str
    metrics_by_task: dict
    total_active_time_seconds: int
    total_sessions: int
    efficiency_score: float
    trend: str


class DailyBreakdownResponse(BaseModel):
    """Daily breakdown response."""
    
    date: str
    task_type: str
    total_sessions: int
    completed_sessions: int
    total_active_seconds: int
    average_duration_seconds: float
    under_target_count: int
    over_target_count: int


class LeaderboardEntryResponse(BaseModel):
    """Leaderboard entry response."""
    
    user_id: str
    completed_sessions: int
    average_duration_seconds: float
    target_compliance_rate: float
    efficiency_rank: int


class RFQSummaryResponse(BaseModel):
    """RFQ intake summary response."""
    
    rfq_id: str
    total_sessions: int
    completed_sessions: int
    active_sessions: int
    abandoned_sessions: int
    total_active_time_seconds: int
    total_active_time_formatted: str
    target_seconds: int
    target_formatted: str
    within_target: bool
    sessions: list[SessionResponse]


class CleanupResponse(BaseModel):
    """Cleanup response."""
    
    expired_sessions: int


# ===== Helper Functions =====


def get_service() -> RFQTimeTrackingService:
    """Get the time tracking service instance."""
    return get_rfq_time_tracking_service()


def validate_task_type(task_type: str) -> TaskType:
    """Validate and convert task type string."""
    try:
        return TaskType(task_type)
    except ValueError:
        valid_types = [t.value for t in TaskType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task type: {task_type}. Valid types: {valid_types}",
        )


def validate_uuid(uuid_str: str, field_name: str) -> UUID:
    """Validate and convert UUID string."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID for {field_name}: {uuid_str}",
        )


# ===== Session Endpoints =====


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a task session",
    description="Start tracking time for a task. Returns existing session if already active.",
)
def start_session(request: StartSessionRequest) -> SessionResponse:
    """Start a new task session."""
    service = get_service()
    
    task_type = validate_task_type(request.task_type)
    entity_id = validate_uuid(request.entity_id, "entity_id")
    user_id = validate_uuid(request.user_id, "user_id")
    
    session = service.start_session(
        task_type=task_type,
        entity_id=entity_id,
        user_id=user_id,
        notes=request.notes,
        metadata=request.metadata,
    )
    
    return SessionResponse(**session.to_dict())


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a session",
    description="Get a task session by ID.",
)
def get_session(session_id: str) -> SessionResponse:
    """Get a session by ID."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    session = service.get_session(sid)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.get(
    "/sessions/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Check session status",
    description="Get real-time status of a session with elapsed time and performance metrics.",
)
def check_session_status(session_id: str) -> SessionStatusResponse:
    """Check current status of a session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    result = service.check_session_status(sid)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )
    
    return SessionStatusResponse(**result)


@router.post(
    "/sessions/{session_id}/pause",
    response_model=SessionResponse,
    summary="Pause a session",
    description="Pause an active session. Time while paused is not counted.",
)
def pause_session(session_id: str, request: PauseSessionRequest) -> SessionResponse:
    """Pause a session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    session = service.pause_session(sid, reason=request.reason)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.post(
    "/sessions/{session_id}/resume",
    response_model=SessionResponse,
    summary="Resume a session",
    description="Resume a paused session.",
)
def resume_session(session_id: str) -> SessionResponse:
    """Resume a paused session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    session = service.resume_session(sid)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.post(
    "/sessions/{session_id}/complete",
    response_model=SessionResponse,
    summary="Complete a session",
    description="Mark a session as completed.",
)
def complete_session(session_id: str, request: CompleteSessionRequest) -> SessionResponse:
    """Complete a session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    session = service.complete_session(sid, notes=request.notes)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.post(
    "/sessions/{session_id}/abandon",
    response_model=SessionResponse,
    summary="Abandon a session",
    description="Abandon a session that won't be completed.",
)
def abandon_session(session_id: str, request: AbandonSessionRequest) -> SessionResponse:
    """Abandon a session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    session = service.abandon_session(sid, reason=request.reason)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.get(
    "/sessions/active/{entity_id}/{user_id}",
    response_model=SessionResponse | None,
    summary="Get active session for entity/user",
    description="Get the active session for a specific entity and user combination.",
)
def get_active_session(entity_id: str, user_id: str) -> SessionResponse | None:
    """Get active session for entity and user."""
    service = get_service()
    
    eid = validate_uuid(entity_id, "entity_id")
    uid = validate_uuid(user_id, "user_id")
    
    session = service.get_active_session(eid, uid)
    
    if not session:
        return None
    
    return SessionResponse(**session.to_dict())


@router.get(
    "/sessions/user/{user_id}/active",
    response_model=list[SessionResponse],
    summary="Get user's active sessions",
    description="Get all active sessions for a user.",
)
def get_user_active_sessions(user_id: str) -> list[SessionResponse]:
    """Get all active sessions for a user."""
    service = get_service()
    
    uid = validate_uuid(user_id, "user_id")
    sessions = service.get_user_active_sessions(uid)
    
    return [SessionResponse(**s.to_dict()) for s in sessions]


@router.get(
    "/sessions/entity/{entity_id}",
    response_model=list[SessionResponse],
    summary="Get entity's sessions",
    description="Get all sessions for an entity.",
)
def get_entity_sessions(entity_id: str) -> list[SessionResponse]:
    """Get all sessions for an entity."""
    service = get_service()
    
    eid = validate_uuid(entity_id, "entity_id")
    sessions = service.get_entity_sessions(eid)
    
    return [SessionResponse(**s.to_dict()) for s in sessions]


# ===== Alert Endpoints =====


@router.get(
    "/sessions/{session_id}/alerts",
    response_model=list[AlertResponse],
    summary="Get session alerts",
    description="Get all alerts for a session.",
)
def get_session_alerts(session_id: str) -> list[AlertResponse]:
    """Get alerts for a session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    alerts = service.get_session_alerts(sid)
    
    return [AlertResponse(**a.to_dict()) for a in alerts]


@router.get(
    "/alerts/pending",
    response_model=list[AlertResponse],
    summary="Get pending alerts",
    description="Get all pending (unacknowledged) alerts, optionally filtered by user.",
)
def get_pending_alerts(
    user_id: Annotated[str | None, Query(description="Filter by user ID")] = None,
) -> list[AlertResponse]:
    """Get pending alerts."""
    service = get_service()
    
    uid = validate_uuid(user_id, "user_id") if user_id else None
    alerts = service.get_pending_alerts(uid)
    
    return [AlertResponse(**a.to_dict()) for a in alerts]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an alert",
    description="Acknowledge a time tracking alert.",
)
def acknowledge_alert(alert_id: str, request: AcknowledgeAlertRequest) -> AlertResponse:
    """Acknowledge an alert."""
    service = get_service()
    
    aid = validate_uuid(alert_id, "alert_id")
    uid = validate_uuid(request.user_id, "user_id")
    
    alert = service.acknowledge_alert(aid, uid)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert not found: {alert_id}",
        )
    
    return AlertResponse(**alert.to_dict())


# ===== Target Endpoints =====


@router.get(
    "/targets",
    response_model=list[TargetResponse],
    summary="Get all targets",
    description="Get all task time targets.",
)
def get_all_targets() -> list[TargetResponse]:
    """Get all task targets."""
    service = get_service()
    targets = service.get_all_targets()
    
    return [TargetResponse(**t.to_dict()) for t in targets.values()]


@router.get(
    "/targets/{task_type}",
    response_model=TargetResponse,
    summary="Get target for task type",
    description="Get the time target for a specific task type.",
)
def get_target(task_type: str) -> TargetResponse:
    """Get target for a task type."""
    service = get_service()
    
    tt = validate_task_type(task_type)
    target = service.get_target(tt)
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No target configured for task type: {task_type}",
        )
    
    return TargetResponse(**target.to_dict())


@router.put(
    "/targets",
    response_model=TargetResponse,
    summary="Set a target",
    description="Set or update a task time target.",
)
def set_target(request: SetTargetRequest) -> TargetResponse:
    """Set a task target."""
    service = get_service()
    
    tt = validate_task_type(request.task_type)
    
    target = TaskTarget(
        task_type=tt,
        target_seconds=request.target_seconds,
        warning_threshold_pct=request.warning_threshold_pct,
        critical_threshold_pct=request.critical_threshold_pct,
        max_threshold_pct=request.max_threshold_pct,
    )
    
    service.set_target(target)
    
    return TargetResponse(**target.to_dict())


# ===== Analytics Endpoints =====


@router.get(
    "/analytics/performance/{task_type}",
    response_model=PerformanceStatsResponse | None,
    summary="Get performance stats",
    description="Get performance statistics for a task type.",
)
def get_performance_stats(
    task_type: str,
    start_date: Annotated[str | None, Query(description="Start date (ISO format)")] = None,
    end_date: Annotated[str | None, Query(description="End date (ISO format)")] = None,
    user_id: Annotated[str | None, Query(description="Filter by user ID")] = None,
) -> PerformanceStatsResponse | None:
    """Get performance statistics."""
    service = get_service()
    
    tt = validate_task_type(task_type)
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    uid = validate_uuid(user_id, "user_id") if user_id else None
    
    stats = service.get_performance_stats(tt, start, end, uid)
    
    if not stats:
        return None
    
    return PerformanceStatsResponse(**stats.to_dict())


@router.get(
    "/analytics/efficiency/{user_id}",
    response_model=UserEfficiencyResponse | None,
    summary="Get user efficiency",
    description="Get efficiency metrics for a user.",
)
def get_user_efficiency(
    user_id: str,
    start_date: Annotated[str | None, Query(description="Start date (ISO format)")] = None,
    end_date: Annotated[str | None, Query(description="End date (ISO format)")] = None,
) -> UserEfficiencyResponse | None:
    """Get user efficiency metrics."""
    service = get_service()
    
    uid = validate_uuid(user_id, "user_id")
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    efficiency = service.get_user_efficiency(uid, start, end)
    
    if not efficiency:
        return None
    
    return UserEfficiencyResponse(**efficiency.to_dict())


@router.get(
    "/analytics/daily/{task_type}",
    response_model=list[DailyBreakdownResponse],
    summary="Get daily breakdown",
    description="Get daily breakdown of task performance.",
)
def get_daily_breakdown(
    task_type: str,
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
) -> list[DailyBreakdownResponse]:
    """Get daily breakdown."""
    service = get_service()
    
    tt = validate_task_type(task_type)
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    breakdown = service.get_daily_breakdown(tt, start, end)
    
    return [DailyBreakdownResponse(**d.to_dict()) for d in breakdown]


@router.get(
    "/analytics/leaderboard/{task_type}",
    response_model=list[LeaderboardEntryResponse],
    summary="Get leaderboard",
    description="Get leaderboard of users by task efficiency.",
)
def get_leaderboard(
    task_type: str,
    start_date: Annotated[str | None, Query(description="Start date (ISO format)")] = None,
    end_date: Annotated[str | None, Query(description="End date (ISO format)")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Max users to return")] = 10,
) -> list[LeaderboardEntryResponse]:
    """Get leaderboard."""
    service = get_service()
    
    tt = validate_task_type(task_type)
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    leaderboard = service.get_leaderboard(tt, start, end, limit)
    
    return [LeaderboardEntryResponse(**entry) for entry in leaderboard]


# ===== RFQ-Specific Endpoints =====


@router.get(
    "/rfq/{rfq_id}/summary",
    response_model=RFQSummaryResponse,
    summary="Get RFQ intake summary",
    description="Get summary of all time tracking for an RFQ.",
)
def get_rfq_intake_summary(rfq_id: str) -> RFQSummaryResponse:
    """Get RFQ intake summary."""
    service = get_service()
    
    rid = validate_uuid(rfq_id, "rfq_id")
    summary = service.get_rfq_intake_summary(rid)
    
    return RFQSummaryResponse(
        rfq_id=summary["rfq_id"],
        total_sessions=summary["total_sessions"],
        completed_sessions=summary["completed_sessions"],
        active_sessions=summary["active_sessions"],
        abandoned_sessions=summary["abandoned_sessions"],
        total_active_time_seconds=summary["total_active_time_seconds"],
        total_active_time_formatted=summary["total_active_time_formatted"],
        target_seconds=summary["target_seconds"],
        target_formatted=summary["target_formatted"],
        within_target=summary["within_target"],
        sessions=[SessionResponse(**s) for s in summary["sessions"]],
    )


# ===== Maintenance Endpoints =====


@router.post(
    "/cleanup",
    response_model=CleanupResponse,
    summary="Cleanup expired sessions",
    description="Clean up abandoned/expired sessions older than specified hours.",
)
def cleanup_expired_sessions(
    max_age_hours: Annotated[int, Query(ge=1, le=168, description="Max age in hours")] = 24,
) -> CleanupResponse:
    """Cleanup expired sessions."""
    service = get_service()
    
    count = service.cleanup_expired_sessions(max_age_hours)
    
    return CleanupResponse(expired_sessions=count)

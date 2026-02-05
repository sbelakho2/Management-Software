"""
Quote Approval Time Tracking API Endpoints.

Provides REST API for quote approval time tracking with < 60 second target.
Includes session management, quick approval options, and analytics.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.api import deps
from sensei.core.config import settings
from sensei.services.sales.quote_approval_time_tracking import (
    QuoteApprovalTimeTrackingService,
    ApprovalDecision,
    ApprovalReason,
    ApprovalCriterionStatus,
    QuoteApprovalContext,
    get_quote_approval_service,
)


router = APIRouter(
    dependencies=[
        Depends(deps.get_current_active_user),
    ]
)


# ===== Request/Response Schemas =====


class QuoteApprovalContextRequest(BaseModel):
    """Request context for quote approval."""
    
    quote_id: str = Field(..., description="ID of the quote")
    quote_number: str = Field(..., description="Quote number")
    version: int = Field(1, ge=1, description="Quote version")
    customer_name: str = Field(..., description="Customer name")
    total_value: float = Field(..., gt=0, description="Total quote value")
    margin_percent: float = Field(..., description="Gross margin percentage")
    line_item_count: int = Field(..., ge=0, description="Number of line items")
    currency: str = Field("USD", description="Currency code")
    requested_by: str | None = Field(None, description="User requesting approval")
    urgency: str = Field("normal", description="Urgency level")
    notes: str | None = Field(None, description="Optional notes")


class StartApprovalRequest(BaseModel):
    """Request to start an approval session."""
    
    approver_id: str = Field(..., description="ID of the approver")
    context: QuoteApprovalContextRequest = Field(..., description="Quote context")


class MakeDecisionRequest(BaseModel):
    """Request to make an approval decision."""
    
    decision: str = Field(..., description="Decision: approved, rejected, returned_for_revision, escalated, delegated")
    reason: str | None = Field(None, description="Pre-defined reason code")
    custom_reason: str | None = Field(None, description="Custom reason text")
    comments: str | None = Field(None, description="Additional comments")
    escalated_to: str | None = Field(None, description="User to escalate to")
    delegated_to: str | None = Field(None, description="User to delegate to")


class QuickApproveRequest(BaseModel):
    """Request for quick approval."""
    
    option_id: str = Field(..., description="ID of the quick option")
    comments: str | None = Field(None, description="Optional comments (required for some options)")


class UpdateCriterionRequest(BaseModel):
    """Request to update a criterion."""
    
    criterion_id: str = Field(..., description="ID of the criterion")
    status: str = Field(..., description="New status: passed, failed, warning, skipped")
    message: str | None = Field(None, description="Optional message")


class AbandonRequest(BaseModel):
    """Request to abandon a session."""
    
    reason: str | None = Field(None, description="Reason for abandoning")


class SetTargetRequest(BaseModel):
    """Request to set time targets."""
    
    target_seconds: int = Field(60, ge=10, le=300, description="Target time in seconds")
    warning_seconds: int = Field(45, ge=5, le=290, description="Warning threshold")
    critical_seconds: int = Field(55, ge=5, le=295, description="Critical threshold")


class CriterionResponse(BaseModel):
    """Criterion response."""
    
    id: str
    name: str
    description: str
    category: str
    status: str
    value: float | str | None = None
    threshold: float | str | None = None
    message: str | None = None


class ContextResponse(BaseModel):
    """Context response."""
    
    quote_id: str
    quote_number: str
    version: int
    customer_name: str
    total_value: float
    margin_percent: float
    line_item_count: int
    currency: str
    requested_by: str | None
    requested_at: str | None
    urgency: str
    notes: str | None


class SessionResponse(BaseModel):
    """Approval session response."""
    
    id: str
    quote_id: str
    approver_id: str
    context: ContextResponse
    status: str
    started_at: str
    completed_at: str | None
    elapsed_seconds: int
    is_within_target: bool
    criteria: list[CriterionResponse]
    criteria_summary: dict
    decision: str | None
    reason: str | None
    custom_reason: str | None
    comments: str | None
    escalated_to: str | None
    delegated_to: str | None


class CountdownResponse(BaseModel):
    """Countdown status response."""
    
    session_id: str
    elapsed_seconds: int
    remaining_seconds: int
    target_seconds: int
    percentage: float
    status: str
    is_within_target: bool
    decision_status: str


class QuickOptionResponse(BaseModel):
    """Quick approval option response."""
    
    id: str
    label: str
    decision: str
    reason: str
    icon: str
    color: str
    requires_comment: bool


class PerformanceResponse(BaseModel):
    """Approver performance response."""
    
    approver_id: str
    period_start: str
    period_end: str
    total_approvals: int
    approvals_within_target: int
    approvals_over_target: int
    average_time_seconds: float
    median_time_seconds: float
    min_time_seconds: int
    max_time_seconds: int
    target_compliance_rate: float
    approval_rate: float
    delegation_rate: float
    escalation_rate: float


class QuoteSummaryResponse(BaseModel):
    """Quote approval summary response."""
    
    quote_id: str
    total_sessions: int
    decided_sessions: int
    pending_sessions: int
    final_decision: str | None
    final_decision_time_seconds: int | None
    within_target: bool | None
    sessions: list[SessionResponse]


class LeaderboardEntryResponse(BaseModel):
    """Leaderboard entry response."""
    
    rank: int
    approver_id: str
    total_approvals: int
    target_compliance_rate: float
    average_time_seconds: float


class TargetResponse(BaseModel):
    """Target configuration response."""
    
    target_seconds: int
    warning_seconds: int
    critical_seconds: int


# ===== Helper Functions =====


def get_service() -> QuoteApprovalTimeTrackingService:
    """Get the quote approval service instance."""
    return get_quote_approval_service()


def validate_uuid(uuid_str: str, field_name: str) -> UUID:
    """Validate and convert UUID string."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID for {field_name}: {uuid_str}",
        )


def validate_decision(decision: str) -> ApprovalDecision:
    """Validate and convert decision string."""
    try:
        return ApprovalDecision(decision)
    except ValueError:
        valid = [d.value for d in ApprovalDecision]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision: {decision}. Valid: {valid}",
        )


def validate_reason(reason: str) -> ApprovalReason:
    """Validate and convert reason string."""
    try:
        return ApprovalReason(reason)
    except ValueError:
        valid = [r.value for r in ApprovalReason]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reason: {reason}. Valid: {valid}",
        )


def validate_criterion_status(status_str: str) -> ApprovalCriterionStatus:
    """Validate and convert criterion status string."""
    try:
        return ApprovalCriterionStatus(status_str)
    except ValueError:
        valid = [s.value for s in ApprovalCriterionStatus]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_str}. Valid: {valid}",
        )


def build_context(req: QuoteApprovalContextRequest) -> QuoteApprovalContext:
    """Build context from request."""
    return QuoteApprovalContext(
        quote_id=validate_uuid(req.quote_id, "quote_id"),
        quote_number=req.quote_number,
        version=req.version,
        customer_name=req.customer_name,
        total_value=req.total_value,
        margin_percent=req.margin_percent,
        line_item_count=req.line_item_count,
        currency=req.currency,
        requested_by=validate_uuid(req.requested_by, "requested_by") if req.requested_by else None,
        urgency=req.urgency,
        notes=req.notes,
    )


# ===== Session Endpoints =====


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an approval session",
    description="Start a quote approval session with 60 second target countdown.",
)
def start_approval_session(request: StartApprovalRequest) -> SessionResponse:
    """Start a new approval session."""
    service = get_service()
    
    approver_id = validate_uuid(request.approver_id, "approver_id")
    context = build_context(request.context)
    
    session = service.start_approval_session(
        quote_id=context.quote_id,
        approver_id=approver_id,
        context=context,
    )
    
    return SessionResponse(**session.to_dict())


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get a session",
    description="Get an approval session by ID.",
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
    "/sessions/{session_id}/countdown",
    response_model=CountdownResponse,
    summary="Get countdown status",
    description="Get real-time countdown status for an approval session.",
)
def get_countdown_status(session_id: str) -> CountdownResponse:
    """Get countdown status for a session."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    result = service.check_session_countdown(sid)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )
    
    return CountdownResponse(**result)


@router.post(
    "/sessions/{session_id}/decide",
    response_model=SessionResponse,
    summary="Make a decision",
    description="Make an approval decision on a quote.",
)
def make_decision(session_id: str, request: MakeDecisionRequest) -> SessionResponse:
    """Make a decision on a quote."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    decision = validate_decision(request.decision)
    reason = validate_reason(request.reason) if request.reason else None
    
    escalated_to = validate_uuid(request.escalated_to, "escalated_to") if request.escalated_to else None
    delegated_to = validate_uuid(request.delegated_to, "delegated_to") if request.delegated_to else None
    
    session = service.make_decision(
        session_id=sid,
        decision=decision,
        reason=reason,
        custom_reason=request.custom_reason,
        comments=request.comments,
        escalated_to=escalated_to,
        delegated_to=delegated_to,
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.post(
    "/sessions/{session_id}/quick-approve",
    response_model=SessionResponse,
    summary="Quick approve",
    description="Use a pre-configured quick approval option.",
)
def quick_approve(session_id: str, request: QuickApproveRequest) -> SessionResponse:
    """Quick approve using pre-configured option."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    
    session = service.quick_approve(
        session_id=sid,
        option_id=request.option_id,
        comments=request.comments,
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quick approval failed. Option not found or comment required.",
        )
    
    return SessionResponse(**session.to_dict())


@router.post(
    "/sessions/{session_id}/criterion",
    response_model=SessionResponse,
    summary="Update criterion",
    description="Update a criterion status in an approval session.",
)
def update_criterion(session_id: str, request: UpdateCriterionRequest) -> SessionResponse:
    """Update a criterion."""
    service = get_service()
    
    sid = validate_uuid(session_id, "session_id")
    criterion_status = validate_criterion_status(request.status)
    
    session = service.update_criterion(
        session_id=sid,
        criterion_id=request.criterion_id,
        status=criterion_status,
        message=request.message,
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    
    return SessionResponse(**session.to_dict())


@router.post(
    "/sessions/{session_id}/abandon",
    response_model=SessionResponse,
    summary="Abandon session",
    description="Abandon an approval session.",
)
def abandon_session(session_id: str, request: AbandonRequest) -> SessionResponse:
    """Abandon an approval session."""
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
    "/sessions/quote/{quote_id}",
    response_model=list[SessionResponse],
    summary="Get quote sessions",
    description="Get all approval sessions for a quote.",
)
def get_quote_sessions(quote_id: str) -> list[SessionResponse]:
    """Get all sessions for a quote."""
    service = get_service()
    
    qid = validate_uuid(quote_id, "quote_id")
    sessions = service.get_quote_sessions(qid)
    
    return [SessionResponse(**s.to_dict()) for s in sessions]


@router.get(
    "/sessions/approver/{approver_id}/pending",
    response_model=list[SessionResponse],
    summary="Get pending sessions",
    description="Get pending approval sessions for an approver.",
)
def get_approver_pending(approver_id: str) -> list[SessionResponse]:
    """Get pending sessions for an approver."""
    service = get_service()
    
    aid = validate_uuid(approver_id, "approver_id")
    sessions = service.get_approver_pending(aid)
    
    return [SessionResponse(**s.to_dict()) for s in sessions]


# ===== Quick Options Endpoints =====


@router.get(
    "/quick-options",
    response_model=list[QuickOptionResponse],
    summary="Get quick options",
    description="Get available quick approval options for mobile/desktop.",
)
def get_quick_options() -> list[QuickOptionResponse]:
    """Get quick approval options."""
    service = get_service()
    options = service.get_quick_options()
    
    return [QuickOptionResponse(**o.to_dict()) for o in options]


# ===== Analytics Endpoints =====


@router.get(
    "/analytics/performance/{approver_id}",
    response_model=PerformanceResponse | None,
    summary="Get approver performance",
    description="Get performance metrics for an approver.",
)
def get_approver_performance(
    approver_id: str,
    start_date: Annotated[str | None, Query(description="Start date (ISO format)")] = None,
    end_date: Annotated[str | None, Query(description="End date (ISO format)")] = None,
) -> PerformanceResponse | None:
    """Get approver performance metrics."""
    service = get_service()
    
    aid = validate_uuid(approver_id, "approver_id")
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    perf = service.get_approver_performance(aid, start, end)
    
    if not perf:
        return None
    
    return PerformanceResponse(**perf.to_dict())


@router.get(
    "/analytics/quote/{quote_id}/summary",
    response_model=QuoteSummaryResponse,
    summary="Get quote summary",
    description="Get approval summary for a quote.",
)
def get_quote_summary(quote_id: str) -> QuoteSummaryResponse:
    """Get quote approval summary."""
    service = get_service()
    
    qid = validate_uuid(quote_id, "quote_id")
    summary = service.get_quote_approval_summary(qid)
    
    return QuoteSummaryResponse(**summary)


@router.get(
    "/analytics/leaderboard",
    response_model=list[LeaderboardEntryResponse],
    summary="Get leaderboard",
    description="Get leaderboard of approvers by speed and compliance.",
)
def get_leaderboard(
    start_date: Annotated[str | None, Query(description="Start date (ISO format)")] = None,
    end_date: Annotated[str | None, Query(description="End date (ISO format)")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Max entries")] = 10,
) -> list[LeaderboardEntryResponse]:
    """Get approval leaderboard."""
    service = get_service()
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    entries = service.get_approval_leaderboard(start, end, limit)
    
    return [LeaderboardEntryResponse(**e) for e in entries]


# ===== Configuration Endpoints =====


@router.get(
    "/targets",
    response_model=TargetResponse,
    summary="Get targets",
    description="Get current time targets.",
)
def get_targets() -> TargetResponse:
    """Get time targets."""
    service = get_service()
    return TargetResponse(**service.get_target())


@router.put(
    "/targets",
    response_model=TargetResponse,
    summary="Set targets",
    description="Set time targets for approval.",
)
def set_targets(request: SetTargetRequest) -> TargetResponse:
    """Set time targets."""
    service = get_service()
    
    service.set_target(
        target_seconds=request.target_seconds,
        warning_seconds=request.warning_seconds,
        critical_seconds=request.critical_seconds,
    )
    
    return TargetResponse(**service.get_target())

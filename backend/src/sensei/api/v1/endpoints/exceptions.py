"""
Exceptions API Endpoints

Provides endpoints for the exceptions-first dashboard navigation,
aggregating all red/warning items across the system.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.api.utils import APIResponse, build_response
from sensei.services.exceptions_aggregator import (
    ExceptionCategory,
    ExceptionItem,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionSummary,
    ExceptionTrend,
    NavigationBadge,
    create_exception,
    get_exceptions_aggregator,
)


router = APIRouter(tags=["exceptions"])


# =============================================================================
# Schemas
# =============================================================================


class ExceptionResponse(BaseModel):
    """Response schema for an exception item."""
    
    id: str
    title: str
    description: str
    category: str
    severity: str
    status: str
    created_at: datetime
    source: str
    due_date: Optional[datetime] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    department: Optional[str] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    source_url: Optional[str] = None
    resolution_time_minutes: Optional[int] = None
    escalated_at: Optional[datetime] = None
    escalated_to: Optional[str] = None
    blocked_reason: Optional[str] = None
    is_overdue: bool
    age_minutes: int
    priority_score: int
    tags: list[str] = Field(default_factory=list)
    
    @classmethod
    def from_item(cls, item: ExceptionItem) -> "ExceptionResponse":
        """Create response from exception item."""
        return cls(
            id=item.id,
            title=item.title,
            description=item.description,
            category=item.category.value,
            severity=item.severity.value,
            status=item.status.value,
            created_at=item.created_at,
            source=item.source,
            due_date=item.due_date,
            owner_id=item.owner_id,
            owner_name=item.owner_name,
            department=item.department,
            source_entity_type=item.source_entity_type,
            source_entity_id=item.source_entity_id,
            source_url=item.source_url,
            resolution_time_minutes=item.resolution_time_minutes,
            escalated_at=item.escalated_at,
            escalated_to=item.escalated_to,
            blocked_reason=item.blocked_reason,
            is_overdue=item.is_overdue,
            age_minutes=item.age_minutes,
            priority_score=item.priority_score,
            tags=item.tags,
        )


class ExceptionsListResponse(BaseModel):
    """Response for list of exceptions."""
    
    items: list[ExceptionResponse]
    total: int
    has_more: bool


class SummaryResponse(BaseModel):
    """Response for exceptions summary."""
    
    total_open: int
    critical_count: int
    high_count: int
    overdue_count: int
    escalated_count: int
    blocked_count: int
    by_category: dict[str, int]
    last_updated: datetime
    
    @classmethod
    def from_summary(cls, summary: ExceptionSummary) -> "SummaryResponse":
        """Create response from summary."""
        return cls(
            total_open=summary.total_open,
            critical_count=summary.critical_count,
            high_count=summary.high_count,
            overdue_count=summary.overdue_count,
            escalated_count=summary.escalated_count,
            blocked_count=summary.blocked_count,
            by_category=summary.by_category,
            last_updated=summary.last_updated,
        )


class BadgeResponse(BaseModel):
    """Response for a navigation badge."""
    
    module: str
    count: int
    severity: str
    has_critical: bool
    
    @classmethod
    def from_badge(cls, badge: NavigationBadge) -> "BadgeResponse":
        """Create response from badge."""
        return cls(
            module=badge.module,
            count=badge.count,
            severity=badge.severity.value,
            has_critical=badge.severity == ExceptionSeverity.CRITICAL,
        )


class NavigationBadgesResponse(BaseModel):
    """Response for all navigation badges."""
    
    badges: list[BadgeResponse]
    total_exceptions: int
    critical_total: int


class TrendPoint(BaseModel):
    """A single trend data point."""
    
    period: str  # Date as string, e.g. "2026-01-08"
    created: int
    resolved: int
    critical: int
    high: int
    medium: int
    low: int
    
    @classmethod
    def from_trend(cls, trend: ExceptionTrend) -> "TrendPoint":
        """Create response from trend."""
        return cls(
            period=trend.period,
            created=trend.created,
            resolved=trend.resolved,
            critical=trend.critical,
            high=trend.high,
            medium=trend.medium,
            low=trend.low,
        )


class TrendsResponse(BaseModel):
    """Response for trend data."""
    
    trends: list[TrendPoint]
    period_days: int


class CreateExceptionRequest(BaseModel):
    """Request to create a new exception."""
    
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    category: ExceptionCategory
    severity: ExceptionSeverity
    due_date: Optional[datetime] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    department: Optional[str] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    source_url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class EscalateRequest(BaseModel):
    """Request to escalate an exception."""
    
    escalate_to: str = Field(..., min_length=1, max_length=100)
    reason: Optional[str] = Field(None, max_length=500)


class ResolveRequest(BaseModel):
    """Request to resolve an exception."""
    
    resolution_notes: Optional[str] = Field(None, max_length=1000)


class BlockRequest(BaseModel):
    """Request to mark exception as blocked."""
    
    blocked_reason: str = Field(..., min_length=1, max_length=500)


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=APIResponse[ExceptionsListResponse],
    summary="Get all exceptions",
    description="Retrieve all exceptions with optional filtering",
)
async def get_exceptions(
    category: Optional[ExceptionCategory] = Query(None, description="Filter by category"),
    severity: Optional[ExceptionSeverity] = Query(None, description="Filter by severity"),
    status: Optional[ExceptionStatus] = Query(None, description="Filter by status"),
    overdue_only: bool = Query(False, description="Only show overdue items"),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> APIResponse:
    """Get all exceptions with optional filters."""
    aggregator = get_exceptions_aggregator()
    
    all_items = aggregator.get_all(
        category=category,
        severity=severity,
        status=status,
        overdue_only=overdue_only,
        limit=limit + offset + 1,  # Get one extra to check has_more
    )
    
    # Apply offset
    paginated = all_items[offset:offset + limit + 1]
    has_more = len(paginated) > limit
    items = paginated[:limit]
    
    data = ExceptionsListResponse(
        items=[ExceptionResponse.from_item(item) for item in items],
        total=len(all_items) - 1 if has_more else len(all_items),
        has_more=has_more,
    )
    return build_response(data=data)


@router.get(
    "/critical",
    response_model=ExceptionsListResponse,
    summary="Get critical exceptions",
    description="Get critical and high severity exceptions",
)
async def get_critical_exceptions(
    limit: int = Query(10, ge=1, le=100),
) -> ExceptionsListResponse:
    """Get critical and high severity exceptions."""
    aggregator = get_exceptions_aggregator()
    items = aggregator.get_critical(limit=limit)
    
    return ExceptionsListResponse(
        items=[ExceptionResponse.from_item(item) for item in items],
        total=len(items),
        has_more=len(items) >= limit,
    )


@router.get(
    "/overdue",
    response_model=ExceptionsListResponse,
    summary="Get overdue exceptions",
    description="Get all overdue exceptions",
)
async def get_overdue_exceptions(
    limit: int = Query(10, ge=1, le=100),
) -> ExceptionsListResponse:
    """Get all overdue exceptions."""
    aggregator = get_exceptions_aggregator()
    items = aggregator.get_overdue(limit=limit)
    
    return ExceptionsListResponse(
        items=[ExceptionResponse.from_item(item) for item in items],
        total=len(items),
        has_more=len(items) >= limit,
    )


@router.get(
    "/escalated",
    response_model=ExceptionsListResponse,
    summary="Get escalated exceptions",
    description="Get all escalated exceptions",
)
async def get_escalated_exceptions(
    limit: int = Query(10, ge=1, le=100),
) -> ExceptionsListResponse:
    """Get all escalated exceptions."""
    aggregator = get_exceptions_aggregator()
    items = aggregator.get_escalated(limit=limit)
    
    return ExceptionsListResponse(
        items=[ExceptionResponse.from_item(item) for item in items],
        total=len(items),
        has_more=len(items) >= limit,
    )


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Get exceptions summary",
    description="Get summary of all exceptions for dashboard",
)
async def get_exceptions_summary() -> SummaryResponse:
    """Get summary of all exceptions."""
    aggregator = get_exceptions_aggregator()
    summary = aggregator.get_summary()
    return SummaryResponse.from_summary(summary)


@router.get(
    "/badges",
    response_model=NavigationBadgesResponse,
    summary="Get navigation badges",
    description="Get badge data for sidebar navigation",
)
async def get_navigation_badges() -> NavigationBadgesResponse:
    """Get navigation badges for sidebar."""
    aggregator = get_exceptions_aggregator()
    badges = aggregator.get_navigation_badges()
    summary = aggregator.get_summary()
    
    return NavigationBadgesResponse(
        badges=[BadgeResponse.from_badge(b) for b in badges],
        total_exceptions=summary.total_open,
        critical_total=summary.critical_count,
    )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Get exception trends",
    description="Get trend data for exception charts",
)
async def get_exception_trends(
    days: int = Query(7, ge=1, le=90, description="Number of days of trend data"),
) -> TrendsResponse:
    """Get trend data for charts."""
    aggregator = get_exceptions_aggregator()
    trends = aggregator.get_trends(days=days)
    
    return TrendsResponse(
        trends=[TrendPoint.from_trend(t) for t in trends],
        period_days=days,
    )


@router.get(
    "/by-category/{category}",
    response_model=ExceptionsListResponse,
    summary="Get exceptions by category",
    description="Get all exceptions for a specific category",
)
async def get_exceptions_by_category(
    category: ExceptionCategory,
    limit: int = Query(20, ge=1, le=100),
) -> ExceptionsListResponse:
    """Get exceptions for a specific category."""
    aggregator = get_exceptions_aggregator()
    items = aggregator.get_by_category(category, limit=limit)
    
    return ExceptionsListResponse(
        items=[ExceptionResponse.from_item(item) for item in items],
        total=len(items),
        has_more=len(items) >= limit,
    )


@router.get(
    "/{exception_id}",
    response_model=ExceptionResponse,
    summary="Get exception by ID",
    description="Get a specific exception by its ID",
)
async def get_exception_by_id(
    exception_id: str,
) -> ExceptionResponse:
    """Get a specific exception by ID."""
    aggregator = get_exceptions_aggregator()
    
    for item in aggregator.get_all(limit=1000):
        if item.id == exception_id:
            return ExceptionResponse.from_item(item)
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Exception {exception_id} not found",
    )


@router.post(
    "",
    response_model=ExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create exception",
    description="Create a new exception manually",
)
async def create_new_exception(
    request: CreateExceptionRequest,
) -> ExceptionResponse:
    """Create a new exception."""
    aggregator = get_exceptions_aggregator()
    
    item = create_exception(
        title=request.title,
        description=request.description,
        category=request.category,
        severity=request.severity,
        due_date=request.due_date,
        owner_id=request.owner_id,
        owner_name=request.owner_name,
        department=request.department,
        source_entity_type=request.source_entity_type,
        source_entity_id=request.source_entity_id,
        source_url=request.source_url,
        tags=request.tags,
    )
    
    aggregator.add_exception(item)
    
    return ExceptionResponse.from_item(item)


@router.post(
    "/{exception_id}/acknowledge",
    response_model=ExceptionResponse,
    summary="Acknowledge exception",
    description="Mark an exception as acknowledged",
)
async def acknowledge_exception(
    exception_id: str,
) -> ExceptionResponse:
    """Acknowledge an exception."""
    aggregator = get_exceptions_aggregator()
    
    item = aggregator.acknowledge_exception(exception_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    
    return ExceptionResponse.from_item(item)


@router.post(
    "/{exception_id}/escalate",
    response_model=ExceptionResponse,
    summary="Escalate exception",
    description="Escalate an exception to someone else",
)
async def escalate_exception(
    exception_id: str,
    request: EscalateRequest,
) -> ExceptionResponse:
    """Escalate an exception."""
    aggregator = get_exceptions_aggregator()
    
    item = aggregator.escalate_exception(
        exception_id,
        escalate_to=request.escalate_to,
        reason=request.reason,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    
    return ExceptionResponse.from_item(item)


@router.post(
    "/{exception_id}/resolve",
    response_model=ExceptionResponse,
    summary="Resolve exception",
    description="Mark an exception as resolved",
)
async def resolve_exception(
    exception_id: str,
    request: ResolveRequest,
) -> ExceptionResponse:
    """Resolve an exception."""
    aggregator = get_exceptions_aggregator()
    
    item = aggregator.resolve_exception(
        exception_id,
        resolution_notes=request.resolution_notes,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    
    return ExceptionResponse.from_item(item)


@router.post(
    "/{exception_id}/block",
    response_model=ExceptionResponse,
    summary="Block exception",
    description="Mark an exception as blocked with a reason",
)
async def block_exception(
    exception_id: str,
    request: BlockRequest,
) -> ExceptionResponse:
    """Mark an exception as blocked."""
    aggregator = get_exceptions_aggregator()
    
    item = aggregator.update_exception(
        exception_id,
        {
            "status": ExceptionStatus.BLOCKED,
            "blocked_reason": request.blocked_reason,
        },
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    
    return ExceptionResponse.from_item(item)


@router.post(
    "/{exception_id}/in-progress",
    response_model=ExceptionResponse,
    summary="Start working on exception",
    description="Mark an exception as in progress",
)
async def start_exception(
    exception_id: str,
) -> ExceptionResponse:
    """Mark an exception as in progress."""
    aggregator = get_exceptions_aggregator()
    
    item = aggregator.update_exception(
        exception_id,
        {"status": ExceptionStatus.IN_PROGRESS},
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exception {exception_id} not found",
        )
    
    return ExceptionResponse.from_item(item)

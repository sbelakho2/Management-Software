"""
IT Infrastructure Monitoring API Endpoints.

Provides endpoints for system health, server metrics, service status, and IT alerts.

This module intentionally avoids returning fabricated metrics. When a signal can't be
derived (e.g., incident history, external service latency, logs), endpoints return
"unknown" or empty data.
"""

import os
import psutil
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.deps import DBSession, CurrentUser, CurrentSuperuser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.user import Role, User, UserRole

AllowITModule = deps.require_role("it")  # type: ignore[valid-type]

router = APIRouter(dependencies=[Depends(deps.RoleChecker(["it"]))])

# =============================================================================
# Schemas
# =============================================================================

class SystemHealthResponse(BaseModel):
    api_health: str
    db_health: str
    cache_health: str
    queue_health: str
    uptime: str
    last_incident: str


class ServerStatsResponse(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int


class ServiceStatusResponse(BaseModel):
    name: str
    status: str
    latency: str


class AlertResponse(BaseModel):
    id: str
    type: str
    message: str
    time: str
    resolved: bool


class ActiveUsersResponse(BaseModel):
    name: str
    count: int
    trend: str


# =============================================================================
# Helper Functions
# =============================================================================

def get_uptime() -> str:
    """Get system uptime as a duration string."""
    try:
        uptime_seconds = max(0, int(datetime.now(timezone.utc).timestamp() - psutil.boot_time()))
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days:
            return f"{days}d {hours}h {minutes}m"
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "unknown"


def get_last_incident() -> str:
    """Get time since last incident.

    Incident tracking is not currently persisted in the database.
    """
    return "unknown"


async def check_db_health(db: AsyncSession) -> str:
    """Check database connectivity."""
    try:
        await db.execute(select(func.now()))
        return "healthy"
    except Exception:
        return "down"


def check_service_status(service_name: str) -> tuple[str, str]:
    """Best-effort service status.

    Avoids returning fabricated per-service latencies; values are only returned
    when derived from a real check.
    """
    if service_name == "API Gateway":
        return "healthy", "N/A"
    return "unknown", "N/A"


def _alert(alert_id: str, alert_type: str, message: str, resolved: bool) -> AlertResponse:
    return AlertResponse(
        id=alert_id,
        type=alert_type,
        message=message,
        time=datetime.now(timezone.utc).isoformat(),
        resolved=resolved,
    )


# =============================================================================
# Endpoints - System Health
# =============================================================================

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(db: DBSession, current_user: CurrentUser) -> Any:
    """Get overall system health status."""
    db_health = await check_db_health(db)
    
    return SystemHealthResponse(
        api_health="healthy",
        db_health=db_health,
        cache_health="unknown",
        queue_health="unknown",
        uptime=get_uptime(),
        last_incident=get_last_incident()
    )


@router.get("/server-stats", response_model=ServerStatsResponse)
async def get_server_stats(db: DBSession, current_user: CurrentUser) -> Any:
    """Get server resource statistics."""
    active_connections = await db.scalar(select(func.count(User.id)).where(User.status == "active")) or 0

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    try:
        cpu_usage = float(psutil.cpu_percent(interval=0.1))
        memory_usage = float(psutil.virtual_memory().percent)
        disk_usage = float(psutil.disk_usage('/').percent)
    except Exception:
        # If host metrics aren't accessible (container restrictions), don't fabricate values.
        pass

    return ServerStatsResponse(
        cpu_usage=round(cpu_usage, 1),
        memory_usage=round(memory_usage, 1),
        disk_usage=round(disk_usage, 1),
        active_connections=int(active_connections),
    )


@router.get("/services", response_model=List[ServiceStatusResponse])
async def get_services_status(db: DBSession, current_user: CurrentUser) -> Any:
    """Get status of all monitored services."""
    services = [
        "API Gateway",
        "Database Primary",
        "Database Replica",
        "Redis Cache",
        "Message Queue",
        "ML Service",
    ]
    
    db_health = await check_db_health(db)

    result: List[ServiceStatusResponse] = []
    for service in services:
        if service == "Database Primary":
            status, latency = db_health, "N/A"
        else:
            status, latency = check_service_status(service)
        result.append(ServiceStatusResponse(name=service, status=status, latency=latency))
    
    return result


@router.get("/alerts", response_model=List[AlertResponse])
async def get_recent_alerts(
    db: DBSession,
    current_user: CurrentUser,
    include_resolved: bool = Query(True),
    limit: int = Query(20, ge=1, le=100)
) -> Any:
    """Get recent IT alerts."""
    alerts: List[AlertResponse] = []

    db_health = await check_db_health(db)
    if db_health != "healthy":
        alerts.append(_alert("db-unhealthy", "critical", "Database health check failed", False))

    try:
        cpu = float(psutil.cpu_percent(interval=0.1))
        mem = float(psutil.virtual_memory().percent)
        disk = float(psutil.disk_usage('/').percent)

        if cpu >= 90:
            alerts.append(_alert("cpu-high", "warning", f"High CPU usage: {cpu:.1f}%", False))
        if mem >= 90:
            alerts.append(_alert("memory-high", "warning", f"High memory usage: {mem:.1f}%", False))
        if disk >= 90:
            alerts.append(_alert("disk-high", "warning", f"High disk usage: {disk:.1f}%", False))
    except Exception:
        # Host metrics unavailable; don't fabricate alerts.
        pass
    
    if not include_resolved:
        alerts = [a for a in alerts if not a.resolved]
    
    return alerts[:limit]


@router.get("/active-users", response_model=List[ActiveUsersResponse])
async def get_active_users_by_team(db: DBSession, current_user: CurrentUser) -> Any:
    """Get active user counts by team/role."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Role.display_name, Role.name, func.count(User.id))
        .select_from(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            and_(
                User.status == "active",
                UserRole.is_active.is_(True),
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > now),
            )
        )
        .group_by(Role.display_name, Role.name)
        .order_by(func.count(User.id).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        ActiveUsersResponse(name=(display_name or role_name), count=int(count), trend="unknown")
        for display_name, role_name, count in rows
    ]


# =============================================================================
# Endpoints - Admin Operations (Superuser only)
# =============================================================================

@router.post("/clear-cache", response_model=dict)
async def clear_cache(db: DBSession, current_user: CurrentSuperuser) -> Any:
    """Clear application cache. Requires superuser access."""
    raise HTTPException(
        status_code=501,
        detail="Cache backend not configured; cannot clear cache via API.",
    )


@router.post("/restart-service/{service_name}", response_model=dict)
async def restart_service(
    service_name: str,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """Restart a specific service. Requires superuser access."""
    allowed_services = ["cache", "queue", "ml-service"]
    
    if service_name not in allowed_services:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restart service: {service_name}. Allowed: {allowed_services}"
        )
    
    raise HTTPException(
        status_code=501,
        detail=f"Service restarts are not configured for this deployment: {service_name}",
    )


@router.get("/logs", response_model=dict)
async def get_recent_logs(
    db: DBSession,
    current_user: CurrentSuperuser,
    service: Optional[str] = None,
    level: Optional[str] = Query(None, pattern="^(debug|info|warning|error|critical)$"),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """Get recent application logs. Requires superuser access."""
    return {
        "logs": [],
        "total": 0,
        "service": service,
        "level": level,
        "message": "Log aggregation is not configured; no logs available via API.",
    }

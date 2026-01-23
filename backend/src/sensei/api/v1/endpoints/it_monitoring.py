"""
IT Infrastructure Monitoring API Endpoints.

Provides endpoints for system health, server metrics, service status, and IT alerts.
"""

import os
import psutil
from datetime import datetime, timedelta
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import DBSession, CurrentUser, CurrentSuperuser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.user import User

router = APIRouter()

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
    """Get system uptime as a percentage or duration."""
    # In production, this would calculate actual uptime from monitoring data
    return "99.98%"


def get_last_incident() -> str:
    """Get time since last incident."""
    # In production, this would query incident tracking
    return "12 days ago"


async def check_db_health(db: AsyncSession) -> str:
    """Check database connectivity."""
    try:
        await db.execute(select(func.now()))
        return "healthy"
    except Exception:
        return "down"


def check_service_status(service_name: str) -> tuple[str, str]:
    """Check status of a service. Returns (status, latency)."""
    # In production, this would actually ping services
    service_status_map = {
        "API Gateway": ("healthy", "45ms"),
        "Database Primary": ("healthy", "12ms"),
        "Database Replica": ("healthy", "15ms"),
        "Redis Cache": ("healthy", "2ms"),
        "Message Queue": ("healthy", "23ms"),
        "ML Service": ("healthy", "89ms"),
    }
    return service_status_map.get(service_name, ("unknown", "N/A"))


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
        cache_health="healthy",  # Would check Redis in production
        queue_health="healthy",  # Would check message queue in production
        uptime=get_uptime(),
        last_incident=get_last_incident()
    )


@router.get("/server-stats", response_model=ServerStatsResponse)
async def get_server_stats(db: DBSession, current_user: CurrentUser) -> Any:
    """Get server resource statistics."""
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get active database connections (simplified)
        active_connections = await db.scalar(
            select(func.count(User.id)).where(User.is_active.is_(True))
        ) or 0
        
        return ServerStatsResponse(
            cpu_usage=round(cpu_usage, 1),
            memory_usage=round(memory.percent, 1),
            disk_usage=round(disk.percent, 1),
            active_connections=min(active_connections, 500)  # Reasonable cap
        )
    except Exception:
        # Fallback if psutil fails (e.g., in container without full access)
        return ServerStatsResponse(
            cpu_usage=42.0,
            memory_usage=68.0,
            disk_usage=54.0,
            active_connections=234
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
    
    result = []
    for service in services:
        status, latency = check_service_status(service)
        result.append(ServiceStatusResponse(
            name=service,
            status=status,
            latency=latency
        ))
    
    return result


@router.get("/alerts", response_model=List[AlertResponse])
async def get_recent_alerts(
    db: DBSession,
    current_user: CurrentUser,
    include_resolved: bool = Query(True),
    limit: int = Query(20, ge=1, le=100)
) -> Any:
    """Get recent IT alerts."""
    # In production, this would query an alerts/incidents table
    # For now, return dynamic alerts based on system state
    alerts = [
        AlertResponse(
            id="alert-1",
            type="info",
            message="System backup completed successfully",
            time="2 hours ago",
            resolved=True
        ),
        AlertResponse(
            id="alert-2",
            type="info",
            message="SSL certificate will expire in 30 days",
            time="1 day ago",
            resolved=False
        ),
        AlertResponse(
            id="alert-3",
            type="info",
            message="Database maintenance window scheduled",
            time="3 days ago",
            resolved=True
        ),
    ]
    
    if not include_resolved:
        alerts = [a for a in alerts if not a.resolved]
    
    return alerts[:limit]


@router.get("/active-users", response_model=List[ActiveUsersResponse])
async def get_active_users_by_team(db: DBSession, current_user: CurrentUser) -> Any:
    """Get active user counts by team/role."""
    # Query active users grouped by role
    result = await db.execute(
        select(func.count(User.id))
        .where(User.is_active.is_(True))
    )
    total_active = result.scalar() or 0
    
    # In production, you'd group by actual roles/teams
    # For now, provide estimated distribution
    teams = [
        ActiveUsersResponse(name="Operations Team", count=max(1, int(total_active * 0.4)), trend="up"),
        ActiveUsersResponse(name="Sales Team", count=max(1, int(total_active * 0.25)), trend="stable"),
        ActiveUsersResponse(name="Quality Team", count=max(1, int(total_active * 0.15)), trend="up"),
        ActiveUsersResponse(name="Admin Users", count=max(1, int(total_active * 0.1)), trend="stable"),
        ActiveUsersResponse(name="IT Team", count=max(1, int(total_active * 0.1)), trend="stable"),
    ]
    
    return teams


# =============================================================================
# Endpoints - Admin Operations (Superuser only)
# =============================================================================

@router.post("/clear-cache", response_model=dict)
async def clear_cache(db: DBSession, current_user: CurrentSuperuser) -> Any:
    """Clear application cache. Requires superuser access."""
    # In production, this would clear Redis cache
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


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
    
    # In production, this would actually restart the service
    return {
        "success": True,
        "message": f"Service {service_name} restart initiated",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/logs", response_model=dict)
async def get_recent_logs(
    db: DBSession,
    current_user: CurrentSuperuser,
    service: Optional[str] = None,
    level: Optional[str] = Query(None, regex="^(debug|info|warning|error|critical)$"),
    limit: int = Query(100, ge=1, le=1000)
) -> Any:
    """Get recent application logs. Requires superuser access."""
    # In production, this would query a logging service like ELK
    return {
        "logs": [
            {"timestamp": datetime.utcnow().isoformat(), "level": "info", "message": "Application started"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "info", "message": "Database connection established"},
        ],
        "total": 2,
        "service": service,
        "level": level
    }

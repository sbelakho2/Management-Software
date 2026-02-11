"""
Backup Scheduler API Endpoints

Admin-only endpoints for automated backup schedule management,
monitoring, and disaster recovery readiness reporting.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime

from sensei.api.deps import require_role, RoleChecker
from sensei.models.user import RoleType
from sensei.services.core.backup_scheduler import (
    BackupSchedulerService,
    BackupSchedule,
    ScheduleType,
    ScheduleExecution,
)
from sensei.services.core.database_backup import BackupStrategy


router = APIRouter()


# Request/Response Models

class ScheduleCreateRequest(BaseModel):
    """Request to create a new backup schedule"""
    id: str = Field(..., description="Unique schedule identifier")
    name: str = Field(..., description="Human-readable schedule name")
    schedule_type: ScheduleType = Field(..., description="Schedule type")
    strategy: BackupStrategy = Field(..., description="Backup strategy")
    enabled: bool = Field(default=True, description="Whether schedule is enabled")
    cron_expression: Optional[str] = Field(None, description="Cron expression for CUSTOM schedules")
    interval_minutes: Optional[int] = Field(None, description="Interval in minutes for CUSTOM schedules")
    retention_days: int = Field(default=30, description="Number of days to retain backups")
    auto_test_restore: bool = Field(default=False, description="Automatically test restores")
    test_frequency_days: int = Field(default=7, description="Days between restore tests")
    alert_on_failure: bool = Field(default=True, description="Send alerts on backup failure")


class ScheduleUpdateRequest(BaseModel):
    """Request to update an existing schedule"""
    name: Optional[str] = Field(None, description="Updated schedule name")
    enabled: Optional[bool] = Field(None, description="Enable/disable schedule")
    cron_expression: Optional[str] = Field(None, description="Updated cron expression")
    interval_minutes: Optional[int] = Field(None, description="Updated interval")
    retention_days: Optional[int] = Field(None, description="Updated retention period")
    auto_test_restore: Optional[bool] = Field(None, description="Enable/disable auto restore testing")
    test_frequency_days: Optional[int] = Field(None, description="Updated test frequency")
    alert_on_failure: Optional[bool] = Field(None, description="Enable/disable failure alerts")


class ScheduleResponse(BaseModel):
    """Backup schedule details"""
    id: str
    name: str
    schedule_type: ScheduleType
    strategy: BackupStrategy
    enabled: bool
    cron_expression: Optional[str]
    interval_minutes: Optional[int]
    retention_days: int
    auto_test_restore: bool
    test_frequency_days: int
    alert_on_failure: bool
    last_execution: Optional[datetime]
    last_test: Optional[datetime]
    consecutive_failures: int


class ExecutionResponse(BaseModel):
    """Backup execution details"""
    id: str
    schedule_id: str
    execution_time: datetime
    status: str
    backup_id: Optional[str]
    duration_seconds: Optional[float]
    size_bytes: Optional[int]
    error_message: Optional[str]
    test_result: Optional[dict]


class RPOComplianceResponse(BaseModel):
    """RPO compliance status"""
    rpo_status: str
    within_target: bool
    total_schedules: int
    enabled_schedules: int
    failed_schedules: int
    backup_service_status: dict


class RTOComplianceResponse(BaseModel):
    """RTO compliance status"""
    rto_status: str
    within_target: bool
    schedules_needing_test: List[str]
    backup_service_status: dict


class ReadinessResponse(BaseModel):
    """Disaster recovery readiness report"""
    readiness_score: int
    readiness_level: str
    rpo_compliance: dict
    rto_compliance: dict
    backup_success_rate: float
    recent_executions: int
    recommendations: List[str]


# Dependency to get scheduler service
async def get_scheduler_service() -> BackupSchedulerService:
    """Get the backup scheduler service instance"""
    from sensei.main import app
    if not hasattr(app.state, "backup_scheduler"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backup scheduler service not initialized"
        )
    return app.state.backup_scheduler


# Endpoints

@router.get(
    "/schedules",
    response_model=List[ScheduleResponse],
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="List all backup schedules",
)
async def list_schedules(
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """List all backup schedules with their current status"""
    schedules = []
    for schedule in scheduler.schedules.values():
        schedules.append(ScheduleResponse(
            id=schedule.id,
            name=schedule.name,
            schedule_type=schedule.schedule_type,
            strategy=schedule.strategy,
            enabled=schedule.enabled,
            cron_expression=schedule.cron_expression,
            interval_minutes=schedule.interval_minutes,
            retention_days=schedule.retention_days,
            auto_test_restore=schedule.auto_test_restore,
            test_frequency_days=schedule.test_frequency_days,
            alert_on_failure=schedule.alert_on_failure,
            last_execution=schedule.last_execution,
            last_test=schedule.last_test,
            consecutive_failures=schedule.consecutive_failures,
        ))
    return schedules


@router.post(
    "/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Create a new backup schedule",
)
async def create_schedule(
    request: ScheduleCreateRequest,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Create a new backup schedule"""
    if request.id in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Schedule with ID '{request.id}' already exists"
        )
    
    schedule = BackupSchedule(
        id=request.id,
        name=request.name,
        schedule_type=request.schedule_type,
        strategy=request.strategy,
        enabled=request.enabled,
        cron_expression=request.cron_expression,
        interval_minutes=request.interval_minutes,
        retention_days=request.retention_days,
        auto_test_restore=request.auto_test_restore,
        test_frequency_days=request.test_frequency_days,
        alert_on_failure=request.alert_on_failure,
    )
    
    scheduler.add_schedule(schedule)
    
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        strategy=schedule.strategy,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        interval_minutes=schedule.interval_minutes,
        retention_days=schedule.retention_days,
        auto_test_restore=schedule.auto_test_restore,
        test_frequency_days=schedule.test_frequency_days,
        alert_on_failure=schedule.alert_on_failure,
        last_execution=schedule.last_execution,
        last_test=schedule.last_test,
        consecutive_failures=schedule.consecutive_failures,
    )


@router.get(
    "/schedules/{schedule_id}",
    response_model=ScheduleResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Get schedule details",
)
async def get_schedule(
    schedule_id: str,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Get details of a specific backup schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    schedule = scheduler.schedules[schedule_id]
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        strategy=schedule.strategy,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        interval_minutes=schedule.interval_minutes,
        retention_days=schedule.retention_days,
        auto_test_restore=schedule.auto_test_restore,
        test_frequency_days=schedule.test_frequency_days,
        alert_on_failure=schedule.alert_on_failure,
        last_execution=schedule.last_execution,
        last_test=schedule.last_test,
        consecutive_failures=schedule.consecutive_failures,
    )


@router.put(
    "/schedules/{schedule_id}",
    response_model=ScheduleResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Update a backup schedule",
)
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdateRequest,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Update an existing backup schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    schedule = scheduler.schedules[schedule_id]
    
    # Update fields if provided
    if request.name is not None:
        schedule.name = request.name
    if request.enabled is not None:
        if request.enabled and not schedule.enabled:
            scheduler.enable_schedule(schedule_id)
        elif not request.enabled and schedule.enabled:
            scheduler.disable_schedule(schedule_id)
    if request.cron_expression is not None:
        schedule.cron_expression = request.cron_expression
    if request.interval_minutes is not None:
        schedule.interval_minutes = request.interval_minutes
    if request.retention_days is not None:
        schedule.retention_days = request.retention_days
    if request.auto_test_restore is not None:
        schedule.auto_test_restore = request.auto_test_restore
    if request.test_frequency_days is not None:
        schedule.test_frequency_days = request.test_frequency_days
    if request.alert_on_failure is not None:
        schedule.alert_on_failure = request.alert_on_failure
    
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        strategy=schedule.strategy,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        interval_minutes=schedule.interval_minutes,
        retention_days=schedule.retention_days,
        auto_test_restore=schedule.auto_test_restore,
        test_frequency_days=schedule.test_frequency_days,
        alert_on_failure=schedule.alert_on_failure,
        last_execution=schedule.last_execution,
        last_test=schedule.last_test,
        consecutive_failures=schedule.consecutive_failures,
    )


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Delete a backup schedule",
)
async def delete_schedule(
    schedule_id: str,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Delete a backup schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    scheduler.remove_schedule(schedule_id)


@router.post(
    "/schedules/{schedule_id}/enable",
    response_model=ScheduleResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Enable a backup schedule",
)
async def enable_schedule(
    schedule_id: str,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Enable a disabled backup schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    scheduler.enable_schedule(schedule_id)
    schedule = scheduler.schedules[schedule_id]
    
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        strategy=schedule.strategy,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        interval_minutes=schedule.interval_minutes,
        retention_days=schedule.retention_days,
        auto_test_restore=schedule.auto_test_restore,
        test_frequency_days=schedule.test_frequency_days,
        alert_on_failure=schedule.alert_on_failure,
        last_execution=schedule.last_execution,
        last_test=schedule.last_test,
        consecutive_failures=schedule.consecutive_failures,
    )


@router.post(
    "/schedules/{schedule_id}/disable",
    response_model=ScheduleResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Disable a backup schedule",
)
async def disable_schedule(
    schedule_id: str,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Disable an active backup schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    scheduler.disable_schedule(schedule_id)
    schedule = scheduler.schedules[schedule_id]
    
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        strategy=schedule.strategy,
        enabled=schedule.enabled,
        cron_expression=schedule.cron_expression,
        interval_minutes=schedule.interval_minutes,
        retention_days=schedule.retention_days,
        auto_test_restore=schedule.auto_test_restore,
        test_frequency_days=schedule.test_frequency_days,
        alert_on_failure=schedule.alert_on_failure,
        last_execution=schedule.last_execution,
        last_test=schedule.last_test,
        consecutive_failures=schedule.consecutive_failures,
    )


@router.post(
    "/schedules/{schedule_id}/force",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Force immediate backup",
)
async def force_backup(
    schedule_id: str,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Force an immediate backup execution for a schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    try:
        backup_id = scheduler.force_backup(schedule_id)
        return {
            "message": f"Backup triggered for schedule '{schedule_id}'",
            "backup_id": backup_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger backup: {str(e)}"
        )


@router.get(
    "/schedules/{schedule_id}/history",
    response_model=List[ExecutionResponse],
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Get schedule execution history",
)
async def get_schedule_history(
    schedule_id: str,
    limit: int = 50,
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Get execution history for a backup schedule"""
    if schedule_id not in scheduler.schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found"
        )
    
    history = scheduler.get_schedule_history(schedule_id, limit=limit)
    
    return [
        ExecutionResponse(
            id=execution.id,
            schedule_id=execution.schedule_id,
            execution_time=execution.execution_time,
            status=execution.status.value,
            backup_id=execution.backup_id,
            duration_seconds=execution.duration_seconds,
            size_bytes=execution.size_bytes,
            error_message=execution.error_message,
            test_result=execution.test_result,
        )
        for execution in history
    ]


@router.get(
    "/rpo",
    response_model=RPOComplianceResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Get RPO compliance status",
)
async def get_rpo_compliance(
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Get Recovery Point Objective (RPO) compliance status"""
    compliance = scheduler.get_rpo_compliance()
    return RPOComplianceResponse(**compliance)


@router.get(
    "/rto",
    response_model=RTOComplianceResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Get RTO compliance status",
)
async def get_rto_compliance(
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Get Recovery Time Objective (RTO) compliance status"""
    compliance = scheduler.get_rto_compliance()
    return RTOComplianceResponse(**compliance)


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    dependencies=[Depends(RoleChecker([RoleType.ADMIN]))],
    summary="Get disaster recovery readiness",
)
async def get_disaster_recovery_readiness(
    scheduler: BackupSchedulerService = Depends(get_scheduler_service),
):
    """Get comprehensive disaster recovery readiness report"""
    readiness = scheduler.get_disaster_recovery_readiness()
    return ReadinessResponse(**readiness)

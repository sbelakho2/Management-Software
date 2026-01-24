"""
Disaster Recovery Drill API endpoints.

Provides endpoints for:
- RPO/RTO target management
- Drill configuration management
- Schedule management
- Drill execution
- Results and compliance reporting
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sensei.services.core.disaster_recovery_drill import (
    BackupInfo,
    ComplianceLevel,
    DrillStatus,
    DrillType,
    RecoveryTarget,
    get_dr_drill_service,
    reset_dr_drill_service,
)


router = APIRouter()


# ===== Request/Response Models =====


class RPOTargetCreate(BaseModel):
    """Request to create an RPO target."""
    
    target_name: str = Field(..., description="Unique name for the target")
    recovery_target: str = Field(..., description="Recovery target type")
    max_data_loss_minutes: int = Field(..., ge=1, description="Maximum data loss in minutes")
    description: str | None = Field(None, description="Optional description")


class RTOTargetCreate(BaseModel):
    """Request to create an RTO target."""
    
    target_name: str = Field(..., description="Unique name for the target")
    recovery_target: str = Field(..., description="Recovery target type")
    max_recovery_minutes: int = Field(..., ge=1, description="Maximum recovery time in minutes")
    description: str | None = Field(None, description="Optional description")


class RPOTargetResponse(BaseModel):
    """Response containing RPO target data."""
    
    target_name: str
    recovery_target: str
    max_data_loss_minutes: int
    description: str | None = None


class RTOTargetResponse(BaseModel):
    """Response containing RTO target data."""
    
    target_name: str
    recovery_target: str
    max_recovery_minutes: int
    description: str | None = None


class ConfigurationCreate(BaseModel):
    """Request to create a drill configuration."""
    
    name: str = Field(..., description="Configuration name")
    description: str = Field(..., description="Configuration description")
    drill_type: str = Field(..., description="Type of drill")
    recovery_target: str = Field(..., description="Recovery target")
    rpo_target_minutes: int = Field(60, ge=1, description="RPO target in minutes")
    rto_target_minutes: int = Field(60, ge=1, description="RTO target in minutes")
    notify_on_failure: bool = Field(True, description="Notify on failure")
    notify_on_success: bool = Field(False, description="Notify on success")
    notification_emails: list[str] = Field(default_factory=list, description="Email addresses")


class ConfigurationResponse(BaseModel):
    """Response containing configuration data."""
    
    id: str
    name: str
    description: str
    drill_type: str
    recovery_target: str
    rpo_target_minutes: int
    rto_target_minutes: int
    notify_on_failure: bool
    notify_on_success: bool
    notification_emails: list[str]
    created_at: datetime


class ScheduleCreate(BaseModel):
    """Request to create a drill schedule."""
    
    configuration_id: str = Field(..., description="ID of the configuration")
    frequency: str = Field(..., description="Schedule frequency: daily, weekly, monthly")
    time_of_day: str = Field("02:00", description="Time to run in HH:MM format")
    day_of_week: int | None = Field(None, ge=0, le=6, description="Day of week (0=Monday)")
    day_of_month: int | None = Field(None, ge=1, le=28, description="Day of month")


class ScheduleResponse(BaseModel):
    """Response containing schedule data."""
    
    id: str
    configuration_id: str
    frequency: str
    time_of_day: str
    day_of_week: int | None
    day_of_month: int | None
    is_active: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime


class ScheduleToggle(BaseModel):
    """Request to toggle schedule active state."""
    
    is_active: bool = Field(..., description="Whether schedule is active")


class BackupInfoModel(BaseModel):
    """Backup information for a drill."""
    
    id: str = Field(..., description="Backup ID")
    created_at: datetime = Field(..., description="When backup was created")
    size_bytes: int = Field(..., ge=0, description="Backup size")
    backup_type: str = Field(..., description="Type of backup")
    tables_included: list[str] | None = Field(None, description="Tables in backup")


class DrillStart(BaseModel):
    """Request to start a drill."""
    
    configuration_id: str = Field(..., description="Configuration ID")
    executed_by: str | None = Field(None, description="User executing the drill")
    notes: str | None = Field(None, description="Optional notes")
    backup_info: BackupInfoModel | None = Field(None, description="Backup to use")


class StepResponse(BaseModel):
    """Response containing drill step data."""
    
    id: str
    name: str
    description: str
    order: int
    status: str
    duration_ms: int | None
    output: dict[str, Any] | None
    error_message: str | None


class ExecutionResponse(BaseModel):
    """Response containing drill execution data."""
    
    id: str
    configuration_id: str
    configuration_name: str
    drill_type: str
    recovery_target: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    rpo_target_minutes: int
    rto_target_minutes: int
    rpo_actual_minutes: float | None
    rto_actual_minutes: float | None
    rpo_compliant: bool | None
    rto_compliant: bool | None
    data_verified: bool | None
    executed_by: str | None
    steps: list[StepResponse]


class StepExecute(BaseModel):
    """Request to execute a drill step."""
    
    success: bool = Field(..., description="Whether step succeeded")
    output: dict[str, Any] | None = Field(None, description="Step output data")
    error_message: str | None = Field(None, description="Error message if failed")


class DrillComplete(BaseModel):
    """Request to complete a drill."""
    
    data_verified: bool = Field(..., description="Whether data was verified")
    verification_errors: list[str] | None = Field(None, description="Verification errors")


class DrillFail(BaseModel):
    """Request to fail a drill."""
    
    error_message: str = Field(..., description="Error message")


class DrillResultResponse(BaseModel):
    """Response containing drill result."""
    
    execution_id: str
    configuration_name: str
    drill_type: str
    recovery_target: str
    status: str
    rpo_target_minutes: int
    rpo_actual_minutes: float
    rpo_compliance: str
    rto_target_minutes: int
    rto_actual_minutes: float
    rto_compliance: str
    data_integrity_verified: bool
    total_steps: int
    completed_steps: int
    failed_steps: int
    total_duration_minutes: float
    executed_at: str
    executed_by: str | None


class DrillSummary(BaseModel):
    """Summary of a drill for compliance report."""
    
    execution_id: str
    configuration_name: str
    drill_type: str
    status: str
    started_at: datetime
    rpo_compliant: bool | None
    rto_compliant: bool | None


class ComplianceReportResponse(BaseModel):
    """Response containing compliance report."""
    
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_drills: int
    successful_drills: int
    failed_drills: int
    rpo_compliance_rate: float
    rto_compliance_rate: float
    overall_compliance: str
    drill_frequency_met: bool
    average_rpo_minutes: float
    average_rto_minutes: float
    worst_rpo_minutes: float
    worst_rto_minutes: float
    recommendations: list[str]
    drills: list[DrillSummary]


# ===== Helper Functions =====


def _serialize_rpo_target(target) -> dict:
    """Serialize RPO target to dict."""
    return {
        "target_name": target.target_name,
        "recovery_target": target.recovery_target.value,
        "max_data_loss_minutes": target.max_data_loss_minutes,
        "description": target.description,
    }


def _serialize_rto_target(target) -> dict:
    """Serialize RTO target to dict."""
    return {
        "target_name": target.target_name,
        "recovery_target": target.recovery_target.value,
        "max_recovery_minutes": target.max_recovery_minutes,
        "description": target.description,
    }


def _serialize_configuration(config) -> dict:
    """Serialize configuration to dict."""
    return {
        "id": config.id,
        "name": config.name,
        "description": config.description,
        "drill_type": config.drill_type.value,
        "recovery_target": config.recovery_target.value,
        "rpo_target_minutes": config.rpo_target_minutes,
        "rto_target_minutes": config.rto_target_minutes,
        "notify_on_failure": config.notify_on_failure,
        "notify_on_success": config.notify_on_success,
        "notification_emails": config.notification_emails,
        "created_at": config.created_at,
    }


def _serialize_schedule(schedule) -> dict:
    """Serialize schedule to dict."""
    return {
        "id": schedule.id,
        "configuration_id": schedule.configuration_id,
        "frequency": schedule.frequency,
        "time_of_day": schedule.time_of_day,
        "day_of_week": schedule.day_of_week,
        "day_of_month": schedule.day_of_month,
        "is_active": schedule.is_active,
        "next_run_at": schedule.next_run_at,
        "last_run_at": schedule.last_run_at,
        "created_at": schedule.created_at,
    }


def _serialize_step(step) -> dict:
    """Serialize step to dict."""
    return {
        "id": step.id,
        "name": step.name,
        "description": step.description,
        "order": step.order,
        "status": step.status,
        "duration_ms": step.duration_ms,
        "output": step.output,
        "error_message": step.error_message,
    }


def _serialize_execution(execution) -> dict:
    """Serialize execution to dict."""
    return {
        "id": execution.id,
        "configuration_id": execution.configuration_id,
        "configuration_name": execution.configuration_name,
        "drill_type": execution.drill_type.value,
        "recovery_target": execution.recovery_target.value,
        "status": execution.status.value,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "rpo_target_minutes": execution.rpo_target_minutes,
        "rto_target_minutes": execution.rto_target_minutes,
        "rpo_actual_minutes": execution.rpo_actual_minutes,
        "rto_actual_minutes": execution.rto_actual_minutes,
        "rpo_compliant": execution.rpo_compliant,
        "rto_compliant": execution.rto_compliant,
        "data_verified": execution.data_verified,
        "executed_by": execution.executed_by,
        "steps": [_serialize_step(s) for s in execution.steps],
    }


def _serialize_result(result) -> dict:
    """Serialize drill result to dict."""
    return {
        "execution_id": result.execution_id,
        "configuration_name": result.configuration_name,
        "drill_type": result.drill_type,
        "recovery_target": result.recovery_target,
        "status": result.status,
        "rpo_target_minutes": result.rpo_target_minutes,
        "rpo_actual_minutes": result.rpo_actual_minutes,
        "rpo_compliance": result.rpo_compliance,
        "rto_target_minutes": result.rto_target_minutes,
        "rto_actual_minutes": result.rto_actual_minutes,
        "rto_compliance": result.rto_compliance,
        "data_integrity_verified": result.data_integrity_verified,
        "total_steps": result.total_steps,
        "completed_steps": result.completed_steps,
        "failed_steps": result.failed_steps,
        "total_duration_minutes": result.total_duration_minutes,
        "executed_at": result.executed_at,
        "executed_by": result.executed_by,
    }


def _serialize_compliance_report(report) -> dict:
    """Serialize compliance report to dict."""
    return {
        "report_id": report.report_id,
        "generated_at": report.generated_at,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "total_drills": report.total_drills,
        "successful_drills": report.successful_drills,
        "failed_drills": report.failed_drills,
        "rpo_compliance_rate": report.rpo_compliance_rate,
        "rto_compliance_rate": report.rto_compliance_rate,
        "overall_compliance": report.overall_compliance.value,
        "drill_frequency_met": report.drill_frequency_met,
        "average_rpo_minutes": report.average_rpo_minutes,
        "average_rto_minutes": report.average_rto_minutes,
        "worst_rpo_minutes": report.worst_rpo_minutes,
        "worst_rto_minutes": report.worst_rto_minutes,
        "recommendations": report.recommendations,
        "drills": [
            {
                "execution_id": d.execution_id,
                "configuration_name": d.configuration_name,
                "drill_type": d.drill_type,
                "status": d.status,
                "started_at": d.executed_at,
                "rpo_compliant": d.rpo_compliance == "compliant",
                "rto_compliant": d.rto_compliance == "compliant",
            }
            for d in report.drills
        ],
    }


def _parse_recovery_target(value: str) -> RecoveryTarget:
    """Parse recovery target string to enum."""
    try:
        return RecoveryTarget(value)
    except ValueError:
        valid = [rt.value for rt in RecoveryTarget]
        raise HTTPException(
            status_code=400,
            detail={"message": f"Invalid recovery target. Valid values: {valid}"},
        )


def _parse_drill_type(value: str) -> DrillType:
    """Parse drill type string to enum."""
    try:
        return DrillType(value)
    except ValueError:
        valid = [dt.value for dt in DrillType]
        raise HTTPException(
            status_code=400,
            detail={"message": f"Invalid drill type. Valid values: {valid}"},
        )


# ===== RPO/RTO Target Endpoints =====


@router.get("/targets/rpo")
async def get_rpo_targets() -> list[RPOTargetResponse]:
    """Get all RPO targets."""
    service = get_dr_drill_service()
    targets = service.get_rpo_targets()
    return [RPOTargetResponse(**_serialize_rpo_target(t)) for t in targets]


@router.post("/targets/rpo", status_code=201)
async def create_rpo_target(request: RPOTargetCreate) -> RPOTargetResponse:
    """Create or update an RPO target."""
    service = get_dr_drill_service()
    try:
        target = service.set_rpo_target(
            target_name=request.target_name,
            recovery_target=_parse_recovery_target(request.recovery_target),
            max_data_loss_minutes=request.max_data_loss_minutes,
            description=request.description or "",
        )
        return RPOTargetResponse(**_serialize_rpo_target(target))
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


@router.get("/targets/rto")
async def get_rto_targets() -> list[RTOTargetResponse]:
    """Get all RTO targets."""
    service = get_dr_drill_service()
    targets = service.get_rto_targets()
    return [RTOTargetResponse(**_serialize_rto_target(t)) for t in targets]


@router.post("/targets/rto", status_code=201)
async def create_rto_target(request: RTOTargetCreate) -> RTOTargetResponse:
    """Create or update an RTO target."""
    service = get_dr_drill_service()
    try:
        target = service.set_rto_target(
            target_name=request.target_name,
            recovery_target=_parse_recovery_target(request.recovery_target),
            max_recovery_minutes=request.max_recovery_minutes,
            description=request.description or "",
        )
        return RTOTargetResponse(**_serialize_rto_target(target))
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


# ===== Configuration Endpoints =====


@router.post("/configurations", status_code=201)
async def create_configuration(request: ConfigurationCreate) -> ConfigurationResponse:
    """Create a drill configuration."""
    service = get_dr_drill_service()
    config = service.create_configuration(
        name=request.name,
        description=request.description,
        drill_type=_parse_drill_type(request.drill_type),
        recovery_target=_parse_recovery_target(request.recovery_target),
        rpo_target_minutes=request.rpo_target_minutes,
        rto_target_minutes=request.rto_target_minutes,
        notify_on_failure=request.notify_on_failure,
        notify_on_success=request.notify_on_success,
        notification_emails=request.notification_emails,
    )
    return ConfigurationResponse(**_serialize_configuration(config))


@router.get("/configurations")
async def list_configurations() -> list[ConfigurationResponse]:
    """List all drill configurations."""
    service = get_dr_drill_service()
    configs = service.list_configurations()
    return [ConfigurationResponse(**_serialize_configuration(c)) for c in configs]


@router.get("/configurations/{configuration_id}")
async def get_configuration(configuration_id: str) -> ConfigurationResponse:
    """Get a drill configuration by ID."""
    service = get_dr_drill_service()
    config = service.get_configuration(configuration_id)
    if not config:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Configuration {configuration_id} not found"},
        )
    return ConfigurationResponse(**_serialize_configuration(config))


@router.delete("/configurations/{configuration_id}", status_code=204)
async def delete_configuration(configuration_id: str) -> None:
    """Delete a drill configuration."""
    service = get_dr_drill_service()
    deleted = service.delete_configuration(configuration_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Configuration {configuration_id} not found"},
        )


# ===== Schedule Endpoints =====


@router.post("/schedules", status_code=201)
async def create_schedule(request: ScheduleCreate) -> ScheduleResponse:
    """Create a drill schedule."""
    service = get_dr_drill_service()
    try:
        schedule = service.create_schedule(
            configuration_id=request.configuration_id,
            frequency=request.frequency,
            time_of_day=request.time_of_day,
            day_of_week=request.day_of_week,
            day_of_month=request.day_of_month,
        )
        return ScheduleResponse(**_serialize_schedule(schedule))
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


@router.get("/schedules")
async def list_schedules() -> list[ScheduleResponse]:
    """List all drill schedules."""
    service = get_dr_drill_service()
    schedules = service.list_schedules()
    return [ScheduleResponse(**_serialize_schedule(s)) for s in schedules]


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str) -> ScheduleResponse:
    """Get a schedule by ID."""
    service = get_dr_drill_service()
    schedule = service.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Schedule {schedule_id} not found"},
        )
    return ScheduleResponse(**_serialize_schedule(schedule))


@router.patch("/schedules/{schedule_id}")
async def toggle_schedule(schedule_id: str, request: ScheduleToggle) -> ScheduleResponse:
    """Toggle a schedule's active state."""
    service = get_dr_drill_service()
    try:
        schedule = service.toggle_schedule(schedule_id, request.is_active)
        return ScheduleResponse(**_serialize_schedule(schedule))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str) -> None:
    """Delete a schedule."""
    service = get_dr_drill_service()
    deleted = service.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Schedule {schedule_id} not found"},
        )


# ===== Drill Execution Endpoints =====


@router.post("/executions", status_code=201)
async def start_drill(request: DrillStart) -> ExecutionResponse:
    """Start a disaster recovery drill."""
    service = get_dr_drill_service()
    
    backup_info = None
    if request.backup_info:
        backup_info = BackupInfo(
            id=request.backup_info.id,
            created_at=request.backup_info.created_at,
            size_bytes=request.backup_info.size_bytes,
            backup_type=request.backup_info.backup_type,
            tables_included=request.backup_info.tables_included or [],
        )
    
    try:
        execution = service.start_drill(
            configuration_id=request.configuration_id,
            executed_by=request.executed_by or "",
            notes=request.notes or "",
            backup_info=backup_info,
        )
        return ExecutionResponse(**_serialize_execution(execution))
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


@router.get("/executions")
async def list_executions(
    configuration_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[ExecutionResponse]:
    """List drill executions."""
    service = get_dr_drill_service()
    
    status_enum = None
    if status:
        try:
            status_enum = DrillStatus(status)
        except ValueError:
            valid = [s.value for s in DrillStatus]
            raise HTTPException(
                status_code=400,
                detail={"message": f"Invalid status. Valid values: {valid}"},
            )
    
    executions = service.list_executions(
        configuration_id=configuration_id,
        status=status_enum,
        limit=limit,
    )
    return [ExecutionResponse(**_serialize_execution(e)) for e in executions]


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str) -> ExecutionResponse:
    """Get a drill execution by ID."""
    service = get_dr_drill_service()
    execution = service.get_execution(execution_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Execution {execution_id} not found"},
        )
    return ExecutionResponse(**_serialize_execution(execution))


@router.post("/executions/{execution_id}/steps/{step_id}/execute")
async def execute_step(
    execution_id: str,
    step_id: str,
    request: StepExecute,
) -> StepResponse:
    """Execute a drill step."""
    service = get_dr_drill_service()
    try:
        step = service.execute_step(
            execution_id=execution_id,
            step_id=step_id,
            success=request.success,
            output=request.output,
            error_message=request.error_message or "",
        )
        return StepResponse(**_serialize_step(step))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})


@router.post("/executions/{execution_id}/complete")
async def complete_drill(execution_id: str, request: DrillComplete) -> ExecutionResponse:
    """Complete a drill."""
    service = get_dr_drill_service()
    try:
        execution = service.complete_drill(
            execution_id=execution_id,
            data_verified=request.data_verified,
            verification_errors=request.verification_errors,
        )
        return ExecutionResponse(**_serialize_execution(execution))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})


@router.post("/executions/{execution_id}/fail")
async def fail_drill(execution_id: str, request: DrillFail) -> ExecutionResponse:
    """Mark a drill as failed."""
    service = get_dr_drill_service()
    try:
        execution = service.fail_drill(
            execution_id=execution_id,
            error_message=request.error_message,
        )
        return ExecutionResponse(**_serialize_execution(execution))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})


@router.post("/executions/{execution_id}/cancel")
async def cancel_drill(execution_id: str) -> ExecutionResponse:
    """Cancel a drill."""
    service = get_dr_drill_service()
    try:
        execution = service.cancel_drill(execution_id)
        return ExecutionResponse(**_serialize_execution(execution))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})


# ===== Results and Reporting Endpoints =====


@router.get("/executions/{execution_id}/result")
async def get_drill_result(execution_id: str) -> DrillResultResponse:
    """Get the result of a drill execution."""
    service = get_dr_drill_service()
    try:
        result = service.get_drill_result(execution_id)
        serialized = _serialize_result(result)
        return DrillResultResponse(**serialized)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": str(e)})


@router.get("/compliance-report")
async def get_compliance_report(
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> ComplianceReportResponse:
    """Generate a compliance report for DR drills."""
    service = get_dr_drill_service()
    report = service.generate_compliance_report(
        period_start=period_start,
        period_end=period_end,
    )
    return ComplianceReportResponse(**_serialize_compliance_report(report))


# ===== Recovery Target Types Endpoint =====


@router.get("/recovery-targets")
async def list_recovery_targets() -> list[str]:
    """List all available recovery target types."""
    return [rt.value for rt in RecoveryTarget]


@router.get("/drill-types")
async def list_drill_types() -> list[str]:
    """List all available drill types."""
    return [dt.value for dt in DrillType]


@router.get("/drill-statuses")
async def list_drill_statuses() -> list[str]:
    """List all available drill statuses."""
    return [ds.value for ds in DrillStatus]


@router.get("/compliance-levels")
async def list_compliance_levels() -> list[str]:
    """List all available compliance levels."""
    return [cl.value for cl in ComplianceLevel]


# ===== Maintenance Endpoints =====


@router.delete("/data", status_code=204)
async def clear_all_data() -> None:
    """Clear all DR drill data. Use with caution."""
    service = get_dr_drill_service()
    service.clear_all_data()


@router.post("/reset", status_code=204)
async def reset_service() -> None:
    """Reset the DR drill service. Use with caution."""
    reset_dr_drill_service()

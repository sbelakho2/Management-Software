"""
Disaster Recovery Drill System.

Provides comprehensive disaster recovery testing capabilities:
- Automated restore rehearsals
- RPO (Recovery Point Objective) verification
- RTO (Recovery Time Objective) verification
- Drill scheduling and execution
- Recovery metrics tracking
- Compliance reporting
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class DrillType(str, Enum):
    """Types of disaster recovery drills."""
    
    FULL_RESTORE = "full_restore"  # Complete database restore
    PARTIAL_RESTORE = "partial_restore"  # Restore specific tables/data
    POINT_IN_TIME = "point_in_time"  # Restore to specific timestamp
    FAILOVER = "failover"  # Switch to standby system
    CONFIGURATION_RESTORE = "configuration_restore"  # Restore configs only
    APPLICATION_RESTART = "application_restart"  # Cold start testing


class DrillStatus(str, Enum):
    """Status of a disaster recovery drill."""
    
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryTarget(str, Enum):
    """What is being recovered."""
    
    DATABASE = "database"
    FILE_STORAGE = "file_storage"
    CONFIGURATION = "configuration"
    APPLICATION_STATE = "application_state"
    CACHE = "cache"
    FULL_SYSTEM = "full_system"


class ComplianceLevel(str, Enum):
    """Compliance level for RPO/RTO."""
    
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"


@dataclass
class RPOTarget:
    """Recovery Point Objective configuration."""
    
    target_name: str
    recovery_target: RecoveryTarget
    max_data_loss_minutes: int  # Maximum acceptable data loss
    description: str = ""


@dataclass
class RTOTarget:
    """Recovery Time Objective configuration."""
    
    target_name: str
    recovery_target: RecoveryTarget
    max_recovery_minutes: int  # Maximum acceptable recovery time
    description: str = ""


@dataclass
class BackupInfo:
    """Information about a backup used for restore."""
    
    id: str
    created_at: datetime
    size_bytes: int
    backup_type: str  # "full", "incremental", "differential"
    tables_included: list[str] = field(default_factory=list)
    is_encrypted: bool = True
    is_compressed: bool = True
    storage_location: str = ""


@dataclass
class DrillStep:
    """A single step in a disaster recovery drill."""
    
    id: str
    name: str
    description: str
    order: int
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    error_message: str = ""
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class DrillConfiguration:
    """Configuration for a disaster recovery drill."""
    
    id: str
    name: str
    description: str
    drill_type: DrillType
    recovery_target: RecoveryTarget
    rpo_target_minutes: int  # Max acceptable data loss
    rto_target_minutes: int  # Max acceptable recovery time
    is_automated: bool = True
    notify_on_failure: bool = True
    notify_on_success: bool = False
    notification_emails: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DrillExecution:
    """An execution of a disaster recovery drill."""
    
    id: str
    configuration_id: str
    configuration_name: str
    drill_type: DrillType
    recovery_target: RecoveryTarget
    status: DrillStatus
    backup_used: BackupInfo | None = None
    steps: list[DrillStep] = field(default_factory=list)
    
    # Timing
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # RPO/RTO measurement
    rpo_target_minutes: int = 15
    rpo_actual_minutes: float = 0.0
    rpo_compliant: bool = False
    
    rto_target_minutes: int = 30
    rto_actual_minutes: float = 0.0
    rto_compliant: bool = False
    
    # Results
    data_verified: bool = False
    verification_errors: list[str] = field(default_factory=list)
    error_message: str = ""
    
    # Audit
    executed_by: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DrillSchedule:
    """Schedule for recurring disaster recovery drills."""
    
    id: str
    configuration_id: str
    frequency: str  # "daily", "weekly", "monthly", "quarterly"
    day_of_week: int | None = None  # 0-6 for weekly
    day_of_month: int | None = None  # 1-31 for monthly
    time_of_day: str = "02:00"  # HH:MM format
    is_active: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DrillResult:
    """Result summary of a drill execution."""
    
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
    executed_by: str


@dataclass
class ComplianceReport:
    """Compliance report for disaster recovery."""
    
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_drills: int
    successful_drills: int
    failed_drills: int
    rpo_compliance_rate: float
    rto_compliance_rate: float
    overall_compliance: ComplianceLevel
    drill_frequency_met: bool
    average_rpo_minutes: float
    average_rto_minutes: float
    worst_rpo_minutes: float
    worst_rto_minutes: float
    recommendations: list[str] = field(default_factory=list)
    drills: list[DrillResult] = field(default_factory=list)


class DisasterRecoveryDrillService:
    """
    Service for disaster recovery drill management.
    
    Provides:
    - Drill configuration and scheduling
    - Automated restore rehearsals
    - RPO/RTO verification
    - Compliance reporting
    """
    
    def __init__(self) -> None:
        """Initialize disaster recovery drill service."""
        self._configurations: dict[str, DrillConfiguration] = {}
        self._executions: dict[str, DrillExecution] = {}
        self._schedules: dict[str, DrillSchedule] = {}
        self._rpo_targets: dict[str, RPOTarget] = {}
        self._rto_targets: dict[str, RTOTarget] = {}
        
        # Default RPO/RTO targets
        self._init_default_targets()
    
    def _init_default_targets(self) -> None:
        """Initialize default RPO/RTO targets."""
        default_rpo = [
            RPOTarget(
                target_name="database_critical",
                recovery_target=RecoveryTarget.DATABASE,
                max_data_loss_minutes=15,
                description="Critical database data - 15 minute RPO",
            ),
            RPOTarget(
                target_name="file_storage",
                recovery_target=RecoveryTarget.FILE_STORAGE,
                max_data_loss_minutes=60,
                description="File storage - 1 hour RPO",
            ),
            RPOTarget(
                target_name="configuration",
                recovery_target=RecoveryTarget.CONFIGURATION,
                max_data_loss_minutes=1440,  # 24 hours
                description="Configuration - 24 hour RPO",
            ),
        ]
        
        default_rto = [
            RTOTarget(
                target_name="database_critical",
                recovery_target=RecoveryTarget.DATABASE,
                max_recovery_minutes=30,
                description="Critical database - 30 minute RTO",
            ),
            RTOTarget(
                target_name="file_storage",
                recovery_target=RecoveryTarget.FILE_STORAGE,
                max_recovery_minutes=120,
                description="File storage - 2 hour RTO",
            ),
            RTOTarget(
                target_name="full_system",
                recovery_target=RecoveryTarget.FULL_SYSTEM,
                max_recovery_minutes=240,
                description="Full system - 4 hour RTO",
            ),
        ]
        
        for rpo in default_rpo:
            self._rpo_targets[rpo.target_name] = rpo
        
        for rto in default_rto:
            self._rto_targets[rto.target_name] = rto
    
    # ===== Target Management =====
    
    def set_rpo_target(
        self,
        target_name: str,
        recovery_target: RecoveryTarget,
        max_data_loss_minutes: int,
        description: str = "",
    ) -> RPOTarget:
        """Set or update an RPO target."""
        if max_data_loss_minutes < 1:
            raise ValueError("max_data_loss_minutes must be at least 1")
        
        target = RPOTarget(
            target_name=target_name,
            recovery_target=recovery_target,
            max_data_loss_minutes=max_data_loss_minutes,
            description=description,
        )
        self._rpo_targets[target_name] = target
        return target
    
    def set_rto_target(
        self,
        target_name: str,
        recovery_target: RecoveryTarget,
        max_recovery_minutes: int,
        description: str = "",
    ) -> RTOTarget:
        """Set or update an RTO target."""
        if max_recovery_minutes < 1:
            raise ValueError("max_recovery_minutes must be at least 1")
        
        target = RTOTarget(
            target_name=target_name,
            recovery_target=recovery_target,
            max_recovery_minutes=max_recovery_minutes,
            description=description,
        )
        self._rto_targets[target_name] = target
        return target
    
    def get_rpo_targets(self) -> list[RPOTarget]:
        """Get all RPO targets."""
        return list(self._rpo_targets.values())
    
    def get_rto_targets(self) -> list[RTOTarget]:
        """Get all RTO targets."""
        return list(self._rto_targets.values())
    
    # ===== Configuration Management =====
    
    def create_configuration(
        self,
        name: str,
        description: str,
        drill_type: DrillType,
        recovery_target: RecoveryTarget,
        rpo_target_minutes: int = 15,
        rto_target_minutes: int = 30,
        is_automated: bool = True,
        notify_on_failure: bool = True,
        notify_on_success: bool = False,
        notification_emails: list[str] | None = None,
    ) -> DrillConfiguration:
        """Create a new drill configuration."""
        config = DrillConfiguration(
            id=str(uuid4()),
            name=name,
            description=description,
            drill_type=drill_type,
            recovery_target=recovery_target,
            rpo_target_minutes=rpo_target_minutes,
            rto_target_minutes=rto_target_minutes,
            is_automated=is_automated,
            notify_on_failure=notify_on_failure,
            notify_on_success=notify_on_success,
            notification_emails=notification_emails or [],
        )
        self._configurations[config.id] = config
        return config
    
    def get_configuration(self, config_id: str) -> DrillConfiguration | None:
        """Get a drill configuration by ID."""
        return self._configurations.get(config_id)
    
    def list_configurations(self) -> list[DrillConfiguration]:
        """List all drill configurations."""
        return list(self._configurations.values())
    
    def delete_configuration(self, config_id: str) -> bool:
        """Delete a drill configuration."""
        if config_id in self._configurations:
            del self._configurations[config_id]
            # Also delete associated schedules
            schedules_to_delete = [
                s.id for s in self._schedules.values()
                if s.configuration_id == config_id
            ]
            for schedule_id in schedules_to_delete:
                del self._schedules[schedule_id]
            return True
        return False
    
    # ===== Schedule Management =====
    
    def create_schedule(
        self,
        configuration_id: str,
        frequency: str,
        day_of_week: int | None = None,
        day_of_month: int | None = None,
        time_of_day: str = "02:00",
    ) -> DrillSchedule:
        """Create a drill schedule."""
        if configuration_id not in self._configurations:
            raise ValueError(f"Configuration {configuration_id} not found")
        
        valid_frequencies = ["daily", "weekly", "monthly", "quarterly"]
        if frequency not in valid_frequencies:
            raise ValueError(f"frequency must be one of: {valid_frequencies}")
        
        schedule = DrillSchedule(
            id=str(uuid4()),
            configuration_id=configuration_id,
            frequency=frequency,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            time_of_day=time_of_day,
        )
        
        # Calculate next run
        schedule.next_run_at = self._calculate_next_run(schedule)
        
        self._schedules[schedule.id] = schedule
        return schedule
    
    def _calculate_next_run(self, schedule: DrillSchedule) -> datetime:
        """Calculate the next run time for a schedule."""
        now = datetime.now(timezone.utc)
        hour, minute = map(int, schedule.time_of_day.split(":"))
        
        if schedule.frequency == "daily":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        elif schedule.frequency == "weekly":
            days_ahead = (schedule.day_of_week or 0) - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif schedule.frequency == "monthly":
            day = schedule.day_of_month or 1
            next_run = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                if now.month == 12:
                    next_run = next_run.replace(year=now.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=now.month + 1)
        else:  # quarterly
            month = ((now.month - 1) // 3 + 1) * 3 + 1
            year = now.year
            if month > 12:
                month = 1
                year += 1
            next_run = datetime(year, month, 1, hour, minute, 0, tzinfo=timezone.utc)
        
        return next_run
    
    def get_schedule(self, schedule_id: str) -> DrillSchedule | None:
        """Get a drill schedule by ID."""
        return self._schedules.get(schedule_id)
    
    def list_schedules(self) -> list[DrillSchedule]:
        """List all drill schedules."""
        return list(self._schedules.values())
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a drill schedule."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False
    
    def toggle_schedule(self, schedule_id: str, is_active: bool) -> DrillSchedule:
        """Enable or disable a drill schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")
        
        schedule.is_active = is_active
        return schedule
    
    # ===== Drill Execution =====
    
    def start_drill(
        self,
        configuration_id: str,
        executed_by: str = "system",
        notes: str = "",
        backup_info: BackupInfo | None = None,
    ) -> DrillExecution:
        """Start a disaster recovery drill."""
        config = self._configurations.get(configuration_id)
        if not config:
            raise ValueError(f"Configuration {configuration_id} not found")
        
        # Create simulated backup if not provided
        if backup_info is None:
            backup_info = self._create_simulated_backup(config)
        
        execution = DrillExecution(
            id=str(uuid4()),
            configuration_id=configuration_id,
            configuration_name=config.name,
            drill_type=config.drill_type,
            recovery_target=config.recovery_target,
            status=DrillStatus.IN_PROGRESS,
            backup_used=backup_info,
            rpo_target_minutes=config.rpo_target_minutes,
            rto_target_minutes=config.rto_target_minutes,
            started_at=datetime.now(timezone.utc),
            executed_by=executed_by,
            notes=notes,
        )
        
        # Create drill steps based on drill type
        execution.steps = self._create_drill_steps(config.drill_type)
        
        self._executions[execution.id] = execution
        return execution
    
    def _create_simulated_backup(self, config: DrillConfiguration) -> BackupInfo:
        """Create a simulated backup for testing."""
        now = datetime.now(timezone.utc)
        # Simulate backup from 5-10 minutes ago
        backup_age_minutes = 5 + (hash(config.id) % 6)
        
        return BackupInfo(
            id=str(uuid4()),
            created_at=now - timedelta(minutes=backup_age_minutes),
            size_bytes=1024 * 1024 * 100,  # 100 MB
            backup_type="full",
            tables_included=["users", "accounts", "quotes", "rfqs", "audit_logs"],
            storage_location="s3://backups/db/latest.dump",
        )
    
    def _create_drill_steps(self, drill_type: DrillType) -> list[DrillStep]:
        """Create the steps for a drill based on type."""
        base_steps = [
            DrillStep(
                id=str(uuid4()),
                name="verify_backup",
                description="Verify backup integrity and availability",
                order=1,
            ),
            DrillStep(
                id=str(uuid4()),
                name="prepare_environment",
                description="Prepare recovery environment",
                order=2,
            ),
        ]
        
        if drill_type == DrillType.FULL_RESTORE:
            base_steps.extend([
                DrillStep(
                    id=str(uuid4()),
                    name="stop_services",
                    description="Stop dependent services",
                    order=3,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="restore_database",
                    description="Restore database from backup",
                    order=4,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="restore_files",
                    description="Restore file storage",
                    order=5,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="start_services",
                    description="Start services",
                    order=6,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="verify_data",
                    description="Verify data integrity",
                    order=7,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="run_health_checks",
                    description="Run application health checks",
                    order=8,
                ),
            ])
        elif drill_type == DrillType.PARTIAL_RESTORE:
            base_steps.extend([
                DrillStep(
                    id=str(uuid4()),
                    name="identify_tables",
                    description="Identify tables to restore",
                    order=3,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="restore_tables",
                    description="Restore selected tables",
                    order=4,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="verify_data",
                    description="Verify restored data",
                    order=5,
                ),
            ])
        elif drill_type == DrillType.POINT_IN_TIME:
            base_steps.extend([
                DrillStep(
                    id=str(uuid4()),
                    name="identify_point",
                    description="Identify recovery point in time",
                    order=3,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="apply_wal",
                    description="Apply WAL logs to target point",
                    order=4,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="verify_state",
                    description="Verify database state at point",
                    order=5,
                ),
            ])
        elif drill_type == DrillType.FAILOVER:
            base_steps.extend([
                DrillStep(
                    id=str(uuid4()),
                    name="check_standby",
                    description="Check standby system health",
                    order=3,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="promote_standby",
                    description="Promote standby to primary",
                    order=4,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="redirect_traffic",
                    description="Redirect traffic to new primary",
                    order=5,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="verify_operation",
                    description="Verify system operation",
                    order=6,
                ),
            ])
        elif drill_type == DrillType.CONFIGURATION_RESTORE:
            base_steps.extend([
                DrillStep(
                    id=str(uuid4()),
                    name="backup_current",
                    description="Backup current configuration",
                    order=3,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="restore_config",
                    description="Restore configuration from backup",
                    order=4,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="validate_config",
                    description="Validate restored configuration",
                    order=5,
                ),
            ])
        else:  # APPLICATION_RESTART
            base_steps.extend([
                DrillStep(
                    id=str(uuid4()),
                    name="stop_application",
                    description="Stop application services",
                    order=3,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="clear_caches",
                    description="Clear application caches",
                    order=4,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="start_application",
                    description="Start application services",
                    order=5,
                ),
                DrillStep(
                    id=str(uuid4()),
                    name="verify_startup",
                    description="Verify successful startup",
                    order=6,
                ),
            ])
        
        return base_steps
    
    def execute_step(
        self,
        execution_id: str,
        step_id: str,
        success: bool = True,
        output: dict[str, Any] | None = None,
        error_message: str = "",
    ) -> DrillStep:
        """Execute a drill step (simulate execution)."""
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        step = None
        for s in execution.steps:
            if s.id == step_id:
                step = s
                break
        
        if not step:
            raise ValueError(f"Step {step_id} not found in execution")
        
        step.started_at = datetime.now(timezone.utc)
        
        # Simulate execution time (50-500ms)
        step.duration_ms = 50 + (hash(step_id) % 450)
        
        step.completed_at = datetime.now(timezone.utc)
        step.status = "completed" if success else "failed"
        step.output = output or {"simulated": True}
        step.error_message = error_message
        
        return step
    
    def complete_drill(
        self,
        execution_id: str,
        data_verified: bool = True,
        verification_errors: list[str] | None = None,
    ) -> DrillExecution:
        """Complete a drill execution and calculate results."""
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution.completed_at = datetime.now(timezone.utc)
        execution.data_verified = data_verified
        execution.verification_errors = verification_errors or []
        
        # Calculate RTO (time to recover)
        if execution.started_at and execution.completed_at:
            rto_delta = execution.completed_at - execution.started_at
            execution.rto_actual_minutes = rto_delta.total_seconds() / 60
            execution.rto_compliant = (
                execution.rto_actual_minutes <= execution.rto_target_minutes
            )
        
        # Calculate RPO (data loss)
        if execution.backup_used:
            now = datetime.now(timezone.utc)
            rpo_delta = now - execution.backup_used.created_at
            execution.rpo_actual_minutes = rpo_delta.total_seconds() / 60
            execution.rpo_compliant = (
                execution.rpo_actual_minutes <= execution.rpo_target_minutes
            )
        
        # Determine overall status
        failed_steps = [s for s in execution.steps if s.status == "failed"]
        if failed_steps:
            execution.status = DrillStatus.FAILED
        elif not data_verified or verification_errors:
            execution.status = DrillStatus.FAILED
            execution.error_message = "Data verification failed"
        else:
            execution.status = DrillStatus.COMPLETED
        
        return execution
    
    def fail_drill(
        self,
        execution_id: str,
        error_message: str,
    ) -> DrillExecution:
        """Mark a drill as failed."""
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution.status = DrillStatus.FAILED
        execution.completed_at = datetime.now(timezone.utc)
        execution.error_message = error_message
        
        return execution
    
    def cancel_drill(self, execution_id: str) -> DrillExecution:
        """Cancel a running drill."""
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        if execution.status not in (DrillStatus.SCHEDULED, DrillStatus.IN_PROGRESS):
            raise ValueError("Can only cancel scheduled or in-progress drills")
        
        execution.status = DrillStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        
        return execution
    
    def get_execution(self, execution_id: str) -> DrillExecution | None:
        """Get a drill execution by ID."""
        return self._executions.get(execution_id)
    
    def list_executions(
        self,
        configuration_id: str | None = None,
        status: DrillStatus | None = None,
        limit: int = 50,
    ) -> list[DrillExecution]:
        """List drill executions with optional filters."""
        executions = list(self._executions.values())
        
        if configuration_id:
            executions = [
                e for e in executions
                if e.configuration_id == configuration_id
            ]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        # Sort by creation time, newest first
        executions.sort(key=lambda e: e.created_at, reverse=True)
        
        return executions[:limit]
    
    # ===== Results and Reporting =====
    
    def get_drill_result(self, execution_id: str) -> DrillResult:
        """Get a formatted result for a drill execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        completed_steps = len([s for s in execution.steps if s.status == "completed"])
        failed_steps = len([s for s in execution.steps if s.status == "failed"])
        
        if execution.started_at and execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds() / 60
        else:
            duration = 0.0
        
        return DrillResult(
            execution_id=execution.id,
            configuration_name=execution.configuration_name,
            drill_type=execution.drill_type.value,
            recovery_target=execution.recovery_target.value,
            status=execution.status.value,
            rpo_target_minutes=execution.rpo_target_minutes,
            rpo_actual_minutes=execution.rpo_actual_minutes,
            rpo_compliance="compliant" if execution.rpo_compliant else "non_compliant",
            rto_target_minutes=execution.rto_target_minutes,
            rto_actual_minutes=execution.rto_actual_minutes,
            rto_compliance="compliant" if execution.rto_compliant else "non_compliant",
            data_integrity_verified=execution.data_verified,
            total_steps=len(execution.steps),
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            total_duration_minutes=duration,
            executed_at=execution.created_at.isoformat(),
            executed_by=execution.executed_by,
        )
    
    def generate_compliance_report(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> ComplianceReport:
        """Generate a compliance report for disaster recovery."""
        now = datetime.now(timezone.utc)
        
        if period_end is None:
            period_end = now
        if period_start is None:
            period_start = now - timedelta(days=90)  # Last 90 days
        
        # Filter executions by period
        relevant_executions = [
            e for e in self._executions.values()
            if e.created_at >= period_start and e.created_at <= period_end
        ]
        
        total_drills = len(relevant_executions)
        successful = [e for e in relevant_executions if e.status == DrillStatus.COMPLETED]
        failed = [e for e in relevant_executions if e.status == DrillStatus.FAILED]
        
        # Calculate compliance rates
        rpo_compliant = [e for e in relevant_executions if e.rpo_compliant]
        rto_compliant = [e for e in relevant_executions if e.rto_compliant]
        
        rpo_rate = len(rpo_compliant) / total_drills if total_drills > 0 else 0.0
        rto_rate = len(rto_compliant) / total_drills if total_drills > 0 else 0.0
        
        # Calculate averages and worst cases
        rpo_values = [e.rpo_actual_minutes for e in relevant_executions if e.rpo_actual_minutes > 0]
        rto_values = [e.rto_actual_minutes for e in relevant_executions if e.rto_actual_minutes > 0]
        
        avg_rpo = sum(rpo_values) / len(rpo_values) if rpo_values else 0.0
        avg_rto = sum(rto_values) / len(rto_values) if rto_values else 0.0
        worst_rpo = max(rpo_values) if rpo_values else 0.0
        worst_rto = max(rto_values) if rto_values else 0.0
        
        # Determine overall compliance
        if rpo_rate >= 0.95 and rto_rate >= 0.95:
            overall = ComplianceLevel.COMPLIANT
        elif rpo_rate >= 0.80 and rto_rate >= 0.80:
            overall = ComplianceLevel.WARNING
        else:
            overall = ComplianceLevel.NON_COMPLIANT
        
        # Check drill frequency
        days_in_period = (period_end - period_start).days
        expected_monthly = days_in_period // 30
        drill_frequency_met = total_drills >= expected_monthly
        
        # Generate recommendations
        recommendations = []
        if rpo_rate < 0.95:
            recommendations.append(
                "RPO compliance is below target. Consider more frequent backups."
            )
        if rto_rate < 0.95:
            recommendations.append(
                "RTO compliance is below target. Review and optimize recovery procedures."
            )
        if worst_rpo > 60:
            recommendations.append(
                f"Worst RPO was {worst_rpo:.1f} minutes. Investigate backup gaps."
            )
        if worst_rto > 120:
            recommendations.append(
                f"Worst RTO was {worst_rto:.1f} minutes. Optimize recovery automation."
            )
        if not drill_frequency_met:
            recommendations.append(
                "Drill frequency is below target. Schedule more regular drills."
            )
        if total_drills == 0:
            recommendations.append(
                "No drills executed in this period. Immediate action required."
            )
        
        # Get drill results
        drill_results = [
            self.get_drill_result(e.id)
            for e in relevant_executions
        ]
        
        return ComplianceReport(
            report_id=str(uuid4()),
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            total_drills=total_drills,
            successful_drills=len(successful),
            failed_drills=len(failed),
            rpo_compliance_rate=rpo_rate,
            rto_compliance_rate=rto_rate,
            overall_compliance=overall,
            drill_frequency_met=drill_frequency_met,
            average_rpo_minutes=avg_rpo,
            average_rto_minutes=avg_rto,
            worst_rpo_minutes=worst_rpo,
            worst_rto_minutes=worst_rto,
            recommendations=recommendations,
            drills=drill_results,
        )
    
    def clear_all_data(self) -> None:
        """Clear all data (for testing)."""
        self._configurations.clear()
        self._executions.clear()
        self._schedules.clear()
        # Reinitialize default targets
        self._rpo_targets.clear()
        self._rto_targets.clear()
        self._init_default_targets()


# Singleton instance
_dr_drill_service: DisasterRecoveryDrillService | None = None


def get_dr_drill_service() -> DisasterRecoveryDrillService:
    """Get the singleton disaster recovery drill service instance."""
    global _dr_drill_service
    if _dr_drill_service is None:
        _dr_drill_service = DisasterRecoveryDrillService()
    return _dr_drill_service


def reset_dr_drill_service() -> None:
    """Reset the disaster recovery drill service (for testing)."""
    global _dr_drill_service
    if _dr_drill_service is not None:
        _dr_drill_service.clear_all_data()
    _dr_drill_service = None

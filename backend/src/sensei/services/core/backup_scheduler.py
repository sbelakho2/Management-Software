"""
Database Backup Scheduler Service

Automated scheduling of database backups with RPO/RTO monitoring and testing.
Provides comprehensive backup automation, verification, and disaster recovery capabilities.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
import logging
from dataclasses import dataclass, field

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from sensei.services.core.database_backup import (
    DatabaseBackupService,
    BackupStrategy,
    BackupStatus,
)

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Backup schedule types"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ScheduleStatus(str, Enum):
    """Schedule execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BackupSchedule:
    """Backup schedule configuration"""
    id: str
    name: str
    schedule_type: ScheduleType
    strategy: BackupStrategy
    enabled: bool = True
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    retention_days: int = 30
    auto_test_restore: bool = True
    test_frequency_days: int = 7
    alert_on_failure: bool = True
    last_execution: Optional[datetime] = None
    last_test: Optional[datetime] = None
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleExecution:
    """Backup schedule execution record"""
    id: str
    schedule_id: str
    execution_time: datetime
    status: ScheduleStatus
    backup_id: Optional[str] = None
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None


class BackupSchedulerService:
    """
    Automated backup scheduling and monitoring service.
    
    Features:
    - Multiple schedule types (hourly, daily, weekly, monthly, custom)
    - Automatic restore testing on schedule
    - RPO/RTO monitoring and alerting
    - Failure tracking and escalation
    - Backup verification and cleanup
    - Disaster recovery readiness reporting
    """
    
    def __init__(
        self,
        backup_service: DatabaseBackupService,
        scheduler: Optional[BackgroundScheduler] = None
    ):
        self.backup_service = backup_service
        self.scheduler = scheduler or BackgroundScheduler()
        self.schedules: Dict[str, BackupSchedule] = {}
        self.executions: List[ScheduleExecution] = []
        self._is_running = False
        
        # Initialize default schedules
        self._initialize_default_schedules()
    
    def _initialize_default_schedules(self):
        """Initialize recommended backup schedules"""
        # Full backup daily at 2 AM
        self.add_schedule(BackupSchedule(
            id="daily-full",
            name="Daily Full Backup",
            schedule_type=ScheduleType.DAILY,
            strategy=BackupStrategy.FULL,
            cron_expression="0 2 * * *",
            retention_days=30,
            auto_test_restore=True,
            test_frequency_days=7,
        ))
        
        # Incremental backup every 4 hours
        self.add_schedule(BackupSchedule(
            id="incremental-4h",
            name="4-Hour Incremental Backup",
            schedule_type=ScheduleType.CUSTOM,
            strategy=BackupStrategy.INCREMENTAL,
            interval_minutes=240,
            retention_days=7,
            auto_test_restore=False,
        ))
        
        # Differential backup every 12 hours
        self.add_schedule(BackupSchedule(
            id="differential-12h",
            name="12-Hour Differential Backup",
            schedule_type=ScheduleType.CUSTOM,
            strategy=BackupStrategy.DIFFERENTIAL,
            interval_minutes=720,
            retention_days=14,
            auto_test_restore=False,
        ))
        
        # Weekly backup for long-term retention
        self.add_schedule(BackupSchedule(
            id="weekly-archive",
            name="Weekly Archive Backup",
            schedule_type=ScheduleType.WEEKLY,
            strategy=BackupStrategy.FULL,
            cron_expression="0 3 * * 0",  # Sunday 3 AM
            retention_days=90,
            auto_test_restore=True,
            test_frequency_days=30,
        ))
    
    def start(self):
        """Start the backup scheduler"""
        if self._is_running:
            logger.warning("Backup scheduler already running")
            return
        
        for schedule in self.schedules.values():
            if schedule.enabled:
                self._register_schedule(schedule)
        
        self.scheduler.start()
        self._is_running = True
        logger.info(f"Backup scheduler started with {len(self.schedules)} schedules")
    
    def stop(self):
        """Stop the backup scheduler"""
        if not self._is_running:
            return
        
        self.scheduler.shutdown()
        self._is_running = False
        logger.info("Backup scheduler stopped")
    
    def add_schedule(self, schedule: BackupSchedule):
        """Add a backup schedule"""
        self.schedules[schedule.id] = schedule
        
        if self._is_running and schedule.enabled:
            self._register_schedule(schedule)
        
        logger.info(f"Added backup schedule: {schedule.name}")
    
    def remove_schedule(self, schedule_id: str):
        """Remove a backup schedule"""
        if schedule_id in self.schedules:
            if self._is_running:
                self.scheduler.remove_job(schedule_id)
            
            del self.schedules[schedule_id]
            logger.info(f"Removed backup schedule: {schedule_id}")
    
    def enable_schedule(self, schedule_id: str):
        """Enable a backup schedule"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        schedule.enabled = True
        
        if self._is_running:
            self._register_schedule(schedule)
    
    def disable_schedule(self, schedule_id: str):
        """Disable a backup schedule"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        schedule.enabled = False
        
        if self._is_running:
            self.scheduler.remove_job(schedule_id)
    
    def _register_schedule(self, schedule: BackupSchedule):
        """Register schedule with APScheduler"""
        if schedule.schedule_type == ScheduleType.CUSTOM and schedule.interval_minutes:
            # Interval-based schedule
            trigger = IntervalTrigger(minutes=schedule.interval_minutes)
        elif schedule.cron_expression:
            # Cron-based schedule
            trigger = CronTrigger.from_crontab(schedule.cron_expression)
        else:
            logger.error(f"Invalid schedule configuration: {schedule.id}")
            return
        
        self.scheduler.add_job(
            func=self._execute_backup,
            trigger=trigger,
            id=schedule.id,
            name=schedule.name,
            args=[schedule.id],
            replace_existing=True,
        )
    
    def _execute_backup(self, schedule_id: str):
        """Execute a scheduled backup"""
        schedule = self.schedules.get(schedule_id)
        if not schedule or not schedule.enabled:
            return
        
        execution_id = f"{schedule_id}-{datetime.now(timezone.utc).isoformat()}"
        execution = ScheduleExecution(
            id=execution_id,
            schedule_id=schedule_id,
            execution_time=datetime.now(timezone.utc),
            status=ScheduleStatus.RUNNING,
        )
        
        self.executions.append(execution)
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create backup
            logger.info(f"Starting scheduled backup: {schedule.name}")
            backup = self.backup_service.create_backup(
                strategy=schedule.strategy,
                metadata={
                    "schedule_id": schedule_id,
                    "schedule_name": schedule.name,
                    "automated": True,
                }
            )
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Update execution record
            execution.status = ScheduleStatus.COMPLETED
            execution.backup_id = backup.backup_id
            execution.duration_seconds = duration
            execution.size_bytes = backup.compressed_size_bytes
            
            # Update schedule
            schedule.last_execution = datetime.now(timezone.utc)
            schedule.consecutive_failures = 0
            
            # Test restore if scheduled
            if schedule.auto_test_restore:
                if self._should_test_restore(schedule):
                    test_result = self._test_backup_restore(backup.backup_id)
                    execution.test_result = test_result
                    schedule.last_test = datetime.now(timezone.utc)
            
            # Apply retention policy
            self._apply_retention(schedule)
            
            logger.info(
                f"Backup completed successfully: {schedule.name} "
                f"(Duration: {duration:.2f}s, Size: {backup.compressed_size_bytes / 1024 / 1024:.2f}MB)"
            )
            
        except Exception as e:
            logger.error(f"Backup failed: {schedule.name} - {str(e)}", exc_info=True)
            
            execution.status = ScheduleStatus.FAILED
            execution.error_message = str(e)
            
            schedule.consecutive_failures += 1
            
            if schedule.alert_on_failure:
                self._send_failure_alert(schedule, str(e))
    
    def _should_test_restore(self, schedule: BackupSchedule) -> bool:
        """Determine if restore test should be performed"""
        if not schedule.last_test:
            return True
        
        days_since_test = (datetime.now(timezone.utc) - schedule.last_test).days
        return days_since_test >= schedule.test_frequency_days
    
    def _test_backup_restore(self, backup_id: str) -> Dict[str, Any]:
        """Test backup restore"""
        try:
            test_result = self.backup_service.test_restore(backup_id)
            
            return {
                "success": test_result.status.value == "success",
                "rto_seconds": test_result.rto_seconds,
                "verification_passed": test_result.verification_passed,
                "test_time": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Restore test failed for backup {backup_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "test_time": datetime.now(timezone.utc).isoformat(),
            }
    
    def _apply_retention(self, schedule: BackupSchedule):
        """Apply retention policy for schedule"""
        try:
            removed_count = self.backup_service.apply_retention_policy(
                retention_days=schedule.retention_days
            )
            
            if removed_count > 0:
                logger.info(
                    f"Applied retention policy for {schedule.name}: "
                    f"Removed {removed_count} old backup(s)"
                )
        except Exception as e:
            logger.error(f"Retention policy failed: {str(e)}")
    
    def _send_failure_alert(self, schedule: BackupSchedule, error_message: str):
        """Send alert for backup failure"""
        # In production, this would integrate with notification service
        logger.critical(
            f"BACKUP FAILURE ALERT: {schedule.name} "
            f"(Consecutive failures: {schedule.consecutive_failures})\n"
            f"Error: {error_message}"
        )
    
    def get_rpo_compliance(self) -> Dict[str, Any]:
        """Check RPO compliance across all schedules"""
        rpo_status = self.backup_service.get_rpo_status()
        
        # Calculate additional metrics
        total_schedules = len(self.schedules)
        enabled_schedules = sum(1 for s in self.schedules.values() if s.enabled)
        failed_schedules = sum(
            1 for s in self.schedules.values() 
            if s.consecutive_failures > 0
        )
        
        return {
            "rpo_status": rpo_status["status"],
            "rpo_message": rpo_status["message"],
            "within_target": rpo_status["within_target"],
            "hours_since_backup": rpo_status.get("hours_since_backup"),
            "total_schedules": total_schedules,
            "enabled_schedules": enabled_schedules,
            "failed_schedules": failed_schedules,
            "last_successful_backup": rpo_status.get("last_backup"),
        }
    
    def get_rto_compliance(self) -> Dict[str, Any]:
        """Check RTO compliance from restore tests"""
        rto_status = self.backup_service.get_rto_status()
        
        # Find schedules needing tests
        schedules_needing_test = []
        for schedule in self.schedules.values():
            if schedule.auto_test_restore and self._should_test_restore(schedule):
                schedules_needing_test.append(schedule.name)
        
        return {
            "rto_status": rto_status["status"],
            "rto_message": rto_status["message"],
            "within_target": rto_status["within_target"],
            "rto_seconds": rto_status.get("rto_seconds"),
            "last_test": rto_status.get("last_test"),
            "schedules_needing_test": schedules_needing_test,
        }
    
    def get_disaster_recovery_readiness(self) -> Dict[str, Any]:
        """Comprehensive disaster recovery readiness report"""
        rpo = self.get_rpo_compliance()
        rto = self.get_rto_compliance()
        
        # Get recent executions
        recent_executions = sorted(
            self.executions,
            key=lambda e: e.execution_time,
            reverse=True
        )[:10]
        
        # Calculate success rate
        total_executions = len(self.executions)
        successful_executions = sum(
            1 for e in self.executions 
            if e.status == ScheduleStatus.COMPLETED
        )
        success_rate = (
            successful_executions / total_executions 
            if total_executions > 0 
            else 0
        ) * 100
        
        # Overall readiness score
        readiness_score = 0
        if rpo["within_target"]:
            readiness_score += 40
        if rto["within_target"]:
            readiness_score += 40
        if success_rate >= 95:
            readiness_score += 20
        
        return {
            "readiness_score": readiness_score,
            "readiness_level": self._get_readiness_level(readiness_score),
            "rpo_compliance": rpo,
            "rto_compliance": rto,
            "backup_success_rate": round(success_rate, 2),
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "recent_executions": [
                {
                    "schedule_name": self.schedules[e.schedule_id].name,
                    "execution_time": e.execution_time.isoformat(),
                    "status": e.status.value,
                    "duration_seconds": e.duration_seconds,
                }
                for e in recent_executions
            ],
            "recommendations": self._get_readiness_recommendations(readiness_score, rpo, rto),
        }
    
    def _get_readiness_level(self, score: int) -> str:
        """Get disaster recovery readiness level"""
        if score >= 90:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 50:
            return "Fair"
        else:
            return "Poor"
    
    def _get_readiness_recommendations(
        self, 
        score: int, 
        rpo: Dict[str, Any], 
        rto: Dict[str, Any]
    ) -> List[str]:
        """Get recommendations for improving readiness"""
        recommendations = []
        
        if not rpo["within_target"]:
            recommendations.append(
                "RPO target not met - increase backup frequency or check for failures"
            )
        
        if not rto["within_target"]:
            recommendations.append(
                "RTO target not met - optimize restore process or test more frequently"
            )
        
        if rpo["failed_schedules"] > 0:
            recommendations.append(
                f"Fix {rpo['failed_schedules']} failed backup schedule(s)"
            )
        
        if rto["schedules_needing_test"]:
            recommendations.append(
                f"Run restore tests for: {', '.join(rto['schedules_needing_test'][:3])}"
            )
        
        if score < 70:
            recommendations.append(
                "Consider increasing backup frequency and test frequency"
            )
        
        if not recommendations:
            recommendations.append("Disaster recovery readiness is excellent")
        
        return recommendations
    
    def force_backup(self, schedule_id: str) -> str:
        """Force immediate backup execution"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        self._execute_backup(schedule_id)
        
        # Get the most recent execution
        recent = [e for e in self.executions if e.schedule_id == schedule_id]
        if recent:
            latest = max(recent, key=lambda e: e.execution_time)
            return latest.backup_id or ""
        
        return ""
    
    def get_schedule_history(
        self, 
        schedule_id: str, 
        limit: int = 50
    ) -> List[ScheduleExecution]:
        """Get execution history for a schedule"""
        history = [
            e for e in self.executions 
            if e.schedule_id == schedule_id
        ]
        
        return sorted(
            history,
            key=lambda e: e.execution_time,
            reverse=True
        )[:limit]

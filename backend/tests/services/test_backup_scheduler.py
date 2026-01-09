"""
Tests for Database Backup Scheduler Service
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from sensei.services.backup_scheduler import (
    BackupSchedulerService,
    BackupSchedule,
    ScheduleType,
    ScheduleStatus,
    ScheduleExecution,
)
from sensei.services.database_backup import (
    BackupStrategy,
    BackupStatus,
    BackupMetadata,
    RestoreTest,
    RestoreStatus,
)


@pytest.fixture
def mock_backup_service():
    """Mock backup service"""
    service = Mock()
    
    # Mock create_backup
    backup = BackupMetadata(
        backup_id="test-backup-123",
        strategy=BackupStrategy.FULL,
        timestamp=datetime.now(timezone.utc),
        database_name="test_db",
        size_bytes=1024 * 1024 * 100,  # 100MB
        compressed_size_bytes=1024 * 1024 * 50,  # 50MB
        checksum="abc123",
        encryption_enabled=True,
        status=BackupStatus.COMPLETED,
        file_path="/backups/test-backup-123.sql.gz",
    )
    service.create_backup.return_value = backup
    
    # Mock test_restore
    test_result = RestoreTest(
        test_id="test-123",
        backup_id="test-backup-123",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(seconds=120),
        status=RestoreStatus.SUCCESS,
        rto_seconds=120.0,
        verification_passed=True,
        test_database="test_restore_db",
    )
    service.test_restore.return_value = test_result
    
    # Mock retention policy
    service.apply_retention_policy.return_value = 2
    
    # Mock status checks
    service.get_rpo_status.return_value = {
        "status": "healthy",
        "message": "Last backup 2 hours ago",
        "within_target": True,
        "hours_since_backup": 2.0,
        "last_backup": datetime.now(timezone.utc).isoformat(),
    }
    
    service.get_rto_status.return_value = {
        "status": "healthy",
        "message": "Last restore test successful",
        "within_target": True,
        "rto_seconds": 120.0,
        "last_test": datetime.now(timezone.utc).isoformat(),
    }
    
    return service


@pytest.fixture
def mock_scheduler():
    """Mock APScheduler"""
    scheduler = Mock()
    scheduler.start = Mock()
    scheduler.shutdown = Mock()
    scheduler.add_job = Mock()
    scheduler.remove_job = Mock()
    return scheduler


@pytest.fixture
def backup_scheduler_service(mock_backup_service, mock_scheduler):
    """Backup scheduler service with mocked dependencies"""
    return BackupSchedulerService(
        backup_service=mock_backup_service,
        scheduler=mock_scheduler
    )


class TestBackupSchedulerInitialization:
    """Test scheduler initialization"""
    
    def test_creates_default_schedules(self, backup_scheduler_service):
        """Should create default backup schedules"""
        assert len(backup_scheduler_service.schedules) == 4
        
        # Check daily full backup
        assert "daily-full" in backup_scheduler_service.schedules
        daily = backup_scheduler_service.schedules["daily-full"]
        assert daily.strategy == BackupStrategy.FULL
        assert daily.schedule_type == ScheduleType.DAILY
        assert daily.cron_expression == "0 2 * * *"
        
        # Check incremental backup
        assert "incremental-4h" in backup_scheduler_service.schedules
        incremental = backup_scheduler_service.schedules["incremental-4h"]
        assert incremental.strategy == BackupStrategy.INCREMENTAL
        assert incremental.interval_minutes == 240
        
        # Check differential backup
        assert "differential-12h" in backup_scheduler_service.schedules
        differential = backup_scheduler_service.schedules["differential-12h"]
        assert differential.strategy == BackupStrategy.DIFFERENTIAL
        assert differential.interval_minutes == 720
        
        # Check weekly archive
        assert "weekly-archive" in backup_scheduler_service.schedules
        weekly = backup_scheduler_service.schedules["weekly-archive"]
        assert weekly.schedule_type == ScheduleType.WEEKLY
        assert weekly.retention_days == 90
    
    def test_scheduler_not_started_initially(self, backup_scheduler_service):
        """Scheduler should not be running initially"""
        assert not backup_scheduler_service._is_running


class TestSchedulerLifecycle:
    """Test scheduler start/stop"""
    
    def test_start_scheduler(self, backup_scheduler_service, mock_scheduler):
        """Should start scheduler and register enabled schedules"""
        backup_scheduler_service.start()
        
        assert backup_scheduler_service._is_running
        mock_scheduler.start.assert_called_once()
        
        # Should register all default schedules (all enabled by default)
        assert mock_scheduler.add_job.call_count == 4
    
    def test_start_already_running(self, backup_scheduler_service, mock_scheduler):
        """Should not start if already running"""
        backup_scheduler_service.start()
        mock_scheduler.start.reset_mock()
        
        backup_scheduler_service.start()
        mock_scheduler.start.assert_not_called()
    
    def test_stop_scheduler(self, backup_scheduler_service, mock_scheduler):
        """Should stop scheduler"""
        backup_scheduler_service.start()
        backup_scheduler_service.stop()
        
        assert not backup_scheduler_service._is_running
        mock_scheduler.shutdown.assert_called_once()
    
    def test_stop_not_running(self, backup_scheduler_service, mock_scheduler):
        """Should handle stop when not running"""
        backup_scheduler_service.stop()
        mock_scheduler.shutdown.assert_not_called()


class TestScheduleManagement:
    """Test schedule management operations"""
    
    def test_add_schedule(self, backup_scheduler_service):
        """Should add new schedule"""
        schedule = BackupSchedule(
            id="custom-backup",
            name="Custom Backup",
            schedule_type=ScheduleType.CUSTOM,
            strategy=BackupStrategy.FULL,
            interval_minutes=60,
        )
        
        backup_scheduler_service.add_schedule(schedule)
        
        assert "custom-backup" in backup_scheduler_service.schedules
        assert backup_scheduler_service.schedules["custom-backup"] == schedule
    
    def test_add_schedule_registers_if_running(
        self, backup_scheduler_service, mock_scheduler
    ):
        """Should register schedule if scheduler is running"""
        backup_scheduler_service.start()
        mock_scheduler.add_job.reset_mock()
        
        schedule = BackupSchedule(
            id="custom-backup",
            name="Custom Backup",
            schedule_type=ScheduleType.CUSTOM,
            strategy=BackupStrategy.FULL,
            interval_minutes=60,
        )
        
        backup_scheduler_service.add_schedule(schedule)
        mock_scheduler.add_job.assert_called_once()
    
    def test_remove_schedule(self, backup_scheduler_service):
        """Should remove schedule"""
        schedule_id = "daily-full"
        assert schedule_id in backup_scheduler_service.schedules
        
        backup_scheduler_service.remove_schedule(schedule_id)
        
        assert schedule_id not in backup_scheduler_service.schedules
    
    def test_remove_schedule_unregisters_if_running(
        self, backup_scheduler_service, mock_scheduler
    ):
        """Should unregister schedule if scheduler is running"""
        backup_scheduler_service.start()
        
        schedule_id = "daily-full"
        backup_scheduler_service.remove_schedule(schedule_id)
        
        mock_scheduler.remove_job.assert_called_with(schedule_id)
    
    def test_enable_schedule(self, backup_scheduler_service):
        """Should enable disabled schedule"""
        schedule_id = "daily-full"
        backup_scheduler_service.schedules[schedule_id].enabled = False
        
        backup_scheduler_service.enable_schedule(schedule_id)
        
        assert backup_scheduler_service.schedules[schedule_id].enabled
    
    def test_enable_schedule_registers_if_running(
        self, backup_scheduler_service, mock_scheduler
    ):
        """Should register when enabling if scheduler is running"""
        backup_scheduler_service.start()
        mock_scheduler.add_job.reset_mock()
        
        schedule_id = "daily-full"
        backup_scheduler_service.schedules[schedule_id].enabled = False
        
        backup_scheduler_service.enable_schedule(schedule_id)
        mock_scheduler.add_job.assert_called_once()
    
    def test_disable_schedule(self, backup_scheduler_service):
        """Should disable schedule"""
        schedule_id = "daily-full"
        
        backup_scheduler_service.disable_schedule(schedule_id)
        
        assert not backup_scheduler_service.schedules[schedule_id].enabled
    
    def test_disable_schedule_unregisters_if_running(
        self, backup_scheduler_service, mock_scheduler
    ):
        """Should unregister when disabling if scheduler is running"""
        backup_scheduler_service.start()
        
        schedule_id = "daily-full"
        backup_scheduler_service.disable_schedule(schedule_id)
        
        mock_scheduler.remove_job.assert_called_with(schedule_id)


class TestBackupExecution:
    """Test backup execution"""
    
    def test_execute_backup_success(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should execute backup successfully"""
        schedule_id = "daily-full"
        schedule = backup_scheduler_service.schedules[schedule_id]
        
        backup_scheduler_service._execute_backup(schedule_id)
        
        # Should create backup
        mock_backup_service.create_backup.assert_called_once_with(
            strategy=schedule.strategy,
            metadata={
                "schedule_id": schedule_id,
                "schedule_name": schedule.name,
                "automated": True,
            }
        )
        
        # Should record execution
        assert len(backup_scheduler_service.executions) > 0
        execution = backup_scheduler_service.executions[-1]
        assert execution.schedule_id == schedule_id
        assert execution.status == ScheduleStatus.COMPLETED
        assert execution.backup_id is not None
        
        # Should update schedule
        assert schedule.last_execution is not None
        assert schedule.consecutive_failures == 0
    
    def test_execute_backup_failure(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should handle backup failure"""
        schedule_id = "daily-full"
        schedule = backup_scheduler_service.schedules[schedule_id]
        
        # Mock failure
        mock_backup_service.create_backup.side_effect = Exception("Backup failed")
        
        backup_scheduler_service._execute_backup(schedule_id)
        
        # Should record failed execution
        execution = backup_scheduler_service.executions[-1]
        assert execution.status == ScheduleStatus.FAILED
        assert execution.error_message == "Backup failed"
        
        # Should increment consecutive failures
        assert schedule.consecutive_failures == 1
    
    def test_execute_backup_with_restore_test(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should test restore if scheduled"""
        schedule_id = "daily-full"
        schedule = backup_scheduler_service.schedules[schedule_id]
        schedule.auto_test_restore = True
        schedule.last_test = None  # Never tested
        
        backup_scheduler_service._execute_backup(schedule_id)
        
        # Should test restore
        mock_backup_service.test_restore.assert_called_once()
        
        # Should record test result
        execution = backup_scheduler_service.executions[-1]
        assert execution.test_result is not None
        assert execution.test_result["success"]
        
        # Should update last test time
        assert schedule.last_test is not None
    
    def test_execute_backup_skips_restore_test_if_recent(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should skip restore test if recently tested"""
        schedule_id = "daily-full"
        schedule = backup_scheduler_service.schedules[schedule_id]
        schedule.auto_test_restore = True
        schedule.test_frequency_days = 7
        schedule.last_test = datetime.now(timezone.utc) - timedelta(days=3)  # Tested 3 days ago
        
        backup_scheduler_service._execute_backup(schedule_id)
        
        # Should not test restore
        mock_backup_service.test_restore.assert_not_called()
    
    def test_execute_backup_applies_retention(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should apply retention policy after backup"""
        schedule_id = "daily-full"
        schedule = backup_scheduler_service.schedules[schedule_id]
        
        backup_scheduler_service._execute_backup(schedule_id)
        
        # Should apply retention
        mock_backup_service.apply_retention_policy.assert_called_once_with(
            retention_days=schedule.retention_days
        )


class TestComplianceMonitoring:
    """Test RPO/RTO compliance monitoring"""
    
    def test_get_rpo_compliance(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should get RPO compliance status"""
        compliance = backup_scheduler_service.get_rpo_compliance()
        
        assert compliance["rpo_status"] == "healthy"
        assert compliance["within_target"]
        assert compliance["total_schedules"] == 4
        assert compliance["enabled_schedules"] == 4
    
    def test_get_rto_compliance(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should get RTO compliance status"""
        compliance = backup_scheduler_service.get_rto_compliance()
        
        assert compliance["rto_status"] == "healthy"
        assert compliance["within_target"]
        assert isinstance(compliance["schedules_needing_test"], list)
    
    def test_rpo_compliance_tracks_failures(self, backup_scheduler_service):
        """Should track failed schedules in RPO compliance"""
        # Mark a schedule as failed
        backup_scheduler_service.schedules["daily-full"].consecutive_failures = 3
        
        compliance = backup_scheduler_service.get_rpo_compliance()
        
        assert compliance["failed_schedules"] == 1
    
    def test_rto_compliance_identifies_schedules_needing_test(
        self, backup_scheduler_service
    ):
        """Should identify schedules needing restore test"""
        # Set schedule needing test
        schedule = backup_scheduler_service.schedules["daily-full"]
        schedule.auto_test_restore = True
        schedule.last_test = datetime.now(timezone.utc) - timedelta(days=10)
        
        compliance = backup_scheduler_service.get_rto_compliance()
        
        assert schedule.name in compliance["schedules_needing_test"]


class TestDisasterRecoveryReadiness:
    """Test disaster recovery readiness reporting"""
    
    def test_get_disaster_recovery_readiness(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should generate comprehensive readiness report"""
        # Execute some backups to create history
        backup_scheduler_service._execute_backup("daily-full")
        backup_scheduler_service._execute_backup("incremental-4h")
        
        report = backup_scheduler_service.get_disaster_recovery_readiness()
        
        assert "readiness_score" in report
        assert "readiness_level" in report
        assert "rpo_compliance" in report
        assert "rto_compliance" in report
        assert "backup_success_rate" in report
        assert "recent_executions" in report
        assert "recommendations" in report
    
    def test_readiness_score_calculation(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should calculate readiness score correctly"""
        # Execute successful backups
        for _ in range(10):
            backup_scheduler_service._execute_backup("daily-full")
        
        report = backup_scheduler_service.get_disaster_recovery_readiness()
        
        # Should have high score (RPO + RTO + success rate)
        assert report["readiness_score"] == 100
        assert report["readiness_level"] == "Excellent"
        assert report["backup_success_rate"] == 100.0
    
    def test_readiness_degraded_by_failures(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should degrade readiness score with failures"""
        # Mock some failures
        mock_backup_service.create_backup.side_effect = Exception("Failure")
        
        for _ in range(5):
            backup_scheduler_service._execute_backup("daily-full")
        
        report = backup_scheduler_service.get_disaster_recovery_readiness()
        
        # Should have lower score
        assert report["backup_success_rate"] == 0.0
        assert report["readiness_score"] < 100
    
    def test_readiness_recommendations(
        self, backup_scheduler_service, mock_backup_service
    ):
        """Should provide actionable recommendations"""
        # Set RPO out of compliance
        mock_backup_service.get_rpo_status.return_value = {
            "status": "warning",
            "message": "Last backup too old",
            "within_target": False,
            "hours_since_backup": 30.0,
        }
        
        report = backup_scheduler_service.get_disaster_recovery_readiness()
        
        assert any(
            "RPO" in rec 
            for rec in report["recommendations"]
        )


class TestForceBackup:
    """Test manual backup triggering"""
    
    def test_force_backup(self, backup_scheduler_service, mock_backup_service):
        """Should force immediate backup"""
        schedule_id = "daily-full"
        
        backup_id = backup_scheduler_service.force_backup(schedule_id)
        
        assert backup_id is not None
        mock_backup_service.create_backup.assert_called_once()
        
        # Should have execution record
        executions = [
            e for e in backup_scheduler_service.executions 
            if e.schedule_id == schedule_id
        ]
        assert len(executions) > 0
    
    def test_force_backup_invalid_schedule(self, backup_scheduler_service):
        """Should raise error for invalid schedule"""
        with pytest.raises(ValueError, match="Schedule not found"):
            backup_scheduler_service.force_backup("nonexistent")


class TestScheduleHistory:
    """Test schedule execution history"""
    
    def test_get_schedule_history(self, backup_scheduler_service):
        """Should get execution history for schedule"""
        schedule_id = "daily-full"
        
        # Execute multiple backups
        for _ in range(5):
            backup_scheduler_service._execute_backup(schedule_id)
        
        history = backup_scheduler_service.get_schedule_history(schedule_id)
        
        assert len(history) == 5
        assert all(e.schedule_id == schedule_id for e in history)
        
        # Should be ordered by time (newest first)
        for i in range(len(history) - 1):
            assert history[i].execution_time >= history[i + 1].execution_time
    
    def test_get_schedule_history_limit(self, backup_scheduler_service):
        """Should respect limit parameter"""
        schedule_id = "daily-full"
        
        # Execute many backups
        for _ in range(100):
            backup_scheduler_service._execute_backup(schedule_id)
        
        history = backup_scheduler_service.get_schedule_history(schedule_id, limit=10)
        
        assert len(history) == 10

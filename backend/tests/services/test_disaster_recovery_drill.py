"""
Tests for Disaster Recovery Drill Service.

Tests disaster recovery capabilities including:
- Drill configuration and scheduling
- Restore rehearsals
- RPO/RTO verification
- Compliance reporting
"""

from datetime import datetime, timedelta, timezone

import pytest

from sensei.services.disaster_recovery_drill import (
    BackupInfo,
    ComplianceLevel,
    DisasterRecoveryDrillService,
    DrillStatus,
    DrillType,
    RecoveryTarget,
    get_dr_drill_service,
    reset_dr_drill_service,
)


@pytest.fixture
def service():
    """Create a fresh DR drill service for each test."""
    reset_dr_drill_service()
    svc = get_dr_drill_service()
    yield svc
    reset_dr_drill_service()


# ===== Target Management Tests =====


class TestTargetManagement:
    """Tests for RPO/RTO target management."""
    
    def test_default_rpo_targets(self, service: DisasterRecoveryDrillService):
        """Test that default RPO targets are initialized."""
        targets = service.get_rpo_targets()
        
        assert len(targets) >= 3
        names = [t.target_name for t in targets]
        assert "database_critical" in names
        assert "file_storage" in names
    
    def test_default_rto_targets(self, service: DisasterRecoveryDrillService):
        """Test that default RTO targets are initialized."""
        targets = service.get_rto_targets()
        
        assert len(targets) >= 3
        names = [t.target_name for t in targets]
        assert "database_critical" in names
    
    def test_set_rpo_target(self, service: DisasterRecoveryDrillService):
        """Test setting a custom RPO target."""
        target = service.set_rpo_target(
            target_name="custom_db",
            recovery_target=RecoveryTarget.DATABASE,
            max_data_loss_minutes=5,
            description="Custom database RPO",
        )
        
        assert target.target_name == "custom_db"
        assert target.max_data_loss_minutes == 5
    
    def test_set_rpo_target_invalid(self, service: DisasterRecoveryDrillService):
        """Test that invalid RPO target is rejected."""
        with pytest.raises(ValueError, match="at least 1"):
            service.set_rpo_target(
                target_name="invalid",
                recovery_target=RecoveryTarget.DATABASE,
                max_data_loss_minutes=0,
            )
    
    def test_set_rto_target(self, service: DisasterRecoveryDrillService):
        """Test setting a custom RTO target."""
        target = service.set_rto_target(
            target_name="custom_app",
            recovery_target=RecoveryTarget.APPLICATION_STATE,
            max_recovery_minutes=10,
            description="Custom app RTO",
        )
        
        assert target.target_name == "custom_app"
        assert target.max_recovery_minutes == 10
    
    def test_set_rto_target_invalid(self, service: DisasterRecoveryDrillService):
        """Test that invalid RTO target is rejected."""
        with pytest.raises(ValueError, match="at least 1"):
            service.set_rto_target(
                target_name="invalid",
                recovery_target=RecoveryTarget.DATABASE,
                max_recovery_minutes=0,
            )


# ===== Configuration Tests =====


class TestConfiguration:
    """Tests for drill configuration management."""
    
    def test_create_configuration(self, service: DisasterRecoveryDrillService):
        """Test creating a drill configuration."""
        config = service.create_configuration(
            name="Full Database Restore",
            description="Monthly full restore drill",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
            rpo_target_minutes=15,
            rto_target_minutes=30,
        )
        
        assert config.id is not None
        assert config.name == "Full Database Restore"
        assert config.drill_type == DrillType.FULL_RESTORE
        assert config.rpo_target_minutes == 15
        assert config.rto_target_minutes == 30
    
    def test_create_configuration_with_notifications(
        self, service: DisasterRecoveryDrillService
    ):
        """Test creating configuration with notification settings."""
        config = service.create_configuration(
            name="Test Drill",
            description="Test",
            drill_type=DrillType.PARTIAL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
            notify_on_failure=True,
            notify_on_success=True,
            notification_emails=["admin@example.com", "ops@example.com"],
        )
        
        assert config.notify_on_failure is True
        assert config.notify_on_success is True
        assert len(config.notification_emails) == 2
    
    def test_get_configuration(self, service: DisasterRecoveryDrillService):
        """Test getting a configuration by ID."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        retrieved = service.get_configuration(config.id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_get_configuration_not_found(self, service: DisasterRecoveryDrillService):
        """Test getting a non-existent configuration."""
        assert service.get_configuration("nonexistent") is None
    
    def test_list_configurations(self, service: DisasterRecoveryDrillService):
        """Test listing all configurations."""
        for i in range(3):
            service.create_configuration(
                name=f"Config {i}",
                description=f"Description {i}",
                drill_type=DrillType.FULL_RESTORE,
                recovery_target=RecoveryTarget.DATABASE,
            )
        
        configs = service.list_configurations()
        assert len(configs) == 3
    
    def test_delete_configuration(self, service: DisasterRecoveryDrillService):
        """Test deleting a configuration."""
        config = service.create_configuration(
            name="Delete Me",
            description="To be deleted",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        deleted = service.delete_configuration(config.id)
        assert deleted is True
        assert service.get_configuration(config.id) is None
    
    def test_delete_configuration_removes_schedules(
        self, service: DisasterRecoveryDrillService
    ):
        """Test that deleting a config removes its schedules."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        schedule = service.create_schedule(
            configuration_id=config.id,
            frequency="weekly",
            day_of_week=1,
        )
        
        service.delete_configuration(config.id)
        
        assert service.get_schedule(schedule.id) is None


# ===== Schedule Tests =====


class TestScheduling:
    """Tests for drill scheduling."""
    
    def test_create_schedule_weekly(self, service: DisasterRecoveryDrillService):
        """Test creating a weekly schedule."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        schedule = service.create_schedule(
            configuration_id=config.id,
            frequency="weekly",
            day_of_week=1,  # Tuesday
            time_of_day="02:00",
        )
        
        assert schedule.id is not None
        assert schedule.frequency == "weekly"
        assert schedule.day_of_week == 1
        assert schedule.next_run_at is not None
    
    def test_create_schedule_monthly(self, service: DisasterRecoveryDrillService):
        """Test creating a monthly schedule."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        schedule = service.create_schedule(
            configuration_id=config.id,
            frequency="monthly",
            day_of_month=15,
            time_of_day="03:00",
        )
        
        assert schedule.frequency == "monthly"
        assert schedule.day_of_month == 15
    
    def test_create_schedule_invalid_frequency(
        self, service: DisasterRecoveryDrillService
    ):
        """Test that invalid frequency is rejected."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        with pytest.raises(ValueError, match="frequency must be"):
            service.create_schedule(
                configuration_id=config.id,
                frequency="hourly",  # Invalid
            )
    
    def test_create_schedule_config_not_found(
        self, service: DisasterRecoveryDrillService
    ):
        """Test creating schedule for non-existent config."""
        with pytest.raises(ValueError, match="not found"):
            service.create_schedule(
                configuration_id="nonexistent",
                frequency="daily",
            )
    
    def test_list_schedules(self, service: DisasterRecoveryDrillService):
        """Test listing schedules."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        for freq in ["daily", "weekly", "monthly"]:
            service.create_schedule(
                configuration_id=config.id,
                frequency=freq,
            )
        
        schedules = service.list_schedules()
        assert len(schedules) == 3
    
    def test_toggle_schedule(self, service: DisasterRecoveryDrillService):
        """Test enabling/disabling a schedule."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        schedule = service.create_schedule(
            configuration_id=config.id,
            frequency="daily",
        )
        
        assert schedule.is_active is True
        
        updated = service.toggle_schedule(schedule.id, False)
        assert updated.is_active is False
    
    def test_delete_schedule(self, service: DisasterRecoveryDrillService):
        """Test deleting a schedule."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        schedule = service.create_schedule(
            configuration_id=config.id,
            frequency="daily",
        )
        
        deleted = service.delete_schedule(schedule.id)
        assert deleted is True


# ===== Drill Execution Tests =====


class TestDrillExecution:
    """Tests for drill execution."""
    
    def test_start_drill(self, service: DisasterRecoveryDrillService):
        """Test starting a drill."""
        config = service.create_configuration(
            name="Full Restore",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(
            configuration_id=config.id,
            executed_by="admin",
            notes="Test drill",
        )
        
        assert execution.id is not None
        assert execution.status == DrillStatus.IN_PROGRESS
        assert execution.configuration_name == "Full Restore"
        assert execution.executed_by == "admin"
        assert len(execution.steps) > 0
    
    def test_start_drill_creates_steps(self, service: DisasterRecoveryDrillService):
        """Test that starting a drill creates appropriate steps."""
        config = service.create_configuration(
            name="Full Restore",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        
        step_names = [s.name for s in execution.steps]
        assert "verify_backup" in step_names
        assert "restore_database" in step_names
        assert "verify_data" in step_names
    
    def test_start_drill_failover_type(self, service: DisasterRecoveryDrillService):
        """Test starting a failover drill creates failover steps."""
        config = service.create_configuration(
            name="Failover",
            description="Test",
            drill_type=DrillType.FAILOVER,
            recovery_target=RecoveryTarget.FULL_SYSTEM,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        
        step_names = [s.name for s in execution.steps]
        assert "check_standby" in step_names
        assert "promote_standby" in step_names
    
    def test_start_drill_with_custom_backup(
        self, service: DisasterRecoveryDrillService
    ):
        """Test starting drill with custom backup info."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        backup = BackupInfo(
            id="backup-123",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            size_bytes=1024 * 1024 * 500,
            backup_type="full",
            tables_included=["users", "accounts"],
        )
        
        execution = service.start_drill(
            configuration_id=config.id,
            backup_info=backup,
        )
        
        assert execution.backup_used.id == "backup-123"
    
    def test_start_drill_config_not_found(
        self, service: DisasterRecoveryDrillService
    ):
        """Test starting drill for non-existent config."""
        with pytest.raises(ValueError, match="not found"):
            service.start_drill(configuration_id="nonexistent")
    
    def test_execute_step(self, service: DisasterRecoveryDrillService):
        """Test executing a drill step."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        step = execution.steps[0]
        
        result = service.execute_step(
            execution_id=execution.id,
            step_id=step.id,
            success=True,
            output={"rows_restored": 1000},
        )
        
        assert result.status == "completed"
        assert result.output["rows_restored"] == 1000
        assert result.duration_ms > 0
    
    def test_execute_step_failure(self, service: DisasterRecoveryDrillService):
        """Test executing a step that fails."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        step = execution.steps[0]
        
        result = service.execute_step(
            execution_id=execution.id,
            step_id=step.id,
            success=False,
            error_message="Connection timeout",
        )
        
        assert result.status == "failed"
        assert result.error_message == "Connection timeout"
    
    def test_complete_drill_success(self, service: DisasterRecoveryDrillService):
        """Test completing a drill successfully."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
            rpo_target_minutes=60,
            rto_target_minutes=60,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        
        # Execute all steps successfully
        for step in execution.steps:
            service.execute_step(execution.id, step.id, success=True)
        
        result = service.complete_drill(
            execution_id=execution.id,
            data_verified=True,
        )
        
        assert result.status == DrillStatus.COMPLETED
        assert result.rto_actual_minutes >= 0
        assert result.data_verified is True
    
    def test_complete_drill_rpo_compliance(
        self, service: DisasterRecoveryDrillService
    ):
        """Test RPO compliance is calculated."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
            rpo_target_minutes=60,  # Large enough to be compliant
        )
        
        execution = service.start_drill(configuration_id=config.id)
        result = service.complete_drill(execution.id, data_verified=True)
        
        assert result.rpo_actual_minutes > 0
        assert result.rpo_compliant is True
    
    def test_complete_drill_verification_failure(
        self, service: DisasterRecoveryDrillService
    ):
        """Test drill fails when verification fails."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        
        result = service.complete_drill(
            execution_id=execution.id,
            data_verified=False,
            verification_errors=["Table count mismatch"],
        )
        
        assert result.status == DrillStatus.FAILED
        assert "Data verification failed" in result.error_message
    
    def test_fail_drill(self, service: DisasterRecoveryDrillService):
        """Test failing a drill."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        
        result = service.fail_drill(
            execution_id=execution.id,
            error_message="Backup corrupted",
        )
        
        assert result.status == DrillStatus.FAILED
        assert result.error_message == "Backup corrupted"
    
    def test_cancel_drill(self, service: DisasterRecoveryDrillService):
        """Test cancelling a drill."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        execution = service.start_drill(configuration_id=config.id)
        
        result = service.cancel_drill(execution.id)
        
        assert result.status == DrillStatus.CANCELLED
    
    def test_list_executions(self, service: DisasterRecoveryDrillService):
        """Test listing executions."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        for _ in range(5):
            service.start_drill(configuration_id=config.id)
        
        executions = service.list_executions()
        assert len(executions) == 5
    
    def test_list_executions_filtered(self, service: DisasterRecoveryDrillService):
        """Test listing executions with filters."""
        config1 = service.create_configuration(
            name="Config1",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        config2 = service.create_configuration(
            name="Config2",
            description="Test",
            drill_type=DrillType.PARTIAL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        service.start_drill(configuration_id=config1.id)
        service.start_drill(configuration_id=config1.id)
        service.start_drill(configuration_id=config2.id)
        
        executions = service.list_executions(configuration_id=config1.id)
        assert len(executions) == 2


# ===== Results and Reporting Tests =====


class TestReporting:
    """Tests for results and compliance reporting."""
    
    def test_get_drill_result(self, service: DisasterRecoveryDrillService):
        """Test getting a drill result."""
        config = service.create_configuration(
            name="Test Drill",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
            rpo_target_minutes=60,
            rto_target_minutes=60,
        )
        
        execution = service.start_drill(
            configuration_id=config.id,
            executed_by="admin",
        )
        
        for step in execution.steps:
            service.execute_step(execution.id, step.id, success=True)
        
        service.complete_drill(execution.id, data_verified=True)
        
        result = service.get_drill_result(execution.id)
        
        assert result.execution_id == execution.id
        assert result.configuration_name == "Test Drill"
        assert result.drill_type == "full_restore"
        assert result.status == "completed"
        assert result.data_integrity_verified is True
    
    def test_generate_compliance_report_empty(
        self, service: DisasterRecoveryDrillService
    ):
        """Test generating report with no drills."""
        report = service.generate_compliance_report()
        
        assert report.total_drills == 0
        assert report.overall_compliance == ComplianceLevel.NON_COMPLIANT
        assert len(report.recommendations) > 0
        # Recommendations address compliance issues when there are no drills
        assert any("compliance" in r.lower() for r in report.recommendations)
    
    def test_generate_compliance_report_with_drills(
        self, service: DisasterRecoveryDrillService
    ):
        """Test generating report with completed drills."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
            rpo_target_minutes=120,  # High to ensure compliance
            rto_target_minutes=120,
        )
        
        # Run 5 successful drills
        for _ in range(5):
            execution = service.start_drill(configuration_id=config.id)
            for step in execution.steps:
                service.execute_step(execution.id, step.id, success=True)
            service.complete_drill(execution.id, data_verified=True)
        
        report = service.generate_compliance_report()
        
        assert report.total_drills == 5
        assert report.successful_drills == 5
        assert report.failed_drills == 0
        assert report.rpo_compliance_rate > 0
        assert len(report.drills) == 5
    
    def test_compliance_report_period_filtering(
        self, service: DisasterRecoveryDrillService
    ):
        """Test that report filters by period."""
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        # Create execution
        service.start_drill(configuration_id=config.id)
        
        # Report for future period should have no drills
        future_start = datetime.now(timezone.utc) + timedelta(days=30)
        future_end = datetime.now(timezone.utc) + timedelta(days=60)
        
        report = service.generate_compliance_report(
            period_start=future_start,
            period_end=future_end,
        )
        
        assert report.total_drills == 0


# ===== Singleton Tests =====


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_service_returns_same_instance(self):
        """Test that get_dr_drill_service returns same instance."""
        reset_dr_drill_service()
        
        s1 = get_dr_drill_service()
        s2 = get_dr_drill_service()
        
        assert s1 is s2
    
    def test_reset_clears_data(self):
        """Test that reset clears all data."""
        service = get_dr_drill_service()
        service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        
        reset_dr_drill_service()
        
        new_service = get_dr_drill_service()
        assert len(new_service.list_configurations()) == 0


# ===== Clear Data Tests =====


class TestClearData:
    """Tests for clearing all data."""
    
    def test_clear_all_data(self, service: DisasterRecoveryDrillService):
        """Test clearing all data."""
        # Create various data
        config = service.create_configuration(
            name="Test",
            description="Test",
            drill_type=DrillType.FULL_RESTORE,
            recovery_target=RecoveryTarget.DATABASE,
        )
        service.create_schedule(
            configuration_id=config.id,
            frequency="daily",
        )
        service.start_drill(configuration_id=config.id)
        
        service.clear_all_data()
        
        assert len(service.list_configurations()) == 0
        assert len(service.list_schedules()) == 0
        assert len(service.list_executions()) == 0
        # Default targets should be restored
        assert len(service.get_rpo_targets()) >= 3

"""
Tests for RFQ Time Tracking Service.

Tests time-on-task tracking for RFQ intake and quote approval workflows.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sensei.services.sales.rfq_time_tracking import (
    RFQTimeTrackingService,
    TaskType,
    TaskSessionStatus,
    PerformanceLevel,
    TaskTarget,
    TaskSession,
    PauseRecord,
    TimeAlert,
    TaskPerformanceStats,
    UserEfficiencyMetrics,
    DailyTimeBreakdown,
    DEFAULT_TASK_TARGETS,
    get_rfq_time_tracking_service,
    reset_rfq_time_tracking_service,
)


@pytest.fixture
def service():
    """Create a fresh service instance for each test."""
    svc = RFQTimeTrackingService()
    yield svc
    svc.reset()


@pytest.fixture
def sample_rfq_id():
    """Sample RFQ ID."""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid4()


class TestTaskTarget:
    """Tests for TaskTarget."""
    
    def test_target_creation(self):
        """Test creating a task target."""
        target = TaskTarget(
            task_type=TaskType.RFQ_INTAKE,
            target_seconds=600,
        )
        
        assert target.task_type == TaskType.RFQ_INTAKE
        assert target.target_seconds == 600
        assert target.warning_threshold_pct == 0.8
        assert target.critical_threshold_pct == 1.0
        assert target.max_threshold_pct == 1.2
    
    def test_warning_seconds(self):
        """Test warning threshold calculation."""
        target = TaskTarget(
            task_type=TaskType.RFQ_INTAKE,
            target_seconds=600,
            warning_threshold_pct=0.8,
        )
        
        assert target.warning_seconds == 480  # 80% of 600
    
    def test_critical_seconds(self):
        """Test critical threshold calculation."""
        target = TaskTarget(
            task_type=TaskType.RFQ_INTAKE,
            target_seconds=600,
            critical_threshold_pct=1.0,
        )
        
        assert target.critical_seconds == 600  # 100% of 600
    
    def test_max_seconds(self):
        """Test max threshold calculation."""
        target = TaskTarget(
            task_type=TaskType.RFQ_INTAKE,
            target_seconds=600,
            max_threshold_pct=1.2,
        )
        
        assert target.max_seconds == 720  # 120% of 600
    
    def test_performance_level_excellent(self):
        """Test excellent performance level."""
        target = TaskTarget(task_type=TaskType.RFQ_INTAKE, target_seconds=600)
        
        assert target.get_performance_level(200) == PerformanceLevel.EXCELLENT  # <50%
        assert target.get_performance_level(299) == PerformanceLevel.EXCELLENT
    
    def test_performance_level_good(self):
        """Test good performance level."""
        target = TaskTarget(task_type=TaskType.RFQ_INTAKE, target_seconds=600)
        
        assert target.get_performance_level(300) == PerformanceLevel.GOOD  # 50-80%
        assert target.get_performance_level(479) == PerformanceLevel.GOOD
    
    def test_performance_level_on_track(self):
        """Test on-track performance level."""
        target = TaskTarget(task_type=TaskType.RFQ_INTAKE, target_seconds=600)
        
        assert target.get_performance_level(480) == PerformanceLevel.ON_TRACK  # 80-100%
        assert target.get_performance_level(599) == PerformanceLevel.ON_TRACK
    
    def test_performance_level_warning(self):
        """Test warning performance level."""
        target = TaskTarget(task_type=TaskType.RFQ_INTAKE, target_seconds=600)
        
        assert target.get_performance_level(600) == PerformanceLevel.WARNING  # 100-120%
        assert target.get_performance_level(719) == PerformanceLevel.WARNING
    
    def test_performance_level_critical(self):
        """Test critical performance level."""
        target = TaskTarget(task_type=TaskType.RFQ_INTAKE, target_seconds=600)
        
        assert target.get_performance_level(720) == PerformanceLevel.CRITICAL  # >120%
        assert target.get_performance_level(1000) == PerformanceLevel.CRITICAL
    
    def test_to_dict(self):
        """Test target to_dict conversion."""
        target = TaskTarget(task_type=TaskType.RFQ_INTAKE, target_seconds=600)
        result = target.to_dict()
        
        assert result["task_type"] == "rfq_intake"
        assert result["target_seconds"] == 600
        assert "warning_seconds" in result
        assert "critical_seconds" in result
        assert "max_seconds" in result


class TestPauseRecord:
    """Tests for PauseRecord."""
    
    def test_pause_creation(self):
        """Test creating a pause record."""
        now = datetime.now(timezone.utc)
        pause = PauseRecord(paused_at=now)
        
        assert pause.paused_at == now
        assert pause.resumed_at is None
        assert pause.reason is None
    
    def test_pause_with_reason(self):
        """Test pause with reason."""
        pause = PauseRecord(
            paused_at=datetime.now(timezone.utc),
            reason="Phone call",
        )
        
        assert pause.reason == "Phone call"
    
    def test_pause_duration_open(self):
        """Test duration of open pause."""
        pause = PauseRecord(
            paused_at=datetime.now(timezone.utc) - timedelta(seconds=30),
        )
        
        # Should be approximately 30 seconds
        assert 25 <= pause.pause_duration_seconds <= 35
    
    def test_pause_duration_closed(self):
        """Test duration of closed pause."""
        now = datetime.now(timezone.utc)
        pause = PauseRecord(
            paused_at=now - timedelta(seconds=60),
            resumed_at=now,
        )
        
        assert pause.pause_duration_seconds == 60
    
    def test_to_dict(self):
        """Test pause to_dict conversion."""
        pause = PauseRecord(
            paused_at=datetime.now(timezone.utc),
            reason="Break",
        )
        result = pause.to_dict()
        
        assert "paused_at" in result
        assert result["reason"] == "Break"
        assert result["resumed_at"] is None


class TestTaskSession:
    """Tests for TaskSession."""
    
    def test_session_creation(self):
        """Test creating a task session."""
        rfq_id = uuid4()
        user_id = uuid4()
        
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=rfq_id,
            user_id=user_id,
            status=TaskSessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        
        assert session.task_type == TaskType.RFQ_INTAKE
        assert session.entity_id == rfq_id
        assert session.user_id == user_id
        assert session.status == TaskSessionStatus.ACTIVE
    
    def test_total_pause_seconds_no_pauses(self):
        """Test total pause time with no pauses."""
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        
        assert session.total_pause_seconds == 0
    
    def test_total_pause_seconds_with_pauses(self):
        """Test total pause time with closed pauses."""
        now = datetime.now(timezone.utc)
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.ACTIVE,
            started_at=now - timedelta(minutes=10),
            pauses=[
                PauseRecord(
                    paused_at=now - timedelta(minutes=8),
                    resumed_at=now - timedelta(minutes=7),
                ),
                PauseRecord(
                    paused_at=now - timedelta(minutes=3),
                    resumed_at=now - timedelta(minutes=2),
                ),
            ],
        )
        
        assert session.total_pause_seconds == 120  # 2 minutes total
    
    def test_active_elapsed_seconds(self):
        """Test active elapsed time calculation."""
        now = datetime.now(timezone.utc)
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.COMPLETED,
            started_at=now - timedelta(minutes=10),
            completed_at=now,
            pauses=[
                PauseRecord(
                    paused_at=now - timedelta(minutes=5),
                    resumed_at=now - timedelta(minutes=4),
                ),
            ],
        )
        
        # 10 minutes total - 1 minute pause = 9 minutes active
        assert 530 <= session.active_elapsed_seconds <= 550
    
    def test_is_currently_paused_false(self):
        """Test not currently paused."""
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        
        assert session.is_currently_paused is False
    
    def test_is_currently_paused_true(self):
        """Test currently paused."""
        now = datetime.now(timezone.utc)
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.PAUSED,
            started_at=now - timedelta(minutes=5),
            pauses=[PauseRecord(paused_at=now)],
        )
        
        assert session.is_currently_paused is True
    
    def test_to_dict(self):
        """Test session to_dict conversion."""
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
            notes="Test session",
        )
        result = session.to_dict()
        
        assert result["task_type"] == "rfq_intake"
        assert result["status"] == "active"
        assert result["notes"] == "Test session"
        assert "active_elapsed_seconds" in result


class TestTimeAlert:
    """Tests for TimeAlert."""
    
    def test_alert_creation(self):
        """Test creating a time alert."""
        alert = TimeAlert(
            id=uuid4(),
            session_id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            alert_type="warning",
            threshold_seconds=480,
            elapsed_seconds=500,
            created_at=datetime.now(timezone.utc),
            message="Approaching target time",
        )
        
        assert alert.alert_type == "warning"
        assert alert.threshold_seconds == 480
        assert alert.acknowledged is False
    
    def test_to_dict(self):
        """Test alert to_dict conversion."""
        alert = TimeAlert(
            id=uuid4(),
            session_id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            alert_type="warning",
            threshold_seconds=480,
            elapsed_seconds=500,
            created_at=datetime.now(timezone.utc),
            message="Test alert",
        )
        result = alert.to_dict()
        
        assert result["alert_type"] == "warning"
        assert result["message"] == "Test alert"
        assert result["acknowledged"] is False


class TestRFQTimeTrackingServiceSessions:
    """Tests for session management."""
    
    def test_start_session(self, service, sample_rfq_id, sample_user_id):
        """Test starting a session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        assert session.task_type == TaskType.RFQ_INTAKE
        assert session.entity_id == sample_rfq_id
        assert session.user_id == sample_user_id
        assert session.status == TaskSessionStatus.ACTIVE
    
    def test_start_session_with_notes(self, service, sample_rfq_id, sample_user_id):
        """Test starting a session with notes."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
            notes="Initial intake for customer X",
        )
        
        assert session.notes == "Initial intake for customer X"
    
    def test_start_session_with_metadata(self, service, sample_rfq_id, sample_user_id):
        """Test starting a session with metadata."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
            metadata={"priority": "high"},
        )
        
        assert session.metadata["priority"] == "high"
    
    def test_start_session_returns_existing(self, service, sample_rfq_id, sample_user_id):
        """Test that starting a session returns existing active session."""
        session1 = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        session2 = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        assert session1.id == session2.id
    
    def test_pause_session(self, service, sample_rfq_id, sample_user_id):
        """Test pausing a session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        paused = service.pause_session(session.id, reason="Phone call")
        
        assert paused.status == TaskSessionStatus.PAUSED
        assert paused.is_currently_paused is True
        assert len(paused.pauses) == 1
        assert paused.pauses[0].reason == "Phone call"
    
    def test_pause_already_paused(self, service, sample_rfq_id, sample_user_id):
        """Test pausing already paused session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        service.pause_session(session.id)
        paused = service.pause_session(session.id)
        
        # Should not add another pause
        assert len(paused.pauses) == 1
    
    def test_resume_session(self, service, sample_rfq_id, sample_user_id):
        """Test resuming a session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        service.pause_session(session.id)
        resumed = service.resume_session(session.id)
        
        assert resumed.status == TaskSessionStatus.ACTIVE
        assert resumed.is_currently_paused is False
        assert resumed.pauses[0].resumed_at is not None
    
    def test_resume_not_paused(self, service, sample_rfq_id, sample_user_id):
        """Test resuming a non-paused session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        resumed = service.resume_session(session.id)
        
        assert resumed.status == TaskSessionStatus.ACTIVE
    
    def test_complete_session(self, service, sample_rfq_id, sample_user_id):
        """Test completing a session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        completed = service.complete_session(session.id, notes="Done")
        
        assert completed.status == TaskSessionStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.notes == "Done"
    
    def test_complete_paused_session(self, service, sample_rfq_id, sample_user_id):
        """Test completing a paused session closes pause."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        service.pause_session(session.id)
        completed = service.complete_session(session.id)
        
        assert completed.status == TaskSessionStatus.COMPLETED
        assert completed.pauses[0].resumed_at is not None
    
    def test_abandon_session(self, service, sample_rfq_id, sample_user_id):
        """Test abandoning a session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        abandoned = service.abandon_session(session.id, reason="Customer cancelled")
        
        assert abandoned.status == TaskSessionStatus.ABANDONED
        assert abandoned.metadata["abandon_reason"] == "Customer cancelled"
    
    def test_get_session(self, service, sample_rfq_id, sample_user_id):
        """Test getting a session by ID."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        retrieved = service.get_session(session.id)
        
        assert retrieved.id == session.id
    
    def test_get_session_not_found(self, service):
        """Test getting non-existent session."""
        result = service.get_session(uuid4())
        
        assert result is None
    
    def test_get_active_session(self, service, sample_rfq_id, sample_user_id):
        """Test getting active session for entity/user."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        active = service.get_active_session(sample_rfq_id, sample_user_id)
        
        assert active.id == session.id
    
    def test_get_active_session_after_complete(self, service, sample_rfq_id, sample_user_id):
        """Test no active session after completion."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        service.complete_session(session.id)
        active = service.get_active_session(sample_rfq_id, sample_user_id)
        
        assert active is None
    
    def test_get_user_active_sessions(self, service, sample_user_id):
        """Test getting all active sessions for a user."""
        rfq1 = uuid4()
        rfq2 = uuid4()
        
        service.start_session(TaskType.RFQ_INTAKE, rfq1, sample_user_id)
        service.start_session(TaskType.RFQ_REVIEW, rfq2, sample_user_id)
        
        sessions = service.get_user_active_sessions(sample_user_id)
        
        assert len(sessions) == 2
    
    def test_get_entity_sessions(self, service, sample_rfq_id):
        """Test getting all sessions for an entity."""
        user1 = uuid4()
        user2 = uuid4()
        
        service.start_session(TaskType.RFQ_INTAKE, sample_rfq_id, user1)
        service.start_session(TaskType.RFQ_REVIEW, sample_rfq_id, user2)
        
        sessions = service.get_entity_sessions(sample_rfq_id)
        
        assert len(sessions) == 2


class TestRFQTimeTrackingServiceMonitoring:
    """Tests for real-time monitoring."""
    
    def test_check_session_status(self, service, sample_rfq_id, sample_user_id):
        """Test checking session status."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        status = service.check_session_status(session.id)
        
        assert status["session_id"] == str(session.id)
        assert status["task_type"] == "rfq_intake"
        assert status["status"] == "active"
        assert "elapsed_seconds" in status
        assert "target_seconds" in status
        assert status["target_seconds"] == 600
    
    def test_check_session_status_not_found(self, service):
        """Test checking non-existent session."""
        result = service.check_session_status(uuid4())
        
        assert "error" in result
    
    def test_check_session_performance_level(self, service, sample_rfq_id, sample_user_id):
        """Test performance level in status check."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        status = service.check_session_status(session.id)
        
        assert "performance_level" in status
        assert status["performance_level"] == "excellent"  # Just started
    
    def test_get_session_alerts(self, service, sample_rfq_id, sample_user_id):
        """Test getting alerts for a session."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        # Alerts are generated during status check
        service.check_session_status(session.id)
        alerts = service.get_session_alerts(session.id)
        
        # New session shouldn't have alerts
        assert len(alerts) == 0
    
    def test_acknowledge_alert(self, service, sample_rfq_id, sample_user_id):
        """Test acknowledging an alert."""
        # Create an alert manually for testing
        from sensei.services.sales.rfq_time_tracking import TimeAlert
        
        alert = TimeAlert(
            id=uuid4(),
            session_id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            alert_type="warning",
            threshold_seconds=480,
            elapsed_seconds=500,
            created_at=datetime.now(timezone.utc),
            message="Test",
        )
        
        service._alerts[alert.id] = alert
        
        ack_user = uuid4()
        acknowledged = service.acknowledge_alert(alert.id, ack_user)
        
        assert acknowledged.acknowledged is True
        assert acknowledged.acknowledged_by == ack_user
        assert acknowledged.acknowledged_at is not None
    
    def test_get_pending_alerts(self, service, sample_rfq_id, sample_user_id):
        """Test getting pending alerts."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        # Add test alert
        from sensei.services.sales.rfq_time_tracking import TimeAlert
        
        alert = TimeAlert(
            id=uuid4(),
            session_id=session.id,
            task_type=TaskType.RFQ_INTAKE,
            alert_type="warning",
            threshold_seconds=480,
            elapsed_seconds=500,
            created_at=datetime.now(timezone.utc),
            message="Test",
        )
        
        service._alerts[alert.id] = alert
        service._alerts_by_session[session.id] = [alert.id]
        
        pending = service.get_pending_alerts()
        
        assert len(pending) == 1
    
    def test_get_pending_alerts_by_user(self, service, sample_rfq_id, sample_user_id):
        """Test getting pending alerts filtered by user."""
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        from sensei.services.sales.rfq_time_tracking import TimeAlert
        
        alert = TimeAlert(
            id=uuid4(),
            session_id=session.id,
            task_type=TaskType.RFQ_INTAKE,
            alert_type="warning",
            threshold_seconds=480,
            elapsed_seconds=500,
            created_at=datetime.now(timezone.utc),
            message="Test",
        )
        
        service._alerts[alert.id] = alert
        service._alerts_by_session[session.id] = [alert.id]
        
        # Should find alert for this user
        pending = service.get_pending_alerts(sample_user_id)
        assert len(pending) == 1
        
        # Should not find alert for different user
        other_user = uuid4()
        pending = service.get_pending_alerts(other_user)
        assert len(pending) == 0
    
    def test_add_alert_listener(self, service, sample_rfq_id, sample_user_id):
        """Test adding alert listener."""
        received_alerts = []
        
        def listener(alert):
            received_alerts.append(alert)
        
        service.add_alert_listener(listener)
        
        # Create a session and trigger alert by simulating elapsed time
        # For this test, we'll manually create an alert
        session = service.start_session(
            task_type=TaskType.RFQ_INTAKE,
            entity_id=sample_rfq_id,
            user_id=sample_user_id,
        )
        
        # Force create an alert
        target = service.get_target(TaskType.RFQ_INTAKE)
        service._create_alert(session, "warning", target.warning_seconds, 500, "Test")
        
        assert len(received_alerts) == 1
    
    def test_remove_alert_listener(self, service):
        """Test removing alert listener."""
        received_alerts = []
        
        def listener(alert):
            received_alerts.append(alert)
        
        service.add_alert_listener(listener)
        service.remove_alert_listener(listener)
        
        assert listener not in service._listeners


class TestRFQTimeTrackingServiceTargets:
    """Tests for target management."""
    
    def test_get_default_targets(self, service):
        """Test getting default targets."""
        targets = service.get_all_targets()
        
        assert TaskType.RFQ_INTAKE in targets
        assert targets[TaskType.RFQ_INTAKE].target_seconds == 600  # 10 min
        
        assert TaskType.QUOTE_APPROVAL in targets
        assert targets[TaskType.QUOTE_APPROVAL].target_seconds == 60  # 60s
    
    def test_get_target(self, service):
        """Test getting a specific target."""
        target = service.get_target(TaskType.RFQ_INTAKE)
        
        assert target is not None
        assert target.target_seconds == 600
    
    def test_set_target(self, service):
        """Test setting a custom target."""
        custom_target = TaskTarget(
            task_type=TaskType.RFQ_INTAKE,
            target_seconds=900,  # 15 min
        )
        
        service.set_target(custom_target)
        
        target = service.get_target(TaskType.RFQ_INTAKE)
        assert target.target_seconds == 900
    
    def test_default_targets_constants(self):
        """Test default target constants."""
        assert TaskType.RFQ_INTAKE in DEFAULT_TASK_TARGETS
        assert DEFAULT_TASK_TARGETS[TaskType.RFQ_INTAKE].target_seconds == 600
        
        assert TaskType.QUOTE_APPROVAL in DEFAULT_TASK_TARGETS
        assert DEFAULT_TASK_TARGETS[TaskType.QUOTE_APPROVAL].target_seconds == 60


class TestRFQTimeTrackingServiceAnalytics:
    """Tests for analytics."""
    
    def test_get_performance_stats_no_data(self, service):
        """Test performance stats with no data."""
        stats = service.get_performance_stats(TaskType.RFQ_INTAKE)
        
        assert stats is None
    
    def test_get_performance_stats_with_data(self, service):
        """Test performance stats with completed sessions."""
        rfq_id = uuid4()
        user_id = uuid4()
        
        # Create and complete some sessions
        for i in range(5):
            session = service.start_session(
                TaskType.RFQ_INTAKE,
                uuid4(),
                user_id,
            )
            service.complete_session(session.id)
        
        stats = service.get_performance_stats(TaskType.RFQ_INTAKE)
        
        assert stats is not None
        assert stats.completed_sessions == 5
        assert stats.task_type == TaskType.RFQ_INTAKE
    
    def test_get_performance_stats_filtered_by_user(self, service):
        """Test performance stats filtered by user."""
        user1 = uuid4()
        user2 = uuid4()
        
        # Create sessions for both users
        session1 = service.start_session(TaskType.RFQ_INTAKE, uuid4(), user1)
        service.complete_session(session1.id)
        
        session2 = service.start_session(TaskType.RFQ_INTAKE, uuid4(), user2)
        service.complete_session(session2.id)
        
        # Get stats for user1 only
        stats = service.get_performance_stats(TaskType.RFQ_INTAKE, user_id=user1)
        
        assert stats.completed_sessions == 1
    
    def test_get_user_efficiency_no_data(self, service):
        """Test user efficiency with no data."""
        result = service.get_user_efficiency(uuid4())
        
        assert result is None
    
    def test_get_user_efficiency_with_data(self, service):
        """Test user efficiency with data."""
        user_id = uuid4()
        
        # Create sessions across task types
        session1 = service.start_session(TaskType.RFQ_INTAKE, uuid4(), user_id)
        service.complete_session(session1.id)
        
        session2 = service.start_session(TaskType.QUOTE_APPROVAL, uuid4(), user_id)
        service.complete_session(session2.id)
        
        efficiency = service.get_user_efficiency(user_id)
        
        assert efficiency is not None
        assert efficiency.user_id == user_id
        assert efficiency.total_sessions == 2
        assert TaskType.RFQ_INTAKE in efficiency.metrics_by_task
    
    def test_get_daily_breakdown(self, service):
        """Test daily breakdown."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        
        breakdown = service.get_daily_breakdown(TaskType.RFQ_INTAKE, start, now)
        
        assert len(breakdown) == 8  # 7 days + today
        assert all(isinstance(d, DailyTimeBreakdown) for d in breakdown)
    
    def test_get_leaderboard(self, service):
        """Test leaderboard generation."""
        user1 = uuid4()
        user2 = uuid4()
        
        # Create more sessions for user1
        for _ in range(5):
            session = service.start_session(TaskType.RFQ_INTAKE, uuid4(), user1)
            service.complete_session(session.id)
        
        for _ in range(3):
            session = service.start_session(TaskType.RFQ_INTAKE, uuid4(), user2)
            service.complete_session(session.id)
        
        leaderboard = service.get_leaderboard(TaskType.RFQ_INTAKE)
        
        assert len(leaderboard) == 2
        assert leaderboard[0]["efficiency_rank"] == 1
        assert leaderboard[1]["efficiency_rank"] == 2


class TestRFQTimeTrackingServiceUtility:
    """Tests for utility methods."""
    
    def test_format_duration_seconds(self, service):
        """Test formatting seconds."""
        assert service._format_duration(45) == "45s"
    
    def test_format_duration_minutes(self, service):
        """Test formatting minutes."""
        assert service._format_duration(125) == "2m 5s"
    
    def test_format_duration_hours(self, service):
        """Test formatting hours."""
        assert service._format_duration(3725) == "1h 2m"
    
    def test_get_rfq_intake_summary(self, service, sample_rfq_id, sample_user_id):
        """Test RFQ intake summary."""
        session = service.start_session(
            TaskType.RFQ_INTAKE,
            sample_rfq_id,
            sample_user_id,
        )
        service.complete_session(session.id)
        
        summary = service.get_rfq_intake_summary(sample_rfq_id)
        
        assert summary["rfq_id"] == str(sample_rfq_id)
        assert summary["completed_sessions"] == 1
        assert summary["target_seconds"] == 600
    
    def test_cleanup_expired_sessions(self, service):
        """Test cleaning up expired sessions."""
        # Create a session with old start time
        session = TaskSession(
            id=uuid4(),
            task_type=TaskType.RFQ_INTAKE,
            entity_id=uuid4(),
            user_id=uuid4(),
            status=TaskSessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        
        service._sessions[session.id] = session
        
        cleaned = service.cleanup_expired_sessions(max_age_hours=24)
        
        assert cleaned == 1
        assert session.status == TaskSessionStatus.EXPIRED
    
    def test_reset(self, service, sample_rfq_id, sample_user_id):
        """Test reset clears all data."""
        service.start_session(TaskType.RFQ_INTAKE, sample_rfq_id, sample_user_id)
        
        service.reset()
        
        assert len(service._sessions) == 0
        assert len(service._alerts) == 0


class TestSingletonPattern:
    """Tests for singleton pattern."""
    
    def test_get_service_instance(self):
        """Test getting singleton instance."""
        reset_rfq_time_tracking_service()
        
        instance1 = get_rfq_time_tracking_service()
        instance2 = get_rfq_time_tracking_service()
        
        assert instance1 is instance2
    
    def test_reset_service_instance(self):
        """Test resetting singleton."""
        instance1 = get_rfq_time_tracking_service()
        reset_rfq_time_tracking_service()
        instance2 = get_rfq_time_tracking_service()
        
        assert instance1 is not instance2


class TestTaskPerformanceStats:
    """Tests for TaskPerformanceStats."""
    
    def test_stats_creation(self):
        """Test creating performance stats."""
        now = datetime.now(timezone.utc)
        stats = TaskPerformanceStats(
            task_type=TaskType.RFQ_INTAKE,
            period_start=now - timedelta(days=30),
            period_end=now,
            total_sessions=100,
            completed_sessions=90,
            abandoned_sessions=10,
            average_duration_seconds=450.5,
            median_duration_seconds=420.0,
            min_duration_seconds=120,
            max_duration_seconds=900,
            p90_duration_seconds=580,
            target_seconds=600,
            sessions_under_target=75,
            sessions_over_target=15,
            target_compliance_rate=83.33,
        )
        
        assert stats.total_sessions == 100
        assert stats.target_compliance_rate == 83.33
    
    def test_stats_to_dict(self):
        """Test stats to_dict conversion."""
        now = datetime.now(timezone.utc)
        stats = TaskPerformanceStats(
            task_type=TaskType.RFQ_INTAKE,
            period_start=now - timedelta(days=30),
            period_end=now,
            total_sessions=100,
            completed_sessions=90,
            abandoned_sessions=10,
            average_duration_seconds=450.5,
            median_duration_seconds=420.0,
            min_duration_seconds=120,
            max_duration_seconds=900,
            p90_duration_seconds=580,
            target_seconds=600,
            sessions_under_target=75,
            sessions_over_target=15,
            target_compliance_rate=83.33,
        )
        
        result = stats.to_dict()
        
        assert result["task_type"] == "rfq_intake"
        assert result["total_sessions"] == 100
        assert result["average_duration_seconds"] == 450.5


class TestUserEfficiencyMetrics:
    """Tests for UserEfficiencyMetrics."""
    
    def test_efficiency_to_dict(self):
        """Test efficiency metrics to_dict conversion."""
        now = datetime.now(timezone.utc)
        user_id = uuid4()
        
        stats = TaskPerformanceStats(
            task_type=TaskType.RFQ_INTAKE,
            period_start=now - timedelta(days=30),
            period_end=now,
            total_sessions=10,
            completed_sessions=10,
            abandoned_sessions=0,
            average_duration_seconds=300,
            median_duration_seconds=280,
            min_duration_seconds=200,
            max_duration_seconds=500,
            p90_duration_seconds=450,
            target_seconds=600,
            sessions_under_target=10,
            sessions_over_target=0,
            target_compliance_rate=100.0,
        )
        
        efficiency = UserEfficiencyMetrics(
            user_id=user_id,
            period_start=now - timedelta(days=30),
            period_end=now,
            metrics_by_task={TaskType.RFQ_INTAKE: stats},
            total_active_time_seconds=3000,
            total_sessions=10,
            efficiency_score=100.0,
            trend="stable",
        )
        
        result = efficiency.to_dict()
        
        assert result["user_id"] == str(user_id)
        assert result["efficiency_score"] == 100.0
        assert result["trend"] == "stable"
        assert "rfq_intake" in result["metrics_by_task"]


class TestDailyTimeBreakdown:
    """Tests for DailyTimeBreakdown."""
    
    def test_breakdown_to_dict(self):
        """Test daily breakdown to_dict conversion."""
        now = datetime.now(timezone.utc)
        
        breakdown = DailyTimeBreakdown(
            date=now,
            task_type=TaskType.RFQ_INTAKE,
            total_sessions=15,
            completed_sessions=12,
            total_active_seconds=5400,
            average_duration_seconds=450.0,
            under_target_count=10,
            over_target_count=2,
        )
        
        result = breakdown.to_dict()
        
        assert result["task_type"] == "rfq_intake"
        assert result["total_sessions"] == 15
        assert result["under_target_count"] == 10

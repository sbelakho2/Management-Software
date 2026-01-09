"""
Tests for Quote Approval Time Tracking Service.

Tests time-on-task tracking for quote approval with < 60 second target.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sensei.services.quote_approval_time_tracking import (
    QuoteApprovalTimeTrackingService,
    ApprovalDecision,
    ApprovalReason,
    ApprovalSessionStatus,
    ApprovalCriterionStatus,
    ApprovalCriterion,
    QuoteApprovalContext,
    ApprovalSession,
    ApprovalAlert,
    ApproverPerformance,
    QuickApprovalOption,
    DEFAULT_QUICK_OPTIONS,
    DEFAULT_APPROVAL_CRITERIA,
    get_quote_approval_service,
    reset_quote_approval_service,
)


@pytest.fixture
def service():
    """Create a fresh service instance for each test."""
    svc = QuoteApprovalTimeTrackingService()
    yield svc
    svc.reset()


@pytest.fixture
def sample_quote_id():
    """Sample quote ID."""
    return uuid4()


@pytest.fixture
def sample_approver_id():
    """Sample approver ID."""
    return uuid4()


@pytest.fixture
def sample_context(sample_quote_id):
    """Sample quote approval context."""
    return QuoteApprovalContext(
        quote_id=sample_quote_id,
        quote_number="Q-2024-0001",
        version=1,
        customer_name="Acme Corp",
        total_value=50000.0,
        margin_percent=22.5,
        line_item_count=5,
        currency="USD",
        urgency="normal",
    )


class TestApprovalCriterion:
    """Tests for ApprovalCriterion."""
    
    def test_criterion_creation(self):
        """Test creating a criterion."""
        criterion = ApprovalCriterion(
            id="margin_check",
            name="Margin Threshold",
            description="Check margin meets minimum",
            category="financial",
        )
        
        assert criterion.id == "margin_check"
        assert criterion.status == ApprovalCriterionStatus.SKIPPED
    
    def test_criterion_to_dict(self):
        """Test criterion to_dict conversion."""
        criterion = ApprovalCriterion(
            id="margin_check",
            name="Margin Threshold",
            description="Check margin",
            category="financial",
            status=ApprovalCriterionStatus.PASSED,
            value=25.0,
            threshold=15.0,
            message="Margin OK",
        )
        
        result = criterion.to_dict()
        assert result["id"] == "margin_check"
        assert result["status"] == "passed"
        assert result["value"] == 25.0


class TestQuoteApprovalContext:
    """Tests for QuoteApprovalContext."""
    
    def test_context_creation(self, sample_quote_id):
        """Test creating a context."""
        context = QuoteApprovalContext(
            quote_id=sample_quote_id,
            quote_number="Q-001",
            version=1,
            customer_name="Customer",
            total_value=10000.0,
            margin_percent=20.0,
            line_item_count=3,
        )
        
        assert context.quote_id == sample_quote_id
        assert context.total_value == 10000.0
    
    def test_context_to_dict(self, sample_quote_id):
        """Test context to_dict conversion."""
        context = QuoteApprovalContext(
            quote_id=sample_quote_id,
            quote_number="Q-001",
            version=1,
            customer_name="Customer",
            total_value=10000.0,
            margin_percent=20.0,
            line_item_count=3,
        )
        
        result = context.to_dict()
        assert result["quote_number"] == "Q-001"
        assert result["total_value"] == 10000.0


class TestApprovalSession:
    """Tests for ApprovalSession."""
    
    def test_session_creation(self, sample_quote_id, sample_approver_id, sample_context):
        """Test creating a session."""
        session = ApprovalSession(
            id=uuid4(),
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
            status=ApprovalSessionStatus.STARTED,
            started_at=datetime.now(timezone.utc),
        )
        
        assert session.status == ApprovalSessionStatus.STARTED
        assert session.decision is None
    
    def test_elapsed_seconds(self, sample_quote_id, sample_approver_id, sample_context):
        """Test elapsed time calculation."""
        session = ApprovalSession(
            id=uuid4(),
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
            status=ApprovalSessionStatus.STARTED,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=30),
        )
        
        assert 25 <= session.elapsed_seconds <= 35
    
    def test_is_within_target_true(self, sample_quote_id, sample_approver_id, sample_context):
        """Test within target check - true."""
        now = datetime.now(timezone.utc)
        session = ApprovalSession(
            id=uuid4(),
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
            status=ApprovalSessionStatus.DECIDED,
            started_at=now - timedelta(seconds=45),
            completed_at=now,
        )
        
        assert session.is_within_target is True
    
    def test_is_within_target_false(self, sample_quote_id, sample_approver_id, sample_context):
        """Test within target check - false."""
        now = datetime.now(timezone.utc)
        session = ApprovalSession(
            id=uuid4(),
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
            status=ApprovalSessionStatus.DECIDED,
            started_at=now - timedelta(seconds=90),
            completed_at=now,
        )
        
        assert session.is_within_target is False
    
    def test_criteria_summary(self, sample_quote_id, sample_approver_id, sample_context):
        """Test criteria summary."""
        session = ApprovalSession(
            id=uuid4(),
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
            status=ApprovalSessionStatus.STARTED,
            started_at=datetime.now(timezone.utc),
            criteria=[
                ApprovalCriterion(id="1", name="C1", description="D1", category="cat", 
                                 status=ApprovalCriterionStatus.PASSED),
                ApprovalCriterion(id="2", name="C2", description="D2", category="cat",
                                 status=ApprovalCriterionStatus.PASSED),
                ApprovalCriterion(id="3", name="C3", description="D3", category="cat",
                                 status=ApprovalCriterionStatus.FAILED),
                ApprovalCriterion(id="4", name="C4", description="D4", category="cat",
                                 status=ApprovalCriterionStatus.WARNING),
            ],
        )
        
        summary = session.criteria_summary
        assert summary["total"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["warning"] == 1
    
    def test_to_dict(self, sample_quote_id, sample_approver_id, sample_context):
        """Test session to_dict conversion."""
        session = ApprovalSession(
            id=uuid4(),
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
            status=ApprovalSessionStatus.STARTED,
            started_at=datetime.now(timezone.utc),
        )
        
        result = session.to_dict()
        assert "id" in result
        assert result["status"] == "started"
        assert "elapsed_seconds" in result


class TestApprovalAlert:
    """Tests for ApprovalAlert."""
    
    def test_alert_creation(self):
        """Test creating an alert."""
        alert = ApprovalAlert(
            id=uuid4(),
            session_id=uuid4(),
            alert_type="warning",
            elapsed_seconds=45,
            created_at=datetime.now(timezone.utc),
            message="15 seconds remaining",
        )
        
        assert alert.alert_type == "warning"
        assert alert.elapsed_seconds == 45
    
    def test_alert_to_dict(self):
        """Test alert to_dict conversion."""
        alert = ApprovalAlert(
            id=uuid4(),
            session_id=uuid4(),
            alert_type="critical",
            elapsed_seconds=55,
            created_at=datetime.now(timezone.utc),
            message="Test",
        )
        
        result = alert.to_dict()
        assert result["alert_type"] == "critical"


class TestQuickApprovalOption:
    """Tests for QuickApprovalOption."""
    
    def test_option_creation(self):
        """Test creating a quick option."""
        option = QuickApprovalOption(
            id="quick_approve",
            label="Approve",
            decision=ApprovalDecision.APPROVED,
            reason=ApprovalReason.WITHIN_AUTHORITY,
            icon="check",
            color="green",
        )
        
        assert option.id == "quick_approve"
        assert option.requires_comment is False
    
    def test_option_to_dict(self):
        """Test option to_dict conversion."""
        option = QuickApprovalOption(
            id="reject",
            label="Reject",
            decision=ApprovalDecision.REJECTED,
            reason=ApprovalReason.MARGIN_TOO_LOW,
            icon="x",
            color="red",
            requires_comment=True,
        )
        
        result = option.to_dict()
        assert result["requires_comment"] is True


class TestDefaultOptions:
    """Tests for default options and criteria."""
    
    def test_default_quick_options(self):
        """Test default quick options exist."""
        assert len(DEFAULT_QUICK_OPTIONS) >= 4
        
        ids = [o.id for o in DEFAULT_QUICK_OPTIONS]
        assert "quick_approve" in ids
        assert "reject_margin" in ids
        assert "escalate" in ids
    
    def test_default_criteria(self):
        """Test default criteria exist."""
        assert len(DEFAULT_APPROVAL_CRITERIA) >= 4
        
        ids = [c["id"] for c in DEFAULT_APPROVAL_CRITERIA]
        assert "margin_check" in ids
        assert "authority_level" in ids


class TestQuoteApprovalServiceSessions:
    """Tests for session management."""
    
    def test_start_approval_session(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test starting an approval session."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        assert session.quote_id == sample_quote_id
        assert session.approver_id == sample_approver_id
        assert session.status == ApprovalSessionStatus.STARTED
        assert len(session.criteria) > 0
    
    def test_start_session_returns_existing(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test that starting returns existing active session."""
        session1 = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        session2 = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        assert session1.id == session2.id
    
    def test_criteria_auto_check_margin_passed(self, service, sample_quote_id, sample_approver_id):
        """Test criteria auto-check for passing margin."""
        context = QuoteApprovalContext(
            quote_id=sample_quote_id,
            quote_number="Q-001",
            version=1,
            customer_name="Customer",
            total_value=10000.0,
            margin_percent=25.0,  # Above 15% threshold
            line_item_count=3,
        )
        
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=context,
        )
        
        margin_criterion = next(c for c in session.criteria if c.id == "margin_check")
        assert margin_criterion.status == ApprovalCriterionStatus.PASSED
    
    def test_criteria_auto_check_margin_failed(self, service, sample_quote_id, sample_approver_id):
        """Test criteria auto-check for failing margin."""
        context = QuoteApprovalContext(
            quote_id=sample_quote_id,
            quote_number="Q-001",
            version=1,
            customer_name="Customer",
            total_value=10000.0,
            margin_percent=10.0,  # Below 15% threshold
            line_item_count=3,
        )
        
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=context,
        )
        
        margin_criterion = next(c for c in session.criteria if c.id == "margin_check")
        assert margin_criterion.status == ApprovalCriterionStatus.FAILED
    
    def test_update_criterion(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test updating a criterion."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        updated = service.update_criterion(
            session_id=session.id,
            criterion_id="authority_level",
            status=ApprovalCriterionStatus.PASSED,
            message="Within authority",
        )
        
        assert updated.status == ApprovalSessionStatus.REVIEWING
        criterion = next(c for c in updated.criteria if c.id == "authority_level")
        assert criterion.status == ApprovalCriterionStatus.PASSED
    
    def test_make_decision_approved(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test approving a quote."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        decided = service.make_decision(
            session_id=session.id,
            decision=ApprovalDecision.APPROVED,
            reason=ApprovalReason.WITHIN_AUTHORITY,
            comments="Looks good",
        )
        
        assert decided.status == ApprovalSessionStatus.DECIDED
        assert decided.decision == ApprovalDecision.APPROVED
        assert decided.completed_at is not None
    
    def test_make_decision_rejected(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test rejecting a quote."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        decided = service.make_decision(
            session_id=session.id,
            decision=ApprovalDecision.REJECTED,
            reason=ApprovalReason.MARGIN_TOO_LOW,
            comments="Margin insufficient",
        )
        
        assert decided.decision == ApprovalDecision.REJECTED
    
    def test_make_decision_escalated(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test escalating a quote."""
        escalate_to = uuid4()
        
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        decided = service.make_decision(
            session_id=session.id,
            decision=ApprovalDecision.ESCALATED,
            reason=ApprovalReason.ABOVE_THRESHOLD,
            escalated_to=escalate_to,
        )
        
        assert decided.decision == ApprovalDecision.ESCALATED
        assert decided.escalated_to == escalate_to
    
    def test_quick_approve(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test quick approval."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        decided = service.quick_approve(
            session_id=session.id,
            option_id="quick_approve",
        )
        
        assert decided.decision == ApprovalDecision.APPROVED
        assert decided.reason == ApprovalReason.WITHIN_AUTHORITY
    
    def test_quick_approve_requires_comment(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test quick approval that requires comment."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        # Should fail without comment
        result = service.quick_approve(
            session_id=session.id,
            option_id="reject_margin",
        )
        
        assert result is None
        
        # Should succeed with comment
        result = service.quick_approve(
            session_id=session.id,
            option_id="reject_margin",
            comments="Margin below threshold",
        )
        
        assert result.decision == ApprovalDecision.REJECTED
    
    def test_abandon_session(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test abandoning a session."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        abandoned = service.abandon_session(
            session_id=session.id,
            reason="Interrupted",
        )
        
        assert abandoned.status == ApprovalSessionStatus.ABANDONED
    
    def test_get_session(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test getting a session by ID."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        retrieved = service.get_session(session.id)
        
        assert retrieved.id == session.id
    
    def test_get_session_not_found(self, service):
        """Test getting non-existent session."""
        result = service.get_session(uuid4())
        
        assert result is None
    
    def test_get_active_session(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test getting active session."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        active = service.get_active_session(sample_quote_id, sample_approver_id)
        
        assert active.id == session.id
    
    def test_get_quote_sessions(self, service, sample_quote_id, sample_context):
        """Test getting all sessions for a quote."""
        approver1 = uuid4()
        approver2 = uuid4()
        
        service.start_approval_session(sample_quote_id, approver1, sample_context)
        service.start_approval_session(sample_quote_id, approver2, sample_context)
        
        sessions = service.get_quote_sessions(sample_quote_id)
        
        assert len(sessions) == 2
    
    def test_get_approver_pending(self, service, sample_approver_id):
        """Test getting pending sessions for an approver."""
        for _ in range(3):
            context = QuoteApprovalContext(
                quote_id=uuid4(),
                quote_number="Q-001",
                version=1,
                customer_name="Customer",
                total_value=10000.0,
                margin_percent=20.0,
                line_item_count=3,
            )
            service.start_approval_session(context.quote_id, sample_approver_id, context)
        
        pending = service.get_approver_pending(sample_approver_id)
        
        assert len(pending) == 3


class TestQuoteApprovalServiceMonitoring:
    """Tests for real-time monitoring."""
    
    def test_check_session_countdown(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test countdown status check."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        status = service.check_session_countdown(session.id)
        
        assert status["session_id"] == str(session.id)
        assert "elapsed_seconds" in status
        assert "remaining_seconds" in status
        assert status["target_seconds"] == 60
        assert status["status"] == "on_track"
    
    def test_check_countdown_not_found(self, service):
        """Test countdown for non-existent session."""
        result = service.check_session_countdown(uuid4())
        
        assert "error" in result
    
    def test_add_alert_listener(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test alert listener."""
        alerts_received = []
        
        def listener(alert):
            alerts_received.append(alert)
        
        service.add_alert_listener(listener)
        
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        # Force create an alert
        service._create_alert(session, "warning", 45, "Test alert")
        
        assert len(alerts_received) == 1
    
    def test_remove_alert_listener(self, service):
        """Test removing alert listener."""
        def listener(alert):
            pass
        
        service.add_alert_listener(listener)
        service.remove_alert_listener(listener)
        
        assert listener not in service._listeners


class TestQuoteApprovalServiceQuickOptions:
    """Tests for quick approval options."""
    
    def test_get_quick_options(self, service):
        """Test getting quick options."""
        options = service.get_quick_options()
        
        assert len(options) >= 4
    
    def test_add_quick_option(self, service):
        """Test adding custom quick option."""
        custom = QuickApprovalOption(
            id="custom_approve",
            label="Custom Approve",
            decision=ApprovalDecision.APPROVED,
            reason=ApprovalReason.CUSTOMER_RELATIONSHIP,
            icon="heart",
            color="purple",
        )
        
        service.add_quick_option(custom)
        options = service.get_quick_options()
        
        assert any(o.id == "custom_approve" for o in options)


class TestQuoteApprovalServiceAnalytics:
    """Tests for analytics."""
    
    def test_get_approver_performance_no_data(self, service):
        """Test performance with no data."""
        result = service.get_approver_performance(uuid4())
        
        assert result is None
    
    def test_get_approver_performance_with_data(self, service, sample_approver_id):
        """Test performance with data."""
        # Create and complete sessions
        for i in range(5):
            context = QuoteApprovalContext(
                quote_id=uuid4(),
                quote_number=f"Q-{i}",
                version=1,
                customer_name="Customer",
                total_value=10000.0,
                margin_percent=20.0,
                line_item_count=3,
            )
            session = service.start_approval_session(
                context.quote_id, sample_approver_id, context
            )
            service.make_decision(
                session_id=session.id,
                decision=ApprovalDecision.APPROVED,
                reason=ApprovalReason.WITHIN_AUTHORITY,
            )
        
        perf = service.get_approver_performance(sample_approver_id)
        
        assert perf is not None
        assert perf.total_approvals == 5
        assert perf.approval_rate == 100.0
    
    def test_get_quote_approval_summary(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test quote approval summary."""
        session = service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        service.make_decision(
            session_id=session.id,
            decision=ApprovalDecision.APPROVED,
        )
        
        summary = service.get_quote_approval_summary(sample_quote_id)
        
        assert summary["quote_id"] == str(sample_quote_id)
        assert summary["total_sessions"] == 1
        assert summary["final_decision"] == "approved"
    
    def test_get_approval_leaderboard(self, service):
        """Test approval leaderboard."""
        # Create approvals for multiple approvers
        for i in range(3):
            approver_id = uuid4()
            for j in range(i + 1):
                context = QuoteApprovalContext(
                    quote_id=uuid4(),
                    quote_number=f"Q-{i}-{j}",
                    version=1,
                    customer_name="Customer",
                    total_value=10000.0,
                    margin_percent=20.0,
                    line_item_count=3,
                )
                session = service.start_approval_session(
                    context.quote_id, approver_id, context
                )
                service.make_decision(
                    session_id=session.id,
                    decision=ApprovalDecision.APPROVED,
                )
        
        leaderboard = service.get_approval_leaderboard()
        
        assert len(leaderboard) == 3
        assert leaderboard[0]["rank"] == 1


class TestQuoteApprovalServiceConfiguration:
    """Tests for configuration."""
    
    def test_get_target(self, service):
        """Test getting targets."""
        target = service.get_target()
        
        assert target["target_seconds"] == 60
        assert target["warning_seconds"] == 45
        assert target["critical_seconds"] == 55
    
    def test_set_target(self, service):
        """Test setting targets."""
        service.set_target(
            target_seconds=30,
            warning_seconds=20,
            critical_seconds=25,
        )
        
        target = service.get_target()
        
        assert target["target_seconds"] == 30
        assert target["warning_seconds"] == 20
    
    def test_reset(self, service, sample_quote_id, sample_approver_id, sample_context):
        """Test reset clears all data."""
        service.start_approval_session(
            quote_id=sample_quote_id,
            approver_id=sample_approver_id,
            context=sample_context,
        )
        
        service.reset()
        
        assert len(service._sessions) == 0


class TestApproverPerformance:
    """Tests for ApproverPerformance."""
    
    def test_target_compliance_rate(self):
        """Test target compliance rate calculation."""
        perf = ApproverPerformance(
            approver_id=uuid4(),
            period_start=datetime.now(timezone.utc) - timedelta(days=30),
            period_end=datetime.now(timezone.utc),
            total_approvals=10,
            approvals_within_target=8,
            approvals_over_target=2,
            average_time_seconds=45.0,
            median_time_seconds=42.0,
            min_time_seconds=20,
            max_time_seconds=90,
            approval_rate=80.0,
            delegation_rate=5.0,
            escalation_rate=10.0,
        )
        
        assert perf.target_compliance_rate == 80.0
    
    def test_to_dict(self):
        """Test performance to_dict conversion."""
        perf = ApproverPerformance(
            approver_id=uuid4(),
            period_start=datetime.now(timezone.utc) - timedelta(days=30),
            period_end=datetime.now(timezone.utc),
            total_approvals=10,
            approvals_within_target=8,
            approvals_over_target=2,
            average_time_seconds=45.5,
            median_time_seconds=42.0,
            min_time_seconds=20,
            max_time_seconds=90,
            approval_rate=80.0,
            delegation_rate=5.0,
            escalation_rate=10.0,
        )
        
        result = perf.to_dict()
        
        assert result["total_approvals"] == 10
        assert result["average_time_seconds"] == 45.5


class TestSingletonPattern:
    """Tests for singleton pattern."""
    
    def test_get_service_instance(self):
        """Test getting singleton instance."""
        reset_quote_approval_service()
        
        instance1 = get_quote_approval_service()
        instance2 = get_quote_approval_service()
        
        assert instance1 is instance2
    
    def test_reset_service_instance(self):
        """Test resetting singleton."""
        instance1 = get_quote_approval_service()
        reset_quote_approval_service()
        instance2 = get_quote_approval_service()
        
        assert instance1 is not instance2

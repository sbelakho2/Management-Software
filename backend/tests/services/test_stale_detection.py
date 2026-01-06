"""
Tests for the Stale Detection Service.

Tests cover:
- StaleThreshold configuration
- StaleDetectionService for opportunities, RFQs, and tasks
- Severity escalation logic
- Job runner and callbacks
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from sensei.services.stale_detection import (
    EntityType,
    StaleSeverity,
    StaleReason,
    StaleThreshold,
    StaleEntity,
    StaleDetectionResult,
    StaleDetectionService,
    StaleDetectionJobRunner,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def stale_service():
    """Create a default StaleDetectionService instance."""
    return StaleDetectionService()


@pytest.fixture
def reference_time():
    """Fixed reference time for testing."""
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_opportunities(reference_time):
    """Sample opportunity data for testing."""
    return [
        {
            "id": uuid4(),
            "name": "Big Deal Corp",
            "opportunity_number": "OPP-001",
            "stage": "prospecting",
            "updated_at": reference_time - timedelta(days=10),  # 10 days old - stale
            "owner_id": uuid4(),
            "owner_name": "John Sales",
            "account_name": "Big Deal Corp",
            "amount": 100000,
            "probability": 25,
            "next_step": "Schedule demo",
            "next_step_date": reference_time + timedelta(days=5),
        },
        {
            "id": uuid4(),
            "name": "Fresh Lead Inc",
            "opportunity_number": "OPP-002",
            "stage": "qualification",
            "updated_at": reference_time - timedelta(days=1),  # 1 day old - not stale
            "owner_id": uuid4(),
            "owner_name": "Jane Sales",
            "account_name": "Fresh Lead Inc",
            "next_step": "Send proposal",
            "next_step_date": reference_time + timedelta(days=3),
        },
        {
            "id": uuid4(),
            "name": "Closed Won Customer",
            "opportunity_number": "OPP-003",
            "stage": "closed_won",
            "updated_at": reference_time - timedelta(days=30),  # Old but closed - excluded
            "owner_id": uuid4(),
            "owner_name": "John Sales",
            "account_name": "Closed Won Customer",
        },
        {
            "id": uuid4(),
            "name": "Stale Proposal",
            "opportunity_number": "OPP-004",
            "stage": "proposal",
            "updated_at": reference_time - timedelta(days=15),  # 15 days in proposal - very stale
            "owner_id": uuid4(),
            "owner_name": "Jane Sales",
            "account_name": "Stale Proposal Corp",
            "amount": 50000,
            "next_step": "Waiting for customer decision",  # Has next step to test proposal threshold
            "next_step_date": reference_time + timedelta(days=5),  # Not overdue
        },
        {
            "id": uuid4(),
            "name": "No Next Step",
            "opportunity_number": "OPP-005",
            "stage": "qualification",
            "updated_at": reference_time - timedelta(days=5),  # 5 days without next step
            "owner_id": uuid4(),
            "owner_name": "John Sales",
            "account_name": "No Next Step Inc",
            "next_step": None,  # Missing next step
            "next_step_date": None,
        },
        {
            "id": uuid4(),
            "name": "Overdue Next Step",
            "opportunity_number": "OPP-006",
            "stage": "negotiation",
            "updated_at": reference_time - timedelta(days=2),
            "owner_id": uuid4(),
            "owner_name": "Jane Sales",
            "account_name": "Overdue Corp",
            "next_step": "Send contract",
            "next_step_date": reference_time - timedelta(days=3),  # 3 days overdue
        },
    ]


@pytest.fixture
def sample_rfqs(reference_time):
    """Sample RFQ data for testing."""
    return [
        {
            "id": uuid4(),
            "rfq_number": "RFQ-001",
            "status": "received",
            "updated_at": reference_time - timedelta(days=5),  # 5 days in received - stale
            "owner_id": uuid4(),
            "owner_name": "Estimator A",
            "account_name": "Customer A",
            "due_date": reference_time + timedelta(days=10),
            "priority": "high",
        },
        {
            "id": uuid4(),
            "rfq_number": "RFQ-002",
            "status": "qualifying",
            "updated_at": reference_time - timedelta(days=1),  # 1 day - not stale
            "owner_id": uuid4(),
            "owner_name": "Estimator B",
            "account_name": "Customer B",
        },
        {
            "id": uuid4(),
            "rfq_number": "RFQ-003",
            "status": "won",
            "updated_at": reference_time - timedelta(days=60),  # Old but won - excluded
            "owner_id": uuid4(),
            "owner_name": "Estimator A",
            "account_name": "Customer C",
        },
        {
            "id": uuid4(),
            "rfq_number": "RFQ-004",
            "status": "questions_pending",
            "updated_at": reference_time - timedelta(days=10),  # 10 days waiting - very stale
            "owner_id": uuid4(),
            "owner_name": "Estimator C",
            "account_name": "Customer D",
        },
        {
            "id": uuid4(),
            "rfq_number": "RFQ-005",
            "status": "quoting",
            "updated_at": reference_time - timedelta(days=20),  # 20 days quoting - critical
            "owner_id": uuid4(),
            "owner_name": "Estimator A",
            "account_name": "Customer E",
            "quote_due_date": reference_time - timedelta(days=5),  # Quote overdue
        },
    ]


@pytest.fixture
def sample_tasks(reference_time):
    """Sample task data for testing."""
    return [
        {
            "id": uuid4(),
            "title": "Call customer",
            "status": "todo",
            "updated_at": reference_time - timedelta(days=10),  # 10 days todo - stale
            "assignee_id": uuid4(),
            "assignee_name": "John Smith",
            "due_date": reference_time + timedelta(days=5),
            "priority": "medium",
            "task_type": "call",
        },
        {
            "id": uuid4(),
            "title": "Review quote",
            "status": "in_progress",
            "updated_at": reference_time - timedelta(days=1),  # 1 day - not stale
            "assignee_id": uuid4(),
            "assignee_name": "Jane Doe",
        },
        {
            "id": uuid4(),
            "title": "Completed task",
            "status": "done",
            "updated_at": reference_time - timedelta(days=30),  # Old but done - excluded
            "assignee_id": uuid4(),
            "assignee_name": "John Smith",
        },
        {
            "id": uuid4(),
            "title": "Blocked task",
            "status": "blocked",
            "updated_at": reference_time - timedelta(days=8),  # 8 days blocked - critical
            "assignee_id": uuid4(),
            "assignee_name": "Jane Doe",
        },
        {
            "id": uuid4(),
            "title": "Overdue task",
            "status": "in_progress",
            "updated_at": reference_time - timedelta(days=1),
            "assignee_id": uuid4(),
            "assignee_name": "John Smith",
            "due_date": reference_time - timedelta(days=5),  # 5 days overdue
        },
        {
            "id": uuid4(),
            "title": "In review too long",
            "status": "in_review",
            "updated_at": reference_time - timedelta(days=6),  # 6 days in review - high severity
            "assignee_id": uuid4(),
            "assignee_name": "Reviewer X",
        },
    ]


# =============================================================================
# StaleThreshold Tests
# =============================================================================


class TestStaleThreshold:
    """Tests for StaleThreshold configuration."""
    
    def test_threshold_creation_basic(self):
        """Test basic threshold creation."""
        threshold = StaleThreshold(days_until_stale=5)
        
        assert threshold.days_until_stale == 5
        assert threshold.severity_escalation_days == 7
        assert threshold.applies_to_statuses is None
        assert threshold.excluded_statuses == []
        assert threshold.reason == StaleReason.NO_ACTIVITY
    
    def test_threshold_creation_full(self):
        """Test threshold creation with all fields."""
        threshold = StaleThreshold(
            days_until_stale=3,
            severity_escalation_days=2,
            applies_to_statuses=["draft", "received"],
            excluded_statuses=["cancelled"],
            reason=StaleReason.STUCK_IN_STATUS,
        )
        
        assert threshold.days_until_stale == 3
        assert threshold.severity_escalation_days == 2
        assert threshold.applies_to_statuses == ["draft", "received"]
        assert threshold.excluded_statuses == ["cancelled"]
        assert threshold.reason == StaleReason.STUCK_IN_STATUS


# =============================================================================
# StaleEntity Tests
# =============================================================================


class TestStaleEntity:
    """Tests for StaleEntity dataclass."""
    
    def test_stale_entity_creation(self):
        """Test creating a stale entity."""
        entity_id = uuid4()
        owner_id = uuid4()
        last_activity = datetime.now()
        
        entity = StaleEntity(
            entity_id=entity_id,
            entity_type=EntityType.OPPORTUNITY,
            entity_name="Test Opportunity",
            reason=StaleReason.NO_ACTIVITY,
            severity=StaleSeverity.MEDIUM,
            days_stale=5,
            last_activity_at=last_activity,
            status="prospecting",
            owner_id=owner_id,
            owner_name="Test User",
            account_name="Test Account",
            suggested_action="Review opportunity",
        )
        
        assert entity.entity_id == entity_id
        assert entity.entity_type == EntityType.OPPORTUNITY
        assert entity.entity_name == "Test Opportunity"
        assert entity.reason == StaleReason.NO_ACTIVITY
        assert entity.severity == StaleSeverity.MEDIUM
        assert entity.days_stale == 5
        assert entity.owner_id == owner_id
    
    def test_stale_entity_metadata(self):
        """Test stale entity with metadata."""
        entity = StaleEntity(
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            reason=StaleReason.WAITING_TOO_LONG,
            severity=StaleSeverity.HIGH,
            days_stale=10,
            last_activity_at=datetime.now(),
            status="questions_pending",
            metadata={"priority": "high", "customer": "Acme Corp"},
        )
        
        assert entity.metadata["priority"] == "high"
        assert entity.metadata["customer"] == "Acme Corp"


# =============================================================================
# StaleDetectionResult Tests
# =============================================================================


class TestStaleDetectionResult:
    """Tests for StaleDetectionResult."""
    
    def test_result_by_severity(self):
        """Test grouping results by severity."""
        entities = [
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="Low",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.LOW,
                days_stale=1,
                last_activity_at=datetime.now(),
                status="prospecting",
            ),
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="High 1",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.HIGH,
                days_stale=15,
                last_activity_at=datetime.now(),
                status="proposal",
            ),
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="High 2",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.HIGH,
                days_stale=16,
                last_activity_at=datetime.now(),
                status="proposal",
            ),
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="Critical",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.CRITICAL,
                days_stale=30,
                last_activity_at=datetime.now(),
                status="negotiation",
            ),
        ]
        
        result = StaleDetectionResult(
            scanned_at=datetime.now(),
            entity_type=EntityType.OPPORTUNITY,
            total_scanned=10,
            stale_count=4,
            stale_entities=entities,
            thresholds_used={},
        )
        
        by_severity = result.by_severity
        
        assert len(by_severity[StaleSeverity.LOW]) == 1
        assert len(by_severity[StaleSeverity.MEDIUM]) == 0
        assert len(by_severity[StaleSeverity.HIGH]) == 2
        assert len(by_severity[StaleSeverity.CRITICAL]) == 1
    
    def test_result_counts(self):
        """Test critical and high counts."""
        entities = [
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="Critical 1",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.CRITICAL,
                days_stale=30,
                last_activity_at=datetime.now(),
                status="negotiation",
            ),
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="Critical 2",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.CRITICAL,
                days_stale=35,
                last_activity_at=datetime.now(),
                status="negotiation",
            ),
            StaleEntity(
                entity_id=uuid4(),
                entity_type=EntityType.OPPORTUNITY,
                entity_name="High",
                reason=StaleReason.NO_ACTIVITY,
                severity=StaleSeverity.HIGH,
                days_stale=20,
                last_activity_at=datetime.now(),
                status="proposal",
            ),
        ]
        
        result = StaleDetectionResult(
            scanned_at=datetime.now(),
            entity_type=EntityType.OPPORTUNITY,
            total_scanned=50,
            stale_count=3,
            stale_entities=entities,
            thresholds_used={},
        )
        
        assert result.critical_count == 2
        assert result.high_count == 1


# =============================================================================
# StaleDetectionService - Opportunity Tests
# =============================================================================


class TestStaleDetectionServiceOpportunities:
    """Tests for detecting stale opportunities."""
    
    def test_detect_stale_opportunities_basic(self, stale_service, sample_opportunities, reference_time):
        """Test basic stale opportunity detection."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        assert result.entity_type == EntityType.OPPORTUNITY
        assert result.total_scanned == 6
        assert result.stale_count >= 1  # At least OPP-001 should be stale
    
    def test_detect_excludes_closed_opportunities(self, stale_service, sample_opportunities, reference_time):
        """Test that closed opportunities are excluded."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-003 (closed_won) should not be in stale list
        stale_names = [e.entity_name for e in result.stale_entities]
        assert "Closed Won Customer" not in stale_names
    
    def test_detect_fresh_opportunity_not_stale(self, stale_service, sample_opportunities, reference_time):
        """Test that fresh opportunities are not marked stale."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-002 (1 day old in qualification) should not be stale
        stale_names = [e.entity_name for e in result.stale_entities]
        assert "Fresh Lead Inc" not in stale_names
    
    def test_detect_stale_opportunity_in_prospecting(self, stale_service, sample_opportunities, reference_time):
        """Test detecting stale opportunity in prospecting stage."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-001 (10 days in prospecting, threshold is 5) should be stale
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Big Deal Corp"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "prospecting"
        assert stale_entity.days_stale >= 5  # At least 5 days beyond threshold
    
    def test_detect_very_stale_proposal(self, stale_service, sample_opportunities, reference_time):
        """Test detecting very stale opportunity in proposal stage."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-004 (15 days in proposal, threshold is 5) should be stale with high severity
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Stale Proposal"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "proposal"
        assert stale_entity.severity in (StaleSeverity.MEDIUM, StaleSeverity.HIGH)
    
    def test_detect_no_next_step_opportunity(self, stale_service, sample_opportunities, reference_time):
        """Test detecting opportunity with no next step."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-005 has no next step
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "No Next Step"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.reason == StaleReason.NO_NEXT_STEP
    
    def test_detect_overdue_next_step(self, stale_service, sample_opportunities, reference_time):
        """Test detecting opportunity with overdue next step."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-006 has overdue next step
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Overdue Next Step"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.reason == StaleReason.NEXT_STEP_OVERDUE
    
    def test_severity_escalation(self, stale_service, reference_time):
        """Test severity increases over time."""
        # Create opportunities at different staleness levels
        # Prospecting threshold: 5 days, escalation: 5 days
        # Adding next_step to avoid triggering NO_NEXT_STEP (3-day threshold)
        opportunities = [
            {
                "id": uuid4(),
                "name": "Just Stale",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=6),  # 1 day over 5-day threshold = LOW
                "next_step": "Call customer",
                "next_step_date": reference_time + timedelta(days=5),
            },
            {
                "id": uuid4(),
                "name": "Medium Stale",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=12),  # 7 days over threshold = MEDIUM
                "next_step": "Call customer",
                "next_step_date": reference_time + timedelta(days=5),
            },
            {
                "id": uuid4(),
                "name": "Very Stale",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=18),  # 13 days over threshold = HIGH
                "next_step": "Call customer",
                "next_step_date": reference_time + timedelta(days=5),
            },
            {
                "id": uuid4(),
                "name": "Critical Stale",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=25),  # 20 days over threshold = CRITICAL
                "next_step": "Call customer",
                "next_step_date": reference_time + timedelta(days=5),
            },
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        # Check severity escalation
        just_stale = next((e for e in result.stale_entities if e.entity_name == "Just Stale"), None)
        medium_stale = next((e for e in result.stale_entities if e.entity_name == "Medium Stale"), None)
        very_stale = next((e for e in result.stale_entities if e.entity_name == "Very Stale"), None)
        critical_stale = next((e for e in result.stale_entities if e.entity_name == "Critical Stale"), None)
        
        assert just_stale.severity == StaleSeverity.LOW
        assert medium_stale.severity == StaleSeverity.MEDIUM
        assert very_stale.severity == StaleSeverity.HIGH
        assert critical_stale.severity == StaleSeverity.CRITICAL
    
    def test_suggested_action_included(self, stale_service, sample_opportunities, reference_time):
        """Test that suggested actions are provided."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        for entity in result.stale_entities:
            assert entity.suggested_action is not None
            assert len(entity.suggested_action) > 0
    
    def test_metadata_captured(self, stale_service, sample_opportunities, reference_time):
        """Test that opportunity metadata is captured."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        # OPP-001 should have metadata
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Big Deal Corp"),
            None
        )
        
        if stale_entity:
            assert "opportunity_number" in stale_entity.metadata
            assert stale_entity.metadata["opportunity_number"] == "OPP-001"
    
    def test_empty_opportunities_list(self, stale_service, reference_time):
        """Test with empty opportunities list."""
        result = stale_service.detect_stale_opportunities([], reference_time)
        
        assert result.total_scanned == 0
        assert result.stale_count == 0
        assert len(result.stale_entities) == 0
    
    def test_scan_duration_tracked(self, stale_service, sample_opportunities, reference_time):
        """Test that scan duration is tracked."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        assert result.scan_duration_ms >= 0


# =============================================================================
# StaleDetectionService - RFQ Tests
# =============================================================================


class TestStaleDetectionServiceRFQs:
    """Tests for detecting stale RFQs."""
    
    def test_detect_stale_rfqs_basic(self, stale_service, sample_rfqs, reference_time):
        """Test basic stale RFQ detection."""
        result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        
        assert result.entity_type == EntityType.RFQ
        assert result.total_scanned == 5
        assert result.stale_count >= 1
    
    def test_detect_excludes_closed_rfqs(self, stale_service, sample_rfqs, reference_time):
        """Test that won/lost/cancelled RFQs are excluded."""
        result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        
        # RFQ-003 (won) should not be in stale list
        stale_numbers = [e.entity_name for e in result.stale_entities]
        assert "RFQ-003" not in stale_numbers
    
    def test_detect_stale_received_rfq(self, stale_service, sample_rfqs, reference_time):
        """Test detecting stale RFQ in received status."""
        result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        
        # RFQ-001 (5 days in received, threshold is 2) should be stale
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "RFQ-001"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "received"
        assert stale_entity.days_stale >= 3  # 5 - 2 = 3 days beyond threshold
    
    def test_detect_stale_questions_pending(self, stale_service, sample_rfqs, reference_time):
        """Test detecting RFQ waiting too long for questions."""
        result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        
        # RFQ-004 (10 days in questions_pending)
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "RFQ-004"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "questions_pending"
        assert stale_entity.reason == StaleReason.WAITING_TOO_LONG
    
    def test_detect_critical_quoting_rfq(self, stale_service, sample_rfqs, reference_time):
        """Test detecting critically stale RFQ in quoting."""
        result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        
        # RFQ-005 (20 days in quoting, threshold is 7) should be very stale
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "RFQ-005"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "quoting"
        assert stale_entity.severity in (StaleSeverity.HIGH, StaleSeverity.CRITICAL)
    
    def test_fresh_rfq_not_stale(self, stale_service, sample_rfqs, reference_time):
        """Test that fresh RFQs are not marked stale."""
        result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        
        # RFQ-002 (1 day old) should not be stale
        stale_numbers = [e.entity_name for e in result.stale_entities]
        assert "RFQ-002" not in stale_numbers


# =============================================================================
# StaleDetectionService - Task Tests
# =============================================================================


class TestStaleDetectionServiceTasks:
    """Tests for detecting stale tasks."""
    
    def test_detect_stale_tasks_basic(self, stale_service, sample_tasks, reference_time):
        """Test basic stale task detection."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        assert result.entity_type == EntityType.TASK
        assert result.total_scanned == 6
        assert result.stale_count >= 1
    
    def test_detect_excludes_done_tasks(self, stale_service, sample_tasks, reference_time):
        """Test that done/cancelled tasks are excluded."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # Completed task should not be in stale list
        stale_titles = [e.entity_name for e in result.stale_entities]
        assert "Completed task" not in stale_titles
    
    def test_detect_stale_todo(self, stale_service, sample_tasks, reference_time):
        """Test detecting stale task in todo status."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # "Call customer" (10 days in todo, threshold is 7) should be stale
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Call customer"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "todo"
        assert stale_entity.days_stale >= 3  # 10 - 7 = 3 days beyond threshold
    
    def test_detect_blocked_task(self, stale_service, sample_tasks, reference_time):
        """Test detecting blocked task."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # Blocked task (8 days, threshold is 2) should be very stale
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Blocked task"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "blocked"
        assert stale_entity.reason == StaleReason.STUCK_IN_STATUS
        assert stale_entity.severity in (StaleSeverity.HIGH, StaleSeverity.CRITICAL)
    
    def test_detect_overdue_task(self, stale_service, sample_tasks, reference_time):
        """Test detecting overdue task."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # Overdue task should be detected
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "Overdue task"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.reason == StaleReason.OVERDUE
    
    def test_detect_in_review_too_long(self, stale_service, sample_tasks, reference_time):
        """Test detecting task in review too long."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # In review too long (6 days, threshold is 2)
        stale_entity = next(
            (e for e in result.stale_entities if e.entity_name == "In review too long"),
            None
        )
        
        assert stale_entity is not None
        assert stale_entity.status == "in_review"
        assert stale_entity.reason == StaleReason.WAITING_TOO_LONG
    
    def test_fresh_task_not_stale(self, stale_service, sample_tasks, reference_time):
        """Test that fresh tasks are not marked stale."""
        result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # "Review quote" (1 day old) should not be stale
        stale_titles = [e.entity_name for e in result.stale_entities]
        assert "Review quote" not in stale_titles


# =============================================================================
# StaleDetectionService - Threshold Management Tests
# =============================================================================


class TestStaleDetectionServiceThresholds:
    """Tests for threshold management."""
    
    def test_get_opportunity_thresholds(self, stale_service):
        """Test getting opportunity thresholds."""
        thresholds = stale_service.get_thresholds(EntityType.OPPORTUNITY)
        
        assert "default" in thresholds
        assert "prospecting" in thresholds
        assert "qualification" in thresholds
        assert thresholds["prospecting"].days_until_stale == 5
    
    def test_get_rfq_thresholds(self, stale_service):
        """Test getting RFQ thresholds."""
        thresholds = stale_service.get_thresholds(EntityType.RFQ)
        
        assert "default" in thresholds
        assert "received" in thresholds
        assert thresholds["received"].days_until_stale == 2
    
    def test_get_task_thresholds(self, stale_service):
        """Test getting task thresholds."""
        thresholds = stale_service.get_thresholds(EntityType.TASK)
        
        assert "default" in thresholds
        assert "blocked" in thresholds
        assert thresholds["blocked"].days_until_stale == 2
    
    def test_update_threshold(self, stale_service):
        """Test updating a threshold."""
        new_threshold = StaleThreshold(
            days_until_stale=1,
            severity_escalation_days=1,
            reason=StaleReason.STUCK_IN_STATUS,
        )
        
        stale_service.update_threshold(EntityType.OPPORTUNITY, "prospecting", new_threshold)
        
        thresholds = stale_service.get_thresholds(EntityType.OPPORTUNITY)
        assert thresholds["prospecting"].days_until_stale == 1
    
    def test_custom_thresholds_in_constructor(self):
        """Test providing custom thresholds in constructor."""
        custom_opp_thresholds = {
            "default": StaleThreshold(days_until_stale=1),
        }
        
        service = StaleDetectionService(opportunity_thresholds=custom_opp_thresholds)
        
        thresholds = service.get_thresholds(EntityType.OPPORTUNITY)
        assert thresholds["default"].days_until_stale == 1
        # Other thresholds should not be present
        assert "prospecting" not in thresholds
    
    def test_invalid_entity_type_raises(self, stale_service):
        """Test that invalid entity type raises error."""
        with pytest.raises(ValueError):
            stale_service.get_thresholds("invalid")


# =============================================================================
# StaleDetectionService - Edge Cases
# =============================================================================


class TestStaleDetectionServiceEdgeCases:
    """Tests for edge cases in stale detection."""
    
    def test_handles_string_uuid(self, stale_service, reference_time):
        """Test handling string UUIDs."""
        entity_id = str(uuid4())
        opportunities = [
            {
                "id": entity_id,  # String instead of UUID
                "name": "Test",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=10),
            }
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        assert result.stale_count == 1
        # Should have converted to UUID
        assert isinstance(result.stale_entities[0].entity_id, type(uuid4()))
    
    def test_handles_iso_string_datetime(self, stale_service, reference_time):
        """Test handling ISO string datetimes."""
        opportunities = [
            {
                "id": uuid4(),
                "name": "Test",
                "stage": "prospecting",
                "updated_at": (reference_time - timedelta(days=10)).isoformat(),  # String
            }
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        assert result.stale_count == 1
    
    def test_handles_missing_id(self, stale_service, reference_time):
        """Test that entities without ID are skipped."""
        opportunities = [
            {
                "name": "No ID",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=10),
            }
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        assert result.total_scanned == 1
        assert result.stale_count == 0
    
    def test_handles_missing_updated_at(self, stale_service, reference_time):
        """Test that entities without updated_at are skipped."""
        opportunities = [
            {
                "id": uuid4(),
                "name": "No Date",
                "stage": "prospecting",
            }
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        assert result.total_scanned == 1
        assert result.stale_count == 0
    
    def test_uses_current_time_as_default(self, stale_service):
        """Test that current time is used when reference_time not provided."""
        opportunities = [
            {
                "id": uuid4(),
                "name": "Test",
                "stage": "prospecting",
                "updated_at": datetime.now() - timedelta(days=100),
            }
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities)
        
        assert result.stale_count == 1
        # scanned_at should be close to now
        assert (datetime.now() - result.scanned_at).total_seconds() < 5
    
    def test_handles_unknown_status(self, stale_service, reference_time):
        """Test handling unknown status uses default threshold."""
        opportunities = [
            {
                "id": uuid4(),
                "name": "Unknown Status",
                "stage": "some_weird_status",
                "updated_at": reference_time - timedelta(days=15),
            }
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        # Should use default threshold (7 days)
        assert result.stale_count == 1


# =============================================================================
# StaleDetectionJobRunner Tests
# =============================================================================


class TestStaleDetectionJobRunner:
    """Tests for the job runner."""
    
    @pytest.fixture
    def job_runner(self):
        """Create a job runner instance."""
        return StaleDetectionJobRunner()
    
    @pytest.fixture
    def mock_callbacks(self):
        """Create mock callbacks for task/notification creation."""
        created_tasks = []
        created_notifications = []
        
        async def create_task(data):
            created_tasks.append(data)
            return {"id": str(uuid4()), **data}
        
        async def create_notification(data):
            created_notifications.append(data)
            return {"id": str(uuid4()), **data}
        
        return create_task, create_notification, created_tasks, created_notifications
    
    @pytest.mark.asyncio
    async def test_run_full_scan(self, job_runner, sample_opportunities, sample_rfqs, sample_tasks, reference_time):
        """Test running a full scan across all entity types."""
        results = await job_runner.run_full_scan(
            opportunities=sample_opportunities,
            rfqs=sample_rfqs,
            tasks=sample_tasks,
            reference_time=reference_time,
            create_follow_up_tasks=False,
            send_notifications=False,
        )
        
        assert EntityType.OPPORTUNITY in results
        assert EntityType.RFQ in results
        assert EntityType.TASK in results
    
    @pytest.mark.asyncio
    async def test_run_full_scan_with_callbacks(
        self,
        sample_opportunities,
        sample_rfqs,
        sample_tasks,
        reference_time,
        mock_callbacks,
    ):
        """Test running a full scan with callbacks."""
        create_task, create_notification, created_tasks, created_notifications = mock_callbacks
        
        runner = StaleDetectionJobRunner(
            create_task_callback=create_task,
            create_notification_callback=create_notification,
        )
        
        await runner.run_full_scan(
            opportunities=sample_opportunities,
            rfqs=sample_rfqs,
            tasks=sample_tasks,
            reference_time=reference_time,
            create_follow_up_tasks=True,
            send_notifications=True,
            min_severity_for_task=StaleSeverity.MEDIUM,
            min_severity_for_notification=StaleSeverity.HIGH,
        )
        
        # Should have created tasks for medium+ severity
        assert len(created_tasks) > 0
        
        # Tasks should have [STALE] prefix
        for task in created_tasks:
            assert task["title"].startswith("[STALE]")
    
    def test_get_summary(self, job_runner, sample_opportunities, sample_rfqs, sample_tasks, reference_time):
        """Test generating a summary of results."""
        # First run detection
        opp_result = job_runner.service.detect_stale_opportunities(sample_opportunities, reference_time)
        rfq_result = job_runner.service.detect_stale_rfqs(sample_rfqs, reference_time)
        task_result = job_runner.service.detect_stale_tasks(sample_tasks, reference_time)
        
        results = {
            EntityType.OPPORTUNITY: opp_result,
            EntityType.RFQ: rfq_result,
            EntityType.TASK: task_result,
        }
        
        summary = job_runner.get_summary(results)
        
        assert "total_scanned" in summary
        assert "total_stale" in summary
        assert "total_critical" in summary
        assert "total_high" in summary
        assert "by_entity_type" in summary
        assert "requires_immediate_attention" in summary
        
        # Verify counts are aggregated
        assert summary["total_scanned"] == opp_result.total_scanned + rfq_result.total_scanned + task_result.total_scanned
        assert summary["total_stale"] == opp_result.stale_count + rfq_result.stale_count + task_result.stale_count
    
    @pytest.mark.asyncio
    async def test_follow_up_tasks_respect_min_severity(
        self,
        sample_opportunities,
        reference_time,
        mock_callbacks,
    ):
        """Test that follow-up tasks respect minimum severity."""
        create_task, _, created_tasks, _ = mock_callbacks
        
        runner = StaleDetectionJobRunner(
            create_task_callback=create_task,
        )
        
        # Only create tasks for CRITICAL severity
        await runner.run_full_scan(
            opportunities=sample_opportunities,
            rfqs=[],
            tasks=[],
            reference_time=reference_time,
            create_follow_up_tasks=True,
            send_notifications=False,
            min_severity_for_task=StaleSeverity.CRITICAL,
        )
        
        # Should only have tasks for critical severity entities
        # (If any, depends on sample data)
        for task in created_tasks:
            # Priority should be high for critical
            assert task["priority"] in ("high", "medium")


# =============================================================================
# Integration Tests
# =============================================================================


class TestStaleDetectionIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_detection_workflow(self, stale_service, sample_opportunities, sample_rfqs, sample_tasks, reference_time):
        """Test a complete detection workflow."""
        # Detect stale entities
        opp_result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        rfq_result = stale_service.detect_stale_rfqs(sample_rfqs, reference_time)
        task_result = stale_service.detect_stale_tasks(sample_tasks, reference_time)
        
        # Verify each result is valid
        for result in [opp_result, rfq_result, task_result]:
            assert result.scanned_at is not None
            assert result.total_scanned >= 0
            assert result.stale_count >= 0
            assert len(result.stale_entities) == result.stale_count
        
        # Verify stale entities have required fields
        all_stale = opp_result.stale_entities + rfq_result.stale_entities + task_result.stale_entities
        for entity in all_stale:
            assert entity.entity_id is not None
            assert entity.entity_type is not None
            assert entity.entity_name is not None
            assert entity.reason is not None
            assert entity.severity is not None
            assert entity.suggested_action is not None
    
    def test_different_thresholds_per_status(self, stale_service, reference_time):
        """Test that different statuses use appropriate thresholds."""
        opportunities = [
            {
                "id": uuid4(),
                "name": "Qualification (3 day threshold)",
                "stage": "qualification",
                "updated_at": reference_time - timedelta(days=4),  # 4 days = stale (threshold 3)
                "next_step": "Review customer needs",  # Include next_step to test status threshold
                "next_step_date": reference_time + timedelta(days=5),
            },
            {
                "id": uuid4(),
                "name": "Prospecting (5 day threshold)",
                "stage": "prospecting",
                "updated_at": reference_time - timedelta(days=4),  # 4 days = NOT stale (threshold 5)
                "next_step": "Call customer",  # Include next_step to test status threshold
                "next_step_date": reference_time + timedelta(days=5),
            },
        ]
        
        result = stale_service.detect_stale_opportunities(opportunities, reference_time)
        
        stale_names = [e.entity_name for e in result.stale_entities]
        
        # Qualification should be stale (4 > 3)
        assert "Qualification (3 day threshold)" in stale_names
        
        # Prospecting should NOT be stale (4 < 5)
        assert "Prospecting (5 day threshold)" not in stale_names
    
    def test_thresholds_in_result(self, stale_service, sample_opportunities, reference_time):
        """Test that thresholds used are included in result."""
        result = stale_service.detect_stale_opportunities(sample_opportunities, reference_time)
        
        assert result.thresholds_used is not None
        assert "default" in result.thresholds_used
        assert "prospecting" in result.thresholds_used
        
        # Verify threshold data structure
        for key, threshold_data in result.thresholds_used.items():
            assert "days" in threshold_data
            assert "reason" in threshold_data

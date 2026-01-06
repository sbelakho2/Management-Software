"""
Tests for the Escalation Policy Service.

Tests cover:
- Aging approval detection
- Value-based approval escalation
- High-severity risk detection
- Overdue risk detection
- Andon SLA breach detection
- Escalation levels and priorities
- Policy configuration
- Job runner functionality
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from sensei.services.escalation_policy import (
    EscalationPolicyService,
    EscalationJobRunner,
    EscalationPolicy,
    EscalationLevelConfig,
    EscalationItem,
    EscalationResult,
    EscalationTargetType,
    EscalationReason,
    EscalationLevel,
    EscalationStatus,
    EscalationPriority,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def service() -> EscalationPolicyService:
    """Create a fresh escalation policy service."""
    return EscalationPolicyService()


@pytest.fixture
def reference_time() -> datetime:
    """Standard reference time for tests."""
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_approval(reference_time: datetime) -> dict:
    """Create a sample approval for testing."""
    return {
        "id": uuid4(),
        "name": "Q-2025-001",
        "status": "pending",
        "value": Decimal("75000"),
        "requested_at": reference_time - timedelta(hours=30),
        "owner_id": uuid4(),
        "owner_name": "John Smith",
        "current_escalation_level": None,
        "account_name": "ACME Corp",
    }


@pytest.fixture
def sample_risk(reference_time: datetime) -> dict:
    """Create a sample risk for testing."""
    return {
        "id": uuid4(),
        "risk_number": "R-2025-001",
        "title": "Supply chain disruption",
        "status": "mitigating",
        "risk_level": "high",
        "inherent_risk_score": 15,
        "residual_risk_score": 12,
        "risk_owner_id": uuid4(),
        "risk_owner_name": "Jane Doe",
        "target_resolution_date": reference_time + timedelta(days=10),
        "identified_date": reference_time - timedelta(days=5),
        "category": "supply_chain",
        "current_escalation_level": None,
    }


@pytest.fixture
def sample_andon(reference_time: datetime) -> dict:
    """Create a sample Andon for testing."""
    return {
        "id": 1001,
        "andon_number": "A-2025-001",
        "description": "Machine breakdown on line 1",
        "status": "open",
        "severity": "red",
        "reported_at": reference_time - timedelta(minutes=10),
        "acknowledged_at": None,
        "station_id": 101,
        "station_name": "Line 1 - Station A",
        "red_ack_minutes": 5,
        "yellow_ack_minutes": 15,
        "current_escalation_level": None,
        "assigned_to_id": uuid4(),
        "assigned_to_name": "Bob Technician",
    }


# ==============================================================================
# EscalationPolicyService Initialization Tests
# ==============================================================================

class TestServiceInitialization:
    """Test service initialization and default configuration."""
    
    def test_service_creates_with_defaults(self, service: EscalationPolicyService):
        """Service initializes with default policies."""
        policies = service.get_all_policies()
        assert len(policies) >= 4
        assert "approval_aging" in policies
        assert "approval_value" in policies
        assert "high_severity_risk" in policies
        assert "andon_sla_breach" in policies
    
    def test_default_approval_thresholds(self, service: EscalationPolicyService):
        """Default approval thresholds are set correctly."""
        thresholds = service.get_approval_thresholds()
        assert "l1" in thresholds
        assert "l2" in thresholds
        assert "l3" in thresholds
        assert "l4" in thresholds
        assert thresholds["l1"]["hours"] == 24
        assert thresholds["l2"]["hours"] == 48
    
    def test_default_risk_thresholds(self, service: EscalationPolicyService):
        """Default risk thresholds are set correctly."""
        thresholds = service.get_risk_thresholds()
        assert thresholds["critical"] == EscalationLevel.L3
        assert thresholds["high"] == EscalationLevel.L2
        assert thresholds["medium"] == EscalationLevel.L1
        assert thresholds["low"] is None


# ==============================================================================
# Policy Management Tests
# ==============================================================================

class TestPolicyManagement:
    """Test policy CRUD operations."""
    
    def test_get_policy(self, service: EscalationPolicyService):
        """Get a specific policy by name."""
        policy = service.get_policy("approval_aging")
        assert policy is not None
        assert policy.name == "approval_aging"
        assert policy.target_type == EscalationTargetType.QUOTE_APPROVAL
    
    def test_get_nonexistent_policy(self, service: EscalationPolicyService):
        """Getting nonexistent policy returns None."""
        policy = service.get_policy("nonexistent")
        assert policy is None
    
    def test_add_policy(self, service: EscalationPolicyService):
        """Add a new policy."""
        new_policy = EscalationPolicy(
            name="custom_policy",
            description="Custom escalation policy",
            target_type=EscalationTargetType.TASK,
            conditions={"status": "blocked"},
        )
        service.add_policy(new_policy)
        
        retrieved = service.get_policy("custom_policy")
        assert retrieved is not None
        assert retrieved.description == "Custom escalation policy"
    
    def test_update_policy(self, service: EscalationPolicyService):
        """Update an existing policy."""
        updated_policy = EscalationPolicy(
            name="approval_aging",
            description="Updated approval aging policy",
            target_type=EscalationTargetType.QUOTE_APPROVAL,
            enabled=False,
        )
        service.add_policy(updated_policy)
        
        retrieved = service.get_policy("approval_aging")
        assert retrieved.description == "Updated approval aging policy"
        assert retrieved.enabled is False
    
    def test_remove_policy(self, service: EscalationPolicyService):
        """Remove a policy."""
        result = service.remove_policy("approval_aging")
        assert result is True
        assert service.get_policy("approval_aging") is None
    
    def test_remove_nonexistent_policy(self, service: EscalationPolicyService):
        """Removing nonexistent policy returns False."""
        result = service.remove_policy("nonexistent")
        assert result is False


# ==============================================================================
# Threshold Configuration Tests
# ==============================================================================

class TestThresholdConfiguration:
    """Test custom threshold configuration."""
    
    def test_set_approval_threshold_hours(self, service: EscalationPolicyService):
        """Set custom approval age threshold."""
        service.set_approval_threshold(EscalationLevel.L1, hours=12)
        thresholds = service.get_approval_thresholds()
        assert thresholds["l1"]["hours"] == 12
    
    def test_set_approval_threshold_value(self, service: EscalationPolicyService):
        """Set custom approval value threshold."""
        service.set_approval_threshold(EscalationLevel.L2, value=Decimal("75000"))
        thresholds = service.get_approval_thresholds()
        assert thresholds["l2"]["value"] == Decimal("75000")
    
    def test_set_risk_threshold(self, service: EscalationPolicyService):
        """Set custom risk severity escalation level."""
        service.set_risk_threshold("medium", EscalationLevel.L2)
        thresholds = service.get_risk_thresholds()
        assert thresholds["medium"] == EscalationLevel.L2


# ==============================================================================
# Aging Approval Detection Tests
# ==============================================================================

class TestAgingApprovalDetection:
    """Test detection of aging approvals."""
    
    def test_detect_l1_aging_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Detect approval at L1 (24+ hours)."""
        # 30 hours old
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L1
        assert result.items[0].reason == EscalationReason.APPROVAL_AGING
    
    def test_detect_l2_aging_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Detect approval at L2 (48+ hours)."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=50)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L2
    
    def test_detect_l3_aging_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Detect approval at L3 (72+ hours)."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=75)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L3
    
    def test_detect_l4_aging_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Detect approval at L4 (96+ hours)."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=100)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L4
    
    def test_no_escalation_for_fresh_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """No escalation for approval less than 24 hours old."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=12)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 0
    
    def test_skip_non_pending_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Skip approvals that are not pending."""
        sample_approval["status"] = "approved"
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 0
    
    def test_skip_already_escalated_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Skip approvals already at or above the target level."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        sample_approval["current_escalation_level"] = "l1"
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 0
    
    def test_escalate_past_current_level(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Escalate to higher level when past current level threshold."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=75)
        sample_approval["current_escalation_level"] = "l1"
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L3
    
    def test_handle_timezone_aware_datetime(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Handle timezone-aware datetime correctly."""
        from datetime import timezone
        
        sample_approval["requested_at"] = (reference_time - timedelta(hours=30)).replace(
            tzinfo=timezone.utc
        )
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.items_escalated == 1
    
    def test_context_includes_age_hours(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Context includes the age in hours."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert "age_hours" in result.items[0].context
        assert result.items[0].context["age_hours"] == 30.0


# ==============================================================================
# Value-Based Approval Escalation Tests
# ==============================================================================

class TestValueBasedApprovalEscalation:
    """Test detection of approvals requiring escalation based on value."""
    
    def test_detect_l2_value_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
    ):
        """Detect approval requiring L2 (50K+)."""
        sample_approval["value"] = Decimal("60000")
        
        result = service.detect_value_based_approvals([sample_approval])
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L2
        assert result.items[0].reason == EscalationReason.APPROVAL_VALUE_THRESHOLD
    
    def test_detect_l3_value_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
    ):
        """Detect approval requiring L3 (100K+)."""
        sample_approval["value"] = Decimal("150000")
        
        result = service.detect_value_based_approvals([sample_approval])
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L3
    
    def test_detect_l4_value_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
    ):
        """Detect approval requiring L4 (500K+)."""
        sample_approval["value"] = Decimal("750000")
        
        result = service.detect_value_based_approvals([sample_approval])
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L4
        assert result.items[0].priority == EscalationPriority.CRITICAL
    
    def test_no_escalation_for_low_value(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
    ):
        """No value-based escalation for low-value approvals."""
        sample_approval["value"] = Decimal("25000")
        
        result = service.detect_value_based_approvals([sample_approval])
        
        assert result.items_escalated == 0
    
    def test_skip_non_pending_approval(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
    ):
        """Skip non-pending approvals."""
        sample_approval["value"] = Decimal("200000")
        sample_approval["status"] = "approved"
        
        result = service.detect_value_based_approvals([sample_approval])
        
        assert result.items_escalated == 0


# ==============================================================================
# High-Severity Risk Detection Tests
# ==============================================================================

class TestHighSeverityRiskDetection:
    """Test detection of high-severity risks."""
    
    def test_detect_critical_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Detect critical severity risk."""
        sample_risk["risk_level"] = "critical"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L3
        assert result.items[0].reason == EscalationReason.RISK_SEVERITY_CRITICAL
        assert result.items[0].priority == EscalationPriority.CRITICAL
    
    def test_detect_high_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Detect high severity risk."""
        sample_risk["risk_level"] = "high"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L2
        assert result.items[0].reason == EscalationReason.RISK_SEVERITY_HIGH
    
    def test_detect_medium_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Detect medium severity risk."""
        sample_risk["risk_level"] = "medium"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L1
    
    def test_no_escalation_for_low_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """No escalation for low severity risks."""
        sample_risk["risk_level"] = "low"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 0
    
    def test_skip_closed_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Skip closed risks."""
        sample_risk["status"] = "closed"
        sample_risk["risk_level"] = "critical"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 0
    
    def test_skip_accepted_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Skip accepted risks."""
        sample_risk["status"] = "accepted"
        sample_risk["risk_level"] = "high"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 0
    
    def test_overdue_risk_changes_reason(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Overdue risk has RISK_OVERDUE reason."""
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=5)
        sample_risk["risk_level"] = "high"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].reason == EscalationReason.RISK_OVERDUE
        assert result.items[0].days_overdue == 5
    
    def test_context_includes_risk_score(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Context includes risk score."""
        sample_risk["risk_level"] = "high"
        
        result = service.detect_high_severity_risks([sample_risk], reference_time)
        
        assert "risk_score" in result.items[0].context
        assert result.items[0].context["risk_score"] == 12  # residual_risk_score


# ==============================================================================
# Overdue Risk Detection Tests
# ==============================================================================

class TestOverdueRiskDetection:
    """Test detection of overdue risks."""
    
    def test_detect_l1_overdue_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Detect risk 7+ days overdue (L1)."""
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=8)
        
        result = service.detect_overdue_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L1
        assert result.items[0].days_overdue == 8
    
    def test_detect_l2_overdue_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Detect risk 14+ days overdue (L2)."""
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=15)
        
        result = service.detect_overdue_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L2
    
    def test_detect_l3_overdue_risk(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Detect risk 30+ days overdue (L3)."""
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=35)
        
        result = service.detect_overdue_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].current_level == EscalationLevel.L3
        assert result.items[0].priority == EscalationPriority.CRITICAL
    
    def test_no_escalation_for_not_overdue(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """No escalation for risks not overdue."""
        sample_risk["target_resolution_date"] = reference_time + timedelta(days=10)
        
        result = service.detect_overdue_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 0
    
    def test_no_escalation_without_target_date(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """No escalation for risks without target resolution date."""
        sample_risk["target_resolution_date"] = None
        
        result = service.detect_overdue_risks([sample_risk], reference_time)
        
        assert result.items_escalated == 0
    
    def test_priority_based_on_days_overdue(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Priority increases with days overdue."""
        # 7-14 days = NORMAL
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=10)
        result = service.detect_overdue_risks([sample_risk], reference_time)
        assert result.items[0].priority == EscalationPriority.NORMAL
        
        # 14-30 days = HIGH
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=20)
        result = service.detect_overdue_risks([sample_risk], reference_time)
        assert result.items[0].priority == EscalationPriority.HIGH
        
        # 30+ days = CRITICAL
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=35)
        result = service.detect_overdue_risks([sample_risk], reference_time)
        assert result.items[0].priority == EscalationPriority.CRITICAL


# ==============================================================================
# Andon SLA Breach Detection Tests
# ==============================================================================

class TestAndonSLABreachDetection:
    """Test detection of Andon SLA breaches."""
    
    def test_detect_red_sla_breach(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Detect red Andon breaching SLA."""
        # 10 minutes elapsed, 5 minute SLA = 2x breach
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].reason == EscalationReason.ANDON_SLA_BREACH
        assert result.items[0].severity == "red"
    
    def test_detect_yellow_sla_breach(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Detect yellow Andon breaching SLA."""
        sample_andon["severity"] = "yellow"
        sample_andon["reported_at"] = reference_time - timedelta(minutes=25)
        
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        
        assert result.items_escalated == 1
        assert result.items[0].severity == "yellow"
    
    def test_escalation_level_based_on_sla_multiple(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Escalation level based on SLA multiple."""
        # 1.5x SLA = L1
        sample_andon["reported_at"] = reference_time - timedelta(minutes=8)
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        assert result.items[0].current_level == EscalationLevel.L1
        
        # 2x SLA = L2
        sample_andon["reported_at"] = reference_time - timedelta(minutes=12)
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        assert result.items[0].current_level == EscalationLevel.L2
        
        # 3x SLA = L3
        sample_andon["reported_at"] = reference_time - timedelta(minutes=20)
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        assert result.items[0].current_level == EscalationLevel.L3
    
    def test_no_escalation_within_sla(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """No escalation for Andons within SLA."""
        sample_andon["reported_at"] = reference_time - timedelta(minutes=3)
        
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        
        assert result.items_escalated == 0
    
    def test_skip_resolved_andon(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Skip resolved Andons."""
        sample_andon["status"] = "resolved"
        
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        
        assert result.items_escalated == 0
    
    def test_priority_for_red_andon(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Red Andon has higher priority."""
        sample_andon["severity"] = "red"
        sample_andon["reported_at"] = reference_time - timedelta(minutes=12)
        
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        
        assert result.items[0].priority == EscalationPriority.CRITICAL
    
    def test_context_includes_sla_multiple(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Context includes SLA multiple."""
        result = service.detect_andon_sla_breaches([sample_andon], reference_time)
        
        assert "sla_multiple" in result.items[0].context
        assert result.items[0].context["sla_minutes"] == 5


# ==============================================================================
# EscalationResult Tests
# ==============================================================================

class TestEscalationResult:
    """Test EscalationResult data structure."""
    
    def test_result_has_metadata(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Result includes metadata."""
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        assert result.policy_name == "approval_aging"
        assert result.target_type == EscalationTargetType.QUOTE_APPROVAL
        assert result.total_evaluated == 1
        assert isinstance(result.evaluated_at, datetime)
    
    def test_error_handling(
        self,
        service: EscalationPolicyService,
        reference_time: datetime,
    ):
        """Errors are captured without failing."""
        # Create an approval where accessing fields will cause an exception
        class BadApproval:
            @property
            def __getitem__(self, key):
                if key == "id":
                    return uuid4()
                if key == "status":
                    return "pending"
                if key == "requested_at":
                    # Return something that can't be subtracted from datetime
                    return "not-a-datetime"
                raise KeyError(key)
            
            def get(self, key, default=None):
                try:
                    return self[key]
                except KeyError:
                    return default
        
        # Actually test with a dict that has a bad requested_at
        bad_approval = {
            "id": uuid4(),
            "status": "pending",
            "requested_at": "not-a-datetime",  # Will cause exception when subtracting
        }
        
        result = service.detect_aging_approvals([bad_approval], reference_time)
        
        assert len(result.errors) > 0


# ==============================================================================
# EscalationItem Tests
# ==============================================================================

class TestEscalationItem:
    """Test EscalationItem data structure."""
    
    def test_item_has_all_fields(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Escalation item has all required fields."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        item = result.items[0]
        
        assert item.entity_id == sample_approval["id"]
        assert item.entity_type == EscalationTargetType.QUOTE_APPROVAL
        assert item.entity_name == sample_approval["name"]
        assert item.reason == EscalationReason.APPROVAL_AGING
        assert item.priority in EscalationPriority
        assert item.current_level in EscalationLevel
        assert item.owner_id == sample_approval["owner_id"]
        assert item.owner_name == sample_approval["owner_name"]
        assert item.value == sample_approval["value"]


# ==============================================================================
# Helper Method Tests
# ==============================================================================

class TestHelperMethods:
    """Test helper methods."""
    
    def test_calculate_approval_priority_high_value(
        self,
        service: EscalationPolicyService,
    ):
        """High value increases priority."""
        # $500K at 24 hours = base 4 (critical value) + age_modifier 0 = 4 = URGENT
        priority = service._calculate_approval_priority(Decimal("500000"), 24)
        assert priority == EscalationPriority.URGENT
        
        # $500K at 48+ hours = base 4 + age_modifier 1 = 5 (capped) = CRITICAL
        priority_old = service._calculate_approval_priority(Decimal("500000"), 50)
        assert priority_old == EscalationPriority.CRITICAL
    
    def test_calculate_approval_priority_age_modifier(
        self,
        service: EscalationPolicyService,
    ):
        """Age increases priority."""
        priority_fresh = service._calculate_approval_priority(Decimal("10000"), 24)
        priority_old = service._calculate_approval_priority(Decimal("10000"), 100)
        
        # Old approval should be higher priority
        priority_order = [
            EscalationPriority.LOW,
            EscalationPriority.NORMAL,
            EscalationPriority.HIGH,
            EscalationPriority.URGENT,
            EscalationPriority.CRITICAL,
        ]
        assert priority_order.index(priority_old) >= priority_order.index(priority_fresh)
    
    def test_get_escalation_target_role(
        self,
        service: EscalationPolicyService,
    ):
        """Get target role for escalation level."""
        role = service.get_escalation_target_role(
            EscalationLevel.L2,
            EscalationTargetType.QUOTE_APPROVAL,
        )
        assert role == "department_manager"


# ==============================================================================
# EscalationJobRunner Tests
# ==============================================================================

class TestEscalationJobRunner:
    """Test the async job runner."""
    
    @pytest.mark.asyncio
    async def test_run_approval_escalation(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Run approval escalation policies."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        runner = EscalationJobRunner(service=service)
        results = await runner.run_approval_escalation([sample_approval], reference_time)
        
        assert "approval_aging" in results
        assert "approval_value" in results
        assert results["approval_aging"].items_escalated == 1
    
    @pytest.mark.asyncio
    async def test_run_risk_escalation(
        self,
        service: EscalationPolicyService,
        sample_risk: dict,
        reference_time: datetime,
    ):
        """Run risk escalation policies."""
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=10)
        
        runner = EscalationJobRunner(service=service)
        results = await runner.run_risk_escalation([sample_risk], reference_time)
        
        assert "high_severity_risk" in results
        assert "risk_overdue" in results
        assert results["risk_overdue"].items_escalated == 1
    
    @pytest.mark.asyncio
    async def test_run_andon_escalation(
        self,
        service: EscalationPolicyService,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Run Andon escalation policies."""
        runner = EscalationJobRunner(service=service)
        results = await runner.run_andon_escalation([sample_andon], reference_time)
        
        assert "andon_sla_breach" in results
        assert results["andon_sla_breach"].items_escalated == 1
    
    @pytest.mark.asyncio
    async def test_run_full_escalation_scan(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        sample_risk: dict,
        sample_andon: dict,
        reference_time: datetime,
    ):
        """Run full escalation scan across all entity types."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        sample_risk["target_resolution_date"] = reference_time - timedelta(days=10)
        
        runner = EscalationJobRunner(service=service)
        summary = await runner.run_full_escalation_scan(
            approvals=[sample_approval],
            risks=[sample_risk],
            andons=[sample_andon],
            reference_time=reference_time,
        )
        
        assert summary["total_evaluated"] > 0
        assert summary["total_escalated"] > 0
        assert "by_policy" in summary
    
    @pytest.mark.asyncio
    async def test_callback_on_escalation(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Callback is called for each escalation."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        callback_items = []
        
        async def on_escalation(item: EscalationItem):
            callback_items.append(item)
        
        runner = EscalationJobRunner(
            service=service,
            on_escalation=on_escalation,
        )
        await runner.run_approval_escalation([sample_approval], reference_time)
        
        assert len(callback_items) >= 1
    
    @pytest.mark.asyncio
    async def test_notification_callback(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Notification callback is called with template."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        notifications = []
        
        async def on_notification(item: EscalationItem, template: str):
            notifications.append((item, template))
        
        runner = EscalationJobRunner(
            service=service,
            on_notification_needed=on_notification,
        )
        await runner.run_approval_escalation([sample_approval], reference_time)
        
        assert len(notifications) >= 1
        assert "escalation" in notifications[0][1]
    
    def test_get_escalation_summary(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Generate summary from results."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        runner = EscalationJobRunner(service=service)
        summary = runner.get_escalation_summary({"approval_aging": result})
        
        assert summary["total_policies_run"] == 1
        assert summary["total_evaluated"] == 1
        assert summary["total_escalated"] == 1
        assert "by_priority" in summary
        assert "by_level" in summary
        assert "by_type" in summary


# ==============================================================================
# Multiple Entity Tests
# ==============================================================================

class TestMultipleEntities:
    """Test processing multiple entities."""
    
    def test_process_multiple_approvals(
        self,
        service: EscalationPolicyService,
        reference_time: datetime,
    ):
        """Process multiple approvals with different ages."""
        approvals = [
            {
                "id": uuid4(),
                "name": f"Q-2025-{i:03d}",
                "status": "pending",
                "value": Decimal("50000"),
                "requested_at": reference_time - timedelta(hours=12 + (i * 12)),
                "owner_id": uuid4(),
                "owner_name": f"Owner {i}",
                "current_escalation_level": None,
            }
            for i in range(1, 11)
        ]
        
        result = service.detect_aging_approvals(approvals, reference_time)
        
        assert result.total_evaluated == 10
        # Only approvals 24+ hours old should be escalated
        assert result.items_escalated >= 6
    
    def test_process_multiple_risks(
        self,
        service: EscalationPolicyService,
        reference_time: datetime,
    ):
        """Process multiple risks with different severities."""
        risks = [
            {
                "id": uuid4(),
                "risk_number": f"R-2025-{i:03d}",
                "title": f"Risk {i}",
                "status": "mitigating",
                "risk_level": level,
                "inherent_risk_score": 15,
                "risk_owner_id": uuid4(),
                "risk_owner_name": f"Owner {i}",
                "target_resolution_date": reference_time + timedelta(days=30),
                "identified_date": reference_time - timedelta(days=5),
                "category": "technical",
                "current_escalation_level": None,
            }
            for i, level in enumerate(["low", "medium", "high", "critical"], 1)
        ]
        
        result = service.detect_high_severity_risks(risks, reference_time)
        
        assert result.total_evaluated == 4
        # low=0, medium=L1, high=L2, critical=L3
        assert result.items_escalated == 3


# ==============================================================================
# Edge Case Tests
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_list(self, service: EscalationPolicyService, reference_time: datetime):
        """Handle empty list gracefully."""
        result = service.detect_aging_approvals([], reference_time)
        
        assert result.total_evaluated == 0
        assert result.items_escalated == 0
        assert len(result.items) == 0
    
    def test_missing_optional_fields(
        self,
        service: EscalationPolicyService,
        reference_time: datetime,
    ):
        """Handle missing optional fields."""
        approval = {
            "id": uuid4(),
            "status": "pending",
            "requested_at": reference_time - timedelta(hours=30),
            # Missing: name, value, owner_id, owner_name, account_name
        }
        
        result = service.detect_aging_approvals([approval], reference_time)
        
        assert result.items_escalated == 1
        item = result.items[0]
        assert item.entity_name == "Unknown"
        assert item.value == Decimal("0")
    
    def test_none_value_handling(
        self,
        service: EscalationPolicyService,
        reference_time: datetime,
    ):
        """Handle None values gracefully."""
        approval = {
            "id": uuid4(),
            "name": None,
            "status": "pending",
            "value": None,
            "requested_at": reference_time - timedelta(hours=30),
            "owner_id": None,
            "owner_name": None,
            "current_escalation_level": None,
            "account_name": None,
        }
        
        result = service.detect_aging_approvals([approval], reference_time)
        
        assert result.items_escalated == 1
    
    def test_invalid_escalation_level_string(
        self,
        service: EscalationPolicyService,
        sample_approval: dict,
        reference_time: datetime,
    ):
        """Handle invalid escalation level string."""
        sample_approval["requested_at"] = reference_time - timedelta(hours=30)
        sample_approval["current_escalation_level"] = "invalid"
        
        result = service.detect_aging_approvals([sample_approval], reference_time)
        
        # Should proceed with escalation despite invalid level
        assert result.items_escalated == 1

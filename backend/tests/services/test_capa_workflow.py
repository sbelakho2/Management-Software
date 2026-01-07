"""
Tests for CAPA Workflow Integration Service.
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4

from sensei.services.capa_workflow import (
    NCType,
    NCSeverity,
    CAPAType,
    CAPAStatus,
    CAPAPriority,
    ActionStatus,
    ClosureGateType,
    LinkType,
    NonConformance,
    RootCauseAnalysis,
    CorrectiveAction,
    ClosureGate,
    EntityLink,
    EffectivenessCheck,
    CAPA,
    CAPACreationResult,
    ClosureCheckResult,
    RecurrenceCheckResult,
    CAPAConfig,
    CAPAWorkflowIntegrationService,
    get_capa_workflow_service,
    reset_capa_workflow_service,
)


# ============================================================================
# Enum Tests
# ============================================================================


class TestNCType:
    """Tests for NCType enum."""
    
    def test_all_nc_types(self):
        """Test all NC type values exist."""
        assert NCType.INTERNAL.value == "internal"
        assert NCType.SUPPLIER.value == "supplier"
        assert NCType.CUSTOMER.value == "customer"
        assert NCType.PROCESS.value == "process"
        assert NCType.PRODUCT.value == "product"
        assert NCType.DOCUMENTATION.value == "documentation"


class TestNCSeverity:
    """Tests for NCSeverity enum."""
    
    def test_all_severities(self):
        """Test all severity values exist."""
        assert NCSeverity.LOW.value == "low"
        assert NCSeverity.MEDIUM.value == "medium"
        assert NCSeverity.HIGH.value == "high"
        assert NCSeverity.CRITICAL.value == "critical"


class TestCAPAType:
    """Tests for CAPAType enum."""
    
    def test_all_capa_types(self):
        """Test all CAPA type values exist."""
        assert CAPAType.CORRECTIVE.value == "corrective"
        assert CAPAType.PREVENTIVE.value == "preventive"
        assert CAPAType.CORRECTIVE_AND_PREVENTIVE.value == "corrective_and_preventive"


class TestCAPAStatus:
    """Tests for CAPAStatus enum."""
    
    def test_all_statuses(self):
        """Test all status values exist."""
        assert CAPAStatus.DRAFT.value == "draft"
        assert CAPAStatus.OPEN.value == "open"
        assert CAPAStatus.ROOT_CAUSE_ANALYSIS.value == "root_cause_analysis"
        assert CAPAStatus.ACTION_PLANNING.value == "action_planning"
        assert CAPAStatus.IMPLEMENTING.value == "implementing"
        assert CAPAStatus.VERIFICATION.value == "verification"
        assert CAPAStatus.CLOSED.value == "closed"
        assert CAPAStatus.CANCELLED.value == "cancelled"


class TestClosureGateType:
    """Tests for ClosureGateType enum."""
    
    def test_key_gate_types(self):
        """Test key closure gate types exist."""
        assert ClosureGateType.ROOT_CAUSE_IDENTIFIED.value == "root_cause_identified"
        assert ClosureGateType.CORRECTIVE_ACTIONS_COMPLETE.value == "corrective_actions_complete"
        assert ClosureGateType.EFFECTIVENESS_VERIFIED.value == "effectiveness_verified"
        assert ClosureGateType.MANAGER_APPROVAL.value == "manager_approval"


class TestLinkType:
    """Tests for LinkType enum."""
    
    def test_all_link_types(self):
        """Test all link types exist."""
        assert LinkType.A3_REPORT.value == "a3_report"
        assert LinkType.STANDARD_WORK.value == "standard_work"
        assert LinkType.NC_RECORD.value == "nc_record"
        assert LinkType.TRAINING_RECORD.value == "training_record"


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestCAPAConfig:
    """Tests for CAPAConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CAPAConfig()
        
        assert config.auto_create_on_critical is True
        assert config.auto_create_on_recurrence is True
        assert config.recurrence_threshold == 2
        assert config.recurrence_period_days == 90
        assert config.default_target_days == 30
        assert config.require_root_cause is True
        assert config.require_effectiveness_check is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = CAPAConfig(
            auto_create_on_critical=False,
            recurrence_threshold=3,
            default_target_days=45,
        )
        
        assert config.auto_create_on_critical is False
        assert config.recurrence_threshold == 3
        assert config.default_target_days == 45


class TestNonConformance:
    """Tests for NonConformance dataclass."""
    
    def test_create_nc(self):
        """Test creating a Non-Conformance."""
        nc = NonConformance(
            id=uuid4(),
            nc_number="NC-2024-0001",
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.HIGH,
            title="Defective widget",
            description="Widget fails functional test",
            detected_by=uuid4(),
            detected_at=datetime.utcnow(),
            product_id=uuid4(),
            product_name="Widget A",
            defect_code="D001",
            quantity_affected=10,
        )
        
        assert nc.nc_number == "NC-2024-0001"
        assert nc.severity == NCSeverity.HIGH
        assert nc.is_closed is False
        assert nc.capa_id is None


class TestCorrectiveAction:
    """Tests for CorrectiveAction dataclass."""
    
    def test_create_action(self):
        """Test creating a corrective action."""
        action = CorrectiveAction(
            id=uuid4(),
            capa_id=uuid4(),
            action_type="corrective",
            description="Retrain operators",
            expected_result="Zero defects",
            assigned_to=uuid4(),
            due_date=date.today() + timedelta(days=7),
        )
        
        assert action.status == ActionStatus.PLANNED
        assert action.completed_at is None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance for testing."""
    reset_capa_workflow_service()
    return CAPAWorkflowIntegrationService()


@pytest.fixture
def user_id():
    """Create a user ID."""
    return uuid4()


@pytest.fixture
def product_id():
    """Create a product ID."""
    return uuid4()


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestServiceInitialization:
    """Tests for service initialization."""
    
    def test_default_initialization(self, service):
        """Test service initializes with defaults."""
        assert service.config is not None
        assert service.config.auto_create_on_critical is True
    
    def test_custom_config(self):
        """Test service with custom config."""
        config = CAPAConfig(auto_create_on_critical=False)
        svc = CAPAWorkflowIntegrationService(config=config)
        assert svc.config.auto_create_on_critical is False


# ============================================================================
# Non-Conformance Tests
# ============================================================================


class TestNCRegistration:
    """Tests for NC registration."""
    
    def test_register_basic_nc(self, service, user_id):
        """Test registering a basic NC."""
        nc, capa_result = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.MEDIUM,
            title="Minor defect",
            description="Surface scratch on widget",
            detected_by=user_id,
        )
        
        assert nc.id is not None
        assert nc.nc_number.startswith("NC-")
        assert nc.severity == NCSeverity.MEDIUM
        assert capa_result is None  # No auto-CAPA for medium severity
    
    def test_register_critical_nc_auto_creates_capa(self, service, user_id):
        """Test that critical NC auto-creates CAPA."""
        nc, capa_result = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.CRITICAL,
            title="Critical failure",
            description="Widget explodes during use",
            detected_by=user_id,
        )
        
        assert nc.capa_required is True
        assert capa_result is not None
        assert capa_result.success is True
        assert capa_result.auto_created is True
        assert capa_result.capa.priority == CAPAPriority.URGENT
        assert nc.capa_id == capa_result.capa.id
    
    def test_register_nc_with_product_info(self, service, user_id, product_id):
        """Test registering NC with product info."""
        nc, _ = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.LOW,
            title="Cosmetic issue",
            description="Minor scratch",
            detected_by=user_id,
            product_id=product_id,
            product_name="Widget X",
            defect_code="SCRATCH-01",
            quantity_affected=5,
        )
        
        assert nc.product_id == product_id
        assert nc.product_name == "Widget X"
        assert nc.defect_code == "SCRATCH-01"
        assert nc.quantity_affected == 5
    
    def test_recurrence_detection(self, service, user_id, product_id):
        """Test that recurrence is detected and triggers CAPA."""
        # Register first NC
        service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.MEDIUM,
            title="Defect 1",
            description="Same defect",
            detected_by=user_id,
            product_id=product_id,
            defect_code="D001",
        )
        
        # Register second NC with same defect code
        service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.MEDIUM,
            title="Defect 2",
            description="Same defect again",
            detected_by=user_id,
            product_id=product_id,
            defect_code="D001",
        )
        
        # Register third NC - this should trigger recurrence (threshold is 2)
        nc3, capa_result = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.MEDIUM,
            title="Defect 3",
            description="Same defect third time",
            detected_by=user_id,
            product_id=product_id,
            defect_code="D001",
        )
        
        assert nc3.is_recurrence is True
        assert nc3.recurrence_count >= 2
        assert capa_result is not None
        assert "recurrence" in capa_result.creation_reason.lower()
    
    def test_get_nc(self, service, user_id):
        """Test getting an NC by ID."""
        nc, _ = service.register_nc(
            nc_type=NCType.INTERNAL,
            severity=NCSeverity.LOW,
            title="Test NC",
            description="Test",
            detected_by=user_id,
        )
        
        retrieved = service.get_nc(nc.id)
        assert retrieved is not None
        assert retrieved.id == nc.id
    
    def test_list_ncs(self, service, user_id):
        """Test listing NCs."""
        for severity in [NCSeverity.LOW, NCSeverity.MEDIUM, NCSeverity.HIGH]:
            service.register_nc(
                nc_type=NCType.PRODUCT,
                severity=severity,
                title=f"{severity.value} NC",
                description="Test",
                detected_by=user_id,
            )
        
        all_ncs = service.list_ncs()
        assert len(all_ncs) >= 3
    
    def test_list_ncs_by_severity(self, service, user_id):
        """Test listing NCs by severity."""
        service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.HIGH,
            title="High severity",
            description="Test",
            detected_by=user_id,
        )
        
        high_ncs = service.list_ncs(severity=NCSeverity.HIGH)
        assert len(high_ncs) >= 1
        assert all(nc.severity == NCSeverity.HIGH for nc in high_ncs)


# ============================================================================
# CAPA Creation Tests
# ============================================================================


class TestCAPACreation:
    """Tests for CAPA creation."""
    
    def test_create_capa_from_nc(self, service, user_id):
        """Test creating a CAPA from an NC."""
        nc, _ = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.MEDIUM,
            title="Test NC",
            description="Test description",
            detected_by=user_id,
        )
        
        result = service.create_capa_from_nc(
            nc_id=nc.id,
            created_by=user_id,
        )
        
        assert result.success is True
        assert result.capa is not None
        assert result.capa.source_nc_id == nc.id
        assert result.capa.status == CAPAStatus.OPEN
        assert len(result.capa.closure_gates) > 0
    
    def test_create_capa_from_nonexistent_nc(self, service, user_id):
        """Test creating CAPA from nonexistent NC."""
        result = service.create_capa_from_nc(
            nc_id=uuid4(),
            created_by=user_id,
        )
        
        assert result.success is False
    
    def test_create_standalone_capa(self, service, user_id):
        """Test creating a standalone CAPA."""
        capa = service.create_capa(
            title="Preventive action for safety",
            description="Improve safety procedures",
            created_by=user_id,
            capa_type=CAPAType.PREVENTIVE,
            priority=CAPAPriority.HIGH,
        )
        
        assert capa.id is not None
        assert capa.capa_number.startswith("CAPA-")
        assert capa.capa_type == CAPAType.PREVENTIVE
        assert capa.status == CAPAStatus.OPEN
        assert capa.target_completion_date is not None
    
    def test_capa_has_default_closure_gates(self, service, user_id):
        """Test that CAPA has default closure gates."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        assert len(capa.closure_gates) > 0
        
        gate_types = [g.gate_type for g in capa.closure_gates]
        assert ClosureGateType.ROOT_CAUSE_IDENTIFIED in gate_types
        assert ClosureGateType.MANAGER_APPROVAL in gate_types
    
    def test_get_capa(self, service, user_id):
        """Test getting a CAPA by ID."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        retrieved = service.get_capa(capa.id)
        assert retrieved is not None
        assert retrieved.id == capa.id
    
    def test_list_capas(self, service, user_id):
        """Test listing CAPAs."""
        for i in range(3):
            service.create_capa(
                title=f"CAPA {i}",
                description="Test",
                created_by=user_id,
            )
        
        capas = service.list_capas()
        assert len(capas) >= 3
    
    def test_list_capas_by_status(self, service, user_id):
        """Test listing CAPAs by status."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        open_capas = service.list_capas(status=CAPAStatus.OPEN)
        assert capa.id in [c.id for c in open_capas]
    
    def test_list_capas_by_owner(self, service, user_id):
        """Test listing CAPAs by owner."""
        owner_id = uuid4()
        
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
            owner_id=owner_id,
        )
        
        owned_capas = service.list_capas(owner_id=owner_id)
        assert len(owned_capas) >= 1
        assert all(c.owner_id == owner_id for c in owned_capas)


# ============================================================================
# Root Cause Analysis Tests
# ============================================================================


class TestRootCauseAnalysis:
    """Tests for root cause analysis."""
    
    def test_add_rca(self, service, user_id):
        """Test adding root cause analysis."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        rca = service.add_root_cause_analysis(
            capa_id=capa.id,
            method="5-Why",
            analysis_details="Why 1: X\nWhy 2: Y\nWhy 3: Z",
            root_causes=["Inadequate training", "Missing procedure"],
            performed_by=user_id,
            contributing_factors=["High workload"],
        )
        
        assert rca is not None
        assert rca.method == "5-Why"
        assert len(rca.root_causes) == 2
        
        # Check CAPA status updated
        capa = service.get_capa(capa.id)
        assert capa.root_cause_analysis is not None
    
    def test_verify_rca(self, service, user_id):
        """Test verifying root cause analysis."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        service.add_root_cause_analysis(
            capa_id=capa.id,
            method="Fishbone",
            analysis_details="Analysis",
            root_causes=["Root cause 1"],
            performed_by=user_id,
        )
        
        verifier_id = uuid4()
        result = service.verify_root_cause(capa.id, verifier_id)
        
        assert result is True
        
        capa = service.get_capa(capa.id)
        assert capa.root_cause_analysis.verified is True
        assert capa.root_cause_analysis.verified_by == verifier_id
        
        # Check gate passed
        rca_gate = next(
            (g for g in capa.closure_gates if g.gate_type == ClosureGateType.ROOT_CAUSE_IDENTIFIED),
            None
        )
        assert rca_gate is not None
        assert rca_gate.is_passed is True


# ============================================================================
# Action Management Tests
# ============================================================================


class TestActionManagement:
    """Tests for action management."""
    
    def test_add_action(self, service, user_id):
        """Test adding an action."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        assignee_id = uuid4()
        action = service.add_action(
            capa_id=capa.id,
            action_type="corrective",
            description="Update procedure",
            expected_result="No more defects",
            assigned_to=assignee_id,
            due_date=date.today() + timedelta(days=7),
            priority=CAPAPriority.HIGH,
        )
        
        assert action is not None
        assert action.action_type == "corrective"
        assert action.assigned_to == assignee_id
        assert action.status == ActionStatus.PLANNED
        
        capa = service.get_capa(capa.id)
        assert len(capa.actions) == 1
    
    def test_start_action(self, service, user_id):
        """Test starting an action."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        action = service.add_action(
            capa_id=capa.id,
            action_type="corrective",
            description="Fix issue",
            expected_result="Issue fixed",
            assigned_to=uuid4(),
            due_date=date.today() + timedelta(days=7),
        )
        
        started = service.start_action(capa.id, action.id)
        
        assert started.status == ActionStatus.IN_PROGRESS
        assert started.started_at is not None
        
        # Check CAPA status
        capa = service.get_capa(capa.id)
        assert capa.status == CAPAStatus.IMPLEMENTING
    
    def test_complete_action(self, service, user_id):
        """Test completing an action."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        action = service.add_action(
            capa_id=capa.id,
            action_type="corrective",
            description="Fix issue",
            expected_result="Issue fixed",
            assigned_to=uuid4(),
            due_date=date.today() + timedelta(days=7),
        )
        
        service.start_action(capa.id, action.id)
        
        completer_id = uuid4()
        completed = service.complete_action(
            capa_id=capa.id,
            action_id=action.id,
            completed_by=completer_id,
            notes="Action completed successfully",
            evidence_links=["http://evidence.com/doc1"],
        )
        
        assert completed.status == ActionStatus.COMPLETED
        assert completed.completed_by == completer_id
        assert completed.notes == "Action completed successfully"
    
    def test_verify_action(self, service, user_id):
        """Test verifying an action."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        action = service.add_action(
            capa_id=capa.id,
            action_type="corrective",
            description="Fix issue",
            expected_result="Issue fixed",
            assigned_to=uuid4(),
            due_date=date.today() + timedelta(days=7),
        )
        
        service.start_action(capa.id, action.id)
        service.complete_action(capa.id, action.id, uuid4())
        
        verifier_id = uuid4()
        verified = service.verify_action(
            capa_id=capa.id,
            action_id=action.id,
            verified_by=verifier_id,
            verification_result="Verified effective",
        )
        
        assert verified.status == ActionStatus.VERIFIED
        assert verified.verified_by == verifier_id
    
    def test_get_overdue_actions(self, service, user_id):
        """Test getting overdue actions."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        action = service.add_action(
            capa_id=capa.id,
            action_type="corrective",
            description="Fix issue",
            expected_result="Issue fixed",
            assigned_to=uuid4(),
            due_date=date.today() - timedelta(days=1),  # Past due
        )
        
        overdue = service.get_overdue_actions()
        
        assert len(overdue) >= 1
        assert action.id in [a.id for a in overdue]


# ============================================================================
# Entity Linking Tests
# ============================================================================


class TestEntityLinking:
    """Tests for entity linking."""
    
    def test_link_a3_report(self, service, user_id):
        """Test linking an A3 report."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        a3_id = uuid4()
        link = service.link_a3_report(
            capa_id=capa.id,
            a3_id=a3_id,
            a3_name="A3-2024-001: Root Cause Investigation",
            created_by=user_id,
            description="A3 for detailed analysis",
        )
        
        assert link is not None
        assert link.link_type == LinkType.A3_REPORT
        assert link.linked_entity_id == a3_id
    
    def test_link_standard_work(self, service, user_id):
        """Test linking Standard Work."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        sw_id = uuid4()
        link = service.link_standard_work(
            capa_id=capa.id,
            standard_work_id=sw_id,
            standard_work_name="SW-001: Assembly Procedure",
            created_by=user_id,
            description="Updated standard work",
        )
        
        assert link is not None
        assert link.link_type == LinkType.STANDARD_WORK
    
    def test_link_training_record(self, service, user_id):
        """Test linking training record."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        training_id = uuid4()
        link = service.link_training_record(
            capa_id=capa.id,
            training_id=training_id,
            training_name="Operator Retraining",
            created_by=user_id,
        )
        
        assert link is not None
        assert link.link_type == LinkType.TRAINING_RECORD
    
    def test_get_linked_entities(self, service, user_id):
        """Test getting linked entities."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        # Add multiple links
        service.link_a3_report(capa.id, uuid4(), "A3-001", user_id)
        service.link_standard_work(capa.id, uuid4(), "SW-001", user_id)
        service.link_training_record(capa.id, uuid4(), "TR-001", user_id)
        
        all_links = service.get_linked_entities(capa.id)
        assert len(all_links) == 3
        
        a3_links = service.get_linked_entities(capa.id, link_type=LinkType.A3_REPORT)
        assert len(a3_links) == 1


# ============================================================================
# Closure Gate Tests
# ============================================================================


class TestClosureGates:
    """Tests for closure gates."""
    
    def test_pass_closure_gate(self, service, user_id):
        """Test passing a closure gate."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        gate = service.pass_closure_gate(
            capa_id=capa.id,
            gate_type=ClosureGateType.DOCUMENTATION_UPDATED,
            passed_by=user_id,
            evidence="All docs updated in system",
            notes="Updated per SOP",
        )
        
        assert gate is not None
        assert gate.is_passed is True
        assert gate.passed_by == user_id
    
    def test_check_closure_readiness_not_ready(self, service, user_id):
        """Test checking closure readiness when not ready."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        result = service.check_closure_readiness(capa.id)
        
        assert result.can_close is False
        assert len(result.failed_gates) > 0
        assert len(result.missing_requirements) > 0
    
    def test_check_closure_readiness_ready(self, service, user_id):
        """Test checking closure readiness when ready."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        # Add and verify root cause
        service.add_root_cause_analysis(
            capa_id=capa.id,
            method="5-Why",
            analysis_details="Analysis",
            root_causes=["Root cause"],
            performed_by=user_id,
        )
        service.verify_root_cause(capa.id, user_id)
        
        # Pass all required gates
        for gate in capa.closure_gates:
            if gate.is_required:
                service.pass_closure_gate(capa.id, gate.gate_type, user_id)
        
        result = service.check_closure_readiness(capa.id)
        
        # Should be ready if all gates passed and no pending actions
        assert result.can_close is True or len(result.pending_actions) > 0


# ============================================================================
# Effectiveness Check Tests
# ============================================================================


class TestEffectivenessCheck:
    """Tests for effectiveness checks."""
    
    def test_add_effectiveness_check(self, service, user_id):
        """Test adding an effectiveness check."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        check = service.add_effectiveness_check(
            capa_id=capa.id,
            performed_by=user_id,
            method="Data review",
            criteria="Zero defects for 30 days",
            result="No defects observed",
            is_effective=True,
            evidence="Quality report Q1-2024",
        )
        
        assert check is not None
        assert check.is_effective is True
        
        capa = service.get_capa(capa.id)
        assert capa.is_effective is True
        
        # Check effectiveness gate passed
        eff_gate = next(
            (g for g in capa.closure_gates if g.gate_type == ClosureGateType.EFFECTIVENESS_VERIFIED),
            None
        )
        assert eff_gate is not None
        assert eff_gate.is_passed is True
    
    def test_add_ineffective_check(self, service, user_id):
        """Test adding an ineffective check."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        check = service.add_effectiveness_check(
            capa_id=capa.id,
            performed_by=user_id,
            method="Data review",
            criteria="Zero defects",
            result="2 defects observed",
            is_effective=False,
            follow_up_required=True,
            follow_up_date=date.today() + timedelta(days=30),
        )
        
        assert check.is_effective is False
        assert check.follow_up_required is True


# ============================================================================
# Closure Tests
# ============================================================================


class TestCAPAClosure:
    """Tests for CAPA closure."""
    
    def test_close_capa_not_ready(self, service, user_id):
        """Test closing CAPA when not ready."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        success, _, issues = service.close_capa(capa.id, user_id)
        
        assert success is False
        assert len(issues) > 0
    
    def test_close_capa_force(self, service, user_id):
        """Test force closing CAPA."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        success, closed_capa, issues = service.close_capa(
            capa.id,
            user_id,
            force=True,
        )
        
        assert success is True
        assert closed_capa.status == CAPAStatus.CLOSED
        assert closed_capa.closed_at is not None
    
    def test_cancel_capa(self, service, user_id):
        """Test cancelling a CAPA."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        cancelled = service.cancel_capa(
            capa.id,
            user_id,
            reason="Duplicate CAPA",
        )
        
        assert cancelled.status == CAPAStatus.CANCELLED
    
    def test_close_capa_closes_linked_nc(self, service, user_id):
        """Test that closing CAPA closes linked NC."""
        nc, capa_result = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.CRITICAL,
            title="Critical issue",
            description="Test",
            detected_by=user_id,
        )
        
        capa = capa_result.capa
        
        # Force close
        service.close_capa(capa.id, user_id, force=True)
        
        # Check NC is closed
        nc = service.get_nc(nc.id)
        assert nc.is_closed is True


# ============================================================================
# Status Updates Tests
# ============================================================================


class TestStatusUpdates:
    """Tests for status updates."""
    
    def test_update_status(self, service, user_id):
        """Test updating CAPA status."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        updated = service.update_status(capa.id, CAPAStatus.VERIFICATION)
        
        assert updated.status == CAPAStatus.VERIFICATION


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetrics:
    """Tests for CAPA metrics."""
    
    def test_get_metrics_empty(self, service):
        """Test getting metrics with no CAPAs."""
        metrics = service.get_capa_metrics()
        
        assert metrics["total_capas"] == 0
    
    def test_get_metrics_with_data(self, service, user_id):
        """Test getting metrics with CAPAs."""
        # Create some CAPAs
        for i in range(3):
            capa = service.create_capa(
                title=f"CAPA {i}",
                description="Test",
                created_by=user_id,
                priority=CAPAPriority.HIGH if i == 0 else CAPAPriority.MEDIUM,
            )
        
        # Close one
        capas = service.list_capas()
        service.close_capa(capas[0].id, user_id, force=True)
        
        metrics = service.get_capa_metrics()
        
        assert metrics["total_capas"] == 3
        assert metrics["open_capas"] == 2
        assert metrics["closed_capas"] == 1
        assert "by_status" in metrics
        assert "by_priority" in metrics


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_singleton_instance(self):
        """Test getting singleton instance."""
        reset_capa_workflow_service()
        
        svc1 = get_capa_workflow_service()
        svc2 = get_capa_workflow_service()
        
        assert svc1 is svc2
    
    def test_reset_singleton(self):
        """Test resetting singleton instance."""
        svc1 = get_capa_workflow_service()
        
        reset_capa_workflow_service()
        
        svc2 = get_capa_workflow_service()
        
        assert svc1 is not svc2


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_disable_auto_capa_on_critical(self, user_id):
        """Test disabling auto CAPA creation on critical."""
        config = CAPAConfig(auto_create_on_critical=False)
        service = CAPAWorkflowIntegrationService(config=config)
        
        nc, capa_result = service.register_nc(
            nc_type=NCType.PRODUCT,
            severity=NCSeverity.CRITICAL,
            title="Critical issue",
            description="Test",
            detected_by=user_id,
        )
        
        assert capa_result is None
        assert nc.capa_id is None
    
    def test_add_action_to_nonexistent_capa(self, service, user_id):
        """Test adding action to nonexistent CAPA."""
        result = service.add_action(
            capa_id=uuid4(),
            action_type="corrective",
            description="Test",
            expected_result="Test",
            assigned_to=uuid4(),
            due_date=date.today(),
        )
        
        assert result is None
    
    def test_link_to_nonexistent_capa(self, service, user_id):
        """Test linking to nonexistent CAPA."""
        result = service.link_a3_report(
            capa_id=uuid4(),
            a3_id=uuid4(),
            a3_name="Test",
            created_by=user_id,
        )
        
        assert result is None
    
    def test_multiple_effectiveness_checks(self, service, user_id):
        """Test multiple effectiveness checks."""
        capa = service.create_capa(
            title="Test CAPA",
            description="Test",
            created_by=user_id,
        )
        
        # First check - not effective
        service.add_effectiveness_check(
            capa_id=capa.id,
            performed_by=user_id,
            method="Review",
            criteria="Zero defects",
            result="1 defect",
            is_effective=False,
        )
        
        # Second check - effective
        service.add_effectiveness_check(
            capa_id=capa.id,
            performed_by=user_id,
            method="Review",
            criteria="Zero defects",
            result="No defects",
            is_effective=True,
        )
        
        capa = service.get_capa(capa.id)
        assert len(capa.effectiveness_checks) == 2
        assert capa.is_effective is True  # Latest check

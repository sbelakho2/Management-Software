"""
Comprehensive tests for State Machine & Gate Enforcement Service.

Tests:
- State machine initialization and configuration
- Transition validation and gate enforcement
- Individual state machines (Opportunity, RFQ, Qualification, Task)
- Registry functionality
- Gate enforcer centralized validation
"""

import pytest
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from sensei.services.core.state_machine import (
    StateMachine,
    StateMachineRegistry,
    GateEnforcer,
    TransitionResult,
    TransitionRule,
    TransitionError,
    create_opportunity_state_machine,
    create_rfq_state_machine,
    create_qualification_state_machine,
    create_task_state_machine,
)


# =============================================================================
# Mock Entity for Testing
# =============================================================================


@dataclass
class MockEntity:
    """Mock entity for testing transitions."""
    
    id: str = ""
    status: str = ""
    account_id: Optional[str] = None
    contact_id: Optional[str] = None
    rfq_id: Optional[str] = None
    title: Optional[str] = None
    quantity: Optional[int] = None
    due_date: Optional[str] = None
    estimated_value: Optional[float] = None
    probability: Optional[int] = None
    expected_close_date: Optional[str] = None
    actual_value: Optional[float] = None
    lost_reason: Optional[str] = None
    hold_reason: Optional[str] = None
    blocked_reason: Optional[str] = None
    proposed_decision: Optional[str] = None
    decision_rationale: Optional[str] = None
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    override_by: Optional[str] = None
    override_rationale: Optional[str] = None
    no_bid_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None
    disqualification_reason: Optional[str] = None
    qualification_decision: Optional[str] = None
    rfq_number: Optional[str] = None


# =============================================================================
# StateMachine Core Tests
# =============================================================================


class TestStateMachineCore:
    """Tests for StateMachine base functionality."""
    
    def test_create_state_machine(self):
        """Test creating a basic state machine."""
        sm = StateMachine(
            name="Test",
            states=["a", "b", "c"],
            initial_state="a",
            final_states=["c"],
        )
        
        assert sm.name == "Test"
        assert sm.initial_state == "a"
        assert "a" in sm.states
        assert "b" in sm.states
        assert "c" in sm.states
        assert "c" in sm.final_states
    
    def test_add_transition(self):
        """Test adding transitions."""
        sm = StateMachine(
            name="Test",
            states=["a", "b", "c"],
            initial_state="a",
        )
        
        sm.add_transition("a", "b", description="Move to B")
        sm.add_transition("b", "c", required_fields=["value"])
        
        assert ("a", "b") in sm.transitions
        assert ("b", "c") in sm.transitions
    
    def test_add_transition_invalid_state(self):
        """Test adding transition with invalid state raises error."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        
        with pytest.raises(ValueError, match="Invalid from_state"):
            sm.add_transition("x", "b")
        
        with pytest.raises(ValueError, match="Invalid to_state"):
            sm.add_transition("a", "y")
    
    def test_can_transition_allowed(self):
        """Test checking allowed transition."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        sm.add_transition("a", "b")
        
        entity = MockEntity()
        result = sm.can_transition(entity, "a", "b")
        
        assert result.allowed is True
        assert result.from_state == "a"
        assert result.to_state == "b"
    
    def test_can_transition_not_defined(self):
        """Test checking undefined transition."""
        sm = StateMachine(
            name="Test",
            states=["a", "b", "c"],
            initial_state="a",
        )
        sm.add_transition("a", "b")
        # No transition from a to c defined
        
        entity = MockEntity()
        result = sm.can_transition(entity, "a", "c")
        
        assert result.allowed is False
        assert "not allowed" in result.error_message
    
    def test_can_transition_from_final_state(self):
        """Test cannot transition from final state."""
        sm = StateMachine(
            name="Test",
            states=["a", "b", "c"],
            initial_state="a",
            final_states=["c"],
        )
        sm.add_transition("a", "b")
        sm.add_transition("c", "a")  # Define it anyway
        
        entity = MockEntity()
        result = sm.can_transition(entity, "c", "a")
        
        assert result.allowed is False
        assert "final state" in result.error_message
    
    def test_transition_with_required_fields_missing(self):
        """Test transition blocked when required fields missing."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        sm.add_transition("a", "b", required_fields=["account_id", "contact_id"])
        
        entity = MockEntity()  # No fields filled
        result = sm.can_transition(entity, "a", "b")
        
        assert result.allowed is False
        assert "account_id" in result.missing_fields
        assert "contact_id" in result.missing_fields
        assert result.requires_override is True
    
    def test_transition_with_required_fields_present(self):
        """Test transition allowed when required fields present."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        sm.add_transition("a", "b", required_fields=["account_id", "contact_id"])
        
        entity = MockEntity(account_id="123", contact_id="456")
        result = sm.can_transition(entity, "a", "b")
        
        assert result.allowed is True
        assert len(result.missing_fields) == 0
    
    def test_transition_with_override(self):
        """Test transition allowed with override when fields missing."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        sm.add_transition("a", "b", required_fields=["account_id"])
        
        entity = MockEntity()  # account_id missing
        
        # Without override - blocked
        result1 = sm.can_transition(entity, "a", "b", allow_override=False)
        assert result1.allowed is False
        
        # With override - allowed
        result2 = sm.can_transition(entity, "a", "b", allow_override=True)
        assert result2.allowed is True
        assert result2.requires_override is True
    
    def test_transition_with_custom_condition(self):
        """Test transition with custom condition."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        
        def check_value(entity):
            val = getattr(entity, "estimated_value", None)
            if val and val > 0:
                return True, None
            return False, "Value must be positive"
        
        sm.add_transition("a", "b", conditions=[check_value])
        
        # Fails condition
        entity1 = MockEntity()
        result1 = sm.can_transition(entity1, "a", "b")
        assert result1.allowed is False
        assert "Value must be positive" in result1.failed_conditions
        
        # Passes condition
        entity2 = MockEntity(estimated_value=100.0)
        result2 = sm.can_transition(entity2, "a", "b")
        assert result2.allowed is True
    
    def test_get_allowed_transitions(self):
        """Test getting allowed transitions from a state."""
        sm = StateMachine(
            name="Test",
            states=["a", "b", "c", "d"],
            initial_state="a",
        )
        sm.add_transition("a", "b")
        sm.add_transition("a", "c")
        sm.add_transition("b", "d")
        
        allowed = sm.get_allowed_transitions("a")
        assert "b" in allowed
        assert "c" in allowed
        assert "d" not in allowed
    
    def test_get_transition_requirements(self):
        """Test getting transition requirements."""
        sm = StateMachine(
            name="Test",
            states=["a", "b"],
            initial_state="a",
        )
        sm.add_transition(
            "a", "b",
            required_fields=["account_id"],
            description="Move to B",
        )
        
        reqs = sm.get_transition_requirements("a", "b")
        
        assert reqs is not None
        assert reqs["from_state"] == "a"
        assert reqs["to_state"] == "b"
        assert "account_id" in reqs["required_fields"]
        assert reqs["description"] == "Move to B"
    
    def test_get_all_states(self):
        """Test getting all states info."""
        sm = StateMachine(
            name="Test",
            states=["a", "b", "c"],
            initial_state="a",
            final_states=["c"],
        )
        sm.add_transition("a", "b")
        sm.add_transition("b", "c")
        
        states = sm.get_all_states()
        
        assert len(states) == 3
        
        state_a = next(s for s in states if s["state"] == "a")
        assert state_a["is_initial"] is True
        assert state_a["is_final"] is False
        assert "b" in state_a["allowed_transitions"]
        
        state_c = next(s for s in states if s["state"] == "c")
        assert state_c["is_initial"] is False
        assert state_c["is_final"] is True


# =============================================================================
# Opportunity State Machine Tests
# =============================================================================


class TestOpportunityStateMachine:
    """Tests for the Opportunity state machine."""
    
    @pytest.fixture
    def sm(self):
        """Create the opportunity state machine."""
        return create_opportunity_state_machine()
    
    def test_initial_state(self, sm):
        """Test opportunity starts in suspect state."""
        assert sm.initial_state == "suspect"
    
    def test_final_states(self, sm):
        """Test opportunity final states."""
        assert "won" in sm.final_states
        assert "lost" in sm.final_states
    
    def test_suspect_to_prospect(self, sm):
        """Test transitioning from suspect to prospect."""
        entity = MockEntity(account_id="acc1", contact_id="con1")
        result = sm.can_transition(entity, "suspect", "prospect")
        
        assert result.allowed is True
    
    def test_suspect_to_prospect_missing_fields(self, sm):
        """Test suspect to prospect blocked without required fields."""
        entity = MockEntity()
        result = sm.can_transition(entity, "suspect", "prospect")
        
        assert result.allowed is False
        assert "account_id" in result.missing_fields
        assert "contact_id" in result.missing_fields
    
    def test_prospect_to_qualified(self, sm):
        """Test transitioning from prospect to qualified."""
        entity = MockEntity(estimated_value=50000.0, probability=60)
        result = sm.can_transition(entity, "prospect", "qualified")
        
        assert result.allowed is True
    
    def test_negotiation_to_won(self, sm):
        """Test closing opportunity as won."""
        entity = MockEntity(actual_value=75000.0)
        result = sm.can_transition(entity, "negotiation", "won")
        
        assert result.allowed is True
    
    def test_negotiation_to_lost(self, sm):
        """Test closing opportunity as lost."""
        entity = MockEntity(lost_reason="Price too high")
        result = sm.can_transition(entity, "negotiation", "lost")
        
        assert result.allowed is True
    
    def test_on_hold_transitions(self, sm):
        """Test on hold transitions."""
        entity_hold = MockEntity(hold_reason="Budget freeze")
        
        # Can go on hold from prospect
        result = sm.can_transition(entity_hold, "prospect", "on_hold")
        assert result.allowed is True
        
        # Can resume from hold
        result = sm.can_transition(MockEntity(), "on_hold", "prospect")
        assert result.allowed is True


# =============================================================================
# RFQ State Machine Tests
# =============================================================================


class TestRFQStateMachine:
    """Tests for the RFQ state machine."""
    
    @pytest.fixture
    def sm(self):
        """Create the RFQ state machine."""
        return create_rfq_state_machine()
    
    def test_initial_state(self, sm):
        """Test RFQ starts in draft state."""
        assert sm.initial_state == "draft"
    
    def test_final_states(self, sm):
        """Test RFQ final states."""
        assert "won" in sm.final_states
        assert "lost" in sm.final_states
        assert "no_bid" in sm.final_states
        assert "cancelled" in sm.final_states
    
    def test_draft_to_received(self, sm):
        """Test transitioning from draft to received."""
        entity = MockEntity(rfq_number="RFQ-001", account_id="acc1", title="Test RFQ")
        result = sm.can_transition(entity, "draft", "received")
        
        assert result.allowed is True
    
    def test_received_to_qualifying(self, sm):
        """Test transitioning to qualifying with required fields."""
        entity = MockEntity(
            account_id="acc1",
            title="Test RFQ",
            quantity=100,
            due_date="2025-01-15",
        )
        result = sm.can_transition(entity, "received", "qualifying")
        
        assert result.allowed is True
    
    def test_received_to_qualifying_missing_fields(self, sm):
        """Test transition to qualifying blocked without completeness."""
        entity = MockEntity(account_id="acc1", title="Test RFQ")
        result = sm.can_transition(entity, "received", "qualifying")
        
        assert result.allowed is False
        assert "quantity" in result.missing_fields
        assert "due_date" in result.missing_fields
    
    def test_waiting_on_customer_flow(self, sm):
        """Test waiting on customer workflow."""
        # Can go to waiting
        result1 = sm.can_transition(MockEntity(), "received", "waiting_on_customer")
        assert result1.allowed is True
        
        # Can return from waiting
        result2 = sm.can_transition(MockEntity(), "waiting_on_customer", "received")
        assert result2.allowed is True
    
    def test_qualification_workflow(self, sm):
        """Test qualification to quoting workflow."""
        entity_qualified = MockEntity(qualification_decision="approved")
        result = sm.can_transition(entity_qualified, "qualifying", "qualified")
        assert result.allowed is True
        
        # Quoting
        result2 = sm.can_transition(MockEntity(), "qualified", "quoting")
        assert result2.allowed is True
        
        # Quoted
        result3 = sm.can_transition(MockEntity(), "quoting", "quoted")
        assert result3.allowed is True
    
    def test_no_bid_from_multiple_states(self, sm):
        """Test no bid can be reached from multiple states."""
        entity = MockEntity(no_bid_reason="Outside our capabilities")
        
        for state in ["draft", "received", "waiting_on_customer", "qualifying"]:
            result = sm.can_transition(entity, state, "no_bid")
            assert result.allowed is True, f"Should allow no_bid from {state}"


# =============================================================================
# Qualification State Machine Tests
# =============================================================================


class TestQualificationStateMachine:
    """Tests for the Qualification state machine."""
    
    @pytest.fixture
    def sm(self):
        """Create the qualification state machine."""
        return create_qualification_state_machine()
    
    def test_initial_state(self, sm):
        """Test qualification starts in not_started."""
        assert sm.initial_state == "not_started"
    
    def test_final_states(self, sm):
        """Test qualification final states."""
        assert "approved" in sm.final_states
        assert "rejected" in sm.final_states
        assert "override_approved" in sm.final_states
    
    def test_start_qualification(self, sm):
        """Test starting qualification."""
        entity = MockEntity(rfq_id="rfq-123")
        result = sm.can_transition(entity, "not_started", "in_progress")
        
        assert result.allowed is True
    
    def test_propose_decision(self, sm):
        """Test proposing a decision."""
        entity = MockEntity(
            proposed_decision="approve",
            decision_rationale="Good fit for our capabilities",
        )
        result = sm.can_transition(entity, "in_progress", "decision_proposed")
        
        assert result.allowed is True
    
    def test_approve_decision(self, sm):
        """Test approving qualification."""
        entity = MockEntity(approved_by="user-123")
        result = sm.can_transition(entity, "decision_proposed", "approved")
        
        assert result.allowed is True
    
    def test_reject_decision(self, sm):
        """Test rejecting qualification."""
        entity = MockEntity(rejected_by="user-123", rejection_reason="High risk")
        result = sm.can_transition(entity, "decision_proposed", "rejected")
        
        assert result.allowed is True
    
    def test_override_path(self, sm):
        """Test GM override path."""
        entity = MockEntity(
            override_by="gm-123",
            override_rationale="Strategic customer - must win",
        )
        result = sm.can_transition(entity, "in_progress", "override_approved")
        
        assert result.allowed is True


# =============================================================================
# Task State Machine Tests
# =============================================================================


class TestTaskStateMachine:
    """Tests for the Task state machine."""
    
    @pytest.fixture
    def sm(self):
        """Create the task state machine."""
        return create_task_state_machine()
    
    def test_initial_state(self, sm):
        """Test task starts in open state."""
        assert sm.initial_state == "open"
    
    def test_final_states(self, sm):
        """Test task final states."""
        assert "done" in sm.final_states
        assert "cancelled" in sm.final_states
    
    def test_start_task(self, sm):
        """Test starting a task."""
        result = sm.can_transition(MockEntity(), "open", "in_progress")
        assert result.allowed is True
    
    def test_block_task(self, sm):
        """Test blocking a task."""
        entity = MockEntity(blocked_reason="Waiting for parts")
        result = sm.can_transition(entity, "in_progress", "blocked")
        
        assert result.allowed is True
    
    def test_block_without_reason(self, sm):
        """Test blocking without reason is not allowed."""
        entity = MockEntity()
        result = sm.can_transition(entity, "in_progress", "blocked")
        
        assert result.allowed is False
        assert "blocked_reason" in result.missing_fields
    
    def test_unblock_task(self, sm):
        """Test unblocking a task."""
        result = sm.can_transition(MockEntity(), "blocked", "in_progress")
        assert result.allowed is True
    
    def test_complete_task(self, sm):
        """Test completing a task."""
        result = sm.can_transition(MockEntity(), "in_progress", "done")
        assert result.allowed is True
    
    def test_quick_complete(self, sm):
        """Test completing directly from open."""
        result = sm.can_transition(MockEntity(), "open", "done")
        assert result.allowed is True
    
    def test_cancel_from_any_state(self, sm):
        """Test cancelling from any non-final state."""
        for state in ["open", "in_progress", "blocked"]:
            result = sm.can_transition(MockEntity(), state, "cancelled")
            assert result.allowed is True, f"Should allow cancel from {state}"


# =============================================================================
# Registry Tests
# =============================================================================


class TestStateMachineRegistry:
    """Tests for the StateMachineRegistry."""
    
    def test_get_machine(self):
        """Test getting a machine by name."""
        machine = StateMachineRegistry.get("rfq")
        assert machine is not None
        assert machine.name == "RFQ"
    
    def test_get_machine_case_insensitive(self):
        """Test getting machine is case insensitive."""
        m1 = StateMachineRegistry.get("RFQ")
        m2 = StateMachineRegistry.get("rfq")
        m3 = StateMachineRegistry.get("Rfq")
        
        assert m1 is not None
        assert m1 == m2 == m3
    
    def test_get_unknown_machine(self):
        """Test getting unknown machine returns None."""
        machine = StateMachineRegistry.get("unknown")
        assert machine is None
    
    def test_list_machines(self):
        """Test listing all machines."""
        machines = StateMachineRegistry.list_machines()
        
        assert "rfq" in machines
        assert "opportunity" in machines
        assert "task" in machines
        assert "qualification" in machines
    
    def test_get_all(self):
        """Test getting all machines."""
        all_machines = StateMachineRegistry.get_all()
        
        assert len(all_machines) >= 4
        assert "rfq" in all_machines
        assert all_machines["rfq"].name == "RFQ"


# =============================================================================
# Gate Enforcer Tests
# =============================================================================


class TestGateEnforcer:
    """Tests for the GateEnforcer centralized validation."""
    
    @pytest.fixture
    def enforcer(self):
        """Create a gate enforcer."""
        return GateEnforcer()
    
    def test_check_transition_allowed(self, enforcer):
        """Test checking an allowed transition."""
        entity = {"account_id": "acc1", "contact_id": "con1"}
        result = enforcer.check_transition(
            entity_type="opportunity",
            entity=entity,
            from_state="suspect",
            to_state="prospect",
        )
        
        assert result.allowed is True
    
    def test_check_transition_blocked(self, enforcer):
        """Test checking a blocked transition."""
        entity = {}  # Missing required fields
        result = enforcer.check_transition(
            entity_type="opportunity",
            entity=entity,
            from_state="suspect",
            to_state="prospect",
        )
        
        assert result.allowed is False
        assert len(result.missing_fields) > 0
    
    def test_check_transition_unknown_type(self, enforcer):
        """Test checking with unknown entity type."""
        result = enforcer.check_transition(
            entity_type="unknown",
            entity={},
            from_state="a",
            to_state="b",
        )
        
        assert result.allowed is False
        assert "Unknown entity type" in result.error_message
    
    def test_check_transition_with_override(self, enforcer):
        """Test checking with override."""
        entity = {}  # Missing fields
        result = enforcer.check_transition(
            entity_type="opportunity",
            entity=entity,
            from_state="suspect",
            to_state="prospect",
            allow_override=True,
            override_rationale="Executive override",
        )
        
        assert result.allowed is True
    
    def test_check_transition_override_without_rationale(self, enforcer):
        """Test override without rationale is rejected."""
        entity = {}
        result = enforcer.check_transition(
            entity_type="opportunity",
            entity=entity,
            from_state="suspect",
            to_state="prospect",
            allow_override=True,
            override_rationale=None,  # No rationale
        )
        
        assert result.allowed is False
        assert "rationale" in result.error_message.lower()
    
    def test_get_available_transitions(self, enforcer):
        """Test getting available transitions."""
        transitions = enforcer.get_available_transitions("rfq", "draft")
        
        assert len(transitions) > 0
        target_states = [t["to_state"] for t in transitions]
        assert "received" in target_states
    
    def test_get_entity_state_info(self, enforcer):
        """Test getting entity state info."""
        info = enforcer.get_entity_state_info("task")
        
        assert info is not None
        assert info["name"] == "Task"
        assert info["initial_state"] == "open"
        assert "done" in info["final_states"]
        assert len(info["states"]) > 0
    
    def test_get_entity_state_info_unknown(self, enforcer):
        """Test getting unknown entity state info."""
        info = enforcer.get_entity_state_info("unknown")
        assert info is None


# =============================================================================
# TransitionResult Tests
# =============================================================================


class TestTransitionResult:
    """Tests for TransitionResult dataclass."""
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = TransitionResult(
            allowed=False,
            from_state="a",
            to_state="b",
            error_message="Missing fields",
            missing_fields=["field1", "field2"],
            failed_conditions=["Condition failed"],
            requires_override=True,
        )
        
        d = result.to_dict()
        
        assert d["allowed"] is False
        assert d["from_state"] == "a"
        assert d["to_state"] == "b"
        assert d["error_message"] == "Missing fields"
        assert "field1" in d["missing_fields"]
        assert "Condition failed" in d["failed_conditions"]
        assert d["requires_override"] is True


# =============================================================================
# Dictionary Entity Tests
# =============================================================================


class TestDictionaryEntity:
    """Test using dictionaries instead of dataclasses."""
    
    def test_transition_with_dict_entity(self):
        """Test transition check with dictionary entity."""
        sm = create_rfq_state_machine()
        
        entity = {
            "rfq_number": "RFQ-001",
            "account_id": "acc-123",
            "title": "Widget RFQ",
            "quantity": 100,
            "due_date": "2025-01-20",
        }
        
        result = sm.can_transition(entity, "received", "qualifying")
        assert result.allowed is True
    
    def test_enforcer_with_dict_entity(self):
        """Test gate enforcer with dictionary entity."""
        enforcer = GateEnforcer()
        
        entity = {
            "account_id": "acc-123",
            "contact_id": "con-456",
        }
        
        result = enforcer.check_transition(
            entity_type="opportunity",
            entity=entity,
            from_state="suspect",
            to_state="prospect",
        )
        
        assert result.allowed is True

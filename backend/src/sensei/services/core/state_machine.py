"""
State Machine & Gate Enforcement Service.

Implements formal state machines with:
- Defined allowed transitions between states
- Required fields for each transition (gates)
- Centralized enforcement for UI and API consistency
- Override mechanisms for authorized exceptions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import UUID


class TransitionError(Exception):
    """Raised when a state transition is not allowed."""
    
    def __init__(self, message: str, from_state: str, to_state: str, missing_fields: list[str] | None = None):
        super().__init__(message)
        self.from_state = from_state
        self.to_state = to_state
        self.missing_fields = missing_fields or []


@dataclass
class TransitionRule:
    """Defines a state transition rule."""
    
    from_state: str
    to_state: str
    required_fields: list[str] = field(default_factory=list)
    conditions: list[Callable[[Any], tuple[bool, str | None]]] = field(default_factory=list)
    requires_override: bool = False
    override_reason_required: bool = True
    description: str = ""


@dataclass
class TransitionResult:
    """Result of a transition attempt."""
    
    allowed: bool
    from_state: str
    to_state: str
    error_message: str | None = None
    missing_fields: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    requires_override: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "error_message": self.error_message,
            "missing_fields": self.missing_fields,
            "failed_conditions": self.failed_conditions,
            "requires_override": self.requires_override,
        }


class StateMachine:
    """
    Generic state machine with gate enforcement.
    """
    
    def __init__(
        self,
        name: str,
        states: list[str],
        initial_state: str,
        final_states: list[str] | None = None,
    ):
        """
        Initialize the state machine.
        
        Args:
            name: Name of this state machine (e.g., "RFQ", "Opportunity")
            states: List of all valid states
            initial_state: The starting state for new entities
            final_states: Terminal states that cannot be transitioned from
        """
        self.name = name
        self.states = set(states)
        self.initial_state = initial_state
        self.final_states = set(final_states or [])
        self.transitions: dict[tuple[str, str], TransitionRule] = {}
    
    def add_transition(
        self,
        from_state: str,
        to_state: str,
        required_fields: list[str] | None = None,
        conditions: list[Callable[[Any], tuple[bool, str | None]]] | None = None,
        requires_override: bool = False,
        description: str = "",
    ) -> None:
        """
        Add a transition rule.
        
        Args:
            from_state: Source state
            to_state: Target state
            required_fields: Fields that must be filled for this transition
            conditions: Callable conditions that must pass
            requires_override: Whether this transition always requires override
            description: Human-readable description of this transition
        """
        if from_state not in self.states:
            raise ValueError(f"Invalid from_state: {from_state}")
        if to_state not in self.states:
            raise ValueError(f"Invalid to_state: {to_state}")
        
        rule = TransitionRule(
            from_state=from_state,
            to_state=to_state,
            required_fields=required_fields or [],
            conditions=conditions or [],
            requires_override=requires_override,
            description=description,
        )
        self.transitions[(from_state, to_state)] = rule
    
    def can_transition(
        self,
        entity: Any,
        from_state: str,
        to_state: str,
        allow_override: bool = False,
    ) -> TransitionResult:
        """
        Check if a transition is allowed.
        
        Args:
            entity: The entity being transitioned (model instance or dict)
            from_state: Current state
            to_state: Target state
            allow_override: Whether override is being used
            
        Returns:
            TransitionResult with details about the check
        """
        # Check if this is a valid transition
        rule = self.transitions.get((from_state, to_state))
        if rule is None:
            return TransitionResult(
                allowed=False,
                from_state=from_state,
                to_state=to_state,
                error_message=f"Transition from '{from_state}' to '{to_state}' is not allowed",
            )
        
        # Check if from_state is final
        if from_state in self.final_states:
            return TransitionResult(
                allowed=False,
                from_state=from_state,
                to_state=to_state,
                error_message=f"Cannot transition from final state '{from_state}'",
            )
        
        # Check required fields
        missing_fields = []
        for field_name in rule.required_fields:
            value = self._get_field_value(entity, field_name)
            if not self._is_filled(value):
                missing_fields.append(field_name)
        
        # Check conditions
        failed_conditions = []
        for condition in rule.conditions:
            passed, error_msg = condition(entity)
            if not passed:
                failed_conditions.append(error_msg or "Condition failed")
        
        # Determine if transition is allowed
        has_issues = bool(missing_fields) or bool(failed_conditions)
        requires_override = rule.requires_override or has_issues
        
        if has_issues and not allow_override:
            error_parts = []
            if missing_fields:
                error_parts.append(f"Missing required fields: {', '.join(missing_fields)}")
            if failed_conditions:
                error_parts.append(f"Failed conditions: {'; '.join(failed_conditions)}")
            
            return TransitionResult(
                allowed=False,
                from_state=from_state,
                to_state=to_state,
                error_message="; ".join(error_parts),
                missing_fields=missing_fields,
                failed_conditions=failed_conditions,
                requires_override=True,
            )
        
        return TransitionResult(
            allowed=True,
            from_state=from_state,
            to_state=to_state,
            requires_override=allow_override and has_issues,
        )
    
    def get_allowed_transitions(self, from_state: str) -> list[str]:
        """Get all states that can be transitioned to from the given state."""
        allowed = []
        for (f, t), rule in self.transitions.items():
            if f == from_state:
                allowed.append(t)
        return allowed
    
    def get_transition_requirements(self, from_state: str, to_state: str) -> dict | None:
        """Get the requirements for a specific transition."""
        rule = self.transitions.get((from_state, to_state))
        if rule is None:
            return None
        
        return {
            "from_state": rule.from_state,
            "to_state": rule.to_state,
            "required_fields": rule.required_fields,
            "requires_override": rule.requires_override,
            "description": rule.description,
        }
    
    def get_all_states(self) -> list[dict]:
        """Get all states with metadata."""
        return [
            {
                "state": s,
                "is_initial": s == self.initial_state,
                "is_final": s in self.final_states,
                "allowed_transitions": self.get_allowed_transitions(s),
            }
            for s in sorted(self.states)
        ]
    
    def _get_field_value(self, entity: Any, field_name: str) -> Any:
        """Get a field value from an entity."""
        if isinstance(entity, dict):
            return entity.get(field_name)
        return getattr(entity, field_name, None)
    
    def _is_filled(self, value: Any) -> bool:
        """Check if a value is considered filled."""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True


# =============================================================================
# Pre-configured State Machines
# =============================================================================


def create_opportunity_state_machine() -> StateMachine:
    """
    Create the Opportunity state machine.
    
    States: Suspect → Prospect → Qualified → Proposal → Negotiation → Won/Lost
    """
    sm = StateMachine(
        name="Opportunity",
        states=[
            "suspect",
            "prospect",
            "qualified",
            "proposal",
            "negotiation",
            "won",
            "lost",
            "on_hold",
        ],
        initial_state="suspect",
        final_states=["won", "lost"],
    )
    
    # Suspect → Prospect: Need account and contact
    sm.add_transition(
        from_state="suspect",
        to_state="prospect",
        required_fields=["account_id", "contact_id"],
        description="Convert suspect to prospect after initial contact",
    )
    
    # Prospect → Qualified: Need value estimate
    sm.add_transition(
        from_state="prospect",
        to_state="qualified",
        required_fields=["estimated_value", "probability"],
        description="Qualify prospect after confirming budget and timeline",
    )
    
    # Qualified → Proposal: Need RFQ or quote
    sm.add_transition(
        from_state="qualified",
        to_state="proposal",
        required_fields=["expected_close_date"],
        description="Move to proposal stage when preparing quote",
    )
    
    # Proposal → Negotiation
    sm.add_transition(
        from_state="proposal",
        to_state="negotiation",
        description="Enter negotiation after quote submitted",
    )
    
    # Negotiation → Won
    sm.add_transition(
        from_state="negotiation",
        to_state="won",
        required_fields=["actual_value"],
        description="Close opportunity as won",
    )
    
    # Negotiation → Lost
    sm.add_transition(
        from_state="negotiation",
        to_state="lost",
        required_fields=["lost_reason"],
        description="Close opportunity as lost",
    )
    
    # On hold transitions (from multiple states)
    for state in ["prospect", "qualified", "proposal", "negotiation"]:
        sm.add_transition(
            from_state=state,
            to_state="on_hold",
            required_fields=["hold_reason"],
            description=f"Put {state} opportunity on hold",
        )
        sm.add_transition(
            from_state="on_hold",
            to_state=state,
            description=f"Resume opportunity from hold to {state}",
        )
    
    # Direct loss from any active state
    for state in ["suspect", "prospect", "qualified", "proposal"]:
        sm.add_transition(
            from_state=state,
            to_state="lost",
            required_fields=["lost_reason"],
            description=f"Mark {state} opportunity as lost",
        )
    
    return sm


def create_rfq_state_machine() -> StateMachine:
    """
    Create the RFQ state machine.
    
    States: Draft → Received → Waiting on Customer → Qualifying → Qualified/Not Qualified → Quoting → Quoted → Won/Lost/No Bid
    """
    sm = StateMachine(
        name="RFQ",
        states=[
            "draft",
            "received",
            "waiting_on_customer",
            "qualifying",
            "qualified",
            "not_qualified",
            "quoting",
            "quoted",
            "won",
            "lost",
            "no_bid",
            "cancelled",
        ],
        initial_state="draft",
        final_states=["won", "lost", "no_bid", "cancelled"],
    )
    
    # Draft → Received: RFQ formally received
    sm.add_transition(
        from_state="draft",
        to_state="received",
        required_fields=["rfq_number", "account_id", "title"],
        description="Formally receive the RFQ",
    )
    
    # Received → Waiting on Customer: Need more info
    sm.add_transition(
        from_state="received",
        to_state="waiting_on_customer",
        description="Waiting for customer to provide missing information",
    )
    
    # Waiting on Customer → Received: Info received
    sm.add_transition(
        from_state="waiting_on_customer",
        to_state="received",
        description="Customer provided requested information",
    )
    
    # Received → Qualifying: Begin qualification (completeness check)
    sm.add_transition(
        from_state="received",
        to_state="qualifying",
        required_fields=["account_id", "title", "quantity", "due_date"],
        description="Begin qualification process (requires minimum completeness)",
    )
    
    # Also allow direct from waiting_on_customer
    sm.add_transition(
        from_state="waiting_on_customer",
        to_state="qualifying",
        required_fields=["account_id", "title", "quantity", "due_date"],
        description="Begin qualification after receiving info",
    )
    
    # Qualifying → Qualified: Qualification approved
    sm.add_transition(
        from_state="qualifying",
        to_state="qualified",
        required_fields=["qualification_decision"],
        description="Qualification approved - proceed to quoting",
    )
    
    # Qualifying → Not Qualified: Declined to quote
    sm.add_transition(
        from_state="qualifying",
        to_state="not_qualified",
        required_fields=["disqualification_reason"],
        description="Declined to quote with reason",
    )
    
    # Qualified → Quoting: Begin quote preparation
    sm.add_transition(
        from_state="qualified",
        to_state="quoting",
        description="Begin preparing quote",
    )
    
    # Quoting → Quoted: Quote submitted
    sm.add_transition(
        from_state="quoting",
        to_state="quoted",
        description="Quote submitted to customer",
    )
    
    # Quoted → Won/Lost
    sm.add_transition(
        from_state="quoted",
        to_state="won",
        description="Customer accepted quote",
    )
    sm.add_transition(
        from_state="quoted",
        to_state="lost",
        required_fields=["lost_reason"],
        description="Customer rejected quote",
    )
    
    # No bid from various stages
    for state in ["draft", "received", "waiting_on_customer", "qualifying"]:
        sm.add_transition(
            from_state=state,
            to_state="no_bid",
            required_fields=["no_bid_reason"],
            description=f"Decline to bid from {state}",
        )
    
    # Cancel from any non-final state
    for state in ["draft", "received", "waiting_on_customer", "qualifying", "qualified", "quoting", "quoted"]:
        sm.add_transition(
            from_state=state,
            to_state="cancelled",
            required_fields=["cancellation_reason"],
            description=f"Cancel RFQ from {state}",
        )
    
    return sm


def create_qualification_state_machine() -> StateMachine:
    """
    Create the Qualification state machine.
    
    States: Not Started → In Progress → Decision Proposed → Approved/Rejected
    """
    sm = StateMachine(
        name="Qualification",
        states=[
            "not_started",
            "in_progress",
            "on_hold",
            "decision_proposed",
            "approved",
            "rejected",
            "override_approved",
        ],
        initial_state="not_started",
        final_states=["approved", "rejected", "override_approved"],
    )
    
    # Not Started → In Progress
    sm.add_transition(
        from_state="not_started",
        to_state="in_progress",
        required_fields=["rfq_id"],
        description="Begin qualification review",
    )
    
    # In Progress → Decision Proposed
    sm.add_transition(
        from_state="in_progress",
        to_state="decision_proposed",
        required_fields=["proposed_decision", "decision_rationale"],
        description="Propose qualification decision",
    )
    
    # In Progress → On Hold
    sm.add_transition(
        from_state="in_progress",
        to_state="on_hold",
        required_fields=["hold_reason"],
        description="Put qualification on hold",
    )
    
    # On Hold → In Progress
    sm.add_transition(
        from_state="on_hold",
        to_state="in_progress",
        description="Resume qualification",
    )
    
    # Decision Proposed → Approved
    sm.add_transition(
        from_state="decision_proposed",
        to_state="approved",
        required_fields=["approved_by"],
        description="Approve qualification",
    )
    
    # Decision Proposed → Rejected
    sm.add_transition(
        from_state="decision_proposed",
        to_state="rejected",
        required_fields=["rejected_by", "rejection_reason"],
        description="Reject qualification",
    )
    
    # Override path (skips normal approval)
    sm.add_transition(
        from_state="in_progress",
        to_state="override_approved",
        required_fields=["override_by", "override_rationale"],
        requires_override=True,
        description="GM override approval",
    )
    
    return sm


def create_task_state_machine() -> StateMachine:
    """
    Create the Task state machine.
    
    States: Open → In Progress → Blocked → Done
    """
    sm = StateMachine(
        name="Task",
        states=[
            "open",
            "in_progress",
            "blocked",
            "done",
            "cancelled",
        ],
        initial_state="open",
        final_states=["done", "cancelled"],
    )
    
    # Open → In Progress
    sm.add_transition(
        from_state="open",
        to_state="in_progress",
        description="Start working on task",
    )
    
    # In Progress → Blocked
    sm.add_transition(
        from_state="in_progress",
        to_state="blocked",
        required_fields=["blocked_reason"],
        description="Mark task as blocked",
    )
    
    # Blocked → In Progress
    sm.add_transition(
        from_state="blocked",
        to_state="in_progress",
        description="Unblock and resume task",
    )
    
    # In Progress → Done
    sm.add_transition(
        from_state="in_progress",
        to_state="done",
        description="Complete task",
    )
    
    # Open → Done (for quick completion)
    sm.add_transition(
        from_state="open",
        to_state="done",
        description="Complete task directly",
    )
    
    # Cancel from any non-final state
    for state in ["open", "in_progress", "blocked"]:
        sm.add_transition(
            from_state=state,
            to_state="cancelled",
            description=f"Cancel task from {state}",
        )
    
    return sm


# =============================================================================
# State Machine Registry
# =============================================================================


class StateMachineRegistry:
    """
    Registry of all state machines for centralized access.
    """
    
    _machines: dict[str, StateMachine] = {}
    _initialized: bool = False
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize all state machines."""
        if cls._initialized:
            return
        
        cls._machines = {
            "opportunity": create_opportunity_state_machine(),
            "rfq": create_rfq_state_machine(),
            "qualification": create_qualification_state_machine(),
            "task": create_task_state_machine(),
        }
        cls._initialized = True
    
    @classmethod
    def get(cls, name: str) -> StateMachine | None:
        """Get a state machine by name."""
        cls.initialize()
        return cls._machines.get(name.lower())
    
    @classmethod
    def list_machines(cls) -> list[str]:
        """List all available state machines."""
        cls.initialize()
        return list(cls._machines.keys())
    
    @classmethod
    def get_all(cls) -> dict[str, StateMachine]:
        """Get all state machines."""
        cls.initialize()
        return cls._machines.copy()


# =============================================================================
# Gate Enforcement Service
# =============================================================================


class GateEnforcer:
    """
    Centralized gate enforcement service.
    
    Ensures UI and API always enforce the same constraints.
    """
    
    def __init__(self):
        """Initialize the gate enforcer."""
        StateMachineRegistry.initialize()
    
    def check_transition(
        self,
        entity_type: str,
        entity: Any,
        from_state: str,
        to_state: str,
        allow_override: bool = False,
        override_rationale: str | None = None,
    ) -> TransitionResult:
        """
        Check if a state transition is allowed.
        
        Args:
            entity_type: Type of entity (rfq, opportunity, task, etc.)
            entity: The entity instance
            from_state: Current state
            to_state: Target state
            allow_override: Whether to use override
            override_rationale: Rationale for override (if applicable)
            
        Returns:
            TransitionResult with check details
        """
        machine = StateMachineRegistry.get(entity_type)
        if machine is None:
            return TransitionResult(
                allowed=False,
                from_state=from_state,
                to_state=to_state,
                error_message=f"Unknown entity type: {entity_type}",
            )
        
        result = machine.can_transition(entity, from_state, to_state, allow_override)
        
        # If override is used but no rationale provided
        if allow_override and result.requires_override and not override_rationale:
            return TransitionResult(
                allowed=False,
                from_state=from_state,
                to_state=to_state,
                error_message="Override rationale is required when using override",
                requires_override=True,
            )
        
        return result
    
    def get_available_transitions(
        self,
        entity_type: str,
        current_state: str,
    ) -> list[dict]:
        """
        Get all available transitions from the current state.
        
        Args:
            entity_type: Type of entity
            current_state: Current state
            
        Returns:
            List of available transitions with requirements
        """
        machine = StateMachineRegistry.get(entity_type)
        if machine is None:
            return []
        
        allowed_states = machine.get_allowed_transitions(current_state)
        transitions = []
        
        for to_state in allowed_states:
            reqs = machine.get_transition_requirements(current_state, to_state)
            if reqs:
                transitions.append(reqs)
        
        return transitions
    
    def get_entity_state_info(
        self,
        entity_type: str,
    ) -> dict | None:
        """
        Get full state machine info for an entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Dictionary with all states and transitions
        """
        machine = StateMachineRegistry.get(entity_type)
        if machine is None:
            return None
        
        return {
            "name": machine.name,
            "initial_state": machine.initial_state,
            "final_states": list(machine.final_states),
            "states": machine.get_all_states(),
        }

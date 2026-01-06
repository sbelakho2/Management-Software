"""
State Machine & Gate Enforcement API Endpoints.

Provides centralized state management:
- Query allowed transitions for entities
- Validate transitions before applying
- Get state machine definitions
- Enforce gates consistently across UI and API
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from sensei.api.deps import CurrentUser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.services.state_machine import (
    GateEnforcer,
    StateMachineRegistry,
)


router = APIRouter(tags=["State Machines"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class TransitionCheckRequest(BaseModel):
    """Request to check if a transition is allowed."""
    
    entity_type: str = Field(
        ...,
        description="Type of entity (rfq, opportunity, task, qualification)",
    )
    from_state: str = Field(..., description="Current state of the entity")
    to_state: str = Field(..., description="Target state for transition")
    entity_data: dict = Field(
        default_factory=dict,
        description="Entity data for field validation",
    )
    allow_override: bool = Field(
        default=False,
        description="Whether to use override for this transition",
    )
    override_rationale: Optional[str] = Field(
        default=None,
        description="Rationale for override (required if allow_override=True)",
    )
    
    model_config = ConfigDict(from_attributes=True)


class TransitionCheckResponse(BaseModel):
    """Response from transition check."""
    
    allowed: bool
    from_state: str
    to_state: str
    error_message: Optional[str] = None
    missing_fields: list[str]
    failed_conditions: list[str]
    requires_override: bool
    
    model_config = ConfigDict(from_attributes=True)


class TransitionRequirement(BaseModel):
    """Requirements for a transition."""
    
    from_state: str
    to_state: str
    required_fields: list[str]
    requires_override: bool
    description: str
    
    model_config = ConfigDict(from_attributes=True)


class StateInfo(BaseModel):
    """Information about a state."""
    
    state: str
    is_initial: bool
    is_final: bool
    allowed_transitions: list[str]
    
    model_config = ConfigDict(from_attributes=True)


class StateMachineInfo(BaseModel):
    """Full state machine information."""
    
    name: str
    initial_state: str
    final_states: list[str]
    states: list[StateInfo]
    
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=APIResponse)
async def list_state_machines(
    current_user: CurrentUser,
):
    """
    List all available state machines.
    
    Returns the names of all state machines that can be queried.
    """
    machines = StateMachineRegistry.list_machines()
    
    return build_response(data={
        "machines": machines,
        "count": len(machines),
    })


@router.get("/{entity_type}", response_model=APIResponse)
async def get_state_machine(
    entity_type: str,
    current_user: CurrentUser,
):
    """
    Get full state machine definition for an entity type.
    
    Returns all states, transitions, and requirements.
    """
    enforcer = GateEnforcer()
    info = enforcer.get_entity_state_info(entity_type)
    
    if info is None:
        from sensei.api.exceptions import NotFoundError
        raise NotFoundError(resource="State Machine", identifier=entity_type)
    
    return build_response(data=info)


@router.get("/{entity_type}/transitions", response_model=APIResponse)
async def get_available_transitions(
    entity_type: str,
    current_state: str,
    current_user: CurrentUser,
):
    """
    Get available transitions from a current state.
    
    Returns all valid target states with their requirements.
    """
    enforcer = GateEnforcer()
    
    # Verify entity type exists
    info = enforcer.get_entity_state_info(entity_type)
    if info is None:
        from sensei.api.exceptions import NotFoundError
        raise NotFoundError(resource="State Machine", identifier=entity_type)
    
    transitions = enforcer.get_available_transitions(entity_type, current_state)
    
    return build_response(data={
        "entity_type": entity_type,
        "current_state": current_state,
        "transitions": transitions,
        "count": len(transitions),
    })


@router.post("/check-transition", response_model=APIResponse)
async def check_transition(
    request: TransitionCheckRequest,
    current_user: CurrentUser,
):
    """
    Check if a state transition is allowed.
    
    Validates:
    - The transition is defined in the state machine
    - All required fields are present
    - Any custom conditions are met
    - Override requirements if applicable
    
    This allows the UI to validate before attempting the actual transition.
    """
    enforcer = GateEnforcer()
    
    result = enforcer.check_transition(
        entity_type=request.entity_type,
        entity=request.entity_data,
        from_state=request.from_state,
        to_state=request.to_state,
        allow_override=request.allow_override,
        override_rationale=request.override_rationale,
    )
    
    response = TransitionCheckResponse(
        allowed=result.allowed,
        from_state=result.from_state,
        to_state=result.to_state,
        error_message=result.error_message,
        missing_fields=result.missing_fields,
        failed_conditions=result.failed_conditions,
        requires_override=result.requires_override,
    )
    
    return build_response(data=response.model_dump())


@router.get("/{entity_type}/states/{state}/requirements", response_model=APIResponse)
async def get_transition_requirements(
    entity_type: str,
    state: str,
    to_state: str = Query(..., description="Target state to get requirements for"),
    current_user: CurrentUser = None,
):
    """
    Get requirements for a specific transition.
    
    Returns the required fields and conditions for transitioning
    from the given state to the target state.
    """
    machine = StateMachineRegistry.get(entity_type)
    if machine is None:
        from sensei.api.exceptions import NotFoundError
        raise NotFoundError(resource="State Machine", identifier=entity_type)
    
    requirements = machine.get_transition_requirements(state, to_state)
    
    if requirements is None:
        from sensei.api.exceptions import NotFoundError
        raise NotFoundError(
            resource="Transition",
            identifier=f"{state} -> {to_state}",
        )
    
    return build_response(data=requirements)

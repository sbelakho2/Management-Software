"""
Tests for State Machine API Endpoints.

Tests the state machine REST API including:
- Listing state machines
- Getting state machine definitions
- Checking transitions
- Getting transition requirements
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sensei.api.v1.endpoints.state_machines import (
    router,
    list_state_machines,
    get_state_machine,
    get_available_transitions,
    check_transition,
    get_transition_requirements,
    TransitionCheckRequest,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.is_superuser = False
    return user


# =============================================================================
# List State Machines Tests
# =============================================================================


class TestListStateMachines:
    """Tests for listing state machines."""
    
    @pytest.mark.asyncio
    async def test_list_state_machines(self, mock_user):
        """Should list all available state machines."""
        response = await list_state_machines(current_user=mock_user)
        
        assert response.success is True
        assert "machines" in response.data
        assert "rfq" in response.data["machines"]
        assert "opportunity" in response.data["machines"]
        assert "task" in response.data["machines"]
        assert "qualification" in response.data["machines"]
        assert response.data["count"] >= 4


# =============================================================================
# Get State Machine Tests
# =============================================================================


class TestGetStateMachine:
    """Tests for getting state machine definitions."""
    
    @pytest.mark.asyncio
    async def test_get_rfq_state_machine(self, mock_user):
        """Should get RFQ state machine definition."""
        response = await get_state_machine(
            entity_type="rfq",
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["name"] == "RFQ"
        assert response.data["initial_state"] == "draft"
        assert "won" in response.data["final_states"]
        assert len(response.data["states"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_opportunity_state_machine(self, mock_user):
        """Should get Opportunity state machine definition."""
        response = await get_state_machine(
            entity_type="opportunity",
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["name"] == "Opportunity"
        assert response.data["initial_state"] == "suspect"
    
    @pytest.mark.asyncio
    async def test_get_task_state_machine(self, mock_user):
        """Should get Task state machine definition."""
        response = await get_state_machine(
            entity_type="task",
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["name"] == "Task"
        assert response.data["initial_state"] == "open"
    
    @pytest.mark.asyncio
    async def test_get_unknown_state_machine(self, mock_user):
        """Should return 404 for unknown state machine."""
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_state_machine(
                entity_type="unknown",
                current_user=mock_user,
            )


# =============================================================================
# Get Available Transitions Tests
# =============================================================================


class TestGetAvailableTransitions:
    """Tests for getting available transitions."""
    
    @pytest.mark.asyncio
    async def test_get_rfq_draft_transitions(self, mock_user):
        """Should get available transitions from RFQ draft state."""
        response = await get_available_transitions(
            entity_type="rfq",
            current_state="draft",
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["entity_type"] == "rfq"
        assert response.data["current_state"] == "draft"
        assert response.data["count"] > 0
        
        target_states = [t["to_state"] for t in response.data["transitions"]]
        assert "received" in target_states
    
    @pytest.mark.asyncio
    async def test_get_task_open_transitions(self, mock_user):
        """Should get available transitions from task open state."""
        response = await get_available_transitions(
            entity_type="task",
            current_state="open",
            current_user=mock_user,
        )
        
        assert response.success is True
        target_states = [t["to_state"] for t in response.data["transitions"]]
        assert "in_progress" in target_states
        assert "done" in target_states
    
    @pytest.mark.asyncio
    async def test_get_transitions_unknown_type(self, mock_user):
        """Should return 404 for unknown entity type."""
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_available_transitions(
                entity_type="unknown",
                current_state="draft",
                current_user=mock_user,
            )


# =============================================================================
# Check Transition Tests
# =============================================================================


class TestCheckTransition:
    """Tests for checking transitions."""
    
    @pytest.mark.asyncio
    async def test_check_allowed_transition(self, mock_user):
        """Should allow valid transition with required fields."""
        request = TransitionCheckRequest(
            entity_type="opportunity",
            from_state="suspect",
            to_state="prospect",
            entity_data={
                "account_id": "acc-123",
                "contact_id": "con-456",
            },
        )
        
        response = await check_transition(
            request=request,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["allowed"] is True
        assert response.data["from_state"] == "suspect"
        assert response.data["to_state"] == "prospect"
    
    @pytest.mark.asyncio
    async def test_check_blocked_transition(self, mock_user):
        """Should block transition with missing required fields."""
        request = TransitionCheckRequest(
            entity_type="opportunity",
            from_state="suspect",
            to_state="prospect",
            entity_data={},  # Missing account_id and contact_id
        )
        
        response = await check_transition(
            request=request,
            current_user=mock_user,
        )
        
        assert response.success is True  # API call succeeded
        assert response.data["allowed"] is False
        assert len(response.data["missing_fields"]) > 0
        assert response.data["requires_override"] is True
    
    @pytest.mark.asyncio
    async def test_check_transition_with_override(self, mock_user):
        """Should allow blocked transition with override."""
        request = TransitionCheckRequest(
            entity_type="opportunity",
            from_state="suspect",
            to_state="prospect",
            entity_data={},  # Missing fields
            allow_override=True,
            override_rationale="Executive approval granted",
        )
        
        response = await check_transition(
            request=request,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["allowed"] is True
    
    @pytest.mark.asyncio
    async def test_check_invalid_transition(self, mock_user):
        """Should reject undefined transition."""
        request = TransitionCheckRequest(
            entity_type="rfq",
            from_state="draft",
            to_state="won",  # Cannot go directly from draft to won
            entity_data={},
        )
        
        response = await check_transition(
            request=request,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["allowed"] is False
        assert "not allowed" in response.data["error_message"]
    
    @pytest.mark.asyncio
    async def test_check_transition_unknown_type(self, mock_user):
        """Should handle unknown entity type gracefully."""
        request = TransitionCheckRequest(
            entity_type="unknown",
            from_state="a",
            to_state="b",
            entity_data={},
        )
        
        response = await check_transition(
            request=request,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["allowed"] is False
        assert "Unknown entity type" in response.data["error_message"]


# =============================================================================
# Get Transition Requirements Tests
# =============================================================================


class TestGetTransitionRequirements:
    """Tests for getting transition requirements."""
    
    @pytest.mark.asyncio
    async def test_get_requirements(self, mock_user):
        """Should get requirements for a valid transition."""
        response = await get_transition_requirements(
            entity_type="opportunity",
            state="suspect",
            to_state="prospect",
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["from_state"] == "suspect"
        assert response.data["to_state"] == "prospect"
        assert "account_id" in response.data["required_fields"]
        assert "contact_id" in response.data["required_fields"]
    
    @pytest.mark.asyncio
    async def test_get_requirements_no_required_fields(self, mock_user):
        """Should return empty required_fields when none needed."""
        response = await get_transition_requirements(
            entity_type="task",
            state="open",
            to_state="in_progress",
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data["required_fields"] == []
    
    @pytest.mark.asyncio
    async def test_get_requirements_unknown_type(self, mock_user):
        """Should return 404 for unknown entity type."""
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_transition_requirements(
                entity_type="unknown",
                state="a",
                to_state="b",
                current_user=mock_user,
            )
    
    @pytest.mark.asyncio
    async def test_get_requirements_invalid_transition(self, mock_user):
        """Should return 404 for undefined transition."""
        from sensei.api.exceptions import NotFoundError
        
        with pytest.raises(NotFoundError):
            await get_transition_requirements(
                entity_type="rfq",
                state="draft",
                to_state="won",  # Invalid direct transition
                current_user=mock_user,
            )

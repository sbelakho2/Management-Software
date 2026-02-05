"""
Tests for Quote Approval Time Tracking API Endpoints.

Tests the REST API for quote approval with < 60 second target.
"""

import time
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.api import deps
from sensei.services.sales.quote_approval_time_tracking import reset_quote_approval_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service before each test."""
    reset_quote_approval_service()
    yield
    reset_quote_approval_service()


@pytest.fixture(autouse=True)
def override_auth():
    """Force authenticated access for quote approval endpoints."""

    async def _mock_get_current_active_user():
        user = MagicMock()
        user.id = uuid4()
        user.status = "active"
        return user

    app.dependency_overrides[deps.get_current_active_user] = _mock_get_current_active_user
    yield
    app.dependency_overrides.pop(deps.get_current_active_user, None)


@pytest.fixture
def sample_context():
    """Sample quote context for testing."""
    return {
        "quote_id": str(uuid4()),
        "quote_number": "Q-2025-001",
        "version": 1,
        "customer_name": "Acme Corp",
        "total_value": 50000.00,
        "margin_percent": 35.0,
        "line_item_count": 5,
        "currency": "USD",
        "requested_by": str(uuid4()),
        "urgency": "normal",
        "notes": "Standard approval",
    }


@pytest.fixture
def sample_approver_id():
    """Sample approver ID."""
    return str(uuid4())


# ===== Session Endpoint Tests =====


class TestStartApprovalSession:
    """Tests for POST /quote-approval/sessions."""
    
    def test_start_session_success(self, client, sample_context, sample_approver_id):
        """Test starting an approval session."""
        response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["quote_id"] == sample_context["quote_id"]
        assert data["approver_id"] == sample_approver_id
        assert data["status"] == "started"
        assert data["decision"] is None
        assert len(data["criteria"]) > 0
        assert data["context"]["customer_name"] == "Acme Corp"
    
    def test_start_session_invalid_approver_id(self, client, sample_context):
        """Test with invalid approver ID."""
        response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": "not-a-uuid",
                "context": sample_context,
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid UUID" in response.json()["message"]
    
    def test_start_session_missing_context(self, client, sample_approver_id):
        """Test with missing context."""
        response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
            },
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestGetSession:
    """Tests for GET /quote-approval/sessions/{session_id}."""
    
    def test_get_session_success(self, client, sample_context, sample_approver_id):
        """Test getting a session."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Get session
        response = client.get(f"/api/v1/quote-approval/sessions/{session_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == session_id
    
    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/quote-approval/sessions/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetCountdownStatus:
    """Tests for GET /quote-approval/sessions/{session_id}/countdown."""
    
    def test_countdown_status_success(self, client, sample_context, sample_approver_id):
        """Test getting countdown status."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Get countdown
        response = client.get(f"/api/v1/quote-approval/sessions/{session_id}/countdown")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["session_id"] == session_id
        assert data["target_seconds"] == 60
        assert data["elapsed_seconds"] >= 0
        assert data["remaining_seconds"] <= 60
        assert data["status"] == "on_track"
    
    def test_countdown_not_found(self, client):
        """Test countdown for non-existent session."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/quote-approval/sessions/{fake_id}/countdown")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMakeDecision:
    """Tests for POST /quote-approval/sessions/{session_id}/decide."""
    
    def test_approve_success(self, client, sample_context, sample_approver_id):
        """Test approving a quote."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Make decision
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "approved",
                "reason": "margin_acceptable",
                "comments": "Good quote",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "decided"
        assert data["decision"] == "approved"
        assert data["reason"] == "margin_acceptable"
    
    def test_reject_quote(self, client, sample_context, sample_approver_id):
        """Test rejecting a quote."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Reject
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "rejected",
                "reason": "margin_too_low",
                "comments": "Margin below threshold",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["decision"] == "rejected"
    
    def test_escalate_quote(self, client, sample_context, sample_approver_id):
        """Test escalating a quote."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        escalate_to = str(uuid4())
        
        # Escalate
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "escalated",
                "reason": "exceeds_authority",
                "escalated_to": escalate_to,
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["decision"] == "escalated"
        assert response.json()["escalated_to"] == escalate_to
    
    def test_invalid_decision(self, client, sample_context, sample_approver_id):
        """Test with invalid decision."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "invalid_decision",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid decision" in response.json()["message"]


class TestQuickApprove:
    """Tests for POST /quote-approval/sessions/{session_id}/quick-approve."""
    
    def test_quick_approve_success(self, client, sample_context, sample_approver_id):
        """Test quick approval."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Quick approve
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/quick-approve",
            json={
                "option_id": "quick_approve",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "decided"
        assert data["decision"] == "approved"
    
    def test_quick_approve_strategic(self, client, sample_context, sample_approver_id):
        """Test strategic quick approval."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Quick approve strategic (requires comment)
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/quick-approve",
            json={
                "option_id": "approve_strategic",
                "comments": "Strategic customer relationship",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["reason"] == "strategic_importance"
    
    def test_quick_approve_invalid_option(self, client, sample_context, sample_approver_id):
        """Test with invalid quick option."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/quick-approve",
            json={
                "option_id": "invalid_option",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdateCriterion:
    """Tests for POST /quote-approval/sessions/{session_id}/criterion."""
    
    def test_update_criterion_success(self, client, sample_context, sample_approver_id):
        """Test updating a criterion."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Update criterion
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/criterion",
            json={
                "criterion_id": "margin_check",
                "status": "passed",
                "message": "Margin verified",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Find the updated criterion
        criteria = response.json()["criteria"]
        margin_criterion = next((c for c in criteria if c["id"] == "margin_check"), None)
        assert margin_criterion is not None
        assert margin_criterion["status"] == "passed"
    
    def test_update_criterion_invalid_status(self, client, sample_context, sample_approver_id):
        """Test with invalid criterion status."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/criterion",
            json={
                "criterion_id": "margin_check",
                "status": "invalid_status",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAbandonSession:
    """Tests for POST /quote-approval/sessions/{session_id}/abandon."""
    
    def test_abandon_success(self, client, sample_context, sample_approver_id):
        """Test abandoning a session."""
        # Create session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        # Abandon
        response = client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/abandon",
            json={
                "reason": "Need more information",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "abandoned"


class TestGetQuoteSessions:
    """Tests for GET /quote-approval/sessions/quote/{quote_id}."""
    
    def test_get_quote_sessions(self, client, sample_context, sample_approver_id):
        """Test getting sessions for a quote."""
        quote_id = sample_context["quote_id"]
        
        # Create session
        client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        
        # Get sessions
        response = client.get(f"/api/v1/quote-approval/sessions/quote/{quote_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1


class TestGetApproverPending:
    """Tests for GET /quote-approval/sessions/approver/{approver_id}/pending."""
    
    def test_get_pending_sessions(self, client, sample_context, sample_approver_id):
        """Test getting pending sessions for approver."""
        # Create session
        client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        
        # Get pending
        response = client.get(f"/api/v1/quote-approval/sessions/approver/{sample_approver_id}/pending")
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1


# ===== Quick Options Tests =====


class TestGetQuickOptions:
    """Tests for GET /quote-approval/quick-options."""
    
    def test_get_quick_options(self, client):
        """Test getting quick options."""
        response = client.get("/api/v1/quote-approval/quick-options")
        
        assert response.status_code == status.HTTP_200_OK
        options = response.json()
        
        assert len(options) >= 5
        
        # Verify quick_approve option exists
        quick_approve = next((o for o in options if o["id"] == "quick_approve"), None)
        assert quick_approve is not None
        assert quick_approve["decision"] == "approved"


# ===== Analytics Tests =====


class TestGetApproverPerformance:
    """Tests for GET /quote-approval/analytics/performance/{approver_id}."""
    
    def test_get_performance_with_data(self, client, sample_context, sample_approver_id):
        """Test getting performance with data."""
        # Create and complete session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "approved",
                "reason": "margin_acceptable",
            },
        )
        
        # Get performance
        response = client.get(f"/api/v1/quote-approval/analytics/performance/{sample_approver_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["approver_id"] == sample_approver_id
        assert data["total_approvals"] == 1
        assert data["approvals_within_target"] == 1
    
    def test_get_performance_no_data(self, client, sample_approver_id):
        """Test getting performance with no data."""
        response = client.get(f"/api/v1/quote-approval/analytics/performance/{sample_approver_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is None


class TestGetQuoteSummary:
    """Tests for GET /quote-approval/analytics/quote/{quote_id}/summary."""
    
    def test_get_quote_summary(self, client, sample_context, sample_approver_id):
        """Test getting quote summary."""
        quote_id = sample_context["quote_id"]
        
        # Create and complete session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "approved",
            },
        )
        
        # Get summary
        response = client.get(f"/api/v1/quote-approval/analytics/quote/{quote_id}/summary")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["quote_id"] == quote_id
        assert data["total_sessions"] == 1
        assert data["final_decision"] == "approved"


class TestGetLeaderboard:
    """Tests for GET /quote-approval/analytics/leaderboard."""
    
    def test_get_leaderboard(self, client, sample_context, sample_approver_id):
        """Test getting leaderboard."""
        # Create and complete session
        create_response = client.post(
            "/api/v1/quote-approval/sessions",
            json={
                "approver_id": sample_approver_id,
                "context": sample_context,
            },
        )
        session_id = create_response.json()["id"]
        
        client.post(
            f"/api/v1/quote-approval/sessions/{session_id}/decide",
            json={
                "decision": "approved",
            },
        )
        
        # Get leaderboard
        response = client.get("/api/v1/quote-approval/analytics/leaderboard")
        
        assert response.status_code == status.HTTP_200_OK
        leaderboard = response.json()
        
        assert len(leaderboard) == 1
        assert leaderboard[0]["approver_id"] == sample_approver_id
        assert leaderboard[0]["rank"] == 1


# ===== Target Configuration Tests =====


class TestTargets:
    """Tests for target configuration endpoints."""
    
    def test_get_targets(self, client):
        """Test getting current targets."""
        response = client.get("/api/v1/quote-approval/targets")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["target_seconds"] == 60
        assert data["warning_seconds"] == 45
        assert data["critical_seconds"] == 55
    
    def test_set_targets(self, client):
        """Test setting targets."""
        response = client.put(
            "/api/v1/quote-approval/targets",
            json={
                "target_seconds": 90,
                "warning_seconds": 60,
                "critical_seconds": 80,
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["target_seconds"] == 90
        assert data["warning_seconds"] == 60
        assert data["critical_seconds"] == 80
        
        # Verify it persists
        get_response = client.get("/api/v1/quote-approval/targets")
        assert get_response.json()["target_seconds"] == 90

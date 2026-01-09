"""
Tests for GM Onboarding API Endpoints

Tests the Day-1 onboarding API.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sensei.api.v1.endpoints import gm_onboarding as gm_onboarding_api
from sensei.services.gm_onboarding import (
    GMOnboardingService,
    OnboardingStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app() -> FastAPI:
    """Create a test app."""
    app = FastAPI()
    app.include_router(gm_onboarding_api.router, prefix="/api/v1/gm-onboarding")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_service() -> GMOnboardingService:
    """Create a mock onboarding service."""
    return GMOnboardingService()


# =============================================================================
# Test Start Onboarding
# =============================================================================


class TestStartOnboarding:
    """Tests for POST /start endpoint."""

    def test_start_onboarding(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test starting onboarding."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/api/v1/gm-onboarding/start",
                json={
                    "user_id": "user-123",
                    "user_name": "John Doe",
                    "role": "GM",
                },
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["status"] == "in_progress"
            assert len(data["steps"]) > 0

    def test_start_onboarding_default_role(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test starting onboarding with default role."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/api/v1/gm-onboarding/start",
                json={
                    "user_id": "user-456",
                    "user_name": "Jane Doe",
                },
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["role"] == "GM"


# =============================================================================
# Test Get Progress
# =============================================================================


class TestGetProgress:
    """Tests for GET /progress/{user_id} endpoint."""

    def test_get_progress(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting progress."""
        # Start onboarding first
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/progress/user-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-123"

    def test_get_progress_not_found(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting progress for unknown user."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/progress/unknown-user")
            
            assert response.status_code == 404


# =============================================================================
# Test Get Summary
# =============================================================================


class TestGetSummary:
    """Tests for GET /summary/{user_id} endpoint."""

    def test_get_summary_not_started(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting summary for user who hasn't started."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/summary/unknown-user")
            
            assert response.status_code == 200
            data = response.json()
            assert data["has_started"] is False

    def test_get_summary_in_progress(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting summary for in-progress onboarding."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/summary/user-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["has_started"] is True
            assert data["status"] == "in_progress"


# =============================================================================
# Test Step Management
# =============================================================================


class TestStepManagement:
    """Tests for step management endpoints."""

    def test_start_step(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test starting a step."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/api/v1/gm-onboarding/steps/user-123/welcome/start"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "in_progress"

    def test_complete_step(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test completing a step."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/api/v1/gm-onboarding/steps/user-123/welcome/complete",
                json={"data": {"acknowledged": True}},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

    def test_skip_optional_step(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test skipping an optional step."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            # team_intro is optional
            response = client.post(
                "/api/v1/gm-onboarding/steps/user-123/team_intro/skip"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "skipped"

    def test_cannot_skip_required_step(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test cannot skip required step."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            # welcome is required
            response = client.post(
                "/api/v1/gm-onboarding/steps/user-123/welcome/skip"
            )
            
            assert response.status_code == 400


# =============================================================================
# Test Dashboard Tour
# =============================================================================


class TestDashboardTour:
    """Tests for GET /tour endpoint."""

    def test_get_tour(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting dashboard tour."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/tour")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0
            assert all("element_selector" in item for item in data)


# =============================================================================
# Test Key Metrics
# =============================================================================


class TestKeyMetrics:
    """Tests for GET /metrics/{user_id} endpoint."""

    def test_get_metrics(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting key metrics."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/metrics/user-123")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0
            assert all("name" in item for item in data)


# =============================================================================
# Test First Actions
# =============================================================================


class TestFirstActions:
    """Tests for first actions endpoints."""

    def test_get_first_actions(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting first actions."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/first-actions/user-123")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0

    def test_complete_first_action(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test completing first action."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.post(
                "/api/v1/gm-onboarding/first-actions/user-123/review_today/complete"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["completed"] is True


# =============================================================================
# Test Workflow Checklist
# =============================================================================


class TestWorkflowChecklist:
    """Tests for GET /workflow-checklist endpoint."""

    def test_get_checklist(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test getting workflow checklist."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.get("/api/v1/gm-onboarding/workflow-checklist")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0


# =============================================================================
# Test Reset
# =============================================================================


class TestReset:
    """Tests for DELETE /reset/{user_id} endpoint."""

    def test_reset_onboarding(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test resetting onboarding."""
        mock_service.start_onboarding("user-123", "John", "GM")
        
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.delete("/api/v1/gm-onboarding/reset/user-123")
            
            assert response.status_code == 204

    def test_reset_nonexistent(
        self, client: TestClient, mock_service: GMOnboardingService
    ):
        """Test resetting nonexistent user."""
        with patch(
            "sensei.api.v1.endpoints.gm_onboarding.get_gm_onboarding_service",
            return_value=mock_service,
        ):
            response = client.delete("/api/v1/gm-onboarding/reset/unknown-user")
            
            assert response.status_code == 404

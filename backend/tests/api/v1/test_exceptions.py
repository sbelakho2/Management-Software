"""
Tests for Exceptions API Endpoints

Tests the exceptions-first navigation API.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sensei.api.v1.endpoints import exceptions as exceptions_api
from sensei.services.exceptions_aggregator import (
    ExceptionCategory,
    ExceptionSeverity,
    ExceptionStatus,
    ExceptionsAggregator,
    create_exception,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app() -> FastAPI:
    """Create a test app."""
    app = FastAPI()
    app.include_router(exceptions_api.router, prefix="/api/v1/exceptions")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_aggregator() -> ExceptionsAggregator:
    """Create a mock aggregator."""
    return ExceptionsAggregator()


@pytest.fixture
def sample_exceptions(mock_aggregator: ExceptionsAggregator) -> list:
    """Create sample exceptions in aggregator."""
    now = datetime.now(timezone.utc)
    
    exceptions = [
        create_exception(
            title="Critical Andon Alert",
            description="Safety issue on line 3",
            category=ExceptionCategory.ANDON,
            severity=ExceptionSeverity.CRITICAL,
            due_date=now + timedelta(hours=1),
        ),
        create_exception(
            title="Overdue Quote",
            description="Quote for Customer X is overdue",
            category=ExceptionCategory.QUOTE,
            severity=ExceptionSeverity.HIGH,
            due_date=now - timedelta(hours=2),  # Overdue
        ),
        create_exception(
            title="Quality NCR",
            description="Non-conformance on part ABC",
            category=ExceptionCategory.QUALITY,
            severity=ExceptionSeverity.MEDIUM,
            due_date=now + timedelta(days=1),
        ),
        create_exception(
            title="Training Gap",
            description="Operator needs certification",
            category=ExceptionCategory.TRAINING,
            severity=ExceptionSeverity.LOW,
            due_date=now + timedelta(days=7),
        ),
    ]
    
    for e in exceptions:
        mock_aggregator.add_exception(e)
    
    return exceptions


# =============================================================================
# Test Get Exceptions
# =============================================================================


class TestGetExceptions:
    """Tests for GET /exceptions endpoint."""

    def test_get_all_exceptions(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting all exceptions."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions")
            
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["items"]) == 4
            assert data["total"] == 4

    def test_filter_by_category(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test filtering by category."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions?category=andon")
            
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["items"]) == 1
            assert data["items"][0]["category"] == "andon"

    def test_filter_by_severity(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test filtering by severity."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions?severity=critical")
            
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["items"]) == 1
            assert data["items"][0]["severity"] == "critical"

    def test_filter_overdue_only(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test filtering for overdue only."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions?overdue_only=true")
            
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["items"]) == 1
            assert data["items"][0]["is_overdue"] is True


# =============================================================================
# Test Critical Exceptions
# =============================================================================


class TestCriticalExceptions:
    """Tests for GET /exceptions/critical endpoint."""

    def test_get_critical_exceptions(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting critical exceptions."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/critical")
            
            assert response.status_code == 200
            data = response.json()
            # Should include critical and high
            assert len(data["items"]) == 2


# =============================================================================
# Test Summary
# =============================================================================


class TestSummary:
    """Tests for GET /exceptions/summary endpoint."""

    def test_get_summary(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting exceptions summary."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_open"] == 4
            assert data["critical_count"] == 1
            assert data["high_count"] == 1
            assert data["overdue_count"] == 1


# =============================================================================
# Test Navigation Badges
# =============================================================================


class TestNavigationBadges:
    """Tests for GET /exceptions/badges endpoint."""

    def test_get_badges(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting navigation badges."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/badges")
            
            assert response.status_code == 200
            data = response.json()
            assert "badges" in data
            assert data["total_exceptions"] == 4


# =============================================================================
# Test Trends
# =============================================================================


class TestTrends:
    """Tests for GET /exceptions/trends endpoint."""

    def test_get_trends(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting exception trends."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/trends?days=7")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["trends"]) == 7
            assert data["period_days"] == 7


# =============================================================================
# Test Get By Category
# =============================================================================


class TestGetByCategory:
    """Tests for GET /exceptions/by-category/{category} endpoint."""

    def test_get_by_category(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting exceptions by category."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/by-category/quality")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["category"] == "quality"


# =============================================================================
# Test Create Exception
# =============================================================================


class TestCreateException:
    """Tests for POST /exceptions endpoint."""

    def test_create_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator
    ):
        """Test creating a new exception."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(
                "/api/v1/exceptions",
                json={
                    "title": "New Exception",
                    "description": "Test exception",
                    "category": "production",
                    "severity": "medium",
                },
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "New Exception"
            assert data["category"] == "production"


# =============================================================================
# Test Status Changes
# =============================================================================


class TestStatusChanges:
    """Tests for exception status change endpoints."""

    def test_acknowledge_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test acknowledging an exception."""
        exception_id = sample_exceptions[0].id
        
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(f"/api/v1/exceptions/{exception_id}/acknowledge")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "acknowledged"

    def test_escalate_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test escalating an exception."""
        exception_id = sample_exceptions[0].id
        
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(
                f"/api/v1/exceptions/{exception_id}/escalate",
                json={"escalate_to": "manager@example.com"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "escalated"
            assert data["escalated_to"] == "manager@example.com"

    def test_resolve_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test resolving an exception."""
        exception_id = sample_exceptions[0].id
        
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(
                f"/api/v1/exceptions/{exception_id}/resolve",
                json={"resolution_notes": "Fixed the issue"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "resolved"

    def test_block_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test blocking an exception."""
        exception_id = sample_exceptions[0].id
        
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(
                f"/api/v1/exceptions/{exception_id}/block",
                json={"blocked_reason": "Waiting for parts"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "blocked"
            assert data["blocked_reason"] == "Waiting for parts"

    def test_start_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test starting work on an exception."""
        exception_id = sample_exceptions[0].id
        
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(f"/api/v1/exceptions/{exception_id}/in-progress")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "in_progress"


# =============================================================================
# Test Error Cases
# =============================================================================


class TestErrorCases:
    """Tests for error handling."""

    def test_get_nonexistent_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator
    ):
        """Test getting a non-existent exception."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/nonexistent-id")
            
            assert response.status_code == 404

    def test_acknowledge_nonexistent_exception(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator
    ):
        """Test acknowledging a non-existent exception."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post("/api/v1/exceptions/nonexistent-id/acknowledge")
            
            assert response.status_code == 404

    def test_invalid_category_filter(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator
    ):
        """Test invalid category filter."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions?category=invalid")
            
            assert response.status_code == 422  # Validation error

    def test_create_exception_missing_title(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator
    ):
        """Test creating exception without required fields."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.post(
                "/api/v1/exceptions",
                json={
                    "description": "Missing title",
                    "category": "production",
                    "severity": "medium",
                },
            )
            
            assert response.status_code == 422


# =============================================================================
# Test Overdue Exceptions
# =============================================================================


class TestOverdueExceptions:
    """Tests for GET /exceptions/overdue endpoint."""

    def test_get_overdue_exceptions(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting overdue exceptions."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/overdue")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["is_overdue"] is True


# =============================================================================
# Test Escalated Exceptions
# =============================================================================


class TestEscalatedExceptions:
    """Tests for GET /exceptions/escalated endpoint."""

    def test_get_escalated_exceptions_initially_empty(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting escalated exceptions when none exist."""
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/escalated")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 0

    def test_get_escalated_after_escalation(
        self, client: TestClient, mock_aggregator: ExceptionsAggregator, sample_exceptions: list
    ):
        """Test getting escalated exceptions after escalating one."""
        exception_id = sample_exceptions[0].id
        mock_aggregator.escalate_exception(exception_id, "manager@example.com")
        
        with patch(
            "sensei.api.v1.endpoints.exceptions.get_exceptions_aggregator",
            return_value=mock_aggregator,
        ):
            response = client.get("/api/v1/exceptions/escalated")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["status"] == "escalated"

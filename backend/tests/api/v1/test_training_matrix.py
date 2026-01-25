"""
Tests for the Training Matrix API Endpoints.

Tests cover all endpoints in the training matrix API:
- Matrix generation
- Gap analysis
- Expiration alerts
- User skill summary
- Station readiness
- Reference data
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sensei.api import deps
from sensei.core.security import TokenData
from sensei.main import app


@pytest.fixture
def client():
    """Create a test client."""
    async def _override_get_token_data() -> TokenData:
        now = datetime.now(timezone.utc)
        return TokenData(
            sub="training-matrix-test-user",
            type="access",
            exp=now + timedelta(hours=1),
            iat=now,
            jti="training-matrix-test-jti",
            roles=["admin"],
            permissions=[],
        )

    app.dependency_overrides[deps.get_token_data] = _override_get_token_data
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps.get_token_data, None)


@pytest.fixture
def reference_date() -> date:
    """Standard reference date for tests."""
    return date.today()


# ==============================================================================
# Matrix Generation Tests
# ==============================================================================

class TestMatrixGeneration:
    """Test matrix generation endpoints."""
    
    def test_generate_mock_matrix(self, client: TestClient):
        """Generate mock matrix for testing."""
        response = client.post(
            "/api/v1/training-matrix/generate/mock",
            params={"num_users": 5, "num_skills": 3},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 5
        assert data["total_skills"] == 3
        assert len(data["rows"]) == 5
        assert len(data["skill_columns"]) == 3
        assert "generated_at" in data
    
    def test_generate_mock_matrix_defaults(self, client: TestClient):
        """Generate mock matrix with defaults."""
        response = client.post("/api/v1/training-matrix/generate/mock")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 10
        assert data["total_skills"] == 5
    
    def test_generate_mock_matrix_limits(self, client: TestClient):
        """Generate mock matrix respects limits."""
        response = client.post(
            "/api/v1/training-matrix/generate/mock",
            params={"num_users": 100, "num_skills": 20},
        )
        
        assert response.status_code == 200
    
    def test_matrix_row_structure(self, client: TestClient):
        """Matrix row has correct structure."""
        response = client.post(
            "/api/v1/training-matrix/generate/mock",
            params={"num_users": 1, "num_skills": 2},
        )
        
        assert response.status_code == 200
        data = response.json()
        row = data["rows"][0]
        
        assert "user_id" in row
        assert "user_name" in row
        assert "user_email" in row
        assert "skills" in row
        assert "total_gaps" in row
        assert "critical_gaps" in row
        assert "expiring_soon" in row
    
    def test_skill_column_structure(self, client: TestClient):
        """Skill column has correct structure."""
        response = client.post(
            "/api/v1/training-matrix/generate/mock",
            params={"num_users": 1, "num_skills": 1},
        )
        
        assert response.status_code == 200
        data = response.json()
        col = data["skill_columns"][0]
        
        assert "skill_id" in col
        assert "skill_code" in col
        assert "skill_name" in col
        assert "is_safety_critical" in col
        assert "is_quality_critical" in col


# ==============================================================================
# Gap Analysis Tests
# ==============================================================================

class TestGapAnalysis:
    """Test gap analysis endpoints."""
    
    def test_get_gap_summary(self, client: TestClient):
        """Get gap severity summary."""
        response = client.get("/api/v1/training-matrix/gaps/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "severity_levels" in data
        assert "critical" in data["severity_levels"]
        assert "high" in data["severity_levels"]
        assert "medium" in data["severity_levels"]
        assert "low" in data["severity_levels"]
    
    def test_analyze_gaps_empty(self, client: TestClient):
        """Analyze gaps with empty data."""
        response = client.post("/api/v1/training-matrix/gaps/analyze")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_gaps"] == 0
        assert data["gaps"] == []
        assert "analyzed_at" in data


# ==============================================================================
# Expiration Alert Tests
# ==============================================================================

class TestExpirationAlerts:
    """Test expiration alert endpoints."""
    
    def test_check_expirations_empty(self, client: TestClient):
        """Check expirations with empty data."""
        response = client.post("/api/v1/training-matrix/expirations/check")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_alerts"] == 0
        assert data["alerts"] == []
        assert "checked_at" in data
    
    def test_check_expirations_custom_days(self, client: TestClient):
        """Check expirations with custom days ahead."""
        response = client.post(
            "/api/v1/training-matrix/expirations/check",
            params={"days_ahead": 30},
        )
        
        assert response.status_code == 200
    
    def test_get_expiration_thresholds(self, client: TestClient):
        """Get expiration thresholds."""
        response = client.get("/api/v1/training-matrix/expirations/thresholds")
        
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data
        assert "critical" in data["thresholds"]
        assert "urgent" in data["thresholds"]
        assert "warning" in data["thresholds"]
        assert "upcoming" in data["thresholds"]
    
    def test_update_expiration_threshold(self, client: TestClient):
        """Update expiration threshold."""
        response = client.put(
            "/api/v1/training-matrix/expirations/thresholds",
            json={"urgency": "critical", "days": 14},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["thresholds"]["critical"] == 14
    
    def test_update_expiration_threshold_invalid_urgency(self, client: TestClient):
        """Update with invalid urgency returns 400 error."""
        response = client.put(
            "/api/v1/training-matrix/expirations/thresholds",
            json={"urgency": "not_a_valid_level", "days": 14},
        )
        
        assert response.status_code == 400
        assert "Invalid urgency" in response.json()["message"]


# ==============================================================================
# User Summary Tests
# ==============================================================================

class TestUserSummary:
    """Test user skill summary endpoints."""
    
    def test_get_user_summary_empty(self, client: TestClient):
        """Get user summary with empty data."""
        user_id = str(uuid4())
        response = client.post(
            f"/api/v1/training-matrix/users/{user_id}/summary",
            json={},  # Empty request body
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["total_skills"] == 0


# ==============================================================================
# Station Readiness Tests
# ==============================================================================

class TestStationReadiness:
    """Test station readiness endpoints."""
    
    def test_get_station_readiness_empty(self, client: TestClient):
        """Get station readiness with empty data."""
        response = client.post(
            "/api/v1/training-matrix/stations/101/readiness",
            json={"station_name": "Test Station"},  # Provide JSON body
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["station_id"] == 101
        assert data["station_name"] == "Test Station"
        assert data["total_assigned_users"] == 0


# ==============================================================================
# Reference Data Tests
# ==============================================================================

class TestReferenceData:
    """Test reference data endpoints."""
    
    def test_get_gap_severities(self, client: TestClient):
        """Get all gap severity levels."""
        response = client.get("/api/v1/training-matrix/severities")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        
        values = [item["value"] for item in data]
        assert "critical" in values
        assert "high" in values
        assert "medium" in values
        assert "low" in values
    
    def test_get_urgency_levels(self, client: TestClient):
        """Get all urgency levels."""
        response = client.get("/api/v1/training-matrix/urgencies")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        
        values = [item["value"] for item in data]
        assert "expired" in values
        assert "critical" in values
        assert "urgent" in values
        assert "warning" in values
        assert "upcoming" in values


# ==============================================================================
# Response Structure Tests
# ==============================================================================

class TestResponseStructures:
    """Test response structure validation."""
    
    def test_matrix_response_structure(self, client: TestClient):
        """Matrix response has all required fields."""
        response = client.post(
            "/api/v1/training-matrix/generate/mock",
            params={"num_users": 2, "num_skills": 2},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "rows", "skill_columns", "total_users", "total_skills",
            "total_gaps", "critical_gaps", "expiring_certifications", "generated_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_gap_response_structure(self, client: TestClient):
        """Gap analysis response has all required fields."""
        response = client.post("/api/v1/training-matrix/gaps/analyze")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "gaps", "total_gaps", "by_severity", "by_skill", "by_station", "analyzed_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_expiration_response_structure(self, client: TestClient):
        """Expiration alert response has all required fields."""
        response = client.post("/api/v1/training-matrix/expirations/check")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "alerts", "total_alerts", "by_urgency", "suggested_tasks", "checked_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

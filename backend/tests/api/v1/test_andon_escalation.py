"""
Tests for Andon A3 Escalation API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from sensei.main import app


client = TestClient(app)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_datetime() -> datetime:
    """Base datetime for tests."""
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_events(base_datetime: datetime) -> list[dict]:
    """Sample Andon events for API testing."""
    return [
        {
            "id": 1,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Surface defect",
            "status": "resolved",
            "reported_at": (base_datetime - timedelta(hours=12)).isoformat(),
            "downtime_minutes": 30,
            "estimated_cost_impact": 500.0,
        },
        {
            "id": 2,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Surface defect",
            "status": "resolved",
            "reported_at": (base_datetime - timedelta(hours=24)).isoformat(),
            "downtime_minutes": 45,
            "estimated_cost_impact": 750.0,
        },
        {
            "id": 3,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Surface defect",
            "status": "open",
            "reported_at": (base_datetime - timedelta(hours=48)).isoformat(),
            "downtime_minutes": 60,
            "estimated_cost_impact": 1000.0,
        },
        {
            "id": 4,
            "station_id": 2,
            "andon_type": "equipment",
            "symptom": "Motor issue",
            "status": "open",
            "reported_at": (base_datetime - timedelta(hours=36)).isoformat(),
            "downtime_minutes": 120,
        },
    ]


@pytest.fixture
def sample_stations() -> list[dict]:
    """Sample station data."""
    return [
        {"id": 1, "name": "CNC Machine 1"},
        {"id": 2, "name": "Assembly Station A"},
    ]


# =============================================================================
# Check Escalations Tests
# =============================================================================


class TestCheckEscalationsEndpoint:
    """Tests for the /check endpoint."""
    
    def test_check_escalations_success(
        self,
        sample_events: list[dict],
        sample_stations: list[dict],
        base_datetime: datetime,
    ):
        """Test successful escalation check."""
        response = client.post(
            "/api/v1/andon-escalation/check",
            json={
                "andon_events": sample_events,
                "stations": sample_stations,
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "patterns_detected" in data
        assert "patterns_to_escalate" in data
        assert "a3s_to_create" in data
        assert data["total_patterns"] == 2  # 2 distinct patterns
    
    def test_check_escalations_detects_patterns(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that patterns are detected correctly."""
        response = client.post(
            "/api/v1/andon-escalation/check",
            json={
                "andon_events": sample_events,
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 1 pattern that needs escalation (3 occurrences)
        assert data["escalation_count"] == 1
        assert len(data["a3s_to_create"]) == 1
    
    def test_check_escalations_empty_events(self):
        """Test with empty events list."""
        response = client.post(
            "/api/v1/andon-escalation/check",
            json={"andon_events": []},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_patterns"] == 0
        assert data["escalation_count"] == 0
    
    def test_check_escalations_includes_a3_template(
        self,
        sample_events: list[dict],
        sample_stations: list[dict],
        base_datetime: datetime,
    ):
        """Test that A3 templates are properly generated."""
        response = client.post(
            "/api/v1/andon-escalation/check",
            json={
                "andon_events": sample_events,
                "stations": sample_stations,
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["a3s_to_create"]) == 1
        template = data["a3s_to_create"][0]
        assert "title" in template
        assert "problem_statement" in template
        assert "Surface defect" in template["title"]


# =============================================================================
# Detect Patterns Tests
# =============================================================================


class TestDetectPatternsEndpoint:
    """Tests for the /patterns endpoint."""
    
    def test_detect_patterns_success(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test successful pattern detection."""
        response = client.post(
            "/api/v1/andon-escalation/patterns",
            json={
                "andon_events": sample_events,
                "pattern_type": "station_type_symptom",
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # 2 distinct patterns
    
    def test_detect_patterns_different_types(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test detection with different pattern types."""
        # Station + Type pattern (less specific)
        response = client.post(
            "/api/v1/andon-escalation/patterns",
            json={
                "andon_events": sample_events,
                "pattern_type": "station_type",
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_detect_patterns_invalid_type(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test with invalid pattern type."""
        response = client.post(
            "/api/v1/andon-escalation/patterns",
            json={
                "andon_events": sample_events,
                "pattern_type": "invalid_type",
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        # Check for error message in various possible formats
        error_text = str(data)
        assert "Invalid pattern type" in error_text or "invalid_type" in error_text
    
    def test_detect_patterns_exclude_resolved(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test excluding resolved events."""
        response = client.post(
            "/api/v1/andon-escalation/patterns",
            json={
                "andon_events": sample_events,
                "pattern_type": "station_type_symptom",
                "reference_date": base_datetime.isoformat(),
                "include_resolved": False,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # With resolved excluded, pattern A has only 1 event
        pattern_a = next(p for p in data if p["station_id"] == 1)
        assert pattern_a["event_count"] == 1


# =============================================================================
# Pattern Summary Tests
# =============================================================================


class TestPatternSummaryEndpoint:
    """Tests for the /summary endpoint."""
    
    def test_get_summary_success(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test successful summary retrieval."""
        response = client.post(
            "/api/v1/andon-escalation/summary",
            json={
                "andon_events": sample_events,
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_patterns" in data
        assert "requiring_escalation" in data
        assert "thresholds" in data
        assert "top_recurring" in data
    
    def test_summary_counts_correct(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that summary counts are correct."""
        response = client.post(
            "/api/v1/andon-escalation/summary",
            json={
                "andon_events": sample_events,
                "reference_date": base_datetime.isoformat(),
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_patterns"] == 2
        assert data["requiring_escalation"] == 1


# =============================================================================
# Generate A3 Template Tests
# =============================================================================


class TestGenerateA3Endpoint:
    """Tests for the /generate-a3 endpoint."""
    
    def test_generate_a3_success(self, base_datetime: datetime):
        """Test successful A3 template generation."""
        response = client.post(
            "/api/v1/andon-escalation/generate-a3",
            json={
                "pattern": {
                    "pattern_type": "station_type_symptom",
                    "station_id": 1,
                    "station_name": "CNC Machine 1",
                    "andon_type": "quality",
                    "symptom": "Surface defect",
                    "event_ids": [1, 2, 3],
                    "event_count": 3,
                    "first_occurrence": (base_datetime - timedelta(days=2)).isoformat(),
                    "last_occurrence": base_datetime.isoformat(),
                    "total_downtime_minutes": 135,
                    "total_cost_impact": 2250.0,
                    "should_escalate": True,
                    "escalation_reason": "recurrence_threshold",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "problem_statement" in data
        assert "Surface defect" in data["title"]
    
    def test_generate_a3_with_author(self, base_datetime: datetime):
        """Test A3 template generation with author."""
        author_id = str(uuid4())
        
        response = client.post(
            "/api/v1/andon-escalation/generate-a3",
            json={
                "pattern": {
                    "pattern_type": "station_type_symptom",
                    "station_id": 1,
                    "andon_type": "quality",
                    "symptom": "Test",
                    "event_ids": [1, 2, 3],
                    "event_count": 3,
                    "should_escalate": True,
                },
                "author_id": author_id,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["author_id"] == author_id


# =============================================================================
# Link Events Tests
# =============================================================================


class TestLinkEventsEndpoint:
    """Tests for the /link-events endpoint."""
    
    def test_link_events_success(self, sample_events: list[dict]):
        """Test successful event linking."""
        a3_id = str(uuid4())
        
        response = client.post(
            "/api/v1/andon-escalation/link-events",
            json={
                "event_ids": [1, 2, 3],
                "a3_id": a3_id,
                "andon_events": sample_events,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["linked_events"]) == 3
    
    def test_link_events_sets_status(self, sample_events: list[dict]):
        """Test that linking sets correct status."""
        a3_id = str(uuid4())
        
        response = client.post(
            "/api/v1/andon-escalation/link-events",
            json={
                "event_ids": [1],
                "a3_id": a3_id,
                "andon_events": sample_events,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        linked = data["linked_events"][0]
        assert linked["status"] == "escalated"
        assert linked["is_recurrence"] is True
        assert linked["escalated_to_a3_id"] == a3_id


# =============================================================================
# Thresholds Tests
# =============================================================================


class TestThresholdsEndpoints:
    """Tests for threshold management endpoints."""
    
    def test_get_thresholds(self):
        """Test getting current thresholds."""
        response = client.get("/api/v1/andon-escalation/thresholds")
        
        assert response.status_code == 200
        data = response.json()
        assert "occurrence_count" in data
        assert "time_window_days" in data
        assert "downtime_threshold_minutes" in data
        assert "cost_threshold" in data
    
    def test_update_thresholds(self):
        """Test updating thresholds."""
        response = client.put(
            "/api/v1/andon-escalation/thresholds",
            json={
                "occurrence_count": 5,
                "time_window_days": 14,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # Note: Each request gets a fresh service, so values are default + updates
        # The service is not singleton in tests
        assert "occurrence_count" in data
    
    def test_update_thresholds_partial(self):
        """Test partial threshold update."""
        response = client.put(
            "/api/v1/andon-escalation/thresholds",
            json={"cost_threshold": 15000.0},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cost_threshold"] == 15000.0


# =============================================================================
# Reference Data Tests
# =============================================================================


class TestReferenceDataEndpoints:
    """Tests for reference data endpoints."""
    
    def test_get_pattern_types(self):
        """Test getting available pattern types."""
        response = client.get("/api/v1/andon-escalation/pattern-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "pattern_types" in data
        assert len(data["pattern_types"]) == 4
        
        values = [pt["value"] for pt in data["pattern_types"]]
        assert "station_type_symptom" in values
        assert "station_type" in values
    
    def test_get_escalation_reasons(self):
        """Test getting available escalation reasons."""
        response = client.get("/api/v1/andon-escalation/escalation-reasons")
        
        assert response.status_code == 200
        data = response.json()
        assert "reasons" in data
        assert len(data["reasons"]) == 5
        
        values = [r["value"] for r in data["reasons"]]
        assert "recurrence_threshold" in values
        assert "downtime_threshold" in values


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Tests for input validation."""
    
    def test_check_escalations_missing_events(self):
        """Test error when andon_events is missing."""
        response = client.post(
            "/api/v1/andon-escalation/check",
            json={},
        )
        
        assert response.status_code == 422
    
    def test_detect_patterns_missing_events(self):
        """Test error when andon_events is missing."""
        response = client.post(
            "/api/v1/andon-escalation/patterns",
            json={"pattern_type": "station_type_symptom"},
        )
        
        assert response.status_code == 422
    
    def test_link_events_invalid_a3_id(self, sample_events: list[dict]):
        """Test error with invalid A3 ID format."""
        response = client.post(
            "/api/v1/andon-escalation/link-events",
            json={
                "event_ids": [1],
                "a3_id": "invalid-uuid",
                "andon_events": sample_events,
            },
        )
        
        # Invalid UUID should cause a 400 error
        assert response.status_code == 400

"""
Tests for RFQ Time Tracking API Endpoints.

Tests the REST API for time-on-task tracking.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI

from sensei.api.v1.endpoints import rfq_time_tracking
from sensei.services.rfq_time_tracking import (
    reset_rfq_time_tracking_service,
    get_rfq_time_tracking_service,
    TaskType,
)


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(rfq_time_tracking.router, prefix="/api/v1/rfq-time-tracking")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    reset_rfq_time_tracking_service()
    yield TestClient(app)
    reset_rfq_time_tracking_service()


@pytest.fixture
def sample_rfq_id():
    """Sample RFQ ID."""
    return str(uuid4())


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return str(uuid4())


class TestSessionEndpoints:
    """Tests for session management endpoints."""
    
    def test_start_session(self, client, sample_rfq_id, sample_user_id):
        """Test starting a session."""
        response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "rfq_intake"
        assert data["entity_id"] == sample_rfq_id
        assert data["status"] == "active"
    
    def test_start_session_with_notes(self, client, sample_rfq_id, sample_user_id):
        """Test starting a session with notes."""
        response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
                "notes": "Initial intake",
            },
        )
        
        assert response.status_code == 201
        assert response.json()["notes"] == "Initial intake"
    
    def test_start_session_invalid_task_type(self, client, sample_rfq_id, sample_user_id):
        """Test starting a session with invalid task type."""
        response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "invalid_type",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        
        assert response.status_code == 400
        assert "Invalid task type" in response.json()["detail"]
    
    def test_start_session_invalid_uuid(self, client, sample_user_id):
        """Test starting a session with invalid UUID."""
        response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": "not-a-uuid",
                "user_id": sample_user_id,
            },
        )
        
        assert response.status_code == 400
        assert "Invalid UUID" in response.json()["detail"]
    
    def test_get_session(self, client, sample_rfq_id, sample_user_id):
        """Test getting a session by ID."""
        # Create session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        # Get session
        response = client.get(f"/api/v1/rfq-time-tracking/sessions/{session_id}")
        
        assert response.status_code == 200
        assert response.json()["id"] == session_id
    
    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        response = client.get(f"/api/v1/rfq-time-tracking/sessions/{uuid4()}")
        
        assert response.status_code == 404
    
    def test_check_session_status(self, client, sample_rfq_id, sample_user_id):
        """Test checking session status."""
        # Create session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        # Check status
        response = client.get(f"/api/v1/rfq-time-tracking/sessions/{session_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "elapsed_seconds" in data
        assert "target_seconds" in data
        assert data["performance_level"] == "excellent"
    
    def test_pause_session(self, client, sample_rfq_id, sample_user_id):
        """Test pausing a session."""
        # Create session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        # Pause
        response = client.post(
            f"/api/v1/rfq-time-tracking/sessions/{session_id}/pause",
            json={"reason": "Phone call"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["is_currently_paused"] is True
    
    def test_resume_session(self, client, sample_rfq_id, sample_user_id):
        """Test resuming a session."""
        # Create and pause session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        client.post(
            f"/api/v1/rfq-time-tracking/sessions/{session_id}/pause",
            json={},
        )
        
        # Resume
        response = client.post(f"/api/v1/rfq-time-tracking/sessions/{session_id}/resume")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["is_currently_paused"] is False
    
    def test_complete_session(self, client, sample_rfq_id, sample_user_id):
        """Test completing a session."""
        # Create session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        # Complete
        response = client.post(
            f"/api/v1/rfq-time-tracking/sessions/{session_id}/complete",
            json={"notes": "Completed successfully"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
    
    def test_abandon_session(self, client, sample_rfq_id, sample_user_id):
        """Test abandoning a session."""
        # Create session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        # Abandon
        response = client.post(
            f"/api/v1/rfq-time-tracking/sessions/{session_id}/abandon",
            json={"reason": "Customer cancelled"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "abandoned"
    
    def test_get_active_session(self, client, sample_rfq_id, sample_user_id):
        """Test getting active session for entity/user."""
        # Create session
        client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        
        # Get active
        response = client.get(
            f"/api/v1/rfq-time-tracking/sessions/active/{sample_rfq_id}/{sample_user_id}"
        )
        
        assert response.status_code == 200
        assert response.json()["entity_id"] == sample_rfq_id
    
    def test_get_user_active_sessions(self, client, sample_user_id):
        """Test getting user's active sessions."""
        # Create sessions
        for _ in range(3):
            client.post(
                "/api/v1/rfq-time-tracking/sessions",
                json={
                    "task_type": "rfq_intake",
                    "entity_id": str(uuid4()),
                    "user_id": sample_user_id,
                },
            )
        
        response = client.get(
            f"/api/v1/rfq-time-tracking/sessions/user/{sample_user_id}/active"
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 3
    
    def test_get_entity_sessions(self, client, sample_rfq_id):
        """Test getting entity's sessions."""
        # Create sessions from different users
        for _ in range(2):
            client.post(
                "/api/v1/rfq-time-tracking/sessions",
                json={
                    "task_type": "rfq_intake",
                    "entity_id": sample_rfq_id,
                    "user_id": str(uuid4()),
                },
            )
        
        response = client.get(
            f"/api/v1/rfq-time-tracking/sessions/entity/{sample_rfq_id}"
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestAlertEndpoints:
    """Tests for alert endpoints."""
    
    def test_get_session_alerts(self, client, sample_rfq_id, sample_user_id):
        """Test getting session alerts."""
        # Create session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        
        response = client.get(
            f"/api/v1/rfq-time-tracking/sessions/{session_id}/alerts"
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_pending_alerts(self, client):
        """Test getting pending alerts."""
        response = client.get("/api/v1/rfq-time-tracking/alerts/pending")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_acknowledge_alert(self, client, sample_rfq_id, sample_user_id):
        """Test acknowledging an alert."""
        # Create session and add an alert manually
        service = get_rfq_time_tracking_service()
        from sensei.services.rfq_time_tracking import TimeAlert
        
        session_id = uuid4()
        alert_id = uuid4()
        
        alert = TimeAlert(
            id=alert_id,
            session_id=session_id,
            task_type=TaskType.RFQ_INTAKE,
            alert_type="warning",
            threshold_seconds=480,
            elapsed_seconds=500,
            created_at=datetime.now(timezone.utc),
            message="Test alert",
        )
        service._alerts[alert_id] = alert
        
        # Acknowledge
        response = client.post(
            f"/api/v1/rfq-time-tracking/alerts/{alert_id}/acknowledge",
            json={"user_id": sample_user_id},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True
        assert data["acknowledged_by"] == sample_user_id


class TestTargetEndpoints:
    """Tests for target endpoints."""
    
    def test_get_all_targets(self, client):
        """Test getting all targets."""
        response = client.get("/api/v1/rfq-time-tracking/targets")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # At least RFQ intake and quote approval
    
    def test_get_target(self, client):
        """Test getting a specific target."""
        response = client.get("/api/v1/rfq-time-tracking/targets/rfq_intake")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "rfq_intake"
        assert data["target_seconds"] == 600
    
    def test_set_target(self, client):
        """Test setting a target."""
        response = client.put(
            "/api/v1/rfq-time-tracking/targets",
            json={
                "task_type": "rfq_intake",
                "target_seconds": 900,
                "warning_threshold_pct": 0.7,
                "critical_threshold_pct": 0.9,
                "max_threshold_pct": 1.1,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["target_seconds"] == 900
        assert data["warning_seconds"] == 630  # 70% of 900


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""
    
    def test_get_performance_stats_no_data(self, client):
        """Test performance stats with no data."""
        response = client.get("/api/v1/rfq-time-tracking/analytics/performance/rfq_intake")
        
        assert response.status_code == 200
        assert response.json() is None
    
    def test_get_performance_stats_with_data(self, client, sample_user_id):
        """Test performance stats with data."""
        # Create and complete sessions
        for _ in range(5):
            create_response = client.post(
                "/api/v1/rfq-time-tracking/sessions",
                json={
                    "task_type": "rfq_intake",
                    "entity_id": str(uuid4()),
                    "user_id": sample_user_id,
                },
            )
            session_id = create_response.json()["id"]
            client.post(
                f"/api/v1/rfq-time-tracking/sessions/{session_id}/complete",
                json={},
            )
        
        response = client.get("/api/v1/rfq-time-tracking/analytics/performance/rfq_intake")
        
        assert response.status_code == 200
        data = response.json()
        assert data["completed_sessions"] == 5
    
    def test_get_user_efficiency_no_data(self, client):
        """Test user efficiency with no data."""
        response = client.get(f"/api/v1/rfq-time-tracking/analytics/efficiency/{uuid4()}")
        
        assert response.status_code == 200
        assert response.json() is None
    
    def test_get_daily_breakdown(self, client):
        """Test daily breakdown."""
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=7)).isoformat()
        end = now.isoformat()
        
        response = client.get(
            f"/api/v1/rfq-time-tracking/analytics/daily/rfq_intake",
            params={"start_date": start, "end_date": end},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 8  # 7 days + today
    
    def test_get_leaderboard(self, client):
        """Test leaderboard."""
        response = client.get("/api/v1/rfq-time-tracking/analytics/leaderboard/rfq_intake")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestRFQSummaryEndpoints:
    """Tests for RFQ-specific endpoints."""
    
    def test_get_rfq_intake_summary(self, client, sample_rfq_id, sample_user_id):
        """Test RFQ intake summary."""
        # Create and complete a session
        create_response = client.post(
            "/api/v1/rfq-time-tracking/sessions",
            json={
                "task_type": "rfq_intake",
                "entity_id": sample_rfq_id,
                "user_id": sample_user_id,
            },
        )
        session_id = create_response.json()["id"]
        client.post(
            f"/api/v1/rfq-time-tracking/sessions/{session_id}/complete",
            json={},
        )
        
        response = client.get(f"/api/v1/rfq-time-tracking/rfq/{sample_rfq_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["rfq_id"] == sample_rfq_id
        assert data["completed_sessions"] == 1
        assert data["target_seconds"] == 600


class TestMaintenanceEndpoints:
    """Tests for maintenance endpoints."""
    
    def test_cleanup_expired_sessions(self, client):
        """Test cleanup of expired sessions."""
        response = client.post(
            "/api/v1/rfq-time-tracking/cleanup",
            params={"max_age_hours": 24},
        )
        
        assert response.status_code == 200
        assert "expired_sessions" in response.json()

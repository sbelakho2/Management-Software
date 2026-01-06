"""
Tests for the Notification Triggers API endpoints.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sensei.api.v1.endpoints.notification_triggers import router, _service


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def now() -> datetime:
    """Reference datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def user_id() -> str:
    """Test user ID."""
    return str(uuid4())


@pytest.fixture(autouse=True)
def reset_service():
    """Reset the service before each test."""
    # Clear snooze settings
    _service._snooze_settings.clear()
    # Re-enable all triggers
    for trigger in _service._triggers.values():
        trigger.is_enabled = True
    yield


# --------------------------------------------------------------------------
# List Endpoints Tests
# --------------------------------------------------------------------------

class TestListEndpoints:
    """Tests for list endpoints."""
    
    def test_list_triggers(self, client: TestClient):
        """Test listing all triggers."""
        response = client.get("/notifications/triggers")
        
        assert response.status_code == 200
        triggers = response.json()
        assert len(triggers) > 0
        
        # Check structure
        trigger = triggers[0]
        assert "trigger_type" in trigger
        assert "name" in trigger
        assert "is_enabled" in trigger
    
    def test_list_trigger_types(self, client: TestClient):
        """Test listing trigger types."""
        response = client.get("/notifications/trigger-types")
        
        assert response.status_code == 200
        types = response.json()
        assert len(types) > 0
        
        # Check some expected types
        values = [t["value"] for t in types]
        assert "task_overdue" in values
        assert "rfq_stalled" in values
        assert "quote_low_margin" in values
    
    def test_list_recipient_roles(self, client: TestClient):
        """Test listing recipient roles."""
        response = client.get("/notifications/recipient-roles")
        
        assert response.status_code == 200
        roles = response.json()
        assert len(roles) > 0
        
        values = [r["value"] for r in roles]
        assert "owner" in values
        assert "assignee" in values
        assert "manager" in values
    
    def test_list_channels(self, client: TestClient):
        """Test listing notification channels."""
        response = client.get("/notifications/channels")
        
        assert response.status_code == 200
        channels = response.json()
        
        values = [c["value"] for c in channels]
        assert "in_app" in values
        assert "email" in values
    
    def test_list_priorities(self, client: TestClient):
        """Test listing priorities."""
        response = client.get("/notifications/priorities")
        
        assert response.status_code == 200
        priorities = response.json()
        
        values = [p["value"] for p in priorities]
        assert "low" in values
        assert "normal" in values
        assert "high" in values
        assert "urgent" in values


# --------------------------------------------------------------------------
# Get Trigger Tests
# --------------------------------------------------------------------------

class TestGetTrigger:
    """Tests for getting specific triggers."""
    
    def test_get_trigger_success(self, client: TestClient):
        """Test getting a trigger by type."""
        response = client.get("/notifications/triggers/task_overdue")
        
        assert response.status_code == 200
        trigger = response.json()
        assert trigger["trigger_type"] == "task_overdue"
        assert trigger["name"] == "Task Overdue"
        assert trigger["is_enabled"] is True
    
    def test_get_trigger_invalid_type(self, client: TestClient):
        """Test getting with invalid trigger type."""
        response = client.get("/notifications/triggers/invalid_type")
        
        assert response.status_code == 400
        assert "Invalid trigger type" in response.json()["detail"]
    
    def test_get_trigger_not_found(self, client: TestClient):
        """Test getting non-existent trigger type."""
        response = client.get("/notifications/triggers/skill_gap")
        
        # skill_gap is a valid type but not registered by default
        assert response.status_code == 404


# --------------------------------------------------------------------------
# Update Trigger Tests
# --------------------------------------------------------------------------

class TestUpdateTrigger:
    """Tests for updating triggers."""
    
    def test_update_trigger_disable(self, client: TestClient):
        """Test disabling a trigger."""
        response = client.put(
            "/notifications/triggers/task_overdue",
            json={"is_enabled": False},
        )
        
        assert response.status_code == 200
        trigger = response.json()
        assert trigger["is_enabled"] is False
    
    def test_update_trigger_thresholds(self, client: TestClient):
        """Test updating trigger thresholds."""
        response = client.put(
            "/notifications/triggers/quote_low_margin",
            json={"margin_threshold": 20.0},
        )
        
        assert response.status_code == 200
        trigger = response.json()
        assert trigger["margin_threshold"] == 20.0
    
    def test_update_trigger_recipients(self, client: TestClient):
        """Test updating trigger recipients."""
        response = client.put(
            "/notifications/triggers/task_overdue",
            json={"recipients": ["owner", "manager", "gm"]},
        )
        
        assert response.status_code == 200
        trigger = response.json()
        assert "owner" in trigger["recipients"]
        assert "manager" in trigger["recipients"]
        assert "gm" in trigger["recipients"]
    
    def test_update_trigger_channels(self, client: TestClient):
        """Test updating trigger channels."""
        response = client.put(
            "/notifications/triggers/task_overdue",
            json={"channels": ["in_app", "email", "push"]},
        )
        
        assert response.status_code == 200
        trigger = response.json()
        assert "in_app" in trigger["channels"]
        assert "email" in trigger["channels"]
        assert "push" in trigger["channels"]
    
    def test_update_trigger_invalid_type(self, client: TestClient):
        """Test updating with invalid trigger type."""
        response = client.put(
            "/notifications/triggers/invalid_type",
            json={"is_enabled": False},
        )
        
        assert response.status_code == 400
    
    def test_update_trigger_invalid_recipient(self, client: TestClient):
        """Test updating with invalid recipient role."""
        response = client.put(
            "/notifications/triggers/task_overdue",
            json={"recipients": ["invalid_role"]},
        )
        
        assert response.status_code == 400
        assert "Invalid recipient role" in response.json()["detail"]
    
    def test_update_trigger_invalid_channel(self, client: TestClient):
        """Test updating with invalid channel."""
        response = client.put(
            "/notifications/triggers/task_overdue",
            json={"channels": ["invalid_channel"]},
        )
        
        assert response.status_code == 400
        assert "Invalid channel" in response.json()["detail"]


# --------------------------------------------------------------------------
# Enable/Disable Tests
# --------------------------------------------------------------------------

class TestEnableDisable:
    """Tests for enable/disable endpoints."""
    
    def test_disable_trigger(self, client: TestClient):
        """Test disabling a trigger."""
        response = client.post("/notifications/triggers/task_overdue/disable")
        
        assert response.status_code == 200
        result = response.json()
        assert result["trigger_type"] == "task_overdue"
        assert result["is_enabled"] is False
    
    def test_enable_trigger(self, client: TestClient):
        """Test enabling a trigger."""
        # First disable
        client.post("/notifications/triggers/task_overdue/disable")
        
        # Then enable
        response = client.post("/notifications/triggers/task_overdue/enable")
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_enabled"] is True
    
    def test_disable_invalid_type(self, client: TestClient):
        """Test disabling invalid trigger type."""
        response = client.post("/notifications/triggers/invalid/disable")
        
        assert response.status_code == 400


# --------------------------------------------------------------------------
# Evaluate Triggers Tests
# --------------------------------------------------------------------------

class TestEvaluateTriggers:
    """Tests for trigger evaluation."""
    
    def test_evaluate_overdue_task(self, client: TestClient, user_id: str, now: datetime):
        """Test evaluating overdue task trigger."""
        response = client.post(
            "/notifications/evaluate",
            json={
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Overdue Task",
                        "due_date": (now - timedelta(days=3)).isoformat(),
                        "status": "pending",
                        "owner_id": user_id,
                        "assignee_id": user_id,
                    }
                ],
                "users": [
                    {
                        "user_id": user_id,
                        "role": "owner",
                    }
                ],
                "reference_date": now.isoformat(),
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["entities_scanned"] == 1
        assert len(result["notifications"]) > 0
        
        # Check notification content
        notif = result["notifications"][0]
        assert notif["trigger_type"] == "task_overdue"
        assert "Overdue Task" in notif["title"]
    
    def test_evaluate_stalled_rfq(self, client: TestClient, user_id: str, now: datetime):
        """Test evaluating stalled RFQ trigger."""
        response = client.post(
            "/notifications/evaluate",
            json={
                "rfqs": [
                    {
                        "id": "rfq-1",
                        "rfq_number": "RFQ-001",
                        "status": "open",
                        "updated_at": (now - timedelta(days=14)).isoformat(),
                        "owner_id": user_id,
                    }
                ],
                "users": [
                    {
                        "user_id": user_id,
                        "role": "owner",
                    }
                ],
                "reference_date": now.isoformat(),
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        
        stalled = [n for n in result["notifications"] if n["trigger_type"] == "rfq_stalled"]
        assert len(stalled) > 0
    
    def test_evaluate_low_margin_quote(self, client: TestClient, user_id: str, now: datetime):
        """Test evaluating low margin quote trigger."""
        response = client.post(
            "/notifications/evaluate",
            json={
                "quotes": [
                    {
                        "id": "quote-1",
                        "quote_number": "Q-001",
                        "status": "draft",
                        "margin_percent": 8.0,
                        "owner_id": user_id,
                    }
                ],
                "users": [
                    {
                        "user_id": user_id,
                        "role": "owner",
                    }
                ],
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        
        low_margin = [n for n in result["notifications"] if n["trigger_type"] == "quote_low_margin"]
        assert len(low_margin) > 0
    
    def test_evaluate_expiring_certification(self, client: TestClient, user_id: str, now: datetime):
        """Test evaluating expiring certification trigger."""
        response = client.post(
            "/notifications/evaluate",
            json={
                "certifications": [
                    {
                        "id": "cert-1",
                        "user_id": user_id,
                        "skill_name": "Safety Training",
                        "expires_at": (now + timedelta(days=15)).isoformat(),
                    }
                ],
                "users": [
                    {
                        "user_id": user_id,
                        "role": "owner",
                    }
                ],
                "reference_date": now.isoformat(),
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        
        expiring = [n for n in result["notifications"] if n["trigger_type"] == "certification_expiring"]
        assert len(expiring) > 0
    
    def test_evaluate_empty_data(self, client: TestClient):
        """Test evaluating with no data."""
        response = client.post(
            "/notifications/evaluate",
            json={},
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["entities_scanned"] == 0
        assert len(result["notifications"]) == 0
    
    def test_evaluate_invalid_reference_date(self, client: TestClient):
        """Test evaluating with invalid reference date."""
        response = client.post(
            "/notifications/evaluate",
            json={
                "reference_date": "not-a-date",
            },
        )
        
        assert response.status_code == 400
        assert "Invalid reference_date" in response.json()["detail"]


# --------------------------------------------------------------------------
# Snooze Tests
# --------------------------------------------------------------------------

class TestSnooze:
    """Tests for snooze functionality."""
    
    def test_snooze_global(self, client: TestClient, user_id: str):
        """Test global snooze."""
        response = client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "snooze_hours": 24,
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["user_id"] == user_id
        assert result["snooze_until"] is not None
    
    def test_snooze_trigger_type(self, client: TestClient, user_id: str):
        """Test snooze for specific trigger type."""
        response = client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "trigger_type": "task_overdue",
                "snooze_hours": 8,
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["trigger_type"] == "task_overdue"
    
    def test_snooze_entity(self, client: TestClient, user_id: str):
        """Test snooze for specific entity."""
        response = client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "entity_key": "task::12345",
                "snooze_hours": 4,
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["entity_key"] == "task::12345"
    
    def test_snooze_invalid_user(self, client: TestClient):
        """Test snooze with invalid user ID."""
        response = client.post(
            "/notifications/snooze",
            json={
                "user_id": "not-a-uuid",
                "snooze_hours": 24,
            },
        )
        
        assert response.status_code == 400
        assert "Invalid user_id" in response.json()["detail"]
    
    def test_snooze_invalid_trigger_type(self, client: TestClient, user_id: str):
        """Test snooze with invalid trigger type."""
        response = client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "trigger_type": "invalid_type",
            },
        )
        
        assert response.status_code == 400
        assert "Invalid trigger type" in response.json()["detail"]


# --------------------------------------------------------------------------
# Acknowledge Tests
# --------------------------------------------------------------------------

class TestAcknowledge:
    """Tests for acknowledge functionality."""
    
    def test_acknowledge_entity(self, client: TestClient, user_id: str):
        """Test acknowledging an entity."""
        response = client.post(
            "/notifications/acknowledge",
            json={
                "user_id": user_id,
                "entity_key": "rfq::67890",
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] is True
        assert result["entity_key"] == "rfq::67890"
    
    def test_acknowledge_invalid_user(self, client: TestClient):
        """Test acknowledge with invalid user ID."""
        response = client.post(
            "/notifications/acknowledge",
            json={
                "user_id": "invalid",
                "entity_key": "task::123",
            },
        )
        
        assert response.status_code == 400


# --------------------------------------------------------------------------
# Clear Snooze Tests
# --------------------------------------------------------------------------

class TestClearSnooze:
    """Tests for clearing snooze settings."""
    
    def test_clear_snooze_global(self, client: TestClient, user_id: str):
        """Test clearing global snooze."""
        # First snooze
        client.post(
            "/notifications/snooze",
            json={"user_id": user_id, "snooze_hours": 24},
        )
        
        # Then clear
        response = client.post(
            "/notifications/clear-snooze",
            json={"user_id": user_id},
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["cleared"] is True
    
    def test_clear_snooze_trigger(self, client: TestClient, user_id: str):
        """Test clearing trigger-specific snooze."""
        # First snooze
        client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "trigger_type": "task_overdue",
                "snooze_hours": 8,
            },
        )
        
        # Then clear
        response = client.post(
            "/notifications/clear-snooze",
            json={
                "user_id": user_id,
                "trigger_type": "task_overdue",
            },
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["cleared"] is True
    
    def test_clear_snooze_invalid_user(self, client: TestClient):
        """Test clearing with invalid user ID."""
        response = client.post(
            "/notifications/clear-snooze",
            json={"user_id": "invalid"},
        )
        
        assert response.status_code == 400


# --------------------------------------------------------------------------
# Get Snooze Settings Tests
# --------------------------------------------------------------------------

class TestGetSnoozeSettings:
    """Tests for getting snooze settings."""
    
    def test_get_settings_empty(self, client: TestClient, user_id: str):
        """Test getting settings for user with no snoozes."""
        response = client.get(f"/notifications/snooze/{user_id}")
        
        assert response.status_code == 200
        settings = response.json()
        assert settings["user_id"] == user_id
        assert settings["global_snooze_until"] is None
        assert settings["trigger_snoozes"] == {}
        assert settings["entity_snoozes"] == {}
        assert settings["acknowledged_entities"] == []
    
    def test_get_settings_with_snoozes(self, client: TestClient, user_id: str):
        """Test getting settings after snoozing."""
        # Add snoozes
        client.post(
            "/notifications/snooze",
            json={"user_id": user_id, "snooze_hours": 24},
        )
        client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "trigger_type": "task_overdue",
                "snooze_hours": 8,
            },
        )
        client.post(
            "/notifications/acknowledge",
            json={
                "user_id": user_id,
                "entity_key": "rfq::123",
            },
        )
        
        response = client.get(f"/notifications/snooze/{user_id}")
        
        assert response.status_code == 200
        settings = response.json()
        assert settings["global_snooze_until"] is not None
        assert "task_overdue" in settings["trigger_snoozes"]
        assert "rfq::123" in settings["acknowledged_entities"]
    
    def test_get_settings_invalid_user(self, client: TestClient):
        """Test getting settings with invalid user ID."""
        response = client.get("/notifications/snooze/invalid-uuid")
        
        assert response.status_code == 400


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests combining multiple operations."""
    
    def test_snooze_blocks_notification(self, client: TestClient, user_id: str, now: datetime):
        """Test that snoozing blocks notifications."""
        task_id = str(uuid4())
        
        # First, verify notification would be generated
        response = client.post(
            "/notifications/evaluate",
            json={
                "tasks": [
                    {
                        "id": task_id,
                        "title": "Test Task",
                        "due_date": (now - timedelta(days=2)).isoformat(),
                        "status": "pending",
                        "owner_id": user_id,
                        "assignee_id": user_id,
                    }
                ],
                "users": [{"user_id": user_id, "role": "owner"}],
                "reference_date": now.isoformat(),
            },
        )
        
        initial_count = len(response.json()["notifications"])
        assert initial_count > 0
        
        # Snooze the entity
        client.post(
            "/notifications/snooze",
            json={
                "user_id": user_id,
                "entity_key": f"task::{task_id}",
                "snooze_hours": 24,
            },
        )
        
        # Re-evaluate - should not generate notification
        response = client.post(
            "/notifications/evaluate",
            json={
                "tasks": [
                    {
                        "id": task_id,
                        "title": "Test Task",
                        "due_date": (now - timedelta(days=2)).isoformat(),
                        "status": "pending",
                        "owner_id": user_id,
                        "assignee_id": user_id,
                    }
                ],
                "users": [{"user_id": user_id, "role": "owner"}],
                "reference_date": now.isoformat(),
            },
        )
        
        # Notifications for this entity should be blocked
        notifications = response.json()["notifications"]
        for notif in notifications:
            assert notif["entity_id"] != task_id
    
    def test_disable_trigger_blocks_notification(self, client: TestClient, user_id: str, now: datetime):
        """Test that disabling trigger blocks notifications."""
        # Disable the trigger
        client.post("/notifications/triggers/task_overdue/disable")
        
        # Evaluate
        response = client.post(
            "/notifications/evaluate",
            json={
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Test Task",
                        "due_date": (now - timedelta(days=5)).isoformat(),
                        "status": "pending",
                        "owner_id": user_id,
                        "assignee_id": user_id,
                    }
                ],
                "users": [{"user_id": user_id, "role": "owner"}],
                "reference_date": now.isoformat(),
            },
        )
        
        overdue = [n for n in response.json()["notifications"] if n["trigger_type"] == "task_overdue"]
        assert len(overdue) == 0

"""
Tests for LSW (Leader Standard Work) Scheduling API endpoints.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from sensei.main import app
from sensei.api.v1.endpoints.lsw import _service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service():
    """Reset service state between tests."""
    # Store original state
    original_templates = _service._templates.copy()
    original_instances = _service._instances.copy()
    original_checklists = _service._checklists.copy()
    original_reminders = _service._reminders.copy()
    
    yield
    
    # Restore original state
    _service._templates = original_templates
    _service._instances = original_instances
    _service._checklists = original_checklists
    _service._reminders = original_reminders


# --------------------------------------------------------------------------
# Template Tests
# --------------------------------------------------------------------------

class TestTemplateEndpoints:
    """Tests for template CRUD endpoints."""
    
    def test_create_template(self, client):
        """Test creating a new template."""
        response = client.post(
            "/api/v1/lsw/templates",
            json={
                "name": "Test Gemba Walk",
                "description": "Daily gemba walk",
                "category": "gemba_walk",
                "frequency": "daily",
                "estimated_duration_minutes": 30,
                "required": True,
                "preferred_time": "08:00",
                "requires_notes": True,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Gemba Walk"
        assert data["category"] == "gemba_walk"
        assert data["frequency"] == "daily"
        assert data["estimated_duration_minutes"] == 30
        assert data["preferred_time"] == "08:00"
        assert data["requires_notes"] is True
    
    def test_create_template_with_sub_items(self, client):
        """Test creating template with sub-items."""
        response = client.post(
            "/api/v1/lsw/templates",
            json={
                "name": "Safety Check",
                "description": "Daily safety checklist",
                "category": "safety_check",
                "frequency": "daily",
                "sub_items": [
                    "Check PPE availability",
                    "Inspect fire extinguishers",
                    "Review safety board",
                ],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["sub_items"]) == 3
        assert "Check PPE availability" in data["sub_items"]
    
    def test_create_template_with_days_of_week(self, client):
        """Test creating weekly template with specific days."""
        response = client.post(
            "/api/v1/lsw/templates",
            json={
                "name": "Weekly Review",
                "description": "Weekly status review",
                "category": "tier_meeting",
                "frequency": "weekly",
                "days_of_week": ["monday", "friday"],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "monday" in data["days_of_week"]
        assert "friday" in data["days_of_week"]
    
    def test_create_template_invalid_time(self, client):
        """Test creating template with invalid time format."""
        response = client.post(
            "/api/v1/lsw/templates",
            json={
                "name": "Test Template",
                "description": "Test",
                "category": "gemba_walk",
                "frequency": "daily",
                "preferred_time": "invalid",
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid time format" in data.get("message", "") or "Invalid time format" in data.get("detail", "")
    
    def test_list_templates(self, client):
        """Test listing templates."""
        response = client.get("/api/v1/lsw/templates")
        
        assert response.status_code == 200
        data = response.json()
        # Should have default templates
        assert len(data) > 0
    
    def test_list_templates_by_frequency(self, client):
        """Test filtering templates by frequency."""
        response = client.get("/api/v1/lsw/templates?frequency=daily")
        
        assert response.status_code == 200
        data = response.json()
        for template in data:
            assert template["frequency"] == "daily"
    
    def test_list_templates_by_category(self, client):
        """Test filtering templates by category."""
        response = client.get("/api/v1/lsw/templates?category=tier_meeting")
        
        assert response.status_code == 200
        data = response.json()
        for template in data:
            assert template["category"] == "tier_meeting"
    
    def test_get_default_templates(self, client):
        """Test getting default template IDs."""
        response = client.get("/api/v1/lsw/templates/defaults")
        
        assert response.status_code == 200
        data = response.json()
        assert "daily-gemba" in data
        assert "weekly-tier2" in data
        assert "monthly-tier3" in data
    
    def test_get_template(self, client):
        """Test getting a specific template."""
        response = client.get("/api/v1/lsw/templates/daily-gemba")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "daily-gemba"
        assert data["name"] == "Daily Gemba Walk"
    
    def test_get_template_not_found(self, client):
        """Test getting non-existent template."""
        response = client.get("/api/v1/lsw/templates/non-existent")
        
        assert response.status_code == 404
    
    def test_update_template(self, client):
        """Test updating a template."""
        # Create template first
        create_response = client.post(
            "/api/v1/lsw/templates",
            json={
                "id": "test-update",
                "name": "Original Name",
                "description": "Original description",
                "category": "gemba_walk",
                "frequency": "daily",
            },
        )
        assert create_response.status_code == 201
        
        # Update it
        response = client.put(
            "/api/v1/lsw/templates/test-update",
            json={
                "name": "Updated Name",
                "estimated_duration_minutes": 45,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["estimated_duration_minutes"] == 45
    
    def test_update_template_not_found(self, client):
        """Test updating non-existent template."""
        response = client.put(
            "/api/v1/lsw/templates/non-existent",
            json={"name": "New Name"},
        )
        
        assert response.status_code == 404
    
    def test_delete_template(self, client):
        """Test deleting a template."""
        # Create template first
        create_response = client.post(
            "/api/v1/lsw/templates",
            json={
                "id": "test-delete",
                "name": "To Delete",
                "description": "Will be deleted",
                "category": "gemba_walk",
                "frequency": "daily",
            },
        )
        assert create_response.status_code == 201
        
        # Delete it
        response = client.delete("/api/v1/lsw/templates/test-delete")
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get("/api/v1/lsw/templates/test-delete")
        assert get_response.status_code == 404
    
    def test_delete_default_template_fails(self, client):
        """Test that default templates cannot be deleted."""
        response = client.delete("/api/v1/lsw/templates/daily-gemba")
        
        assert response.status_code == 400
        data = response.json()
        assert "default templates" in data.get("message", "") or "default templates" in data.get("detail", "")


# --------------------------------------------------------------------------
# Checklist Generation Tests
# --------------------------------------------------------------------------

class TestChecklistGeneration:
    """Tests for checklist generation endpoints."""
    
    def test_generate_checklist(self, client):
        """Test generating a checklist."""
        today = date.today().isoformat()
        response = client.post(
            f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["owner_id"] == "owner-1"
        assert data["date"] == today
        assert data["generated_count"] > 0
        assert len(data["items"]) == data["generated_count"]
    
    def test_generate_checklist_specific_templates(self, client):
        """Test generating checklist with specific templates."""
        today = date.today().isoformat()
        response = client.post(
            f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today}"
            "&template_ids=daily-gemba&template_ids=daily-safety"
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should only have the specified templates
        template_ids = [item["template_id"] for item in data["items"]]
        assert "daily-gemba" in template_ids or "daily-safety" in template_ids
    
    def test_generate_week_checklists(self, client):
        """Test generating a week of checklists."""
        today = date.today().isoformat()
        response = client.post(
            f"/api/v1/lsw/checklists/generate-week?owner_id=owner-1&start_date={today}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7  # Full week
    
    def test_get_checklist(self, client):
        """Test getting a generated checklist."""
        today = date.today().isoformat()
        
        # Generate first
        client.post(f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today}")
        
        # Then retrieve
        response = client.get(
            f"/api/v1/lsw/checklists?owner_id=owner-1&target_date={today}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["owner_id"] == "owner-1"
        assert data["date"] == today
    
    def test_get_checklist_not_found(self, client):
        """Test getting non-existent checklist."""
        response = client.get(
            "/api/v1/lsw/checklists?owner_id=non-existent&target_date=2020-01-01"
        )
        
        assert response.status_code == 200
        assert response.json() is None


# --------------------------------------------------------------------------
# Item Action Tests
# --------------------------------------------------------------------------

class TestItemActions:
    """Tests for item action endpoints."""
    
    @pytest.fixture
    def generated_item(self, client):
        """Generate and return an item for testing."""
        today = date.today().isoformat()
        response = client.post(
            f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today}"
        )
        data = response.json()
        if data["items"]:
            return data["items"][0]
        return None
    
    def test_get_item(self, client, generated_item):
        """Test getting a specific item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.get(f"/api/v1/lsw/items/{generated_item['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == generated_item["id"]
    
    def test_get_item_not_found(self, client):
        """Test getting non-existent item."""
        response = client.get("/api/v1/lsw/items/non-existent")
        
        assert response.status_code == 404
    
    def test_start_item(self, client, generated_item):
        """Test starting an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.post(f"/api/v1/lsw/items/{generated_item['id']}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None
    
    def test_complete_item(self, client, generated_item):
        """Test completing an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        # Start first
        client.post(f"/api/v1/lsw/items/{generated_item['id']}/start")
        
        # Complete
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/complete",
            json={
                "completed_by_id": "user-1",
                "notes": "All checks passed",
                "actual_duration_minutes": 25,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["completed_by_id"] == "user-1"
        assert data["notes"] == "All checks passed"
        assert data["actual_duration_minutes"] == 25
    
    def test_complete_item_with_findings(self, client, generated_item):
        """Test completing an item with findings."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/complete",
            json={
                "completed_by_id": "user-1",
                "findings": [
                    {"type": "observation", "description": "5S needs improvement"},
                ],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["findings"]) == 1
    
    def test_skip_item(self, client, generated_item):
        """Test skipping an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/skip",
            json={"reason": "Equipment down for maintenance"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["skip_reason"] == "Equipment down for maintenance"
    
    def test_defer_item(self, client, generated_item):
        """Test deferring an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/defer",
            json={
                "defer_to": tomorrow,
                "reason": "Meeting conflict",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deferred"
        assert data["deferred_to"] == tomorrow
    
    def test_add_finding(self, client, generated_item):
        """Test adding a finding to an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/findings",
            json={
                "finding": {
                    "type": "issue",
                    "severity": "medium",
                    "description": "Safety hazard identified",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["findings"]) == 1
        assert data["findings"][0]["type"] == "issue"
    
    def test_link_task(self, client, generated_item):
        """Test linking a task to an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/tasks/task-123"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task-123" in data["generated_task_ids"]
    
    def test_link_a3(self, client, generated_item):
        """Test linking an A3 to an item."""
        if not generated_item:
            pytest.skip("No items generated")
        
        response = client.post(
            f"/api/v1/lsw/items/{generated_item['id']}/a3s/a3-456"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "a3-456" in data["generated_a3_ids"]


# --------------------------------------------------------------------------
# Sub-Item Tests
# --------------------------------------------------------------------------

class TestSubItems:
    """Tests for sub-item completion."""
    
    def test_complete_sub_item(self, client):
        """Test completing a sub-item."""
        # Create template with sub-items
        create_response = client.post(
            "/api/v1/lsw/templates",
            json={
                "id": "test-subitems",
                "name": "Sub-Item Test",
                "description": "Testing sub-items",
                "category": "safety_check",
                "frequency": "daily",
                "sub_items": ["Check 1", "Check 2", "Check 3"],
            },
        )
        assert create_response.status_code == 201
        
        # Generate checklist
        today = date.today().isoformat()
        gen_response = client.post(
            f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today}"
            "&template_ids=test-subitems"
        )
        
        if gen_response.json()["generated_count"] == 0:
            pytest.skip("Template not applicable to today")
        
        item = gen_response.json()["items"][0]
        
        # Complete sub-item
        response = client.post(
            f"/api/v1/lsw/items/{item['id']}/sub-items/Check 1"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Check 1" in data["sub_items_completed"]


# --------------------------------------------------------------------------
# Status and Pending Items Tests
# --------------------------------------------------------------------------

class TestStatusEndpoints:
    """Tests for status-related endpoints."""
    
    def test_get_pending_items(self, client):
        """Test getting pending items."""
        # Generate checklist first
        today = date.today().isoformat()
        client.post(f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today}")
        
        response = client.get("/api/v1/lsw/items/pending?owner_id=owner-1")
        
        assert response.status_code == 200
        data = response.json()
        # All generated items should be pending initially
        for item in data:
            assert item["status"] in ["pending", "due", "overdue"]
    
    def test_get_overdue_items(self, client):
        """Test getting overdue items."""
        response = client.get("/api/v1/lsw/items/overdue")
        
        assert response.status_code == 200
        # Result is a list (may be empty if no overdue items)
        assert isinstance(response.json(), list)
    
    def test_update_overdue_items(self, client):
        """Test updating overdue items."""
        response = client.post("/api/v1/lsw/items/update-overdue")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# --------------------------------------------------------------------------
# Analytics Tests
# --------------------------------------------------------------------------

class TestAnalytics:
    """Tests for analytics endpoints."""
    
    def test_get_compliance_stats(self, client):
        """Test getting compliance statistics."""
        # Generate and complete some items
        today = date.today()
        client.post(
            f"/api/v1/lsw/checklists/generate?owner_id=owner-1&target_date={today.isoformat()}"
        )
        
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = today.isoformat()
        
        response = client.get(
            f"/api/v1/lsw/stats/compliance?owner_id=owner-1"
            f"&start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_items" in data
        assert "completed" in data
        assert "completion_rate" in data
        assert "by_category" in data
    
    def test_get_findings_summary(self, client):
        """Test getting findings summary."""
        today = date.today()
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = today.isoformat()
        
        response = client.get(
            f"/api/v1/lsw/stats/findings?start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_findings_by_owner(self, client):
        """Test getting findings for specific owner."""
        today = date.today()
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = today.isoformat()
        
        response = client.get(
            f"/api/v1/lsw/stats/findings?start_date={start_date}&end_date={end_date}"
            "&owner_id=owner-1"
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# --------------------------------------------------------------------------
# Metadata Tests
# --------------------------------------------------------------------------

class TestMetadata:
    """Tests for metadata endpoints."""
    
    def test_get_frequencies(self, client):
        """Test getting available frequencies."""
        response = client.get("/api/v1/lsw/frequencies")
        
        assert response.status_code == 200
        data = response.json()
        values = [f["value"] for f in data]
        assert "daily" in values
        assert "weekly" in values
        assert "monthly" in values
    
    def test_get_categories(self, client):
        """Test getting available categories."""
        response = client.get("/api/v1/lsw/categories")
        
        assert response.status_code == 200
        data = response.json()
        values = [c["value"] for c in data]
        assert "gemba_walk" in values
        assert "tier_meeting" in values
        assert "safety_check" in values
    
    def test_get_statuses(self, client):
        """Test getting available statuses."""
        response = client.get("/api/v1/lsw/statuses")
        
        assert response.status_code == 200
        data = response.json()
        values = [s["value"] for s in data]
        assert "pending" in values
        assert "completed" in values
        assert "skipped" in values
    
    def test_get_days_of_week(self, client):
        """Test getting days of week."""
        response = client.get("/api/v1/lsw/days-of-week")
        
        assert response.status_code == 200
        data = response.json()
        values = [d["value"] for d in data]
        assert "monday" in values
        assert "friday" in values


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_workflow(self, client):
        """Test complete LSW workflow from generation to completion."""
        today = date.today().isoformat()
        owner_id = "workflow-owner"
        
        # 1. Generate checklist
        gen_response = client.post(
            f"/api/v1/lsw/checklists/generate?owner_id={owner_id}&target_date={today}"
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        assert gen_data["generated_count"] > 0
        
        item = gen_data["items"][0]
        
        # 2. Start the item
        start_response = client.post(f"/api/v1/lsw/items/{item['id']}/start")
        assert start_response.status_code == 200
        assert start_response.json()["status"] == "in_progress"
        
        # 3. Add a finding
        finding_response = client.post(
            f"/api/v1/lsw/items/{item['id']}/findings",
            json={
                "finding": {
                    "type": "observation",
                    "description": "Good 5S practices observed",
                },
            },
        )
        assert finding_response.status_code == 200
        
        # 4. Link a task
        task_response = client.post(
            f"/api/v1/lsw/items/{item['id']}/tasks/follow-up-task-1"
        )
        assert task_response.status_code == 200
        
        # 5. Complete the item
        complete_response = client.post(
            f"/api/v1/lsw/items/{item['id']}/complete",
            json={
                "completed_by_id": owner_id,
                "notes": "Completed successfully",
                "actual_duration_minutes": 20,
            },
        )
        assert complete_response.status_code == 200
        complete_data = complete_response.json()
        assert complete_data["status"] == "completed"
        assert len(complete_data["findings"]) == 1
        assert "follow-up-task-1" in complete_data["generated_task_ids"]
        
        # 6. Check compliance stats
        start_date = today
        end_date = today
        stats_response = client.get(
            f"/api/v1/lsw/stats/compliance?owner_id={owner_id}"
            f"&start_date={start_date}&end_date={end_date}"
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["completed"] >= 1
    
    def test_template_lifecycle(self, client):
        """Test complete template lifecycle."""
        # 1. Create template
        create_response = client.post(
            "/api/v1/lsw/templates",
            json={
                "id": "lifecycle-test",
                "name": "Lifecycle Test Template",
                "description": "Testing full lifecycle",
                "category": "coaching",
                "frequency": "weekly",
                "days_of_week": ["wednesday"],
                "estimated_duration_minutes": 60,
                "sub_items": ["Item 1", "Item 2"],
            },
        )
        assert create_response.status_code == 201
        
        # 2. Update template
        update_response = client.put(
            "/api/v1/lsw/templates/lifecycle-test",
            json={
                "name": "Updated Lifecycle Template",
                "estimated_duration_minutes": 45,
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Lifecycle Template"
        assert update_response.json()["estimated_duration_minutes"] == 45
        
        # 3. Verify update
        get_response = client.get("/api/v1/lsw/templates/lifecycle-test")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Updated Lifecycle Template"
        
        # 4. Delete template
        delete_response = client.delete("/api/v1/lsw/templates/lifecycle-test")
        assert delete_response.status_code == 204
        
        # 5. Verify deletion
        verify_response = client.get("/api/v1/lsw/templates/lifecycle-test")
        assert verify_response.status_code == 404

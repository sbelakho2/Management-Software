"""
Tests for Saved Views API endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uuid import uuid4

from sensei.api.v1.endpoints.saved_views import router, get_service, _service


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with saved views router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_service():
    """Clear the service before each test."""
    # Clear user views but keep system views
    _service._views.clear()
    yield
    _service._views.clear()


@pytest.fixture
def user_id() -> str:
    """Create a test user ID."""
    return str(uuid4())


# --------------------------------------------------------------------------
# Create View Tests
# --------------------------------------------------------------------------

class TestCreateView:
    """Tests for POST /saved-views endpoint."""
    
    def test_create_view_minimal(self, client: TestClient, user_id: str):
        """Test creating a view with minimal data."""
        response = client.post("/saved-views", json={
            "name": "My View",
            "entity_type": "task",
            "owner_id": user_id,
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My View"
        assert data["entity_type"] == "task"
        assert data["owner_id"] == user_id
        assert data["visibility"] == "private"
    
    def test_create_view_with_conditions(self, client: TestClient, user_id: str):
        """Test creating a view with filter conditions."""
        response = client.post("/saved-views", json={
            "name": "Active Tasks",
            "entity_type": "task",
            "owner_id": user_id,
            "conditions": [
                {"field": "status", "operator": "equals", "value": "active"},
            ],
        })
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["field"] == "status"
        assert data["conditions"][0]["operator"] == "equals"
    
    def test_create_view_with_all_fields(self, client: TestClient, user_id: str):
        """Test creating a view with all fields."""
        response = client.post("/saved-views", json={
            "name": "Complete View",
            "entity_type": "quote",
            "owner_id": user_id,
            "description": "A complete view",
            "conditions": [
                {"field": "status", "operator": "in", "value": ["draft", "pending"]},
                {"field": "amount", "operator": "greater_than", "value": 1000},
            ],
            "condition_logic": "and",
            "sort_fields": [
                {"field": "created_at", "direction": "desc"},
            ],
            "columns": [
                {"field": "name", "label": "Name", "width": 200, "visible": True, "order": 0},
            ],
            "visibility": "organization",
            "page_size": 50,
            "icon": "star",
            "color": "blue",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "A complete view"
        assert len(data["conditions"]) == 2
        assert len(data["sort_fields"]) == 1
        assert len(data["columns"]) == 1
        assert data["visibility"] == "organization"
        assert data["page_size"] == 50
    
    def test_create_view_invalid_entity_type(self, client: TestClient, user_id: str):
        """Test creating with invalid entity type."""
        response = client.post("/saved-views", json={
            "name": "Test",
            "entity_type": "invalid",
            "owner_id": user_id,
        })
        
        assert response.status_code == 400
        assert "Invalid entity type" in response.json()["detail"]
    
    def test_create_view_invalid_operator(self, client: TestClient, user_id: str):
        """Test creating with invalid operator."""
        response = client.post("/saved-views", json={
            "name": "Test",
            "entity_type": "task",
            "owner_id": user_id,
            "conditions": [
                {"field": "status", "operator": "invalid", "value": "test"},
            ],
        })
        
        assert response.status_code == 400
        assert "Invalid operator" in response.json()["detail"]


# --------------------------------------------------------------------------
# List Views Tests
# --------------------------------------------------------------------------

class TestListViews:
    """Tests for GET /saved-views endpoint."""
    
    def test_list_views_empty(self, client: TestClient, user_id: str):
        """Test listing views with no user views."""
        response = client.get("/saved-views", params={
            "user_id": user_id,
            "include_system": False,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["views"] == []
    
    def test_list_views_with_system(self, client: TestClient, user_id: str):
        """Test listing views including system views."""
        response = client.get("/saved-views", params={
            "user_id": user_id,
            "include_system": True,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] > 0
    
    def test_list_views_by_entity_type(self, client: TestClient, user_id: str):
        """Test filtering views by entity type."""
        # Create views of different types
        client.post("/saved-views", json={
            "name": "Task View",
            "entity_type": "task",
            "owner_id": user_id,
        })
        client.post("/saved-views", json={
            "name": "Quote View",
            "entity_type": "quote",
            "owner_id": user_id,
        })
        
        response = client.get("/saved-views", params={
            "user_id": user_id,
            "entity_type": "task",
            "include_system": False,
        })
        
        assert response.status_code == 200
        data = response.json()
        for view in data["views"]:
            assert view["entity_type"] == "task"
    
    def test_list_views_missing_user_id(self, client: TestClient):
        """Test listing without user_id."""
        response = client.get("/saved-views")
        
        assert response.status_code == 422  # Validation error


class TestListSystemViews:
    """Tests for GET /saved-views/system endpoint."""
    
    def test_list_system_views(self, client: TestClient):
        """Test listing system views."""
        response = client.get("/saved-views/system")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] > 0
        
        # All should be public visibility
        for view in data["views"]:
            assert view["visibility"] == "public"
    
    def test_list_system_views_by_entity_type(self, client: TestClient):
        """Test filtering system views by entity type."""
        response = client.get("/saved-views/system", params={
            "entity_type": "task",
        })
        
        assert response.status_code == 200
        data = response.json()
        for view in data["views"]:
            assert view["entity_type"] == "task"


# --------------------------------------------------------------------------
# Get View Tests
# --------------------------------------------------------------------------

class TestGetView:
    """Tests for GET /saved-views/{view_id} endpoint."""
    
    def test_get_view(self, client: TestClient, user_id: str):
        """Test getting a view by ID."""
        # Create a view
        create_response = client.post("/saved-views", json={
            "name": "Test View",
            "entity_type": "account",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        # Get it
        response = client.get(f"/saved-views/{view_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == view_id
        assert data["name"] == "Test View"
    
    def test_get_system_view(self, client: TestClient):
        """Test getting a system view."""
        response = client.get("/saved-views/system-tasks-overdue")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Overdue Tasks"
    
    def test_get_nonexistent_view(self, client: TestClient):
        """Test getting a nonexistent view."""
        response = client.get("/saved-views/nonexistent")
        
        assert response.status_code == 404


# --------------------------------------------------------------------------
# Update View Tests
# --------------------------------------------------------------------------

class TestUpdateView:
    """Tests for PUT /saved-views/{view_id} endpoint."""
    
    def test_update_view_name(self, client: TestClient, user_id: str):
        """Test updating view name."""
        # Create
        create_response = client.post("/saved-views", json={
            "name": "Original",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        # Update
        response = client.put(f"/saved-views/{view_id}", json={
            "name": "Updated",
        })
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"
    
    def test_update_view_conditions(self, client: TestClient, user_id: str):
        """Test updating view conditions."""
        # Create
        create_response = client.post("/saved-views", json={
            "name": "Test",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        # Update with conditions
        response = client.put(f"/saved-views/{view_id}", json={
            "conditions": [
                {"field": "status", "operator": "equals", "value": "active"},
            ],
        })
        
        assert response.status_code == 200
        assert len(response.json()["conditions"]) == 1
    
    def test_update_nonexistent_view(self, client: TestClient):
        """Test updating a nonexistent view."""
        response = client.put("/saved-views/nonexistent", json={
            "name": "New Name",
        })
        
        assert response.status_code == 404


# --------------------------------------------------------------------------
# Delete View Tests
# --------------------------------------------------------------------------

class TestDeleteView:
    """Tests for DELETE /saved-views/{view_id} endpoint."""
    
    def test_delete_view(self, client: TestClient, user_id: str):
        """Test deleting a view."""
        # Create
        create_response = client.post("/saved-views", json={
            "name": "To Delete",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        # Delete
        response = client.delete(f"/saved-views/{view_id}")
        
        assert response.status_code == 200
        assert response.json()["deleted"] is True
        
        # Verify gone
        get_response = client.get(f"/saved-views/{view_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_view(self, client: TestClient):
        """Test deleting a nonexistent view."""
        response = client.delete("/saved-views/nonexistent")
        
        assert response.status_code == 404


# --------------------------------------------------------------------------
# Duplicate View Tests
# --------------------------------------------------------------------------

class TestDuplicateView:
    """Tests for POST /saved-views/{view_id}/duplicate endpoint."""
    
    def test_duplicate_view(self, client: TestClient, user_id: str):
        """Test duplicating a view."""
        # Create original
        create_response = client.post("/saved-views", json={
            "name": "Original",
            "entity_type": "task",
            "owner_id": user_id,
            "conditions": [
                {"field": "status", "operator": "equals", "value": "active"},
            ],
        })
        view_id = create_response.json()["id"]
        
        # Duplicate
        new_owner = str(uuid4())
        response = client.post(f"/saved-views/{view_id}/duplicate", json={
            "new_owner_id": new_owner,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] != view_id
        assert data["name"] == "Copy of Original"
        assert data["owner_id"] == new_owner
        assert len(data["conditions"]) == 1
    
    def test_duplicate_view_custom_name(self, client: TestClient, user_id: str):
        """Test duplicating with custom name."""
        create_response = client.post("/saved-views", json={
            "name": "Original",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        new_owner = str(uuid4())
        response = client.post(f"/saved-views/{view_id}/duplicate", json={
            "new_owner_id": new_owner,
            "new_name": "My Custom Copy",
        })
        
        assert response.status_code == 200
        assert response.json()["name"] == "My Custom Copy"


# --------------------------------------------------------------------------
# Pin View Tests
# --------------------------------------------------------------------------

class TestPinView:
    """Tests for POST /saved-views/{view_id}/toggle-pin endpoint."""
    
    def test_toggle_pin(self, client: TestClient, user_id: str):
        """Test toggling pin status."""
        # Create
        create_response = client.post("/saved-views", json={
            "name": "Pinnable",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        # Toggle pin on
        response1 = client.post(f"/saved-views/{view_id}/toggle-pin")
        assert response1.status_code == 200
        assert response1.json()["pinned"] is True
        
        # Toggle pin off
        response2 = client.post(f"/saved-views/{view_id}/toggle-pin")
        assert response2.status_code == 200
        assert response2.json()["pinned"] is False
    
    def test_toggle_pin_nonexistent(self, client: TestClient):
        """Test toggling pin on nonexistent view."""
        response = client.post("/saved-views/nonexistent/toggle-pin")
        
        assert response.status_code == 404


class TestPinnedViews:
    """Tests for GET /saved-views/pinned endpoint."""
    
    def test_list_pinned_views(self, client: TestClient, user_id: str):
        """Test listing pinned views."""
        # Create and pin a view
        create_response = client.post("/saved-views", json={
            "name": "Pinned View",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        client.post(f"/saved-views/{view_id}/toggle-pin")
        
        # List pinned
        response = client.get("/saved-views/pinned", params={
            "user_id": user_id,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["views"][0]["id"] == view_id


# --------------------------------------------------------------------------
# Default View Tests
# --------------------------------------------------------------------------

class TestDefaultView:
    """Tests for default view endpoints."""
    
    def test_set_and_get_default(self, client: TestClient, user_id: str):
        """Test setting and getting default view."""
        # Create a view
        create_response = client.post("/saved-views", json={
            "name": "Default View",
            "entity_type": "task",
            "owner_id": user_id,
        })
        view_id = create_response.json()["id"]
        
        # Set as default
        set_response = client.post("/saved-views/default", json={
            "user_id": user_id,
            "entity_type": "task",
            "view_id": view_id,
        })
        
        assert set_response.status_code == 200
        assert set_response.json()["success"] is True
        
        # Get default
        get_response = client.get("/saved-views/default", params={
            "user_id": user_id,
            "entity_type": "task",
        })
        
        assert get_response.status_code == 200
        assert get_response.json()["id"] == view_id
    
    def test_get_default_none(self, client: TestClient, user_id: str):
        """Test getting default when none set."""
        response = client.get("/saved-views/default", params={
            "user_id": user_id,
            "entity_type": "task",
        })
        
        assert response.status_code == 200
        assert response.json() is None


# --------------------------------------------------------------------------
# Apply View Tests
# --------------------------------------------------------------------------

class TestApplyView:
    """Tests for POST /saved-views/{view_id}/apply endpoint."""
    
    def test_apply_view(self, client: TestClient, user_id: str):
        """Test applying a view to entities."""
        # Create view with filter
        create_response = client.post("/saved-views", json={
            "name": "Active Only",
            "entity_type": "task",
            "owner_id": user_id,
            "conditions": [
                {"field": "status", "operator": "equals", "value": "active"},
            ],
        })
        view_id = create_response.json()["id"]
        
        # Apply to entities
        response = client.post(f"/saved-views/{view_id}/apply", json={
            "entities": [
                {"id": "1", "status": "active"},
                {"id": "2", "status": "inactive"},
                {"id": "3", "status": "active"},
            ],
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert data["matched_count"] == 2
        assert len(data["entities"]) == 2
    
    def test_apply_view_with_pagination(self, client: TestClient, user_id: str):
        """Test applying view with pagination."""
        # Create view
        create_response = client.post("/saved-views", json={
            "name": "All",
            "entity_type": "task",
            "owner_id": user_id,
            "page_size": 2,
        })
        view_id = create_response.json()["id"]
        
        entities = [
            {"id": str(i), "name": f"Task {i}"}
            for i in range(5)
        ]
        
        # Get page 1
        response1 = client.post(f"/saved-views/{view_id}/apply", json={
            "entities": entities,
            "page": 1,
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["entities"]) == 2
        assert data1["has_more"] is True
        
        # Get page 2
        response2 = client.post(f"/saved-views/{view_id}/apply", json={
            "entities": entities,
            "page": 2,
        })
        
        data2 = response2.json()
        assert len(data2["entities"]) == 2
    
    def test_apply_view_nonexistent(self, client: TestClient):
        """Test applying nonexistent view."""
        response = client.post("/saved-views/nonexistent/apply", json={
            "entities": [],
        })
        
        assert response.status_code == 404


# --------------------------------------------------------------------------
# Reference Data Tests
# --------------------------------------------------------------------------

class TestReferenceData:
    """Tests for reference data endpoints."""
    
    def test_list_entity_types(self, client: TestClient):
        """Test listing entity types."""
        response = client.get("/saved-views/entity-types")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        values = [item["value"] for item in data]
        assert "task" in values
        assert "quote" in values
        assert "account" in values
    
    def test_list_operators(self, client: TestClient):
        """Test listing operators."""
        response = client.get("/saved-views/operators")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        values = [item["value"] for item in data]
        assert "equals" in values
        assert "contains" in values
        assert "greater_than" in values
    
    def test_list_date_presets(self, client: TestClient):
        """Test listing date presets."""
        response = client.get("/saved-views/date-presets")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        values = [item["value"] for item in data]
        assert "today" in values
        assert "this_week" in values
        assert "last_30_days" in values


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestSavedViewsIntegration:
    """Integration tests for saved views API."""
    
    def test_full_workflow(self, client: TestClient):
        """Test complete saved views workflow."""
        user_id = str(uuid4())
        
        # 1. Create a view
        create_response = client.post("/saved-views", json={
            "name": "High Priority Tasks",
            "entity_type": "task",
            "owner_id": user_id,
            "conditions": [
                {"field": "priority", "operator": "equals", "value": "high"},
            ],
            "sort_fields": [
                {"field": "due_date", "direction": "asc"},
            ],
            "description": "All high priority tasks",
            "icon": "star",
            "color": "red",
        })
        
        assert create_response.status_code == 201
        view_id = create_response.json()["id"]
        
        # 2. Get the view
        get_response = client.get(f"/saved-views/{view_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "High Priority Tasks"
        
        # 3. Update the view
        update_response = client.put(f"/saved-views/{view_id}", json={
            "name": "Urgent Tasks",
        })
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Urgent Tasks"
        
        # 4. Pin the view
        pin_response = client.post(f"/saved-views/{view_id}/toggle-pin")
        assert pin_response.json()["pinned"] is True
        
        # 5. Set as default
        client.post("/saved-views/default", json={
            "user_id": user_id,
            "entity_type": "task",
            "view_id": view_id,
        })
        
        # 6. Apply the view
        apply_response = client.post(f"/saved-views/{view_id}/apply", json={
            "entities": [
                {"id": "1", "priority": "high"},
                {"id": "2", "priority": "low"},
                {"id": "3", "priority": "high"},
            ],
        })
        assert apply_response.json()["matched_count"] == 2
        
        # 7. Duplicate for another user
        other_user = str(uuid4())
        dup_response = client.post(f"/saved-views/{view_id}/duplicate", json={
            "new_owner_id": other_user,
            "new_name": "My Copy",
        })
        assert dup_response.status_code == 200
        
        # 8. List views
        list_response = client.get("/saved-views", params={
            "user_id": user_id,
            "entity_type": "task",
            "include_system": False,
        })
        assert list_response.json()["total_count"] == 1
        
        # 9. Delete original
        delete_response = client.delete(f"/saved-views/{view_id}")
        assert delete_response.json()["deleted"] is True
        
        # 10. Verify the copy still exists
        copy_id = dup_response.json()["id"]
        copy_response = client.get(f"/saved-views/{copy_id}")
        assert copy_response.status_code == 200

"""
Comprehensive API tests for Conditions Library endpoints.

Tests cover:
- Template CRUD operations
- Template rendering
- Condition application to entities
- Hard stop and warning handling
- Condition sets
- Bulk operations
- Validation and export
- Statistics
- Metadata endpoints
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient, ASGITransport

from sensei.main import app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def entity_id():
    """Generate a random entity ID."""
    return str(uuid4())


@pytest.fixture
def user_id():
    """Generate a random user ID."""
    return str(uuid4())


# ============================================================================
# Template CRUD Tests
# ============================================================================

class TestTemplateEndpoints:
    """Tests for template CRUD endpoints."""
    
    @pytest.mark.anyio
    async def test_list_templates(self, client: AsyncClient):
        """Should list all templates."""
        response = await client.get("/api/v1/conditions/templates")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    @pytest.mark.anyio
    async def test_list_templates_filter_category(self, client: AsyncClient):
        """Should filter templates by category."""
        response = await client.get("/api/v1/conditions/templates?category=moq")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for template in data:
            assert template["category"] == "moq"
    
    @pytest.mark.anyio
    async def test_list_templates_filter_type(self, client: AsyncClient):
        """Should filter templates by condition type."""
        response = await client.get("/api/v1/conditions/templates?condition_type=hard_stop")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for template in data:
            assert template["condition_type"] == "hard_stop"
    
    @pytest.mark.anyio
    async def test_list_templates_filter_scope(self, client: AsyncClient):
        """Should filter templates by scope."""
        response = await client.get("/api/v1/conditions/templates?scope=quote")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for template in data:
            assert template["scope"] in ["quote", "universal"]
    
    @pytest.mark.anyio
    async def test_list_templates_search(self, client: AsyncClient):
        """Should search templates."""
        response = await client.get("/api/v1/conditions/templates?search=warranty")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
    
    @pytest.mark.anyio
    async def test_list_default_template_codes(self, client: AsyncClient):
        """Should list default template codes."""
        response = await client.get("/api/v1/conditions/templates/defaults")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "MOQ-001" in data
        assert "LT-001" in data
    
    @pytest.mark.anyio
    async def test_get_template_by_code(self, client: AsyncClient):
        """Should get template by code."""
        response = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == "MOQ-001"
        assert data["category"] == "moq"
    
    @pytest.mark.anyio
    async def test_get_template_by_code_not_found(self, client: AsyncClient):
        """Should return 404 for unknown code."""
        response = await client.get("/api/v1/conditions/templates/by-code/UNKNOWN-999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.anyio
    async def test_create_template(self, client: AsyncClient):
        """Should create a new template."""
        code = f"TEST-{uuid4().hex[:6].upper()}"
        
        response = await client.post(
            "/api/v1/conditions/templates",
            json={
                "code": code,
                "name": "Test Template",
                "category": "custom",
                "condition_type": "standard",
                "scope": "quote",
                "template_text": "Test with {{value}}.",
                "placeholders": [
                    {
                        "name": "value",
                        "display_label": "Value",
                        "placeholder_type": "text",
                    }
                ],
                "description": "A test template",
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == code
        assert data["is_default"] is False
    
    @pytest.mark.anyio
    async def test_create_template_duplicate_code(self, client: AsyncClient):
        """Should reject duplicate template codes."""
        code = f"DUP-{uuid4().hex[:6].upper()}"
        
        # Create first
        await client.post(
            "/api/v1/conditions/templates",
            json={
                "code": code,
                "name": "First",
                "category": "custom",
                "condition_type": "standard",
                "scope": "quote",
                "template_text": "First",
            },
        )
        
        # Try to create duplicate
        response = await client.post(
            "/api/v1/conditions/templates",
            json={
                "code": code,
                "name": "Second",
                "category": "custom",
                "condition_type": "standard",
                "scope": "quote",
                "template_text": "Second",
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_get_template_by_id(self, client: AsyncClient):
        """Should get template by ID."""
        # First get a template code to get its ID
        list_response = await client.get("/api/v1/conditions/templates?category=moq")
        templates = list_response.json()
        template_id = templates[0]["id"]
        
        response = await client.get(f"/api/v1/conditions/templates/{template_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == template_id
    
    @pytest.mark.anyio
    async def test_update_template(self, client: AsyncClient):
        """Should update a custom template."""
        # Create a template first
        code = f"UPD-{uuid4().hex[:6].upper()}"
        create_response = await client.post(
            "/api/v1/conditions/templates",
            json={
                "code": code,
                "name": "Original",
                "category": "custom",
                "condition_type": "standard",
                "scope": "quote",
                "template_text": "Original",
            },
        )
        template_id = create_response.json()["id"]
        
        # Update it
        response = await client.put(
            f"/api/v1/conditions/templates/{template_id}",
            json={"name": "Updated", "description": "Updated description"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated"
        assert data["description"] == "Updated description"
        assert data["version"] == 2
    
    @pytest.mark.anyio
    async def test_update_default_template_rejected(self, client: AsyncClient):
        """Should reject updating default templates."""
        # Get a default template
        response = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        template_id = response.json()["id"]
        
        # Try to update
        response = await client.put(
            f"/api/v1/conditions/templates/{template_id}",
            json={"name": "Modified"},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_delete_template(self, client: AsyncClient):
        """Should delete a custom template."""
        # Create a template
        code = f"DEL-{uuid4().hex[:6].upper()}"
        create_response = await client.post(
            "/api/v1/conditions/templates",
            json={
                "code": code,
                "name": "To Delete",
                "category": "custom",
                "condition_type": "standard",
                "scope": "quote",
                "template_text": "Delete me",
            },
        )
        template_id = create_response.json()["id"]
        
        # Delete it
        response = await client.delete(f"/api/v1/conditions/templates/{template_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deleted
        get_response = await client.get(f"/api/v1/conditions/templates/{template_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.anyio
    async def test_delete_default_template_rejected(self, client: AsyncClient):
        """Should reject deleting default templates."""
        response = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        template_id = response.json()["id"]
        
        response = await client.delete(f"/api/v1/conditions/templates/{template_id}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_render_template(self, client: AsyncClient):
        """Should render a template with placeholder values."""
        # Get MOQ template
        response = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        template_id = response.json()["id"]
        
        # Render it
        response = await client.post(
            f"/api/v1/conditions/templates/{template_id}/render",
            json={"placeholder_values": {"quantity": 500}},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "500" in data["rendered_text"]
    
    @pytest.mark.anyio
    async def test_render_template_missing_placeholder(self, client: AsyncClient):
        """Should error when required placeholder missing."""
        response = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        template_id = response.json()["id"]
        
        response = await client.post(
            f"/api/v1/conditions/templates/{template_id}/render",
            json={"placeholder_values": {}},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Applied Conditions Tests
# ============================================================================

class TestAppliedConditionEndpoints:
    """Tests for applied condition endpoints."""
    
    @pytest.mark.anyio
    async def test_apply_condition_from_template(self, client: AsyncClient, entity_id):
        """Should apply condition from template."""
        # Get template
        response = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        template_id = response.json()["id"]
        
        # Apply condition
        response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "template_id": template_id,
                "placeholder_values": {"quantity": 1000},
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "1000" in data["condition_text"]
        assert data["category"] == "moq"
    
    @pytest.mark.anyio
    async def test_apply_custom_condition(self, client: AsyncClient, entity_id):
        """Should apply custom text condition."""
        response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Custom condition text",
                "category": "custom",
                "condition_type": "standard",
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["condition_text"] == "Custom condition text"
        assert data["template_id"] is None
    
    @pytest.mark.anyio
    async def test_apply_condition_requires_template_or_text(self, client: AsyncClient, entity_id):
        """Should error when neither template nor text provided."""
        response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_get_conditions_for_entity(self, client: AsyncClient, entity_id):
        """Should get conditions for an entity."""
        # Apply some conditions
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Condition 1",
                "sort_order": 0,
            },
        )
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Condition 2",
                "sort_order": 1,
            },
        )
        
        # Get conditions
        response = await client.get(f"/api/v1/conditions/applied/quote/{entity_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
    
    @pytest.mark.anyio
    async def test_get_conditions_filter_category(self, client: AsyncClient, entity_id):
        """Should filter conditions by category."""
        # Apply conditions with different categories
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "MOQ",
                "category": "moq",
            },
        )
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Lead Time",
                "category": "lead_time",
            },
        )
        
        # Filter by category
        response = await client.get(
            f"/api/v1/conditions/applied/quote/{entity_id}?category=moq"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "moq"
    
    @pytest.mark.anyio
    async def test_get_hard_stops(self, client: AsyncClient, entity_id):
        """Should get hard stops for entity."""
        # Apply hard stop
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Blocking issue",
                "condition_type": "hard_stop",
            },
        )
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Standard",
                "condition_type": "standard",
            },
        )
        
        # Get hard stops
        response = await client.get(
            f"/api/v1/conditions/applied/quote/{entity_id}/hard-stops"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["condition_type"] == "hard_stop"
    
    @pytest.mark.anyio
    async def test_validate_entity(self, client: AsyncClient, entity_id):
        """Should validate entity conditions."""
        # Apply conditions
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Hard stop",
                "condition_type": "hard_stop",
            },
        )
        
        # Validate
        response = await client.get(
            f"/api/v1/conditions/applied/quote/{entity_id}/validate"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["can_proceed"] is False
        assert data["unresolved_hard_stops"] == 1
    
    @pytest.mark.anyio
    async def test_acknowledge_warning(self, client: AsyncClient, entity_id, user_id):
        """Should acknowledge warning condition."""
        # Apply warning
        apply_response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Warning",
                "condition_type": "warning",
            },
        )
        condition_id = apply_response.json()["id"]
        
        # Acknowledge
        response = await client.post(
            f"/api/v1/conditions/applied/{condition_id}/acknowledge",
            json={"acknowledged_by_id": user_id},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_acknowledged"] is True
    
    @pytest.mark.anyio
    async def test_acknowledge_non_warning_rejected(self, client: AsyncClient, entity_id, user_id):
        """Should reject acknowledging non-warning conditions."""
        # Apply standard condition
        apply_response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Standard",
                "condition_type": "standard",
            },
        )
        condition_id = apply_response.json()["id"]
        
        # Try to acknowledge
        response = await client.post(
            f"/api/v1/conditions/applied/{condition_id}/acknowledge",
            json={"acknowledged_by_id": user_id},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_resolve_hard_stop(self, client: AsyncClient, entity_id, user_id):
        """Should resolve hard stop condition."""
        # Apply hard stop
        apply_response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Blocking",
                "condition_type": "hard_stop",
            },
        )
        condition_id = apply_response.json()["id"]
        
        # Resolve
        response = await client.post(
            f"/api/v1/conditions/applied/{condition_id}/resolve",
            json={
                "resolved_by_id": user_id,
                "resolution_notes": "Issue fixed",
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_resolved"] is True
        assert data["resolution_notes"] == "Issue fixed"
    
    @pytest.mark.anyio
    async def test_update_condition_text(self, client: AsyncClient, entity_id):
        """Should update condition text."""
        # Apply condition
        apply_response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Original",
            },
        )
        condition_id = apply_response.json()["id"]
        
        # Update text
        response = await client.put(
            f"/api/v1/conditions/applied/{condition_id}/text",
            json={"new_text": "Updated text"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["condition_text"] == "Updated text"
    
    @pytest.mark.anyio
    async def test_remove_condition(self, client: AsyncClient, entity_id):
        """Should remove applied condition."""
        # Apply condition
        apply_response = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "To remove",
            },
        )
        condition_id = apply_response.json()["id"]
        
        # Remove
        response = await client.delete(f"/api/v1/conditions/applied/{condition_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @pytest.mark.anyio
    async def test_reorder_conditions(self, client: AsyncClient, entity_id):
        """Should reorder conditions."""
        # Apply conditions
        r1 = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "First",
                "sort_order": 0,
            },
        )
        r2 = await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Second",
                "sort_order": 1,
            },
        )
        
        id1 = r1.json()["id"]
        id2 = r2.json()["id"]
        
        # Reorder
        response = await client.post(
            f"/api/v1/conditions/applied/quote/{entity_id}/reorder",
            json={"condition_order": [id2, id1]},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data[0]["condition_text"] == "Second"
    
    @pytest.mark.anyio
    async def test_copy_conditions(self, client: AsyncClient):
        """Should copy conditions between entities."""
        source_id = str(uuid4())
        target_id = str(uuid4())
        
        # Apply to source
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": source_id,
                "custom_text": "Condition 1",
            },
        )
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": source_id,
                "custom_text": "Condition 2",
            },
        )
        
        # Copy
        response = await client.post(
            "/api/v1/conditions/applied/copy",
            json={
                "source_entity_type": "quote",
                "source_entity_id": source_id,
                "target_entity_type": "quote",
                "target_entity_id": target_id,
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
    
    @pytest.mark.anyio
    async def test_clear_conditions(self, client: AsyncClient, entity_id):
        """Should clear all conditions."""
        # Apply conditions
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Condition 1",
            },
        )
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Condition 2",
            },
        )
        
        # Clear
        response = await client.delete(
            f"/api/v1/conditions/applied/quote/{entity_id}/clear"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["cleared_count"] == 2
    
    @pytest.mark.anyio
    async def test_export_conditions_text(self, client: AsyncClient, entity_id):
        """Should export conditions as text."""
        # Apply conditions
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Test condition",
            },
        )
        
        # Export
        response = await client.get(
            f"/api/v1/conditions/applied/quote/{entity_id}/export?format=text"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "text"
        assert "Test condition" in data["content"]
    
    @pytest.mark.anyio
    async def test_export_conditions_json(self, client: AsyncClient, entity_id):
        """Should export conditions as JSON."""
        # Apply conditions
        await client.post(
            "/api/v1/conditions/applied",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
                "custom_text": "Test condition",
            },
        )
        
        # Export
        response = await client.get(
            f"/api/v1/conditions/applied/quote/{entity_id}/export?format=json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "json"
        assert len(data["conditions"]) == 1


# ============================================================================
# Condition Sets Tests
# ============================================================================

class TestConditionSetEndpoints:
    """Tests for condition set endpoints."""
    
    @pytest.mark.anyio
    async def test_list_condition_sets(self, client: AsyncClient):
        """Should list condition sets."""
        response = await client.get("/api/v1/conditions/sets")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have default sets
    
    @pytest.mark.anyio
    async def test_create_condition_set(self, client: AsyncClient):
        """Should create a condition set."""
        # Get template IDs
        moq = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        lt = await client.get("/api/v1/conditions/templates/by-code/LT-001")
        
        response = await client.post(
            "/api/v1/conditions/sets",
            json={
                "name": f"Test Set {uuid4().hex[:6]}",
                "description": "A test set",
                "condition_template_ids": [
                    moq.json()["id"],
                    lt.json()["id"],
                ],
            },
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["condition_template_ids"]) == 2
        assert data["is_default"] is False
    
    @pytest.mark.anyio
    async def test_create_condition_set_invalid_template(self, client: AsyncClient):
        """Should reject sets with invalid template IDs."""
        response = await client.post(
            "/api/v1/conditions/sets",
            json={
                "name": "Bad Set",
                "condition_template_ids": [str(uuid4())],
            },
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_get_condition_set(self, client: AsyncClient):
        """Should get condition set by ID."""
        # List sets
        list_response = await client.get("/api/v1/conditions/sets")
        sets = list_response.json()
        set_id = sets[0]["id"]
        
        # Get by ID
        response = await client.get(f"/api/v1/conditions/sets/{set_id}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == set_id
    
    @pytest.mark.anyio
    async def test_update_condition_set(self, client: AsyncClient):
        """Should update a custom condition set."""
        # Create a set
        moq = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        create_response = await client.post(
            "/api/v1/conditions/sets",
            json={
                "name": f"Update Test {uuid4().hex[:6]}",
                "condition_template_ids": [moq.json()["id"]],
            },
        )
        set_id = create_response.json()["id"]
        
        # Update it
        response = await client.put(
            f"/api/v1/conditions/sets/{set_id}",
            json={"name": "Updated Name", "description": "Updated desc"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"
    
    @pytest.mark.anyio
    async def test_delete_condition_set(self, client: AsyncClient):
        """Should delete a custom condition set."""
        # Create a set
        moq = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        create_response = await client.post(
            "/api/v1/conditions/sets",
            json={
                "name": f"Delete Test {uuid4().hex[:6]}",
                "condition_template_ids": [moq.json()["id"]],
            },
        )
        set_id = create_response.json()["id"]
        
        # Delete it
        response = await client.delete(f"/api/v1/conditions/sets/{set_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @pytest.mark.anyio
    async def test_apply_condition_set(self, client: AsyncClient, entity_id):
        """Should apply condition set to entity."""
        # Get a set with no-placeholder templates (compliance)
        comp1 = await client.get("/api/v1/conditions/templates/by-code/COMP-001")
        comp2 = await client.get("/api/v1/conditions/templates/by-code/COMP-002")
        
        # Create set
        create_response = await client.post(
            "/api/v1/conditions/sets",
            json={
                "name": f"Apply Test {uuid4().hex[:6]}",
                "condition_template_ids": [
                    comp1.json()["id"],
                    comp2.json()["id"],
                ],
            },
        )
        set_id = create_response.json()["id"]
        
        # Apply set
        response = await client.post(
            f"/api/v1/conditions/sets/{set_id}/apply",
            json={
                "entity_type": "quote",
                "entity_id": entity_id,
            },
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatisticsEndpoints:
    """Tests for statistics endpoints."""
    
    @pytest.mark.anyio
    async def test_template_usage_stats(self, client: AsyncClient):
        """Should get template usage statistics."""
        # Apply some conditions from templates
        moq = await client.get("/api/v1/conditions/templates/by-code/MOQ-001")
        template_id = moq.json()["id"]
        
        for _ in range(2):
            await client.post(
                "/api/v1/conditions/applied",
                json={
                    "entity_type": "quote",
                    "entity_id": str(uuid4()),
                    "template_id": template_id,
                    "placeholder_values": {"quantity": 100},
                },
            )
        
        # Get stats
        response = await client.get("/api/v1/conditions/stats/usage")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.anyio
    async def test_category_stats(self, client: AsyncClient):
        """Should get category statistics."""
        response = await client.get("/api/v1/conditions/stats/categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


# ============================================================================
# Metadata Tests
# ============================================================================

class TestMetadataEndpoints:
    """Tests for metadata endpoints."""
    
    @pytest.mark.anyio
    async def test_get_categories(self, client: AsyncClient):
        """Should get all categories."""
        response = await client.get("/api/v1/conditions/categories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        values = [c["value"] for c in data]
        assert "moq" in values
        assert "lead_time" in values
        assert "payment_terms" in values
    
    @pytest.mark.anyio
    async def test_get_condition_types(self, client: AsyncClient):
        """Should get all condition types."""
        response = await client.get("/api/v1/conditions/types")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        values = [ct["value"] for ct in data]
        assert "standard" in values
        assert "warning" in values
        assert "hard_stop" in values
    
    @pytest.mark.anyio
    async def test_get_scopes(self, client: AsyncClient):
        """Should get all scopes."""
        response = await client.get("/api/v1/conditions/scopes")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        values = [s["value"] for s in data]
        assert "quote" in values
        assert "qualification" in values
        assert "universal" in values
    
    @pytest.mark.anyio
    async def test_get_placeholder_types(self, client: AsyncClient):
        """Should get all placeholder types."""
        response = await client.get("/api/v1/conditions/placeholder-types")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        values = [pt["value"] for pt in data]
        assert "number" in values
        assert "text" in values
        assert "select" in values


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.anyio
    async def test_invalid_category(self, client: AsyncClient):
        """Should reject invalid category."""
        response = await client.get("/api/v1/conditions/templates?category=invalid")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_invalid_condition_type(self, client: AsyncClient):
        """Should reject invalid condition type."""
        response = await client.get("/api/v1/conditions/templates?condition_type=invalid")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.anyio
    async def test_template_not_found(self, client: AsyncClient):
        """Should return 404 for unknown template."""
        response = await client.get(f"/api/v1/conditions/templates/{uuid4()}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.anyio
    async def test_condition_not_found_acknowledge(self, client: AsyncClient, user_id):
        """Should return 404 when acknowledging unknown condition."""
        response = await client.post(
            f"/api/v1/conditions/applied/{uuid4()}/acknowledge",
            json={"acknowledged_by_id": user_id},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.anyio
    async def test_condition_set_not_found(self, client: AsyncClient):
        """Should return 404 for unknown condition set."""
        response = await client.get(f"/api/v1/conditions/sets/{uuid4()}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

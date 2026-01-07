"""
Tests for Template Cloning Service.

Verifies:
- Entity cloning
- Template management
- Creating from templates
- Quote versioning
- Deep cloning
- Clone history
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.services.template_cloning import (
    CloneableEntityType,
    CloneHistory,
    CloneMode,
    CloneOptions,
    CloneResult,
    FieldMapping,
    Template,
    TemplateCategory,
    TemplateCloningService,
)


class TestTemplateManagement:
    """Tests for template CRUD operations."""
    
    def test_create_template(self) -> None:
        """Test creating a new template."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Custom RFQ",
            description="Custom RFQ template",
            category=TemplateCategory.RFQ,
            entity_type=CloneableEntityType.RFQ,
            template_data={"type": "custom"},
            default_values={"priority": "high"},
            tags=["custom"],
        )
        
        assert template.id is not None
        assert template.name == "Custom RFQ"
        assert template.category == TemplateCategory.RFQ
        assert template.template_data["type"] == "custom"
    
    def test_get_template(self) -> None:
        """Test retrieving a template by ID."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Test Template",
            category=TemplateCategory.QUOTE,
            entity_type=CloneableEntityType.QUOTE,
        )
        
        retrieved = service.get_template(template.id)
        
        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.name == "Test Template"
    
    def test_get_templates_by_category(self) -> None:
        """Test filtering templates by category."""
        service = TemplateCloningService()
        
        service.create_template(
            name="Quote Template",
            category=TemplateCategory.QUOTE,
            entity_type=CloneableEntityType.QUOTE,
        )
        
        quote_templates = service.get_templates(category=TemplateCategory.QUOTE)
        rfq_templates = service.get_templates(category=TemplateCategory.RFQ)
        
        assert len(quote_templates) >= 1
        assert all(t.category == TemplateCategory.QUOTE for t in quote_templates)
    
    def test_get_templates_by_entity_type(self) -> None:
        """Test filtering templates by entity type."""
        service = TemplateCloningService()
        
        templates = service.get_templates(entity_type=CloneableEntityType.RFQ)
        
        assert all(t.entity_type == CloneableEntityType.RFQ for t in templates)
    
    def test_update_template(self) -> None:
        """Test updating a template."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Original Name",
            category=TemplateCategory.CUSTOM,
            entity_type=CloneableEntityType.TASK,
        )
        
        updated = service.update_template(
            template.id,
            name="Updated Name",
            description="New description",
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "New description"
    
    def test_update_system_template_limited(self) -> None:
        """Test that system templates have limited update options."""
        service = TemplateCloningService()
        
        # Get a system template
        system_templates = [t for t in service.get_templates() if t.is_system]
        assert len(system_templates) > 0
        
        template = system_templates[0]
        original_name = template.name
        
        # Try to update name (should be ignored)
        updated = service.update_template(
            template.id,
            name="New Name",
            is_active=False,
        )
        
        assert updated.name == original_name  # Name unchanged
        assert updated.is_active is False  # is_active allowed
    
    def test_delete_template(self) -> None:
        """Test deleting a user template."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Deletable",
            category=TemplateCategory.CUSTOM,
            entity_type=CloneableEntityType.TASK,
        )
        
        result = service.delete_template(template.id)
        
        assert result is True
        assert service.get_template(template.id) is None
    
    def test_delete_system_template_soft_deletes(self) -> None:
        """Test that system templates are soft-deleted."""
        service = TemplateCloningService()
        
        system_templates = [t for t in service.get_templates() if t.is_system]
        template = system_templates[0]
        
        result = service.delete_template(template.id)
        
        assert result is True
        # Template still exists but is inactive
        deleted = service.get_template(template.id)
        assert deleted is not None
        assert deleted.is_active is False
    
    def test_search_templates(self) -> None:
        """Test searching templates by name/description."""
        service = TemplateCloningService()
        
        service.create_template(
            name="Special Quote",
            description="For special customers",
            category=TemplateCategory.QUOTE,
            entity_type=CloneableEntityType.QUOTE,
            tags=["special"],
        )
        
        results = service.search_templates("special")
        
        assert len(results) >= 1
        assert any("special" in t.name.lower() for t in results)
    
    def test_default_templates_created(self) -> None:
        """Test that default templates are created on init."""
        service = TemplateCloningService()
        
        all_templates = service.get_templates()
        system_templates = [t for t in all_templates if t.is_system]
        
        assert len(system_templates) >= 5
        
        # Check for specific templates
        names = [t.name for t in system_templates]
        assert "Standard RFQ" in names
        assert "Standard Quote" in names


class TestEntityCloning:
    """Tests for entity cloning operations."""
    
    def test_clone_entity_basic(self) -> None:
        """Test basic entity cloning."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.RFQ,
            name="Original RFQ",
            status="submitted",
            priority="high",
        )
        
        result = service.clone_entity(
            CloneableEntityType.RFQ,
            source_id,
        )
        
        assert result.success is True
        assert result.target_id is not None
        assert result.target_id != source_id
        
        # Check cloned entity
        cloned = service._get_entity(CloneableEntityType.RFQ, result.target_id)
        assert cloned["name"] == "Original RFQ (Copy)"
        assert cloned["status"] == "draft"  # Reset
    
    def test_clone_entity_not_found(self) -> None:
        """Test cloning non-existent entity."""
        service = TemplateCloningService()
        
        result = service.clone_entity(
            CloneableEntityType.RFQ,
            uuid4(),
        )
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_clone_with_name_prefix_suffix(self) -> None:
        """Test cloning with custom name prefix/suffix."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            name="Original Quote",
        )
        
        options = CloneOptions(
            name_prefix="[COPY] ",
            name_suffix=" - v2",
        )
        
        result = service.clone_entity(
            CloneableEntityType.QUOTE,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.QUOTE, result.target_id)
        assert cloned["name"] == "[COPY] Original Quote - v2"
    
    def test_clone_with_owner_override(self) -> None:
        """Test cloning with new owner assignment."""
        service = TemplateCloningService()
        
        original_owner = uuid4()
        new_owner = uuid4()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.TASK,
            owner_id=original_owner,
        )
        
        options = CloneOptions(new_owner_id=new_owner)
        
        result = service.clone_entity(
            CloneableEntityType.TASK,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.TASK, result.target_id)
        assert cloned["owner_id"] == new_owner
    
    def test_clone_with_field_overrides(self) -> None:
        """Test cloning with field overrides."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.RFQ,
            priority="low",
            notes="Original notes",
        )
        
        options = CloneOptions(
            field_overrides={
                "priority": "high",
                "notes": "Updated notes for clone",
            },
        )
        
        result = service.clone_entity(
            CloneableEntityType.RFQ,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.RFQ, result.target_id)
        assert cloned["priority"] == "high"
        assert cloned["notes"] == "Updated notes for clone"
    
    def test_clone_with_fields_to_skip(self) -> None:
        """Test cloning with fields skipped."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            name="Test Quote",
            internal_notes="Secret notes",
            confidential_data="Sensitive",
        )
        
        options = CloneOptions(
            fields_to_skip=["internal_notes", "confidential_data"],
        )
        
        result = service.clone_entity(
            CloneableEntityType.QUOTE,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.QUOTE, result.target_id)
        assert "internal_notes" not in cloned
        assert "confidential_data" not in cloned
    
    def test_clone_with_field_mappings(self) -> None:
        """Test cloning with field transformations."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            revision_count=5,
            title="Original Title",
        )
        
        options = CloneOptions(
            field_mappings=[
                FieldMapping(
                    source_field="revision_count",
                    transformation="increment",
                ),
                FieldMapping(
                    source_field="title",
                    transformation="prefix",
                ),
            ],
        )
        
        result = service.clone_entity(
            CloneableEntityType.QUOTE,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.QUOTE, result.target_id)
        assert cloned["revision_count"] == 6
        assert cloned["title"].startswith("Copy of")
    
    def test_clone_records_history(self) -> None:
        """Test that clone operations are recorded in history."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(CloneableEntityType.TASK)
        
        result = service.clone_entity(CloneableEntityType.TASK, source_id)
        
        # Check source history
        source_history = service.get_clone_history(source_id)
        assert source_history is not None
        assert result.target_id in source_history.cloned_to_ids
        
        # Check target history
        target_history = service.get_clone_history(result.target_id)
        assert target_history is not None
        assert target_history.cloned_from_id == source_id


class TestDeepCloning:
    """Tests for deep cloning with relationships."""
    
    def test_deep_clone_with_children(self) -> None:
        """Test deep cloning includes child entities."""
        service = TemplateCloningService()
        
        # Create parent
        project_id = service.create_mock_entity(
            CloneableEntityType.PROJECT,
            name="Test Project",
        )
        
        # Create children
        task_id = service.create_mock_entity(
            CloneableEntityType.TASK,
            name="Task 1",
            project_id=project_id,
        )
        
        # Deep clone
        options = CloneOptions(
            mode=CloneMode.DEEP,
            include_children=True,
        )
        
        result = service.clone_entity(
            CloneableEntityType.PROJECT,
            project_id,
            options,
        )
        
        assert result.success is True
        assert len(result.cloned_children) == 1
        assert task_id in result.cloned_children
    
    def test_shallow_clone_excludes_children(self) -> None:
        """Test shallow cloning doesn't include children."""
        service = TemplateCloningService()
        
        project_id = service.create_mock_entity(
            CloneableEntityType.PROJECT,
        )
        
        service.create_mock_entity(
            CloneableEntityType.TASK,
            project_id=project_id,
        )
        
        options = CloneOptions(mode=CloneMode.SHALLOW)
        
        result = service.clone_entity(
            CloneableEntityType.PROJECT,
            project_id,
            options,
        )
        
        assert result.success is True
        assert len(result.cloned_children) == 0


class TestCreateFromTemplate:
    """Tests for creating entities from templates."""
    
    def test_create_from_template_basic(self) -> None:
        """Test creating an entity from a template."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Test Template",
            category=TemplateCategory.WORK_ORDER,
            entity_type=CloneableEntityType.TASK,
            template_data={
                "type": "standard",
                "category": "development",
            },
            default_values={
                "priority": "normal",
                "estimated_hours": 8,
            },
        )
        
        result = service.create_from_template(template.id)
        
        assert result.success is True
        assert result.target_id is not None
        assert result.template_id == template.id
        
        entity = service._get_entity(CloneableEntityType.TASK, result.target_id)
        assert entity["type"] == "standard"
        assert entity["priority"] == "normal"
    
    def test_create_from_template_with_overrides(self) -> None:
        """Test creating with overridden values."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="RFQ Template",
            category=TemplateCategory.RFQ,
            entity_type=CloneableEntityType.RFQ,
            default_values={
                "priority": "normal",
                "status": "draft",
            },
        )
        
        result = service.create_from_template(
            template.id,
            overrides={
                "priority": "high",
                "customer_name": "ACME Corp",
            },
        )
        
        entity = service._get_entity(CloneableEntityType.RFQ, result.target_id)
        assert entity["priority"] == "high"
        assert entity["customer_name"] == "ACME Corp"
    
    def test_create_from_template_not_found(self) -> None:
        """Test creating from non-existent template."""
        service = TemplateCloningService()
        
        result = service.create_from_template(uuid4())
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_create_from_template_updates_usage(self) -> None:
        """Test that template usage is tracked."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Tracked Template",
            category=TemplateCategory.WORK_ORDER,
            entity_type=CloneableEntityType.WORK_ORDER,
        )
        
        assert template.use_count == 0
        assert template.last_used_at is None
        
        service.create_from_template(template.id)
        service.create_from_template(template.id)
        
        assert template.use_count == 2
        assert template.last_used_at is not None
    
    def test_create_from_template_records_history(self) -> None:
        """Test that template creation is recorded in history."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="History Template",
            category=TemplateCategory.CHECKLIST,
            entity_type=CloneableEntityType.CHECKLIST,
        )
        
        result = service.create_from_template(template.id)
        
        history = service.get_clone_history(result.target_id)
        assert history is not None
        assert history.created_from_template_id == template.id
        assert history.created_from_template_name == "History Template"


class TestQuoteVersioning:
    """Tests for quote revision/versioning."""
    
    def test_create_quote_revision(self) -> None:
        """Test creating a revision of a quote."""
        service = TemplateCloningService()
        
        original_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            name="Quote v1",
            version=1,
            is_current=True,
            line_items=[{"part": "A", "qty": 10}],
        )
        
        result = service.create_quote_revision(original_id)
        
        assert result.success is True
        assert result.target_id is not None
        
        # Check revision
        revision = service._get_entity(CloneableEntityType.QUOTE, result.target_id)
        assert revision["version"] == 2
        assert revision["previous_version_id"] == original_id
        assert revision["is_current"] is True
        assert revision["line_items"] == [{"part": "A", "qty": 10}]  # Inherited
        
        # Check original is no longer current
        original = service._get_entity(CloneableEntityType.QUOTE, original_id)
        assert original["is_current"] is False
    
    def test_create_quote_revision_not_found(self) -> None:
        """Test revision of non-existent quote."""
        service = TemplateCloningService()
        
        result = service.create_quote_revision(uuid4())
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_get_quote_versions(self) -> None:
        """Test getting all versions of a quote."""
        service = TemplateCloningService()
        
        # Create v1
        v1_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            name="Quote",
            version=1,
            is_current=True,
        )
        
        # Create v2
        result2 = service.create_quote_revision(v1_id)
        
        # Create v3
        result3 = service.create_quote_revision(result2.target_id)
        
        # Get all versions
        versions = service.get_quote_versions(result3.target_id)
        
        assert len(versions) == 3
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2
        assert versions[2]["version"] == 3
    
    def test_quote_revision_chain(self) -> None:
        """Test multiple quote revisions maintain chain."""
        service = TemplateCloningService()
        
        v1_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            version=1,
        )
        
        v2_result = service.create_quote_revision(v1_id)
        v3_result = service.create_quote_revision(v2_result.target_id)
        
        v3 = service._get_entity(CloneableEntityType.QUOTE, v3_result.target_id)
        
        assert v3["previous_version_id"] == v2_result.target_id
        assert v3["version"] == 3


class TestCloneHistory:
    """Tests for clone history tracking."""
    
    def test_get_clone_history(self) -> None:
        """Test retrieving clone history."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(CloneableEntityType.RFQ)
        
        result = service.clone_entity(CloneableEntityType.RFQ, source_id)
        
        history = service.get_clone_history(result.target_id)
        
        assert history is not None
        assert history.entity_id == result.target_id
        assert history.cloned_from_id == source_id
    
    def test_get_clone_chain(self) -> None:
        """Test getting the full clone chain."""
        service = TemplateCloningService()
        
        original_id = service.create_mock_entity(CloneableEntityType.TASK)
        
        # Clone chain: original -> clone1 -> clone2
        result1 = service.clone_entity(CloneableEntityType.TASK, original_id)
        result2 = service.clone_entity(CloneableEntityType.TASK, result1.target_id)
        
        chain = service.get_clone_chain(result1.target_id)
        
        assert original_id in chain
        assert result1.target_id in chain
        assert result2.target_id in chain
    
    def test_clone_history_for_new_entity(self) -> None:
        """Test that new entities have no clone history."""
        service = TemplateCloningService()
        
        entity_id = service.create_mock_entity(CloneableEntityType.PRODUCT)
        
        history = service.get_clone_history(entity_id)
        
        assert history is None


class TestCloneOptions:
    """Tests for clone options."""
    
    def test_default_clone_options(self) -> None:
        """Test default clone options."""
        options = CloneOptions()
        
        assert options.mode == CloneMode.SHALLOW
        assert options.include_attachments is False
        assert options.include_children is False
        assert options.name_suffix == " (Copy)"
    
    def test_clone_with_all_options(self) -> None:
        """Test clone with all options specified."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            name="Full Options Test",
            priority="low",
            status="approved",
        )
        
        new_owner = uuid4()
        options = CloneOptions(
            mode=CloneMode.SHALLOW,
            include_attachments=True,
            include_comments=True,
            name_prefix="[CLONE] ",
            name_suffix=" - COPY",
            new_owner_id=new_owner,
            field_overrides={"priority": "high"},
        )
        
        result = service.clone_entity(
            CloneableEntityType.QUOTE,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.QUOTE, result.target_id)
        assert cloned["name"] == "[CLONE] Full Options Test - COPY"
        assert cloned["owner_id"] == new_owner
        assert cloned["priority"] == "high"
        assert cloned["status"] == "draft"  # Always reset


class TestFieldMappings:
    """Tests for field mapping transformations."""
    
    def test_field_mapping_increment(self) -> None:
        """Test increment transformation."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            revision_number=3,
        )
        
        options = CloneOptions(
            field_mappings=[
                FieldMapping(
                    source_field="revision_number",
                    transformation="increment",
                ),
            ],
        )
        
        result = service.clone_entity(
            CloneableEntityType.QUOTE,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.QUOTE, result.target_id)
        assert cloned["revision_number"] == 4
    
    def test_field_mapping_reset(self) -> None:
        """Test reset transformation."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.TASK,
            completion_percentage=75,
        )
        
        options = CloneOptions(
            field_mappings=[
                FieldMapping(
                    source_field="completion_percentage",
                    transformation="reset",
                    default_value=0,
                ),
            ],
        )
        
        result = service.clone_entity(
            CloneableEntityType.TASK,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.TASK, result.target_id)
        assert cloned["completion_percentage"] == 0
    
    def test_field_mapping_skip(self) -> None:
        """Test skipping a field."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.RFQ,
            sensitive_data="secret",
            normal_data="visible",
        )
        
        options = CloneOptions(
            field_mappings=[
                FieldMapping(
                    source_field="sensitive_data",
                    skip=True,
                ),
            ],
        )
        
        result = service.clone_entity(
            CloneableEntityType.RFQ,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.RFQ, result.target_id)
        assert "sensitive_data" not in cloned
        assert cloned["normal_data"] == "visible"
    
    def test_field_mapping_rename(self) -> None:
        """Test renaming a field during clone."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.PRODUCT,
            old_field_name="value",
        )
        
        options = CloneOptions(
            field_mappings=[
                FieldMapping(
                    source_field="old_field_name",
                    target_field="new_field_name",
                ),
            ],
        )
        
        result = service.clone_entity(
            CloneableEntityType.PRODUCT,
            source_id,
            options,
        )
        
        cloned = service._get_entity(CloneableEntityType.PRODUCT, result.target_id)
        assert cloned.get("new_field_name") == "value"


class TestSystemTemplates:
    """Tests for system-provided templates."""
    
    def test_system_templates_exist(self) -> None:
        """Test that system templates are available."""
        service = TemplateCloningService()
        
        templates = service.get_templates()
        system = [t for t in templates if t.is_system]
        
        assert len(system) >= 5
    
    def test_system_templates_are_marked(self) -> None:
        """Test that system templates are properly marked."""
        service = TemplateCloningService()
        
        templates = service.get_templates()
        system = [t for t in templates if t.is_system]
        
        for template in system:
            assert template.is_system is True
    
    def test_system_templates_sorted_first(self) -> None:
        """Test that system templates appear first in list."""
        service = TemplateCloningService()
        
        # Add user template
        service.create_template(
            name="AAA User Template",  # Would sort first alphabetically
            category=TemplateCategory.QUOTE,
            entity_type=CloneableEntityType.QUOTE,
        )
        
        templates = service.get_templates()
        system_count = sum(1 for t in templates if t.is_system)
        
        # First templates should be system templates
        for i in range(system_count):
            assert templates[i].is_system is True


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_clone_entity_with_null_fields(self) -> None:
        """Test cloning entity with null fields."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.TASK,
            description=None,
            due_date=None,
        )
        
        result = service.clone_entity(CloneableEntityType.TASK, source_id)
        
        assert result.success is True
    
    def test_clone_with_empty_name(self) -> None:
        """Test cloning entity with empty name."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.RFQ,
            name="",
        )
        
        result = service.clone_entity(CloneableEntityType.RFQ, source_id)
        
        cloned = service._get_entity(CloneableEntityType.RFQ, result.target_id)
        assert cloned["name"] == " (Copy)"
    
    def test_multiple_clones_from_same_source(self) -> None:
        """Test creating multiple clones from same source."""
        service = TemplateCloningService()
        
        source_id = service.create_mock_entity(
            CloneableEntityType.QUOTE,
            name="Original",
        )
        
        result1 = service.clone_entity(CloneableEntityType.QUOTE, source_id)
        result2 = service.clone_entity(CloneableEntityType.QUOTE, source_id)
        result3 = service.clone_entity(CloneableEntityType.QUOTE, source_id)
        
        assert result1.target_id != result2.target_id
        assert result2.target_id != result3.target_id
        
        # All should be in source's clone list
        history = service.get_clone_history(source_id)
        assert result1.target_id in history.cloned_to_ids
        assert result2.target_id in history.cloned_to_ids
        assert result3.target_id in history.cloned_to_ids
    
    def test_clone_of_clone(self) -> None:
        """Test cloning an already cloned entity."""
        service = TemplateCloningService()
        
        original_id = service.create_mock_entity(
            CloneableEntityType.TASK,
            name="Original",
        )
        
        first_clone = service.clone_entity(CloneableEntityType.TASK, original_id)
        second_clone = service.clone_entity(CloneableEntityType.TASK, first_clone.target_id)
        
        assert second_clone.success is True
        assert second_clone.source_id == first_clone.target_id
        
        # Check chain
        chain = service.get_clone_chain(second_clone.target_id)
        assert original_id in chain
        assert first_clone.target_id in chain
        assert second_clone.target_id in chain
    
    def test_template_with_empty_data(self) -> None:
        """Test creating from template with empty data."""
        service = TemplateCloningService()
        
        template = service.create_template(
            name="Empty Template",
            category=TemplateCategory.CUSTOM,
            entity_type=CloneableEntityType.TASK,
            template_data={},
            default_values={},
        )
        
        result = service.create_from_template(template.id)
        
        assert result.success is True
        entity = service._get_entity(CloneableEntityType.TASK, result.target_id)
        assert entity["id"] == result.target_id

"""
Comprehensive tests for the Conditions Library Service.

Tests cover:
- Template management (CRUD)
- Template rendering with placeholders
- Condition application to entities
- Hard stop and warning handling
- Condition sets
- Bulk operations
- Validation
- Statistics
"""

import pytest
from datetime import datetime
from uuid import uuid4

from sensei.services.conditions_library import (
    ConditionsLibraryService,
    ConditionTemplate,
    AppliedCondition,
    ConditionSet,
    Placeholder,
    ConditionCategory,
    ConditionType,
    ConditionScope,
    PlaceholderType,
    get_conditions_library_service,
    get_default_template_codes,
    get_default_condition_set_ids,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def service() -> ConditionsLibraryService:
    """Create a fresh service instance for each test."""
    return ConditionsLibraryService()


@pytest.fixture
def entity_id():
    """Generate a random entity ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Generate a random user ID."""
    return uuid4()


# ============================================================================
# Default Templates Tests
# ============================================================================

class TestDefaultTemplates:
    """Tests for default templates."""
    
    def test_default_templates_loaded(self, service: ConditionsLibraryService):
        """Service should have default templates loaded."""
        templates = service.list_templates()
        assert len(templates) > 0
        
        # Check that all defaults are marked as default
        default_templates = [t for t in templates if t.is_default]
        assert len(default_templates) == len(templates)
    
    def test_default_template_codes(self):
        """Should return list of default template codes."""
        codes = get_default_template_codes()
        assert len(codes) > 0
        assert "MOQ-001" in codes
        assert "LT-001" in codes
        assert "PT-001" in codes
    
    def test_default_templates_have_all_categories(self, service: ConditionsLibraryService):
        """Default templates should cover multiple categories."""
        templates = service.list_templates()
        categories = {t.category for t in templates}
        
        assert ConditionCategory.MOQ in categories
        assert ConditionCategory.LEAD_TIME in categories
        assert ConditionCategory.PAYMENT_TERMS in categories
        assert ConditionCategory.COMPLIANCE in categories
    
    def test_default_condition_sets_loaded(self, service: ConditionsLibraryService):
        """Service should have default condition sets loaded."""
        sets = service.list_condition_sets()
        assert len(sets) > 0
        
        # All should be defaults
        assert all(s.is_default for s in sets)
    
    def test_get_default_condition_set_ids(self):
        """Should return IDs of default condition sets."""
        ids = get_default_condition_set_ids()
        assert len(ids) > 0


# ============================================================================
# Template CRUD Tests
# ============================================================================

class TestTemplateCRUD:
    """Tests for template CRUD operations."""
    
    def test_create_template(self, service: ConditionsLibraryService, user_id):
        """Should create a new template."""
        template = service.create_template(
            code="CUSTOM-001",
            name="Custom Condition",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="Custom text: {{value}}.",
            placeholders=[
                Placeholder(
                    name="value",
                    display_label="Value",
                    placeholder_type=PlaceholderType.TEXT,
                ),
            ],
            description="A custom condition",
            created_by_id=user_id,
        )
        
        assert template.id is not None
        assert template.code == "CUSTOM-001"
        assert template.name == "Custom Condition"
        assert template.is_default is False
        assert template.version == 1
    
    def test_create_template_duplicate_code(self, service: ConditionsLibraryService):
        """Should reject duplicate template codes."""
        service.create_template(
            code="DUP-001",
            name="First",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="First template",
        )
        
        with pytest.raises(ValueError, match="already exists"):
            service.create_template(
                code="DUP-001",
                name="Second",
                category=ConditionCategory.CUSTOM,
                condition_type=ConditionType.STANDARD,
                scope=ConditionScope.QUOTE,
                template_text="Second template",
            )
    
    def test_create_template_missing_placeholder(self, service: ConditionsLibraryService):
        """Should validate placeholder exists in template text."""
        with pytest.raises(ValueError, match="not found in template"):
            service.create_template(
                code="BAD-001",
                name="Bad Template",
                category=ConditionCategory.CUSTOM,
                condition_type=ConditionType.STANDARD,
                scope=ConditionScope.QUOTE,
                template_text="No placeholder here",
                placeholders=[
                    Placeholder(
                        name="missing",
                        display_label="Missing",
                        placeholder_type=PlaceholderType.TEXT,
                    ),
                ],
            )
    
    def test_get_template(self, service: ConditionsLibraryService):
        """Should retrieve template by ID."""
        template = service.create_template(
            code="GET-001",
            name="Get Test",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="Test template",
        )
        
        retrieved = service.get_template(template.id)
        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.code == "GET-001"
    
    def test_get_template_not_found(self, service: ConditionsLibraryService):
        """Should return None for unknown ID."""
        result = service.get_template(uuid4())
        assert result is None
    
    def test_get_template_by_code(self, service: ConditionsLibraryService):
        """Should retrieve template by code."""
        template = service.get_template_by_code("MOQ-001")
        assert template is not None
        assert template.code == "MOQ-001"
    
    def test_get_template_by_code_not_found(self, service: ConditionsLibraryService):
        """Should return None for unknown code."""
        result = service.get_template_by_code("UNKNOWN-999")
        assert result is None
    
    def test_update_template(self, service: ConditionsLibraryService):
        """Should update template."""
        template = service.create_template(
            code="UPD-001",
            name="Original",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="Original text",
        )
        
        updated = service.update_template(
            template.id,
            name="Updated",
            template_text="Updated text",
        )
        
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.template_text == "Updated text"
        assert updated.version == 2
    
    def test_update_default_template_rejected(self, service: ConditionsLibraryService):
        """Should not allow updating default templates."""
        template = service.get_template_by_code("MOQ-001")
        
        with pytest.raises(ValueError, match="Cannot modify default"):
            service.update_template(template.id, name="Modified")
    
    def test_delete_template(self, service: ConditionsLibraryService):
        """Should delete template."""
        template = service.create_template(
            code="DEL-001",
            name="Delete Me",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="To be deleted",
        )
        
        result = service.delete_template(template.id)
        assert result is True
        
        assert service.get_template(template.id) is None
        assert service.get_template_by_code("DEL-001") is None
    
    def test_delete_default_template_rejected(self, service: ConditionsLibraryService):
        """Should not allow deleting default templates."""
        template = service.get_template_by_code("MOQ-001")
        
        with pytest.raises(ValueError, match="Cannot delete default"):
            service.delete_template(template.id)
    
    def test_delete_template_in_use(self, service: ConditionsLibraryService, entity_id):
        """Should not allow deleting templates in use."""
        template = service.create_template(
            code="INUSE-001",
            name="In Use",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="In use template",
        )
        
        # Apply the condition
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            template_id=template.id,
        )
        
        with pytest.raises(ValueError, match="in use"):
            service.delete_template(template.id)


# ============================================================================
# Template Listing Tests
# ============================================================================

class TestTemplateListing:
    """Tests for template listing and filtering."""
    
    def test_list_all_templates(self, service: ConditionsLibraryService):
        """Should list all templates."""
        templates = service.list_templates()
        assert len(templates) > 0
    
    def test_list_templates_by_category(self, service: ConditionsLibraryService):
        """Should filter templates by category."""
        templates = service.list_templates(category=ConditionCategory.MOQ)
        assert len(templates) > 0
        assert all(t.category == ConditionCategory.MOQ for t in templates)
    
    def test_list_templates_by_condition_type(self, service: ConditionsLibraryService):
        """Should filter templates by condition type."""
        templates = service.list_templates(condition_type=ConditionType.HARD_STOP)
        assert len(templates) > 0
        assert all(t.condition_type == ConditionType.HARD_STOP for t in templates)
    
    def test_list_templates_by_scope(self, service: ConditionsLibraryService):
        """Should filter templates by scope."""
        templates = service.list_templates(scope=ConditionScope.QUOTE)
        # Should include QUOTE and UNIVERSAL scopes
        for t in templates:
            assert t.scope in (ConditionScope.QUOTE, ConditionScope.UNIVERSAL)
    
    def test_list_templates_active_only(self, service: ConditionsLibraryService):
        """Should filter by active status."""
        # Create an inactive template
        template = service.create_template(
            code="INACTIVE-001",
            name="Inactive",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="Inactive",
        )
        service.update_template(template.id, is_active=False)
        
        active = service.list_templates(is_active=True)
        assert all(t.is_active for t in active)
        
        inactive = service.list_templates(is_active=False)
        assert any(t.code == "INACTIVE-001" for t in inactive)
    
    def test_list_templates_exclude_defaults(self, service: ConditionsLibraryService):
        """Should be able to exclude default templates."""
        service.create_template(
            code="NONDEFAULT-001",
            name="Non-default",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="Non-default",
        )
        
        templates = service.list_templates(include_defaults=False)
        assert all(not t.is_default for t in templates)
    
    def test_list_templates_search(self, service: ConditionsLibraryService):
        """Should search templates by name/code/description."""
        templates = service.list_templates(search="warranty")
        assert len(templates) > 0
        # Should find warranty-related template
        assert any("warranty" in t.name.lower() or "warranty" in t.code.lower() for t in templates)
    
    def test_get_templates_by_category(self, service: ConditionsLibraryService):
        """Should get all templates for a category."""
        templates = service.get_templates_by_category(ConditionCategory.PAYMENT_TERMS)
        assert len(templates) > 0
        assert all(t.category == ConditionCategory.PAYMENT_TERMS for t in templates)


# ============================================================================
# Template Rendering Tests
# ============================================================================

class TestTemplateRendering:
    """Tests for template rendering with placeholders."""
    
    def test_render_simple_placeholder(self, service: ConditionsLibraryService):
        """Should render template with simple placeholder."""
        template = service.get_template_by_code("MOQ-001")
        
        text = service.render_template(template, {"quantity": 100})
        assert "100" in text
        assert "{{quantity}}" not in text
    
    def test_render_multiple_placeholders(self, service: ConditionsLibraryService):
        """Should render template with multiple placeholders."""
        template = service.get_template_by_code("NRE-001")
        
        text = service.render_template(template, {
            "currency": "USD",
            "amount": 5000,
        })
        
        assert "USD" in text
        assert "5000" in text
    
    def test_render_with_default_value(self, service: ConditionsLibraryService):
        """Should use default value when placeholder not provided."""
        template = service.get_template_by_code("PV-001")
        
        # The default validity is 30 days
        text = service.render_template(template, {})
        assert "30" in text
    
    def test_render_missing_required_placeholder(self, service: ConditionsLibraryService):
        """Should raise error for missing required placeholder."""
        template = service.get_template_by_code("MOQ-001")
        
        with pytest.raises(ValueError, match="not provided"):
            service.render_template(template, {})
    
    def test_render_validates_number_min(self, service: ConditionsLibraryService):
        """Should validate number minimum value."""
        template = service.get_template_by_code("MOQ-001")
        
        with pytest.raises(ValueError, match="at least"):
            service.render_template(template, {"quantity": 0})
    
    def test_render_validates_number_max(self, service: ConditionsLibraryService):
        """Should validate number maximum value."""
        template = service.get_template_by_code("LT-001")
        
        with pytest.raises(ValueError, match="at most"):
            service.render_template(template, {"weeks": 100})
    
    def test_render_validates_select_options(self, service: ConditionsLibraryService):
        """Should validate select options."""
        template = service.get_template_by_code("NRE-001")
        
        with pytest.raises(ValueError, match="must be one of"):
            service.render_template(template, {
                "currency": "INVALID",
                "amount": 100,
            })
    
    def test_render_with_translation(self, service: ConditionsLibraryService):
        """Should use translation when available."""
        # Create template with translation
        template = service.create_template(
            code="TRANS-001",
            name="Translation Test",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="English: {{value}}",
            placeholders=[
                Placeholder(
                    name="value",
                    display_label="Value",
                    placeholder_type=PlaceholderType.TEXT,
                ),
            ],
            translations={"fr": "Français: {{value}}"},
        )
        
        # English
        en_text = service.render_template(template, {"value": "test"}, language="en")
        assert en_text == "English: test"
        
        # French
        fr_text = service.render_template(template, {"value": "test"}, language="fr")
        assert fr_text == "Français: test"


# ============================================================================
# Condition Application Tests
# ============================================================================

class TestConditionApplication:
    """Tests for applying conditions to entities."""
    
    def test_apply_condition_from_template(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should apply condition from template."""
        template = service.get_template_by_code("MOQ-001")
        
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            template_id=template.id,
            placeholder_values={"quantity": 500},
            applied_by_id=user_id,
        )
        
        assert applied.id is not None
        assert applied.template_id == template.id
        assert "500" in applied.condition_text
        assert applied.category == ConditionCategory.MOQ
    
    def test_apply_custom_condition(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should apply custom text condition."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Custom condition text",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            applied_by_id=user_id,
        )
        
        assert applied.template_id is None
        assert applied.condition_text == "Custom condition text"
    
    def test_apply_condition_requires_template_or_text(self, service: ConditionsLibraryService, entity_id):
        """Should require either template_id or custom_text."""
        with pytest.raises(ValueError, match="Either template_id or custom_text"):
            service.apply_condition(
                entity_type="quote",
                entity_id=entity_id,
            )
    
    def test_get_conditions_for_entity(self, service: ConditionsLibraryService, entity_id):
        """Should retrieve all conditions for an entity."""
        # Apply multiple conditions
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="First condition",
            sort_order=0,
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Second condition",
            sort_order=1,
        )
        
        conditions = service.get_conditions_for_entity("quote", entity_id)
        assert len(conditions) == 2
        assert conditions[0].condition_text == "First condition"
        assert conditions[1].condition_text == "Second condition"
    
    def test_get_conditions_filter_by_category(self, service: ConditionsLibraryService, entity_id):
        """Should filter conditions by category."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="MOQ condition",
            category=ConditionCategory.MOQ,
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Lead time condition",
            category=ConditionCategory.LEAD_TIME,
        )
        
        moq_conditions = service.get_conditions_for_entity(
            "quote", entity_id, category=ConditionCategory.MOQ
        )
        assert len(moq_conditions) == 1
    
    def test_get_conditions_filter_by_type(self, service: ConditionsLibraryService, entity_id):
        """Should filter conditions by type."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Standard condition",
            condition_type=ConditionType.STANDARD,
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Warning condition",
            condition_type=ConditionType.WARNING,
        )
        
        warnings = service.get_conditions_for_entity(
            "quote", entity_id, condition_type=ConditionType.WARNING
        )
        assert len(warnings) == 1
    
    def test_remove_condition(self, service: ConditionsLibraryService, entity_id):
        """Should remove an applied condition."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="To be removed",
        )
        
        result = service.remove_condition(applied.id)
        assert result is True
        
        conditions = service.get_conditions_for_entity("quote", entity_id)
        assert len(conditions) == 0
    
    def test_update_condition_text(self, service: ConditionsLibraryService, entity_id):
        """Should update condition text."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Original text",
        )
        
        updated = service.update_condition_text(applied.id, "Updated text")
        assert updated.condition_text == "Updated text"
    
    def test_reorder_conditions(self, service: ConditionsLibraryService, entity_id):
        """Should reorder conditions."""
        c1 = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="First",
            sort_order=0,
        )
        c2 = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Second",
            sort_order=1,
        )
        
        # Reorder - put second first
        service.reorder_conditions("quote", entity_id, [c2.id, c1.id])
        
        conditions = service.get_conditions_for_entity("quote", entity_id)
        assert conditions[0].condition_text == "Second"
        assert conditions[1].condition_text == "First"


# ============================================================================
# Hard Stop and Warning Tests
# ============================================================================

class TestHardStopsAndWarnings:
    """Tests for hard stop and warning handling."""
    
    def test_get_hard_stops(self, service: ConditionsLibraryService, entity_id):
        """Should get unresolved hard stops."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Hard stop",
            condition_type=ConditionType.HARD_STOP,
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Standard",
            condition_type=ConditionType.STANDARD,
        )
        
        hard_stops = service.get_hard_stops_for_entity("quote", entity_id)
        assert len(hard_stops) == 1
        assert hard_stops[0].condition_text == "Hard stop"
    
    def test_has_unresolved_hard_stops(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should check for unresolved hard stops."""
        # No hard stops initially
        assert service.has_unresolved_hard_stops("quote", entity_id) is False
        
        # Add hard stop
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Blocking issue",
            condition_type=ConditionType.HARD_STOP,
        )
        
        assert service.has_unresolved_hard_stops("quote", entity_id) is True
        
        # Resolve it
        service.resolve_hard_stop(applied.id, user_id, "Issue resolved")
        
        assert service.has_unresolved_hard_stops("quote", entity_id) is False
    
    def test_resolve_hard_stop(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should resolve a hard stop."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Blocking",
            condition_type=ConditionType.HARD_STOP,
        )
        
        resolved = service.resolve_hard_stop(
            applied.id, user_id, "Fixed the issue"
        )
        
        assert resolved.is_resolved is True
        assert resolved.resolved_by_id == user_id
        assert resolved.resolution_notes == "Fixed the issue"
        assert resolved.resolved_at is not None
    
    def test_resolve_non_hard_stop_rejected(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should not allow resolving non-hard-stop conditions."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Warning",
            condition_type=ConditionType.WARNING,
        )
        
        with pytest.raises(ValueError, match="HARD_STOP"):
            service.resolve_hard_stop(applied.id, user_id)
    
    def test_acknowledge_warning(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should acknowledge a warning."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Warning",
            condition_type=ConditionType.WARNING,
        )
        
        acknowledged = service.acknowledge_condition(applied.id, user_id)
        
        assert acknowledged.is_acknowledged is True
        assert acknowledged.acknowledged_by_id == user_id
        assert acknowledged.acknowledged_at is not None
    
    def test_acknowledge_non_warning_rejected(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should not allow acknowledging non-warning conditions."""
        applied = service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Standard",
            condition_type=ConditionType.STANDARD,
        )
        
        with pytest.raises(ValueError, match="WARNING"):
            service.acknowledge_condition(applied.id, user_id)


# ============================================================================
# Condition Set Tests
# ============================================================================

class TestConditionSets:
    """Tests for condition sets."""
    
    def test_create_condition_set(self, service: ConditionsLibraryService, user_id):
        """Should create a condition set."""
        # Get some template IDs
        moq = service.get_template_by_code("MOQ-001")
        lt = service.get_template_by_code("LT-001")
        
        condition_set = service.create_condition_set(
            name="Custom Set",
            condition_template_ids=[moq.id, lt.id],
            description="A custom set",
            created_by_id=user_id,
        )
        
        assert condition_set.id is not None
        assert condition_set.name == "Custom Set"
        assert len(condition_set.condition_template_ids) == 2
        assert condition_set.is_default is False
    
    def test_create_condition_set_invalid_template(self, service: ConditionsLibraryService):
        """Should reject sets with invalid template IDs."""
        with pytest.raises(ValueError, match="not found"):
            service.create_condition_set(
                name="Bad Set",
                condition_template_ids=[uuid4()],
            )
    
    def test_get_condition_set(self, service: ConditionsLibraryService):
        """Should retrieve condition set by ID."""
        sets = service.list_condition_sets()
        if sets:
            retrieved = service.get_condition_set(sets[0].id)
            assert retrieved is not None
            assert retrieved.id == sets[0].id
    
    def test_update_condition_set(self, service: ConditionsLibraryService):
        """Should update condition set."""
        moq = service.get_template_by_code("MOQ-001")
        
        condition_set = service.create_condition_set(
            name="Original Name",
            condition_template_ids=[moq.id],
        )
        
        updated = service.update_condition_set(
            condition_set.id,
            name="Updated Name",
            description="Updated description",
        )
        
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
    
    def test_update_default_set_rejected(self, service: ConditionsLibraryService):
        """Should not allow updating default sets."""
        sets = service.list_condition_sets()
        default_set = next((s for s in sets if s.is_default), None)
        
        if default_set:
            with pytest.raises(ValueError, match="Cannot modify default"):
                service.update_condition_set(default_set.id, name="Modified")
    
    def test_delete_condition_set(self, service: ConditionsLibraryService):
        """Should delete condition set."""
        moq = service.get_template_by_code("MOQ-001")
        
        condition_set = service.create_condition_set(
            name="To Delete",
            condition_template_ids=[moq.id],
        )
        
        result = service.delete_condition_set(condition_set.id)
        assert result is True
        
        assert service.get_condition_set(condition_set.id) is None
    
    def test_delete_default_set_rejected(self, service: ConditionsLibraryService):
        """Should not allow deleting default sets."""
        sets = service.list_condition_sets()
        default_set = next((s for s in sets if s.is_default), None)
        
        if default_set:
            with pytest.raises(ValueError, match="Cannot delete default"):
                service.delete_condition_set(default_set.id)
    
    def test_list_condition_sets(self, service: ConditionsLibraryService):
        """Should list condition sets."""
        sets = service.list_condition_sets()
        assert len(sets) > 0
    
    def test_apply_condition_set(self, service: ConditionsLibraryService, entity_id, user_id):
        """Should apply all conditions from a set."""
        # Create a set with templates that don't require placeholders
        comp1 = service.get_template_by_code("COMP-001")  # RoHS
        comp2 = service.get_template_by_code("COMP-002")  # REACH
        
        condition_set = service.create_condition_set(
            name="Compliance Set",
            condition_template_ids=[comp1.id, comp2.id],
        )
        
        applied = service.apply_condition_set(
            condition_set.id,
            entity_type="quote",
            entity_id=entity_id,
            applied_by_id=user_id,
        )
        
        assert len(applied) == 2
        
        # Verify conditions were applied
        conditions = service.get_conditions_for_entity("quote", entity_id)
        assert len(conditions) == 2
    
    def test_apply_condition_set_with_placeholders(self, service: ConditionsLibraryService, entity_id):
        """Should apply set with placeholder values."""
        moq = service.get_template_by_code("MOQ-001")
        lt = service.get_template_by_code("LT-001")
        
        condition_set = service.create_condition_set(
            name="Test Set",
            condition_template_ids=[moq.id, lt.id],
        )
        
        applied = service.apply_condition_set(
            condition_set.id,
            entity_type="quote",
            entity_id=entity_id,
            placeholder_values_map={
                "MOQ-001": {"quantity": 1000},
                "LT-001": {"weeks": 6},
            },
        )
        
        assert len(applied) == 2
        assert "1000" in applied[0].condition_text
        assert "6" in applied[1].condition_text


# ============================================================================
# Bulk Operations Tests
# ============================================================================

class TestBulkOperations:
    """Tests for bulk operations."""
    
    def test_copy_conditions(self, service: ConditionsLibraryService, user_id):
        """Should copy conditions between entities."""
        source_id = uuid4()
        target_id = uuid4()
        
        # Apply conditions to source
        service.apply_condition(
            entity_type="quote",
            entity_id=source_id,
            custom_text="Condition 1",
            sort_order=0,
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=source_id,
            custom_text="Condition 2",
            sort_order=1,
        )
        
        # Copy to target
        copied = service.copy_conditions(
            source_entity_type="quote",
            source_entity_id=source_id,
            target_entity_type="quote",
            target_entity_id=target_id,
            applied_by_id=user_id,
        )
        
        assert len(copied) == 2
        
        # Verify target has conditions
        target_conditions = service.get_conditions_for_entity("quote", target_id)
        assert len(target_conditions) == 2
    
    def test_clear_conditions(self, service: ConditionsLibraryService, entity_id):
        """Should clear all conditions from entity."""
        # Apply conditions
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Condition 1",
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Condition 2",
        )
        
        # Clear
        count = service.clear_conditions("quote", entity_id)
        assert count == 2
        
        # Verify cleared
        conditions = service.get_conditions_for_entity("quote", entity_id)
        assert len(conditions) == 0


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidation:
    """Tests for entity validation."""
    
    def test_validate_entity_clean(self, service: ConditionsLibraryService, entity_id):
        """Should validate clean entity."""
        # Apply only standard conditions
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Standard",
            condition_type=ConditionType.STANDARD,
        )
        
        result = service.validate_entity("quote", entity_id)
        
        assert result["can_proceed"] is True
        assert result["requires_acknowledgment"] is False
        assert result["unresolved_hard_stops"] == 0
    
    def test_validate_entity_with_hard_stop(self, service: ConditionsLibraryService, entity_id):
        """Should detect unresolved hard stops."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Blocking issue",
            condition_type=ConditionType.HARD_STOP,
        )
        
        result = service.validate_entity("quote", entity_id)
        
        assert result["can_proceed"] is False
        assert result["unresolved_hard_stops"] == 1
        assert len(result["issues"]) == 1
    
    def test_validate_entity_with_unacknowledged_warning(self, service: ConditionsLibraryService, entity_id):
        """Should detect unacknowledged warnings."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Warning",
            condition_type=ConditionType.WARNING,
        )
        
        result = service.validate_entity("quote", entity_id)
        
        assert result["can_proceed"] is True  # Warnings don't block
        assert result["requires_acknowledgment"] is True
        assert result["unacknowledged_warnings"] == 1


# ============================================================================
# Export Tests
# ============================================================================

class TestExport:
    """Tests for condition export."""
    
    def test_export_as_text(self, service: ConditionsLibraryService, entity_id):
        """Should export conditions as text."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Standard condition",
            condition_type=ConditionType.STANDARD,
        )
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Warning condition",
            condition_type=ConditionType.WARNING,
        )
        
        text = service.export_conditions("quote", entity_id, format="text")
        
        assert "Standard condition" in text
        assert "[WARNING] Warning condition" in text
    
    def test_export_as_json(self, service: ConditionsLibraryService, entity_id):
        """Should export conditions as JSON-serializable list."""
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Test condition",
        )
        
        data = service.export_conditions("quote", entity_id, format="json")
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["text"] == "Test condition"


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Tests for statistics."""
    
    def test_template_usage_stats(self, service: ConditionsLibraryService):
        """Should track template usage."""
        moq = service.get_template_by_code("MOQ-001")
        
        # Apply condition twice from same template
        for _ in range(2):
            service.apply_condition(
                entity_type="quote",
                entity_id=uuid4(),
                template_id=moq.id,
                placeholder_values={"quantity": 100},
            )
        
        stats = service.get_template_usage_stats()
        assert stats[moq.id] == 2
    
    def test_category_stats(self, service: ConditionsLibraryService):
        """Should track conditions by category."""
        for _ in range(3):
            service.apply_condition(
                entity_type="quote",
                entity_id=uuid4(),
                custom_text="MOQ",
                category=ConditionCategory.MOQ,
            )
        
        stats = service.get_category_stats()
        assert stats[ConditionCategory.MOQ] == 3


# ============================================================================
# Module-Level Function Tests
# ============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""
    
    def test_get_conditions_library_service(self):
        """Should return singleton service instance."""
        service1 = get_conditions_library_service()
        service2 = get_conditions_library_service()
        
        # Both should have templates
        assert len(service1.list_templates()) > 0
        assert len(service2.list_templates()) > 0
    
    def test_get_default_template_codes(self):
        """Should return all default template codes."""
        codes = get_default_template_codes()
        
        assert "MOQ-001" in codes
        assert "MOQ-002" in codes
        assert "LT-001" in codes
        assert "LT-002" in codes
        assert "PT-001" in codes
        assert "NRE-001" in codes
    
    def test_get_default_condition_set_ids(self):
        """Should return all default condition set IDs."""
        ids = get_default_condition_set_ids()
        
        assert len(ids) >= 3  # Standard, New Customer, Compliance


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_apply_condition_to_different_entity_types(self, service: ConditionsLibraryService):
        """Should track conditions separately by entity type."""
        entity_id = uuid4()
        
        service.apply_condition(
            entity_type="quote",
            entity_id=entity_id,
            custom_text="Quote condition",
        )
        service.apply_condition(
            entity_type="qualification",
            entity_id=entity_id,
            custom_text="Qualification condition",
        )
        
        quote_conditions = service.get_conditions_for_entity("quote", entity_id)
        qual_conditions = service.get_conditions_for_entity("qualification", entity_id)
        
        assert len(quote_conditions) == 1
        assert len(qual_conditions) == 1
        assert quote_conditions[0].condition_text != qual_conditions[0].condition_text
    
    def test_condition_with_all_placeholder_types(self, service: ConditionsLibraryService):
        """Should handle all placeholder types."""
        template = service.create_template(
            code="FULL-001",
            name="Full Placeholder Test",
            category=ConditionCategory.CUSTOM,
            condition_type=ConditionType.STANDARD,
            scope=ConditionScope.QUOTE,
            template_text="{{num}} units, {{text}} comment, {{pct}}% rate",
            placeholders=[
                Placeholder(
                    name="num",
                    display_label="Number",
                    placeholder_type=PlaceholderType.NUMBER,
                ),
                Placeholder(
                    name="text",
                    display_label="Text",
                    placeholder_type=PlaceholderType.TEXT,
                ),
                Placeholder(
                    name="pct",
                    display_label="Percentage",
                    placeholder_type=PlaceholderType.PERCENTAGE,
                ),
            ],
        )
        
        text = service.render_template(template, {
            "num": 100,
            "text": "test",
            "pct": 50,
        })
        
        assert "100 units" in text
        assert "test comment" in text
        assert "50% rate" in text
    
    def test_get_applied_condition_not_found(self, service: ConditionsLibraryService):
        """Should return None for unknown applied condition."""
        result = service.get_applied_condition(uuid4())
        assert result is None
    
    def test_remove_nonexistent_condition(self, service: ConditionsLibraryService):
        """Should return False when removing nonexistent condition."""
        result = service.remove_condition(uuid4())
        assert result is False
    
    def test_delete_nonexistent_template(self, service: ConditionsLibraryService):
        """Should return False when deleting nonexistent template."""
        result = service.delete_template(uuid4())
        assert result is False
    
    def test_update_nonexistent_template(self, service: ConditionsLibraryService):
        """Should return None when updating nonexistent template."""
        result = service.update_template(uuid4(), name="New Name")
        assert result is None
    
    def test_template_not_found_in_apply(self, service: ConditionsLibraryService, entity_id):
        """Should error when template not found."""
        with pytest.raises(ValueError, match="not found"):
            service.apply_condition(
                entity_type="quote",
                entity_id=entity_id,
                template_id=uuid4(),
            )
    
    def test_condition_set_not_found_in_apply(self, service: ConditionsLibraryService, entity_id):
        """Should error when condition set not found."""
        with pytest.raises(ValueError, match="not found"):
            service.apply_condition_set(
                uuid4(),
                entity_type="quote",
                entity_id=entity_id,
            )

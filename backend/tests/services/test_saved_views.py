"""
Tests for Saved Views/Filters Service.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sensei.services.saved_views import (
    SavedViewsService,
    SavedView,
    SavedViewEntityType,
    FilterCondition,
    FilterOperator,
    FilterLogic,
    DatePreset,
    SortField,
    SortDirection,
    ColumnConfig,
    ViewVisibility,
    ViewFilterResult,
    build_filter_condition,
    build_sort_field,
    build_column_config,
)


# --------------------------------------------------------------------------
# Enum Tests
# --------------------------------------------------------------------------

class TestEnums:
    """Tests for enum values."""
    
    def test_saved_view_entity_type_values(self):
        """Test SavedViewEntityType enum values."""
        assert SavedViewEntityType.ACCOUNT.value == "account"
        assert SavedViewEntityType.RFQ.value == "rfq"
        assert SavedViewEntityType.QUOTE.value == "quote"
        assert SavedViewEntityType.TASK.value == "task"
        assert SavedViewEntityType.A3.value == "a3"
    
    def test_filter_operator_values(self):
        """Test FilterOperator enum values."""
        assert FilterOperator.EQUALS.value == "equals"
        assert FilterOperator.CONTAINS.value == "contains"
        assert FilterOperator.GREATER_THAN.value == "greater_than"
        assert FilterOperator.OVERDUE.value == "overdue"
        assert FilterOperator.WITHIN_DAYS.value == "within_days"
    
    def test_filter_logic_values(self):
        """Test FilterLogic enum values."""
        assert FilterLogic.AND.value == "and"
        assert FilterLogic.OR.value == "or"
    
    def test_date_preset_values(self):
        """Test DatePreset enum values."""
        assert DatePreset.TODAY.value == "today"
        assert DatePreset.THIS_WEEK.value == "this_week"
        assert DatePreset.LAST_30_DAYS.value == "last_30_days"
        assert DatePreset.NEXT_7_DAYS.value == "next_7_days"
    
    def test_view_visibility_values(self):
        """Test ViewVisibility enum values."""
        assert ViewVisibility.PRIVATE.value == "private"
        assert ViewVisibility.TEAM.value == "team"
        assert ViewVisibility.ORGANIZATION.value == "organization"
        assert ViewVisibility.PUBLIC.value == "public"


# --------------------------------------------------------------------------
# Filter Condition Tests
# --------------------------------------------------------------------------

class TestFilterCondition:
    """Tests for FilterCondition."""
    
    def test_equals_operator(self):
        """Test EQUALS operator."""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.EQUALS,
            value="active",
        )
        
        assert condition.evaluate({"status": "active"}) is True
        assert condition.evaluate({"status": "Active"}) is True  # Case insensitive
        assert condition.evaluate({"status": "inactive"}) is False
        assert condition.evaluate({"status": None}) is False
    
    def test_equals_operator_case_sensitive(self):
        """Test EQUALS with case sensitivity."""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.EQUALS,
            value="Active",
            case_sensitive=True,
        )
        
        assert condition.evaluate({"status": "Active"}) is True
        assert condition.evaluate({"status": "active"}) is False
    
    def test_not_equals_operator(self):
        """Test NOT_EQUALS operator."""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.NOT_EQUALS,
            value="cancelled",
        )
        
        assert condition.evaluate({"status": "active"}) is True
        assert condition.evaluate({"status": "cancelled"}) is False
    
    def test_contains_operator(self):
        """Test CONTAINS operator."""
        condition = FilterCondition(
            field="name",
            operator=FilterOperator.CONTAINS,
            value="corp",
        )
        
        assert condition.evaluate({"name": "Acme Corporation"}) is True
        assert condition.evaluate({"name": "ACME CORP"}) is True
        assert condition.evaluate({"name": "Acme Inc"}) is False
    
    def test_not_contains_operator(self):
        """Test NOT_CONTAINS operator."""
        condition = FilterCondition(
            field="name",
            operator=FilterOperator.NOT_CONTAINS,
            value="test",
        )
        
        assert condition.evaluate({"name": "Production"}) is True
        assert condition.evaluate({"name": "Test Account"}) is False
    
    def test_starts_with_operator(self):
        """Test STARTS_WITH operator."""
        condition = FilterCondition(
            field="code",
            operator=FilterOperator.STARTS_WITH,
            value="RFQ-",
        )
        
        assert condition.evaluate({"code": "RFQ-2024-001"}) is True
        assert condition.evaluate({"code": "Q-2024-001"}) is False
    
    def test_ends_with_operator(self):
        """Test ENDS_WITH operator."""
        condition = FilterCondition(
            field="email",
            operator=FilterOperator.ENDS_WITH,
            value="@example.com",
        )
        
        assert condition.evaluate({"email": "user@example.com"}) is True
        assert condition.evaluate({"email": "user@other.com"}) is False
    
    def test_greater_than_operator(self):
        """Test GREATER_THAN operator."""
        condition = FilterCondition(
            field="amount",
            operator=FilterOperator.GREATER_THAN,
            value=1000,
        )
        
        assert condition.evaluate({"amount": 1500}) is True
        assert condition.evaluate({"amount": 1000}) is False
        assert condition.evaluate({"amount": 500}) is False
    
    def test_greater_than_or_equal_operator(self):
        """Test GREATER_THAN_OR_EQUAL operator."""
        condition = FilterCondition(
            field="amount",
            operator=FilterOperator.GREATER_THAN_OR_EQUAL,
            value=1000,
        )
        
        assert condition.evaluate({"amount": 1500}) is True
        assert condition.evaluate({"amount": 1000}) is True
        assert condition.evaluate({"amount": 500}) is False
    
    def test_less_than_operator(self):
        """Test LESS_THAN operator."""
        condition = FilterCondition(
            field="score",
            operator=FilterOperator.LESS_THAN,
            value=80,
        )
        
        assert condition.evaluate({"score": 70}) is True
        assert condition.evaluate({"score": 80}) is False
        assert condition.evaluate({"score": 90}) is False
    
    def test_less_than_or_equal_operator(self):
        """Test LESS_THAN_OR_EQUAL operator."""
        condition = FilterCondition(
            field="score",
            operator=FilterOperator.LESS_THAN_OR_EQUAL,
            value=80,
        )
        
        assert condition.evaluate({"score": 70}) is True
        assert condition.evaluate({"score": 80}) is True
        assert condition.evaluate({"score": 90}) is False
    
    def test_in_operator(self):
        """Test IN operator."""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.IN,
            value=["active", "pending", "review"],
        )
        
        assert condition.evaluate({"status": "active"}) is True
        assert condition.evaluate({"status": "pending"}) is True
        assert condition.evaluate({"status": "cancelled"}) is False
    
    def test_not_in_operator(self):
        """Test NOT_IN operator."""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.NOT_IN,
            value=["completed", "cancelled"],
        )
        
        assert condition.evaluate({"status": "active"}) is True
        assert condition.evaluate({"status": "cancelled"}) is False
    
    def test_is_null_operator(self):
        """Test IS_NULL operator."""
        condition = FilterCondition(
            field="assigned_to",
            operator=FilterOperator.IS_NULL,
        )
        
        assert condition.evaluate({"assigned_to": None}) is True
        assert condition.evaluate({}) is True
        assert condition.evaluate({"assigned_to": "user-1"}) is False
    
    def test_is_not_null_operator(self):
        """Test IS_NOT_NULL operator."""
        condition = FilterCondition(
            field="assigned_to",
            operator=FilterOperator.IS_NOT_NULL,
        )
        
        assert condition.evaluate({"assigned_to": "user-1"}) is True
        assert condition.evaluate({"assigned_to": None}) is False
        assert condition.evaluate({}) is False
    
    def test_between_operator(self):
        """Test BETWEEN operator."""
        condition = FilterCondition(
            field="amount",
            operator=FilterOperator.BETWEEN,
            value=100,
            second_value=500,
        )
        
        assert condition.evaluate({"amount": 300}) is True
        assert condition.evaluate({"amount": 100}) is True
        assert condition.evaluate({"amount": 500}) is True
        assert condition.evaluate({"amount": 50}) is False
        assert condition.evaluate({"amount": 600}) is False
    
    def test_overdue_operator(self):
        """Test OVERDUE operator."""
        condition = FilterCondition(
            field="due_date",
            operator=FilterOperator.OVERDUE,
        )
        
        past_date = datetime.now() - timedelta(days=1)
        future_date = datetime.now() + timedelta(days=1)
        
        assert condition.evaluate({"due_date": past_date}) is True
        assert condition.evaluate({"due_date": future_date}) is False
    
    def test_within_days_operator(self):
        """Test WITHIN_DAYS operator."""
        condition = FilterCondition(
            field="due_date",
            operator=FilterOperator.WITHIN_DAYS,
            value=7,
        )
        
        tomorrow = datetime.now() + timedelta(days=1)
        next_week = datetime.now() + timedelta(days=5)
        far_future = datetime.now() + timedelta(days=30)
        past = datetime.now() - timedelta(days=1)
        
        assert condition.evaluate({"due_date": tomorrow}) is True
        assert condition.evaluate({"due_date": next_week}) is True
        assert condition.evaluate({"due_date": far_future}) is False
        assert condition.evaluate({"due_date": past}) is False
    
    def test_nested_field_access(self):
        """Test accessing nested fields."""
        condition = FilterCondition(
            field="account.name",
            operator=FilterOperator.EQUALS,
            value="Acme",
        )
        
        assert condition.evaluate({"account": {"name": "Acme"}}) is True
        assert condition.evaluate({"account": {"name": "Other"}}) is False
        assert condition.evaluate({"account": None}) is False
    
    def test_null_field_handling(self):
        """Test handling of null/missing fields."""
        condition = FilterCondition(
            field="missing_field",
            operator=FilterOperator.EQUALS,
            value="test",
        )
        
        assert condition.evaluate({}) is False
        assert condition.evaluate({"missing_field": None}) is False


# --------------------------------------------------------------------------
# Date Preset Tests
# --------------------------------------------------------------------------

class TestDatePresets:
    """Tests for date preset resolution."""
    
    def test_today_preset(self):
        """Test TODAY preset."""
        condition = FilterCondition(
            field="date",
            operator=FilterOperator.BETWEEN,
            date_preset=DatePreset.TODAY,
        )
        
        today = datetime.now().replace(hour=12, minute=0, second=0)
        yesterday = datetime.now() - timedelta(days=1)
        
        # Get the resolved value
        resolved = condition._resolve_date_preset(DatePreset.TODAY)
        assert isinstance(resolved, tuple)
        assert len(resolved) == 2
    
    def test_this_week_preset(self):
        """Test THIS_WEEK preset."""
        condition = FilterCondition(
            field="date",
            operator=FilterOperator.BETWEEN,
            date_preset=DatePreset.THIS_WEEK,
        )
        
        resolved = condition._resolve_date_preset(DatePreset.THIS_WEEK)
        assert isinstance(resolved, tuple)
        # Should be a 7-day range
        start, end = resolved
        assert (end - start).days == 7
    
    def test_last_30_days_preset(self):
        """Test LAST_30_DAYS preset."""
        condition = FilterCondition(
            field="date",
            operator=FilterOperator.BETWEEN,
            date_preset=DatePreset.LAST_30_DAYS,
        )
        
        resolved = condition._resolve_date_preset(DatePreset.LAST_30_DAYS)
        assert isinstance(resolved, tuple)
        start, end = resolved
        # Should cover 31 days (30 days ago to tomorrow)
        assert (end - start).days == 31


# --------------------------------------------------------------------------
# Saved View Tests
# --------------------------------------------------------------------------

class TestSavedView:
    """Tests for SavedView."""
    
    def test_view_creation(self):
        """Test creating a saved view."""
        owner_id = uuid4()
        view = SavedView(
            id="view-1",
            name="My View",
            entity_type=SavedViewEntityType.TASK,
            owner_id=owner_id,
        )
        
        assert view.id == "view-1"
        assert view.name == "My View"
        assert view.entity_type == SavedViewEntityType.TASK
        assert view.owner_id == owner_id
        assert view.visibility == ViewVisibility.PRIVATE
    
    def test_view_matches_with_and_logic(self):
        """Test view matching with AND logic."""
        view = SavedView(
            id="view-1",
            name="Active High Priority",
            entity_type=SavedViewEntityType.TASK,
            owner_id=uuid4(),
            conditions=[
                FilterCondition(field="status", operator=FilterOperator.EQUALS, value="active"),
                FilterCondition(field="priority", operator=FilterOperator.EQUALS, value="high"),
            ],
            condition_logic=FilterLogic.AND,
        )
        
        # Both conditions match
        assert view.matches({"status": "active", "priority": "high"}) is True
        
        # Only one matches
        assert view.matches({"status": "active", "priority": "low"}) is False
        assert view.matches({"status": "inactive", "priority": "high"}) is False
    
    def test_view_matches_with_or_logic(self):
        """Test view matching with OR logic."""
        view = SavedView(
            id="view-1",
            name="High or Critical",
            entity_type=SavedViewEntityType.RISK,
            owner_id=uuid4(),
            conditions=[
                FilterCondition(field="severity", operator=FilterOperator.EQUALS, value="high"),
                FilterCondition(field="severity", operator=FilterOperator.EQUALS, value="critical"),
            ],
            condition_logic=FilterLogic.OR,
        )
        
        # Either matches
        assert view.matches({"severity": "high"}) is True
        assert view.matches({"severity": "critical"}) is True
        
        # Neither matches
        assert view.matches({"severity": "low"}) is False
    
    def test_view_matches_no_conditions(self):
        """Test view with no conditions matches everything."""
        view = SavedView(
            id="view-1",
            name="All Items",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=uuid4(),
        )
        
        assert view.matches({"name": "Anything"}) is True
        assert view.matches({}) is True
    
    def test_view_apply_sort(self):
        """Test applying sort to entities."""
        view = SavedView(
            id="view-1",
            name="Sorted View",
            entity_type=SavedViewEntityType.TASK,
            owner_id=uuid4(),
            sort_fields=[SortField(field="name", direction=SortDirection.ASC)],
        )
        
        entities = [
            {"name": "Charlie"},
            {"name": "Alpha"},
            {"name": "Beta"},
        ]
        
        sorted_entities = view.apply_sort(entities)
        
        assert sorted_entities[0]["name"] == "Alpha"
        assert sorted_entities[1]["name"] == "Beta"
        assert sorted_entities[2]["name"] == "Charlie"
    
    def test_view_apply_sort_desc(self):
        """Test applying descending sort."""
        view = SavedView(
            id="view-1",
            name="Sorted View",
            entity_type=SavedViewEntityType.TASK,
            owner_id=uuid4(),
            sort_fields=[SortField(field="amount", direction=SortDirection.DESC)],
        )
        
        entities = [
            {"amount": 100},
            {"amount": 300},
            {"amount": 200},
        ]
        
        sorted_entities = view.apply_sort(entities)
        
        assert sorted_entities[0]["amount"] == 300
        assert sorted_entities[1]["amount"] == 200
        assert sorted_entities[2]["amount"] == 100


# --------------------------------------------------------------------------
# Saved Views Service Tests
# --------------------------------------------------------------------------

class TestSavedViewsService:
    """Tests for SavedViewsService."""
    
    @pytest.fixture
    def service(self) -> SavedViewsService:
        """Create a service instance."""
        return SavedViewsService()
    
    @pytest.fixture
    def user_id(self) -> uuid4:
        """Create a test user ID."""
        return uuid4()
    
    def test_service_initialization(self, service: SavedViewsService):
        """Test service initialization with system views."""
        system_views = service.get_system_views()
        
        assert len(system_views) > 0
        # Check some expected system views exist
        view_ids = [v.id for v in system_views]
        assert "system-tasks-overdue" in view_ids
        assert "system-quotes-draft" in view_ids
        assert "system-rfqs-stale" in view_ids
    
    def test_get_system_views_by_entity_type(self, service: SavedViewsService):
        """Test filtering system views by entity type."""
        task_views = service.get_system_views(SavedViewEntityType.TASK)
        
        assert len(task_views) > 0
        for view in task_views:
            assert view.entity_type == SavedViewEntityType.TASK
    
    def test_create_view(self, service: SavedViewsService, user_id):
        """Test creating a view."""
        view = service.create_view(
            name="My Custom View",
            entity_type=SavedViewEntityType.QUOTE,
            owner_id=user_id,
            description="Custom filter for quotes",
        )
        
        assert view.id is not None
        assert view.name == "My Custom View"
        assert view.entity_type == SavedViewEntityType.QUOTE
        assert view.owner_id == user_id
        assert view.description == "Custom filter for quotes"
    
    def test_create_view_with_conditions(self, service: SavedViewsService, user_id):
        """Test creating a view with filter conditions."""
        view = service.create_view(
            name="High Value Quotes",
            entity_type=SavedViewEntityType.QUOTE,
            owner_id=user_id,
            conditions=[
                FilterCondition(
                    field="total_value",
                    operator=FilterOperator.GREATER_THAN,
                    value=50000,
                ),
            ],
        )
        
        assert len(view.conditions) == 1
        assert view.conditions[0].field == "total_value"
    
    def test_get_view(self, service: SavedViewsService, user_id):
        """Test getting a view by ID."""
        created = service.create_view(
            name="Test View",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=user_id,
        )
        
        retrieved = service.get_view(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
    
    def test_get_system_view(self, service: SavedViewsService):
        """Test getting a system view by ID."""
        view = service.get_view("system-tasks-overdue")
        
        assert view is not None
        assert view.name == "Overdue Tasks"
        assert view.visibility == ViewVisibility.PUBLIC
    
    def test_get_nonexistent_view(self, service: SavedViewsService):
        """Test getting a nonexistent view."""
        view = service.get_view("nonexistent")
        assert view is None
    
    def test_update_view(self, service: SavedViewsService, user_id):
        """Test updating a view."""
        view = service.create_view(
            name="Original Name",
            entity_type=SavedViewEntityType.TASK,
            owner_id=user_id,
        )
        
        updated = service.update_view(
            view_id=view.id,
            name="Updated Name",
            description="New description",
            icon="star",
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "New description"
        assert updated.icon == "star"
    
    def test_update_view_conditions(self, service: SavedViewsService, user_id):
        """Test updating view conditions."""
        view = service.create_view(
            name="Test View",
            entity_type=SavedViewEntityType.TASK,
            owner_id=user_id,
        )
        
        new_conditions = [
            FilterCondition(field="status", operator=FilterOperator.EQUALS, value="active"),
        ]
        
        updated = service.update_view(
            view_id=view.id,
            conditions=new_conditions,
        )
        
        assert len(updated.conditions) == 1
        assert updated.conditions[0].field == "status"
    
    def test_update_nonexistent_view(self, service: SavedViewsService):
        """Test updating a nonexistent view."""
        result = service.update_view(view_id="nonexistent", name="New Name")
        assert result is None
    
    def test_delete_view(self, service: SavedViewsService, user_id):
        """Test deleting a view."""
        view = service.create_view(
            name="To Delete",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=user_id,
        )
        
        result = service.delete_view(view.id)
        assert result is True
        
        # Verify deleted
        assert service.get_view(view.id) is None
    
    def test_delete_nonexistent_view(self, service: SavedViewsService):
        """Test deleting a nonexistent view."""
        result = service.delete_view("nonexistent")
        assert result is False
    
    def test_list_views_user_only(self, service: SavedViewsService, user_id):
        """Test listing user's own views."""
        other_user = uuid4()
        
        # Create views for different users
        service.create_view("My View", SavedViewEntityType.TASK, user_id)
        service.create_view("Other View", SavedViewEntityType.TASK, other_user)
        
        views = service.list_views(user_id, include_system=False)
        
        # Should only see own view
        user_views = [v for v in views if v.owner_id == user_id]
        assert len(user_views) == 1
        assert user_views[0].name == "My View"
    
    def test_list_views_with_system(self, service: SavedViewsService, user_id):
        """Test listing views including system views."""
        views = service.list_views(user_id, include_system=True)
        
        # Should include system views
        system_views = [v for v in views if v.visibility == ViewVisibility.PUBLIC]
        assert len(system_views) > 0
    
    def test_list_views_by_entity_type(self, service: SavedViewsService, user_id):
        """Test listing views filtered by entity type."""
        service.create_view("Task View", SavedViewEntityType.TASK, user_id)
        service.create_view("Quote View", SavedViewEntityType.QUOTE, user_id)
        
        task_views = service.list_views(
            user_id,
            entity_type=SavedViewEntityType.TASK,
            include_system=False,
        )
        
        for view in task_views:
            assert view.entity_type == SavedViewEntityType.TASK
    
    def test_list_views_organization_visibility(self, service: SavedViewsService, user_id):
        """Test listing organization-visible views."""
        other_user = uuid4()
        
        view = service.create_view(
            name="Org View",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=other_user,
            visibility=ViewVisibility.ORGANIZATION,
        )
        
        views = service.list_views(user_id, include_system=False, include_organization=True)
        
        org_view = next((v for v in views if v.id == view.id), None)
        assert org_view is not None
    
    def test_apply_view(self, service: SavedViewsService, user_id):
        """Test applying a view to filter entities."""
        view = service.create_view(
            name="Active Only",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=user_id,
            conditions=[
                FilterCondition(field="status", operator=FilterOperator.EQUALS, value="active"),
            ],
        )
        
        entities = [
            {"id": "1", "name": "Account 1", "status": "active"},
            {"id": "2", "name": "Account 2", "status": "inactive"},
            {"id": "3", "name": "Account 3", "status": "active"},
        ]
        
        result = service.apply_view(view.id, entities)
        
        assert result is not None
        assert result.total_count == 3
        assert result.matched_count == 2
        assert len(result.entities) == 2
    
    def test_apply_view_with_pagination(self, service: SavedViewsService, user_id):
        """Test applying a view with pagination."""
        view = service.create_view(
            name="All Items",
            entity_type=SavedViewEntityType.TASK,
            owner_id=user_id,
            page_size=2,
        )
        
        entities = [
            {"id": "1", "name": "Task 1"},
            {"id": "2", "name": "Task 2"},
            {"id": "3", "name": "Task 3"},
            {"id": "4", "name": "Task 4"},
        ]
        
        # Get first page
        result1 = service.apply_view(view.id, entities, page=1)
        assert len(result1.entities) == 2
        assert result1.has_more is True
        
        # Get second page
        result2 = service.apply_view(view.id, entities, page=2)
        assert len(result2.entities) == 2
        assert result2.has_more is False
    
    def test_apply_view_with_sorting(self, service: SavedViewsService, user_id):
        """Test applying a view with sorting."""
        view = service.create_view(
            name="Sorted View",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=user_id,
            sort_fields=[SortField(field="name", direction=SortDirection.ASC)],
        )
        
        entities = [
            {"id": "1", "name": "Zebra Corp"},
            {"id": "2", "name": "Alpha Inc"},
            {"id": "3", "name": "Beta LLC"},
        ]
        
        result = service.apply_view(view.id, entities)
        
        assert result.entities[0]["name"] == "Alpha Inc"
        assert result.entities[1]["name"] == "Beta LLC"
        assert result.entities[2]["name"] == "Zebra Corp"
    
    def test_apply_view_nonexistent(self, service: SavedViewsService):
        """Test applying a nonexistent view."""
        result = service.apply_view("nonexistent", [])
        assert result is None
    
    def test_apply_view_tracks_usage(self, service: SavedViewsService, user_id):
        """Test that applying a view tracks usage."""
        view = service.create_view(
            name="Usage Test",
            entity_type=SavedViewEntityType.TASK,
            owner_id=user_id,
        )
        
        initial_count = view.use_count
        
        service.apply_view(view.id, [{"name": "test"}])
        service.apply_view(view.id, [{"name": "test"}])
        
        updated_view = service.get_view(view.id)
        assert updated_view.use_count == initial_count + 2
        assert updated_view.last_used_at is not None
    
    def test_duplicate_view(self, service: SavedViewsService, user_id):
        """Test duplicating a view."""
        original = service.create_view(
            name="Original",
            entity_type=SavedViewEntityType.QUOTE,
            owner_id=user_id,
            conditions=[
                FilterCondition(field="status", operator=FilterOperator.EQUALS, value="draft"),
            ],
            description="Original description",
        )
        
        new_user = uuid4()
        duplicate = service.duplicate_view(original.id, new_user)
        
        assert duplicate is not None
        assert duplicate.id != original.id
        assert duplicate.name == "Copy of Original"
        assert duplicate.owner_id == new_user
        assert len(duplicate.conditions) == 1
        assert duplicate.visibility == ViewVisibility.PRIVATE
    
    def test_duplicate_view_custom_name(self, service: SavedViewsService, user_id):
        """Test duplicating with custom name."""
        original = service.create_view(
            name="Original",
            entity_type=SavedViewEntityType.TASK,
            owner_id=user_id,
        )
        
        new_user = uuid4()
        duplicate = service.duplicate_view(original.id, new_user, new_name="My Copy")
        
        assert duplicate.name == "My Copy"
    
    def test_set_default_view(self, service: SavedViewsService, user_id):
        """Test setting a default view."""
        view1 = service.create_view("View 1", SavedViewEntityType.TASK, user_id)
        view2 = service.create_view("View 2", SavedViewEntityType.TASK, user_id)
        
        # Set view1 as default
        result = service.set_default_view(user_id, SavedViewEntityType.TASK, view1.id)
        assert result is True
        
        default = service.get_default_view(user_id, SavedViewEntityType.TASK)
        assert default.id == view1.id
        
        # Set view2 as default (should unset view1)
        service.set_default_view(user_id, SavedViewEntityType.TASK, view2.id)
        
        default = service.get_default_view(user_id, SavedViewEntityType.TASK)
        assert default.id == view2.id
        
        # Verify view1 is no longer default
        updated_view1 = service.get_view(view1.id)
        assert updated_view1.is_default is False
    
    def test_toggle_pin(self, service: SavedViewsService, user_id):
        """Test toggling pin status."""
        view = service.create_view(
            name="Pinnable",
            entity_type=SavedViewEntityType.ACCOUNT,
            owner_id=user_id,
        )
        
        assert view.pinned is False
        
        service.toggle_pin(view.id)
        updated = service.get_view(view.id)
        assert updated.pinned is True
        
        service.toggle_pin(view.id)
        updated = service.get_view(view.id)
        assert updated.pinned is False
    
    def test_get_pinned_views(self, service: SavedViewsService, user_id):
        """Test getting pinned views."""
        view1 = service.create_view("View 1", SavedViewEntityType.TASK, user_id)
        view2 = service.create_view("View 2", SavedViewEntityType.TASK, user_id)
        view3 = service.create_view("View 3", SavedViewEntityType.QUOTE, user_id)
        
        service.toggle_pin(view1.id)
        service.toggle_pin(view3.id)
        
        pinned = service.get_pinned_views(user_id)
        assert len(pinned) == 2
        
        pinned_tasks = service.get_pinned_views(user_id, SavedViewEntityType.TASK)
        assert len(pinned_tasks) == 1
        assert pinned_tasks[0].id == view1.id


# --------------------------------------------------------------------------
# Helper Function Tests
# --------------------------------------------------------------------------

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_build_filter_condition_with_strings(self):
        """Test building filter condition with string values."""
        condition = build_filter_condition(
            field="status",
            operator="equals",
            value="active",
        )
        
        assert condition.field == "status"
        assert condition.operator == FilterOperator.EQUALS
        assert condition.value == "active"
    
    def test_build_filter_condition_with_enums(self):
        """Test building filter condition with enum values."""
        condition = build_filter_condition(
            field="status",
            operator=FilterOperator.IN,
            value=["a", "b"],
        )
        
        assert condition.operator == FilterOperator.IN
    
    def test_build_filter_condition_with_date_preset(self):
        """Test building filter condition with date preset."""
        condition = build_filter_condition(
            field="created_at",
            operator="between",
            date_preset="this_week",
        )
        
        assert condition.date_preset == DatePreset.THIS_WEEK
    
    def test_build_sort_field(self):
        """Test building sort field."""
        sf = build_sort_field("name", "desc")
        
        assert sf.field == "name"
        assert sf.direction == SortDirection.DESC
    
    def test_build_column_config(self):
        """Test building column config."""
        col = build_column_config(
            field="name",
            label="Name",
            width=200,
            visible=True,
            order=0,
        )
        
        assert col.field == "name"
        assert col.label == "Name"
        assert col.width == 200


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestSavedViewsIntegration:
    """Integration tests for saved views."""
    
    def test_complete_workflow(self):
        """Test complete saved views workflow."""
        service = SavedViewsService()
        user_id = uuid4()
        
        # 1. Create a custom view
        view = service.create_view(
            name="Overdue High Priority Tasks",
            entity_type=SavedViewEntityType.TASK,
            owner_id=user_id,
            conditions=[
                FilterCondition(field="priority", operator=FilterOperator.EQUALS, value="high"),
                FilterCondition(field="due_date", operator=FilterOperator.OVERDUE),
            ],
            condition_logic=FilterLogic.AND,
            sort_fields=[SortField(field="due_date", direction=SortDirection.ASC)],
            description="All high priority tasks that are overdue",
            icon="alert-circle",
            color="red",
        )
        
        # 2. Apply to some entities
        now = datetime.now()
        tasks = [
            {"id": "1", "title": "Task 1", "priority": "high", "due_date": now - timedelta(days=2)},
            {"id": "2", "title": "Task 2", "priority": "low", "due_date": now - timedelta(days=1)},
            {"id": "3", "title": "Task 3", "priority": "high", "due_date": now + timedelta(days=1)},
            {"id": "4", "title": "Task 4", "priority": "high", "due_date": now - timedelta(days=5)},
        ]
        
        result = service.apply_view(view.id, tasks)
        
        assert result.matched_count == 2
        # Should be sorted by due_date ascending, so Task 4 (oldest) comes first
        assert result.entities[0]["id"] == "4"
        assert result.entities[1]["id"] == "1"
        
        # 3. Set as default
        service.set_default_view(user_id, SavedViewEntityType.TASK, view.id)
        default = service.get_default_view(user_id, SavedViewEntityType.TASK)
        assert default.id == view.id
        
        # 4. Pin the view
        service.toggle_pin(view.id)
        pinned = service.get_pinned_views(user_id)
        assert len(pinned) == 1
        
        # 5. Update the view
        service.update_view(view.id, name="Urgent Overdue Tasks")
        updated = service.get_view(view.id)
        assert updated.name == "Urgent Overdue Tasks"
        
        # 6. Duplicate for another user
        other_user = uuid4()
        copy = service.duplicate_view(view.id, other_user)
        assert copy.owner_id == other_user
        assert len(copy.conditions) == 2
        
        # 7. Delete original
        service.delete_view(view.id)
        assert service.get_view(view.id) is None
        
        # Copy should still exist
        assert service.get_view(copy.id) is not None

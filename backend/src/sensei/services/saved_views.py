"""
Saved Views/Filters Service.

Provides functionality for saving, managing, and sharing filter configurations
for entity lists (e.g., "Quotes due this week", "Red items", "Stale opps").
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class SavedViewEntityType(str, Enum):
    """Entity types that support saved views."""
    
    ACCOUNT = "account"
    CONTACT = "contact"
    RFQ = "rfq"
    QUOTE = "quote"
    OPPORTUNITY = "opportunity"
    CTQ = "ctq"
    A3 = "a3"
    TASK = "task"
    PRODUCT = "product"
    WORK_ORDER = "work_order"
    ANDON_EVENT = "andon_event"
    TRAINING = "training"
    STANDARD_WORK = "standard_work"
    KANBAN = "kanban"
    RISK = "risk"


class FilterOperator(str, Enum):
    """Operators for filter conditions."""
    
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    BEFORE = "before"
    AFTER = "after"
    WITHIN_DAYS = "within_days"
    OVERDUE = "overdue"


class FilterLogic(str, Enum):
    """Logic for combining filter conditions."""
    
    AND = "and"
    OR = "or"


class DatePreset(str, Enum):
    """Preset date ranges for filters."""
    
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    NEXT_7_DAYS = "next_7_days"
    NEXT_30_DAYS = "next_30_days"


class SortDirection(str, Enum):
    """Sort direction."""
    
    ASC = "asc"
    DESC = "desc"


class ViewVisibility(str, Enum):
    """Visibility of a saved view."""
    
    PRIVATE = "private"  # Only visible to owner
    TEAM = "team"  # Visible to team members
    ORGANIZATION = "organization"  # Visible to entire organization
    PUBLIC = "public"  # System-wide default views


@dataclass
class FilterCondition:
    """A single filter condition."""
    
    field: str
    operator: FilterOperator
    value: Any = None
    second_value: Any = None  # For BETWEEN operator
    date_preset: DatePreset | None = None
    case_sensitive: bool = False
    
    def evaluate(self, entity: dict[str, Any]) -> bool:
        """Evaluate this condition against an entity."""
        field_value = self._get_field_value(entity, self.field)
        compare_value = self._resolve_value()
        
        if self.operator == FilterOperator.EQUALS:
            return self._compare_equal(field_value, compare_value)
        
        elif self.operator == FilterOperator.NOT_EQUALS:
            return not self._compare_equal(field_value, compare_value)
        
        elif self.operator == FilterOperator.CONTAINS:
            return self._compare_contains(field_value, compare_value)
        
        elif self.operator == FilterOperator.NOT_CONTAINS:
            return not self._compare_contains(field_value, compare_value)
        
        elif self.operator == FilterOperator.STARTS_WITH:
            return self._compare_starts_with(field_value, compare_value)
        
        elif self.operator == FilterOperator.ENDS_WITH:
            return self._compare_ends_with(field_value, compare_value)
        
        elif self.operator == FilterOperator.GREATER_THAN:
            return self._compare_greater(field_value, compare_value)
        
        elif self.operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return self._compare_greater_or_equal(field_value, compare_value)
        
        elif self.operator == FilterOperator.LESS_THAN:
            return self._compare_less(field_value, compare_value)
        
        elif self.operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return self._compare_less_or_equal(field_value, compare_value)
        
        elif self.operator == FilterOperator.IN:
            return self._compare_in(field_value, compare_value)
        
        elif self.operator == FilterOperator.NOT_IN:
            return not self._compare_in(field_value, compare_value)
        
        elif self.operator == FilterOperator.IS_NULL:
            return field_value is None
        
        elif self.operator == FilterOperator.IS_NOT_NULL:
            return field_value is not None
        
        elif self.operator == FilterOperator.BETWEEN:
            return self._compare_between(field_value, compare_value, self.second_value)
        
        elif self.operator == FilterOperator.BEFORE:
            return self._compare_before(field_value, compare_value)
        
        elif self.operator == FilterOperator.AFTER:
            return self._compare_after(field_value, compare_value)
        
        elif self.operator == FilterOperator.WITHIN_DAYS:
            return self._compare_within_days(field_value, compare_value)
        
        elif self.operator == FilterOperator.OVERDUE:
            return self._compare_overdue(field_value)
        
        return False
    
    def _get_field_value(self, entity: dict[str, Any], field_path: str) -> Any:
        """Get a field value from an entity, supporting nested paths."""
        parts = field_path.split(".")
        value: Any = entity
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _resolve_value(self) -> Any:
        """Resolve the comparison value, handling date presets."""
        if self.date_preset:
            return self._resolve_date_preset(self.date_preset)
        return self.value
    
    def _resolve_date_preset(self, preset: DatePreset) -> tuple[datetime, datetime] | datetime:
        """Resolve a date preset to a date range."""
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if preset == DatePreset.TODAY:
            return (today, today + timedelta(days=1))
        
        elif preset == DatePreset.YESTERDAY:
            yesterday = today - timedelta(days=1)
            return (yesterday, today)
        
        elif preset == DatePreset.THIS_WEEK:
            start = today - timedelta(days=today.weekday())
            return (start, start + timedelta(days=7))
        
        elif preset == DatePreset.LAST_WEEK:
            end = today - timedelta(days=today.weekday())
            start = end - timedelta(days=7)
            return (start, end)
        
        elif preset == DatePreset.THIS_MONTH:
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1)
            else:
                end = today.replace(month=today.month + 1, day=1)
            return (start, end)
        
        elif preset == DatePreset.LAST_MONTH:
            end = today.replace(day=1)
            if today.month == 1:
                start = today.replace(year=today.year - 1, month=12, day=1)
            else:
                start = today.replace(month=today.month - 1, day=1)
            return (start, end)
        
        elif preset == DatePreset.THIS_QUARTER:
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            end_month = quarter * 3 + 4
            if end_month > 12:
                end = today.replace(year=today.year + 1, month=1, day=1)
            else:
                end = today.replace(month=end_month, day=1)
            return (start, end)
        
        elif preset == DatePreset.LAST_QUARTER:
            quarter = (today.month - 1) // 3
            if quarter == 0:
                start = today.replace(year=today.year - 1, month=10, day=1)
                end = today.replace(year=today.year, month=1, day=1)
            else:
                start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
                end = today.replace(month=quarter * 3 + 1, day=1)
            return (start, end)
        
        elif preset == DatePreset.THIS_YEAR:
            start = today.replace(month=1, day=1)
            end = today.replace(year=today.year + 1, month=1, day=1)
            return (start, end)
        
        elif preset == DatePreset.LAST_YEAR:
            start = today.replace(year=today.year - 1, month=1, day=1)
            end = today.replace(month=1, day=1)
            return (start, end)
        
        elif preset == DatePreset.LAST_7_DAYS:
            return (today - timedelta(days=7), today + timedelta(days=1))
        
        elif preset == DatePreset.LAST_30_DAYS:
            return (today - timedelta(days=30), today + timedelta(days=1))
        
        elif preset == DatePreset.LAST_90_DAYS:
            return (today - timedelta(days=90), today + timedelta(days=1))
        
        elif preset == DatePreset.NEXT_7_DAYS:
            return (today, today + timedelta(days=7))
        
        elif preset == DatePreset.NEXT_30_DAYS:
            return (today, today + timedelta(days=30))
        
        return now
    
    def _normalize_string(self, value: Any) -> str:
        """Normalize a string value for comparison."""
        s = str(value) if value is not None else ""
        if not self.case_sensitive:
            s = s.lower()
        return s
    
    def _compare_equal(self, field_value: Any, compare_value: Any) -> bool:
        """Compare for equality."""
        if isinstance(field_value, str) and isinstance(compare_value, str):
            return self._normalize_string(field_value) == self._normalize_string(compare_value)
        return field_value == compare_value
    
    def _compare_contains(self, field_value: Any, compare_value: Any) -> bool:
        """Check if field contains value."""
        if field_value is None:
            return False
        return self._normalize_string(compare_value) in self._normalize_string(field_value)
    
    def _compare_starts_with(self, field_value: Any, compare_value: Any) -> bool:
        """Check if field starts with value."""
        if field_value is None:
            return False
        return self._normalize_string(field_value).startswith(self._normalize_string(compare_value))
    
    def _compare_ends_with(self, field_value: Any, compare_value: Any) -> bool:
        """Check if field ends with value."""
        if field_value is None:
            return False
        return self._normalize_string(field_value).endswith(self._normalize_string(compare_value))
    
    def _compare_greater(self, field_value: Any, compare_value: Any) -> bool:
        """Compare for greater than."""
        if field_value is None or compare_value is None:
            return False
        try:
            return field_value > compare_value
        except TypeError:
            return False
    
    def _compare_greater_or_equal(self, field_value: Any, compare_value: Any) -> bool:
        """Compare for greater than or equal."""
        if field_value is None or compare_value is None:
            return False
        try:
            return field_value >= compare_value
        except TypeError:
            return False
    
    def _compare_less(self, field_value: Any, compare_value: Any) -> bool:
        """Compare for less than."""
        if field_value is None or compare_value is None:
            return False
        try:
            return field_value < compare_value
        except TypeError:
            return False
    
    def _compare_less_or_equal(self, field_value: Any, compare_value: Any) -> bool:
        """Compare for less than or equal."""
        if field_value is None or compare_value is None:
            return False
        try:
            return field_value <= compare_value
        except TypeError:
            return False
    
    def _compare_in(self, field_value: Any, compare_value: Any) -> bool:
        """Check if field value is in list."""
        if not isinstance(compare_value, (list, tuple, set)):
            return False
        if isinstance(field_value, str):
            return self._normalize_string(field_value) in [
                self._normalize_string(v) for v in compare_value
            ]
        return field_value in compare_value
    
    def _compare_between(self, field_value: Any, min_value: Any, max_value: Any) -> bool:
        """Check if field is between two values."""
        if field_value is None or min_value is None or max_value is None:
            return False
        try:
            return min_value <= field_value <= max_value
        except TypeError:
            return False
    
    def _compare_before(self, field_value: Any, compare_value: Any) -> bool:
        """Check if date is before value."""
        fv = self._to_datetime(field_value)
        cv = self._to_datetime(compare_value)
        if fv is None or cv is None:
            return False
        return fv < cv
    
    def _compare_after(self, field_value: Any, compare_value: Any) -> bool:
        """Check if date is after value."""
        fv = self._to_datetime(field_value)
        cv = self._to_datetime(compare_value)
        if fv is None or cv is None:
            return False
        return fv > cv
    
    def _compare_within_days(self, field_value: Any, days: Any) -> bool:
        """Check if date is within N days from now."""
        fv = self._to_datetime(field_value)
        if fv is None:
            return False
        try:
            days_int = int(days)
        except (ValueError, TypeError):
            return False
        now = datetime.now()
        future = now + timedelta(days=days_int)
        return now <= fv <= future
    
    def _compare_overdue(self, field_value: Any) -> bool:
        """Check if date is in the past (overdue)."""
        fv = self._to_datetime(field_value)
        if fv is None:
            return False
        return fv < datetime.now()
    
    def _to_datetime(self, value: Any) -> datetime | None:
        """Convert a value to datetime."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, tuple) and len(value) == 2:
            # Date range - return start
            return value[0] if isinstance(value[0], datetime) else None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return None
        return None


@dataclass
class SortField:
    """A field to sort by."""
    
    field: str
    direction: SortDirection = SortDirection.ASC


@dataclass
class ColumnConfig:
    """Configuration for a visible column."""
    
    field: str
    label: str | None = None
    width: int | None = None
    visible: bool = True
    order: int = 0


@dataclass
class SavedView:
    """A saved view configuration."""
    
    id: str
    name: str
    entity_type: SavedViewEntityType
    owner_id: UUID
    visibility: ViewVisibility = ViewVisibility.PRIVATE
    description: str = ""
    conditions: list[FilterCondition] = field(default_factory=list)
    condition_logic: FilterLogic = FilterLogic.AND
    sort_fields: list[SortField] = field(default_factory=list)
    columns: list[ColumnConfig] = field(default_factory=list)
    page_size: int = 25
    is_default: bool = False
    icon: str | None = None
    color: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    last_used_at: datetime | None = None
    team_ids: list[UUID] = field(default_factory=list)
    pinned: bool = False
    
    def matches(self, entity: dict[str, Any]) -> bool:
        """Check if an entity matches this view's filters."""
        if not self.conditions:
            return True
        
        if self.condition_logic == FilterLogic.AND:
            return all(c.evaluate(entity) for c in self.conditions)
        else:  # OR
            return any(c.evaluate(entity) for c in self.conditions)
    
    def apply_sort(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply sorting to a list of entities."""
        if not self.sort_fields:
            return entities
        
        def sort_key(entity: dict[str, Any]) -> tuple:
            values = []
            for sf in self.sort_fields:
                value = self._get_field_value(entity, sf.field)
                # Handle None values
                if value is None:
                    value = "" if isinstance(value, str) else 0
                values.append(value)
            return tuple(values)
        
        # Sort by first field, then by second, etc.
        sorted_entities = sorted(entities, key=sort_key)
        
        # Reverse if first sort is DESC
        if self.sort_fields and self.sort_fields[0].direction == SortDirection.DESC:
            sorted_entities = list(reversed(sorted_entities))
        
        return sorted_entities
    
    def _get_field_value(self, entity: dict[str, Any], field_path: str) -> Any:
        """Get a field value from an entity."""
        parts = field_path.split(".")
        value: Any = entity
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value


@dataclass
class ViewFilterResult:
    """Result of applying a view to entities."""
    
    view: SavedView
    total_count: int
    matched_count: int
    entities: list[dict[str, Any]]
    page: int = 1
    page_size: int = 25
    has_more: bool = False


class SavedViewsService:
    """Service for managing saved views/filters."""
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._views: dict[str, SavedView] = {}
        self._system_views: list[SavedView] = []
        self._register_system_views()
    
    def _register_system_views(self) -> None:
        """Register default system views."""
        system_owner = UUID("00000000-0000-0000-0000-000000000000")
        
        # Tasks - Overdue
        self._system_views.append(SavedView(
            id="system-tasks-overdue",
            name="Overdue Tasks",
            entity_type=SavedViewEntityType.TASK,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="All tasks that are past their due date",
            conditions=[
                FilterCondition(field="due_date", operator=FilterOperator.OVERDUE),
                FilterCondition(field="status", operator=FilterOperator.NOT_IN, value=["completed", "cancelled"]),
            ],
            sort_fields=[SortField(field="due_date", direction=SortDirection.ASC)],
            icon="alert-circle",
            color="red",
        ))
        
        # Tasks - Due This Week
        self._system_views.append(SavedView(
            id="system-tasks-due-this-week",
            name="Due This Week",
            entity_type=SavedViewEntityType.TASK,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="Tasks due within the current week",
            conditions=[
                FilterCondition(field="due_date", operator=FilterOperator.EQUALS, date_preset=DatePreset.THIS_WEEK),
            ],
            sort_fields=[SortField(field="due_date", direction=SortDirection.ASC)],
            icon="calendar",
            color="blue",
        ))
        
        # Quotes - Draft
        self._system_views.append(SavedView(
            id="system-quotes-draft",
            name="Draft Quotes",
            entity_type=SavedViewEntityType.QUOTE,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="Quotes in draft status",
            conditions=[
                FilterCondition(field="status", operator=FilterOperator.EQUALS, value="draft"),
            ],
            sort_fields=[SortField(field="updated_at", direction=SortDirection.DESC)],
            icon="file-text",
            color="gray",
        ))
        
        # Quotes - Pending Approval
        self._system_views.append(SavedView(
            id="system-quotes-pending-approval",
            name="Pending Approval",
            entity_type=SavedViewEntityType.QUOTE,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="Quotes awaiting approval",
            conditions=[
                FilterCondition(field="status", operator=FilterOperator.EQUALS, value="pending_approval"),
            ],
            sort_fields=[SortField(field="created_at", direction=SortDirection.ASC)],
            icon="clock",
            color="yellow",
        ))
        
        # RFQs - Stale
        self._system_views.append(SavedView(
            id="system-rfqs-stale",
            name="Stale RFQs",
            entity_type=SavedViewEntityType.RFQ,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="RFQs with no activity in the last 14 days",
            conditions=[
                FilterCondition(field="is_stale", operator=FilterOperator.EQUALS, value=True),
            ],
            sort_fields=[SortField(field="last_activity_at", direction=SortDirection.ASC)],
            icon="alert-triangle",
            color="orange",
        ))
        
        # RFQs - Incomplete
        self._system_views.append(SavedView(
            id="system-rfqs-incomplete",
            name="Incomplete RFQs",
            entity_type=SavedViewEntityType.RFQ,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="RFQs with completeness score below 80%",
            conditions=[
                FilterCondition(field="completeness_score", operator=FilterOperator.LESS_THAN, value=80),
            ],
            sort_fields=[SortField(field="completeness_score", direction=SortDirection.ASC)],
            icon="edit",
            color="purple",
        ))
        
        # Opportunities - High Value
        self._system_views.append(SavedView(
            id="system-opps-high-value",
            name="High Value Opportunities",
            entity_type=SavedViewEntityType.OPPORTUNITY,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="Opportunities with value over $100,000",
            conditions=[
                FilterCondition(field="estimated_value", operator=FilterOperator.GREATER_THAN_OR_EQUAL, value=100000),
            ],
            sort_fields=[SortField(field="estimated_value", direction=SortDirection.DESC)],
            icon="dollar-sign",
            color="green",
        ))
        
        # A3s - Open
        self._system_views.append(SavedView(
            id="system-a3s-open",
            name="Open A3s",
            entity_type=SavedViewEntityType.A3,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="A3s in open status",
            conditions=[
                FilterCondition(field="status", operator=FilterOperator.IN, value=["open", "in_progress"]),
            ],
            sort_fields=[SortField(field="created_at", direction=SortDirection.DESC)],
            icon="file-plus",
            color="blue",
        ))
        
        # Risks - High Severity
        self._system_views.append(SavedView(
            id="system-risks-high",
            name="High Severity Risks",
            entity_type=SavedViewEntityType.RISK,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="Risks with high or critical severity",
            conditions=[
                FilterCondition(field="severity", operator=FilterOperator.IN, value=["high", "critical"]),
            ],
            sort_fields=[SortField(field="severity", direction=SortDirection.DESC)],
            icon="alert-octagon",
            color="red",
        ))
        
        # Andon Events - Unresolved
        self._system_views.append(SavedView(
            id="system-andon-unresolved",
            name="Unresolved Andon Events",
            entity_type=SavedViewEntityType.ANDON_EVENT,
            owner_id=system_owner,
            visibility=ViewVisibility.PUBLIC,
            description="Andon events that haven't been resolved",
            conditions=[
                FilterCondition(field="resolved_at", operator=FilterOperator.IS_NULL),
            ],
            sort_fields=[SortField(field="created_at", direction=SortDirection.ASC)],
            icon="bell",
            color="red",
        ))
    
    def get_system_views(
        self,
        entity_type: SavedViewEntityType | None = None,
    ) -> list[SavedView]:
        """Get all system views, optionally filtered by entity type."""
        if entity_type:
            return [v for v in self._system_views if v.entity_type == entity_type]
        return list(self._system_views)
    
    def create_view(
        self,
        name: str,
        entity_type: SavedViewEntityType,
        owner_id: UUID,
        conditions: list[FilterCondition] | None = None,
        condition_logic: FilterLogic = FilterLogic.AND,
        sort_fields: list[SortField] | None = None,
        columns: list[ColumnConfig] | None = None,
        visibility: ViewVisibility = ViewVisibility.PRIVATE,
        description: str = "",
        page_size: int = 25,
        icon: str | None = None,
        color: str | None = None,
        team_ids: list[UUID] | None = None,
    ) -> SavedView:
        """Create a new saved view."""
        view_id = str(uuid4())
        
        view = SavedView(
            id=view_id,
            name=name,
            entity_type=entity_type,
            owner_id=owner_id,
            visibility=visibility,
            description=description,
            conditions=conditions or [],
            condition_logic=condition_logic,
            sort_fields=sort_fields or [],
            columns=columns or [],
            page_size=page_size,
            icon=icon,
            color=color,
            team_ids=team_ids or [],
        )
        
        self._views[view_id] = view
        return view
    
    def get_view(self, view_id: str) -> SavedView | None:
        """Get a view by ID."""
        # Check user views first
        if view_id in self._views:
            return self._views[view_id]
        
        # Check system views
        for sv in self._system_views:
            if sv.id == view_id:
                return sv
        
        return None
    
    def update_view(
        self,
        view_id: str,
        name: str | None = None,
        conditions: list[FilterCondition] | None = None,
        condition_logic: FilterLogic | None = None,
        sort_fields: list[SortField] | None = None,
        columns: list[ColumnConfig] | None = None,
        visibility: ViewVisibility | None = None,
        description: str | None = None,
        page_size: int | None = None,
        icon: str | None = None,
        color: str | None = None,
        team_ids: list[UUID] | None = None,
        is_default: bool | None = None,
        pinned: bool | None = None,
    ) -> SavedView | None:
        """Update an existing view."""
        view = self._views.get(view_id)
        if not view:
            return None
        
        if name is not None:
            view.name = name
        if conditions is not None:
            view.conditions = conditions
        if condition_logic is not None:
            view.condition_logic = condition_logic
        if sort_fields is not None:
            view.sort_fields = sort_fields
        if columns is not None:
            view.columns = columns
        if visibility is not None:
            view.visibility = visibility
        if description is not None:
            view.description = description
        if page_size is not None:
            view.page_size = page_size
        if icon is not None:
            view.icon = icon
        if color is not None:
            view.color = color
        if team_ids is not None:
            view.team_ids = team_ids
        if is_default is not None:
            view.is_default = is_default
        if pinned is not None:
            view.pinned = pinned
        
        view.updated_at = datetime.now()
        return view
    
    def delete_view(self, view_id: str) -> bool:
        """Delete a view."""
        if view_id in self._views:
            del self._views[view_id]
            return True
        return False
    
    def list_views(
        self,
        user_id: UUID,
        entity_type: SavedViewEntityType | None = None,
        include_system: bool = True,
        include_team: bool = True,
        include_organization: bool = True,
        team_ids: list[UUID] | None = None,
    ) -> list[SavedView]:
        """List views accessible to a user."""
        results: list[SavedView] = []
        
        # Add system views
        if include_system:
            system_views = self.get_system_views(entity_type)
            results.extend(system_views)
        
        # Add user views
        for view in self._views.values():
            # Filter by entity type
            if entity_type and view.entity_type != entity_type:
                continue
            
            # Check visibility
            if view.owner_id == user_id:
                results.append(view)
            elif view.visibility == ViewVisibility.ORGANIZATION and include_organization:
                results.append(view)
            elif view.visibility == ViewVisibility.TEAM and include_team:
                if team_ids:
                    if any(tid in view.team_ids for tid in team_ids):
                        results.append(view)
                else:
                    results.append(view)
            elif view.visibility == ViewVisibility.PUBLIC:
                results.append(view)
        
        return results
    
    def apply_view(
        self,
        view_id: str,
        entities: list[dict[str, Any]],
        page: int = 1,
        page_size: int | None = None,
    ) -> ViewFilterResult | None:
        """Apply a view's filters to a list of entities."""
        view = self.get_view(view_id)
        if not view:
            return None
        
        # Record usage
        if view_id in self._views:
            self._views[view_id].use_count += 1
            self._views[view_id].last_used_at = datetime.now()
        
        # Filter entities
        matched = [e for e in entities if view.matches(e)]
        
        # Sort entities
        sorted_entities = view.apply_sort(matched)
        
        # Paginate
        effective_page_size = page_size or view.page_size
        start = (page - 1) * effective_page_size
        end = start + effective_page_size
        page_entities = sorted_entities[start:end]
        
        return ViewFilterResult(
            view=view,
            total_count=len(entities),
            matched_count=len(matched),
            entities=page_entities,
            page=page,
            page_size=effective_page_size,
            has_more=end < len(matched),
        )
    
    def duplicate_view(
        self,
        view_id: str,
        new_owner_id: UUID,
        new_name: str | None = None,
    ) -> SavedView | None:
        """Duplicate a view for a new owner."""
        source = self.get_view(view_id)
        if not source:
            return None
        
        return self.create_view(
            name=new_name or f"Copy of {source.name}",
            entity_type=source.entity_type,
            owner_id=new_owner_id,
            conditions=list(source.conditions),
            condition_logic=source.condition_logic,
            sort_fields=list(source.sort_fields),
            columns=list(source.columns),
            visibility=ViewVisibility.PRIVATE,
            description=source.description,
            page_size=source.page_size,
            icon=source.icon,
            color=source.color,
        )
    
    def set_default_view(
        self,
        user_id: UUID,
        entity_type: SavedViewEntityType,
        view_id: str,
    ) -> bool:
        """Set a view as the default for a user and entity type."""
        # Unset any existing default
        for view in self._views.values():
            if (
                view.owner_id == user_id
                and view.entity_type == entity_type
                and view.is_default
            ):
                view.is_default = False
        
        # Set new default
        target_view = self.get_view(view_id)
        if target_view and view_id in self._views:
            self._views[view_id].is_default = True
            return True
        
        return False
    
    def get_default_view(
        self,
        user_id: UUID,
        entity_type: SavedViewEntityType,
    ) -> SavedView | None:
        """Get the default view for a user and entity type."""
        for view in self._views.values():
            if (
                view.owner_id == user_id
                and view.entity_type == entity_type
                and view.is_default
            ):
                return view
        return None
    
    def toggle_pin(self, view_id: str) -> bool:
        """Toggle the pinned status of a view."""
        if view_id in self._views:
            self._views[view_id].pinned = not self._views[view_id].pinned
            return True
        return False
    
    def get_pinned_views(
        self,
        user_id: UUID,
        entity_type: SavedViewEntityType | None = None,
    ) -> list[SavedView]:
        """Get all pinned views for a user."""
        results = []
        for view in self._views.values():
            if view.owner_id == user_id and view.pinned:
                if entity_type is None or view.entity_type == entity_type:
                    results.append(view)
        return results


# --------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------

def build_filter_condition(
    field: str,
    operator: str | FilterOperator,
    value: Any = None,
    second_value: Any = None,
    date_preset: str | DatePreset | None = None,
    case_sensitive: bool = False,
) -> FilterCondition:
    """Build a filter condition with string or enum values."""
    op = operator if isinstance(operator, FilterOperator) else FilterOperator(operator)
    dp = None
    if date_preset:
        dp = date_preset if isinstance(date_preset, DatePreset) else DatePreset(date_preset)
    
    return FilterCondition(
        field=field,
        operator=op,
        value=value,
        second_value=second_value,
        date_preset=dp,
        case_sensitive=case_sensitive,
    )


def build_sort_field(field: str, direction: str | SortDirection = "asc") -> SortField:
    """Build a sort field with string or enum direction."""
    d = direction if isinstance(direction, SortDirection) else SortDirection(direction)
    return SortField(field=field, direction=d)


def build_column_config(
    field: str,
    label: str | None = None,
    width: int | None = None,
    visible: bool = True,
    order: int = 0,
) -> ColumnConfig:
    """Build a column configuration."""
    return ColumnConfig(
        field=field,
        label=label,
        width=width,
        visible=visible,
        order=order,
    )

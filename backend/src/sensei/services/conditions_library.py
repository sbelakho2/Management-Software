"""
Conditions Library Service.

Manages reusable condition templates for quotes and qualifications.
Templates can be standard (built-in) or custom (user-created).

Condition Categories:
- MOQ: Minimum Order Quantity requirements
- Lead Time: Delivery lead time conditions
- Price Validity: Quote/price validity periods
- Payment Terms: Payment conditions
- NRE: Non-Recurring Engineering costs
- Yield: Production yield expectations
- Compliance: Regulatory compliance requirements
- Warranty: Warranty terms and conditions
- Shipping: Shipping and freight conditions
- Custom: User-defined conditions
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConditionCategory(str, Enum):
    """Categories of condition templates."""
    
    MOQ = "moq"  # Minimum Order Quantity
    LEAD_TIME = "lead_time"  # Delivery lead times
    PRICE_VALIDITY = "price_validity"  # Quote validity periods
    PAYMENT_TERMS = "payment_terms"  # Payment conditions
    NRE = "nre"  # Non-Recurring Engineering
    YIELD = "yield"  # Production yield expectations
    COMPLIANCE = "compliance"  # Regulatory/certification requirements
    WARRANTY = "warranty"  # Warranty terms
    SHIPPING = "shipping"  # Shipping/freight/incoterms
    TOOLING = "tooling"  # Tooling ownership/amortization
    PACKAGING = "packaging"  # Packaging requirements
    TESTING = "testing"  # Testing/inspection requirements
    QUALITY = "quality"  # Quality standards/requirements
    CUSTOM = "custom"  # User-defined conditions


class ConditionType(str, Enum):
    """Type of condition."""
    
    STANDARD = "standard"  # Standard condition (informational)
    WARNING = "warning"  # Warning condition (needs acknowledgment)
    HARD_STOP = "hard_stop"  # Blocking condition (must be resolved)
    NEGOTIABLE = "negotiable"  # Can be negotiated with customer
    INTERNAL = "internal"  # Internal-only, not shown on customer documents


class ConditionScope(str, Enum):
    """Where a condition can be applied."""
    
    QUOTE = "quote"  # Applied to quotes
    QUALIFICATION = "qualification"  # Applied to qualification decisions
    RFQ = "rfq"  # Applied to RFQ responses
    ORDER = "order"  # Applied to orders
    UNIVERSAL = "universal"  # Can be applied anywhere


class PlaceholderType(str, Enum):
    """Types of placeholders in condition text."""
    
    NUMBER = "number"  # Numeric value
    TEXT = "text"  # Free text
    DATE = "date"  # Date value
    CURRENCY = "currency"  # Currency amount
    PERCENTAGE = "percentage"  # Percentage value
    SELECT = "select"  # Selection from options
    DURATION = "duration"  # Time duration (e.g., "30 days")


@dataclass
class Placeholder:
    """A placeholder in a condition template."""
    
    name: str  # e.g., "moq_quantity"
    display_label: str  # e.g., "Minimum Order Quantity"
    placeholder_type: PlaceholderType
    required: bool = True
    default_value: str | None = None
    options: list[str] | None = None  # For SELECT type
    min_value: float | None = None  # For NUMBER type
    max_value: float | None = None  # For NUMBER type
    validation_regex: str | None = None  # For TEXT type
    help_text: str | None = None


@dataclass
class ConditionTemplate:
    """A reusable condition template."""
    
    id: UUID
    code: str  # Unique short code (e.g., "MOQ-001")
    name: str  # Display name
    category: ConditionCategory
    condition_type: ConditionType
    scope: ConditionScope
    
    # Template text with placeholders: {{placeholder_name}}
    template_text: str
    
    # Placeholders in the template
    placeholders: list[Placeholder] = field(default_factory=list)
    
    # Metadata
    description: str | None = None
    is_default: bool = False  # System-provided template
    is_active: bool = True
    sort_order: int = 0
    
    # Applicability rules
    applies_to_categories: list[str] | None = None  # Product categories
    applies_to_customers: list[str] | None = None  # Customer segments
    
    # Versioning
    version: int = 1
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    created_by_id: UUID | None = None
    
    # Translations (for multi-language support)
    translations: dict[str, str] | None = None  # {"fr": "...", "ar": "..."}


@dataclass
class AppliedCondition:
    """A condition applied to a specific entity (quote, qualification, etc.)."""
    
    id: UUID
    template_id: UUID | None  # Reference to template (if from template)
    entity_type: str  # "quote", "qualification", "rfq"
    entity_id: UUID
    
    # Resolved text (with placeholders filled in)
    condition_text: str
    
    # Placeholder values used
    placeholder_values: dict[str, Any] = field(default_factory=dict)
    
    # Metadata from template
    category: ConditionCategory = ConditionCategory.CUSTOM
    condition_type: ConditionType = ConditionType.STANDARD
    
    # Status
    is_acknowledged: bool = False  # For WARNING types
    acknowledged_by_id: UUID | None = None
    acknowledged_at: datetime | None = None
    
    is_resolved: bool = False  # For HARD_STOP types
    resolved_by_id: UUID | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    
    # Ordering
    sort_order: int = 0
    
    # Timestamps
    applied_at: datetime = field(default_factory=_utcnow)
    applied_by_id: UUID | None = None


@dataclass
class ConditionSet:
    """A named set of conditions for reuse."""
    
    id: UUID
    name: str
    description: str | None
    condition_template_ids: list[UUID]
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    created_by_id: UUID | None = None


class ConditionsLibraryService:
    """Service for managing condition templates and applied conditions."""
    
    def __init__(self) -> None:
        """Initialize the conditions library service."""
        self._templates: dict[UUID, ConditionTemplate] = {}
        self._applied_conditions: dict[UUID, AppliedCondition] = {}
        self._condition_sets: dict[UUID, ConditionSet] = {}
        self._code_index: dict[str, UUID] = {}  # code -> template_id
        
        # Register default templates
        self._register_default_templates()
    
    # ========== Template Management ==========
    
    def create_template(
        self,
        code: str,
        name: str,
        category: ConditionCategory,
        condition_type: ConditionType,
        scope: ConditionScope,
        template_text: str,
        placeholders: list[Placeholder] | None = None,
        description: str | None = None,
        applies_to_categories: list[str] | None = None,
        applies_to_customers: list[str] | None = None,
        translations: dict[str, str] | None = None,
        created_by_id: UUID | None = None,
    ) -> ConditionTemplate:
        """Create a new condition template."""
        # Validate code uniqueness
        if code in self._code_index:
            raise ValueError(f"Template with code '{code}' already exists")
        
        # Validate placeholders in template text
        if placeholders:
            for placeholder in placeholders:
                if f"{{{{{placeholder.name}}}}}" not in template_text:
                    raise ValueError(
                        f"Placeholder '{placeholder.name}' not found in template text"
                    )
        
        template = ConditionTemplate(
            id=uuid4(),
            code=code,
            name=name,
            category=category,
            condition_type=condition_type,
            scope=scope,
            template_text=template_text,
            placeholders=placeholders or [],
            description=description,
            applies_to_categories=applies_to_categories,
            applies_to_customers=applies_to_customers,
            translations=translations,
            created_by_id=created_by_id,
        )
        
        self._templates[template.id] = template
        self._code_index[code] = template.id
        
        return template
    
    def get_template(self, template_id: UUID) -> ConditionTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_template_by_code(self, code: str) -> ConditionTemplate | None:
        """Get a template by its code."""
        template_id = self._code_index.get(code)
        if template_id:
            return self._templates.get(template_id)
        return None
    
    def update_template(
        self,
        template_id: UUID,
        name: str | None = None,
        template_text: str | None = None,
        placeholders: list[Placeholder] | None = None,
        description: str | None = None,
        condition_type: ConditionType | None = None,
        scope: ConditionScope | None = None,
        applies_to_categories: list[str] | None = None,
        applies_to_customers: list[str] | None = None,
        translations: dict[str, str] | None = None,
        is_active: bool | None = None,
    ) -> ConditionTemplate | None:
        """Update an existing template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        if template.is_default:
            raise ValueError("Cannot modify default templates")
        
        if name is not None:
            template.name = name
        if template_text is not None:
            template.template_text = template_text
        if placeholders is not None:
            template.placeholders = placeholders
        if description is not None:
            template.description = description
        if condition_type is not None:
            template.condition_type = condition_type
        if scope is not None:
            template.scope = scope
        if applies_to_categories is not None:
            template.applies_to_categories = applies_to_categories
        if applies_to_customers is not None:
            template.applies_to_customers = applies_to_customers
        if translations is not None:
            template.translations = translations
        if is_active is not None:
            template.is_active = is_active
        
        template.version += 1
        template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        return template
    
    def delete_template(self, template_id: UUID) -> bool:
        """Delete a template."""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        if template.is_default:
            raise ValueError("Cannot delete default templates")
        
        # Check if template is in use
        for applied in self._applied_conditions.values():
            if applied.template_id == template_id:
                raise ValueError("Cannot delete template that is in use")
        
        del self._templates[template_id]
        del self._code_index[template.code]
        
        return True
    
    def list_templates(
        self,
        category: ConditionCategory | None = None,
        condition_type: ConditionType | None = None,
        scope: ConditionScope | None = None,
        is_active: bool | None = None,
        include_defaults: bool = True,
        search: str | None = None,
    ) -> list[ConditionTemplate]:
        """List templates with optional filtering."""
        templates = list(self._templates.values())
        
        if category is not None:
            templates = [t for t in templates if t.category == category]
        
        if condition_type is not None:
            templates = [t for t in templates if t.condition_type == condition_type]
        
        if scope is not None:
            templates = [
                t for t in templates
                if t.scope == scope or t.scope == ConditionScope.UNIVERSAL
            ]
        
        if is_active is not None:
            templates = [t for t in templates if t.is_active == is_active]
        
        if not include_defaults:
            templates = [t for t in templates if not t.is_default]
        
        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates
                if search_lower in t.name.lower()
                or search_lower in t.code.lower()
                or (t.description and search_lower in t.description.lower())
            ]
        
        # Sort by category, then sort_order, then name
        templates.sort(key=lambda t: (t.category.value, t.sort_order, t.name))
        
        return templates
    
    def get_templates_by_category(
        self,
        category: ConditionCategory,
    ) -> list[ConditionTemplate]:
        """Get all templates for a specific category."""
        return self.list_templates(category=category, is_active=True)
    
    # ========== Condition Application ==========
    
    def render_template(
        self,
        template: ConditionTemplate,
        placeholder_values: dict[str, Any],
        language: str = "en",
    ) -> str:
        """Render a template with placeholder values."""
        # Validate required placeholders
        for placeholder in template.placeholders:
            if placeholder.required and placeholder.name not in placeholder_values:
                if placeholder.default_value is not None:
                    placeholder_values[placeholder.name] = placeholder.default_value
                else:
                    raise ValueError(
                        f"Required placeholder '{placeholder.name}' not provided"
                    )
        
        # Validate placeholder values
        for placeholder in template.placeholders:
            if placeholder.name in placeholder_values:
                value = placeholder_values[placeholder.name]
                
                if placeholder.placeholder_type == PlaceholderType.NUMBER:
                    try:
                        num_value = float(value)
                        if placeholder.min_value is not None and num_value < placeholder.min_value:
                            raise ValueError(
                                f"Value for '{placeholder.name}' must be at least {placeholder.min_value}"
                            )
                        if placeholder.max_value is not None and num_value > placeholder.max_value:
                            raise ValueError(
                                f"Value for '{placeholder.name}' must be at most {placeholder.max_value}"
                            )
                    except (TypeError, ValueError) as e:
                        if "must be" not in str(e):
                            raise ValueError(
                                f"Placeholder '{placeholder.name}' requires a numeric value"
                            )
                        raise
                
                if placeholder.placeholder_type == PlaceholderType.SELECT:
                    if placeholder.options and value not in placeholder.options:
                        raise ValueError(
                            f"Value for '{placeholder.name}' must be one of: {placeholder.options}"
                        )
        
        # Get the appropriate text (translated or default)
        text = template.template_text
        if language != "en" and template.translations and language in template.translations:
            text = template.translations[language]
        
        # Replace placeholders
        for placeholder in template.placeholders:
            if placeholder.name in placeholder_values:
                value = str(placeholder_values[placeholder.name])
                text = text.replace(f"{{{{{placeholder.name}}}}}", value)
        
        return text
    
    def apply_condition(
        self,
        entity_type: str,
        entity_id: UUID,
        template_id: UUID | None = None,
        placeholder_values: dict[str, Any] | None = None,
        custom_text: str | None = None,
        category: ConditionCategory = ConditionCategory.CUSTOM,
        condition_type: ConditionType = ConditionType.STANDARD,
        applied_by_id: UUID | None = None,
        sort_order: int = 0,
        language: str = "en",
    ) -> AppliedCondition:
        """Apply a condition to an entity."""
        if template_id is None and custom_text is None:
            raise ValueError("Either template_id or custom_text must be provided")
        
        if template_id is not None:
            template = self._templates.get(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Render the template
            condition_text = self.render_template(
                template,
                placeholder_values or {},
                language,
            )
            category = template.category
            condition_type = template.condition_type
        else:
            # custom_text is guaranteed non-None due to check above
            assert custom_text is not None
            condition_text = custom_text
        
        applied = AppliedCondition(
            id=uuid4(),
            template_id=template_id,
            entity_type=entity_type,
            entity_id=entity_id,
            condition_text=condition_text,
            placeholder_values=placeholder_values or {},
            category=category,
            condition_type=condition_type,
            sort_order=sort_order,
            applied_by_id=applied_by_id,
        )
        
        self._applied_conditions[applied.id] = applied
        
        return applied
    
    def get_applied_condition(self, condition_id: UUID) -> AppliedCondition | None:
        """Get an applied condition by ID."""
        return self._applied_conditions.get(condition_id)
    
    def get_conditions_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        category: ConditionCategory | None = None,
        condition_type: ConditionType | None = None,
        unresolved_only: bool = False,
    ) -> list[AppliedCondition]:
        """Get all conditions applied to an entity."""
        conditions = [
            c for c in self._applied_conditions.values()
            if c.entity_type == entity_type and c.entity_id == entity_id
        ]
        
        if category is not None:
            conditions = [c for c in conditions if c.category == category]
        
        if condition_type is not None:
            conditions = [c for c in conditions if c.condition_type == condition_type]
        
        if unresolved_only:
            conditions = [
                c for c in conditions
                if c.condition_type == ConditionType.HARD_STOP and not c.is_resolved
            ]
        
        conditions.sort(key=lambda c: c.sort_order)
        return conditions
    
    def get_hard_stops_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[AppliedCondition]:
        """Get unresolved hard stops for an entity."""
        return self.get_conditions_for_entity(
            entity_type,
            entity_id,
            condition_type=ConditionType.HARD_STOP,
            unresolved_only=True,
        )
    
    def has_unresolved_hard_stops(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> bool:
        """Check if an entity has any unresolved hard stops."""
        return len(self.get_hard_stops_for_entity(entity_type, entity_id)) > 0
    
    def acknowledge_condition(
        self,
        condition_id: UUID,
        acknowledged_by_id: UUID,
    ) -> AppliedCondition | None:
        """Acknowledge a warning condition."""
        condition = self._applied_conditions.get(condition_id)
        if not condition:
            return None
        
        if condition.condition_type != ConditionType.WARNING:
            raise ValueError("Only WARNING conditions can be acknowledged")
        
        condition.is_acknowledged = True
        condition.acknowledged_by_id = acknowledged_by_id
        condition.acknowledged_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        return condition
    
    def resolve_hard_stop(
        self,
        condition_id: UUID,
        resolved_by_id: UUID,
        resolution_notes: str | None = None,
    ) -> AppliedCondition | None:
        """Resolve a hard stop condition."""
        condition = self._applied_conditions.get(condition_id)
        if not condition:
            return None
        
        if condition.condition_type != ConditionType.HARD_STOP:
            raise ValueError("Only HARD_STOP conditions can be resolved")
        
        condition.is_resolved = True
        condition.resolved_by_id = resolved_by_id
        condition.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        condition.resolution_notes = resolution_notes
        
        return condition
    
    def remove_condition(self, condition_id: UUID) -> bool:
        """Remove an applied condition."""
        if condition_id in self._applied_conditions:
            del self._applied_conditions[condition_id]
            return True
        return False
    
    def update_condition_text(
        self,
        condition_id: UUID,
        new_text: str,
    ) -> AppliedCondition | None:
        """Update the text of an applied condition."""
        condition = self._applied_conditions.get(condition_id)
        if not condition:
            return None
        
        condition.condition_text = new_text
        return condition
    
    def reorder_conditions(
        self,
        entity_type: str,
        entity_id: UUID,
        condition_order: list[UUID],
    ) -> list[AppliedCondition]:
        """Reorder conditions for an entity."""
        conditions = self.get_conditions_for_entity(entity_type, entity_id)
        condition_map = {c.id: c for c in conditions}
        
        for idx, cid in enumerate(condition_order):
            if cid in condition_map:
                condition_map[cid].sort_order = idx
        
        return self.get_conditions_for_entity(entity_type, entity_id)
    
    # ========== Condition Sets ==========
    
    def create_condition_set(
        self,
        name: str,
        condition_template_ids: list[UUID],
        description: str | None = None,
        created_by_id: UUID | None = None,
    ) -> ConditionSet:
        """Create a named set of conditions."""
        # Validate all template IDs exist
        for tid in condition_template_ids:
            if tid not in self._templates:
                raise ValueError(f"Template {tid} not found")
        
        condition_set = ConditionSet(
            id=uuid4(),
            name=name,
            description=description,
            condition_template_ids=condition_template_ids,
            created_by_id=created_by_id,
        )
        
        self._condition_sets[condition_set.id] = condition_set
        return condition_set
    
    def get_condition_set(self, set_id: UUID) -> ConditionSet | None:
        """Get a condition set by ID."""
        return self._condition_sets.get(set_id)
    
    def update_condition_set(
        self,
        set_id: UUID,
        name: str | None = None,
        description: str | None = None,
        condition_template_ids: list[UUID] | None = None,
        is_active: bool | None = None,
    ) -> ConditionSet | None:
        """Update a condition set."""
        condition_set = self._condition_sets.get(set_id)
        if not condition_set:
            return None
        
        if condition_set.is_default:
            raise ValueError("Cannot modify default condition sets")
        
        if name is not None:
            condition_set.name = name
        if description is not None:
            condition_set.description = description
        if condition_template_ids is not None:
            # Validate all template IDs exist
            for tid in condition_template_ids:
                if tid not in self._templates:
                    raise ValueError(f"Template {tid} not found")
            condition_set.condition_template_ids = condition_template_ids
        if is_active is not None:
            condition_set.is_active = is_active
        
        condition_set.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return condition_set
    
    def delete_condition_set(self, set_id: UUID) -> bool:
        """Delete a condition set."""
        condition_set = self._condition_sets.get(set_id)
        if not condition_set:
            return False
        
        if condition_set.is_default:
            raise ValueError("Cannot delete default condition sets")
        
        del self._condition_sets[set_id]
        return True
    
    def list_condition_sets(
        self,
        is_active: bool | None = None,
        include_defaults: bool = True,
    ) -> list[ConditionSet]:
        """List all condition sets."""
        sets = list(self._condition_sets.values())
        
        if is_active is not None:
            sets = [s for s in sets if s.is_active == is_active]
        
        if not include_defaults:
            sets = [s for s in sets if not s.is_default]
        
        sets.sort(key=lambda s: s.name)
        return sets
    
    def apply_condition_set(
        self,
        set_id: UUID,
        entity_type: str,
        entity_id: UUID,
        placeholder_values_map: dict[str, dict[str, Any]] | None = None,
        applied_by_id: UUID | None = None,
        language: str = "en",
    ) -> list[AppliedCondition]:
        """Apply all conditions from a set to an entity."""
        condition_set = self._condition_sets.get(set_id)
        if not condition_set:
            raise ValueError(f"Condition set {set_id} not found")
        
        applied_conditions = []
        placeholder_values_map = placeholder_values_map or {}
        
        for idx, template_id in enumerate(condition_set.condition_template_ids):
            template = self._templates.get(template_id)
            if template and template.is_active:
                placeholder_values = placeholder_values_map.get(template.code, {})
                applied = self.apply_condition(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    template_id=template_id,
                    placeholder_values=placeholder_values,
                    applied_by_id=applied_by_id,
                    sort_order=idx,
                    language=language,
                )
                applied_conditions.append(applied)
        
        return applied_conditions
    
    # ========== Bulk Operations ==========
    
    def copy_conditions(
        self,
        source_entity_type: str,
        source_entity_id: UUID,
        target_entity_type: str,
        target_entity_id: UUID,
        applied_by_id: UUID | None = None,
    ) -> list[AppliedCondition]:
        """Copy all conditions from one entity to another."""
        source_conditions = self.get_conditions_for_entity(
            source_entity_type, source_entity_id
        )
        
        new_conditions = []
        for condition in source_conditions:
            new_condition = self.apply_condition(
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                template_id=condition.template_id,
                placeholder_values=condition.placeholder_values.copy(),
                custom_text=condition.condition_text if not condition.template_id else None,
                category=condition.category,
                condition_type=condition.condition_type,
                applied_by_id=applied_by_id,
                sort_order=condition.sort_order,
            )
            new_conditions.append(new_condition)
        
        return new_conditions
    
    def clear_conditions(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> int:
        """Remove all conditions from an entity."""
        conditions = self.get_conditions_for_entity(entity_type, entity_id)
        count = 0
        for condition in conditions:
            if self.remove_condition(condition.id):
                count += 1
        return count
    
    # ========== Validation ==========
    
    def validate_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> dict[str, Any]:
        """Validate an entity's conditions."""
        conditions = self.get_conditions_for_entity(entity_type, entity_id)
        
        hard_stops = [c for c in conditions if c.condition_type == ConditionType.HARD_STOP]
        unresolved_hard_stops = [c for c in hard_stops if not c.is_resolved]
        
        warnings = [c for c in conditions if c.condition_type == ConditionType.WARNING]
        unacknowledged_warnings = [c for c in warnings if not c.is_acknowledged]
        
        return {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "total_conditions": len(conditions),
            "hard_stops": len(hard_stops),
            "unresolved_hard_stops": len(unresolved_hard_stops),
            "warnings": len(warnings),
            "unacknowledged_warnings": len(unacknowledged_warnings),
            "can_proceed": len(unresolved_hard_stops) == 0,
            "requires_acknowledgment": len(unacknowledged_warnings) > 0,
            "issues": [
                {
                    "id": str(c.id),
                    "type": c.condition_type.value,
                    "text": c.condition_text,
                }
                for c in unresolved_hard_stops + unacknowledged_warnings
            ],
        }
    
    # ========== Export/Import ==========
    
    def export_conditions(
        self,
        entity_type: str,
        entity_id: UUID,
        format: str = "text",
    ) -> str | list[dict[str, Any]]:
        """Export conditions for an entity."""
        conditions = self.get_conditions_for_entity(entity_type, entity_id)
        
        if format == "text":
            lines = []
            for condition in conditions:
                prefix = ""
                if condition.condition_type == ConditionType.HARD_STOP:
                    prefix = "[BLOCKING] "
                elif condition.condition_type == ConditionType.WARNING:
                    prefix = "[WARNING] "
                elif condition.condition_type == ConditionType.NEGOTIABLE:
                    prefix = "[NEGOTIABLE] "
                elif condition.condition_type == ConditionType.INTERNAL:
                    prefix = "[INTERNAL] "
                
                lines.append(f"{prefix}{condition.condition_text}")
            return "\n".join(lines)
        else:
            return [
                {
                    "id": str(c.id),
                    "category": c.category.value,
                    "type": c.condition_type.value,
                    "text": c.condition_text,
                    "template_id": str(c.template_id) if c.template_id else None,
                    "placeholder_values": c.placeholder_values,
                }
                for c in conditions
            ]
    
    # ========== Statistics ==========
    
    def get_template_usage_stats(self) -> dict[UUID, int]:
        """Get usage count for each template."""
        usage: dict[UUID, int] = {}
        for condition in self._applied_conditions.values():
            if condition.template_id:
                usage[condition.template_id] = usage.get(condition.template_id, 0) + 1
        return usage
    
    def get_category_stats(self) -> dict[ConditionCategory, int]:
        """Get count of conditions by category."""
        stats: dict[ConditionCategory, int] = {}
        for condition in self._applied_conditions.values():
            stats[condition.category] = stats.get(condition.category, 0) + 1
        return stats
    
    # ========== Default Templates ==========
    
    def _register_default_templates(self) -> None:
        """Register system default templates."""
        defaults: list[dict[str, Any]] = [
            # MOQ Templates
            {
                "code": "MOQ-001",
                "name": "Standard MOQ",
                "category": ConditionCategory.MOQ,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Minimum order quantity of {{quantity}} units per order.",
                "placeholders": [
                    Placeholder(
                        name="quantity",
                        display_label="Minimum Quantity",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                    ),
                ],
                "description": "Standard minimum order quantity condition",
                "sort_order": 1,
            },
            {
                "code": "MOQ-002",
                "name": "Annual MOQ",
                "category": ConditionCategory.MOQ,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Minimum annual volume commitment of {{quantity}} units.",
                "placeholders": [
                    Placeholder(
                        name="quantity",
                        display_label="Annual Quantity",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                    ),
                ],
                "description": "Annual volume commitment requirement",
                "sort_order": 2,
            },
            
            # Lead Time Templates
            {
                "code": "LT-001",
                "name": "Standard Lead Time",
                "category": ConditionCategory.LEAD_TIME,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Standard lead time: {{weeks}} weeks ARO (After Receipt of Order).",
                "placeholders": [
                    Placeholder(
                        name="weeks",
                        display_label="Weeks",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                        max_value=52,
                    ),
                ],
                "description": "Standard delivery lead time in weeks",
                "sort_order": 1,
            },
            {
                "code": "LT-002",
                "name": "First Article Lead Time",
                "category": ConditionCategory.LEAD_TIME,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "First article samples: {{weeks}} weeks. Production lead time starts after FAIR approval.",
                "placeholders": [
                    Placeholder(
                        name="weeks",
                        display_label="Weeks for First Article",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                    ),
                ],
                "description": "Lead time for first article inspection samples",
                "sort_order": 2,
            },
            
            # Price Validity Templates
            {
                "code": "PV-001",
                "name": "Standard Quote Validity",
                "category": ConditionCategory.PRICE_VALIDITY,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "This quotation is valid for {{days}} days from the date of issue.",
                "placeholders": [
                    Placeholder(
                        name="days",
                        display_label="Validity Period (Days)",
                        placeholder_type=PlaceholderType.NUMBER,
                        default_value="30",
                        min_value=1,
                        max_value=365,
                    ),
                ],
                "description": "Standard quote validity period",
                "sort_order": 1,
            },
            {
                "code": "PV-002",
                "name": "Material Price Subject to Change",
                "category": ConditionCategory.PRICE_VALIDITY,
                "condition_type": ConditionType.WARNING,
                "scope": ConditionScope.QUOTE,
                "template_text": "Material prices are subject to change based on market conditions at time of order placement.",
                "placeholders": [],
                "description": "Warning about material price volatility",
                "sort_order": 2,
            },
            
            # Payment Terms Templates
            {
                "code": "PT-001",
                "name": "Net Payment Terms",
                "category": ConditionCategory.PAYMENT_TERMS,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Payment terms: Net {{days}} days from date of invoice.",
                "placeholders": [
                    Placeholder(
                        name="days",
                        display_label="Payment Days",
                        placeholder_type=PlaceholderType.NUMBER,
                        default_value="30",
                        min_value=0,
                        max_value=120,
                    ),
                ],
                "description": "Standard net payment terms",
                "sort_order": 1,
            },
            {
                "code": "PT-002",
                "name": "Advance Payment Required",
                "category": ConditionCategory.PAYMENT_TERMS,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "{{percentage}}% advance payment required upon order confirmation.",
                "placeholders": [
                    Placeholder(
                        name="percentage",
                        display_label="Advance Percentage",
                        placeholder_type=PlaceholderType.PERCENTAGE,
                        min_value=0,
                        max_value=100,
                    ),
                ],
                "description": "Advance payment requirement",
                "sort_order": 2,
            },
            {
                "code": "PT-003",
                "name": "New Customer Terms",
                "category": ConditionCategory.PAYMENT_TERMS,
                "condition_type": ConditionType.HARD_STOP,
                "scope": ConditionScope.QUOTE,
                "template_text": "New customer - credit application required. Payment by advance or LC until credit established.",
                "placeholders": [],
                "description": "Credit requirement for new customers",
                "sort_order": 3,
            },
            
            # NRE Templates
            {
                "code": "NRE-001",
                "name": "Tooling NRE",
                "category": ConditionCategory.NRE,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Non-recurring engineering charge for tooling: {{currency}} {{amount}}. Payable upon order confirmation.",
                "placeholders": [
                    Placeholder(
                        name="currency",
                        display_label="Currency",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["USD", "EUR", "GBP", "CAD"],
                        default_value="USD",
                    ),
                    Placeholder(
                        name="amount",
                        display_label="Amount",
                        placeholder_type=PlaceholderType.CURRENCY,
                        min_value=0,
                    ),
                ],
                "description": "Tooling NRE charge",
                "sort_order": 1,
            },
            {
                "code": "NRE-002",
                "name": "Test Fixture NRE",
                "category": ConditionCategory.NRE,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Test fixture development charge: {{currency}} {{amount}}.",
                "placeholders": [
                    Placeholder(
                        name="currency",
                        display_label="Currency",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["USD", "EUR", "GBP", "CAD"],
                        default_value="USD",
                    ),
                    Placeholder(
                        name="amount",
                        display_label="Amount",
                        placeholder_type=PlaceholderType.CURRENCY,
                        min_value=0,
                    ),
                ],
                "description": "Test fixture NRE charge",
                "sort_order": 2,
            },
            
            # Yield Templates
            {
                "code": "YLD-001",
                "name": "Expected Yield",
                "category": ConditionCategory.YIELD,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Pricing based on expected production yield of {{percentage}}%.",
                "placeholders": [
                    Placeholder(
                        name="percentage",
                        display_label="Expected Yield %",
                        placeholder_type=PlaceholderType.PERCENTAGE,
                        default_value="95",
                        min_value=50,
                        max_value=100,
                    ),
                ],
                "description": "Expected production yield",
                "sort_order": 1,
            },
            {
                "code": "YLD-002",
                "name": "Yield Learning Curve",
                "category": ConditionCategory.YIELD,
                "condition_type": ConditionType.WARNING,
                "scope": ConditionScope.QUOTE,
                "template_text": "Initial production yields may be lower. Price protection for first {{quantity}} units.",
                "placeholders": [
                    Placeholder(
                        name="quantity",
                        display_label="Protected Quantity",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                    ),
                ],
                "description": "Yield learning curve protection",
                "sort_order": 2,
            },
            
            # Compliance Templates
            {
                "code": "COMP-001",
                "name": "RoHS Compliance",
                "category": ConditionCategory.COMPLIANCE,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.UNIVERSAL,
                "template_text": "Product is RoHS compliant.",
                "placeholders": [],
                "description": "RoHS compliance statement",
                "sort_order": 1,
            },
            {
                "code": "COMP-002",
                "name": "REACH Compliance",
                "category": ConditionCategory.COMPLIANCE,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.UNIVERSAL,
                "template_text": "Product is REACH compliant. SVHC declarations available upon request.",
                "placeholders": [],
                "description": "REACH compliance statement",
                "sort_order": 2,
            },
            {
                "code": "COMP-003",
                "name": "Missing Certification",
                "category": ConditionCategory.COMPLIANCE,
                "condition_type": ConditionType.HARD_STOP,
                "scope": ConditionScope.QUALIFICATION,
                "template_text": "Required certification {{certification}} not yet obtained. Quote cannot proceed until resolved.",
                "placeholders": [
                    Placeholder(
                        name="certification",
                        display_label="Missing Certification",
                        placeholder_type=PlaceholderType.TEXT,
                    ),
                ],
                "description": "Blocking condition for missing certification",
                "sort_order": 3,
            },
            {
                "code": "COMP-004",
                "name": "Export Control",
                "category": ConditionCategory.COMPLIANCE,
                "condition_type": ConditionType.HARD_STOP,
                "scope": ConditionScope.QUALIFICATION,
                "template_text": "Export control review required. Product/destination may require {{license_type}} license.",
                "placeholders": [
                    Placeholder(
                        name="license_type",
                        display_label="License Type",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["ITAR", "EAR", "Dual-Use"],
                    ),
                ],
                "description": "Export control hard stop",
                "sort_order": 4,
            },
            
            # Warranty Templates
            {
                "code": "WTY-001",
                "name": "Standard Warranty",
                "category": ConditionCategory.WARRANTY,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Standard warranty period: {{months}} months from date of shipment.",
                "placeholders": [
                    Placeholder(
                        name="months",
                        display_label="Warranty Months",
                        placeholder_type=PlaceholderType.NUMBER,
                        default_value="12",
                        min_value=0,
                        max_value=60,
                    ),
                ],
                "description": "Standard warranty period",
                "sort_order": 1,
            },
            
            # Shipping Templates
            {
                "code": "SHIP-001",
                "name": "Incoterms",
                "category": ConditionCategory.SHIPPING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Shipping terms: {{incoterm}} {{location}}.",
                "placeholders": [
                    Placeholder(
                        name="incoterm",
                        display_label="Incoterm",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"],
                        default_value="EXW",
                    ),
                    Placeholder(
                        name="location",
                        display_label="Named Place",
                        placeholder_type=PlaceholderType.TEXT,
                    ),
                ],
                "description": "Incoterms shipping terms",
                "sort_order": 1,
            },
            
            # Tooling Templates
            {
                "code": "TOOL-001",
                "name": "Customer-Owned Tooling",
                "category": ConditionCategory.TOOLING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Tooling remains property of customer. Maintenance costs for tooling beyond normal wear are customer responsibility.",
                "placeholders": [],
                "description": "Customer tooling ownership terms",
                "sort_order": 1,
            },
            {
                "code": "TOOL-002",
                "name": "Amortized Tooling",
                "category": ConditionCategory.TOOLING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Tooling cost of {{currency}} {{amount}} amortized over {{quantity}} units. Shortfall payable if volume not achieved within {{months}} months.",
                "placeholders": [
                    Placeholder(
                        name="currency",
                        display_label="Currency",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["USD", "EUR", "GBP", "CAD"],
                        default_value="USD",
                    ),
                    Placeholder(
                        name="amount",
                        display_label="Tooling Cost",
                        placeholder_type=PlaceholderType.CURRENCY,
                        min_value=0,
                    ),
                    Placeholder(
                        name="quantity",
                        display_label="Amortization Quantity",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                    ),
                    Placeholder(
                        name="months",
                        display_label="Amortization Period (Months)",
                        placeholder_type=PlaceholderType.NUMBER,
                        default_value="24",
                        min_value=1,
                    ),
                ],
                "description": "Amortized tooling terms",
                "sort_order": 2,
            },
            
            # Packaging Templates
            {
                "code": "PKG-001",
                "name": "Standard Packaging",
                "category": ConditionCategory.PACKAGING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Standard industry packaging included in price.",
                "placeholders": [],
                "description": "Standard packaging terms",
                "sort_order": 1,
            },
            {
                "code": "PKG-002",
                "name": "Custom Packaging",
                "category": ConditionCategory.PACKAGING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Custom packaging per customer specification. Additional charge: {{currency}} {{amount}} per unit.",
                "placeholders": [
                    Placeholder(
                        name="currency",
                        display_label="Currency",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["USD", "EUR", "GBP", "CAD"],
                        default_value="USD",
                    ),
                    Placeholder(
                        name="amount",
                        display_label="Per-Unit Charge",
                        placeholder_type=PlaceholderType.CURRENCY,
                        min_value=0,
                    ),
                ],
                "description": "Custom packaging charge",
                "sort_order": 2,
            },
            
            # Testing Templates
            {
                "code": "TEST-001",
                "name": "100% Functional Test",
                "category": ConditionCategory.TESTING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "100% functional testing included per agreed test specification.",
                "placeholders": [],
                "description": "Full functional testing included",
                "sort_order": 1,
            },
            {
                "code": "TEST-002",
                "name": "Burn-In Testing",
                "category": ConditionCategory.TESTING,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "{{hours}}-hour burn-in testing: {{currency}} {{amount}} per unit additional.",
                "placeholders": [
                    Placeholder(
                        name="hours",
                        display_label="Burn-In Hours",
                        placeholder_type=PlaceholderType.NUMBER,
                        min_value=1,
                    ),
                    Placeholder(
                        name="currency",
                        display_label="Currency",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["USD", "EUR", "GBP", "CAD"],
                        default_value="USD",
                    ),
                    Placeholder(
                        name="amount",
                        display_label="Per-Unit Charge",
                        placeholder_type=PlaceholderType.CURRENCY,
                        min_value=0,
                    ),
                ],
                "description": "Burn-in testing charge",
                "sort_order": 2,
            },
            
            # Quality Templates
            {
                "code": "QA-001",
                "name": "Quality Standard",
                "category": ConditionCategory.QUALITY,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.UNIVERSAL,
                "template_text": "Manufacturing to {{standard}} quality management system.",
                "placeholders": [
                    Placeholder(
                        name="standard",
                        display_label="Quality Standard",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["ISO 9001", "AS9100", "IATF 16949", "ISO 13485"],
                        default_value="ISO 9001",
                    ),
                ],
                "description": "Quality management standard",
                "sort_order": 1,
            },
            {
                "code": "QA-002",
                "name": "AQL Inspection",
                "category": ConditionCategory.QUALITY,
                "condition_type": ConditionType.STANDARD,
                "scope": ConditionScope.QUOTE,
                "template_text": "Outgoing inspection to AQL {{level}}, general inspection level {{gi_level}}.",
                "placeholders": [
                    Placeholder(
                        name="level",
                        display_label="AQL Level",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["0.1", "0.25", "0.4", "0.65", "1.0", "1.5", "2.5", "4.0"],
                        default_value="1.0",
                    ),
                    Placeholder(
                        name="gi_level",
                        display_label="General Inspection Level",
                        placeholder_type=PlaceholderType.SELECT,
                        options=["I", "II", "III"],
                        default_value="II",
                    ),
                ],
                "description": "AQL inspection level",
                "sort_order": 2,
            },
        ]
        
        for default in defaults:
            template = ConditionTemplate(
                id=uuid4(),
                code=default["code"],
                name=default["name"],
                category=default["category"],
                condition_type=default["condition_type"],
                scope=default["scope"],
                template_text=default["template_text"],
                placeholders=default.get("placeholders", []),
                description=default.get("description"),
                is_default=True,
                sort_order=default.get("sort_order", 0),
            )
            self._templates[template.id] = template
            self._code_index[template.code] = template.id
        
        # Create default condition sets
        self._create_default_condition_sets()
    
    def _create_default_condition_sets(self) -> None:
        """Create default condition sets."""
        # Standard Quote Conditions
        standard_quote_codes = [
            "MOQ-001", "LT-001", "PV-001", "PT-001", "WTY-001", 
            "SHIP-001", "PKG-001", "TEST-001", "QA-001"
        ]
        standard_ids = [
            self._code_index[code] for code in standard_quote_codes
            if code in self._code_index
        ]
        
        if standard_ids:
            standard_set = ConditionSet(
                id=uuid4(),
                name="Standard Quote Conditions",
                description="Common conditions for standard quotes",
                condition_template_ids=standard_ids,
                is_default=True,
            )
            self._condition_sets[standard_set.id] = standard_set
        
        # New Customer Conditions
        new_customer_codes = ["PT-003", "PT-002"]
        new_customer_ids = [
            self._code_index[code] for code in new_customer_codes
            if code in self._code_index
        ]
        
        if new_customer_ids:
            new_customer_set = ConditionSet(
                id=uuid4(),
                name="New Customer Conditions",
                description="Additional conditions for new customers",
                condition_template_ids=new_customer_ids,
                is_default=True,
            )
            self._condition_sets[new_customer_set.id] = new_customer_set
        
        # Compliance Conditions
        compliance_codes = ["COMP-001", "COMP-002"]
        compliance_ids = [
            self._code_index[code] for code in compliance_codes
            if code in self._code_index
        ]
        
        if compliance_ids:
            compliance_set = ConditionSet(
                id=uuid4(),
                name="Compliance Statements",
                description="Standard compliance statements",
                condition_template_ids=compliance_ids,
                is_default=True,
            )
            self._condition_sets[compliance_set.id] = compliance_set


# Module-level service instance
_service: ConditionsLibraryService | None = None


def get_conditions_library_service() -> ConditionsLibraryService:
    """Get or create the conditions library service instance."""
    global _service
    if _service is None:
        _service = ConditionsLibraryService()
    return _service


def get_default_template_codes() -> list[str]:
    """Get a list of all default template codes."""
    service = get_conditions_library_service()
    return [t.code for t in service.list_templates() if t.is_default]


def get_default_condition_set_ids() -> list[UUID]:
    """Get IDs of all default condition sets."""
    service = get_conditions_library_service()
    return [s.id for s in service.list_condition_sets() if s.is_default]

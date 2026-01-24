"""
Template Cloning Service.

Provides functionality to clone entities, create entities from templates,
and duplicate records for reuse.

Features:
- Clone existing entities with customization
- Create entities from predefined templates
- Duplicate quotes from previous versions
- Create RFQs from templates
- Deep clone with relationships
- Field mapping and transformation
- Clone history tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.entity_providers import (
    build_entity_getter,
    build_entity_query,
    build_entity_saver,
)


class CloneableEntityType(str, Enum):
    """Entity types that can be cloned."""
    
    QUOTE = "quote"
    RFQ = "rfq"
    OPPORTUNITY = "opportunity"
    PRODUCT = "product"
    WORK_ORDER = "work_order"
    TASK = "task"
    CHECKLIST = "checklist"
    RISK = "risk"
    CAPA = "capa"
    PROJECT = "project"


class TemplateCategory(str, Enum):
    """Categories of templates."""
    
    QUOTE = "quote"
    RFQ = "rfq"
    PROJECT = "project"
    CHECKLIST = "checklist"
    PRODUCT = "product"
    WORK_ORDER = "work_order"
    PROCESS = "process"
    QUALITY = "quality"
    CUSTOM = "custom"


class CloneMode(str, Enum):
    """Modes for cloning."""
    
    SHALLOW = "shallow"  # Only the entity itself
    DEEP = "deep"  # Include related entities
    SELECTIVE = "selective"  # User-selected relations


@dataclass
class FieldMapping:
    """Mapping for field transformation during clone."""
    
    source_field: str
    target_field: str | None = None  # None means same as source
    transformation: str | None = None  # e.g., "increment", "reset", "prefix"
    default_value: Any = None  # Value to use if source is empty
    skip: bool = False  # Skip this field entirely


@dataclass
class CloneOptions:
    """Options for cloning an entity."""
    
    mode: CloneMode = CloneMode.SHALLOW
    
    # What to include
    include_attachments: bool = False
    include_comments: bool = False
    include_history: bool = False
    include_children: bool = False  # Child entities
    
    # Field handling
    field_mappings: list[FieldMapping] = field(default_factory=list)
    fields_to_reset: list[str] = field(default_factory=list)
    fields_to_skip: list[str] = field(default_factory=list)
    
    # Overrides
    field_overrides: dict[str, Any] = field(default_factory=dict)
    
    # Naming
    name_prefix: str = ""
    name_suffix: str = " (Copy)"
    
    # Assignment
    new_owner_id: UUID | None = None


@dataclass
class Template:
    """A reusable template for creating entities."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: TemplateCategory = TemplateCategory.CUSTOM
    entity_type: CloneableEntityType = CloneableEntityType.RFQ
    
    # Template data
    template_data: dict[str, Any] = field(default_factory=dict)
    default_values: dict[str, Any] = field(default_factory=dict)
    
    # Related templates for deep creation
    child_templates: list[UUID] = field(default_factory=list)
    
    # Metadata
    tags: list[str] = field(default_factory=list)
    is_system: bool = False  # System-provided vs user-created
    is_active: bool = True
    
    # Ownership
    created_by: UUID | None = None
    organization_id: UUID | None = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Usage tracking
    use_count: int = 0
    last_used_at: datetime | None = None


@dataclass
class CloneResult:
    """Result of a clone operation."""
    
    id: UUID = field(default_factory=uuid4)
    success: bool = True
    
    # Source and target
    source_id: UUID | None = None
    source_type: CloneableEntityType | None = None
    target_id: UUID | None = None
    
    # Clone info
    mode: CloneMode = CloneMode.SHALLOW
    template_id: UUID | None = None
    
    # Related clones
    cloned_children: dict[UUID, UUID] = field(default_factory=dict)  # source -> target
    
    # Timestamps
    cloned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cloned_by: UUID | None = None
    
    # Error handling
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class CloneHistory:
    """History of clone operations."""
    
    id: UUID = field(default_factory=uuid4)
    entity_id: UUID = field(default_factory=uuid4)
    entity_type: CloneableEntityType = CloneableEntityType.RFQ
    
    # Clone chain
    cloned_from_id: UUID | None = None
    cloned_to_ids: list[UUID] = field(default_factory=list)
    
    # Template info
    created_from_template_id: UUID | None = None
    created_from_template_name: str | None = None
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TemplateCloningService:
    """
    Service for cloning entities and creating from templates.
    
    Supports:
    - Duplicating existing entities
    - Creating from predefined templates
    - Deep cloning with relationships
    - Clone history tracking
    """
    
    def __init__(
        self,
        entity_provider: callable | None = None,
        entity_saver: callable | None = None,
        entity_query: callable | None = None,
    ) -> None:
        """Initialize the service."""
        self._templates: dict[UUID, Template] = {}
        self._clone_history: dict[UUID, CloneHistory] = {}
        self._entity_provider = entity_provider
        self._entity_saver = entity_saver
        self._entity_query = entity_query
        
        # Default fields to reset on clone
        self._reset_fields: dict[CloneableEntityType, list[str]] = {
            CloneableEntityType.QUOTE: [
                "status", "submitted_at", "approved_at", "approved_by",
                "version", "is_current", "quote_number",
            ],
            CloneableEntityType.RFQ: [
                "status", "received_at", "due_date", "assigned_to",
                "rfq_number",
            ],
            CloneableEntityType.OPPORTUNITY: [
                "status", "stage", "won_at", "lost_at", "probability",
            ],
            CloneableEntityType.WORK_ORDER: [
                "status", "started_at", "completed_at", "work_order_number",
            ],
            CloneableEntityType.TASK: [
                "status", "started_at", "completed_at", "completed_by",
            ],
            CloneableEntityType.CHECKLIST: [
                "status", "approved_at", "approved_by",
            ],
            CloneableEntityType.RISK: [
                "status", "occurred", "occurred_at", "mitigated_at",
            ],
            CloneableEntityType.CAPA: [
                "status", "closed_at", "verified_at",
            ],
            CloneableEntityType.PRODUCT: [
                "status", "released_at",
            ],
            CloneableEntityType.PROJECT: [
                "status", "stage", "started_at", "completed_at",
            ],
        }
        
        # Initialize default templates
        self._init_default_templates()
    
    def _init_default_templates(self) -> None:
        """Initialize default system templates."""
        # Standard RFQ Template
        self.create_template(
            name="Standard RFQ",
            description="Standard request for quote template",
            category=TemplateCategory.RFQ,
            entity_type=CloneableEntityType.RFQ,
            template_data={
                "type": "standard",
                "priority": "normal",
                "sections": ["requirements", "specifications", "timeline", "terms"],
            },
            default_values={
                "status": "draft",
                "priority": "normal",
            },
            is_system=True,
            tags=["standard", "general"],
        )
        
        # Urgent RFQ Template
        self.create_template(
            name="Urgent RFQ",
            description="Template for time-sensitive requests",
            category=TemplateCategory.RFQ,
            entity_type=CloneableEntityType.RFQ,
            template_data={
                "type": "urgent",
                "priority": "high",
                "fast_track": True,
            },
            default_values={
                "status": "draft",
                "priority": "high",
                "fast_track": True,
            },
            is_system=True,
            tags=["urgent", "priority"],
        )
        
        # Standard Quote Template
        self.create_template(
            name="Standard Quote",
            description="Standard quotation template",
            category=TemplateCategory.QUOTE,
            entity_type=CloneableEntityType.QUOTE,
            template_data={
                "type": "standard",
                "sections": ["items", "pricing", "terms", "validity"],
                "validity_days": 30,
            },
            default_values={
                "status": "draft",
                "version": 1,
                "validity_days": 30,
            },
            is_system=True,
            tags=["standard", "pricing"],
        )
        
        # Revision Quote Template
        self.create_template(
            name="Quote Revision",
            description="Template for quote revisions",
            category=TemplateCategory.QUOTE,
            entity_type=CloneableEntityType.QUOTE,
            template_data={
                "type": "revision",
                "inherit_line_items": True,
                "inherit_pricing": True,
            },
            default_values={
                "status": "draft",
                "is_revision": True,
            },
            is_system=True,
            tags=["revision", "update"],
        )
        
        # NPI Project Template
        self.create_template(
            name="NPI Project",
            description="New Product Introduction project template",
            category=TemplateCategory.PROJECT,
            entity_type=CloneableEntityType.PROJECT,
            template_data={
                "type": "npi",
                "stages": ["intake", "dfm", "prototype", "pilot", "sop"],
                "default_checklists": ["supplier_readiness", "ppap_lite"],
            },
            default_values={
                "status": "draft",
                "stage": "intake",
                "project_type": "npi",
            },
            is_system=True,
            tags=["npi", "product", "launch"],
        )
        
        # Standard Work Order Template
        self.create_template(
            name="Standard Work Order",
            description="Standard work order template",
            category=TemplateCategory.WORK_ORDER,
            entity_type=CloneableEntityType.WORK_ORDER,
            template_data={
                "type": "standard",
                "sections": ["description", "materials", "steps", "quality_checks"],
            },
            default_values={
                "status": "draft",
                "priority": "normal",
            },
            is_system=True,
            tags=["standard", "manufacturing"],
        )
    
    # ---------------------
    # Template Management
    # ---------------------
    
    def create_template(
        self,
        name: str,
        category: TemplateCategory,
        entity_type: CloneableEntityType,
        description: str = "",
        template_data: dict[str, Any] | None = None,
        default_values: dict[str, Any] | None = None,
        is_system: bool = False,
        tags: list[str] | None = None,
        created_by: UUID | None = None,
        organization_id: UUID | None = None,
    ) -> Template:
        """Create a new template."""
        template = Template(
            name=name,
            description=description,
            category=category,
            entity_type=entity_type,
            template_data=template_data or {},
            default_values=default_values or {},
            is_system=is_system,
            tags=tags or [],
            created_by=created_by,
            organization_id=organization_id,
        )
        
        self._templates[template.id] = template
        return template
    
    def get_template(self, template_id: UUID) -> Template | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_templates(
        self,
        category: TemplateCategory | None = None,
        entity_type: CloneableEntityType | None = None,
        include_inactive: bool = False,
        organization_id: UUID | None = None,
    ) -> list[Template]:
        """Get templates with optional filtering."""
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if entity_type:
            templates = [t for t in templates if t.entity_type == entity_type]
        
        if not include_inactive:
            templates = [t for t in templates if t.is_active]
        
        if organization_id:
            templates = [
                t for t in templates
                if t.organization_id == organization_id or t.is_system
            ]
        
        return sorted(templates, key=lambda t: (not t.is_system, t.name))
    
    def update_template(
        self,
        template_id: UUID,
        **updates: Any,
    ) -> Template | None:
        """Update a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        if template.is_system:
            # Only allow limited updates to system templates
            allowed = {"is_active", "tags"}
            updates = {k: v for k, v in updates.items() if k in allowed}
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now(timezone.utc)
        return template
    
    def delete_template(self, template_id: UUID) -> bool:
        """Delete a template (soft delete for system templates)."""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        if template.is_system:
            # Soft delete system templates
            template.is_active = False
            return True
        
        del self._templates[template_id]
        return True
    
    def search_templates(
        self,
        query: str,
        category: TemplateCategory | None = None,
    ) -> list[Template]:
        """Search templates by name or description."""
        query = query.lower()
        templates = self.get_templates(category=category)
        
        results = []
        for template in templates:
            if (
                query in template.name.lower()
                or query in template.description.lower()
                or any(query in tag.lower() for tag in template.tags)
            ):
                results.append(template)
        
        return results
    
    # ---------------------
    # Clone Operations
    # ---------------------
    
    def clone_entity(
        self,
        entity_type: CloneableEntityType,
        entity_id: UUID,
        options: CloneOptions | None = None,
        cloned_by: UUID | None = None,
    ) -> CloneResult:
        """Clone an existing entity."""
        options = options or CloneOptions()
        
        # Get source entity
        source = self._get_entity(entity_type, entity_id)
        if not source:
            return CloneResult(
                success=False,
                source_id=entity_id,
                source_type=entity_type,
                error_message="Source entity not found",
                cloned_by=cloned_by,
            )
        
        # Clone the entity
        cloned_data = self._apply_clone(source, entity_type, options)
        
        # Create new entity
        new_id = uuid4()
        cloned_data["id"] = new_id
        cloned_data["created_at"] = datetime.now(timezone.utc)
        cloned_data["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, new_id, cloned_data)
        
        # Track clone history
        self._record_clone_history(
            source_id=entity_id,
            target_id=new_id,
            entity_type=entity_type,
        )
        
        # Handle children if deep clone
        cloned_children = {}
        if options.mode == CloneMode.DEEP and options.include_children:
            cloned_children = self._clone_children(
                entity_type, entity_id, new_id, options, cloned_by,
            )
        
        result = CloneResult(
            success=True,
            source_id=entity_id,
            source_type=entity_type,
            target_id=new_id,
            mode=options.mode,
            cloned_children=cloned_children,
            cloned_by=cloned_by,
        )
        
        return result
    
    def _apply_clone(
        self,
        source: dict[str, Any],
        entity_type: CloneableEntityType,
        options: CloneOptions,
    ) -> dict[str, Any]:
        """Apply clone transformations to source data."""
        cloned = dict(source)
        
        # Apply field mappings
        for mapping in options.field_mappings:
            if mapping.skip:
                cloned.pop(mapping.source_field, None)
                continue
            
            target = mapping.target_field or mapping.source_field
            value = source.get(mapping.source_field, mapping.default_value)
            
            if mapping.transformation == "increment":
                value = (value or 0) + 1
            elif mapping.transformation == "reset":
                value = mapping.default_value
            elif mapping.transformation == "prefix" and isinstance(value, str):
                value = f"Copy of {value}"
            
            cloned[target] = value
        
        # Reset specified fields
        fields_to_reset = options.fields_to_reset or self._reset_fields.get(entity_type, [])
        for field_name in fields_to_reset:
            if field_name in cloned:
                cloned[field_name] = None
        
        # Skip specified fields
        for field_name in options.fields_to_skip:
            cloned.pop(field_name, None)
        
        # Apply overrides
        cloned.update(options.field_overrides)
        
        # Handle name
        if "name" in cloned:
            name = cloned["name"]
            cloned["name"] = f"{options.name_prefix}{name}{options.name_suffix}"
        
        # Update owner if specified
        if options.new_owner_id:
            cloned["owner_id"] = options.new_owner_id
        
        # Reset status-related fields
        cloned["status"] = "draft"
        
        # Clear IDs and timestamps that should be regenerated
        cloned.pop("id", None)
        cloned.pop("created_at", None)
        cloned.pop("updated_at", None)
        
        return cloned
    
    def _clone_children(
        self,
        parent_type: CloneableEntityType,
        source_parent_id: UUID,
        target_parent_id: UUID,
        options: CloneOptions,
        cloned_by: UUID | None,
    ) -> dict[UUID, UUID]:
        """Clone child entities."""
        cloned_children: dict[UUID, UUID] = {}
        
        # Get child entity relationships
        child_relationships = self._get_child_relationships(parent_type)
        
        for child_type, parent_field in child_relationships:
            children = self._get_children(child_type, parent_field, source_parent_id)
            
            for child in children:
                child_options = CloneOptions(
                    mode=CloneMode.SHALLOW,
                    name_suffix="",
                    field_overrides={parent_field: target_parent_id},
                )
                
                result = self.clone_entity(
                    child_type,
                    child["id"],
                    child_options,
                    cloned_by,
                )
                
                if result.success and result.target_id:
                    cloned_children[child["id"]] = result.target_id
        
        return cloned_children
    
    def _get_child_relationships(
        self,
        parent_type: CloneableEntityType,
    ) -> list[tuple[CloneableEntityType, str]]:
        """Get child entity relationships for a parent type."""
        relationships = {
            CloneableEntityType.QUOTE: [
                (CloneableEntityType.TASK, "quote_id"),
            ],
            CloneableEntityType.RFQ: [
                (CloneableEntityType.QUOTE, "rfq_id"),
            ],
            CloneableEntityType.PROJECT: [
                (CloneableEntityType.CHECKLIST, "project_id"),
                (CloneableEntityType.RISK, "project_id"),
                (CloneableEntityType.TASK, "project_id"),
            ],
            CloneableEntityType.WORK_ORDER: [
                (CloneableEntityType.TASK, "work_order_id"),
            ],
        }
        return relationships.get(parent_type, [])
    
    def _get_children(
        self,
        child_type: CloneableEntityType,
        parent_field: str,
        parent_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get child entities for a parent."""
        if not self._entity_query:
            raise ValueError("TemplateCloningService requires an entity_query in production")
        return self._entity_query(child_type, {parent_field: parent_id})
    
    # ---------------------
    # Create from Template
    # ---------------------
    
    def create_from_template(
        self,
        template_id: UUID,
        overrides: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> CloneResult:
        """Create a new entity from a template."""
        template = self._templates.get(template_id)
        if not template:
            return CloneResult(
                success=False,
                error_message="Template not found",
                cloned_by=created_by,
            )
        
        # Merge template data with defaults
        entity_data = {
            **template.template_data,
            **template.default_values,
            **(overrides or {}),
        }
        
        # Create entity
        entity_id = uuid4()
        entity_data["id"] = entity_id
        entity_data["created_at"] = datetime.now(timezone.utc)
        entity_data["updated_at"] = datetime.now(timezone.utc)
        entity_data["created_from_template_id"] = template_id
        
        self._save_entity(template.entity_type, entity_id, entity_data)
        
        # Update template usage
        template.use_count += 1
        template.last_used_at = datetime.now(timezone.utc)
        
        # Track history
        history = CloneHistory(
            entity_id=entity_id,
            entity_type=template.entity_type,
            created_from_template_id=template_id,
            created_from_template_name=template.name,
        )
        self._clone_history[entity_id] = history
        
        return CloneResult(
            success=True,
            target_id=entity_id,
            source_type=template.entity_type,
            template_id=template_id,
            cloned_by=created_by,
        )
    
    # ---------------------
    # Quote Versioning
    # ---------------------
    
    def create_quote_revision(
        self,
        quote_id: UUID,
        created_by: UUID | None = None,
    ) -> CloneResult:
        """Create a new revision of an existing quote."""
        source_quote = self._get_entity(CloneableEntityType.QUOTE, quote_id)
        if not source_quote:
            return CloneResult(
                success=False,
                source_id=quote_id,
                source_type=CloneableEntityType.QUOTE,
                error_message="Quote not found",
                cloned_by=created_by,
            )
        
        # Get current version
        current_version = source_quote.get("version", 1)
        
        # Clone with revision settings
        options = CloneOptions(
            name_suffix="",
            fields_to_reset=[
                "status", "submitted_at", "approved_at", "approved_by",
                "is_current", "quote_number",
            ],
            field_overrides={
                "version": current_version + 1,
                "parent_quote_id": quote_id,
                "is_revision": True,
                "previous_version_id": quote_id,
            },
        )
        
        result = self.clone_entity(
            CloneableEntityType.QUOTE,
            quote_id,
            options,
            created_by,
        )
        
        # Mark previous as not current
        if result.success and result.target_id:
            source_quote["is_current"] = False
            self._save_entity(CloneableEntityType.QUOTE, quote_id, source_quote)
            
            # Mark new as current
            new_quote = self._get_entity(CloneableEntityType.QUOTE, result.target_id)
            if new_quote:
                new_quote["is_current"] = True
                self._save_entity(CloneableEntityType.QUOTE, result.target_id, new_quote)
        
        return result
    
    def get_quote_versions(
        self,
        quote_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all versions of a quote chain."""
        versions: list[dict[str, Any]] = []
        
        # Find the root quote
        current = self._get_entity(CloneableEntityType.QUOTE, quote_id)
        if not current:
            return versions
        
        # Walk back to find root
        root_id = quote_id
        while current and current.get("previous_version_id"):
            root_id = current["previous_version_id"]
            current = self._get_entity(CloneableEntityType.QUOTE, root_id)
        
        # Now walk forward to get all versions
        versions = [current] if current else []
        
        # Find all quotes that reference this as previous version
        def find_next_versions(parent_id: UUID) -> list[dict[str, Any]]:
            if not self._entity_query:
                raise ValueError("TemplateCloningService requires an entity_query in production")
            nexts = self._entity_query(CloneableEntityType.QUOTE, {"previous_version_id": parent_id})
            expanded: list[dict[str, Any]] = []
            for entity in nexts:
                expanded.append(entity)
                expanded.extend(find_next_versions(entity["id"]))
            return expanded
        
        versions.extend(find_next_versions(root_id))
        
        return sorted(versions, key=lambda q: q.get("version", 1))
    
    # ---------------------
    # Clone History
    # ---------------------
    
    def _record_clone_history(
        self,
        source_id: UUID,
        target_id: UUID,
        entity_type: CloneableEntityType,
    ) -> None:
        """Record clone operation in history."""
        # Update source history
        if source_id in self._clone_history:
            self._clone_history[source_id].cloned_to_ids.append(target_id)
        else:
            self._clone_history[source_id] = CloneHistory(
                entity_id=source_id,
                entity_type=entity_type,
                cloned_to_ids=[target_id],
            )
        
        # Create target history
        self._clone_history[target_id] = CloneHistory(
            entity_id=target_id,
            entity_type=entity_type,
            cloned_from_id=source_id,
        )
    
    def get_clone_history(
        self,
        entity_id: UUID,
    ) -> CloneHistory | None:
        """Get clone history for an entity."""
        return self._clone_history.get(entity_id)
    
    def get_clone_chain(
        self,
        entity_id: UUID,
    ) -> list[UUID]:
        """Get the full clone chain for an entity."""
        chain = [entity_id]
        history = self._clone_history.get(entity_id)
        
        if not history:
            return chain
        
        # Walk back to source
        current_id = history.cloned_from_id
        while current_id:
            chain.insert(0, current_id)
            h = self._clone_history.get(current_id)
            if not h:
                break
            current_id = h.cloned_from_id
        
        # Walk forward to all clones
        def add_descendants(parent_id: UUID) -> None:
            h = self._clone_history.get(parent_id)
            if h:
                for clone_id in h.cloned_to_ids:
                    chain.append(clone_id)
                    add_descendants(clone_id)
        
        add_descendants(entity_id)
        
        return chain
    
    # ---------------------
    # Entity Provider
    # ---------------------
    
    def _get_entity(
        self,
        entity_type: CloneableEntityType,
        entity_id: UUID,
    ) -> dict[str, Any] | None:
        """Get an entity snapshot."""
        if not self._entity_provider:
            raise ValueError("TemplateCloningService requires an entity_provider in production")
        return self._entity_provider(entity_type, entity_id)
    
    def _save_entity(
        self,
        entity_type: CloneableEntityType,
        entity_id: UUID,
        entity: dict[str, Any],
    ) -> None:
        """Persist an entity snapshot."""
        if not self._entity_saver:
            raise ValueError("TemplateCloningService requires an entity_saver in production")
        self._entity_saver(entity_type, entity_id, entity)


def get_template_cloning_service(session: AsyncSession) -> TemplateCloningService:
    """Create a template cloning service wired to the database."""
    sync_session = session.sync_session
    return TemplateCloningService(
        entity_provider=build_entity_getter(sync_session),
        entity_saver=build_entity_saver(sync_session),
        entity_query=build_entity_query(sync_session),
    )

"""
Audit Trail Timeline Service.

Provides comprehensive object-level change history with timeline view,
field-level diffs, and relationship tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class ChangeType(Enum):
    """Type of change made to an entity."""
    
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    RESTORE = "restore"
    STATUS_CHANGE = "status_change"
    OWNER_CHANGE = "owner_change"
    LINK_ADD = "link_add"
    LINK_REMOVE = "link_remove"
    ATTACHMENT_ADD = "attachment_add"
    ATTACHMENT_REMOVE = "attachment_remove"
    COMMENT_ADD = "comment_add"
    APPROVAL = "approval"
    REJECTION = "rejection"
    ESCALATION = "escalation"


class EntityType(Enum):
    """Types of entities that can be audited."""
    
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    QUOTE = "quote"
    QUALIFICATION = "qualification"
    ACCOUNT = "account"
    CONTACT = "contact"
    TASK = "task"
    A3 = "a3"
    ANDON = "andon"
    CTQ = "ctq"
    CAPA = "capa"
    NC = "nc"
    TRAINING = "training"
    WORK_ORDER = "work_order"
    PRODUCT = "product"
    KANBAN = "kanban"
    OBEYA = "obeya"
    USER = "user"
    STANDARD_WORK = "standard_work"


class FieldType(Enum):
    """Types of fields for formatting."""
    
    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    ENUM = "enum"
    UUID = "uuid"
    JSON = "json"
    LIST = "list"


class RelationshipType(Enum):
    """Types of relationships between entities."""
    
    PARENT = "parent"
    CHILD = "child"
    LINKED = "linked"
    ATTACHED = "attached"
    REFERENCED = "referenced"
    CAUSED_BY = "caused_by"
    RESULTED_IN = "resulted_in"


class AccessLevel(Enum):
    """Access levels for viewing audit trails."""
    
    PUBLIC = "public"  # Anyone can see
    TEAM = "team"  # Team members only
    OWNER = "owner"  # Owner/assignee only
    ADMIN = "admin"  # Admins only


@dataclass
class FieldChange:
    """Represents a change to a single field."""
    
    field_name: str
    field_label: str
    field_type: FieldType
    old_value: Any
    new_value: Any
    old_display: Optional[str] = None
    new_display: Optional[str] = None
    is_sensitive: bool = False  # If true, mask values
    
    def __post_init__(self) -> None:
        """Format display values if not provided."""
        if self.old_display is None:
            self.old_display = self._format_value(self.old_value)
        if self.new_display is None:
            self.new_display = self._format_value(self.new_value)
    
    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return "(empty)"
        
        if self.is_sensitive:
            return "****"
        
        if self.field_type == FieldType.BOOLEAN:
            return "Yes" if value else "No"
        
        if self.field_type == FieldType.CURRENCY:
            return f"${value:,.2f}" if isinstance(value, (int, float)) else str(value)
        
        if self.field_type == FieldType.DATE:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            return str(value)
        
        if self.field_type == FieldType.DATETIME:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            return str(value)
        
        if self.field_type == FieldType.LIST:
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)
        
        return str(value)


@dataclass
class RelatedEntity:
    """Represents a related entity in the timeline."""
    
    entity_id: UUID
    entity_type: EntityType
    entity_name: str
    relationship: RelationshipType
    linked_at: datetime = field(default_factory=datetime.utcnow)
    linked_by: Optional[UUID] = None


@dataclass
class AuditEntry:
    """A single entry in the audit trail."""
    
    id: UUID
    entity_id: UUID
    entity_type: EntityType
    entity_name: str
    change_type: ChangeType
    changed_at: datetime
    changed_by: UUID
    changed_by_name: str
    changes: list[FieldChange] = field(default_factory=list)
    summary: str = ""
    details: Optional[str] = None
    related_entities: list[RelatedEntity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    access_level: AccessLevel = AccessLevel.PUBLIC
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Generate summary if not provided."""
        if not self.summary:
            self.summary = self._generate_summary()
    
    def _generate_summary(self) -> str:
        """Generate a human-readable summary."""
        if self.change_type == ChangeType.CREATE:
            return f"Created {self.entity_type.value}"
        
        if self.change_type == ChangeType.DELETE:
            return f"Deleted {self.entity_type.value}"
        
        if self.change_type == ChangeType.STATUS_CHANGE:
            for change in self.changes:
                if change.field_name == "status":
                    return f"Changed status from {change.old_display} to {change.new_display}"
            return "Changed status"
        
        if self.change_type == ChangeType.OWNER_CHANGE:
            for change in self.changes:
                if change.field_name in ("owner_id", "assigned_to"):
                    return f"Changed owner to {change.new_display}"
            return "Changed owner"
        
        if self.change_type == ChangeType.LINK_ADD:
            if self.related_entities:
                rel = self.related_entities[0]
                return f"Linked to {rel.entity_type.value}: {rel.entity_name}"
            return "Added relationship"
        
        if self.change_type == ChangeType.LINK_REMOVE:
            if self.related_entities:
                rel = self.related_entities[0]
                return f"Unlinked from {rel.entity_type.value}: {rel.entity_name}"
            return "Removed relationship"
        
        if self.change_type == ChangeType.APPROVAL:
            return "Approved"
        
        if self.change_type == ChangeType.REJECTION:
            return "Rejected"
        
        if self.change_type == ChangeType.ESCALATION:
            return "Escalated"
        
        if self.change_type == ChangeType.UPDATE:
            if len(self.changes) == 1:
                change = self.changes[0]
                return f"Updated {change.field_label}"
            return f"Updated {len(self.changes)} fields"
        
        return f"{self.change_type.value.replace('_', ' ').title()}"


@dataclass
class TimelineGroup:
    """A group of entries for a time period."""
    
    date: datetime
    date_label: str
    entries: list[AuditEntry] = field(default_factory=list)
    
    @property
    def count(self) -> int:
        """Number of entries in this group."""
        return len(self.entries)


@dataclass
class Timeline:
    """Complete timeline for an entity or set of entities."""
    
    entity_id: Optional[UUID]  # None if aggregated timeline
    entity_type: Optional[EntityType]
    entity_name: Optional[str]
    groups: list[TimelineGroup] = field(default_factory=list)
    total_entries: int = 0
    has_more: bool = False
    oldest_entry_date: Optional[datetime] = None
    newest_entry_date: Optional[datetime] = None


@dataclass
class TimelineFilter:
    """Filters for timeline queries."""
    
    entity_ids: Optional[list[UUID]] = None
    entity_types: Optional[list[EntityType]] = None
    change_types: Optional[list[ChangeType]] = None
    changed_by: Optional[list[UUID]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search_text: Optional[str] = None
    include_related: bool = False
    access_levels: Optional[list[AccessLevel]] = None


@dataclass
class TimelineConfig:
    """Configuration for the timeline service."""
    
    default_page_size: int = 50
    max_page_size: int = 500
    group_by_date: bool = True
    include_metadata: bool = False
    mask_sensitive_fields: bool = True
    retention_days: int = 365 * 5  # 5 years default


@dataclass
class DiffResult:
    """Result of comparing two entity states."""
    
    entity_id: UUID
    entity_type: EntityType
    old_state: dict[str, Any]
    new_state: dict[str, Any]
    changes: list[FieldChange]
    has_changes: bool = False
    
    def __post_init__(self) -> None:
        """Set has_changes based on changes list."""
        self.has_changes = len(self.changes) > 0


# Field metadata for common entity fields
FIELD_METADATA: dict[str, tuple[str, FieldType]] = {
    # Common fields
    "id": ("ID", FieldType.UUID),
    "name": ("Name", FieldType.TEXT),
    "title": ("Title", FieldType.TEXT),
    "description": ("Description", FieldType.TEXT),
    "status": ("Status", FieldType.ENUM),
    "priority": ("Priority", FieldType.ENUM),
    "created_at": ("Created At", FieldType.DATETIME),
    "updated_at": ("Updated At", FieldType.DATETIME),
    "created_by": ("Created By", FieldType.UUID),
    "owner_id": ("Owner", FieldType.UUID),
    "assigned_to": ("Assigned To", FieldType.UUID),
    
    # Quote/RFQ fields
    "total_value": ("Total Value", FieldType.CURRENCY),
    "unit_price": ("Unit Price", FieldType.CURRENCY),
    "quantity": ("Quantity", FieldType.NUMBER),
    "due_date": ("Due Date", FieldType.DATE),
    "valid_until": ("Valid Until", FieldType.DATE),
    "margin": ("Margin", FieldType.NUMBER),
    
    # Task fields
    "completed": ("Completed", FieldType.BOOLEAN),
    "completed_at": ("Completed At", FieldType.DATETIME),
    
    # A3/CAPA fields
    "root_cause": ("Root Cause", FieldType.TEXT),
    "countermeasures": ("Countermeasures", FieldType.TEXT),
    "is_effective": ("Is Effective", FieldType.BOOLEAN),
}


class AuditTrailTimelineService:
    """
    Service for managing audit trail and timeline views.
    
    Features:
    - Record changes to any entity
    - Field-level diff tracking
    - Timeline aggregation and grouping
    - Relationship tracking
    - Filtering and search
    - Access control
    """
    
    def __init__(self, config: Optional[TimelineConfig] = None) -> None:
        """Initialize the service."""
        self.config = config or TimelineConfig()
        
        # In-memory storage
        self._entries: dict[UUID, AuditEntry] = {}
        self._by_entity: dict[UUID, list[UUID]] = {}  # entity_id -> list of entry_ids
        self._by_user: dict[UUID, list[UUID]] = {}  # user_id -> list of entry_ids
        self._field_metadata: dict[str, tuple[str, FieldType]] = FIELD_METADATA.copy()
    
    # Field Metadata Management
    
    def register_field(
        self,
        field_name: str,
        label: str,
        field_type: FieldType,
    ) -> None:
        """Register field metadata for formatting."""
        self._field_metadata[field_name] = (label, field_type)
    
    def get_field_metadata(self, field_name: str) -> tuple[str, FieldType]:
        """Get field metadata, with defaults for unknown fields."""
        if field_name in self._field_metadata:
            return self._field_metadata[field_name]
        
        # Generate default label from field name
        label = field_name.replace("_", " ").title()
        return (label, FieldType.TEXT)
    
    # Diff Calculation
    
    def calculate_diff(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
        exclude_fields: Optional[list[str]] = None,
        sensitive_fields: Optional[list[str]] = None,
    ) -> DiffResult:
        """Calculate differences between two entity states."""
        exclude = set(exclude_fields or [])
        exclude.update({"id", "created_at", "updated_at"})  # Always exclude
        
        sensitive = set(sensitive_fields or [])
        sensitive.update({"password", "token", "secret", "api_key"})
        
        changes: list[FieldChange] = []
        
        # Find all unique keys
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            if key in exclude:
                continue
            
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            
            # Check if values are different
            if old_val != new_val:
                label, field_type = self.get_field_metadata(key)
                is_sensitive = key in sensitive
                
                change = FieldChange(
                    field_name=key,
                    field_label=label,
                    field_type=field_type,
                    old_value=old_val,
                    new_value=new_val,
                    is_sensitive=is_sensitive,
                )
                changes.append(change)
        
        return DiffResult(
            entity_id=entity_id,
            entity_type=entity_type,
            old_state=old_state,
            new_state=new_state,
            changes=changes,
        )
    
    # Entry Recording
    
    def record_create(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        created_by: UUID,
        created_by_name: str,
        initial_state: Optional[dict[str, Any]] = None,
        related_entities: Optional[list[RelatedEntity]] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEntry:
        """Record entity creation."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.CREATE,
            changed_at=datetime.utcnow(),
            changed_by=created_by,
            changed_by_name=created_by_name,
            changes=[],
            summary=f"Created {entity_type.value}: {entity_name}",
            related_entities=related_entities or [],
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if initial_state:
            entry.metadata["initial_state"] = initial_state
        
        self._store_entry(entry)
        return entry
    
    def record_update(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        updated_by: UUID,
        updated_by_name: str,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
        exclude_fields: Optional[list[str]] = None,
        related_entities: Optional[list[RelatedEntity]] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[AuditEntry]:
        """Record entity update with diff."""
        diff = self.calculate_diff(
            entity_id=entity_id,
            entity_type=entity_type,
            old_state=old_state,
            new_state=new_state,
            exclude_fields=exclude_fields,
        )
        
        if not diff.has_changes:
            return None
        
        # Determine change type
        change_type = ChangeType.UPDATE
        if any(c.field_name == "status" for c in diff.changes):
            change_type = ChangeType.STATUS_CHANGE
        elif any(c.field_name in ("owner_id", "assigned_to") for c in diff.changes):
            change_type = ChangeType.OWNER_CHANGE
        
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=change_type,
            changed_at=datetime.utcnow(),
            changed_by=updated_by,
            changed_by_name=updated_by_name,
            changes=diff.changes,
            related_entities=related_entities or [],
            metadata=metadata or {},
            ip_address=ip_address,
        )
        
        self._store_entry(entry)
        return entry
    
    def record_delete(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        deleted_by: UUID,
        deleted_by_name: str,
        final_state: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record entity deletion."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.DELETE,
            changed_at=datetime.utcnow(),
            changed_by=deleted_by,
            changed_by_name=deleted_by_name,
            summary=f"Deleted {entity_type.value}: {entity_name}",
            metadata=metadata or {},
        )
        
        if final_state:
            entry.metadata["final_state"] = final_state
        
        self._store_entry(entry)
        return entry
    
    def record_link(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        linked_by: UUID,
        linked_by_name: str,
        related_entity: RelatedEntity,
        is_add: bool = True,
    ) -> AuditEntry:
        """Record a link being added or removed."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.LINK_ADD if is_add else ChangeType.LINK_REMOVE,
            changed_at=datetime.utcnow(),
            changed_by=linked_by,
            changed_by_name=linked_by_name,
            related_entities=[related_entity],
        )
        
        self._store_entry(entry)
        return entry
    
    def record_attachment(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        user_id: UUID,
        user_name: str,
        attachment_name: str,
        attachment_id: UUID,
        is_add: bool = True,
    ) -> AuditEntry:
        """Record an attachment being added or removed."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.ATTACHMENT_ADD if is_add else ChangeType.ATTACHMENT_REMOVE,
            changed_at=datetime.utcnow(),
            changed_by=user_id,
            changed_by_name=user_name,
            summary=f"{'Added' if is_add else 'Removed'} attachment: {attachment_name}",
            metadata={"attachment_id": str(attachment_id), "attachment_name": attachment_name},
        )
        
        self._store_entry(entry)
        return entry
    
    def record_comment(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        user_id: UUID,
        user_name: str,
        comment_text: str,
        comment_id: UUID,
    ) -> AuditEntry:
        """Record a comment being added."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.COMMENT_ADD,
            changed_at=datetime.utcnow(),
            changed_by=user_id,
            changed_by_name=user_name,
            summary=f"Added comment",
            details=comment_text[:200] + "..." if len(comment_text) > 200 else comment_text,
            metadata={"comment_id": str(comment_id)},
        )
        
        self._store_entry(entry)
        return entry
    
    def record_approval(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        approved_by: UUID,
        approved_by_name: str,
        approval_type: str,
        notes: Optional[str] = None,
    ) -> AuditEntry:
        """Record an approval action."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.APPROVAL,
            changed_at=datetime.utcnow(),
            changed_by=approved_by,
            changed_by_name=approved_by_name,
            summary=f"Approved: {approval_type}",
            details=notes,
        )
        
        self._store_entry(entry)
        return entry
    
    def record_rejection(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        rejected_by: UUID,
        rejected_by_name: str,
        rejection_reason: str,
    ) -> AuditEntry:
        """Record a rejection action."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.REJECTION,
            changed_at=datetime.utcnow(),
            changed_by=rejected_by,
            changed_by_name=rejected_by_name,
            summary="Rejected",
            details=rejection_reason,
        )
        
        self._store_entry(entry)
        return entry
    
    def record_escalation(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        escalated_by: UUID,
        escalated_by_name: str,
        escalation_level: str,
        reason: str,
    ) -> AuditEntry:
        """Record an escalation action."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=ChangeType.ESCALATION,
            changed_at=datetime.utcnow(),
            changed_by=escalated_by,
            changed_by_name=escalated_by_name,
            summary=f"Escalated to level: {escalation_level}",
            details=reason,
            metadata={"escalation_level": escalation_level},
        )
        
        self._store_entry(entry)
        return entry
    
    def record_custom(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        entity_name: str,
        change_type: ChangeType,
        user_id: UUID,
        user_name: str,
        summary: str,
        changes: Optional[list[FieldChange]] = None,
        details: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record a custom audit entry."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            change_type=change_type,
            changed_at=datetime.utcnow(),
            changed_by=user_id,
            changed_by_name=user_name,
            changes=changes or [],
            summary=summary,
            details=details,
            metadata=metadata or {},
        )
        
        self._store_entry(entry)
        return entry
    
    def _store_entry(self, entry: AuditEntry) -> None:
        """Store an entry and update indices."""
        self._entries[entry.id] = entry
        
        # Index by entity
        if entry.entity_id not in self._by_entity:
            self._by_entity[entry.entity_id] = []
        self._by_entity[entry.entity_id].append(entry.id)
        
        # Index by user
        if entry.changed_by not in self._by_user:
            self._by_user[entry.changed_by] = []
        self._by_user[entry.changed_by].append(entry.id)
    
    # Entry Retrieval
    
    def get_entry(self, entry_id: UUID) -> Optional[AuditEntry]:
        """Get a single audit entry by ID."""
        return self._entries.get(entry_id)
    
    def get_entity_history(
        self,
        entity_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0,
        change_types: Optional[list[ChangeType]] = None,
    ) -> list[AuditEntry]:
        """Get audit history for a specific entity."""
        entry_ids = self._by_entity.get(entity_id, [])
        entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]
        
        if change_types:
            entries = [e for e in entries if e.change_type in change_types]
        
        # Sort by date descending
        entries.sort(key=lambda e: e.changed_at, reverse=True)
        
        # Apply pagination
        if limit:
            entries = entries[offset:offset + limit]
        else:
            entries = entries[offset:]
        
        return entries
    
    def get_user_activity(
        self,
        user_id: UUID,
        limit: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[AuditEntry]:
        """Get audit entries for changes made by a user."""
        entry_ids = self._by_user.get(user_id, [])
        entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]
        
        if from_date:
            entries = [e for e in entries if e.changed_at >= from_date]
        
        if to_date:
            entries = [e for e in entries if e.changed_at <= to_date]
        
        entries.sort(key=lambda e: e.changed_at, reverse=True)
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    # Timeline Generation
    
    def get_timeline(
        self,
        entity_id: Optional[UUID] = None,
        filters: Optional[TimelineFilter] = None,
        page_size: Optional[int] = None,
        offset: int = 0,
    ) -> Timeline:
        """Get a grouped timeline view."""
        page_size = page_size or self.config.default_page_size
        page_size = min(page_size, self.config.max_page_size)
        
        # Get all relevant entries
        if entity_id:
            entry_ids = self._by_entity.get(entity_id, [])
            entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]
            entity_type = entries[0].entity_type if entries else None
            entity_name = entries[0].entity_name if entries else None
        else:
            entries = list(self._entries.values())
            entity_type = None
            entity_name = None
        
        # Apply filters
        entries = self._apply_filters(entries, filters)
        
        # Sort by date descending
        entries.sort(key=lambda e: e.changed_at, reverse=True)
        
        total = len(entries)
        
        # Apply pagination
        paginated = entries[offset:offset + page_size]
        has_more = (offset + page_size) < total
        
        # Group by date
        groups = self._group_by_date(paginated)
        
        oldest = entries[-1].changed_at if entries else None
        newest = entries[0].changed_at if entries else None
        
        return Timeline(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            groups=groups,
            total_entries=total,
            has_more=has_more,
            oldest_entry_date=oldest,
            newest_entry_date=newest,
        )
    
    def _apply_filters(
        self,
        entries: list[AuditEntry],
        filters: Optional[TimelineFilter],
    ) -> list[AuditEntry]:
        """Apply filters to entries."""
        if not filters:
            return entries
        
        if filters.entity_ids:
            entries = [e for e in entries if e.entity_id in filters.entity_ids]
        
        if filters.entity_types:
            entries = [e for e in entries if e.entity_type in filters.entity_types]
        
        if filters.change_types:
            entries = [e for e in entries if e.change_type in filters.change_types]
        
        if filters.changed_by:
            entries = [e for e in entries if e.changed_by in filters.changed_by]
        
        if filters.from_date:
            entries = [e for e in entries if e.changed_at >= filters.from_date]
        
        if filters.to_date:
            entries = [e for e in entries if e.changed_at <= filters.to_date]
        
        if filters.access_levels:
            entries = [e for e in entries if e.access_level in filters.access_levels]
        
        if filters.search_text:
            search = filters.search_text.lower()
            entries = [
                e for e in entries
                if search in e.summary.lower()
                or search in (e.details or "").lower()
                or search in e.entity_name.lower()
            ]
        
        return entries
    
    def _group_by_date(self, entries: list[AuditEntry]) -> list[TimelineGroup]:
        """Group entries by date."""
        groups: dict[str, TimelineGroup] = {}
        
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        for entry in entries:
            entry_date = entry.changed_at.date()
            
            # Generate date label
            if entry_date == today:
                label = "Today"
            elif entry_date == yesterday:
                label = "Yesterday"
            elif (today - entry_date).days < 7:
                label = entry_date.strftime("%A")  # Day name
            else:
                label = entry_date.strftime("%B %d, %Y")
            
            key = entry_date.isoformat()
            
            if key not in groups:
                groups[key] = TimelineGroup(
                    date=datetime.combine(entry_date, datetime.min.time()),
                    date_label=label,
                    entries=[],
                )
            
            groups[key].entries.append(entry)
        
        # Sort groups by date descending
        return sorted(groups.values(), key=lambda g: g.date, reverse=True)
    
    # Aggregation and Statistics
    
    def get_change_count(
        self,
        entity_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict[ChangeType, int]:
        """Get count of changes by type."""
        if entity_id:
            entry_ids = self._by_entity.get(entity_id, [])
            entries = [self._entries[eid] for eid in entry_ids]
        else:
            entries = list(self._entries.values())
        
        if from_date:
            entries = [e for e in entries if e.changed_at >= from_date]
        
        if to_date:
            entries = [e for e in entries if e.changed_at <= to_date]
        
        counts: dict[ChangeType, int] = {}
        for entry in entries:
            counts[entry.change_type] = counts.get(entry.change_type, 0) + 1
        
        return counts
    
    def get_activity_summary(
        self,
        entity_id: UUID,
    ) -> dict[str, Any]:
        """Get a summary of activity for an entity."""
        entries = self.get_entity_history(entity_id)
        
        if not entries:
            return {
                "total_changes": 0,
                "last_change": None,
                "created_at": None,
                "created_by": None,
            }
        
        created_entry = next(
            (e for e in reversed(entries) if e.change_type == ChangeType.CREATE),
            None
        )
        
        return {
            "total_changes": len(entries),
            "last_change": entries[0].changed_at if entries else None,
            "last_changed_by": entries[0].changed_by_name if entries else None,
            "created_at": created_entry.changed_at if created_entry else None,
            "created_by": created_entry.changed_by_name if created_entry else None,
            "change_types": self.get_change_count(entity_id),
        }
    
    def get_most_active_entities(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 10,
        from_date: Optional[datetime] = None,
    ) -> list[tuple[UUID, str, int]]:
        """Get entities with most activity."""
        counts: dict[UUID, tuple[str, int]] = {}
        
        for entry in self._entries.values():
            if entity_type and entry.entity_type != entity_type:
                continue
            
            if from_date and entry.changed_at < from_date:
                continue
            
            if entry.entity_id not in counts:
                counts[entry.entity_id] = (entry.entity_name, 0)
            
            name, count = counts[entry.entity_id]
            counts[entry.entity_id] = (name, count + 1)
        
        # Sort by count descending
        sorted_entities = sorted(
            [(eid, name, count) for eid, (name, count) in counts.items()],
            key=lambda x: x[2],
            reverse=True,
        )
        
        return sorted_entities[:limit]
    
    def get_most_active_users(
        self,
        limit: int = 10,
        from_date: Optional[datetime] = None,
    ) -> list[tuple[UUID, str, int]]:
        """Get users with most activity."""
        counts: dict[UUID, tuple[str, int]] = {}
        
        for entry in self._entries.values():
            if from_date and entry.changed_at < from_date:
                continue
            
            if entry.changed_by not in counts:
                counts[entry.changed_by] = (entry.changed_by_name, 0)
            
            name, count = counts[entry.changed_by]
            counts[entry.changed_by] = (name, count + 1)
        
        sorted_users = sorted(
            [(uid, name, count) for uid, (name, count) in counts.items()],
            key=lambda x: x[2],
            reverse=True,
        )
        
        return sorted_users[:limit]
    
    # Cleanup
    
    def cleanup_old_entries(
        self,
        older_than_days: Optional[int] = None,
    ) -> int:
        """Remove entries older than specified days."""
        days = older_than_days or self.config.retention_days
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        to_remove = [
            eid for eid, entry in self._entries.items()
            if entry.changed_at < cutoff
        ]
        
        for eid in to_remove:
            entry = self._entries.pop(eid, None)
            if entry:
                # Remove from indices
                if entry.entity_id in self._by_entity:
                    self._by_entity[entry.entity_id] = [
                        e for e in self._by_entity[entry.entity_id] if e != eid
                    ]
                
                if entry.changed_by in self._by_user:
                    self._by_user[entry.changed_by] = [
                        e for e in self._by_user[entry.changed_by] if e != eid
                    ]
        
        return len(to_remove)


# Singleton management
_service_instance: Optional[AuditTrailTimelineService] = None


def get_audit_trail_service() -> AuditTrailTimelineService:
    """Get the singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AuditTrailTimelineService()
    return _service_instance


def reset_audit_trail_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _service_instance
    _service_instance = None

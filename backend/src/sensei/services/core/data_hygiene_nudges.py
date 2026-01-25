"""
Data Hygiene Nudges Service.

Provides lightweight prompts when fields are missing, without blocking
unless it's a gate. Helps maintain data quality through gentle reminders
rather than hard enforcement.

Features:
- Field completeness analysis
- Context-aware nudge generation
- Priority-based nudge ordering
- Nudge suppression and dismissal
- Aggregated hygiene reports
- Custom nudge rules per entity type
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.entity_providers import build_entity_getter


class NudgeType(str, Enum):
    """Types of data hygiene nudges."""
    
    MISSING_FIELD = "missing_field"
    INCOMPLETE_FIELD = "incomplete_field"
    STALE_DATA = "stale_data"
    FORMAT_ISSUE = "format_issue"
    RELATIONSHIP_MISSING = "relationship_missing"
    BEST_PRACTICE = "best_practice"
    ENRICHMENT_SUGGESTION = "enrichment_suggestion"
    VALIDATION_WARNING = "validation_warning"


class NudgePriority(str, Enum):
    """Priority levels for nudges."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NudgeStatus(str, Enum):
    """Status of a nudge."""
    
    ACTIVE = "active"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    SNOOZED = "snoozed"


class EntityType(str, Enum):
    """Entity types that support hygiene nudges."""
    
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    QUOTE = "quote"
    TASK = "task"
    ACCOUNT = "account"
    CONTACT = "contact"
    RISK = "risk"
    A3 = "a3"
    WORK_ORDER = "work_order"
    PRODUCT = "product"
    CTQ = "ctq"


@dataclass
class FieldRule:
    """Rule for checking field hygiene."""
    
    field_name: str
    display_name: str
    required: bool = False
    recommended: bool = True
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    allowed_values: list[str] | None = None
    nudge_message: str | None = None
    priority: NudgePriority = NudgePriority.MEDIUM
    nudge_type: NudgeType = NudgeType.MISSING_FIELD
    depends_on: dict[str, Any] | None = None  # Conditional rules


@dataclass
class Nudge:
    """A data hygiene nudge."""
    
    id: UUID
    entity_type: EntityType
    entity_id: UUID
    field_name: str
    nudge_type: NudgeType
    priority: NudgePriority
    message: str
    suggestion: str | None
    status: NudgeStatus
    created_at: datetime
    resolved_at: datetime | None = None
    dismissed_at: datetime | None = None
    dismissed_by: UUID | None = None
    snoozed_until: datetime | None = None
    resolution_value: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Check if nudge is currently active."""
        if self.status in (NudgeStatus.RESOLVED, NudgeStatus.DISMISSED):
            return False
        if self.status == NudgeStatus.SNOOZED and self.snoozed_until:
            return datetime.now(timezone.utc) >= self.snoozed_until
        return self.status == NudgeStatus.ACTIVE


@dataclass
class NudgeSuppressionRule:
    """Rule for suppressing nudges."""
    
    id: UUID
    entity_type: EntityType | None  # None = global
    field_name: str | None  # None = all fields
    nudge_type: NudgeType | None  # None = all types
    user_id: UUID | None  # None = all users
    account_id: UUID | None  # None = all accounts
    reason: str
    created_at: datetime
    created_by: UUID
    expires_at: datetime | None = None
    
    def matches(
        self,
        entity_type: EntityType,
        field_name: str,
        nudge_type: NudgeType,
        user_id: UUID | None = None,
        account_id: UUID | None = None,
    ) -> bool:
        """Check if this rule suppresses the given nudge."""
        if self.entity_type and self.entity_type != entity_type:
            return False
        if self.field_name and self.field_name != field_name:
            return False
        if self.nudge_type and self.nudge_type != nudge_type:
            return False
        if self.user_id and self.user_id != user_id:
            return False
        if self.account_id and self.account_id != account_id:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class HygieneReport:
    """Aggregated hygiene report for an entity or user."""
    
    entity_type: EntityType | None
    entity_id: UUID | None
    user_id: UUID | None
    total_nudges: int
    active_nudges: int
    resolved_nudges: int
    dismissed_nudges: int
    by_priority: dict[str, int]
    by_type: dict[str, int]
    by_field: dict[str, int]
    completeness_score: float
    generated_at: datetime


@dataclass
class EntityHygieneScore:
    """Hygiene score for an entity."""
    
    entity_type: EntityType
    entity_id: UUID
    total_fields: int
    complete_fields: int
    missing_fields: list[str]
    incomplete_fields: list[str]
    completeness_percentage: float
    active_nudges: int
    priority_score: float  # Weighted by priority


class DataHygieneNudgesService:
    """Service for managing data hygiene nudges."""
    
    def __init__(self, entity_provider: Callable[..., Any] | None = None) -> None:
        """Initialize the service."""
        self._nudges: dict[UUID, Nudge] = {}
        self._entity_provider = entity_provider
        self._suppression_rules: dict[UUID, NudgeSuppressionRule] = {}
        self._field_rules: dict[EntityType, list[FieldRule]] = {}
        self._mock_entities: dict[EntityType, dict[UUID, dict[str, Any]]] = {}
        
        # Initialize default field rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """Set up default field rules for each entity type."""
        self._field_rules[EntityType.OPPORTUNITY] = [
            FieldRule(
                field_name="name",
                display_name="Opportunity Name",
                required=True,
                min_length=3,
                priority=NudgePriority.HIGH,
                nudge_message="Opportunity name is required",
            ),
            FieldRule(
                field_name="account_id",
                display_name="Account",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_type=NudgeType.RELATIONSHIP_MISSING,
                nudge_message="Please link this opportunity to an account",
            ),
            FieldRule(
                field_name="next_step",
                display_name="Next Step",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_type=NudgeType.BEST_PRACTICE,
                nudge_message="Adding a next step helps track progress",
            ),
            FieldRule(
                field_name="next_step_date",
                display_name="Next Step Date",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Set a date for the next step",
            ),
            FieldRule(
                field_name="value",
                display_name="Expected Value",
                recommended=True,
                priority=NudgePriority.LOW,
                nudge_message="Estimating value helps prioritize",
            ),
            FieldRule(
                field_name="probability",
                display_name="Win Probability",
                recommended=True,
                priority=NudgePriority.LOW,
                nudge_message="Probability helps forecast pipeline",
            ),
        ]
        
        self._field_rules[EntityType.RFQ] = [
            FieldRule(
                field_name="title",
                display_name="RFQ Title",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="RFQ title is required",
            ),
            FieldRule(
                field_name="customer_id",
                display_name="Customer",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_type=NudgeType.RELATIONSHIP_MISSING,
                nudge_message="Please link this RFQ to a customer",
            ),
            FieldRule(
                field_name="due_date",
                display_name="Response Due Date",
                recommended=True,
                priority=NudgePriority.HIGH,
                nudge_message="Setting a due date helps track urgency",
            ),
            FieldRule(
                field_name="product_family",
                display_name="Product Family",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Specifying product family aids categorization",
            ),
            FieldRule(
                field_name="volume",
                display_name="Volume/Quantity",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Volume is needed for accurate quoting",
            ),
            FieldRule(
                field_name="specs",
                display_name="Specifications",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_type=NudgeType.INCOMPLETE_FIELD,
                nudge_message="Complete specifications reduce clarification cycles",
            ),
        ]
        
        self._field_rules[EntityType.QUOTE] = [
            FieldRule(
                field_name="rfq_id",
                display_name="Linked RFQ",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_type=NudgeType.RELATIONSHIP_MISSING,
                nudge_message="Quote should be linked to an RFQ",
            ),
            FieldRule(
                field_name="validity_date",
                display_name="Quote Validity",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="Quote validity date is required",
            ),
            FieldRule(
                field_name="assumptions",
                display_name="Assumptions",
                required=True,
                min_length=10,
                priority=NudgePriority.HIGH,
                nudge_type=NudgeType.BEST_PRACTICE,
                nudge_message="Document assumptions to protect commitments",
            ),
            FieldRule(
                field_name="lead_time",
                display_name="Lead Time",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Lead time should be specified",
            ),
            FieldRule(
                field_name="moq",
                display_name="Minimum Order Quantity",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Consider specifying MOQ",
            ),
        ]
        
        self._field_rules[EntityType.TASK] = [
            FieldRule(
                field_name="title",
                display_name="Task Title",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="Task title is required",
            ),
            FieldRule(
                field_name="due_date",
                display_name="Due Date",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Setting a due date helps prioritization",
            ),
            FieldRule(
                field_name="assigned_to",
                display_name="Assignee",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Assign task to ensure accountability",
            ),
            FieldRule(
                field_name="description",
                display_name="Description",
                recommended=True,
                priority=NudgePriority.LOW,
                nudge_message="A description provides context",
            ),
        ]
        
        self._field_rules[EntityType.ACCOUNT] = [
            FieldRule(
                field_name="name",
                display_name="Account Name",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="Account name is required",
            ),
            FieldRule(
                field_name="industry",
                display_name="Industry",
                recommended=True,
                priority=NudgePriority.LOW,
                nudge_message="Industry helps with segmentation",
            ),
            FieldRule(
                field_name="primary_contact_id",
                display_name="Primary Contact",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_type=NudgeType.RELATIONSHIP_MISSING,
                nudge_message="Link a primary contact for the account",
            ),
        ]
        
        self._field_rules[EntityType.CONTACT] = [
            FieldRule(
                field_name="name",
                display_name="Contact Name",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="Contact name is required",
            ),
            FieldRule(
                field_name="email",
                display_name="Email",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                pattern=r".+@.+\..+",
                nudge_message="Email helps with communication",
            ),
            FieldRule(
                field_name="phone",
                display_name="Phone",
                recommended=True,
                priority=NudgePriority.LOW,
                nudge_message="Phone number aids quick contact",
            ),
        ]
        
        self._field_rules[EntityType.RISK] = [
            FieldRule(
                field_name="title",
                display_name="Risk Title",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="Risk title is required",
            ),
            FieldRule(
                field_name="severity",
                display_name="Severity",
                required=True,
                priority=NudgePriority.HIGH,
                nudge_message="Severity must be assessed",
            ),
            FieldRule(
                field_name="mitigation",
                display_name="Mitigation Plan",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_type=NudgeType.BEST_PRACTICE,
                nudge_message="Define mitigation actions for the risk",
            ),
            FieldRule(
                field_name="owner_id",
                display_name="Risk Owner",
                recommended=True,
                priority=NudgePriority.MEDIUM,
                nudge_message="Assign a risk owner for accountability",
            ),
        ]
    
    # Entity helpers are provided by storage integrations
    
    def get_entity_data(
        self,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> dict[str, Any] | None:
        """Get entity data for hygiene checking."""
        if not self._entity_provider:
            return self._mock_entities.get(entity_type, {}).get(entity_id)
        return self._entity_provider(entity_type, entity_id)

    def create_mock_entity(self, entity_type: EntityType, **data: Any) -> UUID:
        """Create a mock entity for testing."""
        entity_id = uuid4()
        payload = {"id": entity_id, **data}
        if entity_type not in self._mock_entities:
            self._mock_entities[entity_type] = {}
        self._mock_entities[entity_type][entity_id] = payload
        return entity_id

    def add_field_rule(
        self,
        entity_type: EntityType,
        rule: FieldRule,
    ) -> None:
        """Add a custom field rule."""
        if entity_type not in self._field_rules:
            self._field_rules[entity_type] = []
        self._field_rules[entity_type].append(rule)
    
    def get_field_rules(
        self,
        entity_type: EntityType,
    ) -> list[FieldRule]:
        """Get field rules for an entity type."""
        return self._field_rules.get(entity_type, [])
    
    def analyze_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        data: dict[str, Any] | None = None,
        user_id: UUID | None = None,
        account_id: UUID | None = None,
    ) -> list[Nudge]:
        """Analyze an entity and generate nudges for hygiene issues."""
        if data is None:
            data = self.get_entity_data(entity_type, entity_id) or {}
        
        rules = self.get_field_rules(entity_type)
        nudges: list[Nudge] = []
        
        for rule in rules:
            # Check conditional dependencies
            if rule.depends_on:
                skip = False
                for dep_field, dep_value in rule.depends_on.items():
                    if data.get(dep_field) != dep_value:
                        skip = True
                        break
                if skip:
                    continue
            
            field_value = data.get(rule.field_name)
            issue_found = False
            nudge_message = rule.nudge_message or f"{rule.display_name} needs attention"
            nudge_type = rule.nudge_type
            
            # Check for missing required or recommended field
            if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                if rule.required or rule.recommended:
                    issue_found = True
                    nudge_type = NudgeType.MISSING_FIELD
            elif isinstance(field_value, str):
                # Check min length
                if rule.min_length and len(field_value.strip()) < rule.min_length:
                    issue_found = True
                    nudge_type = NudgeType.INCOMPLETE_FIELD
                    nudge_message = f"{rule.display_name} should be at least {rule.min_length} characters"
                
                # Check max length
                if rule.max_length and len(field_value.strip()) > rule.max_length:
                    issue_found = True
                    nudge_type = NudgeType.FORMAT_ISSUE
                    nudge_message = f"{rule.display_name} exceeds maximum length of {rule.max_length}"
                
                # Check pattern
                if rule.pattern:
                    import re
                    if not re.match(rule.pattern, field_value):
                        issue_found = True
                        nudge_type = NudgeType.FORMAT_ISSUE
                        nudge_message = f"{rule.display_name} has an invalid format"
            
            # Check allowed values
            if rule.allowed_values and field_value is not None:
                if field_value not in rule.allowed_values:
                    issue_found = True
                    nudge_type = NudgeType.VALIDATION_WARNING
                    nudge_message = f"{rule.display_name} has an unexpected value"
            
            if issue_found:
                # Check if suppressed
                if not self._is_suppressed(entity_type, rule.field_name, nudge_type, user_id, account_id):
                    # Check if nudge already exists
                    existing = self._find_existing_nudge(entity_type, entity_id, rule.field_name)
                    
                    if existing and existing.status == NudgeStatus.ACTIVE:
                        nudges.append(existing)
                    else:
                        nudge = Nudge(
                            id=uuid4(),
                            entity_type=entity_type,
                            entity_id=entity_id,
                            field_name=rule.field_name,
                            nudge_type=nudge_type,
                            priority=rule.priority,
                            message=nudge_message,
                            suggestion=self._generate_suggestion(rule, data),
                            status=NudgeStatus.ACTIVE,
                            created_at=datetime.now(timezone.utc),
                        )
                        self._nudges[nudge.id] = nudge
                        nudges.append(nudge)
        
        return nudges
    
    def _generate_suggestion(
        self,
        rule: FieldRule,
        data: dict[str, Any],
    ) -> str | None:
        """Generate a helpful suggestion for resolving the nudge."""
        if rule.allowed_values:
            return f"Choose from: {', '.join(rule.allowed_values[:5])}"
        
        if rule.nudge_type == NudgeType.RELATIONSHIP_MISSING:
            return "Click to search and link a related record"
        
        if rule.nudge_type == NudgeType.BEST_PRACTICE:
            return "This improves data quality and helps the team"
        
        return None
    
    def _find_existing_nudge(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        field_name: str,
    ) -> Nudge | None:
        """Find an existing nudge for the same field."""
        for nudge in self._nudges.values():
            if (
                nudge.entity_type == entity_type
                and nudge.entity_id == entity_id
                and nudge.field_name == field_name
                and nudge.status in (NudgeStatus.ACTIVE, NudgeStatus.SNOOZED)
            ):
                return nudge
        return None
    
    def _is_suppressed(
        self,
        entity_type: EntityType,
        field_name: str,
        nudge_type: NudgeType,
        user_id: UUID | None,
        account_id: UUID | None,
    ) -> bool:
        """Check if a nudge should be suppressed."""
        for rule in self._suppression_rules.values():
            if rule.matches(entity_type, field_name, nudge_type, user_id, account_id):
                return True
        return False
    
    def get_nudge(self, nudge_id: UUID) -> Nudge | None:
        """Get a nudge by ID."""
        return self._nudges.get(nudge_id)
    
    def get_entity_nudges(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        include_dismissed: bool = False,
    ) -> list[Nudge]:
        """Get all nudges for an entity."""
        nudges = []
        for nudge in self._nudges.values():
            if nudge.entity_type == entity_type and nudge.entity_id == entity_id:
                if include_dismissed or nudge.status != NudgeStatus.DISMISSED:
                    nudges.append(nudge)
        return sorted(nudges, key=lambda n: (
            0 if n.priority == NudgePriority.CRITICAL else
            1 if n.priority == NudgePriority.HIGH else
            2 if n.priority == NudgePriority.MEDIUM else 3
        ))
    
    def get_user_nudges(
        self,
        user_id: UUID,
        entity_types: list[EntityType] | None = None,
        priority: NudgePriority | None = None,
        limit: int = 50,
    ) -> list[Nudge]:
        """Get nudges relevant to a user across entities they own."""
        # In real implementation, this would filter by ownership
        nudges = []
        for nudge in self._nudges.values():
            if nudge.status != NudgeStatus.ACTIVE:
                continue
            if entity_types and nudge.entity_type not in entity_types:
                continue
            if priority and nudge.priority != priority:
                continue
            nudges.append(nudge)
        
        return sorted(nudges, key=lambda n: n.created_at, reverse=True)[:limit]
    
    def dismiss_nudge(
        self,
        nudge_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> Nudge | None:
        """Dismiss a nudge."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return None
        
        nudge.status = NudgeStatus.DISMISSED
        nudge.dismissed_at = datetime.now(timezone.utc)
        nudge.dismissed_by = user_id
        if reason:
            nudge.metadata["dismiss_reason"] = reason
        
        return nudge
    
    def snooze_nudge(
        self,
        nudge_id: UUID,
        snooze_hours: int = 24,
    ) -> Nudge | None:
        """Snooze a nudge for a specified duration."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return None
        
        nudge.status = NudgeStatus.SNOOZED
        nudge.snoozed_until = datetime.now(timezone.utc) + timedelta(hours=snooze_hours)
        
        return nudge
    
    def resolve_nudge(
        self,
        nudge_id: UUID,
        resolved_value: Any = None,
    ) -> Nudge | None:
        """Mark a nudge as resolved."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return None
        
        nudge.status = NudgeStatus.RESOLVED
        nudge.resolved_at = datetime.now(timezone.utc)
        nudge.resolution_value = resolved_value
        
        return nudge
    
    def check_and_resolve(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        field_name: str,
        new_value: Any,
    ) -> Nudge | None:
        """Check if a field update resolves an existing nudge."""
        nudge = self._find_existing_nudge(entity_type, entity_id, field_name)
        if not nudge:
            return None
        
        # Simple check: if new value is truthy, resolve
        if new_value:
            rules = self.get_field_rules(entity_type)
            for rule in rules:
                if rule.field_name == field_name:
                    # Validate against rule
                    is_valid = True
                    if rule.min_length and isinstance(new_value, str):
                        if len(new_value.strip()) < rule.min_length:
                            is_valid = False
                    
                    if is_valid:
                        return self.resolve_nudge(nudge.id, new_value)
        
        return None
    
    def create_suppression_rule(
        self,
        created_by: UUID,
        reason: str,
        entity_type: EntityType | None = None,
        field_name: str | None = None,
        nudge_type: NudgeType | None = None,
        user_id: UUID | None = None,
        account_id: UUID | None = None,
        expires_in_days: int | None = None,
    ) -> NudgeSuppressionRule:
        """Create a rule to suppress certain nudges."""
        rule = NudgeSuppressionRule(
            id=uuid4(),
            entity_type=entity_type,
            field_name=field_name,
            nudge_type=nudge_type,
            user_id=user_id,
            account_id=account_id,
            reason=reason,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days) if expires_in_days else None,
        )
        self._suppression_rules[rule.id] = rule
        return rule
    
    def delete_suppression_rule(self, rule_id: UUID) -> bool:
        """Delete a suppression rule."""
        if rule_id in self._suppression_rules:
            del self._suppression_rules[rule_id]
            return True
        return False
    
    def get_suppression_rules(
        self,
        entity_type: EntityType | None = None,
    ) -> list[NudgeSuppressionRule]:
        """Get all suppression rules."""
        rules = list(self._suppression_rules.values())
        if entity_type:
            rules = [r for r in rules if r.entity_type is None or r.entity_type == entity_type]
        return rules
    
    def calculate_hygiene_score(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        data: dict[str, Any] | None = None,
    ) -> EntityHygieneScore:
        """Calculate hygiene score for an entity."""
        if data is None:
            data = self.get_entity_data(entity_type, entity_id) or {}
        
        rules = self.get_field_rules(entity_type)
        total_fields = len(rules)
        complete_fields = 0
        missing_fields: list[str] = []
        incomplete_fields: list[str] = []
        
        priority_weights = {
            NudgePriority.CRITICAL: 4,
            NudgePriority.HIGH: 3,
            NudgePriority.MEDIUM: 2,
            NudgePriority.LOW: 1,
        }
        
        weighted_total = 0
        weighted_complete = 0
        
        for rule in rules:
            weight = priority_weights[rule.priority]
            weighted_total += weight
            
            field_value = data.get(rule.field_name)
            
            if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                if rule.required:
                    missing_fields.append(rule.field_name)
                elif rule.recommended:
                    incomplete_fields.append(rule.field_name)
            else:
                is_complete = True
                
                if isinstance(field_value, str):
                    if rule.min_length and len(field_value.strip()) < rule.min_length:
                        is_complete = False
                        incomplete_fields.append(rule.field_name)
                
                if is_complete:
                    complete_fields += 1
                    weighted_complete += weight
        
        # Get active nudges
        active_nudges = len([
            n for n in self._nudges.values()
            if n.entity_type == entity_type
            and n.entity_id == entity_id
            and n.status == NudgeStatus.ACTIVE
        ])
        
        completeness = (complete_fields / total_fields * 100) if total_fields > 0 else 100
        priority_score = (weighted_complete / weighted_total * 100) if weighted_total > 0 else 100
        
        return EntityHygieneScore(
            entity_type=entity_type,
            entity_id=entity_id,
            total_fields=total_fields,
            complete_fields=complete_fields,
            missing_fields=missing_fields,
            incomplete_fields=incomplete_fields,
            completeness_percentage=round(completeness, 1),
            active_nudges=active_nudges,
            priority_score=round(priority_score, 1),
        )
    
    def generate_report(
        self,
        user_id: UUID | None = None,
        entity_type: EntityType | None = None,
        entity_id: UUID | None = None,
    ) -> HygieneReport:
        """Generate an aggregated hygiene report."""
        relevant_nudges = [
            n for n in self._nudges.values()
            if (entity_type is None or n.entity_type == entity_type)
            and (entity_id is None or n.entity_id == entity_id)
        ]
        
        active = [n for n in relevant_nudges if n.status == NudgeStatus.ACTIVE]
        resolved = [n for n in relevant_nudges if n.status == NudgeStatus.RESOLVED]
        dismissed = [n for n in relevant_nudges if n.status == NudgeStatus.DISMISSED]
        
        by_priority: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_field: dict[str, int] = {}
        
        for nudge in active:
            by_priority[nudge.priority.value] = by_priority.get(nudge.priority.value, 0) + 1
            by_type[nudge.nudge_type.value] = by_type.get(nudge.nudge_type.value, 0) + 1
            by_field[nudge.field_name] = by_field.get(nudge.field_name, 0) + 1
        
        # Calculate aggregate completeness
        total_completeness = 100.0
        if entity_id and entity_type:
            score = self.calculate_hygiene_score(entity_type, entity_id)
            total_completeness = score.completeness_percentage
        
        return HygieneReport(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            total_nudges=len(relevant_nudges),
            active_nudges=len(active),
            resolved_nudges=len(resolved),
            dismissed_nudges=len(dismissed),
            by_priority=by_priority,
            by_type=by_type,
            by_field=by_field,
            completeness_score=total_completeness,
            generated_at=datetime.now(timezone.utc),
        )
    
    def get_priority_nudges(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        max_count: int = 3,
    ) -> list[Nudge]:
        """Get top priority nudges for display."""
        nudges = self.get_entity_nudges(entity_type, entity_id)
        active = [n for n in nudges if n.is_active]
        return active[:max_count]
    
    def bulk_analyze(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
    ) -> dict[UUID, list[Nudge]]:
        """Analyze multiple entities at once."""
        results: dict[UUID, list[Nudge]] = {}
        for entity_id in entity_ids:
            results[entity_id] = self.analyze_entity(entity_type, entity_id)
        return results
    
    def get_stale_data_nudges(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        data: dict[str, Any],
        stale_threshold_days: int = 30,
    ) -> list[Nudge]:
        """Generate nudges for stale data."""
        nudges: list[Nudge] = []
        now = datetime.now(timezone.utc)
        
        # Check updated_at field
        updated_at = data.get("updated_at")
        if isinstance(updated_at, datetime):
            days_stale = (now - updated_at).days
            if days_stale > stale_threshold_days:
                nudge = Nudge(
                    id=uuid4(),
                    entity_type=entity_type,
                    entity_id=entity_id,
                    field_name="_entity",
                    nudge_type=NudgeType.STALE_DATA,
                    priority=NudgePriority.LOW,
                    message=f"This record hasn't been updated in {days_stale} days",
                    suggestion="Review and update to ensure data is current",
                    status=NudgeStatus.ACTIVE,
                    created_at=now,
                    metadata={"days_stale": days_stale},
                )
                self._nudges[nudge.id] = nudge
                nudges.append(nudge)
        
        return nudges
    
    def cleanup_old_nudges(
        self,
        older_than_days: int = 90,
    ) -> int:
        """Clean up old resolved/dismissed nudges."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        to_delete: list[UUID] = []
        
        for nudge in self._nudges.values():
            if nudge.status in (NudgeStatus.RESOLVED, NudgeStatus.DISMISSED):
                check_date = nudge.resolved_at or nudge.dismissed_at
                if check_date and check_date < cutoff:
                    to_delete.append(nudge.id)
        
        for nudge_id in to_delete:
            del self._nudges[nudge_id]
        
        return len(to_delete)


def get_data_hygiene_nudges_service(session: AsyncSession) -> DataHygieneNudgesService:
    """Create a data hygiene nudges service wired to the database."""
    sync_session = session.sync_session
    return DataHygieneNudgesService(
        entity_provider=build_entity_getter(sync_session),
    )

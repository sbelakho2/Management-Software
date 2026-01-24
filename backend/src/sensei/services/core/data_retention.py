"""
Data Retention Rules Service.

Provides data lifecycle management including retention policies,
archival, purging, and compliance tracking.

Features:
- Configurable retention policies per entity type
- Automatic archival of old data
- Scheduled purging with safeguards
- Legal hold support
- Compliance audit trails
- Retention reports and analytics
- Data export before deletion
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.entity_providers import (
    build_archived_lister,
    build_archived_restorer,
    build_entity_archiver,
    build_entity_deleter,
    build_entity_getter,
    build_entity_lister,
    build_entity_updater,
)


class EntityType(str, Enum):
    """Entity types that support retention rules."""
    
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    QUOTE = "quote"
    TASK = "task"
    ACCOUNT = "account"
    CONTACT = "contact"
    ATTACHMENT = "attachment"
    AUDIT_LOG = "audit_log"
    NOTIFICATION = "notification"
    SESSION = "session"
    DRAFT = "draft"
    EXPORT = "export"
    EMAIL_LOG = "email_log"
    WORK_ORDER = "work_order"
    COMMENT = "comment"


class RetentionAction(str, Enum):
    """Actions that can be taken on expired data."""
    
    ARCHIVE = "archive"  # Move to cold storage
    DELETE = "delete"  # Permanently remove
    ANONYMIZE = "anonymize"  # Remove PII but keep record
    EXPORT_THEN_DELETE = "export_then_delete"  # Export before removal
    NOTIFY = "notify"  # Just notify, no action


class RetentionStatus(str, Enum):
    """Status of data with respect to retention."""
    
    ACTIVE = "active"  # Within retention period
    APPROACHING_EXPIRY = "approaching_expiry"  # Near retention limit
    EXPIRED = "expired"  # Past retention period
    ARCHIVED = "archived"  # Moved to archive
    HELD = "held"  # Under legal hold
    DELETED = "deleted"  # Marked as deleted


class PolicyStatus(str, Enum):
    """Status of a retention policy."""
    
    ACTIVE = "active"
    DISABLED = "disabled"
    DRAFT = "draft"


@dataclass
class RetentionPolicy:
    """A data retention policy."""
    
    id: UUID
    name: str
    description: str
    entity_type: EntityType
    retention_days: int
    action: RetentionAction
    status: PolicyStatus = PolicyStatus.ACTIVE
    warning_days: int = 30  # Days before expiry to warn
    conditions: dict[str, Any] | None = None  # Additional filter conditions
    exclude_statuses: list[str] | None = None  # Entity statuses to exclude
    requires_approval: bool = False
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = None
    
    @property
    def retention_period(self) -> timedelta:
        """Get retention period as timedelta."""
        return timedelta(days=self.retention_days)
    
    @property
    def is_active(self) -> bool:
        """Check if policy is active."""
        return self.status == PolicyStatus.ACTIVE


@dataclass
class LegalHold:
    """A legal hold that prevents data deletion."""
    
    id: UUID
    name: str
    reason: str
    entity_type: EntityType | None  # None = all types
    entity_ids: list[UUID] | None  # Specific entities, or None for type-wide
    account_ids: list[UUID] | None  # Specific accounts
    start_date: datetime
    end_date: datetime | None = None  # None = indefinite
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = None
    released_at: datetime | None = None
    released_by: UUID | None = None
    
    def covers_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        account_id: UUID | None = None,
    ) -> bool:
        """Check if this hold covers a specific entity."""
        if not self.is_active:
            return False
        
        if self.end_date and datetime.now(timezone.utc) > self.end_date:
            return False
        
        if self.entity_type and self.entity_type != entity_type:
            return False
        
        if self.entity_ids and entity_id not in self.entity_ids:
            return False
        
        if self.account_ids and account_id and account_id not in self.account_ids:
            return False
        
        return True


@dataclass
class RetentionRecord:
    """Record of an entity's retention status."""
    
    id: UUID
    entity_type: EntityType
    entity_id: UUID
    account_id: UUID | None
    status: RetentionStatus
    policy_id: UUID | None
    created_at: datetime
    expires_at: datetime | None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    held_by: list[UUID] | None = None  # Legal hold IDs
    export_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetentionJob:
    """A scheduled retention job."""
    
    id: UUID
    name: str
    policy_id: UUID
    scheduled_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, running, completed, failed
    records_processed: int = 0
    records_archived: int = 0
    records_deleted: int = 0
    records_skipped: int = 0
    error_message: str | None = None
    
    @property
    def is_complete(self) -> bool:
        """Check if job is complete."""
        return self.status in ("completed", "failed")


@dataclass
class RetentionReport:
    """Report on retention status across the system."""
    
    generated_at: datetime
    total_records: int
    by_status: dict[str, int]
    by_entity_type: dict[str, dict[str, int]]
    approaching_expiry: int
    under_hold: int
    storage_estimate_mb: float


class DataRetentionService:
    """Service for managing data retention rules."""
    
    def __init__(
        self,
        entity_getter: callable | None = None,
        entity_lister: callable | None = None,
        entity_archiver: callable | None = None,
        entity_deleter: callable | None = None,
        entity_updater: callable | None = None,
        archived_lister: callable | None = None,
        archived_restorer: callable | None = None,
    ) -> None:
        """Initialize the service."""
        self._policies: dict[UUID, RetentionPolicy] = {}
        self._legal_holds: dict[UUID, LegalHold] = {}
        self._records: dict[UUID, RetentionRecord] = {}
        self._jobs: dict[UUID, RetentionJob] = {}
        self._entity_getter = entity_getter
        self._entity_lister = entity_lister
        self._entity_archiver = entity_archiver
        self._entity_deleter = entity_deleter
        self._entity_updater = entity_updater
        self._archived_lister = archived_lister
        self._archived_restorer = archived_restorer
        
        # Initialize default policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        """Set up default retention policies."""
        defaults = [
            {
                "name": "Opportunity Retention",
                "description": "Retain opportunities for 7 years after closing",
                "entity_type": EntityType.OPPORTUNITY,
                "retention_days": 2555,  # 7 years
                "action": RetentionAction.ARCHIVE,
                "exclude_statuses": ["open", "active"],
            },
            {
                "name": "Quote Retention",
                "description": "Retain quotes for 7 years",
                "entity_type": EntityType.QUOTE,
                "retention_days": 2555,
                "action": RetentionAction.ARCHIVE,
            },
            {
                "name": "Audit Log Retention",
                "description": "Keep audit logs for 10 years",
                "entity_type": EntityType.AUDIT_LOG,
                "retention_days": 3650,
                "action": RetentionAction.ARCHIVE,
            },
            {
                "name": "Session Cleanup",
                "description": "Delete expired sessions after 90 days",
                "entity_type": EntityType.SESSION,
                "retention_days": 90,
                "action": RetentionAction.DELETE,
            },
            {
                "name": "Draft Cleanup",
                "description": "Delete abandoned drafts after 30 days",
                "entity_type": EntityType.DRAFT,
                "retention_days": 30,
                "action": RetentionAction.DELETE,
            },
            {
                "name": "Notification Cleanup",
                "description": "Archive old notifications after 1 year",
                "entity_type": EntityType.NOTIFICATION,
                "retention_days": 365,
                "action": RetentionAction.DELETE,
            },
            {
                "name": "Attachment Retention",
                "description": "Keep attachments for 7 years",
                "entity_type": EntityType.ATTACHMENT,
                "retention_days": 2555,
                "action": RetentionAction.ARCHIVE,
            },
        ]
        
        for policy_data in defaults:
            policy = RetentionPolicy(
                id=uuid4(),
                name=str(policy_data["name"]),
                description=str(policy_data["description"]),
                entity_type=policy_data["entity_type"],  # type: ignore[arg-type]
                retention_days=int(str(policy_data["retention_days"])),
                action=policy_data["action"],  # type: ignore[arg-type]
                exclude_statuses=policy_data.get("exclude_statuses"),  # type: ignore[arg-type]
            )
            self._policies[policy.id] = policy
    
    def get_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> dict[str, Any] | None:
        """Get an entity by type and ID."""
        if not self._entity_getter:
            raise ValueError("DataRetentionService requires an entity_getter in production")
        return self._entity_getter(entity_type, entity_id)
    
    # Policy Management
    
    def create_policy(
        self,
        name: str,
        description: str,
        entity_type: EntityType,
        retention_days: int,
        action: RetentionAction,
        warning_days: int = 30,
        conditions: dict[str, Any] | None = None,
        exclude_statuses: list[str] | None = None,
        requires_approval: bool = False,
        created_by: UUID | None = None,
    ) -> RetentionPolicy:
        """Create a new retention policy."""
        policy = RetentionPolicy(
            id=uuid4(),
            name=name,
            description=description,
            entity_type=entity_type,
            retention_days=retention_days,
            action=action,
            warning_days=warning_days,
            conditions=conditions,
            exclude_statuses=exclude_statuses,
            requires_approval=requires_approval,
            status=PolicyStatus.DRAFT if requires_approval else PolicyStatus.ACTIVE,
            created_by=created_by,
        )
        self._policies[policy.id] = policy
        return policy
    
    def get_policy(self, policy_id: UUID) -> RetentionPolicy | None:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def get_policies(
        self,
        entity_type: EntityType | None = None,
        status: PolicyStatus | None = None,
    ) -> list[RetentionPolicy]:
        """Get all policies, optionally filtered."""
        policies = list(self._policies.values())
        
        if entity_type:
            policies = [p for p in policies if p.entity_type == entity_type]
        if status:
            policies = [p for p in policies if p.status == status]
        
        return policies
    
    def update_policy(
        self,
        policy_id: UUID,
        **updates: Any,
    ) -> RetentionPolicy | None:
        """Update a retention policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        
        policy.updated_at = datetime.now(timezone.utc)
        return policy
    
    def activate_policy(
        self,
        policy_id: UUID,
        approved_by: UUID | None = None,
    ) -> RetentionPolicy | None:
        """Activate a draft or disabled policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        
        if policy.requires_approval and not approved_by:
            return None
        
        policy.status = PolicyStatus.ACTIVE
        if approved_by:
            policy.approved_by = approved_by
            policy.approved_at = datetime.now(timezone.utc)
        
        policy.updated_at = datetime.now(timezone.utc)
        return policy
    
    def disable_policy(self, policy_id: UUID) -> RetentionPolicy | None:
        """Disable an active policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None
        
        policy.status = PolicyStatus.DISABLED
        policy.updated_at = datetime.now(timezone.utc)
        return policy
    
    def delete_policy(self, policy_id: UUID) -> bool:
        """Delete a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False
    
    # Legal Hold Management
    
    def create_legal_hold(
        self,
        name: str,
        reason: str,
        entity_type: EntityType | None = None,
        entity_ids: list[UUID] | None = None,
        account_ids: list[UUID] | None = None,
        end_date: datetime | None = None,
        created_by: UUID | None = None,
    ) -> LegalHold:
        """Create a legal hold."""
        hold = LegalHold(
            id=uuid4(),
            name=name,
            reason=reason,
            entity_type=entity_type,
            entity_ids=entity_ids,
            account_ids=account_ids,
            start_date=datetime.now(timezone.utc),
            end_date=end_date,
            created_by=created_by,
        )
        self._legal_holds[hold.id] = hold
        return hold
    
    def get_legal_hold(self, hold_id: UUID) -> LegalHold | None:
        """Get a legal hold by ID."""
        return self._legal_holds.get(hold_id)
    
    def get_active_holds(
        self,
        entity_type: EntityType | None = None,
    ) -> list[LegalHold]:
        """Get all active legal holds."""
        holds = [h for h in self._legal_holds.values() if h.is_active]
        
        if entity_type:
            holds = [h for h in holds if h.entity_type is None or h.entity_type == entity_type]
        
        return holds
    
    def release_legal_hold(
        self,
        hold_id: UUID,
        released_by: UUID | None = None,
    ) -> LegalHold | None:
        """Release a legal hold."""
        hold = self._legal_holds.get(hold_id)
        if not hold:
            return None
        
        hold.is_active = False
        hold.released_at = datetime.now(timezone.utc)
        hold.released_by = released_by
        return hold
    
    def is_under_hold(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        account_id: UUID | None = None,
    ) -> bool:
        """Check if an entity is under legal hold."""
        for hold in self._legal_holds.values():
            if hold.covers_entity(entity_type, entity_id, account_id):
                return True
        return False
    
    def get_holds_for_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> list[LegalHold]:
        """Get all legal holds covering an entity."""
        return [
            h for h in self._legal_holds.values()
            if h.covers_entity(entity_type, entity_id)
        ]
    
    # Retention Status Management
    
    def calculate_retention_status(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        created_at: datetime,
        status: str | None = None,
        account_id: UUID | None = None,
    ) -> RetentionStatus:
        """Calculate retention status for an entity."""
        now = datetime.now(timezone.utc)
        
        # Check for legal hold first
        if self.is_under_hold(entity_type, entity_id, account_id):
            return RetentionStatus.HELD
        
        # Find applicable policy
        policies = self.get_policies(entity_type=entity_type, status=PolicyStatus.ACTIVE)
        if not policies:
            return RetentionStatus.ACTIVE
        
        policy = policies[0]  # Use first matching policy
        
        # Check excluded statuses
        if policy.exclude_statuses and status in policy.exclude_statuses:
            return RetentionStatus.ACTIVE
        
        # Make created_at timezone aware if needed
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        # Calculate expiry
        expires_at = created_at + policy.retention_period
        days_until_expiry = (expires_at - now).days
        
        if days_until_expiry < 0:
            return RetentionStatus.EXPIRED
        elif days_until_expiry <= policy.warning_days:
            return RetentionStatus.APPROACHING_EXPIRY
        else:
            return RetentionStatus.ACTIVE
    
    def get_expiry_date(
        self,
        entity_type: EntityType,
        created_at: datetime,
    ) -> datetime | None:
        """Get the expiry date for an entity based on policy."""
        policies = self.get_policies(entity_type=entity_type, status=PolicyStatus.ACTIVE)
        if not policies:
            return None
        
        policy = policies[0]
        
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        return created_at + policy.retention_period
    
    def get_entities_by_status(
        self,
        entity_type: EntityType,
        status: RetentionStatus,
    ) -> list[UUID]:
        """Get entities with a specific retention status."""
        result: list[UUID] = []
        if not self._entity_lister:
            raise ValueError("DataRetentionService requires an entity_lister in production")
        entities = self._entity_lister(entity_type)
        
        for data in entities:
            entity_id = data.get("id")
            if not entity_id:
                continue
            created_at = data.get("created_at", datetime.now(timezone.utc))
            entity_status = data.get("status")
            
            calc_status = self.calculate_retention_status(
                entity_type,
                entity_id,
                created_at,
                entity_status,
            )
            
            if calc_status == status:
                result.append(entity_id)
        
        return result
    
    def get_approaching_expiry(
        self,
        entity_type: EntityType | None = None,
        days_threshold: int = 30,
    ) -> list[dict[str, Any]]:
        """Get entities approaching their retention expiry."""
        now = datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []
        
        entity_types = [entity_type] if entity_type else list(EntityType)
        
        for et in entity_types:
            policies = self.get_policies(entity_type=et, status=PolicyStatus.ACTIVE)
            if not policies:
                continue
            
            policy = policies[0]
            if not self._entity_lister:
                raise ValueError("DataRetentionService requires an entity_lister in production")
            entities = self._entity_lister(et)
            
            for data in entities:
                entity_id = data.get("id")
                if not entity_id:
                    continue
                created_at = data.get("created_at", now)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
                expires_at = created_at + policy.retention_period
                days_until = (expires_at - now).days
                
                if 0 < days_until <= days_threshold:
                    results.append({
                        "entity_type": et.value,
                        "entity_id": entity_id,
                        "expires_at": expires_at,
                        "days_until_expiry": days_until,
                    })
        
        return sorted(results, key=lambda x: x["days_until_expiry"])
    
    # Retention Actions
    
    def archive_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> bool:
        """Archive an entity."""
        # Check for legal hold
        if self.is_under_hold(entity_type, entity_id):
            return False
        if not self._entity_archiver:
            raise ValueError("DataRetentionService requires an entity_archiver in production")
        if not self._entity_archiver(entity_type, entity_id):
            return False

        self._create_record(entity_type, entity_id, RetentionStatus.ARCHIVED)
        return True
    
    def delete_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        force: bool = False,
    ) -> bool:
        """Delete an entity permanently."""
        # Check for legal hold
        if not force and self.is_under_hold(entity_type, entity_id):
            return False
        if not self._entity_deleter:
            raise ValueError("DataRetentionService requires an entity_deleter in production")
        if not self._entity_deleter(entity_type, entity_id, force):
            return False

        self._create_record(entity_type, entity_id, RetentionStatus.DELETED)
        return True
    
    def anonymize_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        fields_to_anonymize: list[str] | None = None,
    ) -> bool:
        """Anonymize PII in an entity."""
        if self.is_under_hold(entity_type, entity_id):
            return False
        if not self._entity_getter or not self._entity_updater:
            raise ValueError("DataRetentionService requires entity_getter and entity_updater in production")
        entity_data = self._entity_getter(entity_type, entity_id)
        if not entity_data:
            return False

        # Default PII fields
        if fields_to_anonymize is None:
            fields_to_anonymize = [
                "name", "email", "phone", "address",
                "first_name", "last_name", "contact_name",
            ]
        
        updates = {field_name: "[ANONYMIZED]" for field_name in fields_to_anonymize if field_name in entity_data}
        updates["anonymized_at"] = datetime.now(timezone.utc)
        return self._entity_updater(entity_type, entity_id, updates)
    
    def _create_record(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        status: RetentionStatus,
        policy_id: UUID | None = None,
    ) -> RetentionRecord:
        """Create a retention record."""
        record = RetentionRecord(
            id=uuid4(),
            entity_type=entity_type,
            entity_id=entity_id,
            account_id=None,
            status=status,
            policy_id=policy_id,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        self._records[record.id] = record
        return record
    
    # Batch Operations
    
    def run_retention_job(
        self,
        policy_id: UUID,
        dry_run: bool = False,
    ) -> RetentionJob:
        """Run a retention job for a policy."""
        policy = self._policies.get(policy_id)
        if not policy or not policy.is_active:
            job = RetentionJob(
                id=uuid4(),
                name=f"Failed job for {policy_id}",
                policy_id=policy_id,
                scheduled_at=datetime.now(timezone.utc),
                status="failed",
                error_message="Policy not found or inactive",
            )
            self._jobs[job.id] = job
            return job
        
        job = RetentionJob(
            id=uuid4(),
            name=f"Retention job for {policy.name}",
            policy_id=policy_id,
            scheduled_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        
        now = datetime.now(timezone.utc)
        if not self._entity_lister:
            raise ValueError("DataRetentionService requires an entity_lister in production")
        entities = self._entity_lister(policy.entity_type)
        
        for data in list(entities):
            entity_id = data.get("id")
            if not entity_id:
                continue
            job.records_processed += 1
            
            created_at = data.get("created_at", now)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            entity_status = data.get("status")
            
            # Check exclusions
            if policy.exclude_statuses and entity_status in policy.exclude_statuses:
                job.records_skipped += 1
                continue
            
            # Check if expired
            expires_at = created_at + policy.retention_period
            if now < expires_at:
                job.records_skipped += 1
                continue
            
            # Check legal hold
            if self.is_under_hold(policy.entity_type, entity_id):
                job.records_skipped += 1
                continue
            
            # Apply action
            if not dry_run:
                if policy.action == RetentionAction.ARCHIVE:
                    if self.archive_entity(policy.entity_type, entity_id):
                        job.records_archived += 1
                elif policy.action == RetentionAction.DELETE:
                    if self.delete_entity(policy.entity_type, entity_id):
                        job.records_deleted += 1
                elif policy.action == RetentionAction.ANONYMIZE:
                    if self.anonymize_entity(policy.entity_type, entity_id):
                        job.records_processed += 1
            else:
                # Dry run - just count what would happen
                if policy.action == RetentionAction.ARCHIVE:
                    job.records_archived += 1
                elif policy.action == RetentionAction.DELETE:
                    job.records_deleted += 1
        
        job.completed_at = datetime.now(timezone.utc)
        job.status = "completed"
        self._jobs[job.id] = job
        
        return job
    
    def get_job(self, job_id: UUID) -> RetentionJob | None:
        """Get a retention job by ID."""
        return self._jobs.get(job_id)
    
    def get_jobs(
        self,
        policy_id: UUID | None = None,
        status: str | None = None,
    ) -> list[RetentionJob]:
        """Get retention jobs."""
        jobs = list(self._jobs.values())
        
        if policy_id:
            jobs = [j for j in jobs if j.policy_id == policy_id]
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return sorted(jobs, key=lambda j: j.scheduled_at, reverse=True)
    
    # Restore from Archive
    
    def restore_from_archive(
        self,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> bool:
        """Restore an entity from archive."""
        if not self._archived_restorer:
            raise ValueError("DataRetentionService requires an archived_restorer in production")
        return self._archived_restorer(entity_type, entity_id)
    
    def get_archived_entities(
        self,
        entity_type: EntityType,
    ) -> list[UUID]:
        """Get list of archived entity IDs."""
        if not self._archived_lister:
            raise ValueError("DataRetentionService requires an archived_lister in production")
        return [entity.get("id") for entity in self._archived_lister(entity_type) if entity.get("id")]
    
    # Reports and Analytics
    
    def generate_report(self) -> RetentionReport:
        """Generate a comprehensive retention report."""
        now = datetime.now(timezone.utc)
        total_records = 0
        by_status: dict[str, int] = {}
        by_entity_type: dict[str, dict[str, int]] = {}
        approaching = 0
        under_hold = 0
        
        for et in EntityType:
            if not self._entity_lister:
                raise ValueError("DataRetentionService requires an entity_lister in production")
            entities = self._entity_lister(et)
            type_stats: dict[str, int] = {
                "total": len(entities),
                "active": 0,
                "approaching": 0,
                "expired": 0,
                "held": 0,
            }
            
            for data in entities:
                entity_id = data.get("id")
                if not entity_id:
                    continue
                total_records += 1
                created_at = data.get("created_at", now)
                status = self.calculate_retention_status(
                    et, entity_id, created_at, data.get("status")
                )
                
                status_key = status.value
                by_status[status_key] = by_status.get(status_key, 0) + 1
                
                if status == RetentionStatus.ACTIVE:
                    type_stats["active"] += 1
                elif status == RetentionStatus.APPROACHING_EXPIRY:
                    type_stats["approaching"] += 1
                    approaching += 1
                elif status == RetentionStatus.EXPIRED:
                    type_stats["expired"] += 1
                elif status == RetentionStatus.HELD:
                    type_stats["held"] += 1
                    under_hold += 1
            
            if type_stats["total"] > 0:
                by_entity_type[et.value] = type_stats
        
        # Estimate storage using reported size metadata when available
        storage_bytes = 0
        if self._entity_lister:
            for et in EntityType:
                for data in self._entity_lister(et):
                    size_bytes = data.get("size_bytes")
                    if isinstance(size_bytes, (int, float)):
                        storage_bytes += int(size_bytes)
        storage_mb = storage_bytes / (1024 * 1024) if storage_bytes else 0.0
        
        return RetentionReport(
            generated_at=now,
            total_records=total_records,
            by_status=by_status,
            by_entity_type=by_entity_type,
            approaching_expiry=approaching,
            under_hold=under_hold,
            storage_estimate_mb=round(storage_mb, 2),
        )
    
    def get_retention_summary(
        self,
        entity_type: EntityType,
    ) -> dict[str, Any]:
        """Get retention summary for an entity type."""
        policies = self.get_policies(entity_type=entity_type, status=PolicyStatus.ACTIVE)
        policy = policies[0] if policies else None
        
        if not self._entity_lister:
            raise ValueError("DataRetentionService requires an entity_lister in production")
        if not self._archived_lister:
            raise ValueError("DataRetentionService requires an archived_lister in production")
        entities = self._entity_lister(entity_type)
        archived = self._archived_lister(entity_type)
        
        expired_count = len(self.get_entities_by_status(entity_type, RetentionStatus.EXPIRED))
        approaching_count = len(self.get_entities_by_status(entity_type, RetentionStatus.APPROACHING_EXPIRY))
        
        return {
            "entity_type": entity_type.value,
            "policy_name": policy.name if policy else None,
            "retention_days": policy.retention_days if policy else None,
            "action": policy.action.value if policy else None,
            "active_count": len(entities),
            "archived_count": len(archived),
            "expired_count": expired_count,
            "approaching_expiry_count": approaching_count,
            "under_hold_count": len([
                data.get("id") for data in entities
                if data.get("id") and self.is_under_hold(entity_type, data.get("id"))
            ]),
        }
    
    def get_compliance_audit(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get audit trail of retention actions."""
        records = list(self._records.values())
        
        if start_date:
            records = [r for r in records if r.created_at >= start_date]
        if end_date:
            records = [r for r in records if r.created_at <= end_date]
        
        return [
            {
                "id": str(r.id),
                "entity_type": r.entity_type.value,
                "entity_id": str(r.entity_id),
                "status": r.status.value,
                "action_date": r.created_at.isoformat(),
                "policy_id": str(r.policy_id) if r.policy_id else None,
            }
            for r in sorted(records, key=lambda r: r.created_at, reverse=True)
        ]


def get_data_retention_service(session: AsyncSession) -> DataRetentionService:
    """Create a data retention service wired to the database."""
    sync_session = session.sync_session
    return DataRetentionService(
        entity_getter=build_entity_getter(sync_session),
        entity_lister=build_entity_lister(sync_session),
        entity_archiver=build_entity_archiver(sync_session),
        entity_deleter=build_entity_deleter(sync_session),
        entity_updater=build_entity_updater(sync_session),
        archived_lister=build_archived_lister(sync_session),
        archived_restorer=build_archived_restorer(sync_session),
    )

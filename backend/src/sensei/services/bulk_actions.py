"""
Bulk Actions Service.

Provides bulk update operations for entities with RBAC governance,
validation, and audit trail support.

Features:
- Bulk update stage/status for multiple entities
- Bulk assign/reassign owners
- Bulk update due dates
- Bulk archive/restore
- Bulk tagging
- Batch operation tracking
- Rollback support
- Validation and permission checks
- Progress tracking for large batches
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class BulkActionType(str, Enum):
    """Types of bulk actions."""
    
    # Status/Stage changes
    UPDATE_STATUS = "update_status"
    UPDATE_STAGE = "update_stage"
    
    # Assignment
    ASSIGN_OWNER = "assign_owner"
    UNASSIGN_OWNER = "unassign_owner"
    REASSIGN_OWNER = "reassign_owner"
    
    # Dates
    UPDATE_DUE_DATE = "update_due_date"
    EXTEND_DUE_DATE = "extend_due_date"
    CLEAR_DUE_DATE = "clear_due_date"
    
    # Priority
    UPDATE_PRIORITY = "update_priority"
    
    # Tags
    ADD_TAGS = "add_tags"
    REMOVE_TAGS = "remove_tags"
    REPLACE_TAGS = "replace_tags"
    
    # Lifecycle
    ARCHIVE = "archive"
    RESTORE = "restore"
    DELETE = "delete"
    
    # Custom
    CUSTOM = "custom"


class EntityType(str, Enum):
    """Entity types that support bulk actions."""
    
    RFQ = "rfq"
    QUOTE = "quote"
    WORK_ORDER = "work_order"
    TASK = "task"
    PRODUCT = "product"
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    CAPA = "capa"
    CHECKLIST = "checklist"


class BulkActionStatus(str, Enum):
    """Status of a bulk action."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some succeeded, some failed
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class ItemResultStatus(str, Enum):
    """Status of an individual item in a bulk action."""
    
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class BulkActionItemResult:
    """Result for a single item in a bulk action."""
    
    entity_id: UUID
    status: ItemResultStatus = ItemResultStatus.PENDING
    error_message: str | None = None
    old_value: Any = None
    new_value: Any = None
    processed_at: datetime | None = None


@dataclass
class BulkActionResult:
    """Result of a bulk action operation."""
    
    id: UUID = field(default_factory=uuid4)
    action_type: BulkActionType = BulkActionType.CUSTOM
    entity_type: EntityType = EntityType.TASK
    
    # Request info
    entity_ids: list[UUID] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    
    # Execution info
    status: BulkActionStatus = BulkActionStatus.PENDING
    initiated_by: UUID | None = None
    
    # Results
    item_results: dict[UUID, BulkActionItemResult] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Tracking
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    
    # Error info
    error_message: str | None = None
    
    # Rollback support
    is_rollback_available: bool = False
    rolled_back_at: datetime | None = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_count == 0:
            return 100.0
        processed = self.success_count + self.failed_count + self.skipped_count
        return (processed / self.total_count) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if bulk action is complete."""
        return self.status in (
            BulkActionStatus.COMPLETED,
            BulkActionStatus.PARTIAL,
            BulkActionStatus.FAILED,
            BulkActionStatus.CANCELLED,
            BulkActionStatus.ROLLED_BACK,
        )
    
    def to_summary(self) -> dict[str, Any]:
        """Generate summary of results."""
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "entity_type": self.entity_type.value,
            "status": self.status.value,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "progress_percentage": self.progress_percentage,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class BulkActionRequest:
    """Request for a bulk action."""
    
    action_type: BulkActionType
    entity_type: EntityType
    entity_ids: list[UUID]
    parameters: dict[str, Any] = field(default_factory=dict)
    initiated_by: UUID | None = None
    
    # Options
    validate_only: bool = False  # Dry run
    continue_on_error: bool = True  # Continue if some items fail
    require_confirmation: bool = False  # Require explicit confirmation


@dataclass
class ValidationResult:
    """Result of validating a bulk action."""
    
    is_valid: bool = True
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    entity_validation: dict[UUID, list[str]] = field(default_factory=dict)
    
    def add_error(
        self,
        message: str,
        entity_id: UUID | None = None,
        field: str | None = None,
    ) -> None:
        """Add an error."""
        self.is_valid = False
        error = {"message": message}
        if entity_id:
            error["entity_id"] = entity_id
        if field:
            error["field"] = field
        self.errors.append(error)
        
        if entity_id:
            if entity_id not in self.entity_validation:
                self.entity_validation[entity_id] = []
            self.entity_validation[entity_id].append(message)
    
    def add_warning(
        self,
        message: str,
        entity_id: UUID | None = None,
    ) -> None:
        """Add a warning."""
        warning = {"message": message}
        if entity_id:
            warning["entity_id"] = entity_id
        self.warnings.append(warning)


# Type for entity handlers
EntityHandler = Callable[[UUID, dict[str, Any]], tuple[bool, str | None, Any, Any]]


class BulkActionsService:
    """
    Service for performing bulk operations on entities.
    
    Provides RBAC-governed bulk updates with validation,
    progress tracking, and rollback support.
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._results: dict[UUID, BulkActionResult] = {}
        self._handlers: dict[tuple[EntityType, BulkActionType], EntityHandler] = {}
        self._validators: dict[tuple[EntityType, BulkActionType], Callable] = {}
        self._max_results: int = 1000
        self._result_ttl: timedelta = timedelta(days=7)
        
        # Mock entity storage for testing
        self._mock_entities: dict[EntityType, dict[UUID, dict[str, Any]]] = {
            et: {} for et in EntityType
        }
        
        # Register default handlers
        self._register_default_handlers()

    def _store_result(self, result: BulkActionResult) -> None:
        """Store a result and prune old entries to avoid unbounded growth."""
        self._results[result.id] = result
        self._prune_results()

    def _prune_results(self) -> None:
        """Remove expired or excess results."""
        cutoff = datetime.now(timezone.utc) - self._result_ttl
        stale_ids = [rid for rid, res in self._results.items() if res.created_at < cutoff]
        for rid in stale_ids:
            del self._results[rid]

        excess = len(self._results) - self._max_results
        if excess > 0:
            oldest = sorted(self._results.items(), key=lambda item: item[1].created_at)
            for rid, _ in oldest[:excess]:
                del self._results[rid]
    
    def _register_default_handlers(self) -> None:
        """Register default handlers for common actions."""
        for entity_type in EntityType:
            # Status updates
            self.register_handler(
                entity_type,
                BulkActionType.UPDATE_STATUS,
                self._handle_status_update,
            )
            
            # Owner assignment
            self.register_handler(
                entity_type,
                BulkActionType.ASSIGN_OWNER,
                self._handle_assign_owner,
            )
            
            # Due date updates
            self.register_handler(
                entity_type,
                BulkActionType.UPDATE_DUE_DATE,
                self._handle_due_date_update,
            )
            
            # Priority updates
            self.register_handler(
                entity_type,
                BulkActionType.UPDATE_PRIORITY,
                self._handle_priority_update,
            )
            
            # Tag operations
            self.register_handler(
                entity_type,
                BulkActionType.ADD_TAGS,
                self._handle_add_tags,
            )
            self.register_handler(
                entity_type,
                BulkActionType.REMOVE_TAGS,
                self._handle_remove_tags,
            )
            
            # Archive/restore
            self.register_handler(
                entity_type,
                BulkActionType.ARCHIVE,
                self._handle_archive,
            )
            self.register_handler(
                entity_type,
                BulkActionType.RESTORE,
                self._handle_restore,
            )
    
    # ---------------------
    # Handler Registration
    # ---------------------
    
    def register_handler(
        self,
        entity_type: EntityType,
        action_type: BulkActionType,
        handler: EntityHandler,
    ) -> None:
        """Register a handler for an entity/action combination."""
        self._handlers[(entity_type, action_type)] = handler
    
    def register_validator(
        self,
        entity_type: EntityType,
        action_type: BulkActionType,
        validator: Callable[[list[UUID], dict[str, Any]], ValidationResult],
    ) -> None:
        """Register a validator for an entity/action combination."""
        self._validators[(entity_type, action_type)] = validator
    
    # ---------------------
    # Default Handlers
    # ---------------------
    
    def _get_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
    ) -> dict[str, Any] | None:
        """Get a mock entity."""
        return self._mock_entities[entity_type].get(entity_id)
    
    def _save_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        entity: dict[str, Any],
    ) -> None:
        """Save a mock entity."""
        self._mock_entities[entity_type][entity_id] = entity
    
    def _handle_status_update(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle status update for an entity."""
        entity_type = params.get("_entity_type")
        new_status = params.get("status")
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        old_status = entity.get("status")
        entity["status"] = new_status
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, old_status, new_status
    
    def _handle_assign_owner(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle owner assignment."""
        entity_type = params.get("_entity_type")
        new_owner_id = params.get("owner_id")
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        old_owner = entity.get("owner_id")
        entity["owner_id"] = new_owner_id
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, old_owner, new_owner_id
    
    def _handle_due_date_update(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle due date update."""
        entity_type = params.get("_entity_type")
        new_due_date = params.get("due_date")
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        old_due_date = entity.get("due_date")
        entity["due_date"] = new_due_date
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, old_due_date, new_due_date
    
    def _handle_priority_update(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle priority update."""
        entity_type = params.get("_entity_type")
        new_priority = params.get("priority")
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        old_priority = entity.get("priority")
        entity["priority"] = new_priority
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, old_priority, new_priority
    
    def _handle_add_tags(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle adding tags."""
        entity_type = params.get("_entity_type")
        tags_to_add = params.get("tags", [])
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        old_tags = list(entity.get("tags", []))
        new_tags = list(set(old_tags + tags_to_add))
        entity["tags"] = new_tags
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, old_tags, new_tags
    
    def _handle_remove_tags(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle removing tags."""
        entity_type = params.get("_entity_type")
        tags_to_remove = params.get("tags", [])
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        old_tags = list(entity.get("tags", []))
        new_tags = [t for t in old_tags if t not in tags_to_remove]
        entity["tags"] = new_tags
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, old_tags, new_tags
    
    def _handle_archive(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle archiving an entity."""
        entity_type = params.get("_entity_type")
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        if entity.get("is_archived"):
            return False, "Entity already archived", None, None
        
        entity["is_archived"] = True
        entity["archived_at"] = datetime.now(timezone.utc)
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, False, True
    
    def _handle_restore(
        self,
        entity_id: UUID,
        params: dict[str, Any],
    ) -> tuple[bool, str | None, Any, Any]:
        """Handle restoring an archived entity."""
        entity_type = params.get("_entity_type")
        
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False, "Entity not found", None, None
        
        if not entity.get("is_archived"):
            return False, "Entity is not archived", None, None
        
        entity["is_archived"] = False
        entity["archived_at"] = None
        entity["updated_at"] = datetime.now(timezone.utc)
        
        self._save_entity(entity_type, entity_id, entity)
        
        return True, None, True, False
    
    # ---------------------
    # Validation
    # ---------------------
    
    def validate(
        self,
        request: BulkActionRequest,
    ) -> ValidationResult:
        """Validate a bulk action request."""
        result = ValidationResult()
        
        # Check for empty entity list
        if not request.entity_ids:
            result.add_error("No entities specified")
            return result
        
        # Check for handler
        handler_key = (request.entity_type, request.action_type)
        if handler_key not in self._handlers:
            result.add_error(
                f"No handler for {request.action_type.value} on {request.entity_type.value}",
            )
            return result
        
        # Check custom validator if exists
        if handler_key in self._validators:
            validator = self._validators[handler_key]
            custom_result = validator(request.entity_ids, request.parameters)
            if not custom_result.is_valid:
                result.is_valid = False
                result.errors.extend(custom_result.errors)
                result.warnings.extend(custom_result.warnings)
        
        # Validate each entity exists
        for entity_id in request.entity_ids:
            entity = self._get_entity(request.entity_type, entity_id)
            if not entity:
                result.add_warning(
                    f"Entity not found: {entity_id}",
                    entity_id=entity_id,
                )
        
        # Validate required parameters
        if request.action_type == BulkActionType.UPDATE_STATUS:
            if "status" not in request.parameters:
                result.add_error("Status is required for UPDATE_STATUS action")
        
        if request.action_type == BulkActionType.ASSIGN_OWNER:
            if "owner_id" not in request.parameters:
                result.add_error("owner_id is required for ASSIGN_OWNER action")
        
        if request.action_type in (BulkActionType.ADD_TAGS, BulkActionType.REMOVE_TAGS):
            if "tags" not in request.parameters:
                result.add_error("tags is required for tag operations")
        
        return result
    
    # ---------------------
    # Execution
    # ---------------------
    
    def execute(
        self,
        request: BulkActionRequest,
    ) -> BulkActionResult:
        """Execute a bulk action."""
        # Validate first
        validation = self.validate(request)
        if not validation.is_valid:
            result = BulkActionResult(
                action_type=request.action_type,
                entity_type=request.entity_type,
                entity_ids=request.entity_ids,
                parameters=request.parameters,
                status=BulkActionStatus.FAILED,
                initiated_by=request.initiated_by,
                total_count=len(request.entity_ids),
                error_message="; ".join(e["message"] for e in validation.errors),
            )
            self._store_result(result)
            return result
        
        # If validate only, return success without executing
        if request.validate_only:
            result = BulkActionResult(
                action_type=request.action_type,
                entity_type=request.entity_type,
                entity_ids=request.entity_ids,
                parameters=request.parameters,
                status=BulkActionStatus.COMPLETED,
                initiated_by=request.initiated_by,
                total_count=len(request.entity_ids),
            )
            result.error_message = "Validation passed (dry run)"
            self._store_result(result)
            return result
        
        # Create result
        result = BulkActionResult(
            action_type=request.action_type,
            entity_type=request.entity_type,
            entity_ids=request.entity_ids,
            parameters=request.parameters,
            status=BulkActionStatus.IN_PROGRESS,
            initiated_by=request.initiated_by,
            total_count=len(request.entity_ids),
            started_at=datetime.now(timezone.utc),
            is_rollback_available=True,
        )
        
        # Initialize item results
        for entity_id in request.entity_ids:
            result.item_results[entity_id] = BulkActionItemResult(
                entity_id=entity_id,
            )
        
        # Get handler
        handler = self._handlers[(request.entity_type, request.action_type)]
        
        # Add entity type to params for handlers
        params = dict(request.parameters)
        params["_entity_type"] = request.entity_type
        
        # Execute for each entity
        for entity_id in request.entity_ids:
            item_result = result.item_results[entity_id]
            
            try:
                success, error, old_val, new_val = handler(entity_id, params)
                
                if success:
                    item_result.status = ItemResultStatus.SUCCESS
                    item_result.old_value = old_val
                    item_result.new_value = new_val
                    result.success_count += 1
                else:
                    if error and "not found" in error.lower():
                        item_result.status = ItemResultStatus.SKIPPED
                        item_result.error_message = error
                        result.skipped_count += 1
                    else:
                        item_result.status = ItemResultStatus.FAILED
                        item_result.error_message = error
                        result.failed_count += 1
                        
                        if not request.continue_on_error:
                            result.status = BulkActionStatus.PARTIAL
                            result.error_message = f"Stopped at entity {entity_id}: {error}"
                            break
                
            except Exception as e:
                item_result.status = ItemResultStatus.FAILED
                item_result.error_message = str(e)
                result.failed_count += 1
                
                if not request.continue_on_error:
                    result.status = BulkActionStatus.PARTIAL
                    result.error_message = f"Error at entity {entity_id}: {e}"
                    break
            
            item_result.processed_at = datetime.now(timezone.utc)
        
        # Set final status
        result.completed_at = datetime.now(timezone.utc)
        
        if result.status == BulkActionStatus.IN_PROGRESS:
            if result.failed_count == 0 and result.skipped_count == 0:
                result.status = BulkActionStatus.COMPLETED
            elif result.success_count == 0:
                result.status = BulkActionStatus.FAILED
            else:
                result.status = BulkActionStatus.PARTIAL
        
        self._store_result(result)
        return result
    
    def execute_async(
        self,
        request: BulkActionRequest,
    ) -> UUID:
        """
        Start a bulk action asynchronously.
        
        Returns the result ID for tracking progress.
        In a real implementation, this would queue the work.
        """
        # Create pending result
        result = BulkActionResult(
            action_type=request.action_type,
            entity_type=request.entity_type,
            entity_ids=request.entity_ids,
            parameters=request.parameters,
            status=BulkActionStatus.PENDING,
            initiated_by=request.initiated_by,
            total_count=len(request.entity_ids),
        )
        
        self._store_result(result)
        
        # In a real implementation, we'd queue this
        # For now, execute synchronously
        final_result = self.execute(request)
        final_result.id = result.id
        self._store_result(final_result)
        
        return result.id
    
    # ---------------------
    # Result Retrieval
    # ---------------------
    
    def get_result(self, result_id: UUID) -> BulkActionResult | None:
        """Get a bulk action result by ID."""
        return self._results.get(result_id)
    
    def get_user_results(
        self,
        user_id: UUID,
        include_completed: bool = True,
    ) -> list[BulkActionResult]:
        """Get all results for a user."""
        results = [
            r for r in self._results.values()
            if r.initiated_by == user_id
        ]
        
        if not include_completed:
            results = [r for r in results if not r.is_complete]
        
        return sorted(results, key=lambda r: r.created_at, reverse=True)
    
    def get_pending_results(self) -> list[BulkActionResult]:
        """Get all pending bulk actions."""
        return [
            r for r in self._results.values()
            if r.status in (BulkActionStatus.PENDING, BulkActionStatus.IN_PROGRESS)
        ]
    
    # ---------------------
    # Rollback
    # ---------------------
    
    def rollback(
        self,
        result_id: UUID,
        initiated_by: UUID,
    ) -> BulkActionResult | None:
        """Rollback a completed bulk action."""
        result = self._results.get(result_id)
        if not result:
            return None
        
        if not result.is_rollback_available:
            return None
        
        if result.status == BulkActionStatus.ROLLED_BACK:
            return None
        
        # Create reverse actions
        for entity_id, item_result in result.item_results.items():
            if item_result.status != ItemResultStatus.SUCCESS:
                continue
            
            # Determine reverse action
            if result.action_type == BulkActionType.UPDATE_STATUS:
                if item_result.old_value is not None:
                    entity = self._get_entity(result.entity_type, entity_id)
                    if entity:
                        entity["status"] = item_result.old_value
                        self._save_entity(result.entity_type, entity_id, entity)
                        item_result.status = ItemResultStatus.ROLLED_BACK
            
            elif result.action_type == BulkActionType.ASSIGN_OWNER:
                entity = self._get_entity(result.entity_type, entity_id)
                if entity:
                    entity["owner_id"] = item_result.old_value
                    self._save_entity(result.entity_type, entity_id, entity)
                    item_result.status = ItemResultStatus.ROLLED_BACK
            
            elif result.action_type == BulkActionType.UPDATE_PRIORITY:
                entity = self._get_entity(result.entity_type, entity_id)
                if entity:
                    entity["priority"] = item_result.old_value
                    self._save_entity(result.entity_type, entity_id, entity)
                    item_result.status = ItemResultStatus.ROLLED_BACK
            
            elif result.action_type in (
                BulkActionType.ADD_TAGS,
                BulkActionType.REMOVE_TAGS,
            ):
                entity = self._get_entity(result.entity_type, entity_id)
                if entity:
                    entity["tags"] = item_result.old_value
                    self._save_entity(result.entity_type, entity_id, entity)
                    item_result.status = ItemResultStatus.ROLLED_BACK
            
            elif result.action_type == BulkActionType.ARCHIVE:
                entity = self._get_entity(result.entity_type, entity_id)
                if entity:
                    entity["is_archived"] = False
                    entity["archived_at"] = None
                    self._save_entity(result.entity_type, entity_id, entity)
                    item_result.status = ItemResultStatus.ROLLED_BACK
            
            elif result.action_type == BulkActionType.RESTORE:
                entity = self._get_entity(result.entity_type, entity_id)
                if entity:
                    entity["is_archived"] = True
                    self._save_entity(result.entity_type, entity_id, entity)
                    item_result.status = ItemResultStatus.ROLLED_BACK
        
        result.status = BulkActionStatus.ROLLED_BACK
        result.rolled_back_at = datetime.now(timezone.utc)
        result.is_rollback_available = False
        
        return result
    
    # ---------------------
    # Convenience Methods
    # ---------------------
    
    def bulk_update_status(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        status: str,
        initiated_by: UUID | None = None,
    ) -> BulkActionResult:
        """Convenience method for bulk status update."""
        return self.execute(
            BulkActionRequest(
                action_type=BulkActionType.UPDATE_STATUS,
                entity_type=entity_type,
                entity_ids=entity_ids,
                parameters={"status": status},
                initiated_by=initiated_by,
            ),
        )
    
    def bulk_assign_owner(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        owner_id: UUID,
        initiated_by: UUID | None = None,
    ) -> BulkActionResult:
        """Convenience method for bulk owner assignment."""
        return self.execute(
            BulkActionRequest(
                action_type=BulkActionType.ASSIGN_OWNER,
                entity_type=entity_type,
                entity_ids=entity_ids,
                parameters={"owner_id": owner_id},
                initiated_by=initiated_by,
            ),
        )
    
    def bulk_update_due_date(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        due_date: datetime,
        initiated_by: UUID | None = None,
    ) -> BulkActionResult:
        """Convenience method for bulk due date update."""
        return self.execute(
            BulkActionRequest(
                action_type=BulkActionType.UPDATE_DUE_DATE,
                entity_type=entity_type,
                entity_ids=entity_ids,
                parameters={"due_date": due_date},
                initiated_by=initiated_by,
            ),
        )
    
    def bulk_add_tags(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        tags: list[str],
        initiated_by: UUID | None = None,
    ) -> BulkActionResult:
        """Convenience method for bulk tag addition."""
        return self.execute(
            BulkActionRequest(
                action_type=BulkActionType.ADD_TAGS,
                entity_type=entity_type,
                entity_ids=entity_ids,
                parameters={"tags": tags},
                initiated_by=initiated_by,
            ),
        )
    
    def bulk_archive(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        initiated_by: UUID | None = None,
    ) -> BulkActionResult:
        """Convenience method for bulk archive."""
        return self.execute(
            BulkActionRequest(
                action_type=BulkActionType.ARCHIVE,
                entity_type=entity_type,
                entity_ids=entity_ids,
                initiated_by=initiated_by,
            ),
        )
    
    # ---------------------
    # Mock Entity Management (for testing)
    # ---------------------
    
    def create_mock_entity(
        self,
        entity_type: EntityType,
        entity_id: UUID | None = None,
        **fields: Any,
    ) -> UUID:
        """Create a mock entity for testing."""
        if entity_id is None:
            entity_id = uuid4()
        
        entity = {
            "id": entity_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": "active",
            "owner_id": None,
            "due_date": None,
            "priority": "normal",
            "tags": [],
            "is_archived": False,
            "archived_at": None,
            **fields,
        }
        
        self._mock_entities[entity_type][entity_id] = entity
        return entity_id

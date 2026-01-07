"""
Tests for Bulk Actions Service.

Verifies:
- Bulk status updates
- Bulk owner assignment
- Bulk due date updates
- Bulk tag operations
- Bulk archive/restore
- Validation
- Progress tracking
- Rollback
- Error handling
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.bulk_actions import (
    BulkActionRequest,
    BulkActionResult,
    BulkActionsService,
    BulkActionStatus,
    BulkActionType,
    EntityType,
    ItemResultStatus,
    ValidationResult,
)


class TestBulkStatusUpdates:
    """Tests for bulk status update operations."""
    
    def test_bulk_update_status_single_entity(self) -> None:
        """Test updating status of a single entity."""
        service = BulkActionsService()
        entity_id = service.create_mock_entity(EntityType.TASK, status="pending")
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        assert result.success_count == 1
        assert result.failed_count == 0
        
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["status"] == "completed"
    
    def test_bulk_update_status_multiple_entities(self) -> None:
        """Test updating status of multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK, status="pending")
            for _ in range(5)
        ]
        
        result = service.bulk_update_status(
            EntityType.TASK,
            entity_ids,
            status="in_progress",
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        assert result.success_count == 5
        assert result.total_count == 5
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["status"] == "in_progress"
    
    def test_bulk_update_status_tracks_old_values(self) -> None:
        """Test that old values are tracked for rollback."""
        service = BulkActionsService()
        entity_id = service.create_mock_entity(EntityType.TASK, status="draft")
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="active",
        )
        
        item_result = result.item_results[entity_id]
        assert item_result.old_value == "draft"
        assert item_result.new_value == "active"
    
    def test_bulk_update_status_different_entity_types(self) -> None:
        """Test bulk updates work for different entity types."""
        service = BulkActionsService()
        
        rfq_id = service.create_mock_entity(EntityType.RFQ, status="new")
        wo_id = service.create_mock_entity(EntityType.WORK_ORDER, status="pending")
        
        # Update RFQs
        result1 = service.bulk_update_status(
            EntityType.RFQ,
            [rfq_id],
            status="in_review",
        )
        assert result1.status == BulkActionStatus.COMPLETED
        
        # Update Work Orders
        result2 = service.bulk_update_status(
            EntityType.WORK_ORDER,
            [wo_id],
            status="in_progress",
        )
        assert result2.status == BulkActionStatus.COMPLETED


class TestBulkOwnerAssignment:
    """Tests for bulk owner assignment."""
    
    def test_bulk_assign_owner(self) -> None:
        """Test assigning owner to multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(3)
        ]
        
        new_owner = uuid4()
        result = service.bulk_assign_owner(
            EntityType.TASK,
            entity_ids,
            owner_id=new_owner,
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        assert result.success_count == 3
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["owner_id"] == new_owner
    
    def test_bulk_reassign_owner(self) -> None:
        """Test reassigning from one owner to another."""
        service = BulkActionsService()
        
        old_owner = uuid4()
        new_owner = uuid4()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK, owner_id=old_owner)
            for _ in range(2)
        ]
        
        result = service.bulk_assign_owner(
            EntityType.TASK,
            entity_ids,
            owner_id=new_owner,
        )
        
        assert result.success_count == 2
        
        for entity_id in entity_ids:
            item_result = result.item_results[entity_id]
            assert item_result.old_value == old_owner
            assert item_result.new_value == new_owner


class TestBulkDueDates:
    """Tests for bulk due date updates."""
    
    def test_bulk_update_due_date(self) -> None:
        """Test updating due dates for multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(3)
        ]
        
        new_due_date = datetime.now(timezone.utc) + timedelta(days=7)
        result = service.bulk_update_due_date(
            EntityType.TASK,
            entity_ids,
            due_date=new_due_date,
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["due_date"] == new_due_date
    
    def test_bulk_extend_due_dates(self) -> None:
        """Test extending due dates preserves old dates."""
        service = BulkActionsService()
        
        old_date = datetime.now(timezone.utc)
        new_date = old_date + timedelta(days=14)
        
        entity_id = service.create_mock_entity(
            EntityType.TASK,
            due_date=old_date,
        )
        
        result = service.bulk_update_due_date(
            EntityType.TASK,
            [entity_id],
            due_date=new_date,
        )
        
        item_result = result.item_results[entity_id]
        assert item_result.old_value == old_date
        assert item_result.new_value == new_date


class TestBulkTagOperations:
    """Tests for bulk tag operations."""
    
    def test_bulk_add_tags(self) -> None:
        """Test adding tags to multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK, tags=["existing"])
            for _ in range(2)
        ]
        
        result = service.bulk_add_tags(
            EntityType.TASK,
            entity_ids,
            tags=["new", "tag"],
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert "existing" in entity["tags"]
            assert "new" in entity["tags"]
            assert "tag" in entity["tags"]
    
    def test_bulk_add_tags_no_duplicates(self) -> None:
        """Test adding tags doesn't create duplicates."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(
            EntityType.TASK,
            tags=["existing"],
        )
        
        service.bulk_add_tags(
            EntityType.TASK,
            [entity_id],
            tags=["existing", "new"],
        )
        
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["tags"].count("existing") == 1
    
    def test_bulk_remove_tags(self) -> None:
        """Test removing tags from multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(
                EntityType.TASK,
                tags=["keep", "remove1", "remove2"],
            )
            for _ in range(2)
        ]
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.REMOVE_TAGS,
                entity_type=EntityType.TASK,
                entity_ids=entity_ids,
                parameters={"tags": ["remove1", "remove2"]},
            ),
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["tags"] == ["keep"]


class TestBulkArchive:
    """Tests for bulk archive/restore."""
    
    def test_bulk_archive(self) -> None:
        """Test archiving multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(3)
        ]
        
        result = service.bulk_archive(EntityType.TASK, entity_ids)
        
        assert result.status == BulkActionStatus.COMPLETED
        assert result.success_count == 3
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["is_archived"] is True
            assert entity["archived_at"] is not None
    
    def test_bulk_archive_already_archived(self) -> None:
        """Test archiving already archived entities skips them."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(
            EntityType.TASK,
            is_archived=True,
            archived_at=datetime.now(timezone.utc),
        )
        
        result = service.bulk_archive(EntityType.TASK, [entity_id])
        
        assert result.failed_count == 1
        assert result.item_results[entity_id].error_message == "Entity already archived"
    
    def test_bulk_restore(self) -> None:
        """Test restoring archived entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(
                EntityType.TASK,
                is_archived=True,
                archived_at=datetime.now(timezone.utc),
            )
            for _ in range(2)
        ]
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.RESTORE,
                entity_type=EntityType.TASK,
                entity_ids=entity_ids,
            ),
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["is_archived"] is False
    
    def test_bulk_restore_not_archived(self) -> None:
        """Test restoring non-archived entity fails."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.RESTORE,
                entity_type=EntityType.TASK,
                entity_ids=[entity_id],
            ),
        )
        
        assert result.failed_count == 1
        assert "not archived" in result.item_results[entity_id].error_message


class TestBulkPriority:
    """Tests for bulk priority updates."""
    
    def test_bulk_update_priority(self) -> None:
        """Test updating priority for multiple entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK, priority="low")
            for _ in range(3)
        ]
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.UPDATE_PRIORITY,
                entity_type=EntityType.TASK,
                entity_ids=entity_ids,
                parameters={"priority": "high"},
            ),
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        
        for entity_id in entity_ids:
            entity = service._get_entity(EntityType.TASK, entity_id)
            assert entity["priority"] == "high"


class TestValidation:
    """Tests for validation."""
    
    def test_validate_empty_entity_list(self) -> None:
        """Test validation fails for empty entity list."""
        service = BulkActionsService()
        
        request = BulkActionRequest(
            action_type=BulkActionType.UPDATE_STATUS,
            entity_type=EntityType.TASK,
            entity_ids=[],
            parameters={"status": "active"},
        )
        
        result = service.validate(request)
        
        assert not result.is_valid
        assert any("No entities" in e["message"] for e in result.errors)
    
    def test_validate_missing_status_parameter(self) -> None:
        """Test validation fails when status parameter is missing."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        request = BulkActionRequest(
            action_type=BulkActionType.UPDATE_STATUS,
            entity_type=EntityType.TASK,
            entity_ids=[entity_id],
            parameters={},  # Missing status
        )
        
        result = service.validate(request)
        
        assert not result.is_valid
        assert any("Status is required" in e["message"] for e in result.errors)
    
    def test_validate_missing_owner_parameter(self) -> None:
        """Test validation fails when owner_id is missing."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        request = BulkActionRequest(
            action_type=BulkActionType.ASSIGN_OWNER,
            entity_type=EntityType.TASK,
            entity_ids=[entity_id],
            parameters={},  # Missing owner_id
        )
        
        result = service.validate(request)
        
        assert not result.is_valid
        assert any("owner_id is required" in e["message"] for e in result.errors)
    
    def test_validate_missing_tags_parameter(self) -> None:
        """Test validation fails when tags are missing."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        request = BulkActionRequest(
            action_type=BulkActionType.ADD_TAGS,
            entity_type=EntityType.TASK,
            entity_ids=[entity_id],
            parameters={},  # Missing tags
        )
        
        result = service.validate(request)
        
        assert not result.is_valid
        assert any("tags is required" in e["message"] for e in result.errors)
    
    def test_validate_nonexistent_entity_warning(self) -> None:
        """Test validation warns about nonexistent entities."""
        service = BulkActionsService()
        
        nonexistent_id = uuid4()
        
        request = BulkActionRequest(
            action_type=BulkActionType.UPDATE_STATUS,
            entity_type=EntityType.TASK,
            entity_ids=[nonexistent_id],
            parameters={"status": "active"},
        )
        
        result = service.validate(request)
        
        assert result.is_valid  # Still valid, just warning
        assert len(result.warnings) > 0
    
    def test_dry_run_validation(self) -> None:
        """Test dry run returns success without modifying entities."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK, status="pending")
        
        request = BulkActionRequest(
            action_type=BulkActionType.UPDATE_STATUS,
            entity_type=EntityType.TASK,
            entity_ids=[entity_id],
            parameters={"status": "completed"},
            validate_only=True,
        )
        
        result = service.execute(request)
        
        assert result.status == BulkActionStatus.COMPLETED
        
        # Entity should NOT be modified
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["status"] == "pending"
    
    def test_custom_validator(self) -> None:
        """Test custom validators can be registered."""
        service = BulkActionsService()
        
        def custom_validator(
            entity_ids: list,
            params: dict,
        ) -> ValidationResult:
            result = ValidationResult()
            if len(entity_ids) > 10:
                result.add_error("Cannot update more than 10 entities at once")
            return result
        
        service.register_validator(
            EntityType.TASK,
            BulkActionType.UPDATE_STATUS,
            custom_validator,
        )
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(15)
        ]
        
        request = BulkActionRequest(
            action_type=BulkActionType.UPDATE_STATUS,
            entity_type=EntityType.TASK,
            entity_ids=entity_ids,
            parameters={"status": "active"},
        )
        
        result = service.validate(request)
        
        assert not result.is_valid
        assert any("more than 10" in e["message"] for e in result.errors)


class TestProgressTracking:
    """Tests for progress tracking."""
    
    def test_tracks_total_count(self) -> None:
        """Test total count is tracked."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(10)
        ]
        
        result = service.bulk_update_status(
            EntityType.TASK,
            entity_ids,
            status="completed",
        )
        
        assert result.total_count == 10
    
    def test_tracks_success_count(self) -> None:
        """Test success count is tracked."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(5)
        ]
        
        result = service.bulk_update_status(
            EntityType.TASK,
            entity_ids,
            status="completed",
        )
        
        assert result.success_count == 5
    
    def test_tracks_failed_count(self) -> None:
        """Test failed count is tracked."""
        service = BulkActionsService()
        
        # Create mix of existing and non-existing entities
        existing_ids = [
            service.create_mock_entity(EntityType.TASK, is_archived=True)
            for _ in range(3)
        ]
        
        result = service.bulk_archive(EntityType.TASK, existing_ids)
        
        assert result.failed_count == 3  # Already archived
    
    def test_progress_percentage(self) -> None:
        """Test progress percentage calculation."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(4)
        ]
        
        result = service.bulk_update_status(
            EntityType.TASK,
            entity_ids,
            status="completed",
        )
        
        assert result.progress_percentage == 100.0
    
    def test_timestamps_tracked(self) -> None:
        """Test timestamps are tracked."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
        )
        
        assert result.created_at is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.started_at <= result.completed_at


class TestRollback:
    """Tests for rollback functionality."""
    
    def test_rollback_status_update(self) -> None:
        """Test rolling back a status update."""
        service = BulkActionsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(EntityType.TASK, status="pending")
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
            initiated_by=user_id,
        )
        
        # Verify status changed
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["status"] == "completed"
        
        # Rollback
        rolled_back = service.rollback(result.id, user_id)
        
        assert rolled_back is not None
        assert rolled_back.status == BulkActionStatus.ROLLED_BACK
        
        # Verify status restored
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["status"] == "pending"
    
    def test_rollback_owner_assignment(self) -> None:
        """Test rolling back an owner assignment."""
        service = BulkActionsService()
        user_id = uuid4()
        
        old_owner = uuid4()
        new_owner = uuid4()
        
        entity_id = service.create_mock_entity(
            EntityType.TASK,
            owner_id=old_owner,
        )
        
        result = service.bulk_assign_owner(
            EntityType.TASK,
            [entity_id],
            owner_id=new_owner,
            initiated_by=user_id,
        )
        
        # Rollback
        service.rollback(result.id, user_id)
        
        # Verify owner restored
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["owner_id"] == old_owner
    
    def test_rollback_tag_addition(self) -> None:
        """Test rolling back tag additions."""
        service = BulkActionsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(
            EntityType.TASK,
            tags=["original"],
        )
        
        result = service.bulk_add_tags(
            EntityType.TASK,
            [entity_id],
            tags=["new"],
            initiated_by=user_id,
        )
        
        # Rollback
        service.rollback(result.id, user_id)
        
        # Verify tags restored
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["tags"] == ["original"]
    
    def test_rollback_archive(self) -> None:
        """Test rolling back an archive operation."""
        service = BulkActionsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.bulk_archive(
            EntityType.TASK,
            [entity_id],
            initiated_by=user_id,
        )
        
        # Rollback
        service.rollback(result.id, user_id)
        
        # Verify entity restored
        entity = service._get_entity(EntityType.TASK, entity_id)
        assert entity["is_archived"] is False
    
    def test_cannot_rollback_twice(self) -> None:
        """Test cannot rollback an already rolled back action."""
        service = BulkActionsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(EntityType.TASK, status="pending")
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
            initiated_by=user_id,
        )
        
        # First rollback
        service.rollback(result.id, user_id)
        
        # Second rollback should fail
        second_rollback = service.rollback(result.id, user_id)
        assert second_rollback is None
    
    def test_rollback_not_found(self) -> None:
        """Test rollback returns None for unknown result."""
        service = BulkActionsService()
        
        rolled_back = service.rollback(uuid4(), uuid4())
        
        assert rolled_back is None


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_continue_on_error(self) -> None:
        """Test processing continues when continue_on_error is True."""
        service = BulkActionsService()
        
        # Mix of valid and archived entities
        valid_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(3)
        ]
        archived_ids = [
            service.create_mock_entity(
                EntityType.TASK,
                is_archived=True,
                archived_at=datetime.now(timezone.utc),
            )
            for _ in range(2)
        ]
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.ARCHIVE,
                entity_type=EntityType.TASK,
                entity_ids=valid_ids + archived_ids,
                continue_on_error=True,
            ),
        )
        
        assert result.success_count == 3
        assert result.failed_count == 2
        assert result.status == BulkActionStatus.PARTIAL
    
    def test_stop_on_error(self) -> None:
        """Test processing stops when continue_on_error is False."""
        service = BulkActionsService()
        
        archived_id = service.create_mock_entity(
            EntityType.TASK,
            is_archived=True,
            archived_at=datetime.now(timezone.utc),
        )
        valid_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.ARCHIVE,
                entity_type=EntityType.TASK,
                entity_ids=[archived_id, valid_id],
                continue_on_error=False,
            ),
        )
        
        assert result.status == BulkActionStatus.PARTIAL
        assert result.failed_count == 1
        # Second entity should not be processed
        assert result.success_count == 0
    
    def test_entity_not_found_skipped(self) -> None:
        """Test non-existent entities are skipped."""
        service = BulkActionsService()
        
        valid_id = service.create_mock_entity(EntityType.TASK)
        missing_id = uuid4()
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [valid_id, missing_id],
            status="completed",
        )
        
        assert result.success_count == 1
        assert result.skipped_count == 1
        assert result.item_results[missing_id].status == ItemResultStatus.SKIPPED


class TestResultRetrieval:
    """Tests for result retrieval."""
    
    def test_get_result(self) -> None:
        """Test retrieving a result by ID."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
        )
        
        retrieved = service.get_result(result.id)
        
        assert retrieved is not None
        assert retrieved.id == result.id
    
    def test_get_user_results(self) -> None:
        """Test retrieving all results for a user."""
        service = BulkActionsService()
        
        user_id = uuid4()
        other_user_id = uuid4()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        # User's actions
        service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="active",
            initiated_by=user_id,
        )
        service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
            initiated_by=user_id,
        )
        
        # Other user's action
        service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="pending",
            initiated_by=other_user_id,
        )
        
        user_results = service.get_user_results(user_id)
        
        assert len(user_results) == 2
        assert all(r.initiated_by == user_id for r in user_results)
    
    def test_get_pending_results(self) -> None:
        """Test retrieving pending results."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        # All actions complete synchronously in tests
        service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
        )
        
        pending = service.get_pending_results()
        
        # No pending since all complete synchronously
        assert len(pending) == 0


class TestAsyncExecution:
    """Tests for async execution."""
    
    def test_execute_async_returns_id(self) -> None:
        """Test async execution returns a tracking ID."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result_id = service.execute_async(
            BulkActionRequest(
                action_type=BulkActionType.UPDATE_STATUS,
                entity_type=EntityType.TASK,
                entity_ids=[entity_id],
                parameters={"status": "completed"},
            ),
        )
        
        assert result_id is not None
        
        # Can retrieve result
        result = service.get_result(result_id)
        assert result is not None
        assert result.status == BulkActionStatus.COMPLETED


class TestConvenienceMethods:
    """Tests for convenience methods."""
    
    def test_bulk_update_status_convenience(self) -> None:
        """Test bulk_update_status convenience method."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        user_id = uuid4()
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
            initiated_by=user_id,
        )
        
        assert result.action_type == BulkActionType.UPDATE_STATUS
        assert result.initiated_by == user_id
    
    def test_bulk_assign_owner_convenience(self) -> None:
        """Test bulk_assign_owner convenience method."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.RFQ)
        owner_id = uuid4()
        
        result = service.bulk_assign_owner(
            EntityType.RFQ,
            [entity_id],
            owner_id=owner_id,
        )
        
        assert result.action_type == BulkActionType.ASSIGN_OWNER
        assert result.success_count == 1
    
    def test_bulk_add_tags_convenience(self) -> None:
        """Test bulk_add_tags convenience method."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.PRODUCT)
        
        result = service.bulk_add_tags(
            EntityType.PRODUCT,
            [entity_id],
            tags=["tag1", "tag2"],
        )
        
        assert result.action_type == BulkActionType.ADD_TAGS
        assert result.success_count == 1
    
    def test_bulk_archive_convenience(self) -> None:
        """Test bulk_archive convenience method."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.OPPORTUNITY)
        
        result = service.bulk_archive(EntityType.OPPORTUNITY, [entity_id])
        
        assert result.action_type == BulkActionType.ARCHIVE
        assert result.success_count == 1


class TestResultSummary:
    """Tests for result summary."""
    
    def test_to_summary(self) -> None:
        """Test result summary generation."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(5)
        ]
        
        result = service.bulk_update_status(
            EntityType.TASK,
            entity_ids,
            status="completed",
        )
        
        summary = result.to_summary()
        
        assert summary["id"] == result.id
        assert summary["action_type"] == "update_status"
        assert summary["entity_type"] == "task"
        assert summary["status"] == "completed"
        assert summary["total_count"] == 5
        assert summary["success_count"] == 5
        assert summary["progress_percentage"] == 100.0
    
    def test_is_complete(self) -> None:
        """Test is_complete property."""
        service = BulkActionsService()
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.bulk_update_status(
            EntityType.TASK,
            [entity_id],
            status="completed",
        )
        
        assert result.is_complete


class TestCustomHandlers:
    """Tests for custom handlers."""
    
    def test_register_custom_handler(self) -> None:
        """Test registering a custom handler."""
        service = BulkActionsService()
        
        def custom_handler(
            entity_id,
            params,
        ):
            return True, None, "old", "new"
        
        service.register_handler(
            EntityType.TASK,
            BulkActionType.CUSTOM,
            custom_handler,
        )
        
        entity_id = service.create_mock_entity(EntityType.TASK)
        
        result = service.execute(
            BulkActionRequest(
                action_type=BulkActionType.CUSTOM,
                entity_type=EntityType.TASK,
                entity_ids=[entity_id],
                parameters={},
            ),
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        assert result.success_count == 1


class TestLargeScale:
    """Tests for large-scale operations."""
    
    def test_large_batch(self) -> None:
        """Test handling a large batch of entities."""
        service = BulkActionsService()
        
        entity_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(100)
        ]
        
        result = service.bulk_update_status(
            EntityType.TASK,
            entity_ids,
            status="completed",
        )
        
        assert result.status == BulkActionStatus.COMPLETED
        assert result.success_count == 100
        assert result.total_count == 100
    
    def test_mixed_results_large_batch(self) -> None:
        """Test mixed success/failure in large batch."""
        service = BulkActionsService()
        
        valid_ids = [
            service.create_mock_entity(EntityType.TASK)
            for _ in range(50)
        ]
        archived_ids = [
            service.create_mock_entity(
                EntityType.TASK,
                is_archived=True,
                archived_at=datetime.now(timezone.utc),
            )
            for _ in range(50)
        ]
        
        result = service.bulk_archive(
            EntityType.TASK,
            valid_ids + archived_ids,
        )
        
        assert result.status == BulkActionStatus.PARTIAL
        assert result.success_count == 50
        assert result.failed_count == 50

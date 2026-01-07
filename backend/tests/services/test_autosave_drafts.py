"""
Tests for Autosave Drafts Service.

Verifies:
- Draft creation and management
- Autosave functionality
- Version history
- Conflict detection and resolution
- Draft recovery
- Cleanup operations
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.autosave_drafts import (
    AutosaveDraftsService,
    ConflictInfo,
    ConflictResolution,
    Draft,
    DraftRecovery,
    DraftStatus,
    DraftType,
    DraftVersion,
)


class TestDraftCreation:
    """Tests for creating drafts."""
    
    def test_create_draft(self) -> None:
        """Test creating a new draft."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "New Quote"},
        )
        
        assert draft.id is not None
        assert draft.draft_type == DraftType.QUOTE
        assert draft.user_id == user_id
        assert draft.content["title"] == "New Quote"
    
    def test_create_draft_for_existing_entity(self) -> None:
        """Test creating draft for an existing entity."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(
            "quote",
            title="Existing Quote",
            version=5,
        )
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "Updated Quote"},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        assert draft.entity_id == entity_id
        assert draft.base_version == 5
        assert draft.is_new_entity is False
    
    def test_create_draft_with_session(self) -> None:
        """Test creating draft with session ID."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
            session_id="session-123",
            form_id="task-form",
            route="/tasks/new",
        )
        
        assert draft.session_id == "session-123"
        assert draft.form_id == "task-form"
        assert draft.route == "/tasks/new"
    
    def test_create_draft_with_expiry(self) -> None:
        """Test creating draft with custom expiry."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
            expires_in_hours=48,
        )
        
        assert draft.expires_at is not None
        expected = datetime.now(timezone.utc) + timedelta(hours=48)
        assert abs((draft.expires_at - expected).total_seconds()) < 5
    
    def test_new_entity_flag(self) -> None:
        """Test is_new_entity property."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        new_draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.RFQ,
            content={},
        )
        
        assert new_draft.is_new_entity is True
        
        existing_draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.RFQ,
            content={},
            entity_id=uuid4(),
        )
        
        assert existing_draft.is_new_entity is False


class TestDraftRetrieval:
    """Tests for retrieving drafts."""
    
    def test_get_draft(self) -> None:
        """Test getting a draft by ID."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Test"},
        )
        
        retrieved = service.get_draft(draft.id)
        
        assert retrieved is not None
        assert retrieved.id == draft.id
    
    def test_get_user_drafts(self) -> None:
        """Test getting all drafts for a user."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        other_user_id = uuid4()
        
        # User's drafts
        service.create_draft(user_id=user_id, draft_type=DraftType.TASK, content={})
        service.create_draft(user_id=user_id, draft_type=DraftType.QUOTE, content={})
        
        # Other user's draft
        service.create_draft(user_id=other_user_id, draft_type=DraftType.RFQ, content={})
        
        user_drafts = service.get_user_drafts(user_id)
        
        assert len(user_drafts) == 2
        assert all(d.user_id == user_id for d in user_drafts)
    
    def test_get_user_drafts_by_type(self) -> None:
        """Test filtering drafts by type."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        service.create_draft(user_id=user_id, draft_type=DraftType.TASK, content={})
        service.create_draft(user_id=user_id, draft_type=DraftType.TASK, content={})
        service.create_draft(user_id=user_id, draft_type=DraftType.QUOTE, content={})
        
        task_drafts = service.get_user_drafts(user_id, draft_type=DraftType.TASK)
        
        assert len(task_drafts) == 2
        assert all(d.draft_type == DraftType.TASK for d in task_drafts)
    
    def test_get_entity_draft(self) -> None:
        """Test getting draft for a specific entity."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        entity_id = uuid4()
        
        service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        draft = service.get_entity_draft(user_id, "quote", entity_id)
        
        assert draft is not None
        assert draft.entity_id == entity_id


class TestAutosave:
    """Tests for autosave functionality."""
    
    def test_autosave_updates_content(self) -> None:
        """Test that autosave updates draft content."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Original"},
        )
        
        service.autosave(
            draft.id,
            {"title": "Updated", "description": "New description"},
        )
        
        updated = service.get_draft(draft.id)
        
        assert updated.content["title"] == "Updated"
        assert updated.content["description"] == "New description"
    
    def test_autosave_creates_version(self) -> None:
        """Test that autosave creates a new version."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "v1"},
        )
        
        initial_version = draft.current_version
        
        service.autosave(draft.id, {"title": "v2"})
        
        assert draft.current_version == initial_version + 1
        assert len(draft.versions) == 2
    
    def test_autosave_tracks_changed_fields(self) -> None:
        """Test that autosave detects changed fields."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Original", "status": "draft"},
        )
        
        service.autosave(
            draft.id,
            {"title": "Changed", "status": "draft"},  # Only title changed
        )
        
        latest_version = draft.versions[-1]
        assert "title" in latest_version.changed_fields
        assert "status" not in latest_version.changed_fields
    
    def test_autosave_updates_timestamp(self) -> None:
        """Test that autosave updates timestamps."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        original_updated = draft.updated_at
        
        service.autosave(draft.id, {"title": "Updated"})
        
        assert draft.updated_at > original_updated
        assert draft.last_autosave_at is not None
    
    def test_autosave_not_found(self) -> None:
        """Test autosave with non-existent draft."""
        service = AutosaveDraftsService()
        
        result = service.autosave(uuid4(), {"title": "Test"})
        
        assert result is None


class TestManualSave:
    """Tests for manual save functionality."""
    
    def test_manual_save(self) -> None:
        """Test manual save with reason."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={},
        )
        
        service.save(
            draft.id,
            {"total": 5000},
            reason="Saving before meeting",
        )
        
        assert draft.status == DraftStatus.SAVED
        assert draft.versions[-1].auto_saved is False
        assert draft.versions[-1].save_reason == "Saving before meeting"
    
    def test_manual_save_creates_version(self) -> None:
        """Test that manual save creates a version."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Initial"},
        )
        
        service.save(draft.id, {"title": "Saved"}, reason="Manual save")
        
        assert len(draft.versions) == 2
        assert draft.versions[-1].auto_saved is False


class TestVersionHistory:
    """Tests for version history management."""
    
    def test_get_versions(self) -> None:
        """Test getting all versions of a draft."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"v": 1},
        )
        
        service.autosave(draft.id, {"v": 2})
        service.autosave(draft.id, {"v": 3})
        
        versions = service.get_versions(draft.id)
        
        assert len(versions) == 3
    
    def test_restore_version(self) -> None:
        """Test restoring a previous version."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Version 1"},
        )
        
        service.autosave(draft.id, {"title": "Version 2"})
        service.autosave(draft.id, {"title": "Version 3"})
        
        # Restore version 1
        restored = service.restore_version(draft.id, 1)
        
        assert restored is not None
        assert restored.content["title"] == "Version 1"
        assert len(restored.versions) == 4  # Original + 2 autosaves + restore
    
    def test_compare_versions(self) -> None:
        """Test comparing two versions."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Original", "priority": "low"},
        )
        
        service.autosave(
            draft.id,
            {"title": "Changed", "priority": "high"},
        )
        
        comparison = service.compare_versions(draft.id, 1, 2)
        
        assert comparison is not None
        assert "title" in comparison["changed_fields"]
        assert "priority" in comparison["changed_fields"]
        assert comparison["changes"]["title"]["old"] == "Original"
        assert comparison["changes"]["title"]["new"] == "Changed"
    
    def test_version_trimming(self) -> None:
        """Test that old versions are trimmed."""
        service = AutosaveDraftsService(max_versions=5)
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"v": 0},
        )
        
        # Create more versions than max
        for i in range(10):
            service.autosave(draft.id, {"v": i + 1})
        
        assert len(draft.versions) <= 5


class TestDraftLifecycle:
    """Tests for draft lifecycle operations."""
    
    def test_submit_draft(self) -> None:
        """Test marking draft as submitted."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.RFQ,
            content={},
        )
        
        service.submit(draft.id)
        
        assert draft.status == DraftStatus.SUBMITTED
    
    def test_discard_draft(self) -> None:
        """Test discarding a draft."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        service.discard(draft.id)
        
        assert draft.status == DraftStatus.DISCARDED
    
    def test_delete_draft(self) -> None:
        """Test permanently deleting a draft."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        result = service.delete(draft.id)
        
        assert result is True
        assert service.get_draft(draft.id) is None
    
    def test_discarded_draft_not_in_list(self) -> None:
        """Test that discarded drafts don't appear in user drafts."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        service.discard(draft.id)
        
        user_drafts = service.get_user_drafts(user_id)
        
        assert draft.id not in [d.id for d in user_drafts]


class TestConflictDetection:
    """Tests for conflict detection and resolution."""
    
    def test_detect_conflict(self) -> None:
        """Test detecting a conflict when entity is updated."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(
            "quote",
            title="Original",
        )
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "Draft changes"},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        # Simulate another user updating the entity
        service.update_mock_entity("quote", entity_id, title="External changes")
        
        # Autosave should detect conflict
        service.autosave(draft.id, {"title": "More draft changes"})
        
        assert draft.has_conflict is True
        assert draft.conflict_detected_at is not None
    
    def test_get_conflict_info(self) -> None:
        """Test getting detailed conflict information."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity(
            "quote",
            title="Original",
            status="draft",
        )
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "Local change", "status": "draft"},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        # External update
        service.update_mock_entity("quote", entity_id, title="Remote change")
        
        # Trigger conflict detection
        service.autosave(draft.id, {"title": "More local changes", "status": "draft"})
        
        conflict = service.get_conflict_info(draft.id)
        
        assert conflict is not None
        assert conflict.draft_id == draft.id
        assert conflict.entity_id == entity_id
    
    def test_resolve_conflict_keep_local(self) -> None:
        """Test resolving conflict by keeping local changes."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity("quote", title="Original")
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "Local"},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        service.update_mock_entity("quote", entity_id, title="Remote")
        service.autosave(draft.id, {"title": "My changes"})
        
        resolved = service.resolve_conflict(
            draft.id,
            ConflictResolution.KEEP_LOCAL,
        )
        
        assert resolved is not None
        assert resolved.has_conflict is False
        assert resolved.content["title"] == "My changes"
    
    def test_resolve_conflict_keep_remote(self) -> None:
        """Test resolving conflict by keeping remote changes."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity("quote", title="Original")
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "Local"},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        service.update_mock_entity("quote", entity_id, title="Remote changes")
        service.autosave(draft.id, {"title": "My changes"})
        
        resolved = service.resolve_conflict(
            draft.id,
            ConflictResolution.KEEP_REMOTE,
        )
        
        assert resolved is not None
        assert resolved.has_conflict is False
        assert resolved.content["title"] == "Remote changes"
    
    def test_resolve_conflict_merge(self) -> None:
        """Test resolving conflict with merged content."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        entity_id = service.create_mock_entity("quote", title="Original")
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.QUOTE,
            content={"title": "Local"},
            entity_id=entity_id,
            entity_type="quote",
        )
        
        service.update_mock_entity("quote", entity_id, title="Remote")
        service.autosave(draft.id, {"title": "Local"})
        
        merged_content = {"title": "Merged title"}
        
        resolved = service.resolve_conflict(
            draft.id,
            ConflictResolution.MERGE,
            merged_content=merged_content,
        )
        
        assert resolved is not None
        assert resolved.content["title"] == "Merged title"


class TestDraftRecovery:
    """Tests for draft recovery after crashes."""
    
    def test_get_recoverable_drafts(self) -> None:
        """Test getting drafts that can be recovered."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        # Create draft with old session
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Unsaved work"},
            session_id="old-session",
        )
        
        # Get recoverable from new session
        recoverable = service.get_recoverable_drafts(
            user_id,
            session_id="new-session",
        )
        
        assert len(recoverable) == 1
        assert recoverable[0].draft_id == draft.id
    
    def test_recoverable_excludes_current_session(self) -> None:
        """Test that current session drafts are not in recoverable list."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        session_id = "current-session"
        
        service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
            session_id=session_id,
        )
        
        recoverable = service.get_recoverable_drafts(user_id, session_id=session_id)
        
        assert len(recoverable) == 0
    
    def test_recover_draft(self) -> None:
        """Test recovering a draft to new session."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"title": "Recovery test"},
            session_id="old-session",
        )
        
        recovered = service.recover_draft(draft.id, "new-session")
        
        assert recovered is not None
        assert recovered.session_id == "new-session"
        assert recovered.status == DraftStatus.RECOVERED


class TestCleanup:
    """Tests for cleanup operations."""
    
    def test_cleanup_expired(self) -> None:
        """Test cleaning up expired drafts."""
        service = AutosaveDraftsService(default_expiry_hours=0)  # Immediate expiry
        user_id = uuid4()
        
        # Create draft that expires immediately
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
            expires_in_hours=-1,  # Already expired
        )
        draft.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        expired_count = service.cleanup_expired()
        
        assert expired_count >= 1
        assert draft.status == DraftStatus.EXPIRED
    
    def test_cleanup_submitted(self) -> None:
        """Test cleaning up old submitted drafts."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        service.submit(draft.id)
        
        # Make it old
        draft.updated_at = datetime.now(timezone.utc) - timedelta(hours=48)
        
        deleted_count = service.cleanup_submitted(older_than_hours=24)
        
        assert deleted_count >= 1
        assert service.get_draft(draft.id) is None
    
    def test_is_expired_property(self) -> None:
        """Test is_expired property."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        assert draft.is_expired is False
        
        # Set expiry in the past
        draft.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        assert draft.is_expired is True


class TestStatistics:
    """Tests for draft statistics."""
    
    def test_get_draft_stats(self) -> None:
        """Test getting draft statistics."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        service.create_draft(user_id=user_id, draft_type=DraftType.TASK, content={})
        service.create_draft(user_id=user_id, draft_type=DraftType.TASK, content={})
        service.create_draft(user_id=user_id, draft_type=DraftType.QUOTE, content={})
        
        stats = service.get_draft_stats(user_id)
        
        assert stats["total_drafts"] == 3
        assert stats["by_type"]["task"] == 2
        assert stats["by_type"]["quote"] == 1


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_autosave_discarded_draft(self) -> None:
        """Test that discarded drafts cannot be autosaved."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        service.discard(draft.id)
        
        result = service.autosave(draft.id, {"title": "Should not save"})
        
        assert result is None
    
    def test_restore_nonexistent_version(self) -> None:
        """Test restoring a version that doesn't exist."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        result = service.restore_version(draft.id, 999)
        
        assert result is None
    
    def test_compare_nonexistent_versions(self) -> None:
        """Test comparing versions that don't exist."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        result = service.compare_versions(draft.id, 1, 999)
        
        assert result is None
    
    def test_empty_content(self) -> None:
        """Test handling empty content."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.FORM,
            content={},
        )
        
        service.autosave(draft.id, {})
        
        assert draft.content == {}
    
    def test_version_count_property(self) -> None:
        """Test version_count property."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={},
        )
        
        assert draft.version_count == 1
        
        service.autosave(draft.id, {"v": 2})
        service.autosave(draft.id, {"v": 3})
        
        assert draft.version_count == 3
    
    def test_get_version(self) -> None:
        """Test getting a specific version."""
        service = AutosaveDraftsService()
        user_id = uuid4()
        
        draft = service.create_draft(
            user_id=user_id,
            draft_type=DraftType.TASK,
            content={"v": 1},
        )
        
        version = draft.get_version(1)
        
        assert version is not None
        assert version.content["v"] == 1
        
        nonexistent = draft.get_version(999)
        assert nonexistent is None

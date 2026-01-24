"""
Autosave Drafts Service.

Provides automatic saving of work-in-progress content
to prevent data loss and enable seamless editing.

Features:
- Automatic periodic saving
- Manual save points
- Draft versioning
- Conflict detection
- Draft recovery
- Expiration/cleanup
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.entity_providers import build_entity_getter


class DraftType(str, Enum):
    """Types of drafts."""
    
    QUOTE = "quote"
    RFQ = "rfq"
    TASK = "task"
    WORK_ORDER = "work_order"
    PRODUCT = "product"
    RISK = "risk"
    CAPA = "capa"
    CHECKLIST = "checklist"
    PROJECT = "project"
    COMMENT = "comment"
    DOCUMENT = "document"
    FORM = "form"


class DraftStatus(str, Enum):
    """Status of a draft."""
    
    ACTIVE = "active"  # Currently being edited
    SAVED = "saved"  # Manually saved
    SUBMITTED = "submitted"  # Submitted/published
    DISCARDED = "discarded"  # Explicitly discarded
    EXPIRED = "expired"  # Auto-expired
    RECOVERED = "recovered"  # Recovered from crash


class ConflictResolution(str, Enum):
    """How to resolve conflicts."""
    
    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"
    MERGE = "merge"


@dataclass
class DraftVersion:
    """A version of a draft."""
    
    id: UUID = field(default_factory=uuid4)
    version_number: int = 1
    content: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    saved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auto_saved: bool = True  # True if auto-saved, False if manual
    save_reason: str | None = None  # Optional reason for save
    
    # Diff info
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class Draft:
    """A draft of an entity."""
    
    id: UUID = field(default_factory=uuid4)
    draft_type: DraftType = DraftType.FORM
    status: DraftStatus = DraftStatus.ACTIVE
    
    # Content
    content: dict[str, Any] = field(default_factory=dict)
    
    # Related entity
    entity_id: UUID | None = None  # None for new entities
    entity_type: str | None = None
    
    # Version history
    versions: list[DraftVersion] = field(default_factory=list)
    current_version: int = 0
    
    # Ownership
    user_id: UUID = field(default_factory=uuid4)
    session_id: str | None = None  # Browser/device session
    
    # Context
    form_id: str | None = None  # UI form identifier
    route: str | None = None  # UI route where draft was created
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_autosave_at: datetime | None = None
    expires_at: datetime | None = None
    
    # Conflict tracking
    base_version: int | None = None  # Version of entity when edit started
    has_conflict: bool = False
    conflict_detected_at: datetime | None = None
    
    @property
    def is_new_entity(self) -> bool:
        """Check if this is a draft for a new entity."""
        return self.entity_id is None
    
    @property
    def is_expired(self) -> bool:
        """Check if draft has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def version_count(self) -> int:
        """Get number of saved versions."""
        return len(self.versions)
    
    def get_version(self, version_number: int) -> DraftVersion | None:
        """Get a specific version."""
        for version in self.versions:
            if version.version_number == version_number:
                return version
        return None


@dataclass
class DraftRecovery:
    """Information about a recovered draft."""
    
    draft_id: UUID
    draft_type: DraftType
    entity_id: UUID | None
    
    # Recovery info
    recovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_saved_at: datetime | None = None
    content_preview: str = ""
    
    # Status
    was_recovered: bool = False
    recovery_error: str | None = None


@dataclass
class ConflictInfo:
    """Information about a draft conflict."""
    
    draft_id: UUID
    entity_id: UUID
    
    # Version info
    local_version: int
    remote_version: int
    
    # Content comparison
    conflicting_fields: list[str] = field(default_factory=list)
    local_changes: dict[str, Any] = field(default_factory=dict)
    remote_changes: dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AutosaveDraftsService:
    """
    Service for managing autosaved drafts.
    
    Handles automatic saving, version history, and draft recovery.
    """
    
    def __init__(
        self,
        autosave_interval_seconds: int = 30,
        max_versions: int = 50,
        default_expiry_hours: int = 24 * 7,  # 1 week
        entity_provider: callable | None = None,
    ) -> None:
        """Initialize the service."""
        self._drafts: dict[UUID, Draft] = {}
        self._user_drafts: dict[UUID, list[UUID]] = {}  # user_id -> draft_ids
        
        self.autosave_interval_seconds = autosave_interval_seconds
        self.max_versions = max_versions
        self.default_expiry_hours = default_expiry_hours
        
        # Entity provider for conflict detection
        self._entity_provider = entity_provider
    
    # ---------------------
    # Draft Management
    # ---------------------
    
    def create_draft(
        self,
        user_id: UUID,
        draft_type: DraftType,
        content: dict[str, Any] | None = None,
        entity_id: UUID | None = None,
        entity_type: str | None = None,
        session_id: str | None = None,
        form_id: str | None = None,
        route: str | None = None,
        expires_in_hours: int | None = None,
    ) -> Draft:
        """Create a new draft."""
        expires_at = None
        if expires_in_hours is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        elif self.default_expiry_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.default_expiry_hours)
        
        # Get base version if editing existing entity
        base_version = None
        if entity_id and entity_type:
            entity = self._get_entity(entity_type, entity_id)
            if entity:
                base_version = entity.get("version", 0)
        
        draft = Draft(
            draft_type=draft_type,
            user_id=user_id,
            content=content or {},
            entity_id=entity_id,
            entity_type=entity_type,
            session_id=session_id,
            form_id=form_id,
            route=route,
            expires_at=expires_at,
            base_version=base_version,
        )
        
        # Save initial version
        initial_version = DraftVersion(
            version_number=1,
            content=dict(content or {}),
            auto_saved=False,
            save_reason="Initial draft",
        )
        draft.versions.append(initial_version)
        draft.current_version = 1
        
        self._drafts[draft.id] = draft
        
        # Track by user
        if user_id not in self._user_drafts:
            self._user_drafts[user_id] = []
        self._user_drafts[user_id].append(draft.id)
        
        return draft
    
    def get_draft(self, draft_id: UUID) -> Draft | None:
        """Get a draft by ID."""
        return self._drafts.get(draft_id)
    
    def get_user_drafts(
        self,
        user_id: UUID,
        draft_type: DraftType | None = None,
        include_expired: bool = False,
    ) -> list[Draft]:
        """Get all drafts for a user."""
        draft_ids = self._user_drafts.get(user_id, [])
        drafts = [self._drafts[did] for did in draft_ids if did in self._drafts]
        
        # Filter by type
        if draft_type:
            drafts = [d for d in drafts if d.draft_type == draft_type]
        
        # Filter expired
        if not include_expired:
            drafts = [d for d in drafts if not d.is_expired]
        
        # Filter active only
        drafts = [
            d for d in drafts
            if d.status in (DraftStatus.ACTIVE, DraftStatus.SAVED)
        ]
        
        return sorted(drafts, key=lambda d: d.updated_at, reverse=True)
    
    def get_entity_draft(
        self,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> Draft | None:
        """Get an active draft for a specific entity."""
        drafts = self.get_user_drafts(user_id)
        
        for draft in drafts:
            if draft.entity_type == entity_type and draft.entity_id == entity_id:
                return draft
        
        return None
    
    # ---------------------
    # Autosave Operations
    # ---------------------
    
    def autosave(
        self,
        draft_id: UUID,
        content: dict[str, Any],
        changed_fields: list[str] | None = None,
    ) -> Draft | None:
        """Autosave draft content."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        if draft.status not in (DraftStatus.ACTIVE, DraftStatus.SAVED):
            return None
        
        # Update content
        old_content = draft.content
        draft.content = content
        draft.updated_at = datetime.now(timezone.utc)
        draft.last_autosave_at = datetime.now(timezone.utc)
        draft.status = DraftStatus.ACTIVE
        
        # Detect changed fields if not provided
        if changed_fields is None:
            changed_fields = self._detect_changed_fields(old_content, content)
        
        # Create new version
        new_version = DraftVersion(
            version_number=draft.current_version + 1,
            content=dict(content),
            auto_saved=True,
            changed_fields=changed_fields,
        )
        
        draft.versions.append(new_version)
        draft.current_version = new_version.version_number
        
        # Trim old versions if needed
        self._trim_versions(draft)
        
        # Check for conflicts
        self._check_for_conflicts(draft)
        
        return draft
    
    def save(
        self,
        draft_id: UUID,
        content: dict[str, Any],
        reason: str | None = None,
    ) -> Draft | None:
        """Manually save a draft."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        if draft.status not in (DraftStatus.ACTIVE, DraftStatus.SAVED):
            return None
        
        # Update content
        old_content = draft.content
        draft.content = content
        draft.updated_at = datetime.now(timezone.utc)
        draft.status = DraftStatus.SAVED
        
        # Create new version
        changed_fields = self._detect_changed_fields(old_content, content)
        new_version = DraftVersion(
            version_number=draft.current_version + 1,
            content=dict(content),
            auto_saved=False,
            save_reason=reason,
            changed_fields=changed_fields,
        )
        
        draft.versions.append(new_version)
        draft.current_version = new_version.version_number
        
        # Trim old versions
        self._trim_versions(draft)
        
        return draft
    
    def _detect_changed_fields(
        self,
        old_content: dict[str, Any],
        new_content: dict[str, Any],
    ) -> list[str]:
        """Detect which fields changed between versions."""
        changed = []
        
        all_keys = set(old_content.keys()) | set(new_content.keys())
        
        for key in all_keys:
            old_value = old_content.get(key)
            new_value = new_content.get(key)
            
            if old_value != new_value:
                changed.append(key)
        
        return changed
    
    def _trim_versions(self, draft: Draft) -> None:
        """Trim version history to max size."""
        if len(draft.versions) > self.max_versions:
            # Keep manual saves and most recent
            manual_saves = [v for v in draft.versions if not v.auto_saved]
            auto_saves = [v for v in draft.versions if v.auto_saved]
            
            # Keep most recent auto-saves
            recent_auto = auto_saves[-(self.max_versions - len(manual_saves)):]
            
            # Combine and sort
            draft.versions = sorted(
                manual_saves + recent_auto,
                key=lambda v: v.version_number,
            )
    
    # ---------------------
    # Draft Lifecycle
    # ---------------------
    
    def submit(self, draft_id: UUID) -> Draft | None:
        """Mark draft as submitted (entity created/updated)."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        draft.status = DraftStatus.SUBMITTED
        draft.updated_at = datetime.now(timezone.utc)
        
        return draft
    
    def discard(self, draft_id: UUID) -> Draft | None:
        """Discard a draft."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        draft.status = DraftStatus.DISCARDED
        draft.updated_at = datetime.now(timezone.utc)
        
        return draft
    
    def delete(self, draft_id: UUID) -> bool:
        """Permanently delete a draft."""
        if draft_id not in self._drafts:
            return False
        
        draft = self._drafts[draft_id]
        
        # Remove from user's drafts
        if draft.user_id in self._user_drafts:
            if draft_id in self._user_drafts[draft.user_id]:
                self._user_drafts[draft.user_id].remove(draft_id)
        
        del self._drafts[draft_id]
        return True
    
    # ---------------------
    # Version Management
    # ---------------------
    
    def get_versions(self, draft_id: UUID) -> list[DraftVersion]:
        """Get all versions of a draft."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return []
        
        return list(draft.versions)
    
    def restore_version(
        self,
        draft_id: UUID,
        version_number: int,
    ) -> Draft | None:
        """Restore a specific version."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        version = draft.get_version(version_number)
        if not version:
            return None
        
        # Create new version with restored content
        restored_version = DraftVersion(
            version_number=draft.current_version + 1,
            content=dict(version.content),
            auto_saved=False,
            save_reason=f"Restored from version {version_number}",
        )
        
        draft.versions.append(restored_version)
        draft.current_version = restored_version.version_number
        draft.content = dict(version.content)
        draft.updated_at = datetime.now(timezone.utc)
        
        return draft
    
    def compare_versions(
        self,
        draft_id: UUID,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any] | None:
        """Compare two versions of a draft."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        ver_a = draft.get_version(version_a)
        ver_b = draft.get_version(version_b)
        
        if not ver_a or not ver_b:
            return None
        
        changed_fields = self._detect_changed_fields(ver_a.content, ver_b.content)
        
        return {
            "version_a": version_a,
            "version_b": version_b,
            "changed_fields": changed_fields,
            "changes": {
                field: {
                    "old": ver_a.content.get(field),
                    "new": ver_b.content.get(field),
                }
                for field in changed_fields
            },
        }
    
    # ---------------------
    # Conflict Detection
    # ---------------------
    
    def _check_for_conflicts(self, draft: Draft) -> None:
        """Check if the draft conflicts with the current entity state."""
        if not draft.entity_id or not draft.entity_type:
            return
        
        entity = self._get_entity(draft.entity_type, draft.entity_id)
        if not entity:
            return
        
        current_version = entity.get("version", 0)
        
        if draft.base_version is not None and current_version > draft.base_version:
            draft.has_conflict = True
            draft.conflict_detected_at = datetime.now(timezone.utc)
    
    def get_conflict_info(self, draft_id: UUID) -> ConflictInfo | None:
        """Get detailed conflict information."""
        draft = self._drafts.get(draft_id)
        if not draft or not draft.has_conflict:
            return None
        
        if not draft.entity_id or not draft.entity_type:
            return None
        
        entity = self._get_entity(draft.entity_type, draft.entity_id)
        if not entity:
            return None
        
        # Find what fields conflict
        conflicting_fields = []
        local_changes = {}
        remote_changes = {}
        
        base_version_content = {}
        if draft.base_version:
            # Get the base version content from the first saved version
            for version in draft.versions:
                if version.version_number == 1:
                    base_version_content = version.content
                    break
        
        for field in set(draft.content.keys()) | set(entity.keys()):
            base_value = base_version_content.get(field)
            local_value = draft.content.get(field)
            remote_value = entity.get(field)
            
            # Both changed the same field
            if local_value != base_value and remote_value != base_value:
                if local_value != remote_value:
                    conflicting_fields.append(field)
                    local_changes[field] = local_value
                    remote_changes[field] = remote_value
        
        return ConflictInfo(
            draft_id=draft.id,
            entity_id=draft.entity_id,
            local_version=draft.current_version,
            remote_version=entity.get("version", 0),
            conflicting_fields=conflicting_fields,
            local_changes=local_changes,
            remote_changes=remote_changes,
        )
    
    def resolve_conflict(
        self,
        draft_id: UUID,
        resolution: ConflictResolution,
        merged_content: dict[str, Any] | None = None,
    ) -> Draft | None:
        """Resolve a draft conflict."""
        draft = self._drafts.get(draft_id)
        if not draft or not draft.has_conflict:
            return None
        
        if not draft.entity_id or not draft.entity_type:
            return None
        
        entity = self._get_entity(draft.entity_type, draft.entity_id)
        if not entity:
            return None
        
        if resolution == ConflictResolution.KEEP_LOCAL:
            # Keep local, update base version
            draft.base_version = entity.get("version", 0)
        
        elif resolution == ConflictResolution.KEEP_REMOTE:
            # Replace local with remote
            draft.content = dict(entity)
            draft.base_version = entity.get("version", 0)
            
            # Create version
            new_version = DraftVersion(
                version_number=draft.current_version + 1,
                content=dict(entity),
                auto_saved=False,
                save_reason="Resolved conflict - kept remote changes",
            )
            draft.versions.append(new_version)
            draft.current_version = new_version.version_number
        
        elif resolution == ConflictResolution.MERGE:
            if not merged_content:
                return None
            
            draft.content = merged_content
            draft.base_version = entity.get("version", 0)
            
            # Create version
            new_version = DraftVersion(
                version_number=draft.current_version + 1,
                content=dict(merged_content),
                auto_saved=False,
                save_reason="Resolved conflict - merged changes",
            )
            draft.versions.append(new_version)
            draft.current_version = new_version.version_number
        
        draft.has_conflict = False
        draft.conflict_detected_at = None
        draft.updated_at = datetime.now(timezone.utc)
        
        return draft
    
    # ---------------------
    # Recovery
    # ---------------------
    
    def get_recoverable_drafts(
        self,
        user_id: UUID,
        session_id: str | None = None,
    ) -> list[DraftRecovery]:
        """Get drafts that can be recovered (after crash/refresh)."""
        recoverable = []
        
        drafts = self.get_user_drafts(user_id, include_expired=False)
        
        for draft in drafts:
            # Skip if from current session
            if session_id and draft.session_id == session_id:
                continue
            
            # Only active or saved drafts
            if draft.status not in (DraftStatus.ACTIVE, DraftStatus.SAVED):
                continue
            
            # Generate preview
            preview = self._generate_preview(draft)
            
            recovery = DraftRecovery(
                draft_id=draft.id,
                draft_type=draft.draft_type,
                entity_id=draft.entity_id,
                last_saved_at=draft.updated_at,
                content_preview=preview,
            )
            
            recoverable.append(recovery)
        
        return recoverable
    
    def recover_draft(
        self,
        draft_id: UUID,
        new_session_id: str | None = None,
    ) -> Draft | None:
        """Recover a draft to a new session."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        draft.session_id = new_session_id
        draft.status = DraftStatus.RECOVERED
        draft.updated_at = datetime.now(timezone.utc)
        
        return draft
    
    def _generate_preview(self, draft: Draft) -> str:
        """Generate a preview of draft content."""
        content = draft.content
        
        # Try common preview fields
        for field in ["title", "name", "subject", "description"]:
            if field in content and content[field]:
                preview = str(content[field])[:100]
                return preview + "..." if len(str(content[field])) > 100 else preview
        
        return f"{draft.draft_type.value} draft"
    
    # ---------------------
    # Cleanup
    # ---------------------
    
    def cleanup_expired(self) -> int:
        """Clean up expired drafts."""
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for draft_id in list(self._drafts.keys()):
            draft = self._drafts[draft_id]
            
            if draft.expires_at and now > draft.expires_at:
                draft.status = DraftStatus.EXPIRED
                expired_count += 1
        
        return expired_count
    
    def cleanup_submitted(
        self,
        older_than_hours: int = 24,
    ) -> int:
        """Clean up old submitted drafts."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        deleted_count = 0
        
        for draft_id in list(self._drafts.keys()):
            draft = self._drafts[draft_id]
            
            if draft.status == DraftStatus.SUBMITTED and draft.updated_at < cutoff:
                self.delete(draft_id)
                deleted_count += 1
        
        return deleted_count
    
    # ---------------------
    # Statistics
    # ---------------------
    
    def get_draft_stats(self, user_id: UUID) -> dict[str, Any]:
        """Get draft statistics for a user."""
        drafts = self.get_user_drafts(user_id, include_expired=True)
        
        stats = {
            "total_drafts": len(drafts),
            "active_drafts": sum(1 for d in drafts if d.status == DraftStatus.ACTIVE),
            "saved_drafts": sum(1 for d in drafts if d.status == DraftStatus.SAVED),
            "with_conflicts": sum(1 for d in drafts if d.has_conflict),
            "by_type": {},
            "total_versions": sum(d.version_count for d in drafts),
        }
        
        by_type = cast(dict[str, int], stats["by_type"])
        for draft in drafts:
            dt = draft.draft_type.value
            if dt not in by_type:
                by_type[dt] = 0
            by_type[dt] += 1
        
        return stats
    
    # ---------------------
    # Entity Provider (production)
    # ---------------------

    def _get_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> dict[str, Any] | None:
        """Get the current entity snapshot for conflict detection."""
        if not self._entity_provider:
            raise ValueError("AutosaveDraftsService requires an entity_provider in production")
        return self._entity_provider(entity_type, entity_id)


def get_autosave_drafts_service(session: AsyncSession) -> AutosaveDraftsService:
    """Create an autosave drafts service wired to the database."""
    sync_session = session.sync_session
    return AutosaveDraftsService(
        entity_provider=build_entity_getter(sync_session),
    )

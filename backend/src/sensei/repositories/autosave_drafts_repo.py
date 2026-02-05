"""
Database repository for Autosave Drafts.

Provides async database access for draft persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.service_persistence import (
    DraftDB,
    DraftVersionDB,
    DraftStatusDB,
)


class AutosaveDraftsRepository:
    """Repository for autosave draft database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session
    
    async def create_draft(
        self,
        user_id: UUID,
        draft_type: str,
        content: dict[str, Any] | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        session_id: str | None = None,
        form_id: str | None = None,
        route: str | None = None,
        expires_in_hours: int | None = None,
        base_version: int | None = None,
    ) -> DraftDB:
        """Create a new draft."""
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        draft = DraftDB(
            user_id=user_id,
            draft_type=draft_type,
            content=content or {},
            entity_type=entity_type,
            entity_id=entity_id,
            session_id=session_id,
            form_id=form_id,
            route=route,
            expires_at=expires_at,
            base_version=base_version,
            status=DraftStatusDB.ACTIVE.value,
        )
        self._session.add(draft)
        await self._session.flush()
        await self._session.refresh(draft)
        
        # Create initial version
        await self.add_version(
            draft_id=draft.id,
            version_number=1,
            content=content or {},
            auto_saved=False,
            save_reason="Initial draft",
        )
        
        return draft
    
    async def get_draft(self, draft_id: UUID) -> DraftDB | None:
        """Get a draft by ID."""
        result = await self._session.execute(
            select(DraftDB).where(DraftDB.id == draft_id)
        )
        return result.scalar_one_or_none()
    
    async def update_draft(
        self,
        draft_id: UUID,
        content: dict[str, Any],
        auto_saved: bool = True,
        save_reason: str | None = None,
        changed_fields: list[str] | None = None,
    ) -> DraftDB | None:
        """Update a draft with new content."""
        draft = await self.get_draft(draft_id)
        if not draft:
            return None
        
        draft.content = content
        draft.current_version += 1
        draft.updated_at = datetime.now(timezone.utc)
        
        # Add version record
        await self.add_version(
            draft_id=draft_id,
            version_number=draft.current_version,
            content=content,
            auto_saved=auto_saved,
            save_reason=save_reason,
            changed_fields=changed_fields,
        )
        
        await self._session.flush()
        await self._session.refresh(draft)
        return draft
    
    async def set_status(self, draft_id: UUID, status: str) -> DraftDB | None:
        """Update draft status."""
        draft = await self.get_draft(draft_id)
        if not draft:
            return None
        
        draft.status = status
        draft.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(draft)
        return draft
    
    async def delete_draft(self, draft_id: UUID) -> bool:
        """Delete a draft and its versions."""
        result = await self._session.execute(
            delete(DraftDB).where(DraftDB.id == draft_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def list_user_drafts(
        self,
        user_id: UUID,
        draft_type: str | None = None,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[DraftDB]:
        """List drafts for a user."""
        query = select(DraftDB).where(
            DraftDB.user_id == user_id,
            DraftDB.status == DraftStatusDB.ACTIVE.value,
        )
        
        if draft_type:
            query = query.where(DraftDB.draft_type == draft_type)
        
        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.where(
                or_(
                    DraftDB.expires_at.is_(None),
                    DraftDB.expires_at > now,
                )
            )
        
        query = query.order_by(DraftDB.updated_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def get_draft_for_entity(
        self,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> DraftDB | None:
        """Get an active draft for a specific entity."""
        result = await self._session.execute(
            select(DraftDB).where(
                and_(
                    DraftDB.user_id == user_id,
                    DraftDB.entity_type == entity_type,
                    DraftDB.entity_id == entity_id,
                    DraftDB.status == DraftStatusDB.ACTIVE.value,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def expire_old_drafts(self) -> int:
        """Mark expired drafts."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(DraftDB).where(
                and_(
                    DraftDB.status == DraftStatusDB.ACTIVE.value,
                    DraftDB.expires_at.isnot(None),
                    DraftDB.expires_at < now,
                )
            )
        )
        drafts = list(result.scalars().all())
        
        for draft in drafts:
            draft.status = DraftStatusDB.EXPIRED.value
        
        if drafts:
            await self._session.flush()
        
        return len(drafts)
    
    async def recover_drafts(
        self,
        user_id: UUID,
        session_id: str | None = None,
    ) -> list[DraftDB]:
        """Find drafts that can be recovered after a session loss."""
        query = select(DraftDB).where(
            and_(
                DraftDB.user_id == user_id,
                DraftDB.status == DraftStatusDB.ACTIVE.value,
            )
        )
        
        if session_id:
            query = query.where(DraftDB.session_id == session_id)
        
        result = await self._session.execute(query)
        drafts = list(result.scalars().all())
        
        # Mark as recovered
        for draft in drafts:
            draft.recovered_at = datetime.now(timezone.utc)
            draft.status = DraftStatusDB.RECOVERED.value
        
        if drafts:
            await self._session.flush()
        
        return drafts
    
    # --------------------------------------------------------------------------
    # Draft Versions
    # --------------------------------------------------------------------------
    
    async def add_version(
        self,
        draft_id: UUID,
        version_number: int,
        content: dict[str, Any],
        auto_saved: bool = True,
        save_reason: str | None = None,
        changed_fields: list[str] | None = None,
    ) -> DraftVersionDB:
        """Add a version record for a draft."""
        version = DraftVersionDB(
            draft_id=draft_id,
            version_number=version_number,
            content=content,
            auto_saved=auto_saved,
            save_reason=save_reason,
            changed_fields=changed_fields,
        )
        self._session.add(version)
        await self._session.flush()
        await self._session.refresh(version)
        return version
    
    async def list_versions(
        self,
        draft_id: UUID,
        limit: int = 50,
    ) -> list[DraftVersionDB]:
        """List versions for a draft."""
        result = await self._session.execute(
            select(DraftVersionDB)
            .where(DraftVersionDB.draft_id == draft_id)
            .order_by(DraftVersionDB.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_version(
        self,
        draft_id: UUID,
        version_number: int,
    ) -> DraftVersionDB | None:
        """Get a specific version of a draft."""
        result = await self._session.execute(
            select(DraftVersionDB).where(
                and_(
                    DraftVersionDB.draft_id == draft_id,
                    DraftVersionDB.version_number == version_number,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def prune_versions(
        self,
        draft_id: UUID,
        keep_count: int = 50,
    ) -> int:
        """Prune old versions, keeping only the most recent ones."""
        # Get versions to keep
        versions = await self.list_versions(draft_id, limit=keep_count)
        keep_ids = {v.id for v in versions}
        
        if not keep_ids:
            return 0
        
        # Delete older versions
        result = await self._session.execute(
            delete(DraftVersionDB).where(
                and_(
                    DraftVersionDB.draft_id == draft_id,
                    ~DraftVersionDB.id.in_(keep_ids),
                )
            )
        )
        return result.rowcount  # type: ignore[return-value]


async def get_autosave_drafts_repo(session: AsyncSession) -> AutosaveDraftsRepository:
    """Dependency injection helper for AutosaveDraftsRepository."""
    return AutosaveDraftsRepository(session)

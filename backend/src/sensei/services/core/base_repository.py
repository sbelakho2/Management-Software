"""
Base Repository with tenant/org scoping (#431, #437).

Provides a consistent DB-backed service pattern that all persistent
services should extend.  Every query automatically scopes to the
current ``tenant_id`` when multi-tenancy is enabled.

Usage::

    class InspectionRepository(BaseRepository[Inspection]):
        model = Inspection

    repo = InspectionRepository(session, tenant_id="acme-corp")
    inspections = await repo.list(limit=50, offset=0)
    single = await repo.get(some_uuid)
    created = await repo.create({"title": "Incoming", "status": "open"})
    updated = await repo.update(some_uuid, {"status": "closed"})
    deleted = await repo.soft_delete(some_uuid)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

M = TypeVar("M")  # SQLAlchemy model type


class BaseRepository(Generic[M]):
    """Generic, tenant-aware repository for CRUD + list operations.

    Sub-classes MUST set the ``model`` class attribute to the
    SQLAlchemy model they manage.

    All queries are automatically scoped to ``tenant_id`` when the
    model has a ``tenant_id`` column **and** a non-None tenant_id
    was provided at construction time.
    """

    model: Type[M]

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: Optional[str] = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self._has_tenant_col: bool = hasattr(self.model, "tenant_id")
        self._has_soft_delete: bool = hasattr(self.model, "deleted_at")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_query(self) -> Select:
        """Return a SELECT scoped to tenant and excluding soft-deleted rows."""
        stmt = select(self.model)
        if self._has_tenant_col and self.tenant_id is not None:
            stmt = stmt.where(self.model.tenant_id == self.tenant_id)  # type: ignore[attr-defined]
        if self._has_soft_delete:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    def _apply_filters(self, stmt: Select, filters: Dict[str, Any]) -> Select:
        """Apply simple equality filters to a query."""
        for col_name, value in filters.items():
            if hasattr(self.model, col_name) and value is not None:
                stmt = stmt.where(getattr(self.model, col_name) == value)
        return stmt

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def get(self, entity_id: UUID) -> Optional[M]:
        """Fetch a single entity by primary key."""
        stmt = self._base_query().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = True,
        filters: Dict[str, Any] | None = None,
    ) -> Sequence[M]:
        """List entities with pagination, ordering and optional filters."""
        stmt = self._base_query()

        if filters:
            stmt = self._apply_filters(stmt, filters)

        # Ordering
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            stmt = stmt.order_by(col.desc() if descending else col.asc())
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, *, filters: Dict[str, Any] | None = None) -> int:
        """Return total count (for pagination headers)."""
        stmt = select(func.count()).select_from(self.model)

        if self._has_tenant_col and self.tenant_id is not None:
            stmt = stmt.where(self.model.tenant_id == self.tenant_id)  # type: ignore[attr-defined]
        if self._has_soft_delete:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if filters:
            for col_name, value in filters.items():
                if hasattr(self.model, col_name) and value is not None:
                    stmt = stmt.where(getattr(self.model, col_name) == value)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, data: Dict[str, Any]) -> M:
        """Create a new entity from a dict of column values."""
        # Inject tenant_id if multi-tenant
        if self._has_tenant_col and self.tenant_id is not None:
            data.setdefault("tenant_id", self.tenant_id)

        instance = self.model(**data)  # type: ignore[call-arg]
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, entity_id: UUID, data: Dict[str, Any]) -> Optional[M]:
        """Update an existing entity. Returns None if not found."""
        instance = await self.get(entity_id)
        if instance is None:
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        # Auto-set updated_at if available
        if hasattr(instance, "updated_at"):
            instance.updated_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def soft_delete(self, entity_id: UUID) -> bool:
        """Soft-delete (set deleted_at) if model supports it, else hard-delete."""
        instance = await self.get(entity_id)
        if instance is None:
            return False

        if self._has_soft_delete:
            instance.deleted_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
            await self.session.flush()
        else:
            await self.session.delete(instance)
            await self.session.flush()

        return True

    async def hard_delete(self, entity_id: UUID) -> bool:
        """Permanently delete an entity."""
        instance = await self.get(entity_id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[M]:
        """Create multiple entities in a single flush."""
        instances = []
        for data in items:
            if self._has_tenant_col and self.tenant_id is not None:
                data.setdefault("tenant_id", self.tenant_id)
            instance = self.model(**data)  # type: ignore[call-arg]
            self.session.add(instance)
            instances.append(instance)

        await self.session.flush()
        for inst in instances:
            await self.session.refresh(inst)
        return instances

    async def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        if self._has_tenant_col and self.tenant_id is not None:
            stmt = stmt.where(self.model.tenant_id == self.tenant_id)  # type: ignore[attr-defined]
        if self._has_soft_delete:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]

        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def search(
        self,
        *,
        text_columns: List[str],
        query: str,
        limit: int = 20,
    ) -> Sequence[M]:
        """Simple ILIKE search across multiple text columns."""
        if not query.strip():
            return await self.list(limit=limit)

        stmt = self._base_query()
        pattern = f"%{query}%"
        conditions = []
        for col_name in text_columns:
            if hasattr(self.model, col_name):
                conditions.append(getattr(self.model, col_name).ilike(pattern))

        if conditions:
            from sqlalchemy import or_
            stmt = stmt.where(or_(*conditions))

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

"""
Database repository for SavedViews.

Provides async database access for saved view persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.service_persistence import SavedViewDB
from sensei.services.saved_views import (
    SavedView,
    SavedViewEntityType,
    ViewVisibility,
    FilterCondition,
    FilterOperator,
    SortField,
    SortDirection,
    ColumnConfig,
    FilterLogic,
    DatePreset,
)


def _condition_to_dict(c: FilterCondition) -> dict[str, Any]:
    """Convert a FilterCondition to a dict for JSON storage."""
    return {
        "field": c.field,
        "operator": c.operator.value,
        "value": c.value,
        "second_value": c.second_value,
        "date_preset": c.date_preset.value if c.date_preset else None,
        "case_sensitive": c.case_sensitive,
    }


def _dict_to_condition(d: dict[str, Any]) -> FilterCondition:
    """Convert a dict from JSON to a FilterCondition."""
    return FilterCondition(
        field=d["field"],
        operator=FilterOperator(d["operator"]),
        value=d.get("value"),
        second_value=d.get("second_value"),
        date_preset=DatePreset(d["date_preset"]) if d.get("date_preset") else None,
        case_sensitive=d.get("case_sensitive", False),
    )


def _sort_to_dict(s: SortField) -> dict[str, Any]:
    """Convert a SortField to a dict for JSON storage."""
    return {
        "field": s.field,
        "direction": s.direction.value,
    }


def _dict_to_sort(d: dict[str, Any]) -> SortField:
    """Convert a dict from JSON to a SortField."""
    return SortField(
        field=d["field"],
        direction=SortDirection(d["direction"]),
    )


def _column_to_dict(c: ColumnConfig) -> dict[str, Any]:
    """Convert a ColumnConfig to a dict for JSON storage."""
    return {
        "field": c.field,
        "label": c.label,
        "width": c.width,
        "visible": c.visible,
        "order": c.order,
    }


def _dict_to_column(d: dict[str, Any]) -> ColumnConfig:
    """Convert a dict from JSON to a ColumnConfig."""
    return ColumnConfig(
        field=d["field"],
        label=d.get("label"),
        width=d.get("width"),
        visible=d.get("visible", True),
        order=d.get("order", 0),
    )


def _db_to_saved_view(db_view: SavedViewDB) -> SavedView:
    """Convert a database model to a SavedView dataclass."""
    conditions = []
    if db_view.conditions:
        conditions = [_dict_to_condition(c) for c in db_view.conditions]
    
    sort_fields = []
    if db_view.sort_fields:
        sort_fields = [_dict_to_sort(s) for s in db_view.sort_fields]
    
    columns = []
    if db_view.columns:
        columns = [_dict_to_column(c) for c in db_view.columns]
    
    return SavedView(
        id=str(db_view.id),
        name=db_view.name,
        entity_type=SavedViewEntityType(db_view.entity_type),
        owner_id=db_view.owner_id,
        visibility=ViewVisibility(db_view.visibility),
        description=db_view.description or "",
        conditions=conditions,
        sort_fields=sort_fields,
        columns=columns,
        page_size=25,  # Default, not stored in DB currently
        is_default=False,  # Not stored in DB currently
        icon=db_view.icon,
        color=db_view.color,
        created_at=db_view.created_at,
        updated_at=db_view.updated_at,
        use_count=db_view.use_count,
        last_used_at=db_view.last_used_at,
        team_ids=[db_view.team_id] if db_view.team_id else [],
        pinned=db_view.is_pinned,
    )


def _saved_view_to_db_dict(view: SavedView) -> dict[str, Any]:
    """Convert a SavedView dataclass to a dict for DB insert/update."""
    return {
        "name": view.name,
        "description": view.description,
        "entity_type": view.entity_type.value,
        "owner_id": view.owner_id,
        "visibility": view.visibility.value,
        "team_id": view.team_ids[0] if view.team_ids else None,
        "conditions": [_condition_to_dict(c) for c in view.conditions] if view.conditions else None,
        "sort_fields": [_sort_to_dict(s) for s in view.sort_fields] if view.sort_fields else None,
        "columns": [_column_to_dict(c) for c in view.columns] if view.columns else None,
        "icon": view.icon,
        "color": view.color,
        "is_favorite": False,
        "is_pinned": view.pinned,
        "use_count": view.use_count,
        "last_used_at": view.last_used_at,
    }


class SavedViewsRepository:
    """Repository for saved view database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session
    
    async def create(self, view: SavedView) -> SavedView:
        """Create a new saved view in the database."""
        db_view = SavedViewDB(
            id=UUID(view.id) if isinstance(view.id, str) else view.id,
            **_saved_view_to_db_dict(view),
        )
        self._session.add(db_view)
        await self._session.flush()
        await self._session.refresh(db_view)
        return _db_to_saved_view(db_view)
    
    async def get(self, view_id: str | UUID) -> SavedView | None:
        """Get a saved view by ID."""
        vid = UUID(view_id) if isinstance(view_id, str) else view_id
        result = await self._session.execute(
            select(SavedViewDB).where(SavedViewDB.id == vid)
        )
        db_view = result.scalar_one_or_none()
        if db_view:
            return _db_to_saved_view(db_view)
        return None
    
    async def update(self, view_id: str | UUID, **updates: Any) -> SavedView | None:
        """Update a saved view."""
        vid = UUID(view_id) if isinstance(view_id, str) else view_id
        result = await self._session.execute(
            select(SavedViewDB).where(SavedViewDB.id == vid)
        )
        db_view = result.scalar_one_or_none()
        if not db_view:
            return None
        
        for key, value in updates.items():
            if key == "conditions" and value is not None:
                value = [_condition_to_dict(c) for c in value]
            elif key == "sort_fields" and value is not None:
                value = [_sort_to_dict(s) for s in value]
            elif key == "columns" and value is not None:
                value = [_column_to_dict(c) for c in value]
            elif key == "visibility" and value is not None:
                value = value.value if hasattr(value, "value") else value
            
            if hasattr(db_view, key):
                setattr(db_view, key, value)
        
        db_view.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(db_view)
        return _db_to_saved_view(db_view)
    
    async def delete(self, view_id: str | UUID) -> bool:
        """Delete a saved view."""
        vid = UUID(view_id) if isinstance(view_id, str) else view_id
        result = await self._session.execute(
            delete(SavedViewDB).where(SavedViewDB.id == vid)
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def list_for_user(
        self,
        user_id: UUID,
        entity_type: SavedViewEntityType | None = None,
        include_team: bool = True,
        include_organization: bool = True,
        team_ids: list[UUID] | None = None,
    ) -> list[SavedView]:
        """List views accessible to a user."""
        # Build base query conditions
        conditions = []
        
        # User's own views
        own_views = SavedViewDB.owner_id == user_id
        
        # Public views
        public_views = SavedViewDB.visibility == ViewVisibility.PUBLIC.value
        
        # Organization views
        org_views = SavedViewDB.visibility == ViewVisibility.ORGANIZATION.value
        
        # Team views
        team_conditions = []
        if include_team and team_ids:
            for tid in team_ids:
                team_conditions.append(
                    and_(
                        SavedViewDB.visibility == ViewVisibility.TEAM.value,
                        SavedViewDB.team_id == tid,
                    )
                )
        
        # Combine conditions
        visibility_conditions = [own_views, public_views]
        if include_organization:
            visibility_conditions.append(org_views)
        visibility_conditions.extend(team_conditions)
        
        from sqlalchemy import or_
        
        query = select(SavedViewDB).where(or_(*visibility_conditions))
        
        if entity_type:
            query = query.where(SavedViewDB.entity_type == entity_type.value)
        
        query = query.order_by(SavedViewDB.position, SavedViewDB.name)
        
        result = await self._session.execute(query)
        db_views = result.scalars().all()
        
        return [_db_to_saved_view(v) for v in db_views]
    
    async def record_usage(self, view_id: str | UUID) -> None:
        """Record a view usage."""
        vid = UUID(view_id) if isinstance(view_id, str) else view_id
        result = await self._session.execute(
            select(SavedViewDB).where(SavedViewDB.id == vid)
        )
        db_view = result.scalar_one_or_none()
        if db_view:
            db_view.use_count += 1
            db_view.last_used_at = datetime.now(timezone.utc)
            await self._session.flush()
    
    async def set_pinned(self, view_id: str | UUID, pinned: bool) -> bool:
        """Set the pinned status of a view."""
        vid = UUID(view_id) if isinstance(view_id, str) else view_id
        result = await self._session.execute(
            select(SavedViewDB).where(SavedViewDB.id == vid)
        )
        db_view = result.scalar_one_or_none()
        if db_view:
            db_view.is_pinned = pinned
            await self._session.flush()
            return True
        return False


async def get_saved_views_repo(session: AsyncSession) -> SavedViewsRepository:
    """Dependency injection helper for SavedViewsRepository."""
    return SavedViewsRepository(session)

"""
Sensei OS Base Repository

Generic CRUD repository for all database models.
Provides common database operations with filtering, pagination, and sorting.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.api.exceptions import NotFoundError
from sensei.api.schemas import FilterOperator, SortOrder
from sensei.models.base import Base as SenseiBaseModel


def escape_like_pattern(value: str) -> str:
    """
    Escape special characters in LIKE/ILIKE patterns to prevent SQL injection.
    
    PostgreSQL LIKE patterns treat '%', '_', and '\\' as special characters.
    This function escapes them so they are treated literally.
    
    Args:
        value: The search string to escape
        
    Returns:
        Escaped string safe for use in LIKE/ILIKE patterns
    """
    # Escape backslash first (since it's the escape character)
    value = value.replace("\\", "\\\\")
    # Escape percent sign
    value = value.replace("%", "\\%")
    # Escape underscore
    value = value.replace("_", "\\_")
    return value

# Type variable for the model class
ModelT = TypeVar("ModelT", bound=SenseiBaseModel)


class BaseRepository(Generic[ModelT]):
    """
    Base repository with common CRUD operations.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(User, db)
                
        repo = UserRepository(db)
        users = await repo.get_all()
    """
    
    def __init__(
        self,
        model: Type[ModelT],
        db: AsyncSession,
        *,
        soft_delete: bool = True,
    ):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            db: Async database session
            soft_delete: Whether to use soft delete (default: True)
        """
        self.model = model
        self.db = db
        self.soft_delete = soft_delete
    
    # =========================================================================
    # Read Operations
    # =========================================================================
    
    async def get_by_id(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
    ) -> Optional[ModelT]:
        """
        Get entity by ID.
        
        Args:
            id: Entity UUID
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            
        Returns:
            Entity or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_id_or_raise(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
    ) -> ModelT:
        """
        Get entity by ID or raise NotFoundError.
        
        Args:
            id: Entity UUID
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            
        Returns:
            Entity
            
        Raises:
            NotFoundError: If entity not found
        """
        entity = await self.get_by_id(
            id,
            include_deleted=include_deleted,
            load_relations=load_relations,
        )
        
        if not entity:
            raise NotFoundError(
                resource=self.model.__name__,
                identifier=str(id),
            )
        
        return entity
    
    async def get_by_ids(
        self,
        ids: List[UUID],
        *,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
    ) -> List[ModelT]:
        """
        Get multiple entities by IDs.
        
        Args:
            ids: List of entity UUIDs
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            
        Returns:
            List of entities (may be fewer than requested if some not found)
        """
        if not ids:
            return []
        
        query = select(self.model).where(self.model.id.in_(ids))
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_all(
        self,
        *,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
    ) -> List[ModelT]:
        """
        Get all entities.
        
        Args:
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            
        Returns:
            List of all entities
        """
        query = select(self.model)
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
        filters: Optional[List[FilterOperator]] = None,
        sort: Optional[List[SortOrder]] = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        load_relations: Optional[List[str]] = None,
    ) -> Tuple[List[ModelT], int]:
        """
        Get paginated entities with optional filtering, sorting, and search.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            include_deleted: Include soft-deleted entities
            filters: List of filter operators
            sort: List of sort orders
            search: Full-text search query
            search_fields: Fields to search in
            load_relations: List of relationship names to eager load
            
        Returns:
            Tuple of (entities, total_count)
        """
        # Base query
        query = select(self.model)
        count_query = select(func.count(self.model.id))
        
        # Exclude deleted
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
            count_query = count_query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        # Apply filters
        if filters:
            for f in filters:
                condition = self._build_filter_condition(f)
                if condition is not None:
                    query = query.where(condition)
                    count_query = count_query.where(condition)
        
        # Apply search
        if search and search_fields:
            search_conditions = []
            escaped_search = escape_like_pattern(search)
            for field_name in search_fields:
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    search_conditions.append(field.ilike(f"%{escaped_search}%"))
            
            if search_conditions:
                query = query.where(or_(*search_conditions))
                count_query = count_query.where(or_(*search_conditions))
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply sorting
        if sort:
            for s in sort:
                if hasattr(self.model, s.field):
                    field = getattr(self.model, s.field)
                    query = query.order_by(desc(field) if s.direction == "desc" else asc(field))
        else:
            # Default sort by created_at desc if available
            if hasattr(self.model, "created_at"):
                query = query.order_by(desc(self.model.created_at))
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Load relations
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        entities = list(result.scalars().all())
        
        return entities, total
    
    async def exists(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
    ) -> bool:
        """Check if entity exists by ID."""
        query = select(func.count(self.model.id)).where(self.model.id == id)
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        return count > 0
    
    async def count(
        self,
        *,
        include_deleted: bool = False,
        filters: Optional[List[FilterOperator]] = None,
    ) -> int:
        """Count entities with optional filters."""
        query = select(func.count(self.model.id))
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        if filters:
            for f in filters:
                condition = self._build_filter_condition(f)
                if condition is not None:
                    query = query.where(condition)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    # =========================================================================
    # Write Operations
    # =========================================================================
    
    async def create(
        self,
        data: Dict[str, Any],
        *,
        created_by: Optional[UUID] = None,
        commit: bool = True,
    ) -> ModelT:
        """
        Create a new entity.
        
        Args:
            data: Entity data dictionary
            created_by: User ID who created the entity
            commit: Whether to commit the transaction
            
        Returns:
            Created entity
        """
        # Add audit fields
        if created_by and hasattr(self.model, "created_by"):
            data["created_by"] = created_by
        
        entity = self.model(**data)
        self.db.add(entity)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(entity)
        else:
            await self.db.flush()
        
        return entity
    
    async def create_many(
        self,
        items: List[Dict[str, Any]],
        *,
        created_by: Optional[UUID] = None,
        commit: bool = True,
    ) -> List[ModelT]:
        """
        Create multiple entities.
        
        Args:
            items: List of entity data dictionaries
            created_by: User ID who created the entities
            commit: Whether to commit the transaction
            
        Returns:
            List of created entities
        """
        entities = []
        
        for data in items:
            if created_by and hasattr(self.model, "created_by"):
                data["created_by"] = created_by
            
            entity = self.model(**data)
            self.db.add(entity)
            entities.append(entity)
        
        if commit:
            await self.db.commit()
            for entity in entities:
                await self.db.refresh(entity)
        else:
            await self.db.flush()
        
        return entities
    
    async def update(
        self,
        id: UUID,
        data: Dict[str, Any],
        *,
        updated_by: Optional[UUID] = None,
        commit: bool = True,
    ) -> Optional[ModelT]:
        """
        Update an entity by ID.
        
        Args:
            id: Entity UUID
            data: Update data dictionary
            updated_by: User ID who updated the entity
            commit: Whether to commit the transaction
            
        Returns:
            Updated entity or None if not found
        """
        entity = await self.get_by_id(id)
        
        if not entity:
            return None
        
        # Add audit fields
        if hasattr(entity, "updated_at"):
            data["updated_at"] = datetime.now(timezone.utc)
        
        if updated_by and hasattr(entity, "updated_by"):
            data["updated_by"] = updated_by
        
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(entity)
        else:
            await self.db.flush()
        
        return entity
    
    async def update_or_raise(
        self,
        id: UUID,
        data: Dict[str, Any],
        *,
        updated_by: Optional[UUID] = None,
        commit: bool = True,
    ) -> ModelT:
        """
        Update an entity by ID or raise NotFoundError.
        
        Args:
            id: Entity UUID
            data: Update data dictionary
            updated_by: User ID who updated the entity
            commit: Whether to commit the transaction
            
        Returns:
            Updated entity
            
        Raises:
            NotFoundError: If entity not found
        """
        entity = await self.update(id, data, updated_by=updated_by, commit=commit)
        
        if not entity:
            raise NotFoundError(
                resource=self.model.__name__,
                identifier=str(id),
            )
        
        return entity
    
    async def delete(
        self,
        id: UUID,
        *,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False,
        commit: bool = True,
    ) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: Entity UUID
            deleted_by: User ID who deleted the entity
            hard_delete: Force hard delete instead of soft delete
            commit: Whether to commit the transaction
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        
        if not entity:
            return False
        
        if self.soft_delete and hasattr(entity, "deleted_at") and not hard_delete:
            # Soft delete
            entity.deleted_at = datetime.now(timezone.utc)
            if deleted_by and hasattr(entity, "deleted_by"):
                entity.deleted_by = deleted_by
        else:
            # Hard delete
            await self.db.delete(entity)
        
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        
        return True
    
    async def delete_or_raise(
        self,
        id: UUID,
        *,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False,
        commit: bool = True,
    ) -> None:
        """
        Delete an entity by ID or raise NotFoundError.
        
        Args:
            id: Entity UUID
            deleted_by: User ID who deleted the entity
            hard_delete: Force hard delete instead of soft delete
            commit: Whether to commit the transaction
            
        Raises:
            NotFoundError: If entity not found
        """
        deleted = await self.delete(
            id,
            deleted_by=deleted_by,
            hard_delete=hard_delete,
            commit=commit,
        )
        
        if not deleted:
            raise NotFoundError(
                resource=self.model.__name__,
                identifier=str(id),
            )
    
    async def delete_many(
        self,
        ids: List[UUID],
        *,
        deleted_by: Optional[UUID] = None,
        hard_delete: bool = False,
        commit: bool = True,
    ) -> int:
        """
        Delete multiple entities by IDs.
        
        Args:
            ids: List of entity UUIDs
            deleted_by: User ID who deleted the entities
            hard_delete: Force hard delete instead of soft delete
            commit: Whether to commit the transaction
            
        Returns:
            Number of entities deleted
        """
        if not ids:
            return 0
        
        entities = await self.get_by_ids(ids)
        
        for entity in entities:
            if self.soft_delete and hasattr(entity, "deleted_at") and not hard_delete:
                entity.deleted_at = datetime.now(timezone.utc)
                if deleted_by and hasattr(entity, "deleted_by"):
                    entity.deleted_by = deleted_by
            else:
                await self.db.delete(entity)
        
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        
        return len(entities)
    
    async def restore(
        self,
        id: UUID,
        *,
        commit: bool = True,
    ) -> Optional[ModelT]:
        """
        Restore a soft-deleted entity.
        
        Args:
            id: Entity UUID
            commit: Whether to commit the transaction
            
        Returns:
            Restored entity or None if not found
        """
        if not self.soft_delete or not hasattr(self.model, "deleted_at"):
            return None
        
        entity = await self.get_by_id(id, include_deleted=True)
        
        if not entity or not entity.deleted_at:
            return None
        
        entity.deleted_at = None
        if hasattr(entity, "deleted_by"):
            entity.deleted_by = None
        
        if commit:
            await self.db.commit()
            await self.db.refresh(entity)
        else:
            await self.db.flush()
        
        return entity
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _build_filter_condition(self, filter_op: FilterOperator):
        """Build SQLAlchemy filter condition from FilterOperator."""
        if not hasattr(self.model, filter_op.field):
            return None
        
        field = getattr(self.model, filter_op.field)
        value = filter_op.value
        operator = filter_op.operator.lower()
        
        operators = {
            "eq": lambda f, v: f == v,
            "ne": lambda f, v: f != v,
            "gt": lambda f, v: f > v,
            "gte": lambda f, v: f >= v,
            "lt": lambda f, v: f < v,
            "lte": lambda f, v: f <= v,
            "like": lambda f, v: f.like(f"%{escape_like_pattern(str(v))}%"),
            "ilike": lambda f, v: f.ilike(f"%{escape_like_pattern(str(v))}%"),
            "in": lambda f, v: f.in_(v if isinstance(v, list) else [v]),
            "notin": lambda f, v: ~f.in_(v if isinstance(v, list) else [v]),
            "isnull": lambda f, v: f.is_(None) if v else f.isnot(None),
            "isnotnull": lambda f, v: f.isnot(None) if v else f.is_(None),
            "startswith": lambda f, v: f.like(f"{escape_like_pattern(str(v))}%"),
            "endswith": lambda f, v: f.like(f"%{escape_like_pattern(str(v))}"),
            "contains": lambda f, v: f.ilike(f"%{escape_like_pattern(str(v))}%"),
        }
        
        if operator in operators:
            return operators[operator](field, value)
        
        return None
    
    async def find_one_by(
        self,
        *,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[ModelT]:
        """
        Find a single entity by field values.
        
        Args:
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            **kwargs: Field=value pairs to filter by
            
        Returns:
            Entity or None if not found
        """
        query = select(self.model)
        
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def find_all_by(
        self,
        *,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
        **kwargs,
    ) -> List[ModelT]:
        """
        Find all entities by field values.
        
        Args:
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            **kwargs: Field=value pairs to filter by
            
        Returns:
            List of entities
        """
        query = select(self.model)
        
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

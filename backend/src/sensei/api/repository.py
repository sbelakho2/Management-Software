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
        tenant_id: Optional[UUID] = None,
    ):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            db: Async database session
            soft_delete: Whether to use soft delete (default: True)
            tenant_id: Optional tenant UUID for multi-tenant scoping (#143)
        """
        self.model = model
        self.db = db
        self.soft_delete = soft_delete
        self.tenant_id = tenant_id

    def _apply_base_filters(
        self,
        query: Select,  # type: ignore[type-arg]
        *,
        include_deleted: bool = False,
    ) -> Select:  # type: ignore[type-arg]
        """Apply standard soft-delete and tenant scoping filters."""
        if not include_deleted and self.soft_delete and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if self.tenant_id is not None and hasattr(self.model, "tenant_id"):
            query = query.where(self.model.tenant_id == self.tenant_id)  # type: ignore[attr-defined]
        return query
    
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
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
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
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
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
        max_rows: int = 10_000,
    ) -> List[ModelT]:
        """
        Get all entities.
        
        Args:
            include_deleted: Include soft-deleted entities
            load_relations: List of relationship names to eager load
            max_rows: Safety limit to prevent loading unbounded rows (#106)
            
        Returns:
            List of all entities (capped at max_rows)
        """
        query = select(self.model)
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        # Safety limit to prevent unbounded result sets (#106)
        query = query.limit(max_rows)
        
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
            page_size: Number of items per page (max 200)
            include_deleted: Include soft-deleted entities
            filters: List of filter operators
            sort: List of sort orders
            search: Full-text search query
            search_fields: Fields to search in
            load_relations: List of relationship names to eager load
            
        Returns:
            Tuple of (entities, total_count)
        """
        # Cap page_size to prevent excessive result sets (#243)
        _MAX_PAGE_SIZE = 200
        if page_size > _MAX_PAGE_SIZE:
            page_size = _MAX_PAGE_SIZE
        if page < 1:
            page = 1
        # Base query with window-function total count (#122)
        # Single query instead of separate count + data queries
        count_over = func.count(self.model.id).over().label("_total_count")
        query = select(self.model, count_over)
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
        # Apply filters
        if filters:
            for f in filters:
                condition = self._build_filter_condition(f)
                if condition is not None:
                    query = query.where(condition)
        
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
        
        # Apply sorting
        if sort:
            for s in sort:
                if hasattr(self.model, s.field):
                    field = getattr(self.model, s.field)
                    query = query.order_by(desc(field) if s.direction == "desc" else asc(field))
        else:
            # Default sort by created_at desc if available
            if hasattr(self.model, "created_at"):
                created_at_field = getattr(self.model, "created_at")
                query = query.order_by(desc(created_at_field))
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Load relations
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        rows = result.all()
        
        if rows:
            entities = [row[0] for row in rows]
            total = rows[0][1]  # _total_count is the same for all rows
        else:
            entities = []
            total = 0
        
        return entities, total
    
    async def exists(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
    ) -> bool:
        """Check if entity exists by ID."""
        query = select(func.count(self.model.id)).where(self.model.id == id)
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
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
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
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
        max_items: int = 500,
    ) -> List[ModelT]:
        """
        Create multiple entities.
        
        Args:
            items: List of entity data dictionaries
            created_by: User ID who created the entities
            commit: Whether to commit the transaction
            max_items: Maximum allowed items per batch (#162)
            
        Returns:
            List of created entities
            
        Raises:
            ValueError: If items list exceeds max_items
        """
        if len(items) > max_items:
            raise ValueError(
                f"Batch size {len(items)} exceeds maximum of {max_items} items. "
                "Split into smaller batches."
            )
        entities = []
        
        # Use savepoint so partial adds roll back atomically on error (#185)
        async with self.db.begin_nested():
            for data in items:
                if created_by and hasattr(self.model, "created_by"):
                    data["created_by"] = created_by
                
                entity = self.model(**data)
                self.db.add(entity)
                entities.append(entity)
        
        if commit:
            await self.db.commit()
            # Bulk-refresh: re-query by PKs instead of N individual refreshes (#102)
            if entities:
                pks = [entity.id for entity in entities]
                stmt = select(self.model).where(self.model.id.in_(pks))
                result = await self.db.execute(stmt)
                entities = list(result.scalars().all())
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
    
    _MAX_DELETE_IDS = 100  # Match BulkDeleteRequest.ids max_length (#246)

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
        
        Uses a single bulk UPDATE for soft-deletes instead of fetching
        and mutating one-by-one (#103).
        
        Args:
            ids: List of entity UUIDs (max 100; #246)
            deleted_by: User ID who deleted the entities
            hard_delete: Force hard delete instead of soft delete
            commit: Whether to commit the transaction
            
        Returns:
            Number of entities deleted
            
        Raises:
            ValueError: If more than 100 IDs are provided
        """
        if not ids:
            return 0
        if len(ids) > self._MAX_DELETE_IDS:
            raise ValueError(
                f"Cannot delete more than {self._MAX_DELETE_IDS} entities at once; got {len(ids)}"
            )
        
        use_soft = self.soft_delete and hasattr(self.model, "deleted_at") and not hard_delete
        
        if use_soft:
            # Bulk UPDATE — single statement instead of N fetches + N updates (#103)
            from sqlalchemy import update
            
            values: Dict[str, Any] = {"deleted_at": datetime.now(timezone.utc)}
            if deleted_by and hasattr(self.model, "deleted_by"):
                values["deleted_by"] = deleted_by
            
            stmt = (
                update(self.model)
                .where(self.model.id.in_(ids))
                .where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
            )
            result = await self.db.execute(stmt.values(**values))
            count = result.rowcount  # type: ignore[union-attr]
        else:
            # Hard delete still needs to load entities for cascade
            entities = await self.get_by_ids(ids)
            for entity in entities:
                await self.db.delete(entity)
            count = len(entities)
        
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        
        return count
    
    async def restore(
        self,
        id: UUID,
        *,
        restored_by: Optional[UUID] = None,
        commit: bool = True,
    ) -> Optional[ModelT]:
        """
        Restore a soft-deleted entity.
        
        Args:
            id: Entity UUID
            restored_by: User ID performing the restore (required for audit trail, #149)
            commit: Whether to commit the transaction
            
        Returns:
            Restored entity or None if not found
        """
        if not self.soft_delete or not hasattr(self.model, "deleted_at"):
            return None
        
        entity = await self.get_by_id(id, include_deleted=True)
        
        if not entity or not getattr(entity, "deleted_at", None):
            return None
        
        setattr(entity, "deleted_at", None)
        if hasattr(entity, "deleted_by"):
            setattr(entity, "deleted_by", None)
        # Record who restored and when for audit purposes (#149)
        if restored_by and hasattr(entity, "updated_by"):
            setattr(entity, "updated_by", restored_by)
        if hasattr(entity, "updated_at"):
            setattr(entity, "updated_at", datetime.now(timezone.utc))
        
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
            raise ValueError(
                f"Invalid filter field '{filter_op.field}' for {self.model.__name__}"
            )
        
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
        
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
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
        
        query = self._apply_base_filters(query, include_deleted=include_deleted)
        
        if load_relations:
            for relation in load_relations:
                if hasattr(self.model, relation):
                    query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

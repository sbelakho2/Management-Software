"""
Tests for Sensei OS Base Repository

Comprehensive tests for the generic CRUD repository pattern.
"""

from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.repository import BaseRepository
from sensei.api.schemas import FilterOperator, SortOrder
from sensei.api.exceptions import NotFoundError
from sensei.models.base import Base as SenseiBaseModel, SoftDeleteMixin, TimestampMixin


# =============================================================================
# Mock Model for Testing
# =============================================================================


class MockModel(SenseiBaseModel, TimestampMixin, SoftDeleteMixin):
    """Mock model for testing repository operations."""
    
    __tablename__ = "mock_models"
    
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    status = Column(String(50), default="active")
    is_active = Column(Boolean, default=True)


# =============================================================================
# Repository Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def repository(mock_db):
    """Create repository instance with mock database."""
    return BaseRepository(MockModel, mock_db)


@pytest.fixture
def sample_entity():
    """Create sample entity for testing."""
    entity = MockModel(
        name="Test Entity",
        email="test@example.com",
        status="active",
    )
    entity.id = uuid4()
    entity.created_at = datetime.now(timezone.utc)
    entity.deleted_at = None
    return entity


# =============================================================================
# Get by ID Tests
# =============================================================================


class TestGetById:
    """Tests for get_by_id operation."""
    
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db, sample_entity):
        """Test getting entity by ID when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_by_id(sample_entity.id)
        
        assert result == sample_entity
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db):
        """Test getting entity by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_by_id(uuid4())
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_excludes_deleted(self, repository, mock_db, sample_entity):
        """Test that deleted entities are excluded by default."""
        sample_entity.deleted_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_by_id(sample_entity.id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_includes_deleted(self, repository, mock_db, sample_entity):
        """Test including deleted entities."""
        sample_entity.deleted_at = datetime.now(timezone.utc)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_by_id(sample_entity.id, include_deleted=True)
        
        assert result == sample_entity


class TestGetByIdOrRaise:
    """Tests for get_by_id_or_raise operation."""
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_found(self, repository, mock_db, sample_entity):
        """Test getting entity when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_by_id_or_raise(sample_entity.id)
        
        assert result == sample_entity
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_not_found(self, repository, mock_db):
        """Test raising NotFoundError when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        entity_id = uuid4()
        
        with pytest.raises(NotFoundError) as exc_info:
            await repository.get_by_id_or_raise(entity_id)
        
        assert "MockModel" in exc_info.value.message
        assert str(entity_id) in exc_info.value.message


# =============================================================================
# Get Multiple Tests
# =============================================================================


class TestGetByIds:
    """Tests for get_by_ids operation."""
    
    @pytest.mark.asyncio
    async def test_get_by_ids(self, repository, mock_db):
        """Test getting multiple entities by IDs."""
        entities = [
            MagicMock(id=uuid4(), deleted_at=None),
            MagicMock(id=uuid4(), deleted_at=None),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entities
        mock_db.execute.return_value = mock_result
        
        ids = [e.id for e in entities]
        result = await repository.get_by_ids(ids)
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_by_ids_empty(self, repository, mock_db):
        """Test getting with empty ID list."""
        result = await repository.get_by_ids([])
        
        assert result == []
        mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_by_ids_partial_results(self, repository, mock_db):
        """Test getting when some IDs don't exist."""
        entity = MagicMock(id=uuid4(), deleted_at=None)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entity]
        mock_db.execute.return_value = mock_result
        
        ids = [entity.id, uuid4(), uuid4()]
        result = await repository.get_by_ids(ids)
        
        # Only 1 found out of 3 requested
        assert len(result) == 1


class TestGetAll:
    """Tests for get_all operation."""
    
    @pytest.mark.asyncio
    async def test_get_all(self, repository, mock_db):
        """Test getting all entities."""
        entities = [MagicMock() for _ in range(5)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entities
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_all()
        
        assert len(result) == 5
    
    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository, mock_db):
        """Test getting all when no entities exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await repository.get_all()
        
        assert result == []


# =============================================================================
# Paginated Query Tests
# =============================================================================


class TestGetPaginated:
    """Tests for get_paginated operation."""
    
    @pytest.mark.asyncio
    async def test_get_paginated_basic(self, repository, mock_db):
        """Test basic pagination."""
        entities = [MagicMock() for _ in range(10)]
        total_count = 35

        # Single query with window function: result.all() returns [(entity, total), ...]
        rows = [(e, total_count) for e in entities]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        result, total = await repository.get_paginated(page=1, page_size=10)

        assert len(result) == 10
        assert total == 35
    
    @pytest.mark.asyncio
    async def test_get_paginated_with_offset(self, repository, mock_db):
        """Test pagination with offset."""
        entities = [MagicMock() for _ in range(10)]
        total_count = 35

        rows = [(e, total_count) for e in entities]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        result, total = await repository.get_paginated(page=2, page_size=10)

        assert len(result) == 10
        assert total == 35
    
    @pytest.mark.asyncio
    async def test_get_paginated_with_filters(self, repository, mock_db):
        """Test pagination with filters."""
        entities = [MagicMock() for _ in range(5)]
        total_count = 5

        rows = [(e, total_count) for e in entities]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        filters = [
            FilterOperator(field="status", operator="eq", value="active"),
        ]

        result, total = await repository.get_paginated(
            page=1,
            page_size=10,
            filters=filters,
        )

        assert len(result) == 5
        assert total == 5
    
    @pytest.mark.asyncio
    async def test_get_paginated_with_sort(self, repository, mock_db):
        """Test pagination with sorting."""
        entities = [MagicMock() for _ in range(10)]
        total_count = 10

        rows = [(e, total_count) for e in entities]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        sort = [
            SortOrder(field="name", direction="asc"),
            SortOrder(field="created_at", direction="desc"),
        ]

        result, total = await repository.get_paginated(
            page=1,
            page_size=10,
            sort=sort,
        )

        assert len(result) == 10
    
    @pytest.mark.asyncio
    async def test_get_paginated_with_search(self, repository, mock_db):
        """Test pagination with search."""
        entities = [MagicMock() for _ in range(3)]
        total_count = 3

        rows = [(e, total_count) for e in entities]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        result, total = await repository.get_paginated(
            page=1,
            page_size=10,
            search="test",
            search_fields=["name", "email"],
        )

        assert len(result) == 3


# =============================================================================
# Exists and Count Tests
# =============================================================================


class TestExists:
    """Tests for exists operation."""
    
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_db):
        """Test exists when entity exists."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result
        
        result = await repository.exists(uuid4())
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_db):
        """Test exists when entity doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result
        
        result = await repository.exists(uuid4())
        
        assert result is False


class TestCount:
    """Tests for count operation."""
    
    @pytest.mark.asyncio
    async def test_count_all(self, repository, mock_db):
        """Test counting all entities."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result
        
        result = await repository.count()
        
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_count_with_filters(self, repository, mock_db):
        """Test counting with filters."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_db.execute.return_value = mock_result
        
        filters = [
            FilterOperator(field="status", operator="eq", value="active"),
        ]
        
        result = await repository.count(filters=filters)
        
        assert result == 10


# =============================================================================
# Create Tests
# =============================================================================


class TestCreate:
    """Tests for create operation."""
    
    @pytest.mark.asyncio
    async def test_create_basic(self, repository, mock_db):
        """Test basic entity creation."""
        data = {"name": "New Entity", "email": "new@example.com"}
        
        async def refresh_side_effect(entity):
            entity.id = uuid4()
            entity.created_at = datetime.now(timezone.utc)
        
        mock_db.refresh.side_effect = refresh_side_effect
        
        result = await repository.create(data)
        
        assert result.name == "New Entity"
        assert result.email == "new@example.com"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_with_created_by(self, repository, mock_db):
        """Test creation with created_by field.
        
        Note: The MockModel doesn't have created_by field since it's from
        AuditMixin. This test verifies the create method handles the parameter
        gracefully when the model doesn't have the field.
        """
        user_id = uuid4()
        data = {"name": "New Entity"}
        
        async def refresh_side_effect(entity):
            entity.id = uuid4()
            entity.created_at = datetime.now(timezone.utc)
        
        mock_db.refresh.side_effect = refresh_side_effect
        
        # Should not raise even if model doesn't have created_by
        result = await repository.create(data, created_by=user_id)
        
        # Entity should still be created successfully
        assert result.name == "New Entity"
    
    @pytest.mark.asyncio
    async def test_create_without_commit(self, repository, mock_db):
        """Test creation without commit."""
        data = {"name": "New Entity"}
        
        result = await repository.create(data, commit=False)
        
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()


class TestCreateMany:
    """Tests for create_many operation."""
    
    @pytest.mark.asyncio
    async def test_create_many(self, repository, mock_db):
        """Test creating multiple entities."""
        items = [
            {"name": "Entity 1"},
            {"name": "Entity 2"},
            {"name": "Entity 3"},
        ]

        # Mock begin_nested() as an async context manager
        mock_db.begin_nested = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock())
        )

        # After commit, create_many does a bulk re-query by PKs
        created_entities = [MagicMock(id=uuid4()) for _ in range(3)]
        requery_result = MagicMock()
        requery_result.scalars.return_value.all.return_value = created_entities
        mock_db.execute.return_value = requery_result

        result = await repository.create_many(items)

        assert len(result) == 3
        assert mock_db.add.call_count == 3
        mock_db.commit.assert_called_once()


# =============================================================================
# Update Tests
# =============================================================================


class TestUpdate:
    """Tests for update operation."""
    
    @pytest.mark.asyncio
    async def test_update_basic(self, repository, mock_db, sample_entity):
        """Test basic entity update."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        data = {"name": "Updated Name"}
        
        result = await repository.update(sample_entity.id, data)
        
        assert result.name == "Updated Name"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_not_found(self, repository, mock_db):
        """Test update when entity not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await repository.update(uuid4(), {"name": "New"})
        
        assert result is None
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_with_updated_by(self, repository, mock_db, sample_entity):
        """Test update with updated_by field.
        
        Note: The MockModel doesn't have updated_by field since it's from
        AuditMixin. This test verifies the update method handles the parameter
        gracefully when the model doesn't have the field.
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        user_id = uuid4()
        data = {"name": "Updated"}
        
        result = await repository.update(
            sample_entity.id,
            data,
            updated_by=user_id,
        )
        
        # Entity should still be updated successfully
        assert result.name == "Updated"


class TestUpdateOrRaise:
    """Tests for update_or_raise operation."""
    
    @pytest.mark.asyncio
    async def test_update_or_raise_found(self, repository, mock_db, sample_entity):
        """Test update when entity found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.update_or_raise(
            sample_entity.id,
            {"name": "Updated"},
        )
        
        assert result.name == "Updated"
    
    @pytest.mark.asyncio
    async def test_update_or_raise_not_found(self, repository, mock_db):
        """Test update raises NotFoundError when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(NotFoundError):
            await repository.update_or_raise(uuid4(), {"name": "New"})


# =============================================================================
# Delete Tests
# =============================================================================


class TestDelete:
    """Tests for delete operation."""
    
    @pytest.mark.asyncio
    async def test_soft_delete(self, repository, mock_db, sample_entity):
        """Test soft delete."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.delete(sample_entity.id)
        
        assert result is True
        assert sample_entity.deleted_at is not None
        mock_db.delete.assert_not_called()  # Soft delete, not hard
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hard_delete(self, repository, mock_db, sample_entity):
        """Test hard delete."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.delete(sample_entity.id, hard_delete=True)
        
        assert result is True
        mock_db.delete.assert_called_once_with(sample_entity)
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_db):
        """Test delete when entity not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await repository.delete(uuid4())
        
        assert result is False
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_with_deleted_by(self, repository, mock_db, sample_entity):
        """Test delete with deleted_by field."""
        sample_entity.deleted_by = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        user_id = uuid4()
        
        await repository.delete(sample_entity.id, deleted_by=user_id)
        
        assert sample_entity.deleted_by == user_id


class TestDeleteOrRaise:
    """Tests for delete_or_raise operation."""
    
    @pytest.mark.asyncio
    async def test_delete_or_raise_found(self, repository, mock_db, sample_entity):
        """Test delete when entity found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        # Should not raise
        await repository.delete_or_raise(sample_entity.id)
        
        assert sample_entity.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_or_raise_not_found(self, repository, mock_db):
        """Test delete raises NotFoundError when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(NotFoundError):
            await repository.delete_or_raise(uuid4())


class TestDeleteMany:
    """Tests for delete_many operation."""
    
    @pytest.mark.asyncio
    async def test_delete_many(self, repository, mock_db):
        """Test deleting multiple entities (bulk UPDATE)."""
        ids = [uuid4(), uuid4()]

        # Bulk UPDATE returns a result with rowcount
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute.return_value = mock_result

        result = await repository.delete_many(ids)

        assert result == 2
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_many_empty(self, repository, mock_db):
        """Test delete many with empty list."""
        result = await repository.delete_many([])
        
        assert result == 0
        mock_db.execute.assert_not_called()


# =============================================================================
# Restore Tests
# =============================================================================


class TestRestore:
    """Tests for restore operation."""
    
    @pytest.mark.asyncio
    async def test_restore(self, repository, mock_db, sample_entity):
        """Test restoring soft-deleted entity."""
        sample_entity.deleted_at = datetime.now(timezone.utc)
        sample_entity.deleted_by = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.restore(sample_entity.id)
        
        assert result == sample_entity
        assert result.deleted_at is None
        assert result.deleted_by is None
    
    @pytest.mark.asyncio
    async def test_restore_not_deleted(self, repository, mock_db, sample_entity):
        """Test restoring entity that's not deleted."""
        sample_entity.deleted_at = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.restore(sample_entity.id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_restore_not_found(self, repository, mock_db):
        """Test restoring non-existent entity."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await repository.restore(uuid4())
        
        assert result is None


# =============================================================================
# Filter Builder Tests
# =============================================================================


class TestFilterBuilder:
    """Tests for _build_filter_condition method."""
    
    def test_eq_operator(self, repository):
        """Test eq (equals) operator."""
        filter_op = FilterOperator(field="status", operator="eq", value="active")
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is not None
    
    def test_ne_operator(self, repository):
        """Test ne (not equals) operator."""
        filter_op = FilterOperator(field="status", operator="ne", value="inactive")
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is not None
    
    def test_gt_operator(self, repository):
        """Test gt (greater than) operator."""
        filter_op = FilterOperator(field="id", operator="gt", value=10)
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is not None
    
    def test_like_operator(self, repository):
        """Test like operator."""
        filter_op = FilterOperator(field="name", operator="like", value="test")
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is not None
    
    def test_in_operator(self, repository):
        """Test in operator."""
        filter_op = FilterOperator(
            field="status",
            operator="in",
            value=["active", "pending"],
        )
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is not None
    
    def test_isnull_operator(self, repository):
        """Test isnull operator."""
        filter_op = FilterOperator(field="email", operator="isnull", value=True)
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is not None
    
    def test_invalid_field(self, repository):
        """Test filter with non-existent field raises ValueError."""
        filter_op = FilterOperator(field="nonexistent", operator="eq", value="test")

        with pytest.raises(ValueError, match="Invalid filter field"):
            repository._build_filter_condition(filter_op)
    
    def test_invalid_operator(self, repository):
        """Test filter with invalid operator returns None."""
        filter_op = FilterOperator(field="status", operator="invalid", value="test")
        condition = repository._build_filter_condition(filter_op)
        
        assert condition is None


# =============================================================================
# Find By Tests
# =============================================================================


class TestFindOneBy:
    """Tests for find_one_by operation."""
    
    @pytest.mark.asyncio
    async def test_find_one_by(self, repository, mock_db, sample_entity):
        """Test finding single entity by field value."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.find_one_by(email="test@example.com")
        
        assert result == sample_entity
    
    @pytest.mark.asyncio
    async def test_find_one_by_multiple_fields(self, repository, mock_db, sample_entity):
        """Test finding by multiple field values."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        result = await repository.find_one_by(
            email="test@example.com",
            status="active",
        )
        
        assert result == sample_entity


class TestFindAllBy:
    """Tests for find_all_by operation."""
    
    @pytest.mark.asyncio
    async def test_find_all_by(self, repository, mock_db):
        """Test finding all entities by field value."""
        entities = [MagicMock() for _ in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entities
        mock_db.execute.return_value = mock_result
        
        result = await repository.find_all_by(status="active")
        
        assert len(result) == 3


# =============================================================================
# Repository Configuration Tests
# =============================================================================


class TestRepositoryConfiguration:
    """Tests for repository configuration."""
    
    def test_soft_delete_enabled_by_default(self, mock_db):
        """Test that soft delete is enabled by default."""
        repo = BaseRepository(MockModel, mock_db)
        assert repo.soft_delete is True
    
    def test_soft_delete_can_be_disabled(self, mock_db):
        """Test that soft delete can be disabled."""
        repo = BaseRepository(MockModel, mock_db, soft_delete=False)
        assert repo.soft_delete is False
    
    @pytest.mark.asyncio
    async def test_hard_delete_when_soft_delete_disabled(self, mock_db, sample_entity):
        """Test that delete is hard delete when soft delete is disabled."""
        repo = BaseRepository(MockModel, mock_db, soft_delete=False)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_entity
        mock_db.execute.return_value = mock_result
        
        await repo.delete(sample_entity.id)
        
        mock_db.delete.assert_called_once_with(sample_entity)

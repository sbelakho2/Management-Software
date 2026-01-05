"""
Comprehensive Tests for Work Center and Station Endpoints

Tests all Work Center and Station functionality including:
- CRUD operations for work centers
- CRUD operations for stations
- Filtering and pagination
- Statistics
- Edge cases and error handling
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi import status, Query

from sensei.api.v1.endpoints.work_centers import (
    router,
    list_work_centers,
    create_work_center,
    get_work_center,
    update_work_center,
    delete_work_center,
    restore_work_center,
    get_work_center_stats,
    list_stations,
    create_station,
    get_station,
    update_station,
    delete_station,
    restore_station,
    create_station_direct,
    WorkCenterCreate,
    WorkCenterUpdate,
    WorkCenterResponse,
    WorkCenterListResponse,
    StationBase,
    StationCreate,
    StationUpdate,
    StationResponse,
    StationListResponse,
    WorkCenterStatsResponse,
    work_center_to_response,
    work_center_to_list_response,
    station_to_response,
    station_to_list_response,
)
from sensei.models.work_center import (
    WorkCenter,
    WorkCenterStatus,
    Station,
    StationType,
    StationStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.is_superuser = False
    return user


@pytest.fixture
def mock_superuser():
    """Create a mock superuser."""
    user = MagicMock()
    user.id = uuid4()
    user.is_superuser = True
    return user


@pytest.fixture
def sample_work_center():
    """Create a sample work center model."""
    wc = MagicMock(spec=WorkCenter)
    wc.id = 1
    wc.name = "Assembly Line A"
    wc.code = "WC-ASMA"
    wc.description = "Main assembly line for precision parts"
    wc.location = "Building A, Floor 1"
    wc.capacity_units = "units/hour"
    wc.capacity_value = Decimal("100.0000")
    wc.efficiency_target = Decimal("85.00")
    wc.status = WorkCenterStatus.ACTIVE
    wc.account_id = uuid4()
    wc.created_at = datetime.now(timezone.utc)
    wc.updated_at = datetime.now(timezone.utc)
    wc.created_by_id = uuid4()
    wc.updated_by_id = None
    wc.deleted_at = None
    
    # Mock stations for active_stations_count
    active_station = MagicMock()
    active_station.status = StationStatus.ACTIVE
    inactive_station = MagicMock()
    inactive_station.status = StationStatus.INACTIVE
    wc.stations = [active_station, inactive_station]
    
    # Computed properties
    wc.active_stations_count = 1
    wc.is_operational = True
    
    return wc


@pytest.fixture
def sample_station():
    """Create a sample station model."""
    station = MagicMock(spec=Station)
    station.id = 1
    station.name = "Assembly Station 1"
    station.code = "ST-ASM-01"
    station.description = "First assembly station"
    station.station_type = StationType.ASSEMBLY
    station.takt_time_seconds = 60
    station.cycle_time_seconds = 55
    station.setup_time_seconds = 300
    station.status = StationStatus.ACTIVE
    station.yellow_ack_minutes = 5
    station.red_ack_minutes = 2
    station.resolution_target_minutes = 30
    station.work_center_id = 1
    station.production_cell_id = None
    station.created_at = datetime.now(timezone.utc)
    station.updated_at = datetime.now(timezone.utc)
    station.created_by_id = uuid4()
    station.updated_by_id = None
    station.deleted_at = None
    
    # Computed properties
    station.efficiency_ratio = Decimal("1.09")  # 60/55
    station.is_bottleneck = False
    station.is_available = True
    
    return station


@pytest.fixture
def sample_bottleneck_station():
    """Create a sample bottleneck station (cycle > takt)."""
    station = MagicMock(spec=Station)
    station.id = 2
    station.name = "Inspection Station"
    station.code = "ST-INS-01"
    station.description = "Quality inspection station"
    station.station_type = StationType.INSPECTION
    station.takt_time_seconds = 60
    station.cycle_time_seconds = 75  # Bottleneck: cycle > takt
    station.setup_time_seconds = 120
    station.status = StationStatus.ACTIVE
    station.yellow_ack_minutes = 5
    station.red_ack_minutes = 2
    station.resolution_target_minutes = 30
    station.work_center_id = 1
    station.production_cell_id = None
    station.created_at = datetime.now(timezone.utc)
    station.updated_at = datetime.now(timezone.utc)
    station.created_by_id = uuid4()
    station.updated_by_id = None
    station.deleted_at = None
    
    # Computed properties
    station.efficiency_ratio = Decimal("0.80")  # 60/75
    station.is_bottleneck = True
    station.is_available = True
    
    return station


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


# =============================================================================
# Schema Conversion Tests
# =============================================================================


class TestWorkCenterConversion:
    """Test work center schema conversions."""

    def test_work_center_to_response(self, sample_work_center):
        """Test work_center_to_response conversion."""
        response = work_center_to_response(sample_work_center)
        
        assert response.id == sample_work_center.id
        assert response.name == sample_work_center.name
        assert response.code == sample_work_center.code
        assert response.description == sample_work_center.description
        assert response.location == sample_work_center.location
        assert response.capacity_units == sample_work_center.capacity_units
        assert response.capacity_value == float(sample_work_center.capacity_value)
        assert response.efficiency_target == float(sample_work_center.efficiency_target)
        assert response.status == sample_work_center.status.value
        assert response.account_id == sample_work_center.account_id
        assert response.active_stations_count == 1
        assert response.is_operational is True
        assert response.created_at == sample_work_center.created_at
        assert response.updated_at == sample_work_center.updated_at
        assert response.created_by_id == sample_work_center.created_by_id
        assert response.updated_by_id == sample_work_center.updated_by_id

    def test_work_center_to_list_response(self, sample_work_center):
        """Test work_center_to_list_response conversion."""
        response = work_center_to_list_response(sample_work_center)
        
        assert response.id == sample_work_center.id
        assert response.name == sample_work_center.name
        assert response.code == sample_work_center.code
        assert response.status == sample_work_center.status.value
        assert response.location == sample_work_center.location
        assert response.efficiency_target == float(sample_work_center.efficiency_target)
        assert response.active_stations_count == 1
        assert response.is_operational is True
        assert response.created_at == sample_work_center.created_at

    def test_work_center_to_response_null_capacity(self, sample_work_center):
        """Test conversion with null capacity_value."""
        sample_work_center.capacity_value = None
        response = work_center_to_response(sample_work_center)
        assert response.capacity_value is None

    def test_work_center_to_response_string_status(self, sample_work_center):
        """Test conversion when status is string instead of enum."""
        sample_work_center.status = "active"
        response = work_center_to_response(sample_work_center)
        assert response.status == "active"


class TestStationConversion:
    """Test station schema conversions."""

    def test_station_to_response(self, sample_station):
        """Test station_to_response conversion."""
        response = station_to_response(sample_station)
        
        assert response.id == sample_station.id
        assert response.name == sample_station.name
        assert response.code == sample_station.code
        assert response.description == sample_station.description
        assert response.station_type == sample_station.station_type.value
        assert response.takt_time_seconds == sample_station.takt_time_seconds
        assert response.cycle_time_seconds == sample_station.cycle_time_seconds
        assert response.setup_time_seconds == sample_station.setup_time_seconds
        assert response.status == sample_station.status.value
        assert response.yellow_ack_minutes == sample_station.yellow_ack_minutes
        assert response.red_ack_minutes == sample_station.red_ack_minutes
        assert response.resolution_target_minutes == sample_station.resolution_target_minutes
        assert response.work_center_id == sample_station.work_center_id
        assert response.production_cell_id == sample_station.production_cell_id
        assert response.efficiency_ratio == float(sample_station.efficiency_ratio)
        assert response.is_bottleneck is False
        assert response.is_available is True

    def test_station_to_list_response(self, sample_station):
        """Test station_to_list_response conversion."""
        response = station_to_list_response(sample_station)
        
        assert response.id == sample_station.id
        assert response.name == sample_station.name
        assert response.code == sample_station.code
        assert response.station_type == sample_station.station_type.value
        assert response.status == sample_station.status.value
        assert response.takt_time_seconds == sample_station.takt_time_seconds
        assert response.cycle_time_seconds == sample_station.cycle_time_seconds
        assert response.is_bottleneck is False
        assert response.is_available is True
        assert response.work_center_id == sample_station.work_center_id
        assert response.created_at == sample_station.created_at

    def test_station_to_response_bottleneck(self, sample_bottleneck_station):
        """Test conversion for bottleneck station."""
        response = station_to_response(sample_bottleneck_station)
        assert response.is_bottleneck is True
        assert response.cycle_time_seconds > response.takt_time_seconds

    def test_station_to_response_string_status(self, sample_station):
        """Test conversion when status/type are strings."""
        sample_station.status = "active"
        sample_station.station_type = "assembly"
        response = station_to_response(sample_station)
        assert response.status == "active"
        assert response.station_type == "assembly"


# =============================================================================
# Work Center CRUD Tests
# =============================================================================


class TestListWorkCenters:
    """Test list_work_centers endpoint."""

    @pytest.mark.asyncio
    async def test_list_work_centers_empty(self, mock_db, mock_user):
        """Test listing work centers when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=0)),  # count
            mock_result,  # items
        ])
        
        response = await list_work_centers(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            account_id=None,
            search=None,
            sort=None,
            include_deleted=False,
        )
        
        assert response.data == []
        assert response.pagination.total_items == 0
        assert response.pagination.page == 1
        assert response.pagination.page_size == 20

    @pytest.mark.asyncio
    async def test_list_work_centers_with_items(self, mock_db, mock_user, sample_work_center):
        """Test listing work centers with items."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_work_center]
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),  # count
            mock_result,  # items
        ])
        
        response = await list_work_centers(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            account_id=None,
            search=None,
            sort=None,
            include_deleted=False,
        )
        
        assert len(response.data) == 1
        assert response.data[0].id == sample_work_center.id
        assert response.data[0].name == sample_work_center.name
        assert response.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_list_work_centers_with_status_filter(self, mock_db, mock_user, sample_work_center):
        """Test listing work centers filtered by status."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_work_center]
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            mock_result,
        ])
        
        response = await list_work_centers(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status="active",
            account_id=None,
            search=None,
            sort=None,
            include_deleted=False,
        )
        
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_list_work_centers_with_search(self, mock_db, mock_user, sample_work_center):
        """Test listing work centers with search."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_work_center]
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            mock_result,
        ])
        
        response = await list_work_centers(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            account_id=None,
            search="Assembly",
            sort=None,
            include_deleted=False,
        )
        
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_list_work_centers_with_sorting(self, mock_db, mock_user, sample_work_center):
        """Test listing work centers with sorting."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_work_center]
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            mock_result,
        ])
        
        response = await list_work_centers(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            account_id=None,
            search=None,
            sort="-name",
            include_deleted=False,
        )
        
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_list_work_centers_pagination(self, mock_db, mock_user, sample_work_center):
        """Test pagination."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_work_center]
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=50)),  # total = 50
            mock_result,
        ])
        
        response = await list_work_centers(
            db=mock_db,
            current_user=mock_user,
            page=3,
            page_size=10,
            status=None,
            account_id=None,
            search=None,
            sort=None,
            include_deleted=False,
        )
        
        assert response.pagination.page == 3
        assert response.pagination.page_size == 10
        assert response.pagination.total_items == 50


class TestCreateWorkCenter:
    """Test create_work_center endpoint."""

    @pytest.mark.asyncio
    async def test_create_work_center_success(self, mock_db, mock_user):
        """Test successful work center creation."""
        # Mock - no existing work center with this code
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        # Track what gets added to DB
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            # Set the id as if it was auto-generated
            obj.id = 1
            # Mock the computed properties
            obj.stations = []
        
        mock_db.add = MagicMock(side_effect=capture_add)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()  # No-op since we set everything in add
        
        data = WorkCenterCreate(
            name="Test Work Center",
            code="WC-TEST",
            description="Test description",
            location="Building A",
            capacity_units="units/hour",
            capacity_value=100.0,
            efficiency_target=85.0,
            status="active",
        )
        
        response = await create_work_center(
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        # Verify the object was added to DB
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify the added object has correct properties
        assert added_object is not None
        assert added_object.name == "Test Work Center"
        assert added_object.code == "WC-TEST"
        
        # Response should have the data
        assert response.data is not None
        assert response.message == "Work center created successfully"

    @pytest.mark.asyncio
    async def test_create_work_center_duplicate_code(self, mock_db, mock_user, sample_work_center):
        """Test creating work center with duplicate code."""
        from sensei.api.exceptions import ConflictError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        
        data = WorkCenterCreate(
            name="New Work Center",
            code="WC-ASMA",  # Duplicate code
        )
        
        with pytest.raises(ConflictError) as exc_info:
            await create_work_center(
                data=data,
                db=mock_db,
                current_user=mock_user,
            )
        
        assert "already exists" in str(exc_info.value)


class TestGetWorkCenter:
    """Test get_work_center endpoint."""

    @pytest.mark.asyncio
    async def test_get_work_center_success(self, mock_db, mock_user, sample_work_center):
        """Test getting a work center by ID."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        
        response = await get_work_center(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data.id == sample_work_center.id
        assert response.data.name == sample_work_center.name

    @pytest.mark.asyncio
    async def test_get_work_center_not_found(self, mock_db, mock_user):
        """Test getting non-existent work center."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError) as exc_info:
            await get_work_center(
                work_center_id=999,
                db=mock_db,
                current_user=mock_user,
                include_deleted=False,
            )
        
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_work_center_include_deleted(self, mock_db, mock_user, sample_work_center):
        """Test getting deleted work center with include_deleted=True."""
        sample_work_center.deleted_at = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        
        response = await get_work_center(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
            include_deleted=True,
        )
        
        assert response.data.id == sample_work_center.id


class TestUpdateWorkCenter:
    """Test update_work_center endpoint."""

    @pytest.mark.asyncio
    async def test_update_work_center_success(self, mock_db, mock_user, sample_work_center):
        """Test updating a work center."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        data = WorkCenterUpdate(
            name="Updated Name",
            efficiency_target=90.0,
        )
        
        response = await update_work_center(
            work_center_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.message == "Work center updated successfully"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_work_center_not_found(self, mock_db, mock_user):
        """Test updating non-existent work center."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        data = WorkCenterUpdate(name="Updated Name")
        
        with pytest.raises(NotFoundError):
            await update_work_center(
                work_center_id=999,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_update_work_center_duplicate_code(self, mock_db, mock_user, sample_work_center):
        """Test updating work center with duplicate code."""
        from sensei.api.exceptions import ConflictError
        
        # First call returns the work center to update
        # Second call returns another work center with the same code
        existing_wc = MagicMock()
        existing_wc.id = 2
        existing_wc.code = "WC-DUP"
        
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_center)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_wc)),
        ])
        
        data = WorkCenterUpdate(code="WC-DUP")
        
        with pytest.raises(ConflictError):
            await update_work_center(
                work_center_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestDeleteWorkCenter:
    """Test delete_work_center endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_work_center(self, mock_db, mock_user, sample_work_center):
        """Test soft deleting a work center."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        mock_db.commit = AsyncMock()
        
        response = await delete_work_center(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response.message == "Work center deleted successfully"
        assert sample_work_center.deleted_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete_work_center(self, mock_db, mock_user, sample_work_center):
        """Test hard deleting a work center."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        response = await delete_work_center(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=True,
        )
        
        assert response.message == "Work center deleted successfully"
        mock_db.delete.assert_called_once_with(sample_work_center)

    @pytest.mark.asyncio
    async def test_delete_work_center_not_found(self, mock_db, mock_user):
        """Test deleting non-existent work center."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await delete_work_center(
                work_center_id=999,
                db=mock_db,
                current_user=mock_user,
                hard_delete=False,
            )


class TestRestoreWorkCenter:
    """Test restore_work_center endpoint."""

    @pytest.mark.asyncio
    async def test_restore_work_center_success(self, mock_db, mock_user, sample_work_center):
        """Test restoring a soft-deleted work center."""
        sample_work_center.deleted_at = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_center)
        ))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        response = await restore_work_center(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.message == "Work center restored successfully"
        assert sample_work_center.deleted_at is None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_work_center_not_found(self, mock_db, mock_user):
        """Test restoring non-existent deleted work center."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await restore_work_center(
                work_center_id=999,
                db=mock_db,
                current_user=mock_user,
            )


class TestWorkCenterStats:
    """Test get_work_center_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_work_center_stats(self, mock_db, mock_user):
        """Test getting work center statistics."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=10)),  # total_work_centers
            MagicMock(all=MagicMock(return_value=[
                (WorkCenterStatus.ACTIVE, 8),
                (WorkCenterStatus.MAINTENANCE, 2),
            ])),  # by_status
            MagicMock(scalar=MagicMock(return_value=25)),  # total_stations
            MagicMock(all=MagicMock(return_value=[
                (StationType.ASSEMBLY, 15),
                (StationType.INSPECTION, 10),
            ])),  # stations_by_type
            MagicMock(all=MagicMock(return_value=[
                (StationStatus.ACTIVE, 20),
                (StationStatus.MAINTENANCE, 5),
            ])),  # stations_by_status
            MagicMock(scalar=MagicMock(return_value=8)),  # active_work_centers
            MagicMock(scalar=MagicMock(return_value=3)),  # bottleneck_stations
        ])
        
        response = await get_work_center_stats(
            db=mock_db,
            current_user=mock_user,
            account_id=None,
        )
        
        assert response.data.total_work_centers == 10
        assert response.data.total_stations == 25
        assert response.data.active_work_centers == 8
        assert response.data.bottleneck_stations == 3


# =============================================================================
# Station CRUD Tests
# =============================================================================


class TestListStations:
    """Test list_stations endpoint."""

    @pytest.mark.asyncio
    async def test_list_stations_empty(self, mock_db, mock_user, sample_work_center):
        """Test listing stations when none exist."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_center)),  # work center exists
            MagicMock(scalar=MagicMock(return_value=0)),  # count
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # items
        ])
        
        response = await list_stations(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            station_type=None,
            status=None,
            search=None,
            include_deleted=False,
        )
        
        assert response.data == []
        assert response.pagination.total_items == 0

    @pytest.mark.asyncio
    async def test_list_stations_with_items(self, mock_db, mock_user, sample_work_center, sample_station):
        """Test listing stations with items."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_center)),
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_station])))),
        ])
        
        response = await list_stations(
            work_center_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            station_type=None,
            status=None,
            search=None,
            include_deleted=False,
        )
        
        assert len(response.data) == 1
        assert response.data[0].id == sample_station.id

    @pytest.mark.asyncio
    async def test_list_stations_work_center_not_found(self, mock_db, mock_user):
        """Test listing stations when work center doesn't exist."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await list_stations(
                work_center_id=999,
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                station_type=None,
                status=None,
                search=None,
                include_deleted=False,
            )


class TestCreateStation:
    """Test create_station endpoint."""

    @pytest.mark.asyncio
    async def test_create_station_success(self, mock_db, mock_user, sample_work_center):
        """Test successful station creation."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_center)),  # wc exists
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # no duplicate code
        ])
        
        # Use capture pattern for db.add to set attributes on the actual Station object
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            # Set the ID on the object as the DB would
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.deleted_at = None
        
        mock_db.add = MagicMock(side_effect=capture_add)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        data = StationBase(
            name="New Station",
            code="ST-NEW",
        )
        
        response = await create_station(
            work_center_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data.name == "New Station"
        assert response.message == "Station created successfully"

    @pytest.mark.asyncio
    async def test_create_station_work_center_not_found(self, mock_db, mock_user):
        """Test creating station when work center doesn't exist."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        data = StationBase(name="New Station", code="ST-NEW")
        
        with pytest.raises(NotFoundError):
            await create_station(
                work_center_id=999,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_create_station_duplicate_code(self, mock_db, mock_user, sample_work_center, sample_station):
        """Test creating station with duplicate code."""
        from sensei.api.exceptions import ConflictError
        
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_center)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_station)),  # duplicate
        ])
        
        data = StationBase(name="Another Station", code="ST-ASM-01")  # Duplicate
        
        with pytest.raises(ConflictError):
            await create_station(
                work_center_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestGetStation:
    """Test get_station endpoint."""

    @pytest.mark.asyncio
    async def test_get_station_success(self, mock_db, mock_user, sample_station):
        """Test getting a station by ID."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_station)
        ))
        
        response = await get_station(
            work_center_id=1,
            station_id=1,
            db=mock_db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data.id == sample_station.id

    @pytest.mark.asyncio
    async def test_get_station_not_found(self, mock_db, mock_user):
        """Test getting non-existent station."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await get_station(
                work_center_id=1,
                station_id=999,
                db=mock_db,
                current_user=mock_user,
                include_deleted=False,
            )


class TestUpdateStation:
    """Test update_station endpoint."""

    @pytest.mark.asyncio
    async def test_update_station_success(self, mock_db, mock_user, sample_station):
        """Test updating a station."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_station)
        ))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        data = StationUpdate(
            name="Updated Station Name",
            cycle_time_seconds=70,
        )
        
        response = await update_station(
            work_center_id=1,
            station_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.message == "Station updated successfully"

    @pytest.mark.asyncio
    async def test_update_station_not_found(self, mock_db, mock_user):
        """Test updating non-existent station."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        data = StationUpdate(name="Updated Name")
        
        with pytest.raises(NotFoundError):
            await update_station(
                work_center_id=1,
                station_id=999,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_update_station_duplicate_code(self, mock_db, mock_user, sample_station):
        """Test updating station with duplicate code."""
        from sensei.api.exceptions import ConflictError
        
        existing_station = MagicMock()
        existing_station.id = 2
        existing_station.code = "ST-DUP"
        
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_station)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_station)),
        ])
        
        data = StationUpdate(code="ST-DUP")
        
        with pytest.raises(ConflictError):
            await update_station(
                work_center_id=1,
                station_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestDeleteStation:
    """Test delete_station endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_station(self, mock_db, mock_user, sample_station):
        """Test soft deleting a station."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_station)
        ))
        mock_db.commit = AsyncMock()
        
        response = await delete_station(
            work_center_id=1,
            station_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response.message == "Station deleted successfully"
        assert sample_station.deleted_at is not None

    @pytest.mark.asyncio
    async def test_hard_delete_station(self, mock_db, mock_user, sample_station):
        """Test hard deleting a station."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_station)
        ))
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        response = await delete_station(
            work_center_id=1,
            station_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=True,
        )
        
        assert response.message == "Station deleted successfully"
        mock_db.delete.assert_called_once_with(sample_station)

    @pytest.mark.asyncio
    async def test_delete_station_not_found(self, mock_db, mock_user):
        """Test deleting non-existent station."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await delete_station(
                work_center_id=1,
                station_id=999,
                db=mock_db,
                current_user=mock_user,
                hard_delete=False,
            )


class TestRestoreStation:
    """Test restore_station endpoint."""

    @pytest.mark.asyncio
    async def test_restore_station_success(self, mock_db, mock_user, sample_station):
        """Test restoring a soft-deleted station."""
        sample_station.deleted_at = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_station)
        ))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        response = await restore_station(
            work_center_id=1,
            station_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.message == "Station restored successfully"
        assert sample_station.deleted_at is None

    @pytest.mark.asyncio
    async def test_restore_station_not_found(self, mock_db, mock_user):
        """Test restoring non-existent deleted station."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await restore_station(
                work_center_id=1,
                station_id=999,
                db=mock_db,
                current_user=mock_user,
            )


class TestCreateStationDirect:
    """Test create_station_direct endpoint."""

    @pytest.mark.asyncio
    async def test_create_station_direct_success(self, mock_db, mock_user, sample_work_center):
        """Test creating station via direct endpoint."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_center)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ])
        
        # Use capture pattern for db.add to set attributes on the actual Station object
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            # Set the ID on the object as the DB would
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.deleted_at = None
        
        mock_db.add = MagicMock(side_effect=capture_add)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        data = StationCreate(
            name="Direct Station",
            code="ST-DIR",
            work_center_id=1,
        )
        
        response = await create_station_direct(
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data.name == "Direct Station"


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestWorkCenterSchemaValidation:
    """Test work center schema validation."""

    def test_work_center_create_valid(self):
        """Test valid work center create schema."""
        data = WorkCenterCreate(
            name="Test Work Center",
            code="WC-TEST",
            efficiency_target=85.0,
        )
        assert data.name == "Test Work Center"
        assert data.code == "WC-TEST"
        assert data.efficiency_target == 85.0

    def test_work_center_create_invalid_status(self):
        """Test work center create with invalid status."""
        with pytest.raises(ValueError):
            WorkCenterCreate(
                name="Test",
                code="WC-TEST",
                status="invalid_status",
            )

    def test_work_center_create_default_values(self):
        """Test work center create default values."""
        data = WorkCenterCreate(
            name="Test",
            code="WC-TEST",
        )
        assert data.status == "active"
        assert data.efficiency_target == 85.0
        assert data.capacity_units == "units/hour"

    def test_work_center_update_valid(self):
        """Test valid work center update schema."""
        data = WorkCenterUpdate(
            name="Updated Name",
            efficiency_target=90.0,
        )
        assert data.name == "Updated Name"
        assert data.efficiency_target == 90.0

    def test_work_center_update_invalid_status(self):
        """Test work center update with invalid status."""
        with pytest.raises(ValueError):
            WorkCenterUpdate(status="invalid_status")

    def test_work_center_update_null_status_allowed(self):
        """Test work center update allows null status."""
        data = WorkCenterUpdate(status=None)
        assert data.status is None

    def test_work_center_efficiency_bounds(self):
        """Test efficiency target bounds."""
        # Valid bounds
        data1 = WorkCenterCreate(name="Test", code="WC1", efficiency_target=0)
        assert data1.efficiency_target == 0

        data2 = WorkCenterCreate(name="Test", code="WC2", efficiency_target=100)
        assert data2.efficiency_target == 100

        # Invalid bounds
        with pytest.raises(ValueError):
            WorkCenterCreate(name="Test", code="WC3", efficiency_target=-1)

        with pytest.raises(ValueError):
            WorkCenterCreate(name="Test", code="WC4", efficiency_target=101)


class TestStationSchemaValidation:
    """Test station schema validation."""

    def test_station_base_valid(self):
        """Test valid station base schema."""
        data = StationBase(
            name="Test Station",
            code="ST-TEST",
        )
        assert data.name == "Test Station"
        assert data.code == "ST-TEST"

    def test_station_base_invalid_station_type(self):
        """Test station base with invalid station type."""
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                station_type="invalid_type",
            )

    def test_station_base_invalid_status(self):
        """Test station base with invalid status."""
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                status="invalid_status",
            )

    def test_station_base_default_values(self):
        """Test station base default values."""
        data = StationBase(name="Test", code="ST-TEST")
        assert data.station_type == "assembly"
        assert data.status == "active"
        assert data.takt_time_seconds == 60
        assert data.cycle_time_seconds == 60
        assert data.setup_time_seconds == 0
        assert data.yellow_ack_minutes == 5
        assert data.red_ack_minutes == 2
        assert data.resolution_target_minutes == 30

    def test_station_time_constraints(self):
        """Test station time field constraints."""
        # Valid values
        data = StationBase(
            name="Test",
            code="ST-TEST",
            takt_time_seconds=120,
            cycle_time_seconds=100,
            setup_time_seconds=60,
        )
        assert data.takt_time_seconds == 120
        assert data.cycle_time_seconds == 100
        assert data.setup_time_seconds == 60

        # Invalid: takt_time must be > 0
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                takt_time_seconds=0,
            )

        # Invalid: cycle_time must be > 0
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                cycle_time_seconds=0,
            )

        # Invalid: setup_time must be >= 0
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                setup_time_seconds=-1,
            )

    def test_station_create_requires_work_center_id(self):
        """Test station create requires work_center_id."""
        data = StationCreate(
            name="Test",
            code="ST-TEST",
            work_center_id=1,
        )
        assert data.work_center_id == 1

    def test_station_update_all_optional(self):
        """Test station update with all fields optional."""
        data = StationUpdate()
        assert data.name is None
        assert data.code is None
        assert data.takt_time_seconds is None

    def test_station_update_valid(self):
        """Test valid station update schema."""
        data = StationUpdate(
            name="Updated Station",
            cycle_time_seconds=75,
        )
        assert data.name == "Updated Station"
        assert data.cycle_time_seconds == 75


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_work_center_name_max_length(self):
        """Test work center name max length."""
        # Valid: 255 chars
        data = WorkCenterCreate(
            name="A" * 255,
            code="WC-TEST",
        )
        assert len(data.name) == 255

        # Invalid: > 255 chars
        with pytest.raises(ValueError):
            WorkCenterCreate(
                name="A" * 256,
                code="WC-TEST",
            )

    def test_work_center_code_max_length(self):
        """Test work center code max length."""
        # Valid: 50 chars
        data = WorkCenterCreate(
            name="Test",
            code="A" * 50,
        )
        assert len(data.code) == 50

        # Invalid: > 50 chars
        with pytest.raises(ValueError):
            WorkCenterCreate(
                name="Test",
                code="A" * 51,
            )

    def test_work_center_empty_name(self):
        """Test work center with empty name."""
        with pytest.raises(ValueError):
            WorkCenterCreate(
                name="",
                code="WC-TEST",
            )

    def test_work_center_empty_code(self):
        """Test work center with empty code."""
        with pytest.raises(ValueError):
            WorkCenterCreate(
                name="Test",
                code="",
            )

    def test_station_empty_name(self):
        """Test station with empty name."""
        with pytest.raises(ValueError):
            StationBase(
                name="",
                code="ST-TEST",
            )

    def test_station_empty_code(self):
        """Test station with empty code."""
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="",
            )

    def test_station_andon_sla_constraints(self):
        """Test station Andon SLA constraints."""
        # Valid values
        data = StationBase(
            name="Test",
            code="ST-TEST",
            yellow_ack_minutes=10,
            red_ack_minutes=5,
            resolution_target_minutes=60,
        )
        assert data.yellow_ack_minutes == 10

        # Invalid: yellow_ack must be > 0
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                yellow_ack_minutes=0,
            )

        # Invalid: red_ack must be > 0
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                red_ack_minutes=0,
            )

        # Invalid: resolution_target must be > 0
        with pytest.raises(ValueError):
            StationBase(
                name="Test",
                code="ST-TEST",
                resolution_target_minutes=0,
            )

    def test_capacity_value_non_negative(self):
        """Test capacity_value must be non-negative."""
        # Valid: 0
        data = WorkCenterCreate(
            name="Test",
            code="WC-TEST",
            capacity_value=0,
        )
        assert data.capacity_value == 0

        # Invalid: negative
        with pytest.raises(ValueError):
            WorkCenterCreate(
                name="Test",
                code="WC-TEST",
                capacity_value=-1,
            )

    def test_all_station_types_valid(self):
        """Test all station types are valid."""
        valid_types = [
            "assembly", "machining", "inspection", "packaging",
            "testing", "rework", "welding", "painting",
            "cleaning", "material_handling"
        ]
        for st_type in valid_types:
            data = StationBase(
                name="Test",
                code="ST-TEST",
                station_type=st_type,
            )
            assert data.station_type == st_type

    def test_all_station_statuses_valid(self):
        """Test all station statuses are valid."""
        valid_statuses = [
            "active", "inactive", "maintenance", "breakdown", "changeover"
        ]
        for st_status in valid_statuses:
            data = StationBase(
                name="Test",
                code="ST-TEST",
                status=st_status,
            )
            assert data.status == st_status

    def test_all_work_center_statuses_valid(self):
        """Test all work center statuses are valid."""
        valid_statuses = ["active", "inactive", "maintenance", "decommissioned"]
        for wc_status in valid_statuses:
            data = WorkCenterCreate(
                name="Test",
                code="WC-TEST",
                status=wc_status,
            )
            assert data.status == wc_status

"""
Comprehensive tests for Production Cells API endpoints.

Tests cover:
- Production Cell CRUD operations
- Cell Performance tracking
- OEE calculations
- Status transitions
- Operator management
- Output tracking
- Edge cases and error handling
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sensei.api.v1.endpoints.production_cells import (
    router,
    ProductionCellCreate,
    ProductionCellUpdate,
    ProductionCellResponse,
    ProductionCellListResponse,
    CellPerformanceCreate,
    CellPerformanceUpdate,
    CellPerformanceResponse,
    CellPerformanceListResponse,
    CellStatsResponse,
    CellDailyOEEResponse,
    cell_to_response,
    performance_to_response,
    list_production_cells,
    create_production_cell,
    get_production_cell,
    update_production_cell,
    delete_production_cell,
    restore_production_cell,
    set_cell_status,
    update_operators,
    update_output,
    reset_shift,
    get_cell_stats,
    list_cell_performances,
    create_cell_performance,
    get_cell_performance,
    update_cell_performance,
    delete_cell_performance,
    get_cell_oee_trend,
)
from sensei.models.production import (
    ProductionCell,
    CellPerformance,
    CellType,
    CellStatus,
    ShiftNumber,
)
from sensei.models.user import User


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    return user


@pytest.fixture
def sample_cell():
    """Create a sample production cell."""
    cell = MagicMock(spec=ProductionCell)
    cell.id = 1
    cell.name = "Assembly Cell 1"
    cell.code = "CELL-001"
    cell.description = "Main assembly cell"
    cell.work_center_id = 1
    cell.cell_type = CellType.U_CELL
    cell.status = CellStatus.ACTIVE
    cell.takt_time_seconds = 60
    cell.target_cycle_time_seconds = 55
    cell.target_output_per_shift = 480
    cell.shift_duration_hours = Decimal("8.0")
    cell.planned_efficiency = Decimal("85.00")
    cell.current_output = 240
    cell.current_efficiency_percentage = Decimal("80.00")
    cell.current_oee_percentage = Decimal("75.00")
    cell.min_operators = 2
    cell.standard_operators = 3
    cell.max_operators = 4
    cell.current_operators = 3
    cell.stations = []
    cell.created_at = datetime.now(timezone.utc)
    cell.updated_at = datetime.now(timezone.utc)
    cell.deleted_at = None
    
    # Computed properties
    cell.station_count = 0
    cell.is_operational = True
    cell.is_understaffed = False
    cell.output_vs_target_percentage = Decimal("50.00")
    cell.theoretical_capacity_per_shift = 480
    
    return cell


@pytest.fixture
def sample_cell_string_enums():
    """Create a sample production cell with string enum values."""
    cell = MagicMock(spec=ProductionCell)
    cell.id = 2
    cell.name = "Paint Cell"
    cell.code = "CELL-002"
    cell.description = "Paint booth cell"
    cell.work_center_id = 2
    cell.cell_type = "flow"
    cell.status = "maintenance"
    cell.takt_time_seconds = 90
    cell.target_cycle_time_seconds = 85
    cell.target_output_per_shift = 320
    cell.shift_duration_hours = Decimal("8.0")
    cell.planned_efficiency = Decimal("90.00")
    cell.current_output = 0
    cell.current_efficiency_percentage = None
    cell.current_oee_percentage = None
    cell.min_operators = 1
    cell.standard_operators = 2
    cell.max_operators = 3
    cell.current_operators = 0
    cell.stations = []
    cell.created_at = datetime.now(timezone.utc)
    cell.updated_at = datetime.now(timezone.utc)
    cell.deleted_at = None
    
    cell.station_count = 0
    cell.is_operational = False
    cell.is_understaffed = True
    cell.output_vs_target_percentage = Decimal("0")
    cell.theoretical_capacity_per_shift = 320
    
    return cell


@pytest.fixture
def sample_performance():
    """Create a sample cell performance record."""
    perf = MagicMock(spec=CellPerformance)
    perf.id = 1
    perf.cell_id = 1
    perf.shift_date = date(2025, 1, 15)
    perf.shift_number = ShiftNumber.SHIFT_1
    perf.planned_output = 480
    perf.actual_output = 450
    perf.good_output = 440
    perf.rework_output = 5
    perf.scrap_output = 5
    perf.planned_time_minutes = 480
    perf.operating_time_minutes = 450
    perf.downtime_minutes = 30
    perf.changeover_minutes = 15
    perf.unplanned_downtime_minutes = 15
    perf.planned_downtime_minutes = 15
    perf.availability_percentage = Decimal("93.75")
    perf.performance_percentage = Decimal("91.67")
    perf.quality_percentage = Decimal("97.78")
    perf.oee_percentage = Decimal("84.03")
    perf.efficiency_percentage = Decimal("93.75")
    perf.operator_count = 3
    perf.labor_hours = Decimal("24.00")
    perf.units_per_labor_hour = Decimal("18.33")
    perf.andon_events_count = 2
    perf.quality_issues_count = 1
    perf.notes = "Good shift"
    perf.issues_summary = None
    perf.created_at = datetime.now(timezone.utc)
    perf.updated_at = datetime.now(timezone.utc)
    
    perf.output_target_ratio = Decimal("93.75")
    perf.scrap_rate = Decimal("1.11")
    
    return perf


@pytest.fixture
def sample_performance_string_enums():
    """Create a sample performance with string enum values."""
    perf = MagicMock(spec=CellPerformance)
    perf.id = 2
    perf.cell_id = 1
    perf.shift_date = date(2025, 1, 15)
    perf.shift_number = "shift_2"
    perf.planned_output = 480
    perf.actual_output = 400
    perf.good_output = 380
    perf.rework_output = 10
    perf.scrap_output = 10
    perf.planned_time_minutes = 480
    perf.operating_time_minutes = 420
    perf.downtime_minutes = 60
    perf.changeover_minutes = 20
    perf.unplanned_downtime_minutes = 40
    perf.planned_downtime_minutes = 20
    perf.availability_percentage = Decimal("87.50")
    perf.performance_percentage = Decimal("85.00")
    perf.quality_percentage = Decimal("95.00")
    perf.oee_percentage = Decimal("70.66")
    perf.efficiency_percentage = Decimal("83.33")
    perf.operator_count = 2
    perf.labor_hours = Decimal("16.00")
    perf.units_per_labor_hour = Decimal("23.75")
    perf.andon_events_count = 5
    perf.quality_issues_count = 3
    perf.notes = "Issues with machine 2"
    perf.issues_summary = "Machine 2 required maintenance"
    perf.created_at = datetime.now(timezone.utc)
    perf.updated_at = datetime.now(timezone.utc)
    
    perf.output_target_ratio = Decimal("83.33")
    perf.scrap_rate = Decimal("2.50")
    
    return perf


# =============================================================================
# Conversion Function Tests
# =============================================================================


class TestCellConversion:
    """Tests for production cell conversion functions."""

    def test_cell_to_response(self, sample_cell):
        """Test converting a production cell to response."""
        response = cell_to_response(sample_cell)
        
        assert isinstance(response, ProductionCellResponse)
        assert response.id == 1
        assert response.name == "Assembly Cell 1"
        assert response.code == "CELL-001"
        assert response.cell_type == "u_cell"
        assert response.status == "active"
        assert response.takt_time_seconds == 60
        assert response.target_output_per_shift == 480
        assert response.current_output == 240
        assert response.is_operational is True
        assert response.is_understaffed is False

    def test_cell_to_response_with_string_enums(self, sample_cell_string_enums):
        """Test converting a cell with string enum values."""
        response = cell_to_response(sample_cell_string_enums)
        
        assert isinstance(response, ProductionCellResponse)
        assert response.cell_type == "flow"
        assert response.status == "maintenance"
        assert response.is_operational is False
        assert response.is_understaffed is True


class TestPerformanceConversion:
    """Tests for cell performance conversion functions."""

    def test_performance_to_response(self, sample_performance):
        """Test converting a performance record to response."""
        response = performance_to_response(sample_performance)
        
        assert isinstance(response, CellPerformanceResponse)
        assert response.id == 1
        assert response.cell_id == 1
        assert response.shift_date == date(2025, 1, 15)
        assert response.shift_number == "shift_1"
        assert response.planned_output == 480
        assert response.actual_output == 450
        assert response.oee_percentage == Decimal("84.03")
        assert response.scrap_rate == Decimal("1.11")

    def test_performance_to_response_with_string_enum(self, sample_performance_string_enums):
        """Test converting a performance with string enum values."""
        response = performance_to_response(sample_performance_string_enums)
        
        assert isinstance(response, CellPerformanceResponse)
        assert response.shift_number == "shift_2"
        assert response.oee_percentage == Decimal("70.66")


# =============================================================================
# List Production Cells Tests
# =============================================================================


class TestListProductionCells:
    """Tests for list production cells endpoint."""

    @pytest.mark.asyncio
    async def test_list_cells_empty(self, mock_db, mock_user):
        """Test listing cells when none exist."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])
        
        response = await list_production_cells(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            work_center_id=None,
            cell_type=None,
            status=None,
            search=None,
            sort_by="name",
            sort_order="asc",
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.cells == []
        assert response.total == 0

    @pytest.mark.asyncio
    async def test_list_cells_with_items(self, mock_db, mock_user, sample_cell):
        """Test listing cells with results."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_cell])))),
        ])
        
        response = await list_production_cells(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            work_center_id=None,
            cell_type=None,
            status=None,
            search=None,
            sort_by="name",
            sort_order="asc",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.cells) == 1
        assert response.total == 1
        assert response.cells[0].code == "CELL-001"

    @pytest.mark.asyncio
    async def test_list_cells_with_cell_type_filter(self, mock_db, mock_user, sample_cell):
        """Test listing cells with cell type filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_cell])))),
        ])
        
        response = await list_production_cells(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            work_center_id=None,
            cell_type="u_cell",
            status=None,
            search=None,
            sort_by="name",
            sort_order="asc",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.cells) == 1

    @pytest.mark.asyncio
    async def test_list_cells_with_status_filter(self, mock_db, mock_user, sample_cell):
        """Test listing cells with status filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_cell])))),
        ])
        
        response = await list_production_cells(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            work_center_id=None,
            cell_type=None,
            status="active",
            search=None,
            sort_by="name",
            sort_order="asc",
            include_deleted=False,
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_list_cells_invalid_cell_type(self, mock_db, mock_user):
        """Test listing cells with invalid cell type."""
        from sensei.api.exceptions import BadRequestError
        
        with pytest.raises(BadRequestError) as exc_info:
            await list_production_cells(
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                work_center_id=None,
                cell_type="invalid_type",
                status=None,
                search=None,
                sort_by="name",
                sort_order="asc",
                include_deleted=False,
            )
        
        assert "Invalid cell_type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_cells_invalid_status(self, mock_db, mock_user):
        """Test listing cells with invalid status."""
        from sensei.api.exceptions import BadRequestError
        
        with pytest.raises(BadRequestError) as exc_info:
            await list_production_cells(
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                work_center_id=None,
                cell_type=None,
                status="invalid_status",
                search=None,
                sort_by="name",
                sort_order="asc",
                include_deleted=False,
            )
        
        assert "Invalid status" in str(exc_info.value)


# =============================================================================
# Create Production Cell Tests
# =============================================================================


class TestCreateProductionCell:
    """Tests for create production cell endpoint."""

    @pytest.mark.asyncio
    async def test_create_cell_success(self, mock_db, mock_user):
        """Test successfully creating a production cell."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.current_output = 0
            obj.current_operators = 0
            obj.current_efficiency_percentage = None
            obj.current_oee_percentage = None
            obj.deleted_at = None
            obj.stations = []
            # Note: station_count, is_operational, is_understaffed, 
            # output_vs_target_percentage, theoretical_capacity_per_shift are computed properties
        
        mock_db.add = MagicMock(side_effect=capture_add)
        
        data = ProductionCellCreate(
            name="New Cell",
            code="NEW-001",
            work_center_id=1,
            takt_time_seconds=60,
            min_operators=1,
            standard_operators=2,
            max_operators=3,
        )
        
        response = await create_production_cell(
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert response["message"] == "Production cell created successfully"

    @pytest.mark.asyncio
    async def test_create_cell_duplicate_code(self, mock_db, mock_user, sample_cell):
        """Test creating cell with duplicate code."""
        from sensei.api.exceptions import ConflictError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        data = ProductionCellCreate(
            name="Duplicate Cell",
            code="CELL-001",
            work_center_id=1,
        )
        
        with pytest.raises(ConflictError) as exc_info:
            await create_production_cell(
                data=data,
                db=mock_db,
                current_user=mock_user,
            )
        
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_cell_invalid_operator_constraints(self, mock_db, mock_user):
        """Test creating cell with invalid operator constraints."""
        from sensei.api.exceptions import BadRequestError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        # standard_operators < min_operators
        data = ProductionCellCreate(
            name="Bad Cell",
            code="BAD-001",
            work_center_id=1,
            min_operators=3,
            standard_operators=2,
            max_operators=4,
        )
        
        with pytest.raises(BadRequestError) as exc_info:
            await create_production_cell(
                data=data,
                db=mock_db,
                current_user=mock_user,
            )
        
        assert "standard_operators must be >= min_operators" in str(exc_info.value)


# =============================================================================
# Get Production Cell Tests
# =============================================================================


class TestGetProductionCell:
    """Tests for get production cell endpoint."""

    @pytest.mark.asyncio
    async def test_get_cell_success(self, mock_db, mock_user, sample_cell):
        """Test successfully getting a production cell."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await get_production_cell(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response["success"] is True
        assert response["cell"].code == "CELL-001"

    @pytest.mark.asyncio
    async def test_get_cell_not_found(self, mock_db, mock_user):
        """Test getting a cell that doesn't exist."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError) as exc_info:
            await get_production_cell(
                cell_id=999,
                db=mock_db,
                current_user=mock_user,
                include_deleted=False,
            )
        
        assert "not found" in str(exc_info.value)


# =============================================================================
# Update Production Cell Tests
# =============================================================================


class TestUpdateProductionCell:
    """Tests for update production cell endpoint."""

    @pytest.mark.asyncio
    async def test_update_cell_success(self, mock_db, mock_user, sample_cell):
        """Test successfully updating a production cell."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        data = ProductionCellUpdate(name="Updated Cell Name")
        
        response = await update_production_cell(
            cell_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert response["message"] == "Production cell updated successfully"

    @pytest.mark.asyncio
    async def test_update_cell_not_found(self, mock_db, mock_user):
        """Test updating a cell that doesn't exist."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        data = ProductionCellUpdate(name="Updated")
        
        with pytest.raises(NotFoundError):
            await update_production_cell(
                cell_id=999,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Delete Production Cell Tests
# =============================================================================


class TestDeleteProductionCell:
    """Tests for delete production cell endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_cell(self, mock_db, mock_user, sample_cell):
        """Test soft deleting a production cell."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await delete_production_cell(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response["success"] is True
        assert "deleted successfully" in response["message"]

    @pytest.mark.asyncio
    async def test_hard_delete_cell(self, mock_db, mock_user, sample_cell):
        """Test hard deleting a production cell."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await delete_production_cell(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=True,
        )
        
        assert response["success"] is True
        assert "permanently deleted" in response["message"]


# =============================================================================
# Restore Production Cell Tests
# =============================================================================


class TestRestoreProductionCell:
    """Tests for restore production cell endpoint."""

    @pytest.mark.asyncio
    async def test_restore_cell_success(self, mock_db, mock_user, sample_cell):
        """Test restoring a soft-deleted production cell."""
        sample_cell.deleted_at = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await restore_production_cell(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert "restored" in response["message"]

    @pytest.mark.asyncio
    async def test_restore_cell_not_found(self, mock_db, mock_user):
        """Test restoring a cell that doesn't exist."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await restore_production_cell(
                cell_id=999,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Set Cell Status Tests
# =============================================================================


class TestSetCellStatus:
    """Tests for set cell status endpoint."""

    @pytest.mark.asyncio
    async def test_set_status_success(self, mock_db, mock_user, sample_cell):
        """Test setting cell status."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await set_cell_status(
            cell_id=1,
            status="maintenance",
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert "status changed" in response["message"]

    @pytest.mark.asyncio
    async def test_set_status_invalid(self, mock_db, mock_user):
        """Test setting invalid status."""
        from sensei.api.exceptions import BadRequestError
        
        with pytest.raises(BadRequestError) as exc_info:
            await set_cell_status(
                cell_id=1,
                status="invalid_status",
                db=mock_db,
                current_user=mock_user,
            )
        
        assert "Invalid status" in str(exc_info.value)


# =============================================================================
# Update Operators Tests
# =============================================================================


class TestUpdateOperators:
    """Tests for update operators endpoint."""

    @pytest.mark.asyncio
    async def test_update_operators_success(self, mock_db, mock_user, sample_cell):
        """Test updating operator count."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await update_operators(
            cell_id=1,
            operator_count=4,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert "updated to 4" in response["message"]

    @pytest.mark.asyncio
    async def test_update_operators_negative(self, mock_db, mock_user):
        """Test updating with negative operator count."""
        from sensei.api.exceptions import BadRequestError
        
        with pytest.raises(BadRequestError) as exc_info:
            await update_operators(
                cell_id=1,
                operator_count=-1,
                db=mock_db,
                current_user=mock_user,
            )
        
        assert "cannot be negative" in str(exc_info.value)


# =============================================================================
# Update Output Tests
# =============================================================================


class TestUpdateOutput:
    """Tests for update output endpoint."""

    @pytest.mark.asyncio
    async def test_update_output_success(self, mock_db, mock_user, sample_cell):
        """Test updating output."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await update_output(
            cell_id=1,
            output=300,
            db=mock_db,
            current_user=mock_user,
            efficiency_percentage=None,
            oee_percentage=None,
        )
        
        assert response["success"] is True
        assert "updated to 300" in response["message"]

    @pytest.mark.asyncio
    async def test_update_output_with_metrics(self, mock_db, mock_user, sample_cell):
        """Test updating output with efficiency and OEE."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await update_output(
            cell_id=1,
            output=350,
            db=mock_db,
            current_user=mock_user,
            efficiency_percentage=Decimal("85.50"),
            oee_percentage=Decimal("80.25"),
        )
        
        assert response["success"] is True

    @pytest.mark.asyncio
    async def test_update_output_negative(self, mock_db, mock_user):
        """Test updating with negative output."""
        from sensei.api.exceptions import BadRequestError
        
        with pytest.raises(BadRequestError) as exc_info:
            await update_output(
                cell_id=1,
                output=-10,
                db=mock_db,
                current_user=mock_user,
                efficiency_percentage=None,
                oee_percentage=None,
            )
        
        assert "cannot be negative" in str(exc_info.value)


# =============================================================================
# Reset Shift Tests
# =============================================================================


class TestResetShift:
    """Tests for reset shift endpoint."""

    @pytest.mark.asyncio
    async def test_reset_shift_success(self, mock_db, mock_user, sample_cell):
        """Test resetting shift metrics."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        response = await reset_shift(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert "reset successfully" in response["message"]

    @pytest.mark.asyncio
    async def test_reset_shift_not_found(self, mock_db, mock_user):
        """Test resetting shift for non-existent cell."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await reset_shift(
                cell_id=999,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Get Cell Stats Tests
# =============================================================================


class TestGetCellStats:
    """Tests for get cell stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, mock_db, mock_user, sample_cell):
        """Test getting cell statistics."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_cell])))
        ))
        
        response = await get_cell_stats(
            db=mock_db,
            current_user=mock_user,
            work_center_id=None,
        )
        
        assert response.success is True
        assert response.total_cells == 1
        assert response.active_cells == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, mock_db, mock_user):
        """Test getting stats when no cells exist."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        ))
        
        response = await get_cell_stats(
            db=mock_db,
            current_user=mock_user,
            work_center_id=None,
        )
        
        assert response.success is True
        assert response.total_cells == 0
        assert response.average_oee is None


# =============================================================================
# Cell Performance Endpoint Tests
# =============================================================================


class TestListCellPerformances:
    """Tests for list cell performances endpoint."""

    @pytest.mark.asyncio
    async def test_list_performances_empty(self, mock_db, mock_user, sample_cell):
        """Test listing performances when none exist."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])
        
        response = await list_cell_performances(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            shift_number=None,
            start_date=None,
            end_date=None,
            sort_by="shift_date",
            sort_order="desc",
        )
        
        assert response.success is True
        assert response.performances == []

    @pytest.mark.asyncio
    async def test_list_performances_with_items(self, mock_db, mock_user, sample_cell, sample_performance):
        """Test listing performances with results."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_performance])))),
        ])
        
        response = await list_cell_performances(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            shift_number=None,
            start_date=None,
            end_date=None,
            sort_by="shift_date",
            sort_order="desc",
        )
        
        assert response.success is True
        assert len(response.performances) == 1
        assert response.total == 1

    @pytest.mark.asyncio
    async def test_list_performances_cell_not_found(self, mock_db, mock_user):
        """Test listing performances for non-existent cell."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await list_cell_performances(
                cell_id=999,
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                shift_number=None,
                start_date=None,
                end_date=None,
                sort_by="shift_date",
                sort_order="desc",
            )


class TestCreateCellPerformance:
    """Tests for create cell performance endpoint."""

    @pytest.mark.asyncio
    async def test_create_performance_success(self, mock_db, mock_user, sample_cell):
        """Test successfully creating a performance record."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ])
        
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            # Note: output_target_ratio and scrap_rate are computed properties
        
        mock_db.add = MagicMock(side_effect=capture_add)
        
        data = CellPerformanceCreate(
            shift_date=date(2025, 1, 15),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=480,
            actual_output=450,
            good_output=440,
            planned_time_minutes=480,
            operating_time_minutes=450,
        )
        
        response = await create_cell_performance(
            cell_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert response["message"] == "Performance record created successfully"

    @pytest.mark.asyncio
    async def test_create_performance_duplicate(self, mock_db, mock_user, sample_cell, sample_performance):
        """Test creating duplicate performance record."""
        from sensei.api.exceptions import ConflictError
        
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_performance)),
        ])
        
        data = CellPerformanceCreate(
            shift_date=date(2025, 1, 15),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=480,
            actual_output=450,
            good_output=440,
            planned_time_minutes=480,
            operating_time_minutes=450,
        )
        
        with pytest.raises(ConflictError):
            await create_cell_performance(
                cell_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestGetCellPerformance:
    """Tests for get cell performance endpoint."""

    @pytest.mark.asyncio
    async def test_get_performance_success(self, mock_db, mock_user, sample_performance):
        """Test getting a performance record."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_performance)
        ))
        
        response = await get_cell_performance(
            cell_id=1,
            performance_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert response["performance"].id == 1

    @pytest.mark.asyncio
    async def test_get_performance_not_found(self, mock_db, mock_user):
        """Test getting non-existent performance record."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await get_cell_performance(
                cell_id=1,
                performance_id=999,
                db=mock_db,
                current_user=mock_user,
            )


class TestUpdateCellPerformance:
    """Tests for update cell performance endpoint."""

    @pytest.mark.asyncio
    async def test_update_performance_success(self, mock_db, mock_user, sample_performance, sample_cell):
        """Test updating a performance record."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_performance)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
        ])
        
        data = CellPerformanceUpdate(actual_output=460)
        
        response = await update_cell_performance(
            cell_id=1,
            performance_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert response["message"] == "Performance record updated successfully"


class TestDeleteCellPerformance:
    """Tests for delete cell performance endpoint."""

    @pytest.mark.asyncio
    async def test_delete_performance_success(self, mock_db, mock_user, sample_performance):
        """Test deleting a performance record."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_performance)
        ))
        
        response = await delete_cell_performance(
            cell_id=1,
            performance_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response["success"] is True
        assert response["message"] == "Performance record deleted successfully"


# =============================================================================
# OEE Trend Tests
# =============================================================================


class TestGetCellOEETrend:
    """Tests for get cell OEE trend endpoint."""

    @pytest.mark.asyncio
    async def test_get_oee_trend_success(self, mock_db, mock_user, sample_cell, sample_performance):
        """Test getting OEE trend data."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_performance])))),
        ])
        
        response = await get_cell_oee_trend(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        
        assert response.success is True
        assert response.cell_id == 1
        assert response.cell_code == "CELL-001"
        assert len(response.daily_data) == 1
        assert response.average_oee is not None

    @pytest.mark.asyncio
    async def test_get_oee_trend_invalid_date_range(self, mock_db, mock_user, sample_cell):
        """Test getting OEE trend with invalid date range."""
        from sensei.api.exceptions import BadRequestError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        with pytest.raises(BadRequestError) as exc_info:
            await get_cell_oee_trend(
                cell_id=1,
                db=mock_db,
                current_user=mock_user,
                start_date=date(2025, 1, 31),
                end_date=date(2025, 1, 1),
            )
        
        assert "start_date must be before" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_oee_trend_empty_data(self, mock_db, mock_user, sample_cell):
        """Test getting OEE trend with no data."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])
        
        response = await get_cell_oee_trend(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        
        assert response.success is True
        assert response.daily_data == []
        assert response.average_oee is None


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestProductionCellSchemaValidation:
    """Tests for production cell schema validation."""

    def test_cell_create_valid(self):
        """Test valid cell creation schema."""
        data = ProductionCellCreate(
            name="Test Cell",
            code="TEST-001",
            work_center_id=1,
        )
        assert data.name == "Test Cell"
        assert data.code == "TEST-001"
        assert data.cell_type == CellType.U_CELL

    def test_cell_create_invalid_cell_type(self):
        """Test cell creation with invalid cell type."""
        with pytest.raises(ValidationError):
            ProductionCellCreate(
                name="Test Cell",
                code="TEST-001",
                work_center_id=1,
                cell_type="invalid_type",
            )

    def test_cell_create_invalid_status(self):
        """Test cell creation with invalid status."""
        with pytest.raises(ValidationError):
            ProductionCellCreate(
                name="Test Cell",
                code="TEST-001",
                work_center_id=1,
                status="invalid_status",
            )

    def test_cell_create_invalid_takt_time(self):
        """Test cell creation with invalid takt time."""
        with pytest.raises(ValidationError):
            ProductionCellCreate(
                name="Test Cell",
                code="TEST-001",
                work_center_id=1,
                takt_time_seconds=0,
            )

    def test_cell_create_invalid_efficiency(self):
        """Test cell creation with invalid efficiency."""
        with pytest.raises(ValidationError):
            ProductionCellCreate(
                name="Test Cell",
                code="TEST-001",
                work_center_id=1,
                planned_efficiency=Decimal("150.00"),
            )


class TestCellPerformanceSchemaValidation:
    """Tests for cell performance schema validation."""

    def test_performance_create_valid(self):
        """Test valid performance creation schema."""
        data = CellPerformanceCreate(
            shift_date=date(2025, 1, 15),
            shift_number=ShiftNumber.SHIFT_1,
            planned_output=480,
            actual_output=450,
            good_output=440,
            planned_time_minutes=480,
            operating_time_minutes=450,
        )
        assert data.shift_date == date(2025, 1, 15)
        assert data.shift_number == ShiftNumber.SHIFT_1

    def test_performance_create_invalid_shift_number(self):
        """Test performance creation with invalid shift number."""
        with pytest.raises(ValidationError):
            CellPerformanceCreate(
                shift_date=date(2025, 1, 15),
                shift_number="invalid_shift",
                planned_output=480,
                actual_output=450,
                good_output=440,
                planned_time_minutes=480,
                operating_time_minutes=450,
            )

    def test_performance_create_negative_output(self):
        """Test performance creation with negative output."""
        with pytest.raises(ValidationError):
            CellPerformanceCreate(
                shift_date=date(2025, 1, 15),
                shift_number=ShiftNumber.SHIFT_1,
                planned_output=-10,
                actual_output=450,
                good_output=440,
                planned_time_minutes=480,
                operating_time_minutes=450,
            )


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_list_cells_with_search(self, mock_db, mock_user, sample_cell):
        """Test listing cells with search query."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_cell])))),
        ])
        
        response = await list_production_cells(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            work_center_id=None,
            cell_type=None,
            status=None,
            search="assembly",
            sort_by="name",
            sort_order="asc",
            include_deleted=False,
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_list_cells_desc_sorting(self, mock_db, mock_user, sample_cell):
        """Test listing cells with descending sort."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_cell])))),
        ])
        
        response = await list_production_cells(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            work_center_id=None,
            cell_type=None,
            status=None,
            search=None,
            sort_by="created_at",
            sort_order="desc",
            include_deleted=False,
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_create_cell_max_operators_less_than_standard(self, mock_db, mock_user):
        """Test creating cell with max_operators < standard_operators."""
        from sensei.api.exceptions import BadRequestError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        data = ProductionCellCreate(
            name="Bad Cell",
            code="BAD-001",
            work_center_id=1,
            min_operators=1,
            standard_operators=3,
            max_operators=2,
        )
        
        with pytest.raises(BadRequestError) as exc_info:
            await create_production_cell(
                data=data,
                db=mock_db,
                current_user=mock_user,
            )
        
        assert "max_operators must be >= standard_operators" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_performances_with_shift_filter(self, mock_db, mock_user, sample_cell, sample_performance):
        """Test listing performances with shift filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_performance])))),
        ])
        
        response = await list_cell_performances(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            shift_number="shift_1",
            start_date=None,
            end_date=None,
            sort_by="shift_date",
            sort_order="desc",
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_list_performances_invalid_shift(self, mock_db, mock_user, sample_cell):
        """Test listing performances with invalid shift number."""
        from sensei.api.exceptions import BadRequestError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_cell)
        ))
        
        with pytest.raises(BadRequestError) as exc_info:
            await list_cell_performances(
                cell_id=1,
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                shift_number="invalid_shift",
                start_date=None,
                end_date=None,
                sort_by="shift_date",
                sort_order="desc",
            )
        
        assert "Invalid shift_number" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_performances_with_date_filter(self, mock_db, mock_user, sample_cell, sample_performance):
        """Test listing performances with date range filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_cell)),
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_performance])))),
        ])
        
        response = await list_cell_performances(
            cell_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            shift_number=None,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            sort_by="shift_date",
            sort_order="desc",
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_stats_with_multiple_cells(self, mock_db, mock_user, sample_cell, sample_cell_string_enums):
        """Test stats with multiple cells of different types."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(
                all=MagicMock(return_value=[sample_cell, sample_cell_string_enums])
            ))
        ))
        
        response = await get_cell_stats(
            db=mock_db,
            current_user=mock_user,
            work_center_id=None,
        )
        
        assert response.success is True
        assert response.total_cells == 2

    @pytest.mark.asyncio
    async def test_cell_response_with_stations(self, sample_cell):
        """Test cell response with station count."""
        sample_cell.stations = [MagicMock(), MagicMock(), MagicMock()]
        sample_cell.station_count = 3
        
        response = cell_to_response(sample_cell)
        
        assert response.station_count == 3

    @pytest.mark.asyncio
    async def test_oee_trend_cell_not_found(self, mock_db, mock_user):
        """Test OEE trend for non-existent cell."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await get_cell_oee_trend(
                cell_id=999,
                db=mock_db,
                current_user=mock_user,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
            )

    def test_cell_update_with_all_fields(self):
        """Test cell update schema with all fields."""
        data = ProductionCellUpdate(
            name="Updated Cell",
            description="Updated description",
            cell_type=CellType.LINE,
            status=CellStatus.MAINTENANCE,
            takt_time_seconds=90,
            target_cycle_time_seconds=85,
            target_output_per_shift=400,
            shift_duration_hours=Decimal("10.0"),
            planned_efficiency=Decimal("90.00"),
            min_operators=2,
            standard_operators=4,
            max_operators=6,
            current_operators=5,
            current_output=200,
            current_efficiency_percentage=Decimal("88.00"),
            current_oee_percentage=Decimal("82.00"),
        )
        
        assert data.name == "Updated Cell"
        assert data.cell_type == CellType.LINE

    def test_performance_update_with_all_fields(self):
        """Test performance update schema with all fields."""
        data = CellPerformanceUpdate(
            planned_output=500,
            actual_output=480,
            good_output=470,
            rework_output=5,
            scrap_output=5,
            planned_time_minutes=500,
            operating_time_minutes=480,
            downtime_minutes=20,
            changeover_minutes=10,
            unplanned_downtime_minutes=10,
            planned_downtime_minutes=10,
            operator_count=4,
            labor_hours=Decimal("32.00"),
            andon_events_count=3,
            quality_issues_count=2,
            notes="Updated notes",
            issues_summary="Updated issues",
        )
        
        assert data.planned_output == 500
        assert data.notes == "Updated notes"

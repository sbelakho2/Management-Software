"""
Comprehensive tests for Work Orders API endpoints.

Tests cover CRUD operations, work order lifecycle transitions,
and work order operations management.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from sensei.api.v1.endpoints.work_orders import (
    # Endpoints
    list_work_orders,
    create_work_order,
    get_work_order,
    update_work_order,
    delete_work_order,
    restore_work_order,
    get_work_order_stats,
    release_work_order,
    start_work_order,
    hold_work_order,
    resume_work_order,
    complete_work_order,
    cancel_work_order,
    close_work_order,
    list_operations,
    create_operation,
    get_operation,
    update_operation,
    delete_operation,
    start_operation,
    complete_operation,
    block_operation,
    unblock_operation,
    skip_operation,
    # Schemas
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderHold,
    WorkOrderRelease,
    WorkOrderResponse,
    WorkOrderListResponse,
    WorkOrderStatsResponse,
    WorkOrderOperationResponse,
    OperationCreate,
    OperationUpdate,
    OperationStart,
    OperationComplete,
    # Conversion functions
    work_order_to_response,
    work_order_to_list_response,
    operation_to_response,
)
from sensei.models.work_order import (
    WorkOrder,
    WorkOrderOperation,
    WorkOrderStatus,
    WorkOrderPriority,
    OperationStatus,
    HoldReason,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock current user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def sample_work_order(mock_user):
    """Create a sample work order."""
    wo = MagicMock(spec=WorkOrder)
    wo.id = 1
    wo.work_order_number = "WO-2024-0001"
    wo.external_reference = "PO-12345"
    wo.product_id = 10
    wo.quantity_ordered = Decimal("100")
    wo.quantity_completed = Decimal("50")
    wo.quantity_scrapped = Decimal("5")
    wo.quantity_in_progress = Decimal("10")
    wo.quantity_remaining = Decimal("45")
    wo.completion_percentage = Decimal("50.00")
    wo.yield_percentage = Decimal("90.91")
    wo.priority = WorkOrderPriority.HIGH
    wo.status = WorkOrderStatus.IN_PROGRESS
    wo.hold_reason = None
    wo.hold_notes = None
    wo.held_at = None
    wo.held_by_id = None
    wo.scheduled_start = datetime.now(timezone.utc)
    wo.scheduled_end = datetime.now(timezone.utc) + timedelta(days=5)
    wo.actual_start = datetime.now(timezone.utc)
    wo.actual_end = None
    wo.work_center_id = 1
    wo.current_station_id = 1
    wo.current_operation_sequence = 2
    wo.lot_number = "LOT-001"
    wo.batch_id = "BATCH-A"
    wo.notes = "Test work order"
    wo.production_notes = "Handle with care"
    wo.is_late = False
    wo.is_on_hold = False
    wo.operations = []
    wo.created_at = datetime.now(timezone.utc)
    wo.updated_at = datetime.now(timezone.utc)
    wo.created_by_id = mock_user.id
    wo.updated_by_id = None
    wo.deleted_at = None
    return wo


@pytest.fixture
def sample_operation(mock_user):
    """Create a sample work order operation."""
    op = MagicMock(spec=WorkOrderOperation)
    op.id = 1
    op.work_order_id = 1
    op.routing_id = 5
    op.sequence = 1
    op.operation_name = "Assembly Step 1"
    op.station_id = 10
    op.standard_time_seconds = 120
    op.setup_time_seconds = 30
    op.status = OperationStatus.IN_PROGRESS
    op.blocked_reason = None
    op.quantity_completed = Decimal("25")
    op.quantity_scrapped = Decimal("2")
    op.started_at = datetime.now(timezone.utc)
    op.completed_at = None
    op.actual_time_seconds = None
    op.actual_setup_seconds = None
    op.operator_id = mock_user.id
    op.notes = "Operation notes"
    op.efficiency = Decimal("95.50")
    op.elapsed_time_seconds = 3600
    op.is_active = True
    op.is_blocked = False
    op.created_at = datetime.now(timezone.utc)
    op.updated_at = datetime.now(timezone.utc)
    op.created_by_id = mock_user.id
    op.updated_by_id = None
    return op


# =============================================================================
# Conversion Function Tests
# =============================================================================


class TestWorkOrderConversion:
    """Test work order conversion functions."""

    def test_work_order_to_response(self, sample_work_order):
        """Test converting work order model to response."""
        response = work_order_to_response(sample_work_order)
        
        assert response.id == sample_work_order.id
        assert response.work_order_number == sample_work_order.work_order_number
        assert response.external_reference == sample_work_order.external_reference
        assert response.product_id == sample_work_order.product_id
        assert response.quantity_ordered == sample_work_order.quantity_ordered
        assert response.quantity_completed == sample_work_order.quantity_completed
        assert response.priority == "high"
        assert response.status == "in_progress"
        assert response.is_late == sample_work_order.is_late
        assert response.operation_count == 0

    def test_work_order_to_list_response(self, sample_work_order):
        """Test converting work order model to list response."""
        response = work_order_to_list_response(sample_work_order)
        
        assert response.id == sample_work_order.id
        assert response.work_order_number == sample_work_order.work_order_number
        assert response.priority == "high"
        assert response.status == "in_progress"
        assert response.is_late == sample_work_order.is_late

    def test_work_order_to_response_with_string_status(self, sample_work_order):
        """Test conversion when status/priority are already strings."""
        sample_work_order.status = "draft"
        sample_work_order.priority = "normal"
        sample_work_order.hold_reason = None
        
        response = work_order_to_response(sample_work_order)
        
        assert response.status == "draft"
        assert response.priority == "normal"

    def test_work_order_to_response_on_hold(self, sample_work_order, mock_user):
        """Test conversion for work order on hold."""
        sample_work_order.status = WorkOrderStatus.ON_HOLD
        sample_work_order.hold_reason = HoldReason.MATERIAL_SHORTAGE
        sample_work_order.hold_notes = "Waiting for materials"
        sample_work_order.held_at = datetime.now(timezone.utc)
        sample_work_order.held_by_id = mock_user.id
        sample_work_order.is_on_hold = True
        
        response = work_order_to_response(sample_work_order)
        
        assert response.status == "on_hold"
        assert response.hold_reason == "material_shortage"
        assert response.hold_notes == "Waiting for materials"
        assert response.is_on_hold is True


class TestOperationConversion:
    """Test operation conversion functions."""

    def test_operation_to_response(self, sample_operation):
        """Test converting operation model to response."""
        response = operation_to_response(sample_operation)
        
        assert response.id == sample_operation.id
        assert response.work_order_id == sample_operation.work_order_id
        assert response.sequence == sample_operation.sequence
        assert response.operation_name == sample_operation.operation_name
        assert response.status == "in_progress"
        assert response.is_active is True
        assert response.is_blocked is False

    def test_operation_to_response_with_string_status(self, sample_operation):
        """Test conversion when status is already a string."""
        sample_operation.status = "pending"
        
        response = operation_to_response(sample_operation)
        
        assert response.status == "pending"


# =============================================================================
# List Work Orders Tests
# =============================================================================


class TestListWorkOrders:
    """Test list_work_orders endpoint."""

    @pytest.mark.asyncio
    async def test_list_work_orders_empty(self, mock_db, mock_user):
        """Test listing work orders when none exist."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=0)),  # count
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # items
        ])
        
        response = await list_work_orders(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            priority=None,
            work_center_id=None,
            product_id=None,
            is_late=None,
            search=None,
            sort_by="created_at",
            sort_order="desc",
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data == []
        assert response.pagination.total_items == 0

    @pytest.mark.asyncio
    async def test_list_work_orders_with_items(self, mock_db, mock_user, sample_work_order):
        """Test listing work orders with items."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),  # count
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_work_order])))),  # items
        ])
        
        response = await list_work_orders(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            priority=None,
            work_center_id=None,
            product_id=None,
            is_late=None,
            search=None,
            sort_by="created_at",
            sort_order="desc",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.data) == 1
        assert response.data[0].work_order_number == sample_work_order.work_order_number

    @pytest.mark.asyncio
    async def test_list_work_orders_with_status_filter(self, mock_db, mock_user, sample_work_order):
        """Test listing work orders with status filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_work_order])))),
        ])
        
        response = await list_work_orders(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status="in_progress",
            priority=None,
            work_center_id=None,
            product_id=None,
            is_late=None,
            search=None,
            sort_by="created_at",
            sort_order="desc",
            include_deleted=False,
        )
        
        assert response.success is True
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_list_work_orders_with_priority_filter(self, mock_db, mock_user, sample_work_order):
        """Test listing work orders with priority filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_work_order])))),
        ])
        
        response = await list_work_orders(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            priority="high",
            work_center_id=None,
            product_id=None,
            is_late=None,
            search=None,
            sort_by="created_at",
            sort_order="desc",
            include_deleted=False,
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_list_work_orders_with_search(self, mock_db, mock_user, sample_work_order):
        """Test listing work orders with search."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_work_order])))),
        ])
        
        response = await list_work_orders(
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
            priority=None,
            work_center_id=None,
            product_id=None,
            is_late=None,
            search="WO-2024",
            sort_by="created_at",
            sort_order="desc",
            include_deleted=False,
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_list_work_orders_invalid_status(self, mock_db, mock_user):
        """Test listing work orders with invalid status."""
        from sensei.api.exceptions import BadRequestError
        
        with pytest.raises(BadRequestError):
            await list_work_orders(
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                status="invalid_status",
                priority=None,
                work_center_id=None,
                product_id=None,
                is_late=None,
                search=None,
                sort_by="created_at",
                sort_order="desc",
                include_deleted=False,
            )


# =============================================================================
# Create Work Order Tests
# =============================================================================


class TestCreateWorkOrder:
    """Test create_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_create_work_order_success(self, mock_db, mock_user):
        """Test successful work order creation."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)  # no duplicate
        ))
        
        # Use capture pattern for db.add
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            obj.id = 1
            # Set only non-property attributes
            obj.quantity_completed = Decimal("0")
            obj.quantity_scrapped = Decimal("0")
            obj.quantity_in_progress = Decimal("0")
            obj.operations = []
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.deleted_at = None
            obj.hold_reason = None
            obj.hold_notes = None
            obj.held_at = None
            obj.held_by_id = None
            obj.actual_start = None
            obj.actual_end = None
            obj.current_station_id = None
            obj.current_operation_sequence = None
        
        mock_db.add = MagicMock(side_effect=capture_add)
        
        data = WorkOrderCreate(
            work_order_number="WO-2024-0001",
            product_id=10,
            quantity_ordered=Decimal("100"),
            priority="high",
        )
        
        response = await create_work_order(
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data.work_order_number == "WO-2024-0001"
        assert response.message == "Work order created successfully"

    @pytest.mark.asyncio
    async def test_create_work_order_duplicate_number(self, mock_db, mock_user, sample_work_order):
        """Test creating work order with duplicate number."""
        from sensei.api.exceptions import ConflictError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        data = WorkOrderCreate(
            work_order_number="WO-2024-0001",
            product_id=10,
            quantity_ordered=Decimal("100"),
        )
        
        with pytest.raises(ConflictError):
            await create_work_order(
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Get Work Order Tests
# =============================================================================


class TestGetWorkOrder:
    """Test get_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_get_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test getting a work order by ID."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await get_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
            include_deleted=False,
        )
        
        assert response.success is True
        assert response.data.id == sample_work_order.id
        assert response.data.work_order_number == sample_work_order.work_order_number

    @pytest.mark.asyncio
    async def test_get_work_order_not_found(self, mock_db, mock_user):
        """Test getting non-existent work order."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await get_work_order(
                work_order_id=999,
                db=mock_db,
                current_user=mock_user,
                include_deleted=False,
            )


# =============================================================================
# Update Work Order Tests
# =============================================================================


class TestUpdateWorkOrder:
    """Test update_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_update_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test successful work order update."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_order)),  # get wo
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # no duplicate
        ])
        
        data = WorkOrderUpdate(
            priority="urgent",
            notes="Updated notes",
        )
        
        response = await update_work_order(
            work_order_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.message == "Work order updated successfully"

    @pytest.mark.asyncio
    async def test_update_work_order_not_found(self, mock_db, mock_user):
        """Test updating non-existent work order."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        data = WorkOrderUpdate(notes="Updated")
        
        with pytest.raises(NotFoundError):
            await update_work_order(
                work_order_id=999,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Delete Work Order Tests
# =============================================================================


class TestDeleteWorkOrder:
    """Test delete_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_work_order(self, mock_db, mock_user, sample_work_order):
        """Test soft deleting a work order."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await delete_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=False,
        )
        
        assert response.success is True
        assert response.message == "Work order deleted successfully"
        assert sample_work_order.deleted_at is not None

    @pytest.mark.asyncio
    async def test_hard_delete_work_order(self, mock_db, mock_user, sample_work_order):
        """Test hard deleting a work order."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        mock_db.delete = AsyncMock()
        
        response = await delete_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
            hard_delete=True,
        )
        
        assert response.success is True
        mock_db.delete.assert_called_once()


# =============================================================================
# Work Order Status Transition Tests
# =============================================================================


class TestReleaseWorkOrder:
    """Test release_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_release_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test releasing a work order from draft."""
        sample_work_order.status = WorkOrderStatus.DRAFT
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        data = WorkOrderRelease(
            scheduled_start=datetime.now(timezone.utc),
            scheduled_end=datetime.now(timezone.utc) + timedelta(days=3),
        )
        
        response = await release_work_order(
            work_order_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.RELEASED

    @pytest.mark.asyncio
    async def test_release_work_order_not_draft(self, mock_db, mock_user, sample_work_order):
        """Test releasing work order that is not in draft."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.IN_PROGRESS
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        data = WorkOrderRelease()
        
        with pytest.raises(BadRequestError):
            await release_work_order(
                work_order_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestStartWorkOrder:
    """Test start_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_start_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test starting a work order."""
        sample_work_order.status = WorkOrderStatus.RELEASED
        sample_work_order.can_start = MagicMock(return_value=True)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await start_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.IN_PROGRESS
        assert sample_work_order.actual_start is not None

    @pytest.mark.asyncio
    async def test_start_work_order_not_released(self, mock_db, mock_user, sample_work_order):
        """Test starting work order that is not released."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.DRAFT
        sample_work_order.can_start = MagicMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        with pytest.raises(BadRequestError):
            await start_work_order(
                work_order_id=1,
                db=mock_db,
                current_user=mock_user,
            )


class TestHoldWorkOrder:
    """Test hold_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_hold_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test putting a work order on hold."""
        sample_work_order.status = WorkOrderStatus.IN_PROGRESS
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        data = WorkOrderHold(
            reason="material_shortage",
            notes="Waiting for parts",
        )
        
        response = await hold_work_order(
            work_order_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.ON_HOLD
        assert sample_work_order.hold_reason == HoldReason.MATERIAL_SHORTAGE

    @pytest.mark.asyncio
    async def test_hold_completed_work_order(self, mock_db, mock_user, sample_work_order):
        """Test holding completed work order."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.COMPLETED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        data = WorkOrderHold(reason="other")
        
        with pytest.raises(BadRequestError):
            await hold_work_order(
                work_order_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestResumeWorkOrder:
    """Test resume_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_resume_work_order_to_in_progress(self, mock_db, mock_user, sample_work_order):
        """Test resuming a work order that was started before hold."""
        sample_work_order.status = WorkOrderStatus.ON_HOLD
        sample_work_order.actual_start = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await resume_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.IN_PROGRESS
        assert sample_work_order.hold_reason is None

    @pytest.mark.asyncio
    async def test_resume_work_order_to_released(self, mock_db, mock_user, sample_work_order):
        """Test resuming a work order that was not started."""
        sample_work_order.status = WorkOrderStatus.ON_HOLD
        sample_work_order.actual_start = None
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await resume_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert sample_work_order.status == WorkOrderStatus.RELEASED

    @pytest.mark.asyncio
    async def test_resume_not_on_hold(self, mock_db, mock_user, sample_work_order):
        """Test resuming work order that is not on hold."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.IN_PROGRESS
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        with pytest.raises(BadRequestError):
            await resume_work_order(
                work_order_id=1,
                db=mock_db,
                current_user=mock_user,
            )


class TestCompleteWorkOrder:
    """Test complete_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_complete_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test completing a work order."""
        sample_work_order.status = WorkOrderStatus.IN_PROGRESS
        sample_work_order.can_complete = MagicMock(return_value=True)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await complete_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.COMPLETED
        assert sample_work_order.actual_end is not None

    @pytest.mark.asyncio
    async def test_complete_work_order_cannot_complete(self, mock_db, mock_user, sample_work_order):
        """Test completing work order that cannot be completed."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.IN_PROGRESS
        sample_work_order.can_complete = MagicMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        with pytest.raises(BadRequestError):
            await complete_work_order(
                work_order_id=1,
                db=mock_db,
                current_user=mock_user,
            )


class TestCancelWorkOrder:
    """Test cancel_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test cancelling a work order."""
        sample_work_order.status = WorkOrderStatus.RELEASED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await cancel_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_completed_work_order(self, mock_db, mock_user, sample_work_order):
        """Test cancelling completed work order."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.COMPLETED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        with pytest.raises(BadRequestError):
            await cancel_work_order(
                work_order_id=1,
                db=mock_db,
                current_user=mock_user,
            )


class TestCloseWorkOrder:
    """Test close_work_order endpoint."""

    @pytest.mark.asyncio
    async def test_close_completed_work_order(self, mock_db, mock_user, sample_work_order):
        """Test closing a completed work order."""
        sample_work_order.status = WorkOrderStatus.COMPLETED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await close_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.status == WorkOrderStatus.CLOSED

    @pytest.mark.asyncio
    async def test_close_in_progress_work_order(self, mock_db, mock_user, sample_work_order):
        """Test closing work order that is in progress."""
        from sensei.api.exceptions import BadRequestError
        
        sample_work_order.status = WorkOrderStatus.IN_PROGRESS
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        with pytest.raises(BadRequestError):
            await close_work_order(
                work_order_id=1,
                db=mock_db,
                current_user=mock_user,
            )


# =============================================================================
# Work Order Operations Tests
# =============================================================================


class TestListOperations:
    """Test list_operations endpoint."""

    @pytest.mark.asyncio
    async def test_list_operations_empty(self, mock_db, mock_user, sample_work_order):
        """Test listing operations when none exist."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_order)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        ])
        
        response = await list_operations(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
        )
        
        assert response.success is True
        assert response.data == []

    @pytest.mark.asyncio
    async def test_list_operations_with_items(self, mock_db, mock_user, sample_work_order, sample_operation):
        """Test listing operations with items."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_order)),
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_operation])))),
        ])
        
        response = await list_operations(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status=None,
        )
        
        assert response.success is True
        assert len(response.data) == 1

    @pytest.mark.asyncio
    async def test_list_operations_work_order_not_found(self, mock_db, mock_user):
        """Test listing operations for non-existent work order."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await list_operations(
                work_order_id=999,
                db=mock_db,
                current_user=mock_user,
                page=1,
                page_size=20,
                status=None,
            )


class TestCreateOperation:
    """Test create_operation endpoint."""

    @pytest.mark.asyncio
    async def test_create_operation_success(self, mock_db, mock_user, sample_work_order):
        """Test successful operation creation."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_order)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # no duplicate
        ])
        
        added_object = None
        def capture_add(obj):
            nonlocal added_object
            added_object = obj
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)
            obj.quantity_completed = Decimal("0")
            obj.quantity_scrapped = Decimal("0")
            obj.started_at = None
            obj.completed_at = None
            obj.actual_time_seconds = None
            obj.actual_setup_seconds = None
            obj.operator_id = None
            obj.blocked_reason = None
            # Note: efficiency, elapsed_time_seconds, is_active, is_blocked are computed properties
        
        mock_db.add = MagicMock(side_effect=capture_add)
        
        data = OperationCreate(
            sequence=1,
            operation_name="Assembly Step 1",
            station_id=10,
        )
        
        response = await create_operation(
            work_order_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.message == "Operation created successfully"

    @pytest.mark.asyncio
    async def test_create_operation_duplicate_sequence(self, mock_db, mock_user, sample_work_order, sample_operation):
        """Test creating operation with duplicate sequence."""
        from sensei.api.exceptions import ConflictError
        
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_order)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_operation)),
        ])
        
        data = OperationCreate(
            sequence=1,
            operation_name="Duplicate",
            station_id=10,
        )
        
        with pytest.raises(ConflictError):
            await create_operation(
                work_order_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestStartOperation:
    """Test start_operation endpoint."""

    @pytest.mark.asyncio
    async def test_start_operation_success(self, mock_db, mock_user, sample_operation):
        """Test starting an operation."""
        sample_operation.status = OperationStatus.PENDING
        sample_operation.can_start = MagicMock(return_value=True)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        data = OperationStart(operator_id=str(mock_user.id))
        
        response = await start_operation(
            work_order_id=1,
            operation_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_operation.status == OperationStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_start_operation_cannot_start(self, mock_db, mock_user, sample_operation):
        """Test starting operation that cannot be started."""
        from sensei.api.exceptions import BadRequestError
        
        sample_operation.status = OperationStatus.IN_PROGRESS
        sample_operation.can_start = MagicMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        data = OperationStart()
        
        with pytest.raises(BadRequestError):
            await start_operation(
                work_order_id=1,
                operation_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )


class TestCompleteOperation:
    """Test complete_operation endpoint."""

    @pytest.mark.asyncio
    async def test_complete_operation_success(self, mock_db, mock_user, sample_operation):
        """Test completing an operation."""
        sample_operation.status = OperationStatus.IN_PROGRESS
        sample_operation.can_complete = MagicMock(return_value=True)
        sample_operation.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        data = OperationComplete(
            quantity_completed=Decimal("50"),
            quantity_scrapped=Decimal("2"),
        )
        
        response = await complete_operation(
            work_order_id=1,
            operation_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_operation.status == OperationStatus.COMPLETED


class TestBlockOperation:
    """Test block_operation endpoint."""

    @pytest.mark.asyncio
    async def test_block_operation_success(self, mock_db, mock_user, sample_operation):
        """Test blocking an operation."""
        sample_operation.status = OperationStatus.IN_PROGRESS
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        response = await block_operation(
            work_order_id=1,
            operation_id=1,
            db=mock_db,
            current_user=mock_user,
            reason="Equipment failure",
        )
        
        assert response.success is True
        assert sample_operation.status == OperationStatus.BLOCKED
        assert sample_operation.blocked_reason == "Equipment failure"


class TestUnblockOperation:
    """Test unblock_operation endpoint."""

    @pytest.mark.asyncio
    async def test_unblock_operation_to_in_progress(self, mock_db, mock_user, sample_operation):
        """Test unblocking operation that was in progress."""
        sample_operation.status = OperationStatus.BLOCKED
        sample_operation.started_at = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        response = await unblock_operation(
            work_order_id=1,
            operation_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_operation.status == OperationStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_unblock_operation_to_pending(self, mock_db, mock_user, sample_operation):
        """Test unblocking operation that was not started."""
        sample_operation.status = OperationStatus.BLOCKED
        sample_operation.started_at = None
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        response = await unblock_operation(
            work_order_id=1,
            operation_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert sample_operation.status == OperationStatus.PENDING


class TestSkipOperation:
    """Test skip_operation endpoint."""

    @pytest.mark.asyncio
    async def test_skip_operation_success(self, mock_db, mock_user, sample_operation):
        """Test skipping an operation."""
        sample_operation.status = OperationStatus.PENDING
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        response = await skip_operation(
            work_order_id=1,
            operation_id=1,
            db=mock_db,
            current_user=mock_user,
            reason="Not required for this batch",
        )
        
        assert response.success is True
        assert sample_operation.status == OperationStatus.SKIPPED


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestWorkOrderSchemaValidation:
    """Test work order schema validation."""

    def test_work_order_create_valid(self):
        """Test valid work order create schema."""
        data = WorkOrderCreate(
            work_order_number="WO-2024-0001",
            product_id=10,
            quantity_ordered=Decimal("100"),
            priority="high",
        )
        assert data.work_order_number == "WO-2024-0001"
        assert data.priority == "high"

    def test_work_order_create_invalid_priority(self):
        """Test work order create with invalid priority."""
        with pytest.raises(PydanticValidationError):
            WorkOrderCreate(
                work_order_number="WO-2024-0001",
                product_id=10,
                quantity_ordered=Decimal("100"),
                priority="invalid",
            )

    def test_work_order_create_invalid_status(self):
        """Test work order create with invalid status."""
        with pytest.raises(PydanticValidationError):
            WorkOrderCreate(
                work_order_number="WO-2024-0001",
                product_id=10,
                quantity_ordered=Decimal("100"),
                status="invalid",
            )

    def test_work_order_create_invalid_quantity(self):
        """Test work order create with invalid quantity."""
        with pytest.raises(PydanticValidationError):
            WorkOrderCreate(
                work_order_number="WO-2024-0001",
                product_id=10,
                quantity_ordered=Decimal("-10"),
            )

    def test_work_order_hold_valid(self):
        """Test valid work order hold schema."""
        data = WorkOrderHold(
            reason="material_shortage",
            notes="Waiting for parts",
        )
        assert data.reason == "material_shortage"

    def test_work_order_hold_invalid_reason(self):
        """Test work order hold with invalid reason."""
        with pytest.raises(PydanticValidationError):
            WorkOrderHold(reason="invalid_reason")


class TestOperationSchemaValidation:
    """Test operation schema validation."""

    def test_operation_create_valid(self):
        """Test valid operation create schema."""
        data = OperationCreate(
            sequence=1,
            operation_name="Assembly",
            station_id=10,
        )
        assert data.sequence == 1
        assert data.operation_name == "Assembly"

    def test_operation_create_invalid_sequence(self):
        """Test operation create with invalid sequence."""
        with pytest.raises(PydanticValidationError):
            OperationCreate(
                sequence=0,
                operation_name="Assembly",
                station_id=10,
            )

    def test_operation_update_invalid_status(self):
        """Test operation update with invalid status."""
        with pytest.raises(PydanticValidationError):
            OperationUpdate(status="invalid_status")


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_restore_work_order_success(self, mock_db, mock_user, sample_work_order):
        """Test restoring a soft-deleted work order."""
        sample_work_order.deleted_at = datetime.now(timezone.utc)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_work_order)
        ))
        
        response = await restore_work_order(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert sample_work_order.deleted_at is None

    @pytest.mark.asyncio
    async def test_restore_work_order_not_found(self, mock_db, mock_user):
        """Test restoring non-existent work order."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await restore_work_order(
                work_order_id=999,
                db=mock_db,
                current_user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_get_work_order_stats(self, mock_db, mock_user):
        """Test getting work order statistics."""
        # Setup mocks for stats query
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar=MagicMock(return_value=100)),  # total
            MagicMock(scalar=MagicMock(return_value=10)),  # draft
            MagicMock(scalar=MagicMock(return_value=20)),  # released
            MagicMock(scalar=MagicMock(return_value=30)),  # in_progress
            MagicMock(scalar=MagicMock(return_value=5)),   # on_hold
            MagicMock(scalar=MagicMock(return_value=25)),  # completed
            MagicMock(scalar=MagicMock(return_value=5)),   # cancelled
            MagicMock(scalar=MagicMock(return_value=5)),   # closed
            MagicMock(one=MagicMock(return_value=(Decimal("1000"), Decimal("500")))),  # quantities
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # late
        ])
        
        response = await get_work_order_stats(
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        assert response.data.total_work_orders == 100

    @pytest.mark.asyncio
    async def test_get_operation_not_found(self, mock_db, mock_user):
        """Test getting non-existent operation."""
        from sensei.api.exceptions import NotFoundError
        
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        with pytest.raises(NotFoundError):
            await get_operation(
                work_order_id=1,
                operation_id=999,
                db=mock_db,
                current_user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_update_operation_success(self, mock_db, mock_user, sample_operation):
        """Test updating an operation."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        data = OperationUpdate(
            operation_name="Updated Assembly",
            notes="Updated notes",
        )
        
        response = await update_operation(
            work_order_id=1,
            operation_id=1,
            data=data,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_delete_operation_success(self, mock_db, mock_user, sample_operation):
        """Test deleting an operation."""
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        mock_db.delete = AsyncMock()
        
        response = await delete_operation(
            work_order_id=1,
            operation_id=1,
            db=mock_db,
            current_user=mock_user,
        )
        
        assert response.success is True
        mock_db.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_work_order_with_operations_count(self, mock_db, mock_user, sample_work_order, sample_operation):
        """Test work order response includes operation count."""
        sample_work_order.operations = [sample_operation, sample_operation]
        
        response = work_order_to_response(sample_work_order)
        
        assert response.operation_count == 2

    def test_work_order_response_with_hold_info(self, sample_work_order, mock_user):
        """Test work order response with hold information."""
        sample_work_order.hold_reason = HoldReason.QUALITY_ISSUE
        sample_work_order.hold_notes = "Quality check failed"
        sample_work_order.held_at = datetime.now(timezone.utc)
        sample_work_order.held_by_id = mock_user.id
        
        response = work_order_to_response(sample_work_order)
        
        assert response.hold_reason == "quality_issue"
        assert response.hold_notes == "Quality check failed"
        assert response.held_by_id == str(mock_user.id)

    def test_operation_response_efficiency_calculation(self, sample_operation):
        """Test operation response with efficiency."""
        sample_operation.efficiency = Decimal("95.5")
        
        response = operation_to_response(sample_operation)
        
        assert response.efficiency == Decimal("95.5")

    @pytest.mark.asyncio
    async def test_list_operations_with_status_filter(self, mock_db, mock_user, sample_work_order, sample_operation):
        """Test listing operations with status filter."""
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_work_order)),
            MagicMock(scalar=MagicMock(return_value=1)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[sample_operation])))),
        ])
        
        response = await list_operations(
            work_order_id=1,
            db=mock_db,
            current_user=mock_user,
            page=1,
            page_size=20,
            status="in_progress",
        )
        
        assert response.success is True

    @pytest.mark.asyncio
    async def test_block_completed_operation_fails(self, mock_db, mock_user, sample_operation):
        """Test blocking a completed operation fails."""
        from sensei.api.exceptions import BadRequestError
        
        sample_operation.status = OperationStatus.COMPLETED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        with pytest.raises(BadRequestError):
            await block_operation(
                work_order_id=1,
                operation_id=1,
                db=mock_db,
                current_user=mock_user,
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_skip_completed_operation_fails(self, mock_db, mock_user, sample_operation):
        """Test skipping a completed operation fails."""
        from sensei.api.exceptions import BadRequestError
        
        sample_operation.status = OperationStatus.COMPLETED
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        with pytest.raises(BadRequestError):
            await skip_operation(
                work_order_id=1,
                operation_id=1,
                db=mock_db,
                current_user=mock_user,
                reason="Test",
            )

    @pytest.mark.asyncio
    async def test_unblock_not_blocked_operation_fails(self, mock_db, mock_user, sample_operation):
        """Test unblocking operation that is not blocked fails."""
        from sensei.api.exceptions import BadRequestError
        
        sample_operation.status = OperationStatus.IN_PROGRESS
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        with pytest.raises(BadRequestError):
            await unblock_operation(
                work_order_id=1,
                operation_id=1,
                db=mock_db,
                current_user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_complete_operation_without_start(self, mock_db, mock_user, sample_operation):
        """Test completing operation that was not started fails."""
        from sensei.api.exceptions import BadRequestError
        
        sample_operation.status = OperationStatus.PENDING
        sample_operation.can_complete = MagicMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=sample_operation)
        ))
        
        data = OperationComplete(quantity_completed=Decimal("10"))
        
        with pytest.raises(BadRequestError):
            await complete_operation(
                work_order_id=1,
                operation_id=1,
                data=data,
                db=mock_db,
                current_user=mock_user,
            )

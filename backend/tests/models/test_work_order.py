"""
Tests for Work Order models.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from sensei.models.work_order import (
    WorkOrder,
    WorkOrderStatus,
    WorkOrderPriority,
    HoldReason,
    WorkOrderOperation,
    OperationStatus,
)


class TestWorkOrderModel:
    """Test cases for WorkOrder model."""

    def test_work_order_creation_basic(self):
        """Test basic work order creation."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("0"),
            quantity_scrapped=Decimal("0"),
            status=WorkOrderStatus.DRAFT,
            priority=WorkOrderPriority.NORMAL,
        )

        assert work_order.work_order_number == "WO-001"
        assert work_order.product_id == 1
        assert work_order.quantity_ordered == Decimal("100.0000")
        assert work_order.quantity_completed == Decimal("0")
        assert work_order.quantity_scrapped == Decimal("0")
        assert work_order.status == WorkOrderStatus.DRAFT
        assert work_order.priority == WorkOrderPriority.NORMAL

    def test_work_order_creation_full(self):
        """Test work order creation with all fields."""
        scheduled_start = datetime.now(timezone.utc).replace(tzinfo=None)
        scheduled_end = scheduled_start + timedelta(days=5)

        work_order = WorkOrder(
            work_order_number="WO-002",
            external_reference="PO-12345",
            product_id=1,
            quantity_ordered=Decimal("500.0000"),
            quantity_completed=Decimal("100.0000"),
            quantity_scrapped=Decimal("5.0000"),
            quantity_in_progress=Decimal("50.0000"),
            priority=WorkOrderPriority.HIGH,
            status=WorkOrderStatus.IN_PROGRESS,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            lot_number="LOT-2024-001",
            notes="Rush order",
            work_center_id=1,
        )

        assert work_order.external_reference == "PO-12345"
        assert work_order.quantity_ordered == Decimal("500.0000")
        assert work_order.quantity_completed == Decimal("100.0000")
        assert work_order.priority == WorkOrderPriority.HIGH
        assert work_order.status == WorkOrderStatus.IN_PROGRESS
        assert work_order.lot_number == "LOT-2024-001"

    def test_work_order_status_values(self):
        """Test all valid work order status values."""
        for status in WorkOrderStatus:
            work_order = WorkOrder(
                work_order_number=f"WO-{status.value}",
                product_id=1,
                quantity_ordered=Decimal("10.0000"),
                status=status,
            )
            assert work_order.status == status

    def test_work_order_priority_values(self):
        """Test all valid priority values."""
        for priority in WorkOrderPriority:
            work_order = WorkOrder(
                work_order_number=f"WO-{priority.value}",
                product_id=1,
                quantity_ordered=Decimal("10.0000"),
                priority=priority,
            )
            assert work_order.priority == priority

    def test_work_order_quantity_remaining(self):
        """Test quantity remaining calculation."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("60.0000"),
            quantity_scrapped=Decimal("5.0000"),
        )

        expected = Decimal("100.0000") - Decimal("60.0000") - Decimal("5.0000")
        assert work_order.quantity_remaining == expected

    def test_work_order_completion_percentage(self):
        """Test completion percentage calculation."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("75.0000"),
        )

        assert work_order.completion_percentage == Decimal("75")

    def test_work_order_completion_percentage_zero(self):
        """Test completion percentage with zero ordered."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("0"),
        )

        assert work_order.completion_percentage == Decimal("0")

    def test_work_order_yield_percentage(self):
        """Test yield percentage calculation."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("90.0000"),
            quantity_scrapped=Decimal("10.0000"),
        )

        # Yield = 90 / (90 + 10) * 100 = 90%
        assert work_order.yield_percentage == Decimal("90")

    def test_work_order_yield_percentage_no_production(self):
        """Test yield percentage with no production."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("0"),
            quantity_scrapped=Decimal("0"),
        )

        assert work_order.yield_percentage == Decimal("100")

    def test_work_order_is_late(self):
        """Test late detection."""
        past_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)

        work_order_late = WorkOrder(
            work_order_number="WO-LATE",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.IN_PROGRESS,
            scheduled_end=past_date,
        )

        work_order_complete = WorkOrder(
            work_order_number="WO-COMPLETE",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.COMPLETED,
            scheduled_end=past_date,
        )

        assert work_order_late.is_late is True
        assert work_order_complete.is_late is False

    def test_work_order_is_on_hold(self):
        """Test on hold detection."""
        work_order_hold = WorkOrder(
            work_order_number="WO-HOLD",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.ON_HOLD,
            hold_reason=HoldReason.MATERIAL_SHORTAGE,
        )

        work_order_active = WorkOrder(
            work_order_number="WO-ACTIVE",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.IN_PROGRESS,
        )

        assert work_order_hold.is_on_hold is True
        assert work_order_active.is_on_hold is False

    def test_work_order_can_start(self):
        """Test can_start logic."""
        work_order_draft = WorkOrder(
            work_order_number="WO-DRAFT",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.DRAFT,
        )

        work_order_released = WorkOrder(
            work_order_number="WO-RELEASED",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.RELEASED,
        )

        assert work_order_draft.can_start() is False
        assert work_order_released.can_start() is True

    def test_work_order_hold_reason_values(self):
        """Test all valid hold reason values."""
        for reason in HoldReason:
            work_order = WorkOrder(
                work_order_number=f"WO-{reason.value}",
                product_id=1,
                quantity_ordered=Decimal("10.0000"),
                status=WorkOrderStatus.ON_HOLD,
                hold_reason=reason,
            )
            assert work_order.hold_reason == reason

    def test_work_order_repr(self):
        """Test string representation."""
        work_order = WorkOrder(
            work_order_number="WO-TEST",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            status=WorkOrderStatus.IN_PROGRESS,
        )
        work_order.id = 1

        assert "WorkOrder" in repr(work_order)
        assert "WO-TEST" in repr(work_order)


class TestWorkOrderOperationModel:
    """Test cases for WorkOrderOperation model."""

    def test_operation_creation_basic(self):
        """Test basic operation creation."""
        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Assembly",
            station_id=1,
            status=OperationStatus.PENDING,
            quantity_completed=Decimal("0"),
        )

        assert operation.work_order_id == 1
        assert operation.sequence == 10
        assert operation.operation_name == "Assembly"
        assert operation.station_id == 1
        assert operation.status == OperationStatus.PENDING
        assert operation.quantity_completed == Decimal("0")

    def test_operation_creation_full(self):
        """Test operation creation with all fields."""
        started = datetime.now(timezone.utc).replace(tzinfo=None)
        completed = started + timedelta(hours=2)

        operation = WorkOrderOperation(
            work_order_id=1,
            routing_id=5,
            sequence=20,
            operation_name="Machining",
            station_id=2,
            standard_time_seconds=180,
            setup_time_seconds=600,
            status=OperationStatus.COMPLETED,
            quantity_completed=Decimal("50.0000"),
            quantity_scrapped=Decimal("2.0000"),
            started_at=started,
            completed_at=completed,
            actual_time_seconds=7200,
            actual_setup_seconds=900,
            operator_id=10,
            notes="Completed ahead of schedule",
        )

        assert operation.routing_id == 5
        assert operation.standard_time_seconds == 180
        assert operation.actual_time_seconds == 7200
        assert operation.operator_id == 10

    def test_operation_status_values(self):
        """Test all valid operation status values."""
        for status in OperationStatus:
            operation = WorkOrderOperation(
                work_order_id=1,
                sequence=10,
                operation_name=f"Op {status.value}",
                station_id=1,
                status=status,
            )
            assert operation.status == status

    def test_operation_efficiency(self):
        """Test efficiency calculation."""
        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            standard_time_seconds=100,
            actual_time_seconds=80,
        )

        # Efficiency = standard / actual * 100 = 100/80 * 100 = 125%
        assert operation.efficiency == Decimal("125")

    def test_operation_efficiency_no_actual(self):
        """Test efficiency with no actual time."""
        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            standard_time_seconds=100,
            actual_time_seconds=None,
        )

        assert operation.efficiency is None

    def test_operation_is_active(self):
        """Test is_active property."""
        operation_active = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Active Op",
            station_id=1,
            status=OperationStatus.IN_PROGRESS,
        )

        operation_pending = WorkOrderOperation(
            work_order_id=1,
            sequence=20,
            operation_name="Pending Op",
            station_id=1,
            status=OperationStatus.PENDING,
        )

        assert operation_active.is_active is True
        assert operation_pending.is_active is False

    def test_operation_is_blocked(self):
        """Test is_blocked property."""
        operation_blocked = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Blocked Op",
            station_id=1,
            status=OperationStatus.BLOCKED,
            blocked_reason="Material shortage",
        )

        assert operation_blocked.is_blocked is True
        assert operation_blocked.blocked_reason == "Material shortage"

    def test_operation_can_start(self):
        """Test can_start logic."""
        operation_pending = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Pending Op",
            station_id=1,
            status=OperationStatus.PENDING,
        )

        operation_active = WorkOrderOperation(
            work_order_id=1,
            sequence=20,
            operation_name="Active Op",
            station_id=1,
            status=OperationStatus.IN_PROGRESS,
        )

        assert operation_pending.can_start() is True
        assert operation_active.can_start() is False

    def test_operation_can_complete(self):
        """Test can_complete logic."""
        operation_active = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Active Op",
            station_id=1,
            status=OperationStatus.IN_PROGRESS,
        )

        operation_pending = WorkOrderOperation(
            work_order_id=1,
            sequence=20,
            operation_name="Pending Op",
            station_id=1,
            status=OperationStatus.PENDING,
        )

        assert operation_active.can_complete() is True
        assert operation_pending.can_complete() is False

    def test_operation_repr(self):
        """Test string representation."""
        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            status=OperationStatus.IN_PROGRESS,
        )

        assert "WorkOrderOperation" in repr(operation)
        assert "10" in repr(operation)


class TestWorkOrderOperationRelationship:
    """Test Work Order - Operation relationships."""

    def test_work_order_has_operations_list(self):
        """Test that work order has operations list."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
        )
        assert hasattr(work_order, 'operations')

    def test_operation_references_work_order(self):
        """Test that operation references work order."""
        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
        )
        assert operation.work_order_id == 1
        assert hasattr(operation, 'work_order')


class TestWorkOrderValidation:
    """Test Work Order validation constraints."""

    def test_work_order_explicit_quantities(self):
        """Test explicit quantity values."""
        work_order = WorkOrder(
            work_order_number="WO-001",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("0"),
            quantity_scrapped=Decimal("0"),
            quantity_in_progress=Decimal("0"),
        )

        assert work_order.quantity_completed == Decimal("0")
        assert work_order.quantity_scrapped == Decimal("0")
        assert work_order.quantity_in_progress == Decimal("0")


class TestWorkOrderEdgeCases:
    """Test edge cases for Work Order model."""

    def test_work_order_all_scrapped(self):
        """Test work order with all quantity scrapped."""
        work_order = WorkOrder(
            work_order_number="WO-SCRAP",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("0"),
            quantity_scrapped=Decimal("100.0000"),
        )

        assert work_order.quantity_remaining == Decimal("0")
        assert work_order.yield_percentage == Decimal("0")

    def test_work_order_partial_completion(self):
        """Test work order with partial completion."""
        work_order = WorkOrder(
            work_order_number="WO-PARTIAL",
            product_id=1,
            quantity_ordered=Decimal("100.0000"),
            quantity_completed=Decimal("50.0000"),
            quantity_scrapped=Decimal("0"),
        )

        assert work_order.quantity_remaining == Decimal("50.0000")
        assert work_order.completion_percentage == Decimal("50")

    def test_operation_elapsed_time(self):
        """Test operation elapsed time calculation."""
        started = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Active Op",
            station_id=1,
            status=OperationStatus.IN_PROGRESS,
            started_at=started,
        )

        elapsed = operation.elapsed_time_seconds
        assert elapsed is not None
        assert elapsed >= 3600  # At least 1 hour

    def test_operation_elapsed_time_completed(self):
        """Test elapsed time for completed operation."""
        started = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        completed = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

        operation = WorkOrderOperation(
            work_order_id=1,
            sequence=10,
            operation_name="Complete Op",
            station_id=1,
            status=OperationStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
        )

        elapsed = operation.elapsed_time_seconds
        assert elapsed is not None
        assert 3500 <= elapsed <= 3700  # About 1 hour

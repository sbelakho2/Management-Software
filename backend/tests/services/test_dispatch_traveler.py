"""Tests for Dispatching & Electronic Traveler Service (Development Plan 22.7)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest

from sensei.services.dispatch_traveler import (
    DispatchTravelerService,
    OperationStatus,
    CheckpointType,
    CheckpointResult,
    DispatchPriority,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> DispatchTravelerService:
    return DispatchTravelerService()


@pytest.fixture
def ops_roles() -> set[str]:
    return {"ops"}


@pytest.fixture
def operator_roles() -> set[str]:
    return {"operator"}


@pytest.fixture
def reader_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def norole() -> set[str]:
    return {"guest"}


@pytest.fixture
def route_id(svc: DispatchTravelerService, ops_roles: set[str]) -> tuple:
    """Create a route with operations and return (route_id, operation_ids)."""
    route_id = svc.define_route(
        actor_id="planner1",
        actor_roles=ops_roles,
        correlation_id="setup-1",
        operations=[
            {
                "station_id": "STATION-A",
                "operation_code": "OP-010",
                "description": "Assembly",
                "estimated_time_minutes": 30,
                "required_skills": ["welding"],
            },
            {
                "station_id": "STATION-B",
                "operation_code": "OP-020",
                "description": "Inspection",
                "estimated_time_minutes": 15,
            },
        ],
    )
    return route_id


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_define_route_requires_write_role(
        self, svc: DispatchTravelerService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="MES write role required"):
            svc.define_route(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                operations=[{"station_id": "A", "operation_code": "OP-1"}],
            )

    def test_create_traveler_requires_write_role(
        self, svc: DispatchTravelerService, norole: set[str], route_id, ops_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="MES write role required"):
            svc.create_traveler(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                work_order_id="WO-001",
                product_id="PROD-001",
                lot_number="LOT-001",
                route_id=route_id,
                quantity=10,
            )

    def test_start_operation_requires_operator_role(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id, reader_roles: set[str]
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        with pytest.raises(PermissionError, match="Operator role required"):
            svc.start_operation(
                actor_id="auditor1",
                actor_roles=reader_roles,
                correlation_id="cor-2",
                traveler_operation_id=ops[0].id,
            )

    def test_reader_can_view_dispatch_queue(
        self, svc: DispatchTravelerService, reader_roles: set[str]
    ) -> None:
        queue = svc.get_dispatch_queue(actor_roles=reader_roles)
        assert isinstance(queue, list)


# ============================================================
# Route Definition Tests
# ============================================================


class TestRouteDefinition:
    def test_define_route_basic(
        self, svc: DispatchTravelerService, ops_roles: set[str]
    ) -> None:
        route_id = svc.define_route(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            operations=[
                {
                    "station_id": "STATION-A",
                    "operation_code": "OP-010",
                    "description": "First op",
                    "estimated_time_minutes": 30,
                },
                {
                    "station_id": "STATION-B",
                    "operation_code": "OP-020",
                    "description": "Second op",
                    "estimated_time_minutes": 20,
                },
            ],
        )

        assert route_id is not None

    def test_define_route_empty_fails(
        self, svc: DispatchTravelerService, ops_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="At least one operation required"):
            svc.define_route(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id="cor-1",
                operations=[],
            )

    def test_add_checkpoint_to_operation(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        # Get an operation ID (we need to create traveler to get op IDs)
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        checkpoint = svc.add_checkpoint(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            operation_id=ops[0].operation_id,
            checkpoint_type=CheckpointType.CTQ,
            name="Dimension Check",
            specification="10.0mm ± 0.1mm",
            lower_limit=9.9,
            upper_limit=10.1,
            unit="mm",
        )

        assert checkpoint.name == "Dimension Check"
        assert checkpoint.checkpoint_type == CheckpointType.CTQ
        assert checkpoint.lower_limit == 9.9
        assert checkpoint.upper_limit == 10.1


# ============================================================
# Traveler Tests
# ============================================================


class TestTraveler:
    def test_create_traveler_basic(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
            serial_number="SN-12345",
        )

        assert traveler.work_order_id == "WO-001"
        assert traveler.lot_number == "LOT-001"
        assert traveler.quantity == 10
        assert traveler.serial_number == "SN-12345"

    def test_create_traveler_with_genealogy(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-002",
            product_id="PROD-001",
            lot_number="LOT-002",
            route_id=route_id,
            quantity=5,
            genealogy=["LOT-001", "LOT-000"],
        )

        assert len(traveler.genealogy) == 2
        assert "LOT-001" in traveler.genealogy

    def test_create_traveler_invalid_route_fails(
        self, svc: DispatchTravelerService, ops_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="route_id not found"):
            svc.create_traveler(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id="cor-1",
                work_order_id="WO-001",
                product_id="PROD-001",
                lot_number="LOT-001",
                route_id=uuid4(),  # Non-existent
                quantity=10,
            )

    def test_traveler_creates_operations(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )

        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)
        assert len(ops) == 2
        assert ops[0].sequence == 1
        assert ops[1].sequence == 2
        assert all(op.status == OperationStatus.PENDING for op in ops)


# ============================================================
# Operation Execution Tests
# ============================================================


class TestOperationExecution:
    def test_start_operation(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        started = svc.start_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-2",
            traveler_operation_id=ops[0].id,
        )

        assert started.status == OperationStatus.IN_PROGRESS
        assert started.operator_id == "operator1"
        assert started.started_at is not None

    def test_cannot_start_out_of_sequence(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        # Try to start second op before first
        with pytest.raises(ValueError, match="Previous operations must be completed"):
            svc.start_operation(
                actor_id="operator1",
                actor_roles=operator_roles,
                correlation_id="cor-2",
                traveler_operation_id=ops[1].id,
            )

    def test_complete_operation(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        svc.start_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-2",
            traveler_operation_id=ops[0].id,
        )

        completed = svc.complete_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-3",
            traveler_operation_id=ops[0].id,
            quantity_completed=9,
            quantity_scrapped=1,
            notes="Minor defect found",
        )

        assert completed.status == OperationStatus.COMPLETED
        assert completed.quantity_completed == 9
        assert completed.quantity_scrapped == 1
        assert completed.completed_at is not None

    def test_cannot_complete_without_start(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        with pytest.raises(ValueError, match="must be in progress"):
            svc.complete_operation(
                actor_id="operator1",
                actor_roles=operator_roles,
                correlation_id="cor-2",
                traveler_operation_id=ops[0].id,
                quantity_completed=10,
            )


# ============================================================
# Checkpoint Tests
# ============================================================


class TestCheckpoints:
    def test_record_checkpoint_pass(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        checkpoint = svc.add_checkpoint(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            operation_id=ops[0].operation_id,
            checkpoint_type=CheckpointType.MEASUREMENT,
            name="Length Check",
            specification="100mm ± 1mm",
            lower_limit=99.0,
            upper_limit=101.0,
            unit="mm",
        )

        record = svc.record_checkpoint(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-3",
            checkpoint_id=checkpoint.id,
            traveler_id=traveler.id,
            result=CheckpointResult.PASS,
            measured_value=100.2,
        )

        assert record.result == CheckpointResult.PASS
        assert record.measured_value == 100.2

    def test_record_checkpoint_validates_limits(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        checkpoint = svc.add_checkpoint(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            operation_id=ops[0].operation_id,
            checkpoint_type=CheckpointType.MEASUREMENT,
            name="Width Check",
            specification="50mm ± 0.5mm",
            lower_limit=49.5,
            upper_limit=50.5,
            unit="mm",
        )

        # Cannot mark PASS if out of spec
        with pytest.raises(ValueError, match="above upper limit"):
            svc.record_checkpoint(
                actor_id="operator1",
                actor_roles=operator_roles,
                correlation_id="cor-3",
                checkpoint_id=checkpoint.id,
                traveler_id=traveler.id,
                result=CheckpointResult.PASS,
                measured_value=51.0,  # Out of spec
            )

    def test_mandatory_checkpoint_blocks_completion(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        svc.add_checkpoint(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            operation_id=ops[0].operation_id,
            checkpoint_type=CheckpointType.CTQ,
            name="Critical Check",
            specification="Required",
            is_mandatory=True,
        )

        svc.start_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-3",
            traveler_operation_id=ops[0].id,
        )

        # Cannot complete without passing mandatory checkpoint
        with pytest.raises(ValueError, match="Mandatory checkpoint"):
            svc.complete_operation(
                actor_id="operator1",
                actor_roles=operator_roles,
                correlation_id="cor-4",
                traveler_operation_id=ops[0].id,
                quantity_completed=10,
            )


# ============================================================
# Dispatching Tests
# ============================================================


class TestDispatching:
    def test_queue_for_dispatch(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        dispatch = svc.queue_for_dispatch(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            traveler_operation_id=ops[0].id,
            priority=DispatchPriority.HIGH,
        )

        assert dispatch.station_id == "STATION-A"
        assert dispatch.priority == DispatchPriority.HIGH
        assert dispatch.work_order_id == "WO-001"

        # Operation status should be QUEUED
        updated_ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)
        assert updated_ops[0].status == OperationStatus.QUEUED

    def test_get_dispatch_queue_by_station(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        # Create two travelers
        for i in range(2):
            traveler = svc.create_traveler(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id=f"cor-{i}",
                work_order_id=f"WO-00{i+1}",
                product_id="PROD-001",
                lot_number=f"LOT-00{i+1}",
                route_id=route_id,
                quantity=10,
            )
            ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)
            svc.queue_for_dispatch(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id=f"cor-q{i}",
                traveler_operation_id=ops[0].id,
            )

        queue = svc.get_dispatch_queue(actor_roles=ops_roles, station_id="STATION-A")
        assert len(queue) == 2

    def test_dispatch_queue_sorted_by_priority(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        priorities = [DispatchPriority.LOW, DispatchPriority.URGENT, DispatchPriority.NORMAL]

        for i, priority in enumerate(priorities):
            traveler = svc.create_traveler(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id=f"cor-{i}",
                work_order_id=f"WO-00{i+1}",
                product_id="PROD-001",
                lot_number=f"LOT-00{i+1}",
                route_id=route_id,
                quantity=10,
            )
            ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)
            svc.queue_for_dispatch(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id=f"cor-q{i}",
                traveler_operation_id=ops[0].id,
                priority=priority,
            )

        queue = svc.get_dispatch_queue(actor_roles=ops_roles)

        # URGENT should be first
        assert queue[0].priority == DispatchPriority.URGENT
        assert queue[1].priority == DispatchPriority.NORMAL
        assert queue[2].priority == DispatchPriority.LOW

    def test_start_removes_from_queue(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        svc.queue_for_dispatch(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            traveler_operation_id=ops[0].id,
        )

        assert len(svc.get_dispatch_queue(actor_roles=ops_roles)) == 1

        svc.start_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-3",
            traveler_operation_id=ops[0].id,
        )

        assert len(svc.get_dispatch_queue(actor_roles=ops_roles)) == 0


# ============================================================
# Genealogy Tests
# ============================================================


class TestGenealogy:
    def test_get_genealogy(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-002",
            product_id="PROD-001",
            lot_number="LOT-002",
            route_id=route_id,
            quantity=5,
            serial_number="SN-100",
            genealogy=["LOT-001", "LOT-000"],
        )

        genealogy = svc.get_genealogy(actor_roles=ops_roles, traveler_id=traveler.id)

        assert genealogy["lot_number"] == "LOT-002"
        assert genealogy["serial_number"] == "SN-100"
        assert "LOT-001" in genealogy["parent_lots"]
        assert "LOT-000" in genealogy["parent_lots"]


# ============================================================
# Audit Tests
# ============================================================


class TestAudit:
    def test_audit_trail_for_operations(
        self, svc: DispatchTravelerService, ops_roles: set[str], operator_roles: set[str], route_id
    ) -> None:
        traveler = svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )
        ops = svc.get_traveler_operations(actor_roles=ops_roles, traveler_id=traveler.id)

        svc.start_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-2",
            traveler_operation_id=ops[0].id,
        )

        svc.complete_operation(
            actor_id="operator1",
            actor_roles=operator_roles,
            correlation_id="cor-3",
            traveler_operation_id=ops[0].id,
            quantity_completed=10,
        )

        events = svc.list_audit_events(actor_roles=ops_roles)

        actions = [e.action for e in events]
        assert "dispatch.route.define" in actions
        assert "dispatch.traveler.create" in actions
        assert "dispatch.operation.start" in actions
        assert "dispatch.operation.complete" in actions

    def test_audit_includes_correlation_id(
        self, svc: DispatchTravelerService, ops_roles: set[str], route_id
    ) -> None:
        svc.create_traveler(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="trace-travel123",
            work_order_id="WO-001",
            product_id="PROD-001",
            lot_number="LOT-001",
            route_id=route_id,
            quantity=10,
        )

        events = svc.list_audit_events(actor_roles=ops_roles)

        assert any(e.correlation_id == "trace-travel123" for e in events)

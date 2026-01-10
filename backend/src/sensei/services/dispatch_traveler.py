"""Dispatching & Electronic Traveler Service (Development Plan 22.7).

Implements:
- Dispatching / Operator Queue: station-level dispatch list with constraints
  (skills, tools, materials).
- Electronic Traveler / Route Card: operation-by-operation sign-off, CTQ
  checkpoints, and genealogy binding.

This module is in-memory and pure-Python to match other services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Protocol
from uuid import UUID, uuid4


class OperationStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    SKIPPED = "skipped"


class CheckpointType(str, Enum):
    CTQ = "ctq"  # Critical to Quality
    INSPECTION = "inspection"
    SIGN_OFF = "sign_off"
    MEASUREMENT = "measurement"
    VERIFICATION = "verification"


class CheckpointResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"
    PENDING = "pending"


class DispatchPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# RBAC
_MES_WRITE_ROLES: set[str] = {"admin", "ops", "supervisor", "ceo", "gm"}
_MES_READ_ROLES: set[str] = {"admin", "ops", "supervisor", "ceo", "gm", "quality", "auditor", "operator"}
_OPERATOR_ROLES: set[str] = {"admin", "ops", "supervisor", "operator", "team_lead"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Traveler / Route Card Models
# ============================================================


@dataclass(frozen=True)
class RouteOperation:
    """A single operation in a route card."""

    id: UUID
    sequence: int
    station_id: str
    operation_code: str
    description: str
    estimated_time_minutes: int
    required_skills: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    required_materials: tuple[tuple[str, float], ...] = ()  # (material_id, qty)
    checkpoints: tuple[str, ...] = ()  # Checkpoint IDs


@dataclass(frozen=True)
class Checkpoint:
    """A CTQ or inspection checkpoint."""

    id: UUID
    operation_id: UUID
    checkpoint_type: CheckpointType
    name: str
    specification: str
    lower_limit: float | None = None
    upper_limit: float | None = None
    unit: str = ""
    is_mandatory: bool = True


@dataclass(frozen=True)
class CheckpointRecord:
    """Recorded result of a checkpoint."""

    id: UUID
    checkpoint_id: UUID
    traveler_id: UUID
    operation_id: UUID
    result: CheckpointResult
    measured_value: float | None = None
    notes: str = ""
    recorded_by: str = ""
    recorded_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class Traveler:
    """Electronic traveler tracking a work order through operations."""

    id: UUID
    work_order_id: str
    product_id: str
    lot_number: str
    serial_number: str | None
    quantity: int
    route_id: UUID
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    genealogy: tuple[str, ...] = ()  # Parent lot/serial numbers


@dataclass(frozen=True)
class TravelerOperation:
    """Status of an operation within a traveler."""

    id: UUID
    traveler_id: UUID
    operation_id: UUID
    sequence: int
    status: OperationStatus
    station_id: str
    operator_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    quantity_completed: int = 0
    quantity_scrapped: int = 0
    notes: str = ""


# ============================================================
# Dispatching Models
# ============================================================


@dataclass(frozen=True)
class DispatchItem:
    """An item in the dispatch queue."""

    id: UUID
    traveler_operation_id: UUID
    station_id: str
    priority: DispatchPriority
    work_order_id: str
    operation_code: str
    product_id: str
    quantity: int
    due_at: datetime | None = None
    estimated_time_minutes: int = 0
    required_skills: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    materials_ready: bool = True
    tools_ready: bool = True
    skills_available: bool = True
    queued_at: datetime = field(default_factory=_utcnow)


# ============================================================
# Provider Protocols
# ============================================================


class MaterialsProvider(Protocol):
    def check_materials_available(
        self, materials: list[tuple[str, float]]
    ) -> bool: ...


class ToolsProvider(Protocol):
    def check_tools_available(self, tool_ids: list[str]) -> bool: ...


class SkillsProvider(Protocol):
    def check_operator_skills(
        self, operator_id: str, required_skills: list[str]
    ) -> bool: ...


# ============================================================
# Service
# ============================================================


class DispatchTravelerService:
    """In-memory dispatching and electronic traveler service."""

    def __init__(
        self,
        *,
        materials_provider: MaterialsProvider | None = None,
        tools_provider: ToolsProvider | None = None,
        skills_provider: SkillsProvider | None = None,
    ) -> None:
        # Route definitions
        self._routes: dict[UUID, list[RouteOperation]] = {}
        self._checkpoints: dict[UUID, Checkpoint] = {}

        # Travelers
        self._travelers: dict[UUID, Traveler] = {}
        self._traveler_operations: dict[UUID, TravelerOperation] = {}
        self._checkpoint_records: dict[UUID, CheckpointRecord] = {}

        # Dispatch queue
        self._dispatch_queue: dict[UUID, DispatchItem] = {}

        # Providers
        self._materials_provider = materials_provider
        self._tools_provider = tools_provider
        self._skills_provider = skills_provider

        self._audit: list[AuditEvent] = []

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ev = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(ev)

    # ----------------------------------------------------------------
    # Audit API
    # ----------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")
        return list(self._audit)

    # ----------------------------------------------------------------
    # Route Definition
    # ----------------------------------------------------------------

    def define_route(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        operations: list[dict[str, Any]],
    ) -> UUID:
        """Define a route (sequence of operations) for a product."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write role required")

        if not operations:
            raise ValueError("At least one operation required")

        route_id = uuid4()
        route_ops = []

        for seq, op_data in enumerate(operations, start=1):
            op = RouteOperation(
                id=uuid4(),
                sequence=seq,
                station_id=op_data.get("station_id", ""),
                operation_code=op_data.get("operation_code", ""),
                description=op_data.get("description", ""),
                estimated_time_minutes=op_data.get("estimated_time_minutes", 0),
                required_skills=tuple(op_data.get("required_skills", [])),
                required_tools=tuple(op_data.get("required_tools", [])),
                required_materials=tuple(
                    (m[0], m[1]) for m in op_data.get("required_materials", [])
                ),
            )
            route_ops.append(op)

        self._routes[route_id] = route_ops

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.route.define",
            entity_type="route",
            entity_id=str(route_id),
            correlation_id=correlation_id,
            metadata={"operation_count": len(operations)},
        )

        return route_id

    def add_checkpoint(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        operation_id: UUID,
        checkpoint_type: CheckpointType,
        name: str,
        specification: str,
        lower_limit: float | None = None,
        upper_limit: float | None = None,
        unit: str = "",
        is_mandatory: bool = True,
    ) -> Checkpoint:
        """Add a checkpoint to an operation."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write role required")

        if not name or not name.strip():
            raise ValueError("name required")

        checkpoint = Checkpoint(
            id=uuid4(),
            operation_id=operation_id,
            checkpoint_type=checkpoint_type,
            name=name.strip(),
            specification=specification,
            lower_limit=lower_limit,
            upper_limit=upper_limit,
            unit=unit,
            is_mandatory=is_mandatory,
        )
        self._checkpoints[checkpoint.id] = checkpoint

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.checkpoint.add",
            entity_type="checkpoint",
            entity_id=str(checkpoint.id),
            correlation_id=correlation_id,
            metadata={"type": checkpoint_type.value, "name": name},
        )

        return checkpoint

    # ----------------------------------------------------------------
    # Traveler Management
    # ----------------------------------------------------------------

    def create_traveler(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        product_id: str,
        lot_number: str,
        route_id: UUID,
        quantity: int,
        serial_number: str | None = None,
        genealogy: list[str] | None = None,
    ) -> Traveler:
        """Create an electronic traveler for a work order."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write role required")

        if not work_order_id or not work_order_id.strip():
            raise ValueError("work_order_id required")
        if not lot_number or not lot_number.strip():
            raise ValueError("lot_number required")
        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        if route_id not in self._routes:
            raise ValueError("route_id not found")

        traveler = Traveler(
            id=uuid4(),
            work_order_id=work_order_id.strip(),
            product_id=product_id.strip(),
            lot_number=lot_number.strip(),
            serial_number=serial_number,
            quantity=quantity,
            route_id=route_id,
            created_at=_utcnow(),
            created_by=actor_id,
            genealogy=tuple(genealogy) if genealogy else (),
        )
        self._travelers[traveler.id] = traveler

        # Create traveler operations from route
        route = self._routes[route_id]
        for op in route:
            trav_op = TravelerOperation(
                id=uuid4(),
                traveler_id=traveler.id,
                operation_id=op.id,
                sequence=op.sequence,
                status=OperationStatus.PENDING,
                station_id=op.station_id,
            )
            self._traveler_operations[trav_op.id] = trav_op

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.traveler.create",
            entity_type="traveler",
            entity_id=str(traveler.id),
            correlation_id=correlation_id,
            metadata={
                "work_order_id": work_order_id,
                "lot_number": lot_number,
                "quantity": quantity,
            },
        )

        return traveler

    def get_traveler(
        self, *, actor_roles: Iterable[str], traveler_id: UUID
    ) -> Traveler | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")
        return self._travelers.get(traveler_id)

    def get_traveler_operations(
        self, *, actor_roles: Iterable[str], traveler_id: UUID
    ) -> list[TravelerOperation]:
        """Get all operations for a traveler in sequence order."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")

        ops = [
            op for op in self._traveler_operations.values()
            if op.traveler_id == traveler_id
        ]
        return sorted(ops, key=lambda o: o.sequence)

    # ----------------------------------------------------------------
    # Operation Execution
    # ----------------------------------------------------------------

    def start_operation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        traveler_operation_id: UUID,
        operator_id: str | None = None,
    ) -> TravelerOperation:
        """Start working on a traveler operation."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _OPERATOR_ROLES, "Operator role required")

        trav_op = self._traveler_operations.get(traveler_operation_id)
        if not trav_op:
            raise ValueError("traveler_operation_id not found")
        if trav_op.status not in (OperationStatus.PENDING, OperationStatus.QUEUED):
            raise ValueError(f"Cannot start operation in status {trav_op.status.value}")

        # Check previous operations are complete
        prev_ops = [
            op for op in self._traveler_operations.values()
            if op.traveler_id == trav_op.traveler_id and op.sequence < trav_op.sequence
        ]
        for prev in prev_ops:
            if prev.status not in (OperationStatus.COMPLETED, OperationStatus.SKIPPED):
                raise ValueError("Previous operations must be completed first")

        updated = TravelerOperation(
            id=trav_op.id,
            traveler_id=trav_op.traveler_id,
            operation_id=trav_op.operation_id,
            sequence=trav_op.sequence,
            status=OperationStatus.IN_PROGRESS,
            station_id=trav_op.station_id,
            operator_id=operator_id or actor_id,
            started_at=_utcnow(),
        )
        self._traveler_operations[trav_op.id] = updated

        # Remove from dispatch queue if present
        for dispatch_id, item in list(self._dispatch_queue.items()):
            if item.traveler_operation_id == traveler_operation_id:
                del self._dispatch_queue[dispatch_id]

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.operation.start",
            entity_type="traveler_operation",
            entity_id=str(traveler_operation_id),
            correlation_id=correlation_id,
            metadata={"operator_id": operator_id or actor_id},
        )

        return updated

    def complete_operation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        traveler_operation_id: UUID,
        quantity_completed: int,
        quantity_scrapped: int = 0,
        notes: str = "",
    ) -> TravelerOperation:
        """Complete a traveler operation with sign-off."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _OPERATOR_ROLES, "Operator role required")

        trav_op = self._traveler_operations.get(traveler_operation_id)
        if not trav_op:
            raise ValueError("traveler_operation_id not found")
        if trav_op.status != OperationStatus.IN_PROGRESS:
            raise ValueError("Operation must be in progress to complete")

        # Check all mandatory checkpoints are passed
        checkpoints = [
            cp for cp in self._checkpoints.values()
            if cp.operation_id == trav_op.operation_id and cp.is_mandatory
        ]
        for cp in checkpoints:
            records = [
                r for r in self._checkpoint_records.values()
                if r.checkpoint_id == cp.id and r.traveler_id == trav_op.traveler_id
            ]
            if not records or records[-1].result not in (
                CheckpointResult.PASS, CheckpointResult.CONDITIONAL
            ):
                raise ValueError(f"Mandatory checkpoint '{cp.name}' not passed")

        # Get traveler to check quantity
        traveler = self._travelers.get(trav_op.traveler_id)
        if traveler and quantity_completed + quantity_scrapped > traveler.quantity:
            raise ValueError("Quantity exceeds traveler quantity")

        updated = TravelerOperation(
            id=trav_op.id,
            traveler_id=trav_op.traveler_id,
            operation_id=trav_op.operation_id,
            sequence=trav_op.sequence,
            status=OperationStatus.COMPLETED,
            station_id=trav_op.station_id,
            operator_id=trav_op.operator_id,
            started_at=trav_op.started_at,
            completed_at=_utcnow(),
            quantity_completed=quantity_completed,
            quantity_scrapped=quantity_scrapped,
            notes=notes,
        )
        self._traveler_operations[trav_op.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.operation.complete",
            entity_type="traveler_operation",
            entity_id=str(traveler_operation_id),
            correlation_id=correlation_id,
            metadata={
                "quantity_completed": quantity_completed,
                "quantity_scrapped": quantity_scrapped,
            },
        )

        return updated

    # ----------------------------------------------------------------
    # Checkpoint Recording
    # ----------------------------------------------------------------

    def record_checkpoint(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        checkpoint_id: UUID,
        traveler_id: UUID,
        result: CheckpointResult,
        measured_value: float | None = None,
        notes: str = "",
    ) -> CheckpointRecord:
        """Record a checkpoint result."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _OPERATOR_ROLES, "Operator role required")

        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError("checkpoint_id not found")
        if traveler_id not in self._travelers:
            raise ValueError("traveler_id not found")

        # Validate measurement against limits if provided
        if measured_value is not None:
            if checkpoint.lower_limit is not None and measured_value < checkpoint.lower_limit:
                if result == CheckpointResult.PASS:
                    raise ValueError("Measured value below lower limit")
            if checkpoint.upper_limit is not None and measured_value > checkpoint.upper_limit:
                if result == CheckpointResult.PASS:
                    raise ValueError("Measured value above upper limit")

        record = CheckpointRecord(
            id=uuid4(),
            checkpoint_id=checkpoint_id,
            traveler_id=traveler_id,
            operation_id=checkpoint.operation_id,
            result=result,
            measured_value=measured_value,
            notes=notes,
            recorded_by=actor_id,
            recorded_at=_utcnow(),
        )
        self._checkpoint_records[record.id] = record

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.checkpoint.record",
            entity_type="checkpoint_record",
            entity_id=str(record.id),
            correlation_id=correlation_id,
            metadata={
                "checkpoint_name": checkpoint.name,
                "result": result.value,
                "measured_value": measured_value,
            },
        )

        return record

    def get_checkpoint_records(
        self,
        *,
        actor_roles: Iterable[str],
        traveler_id: UUID,
        operation_id: UUID | None = None,
    ) -> list[CheckpointRecord]:
        """Get checkpoint records for a traveler."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")

        result = []
        for rec in self._checkpoint_records.values():
            if rec.traveler_id != traveler_id:
                continue
            if operation_id and rec.operation_id != operation_id:
                continue
            result.append(rec)

        return sorted(result, key=lambda r: r.recorded_at)

    # ----------------------------------------------------------------
    # Dispatching
    # ----------------------------------------------------------------

    def queue_for_dispatch(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        traveler_operation_id: UUID,
        priority: DispatchPriority = DispatchPriority.NORMAL,
        due_at: datetime | None = None,
    ) -> DispatchItem:
        """Add a traveler operation to the dispatch queue."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write role required")

        trav_op = self._traveler_operations.get(traveler_operation_id)
        if not trav_op:
            raise ValueError("traveler_operation_id not found")
        if trav_op.status != OperationStatus.PENDING:
            raise ValueError("Only pending operations can be queued")

        traveler = self._travelers.get(trav_op.traveler_id)
        if not traveler:
            raise ValueError("Traveler not found")

        # Find route operation for details
        route = self._routes.get(traveler.route_id, [])
        route_op = next((op for op in route if op.id == trav_op.operation_id), None)

        # Check constraints
        materials_ready = True
        tools_ready = True
        skills_available = True

        if route_op:
            if self._materials_provider and route_op.required_materials:
                materials_ready = self._materials_provider.check_materials_available(
                    list(route_op.required_materials)
                )
            if self._tools_provider and route_op.required_tools:
                tools_ready = self._tools_provider.check_tools_available(
                    list(route_op.required_tools)
                )

        dispatch_item = DispatchItem(
            id=uuid4(),
            traveler_operation_id=traveler_operation_id,
            station_id=trav_op.station_id,
            priority=priority,
            work_order_id=traveler.work_order_id,
            operation_code=route_op.operation_code if route_op else "",
            product_id=traveler.product_id,
            quantity=traveler.quantity,
            due_at=due_at,
            estimated_time_minutes=route_op.estimated_time_minutes if route_op else 0,
            required_skills=route_op.required_skills if route_op else (),
            required_tools=route_op.required_tools if route_op else (),
            materials_ready=materials_ready,
            tools_ready=tools_ready,
            skills_available=skills_available,
            queued_at=_utcnow(),
        )
        self._dispatch_queue[dispatch_item.id] = dispatch_item

        # Update operation status
        updated_op = TravelerOperation(
            id=trav_op.id,
            traveler_id=trav_op.traveler_id,
            operation_id=trav_op.operation_id,
            sequence=trav_op.sequence,
            status=OperationStatus.QUEUED,
            station_id=trav_op.station_id,
        )
        self._traveler_operations[trav_op.id] = updated_op

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="dispatch.queue",
            entity_type="dispatch_item",
            entity_id=str(dispatch_item.id),
            correlation_id=correlation_id,
            metadata={"priority": priority.value, "station_id": trav_op.station_id},
        )

        return dispatch_item

    def get_dispatch_queue(
        self,
        *,
        actor_roles: Iterable[str],
        station_id: str | None = None,
    ) -> list[DispatchItem]:
        """Get dispatch queue, optionally filtered by station."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")

        result = []
        for item in self._dispatch_queue.values():
            if station_id and item.station_id != station_id:
                continue
            result.append(item)

        # Sort by priority (urgent first) then due date
        priority_order = {
            DispatchPriority.URGENT: 0,
            DispatchPriority.HIGH: 1,
            DispatchPriority.NORMAL: 2,
            DispatchPriority.LOW: 3,
        }
        return sorted(
            result,
            key=lambda i: (
                priority_order[i.priority],
                i.due_at or datetime.max.replace(tzinfo=timezone.utc),
            ),
        )

    def get_ready_items(
        self,
        *,
        actor_roles: Iterable[str],
        station_id: str | None = None,
    ) -> list[DispatchItem]:
        """Get dispatch items where all constraints are satisfied."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")

        queue = self.get_dispatch_queue(actor_roles=actor_roles, station_id=station_id)
        return [
            item for item in queue
            if item.materials_ready and item.tools_ready and item.skills_available
        ]

    # ----------------------------------------------------------------
    # Genealogy
    # ----------------------------------------------------------------

    def get_genealogy(
        self,
        *,
        actor_roles: Iterable[str],
        traveler_id: UUID,
    ) -> dict[str, Any]:
        """Get genealogy information for a traveler."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read role required")

        traveler = self._travelers.get(traveler_id)
        if not traveler:
            raise ValueError("traveler_id not found")

        return {
            "traveler_id": str(traveler.id),
            "lot_number": traveler.lot_number,
            "serial_number": traveler.serial_number,
            "product_id": traveler.product_id,
            "parent_lots": list(traveler.genealogy),
            "work_order_id": traveler.work_order_id,
        }

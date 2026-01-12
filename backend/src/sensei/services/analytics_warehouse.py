"""Analytics Warehouse Export (Development Plan 21.9).

Implements:
- Daily Snapshots: automated state export to reporting-optimized store (Parquet-like).
- Dimensional Modeling: Fact/Dimension schemas for WO operations, NCs, Andon history.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class SnapshotStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DimensionType(str, Enum):
    TIME = "time"
    PART = "part"
    STATION = "station"
    OPERATOR = "operator"
    SHIFT = "shift"
    CUSTOMER = "customer"


class FactType(str, Enum):
    WORK_ORDER = "work_order"
    NON_CONFORMANCE = "non_conformance"
    ANDON_EVENT = "andon_event"
    CYCLE_TIME = "cycle_time"
    QUALITY_METRIC = "quality_metric"


_WAREHOUSE_ADMIN_ROLES: set[str] = {"admin", "bi", "exec", "ceo", "gm", "analyst"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DailySnapshot:
    id: UUID
    snapshot_date: date
    status: SnapshotStatus
    started_at: datetime | None
    completed_at: datetime | None
    record_count: int
    error_message: str | None
    created_by: UUID


@dataclass(frozen=True)
class DimensionSchema:
    id: UUID
    name: str
    dim_type: DimensionType
    key_column: str
    attribute_columns: list[str]
    created_at: datetime


@dataclass(frozen=True)
class FactSchema:
    id: UUID
    name: str
    fact_type: FactType
    dimension_keys: list[str]  # References to dimension key columns.
    measure_columns: list[str]
    created_at: datetime


@dataclass(frozen=True)
class ExportedRecord:
    snapshot_id: UUID
    fact_type: FactType
    data: dict[str, Any]


class AnalyticsWarehouseService:
    """In-memory analytics warehouse export service."""

    def __init__(self) -> None:
        self._snapshots: dict[UUID, DailySnapshot] = {}
        self._dimensions: dict[UUID, DimensionSchema] = {}
        self._facts: dict[UUID, FactSchema] = {}
        self._exported_records: list[ExportedRecord] = []

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_WAREHOUSE_ADMIN_ROLES)) > 0

    # ---- Daily Snapshots ----

    def create_snapshot(
        self,
        *,
        snapshot_date: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> DailySnapshot:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create snapshots")

        # Check idempotency.
        for s in self._snapshots.values():
            if s.snapshot_date == snapshot_date and s.status != SnapshotStatus.FAILED:
                return s

        snapshot = DailySnapshot(
            id=uuid4(),
            snapshot_date=snapshot_date,
            status=SnapshotStatus.PENDING,
            started_at=None,
            completed_at=None,
            record_count=0,
            error_message=None,
            created_by=actor_user_id,
        )
        self._snapshots[snapshot.id] = snapshot
        return snapshot

    def run_snapshot(
        self,
        snapshot_id: UUID,
        *,
        actor_roles: Iterable[str],
        records: list[dict[str, Any]] | None = None,
    ) -> DailySnapshot:
        """Execute the snapshot export. In real impl, would serialize to Parquet."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to run snapshots")
        if snapshot_id not in self._snapshots:
            raise KeyError("Snapshot not found")

        snapshot = self._snapshots[snapshot_id]
        snapshot.status = SnapshotStatus.RUNNING
        snapshot.started_at = _utcnow()

        try:
            # Simulate export.
            for rec in records or []:
                fact_type = rec.get("_fact_type", FactType.WORK_ORDER)
                self._exported_records.append(
                    ExportedRecord(
                        snapshot_id=snapshot_id,
                        fact_type=fact_type if isinstance(fact_type, FactType) else FactType.WORK_ORDER,
                        data=rec,
                    )
                )

            snapshot.record_count = len(records or [])
            snapshot.status = SnapshotStatus.COMPLETED
            snapshot.completed_at = _utcnow()
        except Exception as e:
            snapshot.status = SnapshotStatus.FAILED
            snapshot.error_message = str(e)

        return snapshot

    def list_snapshots(
        self,
        *,
        actor_roles: Iterable[str],
        status: SnapshotStatus | None = None,
    ) -> list[DailySnapshot]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view snapshots")

        result = list(self._snapshots.values())
        if status:
            result = [s for s in result if s.status == status]
        result.sort(key=lambda s: s.snapshot_date, reverse=True)
        return result

    # ---- Dimensional Modeling ----

    def register_dimension(
        self,
        *,
        name: str,
        dim_type: DimensionType,
        key_column: str,
        attribute_columns: list[str],
        actor_roles: Iterable[str],
    ) -> DimensionSchema:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage dimensions")

        dimension = DimensionSchema(
            id=uuid4(),
            name=name.strip(),
            dim_type=dim_type,
            key_column=key_column,
            attribute_columns=list(attribute_columns),
            created_at=_utcnow(),
        )
        self._dimensions[dimension.id] = dimension
        return dimension

    def register_fact(
        self,
        *,
        name: str,
        fact_type: FactType,
        dimension_keys: list[str],
        measure_columns: list[str],
        actor_roles: Iterable[str],
    ) -> FactSchema:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage facts")

        fact = FactSchema(
            id=uuid4(),
            name=name.strip(),
            fact_type=fact_type,
            dimension_keys=list(dimension_keys),
            measure_columns=list(measure_columns),
            created_at=_utcnow(),
        )
        self._facts[fact.id] = fact
        return fact

    def list_dimensions(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[DimensionSchema]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view dimensions")

        return sorted(self._dimensions.values(), key=lambda d: d.name.lower())

    def list_facts(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[FactSchema]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view facts")

        return sorted(self._facts.values(), key=lambda f: f.name.lower())

    def get_exported_records(
        self,
        snapshot_id: UUID | None = None,
        *,
        actor_roles: Iterable[str],
        fact_type: FactType | None = None,
    ) -> list[ExportedRecord]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view exported records")

        result = self._exported_records
        if snapshot_id:
            result = [r for r in result if r.snapshot_id == snapshot_id]
        if fact_type:
            result = [r for r in result if r.fact_type == fact_type]
        return result

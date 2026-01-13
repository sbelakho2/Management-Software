"""Analytics Warehouse Export (Development Plan 21.9).

Implements:
- Daily Snapshots: automated state export to reporting-optimized store (Parquet-like).
- Dimensional Modeling: Fact/Dimension schemas for WO operations, NCs, Andon history.

Production-grade service using SQLAlchemy.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Iterable, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.analytics import (
    DailySnapshot as DailySnapshotModel,
    DimensionSchema as DimensionSchemaModel,
    FactSchema as FactSchemaModel,
    ExportedRecord as ExportedRecordModel,
)


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


class AnalyticsWarehouseService:
    """Production analytics warehouse export service."""

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_WAREHOUSE_ADMIN_ROLES)) > 0

    # ---- Daily Snapshots ----

    async def create_snapshot(
        self,
        db: AsyncSession,
        *,
        snapshot_date: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> DailySnapshotModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create snapshots")

        # Check idempotency.
        stmt = select(DailySnapshotModel).where(
            and_(
                DailySnapshotModel.snapshot_date == snapshot_date,
                DailySnapshotModel.status != SnapshotStatus.FAILED.value
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        snapshot = DailySnapshotModel(
            id=uuid4(),
            snapshot_date=snapshot_date,
            status=SnapshotStatus.PENDING.value,
            record_count=0,
            created_by_id=actor_user_id,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot

    async def run_snapshot(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        *,
        actor_roles: Iterable[str],
        records: list[dict[str, Any]] | None = None,
    ) -> DailySnapshotModel:
        """Execute the snapshot export."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to run snapshots")
        
        stmt = select(DailySnapshotModel).where(DailySnapshotModel.id == snapshot_id)
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            raise KeyError("Snapshot not found")

        snapshot.status = SnapshotStatus.RUNNING.value
        snapshot.started_at = _utcnow()
        await db.flush()

        try:
            # Export records.
            for rec in records or []:
                fact_type = rec.get("_fact_type", FactType.WORK_ORDER.value)
                if isinstance(fact_type, FactType):
                    fact_type = fact_type.value
                
                exported = ExportedRecordModel(
                    id=uuid4(),
                    snapshot_id=snapshot_id,
                    fact_type=fact_type,
                    data=rec,
                )
                db.add(exported)

            snapshot.record_count = len(records or [])
            snapshot.status = SnapshotStatus.COMPLETED.value
            snapshot.completed_at = _utcnow()
            await db.flush()
        except Exception as e:
            snapshot.status = SnapshotStatus.FAILED.value
            snapshot.error_message = str(e)
            await db.flush()

        return snapshot

    async def list_snapshots(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        status: SnapshotStatus | None = None,
    ) -> list[DailySnapshotModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view snapshots")

        stmt = select(DailySnapshotModel)
        if status:
            stmt = stmt.where(DailySnapshotModel.status == status.value)
        stmt = stmt.order_by(DailySnapshotModel.snapshot_date.desc())
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Dimensional Modeling ----

    async def register_dimension(
        self,
        db: AsyncSession,
        *,
        name: str,
        dim_type: DimensionType,
        key_column: str,
        attribute_columns: list[str],
        actor_roles: Iterable[str],
    ) -> DimensionSchemaModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage dimensions")

        dimension = DimensionSchemaModel(
            id=uuid4(),
            name=name.strip(),
            dim_type=dim_type.value,
            key_column=key_column,
            attribute_columns=list(attribute_columns),
        )
        db.add(dimension)
        await db.flush()
        return dimension

    async def register_fact(
        self,
        db: AsyncSession,
        *,
        name: str,
        fact_type: FactType,
        dimension_keys: list[str],
        measure_columns: list[str],
        actor_roles: Iterable[str],
    ) -> FactSchemaModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage facts")

        fact = FactSchemaModel(
            id=uuid4(),
            name=name.strip(),
            fact_type=fact_type.value,
            dimension_keys=list(dimension_keys),
            measure_columns=list(measure_columns),
        )
        db.add(fact)
        await db.flush()
        return fact

    async def list_dimensions(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> list[DimensionSchemaModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view dimensions")

        stmt = select(DimensionSchemaModel).order_by(DimensionSchemaModel.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_facts(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> list[FactSchemaModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view facts")

        stmt = select(FactSchemaModel).order_by(FactSchemaModel.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_exported_records(
        self,
        db: AsyncSession,
        snapshot_id: UUID | None = None,
        *,
        actor_roles: Iterable[str],
        fact_type: FactType | None = None,
    ) -> list[ExportedRecordModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view exported records")

        stmt = select(ExportedRecordModel)
        if snapshot_id:
            stmt = stmt.where(ExportedRecordModel.snapshot_id == snapshot_id)
        if fact_type:
            stmt = stmt.where(ExportedRecordModel.fact_type == fact_type.value)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

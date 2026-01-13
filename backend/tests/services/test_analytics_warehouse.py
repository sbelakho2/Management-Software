"""Tests for Analytics Warehouse Export service."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.ops.analytics_warehouse import (
    AnalyticsWarehouseService,
    DailySnapshot,
    DimensionSchema,
    DimensionType,
    FactSchema,
    FactType,
    SnapshotStatus,
)


@pytest.fixture
def svc() -> AnalyticsWarehouseService:
    return AnalyticsWarehouseService()


ADMIN_ROLES = ("admin",)
BI_ROLES = ("bi",)
ANALYST_ROLES = ("analyst",)
VIEWER_ROLES = ("viewer",)


@pytest.mark.asyncio
class TestDailySnapshots:
    async def test_create_snapshot_requires_role(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        with pytest.raises(PermissionError):
            await svc.create_snapshot(
                async_session,
                snapshot_date=date.today(),
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

        snapshot = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=BI_ROLES,
        )
        assert isinstance(snapshot, DailySnapshot)
        assert snapshot.status == SnapshotStatus.PENDING.value

    async def test_snapshot_idempotency(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        today = date.today()
        s1 = await svc.create_snapshot(
            async_session,
            snapshot_date=today,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        s2 = await svc.create_snapshot(
            async_session,
            snapshot_date=today,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert s1.id == s2.id

    async def test_run_snapshot_exports_records(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        snapshot = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        records = [
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001", "qty": 100},
            {"_fact_type": FactType.ANDON_EVENT, "event_id": "A-001", "duration": 15},
        ]

        completed = await svc.run_snapshot(async_session, snapshot.id, actor_roles=ADMIN_ROLES, records=records)
        assert completed.status == SnapshotStatus.COMPLETED.value
        assert completed.record_count == 2

        exported = await svc.get_exported_records(async_session, snapshot.id, actor_roles=ADMIN_ROLES)
        assert len(exported) == 2


@pytest.mark.asyncio
class TestDimensionalModeling:
    async def test_register_dimension(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        dim = await svc.register_dimension(
            async_session,
            name="Time",
            dim_type=DimensionType.TIME,
            key_column="date_key",
            attribute_columns=["year", "quarter", "month", "week", "day"],
            actor_roles=ANALYST_ROLES,
        )

        assert isinstance(dim, DimensionSchema)
        assert dim.dim_type == DimensionType.TIME.value

        dims = await svc.list_dimensions(async_session, actor_roles=ADMIN_ROLES)
        assert len(dims) == 1

    async def test_register_fact(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        fact = await svc.register_fact(
            async_session,
            name="Work Order Operations",
            fact_type=FactType.WORK_ORDER,
            dimension_keys=["date_key", "part_key", "station_key"],
            measure_columns=["quantity", "cycle_time", "scrap_qty"],
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(fact, FactSchema)
        assert fact.fact_type == FactType.WORK_ORDER.value

        facts = await svc.list_facts(async_session, actor_roles=ADMIN_ROLES)
        assert len(facts) == 1

    async def test_dimension_requires_role(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        with pytest.raises(PermissionError):
            await svc.register_dimension(
                async_session,
                name="Part",
                dim_type=DimensionType.PART,
                key_column="part_key",
                attribute_columns=["part_number", "description"],
                actor_roles=VIEWER_ROLES,
            )


@pytest.mark.asyncio
class TestSnapshotListing:
    async def test_list_by_status(self, svc: AnalyticsWarehouseService, async_session: AsyncSession) -> None:
        s1 = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today() - timedelta(days=1),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        await svc.run_snapshot(async_session, s1.id, actor_roles=ADMIN_ROLES, records=[{"x": 1}])

        s2 = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        pending = await svc.list_snapshots(async_session, actor_roles=ADMIN_ROLES, status=SnapshotStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].id == s2.id

        completed = await svc.list_snapshots(async_session, actor_roles=ADMIN_ROLES, status=SnapshotStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == s1.id

"""Tests for Analytics Warehouse Export service."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from sensei.services.analytics_warehouse import (
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


class TestDailySnapshots:
    def test_create_snapshot_requires_role(self, svc: AnalyticsWarehouseService) -> None:
        with pytest.raises(PermissionError):
            svc.create_snapshot(
                snapshot_date=date.today(),
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

        snapshot = svc.create_snapshot(
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=BI_ROLES,
        )
        assert isinstance(snapshot, DailySnapshot)
        assert snapshot.status == SnapshotStatus.PENDING

    def test_snapshot_idempotency(self, svc: AnalyticsWarehouseService) -> None:
        today = date.today()
        s1 = svc.create_snapshot(
            snapshot_date=today,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        s2 = svc.create_snapshot(
            snapshot_date=today,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert s1.id == s2.id

    def test_run_snapshot_exports_records(self, svc: AnalyticsWarehouseService) -> None:
        snapshot = svc.create_snapshot(
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        records = [
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001", "qty": 100},
            {"_fact_type": FactType.ANDON_EVENT, "event_id": "A-001", "duration": 15},
        ]

        completed = svc.run_snapshot(snapshot.id, actor_roles=ADMIN_ROLES, records=records)
        assert completed.status == SnapshotStatus.COMPLETED
        assert completed.record_count == 2

        exported = svc.get_exported_records(snapshot.id, actor_roles=ADMIN_ROLES)
        assert len(exported) == 2


class TestDimensionalModeling:
    def test_register_dimension(self, svc: AnalyticsWarehouseService) -> None:
        dim = svc.register_dimension(
            name="Time",
            dim_type=DimensionType.TIME,
            key_column="date_key",
            attribute_columns=["year", "quarter", "month", "week", "day"],
            actor_roles=ANALYST_ROLES,
        )

        assert isinstance(dim, DimensionSchema)
        assert dim.dim_type == DimensionType.TIME

        dims = svc.list_dimensions(actor_roles=ADMIN_ROLES)
        assert len(dims) == 1

    def test_register_fact(self, svc: AnalyticsWarehouseService) -> None:
        fact = svc.register_fact(
            name="Work Order Operations",
            fact_type=FactType.WORK_ORDER,
            dimension_keys=["date_key", "part_key", "station_key"],
            measure_columns=["quantity", "cycle_time", "scrap_qty"],
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(fact, FactSchema)
        assert fact.fact_type == FactType.WORK_ORDER

        facts = svc.list_facts(actor_roles=ADMIN_ROLES)
        assert len(facts) == 1

    def test_dimension_requires_role(self, svc: AnalyticsWarehouseService) -> None:
        with pytest.raises(PermissionError):
            svc.register_dimension(
                name="Part",
                dim_type=DimensionType.PART,
                key_column="part_key",
                attribute_columns=["part_number", "description"],
                actor_roles=VIEWER_ROLES,
            )


class TestSnapshotListing:
    def test_list_by_status(self, svc: AnalyticsWarehouseService) -> None:
        s1 = svc.create_snapshot(
            snapshot_date=date.today() - timedelta(days=1),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.run_snapshot(s1.id, actor_roles=ADMIN_ROLES, records=[{"x": 1}])

        s2 = svc.create_snapshot(
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        pending = svc.list_snapshots(actor_roles=ADMIN_ROLES, status=SnapshotStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].id == s2.id

        completed = svc.list_snapshots(actor_roles=ADMIN_ROLES, status=SnapshotStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == s1.id

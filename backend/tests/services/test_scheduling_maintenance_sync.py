"""Tests for Scheduling ↔ Maintenance Sync (Development Plan 23.2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from sensei.services.maintenance.maintenance_tpm import (
    AssetType,
    MaintenanceService,
    PMFrequencyType,
    WorkOrderStatus,
    WorkOrderType,
)
from sensei.services.production.production_scheduling import (
    CalendarWindow,
    CalendarWindowType,
    ProductionSchedulingService,
    WorkOrderTask,
)
from sensei.services.production.scheduling_maintenance_sync import SchedulingMaintenanceSyncService


@pytest.fixture
def start_at() -> datetime:
    return datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)


def test_sync_work_order_maintenance_blocks_finite_scheduling(start_at: datetime) -> None:
    maintenance = MaintenanceService()
    scheduler = ProductionSchedulingService()

    # Two days of shifts.
    scheduler.add_calendar_window(
        CalendarWindow(
            station_id="S1",
            start=start_at,
            end=start_at + timedelta(hours=8),
            window_type=CalendarWindowType.SHIFT,
            name="Day Shift",
        )
    )
    next_day = start_at + timedelta(days=1)
    scheduler.add_calendar_window(
        CalendarWindow(
            station_id="S1",
            start=next_day,
            end=next_day + timedelta(hours=8),
            window_type=CalendarWindowType.SHIFT,
            name="Day Shift+1",
        )
    )

    asset = maintenance.create_asset(
        name="CNC-1",
        asset_type=AssetType.MACHINE,
        work_center_id="S1",
    )

    wo = maintenance.create_work_order(
        asset_id=asset.id,
        work_order_type=WorkOrderType.PREVENTIVE,
        description="Planned maintenance",
        scheduled_start=start_at + timedelta(hours=4),
        scheduled_end=start_at + timedelta(hours=5),
    )
    maintenance.update_work_order_status(wo.id, WorkOrderStatus.OPEN)

    sync = SchedulingMaintenanceSyncService(maintenance=maintenance, scheduler=scheduler)
    summary = sync.apply_maintenance_windows(start_at=start_at, end_at=next_day + timedelta(hours=8))

    assert summary.windows_applied == 1
    windows = scheduler.list_calendar_windows("S1")
    assert any(w.window_type == CalendarWindowType.MAINTENANCE and w.name == wo.work_order_number for w in windows)

    tasks = [
        WorkOrderTask(id="A", station_id="S1", duration_minutes=120),
        WorkOrderTask(id="B", station_id="S1", duration_minutes=240),
    ]

    result = scheduler.schedule(tasks, start_at=start_at)
    assert result.unscheduled == []

    scheduled = {t.id: t for t in result.scheduled}
    assert scheduled["A"].start == start_at
    assert scheduled["A"].end == start_at + timedelta(hours=2)

    # B cannot fit 10:00-12:00 (only 2h) and can't run across maintenance (12:00-13:00).
    # So it should land on the next day's shift.
    assert scheduled["B"].start == next_day
    assert scheduled["B"].end == next_day + timedelta(hours=4)


def test_sync_pm_due_blocks_capacity(start_at: datetime) -> None:
    maintenance = MaintenanceService()
    scheduler = ProductionSchedulingService()

    scheduler.add_calendar_window(
        CalendarWindow(
            station_id="S1",
            start=start_at,
            end=start_at + timedelta(hours=8),
            window_type=CalendarWindowType.SHIFT,
            name="Day Shift",
        )
    )

    asset = maintenance.create_asset(
        name="Press-1",
        asset_type=AssetType.MACHINE,
        work_center_id="S1",
    )

    pm = maintenance.create_pm_schedule(
        asset_id=asset.id,
        name="Lubrication",
        frequency_type=PMFrequencyType.CALENDAR,
        frequency_value=7,
        frequency_unit="days",
        estimated_duration_hours=Decimal("2"),
    )

    # Force PM due into the horizon deterministically for test.
    pm.next_due = start_at + timedelta(hours=1)  # 09:00-11:00 maintenance window

    sync = SchedulingMaintenanceSyncService(maintenance=maintenance, scheduler=scheduler)
    summary = sync.apply_maintenance_windows(start_at=start_at, end_at=start_at + timedelta(hours=8))

    assert summary.windows_applied == 1

    task = WorkOrderTask(id="T1", station_id="S1", duration_minutes=120)
    result = scheduler.schedule([task], start_at=start_at)

    # 2h cannot fit 08:00-09:00; should schedule after PM window.
    assert result.unscheduled == []
    assert result.scheduled[0].start == start_at + timedelta(hours=3)  # 11:00
    assert result.scheduled[0].end == start_at + timedelta(hours=5)  # 13:00

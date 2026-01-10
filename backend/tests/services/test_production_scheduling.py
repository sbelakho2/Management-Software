"""Tests for Production Scheduling & Finite Capacity Service (Development Plan 21.6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sensei.services.production_scheduling import (
    ProductionSchedulingService,
    WorkOrderTask,
    TaskPriority,
    CalendarWindow,
    CalendarWindowType,
    ScheduleFailureReason,
)


class _MaterialsProvider:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def materials_available(self, materials, start, end) -> bool:  # noqa: ANN001
        return self._available


class _ToolingProvider:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def tooling_available(self, tooling_ids, start, end) -> bool:  # noqa: ANN001
        return self._available


class _SkillsProvider:
    def __init__(self, available: bool = True) -> None:
        self._available = available

    def skills_available(self, skill_requirements, start, end) -> bool:  # noqa: ANN001
        return self._available


@pytest.fixture
def start_at() -> datetime:
    return datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)


def test_schedules_without_overlap_same_station(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    tasks = [
        WorkOrderTask(id="wo-1", station_id="S1", duration_minutes=60),
        WorkOrderTask(id="wo-2", station_id="S1", duration_minutes=30),
    ]

    result = svc.schedule(tasks, start_at=start_at)
    assert result.unscheduled == []
    assert len(result.scheduled) == 2

    scheduled = {t.id: t for t in result.scheduled}
    assert scheduled["wo-1"].start == start_at
    assert scheduled["wo-1"].end == start_at + timedelta(minutes=60)
    assert scheduled["wo-2"].start == start_at + timedelta(minutes=60)
    assert scheduled["wo-2"].end == start_at + timedelta(minutes=90)


def test_schedules_parallel_different_stations(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    tasks = [
        WorkOrderTask(id="wo-1", station_id="S1", duration_minutes=60),
        WorkOrderTask(id="wo-2", station_id="S2", duration_minutes=60),
    ]

    result = svc.schedule(tasks, start_at=start_at)
    assert result.unscheduled == []

    scheduled = {t.id: t for t in result.scheduled}
    assert scheduled["wo-1"].start == start_at
    assert scheduled["wo-2"].start == start_at


def test_respects_earliest_start(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    es = start_at + timedelta(hours=2)
    tasks = [WorkOrderTask(id="wo-1", station_id="S1", duration_minutes=30, earliest_start=es)]

    result = svc.schedule(tasks, start_at=start_at)
    assert result.unscheduled == []
    assert result.scheduled[0].start == es


def test_shift_calendar_and_maintenance_windows(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    # Shift: 08:00-16:00
    svc.add_calendar_window(
        CalendarWindow(
            station_id="S1",
            start=start_at,
            end=start_at + timedelta(hours=8),
            window_type=CalendarWindowType.SHIFT,
            name="Day Shift",
        )
    )

    # Maintenance: 12:00-13:00 blocks the middle of the shift
    svc.add_calendar_window(
        CalendarWindow(
            station_id="S1",
            start=start_at + timedelta(hours=4),
            end=start_at + timedelta(hours=5),
            window_type=CalendarWindowType.MAINTENANCE,
            name="PM",
        )
    )

    # Task A: 2h fits 08:00-10:00
    # Task B: 4h cannot fit 10:00-12:00 (only 2h) and can't run across maintenance.
    # Provide next-day shift so it can be scheduled.
    next_day = start_at + timedelta(days=1)
    svc.add_calendar_window(
        CalendarWindow(
            station_id="S1",
            start=next_day,
            end=next_day + timedelta(hours=8),
            window_type=CalendarWindowType.SHIFT,
            name="Day Shift+1",
        )
    )

    tasks = [
        WorkOrderTask(id="A", station_id="S1", duration_minutes=120),
        WorkOrderTask(id="B", station_id="S1", duration_minutes=240),
    ]

    result = svc.schedule(tasks, start_at=start_at)
    assert result.unscheduled == []

    scheduled = {t.id: t for t in result.scheduled}
    assert scheduled["A"].start == start_at
    assert scheduled["A"].end == start_at + timedelta(hours=2)

    # B lands next day at 08:00
    assert scheduled["B"].start == next_day
    assert scheduled["B"].end == next_day + timedelta(hours=4)


def test_horizon_blocks_unschedulable(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    task = WorkOrderTask(id="wo-1", station_id="S1", duration_minutes=60)
    result = svc.schedule([task], start_at=start_at, horizon_end=start_at + timedelta(minutes=30))

    assert result.scheduled == []
    assert len(result.unscheduled) == 1
    assert result.unscheduled[0].reason == ScheduleFailureReason.NO_CAPACITY_WITHIN_HORIZON


def test_resource_unavailable_blocks_scheduling(start_at: datetime) -> None:
    svc = ProductionSchedulingService(materials_provider=_MaterialsProvider(available=False))

    task = WorkOrderTask(
        id="wo-1",
        station_id="S1",
        duration_minutes=30,
        materials={"part-1": 1.0},
    )

    result = svc.schedule([task], start_at=start_at)

    assert result.scheduled == []
    assert len(result.unscheduled) == 1
    assert result.unscheduled[0].reason == ScheduleFailureReason.MATERIALS_UNAVAILABLE


def test_rush_requires_gm_approval(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    rush = WorkOrderTask(
        id="rush-1",
        station_id="S1",
        duration_minutes=30,
        priority=TaskPriority.CRITICAL,
        is_rush=True,
    )

    result = svc.schedule([rush], start_at=start_at)
    assert result.scheduled == []
    assert result.unscheduled[0].reason == ScheduleFailureReason.RUSH_NOT_APPROVED

    svc.request_rush("rush-1", requested_by="operator-1", rationale="Customer expedite")
    svc.approve_rush(
        "rush-1",
        approved_by="gm-1",
        approver_role="gm",
        rationale="Approved: customer line down",
    )

    result2 = svc.schedule([rush], start_at=start_at)
    assert result2.unscheduled == []
    assert result2.scheduled[0].start == start_at


def test_priority_orders_tasks(start_at: datetime) -> None:
    svc = ProductionSchedulingService()

    normal = WorkOrderTask(id="n", station_id="S1", duration_minutes=60, priority=TaskPriority.NORMAL)
    critical = WorkOrderTask(id="c", station_id="S1", duration_minutes=30, priority=TaskPriority.CRITICAL)

    # Provide in reverse order, expect critical to be scheduled first.
    result = svc.schedule([normal, critical], start_at=start_at)
    assert result.unscheduled == []

    scheduled = {t.id: t for t in result.scheduled}
    assert scheduled["c"].start == start_at
    assert scheduled["n"].start == start_at + timedelta(minutes=30)

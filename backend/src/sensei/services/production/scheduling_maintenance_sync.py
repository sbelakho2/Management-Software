"""Scheduling ↔ Maintenance (TPM) synchronization.

Development Plan 23.2: Unified Scheduling & Maintenance Sync

This module bridges the in-memory TPM maintenance layer (`MaintenanceService`) with
finite capacity scheduling (`ProductionSchedulingService`) by translating scheduled
maintenance work into scheduler MAINTENANCE calendar windows.

The scheduler already respects MAINTENANCE windows. This service makes sure those
windows are kept in sync with TPM's scheduled work orders and (optionally) upcoming
PM schedules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from sensei.services.maintenance.maintenance_tpm import MaintenanceService, WorkOrderStatus
from sensei.services.production.production_scheduling import (
    CalendarWindow,
    CalendarWindowType,
    ProductionSchedulingService,
)


def _require_tzaware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("All datetimes must be timezone-aware")


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


@dataclass(frozen=True)
class MaintenanceSyncSummary:
    stations_touched: int
    windows_applied: int
    windows_skipped: int


class SchedulingMaintenanceSyncService:
    """Unifies TPM maintenance schedules with finite scheduling constraints."""

    _asset_to_station: Callable[[str], str | None]

    def __init__(
        self,
        *,
        maintenance: MaintenanceService,
        scheduler: ProductionSchedulingService,
        asset_to_station: Callable[[str], str | None] | None = None,
    ) -> None:
        self._maintenance = maintenance
        self._scheduler = scheduler

        # asset_id -> station_id resolver
        if asset_to_station is None:
            self._asset_to_station = self._default_asset_to_station
        else:
            self._asset_to_station = asset_to_station

    def _default_asset_to_station(self, asset_id: str) -> str | None:
        asset = self._maintenance.get_asset(asset_id)
        if asset is None:
            return None
        return asset.work_center_id

    def apply_maintenance_windows(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        include_work_orders: bool = True,
        include_pm_due: bool = True,
        clear_existing_maintenance_windows: bool = True,
        station_filter: set[str] | None = None,
    ) -> MaintenanceSyncSummary:
        """Generate and apply MAINTENANCE windows to the scheduler.

        - Work orders: scheduled_start/scheduled_end become MAINTENANCE windows.
        - PM schedules: next_due + estimated_duration_hours becomes a MAINTENANCE window.

        Notes:
        - Only COMPLETED/CANCELLED work orders are ignored.
        - If an asset cannot be mapped to a station_id, the window is skipped.
        """

        _require_tzaware(start_at)
        _require_tzaware(end_at)
        if end_at <= start_at:
            raise ValueError("end_at must be after start_at")

        windows_by_station: dict[str, list[CalendarWindow]] = {}
        skipped = 0

        if include_work_orders:
            for wo in self._maintenance.get_work_orders():
                if wo.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
                    continue
                if wo.scheduled_start is None or wo.scheduled_end is None:
                    continue

                _require_tzaware(wo.scheduled_start)
                _require_tzaware(wo.scheduled_end)
                if wo.scheduled_end <= wo.scheduled_start:
                    skipped += 1
                    continue

                if not _overlaps(wo.scheduled_start, wo.scheduled_end, start_at, end_at):
                    continue

                station_id = self._asset_to_station(wo.asset_id)
                if station_id is None:
                    skipped += 1
                    continue
                if station_filter is not None and station_id not in station_filter:
                    continue

                windows_by_station.setdefault(station_id, []).append(
                    CalendarWindow(
                        station_id=station_id,
                        start=wo.scheduled_start,
                        end=wo.scheduled_end,
                        window_type=CalendarWindowType.MAINTENANCE,
                        name=f"{wo.work_order_number}",
                    )
                )

        if include_pm_due:
            for sched in self._maintenance.get_pm_schedules(is_active=True):
                if sched.next_due is None:
                    continue
                _require_tzaware(sched.next_due)

                duration_hours = float(sched.estimated_duration_hours)
                if duration_hours <= 0:
                    skipped += 1
                    continue

                pm_start = sched.next_due
                pm_end = pm_start + timedelta(hours=duration_hours)

                if not _overlaps(pm_start, pm_end, start_at, end_at):
                    continue

                station_id = self._asset_to_station(sched.asset_id)
                if station_id is None:
                    skipped += 1
                    continue
                if station_filter is not None and station_id not in station_filter:
                    continue

                windows_by_station.setdefault(station_id, []).append(
                    CalendarWindow(
                        station_id=station_id,
                        start=pm_start,
                        end=pm_end,
                        window_type=CalendarWindowType.MAINTENANCE,
                        name=f"PM:{sched.name}",
                    )
                )

        # Apply in deterministic order: station_id asc then window start asc
        stations = sorted(windows_by_station.keys())
        windows_applied = 0

        for station_id in stations:
            windows = sorted(windows_by_station[station_id], key=lambda w: (w.start, w.end, w.name))

            if clear_existing_maintenance_windows:
                self._scheduler.clear_calendar_windows(station_id, window_type=CalendarWindowType.MAINTENANCE)

            for w in windows:
                self._scheduler.add_calendar_window(w)
                windows_applied += 1

        return MaintenanceSyncSummary(
            stations_touched=len(stations),
            windows_applied=windows_applied,
            windows_skipped=skipped,
        )

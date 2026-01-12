"""Production Scheduling & Finite Capacity Service.

Implements a constraint-aware finite-capacity scheduling engine.

Scope (Development Plan 21.6):
- Finite capacity scheduling across Stations (no overlap)
- Constraint modeling: shift calendars + planned maintenance windows
- Resource checks: materials (WMS), tooling (asset registry), skills (training matrix)
- Priority/expedite workflow: auditable rush orders requiring GM approval + rationale

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Protocol, Any


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class ScheduleFailureReason(str, Enum):
    NO_CAPACITY_WITHIN_HORIZON = "no_capacity_within_horizon"
    RUSH_NOT_APPROVED = "rush_not_approved"
    MATERIALS_UNAVAILABLE = "materials_unavailable"
    TOOLING_UNAVAILABLE = "tooling_unavailable"
    SKILLS_UNAVAILABLE = "skills_unavailable"


class CalendarWindowType(str, Enum):
    SHIFT = "shift"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class CalendarWindow:
    """A time window for a station.

    - SHIFT windows define when work *can* be scheduled.
    - MAINTENANCE windows define downtime that blocks scheduling.
    """

    station_id: str
    start: datetime
    end: datetime
    window_type: CalendarWindowType
    name: str = ""


@dataclass(frozen=True)
class WorkOrderTask:
    """A schedulable work-order task or operation.

    The scheduler treats each task as a single contiguous block.
    """

    id: str
    station_id: str
    duration_minutes: int
    priority: TaskPriority = TaskPriority.NORMAL
    earliest_start: datetime | None = None
    due_at: datetime | None = None

    # Resource requirements
    materials: dict[str, float] = field(default_factory=dict)  # part_id -> qty
    tooling_ids: list[str] = field(default_factory=list)
    skill_requirements: dict[str, int] = field(default_factory=dict)  # skill_code -> min level

    # Expedite
    is_rush: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduledTask:
    id: str
    station_id: str
    start: datetime
    end: datetime
    priority: TaskPriority


@dataclass(frozen=True)
class UnscheduledTask:
    task_id: str
    station_id: str
    reason: ScheduleFailureReason
    details: str = ""


@dataclass(frozen=True)
class SchedulingResult:
    scheduled: list[ScheduledTask]
    unscheduled: list[UnscheduledTask]


@dataclass
class RushRequest:
    task_id: str
    requested_by: str
    requested_at: datetime
    request_rationale: str

    approved: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_rationale: str = ""


class MaterialsAvailabilityProvider(Protocol):
    def materials_available(
        self,
        materials: dict[str, float],
        start: datetime,
        end: datetime,
    ) -> bool: ...


class ToolingAvailabilityProvider(Protocol):
    def tooling_available(
        self,
        tooling_ids: list[str],
        start: datetime,
        end: datetime,
    ) -> bool: ...


class SkillsAvailabilityProvider(Protocol):
    def skills_available(
        self,
        skill_requirements: dict[str, int],
        start: datetime,
        end: datetime,
    ) -> bool: ...


class _AlwaysAvailable:
    def materials_available(self, materials: dict[str, float], start: datetime, end: datetime) -> bool:
        return True

    def tooling_available(self, tooling_ids: list[str], start: datetime, end: datetime) -> bool:
        return True

    def skills_available(self, skill_requirements: dict[str, int], start: datetime, end: datetime) -> bool:
        return True


def _require_tzaware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("All datetimes must be timezone-aware")


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _priority_rank(priority: TaskPriority) -> int:
    # Higher number means higher priority
    return {
        TaskPriority.LOW: 1,
        TaskPriority.NORMAL: 2,
        TaskPriority.HIGH: 3,
        TaskPriority.URGENT: 4,
        TaskPriority.CRITICAL: 5,
    }[priority]


class ProductionSchedulingService:
    """Finite-capacity scheduling engine with constraint and resource checks."""

    def __init__(
        self,
        *,
        materials_provider: MaterialsAvailabilityProvider | None = None,
        tooling_provider: ToolingAvailabilityProvider | None = None,
        skills_provider: SkillsAvailabilityProvider | None = None,
    ) -> None:
        self._materials = materials_provider or _AlwaysAvailable()
        self._tooling = tooling_provider or _AlwaysAvailable()
        self._skills = skills_provider or _AlwaysAvailable()

        self._calendar: dict[str, list[CalendarWindow]] = {}
        self._schedule_by_station: dict[str, list[ScheduledTask]] = {}
        self._rush_requests: dict[str, RushRequest] = {}

    # ---------------------------------------------------------------------
    # Calendar configuration
    # ---------------------------------------------------------------------

    def add_calendar_window(self, window: CalendarWindow) -> None:
        _require_tzaware(window.start)
        _require_tzaware(window.end)
        if window.end <= window.start:
            raise ValueError("window.end must be after window.start")
        self._calendar.setdefault(window.station_id, []).append(window)

    def clear_calendar_windows(
        self,
        station_id: str,
        *,
        window_type: CalendarWindowType | None = None,
    ) -> None:
        """Clear calendar windows for a station.

        If `window_type` is provided, only windows of that type are removed.
        """
        if station_id not in self._calendar:
            return

        if window_type is None:
            self._calendar.pop(station_id, None)
            return

        self._calendar[station_id] = [
            w for w in self._calendar.get(station_id, []) if w.window_type != window_type
        ]
        if not self._calendar[station_id]:
            self._calendar.pop(station_id, None)

    def list_calendar_windows(self, station_id: str) -> list[CalendarWindow]:
        return sorted(self._calendar.get(station_id, []), key=lambda w: (w.start, w.end, w.window_type.value))

    # ---------------------------------------------------------------------
    # Rush workflow
    # ---------------------------------------------------------------------

    def request_rush(
        self,
        task_id: str,
        *,
        requested_by: str,
        rationale: str,
        requested_at: datetime | None = None,
    ) -> RushRequest:
        if not rationale.strip():
            raise ValueError("Rush request rationale is required")
        now = requested_at or datetime.now(timezone.utc)
        _require_tzaware(now)
        req = RushRequest(
            task_id=task_id,
            requested_by=requested_by,
            requested_at=now,
            request_rationale=rationale.strip(),
        )
        self._rush_requests[task_id] = req
        return req

    def approve_rush(
        self,
        task_id: str,
        *,
        approved_by: str,
        approver_role: str,
        rationale: str,
        approved_at: datetime | None = None,
    ) -> RushRequest:
        req = self._rush_requests.get(task_id)
        if req is None:
            raise ValueError("Rush request not found")
        if not rationale.strip():
            raise ValueError("Rush approval rationale is required")
        role_norm = approver_role.strip().lower()
        if role_norm not in {"gm", "general_manager", "ceo"}:
            raise PermissionError("Rush approval requires GM/CEO")
        now = approved_at or datetime.now(timezone.utc)
        _require_tzaware(now)
        req.approved = True
        req.approved_by = approved_by
        req.approved_at = now
        req.approval_rationale = rationale.strip()
        return req

    def get_rush_request(self, task_id: str) -> RushRequest | None:
        return self._rush_requests.get(task_id)

    # ---------------------------------------------------------------------
    # Scheduling
    # ---------------------------------------------------------------------

    def list_station_schedule(self, station_id: str) -> list[ScheduledTask]:
        return sorted(self._schedule_by_station.get(station_id, []), key=lambda s: s.start)

    def clear_schedule(self) -> None:
        self._schedule_by_station.clear()

    def schedule(
        self,
        tasks: list[WorkOrderTask],
        *,
        start_at: datetime,
        horizon_end: datetime | None = None,
    ) -> SchedulingResult:
        _require_tzaware(start_at)
        if horizon_end is not None:
            _require_tzaware(horizon_end)
            if horizon_end <= start_at:
                raise ValueError("horizon_end must be after start_at")

        # Stable ordering: priority desc, then earliest_start asc, then due_at asc, then original order.
        indexed = list(enumerate(tasks))

        def sort_key(item: tuple[int, WorkOrderTask]) -> tuple[int, datetime, datetime, int]:
            idx, task = item
            es = task.earliest_start or start_at
            da = task.due_at or datetime.max.replace(tzinfo=timezone.utc)
            return (-_priority_rank(task.priority), es, da, idx)

        indexed.sort(key=sort_key)

        scheduled: list[ScheduledTask] = []
        unscheduled: list[UnscheduledTask] = []

        for _, task in indexed:
            if task.duration_minutes <= 0:
                raise ValueError("duration_minutes must be positive")
            if task.earliest_start is not None:
                _require_tzaware(task.earliest_start)
            if task.due_at is not None:
                _require_tzaware(task.due_at)

            # Rush gating
            if task.is_rush:
                req = self._rush_requests.get(task.id)
                if req is None or not req.approved:
                    unscheduled.append(
                        UnscheduledTask(
                            task_id=task.id,
                            station_id=task.station_id,
                            reason=ScheduleFailureReason.RUSH_NOT_APPROVED,
                            details="Rush task requires GM approval",
                        )
                    )
                    continue

            # Resource checks
            # (Checked at the candidate window time, but we can fail fast if providers are strictly boolean.)
            # We will re-check again at the chosen slot for correctness.

            slot = self._find_slot(task, start_at=start_at, horizon_end=horizon_end)
            if slot is None:
                unscheduled.append(
                    UnscheduledTask(
                        task_id=task.id,
                        station_id=task.station_id,
                        reason=ScheduleFailureReason.NO_CAPACITY_WITHIN_HORIZON,
                    )
                )
                continue

            slot_start, slot_end = slot

            if task.materials and not self._materials.materials_available(task.materials, slot_start, slot_end):
                unscheduled.append(
                    UnscheduledTask(
                        task_id=task.id,
                        station_id=task.station_id,
                        reason=ScheduleFailureReason.MATERIALS_UNAVAILABLE,
                    )
                )
                continue

            if task.tooling_ids and not self._tooling.tooling_available(task.tooling_ids, slot_start, slot_end):
                unscheduled.append(
                    UnscheduledTask(
                        task_id=task.id,
                        station_id=task.station_id,
                        reason=ScheduleFailureReason.TOOLING_UNAVAILABLE,
                    )
                )
                continue

            if task.skill_requirements and not self._skills.skills_available(task.skill_requirements, slot_start, slot_end):
                unscheduled.append(
                    UnscheduledTask(
                        task_id=task.id,
                        station_id=task.station_id,
                        reason=ScheduleFailureReason.SKILLS_UNAVAILABLE,
                    )
                )
                continue

            scheduled_task = ScheduledTask(
                id=task.id,
                station_id=task.station_id,
                start=slot_start,
                end=slot_end,
                priority=task.priority,
            )
            self._schedule_by_station.setdefault(task.station_id, []).append(scheduled_task)
            scheduled.append(scheduled_task)

        # Normalize station schedules to sorted order
        for station_id in list(self._schedule_by_station.keys()):
            self._schedule_by_station[station_id].sort(key=lambda s: s.start)

        return SchedulingResult(scheduled=scheduled, unscheduled=unscheduled)

    def _find_slot(
        self,
        task: WorkOrderTask,
        *,
        start_at: datetime,
        horizon_end: datetime | None,
    ) -> tuple[datetime, datetime] | None:
        station_id = task.station_id
        duration = timedelta(minutes=task.duration_minutes)

        earliest = max(start_at, task.earliest_start or start_at)

        # Occupied intervals include scheduled tasks plus maintenance windows.
        occupied: list[tuple[datetime, datetime]] = []
        for s in self._schedule_by_station.get(station_id, []):
            occupied.append((s.start, s.end))

        for w in self._calendar.get(station_id, []):
            if w.window_type == CalendarWindowType.MAINTENANCE:
                occupied.append((w.start, w.end))

        occupied.sort(key=lambda x: x[0])

        # Determine availability windows.
        shift_windows = [
            w
            for w in self._calendar.get(station_id, [])
            if w.window_type == CalendarWindowType.SHIFT
        ]
        shift_windows.sort(key=lambda w: w.start)

        # If no shift windows provided, treat the station as continuously available.
        if not shift_windows:
            end_limit = horizon_end or (earliest + timedelta(days=365))
            start = self._find_gap_in_window(
                window_start=earliest,
                window_end=end_limit,
                occupied=occupied,
                duration=duration,
            )
            if start is None:
                return None
            end = start + duration
            if horizon_end is not None and end > horizon_end:
                return None
            return start, end

        # Evaluate each shift window in order, starting no earlier than `earliest`.
        for shift in shift_windows:
            if shift.end <= earliest:
                continue
            window_start = max(shift.start, earliest)
            window_end = shift.end
            slot_start = self._find_gap_in_window(
                window_start=window_start,
                window_end=window_end,
                occupied=occupied,
                duration=duration,
            )
            if slot_start is None:
                continue
            slot_end = slot_start + duration
            if horizon_end is not None and slot_end > horizon_end:
                return None
            return slot_start, slot_end

        return None

    @staticmethod
    def _find_gap_in_window(
        *,
        window_start: datetime,
        window_end: datetime,
        occupied: list[tuple[datetime, datetime]],
        duration: timedelta,
    ) -> datetime | None:
        """Find the earliest start time within [window_start, window_end) with enough free space."""
        candidate = window_start

        for occ_start, occ_end in occupied:
            if occ_end <= candidate:
                continue
            if occ_start >= window_end:
                break

            if candidate + duration <= occ_start and candidate + duration <= window_end:
                return candidate

            if _overlaps(candidate, candidate + duration, occ_start, occ_end):
                candidate = max(candidate, occ_end)

            if candidate >= window_end:
                return None

        if candidate + duration <= window_end:
            return candidate
        return None

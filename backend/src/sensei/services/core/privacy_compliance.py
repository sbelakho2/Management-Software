"""Privacy & Compliance (Development Plan 21.7).

Implements:
- Attendance Evidence: secure logging of attendance scan events for labor law compliance.
- People Analytics Privacy: role-based masking of individual performance data
  (CEO/GM view vs. Peer view).
- Data Retention: automated deletion of sensitive personnel data according to
  legal retention schedules.

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class AttendanceEventType(str, Enum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    BREAK_START = "break_start"
    BREAK_END = "break_end"


class DataCategory(str, Enum):
    ATTENDANCE = "attendance"
    PERFORMANCE = "performance"
    PERSONAL = "personal"
    DISCIPLINARY = "disciplinary"
    HEALTH = "health"


_PRIVILEGED_VIEW_ROLES: set[str] = {"admin", "hr", "gm", "exec", "ceo"}
_RETENTION_WRITE_ROLES: set[str] = {"admin", "hr"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AttendanceEvent:
    id: UUID
    employee_id: UUID
    event_type: AttendanceEventType
    timestamp: datetime
    source: str  # e.g., "badge_reader", "terminal_123", "mobile_app"
    site_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetentionPolicy:
    id: UUID
    category: DataCategory
    retention_days: int
    description: str
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True)
class DeletionRun:
    id: UUID
    policy_id: UUID
    run_at: datetime
    records_deleted: int
    cutoff_date: date
    details: dict[str, Any] = field(default_factory=dict)


class PrivacyComplianceService:
    """In-memory attendance evidence + people analytics privacy + data retention."""

    def __init__(self) -> None:
        self._attendance: dict[UUID, AttendanceEvent] = {}
        self._retention_policies: dict[UUID, RetentionPolicy] = {}
        self._deletion_runs: list[DeletionRun] = []

        # Sample anonymized individual metrics keyed by employee_id.
        self._performance_data: dict[UUID, dict[str, Any]] = {}

    # ---- RBAC helpers ----

    def can_view_privileged(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_PRIVILEGED_VIEW_ROLES)) > 0

    def can_write_retention(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_RETENTION_WRITE_ROLES)) > 0

    # ---- Attendance evidence ----

    def record_attendance(
        self,
        *,
        employee_id: UUID,
        event_type: AttendanceEventType,
        source: str,
        timestamp: datetime | None = None,
        site_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AttendanceEvent:
        ev = AttendanceEvent(
            id=uuid4(),
            employee_id=employee_id,
            event_type=event_type,
            timestamp=timestamp or _utcnow(),
            source=source,
            site_id=site_id,
            metadata=dict(metadata or {}),
        )
        self._attendance[ev.id] = ev
        return ev

    def list_attendance(
        self,
        *,
        employee_id: UUID | None = None,
        start_after: datetime | None = None,
        end_before: datetime | None = None,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None = None,
    ) -> list[AttendanceEvent]:
        # Self or privileged can view.
        if employee_id is not None:
            if not (
                (actor_employee_id is not None and actor_employee_id == employee_id)
                or self.can_view_privileged(actor_roles=actor_roles)
            ):
                raise PermissionError("Not permitted to view attendance")
        elif not self.can_view_privileged(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view all attendance")

        result = list(self._attendance.values())
        if employee_id is not None:
            result = [e for e in result if e.employee_id == employee_id]
        if start_after is not None:
            result = [e for e in result if e.timestamp >= start_after]
        if end_before is not None:
            result = [e for e in result if e.timestamp <= end_before]
        result.sort(key=lambda e: e.timestamp)
        return result

    # ---- People analytics privacy ----

    def store_performance_metrics(
        self,
        employee_id: UUID,
        metrics: dict[str, Any],
    ) -> None:
        self._performance_data[employee_id] = dict(metrics)

    def get_performance_metrics(
        self,
        employee_id: UUID,
        *,
        actor_roles: Iterable[str],
        actor_employee_id: UUID | None = None,
    ) -> dict[str, Any]:
        if employee_id not in self._performance_data:
            raise KeyError("No performance data for employee")

        raw = self._performance_data[employee_id]

        # Privileged get full data.
        if self.can_view_privileged(actor_roles=actor_roles):
            return dict(raw)

        # Self gets limited data (no comparison ranking).
        if actor_employee_id is not None and actor_employee_id == employee_id:
            return {k: v for k, v in raw.items() if not k.startswith("_rank")}

        # Peer view: mask individual identifiers.
        return {"masked": True}

    # ---- Retention policies ----

    def create_retention_policy(
        self,
        *,
        category: DataCategory,
        retention_days: int,
        description: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> RetentionPolicy:
        if not self.can_write_retention(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create retention policies")
        if retention_days <= 0:
            raise ValueError("retention_days must be positive")

        policy = RetentionPolicy(
            id=uuid4(),
            category=category,
            retention_days=retention_days,
            description=description,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._retention_policies[policy.id] = policy
        return policy

    def list_retention_policies(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[RetentionPolicy]:
        if not self.can_view_privileged(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view retention policies")
        return sorted(self._retention_policies.values(), key=lambda p: p.category.value)

    def run_retention_cleanup(
        self,
        *,
        as_of: date,
        actor_roles: Iterable[str],
    ) -> list[DeletionRun]:
        if not self.can_write_retention(actor_roles=actor_roles):
            raise PermissionError("Not permitted to run retention cleanup")

        runs: list[DeletionRun] = []

        for policy in self._retention_policies.values():
            cutoff = as_of - timedelta(days=policy.retention_days)
            deleted_count = 0

            if policy.category == DataCategory.ATTENDANCE:
                to_delete = [
                    eid
                    for eid, ev in self._attendance.items()
                    if ev.timestamp.date() < cutoff
                ]
                for eid in to_delete:
                    del self._attendance[eid]
                deleted_count = len(to_delete)

            run = DeletionRun(
                id=uuid4(),
                policy_id=policy.id,
                run_at=_utcnow(),
                records_deleted=deleted_count,
                cutoff_date=cutoff,
            )
            self._deletion_runs.append(run)
            runs.append(run)

        return runs

    def list_deletion_runs(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[DeletionRun]:
        if not self.can_view_privileged(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view deletion runs")
        return list(self._deletion_runs)

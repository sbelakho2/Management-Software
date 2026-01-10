"""Business Continuity: Plant-Grade DR & Offline Resilience (Development Plan 21.12).

Implements:
- Store-and-Forward (Resilient Queuing): local priority queue for events during outages.
- Smart Conflict Resolution: Last-Write-Wins or Manual Review based on criticality.
- RTO/RPO Validation: Recovery Time/Point Objective tracking and validation.
- Restore Rehearsal: automated monthly restore validation in sandbox.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class EventPriority(str, Enum):
    CRITICAL = "critical"  # Andon, safety events.
    HIGH = "high"  # Work order completions.
    NORMAL = "normal"  # Quality events.
    LOW = "low"  # Log entries.


class ConflictResolutionStrategy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    MANUAL_REVIEW = "manual_review"
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"


class QueuedEventStatus(str, Enum):
    QUEUED = "queued"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    RESOLVED = "resolved"
    FAILED = "failed"


class RehearsalStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


_DR_ADMIN_ROLES: set[str] = {"admin", "it", "ops", "gm"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class QueuedEvent:
    id: UUID
    device_id: str
    entity_type: str
    entity_id: UUID | None
    operation: str
    priority: EventPriority
    payload: dict[str, Any]
    client_timestamp: datetime
    status: QueuedEventStatus
    queued_at: datetime
    synced_at: datetime | None = None
    conflict_details: dict[str, Any] | None = None
    resolution_strategy: ConflictResolutionStrategy | None = None


@dataclass(frozen=True)
class CriticalityRule:
    id: UUID
    entity_type: str
    resolution_strategy: ConflictResolutionStrategy


@dataclass
class RTORPOConfig:
    id: UUID
    rto_minutes: int  # Recovery Time Objective.
    rpo_minutes: int  # Recovery Point Objective.
    last_validated_at: datetime | None
    validation_passed: bool | None
    created_at: datetime
    updated_by: UUID


@dataclass
class RestoreRehearsal:
    id: UUID
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    status: RehearsalStatus
    rto_achieved_minutes: int | None
    rpo_achieved_minutes: int | None
    notes: str | None
    created_by: UUID


class BusinessContinuityService:
    """In-memory business continuity and DR service."""

    def __init__(self) -> None:
        self._event_queue: dict[UUID, QueuedEvent] = {}
        self._criticality_rules: dict[str, CriticalityRule] = {}  # Keyed by entity_type.
        self._rto_rpo_config: RTORPOConfig | None = None
        self._rehearsals: dict[UUID, RestoreRehearsal] = {}

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_DR_ADMIN_ROLES)) > 0

    # ---- Store-and-Forward Queue ----

    def queue_event(
        self,
        *,
        device_id: str,
        entity_type: str,
        entity_id: UUID | None,
        operation: str,
        priority: EventPriority,
        payload: dict[str, Any],
        client_timestamp: datetime,
    ) -> QueuedEvent:
        """Queue an event from an offline device."""
        event = QueuedEvent(
            id=uuid4(),
            device_id=device_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            priority=priority,
            payload=payload,
            client_timestamp=client_timestamp,
            status=QueuedEventStatus.QUEUED,
            queued_at=_utcnow(),
        )
        self._event_queue[event.id] = event
        return event

    def get_pending_events(
        self,
        *,
        device_id: str | None = None,
        priority: EventPriority | None = None,
    ) -> list[QueuedEvent]:
        result = [
            e for e in self._event_queue.values()
            if e.status == QueuedEventStatus.QUEUED
        ]
        if device_id:
            result = [e for e in result if e.device_id == device_id]
        if priority:
            result = [e for e in result if e.priority == priority]

        # Sort by priority (critical first), then by client timestamp.
        priority_order = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }
        result.sort(key=lambda e: (priority_order[e.priority], e.client_timestamp))
        return result

    def mark_synced(self, event_id: UUID) -> QueuedEvent:
        if event_id not in self._event_queue:
            raise KeyError("Event not found")

        event = self._event_queue[event_id]
        event.status = QueuedEventStatus.SYNCED
        event.synced_at = _utcnow()
        return event

    def mark_conflict(
        self,
        event_id: UUID,
        *,
        conflict_details: dict[str, Any],
    ) -> QueuedEvent:
        if event_id not in self._event_queue:
            raise KeyError("Event not found")

        event = self._event_queue[event_id]
        event.status = QueuedEventStatus.CONFLICT
        event.conflict_details = conflict_details

        # Apply resolution strategy from rules.
        rule = self._criticality_rules.get(event.entity_type)
        if rule:
            event.resolution_strategy = rule.resolution_strategy
        else:
            event.resolution_strategy = ConflictResolutionStrategy.MANUAL_REVIEW

        return event

    def resolve_conflict(
        self,
        event_id: UUID,
        *,
        resolution: ConflictResolutionStrategy,
        actor_roles: Iterable[str],
    ) -> QueuedEvent:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to resolve conflicts")
        if event_id not in self._event_queue:
            raise KeyError("Event not found")

        event = self._event_queue[event_id]
        event.resolution_strategy = resolution
        event.status = QueuedEventStatus.RESOLVED
        return event

    def get_conflicts(self) -> list[QueuedEvent]:
        return [
            e for e in self._event_queue.values()
            if e.status == QueuedEventStatus.CONFLICT
        ]

    # ---- Criticality Rules ----

    def set_criticality_rule(
        self,
        *,
        entity_type: str,
        resolution_strategy: ConflictResolutionStrategy,
        actor_roles: Iterable[str],
    ) -> CriticalityRule:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to set criticality rules")

        rule = CriticalityRule(
            id=uuid4(),
            entity_type=entity_type,
            resolution_strategy=resolution_strategy,
        )
        self._criticality_rules[entity_type] = rule
        return rule

    def get_criticality_rule(self, entity_type: str) -> CriticalityRule | None:
        return self._criticality_rules.get(entity_type)

    # ---- RTO/RPO Validation ----

    def set_rto_rpo_targets(
        self,
        *,
        rto_minutes: int,
        rpo_minutes: int,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> RTORPOConfig:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to set RTO/RPO targets")

        config = RTORPOConfig(
            id=uuid4(),
            rto_minutes=rto_minutes,
            rpo_minutes=rpo_minutes,
            last_validated_at=None,
            validation_passed=None,
            created_at=_utcnow(),
            updated_by=actor_user_id,
        )
        self._rto_rpo_config = config
        return config

    def get_rto_rpo_config(self) -> RTORPOConfig | None:
        return self._rto_rpo_config

    def validate_rto_rpo(
        self,
        *,
        achieved_rto_minutes: int,
        achieved_rpo_minutes: int,
        actor_roles: Iterable[str],
    ) -> dict[str, Any]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to validate RTO/RPO")
        if not self._rto_rpo_config:
            raise ValueError("RTO/RPO targets not configured")

        config = self._rto_rpo_config
        rto_passed = achieved_rto_minutes <= config.rto_minutes
        rpo_passed = achieved_rpo_minutes <= config.rpo_minutes
        overall_passed = rto_passed and rpo_passed

        config.last_validated_at = _utcnow()
        config.validation_passed = overall_passed

        return {
            "rto_target": config.rto_minutes,
            "rto_achieved": achieved_rto_minutes,
            "rto_passed": rto_passed,
            "rpo_target": config.rpo_minutes,
            "rpo_achieved": achieved_rpo_minutes,
            "rpo_passed": rpo_passed,
            "overall_passed": overall_passed,
        }

    # ---- Restore Rehearsal ----

    def schedule_rehearsal(
        self,
        *,
        scheduled_at: datetime,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> RestoreRehearsal:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to schedule rehearsals")

        rehearsal = RestoreRehearsal(
            id=uuid4(),
            scheduled_at=scheduled_at,
            started_at=None,
            completed_at=None,
            status=RehearsalStatus.SCHEDULED,
            rto_achieved_minutes=None,
            rpo_achieved_minutes=None,
            notes=None,
            created_by=actor_user_id,
        )
        self._rehearsals[rehearsal.id] = rehearsal
        return rehearsal

    def start_rehearsal(
        self,
        rehearsal_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> RestoreRehearsal:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to start rehearsals")
        if rehearsal_id not in self._rehearsals:
            raise KeyError("Rehearsal not found")

        rehearsal = self._rehearsals[rehearsal_id]
        rehearsal.status = RehearsalStatus.RUNNING
        rehearsal.started_at = _utcnow()
        return rehearsal

    def complete_rehearsal(
        self,
        rehearsal_id: UUID,
        *,
        rto_achieved_minutes: int,
        rpo_achieved_minutes: int,
        notes: str | None,
        actor_roles: Iterable[str],
    ) -> RestoreRehearsal:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to complete rehearsals")
        if rehearsal_id not in self._rehearsals:
            raise KeyError("Rehearsal not found")

        rehearsal = self._rehearsals[rehearsal_id]
        rehearsal.completed_at = _utcnow()
        rehearsal.rto_achieved_minutes = rto_achieved_minutes
        rehearsal.rpo_achieved_minutes = rpo_achieved_minutes
        rehearsal.notes = notes

        # Determine pass/fail based on current config.
        if self._rto_rpo_config:
            passed = (
                rto_achieved_minutes <= self._rto_rpo_config.rto_minutes
                and rpo_achieved_minutes <= self._rto_rpo_config.rpo_minutes
            )
            rehearsal.status = RehearsalStatus.PASSED if passed else RehearsalStatus.FAILED
        else:
            rehearsal.status = RehearsalStatus.PASSED

        return rehearsal

    def list_rehearsals(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[RestoreRehearsal]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view rehearsals")

        result = list(self._rehearsals.values())
        result.sort(key=lambda r: r.scheduled_at, reverse=True)
        return result

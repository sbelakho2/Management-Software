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
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.models.business_continuity import (
    QueuedEvent as QueuedEventModel,
    CriticalityRule as CriticalityRuleModel,
    RTORPOConfig as RTORPOConfigModel,
    RestoreRehearsal as RestoreRehearsalModel,
)


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


class AsyncBusinessContinuityService:
    """Production business continuity and DR service using SQLAlchemy."""

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_DR_ADMIN_ROLES)) > 0

    # ---- Store-and-Forward Queue ----

    async def queue_event(
        self,
        db: AsyncSession,
        *,
        device_id: str,
        entity_type: str,
        entity_id: UUID | None,
        operation: str,
        priority: EventPriority,
        payload: dict[str, Any],
        client_timestamp: datetime,
    ) -> QueuedEventModel:
        """Queue an event from an offline device."""
        event = QueuedEventModel(
            id=uuid4(),
            device_id=device_id,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            operation=operation,
            priority=priority.value,
            payload=payload,
            client_timestamp=client_timestamp,
            status=QueuedEventStatus.QUEUED.value,
        )
        db.add(event)
        await db.flush()
        return event

    async def get_pending_events(
        self,
        db: AsyncSession,
        *,
        device_id: str | None = None,
        priority: EventPriority | None = None,
    ) -> list[QueuedEventModel]:
        stmt = select(QueuedEventModel).where(QueuedEventModel.status == QueuedEventStatus.QUEUED.value)
        if device_id:
            stmt = stmt.where(QueuedEventModel.device_id == device_id)
        if priority:
            stmt = stmt.where(QueuedEventModel.priority == priority.value)

        # Sort by priority (critical first), then by client timestamp.
        # Note: priority values are strings, so we might need a mapping in SQL if we wanted ORDER BY priority
        # But for simulation matching, we'll fetch and sort in memory if needed or just use multiple queries.
        # Let's use simple ORDER BY if priority was numeric, but it's string.
        
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        priority_order = {
            EventPriority.CRITICAL.value: 0,
            EventPriority.HIGH.value: 1,
            EventPriority.NORMAL.value: 2,
            EventPriority.LOW.value: 3,
        }
        events.sort(key=lambda e: (priority_order.get(e.priority, 9), e.client_timestamp))
        return events

    async def mark_synced(self, db: AsyncSession, event_id: UUID) -> QueuedEventModel:
        stmt = select(QueuedEventModel).where(QueuedEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise KeyError("Event not found")

        event.status = QueuedEventStatus.SYNCED.value
        event.synced_at = _utcnow()
        await db.flush()
        return event

    async def mark_conflict(
        self,
        db: AsyncSession,
        event_id: UUID,
        *,
        conflict_details: dict[str, Any],
    ) -> QueuedEventModel:
        stmt = select(QueuedEventModel).where(QueuedEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise KeyError("Event not found")

        event.status = QueuedEventStatus.CONFLICT.value
        event.conflict_details = conflict_details

        # Apply resolution strategy from rules.
        rule_stmt = select(CriticalityRuleModel).where(CriticalityRuleModel.entity_type == event.entity_type)
        rule_result = await db.execute(rule_stmt)
        rule = rule_result.scalar_one_or_none()
        
        if rule:
            event.resolution_strategy = rule.resolution_strategy
        else:
            event.resolution_strategy = ConflictResolutionStrategy.MANUAL_REVIEW.value

        await db.flush()
        return event

    async def resolve_conflict(
        self,
        db: AsyncSession,
        event_id: UUID,
        *,
        resolution: ConflictResolutionStrategy,
        actor_roles: Iterable[str],
    ) -> QueuedEventModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to resolve conflicts")
        
        stmt = select(QueuedEventModel).where(QueuedEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise KeyError("Event not found")

        event.resolution_strategy = resolution.value
        event.status = QueuedEventStatus.RESOLVED.value
        await db.flush()
        return event

    async def get_conflicts(self, db: AsyncSession) -> list[QueuedEventModel]:
        stmt = select(QueuedEventModel).where(QueuedEventModel.status == QueuedEventStatus.CONFLICT.value)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Criticality Rules ----

    async def set_criticality_rule(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        resolution_strategy: ConflictResolutionStrategy,
        actor_roles: Iterable[str],
    ) -> CriticalityRuleModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to set criticality rules")

        stmt = select(CriticalityRuleModel).where(CriticalityRuleModel.entity_type == entity_type)
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()
        
        if not rule:
            rule = CriticalityRuleModel(
                id=uuid4(),
                entity_type=entity_type,
            )
            db.add(rule)
        
        rule.resolution_strategy = resolution_strategy.value
        await db.flush()
        return rule

    async def get_criticality_rule(self, db: AsyncSession, entity_type: str) -> CriticalityRuleModel | None:
        stmt = select(CriticalityRuleModel).where(CriticalityRuleModel.entity_type == entity_type)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ---- RTO/RPO Validation ----

    async def set_rto_rpo_targets(
        self,
        db: AsyncSession,
        *,
        rto_minutes: int,
        rpo_minutes: int,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> RTORPOConfigModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to set RTO/RPO targets")

        # Get latest or create
        stmt = select(RTORPOConfigModel).order_by(RTORPOConfigModel.created_at.desc())
        result = await db.execute(stmt)
        config = result.scalars().first()
        
        if not config:
            config = RTORPOConfigModel(id=uuid4())
            db.add(config)
            
        config.rto_minutes = rto_minutes
        config.rpo_minutes = rpo_minutes
        config.updated_by_id = actor_user_id
        
        await db.flush()
        return config

    async def get_rto_rpo_config(self, db: AsyncSession) -> RTORPOConfigModel | None:
        stmt = select(RTORPOConfigModel).order_by(RTORPOConfigModel.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().first()

    async def validate_rto_rpo(
        self,
        db: AsyncSession,
        *,
        achieved_rto_minutes: int,
        achieved_rpo_minutes: int,
        actor_roles: Iterable[str],
    ) -> dict[str, Any]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to validate RTO/RPO")
        
        config = await self.get_rto_rpo_config(db)
        if not config:
            raise ValueError("RTO/RPO targets not configured")

        rto_passed = achieved_rto_minutes <= config.rto_minutes
        rpo_passed = achieved_rpo_minutes <= config.rpo_minutes
        overall_passed = rto_passed and rpo_passed

        config.last_validated_at = _utcnow()
        config.validation_passed = overall_passed
        await db.flush()

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

    async def schedule_rehearsal(
        self,
        db: AsyncSession,
        *,
        scheduled_at: datetime,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> RestoreRehearsalModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to schedule rehearsals")

        rehearsal = RestoreRehearsalModel(
            id=uuid4(),
            scheduled_at=scheduled_at,
            status=RehearsalStatus.SCHEDULED.value,
            created_by_id=actor_user_id,
        )
        db.add(rehearsal)
        await db.flush()
        return rehearsal

    async def start_rehearsal(
        self,
        db: AsyncSession,
        rehearsal_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> RestoreRehearsalModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to start rehearsals")
        
        stmt = select(RestoreRehearsalModel).where(RestoreRehearsalModel.id == rehearsal_id)
        result = await db.execute(stmt)
        rehearsal = result.scalar_one_or_none()
        if not rehearsal:
            raise KeyError("Rehearsal not found")

        rehearsal.status = RehearsalStatus.RUNNING.value
        rehearsal.started_at = _utcnow()
        await db.flush()
        return rehearsal

    async def complete_rehearsal(
        self,
        db: AsyncSession,
        rehearsal_id: UUID,
        *,
        rto_achieved_minutes: int,
        rpo_achieved_minutes: int,
        notes: str | None,
        actor_roles: Iterable[str],
    ) -> RestoreRehearsalModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to complete rehearsals")
        
        stmt = select(RestoreRehearsalModel).where(RestoreRehearsalModel.id == rehearsal_id)
        result = await db.execute(stmt)
        rehearsal = result.scalar_one_or_none()
        if not rehearsal:
            raise KeyError("Rehearsal not found")

        rehearsal.completed_at = _utcnow()
        rehearsal.rto_achieved_minutes = rto_achieved_minutes
        rehearsal.rpo_achieved_minutes = rpo_achieved_minutes
        rehearsal.notes = notes

        # Determine pass/fail based on current config.
        config = await self.get_rto_rpo_config(db)
        if config:
            passed = (
                rto_achieved_minutes <= config.rto_minutes
                and rpo_achieved_minutes <= config.rpo_minutes
            )
            rehearsal.status = RehearsalStatus.PASSED.value if passed else RehearsalStatus.FAILED.value
        else:
            rehearsal.status = RehearsalStatus.PASSED.value

        await db.flush()
        return rehearsal

    async def list_rehearsals(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> list[RestoreRehearsalModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view rehearsals")

        stmt = select(RestoreRehearsalModel).order_by(RestoreRehearsalModel.scheduled_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())


class BusinessContinuityService:
    """In-memory Business Continuity service for sync workflows and tests."""

    def __init__(self):
        self._events: dict[UUID, QueuedEvent] = {}
        self._rules: dict[str, CriticalityRule] = {}
        self._rto_rpo: RTORPOConfig | None = None
        self._rehearsals: dict[UUID, RestoreRehearsal] = {}

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_DR_ADMIN_ROLES)) > 0

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
        self._events[event.id] = event
        return event

    def get_pending_events(
        self,
        *,
        device_id: str | None = None,
        priority: EventPriority | None = None,
    ) -> list[QueuedEvent]:
        events = [e for e in self._events.values() if e.status == QueuedEventStatus.QUEUED]
        if device_id:
            events = [e for e in events if e.device_id == device_id]
        if priority:
            events = [e for e in events if e.priority == priority]

        priority_order = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }
        events.sort(key=lambda e: (priority_order.get(e.priority, 9), e.client_timestamp))
        return events

    def mark_synced(self, event_id: UUID) -> QueuedEvent:
        event = self._events.get(event_id)
        if not event:
            raise KeyError("Event not found")
        event.status = QueuedEventStatus.SYNCED
        event.synced_at = _utcnow()
        return event

    def mark_conflict(self, event_id: UUID, *, conflict_details: dict[str, Any]) -> QueuedEvent:
        event = self._events.get(event_id)
        if not event:
            raise KeyError("Event not found")
        event.status = QueuedEventStatus.CONFLICT
        event.conflict_details = conflict_details
        rule = self._rules.get(event.entity_type)
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
        event = self._events.get(event_id)
        if not event:
            raise KeyError("Event not found")
        event.resolution_strategy = resolution
        event.status = QueuedEventStatus.RESOLVED
        return event

    def get_conflicts(self) -> list[QueuedEvent]:
        return [e for e in self._events.values() if e.status == QueuedEventStatus.CONFLICT]

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
        self._rules[entity_type] = rule
        return rule

    def get_criticality_rule(self, entity_type: str) -> CriticalityRule | None:
        return self._rules.get(entity_type)

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
        now = _utcnow()
        if self._rto_rpo is None:
            self._rto_rpo = RTORPOConfig(
                id=uuid4(),
                rto_minutes=rto_minutes,
                rpo_minutes=rpo_minutes,
                last_validated_at=None,
                validation_passed=None,
                created_at=now,
                updated_by=actor_user_id,
            )
        else:
            self._rto_rpo.rto_minutes = rto_minutes
            self._rto_rpo.rpo_minutes = rpo_minutes
            self._rto_rpo.updated_by = actor_user_id
        return self._rto_rpo

    def get_rto_rpo_config(self) -> RTORPOConfig | None:
        return self._rto_rpo

    def validate_rto_rpo(
        self,
        *,
        achieved_rto_minutes: int,
        achieved_rpo_minutes: int,
        actor_roles: Iterable[str],
    ) -> dict[str, Any]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to validate RTO/RPO")
        if not self._rto_rpo:
            raise ValueError("RTO/RPO targets not configured")

        rto_passed = achieved_rto_minutes <= self._rto_rpo.rto_minutes
        rpo_passed = achieved_rpo_minutes <= self._rto_rpo.rpo_minutes
        overall_passed = rto_passed and rpo_passed

        self._rto_rpo.last_validated_at = _utcnow()
        self._rto_rpo.validation_passed = overall_passed

        return {
            "rto_target": self._rto_rpo.rto_minutes,
            "rto_achieved": achieved_rto_minutes,
            "rto_passed": rto_passed,
            "rpo_target": self._rto_rpo.rpo_minutes,
            "rpo_achieved": achieved_rpo_minutes,
            "rpo_passed": rpo_passed,
            "overall_passed": overall_passed,
        }

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
        rehearsal = self._rehearsals.get(rehearsal_id)
        if not rehearsal:
            raise KeyError("Rehearsal not found")
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
        rehearsal = self._rehearsals.get(rehearsal_id)
        if not rehearsal:
            raise KeyError("Rehearsal not found")

        rehearsal.completed_at = _utcnow()
        rehearsal.rto_achieved_minutes = rto_achieved_minutes
        rehearsal.rpo_achieved_minutes = rpo_achieved_minutes
        rehearsal.notes = notes

        if self._rto_rpo:
            passed = (
                rto_achieved_minutes <= self._rto_rpo.rto_minutes
                and rpo_achieved_minutes <= self._rto_rpo.rpo_minutes
            )
            rehearsal.status = RehearsalStatus.PASSED if passed else RehearsalStatus.FAILED
        else:
            rehearsal.status = RehearsalStatus.PASSED
        return rehearsal

    def list_rehearsals(self, *, actor_roles: Iterable[str]) -> list[RestoreRehearsal]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view rehearsals")
        rehearsals = list(self._rehearsals.values())
        rehearsals.sort(key=lambda r: r.scheduled_at, reverse=True)
        return rehearsals

"""Tests for Business Continuity (DR & Offline Resilience) service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.business_continuity import (
    BusinessContinuityService,
    ConflictResolutionStrategy,
    EventPriority,
    QueuedEvent,
    QueuedEventStatus,
    RehearsalStatus,
    RestoreRehearsal,
    RTORPOConfig,
)


@pytest.fixture
def svc() -> BusinessContinuityService:
    return BusinessContinuityService()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ADMIN_ROLES = ("admin",)
IT_ROLES = ("it",)
VIEWER_ROLES = ("viewer",)


class TestStoreAndForward:
    def test_queue_and_get_pending(self, svc: BusinessContinuityService) -> None:
        event = svc.queue_event(
            device_id="KIOSK-01",
            entity_type="andon_event",
            entity_id=uuid4(),
            operation="create",
            priority=EventPriority.CRITICAL,
            payload={"station": "A1", "reason": "Machine down"},
            client_timestamp=_utcnow() - timedelta(minutes=5),
        )

        assert isinstance(event, QueuedEvent)
        assert event.status == QueuedEventStatus.QUEUED

        pending = svc.get_pending_events(device_id="KIOSK-01")
        assert len(pending) == 1

    def test_priority_ordering(self, svc: BusinessContinuityService) -> None:
        base_time = _utcnow()

        svc.queue_event(
            device_id="D1",
            entity_type="log",
            entity_id=None,
            operation="create",
            priority=EventPriority.LOW,
            payload={},
            client_timestamp=base_time,
        )
        svc.queue_event(
            device_id="D1",
            entity_type="andon",
            entity_id=None,
            operation="create",
            priority=EventPriority.CRITICAL,
            payload={},
            client_timestamp=base_time + timedelta(seconds=10),
        )
        svc.queue_event(
            device_id="D1",
            entity_type="work_order",
            entity_id=None,
            operation="update",
            priority=EventPriority.HIGH,
            payload={},
            client_timestamp=base_time + timedelta(seconds=5),
        )

        pending = svc.get_pending_events()
        priorities = [e.priority for e in pending]
        assert priorities == [
            EventPriority.CRITICAL,
            EventPriority.HIGH,
            EventPriority.LOW,
        ]

    def test_mark_synced(self, svc: BusinessContinuityService) -> None:
        event = svc.queue_event(
            device_id="D2",
            entity_type="quality",
            entity_id=uuid4(),
            operation="create",
            priority=EventPriority.NORMAL,
            payload={},
            client_timestamp=_utcnow(),
        )

        synced = svc.mark_synced(event.id)
        assert synced.status == QueuedEventStatus.SYNCED
        assert synced.synced_at is not None

        pending = svc.get_pending_events()
        assert len(pending) == 0


class TestConflictResolution:
    def test_mark_conflict_with_auto_strategy(self, svc: BusinessContinuityService) -> None:
        # Set rule for work_order to use last-write-wins.
        svc.set_criticality_rule(
            entity_type="work_order",
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
            actor_roles=ADMIN_ROLES,
        )

        event = svc.queue_event(
            device_id="D3",
            entity_type="work_order",
            entity_id=uuid4(),
            operation="update",
            priority=EventPriority.HIGH,
            payload={"status": "completed"},
            client_timestamp=_utcnow(),
        )

        conflict = svc.mark_conflict(
            event.id,
            conflict_details={"server_version": 5, "client_version": 4},
        )

        assert conflict.status == QueuedEventStatus.CONFLICT
        assert conflict.resolution_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS

    def test_manual_review_default(self, svc: BusinessContinuityService) -> None:
        event = svc.queue_event(
            device_id="D4",
            entity_type="unknown_type",
            entity_id=uuid4(),
            operation="create",
            priority=EventPriority.NORMAL,
            payload={},
            client_timestamp=_utcnow(),
        )

        conflict = svc.mark_conflict(event.id, conflict_details={})
        assert conflict.resolution_strategy == ConflictResolutionStrategy.MANUAL_REVIEW

    def test_resolve_conflict(self, svc: BusinessContinuityService) -> None:
        event = svc.queue_event(
            device_id="D5",
            entity_type="quality_event",
            entity_id=uuid4(),
            operation="update",
            priority=EventPriority.NORMAL,
            payload={},
            client_timestamp=_utcnow(),
        )
        svc.mark_conflict(event.id, conflict_details={"reason": "version mismatch"})

        resolved = svc.resolve_conflict(
            event.id,
            resolution=ConflictResolutionStrategy.CLIENT_WINS,
            actor_roles=ADMIN_ROLES,
        )
        assert resolved.status == QueuedEventStatus.RESOLVED


class TestRTORPO:
    def test_set_and_validate_targets(self, svc: BusinessContinuityService) -> None:
        config = svc.set_rto_rpo_targets(
            rto_minutes=60,
            rpo_minutes=5,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(config, RTORPOConfig)
        assert config.rto_minutes == 60
        assert config.rpo_minutes == 5

        # Validate with passing values.
        result = svc.validate_rto_rpo(
            achieved_rto_minutes=45,
            achieved_rpo_minutes=3,
            actor_roles=IT_ROLES,
        )
        assert result["overall_passed"] is True

        # Validate with failing RTO.
        result2 = svc.validate_rto_rpo(
            achieved_rto_minutes=90,
            achieved_rpo_minutes=3,
            actor_roles=ADMIN_ROLES,
        )
        assert result2["rto_passed"] is False
        assert result2["overall_passed"] is False


class TestRestoreRehearsal:
    def test_schedule_and_complete_rehearsal(self, svc: BusinessContinuityService) -> None:
        svc.set_rto_rpo_targets(
            rto_minutes=60,
            rpo_minutes=5,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        rehearsal = svc.schedule_rehearsal(
            scheduled_at=_utcnow() + timedelta(days=30),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert isinstance(rehearsal, RestoreRehearsal)
        assert rehearsal.status == RehearsalStatus.SCHEDULED

        svc.start_rehearsal(rehearsal.id, actor_roles=ADMIN_ROLES)
        assert svc._rehearsals[rehearsal.id].status == RehearsalStatus.RUNNING

        completed = svc.complete_rehearsal(
            rehearsal.id,
            rto_achieved_minutes=50,
            rpo_achieved_minutes=4,
            notes="Restore from S3 completed successfully",
            actor_roles=ADMIN_ROLES,
        )
        assert completed.status == RehearsalStatus.PASSED

    def test_rehearsal_fails_if_targets_exceeded(self, svc: BusinessContinuityService) -> None:
        svc.set_rto_rpo_targets(
            rto_minutes=30,
            rpo_minutes=5,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        rehearsal = svc.schedule_rehearsal(
            scheduled_at=_utcnow(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.start_rehearsal(rehearsal.id, actor_roles=ADMIN_ROLES)

        completed = svc.complete_rehearsal(
            rehearsal.id,
            rto_achieved_minutes=45,
            rpo_achieved_minutes=10,
            notes="Issues with restore",
            actor_roles=ADMIN_ROLES,
        )
        assert completed.status == RehearsalStatus.FAILED

    def test_rehearsal_requires_role(self, svc: BusinessContinuityService) -> None:
        with pytest.raises(PermissionError):
            svc.schedule_rehearsal(
                scheduled_at=_utcnow(),
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

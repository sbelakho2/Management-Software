"""Tests for Shift Handover & Tier Meeting System (Development Plan 21.6)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.production.shift_handover_tier_meetings import (
    ShiftHandoverTierMeetingService,
    HandoverSeverity,
    TierLevel,
)

from sensei.services.production.shift_handover_tier_meetings import (  # noqa: E402
    AgendaItemType,
)

from sensei.services.ops.today_screen import (  # noqa: E402
    get_today_screen_service,
    reset_today_screen_service,
    CommitmentType,
)


@pytest.fixture
def svc() -> ShiftHandoverTierMeetingService:
    return ShiftHandoverTierMeetingService()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 1, 9, 7, 0, tzinfo=timezone.utc)


def test_create_and_list_unacknowledged_notes(svc: ShiftHandoverTierMeetingService, now: datetime) -> None:
    svc.create_handover_note(
        note_id="n1",
        station_id="ST-10",
        created_by="op-a",
        created_at=now,
        work_order_id="WO-1",
        severity=HandoverSeverity.WARNING,
        safety="Guard missing on press",
        notes="Notify maintenance",
        tags=["safety"],
    )

    notes = svc.list_handover_notes(station_id="ST-10", include_acknowledged=False)
    assert len(notes) == 1
    assert notes[0].id == "n1"
    assert notes[0].acknowledged is False


def test_acknowledge_note_hides_when_filtered(svc: ShiftHandoverTierMeetingService, now: datetime) -> None:
    svc.create_handover_note(note_id="n1", station_id="ST-10", created_by="op-a", created_at=now)
    svc.acknowledge_handover_note("n1", acknowledged_by="op-b", acknowledged_at=now + timedelta(minutes=5))

    notes = svc.list_handover_notes(station_id="ST-10", include_acknowledged=False)
    assert notes == []


def test_payloads_can_surface_on_today_screen(svc: ShiftHandoverTierMeetingService, now: datetime) -> None:
    reset_today_screen_service()
    today = get_today_screen_service()

    incoming_user_id = str(uuid4())
    incoming_uuid = uuid4()

    svc.create_handover_note(
        note_id="n1",
        station_id="ST-10",
        created_by="op-a",
        created_at=now,
        work_order_id="WO-1",
        severity=HandoverSeverity.CRITICAL,
        quality="Suspect dimension drift",
        notes="Hold next 10 pcs for inspection",
    )

    payloads = svc.build_today_shift_handoff_commitment_payloads(
        incoming_user_id=incoming_user_id,
        assigned_station_ids=["ST-10"],
        since=now - timedelta(hours=1),
    )
    assert len(payloads) == 1

    p = payloads[0]
    assert p["commitment_type"] == "shift_handoff"

    # Surface by creating a Today screen commitment for the incoming operator.
    today.add_commitment(
        title=p["title"],
        commitment_type=CommitmentType.SHIFT_HANDOFF,
        due_date=date.today(),
        description=p["description"],
        owner_id=incoming_uuid,
        owner_name="Incoming Operator",
        entity_type=p["entity_type"],
        entity_id=None,
    )

    data = today.get_today_screen(user_id=incoming_uuid, user_name="Incoming Operator")
    assert any(c.commitment_type == CommitmentType.SHIFT_HANDOFF for c in data.todays_commitments)


def test_generate_agenda_from_red_metrics_and_open_andons(svc: ShiftHandoverTierMeetingService, now: datetime) -> None:
    red_metrics = [
        {"metric_id": "q1", "category": "quality", "name": "FPY", "status": "red", "description": "Below target"},
        {"metric_id": "d1", "category": "delivery", "name": "OTD", "status": "green"},
    ]
    open_andons = [
        {"id": "a1", "station_id": "ST-10", "andon_type": "machine", "symptom": "Spindle vibration", "status": "open", "severity": "critical"},
        {"id": "a2", "station_id": "ST-11", "andon_type": "quality", "symptom": "Scratch", "status": "resolved", "severity": "warning"},
    ]

    agenda = svc.generate_tier_meeting_agenda(
        agenda_id="ag1",
        tier=TierLevel.TIER_1,
        station_id="ST-10",
        red_sqdcp_items=red_metrics,
        open_andon_events=open_andons,
        generated_at=now,
    )

    assert agenda.tier == TierLevel.TIER_1
    assert len(agenda.items) == 2  # one red metric + one open andon
    assert {i.item_type for i in agenda.items} == {AgendaItemType.SQDCP_RED, AgendaItemType.ANDON_OPEN}

    # Escalation chain Tier1 -> Tier2 -> Obeya
    for item in agenda.items:
        assert item.escalation_chain[:2] == [TierLevel.TIER_2, TierLevel.OBEYA]


def test_escalation_creates_derived_item(svc: ShiftHandoverTierMeetingService, now: datetime) -> None:
    agenda = svc.generate_tier_meeting_agenda(
        agenda_id="ag1",
        tier=TierLevel.TIER_1,
        station_id="ST-10",
        red_sqdcp_items=[{"metric_id": "q1", "category": "quality", "name": "FPY", "status": "red"}],
        open_andon_events=[],
        generated_at=now,
    )

    item_id = agenda.items[0].id
    ev = svc.escalate_agenda_item(
        item_id,
        from_tier=TierLevel.TIER_1,
        escalated_by="leader-1",
        reason="Needs cross-cell support",
        escalated_at=now + timedelta(minutes=10),
    )

    assert ev.from_tier == TierLevel.TIER_1
    assert ev.to_tier == TierLevel.TIER_2
    assert len(svc.list_escalations()) == 1

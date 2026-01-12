"""Shift Handover & Tier Meeting System (Development Plan 21.6).

Implements:
- Digital handover notes tied to Stations and Work Orders
- Tier meeting agenda templates auto-generated from SQDCP red items + open Andon events
- Escalation pathing Tier 1 (Station) -> Tier 2 (Cell) -> Obeya (Site)

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class HandoverSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TierLevel(str, Enum):
    TIER_1 = "tier_1"  # Station
    TIER_2 = "tier_2"  # Cell
    OBEYA = "obeya"  # Site


class AgendaItemType(str, Enum):
    SQDCP_RED = "sqdcp_red"
    ANDON_OPEN = "andon_open"
    FOLLOW_UP = "follow_up"


@dataclass(frozen=True)
class ShiftHandoverNote:
    id: str
    station_id: str
    created_at: datetime
    created_by: str

    work_order_id: str | None = None
    severity: HandoverSeverity = HandoverSeverity.INFO

    # Structured fields (kept simple and explicit)
    safety: str = ""
    quality: str = ""
    delivery: str = ""
    cost: str = ""
    people: str = ""
    notes: str = ""

    tags: list[str] = field(default_factory=list)

    # Acknowledgement
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


@dataclass(frozen=True)
class TierMeetingAgendaItem:
    id: str
    tier: TierLevel
    item_type: AgendaItemType
    title: str
    description: str
    severity: HandoverSeverity

    # Link back to originating system objects
    source_type: str
    source_id: str

    # Unified escalation chain
    escalation_chain: list[TierLevel]

    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TierMeetingAgenda:
    id: str
    tier: TierLevel
    station_id: str | None
    cell_id: str | None

    generated_at: datetime
    items: list[TierMeetingAgendaItem]


@dataclass(frozen=True)
class EscalationEvent:
    id: str
    item_id: str
    from_tier: TierLevel
    to_tier: TierLevel
    escalated_by: str
    escalated_at: datetime
    reason: str


def _require_tzaware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("All datetimes must be timezone-aware")


def _default_chain(tier: TierLevel) -> list[TierLevel]:
    if tier == TierLevel.TIER_1:
        return [TierLevel.TIER_2, TierLevel.OBEYA]
    if tier == TierLevel.TIER_2:
        return [TierLevel.OBEYA]
    return []


def _severity_from_status(status: str) -> HandoverSeverity:
    s = (status or "").strip().lower()
    if s in {"critical", "red", "severe"}:
        return HandoverSeverity.CRITICAL
    if s in {"warning", "yellow", "at_risk"}:
        return HandoverSeverity.WARNING
    return HandoverSeverity.INFO


class ShiftHandoverTierMeetingService:
    """Service managing shift handovers and tier meeting agenda generation."""

    def __init__(self) -> None:
        self._notes: dict[str, ShiftHandoverNote] = {}
        self._agenda_items: dict[str, TierMeetingAgendaItem] = {}
        self._escalations: list[EscalationEvent] = []

    # ------------------------------------------------------------------
    # Digital handover
    # ------------------------------------------------------------------

    def create_handover_note(
        self,
        *,
        note_id: str,
        station_id: str,
        created_by: str,
        created_at: datetime | None = None,
        work_order_id: str | None = None,
        severity: HandoverSeverity = HandoverSeverity.INFO,
        safety: str = "",
        quality: str = "",
        delivery: str = "",
        cost: str = "",
        people: str = "",
        notes: str = "",
        tags: list[str] | None = None,
    ) -> ShiftHandoverNote:
        at = created_at or datetime.now(timezone.utc)
        _require_tzaware(at)
        if not station_id:
            raise ValueError("station_id is required")
        if not created_by:
            raise ValueError("created_by is required")

        note = ShiftHandoverNote(
            id=note_id,
            station_id=station_id,
            created_at=at,
            created_by=created_by,
            work_order_id=work_order_id,
            severity=severity,
            safety=safety,
            quality=quality,
            delivery=delivery,
            cost=cost,
            people=people,
            notes=notes,
            tags=list(tags or []),
        )
        self._notes[note.id] = note
        return note

    def list_handover_notes(
        self,
        *,
        station_id: str | None = None,
        include_acknowledged: bool = True,
        since: datetime | None = None,
    ) -> list[ShiftHandoverNote]:
        if since is not None:
            _require_tzaware(since)

        notes = list(self._notes.values())
        if station_id is not None:
            notes = [n for n in notes if n.station_id == station_id]
        if not include_acknowledged:
            notes = [n for n in notes if not n.acknowledged]
        if since is not None:
            notes = [n for n in notes if n.created_at >= since]

        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes

    def acknowledge_handover_note(
        self,
        note_id: str,
        *,
        acknowledged_by: str,
        acknowledged_at: datetime | None = None,
    ) -> ShiftHandoverNote:
        note = self._notes.get(note_id)
        if note is None:
            raise ValueError("handover note not found")
        at = acknowledged_at or datetime.now(timezone.utc)
        _require_tzaware(at)

        updated = ShiftHandoverNote(
            **{
                **note.__dict__,
                "acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": at,
            }
        )
        self._notes[note_id] = updated
        return updated

    def build_today_shift_handoff_commitment_payloads(
        self,
        *,
        incoming_user_id: str,
        assigned_station_ids: list[str],
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return payload dicts usable with TodayScreenService.add_commitment.

        This avoids a direct dependency on today_screen while still enabling the
        notes to be surfaced on the incoming operator's Today screen.
        """
        notes = self.list_handover_notes(include_acknowledged=False, since=since)
        notes = [n for n in notes if n.station_id in set(assigned_station_ids)]

        payloads: list[dict[str, Any]] = []
        for n in notes:
            title = f"Shift handoff: Station {n.station_id}"
            if n.work_order_id:
                title += f" (WO {n.work_order_id})"

            desc_parts = [p for p in [n.safety, n.quality, n.delivery, n.cost, n.people, n.notes] if p.strip()]
            description = "\n".join(desc_parts) if desc_parts else None

            payloads.append(
                {
                    "title": title,
                    "commitment_type": "shift_handoff",
                    "due_date": datetime.now(timezone.utc).date(),
                    "description": description,
                    "entity_type": "handover_note",
                    "entity_id": None,
                    "owner_id": None,
                    "owner_name": None,
                    "customer_name": None,
                    "metadata": {
                        "handover_note_id": n.id,
                        "station_id": n.station_id,
                        "work_order_id": n.work_order_id,
                        "incoming_user_id": incoming_user_id,
                        "severity": n.severity.value,
                    },
                }
            )

        return payloads

    # ------------------------------------------------------------------
    # Tier meeting templates
    # ------------------------------------------------------------------

    def generate_tier_meeting_agenda(
        self,
        *,
        agenda_id: str,
        tier: TierLevel,
        station_id: str | None = None,
        cell_id: str | None = None,
        red_sqdcp_items: list[dict[str, Any]] | None = None,
        open_andon_events: list[dict[str, Any]] | None = None,
        generated_at: datetime | None = None,
    ) -> TierMeetingAgenda:
        at = generated_at or datetime.now(timezone.utc)
        _require_tzaware(at)

        items: list[TierMeetingAgendaItem] = []

        for metric in red_sqdcp_items or []:
            metric_id = str(metric.get("metric_id") or metric.get("id") or "")
            name = str(metric.get("name") or "SQDCP Metric")
            category = str(metric.get("category") or "")
            status = str(metric.get("status") or "red")

            if status.strip().lower() != "red":
                continue

            title = f"{category.upper()}: {name} is RED" if category else f"{name} is RED"
            desc = str(metric.get("description") or metric.get("recommendation") or "")
            item = TierMeetingAgendaItem(
                id=f"agenda:{agenda_id}:metric:{metric_id}",
                tier=tier,
                item_type=AgendaItemType.SQDCP_RED,
                title=title,
                description=desc,
                severity=HandoverSeverity.CRITICAL,
                source_type="sqdcp_metric",
                source_id=metric_id,
                escalation_chain=_default_chain(tier),
                created_at=at,
                metadata={"raw": metric},
            )
            items.append(item)
            self._agenda_items[item.id] = item

        for event in open_andon_events or []:
            event_id = str(event.get("id") or event.get("event_id") or "")
            station = str(event.get("station_id") or "")
            status = str(event.get("status") or "open")
            if status.strip().lower() in {"resolved", "closed"}:
                continue

            andon_type = str(event.get("andon_type") or event.get("type") or "andon")
            symptom = str(event.get("symptom") or event.get("title") or "")
            sev = _severity_from_status(str(event.get("severity") or "warning"))

            title = f"Andon OPEN: {andon_type}"
            if station:
                title += f" @ {station}"
            description = symptom

            item = TierMeetingAgendaItem(
                id=f"agenda:{agenda_id}:andon:{event_id}",
                tier=tier,
                item_type=AgendaItemType.ANDON_OPEN,
                title=title,
                description=description,
                severity=sev,
                source_type="andon_event",
                source_id=event_id,
                escalation_chain=_default_chain(tier),
                created_at=at,
                metadata={"raw": event},
            )
            items.append(item)
            self._agenda_items[item.id] = item

        # Order: critical first, then warning, then info (stable by insertion)
        items.sort(key=lambda i: {HandoverSeverity.CRITICAL: 0, HandoverSeverity.WARNING: 1, HandoverSeverity.INFO: 2}[i.severity])

        return TierMeetingAgenda(
            id=agenda_id,
            tier=tier,
            station_id=station_id,
            cell_id=cell_id,
            generated_at=at,
            items=items,
        )

    # ------------------------------------------------------------------
    # Escalation pathing
    # ------------------------------------------------------------------

    def escalate_agenda_item(
        self,
        item_id: str,
        *,
        from_tier: TierLevel,
        escalated_by: str,
        reason: str,
        escalated_at: datetime | None = None,
    ) -> EscalationEvent:
        item = self._agenda_items.get(item_id)
        if item is None:
            raise ValueError("agenda item not found")
        if item.tier != from_tier:
            raise ValueError("from_tier does not match item tier")
        if not item.escalation_chain:
            raise ValueError("item has no higher-tier escalation path")

        to_tier = item.escalation_chain[0]
        at = escalated_at or datetime.now(timezone.utc)
        _require_tzaware(at)
        if not reason.strip():
            raise ValueError("Escalation reason is required")

        ev = EscalationEvent(
            id=f"esc:{item_id}:{to_tier.value}:{len(self._escalations)+1}",
            item_id=item_id,
            from_tier=from_tier,
            to_tier=to_tier,
            escalated_by=escalated_by,
            escalated_at=at,
            reason=reason.strip(),
        )
        self._escalations.append(ev)

        # Create a derived item at the higher tier, linked by metadata
        derived = TierMeetingAgendaItem(
            id=f"{item_id}:escalated:{to_tier.value}",
            tier=to_tier,
            item_type=item.item_type,
            title=item.title,
            description=item.description,
            severity=item.severity,
            source_type=item.source_type,
            source_id=item.source_id,
            escalation_chain=_default_chain(to_tier),
            created_at=at,
            metadata={
                **item.metadata,
                "escalated_from": item_id,
                "escalation_reason": ev.reason,
                "escalated_by": escalated_by,
            },
        )
        self._agenda_items[derived.id] = derived
        return ev

    def list_escalations(self) -> list[EscalationEvent]:
        return list(self._escalations)

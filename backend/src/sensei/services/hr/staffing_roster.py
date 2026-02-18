"""Staffing & Roster Management (Development Plan 21.7).

Implements:
- Shift Assignments: rosters per station/cell with employee slots.
- Absence Tracking: track and surface absences that impact skill coverage.
- Skill Coverage Risk Alerts: "Single Point of Failure" alerts when skill
  coverage drops below threshold based on Training Matrix data.

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass

_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


class ShiftType(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    FLEX = "flex"


class AbsenceType(str, Enum):
    SICK = "sick"
    VACATION = "vacation"
    TRAINING = "training"
    PERSONAL = "personal"
    OTHER = "other"


class AbsenceStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_ROSTER_WRITE_ROLES: set[str] = {"admin", "hr", "gm", "supervisor", "ops"}
_ROSTER_VIEW_ROLES: set[str] = {"admin", "hr", "gm", "supervisor", "ops", "exec", "ceo"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ShiftDefinition:
    id: UUID
    name: str
    shift_type: ShiftType
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    site_id: str | None = None
    station_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RosterSlot:
    id: UUID
    shift_id: UUID
    roster_date: date
    employee_id: UUID
    station_id: str | None = None
    notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: UUID | None = None


@dataclass(frozen=True)
class Absence:
    id: UUID
    employee_id: UUID
    absence_type: AbsenceType
    start_date: date
    end_date: date
    status: AbsenceStatus
    reason: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: UUID | None = None
    decided_at: datetime | None = None
    decided_by: UUID | None = None


@dataclass(frozen=True)
class SkillCoverageRisk:
    id: UUID
    skill_code: str
    skill_name: str
    station_id: str
    station_name: str
    shift_id: UUID
    roster_date: date
    severity: RiskSeverity
    available_count: int
    minimum_required: int
    absent_employee_ids: list[UUID] = field(default_factory=list)
    flagged_at: datetime = field(default_factory=_utcnow)
    acknowledged: bool = False
    acknowledged_by: UUID | None = None


class StaffingRosterService(PersistentServiceMixin):
    """In-memory roster + absence + skill-coverage risk service."""

    SERVICE_NAME = "staffing_roster"

    def __init__(self) -> None:
        self._shifts: dict[UUID, ShiftDefinition] = {}
        self._roster_slots: dict[UUID, RosterSlot] = {}
        self._absences: dict[UUID, Absence] = {}
        self._risks: dict[UUID, SkillCoverageRisk] = {}

        # External hooks for skill lookup (injected).
        self._employee_skill_lookup: dict[UUID, set[str]] = {}
        self._station_skill_requirements: dict[str, set[str]] = {}
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        shifts_data = await self.load_state(_DEFAULT_TENANT_ID, "shifts") or {}
        roster_data = await self.load_state(_DEFAULT_TENANT_ID, "roster_slots") or {}
        absences_data = await self.load_state(_DEFAULT_TENANT_ID, "absences") or {}
        risks_data = await self.load_state(_DEFAULT_TENANT_ID, "risks") or {}
        skills_data = await self.load_state(_DEFAULT_TENANT_ID, "employee_skills") or {}
        station_reqs_data = await self.load_state(_DEFAULT_TENANT_ID, "station_skill_requirements") or {}

        self._shifts = {UUID(sid): decode_dataclass(shift, ShiftDefinition) for sid, shift in shifts_data.items()}
        self._roster_slots = {UUID(rid): decode_dataclass(slot, RosterSlot) for rid, slot in roster_data.items()}
        self._absences = {UUID(aid): decode_dataclass(absence, Absence) for aid, absence in absences_data.items()}
        self._risks = {UUID(rid): decode_dataclass(risk, SkillCoverageRisk) for rid, risk in risks_data.items()}
        self._employee_skill_lookup = {UUID(eid): set(codes) for eid, codes in skills_data.items()}
        self._station_skill_requirements = {station_id: set(codes) for station_id, codes in station_reqs_data.items()}
        self._state_loaded = True

    async def persist_all(self) -> None:
        shifts_data = {str(sid): encode_dataclass(shift) for sid, shift in self._shifts.items()}
        roster_data = {str(rid): encode_dataclass(slot) for rid, slot in self._roster_slots.items()}
        absences_data = {str(aid): encode_dataclass(absence) for aid, absence in self._absences.items()}
        risks_data = {str(rid): encode_dataclass(risk) for rid, risk in self._risks.items()}
        skills_data = {str(eid): sorted(list(codes)) for eid, codes in self._employee_skill_lookup.items()}
        station_reqs_data = {station_id: sorted(list(codes)) for station_id, codes in self._station_skill_requirements.items()}

        await self.save_state(_DEFAULT_TENANT_ID, "shifts", shifts_data)
        await self.save_state(_DEFAULT_TENANT_ID, "roster_slots", roster_data)
        await self.save_state(_DEFAULT_TENANT_ID, "absences", absences_data)
        await self.save_state(_DEFAULT_TENANT_ID, "risks", risks_data)
        await self.save_state(_DEFAULT_TENANT_ID, "employee_skills", skills_data)
        await self.save_state(_DEFAULT_TENANT_ID, "station_skill_requirements", station_reqs_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ---- RBAC helpers ----

    def can_write(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_ROSTER_WRITE_ROLES)) > 0

    def can_view(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_ROSTER_VIEW_ROLES)) > 0

    # ---- Shift definitions ----

    def create_shift(
        self,
        *,
        name: str,
        shift_type: ShiftType,
        start_time: str,
        end_time: str,
        actor_roles: Iterable[str],
        site_id: str | None = None,
        station_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ShiftDefinition:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create shifts")

        shift = ShiftDefinition(
            id=uuid4(),
            name=name.strip(),
            shift_type=shift_type,
            start_time=start_time,
            end_time=end_time,
            site_id=site_id,
            station_ids=list(station_ids or []),
            metadata=dict(metadata or {}),
        )
        self._shifts[shift.id] = shift
        return shift

    async def create_shift_async(self, **kwargs: Any) -> ShiftDefinition:
        await self._ensure_loaded()
        shift = self.create_shift(**kwargs)
        await self.persist_all()
        return shift

    def list_shifts(self, *, actor_roles: Iterable[str]) -> list[ShiftDefinition]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view shifts")
        return sorted(self._shifts.values(), key=lambda s: s.name.lower())

    async def list_shifts_async(self, *, actor_roles: Iterable[str]) -> list[ShiftDefinition]:
        await self._ensure_loaded()
        return self.list_shifts(actor_roles=actor_roles)

    # ---- Roster slots ----

    def assign_slot(
        self,
        *,
        shift_id: UUID,
        roster_date: date,
        employee_id: UUID,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        station_id: str | None = None,
        notes: str = "",
    ) -> RosterSlot:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to assign roster slots")
        if shift_id not in self._shifts:
            raise KeyError("Shift not found")

        slot = RosterSlot(
            id=uuid4(),
            shift_id=shift_id,
            roster_date=roster_date,
            employee_id=employee_id,
            station_id=station_id,
            notes=notes,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._roster_slots[slot.id] = slot
        return slot

    async def assign_slot_async(self, **kwargs: Any) -> RosterSlot:
        await self._ensure_loaded()
        slot = self.assign_slot(**kwargs)
        await self.persist_all()
        return slot

    def remove_slot(
        self,
        slot_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> None:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to remove roster slots")
        if slot_id not in self._roster_slots:
            raise KeyError("Roster slot not found")
        del self._roster_slots[slot_id]

    async def remove_slot_async(self, **kwargs: Any) -> None:
        await self._ensure_loaded()
        self.remove_slot(**kwargs)
        await self.persist_all()

    def list_roster(
        self,
        *,
        shift_id: UUID | None = None,
        roster_date: date | None = None,
        employee_id: UUID | None = None,
        actor_roles: Iterable[str],
    ) -> list[RosterSlot]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view roster")

        result = list(self._roster_slots.values())
        if shift_id is not None:
            result = [s for s in result if s.shift_id == shift_id]
        if roster_date is not None:
            result = [s for s in result if s.roster_date == roster_date]
        if employee_id is not None:
            result = [s for s in result if s.employee_id == employee_id]
        result.sort(key=lambda s: (s.roster_date, s.shift_id))
        return result

    async def list_roster_async(self, **kwargs: Any) -> list[RosterSlot]:
        await self._ensure_loaded()
        return self.list_roster(**kwargs)

    # ---- Absences ----

    def record_absence(
        self,
        *,
        employee_id: UUID,
        absence_type: AbsenceType,
        start_date: date,
        end_date: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        reason: str = "",
        auto_approve: bool = False,
    ) -> Absence:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to record absences")
        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")

        status = AbsenceStatus.APPROVED if auto_approve else AbsenceStatus.REQUESTED
        absence = Absence(
            id=uuid4(),
            employee_id=employee_id,
            absence_type=absence_type,
            start_date=start_date,
            end_date=end_date,
            status=status,
            reason=reason,
            created_at=_utcnow(),
            created_by=actor_user_id,
            decided_at=_utcnow() if auto_approve else None,
            decided_by=actor_user_id if auto_approve else None,
        )
        self._absences[absence.id] = absence
        return absence

    async def record_absence_async(self, **kwargs: Any) -> Absence:
        await self._ensure_loaded()
        absence = self.record_absence(**kwargs)
        await self.persist_all()
        return absence

    def decide_absence(
        self,
        absence_id: UUID,
        *,
        approved: bool,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> Absence:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to decide absences")
        if absence_id not in self._absences:
            raise KeyError("Absence not found")

        absence = self._absences[absence_id]
        if absence.status != AbsenceStatus.REQUESTED:
            raise ValueError("Only REQUESTED absences can be decided")

        updated = replace(
            absence,
            status=AbsenceStatus.APPROVED if approved else AbsenceStatus.REJECTED,
            decided_at=_utcnow(),
            decided_by=actor_user_id,
        )
        self._absences[absence_id] = updated
        return updated

    async def decide_absence_async(self, **kwargs: Any) -> Absence:
        await self._ensure_loaded()
        absence = self.decide_absence(**kwargs)
        await self.persist_all()
        return absence

    def list_absences(
        self,
        *,
        employee_id: UUID | None = None,
        start_after: date | None = None,
        end_before: date | None = None,
        actor_roles: Iterable[str],
        include_cancelled: bool = False,
    ) -> list[Absence]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view absences")

        result = list(self._absences.values())
        if employee_id is not None:
            result = [a for a in result if a.employee_id == employee_id]
        if start_after is not None:
            result = [a for a in result if a.end_date >= start_after]
        if end_before is not None:
            result = [a for a in result if a.start_date <= end_before]
        if not include_cancelled:
            result = [a for a in result if a.status != AbsenceStatus.CANCELLED]
        result.sort(key=lambda a: (a.start_date, a.employee_id))
        return result

    async def list_absences_async(self, **kwargs: Any) -> list[Absence]:
        await self._ensure_loaded()
        return self.list_absences(**kwargs)

    def get_absent_employees_on(self, *, on_date: date) -> set[UUID]:
        return {
            a.employee_id
            for a in self._absences.values()
            if a.status == AbsenceStatus.APPROVED and a.start_date <= on_date <= a.end_date
        }

    async def get_absent_employees_on_async(self, *, on_date: date) -> set[UUID]:
        await self._ensure_loaded()
        return self.get_absent_employees_on(on_date=on_date)

    # ---- Skill lookup injection ----

    def set_employee_skills(self, employee_id: UUID, skill_codes: Iterable[str]) -> None:
        self._employee_skill_lookup[employee_id] = set(skill_codes)

    async def set_employee_skills_async(self, employee_id: UUID, skill_codes: Iterable[str]) -> None:
        await self._ensure_loaded()
        self.set_employee_skills(employee_id, skill_codes)
        await self.persist_all()

    def set_station_skill_requirements(self, station_id: str, skill_codes: Iterable[str]) -> None:
        self._station_skill_requirements[station_id] = set(skill_codes)

    async def set_station_skill_requirements_async(self, station_id: str, skill_codes: Iterable[str]) -> None:
        await self._ensure_loaded()
        self.set_station_skill_requirements(station_id, skill_codes)
        await self.persist_all()

    # ---- Skill coverage risk detection ----

    def compute_coverage_risks(
        self,
        *,
        roster_date: date,
        actor_roles: Iterable[str],
        minimum_required: int = 2,
    ) -> list[SkillCoverageRisk]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to compute coverage risks")

        absent_on_date = self.get_absent_employees_on(on_date=roster_date)
        risks: list[SkillCoverageRisk] = []

        for shift in self._shifts.values():
            for station_id in shift.station_ids:
                required_skills = self._station_skill_requirements.get(station_id, set())
                if not required_skills:
                    continue

                # Which rostered employees are available?
                rostered = [
                    s.employee_id
                    for s in self._roster_slots.values()
                    if s.shift_id == shift.id and s.roster_date == roster_date
                ]

                available = [eid for eid in rostered if eid not in absent_on_date]

                for skill_code in required_skills:
                    covered_count = sum(
                        1 for eid in available if skill_code in self._employee_skill_lookup.get(eid, set())
                    )
                    if covered_count < minimum_required:
                        severity = RiskSeverity.CRITICAL if covered_count == 0 else (
                            RiskSeverity.HIGH if covered_count == 1 else RiskSeverity.MEDIUM
                        )
                        risk = SkillCoverageRisk(
                            id=uuid4(),
                            skill_code=skill_code,
                            skill_name=skill_code,
                            station_id=station_id,
                            station_name=station_id,
                            shift_id=shift.id,
                            roster_date=roster_date,
                            severity=severity,
                            available_count=covered_count,
                            minimum_required=minimum_required,
                            absent_employee_ids=[eid for eid in rostered if eid in absent_on_date],
                            flagged_at=_utcnow(),
                        )
                        self._risks[risk.id] = risk
                        risks.append(risk)

        risks.sort(key=lambda r: (r.severity.value, r.station_id))
        return risks

    async def compute_coverage_risks_async(self, **kwargs: Any) -> list[SkillCoverageRisk]:
        await self._ensure_loaded()
        risks = self.compute_coverage_risks(**kwargs)
        await self.persist_all()
        return risks

    def list_coverage_risks(
        self,
        *,
        roster_date: date | None = None,
        station_id: str | None = None,
        only_critical: bool = False,
        actor_roles: Iterable[str],
    ) -> list[SkillCoverageRisk]:
        if not self.can_view(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view coverage risks")

        result = list(self._risks.values())
        if roster_date is not None:
            result = [r for r in result if r.roster_date == roster_date]
        if station_id is not None:
            result = [r for r in result if r.station_id == station_id]
        if only_critical:
            result = [r for r in result if r.severity == RiskSeverity.CRITICAL]
        result.sort(key=lambda r: (r.severity.value, r.roster_date, r.station_id))
        return result

    async def list_coverage_risks_async(self, **kwargs: Any) -> list[SkillCoverageRisk]:
        await self._ensure_loaded()
        return self.list_coverage_risks(**kwargs)

    def acknowledge_risk(
        self,
        risk_id: UUID,
        *,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> SkillCoverageRisk:
        if not self.can_write(actor_roles=actor_roles):
            raise PermissionError("Not permitted to acknowledge risks")
        if risk_id not in self._risks:
            raise KeyError("Risk not found")

        risk = self._risks[risk_id]
        updated = replace(risk, acknowledged=True, acknowledged_by=actor_user_id)
        self._risks[risk_id] = updated
        return updated

    async def acknowledge_risk_async(self, **kwargs: Any) -> SkillCoverageRisk:
        await self._ensure_loaded()
        risk = self.acknowledge_risk(**kwargs)
        await self.persist_all()
        return risk

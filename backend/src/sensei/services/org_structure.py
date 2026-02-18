"""Org Structure & Headcount (Development Plan 22.6).

Implements:
- Org Chart: hierarchical organization structure with units and positions.
- Reporting Lines: manager-subordinate relationships.
- Positions: job positions with headcount tracking.
- Requisition-to-Hire: traceability from open positions to hires.

This module is in-memory and pure-Python to match other services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class OrgUnitType(str, Enum):
    COMPANY = "company"
    DIVISION = "division"
    DEPARTMENT = "department"
    TEAM = "team"
    CELL = "cell"


class PositionType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"


class PositionStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class AssignmentStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    PENDING = "pending"


# RBAC
_HR_WRITE_ROLES: set[str] = {"admin", "hr", "ceo"}
_HR_READ_ROLES: set[str] = {"admin", "hr", "ceo", "exec", "gm", "finance", "auditor"}
_ORG_VIEW_ROLES: set[str] = {"admin", "hr", "ceo", "exec", "gm", "supervisor", "team_lead"}
_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrgUnit:
    """Organizational unit (department, team, etc.)."""

    id: UUID
    code: str
    name: str
    unit_type: OrgUnitType
    parent_id: UUID | None = None
    manager_id: UUID | None = None  # Employee ID of manager
    cost_center: str = ""
    location: str = ""
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Position:
    """Job position with headcount tracking."""

    id: UUID
    code: str
    title: str
    org_unit_id: UUID
    position_type: PositionType
    status: PositionStatus
    reports_to_position_id: UUID | None = None
    headcount: int = 1  # Number of positions with this title in this unit
    grade: str = ""
    job_family: str = ""
    requisition_id: UUID | None = None  # Link to recruiting requisition
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PositionAssignment:
    """Assignment of employee to position."""

    id: UUID
    position_id: UUID
    employee_id: UUID
    status: AssignmentStatus
    start_date: date
    end_date: date | None = None
    is_primary: bool = True
    reason: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""


@dataclass(frozen=True)
class ReportingRelation:
    """Manager-subordinate reporting relationship."""

    id: UUID
    employee_id: UUID
    manager_id: UUID
    start_date: date
    end_date: date | None = None
    is_primary: bool = True
    relation_type: str = "direct"  # direct, dotted, matrix


class OrgStructureService(PersistentServiceMixin):
    """In-memory org structure service."""

    SERVICE_NAME = "org_structure"

    def __init__(self) -> None:
        self._units: dict[UUID, OrgUnit] = {}
        self._positions: dict[UUID, Position] = {}
        self._assignments: dict[UUID, PositionAssignment] = {}
        self._reporting: dict[UUID, ReportingRelation] = {}
        self._audit: list[AuditEvent] = []
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        units_data = await self.load_state(_DEFAULT_TENANT_ID, "units") or {}
        positions_data = await self.load_state(_DEFAULT_TENANT_ID, "positions") or {}
        assignments_data = await self.load_state(_DEFAULT_TENANT_ID, "assignments") or {}
        reporting_data = await self.load_state(_DEFAULT_TENANT_ID, "reporting") or {}
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []

        self._units = {UUID(uid): decode_dataclass(unit, OrgUnit) for uid, unit in units_data.items()}
        self._positions = {UUID(pid): decode_dataclass(pos, Position) for pid, pos in positions_data.items()}
        self._assignments = {UUID(aid): decode_dataclass(assign, PositionAssignment) for aid, assign in assignments_data.items()}
        self._reporting = {UUID(rid): decode_dataclass(rel, ReportingRelation) for rid, rel in reporting_data.items()}
        self._audit = [decode_dataclass(ev, AuditEvent) for ev in audit_data]
        self._state_loaded = True

    async def persist_all(self) -> None:
        units_data = {str(uid): encode_dataclass(unit) for uid, unit in self._units.items()}
        positions_data = {str(pid): encode_dataclass(pos) for pid, pos in self._positions.items()}
        assignments_data = {str(aid): encode_dataclass(assign) for aid, assign in self._assignments.items()}
        reporting_data = {str(rid): encode_dataclass(rel) for rid, rel in self._reporting.items()}
        audit_data = [encode_dataclass(ev) for ev in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "units", units_data)
        await self.save_state(_DEFAULT_TENANT_ID, "positions", positions_data)
        await self.save_state(_DEFAULT_TENANT_ID, "assignments", assignments_data)
        await self.save_state(_DEFAULT_TENANT_ID, "reporting", reporting_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ev = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(ev)

    # ----------------------------------------------------------------
    # Audit API
    # ----------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return list(self._audit)

    async def list_audit_events_async(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(actor_roles=actor_roles)

    # ----------------------------------------------------------------
    # Org Units
    # ----------------------------------------------------------------

    def create_org_unit(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        code: str,
        name: str,
        unit_type: OrgUnitType,
        parent_id: UUID | None = None,
        manager_id: UUID | None = None,
        cost_center: str = "",
        location: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> OrgUnit:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not code or not code.strip():
            raise ValueError("code required")
        if not name or not name.strip():
            raise ValueError("name required")

        # Check code uniqueness
        for unit in self._units.values():
            if unit.code == code.strip():
                raise ValueError("code already exists")

        # Validate parent exists
        if parent_id and parent_id not in self._units:
            raise ValueError("parent_id not found")

        unit = OrgUnit(
            id=uuid4(),
            code=code.strip(),
            name=name.strip(),
            unit_type=unit_type,
            parent_id=parent_id,
            manager_id=manager_id,
            cost_center=cost_center,
            location=location,
            metadata=metadata or {},
        )
        self._units[unit.id] = unit

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.unit.create",
            entity_type="org_unit",
            entity_id=str(unit.id),
            correlation_id=correlation_id,
            metadata={"code": code, "unit_type": unit_type.value},
        )

        return unit

    async def create_org_unit_async(self, **kwargs: Any) -> OrgUnit:
        await self._ensure_loaded()
        unit = self.create_org_unit(**kwargs)
        await self.persist_all()
        return unit

    def get_org_unit(
        self, *, actor_roles: Iterable[str], unit_id: UUID
    ) -> OrgUnit | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")
        return self._units.get(unit_id)

    async def get_org_unit_async(self, *, actor_roles: Iterable[str], unit_id: UUID) -> OrgUnit | None:
        await self._ensure_loaded()
        return self.get_org_unit(actor_roles=actor_roles, unit_id=unit_id)

    def list_org_units(
        self,
        *,
        actor_roles: Iterable[str],
        parent_id: UUID | None = None,
        unit_type: OrgUnitType | None = None,
        active_only: bool = True,
    ) -> list[OrgUnit]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")

        result = []
        for unit in self._units.values():
            if active_only and not unit.is_active:
                continue
            if parent_id is not None and unit.parent_id != parent_id:
                continue
            if unit_type and unit.unit_type != unit_type:
                continue
            result.append(unit)

        return sorted(result, key=lambda u: u.code)

    async def list_org_units_async(self, **kwargs: Any) -> list[OrgUnit]:
        await self._ensure_loaded()
        return self.list_org_units(**kwargs)

    def get_org_tree(
        self, *, actor_roles: Iterable[str], root_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """Get hierarchical org tree starting from root."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")

        def build_tree(parent_id: UUID | None) -> list[dict[str, Any]]:
            children = []
            for unit in self._units.values():
                if unit.parent_id == parent_id and unit.is_active:
                    children.append({
                        "id": str(unit.id),
                        "code": unit.code,
                        "name": unit.name,
                        "unit_type": unit.unit_type.value,
                        "children": build_tree(unit.id),
                    })
            return sorted(children, key=lambda c: c["code"])

        return build_tree(root_id)

    async def get_org_tree_async(
        self, *, actor_roles: Iterable[str], root_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        await self._ensure_loaded()
        return self.get_org_tree(actor_roles=actor_roles, root_id=root_id)

    def update_org_unit(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        unit_id: UUID,
        name: str | None = None,
        manager_id: UUID | None = None,
        cost_center: str | None = None,
        location: str | None = None,
        is_active: bool | None = None,
    ) -> OrgUnit:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        unit = self._units.get(unit_id)
        if not unit:
            raise ValueError("unit_id not found")

        updated = OrgUnit(
            id=unit.id,
            code=unit.code,
            name=name.strip() if name else unit.name,
            unit_type=unit.unit_type,
            parent_id=unit.parent_id,
            manager_id=manager_id if manager_id is not None else unit.manager_id,
            cost_center=cost_center if cost_center is not None else unit.cost_center,
            location=location if location is not None else unit.location,
            is_active=is_active if is_active is not None else unit.is_active,
            metadata=unit.metadata,
        )
        self._units[unit.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.unit.update",
            entity_type="org_unit",
            entity_id=str(unit_id),
            correlation_id=correlation_id,
        )

        return updated

    async def update_org_unit_async(self, **kwargs: Any) -> OrgUnit:
        await self._ensure_loaded()
        unit = self.update_org_unit(**kwargs)
        await self.persist_all()
        return unit

    # ----------------------------------------------------------------
    # Positions
    # ----------------------------------------------------------------

    def create_position(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        code: str,
        title: str,
        org_unit_id: UUID,
        position_type: PositionType = PositionType.FULL_TIME,
        reports_to_position_id: UUID | None = None,
        headcount: int = 1,
        grade: str = "",
        job_family: str = "",
        requisition_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not code or not code.strip():
            raise ValueError("code required")
        if not title or not title.strip():
            raise ValueError("title required")
        if headcount < 1:
            raise ValueError("headcount must be >= 1")

        # Validate org unit exists
        if org_unit_id not in self._units:
            raise ValueError("org_unit_id not found")

        # Validate reports_to position exists
        if reports_to_position_id and reports_to_position_id not in self._positions:
            raise ValueError("reports_to_position_id not found")

        # Check code uniqueness
        for pos in self._positions.values():
            if pos.code == code.strip():
                raise ValueError("position code already exists")

        position = Position(
            id=uuid4(),
            code=code.strip(),
            title=title.strip(),
            org_unit_id=org_unit_id,
            position_type=position_type,
            status=PositionStatus.OPEN,
            reports_to_position_id=reports_to_position_id,
            headcount=headcount,
            grade=grade,
            job_family=job_family,
            requisition_id=requisition_id,
            metadata=metadata or {},
        )
        self._positions[position.id] = position

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.position.create",
            entity_type="position",
            entity_id=str(position.id),
            correlation_id=correlation_id,
            metadata={"code": code, "title": title},
        )

        return position

    async def create_position_async(self, **kwargs: Any) -> Position:
        await self._ensure_loaded()
        position = self.create_position(**kwargs)
        await self.persist_all()
        return position

    def get_position(
        self, *, actor_roles: Iterable[str], position_id: UUID
    ) -> Position | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")
        return self._positions.get(position_id)

    async def get_position_async(self, *, actor_roles: Iterable[str], position_id: UUID) -> Position | None:
        await self._ensure_loaded()
        return self.get_position(actor_roles=actor_roles, position_id=position_id)

    def list_positions(
        self,
        *,
        actor_roles: Iterable[str],
        org_unit_id: UUID | None = None,
        status: PositionStatus | None = None,
    ) -> list[Position]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")

        result = []
        for pos in self._positions.values():
            if org_unit_id and pos.org_unit_id != org_unit_id:
                continue
            if status and pos.status != status:
                continue
            result.append(pos)

        return sorted(result, key=lambda p: p.code)

    async def list_positions_async(self, **kwargs: Any) -> list[Position]:
        await self._ensure_loaded()
        return self.list_positions(**kwargs)

    def update_position_status(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        position_id: UUID,
        status: PositionStatus,
    ) -> Position:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        position = self._positions.get(position_id)
        if not position:
            raise ValueError("position_id not found")

        updated = Position(
            id=position.id,
            code=position.code,
            title=position.title,
            org_unit_id=position.org_unit_id,
            position_type=position.position_type,
            status=status,
            reports_to_position_id=position.reports_to_position_id,
            headcount=position.headcount,
            grade=position.grade,
            job_family=position.job_family,
            requisition_id=position.requisition_id,
            metadata=position.metadata,
        )
        self._positions[position.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.position.update_status",
            entity_type="position",
            entity_id=str(position_id),
            correlation_id=correlation_id,
            metadata={"old_status": position.status.value, "new_status": status.value},
        )

        return updated

    async def update_position_status_async(self, **kwargs: Any) -> Position:
        await self._ensure_loaded()
        position = self.update_position_status(**kwargs)
        await self.persist_all()
        return position

    # ----------------------------------------------------------------
    # Position Assignments
    # ----------------------------------------------------------------

    def assign_employee_to_position(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        position_id: UUID,
        employee_id: UUID,
        start_date: date | None = None,
        is_primary: bool = True,
        reason: str = "",
    ) -> PositionAssignment:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        position = self._positions.get(position_id)
        if not position:
            raise ValueError("position_id not found")

        # Count current assignments
        current_count = sum(
            1
            for a in self._assignments.values()
            if a.position_id == position_id and a.status == AssignmentStatus.ACTIVE
        )
        if current_count >= position.headcount:
            raise ValueError("Position headcount already filled")

        assignment = PositionAssignment(
            id=uuid4(),
            position_id=position_id,
            employee_id=employee_id,
            status=AssignmentStatus.ACTIVE,
            start_date=start_date or date.today(),
            is_primary=is_primary,
            reason=reason,
            created_at=_utcnow(),
            created_by=actor_id,
        )
        self._assignments[assignment.id] = assignment

        # Update position status if filled
        new_count = current_count + 1
        if new_count >= position.headcount:
            self.update_position_status(
                actor_id=actor_id,
                actor_roles=actor_roles,
                correlation_id=correlation_id,
                position_id=position_id,
                status=PositionStatus.FILLED,
            )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.assignment.create",
            entity_type="position_assignment",
            entity_id=str(assignment.id),
            correlation_id=correlation_id,
            metadata={
                "position_id": str(position_id),
                "employee_id": str(employee_id),
            },
        )

        return assignment

    async def assign_employee_to_position_async(self, **kwargs: Any) -> PositionAssignment:
        await self._ensure_loaded()
        assignment = self.assign_employee_to_position(**kwargs)
        await self.persist_all()
        return assignment

    def end_assignment(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        assignment_id: UUID,
        end_date: date | None = None,
        reason: str = "",
    ) -> PositionAssignment:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        assignment = self._assignments.get(assignment_id)
        if not assignment:
            raise ValueError("assignment_id not found")
        if assignment.status != AssignmentStatus.ACTIVE:
            raise ValueError("Assignment is not active")

        ended = PositionAssignment(
            id=assignment.id,
            position_id=assignment.position_id,
            employee_id=assignment.employee_id,
            status=AssignmentStatus.ENDED,
            start_date=assignment.start_date,
            end_date=end_date or date.today(),
            is_primary=assignment.is_primary,
            reason=reason or assignment.reason,
            created_at=assignment.created_at,
            created_by=assignment.created_by,
        )
        self._assignments[assignment.id] = ended

        # Update position status back to open
        position = self._positions.get(assignment.position_id)
        if position and position.status == PositionStatus.FILLED:
            self.update_position_status(
                actor_id=actor_id,
                actor_roles=actor_roles,
                correlation_id=correlation_id,
                position_id=position.id,
                status=PositionStatus.OPEN,
            )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.assignment.end",
            entity_type="position_assignment",
            entity_id=str(assignment_id),
            correlation_id=correlation_id,
            metadata={"reason": reason},
        )

        return ended

    async def end_assignment_async(self, **kwargs: Any) -> PositionAssignment:
        await self._ensure_loaded()
        assignment = self.end_assignment(**kwargs)
        await self.persist_all()
        return assignment

    def get_employee_assignments(
        self,
        *,
        actor_roles: Iterable[str],
        employee_id: UUID,
        active_only: bool = True,
    ) -> list[PositionAssignment]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")

        result = []
        for a in self._assignments.values():
            if a.employee_id != employee_id:
                continue
            if active_only and a.status != AssignmentStatus.ACTIVE:
                continue
            result.append(a)

        return sorted(result, key=lambda a: a.start_date)

    async def get_employee_assignments_async(self, **kwargs: Any) -> list[PositionAssignment]:
        await self._ensure_loaded()
        return self.get_employee_assignments(**kwargs)

    # ----------------------------------------------------------------
    # Reporting Relations
    # ----------------------------------------------------------------

    def set_reporting_relation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        employee_id: UUID,
        manager_id: UUID,
        start_date: date | None = None,
        is_primary: bool = True,
        relation_type: str = "direct",
    ) -> ReportingRelation:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if employee_id == manager_id:
            raise ValueError("Employee cannot report to themselves")

        # End any existing primary reporting relation
        if is_primary:
            for rel in self._reporting.values():
                if (
                    rel.employee_id == employee_id
                    and rel.is_primary
                    and rel.end_date is None
                ):
                    ended = ReportingRelation(
                        id=rel.id,
                        employee_id=rel.employee_id,
                        manager_id=rel.manager_id,
                        start_date=rel.start_date,
                        end_date=start_date or date.today(),
                        is_primary=rel.is_primary,
                        relation_type=rel.relation_type,
                    )
                    self._reporting[rel.id] = ended

        relation = ReportingRelation(
            id=uuid4(),
            employee_id=employee_id,
            manager_id=manager_id,
            start_date=start_date or date.today(),
            is_primary=is_primary,
            relation_type=relation_type,
        )
        self._reporting[relation.id] = relation

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="org.reporting.set",
            entity_type="reporting_relation",
            entity_id=str(relation.id),
            correlation_id=correlation_id,
            metadata={
                "employee_id": str(employee_id),
                "manager_id": str(manager_id),
                "relation_type": relation_type,
            },
        )

        return relation

    async def set_reporting_relation_async(self, **kwargs: Any) -> ReportingRelation:
        await self._ensure_loaded()
        relation = self.set_reporting_relation(**kwargs)
        await self.persist_all()
        return relation

    def get_direct_reports(
        self,
        *,
        actor_roles: Iterable[str],
        manager_id: UUID,
    ) -> list[UUID]:
        """Get employee IDs who report directly to this manager."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")

        return [
            rel.employee_id
            for rel in self._reporting.values()
            if rel.manager_id == manager_id
            and rel.is_primary
            and rel.end_date is None
        ]

    async def get_direct_reports_async(self, **kwargs: Any) -> list[UUID]:
        await self._ensure_loaded()
        return self.get_direct_reports(**kwargs)

    def get_manager(
        self,
        *,
        actor_roles: Iterable[str],
        employee_id: UUID,
    ) -> UUID | None:
        """Get primary manager ID for an employee."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ORG_VIEW_ROLES, "Org view role required")

        for rel in self._reporting.values():
            if (
                rel.employee_id == employee_id
                and rel.is_primary
                and rel.end_date is None
            ):
                return rel.manager_id
        return None

    async def get_manager_async(self, **kwargs: Any) -> UUID | None:
        await self._ensure_loaded()
        return self.get_manager(**kwargs)

    # ----------------------------------------------------------------
    # Headcount Analytics
    # ----------------------------------------------------------------

    def get_headcount_summary(
        self,
        *,
        actor_roles: Iterable[str],
        org_unit_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get headcount summary for an org unit (or all)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        positions = self.list_positions(actor_roles=actor_roles, org_unit_id=org_unit_id)

        total_headcount = sum(p.headcount for p in positions)
        filled_count = 0
        open_count = 0

        for pos in positions:
            active_assignments = sum(
                1
                for a in self._assignments.values()
                if a.position_id == pos.id and a.status == AssignmentStatus.ACTIVE
            )
            filled_count += active_assignments
            open_count += pos.headcount - active_assignments

        return {
            "total_positions": len(positions),
            "total_headcount": total_headcount,
            "filled": filled_count,
            "open": open_count,
            "fill_rate": (filled_count / total_headcount * 100) if total_headcount > 0 else 0,
        }

    async def get_headcount_summary_async(self, **kwargs: Any) -> dict[str, Any]:
        await self._ensure_loaded()
        return self.get_headcount_summary(**kwargs)

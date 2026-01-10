"""Tests for Org Structure & Headcount (Development Plan 22.6)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from sensei.services.org_structure import (
    OrgStructureService,
    OrgUnitType,
    PositionType,
    PositionStatus,
    AssignmentStatus,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> OrgStructureService:
    return OrgStructureService()


@pytest.fixture
def hr_roles() -> set[str]:
    return {"hr"}


@pytest.fixture
def viewer_roles() -> set[str]:
    return {"supervisor"}


@pytest.fixture
def norole() -> set[str]:
    return {"guest"}


@pytest.fixture
def company(svc: OrgStructureService, hr_roles: set[str]) -> dict:
    """Create a root company org unit."""
    unit = svc.create_org_unit(
        actor_id="setup",
        actor_roles=hr_roles,
        correlation_id="setup-1",
        code="CORP",
        name="Corporation",
        unit_type=OrgUnitType.COMPANY,
    )
    return {"unit": unit}


@pytest.fixture
def department(svc: OrgStructureService, hr_roles: set[str], company: dict) -> dict:
    """Create a department under company."""
    unit = svc.create_org_unit(
        actor_id="setup",
        actor_roles=hr_roles,
        correlation_id="setup-2",
        code="ENG",
        name="Engineering",
        unit_type=OrgUnitType.DEPARTMENT,
        parent_id=company["unit"].id,
    )
    return {"unit": unit, "company": company["unit"]}


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_create_org_unit_requires_hr_role(
        self, svc: OrgStructureService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.create_org_unit(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                code="DEPT",
                name="Department",
                unit_type=OrgUnitType.DEPARTMENT,
            )

    def test_viewer_can_list_units(
        self, svc: OrgStructureService, hr_roles: set[str], viewer_roles: set[str]
    ) -> None:
        # Create as HR
        svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="DEPT",
            name="Department",
            unit_type=OrgUnitType.DEPARTMENT,
        )
        # View as supervisor
        units = svc.list_org_units(actor_roles=viewer_roles)
        assert len(units) == 1

    def test_guest_cannot_view_units(
        self, svc: OrgStructureService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Org view role required"):
            svc.list_org_units(actor_roles=norole)

    def test_create_position_requires_hr_role(
        self, svc: OrgStructureService, department: dict, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.create_position(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                code="SWE-001",
                title="Software Engineer",
                org_unit_id=department["unit"].id,
            )

    def test_assign_employee_requires_hr_role(
        self, svc: OrgStructureService, department: dict, hr_roles: set[str], norole: set[str]
    ) -> None:
        position = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
        )
        with pytest.raises(PermissionError, match="HR write role required"):
            svc.assign_employee_to_position(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-2",
                position_id=position.id,
                employee_id=uuid4(),
            )


# ============================================================
# Org Unit Tests
# ============================================================


class TestOrgUnits:
    def test_create_org_unit_basic(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        unit = svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SALES",
            name="Sales Department",
            unit_type=OrgUnitType.DEPARTMENT,
            cost_center="CC-100",
            location="Building A",
        )

        assert unit.code == "SALES"
        assert unit.name == "Sales Department"
        assert unit.unit_type == OrgUnitType.DEPARTMENT
        assert unit.cost_center == "CC-100"
        assert unit.location == "Building A"
        assert unit.is_active is True

    def test_create_child_unit(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        team = svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="BACKEND",
            name="Backend Team",
            unit_type=OrgUnitType.TEAM,
            parent_id=department["unit"].id,
        )

        assert team.parent_id == department["unit"].id

    def test_create_unit_duplicate_code_fails(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="UNIQUE",
            name="First",
            unit_type=OrgUnitType.DEPARTMENT,
        )

        with pytest.raises(ValueError, match="code already exists"):
            svc.create_org_unit(
                actor_id="hr1",
                actor_roles=hr_roles,
                correlation_id="cor-2",
                code="UNIQUE",
                name="Second",
                unit_type=OrgUnitType.DEPARTMENT,
            )

    def test_create_unit_invalid_parent_fails(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="parent_id not found"):
            svc.create_org_unit(
                actor_id="hr1",
                actor_roles=hr_roles,
                correlation_id="cor-1",
                code="ORPHAN",
                name="Orphan",
                unit_type=OrgUnitType.TEAM,
                parent_id=uuid4(),  # Non-existent
            )

    def test_update_org_unit(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        updated = svc.update_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            unit_id=department["unit"].id,
            name="Engineering Dept",
            location="Building B",
        )

        assert updated.name == "Engineering Dept"
        assert updated.location == "Building B"
        assert updated.code == department["unit"].code  # Unchanged

    def test_get_org_tree(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        # Create hierarchy
        corp = svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="CORP",
            name="Corporation",
            unit_type=OrgUnitType.COMPANY,
        )
        eng = svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            code="ENG",
            name="Engineering",
            unit_type=OrgUnitType.DEPARTMENT,
            parent_id=corp.id,
        )
        svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-3",
            code="BACKEND",
            name="Backend",
            unit_type=OrgUnitType.TEAM,
            parent_id=eng.id,
        )

        tree = svc.get_org_tree(actor_roles=hr_roles)

        assert len(tree) == 1  # One root
        assert tree[0]["code"] == "CORP"
        assert len(tree[0]["children"]) == 1  # One department
        assert tree[0]["children"][0]["code"] == "ENG"
        assert len(tree[0]["children"][0]["children"]) == 1  # One team


# ============================================================
# Position Tests
# ============================================================


class TestPositions:
    def test_create_position_basic(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        position = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Senior Software Engineer",
            org_unit_id=department["unit"].id,
            position_type=PositionType.FULL_TIME,
            headcount=2,
            grade="L5",
            job_family="Engineering",
        )

        assert position.code == "SWE-001"
        assert position.title == "Senior Software Engineer"
        assert position.headcount == 2
        assert position.status == PositionStatus.OPEN
        assert position.grade == "L5"

    def test_create_position_with_reports_to(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        manager_pos = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="MGR-001",
            title="Engineering Manager",
            org_unit_id=department["unit"].id,
        )
        engineer_pos = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
            reports_to_position_id=manager_pos.id,
        )

        assert engineer_pos.reports_to_position_id == manager_pos.id

    def test_create_position_invalid_org_unit_fails(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="org_unit_id not found"):
            svc.create_position(
                actor_id="hr1",
                actor_roles=hr_roles,
                correlation_id="cor-1",
                code="SWE-001",
                title="Engineer",
                org_unit_id=uuid4(),
            )

    def test_list_positions_by_status(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        pos1 = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="POS-001",
            title="Position 1",
            org_unit_id=department["unit"].id,
        )
        pos2 = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            code="POS-002",
            title="Position 2",
            org_unit_id=department["unit"].id,
        )

        # Put one on hold
        svc.update_position_status(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-3",
            position_id=pos2.id,
            status=PositionStatus.ON_HOLD,
        )

        open_positions = svc.list_positions(
            actor_roles=hr_roles, status=PositionStatus.OPEN
        )
        assert len(open_positions) == 1
        assert open_positions[0].id == pos1.id


# ============================================================
# Assignment Tests
# ============================================================


class TestAssignments:
    def test_assign_employee_to_position(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        position = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
        )
        employee_id = uuid4()

        assignment = svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            position_id=position.id,
            employee_id=employee_id,
        )

        assert assignment.position_id == position.id
        assert assignment.employee_id == employee_id
        assert assignment.status == AssignmentStatus.ACTIVE
        assert assignment.is_primary is True

        # Position should be filled now
        updated_pos = svc.get_position(actor_roles=hr_roles, position_id=position.id)
        assert updated_pos.status == PositionStatus.FILLED

    def test_assign_exceeds_headcount_fails(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        position = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
            headcount=1,  # Only 1 slot
        )

        # First assignment succeeds
        svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            position_id=position.id,
            employee_id=uuid4(),
        )

        # Second assignment fails
        with pytest.raises(ValueError, match="headcount already filled"):
            svc.assign_employee_to_position(
                actor_id="hr1",
                actor_roles=hr_roles,
                correlation_id="cor-3",
                position_id=position.id,
                employee_id=uuid4(),
            )

    def test_end_assignment(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        position = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
        )
        employee_id = uuid4()
        assignment = svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            position_id=position.id,
            employee_id=employee_id,
        )

        ended = svc.end_assignment(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-3",
            assignment_id=assignment.id,
            reason="Resigned",
        )

        assert ended.status == AssignmentStatus.ENDED
        assert ended.end_date == date.today()

        # Position should be open again
        updated_pos = svc.get_position(actor_roles=hr_roles, position_id=position.id)
        assert updated_pos.status == PositionStatus.OPEN

    def test_get_employee_assignments(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        pos1 = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
        )
        pos2 = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            code="SWE-002",
            title="Sr Software Engineer",
            org_unit_id=department["unit"].id,
        )

        employee_id = uuid4()
        svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-3",
            position_id=pos1.id,
            employee_id=employee_id,
        )
        svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-4",
            position_id=pos2.id,
            employee_id=employee_id,
            is_primary=False,
        )

        assignments = svc.get_employee_assignments(
            actor_roles=hr_roles, employee_id=employee_id
        )
        assert len(assignments) == 2


# ============================================================
# Reporting Relation Tests
# ============================================================


class TestReportingRelations:
    def test_set_reporting_relation(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        manager_id = uuid4()
        employee_id = uuid4()

        relation = svc.set_reporting_relation(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            employee_id=employee_id,
            manager_id=manager_id,
        )

        assert relation.employee_id == employee_id
        assert relation.manager_id == manager_id
        assert relation.is_primary is True
        assert relation.relation_type == "direct"

    def test_cannot_report_to_self(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        employee_id = uuid4()

        with pytest.raises(ValueError, match="cannot report to themselves"):
            svc.set_reporting_relation(
                actor_id="hr1",
                actor_roles=hr_roles,
                correlation_id="cor-1",
                employee_id=employee_id,
                manager_id=employee_id,
            )

    def test_get_direct_reports(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        manager_id = uuid4()
        emp1_id = uuid4()
        emp2_id = uuid4()

        svc.set_reporting_relation(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            employee_id=emp1_id,
            manager_id=manager_id,
        )
        svc.set_reporting_relation(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            employee_id=emp2_id,
            manager_id=manager_id,
        )

        reports = svc.get_direct_reports(actor_roles=hr_roles, manager_id=manager_id)
        assert len(reports) == 2
        assert emp1_id in reports
        assert emp2_id in reports

    def test_get_manager(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        manager_id = uuid4()
        employee_id = uuid4()

        svc.set_reporting_relation(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            employee_id=employee_id,
            manager_id=manager_id,
        )

        result = svc.get_manager(actor_roles=hr_roles, employee_id=employee_id)
        assert result == manager_id

    def test_change_manager_ends_previous_relation(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        manager1_id = uuid4()
        manager2_id = uuid4()
        employee_id = uuid4()

        svc.set_reporting_relation(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            employee_id=employee_id,
            manager_id=manager1_id,
        )
        svc.set_reporting_relation(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            employee_id=employee_id,
            manager_id=manager2_id,
        )

        # Should have new manager
        result = svc.get_manager(actor_roles=hr_roles, employee_id=employee_id)
        assert result == manager2_id


# ============================================================
# Headcount Analytics Tests
# ============================================================


class TestHeadcountAnalytics:
    def test_get_headcount_summary(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        # Create positions with different headcounts
        pos1 = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
            headcount=3,
        )
        pos2 = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            code="MGR-001",
            title="Manager",
            org_unit_id=department["unit"].id,
            headcount=1,
        )

        # Fill one position
        svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-3",
            position_id=pos1.id,
            employee_id=uuid4(),
        )
        svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-4",
            position_id=pos2.id,
            employee_id=uuid4(),
        )

        summary = svc.get_headcount_summary(
            actor_roles=hr_roles, org_unit_id=department["unit"].id
        )

        assert summary["total_positions"] == 2
        assert summary["total_headcount"] == 4  # 3 + 1
        assert summary["filled"] == 2
        assert summary["open"] == 2
        assert summary["fill_rate"] == 50.0

    def test_headcount_summary_all_units(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Software Engineer",
            org_unit_id=department["unit"].id,
            headcount=5,
        )

        summary = svc.get_headcount_summary(actor_roles=hr_roles)

        assert summary["total_headcount"] == 5
        assert summary["open"] == 5
        assert summary["fill_rate"] == 0.0


# ============================================================
# Audit Tests
# ============================================================


class TestAudit:
    def test_audit_trail_for_org_unit_operations(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        unit = svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="DEPT",
            name="Department",
            unit_type=OrgUnitType.DEPARTMENT,
        )
        svc.update_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            unit_id=unit.id,
            name="Updated Department",
        )

        events = svc.list_audit_events(actor_roles=hr_roles)

        assert len(events) >= 2
        actions = [e.action for e in events]
        assert "org.unit.create" in actions
        assert "org.unit.update" in actions

    def test_audit_trail_for_position_operations(
        self, svc: OrgStructureService, hr_roles: set[str], department: dict
    ) -> None:
        position = svc.create_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-1",
            code="SWE-001",
            title="Engineer",
            org_unit_id=department["unit"].id,
        )
        svc.assign_employee_to_position(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="cor-2",
            position_id=position.id,
            employee_id=uuid4(),
        )

        events = svc.list_audit_events(actor_roles=hr_roles)

        actions = [e.action for e in events]
        assert "org.position.create" in actions
        assert "org.assignment.create" in actions

    def test_audit_includes_correlation_id(
        self, svc: OrgStructureService, hr_roles: set[str]
    ) -> None:
        svc.create_org_unit(
            actor_id="hr1",
            actor_roles=hr_roles,
            correlation_id="trace-abc123",
            code="DEPT",
            name="Department",
            unit_type=OrgUnitType.DEPARTMENT,
        )

        events = svc.list_audit_events(actor_roles=hr_roles)

        assert any(e.correlation_id == "trace-abc123" for e in events)

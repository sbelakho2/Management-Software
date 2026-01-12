"""Tests for MRP-lite Service (Development Plan 22.7)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.production.mrp_lite import (
    MRPService,
    RequirementType,
    SuggestionStatus,
    DemandType,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> MRPService:
    return MRPService()


@pytest.fixture
def ops_roles() -> set[str]:
    return {"ops"}


@pytest.fixture
def planner_roles() -> set[str]:
    return {"planner"}


@pytest.fixture
def reader_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def norole() -> set[str]:
    return {"guest"}


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_register_bom_requires_write_role(
        self, svc: MRPService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="MRP write role required"):
            svc.register_bom(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                parent_item_id="ASSY-001",
                components=[("COMP-001", Decimal("2"), Decimal("0"))],
            )

    def test_set_inventory_requires_write_role(
        self, svc: MRPService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="MRP write role required"):
            svc.set_inventory_level(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                item_id="PART-001",
                on_hand=Decimal("100"),
            )

    def test_add_demand_requires_write_role(
        self, svc: MRPService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="MRP write role required"):
            svc.add_demand(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
                item_id="PART-001",
                quantity=Decimal("10"),
                required_date=date.today(),
                demand_type=DemandType.SALES_ORDER,
            )

    def test_run_mrp_requires_write_role(
        self, svc: MRPService, norole: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="MRP write role required"):
            svc.run_mrp(
                actor_id="guest",
                actor_roles=norole,
                correlation_id="cor-1",
            )

    def test_approve_suggestion_requires_approve_role(
        self, svc: MRPService, ops_roles: set[str], reader_roles: set[str]
    ) -> None:
        # Setup demand and run MRP
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        with pytest.raises(PermissionError, match="MRP approve role required"):
            svc.approve_suggestion(
                actor_id="auditor1",
                actor_roles=reader_roles,
                correlation_id="cor-3",
                suggestion_id=suggestion_id,
            )

    def test_reader_can_list_suggestions(
        self, svc: MRPService, ops_roles: set[str], reader_roles: set[str]
    ) -> None:
        # Setup demand and run MRP
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        # Auditor can read
        suggestions = svc.list_suggestions(actor_roles=reader_roles)
        assert len(suggestions) == 1


# ============================================================
# BOM Tests
# ============================================================


class TestBOM:
    def test_register_bom_basic(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        components = svc.register_bom(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            parent_item_id="ASSY-001",
            components=[
                ("COMP-001", Decimal("2"), Decimal("0.05")),
                ("COMP-002", Decimal("1"), Decimal("0")),
            ],
        )

        assert len(components) == 2
        assert components[0].parent_item_id == "ASSY-001"
        assert components[0].component_item_id == "COMP-001"
        assert components[0].quantity_per == Decimal("2")
        assert components[0].scrap_factor == Decimal("0.05")

    def test_register_bom_invalid_quantity_fails(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="quantity_per must be positive"):
            svc.register_bom(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id="cor-1",
                parent_item_id="ASSY-001",
                components=[("COMP-001", Decimal("0"), Decimal("0"))],
            )


# ============================================================
# Inventory Tests
# ============================================================


class TestInventory:
    def test_set_inventory_level(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        level = svc.set_inventory_level(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            on_hand=Decimal("100"),
            on_order=Decimal("50"),
            reserved=Decimal("20"),
            safety_stock=Decimal("10"),
        )

        assert level.item_id == "PART-001"
        assert level.on_hand == Decimal("100")
        assert level.on_order == Decimal("50")
        assert level.reserved == Decimal("20")
        assert level.safety_stock == Decimal("10")

    def test_set_item_type(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.set_item_type(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            requirement_type=RequirementType.BUY,
            lead_time_days=7,
        )

        # Verify via suggestion type in MRP run
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=14),
            demand_type=DemandType.SALES_ORDER,
        )

        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-3",
        )

        assert len(result.suggestions) == 1
        assert result.suggestions[0].requirement_type == RequirementType.BUY
        assert result.suggestions[0].lead_time_days == 7


# ============================================================
# Demand Tests
# ============================================================


class TestDemand:
    def test_add_demand(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        demand = svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("25"),
            required_date=date.today() + timedelta(days=10),
            demand_type=DemandType.SALES_ORDER,
            source_id="SO-001",
        )

        assert demand.item_id == "PART-001"
        assert demand.quantity == Decimal("25")
        assert demand.demand_type == DemandType.SALES_ORDER
        assert demand.source_id == "SO-001"

    def test_add_demand_invalid_quantity_fails(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="quantity must be positive"):
            svc.add_demand(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id="cor-1",
                item_id="PART-001",
                quantity=Decimal("-5"),
                required_date=date.today(),
                demand_type=DemandType.SALES_ORDER,
            )

    def test_remove_demand(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        demand = svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today(),
            demand_type=DemandType.FORECAST,
        )

        svc.remove_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            demand_id=demand.id,
        )

        demands = svc.list_demands(actor_roles=ops_roles)
        assert len(demands) == 0

    def test_list_demands_by_item(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today(),
            demand_type=DemandType.SALES_ORDER,
        )
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="PART-002",
            quantity=Decimal("20"),
            required_date=date.today(),
            demand_type=DemandType.SALES_ORDER,
        )

        demands = svc.list_demands(actor_roles=ops_roles, item_id="PART-001")
        assert len(demands) == 1
        assert demands[0].item_id == "PART-001"


# ============================================================
# MRP Run Tests
# ============================================================


class TestMRPRun:
    def test_run_mrp_creates_buy_suggestion(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        # No inventory, so demand creates shortage
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("100"),
            required_date=date.today() + timedelta(days=14),
            demand_type=DemandType.SALES_ORDER,
        )

        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        assert len(result.suggestions) == 1
        assert result.suggestions[0].item_id == "PART-001"
        assert result.suggestions[0].quantity == Decimal("100")
        assert result.suggestions[0].requirement_type == RequirementType.BUY  # Default
        assert result.suggestions[0].status == SuggestionStatus.PENDING
        assert "PART-001" in result.shortage_items

    def test_run_mrp_accounts_for_inventory(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        # Set inventory
        svc.set_inventory_level(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            on_hand=Decimal("60"),
            on_order=Decimal("20"),
            reserved=Decimal("10"),
            safety_stock=Decimal("10"),
        )  # Available = 60 + 20 - 10 - 10 = 60

        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="PART-001",
            quantity=Decimal("100"),
            required_date=date.today() + timedelta(days=14),
            demand_type=DemandType.SALES_ORDER,
        )

        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-3",
        )

        # Net = 100 - 60 = 40
        assert len(result.suggestions) == 1
        assert result.suggestions[0].quantity == Decimal("40")

    def test_run_mrp_no_shortage_no_suggestion(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        # Enough inventory
        svc.set_inventory_level(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            on_hand=Decimal("200"),
        )

        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="PART-001",
            quantity=Decimal("100"),
            required_date=date.today() + timedelta(days=14),
            demand_type=DemandType.SALES_ORDER,
        )

        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-3",
        )

        assert len(result.suggestions) == 0
        assert len(result.shortage_items) == 0

    def test_run_mrp_explodes_bom(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        # Setup BOM: ASSY-001 needs 2x COMP-001
        svc.register_bom(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            parent_item_id="ASSY-001",
            components=[("COMP-001", Decimal("2"), Decimal("0.1"))],  # 10% scrap
        )

        svc.set_item_type(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="ASSY-001",
            requirement_type=RequirementType.BUILD,
        )

        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-3",
            item_id="ASSY-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=14),
            demand_type=DemandType.SALES_ORDER,
        )

        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-4",
        )

        # Should have 2 suggestions: 1 for ASSY-001 (build), 1 for COMP-001 (buy)
        assert len(result.suggestions) == 2

        assy_suggestion = next(s for s in result.suggestions if s.item_id == "ASSY-001")
        comp_suggestion = next(s for s in result.suggestions if s.item_id == "COMP-001")

        assert assy_suggestion.requirement_type == RequirementType.BUILD
        assert assy_suggestion.quantity == Decimal("10")

        # Component: 10 * 2 * 1.1 = 22
        assert comp_suggestion.requirement_type == RequirementType.BUY
        assert comp_suggestion.quantity == Decimal("22")


# ============================================================
# Suggestion Approval Tests
# ============================================================


class TestSuggestionApproval:
    def test_approve_suggestion(
        self, svc: MRPService, ops_roles: set[str], planner_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        # Different user approves
        approved = svc.approve_suggestion(
            actor_id="manager1",
            actor_roles=planner_roles,
            correlation_id="cor-3",
            suggestion_id=suggestion_id,
        )

        assert approved.status == SuggestionStatus.APPROVED
        assert approved.approved_by == "manager1"
        assert approved.approved_at is not None

    def test_creator_cannot_approve_own_suggestion(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        # Same user tries to approve - SoD violation
        with pytest.raises(PermissionError, match="cannot approve their own"):
            svc.approve_suggestion(
                actor_id="planner1",
                actor_roles=ops_roles,
                correlation_id="cor-3",
                suggestion_id=suggestion_id,
            )

    def test_reject_suggestion(
        self, svc: MRPService, ops_roles: set[str], planner_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        rejected = svc.reject_suggestion(
            actor_id="manager1",
            actor_roles=planner_roles,
            correlation_id="cor-3",
            suggestion_id=suggestion_id,
            reason="Vendor on hold",
        )

        assert rejected.status == SuggestionStatus.REJECTED
        assert rejected.rejection_reason == "Vendor on hold"

    def test_reject_requires_reason(
        self, svc: MRPService, ops_roles: set[str], planner_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        with pytest.raises(ValueError, match="rejection reason required"):
            svc.reject_suggestion(
                actor_id="manager1",
                actor_roles=planner_roles,
                correlation_id="cor-3",
                suggestion_id=suggestion_id,
                reason="",
            )

    def test_release_approved_suggestion(
        self, svc: MRPService, ops_roles: set[str], planner_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        svc.approve_suggestion(
            actor_id="manager1",
            actor_roles=planner_roles,
            correlation_id="cor-3",
            suggestion_id=suggestion_id,
        )

        released = svc.release_suggestion(
            actor_id="manager1",
            actor_roles=planner_roles,
            correlation_id="cor-4",
            suggestion_id=suggestion_id,
        )

        assert released.status == SuggestionStatus.RELEASED

    def test_cannot_release_pending_suggestion(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )
        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )

        suggestion_id = result.suggestions[0].id

        with pytest.raises(ValueError, match="Only approved suggestions can be released"):
            svc.release_suggestion(
                actor_id="manager1",
                actor_roles=ops_roles,
                correlation_id="cor-3",
                suggestion_id=suggestion_id,
            )


# ============================================================
# Reporting Tests
# ============================================================


class TestReporting:
    def test_get_item_requirements(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.set_inventory_level(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            on_hand=Decimal("50"),
            on_order=Decimal("30"),
            reserved=Decimal("10"),
            safety_stock=Decimal("5"),
        )

        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="PART-001",
            quantity=Decimal("100"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )

        reqs = svc.get_item_requirements(actor_roles=ops_roles, item_id="PART-001")

        assert reqs["item_id"] == "PART-001"
        assert reqs["total_demand"] == Decimal("100")
        assert reqs["on_hand"] == Decimal("50")
        assert reqs["on_order"] == Decimal("30")
        assert reqs["available"] == Decimal("65")  # 50 + 30 - 10 - 5
        assert reqs["net_requirement"] == Decimal("35")  # 100 - 65

    def test_list_runs(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )

        svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
        )
        svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-3",
        )

        runs = svc.list_runs(actor_roles=ops_roles)
        assert len(runs) == 2


# ============================================================
# Audit Tests
# ============================================================


class TestAudit:
    def test_audit_trail_for_mrp_operations(
        self, svc: MRPService, ops_roles: set[str], planner_roles: set[str]
    ) -> None:
        svc.register_bom(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            parent_item_id="ASSY-001",
            components=[("COMP-001", Decimal("1"), Decimal("0"))],
        )

        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )

        result = svc.run_mrp(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="cor-3",
        )

        suggestion_id = result.suggestions[0].id
        svc.approve_suggestion(
            actor_id="manager1",
            actor_roles=planner_roles,
            correlation_id="cor-4",
            suggestion_id=suggestion_id,
        )

        events = svc.list_audit_events(actor_roles=ops_roles)

        actions = [e.action for e in events]
        assert "mrp.bom.register" in actions
        assert "mrp.demand.add" in actions
        assert "mrp.run" in actions
        assert "mrp.suggestion.approve" in actions

    def test_audit_includes_correlation_id(
        self, svc: MRPService, ops_roles: set[str]
    ) -> None:
        svc.add_demand(
            actor_id="planner1",
            actor_roles=ops_roles,
            correlation_id="trace-xyz789",
            item_id="PART-001",
            quantity=Decimal("10"),
            required_date=date.today() + timedelta(days=7),
            demand_type=DemandType.SALES_ORDER,
        )

        events = svc.list_audit_events(actor_roles=ops_roles)

        assert any(e.correlation_id == "trace-xyz789" for e in events)

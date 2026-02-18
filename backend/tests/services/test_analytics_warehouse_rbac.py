"""Tests for Analytics Warehouse RBAC scoping and cross-domain extraction.

Covers:
- allowed_fact_types RBAC mapping per role
- get_role_scoped_fact_counts filtering
- get_role_scoped_records filtering
- extract_finance_summary live queries
- extract_hr_summary live queries
- extract_inventory_summary live queries
- build_cross_domain_summary RBAC gating
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.ops.analytics_warehouse import (
    AnalyticsWarehouseService,
    FactType,
)


@pytest.fixture
def svc() -> AnalyticsWarehouseService:
    return AnalyticsWarehouseService()


# ---------------------------------------------------------------------------
# Role tuples
# ---------------------------------------------------------------------------
ADMIN_ROLES = ("admin",)
CEO_ROLES = ("ceo",)
FINANCE_ROLES = ("finance",)
HR_ROLES = ("hr",)
OPS_ROLES = ("ops",)
QUALITY_ROLES = ("quality",)
VIEWER_ROLES = ("viewer",)
BI_ROLES = ("bi",)


# ========================== allowed_fact_types =============================

class TestAllowedFactTypes:
    """Verify that each role sees exactly the fact types it should."""

    def test_admin_sees_all(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=ADMIN_ROLES)
        assert allowed == {ft.value for ft in FactType}

    def test_ceo_sees_all(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=CEO_ROLES)
        assert allowed == {ft.value for ft in FactType}

    def test_finance_sees_only_finance(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=FINANCE_ROLES)
        expected = {
            FactType.FINANCIAL_TRANSACTION.value,
            FactType.AP_INVOICE.value,
            FactType.AR_INVOICE.value,
            FactType.COST_ROLLUP.value,
        }
        assert allowed == expected
        # Ensure no ops leakage
        assert FactType.WORK_ORDER.value not in allowed
        assert FactType.HEADCOUNT_SNAPSHOT.value not in allowed

    def test_hr_sees_only_hr(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=HR_ROLES)
        expected = {
            FactType.HEADCOUNT_SNAPSHOT.value,
            FactType.EMPLOYEE_TURNOVER.value,
            FactType.TIME_TO_HIRE.value,
            FactType.TRAINING_COMPLIANCE.value,
        }
        assert allowed == expected
        assert FactType.WORK_ORDER.value not in allowed
        assert FactType.FINANCIAL_TRANSACTION.value not in allowed

    def test_ops_sees_ops_and_inventory(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=OPS_ROLES)
        assert FactType.WORK_ORDER.value in allowed
        assert FactType.CYCLE_TIME.value in allowed
        assert FactType.INVENTORY_LEVEL.value in allowed
        assert FactType.STOCK_MOVEMENT.value in allowed
        # No finance or HR
        assert FactType.FINANCIAL_TRANSACTION.value not in allowed
        assert FactType.HEADCOUNT_SNAPSHOT.value not in allowed

    def test_quality_sees_quality(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=QUALITY_ROLES)
        assert FactType.WORK_ORDER.value in allowed
        assert FactType.NON_CONFORMANCE.value in allowed
        assert FactType.QUALITY_METRIC.value in allowed
        assert FactType.INVENTORY_LEVEL.value not in allowed

    def test_viewer_sees_nothing(self, svc: AnalyticsWarehouseService) -> None:
        allowed = svc.allowed_fact_types(actor_roles=VIEWER_ROLES)
        assert allowed == set()

    def test_multi_role_union(self, svc: AnalyticsWarehouseService) -> None:
        """A user with both finance and hr roles should see both sets."""
        allowed = svc.allowed_fact_types(actor_roles=("finance", "hr"))
        assert FactType.FINANCIAL_TRANSACTION.value in allowed
        assert FactType.HEADCOUNT_SNAPSHOT.value in allowed
        assert len(allowed) == 8  # 4 finance + 4 hr


# ======================= get_role_scoped_fact_counts =======================

@pytest.mark.asyncio
class TestRoleScopedFactCounts:
    async def test_viewer_cannot_access(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        with pytest.raises(PermissionError):
            await svc.get_role_scoped_fact_counts(
                async_session, actor_roles=VIEWER_ROLES
            )

    async def test_admin_all_facts_counted(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        # Create a snapshot with mixed fact types
        snap = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        records = [
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001"},
            {"_fact_type": FactType.FINANCIAL_TRANSACTION, "txn_id": "FIN-001"},
            {"_fact_type": FactType.HEADCOUNT_SNAPSHOT, "emp_id": "EMP-001"},
            {"_fact_type": FactType.INVENTORY_LEVEL, "sku": "SKU-001"},
        ]
        await svc.run_snapshot(
            async_session, snap.id, actor_roles=ADMIN_ROLES, records=records
        )

        counts = await svc.get_role_scoped_fact_counts(
            async_session, actor_roles=ADMIN_ROLES
        )
        assert len(counts) == 4

    async def test_finance_only_sees_finance_counts(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        snap = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        records = [
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001"},
            {"_fact_type": FactType.FINANCIAL_TRANSACTION, "txn_id": "FIN-001"},
            {"_fact_type": FactType.HEADCOUNT_SNAPSHOT, "emp_id": "EMP-001"},
        ]
        await svc.run_snapshot(
            async_session, snap.id, actor_roles=ADMIN_ROLES, records=records
        )

        counts = await svc.get_role_scoped_fact_counts(
            async_session, actor_roles=FINANCE_ROLES
        )
        # Finance should only see financial_transaction
        assert FactType.FINANCIAL_TRANSACTION.value in counts
        assert FactType.WORK_ORDER.value not in counts
        assert FactType.HEADCOUNT_SNAPSHOT.value not in counts

    async def test_hr_only_sees_hr_counts(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        snap = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        records = [
            {"_fact_type": FactType.HEADCOUNT_SNAPSHOT, "emp_id": "EMP-001"},
            {"_fact_type": FactType.EMPLOYEE_TURNOVER, "turnover_id": "T-001"},
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001"},
        ]
        await svc.run_snapshot(
            async_session, snap.id, actor_roles=ADMIN_ROLES, records=records
        )

        counts = await svc.get_role_scoped_fact_counts(
            async_session, actor_roles=HR_ROLES
        )
        assert FactType.HEADCOUNT_SNAPSHOT.value in counts
        assert FactType.EMPLOYEE_TURNOVER.value in counts
        assert FactType.WORK_ORDER.value not in counts


# ======================= get_role_scoped_records ===========================

@pytest.mark.asyncio
class TestRoleScopedRecords:
    async def test_viewer_cannot_access(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        with pytest.raises(PermissionError):
            await svc.get_role_scoped_records(
                async_session, actor_roles=VIEWER_ROLES
            )

    async def test_finance_only_gets_finance_records(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        snap = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        records = [
            {"_fact_type": FactType.AP_INVOICE, "inv_id": "AP-001"},
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001"},
            {"_fact_type": FactType.HEADCOUNT_SNAPSHOT, "emp_id": "EMP-001"},
        ]
        await svc.run_snapshot(
            async_session, snap.id, actor_roles=ADMIN_ROLES, records=records
        )

        recs = await svc.get_role_scoped_records(
            async_session, actor_roles=FINANCE_ROLES
        )
        fact_types = {r.fact_type for r in recs}
        assert FactType.AP_INVOICE.value in fact_types
        assert FactType.WORK_ORDER.value not in fact_types
        assert FactType.HEADCOUNT_SNAPSHOT.value not in fact_types

    async def test_requesting_disallowed_fact_type_returns_empty(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        snap = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        records = [
            {"_fact_type": FactType.WORK_ORDER, "wo_id": "WO-001"},
        ]
        await svc.run_snapshot(
            async_session, snap.id, actor_roles=ADMIN_ROLES, records=records
        )

        # Finance can't request WORK_ORDER
        recs = await svc.get_role_scoped_records(
            async_session,
            actor_roles=FINANCE_ROLES,
            fact_type=FactType.WORK_ORDER,
        )
        assert recs == []

    async def test_limit_respected(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        snap = await svc.create_snapshot(
            async_session,
            snapshot_date=date.today(),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        records = [
            {"_fact_type": FactType.WORK_ORDER, "wo_id": f"WO-{i}"}
            for i in range(10)
        ]
        await svc.run_snapshot(
            async_session, snap.id, actor_roles=ADMIN_ROLES, records=records
        )

        recs = await svc.get_role_scoped_records(
            async_session, actor_roles=ADMIN_ROLES, limit=3
        )
        assert len(recs) == 3


# ======================= Cross-Domain Extraction ===========================

@pytest.mark.asyncio
class TestExtractFinanceSummary:
    async def test_returns_expected_keys(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        result = await svc.extract_finance_summary(async_session)
        expected_keys = {
            "ar_outstanding_count",
            "ar_overdue_count",
            "ap_unpaid_count",
            "open_po_count",
            "journal_entries_mtd",
        }
        assert set(result.keys()) == expected_keys
        # With empty DB everything should be 0
        for v in result.values():
            assert v == 0


@pytest.mark.asyncio
class TestExtractHRSummary:
    async def test_returns_expected_keys(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        result = await svc.extract_hr_summary(async_session)
        expected_keys = {
            "active_employees",
            "terminated_last_90d",
            "turnover_rate_pct",
            "open_positions",
            "active_applications",
            "pending_leave_requests",
        }
        assert set(result.keys()) == expected_keys
        for k, v in result.items():
            assert isinstance(v, (int, float)), f"{k} should be numeric"

    async def test_turnover_rate_is_zero_with_no_employees(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        result = await svc.extract_hr_summary(async_session)
        assert result["turnover_rate_pct"] == 0.0


@pytest.mark.asyncio
class TestExtractInventorySummary:
    async def test_returns_expected_keys(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        result = await svc.extract_inventory_summary(async_session)
        expected_keys = {
            "tracked_skus",
            "zero_stock_items",
            "pending_stock_moves",
            "open_mrp_suggestions",
        }
        assert set(result.keys()) == expected_keys
        for v in result.values():
            assert v == 0


# ======================= build_cross_domain_summary ========================

@pytest.mark.asyncio
class TestBuildCrossDomainSummary:
    async def test_admin_gets_all_domains(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=ADMIN_ROLES
        )
        assert "finance" in summary
        assert "hr" in summary
        assert "inventory" in summary

    async def test_ceo_gets_all_domains(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=CEO_ROLES
        )
        assert "finance" in summary
        assert "hr" in summary
        assert "inventory" in summary

    async def test_finance_gets_only_finance(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=FINANCE_ROLES
        )
        assert "finance" in summary
        assert "hr" not in summary
        assert "inventory" not in summary

    async def test_hr_gets_only_hr(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=HR_ROLES
        )
        assert "hr" in summary
        assert "finance" not in summary
        assert "inventory" not in summary

    async def test_ops_gets_inventory_no_finance_no_hr(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=OPS_ROLES
        )
        assert "inventory" in summary
        assert "finance" not in summary
        assert "hr" not in summary

    async def test_quality_gets_nothing_cross_domain(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        """Quality role has no finance/hr/inventory fact access."""
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=QUALITY_ROLES
        )
        # Quality doesn't see FINANCIAL_TRANSACTION, HEADCOUNT_SNAPSHOT, or INVENTORY_LEVEL
        assert "finance" not in summary
        assert "hr" not in summary
        assert "inventory" not in summary

    async def test_multi_role_builds_union(
        self, svc: AnalyticsWarehouseService, async_session: AsyncSession
    ) -> None:
        summary = await svc.build_cross_domain_summary(
            async_session, actor_roles=("finance", "hr")
        )
        assert "finance" in summary
        assert "hr" in summary
        assert "inventory" not in summary

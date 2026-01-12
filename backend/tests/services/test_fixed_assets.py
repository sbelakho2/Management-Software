"""Tests for Fixed Assets (Accounting) service.

Covers Section 22.5:
- Capitalization workflow
- Depreciation schedules (monthly)
- Asset events (transfer, impairment, disposal)
- RBAC enforcement
- GL integration (optional)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.finance.fixed_assets import (
    AssetEventType,
    DepreciationMethod,
    FixedAssetStatus,
    FixedAssetsConfig,
    FixedAssetsService,
)


# ---------------------- Fixtures ----------------------


@pytest.fixture
def svc() -> FixedAssetsService:
    """Fresh fixed assets service instance (no GL)."""
    return FixedAssetsService()


@pytest.fixture
def svc_with_gl(accounting_ledger):
    """Fixed assets service with GL integration."""
    return FixedAssetsService(ledger=accounting_ledger)


@pytest.fixture
def accounting_ledger():
    """Minimal in-memory accounting ledger for GL tests."""
    from sensei.services.finance.accounting_ledger import AccountingLedgerService, AccountType

    ledger = AccountingLedgerService()

    # Create minimal COA for fixed assets
    roles = ["accountant"]
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="1500",
        name="Fixed Assets",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="1590",
        name="Accumulated Depreciation",
        account_type=AccountType.ASSET,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="2100",
        name="AP Clearing",
        account_type=AccountType.LIABILITY,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="6100",
        name="Depreciation Expense",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="6200",
        name="Impairment Loss",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )
    ledger.upsert_account(
        actor_id="setup",
        actor_roles=roles,
        correlation_id="setup-coa",
        code="6300",
        name="Gain/Loss on Disposal",
        account_type=AccountType.EXPENSE,
        currency="EUR",
    )

    return ledger


# ---------------------- RBAC Tests ----------------------


class TestFixedAssetsRBAC:
    """Test RBAC enforcement for fixed assets operations."""

    def test_unauthorized_read_raises(self, svc: FixedAssetsService):
        with pytest.raises(PermissionError, match="Finance read role required"):
            svc.list_assets(actor_roles=["operator"])

    def test_unauthorized_write_raises(self, svc: FixedAssetsService):
        with pytest.raises(PermissionError, match="Finance write role required"):
            svc.capitalize_from_source(
                actor_id="u1",
                actor_roles=["viewer"],
                correlation_id="c1",
                asset_tag="FA-001",
                name="Test Asset",
                acquisition_cost=Decimal("10000"),
                useful_life_months=60,
            )

    def test_unauthorized_approve_raises(self, svc: FixedAssetsService):
        # First create asset with valid roles
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
        )
        # Now try depreciation with invalid role
        with pytest.raises(PermissionError, match="Finance approve role required"):
            svc.post_monthly_depreciation(
                actor_id="op",
                actor_roles=["operator"],
                correlation_id="c2",
                asset_id=asset.id,
                period_key="2026-01",
                post_date=date(2026, 1, 31),
            )

    def test_finance_roles_can_read(self, svc: FixedAssetsService):
        for role in ["admin", "ceo", "exec", "gm", "finance", "accountant", "auditor"]:
            assets = svc.list_assets(actor_roles=[role])
            assert assets == []

    def test_finance_roles_can_write(self, svc: FixedAssetsService):
        for i, role in enumerate(
            ["admin", "ceo", "exec", "gm", "finance", "accountant"]
        ):
            asset = svc.capitalize_from_source(
                actor_id=f"user-{i}",
                actor_roles=[role],
                correlation_id=f"c-{i}",
                asset_tag=f"FA-{i:03d}",
                name=f"Asset {i}",
                acquisition_cost=Decimal("1000"),
                useful_life_months=12,
            )
            assert asset is not None


# ---------------------- Capitalization Tests ----------------------


class TestCapitalization:
    """Test fixed asset capitalization workflow."""

    def test_capitalize_basic(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="CNC Machine",
            acquisition_cost=Decimal("50000.00"),
            residual_value=Decimal("5000.00"),
            useful_life_months=60,
            currency="EUR",
            capitalization_date=date(2026, 1, 1),
            in_service_date=date(2026, 1, 15),
            location="Plant A",
            cost_center="CC100",
        )

        assert asset.asset_tag == "FA-001"
        assert asset.name == "CNC Machine"
        assert asset.acquisition_cost == Decimal("50000.00")
        assert asset.residual_value == Decimal("5000.00")
        assert asset.useful_life_months == 60
        assert asset.depreciable_base == Decimal("45000.00")
        assert asset.carrying_amount == Decimal("50000.00")
        assert asset.status == FixedAssetStatus.IN_SERVICE
        assert asset.location == "Plant A"
        assert asset.cost_center == "CC100"

    def test_capitalize_from_maintenance_source(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-002",
            name="Injection Mold",
            acquisition_cost=Decimal("25000"),
            useful_life_months=120,
            source_system="maintenance_tpm",
            source_asset_id="asset-uuid-12345",
        )

        assert asset.source_system == "maintenance_tpm"
        assert asset.source_asset_id == "asset-uuid-12345"

    def test_capitalize_duplicate_tag_fails(self, svc: FixedAssetsService):
        svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Asset 1",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )

        with pytest.raises(ValueError, match="asset_tag already exists"):
            svc.capitalize_from_source(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c2",
                asset_tag="FA-001",
                name="Asset 2",
                acquisition_cost=Decimal("2000"),
                useful_life_months=24,
            )

    def test_capitalize_validation(self, svc: FixedAssetsService):
        roles = ["accountant"]

        # Missing tag
        with pytest.raises(ValueError, match="asset_tag required"):
            svc.capitalize_from_source(
                actor_id="acc",
                actor_roles=roles,
                correlation_id="c1",
                asset_tag="",
                name="Test",
                acquisition_cost=Decimal("1000"),
                useful_life_months=12,
            )

        # Missing name
        with pytest.raises(ValueError, match="name required"):
            svc.capitalize_from_source(
                actor_id="acc",
                actor_roles=roles,
                correlation_id="c1",
                asset_tag="FA-001",
                name="",
                acquisition_cost=Decimal("1000"),
                useful_life_months=12,
            )

        # Zero cost
        with pytest.raises(ValueError, match="acquisition_cost must be > 0"):
            svc.capitalize_from_source(
                actor_id="acc",
                actor_roles=roles,
                correlation_id="c1",
                asset_tag="FA-001",
                name="Test",
                acquisition_cost=Decimal("0"),
                useful_life_months=12,
            )

        # Residual > cost
        with pytest.raises(
            ValueError, match="residual_value cannot exceed acquisition_cost"
        ):
            svc.capitalize_from_source(
                actor_id="acc",
                actor_roles=roles,
                correlation_id="c1",
                asset_tag="FA-001",
                name="Test",
                acquisition_cost=Decimal("1000"),
                residual_value=Decimal("2000"),
                useful_life_months=12,
            )

        # Invalid useful life
        with pytest.raises(ValueError, match="useful_life_months must be > 0"):
            svc.capitalize_from_source(
                actor_id="acc",
                actor_roles=roles,
                correlation_id="c1",
                asset_tag="FA-001",
                name="Test",
                acquisition_cost=Decimal("1000"),
                useful_life_months=0,
            )

    def test_capitalize_creates_audit_and_events(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
        )

        audits = svc.list_audit_events(actor_roles=["accountant"])
        assert len(audits) == 1
        assert audits[0].action == "fa.capitalize"
        assert audits[0].entity_id == str(asset.id)
        assert audits[0].correlation_id == "c1"

        events = svc.list_asset_events(actor_roles=["accountant"], asset_id=asset.id)
        assert len(events) == 1
        assert events[0].event_type == AssetEventType.CAPITALIZED
        assert events[0].amount == Decimal("10000")


# ---------------------- Depreciation Tests ----------------------


class TestDepreciation:
    """Test monthly depreciation schedules."""

    def test_compute_monthly_depreciation(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("12000.00"),
            residual_value=Decimal("0"),
            useful_life_months=12,
        )

        monthly = svc.compute_monthly_depreciation(
            actor_roles=["accountant"], asset_id=asset.id
        )
        assert monthly == Decimal("1000.00")

    def test_compute_monthly_depreciation_with_residual(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("50000.00"),
            residual_value=Decimal("5000.00"),
            useful_life_months=60,
        )

        monthly = svc.compute_monthly_depreciation(
            actor_roles=["accountant"], asset_id=asset.id
        )
        # (50000 - 5000) / 60 = 750
        assert monthly == Decimal("750.00")

    def test_post_monthly_depreciation(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("12000.00"),
            residual_value=Decimal("0"),
            useful_life_months=12,
        )

        posting = svc.post_monthly_depreciation(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            period_key="2026-01",
            post_date=date(2026, 1, 31),
        )

        assert posting.asset_id == asset.id
        assert posting.period_key == "2026-01"
        assert posting.amount == Decimal("1000.00")
        assert posting.posted_by == "acc"

        # Check accumulated depreciation updated
        updated = svc.get_asset(actor_roles=["accountant"], asset_id=asset.id)
        assert updated.accumulated_depreciation == Decimal("1000.00")
        assert updated.carrying_amount == Decimal("11000.00")

    def test_post_depreciation_idempotent(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("12000.00"),
            useful_life_months=12,
        )

        posting1 = svc.post_monthly_depreciation(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            period_key="2026-01",
            post_date=date(2026, 1, 31),
        )

        # Same period again returns same posting
        posting2 = svc.post_monthly_depreciation(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c3",
            asset_id=asset.id,
            period_key="2026-01",
            post_date=date(2026, 1, 31),
        )

        assert posting1.id == posting2.id
        # Accumulated should still be 1000
        updated = svc.get_asset(actor_roles=["accountant"], asset_id=asset.id)
        assert updated.accumulated_depreciation == Decimal("1000.00")

    def test_depreciation_caps_at_depreciable_base(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("1200.00"),
            residual_value=Decimal("200.00"),
            useful_life_months=10,  # 100/month for 10 months = 1000 depreciable
        )

        # Post 10 months
        for m in range(1, 11):
            svc.post_monthly_depreciation(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id=f"c-{m}",
                asset_id=asset.id,
                period_key=f"2026-{m:02d}",
                post_date=date(2026, m, 28),
            )

        updated = svc.get_asset(actor_roles=["accountant"], asset_id=asset.id)
        assert updated.accumulated_depreciation == Decimal("1000.00")
        assert updated.carrying_amount == Decimal("200.00")  # residual

        # 11th month should fail - no remaining
        with pytest.raises(ValueError, match="No remaining depreciable amount"):
            svc.post_monthly_depreciation(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c-11",
                asset_id=asset.id,
                period_key="2026-11",
                post_date=date(2026, 11, 30),
            )

    def test_depreciation_invalid_period_key(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )

        with pytest.raises(ValueError, match="period_key must be YYYY-MM"):
            svc.post_monthly_depreciation(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c2",
                asset_id=asset.id,
                period_key="01-2026",  # wrong format
                post_date=date(2026, 1, 31),
            )

    def test_depreciation_on_disposed_asset_fails(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )

        svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            disposal_date=date(2026, 1, 15),
            reason="End of life",
        )

        with pytest.raises(ValueError, match="Asset is disposed"):
            svc.post_monthly_depreciation(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c3",
                asset_id=asset.id,
                period_key="2026-02",
                post_date=date(2026, 2, 28),
            )


# ---------------------- Transfer Tests ----------------------


class TestTransfer:
    """Test asset transfer events."""

    def test_transfer_asset(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
            location="Plant A",
            cost_center="CC100",
        )

        updated = svc.transfer_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            new_location="Plant B",
            new_cost_center="CC200",
            reason="Production relocation",
        )

        assert updated.location == "Plant B"
        assert updated.cost_center == "CC200"

        events = svc.list_asset_events(actor_roles=["accountant"], asset_id=asset.id)
        transfer_events = [e for e in events if e.event_type == AssetEventType.TRANSFER]
        assert len(transfer_events) == 1
        assert transfer_events[0].details["reason"] == "Production relocation"
        assert transfer_events[0].details["old_location"] == "Plant A"
        assert transfer_events[0].details["new_location"] == "Plant B"

    def test_transfer_requires_reason(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )

        with pytest.raises(ValueError, match="reason required"):
            svc.transfer_asset(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c2",
                asset_id=asset.id,
                new_location="Plant B",
                reason="",
            )


# ---------------------- Impairment Tests ----------------------


class TestImpairment:
    """Test asset impairment events."""

    def test_impair_asset(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("10000"),
            residual_value=Decimal("1000"),
            useful_life_months=60,
        )

        updated = svc.impair_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            amount=Decimal("2000"),
            impairment_date=date(2026, 6, 30),
            reason="Market decline",
        )

        assert updated.impairment_loss_total == Decimal("2000.00")
        assert updated.carrying_amount == Decimal("8000.00")

        events = svc.list_asset_events(actor_roles=["accountant"], asset_id=asset.id)
        impair_events = [
            e for e in events if e.event_type == AssetEventType.IMPAIRMENT
        ]
        assert len(impair_events) == 1
        assert impair_events[0].amount == Decimal("2000.00")

    def test_impairment_exceeds_carrying_amount_fails(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
        )

        with pytest.raises(ValueError, match="impairment exceeds carrying amount"):
            svc.impair_asset(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c2",
                asset_id=asset.id,
                amount=Decimal("15000"),
                impairment_date=date(2026, 6, 30),
                reason="Total loss",
            )

    def test_impairment_requires_reason(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
        )

        with pytest.raises(ValueError, match="reason required"):
            svc.impair_asset(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c2",
                asset_id=asset.id,
                amount=Decimal("1000"),
                impairment_date=date(2026, 6, 30),
                reason="",
            )


# ---------------------- Disposal Tests ----------------------


class TestDisposal:
    """Test asset disposal events."""

    def test_dispose_asset_at_loss(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
        )

        # Depreciate some
        svc.post_monthly_depreciation(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            period_key="2026-01",
            post_date=date(2026, 1, 31),
        )

        asset_before = svc.get_asset(actor_roles=["accountant"], asset_id=asset.id)
        carrying_before = asset_before.carrying_amount

        result = svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c3",
            asset_id=asset.id,
            disposal_date=date(2026, 2, 15),
            proceeds=Decimal("5000"),
            reason="Sold to vendor",
        )

        assert result.carrying_amount == carrying_before
        assert result.proceeds == Decimal("5000.00")
        # Loss = proceeds - carrying
        expected_loss = Decimal("5000") - carrying_before
        assert result.gain_loss == expected_loss
        assert result.gain_loss < 0  # It's a loss

        disposed = svc.get_asset(actor_roles=["accountant"], asset_id=asset.id)
        assert disposed.status == FixedAssetStatus.DISPOSED
        assert disposed.disposed_by == "acc"

    def test_dispose_asset_at_gain(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("5000"),
            useful_life_months=60,
        )

        # Depreciate significantly
        for m in range(1, 49):
            try:
                svc.post_monthly_depreciation(
                    actor_id="acc",
                    actor_roles=["accountant"],
                    correlation_id=f"c-{m}",
                    asset_id=asset.id,
                    period_key=f"{2020 + m // 12}-{(m % 12) + 1:02d}",
                    post_date=date(2020 + m // 12, (m % 12) + 1, 28),
                )
            except ValueError:
                break

        asset_before = svc.get_asset(actor_roles=["accountant"], asset_id=asset.id)

        result = svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c-final",
            asset_id=asset.id,
            disposal_date=date(2026, 1, 15),
            proceeds=Decimal("2000"),
            reason="Auction sale",
        )

        assert result.proceeds == Decimal("2000.00")
        assert result.gain_loss > 0  # Gain

    def test_dispose_asset_no_proceeds(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )

        result = svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            disposal_date=date(2026, 1, 15),
            proceeds=Decimal("0"),
            reason="Scrapped",
        )

        assert result.proceeds == Decimal("0")
        assert result.gain_loss == Decimal("-1000.00")  # Total loss

    def test_dispose_already_disposed_fails(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )

        svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            disposal_date=date(2026, 1, 15),
            reason="First disposal",
        )

        with pytest.raises(ValueError, match="Asset already disposed"):
            svc.dispose_asset(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c3",
                asset_id=asset.id,
                disposal_date=date(2026, 1, 16),
                reason="Second disposal",
            )

    def test_dispose_currency_mismatch_fails(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
            currency="EUR",
        )

        with pytest.raises(ValueError, match="Currency mismatch"):
            svc.dispose_asset(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id="c2",
                asset_id=asset.id,
                disposal_date=date(2026, 1, 15),
                proceeds=Decimal("500"),
                currency="USD",
                reason="Sale",
            )


# ---------------------- Query Tests ----------------------


class TestQueries:
    """Test query operations."""

    def test_list_assets_excludes_disposed_by_default(self, svc: FixedAssetsService):
        a1 = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Asset 1",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )
        a2 = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_tag="FA-002",
            name="Asset 2",
            acquisition_cost=Decimal("2000"),
            useful_life_months=24,
        )

        svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c3",
            asset_id=a1.id,
            disposal_date=date(2026, 1, 15),
            reason="Sold",
        )

        assets = svc.list_assets(actor_roles=["accountant"])
        assert len(assets) == 1
        assert assets[0].id == a2.id

    def test_list_assets_include_disposed(self, svc: FixedAssetsService):
        a1 = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Asset 1",
            acquisition_cost=Decimal("1000"),
            useful_life_months=12,
        )
        a2 = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_tag="FA-002",
            name="Asset 2",
            acquisition_cost=Decimal("2000"),
            useful_life_months=24,
        )

        svc.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c3",
            asset_id=a1.id,
            disposal_date=date(2026, 1, 15),
            reason="Sold",
        )

        assets = svc.list_assets(actor_roles=["accountant"], include_disposed=True)
        assert len(assets) == 2

    def test_get_depreciation_postings(self, svc: FixedAssetsService):
        asset = svc.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test",
            acquisition_cost=Decimal("1200"),
            useful_life_months=12,
        )

        for m in range(1, 4):
            svc.post_monthly_depreciation(
                actor_id="acc",
                actor_roles=["accountant"],
                correlation_id=f"c-{m}",
                asset_id=asset.id,
                period_key=f"2026-{m:02d}",
                post_date=date(2026, m, 28),
            )

        postings = svc.get_depreciation_postings(
            actor_roles=["accountant"], asset_id=asset.id
        )
        assert len(postings) == 3
        assert [p.period_key for p in postings] == ["2026-01", "2026-02", "2026-03"]


# ---------------------- GL Integration Tests ----------------------


class TestGLIntegration:
    """Test optional GL posting integration."""

    def test_capitalize_posts_to_gl(self, svc_with_gl, accounting_ledger):
        asset = svc_with_gl.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
            post_to_gl=True,
        )

        # Check GL has the entry (using _entries dict directly since no list_entries method)
        entries = list(accounting_ledger._entries.values())
        assert len(entries) == 1
        assert entries[0].reference == "FA-FA-001"
        assert entries[0].status.value == "posted"

    def test_depreciation_posts_to_gl(self, svc_with_gl, accounting_ledger):
        asset = svc_with_gl.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("12000"),
            useful_life_months=12,
            post_to_gl=True,
        )

        posting = svc_with_gl.post_monthly_depreciation(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            period_key="2026-01",
            post_date=date(2026, 1, 31),
        )

        assert posting.journal_entry_id is not None

        entries = list(accounting_ledger._entries.values())
        dep_entries = [e for e in entries if "DEP-" in e.reference]
        assert len(dep_entries) == 1

    def test_impairment_posts_to_gl(self, svc_with_gl, accounting_ledger):
        asset = svc_with_gl.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
            post_to_gl=True,
        )

        svc_with_gl.impair_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            amount=Decimal("2000"),
            impairment_date=date(2026, 6, 30),
            reason="Market decline",
        )

        entries = list(accounting_ledger._entries.values())
        imp_entries = [e for e in entries if "IMP-" in e.reference]
        assert len(imp_entries) == 1

    def test_disposal_posts_to_gl(self, svc_with_gl, accounting_ledger):
        asset = svc_with_gl.capitalize_from_source(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c1",
            asset_tag="FA-001",
            name="Test Asset",
            acquisition_cost=Decimal("10000"),
            useful_life_months=60,
            post_to_gl=True,
        )

        # Depreciate once
        svc_with_gl.post_monthly_depreciation(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c2",
            asset_id=asset.id,
            period_key="2026-01",
            post_date=date(2026, 1, 31),
        )

        svc_with_gl.dispose_asset(
            actor_id="acc",
            actor_roles=["accountant"],
            correlation_id="c3",
            asset_id=asset.id,
            disposal_date=date(2026, 2, 15),
            proceeds=Decimal("5000"),
            reason="Sold",
        )

        entries = list(accounting_ledger._entries.values())
        dsp_entries = [e for e in entries if "DSP-" in e.reference]
        assert len(dsp_entries) == 1
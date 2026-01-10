"""Tests for Productionization Service (Development Plan 22.10)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.productionization import (
    ProductionizationService,
    EntityType,
    ImportStatus,
    ValidationResult,
    PageRequest,
    FilterSpec,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> ProductionizationService:
    return ProductionizationService()


@pytest.fixture
def admin_roles() -> set[str]:
    return {"admin"}


@pytest.fixture
def finance_roles() -> set[str]:
    return {"finance"}


@pytest.fixture
def ops_roles() -> set[str]:
    return {"ops"}


@pytest.fixture
def auditor_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def viewer_roles() -> set[str]:
    return {"viewer"}


# ============================================================
# GL Account Tests
# ============================================================


class TestGLAccounts:
    def test_create_gl_account(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        account = svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            normal_balance="debit",
        )

        assert account.account_code == "1000"
        assert account.account_name == "Cash"
        assert account.account_type == "asset"

    def test_duplicate_account_code_rejected(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )

        with pytest.raises(ValueError, match="already exists"):
            svc.create_gl_account(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id="cor-2",
                account_code="1000",
                account_name="Another Cash",
                account_type="asset",
            )

    def test_list_gl_accounts_with_pagination(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        # Create multiple accounts
        for i in range(25):
            svc.create_gl_account(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id=f"cor-{i}",
                account_code=f"{1000 + i}",
                account_name=f"Account {i}",
                account_type="asset",
            )

        # Test first page
        page1 = svc.list_gl_accounts(
            actor_roles=finance_roles,
            page=PageRequest(page=1, page_size=10),
        )
        assert len(page1.items) == 10
        assert page1.total_count == 25
        assert page1.total_pages == 3
        assert page1.has_next is True
        assert page1.has_prev is False

        # Test last page
        page3 = svc.list_gl_accounts(
            actor_roles=finance_roles,
            page=PageRequest(page=3, page_size=10),
        )
        assert len(page3.items) == 5
        assert page3.has_next is False
        assert page3.has_prev is True

    def test_list_gl_accounts_with_filter(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            account_code="2000",
            account_name="Accounts Payable",
            account_type="liability",
        )

        result = svc.list_gl_accounts(
            actor_roles=finance_roles,
            filters=[FilterSpec(field="account_type", operator="eq", value="asset")],
        )

        assert result.total_count == 1
        assert result.items[0]["account_type"] == "asset"

    def test_viewer_cannot_create_gl_account(
        self, svc: ProductionizationService, viewer_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Finance write access required"):
            svc.create_gl_account(
                actor_id="viewer1",
                actor_roles=viewer_roles,
                correlation_id="cor-1",
                account_code="1000",
                account_name="Cash",
                account_type="asset",
            )


# ============================================================
# Supplier Tests
# ============================================================


class TestSuppliers:
    def test_create_supplier(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        supplier = svc.create_supplier(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            supplier_code="SUP-001",
            name="Acme Supplies",
            contact_name="John Smith",
            email="john@acme.com",
            payment_terms_days=45,
        )

        assert supplier.supplier_code == "SUP-001"
        assert supplier.name == "Acme Supplies"
        assert supplier.payment_terms_days == 45

    def test_list_suppliers(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        for i in range(5):
            svc.create_supplier(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id=f"cor-{i}",
                supplier_code=f"SUP-{i:03d}",
                name=f"Supplier {i}",
            )

        result = svc.list_suppliers(actor_roles=finance_roles)
        assert result.total_count == 5


# ============================================================
# Customer Tests
# ============================================================


class TestCustomers:
    def test_create_customer(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        customer = svc.create_customer(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            customer_code="CUST-001",
            name="Big Corp",
            credit_limit=Decimal("50000.00"),
            payment_terms_days=60,
        )

        assert customer.customer_code == "CUST-001"
        assert customer.credit_limit == Decimal("50000.00")

    def test_list_customers_with_filter(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        svc.create_customer(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            customer_code="CUST-001",
            name="Active Corp",
        )

        result = svc.list_customers(
            actor_roles=finance_roles,
            filters=[FilterSpec(field="is_active", operator="eq", value=True)],
        )

        assert result.total_count == 1


# ============================================================
# Inventory Tests
# ============================================================


class TestInventory:
    def test_create_inventory_item(
        self, svc: ProductionizationService, ops_roles: set[str]
    ) -> None:
        item = svc.create_inventory_item(
            actor_id="ops1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_code="PART-001",
            description="Steel Rod 10mm",
            category="Raw Material",
            unit_of_measure="KG",
            unit_cost=Decimal("5.50"),
            reorder_point=Decimal("100"),
        )

        assert item.item_code == "PART-001"
        assert item.unit_cost == Decimal("5.50")

    def test_set_inventory_level(
        self, svc: ProductionizationService, ops_roles: set[str]
    ) -> None:
        item = svc.create_inventory_item(
            actor_id="ops1",
            actor_roles=ops_roles,
            correlation_id="cor-1",
            item_code="PART-002",
            description="Steel Bar",
        )

        level = svc.set_inventory_level(
            actor_id="ops1",
            actor_roles=ops_roles,
            correlation_id="cor-2",
            item_id=item.id,
            location_id="WAREHOUSE-A",
            quantity_on_hand=Decimal("500"),
        )

        assert level.quantity_on_hand == Decimal("500")
        assert level.location_id == "WAREHOUSE-A"

    def test_set_level_for_nonexistent_item_fails(
        self, svc: ProductionizationService, ops_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="item_id not found"):
            svc.set_inventory_level(
                actor_id="ops1",
                actor_roles=ops_roles,
                correlation_id="cor-1",
                item_id=uuid4(),
                location_id="WAREHOUSE-A",
                quantity_on_hand=Decimal("100"),
            )


# ============================================================
# Import/Migration Tests
# ============================================================


class TestImportMigration:
    def test_validate_coa_import(
        self, svc: ProductionizationService, admin_roles: set[str]
    ) -> None:
        records = [
            {"account_code": "1000", "account_name": "Cash", "account_type": "asset"},
            {"account_code": "2000", "account_name": "AP", "account_type": "liability"},
            {"account_code": "", "account_name": "Bad", "account_type": "asset"},  # Error
        ]

        validations, valid, errors = svc.validate_import_data(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type=EntityType.CHART_OF_ACCOUNTS,
            records=records,
        )

        assert valid == 2
        assert errors == 1
        assert validations[2].result == ValidationResult.ERROR

    def test_execute_coa_import(
        self, svc: ProductionizationService, admin_roles: set[str]
    ) -> None:
        records = [
            {"account_code": "1000", "account_name": "Cash", "account_type": "asset"},
            {"account_code": "1100", "account_name": "AR", "account_type": "asset"},
            {"account_code": "2000", "account_name": "AP", "account_type": "liability"},
        ]

        batch = svc.execute_import(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type=EntityType.CHART_OF_ACCOUNTS,
            source_file="coa_import.csv",
            records=records,
        )

        assert batch.status == ImportStatus.COMPLETED
        assert batch.valid_records == 3
        assert batch.error_records == 0

        # Verify accounts were created
        accounts = svc.list_gl_accounts(actor_roles=admin_roles)
        assert accounts.total_count == 3

    def test_execute_supplier_import(
        self, svc: ProductionizationService, admin_roles: set[str]
    ) -> None:
        records = [
            {"supplier_code": "SUP-001", "name": "Supplier A", "email": "a@sup.com"},
            {"supplier_code": "SUP-002", "name": "Supplier B"},
        ]

        batch = svc.execute_import(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type=EntityType.SUPPLIER,
            source_file="suppliers.csv",
            records=records,
        )

        assert batch.status == ImportStatus.COMPLETED
        assert batch.valid_records == 2

    def test_import_with_errors_fails_batch(
        self, svc: ProductionizationService, admin_roles: set[str]
    ) -> None:
        records = [
            {"supplier_code": "", "name": ""},  # Both required fields missing
            {"supplier_code": "SUP-001", "name": "Valid Supplier"},
        ]

        batch = svc.execute_import(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type=EntityType.SUPPLIER,
            source_file="bad_suppliers.csv",
            records=records,
        )

        assert batch.status == ImportStatus.FAILED
        assert batch.error_records == 1
        assert len(batch.error_log) == 1

    def test_non_admin_cannot_import(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Admin role required"):
            svc.execute_import(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id="cor-1",
                entity_type=EntityType.CHART_OF_ACCOUNTS,
                source_file="test.csv",
                records=[],
            )

    def test_list_import_batches(
        self, svc: ProductionizationService, admin_roles: set[str]
    ) -> None:
        svc.execute_import(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type=EntityType.CHART_OF_ACCOUNTS,
            source_file="coa.csv",
            records=[{"account_code": "1000", "account_name": "Cash", "account_type": "asset"}],
        )
        svc.execute_import(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            entity_type=EntityType.SUPPLIER,
            source_file="suppliers.csv",
            records=[{"supplier_code": "SUP-001", "name": "Test"}],
        )

        batches = svc.list_import_batches(actor_roles=admin_roles)
        assert len(batches) >= 2

        coa_batches = svc.list_import_batches(
            actor_roles=admin_roles, entity_type=EntityType.CHART_OF_ACCOUNTS
        )
        assert len(coa_batches) == 1


# ============================================================
# Opening Balance Tests
# ============================================================


class TestOpeningBalances:
    def test_set_opening_balance(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        account = svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )

        balance = svc.set_opening_balance(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            account_id=account.id,
            period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            debit_amount=Decimal("10000.00"),
            credit_amount=Decimal("0"),
        )

        assert balance.net_amount == Decimal("10000.00")

    def test_opening_balance_for_nonexistent_account_fails(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(ValueError, match="account_id not found"):
            svc.set_opening_balance(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id="cor-1",
                account_id=uuid4(),
                period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
                debit_amount=Decimal("1000"),
            )

    def test_list_opening_balances(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        acct1 = svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        acct2 = svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            account_code="1100",
            account_name="AR",
            account_type="asset",
        )

        svc.set_opening_balance(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            account_id=acct1.id,
            period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            debit_amount=Decimal("5000"),
        )
        svc.set_opening_balance(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-4",
            account_id=acct2.id,
            period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            debit_amount=Decimal("3000"),
        )

        all_balances = svc.list_opening_balances(actor_roles=finance_roles)
        assert len(all_balances) == 2

        acct1_balances = svc.list_opening_balances(
            actor_roles=finance_roles, account_id=acct1.id
        )
        assert len(acct1_balances) == 1


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_viewer_cannot_read_finance_data(
        self, svc: ProductionizationService, finance_roles: set[str], viewer_roles: set[str]
    ) -> None:
        # Create some data first
        svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )

        with pytest.raises(PermissionError, match="Finance read access required"):
            svc.list_gl_accounts(actor_roles=viewer_roles)

    def test_auditor_can_read_finance_data(
        self, svc: ProductionizationService, finance_roles: set[str], auditor_roles: set[str]
    ) -> None:
        svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )

        result = svc.list_gl_accounts(actor_roles=auditor_roles)
        assert result.total_count == 1

    def test_auditor_cannot_write_finance_data(
        self, svc: ProductionizationService, auditor_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Finance write access required"):
            svc.create_gl_account(
                actor_id="auditor1",
                actor_roles=auditor_roles,
                correlation_id="cor-1",
                account_code="1000",
                account_name="Cash",
                account_type="asset",
            )


# ============================================================
# Audit Trail Tests
# ============================================================


class TestAuditTrail:
    def test_audit_trail_for_crud_operations(
        self, svc: ProductionizationService, finance_roles: set[str], admin_roles: set[str]
    ) -> None:
        svc.create_gl_account(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        svc.create_supplier(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            supplier_code="SUP-001",
            name="Test Supplier",
        )

        events = svc.list_audit_events(actor_roles=admin_roles)
        actions = [e.action for e in events]

        assert "gl_account.create" in actions
        assert "supplier.create" in actions

    def test_audit_includes_correlation_id(
        self, svc: ProductionizationService, finance_roles: set[str], admin_roles: set[str]
    ) -> None:
        svc.create_customer(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="trace-cust-999",
            customer_code="CUST-001",
            name="Test Customer",
        )

        events = svc.list_audit_events(actor_roles=admin_roles)
        assert any(e.correlation_id == "trace-cust-999" for e in events)

    def test_non_auditor_cannot_view_audit(
        self, svc: ProductionizationService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Audit access required"):
            svc.list_audit_events(actor_roles=finance_roles)

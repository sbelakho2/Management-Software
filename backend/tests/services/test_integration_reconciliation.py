"""Tests for Integration & Reconciliation Service (Development Plan 22.9)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.integration_reconciliation import (
    IntegrationReconciliationService,
    SyncDirection,
    SyncStatus,
    ConflictResolution,
    ExceptionType,
    ReconciliationStatus,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> IntegrationReconciliationService:
    return IntegrationReconciliationService()


@pytest.fixture
def admin_roles() -> set[str]:
    return {"admin"}


@pytest.fixture
def finance_roles() -> set[str]:
    return {"finance"}


@pytest.fixture
def it_roles() -> set[str]:
    return {"it"}


@pytest.fixture
def auditor_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def viewer_roles() -> set[str]:
    return {"viewer"}


# ============================================================
# ERP Sync Contract Tests
# ============================================================


class TestSyncContracts:
    def test_create_sync_contract(
        self, svc: IntegrationReconciliationService, admin_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Invoice Sync",
            external_system="SAGE",
            direction=SyncDirection.OUTBOUND,
            entity_type="invoice",
            conflict_resolution=ConflictResolution.SOURCE_WINS,
            max_retries=5,
        )

        assert contract.name == "Invoice Sync"
        assert contract.external_system == "SAGE"
        assert contract.max_retries == 5

    def test_non_admin_cannot_create_contract(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Admin role required"):
            svc.create_sync_contract(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id="cor-1",
                name="Test Contract",
                external_system="TEST",
                direction=SyncDirection.INBOUND,
                entity_type="customer",
            )

    def test_list_contracts(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Contract A",
            external_system="ERP1",
            direction=SyncDirection.INBOUND,
            entity_type="customer",
        )

        contracts = svc.list_sync_contracts(actor_roles=finance_roles)
        assert len(contracts) == 1


# ============================================================
# Sync Operation Tests
# ============================================================


class TestSyncOperations:
    def test_submit_sync_operation(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Invoice Sync",
            external_system="SAGE",
            direction=SyncDirection.OUTBOUND,
            entity_type="invoice",
        )

        op = svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="INV-001",
            entity_id="invoice-123",
            payload={"invoice_number": "INV-001", "amount": 1000},
        )

        assert op.idempotency_key == "INV-001"
        assert op.status == SyncStatus.PENDING

    def test_idempotency_prevents_duplicate(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Invoice Sync",
            external_system="SAGE",
            direction=SyncDirection.OUTBOUND,
            entity_type="invoice",
        )

        op1 = svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="INV-002",
            entity_id="invoice-456",
            payload={"test": 1},
        )

        # Submit again with same idempotency key
        op2 = svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            contract_id=contract.id,
            idempotency_key="INV-002",
            entity_id="invoice-456",
            payload={"test": 2},
        )

        assert op2.id == op1.id
        assert op2.status == SyncStatus.SKIPPED_DUPLICATE

    def test_mark_sync_success(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Invoice Sync",
            external_system="SAGE",
            direction=SyncDirection.OUTBOUND,
            entity_type="invoice",
        )

        op = svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="INV-003",
            entity_id="invoice-789",
            payload={},
        )

        completed = svc.mark_sync_success(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            operation_id=op.id,
            external_id="SAGE-12345",
        )

        assert completed.status == SyncStatus.SUCCESS
        assert completed.external_id == "SAGE-12345"
        assert completed.completed_at is not None

    def test_mark_sync_failed_with_retry(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], it_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Customer Sync",
            external_system="ERP",
            direction=SyncDirection.INBOUND,
            entity_type="customer",
            max_retries=3,
            retry_delay_seconds=60,
        )

        op = svc.submit_sync_operation(
            actor_id="it1",
            actor_roles=it_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="CUST-001",
            entity_id="customer-1",
            payload={},
        )

        failed = svc.mark_sync_failed(
            actor_id="it1",
            actor_roles=it_roles,
            correlation_id="cor-3",
            operation_id=op.id,
            error_message="Connection timeout",
        )

        assert failed.status == SyncStatus.RETRY_SCHEDULED
        assert failed.retry_count == 1
        assert failed.scheduled_retry_at is not None

    def test_max_retries_exceeded(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], it_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Customer Sync",
            external_system="ERP",
            direction=SyncDirection.INBOUND,
            entity_type="customer",
            max_retries=2,
        )

        op = svc.submit_sync_operation(
            actor_id="it1",
            actor_roles=it_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="CUST-002",
            entity_id="customer-2",
            payload={},
        )

        # Fail multiple times
        for i in range(3):
            op = svc.mark_sync_failed(
                actor_id="it1",
                actor_roles=it_roles,
                correlation_id=f"cor-{i+3}",
                operation_id=op.id,
                error_message=f"Error {i+1}",
            )

        assert op.status == SyncStatus.FAILED
        assert op.retry_count == 3


# ============================================================
# Conflict Resolution Tests
# ============================================================


class TestConflictResolution:
    def test_record_conflict(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Invoice Sync",
            external_system="SAGE",
            direction=SyncDirection.INBOUND,
            entity_type="invoice",
            conflict_resolution=ConflictResolution.MANUAL,
        )

        op = svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="INV-CONFLICT",
            entity_id="invoice-conflict",
            payload={"amount": 1000},
        )

        conflict = svc.record_conflict(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            operation_id=op.id,
            source_data={"amount": 1000},
            target_data={"amount": 1200},
        )

        assert conflict.source_data["amount"] == 1000
        assert conflict.target_data["amount"] == 1200
        assert not conflict.resolved

    def test_resolve_conflict(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Invoice Sync",
            external_system="SAGE",
            direction=SyncDirection.INBOUND,
            entity_type="invoice",
        )

        op = svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="INV-RESOLVE",
            entity_id="invoice-resolve",
            payload={},
        )

        conflict = svc.record_conflict(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            operation_id=op.id,
            source_data={"x": 1},
            target_data={"x": 2},
        )

        resolved = svc.resolve_conflict(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-4",
            conflict_id=conflict.id,
            resolution_notes="Used source value after verification",
        )

        assert resolved.resolved is True
        assert resolved.resolved_by == "finance1"


# ============================================================
# Bank Import/Export Tests
# ============================================================


class TestBankImportExport:
    def test_import_bank_csv(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        csv_content = """date,description,amount,reference
2025-01-01,Deposit,1000.00,DEP001
2025-01-02,Payment,-500.00,PAY001
2025-01-03,Interest,25.50,INT001"""

        batch, transactions = svc.import_bank_csv(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            bank_name="First National Bank",
            file_name="january_statement.csv",
            csv_content=csv_content,
        )

        assert batch.transaction_count == 3
        assert batch.total_credits == Decimal("1025.50")
        assert batch.total_debits == Decimal("500.00")
        assert len(transactions) == 3

    def test_export_payment_csv(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        payments = [
            {"date": "2025-01-15", "payee": "Vendor A", "amount": "1000.00", "reference": "CHK001", "memo": "Invoice 123"},
            {"date": "2025-01-16", "payee": "Vendor B", "amount": "2500.00", "reference": "CHK002", "memo": "Invoice 456"},
        ]

        csv_output = svc.export_payment_csv(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            payments=payments,
        )

        assert "Vendor A" in csv_output
        assert "CHK001" in csv_output
        assert "2500.00" in csv_output

    def test_list_bank_transactions(
        self, svc: IntegrationReconciliationService, finance_roles: set[str], auditor_roles: set[str]
    ) -> None:
        csv_content = """date,description,amount,reference
2025-01-01,Deposit,500.00,DEP002"""

        batch, _ = svc.import_bank_csv(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-002",
            bank_name="Test Bank",
            file_name="test.csv",
            csv_content=csv_content,
        )

        transactions = svc.list_bank_transactions(
            actor_roles=auditor_roles, batch_id=batch.id
        )
        assert len(transactions) == 1


# ============================================================
# Reconciliation Tests
# ============================================================


class TestReconciliation:
    def test_create_reconciliation_session(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("12500.00"),
        )

        assert session.account_id == "CHECKING-001"
        assert session.status == "in_progress"

    def test_add_reconciliation_item(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("12500.00"),
        )

        item = svc.add_reconciliation_item(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            session_id=session.id,
            bank_amount=Decimal("1000.00"),
            book_amount=Decimal("1000.00"),
            bank_date=now - timedelta(days=5),
            book_date=now - timedelta(days=5),
        )

        assert item.status == ReconciliationStatus.UNMATCHED
        assert item.bank_amount == Decimal("1000.00")

    def test_match_items(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("10500.00"),
        )

        item = svc.add_reconciliation_item(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            session_id=session.id,
            bank_amount=Decimal("500.00"),
            book_amount=Decimal("500.00"),
        )

        matched = svc.match_items(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            item_id=item.id,
        )

        assert matched.status == ReconciliationStatus.MATCHED
        assert matched.matched_by == "finance1"

    def test_create_exception(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("10500.00"),
        )

        item = svc.add_reconciliation_item(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            session_id=session.id,
            bank_amount=Decimal("1000.00"),
            book_amount=Decimal("950.00"),
        )

        exc = svc.create_exception(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            item_id=item.id,
            exception_type=ExceptionType.AMOUNT_MISMATCH,
            description="$50 variance - possible bank fee not recorded",
        )

        assert exc.exception_type == ExceptionType.AMOUNT_MISMATCH
        assert exc.difference == Decimal("50.00")
        assert not exc.resolved

    def test_resolve_exception(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("10500.00"),
        )

        item = svc.add_reconciliation_item(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            session_id=session.id,
            bank_amount=Decimal("100.00"),
            book_amount=Decimal("0"),
        )

        exc = svc.create_exception(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            item_id=item.id,
            exception_type=ExceptionType.MISSING_IN_BOOKS,
            description="Transaction not in books",
        )

        resolved = svc.resolve_exception(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-4",
            exception_id=exc.id,
            resolution_notes="Created journal entry JE-123 for bank fee",
        )

        assert resolved.resolved is True
        assert "JE-123" in resolved.resolution_notes

    def test_get_exception_queue(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("10500.00"),
        )

        # Create multiple items with exceptions
        for i in range(3):
            item = svc.add_reconciliation_item(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id=f"cor-{i+2}",
                session_id=session.id,
                bank_amount=Decimal("100.00"),
                book_amount=Decimal("90.00"),
            )
            svc.create_exception(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id=f"cor-exc-{i}",
                item_id=item.id,
                exception_type=ExceptionType.AMOUNT_MISMATCH,
                description=f"Exception {i+1}",
            )

        queue = svc.get_exception_queue(actor_roles=finance_roles)
        assert len(queue) == 3

    def test_get_reconciliation_summary(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        session = svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-1",
            account_id="CHECKING-001",
            period_start=now - timedelta(days=30),
            period_end=now,
            opening_balance=Decimal("10000.00"),
            closing_balance=Decimal("10500.00"),
        )

        # Add items
        item1 = svc.add_reconciliation_item(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            session_id=session.id,
            bank_amount=Decimal("500.00"),
            book_amount=Decimal("500.00"),
        )
        svc.match_items(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-3",
            item_id=item1.id,
        )

        item2 = svc.add_reconciliation_item(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-4",
            session_id=session.id,
            bank_amount=Decimal("100.00"),
            book_amount=Decimal("90.00"),
        )
        svc.create_exception(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-5",
            item_id=item2.id,
            exception_type=ExceptionType.AMOUNT_MISMATCH,
            description="Variance",
        )

        summary = svc.get_reconciliation_summary(
            actor_roles=finance_roles, session_id=session.id
        )

        assert summary["items"]["total"] == 2
        assert summary["items"]["matched"] == 1
        assert summary["items"]["with_exceptions"] == 1
        assert summary["exceptions"]["total"] == 1
        assert summary["exceptions"]["unresolved"] == 1


# ============================================================
# RBAC Tests
# ============================================================


class TestRBAC:
    def test_viewer_cannot_import_bank_data(
        self, svc: IntegrationReconciliationService, viewer_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Reconciliation access required"):
            svc.import_bank_csv(
                actor_id="viewer1",
                actor_roles=viewer_roles,
                correlation_id="cor-1",
                account_id="TEST",
                bank_name="Test",
                file_name="test.csv",
                csv_content="date,amount\n2025-01-01,100",
            )

    def test_viewer_cannot_submit_sync_operation(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], viewer_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Test",
            external_system="TEST",
            direction=SyncDirection.OUTBOUND,
            entity_type="test",
        )

        with pytest.raises(PermissionError, match="Integration write access required"):
            svc.submit_sync_operation(
                actor_id="viewer1",
                actor_roles=viewer_roles,
                correlation_id="cor-2",
                contract_id=contract.id,
                idempotency_key="TEST-001",
                entity_id="test-1",
                payload={},
            )


# ============================================================
# Audit Trail Tests
# ============================================================


class TestAuditTrail:
    def test_audit_trail_for_sync_operations(
        self, svc: IntegrationReconciliationService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        contract = svc.create_sync_contract(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Test Sync",
            external_system="TEST",
            direction=SyncDirection.OUTBOUND,
            entity_type="invoice",
        )

        svc.submit_sync_operation(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="cor-2",
            contract_id=contract.id,
            idempotency_key="AUDIT-001",
            entity_id="invoice-audit",
            payload={},
        )

        events = svc.list_audit_events(actor_roles=admin_roles)
        actions = [e.action for e in events]

        assert "sync.contract.create" in actions
        assert "sync.operation.submit" in actions

    def test_audit_includes_correlation_id(
        self, svc: IntegrationReconciliationService, finance_roles: set[str]
    ) -> None:
        now = datetime.now(timezone.utc)
        svc.create_reconciliation_session(
            actor_id="finance1",
            actor_roles=finance_roles,
            correlation_id="trace-recon-999",
            account_id="TEST",
            period_start=now - timedelta(days=1),
            period_end=now,
            opening_balance=Decimal("0"),
            closing_balance=Decimal("0"),
        )

        events = svc.list_audit_events(actor_roles=finance_roles)
        assert any(e.correlation_id == "trace-recon-999" for e in events)

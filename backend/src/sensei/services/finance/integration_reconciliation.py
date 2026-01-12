"""Integration & Reconciliation Hardening Service (Development Plan 22.9).

Provides:
- ERP Sync Contracts with idempotency keys and retry semantics
- Bank file import/export (CSV/OFX-like)
- Reconciliation dashboards with exceptions queue
- AR/AP/GL mismatch detection and workflows
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4
import csv
import io


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _norm_roles(roles: Iterable[str]) -> frozenset[str]:
    return frozenset(r.lower().strip() for r in roles if r)


def _require_any(
    roles: frozenset[str], allowed: frozenset[str], msg: str
) -> None:
    if not roles & allowed:
        raise PermissionError(msg)


# ============================================================
# Role Sets
# ============================================================

_ADMIN_ROLES = frozenset({"admin", "ceo"})
_INTEGRATION_WRITE_ROLES = frozenset({"admin", "it", "finance"})
_RECONCILIATION_ROLES = frozenset({"admin", "finance", "accountant", "ceo", "gm"})
_READER_ROLES = frozenset({
    "admin", "ceo", "gm", "finance", "accountant", "auditor", "it"
})


# ============================================================
# Enums
# ============================================================


class SyncStatus(str, Enum):
    """Status of a sync operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CONFLICT = "conflict"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class SyncDirection(str, Enum):
    """Direction of sync operation."""

    INBOUND = "inbound"  # From external system to us
    OUTBOUND = "outbound"  # From us to external system


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""

    SOURCE_WINS = "source_wins"  # External system data wins
    TARGET_WINS = "target_wins"  # Our data wins
    MANUAL = "manual"  # Requires manual resolution
    MERGE = "merge"  # Attempt to merge changes


class BankTransactionType(str, Enum):
    """Type of bank transaction."""

    CREDIT = "credit"
    DEBIT = "debit"
    FEE = "fee"
    INTEREST = "interest"
    TRANSFER = "transfer"


class ReconciliationStatus(str, Enum):
    """Status of a reconciliation item."""

    UNMATCHED = "unmatched"
    MATCHED = "matched"
    EXCEPTION = "exception"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class ExceptionType(str, Enum):
    """Type of reconciliation exception."""

    AMOUNT_MISMATCH = "amount_mismatch"
    MISSING_IN_BANK = "missing_in_bank"
    MISSING_IN_BOOKS = "missing_in_books"
    DUPLICATE = "duplicate"
    DATE_MISMATCH = "date_mismatch"
    REFERENCE_MISMATCH = "reference_mismatch"


# ============================================================
# Data Classes - ERP Sync
# ============================================================


@dataclass(frozen=True)
class SyncContract:
    """Definition of a sync contract with external system."""

    id: UUID
    name: str
    external_system: str  # e.g., "SAGE", "QUICKBOOKS", "BANK_XYZ"
    direction: SyncDirection
    entity_type: str  # e.g., "invoice", "payment", "customer"
    conflict_resolution: ConflictResolution
    max_retries: int = 3
    retry_delay_seconds: int = 60
    idempotency_key_field: str = "external_id"
    enabled: bool = True
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class SyncOperation:
    """A single sync operation record."""

    id: UUID
    contract_id: UUID
    idempotency_key: str
    direction: SyncDirection
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    status: SyncStatus
    retry_count: int = 0
    error_message: str | None = None
    external_id: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None
    scheduled_retry_at: datetime | None = None


@dataclass(frozen=True)
class ConflictRecord:
    """Record of a sync conflict for manual resolution."""

    id: UUID
    sync_operation_id: UUID
    source_data: dict[str, Any]
    target_data: dict[str, Any]
    resolution_strategy: ConflictResolution
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    created_at: datetime = field(default_factory=_utcnow)


# ============================================================
# Data Classes - Bank Import/Export
# ============================================================


@dataclass(frozen=True)
class BankTransaction:
    """Imported bank transaction."""

    id: UUID
    import_batch_id: UUID
    transaction_date: datetime
    post_date: datetime | None
    description: str
    reference: str
    transaction_type: BankTransactionType
    amount: Decimal
    balance: Decimal | None = None
    check_number: str | None = None
    external_id: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class BankImportBatch:
    """A batch of imported bank transactions."""

    id: UUID
    account_id: str
    bank_name: str
    file_name: str
    file_format: str  # "csv", "ofx", "qfx"
    start_date: datetime
    end_date: datetime
    transaction_count: int
    total_credits: Decimal
    total_debits: Decimal
    imported_by: str
    created_at: datetime = field(default_factory=_utcnow)


# ============================================================
# Data Classes - Reconciliation
# ============================================================


@dataclass(frozen=True)
class ReconciliationItem:
    """An item in the reconciliation process."""

    id: UUID
    session_id: UUID
    bank_transaction_id: UUID | None
    book_entry_id: UUID | None
    book_entry_type: str | None  # "ar_receipt", "ap_payment", "gl_entry"
    bank_amount: Decimal | None
    book_amount: Decimal | None
    bank_date: datetime | None
    book_date: datetime | None
    status: ReconciliationStatus
    matched_at: datetime | None = None
    matched_by: str | None = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class ReconciliationException:
    """An exception requiring attention."""

    id: UUID
    session_id: UUID
    reconciliation_item_id: UUID
    exception_type: ExceptionType
    description: str
    bank_amount: Decimal | None
    book_amount: Decimal | None
    difference: Decimal | None
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class ReconciliationSession:
    """A reconciliation session/batch."""

    id: UUID
    account_id: str
    period_start: datetime
    period_end: datetime
    opening_balance: Decimal
    closing_balance: Decimal
    total_items: int
    matched_count: int
    exception_count: int
    status: str  # "in_progress", "completed", "reviewed"
    created_by: str
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event."""

    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Service
# ============================================================


class IntegrationReconciliationService:
    """Integration layer with ERP sync and bank reconciliation."""

    def __init__(self) -> None:
        # Sync contracts
        self._contracts: dict[UUID, SyncContract] = {}
        self._sync_operations: dict[UUID, SyncOperation] = {}
        self._conflicts: dict[UUID, ConflictRecord] = {}
        self._idempotency_registry: dict[str, UUID] = {}  # key -> operation_id

        # Bank imports
        self._import_batches: dict[UUID, BankImportBatch] = {}
        self._bank_transactions: dict[UUID, BankTransaction] = {}

        # Reconciliation
        self._recon_sessions: dict[UUID, ReconciliationSession] = {}
        self._recon_items: dict[UUID, ReconciliationItem] = {}
        self._exceptions: dict[UUID, ReconciliationException] = {}

        self._audit: list[AuditEvent] = []

    # ----------------------------------------------------------------
    # Internal Helpers
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
    # ERP Sync Contracts
    # ----------------------------------------------------------------

    def create_sync_contract(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        name: str,
        external_system: str,
        direction: SyncDirection,
        entity_type: str,
        conflict_resolution: ConflictResolution = ConflictResolution.MANUAL,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
        idempotency_key_field: str = "external_id",
    ) -> SyncContract:
        """Create a sync contract with an external system."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required")

        contract = SyncContract(
            id=uuid4(),
            name=name,
            external_system=external_system,
            direction=direction,
            entity_type=entity_type,
            conflict_resolution=conflict_resolution,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            idempotency_key_field=idempotency_key_field,
        )
        self._contracts[contract.id] = contract

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="sync.contract.create",
            entity_type="sync_contract",
            entity_id=str(contract.id),
            correlation_id=correlation_id,
            metadata={"name": name, "system": external_system},
        )

        return contract

    def list_sync_contracts(
        self, *, actor_roles: Iterable[str]
    ) -> list[SyncContract]:
        """List all sync contracts."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _READER_ROLES, "Read access required")
        return list(self._contracts.values())

    def submit_sync_operation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        contract_id: UUID,
        idempotency_key: str,
        entity_id: str,
        payload: dict[str, Any],
    ) -> SyncOperation:
        """Submit a sync operation with idempotency protection."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _INTEGRATION_WRITE_ROLES, "Integration write access required")

        contract = self._contracts.get(contract_id)
        if not contract:
            raise ValueError("contract_id not found")

        # Check idempotency
        composite_key = f"{contract_id}:{idempotency_key}"
        if composite_key in self._idempotency_registry:
            existing_op_id = self._idempotency_registry[composite_key]
            existing_op = self._sync_operations[existing_op_id]

            # Return existing operation - idempotent behavior
            new_op = SyncOperation(
                id=existing_op.id,
                contract_id=existing_op.contract_id,
                idempotency_key=existing_op.idempotency_key,
                direction=existing_op.direction,
                entity_type=existing_op.entity_type,
                entity_id=existing_op.entity_id,
                payload=existing_op.payload,
                status=SyncStatus.SKIPPED_DUPLICATE,
                retry_count=existing_op.retry_count,
                error_message=existing_op.error_message,
                external_id=existing_op.external_id,
                created_at=existing_op.created_at,
                completed_at=existing_op.completed_at,
            )

            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="sync.operation.duplicate",
                entity_type="sync_operation",
                entity_id=str(existing_op.id),
                correlation_id=correlation_id,
            )

            return new_op

        # Create new operation
        operation = SyncOperation(
            id=uuid4(),
            contract_id=contract_id,
            idempotency_key=idempotency_key,
            direction=contract.direction,
            entity_type=contract.entity_type,
            entity_id=entity_id,
            payload=payload,
            status=SyncStatus.PENDING,
        )
        self._sync_operations[operation.id] = operation
        self._idempotency_registry[composite_key] = operation.id

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="sync.operation.submit",
            entity_type="sync_operation",
            entity_id=str(operation.id),
            correlation_id=correlation_id,
        )

        return operation

    def mark_sync_success(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        operation_id: UUID,
        external_id: str | None = None,
    ) -> SyncOperation:
        """Mark a sync operation as successful."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _INTEGRATION_WRITE_ROLES, "Integration write access required")

        op = self._sync_operations.get(operation_id)
        if not op:
            raise ValueError("operation_id not found")

        updated = SyncOperation(
            id=op.id,
            contract_id=op.contract_id,
            idempotency_key=op.idempotency_key,
            direction=op.direction,
            entity_type=op.entity_type,
            entity_id=op.entity_id,
            payload=op.payload,
            status=SyncStatus.SUCCESS,
            retry_count=op.retry_count,
            error_message=None,
            external_id=external_id,
            created_at=op.created_at,
            completed_at=_utcnow(),
        )
        self._sync_operations[op.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="sync.operation.success",
            entity_type="sync_operation",
            entity_id=str(op.id),
            correlation_id=correlation_id,
        )

        return updated

    def mark_sync_failed(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        operation_id: UUID,
        error_message: str,
    ) -> SyncOperation:
        """Mark a sync operation as failed with retry scheduling."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _INTEGRATION_WRITE_ROLES, "Integration write access required")

        op = self._sync_operations.get(operation_id)
        if not op:
            raise ValueError("operation_id not found")

        contract = self._contracts[op.contract_id]
        new_retry_count = op.retry_count + 1

        if new_retry_count <= contract.max_retries:
            # Schedule retry
            scheduled = _utcnow() + timedelta(
                seconds=contract.retry_delay_seconds * (2 ** (new_retry_count - 1))
            )
            new_status = SyncStatus.RETRY_SCHEDULED
        else:
            # Max retries exceeded
            scheduled = None
            new_status = SyncStatus.FAILED

        updated = SyncOperation(
            id=op.id,
            contract_id=op.contract_id,
            idempotency_key=op.idempotency_key,
            direction=op.direction,
            entity_type=op.entity_type,
            entity_id=op.entity_id,
            payload=op.payload,
            status=new_status,
            retry_count=new_retry_count,
            error_message=error_message,
            external_id=op.external_id,
            created_at=op.created_at,
            completed_at=_utcnow() if new_status == SyncStatus.FAILED else None,
            scheduled_retry_at=scheduled,
        )
        self._sync_operations[op.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="sync.operation.failed",
            entity_type="sync_operation",
            entity_id=str(op.id),
            correlation_id=correlation_id,
            metadata={"retry": new_retry_count, "max": contract.max_retries},
        )

        return updated

    def record_conflict(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        operation_id: UUID,
        source_data: dict[str, Any],
        target_data: dict[str, Any],
    ) -> ConflictRecord:
        """Record a sync conflict for manual resolution."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _INTEGRATION_WRITE_ROLES, "Integration write access required")

        op = self._sync_operations.get(operation_id)
        if not op:
            raise ValueError("operation_id not found")

        contract = self._contracts[op.contract_id]

        conflict = ConflictRecord(
            id=uuid4(),
            sync_operation_id=operation_id,
            source_data=source_data,
            target_data=target_data,
            resolution_strategy=contract.conflict_resolution,
        )
        self._conflicts[conflict.id] = conflict

        # Update operation status
        updated_op = SyncOperation(
            id=op.id,
            contract_id=op.contract_id,
            idempotency_key=op.idempotency_key,
            direction=op.direction,
            entity_type=op.entity_type,
            entity_id=op.entity_id,
            payload=op.payload,
            status=SyncStatus.CONFLICT,
            retry_count=op.retry_count,
            error_message="Conflict detected - manual resolution required",
            external_id=op.external_id,
            created_at=op.created_at,
        )
        self._sync_operations[op.id] = updated_op

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="sync.conflict.record",
            entity_type="conflict_record",
            entity_id=str(conflict.id),
            correlation_id=correlation_id,
        )

        return conflict

    def resolve_conflict(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        conflict_id: UUID,
        resolution_notes: str,
    ) -> ConflictRecord:
        """Resolve a sync conflict."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            raise ValueError("conflict_id not found")

        updated = ConflictRecord(
            id=conflict.id,
            sync_operation_id=conflict.sync_operation_id,
            source_data=conflict.source_data,
            target_data=conflict.target_data,
            resolution_strategy=conflict.resolution_strategy,
            resolved=True,
            resolved_by=actor_id,
            resolved_at=_utcnow(),
            resolution_notes=resolution_notes,
            created_at=conflict.created_at,
        )
        self._conflicts[conflict.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="sync.conflict.resolve",
            entity_type="conflict_record",
            entity_id=str(conflict.id),
            correlation_id=correlation_id,
        )

        return updated

    def get_pending_retries(
        self, *, actor_roles: Iterable[str]
    ) -> list[SyncOperation]:
        """Get operations due for retry."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _READER_ROLES, "Read access required")

        now = _utcnow()
        return [
            op for op in self._sync_operations.values()
            if op.status == SyncStatus.RETRY_SCHEDULED
            and op.scheduled_retry_at is not None
            and op.scheduled_retry_at <= now
        ]

    # ----------------------------------------------------------------
    # Bank File Import/Export
    # ----------------------------------------------------------------

    def import_bank_csv(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: str,
        bank_name: str,
        file_name: str,
        csv_content: str,
        date_format: str = "%Y-%m-%d",
    ) -> tuple[BankImportBatch, list[BankTransaction]]:
        """Import bank transactions from CSV content."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        transactions: list[BankTransaction] = []
        total_credits = Decimal("0")
        total_debits = Decimal("0")
        min_date: datetime | None = None
        max_date: datetime | None = None

        batch_id = uuid4()

        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            # Parse date
            date_str = row.get("date") or row.get("Date") or row.get("DATE", "")
            try:
                txn_date = datetime.strptime(date_str.strip(), date_format).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                txn_date = _utcnow()

            # Parse amount
            amount_str = row.get("amount") or row.get("Amount") or row.get("AMOUNT", "0")
            amount = Decimal(amount_str.replace(",", "").replace("$", ""))

            # Determine type
            if amount >= 0:
                txn_type = BankTransactionType.CREDIT
                total_credits += amount
            else:
                txn_type = BankTransactionType.DEBIT
                total_debits += abs(amount)
                amount = abs(amount)

            # Track date range
            if min_date is None or txn_date < min_date:
                min_date = txn_date
            if max_date is None or txn_date > max_date:
                max_date = txn_date

            txn = BankTransaction(
                id=uuid4(),
                import_batch_id=batch_id,
                transaction_date=txn_date,
                post_date=txn_date,
                description=row.get("description", row.get("Description", "")),
                reference=row.get("reference", row.get("Reference", "")),
                transaction_type=txn_type,
                amount=amount,
                check_number=row.get("check_number", row.get("Check Number")),
                external_id=row.get("id", row.get("ID")),
                raw_data=dict(row),
            )
            transactions.append(txn)
            self._bank_transactions[txn.id] = txn

        batch = BankImportBatch(
            id=batch_id,
            account_id=account_id,
            bank_name=bank_name,
            file_name=file_name,
            file_format="csv",
            start_date=min_date or _utcnow(),
            end_date=max_date or _utcnow(),
            transaction_count=len(transactions),
            total_credits=total_credits,
            total_debits=total_debits,
            imported_by=actor_id,
        )
        self._import_batches[batch.id] = batch

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="bank.import.csv",
            entity_type="bank_import_batch",
            entity_id=str(batch.id),
            correlation_id=correlation_id,
            metadata={"count": len(transactions), "account": account_id},
        )

        return batch, transactions

    def export_payment_csv(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        payments: list[dict[str, Any]],
    ) -> str:
        """Export payments to CSV format for bank upload."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        output = io.StringIO()
        if not payments:
            return ""

        fieldnames = ["date", "payee", "amount", "reference", "memo"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for payment in payments:
            writer.writerow({
                "date": payment.get("date", ""),
                "payee": payment.get("payee", ""),
                "amount": str(payment.get("amount", "")),
                "reference": payment.get("reference", ""),
                "memo": payment.get("memo", ""),
            })

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="bank.export.csv",
            entity_type="payment_export",
            entity_id="batch",
            correlation_id=correlation_id,
            metadata={"count": len(payments)},
        )

        return output.getvalue()

    def list_bank_transactions(
        self,
        *,
        actor_roles: Iterable[str],
        batch_id: UUID | None = None,
        account_id: str | None = None,
    ) -> list[BankTransaction]:
        """List imported bank transactions."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _READER_ROLES, "Read access required")

        result = list(self._bank_transactions.values())

        if batch_id:
            result = [t for t in result if t.import_batch_id == batch_id]

        if account_id:
            result = [
                t for t in result
                if self._import_batches.get(t.import_batch_id, None)
                and self._import_batches[t.import_batch_id].account_id == account_id
            ]

        return result

    # ----------------------------------------------------------------
    # Reconciliation
    # ----------------------------------------------------------------

    def create_reconciliation_session(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: str,
        period_start: datetime,
        period_end: datetime,
        opening_balance: Decimal,
        closing_balance: Decimal,
    ) -> ReconciliationSession:
        """Create a new reconciliation session."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        session = ReconciliationSession(
            id=uuid4(),
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            total_items=0,
            matched_count=0,
            exception_count=0,
            status="in_progress",
            created_by=actor_id,
        )
        self._recon_sessions[session.id] = session

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="reconciliation.session.create",
            entity_type="reconciliation_session",
            entity_id=str(session.id),
            correlation_id=correlation_id,
        )

        return session

    def add_reconciliation_item(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        session_id: UUID,
        bank_transaction_id: UUID | None = None,
        book_entry_id: UUID | None = None,
        book_entry_type: str | None = None,
        bank_amount: Decimal | None = None,
        book_amount: Decimal | None = None,
        bank_date: datetime | None = None,
        book_date: datetime | None = None,
    ) -> ReconciliationItem:
        """Add an item to reconciliation."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        session = self._recon_sessions.get(session_id)
        if not session:
            raise ValueError("session_id not found")

        item = ReconciliationItem(
            id=uuid4(),
            session_id=session_id,
            bank_transaction_id=bank_transaction_id,
            book_entry_id=book_entry_id,
            book_entry_type=book_entry_type,
            bank_amount=bank_amount,
            book_amount=book_amount,
            bank_date=bank_date,
            book_date=book_date,
            status=ReconciliationStatus.UNMATCHED,
        )
        self._recon_items[item.id] = item

        # Update session counts
        updated_session = ReconciliationSession(
            id=session.id,
            account_id=session.account_id,
            period_start=session.period_start,
            period_end=session.period_end,
            opening_balance=session.opening_balance,
            closing_balance=session.closing_balance,
            total_items=session.total_items + 1,
            matched_count=session.matched_count,
            exception_count=session.exception_count,
            status=session.status,
            created_by=session.created_by,
            created_at=session.created_at,
        )
        self._recon_sessions[session.id] = updated_session

        return item

    def match_items(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: UUID,
    ) -> ReconciliationItem:
        """Mark a reconciliation item as matched."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        item = self._recon_items.get(item_id)
        if not item:
            raise ValueError("item_id not found")

        updated = ReconciliationItem(
            id=item.id,
            session_id=item.session_id,
            bank_transaction_id=item.bank_transaction_id,
            book_entry_id=item.book_entry_id,
            book_entry_type=item.book_entry_type,
            bank_amount=item.bank_amount,
            book_amount=item.book_amount,
            bank_date=item.bank_date,
            book_date=item.book_date,
            status=ReconciliationStatus.MATCHED,
            matched_at=_utcnow(),
            matched_by=actor_id,
            created_at=item.created_at,
        )
        self._recon_items[item.id] = updated

        # Update session matched count
        session = self._recon_sessions[item.session_id]
        updated_session = ReconciliationSession(
            id=session.id,
            account_id=session.account_id,
            period_start=session.period_start,
            period_end=session.period_end,
            opening_balance=session.opening_balance,
            closing_balance=session.closing_balance,
            total_items=session.total_items,
            matched_count=session.matched_count + 1,
            exception_count=session.exception_count,
            status=session.status,
            created_by=session.created_by,
            created_at=session.created_at,
        )
        self._recon_sessions[session.id] = updated_session

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="reconciliation.item.match",
            entity_type="reconciliation_item",
            entity_id=str(item.id),
            correlation_id=correlation_id,
        )

        return updated

    def create_exception(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: UUID,
        exception_type: ExceptionType,
        description: str,
    ) -> ReconciliationException:
        """Create a reconciliation exception."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        item = self._recon_items.get(item_id)
        if not item:
            raise ValueError("item_id not found")

        difference = None
        if item.bank_amount is not None and item.book_amount is not None:
            difference = item.bank_amount - item.book_amount

        exc = ReconciliationException(
            id=uuid4(),
            session_id=item.session_id,
            reconciliation_item_id=item_id,
            exception_type=exception_type,
            description=description,
            bank_amount=item.bank_amount,
            book_amount=item.book_amount,
            difference=difference,
        )
        self._exceptions[exc.id] = exc

        # Update item status
        updated_item = ReconciliationItem(
            id=item.id,
            session_id=item.session_id,
            bank_transaction_id=item.bank_transaction_id,
            book_entry_id=item.book_entry_id,
            book_entry_type=item.book_entry_type,
            bank_amount=item.bank_amount,
            book_amount=item.book_amount,
            bank_date=item.bank_date,
            book_date=item.book_date,
            status=ReconciliationStatus.EXCEPTION,
            matched_at=item.matched_at,
            matched_by=item.matched_by,
            created_at=item.created_at,
        )
        self._recon_items[item.id] = updated_item

        # Update session exception count
        session = self._recon_sessions[item.session_id]
        updated_session = ReconciliationSession(
            id=session.id,
            account_id=session.account_id,
            period_start=session.period_start,
            period_end=session.period_end,
            opening_balance=session.opening_balance,
            closing_balance=session.closing_balance,
            total_items=session.total_items,
            matched_count=session.matched_count,
            exception_count=session.exception_count + 1,
            status=session.status,
            created_by=session.created_by,
            created_at=session.created_at,
        )
        self._recon_sessions[session.id] = updated_session

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="reconciliation.exception.create",
            entity_type="reconciliation_exception",
            entity_id=str(exc.id),
            correlation_id=correlation_id,
        )

        return exc

    def resolve_exception(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        exception_id: UUID,
        resolution_notes: str,
    ) -> ReconciliationException:
        """Resolve a reconciliation exception."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _RECONCILIATION_ROLES, "Reconciliation access required")

        exc = self._exceptions.get(exception_id)
        if not exc:
            raise ValueError("exception_id not found")

        updated = ReconciliationException(
            id=exc.id,
            session_id=exc.session_id,
            reconciliation_item_id=exc.reconciliation_item_id,
            exception_type=exc.exception_type,
            description=exc.description,
            bank_amount=exc.bank_amount,
            book_amount=exc.book_amount,
            difference=exc.difference,
            resolved=True,
            resolved_by=actor_id,
            resolved_at=_utcnow(),
            resolution_notes=resolution_notes,
            created_at=exc.created_at,
        )
        self._exceptions[exc.id] = updated

        # Update item status
        item = self._recon_items[exc.reconciliation_item_id]
        updated_item = ReconciliationItem(
            id=item.id,
            session_id=item.session_id,
            bank_transaction_id=item.bank_transaction_id,
            book_entry_id=item.book_entry_id,
            book_entry_type=item.book_entry_type,
            bank_amount=item.bank_amount,
            book_amount=item.book_amount,
            bank_date=item.bank_date,
            book_date=item.book_date,
            status=ReconciliationStatus.RESOLVED,
            matched_at=item.matched_at,
            matched_by=item.matched_by,
            created_at=item.created_at,
        )
        self._recon_items[item.id] = updated_item

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="reconciliation.exception.resolve",
            entity_type="reconciliation_exception",
            entity_id=str(exc.id),
            correlation_id=correlation_id,
        )

        return updated

    def get_exception_queue(
        self,
        *,
        actor_roles: Iterable[str],
        session_id: UUID | None = None,
    ) -> list[ReconciliationException]:
        """Get unresolved exceptions (the exceptions queue)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _READER_ROLES, "Read access required")

        result = [
            exc for exc in self._exceptions.values()
            if not exc.resolved
        ]

        if session_id:
            result = [e for e in result if e.session_id == session_id]

        return result

    def get_reconciliation_summary(
        self,
        *,
        actor_roles: Iterable[str],
        session_id: UUID,
    ) -> dict[str, Any]:
        """Get summary of a reconciliation session."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _READER_ROLES, "Read access required")

        session = self._recon_sessions.get(session_id)
        if not session:
            raise ValueError("session_id not found")

        items = [i for i in self._recon_items.values() if i.session_id == session_id]
        exceptions = [e for e in self._exceptions.values() if e.session_id == session_id]

        unmatched = len([i for i in items if i.status == ReconciliationStatus.UNMATCHED])
        matched = len([i for i in items if i.status == ReconciliationStatus.MATCHED])
        with_exceptions = len([i for i in items if i.status == ReconciliationStatus.EXCEPTION])
        resolved = len([i for i in items if i.status == ReconciliationStatus.RESOLVED])

        unresolved_exceptions = len([e for e in exceptions if not e.resolved])

        return {
            "session_id": str(session.id),
            "account_id": session.account_id,
            "period": {
                "start": session.period_start.isoformat(),
                "end": session.period_end.isoformat(),
            },
            "balances": {
                "opening": str(session.opening_balance),
                "closing": str(session.closing_balance),
            },
            "items": {
                "total": len(items),
                "unmatched": unmatched,
                "matched": matched,
                "with_exceptions": with_exceptions,
                "resolved": resolved,
            },
            "exceptions": {
                "total": len(exceptions),
                "unresolved": unresolved_exceptions,
                "resolved": len(exceptions) - unresolved_exceptions,
            },
            "status": session.status,
        }

    # ----------------------------------------------------------------
    # Audit
    # ----------------------------------------------------------------

    def list_audit_events(
        self, *, actor_roles: Iterable[str]
    ) -> list[AuditEvent]:
        """List audit events."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _READER_ROLES, "Read access required")
        return list(self._audit)

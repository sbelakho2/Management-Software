"""Accounts Receivable (Order-to-Cash) service.

Implements Development Plan Section 22.2:
- Quote → Sales Order
- Invoicing + credit memos
- Receipts + allocation
- A/R aging + dunning + disputes
- Customer credit controls

State is persisted via the service_state table for DB-backed continuity.
Optionally integrates with `AccountingLedgerService` to post GL journal entries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _encode_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _decode_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _encode_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _encode_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _encode_uuid(value: UUID | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _decode_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    return UUID(value)


def _encode_audit_event(event: "AuditEvent") -> dict[str, Any]:
    return {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": event.actor_id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "correlation_id": event.correlation_id,
        "metadata": event.metadata,
    }


def _decode_audit_event(data: dict[str, Any]) -> "AuditEvent":
    return AuditEvent(
        id=UUID(data["id"]),
        occurred_at=datetime.fromisoformat(data["occurred_at"]),
        actor_id=data["actor_id"],
        action=data["action"],
        entity_type=data["entity_type"],
        entity_id=data["entity_id"],
        correlation_id=data.get("correlation_id", ""),
        metadata=data.get("metadata", {}) or {},
    )


def _encode_credit_profile(profile: "CustomerCreditProfile") -> dict[str, Any]:
    return {
        "account_id": profile.account_id,
        "credit_limit": _encode_decimal(profile.credit_limit),
        "currency": profile.currency,
        "is_on_credit_hold": profile.is_on_credit_hold,
        "hold_reason": profile.hold_reason,
        "updated_at": profile.updated_at.isoformat(),
    }


def _decode_credit_profile(data: dict[str, Any]) -> "CustomerCreditProfile":
    return CustomerCreditProfile(
        account_id=data.get("account_id", ""),
        credit_limit=Decimal(data.get("credit_limit", "0")),
        currency=data.get("currency", ""),
        is_on_credit_hold=bool(data.get("is_on_credit_hold", False)),
        hold_reason=data.get("hold_reason"),
        updated_at=datetime.fromisoformat(data["updated_at"])
        if data.get("updated_at")
        else _now(),
    )


def _encode_sales_order_line(line: "SalesOrderLine") -> dict[str, Any]:
    return {
        "sku": line.sku,
        "description": line.description,
        "quantity": _encode_decimal(line.quantity),
        "unit_price": _encode_decimal(line.unit_price),
    }


def _decode_sales_order_line(data: dict[str, Any]) -> "SalesOrderLine":
    return SalesOrderLine(
        sku=data.get("sku", ""),
        description=data.get("description", ""),
        quantity=Decimal(data.get("quantity", "0")),
        unit_price=Decimal(data.get("unit_price", "0")),
    )


def _encode_sales_order(order: "SalesOrder") -> dict[str, Any]:
    return {
        "id": str(order.id),
        "so_number": order.so_number,
        "account_id": order.account_id,
        "currency": order.currency,
        "created_at": order.created_at.isoformat(),
        "created_by": order.created_by,
        "status": order.status.value,
        "approved_at": _encode_datetime(order.approved_at),
        "approved_by": order.approved_by,
        "released_at": _encode_datetime(order.released_at),
        "released_by": order.released_by,
        "source_quote_id": order.source_quote_id,
        "source_quote_version": order.source_quote_version,
        "payment_terms_days": order.payment_terms_days,
        "lines": [_encode_sales_order_line(line) for line in order.lines],
        "metadata": order.metadata,
    }


def _decode_sales_order(data: dict[str, Any]) -> "SalesOrder":
    return SalesOrder(
        id=UUID(data["id"]),
        so_number=data.get("so_number", ""),
        account_id=data.get("account_id", ""),
        currency=data.get("currency", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        status=SalesOrderStatus(data.get("status", SalesOrderStatus.DRAFT.value)),
        approved_at=_decode_datetime(data.get("approved_at")),
        approved_by=data.get("approved_by"),
        released_at=_decode_datetime(data.get("released_at")),
        released_by=data.get("released_by"),
        source_quote_id=data.get("source_quote_id"),
        source_quote_version=data.get("source_quote_version"),
        payment_terms_days=int(data.get("payment_terms_days", 30)),
        lines=[_decode_sales_order_line(line) for line in data.get("lines", [])],
        metadata=data.get("metadata", {}) or {},
    )


def _encode_invoice_line(line: "InvoiceLine") -> dict[str, Any]:
    return {
        "sku": line.sku,
        "description": line.description,
        "quantity": _encode_decimal(line.quantity),
        "unit_price": _encode_decimal(line.unit_price),
    }


def _decode_invoice_line(data: dict[str, Any]) -> "InvoiceLine":
    return InvoiceLine(
        sku=data.get("sku", ""),
        description=data.get("description", ""),
        quantity=Decimal(data.get("quantity", "0")),
        unit_price=Decimal(data.get("unit_price", "0")),
    )


def _encode_invoice(inv: "Invoice") -> dict[str, Any]:
    return {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "account_id": inv.account_id,
        "currency": inv.currency,
        "issued_at": inv.issued_at.isoformat(),
        "issued_by": inv.issued_by,
        "due_date": inv.due_date.isoformat(),
        "status": inv.status.value,
        "sales_order_id": _encode_uuid(inv.sales_order_id),
        "memo": inv.memo,
        "is_credit_memo": inv.is_credit_memo,
        "lines": [_encode_invoice_line(line) for line in inv.lines],
        "disputed": inv.disputed,
    }


def _decode_invoice(data: dict[str, Any]) -> "Invoice":
    return Invoice(
        id=UUID(data["id"]),
        invoice_number=data.get("invoice_number", ""),
        account_id=data.get("account_id", ""),
        currency=data.get("currency", ""),
        issued_at=datetime.fromisoformat(data["issued_at"]),
        issued_by=data.get("issued_by", ""),
        due_date=date.fromisoformat(data["due_date"]),
        status=InvoiceStatus(data.get("status", InvoiceStatus.ISSUED.value)),
        sales_order_id=_decode_uuid(data.get("sales_order_id")),
        memo=data.get("memo"),
        is_credit_memo=bool(data.get("is_credit_memo", False)),
        lines=[_decode_invoice_line(line) for line in data.get("lines", [])],
        disputed=bool(data.get("disputed", False)),
    )


def _encode_payment_allocation(alloc: "PaymentAllocation") -> dict[str, Any]:
    return {
        "invoice_id": str(alloc.invoice_id),
        "amount": _encode_decimal(alloc.amount),
    }


def _decode_payment_allocation(data: dict[str, Any]) -> "PaymentAllocation":
    return PaymentAllocation(
        invoice_id=UUID(data["invoice_id"]),
        amount=Decimal(data.get("amount", "0")),
    )


def _encode_payment_receipt(receipt: "PaymentReceipt") -> dict[str, Any]:
    return {
        "id": str(receipt.id),
        "account_id": receipt.account_id,
        "received_at": receipt.received_at.isoformat(),
        "received_by": receipt.received_by,
        "currency": receipt.currency,
        "amount": _encode_decimal(receipt.amount),
        "status": receipt.status.value,
        "allocations": [_encode_payment_allocation(a) for a in receipt.allocations],
        "reference": receipt.reference,
        "notes": receipt.notes,
    }


def _decode_payment_receipt(data: dict[str, Any]) -> "PaymentReceipt":
    return PaymentReceipt(
        id=UUID(data["id"]),
        account_id=data.get("account_id", ""),
        received_at=datetime.fromisoformat(data["received_at"]),
        received_by=data.get("received_by", ""),
        currency=data.get("currency", ""),
        amount=Decimal(data.get("amount", "0")),
        status=PaymentStatus(data.get("status", PaymentStatus.POSTED.value)),
        allocations=[_decode_payment_allocation(a) for a in data.get("allocations", [])],
        reference=data.get("reference"),
        notes=data.get("notes"),
    )


def _encode_invoice_dispute(dispute: "InvoiceDispute") -> dict[str, Any]:
    return {
        "id": str(dispute.id),
        "invoice_id": str(dispute.invoice_id),
        "opened_at": dispute.opened_at.isoformat(),
        "opened_by": dispute.opened_by,
        "reason": dispute.reason,
        "status": dispute.status.value,
        "resolved_at": _encode_datetime(dispute.resolved_at),
        "resolved_by": dispute.resolved_by,
        "resolution": dispute.resolution,
    }


def _decode_invoice_dispute(data: dict[str, Any]) -> "InvoiceDispute":
    return InvoiceDispute(
        id=UUID(data["id"]),
        invoice_id=UUID(data["invoice_id"]),
        opened_at=datetime.fromisoformat(data["opened_at"]),
        opened_by=data.get("opened_by", ""),
        reason=data.get("reason", ""),
        status=DisputeStatus(data.get("status", DisputeStatus.OPEN.value)),
        resolved_at=_decode_datetime(data.get("resolved_at")),
        resolved_by=data.get("resolved_by"),
        resolution=data.get("resolution"),
    )


def _encode_config(cfg: "ARConfig") -> dict[str, Any]:
    return {
        "base_currency": cfg.base_currency,
        "invoice_prefix": cfg.invoice_prefix,
        "sales_order_prefix": cfg.sales_order_prefix,
        "next_invoice_seq": cfg.next_invoice_seq,
        "next_so_seq": cfg.next_so_seq,
        "ar_account_code": cfg.ar_account_code,
        "revenue_account_code": cfg.revenue_account_code,
        "cash_account_code": cfg.cash_account_code,
    }


def _decode_config(data: dict[str, Any], fallback: "ARConfig") -> "ARConfig":
    return ARConfig(
        base_currency=data.get("base_currency", fallback.base_currency),
        invoice_prefix=data.get("invoice_prefix", fallback.invoice_prefix),
        sales_order_prefix=data.get("sales_order_prefix", fallback.sales_order_prefix),
        next_invoice_seq=int(data.get("next_invoice_seq", fallback.next_invoice_seq)),
        next_so_seq=int(data.get("next_so_seq", fallback.next_so_seq)),
        ar_account_code=data.get("ar_account_code", fallback.ar_account_code),
        revenue_account_code=data.get("revenue_account_code", fallback.revenue_account_code),
        cash_account_code=data.get("cash_account_code", fallback.cash_account_code),
    )


_AR_READ_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "auditor",
    "sales",
}

_AR_WRITE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "sales",
}

_AR_APPROVE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
}


class SalesOrderStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ON_HOLD = "on_hold"
    RELEASED = "released"
    CLOSED = "closed"
    CANCELED = "canceled"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class PaymentStatus(str, Enum):
    POSTED = "posted"
    REVERSED = "reversed"


class DisputeStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    occurred_at: datetime
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerCreditProfile:
    account_id: str
    credit_limit: Decimal
    currency: str
    is_on_credit_hold: bool = False
    hold_reason: str | None = None
    updated_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class SalesOrderLine:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _q2(self.quantity * self.unit_price)


@dataclass
class SalesOrder:
    id: UUID
    so_number: str
    account_id: str
    currency: str
    created_at: datetime
    created_by: str
    status: SalesOrderStatus = SalesOrderStatus.DRAFT
    approved_at: datetime | None = None
    approved_by: str | None = None
    released_at: datetime | None = None
    released_by: str | None = None

    source_quote_id: str | None = None
    source_quote_version: int | None = None

    payment_terms_days: int = 30
    lines: list[SalesOrderLine] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> Decimal:
        return _q2(sum((ln.line_total for ln in self.lines), Decimal("0")))


@dataclass(frozen=True)
class InvoiceLine:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _q2(self.quantity * self.unit_price)


@dataclass
class Invoice:
    id: UUID
    invoice_number: str
    account_id: str
    currency: str
    issued_at: datetime
    issued_by: str
    due_date: date
    status: InvoiceStatus = InvoiceStatus.ISSUED

    sales_order_id: UUID | None = None
    memo: str | None = None
    is_credit_memo: bool = False

    lines: list[InvoiceLine] = field(default_factory=list)
    disputed: bool = False

    @property
    def total(self) -> Decimal:
        return _q2(sum((ln.line_total for ln in self.lines), Decimal("0")))


@dataclass(frozen=True)
class PaymentAllocation:
    invoice_id: UUID
    amount: Decimal


@dataclass
class PaymentReceipt:
    id: UUID
    account_id: str
    received_at: datetime
    received_by: str
    currency: str
    amount: Decimal
    status: PaymentStatus = PaymentStatus.POSTED
    allocations: list[PaymentAllocation] = field(default_factory=list)
    reference: str | None = None
    notes: str | None = None


@dataclass
class InvoiceDispute:
    id: UUID
    invoice_id: UUID
    opened_at: datetime
    opened_by: str
    reason: str
    status: DisputeStatus = DisputeStatus.OPEN
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution: str | None = None


@dataclass(frozen=True)
class DunningAction:
    invoice_id: UUID
    bucket: str
    message: str


@dataclass
class ARConfig:
    base_currency: str = "EUR"
    invoice_prefix: str = "INV"
    sales_order_prefix: str = "SO"
    next_invoice_seq: int = 1
    next_so_seq: int = 1

    # When integrating with GL
    ar_account_code: str = "1100"  # Accounts Receivable
    revenue_account_code: str = "4000"  # Revenue
    cash_account_code: str = "1000"  # Cash/Bank


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


def _norm_currency(c: str) -> str:
    cc = (c or "").strip().upper()
    if len(cc) != 3 or not cc.isalpha():
        raise ValueError("Invalid currency")
    return cc


def _parse_quote_like(quote: Any) -> dict[str, Any]:
    """Accept either a SQLAlchemy Quote model or a dict-like input."""
    # Use attribute access first
    if hasattr(quote, "id"):
        return {
            "id": str(getattr(quote, "id")),
            "account_id": str(getattr(quote, "account_id")),
            "currency": str(getattr(quote, "currency")),
            "total": Decimal(str(getattr(quote, "total"))),
            "current_version": int(getattr(quote, "current_version")),
            "status": str(getattr(quote, "status")),
            "approval_status": str(getattr(quote, "approval_status")),
        }
    # Fallback dict
    return {
        "id": str(quote["id"]),
        "account_id": str(quote["account_id"]),
        "currency": str(quote.get("currency", "EUR")),
        "total": Decimal(str(quote.get("total", "0"))),
        "current_version": int(quote.get("current_version", 1)),
        "status": str(quote.get("status", "")),
        "approval_status": str(quote.get("approval_status", "")),
    }


class AccountsReceivableService(PersistentServiceMixin):
    """Order-to-cash workflows with optional GL postings.

    In-memory state backed by PostgreSQL ar_invoices, ar_payments,
    and credit_memos tables.
    """

    SERVICE_NAME = "accounts_receivable"

    def __init__(self, *, config: ARConfig | None = None, ledger: Any | None = None):
        self._cfg = config or ARConfig()
        self._ledger = ledger

        self._sales_orders: dict[UUID, SalesOrder] = {}
        self._invoices: dict[UUID, Invoice] = {}
        self._payments: dict[UUID, PaymentReceipt] = {}
        self._credit: dict[str, CustomerCreditProfile] = {}
        self._disputes: dict[UUID, InvoiceDispute] = {}

        self._audit: list[AuditEvent] = []
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        cfg_data = await self.load_state(_DEFAULT_TENANT_ID, "config") or {}
        sales_orders_data = await self.load_state(_DEFAULT_TENANT_ID, "sales_orders") or {}
        invoices_data = await self.load_state(_DEFAULT_TENANT_ID, "invoices") or {}
        payments_data = await self.load_state(_DEFAULT_TENANT_ID, "payments") or {}
        credit_data = await self.load_state(_DEFAULT_TENANT_ID, "credit") or {}
        disputes_data = await self.load_state(_DEFAULT_TENANT_ID, "disputes") or {}
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []

        if cfg_data:
            self._cfg = _decode_config(cfg_data, self._cfg)

        self._sales_orders = {UUID(sid): _decode_sales_order(s) for sid, s in sales_orders_data.items()}
        self._invoices = {UUID(iid): _decode_invoice(i) for iid, i in invoices_data.items()}
        self._payments = {UUID(pid): _decode_payment_receipt(p) for pid, p in payments_data.items()}
        self._credit = {cid: _decode_credit_profile(c) for cid, c in credit_data.items()}
        self._disputes = {UUID(did): _decode_invoice_dispute(d) for did, d in disputes_data.items()}
        self._audit = [_decode_audit_event(a) for a in audit_data]

        self._state_loaded = True

    async def persist_all(self) -> None:
        cfg_data = _encode_config(self._cfg)
        sales_orders_data = {str(sid): _encode_sales_order(so) for sid, so in self._sales_orders.items()}
        invoices_data = {str(iid): _encode_invoice(inv) for iid, inv in self._invoices.items()}
        payments_data = {str(pid): _encode_payment_receipt(p) for pid, p in self._payments.items()}
        credit_data = {cid: _encode_credit_profile(c) for cid, c in self._credit.items()}
        disputes_data = {str(did): _encode_invoice_dispute(d) for did, d in self._disputes.items()}
        audit_data = [_encode_audit_event(a) for a in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "config", cfg_data)
        await self.save_state(_DEFAULT_TENANT_ID, "sales_orders", sales_orders_data)
        await self.save_state(_DEFAULT_TENANT_ID, "invoices", invoices_data)
        await self.save_state(_DEFAULT_TENANT_ID, "payments", payments_data)
        await self.save_state(_DEFAULT_TENANT_ID, "credit", credit_data)
        await self.save_state(_DEFAULT_TENANT_ID, "disputes", disputes_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    async def list_audit_events_async(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(actor_roles=actor_roles)

    async def set_credit_profile_async(self, **kwargs: Any) -> CustomerCreditProfile:
        await self._ensure_loaded()
        profile = self.set_credit_profile(**kwargs)
        await self.persist_all()
        return profile

    async def get_credit_profile_async(self, *, actor_roles: Iterable[str], account_id: str) -> CustomerCreditProfile | None:
        await self._ensure_loaded()
        return self.get_credit_profile(actor_roles=actor_roles, account_id=account_id)

    async def create_sales_order_from_quote_async(self, **kwargs: Any) -> SalesOrder:
        await self._ensure_loaded()
        so = self.create_sales_order_from_quote(**kwargs)
        await self.persist_all()
        return so

    async def approve_sales_order_async(self, **kwargs: Any) -> SalesOrder:
        await self._ensure_loaded()
        so = self.approve_sales_order(**kwargs)
        await self.persist_all()
        return so

    async def release_sales_order_async(self, **kwargs: Any) -> SalesOrder:
        await self._ensure_loaded()
        so = self.release_sales_order(**kwargs)
        await self.persist_all()
        return so

    async def get_sales_order_async(self, *, actor_roles: Iterable[str], sales_order_id: UUID) -> SalesOrder | None:
        await self._ensure_loaded()
        return self.get_sales_order(actor_roles=actor_roles, sales_order_id=sales_order_id)

    async def create_invoice_from_sales_order_async(self, **kwargs: Any) -> Invoice:
        await self._ensure_loaded()
        inv = self.create_invoice_from_sales_order(**kwargs)
        await self.persist_all()
        return inv

    async def create_credit_memo_async(self, **kwargs: Any) -> Invoice:
        await self._ensure_loaded()
        inv = self.create_credit_memo(**kwargs)
        await self.persist_all()
        return inv

    async def get_invoice_async(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> Invoice | None:
        await self._ensure_loaded()
        return self.get_invoice(actor_roles=actor_roles, invoice_id=invoice_id)

    async def list_invoices_async(self, *, actor_roles: Iterable[str], account_id: str | None = None) -> list[Invoice]:
        await self._ensure_loaded()
        return self.list_invoices(actor_roles=actor_roles, account_id=account_id)

    async def open_dispute_async(self, **kwargs: Any) -> InvoiceDispute:
        await self._ensure_loaded()
        dispute = self.open_dispute(**kwargs)
        await self.persist_all()
        return dispute

    async def resolve_dispute_async(self, **kwargs: Any) -> InvoiceDispute:
        await self._ensure_loaded()
        dispute = self.resolve_dispute(**kwargs)
        await self.persist_all()
        return dispute

    async def record_payment_async(self, **kwargs: Any) -> PaymentReceipt:
        await self._ensure_loaded()
        payment = self.record_payment(**kwargs)
        await self.persist_all()
        return payment

    async def invoice_balance_async(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> Decimal:
        await self._ensure_loaded()
        return self.invoice_balance(actor_roles=actor_roles, invoice_id=invoice_id)

    async def ar_aging_async(self, *, actor_roles: Iterable[str], as_of: date, account_id: str | None = None) -> dict[str, Decimal]:
        await self._ensure_loaded()
        return self.ar_aging(actor_roles=actor_roles, as_of=as_of, account_id=account_id)

    async def dunning_actions_async(self, *, actor_roles: Iterable[str], as_of: date, account_id: str) -> list[DunningAction]:
        await self._ensure_loaded()
        return self.dunning_actions(actor_roles=actor_roles, as_of=as_of, account_id=account_id)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")
        return list(self._audit)

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
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_WRITE_ROLES, "AR write role required")
        self._audit.append(
            AuditEvent(
                id=uuid4(),
                occurred_at=_now(),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                metadata=metadata or {},
            )
        )

    # ------------------------------------------------------------------
    # Credit controls
    # ------------------------------------------------------------------

    def set_credit_profile(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: str,
        credit_limit: Decimal,
        currency: str,
        credit_hold: bool = False,
        hold_reason: str | None = None,
    ) -> CustomerCreditProfile:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_WRITE_ROLES, "AR write role required")
        if credit_limit < 0:
            raise ValueError("credit_limit must be >= 0")
        cur = _norm_currency(currency)
        profile = CustomerCreditProfile(
            account_id=str(account_id),
            credit_limit=_q2(credit_limit),
            currency=cur,
            is_on_credit_hold=bool(credit_hold),
            hold_reason=(hold_reason or None),
        )
        self._credit[profile.account_id] = profile
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.credit.set",
            entity_type="credit_profile",
            entity_id=profile.account_id,
            correlation_id=correlation_id,
        )
        return profile

    def get_credit_profile(self, *, actor_roles: Iterable[str], account_id: str) -> CustomerCreditProfile | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")
        return self._credit.get(str(account_id))

    def _outstanding_for_account(self, *, account_id: str, currency: str) -> Decimal:
        # Sum issued invoices - payments allocated, excluding void
        inv_total = Decimal("0")
        for inv in self._invoices.values():
            if inv.account_id != account_id or inv.currency != currency:
                continue
            if inv.status == InvoiceStatus.VOID:
                continue
            inv_total += inv.total

        paid = Decimal("0")
        for pay in self._payments.values():
            if pay.account_id != account_id or pay.currency != currency:
                continue
            if pay.status != PaymentStatus.POSTED:
                continue
            for alloc in pay.allocations:
                paid += alloc.amount

        return _q2(inv_total - paid)

    # ------------------------------------------------------------------
    # Quote → Sales Order
    # ------------------------------------------------------------------

    def create_sales_order_from_quote(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        quote: Any,
        lines: list[SalesOrderLine],
        payment_terms_days: int | None = None,
    ) -> SalesOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_WRITE_ROLES, "AR write role required")

        q = _parse_quote_like(quote)
        approval = (q.get("approval_status") or "").lower()
        if approval not in {"approved", "not_required"}:
            raise ValueError("Quote must be approved (or not require approval) to create Sales Order")

        cur = _norm_currency(q.get("currency") or self._cfg.base_currency)
        if not lines:
            raise ValueError("Sales order must have at least one line")

        so_number = f"{self._cfg.sales_order_prefix}-{self._cfg.next_so_seq:06d}"
        self._cfg.next_so_seq += 1

        so = SalesOrder(
            id=uuid4(),
            so_number=so_number,
            account_id=str(q["account_id"]),
            currency=cur,
            created_at=_now(),
            created_by=actor_id,
            source_quote_id=str(q["id"]),
            source_quote_version=int(q.get("current_version") or 1),
            payment_terms_days=int(payment_terms_days or 30),
            lines=list(lines),
        )

        self._sales_orders[so.id] = so
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.sales_order.create_from_quote",
            entity_type="sales_order",
            entity_id=str(so.id),
            correlation_id=correlation_id,
            metadata={"so_number": so_number, "quote_id": so.source_quote_id},
        )

        return so

    def approve_sales_order(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        sales_order_id: UUID,
        override_credit: bool = False,
        override_reason: str | None = None,
    ) -> SalesOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_APPROVE_ROLES, "AR approve role required")

        so = self._sales_orders.get(sales_order_id)
        if so is None:
            raise ValueError("Unknown sales order")
        if so.status != SalesOrderStatus.DRAFT:
            return so

        # Credit checks
        profile = self._credit.get(so.account_id)
        if profile and profile.is_on_credit_hold:
            if not override_credit:
                so.status = SalesOrderStatus.ON_HOLD
                raise ValueError("Customer is on credit hold")
            reason = (override_reason or "").strip()
            if not reason:
                raise ValueError("override_reason required for credit override")
            so.metadata.update(
                {
                    "credit_override": True,
                    "credit_override_reason": reason,
                    "credit_override_by": actor_id,
                    "credit_override_at": _now().isoformat(),
                    "credit_override_type": "credit_hold",
                }
            )
            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="ar.credit.override",
                entity_type="sales_order",
                entity_id=str(so.id),
                correlation_id=correlation_id,
                metadata={"type": "credit_hold", "reason": reason},
            )

        if profile and profile.currency == so.currency:
            outstanding = self._outstanding_for_account(account_id=so.account_id, currency=so.currency)
            projected = _q2(outstanding + so.total)
            if projected > profile.credit_limit:
                if not override_credit:
                    so.status = SalesOrderStatus.ON_HOLD
                    raise ValueError("Credit limit exceeded")
                reason = (override_reason or "").strip()
                if not reason:
                    raise ValueError("override_reason required for credit override")
                so.metadata.update(
                    {
                        "credit_override": True,
                        "credit_override_reason": reason,
                        "credit_override_by": actor_id,
                        "credit_override_at": _now().isoformat(),
                        "credit_override_type": "credit_limit",
                        "credit_limit": str(profile.credit_limit),
                        "projected_exposure": str(projected),
                    }
                )
                self._audit_event(
                    actor_id=actor_id,
                    actor_roles=roles,
                    action="ar.credit.override",
                    entity_type="sales_order",
                    entity_id=str(so.id),
                    correlation_id=correlation_id,
                    metadata={"type": "credit_limit", "reason": reason, "projected": str(projected)},
                )

        so.status = SalesOrderStatus.APPROVED
        so.approved_at = _now()
        so.approved_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.sales_order.approve",
            entity_type="sales_order",
            entity_id=str(so.id),
            correlation_id=correlation_id,
        )
        return so

    def release_sales_order(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        sales_order_id: UUID,
    ) -> SalesOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_APPROVE_ROLES, "AR approve role required")

        so = self._sales_orders.get(sales_order_id)
        if so is None:
            raise ValueError("Unknown sales order")
        if so.status not in {SalesOrderStatus.APPROVED, SalesOrderStatus.RELEASED}:
            raise ValueError("Sales order must be approved before release")

        so.status = SalesOrderStatus.RELEASED
        so.released_at = _now()
        so.released_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.sales_order.release",
            entity_type="sales_order",
            entity_id=str(so.id),
            correlation_id=correlation_id,
        )
        return so

    def get_sales_order(self, *, actor_roles: Iterable[str], sales_order_id: UUID) -> SalesOrder | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")
        return self._sales_orders.get(sales_order_id)

    # ------------------------------------------------------------------
    # Invoicing
    # ------------------------------------------------------------------

    def create_invoice_from_sales_order(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        sales_order_id: UUID,
        issue_date: date,
        memo: str | None = None,
        invoice_terms_days: int | None = None,
    ) -> Invoice:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_WRITE_ROLES, "AR write role required")

        so = self._sales_orders.get(sales_order_id)
        if so is None:
            raise ValueError("Unknown sales order")
        if so.status != SalesOrderStatus.RELEASED:
            raise ValueError("Sales order must be released before invoicing")

        inv_number = f"{self._cfg.invoice_prefix}-{self._cfg.next_invoice_seq:06d}"
        self._cfg.next_invoice_seq += 1

        terms = int(invoice_terms_days or so.payment_terms_days)
        due = issue_date + timedelta(days=terms)

        lines = [InvoiceLine(sku=ln.sku, description=ln.description, quantity=ln.quantity, unit_price=ln.unit_price) for ln in so.lines]
        inv = Invoice(
            id=uuid4(),
            invoice_number=inv_number,
            account_id=so.account_id,
            currency=so.currency,
            issued_at=datetime.combine(issue_date, datetime.min.time(), tzinfo=timezone.utc),
            issued_by=actor_id,
            due_date=due,
            sales_order_id=so.id,
            memo=memo,
            lines=lines,
        )

        self._invoices[inv.id] = inv
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.invoice.create",
            entity_type="invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
            metadata={"invoice_number": inv_number, "so_id": str(so.id)},
        )

        self._post_invoice_to_gl(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            invoice=inv,
        )

        return inv

    def create_credit_memo(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: str,
        currency: str,
        issue_date: date,
        reason: str,
        amount: Decimal,
        reference_invoice_id: UUID | None = None,
    ) -> Invoice:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_APPROVE_ROLES, "AR approve role required")

        amt = _q2(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        cur = _norm_currency(currency)

        inv_number = f"CM-{self._cfg.next_invoice_seq:06d}"
        self._cfg.next_invoice_seq += 1

        line = InvoiceLine(sku="CREDIT", description=reason, quantity=Decimal("1"), unit_price=-amt)
        inv = Invoice(
            id=uuid4(),
            invoice_number=inv_number,
            account_id=str(account_id),
            currency=cur,
            issued_at=datetime.combine(issue_date, datetime.min.time(), tzinfo=timezone.utc),
            issued_by=actor_id,
            due_date=issue_date,
            is_credit_memo=True,
            memo=reason,
            lines=[line],
        )
        self._invoices[inv.id] = inv
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.credit_memo.create",
            entity_type="invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
            metadata={"reference_invoice_id": str(reference_invoice_id) if reference_invoice_id else None},
        )

        self._post_invoice_to_gl(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, invoice=inv)
        return inv

    def get_invoice(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> Invoice | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")
        return self._invoices.get(invoice_id)

    def list_invoices(self, *, actor_roles: Iterable[str], account_id: str | None = None) -> list[Invoice]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")
        invoices = list(self._invoices.values())
        if account_id:
            invoices = [i for i in invoices if i.account_id == str(account_id)]
        invoices.sort(key=lambda i: (i.issued_at, i.invoice_number))
        return invoices

    # ------------------------------------------------------------------
    # Disputes
    # ------------------------------------------------------------------

    def open_dispute(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        invoice_id: UUID,
        reason: str,
    ) -> InvoiceDispute:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_WRITE_ROLES, "AR write role required")

        inv = self._invoices.get(invoice_id)
        if inv is None:
            raise ValueError("Unknown invoice")
        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")

        inv.disputed = True
        dispute = InvoiceDispute(id=uuid4(), invoice_id=inv.id, opened_at=_now(), opened_by=actor_id, reason=r)
        self._disputes[dispute.id] = dispute
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.dispute.open",
            entity_type="invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
            metadata={"dispute_id": str(dispute.id)},
        )
        return dispute

    def resolve_dispute(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        dispute_id: UUID,
        resolution: str,
    ) -> InvoiceDispute:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_APPROVE_ROLES, "AR approve role required")

        dispute = self._disputes.get(dispute_id)
        if dispute is None:
            raise ValueError("Unknown dispute")
        if dispute.status == DisputeStatus.RESOLVED:
            return dispute
        res = (resolution or "").strip()
        if not res:
            raise ValueError("resolution required")

        dispute.status = DisputeStatus.RESOLVED
        dispute.resolved_at = _now()
        dispute.resolved_by = actor_id
        dispute.resolution = res

        inv = self._invoices.get(dispute.invoice_id)
        if inv:
            inv.disputed = False

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.dispute.resolve",
            entity_type="invoice",
            entity_id=str(dispute.invoice_id),
            correlation_id=correlation_id,
            metadata={"dispute_id": str(dispute.id)},
        )
        return dispute

    # ------------------------------------------------------------------
    # Receipts
    # ------------------------------------------------------------------

    def record_payment(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: str,
        currency: str,
        amount: Decimal,
        received_at: datetime | None = None,
        reference: str | None = None,
        notes: str | None = None,
    ) -> PaymentReceipt:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_WRITE_ROLES, "AR write role required")

        amt = _q2(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        cur = _norm_currency(currency)

        pay = PaymentReceipt(
            id=uuid4(),
            account_id=str(account_id),
            received_at=received_at or _now(),
            received_by=actor_id,
            currency=cur,
            amount=amt,
            reference=reference,
            notes=notes,
        )

        # Allocate FIFO to oldest outstanding invoices (excluding disputed/void)
        remaining = amt
        invoices = [
            i
            for i in self.list_invoices(actor_roles=roles, account_id=pay.account_id)
            if i.currency == cur and i.status != InvoiceStatus.VOID and not i.disputed
        ]

        for inv in invoices:
            if remaining <= 0:
                break
            inv_balance = self.invoice_balance(actor_roles=roles, invoice_id=inv.id)
            if inv_balance <= 0:
                continue
            alloc = min(inv_balance, remaining)
            pay.allocations.append(PaymentAllocation(invoice_id=inv.id, amount=_q2(alloc)))
            remaining = _q2(remaining - alloc)

        self._payments[pay.id] = pay

        # Update invoice statuses
        for inv in invoices:
            if self.invoice_balance(actor_roles=roles, invoice_id=inv.id) == 0:
                inv.status = InvoiceStatus.PAID

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ar.payment.record",
            entity_type="payment",
            entity_id=str(pay.id),
            correlation_id=correlation_id,
            metadata={"allocated_invoice_ids": [str(a.invoice_id) for a in pay.allocations]},
        )

        self._post_payment_to_gl(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, payment=pay)
        return pay

    def invoice_balance(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> Decimal:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")
        inv = self._invoices.get(invoice_id)
        if inv is None:
            raise ValueError("Unknown invoice")

        paid = Decimal("0")
        for pay in self._payments.values():
            if pay.status != PaymentStatus.POSTED:
                continue
            for alloc in pay.allocations:
                if alloc.invoice_id == inv.id:
                    paid += alloc.amount
        return _q2(inv.total - paid)

    # ------------------------------------------------------------------
    # Aging + Dunning
    # ------------------------------------------------------------------

    def ar_aging(self, *, actor_roles: Iterable[str], as_of: date, account_id: str | None = None) -> dict[str, Decimal]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")

        buckets = {
            "current": Decimal("0"),
            "1_30": Decimal("0"),
            "31_60": Decimal("0"),
            "61_90": Decimal("0"),
            "91_plus": Decimal("0"),
        }

        for inv in self._invoices.values():
            if inv.status == InvoiceStatus.VOID:
                continue
            if account_id and inv.account_id != str(account_id):
                continue
            bal = self.invoice_balance(actor_roles=roles, invoice_id=inv.id)
            if bal <= 0:
                continue
            days_past_due = (as_of - inv.due_date).days
            if days_past_due <= 0:
                buckets["current"] += bal
            elif days_past_due <= 30:
                buckets["1_30"] += bal
            elif days_past_due <= 60:
                buckets["31_60"] += bal
            elif days_past_due <= 90:
                buckets["61_90"] += bal
            else:
                buckets["91_plus"] += bal

        return {k: _q2(v) for k, v in buckets.items()}

    def dunning_actions(self, *, actor_roles: Iterable[str], as_of: date, account_id: str) -> list[DunningAction]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AR_READ_ROLES, "AR read role required")

        actions: list[DunningAction] = []
        for inv in self.list_invoices(actor_roles=roles, account_id=account_id):
            if inv.status == InvoiceStatus.VOID or inv.disputed:
                continue
            bal = self.invoice_balance(actor_roles=roles, invoice_id=inv.id)
            if bal <= 0:
                continue
            days_past_due = (as_of - inv.due_date).days
            if days_past_due <= 0:
                continue

            if days_past_due <= 7:
                bucket = "gentle"
                msg = f"Reminder: Invoice {inv.invoice_number} is overdue by {days_past_due} days."
            elif days_past_due <= 30:
                bucket = "firm"
                msg = f"Action required: Invoice {inv.invoice_number} is {days_past_due} days overdue."
            else:
                bucket = "escalate"
                msg = f"Escalation: Invoice {inv.invoice_number} is {days_past_due} days overdue; consider credit hold."

            actions.append(DunningAction(invoice_id=inv.id, bucket=bucket, message=msg))

        return actions

    # ------------------------------------------------------------------
    # GL integration
    # ------------------------------------------------------------------

    def _post_invoice_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        invoice: Invoice,
    ) -> None:
        if self._ledger is None:
            return

        # Debit AR, credit Revenue for invoice totals. For credit memo, reverse.
        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        roles = _norm_roles(actor_roles)

        amt = invoice.total
        if invoice.is_credit_memo:
            amt = -amt

        lines = [
            GLLine(
                account_code=self._cfg.ar_account_code,
                debit=_q2(amt) if amt > 0 else Decimal("0"),
                credit=Decimal("0") if amt > 0 else _q2(-amt),
                currency=invoice.currency,
                memo=f"AR {invoice.invoice_number}",
            ),
            GLLine(
                account_code=self._cfg.revenue_account_code,
                debit=Decimal("0") if amt > 0 else _q2(-amt),
                credit=_q2(amt) if amt > 0 else Decimal("0"),
                currency=invoice.currency,
                memo=f"Revenue {invoice.invoice_number}",
            ),
        ]

        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=invoice.invoice_number,
            entry_date=invoice.issued_at.date(),
            description=f"Invoice {invoice.invoice_number}",
            lines=lines,
            metadata={"source": "ar", "invoice_id": str(invoice.id)},
        )
        self._ledger.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self._ledger.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)

    def _post_payment_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        payment: PaymentReceipt,
    ) -> None:
        if self._ledger is None:
            return

        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        roles = _norm_roles(actor_roles)

        lines = [
            GLLine(
                account_code=self._cfg.cash_account_code,
                debit=payment.amount,
                credit=Decimal("0"),
                currency=payment.currency,
                memo=f"Receipt {payment.reference or payment.id}",
            ),
            GLLine(
                account_code=self._cfg.ar_account_code,
                debit=Decimal("0"),
                credit=payment.amount,
                currency=payment.currency,
                memo=f"Receipt {payment.reference or payment.id}",
            ),
        ]

        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=f"RCPT-{str(payment.id)[:8]}",
            entry_date=payment.received_at.date(),
            description="Customer receipt",
            lines=lines,
            metadata={"source": "ar", "payment_id": str(payment.id)},
        )
        self._ledger.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self._ledger.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)

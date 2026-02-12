"""Accounts Payable (Procure-to-Pay) service.

Implements Development Plan Section 22.3:
- Purchase Requisitions (PR): request/submit/approve
- Purchase Orders (PO): create/approve/send/receive/close
- Supplier Invoices: capture/approve/post (optionally to GL)
- 3-Way Match: PO ↔ goods receipt ↔ supplier invoice
- Payments: payment run preparation/approval/execution tracking (optionally to GL)

State is persisted via the service_state table for DB-backed continuity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from collections.abc import Callable
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


def _norm_currency(c: str) -> str:
    cc = (c or "").strip().upper()
    if len(cc) != 3 or not cc.isalpha():
        raise ValueError("Invalid currency")
    return cc


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


def _encode_pr_line(line: "PRLine") -> dict[str, Any]:
    return {
        "sku": line.sku,
        "description": line.description,
        "quantity": _encode_decimal(line.quantity),
        "unit_price": _encode_decimal(line.unit_price),
    }


def _decode_pr_line(data: dict[str, Any]) -> "PRLine":
    return PRLine(
        sku=data.get("sku", ""),
        description=data.get("description", ""),
        quantity=Decimal(data.get("quantity", "0")),
        unit_price=Decimal(data.get("unit_price", "0")),
    )


def _encode_po_line(line: "POLine") -> dict[str, Any]:
    return {
        "sku": line.sku,
        "description": line.description,
        "quantity": _encode_decimal(line.quantity),
        "unit_price": _encode_decimal(line.unit_price),
    }


def _decode_po_line(data: dict[str, Any]) -> "POLine":
    return POLine(
        sku=data.get("sku", ""),
        description=data.get("description", ""),
        quantity=Decimal(data.get("quantity", "0")),
        unit_price=Decimal(data.get("unit_price", "0")),
    )


def _encode_receipt_line(line: "ReceiptLine") -> dict[str, Any]:
    return {
        "sku": line.sku,
        "quantity_received": _encode_decimal(line.quantity_received),
    }


def _decode_receipt_line(data: dict[str, Any]) -> "ReceiptLine":
    return ReceiptLine(
        sku=data.get("sku", ""),
        quantity_received=Decimal(data.get("quantity_received", "0")),
    )


def _encode_supplier_invoice_line(line: "SupplierInvoiceLine") -> dict[str, Any]:
    return {
        "sku": line.sku,
        "description": line.description,
        "quantity": _encode_decimal(line.quantity),
        "unit_price": _encode_decimal(line.unit_price),
    }


def _decode_supplier_invoice_line(data: dict[str, Any]) -> "SupplierInvoiceLine":
    return SupplierInvoiceLine(
        sku=data.get("sku", ""),
        description=data.get("description", ""),
        quantity=Decimal(data.get("quantity", "0")),
        unit_price=Decimal(data.get("unit_price", "0")),
    )


def _encode_requisition(req: "PurchaseRequisition") -> dict[str, Any]:
    return {
        "id": str(req.id),
        "pr_number": req.pr_number,
        "requested_by": req.requested_by,
        "created_at": req.created_at.isoformat(),
        "currency": req.currency,
        "supplier_id": req.supplier_id,
        "cost_center": req.cost_center,
        "status": req.status.value,
        "submitted_at": _encode_datetime(req.submitted_at),
        "submitted_by": req.submitted_by,
        "approved_at": _encode_datetime(req.approved_at),
        "approved_by": req.approved_by,
        "rejected_at": _encode_datetime(req.rejected_at),
        "rejected_by": req.rejected_by,
        "rejection_reason": req.rejection_reason,
        "lines": [_encode_pr_line(line) for line in req.lines],
        "metadata": req.metadata,
    }


def _decode_requisition(data: dict[str, Any]) -> "PurchaseRequisition":
    return PurchaseRequisition(
        id=UUID(data["id"]),
        pr_number=data.get("pr_number", ""),
        requested_by=data.get("requested_by", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        currency=data.get("currency", ""),
        supplier_id=data.get("supplier_id"),
        cost_center=data.get("cost_center"),
        status=PRStatus(data.get("status", PRStatus.DRAFT.value)),
        submitted_at=_decode_datetime(data.get("submitted_at")),
        submitted_by=data.get("submitted_by"),
        approved_at=_decode_datetime(data.get("approved_at")),
        approved_by=data.get("approved_by"),
        rejected_at=_decode_datetime(data.get("rejected_at")),
        rejected_by=data.get("rejected_by"),
        rejection_reason=data.get("rejection_reason"),
        lines=[_decode_pr_line(line) for line in data.get("lines", [])],
        metadata=data.get("metadata", {}) or {},
    )


def _encode_purchase_order(po: "PurchaseOrder") -> dict[str, Any]:
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "supplier_id": po.supplier_id,
        "created_at": po.created_at.isoformat(),
        "created_by": po.created_by,
        "currency": po.currency,
        "status": po.status.value,
        "source_pr_id": _encode_uuid(po.source_pr_id),
        "cost_center": po.cost_center,
        "approved_at": _encode_datetime(po.approved_at),
        "approved_by": po.approved_by,
        "sent_at": _encode_datetime(po.sent_at),
        "sent_by": po.sent_by,
        "lines": [_encode_po_line(line) for line in po.lines],
        "metadata": po.metadata,
    }


def _decode_purchase_order(data: dict[str, Any]) -> "PurchaseOrder":
    return PurchaseOrder(
        id=UUID(data["id"]),
        po_number=data.get("po_number", ""),
        supplier_id=data.get("supplier_id", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        currency=data.get("currency", ""),
        status=POStatus(data.get("status", POStatus.DRAFT.value)),
        source_pr_id=_decode_uuid(data.get("source_pr_id")),
        cost_center=data.get("cost_center"),
        approved_at=_decode_datetime(data.get("approved_at")),
        approved_by=data.get("approved_by"),
        sent_at=_decode_datetime(data.get("sent_at")),
        sent_by=data.get("sent_by"),
        lines=[_decode_po_line(line) for line in data.get("lines", [])],
        metadata=data.get("metadata", {}) or {},
    )


def _encode_goods_receipt(gr: "GoodsReceipt") -> dict[str, Any]:
    return {
        "id": str(gr.id),
        "po_id": str(gr.po_id),
        "received_at": gr.received_at.isoformat(),
        "received_by": gr.received_by,
        "lines": [_encode_receipt_line(line) for line in gr.lines],
        "reference": gr.reference,
    }


def _decode_goods_receipt(data: dict[str, Any]) -> "GoodsReceipt":
    return GoodsReceipt(
        id=UUID(data["id"]),
        po_id=UUID(data["po_id"]),
        received_at=datetime.fromisoformat(data["received_at"]),
        received_by=data.get("received_by", ""),
        lines=[_decode_receipt_line(line) for line in data.get("lines", [])],
        reference=data.get("reference"),
    )


def _encode_supplier_invoice(inv: "SupplierInvoice") -> dict[str, Any]:
    return {
        "id": str(inv.id),
        "supplier_invoice_number": inv.supplier_invoice_number,
        "supplier_id": inv.supplier_id,
        "invoice_date": inv.invoice_date.isoformat(),
        "due_date": inv.due_date.isoformat(),
        "currency": inv.currency,
        "created_at": inv.created_at.isoformat(),
        "created_by": inv.created_by,
        "status": inv.status.value,
        "po_id": _encode_uuid(inv.po_id),
        "memo": inv.memo,
        "approved_at": _encode_datetime(inv.approved_at),
        "approved_by": inv.approved_by,
        "posted_at": _encode_datetime(inv.posted_at),
        "posted_by": inv.posted_by,
        "paid_at": _encode_datetime(inv.paid_at),
        "paid_by": inv.paid_by,
        "lines": [_encode_supplier_invoice_line(line) for line in inv.lines],
        "metadata": inv.metadata,
    }


def _decode_supplier_invoice(data: dict[str, Any]) -> "SupplierInvoice":
    return SupplierInvoice(
        id=UUID(data["id"]),
        supplier_invoice_number=data.get("supplier_invoice_number", ""),
        supplier_id=data.get("supplier_id", ""),
        invoice_date=date.fromisoformat(data["invoice_date"]),
        due_date=date.fromisoformat(data["due_date"]),
        currency=data.get("currency", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        status=InvoiceStatus(data.get("status", InvoiceStatus.DRAFT.value)),
        po_id=_decode_uuid(data.get("po_id")),
        memo=data.get("memo"),
        approved_at=_decode_datetime(data.get("approved_at")),
        approved_by=data.get("approved_by"),
        posted_at=_decode_datetime(data.get("posted_at")),
        posted_by=data.get("posted_by"),
        paid_at=_decode_datetime(data.get("paid_at")),
        paid_by=data.get("paid_by"),
        lines=[_decode_supplier_invoice_line(line) for line in data.get("lines", [])],
        metadata=data.get("metadata", {}) or {},
    )


def _encode_payment(payment: "Payment") -> dict[str, Any]:
    return {
        "id": str(payment.id),
        "supplier_id": payment.supplier_id,
        "amount": _encode_decimal(payment.amount),
        "currency": payment.currency,
        "executed_at": payment.executed_at.isoformat(),
        "reference": payment.reference,
        "invoice_ids": [str(iid) for iid in payment.invoice_ids],
    }


def _decode_payment(data: dict[str, Any]) -> "Payment":
    return Payment(
        id=UUID(data["id"]),
        supplier_id=data.get("supplier_id", ""),
        amount=Decimal(data.get("amount", "0")),
        currency=data.get("currency", ""),
        executed_at=datetime.fromisoformat(data["executed_at"]),
        reference=data.get("reference"),
        invoice_ids=[UUID(iid) for iid in data.get("invoice_ids", [])],
    )


def _encode_payment_run(payrun: "PaymentRun") -> dict[str, Any]:
    return {
        "id": str(payrun.id),
        "run_number": payrun.run_number,
        "created_at": payrun.created_at.isoformat(),
        "created_by": payrun.created_by,
        "currency": payrun.currency,
        "status": payrun.status.value,
        "invoice_ids": [str(iid) for iid in payrun.invoice_ids],
        "approved_at": _encode_datetime(payrun.approved_at),
        "approved_by": payrun.approved_by,
        "executed_at": _encode_datetime(payrun.executed_at),
        "executed_by": payrun.executed_by,
        "payments": [_encode_payment(p) for p in payrun.payments],
    }


def _decode_payment_run(data: dict[str, Any]) -> "PaymentRun":
    return PaymentRun(
        id=UUID(data["id"]),
        run_number=data.get("run_number", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        created_by=data.get("created_by", ""),
        currency=data.get("currency", ""),
        status=PaymentRunStatus(data.get("status", PaymentRunStatus.DRAFT.value)),
        invoice_ids=[UUID(iid) for iid in data.get("invoice_ids", [])],
        approved_at=_decode_datetime(data.get("approved_at")),
        approved_by=data.get("approved_by"),
        executed_at=_decode_datetime(data.get("executed_at")),
        executed_by=data.get("executed_by"),
        payments=[_decode_payment(p) for p in data.get("payments", [])],
    )


def _encode_config(cfg: "APConfig") -> dict[str, Any]:
    return {
        "base_currency": cfg.base_currency,
        "pr_prefix": cfg.pr_prefix,
        "po_prefix": cfg.po_prefix,
        "payrun_prefix": cfg.payrun_prefix,
        "next_pr_seq": cfg.next_pr_seq,
        "next_po_seq": cfg.next_po_seq,
        "next_payrun_seq": cfg.next_payrun_seq,
        "cash_account_code": cfg.cash_account_code,
        "ap_account_code": cfg.ap_account_code,
        "expense_account_code": cfg.expense_account_code,
        "qty_tolerance_pct": _encode_decimal(cfg.qty_tolerance_pct),
        "price_tolerance_pct": _encode_decimal(cfg.price_tolerance_pct),
    }


def _decode_config(data: dict[str, Any], fallback: "APConfig") -> "APConfig":
    return APConfig(
        base_currency=data.get("base_currency", fallback.base_currency),
        pr_prefix=data.get("pr_prefix", fallback.pr_prefix),
        po_prefix=data.get("po_prefix", fallback.po_prefix),
        payrun_prefix=data.get("payrun_prefix", fallback.payrun_prefix),
        next_pr_seq=int(data.get("next_pr_seq", fallback.next_pr_seq)),
        next_po_seq=int(data.get("next_po_seq", fallback.next_po_seq)),
        next_payrun_seq=int(data.get("next_payrun_seq", fallback.next_payrun_seq)),
        cash_account_code=data.get("cash_account_code", fallback.cash_account_code),
        ap_account_code=data.get("ap_account_code", fallback.ap_account_code),
        expense_account_code=data.get("expense_account_code", fallback.expense_account_code),
        qty_tolerance_pct=Decimal(data.get("qty_tolerance_pct", str(fallback.qty_tolerance_pct))),
        price_tolerance_pct=Decimal(data.get("price_tolerance_pct", str(fallback.price_tolerance_pct))),
    )


_AP_READ_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "auditor",
    "buyer",
    "procurement",
}

_AP_WRITE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "buyer",
    "procurement",
}

_AP_APPROVE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
}


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


class PRStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"


class POStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELED = "canceled"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    POSTED = "posted"
    PAID = "paid"
    REJECTED = "rejected"
    VOID = "void"


class PaymentRunStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTED = "executed"
    CANCELED = "canceled"


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


@dataclass(frozen=True)
class PRLine:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _q2(self.quantity * self.unit_price)


@dataclass
class PurchaseRequisition:
    id: UUID
    pr_number: str
    requested_by: str
    created_at: datetime
    currency: str
    supplier_id: str | None = None
    cost_center: str | None = None
    status: PRStatus = PRStatus.DRAFT

    submitted_at: datetime | None = None
    submitted_by: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None
    rejection_reason: str | None = None

    lines: list[PRLine] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> Decimal:
        return _q2(sum((ln.line_total for ln in self.lines), Decimal("0")))


@dataclass(frozen=True)
class POLine:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _q2(self.quantity * self.unit_price)


@dataclass
class PurchaseOrder:
    id: UUID
    po_number: str
    supplier_id: str
    created_at: datetime
    created_by: str
    currency: str
    status: POStatus = POStatus.DRAFT

    source_pr_id: UUID | None = None
    cost_center: str | None = None

    approved_at: datetime | None = None
    approved_by: str | None = None
    sent_at: datetime | None = None
    sent_by: str | None = None

    lines: list[POLine] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> Decimal:
        return _q2(sum((ln.line_total for ln in self.lines), Decimal("0")))


@dataclass(frozen=True)
class ReceiptLine:
    sku: str
    quantity_received: Decimal


@dataclass
class GoodsReceipt:
    id: UUID
    po_id: UUID
    received_at: datetime
    received_by: str
    lines: list[ReceiptLine]
    reference: str | None = None


@dataclass(frozen=True)
class SupplierInvoiceLine:
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _q2(self.quantity * self.unit_price)


@dataclass
class SupplierInvoice:
    id: UUID
    supplier_invoice_number: str
    supplier_id: str
    invoice_date: date
    due_date: date
    currency: str
    created_at: datetime
    created_by: str

    status: InvoiceStatus = InvoiceStatus.DRAFT

    po_id: UUID | None = None
    memo: str | None = None

    approved_at: datetime | None = None
    approved_by: str | None = None

    posted_at: datetime | None = None
    posted_by: str | None = None

    paid_at: datetime | None = None
    paid_by: str | None = None

    lines: list[SupplierInvoiceLine] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> Decimal:
        return _q2(sum((ln.line_total for ln in self.lines), Decimal("0")))


@dataclass(frozen=True)
class MatchException:
    code: str
    message: str


@dataclass(frozen=True)
class ThreeWayMatchResult:
    ok: bool
    exceptions: list[MatchException]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Payment:
    id: UUID
    supplier_id: str
    amount: Decimal
    currency: str
    executed_at: datetime
    reference: str | None = None
    invoice_ids: list[UUID] = field(default_factory=list)


@dataclass
class PaymentRun:
    id: UUID
    run_number: str
    created_at: datetime
    created_by: str
    currency: str
    status: PaymentRunStatus = PaymentRunStatus.DRAFT

    invoice_ids: list[UUID] = field(default_factory=list)
    approved_at: datetime | None = None
    approved_by: str | None = None

    executed_at: datetime | None = None
    executed_by: str | None = None
    payments: list[Payment] = field(default_factory=list)


@dataclass
class APConfig:
    base_currency: str = "EUR"

    pr_prefix: str = "PR"
    po_prefix: str = "PO"
    payrun_prefix: str = "PAY"
    next_pr_seq: int = 1
    next_po_seq: int = 1
    next_payrun_seq: int = 1

    # GL integration
    cash_account_code: str = "1000"  # Cash/Bank
    ap_account_code: str = "2000"  # Accounts Payable
    expense_account_code: str = "5000"  # Expenses

    # 3-way match tolerances
    qty_tolerance_pct: Decimal = Decimal("0")
    price_tolerance_pct: Decimal = Decimal("0")


class AccountsPayableService(PersistentServiceMixin):
    """Procure-to-Pay workflows with optional GL postings.

    In-memory state backed by PostgreSQL ap_invoices, ap_payments,
    purchase_orders, purchase_requisitions, and goods_receipts tables.
    """

    SERVICE_NAME = "accounts_payable"

    def __init__(
        self,
        *,
        config: APConfig | None = None,
        ledger: Any | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self._cfg = config or APConfig()
        self._ledger = ledger
        self._now_fn: Callable[[], datetime] = now_fn or _now

        self._prs: dict[UUID, PurchaseRequisition] = {}
        self._pos: dict[UUID, PurchaseOrder] = {}
        self._receipts: dict[UUID, GoodsReceipt] = {}
        self._invoices: dict[UUID, SupplierInvoice] = {}
        self._payruns: dict[UUID, PaymentRun] = {}

        self._audit: list[AuditEvent] = []
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        cfg_data = await self.load_state(_DEFAULT_TENANT_ID, "config") or {}
        prs_data = await self.load_state(_DEFAULT_TENANT_ID, "prs") or {}
        pos_data = await self.load_state(_DEFAULT_TENANT_ID, "pos") or {}
        receipts_data = await self.load_state(_DEFAULT_TENANT_ID, "receipts") or {}
        invoices_data = await self.load_state(_DEFAULT_TENANT_ID, "invoices") or {}
        payruns_data = await self.load_state(_DEFAULT_TENANT_ID, "payruns") or {}
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []

        if cfg_data:
            self._cfg = _decode_config(cfg_data, self._cfg)

        self._prs = {UUID(pid): _decode_requisition(p) for pid, p in prs_data.items()}
        self._pos = {UUID(pid): _decode_purchase_order(p) for pid, p in pos_data.items()}
        self._receipts = {UUID(rid): _decode_goods_receipt(r) for rid, r in receipts_data.items()}
        self._invoices = {UUID(iid): _decode_supplier_invoice(i) for iid, i in invoices_data.items()}
        self._payruns = {UUID(pid): _decode_payment_run(p) for pid, p in payruns_data.items()}
        self._audit = [_decode_audit_event(a) for a in audit_data]

        self._state_loaded = True

    async def persist_all(self) -> None:
        cfg_data = _encode_config(self._cfg)
        prs_data = {str(pid): _encode_requisition(pr) for pid, pr in self._prs.items()}
        pos_data = {str(pid): _encode_purchase_order(po) for pid, po in self._pos.items()}
        receipts_data = {str(rid): _encode_goods_receipt(gr) for rid, gr in self._receipts.items()}
        invoices_data = {str(iid): _encode_supplier_invoice(inv) for iid, inv in self._invoices.items()}
        payruns_data = {str(pid): _encode_payment_run(pr) for pid, pr in self._payruns.items()}
        audit_data = [_encode_audit_event(a) for a in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "config", cfg_data)
        await self.save_state(_DEFAULT_TENANT_ID, "prs", prs_data)
        await self.save_state(_DEFAULT_TENANT_ID, "pos", pos_data)
        await self.save_state(_DEFAULT_TENANT_ID, "receipts", receipts_data)
        await self.save_state(_DEFAULT_TENANT_ID, "invoices", invoices_data)
        await self.save_state(_DEFAULT_TENANT_ID, "payruns", payruns_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    async def list_audit_events_async(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(actor_roles=actor_roles)

    async def create_requisition_async(self, **kwargs: Any) -> PurchaseRequisition:
        await self._ensure_loaded()
        pr = self.create_requisition(**kwargs)
        await self.persist_all()
        return pr

    async def submit_requisition_async(self, **kwargs: Any) -> PurchaseRequisition:
        await self._ensure_loaded()
        pr = self.submit_requisition(**kwargs)
        await self.persist_all()
        return pr

    async def approve_requisition_async(self, **kwargs: Any) -> PurchaseRequisition:
        await self._ensure_loaded()
        pr = self.approve_requisition(**kwargs)
        await self.persist_all()
        return pr

    async def reject_requisition_async(self, **kwargs: Any) -> PurchaseRequisition:
        await self._ensure_loaded()
        pr = self.reject_requisition(**kwargs)
        await self.persist_all()
        return pr

    async def get_requisition_async(self, *, actor_roles: Iterable[str], pr_id: UUID) -> PurchaseRequisition | None:
        await self._ensure_loaded()
        return self.get_requisition(actor_roles=actor_roles, pr_id=pr_id)

    async def create_po_from_requisition_async(self, **kwargs: Any) -> PurchaseOrder:
        await self._ensure_loaded()
        po = self.create_po_from_requisition(**kwargs)
        await self.persist_all()
        return po

    async def approve_po_async(self, **kwargs: Any) -> PurchaseOrder:
        await self._ensure_loaded()
        po = self.approve_po(**kwargs)
        await self.persist_all()
        return po

    async def send_po_async(self, **kwargs: Any) -> PurchaseOrder:
        await self._ensure_loaded()
        po = self.send_po(**kwargs)
        await self.persist_all()
        return po

    async def receive_goods_async(self, **kwargs: Any) -> GoodsReceipt:
        await self._ensure_loaded()
        gr = self.receive_goods(**kwargs)
        await self.persist_all()
        return gr

    async def close_po_async(self, **kwargs: Any) -> PurchaseOrder:
        await self._ensure_loaded()
        po = self.close_po(**kwargs)
        await self.persist_all()
        return po

    async def get_po_async(self, *, actor_roles: Iterable[str], po_id: UUID) -> PurchaseOrder | None:
        await self._ensure_loaded()
        return self.get_po(actor_roles=actor_roles, po_id=po_id)

    async def create_supplier_invoice_async(self, **kwargs: Any) -> SupplierInvoice:
        await self._ensure_loaded()
        inv = self.create_supplier_invoice(**kwargs)
        await self.persist_all()
        return inv

    async def submit_supplier_invoice_async(self, **kwargs: Any) -> SupplierInvoice:
        await self._ensure_loaded()
        inv = self.submit_supplier_invoice(**kwargs)
        await self.persist_all()
        return inv

    async def three_way_match_async(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> ThreeWayMatchResult:
        await self._ensure_loaded()
        return self.three_way_match(actor_roles=actor_roles, invoice_id=invoice_id)

    async def approve_supplier_invoice_async(self, **kwargs: Any) -> SupplierInvoice:
        await self._ensure_loaded()
        inv = self.approve_supplier_invoice(**kwargs)
        await self.persist_all()
        return inv

    async def post_supplier_invoice_async(self, **kwargs: Any) -> SupplierInvoice:
        await self._ensure_loaded()
        inv = self.post_supplier_invoice(**kwargs)
        await self.persist_all()
        return inv

    async def get_supplier_invoice_async(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> SupplierInvoice | None:
        await self._ensure_loaded()
        return self.get_supplier_invoice(actor_roles=actor_roles, invoice_id=invoice_id)

    async def create_payment_run_async(self, **kwargs: Any) -> PaymentRun:
        await self._ensure_loaded()
        pr = self.create_payment_run(**kwargs)
        await self.persist_all()
        return pr

    async def approve_payment_run_async(self, **kwargs: Any) -> PaymentRun:
        await self._ensure_loaded()
        pr = self.approve_payment_run(**kwargs)
        await self.persist_all()
        return pr

    async def execute_payment_run_async(self, **kwargs: Any) -> PaymentRun:
        await self._ensure_loaded()
        pr = self.execute_payment_run(**kwargs)
        await self.persist_all()
        return pr

    async def get_payment_run_async(self, *, actor_roles: Iterable[str], payrun_id: UUID) -> PaymentRun | None:
        await self._ensure_loaded()
        return self.get_payment_run(actor_roles=actor_roles, payrun_id=payrun_id)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_READ_ROLES, "AP read role required")
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
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")
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
    # Purchase Requisitions
    # ------------------------------------------------------------------

    def create_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        requested_by: str,
        currency: str,
        supplier_id: str | None,
        cost_center: str | None,
        lines: list[PRLine],
    ) -> PurchaseRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")
        if not lines:
            raise ValueError("PR must have at least one line")

        pr_number = f"{self._cfg.pr_prefix}-{self._cfg.next_pr_seq:06d}"
        self._cfg.next_pr_seq += 1

        pr = PurchaseRequisition(
            id=uuid4(),
            pr_number=pr_number,
            requested_by=str(requested_by),
            created_at=_now(),
            currency=_norm_currency(currency or self._cfg.base_currency),
            supplier_id=str(supplier_id) if supplier_id else None,
            cost_center=str(cost_center) if cost_center else None,
            lines=list(lines),
        )
        self._prs[pr.id] = pr
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.pr.create",
            entity_type="pr",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
            metadata={"pr_number": pr.pr_number},
        )
        return pr

    def submit_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        pr_id: UUID,
    ) -> PurchaseRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")

        pr = self._prs.get(pr_id)
        if pr is None:
            raise ValueError("Unknown PR")
        if pr.status not in {PRStatus.DRAFT, PRStatus.SUBMITTED}:
            raise ValueError("PR cannot be submitted in current status")

        pr.status = PRStatus.SUBMITTED
        pr.submitted_at = _now()
        pr.submitted_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.pr.submit",
            entity_type="pr",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
        )
        return pr

    def approve_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        pr_id: UUID,
    ) -> PurchaseRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        pr = self._prs.get(pr_id)
        if pr is None:
            raise ValueError("Unknown PR")
        if pr.status not in {PRStatus.SUBMITTED, PRStatus.APPROVED}:
            raise ValueError("PR must be submitted before approval")

        # Segregation of Duties: approver must differ from requester
        if pr.requested_by == actor_id:
            raise ValueError(
                "Segregation of duties violation: requester cannot approve their own PR"
            )

        pr.status = PRStatus.APPROVED
        pr.approved_at = _now()
        pr.approved_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.pr.approve",
            entity_type="pr",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
        )
        return pr

    def reject_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        pr_id: UUID,
        reason: str,
    ) -> PurchaseRequisition:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        pr = self._prs.get(pr_id)
        if pr is None:
            raise ValueError("Unknown PR")
        if pr.status not in {PRStatus.SUBMITTED, PRStatus.REJECTED}:
            raise ValueError("PR must be submitted before rejection")
        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")

        pr.status = PRStatus.REJECTED
        pr.rejected_at = _now()
        pr.rejected_by = actor_id
        pr.rejection_reason = r
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.pr.reject",
            entity_type="pr",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
            metadata={"reason": r},
        )
        return pr

    def get_requisition(self, *, actor_roles: Iterable[str], pr_id: UUID) -> PurchaseRequisition | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_READ_ROLES, "AP read role required")
        return self._prs.get(pr_id)

    # ------------------------------------------------------------------
    # Purchase Orders
    # ------------------------------------------------------------------

    def create_po_from_requisition(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        pr_id: UUID,
        supplier_id: str | None = None,
    ) -> PurchaseOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")

        pr = self._prs.get(pr_id)
        if pr is None:
            raise ValueError("Unknown PR")
        if pr.status != PRStatus.APPROVED:
            raise ValueError("PR must be approved before PO creation")

        supp = supplier_id or pr.supplier_id
        if not supp:
            raise ValueError("supplier_id required")

        po_number = f"{self._cfg.po_prefix}-{self._cfg.next_po_seq:06d}"
        self._cfg.next_po_seq += 1

        po = PurchaseOrder(
            id=uuid4(),
            po_number=po_number,
            supplier_id=str(supp),
            created_at=_now(),
            created_by=actor_id,
            currency=pr.currency,
            source_pr_id=pr.id,
            cost_center=pr.cost_center,
            lines=[POLine(sku=l.sku, description=l.description, quantity=l.quantity, unit_price=l.unit_price) for l in pr.lines],
        )
        self._pos[po.id] = po
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.po.create_from_pr",
            entity_type="po",
            entity_id=str(po.id),
            correlation_id=correlation_id,
            metadata={"po_number": po.po_number, "pr_id": str(pr.id)},
        )
        return po

    def approve_po(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        po_id: UUID,
    ) -> PurchaseOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        po = self._pos.get(po_id)
        if po is None:
            raise ValueError("Unknown PO")
        if po.status not in {POStatus.DRAFT, POStatus.APPROVED}:
            raise ValueError("PO cannot be approved in current status")

        # Segregation of Duties: approver must differ from creator
        if po.created_by == actor_id:
            raise ValueError(
                "Segregation of duties violation: creator cannot approve their own PO"
            )

        po.status = POStatus.APPROVED
        po.approved_at = _now()
        po.approved_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.po.approve",
            entity_type="po",
            entity_id=str(po.id),
            correlation_id=correlation_id,
        )
        return po

    def send_po(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        po_id: UUID,
    ) -> PurchaseOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")

        po = self._pos.get(po_id)
        if po is None:
            raise ValueError("Unknown PO")
        if po.status not in {POStatus.APPROVED, POStatus.SENT}:
            raise ValueError("PO must be approved before sending")

        po.status = POStatus.SENT
        po.sent_at = _now()
        po.sent_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.po.send",
            entity_type="po",
            entity_id=str(po.id),
            correlation_id=correlation_id,
        )
        return po

    def _received_qty_for_po(self, po_id: UUID) -> dict[str, Decimal]:
        sums: dict[str, Decimal] = {}
        for gr in self._receipts.values():
            if gr.po_id != po_id:
                continue
            for ln in gr.lines:
                sums[ln.sku] = sums.get(ln.sku, Decimal("0")) + ln.quantity_received
        return sums

    def receive_goods(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        po_id: UUID,
        lines: list[ReceiptLine],
        received_at: datetime | None = None,
        reference: str | None = None,
    ) -> GoodsReceipt:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")
        if not lines:
            raise ValueError("Receipt must have lines")

        po = self._pos.get(po_id)
        if po is None:
            raise ValueError("Unknown PO")
        if po.status not in {POStatus.SENT, POStatus.PARTIALLY_RECEIVED, POStatus.RECEIVED}:
            raise ValueError("PO must be sent before receiving")

        sku_to_po_qty = {ln.sku: ln.quantity for ln in po.lines}
        for ln in lines:
            if ln.sku not in sku_to_po_qty:
                raise ValueError(f"Unknown SKU on receipt: {ln.sku}")
            if ln.quantity_received <= 0:
                raise ValueError("quantity_received must be > 0")

        gr = GoodsReceipt(
            id=uuid4(),
            po_id=po.id,
            received_at=received_at or _now(),
            received_by=actor_id,
            lines=list(lines),
            reference=reference,
        )
        self._receipts[gr.id] = gr

        received = self._received_qty_for_po(po.id)
        fully = True
        any_received = False
        for sku, po_qty in sku_to_po_qty.items():
            rcv = received.get(sku, Decimal("0"))
            if rcv > 0:
                any_received = True
            if rcv < po_qty:
                fully = False

        if fully:
            po.status = POStatus.RECEIVED
        elif any_received:
            po.status = POStatus.PARTIALLY_RECEIVED

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.po.receive",
            entity_type="goods_receipt",
            entity_id=str(gr.id),
            correlation_id=correlation_id,
            metadata={"po_id": str(po.id)},
        )
        return gr

    def close_po(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        po_id: UUID,
        reason: str | None = None,
    ) -> PurchaseOrder:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        po = self._pos.get(po_id)
        if po is None:
            raise ValueError("Unknown PO")
        if po.status not in {POStatus.RECEIVED, POStatus.CLOSED}:
            raise ValueError("PO must be received before close")

        po.status = POStatus.CLOSED
        po.metadata["close_reason"] = (reason or "").strip() or None
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.po.close",
            entity_type="po",
            entity_id=str(po.id),
            correlation_id=correlation_id,
        )
        return po

    def get_po(self, *, actor_roles: Iterable[str], po_id: UUID) -> PurchaseOrder | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_READ_ROLES, "AP read role required")
        return self._pos.get(po_id)

    # ------------------------------------------------------------------
    # Supplier invoices + 3-way match
    # ------------------------------------------------------------------

    def create_supplier_invoice(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        supplier_id: str,
        supplier_invoice_number: str,
        invoice_date: date,
        currency: str,
        due_date: date | None,
        po_id: UUID | None,
        lines: list[SupplierInvoiceLine],
        memo: str | None = None,
    ) -> SupplierInvoice:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")

        if not supplier_invoice_number.strip():
            raise ValueError("supplier_invoice_number required")
        if not lines:
            raise ValueError("Supplier invoice must have lines")

        cur = _norm_currency(currency or self._cfg.base_currency)
        dd = due_date or (invoice_date + timedelta(days=30))

        if po_id is not None and po_id not in self._pos:
            raise ValueError("Unknown PO")

        inv = SupplierInvoice(
            id=uuid4(),
            supplier_invoice_number=supplier_invoice_number.strip(),
            supplier_id=str(supplier_id),
            invoice_date=invoice_date,
            due_date=dd,
            currency=cur,
            created_at=_now(),
            created_by=actor_id,
            po_id=po_id,
            memo=memo,
            lines=list(lines),
        )
        self._invoices[inv.id] = inv
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.invoice.create",
            entity_type="supplier_invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
            metadata={"supplier_invoice_number": inv.supplier_invoice_number},
        )
        return inv

    def submit_supplier_invoice(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        invoice_id: UUID,
    ) -> SupplierInvoice:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")

        inv = self._invoices.get(invoice_id)
        if inv is None:
            raise ValueError("Unknown invoice")
        if inv.status not in {InvoiceStatus.DRAFT, InvoiceStatus.SUBMITTED}:
            raise ValueError("Invoice cannot be submitted in current status")

        inv.status = InvoiceStatus.SUBMITTED
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.invoice.submit",
            entity_type="supplier_invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
        )
        return inv

    def three_way_match(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> ThreeWayMatchResult:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_READ_ROLES, "AP read role required")

        inv = self._invoices.get(invoice_id)
        if inv is None:
            raise ValueError("Unknown invoice")
        if inv.po_id is None:
            # No PO → no 3-way match required
            return ThreeWayMatchResult(ok=True, exceptions=[], details={"po_required": False})

        po = self._pos.get(inv.po_id)
        if po is None:
            raise ValueError("Unknown PO")

        po_qty = {ln.sku: ln.quantity for ln in po.lines}
        po_price = {ln.sku: ln.unit_price for ln in po.lines}

        received_qty = self._received_qty_for_po(po.id)

        tol_qty = self._cfg.qty_tolerance_pct
        tol_price = self._cfg.price_tolerance_pct

        exceptions: list[MatchException] = []
        details: dict[str, Any] = {"po_id": str(po.id), "po_number": po.po_number, "line_checks": []}

        for il in inv.lines:
            if il.sku not in po_qty:
                exceptions.append(MatchException(code="SKU_NOT_ON_PO", message=f"Invoice SKU {il.sku} not on PO"))
                continue

            poq = po_qty[il.sku]
            rcv = received_qty.get(il.sku, Decimal("0"))

            # quantity: invoice qty should be <= received qty (with tolerance)
            allowed_qty = rcv * (Decimal("1") + (tol_qty / Decimal("100")))
            if il.quantity > allowed_qty:
                exceptions.append(
                    MatchException(
                        code="QTY_GT_RECEIPT",
                        message=f"Invoice qty {il.quantity} for {il.sku} exceeds received {rcv}",
                    )
                )

            # price: invoice unit price should be <= PO price (with tolerance)
            pop = po_price[il.sku]
            allowed_price = pop * (Decimal("1") + (tol_price / Decimal("100")))
            if il.unit_price > allowed_price:
                exceptions.append(
                    MatchException(
                        code="PRICE_GT_PO",
                        message=f"Invoice price {il.unit_price} for {il.sku} exceeds PO price {pop}",
                    )
                )

            details["line_checks"].append(
                {
                    "sku": il.sku,
                    "po_qty": str(poq),
                    "received_qty": str(rcv),
                    "invoice_qty": str(il.quantity),
                    "po_price": str(pop),
                    "invoice_price": str(il.unit_price),
                }
            )

        return ThreeWayMatchResult(ok=len(exceptions) == 0, exceptions=exceptions, details=details)

    def approve_supplier_invoice(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        invoice_id: UUID,
        allow_exceptions: bool = False,
        exception_override_reason: str | None = None,
    ) -> SupplierInvoice:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        inv = self._invoices.get(invoice_id)
        if inv is None:
            raise ValueError("Unknown invoice")
        if inv.status not in {InvoiceStatus.SUBMITTED, InvoiceStatus.APPROVED}:
            raise ValueError("Invoice must be submitted before approval")

        # Segregation of Duties: approver must differ from creator
        if inv.created_by == actor_id:
            raise ValueError(
                "Segregation of duties violation: creator cannot approve their own invoice"
            )

        match = self.three_way_match(actor_roles=roles, invoice_id=inv.id)
        if not match.ok and not allow_exceptions:
            raise ValueError("3-way match failed")
        if not match.ok and allow_exceptions:
            reason = (exception_override_reason or "").strip()
            if not reason:
                raise ValueError("exception_override_reason required")
            inv.metadata["three_way_match_override"] = True
            inv.metadata["three_way_match_override_reason"] = reason
            inv.metadata["three_way_match_exceptions"] = [e.code for e in match.exceptions]
            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="ap.invoice.3way_override",
                entity_type="supplier_invoice",
                entity_id=str(inv.id),
                correlation_id=correlation_id,
                metadata={"reason": reason, "exceptions": [e.code for e in match.exceptions]},
            )

        inv.status = InvoiceStatus.APPROVED
        inv.approved_at = _now()
        inv.approved_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.invoice.approve",
            entity_type="supplier_invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
        )
        return inv

    def post_supplier_invoice(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        invoice_id: UUID,
    ) -> SupplierInvoice:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        inv = self._invoices.get(invoice_id)
        if inv is None:
            raise ValueError("Unknown invoice")
        if inv.status not in {InvoiceStatus.APPROVED, InvoiceStatus.POSTED}:
            raise ValueError("Invoice must be approved before posting")

        if inv.status == InvoiceStatus.POSTED:
            return inv

        inv.status = InvoiceStatus.POSTED
        inv.posted_at = _now()
        inv.posted_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.invoice.post",
            entity_type="supplier_invoice",
            entity_id=str(inv.id),
            correlation_id=correlation_id,
        )

        self._post_invoice_to_gl(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, invoice=inv)
        return inv

    def get_supplier_invoice(self, *, actor_roles: Iterable[str], invoice_id: UUID) -> SupplierInvoice | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_READ_ROLES, "AP read role required")
        return self._invoices.get(invoice_id)

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def create_payment_run(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        invoice_ids: list[UUID],
        currency: str,
    ) -> PaymentRun:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_WRITE_ROLES, "AP write role required")

        if not invoice_ids:
            raise ValueError("invoice_ids required")
        cur = _norm_currency(currency or self._cfg.base_currency)

        # Validate invoice eligibility
        for iid in invoice_ids:
            inv = self._invoices.get(iid)
            if inv is None:
                raise ValueError("Unknown invoice")
            if inv.currency != cur:
                raise ValueError("All invoices must share currency")
            if inv.status not in {InvoiceStatus.POSTED, InvoiceStatus.PAID}:
                raise ValueError("Invoices must be posted before payment")
            if inv.status == InvoiceStatus.PAID:
                raise ValueError("Invoice already paid")

        run_number = f"{self._cfg.payrun_prefix}-{self._cfg.next_payrun_seq:06d}"
        self._cfg.next_payrun_seq += 1

        pr = PaymentRun(
            id=uuid4(),
            run_number=run_number,
            created_at=_now(),
            created_by=actor_id,
            currency=cur,
            invoice_ids=list(invoice_ids),
        )
        self._payruns[pr.id] = pr
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.payrun.create",
            entity_type="payment_run",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
            metadata={"run_number": pr.run_number},
        )
        return pr

    def approve_payment_run(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        payrun_id: UUID,
    ) -> PaymentRun:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        pr = self._payruns.get(payrun_id)
        if pr is None:
            raise ValueError("Unknown payment run")
        if pr.status not in {PaymentRunStatus.DRAFT, PaymentRunStatus.APPROVED}:
            raise ValueError("Payment run cannot be approved in current status")

        # Segregation of Duties: approver must differ from creator
        if pr.created_by == actor_id:
            raise ValueError(
                "Segregation of duties violation: creator cannot approve their own payment run"
            )

        pr.status = PaymentRunStatus.APPROVED
        pr.approved_at = _now()
        pr.approved_by = actor_id
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.payrun.approve",
            entity_type="payment_run",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
        )
        return pr

    def execute_payment_run(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        payrun_id: UUID,
        reference: str | None = None,
    ) -> PaymentRun:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_APPROVE_ROLES, "AP approve role required")

        pr = self._payruns.get(payrun_id)
        if pr is None:
            raise ValueError("Unknown payment run")
        if pr.status not in {PaymentRunStatus.APPROVED, PaymentRunStatus.EXECUTED}:
            raise ValueError("Payment run must be approved before execution")
        if pr.status == PaymentRunStatus.EXECUTED:
            return pr

        # Group by supplier
        by_supplier: dict[str, list[SupplierInvoice]] = {}
        for iid in pr.invoice_ids:
            inv = self._invoices.get(iid)
            if inv is None:
                raise ValueError("Unknown invoice")
            if inv.status != InvoiceStatus.POSTED:
                raise ValueError("Invoice must be posted and unpaid")
            by_supplier.setdefault(inv.supplier_id, []).append(inv)

        payments: list[Payment] = []
        executed_at = self._now_fn()
        for supplier_id, invoices in by_supplier.items():
            amt = _q2(sum((i.total for i in invoices), Decimal("0")))
            pay = Payment(
                id=uuid4(),
                supplier_id=supplier_id,
                amount=amt,
                currency=pr.currency,
                executed_at=executed_at,
                reference=reference,
                invoice_ids=[i.id for i in invoices],
            )
            payments.append(pay)

            for inv in invoices:
                inv.status = InvoiceStatus.PAID
                inv.paid_at = executed_at
                inv.paid_by = actor_id

        pr.payments = payments
        pr.status = PaymentRunStatus.EXECUTED
        pr.executed_at = executed_at
        pr.executed_by = actor_id

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="ap.payrun.execute",
            entity_type="payment_run",
            entity_id=str(pr.id),
            correlation_id=correlation_id,
            metadata={"payment_count": len(payments)},
        )

        self._post_payment_run_to_gl(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, payrun=pr)
        return pr

    def get_payment_run(self, *, actor_roles: Iterable[str], payrun_id: UUID) -> PaymentRun | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _AP_READ_ROLES, "AP read role required")
        return self._payruns.get(payrun_id)

    # ------------------------------------------------------------------
    # GL integration
    # ------------------------------------------------------------------

    def _post_invoice_to_gl(self, *, actor_id: str, actor_roles: Iterable[str], correlation_id: str, invoice: SupplierInvoice) -> None:
        if self._ledger is None:
            return

        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        roles = _norm_roles(actor_roles)

        lines = [
            GLLine(
                account_code=self._cfg.expense_account_code,
                debit=invoice.total,
                credit=Decimal("0"),
                currency=invoice.currency,
                memo=f"Expense {invoice.supplier_invoice_number}",
            ),
            GLLine(
                account_code=self._cfg.ap_account_code,
                debit=Decimal("0"),
                credit=invoice.total,
                currency=invoice.currency,
                memo=f"AP {invoice.supplier_invoice_number}",
            ),
        ]

        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=invoice.supplier_invoice_number,
            entry_date=invoice.invoice_date,
            description=f"Supplier invoice {invoice.supplier_invoice_number}",
            lines=lines,
            metadata={"source": "ap", "supplier_invoice_id": str(invoice.id)},
        )
        self._ledger.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self._ledger.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)

    def _post_payment_run_to_gl(self, *, actor_id: str, actor_roles: Iterable[str], correlation_id: str, payrun: PaymentRun) -> None:
        if self._ledger is None:
            return

        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        roles = _norm_roles(actor_roles)

        total = _q2(sum((p.amount for p in payrun.payments), Decimal("0")))
        if total <= 0:
            return

        lines = [
            GLLine(
                account_code=self._cfg.ap_account_code,
                debit=total,
                credit=Decimal("0"),
                currency=payrun.currency,
                memo=f"AP payments {payrun.run_number}",
            ),
            GLLine(
                account_code=self._cfg.cash_account_code,
                debit=Decimal("0"),
                credit=total,
                currency=payrun.currency,
                memo=f"Cash payments {payrun.run_number}",
            ),
        ]

        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=payrun.run_number,
            entry_date=payrun.executed_at.date() if payrun.executed_at else date.today(),
            description=f"Payment run {payrun.run_number}",
            lines=lines,
            metadata={"source": "ap", "payrun_id": str(payrun.id)},
        )
        self._ledger.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self._ledger.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)

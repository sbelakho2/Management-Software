"""Accounts Payable (Procure-to-Pay) service.

Implements Development Plan Section 22.3:
- Purchase Requisitions (PR): request/submit/approve
- Purchase Orders (PO): create/approve/send/receive/close
- Supplier Invoices: capture/approve/post (optionally to GL)
- 3-Way Match: PO ↔ goods receipt ↔ supplier invoice
- Payments: payment run preparation/approval/execution tracking (optionally to GL)

Pure-Python and in-memory, consistent with existing service patterns.
Persistence + APIs are planned later in 22.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


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


class AccountsPayableService:
    """Procure-to-Pay workflows with optional GL postings."""

    def __init__(self, *, config: APConfig | None = None, ledger: Any | None = None):
        self._cfg = config or APConfig()
        self._ledger = ledger

        self._prs: dict[UUID, PurchaseRequisition] = {}
        self._pos: dict[UUID, PurchaseOrder] = {}
        self._receipts: dict[UUID, GoodsReceipt] = {}
        self._invoices: dict[UUID, SupplierInvoice] = {}
        self._payruns: dict[UUID, PaymentRun] = {}

        self._audit: list[AuditEvent] = []

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
        executed_at = _now()
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

        from sensei.services.accounting_ledger import JournalLine as GLLine

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

        from sensei.services.accounting_ledger import JournalLine as GLLine

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

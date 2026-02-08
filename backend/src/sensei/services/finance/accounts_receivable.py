"""Accounts Receivable (Order-to-Cash) service.

Implements Development Plan Section 22.2:
- Quote → Sales Order
- Invoicing + credit memos
- Receipts + allocation
- A/R aging + dunning + disputes
- Customer credit controls

This module is pure-Python and in-memory, matching existing service patterns.
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

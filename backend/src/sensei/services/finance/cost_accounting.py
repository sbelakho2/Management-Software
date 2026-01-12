"""Inventory valuation & cost accounting.

Implements Development Plan Section 22.4:
- Costing Methods: standard cost (minimum)
- WIP Valuation: rollup by Work Order using material issues + labor bookings (+ optional routing standards)
- Variance Accounting: material/labor/overhead variances posted to GL with drill-down
- COGS & Margin: per-product/per-customer margin from shipments/invoices + cost rollups

This module is pure-Python and in-memory (persistence planned in 22.10).
Optionally integrates with `AccountingLedgerService` for postings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from collections.abc import Callable
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


_FINANCE_READ_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "auditor",
}

_COST_WRITE_ROLES: set[str] = _FINANCE_READ_ROLES.union({"ops", "production", "planner"})

_FINANCE_APPROVE_ROLES: set[str] = {
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


class CostMethod(str, Enum):
    STANDARD = "standard"


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
class StandardCost:
    sku: str
    currency: str
    effective_date: date
    material_unit_cost: Decimal
    labor_unit_cost: Decimal
    overhead_unit_cost: Decimal

    @property
    def total_unit_cost(self) -> Decimal:
        return _q2(self.material_unit_cost + self.labor_unit_cost + self.overhead_unit_cost)


@dataclass(frozen=True)
class MaterialIssue:
    id: UUID
    work_order_id: str
    sku: str
    quantity: Decimal
    unit_cost: Decimal
    issued_at: datetime
    issued_by: str

    @property
    def extended_cost(self) -> Decimal:
        return _q2(self.quantity * self.unit_cost)


@dataclass(frozen=True)
class DirectLaborBooking:
    id: UUID
    work_order_id: str
    operation_id: str | None
    hours: Decimal
    hourly_rate: Decimal
    booked_at: datetime
    booked_by: str

    @property
    def extended_cost(self) -> Decimal:
        return _q2(self.hours * self.hourly_rate)


@dataclass(frozen=True)
class OverheadBooking:
    id: UUID
    work_order_id: str
    amount: Decimal
    booked_at: datetime
    booked_by: str


@dataclass(frozen=True)
class CompletionReceipt:
    id: UUID
    work_order_id: str
    finished_sku: str
    quantity_completed: Decimal
    received_at: datetime
    received_by: str


@dataclass(frozen=True)
class Shipment:
    id: UUID
    customer_id: str
    sku: str
    quantity_shipped: Decimal
    revenue_total: Decimal
    currency: str
    shipped_at: datetime
    reference: str | None = None  # e.g., invoice number


@dataclass
class WorkOrderCostState:
    work_order_id: str
    finished_sku: str
    currency: str
    planned_quantity: Decimal

    completed_quantity: Decimal = Decimal("0")

    actual_material_cost: Decimal = Decimal("0")
    actual_labor_cost: Decimal = Decimal("0")
    actual_overhead_cost: Decimal = Decimal("0")

    relieved_actual_cost: Decimal = Decimal("0")

    @property
    def actual_total_cost(self) -> Decimal:
        return _q2(self.actual_material_cost + self.actual_labor_cost + self.actual_overhead_cost)

    @property
    def wip_actual_cost(self) -> Decimal:
        return _q2(self.actual_total_cost - self.relieved_actual_cost)


@dataclass(frozen=True)
class VarianceBreakdown:
    material: Decimal
    labor: Decimal
    overhead: Decimal

    @property
    def total(self) -> Decimal:
        return _q2(self.material + self.labor + self.overhead)


@dataclass(frozen=True)
class WIPValuationRow:
    work_order_id: str
    finished_sku: str
    planned_quantity: Decimal
    completed_quantity: Decimal
    wip_actual_cost: Decimal


@dataclass(frozen=True)
class MarginRow:
    customer_id: str
    sku: str
    revenue: Decimal
    cogs: Decimal

    @property
    def margin(self) -> Decimal:
        return _q2(self.revenue - self.cogs)


@dataclass
class CostAccountingConfig:
    base_currency: str = "EUR"
    method: CostMethod = CostMethod.STANDARD

    # GL accounts
    wip_account_code: str = "1200"
    fg_inventory_account_code: str = "1300"
    cogs_account_code: str = "6000"

    material_variance_account_code: str = "5100"
    labor_variance_account_code: str = "5200"
    overhead_variance_account_code: str = "5300"


class CostAccountingService:
    """Tracks manufacturing costs, WIP, variances, and COGS/margins."""

    def __init__(
        self,
        *,
        config: CostAccountingConfig | None = None,
        ledger: Any | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self._cfg = config or CostAccountingConfig()
        self._ledger = ledger
        self._now_fn: Callable[[], datetime] = now_fn or _now

        self._standard_costs: dict[str, list[StandardCost]] = {}
        self._work_orders: dict[str, WorkOrderCostState] = {}

        self._issues: dict[UUID, MaterialIssue] = {}
        self._labor: dict[UUID, DirectLaborBooking] = {}
        self._overhead: dict[UUID, OverheadBooking] = {}
        self._completions: dict[UUID, CompletionReceipt] = {}
        self._shipments: dict[UUID, Shipment] = {}

        # Inventory at standard cost
        self._fg_qty: dict[str, Decimal] = {}
        self._fg_value: dict[str, Decimal] = {}

        self._audit: list[AuditEvent] = []

    # ------------------------------------------------------------------
    # Standards
    # ------------------------------------------------------------------

    def set_standard_cost(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        sku: str,
        currency: str,
        effective_date: date,
        material_unit_cost: Decimal,
        labor_unit_cost: Decimal,
        overhead_unit_cost: Decimal,
    ) -> StandardCost:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COST_WRITE_ROLES, "Cost write role required")

        s = (sku or "").strip()
        if not s:
            raise ValueError("sku required")

        cur = _norm_currency(currency or self._cfg.base_currency)
        for v in (material_unit_cost, labor_unit_cost, overhead_unit_cost):
            if v < 0:
                raise ValueError("unit costs must be >= 0")

        sc = StandardCost(
            sku=s,
            currency=cur,
            effective_date=effective_date,
            material_unit_cost=_q2(material_unit_cost),
            labor_unit_cost=_q2(labor_unit_cost),
            overhead_unit_cost=_q2(overhead_unit_cost),
        )

        items = self._standard_costs.setdefault(s, [])
        # Replace exact effective date
        items = [i for i in items if i.effective_date != effective_date]
        items.append(sc)
        items.sort(key=lambda x: x.effective_date)
        self._standard_costs[s] = items

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.standard.set",
            entity_type="sku",
            entity_id=s,
            correlation_id=correlation_id,
            metadata={"effective_date": effective_date.isoformat(), "currency": cur},
        )
        return sc

    def get_standard_cost(self, *, actor_roles: Iterable[str], sku: str, as_of: date) -> StandardCost | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")

        s = (sku or "").strip()
        if not s:
            return None
        items = self._standard_costs.get(s, [])
        best: StandardCost | None = None
        for sc in items:
            if sc.effective_date <= as_of:
                best = sc
            else:
                break
        return best

    # ------------------------------------------------------------------
    # Work orders
    # ------------------------------------------------------------------

    def register_work_order(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        finished_sku: str,
        planned_quantity: Decimal,
        currency: str | None = None,
    ) -> WorkOrderCostState:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COST_WRITE_ROLES, "Cost write role required")

        wid = (work_order_id or "").strip()
        if not wid:
            raise ValueError("work_order_id required")
        sku = (finished_sku or "").strip()
        if not sku:
            raise ValueError("finished_sku required")
        if planned_quantity <= 0:
            raise ValueError("planned_quantity must be > 0")

        cur = _norm_currency(currency or self._cfg.base_currency)
        st = WorkOrderCostState(
            work_order_id=wid,
            finished_sku=sku,
            currency=cur,
            planned_quantity=planned_quantity,
        )
        self._work_orders[wid] = st
        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.wo.register",
            entity_type="work_order",
            entity_id=wid,
            correlation_id=correlation_id,
            metadata={"finished_sku": sku, "planned_quantity": str(planned_quantity)},
        )
        return st

    def get_work_order(self, *, actor_roles: Iterable[str], work_order_id: str) -> WorkOrderCostState | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES.union({"ops", "production"}), "Read role required")
        return self._work_orders.get((work_order_id or "").strip())

    # ------------------------------------------------------------------
    # Cost inputs
    # ------------------------------------------------------------------

    def record_material_issue(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        sku: str,
        quantity: Decimal,
        unit_cost: Decimal,
        issued_at: datetime | None = None,
    ) -> MaterialIssue:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COST_WRITE_ROLES, "Cost write role required")

        st = self._require_wo(work_order_id)
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if unit_cost < 0:
            raise ValueError("unit_cost must be >= 0")

        mi = MaterialIssue(
            id=uuid4(),
            work_order_id=st.work_order_id,
            sku=(sku or "").strip(),
            quantity=quantity,
            unit_cost=_q2(unit_cost),
            issued_at=issued_at or self._now_fn(),
            issued_by=actor_id,
        )
        self._issues[mi.id] = mi
        st.actual_material_cost = _q2(st.actual_material_cost + mi.extended_cost)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.material.issue",
            entity_type="work_order",
            entity_id=st.work_order_id,
            correlation_id=correlation_id,
            metadata={"sku": mi.sku, "qty": str(quantity), "cost": str(mi.extended_cost)},
        )
        return mi

    def record_labor_booking(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        hours: Decimal,
        hourly_rate: Decimal,
        operation_id: str | None = None,
        booked_at: datetime | None = None,
    ) -> DirectLaborBooking:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COST_WRITE_ROLES, "Cost write role required")

        st = self._require_wo(work_order_id)
        if hours <= 0:
            raise ValueError("hours must be > 0")
        if hourly_rate < 0:
            raise ValueError("hourly_rate must be >= 0")

        lb = DirectLaborBooking(
            id=uuid4(),
            work_order_id=st.work_order_id,
            operation_id=(operation_id or None),
            hours=_q2(hours),
            hourly_rate=_q2(hourly_rate),
            booked_at=booked_at or self._now_fn(),
            booked_by=actor_id,
        )
        self._labor[lb.id] = lb
        st.actual_labor_cost = _q2(st.actual_labor_cost + lb.extended_cost)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.labor.book",
            entity_type="work_order",
            entity_id=st.work_order_id,
            correlation_id=correlation_id,
            metadata={"hours": str(lb.hours), "cost": str(lb.extended_cost), "operation_id": lb.operation_id},
        )
        return lb

    def ingest_labor_booking_like(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        booking: Any,
        default_hourly_rate: Decimal,
    ) -> DirectLaborBooking:
        """Ingest a labor booking from another service (e.g., payroll_labor_costing).

        Expected attrs/keys:
        - work_order_id
        - operation_id (optional)
        - hours (float/Decimal) OR minutes
        """
        wid = getattr(booking, "work_order_id", None) or getattr(booking, "workOrderId", None)
        if wid is None and isinstance(booking, dict):
            wid = booking.get("work_order_id")
        if wid is None:
            raise ValueError("booking missing work_order_id")

        op = getattr(booking, "operation_id", None)
        if op is None and isinstance(booking, dict):
            op = booking.get("operation_id")

        hours_val = getattr(booking, "hours", None)
        if hours_val is None and isinstance(booking, dict):
            hours_val = booking.get("hours")

        if hours_val is None:
            minutes_val = getattr(booking, "minutes", None)
            if minutes_val is None and isinstance(booking, dict):
                minutes_val = booking.get("minutes")
            if minutes_val is None:
                raise ValueError("booking missing hours/minutes")
            hours_val = Decimal(str(minutes_val)) / Decimal("60")

        return self.record_labor_booking(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            work_order_id=str(wid),
            hours=Decimal(str(hours_val)),
            hourly_rate=default_hourly_rate,
            operation_id=str(op) if op else None,
        )

    def record_overhead(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        amount: Decimal,
        booked_at: datetime | None = None,
    ) -> OverheadBooking:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COST_WRITE_ROLES, "Cost write role required")

        st = self._require_wo(work_order_id)
        amt = _q2(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")

        ob = OverheadBooking(
            id=uuid4(),
            work_order_id=st.work_order_id,
            amount=amt,
            booked_at=booked_at or self._now_fn(),
            booked_by=actor_id,
        )
        self._overhead[ob.id] = ob
        st.actual_overhead_cost = _q2(st.actual_overhead_cost + ob.amount)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.overhead.book",
            entity_type="work_order",
            entity_id=st.work_order_id,
            correlation_id=correlation_id,
            metadata={"amount": str(ob.amount)},
        )
        return ob

    # ------------------------------------------------------------------
    # WIP, completion, variances
    # ------------------------------------------------------------------

    def wip_valuation(self, *, actor_roles: Iterable[str], as_of: date | None = None) -> list[WIPValuationRow]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES.union({"ops", "production"}), "Read role required")
        # as_of is reserved for future time filtering; current implementation is all-to-date.
        _ = as_of

        rows = [
            WIPValuationRow(
                work_order_id=st.work_order_id,
                finished_sku=st.finished_sku,
                planned_quantity=st.planned_quantity,
                completed_quantity=st.completed_quantity,
                wip_actual_cost=st.wip_actual_cost,
            )
            for st in self._work_orders.values()
            if st.wip_actual_cost != 0
        ]
        rows.sort(key=lambda r: r.work_order_id)
        return rows

    def receive_completion(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        quantity_completed: Decimal,
        received_at: datetime | None = None,
    ) -> tuple[CompletionReceipt, VarianceBreakdown]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES.union({"ops", "production"}), "Completion role required")

        st = self._require_wo(work_order_id)
        qty = quantity_completed
        if qty <= 0:
            raise ValueError("quantity_completed must be > 0")

        remaining_qty = st.planned_quantity - st.completed_quantity
        if qty > remaining_qty:
            raise ValueError("quantity_completed exceeds remaining")

        prev_relieved = st.relieved_actual_cost

        receipt = CompletionReceipt(
            id=uuid4(),
            work_order_id=st.work_order_id,
            finished_sku=st.finished_sku,
            quantity_completed=qty,
            received_at=received_at or self._now_fn(),
            received_by=actor_id,
        )
        self._completions[receipt.id] = receipt

        # Allocate actual WIP proportionally on remaining WIP (use pre-relief state)
        remaining_wip_actual = _q2(st.actual_total_cost - prev_relieved)
        if remaining_qty <= 0:
            raise ValueError("No remaining quantity")

        allocate = _q2(remaining_wip_actual * (qty / remaining_qty))

        # Standard cost for receipt
        sc = self.get_standard_cost(actor_roles=roles, sku=st.finished_sku, as_of=receipt.received_at.date())
        if sc is None:
            raise ValueError("No standard cost set for finished SKU")
        if sc.currency != st.currency:
            raise ValueError("Currency mismatch between WO and standard cost")

        std_material = _q2(sc.material_unit_cost * qty)
        std_labor = _q2(sc.labor_unit_cost * qty)
        std_overhead = _q2(sc.overhead_unit_cost * qty)
        std_total = _q2(std_material + std_labor + std_overhead)

        # Approximate actual component allocation based on remaining (unrelieved) composition.
        # Important: base "relieved component share" on the pre-relief relieved total; otherwise
        # the remaining components can incorrectly collapse to 0 during this receipt.
        total_actual = st.actual_total_cost
        if remaining_wip_actual <= 0 or total_actual <= 0:
            actual_material = Decimal("0")
            actual_labor = Decimal("0")
            actual_overhead = Decimal("0")
        else:
            # Relieved-to-date component approximation from pre-relief state
            rel_mat = _q2(prev_relieved * (st.actual_material_cost / total_actual))
            rel_lab = _q2(prev_relieved * (st.actual_labor_cost / total_actual))
            rel_ovh = _q2(prev_relieved * (st.actual_overhead_cost / total_actual))

            rem_mat = _q2(st.actual_material_cost - rel_mat)
            rem_lab = _q2(st.actual_labor_cost - rel_lab)
            rem_ovh = _q2(st.actual_overhead_cost - rel_ovh)
            denom = rem_mat + rem_lab + rem_ovh
            if denom <= 0:
                actual_material = Decimal("0")
                actual_labor = Decimal("0")
                actual_overhead = Decimal("0")
            else:
                actual_material = _q2(allocate * (rem_mat / denom))
                actual_labor = _q2(allocate * (rem_lab / denom))
                actual_overhead = _q2(allocate * (rem_ovh / denom))

        st.relieved_actual_cost = _q2(prev_relieved + allocate)
        st.completed_quantity = _q2(st.completed_quantity + qty)

        vb = VarianceBreakdown(
            material=_q2(actual_material - std_material),
            labor=_q2(actual_labor - std_labor),
            overhead=_q2(actual_overhead - std_overhead),
        )

        # Update FG inventory at standard cost
        self._fg_qty[st.finished_sku] = _q2(self._fg_qty.get(st.finished_sku, Decimal("0")) + qty)
        self._fg_value[st.finished_sku] = _q2(self._fg_value.get(st.finished_sku, Decimal("0")) + std_total)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.wo.complete",
            entity_type="work_order",
            entity_id=st.work_order_id,
            correlation_id=correlation_id,
            metadata={"qty": str(qty), "std_total": str(std_total), "actual_alloc": str(allocate)},
        )

        self._post_completion_to_gl(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            work_order_id=st.work_order_id,
            receipt=receipt,
            allocated_actual=allocate,
            standard_total=std_total,
            variances=vb,
            currency=st.currency,
        )

        return receipt, vb

    def ship(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        customer_id: str,
        sku: str,
        quantity_shipped: Decimal,
        revenue_total: Decimal,
        currency: str,
        shipped_at: datetime | None = None,
        reference: str | None = None,
    ) -> Shipment:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COST_WRITE_ROLES.union({"sales", "shipping"}), "Shipment role required")

        s = (sku or "").strip()
        if not s:
            raise ValueError("sku required")
        qty = quantity_shipped
        if qty <= 0:
            raise ValueError("quantity_shipped must be > 0")
        rev = _q2(revenue_total)
        if rev < 0:
            raise ValueError("revenue_total must be >= 0")
        cur = _norm_currency(currency or self._cfg.base_currency)

        onhand = self._fg_qty.get(s, Decimal("0"))
        if qty > onhand:
            raise ValueError("Insufficient FG inventory")

        sc = self.get_standard_cost(actor_roles=roles, sku=s, as_of=(shipped_at or self._now_fn()).date())
        if sc is None:
            raise ValueError("No standard cost set for SKU")
        if sc.currency != cur:
            raise ValueError("Currency mismatch")

        cogs = _q2(sc.total_unit_cost * qty)

        # Reduce inventory at standard cost
        self._fg_qty[s] = _q2(onhand - qty)
        self._fg_value[s] = _q2(self._fg_value.get(s, Decimal("0")) - cogs)

        sh = Shipment(
            id=uuid4(),
            customer_id=str(customer_id),
            sku=s,
            quantity_shipped=qty,
            revenue_total=rev,
            currency=cur,
            shipped_at=shipped_at or self._now_fn(),
            reference=reference,
        )
        self._shipments[sh.id] = sh

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="cost.ship",
            entity_type="shipment",
            entity_id=str(sh.id),
            correlation_id=correlation_id,
            metadata={"sku": s, "qty": str(qty), "cogs": str(cogs), "revenue": str(rev)},
        )

        self._post_cogs_to_gl(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            shipment=sh,
            cogs=cogs,
        )

        return sh

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def margin_report(self, *, actor_roles: Iterable[str], start: date, end: date) -> list[MarginRow]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES.union({"sales", "gm"}), "Report role required")

        sums: dict[tuple[str, str], dict[str, Decimal]] = {}
        for sh in self._shipments.values():
            d = sh.shipped_at.date()
            if d < start or d > end:
                continue
            key = (sh.customer_id, sh.sku)
            bucket = sums.setdefault(key, {"revenue": Decimal("0"), "cogs": Decimal("0")})

            sc = self.get_standard_cost(actor_roles=roles, sku=sh.sku, as_of=d)
            if sc is None:
                continue
            cogs = _q2(sc.total_unit_cost * sh.quantity_shipped)

            bucket["revenue"] = _q2(bucket["revenue"] + sh.revenue_total)
            bucket["cogs"] = _q2(bucket["cogs"] + cogs)

        rows = [
            MarginRow(customer_id=k[0], sku=k[1], revenue=v["revenue"], cogs=v["cogs"])
            for k, v in sums.items()
        ]
        rows.sort(key=lambda r: (r.customer_id, r.sku))
        return rows

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
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
        _require_any(roles, _COST_WRITE_ROLES, "Cost write role required")
        self._audit.append(
            AuditEvent(
                id=uuid4(),
                occurred_at=self._now_fn(),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                metadata=metadata or {},
            )
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_wo(self, work_order_id: str) -> WorkOrderCostState:
        wid = (work_order_id or "").strip()
        st = self._work_orders.get(wid)
        if st is None:
            raise ValueError("Unknown work order")
        return st

    def _relieved_component_share(self, st: WorkOrderCostState, component: str) -> Decimal:
        """Approximate relieved component share proportional to totals."""
        total = st.actual_total_cost
        if total <= 0:
            return Decimal("0")
        if component == "material":
            share = st.actual_material_cost / total
        elif component == "labor":
            share = st.actual_labor_cost / total
        elif component == "overhead":
            share = st.actual_overhead_cost / total
        else:
            return Decimal("0")
        return _q2(st.relieved_actual_cost * share)

    # ------------------------------------------------------------------
    # GL integration
    # ------------------------------------------------------------------

    def _post_completion_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        receipt: CompletionReceipt,
        allocated_actual: Decimal,
        standard_total: Decimal,
        variances: VarianceBreakdown,
        currency: str,
    ) -> None:
        if self._ledger is None:
            return

        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        roles = _norm_roles(actor_roles)

        lines: list[GLLine] = []

        # Dr FG Inventory at standard
        lines.append(
            GLLine(
                account_code=self._cfg.fg_inventory_account_code,
                debit=_q2(standard_total),
                credit=Decimal("0"),
                currency=currency,
                memo=f"WO {work_order_id} completion",
            )
        )

        # Variance lines (debit if unfavorable, credit if favorable)
        for acct, amt, label in (
            (self._cfg.material_variance_account_code, variances.material, "material"),
            (self._cfg.labor_variance_account_code, variances.labor, "labor"),
            (self._cfg.overhead_variance_account_code, variances.overhead, "overhead"),
        ):
            if amt == 0:
                continue
            if amt > 0:
                lines.append(
                    GLLine(
                        account_code=acct,
                        debit=_q2(amt),
                        credit=Decimal("0"),
                        currency=currency,
                        memo=f"WO {work_order_id} {label} variance",
                    )
                )
            else:
                lines.append(
                    GLLine(
                        account_code=acct,
                        debit=Decimal("0"),
                        credit=_q2(-amt),
                        currency=currency,
                        memo=f"WO {work_order_id} {label} variance",
                    )
                )

        # Cr WIP at actual allocated
        lines.append(
            GLLine(
                account_code=self._cfg.wip_account_code,
                debit=Decimal("0"),
                credit=_q2(allocated_actual),
                currency=currency,
                memo=f"WO {work_order_id} relieve WIP",
            )
        )

        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=f"WO-{work_order_id}",
            entry_date=receipt.received_at.date(),
            description=f"WO completion {work_order_id}",
            lines=lines,
            metadata={
                "source": "cost_accounting",
                "work_order_id": work_order_id,
                "receipt_id": str(receipt.id),
                "allocated_actual": str(_q2(allocated_actual)),
                "standard_total": str(_q2(standard_total)),
                "variance_breakdown": {
                    "material": str(_q2(variances.material)),
                    "labor": str(_q2(variances.labor)),
                    "overhead": str(_q2(variances.overhead)),
                },
            },
        )
        self._ledger.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self._ledger.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)

    def _post_cogs_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        shipment: Shipment,
        cogs: Decimal,
    ) -> None:
        if self._ledger is None:
            return

        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        roles = _norm_roles(actor_roles)

        lines = [
            GLLine(
                account_code=self._cfg.cogs_account_code,
                debit=_q2(cogs),
                credit=Decimal("0"),
                currency=shipment.currency,
                memo=f"COGS shipment {shipment.reference or shipment.id}",
            ),
            GLLine(
                account_code=self._cfg.fg_inventory_account_code,
                debit=Decimal("0"),
                credit=_q2(cogs),
                currency=shipment.currency,
                memo=f"Inventory relieve {shipment.reference or shipment.id}",
            ),
        ]

        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            reference=shipment.reference or f"SHIP-{str(shipment.id)[:8]}",
            entry_date=shipment.shipped_at.date(),
            description="COGS booking",
            lines=lines,
            metadata={"source": "cost_accounting", "shipment_id": str(shipment.id)},
        )
        self._ledger.approve_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)
        self._ledger.post_journal_entry(actor_id=actor_id, actor_roles=roles, correlation_id=correlation_id, entry_id=je.id)

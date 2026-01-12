"""Financial ↔ Operational Feedback Loop (Development Plan 23.2).

Provides:
- Automated reconciliation between MES labor bookings (PayrollLaborCostingService)
  and manufacturing cost rollups (CostAccountingService).
- Variance alerting into CEOControlPlaneService when actual COGS deviates from
  quote estimate beyond a threshold.

This service is deterministic, pure-Python, and designed to compose existing
in-memory service modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable

from sensei.services.ops.ceo_control_plane import CEOControlPlaneService


class ReconciliationIssueType(str, Enum):
    MISSING_WORK_ORDER = "missing_work_order"
    MISSING_COST_CENTER = "missing_cost_center"
    UNKNOWN_COST_CENTER = "unknown_cost_center"
    MISSING_EMPLOYEE_RATE = "missing_employee_rate"


@dataclass(frozen=True)
class ReconciliationIssue:
    issue_type: ReconciliationIssueType
    booking_id: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationReport:
    total_bookings_seen: int
    bookings_ingested: int
    issues: list[ReconciliationIssue]


@dataclass(frozen=True)
class QuoteCOGSVariance:
    quote_id: str
    estimated_cogs: Decimal
    actual_cogs: Decimal
    deviation_pct: Decimal
    threshold_pct: Decimal
    work_order_ids: list[str]


class FinancialOperationalFeedbackService:
    def __init__(
        self,
        *,
        ceo_control_plane: CEOControlPlaneService,
    ) -> None:
        self._ceo = ceo_control_plane

    @staticmethod
    def reconcile_labor_bookings(
        *,
        payroll: Any,
        cost_accounting: Any,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        allowed_cost_centers: set[str] | None = None,
        default_hourly_rate: Decimal,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> ReconciliationReport:
        """Ingest labor bookings into cost accounting with basic validation.

        - Validates cost center against allowed list (if provided)
        - Requires a work_order_id for cost attribution
        - Uses per-employee hourly rate when available, else default

        Notes:
        - This is intentionally best-effort: invalid bookings produce issues and are skipped.
        """

        allowed = {c.strip() for c in (allowed_cost_centers or set()) if c and c.strip()}
        issues: list[ReconciliationIssue] = []

        bookings = payroll.list_labor_bookings(start=start, end=end)
        ingested = 0

        for b in bookings:
            bid = str(getattr(b, "id", ""))

            cost_center = (getattr(b, "cost_center", "") or "").strip()
            if not cost_center:
                issues.append(
                    ReconciliationIssue(
                        issue_type=ReconciliationIssueType.MISSING_COST_CENTER,
                        booking_id=bid,
                        description="Labor booking missing cost_center",
                    )
                )
                continue
            if allowed and cost_center not in allowed:
                issues.append(
                    ReconciliationIssue(
                        issue_type=ReconciliationIssueType.UNKNOWN_COST_CENTER,
                        booking_id=bid,
                        description="Labor booking cost_center not recognized",
                        metadata={"cost_center": cost_center},
                    )
                )
                continue

            work_order_id = (getattr(b, "work_order_id", None) or "").strip()
            if not work_order_id:
                issues.append(
                    ReconciliationIssue(
                        issue_type=ReconciliationIssueType.MISSING_WORK_ORDER,
                        booking_id=bid,
                        description="Labor booking missing work_order_id",
                        metadata={"cost_center": cost_center},
                    )
                )
                continue

            # Attempt to pull a per-employee rate from payroll service if exposed.
            rate: Decimal | None = None
            if hasattr(payroll, "get_employee_hourly_rate"):
                r = payroll.get_employee_hourly_rate(employee_id=b.employee_id)
                if r is not None:
                    rate = Decimal(str(r))

            if rate is None:
                # If payroll doesn't have the rate, continue with default but record issue.
                issues.append(
                    ReconciliationIssue(
                        issue_type=ReconciliationIssueType.MISSING_EMPLOYEE_RATE,
                        booking_id=bid,
                        description="Employee hourly rate missing; used default",
                        metadata={"employee_id": getattr(b, "employee_id", "")},
                    )
                )
                rate = default_hourly_rate

            # CostAccountingService performs its own RBAC and will raise if actor_roles are insufficient.
            cost_accounting.ingest_labor_booking_like(
                actor_id=actor_id,
                actor_roles=actor_roles,
                correlation_id=correlation_id,
                booking=b,
                default_hourly_rate=rate,
            )
            ingested += 1

        return ReconciliationReport(
            total_bookings_seen=len(bookings),
            bookings_ingested=ingested,
            issues=issues,
        )

    def evaluate_quote_cogs_variance_and_alert(
        self,
        *,
        role: str,
        quote_id: str,
        estimated_cogs: Decimal,
        cost_accounting: Any,
        actor_roles: Iterable[str],
        work_order_ids: list[str],
        threshold_pct: Decimal = Decimal("0.10"),
        correlation_id: str | None = None,
    ) -> QuoteCOGSVariance | None:
        """Compare actual COGS against quote estimate and alert if threshold exceeded."""

        qid = (quote_id or "").strip()
        if not qid:
            raise ValueError("quote_id is required")

        if estimated_cogs <= 0:
            return None

        if threshold_pct <= 0:
            raise ValueError("threshold_pct must be > 0")

        actual = Decimal("0")
        resolved_wos: list[str] = []
        for wid in work_order_ids:
            wid_norm = (wid or "").strip()
            if not wid_norm:
                continue
            st = cost_accounting.get_work_order(actor_roles=actor_roles, work_order_id=wid_norm)
            if st is None:
                continue
            resolved_wos.append(wid_norm)
            actual += Decimal(str(st.actual_total_cost))

        if actual <= 0:
            return None

        deviation = (actual - estimated_cogs) / estimated_cogs
        result = QuoteCOGSVariance(
            quote_id=qid,
            estimated_cogs=estimated_cogs,
            actual_cogs=actual,
            deviation_pct=deviation,
            threshold_pct=threshold_pct,
            work_order_ids=resolved_wos,
        )

        if abs(deviation) >= threshold_pct:
            self._ceo.record_variance_alert(
                role,
                quote_id=qid,
                actual_cogs=float(actual),
                estimated_cogs=float(estimated_cogs),
                threshold_pct=float(threshold_pct),
                work_order_ids=resolved_wos,
                correlation_id=correlation_id,
            )

        return result

"""Executive intelligence endpoints (CEO/Exec).

Development Plan 23.3 persona flow prerequisites:
- NL2SQL query endpoint (deterministic, safe, read-only)

This intentionally implements a *restricted* NL2SQL capability:
- only a small allowlist of supported questions
- executed via SQLAlchemy ORM (no raw SQL)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import json

from typing import Any, Annotated, TypeAlias, Iterable
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case, and_

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import BadRequestError
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.quality import CAPA, CAPAStatus, NCStatus, NCSeverity, NonConformance
from sensei.models.work_order import WorkOrder, WorkOrderStatus
from sensei.models.rfq import RFQ, RFQStatus
from sensei.models.quote import Quote, QuoteLineItem, QuoteStatus
from sensei.models.task import Task, TaskStatus
from sensei.models.product import Product, ProductStatus
from sensei.models.user import User, UserStatus
from sensei.models.opportunity import Opportunity, OpportunityStage
from sensei.models.accounts_receivable import CustomerInvoice, CustomerInvoiceLine, SalesOrder, SalesOrderLine, Shipment
from sensei.models.accounts_payable import PurchaseOrder, SupplierInvoice
from sensei.models.andon import AndonEvent, AndonType
from sensei.models.inventory import InventoryLevel, StockMove
from sensei.models.hr import EmployeeProfile, HRJobOpening
from sensei.models.mrp import MRPSuggestion
from sensei.models.data_lineage import DataLineageLink
from sensei.models.reasoning_trace import ReasoningTrace
from sensei.services.ops.ceo_control_plane import CEOControlPlaneService
from sensei.services.ops.analytics_warehouse import AnalyticsWarehouseService
from sensei.services.ops.insight_generator import generate_insights
from sensei.services.ops.cognitive_obeya import AsyncPrescriptiveMetricAnalyzer
from sensei.services.core.role_insights_config import filter_insights_for_role
from sensei.services.core.insight_audit_logger import get_insight_audit_logger
from sensei.core.pii import mask_analytics_data
from sensei.services.event_bus import event_bus

# Role requirements
AllowExec: TypeAlias = deps.require_role("admin", "ceo", "gm", "exec")  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[Depends(deps.RoleChecker(["admin", "ceo", "gm", "exec"]))]
)


class NL2SQLRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class NL2SQLResponse(BaseModel):
    query_id: str
    natural_language: str
    generated_sql: str
    explanation: str
    result: dict


class EmployeeRiskRequest(BaseModel):
    employee_name: str = Field(..., min_length=1, max_length=200)
    department: str = Field(default="", max_length=200)
    tenure_months: int = Field(default=12, ge=0, le=600)
    overtime_hours_weekly: float = Field(default=0, ge=0, le=168)
    skip_rate: float = Field(default=0, ge=0, le=1)
    peer_comparison: float = Field(default=1.0, ge=0, le=10)


class EmployeeRiskResponse(BaseModel):
    employee_name: str
    retention_risk: str
    retention_score: float
    burnout_risk: str
    burnout_score: float
    risk_factors: list[str]
    recommendations: list[str]


def _roles_for_user(user: object) -> set[str]:
    if getattr(user, "is_superuser", False):
        return {"superuser"}
    role_names = []
    if hasattr(user, "get_role_names"):
        try:
            role_names = list(user.get_role_names())  # type: ignore[attr-defined]
        except Exception:
            role_names = []
    return {str(r).lower() for r in role_names}


def _coerce_exec_role(user: object) -> str:
    roles = _roles_for_user(user)
    for candidate in ("ceo", "exec", "admin", "superuser"):
        if candidate in roles:
            return candidate
    # Default to superuser check only; otherwise deny.
    raise BadRequestError("Executive access required")


def _normalize(q: str) -> str:
    return " ".join(q.strip().lower().split())


@router.post("/nl2sql", response_model=APIResponse[NL2SQLResponse])
async def nl2sql_query(
    _: AllowExec,
    payload: NL2SQLRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[NL2SQLResponse]:
    q = _normalize(payload.question)

    # ── Registry of deterministic, read-only ORM queries ──
    # Each matcher returns an NL2SQLResponse or None.

    resp = await _try_match_query(q, payload.question, db)
    if resp is not None:
        return build_response(data=resp)

    raise BadRequestError(
        "Unsupported NL2SQL question (restricted allowlist)",
        details={
            "supported_examples": _SUPPORTED_EXAMPLES,
        },
    )


# ---------------------------------------------------------------------------
# Supported questions catalogue
# ---------------------------------------------------------------------------

_SUPPORTED_EXAMPLES: list[str] = [
    "How many open non conformances are there?",
    "How many critical non conformances are there?",
    "How many open CAPAs are there?",
    "How many CAPAs are in progress?",
    "How many work orders are in progress?",
    "How many work orders are on hold?",
    "How many completed work orders are there?",
    "How many open RFQs are there?",
    "How many quotes are pending approval?",
    "How many quotes were accepted?",
    "How many open tasks are there?",
    "How many blocked tasks are there?",
    "How many overdue tasks are there?",
    "How many active products do we have?",
    "How many active users are there?",
    "How many open opportunities are there?",
    "What is the total opportunity pipeline value?",
    "How many purchase orders are open?",
    "How many customer invoices are outstanding?",
    "How many pending shipments are there?",
    "How many active andon events are there?",
    "How many sales orders are open?",
    "What is the total inventory on hand?",
    "Give me a work order summary by status.",
    "Give me an NC summary by severity.",
]


async def _try_match_query(
    q: str, raw_question: str, db: DBSession
) -> NL2SQLResponse | None:
    """Pattern-match the normalised question *q* against the allowlist."""

    # ── Non Conformance queries ──────────────────────────────────
    if "non conformance" in q or "nonconformance" in q or " nc " in f" {q} " or "ncr" in q:
        if "critical" in q:
            stmt = select(func.count()).select_from(NonConformance).where(
                NonConformance.severity == NCSeverity.CRITICAL
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:critical_ncs",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM non_conformances WHERE severity = 'critical';",
                explanation="Counts non-conformance records with critical severity.",
                result={"critical_non_conformances": int(count)},
            )
        if "summary" in q and "severity" in q:
            stmt = (
                select(NonConformance.severity, func.count())
                .group_by(NonConformance.severity)
            )
            rows = (await db.execute(stmt)).all()
            breakdown = {(r[0].value if hasattr(r[0], "value") else str(r[0])): int(r[1]) for r in rows}
            return NL2SQLResponse(
                query_id="nl2sql:nc_severity_summary",
                natural_language=raw_question,
                generated_sql="SELECT severity, COUNT(*) FROM non_conformances GROUP BY severity;",
                explanation="Breaks down non-conformance records by severity level.",
                result={"nc_by_severity": breakdown, "total": sum(breakdown.values())},
            )
        # default: open NCs
        stmt = select(func.count()).select_from(NonConformance).where(
            NonConformance.status == NCStatus.OPEN
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_non_conformances",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM non_conformances WHERE status = 'open';",
            explanation="Counts open non-conformance records.",
            result={"open_non_conformances": int(count)},
        )

    # ── CAPA queries ─────────────────────────────────────────────
    if "capa" in q:
        if "in progress" in q or "in_progress" in q:
            stmt = select(func.count()).select_from(CAPA).where(
                CAPA.status == CAPAStatus.IN_PROGRESS
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:in_progress_capas",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM capas WHERE status = 'in_progress';",
                explanation="Counts CAPA records currently in progress.",
                result={"in_progress_capas": int(count)},
            )
        # default: open CAPAs
        stmt = select(func.count()).select_from(CAPA).where(CAPA.status == CAPAStatus.OPEN)
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_capas",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM capas WHERE status = 'open';",
            explanation="Counts open CAPA records.",
            result={"open_capas": int(count)},
        )

    # ── Work Order queries ───────────────────────────────────────
    if "work order" in q or "workorder" in q or " wo " in f" {q} ":
        if "on hold" in q or "on_hold" in q:
            stmt = select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.ON_HOLD
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:on_hold_work_orders",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM work_orders WHERE status = 'on_hold';",
                explanation="Counts work orders currently on hold.",
                result={"on_hold_work_orders": int(count)},
            )
        if "completed" in q or "complete" in q:
            stmt = select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.COMPLETED
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:completed_work_orders",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM work_orders WHERE status = 'completed';",
                explanation="Counts completed work orders.",
                result={"completed_work_orders": int(count)},
            )
        if "summary" in q and "status" in q:
            stmt = (
                select(WorkOrder.status, func.count())
                .group_by(WorkOrder.status)
            )
            rows = (await db.execute(stmt)).all()
            breakdown = {(r[0].value if hasattr(r[0], "value") else str(r[0])): int(r[1]) for r in rows}
            return NL2SQLResponse(
                query_id="nl2sql:work_order_status_summary",
                natural_language=raw_question,
                generated_sql="SELECT status, COUNT(*) FROM work_orders GROUP BY status;",
                explanation="Breaks down work orders by current status.",
                result={"work_orders_by_status": breakdown, "total": sum(breakdown.values())},
            )
        # default: in-progress work orders
        stmt = select(func.count()).select_from(WorkOrder).where(
            WorkOrder.status == WorkOrderStatus.IN_PROGRESS
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:in_progress_work_orders",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM work_orders WHERE status = 'in_progress';",
            explanation="Counts work orders currently in progress.",
            result={"in_progress_work_orders": int(count)},
        )

    # ── RFQ queries ──────────────────────────────────────────────
    if "rfq" in q or "request for quote" in q:
        stmt = select(func.count()).select_from(RFQ).where(
            RFQ.status.in_([RFQStatus.RECEIVED, RFQStatus.UNDER_REVIEW, RFQStatus.QUALIFYING, RFQStatus.QUOTING])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_rfqs",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM rfqs WHERE status IN ('received','under_review','qualifying','quoting');",
            explanation="Counts RFQs that are actively being worked (received, under review, qualifying, or quoting).",
            result={"open_rfqs": int(count)},
        )

    # ── Quote queries ────────────────────────────────────────────
    if "quote" in q and "rfq" not in q:
        if "pending" in q and "approval" in q:
            stmt = select(func.count()).select_from(Quote).where(
                Quote.status == QuoteStatus.PENDING_APPROVAL
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:pending_approval_quotes",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM quotes WHERE status = 'pending_approval';",
                explanation="Counts quotes awaiting approval.",
                result={"pending_approval_quotes": int(count)},
            )
        if "accepted" in q or "won" in q:
            stmt = select(func.count()).select_from(Quote).where(
                Quote.status == QuoteStatus.ACCEPTED
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:accepted_quotes",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM quotes WHERE status = 'accepted';",
                explanation="Counts quotes that have been accepted by customers.",
                result={"accepted_quotes": int(count)},
            )
        # default: total active quotes (draft + pending_review + pending_approval + sent)
        stmt = select(func.count()).select_from(Quote).where(
            Quote.status.in_([QuoteStatus.DRAFT, QuoteStatus.PENDING_REVIEW, QuoteStatus.PENDING_APPROVAL, QuoteStatus.SENT])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:active_quotes",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM quotes WHERE status IN ('draft','pending_review','pending_approval','sent');",
            explanation="Counts quotes still in the active pipeline (draft through sent).",
            result={"active_quotes": int(count)},
        )

    # ── Task queries ─────────────────────────────────────────────
    if "task" in q:
        if "blocked" in q:
            stmt = select(func.count()).select_from(Task).where(Task.status == TaskStatus.BLOCKED)
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:blocked_tasks",
                natural_language=raw_question,
                generated_sql="SELECT COUNT(*) FROM tasks WHERE status = 'blocked';",
                explanation="Counts tasks currently in blocked status.",
                result={"blocked_tasks": int(count)},
            )
        if "overdue" in q:
            now = datetime.now(timezone.utc)
            stmt = select(func.count()).select_from(Task).where(
                and_(
                    Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                    Task.due_date < now,
                )
            )
            count = (await db.execute(stmt)).scalar() or 0
            return NL2SQLResponse(
                query_id="nl2sql:overdue_tasks",
                natural_language=raw_question,
                generated_sql=f"SELECT COUNT(*) FROM tasks WHERE status IN ('open','todo','in_progress') AND due_date < NOW();",
                explanation="Counts tasks that are past their due date and not yet completed.",
                result={"overdue_tasks": int(count)},
            )
        # default: open tasks
        stmt = select(func.count()).select_from(Task).where(
            Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_tasks",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM tasks WHERE status IN ('open','todo');",
            explanation="Counts tasks in open or to-do status.",
            result={"open_tasks": int(count)},
        )

    # ── Product queries ──────────────────────────────────────────
    if "product" in q:
        stmt = select(func.count()).select_from(Product).where(
            Product.status == ProductStatus.ACTIVE
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:active_products",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM products WHERE status = 'active';",
            explanation="Counts currently active products in the catalogue.",
            result={"active_products": int(count)},
        )

    # ── User queries ─────────────────────────────────────────────
    if "user" in q or "employee" in q or "staff" in q:
        stmt = select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:active_users",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM users WHERE status = 'active';",
            explanation="Counts active user accounts.",
            result={"active_users": int(count)},
        )

    # ── Opportunity / Pipeline queries ───────────────────────────
    if "opportunity" in q or "pipeline" in q:
        if "value" in q or "total" in q or "worth" in q or "amount" in q:
            stmt = select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
                Opportunity.stage.in_([
                    OpportunityStage.PROSPECTING,
                    OpportunityStage.QUALIFICATION,
                    OpportunityStage.NEEDS_ANALYSIS,
                    OpportunityStage.VALUE_PROPOSITION,
                    OpportunityStage.PROPOSAL,
                    OpportunityStage.NEGOTIATION,
                ])
            )
            total = float((await db.execute(stmt)).scalar() or 0)
            return NL2SQLResponse(
                query_id="nl2sql:pipeline_value",
                natural_language=raw_question,
                generated_sql="SELECT SUM(value) FROM opportunities WHERE stage NOT IN ('closed_won','closed_lost');",
                explanation="Sums the monetary value of all opportunities still in the active pipeline.",
                result={"pipeline_value": total},
            )
        # default: count open opportunities
        stmt = select(func.count()).select_from(Opportunity).where(
            Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_opportunities",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM opportunities WHERE stage NOT IN ('closed_won','closed_lost');",
            explanation="Counts opportunities that have not yet been closed (won or lost).",
            result={"open_opportunities": int(count)},
        )

    # ── Purchase Order queries ───────────────────────────────────
    if "purchase order" in q or " po " in f" {q} ":
        stmt = select(func.count()).select_from(PurchaseOrder).where(
            PurchaseOrder.status.in_(["draft", "submitted", "approved", "ordered", "partial"])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_purchase_orders",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM purchase_orders WHERE status IN ('draft','submitted','approved','ordered','partial');",
            explanation="Counts purchase orders that are still open (not fully received, cancelled, or closed).",
            result={"open_purchase_orders": int(count)},
        )

    # ── Customer Invoice queries ─────────────────────────────────
    if "invoice" in q and "supplier" not in q:
        stmt = select(func.count()).select_from(CustomerInvoice).where(
            CustomerInvoice.status.in_(["draft", "sent", "overdue", "partial"])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:outstanding_invoices",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM customer_invoices WHERE status IN ('draft','sent','overdue','partial');",
            explanation="Counts customer invoices that are not yet fully paid.",
            result={"outstanding_invoices": int(count)},
        )

    # ── Shipment queries ─────────────────────────────────────────
    if "shipment" in q or "shipping" in q or "delivery" in q:
        stmt = select(func.count()).select_from(Shipment).where(
            Shipment.status.in_(["pending", "processing", "packed", "ready"])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:pending_shipments",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM shipments WHERE status IN ('pending','processing','packed','ready');",
            explanation="Counts shipments that have not yet been dispatched.",
            result={"pending_shipments": int(count)},
        )

    # ── Andon queries ────────────────────────────────────────────
    if "andon" in q:
        stmt = select(func.count()).select_from(AndonEvent).where(
            AndonEvent.status.in_(["open", "acknowledged", "escalated"])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:active_andon_events",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM andon_events WHERE status IN ('open','acknowledged','escalated');",
            explanation="Counts andon events that are currently active (not resolved).",
            result={"active_andon_events": int(count)},
        )

    # ── Sales Order queries ──────────────────────────────────────
    if "sales order" in q or "sales_order" in q:
        stmt = select(func.count()).select_from(SalesOrder).where(
            SalesOrder.status.in_(["draft", "confirmed", "processing", "partial"])
        )
        count = (await db.execute(stmt)).scalar() or 0
        return NL2SQLResponse(
            query_id="nl2sql:open_sales_orders",
            natural_language=raw_question,
            generated_sql="SELECT COUNT(*) FROM sales_orders WHERE status IN ('draft','confirmed','processing','partial');",
            explanation="Counts sales orders that are still being processed.",
            result={"open_sales_orders": int(count)},
        )

    # ── Inventory queries ────────────────────────────────────────
    if "inventory" in q or "stock" in q:
        stmt = select(func.coalesce(func.sum(InventoryLevel.qty_on_hand), 0))
        total = float((await db.execute(stmt)).scalar() or 0)
        return NL2SQLResponse(
            query_id="nl2sql:total_inventory_on_hand",
            natural_language=raw_question,
            generated_sql="SELECT SUM(qty_on_hand) FROM inventory_levels;",
            explanation="Sums the total on-hand inventory across all locations and products.",
            result={"total_qty_on_hand": total},
        )

    return None


@router.post("/employee-risk/analyze", response_model=APIResponse[EmployeeRiskResponse])
async def analyze_employee_risk(
    _: AllowExec,
    payload: EmployeeRiskRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[EmployeeRiskResponse]:
    """Deterministic employee retention/burnout risk assessment.

    Note: This uses the existing CEO control plane service logic (Section 20.5) to keep
    behavior consistent with the executive risk model.
    """

    role = _coerce_exec_role(current_user)

    svc = CEOControlPlaneService(db)
    emp_id = svc.register_employee(role, name=payload.employee_name, department=payload.department)
    if not asyncio.iscoroutinefunction(getattr(db, "commit", None)):
        assessment = svc.assess_retention_risk(
            role,
            employee_id=emp_id,
            tenure_months=payload.tenure_months,
            overtime_hours_weekly=payload.overtime_hours_weekly,
            skip_rate=payload.skip_rate,
            peer_comparison=payload.peer_comparison,
        )
    else:
        assessment = await svc.assess_retention_risk_async(
            db,
            role,
            employee_id=emp_id,
            tenure_months=payload.tenure_months,
            overtime_hours_weekly=payload.overtime_hours_weekly,
            skip_rate=payload.skip_rate,
            peer_comparison=payload.peer_comparison,
        )

    resp = EmployeeRiskResponse(
        employee_name=assessment.employee_name,
        retention_risk=getattr(assessment.retention_risk, "value", str(assessment.retention_risk)).lower(),
        retention_score=float(assessment.retention_score),
        burnout_risk=getattr(assessment.burnout_risk, "value", str(assessment.burnout_risk)).lower(),
        burnout_score=float(assessment.burnout_score),
        risk_factors=list(assessment.risk_factors),
        recommendations=list(assessment.recommendations),
    )

    return build_response(data=resp)


@router.get("/strategic-report/export")
async def export_strategic_report(
    _: AllowExec,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    """Export a comprehensive strategic report pack as a downloadable JSON file.

    Includes KPIs from quality, operations, sales, finance, supply chain, and HR.
    """

    _ = _coerce_exec_role(current_user)

    # ── Quality KPIs ─────────────────────────────────────────
    open_nc_stmt = select(func.count()).select_from(NonConformance).where(
        NonConformance.status == NCStatus.OPEN
    )
    critical_nc_stmt = select(func.count()).select_from(NonConformance).where(
        NonConformance.severity == NCSeverity.CRITICAL
    )
    open_capa_stmt = select(func.count()).select_from(CAPA).where(
        CAPA.status == CAPAStatus.OPEN
    )
    in_progress_capa_stmt = select(func.count()).select_from(CAPA).where(
        CAPA.status == CAPAStatus.IN_PROGRESS
    )

    # ── Operations KPIs ──────────────────────────────────────
    in_progress_wo_stmt = select(func.count()).select_from(WorkOrder).where(
        WorkOrder.status == WorkOrderStatus.IN_PROGRESS
    )
    on_hold_wo_stmt = select(func.count()).select_from(WorkOrder).where(
        WorkOrder.status == WorkOrderStatus.ON_HOLD
    )
    completed_wo_stmt = select(func.count()).select_from(WorkOrder).where(
        WorkOrder.status == WorkOrderStatus.COMPLETED
    )
    active_andon_stmt = select(func.count()).select_from(AndonEvent).where(
        AndonEvent.status.in_(["open", "acknowledged", "escalated"])
    )

    # ── Sales & CRM KPIs ────────────────────────────────────
    open_rfq_stmt = select(func.count()).select_from(RFQ).where(
        RFQ.status.in_([RFQStatus.RECEIVED, RFQStatus.UNDER_REVIEW, RFQStatus.QUALIFYING, RFQStatus.QUOTING])
    )
    pending_quote_stmt = select(func.count()).select_from(Quote).where(
        Quote.status == QuoteStatus.PENDING_APPROVAL
    )
    accepted_quote_stmt = select(func.count()).select_from(Quote).where(
        Quote.status == QuoteStatus.ACCEPTED
    )
    open_opp_stmt = select(func.count()).select_from(Opportunity).where(
        Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
    )
    pipeline_value_stmt = select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
        Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
    )

    # ── Finance KPIs ─────────────────────────────────────────
    outstanding_inv_stmt = select(func.count()).select_from(CustomerInvoice).where(
        CustomerInvoice.status.in_(["draft", "sent", "overdue", "partial"])
    )
    open_po_stmt = select(func.count()).select_from(PurchaseOrder).where(
        PurchaseOrder.status.in_(["draft", "submitted", "approved", "ordered", "partial"])
    )
    open_so_stmt = select(func.count()).select_from(SalesOrder).where(
        SalesOrder.status.in_(["draft", "confirmed", "processing", "partial"])
    )

    # ── Supply Chain KPIs ────────────────────────────────────
    pending_ship_stmt = select(func.count()).select_from(Shipment).where(
        Shipment.status.in_(["pending", "processing", "packed", "ready"])
    )
    inventory_stmt = select(func.coalesce(func.sum(InventoryLevel.quantity_on_hand), 0))

    # ── HR KPIs ──────────────────────────────────────────────
    active_users_stmt = select(func.count()).select_from(User).where(
        User.status == UserStatus.ACTIVE
    )

    # ── Task KPIs ────────────────────────────────────────────
    open_tasks_stmt = select(func.count()).select_from(Task).where(
        Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO])
    )
    blocked_tasks_stmt = select(func.count()).select_from(Task).where(
        Task.status == TaskStatus.BLOCKED
    )
    overdue_tasks_stmt = select(func.count()).select_from(Task).where(
        and_(
            Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
            Task.due_date < datetime.now(timezone.utc),
        )
    )

    # Execute all queries concurrently
    results = await asyncio.gather(
        db.execute(open_nc_stmt),
        db.execute(critical_nc_stmt),
        db.execute(open_capa_stmt),
        db.execute(in_progress_capa_stmt),
        db.execute(in_progress_wo_stmt),
        db.execute(on_hold_wo_stmt),
        db.execute(completed_wo_stmt),
        db.execute(active_andon_stmt),
        db.execute(open_rfq_stmt),
        db.execute(pending_quote_stmt),
        db.execute(accepted_quote_stmt),
        db.execute(open_opp_stmt),
        db.execute(pipeline_value_stmt),
        db.execute(outstanding_inv_stmt),
        db.execute(open_po_stmt),
        db.execute(open_so_stmt),
        db.execute(pending_ship_stmt),
        db.execute(inventory_stmt),
        db.execute(active_users_stmt),
        db.execute(open_tasks_stmt),
        db.execute(blocked_tasks_stmt),
        db.execute(overdue_tasks_stmt),
    )

    (
        r_open_nc, r_critical_nc, r_open_capa, r_ip_capa,
        r_ip_wo, r_hold_wo, r_done_wo, r_andon,
        r_rfq, r_pend_q, r_acc_q, r_opp, r_pipeline,
        r_inv, r_po, r_so,
        r_ship, r_inventory, r_users,
        r_tasks, r_blocked, r_overdue,
    ) = results

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quality": {
            "open_non_conformances": int(r_open_nc.scalar() or 0),
            "critical_non_conformances": int(r_critical_nc.scalar() or 0),
            "open_capas": int(r_open_capa.scalar() or 0),
            "in_progress_capas": int(r_ip_capa.scalar() or 0),
        },
        "operations": {
            "in_progress_work_orders": int(r_ip_wo.scalar() or 0),
            "on_hold_work_orders": int(r_hold_wo.scalar() or 0),
            "completed_work_orders": int(r_done_wo.scalar() or 0),
            "active_andon_events": int(r_andon.scalar() or 0),
        },
        "sales_crm": {
            "open_rfqs": int(r_rfq.scalar() or 0),
            "pending_approval_quotes": int(r_pend_q.scalar() or 0),
            "accepted_quotes": int(r_acc_q.scalar() or 0),
            "open_opportunities": int(r_opp.scalar() or 0),
            "pipeline_value": float(r_pipeline.scalar() or 0),
        },
        "finance": {
            "outstanding_customer_invoices": int(r_inv.scalar() or 0),
            "open_purchase_orders": int(r_po.scalar() or 0),
            "open_sales_orders": int(r_so.scalar() or 0),
        },
        "supply_chain": {
            "pending_shipments": int(r_ship.scalar() or 0),
            "total_inventory_on_hand": float(r_inventory.scalar() or 0),
        },
        "workforce": {
            "active_users": int(r_users.scalar() or 0),
            "open_tasks": int(r_tasks.scalar() or 0),
            "blocked_tasks": int(r_blocked.scalar() or 0),
            "overdue_tasks": int(r_overdue.scalar() or 0),
        },
    }

    # Apply PII masking before exporting
    roles = _roles_for_user(current_user)
    report = await mask_analytics_data(report, list(roles))

    payload = json.dumps(report, indent=2, sort_keys=True)
    filename = f"strategic-report-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# SQDCP Dashboard (Safety, Quality, Delivery, Cost, People)
# ---------------------------------------------------------------------------

class SQDCPResponse(BaseModel):
    safety: dict
    quality: dict
    delivery: dict
    cost: dict
    people: dict
    generated_at: str


async def _build_sqdcp_payload(db: DBSession) -> SQDCPResponse:
    """Build SQDCP payload from live data."""
    # Safety: active andon events + safety-typed andons
    safety_andons = int((await db.execute(
        select(func.count()).select_from(AndonEvent).where(
            and_(
                AndonEvent.andon_type == AndonType.SAFETY,
                AndonEvent.status.in_(["open", "acknowledged", "escalated"]),
            )
        )
    )).scalar() or 0)
    total_active_andons = int((await db.execute(
        select(func.count()).select_from(AndonEvent).where(
            AndonEvent.status.in_(["open", "acknowledged", "escalated"])
        )
    )).scalar() or 0)

    # Quality: open NCs, critical NCs, open CAPAs
    open_ncs = int((await db.execute(
        select(func.count()).select_from(NonConformance).where(
            NonConformance.status == NCStatus.OPEN
        )
    )).scalar() or 0)
    critical_ncs = int((await db.execute(
        select(func.count()).select_from(NonConformance).where(
            NonConformance.severity == NCSeverity.CRITICAL
        )
    )).scalar() or 0)
    open_capas = int((await db.execute(
        select(func.count()).select_from(CAPA).where(CAPA.status == CAPAStatus.OPEN)
    )).scalar() or 0)

    # Delivery: pending shipments, completed WOs, in-progress WOs
    pending_shipments = int((await db.execute(
        select(func.count()).select_from(Shipment).where(
            Shipment.status.in_(["pending", "processing", "packed", "ready"])
        )
    )).scalar() or 0)
    completed_wos = int((await db.execute(
        select(func.count()).select_from(WorkOrder).where(
            WorkOrder.status == WorkOrderStatus.COMPLETED
        )
    )).scalar() or 0)
    in_progress_wos = int((await db.execute(
        select(func.count()).select_from(WorkOrder).where(
            WorkOrder.status == WorkOrderStatus.IN_PROGRESS
        )
    )).scalar() or 0)
    total_wos = completed_wos + in_progress_wos
    on_time_rate = (completed_wos / total_wos * 100) if total_wos > 0 else 0.0

    # Cost: open POs count, outstanding invoices count
    open_po_count = int((await db.execute(
        select(func.count()).select_from(PurchaseOrder).where(
            PurchaseOrder.status.in_(["draft", "submitted", "approved", "ordered", "partial"])
        )
    )).scalar() or 0)
    outstanding_inv_count = int((await db.execute(
        select(func.count()).select_from(CustomerInvoice).where(
            CustomerInvoice.status.in_(["draft", "sent", "overdue", "partial"])
        )
    )).scalar() or 0)
    pipeline_value = float((await db.execute(
        select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
        )
    )).scalar() or 0)

    # People: active users, overdue tasks, blocked tasks + HR headcount/turnover
    active_users = int((await db.execute(
        select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
    )).scalar() or 0)
    overdue_tasks = int((await db.execute(
        select(func.count()).select_from(Task).where(
            and_(
                Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                Task.due_date < datetime.now(timezone.utc),
            )
        )
    )).scalar() or 0)
    blocked_tasks = int((await db.execute(
        select(func.count()).select_from(Task).where(Task.status == TaskStatus.BLOCKED)
    )).scalar() or 0)

    # HR headcount and turnover (data thread harmonization)
    active_employees = int((await db.execute(
        select(func.count()).select_from(EmployeeProfile).where(
            EmployeeProfile.status == "active"
        )
    )).scalar() or 0)
    open_positions = int((await db.execute(
        select(func.count()).select_from(HRJobOpening).where(
            HRJobOpening.status == "open"
        )
    )).scalar() or 0)
    terminated_90d = int((await db.execute(
        select(func.count()).select_from(EmployeeProfile).where(
            and_(
                EmployeeProfile.status == "terminated",
                EmployeeProfile.termination_date >= (datetime.now(timezone.utc) - timedelta(days=90)),
            )
        )
    )).scalar() or 0)
    turnover_rate = round((terminated_90d / max(active_employees, 1)) * 100, 1)

    # Inventory health for Cost pillar (data thread harmonization)
    zero_stock = int((await db.execute(
        select(func.count()).select_from(InventoryLevel).where(
            InventoryLevel.quantity_on_hand <= 0
        )
    )).scalar() or 0)
    pending_mrp = int((await db.execute(
        select(func.count()).select_from(MRPSuggestion).where(
            MRPSuggestion.status == "pending"
        )
    )).scalar() or 0)

    # AP unpaid (data thread harmonization)
    ap_unpaid = int((await db.execute(
        select(func.count()).select_from(SupplierInvoice).where(
            SupplierInvoice.status.in_(["draft", "submitted", "approved", "posted"])
        )
    )).scalar() or 0)

    people_status = "GREEN"
    if overdue_tasks > 10 or turnover_rate > 15:
        people_status = "RED"
    elif overdue_tasks > 3 or turnover_rate > 5 or open_positions > 5:
        people_status = "YELLOW"

    cost_status = "GREEN"
    if ap_unpaid > 20 or outstanding_inv_count > 20:
        cost_status = "RED"
    elif ap_unpaid > 5 or outstanding_inv_count > 5 or zero_stock > 10:
        cost_status = "YELLOW"

    return SQDCPResponse(
        safety={
            "active_safety_andons": safety_andons,
            "total_active_andons": total_active_andons,
            "status": "GREEN" if safety_andons == 0 else "RED" if safety_andons > 2 else "YELLOW",
        },
        quality={
            "open_ncs": open_ncs,
            "critical_ncs": critical_ncs,
            "open_capas": open_capas,
            "status": "RED" if critical_ncs > 0 else "YELLOW" if open_ncs > 5 else "GREEN",
        },
        delivery={
            "pending_shipments": pending_shipments,
            "completed_work_orders": completed_wos,
            "in_progress_work_orders": in_progress_wos,
            "on_time_rate_pct": round(on_time_rate, 1),
            "status": "RED" if pending_shipments > 10 else "YELLOW" if pending_shipments > 3 else "GREEN",
        },
        cost={
            "pipeline_value": pipeline_value,
            "open_po_count": open_po_count,
            "outstanding_invoice_count": outstanding_inv_count,
            "ap_unpaid_count": ap_unpaid,
            "zero_stock_items": zero_stock,
            "pending_mrp_suggestions": pending_mrp,
            "status": cost_status,
        },
        people={
            "active_users": active_users,
            "active_employees": active_employees,
            "open_positions": open_positions,
            "turnover_rate_pct": turnover_rate,
            "overdue_tasks": overdue_tasks,
            "blocked_tasks": blocked_tasks,
            "status": people_status,
        },
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/sqdcp", response_model=APIResponse[SQDCPResponse])
async def get_sqdcp_dashboard(
    _: AllowExec,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SQDCPResponse]:
    """SQDCP (Safety, Quality, Delivery, Cost, People) executive dashboard.

    Returns the five pillars of lean manufacturing performance.
    """
    _ = _coerce_exec_role(current_user)

    resp = await _build_sqdcp_payload(db)
    roles = _roles_for_user(current_user)
    masked_resp = await mask_analytics_data(resp.model_dump(), list(roles))
    return build_response(data=masked_resp)


# ---------------------------------------------------------------------------
# Strategic Directives (AI-generated from live data)
# ---------------------------------------------------------------------------

class StrategicDirective(BaseModel):
    priority: str
    title: str
    description: str
    severity: str
    category: str


class StrategicDirectivesResponse(BaseModel):
    directives: list[StrategicDirective]
    generated_at: str


@router.get("/strategic-directives", response_model=APIResponse[StrategicDirectivesResponse])
async def get_strategic_directives(
    _: AllowExec,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StrategicDirectivesResponse]:
    """Generate strategic directives from live operational data.

    Produces priority-ordered action items for executive attention based on
    current quality, delivery, cost, and workforce signals.
    """
    _ = _coerce_exec_role(current_user)

    from sensei.services.ops.insight_generator import generate_insights

    insights = await generate_insights(db)

    # Sort by severity (critical first, then warning, then info)
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_insights = sorted(insights, key=lambda i: severity_order.get(i.get("severity", "info"), 3))

    priority_labels = ["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA"]
    directives: list[StrategicDirective] = []

    for idx, insight in enumerate(sorted_insights[:6]):
        directives.append(StrategicDirective(
            priority=priority_labels[idx] if idx < len(priority_labels) else f"P{idx + 1}",
            title=insight.get("title", "Insight"),
            description=insight.get("description", ""),
            severity=insight.get("severity", "info"),
            category=insight.get("category", "general"),
        ))

    if not directives:
        directives.append(StrategicDirective(
            priority="ALPHA",
            title="All Systems Nominal",
            description="No actionable insights detected. All operational metrics are within normal parameters.",
            severity="info",
            category="company_health",
        ))

    resp = StrategicDirectivesResponse(
        directives=directives,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return build_response(data=resp)


# ---------------------------------------------------------------------------
# Cross-Functional KPI Summary
# ---------------------------------------------------------------------------

class CrossFunctionalKPIResponse(BaseModel):
    quality_score: float
    delivery_score: float
    cost_efficiency: float
    workforce_utilization: float
    inventory_health: float
    overall_score: float
    details: dict


async def _build_kpi_summary_payload(db: DBSession) -> CrossFunctionalKPIResponse:
    """Build cross-functional KPI summary payload from live data."""
    # Quality score: penalize for open NCs and CAPAs
    open_ncs = int((await db.execute(
        select(func.count()).select_from(NonConformance).where(
            NonConformance.status == NCStatus.OPEN
        )
    )).scalar() or 0)
    critical_ncs = int((await db.execute(
        select(func.count()).select_from(NonConformance).where(
            NonConformance.severity == NCSeverity.CRITICAL
        )
    )).scalar() or 0)
    q_score = max(0.0, 100.0 - (open_ncs * 3) - (critical_ncs * 10))

    # Delivery score: based on pending shipment ratio
    pending_ship = int((await db.execute(
        select(func.count()).select_from(Shipment).where(
            Shipment.status.in_(["pending", "processing", "packed", "ready"])
        )
    )).scalar() or 0)
    completed_wos = int((await db.execute(
        select(func.count()).select_from(WorkOrder).where(
            WorkOrder.status == WorkOrderStatus.COMPLETED
        )
    )).scalar() or 0)
    d_score = max(0.0, 100.0 - (pending_ship * 5)) if completed_wos > 0 else 50.0

    # Cost efficiency: ratio of outstanding invoices to open POs + AP health
    outstanding_inv = int((await db.execute(
        select(func.count()).select_from(CustomerInvoice).where(
            CustomerInvoice.status.in_(["draft", "sent", "overdue", "partial"])
        )
    )).scalar() or 0)
    open_po = int((await db.execute(
        select(func.count()).select_from(PurchaseOrder).where(
            PurchaseOrder.status.in_(["draft", "submitted", "approved", "ordered", "partial"])
        )
    )).scalar() or 0)
    ap_unpaid = int((await db.execute(
        select(func.count()).select_from(SupplierInvoice).where(
            SupplierInvoice.status.in_(["draft", "submitted", "approved", "posted"])
        )
    )).scalar() or 0)
    c_score = 75.0
    if open_po > 0 and outstanding_inv > 0:
        ratio = outstanding_inv / open_po
        c_score = min(100.0, max(0.0, ratio * 80))
    # Penalize for high AP backlog
    c_score = max(0.0, c_score - (ap_unpaid * 2))

    # Workforce: penalize for overdue tasks + HR turnover
    overdue_tasks = int((await db.execute(
        select(func.count()).select_from(Task).where(
            and_(
                Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                Task.due_date < datetime.now(timezone.utc),
            )
        )
    )).scalar() or 0)
    active_employees = int((await db.execute(
        select(func.count()).select_from(EmployeeProfile).where(
            EmployeeProfile.status == "active"
        )
    )).scalar() or 0)
    terminated_90d = int((await db.execute(
        select(func.count()).select_from(EmployeeProfile).where(
            and_(
                EmployeeProfile.status == "terminated",
                EmployeeProfile.termination_date >= (datetime.now(timezone.utc) - timedelta(days=90)),
            )
        )
    )).scalar() or 0)
    turnover_rate = round((terminated_90d / max(active_employees, 1)) * 100, 1)
    w_score = max(0.0, 100.0 - (overdue_tasks * 4) - (turnover_rate * 2))

    # Inventory health: penalize for zero-stock and pending MRP exceptions
    zero_stock = int((await db.execute(
        select(func.count()).select_from(InventoryLevel).where(
            InventoryLevel.quantity_on_hand <= 0
        )
    )).scalar() or 0)
    pending_mrp = int((await db.execute(
        select(func.count()).select_from(MRPSuggestion).where(
            MRPSuggestion.status == "pending"
        )
    )).scalar() or 0)
    i_score = max(0.0, 100.0 - (zero_stock * 5) - (pending_mrp * 3))

    overall = round((q_score + d_score + c_score + w_score + i_score) / 5, 1)

    return CrossFunctionalKPIResponse(
        quality_score=round(q_score, 1),
        delivery_score=round(d_score, 1),
        cost_efficiency=round(c_score, 1),
        workforce_utilization=round(w_score, 1),
        inventory_health=round(i_score, 1),
        overall_score=overall,
        details={
            "open_ncs": open_ncs,
            "critical_ncs": critical_ncs,
            "pending_shipments": pending_ship,
            "completed_work_orders": completed_wos,
            "outstanding_invoice_total": outstanding_inv,
            "open_po_total": open_po,
            "ap_unpaid_total": ap_unpaid,
            "overdue_tasks": overdue_tasks,
            "active_employees": active_employees,
            "turnover_rate_pct": turnover_rate,
            "zero_stock_items": zero_stock,
            "pending_mrp_suggestions": pending_mrp,
        },
    )


@router.get("/kpi-summary", response_model=APIResponse[CrossFunctionalKPIResponse])
async def get_cross_functional_kpi_summary(
    _: AllowExec,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CrossFunctionalKPIResponse]:
    """Cross-functional KPI summary scored 0-100 for each pillar."""
    _ = _coerce_exec_role(current_user)

    resp = await _build_kpi_summary_payload(db)
    return build_response(data=resp)


class DataThreadSummary(BaseModel):
    latest_snapshot_date: str | None
    exported_record_count: int
    fact_counts: dict[str, int]
    lineage_link_count: int
    reasoning_trace_count: int
    event_bus: dict[str, Any]
    cross_domain: dict[str, Any]


class CEODashboardResponse(BaseModel):
    data_thread: DataThreadSummary
    sqdcp: SQDCPResponse
    kpi_summary: CrossFunctionalKPIResponse
    insights: list[dict[str, Any]]
    cognitive_obeya: dict[str, Any] | None = None
    generated_at: str


async def _build_data_thread_summary(
    db: DBSession,
    actor_roles: Iterable[str],
) -> DataThreadSummary:
    warehouse = AnalyticsWarehouseService()
    snapshot = await warehouse.get_latest_snapshot(db, actor_roles=actor_roles)
    snapshot_id = snapshot.id if snapshot else None
    fact_counts = await warehouse.get_role_scoped_fact_counts(
        db,
        actor_roles=actor_roles,
        snapshot_id=snapshot_id,
    )
    exported_count = sum(fact_counts.values())

    lineage_count = int((await db.execute(
        select(func.count()).select_from(DataLineageLink)
    )).scalar() or 0)
    reasoning_count = int((await db.execute(
        select(func.count()).select_from(ReasoningTrace)
    )).scalar() or 0)

    cross_domain = await warehouse.build_cross_domain_summary(
        db, actor_roles=actor_roles,
    )

    return DataThreadSummary(
        latest_snapshot_date=snapshot.snapshot_date.isoformat() if snapshot else None,
        exported_record_count=exported_count,
        fact_counts=fact_counts,
        lineage_link_count=lineage_count,
        reasoning_trace_count=reasoning_count,
        event_bus=await event_bus.get_stats_async(),
        cross_domain=cross_domain,
    )


@router.get("/ceo-dashboard", response_model=APIResponse[CEODashboardResponse])
async def get_ceo_dashboard(
    _: AllowExec,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CEODashboardResponse]:
    """Unified CEO dashboard driven by the single data thread."""
    roles = _roles_for_user(current_user)
    audit_logger = get_insight_audit_logger()

    sqdcp = await _build_sqdcp_payload(db)
    kpi_summary = await _build_kpi_summary_payload(db)
    insights = await generate_insights(db)
    filtered = filter_insights_for_role(insights, list(roles))
    masked = await mask_analytics_data(filtered, list(roles))

    # Audit: Log batch insight filter for CEO dashboard
    removed_categories = list(set(
        i.get("category", "unknown") for i in insights
    ) - set(
        i.get("category", "unknown") for i in filtered
    ))
    
    audit_logger.log_batch_filter(
        user_id=str(current_user.id),
        user_roles=list(roles),
        total_insights=len(insights),
        filtered_count=len(filtered),
        removed_categories=removed_categories,
        endpoint="/api/v1/executive/ceo-dashboard",
    )

    data_thread = await _build_data_thread_summary(db, roles)

    # Cognitive Obeya integration — surface trend warnings & causal links
    cognitive_summary: dict[str, Any] | None = None
    try:
        analyzer = AsyncPrescriptiveMetricAnalyzer()
        warnings = await analyzer.get_all_warnings(db)
        cognitive_summary = {
            "trend_warnings": [
                {
                    "metric_id": w.metric_id,
                    "direction": w.direction.value if hasattr(w.direction, "value") else str(w.direction),
                    "days_to_breach": w.days_to_breach,
                    "confidence": w.confidence,
                    "recommendation": w.recommendation,
                }
                for w in warnings[:10]  # top 10 most recent
            ],
            "warning_count": len(warnings),
        }
    except Exception:
        cognitive_summary = None

    return build_response(
        data=CEODashboardResponse(
            data_thread=data_thread,
            sqdcp=sqdcp,
            kpi_summary=kpi_summary,
            insights=masked,
            cognitive_obeya=cognitive_summary,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    )


# ---------------------------------------------------------------------------
# Revenue Waterfall — aggregates revenue through Quote → SO → Invoice stages
# ---------------------------------------------------------------------------

class WaterfallStage(BaseModel):
    stage: str
    label: str
    value: float = 0.0
    count: int = 0


class RevenueWaterfallResponse(BaseModel):
    stages: list[WaterfallStage] = Field(default_factory=list)
    total_quoted: float = 0.0
    total_ordered: float = 0.0
    total_invoiced: float = 0.0
    conversion_rate: float | None = None


@router.get("/revenue-waterfall", response_model=APIResponse[RevenueWaterfallResponse])
async def get_revenue_waterfall(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RevenueWaterfallResponse]:
    """Revenue waterfall: Quote → SalesOrder → Invoice pipeline.

    Aggregates totals at each stage from real database data.
    """
    # Quoted value (sum of Quote.total for non-cancelled quotes)
    quoted_res = (await db.execute(
        select(
            func.coalesce(func.sum(Quote.total), 0),
            func.count(),
        ).where(Quote.status != QuoteStatus.CANCELLED.value)
    )).one()
    total_quoted = float(quoted_res[0])
    quote_count = int(quoted_res[1])

    # Won/accepted quotes
    won_res = (await db.execute(
        select(
            func.coalesce(func.sum(Quote.total), 0),
            func.count(),
        ).where(Quote.status == QuoteStatus.ACCEPTED.value)
    )).one()
    total_won = float(won_res[0])
    won_count = int(won_res[1])

    # Sales-order value (sum of line quantity × unit_price)
    so_res = (await db.execute(
        select(
            func.coalesce(func.sum(SalesOrderLine.quantity * SalesOrderLine.unit_price), 0),
            func.count(func.distinct(SalesOrderLine.so_id)),
        )
    )).one()
    total_ordered = float(so_res[0])
    so_count = int(so_res[1])

    # Invoice value (sum of line quantity × unit_price)
    inv_res = (await db.execute(
        select(
            func.coalesce(func.sum(CustomerInvoiceLine.quantity * CustomerInvoiceLine.unit_price), 0),
            func.count(func.distinct(CustomerInvoiceLine.invoice_id)),
        )
    )).one()
    total_invoiced = float(inv_res[0])
    inv_count = int(inv_res[1])

    stages = [
        WaterfallStage(stage="quoted", label="Total Quoted", value=total_quoted, count=quote_count),
        WaterfallStage(stage="won", label="Won Quotes", value=total_won, count=won_count),
        WaterfallStage(stage="ordered", label="Sales Orders", value=total_ordered, count=so_count),
        WaterfallStage(stage="invoiced", label="Invoiced", value=total_invoiced, count=inv_count),
    ]

    conversion_rate = None
    if total_quoted > 0:
        conversion_rate = round(total_invoiced / total_quoted * 100, 1)

    return build_response(data=await mask_analytics_data(
        RevenueWaterfallResponse(
            stages=stages,
            total_quoted=total_quoted,
            total_ordered=total_ordered,
            total_invoiced=total_invoiced,
            conversion_rate=conversion_rate,
        ).model_dump(),
        list(_roles_for_user(current_user)),
    ))


# ---------------------------------------------------------------------------
# Margin Analysis — uses Quote margin fields and line-item costs
# ---------------------------------------------------------------------------

class MarginBucket(BaseModel):
    bucket: str
    count: int = 0
    avg_margin: float = 0.0
    total_revenue: float = 0.0
    total_cost: float = 0.0


class MarginAnalysisResponse(BaseModel):
    overall_target_margin: float | None = None
    overall_actual_margin: float | None = None
    margin_gap: float | None = None
    quote_count: int = 0
    buckets: list[MarginBucket] = Field(default_factory=list)
    top_margin_products: list[dict[str, Any]] = Field(default_factory=list)
    bottom_margin_products: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/margin-analysis", response_model=APIResponse[MarginAnalysisResponse])
async def get_margin_analysis(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MarginAnalysisResponse]:
    """Margin analysis from Quote.actual_margin, target_margin, and line-item costs.

    Provides overall margin stats, margin-bucket distribution, and
    top/bottom-margin products from QuoteLineItem data.
    """
    # Overall margin from quotes that have actual_margin set
    margin_res = (await db.execute(
        select(
            func.avg(Quote.target_margin),
            func.avg(Quote.actual_margin),
            func.count(),
        ).where(Quote.actual_margin.isnot(None))
    )).one()

    overall_target = float(margin_res[0]) if margin_res[0] is not None else None
    overall_actual = float(margin_res[1]) if margin_res[1] is not None else None
    quote_count = int(margin_res[2])

    margin_gap = None
    if overall_target is not None and overall_actual is not None:
        margin_gap = round(overall_actual - overall_target, 2)

    # Margin-bucket distribution
    buckets: list[MarginBucket] = []
    bucket_ranges = [
        ("negative", None, 0),
        ("0-10%", 0, 10),
        ("10-20%", 10, 20),
        ("20-30%", 20, 30),
        ("30%+", 30, None),
    ]
    for label, low, high in bucket_ranges:
        conditions = [Quote.actual_margin.isnot(None)]
        if low is not None:
            conditions.append(Quote.actual_margin >= low)
        if high is not None:
            conditions.append(Quote.actual_margin < high)
        row = (await db.execute(
            select(
                func.count(),
                func.coalesce(func.avg(Quote.actual_margin), 0),
                func.coalesce(func.sum(Quote.total), 0),
                func.coalesce(func.sum(Quote.total_cost), 0),
            ).where(and_(*conditions))
        )).one()
        buckets.append(MarginBucket(
            bucket=label,
            count=int(row[0]),
            avg_margin=round(float(row[1]), 2),
            total_revenue=float(row[2]),
            total_cost=float(row[3]),
        ))

    # Top 5 and bottom 5 margin products from QuoteLineItem
    top_products: list[dict[str, Any]] = []
    bottom_products: list[dict[str, Any]] = []

    top_rows = (await db.execute(
        select(
            QuoteLineItem.product_name,
            func.avg(QuoteLineItem.margin_percentage),
            func.sum(QuoteLineItem.line_total),
            func.count(),
        ).where(
            QuoteLineItem.margin_percentage.isnot(None),
            QuoteLineItem.product_name.isnot(None),
        ).group_by(QuoteLineItem.product_name)
        .order_by(func.avg(QuoteLineItem.margin_percentage).desc())
        .limit(5)
    )).all()
    for r in top_rows:
        top_products.append({
            "product": r[0],
            "avg_margin": round(float(r[1]), 2),
            "total_revenue": float(r[2] or 0),
            "line_count": int(r[3]),
        })

    bottom_rows = (await db.execute(
        select(
            QuoteLineItem.product_name,
            func.avg(QuoteLineItem.margin_percentage),
            func.sum(QuoteLineItem.line_total),
            func.count(),
        ).where(
            QuoteLineItem.margin_percentage.isnot(None),
            QuoteLineItem.product_name.isnot(None),
        ).group_by(QuoteLineItem.product_name)
        .order_by(func.avg(QuoteLineItem.margin_percentage).asc())
        .limit(5)
    )).all()
    for r in bottom_rows:
        bottom_products.append({
            "product": r[0],
            "avg_margin": round(float(r[1]), 2),
            "total_revenue": float(r[2] or 0),
            "line_count": int(r[3]),
        })

    return build_response(data=await mask_analytics_data(
        MarginAnalysisResponse(
            overall_target_margin=round(overall_target, 2) if overall_target is not None else None,
            overall_actual_margin=round(overall_actual, 2) if overall_actual is not None else None,
            margin_gap=margin_gap,
            quote_count=quote_count,
            buckets=buckets,
            top_margin_products=top_products,
            bottom_margin_products=bottom_products,
        ).model_dump(),
        list(_roles_for_user(current_user)),
    ))
"""Common Thread genealogy endpoints.

Exposes deterministic trace retrieval across modules by combining:
- data lineage graph
- reasoning IDs attached to entities

Also supports explicit binding of entities across the full thread:
  Opportunity -> RFQ -> Quote -> SalesOrder -> WorkOrder -> NC -> CAPA
                                                          -> Shipment -> Invoice
Plus: PO -> WO (material sourcing), Andon -> CAPA (recurrence), Andon -> WO (disruption).

Impact analysis endpoint aggregates cost/revenue data traversing the thread.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import CurrentUser, DBSession, RoleChecker
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.services.core.common_thread import get_common_thread_service
from sensei.models.work_order import WorkOrder
from sensei.models.quote import Quote, QuoteLineItem
from sensei.models.accounts_receivable import CustomerInvoice, CustomerInvoiceLine, SalesOrder, SalesOrderLine
from sensei.models.accounts_payable import PurchaseOrder, POLine
from sensei.models.quality import NonConformance

router = APIRouter(
    dependencies=[Depends(RoleChecker(["admin", "ceo", "gm", "exec", "ops", "quality", "finance", "auditor"]))],
)


class CommonThreadNodeResponse(BaseModel):
    entity_type: str
    entity_id: str
    reasoning_ids: list[str] = Field(default_factory=list)


class CommonThreadEdgeResponse(BaseModel):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship_type: str


class CommonThreadTraceResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    nodes: list[CommonThreadNodeResponse]
    edges: list[CommonThreadEdgeResponse]


class CommonThreadBindRequest(BaseModel):
    rfq_id: str | None = None
    quote_id: str | None = None
    work_order_id: str | None = None
    non_conformance_id: str | None = None
    shipment_id: str | None = None
    invoice_id: str | None = None
    sales_order_id: str | None = None
    purchase_order_id: str | None = None
    andon_event_id: str | None = None
    capa_id: str | None = None
    opportunity_id: str | None = None

    source: str | None = Field(default="api")


@router.get("/trace", response_model=APIResponse[CommonThreadTraceResponse])
async def get_common_thread_trace(
    db: DBSession,
    current_user: CurrentUser,  # noqa: ARG001
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(3, ge=0, le=10),
) -> APIResponse[CommonThreadTraceResponse]:
    trace = await get_common_thread_service().get_trace(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    resp = CommonThreadTraceResponse(
        root_entity_type=trace.root_entity_type,
        root_entity_id=trace.root_entity_id,
        nodes=[
            CommonThreadNodeResponse(
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                reasoning_ids=n.reasoning_ids,
            )
            for n in trace.nodes
        ],
        edges=[
            CommonThreadEdgeResponse(
                source_entity_type=e.source_entity_type,
                source_entity_id=e.source_entity_id,
                target_entity_type=e.target_entity_type,
                target_entity_id=e.target_entity_id,
                relationship_type=e.relationship_type,
            )
            for e in trace.edges
        ],
    )

    return build_response(data=resp)


@router.post("/bind", response_model=APIResponse[dict])
async def bind_common_thread(
    req: CommonThreadBindRequest,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[dict]:
    await get_common_thread_service().bind(
        db,
        rfq_id=req.rfq_id,
        quote_id=req.quote_id,
        work_order_id=req.work_order_id,
        non_conformance_id=req.non_conformance_id,
        shipment_id=req.shipment_id,
        invoice_id=req.invoice_id,
        sales_order_id=req.sales_order_id,
        purchase_order_id=req.purchase_order_id,
        andon_event_id=req.andon_event_id,
        capa_id=req.capa_id,
        opportunity_id=req.opportunity_id,
        created_by_id=current_user.id,
        reasoning_id=x_reasoning_id,
        source=req.source,
    )
    await db.commit()
    return build_response(data={"bound": True})


# ---------------------------------------------------------------------------
# Impact Analysis
# ---------------------------------------------------------------------------

class ImpactBreakdown(BaseModel):
    entity_type: str
    entity_id: str
    label: str
    value: float = 0.0


class ImpactAnalysisResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    total_thread_entities: int
    entity_types_found: list[str]
    quote_value: float | None = None
    work_order_cost: float | None = None
    invoice_total: float | None = None
    po_total: float | None = None
    nc_count: int = 0
    estimated_cost_of_quality: float = 0.0
    breakdown: list[ImpactBreakdown] = Field(default_factory=list)


@router.get("/impact", response_model=APIResponse[ImpactAnalysisResponse])
async def get_impact_analysis(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(5, ge=1, le=10),
) -> APIResponse[ImpactAnalysisResponse]:
    """Trace an entity through the common thread and aggregate financial impact.

    Starting from any entity (e.g. a work order or NC), walks the lineage graph
    and pulls cost/revenue data from every connected entity.
    """
    trace = await get_common_thread_service().get_trace(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    # Group node IDs by entity type
    by_type: dict[str, list[str]] = {}
    for n in trace.nodes:
        by_type.setdefault(n.entity_type, []).append(n.entity_id)

    breakdown: list[ImpactBreakdown] = []
    quote_value: float | None = None
    wo_cost: float | None = None
    invoice_total: float | None = None
    po_total: float | None = None
    nc_count: int = 0

    # Aggregate quote values
    if "quote" in by_type:
        for qid in by_type["quote"]:
            try:
                row = (await db.execute(
                    select(Quote.total).where(Quote.id == qid)
                )).scalar()
                val = float(row or 0)
                if val:
                    quote_value = (quote_value or 0) + val
                    breakdown.append(ImpactBreakdown(
                        entity_type="quote", entity_id=qid,
                        label="Quote Value", value=val,
                    ))
            except Exception:
                pass

    # Count work orders in lineage (no cost field on WO model)
    if "work_order" in by_type:
        wo_count = len(by_type["work_order"])
        if wo_count:
            breakdown.append(ImpactBreakdown(
                entity_type="work_order", entity_id=by_type["work_order"][0],
                label="Work Orders in Lineage", value=float(wo_count),
            ))

    # Aggregate invoice totals (sum line quantity * unit_price)
    if "invoice" in by_type:
        for iid in by_type["invoice"]:
            try:
                row = (await db.execute(
                    select(func.coalesce(
                        func.sum(CustomerInvoiceLine.quantity * CustomerInvoiceLine.unit_price), 0
                    )).where(CustomerInvoiceLine.invoice_id == iid)
                )).scalar()
                val = float(row or 0)
                if val:
                    invoice_total = (invoice_total or 0) + val
                    breakdown.append(ImpactBreakdown(
                        entity_type="invoice", entity_id=iid,
                        label="Invoice Total", value=val,
                    ))
            except Exception:
                pass

    # Aggregate PO totals (sum line quantity * unit_price)
    if "purchase_order" in by_type:
        for pid in by_type["purchase_order"]:
            try:
                row = (await db.execute(
                    select(func.coalesce(
                        func.sum(POLine.quantity * POLine.unit_price), 0
                    )).where(POLine.po_id == pid)
                )).scalar()
                val = float(row or 0)
                if val:
                    po_total = (po_total or 0) + val
                    breakdown.append(ImpactBreakdown(
                        entity_type="purchase_order", entity_id=pid,
                        label="PO Total", value=val,
                    ))
            except Exception:
                pass

    # Count NCs and estimate cost of quality (heuristic: each NC ~ avg rework cost)
    if "non_conformance" in by_type:
        nc_count = len(by_type["non_conformance"])

    # Estimated cost of quality: NCs × average rework cost factor ($500 default)
    estimated_coq = nc_count * 500.0

    resp = ImpactAnalysisResponse(
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        total_thread_entities=len(trace.nodes),
        entity_types_found=sorted(by_type.keys()),
        quote_value=quote_value,
        work_order_cost=wo_cost,
        invoice_total=invoice_total,
        po_total=po_total,
        nc_count=nc_count,
        estimated_cost_of_quality=estimated_coq,
        breakdown=breakdown,
    )
    return build_response(data=resp)


# ---------------------------------------------------------------------------
# Cost Trace — follows a lineage thread and aggregates cost at each stage
# ---------------------------------------------------------------------------

class CostTraceStage(BaseModel):
    stage: str
    entity_type: str
    entity_id: str
    cost: float = 0.0
    label: str = ""


class CostTraceResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    stages: list[CostTraceStage] = Field(default_factory=list)
    total_cost: float = 0.0
    total_revenue: float = 0.0
    margin: float | None = None


@router.get("/cost-trace", response_model=APIResponse[CostTraceResponse])
async def get_cost_trace(
    db: DBSession,
    current_user: CurrentUser,  # noqa: ARG001
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(5, ge=1, le=10),
) -> APIResponse[CostTraceResponse]:
    """Trace cost flow through the manufacturing chain.

    Walks the lineage graph starting from any entity and aggregates cost/revenue
    at each stage: Quote → PO → WO → Invoice.
    """
    trace = await get_common_thread_service().get_trace(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    by_type: dict[str, list[str]] = {}
    for n in trace.nodes:
        by_type.setdefault(n.entity_type, []).append(n.entity_id)

    stages: list[CostTraceStage] = []
    total_cost: float = 0.0
    total_revenue: float = 0.0

    # 1) Quote cost
    if "quote" in by_type:
        for qid in by_type["quote"]:
            try:
                row = (await db.execute(
                    select(Quote.total_cost, Quote.total).where(Quote.id == qid)
                )).one_or_none()
                if row:
                    cost = float(row[0] or 0)
                    rev = float(row[1] or 0)
                    total_cost += cost
                    total_revenue += rev
                    stages.append(CostTraceStage(
                        stage="quote", entity_type="quote", entity_id=qid,
                        cost=cost, label=f"Quote cost ≈ {cost:,.2f}",
                    ))
            except Exception:
                pass

    # 2) PO cost
    if "purchase_order" in by_type:
        for pid in by_type["purchase_order"]:
            try:
                val = (await db.execute(
                    select(func.coalesce(
                        func.sum(POLine.quantity * POLine.unit_price), 0
                    )).where(POLine.po_id == pid)
                )).scalar() or 0
                cost = float(val)
                total_cost += cost
                stages.append(CostTraceStage(
                    stage="purchasing", entity_type="purchase_order", entity_id=pid,
                    cost=cost, label=f"PO material cost {cost:,.2f}",
                ))
            except Exception:
                pass

    # 3) WO (count only — model has no cost column)
    if "work_order" in by_type:
        for wid in by_type["work_order"]:
            stages.append(CostTraceStage(
                stage="production", entity_type="work_order", entity_id=wid,
                cost=0, label="Work Order (no cost field)",
            ))

    # 4) Invoice revenue
    if "invoice" in by_type:
        for iid in by_type["invoice"]:
            try:
                val = (await db.execute(
                    select(func.coalesce(
                        func.sum(CustomerInvoiceLine.quantity * CustomerInvoiceLine.unit_price), 0
                    )).where(CustomerInvoiceLine.invoice_id == iid)
                )).scalar() or 0
                rev = float(val)
                total_revenue += rev
                stages.append(CostTraceStage(
                    stage="invoicing", entity_type="invoice", entity_id=iid,
                    cost=rev, label=f"Invoice total {rev:,.2f}",
                ))
            except Exception:
                pass

    margin = None
    if total_revenue > 0:
        margin = round((total_revenue - total_cost) / total_revenue * 100, 2)

    return build_response(data=CostTraceResponse(
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        stages=stages,
        total_cost=total_cost,
        total_revenue=total_revenue,
        margin=margin,
    ))


# ---------------------------------------------------------------------------
# Timeline — chronological events across a lineage thread
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    entity_type: str
    entity_id: str
    event: str
    timestamp: str | None = None
    detail: str = ""


class TimelineResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    events: list[TimelineEvent] = Field(default_factory=list)


@router.get("/timeline", response_model=APIResponse[TimelineResponse])
async def get_thread_timeline(
    db: DBSession,
    current_user: CurrentUser,  # noqa: ARG001
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(5, ge=1, le=10),
) -> APIResponse[TimelineResponse]:
    """Return a chronological timeline of events across a lineage thread.

    Aggregates created_at / status-change timestamps from each entity in the
    traced thread and sorts them chronologically.
    """
    trace = await get_common_thread_service().get_trace(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    by_type: dict[str, list[str]] = {}
    for n in trace.nodes:
        by_type.setdefault(n.entity_type, []).append(n.entity_id)

    events: list[TimelineEvent] = []

    # Quotes
    if "quote" in by_type:
        for qid in by_type["quote"]:
            try:
                row = (await db.execute(
                    select(Quote.created_at, Quote.status, Quote.sent_at, Quote.accepted_at).where(Quote.id == qid)
                )).one_or_none()
                if row:
                    events.append(TimelineEvent(
                        entity_type="quote", entity_id=qid,
                        event="created", timestamp=str(row[0]) if row[0] else None,
                        detail=f"Status: {row[1]}",
                    ))
                    if row[2]:
                        events.append(TimelineEvent(
                            entity_type="quote", entity_id=qid,
                            event="sent", timestamp=str(row[2]),
                        ))
                    if row[3]:
                        events.append(TimelineEvent(
                            entity_type="quote", entity_id=qid,
                            event="accepted", timestamp=str(row[3]),
                        ))
            except Exception:
                pass

    # Work orders
    if "work_order" in by_type:
        for wid in by_type["work_order"]:
            try:
                row = (await db.execute(
                    select(
                        WorkOrder.created_at, WorkOrder.status,
                        WorkOrder.actual_start, WorkOrder.actual_end,
                    ).where(WorkOrder.id == int(wid) if wid.isdigit() else WorkOrder.work_order_number == wid)
                )).one_or_none()
                if row:
                    events.append(TimelineEvent(
                        entity_type="work_order", entity_id=wid,
                        event="created", timestamp=str(row[0]) if row[0] else None,
                        detail=f"Status: {row[1].value if hasattr(row[1], 'value') else row[1]}",
                    ))
                    if row[2]:
                        events.append(TimelineEvent(
                            entity_type="work_order", entity_id=wid,
                            event="started", timestamp=str(row[2]),
                        ))
                    if row[3]:
                        events.append(TimelineEvent(
                            entity_type="work_order", entity_id=wid,
                            event="completed", timestamp=str(row[3]),
                        ))
            except Exception:
                pass

    # Invoices
    if "invoice" in by_type:
        for iid in by_type["invoice"]:
            try:
                row = (await db.execute(
                    select(CustomerInvoice.created_at, CustomerInvoice.status).where(CustomerInvoice.id == iid)
                )).one_or_none()
                if row:
                    events.append(TimelineEvent(
                        entity_type="invoice", entity_id=iid,
                        event="created", timestamp=str(row[0]) if row[0] else None,
                        detail=f"Status: {row[1]}",
                    ))
            except Exception:
                pass

    # POs
    if "purchase_order" in by_type:
        for pid in by_type["purchase_order"]:
            try:
                row = (await db.execute(
                    select(PurchaseOrder.created_at, PurchaseOrder.status).where(PurchaseOrder.id == pid)
                )).one_or_none()
                if row:
                    events.append(TimelineEvent(
                        entity_type="purchase_order", entity_id=pid,
                        event="created", timestamp=str(row[0]) if row[0] else None,
                        detail=f"Status: {row[1]}",
                    ))
            except Exception:
                pass

    # NCs
    if "non_conformance" in by_type:
        for nid in by_type["non_conformance"]:
            try:
                row = (await db.execute(
                    select(NonConformance.created_at, NonConformance.status).where(NonConformance.id == nid)
                )).one_or_none()
                if row:
                    events.append(TimelineEvent(
                        entity_type="non_conformance", entity_id=nid,
                        event="created", timestamp=str(row[0]) if row[0] else None,
                        detail=f"Status: {row[1].value if hasattr(row[1], 'value') else row[1]}",
                    ))
            except Exception:
                pass

    # Sort by timestamp (None last)
    events.sort(key=lambda e: e.timestamp or "9999")

    return build_response(data=TimelineResponse(
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        events=events,
    ))
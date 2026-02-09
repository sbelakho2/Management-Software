"""Common Thread Genealogy Binding.

Provides deterministic integrity binding across modules:
RFQ -> Quote -> Production (Work Orders) -> Quality (NCs) -> Shipping/Invoice.

Extended to support HR module bindings:
Employee -> Work Order (labor booking)
Employee -> Training Record (skill verification)
Employee -> Leave Request (capacity planning)
Employee -> Performance Review (A3/OEE integration)

This module focuses on two things:
1) ensuring lineage edges exist between stages (DataLineageService)
2) ensuring each entity is tagged with a Reasoning ID (ReasoningTrace)

No LLM calls; safe for best-effort endpoint enrichment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.reasoning_trace import ReasoningTrace
from sensei.services.core.data_lineage import DataLineageService, LineageGraph


@dataclass(frozen=True)
class CommonThreadNode:
    entity_type: str
    entity_id: str
    reasoning_ids: list[str]


@dataclass(frozen=True)
class CommonThreadEdge:
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship_type: str


@dataclass(frozen=True)
class CommonThreadTrace:
    root_entity_type: str
    root_entity_id: str
    nodes: list[CommonThreadNode]
    edges: list[CommonThreadEdge]


class CommonThreadService:
    def __init__(self, lineage_service: DataLineageService | None = None) -> None:
        self._lineage = lineage_service or DataLineageService()

    async def record_reasoning(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: Any,
        reasoning_id: str,
        created_by_id: Any | None = None,
        source: str | None = None,
    ) -> None:
        if not reasoning_id:
            return

        et = entity_type.strip().lower()
        eid = str(entity_id)

        existing = await db.execute(
            select(ReasoningTrace).where(
                ReasoningTrace.entity_type == et,
                ReasoningTrace.entity_id == eid,
                ReasoningTrace.reasoning_id == reasoning_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return

        tr = ReasoningTrace(
            entity_type=et,
            entity_id=eid,
            reasoning_id=reasoning_id,
            source=source,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.add(tr)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()

    async def bind(
        self,
        db: AsyncSession,
        *,
        rfq_id: Any | None = None,
        quote_id: Any | None = None,
        work_order_id: Any | None = None,
        non_conformance_id: Any | None = None,
        shipment_id: Any | None = None,
        invoice_id: Any | None = None,
        sales_order_id: Any | None = None,
        purchase_order_id: Any | None = None,
        goods_receipt_id: Any | None = None,
        inventory_move_id: Any | None = None,
        andon_event_id: Any | None = None,
        capa_id: Any | None = None,
        opportunity_id: Any | None = None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
        source: str | None = None,
    ) -> None:
        """Create best-effort lineage links across the common thread stages.

        Full thread:
        Opportunity -> RFQ -> Quote -> SalesOrder -> WorkOrder -> NC -> Shipment -> Invoice
        Plus cross-links: NC -> CAPA, Andon -> CAPA, Quote -> Opportunity, PO -> WorkOrder.
        Supply chain links: PO -> GoodsReceipt -> InventoryMove.
        """

        def _id(x: Any | None) -> str | None:
            return None if x is None else str(x)

        # Opportunity -> RFQ
        if opportunity_id is not None and rfq_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="opportunity",
                source_entity_id=_id(opportunity_id),
                relationship_type="has_rfq",
                target_entity_type="rfq",
                target_entity_id=_id(rfq_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # RFQ -> Quote
        if rfq_id is not None and quote_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="rfq",
                source_entity_id=_id(rfq_id),
                relationship_type="has_quote",
                target_entity_type="quote",
                target_entity_id=_id(quote_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Quote -> Sales Order (revenue linkage)
        if quote_id is not None and sales_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="quote",
                source_entity_id=_id(quote_id),
                relationship_type="has_sales_order",
                target_entity_type="sales_order",
                target_entity_id=_id(sales_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Quote -> Work Order
        if quote_id is not None and work_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="quote",
                source_entity_id=_id(quote_id),
                relationship_type="has_work_order",
                target_entity_type="work_order",
                target_entity_id=_id(work_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Sales Order -> Work Order
        if sales_order_id is not None and work_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="sales_order",
                source_entity_id=_id(sales_order_id),
                relationship_type="has_work_order",
                target_entity_type="work_order",
                target_entity_id=_id(work_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Work Order -> Non Conformance
        if work_order_id is not None and non_conformance_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="work_order",
                source_entity_id=_id(work_order_id),
                relationship_type="has_non_conformance",
                target_entity_type="non_conformance",
                target_entity_id=_id(non_conformance_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Non Conformance -> CAPA (escalation)
        if non_conformance_id is not None and capa_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="non_conformance",
                source_entity_id=_id(non_conformance_id),
                relationship_type="escalated_to_capa",
                target_entity_type="capa",
                target_entity_id=_id(capa_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Andon Event -> CAPA (recurrence-triggered CAPA)
        if andon_event_id is not None and capa_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="andon_event",
                source_entity_id=_id(andon_event_id),
                relationship_type="triggered_capa",
                target_entity_type="capa",
                target_entity_id=_id(capa_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Andon Event -> Work Order (production disruption link)
        if andon_event_id is not None and work_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="andon_event",
                source_entity_id=_id(andon_event_id),
                relationship_type="disrupted_work_order",
                target_entity_type="work_order",
                target_entity_id=_id(work_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Purchase Order -> Work Order (material sourcing)
        if purchase_order_id is not None and work_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="purchase_order",
                source_entity_id=_id(purchase_order_id),
                relationship_type="supplies_material_for",
                target_entity_type="work_order",
                target_entity_id=_id(work_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Purchase Order -> Goods Receipt (receiving)
        if purchase_order_id is not None and goods_receipt_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="purchase_order",
                source_entity_id=_id(purchase_order_id),
                relationship_type="has_goods_receipt",
                target_entity_type="goods_receipt",
                target_entity_id=_id(goods_receipt_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Goods Receipt -> Inventory Move (stock update)
        if goods_receipt_id is not None and inventory_move_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="goods_receipt",
                source_entity_id=_id(goods_receipt_id),
                relationship_type="created_stock_move",
                target_entity_type="inventory_move",
                target_entity_id=_id(inventory_move_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Work Order -> Shipment (shipping module may be external)
        if work_order_id is not None and shipment_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="work_order",
                source_entity_id=_id(work_order_id),
                relationship_type="has_shipment",
                target_entity_type="shipment",
                target_entity_id=_id(shipment_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Shipment -> Invoice (optional)
        if shipment_id is not None and invoice_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="shipment",
                source_entity_id=_id(shipment_id),
                relationship_type="has_invoice",
                target_entity_type="invoice",
                target_entity_id=_id(invoice_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Sales Order -> Invoice (revenue recognition)
        if sales_order_id is not None and invoice_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="sales_order",
                source_entity_id=_id(sales_order_id),
                relationship_type="has_invoice",
                target_entity_type="invoice",
                target_entity_id=_id(invoice_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "common_thread"},
            )

        # Reasoning trace stamping
        if reasoning_id:
            for et, eid in (
                ("opportunity", opportunity_id),
                ("rfq", rfq_id),
                ("quote", quote_id),
                ("sales_order", sales_order_id),
                ("work_order", work_order_id),
                ("non_conformance", non_conformance_id),
                ("capa", capa_id),
                ("andon_event", andon_event_id),
                ("purchase_order", purchase_order_id),
                ("goods_receipt", goods_receipt_id),
                ("inventory_move", inventory_move_id),
                ("shipment", shipment_id),
                ("invoice", invoice_id),
            ):
                if eid is not None:
                    await self.record_reasoning(
                        db,
                        entity_type=et,
                        entity_id=_id(eid),
                        reasoning_id=reasoning_id,
                        created_by_id=created_by_id,
                        source=source,
                    )

    async def bind_hr(
        self,
        db: AsyncSession,
        *,
        employee_id: Any | None = None,
        work_order_id: Any | None = None,
        training_record_id: Any | None = None,
        leave_request_id: Any | None = None,
        performance_review_id: Any | None = None,
        labor_booking_id: Any | None = None,
        hr_case_id: Any | None = None,
        timecard_id: Any | None = None,
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
        source: str | None = None,
    ) -> None:
        """Create best-effort lineage links for HR module entities.
        
        Connects HR data to the production common thread:
        - Employee -> Work Order (labor booking linkage)
        - Employee -> Training Record (skill verification)
        - Employee -> Leave Request (capacity planning)
        - Employee -> Performance Review (A3/OEE integration)
        - Employee -> HR Case (disciplinary/grievance tracking)
        - Employee -> Timecard (time & attendance)
        """

        def _id(x: Any | None) -> str | None:
            return None if x is None else str(x)

        # Employee -> Work Order (labor booking)
        if employee_id is not None and work_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="worked_on",
                target_entity_type="work_order",
                target_entity_id=_id(work_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Employee -> Labor Booking (direct time tracking)
        if employee_id is not None and labor_booking_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="has_labor_booking",
                target_entity_type="labor_booking",
                target_entity_id=_id(labor_booking_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Labor Booking -> Work Order (cost attribution)
        if labor_booking_id is not None and work_order_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="labor_booking",
                source_entity_id=_id(labor_booking_id),
                relationship_type="charged_to",
                target_entity_type="work_order",
                target_entity_id=_id(work_order_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Employee -> Training Record (skill verification)
        if employee_id is not None and training_record_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="has_training",
                target_entity_type="training_record",
                target_entity_id=_id(training_record_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Employee -> Leave Request (capacity planning)
        if employee_id is not None and leave_request_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="has_leave_request",
                target_entity_type="leave_request",
                target_entity_id=_id(leave_request_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Employee -> Performance Review (A3/OEE integration)
        if employee_id is not None and performance_review_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="has_performance_review",
                target_entity_type="performance_review",
                target_entity_id=_id(performance_review_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Employee -> HR Case (disciplinary/grievance)
        if employee_id is not None and hr_case_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="has_hr_case",
                target_entity_type="hr_case",
                target_entity_id=_id(hr_case_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Employee -> Timecard (time & attendance)
        if employee_id is not None and timecard_id is not None:
            await self._lineage.link(
                db,
                source_entity_type="employee",
                source_entity_id=_id(employee_id),
                relationship_type="has_timecard",
                target_entity_type="timecard",
                target_entity_id=_id(timecard_id),
                created_by_id=created_by_id,
                reasoning_id=reasoning_id,
                metadata={"source": source or "hr_common_thread"},
            )

        # Reasoning trace stamping for HR entities
        if reasoning_id:
            for et, eid in (
                ("employee", employee_id),
                ("work_order", work_order_id),
                ("training_record", training_record_id),
                ("leave_request", leave_request_id),
                ("performance_review", performance_review_id),
                ("labor_booking", labor_booking_id),
                ("hr_case", hr_case_id),
                ("timecard", timecard_id),
            ):
                if eid is not None:
                    await self.record_reasoning(
                        db,
                        entity_type=et,
                        entity_id=_id(eid),
                        reasoning_id=reasoning_id,
                        created_by_id=created_by_id,
                        source=source,
                    )

    async def get_trace(
        self,
        db: AsyncSession,
        *,
        root_entity_type: str,
        root_entity_id: Any,
        max_depth: int = 3,
    ) -> CommonThreadTrace:
        graph = await self._lineage.get_graph(
            db,
            root_entity_type=root_entity_type,
            root_entity_id=root_entity_id,
            max_depth=max_depth,
        )

        reasoning_map = await self._get_reasoning_map(db, graph)

        nodes = [
            CommonThreadNode(
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                reasoning_ids=sorted(reasoning_map.get((n.entity_type, n.entity_id), set())),
            )
            for n in graph.nodes
        ]
        edges = [
            CommonThreadEdge(
                source_entity_type=e.source.entity_type,
                source_entity_id=e.source.entity_id,
                target_entity_type=e.target.entity_type,
                target_entity_id=e.target.entity_id,
                relationship_type=e.relationship_type,
            )
            for e in graph.edges
        ]

        return CommonThreadTrace(
            root_entity_type=root_entity_type,
            root_entity_id=str(root_entity_id),
            nodes=nodes,
            edges=edges,
        )

    async def _get_reasoning_map(
        self,
        db: AsyncSession,
        graph: LineageGraph,
    ) -> dict[tuple[str, str], set[str]]:
        keys = {(n.entity_type.strip().lower(), n.entity_id) for n in graph.nodes}
        if not keys:
            return {}

        entity_types = sorted({k[0] for k in keys})
        result = await db.execute(
            select(ReasoningTrace).where(ReasoningTrace.entity_type.in_(entity_types))
        )
        traces = result.scalars().all()

        out: dict[tuple[str, str], set[str]] = {}
        for tr in traces:
            key = (tr.entity_type, tr.entity_id)
            if key in keys:
                out.setdefault(key, set()).add(tr.reasoning_id)
        return out


_service_instance: Optional[CommonThreadService] = None


def get_common_thread_service() -> CommonThreadService:
    global _service_instance
    if _service_instance is None:
        _service_instance = CommonThreadService()
    return _service_instance

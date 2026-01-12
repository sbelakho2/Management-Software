"""Common Thread Genealogy Binding.

Provides deterministic integrity binding across modules:
RFQ -> Quote -> Production (Work Orders) -> Quality (NCs) -> Shipping/Invoice.

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
        created_by_id: Any | None = None,
        reasoning_id: str | None = None,
        source: str | None = None,
    ) -> None:
        """Create best-effort lineage links across the common thread stages."""

        def _id(x: Any | None) -> str | None:
            return None if x is None else str(x)

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

        # Reasoning trace stamping
        if reasoning_id:
            for et, eid in (
                ("rfq", rfq_id),
                ("quote", quote_id),
                ("work_order", work_order_id),
                ("non_conformance", non_conformance_id),
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

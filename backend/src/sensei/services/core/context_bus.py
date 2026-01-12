"""Cross-Module Context Bus service.

Builds a deterministic "context pack" around an entity by:
- expanding the Data Lineage graph (directed edges)
- fetching cross-silo entity snapshots for known entity types
- computing lightweight derived metrics (e.g., Work Order labor variance)

This service is intentionally deterministic (no LLM calls).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.product import Product
from sensei.models.quality import NonConformance
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.work_order import WorkOrder
from sensei.services.core.data_lineage import DataLineageService, LineageGraph


@dataclass(frozen=True)
class ContextEntitySnapshot:
    entity_type: str
    entity_id: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ContextPack:
    root_entity_type: str
    root_entity_id: str
    nodes: list[ContextEntitySnapshot]
    edges: list[dict[str, Any]]


class ContextService:
    """Deterministic context aggregation across modules."""

    def __init__(self, lineage_service: DataLineageService | None = None) -> None:
        self._lineage = lineage_service or DataLineageService()

    async def get_context_pack(
        self,
        db: AsyncSession,
        *,
        root_entity_type: str,
        root_entity_id: str,
        max_depth: int = 3,
    ) -> ContextPack:
        graph = await self._lineage.get_graph(
            db,
            root_entity_type=root_entity_type,
            root_entity_id=root_entity_id,
            max_depth=max_depth,
        )

        nodes: list[ContextEntitySnapshot] = []
        for node in graph.nodes:
            snapshot = await self._snapshot_entity(db, node.entity_type, node.entity_id)
            if snapshot is not None:
                nodes.append(snapshot)

        edges = [
            {
                "source_entity_type": e.source.entity_type,
                "source_entity_id": e.source.entity_id,
                "target_entity_type": e.target.entity_type,
                "target_entity_id": e.target.entity_id,
                "relationship_type": e.relationship_type,
            }
            for e in graph.edges
        ]

        return ContextPack(
            root_entity_type=root_entity_type,
            root_entity_id=str(root_entity_id),
            nodes=nodes,
            edges=edges,
        )

    async def _snapshot_entity(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> Optional[ContextEntitySnapshot]:
        entity_type_norm = entity_type.strip().lower()

        if entity_type_norm == "rfq":
            rfq_id = self._parse_uuid(entity_id)
            if rfq_id is None:
                return None
            rfq = await db.get(RFQ, rfq_id)
            if rfq is None:
                return None
            data = {
                "rfq_number": rfq.rfq_number,
                "title": rfq.title,
                "status": rfq.status,
                "part_number": rfq.part_number,
                "part_name": rfq.part_name,
                "primary_process": rfq.primary_process,
                "secondary_processes": rfq.secondary_processes,
                "material_spec": rfq.material_spec,
                "material_grade": rfq.material_grade,
                "finish_requirements": rfq.finish_requirements,
                "tolerance_requirements": rfq.tolerance_requirements,
                "quality_requirements": rfq.quality_requirements,
                "certifications_required": rfq.certifications_required,
                "inspection_requirements": rfq.inspection_requirements,
                "delivery_terms": rfq.delivery_terms,
                "lead_time_required_days": rfq.lead_time_required,
                "packaging_requirements": rfq.packaging_requirements,
            }
            return ContextEntitySnapshot(entity_type="rfq", entity_id=str(rfq.id), data=data)

        if entity_type_norm == "quote":
            quote_id = self._parse_uuid(entity_id)
            if quote_id is None:
                return None
            quote = await db.get(Quote, quote_id)
            if quote is None:
                return None

            assumptions = []
            if isinstance(quote.custom_fields, dict):
                raw = quote.custom_fields.get("assumptions")
                if isinstance(raw, list):
                    assumptions = [str(x) for x in raw if str(x).strip()]
                elif isinstance(raw, str) and raw.strip():
                    assumptions = [raw.strip()]

            data = {
                "quote_number": quote.quote_number,
                "title": quote.title,
                "status": quote.status,
                "currency": quote.currency,
                "total": str(quote.total) if quote.total is not None else None,
                "rfq_id": str(quote.rfq_id) if quote.rfq_id else None,
                "payment_terms": quote.payment_terms,
                "delivery_terms": quote.delivery_terms,
                "lead_time_days": quote.lead_time_days,
                "special_conditions": quote.special_conditions,
                "assumptions": assumptions,
            }
            return ContextEntitySnapshot(entity_type="quote", entity_id=str(quote.id), data=data)

        if entity_type_norm == "work_order":
            wo_id = self._parse_int(entity_id)
            if wo_id is None:
                return None

            stmt = (
                select(WorkOrder)
                .where(WorkOrder.id == wo_id)
                .options(selectinload(WorkOrder.operations))
            )
            wo = (await db.execute(stmt)).scalars().first()
            if wo is None:
                return None

            standard_seconds = sum(
                int(op.standard_time_seconds or 0) + int(op.setup_time_seconds or 0)
                for op in (wo.operations or [])
            )
            actual_seconds = sum(
                int(op.actual_time_seconds or 0) + int(op.actual_setup_seconds or 0)
                for op in (wo.operations or [])
            )
            variance_seconds = actual_seconds - standard_seconds

            efficiency_pct: float | None = None
            if actual_seconds > 0:
                efficiency_pct = float(Decimal(standard_seconds) / Decimal(actual_seconds) * 100)

            nc_count_stmt = select(func.count()).select_from(NonConformance).where(NonConformance.work_order_id == wo.id)
            nc_count = int((await db.execute(nc_count_stmt)).scalar_one())

            data = {
                "work_order_number": wo.work_order_number,
                "status": wo.status.value if hasattr(wo.status, "value") else str(wo.status),
                "product_id": str(wo.product_id),
                "quantity_ordered": str(wo.quantity_ordered),
                "quantity_completed": str(wo.quantity_completed),
                "quantity_scrapped": str(wo.quantity_scrapped),
                "scheduled_start": wo.scheduled_start.isoformat() if wo.scheduled_start else None,
                "scheduled_end": wo.scheduled_end.isoformat() if wo.scheduled_end else None,
                "labor_standard_seconds": standard_seconds,
                "labor_actual_seconds": actual_seconds,
                "labor_variance_seconds": variance_seconds,
                "labor_efficiency_pct": efficiency_pct,
                "non_conformance_count": nc_count,
            }
            return ContextEntitySnapshot(entity_type="work_order", entity_id=str(wo.id), data=data)

        if entity_type_norm == "product":
            product_id = self._parse_int(entity_id)
            if product_id is None:
                return None
            product = await db.get(Product, product_id)
            if product is None:
                return None
            data = {
                "name": product.name,
                "part_number": product.part_number,
                "revision": product.revision,
                "lead_time_days": product.lead_time_days,
                "standard_labor_hours": str(product.standard_labor_hours) if product.standard_labor_hours is not None else None,
            }
            return ContextEntitySnapshot(entity_type="product", entity_id=str(product.id), data=data)

        if entity_type_norm == "non_conformance":
            nc_id = self._parse_int(entity_id)
            if nc_id is None:
                return None
            nc = await db.get(NonConformance, nc_id)
            if nc is None:
                return None
            data = {
                "nc_number": nc.nc_number,
                "status": nc.status.value if hasattr(nc.status, "value") else str(nc.status),
                "severity": nc.severity.value if hasattr(nc.severity, "value") else str(nc.severity),
                "title": nc.title,
                "work_order_id": str(nc.work_order_id) if nc.work_order_id is not None else None,
                "product_id": str(nc.product_id) if nc.product_id is not None else None,
            }
            return ContextEntitySnapshot(entity_type="non_conformance", entity_id=str(nc.id), data=data)

        return None

    @staticmethod
    def _parse_uuid(value: str) -> UUID | None:
        try:
            return UUID(str(value))
        except Exception:
            return None

    @staticmethod
    def _parse_int(value: str) -> int | None:
        try:
            return int(str(value))
        except Exception:
            return None


_context_service_singleton: ContextService | None = None


def get_context_service() -> ContextService:
    global _context_service_singleton
    if _context_service_singleton is None:
        _context_service_singleton = ContextService()
    return _context_service_singleton

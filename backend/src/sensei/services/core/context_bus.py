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

from sensei.models.account import Account
from sensei.models.accounts_receivable import SalesOrder, Shipment
from sensei.models.accounts_receivable import CustomerInvoice, PaymentReceipt
from sensei.models.finance import JournalEntry, BankTransaction
from sensei.models.hr import EmployeeProfile, HRLeaveRequest, HRTimeClockEvent
from sensei.models.opportunity import Opportunity
from sensei.models.product import Product
from sensei.models.quality import NonConformance, CAPA
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.training import TrainingParticipant
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
                "labor_efficiency_pct": str(efficiency_pct) if efficiency_pct is not None else None,
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

        if entity_type_norm == "opportunity":
            opp_id = self._parse_uuid(entity_id)
            if opp_id is None:
                return None
            opp = await db.get(Opportunity, opp_id)
            if opp is None:
                return None
            data = {
                "name": opp.name,
                "stage": opp.stage.value if hasattr(opp.stage, "value") else str(opp.stage),
                "amount": str(opp.amount) if opp.amount is not None else None,
                "currency": opp.currency,
                "probability": opp.probability,
                "close_date": opp.close_date.isoformat() if opp.close_date else None,
                "account_id": str(opp.account_id),
                "primary_contact_id": str(opp.primary_contact_id) if opp.primary_contact_id else None,
                "forecast_category": opp.forecast_category,
                "next_step": opp.next_step,
            }
            return ContextEntitySnapshot(entity_type="opportunity", entity_id=str(opp.id), data=data)

        if entity_type_norm == "sales_order":
            so_id = self._parse_uuid(entity_id)
            if so_id is None:
                return None
            so = await db.get(SalesOrder, so_id)
            if so is None:
                return None
            data = {
                "so_number": so.so_number,
                "status": so.status,
                "currency": so.currency,
                "account_id": str(so.account_id),
                "source_quote_id": str(so.source_quote_id) if so.source_quote_id else None,
                "payment_terms_days": so.payment_terms_days,
                "approved_at": so.approved_at.isoformat() if so.approved_at else None,
            }
            return ContextEntitySnapshot(entity_type="sales_order", entity_id=str(so.id), data=data)

        if entity_type_norm == "account":
            acc_id = self._parse_uuid(entity_id)
            if acc_id is None:
                return None
            acc = await db.get(Account, acc_id)
            if acc is None:
                return None
            data = {
                "name": acc.name,
                "account_type": acc.account_type,
                "status": acc.status,
                "tier": acc.tier,
                "industry": acc.industry,
                "country": acc.country,
                "city": acc.city,
                "website": acc.website,
            }
            return ContextEntitySnapshot(entity_type="account", entity_id=str(acc.id), data=data)

        if entity_type_norm == "capa":
            capa_id = self._parse_int(entity_id)
            if capa_id is None:
                return None
            capa = await db.get(CAPA, capa_id)
            if capa is None:
                return None
            data = {
                "capa_number": capa.capa_number,
                "title": capa.title,
                "capa_type": capa.capa_type.value if hasattr(capa.capa_type, "value") else str(capa.capa_type),
                "status": capa.status.value if hasattr(capa.status, "value") else str(capa.status),
                "priority": capa.priority.value if hasattr(capa.priority, "value") else str(capa.priority),
                "root_cause_category": (
                    capa.root_cause_category.value
                    if capa.root_cause_category and hasattr(capa.root_cause_category, "value")
                    else str(capa.root_cause_category) if capa.root_cause_category else None
                ),
                "due_date": capa.due_date.isoformat() if capa.due_date else None,
            }
            return ContextEntitySnapshot(entity_type="capa", entity_id=str(capa.id), data=data)

        if entity_type_norm == "shipment":
            ship_id = self._parse_uuid(entity_id)
            if ship_id is None:
                return None
            ship = await db.get(Shipment, ship_id)
            if ship is None:
                return None
            data = {
                "shipment_number": ship.shipment_number,
                "status": ship.status,
                "carrier": ship.carrier,
                "tracking_number": ship.tracking_number,
                "ship_date": ship.ship_date.isoformat() if ship.ship_date else None,
                "expected_delivery": ship.expected_delivery.isoformat() if ship.expected_delivery else None,
                "actual_delivery": ship.actual_delivery.isoformat() if ship.actual_delivery else None,
                "account_id": str(ship.account_id),
                "sales_order_id": str(ship.sales_order_id) if ship.sales_order_id else None,
            }
            return ContextEntitySnapshot(entity_type="shipment", entity_id=str(ship.id), data=data)

        if entity_type_norm == "invoice":
            inv_id = self._parse_uuid(entity_id)
            if inv_id is None:
                return None
            inv = await db.get(CustomerInvoice, inv_id)
            if inv is None:
                return None
            data = {
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "currency": inv.currency,
                "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "account_id": str(inv.account_id),
                "sales_order_id": str(inv.sales_order_id) if inv.sales_order_id else None,
                "is_credit_memo": inv.is_credit_memo,
                "disputed": inv.disputed,
            }
            return ContextEntitySnapshot(entity_type="invoice", entity_id=str(inv.id), data=data)

        if entity_type_norm == "payment":
            payment_id = self._parse_uuid(entity_id)
            if payment_id is None:
                return None
            payment = await db.get(PaymentReceipt, payment_id)
            if payment is None:
                return None
            data = {
                "status": payment.status,
                "currency": payment.currency,
                "amount": str(payment.amount),
                "received_at": payment.received_at.isoformat() if payment.received_at else None,
                "account_id": str(payment.account_id),
                "reference": payment.reference,
            }
            return ContextEntitySnapshot(entity_type="payment", entity_id=str(payment.id), data=data)

        if entity_type_norm == "journal_entry":
            je_id = self._parse_uuid(entity_id)
            if je_id is None:
                return None
            je = await db.get(JournalEntry, je_id)
            if je is None:
                return None
            data = {
                "reference": je.reference,
                "entry_date": je.entry_date.isoformat() if je.entry_date else None,
                "status": je.status,
                "description": je.description,
                "posted_at": je.posted_at.isoformat() if je.posted_at else None,
            }
            return ContextEntitySnapshot(entity_type="journal_entry", entity_id=str(je.id), data=data)

        if entity_type_norm == "bank_transaction":
            bt_id = self._parse_uuid(entity_id)
            if bt_id is None:
                return None
            bt = await db.get(BankTransaction, bt_id)
            if bt is None:
                return None
            data = {
                "transaction_date": bt.transaction_date.isoformat() if bt.transaction_date else None,
                "transaction_type": bt.transaction_type,
                "amount": str(bt.amount),
                "currency": bt.currency,
                "status": bt.status,
                "bank_account_id": str(bt.bank_account_id),
                "source_type": bt.source_type,
                "source_id": str(bt.source_id) if bt.source_id else None,
            }
            return ContextEntitySnapshot(entity_type="bank_transaction", entity_id=str(bt.id), data=data)

        if entity_type_norm == "employee":
            emp_id = self._parse_uuid(entity_id)
            if emp_id is None:
                return None
            emp = await db.get(EmployeeProfile, emp_id)
            if emp is None:
                return None
            data = {
                "user_id": str(emp.user_id) if emp.user_id else None,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "department": emp.department,
                "job_title": emp.job_title,
                "status": emp.status,
                "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
            }
            return ContextEntitySnapshot(entity_type="employee", entity_id=str(emp.id), data=data)

        if entity_type_norm == "leave_request":
            leave_id = self._parse_uuid(entity_id)
            if leave_id is None:
                return None
            leave = await db.get(HRLeaveRequest, leave_id)
            if leave is None:
                return None
            data = {
                "employee_id": str(leave.employee_id),
                "leave_type": leave.leave_type,
                "start_date": leave.start_date.isoformat() if leave.start_date else None,
                "end_date": leave.end_date.isoformat() if leave.end_date else None,
                "status": leave.status,
                "approved_by_id": str(leave.approved_by_id) if leave.approved_by_id else None,
            }
            return ContextEntitySnapshot(entity_type="leave_request", entity_id=str(leave.id), data=data)

        if entity_type_norm == "timecard":
            tc_id = self._parse_uuid(entity_id)
            if tc_id is None:
                return None
            tc = await db.get(HRTimeClockEvent, tc_id)
            if tc is None:
                return None
            data = {
                "employee_id": str(tc.employee_id),
                "event_type": tc.event_type,
                "event_time": tc.event_time.isoformat() if tc.event_time else None,
                "is_within_geofence": tc.is_within_geofence,
                "is_anomaly": tc.is_anomaly,
                "anomaly_reason": tc.anomaly_reason,
                "station_id": tc.station_id,
            }
            return ContextEntitySnapshot(entity_type="timecard", entity_id=str(tc.id), data=data)

        if entity_type_norm == "training_record":
            tr_id = self._parse_int(entity_id)
            if tr_id is None:
                return None
            tr = await db.get(TrainingParticipant, tr_id)
            if tr is None:
                return None
            data = {
                "training_id": str(tr.training_id),
                "employee_id": str(tr.user_id),
                "enrollment_status": tr.enrollment_status,
                "attendance_status": tr.attendance_status,
                "score": str(tr.score) if tr.score is not None else None,
                "completed_at": tr.completed_at.isoformat() if tr.completed_at else None,
            }
            return ContextEntitySnapshot(entity_type="training_record", entity_id=str(tr.id), data=data)

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

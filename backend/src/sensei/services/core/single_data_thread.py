"""Single data thread bridge.

Wires domain events into the common thread and analytics warehouse so
executive analytics are driven by a unified data stream.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.database import async_session_factory
from sensei.services.core.common_thread import get_common_thread_service
from sensei.services.core.state_codec import encode_value
from sensei.services.event_bus import DomainEvent
from sensei.services.ops.analytics_warehouse import AnalyticsWarehouseService, FactType


_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
_SYSTEM_ROLES: tuple[str, ...] = ("ceo",)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _event_payload(event: DomainEvent) -> dict[str, Any]:
    if is_dataclass(event):
        raw = asdict(event)
    else:
        raw = dict(getattr(event, "__dict__", {}))
    return encode_value(raw)


def _map_fact_type(event: DomainEvent) -> FactType:
    name = type(event).__name__.lower()

    # Quality / compliance
    if "nonconformance" in name or "nccreated" in name or "capa" in name or "inspection" in name or "audit" in name:
        return FactType.NON_CONFORMANCE
    if "andon" in name:
        return FactType.ANDON_EVENT

    # Operations / production
    if "workorder" in name or "productionorder" in name:
        return FactType.WORK_ORDER
    if "downtime" in name or "cycle" in name:
        return FactType.CYCLE_TIME

    # Finance
    if "costrollup" in name:
        return FactType.COST_ROLLUP
    if "journal" in name:
        return FactType.FINANCIAL_TRANSACTION
    if "invoice" in name:
        invoice_type = getattr(event, "invoice_type", "")
        if invoice_type == "payable":
            return FactType.AP_INVOICE
        return FactType.AR_INVOICE
    if "purchaseorder" in name:
        return FactType.AP_INVOICE
    if "payment" in name:
        return FactType.FINANCIAL_TRANSACTION

    # HR / Training
    if "training" in name or "certification" in name:
        return FactType.TRAINING_COMPLIANCE
    if "employee" in name or "onboard" in name or "application" in name:
        return FactType.HEADCOUNT_SNAPSHOT
    if "turnover" in name or "terminated" in name:
        return FactType.EMPLOYEE_TURNOVER
    if "leave" in name or "timecard" in name or "performance" in name or "hrcase" in name:
        return FactType.HEADCOUNT_SNAPSHOT

    # Inventory / Supply Chain
    if "inventory" in name or "stock" in name or "goodsreceipt" in name:
        return FactType.STOCK_MOVEMENT
    if "mrp" in name:
        return FactType.MRP_EXCEPTION
    if "supplier" in name:
        return FactType.INVENTORY_LEVEL

    # PM / maintenance schedule
    if "pmschedule" in name or "maintenance" in name:
        return FactType.WORK_ORDER

    # CRM / Sales
    if "opportunity" in name:
        return FactType.OPPORTUNITY
    if "rfq" in name:
        return FactType.RFQ_FACT
    if "quote" in name:
        return FactType.QUOTE_FACT
    if "salesorder" in name:
        return FactType.SALES_ORDER_FACT

    # Project Management
    if "project" in name or "sprint" in name or "issue" in name:
        return FactType.PROJECT_FACT

    # A3 / Problem Solving
    if "a3" in name:
        return FactType.A3_FACT

    # Risk
    if "risk" in name:
        return FactType.RISK_EVENT

    # Kanban
    if "kanban" in name:
        return FactType.KANBAN_FACT

    # AI / ML
    if "anomaly" in name:
        return FactType.ANOMALY_DETECTION
    if "modelretrained" in name or "retrain" in name:
        return FactType.MODEL_RETRAIN

    # Fallback
    return FactType.QUALITY_METRIC


def _pluck_ids(payload: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            out[key] = payload[key]
    return out


class SingleDataThreadService:
    """Bridges domain events into the common thread and analytics warehouse."""

    def __init__(
        self,
        session_factory=async_session_factory,
        warehouse: AnalyticsWarehouseService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._warehouse = warehouse or AnalyticsWarehouseService()
        self._common_thread = get_common_thread_service()

    async def handle_event(self, event: DomainEvent) -> None:
        payload = _event_payload(event)
        fact_type = _map_fact_type(event)

        common_ids = _pluck_ids(
            payload,
            [
                "rfq_id",
                "quote_id",
                "work_order_id",
                "nc_id",
                "non_conformance_id",
                "shipment_id",
                "invoice_id",
                "sales_order_id",
                "purchase_order_id",
                "goods_receipt_id",
                "inventory_move_id",
                "andon_event_id",
                "capa_id",
                "opportunity_id",
                "journal_entry_id",
                "bank_transaction_id",
                "payment_id",
                "product_id",
                "employee_id",
                "training_id",
                "leave_request_id",
                "performance_review_id",
                "labor_booking_id",
                "hr_case_id",
                "timecard_id",
                "supplier_id",
                "asset_id",
            ],
        )

        async with self._session_factory() as session:
            await self._record_common_thread(session, common_ids, event.event_id)
            await self._warehouse.append_exported_record(
                session,
                actor_roles=_SYSTEM_ROLES,
                actor_user_id=_SYSTEM_USER_ID,
                fact_type=fact_type,
                data={
                    "event_type": type(event).__name__,
                    "event_id": event.event_id,
                    "occurred_at": payload.get("occurred_at") or _utcnow().isoformat(),
                    "tenant_id": payload.get("tenant_id"),
                    "payload": payload,
                },
                occurred_at=getattr(event, "occurred_at", None),
            )
            await session.commit()

    async def _record_common_thread(
        self,
        session: AsyncSession,
        ids: dict[str, Any],
        reasoning_id: str,
    ) -> None:
        non_conformance_id = ids.get("non_conformance_id") or ids.get("nc_id")

        await self._common_thread.bind(
            session,
            rfq_id=ids.get("rfq_id"),
            quote_id=ids.get("quote_id"),
            work_order_id=ids.get("work_order_id"),
            non_conformance_id=non_conformance_id,
            shipment_id=ids.get("shipment_id"),
            invoice_id=ids.get("invoice_id"),
            sales_order_id=ids.get("sales_order_id"),
            purchase_order_id=ids.get("purchase_order_id"),
            goods_receipt_id=ids.get("goods_receipt_id"),
            inventory_move_id=ids.get("inventory_move_id"),
            andon_event_id=ids.get("andon_event_id"),
            capa_id=ids.get("capa_id"),
            opportunity_id=ids.get("opportunity_id"),
            journal_entry_id=ids.get("journal_entry_id"),
            bank_transaction_id=ids.get("bank_transaction_id"),
            payment_id=ids.get("payment_id"),
            reasoning_id=reasoning_id,
            source="single_data_thread",
        )

        # Wire HR thread if any HR entity IDs are present
        hr_ids = _pluck_ids(
            ids,
            [
                "employee_id",
                "work_order_id",
                "training_id",
                "leave_request_id",
                "performance_review_id",
                "labor_booking_id",
                "hr_case_id",
                "timecard_id",
            ],
        )
        if hr_ids.get("employee_id"):
            await self._common_thread.bind_hr(
                session,
                employee_id=hr_ids.get("employee_id"),
                work_order_id=hr_ids.get("work_order_id"),
                training_record_id=hr_ids.get("training_id"),
                leave_request_id=hr_ids.get("leave_request_id"),
                performance_review_id=hr_ids.get("performance_review_id"),
                labor_booking_id=hr_ids.get("labor_booking_id"),
                hr_case_id=hr_ids.get("hr_case_id"),
                timecard_id=hr_ids.get("timecard_id"),
                reasoning_id=reasoning_id,
                source="single_data_thread_hr",
            )

        reasoning_map = {
            "rfq": ids.get("rfq_id"),
            "quote": ids.get("quote_id"),
            "work_order": ids.get("work_order_id"),
            "non_conformance": non_conformance_id,
            "shipment": ids.get("shipment_id"),
            "invoice": ids.get("invoice_id"),
            "sales_order": ids.get("sales_order_id"),
            "purchase_order": ids.get("purchase_order_id"),
            "inventory_move": ids.get("inventory_move_id"),
            "andon_event": ids.get("andon_event_id"),
            "capa": ids.get("capa_id"),
            "opportunity": ids.get("opportunity_id"),
            "journal_entry": ids.get("journal_entry_id"),
            "bank_transaction": ids.get("bank_transaction_id"),
            "payment": ids.get("payment_id"),
            "product": ids.get("product_id"),
            "employee": ids.get("employee_id"),
            "training": ids.get("training_id"),
            "leave_request": ids.get("leave_request_id"),
            "performance_review": ids.get("performance_review_id"),
            "labor_booking": ids.get("labor_booking_id"),
            "hr_case": ids.get("hr_case_id"),
            "timecard": ids.get("timecard_id"),
            "supplier": ids.get("supplier_id"),
            "asset": ids.get("asset_id"),
        }

        for entity_type, entity_id in reasoning_map.items():
            if entity_id in (None, ""):
                continue
            await self._common_thread.record_reasoning(
                session,
                entity_type=entity_type,
                entity_id=entity_id,
                reasoning_id=reasoning_id,
                source="single_data_thread",
            )


_service_instance: SingleDataThreadService | None = None


def get_single_data_thread_service() -> SingleDataThreadService:
    global _service_instance
    if _service_instance is None:
        _service_instance = SingleDataThreadService()
    return _service_instance

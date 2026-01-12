from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.context_bus import get_context_pack
from sensei.models.account import Account
from sensei.models.product import Product
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.user import User
from sensei.models.work_center import WorkCenter, WorkCenterStatus, Station
from sensei.models.work_order import WorkOrder, WorkOrderOperation, WorkOrderPriority, WorkOrderStatus
from sensei.services.core.data_lineage import DataLineageService


@pytest.mark.asyncio
async def test_get_context_pack_returns_cross_silo_snapshots(async_session):
    user = User(
        email="ctx-api@example.com",
        username="ctxapi",
        password_hash="x",
        first_name="Ctx",
        last_name="API",
    )
    async_session.add(user)

    account = Account(name="Acme Corp")
    async_session.add(account)
    await async_session.flush()

    rfq = RFQ(
        rfq_number="RFQ-CTX-API-1",
        title="Widget RFQ",
        account_id=account.id,
        material_spec="SS304",
        certifications_required=["ISO 9001"],
    )
    async_session.add(rfq)

    quote = Quote(
        quote_number="Q-CTX-API-1",
        title="Widget Quote",
        account_id=account.id,
        rfq_id=rfq.id,
        currency="MAD",
        total=Decimal("200.00"),
        custom_fields={"assumptions": ["Lead time excludes plating"]},
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(quote)

    product = Product(name="Widget", part_number="W-CTX-API")
    async_session.add(product)
    await async_session.flush()

    wc = WorkCenter(code="WC-2", name="Cell 2", status=WorkCenterStatus.ACTIVE)
    async_session.add(wc)
    await async_session.flush()

    station = Station(name="Station 2", code="S-2", work_center_id=wc.id)
    async_session.add(station)
    await async_session.flush()

    wo = WorkOrder(
        work_order_number="WO-CTX-API-1",
        product_id=product.id,
        quantity_ordered=Decimal("1"),
        priority=WorkOrderPriority.NORMAL,
        status=WorkOrderStatus.DRAFT,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(wo)
    await async_session.flush()

    op = WorkOrderOperation(
        work_order_id=wo.id,
        routing_id=None,
        sequence=1,
        operation_name="Op",
        station_id=station.id,
        standard_time_seconds=60,
        actual_time_seconds=90,
    )
    async_session.add(op)
    await async_session.flush()

    lineage = DataLineageService()
    await lineage.link(
        async_session,
        source_entity_type="rfq",
        source_entity_id=str(rfq.id),
        target_entity_type="quote",
        target_entity_id=str(quote.id),
        relationship_type="has_quote",
        created_by_id=user.id,
        reasoning_id=str(uuid4()),
    )
    await lineage.link(
        async_session,
        source_entity_type="quote",
        source_entity_id=str(quote.id),
        target_entity_type="work_order",
        target_entity_id=str(wo.id),
        relationship_type="has_work_order",
        created_by_id=user.id,
        reasoning_id=str(uuid4()),
    )
    await async_session.commit()

    resp = await get_context_pack(
        entity_type="work_order",
        entity_id=str(wo.id),
        max_depth=3,
        db=async_session,
        current_user=user,
    )

    assert resp.success is True
    node_keys = {(n.entity_type, n.entity_id) for n in resp.data.nodes}
    assert ("work_order", str(wo.id)) in node_keys
    assert ("quote", str(quote.id)) in node_keys
    assert ("rfq", str(rfq.id)) in node_keys

    # Ensure computed variance is present on the work order snapshot
    wo_node = next(n for n in resp.data.nodes if n.entity_type == "work_order")
    assert wo_node.data["labor_standard_seconds"] == 60
    assert wo_node.data["labor_actual_seconds"] == 90
    assert wo_node.data["labor_variance_seconds"] == 30

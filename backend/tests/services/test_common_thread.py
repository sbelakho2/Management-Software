from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.account import Account
from sensei.models.product import Product
from sensei.models.quality import NCSeverity, NCSource, NCStatus, NCType, NonConformance
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.user import User
from sensei.models.work_center import Station, WorkCenter
from sensei.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus
from sensei.services.core.common_thread import CommonThreadService


@pytest.mark.asyncio
async def test_common_thread_trace_contains_reasoning_ids_and_external_shipping(async_session):
    user = User(
        email="ct@example.com",
        username="ct",
        password_hash="x",
        first_name="CT",
        last_name="User",
    )
    async_session.add(user)

    account = Account(name="Acme Corp")
    async_session.add(account)
    await async_session.flush()

    rfq = RFQ(
        rfq_number="RFQ-CT-1",
        title="Widget RFQ",
        account_id=account.id,
    )
    async_session.add(rfq)

    quote = Quote(
        quote_number="Q-CT-1",
        title="Widget Quote",
        account_id=account.id,
        rfq_id=rfq.id,
        currency="MAD",
        total=Decimal("100.00"),
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(quote)

    product = Product(name="Widget", part_number="W-CT")
    async_session.add(product)
    await async_session.flush()

    wc = WorkCenter(code="WC-CT", name="Cell CT")
    async_session.add(wc)
    await async_session.flush()

    station = Station(name="Station CT", code="S-CT", work_center_id=wc.id)
    async_session.add(station)

    wo = WorkOrder(
        work_order_number="WO-CT-1",
        product_id=product.id,
        quantity_ordered=Decimal("1"),
        priority=WorkOrderPriority.NORMAL,
        status=WorkOrderStatus.DRAFT,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(wo)
    await async_session.flush()

    nc = NonConformance(
        nc_number="NC-CT-1",
        nc_type=NCType.PRODUCT,
        source=NCSource.IN_PROCESS,
        severity=NCSeverity.MINOR,
        product_id=product.id,
        work_order_id=wo.id,
        quantity_affected=1,
        title="Out of spec",
        description="Measured out of spec",
        detected_by_id=user.id,
        status=NCStatus.OPEN,
    )
    async_session.add(nc)
    await async_session.flush()

    reasoning_id = str(uuid4())
    svc = CommonThreadService()

    await svc.bind(
        async_session,
        rfq_id=str(rfq.id),
        quote_id=str(quote.id),
        work_order_id=str(wo.id),
        non_conformance_id=str(nc.id),
        shipment_id="SHIP-EXT-1",
        invoice_id="INV-EXT-1",
        created_by_id=user.id,
        reasoning_id=reasoning_id,
        source="test",
    )
    await async_session.commit()

    trace = await svc.get_trace(
        async_session,
        root_entity_type="work_order",
        root_entity_id=str(wo.id),
        max_depth=4,
    )

    node_map = {(n.entity_type, n.entity_id): n for n in trace.nodes}
    assert ("rfq", str(rfq.id)) in node_map
    assert ("quote", str(quote.id)) in node_map
    assert ("work_order", str(wo.id)) in node_map
    assert ("non_conformance", str(nc.id)) in node_map
    assert ("shipment", "SHIP-EXT-1") in node_map
    assert ("invoice", "INV-EXT-1") in node_map

    assert reasoning_id in node_map[("rfq", str(rfq.id))].reasoning_ids
    assert reasoning_id in node_map[("quote", str(quote.id))].reasoning_ids
    assert reasoning_id in node_map[("work_order", str(wo.id))].reasoning_ids

    edge_keys = {(e.source_entity_type, e.relationship_type, e.target_entity_type) for e in trace.edges}
    assert ("rfq", "has_quote", "quote") in edge_keys
    assert ("quote", "has_work_order", "work_order") in edge_keys
    assert ("work_order", "has_non_conformance", "non_conformance") in edge_keys
    assert ("work_order", "has_shipment", "shipment") in edge_keys
    assert ("shipment", "has_invoice", "invoice") in edge_keys

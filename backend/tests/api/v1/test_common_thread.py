from __future__ import annotations

from decimal import Decimal

import pytest

from sensei.api.v1.endpoints.common_thread import bind_common_thread, get_common_thread_trace, CommonThreadBindRequest
from sensei.models.account import Account
from sensei.models.product import Product
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.user import User
from sensei.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus


@pytest.mark.asyncio
async def test_common_thread_api_bind_and_trace(async_session):
    user = User(
        email="ct-api@example.com",
        username="ctapi",
        password_hash="x",
        first_name="CT",
        last_name="API",
    )
    async_session.add(user)

    account = Account(name="Acme Corp")
    async_session.add(account)
    await async_session.flush()

    rfq = RFQ(rfq_number="RFQ-CT-API-1", title="Widget RFQ", account_id=account.id)
    async_session.add(rfq)

    quote = Quote(
        quote_number="Q-CT-API-1",
        title="Widget Quote",
        account_id=account.id,
        rfq_id=rfq.id,
        currency="MAD",
        total=Decimal("100.00"),
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(quote)

    product = Product(name="Widget", part_number="W-CT-API")
    async_session.add(product)
    await async_session.flush()

    wo = WorkOrder(
        work_order_number="WO-CT-API-1",
        product_id=product.id,
        quantity_ordered=Decimal("1"),
        priority=WorkOrderPriority.NORMAL,
        status=WorkOrderStatus.DRAFT,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(wo)
    await async_session.flush()
    await async_session.commit()

    req = CommonThreadBindRequest(
        rfq_id=str(rfq.id),
        quote_id=str(quote.id),
        work_order_id=str(wo.id),
        shipment_id="SHIP-API-1",
        invoice_id="INV-API-1",
        source="test_api",
    )

    bind_resp = await bind_common_thread(
        req,
        db=async_session,
        current_user=user,
        x_reasoning_id="RID-API-1",
    )
    assert bind_resp.success is True

    trace_resp = await get_common_thread_trace(
        entity_type="work_order",
        entity_id=str(wo.id),
        max_depth=4,
        db=async_session,
        current_user=user,
    )

    assert trace_resp.success is True
    node_map = {(n.entity_type, n.entity_id): n for n in trace_resp.data.nodes}
    assert ("rfq", str(rfq.id)) in node_map
    assert ("quote", str(quote.id)) in node_map
    assert ("work_order", str(wo.id)) in node_map
    assert ("shipment", "SHIP-API-1") in node_map
    assert ("invoice", "INV-API-1") in node_map

    assert "RID-API-1" in node_map[("rfq", str(rfq.id))].reasoning_ids
    assert "RID-API-1" in node_map[("quote", str(quote.id))].reasoning_ids
    assert "RID-API-1" in node_map[("work_order", str(wo.id))].reasoning_ids

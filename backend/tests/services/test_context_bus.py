from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.account import Account
from sensei.models.product import Product
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.user import User
from sensei.models.work_center import WorkCenter, WorkCenterStatus, Station
from sensei.models.work_order import WorkOrder, WorkOrderOperation, WorkOrderPriority, WorkOrderStatus
from sensei.services.core.context_bus import ContextService
from sensei.services.core.data_lineage import DataLineageService


@pytest.mark.asyncio
async def test_context_pack_links_rfq_to_work_order_variance(async_session):
    user = User(
        email="ctx@example.com",
        username="ctx",
        password_hash="x",
        first_name="Ctx",
        last_name="User",
    )
    async_session.add(user)

    account = Account(name="Acme Corp")
    async_session.add(account)
    await async_session.flush()

    rfq = RFQ(
        rfq_number="RFQ-CTX-1",
        title="Widget RFQ",
        account_id=account.id,
        material_spec="AL 6061",
        tolerance_requirements="±0.1mm",
        certifications_required=["ISO 9001"],
        primary_process="CNC",
    )
    async_session.add(rfq)

    quote = Quote(
        quote_number="Q-CTX-1",
        title="Widget Quote",
        account_id=account.id,
        rfq_id=rfq.id,
        currency="MAD",
        total=Decimal("100.00"),
        custom_fields={"assumptions": ["Material pricing stable for 30 days"]},
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(quote)

    product = Product(name="Widget", part_number="W-CTX")
    async_session.add(product)
    await async_session.flush()

    wc = WorkCenter(code="WC-1", name="Cell 1", status=WorkCenterStatus.ACTIVE)
    async_session.add(wc)
    await async_session.flush()

    station = Station(name="Station 1", code="S-1", work_center_id=wc.id)
    async_session.add(station)
    await async_session.flush()

    wo = WorkOrder(
        work_order_number="WO-CTX-1",
        product_id=product.id,
        quantity_ordered=Decimal("10"),
        priority=WorkOrderPriority.NORMAL,
        status=WorkOrderStatus.DRAFT,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    async_session.add(wo)
    await async_session.flush()

    # Two operations: standard 120s each, actual 180s each.
    op1 = WorkOrderOperation(
        work_order_id=wo.id,
        routing_id=None,
        sequence=1,
        operation_name="Op1",
        station_id=station.id,
        standard_time_seconds=120,
        setup_time_seconds=0,
        actual_time_seconds=180,
        actual_setup_seconds=0,
    )
    op2 = WorkOrderOperation(
        work_order_id=wo.id,
        routing_id=None,
        sequence=2,
        operation_name="Op2",
        station_id=station.id,
        standard_time_seconds=120,
        setup_time_seconds=0,
        actual_time_seconds=180,
        actual_setup_seconds=0,
    )
    async_session.add_all([op1, op2])
    await async_session.flush()

    lineage = DataLineageService()
    # Explicitly link RFQ -> Quote -> Work Order
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

    svc = ContextService(lineage_service=lineage)
    pack = await svc.get_context_pack(
        async_session,
        root_entity_type="work_order",
        root_entity_id=str(wo.id),
        max_depth=3,
    )

    by_type = {n.entity_type: n for n in pack.nodes}
    assert "work_order" in by_type
    assert "quote" in by_type
    assert "rfq" in by_type

    # Verify RFQ technical assumptions (deterministic fields)
    assert by_type["rfq"].data["material_spec"] == "AL 6061"
    assert by_type["rfq"].data["tolerance_requirements"] == "±0.1mm"

    # Verify Quote assumptions are exposed
    assert by_type["quote"].data["assumptions"] == ["Material pricing stable for 30 days"]

    # Verify labor variance computed from work order ops: (180+180)-(120+120)=120
    wo_data = by_type["work_order"].data
    assert wo_data["labor_standard_seconds"] == 240
    assert wo_data["labor_actual_seconds"] == 360
    assert wo_data["labor_variance_seconds"] == 120

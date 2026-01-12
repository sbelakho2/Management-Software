from __future__ import annotations

from decimal import Decimal

import pytest

from sensei.api.v1.endpoints.data_lineage import get_lineage_graph
from sensei.models.product import Product
from sensei.models.quality import NCSeverity, NCSource, NCStatus, NCType, NonConformance
from sensei.models.user import User
from sensei.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus
from sensei.services.core.data_lineage import DataLineageService


@pytest.mark.asyncio
async def test_get_lineage_graph_returns_nodes_and_edges(async_session):
    user = User(
        email="dl-api@example.com",
        username="dlapi",
        password_hash="x",
        first_name="DL",
        last_name="API",
    )
    async_session.add(user)

    product = Product(name="Widget", part_number="W-API")
    async_session.add(product)
    await async_session.flush()

    wo = WorkOrder(
        work_order_number="WO-API-1",
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
        nc_number="NC-API-1",
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

    svc = DataLineageService()
    await svc.capture_work_order_created(
        async_session,
        work_order_id=wo.id,
        product_id=product.id,
        created_by_id=user.id,
    )
    await svc.capture_non_conformance_created(
        async_session,
        non_conformance_id=nc.id,
        product_id=product.id,
        work_order_id=wo.id,
        created_by_id=user.id,
    )
    await async_session.commit()

    resp = await get_lineage_graph(
        entity_type="work_order",
        entity_id=str(wo.id),
        max_depth=2,
        db=async_session,
        current_user=user,
    )

    assert resp.success is True
    node_keys = {(n.entity_type, n.entity_id) for n in resp.data.nodes}
    assert ("work_order", str(wo.id)) in node_keys
    assert ("product", str(product.id)) in node_keys
    assert ("non_conformance", str(nc.id)) in node_keys

    edge_keys = {(e.source_entity_type, e.relationship_type, e.target_entity_type) for e in resp.data.edges}
    assert ("product", "has_work_order", "work_order") in edge_keys
    assert ("work_order", "has_non_conformance", "non_conformance") in edge_keys

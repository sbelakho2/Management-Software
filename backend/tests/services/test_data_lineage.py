from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from sensei.models.data_lineage import DataLineageLink
from sensei.models.product import Product
from sensei.models.quality import NCSeverity, NCSource, NCStatus, NCType, NonConformance
from sensei.models.user import User
from sensei.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus
from sensei.services.core.data_lineage import DataLineageService


@pytest.mark.asyncio
async def test_data_lineage_link_idempotent(async_session):
    svc = DataLineageService()

    await svc.link(
        async_session,
        source_entity_type="product",
        source_entity_id=1,
        relationship_type="has_work_order",
        target_entity_type="work_order",
        target_entity_id=10,
    )
    await svc.link(
        async_session,
        source_entity_type="product",
        source_entity_id=1,
        relationship_type="has_work_order",
        target_entity_type="work_order",
        target_entity_id=10,
    )

    result = await async_session.execute(select(DataLineageLink))
    links = result.scalars().all()
    assert len(links) == 1


@pytest.mark.asyncio
async def test_data_lineage_graph_from_work_order_to_non_conformance(async_session):
    # Minimal user for detected_by_id
    user = User(
        email="dl@example.com",
        username="dluser",
        password_hash="x",
        first_name="DL",
        last_name="User",
    )
    async_session.add(user)

    product = Product(name="Widget", part_number="W-1")
    async_session.add(product)
    await async_session.flush()

    wo = WorkOrder(
        work_order_number="WO-DL-1",
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
        nc_number="NC-DL-1",
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

    graph = await svc.get_graph(
        async_session,
        root_entity_type="work_order",
        root_entity_id=wo.id,
        max_depth=2,
    )

    node_keys = {(n.entity_type, n.entity_id) for n in graph.nodes}
    assert ("work_order", str(wo.id)) in node_keys
    assert ("product", str(product.id)) in node_keys
    assert ("non_conformance", str(nc.id)) in node_keys

    edge_keys = {(e.source.entity_type, e.relationship_type, e.target.entity_type) for e in graph.edges}
    assert ("product", "has_work_order", "work_order") in edge_keys
    assert ("work_order", "has_non_conformance", "non_conformance") in edge_keys


@pytest.mark.asyncio
async def test_data_lineage_quality_capa_and_inspection(async_session):
    svc = DataLineageService()

    # Use realistic IDs (no FK constraints for lineage links)
    nc_id = 100
    capa_id = 200
    action_id = 201
    plan_id = 300
    record_id = 301
    product_id = 400
    station_id = 500
    work_order_id = 600

    await svc.capture_capa_created(
        async_session,
        capa_id=capa_id,
        source_nc_id=nc_id,
    )
    await svc.capture_capa_action_created(
        async_session,
        capa_id=capa_id,
        action_id=action_id,
    )
    await svc.capture_inspection_plan_created(
        async_session,
        plan_id=plan_id,
        product_id=product_id,
        station_id=station_id,
    )
    await svc.capture_inspection_record_created(
        async_session,
        record_id=record_id,
        inspection_plan_id=plan_id,
        work_order_id=work_order_id,
        nc_id=nc_id,
    )
    await async_session.commit()

    graph = await svc.get_graph(
        async_session,
        root_entity_type="non_conformance",
        root_entity_id=nc_id,
        max_depth=3,
    )

    node_keys = {(n.entity_type, n.entity_id) for n in graph.nodes}
    assert ("non_conformance", str(nc_id)) in node_keys
    assert ("capa", str(capa_id)) in node_keys
    assert ("capa_action", str(action_id)) in node_keys
    assert ("inspection_record", str(record_id)) in node_keys

    edge_keys = {(e.source.entity_type, e.relationship_type, e.target.entity_type) for e in graph.edges}
    assert ("non_conformance", "has_capa", "capa") in edge_keys
    assert ("capa", "has_capa_action", "capa_action") in edge_keys
    assert ("inspection_plan", "has_inspection_record", "inspection_record") in edge_keys
    assert ("work_order", "has_inspection_record", "inspection_record") in edge_keys
    assert ("non_conformance", "has_inspection_record", "inspection_record") in edge_keys


@pytest.mark.asyncio
async def test_data_lineage_training_and_certification(async_session):
    svc = DataLineageService()

    requirement_id = 10
    skill_id = 11
    station_id = 12
    product_id = 13
    training_id = 20
    participant_id = 21
    user_id = uuid4()
    user_skill_id = 30

    await svc.capture_skill_requirement_created(
        async_session,
        requirement_id=requirement_id,
        skill_id=skill_id,
        station_id=station_id,
        product_id=product_id,
    )
    await svc.capture_training_created(
        async_session,
        training_id=training_id,
        skill_id=skill_id,
    )
    await svc.capture_training_participant_enrolled(
        async_session,
        training_id=training_id,
        participant_id=participant_id,
        user_id=user_id,
    )
    await svc.capture_user_skill_created(
        async_session,
        user_skill_id=user_skill_id,
        user_id=user_id,
        skill_id=skill_id,
    )
    await async_session.commit()

    graph = await svc.get_graph(
        async_session,
        root_entity_type="user",
        root_entity_id=user_id,
        max_depth=3,
    )

    edge_keys = {(e.source.entity_type, e.relationship_type, e.target.entity_type) for e in graph.edges}
    assert ("user", "enrolled_in", "training") in edge_keys
    assert ("user", "has_skill", "user_skill") in edge_keys
    assert ("skill", "has_training", "training") in edge_keys
    assert ("skill", "has_user_skill", "user_skill") in edge_keys

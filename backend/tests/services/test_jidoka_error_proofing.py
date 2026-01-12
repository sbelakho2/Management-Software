"""Service tests for Jidoka (AI Error-Proofing) suggestions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.product import Product, ProductStatus, UnitOfMeasure
from sensei.models.quality import (
    NonConformance,
    NCType,
    NCSource,
    NCSeverity,
    NCStatus,
    RootCauseCategory,
)
from sensei.models.user import User
from sensei.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from sensei.services.production.jidoka_error_proofing import JidokaErrorProofingService


@pytest.mark.asyncio
async def test_jidoka_suggests_measurement_pokayoke_for_out_of_spec(async_session) -> None:
    user = User(
        id=uuid4(),
        email="qa@sensei.local",
        username="qa",
        password_hash="x",
        first_name="QA",
        last_name="User",
        status="active",
        is_superuser=False,
        email_verified=True,
    )
    async_session.add(user)

    product = Product(
        name="Widget",
        part_number="W-001",
        revision="A",
        status=ProductStatus.ACTIVE,
        unit_of_measure=UnitOfMeasure.EACH,
    )
    async_session.add(product)
    await async_session.flush()

    wo = WorkOrder(
        work_order_number="WO-0001",
        product_id=product.id,
        quantity_ordered=Decimal("10"),
        priority=WorkOrderPriority.NORMAL,
        status=WorkOrderStatus.DRAFT,
    )
    async_session.add(wo)
    await async_session.flush()

    nc = NonConformance(
        nc_number="NC-0001",
        nc_type=NCType.PRODUCT,
        source=NCSource.IN_PROCESS,
        severity=NCSeverity.MAJOR,
        product_id=product.id,
        work_order_id=wo.id,
        station_id=None,
        title="Dimension out of spec",
        description="Part width is 10.2mm instead of 10.0mm (out of spec)",
        root_cause_category=RootCauseCategory.MEASUREMENT,
        detected_by_id=user.id,
        detected_at=datetime(2026, 1, 10, 12, 0, 0),
        status=NCStatus.OPEN,
    )
    async_session.add(nc)
    await async_session.flush()

    svc = JidokaErrorProofingService()
    suggestions = await svc.suggest_for_work_order_release(async_session, work_order_id=wo.id)

    assert suggestions
    assert any("measurement" in s.title.lower() or "go/no-go" in s.title.lower() for s in suggestions)
    assert any(nc.id in s.related_non_conformance_ids for s in suggestions)

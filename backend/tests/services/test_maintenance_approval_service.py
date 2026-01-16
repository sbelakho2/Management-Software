from __future__ import annotations

import pytest

from sensei.models.maintenance import Asset
from sensei.models.user import User
from sensei.services.maintenance.persistent_maintenance import PersistentMaintenanceService


@pytest.mark.asyncio
async def test_work_order_approval_flow(async_session):
    user = User(
        email="approver@example.com",
        username="approver",
        password_hash="hashed",
        first_name="Approver",
        last_name="User",
        status="active",
    )
    async_session.add(user)

    asset = Asset(
        asset_number="AST-200",
        name="Compressor",
        asset_type="utility",
    )
    async_session.add(asset)
    await async_session.flush()

    svc = PersistentMaintenanceService(async_session)
    wo = await svc.create_work_order(
        asset_id=asset.id,
        work_order_number="MWO-0001",
        work_order_type="corrective",
        status="open",
        priority=9,
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    requested = await svc.request_work_order_approval(wo.id, user.id)
    assert requested is not None
    assert requested.approval_status == "pending"

    approved = await svc.approve_work_order(wo.id, user.id, "Approved for urgent repair")
    assert approved is not None
    assert approved.approval_status == "approved"
    assert approved.approved_by_id == user.id

from __future__ import annotations

import pytest

from sensei.models.user import User
from sensei.services.maintenance.tool_crib import ToolCribService


@pytest.mark.asyncio
async def test_tool_checkout_and_return(async_session):
    user = User(
        email="tool@example.com",
        username="tool_user",
        password_hash="hashed",
        first_name="Tool",
        last_name="User",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = ToolCribService(async_session)
    tool = await svc.create_tool(
        tool_number="TL-100",
        name="Torque Wrench",
        status="available",
        quantity_on_hand=2,
        min_quantity=1,
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    checkout = await svc.checkout_tool(
        tool_id=tool.id,
        checked_out_by_id=user.id,
        condition_out="good",
    )
    assert checkout is not None

    active = await svc.list_active_checkouts()
    assert len(active) == 1

    returned = await svc.return_tool(
        checkout_id=checkout.id,
        returned_by_id=user.id,
        condition_in="good",
    )
    assert returned is not None
    assert returned.returned_at is not None

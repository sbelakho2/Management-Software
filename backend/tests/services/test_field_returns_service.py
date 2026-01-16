from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from sensei.models.maintenance import Asset
from sensei.services.maintenance.field_returns import FieldReturnService


@pytest.mark.asyncio
async def test_field_returns_flow(async_session):
    asset = Asset(
        asset_number="ASSET-RET-001",
        name="Returned Pump",
        asset_type="machine",
        status="operational",
        criticality="B",
        meter_reading=Decimal("0"),
        meter_unit="cycles",
        operating_hours=Decimal("0"),
    )
    async_session.add(asset)
    await async_session.flush()

    svc = FieldReturnService(async_session)
    field_return = await svc.create_return(
        asset_id=asset.id,
        return_number="FR-2026-001",
        received_at=datetime.now(timezone.utc),
        failure_mode="seal_leak",
    )

    assert field_return.status == "received"

    await svc.update_return(field_return, status="investigating", cost_impact=Decimal("150.00"))
    assert field_return.status == "investigating"

    await svc.close_return(field_return)
    assert field_return.status == "closed"
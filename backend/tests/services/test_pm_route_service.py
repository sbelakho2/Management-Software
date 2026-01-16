from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sensei.models.maintenance import Asset, PMSchedule
from sensei.services.maintenance.persistent_maintenance import PersistentMaintenanceService


@pytest.mark.asyncio
async def test_pm_route(async_session):
    asset = Asset(
        asset_number="AST-300",
        name="Laser Cutter",
        asset_type="machine",
    )
    async_session.add(asset)
    await async_session.flush()

    pm = PMSchedule(
        asset_id=asset.id,
        name="Monthly Inspection",
        frequency_type="calendar",
        frequency_value=30,
        frequency_unit="days",
        next_due=datetime.now(timezone.utc) + timedelta(days=3),
        is_active=True,
    )
    async_session.add(pm)
    await async_session.flush()

    svc = PersistentMaintenanceService(async_session)
    route = await svc.get_pm_route(days_ahead=7)
    assert len(route) == 1
    assert route[0]["name"] == "Monthly Inspection"

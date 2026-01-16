from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sensei.services.quality.aql_sampling_service import AQLSamplingService


@pytest.mark.asyncio
async def test_aql_sampling_flow(async_session):
    svc = AQLSamplingService(async_session)
    plan = await svc.create_plan(
        plan_code="AQL-II-1.0-80-125",
        standard="ANSI/ASQ Z1.4",
        inspection_level="II",
        aql_level="1.0",
        lot_size_min=80,
        lot_size_max=125,
        sample_size=13,
        accept_limit=1,
        reject_limit=2,
        status="active",
    )

    inspection = await svc.create_inspection(
        plan=plan,
        lot_number="LOT-2026-001",
        lot_size=100,
        defect_count=1,
        sample_size=None,
        inspected_at=datetime.now(timezone.utc),
    )

    assert inspection.result == "accept"
    assert inspection.sample_size == 13

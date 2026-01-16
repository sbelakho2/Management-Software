from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from sensei.services.quality.change_point_service import ChangePointService


@pytest.mark.asyncio
async def test_change_point_detection(async_session):
    svc = ChangePointService(async_session)
    study = await svc.create_study(
        name="Drift Check",
        process_name="Drill",
        characteristic="Hole Diameter",
        method="mean_shift",
        sensitivity=Decimal("0.2"),
        status="active",
        started_at=datetime.now(timezone.utc),
    )

    for value in [Decimal("10.00"), Decimal("10.05"), Decimal("10.02"), Decimal("10.60"), Decimal("10.55")]:
        await svc.add_observation(
            study_id=study.id,
            observed_at=datetime.now(timezone.utc),
            value=value,
        )

    event = await svc.detect_change_points(study)
    assert event is not None
    assert event.change_magnitude != 0

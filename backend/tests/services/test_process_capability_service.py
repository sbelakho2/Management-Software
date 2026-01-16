from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from sensei.models.user import User
from sensei.services.quality.process_capability_service import ProcessCapabilityService


@pytest.mark.asyncio
async def test_process_capability_compute(async_session):
    user = User(
        email="capability@example.com",
        username="capability_user",
        password_hash="hashed",
        first_name="Cap",
        last_name="Ability",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = ProcessCapabilityService(async_session)
    study = await svc.create_study(
        name="CNC Mill 1 Diameter",
        process_name="CNC Mill 1",
        characteristic="Bore Diameter",
        lsl=Decimal("9.95"),
        usl=Decimal("10.05"),
        target=Decimal("10.00"),
        unit="mm",
        started_at=datetime.now(timezone.utc),
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    values = [
        Decimal("9.98"),
        Decimal("9.99"),
        Decimal("10.00"),
        Decimal("10.01"),
        Decimal("10.02"),
    ]

    for idx, value in enumerate(values, start=1):
        await svc.add_measurement(
            study_id=study.id,
            measured_value=value,
            sample_label=f"S{idx}",
        )

    result = await svc.compute_capability(study.id)
    assert result is not None
    assert result.sample_size == len(values)
    assert result.cp >= 0
    assert result.cpk >= 0

    await async_session.refresh(study)
    assert study.status == "completed"
    assert study.completed_at is not None

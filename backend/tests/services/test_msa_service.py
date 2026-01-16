from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from sensei.models.quality_qms import Gauge
from sensei.models.user import User
from sensei.services.quality.msa_service import MSAService


@pytest.mark.asyncio
async def test_msa_service_compute_grr(async_session):
    operator_a = User(
        email="operator.a@example.com",
        username="operator_a",
        password_hash="hashed",
        first_name="Operator",
        last_name="A",
        status="active",
    )
    operator_b = User(
        email="operator.b@example.com",
        username="operator_b",
        password_hash="hashed",
        first_name="Operator",
        last_name="B",
        status="active",
    )
    async_session.add_all([operator_a, operator_b])
    await async_session.flush()

    gauge = Gauge(
        gauge_number="G-1001",
        description="CMM for Line 2",
        owner_id=operator_a.id,
        status="active",
    )
    async_session.add(gauge)
    await async_session.flush()

    svc = MSAService(async_session)
    study = await svc.create_study(
        gauge_id=gauge.id,
        name="Line 2 GRR",
        study_type="grr",
        parts_count=2,
        operators_count=2,
        trials_count=2,
        started_at=datetime.now(timezone.utc),
    )

    measurements = [
        (operator_a.id, "P1", 1, Decimal("10.01")),
        (operator_a.id, "P1", 2, Decimal("10.03")),
        (operator_a.id, "P2", 1, Decimal("10.55")),
        (operator_a.id, "P2", 2, Decimal("10.52")),
        (operator_b.id, "P1", 1, Decimal("10.05")),
        (operator_b.id, "P1", 2, Decimal("10.02")),
        (operator_b.id, "P2", 1, Decimal("10.50")),
        (operator_b.id, "P2", 2, Decimal("10.49")),
    ]

    for operator_id, part_id, trial_number, measured_value in measurements:
        await svc.add_measurement(
            study_id=study.id,
            operator_id=operator_id,
            part_id=part_id,
            trial_number=trial_number,
            measured_value=measured_value,
        )

    result = await svc.compute_grr(study.id)
    assert result is not None
    assert result.grr_percent >= 0
    assert result.ndc >= 0

    await async_session.refresh(study)
    assert study.status == "completed"
    assert study.completed_at is not None

"""Tests for muda nudging background worker runner."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from sensei.services.utils.job_idempotency import JobIdempotencyService
from sensei.services.ops.kpi_metrics import KPIService, KPIValue
from sensei.services.ops.muda_contextual_nudging import MudaAwareContextualNudgingService
from sensei.services.ops.muda_nudging_worker import MudaNudgingJobRunner


@pytest.mark.asyncio
async def test_muda_nudging_worker_is_idempotent_per_recipient_trigger_bucket() -> None:
    kpi_service = KPIService()

    # Low FPY -> high defect rate trigger
    kpi_service.record_value(
        KPIValue(
            id="v1",
            kpi_id="first-pass-yield",
            value=90.0,
            timestamp=datetime(2026, 1, 11, 12, 0, 0),
            dimensions={},
        )
    )
    # Low OEE trigger
    kpi_service.record_value(
        KPIValue(
            id="v2",
            kpi_id="oee",
            value=50.0,
            timestamp=datetime(2026, 1, 11, 12, 0, 1),
            dimensions={},
        )
    )

    nudging = MudaAwareContextualNudgingService(kpi_service=kpi_service)
    idempotency = JobIdempotencyService()
    runner = MudaNudgingJobRunner(nudging_service=nudging, idempotency=idempotency)

    delivered: list[str] = []

    def _on_deliver(nudge):
        delivered.append(f"{nudge.recipient_id}:{nudge.trigger.value}")

    bucket = date(2026, 1, 11)

    first = await runner.run(
        recipient_ids=["u1"],
        include_knowledge=False,
        deliver=True,
        on_deliver=_on_deliver,
        bucket_date=bucket,
    )

    assert first.delivered_count == len(first.nudges)
    assert first.cached_count == 0
    assert len(delivered) == len(first.nudges)
    assert {n.trigger.value for n in first.nudges} >= {"high_defect_rate", "low_oee"}

    second = await runner.run(
        recipient_ids=["u1"],
        include_knowledge=False,
        deliver=True,
        on_deliver=_on_deliver,
        bucket_date=bucket,
    )

    assert second.delivered_count == 0
    assert second.cached_count == len(second.nudges)
    assert len(delivered) == len(first.nudges)


@pytest.mark.asyncio
async def test_muda_nudging_worker_scopes_idempotency_by_recipient() -> None:
    kpi_service = KPIService()

    kpi_service.record_value(
        KPIValue(
            id="v1",
            kpi_id="first-pass-yield",
            value=90.0,
            timestamp=datetime(2026, 1, 11, 12, 0, 0),
            dimensions={},
        )
    )

    nudging = MudaAwareContextualNudgingService(kpi_service=kpi_service)
    runner = MudaNudgingJobRunner(
        nudging_service=nudging,
        idempotency=JobIdempotencyService(),
    )

    bucket = date(2026, 1, 11)

    r1 = await runner.run(
        recipient_ids=["u1"],
        include_knowledge=False,
        bucket_date=bucket,
    )
    r2 = await runner.run(
        recipient_ids=["u2"],
        include_knowledge=False,
        bucket_date=bucket,
    )

    assert len(r1.nudges) > 0
    assert len(r2.nudges) > 0
    assert {n.recipient_id for n in r1.nudges} == {"u1"}
    assert {n.recipient_id for n in r2.nudges} == {"u2"}

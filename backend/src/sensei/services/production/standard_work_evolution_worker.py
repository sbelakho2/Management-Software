"""Standard Work Evolution job runner.

Runs evaluations across recently completed A3s and drafts StandardWork revisions
when success patterns are detected.

Idempotency is enforced per A3 per bucket day.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable
from uuid import UUID

from sensei.services.utils.job_idempotency import IdempotencyKey, JobIdempotencyService, JobType
from sensei.services.production.standard_work_evolution import (
    AutonomousStandardWorkEvolutionService,
    EvolutionDecision,
    SYSTEM_ACTOR_ID,
)


@dataclass(frozen=True)
class StandardWorkEvolutionRunResult:
    decisions: list[EvolutionDecision]
    delivered_count: int
    cached_count: int
    generated_at: datetime


class StandardWorkEvolutionJobRunner:
    def __init__(
        self,
        *,
        evolution_service: AutonomousStandardWorkEvolutionService,
        idempotency: JobIdempotencyService | None = None,
    ) -> None:
        self.evolution_service = evolution_service
        self.idempotency = idempotency or JobIdempotencyService()

    async def run(
        self,
        *,
        db,
        a3_ids: list[UUID],
        actor_user_id: UUID = SYSTEM_ACTOR_ID,
        bucket_date: date | None = None,
        deliver: bool = False,
        on_deliver: Callable[[EvolutionDecision], None] | None = None,
    ) -> StandardWorkEvolutionRunResult:
        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        bucket = bucket_date or generated_at.date()

        delivered_count = 0
        cached_count = 0
        decisions: list[EvolutionDecision] = []

        for a3_id in a3_ids:
            key = IdempotencyKey.from_explicit_key(
                explicit_key=f"sw-evolution:{a3_id}:{bucket.isoformat()}",
                job_type=JobType.SCHEDULED_TASK,
                ttl_hours=24,
            )

            async def _job() -> EvolutionDecision:
                return await self.evolution_service.evaluate_and_draft(
                    db,
                    a3_id=a3_id,
                    actor_user_id=actor_user_id,
                )

            result = await self.idempotency.execute_idempotent(key, _job)
            if result.value is None:
                continue

            decisions.append(result.value)

            if result.cached:
                cached_count += 1
                continue

            delivered_count += 1
            if deliver and on_deliver:
                on_deliver(result.value)

        return StandardWorkEvolutionRunResult(
            decisions=decisions,
            delivered_count=delivered_count,
            cached_count=cached_count,
            generated_at=generated_at,
        )

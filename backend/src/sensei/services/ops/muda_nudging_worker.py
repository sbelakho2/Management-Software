"""Muda nudging background worker.

Implements a scheduler-friendly job runner that:
- Builds operational snapshots (KPIService + overrides)
- Detects muda-related triggers
- Proactively generates micro-lesson nudges
- Uses JobIdempotencyService to avoid spamming the same recipient/trigger

This module is intentionally transport-agnostic: it can be wired to APScheduler,
Celery, or any orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.utils.job_idempotency import IdempotencyKey, JobIdempotencyService, JobType
from sensei.services.ops.muda_contextual_nudging import MudaAwareContextualNudgingService, MudaNudge


@dataclass(frozen=True)
class MudaNudgingRunResult:
    nudges: list[MudaNudge]
    delivered_count: int
    cached_count: int
    generated_at: datetime


class MudaNudgingJobRunner:
    """Background runner for muda-aware micro-lesson nudges."""

    def __init__(
        self,
        nudging_service: MudaAwareContextualNudgingService,
        idempotency: JobIdempotencyService | None = None,
    ) -> None:
        self.nudging_service = nudging_service
        self.idempotency = idempotency or JobIdempotencyService()

    async def run(
        self,
        db: AsyncSession | None = None,
        *,
        recipient_ids: list[UUID],
        dimensions_by_recipient: dict[UUID, dict[str, str]] | None = None,
        overrides: dict[str, Any] | None = None,
        include_knowledge: bool = True,
        deliver: bool = False,
        on_deliver: Callable[[MudaNudge], Any] | None = None,
        bucket_date: date | None = None,
    ) -> MudaNudgingRunResult:
        """Generate and optionally deliver nudges.

        Idempotency is enforced per (recipient_id, trigger, bucket_date).

        Args:
            db: Async database session.
            recipient_ids: Recipients to evaluate.
            dimensions_by_recipient: Optional KPI dimensions per recipient.
            overrides: Optional operational override signals.
            include_knowledge: Whether to attach knowledge recommendations.
            deliver: Whether to call on_deliver for newly generated nudges.
            on_deliver: Callback invoked for newly generated (non-cached) nudges.
            bucket_date: Time bucket for idempotency (defaults to today).
        """
        generated_at = datetime.now(timezone.utc)
        bucket = bucket_date or generated_at.date()

        delivered_count = 0
        cached_count = 0
        collected: list[MudaNudge] = []

        for recipient_id in recipient_ids:
            dims = (dimensions_by_recipient or {}).get(recipient_id)
            snapshot = self.nudging_service.build_operational_snapshot(
                dimensions=dims or None,
                overrides=overrides or None,
            )
            triggers = self.nudging_service.evaluate_triggers(snapshot)

            for trigger in triggers:
                key = IdempotencyKey.from_explicit_key(
                    explicit_key=f"muda:{recipient_id}:{trigger.value}:{bucket.isoformat()}",
                    job_type=JobType.SCHEDULED_TASK,
                    ttl_hours=24,
                )

                async def _job() -> MudaNudge:
                    return await self.nudging_service.generate_nudge_for_trigger(
                        db=db,
                        trigger=trigger,
                        recipient_id=recipient_id,
                        trigger_context=snapshot,
                        include_knowledge=include_knowledge,
                        generated_at=generated_at,
                    )

                result = await self.idempotency.execute_idempotent(key, _job)
                if result.value is None:
                    continue

                collected.append(result.value)

                if result.cached:
                    cached_count += 1
                    continue

                delivered_count += 1
                if deliver and on_deliver:
                    on_deliver(result.value)

        return MudaNudgingRunResult(
            nudges=collected,
            delivered_count=delivered_count,
            cached_count=cached_count,
            generated_at=generated_at,
        )

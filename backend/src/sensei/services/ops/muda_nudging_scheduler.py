"""Muda nudging scheduler service.

Runs the muda nudging job runner on a fixed interval, using APScheduler.
This is intentionally conservative and off by default.

Because APScheduler's BackgroundScheduler runs jobs in a thread pool, this
service bridges into the main asyncio loop via run_coroutine_threadsafe.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from sensei.services.ops.muda_nudging_worker import MudaNudgingJobRunner

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MudaNudgingScheduleConfig:
    enabled: bool
    interval_seconds: int
    recipient_ids: list[UUID]


class MudaNudgingSchedulerService:
    """Starts/stops a periodic muda nudging evaluation."""

    JOB_ID = "muda-nudging"

    def __init__(
        self,
        *,
        job_runner: MudaNudgingJobRunner,
        loop: asyncio.AbstractEventLoop,
        config: MudaNudgingScheduleConfig,
        scheduler: Optional[BackgroundScheduler] = None,
    ) -> None:
        self.job_runner = job_runner
        self.loop = loop
        self.config = config
        self.scheduler = scheduler or BackgroundScheduler()
        self._is_running = False

    def start(self) -> None:
        if self._is_running:
            logger.warning("Muda nudging scheduler already running")
            return

        if not self.config.enabled:
            logger.info("Muda nudging scheduler disabled")
            return

        if not self.config.recipient_ids:
            logger.info("Muda nudging scheduler enabled but no recipients configured")
            return

        self.scheduler.add_job(
            func=self._run_once,
            trigger=IntervalTrigger(seconds=self.config.interval_seconds),
            id=self.JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        self.scheduler.start()
        self._is_running = True
        logger.info(
            "Muda nudging scheduler started",
            extra={
                "interval_seconds": self.config.interval_seconds,
                "recipient_count": len(self.config.recipient_ids),
            },
        )

    def stop(self) -> None:
        if not self._is_running:
            return

        try:
            self.scheduler.shutdown()
        finally:
            self._is_running = False
            logger.info("Muda nudging scheduler stopped")

    def _run_once(self) -> None:
        """Run one evaluation tick (threadpool context)."""
        from sensei.core.websocket import get_websocket_manager
        from sensei.db.session import async_session_maker

        async def _run() -> None:
            ws_manager = get_websocket_manager()
            
            async def deliver_nudge(nudge):
                """Deliver nudge via WebSocket for real-time push coaching."""
                try:
                    await ws_manager.send_personal_message(
                        {
                            "type": "muda_nudge",
                            "payload": {
                                "trigger": nudge.trigger.value,
                                "recipient_id": str(nudge.recipient_id),
                                "lesson_id": nudge.lesson_id,
                                "lesson_title": nudge.lesson_title,
                                "lesson_summary": nudge.lesson_summary,
                                "lesson_category": nudge.lesson_category,
                                "recommended_documents": nudge.recommended_documents,
                                "generated_at": nudge.generated_at.isoformat(),
                            },
                        },
                        str(nudge.recipient_id),
                    )
                    logger.debug(
                        "Delivered muda nudge via WebSocket",
                        extra={"recipient": str(nudge.recipient_id), "trigger": nudge.trigger.value},
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to deliver nudge via WebSocket",
                        extra={"error": str(e), "recipient": str(nudge.recipient_id)},
                    )
            
            async with async_session_maker() as db:
                result = await self.job_runner.run(
                    db,
                    recipient_ids=self.config.recipient_ids,
                    include_knowledge=True,
                    deliver=True,  # Enable delivery
                    on_deliver=lambda nudge: asyncio.create_task(deliver_nudge(nudge)),
                )
            logger.info(
                "Muda nudging tick completed",
                extra={
                    "nudges": len(result.nudges),
                    "delivered": result.delivered_count,
                    "cached": result.cached_count,
                },
            )

        try:
            fut = asyncio.run_coroutine_threadsafe(_run(), self.loop)
            fut.result(timeout=300)
        except Exception:
            logger.exception("Muda nudging tick failed")

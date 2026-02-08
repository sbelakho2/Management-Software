import logging

from celery import Celery
from celery.signals import worker_shutting_down

from sensei.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "sensei",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DEFAULT_TIMEZONE,
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,

    # ---------- Reliability (Items #271–273) ----------
    # Acknowledge tasks AFTER they complete, not when received.
    # If a worker crashes mid-task the message is re-delivered.
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Hard kill after 10 min; soft signal at 5 min so tasks can clean up.
    task_time_limit=600,
    task_soft_time_limit=300,

    # Expire stored results after 1 hour to prevent Redis memory growth.
    result_expires=3600,

    # ---------- Worker tuning (Item #275) ----------
    # Prefetch 1 task at a time — prevents one worker from hogging a burst.
    worker_prefetch_multiplier=1,
    # Re-create workers after N tasks to mitigate memory leaks.
    worker_max_tasks_per_child=1000,
    # Concurrency: let env override, default 2 for VPS.
    worker_concurrency=getattr(settings, "CELERY_WORKER_CONCURRENCY", 2),

    # ---------- Dead-letter / retry policy (Item #273) ----------
    # Global default retry policy — tasks can override per-task.
    task_default_retry_delay=60,
    task_max_retries=3,

    # Track task state transitions (PENDING → STARTED → SUCCESS/FAILURE).
    task_track_started=True,
)

# Autodiscover tasks from all registered apps
celery_app.autodiscover_tasks(["sensei.tasks"])


# ---------- Graceful Shutdown (#407) ----------
@worker_shutting_down.connect
def worker_shutdown_handler(sig, how, exitcode, **kwargs):
    """Log and handle graceful worker shutdown."""
    logger.info(
        "Celery worker shutting down (signal=%s, how=%s, exitcode=%s)",
        sig, how, exitcode,
    )
    # Allow in-flight tasks to complete (acks_late ensures redelivery on crash)
    # Additional cleanup hooks can be registered here.

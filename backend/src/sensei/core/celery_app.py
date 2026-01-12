from celery import Celery
from sensei.core.config import settings

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
)

# Autodiscover tasks from all registered apps
celery_app.autodiscover_tasks(["sensei.tasks"])

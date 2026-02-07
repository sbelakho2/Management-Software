"""
Celery Tasks Package.

Contains all async background tasks for Sensei OS:
- ML Training Tasks (ml_tasks.py)
- PDF Generation Tasks (pdf_tasks.py)
"""

from sensei.tasks.ml_tasks import (
    run_model_training,
    check_drift_and_retrain,
    scheduled_retrain_all,
    force_model_retrain,
)
from sensei.tasks.pdf_tasks import (
    generate_a3_pdf,
    generate_quote_pdf,
    get_pdf_generation_progress,
)

__all__ = [
    # ML Tasks
    "run_model_training",
    "check_drift_and_retrain",
    "scheduled_retrain_all",
    "force_model_retrain",
    # PDF Tasks
    "generate_a3_pdf",
    "generate_quote_pdf",
    "get_pdf_generation_progress",
]

"""
Celery Tasks for ML Training and Continuous Learning.

This module provides async tasks for:
- Model training
- Drift detection and auto-retraining
- Scheduled model refresh
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from types import SimpleNamespace
from datetime import datetime
from sensei.core.celery_app import celery_app
from sensei.ml.mlops import MLPipeline

logger = logging.getLogger(__name__)


@celery_app.task(name="sensei.tasks.ml_tasks.run_model_training")
def run_model_training(
    model_name: str,
    model_class_path: str,  # Import string for model class
    train_data: Any,
    eval_data: Any,
    hyperparameters: Dict[str, Any],
    version: str = "1.0.0",
) -> str:
    """
    Celery task to run model training asynchronously.
    """
    logger.info(f"Starting async training for {model_name} v{version}")
    
    # Dynamic import of model class
    import importlib
    module_path, class_name = model_class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    model_class = getattr(module, class_name)
    
    def _inflate_value(value: Any) -> Any:
        if isinstance(value, dict):
            # Convert ISO date strings where possible
            converted = {}
            for k, v in value.items():
                if isinstance(v, str) and k in {"timestamp", "date", "installation_date"}:
                    try:
                        converted[k] = datetime.fromisoformat(v)
                    except Exception:
                        converted[k] = v
                else:
                    converted[k] = v
            return SimpleNamespace(**converted)
        if isinstance(value, list):
            return [_inflate_value(v) for v in value]
        return value

    if isinstance(train_data, dict):
        train_data = {k: _inflate_value(v) for k, v in train_data.items()}
    if isinstance(eval_data, dict):
        eval_data = {k: _inflate_value(v) for k, v in eval_data.items()}

    # Initialize pipeline
    # Note: MLPipeline might need its own initialization logic if it depends on DB/Registry
    pipeline = MLPipeline()
    
    try:
        model_id = asyncio.run(pipeline.run_training(
            model_name=model_name,
            model_class=model_class,
            train_data=train_data,
            eval_data=eval_data,
            hyperparameters=hyperparameters,
            version=version,
        ))
        return model_id
    except Exception as e:
        logger.error(f"Async training failed for {model_name}: {e}")
        raise


@celery_app.task(name="sensei.tasks.ml_tasks.check_drift_and_retrain")
def check_drift_and_retrain(model_name: str) -> Dict[str, Any]:
    """
    Celery task to check drift and trigger retraining if needed.
    
    This task is designed to be called periodically or triggered
    when drift is suspected.
    """
    logger.info(f"Checking drift for model: {model_name}")
    
    try:
        from sensei.services.ai.continuous_learning import (
            get_continuous_learning_service,
        )
        
        service = get_continuous_learning_service()
        
        # Run async check in sync context
        loop = asyncio.new_event_loop()
        try:
            job = loop.run_until_complete(
                service.check_and_retrain_if_needed(model_name)
            )
        finally:
            loop.close()
        
        if job:
            logger.info(
                f"Retraining triggered for {model_name}: "
                f"trigger={job.trigger.value}, improvement={job.improvement:.4f}"
            )
            return {
                "model": model_name,
                "job_id": job.job_id,
                "trigger": job.trigger.value,
                "status": job.status,
                "improvement": job.improvement,
            }
        
        logger.debug(f"No retraining needed for {model_name}")
        return {
            "model": model_name,
            "status": "no_retraining_needed",
        }
        
    except Exception as e:
        logger.error(f"Drift check failed for {model_name}: {e}")
        return {
            "model": model_name,
            "status": "error",
            "error": str(e),
        }


@celery_app.task(name="sensei.tasks.ml_tasks.scheduled_retrain_all")
def scheduled_retrain_all() -> List[Dict[str, Any]]:
    """
    Celery task for scheduled retraining of all registered models.
    
    This task should be scheduled via Celery Beat to run periodically
    (e.g., weekly or daily during off-hours).
    """
    logger.info("Starting scheduled retraining check for all models")
    
    try:
        from sensei.services.ai.continuous_learning import (
            get_continuous_learning_service,
        )
        
        service = get_continuous_learning_service()
        results = []
        
        for model_name in list(service._models.keys()):
            try:
                loop = asyncio.new_event_loop()
                try:
                    job = loop.run_until_complete(
                        service.check_and_retrain_if_needed(model_name)
                    )
                finally:
                    loop.close()
                
                if job:
                    results.append({
                        "model": model_name,
                        "job_id": job.job_id,
                        "trigger": job.trigger.value,
                        "status": job.status,
                    })
                else:
                    results.append({
                        "model": model_name,
                        "status": "no_retraining_needed",
                    })
                    
            except Exception as e:
                logger.error(f"Error checking {model_name}: {e}")
                results.append({
                    "model": model_name,
                    "status": "error",
                    "error": str(e),
                })
        
        logger.info(f"Scheduled retraining complete: {len(results)} models checked")
        return results
        
    except Exception as e:
        logger.error(f"Scheduled retraining failed: {e}")
        return [{"status": "error", "error": str(e)}]


@celery_app.task(name="sensei.tasks.ml_tasks.force_model_retrain")
def force_model_retrain(
    model_name: str,
    learning_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Celery task to force immediate retraining of a model.
    
    Args:
        model_name: Name of the model to retrain
        learning_mode: Optional learning mode ("batch", "incremental", "online")
    """
    logger.info(f"Force retraining model: {model_name}")
    
    try:
        from sensei.services.ai.continuous_learning import (
            get_continuous_learning_service,
            LearningMode,
        )
        
        service = get_continuous_learning_service()
        
        # Parse learning mode
        mode = None
        if learning_mode:
            mode = LearningMode(learning_mode)
        
        loop = asyncio.new_event_loop()
        try:
            job = loop.run_until_complete(
                service.force_retrain(model_name, learning_mode=mode)
            )
        finally:
            loop.close()
        
        logger.info(
            f"Force retraining completed for {model_name}: "
            f"samples={job.sample_count}, improvement={job.improvement:.4f}"
        )
        
        return {
            "model": model_name,
            "job_id": job.job_id,
            "status": job.status,
            "sample_count": job.sample_count,
            "previous_metrics": job.previous_metrics,
            "new_metrics": job.new_metrics,
            "improvement": job.improvement,
        }
        
    except Exception as e:
        logger.error(f"Force retraining failed for {model_name}: {e}")
        return {
            "model": model_name,
            "status": "error",
            "error": str(e),
        }


# =============================================================================
# Celery Beat Schedule (to be added to celeryconfig.py)
# =============================================================================

# Example beat schedule for continuous learning:
# 
# beat_schedule = {
#     'check-drift-all-models': {
#         'task': 'sensei.tasks.ml_tasks.scheduled_retrain_all',
#         'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
#     },
# }

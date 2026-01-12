import logging
from typing import Any, Dict
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
    
    # Initialize pipeline
    # Note: MLPipeline might need its own initialization logic if it depends on DB/Registry
    pipeline = MLPipeline()
    
    try:
        model_id = pipeline.run_training(
            model_name=model_name,
            model_class=model_class,
            train_data=train_data,
            eval_data=eval_data,
            hyperparameters=hyperparameters,
            version=version,
        )
        return model_id
    except Exception as e:
        logger.error(f"Async training failed for {model_name}: {e}")
        raise

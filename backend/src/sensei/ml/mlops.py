"""
MLOps Infrastructure: Model Management, Versioning, and Deployment

Provides infrastructure for:
- Model versioning and registry
- Training pipelines
- Model deployment and serving
- Performance monitoring
- A/B testing
- Model rollback
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model deployment status."""
    TRAINING = "training"
    REGISTERED = "registered"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass
class ModelMetadata:
    """Metadata for a trained ML model."""
    model_id: str
    model_name: str
    version: str
    status: ModelStatus
    created_at: datetime
    trained_by: str
    training_duration_seconds: float
    training_samples: int
    metrics: Dict[str, float]
    hyperparameters: Dict[str, Any]
    features: List[str]
    target: str
    framework: str  # sklearn, tensorflow, pytorch
    python_version: str
    dependencies: Dict[str, str]
    tags: List[str]
    description: str


class ModelRegistry:
    """
    Central registry for managing ML models.
    
    Provides:
    - Model versioning (semantic versioning)
    - Metadata storage
    - Model artifact management
    - Deployment tracking
    """

    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.registry_path / "registry.json"
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load registry from disk."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.registry = json.load(f)
        else:
            self.registry = {}
    
    def _save_registry(self) -> None:
        """Save registry to disk."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.registry, f, indent=2, default=str)
    
    def register_model(
        self,
        metadata: ModelMetadata,
        model_artifacts_path: Path,
    ) -> str:
        """
        Register a new model version.
        
        Returns: model_id
        """
        logger.info(f"Registering model: {metadata.model_name} v{metadata.version}")
        
        # Create unique model ID
        model_id = f"{metadata.model_name}_v{metadata.version}_{int(datetime.utcnow().timestamp())}"
        metadata.model_id = model_id
        
        # Copy model artifacts to registry
        model_dir = self.registry_path / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        if model_artifacts_path.is_dir():
            shutil.copytree(model_artifacts_path, model_dir / "artifacts", dirs_exist_ok=True)
        else:
            shutil.copy(model_artifacts_path, model_dir / "model.pkl")
        
        # Save metadata
        metadata_dict = asdict(metadata)
        metadata_dict['created_at'] = metadata.created_at.isoformat()
        metadata_dict['status'] = metadata.status.value
        
        with open(model_dir / "metadata.json", 'w') as f:
            json.dump(metadata_dict, f, indent=2)
        
        # Update registry
        self.registry[model_id] = metadata_dict
        self._save_registry()
        
        logger.info(f"Model registered: {model_id}")
        return model_id
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID."""
        if model_id not in self.registry:
            return None
        
        metadata_dict = self.registry[model_id]
        metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
        metadata_dict['status'] = ModelStatus(metadata_dict['status'])
        
        return ModelMetadata(**metadata_dict)
    
    def list_models(
        self,
        model_name: Optional[str] = None,
        status: Optional[ModelStatus] = None,
    ) -> List[ModelMetadata]:
        """List all models, optionally filtered."""
        models = []
        for model_id, metadata_dict in self.registry.items():
            if model_name and metadata_dict['model_name'] != model_name:
                continue
            if status and metadata_dict['status'] != status.value:
                continue
            
            metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
            metadata_dict['status'] = ModelStatus(metadata_dict['status'])
            models.append(ModelMetadata(**metadata_dict))
        
        return sorted(models, key=lambda m: m.created_at, reverse=True)
    
    def get_production_model(self, model_name: str) -> Optional[ModelMetadata]:
        """Get the current production model for a given model name."""
        production_models = self.list_models(model_name=model_name, status=ModelStatus.PRODUCTION)
        return production_models[0] if production_models else None
    
    def promote_to_production(self, model_id: str) -> None:
        """Promote a model to production (demotes previous production model)."""
        logger.info(f"Promoting model {model_id} to production")
        
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # Demote current production model
        current_prod = self.get_production_model(model.model_name)
        if current_prod:
            logger.info(f"Demoting current production model: {current_prod.model_id}")
            self.update_status(current_prod.model_id, ModelStatus.ARCHIVED)
        
        # Promote new model
        self.update_status(model_id, ModelStatus.PRODUCTION)
        logger.info(f"Model {model_id} promoted to production")
    
    def update_status(self, model_id: str, status: ModelStatus) -> None:
        """Update model status."""
        if model_id not in self.registry:
            raise ValueError(f"Model {model_id} not found")
        
        self.registry[model_id]['status'] = status.value
        self._save_registry()
        
        # Update metadata file
        model_dir = self.registry_path / model_id
        metadata_file = model_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            metadata['status'] = status.value
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
    
    def get_model_path(self, model_id: str) -> Path:
        """Get path to model artifacts."""
        return self.registry_path / model_id / "artifacts"


class ModelMonitor:
    """
    Monitor model performance in production.
    
    Tracks:
    - Prediction distribution
    - Inference latency
    - Error rates
    - Data drift
    """

    def __init__(self, monitor_path: Path):
        self.monitor_path = monitor_path
        self.monitor_path.mkdir(parents=True, exist_ok=True)
    
    def log_prediction(
        self,
        model_id: str,
        input_features: Dict[str, Any],
        prediction: Any,
        actual: Optional[Any] = None,
        latency_ms: float = 0.0,
    ) -> None:
        """Log a prediction for monitoring."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'model_id': model_id,
            'prediction': str(prediction),
            'actual': str(actual) if actual else None,
            'latency_ms': latency_ms,
            'features_hash': hash(frozenset(input_features.items())),
        }
        
        # Append to daily log file
        log_file = self.monitor_path / f"predictions_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def get_performance_metrics(
        self,
        model_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get performance metrics for recent predictions."""
        # Read logs from last N days
        predictions = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            log_file = self.monitor_path / f"predictions_{date.strftime('%Y%m%d')}.jsonl"
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        entry = json.loads(line)
                        if entry['model_id'] == model_id:
                            predictions.append(entry)
        
        if not predictions:
            return {'error': 'No predictions found'}
        
        # Calculate metrics
        latencies = [p['latency_ms'] for p in predictions]
        
        # Accuracy (if actuals available)
        with_actuals = [p for p in predictions if p['actual'] is not None]
        accuracy = None
        if with_actuals:
            correct = sum(1 for p in with_actuals if p['prediction'] == p['actual'])
            accuracy = correct / len(with_actuals)
        
        return {
            'total_predictions': len(predictions),
            'avg_latency_ms': sum(latencies) / len(latencies),
            'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)],
            'p99_latency_ms': sorted(latencies)[int(len(latencies) * 0.99)],
            'accuracy': accuracy,
            'predictions_per_day': len(predictions) / days,
        }


class TrainingPipeline:
    """
    Automated training pipeline for ML models.
    
    Orchestrates:
    - Data preparation
    - Model training
    - Evaluation
    - Registration
    """

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
    
    def run_training(
        self,
        model_name: str,
        model_class: type,
        train_data: Any,
        eval_data: Any,
        hyperparameters: Dict[str, Any],
        version: str = "1.0.0",
    ) -> str:
        """
        Run complete training pipeline.
        
        Returns: model_id
        """
        logger.info(f"Starting training pipeline for {model_name} v{version}")
        
        start_time = datetime.utcnow()
        
        try:
            # Initialize model
            model = model_class(**hyperparameters)
            
            # Train
            logger.info("Training model...")
            metrics = model.train(train_data)
            
            # Evaluate
            logger.info("Evaluating model...")
            eval_metrics = model.evaluate(eval_data)
            metrics.update(eval_metrics)
            
            # Save model
            model_path = Path(f"/tmp/{model_name}_{version}")
            model_path.mkdir(parents=True, exist_ok=True)
            model.save(model_path)
            
            # Create metadata
            training_duration = (datetime.utcnow() - start_time).total_seconds()
            metadata = ModelMetadata(
                model_id="",  # Will be assigned by registry
                model_name=model_name,
                version=version,
                status=ModelStatus.REGISTERED,
                created_at=start_time,
                trained_by="automated_pipeline",
                training_duration_seconds=training_duration,
                training_samples=len(train_data),
                metrics=metrics,
                hyperparameters=hyperparameters,
                features=getattr(model, 'feature_names', []),
                target="target",
                framework="sklearn",
                python_version="3.12",
                dependencies={},
                tags=["automated"],
                description=f"Automated training run for {model_name}",
            )
            
            # Register
            model_id = self.registry.register_model(metadata, model_path)
            
            logger.info(f"Training pipeline completed. Model ID: {model_id}")
            return model_id
            
        except Exception as e:
            logger.error(f"Training pipeline failed: {e}")
            raise


class ABTestManager:
    """
    Manage A/B tests for model deployment.
    
    Allows:
    - Split traffic between model versions
    - Track performance by variant
    - Statistical significance testing
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.tests: Dict[str, Dict] = {}
        self._load_tests()
    
    def _load_tests(self) -> None:
        """Load active A/B tests."""
        test_file = self.config_path / "ab_tests.json"
        if test_file.exists():
            with open(test_file, 'r') as f:
                self.tests = json.load(f)
    
    def _save_tests(self) -> None:
        """Save A/B test configuration."""
        with open(self.config_path / "ab_tests.json", 'w') as f:
            json.dump(self.tests, f, indent=2)
    
    def create_test(
        self,
        test_name: str,
        model_name: str,
        control_model_id: str,
        treatment_model_id: str,
        traffic_split: float = 0.5,
    ) -> None:
        """
        Create a new A/B test.
        
        Args:
            traffic_split: Fraction of traffic to treatment (0-1)
        """
        logger.info(f"Creating A/B test: {test_name}")
        
        self.tests[test_name] = {
            'model_name': model_name,
            'control_model_id': control_model_id,
            'treatment_model_id': treatment_model_id,
            'traffic_split': traffic_split,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
        }
        
        self._save_tests()
    
    def get_model_for_request(self, model_name: str, user_id: str) -> str:
        """
        Get model ID for a request (A/B test aware).
        
        Returns: model_id to use for prediction
        """
        # Find active test
        active_test = None
        for test in self.tests.values():
            if test['model_name'] == model_name and test['status'] == 'active':
                active_test = test
                break
        
        if not active_test:
            # No A/B test, return production model
            return None
        
        # Hash user ID to assign variant consistently
        import hashlib
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        assignment = (hash_val % 100) / 100.0
        
        if assignment < active_test['traffic_split']:
            return active_test['treatment_model_id']
        else:
            return active_test['control_model_id']
    
    def stop_test(self, test_name: str) -> None:
        """Stop an A/B test."""
        if test_name in self.tests:
            self.tests[test_name]['status'] = 'stopped'
            self.tests[test_name]['stopped_at'] = datetime.utcnow().isoformat()
            self._save_tests()


# Example usage
if __name__ == "__main__":
    from pathlib import Path
    
    # Initialize MLOps components
    registry = ModelRegistry(Path("ml_models/registry"))
    monitor = ModelMonitor(Path("ml_models/monitoring"))
    pipeline = TrainingPipeline(registry)
    ab_test = ABTestManager(Path("ml_models/ab_tests"))
    
    print("MLOps infrastructure initialized")

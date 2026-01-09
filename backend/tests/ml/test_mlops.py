"""
Tests for MLOps Infrastructure: Model Management, Versioning, and Deployment

Tests the ML operations infrastructure including:
- Model registry
- Versioning and rollback
- Training pipeline
- A/B testing
- Performance monitoring
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import tempfile

from sensei.ml.mlops import (
    ModelStatus,
    ModelMetadata,
    ModelRegistry,
    ModelMonitor,
    TrainingPipeline,
    ABTestManager,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_registry_path():
    """Create temporary directory for model registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_model_metadata():
    """Create sample model metadata."""
    return ModelMetadata(
        model_id="",  # Will be assigned by registry
        model_name="lesson_recommender",
        version="1.0.0",
        status=ModelStatus.REGISTERED,
        created_at=datetime.utcnow(),
        trained_by="test_pipeline",
        training_duration_seconds=120.5,
        training_samples=1000,
        metrics={"precision@5": 0.85, "recall@5": 0.78, "f1": 0.81},
        hyperparameters={"n_estimators": 100, "max_depth": 10},
        features=["user_skills", "lesson_tags", "completion_history"],
        target="lesson_recommendation",
        framework="sklearn",
        python_version="3.12",
        dependencies={"scikit-learn": "1.4.0", "numpy": "1.26.0"},
        tags=["production", "v1"],
        description="Lesson recommendation model for training system",
    )


@pytest.fixture
def sample_model_artifacts(temp_registry_path):
    """Create sample model artifacts directory."""
    artifacts_path = temp_registry_path / "artifacts"
    artifacts_path.mkdir()
    
    # Create dummy model files
    (artifacts_path / "model.pkl").write_bytes(b"dummy model")
    (artifacts_path / "vectorizer.pkl").write_bytes(b"dummy vectorizer")
    (artifacts_path / "config.json").write_text('{"version": "1.0.0"}')
    
    return artifacts_path


# =============================================================================
# Test: ModelStatus Enum
# =============================================================================

class TestModelStatus:
    """Test ModelStatus enumeration."""
    
    def test_status_values(self):
        """Test that all expected status values exist."""
        assert ModelStatus.TRAINING == "training"
        assert ModelStatus.REGISTERED == "registered"
        assert ModelStatus.STAGING == "staging"
        assert ModelStatus.PRODUCTION == "production"
        assert ModelStatus.ARCHIVED == "archived"
        assert ModelStatus.FAILED == "failed"
    
    def test_status_is_string(self):
        """Test that status values are strings."""
        for status in ModelStatus:
            assert isinstance(status.value, str)


# =============================================================================
# Test: ModelMetadata Dataclass
# =============================================================================

class TestModelMetadata:
    """Test ModelMetadata dataclass."""
    
    def test_create_metadata(self, sample_model_metadata):
        """Test creating model metadata."""
        assert sample_model_metadata.model_name == "lesson_recommender"
        assert sample_model_metadata.version == "1.0.0"
        assert sample_model_metadata.status == ModelStatus.REGISTERED
    
    def test_metadata_has_all_fields(self, sample_model_metadata):
        """Test that metadata has all required fields."""
        assert hasattr(sample_model_metadata, 'model_id')
        assert hasattr(sample_model_metadata, 'model_name')
        assert hasattr(sample_model_metadata, 'version')
        assert hasattr(sample_model_metadata, 'status')
        assert hasattr(sample_model_metadata, 'created_at')
        assert hasattr(sample_model_metadata, 'trained_by')
        assert hasattr(sample_model_metadata, 'training_duration_seconds')
        assert hasattr(sample_model_metadata, 'training_samples')
        assert hasattr(sample_model_metadata, 'metrics')
        assert hasattr(sample_model_metadata, 'hyperparameters')
        assert hasattr(sample_model_metadata, 'features')
        assert hasattr(sample_model_metadata, 'target')
        assert hasattr(sample_model_metadata, 'framework')
        assert hasattr(sample_model_metadata, 'python_version')
        assert hasattr(sample_model_metadata, 'dependencies')
        assert hasattr(sample_model_metadata, 'tags')
        assert hasattr(sample_model_metadata, 'description')


# =============================================================================
# Test: ModelRegistry
# =============================================================================

class TestModelRegistry:
    """Test ModelRegistry for model management."""
    
    def test_init_creates_registry_directory(self, temp_registry_path):
        """Test that initializing registry creates directory."""
        registry = ModelRegistry(temp_registry_path / "registry")
        assert (temp_registry_path / "registry").exists()
    
    def test_register_model(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test registering a new model."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        assert model_id is not None
        assert "lesson_recommender" in model_id
        assert "1.0.0" in model_id
    
    def test_register_model_creates_artifacts(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test that registering model copies artifacts."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        # Check artifacts were copied
        model_path = registry.get_model_path(model_id)
        assert model_path.exists()
        assert (model_path / "model.pkl").exists()
    
    def test_get_model(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test retrieving model by ID."""
        registry = ModelRegistry(temp_registry_path / "registry")
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        model = registry.get_model(model_id)
        
        assert model is not None
        assert model.model_name == "lesson_recommender"
        assert model.version == "1.0.0"
    
    def test_get_nonexistent_model(self, temp_registry_path):
        """Test retrieving non-existent model returns None."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        model = registry.get_model("nonexistent_model_id")
        
        assert model is None
    
    def test_list_models(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test listing all models."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        # Register multiple models
        registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        sample_model_metadata.version = "1.1.0"
        registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        models = registry.list_models()
        
        assert len(models) == 2
    
    def test_list_models_by_name(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test listing models filtered by name."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        # Register models with different names
        registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        sample_model_metadata.model_name = "evidence_detector"
        registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        models = registry.list_models(model_name="lesson_recommender")
        
        assert len(models) == 1
        assert models[0].model_name == "lesson_recommender"
    
    def test_list_models_by_status(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test listing models filtered by status."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        registry.update_status(model_id, ModelStatus.PRODUCTION)
        
        models = registry.list_models(status=ModelStatus.PRODUCTION)
        
        assert len(models) == 1
        assert models[0].status == ModelStatus.PRODUCTION
    
    def test_promote_to_production(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test promoting model to production."""
        registry = ModelRegistry(temp_registry_path / "registry")
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        registry.promote_to_production(model_id)
        
        model = registry.get_model(model_id)
        assert model.status == ModelStatus.PRODUCTION
    
    def test_promote_demotes_previous_production(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test that promoting new model demotes previous production model."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        # Register and promote first model
        model_id_1 = registry.register_model(sample_model_metadata, sample_model_artifacts)
        registry.promote_to_production(model_id_1)
        
        # Register and promote second model
        sample_model_metadata.version = "2.0.0"
        model_id_2 = registry.register_model(sample_model_metadata, sample_model_artifacts)
        registry.promote_to_production(model_id_2)
        
        # First model should be archived
        model_1 = registry.get_model(model_id_1)
        model_2 = registry.get_model(model_id_2)
        
        assert model_1.status == ModelStatus.ARCHIVED
        assert model_2.status == ModelStatus.PRODUCTION
    
    def test_get_production_model(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test getting current production model."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        registry.promote_to_production(model_id)
        
        production_model = registry.get_production_model("lesson_recommender")
        
        assert production_model is not None
        assert production_model.model_id == model_id
        assert production_model.status == ModelStatus.PRODUCTION
    
    def test_update_status(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test updating model status."""
        registry = ModelRegistry(temp_registry_path / "registry")
        model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
        
        registry.update_status(model_id, ModelStatus.STAGING)
        
        model = registry.get_model(model_id)
        assert model.status == ModelStatus.STAGING
    
    def test_update_status_nonexistent_raises(self, temp_registry_path):
        """Test updating status of non-existent model raises error."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        with pytest.raises(ValueError, match="not found"):
            registry.update_status("nonexistent", ModelStatus.PRODUCTION)
    
    def test_registry_persists(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test that registry data persists across instances."""
        registry_path = temp_registry_path / "registry"
        
        # Register model with first instance
        registry1 = ModelRegistry(registry_path)
        model_id = registry1.register_model(sample_model_metadata, sample_model_artifacts)
        
        # Create new instance and verify model exists
        registry2 = ModelRegistry(registry_path)
        model = registry2.get_model(model_id)
        
        assert model is not None
        assert model.model_name == "lesson_recommender"


# =============================================================================
# Test: ModelMonitor
# =============================================================================

class TestModelMonitor:
    """Test ModelMonitor for performance tracking."""
    
    def test_init_creates_directory(self, temp_registry_path):
        """Test that initializing monitor creates directory."""
        monitor = ModelMonitor(temp_registry_path / "monitoring")
        assert (temp_registry_path / "monitoring").exists()
    
    def test_log_prediction(self, temp_registry_path):
        """Test logging a prediction."""
        monitor = ModelMonitor(temp_registry_path / "monitoring")
        
        monitor.log_prediction(
            model_id="model_123",
            input_features={"user_id": "U001", "skills": ["5S"]},
            prediction="L001",
            actual="L001",
            latency_ms=15.5,
        )
        
        # Check log file was created
        log_files = list((temp_registry_path / "monitoring").glob("predictions_*.jsonl"))
        assert len(log_files) == 1
    
    def test_log_prediction_appends(self, temp_registry_path):
        """Test that multiple predictions are appended."""
        monitor = ModelMonitor(temp_registry_path / "monitoring")
        
        for i in range(5):
            monitor.log_prediction(
                model_id="model_123",
                input_features={"user_id": f"U{i:03d}"},
                prediction=f"L{i:03d}",
                latency_ms=10.0 + i,
            )
        
        # Read log file and count entries
        log_files = list((temp_registry_path / "monitoring").glob("predictions_*.jsonl"))
        with open(log_files[0], 'r') as f:
            entries = f.readlines()
        
        assert len(entries) == 5
    
    def test_get_performance_metrics(self, temp_registry_path):
        """Test getting performance metrics."""
        monitor = ModelMonitor(temp_registry_path / "monitoring")
        
        # Log some predictions
        for i in range(10):
            monitor.log_prediction(
                model_id="model_123",
                input_features={"user_id": f"U{i:03d}"},
                prediction="L001" if i % 2 == 0 else "L002",
                actual="L001",
                latency_ms=10.0 + i,
            )
        
        metrics = monitor.get_performance_metrics("model_123", days=7)
        
        assert 'total_predictions' in metrics
        assert 'avg_latency_ms' in metrics
        assert metrics['total_predictions'] == 10
    
    def test_get_performance_metrics_no_data(self, temp_registry_path):
        """Test getting metrics when no data exists."""
        monitor = ModelMonitor(temp_registry_path / "monitoring")
        
        metrics = monitor.get_performance_metrics("nonexistent_model", days=7)
        
        assert 'error' in metrics


# =============================================================================
# Test: ABTestManager
# =============================================================================

class TestABTestManager:
    """Test ABTestManager for A/B testing."""
    
    def test_init_creates_directory(self, temp_registry_path):
        """Test that initializing creates directory."""
        manager = ABTestManager(temp_registry_path / "ab_tests")
        assert (temp_registry_path / "ab_tests").exists()
    
    def test_create_test(self, temp_registry_path):
        """Test creating an A/B test."""
        manager = ABTestManager(temp_registry_path / "ab_tests")
        
        manager.create_test(
            test_name="recommender_v2_test",
            model_name="lesson_recommender",
            control_model_id="model_v1",
            treatment_model_id="model_v2",
            traffic_split=0.5,
        )
        
        assert "recommender_v2_test" in manager.tests
        assert manager.tests["recommender_v2_test"]["status"] == "active"
    
    def test_get_model_for_request_consistent(self, temp_registry_path):
        """Test that user assignment is consistent."""
        manager = ABTestManager(temp_registry_path / "ab_tests")
        
        manager.create_test(
            test_name="test_1",
            model_name="lesson_recommender",
            control_model_id="model_v1",
            treatment_model_id="model_v2",
            traffic_split=0.5,
        )
        
        # Same user should always get same model
        user_id = "user_123"
        model_1 = manager.get_model_for_request("lesson_recommender", user_id)
        model_2 = manager.get_model_for_request("lesson_recommender", user_id)
        
        assert model_1 == model_2
    
    def test_get_model_for_request_no_active_test(self, temp_registry_path):
        """Test getting model when no active test exists."""
        manager = ABTestManager(temp_registry_path / "ab_tests")
        
        model = manager.get_model_for_request("lesson_recommender", "user_123")
        
        assert model is None
    
    def test_stop_test(self, temp_registry_path):
        """Test stopping an A/B test."""
        manager = ABTestManager(temp_registry_path / "ab_tests")
        
        manager.create_test(
            test_name="test_to_stop",
            model_name="lesson_recommender",
            control_model_id="model_v1",
            treatment_model_id="model_v2",
            traffic_split=0.5,
        )
        
        manager.stop_test("test_to_stop")
        
        assert manager.tests["test_to_stop"]["status"] == "stopped"
        assert "stopped_at" in manager.tests["test_to_stop"]
    
    def test_traffic_split_distribution(self, temp_registry_path):
        """Test that traffic split is roughly correct."""
        manager = ABTestManager(temp_registry_path / "ab_tests")
        
        manager.create_test(
            test_name="distribution_test",
            model_name="lesson_recommender",
            control_model_id="control",
            treatment_model_id="treatment",
            traffic_split=0.5,
        )
        
        # Simulate many users
        control_count = 0
        treatment_count = 0
        
        for i in range(1000):
            model = manager.get_model_for_request("lesson_recommender", f"user_{i}")
            if model == "control":
                control_count += 1
            else:
                treatment_count += 1
        
        # Should be roughly 50/50 (allow for some variance)
        assert 400 < control_count < 600
        assert 400 < treatment_count < 600


# =============================================================================
# Test: TrainingPipeline
# =============================================================================

class TestTrainingPipeline:
    """Test TrainingPipeline for automated training."""
    
    def test_init_with_registry(self, temp_registry_path):
        """Test initializing pipeline with registry."""
        registry = ModelRegistry(temp_registry_path / "registry")
        pipeline = TrainingPipeline(registry)
        
        assert pipeline.registry == registry


# =============================================================================
# Test: Rollback Scenarios
# =============================================================================

class TestRollbackScenarios:
    """Test model rollback scenarios."""
    
    def test_rollback_to_previous_version(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test rolling back to a previous version."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        # Register and promote v1
        model_id_v1 = registry.register_model(sample_model_metadata, sample_model_artifacts)
        registry.promote_to_production(model_id_v1)
        
        # Register and promote v2
        sample_model_metadata.version = "2.0.0"
        model_id_v2 = registry.register_model(sample_model_metadata, sample_model_artifacts)
        registry.promote_to_production(model_id_v2)
        
        # Rollback: promote v1 again
        registry.update_status(model_id_v1, ModelStatus.REGISTERED)  # Unarchive
        registry.promote_to_production(model_id_v1)
        
        # v1 should be production, v2 should be archived
        model_v1 = registry.get_model(model_id_v1)
        model_v2 = registry.get_model(model_id_v2)
        
        assert model_v1.status == ModelStatus.PRODUCTION
        assert model_v2.status == ModelStatus.ARCHIVED
    
    def test_version_history_maintained(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test that version history is maintained."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        # Register multiple versions
        versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
        model_ids = []
        
        for version in versions:
            sample_model_metadata.version = version
            model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
            model_ids.append(model_id)
        
        # List all models for this name
        models = registry.list_models(model_name="lesson_recommender")
        
        assert len(models) == 4
        
        # Versions should all be different
        model_versions = {m.version for m in models}
        assert len(model_versions) == 4


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestMLOpsEdgeCases:
    """Test edge cases and error handling."""
    
    def test_registry_with_empty_metadata(self, temp_registry_path, sample_model_artifacts):
        """Test handling minimal metadata."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        minimal_metadata = ModelMetadata(
            model_id="",
            model_name="minimal",
            version="0.0.1",
            status=ModelStatus.REGISTERED,
            created_at=datetime.utcnow(),
            trained_by="test",
            training_duration_seconds=1.0,
            training_samples=1,
            metrics={},
            hyperparameters={},
            features=[],
            target="",
            framework="sklearn",
            python_version="3.12",
            dependencies={},
            tags=[],
            description="",
        )
        
        model_id = registry.register_model(minimal_metadata, sample_model_artifacts)
        assert model_id is not None
    
    def test_concurrent_registrations(self, temp_registry_path, sample_model_metadata, sample_model_artifacts):
        """Test that concurrent registrations get unique IDs."""
        registry = ModelRegistry(temp_registry_path / "registry")
        
        # Register same model multiple times rapidly
        model_ids = []
        for i in range(5):
            sample_model_metadata.version = f"1.0.{i}"
            model_id = registry.register_model(sample_model_metadata, sample_model_artifacts)
            model_ids.append(model_id)
        
        # All IDs should be unique
        assert len(set(model_ids)) == 5

"""
Tests for Enhanced ML Pipeline Service.

Tests world-class ML infrastructure capabilities:
- Feature Store with point-in-time retrieval
- Model Registry with versioning
- Drift detection (PSI, KS, Chi-Square)
- A/B testing
- Experiment tracking
- Model monitoring
- AutoML
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from sensei.services.enhanced_ml_pipeline import (
    # Enums
    ModelType,
    ModelStage,
    ModelStatus,
    DriftType,
    DriftSeverity,
    FeatureType,
    ExperimentStatus,
    PipelineStage,
    # Data models
    FeatureDefinition,
    FeatureVector,
    FeatureGroup,
    TrainingDataset,
    ModelMetrics,
    ModelVersion,
    ModelRegistry,
    DriftDetectionResult,
    Experiment,
    ABTest,
    PredictionLog,
    MonitoringAlert,
    # Components
    FeatureStore,
    ModelRegistryService,
    DriftDetector,
    ExperimentTracker,
    AutoMLService,
    ModelMonitor,
    EnhancedMLPipelineService,
)


# =============================================================================
# FeatureDefinition Tests
# =============================================================================


class TestFeatureDefinition:
    """Tests for FeatureDefinition class."""
    
    def test_feature_definition_creation(self):
        """Test basic feature definition creation."""
        feature = FeatureDefinition(
            name="temperature",
            feature_type=FeatureType.NUMERICAL,
            description="Temperature reading in Celsius",
            default_value=25.0,
        )
        
        assert feature.name == "temperature"
        assert feature.feature_type == FeatureType.NUMERICAL
    
    def test_feature_definition_with_constraints(self):
        """Test feature definition with validation constraints."""
        feature = FeatureDefinition(
            name="pressure",
            feature_type=FeatureType.NUMERICAL,
            min_value=0.0,
            max_value=100.0,
            nullable=False,
        )
        
        assert feature.min_value == 0.0
        assert feature.max_value == 100.0
    
    def test_categorical_feature(self):
        """Test categorical feature definition."""
        feature = FeatureDefinition(
            name="status",
            feature_type=FeatureType.CATEGORICAL,
            categories=["active", "inactive", "pending"],
        )
        
        assert len(feature.categories) == 3


# =============================================================================
# FeatureVector Tests
# =============================================================================


class TestFeatureVector:
    """Tests for FeatureVector class."""
    
    def test_feature_vector_creation(self):
        """Test feature vector creation."""
        vector = FeatureVector(
            entity_id="user_123",
            features={"age": 30, "income": 50000.0, "status": "active"},
            timestamp=datetime.utcnow(),
        )
        
        assert vector.entity_id == "user_123"
        assert len(vector.features) == 3
    
    def test_feature_vector_to_array(self):
        """Test conversion to numpy array."""
        vector = FeatureVector(
            entity_id="e1",
            features={"f1": 1.0, "f2": 2.0, "f3": 3.0},
            timestamp=datetime.utcnow(),
        )
        
        arr = vector.to_array(["f1", "f2", "f3"])
        
        assert isinstance(arr, np.ndarray)
        assert len(arr) == 3
    
    def test_feature_vector_to_array_with_missing(self):
        """Test array conversion with missing features."""
        vector = FeatureVector(
            entity_id="e1",
            features={"f1": 1.0, "f3": 3.0},
            timestamp=datetime.utcnow(),
        )
        
        arr = vector.to_array(["f1", "f2", "f3"], fill_value=0.0)
        
        assert arr[1] == 0.0  # f2 is missing


# =============================================================================
# FeatureGroup Tests
# =============================================================================


class TestFeatureGroup:
    """Tests for FeatureGroup class."""
    
    def test_feature_group_creation(self):
        """Test feature group creation."""
        features = [
            FeatureDefinition("f1", FeatureType.NUMERICAL),
            FeatureDefinition("f2", FeatureType.CATEGORICAL, categories=["a", "b"]),
        ]
        
        group = FeatureGroup(
            name="user_features",
            features=features,
            entity_key="user_id",
        )
        
        assert group.name == "user_features"
        assert len(group.features) == 2
    
    def test_feature_group_get_feature(self):
        """Test getting feature by name."""
        features = [
            FeatureDefinition("f1", FeatureType.NUMERICAL),
            FeatureDefinition("f2", FeatureType.NUMERICAL),
        ]
        
        group = FeatureGroup(
            name="test_group",
            features=features,
            entity_key="id",
        )
        
        f1 = group.get_feature("f1")
        
        assert f1 is not None
        assert f1.name == "f1"
    
    def test_feature_group_feature_names(self):
        """Test getting feature names."""
        features = [
            FeatureDefinition("a", FeatureType.NUMERICAL),
            FeatureDefinition("b", FeatureType.NUMERICAL),
            FeatureDefinition("c", FeatureType.NUMERICAL),
        ]
        
        group = FeatureGroup("g", features, "id")
        
        assert group.feature_names == ["a", "b", "c"]


# =============================================================================
# ModelMetrics Tests
# =============================================================================


class TestModelMetrics:
    """Tests for ModelMetrics class."""
    
    def test_model_metrics_classification(self):
        """Test classification metrics."""
        metrics = ModelMetrics(
            accuracy=0.95,
            precision=0.93,
            recall=0.92,
            f1_score=0.925,
            auc_roc=0.98,
        )
        
        assert metrics.accuracy == 0.95
        assert metrics.f1_score == 0.925
    
    def test_model_metrics_regression(self):
        """Test regression metrics."""
        metrics = ModelMetrics(
            mse=0.05,
            rmse=0.223,
            mae=0.15,
            r2=0.92,
        )
        
        assert metrics.mse == 0.05
        assert metrics.r2 == 0.92
    
    def test_model_metrics_custom(self):
        """Test custom metrics."""
        metrics = ModelMetrics(
            custom_metrics={
                "business_metric": 0.85,
                "latency_p99": 45.0,
            }
        )
        
        assert metrics.custom_metrics["business_metric"] == 0.85


# =============================================================================
# ModelVersion Tests
# =============================================================================


class TestModelVersion:
    """Tests for ModelVersion class."""
    
    def test_model_version_creation(self):
        """Test model version creation."""
        version = ModelVersion(
            version_id="v1",
            model_name="predictor",
            model_type=ModelType.CLASSIFICATION,
            version="1.0.0",
            stage=ModelStage.STAGING,
            status=ModelStatus.ACTIVE,
            created_at=datetime.utcnow(),
        )
        
        assert version.version == "1.0.0"
        assert version.stage == ModelStage.STAGING
    
    def test_model_version_with_metrics(self):
        """Test model version with performance metrics."""
        metrics = ModelMetrics(accuracy=0.95, f1_score=0.93)
        
        version = ModelVersion(
            version_id="v1",
            model_name="classifier",
            model_type=ModelType.CLASSIFICATION,
            version="1.0.0",
            stage=ModelStage.PRODUCTION,
            status=ModelStatus.ACTIVE,
            created_at=datetime.utcnow(),
            metrics=metrics,
        )
        
        assert version.metrics.accuracy == 0.95
    
    def test_model_version_is_production(self):
        """Test production check."""
        prod_version = ModelVersion(
            "v1", "model", ModelType.CLASSIFICATION, "1.0",
            ModelStage.PRODUCTION, ModelStatus.ACTIVE, datetime.utcnow()
        )
        
        staging_version = ModelVersion(
            "v2", "model", ModelType.CLASSIFICATION, "2.0",
            ModelStage.STAGING, ModelStatus.ACTIVE, datetime.utcnow()
        )
        
        assert prod_version.is_production is True
        assert staging_version.is_production is False


# =============================================================================
# DriftDetectionResult Tests
# =============================================================================


class TestDriftDetectionResult:
    """Tests for DriftDetectionResult class."""
    
    def test_drift_result_no_drift(self):
        """Test drift result with no drift detected."""
        result = DriftDetectionResult(
            feature_name="temperature",
            drift_type=DriftType.FEATURE,
            drift_detected=False,
            severity=DriftSeverity.NONE,
            score=0.02,
            threshold=0.1,
        )
        
        assert result.drift_detected is False
        assert result.severity == DriftSeverity.NONE
    
    def test_drift_result_with_drift(self):
        """Test drift result with drift detected."""
        result = DriftDetectionResult(
            feature_name="user_age",
            drift_type=DriftType.FEATURE,
            drift_detected=True,
            severity=DriftSeverity.HIGH,
            score=0.35,
            threshold=0.1,
            details={"psi": 0.35, "reference_mean": 30.5, "current_mean": 45.2},
        )
        
        assert result.drift_detected is True
        assert result.severity == DriftSeverity.HIGH
        assert result.details["psi"] == 0.35


# =============================================================================
# Experiment Tests
# =============================================================================


class TestExperiment:
    """Tests for Experiment class."""
    
    def test_experiment_creation(self):
        """Test experiment creation."""
        experiment = Experiment(
            experiment_id="exp_001",
            name="Hyperparameter Tuning",
            status=ExperimentStatus.RUNNING,
            parameters={"learning_rate": 0.01, "epochs": 100},
            started_at=datetime.utcnow(),
        )
        
        assert experiment.experiment_id == "exp_001"
        assert experiment.status == ExperimentStatus.RUNNING
    
    def test_experiment_with_results(self):
        """Test experiment with results."""
        experiment = Experiment(
            experiment_id="exp_002",
            name="Model Comparison",
            status=ExperimentStatus.COMPLETED,
            parameters={"model": "xgboost"},
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow(),
            metrics={"accuracy": 0.94, "f1": 0.92},
        )
        
        assert experiment.metrics["accuracy"] == 0.94
    
    def test_experiment_duration(self):
        """Test experiment duration calculation."""
        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow()
        
        experiment = Experiment(
            experiment_id="exp_003",
            name="Test",
            status=ExperimentStatus.COMPLETED,
            parameters={},
            started_at=start,
            completed_at=end,
        )
        
        duration = experiment.duration
        
        assert duration is not None
        assert duration.total_seconds() >= 7200  # 2 hours


# =============================================================================
# ABTest Tests
# =============================================================================


class TestABTest:
    """Tests for ABTest class."""
    
    def test_ab_test_creation(self):
        """Test A/B test creation."""
        test = ABTest(
            test_id="ab_001",
            name="Model V1 vs V2",
            control_model="model_v1",
            treatment_model="model_v2",
            traffic_split={"control": 0.5, "treatment": 0.5},
            started_at=datetime.utcnow(),
        )
        
        assert test.traffic_split["control"] == 0.5
    
    def test_ab_test_with_results(self):
        """Test A/B test with results."""
        test = ABTest(
            test_id="ab_002",
            name="Algorithm Test",
            control_model="baseline",
            treatment_model="new_algo",
            traffic_split={"control": 0.5, "treatment": 0.5},
            started_at=datetime.utcnow() - timedelta(days=7),
            control_metrics={"conversion": 0.05, "revenue": 100.0},
            treatment_metrics={"conversion": 0.07, "revenue": 140.0},
        )
        
        assert test.treatment_metrics["conversion"] > test.control_metrics["conversion"]
    
    def test_ab_test_lift_calculation(self):
        """Test lift calculation between variants."""
        test = ABTest(
            test_id="ab_003",
            name="Lift Test",
            control_model="a",
            treatment_model="b",
            traffic_split={"control": 0.5, "treatment": 0.5},
            started_at=datetime.utcnow(),
            control_metrics={"metric": 100},
            treatment_metrics={"metric": 110},
        )
        
        lift = test.calculate_lift("metric")
        
        assert lift == 0.1  # 10% lift


# =============================================================================
# FeatureStore Tests
# =============================================================================


class TestFeatureStore:
    """Tests for FeatureStore."""
    
    def test_register_feature_group(self):
        """Test registering a feature group."""
        store = FeatureStore()
        
        features = [
            FeatureDefinition("age", FeatureType.NUMERICAL),
            FeatureDefinition("income", FeatureType.NUMERICAL),
        ]
        
        group = FeatureGroup("user_features", features, "user_id")
        
        store.register_feature_group(group)
        
        assert "user_features" in store.groups
    
    def test_ingest_features(self):
        """Test ingesting feature vectors."""
        store = FeatureStore()
        
        features = [FeatureDefinition("f1", FeatureType.NUMERICAL)]
        group = FeatureGroup("test", features, "id")
        store.register_feature_group(group)
        
        vectors = [
            FeatureVector("e1", {"f1": 1.0}, datetime.utcnow()),
            FeatureVector("e2", {"f1": 2.0}, datetime.utcnow()),
        ]
        
        store.ingest(group.name, vectors)
        
        # Should be able to retrieve
        result = store.get_features("test", "e1")
        
        assert result is not None
        assert result.features["f1"] == 1.0
    
    def test_get_features_point_in_time(self):
        """Test point-in-time feature retrieval."""
        store = FeatureStore()
        
        features = [FeatureDefinition("value", FeatureType.NUMERICAL)]
        group = FeatureGroup("timeseries", features, "sensor_id")
        store.register_feature_group(group)
        
        # Ingest features at different times
        now = datetime.utcnow()
        
        vectors = [
            FeatureVector("s1", {"value": 100.0}, now - timedelta(hours=2)),
            FeatureVector("s1", {"value": 150.0}, now - timedelta(hours=1)),
            FeatureVector("s1", {"value": 200.0}, now),
        ]
        
        for v in vectors:
            store.ingest(group.name, [v])
        
        # Get features as of 1.5 hours ago
        result = store.get_features(
            "timeseries",
            "s1",
            as_of=now - timedelta(hours=1, minutes=30)
        )
        
        # Should get the 2-hour-old value (most recent before the as_of time)
        assert result.features["value"] == 100.0
    
    def test_get_features_for_training(self):
        """Test getting features for training dataset."""
        store = FeatureStore()
        
        features = [
            FeatureDefinition("f1", FeatureType.NUMERICAL),
            FeatureDefinition("f2", FeatureType.NUMERICAL),
        ]
        group = FeatureGroup("features", features, "id")
        store.register_feature_group(group)
        
        # Ingest features
        vectors = [
            FeatureVector(f"e{i}", {"f1": float(i), "f2": float(i * 2)}, datetime.utcnow())
            for i in range(10)
        ]
        store.ingest(group.name, vectors)
        
        # Get training data
        entity_ids = [f"e{i}" for i in range(5)]
        X = store.get_training_features("features", entity_ids, ["f1", "f2"])
        
        assert X.shape == (5, 2)


# =============================================================================
# ModelRegistryService Tests
# =============================================================================


class TestModelRegistryService:
    """Tests for ModelRegistryService."""
    
    def test_register_model(self):
        """Test registering a model."""
        registry = ModelRegistryService()
        
        version = registry.register_model(
            model_name="classifier",
            model_type=ModelType.CLASSIFICATION,
            model_path="/models/classifier_v1.pkl",
            metrics=ModelMetrics(accuracy=0.95),
        )
        
        assert version.version_id is not None
        assert version.stage == ModelStage.DEVELOPMENT
    
    def test_promote_model(self):
        """Test promoting model to staging."""
        registry = ModelRegistryService()
        
        version = registry.register_model(
            model_name="model",
            model_type=ModelType.REGRESSION,
            model_path="/models/model.pkl",
        )
        
        promoted = registry.promote_model(version.version_id, ModelStage.STAGING)
        
        assert promoted.stage == ModelStage.STAGING
    
    def test_promote_to_production(self):
        """Test promoting model to production."""
        registry = ModelRegistryService()
        
        version = registry.register_model(
            model_name="prod_model",
            model_type=ModelType.CLASSIFICATION,
            model_path="/models/prod.pkl",
        )
        
        # Promote through stages
        registry.promote_model(version.version_id, ModelStage.STAGING)
        registry.promote_model(version.version_id, ModelStage.PRODUCTION)
        
        # Should be in production
        prod = registry.get_production_model("prod_model")
        
        assert prod is not None
        assert prod.stage == ModelStage.PRODUCTION
    
    def test_get_model_history(self):
        """Test getting model version history."""
        registry = ModelRegistryService()
        
        # Register multiple versions
        for i in range(3):
            registry.register_model(
                model_name="versioned_model",
                model_type=ModelType.CLASSIFICATION,
                model_path=f"/models/v{i}.pkl",
            )
        
        history = registry.get_model_history("versioned_model")
        
        assert len(history) == 3
    
    def test_archive_model(self):
        """Test archiving a model version."""
        registry = ModelRegistryService()
        
        version = registry.register_model(
            model_name="old_model",
            model_type=ModelType.CLASSIFICATION,
            model_path="/models/old.pkl",
        )
        
        archived = registry.archive_model(version.version_id)
        
        assert archived.stage == ModelStage.ARCHIVED
        assert archived.status == ModelStatus.ARCHIVED


# =============================================================================
# DriftDetector Tests
# =============================================================================


class TestDriftDetector:
    """Tests for DriftDetector."""
    
    def test_detect_no_drift(self):
        """Test detection with no drift."""
        detector = DriftDetector()
        
        # Same distribution
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 1000)
        
        result = detector.detect_feature_drift("feature1", reference, current)
        
        # Minimal drift expected
        assert result.severity in [DriftSeverity.NONE, DriftSeverity.LOW]
    
    def test_detect_significant_drift(self):
        """Test detection with significant drift."""
        detector = DriftDetector()
        
        # Very different distributions
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(5, 2, 1000)  # Shifted mean and variance
        
        result = detector.detect_feature_drift("feature1", reference, current)
        
        assert result.drift_detected is True
        assert result.severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH, DriftSeverity.CRITICAL]
    
    def test_psi_calculation(self):
        """Test Population Stability Index calculation."""
        detector = DriftDetector()
        
        # Same distribution should have low PSI
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(0, 1, 1000)
        
        psi = detector.calculate_psi(reference, current)
        
        assert psi < 0.1  # Low PSI indicates no significant shift
    
    def test_psi_with_shift(self):
        """Test PSI with distribution shift."""
        detector = DriftDetector()
        
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(3, 1, 1000)  # Shifted mean
        
        psi = detector.calculate_psi(reference, current)
        
        assert psi > 0.1  # Higher PSI indicates shift
    
    def test_detect_concept_drift(self):
        """Test concept drift detection."""
        detector = DriftDetector()
        
        # Predictions that drift over time
        reference_predictions = np.random.choice([0, 1], 1000, p=[0.5, 0.5])
        current_predictions = np.random.choice([0, 1], 1000, p=[0.3, 0.7])  # Shifted
        
        result = detector.detect_prediction_drift(reference_predictions, current_predictions)
        
        assert result.drift_type == DriftType.PREDICTION


# =============================================================================
# ExperimentTracker Tests
# =============================================================================


class TestExperimentTracker:
    """Tests for ExperimentTracker."""
    
    def test_start_experiment(self):
        """Test starting an experiment."""
        tracker = ExperimentTracker()
        
        exp = tracker.start_experiment(
            name="Test Experiment",
            parameters={"lr": 0.01, "batch_size": 32},
        )
        
        assert exp.status == ExperimentStatus.RUNNING
        assert exp.parameters["lr"] == 0.01
    
    def test_log_metrics(self):
        """Test logging metrics during experiment."""
        tracker = ExperimentTracker()
        
        exp = tracker.start_experiment("Test", {})
        
        tracker.log_metrics(exp.experiment_id, {"loss": 0.5, "accuracy": 0.8})
        tracker.log_metrics(exp.experiment_id, {"loss": 0.3, "accuracy": 0.9})
        
        history = tracker.get_metric_history(exp.experiment_id)
        
        assert len(history) == 2
    
    def test_complete_experiment(self):
        """Test completing an experiment."""
        tracker = ExperimentTracker()
        
        exp = tracker.start_experiment("Test", {})
        
        completed = tracker.complete_experiment(
            exp.experiment_id,
            final_metrics={"accuracy": 0.95},
        )
        
        assert completed.status == ExperimentStatus.COMPLETED
        assert completed.completed_at is not None
    
    def test_fail_experiment(self):
        """Test marking experiment as failed."""
        tracker = ExperimentTracker()
        
        exp = tracker.start_experiment("Test", {})
        
        failed = tracker.fail_experiment(exp.experiment_id, "Out of memory")
        
        assert failed.status == ExperimentStatus.FAILED
        assert "memory" in failed.error_message.lower()
    
    def test_compare_experiments(self):
        """Test comparing multiple experiments."""
        tracker = ExperimentTracker()
        
        # Run multiple experiments
        exp_ids = []
        for lr in [0.001, 0.01, 0.1]:
            exp = tracker.start_experiment("LR Test", {"lr": lr})
            tracker.complete_experiment(exp.experiment_id, {"accuracy": 0.9 + lr})
            exp_ids.append(exp.experiment_id)
        
        comparison = tracker.compare_experiments(exp_ids, "accuracy")
        
        assert len(comparison) == 3


# =============================================================================
# AutoMLService Tests
# =============================================================================


class TestAutoMLService:
    """Tests for AutoMLService."""
    
    @pytest.mark.asyncio
    async def test_run_automl(self):
        """Test running AutoML."""
        service = AutoMLService()
        
        X = np.random.rand(100, 5)
        y = np.random.randint(0, 2, 100)
        
        result = await service.run(
            X, y,
            task_type="classification",
            time_budget=60,
        )
        
        assert "best_model" in result
        assert "best_score" in result
    
    @pytest.mark.asyncio
    async def test_automl_with_validation(self):
        """Test AutoML with validation split."""
        service = AutoMLService()
        
        X = np.random.rand(100, 3)
        y = np.random.rand(100)
        
        result = await service.run(
            X, y,
            task_type="regression",
            validation_split=0.2,
        )
        
        assert "validation_score" in result
    
    def test_get_search_space(self):
        """Test getting hyperparameter search space."""
        service = AutoMLService()
        
        space = service.get_search_space("classification")
        
        assert "random_forest" in space
        assert "xgboost" in space or "gradient_boosting" in space


# =============================================================================
# ModelMonitor Tests
# =============================================================================


class TestModelMonitor:
    """Tests for ModelMonitor."""
    
    def test_log_prediction(self):
        """Test logging predictions."""
        monitor = ModelMonitor()
        
        log = PredictionLog(
            model_name="classifier",
            model_version="1.0",
            timestamp=datetime.utcnow(),
            features={"f1": 1.0, "f2": 2.0},
            prediction=1,
            probability=0.85,
        )
        
        monitor.log_prediction(log)
        
        assert len(monitor.prediction_logs) == 1
    
    def test_log_prediction_with_ground_truth(self):
        """Test logging prediction with ground truth."""
        monitor = ModelMonitor()
        
        log = PredictionLog(
            model_name="classifier",
            model_version="1.0",
            timestamp=datetime.utcnow(),
            features={"f1": 1.0},
            prediction=1,
            ground_truth=0,  # Wrong prediction
        )
        
        monitor.log_prediction(log)
        
        # Check for alert on error
        assert len(monitor.prediction_logs) == 1
    
    def test_calculate_metrics(self):
        """Test calculating monitoring metrics."""
        monitor = ModelMonitor()
        
        # Log some predictions
        for i in range(10):
            log = PredictionLog(
                model_name="model",
                model_version="1.0",
                timestamp=datetime.utcnow(),
                features={"f": float(i)},
                prediction=i % 2,
                ground_truth=i % 2,
                latency_ms=50.0,
            )
            monitor.log_prediction(log)
        
        metrics = monitor.calculate_metrics("model", "1.0")
        
        assert "accuracy" in metrics
        assert metrics["accuracy"] == 1.0  # All correct
    
    def test_detect_anomalies(self):
        """Test anomaly detection in predictions."""
        monitor = ModelMonitor()
        
        # Log normal predictions
        for i in range(100):
            log = PredictionLog(
                model_name="model",
                model_version="1.0",
                timestamp=datetime.utcnow(),
                features={"f": 50.0},
                prediction=0,
                latency_ms=50.0,
            )
            monitor.log_prediction(log)
        
        # Log anomalous prediction
        anomaly_log = PredictionLog(
            model_name="model",
            model_version="1.0",
            timestamp=datetime.utcnow(),
            features={"f": 1000.0},  # Unusual feature value
            prediction=1,
            latency_ms=5000.0,  # High latency
        )
        monitor.log_prediction(anomaly_log)
        
        anomalies = monitor.detect_anomalies("model", "1.0")
        
        assert len(anomalies) > 0
    
    def test_create_alert(self):
        """Test alert creation."""
        monitor = ModelMonitor()
        
        alert = monitor.create_alert(
            model_name="model",
            alert_type="drift",
            severity=DriftSeverity.HIGH,
            message="Feature drift detected",
        )
        
        assert alert.severity == DriftSeverity.HIGH
        assert len(monitor.alerts) == 1


# =============================================================================
# EnhancedMLPipelineService Tests
# =============================================================================


class TestEnhancedMLPipelineService:
    """Tests for EnhancedMLPipelineService."""
    
    @pytest.mark.asyncio
    async def test_train_model(self):
        """Test model training."""
        service = EnhancedMLPipelineService()
        
        X = np.random.rand(100, 5)
        y = np.random.randint(0, 2, 100)
        
        result = await service.train_model(
            model_name="test_classifier",
            model_type=ModelType.CLASSIFICATION,
            X=X,
            y=y,
        )
        
        assert "model_version" in result
        assert "metrics" in result
    
    @pytest.mark.asyncio
    async def test_train_with_feature_store(self):
        """Test training with feature store integration."""
        service = EnhancedMLPipelineService()
        
        # Register features
        features = [
            FeatureDefinition("f1", FeatureType.NUMERICAL),
            FeatureDefinition("f2", FeatureType.NUMERICAL),
        ]
        group = FeatureGroup("training_features", features, "id")
        service.feature_store.register_feature_group(group)
        
        # Ingest features
        vectors = [
            FeatureVector(f"e{i}", {"f1": float(i), "f2": float(i*2)}, datetime.utcnow())
            for i in range(50)
        ]
        service.feature_store.ingest("training_features", vectors)
        
        # Train with feature store
        entity_ids = [f"e{i}" for i in range(50)]
        labels = [i % 2 for i in range(50)]
        
        result = await service.train_model_from_features(
            model_name="feature_model",
            model_type=ModelType.CLASSIFICATION,
            feature_group="training_features",
            entity_ids=entity_ids,
            labels=labels,
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_deploy_model(self):
        """Test model deployment."""
        service = EnhancedMLPipelineService()
        
        # Train a model first
        X = np.random.rand(50, 3)
        y = np.random.randint(0, 2, 50)
        
        train_result = await service.train_model(
            model_name="deploy_test",
            model_type=ModelType.CLASSIFICATION,
            X=X,
            y=y,
        )
        
        # Deploy
        deploy_result = service.deploy_model(train_result["model_version"])
        
        assert deploy_result["status"] == "deployed"
        assert deploy_result["stage"] == ModelStage.PRODUCTION
    
    @pytest.mark.asyncio
    async def test_predict(self):
        """Test making predictions."""
        service = EnhancedMLPipelineService()
        
        # Train and deploy
        X = np.random.rand(50, 3)
        y = np.random.randint(0, 2, 50)
        
        train_result = await service.train_model(
            "predictor", ModelType.CLASSIFICATION, X, y
        )
        service.deploy_model(train_result["model_version"])
        
        # Predict
        X_test = np.random.rand(5, 3)
        predictions = await service.predict("predictor", X_test)
        
        assert len(predictions) == 5
    
    def test_get_pipeline_health(self):
        """Test getting pipeline health status."""
        service = EnhancedMLPipelineService()
        
        health = service.get_pipeline_health()
        
        assert "feature_store" in health
        assert "model_registry" in health
        assert "monitoring" in health
    
    @pytest.mark.asyncio
    async def test_run_ab_test(self):
        """Test A/B testing."""
        service = EnhancedMLPipelineService()
        
        # Create two models
        X = np.random.rand(100, 3)
        y = np.random.randint(0, 2, 100)
        
        v1 = await service.train_model("model_a", ModelType.CLASSIFICATION, X, y)
        v2 = await service.train_model("model_b", ModelType.CLASSIFICATION, X, y)
        
        # Start A/B test
        ab_test = service.start_ab_test(
            name="Model Comparison",
            control_version=v1["model_version"],
            treatment_version=v2["model_version"],
            traffic_split=0.5,
        )
        
        assert ab_test is not None
        assert ab_test.control_model is not None
    
    def test_check_drift(self):
        """Test drift checking."""
        service = EnhancedMLPipelineService()
        
        # Simulate reference and current data
        reference = np.random.normal(0, 1, (100, 3))
        current = np.random.normal(0.5, 1, (100, 3))  # Slight shift
        
        drift_results = service.check_drift(
            feature_names=["f1", "f2", "f3"],
            reference_data=reference,
            current_data=current,
        )
        
        assert len(drift_results) == 3
        for result in drift_results:
            assert result.drift_type == DriftType.FEATURE


# =============================================================================
# Integration Tests
# =============================================================================


class TestEnhancedMLPipelineIntegration:
    """Integration tests for Enhanced ML Pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_ml_workflow(self):
        """Test complete ML workflow."""
        service = EnhancedMLPipelineService()
        
        # 1. Set up features
        features = [
            FeatureDefinition("feature_a", FeatureType.NUMERICAL),
            FeatureDefinition("feature_b", FeatureType.NUMERICAL),
            FeatureDefinition("feature_c", FeatureType.NUMERICAL),
        ]
        group = FeatureGroup("workflow_features", features, "sample_id")
        service.feature_store.register_feature_group(group)
        
        # 2. Generate training data
        X = np.random.rand(100, 3)
        y = (X[:, 0] + X[:, 1] > 1).astype(int)
        
        # 3. Train model
        train_result = await service.train_model(
            model_name="workflow_model",
            model_type=ModelType.CLASSIFICATION,
            X=X,
            y=y,
        )
        
        # 4. Deploy model
        service.deploy_model(train_result["model_version"])
        
        # 5. Make predictions and log
        X_test = np.random.rand(10, 3)
        predictions = await service.predict("workflow_model", X_test)
        
        # 6. Check for drift
        current_X = np.random.normal(0.5, 1, (50, 3))  # Shifted distribution
        drift_results = service.check_drift(
            ["feature_a", "feature_b", "feature_c"],
            X,
            current_X,
        )
        
        # 7. Get pipeline health
        health = service.get_pipeline_health()
        
        assert len(predictions) == 10
        assert len(drift_results) == 3
        assert health is not None
    
    @pytest.mark.asyncio
    async def test_experiment_tracking_integration(self):
        """Test experiment tracking integration."""
        service = EnhancedMLPipelineService()
        
        # Start experiment
        exp = service.experiment_tracker.start_experiment(
            name="Hyperparameter Search",
            parameters={"search_type": "grid"},
        )
        
        best_accuracy = 0
        best_params = None
        
        # Try different hyperparameters
        for lr in [0.001, 0.01, 0.1]:
            for batch_size in [16, 32, 64]:
                # Simulate training
                accuracy = np.random.rand() * 0.2 + 0.8
                
                service.experiment_tracker.log_metrics(exp.experiment_id, {
                    "lr": lr,
                    "batch_size": batch_size,
                    "accuracy": accuracy,
                })
                
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_params = {"lr": lr, "batch_size": batch_size}
        
        # Complete experiment
        service.experiment_tracker.complete_experiment(
            exp.experiment_id,
            {"best_accuracy": best_accuracy, **best_params},
        )
        
        history = service.experiment_tracker.get_metric_history(exp.experiment_id)
        
        assert len(history) == 9  # 3 * 3 combinations


# =============================================================================
# Edge Cases
# =============================================================================


class TestEnhancedMLPipelineEdgeCases:
    """Edge case tests for Enhanced ML Pipeline."""
    
    @pytest.mark.asyncio
    async def test_train_with_single_sample(self):
        """Test training with single sample."""
        service = EnhancedMLPipelineService()
        
        X = np.random.rand(1, 3)
        y = np.array([0])
        
        # Should handle gracefully
        with pytest.raises(ValueError):
            await service.train_model("single", ModelType.CLASSIFICATION, X, y)
    
    def test_predict_without_deployment(self):
        """Test prediction without deployed model."""
        service = EnhancedMLPipelineService()
        
        X = np.random.rand(5, 3)
        
        with pytest.raises(ValueError, match="not found|not deployed"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.predict("nonexistent", X)
            )
    
    def test_drift_with_empty_data(self):
        """Test drift detection with empty data."""
        service = EnhancedMLPipelineService()
        
        reference = np.array([])
        current = np.array([])
        
        results = service.check_drift(["f1"], reference.reshape(-1, 1), current.reshape(-1, 1))
        
        # Should handle gracefully
        assert len(results) == 0 or not results[0].drift_detected
    
    def test_feature_store_missing_entity(self):
        """Test feature store with missing entity."""
        store = FeatureStore()
        
        features = [FeatureDefinition("f1", FeatureType.NUMERICAL)]
        group = FeatureGroup("test", features, "id")
        store.register_feature_group(group)
        
        result = store.get_features("test", "nonexistent")
        
        assert result is None


# =============================================================================
# Performance Tests
# =============================================================================


class TestEnhancedMLPipelinePerformance:
    """Performance tests for Enhanced ML Pipeline."""
    
    @pytest.mark.asyncio
    async def test_training_performance(self):
        """Test training performance."""
        service = EnhancedMLPipelineService()
        
        # Larger dataset
        X = np.random.rand(1000, 10)
        y = np.random.randint(0, 2, 1000)
        
        import time
        start = time.time()
        
        result = await service.train_model(
            "perf_model",
            ModelType.CLASSIFICATION,
            X, y,
        )
        
        elapsed = time.time() - start
        
        assert elapsed < 60  # Should complete within 60 seconds
    
    def test_feature_store_throughput(self):
        """Test feature store ingestion throughput."""
        store = FeatureStore()
        
        features = [FeatureDefinition(f"f{i}", FeatureType.NUMERICAL) for i in range(10)]
        group = FeatureGroup("throughput_test", features, "id")
        store.register_feature_group(group)
        
        # Generate many vectors
        vectors = [
            FeatureVector(
                f"e{i}",
                {f"f{j}": float(i + j) for j in range(10)},
                datetime.utcnow(),
            )
            for i in range(1000)
        ]
        
        import time
        start = time.time()
        
        store.ingest("throughput_test", vectors)
        
        elapsed = time.time() - start
        
        # Should handle 1000 vectors quickly
        assert elapsed < 5
    
    @pytest.mark.asyncio
    async def test_prediction_latency(self):
        """Test prediction latency."""
        service = EnhancedMLPipelineService()
        
        # Train and deploy
        X = np.random.rand(100, 5)
        y = np.random.randint(0, 2, 100)
        
        result = await service.train_model("latency_test", ModelType.CLASSIFICATION, X, y)
        service.deploy_model(result["model_version"])
        
        # Measure prediction latency
        X_test = np.random.rand(1, 5)
        
        import time
        start = time.time()
        
        for _ in range(100):
            await service.predict("latency_test", X_test)
        
        elapsed = time.time() - start
        avg_latency = elapsed / 100 * 1000  # ms
        
        assert avg_latency < 100  # Should be under 100ms on average

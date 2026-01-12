"""
Tests for the Continuous Learning System.

Tests cover:
- FeedbackCollector: Collecting and preparing training feedback
- IncrementalLearner: Online/incremental model updates
- RetrainingManager: Auto-retraining triggers and execution
- ContinuousLearningService: End-to-end continuous learning
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from sensei.services.ai.continuous_learning import (
    FeedbackCollector,
    IncrementalLearner,
    RetrainingManager,
    ContinuousLearningService,
    LearningFeedback,
    RetrainingJob,
    RetrainingConfig,
    ModelLearningState,
    LearningMode,
    RetrainingTrigger,
    FeedbackSource,
    get_continuous_learning_service,
    reset_continuous_learning_service,
)
from sensei.services.ai.enhanced_ml_pipeline import (
    DriftSeverity,
    DriftDetectionResult,
    DriftType,
    ModelType,
)


# =============================================================================
# FeedbackCollector Tests
# =============================================================================


class TestFeedbackCollector:
    """Tests for FeedbackCollector."""

    def test_record_feedback(self):
        """Test recording basic feedback."""
        collector = FeedbackCollector()
        
        feedback = collector.record_feedback(
            model_name="test_model",
            features={"feature1": 1.0, "feature2": 2.0},
            prediction=1,
            actual_outcome=0,
            source=FeedbackSource.PREDICTION_OUTCOME,
        )
        
        assert feedback.model_name == "test_model"
        assert feedback.prediction == 1
        assert feedback.actual_outcome == 0
        assert feedback.source == FeedbackSource.PREDICTION_OUTCOME
    
    def test_record_user_correction(self):
        """Test recording user corrections with high confidence."""
        collector = FeedbackCollector()
        
        feedback = collector.record_user_correction(
            model_name="test_model",
            features={"f1": 1.0},
            original_prediction="A",
            corrected_value="B",
            user_id="user123",
        )
        
        assert feedback.confidence == 1.0
        assert feedback.source == FeedbackSource.USER_CORRECTION
        assert feedback.user_id == "user123"
    
    def test_get_feedback_for_training(self):
        """Test retrieving feedback for training."""
        collector = FeedbackCollector()
        
        # Record multiple feedback entries
        for i in range(10):
            collector.record_feedback(
                model_name="test_model",
                features={"f": float(i)},
                prediction=i % 2,
                actual_outcome=(i + 1) % 2,
                confidence=0.5 + (i / 20),
            )
        
        # Get all feedback
        feedback_list = collector.get_feedback_for_training("test_model")
        assert len(feedback_list) == 10
        
        # Get limited feedback
        feedback_list = collector.get_feedback_for_training("test_model", max_samples=5)
        assert len(feedback_list) == 5
        
        # Get filtered by confidence
        feedback_list = collector.get_feedback_for_training(
            "test_model", min_confidence=0.7
        )
        assert all(f.confidence >= 0.7 for f in feedback_list)
    
    def test_prepare_training_data(self):
        """Test preparing feedback as numpy arrays."""
        collector = FeedbackCollector()
        
        # Record feedback
        for i in range(5):
            collector.record_feedback(
                model_name="test_model",
                features={"x1": float(i), "x2": float(i * 2)},
                prediction=0,
                actual_outcome=i % 2,
            )
        
        X, y = collector.prepare_training_data(
            "test_model",
            feature_names=["x1", "x2"],
        )
        
        assert X.shape == (5, 2)
        assert y.shape == (5,)
        assert list(y) == [0, 1, 0, 1, 0]
    
    def test_buffer_size_limit(self):
        """Test that buffer respects size limit."""
        collector = FeedbackCollector(buffer_size=5)
        
        for i in range(10):
            collector.record_feedback(
                model_name="test_model",
                features={"f": float(i)},
                prediction=0,
                actual_outcome=1,
            )
        
        # Should only have last 5
        assert collector.get_feedback_count("test_model") == 5
    
    def test_feedback_callback(self):
        """Test feedback callbacks are called."""
        collector = FeedbackCollector()
        callback_calls = []
        
        def callback(feedback):
            callback_calls.append(feedback)
        
        collector.add_feedback_callback(callback)
        
        collector.record_feedback(
            model_name="test_model",
            features={},
            prediction=0,
            actual_outcome=1,
        )
        
        assert len(callback_calls) == 1


# =============================================================================
# IncrementalLearner Tests
# =============================================================================


class TestIncrementalLearner:
    """Tests for IncrementalLearner."""
    
    def test_can_learn_incrementally_sgd(self):
        """Test detection of partial_fit support."""
        from sklearn.linear_model import SGDClassifier
        
        learner = IncrementalLearner()
        model = SGDClassifier()
        
        assert learner.can_learn_incrementally(model) is True
    
    def test_can_learn_incrementally_random_forest(self):
        """Test detection of warm_start support."""
        from sklearn.ensemble import RandomForestClassifier
        
        learner = IncrementalLearner()
        model = RandomForestClassifier(warm_start=True)
        
        assert learner.can_learn_incrementally(model) is True
    
    def test_incremental_fit_sgd(self):
        """Test incremental fitting with SGD."""
        from sklearn.linear_model import SGDClassifier
        
        learner = IncrementalLearner()
        model = SGDClassifier(max_iter=1000, tol=1e-3)
        
        X = np.random.randn(50, 4)
        y = np.random.randint(0, 2, 50)
        
        # First fit
        model = learner.incremental_fit(model, X[:25], y[:25], classes=np.array([0, 1]))
        
        # Incremental update
        model = learner.incremental_fit(model, X[25:], y[25:], model_id="test")
        
        # Should be able to predict
        predictions = model.predict(X[:5])
        assert len(predictions) == 5
    
    def test_incremental_fit_naive_bayes(self):
        """Test incremental fitting with GaussianNB."""
        from sklearn.naive_bayes import GaussianNB
        
        learner = IncrementalLearner()
        model = GaussianNB()
        
        X = np.random.randn(50, 3)
        y = np.random.randint(0, 2, 50)
        
        model = learner.incremental_fit(model, X[:25], y[:25], classes=np.array([0, 1]))
        model = learner.incremental_fit(model, X[25:], y[25:], model_id="test")
        
        predictions = model.predict(X[:5])
        assert len(predictions) == 5
    
    def test_create_incremental_model_classification(self):
        """Test creating incremental model for classification."""
        learner = IncrementalLearner()
        model = learner.create_incremental_model(ModelType.CLASSIFICATION)
        
        assert model is not None
        assert hasattr(model, "partial_fit")
    
    def test_create_incremental_model_regression(self):
        """Test creating incremental model for regression."""
        learner = IncrementalLearner()
        model = learner.create_incremental_model(ModelType.REGRESSION)
        
        assert model is not None
        assert hasattr(model, "partial_fit")


# =============================================================================
# RetrainingManager Tests
# =============================================================================


class TestRetrainingManager:
    """Tests for RetrainingManager."""
    
    def test_register_model(self):
        """Test registering a model for continuous learning."""
        manager = RetrainingManager()
        
        state = manager.register_model(
            model_name="test_model",
            baseline_metrics={"accuracy": 0.95},
        )
        
        assert state.model_name == "test_model"
        assert state.baseline_metrics["accuracy"] == 0.95
    
    def test_check_retraining_data_threshold(self):
        """Test data threshold triggers retraining."""
        config = RetrainingConfig(
            min_samples_for_retrain=5,
            enable_scheduled_retraining=False,  # Disable scheduled to test data threshold
        )
        manager = RetrainingManager(config=config)
        
        # Register and mark as trained to bypass initial training trigger
        state = manager.register_model("test_model")
        state.last_retrained_at = datetime.now(timezone.utc)
        
        # Add feedback below threshold
        for i in range(3):
            manager.feedback_collector.record_feedback(
                model_name="test_model",
                features={},
                prediction=0,
                actual_outcome=1,
            )
        
        needs, trigger, reason = manager.check_retraining_needed("test_model")
        assert needs is False
        
        # Add more to exceed threshold
        for i in range(3):
            manager.feedback_collector.record_feedback(
                model_name="test_model",
                features={},
                prediction=0,
                actual_outcome=1,
            )
        
        needs, trigger, reason = manager.check_retraining_needed("test_model")
        assert needs is True
        assert trigger == RetrainingTrigger.DATA_THRESHOLD
    
    def test_check_retraining_performance_degradation(self):
        """Test performance degradation triggers retraining."""
        config = RetrainingConfig(performance_degradation_threshold=0.05)
        manager = RetrainingManager(config=config)
        manager.register_model(
            "test_model",
            baseline_metrics={"accuracy": 0.90},
        )
        
        # 10% degradation should trigger
        needs, trigger, reason = manager.check_retraining_needed(
            "test_model",
            current_metrics={"accuracy": 0.80},
        )
        
        assert needs is True
        assert trigger == RetrainingTrigger.PERFORMANCE_DEGRADATION
    
    @pytest.mark.asyncio
    async def test_trigger_retraining(self):
        """Test triggering model retraining."""
        from sklearn.linear_model import SGDClassifier
        
        config = RetrainingConfig(min_samples_for_retrain=5)
        manager = RetrainingManager(config=config)
        manager.register_model("test_model")
        
        # Add training data
        for i in range(10):
            manager.feedback_collector.record_feedback(
                model_name="test_model",
                features={"x1": float(i), "x2": float(i * 2)},
                prediction=0,
                actual_outcome=i % 2,
            )
        
        model = SGDClassifier(max_iter=1000, tol=1e-3)
        
        job = await manager.trigger_retraining(
            model_name="test_model",
            trigger=RetrainingTrigger.DATA_THRESHOLD,
            model=model,
            feature_names=["x1", "x2"],
        )
        
        assert job.status == "completed"
        assert job.sample_count == 10
    
    def test_get_retraining_history(self):
        """Test getting retraining history."""
        manager = RetrainingManager()
        
        # Initially empty
        history = manager.get_retraining_history("test_model")
        assert len(history) == 0


# =============================================================================
# ContinuousLearningService Tests
# =============================================================================


class TestContinuousLearningService:
    """Tests for ContinuousLearningService."""
    
    def test_register_model(self):
        """Test registering a model."""
        from sklearn.ensemble import RandomForestClassifier
        
        service = ContinuousLearningService()
        model = RandomForestClassifier(n_estimators=10)
        
        service.register_model(
            model_name="test_rf",
            model=model,
            feature_names=["f1", "f2", "f3"],
            baseline_metrics={"accuracy": 0.85},
        )
        
        assert "test_rf" in service._models
        assert "test_rf" in service._feature_names
    
    def test_log_prediction_with_outcome(self):
        """Test logging predictions with outcomes."""
        service = ContinuousLearningService()
        
        service.log_prediction(
            model_name="test_model",
            features={"x": 1.0},
            prediction=1,
            actual_outcome=0,
        )
        
        assert service._predictions_logged == 1
        assert service.feedback_collector.get_feedback_count("test_model") == 1
    
    def test_record_correction(self):
        """Test recording user corrections."""
        service = ContinuousLearningService()
        
        service.record_correction(
            model_name="test_model",
            features={"x": 1.0},
            original_prediction="A",
            corrected_value="B",
            user_id="user1",
        )
        
        assert service._corrections_received == 1
    
    def test_get_model_health(self):
        """Test getting model health status."""
        from sklearn.linear_model import SGDClassifier
        
        service = ContinuousLearningService()
        model = SGDClassifier()
        
        service.register_model(
            model_name="test_model",
            model=model,
            feature_names=["f1"],
            baseline_metrics={"accuracy": 0.9},
        )
        
        health = service.get_model_health("test_model")
        
        assert health["status"] == "healthy"
        assert health["model_name"] == "test_model"
        assert health["baseline_metrics"]["accuracy"] == 0.9
    
    def test_get_model_health_unregistered(self):
        """Test health check for unregistered model."""
        service = ContinuousLearningService()
        
        health = service.get_model_health("unknown_model")
        
        assert health["status"] == "not_registered"
    
    @pytest.mark.asyncio
    async def test_check_and_retrain_if_needed(self):
        """Test auto-retraining trigger check."""
        from sklearn.linear_model import SGDClassifier
        
        config = RetrainingConfig(
            min_samples_for_retrain=5,
            enable_scheduled_retraining=False,  # Disable scheduled to test data threshold
        )
        service = ContinuousLearningService(config=config)
        model = SGDClassifier(max_iter=1000)
        
        service.register_model(
            model_name="test_model",
            model=model,
            feature_names=["x"],
        )
        
        # Add feedback below threshold (alternating outcomes for valid training data)
        for i in range(3):
            service.log_prediction(
                model_name="test_model",
                features={"x": float(i)},
                prediction=0,
                actual_outcome=i % 2,  # Alternate 0, 1, 0
            )
        
        # Should not trigger retraining
        job = await service.check_and_retrain_if_needed("test_model")
        assert job is None
        
        # Add more feedback with both classes
        for i in range(5):
            service.log_prediction(
                model_name="test_model",
                features={"x": float(i + 10)},
                prediction=0,
                actual_outcome=i % 2,  # Alternate outcomes
            )
        
        # Should trigger retraining now
        job = await service.check_and_retrain_if_needed("test_model")
        assert job is not None
        assert job.trigger == RetrainingTrigger.DATA_THRESHOLD
    
    @pytest.mark.asyncio
    async def test_force_retrain(self):
        """Test forcing immediate retraining."""
        from sklearn.linear_model import SGDClassifier
        
        service = ContinuousLearningService()
        model = SGDClassifier(max_iter=1000)
        
        service.register_model(
            model_name="test_model",
            model=model,
            feature_names=["x", "y"],
        )
        
        # Add some feedback
        for i in range(10):
            service.log_prediction(
                model_name="test_model",
                features={"x": float(i), "y": float(i * 2)},
                prediction=0,
                actual_outcome=i % 2,
            )
        
        job = await service.force_retrain("test_model", LearningMode.INCREMENTAL)
        
        assert job.status == "completed"
        assert job.trigger == RetrainingTrigger.MANUAL
    
    def test_get_statistics(self):
        """Test getting overall statistics."""
        service = ContinuousLearningService()
        
        # Log some activity
        service.log_prediction("m1", {}, 0, 1)
        service.record_correction("m1", {}, 0, 1, "user")
        
        stats = service.get_statistics()
        
        assert stats["predictions_logged"] == 1
        assert stats["corrections_received"] == 1


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for singleton behavior."""
    
    def test_get_continuous_learning_service(self):
        """Test getting the singleton service."""
        reset_continuous_learning_service()
        
        service1 = get_continuous_learning_service()
        service2 = get_continuous_learning_service()
        
        assert service1 is service2
    
    def test_reset_continuous_learning_service(self):
        """Test resetting the singleton."""
        service1 = get_continuous_learning_service()
        reset_continuous_learning_service()
        service2 = get_continuous_learning_service()
        
        assert service1 is not service2


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the continuous learning system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_feedback_loop(self):
        """Test complete feedback loop: predict → correct → retrain."""
        from sklearn.linear_model import SGDClassifier
        
        # Setup
        config = RetrainingConfig(
            min_samples_for_retrain=10,
            preferred_learning_mode=LearningMode.INCREMENTAL,
        )
        service = ContinuousLearningService(config=config)
        model = SGDClassifier(max_iter=1000, random_state=42)
        
        service.register_model(
            model_name="sales_predictor",
            model=model,
            feature_names=["price", "quantity", "margin"],
            baseline_metrics={"accuracy": 0.80},
        )
        
        # Simulate predictions with outcomes
        np.random.seed(42)
        for i in range(15):
            features = {
                "price": np.random.uniform(10, 100),
                "quantity": np.random.randint(1, 50),
                "margin": np.random.uniform(0.1, 0.5),
            }
            service.log_prediction(
                model_name="sales_predictor",
                features=features,
                prediction=0,
                actual_outcome=np.random.randint(0, 2),
            )
        
        # Check statistics
        stats = service.get_statistics()
        assert stats["predictions_logged"] == 15
        
        # Trigger retraining check
        job = await service.check_and_retrain_if_needed("sales_predictor")
        
        assert job is not None
        assert job.status == "completed"
        assert job.sample_count >= 10
        
        # Check model health after retraining
        health = service.get_model_health("sales_predictor")
        assert health["status"] == "healthy"
        assert health["last_retrained_at"] is not None

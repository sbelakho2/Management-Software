"""
Continuous Learning System for Self-Refining AI.

This module connects feedback collection, drift detection, and model retraining
to enable AI models that continuously improve with new data.

Features:
- Online/Incremental Learning: Models learn from new data without full retraining
- Feedback-to-Training Pipeline: User corrections feed back into model improvement
- Auto-Retraining Triggers: Drift detection triggers automatic retraining
- Scheduled Retraining: Periodic retraining with accumulated data
- Warm-Starting: Reuse previous model weights for faster convergence

References:
- Online Learning: https://scikit-learn.org/stable/modules/scaling_strategies.html
- River: https://riverml.xyz/latest/ (streaming ML)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import pickle
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Generic
import threading
import uuid
import os

import numpy as np

from sensei.services.ai.enhanced_ml_pipeline import (
    DriftDetector,
    DriftDetectionResult,
    DriftSeverity,
    DriftType,
    ModelType,
    ModelStage,
    ModelMetrics,
    FeatureStore,
    FeatureGroup,
    ModelRegistryService,
    ExperimentTracker,
    ModelMonitor,
    PredictionLog,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Enums
# =============================================================================


class LearningMode(str, Enum):
    """Mode of model learning."""
    BATCH = "batch"  # Full retraining with all data
    INCREMENTAL = "incremental"  # Partial updates with new data
    ONLINE = "online"  # Single-sample updates (streaming)


class RetrainingTrigger(str, Enum):
    """What triggered a retraining."""
    DRIFT_DETECTED = "drift_detected"
    DATA_THRESHOLD = "data_threshold"
    SCHEDULED = "scheduled"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    FEEDBACK_ACCUMULATED = "feedback_accumulated"
    MANUAL = "manual"


class FeedbackSource(str, Enum):
    """Source of feedback for learning."""
    USER_CORRECTION = "user_correction"
    PREDICTION_OUTCOME = "prediction_outcome"
    EXPERT_ANNOTATION = "expert_annotation"
    A_B_TEST_RESULT = "ab_test_result"
    AUTOMATED_VALIDATION = "automated_validation"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class LearningFeedback:
    """Feedback data for model learning."""
    feedback_id: str
    model_name: str
    timestamp: datetime
    source: FeedbackSource
    
    # Input/output
    features: Dict[str, Any]
    prediction: Any
    actual_outcome: Any
    
    # Metadata
    confidence: float = 1.0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrainingJob:
    """A model retraining job."""
    job_id: str
    model_name: str
    trigger: RetrainingTrigger
    learning_mode: LearningMode
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Config
    sample_count: int = 0
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    status: str = "pending"  # pending, running, completed, failed
    previous_metrics: Dict[str, float] = field(default_factory=dict)
    new_metrics: Dict[str, float] = field(default_factory=dict)
    improvement: float = 0.0
    error_message: Optional[str] = None
    
    # Model versions
    previous_version_id: Optional[str] = None
    new_version_id: Optional[str] = None


@dataclass
class RetrainingConfig:
    """Configuration for auto-retraining."""
    # Thresholds
    drift_threshold: DriftSeverity = DriftSeverity.MEDIUM
    min_samples_for_retrain: int = 100
    performance_degradation_threshold: float = 0.05  # 5% drop
    
    # Scheduling
    enable_scheduled_retraining: bool = True
    retraining_interval_hours: int = 168  # Weekly
    
    # Learning
    preferred_learning_mode: LearningMode = LearningMode.INCREMENTAL
    warm_start_enabled: bool = True
    
    # Safety
    require_improvement_for_deploy: bool = True
    minimum_improvement: float = 0.01  # 1% improvement required
    max_concurrent_retraining: int = 2
    
    # Data
    max_training_samples: int = 100000
    feedback_buffer_size: int = 10000


@dataclass
class ModelLearningState:
    """State of a model's continuous learning."""
    model_name: str
    last_retrained_at: Optional[datetime] = None
    last_drift_check_at: Optional[datetime] = None
    last_drift_result: Optional[DriftDetectionResult] = None
    
    # Accumulated data
    feedback_count: int = 0
    pending_samples: int = 0
    
    # Performance tracking
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    current_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Reference data for drift detection
    reference_features: Optional[np.ndarray] = None
    reference_predictions: Optional[np.ndarray] = None


# =============================================================================
# Feedback Collector
# =============================================================================


class FeedbackCollector:
    """
    Collects and stores feedback for model improvement.
    
    Aggregates feedback from multiple sources and prepares data
    for model retraining.
    """
    
    def __init__(
        self,
        buffer_size: int = 10000,
        feature_store: FeatureStore | None = None,
        feature_group_prefix: str = "model_feedback",
    ):
        self.buffer_size = buffer_size
        self._feature_store = feature_store
        self._feature_group_prefix = feature_group_prefix
        
        # Per-model feedback buffers
        self._feedback: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=buffer_size)
        )
        self._feedback_counts: Dict[str, int] = defaultdict(int)
        
        # Callbacks
        self._on_feedback_callbacks: List[Callable[[LearningFeedback], None]] = []

    def _ensure_feature_group(self, model_name: str) -> str:
        if not self._feature_store:
            return ""
        group_name = f"{self._feature_group_prefix}:{model_name}"
        if group_name not in self._feature_store.groups:
            self._feature_store.register_feature_group(
                FeatureGroup(
                    name=group_name,
                    features=[],
                    entity_key="feedback_id",
                    description="Continuous learning feedback samples",
                )
            )
        return group_name
    
    def record_feedback(
        self,
        model_name: str,
        features: Dict[str, Any],
        prediction: Any,
        actual_outcome: Any,
        source: FeedbackSource = FeedbackSource.PREDICTION_OUTCOME,
        confidence: float = 1.0,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LearningFeedback:
        """Record feedback for a model."""
        feedback = LearningFeedback(
            feedback_id=str(uuid.uuid4())[:12],
            model_name=model_name,
            timestamp=_utcnow(),
            source=source,
            features=features,
            prediction=prediction,
            actual_outcome=actual_outcome,
            confidence=confidence,
            user_id=user_id,
            metadata=metadata or {},
        )
        
        self._feedback[model_name].append(feedback)
        self._feedback_counts[model_name] += 1

        if self._feature_store:
            group_name = self._ensure_feature_group(model_name)
            payload = {
                **features,
                "model_name": model_name,
                "prediction": prediction,
                "actual_outcome": actual_outcome,
                "confidence": confidence,
                "source": source.value,
                "user_id": user_id,
            }
            self._feature_store.ingest_features(
                group_name,
                entity_id=feedback.feedback_id,
                features=payload,
                timestamp=feedback.timestamp,
            )
        
        # Notify callbacks
        for callback in self._on_feedback_callbacks:
            try:
                callback(feedback)
            except Exception as e:
                logger.warning(f"Feedback callback error: {e}")
        
        logger.debug(
            f"Recorded feedback for {model_name}: "
            f"prediction={prediction}, actual={actual_outcome}"
        )
        
        return feedback
    
    def record_user_correction(
        self,
        model_name: str,
        features: Dict[str, Any],
        original_prediction: Any,
        corrected_value: Any,
        user_id: str,
    ) -> LearningFeedback:
        """Record a user correction as high-confidence feedback."""
        return self.record_feedback(
            model_name=model_name,
            features=features,
            prediction=original_prediction,
            actual_outcome=corrected_value,
            source=FeedbackSource.USER_CORRECTION,
            confidence=1.0,  # User corrections are high confidence
            user_id=user_id,
        )
    
    def get_feedback_for_training(
        self,
        model_name: str,
        max_samples: Optional[int] = None,
        min_confidence: float = 0.0,
    ) -> List[LearningFeedback]:
        """Get accumulated feedback for training."""
        feedback_list = list(self._feedback.get(model_name, []))

        if not feedback_list and self._feature_store:
            group_name = f"{self._feature_group_prefix}:{model_name}"
            persisted: list[LearningFeedback] = []
            for key, vectors in self._feature_store.feature_vectors.items():
                if not key.startswith(f"{group_name}:"):
                    continue
                for vector in vectors:
                    source_value = vector.features.get("source", FeedbackSource.PREDICTION_OUTCOME.value)
                    if isinstance(source_value, FeedbackSource):
                        source_value = source_value.value
                    persisted.append(
                        LearningFeedback(
                            feedback_id=vector.entity_id,
                            model_name=model_name,
                            timestamp=vector.timestamp,
                            source=FeedbackSource(str(source_value)),
                            features={k: v for k, v in vector.features.items() if k not in {
                                "model_name",
                                "prediction",
                                "actual_outcome",
                                "confidence",
                                "source",
                                "user_id",
                            }},
                            prediction=vector.features.get("prediction"),
                            actual_outcome=vector.features.get("actual_outcome"),
                            confidence=float(vector.features.get("confidence", 1.0)),
                            user_id=vector.features.get("user_id"),
                        )
                    )
            feedback_list = persisted
        
        # Filter by confidence
        if min_confidence > 0:
            feedback_list = [f for f in feedback_list if f.confidence >= min_confidence]
        
        # Limit samples
        if max_samples and len(feedback_list) > max_samples:
            # Take most recent
            feedback_list = feedback_list[-max_samples:]
        
        return feedback_list
    
    def prepare_training_data(
        self,
        model_name: str,
        feature_names: List[str],
        max_samples: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare feedback as training data (X, y arrays).
        
        Returns:
            Tuple of (features array, labels array)
        """
        feedback_list = self.get_feedback_for_training(model_name, max_samples)
        
        if not feedback_list:
            return np.array([]), np.array([])
        
        X = []
        y = []
        
        for feedback in feedback_list:
            # Extract features in order
            features_row = []
            for fname in feature_names:
                value = feedback.features.get(fname, 0.0)
                try:
                    features_row.append(float(value))
                except (TypeError, ValueError):
                    features_row.append(0.0)
            
            X.append(features_row)
            y.append(feedback.actual_outcome)
        
        return np.array(X), np.array(y)
    
    def get_feedback_count(self, model_name: str) -> int:
        """Get total feedback count for a model."""
        return len(self._feedback.get(model_name, []))
    
    def clear_feedback(self, model_name: str) -> int:
        """Clear feedback buffer for a model."""
        count = len(self._feedback.get(model_name, []))
        self._feedback[model_name].clear()
        return count
    
    def add_feedback_callback(
        self,
        callback: Callable[[LearningFeedback], None],
    ) -> None:
        """Add a callback to be called when feedback is recorded."""
        self._on_feedback_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get feedback collection statistics."""
        return {
            "models": list(self._feedback.keys()),
            "buffer_counts": {
                k: len(v) for k, v in self._feedback.items()
            },
            "total_counts": dict(self._feedback_counts),
        }


# =============================================================================
# Incremental Learner
# =============================================================================


class IncrementalLearner:
    """
    Supports incremental/online learning for sklearn models.
    
    Uses partial_fit for models that support it, or warm_start
    for ensemble models.
    """
    
    # Models that support partial_fit
    PARTIAL_FIT_MODELS = {
        "SGDClassifier",
        "SGDRegressor",
        "PassiveAggressiveClassifier",
        "PassiveAggressiveRegressor",
        "Perceptron",
        "MiniBatchKMeans",
        "BernoulliNB",
        "MultinomialNB",
        "GaussianNB",
    }
    
    # Models that support warm_start
    WARM_START_MODELS = {
        "RandomForestClassifier",
        "RandomForestRegressor",
        "GradientBoostingClassifier",
        "GradientBoostingRegressor",
        "BaggingClassifier",
        "BaggingRegressor",
    }
    
    def __init__(self):
        self._classes_cache: Dict[str, np.ndarray] = {}
    
    def can_learn_incrementally(self, model: Any) -> bool:
        """Check if a model supports incremental learning."""
        model_name = type(model).__name__
        
        if hasattr(model, "partial_fit"):
            return True
        
        if model_name in self.WARM_START_MODELS:
            return hasattr(model, "warm_start")
        
        return False
    
    def incremental_fit(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        classes: Optional[np.ndarray] = None,
        model_id: Optional[str] = None,
    ) -> Any:
        """
        Perform incremental learning on a model.
        
        Uses partial_fit if available, otherwise warm_start.
        """
        if len(X) == 0:
            return model
        
        model_name = type(model).__name__
        
        # Try partial_fit first
        if hasattr(model, "partial_fit"):
            # For classifiers, need to provide classes on first call
            if classes is not None:
                model.partial_fit(X, y, classes=classes)
            elif model_id and model_id in self._classes_cache:
                model.partial_fit(X, y, classes=self._classes_cache[model_id])
            else:
                # Infer classes from data
                unique_classes = np.unique(y)
                if model_id:
                    self._classes_cache[model_id] = unique_classes
                try:
                    model.partial_fit(X, y, classes=unique_classes)
                except TypeError:
                    # Some models don't need classes parameter
                    model.partial_fit(X, y)
            
            logger.debug(f"Performed partial_fit on {model_name} with {len(X)} samples")
            return model
        
        # Try warm_start for ensemble models
        if model_name in self.WARM_START_MODELS:
            if hasattr(model, "warm_start"):
                model.warm_start = True
                # Increase n_estimators for ensemble models
                if hasattr(model, "n_estimators"):
                    current_estimators = model.n_estimators
                    # Add more trees proportional to new data
                    additional = max(1, len(X) // 100)
                    model.n_estimators = current_estimators + additional
                
                model.fit(X, y)
                logger.debug(
                    f"Performed warm_start fit on {model_name} with {len(X)} samples"
                )
                return model
        
        # Fallback: full refit
        logger.warning(
            f"{model_name} doesn't support incremental learning, performing full fit"
        )
        model.fit(X, y)
        return model
    
    def create_incremental_model(
        self,
        model_type: ModelType,
    ) -> Any:
        """Create a model that supports incremental learning."""
        try:
            from sklearn.linear_model import SGDClassifier, SGDRegressor
            from sklearn.naive_bayes import GaussianNB
        except ImportError:
            logger.warning("sklearn not available")
            return None
        
        if model_type in (ModelType.CLASSIFICATION, ModelType.ANOMALY_DETECTION):
            # SGDClassifier with log loss is like logistic regression
            return SGDClassifier(
                loss="log_loss",
                penalty="l2",
                alpha=0.0001,
                max_iter=1000,
                tol=1e-3,
                random_state=42,
                warm_start=True,
            )
        elif model_type == ModelType.REGRESSION:
            return SGDRegressor(
                loss="squared_error",
                penalty="l2",
                alpha=0.0001,
                max_iter=1000,
                tol=1e-3,
                random_state=42,
                warm_start=True,
            )
        else:
            # Default to GaussianNB which supports partial_fit
            return GaussianNB()


# =============================================================================
# Retraining Manager
# =============================================================================


class RetrainingManager:
    """
    Manages model retraining based on various triggers.
    
    Coordinates drift detection, feedback accumulation, and
    scheduled retraining.
    """
    
    def __init__(
        self,
        config: Optional[RetrainingConfig] = None,
        feedback_collector: Optional[FeedbackCollector] = None,
        drift_detector: Optional[DriftDetector] = None,
    ):
        self.config = config or RetrainingConfig()
        self.feedback_collector = feedback_collector or FeedbackCollector(
            buffer_size=self.config.feedback_buffer_size
        )
        self.drift_detector = drift_detector or DriftDetector()
        self.incremental_learner = IncrementalLearner()
        
        # Model states
        self._model_states: Dict[str, ModelLearningState] = {}
        
        # Retraining jobs
        self._retraining_jobs: List[RetrainingJob] = []
        self._active_jobs: Dict[str, RetrainingJob] = {}
        
        # Callbacks
        self._on_retrain_callbacks: List[Callable[[RetrainingJob], None]] = []
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def register_model(
        self,
        model_name: str,
        baseline_metrics: Optional[Dict[str, float]] = None,
        reference_features: Optional[np.ndarray] = None,
    ) -> ModelLearningState:
        """Register a model for continuous learning."""
        state = ModelLearningState(
            model_name=model_name,
            baseline_metrics=baseline_metrics or {},
            reference_features=reference_features,
        )
        self._model_states[model_name] = state
        
        # Set reference data in drift detector
        if reference_features is not None and len(reference_features) > 0:
            if reference_features.ndim == 2:
                for i in range(reference_features.shape[1]):
                    self.drift_detector.set_reference_data(
                        f"{model_name}_feature_{i}",
                        reference_features[:, i],
                    )
        
        logger.info(f"Registered model {model_name} for continuous learning")
        return state
    
    def check_retraining_needed(
        self,
        model_name: str,
        current_features: Optional[np.ndarray] = None,
        current_metrics: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, Optional[RetrainingTrigger], str]:
        """
        Check if a model needs retraining.
        
        Returns:
            Tuple of (needs_retraining, trigger, reason)
        """
        state = self._model_states.get(model_name)
        if state is None:
            return False, None, "Model not registered"
        
        # Check feedback threshold
        feedback_count = self.feedback_collector.get_feedback_count(model_name)
        if feedback_count >= self.config.min_samples_for_retrain:
            return True, RetrainingTrigger.DATA_THRESHOLD, (
                f"Feedback threshold reached: {feedback_count} samples"
            )
        
        # Check drift
        if current_features is not None and len(current_features) > 0:
            drift_result = self._check_drift(model_name, current_features)
            if drift_result and drift_result.drift_detected:
                if self._severity_meets_threshold(drift_result.severity):
                    state.last_drift_result = drift_result
                    return True, RetrainingTrigger.DRIFT_DETECTED, (
                        f"Drift detected: {drift_result.severity.value}"
                    )
        
        # Check performance degradation
        if current_metrics and state.baseline_metrics:
            degradation = self._calculate_degradation(
                state.baseline_metrics,
                current_metrics,
            )
            if degradation > self.config.performance_degradation_threshold:
                return True, RetrainingTrigger.PERFORMANCE_DEGRADATION, (
                    f"Performance degraded by {degradation*100:.1f}%"
                )
        
        # Check scheduled retraining
        if self.config.enable_scheduled_retraining:
            if state.last_retrained_at is None:
                return True, RetrainingTrigger.SCHEDULED, "Initial training"
            
            hours_since_retrain = (
                _utcnow() - state.last_retrained_at
            ).total_seconds() / 3600
            
            if hours_since_retrain >= self.config.retraining_interval_hours:
                return True, RetrainingTrigger.SCHEDULED, (
                    f"Scheduled retraining ({hours_since_retrain:.0f}h since last)"
                )
        
        return False, None, "No retraining needed"
    
    def _check_drift(
        self,
        model_name: str,
        current_features: np.ndarray,
    ) -> Optional[DriftDetectionResult]:
        """Check for drift in current features."""
        if current_features.ndim != 2:
            return None
        
        feature_data = {}
        for i in range(current_features.shape[1]):
            feature_name = f"{model_name}_feature_{i}"
            feature_data[feature_name] = current_features[:, i]
        
        try:
            return self.drift_detector.detect_data_drift(feature_data)
        except Exception as e:
            logger.warning(f"Drift detection failed: {e}")
            return None
    
    def _severity_meets_threshold(self, severity: DriftSeverity) -> bool:
        """Check if drift severity meets the threshold."""
        severity_order = [
            DriftSeverity.NONE,
            DriftSeverity.LOW,
            DriftSeverity.MEDIUM,
            DriftSeverity.HIGH,
            DriftSeverity.CRITICAL,
        ]
        
        threshold_idx = severity_order.index(self.config.drift_threshold)
        current_idx = severity_order.index(severity)
        
        return current_idx >= threshold_idx
    
    def _calculate_degradation(
        self,
        baseline: Dict[str, float],
        current: Dict[str, float],
    ) -> float:
        """Calculate performance degradation."""
        # Use accuracy as primary metric
        if "accuracy" in baseline and "accuracy" in current:
            baseline_acc = baseline["accuracy"]
            current_acc = current["accuracy"]
            if baseline_acc > 0:
                return (baseline_acc - current_acc) / baseline_acc
        
        return 0.0
    
    async def trigger_retraining(
        self,
        model_name: str,
        trigger: RetrainingTrigger,
        model: Any,
        feature_names: List[str],
        force_mode: Optional[LearningMode] = None,
    ) -> RetrainingJob:
        """
        Trigger model retraining.
        
        Args:
            model_name: Name of the model to retrain
            trigger: What triggered the retraining
            model: The current model object
            feature_names: Names of features for training data
            force_mode: Override the configured learning mode
            
        Returns:
            The retraining job
        """
        with self._lock:
            # Check concurrent limit
            if len(self._active_jobs) >= self.config.max_concurrent_retraining:
                raise RuntimeError(
                    f"Max concurrent retraining jobs reached: "
                    f"{self.config.max_concurrent_retraining}"
                )
            
            job = RetrainingJob(
                job_id=str(uuid.uuid4())[:12],
                model_name=model_name,
                trigger=trigger,
                learning_mode=force_mode or self.config.preferred_learning_mode,
                created_at=_utcnow(),
            )
            
            self._retraining_jobs.append(job)
            self._active_jobs[job.job_id] = job
        
        try:
            await self._execute_retraining(job, model, feature_names)
        finally:
            with self._lock:
                self._active_jobs.pop(job.job_id, None)
        
        # Notify callbacks
        for callback in self._on_retrain_callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.warning(f"Retrain callback error: {e}")
        
        return job
    
    async def _execute_retraining(
        self,
        job: RetrainingJob,
        model: Any,
        feature_names: List[str],
    ) -> None:
        """Execute the retraining job."""
        job.started_at = _utcnow()
        job.status = "running"
        
        try:
            # Get training data from feedback
            X, y = self.feedback_collector.prepare_training_data(
                job.model_name,
                feature_names,
                max_samples=self.config.max_training_samples,
            )
            
            if len(X) == 0:
                job.status = "completed"
                job.completed_at = _utcnow()
                job.error_message = "No training data available"
                return
            
            job.sample_count = len(X)
            
            # Evaluate current performance
            if hasattr(model, "predict") and len(X) > 0:
                try:
                    from sklearn.metrics import accuracy_score
                    predictions = model.predict(X)
                    job.previous_metrics["accuracy"] = accuracy_score(y, predictions)
                except Exception as e:
                    logger.debug(f"Could not evaluate previous model: {e}")
            
            # Perform retraining based on mode
            if job.learning_mode == LearningMode.INCREMENTAL:
                if self.incremental_learner.can_learn_incrementally(model):
                    model = self.incremental_learner.incremental_fit(
                        model, X, y,
                        model_id=job.model_name,
                    )
                else:
                    # Fallback to full retrain with warm_start if available
                    if hasattr(model, "warm_start"):
                        model.warm_start = True
                    model.fit(X, y)
            
            elif job.learning_mode == LearningMode.ONLINE:
                # Online learning: process samples one at a time
                for i in range(len(X)):
                    self.incremental_learner.incremental_fit(
                        model,
                        X[i:i+1],
                        y[i:i+1],
                        model_id=job.model_name,
                    )
            
            else:  # BATCH
                model.fit(X, y)
            
            # Evaluate new performance
            try:
                from sklearn.metrics import accuracy_score
                predictions = model.predict(X)
                job.new_metrics["accuracy"] = accuracy_score(y, predictions)
                
                if "accuracy" in job.previous_metrics:
                    job.improvement = (
                        job.new_metrics["accuracy"] - job.previous_metrics["accuracy"]
                    )
            except Exception as e:
                logger.debug(f"Could not evaluate new model: {e}")
            
            job.status = "completed"
            job.completed_at = _utcnow()
            
            # Update model state
            state = self._model_states.get(job.model_name)
            if state:
                state.last_retrained_at = job.completed_at
                state.current_metrics = job.new_metrics.copy()
                state.feedback_count += job.sample_count
            
            logger.info(
                f"Retraining completed for {job.model_name}: "
                f"{job.sample_count} samples, "
                f"improvement={job.improvement:.4f}"
            )
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = _utcnow()
            logger.error(f"Retraining failed for {job.model_name}: {e}")
            raise
    
    def get_retraining_history(
        self,
        model_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[RetrainingJob]:
        """Get retraining history."""
        jobs = self._retraining_jobs
        
        if model_name:
            jobs = [j for j in jobs if j.model_name == model_name]
        
        return sorted(
            jobs[-limit:],
            key=lambda j: j.created_at,
            reverse=True,
        )
    
    def get_model_state(self, model_name: str) -> Optional[ModelLearningState]:
        """Get the learning state of a model."""
        return self._model_states.get(model_name)
    
    def add_retrain_callback(
        self,
        callback: Callable[[RetrainingJob], None],
    ) -> None:
        """Add a callback to be called after retraining."""
        self._on_retrain_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retraining manager statistics."""
        return {
            "registered_models": list(self._model_states.keys()),
            "total_jobs": len(self._retraining_jobs),
            "active_jobs": len(self._active_jobs),
            "completed_jobs": len([
                j for j in self._retraining_jobs if j.status == "completed"
            ]),
            "failed_jobs": len([
                j for j in self._retraining_jobs if j.status == "failed"
            ]),
            "feedback_stats": self.feedback_collector.get_statistics(),
        }


# =============================================================================
# Continuous Learning Service
# =============================================================================


class ContinuousLearningService:
    """
    Main service for continuous learning and self-refining AI.
    
    Integrates feedback collection, drift detection, and auto-retraining
    into a unified service.
    """
    
    def __init__(
        self,
        config: Optional[RetrainingConfig] = None,
    ):
        self.config = config or RetrainingConfig()
        
        # Components
        self.feature_store = FeatureStore()
        self.feedback_collector = FeedbackCollector(
            buffer_size=self.config.feedback_buffer_size,
            feature_store=self.feature_store,
        )
        self.drift_detector = DriftDetector()
        self.retraining_manager = RetrainingManager(
            config=self.config,
            feedback_collector=self.feedback_collector,
            drift_detector=self.drift_detector,
        )
        self.incremental_learner = IncrementalLearner()
        
        # Model cache
        self._models: Dict[str, Any] = {}
        self._feature_names: Dict[str, List[str]] = {}
        
        # Monitoring
        self._predictions_logged: int = 0
        self._corrections_received: int = 0
        self._auto_retrains_triggered: int = 0
    
    def register_model(
        self,
        model_name: str,
        model: Any,
        feature_names: List[str],
        baseline_metrics: Optional[Dict[str, float]] = None,
        reference_data: Optional[np.ndarray] = None,
    ) -> None:
        """
        Register a model for continuous learning.
        
        Args:
            model_name: Unique name for the model
            model: The sklearn-compatible model object
            feature_names: Names of input features
            baseline_metrics: Initial performance metrics
            reference_data: Reference feature data for drift detection
        """
        self._models[model_name] = model
        self._feature_names[model_name] = feature_names
        
        self.retraining_manager.register_model(
            model_name=model_name,
            baseline_metrics=baseline_metrics,
            reference_features=reference_data,
        )
        
        logger.info(
            f"Registered model {model_name} with {len(feature_names)} features"
        )
    
    def log_prediction(
        self,
        model_name: str,
        features: Dict[str, Any],
        prediction: Any,
        actual_outcome: Optional[Any] = None,
    ) -> None:
        """
        Log a prediction, optionally with the actual outcome.
        
        If actual_outcome is provided, this becomes training feedback.
        """
        self._predictions_logged += 1
        
        if actual_outcome is not None:
            self.feedback_collector.record_feedback(
                model_name=model_name,
                features=features,
                prediction=prediction,
                actual_outcome=actual_outcome,
                source=FeedbackSource.PREDICTION_OUTCOME,
            )
    
    def record_correction(
        self,
        model_name: str,
        features: Dict[str, Any],
        original_prediction: Any,
        corrected_value: Any,
        user_id: str,
    ) -> None:
        """Record a user correction for a prediction."""
        self._corrections_received += 1
        
        self.feedback_collector.record_user_correction(
            model_name=model_name,
            features=features,
            original_prediction=original_prediction,
            corrected_value=corrected_value,
            user_id=user_id,
        )
        
        logger.info(
            f"Recorded correction for {model_name}: "
            f"{original_prediction} -> {corrected_value}"
        )
    
    async def check_and_retrain_if_needed(
        self,
        model_name: str,
        current_features: Optional[np.ndarray] = None,
        current_metrics: Optional[Dict[str, float]] = None,
    ) -> Optional[RetrainingJob]:
        """
        Check if retraining is needed and trigger it if so.
        
        Returns:
            RetrainingJob if retraining was triggered, None otherwise
        """
        needs_retrain, trigger, reason = self.retraining_manager.check_retraining_needed(
            model_name,
            current_features=current_features,
            current_metrics=current_metrics,
        )
        
        if not needs_retrain or trigger is None:
            return None
        
        logger.info(f"Retraining triggered for {model_name}: {reason}")
        
        model = self._models.get(model_name)
        feature_names = self._feature_names.get(model_name, [])
        
        if model is None:
            logger.error(f"Model {model_name} not found in cache")
            return None
        
        self._auto_retrains_triggered += 1
        
        job = await self.retraining_manager.trigger_retraining(
            model_name=model_name,
            trigger=trigger,
            model=model,
            feature_names=feature_names,
        )
        
        return job
    
    async def force_retrain(
        self,
        model_name: str,
        learning_mode: Optional[LearningMode] = None,
    ) -> RetrainingJob:
        """Force immediate retraining of a model."""
        model = self._models.get(model_name)
        feature_names = self._feature_names.get(model_name, [])
        
        if model is None:
            raise ValueError(f"Model {model_name} not registered")
        
        return await self.retraining_manager.trigger_retraining(
            model_name=model_name,
            trigger=RetrainingTrigger.MANUAL,
            model=model,
            feature_names=feature_names,
            force_mode=learning_mode,
        )
    
    def get_model_health(self, model_name: str) -> Dict[str, Any]:
        """Get health status of a model's continuous learning."""
        state = self.retraining_manager.get_model_state(model_name)
        if state is None:
            return {"status": "not_registered"}
        
        feedback_count = self.feedback_collector.get_feedback_count(model_name)
        
        return {
            "status": "healthy",
            "model_name": model_name,
            "last_retrained_at": (
                state.last_retrained_at.isoformat()
                if state.last_retrained_at else None
            ),
            "feedback_pending": feedback_count,
            "total_feedback": state.feedback_count,
            "baseline_metrics": state.baseline_metrics,
            "current_metrics": state.current_metrics,
            "drift_status": (
                state.last_drift_result.severity.value
                if state.last_drift_result else "none"
            ),
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall continuous learning statistics."""
        return {
            "predictions_logged": self._predictions_logged,
            "corrections_received": self._corrections_received,
            "auto_retrains_triggered": self._auto_retrains_triggered,
            "registered_models": list(self._models.keys()),
            "retraining_stats": self.retraining_manager.get_statistics(),
        }


# =============================================================================
# Celery Tasks for Background Retraining
# =============================================================================


def create_retraining_celery_tasks():
    """
    Create Celery tasks for scheduled and triggered retraining.
    
    Returns task functions that can be registered with Celery.
    """
    
    async def check_drift_and_retrain(model_name: str):
        """Celery task to check drift and trigger retraining if needed."""
        from sensei.services.ai.continuous_learning import (
            get_continuous_learning_service,
        )
        
        service = get_continuous_learning_service()
        job = await service.check_and_retrain_if_needed(model_name)
        
        if job:
            return {
                "model": model_name,
                "job_id": job.job_id,
                "trigger": job.trigger.value,
                "improvement": job.improvement,
            }
        return {"model": model_name, "status": "no_retraining_needed"}
    
    async def scheduled_retrain_all():
        """Celery task for scheduled retraining of all models."""
        from sensei.services.ai.continuous_learning import (
            get_continuous_learning_service,
        )
        
        service = get_continuous_learning_service()
        results = []
        
        for model_name in list(service._models.keys()):
            try:
                job = await service.check_and_retrain_if_needed(model_name)
                if job:
                    results.append({
                        "model": model_name,
                        "job_id": job.job_id,
                        "status": job.status,
                    })
            except Exception as e:
                results.append({
                    "model": model_name,
                    "error": str(e),
                })
        
        return results
    
    return {
        "check_drift_and_retrain": check_drift_and_retrain,
        "scheduled_retrain_all": scheduled_retrain_all,
    }


# =============================================================================
# Singleton
# =============================================================================


_continuous_learning_service: ContinuousLearningService | None = None


def get_continuous_learning_service() -> ContinuousLearningService:
    """Get the continuous learning service singleton."""
    global _continuous_learning_service
    if _continuous_learning_service is None:
        _continuous_learning_service = ContinuousLearningService()
    return _continuous_learning_service


def reset_continuous_learning_service() -> None:
    """Reset the singleton (for testing)."""
    global _continuous_learning_service
    _continuous_learning_service = None

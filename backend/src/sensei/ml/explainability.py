"""
ML Model Explainability with SHAP and LIME.

Provides interpretable machine learning explanations:
- SHAP (SHapley Additive exPlanations) for global and local feature importance
- LIME (Local Interpretable Model-agnostic Explanations) for local explanations
- Integrated visualization and reporting
- Caching for performance optimization

This module enables transparent AI decision-making for compliance and trust.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import numpy as np
import joblib

# Optional SHAP import with fallback
try:
    import shap
    HAS_SHAP = True
except ImportError:
    shap = None  # type: ignore
    HAS_SHAP = False

# Optional LIME import with fallback
try:
    from lime.lime_tabular import LimeTabularExplainer
    HAS_LIME = True
except ImportError:
    LimeTabularExplainer = None  # type: ignore
    HAS_LIME = False

# Optional sklearn for synthetic data generation
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.linear_model import LogisticRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Enums and Constants
# =============================================================================


class ExplanationType(str, Enum):
    """Types of model explanations."""
    
    SHAP_LOCAL = "shap_local"
    SHAP_GLOBAL = "shap_global"
    LIME_LOCAL = "lime_local"
    FEATURE_IMPORTANCE = "feature_importance"
    DECISION_PATH = "decision_path"
    COUNTERFACTUAL = "counterfactual"


class ModelType(str, Enum):
    """Supported model types for explainability."""
    
    TREE_ENSEMBLE = "tree_ensemble"  # RandomForest, GradientBoosting, XGBoost
    LINEAR = "linear"  # LogisticRegression, LinearRegression
    DEEP_LEARNING = "deep_learning"  # Neural networks
    GENERIC = "generic"  # Any model with predict function


# Default feature names for CBM predictor
CBM_FEATURE_NAMES = [
    "temperature",
    "vibration",
    "pressure",
    "current",
    "noise",
    "operating_hours",
    "temp_mean",
    "temp_std",
    "vib_mean",
    "vib_std",
    "temp_trend",
    "vib_trend",
    "equipment_age_days",
    "total_operating_hours",
    "total_cycles",
    "days_since_maintenance",
    "maintenance_count",
    "avg_maintenance_interval",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class FeatureContribution:
    """Single feature's contribution to a prediction."""
    
    feature_name: str
    feature_value: float
    contribution: float  # SHAP value or LIME weight
    contribution_abs: float
    direction: str  # "positive", "negative", "neutral"
    percentile_rank: Optional[float] = None  # Where this feature contribution ranks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "feature_value": self.feature_value,
            "contribution": self.contribution,
            "contribution_abs": self.contribution_abs,
            "direction": self.direction,
            "percentile_rank": self.percentile_rank,
        }


@dataclass
class LocalExplanation:
    """
    Local explanation for a single prediction.
    
    Contains feature contributions explaining why a specific prediction was made.
    """
    
    explanation_id: UUID
    model_name: str
    explanation_type: ExplanationType
    timestamp: datetime
    
    # Prediction details
    input_features: Dict[str, float]
    predicted_class: Optional[int]
    predicted_probability: float
    base_value: float  # Expected value (SHAP) or intercept (LIME)
    
    # Feature contributions (sorted by importance)
    feature_contributions: List[FeatureContribution]
    
    # Summary
    top_positive_features: List[str]  # Features pushing prediction up
    top_negative_features: List[str]  # Features pushing prediction down
    natural_language_explanation: str
    
    # Metadata
    computation_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": str(self.explanation_id),
            "model_name": self.model_name,
            "explanation_type": self.explanation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "input_features": self.input_features,
            "predicted_class": self.predicted_class,
            "predicted_probability": self.predicted_probability,
            "base_value": self.base_value,
            "feature_contributions": [fc.to_dict() for fc in self.feature_contributions],
            "top_positive_features": self.top_positive_features,
            "top_negative_features": self.top_negative_features,
            "natural_language_explanation": self.natural_language_explanation,
            "computation_time_ms": self.computation_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class GlobalExplanation:
    """
    Global explanation for model behavior.
    
    Contains overall feature importance and feature interaction effects.
    """
    
    explanation_id: UUID
    model_name: str
    explanation_type: ExplanationType
    timestamp: datetime
    
    # Global feature importance (sorted by importance)
    feature_importance: Dict[str, float]
    feature_importance_std: Dict[str, float]  # Standard deviation of SHAP values
    
    # Feature interactions (top pairs)
    feature_interactions: List[Dict[str, Any]]
    
    # Summary
    top_features: List[str]
    natural_language_summary: str
    
    # Training data stats used for explanation
    num_samples_used: int
    
    # Metadata
    computation_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": str(self.explanation_id),
            "model_name": self.model_name,
            "explanation_type": self.explanation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "feature_importance": self.feature_importance,
            "feature_importance_std": self.feature_importance_std,
            "feature_interactions": self.feature_interactions,
            "top_features": self.top_features,
            "natural_language_summary": self.natural_language_summary,
            "num_samples_used": self.num_samples_used,
            "computation_time_ms": self.computation_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class CounterfactualExplanation:
    """
    Counterfactual explanation showing what changes would flip the prediction.
    """
    
    explanation_id: UUID
    model_name: str
    timestamp: datetime
    
    # Original prediction
    original_input: Dict[str, float]
    original_prediction: int
    original_probability: float
    
    # Counterfactual
    counterfactual_input: Dict[str, float]
    counterfactual_prediction: int
    counterfactual_probability: float
    
    # Changes needed
    feature_changes: List[Dict[str, Any]]  # {feature, original, changed, delta}
    num_features_changed: int
    total_change_magnitude: float
    
    # Natural language
    natural_language_explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": str(self.explanation_id),
            "model_name": self.model_name,
            "timestamp": self.timestamp.isoformat(),
            "original_input": self.original_input,
            "original_prediction": self.original_prediction,
            "original_probability": self.original_probability,
            "counterfactual_input": self.counterfactual_input,
            "counterfactual_prediction": self.counterfactual_prediction,
            "counterfactual_probability": self.counterfactual_probability,
            "feature_changes": self.feature_changes,
            "num_features_changed": self.num_features_changed,
            "total_change_magnitude": self.total_change_magnitude,
            "natural_language_explanation": self.natural_language_explanation,
        }


# =============================================================================
# SHAP Explainer
# =============================================================================


class SHAPExplainer:
    """
    SHAP-based model explainability.
    
    Provides both local (individual prediction) and global (model-level)
    explanations using SHAP values.
    """
    
    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        model_type: ModelType = ModelType.GENERIC,
        background_data: Optional[np.ndarray] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained model with predict/predict_proba methods
            feature_names: Names of input features
            model_type: Type of model for optimized explanations
            background_data: Background dataset for SHAP computations
            cache_dir: Directory to cache computed SHAP values
        """
        if not HAS_SHAP:
            raise ImportError(
                "SHAP is not installed. Install with: pip install shap"
            )
        
        self.model = model
        self.feature_names = feature_names
        self.model_type = model_type
        self.background_data = background_data
        self.cache_dir = cache_dir
        
        self._explainer: Optional[Any] = None
        self._global_shap_values: Optional[np.ndarray] = None
        
        self._initialize_explainer()
    
    def _initialize_explainer(self) -> None:
        """Initialize appropriate SHAP explainer based on model type."""
        try:
            if self.model_type == ModelType.TREE_ENSEMBLE:
                # Use TreeExplainer for tree-based models (fast, exact)
                self._explainer = shap.TreeExplainer(self.model)
                logger.info("Initialized SHAP TreeExplainer")
            elif self.model_type == ModelType.LINEAR:
                # Use LinearExplainer for linear models
                if self.background_data is not None:
                    self._explainer = shap.LinearExplainer(
                        self.model, self.background_data
                    )
                else:
                    logger.warning("LinearExplainer requires background data")
                    self._fallback_to_kernel_explainer()
                logger.info("Initialized SHAP LinearExplainer")
            else:
                self._fallback_to_kernel_explainer()
        except Exception as e:
            logger.warning(f"Failed to initialize optimal explainer: {e}")
            self._fallback_to_kernel_explainer()
    
    def _fallback_to_kernel_explainer(self) -> None:
        """Fallback to KernelExplainer (model-agnostic, slower)."""
        if self.background_data is not None:
            # Sample background data for efficiency
            if len(self.background_data) > 100:
                indices = np.random.choice(
                    len(self.background_data), 100, replace=False
                )
                background_sample = self.background_data[indices]
            else:
                background_sample = self.background_data
            
            self._explainer = shap.KernelExplainer(
                self._predict_fn, background_sample
            )
            logger.info("Initialized SHAP KernelExplainer with background data")
        else:
            # Generate synthetic background data
            synthetic_data = self._generate_synthetic_background()
            self._explainer = shap.KernelExplainer(
                self._predict_fn, synthetic_data
            )
            logger.info("Initialized SHAP KernelExplainer with synthetic data")
    
    def _predict_fn(self, X: np.ndarray) -> np.ndarray:
        """Prediction function for SHAP."""
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)[:, 1]
        return self.model.predict(X)
    
    def _generate_synthetic_background(self, n_samples: int = 100) -> np.ndarray:
        """Generate synthetic background data for SHAP computations."""
        # Use reasonable ranges for CBM features
        np.random.seed(42)
        n_features = len(self.feature_names)
        
        # Define feature ranges based on domain knowledge
        feature_ranges = {
            "temperature": (20, 80),
            "vibration": (0, 10),
            "pressure": (50, 150),
            "current": (0, 20),
            "noise": (40, 85),
            "operating_hours": (0, 10000),
            "temp_mean": (20, 70),
            "temp_std": (0, 10),
            "vib_mean": (0, 8),
            "vib_std": (0, 3),
            "temp_trend": (-1, 1),
            "vib_trend": (-1, 1),
            "equipment_age_days": (0, 3650),
            "total_operating_hours": (0, 50000),
            "total_cycles": (0, 100000),
            "days_since_maintenance": (0, 365),
            "maintenance_count": (0, 50),
            "avg_maintenance_interval": (0, 365),
        }
        
        data = np.zeros((n_samples, n_features))
        for i, fname in enumerate(self.feature_names):
            low, high = feature_ranges.get(fname, (0, 100))
            data[:, i] = np.random.uniform(low, high, n_samples)
        
        return data
    
    def explain_prediction(
        self,
        input_features: np.ndarray,
        predicted_class: Optional[int] = None,
        predicted_probability: Optional[float] = None,
    ) -> LocalExplanation:
        """
        Generate SHAP-based local explanation for a single prediction.
        
        Args:
            input_features: Feature vector (1D array)
            predicted_class: Optional predicted class
            predicted_probability: Optional predicted probability
            
        Returns:
            LocalExplanation with feature contributions
        """
        import time
        start_time = time.time()
        
        # Ensure 2D input
        X = input_features.reshape(1, -1)
        
        # Compute SHAP values
        shap_values = self._explainer.shap_values(X)
        
        # Handle multi-class output
        if isinstance(shap_values, list):
            # For binary classification, use positive class
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        
        shap_values = shap_values.flatten()
        
        # Get base value
        if hasattr(self._explainer, 'expected_value'):
            base_value = self._explainer.expected_value
            if isinstance(base_value, np.ndarray):
                base_value = float(base_value[1]) if len(base_value) > 1 else float(base_value[0])
            else:
                base_value = float(base_value)
        else:
            base_value = 0.5
        
        # Get prediction if not provided
        if predicted_probability is None:
            predicted_probability = float(self._predict_fn(X)[0])
        if predicted_class is None:
            predicted_class = 1 if predicted_probability >= 0.5 else 0
        
        # Build feature contributions
        contributions = []
        for i, (fname, fval, shap_val) in enumerate(
            zip(self.feature_names, input_features, shap_values)
        ):
            direction = "positive" if shap_val > 0.01 else ("negative" if shap_val < -0.01 else "neutral")
            contributions.append(FeatureContribution(
                feature_name=fname,
                feature_value=float(fval),
                contribution=float(shap_val),
                contribution_abs=abs(float(shap_val)),
                direction=direction,
            ))
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: x.contribution_abs, reverse=True)
        
        # Add percentile ranks
        total_abs = sum(c.contribution_abs for c in contributions)
        if total_abs > 0:
            cumsum = 0
            for c in contributions:
                cumsum += c.contribution_abs
                c.percentile_rank = cumsum / total_abs
        
        # Extract top features
        top_positive = [c.feature_name for c in contributions if c.direction == "positive"][:3]
        top_negative = [c.feature_name for c in contributions if c.direction == "negative"][:3]
        
        # Generate natural language explanation
        nl_explanation = self._generate_local_explanation(
            contributions, predicted_class, predicted_probability
        )
        
        computation_time = (time.time() - start_time) * 1000
        
        return LocalExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            explanation_type=ExplanationType.SHAP_LOCAL,
            timestamp=_utcnow(),
            input_features={fn: float(fv) for fn, fv in zip(self.feature_names, input_features)},
            predicted_class=predicted_class,
            predicted_probability=predicted_probability,
            base_value=base_value,
            feature_contributions=contributions,
            top_positive_features=top_positive,
            top_negative_features=top_negative,
            natural_language_explanation=nl_explanation,
            computation_time_ms=computation_time,
        )
    
    def explain_global(
        self,
        X_data: np.ndarray,
        max_samples: int = 1000,
    ) -> GlobalExplanation:
        """
        Generate SHAP-based global explanation.
        
        Args:
            X_data: Feature matrix for computing global importance
            max_samples: Maximum samples to use (for efficiency)
            
        Returns:
            GlobalExplanation with global feature importance
        """
        import time
        start_time = time.time()
        
        # Sample data if too large
        if len(X_data) > max_samples:
            indices = np.random.choice(len(X_data), max_samples, replace=False)
            X_sample = X_data[indices]
        else:
            X_sample = X_data
        
        # Compute SHAP values for all samples
        shap_values = self._explainer.shap_values(X_sample)
        
        # Handle multi-class output
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        
        self._global_shap_values = shap_values
        
        # Compute global importance (mean absolute SHAP value per feature)
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        std_shap = np.std(shap_values, axis=0)
        
        # Build importance dict
        feature_importance = {
            fname: float(val)
            for fname, val in zip(self.feature_names, mean_abs_shap)
        }
        feature_importance_std = {
            fname: float(val)
            for fname, val in zip(self.feature_names, std_shap)
        }
        
        # Sort by importance
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )
        top_features = [f[0] for f in sorted_features[:5]]
        
        # Compute feature interactions (simplified)
        interactions = self._compute_feature_interactions(shap_values, top_n=5)
        
        # Generate natural language summary
        nl_summary = self._generate_global_summary(sorted_features)
        
        computation_time = (time.time() - start_time) * 1000
        
        return GlobalExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            explanation_type=ExplanationType.SHAP_GLOBAL,
            timestamp=_utcnow(),
            feature_importance=dict(sorted_features),
            feature_importance_std=feature_importance_std,
            feature_interactions=interactions,
            top_features=top_features,
            natural_language_summary=nl_summary,
            num_samples_used=len(X_sample),
            computation_time_ms=computation_time,
        )
    
    def _compute_feature_interactions(
        self,
        shap_values: np.ndarray,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Compute top feature interactions based on correlation of SHAP values."""
        n_features = shap_values.shape[1]
        interactions = []
        
        for i in range(n_features):
            for j in range(i + 1, n_features):
                # Correlation between SHAP values indicates interaction
                corr = np.corrcoef(shap_values[:, i], shap_values[:, j])[0, 1]
                if not np.isnan(corr):
                    interactions.append({
                        "feature_1": self.feature_names[i],
                        "feature_2": self.feature_names[j],
                        "interaction_strength": abs(float(corr)),
                        "direction": "positive" if corr > 0 else "negative",
                    })
        
        # Sort and return top interactions
        interactions.sort(key=lambda x: x["interaction_strength"], reverse=True)
        return interactions[:top_n]
    
    def _generate_local_explanation(
        self,
        contributions: List[FeatureContribution],
        predicted_class: int,
        predicted_probability: float,
    ) -> str:
        """Generate natural language explanation for local prediction."""
        outcome = "high failure risk" if predicted_class == 1 else "low failure risk"
        prob_pct = predicted_probability * 100
        
        # Get top 3 contributors
        top_contributors = contributions[:3]
        
        explanations = []
        for c in top_contributors:
            if c.direction == "positive":
                explanations.append(
                    f"{c.feature_name}={c.feature_value:.1f} (increasing risk by {c.contribution:.3f})"
                )
            elif c.direction == "negative":
                explanations.append(
                    f"{c.feature_name}={c.feature_value:.1f} (decreasing risk by {abs(c.contribution):.3f})"
                )
        
        reason_text = "; ".join(explanations) if explanations else "balanced feature values"
        
        return (
            f"The model predicts {outcome} with {prob_pct:.1f}% confidence. "
            f"Key factors: {reason_text}."
        )
    
    def _generate_global_summary(
        self,
        sorted_features: List[Tuple[str, float]],
    ) -> str:
        """Generate natural language summary of global feature importance."""
        top_5 = sorted_features[:5]
        total_importance = sum(f[1] for f in sorted_features)
        top_5_importance = sum(f[1] for f in top_5)
        top_5_pct = (top_5_importance / total_importance * 100) if total_importance > 0 else 0
        
        feature_list = ", ".join([f"{f[0]} ({f[1]:.3f})" for f in top_5])
        
        return (
            f"The model's predictions are most influenced by: {feature_list}. "
            f"These top 5 features account for {top_5_pct:.1f}% of the model's decision-making."
        )


# =============================================================================
# LIME Explainer
# =============================================================================


class LIMEExplainer:
    """
    LIME-based model explainability.
    
    Provides local interpretable model-agnostic explanations.
    """
    
    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        training_data: Optional[np.ndarray] = None,
        mode: str = "classification",
    ):
        """
        Initialize LIME explainer.
        
        Args:
            model: Trained model with predict/predict_proba methods
            feature_names: Names of input features
            training_data: Training data for LIME reference distribution
            mode: "classification" or "regression"
        """
        if not HAS_LIME:
            raise ImportError(
                "LIME is not installed. Install with: pip install lime"
            )
        
        self.model = model
        self.feature_names = feature_names
        self.mode = mode
        
        # Generate synthetic training data if not provided
        if training_data is None:
            training_data = self._generate_synthetic_training_data()
        
        self._explainer = LimeTabularExplainer(
            training_data,
            feature_names=feature_names,
            mode=mode,
            discretize_continuous=True,
        )
    
    def _generate_synthetic_training_data(self, n_samples: int = 500) -> np.ndarray:
        """Generate synthetic training data for LIME."""
        np.random.seed(42)
        n_features = len(self.feature_names)
        
        # Use same ranges as SHAP
        feature_ranges = {
            "temperature": (20, 80),
            "vibration": (0, 10),
            "pressure": (50, 150),
            "current": (0, 20),
            "noise": (40, 85),
            "operating_hours": (0, 10000),
            "temp_mean": (20, 70),
            "temp_std": (0, 10),
            "vib_mean": (0, 8),
            "vib_std": (0, 3),
            "temp_trend": (-1, 1),
            "vib_trend": (-1, 1),
            "equipment_age_days": (0, 3650),
            "total_operating_hours": (0, 50000),
            "total_cycles": (0, 100000),
            "days_since_maintenance": (0, 365),
            "maintenance_count": (0, 50),
            "avg_maintenance_interval": (0, 365),
        }
        
        data = np.zeros((n_samples, n_features))
        for i, fname in enumerate(self.feature_names):
            low, high = feature_ranges.get(fname, (0, 100))
            data[:, i] = np.random.uniform(low, high, n_samples)
        
        return data
    
    def _predict_fn(self, X: np.ndarray) -> np.ndarray:
        """Prediction function for LIME."""
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)
        # For regression, return predictions as 2D array
        preds = self.model.predict(X)
        return np.column_stack([1 - preds, preds])
    
    def explain_prediction(
        self,
        input_features: np.ndarray,
        num_features: int = 10,
        num_samples: int = 5000,
    ) -> LocalExplanation:
        """
        Generate LIME-based local explanation.
        
        Args:
            input_features: Feature vector (1D array)
            num_features: Number of features to include in explanation
            num_samples: Number of samples for LIME perturbations
            
        Returns:
            LocalExplanation with feature contributions
        """
        import time
        start_time = time.time()
        
        # Get LIME explanation
        exp = self._explainer.explain_instance(
            input_features,
            self._predict_fn,
            num_features=num_features,
            num_samples=num_samples,
        )
        
        # Get prediction
        proba = self._predict_fn(input_features.reshape(1, -1))[0]
        predicted_probability = float(proba[1])
        predicted_class = 1 if predicted_probability >= 0.5 else 0
        
        # Extract local prediction (intercept)
        base_value = float(exp.intercept[1]) if hasattr(exp, 'intercept') else 0.5
        
        # Build feature contributions from LIME weights
        lime_list = exp.as_list(label=1)  # For positive class
        
        # Create mapping from LIME feature descriptions to actual feature names
        contributions = []
        for lime_feat, weight in lime_list:
            # Parse LIME's feature description (e.g., "temperature > 50.00")
            feature_name = self._parse_lime_feature(lime_feat)
            feature_idx = self.feature_names.index(feature_name) if feature_name in self.feature_names else -1
            
            if feature_idx >= 0:
                fval = input_features[feature_idx]
            else:
                fval = 0.0
            
            direction = "positive" if weight > 0.01 else ("negative" if weight < -0.01 else "neutral")
            contributions.append(FeatureContribution(
                feature_name=feature_name if feature_name else lime_feat,
                feature_value=float(fval),
                contribution=float(weight),
                contribution_abs=abs(float(weight)),
                direction=direction,
            ))
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: x.contribution_abs, reverse=True)
        
        # Extract top features
        top_positive = [c.feature_name for c in contributions if c.direction == "positive"][:3]
        top_negative = [c.feature_name for c in contributions if c.direction == "negative"][:3]
        
        # Generate natural language explanation
        nl_explanation = self._generate_lime_explanation(
            contributions, predicted_class, predicted_probability
        )
        
        computation_time = (time.time() - start_time) * 1000
        
        return LocalExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            explanation_type=ExplanationType.LIME_LOCAL,
            timestamp=_utcnow(),
            input_features={fn: float(fv) for fn, fv in zip(self.feature_names, input_features)},
            predicted_class=predicted_class,
            predicted_probability=predicted_probability,
            base_value=base_value,
            feature_contributions=contributions,
            top_positive_features=top_positive,
            top_negative_features=top_negative,
            natural_language_explanation=nl_explanation,
            computation_time_ms=computation_time,
        )
    
    def _parse_lime_feature(self, lime_description: str) -> str:
        """Parse LIME's feature description to extract feature name."""
        # LIME generates descriptions like "temperature > 50.00" or "vibration <= 5.00"
        for fname in self.feature_names:
            if fname in lime_description:
                return fname
        return lime_description.split()[0] if lime_description else "unknown"
    
    def _generate_lime_explanation(
        self,
        contributions: List[FeatureContribution],
        predicted_class: int,
        predicted_probability: float,
    ) -> str:
        """Generate natural language explanation from LIME."""
        outcome = "high failure risk" if predicted_class == 1 else "low failure risk"
        prob_pct = predicted_probability * 100
        
        top_contributors = contributions[:3]
        
        explanations = []
        for c in top_contributors:
            if c.direction == "positive":
                explanations.append(
                    f"{c.feature_name} (contributing +{c.contribution:.3f} to risk)"
                )
            elif c.direction == "negative":
                explanations.append(
                    f"{c.feature_name} (contributing {c.contribution:.3f} to risk)"
                )
        
        reason_text = "; ".join(explanations) if explanations else "balanced conditions"
        
        return (
            f"LIME analysis predicts {outcome} with {prob_pct:.1f}% probability. "
            f"Primary factors: {reason_text}."
        )


# =============================================================================
# Unified Explainability Service
# =============================================================================


class ModelExplainabilityService:
    """
    Unified service for model explainability.
    
    Provides a single interface to SHAP, LIME, and other explanation methods.
    Includes caching, persistence, and comparison utilities.
    """
    
    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        model_type: ModelType = ModelType.TREE_ENSEMBLE,
        background_data: Optional[np.ndarray] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize explainability service.
        
        Args:
            model: Trained model
            feature_names: Feature names
            model_type: Type of model
            background_data: Background data for SHAP
            cache_dir: Directory for caching explanations
        """
        self.model = model
        self.feature_names = feature_names
        self.model_type = model_type
        self.background_data = background_data
        self.cache_dir = cache_dir
        
        self._shap_explainer: Optional[SHAPExplainer] = None
        self._lime_explainer: Optional[LIMEExplainer] = None
        
        # Explanation cache
        self._explanation_cache: Dict[str, Any] = {}
    
    def _get_shap_explainer(self) -> SHAPExplainer:
        """Get or create SHAP explainer."""
        if self._shap_explainer is None:
            self._shap_explainer = SHAPExplainer(
                model=self.model,
                feature_names=self.feature_names,
                model_type=self.model_type,
                background_data=self.background_data,
                cache_dir=self.cache_dir,
            )
        return self._shap_explainer
    
    def _get_lime_explainer(self) -> LIMEExplainer:
        """Get or create LIME explainer."""
        if self._lime_explainer is None:
            self._lime_explainer = LIMEExplainer(
                model=self.model,
                feature_names=self.feature_names,
                training_data=self.background_data,
            )
        return self._lime_explainer
    
    def explain_with_shap(
        self,
        input_features: np.ndarray,
        predicted_class: Optional[int] = None,
        predicted_probability: Optional[float] = None,
    ) -> LocalExplanation:
        """Generate SHAP-based local explanation."""
        if not HAS_SHAP:
            raise ImportError("SHAP is not installed")
        return self._get_shap_explainer().explain_prediction(
            input_features, predicted_class, predicted_probability
        )
    
    def explain_with_lime(
        self,
        input_features: np.ndarray,
        num_features: int = 10,
    ) -> LocalExplanation:
        """Generate LIME-based local explanation."""
        if not HAS_LIME:
            raise ImportError("LIME is not installed")
        return self._get_lime_explainer().explain_prediction(
            input_features, num_features=num_features
        )
    
    def explain_global(
        self,
        X_data: np.ndarray,
    ) -> GlobalExplanation:
        """Generate global model explanation using SHAP."""
        if not HAS_SHAP:
            raise ImportError("SHAP is not installed")
        return self._get_shap_explainer().explain_global(X_data)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from the model.
        
        Falls back to tree-based importance if SHAP unavailable.
        """
        # Try tree-based importance first (fast)
        if hasattr(self.model, 'feature_importances_'):
            return {
                fname: float(imp)
                for fname, imp in zip(
                    self.feature_names,
                    self.model.feature_importances_
                )
            }
        
        # Fallback to coefficients for linear models
        if hasattr(self.model, 'coef_'):
            coefs = self.model.coef_.flatten()
            return {
                fname: abs(float(coef))
                for fname, coef in zip(self.feature_names, coefs)
            }
        
        return {}
    
    def generate_counterfactual(
        self,
        input_features: np.ndarray,
        desired_class: int = 0,
        max_changes: int = 3,
    ) -> CounterfactualExplanation:
        """
        Generate counterfactual explanation.
        
        Finds minimal changes to flip the prediction.
        
        Args:
            input_features: Original feature vector
            desired_class: Target class (default: flip to class 0)
            max_changes: Maximum number of features to change
            
        Returns:
            CounterfactualExplanation showing what changes would flip prediction
        """
        # Get original prediction
        if hasattr(self.model, 'predict_proba'):
            orig_proba = self.model.predict_proba(input_features.reshape(1, -1))[0]
            orig_pred = int(np.argmax(orig_proba))
            orig_prob = float(orig_proba[orig_pred])
        else:
            orig_pred = int(self.model.predict(input_features.reshape(1, -1))[0])
            orig_prob = 1.0
        
        # If already desired class, no counterfactual needed
        if orig_pred == desired_class:
            return CounterfactualExplanation(
                explanation_id=uuid4(),
                model_name="cbm_predictor",
                timestamp=_utcnow(),
                original_input={fn: float(fv) for fn, fv in zip(self.feature_names, input_features)},
                original_prediction=orig_pred,
                original_probability=orig_prob,
                counterfactual_input={fn: float(fv) for fn, fv in zip(self.feature_names, input_features)},
                counterfactual_prediction=orig_pred,
                counterfactual_probability=orig_prob,
                feature_changes=[],
                num_features_changed=0,
                total_change_magnitude=0.0,
                natural_language_explanation="No changes needed - already at desired outcome.",
            )
        
        # Get feature importance to prioritize changes
        importance = self.get_feature_importance()
        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        
        # Try changing top features one at a time
        best_counterfactual = input_features.copy()
        feature_changes = []
        
        for fname, _ in sorted_features[:max_changes]:
            idx = self.feature_names.index(fname)
            original_value = input_features[idx]
            
            # Try different modifications
            for multiplier in [0.5, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9, 0.0]:
                modified = best_counterfactual.copy()
                new_value = original_value * multiplier
                modified[idx] = new_value
                
                # Check prediction
                if hasattr(self.model, 'predict_proba'):
                    proba = self.model.predict_proba(modified.reshape(1, -1))[0]
                    pred = int(np.argmax(proba))
                else:
                    pred = int(self.model.predict(modified.reshape(1, -1))[0])
                
                if pred == desired_class:
                    best_counterfactual = modified
                    feature_changes.append({
                        "feature": fname,
                        "original_value": float(original_value),
                        "changed_value": float(new_value),
                        "delta": float(new_value - original_value),
                    })
                    break
            
            # Check if we've achieved the goal
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(best_counterfactual.reshape(1, -1))[0]
                pred = int(np.argmax(proba))
                prob = float(proba[pred])
            else:
                pred = int(self.model.predict(best_counterfactual.reshape(1, -1))[0])
                prob = 1.0
            
            if pred == desired_class:
                break
        
        # Calculate total change magnitude
        total_magnitude = sum(abs(fc["delta"]) for fc in feature_changes)
        
        # Generate natural language
        if feature_changes:
            changes_text = ", ".join([
                f"change {fc['feature']} from {fc['original_value']:.1f} to {fc['changed_value']:.1f}"
                for fc in feature_changes
            ])
            nl_explanation = f"To achieve desired outcome, {changes_text}."
        else:
            nl_explanation = "Could not find counterfactual within constraints."
        
        return CounterfactualExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            timestamp=_utcnow(),
            original_input={fn: float(fv) for fn, fv in zip(self.feature_names, input_features)},
            original_prediction=orig_pred,
            original_probability=orig_prob,
            counterfactual_input={fn: float(fv) for fn, fv in zip(self.feature_names, best_counterfactual)},
            counterfactual_prediction=pred,
            counterfactual_probability=prob,
            feature_changes=feature_changes,
            num_features_changed=len(feature_changes),
            total_change_magnitude=total_magnitude,
            natural_language_explanation=nl_explanation,
        )
    
    def compare_explanations(
        self,
        input_features: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Compare SHAP and LIME explanations for the same prediction.
        
        Useful for validating explanations and understanding model behavior.
        """
        result = {
            "input_features": {fn: float(fv) for fn, fv in zip(self.feature_names, input_features)},
            "explanations": {},
        }
        
        # SHAP explanation
        if HAS_SHAP:
            try:
                shap_exp = self.explain_with_shap(input_features)
                result["explanations"]["shap"] = shap_exp.to_dict()
            except Exception as e:
                result["explanations"]["shap_error"] = str(e)
        
        # LIME explanation
        if HAS_LIME:
            try:
                lime_exp = self.explain_with_lime(input_features)
                result["explanations"]["lime"] = lime_exp.to_dict()
            except Exception as e:
                result["explanations"]["lime_error"] = str(e)
        
        # Feature importance
        result["feature_importance"] = self.get_feature_importance()
        
        # Agreement analysis
        if "shap" in result["explanations"] and "lime" in result["explanations"]:
            shap_top = result["explanations"]["shap"]["top_positive_features"]
            lime_top = result["explanations"]["lime"]["top_positive_features"]
            overlap = set(shap_top) & set(lime_top)
            result["agreement"] = {
                "top_features_overlap": list(overlap),
                "agreement_score": len(overlap) / max(len(shap_top), len(lime_top), 1),
            }
        
        return result


# =============================================================================
# Factory Function
# =============================================================================


def create_explainability_service(
    model: Any,
    feature_names: Optional[List[str]] = None,
    model_type: ModelType = ModelType.TREE_ENSEMBLE,
    background_data: Optional[np.ndarray] = None,
) -> ModelExplainabilityService:
    """
    Factory function to create explainability service.
    
    Args:
        model: Trained model
        feature_names: Feature names (defaults to CBM features)
        model_type: Type of model
        background_data: Background data for SHAP
        
    Returns:
        Configured ModelExplainabilityService
    """
    if feature_names is None:
        feature_names = CBM_FEATURE_NAMES
    
    return ModelExplainabilityService(
        model=model,
        feature_names=feature_names,
        model_type=model_type,
        background_data=background_data,
    )


# =============================================================================
# Availability Check
# =============================================================================


def check_explainability_availability() -> Dict[str, bool]:
    """Check which explainability libraries are available."""
    return {
        "shap": HAS_SHAP,
        "lime": HAS_LIME,
        "sklearn": HAS_SKLEARN,
    }

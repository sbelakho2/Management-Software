"""
Predictive Win/Loss Attribution - Explainable AI for RFQ outcome prediction.

Includes:
- Explainability (SHAP/LIME): Feature contribution analysis
- Counterfactual Analysis: "What if" simulations
- Confidence Intervals: Score ranges based on data volatility
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, Union
import math
import random
from collections import defaultdict
import hashlib


# =============================================================================
# Constants
# =============================================================================

DEFAULT_CONFIDENCE_LEVEL = 0.95
MIN_SAMPLES_FOR_PREDICTION = 10
SHAP_SAMPLE_SIZE = 100


# =============================================================================
# Enums
# =============================================================================

class PredictionOutcome(Enum):
    """Predicted outcome."""
    WIN = "win"
    LOSS = "loss"
    UNCERTAIN = "uncertain"


class FeatureCategory(Enum):
    """Feature categories for analysis."""
    PRICE = "price"
    TIMELINE = "timeline"
    QUALITY = "quality"
    RELATIONSHIP = "relationship"
    COMPETITION = "competition"
    TECHNICAL = "technical"
    CAPACITY = "capacity"


class ContributionDirection(Enum):
    """Direction of feature contribution."""
    POSITIVE = "positive"  # Increases win probability
    NEGATIVE = "negative"  # Decreases win probability
    NEUTRAL = "neutral"


class ExplainerType(Enum):
    """Type of explainability method."""
    SHAP = "shap"
    LIME = "lime"
    PERMUTATION = "permutation"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Feature:
    """A feature used in prediction."""
    name: str
    value: float
    category: FeatureCategory
    description: str = ""
    normalized_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0


@dataclass
class FeatureContribution:
    """Contribution of a feature to the prediction."""
    feature_name: str
    category: FeatureCategory
    contribution: float  # SHAP value or similar
    direction: ContributionDirection
    importance_rank: int = 0
    baseline_value: float = 0.0
    actual_value: float = 0.0
    explanation: str = ""


@dataclass
class ConfidenceInterval:
    """Confidence interval for a prediction."""
    point_estimate: float
    lower_bound: float
    upper_bound: float
    confidence_level: float
    std_error: float
    sample_size: int
    
    @property
    def margin_of_error(self) -> float:
        """Calculate margin of error."""
        return (self.upper_bound - self.lower_bound) / 2
    
    @property
    def interval_width(self) -> float:
        """Get interval width as percentage."""
        return (self.upper_bound - self.lower_bound) * 100
    
    def format(self) -> str:
        """Format as display string."""
        return f"{self.point_estimate * 100:.0f}% ± {self.margin_of_error * 100:.1f}%"


@dataclass
class CounterfactualScenario:
    """A counterfactual what-if scenario."""
    scenario_id: str
    description: str
    feature_changes: dict[str, float]
    original_prediction: float
    counterfactual_prediction: float
    prediction_change: float
    is_favorable: bool
    recommendations: list[str] = field(default_factory=list)
    
    @property
    def change_percentage(self) -> float:
        """Get change as percentage."""
        if self.original_prediction == 0:
            return 0.0
        return (self.counterfactual_prediction - self.original_prediction) / self.original_prediction * 100


@dataclass
class PredictionResult:
    """Complete prediction result with explainability."""
    prediction_id: str
    rfq_id: str
    timestamp: datetime
    
    # Core prediction
    win_probability: float
    outcome: PredictionOutcome
    confidence_interval: ConfidenceInterval
    
    # Explainability
    feature_contributions: list[FeatureContribution] = field(default_factory=list)
    explainer_type: ExplainerType = ExplainerType.SHAP
    
    # Counterfactuals
    counterfactual_scenarios: list[CounterfactualScenario] = field(default_factory=list)
    
    # Metadata
    model_version: str = "1.0"
    data_quality_score: float = 0.8
    
    def get_top_factors(self, n: int = 5) -> list[FeatureContribution]:
        """Get top N contributing factors."""
        sorted_contribs = sorted(
            self.feature_contributions,
            key=lambda x: abs(x.contribution),
            reverse=True,
        )
        return sorted_contribs[:n]
    
    def get_positive_factors(self) -> list[FeatureContribution]:
        """Get factors contributing positively."""
        return [
            c for c in self.feature_contributions
            if c.direction == ContributionDirection.POSITIVE
        ]
    
    def get_negative_factors(self) -> list[FeatureContribution]:
        """Get factors contributing negatively."""
        return [
            c for c in self.feature_contributions
            if c.direction == ContributionDirection.NEGATIVE
        ]


@dataclass
class HistoricalRFQ:
    """Historical RFQ data for training."""
    rfq_id: str
    customer_id: str
    features: dict[str, float]
    outcome: bool  # True = won, False = lost
    quote_price: float
    target_price: Optional[float] = None
    won_price: Optional[float] = None
    lost_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rfq_id": self.rfq_id,
            "customer_id": self.customer_id,
            "features": self.features,
            "outcome": self.outcome,
            "quote_price": self.quote_price,
            "target_price": self.target_price,
            "won_price": self.won_price,
            "lost_reason": self.lost_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoricalRFQ":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            rfq_id=data["rfq_id"],
            customer_id=data["customer_id"],
            features=data["features"],
            outcome=data["outcome"],
            quote_price=data["quote_price"],
            target_price=data.get("target_price"),
            won_price=data.get("won_price"),
            lost_reason=data.get("lost_reason"),
            created_at=created_at or datetime.now(timezone.utc),
        )


# =============================================================================
# Feature Engineering
# =============================================================================

class FeatureEngineer:
    """Engineers features from RFQ data."""
    
    FEATURE_DEFINITIONS = {
        "price_competitiveness": FeatureCategory.PRICE,
        "price_vs_target": FeatureCategory.PRICE,
        "margin_percentage": FeatureCategory.PRICE,
        "customer_win_rate": FeatureCategory.RELATIONSHIP,
        "customer_lifetime_value": FeatureCategory.RELATIONSHIP,
        "previous_orders": FeatureCategory.RELATIONSHIP,
        "days_to_deadline": FeatureCategory.TIMELINE,
        "response_time_days": FeatureCategory.TIMELINE,
        "technical_complexity": FeatureCategory.TECHNICAL,
        "dfm_score": FeatureCategory.TECHNICAL,
        "capacity_utilization": FeatureCategory.CAPACITY,
        "quality_history": FeatureCategory.QUALITY,
        "competitor_count": FeatureCategory.COMPETITION,
    }
    
    def __init__(self):
        """Initialize feature engineer."""
        self._feature_stats: dict[str, dict[str, float]] = {}
    
    def compute_feature_stats(self, historical_data: list[HistoricalRFQ]) -> None:
        """Compute feature statistics from historical data."""
        feature_values: dict[str, list[float]] = defaultdict(list)
        
        for rfq in historical_data:
            for name, value in rfq.features.items():
                feature_values[name].append(value)
        
        for name, values in feature_values.items():
            if values:
                self._feature_stats[name] = {
                    "mean": sum(values) / len(values),
                    "std": self._std_dev(values),
                    "min": min(values),
                    "max": max(values),
                }
    
    def _std_dev(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def normalize_features(self, features: dict[str, float]) -> dict[str, float]:
        """Normalize features using z-score normalization."""
        normalized = {}
        
        for name, value in features.items():
            stats = self._feature_stats.get(name)
            if stats and stats["std"] > 0:
                normalized[name] = (value - stats["mean"]) / stats["std"]
            else:
                normalized[name] = 0.0
        
        return normalized
    
    def get_feature_info(self, name: str, value: float) -> Feature:
        """Get feature with category information."""
        category = self.FEATURE_DEFINITIONS.get(name, FeatureCategory.TECHNICAL)
        stats = self._feature_stats.get(name, {})
        
        return Feature(
            name=name,
            value=value,
            category=category,
            normalized_value=self.normalize_features({name: value}).get(name, 0.0),
            min_value=stats.get("min", 0.0),
            max_value=stats.get("max", 1.0),
        )


# =============================================================================
# SHAP-like Explainer
# =============================================================================

class SHAPExplainer:
    """
    SHAP-like feature importance explainer.
    
    Uses a simplified Shapley value approximation with deterministic
    random sampling for reproducible explanations.
    """
    
    def __init__(
        self,
        model_predict: Callable[[dict[str, float]], float],
        random_seed: int = 42,
    ):
        """Initialize explainer with prediction function and random seed."""
        self.model_predict = model_predict
        self._baseline: Optional[dict[str, float]] = None
        self._baseline_prediction: float = 0.5
        self._rng = random.Random(random_seed)
    
    def set_baseline(self, baseline_features: dict[str, float]) -> None:
        """Set baseline (expected) feature values."""
        self._baseline = baseline_features.copy()
        self._baseline_prediction = self.model_predict(baseline_features)
    
    def explain(
        self,
        features: dict[str, float],
        feature_engineer: FeatureEngineer,
        n_samples: int = SHAP_SAMPLE_SIZE,
    ) -> list[FeatureContribution]:
        """Calculate SHAP-like values for features."""
        if self._baseline is None:
            self._baseline = {k: 0.0 for k in features.keys()}
            self._baseline_prediction = self.model_predict(self._baseline)
        
        contributions = []
        feature_names = list(features.keys())
        
        for feature_name in feature_names:
            shap_value = self._calculate_shap_value(
                feature_name,
                features,
                feature_names,
                n_samples,
            )
            
            direction = ContributionDirection.NEUTRAL
            if shap_value > 0.01:
                direction = ContributionDirection.POSITIVE
            elif shap_value < -0.01:
                direction = ContributionDirection.NEGATIVE
            
            category = FeatureEngineer.FEATURE_DEFINITIONS.get(
                feature_name, FeatureCategory.TECHNICAL
            )
            
            contributions.append(FeatureContribution(
                feature_name=feature_name,
                category=category,
                contribution=shap_value,
                direction=direction,
                baseline_value=self._baseline.get(feature_name, 0.0),
                actual_value=features[feature_name],
                explanation=self._generate_explanation(
                    feature_name, features[feature_name], shap_value
                ),
            ))
        
        # Assign importance ranks
        sorted_contribs = sorted(
            contributions,
            key=lambda x: abs(x.contribution),
            reverse=True,
        )
        for rank, contrib in enumerate(sorted_contribs, 1):
            contrib.importance_rank = rank
        
        return contributions
    
    def _calculate_shap_value(
        self,
        feature_name: str,
        features: dict[str, float],
        all_features: list[str],
        n_samples: int,
    ) -> float:
        """Calculate SHAP value for a single feature."""
        other_features = [f for f in all_features if f != feature_name]
        shap_value = 0.0
        
        if not other_features:
            # Only one feature
            with_feature = self.model_predict(features)
            without_feature = self._baseline_prediction
            return with_feature - without_feature
        
        # Sample coalition permutations using seeded RNG for reproducibility
        for _ in range(n_samples):
            # Random subset size
            k = self._rng.randint(0, len(other_features))
            
            # Random subset
            subset = self._rng.sample(other_features, k) if k > 0 else []
            
            # Compute marginal contribution
            with_feature_dict = {
                f: features[f] if f in subset or f == feature_name
                else self._baseline.get(f, 0.0)
                for f in all_features
            }
            without_feature_dict = {
                f: features[f] if f in subset
                else self._baseline.get(f, 0.0)
                for f in all_features
            }
            
            with_prediction = self.model_predict(with_feature_dict)
            without_prediction = self.model_predict(without_feature_dict)
            
            shap_value += (with_prediction - without_prediction)
        
        return shap_value / n_samples
    
    def _generate_explanation(
        self,
        feature_name: str,
        value: float,
        shap_value: float,
    ) -> str:
        """Generate human-readable explanation."""
        direction = "increases" if shap_value > 0 else "decreases"
        magnitude = abs(shap_value)
        
        if magnitude > 0.1:
            impact = "strongly"
        elif magnitude > 0.05:
            impact = "moderately"
        else:
            impact = "slightly"
        
        readable_name = feature_name.replace("_", " ")
        
        return f"{readable_name.capitalize()} of {value:.2f} {impact} {direction} win probability"


# =============================================================================
# LIME-like Explainer
# =============================================================================

class LIMEExplainer:
    """
    LIME-like local interpretable model explanation.
    
    Creates local linear approximations around predictions with
    deterministic random perturbations for reproducible explanations.
    """
    
    def __init__(
        self,
        model_predict: Callable[[dict[str, float]], float],
        random_seed: int = 42,
    ):
        """Initialize explainer with random seed for reproducibility."""
        self.model_predict = model_predict
        self._rng = random.Random(random_seed)
    
    def explain(
        self,
        features: dict[str, float],
        feature_engineer: FeatureEngineer,
        n_samples: int = 100,
        kernel_width: float = 0.75,
    ) -> list[FeatureContribution]:
        """Generate LIME explanation."""
        # Generate perturbed samples
        samples, weights, predictions = self._generate_samples(
            features, n_samples, kernel_width
        )
        
        # Fit local linear model
        coefficients = self._fit_local_model(samples, predictions, weights)
        
        contributions = []
        for feature_name, coef in coefficients.items():
            direction = ContributionDirection.NEUTRAL
            if coef > 0.01:
                direction = ContributionDirection.POSITIVE
            elif coef < -0.01:
                direction = ContributionDirection.NEGATIVE
            
            category = FeatureEngineer.FEATURE_DEFINITIONS.get(
                feature_name, FeatureCategory.TECHNICAL
            )
            
            contributions.append(FeatureContribution(
                feature_name=feature_name,
                category=category,
                contribution=coef * features[feature_name],
                direction=direction,
                actual_value=features[feature_name],
            ))
        
        return contributions
    
    def _generate_samples(
        self,
        features: dict[str, float],
        n_samples: int,
        kernel_width: float,
    ) -> tuple[list[dict[str, float]], list[float], list[float]]:
        """Generate perturbed samples around the instance."""
        samples = []
        weights = []
        predictions = []
        
        for _ in range(n_samples):
            perturbed = {}
            distance_sq = 0.0
            
            for name, value in features.items():
                # Add Gaussian noise using seeded RNG for reproducibility
                noise = self._rng.gauss(0, kernel_width * abs(value + 0.1))
                perturbed[name] = value + noise
                distance_sq += noise ** 2
            
            samples.append(perturbed)
            
            # Exponential kernel weight
            weight = math.exp(-distance_sq / (2 * kernel_width ** 2))
            weights.append(weight)
            
            predictions.append(self.model_predict(perturbed))
        
        return samples, weights, predictions
    
    def _fit_local_model(
        self,
        samples: list[dict[str, float]],
        predictions: list[float],
        weights: list[float],
    ) -> dict[str, float]:
        """Fit weighted linear regression."""
        if not samples:
            return {}
        
        feature_names = list(samples[0].keys())
        coefficients = {}
        
        total_weight = sum(weights)
        if total_weight == 0:
            # All weights are zero, return zero coefficients
            return {name: 0.0 for name in feature_names}
        
        # Simple weighted correlation for each feature
        for name in feature_names:
            feature_values = [s[name] for s in samples]
            
            weighted_mean_x = sum(w * x for w, x in zip(weights, feature_values)) / total_weight
            weighted_mean_y = sum(w * y for w, y in zip(weights, predictions)) / total_weight
            
            numerator = sum(
                w * (x - weighted_mean_x) * (y - weighted_mean_y)
                for w, x, y in zip(weights, feature_values, predictions)
            )
            denominator = sum(
                w * (x - weighted_mean_x) ** 2
                for w, x in zip(weights, feature_values)
            )
            
            if denominator > 0:
                coefficients[name] = numerator / denominator
            else:
                coefficients[name] = 0.0
        
        return coefficients


# =============================================================================
# Confidence Interval Calculator
# =============================================================================

class ConfidenceIntervalCalculator:
    """Calculates confidence intervals for predictions."""
    
    # Z-scores for common confidence levels
    Z_SCORES = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    
    def __init__(self, confidence_level: float = DEFAULT_CONFIDENCE_LEVEL):
        """Initialize calculator."""
        self.confidence_level = confidence_level
    
    def calculate(
        self,
        point_estimate: float,
        historical_predictions: list[tuple[float, bool]],
    ) -> ConfidenceInterval:
        """
        Calculate confidence interval.
        
        Args:
            point_estimate: The predicted probability
            historical_predictions: List of (prediction, actual_outcome) tuples
        """
        sample_size = len(historical_predictions)
        
        if sample_size < MIN_SAMPLES_FOR_PREDICTION:
            # Not enough data - use wide interval
            return ConfidenceInterval(
                point_estimate=point_estimate,
                lower_bound=max(0.0, point_estimate - 0.2),
                upper_bound=min(1.0, point_estimate + 0.2),
                confidence_level=self.confidence_level,
                std_error=0.2,
                sample_size=sample_size,
            )
        
        # Calculate prediction errors
        errors = []
        for prediction, actual in historical_predictions:
            actual_value = 1.0 if actual else 0.0
            errors.append(prediction - actual_value)
        
        # Calculate standard error
        mean_error = sum(errors) / len(errors)
        variance = sum((e - mean_error) ** 2 for e in errors) / (len(errors) - 1)
        std_error = math.sqrt(variance / sample_size)
        
        # Get z-score
        z_score = self.Z_SCORES.get(self.confidence_level, 1.96)
        
        # Calculate interval
        margin = z_score * std_error
        lower = max(0.0, point_estimate - margin)
        upper = min(1.0, point_estimate + margin)
        
        return ConfidenceInterval(
            point_estimate=point_estimate,
            lower_bound=lower,
            upper_bound=upper,
            confidence_level=self.confidence_level,
            std_error=std_error,
            sample_size=sample_size,
        )
    
    def calculate_from_volatility(
        self,
        point_estimate: float,
        data_volatility: float,
        sample_size: int,
    ) -> ConfidenceInterval:
        """Calculate interval from data volatility measure."""
        z_score = self.Z_SCORES.get(self.confidence_level, 1.96)
        
        # Adjust volatility based on sample size
        adjusted_volatility = data_volatility / math.sqrt(max(1, sample_size))
        
        margin = z_score * adjusted_volatility
        lower = max(0.0, point_estimate - margin)
        upper = min(1.0, point_estimate + margin)
        
        return ConfidenceInterval(
            point_estimate=point_estimate,
            lower_bound=lower,
            upper_bound=upper,
            confidence_level=self.confidence_level,
            std_error=adjusted_volatility,
            sample_size=sample_size,
        )


# =============================================================================
# Counterfactual Analyzer
# =============================================================================

class CounterfactualAnalyzer:
    """
    Generates counterfactual what-if scenarios.
    
    "What if we lowered the price by 5%?"
    """
    
    COMMON_SCENARIOS = [
        ("price_reduction_5", {"price_competitiveness": 0.05}, "Lower price by 5%"),
        ("price_reduction_10", {"price_competitiveness": 0.10}, "Lower price by 10%"),
        ("faster_delivery", {"days_to_deadline": -5}, "Reduce delivery time by 5 days"),
        ("improved_quality", {"quality_history": 0.1}, "Improve quality score by 10%"),
        ("dedicated_support", {"customer_win_rate": 0.05}, "Provide dedicated support"),
    ]
    
    def __init__(self, model_predict: Callable[[dict[str, float]], float]):
        """Initialize analyzer."""
        self.model_predict = model_predict
    
    def analyze_scenario(
        self,
        original_features: dict[str, float],
        feature_changes: dict[str, float],
        description: str,
    ) -> CounterfactualScenario:
        """Analyze a single counterfactual scenario."""
        scenario_id = hashlib.md5(
            f"{description}:{datetime.now(timezone.utc)}".encode()
        ).hexdigest()[:12]
        
        # Apply changes
        counterfactual_features = original_features.copy()
        for feature, delta in feature_changes.items():
            if feature in counterfactual_features:
                counterfactual_features[feature] += delta
        
        # Get predictions
        original_prediction = self.model_predict(original_features)
        counterfactual_prediction = self.model_predict(counterfactual_features)
        
        prediction_change = counterfactual_prediction - original_prediction
        is_favorable = prediction_change > 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            feature_changes, prediction_change
        )
        
        return CounterfactualScenario(
            scenario_id=scenario_id,
            description=description,
            feature_changes=feature_changes,
            original_prediction=original_prediction,
            counterfactual_prediction=counterfactual_prediction,
            prediction_change=prediction_change,
            is_favorable=is_favorable,
            recommendations=recommendations,
        )
    
    def generate_common_scenarios(
        self,
        features: dict[str, float],
    ) -> list[CounterfactualScenario]:
        """Generate common what-if scenarios."""
        scenarios = []
        
        for scenario_name, changes, description in self.COMMON_SCENARIOS:
            # Only generate if relevant features exist
            if all(f in features for f in changes.keys()):
                scenario = self.analyze_scenario(features, changes, description)
                scenarios.append(scenario)
        
        # Sort by favorable impact
        scenarios.sort(key=lambda s: s.prediction_change, reverse=True)
        
        return scenarios
    
    def find_minimal_change_for_win(
        self,
        features: dict[str, float],
        feature_to_change: str,
        target_probability: float = 0.6,
        max_iterations: int = 20,
    ) -> CounterfactualScenario | None:
        """Find minimal change in a feature to reach target probability."""
        if feature_to_change not in features:
            return None
        
        current_prediction = self.model_predict(features)
        if current_prediction >= target_probability:
            return None  # Already at target
        
        # Binary search for minimal change
        low = 0.0
        high = abs(features[feature_to_change]) * 0.5 + 0.2  # Max 50% change
        
        best_change = None
        
        for _ in range(max_iterations):
            mid = (low + high) / 2
            
            test_features = features.copy()
            test_features[feature_to_change] += mid
            
            test_prediction = self.model_predict(test_features)
            
            if test_prediction >= target_probability:
                best_change = mid
                high = mid
            else:
                low = mid
        
        if best_change is not None:
            return self.analyze_scenario(
                features,
                {feature_to_change: best_change},
                f"Minimal change to {feature_to_change} to reach {target_probability:.0%}",
            )
        
        return None
    
    def _generate_recommendations(
        self,
        feature_changes: dict[str, float],
        prediction_change: float,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if prediction_change > 0.1:
            recommendations.append("High impact change - strongly recommended")
        elif prediction_change > 0.05:
            recommendations.append("Moderate impact - consider implementing")
        elif prediction_change > 0:
            recommendations.append("Small positive impact")
        else:
            recommendations.append("No positive impact expected")
        
        for feature, delta in feature_changes.items():
            if "price" in feature.lower():
                if delta > 0:
                    recommendations.append(f"Review pricing flexibility for {delta*100:.0f}% adjustment")
            elif "timeline" in feature.lower() or "deadline" in feature.lower():
                if delta < 0:
                    recommendations.append("Explore expedited production options")
        
        return recommendations


# =============================================================================
# Win/Loss Prediction Model
# =============================================================================

class WinLossPredictionModel:
    """
    Win/Loss prediction model with explainability.
    
    Uses a simplified logistic-like model for predictions.
    """
    
    # Feature weights (learned from data or predefined)
    DEFAULT_WEIGHTS = {
        "price_competitiveness": 2.5,
        "price_vs_target": 1.5,
        "margin_percentage": -0.5,
        "customer_win_rate": 3.0,
        "customer_lifetime_value": 1.0,
        "previous_orders": 0.8,
        "days_to_deadline": -0.02,
        "response_time_days": -0.3,
        "technical_complexity": -0.5,
        "dfm_score": 1.5,
        "capacity_utilization": -0.8,
        "quality_history": 2.0,
        "competitor_count": -0.4,
    }
    
    def __init__(self):
        """Initialize model."""
        self._weights = self.DEFAULT_WEIGHTS.copy()
        self._intercept = 0.0
        self._trained = False
    
    def predict(self, features: dict[str, float]) -> float:
        """Predict win probability."""
        score = self._intercept
        
        for feature_name, value in features.items():
            weight = self._weights.get(feature_name, 0.0)
            score += weight * value
        
        # Sigmoid activation
        probability = 1 / (1 + math.exp(-score))
        
        return probability
    
    def train(self, historical_data: Union[list[HistoricalRFQ], list[dict[str, Any]]], epochs: int = 10) -> None:
        """Train model on historical data synchronously."""
        # Reconstruct objects if needed
        data = []
        for item in historical_data:
            if isinstance(item, dict):
                data.append(HistoricalRFQ.from_dict(item))
            else:
                data.append(item)
        
        if len(data) < MIN_SAMPLES_FOR_PREDICTION:
            return
        
        learning_rate = 0.01
        
        for _ in range(epochs):
            for rfq in data:
                prediction = self.predict(rfq.features)
                target = 1.0 if rfq.outcome else 0.0
                error = target - prediction
                
                # Gradient update
                for feature_name, value in rfq.features.items():
                    if feature_name not in self._weights:
                        self._weights[feature_name] = 0.0
                    self._weights[feature_name] += learning_rate * error * value
                
                self._intercept += learning_rate * error
        
        self._trained = True

    def train_async(self, historical_data: list[HistoricalRFQ], epochs: int = 10) -> str:
        """Offload training to Celery."""
        from sensei.tasks.ml_tasks import run_model_training
        
        # Serialize data
        serialized_data = [rfq.to_dict() for rfq in historical_data]
        
        task = run_model_training.delay(
            model_name="win_loss_predictor",
            model_class_path="sensei.services.sales.predictive_win_loss.WinLossPredictionModel",
            train_data=serialized_data,
            eval_data=None,
            hyperparameters={"epochs": epochs}
        )
        return task.id
    
    def get_weights(self) -> dict[str, float]:
        """Get current model weights."""
        return self._weights.copy()


# =============================================================================
# Predictive Win/Loss Attribution Engine
# =============================================================================

class PredictiveWinLossEngine:
    """
    Complete predictive win/loss attribution engine.
    
    Combines prediction, explainability, and counterfactual analysis.
    """
    
    def __init__(
        self,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        explainer_type: ExplainerType = ExplainerType.SHAP,
        random_seed: int = 42,
    ):
        """Initialize engine with optional random seed for reproducibility."""
        self.confidence_level = confidence_level
        self.explainer_type = explainer_type
        self._random_seed = random_seed
        
        # Components
        self.model = WinLossPredictionModel()
        self.feature_engineer = FeatureEngineer()
        self.ci_calculator = ConfidenceIntervalCalculator(confidence_level)
        self.counterfactual_analyzer = CounterfactualAnalyzer(self.model.predict)
        
        # Explainers with deterministic seeds for reproducible explanations
        self._shap_explainer = SHAPExplainer(self.model.predict, random_seed=random_seed)
        self._lime_explainer = LIMEExplainer(self.model.predict, random_seed=random_seed)
        
        # Data storage
        self._historical_data: list[HistoricalRFQ] = []
        self._prediction_history: list[tuple[float, bool]] = []
    
    def add_historical_data(self, data: list[HistoricalRFQ], async_train: bool = True) -> None:
        """Add historical RFQ data for training."""
        self._historical_data.extend(data)
        
        # Update feature statistics
        self.feature_engineer.compute_feature_stats(self._historical_data)
        
        # Retrain model
        if async_train:
            self.model.train_async(self._historical_data)
        else:
            self.model.train(self._historical_data)
        
        # Update SHAP baseline
        if self._historical_data:
            baseline_features = {}
            for name in self._historical_data[0].features.keys():
                values = [
                    rfq.features.get(name, 0.0)
                    for rfq in self._historical_data
                ]
                baseline_features[name] = sum(values) / len(values)
            self._shap_explainer.set_baseline(baseline_features)
    
    def record_outcome(self, prediction: float, actual_outcome: bool) -> None:
        """Record actual outcome for a previous prediction."""
        self._prediction_history.append((prediction, actual_outcome))
    
    def predict(
        self,
        rfq_id: str,
        features: dict[str, float],
        generate_counterfactuals: bool = True,
    ) -> PredictionResult:
        """Generate complete prediction with explainability."""
        prediction_id = hashlib.md5(
            f"{rfq_id}:{datetime.now(timezone.utc)}".encode()
        ).hexdigest()[:16]
        
        # Get base prediction
        win_probability = self.model.predict(features)
        
        # Determine outcome
        if win_probability >= 0.6:
            outcome = PredictionOutcome.WIN
        elif win_probability <= 0.4:
            outcome = PredictionOutcome.LOSS
        else:
            outcome = PredictionOutcome.UNCERTAIN
        
        # Calculate confidence interval
        if self._prediction_history:
            confidence_interval = self.ci_calculator.calculate(
                win_probability, self._prediction_history
            )
        else:
            # Use volatility-based interval
            confidence_interval = self.ci_calculator.calculate_from_volatility(
                win_probability,
                data_volatility=0.15,
                sample_size=len(self._historical_data),
            )
        
        # Generate explanations
        if self.explainer_type == ExplainerType.SHAP:
            feature_contributions = self._shap_explainer.explain(
                features, self.feature_engineer
            )
        else:
            feature_contributions = self._lime_explainer.explain(
                features, self.feature_engineer
            )
        
        # Generate counterfactuals
        counterfactual_scenarios = []
        if generate_counterfactuals:
            counterfactual_scenarios = self.counterfactual_analyzer.generate_common_scenarios(
                features
            )
        
        # Calculate data quality score
        data_quality = self._calculate_data_quality(features)
        
        return PredictionResult(
            prediction_id=prediction_id,
            rfq_id=rfq_id,
            timestamp=datetime.now(timezone.utc),
            win_probability=win_probability,
            outcome=outcome,
            confidence_interval=confidence_interval,
            feature_contributions=feature_contributions,
            explainer_type=self.explainer_type,
            counterfactual_scenarios=counterfactual_scenarios,
            data_quality_score=data_quality,
        )
    
    def simulate_price_change(
        self,
        features: dict[str, float],
        price_change_percent: float,
    ) -> CounterfactualScenario:
        """Simulate effect of price change."""
        return self.counterfactual_analyzer.analyze_scenario(
            features,
            {"price_competitiveness": price_change_percent / 100},
            f"Price change of {price_change_percent:+.1f}%",
        )
    
    def find_win_threshold(
        self,
        features: dict[str, float],
        feature_name: str,
        target_probability: float = 0.6,
    ) -> CounterfactualScenario | None:
        """Find the change needed to reach win threshold."""
        return self.counterfactual_analyzer.find_minimal_change_for_win(
            features, feature_name, target_probability
        )
    
    def _calculate_data_quality(self, features: dict[str, float]) -> float:
        """Calculate data quality score."""
        if not features:
            return 0.0
        
        # Check feature completeness
        expected_features = set(FeatureEngineer.FEATURE_DEFINITIONS.keys())
        provided_features = set(features.keys())
        completeness = len(provided_features & expected_features) / len(expected_features)
        
        # Check for missing values (zeros might indicate missing)
        non_zero = sum(1 for v in features.values() if v != 0)
        fill_rate = non_zero / len(features) if features else 0
        
        return (completeness + fill_rate) / 2
    
    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "historical_records": len(self._historical_data),
            "recorded_outcomes": len(self._prediction_history),
            "model_trained": self.model._trained,
            "explainer_type": self.explainer_type.value,
            "confidence_level": self.confidence_level,
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_win_loss_predictor(
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    explainer_type: ExplainerType = ExplainerType.SHAP,
) -> PredictiveWinLossEngine:
    """Create a configured win/loss prediction engine."""
    return PredictiveWinLossEngine(
        confidence_level=confidence_level,
        explainer_type=explainer_type,
    )

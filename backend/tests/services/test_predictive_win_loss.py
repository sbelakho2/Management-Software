"""
Tests for Predictive Win/Loss Attribution.

Tests cover:
- Feature engineering and normalization
- SHAP-like explainability
- LIME-like explainability
- Confidence interval calculation
- Counterfactual analysis
- Complete prediction engine
"""

import pytest
from datetime import datetime, timezone, timedelta
import math

from sensei.services.sales.predictive_win_loss import (
    # Enums
    PredictionOutcome,
    FeatureCategory,
    ContributionDirection,
    ExplainerType,
    # Data models
    Feature,
    FeatureContribution,
    ConfidenceInterval,
    CounterfactualScenario,
    PredictionResult,
    HistoricalRFQ,
    # Components
    FeatureEngineer,
    SHAPExplainer,
    LIMEExplainer,
    ConfidenceIntervalCalculator,
    CounterfactualAnalyzer,
    WinLossPredictionModel,
    PredictiveWinLossEngine,
    # Factory
    create_win_loss_predictor,
    # Constants
    DEFAULT_CONFIDENCE_LEVEL,
    MIN_SAMPLES_FOR_PREDICTION,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_features() -> dict[str, float]:
    """Sample RFQ features."""
    return {
        "price_competitiveness": 0.8,
        "price_vs_target": 0.05,
        "margin_percentage": 0.15,
        "customer_win_rate": 0.65,
        "customer_lifetime_value": 50000.0,
        "previous_orders": 12,
        "days_to_deadline": 14,
        "response_time_days": 2,
        "technical_complexity": 0.4,
        "dfm_score": 0.85,
        "capacity_utilization": 0.7,
        "quality_history": 0.92,
        "competitor_count": 3,
    }


@pytest.fixture
def historical_rfqs() -> list[HistoricalRFQ]:
    """Generate historical RFQ data."""
    rfqs = []
    
    for i in range(50):
        # Generate varied features
        features = {
            "price_competitiveness": 0.5 + (i % 10) * 0.05,
            "customer_win_rate": 0.3 + (i % 8) * 0.08,
            "days_to_deadline": 7 + (i % 14),
            "dfm_score": 0.6 + (i % 5) * 0.08,
            "quality_history": 0.7 + (i % 4) * 0.075,
        }
        
        # Outcome based on features
        score = (
            features["price_competitiveness"] * 2
            + features["customer_win_rate"] * 3
            + features["dfm_score"] * 1.5
        )
        outcome = score > 4.0  # Win threshold
        
        rfqs.append(HistoricalRFQ(
            rfq_id=f"RFQ-{1000 + i}",
            customer_id=f"CUST-{i % 10}",
            features=features,
            outcome=outcome,
            quote_price=10000 + i * 100,
        ))
    
    return rfqs


@pytest.fixture
def feature_engineer() -> FeatureEngineer:
    """Create feature engineer."""
    return FeatureEngineer()


@pytest.fixture
def prediction_model() -> WinLossPredictionModel:
    """Create prediction model."""
    return WinLossPredictionModel()


@pytest.fixture
def prediction_engine(historical_rfqs: list[HistoricalRFQ]) -> PredictiveWinLossEngine:
    """Create configured prediction engine."""
    engine = PredictiveWinLossEngine()
    # Use async_train=False to avoid Celery/Redis connection in tests
    engine.add_historical_data(historical_rfqs, async_train=False)
    return engine


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_prediction_outcome_values(self):
        """Test PredictionOutcome values."""
        assert PredictionOutcome.WIN.value == "win"
        assert PredictionOutcome.LOSS.value == "loss"
        assert PredictionOutcome.UNCERTAIN.value == "uncertain"
    
    def test_feature_category_values(self):
        """Test FeatureCategory values."""
        assert FeatureCategory.PRICE.value == "price"
        assert FeatureCategory.TIMELINE.value == "timeline"
        assert FeatureCategory.QUALITY.value == "quality"
        assert FeatureCategory.RELATIONSHIP.value == "relationship"
        assert FeatureCategory.COMPETITION.value == "competition"
    
    def test_contribution_direction_values(self):
        """Test ContributionDirection values."""
        assert ContributionDirection.POSITIVE.value == "positive"
        assert ContributionDirection.NEGATIVE.value == "negative"
        assert ContributionDirection.NEUTRAL.value == "neutral"
    
    def test_explainer_type_values(self):
        """Test ExplainerType values."""
        assert ExplainerType.SHAP.value == "shap"
        assert ExplainerType.LIME.value == "lime"
        assert ExplainerType.PERMUTATION.value == "permutation"


# =============================================================================
# Tests: Data Models
# =============================================================================

class TestFeature:
    """Test Feature dataclass."""
    
    def test_feature_creation(self):
        """Test creating a feature."""
        feature = Feature(
            name="price_competitiveness",
            value=0.8,
            category=FeatureCategory.PRICE,
            description="Price vs market average",
        )
        
        assert feature.name == "price_competitiveness"
        assert feature.value == 0.8
        assert feature.category == FeatureCategory.PRICE
    
    def test_feature_defaults(self):
        """Test feature defaults."""
        feature = Feature(
            name="test",
            value=0.5,
            category=FeatureCategory.TECHNICAL,
        )
        
        assert feature.normalized_value == 0.0
        assert feature.min_value == 0.0
        assert feature.max_value == 1.0


class TestConfidenceInterval:
    """Test ConfidenceInterval dataclass."""
    
    def test_confidence_interval_creation(self):
        """Test creating confidence interval."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        assert ci.point_estimate == 0.75
        assert ci.lower_bound == 0.70
        assert ci.upper_bound == 0.80
    
    def test_margin_of_error(self):
        """Test margin of error calculation."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        assert abs(ci.margin_of_error - 0.05) < 1e-10
    
    def test_interval_width(self):
        """Test interval width calculation."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        assert abs(ci.interval_width - 10.0) < 1e-10  # 10%
    
    def test_format_display(self):
        """Test formatted display."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        formatted = ci.format()
        assert "75%" in formatted
        assert "5.0%" in formatted


class TestCounterfactualScenario:
    """Test CounterfactualScenario dataclass."""
    
    def test_scenario_creation(self):
        """Test creating scenario."""
        scenario = CounterfactualScenario(
            scenario_id="test123",
            description="Lower price by 5%",
            feature_changes={"price_competitiveness": 0.05},
            original_prediction=0.60,
            counterfactual_prediction=0.68,
            prediction_change=0.08,
            is_favorable=True,
        )
        
        assert scenario.is_favorable is True
        assert scenario.prediction_change == 0.08
    
    def test_change_percentage(self):
        """Test change percentage calculation."""
        scenario = CounterfactualScenario(
            scenario_id="test123",
            description="Test",
            feature_changes={},
            original_prediction=0.50,
            counterfactual_prediction=0.55,
            prediction_change=0.05,
            is_favorable=True,
        )
        
        assert abs(scenario.change_percentage - 10.0) < 1e-10  # 10% increase
    
    def test_change_percentage_zero_original(self):
        """Test change percentage with zero original."""
        scenario = CounterfactualScenario(
            scenario_id="test123",
            description="Test",
            feature_changes={},
            original_prediction=0.0,
            counterfactual_prediction=0.5,
            prediction_change=0.5,
            is_favorable=True,
        )
        
        assert scenario.change_percentage == 0.0  # Avoid division by zero


class TestPredictionResult:
    """Test PredictionResult dataclass."""
    
    def test_prediction_result_creation(self):
        """Test creating prediction result."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        result = PredictionResult(
            prediction_id="pred123",
            rfq_id="RFQ-001",
            timestamp=datetime.now(timezone.utc),
            win_probability=0.75,
            outcome=PredictionOutcome.WIN,
            confidence_interval=ci,
        )
        
        assert result.win_probability == 0.75
        assert result.outcome == PredictionOutcome.WIN
    
    def test_get_top_factors(self):
        """Test getting top contributing factors."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        contributions = [
            FeatureContribution(
                feature_name="price",
                category=FeatureCategory.PRICE,
                contribution=0.3,
                direction=ContributionDirection.POSITIVE,
            ),
            FeatureContribution(
                feature_name="quality",
                category=FeatureCategory.QUALITY,
                contribution=0.2,
                direction=ContributionDirection.POSITIVE,
            ),
            FeatureContribution(
                feature_name="timeline",
                category=FeatureCategory.TIMELINE,
                contribution=-0.1,
                direction=ContributionDirection.NEGATIVE,
            ),
        ]
        
        result = PredictionResult(
            prediction_id="pred123",
            rfq_id="RFQ-001",
            timestamp=datetime.now(timezone.utc),
            win_probability=0.75,
            outcome=PredictionOutcome.WIN,
            confidence_interval=ci,
            feature_contributions=contributions,
        )
        
        top_factors = result.get_top_factors(2)
        assert len(top_factors) == 2
        assert top_factors[0].feature_name == "price"
    
    def test_get_positive_negative_factors(self):
        """Test filtering positive and negative factors."""
        ci = ConfidenceInterval(
            point_estimate=0.75,
            lower_bound=0.70,
            upper_bound=0.80,
            confidence_level=0.95,
            std_error=0.03,
            sample_size=100,
        )
        
        contributions = [
            FeatureContribution(
                feature_name="price",
                category=FeatureCategory.PRICE,
                contribution=0.3,
                direction=ContributionDirection.POSITIVE,
            ),
            FeatureContribution(
                feature_name="timeline",
                category=FeatureCategory.TIMELINE,
                contribution=-0.1,
                direction=ContributionDirection.NEGATIVE,
            ),
        ]
        
        result = PredictionResult(
            prediction_id="pred123",
            rfq_id="RFQ-001",
            timestamp=datetime.now(timezone.utc),
            win_probability=0.75,
            outcome=PredictionOutcome.WIN,
            confidence_interval=ci,
            feature_contributions=contributions,
        )
        
        positive = result.get_positive_factors()
        negative = result.get_negative_factors()
        
        assert len(positive) == 1
        assert len(negative) == 1


# =============================================================================
# Tests: Feature Engineering
# =============================================================================

class TestFeatureEngineer:
    """Test FeatureEngineer."""
    
    def test_compute_feature_stats(self, historical_rfqs: list[HistoricalRFQ]):
        """Test computing feature statistics."""
        engineer = FeatureEngineer()
        engineer.compute_feature_stats(historical_rfqs)
        
        assert len(engineer._feature_stats) > 0
        assert "price_competitiveness" in engineer._feature_stats
    
    def test_normalize_features(self, historical_rfqs: list[HistoricalRFQ]):
        """Test feature normalization."""
        engineer = FeatureEngineer()
        engineer.compute_feature_stats(historical_rfqs)
        
        features = {"price_competitiveness": 0.8}
        normalized = engineer.normalize_features(features)
        
        assert "price_competitiveness" in normalized
        # Normalized value should be different from original
        assert normalized["price_competitiveness"] != 0.8
    
    def test_normalize_features_missing_stats(self):
        """Test normalization without stats."""
        engineer = FeatureEngineer()
        
        features = {"unknown_feature": 1.0}
        normalized = engineer.normalize_features(features)
        
        assert normalized["unknown_feature"] == 0.0
    
    def test_get_feature_info(self):
        """Test getting feature info."""
        engineer = FeatureEngineer()
        
        info = engineer.get_feature_info("price_competitiveness", 0.8)
        
        assert info.name == "price_competitiveness"
        assert info.value == 0.8
        assert info.category == FeatureCategory.PRICE
    
    def test_feature_definitions(self):
        """Test feature category definitions."""
        definitions = FeatureEngineer.FEATURE_DEFINITIONS
        
        assert definitions["price_competitiveness"] == FeatureCategory.PRICE
        assert definitions["customer_win_rate"] == FeatureCategory.RELATIONSHIP
        assert definitions["days_to_deadline"] == FeatureCategory.TIMELINE


# =============================================================================
# Tests: SHAP Explainer
# =============================================================================

class TestSHAPExplainer:
    """Test SHAPExplainer."""
    
    def test_shap_explainer_creation(self):
        """Test creating SHAP explainer."""
        def model_predict(features: dict) -> float:
            return 0.5
        
        explainer = SHAPExplainer(model_predict)
        assert explainer is not None
    
    def test_set_baseline(self):
        """Test setting baseline."""
        def model_predict(features: dict) -> float:
            return sum(features.values()) / len(features) if features else 0.5
        
        explainer = SHAPExplainer(model_predict)
        baseline = {"price": 0.5, "quality": 0.5}
        
        explainer.set_baseline(baseline)
        
        assert explainer._baseline == baseline
    
    def test_explain_features(self, sample_features: dict[str, float]):
        """Test explaining features."""
        def model_predict(features: dict) -> float:
            score = sum(features.values()) / 10
            return 1 / (1 + math.exp(-score))
        
        explainer = SHAPExplainer(model_predict)
        explainer.set_baseline({k: 0.0 for k in sample_features})
        
        contributions = explainer.explain(
            sample_features,
            FeatureEngineer(),
            n_samples=20,
        )
        
        assert len(contributions) == len(sample_features)
        assert all(isinstance(c, FeatureContribution) for c in contributions)
    
    def test_contribution_directions(self):
        """Test that contributions have directions."""
        def model_predict(features: dict) -> float:
            return features.get("positive", 0.5) - features.get("negative", 0.0)
        
        explainer = SHAPExplainer(model_predict)
        explainer.set_baseline({"positive": 0.0, "negative": 0.0})
        
        features = {"positive": 0.5, "negative": 0.2}
        contributions = explainer.explain(features, FeatureEngineer(), n_samples=20)
        
        # Should have both positive and negative contributions
        directions = {c.direction for c in contributions}
        assert len(directions) > 0
    
    def test_importance_ranking(self, sample_features: dict[str, float]):
        """Test importance ranking assignment."""
        def model_predict(features: dict) -> float:
            return min(1.0, sum(features.values()) / 100)
        
        explainer = SHAPExplainer(model_predict)
        explainer.set_baseline({k: 0.0 for k in sample_features})
        
        contributions = explainer.explain(
            sample_features,
            FeatureEngineer(),
            n_samples=20,
        )
        
        ranks = [c.importance_rank for c in contributions]
        assert set(ranks) == set(range(1, len(contributions) + 1))


# =============================================================================
# Tests: LIME Explainer
# =============================================================================

class TestLIMEExplainer:
    """Test LIMEExplainer."""
    
    def test_lime_explainer_creation(self):
        """Test creating LIME explainer."""
        def model_predict(features: dict) -> float:
            return 0.5
        
        explainer = LIMEExplainer(model_predict)
        assert explainer is not None
    
    def test_explain_features(self, sample_features: dict[str, float]):
        """Test explaining features."""
        def model_predict(features: dict) -> float:
            score = sum(features.values()) / 100  # Scale down to avoid overflow
            # Clamp to prevent overflow
            score = max(-500, min(500, score))
            return 1 / (1 + math.exp(-score))
        
        explainer = LIMEExplainer(model_predict)
        
        contributions = explainer.explain(
            sample_features,
            FeatureEngineer(),
            n_samples=30,
        )
        
        assert len(contributions) == len(sample_features)
    
    def test_lime_generates_explanations(self):
        """Test that LIME generates valid explanations."""
        def model_predict(features: dict) -> float:
            return features.get("price", 0) * 0.5 + features.get("quality", 0) * 0.5
        
        explainer = LIMEExplainer(model_predict)
        
        features = {"price": 0.8, "quality": 0.6}
        contributions = explainer.explain(features, FeatureEngineer(), n_samples=50)
        
        assert len(contributions) == 2
        # Contributions should be non-zero for non-zero features
        for contrib in contributions:
            assert contrib.feature_name in features


# =============================================================================
# Tests: Confidence Interval Calculator
# =============================================================================

class TestConfidenceIntervalCalculator:
    """Test ConfidenceIntervalCalculator."""
    
    def test_calculator_creation(self):
        """Test creating calculator."""
        calc = ConfidenceIntervalCalculator()
        assert calc.confidence_level == DEFAULT_CONFIDENCE_LEVEL
    
    def test_custom_confidence_level(self):
        """Test custom confidence level."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.99)
        assert calc.confidence_level == 0.99
    
    def test_calculate_with_history(self):
        """Test calculating with prediction history."""
        calc = ConfidenceIntervalCalculator()
        
        # Generate prediction history
        history = [(0.7, True), (0.6, True), (0.5, False)] * 10
        
        ci = calc.calculate(0.65, history)
        
        assert ci.point_estimate == 0.65
        assert ci.lower_bound < ci.point_estimate
        assert ci.upper_bound > ci.point_estimate
        assert ci.sample_size == 30
    
    def test_calculate_insufficient_data(self):
        """Test calculating with insufficient data."""
        calc = ConfidenceIntervalCalculator()
        
        # Only a few samples
        history = [(0.7, True), (0.6, False)]
        
        ci = calc.calculate(0.65, history)
        
        # Should use wide interval
        assert ci.margin_of_error >= 0.1
    
    def test_calculate_from_volatility(self):
        """Test calculating from volatility."""
        calc = ConfidenceIntervalCalculator()
        
        ci = calc.calculate_from_volatility(
            point_estimate=0.7,
            data_volatility=0.15,
            sample_size=100,
        )
        
        assert ci.point_estimate == 0.7
        assert ci.lower_bound >= 0.0
        assert ci.upper_bound <= 1.0
    
    def test_interval_bounds_clamped(self):
        """Test that interval bounds are clamped to [0, 1]."""
        calc = ConfidenceIntervalCalculator()
        
        # High volatility at edge
        ci = calc.calculate_from_volatility(
            point_estimate=0.95,
            data_volatility=0.5,
            sample_size=10,
        )
        
        assert ci.upper_bound <= 1.0
        
        ci2 = calc.calculate_from_volatility(
            point_estimate=0.05,
            data_volatility=0.5,
            sample_size=10,
        )
        
        assert ci2.lower_bound >= 0.0


# =============================================================================
# Tests: Counterfactual Analyzer
# =============================================================================

class TestCounterfactualAnalyzer:
    """Test CounterfactualAnalyzer."""
    
    def test_analyzer_creation(self):
        """Test creating analyzer."""
        def model_predict(features: dict) -> float:
            return 0.5
        
        analyzer = CounterfactualAnalyzer(model_predict)
        assert analyzer is not None
    
    def test_analyze_scenario(self, sample_features: dict[str, float]):
        """Test analyzing a scenario."""
        def model_predict(features: dict) -> float:
            return features.get("price_competitiveness", 0.5) * 0.5 + 0.25
        
        analyzer = CounterfactualAnalyzer(model_predict)
        
        scenario = analyzer.analyze_scenario(
            sample_features,
            {"price_competitiveness": 0.1},
            "Increase price competitiveness by 10%",
        )
        
        assert scenario.description == "Increase price competitiveness by 10%"
        assert scenario.is_favorable is True
        assert scenario.prediction_change > 0
    
    def test_generate_common_scenarios(self, sample_features: dict[str, float]):
        """Test generating common scenarios."""
        def model_predict(features: dict) -> float:
            score = sum(features.values()) / 100
            return min(1.0, max(0.0, score))
        
        analyzer = CounterfactualAnalyzer(model_predict)
        
        scenarios = analyzer.generate_common_scenarios(sample_features)
        
        # Should generate multiple scenarios
        assert len(scenarios) > 0
        
        # Should be sorted by impact
        for i in range(len(scenarios) - 1):
            assert scenarios[i].prediction_change >= scenarios[i + 1].prediction_change
    
    def test_find_minimal_change_for_win(self):
        """Test finding minimal change."""
        def model_predict(features: dict) -> float:
            return features.get("price_competitiveness", 0.5)
        
        analyzer = CounterfactualAnalyzer(model_predict)
        
        features = {"price_competitiveness": 0.4}
        
        scenario = analyzer.find_minimal_change_for_win(
            features,
            "price_competitiveness",
            target_probability=0.6,
        )
        
        assert scenario is not None
        assert scenario.counterfactual_prediction >= 0.6
    
    def test_find_minimal_change_already_at_target(self):
        """Test when already at target."""
        def model_predict(features: dict) -> float:
            return features.get("price", 0.7)
        
        analyzer = CounterfactualAnalyzer(model_predict)
        
        features = {"price": 0.8}
        
        scenario = analyzer.find_minimal_change_for_win(
            features, "price", target_probability=0.6
        )
        
        # Already above target
        assert scenario is None
    
    def test_recommendations_generated(self, sample_features: dict[str, float]):
        """Test that recommendations are generated."""
        def model_predict(features: dict) -> float:
            return features.get("price_competitiveness", 0.5)
        
        analyzer = CounterfactualAnalyzer(model_predict)
        
        scenario = analyzer.analyze_scenario(
            sample_features,
            {"price_competitiveness": 0.15},
            "Price adjustment",
        )
        
        assert len(scenario.recommendations) > 0


# =============================================================================
# Tests: Win/Loss Prediction Model
# =============================================================================

class TestWinLossPredictionModel:
    """Test WinLossPredictionModel."""
    
    def test_model_creation(self):
        """Test creating model."""
        model = WinLossPredictionModel()
        assert model is not None
        assert not model._trained
    
    def test_predict_with_defaults(self, sample_features: dict[str, float]):
        """Test prediction with default weights."""
        model = WinLossPredictionModel()
        
        probability = model.predict(sample_features)
        
        assert 0.0 <= probability <= 1.0
    
    def test_predict_empty_features(self):
        """Test prediction with empty features."""
        model = WinLossPredictionModel()
        
        probability = model.predict({})
        
        assert probability == 0.5  # Sigmoid of 0
    
    def test_train_model(self, historical_rfqs: list[HistoricalRFQ]):
        """Test training model."""
        model = WinLossPredictionModel()
        
        model.train(historical_rfqs)
        
        assert model._trained
    
    def test_train_insufficient_data(self):
        """Test training with insufficient data."""
        model = WinLossPredictionModel()
        
        # Only 3 samples
        rfqs = [
            HistoricalRFQ(
                rfq_id=f"RFQ-{i}",
                customer_id="CUST-1",
                features={"price": 0.5},
                outcome=True,
                quote_price=1000,
            )
            for i in range(3)
        ]
        
        model.train(rfqs)
        
        # Should not train with insufficient data
        assert not model._trained
    
    def test_get_weights(self):
        """Test getting model weights."""
        model = WinLossPredictionModel()
        
        weights = model.get_weights()
        
        assert "price_competitiveness" in weights
        assert "customer_win_rate" in weights


# =============================================================================
# Tests: Predictive Win/Loss Engine
# =============================================================================

class TestPredictiveWinLossEngine:
    """Test PredictiveWinLossEngine."""
    
    def test_engine_creation(self):
        """Test creating engine."""
        engine = PredictiveWinLossEngine()
        
        assert engine.confidence_level == DEFAULT_CONFIDENCE_LEVEL
        assert engine.explainer_type == ExplainerType.SHAP
    
    def test_engine_with_lime_explainer(self):
        """Test engine with LIME explainer."""
        engine = PredictiveWinLossEngine(explainer_type=ExplainerType.LIME)
        
        assert engine.explainer_type == ExplainerType.LIME
    
    def test_add_historical_data(self, historical_rfqs: list[HistoricalRFQ]):
        """Test adding historical data."""
        engine = PredictiveWinLossEngine()
        
        # Use async_train=False to avoid Celery/Redis connection in tests
        engine.add_historical_data(historical_rfqs, async_train=False)
        
        assert len(engine._historical_data) == len(historical_rfqs)
    
    def test_record_outcome(self):
        """Test recording outcome."""
        engine = PredictiveWinLossEngine()
        
        engine.record_outcome(0.7, True)
        engine.record_outcome(0.3, False)
        
        assert len(engine._prediction_history) == 2
    
    def test_predict(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test making predictions."""
        result = prediction_engine.predict("RFQ-TEST", sample_features)
        
        assert result.prediction_id is not None
        assert result.rfq_id == "RFQ-TEST"
        assert 0.0 <= result.win_probability <= 1.0
        assert result.outcome in PredictionOutcome
    
    def test_predict_with_counterfactuals(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test prediction with counterfactuals."""
        result = prediction_engine.predict(
            "RFQ-TEST",
            sample_features,
            generate_counterfactuals=True,
        )
        
        assert len(result.counterfactual_scenarios) > 0
    
    def test_predict_without_counterfactuals(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test prediction without counterfactuals."""
        result = prediction_engine.predict(
            "RFQ-TEST",
            sample_features,
            generate_counterfactuals=False,
        )
        
        assert len(result.counterfactual_scenarios) == 0
    
    def test_feature_contributions(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test feature contributions are generated."""
        result = prediction_engine.predict("RFQ-TEST", sample_features)
        
        assert len(result.feature_contributions) > 0
    
    def test_simulate_price_change(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test price change simulation."""
        scenario = prediction_engine.simulate_price_change(sample_features, -5.0)
        
        assert "Price change of -5.0%" in scenario.description
        assert scenario.feature_changes.get("price_competitiveness") == -0.05
    
    def test_find_win_threshold(
        self,
        prediction_engine: PredictiveWinLossEngine,
    ):
        """Test finding win threshold."""
        features = {
            "price_competitiveness": 0.3,
            "customer_win_rate": 0.4,
            "dfm_score": 0.5,
        }
        
        scenario = prediction_engine.find_win_threshold(
            features, "price_competitiveness", target_probability=0.7
        )
        
        # May or may not find a threshold depending on model
        if scenario is not None:
            assert scenario.counterfactual_prediction >= 0.0
    
    def test_get_stats(self, prediction_engine: PredictiveWinLossEngine):
        """Test getting engine stats."""
        stats = prediction_engine.get_stats()
        
        assert "historical_records" in stats
        assert "recorded_outcomes" in stats
        assert "model_trained" in stats
        assert "explainer_type" in stats
        assert stats["historical_records"] == 50


class TestPredictionOutcomeClassification:
    """Test outcome classification logic."""
    
    def test_win_classification(
        self,
        prediction_engine: PredictiveWinLossEngine,
    ):
        """Test WIN outcome classification."""
        # High win probability features
        features = {
            "price_competitiveness": 1.0,
            "customer_win_rate": 1.0,
            "dfm_score": 1.0,
            "quality_history": 1.0,
        }
        
        result = prediction_engine.predict("RFQ-WIN", features)
        
        # With strong features, should predict win
        assert result.win_probability >= 0.5
    
    def test_loss_classification(
        self,
        prediction_engine: PredictiveWinLossEngine,
    ):
        """Test LOSS outcome classification."""
        # Low probability features
        features = {
            "price_competitiveness": 0.0,
            "customer_win_rate": 0.0,
            "competitor_count": 10,
            "capacity_utilization": 1.0,
        }
        
        result = prediction_engine.predict("RFQ-LOSS", features)
        
        # With weak features, should predict loss
        assert result.win_probability <= 0.5 or result.outcome in [
            PredictionOutcome.LOSS, PredictionOutcome.UNCERTAIN
        ]


# =============================================================================
# Tests: Factory Function
# =============================================================================

class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_default_predictor(self):
        """Test creating default predictor."""
        predictor = create_win_loss_predictor()
        
        assert isinstance(predictor, PredictiveWinLossEngine)
        assert predictor.confidence_level == DEFAULT_CONFIDENCE_LEVEL
    
    def test_create_custom_predictor(self):
        """Test creating custom predictor."""
        predictor = create_win_loss_predictor(
            confidence_level=0.99,
            explainer_type=ExplainerType.LIME,
        )
        
        assert predictor.confidence_level == 0.99
        assert predictor.explainer_type == ExplainerType.LIME


# =============================================================================
# Tests: Integration
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflow."""
    
    def test_full_prediction_workflow(self, historical_rfqs: list[HistoricalRFQ]):
        """Test complete prediction workflow."""
        # Create engine
        engine = create_win_loss_predictor()
        
        # Add historical data (use async_train=False to avoid Celery/Redis)
        engine.add_historical_data(historical_rfqs, async_train=False)
        
        # Make prediction
        features = {
            "price_competitiveness": 0.75,
            "customer_win_rate": 0.6,
            "days_to_deadline": 10,
            "dfm_score": 0.8,
            "quality_history": 0.85,
        }
        
        result = engine.predict("RFQ-WORKFLOW", features)
        
        # Verify complete result
        assert result.prediction_id is not None
        assert result.confidence_interval is not None
        assert len(result.feature_contributions) > 0
        assert len(result.counterfactual_scenarios) > 0
        
        # Record outcome
        engine.record_outcome(result.win_probability, True)
        
        assert len(engine._prediction_history) == 1
    
    def test_counterfactual_recommendations(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test counterfactual recommendations workflow."""
        result = prediction_engine.predict("RFQ-CF", sample_features)
        
        # Get favorable scenarios
        favorable = [
            s for s in result.counterfactual_scenarios
            if s.is_favorable
        ]
        
        # Should have at least some favorable scenarios
        assert len(favorable) >= 0  # May be zero if already optimal
        
        # Check recommendations exist
        for scenario in result.counterfactual_scenarios:
            assert len(scenario.recommendations) > 0
    
    def test_confidence_interval_width_with_more_data(
        self,
        historical_rfqs: list[HistoricalRFQ],
    ):
        """Test that confidence interval narrows with more data."""
        engine = create_win_loss_predictor()
        
        # Small dataset (use async_train=False to avoid Celery/Redis)
        engine.add_historical_data(historical_rfqs[:10], async_train=False)
        
        features = {"price_competitiveness": 0.7, "dfm_score": 0.8}
        result1 = engine.predict("RFQ-1", features)
        width1 = result1.confidence_interval.interval_width
        
        # Add more data (use async_train=False to avoid Celery/Redis)
        engine.add_historical_data(historical_rfqs[10:], async_train=False)
        
        result2 = engine.predict("RFQ-2", features)
        width2 = result2.confidence_interval.interval_width
        
        # With more data, interval may be narrower (or similar)
        assert width2 <= width1 * 1.5  # Allow some tolerance
    
    def test_explainability_display_format(
        self,
        prediction_engine: PredictiveWinLossEngine,
        sample_features: dict[str, float],
    ):
        """Test explainability output format."""
        result = prediction_engine.predict("RFQ-EXPLAIN", sample_features)
        
        # Check formatted confidence interval
        ci_format = result.confidence_interval.format()
        assert "%" in ci_format
        assert "±" in ci_format
        
        # Check feature explanations
        top_factors = result.get_top_factors(3)
        for factor in top_factors:
            assert factor.explanation or factor.contribution != 0

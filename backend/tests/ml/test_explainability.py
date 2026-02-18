"""
Tests for ML Explainability module (SHAP/LIME).

Tests cover:
- SHAP local explanations
- SHAP global explanations
- LIME local explanations
- Counterfactual explanations
- Feature importance
- Explanation comparison
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Import the module components
from sensei.ml.explainability import (
    check_explainability_availability,
    CBM_FEATURE_NAMES,
    FeatureContribution,
    LocalExplanation,
    GlobalExplanation,
    CounterfactualExplanation,
    ExplanationType,
    ModelType,
    HAS_SHAP,
    HAS_LIME,
)


class TestExplainabilityAvailability:
    """Test explainability library availability checks."""
    
    def test_check_availability_returns_dict(self):
        """Check availability returns a dictionary with required keys."""
        result = check_explainability_availability()
        
        assert isinstance(result, dict)
        assert "shap" in result
        assert "lime" in result
        assert "sklearn" in result
        assert all(isinstance(v, bool) for v in result.values())


class TestFeatureContribution:
    """Test FeatureContribution dataclass."""
    
    def test_feature_contribution_creation(self):
        """Test creating a feature contribution."""
        fc = FeatureContribution(
            feature_name="temperature",
            feature_value=75.0,
            contribution=0.15,
            contribution_abs=0.15,
            direction="positive",
            percentile_rank=0.8,
        )
        
        assert fc.feature_name == "temperature"
        assert fc.feature_value == 75.0
        assert fc.contribution == 0.15
        assert fc.direction == "positive"
    
    def test_feature_contribution_to_dict(self):
        """Test serialization to dictionary."""
        fc = FeatureContribution(
            feature_name="vibration",
            feature_value=8.5,
            contribution=-0.1,
            contribution_abs=0.1,
            direction="negative",
        )
        
        result = fc.to_dict()
        
        assert result["feature_name"] == "vibration"
        assert result["feature_value"] == 8.5
        assert result["contribution"] == -0.1
        assert result["direction"] == "negative"


class TestLocalExplanation:
    """Test LocalExplanation dataclass."""
    
    def test_local_explanation_creation(self):
        """Test creating a local explanation."""
        contributions = [
            FeatureContribution(
                feature_name="temperature",
                feature_value=70.0,
                contribution=0.2,
                contribution_abs=0.2,
                direction="positive",
            ),
        ]
        
        explanation = LocalExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            explanation_type=ExplanationType.SHAP_LOCAL,
            timestamp=None,  # type: ignore
            input_features={"temperature": 70.0},
            predicted_class=1,
            predicted_probability=0.75,
            base_value=0.5,
            feature_contributions=contributions,
            top_positive_features=["temperature"],
            top_negative_features=[],
            natural_language_explanation="High temperature increases risk.",
        )
        
        assert explanation.model_name == "cbm_predictor"
        assert explanation.predicted_class == 1
        assert len(explanation.feature_contributions) == 1
    
    def test_local_explanation_to_dict(self):
        """Test serialization to dictionary."""
        from datetime import datetime, timezone
        
        explanation = LocalExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            explanation_type=ExplanationType.LIME_LOCAL,
            timestamp=datetime.now(timezone.utc),
            input_features={"temperature": 65.0},
            predicted_class=0,
            predicted_probability=0.3,
            base_value=0.5,
            feature_contributions=[],
            top_positive_features=[],
            top_negative_features=[],
            natural_language_explanation="Low risk prediction.",
        )
        
        result = explanation.to_dict()
        
        assert "explanation_id" in result
        assert result["model_name"] == "cbm_predictor"
        assert result["explanation_type"] == "lime_local"
        assert result["predicted_probability"] == 0.3


class TestCBMFeatureNames:
    """Test CBM feature name constants."""
    
    def test_feature_names_count(self):
        """Verify expected number of features."""
        assert len(CBM_FEATURE_NAMES) == 18
    
    def test_required_features_present(self):
        """Check required feature names are present."""
        required = [
            "temperature",
            "vibration",
            "pressure",
            "operating_hours",
            "days_since_maintenance",
        ]
        for f in required:
            assert f in CBM_FEATURE_NAMES


class TestModelTypeEnum:
    """Test ModelType enumeration."""
    
    def test_model_types(self):
        """Verify model type values."""
        assert ModelType.TREE_ENSEMBLE.value == "tree_ensemble"
        assert ModelType.LINEAR.value == "linear"
        assert ModelType.GENERIC.value == "generic"


@pytest.mark.skipif(not HAS_SHAP, reason="SHAP not installed")
class TestSHAPExplainer:
    """Test SHAP explainer functionality."""
    
    def test_shap_explainer_creation(self):
        """Test creating SHAP explainer with mock model."""
        from sklearn.ensemble import RandomForestClassifier
        from sensei.ml.explainability import SHAPExplainer
        
        # Create a simple trained model
        X = np.random.rand(100, 18)
        y = (X[:, 0] > 0.5).astype(int)
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        explainer = SHAPExplainer(
            model=model,
            feature_names=CBM_FEATURE_NAMES,
            model_type=ModelType.TREE_ENSEMBLE,
            background_data=X[:50],
        )
        
        assert explainer is not None
        assert explainer.feature_names == CBM_FEATURE_NAMES
    
    def test_shap_local_explanation(self):
        """Test generating local SHAP explanation."""
        from sklearn.ensemble import RandomForestClassifier
        from sensei.ml.explainability import SHAPExplainer
        
        X = np.random.rand(100, 18)
        y = (X[:, 0] > 0.5).astype(int)
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        explainer = SHAPExplainer(
            model=model,
            feature_names=CBM_FEATURE_NAMES,
            model_type=ModelType.TREE_ENSEMBLE,
            background_data=X[:50],
        )
        
        # Generate explanation for a single sample
        explanation = explainer.explain_prediction(X[0])
        
        assert isinstance(explanation, LocalExplanation)
        assert explanation.explanation_type == ExplanationType.SHAP_LOCAL
        assert len(explanation.feature_contributions) == 18
        assert explanation.natural_language_explanation != ""


@pytest.mark.skipif(not HAS_LIME, reason="LIME not installed")
class TestLIMEExplainer:
    """Test LIME explainer functionality."""
    
    def test_lime_explainer_creation(self):
        """Test creating LIME explainer with mock model."""
        from sklearn.ensemble import RandomForestClassifier
        from sensei.ml.explainability import LIMEExplainer
        
        X = np.random.rand(100, 18)
        y = (X[:, 0] > 0.5).astype(int)
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        explainer = LIMEExplainer(
            model=model,
            feature_names=CBM_FEATURE_NAMES,
            training_data=X,
        )
        
        assert explainer is not None
        assert explainer.feature_names == CBM_FEATURE_NAMES


class TestModelExplainabilityService:
    """Test unified explainability service."""
    
    def test_get_feature_importance_from_tree_model(self):
        """Test extracting feature importance from tree model."""
        from sklearn.ensemble import RandomForestClassifier
        from sensei.ml.explainability import ModelExplainabilityService, ModelType
        
        X = np.random.rand(100, 18)
        y = (X[:, 0] > 0.5).astype(int)
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        service = ModelExplainabilityService(
            model=model,
            feature_names=CBM_FEATURE_NAMES,
            model_type=ModelType.TREE_ENSEMBLE,
        )
        
        importance = service.get_feature_importance()
        
        assert isinstance(importance, dict)
        assert len(importance) == 18
        assert all(isinstance(v, float) for v in importance.values())
    
    def test_counterfactual_already_desired_class(self):
        """Test counterfactual when already at desired class."""
        from sklearn.ensemble import RandomForestClassifier
        from sensei.ml.explainability import ModelExplainabilityService, ModelType
        
        X = np.random.rand(100, 18)
        y = np.zeros(100, dtype=int)  # All class 0
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        service = ModelExplainabilityService(
            model=model,
            feature_names=CBM_FEATURE_NAMES,
            model_type=ModelType.TREE_ENSEMBLE,
        )
        
        # Input that predicts class 0
        cf = service.generate_counterfactual(X[0], desired_class=0)
        
        assert cf.num_features_changed == 0
        assert "No changes needed" in cf.natural_language_explanation


class TestCBMPredictorExplainability:
    """Test CBM predictor explainability integration."""
    
    def test_explainability_status(self):
        """Test checking explainability status."""
        from sensei.ml.cbm_predictor import ConditionBasedMaintenancePredictor
        
        status = ConditionBasedMaintenancePredictor.get_explainability_status()
        
        assert isinstance(status, dict)
        assert "explainability_available" in status
        assert "shap_available" in status
        assert "lime_available" in status
    
    def test_feature_names_defined(self):
        """Test that feature names are defined in predictor."""
        from sensei.ml.cbm_predictor import ConditionBasedMaintenancePredictor
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = ConditionBasedMaintenancePredictor(model_path=Path(tmpdir))
            
            assert hasattr(predictor, 'feature_names')
            assert len(predictor.feature_names) == 18
            assert "temperature" in predictor.feature_names


class TestCounterfactualExplanation:
    """Test CounterfactualExplanation dataclass."""
    
    def test_counterfactual_creation(self):
        """Test creating a counterfactual explanation."""
        cf = CounterfactualExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            timestamp=None,  # type: ignore
            original_input={"temperature": 80.0},
            original_prediction=1,
            original_probability=0.9,
            counterfactual_input={"temperature": 50.0},
            counterfactual_prediction=0,
            counterfactual_probability=0.2,
            feature_changes=[
                {"feature": "temperature", "original_value": 80.0, "changed_value": 50.0, "delta": -30.0}
            ],
            num_features_changed=1,
            total_change_magnitude=30.0,
            natural_language_explanation="Reduce temperature to lower risk.",
        )
        
        assert cf.num_features_changed == 1
        assert cf.total_change_magnitude == 30.0
    
    def test_counterfactual_to_dict(self):
        """Test serialization to dictionary."""
        from datetime import datetime, timezone
        
        cf = CounterfactualExplanation(
            explanation_id=uuid4(),
            model_name="cbm_predictor",
            timestamp=datetime.now(timezone.utc),
            original_input={"vibration": 9.0},
            original_prediction=1,
            original_probability=0.85,
            counterfactual_input={"vibration": 4.0},
            counterfactual_prediction=0,
            counterfactual_probability=0.25,
            feature_changes=[
                {"feature": "vibration", "original_value": 9.0, "changed_value": 4.0, "delta": -5.0}
            ],
            num_features_changed=1,
            total_change_magnitude=5.0,
            natural_language_explanation="Reduce vibration.",
        )
        
        result = cf.to_dict()
        
        assert "feature_changes" in result
        assert len(result["feature_changes"]) == 1
        assert result["num_features_changed"] == 1

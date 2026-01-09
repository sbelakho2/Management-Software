"""
Tests for ML Model Evaluation Framework

Tests:
- EvaluationResults data structure
- ModelEvaluator classifier evaluation
- Regression evaluation
- Calibration analysis
- Fairness metrics
- Business metrics
- Model comparison
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path

from sensei.ml.evaluation import ModelEvaluator, EvaluationResults


# =============================================================================
# Test: EvaluationResults Data Structure
# =============================================================================

class TestEvaluationResults:
    """Test EvaluationResults dataclass."""
    
    def test_create_evaluation_results(self):
        """Test creating EvaluationResults instance."""
        results = EvaluationResults(
            accuracy=0.85,
            precision=0.82,
            recall=0.78,
            f1_score=0.80,
            roc_auc=0.87,
            confusion_matrix=np.array([[80, 20], [15, 85]]),
            classification_report="test report",
            calibration_score=0.08,
            fairness_metrics={'demographic_parity': 0.05},
            business_metrics={'net_benefit': 1000},
            feature_importance={'feature1': 0.5},
        )
        
        assert results.accuracy == 0.85
        assert results.precision == 0.82
        assert results.recall == 0.78
        assert results.f1_score == 0.80
        assert results.roc_auc == 0.87
    
    def test_to_dict(self):
        """Test converting EvaluationResults to dictionary."""
        results = EvaluationResults(
            accuracy=0.85,
            precision=0.82,
            recall=0.78,
            f1_score=0.80,
            roc_auc=0.87,
            confusion_matrix=np.array([[80, 20], [15, 85]]),
            classification_report="test report",
            calibration_score=0.08,
            fairness_metrics={'demographic_parity': 0.05},
            business_metrics={'net_benefit': 1000},
            feature_importance={'feature1': 0.5},
        )
        
        result_dict = results.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['accuracy'] == 0.85
        assert result_dict['precision'] == 0.82
        assert result_dict['confusion_matrix'] == [[80, 20], [15, 85]]
    
    def test_results_with_none_values(self):
        """Test results with optional None values."""
        results = EvaluationResults(
            accuracy=0.85,
            precision=0.82,
            recall=0.78,
            f1_score=0.80,
            roc_auc=None,
            confusion_matrix=np.array([[80, 20], [15, 85]]),
            classification_report="test report",
            calibration_score=None,
            fairness_metrics={},
            business_metrics={},
            feature_importance=None,
        )
        
        assert results.roc_auc is None
        assert results.calibration_score is None
        assert results.feature_importance is None


# =============================================================================
# Test: ModelEvaluator Initialization
# =============================================================================

class TestModelEvaluatorInit:
    """Test ModelEvaluator initialization."""
    
    def test_init(self):
        """Test creating ModelEvaluator."""
        evaluator = ModelEvaluator()
        assert evaluator is not None


# =============================================================================
# Test: Classifier Evaluation
# =============================================================================

class TestClassifierEvaluation:
    """Test classifier evaluation functionality."""
    
    @pytest.fixture
    def sample_classification_data(self):
        """Create sample classification data."""
        np.random.seed(42)
        # Binary classification with 85% accuracy
        y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 20)
        y_pred = y_true.copy()
        # Introduce some errors
        y_pred[0:5] = 1  # 5 false positives
        y_pred[100:105] = 0  # 5 false negatives
        
        return y_true, y_pred
    
    @pytest.fixture
    def sample_probabilities(self, sample_classification_data):
        """Create sample prediction probabilities."""
        y_true, y_pred = sample_classification_data
        # Create probability array
        proba = np.zeros((len(y_pred), 2))
        proba[:, 1] = y_pred * 0.9 + 0.05  # High prob for positive class
        proba[:, 0] = 1 - proba[:, 1]
        return proba
    
    def test_evaluate_classifier_basic(self, sample_classification_data):
        """Test basic classifier evaluation."""
        evaluator = ModelEvaluator()
        y_true, y_pred = sample_classification_data
        
        results = evaluator.evaluate_classifier(y_true, y_pred)
        
        assert results.accuracy > 0
        assert results.precision > 0
        assert results.recall > 0
        assert results.f1_score > 0
        assert results.confusion_matrix is not None
        assert results.classification_report is not None
    
    def test_evaluate_classifier_with_probabilities(
        self, sample_classification_data, sample_probabilities
    ):
        """Test classifier evaluation with probabilities."""
        evaluator = ModelEvaluator()
        y_true, y_pred = sample_classification_data
        
        results = evaluator.evaluate_classifier(
            y_true, y_pred, y_pred_proba=sample_probabilities
        )
        
        assert results.roc_auc is not None
        assert results.calibration_score is not None
        assert 0 <= results.roc_auc <= 1
        assert 0 <= results.calibration_score <= 1
    
    def test_evaluate_classifier_with_protected_attributes(
        self, sample_classification_data
    ):
        """Test classifier evaluation with fairness analysis."""
        evaluator = ModelEvaluator()
        y_true, y_pred = sample_classification_data
        
        # Create protected attribute
        protected = np.array([0, 1] * 100)  # Binary attribute
        
        results = evaluator.evaluate_classifier(
            y_true, y_pred,
            protected_attributes={'gender': protected}
        )
        
        assert 'gender_demographic_parity' in results.fairness_metrics
        assert 'gender_fpr_difference' in results.fairness_metrics
        assert 'gender_tpr_difference' in results.fairness_metrics
    
    def test_evaluate_classifier_with_business_costs(
        self, sample_classification_data
    ):
        """Test classifier evaluation with business metrics."""
        evaluator = ModelEvaluator()
        y_true, y_pred = sample_classification_data
        
        costs = {
            'false_positive_cost': 10.0,
            'false_negative_cost': 100.0,
            'true_positive_benefit': 50.0,
        }
        
        results = evaluator.evaluate_classifier(
            y_true, y_pred,
            business_costs=costs
        )
        
        assert 'false_positive_cost' in results.business_metrics
        assert 'false_negative_cost' in results.business_metrics
        assert 'true_positive_benefit' in results.business_metrics
        assert 'net_benefit' in results.business_metrics
        assert 'cost_per_prediction' in results.business_metrics
    
    def test_perfect_classifier(self):
        """Test evaluation of a perfect classifier."""
        evaluator = ModelEvaluator()
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 1, 1, 1])
        
        results = evaluator.evaluate_classifier(y_true, y_pred)
        
        assert results.accuracy == 1.0
        assert results.precision == 1.0
        assert results.recall == 1.0
        assert results.f1_score == 1.0
    
    def test_worst_classifier(self):
        """Test evaluation of a worst classifier (all wrong)."""
        evaluator = ModelEvaluator()
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 0, 0, 0])  # All wrong
        
        results = evaluator.evaluate_classifier(y_true, y_pred)
        
        assert results.accuracy == 0.0


# =============================================================================
# Test: Regression Evaluation
# =============================================================================

class TestRegressionEvaluation:
    """Test regression evaluation functionality."""
    
    def test_evaluate_regression(self):
        """Test regression model evaluation."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 1.9, 3.1, 3.9, 5.1])
        
        results = evaluator.evaluate_regression(y_true, y_pred)
        
        assert 'mse' in results
        assert 'rmse' in results
        assert 'mae' in results
        assert 'r2' in results
        assert 'mape' in results
    
    def test_perfect_regression(self):
        """Test evaluation of a perfect regressor."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.0, 2.0, 3.0, 4.0, 5.0])  # Perfect
        
        results = evaluator.evaluate_regression(y_true, y_pred)
        
        assert results['mse'] == 0.0
        assert results['rmse'] == 0.0
        assert results['mae'] == 0.0
        assert results['r2'] == 1.0
        assert results['mape'] == 0.0
    
    def test_regression_metrics_values(self):
        """Test regression metrics have correct values."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.5, 2.5, 3.5])  # Each is off by 0.5
        
        results = evaluator.evaluate_regression(y_true, y_pred)
        
        assert results['mae'] == 0.5  # Mean of [0.5, 0.5, 0.5]
        assert results['mse'] == 0.25  # Mean of [0.25, 0.25, 0.25]
        assert results['rmse'] == 0.5


# =============================================================================
# Test: Calibration Analysis
# =============================================================================

class TestCalibrationAnalysis:
    """Test model calibration analysis."""
    
    def test_calibration_evaluation(self):
        """Test calibration score calculation."""
        evaluator = ModelEvaluator()
        
        # Well-calibrated predictions
        y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 10)
        y_proba = np.column_stack([
            1 - y_true * 0.8 - 0.1,
            y_true * 0.8 + 0.1
        ])
        
        calibration_score = evaluator._evaluate_calibration(y_true, y_proba)
        
        assert 0 <= calibration_score <= 1
    
    def test_poor_calibration(self):
        """Test detection of poor calibration."""
        evaluator = ModelEvaluator()
        
        # Poorly calibrated - always predict 0.9 probability
        y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1] * 10)
        y_proba = np.column_stack([
            np.full_like(y_true, 0.1, dtype=float),
            np.full_like(y_true, 0.9, dtype=float)
        ])
        
        calibration_score = evaluator._evaluate_calibration(y_true, y_proba)
        
        # Poor calibration should have higher score
        assert calibration_score > 0


# =============================================================================
# Test: Fairness Metrics
# =============================================================================

class TestFairnessMetrics:
    """Test fairness metric calculations."""
    
    def test_demographic_parity(self):
        """Test demographic parity calculation."""
        evaluator = ModelEvaluator()
        
        # Equal positive rates across groups
        y_true = np.array([0, 0, 1, 1, 0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 0, 0, 1, 1])
        protected = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        fairness = evaluator._evaluate_fairness(y_true, y_pred, {'attr': protected})
        
        assert 'attr_demographic_parity' in fairness
        assert fairness['attr_demographic_parity'] == 0.0  # Perfect parity
    
    def test_fairness_with_disparity(self):
        """Test fairness detection with actual disparity."""
        evaluator = ModelEvaluator()
        
        # Group 0: 25% positive, Group 1: 75% positive
        y_true = np.array([0, 0, 0, 1, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 1, 1, 1, 1, 1])  # Biased toward group 1
        protected = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        fairness = evaluator._evaluate_fairness(y_true, y_pred, {'attr': protected})
        
        # Should detect disparity
        assert fairness['attr_demographic_parity'] > 0
    
    def test_multiple_protected_attributes(self):
        """Test fairness with multiple protected attributes."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([0, 0, 1, 1, 0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 0, 0, 1, 1])
        
        fairness = evaluator._evaluate_fairness(
            y_true, y_pred,
            {
                'gender': np.array([0, 0, 0, 0, 1, 1, 1, 1]),
                'age': np.array([0, 1, 0, 1, 0, 1, 0, 1]),
            }
        )
        
        assert 'gender_demographic_parity' in fairness
        assert 'age_demographic_parity' in fairness


# =============================================================================
# Test: Business Metrics
# =============================================================================

class TestBusinessMetrics:
    """Test business metric calculations."""
    
    def test_calculate_business_metrics(self):
        """Test business metric calculation."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 1, 0])  # 1 FP, 1 FN, 2 TP
        cm = np.array([[2, 1], [1, 2]])
        
        costs = {
            'false_positive_cost': 10.0,
            'false_negative_cost': 100.0,
            'true_positive_benefit': 50.0,
        }
        
        metrics = evaluator._calculate_business_metrics(y_true, y_pred, cm, costs)
        
        assert metrics['false_positive_cost'] == 10.0  # 1 FP * $10
        assert metrics['false_negative_cost'] == 100.0  # 1 FN * $100
        assert metrics['true_positive_benefit'] == 100.0  # 2 TP * $50
        assert metrics['total_cost'] == 110.0
        assert metrics['net_benefit'] == -10.0  # 100 - 110
    
    def test_positive_net_benefit(self):
        """Test scenario with positive net benefit."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([0, 0, 1, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 1, 1])  # Perfect
        cm = np.array([[2, 0], [0, 4]])  # No FP, No FN, 4 TP
        
        costs = {
            'false_positive_cost': 10.0,
            'false_negative_cost': 100.0,
            'true_positive_benefit': 50.0,
        }
        
        metrics = evaluator._calculate_business_metrics(y_true, y_pred, cm, costs)
        
        assert metrics['net_benefit'] == 200.0  # 4 * 50 = 200
        assert metrics['total_cost'] == 0.0


# =============================================================================
# Test: Model Comparison
# =============================================================================

class TestModelComparison:
    """Test model comparison functionality."""
    
    def test_compare_models(self):
        """Test comparing multiple models."""
        evaluator = ModelEvaluator()
        
        results1 = EvaluationResults(
            accuracy=0.85,
            precision=0.82,
            recall=0.78,
            f1_score=0.80,
            roc_auc=0.87,
            confusion_matrix=np.array([[80, 20], [15, 85]]),
            classification_report="",
            calibration_score=0.08,
            fairness_metrics={},
            business_metrics={},
            feature_importance=None,
        )
        
        results2 = EvaluationResults(
            accuracy=0.90,
            precision=0.88,
            recall=0.85,
            f1_score=0.86,
            roc_auc=0.92,
            confusion_matrix=np.array([[85, 15], [10, 90]]),
            classification_report="",
            calibration_score=0.05,
            fairness_metrics={},
            business_metrics={},
            feature_importance=None,
        )
        
        comparison = evaluator.compare_models([
            ('model_a', results1),
            ('model_b', results2),
        ])
        
        assert len(comparison) == 2
        assert 'model' in comparison.columns
        assert 'f1_score' in comparison.columns
        # Model B should be first (higher F1)
        assert comparison.iloc[0]['model'] == 'model_b'


# =============================================================================
# Test: Report Generation
# =============================================================================

class TestReportGeneration:
    """Test evaluation report generation."""
    
    def test_generate_html_report(self):
        """Test generating HTML evaluation report."""
        evaluator = ModelEvaluator()
        
        results = EvaluationResults(
            accuracy=0.85,
            precision=0.82,
            recall=0.78,
            f1_score=0.80,
            roc_auc=0.87,
            confusion_matrix=np.array([[80, 20], [15, 85]]),
            classification_report="test report",
            calibration_score=0.08,
            fairness_metrics={'demographic_parity': 0.05},
            business_metrics={'net_benefit': 1000},
            feature_importance=None,
        )
        
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            output_path = f.name
        
        try:
            evaluator.generate_report(results, output_path)
            
            # Check file was created
            assert Path(output_path).exists()
            
            # Check content
            with open(output_path, 'r') as f:
                content = f.read()
            
            assert '<html>' in content
            assert 'Accuracy' in content
            assert '0.85' in content
            assert 'Fairness Metrics' in content
            assert 'Business Metrics' in content
        finally:
            Path(output_path).unlink(missing_ok=True)


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases in evaluation."""
    
    def test_single_sample(self):
        """Test evaluation with single sample."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([1])
        y_pred = np.array([1])
        
        results = evaluator.evaluate_classifier(y_true, y_pred)
        
        assert results.accuracy == 1.0
    
    def test_all_same_class(self):
        """Test evaluation when all samples are same class."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([1, 1, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 1, 1])
        
        results = evaluator.evaluate_classifier(y_true, y_pred)
        
        assert results.accuracy == 1.0
    
    def test_empty_protected_attributes(self):
        """Test with empty protected attributes dict."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        
        results = evaluator.evaluate_classifier(
            y_true, y_pred,
            protected_attributes={}
        )
        
        assert results.fairness_metrics == {}
    
    def test_empty_business_costs(self):
        """Test with empty business costs dict."""
        evaluator = ModelEvaluator()
        
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        
        results = evaluator.evaluate_classifier(
            y_true, y_pred,
            business_costs={}
        )
        
        # Empty business costs should result in empty business metrics
        assert results.business_metrics == {}

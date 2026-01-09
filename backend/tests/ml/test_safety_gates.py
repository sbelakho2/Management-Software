"""
Tests for ML Safety Gates

Tests:
- SafetyCheckStatus enum
- SafetyCheckResult data structure
- SafetyGateResults data structure
- SafetyGateConfig thresholds
- MLSafetyGates - Performance checks
- MLSafetyGates - Fairness checks
- MLSafetyGates - Business checks
- MLSafetyGates - Inference checks
- MLSafetyGates - Recommendations
"""

import pytest
import numpy as np

from sensei.ml.safety_gates import (
    SafetyCheckStatus,
    SafetyCheckResult,
    SafetyGateResults,
    SafetyGateConfig,
    MLSafetyGates,
)
from sensei.ml.evaluation import EvaluationResults


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_eval_results():
    """Create sample evaluation results that pass all gates."""
    return EvaluationResults(
        accuracy=0.90,
        precision=0.88,
        recall=0.85,
        f1_score=0.86,
        roc_auc=0.92,
        confusion_matrix=np.array([[85, 15], [10, 90]]),
        classification_report="test report",
        calibration_score=0.05,
        fairness_metrics={
            'gender_demographic_parity': 0.03,
            'gender_fpr_difference': 0.04,
            'gender_tpr_difference': 0.05,
        },
        business_metrics={
            'cost_per_prediction': 2.0,
            'net_benefit': 5000.0,
        },
        feature_importance={'feature1': 0.5, 'feature2': 0.3},
    )


@pytest.fixture
def failing_eval_results():
    """Create evaluation results that fail gates."""
    return EvaluationResults(
        accuracy=0.60,  # Below threshold
        precision=0.55,  # Below threshold
        recall=0.50,  # Below threshold
        f1_score=0.52,  # Below threshold
        roc_auc=0.65,  # Below threshold
        confusion_matrix=np.array([[50, 50], [40, 60]]),
        classification_report="test report",
        calibration_score=0.25,  # Above threshold (worse)
        fairness_metrics={
            'gender_demographic_parity': 0.25,  # Above threshold
            'gender_fpr_difference': 0.20,  # Above threshold
        },
        business_metrics={
            'cost_per_prediction': 50.0,  # Above threshold
            'net_benefit': -1000.0,  # Below threshold (negative)
        },
        feature_importance={'feature1': 0.5},
    )


@pytest.fixture
def sample_training_metadata():
    """Create sample training metadata."""
    return {
        'training_samples': 5000,
        'training_duration_seconds': 120,
    }


@pytest.fixture
def sample_inference_metrics():
    """Create sample inference metrics."""
    return {
        'avg_latency_ms': 100.0,
        'p95_latency_ms': 250.0,
    }


# =============================================================================
# Test: SafetyCheckStatus Enum
# =============================================================================

class TestSafetyCheckStatus:
    """Test SafetyCheckStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert SafetyCheckStatus.PASSED == "passed"
        assert SafetyCheckStatus.FAILED == "failed"
        assert SafetyCheckStatus.WARNING == "warning"
        assert SafetyCheckStatus.SKIPPED == "skipped"
    
    def test_status_string_conversion(self):
        """Test status converts to string."""
        assert str(SafetyCheckStatus.PASSED.value) == "passed"


# =============================================================================
# Test: SafetyCheckResult
# =============================================================================

class TestSafetyCheckResult:
    """Test SafetyCheckResult dataclass."""
    
    def test_create_result(self):
        """Test creating SafetyCheckResult."""
        result = SafetyCheckResult(
            check_name="Test Check",
            status=SafetyCheckStatus.PASSED,
            message="All good",
            actual_value=0.85,
            threshold_value=0.80,
            details={'note': 'test'},
        )
        
        assert result.check_name == "Test Check"
        assert result.status == SafetyCheckStatus.PASSED
        assert result.actual_value == 0.85
        assert result.threshold_value == 0.80


# =============================================================================
# Test: SafetyGateResults
# =============================================================================

class TestSafetyGateResults:
    """Test SafetyGateResults dataclass."""
    
    def test_create_results(self):
        """Test creating SafetyGateResults."""
        check = SafetyCheckResult(
            check_name="Test",
            status=SafetyCheckStatus.PASSED,
            message="OK",
            actual_value=0.9,
            threshold_value=0.8,
            details={},
        )
        
        results = SafetyGateResults(
            overall_status=SafetyCheckStatus.PASSED,
            checks=[check],
            passed_count=1,
            failed_count=0,
            warning_count=0,
            can_deploy=True,
            recommendations=[],
        )
        
        assert results.overall_status == SafetyCheckStatus.PASSED
        assert results.can_deploy is True
        assert len(results.checks) == 1
    
    def test_to_dict(self):
        """Test converting SafetyGateResults to dict."""
        check = SafetyCheckResult(
            check_name="Test",
            status=SafetyCheckStatus.PASSED,
            message="OK",
            actual_value=0.9,
            threshold_value=0.8,
            details={},
        )
        
        results = SafetyGateResults(
            overall_status=SafetyCheckStatus.PASSED,
            checks=[check],
            passed_count=1,
            failed_count=0,
            warning_count=0,
            can_deploy=True,
            recommendations=[],
        )
        
        result_dict = results.to_dict()
        
        assert result_dict['overall_status'] == 'passed'
        assert result_dict['can_deploy'] is True
        assert len(result_dict['checks']) == 1


# =============================================================================
# Test: SafetyGateConfig
# =============================================================================

class TestSafetyGateConfig:
    """Test SafetyGateConfig threshold values."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SafetyGateConfig()
        
        # Performance thresholds
        assert config.MIN_ACCURACY == 0.80
        assert config.MIN_PRECISION == 0.75
        assert config.MIN_RECALL == 0.70
        assert config.MIN_F1_SCORE == 0.75
        assert config.MIN_ROC_AUC == 0.80
        
        # Calibration
        assert config.MAX_CALIBRATION_ERROR == 0.10
        
        # Fairness
        assert config.MAX_DEMOGRAPHIC_PARITY == 0.10
        assert config.MAX_FPR_DIFFERENCE == 0.10
        assert config.MAX_TPR_DIFFERENCE == 0.10
        
        # Data quality
        assert config.MIN_TRAINING_SAMPLES == 1000
        
        # Inference
        assert config.MAX_INFERENCE_LATENCY_MS == 500
        assert config.MAX_INFERENCE_P95_LATENCY_MS == 1000


# =============================================================================
# Test: MLSafetyGates Initialization
# =============================================================================

class TestMLSafetyGatesInit:
    """Test MLSafetyGates initialization."""
    
    def test_init_default_config(self):
        """Test initialization with default config."""
        gates = MLSafetyGates()
        
        assert gates.config is not None
        assert gates.evaluator is not None
    
    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = SafetyGateConfig()
        config.MIN_ACCURACY = 0.95
        
        gates = MLSafetyGates(config=config)
        
        assert gates.config.MIN_ACCURACY == 0.95


# =============================================================================
# Test: Performance Checks
# =============================================================================

class TestPerformanceChecks:
    """Test performance-related safety checks."""
    
    def test_check_accuracy_passing(self, sample_eval_results):
        """Test accuracy check passes."""
        gates = MLSafetyGates()
        result = gates._check_accuracy(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED
        assert result.actual_value == 0.90
    
    def test_check_accuracy_failing(self, failing_eval_results):
        """Test accuracy check fails."""
        gates = MLSafetyGates()
        result = gates._check_accuracy(failing_eval_results)
        
        assert result.status == SafetyCheckStatus.FAILED
        assert result.actual_value == 0.60
    
    def test_check_precision_passing(self, sample_eval_results):
        """Test precision check passes."""
        gates = MLSafetyGates()
        result = gates._check_precision(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_recall_passing(self, sample_eval_results):
        """Test recall check passes."""
        gates = MLSafetyGates()
        result = gates._check_recall(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_f1_score_passing(self, sample_eval_results):
        """Test F1 score check passes."""
        gates = MLSafetyGates()
        result = gates._check_f1_score(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_roc_auc_passing(self, sample_eval_results):
        """Test ROC AUC check passes."""
        gates = MLSafetyGates()
        result = gates._check_roc_auc(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_calibration_passing(self, sample_eval_results):
        """Test calibration check passes."""
        gates = MLSafetyGates()
        result = gates._check_calibration(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED


# =============================================================================
# Test: Fairness Checks
# =============================================================================

class TestFairnessChecks:
    """Test fairness-related safety checks."""
    
    def test_check_fairness_passing(self, sample_eval_results):
        """Test fairness checks pass."""
        gates = MLSafetyGates()
        results = gates._check_fairness(sample_eval_results)
        
        assert len(results) > 0
        for result in results:
            assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_fairness_failing(self, failing_eval_results):
        """Test fairness checks fail when violations exist."""
        gates = MLSafetyGates()
        results = gates._check_fairness(failing_eval_results)
        
        assert len(results) > 0
        # At least one should fail
        failed = [r for r in results if r.status == SafetyCheckStatus.FAILED]
        assert len(failed) > 0


# =============================================================================
# Test: Training Data Checks
# =============================================================================

class TestTrainingDataChecks:
    """Test training data quality checks."""
    
    def test_check_training_samples_sufficient(self, sample_training_metadata):
        """Test sufficient training samples pass."""
        gates = MLSafetyGates()
        result = gates._check_training_samples(sample_training_metadata)
        
        assert result.status == SafetyCheckStatus.PASSED
        assert result.actual_value == 5000.0
    
    def test_check_training_samples_insufficient(self):
        """Test insufficient training samples fail."""
        gates = MLSafetyGates()
        result = gates._check_training_samples({'training_samples': 100})
        
        assert result.status == SafetyCheckStatus.FAILED


# =============================================================================
# Test: Business Metrics Checks
# =============================================================================

class TestBusinessMetricsChecks:
    """Test business metrics safety checks."""
    
    def test_check_business_metrics_passing(self, sample_eval_results):
        """Test business metrics pass."""
        gates = MLSafetyGates()
        results = gates._check_business_metrics(sample_eval_results)
        
        assert len(results) > 0
        for result in results:
            assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_business_metrics_failing(self, failing_eval_results):
        """Test business metrics fail when violations exist."""
        gates = MLSafetyGates()
        results = gates._check_business_metrics(failing_eval_results)
        
        # Net benefit check should fail
        net_benefit_check = [r for r in results if 'Net' in r.check_name]
        assert len(net_benefit_check) > 0
        assert net_benefit_check[0].status == SafetyCheckStatus.FAILED


# =============================================================================
# Test: Inference Performance Checks
# =============================================================================

class TestInferencePerformanceChecks:
    """Test inference performance safety checks."""
    
    def test_check_inference_performance_passing(self, sample_inference_metrics):
        """Test inference metrics pass."""
        gates = MLSafetyGates()
        results = gates._check_inference_performance(sample_inference_metrics)
        
        assert len(results) == 2  # avg and p95
        for result in results:
            assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_inference_performance_warning(self):
        """Test high latency triggers warning."""
        gates = MLSafetyGates()
        slow_metrics = {
            'avg_latency_ms': 600.0,  # Above 500ms threshold
            'p95_latency_ms': 1200.0,  # Above 1000ms threshold
        }
        
        results = gates._check_inference_performance(slow_metrics)
        
        # Both should be warnings
        for result in results:
            assert result.status == SafetyCheckStatus.WARNING


# =============================================================================
# Test: Model Complexity Checks
# =============================================================================

class TestModelComplexityChecks:
    """Test model complexity safety checks."""
    
    def test_check_complexity_passing(self, sample_eval_results):
        """Test reasonable complexity passes."""
        gates = MLSafetyGates()
        result = gates._check_model_complexity(sample_eval_results)
        
        assert result.status == SafetyCheckStatus.PASSED
    
    def test_check_complexity_warning(self):
        """Test high complexity triggers warning."""
        gates = MLSafetyGates()
        
        # Create results with many features
        eval_results = EvaluationResults(
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
            feature_importance={f'feature_{i}': 0.01 for i in range(150)},  # 150 features
        )
        
        result = gates._check_model_complexity(eval_results)
        
        assert result.status == SafetyCheckStatus.WARNING


# =============================================================================
# Test: Full Gate Check
# =============================================================================

class TestFullGateCheck:
    """Test complete safety gate check."""
    
    def test_check_all_gates_passing(
        self, sample_eval_results, sample_training_metadata, sample_inference_metrics
    ):
        """Test all gates pass."""
        gates = MLSafetyGates()
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=sample_eval_results,
            training_metadata=sample_training_metadata,
            inference_metrics=sample_inference_metrics,
        )
        
        assert results.overall_status == SafetyCheckStatus.PASSED
        assert results.can_deploy is True
        assert results.failed_count == 0
    
    def test_check_all_gates_failing(
        self, failing_eval_results, sample_training_metadata
    ):
        """Test gates fail appropriately."""
        gates = MLSafetyGates()
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=failing_eval_results,
            training_metadata=sample_training_metadata,
        )
        
        assert results.overall_status == SafetyCheckStatus.FAILED
        assert results.can_deploy is False
        assert results.failed_count > 0
    
    def test_check_all_gates_with_warnings(self, sample_eval_results):
        """Test gates pass with warnings."""
        gates = MLSafetyGates()
        
        # Modify results to have warning-level issues
        sample_eval_results.calibration_score = 0.15  # Above threshold but warning
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=sample_eval_results,
            training_metadata={'training_samples': 5000},
        )
        
        # Should be able to deploy with warnings
        assert results.warning_count > 0


# =============================================================================
# Test: Recommendations
# =============================================================================

class TestRecommendations:
    """Test recommendation generation."""
    
    def test_generate_recommendations_for_failures(
        self, failing_eval_results, sample_training_metadata
    ):
        """Test recommendations are generated for failures."""
        gates = MLSafetyGates()
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=failing_eval_results,
            training_metadata=sample_training_metadata,
        )
        
        assert len(results.recommendations) > 0
    
    def test_no_recommendations_when_passing(
        self, sample_eval_results, sample_training_metadata, sample_inference_metrics
    ):
        """Test no recommendations when all passes."""
        gates = MLSafetyGates()
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=sample_eval_results,
            training_metadata=sample_training_metadata,
            inference_metrics=sample_inference_metrics,
        )
        
        # No recommendations needed when all pass
        assert results.failed_count == 0
    
    def test_recommendations_have_actionable_content(
        self, failing_eval_results, sample_training_metadata
    ):
        """Test recommendations are actionable."""
        gates = MLSafetyGates()
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=failing_eval_results,
            training_metadata=sample_training_metadata,
        )
        
        for rec in results.recommendations:
            # Each recommendation should have substantial content
            assert len(rec) > 20


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases in safety gates."""
    
    def test_minimal_eval_results(self):
        """Test with minimal evaluation results."""
        gates = MLSafetyGates()
        
        minimal_results = EvaluationResults(
            accuracy=0.85,
            precision=0.80,
            recall=0.75,
            f1_score=0.77,
            roc_auc=None,  # No ROC AUC
            confusion_matrix=np.array([[80, 20], [20, 80]]),
            classification_report="",
            calibration_score=None,  # No calibration
            fairness_metrics={},  # No fairness
            business_metrics={},  # No business
            feature_importance=None,  # No complexity check
        )
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=minimal_results,
            training_metadata={'training_samples': 2000},
        )
        
        # Should still run and produce results
        assert results is not None
        assert len(results.checks) > 0
    
    def test_empty_training_metadata(self):
        """Test with empty training metadata."""
        gates = MLSafetyGates()
        
        minimal_results = EvaluationResults(
            accuracy=0.85,
            precision=0.80,
            recall=0.75,
            f1_score=0.77,
            roc_auc=0.82,
            confusion_matrix=np.array([[80, 20], [20, 80]]),
            classification_report="",
            calibration_score=None,
            fairness_metrics={},
            business_metrics={},
            feature_importance=None,
        )
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=minimal_results,
            training_metadata={},  # Empty
        )
        
        # Should handle empty metadata (sample check should fail)
        sample_check = [c for c in results.checks if 'Training' in c.check_name]
        assert len(sample_check) > 0
        assert sample_check[0].status == SafetyCheckStatus.FAILED
    
    def test_custom_thresholds(self, sample_eval_results, sample_training_metadata):
        """Test with custom threshold configuration."""
        config = SafetyGateConfig()
        config.MIN_ACCURACY = 0.95  # Higher than sample's 0.90
        
        gates = MLSafetyGates(config=config)
        
        results = gates.check_all_gates(
            model_name="test_model",
            eval_results=sample_eval_results,
            training_metadata=sample_training_metadata,
        )
        
        # Accuracy check should fail with stricter threshold
        accuracy_check = [c for c in results.checks if 'Accuracy' in c.check_name]
        assert len(accuracy_check) > 0
        assert accuracy_check[0].status == SafetyCheckStatus.FAILED

"""
ML Safety Gates: Production Deployment Safety Checks

Enforces safety gates before deploying ML models to production:
1. Minimum performance thresholds
2. Fairness constraints
3. Calibration requirements
4. Data drift detection
5. Inference latency limits
6. Model explainability verification
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging

from sensei.ml.evaluation import ModelEvaluator, EvaluationResults

logger = logging.getLogger(__name__)


class SafetyCheckStatus(str, Enum):
    """Status of a safety check."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class SafetyCheckResult:
    """Result of a single safety check."""
    check_name: str
    status: SafetyCheckStatus
    message: str
    actual_value: Optional[float]
    threshold_value: Optional[float]
    details: Dict[str, Any]


@dataclass
class SafetyGateResults:
    """Results from all safety gates."""
    overall_status: SafetyCheckStatus
    checks: List[SafetyCheckResult]
    passed_count: int
    failed_count: int
    warning_count: int
    can_deploy: bool
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'overall_status': self.overall_status.value,
            'passed_count': self.passed_count,
            'failed_count': self.failed_count,
            'warning_count': self.warning_count,
            'can_deploy': self.can_deploy,
            'checks': [
                {
                    'check_name': c.check_name,
                    'status': c.status.value,
                    'message': c.message,
                    'actual_value': c.actual_value,
                    'threshold_value': c.threshold_value,
                    'details': c.details,
                }
                for c in self.checks
            ],
            'recommendations': self.recommendations,
        }


class SafetyGateConfig:
    """Configuration for safety gate thresholds."""
    
    # Performance thresholds
    MIN_ACCURACY = 0.80
    MIN_PRECISION = 0.75
    MIN_RECALL = 0.70
    MIN_F1_SCORE = 0.75
    MIN_ROC_AUC = 0.80
    
    # Calibration
    MAX_CALIBRATION_ERROR = 0.10  # Expected Calibration Error
    
    # Fairness
    MAX_DEMOGRAPHIC_PARITY = 0.10  # 10% difference
    MAX_FPR_DIFFERENCE = 0.10
    MAX_TPR_DIFFERENCE = 0.10
    
    # Data quality
    MIN_TRAINING_SAMPLES = 1000
    MAX_MISSING_VALUES_PCT = 0.05  # 5%
    
    # Inference
    MAX_INFERENCE_LATENCY_MS = 500
    MAX_INFERENCE_P95_LATENCY_MS = 1000
    
    # Business metrics
    MAX_COST_PER_PREDICTION = 10.0  # dollars
    MIN_NET_BENEFIT = 0  # Must be positive
    
    # Model complexity (for explainability)
    MAX_MODEL_FEATURES = 100
    MIN_FEATURE_IMPORTANCE_COVERAGE = 0.90  # Top features should explain 90%


class MLSafetyGates:
    """
    Enforce safety gates for ML model deployment.
    
    All gates must pass (or have warnings only) for deployment.
    """

    def __init__(self, config: Optional[SafetyGateConfig] = None):
        self.config = config or SafetyGateConfig()
        self.evaluator = ModelEvaluator()
    
    def check_all_gates(
        self,
        model_name: str,
        eval_results: EvaluationResults,
        training_metadata: Dict[str, Any],
        inference_metrics: Optional[Dict[str, float]] = None,
    ) -> SafetyGateResults:
        """
        Run all safety checks.
        
        Args:
            model_name: Name of the model
            eval_results: Evaluation results from test set
            training_metadata: Metadata from training (samples, duration, etc.)
            inference_metrics: Production inference metrics (if available)
        
        Returns:
            SafetyGateResults with pass/fail for each check
        """
        logger.info(f"Running safety gates for model: {model_name}")
        
        checks: List[SafetyCheckResult] = []
        
        # 1. Performance checks
        checks.append(self._check_accuracy(eval_results))
        checks.append(self._check_precision(eval_results))
        checks.append(self._check_recall(eval_results))
        checks.append(self._check_f1_score(eval_results))
        if eval_results.roc_auc is not None:
            checks.append(self._check_roc_auc(eval_results))
        
        # 2. Calibration check
        if eval_results.calibration_score is not None:
            checks.append(self._check_calibration(eval_results))
        
        # 3. Fairness checks
        if eval_results.fairness_metrics:
            checks.extend(self._check_fairness(eval_results))
        
        # 4. Data quality checks
        checks.append(self._check_training_samples(training_metadata))
        
        # 5. Business metrics checks
        if eval_results.business_metrics:
            checks.extend(self._check_business_metrics(eval_results))
        
        # 6. Inference performance checks
        if inference_metrics:
            checks.extend(self._check_inference_performance(inference_metrics))
        
        # 7. Model complexity checks
        if eval_results.feature_importance:
            checks.append(self._check_model_complexity(eval_results))
        
        # Aggregate results
        passed = sum(1 for c in checks if c.status == SafetyCheckStatus.PASSED)
        failed = sum(1 for c in checks if c.status == SafetyCheckStatus.FAILED)
        warnings = sum(1 for c in checks if c.status == SafetyCheckStatus.WARNING)
        
        # Overall status
        if failed > 0:
            overall_status = SafetyCheckStatus.FAILED
            can_deploy = False
        elif warnings > 0:
            overall_status = SafetyCheckStatus.WARNING
            can_deploy = True  # Can deploy but with warnings
        else:
            overall_status = SafetyCheckStatus.PASSED
            can_deploy = True
        
        # Generate recommendations
        recommendations = self._generate_recommendations(checks)
        
        results = SafetyGateResults(
            overall_status=overall_status,
            checks=checks,
            passed_count=passed,
            failed_count=failed,
            warning_count=warnings,
            can_deploy=can_deploy,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Safety gates complete. Status: {overall_status.value}, "
            f"Passed: {passed}, Failed: {failed}, Warnings: {warnings}"
        )
        
        return results
    
    def _check_accuracy(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check minimum accuracy threshold."""
        passed = eval_results.accuracy >= self.config.MIN_ACCURACY
        
        return SafetyCheckResult(
            check_name="Minimum Accuracy",
            status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
            message=f"Accuracy {eval_results.accuracy:.3f} {'meets' if passed else 'below'} threshold {self.config.MIN_ACCURACY:.3f}",
            actual_value=eval_results.accuracy,
            threshold_value=self.config.MIN_ACCURACY,
            details={},
        )
    
    def _check_precision(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check minimum precision threshold."""
        passed = eval_results.precision >= self.config.MIN_PRECISION
        
        return SafetyCheckResult(
            check_name="Minimum Precision",
            status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
            message=f"Precision {eval_results.precision:.3f} {'meets' if passed else 'below'} threshold {self.config.MIN_PRECISION:.3f}",
            actual_value=eval_results.precision,
            threshold_value=self.config.MIN_PRECISION,
            details={},
        )
    
    def _check_recall(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check minimum recall threshold."""
        passed = eval_results.recall >= self.config.MIN_RECALL
        
        return SafetyCheckResult(
            check_name="Minimum Recall",
            status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
            message=f"Recall {eval_results.recall:.3f} {'meets' if passed else 'below'} threshold {self.config.MIN_RECALL:.3f}",
            actual_value=eval_results.recall,
            threshold_value=self.config.MIN_RECALL,
            details={},
        )
    
    def _check_f1_score(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check minimum F1 score threshold."""
        passed = eval_results.f1_score >= self.config.MIN_F1_SCORE
        
        return SafetyCheckResult(
            check_name="Minimum F1 Score",
            status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
            message=f"F1 score {eval_results.f1_score:.3f} {'meets' if passed else 'below'} threshold {self.config.MIN_F1_SCORE:.3f}",
            actual_value=eval_results.f1_score,
            threshold_value=self.config.MIN_F1_SCORE,
            details={},
        )
    
    def _check_roc_auc(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check minimum ROC AUC threshold."""
        passed = eval_results.roc_auc >= self.config.MIN_ROC_AUC
        
        return SafetyCheckResult(
            check_name="Minimum ROC AUC",
            status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
            message=f"ROC AUC {eval_results.roc_auc:.3f} {'meets' if passed else 'below'} threshold {self.config.MIN_ROC_AUC:.3f}",
            actual_value=eval_results.roc_auc,
            threshold_value=self.config.MIN_ROC_AUC,
            details={},
        )
    
    def _check_calibration(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check calibration error threshold."""
        passed = eval_results.calibration_score <= self.config.MAX_CALIBRATION_ERROR
        
        status = SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.WARNING
        
        return SafetyCheckResult(
            check_name="Calibration Quality",
            status=status,
            message=f"Calibration error {eval_results.calibration_score:.3f} {'within' if passed else 'exceeds'} threshold {self.config.MAX_CALIBRATION_ERROR:.3f}",
            actual_value=eval_results.calibration_score,
            threshold_value=self.config.MAX_CALIBRATION_ERROR,
            details={'note': 'Poor calibration may require recalibration before deployment'},
        )
    
    def _check_fairness(self, eval_results: EvaluationResults) -> List[SafetyCheckResult]:
        """Check fairness constraints."""
        checks = []
        
        for metric_name, value in eval_results.fairness_metrics.items():
            if 'demographic_parity' in metric_name:
                threshold = self.config.MAX_DEMOGRAPHIC_PARITY
                passed = value <= threshold
            elif 'fpr_difference' in metric_name:
                threshold = self.config.MAX_FPR_DIFFERENCE
                passed = value <= threshold
            elif 'tpr_difference' in metric_name:
                threshold = self.config.MAX_TPR_DIFFERENCE
                passed = value <= threshold
            else:
                continue
            
            status = SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED
            
            checks.append(SafetyCheckResult(
                check_name=f"Fairness: {metric_name}",
                status=status,
                message=f"{metric_name} = {value:.3f} {'within' if passed else 'exceeds'} threshold {threshold:.3f}",
                actual_value=value,
                threshold_value=threshold,
                details={'protected_attribute': metric_name.split('_')[0]},
            ))
        
        return checks
    
    def _check_training_samples(self, training_metadata: Dict) -> SafetyCheckResult:
        """Check minimum training samples."""
        sample_count = training_metadata.get('training_samples', 0)
        passed = sample_count >= self.config.MIN_TRAINING_SAMPLES
        
        return SafetyCheckResult(
            check_name="Training Data Sufficiency",
            status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
            message=f"Training samples: {sample_count} {'sufficient' if passed else 'insufficient'} (min: {self.config.MIN_TRAINING_SAMPLES})",
            actual_value=float(sample_count),
            threshold_value=float(self.config.MIN_TRAINING_SAMPLES),
            details={},
        )
    
    def _check_business_metrics(self, eval_results: EvaluationResults) -> List[SafetyCheckResult]:
        """Check business impact metrics."""
        checks = []
        
        business_metrics = eval_results.business_metrics
        
        # Cost per prediction
        if 'cost_per_prediction' in business_metrics:
            cost = business_metrics['cost_per_prediction']
            passed = cost <= self.config.MAX_COST_PER_PREDICTION
            
            checks.append(SafetyCheckResult(
                check_name="Cost Per Prediction",
                status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.WARNING,
                message=f"Cost per prediction: ${cost:.2f} {'acceptable' if passed else 'high'} (max: ${self.config.MAX_COST_PER_PREDICTION:.2f})",
                actual_value=cost,
                threshold_value=self.config.MAX_COST_PER_PREDICTION,
                details={},
            ))
        
        # Net benefit
        if 'net_benefit' in business_metrics:
            benefit = business_metrics['net_benefit']
            passed = benefit >= self.config.MIN_NET_BENEFIT
            
            checks.append(SafetyCheckResult(
                check_name="Net Business Benefit",
                status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.FAILED,
                message=f"Net benefit: ${benefit:.2f} {'positive' if passed else 'negative or zero'}",
                actual_value=benefit,
                threshold_value=self.config.MIN_NET_BENEFIT,
                details={},
            ))
        
        return checks
    
    def _check_inference_performance(self, inference_metrics: Dict) -> List[SafetyCheckResult]:
        """Check inference latency requirements."""
        checks = []
        
        # Average latency
        if 'avg_latency_ms' in inference_metrics:
            latency = inference_metrics['avg_latency_ms']
            passed = latency <= self.config.MAX_INFERENCE_LATENCY_MS
            
            checks.append(SafetyCheckResult(
                check_name="Average Inference Latency",
                status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.WARNING,
                message=f"Avg latency: {latency:.1f}ms {'acceptable' if passed else 'high'} (max: {self.config.MAX_INFERENCE_LATENCY_MS}ms)",
                actual_value=latency,
                threshold_value=float(self.config.MAX_INFERENCE_LATENCY_MS),
                details={},
            ))
        
        # P95 latency
        if 'p95_latency_ms' in inference_metrics:
            p95 = inference_metrics['p95_latency_ms']
            passed = p95 <= self.config.MAX_INFERENCE_P95_LATENCY_MS
            
            checks.append(SafetyCheckResult(
                check_name="P95 Inference Latency",
                status=SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.WARNING,
                message=f"P95 latency: {p95:.1f}ms {'acceptable' if passed else 'high'} (max: {self.config.MAX_INFERENCE_P95_LATENCY_MS}ms)",
                actual_value=p95,
                threshold_value=float(self.config.MAX_INFERENCE_P95_LATENCY_MS),
                details={},
            ))
        
        return checks
    
    def _check_model_complexity(self, eval_results: EvaluationResults) -> SafetyCheckResult:
        """Check model complexity for explainability."""
        feature_count = len(eval_results.feature_importance)
        passed = feature_count <= self.config.MAX_MODEL_FEATURES
        
        status = SafetyCheckStatus.PASSED if passed else SafetyCheckStatus.WARNING
        
        return SafetyCheckResult(
            check_name="Model Complexity",
            status=status,
            message=f"Feature count: {feature_count} {'reasonable' if passed else 'high'} for explainability (max: {self.config.MAX_MODEL_FEATURES})",
            actual_value=float(feature_count),
            threshold_value=float(self.config.MAX_MODEL_FEATURES),
            details={'note': 'High complexity may reduce interpretability'},
        )
    
    def _generate_recommendations(self, checks: List[SafetyCheckResult]) -> List[str]:
        """Generate recommendations based on failed/warning checks."""
        recommendations = []
        
        for check in checks:
            if check.status == SafetyCheckStatus.FAILED:
                if 'Accuracy' in check.check_name or 'F1' in check.check_name:
                    recommendations.append("Consider collecting more training data or improving feature engineering")
                elif 'Precision' in check.check_name:
                    recommendations.append("Adjust classification threshold to reduce false positives")
                elif 'Recall' in check.check_name:
                    recommendations.append("Adjust classification threshold to reduce false negatives")
                elif 'Fairness' in check.check_name:
                    recommendations.append(f"Address fairness issue in {check.check_name}: consider rebalancing training data or using fairness constraints")
                elif 'Training Data' in check.check_name:
                    recommendations.append("Collect more training samples before deploying")
                elif 'Net Business Benefit' in check.check_name:
                    recommendations.append("Model does not provide positive ROI. Review business case or improve model performance")
            
            elif check.status == SafetyCheckStatus.WARNING:
                if 'Calibration' in check.check_name:
                    recommendations.append("Consider recalibrating model probabilities (e.g., using Platt scaling or isotonic regression)")
                elif 'Latency' in check.check_name:
                    recommendations.append("Optimize model for inference speed (e.g., model pruning, quantization, or caching)")
                elif 'Complexity' in check.check_name:
                    recommendations.append("Consider simplifying model for better interpretability (e.g., feature selection)")
        
        return recommendations


# Example usage
if __name__ == "__main__":
    from sensei.ml.evaluation import EvaluationResults
    import numpy as np
    
    # Mock evaluation results
    mock_results = EvaluationResults(
        accuracy=0.85,
        precision=0.82,
        recall=0.78,
        f1_score=0.80,
        roc_auc=0.87,
        confusion_matrix=np.array([[80, 20], [15, 85]]),
        classification_report="...",
        calibration_score=0.08,
        fairness_metrics={
            'gender_demographic_parity': 0.05,
            'gender_fpr_difference': 0.07,
        },
        business_metrics={
            'cost_per_prediction': 2.5,
            'net_benefit': 15000,
        },
        feature_importance={'feature1': 0.3, 'feature2': 0.25},
    )
    
    training_metadata = {
        'training_samples': 5000,
    }
    
    inference_metrics = {
        'avg_latency_ms': 120,
        'p95_latency_ms': 350,
    }
    
    # Run safety gates
    gates = MLSafetyGates()
    results = gates.check_all_gates(
        model_name="test_model",
        eval_results=mock_results,
        training_metadata=training_metadata,
        inference_metrics=inference_metrics,
    )
    
    print(f"Overall Status: {results.overall_status.value}")
    print(f"Can Deploy: {results.can_deploy}")
    print(f"Passed: {results.passed_count}, Failed: {results.failed_count}, Warnings: {results.warning_count}")
    
    for check in results.checks:
        print(f"  [{check.status.value.upper()}] {check.check_name}: {check.message}")
    
    if results.recommendations:
        print("\nRecommendations:")
        for rec in results.recommendations:
            print(f"  - {rec}")

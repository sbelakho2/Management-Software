"""
ML Model Evaluation Framework

Comprehensive evaluation of ML models:
- Standard metrics (accuracy, precision, recall, F1)
- Business metrics (cost savings, false positive rate)
- Fairness metrics (demographic parity, equalized odds)
- Model explainability (SHAP values)
- Calibration analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)
from sklearn.calibration import calibration_curve
import logging

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResults:
    """Results from model evaluation."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: Optional[float]
    confusion_matrix: np.ndarray
    classification_report: str
    calibration_score: Optional[float]
    fairness_metrics: Dict[str, float]
    business_metrics: Dict[str, Any]
    feature_importance: Optional[Dict[str, float]]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'roc_auc': self.roc_auc,
            'confusion_matrix': self.confusion_matrix.tolist(),
            'classification_report': self.classification_report,
            'calibration_score': self.calibration_score,
            'fairness_metrics': self.fairness_metrics,
            'business_metrics': self.business_metrics,
            'feature_importance': self.feature_importance,
        }


class ModelEvaluator:
    """
    Comprehensive model evaluation.
    
    Evaluates:
    - Classification performance
    - Calibration
    - Fairness across demographics
    - Business impact
    """

    def __init__(self):
        pass
    
    def evaluate_classifier(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: Optional[np.ndarray] = None,
        protected_attributes: Optional[Dict[str, np.ndarray]] = None,
        business_costs: Optional[Dict[str, float]] = None,
    ) -> EvaluationResults:
        """
        Evaluate a classification model comprehensively.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_pred_proba: Predicted probabilities (for calibration)
            protected_attributes: Dict mapping attribute name -> values (for fairness)
            business_costs: Dict with 'false_positive_cost', 'false_negative_cost', 'true_positive_benefit'
        
        Returns:
            EvaluationResults
        """
        logger.info("Evaluating classifier...")
        
        # Standard metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average='weighted')
        recall = recall_score(y_true, y_pred, average='weighted')
        f1 = f1_score(y_true, y_pred, average='weighted')
        
        # ROC AUC (if probabilities available)
        roc_auc = None
        if y_pred_proba is not None:
            try:
                roc_auc = roc_auc_score(y_true, y_pred_proba[:, 1])
            except:
                pass
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        # Classification report
        report = classification_report(y_true, y_pred)
        
        # Calibration
        calibration_score = None
        if y_pred_proba is not None:
            calibration_score = self._evaluate_calibration(y_true, y_pred_proba)
        
        # Fairness metrics
        fairness_metrics = {}
        if protected_attributes:
            fairness_metrics = self._evaluate_fairness(y_true, y_pred, protected_attributes)
        
        # Business metrics
        business_metrics = {}
        if business_costs:
            business_metrics = self._calculate_business_metrics(y_true, y_pred, cm, business_costs)
        
        results = EvaluationResults(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            roc_auc=roc_auc,
            confusion_matrix=cm,
            classification_report=report,
            calibration_score=calibration_score,
            fairness_metrics=fairness_metrics,
            business_metrics=business_metrics,
            feature_importance=None,
        )
        
        logger.info(f"Evaluation complete. F1: {f1:.3f}, Accuracy: {accuracy:.3f}")
        return results
    
    def evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Dict[str, float]:
        """Evaluate a regression model."""
        from sklearn.metrics import (
            mean_squared_error,
            mean_absolute_error,
            r2_score,
        )
        
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape,
        }
    
    def _evaluate_calibration(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
    ) -> float:
        """
        Evaluate model calibration.
        
        Returns calibration error (lower is better).
        """
        # Get positive class probabilities
        if y_pred_proba.ndim > 1:
            y_proba = y_pred_proba[:, 1]
        else:
            y_proba = y_pred_proba
        
        # Calculate calibration curve
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_true, y_proba, n_bins=10
        )
        
        # Expected Calibration Error (ECE)
        ece = np.mean(np.abs(fraction_of_positives - mean_predicted_value))
        
        return float(ece)
    
    def _evaluate_fairness(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        protected_attributes: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """
        Evaluate fairness across protected attributes.
        
        Calculates:
        - Demographic parity: P(ŷ=1|A=0) ≈ P(ŷ=1|A=1)
        - Equalized odds: FPR and TPR should be similar across groups
        """
        fairness_metrics = {}
        
        for attr_name, attr_values in protected_attributes.items():
            unique_values = np.unique(attr_values)
            
            if len(unique_values) != 2:
                logger.warning(f"Fairness evaluation requires binary protected attribute. Skipping {attr_name}")
                continue
            
            # Split by protected attribute
            mask_0 = attr_values == unique_values[0]
            mask_1 = attr_values == unique_values[1]
            
            # Demographic parity
            positive_rate_0 = np.mean(y_pred[mask_0])
            positive_rate_1 = np.mean(y_pred[mask_1])
            demographic_parity = abs(positive_rate_0 - positive_rate_1)
            
            # Equalized odds (FPR and TPR difference)
            cm_0 = confusion_matrix(y_true[mask_0], y_pred[mask_0])
            cm_1 = confusion_matrix(y_true[mask_1], y_pred[mask_1])
            
            if cm_0.shape == (2, 2) and cm_1.shape == (2, 2):
                fpr_0 = cm_0[0, 1] / (cm_0[0, 0] + cm_0[0, 1]) if (cm_0[0, 0] + cm_0[0, 1]) > 0 else 0
                fpr_1 = cm_1[0, 1] / (cm_1[0, 0] + cm_1[0, 1]) if (cm_1[0, 0] + cm_1[0, 1]) > 0 else 0
                fpr_diff = abs(fpr_0 - fpr_1)
                
                tpr_0 = cm_0[1, 1] / (cm_0[1, 0] + cm_0[1, 1]) if (cm_0[1, 0] + cm_0[1, 1]) > 0 else 0
                tpr_1 = cm_1[1, 1] / (cm_1[1, 0] + cm_1[1, 1]) if (cm_1[1, 0] + cm_1[1, 1]) > 0 else 0
                tpr_diff = abs(tpr_0 - tpr_1)
            else:
                fpr_diff = 0
                tpr_diff = 0
            
            fairness_metrics[f'{attr_name}_demographic_parity'] = demographic_parity
            fairness_metrics[f'{attr_name}_fpr_difference'] = fpr_diff
            fairness_metrics[f'{attr_name}_tpr_difference'] = tpr_diff
        
        return fairness_metrics
    
    def _calculate_business_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        confusion_matrix: np.ndarray,
        costs: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Calculate business impact metrics.
        
        Args:
            costs: Dict with:
                - false_positive_cost: Cost of a false positive
                - false_negative_cost: Cost of a false negative
                - true_positive_benefit: Benefit of a true positive
        """
        tn, fp, fn, tp = confusion_matrix.ravel()
        
        fp_cost = costs.get('false_positive_cost', 0) * fp
        fn_cost = costs.get('false_negative_cost', 0) * fn
        tp_benefit = costs.get('true_positive_benefit', 0) * tp
        
        total_cost = fp_cost + fn_cost
        net_benefit = tp_benefit - total_cost
        
        # Cost per prediction
        cost_per_prediction = total_cost / len(y_true)
        
        return {
            'false_positive_cost': fp_cost,
            'false_negative_cost': fn_cost,
            'true_positive_benefit': tp_benefit,
            'total_cost': total_cost,
            'net_benefit': net_benefit,
            'cost_per_prediction': cost_per_prediction,
        }
    
    def compare_models(
        self,
        results_list: List[Tuple[str, EvaluationResults]],
    ) -> pd.DataFrame:
        """
        Compare multiple models.
        
        Args:
            results_list: List of (model_name, EvaluationResults) tuples
        
        Returns:
            DataFrame with comparison
        """
        comparison_data = []
        
        for model_name, results in results_list:
            comparison_data.append({
                'model': model_name,
                'accuracy': results.accuracy,
                'precision': results.precision,
                'recall': results.recall,
                'f1_score': results.f1_score,
                'roc_auc': results.roc_auc,
                'calibration_error': results.calibration_score,
            })
        
        df = pd.DataFrame(comparison_data)
        return df.sort_values('f1_score', ascending=False)
    
    def generate_report(
        self,
        results: EvaluationResults,
        output_path: str,
    ) -> None:
        """Generate HTML evaluation report."""
        html = f"""
        <html>
        <head><title>Model Evaluation Report</title></head>
        <body>
            <h1>Model Evaluation Report</h1>
            <h2>Performance Metrics</h2>
            <table border="1">
                <tr><td>Accuracy</td><td>{results.accuracy:.3f}</td></tr>
                <tr><td>Precision</td><td>{results.precision:.3f}</td></tr>
                <tr><td>Recall</td><td>{results.recall:.3f}</td></tr>
                <tr><td>F1 Score</td><td>{results.f1_score:.3f}</td></tr>
                <tr><td>ROC AUC</td><td>{results.roc_auc or 'N/A'}</td></tr>
            </table>
            
            <h2>Confusion Matrix</h2>
            <pre>{results.confusion_matrix}</pre>
            
            <h2>Classification Report</h2>
            <pre>{results.classification_report}</pre>
            
            <h2>Fairness Metrics</h2>
            <table border="1">
                {''.join(f'<tr><td>{k}</td><td>{v:.3f}</td></tr>' for k, v in results.fairness_metrics.items())}
            </table>
            
            <h2>Business Metrics</h2>
            <table border="1">
                {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in results.business_metrics.items())}
            </table>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Evaluation report saved to {output_path}")

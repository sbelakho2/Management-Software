//! ML Model Evaluation Framework.
//!
//! Comprehensive evaluation of ML models:
//! - Standard metrics (accuracy, precision, recall, F1, ROC AUC)
//! - Regression metrics (MSE, RMSE, MAE, R², MAPE)
//! - Confusion matrix and classification reports
//! - Calibration analysis (Expected Calibration Error)
//! - Fairness metrics (demographic parity, equalized odds)
//! - Business impact metrics

use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Evaluation Results
// ---------------------------------------------------------------------------

/// Results from a classification model evaluation.
#[derive(Debug, Clone)]
pub struct EvaluationResults {
    pub accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1_score: f64,
    pub roc_auc: Option<f64>,
    pub confusion_matrix: [[usize; 2]; 2], // [[TN, FP], [FN, TP]]
    pub classification_report: String,
    pub calibration_score: Option<f64>,
    pub fairness_metrics: HashMap<String, f64>,
    pub business_metrics: HashMap<String, f64>,
    pub feature_importance: Option<HashMap<String, f64>>,
}

impl EvaluationResults {
    pub fn to_map(&self) -> HashMap<String, serde_json::Value> {
        let mut map = HashMap::new();
        map.insert("accuracy".into(), serde_json::json!(self.accuracy));
        map.insert("precision".into(), serde_json::json!(self.precision));
        map.insert("recall".into(), serde_json::json!(self.recall));
        map.insert("f1_score".into(), serde_json::json!(self.f1_score));
        if let Some(auc) = self.roc_auc {
            map.insert("roc_auc".into(), serde_json::json!(auc));
        }
        map.insert(
            "confusion_matrix".into(),
            serde_json::json!([
                [self.confusion_matrix[0][0], self.confusion_matrix[0][1]],
                [self.confusion_matrix[1][0], self.confusion_matrix[1][1]],
            ]),
        );
        map.insert(
            "calibration_score".into(),
            serde_json::json!(self.calibration_score),
        );
        let fm: HashMap<_, _> = self
            .fairness_metrics
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!(v)))
            .collect();
        map.insert("fairness_metrics".into(), serde_json::json!(fm));
        let bm: HashMap<_, _> = self
            .business_metrics
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!(v)))
            .collect();
        map.insert("business_metrics".into(), serde_json::json!(bm));
        map
    }
}

// ---------------------------------------------------------------------------
// Model Evaluator
// ---------------------------------------------------------------------------

/// Comprehensive model evaluation engine.
#[derive(Debug, Clone)]
pub struct ModelEvaluator;

impl ModelEvaluator {
    pub fn new() -> Self {
        Self
    }

    /// Evaluate a classification model comprehensively.
    ///
    /// * `y_true` - True binary labels (0 or 1).
    /// * `y_pred` - Predicted binary labels (0 or 1).
    /// * `y_pred_proba` - Predicted probabilities for the positive class (optional).
    /// * `protected_attributes` - Map of attribute name → binary array for fairness evaluation (optional).
    /// * `business_costs` - Map with keys: false_positive_cost, false_negative_cost, true_positive_benefit (optional).
    pub fn evaluate_classifier(
        &self,
        y_true: &[f64],
        y_pred: &[f64],
        y_pred_proba: Option<&[f64]>,
        protected_attributes: Option<&HashMap<String, Vec<f64>>>,
        business_costs: Option<&HashMap<String, f64>>,
    ) -> EvaluationResults {
        let n = y_true.len();
        assert_eq!(y_pred.len(), n, "y_true and y_pred must have same length");

        // Confusion matrix
        let cm = compute_confusion_matrix(y_true, y_pred);
        let (tn, fp, fn_, tp) = (cm[0][0], cm[0][1], cm[1][0], cm[1][1]);

        // Standard metrics
        let accuracy = accuracy_score(y_true, y_pred);
        let precision = precision_score(tp, fp);
        let recall = recall_score(tp, fn_);
        let f1 = f1_score(precision, recall);

        // ROC AUC
        let roc_auc = y_pred_proba.map(|proba| roc_auc_score(y_true, proba));

        // Classification report string
        let report = format!(
            "              precision    recall  f1-score   support\n\
             \n\
              0           {:.3}      {:.3}     {:.3}     {:>6}\n\
              1           {:.3}      {:.3}     {:.3}     {:>6}\n\
             \n\
             accuracy                           {:.3}     {:>6}\n\
             macro avg    {:.3}      {:.3}     {:.3}     {:>6}\n\
             weighted avg {:.3}      {:.3}     {:.3}     {:>6}\n",
            precision_score(tn, fn_), // precision for class 0 = TN/(TN+FN)
            recall_score(tn, fp),     // recall for class 0 = TN/(TN+FP)
            f1_score(precision_score(tn, fn_), recall_score(tn, fp)),
            tn + fn_,
            precision,
            recall,
            f1,
            tp + fp,
            accuracy,
            n,
            (precision_score(tn, fn_) + precision) / 2.0,
            (recall_score(tn, fp) + recall) / 2.0,
            (f1_score(precision_score(tn, fn_), recall_score(tn, fp)) + f1) / 2.0,
            n,
            precision * (tp + fp) as f64 / n as f64
                + precision_score(tn, fn_) * (tn + fn_) as f64 / n as f64,
            recall * (tp + fn_) as f64 / n as f64
                + recall_score(tn, fp) * (tn + fp) as f64 / n as f64,
            f1 * (tp + fp) as f64 / n as f64
                + f1_score(precision_score(tn, fn_), recall_score(tn, fp)) * (tn + fn_) as f64
                    / n as f64,
            n,
        );

        // Calibration
        let calibration_score = y_pred_proba.map(|proba| evaluate_calibration(y_true, proba, 10));

        // Fairness metrics
        let fairness_metrics = if let Some(attrs) = protected_attributes {
            evaluate_fairness(y_true, y_pred, attrs)
        } else {
            HashMap::new()
        };

        // Business metrics
        let business_metrics = if let Some(costs) = business_costs {
            calculate_business_metrics(cm, costs, n)
        } else {
            HashMap::new()
        };

        EvaluationResults {
            accuracy,
            precision,
            recall,
            f1_score: f1,
            roc_auc,
            confusion_matrix: cm,
            classification_report: report,
            calibration_score,
            fairness_metrics,
            business_metrics,
            feature_importance: None,
        }
    }

    /// Evaluate a regression model.
    ///
    /// Returns a map with keys: mse, rmse, mae, r2, mape.
    pub fn evaluate_regression(&self, y_true: &[f64], y_pred: &[f64]) -> HashMap<String, f64> {
        let mut metrics = HashMap::new();
        let mse_val = mean_squared_error(y_true, y_pred);
        metrics.insert("mse".into(), mse_val);
        metrics.insert("rmse".into(), mse_val.sqrt());
        metrics.insert("mae".into(), mean_absolute_error(y_true, y_pred));
        metrics.insert("r2".into(), r2_score(y_true, y_pred));
        metrics.insert(
            "mape".into(),
            mean_absolute_percentage_error(y_true, y_pred),
        );
        metrics
    }
}

impl Default for ModelEvaluator {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Metric Functions
// ---------------------------------------------------------------------------

/// Compute confusion matrix: [[TN, FP], [FN, TP]].
pub fn compute_confusion_matrix(y_true: &[f64], y_pred: &[f64]) -> [[usize; 2]; 2] {
    let mut cm = [[0usize; 2]; 2];
    for (&t, &p) in y_true.iter().zip(y_pred.iter()) {
        let ti = if t > 0.5 { 1 } else { 0 };
        let pi = if p > 0.5 { 1 } else { 0 };
        cm[ti][pi] += 1;
    }
    cm
}

/// Compute accuracy score.
pub fn accuracy_score(y_true: &[f64], y_pred: &[f64]) -> f64 {
    let correct = y_true
        .iter()
        .zip(y_pred.iter())
        .filter(|(&t, &p)| (t > 0.5) == (p > 0.5))
        .count();
    correct as f64 / y_true.len() as f64
}

/// Compute precision: TP / (TP + FP).
pub fn precision_score(tp: usize, fp: usize) -> f64 {
    let denom = tp + fp;
    if denom == 0 {
        0.0
    } else {
        tp as f64 / denom as f64
    }
}

/// Compute recall (sensitivity): TP / (TP + FN).
pub fn recall_score(tp: usize, fn_: usize) -> f64 {
    let denom = tp + fn_;
    if denom == 0 {
        0.0
    } else {
        tp as f64 / denom as f64
    }
}

/// Compute F1 score: 2 * precision * recall / (precision + recall).
pub fn f1_score(precision: f64, recall: f64) -> f64 {
    let denom = precision + recall;
    if denom == 0.0 {
        0.0
    } else {
        2.0 * precision * recall / denom
    }
}

/// Compute ROC AUC score using the trapezoidal rule.
pub fn roc_auc_score(y_true: &[f64], y_score: &[f64]) -> f64 {
    let n_pos = y_true.iter().filter(|&&v| v > 0.5).count();
    let n_neg = y_true.len() - n_pos;
    if n_pos == 0 || n_neg == 0 {
        return 0.5;
    }

    // Wilcoxon–Mann–Whitney U statistic: rank scores ascending (ties share
    // the average rank) and sum the ranks of the positive class.
    let mut pairs: Vec<(f64, f64)> = y_true
        .iter()
        .zip(y_score.iter())
        .map(|(&t, &s)| (s, t))
        .collect();
    pairs.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

    let n = pairs.len();
    let mut rank_sum_pos = 0.0f64;
    let mut i = 0usize;
    while i < n {
        let mut j = i;
        while j + 1 < n && (pairs[j + 1].0 - pairs[i].0).abs() <= f64::EPSILON {
            j += 1;
        }
        let avg_rank = ((i + 1) + (j + 1)) as f64 / 2.0;
        for (_, label) in &pairs[i..=j] {
            if *label > 0.5 {
                rank_sum_pos += avg_rank;
            }
        }
        i = j + 1;
    }

    let auc =
        (rank_sum_pos - n_pos as f64 * (n_pos as f64 + 1.0) / 2.0) / (n_pos as f64 * n_neg as f64);
    auc.clamp(0.0, 1.0)
}

/// Mean Squared Error.
pub fn mean_squared_error(y_true: &[f64], y_pred: &[f64]) -> f64 {
    let n = y_true.len() as f64;
    y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(&t, &p)| (t - p).powi(2))
        .sum::<f64>()
        / n
}

/// Mean Absolute Error.
pub fn mean_absolute_error(y_true: &[f64], y_pred: &[f64]) -> f64 {
    let n = y_true.len() as f64;
    y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(&t, &p)| (t - p).abs())
        .sum::<f64>()
        / n
}

/// R² (coefficient of determination) score.
pub fn r2_score(y_true: &[f64], y_pred: &[f64]) -> f64 {
    let mean_true = y_true.iter().sum::<f64>() / y_true.len() as f64;
    let ss_res: f64 = y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(&t, &p)| (t - p).powi(2))
        .sum();
    let ss_tot: f64 = y_true.iter().map(|&t| (t - mean_true).powi(2)).sum();
    if ss_tot == 0.0 {
        0.0
    } else {
        1.0 - ss_res / ss_tot
    }
}

/// Mean Absolute Percentage Error.
pub fn mean_absolute_percentage_error(y_true: &[f64], y_pred: &[f64]) -> f64 {
    let n = y_true.len() as f64;
    y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(&t, &p)| {
            if t.abs() < f64::EPSILON {
                0.0
            } else {
                ((t - p) / t).abs()
            }
        })
        .sum::<f64>()
        / n
        * 100.0
}

/// Evaluate calibration using Expected Calibration Error (ECE).
pub fn evaluate_calibration(y_true: &[f64], y_pred_proba: &[f64], n_bins: usize) -> f64 {
    let n = y_true.len();
    let _bin_indices: Vec<usize> = y_pred_proba
        .iter()
        .map(|&p| ((p * n_bins as f64).min((n_bins - 1) as f64)) as usize)
        .collect();

    // Sort by predicted probability for binning
    let mut pairs: Vec<(f64, f64)> = y_pred_proba
        .iter()
        .zip(y_true.iter())
        .map(|(&p, &t)| (p, t))
        .collect();
    pairs.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

    let mut ece = 0.0;
    let bin_size = n.div_ceil(n_bins);

    for bin in 0..n_bins {
        let start = bin * bin_size;
        let end = ((bin + 1) * bin_size).min(n);
        if start >= end {
            continue;
        }
        let slice = &pairs[start..end];
        let avg_pred: f64 = slice.iter().map(|(p, _)| p).sum::<f64>() / slice.len() as f64;
        let avg_true: f64 = slice.iter().map(|(_, t)| t).sum::<f64>() / slice.len() as f64;
        ece += (avg_pred - avg_true).abs() * slice.len() as f64 / n as f64;
    }

    ece
}

/// Evaluate fairness across protected attributes.
pub fn evaluate_fairness(
    y_true: &[f64],
    y_pred: &[f64],
    protected_attributes: &HashMap<String, Vec<f64>>,
) -> HashMap<String, f64> {
    let mut metrics = HashMap::new();

    for (attr_name, attr_values) in protected_attributes {
        let unique: Vec<f64> = {
            let mut v: Vec<f64> = attr_values.clone();
            v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            v.dedup();
            v
        };
        if unique.len() != 2 {
            continue;
        }

        let v0 = unique[0];
        let v1 = unique[1];

        let mask0: Vec<bool> = attr_values.iter().map(|&v| (v - v0).abs() < 0.5).collect();
        let mask1: Vec<bool> = attr_values.iter().map(|&v| (v - v1).abs() < 0.5).collect();

        let pred0: Vec<f64> = y_pred
            .iter()
            .zip(mask0.iter())
            .filter(|(_, &m)| m)
            .map(|(&p, _)| p)
            .collect();
        let pred1: Vec<f64> = y_pred
            .iter()
            .zip(mask1.iter())
            .filter(|(_, &m)| m)
            .map(|(&p, _)| p)
            .collect();

        if pred0.is_empty() || pred1.is_empty() {
            continue;
        }

        // Demographic parity
        let pos_rate_0 = pred0.iter().filter(|&&p| p > 0.5).count() as f64 / pred0.len() as f64;
        let pos_rate_1 = pred1.iter().filter(|&&p| p > 0.5).count() as f64 / pred1.len() as f64;
        metrics.insert(
            format!("{}_demographic_parity", attr_name),
            (pos_rate_0 - pos_rate_1).abs(),
        );

        // Confusion matrices for each group
        let cm0 = compute_confusion_matrix_for_subset(y_true, y_pred, &mask0);
        let cm1 = compute_confusion_matrix_for_subset(y_true, y_pred, &mask1);

        let fpr0 = if cm0[0][0] + cm0[0][1] > 0 {
            cm0[0][1] as f64 / (cm0[0][0] + cm0[0][1]) as f64
        } else {
            0.0
        };
        let fpr1 = if cm1[0][0] + cm1[0][1] > 0 {
            cm1[0][1] as f64 / (cm1[0][0] + cm1[0][1]) as f64
        } else {
            0.0
        };
        metrics.insert(format!("{}_fpr_difference", attr_name), (fpr0 - fpr1).abs());

        let tpr0 = if cm0[1][0] + cm0[1][1] > 0 {
            cm0[1][1] as f64 / (cm0[1][0] + cm0[1][1]) as f64
        } else {
            0.0
        };
        let tpr1 = if cm1[1][0] + cm1[1][1] > 0 {
            cm1[1][1] as f64 / (cm1[1][0] + cm1[1][1]) as f64
        } else {
            0.0
        };
        metrics.insert(format!("{}_tpr_difference", attr_name), (tpr0 - tpr1).abs());
    }

    metrics
}

fn compute_confusion_matrix_for_subset(
    y_true: &[f64],
    y_pred: &[f64],
    mask: &[bool],
) -> [[usize; 2]; 2] {
    let mut cm = [[0usize; 2]; 2];
    for ((&t, &p), &m) in y_true.iter().zip(y_pred.iter()).zip(mask.iter()) {
        if !m {
            continue;
        }
        let ti = if t > 0.5 { 1 } else { 0 };
        let pi = if p > 0.5 { 1 } else { 0 };
        cm[ti][pi] += 1;
    }
    cm
}

/// Calculate business impact metrics from a confusion matrix.
pub fn calculate_business_metrics(
    cm: [[usize; 2]; 2],
    costs: &HashMap<String, f64>,
    n: usize,
) -> HashMap<String, f64> {
    let (_tn, fp, fn_, tp) = (cm[0][0], cm[0][1], cm[1][0], cm[1][1]);

    let fp_cost = costs.get("false_positive_cost").copied().unwrap_or(0.0) * fp as f64;
    let fn_cost = costs.get("false_negative_cost").copied().unwrap_or(0.0) * fn_ as f64;
    let tp_benefit = costs.get("true_positive_benefit").copied().unwrap_or(0.0) * tp as f64;

    let total_cost = fp_cost + fn_cost;
    let net_benefit = tp_benefit - total_cost;
    let cost_per_prediction = if n > 0 { total_cost / n as f64 } else { 0.0 };

    let mut m = HashMap::new();
    m.insert("false_positive_cost".into(), fp_cost);
    m.insert("false_negative_cost".into(), fn_cost);
    m.insert("true_positive_benefit".into(), tp_benefit);
    m.insert("total_cost".into(), total_cost);
    m.insert("net_benefit".into(), net_benefit);
    m.insert("cost_per_prediction".into(), cost_per_prediction);
    m
}

// ---------------------------------------------------------------------------
// Utility: train/test split
// ---------------------------------------------------------------------------

/// Split data into training and test sets.
pub fn train_test_split(
    x: &ndarray::Array2<f64>,
    y: &ndarray::Array1<f64>,
    test_size: f64,
    seed: u64,
) -> (
    ndarray::Array2<f64>,
    ndarray::Array2<f64>,
    ndarray::Array1<f64>,
    ndarray::Array1<f64>,
) {
    use rand::seq::SliceRandom;
    use rand::SeedableRng;

    let n = x.nrows();
    let n_test = (n as f64 * test_size).ceil() as usize;
    let n_train = n - n_test;

    let mut indices: Vec<usize> = (0..n).collect();
    let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
    indices.shuffle(&mut rng);

    let train_idx: Vec<usize> = indices[..n_train].to_vec();
    let test_idx: Vec<usize> = indices[n_train..].to_vec();

    let n_cols = x.ncols();
    let mut x_train = ndarray::Array2::zeros((n_train, n_cols));
    let mut x_test = ndarray::Array2::zeros((n_test, n_cols));
    let mut y_train = ndarray::Array1::zeros(n_train);
    let mut y_test = ndarray::Array1::zeros(n_test);

    for (i, &idx) in train_idx.iter().enumerate() {
        x_train.row_mut(i).assign(&x.row(idx));
        y_train[i] = y[idx];
    }
    for (i, &idx) in test_idx.iter().enumerate() {
        x_test.row_mut(i).assign(&x.row(idx));
        y_test[i] = y[idx];
    }

    (x_train, x_test, y_train, y_test)
}

// ---------------------------------------------------------------------------
// Cross-Validation Helpers
// ---------------------------------------------------------------------------

/// Prepare training and testing fold data from indices.
pub fn prepare_fold_data(
    x: &ndarray::Array2<f64>,
    y: &[f64],
    train_idx: &[usize],
    test_idx: &[usize],
) -> (ndarray::Array2<f64>, Vec<f64>, ndarray::Array2<f64>) {
    let n_train = train_idx.len();
    let n_test = test_idx.len();
    let n_cols = x.ncols();

    let mut x_train = ndarray::Array2::zeros((n_train, n_cols));
    let mut y_train = Vec::with_capacity(n_train);
    let mut x_test = ndarray::Array2::zeros((n_test, n_cols));

    for (i, &idx) in train_idx.iter().enumerate() {
        x_train.row_mut(i).assign(&x.row(idx));
        y_train.push(y[idx]);
    }
    for (i, &idx) in test_idx.iter().enumerate() {
        x_test.row_mut(i).assign(&x.row(idx));
    }

    (x_train, y_train, x_test)
}

// ---------------------------------------------------------------------------
// Cross-Validation
// ---------------------------------------------------------------------------

/// Simple k-fold cross-validation for classification.
/// Uses the provided `train_and_predict` closure to train on a fold and return predictions.
pub fn cross_val_score_classification(
    x: &ndarray::Array2<f64>,
    y: &[f64],
    n_folds: usize,
    seed: u64,
    mut train_and_predict: impl FnMut(&ndarray::Array2<f64>, &[f64], &ndarray::Array2<f64>) -> Vec<f64>,
) -> Vec<f64> {
    use rand::seq::SliceRandom;
    use rand::SeedableRng;

    let n = x.nrows();
    let mut indices: Vec<usize> = (0..n).collect();
    let mut rng = rand::rngs::StdRng::seed_from_u64(seed);
    indices.shuffle(&mut rng);

    let fold_size = n.div_ceil(n_folds);
    let mut scores = Vec::with_capacity(n_folds);

    for fold in 0..n_folds {
        let test_start = fold * fold_size;
        let test_end = (test_start + fold_size).min(n);

        let test_idx: Vec<usize> = indices[test_start..test_end].to_vec();
        let train_idx: Vec<usize> = indices[..test_start]
            .iter()
            .chain(indices[test_end..].iter())
            .copied()
            .collect();

        let n_train = train_idx.len();
        let n_test = test_idx.len();
        let n_cols = x.ncols();

        let mut x_train = ndarray::Array2::zeros((n_train, n_cols));
        let mut y_train = Vec::with_capacity(n_train);
        let mut x_test = ndarray::Array2::zeros((n_test, n_cols));

        for (i, &idx) in train_idx.iter().enumerate() {
            x_train.row_mut(i).assign(&x.row(idx));
            y_train.push(y[idx]);
        }
        for (i, &idx) in test_idx.iter().enumerate() {
            x_test.row_mut(i).assign(&x.row(idx));
        }

        let preds = train_and_predict(&x_train, &y_train, &x_test);
        let correct = preds
            .iter()
            .zip(test_idx.iter())
            .filter(|(&p, &idx)| (p > 0.5) == (y[idx] > 0.5))
            .count();
        scores.push(correct as f64 / n_test as f64);
    }

    scores
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_accuracy_score_perfect() {
        let y_true = vec![1.0, 0.0, 1.0, 0.0];
        let y_pred = vec![1.0, 0.0, 1.0, 0.0];
        assert!((accuracy_score(&y_true, &y_pred) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_accuracy_score_half() {
        let y_true = vec![1.0, 0.0, 1.0, 0.0];
        let y_pred = vec![1.0, 0.0, 0.0, 0.0];
        assert!((accuracy_score(&y_true, &y_pred) - 0.75).abs() < 1e-10);
    }

    #[test]
    fn test_confusion_matrix() {
        let y_true = vec![1.0, 0.0, 1.0, 0.0, 1.0];
        let y_pred = vec![1.0, 1.0, 0.0, 0.0, 1.0];
        let cm = compute_confusion_matrix(&y_true, &y_pred);
        // TN=1 (idx1=0,pred=0), FP=1 (idx1=0,pred=1 -> actually idx1=0,pred=1 is FP)
        // Let me trace: (1,1)=TP, (0,1)=FP, (1,0)=FN, (0,0)=TN
        // idx0: t=1,p=1 → TP
        // idx1: t=0,p=1 → FP
        // idx2: t=1,p=0 → FN
        // idx3: t=0,p=0 → TN
        // idx4: t=1,p=1 → TP
        assert_eq!(cm[0][0], 1); // TN
        assert_eq!(cm[0][1], 1); // FP
        assert_eq!(cm[1][0], 1); // FN
        assert_eq!(cm[1][1], 2); // TP
    }

    #[test]
    fn test_precision_recall_f1() {
        let p = precision_score(10, 5);
        let r = recall_score(10, 3);
        let f1 = f1_score(p, r);
        assert!((p - 10.0 / 15.0).abs() < 1e-10);
        assert!((r - 10.0 / 13.0).abs() < 1e-10);
        assert!(f1 > 0.0);
    }

    #[test]
    fn test_mse() {
        let y_true = vec![2.0, 4.0, 6.0];
        let y_pred = vec![2.5, 3.5, 6.5];
        let mse = mean_squared_error(&y_true, &y_pred);
        // (0.25 + 0.25 + 0.25) / 3 = 0.25
        assert!((mse - 0.25).abs() < 1e-10);
    }

    #[test]
    fn test_r2_perfect() {
        let y_true = vec![1.0, 2.0, 3.0];
        let y_pred = vec![1.0, 2.0, 3.0];
        assert!((r2_score(&y_true, &y_pred) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_train_test_split() {
        let x = ndarray::array![[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]];
        let y = ndarray::array![0.0, 0.0, 1.0, 1.0, 0.0, 0.0];
        let (x_tr, x_te, y_tr, y_te) = train_test_split(&x, &y, 0.33, 42);
        assert_eq!(x_tr.nrows() + x_te.nrows(), 6);
        assert_eq!(y_tr.len() + y_te.len(), 6);
    }

    #[test]
    fn test_cross_val_score() {
        let x = ndarray::array![
            [1.0, 2.0],
            [2.0, 3.0],
            [3.0, 4.0],
            [4.0, 5.0],
            [5.0, 6.0],
            [6.0, 7.0],
        ];
        let y = vec![0.0, 0.0, 0.0, 1.0, 1.0, 1.0];
        let scores = cross_val_score_classification(&x, &y, 3, 42, |_x_tr, y_tr, x_te| {
            // Simple baseline: predict majority class
            let majority = if y_tr.iter().filter(|&&v| v > 0.5).count() > y_tr.len() / 2 {
                1.0
            } else {
                0.0
            };
            vec![majority; x_te.nrows()]
        });
        assert_eq!(scores.len(), 3);
    }

    #[test]
    fn test_evaluate_classifier() {
        let evaluator = ModelEvaluator::new();
        let y_true = vec![1.0, 0.0, 1.0, 0.0, 1.0, 0.0];
        let y_pred = vec![1.0, 0.0, 1.0, 0.0, 1.0, 1.0];
        let results = evaluator.evaluate_classifier(&y_true, &y_pred, None, None, None);
        assert!((results.accuracy - 5.0 / 6.0).abs() < 1e-10);
        assert!(results.f1_score > 0.0);
        assert!(results.roc_auc.is_none());
    }

    #[test]
    fn test_evaluate_regression() {
        let evaluator = ModelEvaluator::new();
        let y_true = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y_pred = vec![1.1, 1.9, 3.2, 3.8, 5.1];
        let metrics = evaluator.evaluate_regression(&y_true, &y_pred);
        assert!(metrics.contains_key("mse"));
        assert!(metrics.contains_key("r2"));
        assert!(metrics["r2"] > 0.9);
    }

    #[test]
    fn test_business_metrics() {
        let cm = [[10, 2], [3, 15]];
        let mut costs = HashMap::new();
        costs.insert("false_positive_cost".into(), 100.0);
        costs.insert("false_negative_cost".into(), 500.0);
        costs.insert("true_positive_benefit".into(), 200.0);
        let metrics = calculate_business_metrics(cm, &costs, 30);
        assert_eq!(metrics["false_positive_cost"], 200.0);
        assert_eq!(metrics["false_negative_cost"], 1500.0);
        assert_eq!(metrics["true_positive_benefit"], 3000.0);
    }

    #[test]
    fn test_roc_auc_score() {
        let y_true = vec![0.0, 0.0, 1.0, 1.0];
        let y_score = vec![0.1, 0.4, 0.35, 0.8];
        let auc = roc_auc_score(&y_true, &y_score);
        assert!(auc > 0.5); // Should be better than random
    }

    #[test]
    fn test_evaluate_calibration() {
        let y_true = vec![1.0, 0.0, 1.0, 0.0, 1.0];
        let y_proba = vec![0.9, 0.1, 0.8, 0.2, 0.7];
        let ece = evaluate_calibration(&y_true, &y_proba, 5);
        assert!(ece >= 0.0);
    }
}

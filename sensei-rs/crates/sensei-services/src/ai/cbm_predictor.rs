//! Condition-Based Maintenance (CBM) Predictor.
//!
//! Suggests preventive maintenance actions based on:
//! - Equipment condition monitoring data
//! - Historical failure patterns
//! - Operating hours and cycles
//! - Environmental factors (temperature, vibration, pressure, etc.)
//! - Anomaly detection using statistical methods
//! - Rule-based thresholds for critical parameters

use chrono::{DateTime, Duration, Utc};
use ndarray::Array1;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

/// Errors that can occur during CBM operations.
#[derive(Debug, thiserror::Error)]
pub enum CbmError {
    #[error("Model not trained: {0}")]
    ModelNotTrained(String),
    #[error("Insufficient data: {0}")]
    InsufficientData(String),
    #[error("Computation error: {0}")]
    Computation(String),
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Critical thresholds for immediate action.
pub const CRITICAL_THRESHOLDS: &[(&str, f64, &str)] = &[
    ("temperature", 80.0, "°C"),
    ("vibration", 10.0, "mm/s"),
    ("pressure", 150.0, "psi"),
    ("current", 20.0, "A"),
    ("noise", 85.0, "dB"),
];

/// Feature names for CBM predictor.
pub const CBM_FEATURE_NAMES: &[&str] = &[
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
];

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A single condition reading from an equipment sensor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConditionReading {
    pub equipment_id: String,
    pub timestamp: DateTime<Utc>,
    pub temperature: Option<f64>,
    pub vibration: Option<f64>,
    pub pressure: Option<f64>,
    pub current: Option<f64>,
    pub noise: Option<f64>,
    pub operating_hours: Option<f64>,
}

/// A maintenance record for equipment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenanceRecord {
    pub equipment_id: String,
    pub date: DateTime<Utc>,
    pub maintenance_type: String, // "repair", "breakdown", "preventive", "inspection"
}

/// Equipment asset information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Equipment {
    pub id: String,
    pub installation_date: Option<DateTime<Utc>>,
    pub operating_hours: Option<f64>,
    pub cycles: Option<f64>,
}

/// Prediction result for maintenance needs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenancePrediction {
    pub risk_level: String, // "low", "medium", "high", "critical", "unknown"
    pub failure_probability: f64,
    pub is_anomaly: bool,
    pub recommendations: Vec<Recommendation>,
    pub reasons: Vec<String>,
    pub estimated_time_to_failure: Option<i64>, // days
}

/// A single maintenance recommendation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recommendation {
    pub action: String,
    pub reason: String,
    pub parameter: Option<String>,
    pub value: Option<f64>,
}

/// Training metrics returned after model training.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingMetrics {
    /// Mean accuracy over the seeded 3-fold cross-validation (train/test
    /// splits are real; the per-fold metric is accuracy, NOT F1).
    pub cv_accuracy_mean: f64,
    pub cv_accuracy_std: f64,
    pub training_samples: usize,
    pub error: Option<String>,
}

// ---------------------------------------------------------------------------
// StandardScaler (manual ndarray implementation)
// ---------------------------------------------------------------------------

/// Manual implementation of sklearn's StandardScaler.
#[derive(Debug, Clone)]
pub struct StandardScaler {
    pub mean: Option<Array1<f64>>,
    pub std: Option<Array1<f64>>,
    pub n_samples_seen: usize,
}

impl StandardScaler {
    pub fn new() -> Self {
        Self {
            mean: None,
            std: None,
            n_samples_seen: 0,
        }
    }

    /// Fit the scaler on data (rows = samples, cols = features).
    pub fn fit(&mut self, x: &ndarray::Array2<f64>) -> Result<(), CbmError> {
        let n_samples = x.nrows();
        if n_samples == 0 {
            return Err(CbmError::InsufficientData(
                "No samples provided for fit".into(),
            ));
        }
        let n_features = x.ncols();

        let mut mean = Array1::zeros(n_features);
        let mut std = Array1::zeros(n_features);

        for j in 0..n_features {
            let col: Vec<f64> = x.column(j).iter().copied().collect();
            let col_mean = col.iter().sum::<f64>() / n_samples as f64;
            let variance =
                col.iter().map(|&v| (v - col_mean).powi(2)).sum::<f64>() / n_samples as f64;
            mean[j] = col_mean;
            std[j] = variance.sqrt().max(f64::EPSILON);
        }

        self.mean = Some(mean);
        self.std = Some(std);
        self.n_samples_seen = n_samples;
        Ok(())
    }

    /// Transform data using fitted parameters.
    pub fn transform(&self, x: &ndarray::Array2<f64>) -> Result<ndarray::Array2<f64>, CbmError> {
        let mean = self
            .mean
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("Scaler not fitted".into()))?;
        let std = self
            .std
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("Scaler not fitted".into()))?;

        let (n_rows, n_cols) = (x.nrows(), x.ncols());
        let mut result = ndarray::Array2::zeros((n_rows, n_cols));

        for i in 0..n_rows {
            for j in 0..n_cols {
                result[[i, j]] = (x[[i, j]] - mean[j]) / std[j];
            }
        }

        Ok(result)
    }

    /// Fit and transform in one step.
    pub fn fit_transform(
        &mut self,
        x: &ndarray::Array2<f64>,
    ) -> Result<ndarray::Array2<f64>, CbmError> {
        self.fit(x)?;
        self.transform(x)
    }

    /// Transform a single feature vector (1D array).
    pub fn transform_single(&self, features: &[f64]) -> Result<Vec<f64>, CbmError> {
        let mean = self
            .mean
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("Scaler not fitted".into()))?;
        let std = self
            .std
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("Scaler not fitted".into()))?;

        Ok(features
            .iter()
            .enumerate()
            .map(|(j, &v)| (v - mean[j]) / std[j])
            .collect())
    }

    /// Inverse transform (for explainability).
    pub fn inverse_transform(
        &self,
        x: &ndarray::Array2<f64>,
    ) -> Result<ndarray::Array2<f64>, CbmError> {
        let mean = self
            .mean
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("Scaler not fitted".into()))?;
        let std = self
            .std
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("Scaler not fitted".into()))?;

        let (n_rows, n_cols) = (x.nrows(), x.ncols());
        let mut result = ndarray::Array2::zeros((n_rows, n_cols));

        for i in 0..n_rows {
            for j in 0..n_cols {
                result[[i, j]] = x[[i, j]] * std[j] + mean[j];
            }
        }

        Ok(result)
    }
}

impl Default for StandardScaler {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Anomaly Detector (Isolation-Forest-style using statistical methods)
// ---------------------------------------------------------------------------

/// Statistical anomaly detector (conceptual equivalent of IsolationForest).
///
/// Uses z-score and interquartile range methods to detect outliers.
#[derive(Debug, Clone)]
pub struct AnomalyDetector {
    /// Per-feature means (fitted)
    pub feature_means: Option<Array1<f64>>,
    /// Per-feature stds (fitted)
    pub feature_stds: Option<Array1<f64>>,
    /// Z-score threshold for anomaly detection
    pub zscore_threshold: f64,
    /// Expected contamination rate (for scoring)
    pub contamination: f64,
}

impl AnomalyDetector {
    pub fn new(contamination: f64, zscore_threshold: f64) -> Self {
        Self {
            feature_means: None,
            feature_stds: None,
            zscore_threshold,
            contamination,
        }
    }

    /// Fit the anomaly detector on training data.
    pub fn fit(&mut self, x: &ndarray::Array2<f64>) -> Result<(), CbmError> {
        let n_samples = x.nrows();
        if n_samples == 0 {
            return Err(CbmError::InsufficientData(
                "No samples for anomaly detector fit".into(),
            ));
        }
        let n_features = x.ncols();

        let mut means = Array1::zeros(n_features);
        let mut stds = Array1::zeros(n_features);

        for j in 0..n_features {
            let col: Vec<f64> = x.column(j).iter().copied().collect();
            let m = col.iter().sum::<f64>() / n_samples as f64;
            let variance = col.iter().map(|&v| (v - m).powi(2)).sum::<f64>() / n_samples as f64;
            means[j] = m;
            stds[j] = variance.sqrt().max(f64::EPSILON);
        }

        self.feature_means = Some(means);
        self.feature_stds = Some(stds);
        Ok(())
    }

    /// Predict anomaly scores for samples.
    /// Returns scores where positive = anomaly (similar to IsolationForest where -1 = anomaly).
    /// Score > 0 means anomalous, score ≤ 0 means normal.
    pub fn predict(&self, x: &ndarray::Array2<f64>) -> Result<Vec<f64>, CbmError> {
        let means = self
            .feature_means
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("AnomalyDetector not fitted".into()))?;
        let stds = self
            .feature_stds
            .as_ref()
            .ok_or_else(|| CbmError::ModelNotTrained("AnomalyDetector not fitted".into()))?;

        let mut scores = Vec::with_capacity(x.nrows());
        for i in 0..x.nrows() {
            let mut max_z = 0.0_f64;
            for j in 0..x.ncols() {
                let z = ((x[[i, j]] - means[j]) / stds[j]).abs();
                max_z = max_z.max(z);
            }
            // Score > 0 if any feature exceeds z-score threshold
            scores.push(if max_z > self.zscore_threshold {
                max_z / self.zscore_threshold - 1.0
            } else {
                -(1.0 - max_z / self.zscore_threshold)
            });
        }
        Ok(scores)
    }

    /// Binary anomaly prediction: true = anomaly.
    pub fn predict_binary(&self, x: &ndarray::Array2<f64>) -> Result<Vec<bool>, CbmError> {
        let scores = self.predict(x)?;
        Ok(scores.iter().map(|&s| s > 0.0).collect())
    }
}

impl Default for AnomalyDetector {
    fn default() -> Self {
        Self::new(0.1, 3.0)
    }
}

// ---------------------------------------------------------------------------
// Failure Predictor (Random-Forest-style ensemble)
// ---------------------------------------------------------------------------

/// Simple decision stump: a single-feature threshold classifier.
#[derive(Debug, Clone)]
struct DecisionStump {
    feature_idx: usize,
    threshold: f64,
    left_pred: f64,  // prediction when value <= threshold
    right_pred: f64, // prediction when value > threshold
    weight: f64,     // ensemble weight
}

/// Simple ensemble classifier (conceptual equivalent of RandomForest).
///
/// Uses a collection of random decision stumps trained via bootstrap sampling.
#[derive(Debug, Clone)]
pub struct EnsembleClassifier {
    stumps: Vec<DecisionStump>,
    n_features: usize,
    n_estimators: usize,
    max_depth: usize,
}

impl EnsembleClassifier {
    pub fn new(n_estimators: usize, max_depth: usize) -> Self {
        Self {
            stumps: Vec::new(),
            n_features: 0,
            n_estimators,
            max_depth,
        }
    }

    /// Train the ensemble on labeled data.
    pub fn fit(&mut self, x: &ndarray::Array2<f64>, y: &[f64]) -> Result<(), CbmError> {
        use rand::Rng;

        let n_samples = x.nrows();
        let n_features = x.ncols();
        if n_samples == 0 {
            return Err(CbmError::InsufficientData("No samples for training".into()));
        }
        self.n_features = n_features;

        let mut rng = rand::thread_rng();
        self.stumps.clear();

        for _ in 0..self.n_estimators {
            // Bootstrap sample
            let mut bootstrap_x = Vec::new();
            let mut bootstrap_y = Vec::new();
            for _ in 0..n_samples {
                let idx = rng.gen_range(0..n_samples);
                bootstrap_x.push(x.row(idx).to_vec());
                bootstrap_y.push(y[idx]);
            }

            // Train a decision stump on a random feature
            let feat_idx = rng.gen_range(0..n_features);

            // Find best threshold on this feature
            let mut best_threshold = 0.0;
            let mut best_gini = f64::MAX;
            let mut best_left_pred = 0.0;
            let mut best_right_pred = 0.0;

            // Sample random thresholds
            let col_vals: Vec<f64> = bootstrap_x.iter().map(|row| row[feat_idx]).collect();
            let min_v = col_vals.iter().cloned().fold(f64::MAX, f64::min);
            let max_v = col_vals.iter().cloned().fold(f64::MIN, f64::max);

            // Search `max_depth` random threshold candidates per stump; a
            // larger depth explores more of the feature range per stump.
            for _ in 0..self.max_depth.max(1) {
                let threshold = rng.gen_range(min_v..=max_v);

                let mut left_true = 0usize;
                let mut left_total = 0usize;
                let mut right_true = 0usize;
                let mut right_total = 0usize;

                for (row, &label) in bootstrap_x.iter().zip(bootstrap_y.iter()) {
                    if row[feat_idx] <= threshold {
                        left_total += 1;
                        if label > 0.5 {
                            left_true += 1;
                        }
                    } else {
                        right_total += 1;
                        if label > 0.5 {
                            right_true += 1;
                        }
                    }
                }

                // Gini impurity
                let gini_left = if left_total == 0 {
                    0.0
                } else {
                    let p = left_true as f64 / left_total as f64;
                    1.0 - p * p - (1.0 - p) * (1.0 - p)
                };
                let gini_right = if right_total == 0 {
                    0.0
                } else {
                    let p = right_true as f64 / right_total as f64;
                    1.0 - p * p - (1.0 - p) * (1.0 - p)
                };
                let gini = (left_total as f64 / n_samples as f64) * gini_left
                    + (right_total as f64 / n_samples as f64) * gini_right;

                if gini < best_gini {
                    best_gini = gini;
                    best_threshold = threshold;
                    best_left_pred = if left_total > 0 {
                        left_true as f64 / left_total as f64
                    } else {
                        0.0
                    };
                    best_right_pred = if right_total > 0 {
                        right_true as f64 / right_total as f64
                    } else {
                        0.0
                    };
                }
            }

            self.stumps.push(DecisionStump {
                feature_idx: feat_idx,
                threshold: best_threshold,
                left_pred: best_left_pred,
                right_pred: best_right_pred,
                weight: 1.0 / self.n_estimators as f64,
            });
        }

        Ok(())
    }

    /// Predict probabilities for the positive class.
    pub fn predict_proba(&self, x: &ndarray::Array2<f64>) -> Result<Vec<f64>, CbmError> {
        if self.stumps.is_empty() {
            return Err(CbmError::ModelNotTrained("Ensemble not fitted".into()));
        }

        let mut probas = Vec::with_capacity(x.nrows());
        for i in 0..x.nrows() {
            let mut prob = 0.0;
            for stump in &self.stumps {
                if x[[i, stump.feature_idx]] <= stump.threshold {
                    prob += stump.left_pred * stump.weight;
                } else {
                    prob += stump.right_pred * stump.weight;
                }
            }
            probas.push(prob);
        }
        Ok(probas)
    }

    /// Predict binary labels.
    pub fn predict(&self, x: &ndarray::Array2<f64>) -> Result<Vec<f64>, CbmError> {
        let probas = self.predict_proba(x)?;
        Ok(probas
            .iter()
            .map(|&p| if p > 0.5 { 1.0 } else { 0.0 })
            .collect())
    }

    /// Get feature importances (how often each feature is used by stumps).
    pub fn feature_importances(&self, n_features: usize) -> Vec<f64> {
        let mut counts = vec![0usize; n_features];
        for stump in &self.stumps {
            if stump.feature_idx < n_features {
                counts[stump.feature_idx] += 1;
            }
        }
        let total = counts.iter().sum::<usize>().max(1) as f64;
        counts.iter().map(|&c| c as f64 / total).collect()
    }
}

// ---------------------------------------------------------------------------
// Condition-Based Maintenance Predictor
// ---------------------------------------------------------------------------

/// ML model for condition-based maintenance predictions.
///
/// Combines:
/// 1. Anomaly detection (statistical) for sensor data
/// 2. Failure prediction (ensemble classifier) based on historical patterns
/// 3. Rule-based thresholds for critical parameters
#[derive(Debug, Clone)]
pub struct ConditionBasedMaintenancePredictor {
    /// Failure prediction ensemble
    pub failure_classifier: Option<EnsembleClassifier>,
    /// Anomaly detector
    pub anomaly_detector: Option<AnomalyDetector>,
    /// Feature normalizer
    pub scaler: Option<StandardScaler>,
    /// Feature names
    pub feature_names: Vec<String>,
    /// Whether the model has been trained
    pub is_trained: bool,
}

impl Default for ConditionBasedMaintenancePredictor {
    fn default() -> Self {
        Self::new()
    }
}

impl ConditionBasedMaintenancePredictor {
    pub fn new() -> Self {
        Self {
            failure_classifier: None,
            anomaly_detector: None,
            scaler: None,
            feature_names: CBM_FEATURE_NAMES.iter().map(|&s| s.to_string()).collect(),
            is_trained: false,
        }
    }

    /// Train the CBM prediction models.
    ///
    /// `equipment_list`: List of equipment assets.
    /// `maintenance_records`: Historical maintenance records.
    /// `condition_readings`: Historical condition readings.
    pub fn train(
        &mut self,
        equipment_list: &[Equipment],
        maintenance_records: &[MaintenanceRecord],
        condition_readings: &[ConditionReading],
    ) -> Result<TrainingMetrics, CbmError> {
        // Build training dataset
        let (x_train, y_train) =
            self.build_training_data(equipment_list, maintenance_records, condition_readings)?;

        if x_train.nrows() < 10 {
            return Ok(TrainingMetrics {
                cv_accuracy_mean: 0.0,
                cv_accuracy_std: 0.0,
                training_samples: x_train.nrows(),
                error: Some("insufficient_data".into()),
            });
        }

        // Normalize features
        let mut scaler = StandardScaler::new();
        let x_scaled = scaler.fit_transform(&x_train)?;
        self.scaler = Some(scaler);

        // Train failure predictor
        let mut classifier = EnsembleClassifier::new(200, 15);
        classifier.fit(&x_scaled, &y_train)?;
        self.failure_classifier = Some(classifier);

        // Train anomaly detector
        let mut detector = AnomalyDetector::new(0.1, 3.0);
        detector.fit(&x_scaled)?;
        self.anomaly_detector = Some(detector);

        // Cross-validation (simple 3-fold)
        let cv_scores = self.cross_val_score(&x_scaled, &y_train, 3)?;
        let cv_accuracy_mean = cv_scores.iter().sum::<f64>() / cv_scores.len() as f64;
        let cv_accuracy_std = if cv_scores.len() > 1 {
            let variance = cv_scores
                .iter()
                .map(|&s| (s - cv_accuracy_mean).powi(2))
                .sum::<f64>()
                / (cv_scores.len() - 1) as f64;
            variance.sqrt()
        } else {
            0.0
        };

        self.is_trained = true;

        Ok(TrainingMetrics {
            cv_accuracy_mean,
            cv_accuracy_std,
            training_samples: x_train.nrows(),
            error: None,
        })
    }

    /// Predict maintenance needs for a piece of equipment.
    pub fn predict_maintenance_needs(
        &self,
        equipment: &Equipment,
        recent_readings: &[ConditionReading],
        maintenance_history: &[MaintenanceRecord],
    ) -> MaintenancePrediction {
        if recent_readings.is_empty() {
            return MaintenancePrediction {
                risk_level: "unknown".into(),
                failure_probability: 0.0,
                is_anomaly: false,
                recommendations: vec![],
                reasons: vec!["No condition data available".into()],
                estimated_time_to_failure: None,
            };
        }

        // Check critical thresholds first
        let critical_issues = self.check_critical_thresholds(recent_readings);
        if !critical_issues.is_empty() {
            return MaintenancePrediction {
                risk_level: "critical".into(),
                failure_probability: 1.0,
                is_anomaly: true,
                recommendations: critical_issues
                    .iter()
                    .map(|issue| Recommendation {
                        action: "immediate_shutdown".into(),
                        reason: issue.reason.clone(),
                        parameter: Some(issue.parameter.clone()),
                        value: Some(issue.value),
                    })
                    .collect(),
                reasons: critical_issues.iter().map(|i| i.reason.clone()).collect(),
                estimated_time_to_failure: Some(0),
            };
        }

        // Extract features
        let features = self.extract_features(equipment, recent_readings, maintenance_history);

        // ML predictions
        if let (Some(ref classifier), Some(ref scaler), Some(ref detector)) = (
            &self.failure_classifier,
            &self.scaler,
            &self.anomaly_detector,
        ) {
            let features_arr =
                ndarray::Array2::from_shape_vec((1, features.len()), features.clone())
                    .unwrap_or_else(|_| ndarray::Array2::zeros((1, features.len())));
            let x_scaled = match scaler.transform(&features_arr) {
                Ok(x) => x,
                Err(_) => {
                    return self.rule_based_assessment(
                        equipment,
                        recent_readings,
                        maintenance_history,
                    );
                }
            };

            let failure_prob = match classifier.predict_proba(&x_scaled) {
                Ok(probs) => probs[0],
                Err(_) => 0.5,
            };

            let anomaly_scores = match detector.predict(&x_scaled) {
                Ok(scores) => scores,
                Err(_) => vec![0.0],
            };
            let is_anomaly = anomaly_scores[0] > 0.0;

            let risk_level = if failure_prob >= 0.8 || is_anomaly {
                "high"
            } else if failure_prob >= 0.5 {
                "medium"
            } else {
                "low"
            };

            let recommendations = self.generate_recommendations(
                equipment,
                recent_readings,
                maintenance_history,
                failure_prob,
                is_anomaly,
            );

            let ttf = self.estimate_time_to_failure(failure_prob, equipment, maintenance_history);

            let reasons = self.explain_prediction(&features, recent_readings);

            MaintenancePrediction {
                risk_level: risk_level.into(),
                failure_probability: failure_prob,
                is_anomaly,
                recommendations,
                reasons,
                estimated_time_to_failure: ttf,
            }
        } else {
            self.rule_based_assessment(equipment, recent_readings, maintenance_history)
        }
    }

    // -----------------------------------------------------------------------
    // Internal helpers
    // -----------------------------------------------------------------------

    /// Check if recent readings exceed critical thresholds.
    fn check_critical_thresholds(&self, readings: &[ConditionReading]) -> Vec<CriticalIssue> {
        let mut issues = Vec::new();
        if let Some(latest) = readings.last() {
            for &(param, threshold, _unit) in CRITICAL_THRESHOLDS {
                let value = match param {
                    "temperature" => latest.temperature,
                    "vibration" => latest.vibration,
                    "pressure" => latest.pressure,
                    "current" => latest.current,
                    "noise" => latest.noise,
                    _ => None,
                };
                if let Some(v) = value {
                    if v > threshold {
                        issues.push(CriticalIssue {
                            parameter: param.to_string(),
                            value: v,
                            reason: format!(
                                "{} ({:.1}) exceeds critical threshold ({:.1})",
                                param, v, threshold
                            ),
                        });
                    }
                }
            }
        }
        issues
    }

    /// Build training dataset from historical data.
    fn build_training_data(
        &self,
        equipment_list: &[Equipment],
        maintenance_records: &[MaintenanceRecord],
        condition_readings: &[ConditionReading],
    ) -> Result<(ndarray::Array2<f64>, Vec<f64>), CbmError> {
        // Group readings and maintenance by equipment
        let mut eq_readings: HashMap<String, Vec<&ConditionReading>> = HashMap::new();
        let mut eq_maintenance: HashMap<String, Vec<&MaintenanceRecord>> = HashMap::new();

        for reading in condition_readings {
            eq_readings
                .entry(reading.equipment_id.clone())
                .or_default()
                .push(reading);
        }
        for record in maintenance_records {
            eq_maintenance
                .entry(record.equipment_id.clone())
                .or_default()
                .push(record);
        }

        let mut x_rows = Vec::new();
        let mut y_labels = Vec::new();

        for equipment in equipment_list {
            let readings = match eq_readings.get(&equipment.id) {
                Some(r) => r,
                None => continue,
            };
            let maintenance = eq_maintenance
                .get(&equipment.id)
                .cloned()
                .unwrap_or_default();

            if readings.len() < 2 {
                continue;
            }

            // Create samples from each reading point
            for i in 0..readings.len() - 1 {
                let reading = readings[i];
                let historical: Vec<&ConditionReading> = readings[..=i].to_vec();
                let historical_maint: Vec<&MaintenanceRecord> = maintenance
                    .iter()
                    .filter(|m| m.date <= reading.timestamp)
                    .copied()
                    .collect();

                let features = self.extract_raw_features(
                    equipment,
                    &historical
                        .iter()
                        .map(|cr| (*cr).clone())
                        .collect::<Vec<_>>(),
                    &historical_maint
                        .iter()
                        .map(|mr| (*mr).clone())
                        .collect::<Vec<_>>(),
                );

                // Label: was there a failure within next 7 days?
                let future_date = reading.timestamp + Duration::days(7);
                let has_future_failure = maintenance.iter().any(|m| {
                    m.date > reading.timestamp
                        && m.date <= future_date
                        && (m.maintenance_type == "repair" || m.maintenance_type == "breakdown")
                });

                x_rows.push(features);
                y_labels.push(if has_future_failure { 1.0 } else { 0.0 });
            }
        }

        if x_rows.is_empty() {
            return Err(CbmError::InsufficientData(
                "No training samples could be generated".into(),
            ));
        }

        let n_features = x_rows[0].len();
        let n_samples = x_rows.len();
        let mut x_arr = ndarray::Array2::zeros((n_samples, n_features));
        for (i, row) in x_rows.iter().enumerate() {
            for (j, &val) in row.iter().enumerate() {
                x_arr[[i, j]] = val;
            }
        }

        Ok((x_arr, y_labels))
    }

    /// Extract feature vector for ML models.
    fn extract_features(
        &self,
        equipment: &Equipment,
        recent_readings: &[ConditionReading],
        maintenance_history: &[MaintenanceRecord],
    ) -> Vec<f64> {
        self.extract_raw_features(equipment, recent_readings, maintenance_history)
    }

    /// Raw feature extraction (used by both training and prediction).
    fn extract_raw_features(
        &self,
        equipment: &Equipment,
        recent_readings: &[ConditionReading],
        maintenance_history: &[MaintenanceRecord],
    ) -> Vec<f64> {
        let mut features = Vec::with_capacity(18);

        // 1. Latest sensor readings (6 features)
        let latest = recent_readings.last();
        features.push(latest.and_then(|r| r.temperature).unwrap_or(0.0));
        features.push(latest.and_then(|r| r.vibration).unwrap_or(0.0));
        features.push(latest.and_then(|r| r.pressure).unwrap_or(0.0));
        features.push(latest.and_then(|r| r.current).unwrap_or(0.0));
        features.push(latest.and_then(|r| r.noise).unwrap_or(0.0));
        features.push(latest.and_then(|r| r.operating_hours).unwrap_or(0.0));

        // 2. Statistical features over recent readings (12 features)
        let _n_readings = recent_readings.len();

        // Temperature mean and std
        let temps: Vec<f64> = recent_readings
            .iter()
            .filter_map(|r| r.temperature)
            .collect();
        let (t_mean, t_std) = compute_mean_std(&temps);
        features.push(t_mean);
        features.push(t_std);

        // Vibration mean and std
        let vibs: Vec<f64> = recent_readings.iter().filter_map(|r| r.vibration).collect();
        let (v_mean, v_std) = compute_mean_std(&vibs);
        features.push(v_mean);
        features.push(v_std);

        // Temperature trend (slope of last N readings)
        let temp_trend = if temps.len() >= 2 {
            compute_slope(&temps)
        } else {
            0.0
        };
        features.push(temp_trend);

        // Vibration trend
        let vib_trend = if vibs.len() >= 2 {
            compute_slope(&vibs)
        } else {
            0.0
        };
        features.push(vib_trend);

        // Equipment age in days
        let age_days = equipment
            .installation_date
            .map(|d| (Utc::now() - d).num_days() as f64)
            .unwrap_or(0.0);
        features.push(age_days);

        // Total operating hours
        features.push(equipment.operating_hours.unwrap_or(0.0));

        // Total cycles
        features.push(equipment.cycles.unwrap_or(0.0));

        // Days since last maintenance
        let last_maint_date = maintenance_history
            .iter()
            .map(|m| m.date)
            .max()
            .unwrap_or(Utc::now());
        let days_since_maint = (Utc::now() - last_maint_date).num_days().max(0) as f64;
        features.push(days_since_maint);

        // Maintenance count
        features.push(maintenance_history.len() as f64);

        // Average maintenance interval
        let avg_interval = if maintenance_history.len() >= 2 {
            let mut dates: Vec<DateTime<Utc>> =
                maintenance_history.iter().map(|m| m.date).collect();
            dates.sort();
            let intervals: Vec<i64> = dates.windows(2).map(|w| (w[1] - w[0]).num_days()).collect();
            if !intervals.is_empty() {
                intervals.iter().sum::<i64>() as f64 / intervals.len() as f64
            } else {
                0.0
            }
        } else {
            0.0
        };
        features.push(avg_interval);

        features
    }

    /// Simple cross-validation scoring.
    fn cross_val_score(
        &self,
        x: &ndarray::Array2<f64>,
        y: &[f64],
        n_folds: usize,
    ) -> Result<Vec<f64>, CbmError> {
        use rand::seq::SliceRandom;
        use rand::SeedableRng;

        let n = x.nrows();
        let mut indices: Vec<usize> = (0..n).collect();
        let mut rng = rand::rngs::StdRng::seed_from_u64(42);
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

            // Build train/test arrays
            let (x_train, y_train, x_test) =
                crate::ai::evaluation::prepare_fold_data(x, y, &train_idx, &test_idx);

            // Train a small ensemble on this fold
            let mut clf = EnsembleClassifier::new(50, 10);
            if clf.fit(&x_train, &y_train).is_err() {
                continue;
            }
            let preds = clf.predict(&x_test).unwrap_or_default();

            let correct = preds
                .iter()
                .zip(test_idx.iter())
                .filter(|(&p, &idx)| (p > 0.5) == (y[idx] > 0.5))
                .count();
            scores.push(correct as f64 / test_idx.len() as f64);
        }

        Ok(scores)
    }

    /// Generate maintenance recommendations based on model outputs.
    fn generate_recommendations(
        &self,
        _equipment: &Equipment,
        recent_readings: &[ConditionReading],
        _maintenance_history: &[MaintenanceRecord],
        failure_prob: f64,
        is_anomaly: bool,
    ) -> Vec<Recommendation> {
        let mut recs = Vec::new();

        if failure_prob >= 0.8 {
            recs.push(Recommendation {
                action: "schedule_immediate_inspection".into(),
                reason: format!("High failure probability ({:.1}%)", failure_prob * 100.0),
                parameter: None,
                value: None,
            });
        } else if failure_prob >= 0.5 {
            recs.push(Recommendation {
                action: "schedule_preventive_maintenance".into(),
                reason: format!(
                    "Elevated failure probability ({:.1}%)",
                    failure_prob * 100.0
                ),
                parameter: None,
                value: None,
            });
        }

        if is_anomaly {
            recs.push(Recommendation {
                action: "investigate_anomaly".into(),
                reason: "Anomalous sensor readings detected".into(),
                parameter: None,
                value: None,
            });
        }

        // Check specific sensor readings
        if let Some(latest) = recent_readings.last() {
            if let Some(t) = latest.temperature {
                if t > 70.0 {
                    recs.push(Recommendation {
                        action: "check_cooling_system".into(),
                        reason: format!("High temperature ({:.1}°C)", t),
                        parameter: Some("temperature".into()),
                        value: Some(t),
                    });
                }
            }
            if let Some(v) = latest.vibration {
                if v > 8.0 {
                    recs.push(Recommendation {
                        action: "check_bearings_and_alignment".into(),
                        reason: format!("High vibration ({:.1} mm/s)", v),
                        parameter: Some("vibration".into()),
                        value: Some(v),
                    });
                }
            }
        }

        recs
    }

    /// Estimate time to failure in days.
    fn estimate_time_to_failure(
        &self,
        failure_prob: f64,
        equipment: &Equipment,
        _maintenance_history: &[MaintenanceRecord],
    ) -> Option<i64> {
        if failure_prob < 0.3 {
            return None;
        }

        // Simple heuristic based on failure probability and equipment age
        let base_ttf = ((1.0 - failure_prob) / failure_prob * 90.0) as i64;
        let age_factor = equipment
            .installation_date
            .map(|d| {
                let days = (Utc::now() - d).num_days().max(1);
                (365.0 / days as f64).clamp(0.5, 2.0)
            })
            .unwrap_or(1.0);
        Some((base_ttf as f64 * age_factor) as i64)
    }

    /// Generate explanations for the prediction.
    fn explain_prediction(&self, features: &[f64], _readings: &[ConditionReading]) -> Vec<String> {
        let mut reasons = Vec::new();
        if features.len() >= 5 {
            if features[0] > 70.0 {
                reasons.push(format!(
                    "High temperature ({:.1}°C) contributes to risk",
                    features[0]
                ));
            }
            if features[1] > 8.0 {
                reasons.push(format!(
                    "High vibration ({:.1} mm/s) indicates wear",
                    features[1]
                ));
            }
            if features[12] > 90.0 {
                reasons.push(format!(
                    "Equipment age ({:.0} days) increases risk",
                    features[12]
                ));
            }
            if features[15] > 60.0 {
                reasons.push(format!(
                    "Days since last maintenance ({:.0}) exceeds recommended interval",
                    features[15]
                ));
            }
        }
        if reasons.is_empty() {
            reasons.push("All parameters within normal ranges".into());
        }
        reasons
    }

    /// Fallback: rule-based assessment when ML model is not available.
    fn rule_based_assessment(
        &self,
        _equipment: &Equipment,
        recent_readings: &[ConditionReading],
        _maintenance_history: &[MaintenanceRecord],
    ) -> MaintenancePrediction {
        let mut risk_score = 0.0_f64;
        let mut reasons = Vec::new();

        if let Some(latest) = recent_readings.last() {
            if let Some(t) = latest.temperature {
                if t > 65.0 {
                    risk_score += 0.3;
                    reasons.push(format!("High temperature: {:.1}°C", t));
                }
            }
            if let Some(v) = latest.vibration {
                if v > 7.0 {
                    risk_score += 0.3;
                    reasons.push(format!("High vibration: {:.1} mm/s", v));
                }
            }
            if let Some(p) = latest.pressure {
                if p > 120.0 {
                    risk_score += 0.2;
                    reasons.push(format!("High pressure: {:.1} psi", p));
                }
            }
        }

        let (risk_level, failure_prob) = if risk_score >= 0.7 {
            ("high", 0.75)
        } else if risk_score >= 0.4 {
            ("medium", 0.5)
        } else {
            ("low", 0.2)
        };

        if reasons.is_empty() {
            reasons.push("All parameters within normal ranges".into());
        }

        MaintenancePrediction {
            risk_level: risk_level.into(),
            failure_probability: failure_prob,
            is_anomaly: risk_score >= 0.5,
            recommendations: vec![],
            reasons,
            estimated_time_to_failure: None,
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
struct CriticalIssue {
    parameter: String,
    value: f64,
    reason: String,
}

/// Compute mean and standard deviation of a slice.
fn compute_mean_std(values: &[f64]) -> (f64, f64) {
    if values.is_empty() {
        return (0.0, 0.0);
    }
    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let variance = values.iter().map(|&v| (v - mean).powi(2)).sum::<f64>() / n;
    (mean, variance.sqrt())
}

/// Compute simple linear regression slope.
fn compute_slope(values: &[f64]) -> f64 {
    let n = values.len() as f64;
    let indices: Vec<f64> = (0..values.len()).map(|i| i as f64).collect();
    let x_mean = indices.iter().sum::<f64>() / n;
    let y_mean = values.iter().sum::<f64>() / n;

    let num: f64 = indices
        .iter()
        .zip(values.iter())
        .map(|(&x, &y)| (x - x_mean) * (y - y_mean))
        .sum();
    let den: f64 = indices.iter().map(|&x| (x - x_mean).powi(2)).sum();

    if den == 0.0 {
        0.0
    } else {
        num / den
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_reading(
        eq_id: &str,
        temp: f64,
        vib: f64,
        pressure: f64,
        ts: DateTime<Utc>,
    ) -> ConditionReading {
        ConditionReading {
            equipment_id: eq_id.into(),
            timestamp: ts,
            temperature: Some(temp),
            vibration: Some(vib),
            pressure: Some(pressure),
            current: Some(20.0),
            noise: Some(60.0),
            operating_hours: Some(1000.0),
        }
    }

    #[test]
    fn test_standard_scaler() {
        let data = ndarray::array![[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]];
        let mut scaler = StandardScaler::new();
        let transformed = scaler.fit_transform(&data).unwrap();

        // After scaling, each column should have mean ~0 and std ~1
        let col0_mean = transformed.column(0).mean().unwrap();
        let col1_mean = transformed.column(1).mean().unwrap();
        assert!((col0_mean).abs() < 1e-10);
        assert!((col1_mean).abs() < 1e-10);

        // Inverse transform should recover original
        let recovered = scaler.inverse_transform(&transformed).unwrap();
        for i in 0..3 {
            for j in 0..2 {
                assert!((recovered[[i, j]] - data[[i, j]]).abs() < 1e-10);
            }
        }
    }

    #[test]
    fn test_anomaly_detector() {
        // Fit on clean data only — fitting on data that already contains the
        // anomaly inflates the mean/std and masks it (z-score masking).
        let training = ndarray::array![[0.0, 0.0], [0.1, 0.1], [-0.1, -0.1]];
        let data = ndarray::array![
            [0.0, 0.0],
            [0.1, 0.1],
            [-0.1, -0.1],
            [10.0, 10.0], // anomaly
        ];
        let mut detector = AnomalyDetector::new(0.1, 2.0);
        detector.fit(&training).unwrap();
        let anomalies = detector.predict_binary(&data).unwrap();
        assert!(!anomalies[0]); // normal
        assert!(!anomalies[1]); // normal
        assert!(!anomalies[2]); // normal
        assert!(anomalies[3]); // anomaly
    }

    #[test]
    fn test_ensemble_classifier() {
        let x = ndarray::array![
            [1.0, 0.0],
            [2.0, 0.0],
            [3.0, 1.0],
            [4.0, 1.0],
            [1.5, 0.0],
            [3.5, 1.0],
        ];
        let y = vec![0.0, 0.0, 1.0, 1.0, 0.0, 1.0];

        let mut clf = EnsembleClassifier::new(50, 10);
        clf.fit(&x, &y).unwrap();
        let preds = clf.predict(&x).unwrap();
        assert_eq!(preds.len(), 6);
    }

    #[test]
    fn test_cbm_predictor_critical_threshold() {
        let predictor = ConditionBasedMaintenancePredictor::new();
        let now = Utc::now();
        let readings = vec![make_reading("eq1", 95.0, 5.0, 100.0, now)];

        let equipment = Equipment {
            id: "eq1".into(),
            installation_date: Some(now - Duration::days(365)),
            operating_hours: Some(5000.0),
            cycles: Some(1000.0),
        };

        let prediction = predictor.predict_maintenance_needs(&equipment, &readings, &[]);
        assert_eq!(prediction.risk_level, "critical");
        assert!((prediction.failure_probability - 1.0).abs() < 1e-10);
        assert!(!prediction.recommendations.is_empty());
    }

    #[test]
    fn test_cbm_predictor_no_data() {
        let predictor = ConditionBasedMaintenancePredictor::new();
        let equipment = Equipment {
            id: "eq1".into(),
            installation_date: None,
            operating_hours: None,
            cycles: None,
        };
        let prediction = predictor.predict_maintenance_needs(&equipment, &[], &[]);
        assert_eq!(prediction.risk_level, "unknown");
    }

    #[test]
    fn test_cbm_training_pipeline() {
        let now = Utc::now();
        let mut predictor = ConditionBasedMaintenancePredictor::new();

        let equipment = Equipment {
            id: "eq1".into(),
            installation_date: Some(now - Duration::days(365)),
            operating_hours: Some(5000.0),
            cycles: Some(1000.0),
        };

        let mut readings = Vec::new();
        for i in 0..30 {
            readings.push(make_reading(
                "eq1",
                40.0 + (i as f64 * 0.5),
                3.0 + (i as f64 * 0.1),
                80.0,
                now - Duration::days(30) + Duration::days(i as i64),
            ));
        }

        let maintenance = vec![MaintenanceRecord {
            equipment_id: "eq1".into(),
            date: now - Duration::days(5),
            maintenance_type: "repair".into(),
        }];

        let metrics = predictor
            .train(&[equipment], &maintenance, &readings)
            .unwrap();
        assert!(metrics.training_samples > 0);
        assert!(metrics.cv_accuracy_mean >= 0.0);
    }

    #[test]
    fn test_compute_mean_std() {
        let values = vec![2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0];
        let (mean, std) = compute_mean_std(&values);
        assert!((mean - 5.0).abs() < 0.01);
        assert!((std - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_compute_slope() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let slope = compute_slope(&values);
        assert!((slope - 1.0).abs() < 0.01);
    }
}

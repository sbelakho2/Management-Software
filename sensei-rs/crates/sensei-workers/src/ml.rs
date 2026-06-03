//! ML worker — replaces Celery's `run_model_training`, `check_drift_and_retrain`,
//! `force_model_retrain`, and `scheduled_retrain_all`.
//!
//! Listens on:
//! - `sensei.tasks.ml.training`
//! - `sensei.tasks.ml.drift-check`
//! - `sensei.tasks.ml.force-retrain`
//! - `sensei.tasks.ml.retrain-all`
//!
//! Implements real statistical model training (mean, std_dev, control limits for
//! SPC-style models) and drift detection using the Population Stability Index (PSI).
//! When a database pool is available, training data is queried from production
//! tables; otherwise the model operates on synthetic calibration data with a warning.

use crate::error::{Result, WorkerError};
use crate::task::{TaskConsumer, TaskMetadata};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

/// Payload for ML-related tasks.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MlTaskPayload {
    /// Name / identifier of the model to train or check.
    pub model_name: Option<String>,
    /// Optional dataset version or reference.
    pub dataset_version: Option<String>,
    /// Optional hyper-parameters to override defaults.
    pub hyperparameters: Option<HashMap<String, serde_json::Value>>,
    /// Optional tenant ID for multi-tenancy.
    pub tenant_id: Option<String>,
}

/// Status of an ML model.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ModelStatus {
    /// Model is performing within acceptable bounds.
    Healthy,
    /// Drift has been detected — retraining recommended.
    DriftDetected {
        /// Drift score (0.0 – 1.0).
        score: f64,
        /// Metric that drifted.
        metric: String,
    },
    /// Model is currently being trained.
    Training {
        /// Progress percentage.
        progress: f64,
    },
    /// Model has been trained successfully.
    Trained {
        /// Accuracy / performance metric.
        accuracy: f64,
        /// Training duration in seconds.
        duration_secs: f64,
    },
    /// Training or evaluation failed.
    Failed {
        /// Error message.
        error: String,
    },
}

/// Statistical model parameters computed during training.
///
/// For SPC-style models this stores the process mean, standard deviation,
/// and control limits (UCL/LCL at ±3σ). For other model types, additional
/// parameters may be stored in the `extra` map.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelParameters {
    /// Arithmetic mean of the training data.
    pub mean: f64,
    /// Population standard deviation.
    pub std_dev: f64,
    /// Upper control limit (mean + 3σ).
    pub ucl: f64,
    /// Lower control limit (mean - 3σ).
    pub lcl: f64,
    /// Number of training samples used.
    pub sample_count: usize,
    /// Process capability index (Cp).
    pub cp: Option<f64>,
    /// Process capability index (Cpk).
    pub cpk: Option<f64>,
    /// Additional model-specific parameters.
    pub extra: HashMap<String, f64>,
}

impl ModelParameters {
    /// Compute model parameters from a slice of training data.
    ///
    /// If `spec_lsl` and `spec_usl` are provided, Cp and Cpk are calculated.
    pub fn from_data(data: &[f64], spec_lsl: Option<f64>, spec_usl: Option<f64>) -> Self {
        let n = data.len();
        if n == 0 {
            return Self {
                mean: 0.0,
                std_dev: 0.0,
                ucl: 0.0,
                lcl: 0.0,
                sample_count: 0,
                cp: None,
                cpk: None,
                extra: HashMap::new(),
            };
        }

        let mean = data.iter().sum::<f64>() / n as f64;
        let variance = data.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n as f64;
        let std_dev = variance.sqrt();

        let ucl = mean + 3.0 * std_dev;
        let lcl = mean - 3.0 * std_dev;

        // Compute Cp and Cpk if specification limits are available.
        let (cp, cpk) = match (spec_lsl, spec_usl) {
            (Some(lsl), Some(usl)) if std_dev > 0.0 => {
                let cp = (usl - lsl) / (6.0 * std_dev);
                let cpk = ((usl - mean).min(mean - lsl)) / (3.0 * std_dev);
                (Some(cp), Some(cpk))
            }
            _ => (None, None),
        };

        Self {
            mean,
            std_dev,
            ucl,
            lcl,
            sample_count: n,
            cp,
            cpk,
            extra: HashMap::new(),
        }
    }
}

/// Describes a single registered model.
#[derive(Debug, Clone)]
pub struct ModelDefinition {
    /// Unique model name.
    pub name: &'static str,
    /// Current status.
    pub status: ModelStatus,
    /// Version string.
    pub version: String,
    /// Last computed model parameters (if trained).
    pub parameters: Option<ModelParameters>,
    /// Reference (baseline) distribution for drift detection.
    pub baseline_histogram: Option<Vec<f64>>,
}

/// Registry of available models with their metadata.
///
/// Backed by an in-memory store; in production this would be persisted to
/// the database and integrated with an MLflow-compatible model registry.
pub struct ModelRegistry {
    models: Arc<RwLock<HashMap<String, ModelDefinition>>>,
}

impl ModelRegistry {
    /// Create a new registry with default model definitions.
    pub fn new() -> Self {
        let mut models = HashMap::new();

        models.insert(
            "quality_defect_prediction".to_string(),
            ModelDefinition {
                name: "quality_defect_prediction",
                status: ModelStatus::Healthy,
                version: "1.2.0".to_string(),
                parameters: None,
                baseline_histogram: None,
            },
        );

        models.insert(
            "demand_forecasting".to_string(),
            ModelDefinition {
                name: "demand_forecasting",
                status: ModelStatus::Healthy,
                version: "2.0.1".to_string(),
                parameters: None,
                baseline_histogram: None,
            },
        );

        models.insert(
            "maintenance_prediction".to_string(),
            ModelDefinition {
                name: "maintenance_prediction",
                status: ModelStatus::Healthy,
                version: "1.0.3".to_string(),
                parameters: None,
                baseline_histogram: None,
            },
        );

        Self {
            models: Arc::new(RwLock::new(models)),
        }
    }

    /// Get all model names.
    pub async fn model_names(&self) -> Vec<String> {
        let models = self.models.read().await;
        models.keys().cloned().collect()
    }

    /// Get a model's definition.
    pub async fn get_model(&self, name: &str) -> Option<ModelDefinition> {
        let models = self.models.read().await;
        models.get(name).cloned()
    }

    /// Update a model's status.
    pub async fn update_status(&self, name: &str, status: ModelStatus) {
        let mut models = self.models.write().await;
        if let Some(def) = models.get_mut(name) {
            def.status = status;
        }
    }

    /// Update a model's parameters and baseline histogram.
    pub async fn update_parameters(
        &self,
        name: &str,
        parameters: ModelParameters,
        baseline: Vec<f64>,
    ) {
        let mut models = self.models.write().await;
        if let Some(def) = models.get_mut(name) {
            def.parameters = Some(parameters);
            def.baseline_histogram = Some(baseline);
        }
    }
}

impl Default for ModelRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Worker that processes ML-related tasks.
///
/// Implements real statistical model training (SPC control charts, process
/// capability) and drift detection (Population Stability Index). When a
/// database pool is provided, training data is loaded from production tables.
pub struct MlWorker {
    /// Registry of models managed by this worker.
    registry: Arc<ModelRegistry>,
    /// Optional database pool for loading training data.
    pool: Option<Arc<PgPool>>,
}

impl MlWorker {
    /// Create a new [`MlWorker`] with the default model registry (no DB pool).
    pub fn new() -> Self {
        Self {
            registry: Arc::new(ModelRegistry::new()),
            pool: None,
        }
    }

    /// Create an [`MlWorker`] with a custom model registry.
    pub fn with_registry(registry: Arc<ModelRegistry>) -> Self {
        Self {
            registry,
            pool: None,
        }
    }

    /// Create an [`MlWorker`] with a database pool for loading training data.
    pub fn with_pool(pool: Arc<PgPool>) -> Self {
        Self {
            registry: Arc::new(ModelRegistry::new()),
            pool: Some(pool),
        }
    }

    /// Load training data for a model from the database.
    ///
    /// Queries the relevant domain table based on the model name. Returns
    /// a vector of f64 values suitable for statistical analysis.
    async fn load_training_data(&self, model_name: &str) -> Result<Vec<f64>> {
        match &self.pool {
            Some(pool) => {
                let data = match model_name {
                    "quality_defect_prediction" => {
                        // Query defect rates from quality inspections.
                        let rows = sqlx::query_scalar::<_, f64>(
                            "SELECT COALESCE(defect_rate, 0.0) FROM quality_inspections \
                             WHERE created_at > NOW() - INTERVAL '90 days' \
                             ORDER BY created_at DESC LIMIT 10000",
                        )
                        .fetch_all(pool.as_ref())
                        .await
                        .map_err(|e| {
                            WorkerError::Processing(format!(
                                "Failed to load quality training data: {}", e
                            ))
                        })?;
                        rows
                    }
                    "demand_forecasting" => {
                        // Query daily order quantities.
                        let rows = sqlx::query_scalar::<_, f64>(
                            "SELECT COALESCE(daily_quantity, 0.0) FROM production_daily_summary \
                             WHERE date > NOW() - INTERVAL '180 days' \
                             ORDER BY date DESC LIMIT 10000",
                        )
                        .fetch_all(pool.as_ref())
                        .await
                        .map_err(|e| {
                            WorkerError::Processing(format!(
                                "Failed to load demand training data: {}", e
                            ))
                        })?;
                        rows
                    }
                    "maintenance_prediction" => {
                        // Query equipment operating hours between failures.
                        let rows = sqlx::query_scalar::<_, f64>(
                            "SELECT COALESCE(hours_since_last_pm, 0.0) \
                             FROM maintenance_equipment_summary \
                             WHERE last_maintenance > NOW() - INTERVAL '365 days' \
                             ORDER BY last_maintenance DESC LIMIT 10000",
                        )
                        .fetch_all(pool.as_ref())
                        .await
                        .map_err(|e| {
                            WorkerError::Processing(format!(
                                "Failed to load maintenance training data: {}", e
                            ))
                        })?;
                        rows
                    }
                    _ => {
                        warn!(
                            model = %model_name,
                            "Unknown model name — no training data query defined"
                        );
                        Vec::new()
                    }
                };

                if data.is_empty() {
                    warn!(
                        model = %model_name,
                        "No training data returned from database — using calibration data"
                    );
                }

                Ok(data)
            }
            None => {
                warn!(
                    model = %model_name,
                    "No database pool configured — using synthetic calibration data"
                );
                Ok(Vec::new())
            }
        }
    }

    /// Generate synthetic calibration data for a model.
    ///
    /// Used when no database pool is available or when no real data exists.
    /// Produces a realistic distribution based on the model type.
    fn calibration_data(model_name: &str) -> Vec<f64> {
        match model_name {
            "quality_defect_prediction" => {
                // Typical defect rates: 0.5% – 5% with mean ~2%.
                (0..200)
                    .map(|i| {
                        let base = 0.02;
                        // Deterministic spread using index.
                        let variation = ((i as f64 * 7.31) % 1.0 - 0.5) * 0.04;
                        (base + variation).max(0.0).min(1.0)
                    })
                    .collect()
            }
            "demand_forecasting" => {
                // Typical daily demand: 50 – 200 units.
                (0..200)
                    .map(|i| {
                        let base = 120.0;
                        let variation = ((i as f64 * 13.17) % 1.0 - 0.5) * 140.0;
                        (base + variation).max(0.0)
                    })
                    .collect()
            }
            "maintenance_prediction" => {
                // Typical hours between failures: 100 – 2000 hours.
                (0..200)
                    .map(|i| {
                        let base = 800.0;
                        let variation = ((i as f64 * 19.73) % 1.0 - 0.5) * 1800.0;
                        (base + variation).max(0.0)
                    })
                    .collect()
            }
            _ => {
                // Generic: values around 100 with moderate spread.
                (0..200)
                    .map(|i| {
                        let base = 100.0;
                        let variation = ((i as f64 * 11.37) % 1.0 - 0.5) * 40.0;
                        base + variation
                    })
                    .collect()
            }
        }
    }

    /// Build a histogram (frequency distribution) from data for drift detection.
    ///
    /// Returns a normalized histogram with `bins` buckets covering the range
    /// of the data.
    fn build_histogram(data: &[f64], bins: usize) -> Vec<f64> {
        if data.is_empty() || bins == 0 {
            return vec![0.0; bins.max(1)];
        }

        let min_val = data.iter().cloned().fold(f64::INFINITY, f64::min);
        let max_val = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        if (max_val - min_val).abs() < f64::EPSILON {
            let mut hist = vec![0.0; bins];
            hist[bins / 2] = 1.0;
            return hist;
        }

        let bin_width = (max_val - min_val) / bins as f64;
        let mut counts = vec![0usize; bins];

        for &val in data {
            let idx = ((val - min_val) / bin_width).floor() as usize;
            let idx = idx.min(bins - 1);
            counts[idx] += 1;
        }

        // Normalize to proportions.
        let total: usize = counts.iter().sum();
        if total == 0 {
            return vec![0.0; bins];
        }

        counts.iter().map(|&c| c as f64 / total as f64).collect()
    }

    /// Compute the Population Stability Index (PSI) between two distributions.
    ///
    /// PSI measures how much a distribution has shifted relative to a baseline:
    /// - PSI < 0.10: No significant change
    /// - 0.10 ≤ PSI < 0.25: Moderate change (investigate)
    /// - PSI ≥ 0.25: Significant change (action required)
    fn compute_psi(baseline: &[f64], current: &[f64]) -> f64 {
        if baseline.len() != current.len() || baseline.is_empty() {
            return 0.0;
        }

        let mut psi = 0.0;
        for i in 0..baseline.len() {
            let b = baseline[i].max(0.0001); // Avoid division by zero.
            let c = current[i].max(0.0001);
            psi += (c - b) * (c / b).ln();
        }

        psi
    }

    /// Run model training for a specific model.
    ///
    /// Loads training data (from DB or calibration), computes statistical
    /// parameters (mean, std_dev, control limits), and stores the results
    /// in the model registry.
    async fn train_model(&self, model_name: &str) -> Result<ModelStatus> {
        let start = std::time::Instant::now();
        info!(model = %model_name, "Starting model training");

        self.registry
            .update_status(
                model_name,
                ModelStatus::Training { progress: 0.0 },
            )
            .await;

        // Step 1: Load training data.
        self.registry
            .update_status(
                model_name,
                ModelStatus::Training { progress: 0.2 },
            )
            .await;

        let mut data = self.load_training_data(model_name).await?;

        // Fall back to calibration data if no real data available.
        if data.is_empty() {
            data = Self::calibration_data(model_name);
        }

        self.registry
            .update_status(
                model_name,
                ModelStatus::Training { progress: 0.5 },
            )
            .await;

        // Step 2: Compute statistical model parameters.
        let spec_lsl = match model_name {
            "quality_defect_prediction" => Some(0.0),
            _ => None,
        };
        let spec_usl = match model_name {
            "quality_defect_prediction" => Some(0.05),
            _ => None,
        };
        let parameters = ModelParameters::from_data(&data, spec_lsl, spec_usl);

        self.registry
            .update_status(
                model_name,
                ModelStatus::Training { progress: 0.75 },
            )
            .await;

        // Step 3: Build baseline histogram for future drift detection.
        let baseline = Self::build_histogram(&data, 10);

        // Step 4: Store parameters and baseline.
        self.registry
            .update_parameters(model_name, parameters.clone(), baseline)
            .await;

        let duration = start.elapsed().as_secs_f64();

        // Compute an "accuracy" metric based on how well the data fits
        // within control limits (percentage of points within ±3σ).
        let within_limits = data
            .iter()
            .filter(|&&v| v >= parameters.lcl && v <= parameters.ucl)
            .count();
        let accuracy = if data.is_empty() {
            1.0
        } else {
            within_limits as f64 / data.len() as f64
        };

        let status = ModelStatus::Trained {
            accuracy,
            duration_secs: duration,
        };

        self.registry
            .update_status(model_name, status.clone())
            .await;

        info!(
            model = %model_name,
            mean = %parameters.mean,
            std_dev = %parameters.std_dev,
            ucl = %parameters.ucl,
            lcl = %parameters.lcl,
            sample_count = %parameters.sample_count,
            accuracy = %accuracy,
            duration_secs = %duration,
            "Model training completed"
        );
        Ok(status)
    }

    /// Check for model drift using the Population Stability Index.
    ///
    /// Compares the current data distribution against the stored baseline.
    /// If PSI exceeds the threshold (0.25), drift is flagged.
    async fn check_drift(&self, model_name: &str) -> Result<ModelStatus> {
        info!(model = %model_name, "Checking for model drift");

        let model = self.registry.get_model(model_name).await;
        let baseline = match model.and_then(|m| m.baseline_histogram) {
            Some(b) => b,
            None => {
                warn!(
                    model = %model_name,
                    "No baseline histogram — model has not been trained yet, skipping drift check"
                );
                return Ok(ModelStatus::Healthy);
            }
        };

        // Load current data.
        let mut current_data = self.load_training_data(model_name).await?;
        if current_data.is_empty() {
            current_data = Self::calibration_data(model_name);
        }

        // Build current histogram with the same number of bins.
        let current_hist = Self::build_histogram(&current_data, baseline.len());

        // Compute PSI.
        let psi = Self::compute_psi(&baseline, &current_hist);

        let status = if psi >= 0.25 {
            warn!(
                model = %model_name,
                psi = %psi,
                "Significant drift detected (PSI >= 0.25) — retraining recommended"
            );
            ModelStatus::DriftDetected {
                score: psi,
                metric: "population_stability_index".to_string(),
            }
        } else if psi >= 0.10 {
            info!(
                model = %model_name,
                psi = %psi,
                "Moderate drift detected (PSI >= 0.10) — monitoring"
            );
            // Not severe enough to flag as drifted, but worth noting.
            ModelStatus::Healthy
        } else {
            info!(
                model = %model_name,
                psi = %psi,
                "No significant drift detected — model is healthy"
            );
            ModelStatus::Healthy
        };

        self.registry
            .update_status(model_name, status.clone())
            .await;

        Ok(status)
    }

    /// Force retrain regardless of drift status.
    async fn force_retrain(&self, model_name: &str) -> Result<ModelStatus> {
        info!(model = %model_name, "Force retrain triggered");
        self.train_model(model_name).await
    }

    /// Retrain all registered models.
    async fn retrain_all(&self) -> Result<Vec<(String, ModelStatus)>> {
        info!("Starting scheduled retrain of all models");

        let model_names = self.registry.model_names().await;
        let mut results = Vec::new();

        for name in &model_names {
            match self.train_model(name).await {
                Ok(status) => {
                    results.push((name.clone(), status));
                }
                Err(e) => {
                    error!(model = %name, error = %e, "Retrain-all failed for model");
                    results.push((
                        name.clone(),
                        ModelStatus::Failed {
                            error: e.to_string(),
                        },
                    ));
                }
            }
        }

        info!(
            trained = results.len(),
            "Scheduled retrain-all completed"
        );
        Ok(results)
    }
}

impl Default for MlWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for MlWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.ml.training"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-ml"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        let ml_payload: MlTaskPayload = serde_json::from_slice(payload).map_err(|e| {
            error!(
                task_id = %metadata.task_id,
                error = %e,
                "Failed to deserialize ML task payload"
            );
            WorkerError::Serialization(e)
        })?;

        let model_name = ml_payload
            .model_name
            .as_deref()
            .unwrap_or("quality_defect_prediction");

        match metadata.task_type {
            crate::task::TaskType::RunModelTraining => {
                let status = self.train_model(model_name).await?;
                info!(
                    task_id = %metadata.task_id,
                    model = %model_name,
                    status = ?status,
                    "Model training task completed"
                );
                Ok(())
            }
            crate::task::TaskType::CheckDriftAndRetrain => {
                let drift_status = self.check_drift(model_name).await?;

                if matches!(drift_status, ModelStatus::DriftDetected { .. }) {
                    info!(
                        task_id = %metadata.task_id,
                        model = %model_name,
                        "Drift detected — triggering retrain"
                    );
                    let _ = self.train_model(model_name).await?;
                }

                info!(
                    task_id = %metadata.task_id,
                    model = %model_name,
                    "Drift check completed"
                );
                Ok(())
            }
            crate::task::TaskType::ForceModelRetrain => {
                let status = self.force_retrain(model_name).await?;
                info!(
                    task_id = %metadata.task_id,
                    model = %model_name,
                    status = ?status,
                    "Force retrain completed"
                );
                Ok(())
            }
            crate::task::TaskType::ScheduledRetrainAll => {
                let results = self.retrain_all().await?;
                info!(
                    task_id = %metadata.task_id,
                    model_count = results.len(),
                    "Scheduled retrain-all completed"
                );
                Ok(())
            }
            _ => Err(WorkerError::Processing(format!(
                "Unsupported task type for MlWorker: {:?}",
                metadata.task_type
            ))),
        }
    }
}

/// Convenience wrapper listening on `sensei.tasks.ml.training`.
pub struct TrainingWorker {
    inner: MlWorker,
}

impl TrainingWorker {
    pub fn new() -> Self {
        Self {
            inner: MlWorker::new(),
        }
    }
}

impl Default for TrainingWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for TrainingWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.ml.training"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-ml-training"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        self.inner.process(payload, metadata).await
    }
}

/// Convenience wrapper listening on `sensei.tasks.ml.drift-check`.
pub struct DriftCheckWorker {
    inner: MlWorker,
}

impl DriftCheckWorker {
    pub fn new() -> Self {
        Self {
            inner: MlWorker::new(),
        }
    }
}

impl Default for DriftCheckWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for DriftCheckWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.ml.drift-check"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-ml-drift"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        self.inner.process(payload, metadata).await
    }
}

/// Convenience wrapper listening on `sensei.tasks.ml.force-retrain`.
pub struct ForceRetrainWorker {
    inner: MlWorker,
}

impl ForceRetrainWorker {
    pub fn new() -> Self {
        Self {
            inner: MlWorker::new(),
        }
    }
}

impl Default for ForceRetrainWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for ForceRetrainWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.ml.force-retrain"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-ml-force-retrain"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        self.inner.process(payload, metadata).await
    }
}

/// Convenience wrapper listening on `sensei.tasks.ml.retrain-all`.
pub struct RetrainAllWorker {
    inner: MlWorker,
}

impl RetrainAllWorker {
    pub fn new() -> Self {
        Self {
            inner: MlWorker::new(),
        }
    }
}

impl Default for RetrainAllWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for RetrainAllWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.ml.retrain-all"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-ml-retrain-all"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        self.inner.process(payload, metadata).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_parameters_from_data() {
        let data = vec![10.0, 12.0, 11.0, 13.0, 9.0, 11.5, 10.5];
        let params = ModelParameters::from_data(&data, Some(6.0), Some(14.0));

        assert_eq!(params.sample_count, 7);
        assert!(params.mean > 0.0);
        assert!(params.std_dev > 0.0);
        assert!(params.ucl > params.mean);
        assert!(params.lcl < params.mean);
        assert!(params.cp.is_some());
        assert!(params.cpk.is_some());
    }

    #[test]
    fn test_model_parameters_empty_data() {
        let params = ModelParameters::from_data(&[], None, None);
        assert_eq!(params.sample_count, 0);
        assert_eq!(params.mean, 0.0);
    }

    #[test]
    fn test_psi_identical_distributions() {
        let baseline = vec![0.1, 0.2, 0.4, 0.2, 0.1];
        let psi = MlWorker::compute_psi(&baseline, &baseline);
        assert!(psi.abs() < 0.001, "PSI should be ~0 for identical distributions");
    }

    #[test]
    fn test_psi_shifted_distributions() {
        let baseline = vec![0.4, 0.3, 0.2, 0.08, 0.02];
        let current = vec![0.02, 0.08, 0.2, 0.3, 0.4];
        let psi = MlWorker::compute_psi(&baseline, &current);
        assert!(psi > 0.25, "PSI should be significant for shifted distributions");
    }

    #[test]
    fn test_histogram() {
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let hist = MlWorker::build_histogram(&data, 5);
        let sum: f64 = hist.iter().sum();
        assert!((sum - 1.0).abs() < 0.001, "Histogram should sum to ~1.0");
    }

    #[test]
    fn test_calibration_data() {
        for model in &[
            "quality_defect_prediction",
            "demand_forecasting",
            "maintenance_prediction",
        ] {
            let data = MlWorker::calibration_data(model);
            assert!(!data.is_empty(), "Calibration data should not be empty");
        }
    }
}

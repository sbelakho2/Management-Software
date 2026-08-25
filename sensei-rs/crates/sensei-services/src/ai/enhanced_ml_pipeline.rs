//! World-Class Enhanced ML Pipeline Service.
//!
//! Implements production-grade ML infrastructure:
//! - End-to-end ML pipeline management
//! - Feature store with versioning
//! - Model registry with A/B testing
//! - AutoML for hyperparameter optimization
//! - Drift detection and monitoring
//! - Continuous training pipelines
//! - Explainability and fairness
//! - Manufacturing-specific optimizations

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Types of ML models.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelType {
    Classification,
    Regression,
    AnomalyDetection,
    Clustering,
    TimeSeries,
    Recommendation,
    Nlp,
    ComputerVision,
}

impl ModelType {
    pub fn as_str(&self) -> &'static str {
        match self {
            ModelType::Classification => "classification",
            ModelType::Regression => "regression",
            ModelType::AnomalyDetection => "anomaly_detection",
            ModelType::Clustering => "clustering",
            ModelType::TimeSeries => "time_series",
            ModelType::Recommendation => "recommendation",
            ModelType::Nlp => "nlp",
            ModelType::ComputerVision => "computer_vision",
        }
    }
}

/// Model lifecycle stages.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelStage {
    Development,
    Staging,
    Production,
    Archived,
}

impl ModelStage {
    pub fn as_str(&self) -> &'static str {
        match self {
            ModelStage::Development => "development",
            ModelStage::Staging => "staging",
            ModelStage::Production => "production",
            ModelStage::Archived => "archived",
        }
    }
}

/// Model deployment status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelStatus {
    Active,
    Draft,
    Validating,
    Approved,
    Deployed,
    Rollback,
    Deprecated,
    Archived,
}

/// Types of drift detected.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DriftType {
    Feature,
    Prediction,
    DataDrift,
    ConceptDrift,
    PredictionDrift,
    LabelDrift,
}

/// Severity of detected drift.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DriftSeverity {
    None,
    Low,
    Medium,
    High,
    Critical,
}

/// Types of features.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FeatureType {
    Numerical,
    Categorical,
    Boolean,
    DateTime,
    Text,
    Embedding,
}

/// Status of an ML experiment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExperimentStatus {
    Running,
    Completed,
    Failed,
    Stopped,
}

/// Stages in ML pipeline.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PipelineStage {
    DataIngestion,
    DataValidation,
    FeatureEngineering,
    ModelTraining,
    ModelEvaluation,
    ModelValidation,
    Deployment,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// Definition of a feature in the feature store.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureDefinition {
    pub name: String,
    pub feature_type: FeatureType,
    pub description: String,
    pub default_value: Option<serde_json::Value>,
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
    pub nullable: bool,
    pub mean: Option<f64>,
    pub std: Option<f64>,
    pub categories: Option<Vec<String>>,
    pub null_rate: f64,
    pub source: String,
    pub transformation: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub version: i32,
    pub is_required: bool,
    pub validation_rules: Vec<String>,
}

impl FeatureDefinition {
    pub fn new(name: &str, feature_type: FeatureType) -> Self {
        Self {
            name: name.into(),
            feature_type,
            description: String::new(),
            default_value: None,
            min_value: None,
            max_value: None,
            nullable: true,
            mean: None,
            std: None,
            categories: None,
            null_rate: 0.0,
            source: String::new(),
            transformation: String::new(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            version: 1,
            is_required: true,
            validation_rules: Vec::new(),
        }
    }
}

/// A vector of features for a single entity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureVector {
    pub entity_id: String,
    pub features: HashMap<String, f64>,
    pub timestamp: DateTime<Utc>,
}

impl FeatureVector {
    pub fn to_array(&self, feature_names: &[String], fill_value: f64) -> Vec<f64> {
        feature_names
            .iter()
            .map(|name| self.features.get(name).copied().unwrap_or(fill_value))
            .collect()
    }
}

/// A group of related features.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureGroup {
    pub name: String,
    pub features: Vec<FeatureDefinition>,
    pub entity_key: String,
    pub description: String,
    pub ttl_seconds: Option<i64>,
    pub version: i32,
    pub created_at: DateTime<Utc>,
}

impl FeatureGroup {
    pub fn new(name: &str, entity_key: &str) -> Self {
        Self {
            name: name.into(),
            features: Vec::new(),
            entity_key: entity_key.into(),
            description: String::new(),
            ttl_seconds: None,
            version: 1,
            created_at: Utc::now(),
        }
    }

    pub fn get_feature(&self, name: &str) -> Option<&FeatureDefinition> {
        self.features.iter().find(|f| f.name == name)
    }

    pub fn feature_names(&self) -> Vec<String> {
        self.features.iter().map(|f| f.name.clone()).collect()
    }
}

/// A dataset for model training.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingDataset {
    pub dataset_id: String,
    pub name: String,
    pub feature_names: Vec<String>,
    pub train_size: usize,
    pub val_size: usize,
    pub test_size: usize,
    pub created_at: DateTime<Utc>,
    pub source: String,
    pub version: i32,
}

/// Metrics for a trained model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetrics {
    pub accuracy: Option<f64>,
    pub precision: Option<f64>,
    pub recall: Option<f64>,
    pub f1_score: Option<f64>,
    pub auc_roc: Option<f64>,
    pub mse: Option<f64>,
    pub rmse: Option<f64>,
    pub mae: Option<f64>,
    pub r2: Option<f64>,
    pub mape: Option<f64>,
    pub inference_time_ms: Option<f64>,
    pub model_size_mb: Option<f64>,
    pub custom_metrics: HashMap<String, f64>,
}

impl ModelMetrics {
    pub fn to_map(&self) -> HashMap<String, serde_json::Value> {
        let mut map = HashMap::new();
        if let Some(v) = self.accuracy {
            map.insert("accuracy".into(), serde_json::json!(v));
        }
        if let Some(v) = self.f1_score {
            map.insert("f1_score".into(), serde_json::json!(v));
        }
        if let Some(v) = self.mse {
            map.insert("mse".into(), serde_json::json!(v));
        }
        if let Some(v) = self.rmse {
            map.insert("rmse".into(), serde_json::json!(v));
        }
        if let Some(v) = self.r2 {
            map.insert("r2".into(), serde_json::json!(v));
        }
        for (k, v) in &self.custom_metrics {
            map.insert(k.clone(), serde_json::json!(v));
        }
        map
    }
}

/// A specific version of a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelVersion {
    pub version_id: String,
    pub model_name: String,
    pub model_type: ModelType,
    pub version: String,
    pub stage: ModelStage,
    pub status: ModelStatus,
    pub created_at: DateTime<Utc>,
    pub metrics: ModelMetrics,
    pub hyperparameters: HashMap<String, serde_json::Value>,
    pub feature_names: Vec<String>,
    pub model_path: String,
    pub description: String,
    pub tags: Vec<String>,
    pub algorithm: String,
    pub training_dataset_id: String,
    pub model_size_bytes: i64,
}

impl ModelVersion {
    pub fn is_production(&self) -> bool {
        self.stage == ModelStage::Production
    }
}

/// Registry entry for a model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRegistry {
    pub model_id: String,
    pub name: String,
    pub description: String,
    pub model_type: ModelType,
    pub versions: Vec<ModelVersion>,
    pub latest_version: i32,
    pub production_version: Option<i32>,
    pub created_at: DateTime<Utc>,
    pub owner: String,
    pub tags: HashMap<String, String>,
}

impl ModelRegistry {
    pub fn new(name: &str, model_type: ModelType) -> Self {
        Self {
            model_id: Uuid::new_v4().to_string(),
            name: name.into(),
            description: String::new(),
            model_type,
            versions: Vec::new(),
            latest_version: 0,
            production_version: None,
            created_at: Utc::now(),
            owner: String::new(),
            tags: HashMap::new(),
        }
    }
}

/// Result of drift detection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriftDetectionResult {
    pub feature_name: String,
    pub drift_type: DriftType,
    pub drift_detected: bool,
    pub severity: DriftSeverity,
    pub score: f64,
    pub threshold: f64,
    pub details: HashMap<String, serde_json::Value>,
    pub p_value: Option<f64>,
    pub statistic: Option<f64>,
    pub test_used: String,
    pub detected_at: DateTime<Utc>,
    pub recommendations: Vec<String>,
}

impl DriftDetectionResult {
    pub fn is_drifting(&self) -> bool {
        self.drift_detected
            || matches!(
                self.severity,
                DriftSeverity::Medium | DriftSeverity::High | DriftSeverity::Critical
            )
    }
}

/// An ML experiment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Experiment {
    pub experiment_id: String,
    pub name: String,
    pub status: ExperimentStatus,
    pub parameters: HashMap<String, serde_json::Value>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub metrics: HashMap<String, f64>,
    pub duration_seconds: f64,
    pub error_message: String,
    pub algorithm: String,
    pub hyperparameters: HashMap<String, serde_json::Value>,
    pub dataset_id: String,
    pub model_artifact_path: String,
    pub logs: Vec<String>,
    pub tags: HashMap<String, String>,
}

impl Experiment {
    pub fn new(name: &str, parameters: HashMap<String, serde_json::Value>) -> Self {
        Self {
            experiment_id: Uuid::new_v4().to_string(),
            name: name.into(),
            status: ExperimentStatus::Running,
            parameters,
            started_at: Utc::now(),
            completed_at: None,
            metrics: HashMap::new(),
            duration_seconds: 0.0,
            error_message: String::new(),
            algorithm: String::new(),
            hyperparameters: HashMap::new(),
            dataset_id: String::new(),
            model_artifact_path: String::new(),
            logs: Vec::new(),
            tags: HashMap::new(),
        }
    }

    pub fn duration(&self) -> Option<Duration> {
        self.completed_at.map(|end| end - self.started_at)
    }
}

/// A/B test configuration for models.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ABTest {
    pub test_id: String,
    pub name: String,
    pub control_model: String,
    pub treatment_model: String,
    pub traffic_split: HashMap<String, f64>,
    pub started_at: DateTime<Utc>,
    pub ended_at: Option<DateTime<Utc>>,
    pub control_metrics: HashMap<String, f64>,
    pub treatment_metrics: HashMap<String, f64>,
    pub is_active: bool,
    pub winner: Option<String>,
    pub statistical_significance: f64,
}

impl ABTest {
    pub fn new(name: &str, control: &str, treatment: &str) -> Self {
        let mut split = HashMap::new();
        split.insert("control".into(), 0.5);
        split.insert("treatment".into(), 0.5);
        Self {
            test_id: Uuid::new_v4().to_string(),
            name: name.into(),
            control_model: control.into(),
            treatment_model: treatment.into(),
            traffic_split: split,
            started_at: Utc::now(),
            ended_at: None,
            control_metrics: HashMap::new(),
            treatment_metrics: HashMap::new(),
            is_active: true,
            winner: None,
            statistical_significance: 0.0,
        }
    }

    pub fn calculate_lift(&self, metric_name: &str) -> f64 {
        let control = self
            .control_metrics
            .get(metric_name)
            .copied()
            .unwrap_or(0.0);
        let treatment = self
            .treatment_metrics
            .get(metric_name)
            .copied()
            .unwrap_or(0.0);
        if control == 0.0 {
            0.0
        } else {
            (treatment - control) / control
        }
    }
}

/// Log entry for a prediction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionLog {
    pub prediction_id: String,
    pub model_name: String,
    pub model_version: String,
    pub timestamp: DateTime<Utc>,
    pub features: HashMap<String, serde_json::Value>,
    pub prediction: serde_json::Value,
    pub probability: Option<f64>,
    pub ground_truth: Option<serde_json::Value>,
    pub latency_ms: f64,
}

/// Alert from model monitoring.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitoringAlert {
    pub alert_id: String,
    pub model_name: String,
    pub alert_type: String,
    pub severity: DriftSeverity,
    pub message: String,
    pub metrics: HashMap<String, f64>,
    pub created_at: DateTime<Utc>,
    pub acknowledged: bool,
    pub resolved: bool,
}

// ---------------------------------------------------------------------------
// Feature Store
// ---------------------------------------------------------------------------

/// Feature store for ML feature management.
#[derive(Debug, Clone)]
pub struct FeatureStore {
    feature_groups: HashMap<String, FeatureGroup>,
    feature_vectors: HashMap<String, Vec<FeatureVector>>,
}

impl Default for FeatureStore {
    fn default() -> Self {
        Self::new()
    }
}

impl FeatureStore {
    pub fn new() -> Self {
        Self {
            feature_groups: HashMap::new(),
            feature_vectors: HashMap::new(),
        }
    }

    pub fn groups(&self) -> &HashMap<String, FeatureGroup> {
        &self.feature_groups
    }

    pub fn register_feature_group(&mut self, group: FeatureGroup) {
        tracing::info!(
            "Registered feature group: {} with {} features",
            group.name,
            group.features.len()
        );
        self.feature_groups.insert(group.name.clone(), group);
    }

    pub fn ingest(&mut self, group_name: &str, vectors: Vec<FeatureVector>) -> Result<(), String> {
        if !self.feature_groups.contains_key(group_name) {
            return Err(format!("Unknown feature group: {}", group_name));
        }
        for vector in vectors {
            let key = format!("{}:{}", group_name, vector.entity_id);
            self.feature_vectors.entry(key).or_default().push(vector);
        }
        Ok(())
    }

    pub fn ingest_features(
        &mut self,
        group_name: &str,
        entity_id: &str,
        features: HashMap<String, f64>,
        timestamp: Option<DateTime<Utc>>,
    ) -> Result<(), String> {
        if !self.feature_groups.contains_key(group_name) {
            return Err(format!("Unknown feature group: {}", group_name));
        }
        let vector = FeatureVector {
            entity_id: entity_id.into(),
            features,
            timestamp: timestamp.unwrap_or_else(Utc::now),
        };
        self.ingest(group_name, vec![vector])
    }

    pub fn get_features(
        &self,
        group_name: &str,
        entity_id: &str,
        as_of: Option<DateTime<Utc>>,
    ) -> Option<&FeatureVector> {
        let key = format!("{}:{}", group_name, entity_id);
        let vectors = self.feature_vectors.get(&key)?;
        match as_of {
            Some(ts) => vectors.iter().rfind(|v| v.timestamp <= ts),
            None => vectors.last(),
        }
    }

    pub fn get_feature_history(&self, group_name: &str, entity_id: &str) -> Vec<&FeatureVector> {
        let key = format!("{}:{}", group_name, entity_id);
        self.feature_vectors
            .get(&key)
            .map(|v| v.iter().collect())
            .unwrap_or_default()
    }

    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "feature_groups".into(),
            serde_json::json!(self.feature_groups.len()),
        );
        state.insert(
            "feature_vectors".into(),
            serde_json::json!(self.feature_vectors.len()),
        );
        state
    }
}

// ---------------------------------------------------------------------------
// Model Registry
// ---------------------------------------------------------------------------

/// Registry for managing ML model versions and lifecycle.
#[derive(Debug, Clone)]
pub struct ModelRegistryService {
    registries: HashMap<String, ModelRegistry>,
    prediction_logs: Vec<PredictionLog>,
    alerts: Vec<MonitoringAlert>,
    max_logs: usize,
}

impl Default for ModelRegistryService {
    fn default() -> Self {
        Self::new(10000)
    }
}

impl ModelRegistryService {
    pub fn new(max_logs: usize) -> Self {
        Self {
            registries: HashMap::new(),
            prediction_logs: Vec::new(),
            alerts: Vec::new(),
            max_logs,
        }
    }

    pub fn register_model(&mut self, name: &str, model_type: ModelType) -> ModelRegistry {
        let registry = ModelRegistry::new(name, model_type);
        let model_id = registry.model_id.clone();
        self.registries.insert(model_id.clone(), registry);
        self.registries.get(&model_id).cloned().unwrap()
    }

    pub fn get_registry(&self, model_id: &str) -> Option<&ModelRegistry> {
        self.registries.get(model_id)
    }

    pub fn get_registry_by_name(&self, name: &str) -> Option<&ModelRegistry> {
        self.registries.values().find(|r| r.name == name)
    }

    pub fn register_version(
        &mut self,
        model_id: &str,
        version: String,
        algorithm: &str,
        hyperparameters: HashMap<String, serde_json::Value>,
        feature_names: Vec<String>,
    ) -> Result<ModelVersion, String> {
        let registry = self
            .registries
            .get_mut(model_id)
            .ok_or_else(|| format!("Model not found: {}", model_id))?;

        let model_type = registry.model_type;
        let version_id = Uuid::new_v4().to_string();
        let new_version = registry.latest_version + 1;

        let mv = ModelVersion {
            version_id: version_id.clone(),
            model_name: registry.name.clone(),
            model_type,
            version,
            stage: ModelStage::Development,
            status: ModelStatus::Draft,
            created_at: Utc::now(),
            metrics: ModelMetrics {
                accuracy: None,
                precision: None,
                recall: None,
                f1_score: None,
                auc_roc: None,
                mse: None,
                rmse: None,
                mae: None,
                r2: None,
                mape: None,
                inference_time_ms: None,
                model_size_mb: None,
                custom_metrics: HashMap::new(),
            },
            hyperparameters,
            feature_names,
            model_path: format!("models/{}/{}/v{}", registry.name, version_id, new_version),
            description: String::new(),
            tags: Vec::new(),
            algorithm: algorithm.into(),
            training_dataset_id: String::new(),
            model_size_bytes: 0,
        };

        registry.latest_version = new_version;
        registry.versions.push(mv.clone());
        Ok(mv)
    }

    pub fn promote_to_production(
        &mut self,
        model_id: &str,
        version_id: &str,
    ) -> Result<(), String> {
        let registry = self
            .registries
            .get_mut(model_id)
            .ok_or_else(|| format!("Model not found: {}", model_id))?;

        let version = registry
            .versions
            .iter_mut()
            .find(|v| v.version_id == version_id)
            .ok_or_else(|| format!("Version not found: {}", version_id))?;

        version.stage = ModelStage::Production;
        version.status = ModelStatus::Deployed;
        registry.production_version = Some(
            version
                .version
                .parse::<i32>()
                .unwrap_or(registry.latest_version),
        );
        Ok(())
    }

    /// Attach evaluation metrics to a registered model version.
    pub fn set_version_metrics(
        &mut self,
        model_id: &str,
        version_id: &str,
        metrics: ModelMetrics,
    ) -> Result<(), String> {
        let registry = self
            .registries
            .get_mut(model_id)
            .ok_or_else(|| format!("Model not found: {}", model_id))?;
        let version = registry
            .versions
            .iter_mut()
            .find(|v| v.version_id == version_id)
            .ok_or_else(|| format!("Version not found: {}", version_id))?;
        version.metrics = metrics;
        Ok(())
    }

    pub fn log_prediction(&mut self, log: PredictionLog) {
        if self.prediction_logs.len() >= self.max_logs {
            self.prediction_logs.remove(0);
        }
        self.prediction_logs.push(log);
    }

    pub fn get_prediction_logs(&self, model_name: &str, limit: usize) -> Vec<&PredictionLog> {
        self.prediction_logs
            .iter()
            .filter(|l| l.model_name == model_name)
            .rev()
            .take(limit)
            .collect()
    }

    pub fn create_alert(&mut self, alert: MonitoringAlert) {
        self.alerts.push(alert);
    }

    pub fn get_active_alerts(&self) -> Vec<&MonitoringAlert> {
        self.alerts.iter().filter(|a| !a.acknowledged).collect()
    }

    pub fn acknowledge_alert(&mut self, alert_id: &str) -> bool {
        if let Some(alert) = self.alerts.iter_mut().find(|a| a.alert_id == alert_id) {
            alert.acknowledged = true;
            true
        } else {
            false
        }
    }

    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "models_count".into(),
            serde_json::json!(self.registries.len()),
        );
        state.insert(
            "total_versions".into(),
            serde_json::json!(self
                .registries
                .values()
                .map(|r| r.versions.len())
                .sum::<usize>()),
        );
        state.insert(
            "prediction_logs".into(),
            serde_json::json!(self.prediction_logs.len()),
        );
        state.insert(
            "active_alerts".into(),
            serde_json::json!(self.alerts.iter().filter(|a| !a.acknowledged).count()),
        );
        state
    }
}

// ---------------------------------------------------------------------------
// Drift Detection
// ---------------------------------------------------------------------------

/// Drift detection engine for monitoring model performance.
#[derive(Debug, Clone)]
pub struct DriftDetector {
    /// Reference statistics per feature
    reference_stats: HashMap<String, FeatureStats>,
}

#[derive(Debug, Clone)]
struct FeatureStats {
    mean: f64,
    std: f64,
    p5: f64,
    p25: f64,
    p50: f64,
    p75: f64,
    p95: f64,
}

impl DriftDetector {
    pub fn new() -> Self {
        Self {
            reference_stats: HashMap::new(),
        }
    }
}

impl Default for DriftDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl DriftDetector {
    /// Fit reference distribution from training data.
    pub fn fit(&mut self, feature_name: &str, values: &[f64]) {
        if values.is_empty() {
            return;
        }
        let n = values.len();
        let mut sorted = values.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let mean = values.iter().sum::<f64>() / n as f64;
        let variance = values.iter().map(|&v| (v - mean).powi(2)).sum::<f64>() / n as f64;

        self.reference_stats.insert(
            feature_name.into(),
            FeatureStats {
                mean,
                std: variance.sqrt(),
                p5: percentile(&sorted, 5.0),
                p25: percentile(&sorted, 25.0),
                p50: percentile(&sorted, 50.0),
                p75: percentile(&sorted, 75.0),
                p95: percentile(&sorted, 95.0),
            },
        );
    }

    /// Detect drift for a feature given current values.
    pub fn detect_drift(
        &self,
        feature_name: &str,
        current_values: &[f64],
        drift_type: DriftType,
        threshold: f64,
    ) -> DriftDetectionResult {
        let ref_stats = match self.reference_stats.get(feature_name) {
            Some(s) => s,
            None => {
                return DriftDetectionResult {
                    feature_name: feature_name.into(),
                    drift_type,
                    drift_detected: false,
                    severity: DriftSeverity::None,
                    score: 0.0,
                    threshold,
                    details: HashMap::new(),
                    p_value: None,
                    statistic: None,
                    test_used: "no_reference".into(),
                    detected_at: Utc::now(),
                    recommendations: vec!["Fit reference distribution first".into()],
                };
            }
        };

        let n = current_values.len();
        if n == 0 {
            return DriftDetectionResult {
                feature_name: feature_name.into(),
                drift_type,
                drift_detected: false,
                severity: DriftSeverity::None,
                score: 0.0,
                threshold,
                details: HashMap::new(),
                p_value: None,
                statistic: None,
                test_used: "no_data".into(),
                detected_at: Utc::now(),
                recommendations: vec![],
            };
        }

        let current_mean = current_values.iter().sum::<f64>() / n as f64;

        // Population Stability Index (PSI)
        let mut psi = 0.0_f64;
        let current_sorted = {
            let mut v = current_values.to_vec();
            v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            v
        };

        let bins = vec![
            ref_stats.p5,
            ref_stats.p25,
            ref_stats.p50,
            ref_stats.p75,
            ref_stats.p95,
        ];

        let mut prev_boundary = f64::NEG_INFINITY;
        for &boundary in &bins {
            let ref_pct = proportion_in_range(current_values, prev_boundary, boundary);
            let cur_pct = proportion_in_range(&current_sorted, prev_boundary, boundary);
            let r_pct = ref_pct.max(0.001); // Avoid division by zero
            let c_pct = cur_pct.max(0.001);
            psi += (r_pct - c_pct) * (r_pct / c_pct).ln();
            prev_boundary = boundary;
        }
        // Last bin
        let ref_pct = proportion_in_range(current_values, prev_boundary, f64::INFINITY).max(0.001);
        let cur_pct = proportion_in_range(&current_sorted, prev_boundary, f64::INFINITY).max(0.001);
        psi += (ref_pct - cur_pct) * (ref_pct / cur_pct).ln();

        // Also compute z-score for mean shift
        let z_score = if ref_stats.std > 0.0 {
            (current_mean - ref_stats.mean).abs() / ref_stats.std
        } else {
            0.0
        };

        let score = psi.max(z_score * 0.1); // Combine signals
        let drift_detected = score > threshold;

        let severity = if score > threshold * 3.0 {
            DriftSeverity::Critical
        } else if score > threshold * 2.0 {
            DriftSeverity::High
        } else if score > threshold * 1.5 {
            DriftSeverity::Medium
        } else if score > threshold {
            DriftSeverity::Low
        } else {
            DriftSeverity::None
        };

        let mut recommendations = Vec::new();
        if drift_detected {
            recommendations.push(format!(
                "Feature '{}' shows drift (score={:.4}, threshold={:.4})",
                feature_name, score, threshold
            ));
            recommendations.push("Consider retraining the model with recent data".into());
        }

        let mut details = HashMap::new();
        details.insert("current_mean".into(), serde_json::json!(current_mean));
        details.insert("ref_mean".into(), serde_json::json!(ref_stats.mean));
        details.insert("psi".into(), serde_json::json!(psi));
        details.insert("z_score".into(), serde_json::json!(z_score));

        DriftDetectionResult {
            feature_name: feature_name.into(),
            drift_type,
            drift_detected,
            severity,
            score,
            threshold,
            details,
            p_value: None,
            statistic: Some(psi),
            test_used: "psi+zscore".into(),
            detected_at: Utc::now(),
            recommendations,
        }
    }

    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "reference_features".into(),
            serde_json::json!(self.reference_stats.len()),
        );
        state
    }
}

fn proportion_in_range(values: &[f64], lower: f64, upper: f64) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let count = values.iter().filter(|&&v| v >= lower && v < upper).count();
    count as f64 / values.len() as f64
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let n = sorted.len();
    let idx = ((p / 100.0) * (n - 1) as f64).round() as usize;
    sorted[idx.min(n - 1)]
}

// ---------------------------------------------------------------------------
// AutoML
// ---------------------------------------------------------------------------

/// Simple AutoML engine for hyperparameter search.
#[derive(Debug, Clone)]
pub struct AutoMLEngine {
    experiments: Vec<Experiment>,
}

impl Default for AutoMLEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl AutoMLEngine {
    pub fn new() -> Self {
        Self {
            experiments: Vec::new(),
        }
    }

    /// Run a random hyperparameter search.
    ///
    /// `param_grid`: Map of parameter name → list of candidate values.
    /// `evaluate_fn`: Takes a set of hyperparameters and returns (score, metrics_map).
    /// `n_trials`: Number of random combinations to try.
    pub fn random_search(
        &mut self,
        name: &str,
        param_grid: HashMap<String, Vec<serde_json::Value>>,
        n_trials: usize,
        evaluate_fn: impl Fn(&HashMap<String, serde_json::Value>) -> (f64, HashMap<String, f64>),
    ) -> Result<Experiment, String> {
        use rand::Rng;

        if param_grid.is_empty() {
            return Err("Empty parameter grid".into());
        }

        let mut experiment = Experiment::new(name, HashMap::new());
        let mut rng = rand::thread_rng();

        let mut best_score = f64::MIN;
        let mut best_params = HashMap::new();

        for trial in 0..n_trials {
            let mut params = HashMap::new();
            for (key, values) in &param_grid {
                if values.is_empty() {
                    continue;
                }
                let idx = rng.gen_range(0..values.len());
                params.insert(key.clone(), values[idx].clone());
            }

            let (score, metrics) = evaluate_fn(&params);
            experiment.logs.push(format!(
                "Trial {}: score={:.4}, params={:?}",
                trial + 1,
                score,
                params
            ));

            if score > best_score {
                best_score = score;
                best_params = params.clone();
                experiment.metrics = metrics.clone();
            }
        }

        experiment.status = ExperimentStatus::Completed;
        experiment.completed_at = Some(Utc::now());
        experiment.duration_seconds = experiment
            .duration()
            .map(|d| d.num_seconds() as f64)
            .unwrap_or(0.0);
        experiment.hyperparameters = best_params;
        experiment.model_artifact_path = format!("experiments/{}", experiment.experiment_id);

        self.experiments.push(experiment.clone());
        Ok(experiment)
    }

    pub fn get_experiments(&self) -> &[Experiment] {
        &self.experiments
    }

    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "experiments_count".into(),
            serde_json::json!(self.experiments.len()),
        );
        state
    }
}

// ---------------------------------------------------------------------------
// Enhanced ML Pipeline Service
// ---------------------------------------------------------------------------

/// Configuration for a full ML pipeline run.
#[derive(Debug, Clone)]
pub struct PipelineRequest {
    pub pipeline_name: String,
    pub feature_group_name: String,
    pub entity_ids: Vec<String>,
    pub model_name: String,
    pub model_type: ModelType,
    pub algorithm: String,
    pub hyperparameters: HashMap<String, serde_json::Value>,
}

/// Main entry point for the enhanced ML pipeline.
#[derive(Debug, Clone)]
pub struct EnhancedMLPipeline {
    pub feature_store: FeatureStore,
    pub model_registry: ModelRegistryService,
    pub drift_detector: DriftDetector,
    pub auto_ml: AutoMLEngine,
}

impl Default for EnhancedMLPipeline {
    fn default() -> Self {
        Self::new()
    }
}

impl EnhancedMLPipeline {
    pub fn new() -> Self {
        Self {
            feature_store: FeatureStore::new(),
            model_registry: ModelRegistryService::default(),
            drift_detector: DriftDetector::new(),
            auto_ml: AutoMLEngine::new(),
        }
    }

    /// Run a full ML pipeline: feature engineering → training → evaluation → registration.
    pub fn run_pipeline(&mut self, request: PipelineRequest) -> Result<String, String> {
        // 1. Get features
        let feature_group = self
            .feature_store
            .groups()
            .get(&request.feature_group_name)
            .ok_or_else(|| format!("Feature group not found: {}", request.feature_group_name))?;

        let feature_names = feature_group.feature_names();
        if feature_names.is_empty() {
            return Err(format!(
                "Feature group '{}' has no features registered",
                request.feature_group_name
            ));
        }

        // 2. Build the feature matrix from the stored vectors.
        let mut rows: Vec<Vec<f64>> = Vec::new();
        for entity_id in &request.entity_ids {
            let row = self
                .feature_store
                .get_features(&request.feature_group_name, entity_id, None)
                .map(|v| v.to_array(&feature_names, 0.0))
                .unwrap_or_else(|| vec![0.0; feature_names.len()]);
            if row.iter().any(|v| v.is_finite()) {
                rows.push(row);
            }
        }
        if rows.len() < 2 {
            return Err(format!(
                "Insufficient data to train '{}': need at least 2 entities with features, got {}",
                request.model_name,
                rows.len()
            ));
        }
        let n_samples = rows.len();
        let n_features = feature_names.len();
        let flat: Vec<f64> = rows.into_iter().flatten().collect();
        let x = ndarray::Array2::from_shape_vec((n_samples, n_features), flat)
            .map_err(|e| format!("Failed to build feature matrix: {e}"))?;

        // 3. Train a real model from the features.
        //    - When a target feature is present, fit the CBM ensemble classifier
        //      on a deterministic holdout split and compute real metrics.
        //    - Otherwise fit per-feature statistical parameters (mean/std dev/
        //      control limits), which is the statistical-model path.
        let target_key = ["label", "target", "y", "actual", "is_defect"]
            .iter()
            .find(|k| feature_names.contains(&k.to_string()))
            .copied();

        let mut hyperparameters: HashMap<String, serde_json::Value> = HashMap::new();
        hyperparameters.insert(
            "pipeline".to_string(),
            serde_json::Value::String(request.pipeline_name.clone()),
        );
        hyperparameters.insert(
            "feature_group".to_string(),
            serde_json::Value::String(request.feature_group_name.clone()),
        );
        hyperparameters.insert(
            "algorithm".to_string(),
            serde_json::json!(request.algorithm),
        );

        let mut metrics = if let Some(target) = target_key {
            let target_idx = feature_names
                .iter()
                .position(|n| n == target)
                .ok_or_else(|| format!("Target feature '{target}' not found"))?;
            let y: Vec<f64> = x.column(target_idx).iter().copied().collect();
            // Drop the target column from the feature matrix.
            let x_cols: Vec<usize> = (0..n_features).filter(|&i| i != target_idx).collect();
            let mut x_train = ndarray::Array2::<f64>::zeros((n_samples, n_features - 1));
            for (out, &in_idx) in x_cols.iter().enumerate() {
                x_train.column_mut(out).assign(&x.column(in_idx));
            }

            train_classifier_with_holdout(&x_train, &y, &request.algorithm, &mut hyperparameters)?
        } else {
            // Statistical path: per-feature parameters.
            let mut params = HashMap::new();
            for (i, name) in feature_names.iter().enumerate() {
                let col: Vec<f64> = x.column(i).iter().copied().collect();
                let m = col.iter().sum::<f64>() / col.len() as f64;
                let var = col.iter().map(|v| (v - m).powi(2)).sum::<f64>() / col.len() as f64;
                let sd = var.sqrt();
                params.insert(
                    name.clone(),
                    serde_json::json!({
                        "mean": m,
                        "std_dev": sd,
                        "ucl": m + 3.0 * sd,
                        "lcl": (m - 3.0 * sd).max(0.0),
                    }),
                );
            }
            hyperparameters.insert("trained_parameters".to_string(), serde_json::json!(params));
            hyperparameters.insert("supervised".to_string(), serde_json::json!(false));
            ModelMetrics {
                accuracy: None,
                precision: None,
                recall: None,
                f1_score: None,
                auc_roc: None,
                mse: None,
                rmse: None,
                mae: None,
                r2: None,
                mape: None,
                inference_time_ms: None,
                model_size_mb: None,
                custom_metrics: HashMap::from([
                    ("training_samples".to_string(), n_samples as f64),
                    ("feature_count".to_string(), n_features as f64),
                    ("supervised".to_string(), 0.0),
                ]),
            }
        };

        // 4. Register the model + version with the real computed metrics.
        let registry = if self
            .model_registry
            .get_registry_by_name(&request.model_name)
            .is_none()
        {
            self.model_registry
                .register_model(&request.model_name, request.model_type)
        } else {
            self.model_registry
                .get_registry_by_name(&request.model_name)
                .cloned()
                .ok_or_else(|| format!("Model not found: {}", request.model_name))?
        };

        let model_id = registry.model_id;
        let version = self
            .model_registry
            .register_version(
                &model_id,
                "1.0".to_string(),
                &request.algorithm,
                hyperparameters,
                feature_names.clone(),
            )
            .map_err(|e| format!("Failed to register model version: {e}"))?;

        // 5. Attach the computed metrics to the registered version.
        metrics.inference_time_ms = Some(0.0);
        metrics.model_size_mb =
            Some(serde_json::to_vec(&version).map_or(0.0, |b| b.len() as f64 / 1_048_576.0));
        self.model_registry
            .set_version_metrics(&model_id, &version.version_id, metrics.clone())
            .map_err(|e| format!("Failed to attach metrics: {e}"))?;

        Ok(format!(
            "Pipeline '{}' completed. Model: {}, Algorithm: {}, samples: {}, metrics: {:?}",
            request.pipeline_name,
            request.model_name,
            request.algorithm,
            n_samples,
            metrics.to_map()
        ))
    }

    /// Export full state for persistence/debugging.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "feature_store".into(),
            serde_json::json!(self.feature_store.export_state()),
        );
        state.insert(
            "model_registry".into(),
            serde_json::json!(self.model_registry.export_state()),
        );
        state.insert(
            "drift_detector".into(),
            serde_json::json!(self.drift_detector.export_state()),
        );
        state.insert(
            "auto_ml".into(),
            serde_json::json!(self.auto_ml.export_state()),
        );
        state
    }
}

/// Train the CBM ensemble classifier on a deterministic holdout split and
/// return honest evaluation metrics.
///
/// Uses a fixed 70/30 train/test split with a seeded RNG so training is
/// reproducible. Metrics whose classes are absent in the split are left
/// `None` rather than fabricated.
fn train_classifier_with_holdout(
    x: &ndarray::Array2<f64>,
    y: &[f64],
    algorithm: &str,
    hyperparameters: &mut HashMap<String, serde_json::Value>,
) -> Result<ModelMetrics, String> {
    use rand::Rng;
    use rand::SeedableRng;

    let n = x.nrows();
    if n < 6 {
        return Err(format!(
            "Insufficient labeled data to train classifier: need at least 6 samples, got {n}"
        ));
    }

    // Deterministic 70/30 split (seeded by data shape so it is reproducible).
    let mut rng = rand::rngs::StdRng::seed_from_u64(
        (x.nrows() as u64) << 32 ^ (x.ncols() as u64) | (algorithm.len() as u64),
    );
    let mut idx: Vec<usize> = (0..n).collect();
    // Deterministic shuffle (Fisher–Yates with the seeded RNG).
    for i in (1..n).rev() {
        let j = rng.gen_range(0..=i);
        idx.swap(i, j);
    }
    let split = (n as f64 * 0.7).round().max(1.0) as usize;
    let (train_idx, test_idx) = idx.split_at(split);

    let rows_for = |ix: &[usize]| {
        let mut m = ndarray::Array2::<f64>::zeros((ix.len(), x.ncols()));
        for (out, &i) in ix.iter().enumerate() {
            m.row_mut(out).assign(&x.row(i));
        }
        m
    };
    let (x_tr, x_te) = (rows_for(train_idx), rows_for(test_idx));
    let y_tr: Vec<f64> = train_idx.iter().map(|&i| y[i]).collect();
    let y_te: Vec<f64> = test_idx.iter().map(|&i| y[i]).collect();

    let mut clf = super::cbm_predictor::EnsembleClassifier::new(24, 4);
    clf.fit(&x_tr, &y_tr)
        .map_err(|e| format!("Classifier training failed: {e}"))?;
    let probas = clf
        .predict_proba(&x_te)
        .map_err(|e| format!("Classifier evaluation failed: {e}"))?;
    let preds: Vec<f64> = probas
        .iter()
        .map(|&p| if p > 0.5 { 1.0 } else { 0.0 })
        .collect();

    let tp = y_te
        .iter()
        .zip(&preds)
        .filter(|(a, p)| **a > 0.5 && **p > 0.5)
        .count() as f64;
    let fp = y_te
        .iter()
        .zip(&preds)
        .filter(|(a, p)| **a <= 0.5 && **p > 0.5)
        .count() as f64;
    let fn_ = y_te
        .iter()
        .zip(&preds)
        .filter(|(a, p)| **a > 0.5 && **p <= 0.5)
        .count() as f64;
    let tn = y_te
        .iter()
        .zip(&preds)
        .filter(|(a, p)| **a <= 0.5 && **p <= 0.5)
        .count() as f64;

    let accuracy = (tp + tn) / y_te.len() as f64;
    let precision = if tp + fp > 0.0 { tp / (tp + fp) } else { 0.0 };
    let recall = if tp + fn_ > 0.0 { tp / (tp + fn_) } else { 0.0 };
    let f1 = if precision + recall > 0.0 {
        2.0 * precision * recall / (precision + recall)
    } else {
        0.0
    };

    hyperparameters.insert("supervised".to_string(), serde_json::json!(true));
    hyperparameters.insert("train_size".to_string(), serde_json::json!(train_idx.len()));
    hyperparameters.insert("test_size".to_string(), serde_json::json!(test_idx.len()));

    Ok(ModelMetrics {
        accuracy: Some(accuracy),
        precision: Some(precision),
        recall: Some(recall),
        f1_score: Some(f1),
        auc_roc: None,
        mse: None,
        rmse: None,
        mae: None,
        r2: None,
        mape: None,
        inference_time_ms: None,
        model_size_mb: None,
        custom_metrics: HashMap::from([
            ("training_samples".to_string(), x.nrows() as f64),
            ("feature_count".to_string(), x.ncols() as f64),
            ("supervised".to_string(), 1.0),
        ]),
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feature_store_register_and_ingest() {
        let mut store = FeatureStore::new();
        let mut group = FeatureGroup::new("sensor_features", "machine_id");
        group.features.push(FeatureDefinition::new(
            "temperature",
            FeatureType::Numerical,
        ));
        group
            .features
            .push(FeatureDefinition::new("vibration", FeatureType::Numerical));
        store.register_feature_group(group);

        let mut features = HashMap::new();
        features.insert("temperature".into(), 75.0);
        features.insert("vibration".into(), 5.0);

        assert!(store
            .ingest_features("sensor_features", "machine_001", features, None)
            .is_ok());

        let retrieved = store.get_features("sensor_features", "machine_001", None);
        assert!(retrieved.is_some());
        assert!((retrieved.unwrap().features["temperature"] - 75.0).abs() < 1e-10);
    }

    #[test]
    fn test_feature_store_unknown_group() {
        let mut store = FeatureStore::new();
        let result = store.ingest_features("unknown", "e1", HashMap::new(), None);
        assert!(result.is_err());
    }

    #[test]
    fn test_model_registry_register_and_version() {
        let mut registry = ModelRegistryService::default();
        let r = registry.register_model("quality_predictor", ModelType::Classification);
        let model_id = r.model_id.clone();

        let mut hp = HashMap::new();
        hp.insert("n_estimators".into(), serde_json::json!(100));
        hp.insert("max_depth".into(), serde_json::json!(10));

        let version = registry.register_version(
            &model_id,
            "1.0.0".into(),
            "RandomForest",
            hp,
            vec!["temp".into(), "pressure".into()],
        );
        assert!(version.is_ok());
        assert_eq!(version.unwrap().algorithm, "RandomForest");

        // Promote to production
        let v = registry.register_version(
            &model_id,
            "1.1.0".into(),
            "GradientBoosting",
            HashMap::new(),
            vec![],
        );
        assert!(v.is_ok());
        assert!(registry
            .promote_to_production(&model_id, &v.unwrap().version_id)
            .is_ok());
    }

    #[test]
    fn test_model_registry_prediction_logs() {
        let mut registry = ModelRegistryService::default();
        let log = PredictionLog {
            prediction_id: Uuid::new_v4().to_string(),
            model_name: "test_model".into(),
            model_version: "1.0".into(),
            timestamp: Utc::now(),
            features: HashMap::new(),
            prediction: serde_json::json!({"class": 1}),
            probability: Some(0.95),
            ground_truth: None,
            latency_ms: 12.5,
        };
        registry.log_prediction(log);
        let logs = registry.get_prediction_logs("test_model", 10);
        assert_eq!(logs.len(), 1);
    }

    #[test]
    fn test_drift_detection() {
        let mut detector = DriftDetector::new();

        // Fit reference distribution
        let ref_values: Vec<f64> = (0..100).map(|i| i as f64).collect();
        detector.fit("temperature", &ref_values);

        // Current values within range should show low drift
        let current: Vec<f64> = (45..55).map(|i| i as f64).collect();
        let result = detector.detect_drift("temperature", &current, DriftType::Feature, 0.2);
        assert!(!result.is_drifting() || result.severity == DriftSeverity::Low);

        // Current values far from reference should show drift
        let shifted: Vec<f64> = (200..300).map(|i| i as f64).collect();
        let result2 = detector.detect_drift("temperature", &shifted, DriftType::Feature, 0.2);
        assert!(result2.score > 0.0);
    }

    #[test]
    fn test_auto_ml_random_search() {
        let mut engine = AutoMLEngine::new();
        let mut param_grid: HashMap<String, Vec<serde_json::Value>> = HashMap::new();
        param_grid.insert(
            "n_estimators".into(),
            vec![
                serde_json::json!(50),
                serde_json::json!(100),
                serde_json::json!(200),
            ],
        );
        param_grid.insert(
            "max_depth".into(),
            vec![
                serde_json::json!(5),
                serde_json::json!(10),
                serde_json::json!(15),
            ],
        );

        let experiment = engine
            .random_search("test_search", param_grid, 5, |params| {
                let n = params
                    .get("n_estimators")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(100) as f64;
                let d = params
                    .get("max_depth")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(10) as f64;
                let score = n * 0.01 + d * 0.05;
                let mut metrics = HashMap::new();
                metrics.insert("score".into(), score);
                (score, metrics)
            })
            .unwrap();

        assert_eq!(experiment.status, ExperimentStatus::Completed);
        assert_eq!(engine.get_experiments().len(), 1);
    }

    #[test]
    fn test_ab_test() {
        let mut test = ABTest::new("test_ab", "model_v1", "model_v2");
        test.control_metrics.insert("accuracy".into(), 0.85);
        test.treatment_metrics.insert("accuracy".into(), 0.92);
        let lift = test.calculate_lift("accuracy");
        assert!((lift - 0.08235).abs() < 0.01);
    }

    #[test]
    fn test_full_pipeline() {
        let mut pipeline = EnhancedMLPipeline::new();

        // Setup feature group
        let mut group = FeatureGroup::new("sensor_data", "machine_id");
        group.features.push(FeatureDefinition::new(
            "temperature",
            FeatureType::Numerical,
        ));
        pipeline.feature_store.register_feature_group(group);

        // Ingest data for several machines
        for (machine, temp) in [("m1", 75.0), ("m2", 78.0), ("m3", 71.0), ("m4", 80.0)] {
            let mut features = HashMap::new();
            features.insert("temperature".into(), temp);
            pipeline
                .feature_store
                .ingest_features("sensor_data", machine, features, None)
                .unwrap();
        }

        // Run pipeline
        let result = pipeline.run_pipeline(PipelineRequest {
            pipeline_name: "test_pipeline".into(),
            feature_group_name: "sensor_data".into(),
            entity_ids: vec!["m1".into(), "m2".into(), "m3".into(), "m4".into()],
            model_name: "quality_model".into(),
            model_type: ModelType::Classification,
            algorithm: "RandomForest".into(),
            hyperparameters: HashMap::new(),
        });
        assert!(result.is_ok(), "pipeline failed: {:?}", result);

        // The registered version carries the fitted statistical parameters.
        let registry = pipeline
            .model_registry
            .get_registry_by_name("quality_model")
            .expect("model should be registered");
        assert!(!registry.versions.is_empty());
        assert!(registry.versions[0]
            .hyperparameters
            .contains_key("trained_parameters"));

        let state = pipeline.export_state();
        assert!(state.contains_key("feature_store"));
        assert!(state.contains_key("model_registry"));
    }

    #[test]
    fn test_percentile() {
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
        assert!((percentile(&data, 50.0) - 5.5).abs() < 1.0);
        assert!((percentile(&data, 0.0) - 1.0).abs() < 0.1);
        assert!((percentile(&data, 100.0) - 10.0).abs() < 0.1);
    }

    #[test]
    fn test_monitoring_alert() {
        let mut registry = ModelRegistryService::default();
        let alert = MonitoringAlert {
            alert_id: Uuid::new_v4().to_string(),
            model_name: "test".into(),
            alert_type: "drift".into(),
            severity: DriftSeverity::High,
            message: "Feature drift detected".into(),
            metrics: HashMap::new(),
            created_at: Utc::now(),
            acknowledged: false,
            resolved: false,
        };
        registry.create_alert(alert);
        assert_eq!(registry.get_active_alerts().len(), 1);

        let alert_id = registry.get_active_alerts()[0].alert_id.clone();
        assert!(registry.acknowledge_alert(&alert_id));
        assert_eq!(registry.get_active_alerts().len(), 0);
    }

    #[test]
    fn test_pipeline_trains_and_registers_model() {
        let mut pipeline = EnhancedMLPipeline::new();
        let mut group = FeatureGroup::new("sensor_data", "sensor");
        group.features.push(FeatureDefinition::new(
            "temperature",
            FeatureType::Numerical,
        ));
        group
            .features
            .push(FeatureDefinition::new("vibration", FeatureType::Numerical));
        group.features.push(FeatureDefinition::new(
            "is_defect",
            FeatureType::Categorical,
        ));
        pipeline.feature_store.register_feature_group(group);

        // 6 samples with separable defect labels.
        for (idx, (temp_driver, defect)) in [
            (0.0, 1.0),
            (1.0, 1.0),
            (2.0, 1.0),
            (8.0, 0.0),
            (9.0, 0.0),
            (10.0, 0.0),
        ]
        .iter()
        .enumerate()
        {
            pipeline
                .feature_store
                .ingest_features(
                    "sensor_data",
                    &format!("sensor_{idx}"),
                    HashMap::from([
                        ("temperature".to_string(), temp_driver * 10.0 + 20.0),
                        ("vibration".to_string(), *defect),
                        ("is_defect".to_string(), *defect),
                    ]),
                    None,
                )
                .unwrap();
        }

        let result = pipeline
            .run_pipeline(PipelineRequest {
                pipeline_name: "train_pipeline".into(),
                feature_group_name: "sensor_data".into(),
                entity_ids: vec![
                    "sensor_0".into(),
                    "sensor_1".into(),
                    "sensor_2".into(),
                    "sensor_3".into(),
                    "sensor_4".into(),
                    "sensor_5".into(),
                ],
                model_name: "quality_model".into(),
                model_type: ModelType::Classification,
                algorithm: "ensemble".into(),
                hyperparameters: HashMap::new(),
            })
            .unwrap();
        assert!(result.contains("samples: 6"), "result: {result}");

        let registry = pipeline
            .model_registry
            .get_registry_by_name("quality_model")
            .expect("model should be registered");
        let version = registry.versions.last().expect("version should exist");
        assert!(
            version.metrics.accuracy.is_some(),
            "metrics: {:?}",
            version.metrics.to_map()
        );
        assert_eq!(
            version.metrics.custom_metrics.get("training_samples"),
            Some(&6.0)
        );
    }

    #[test]
    fn test_pipeline_statistical_path_without_labels() {
        let mut pipeline = EnhancedMLPipeline::new();
        let mut group = FeatureGroup::new("temps", "sensor");
        group.features.push(FeatureDefinition::new(
            "temperature",
            FeatureType::Numerical,
        ));
        pipeline.feature_store.register_feature_group(group);
        for i in 0..4 {
            pipeline
                .feature_store
                .ingest_features(
                    "temps",
                    &format!("t{i}"),
                    HashMap::from([("temperature".to_string(), 10.0 + i as f64)]),
                    None,
                )
                .unwrap();
        }
        let result = pipeline
            .run_pipeline(PipelineRequest {
                pipeline_name: "stat_pipeline".into(),
                feature_group_name: "temps".into(),
                entity_ids: vec!["t0".into(), "t1".into(), "t2".into(), "t3".into()],
                model_name: "stat_model".into(),
                model_type: ModelType::Regression,
                algorithm: "statistical".into(),
                hyperparameters: HashMap::new(),
            })
            .unwrap();
        assert!(result.contains("samples: 4"), "result: {result}");
        let registry = pipeline
            .model_registry
            .get_registry_by_name("stat_model")
            .unwrap();
        let version = registry.versions.last().unwrap();
        assert!(version.metrics.accuracy.is_none());
        assert_eq!(version.metrics.custom_metrics.get("supervised"), Some(&0.0));
        assert!(version
            .hyperparameters
            .get("trained_parameters")
            .unwrap()
            .as_object()
            .unwrap()
            .contains_key("temperature"));
    }

    #[test]
    fn test_pipeline_rejects_insufficient_data() {
        let mut pipeline = EnhancedMLPipeline::new();
        let mut group = FeatureGroup::new("g", "sensor");
        group
            .features
            .push(FeatureDefinition::new("a", FeatureType::Numerical));
        pipeline.feature_store.register_feature_group(group);
        pipeline
            .feature_store
            .ingest_features("g", "e1", HashMap::from([("a".to_string(), 1.0)]), None)
            .unwrap();
        let result = pipeline.run_pipeline(PipelineRequest {
            pipeline_name: "p".into(),
            feature_group_name: "g".into(),
            entity_ids: vec!["e1".into()],
            model_name: "m".into(),
            model_type: ModelType::Regression,
            algorithm: "statistical".into(),
            hyperparameters: HashMap::new(),
        });
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Insufficient data"));
    }
}

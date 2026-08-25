//! Continuous Learning — Feedback Collection, Retraining Management, and Drift Detection.
//!
//! Ported from [`continuous_learning.py`](backend/src/sensei/services/ai/continuous_learning.py).
//!
//! # Components
//!
//! - [`FeedbackCollector`] — Collects and stores feedback (predictions + corrections),
//!   prepares training data, and manages feedback buffers.
//! - [`RetrainingManager`] — Manages retraining jobs, detects drift, tracks model
//!   performance, and enforces scheduling/cooldown policies.
//! - [`ContinuousLearningService`] — Orchestrates feedback collection and retraining
//!   with a unified API.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Learning mode for a model.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LearningMode {
    Batch,
    Incremental,
    Online,
}

/// What triggered a retraining job.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RetrainingTrigger {
    Scheduled,
    DriftDetected,
    PerformanceDegradation,
    Manual,
    DataThresholdReached,
}

/// Source of feedback.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FeedbackSource {
    User,
    Automated,
    System,
    Validation,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A single piece of feedback for learning.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearningFeedback {
    pub id: Uuid,
    pub model_name: String,
    pub prediction: serde_json::Value,
    pub actual: serde_json::Value,
    pub features: HashMap<String, f64>,
    pub source: FeedbackSource,
    pub correct: bool,
    pub confidence: f64,
    pub timestamp: DateTime<Utc>,
}

/// A retraining job.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrainingJob {
    pub id: Uuid,
    pub model_name: String,
    pub trigger: RetrainingTrigger,
    pub status: String,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub accuracy_before: Option<f64>,
    pub accuracy_after: Option<f64>,
    pub data_size: usize,
    pub error: Option<String>,
}

/// Configuration for retraining behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrainingConfig {
    pub schedule_interval_hours: i64,
    pub min_data_threshold: usize,
    pub max_concurrent_jobs: usize,
    pub performance_degradation_threshold: f64,
    pub cooldown_hours: i64,
}

impl Default for RetrainingConfig {
    fn default() -> Self {
        Self {
            schedule_interval_hours: 168,     // 7 days
            min_data_threshold: 100,
            max_concurrent_jobs: 2,
            performance_degradation_threshold: 0.05, // 5 % degradation triggers retrain
            cooldown_hours: 24,
        }
    }
}

/// Tracking state for a model's learning progress.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelLearningState {
    pub model_name: String,
    pub learning_mode: LearningMode,
    pub accuracy: f64,
    pub data_size: usize,
    pub last_trained_at: Option<DateTime<Utc>>,
    pub last_drift_check_at: Option<DateTime<Utc>>,
    pub is_training: bool,
    pub version: String,
    pub created_at: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// FeedbackCollector
// ---------------------------------------------------------------------------

/// Collects and manages feedback data for model training.
///
/// Maintains separate feedback buffers per model, with configurable capacity
/// and callback support.
pub struct FeedbackCollector {
    /// Feedback buffer per model.
    feedback_buffers: HashMap<String, Vec<LearningFeedback>>,
    /// Maximum feedback entries per model.
    max_buffer_size: usize,
    /// Feature names known across all models.
    known_features: HashMap<String, Vec<String>>,
}

impl FeedbackCollector {
    /// Create a new [`FeedbackCollector`] with the given buffer size limit.
    pub fn new(max_buffer_size: usize) -> Self {
        Self {
            feedback_buffers: HashMap::new(),
            max_buffer_size,
            known_features: HashMap::new(),
        }
    }

    /// Ensure a feature group exists for a model.
    fn ensure_feature_group(&mut self, model_name: &str) -> &mut Vec<String> {
        self.known_features
            .entry(model_name.to_string())
            .or_default()
    }

    /// Record a feedback entry.
    ///
    /// If the buffer exceeds capacity, the oldest entries are evicted (first 25 %).
    pub fn record_feedback(&mut self, feedback: LearningFeedback) {
        let model = feedback.model_name.clone();

        // Track feature names
        let features = self.ensure_feature_group(&model);
        for feature_name in feedback.features.keys() {
            if !features.contains(feature_name) {
                features.push(feature_name.clone());
            }
        }

        let buffer = self
            .feedback_buffers
            .entry(model)
            .or_insert_with(|| Vec::with_capacity(self.max_buffer_size));

        buffer.push(feedback);

        // Evict oldest 25 % if over capacity
        if buffer.len() > self.max_buffer_size {
            let to_remove = self.max_buffer_size / 4;
            buffer.drain(..to_remove);
        }
    }

    /// Record a user correction (feedback where the user explicitly corrected a prediction).
    pub fn record_user_correction(
        &mut self,
        model_name: &str,
        prediction: serde_json::Value,
        correction: serde_json::Value,
        features: HashMap<String, f64>,
        confidence: f64,
    ) {
        let feedback = LearningFeedback {
            id: Uuid::new_v4(),
            model_name: model_name.to_string(),
            prediction,
            actual: correction,
            features,
            source: FeedbackSource::User,
            correct: false,
            confidence,
            timestamp: Utc::now(),
        };
        self.record_feedback(feedback);
    }

    /// Get feedback entries for training (up to the specified limit).
    pub fn get_feedback_for_training(
        &self,
        model_name: &str,
        limit: Option<usize>,
    ) -> Vec<&LearningFeedback> {
        let buffer = match self.feedback_buffers.get(model_name) {
            Some(b) => b,
            None => return Vec::new(),
        };

        match limit {
            Some(max) => buffer.iter().rev().take(max).collect(),
            None => buffer.iter().collect(),
        }
    }

    /// Prepare training data from accumulated feedback.
    ///
    /// Returns (feature_matrix, labels) as parallel vectors of (features, is_correct).
    pub fn prepare_training_data(
        &self,
        model_name: &str,
    ) -> (Vec<HashMap<String, f64>>, Vec<bool>) {
        let buffer = match self.feedback_buffers.get(model_name) {
            Some(b) => b,
            None => return (Vec::new(), Vec::new()),
        };

        let features: Vec<HashMap<String, f64>> = buffer
            .iter()
            .map(|f| f.features.clone())
            .collect();

        let labels: Vec<bool> = buffer.iter().map(|f| f.correct).collect();

        (features, labels)
    }

    /// Clear all feedback for a model, returning the count of removed entries.
    pub fn clear_feedback(&mut self, model_name: &str) -> usize {
        match self.feedback_buffers.remove(model_name) {
            Some(buffer) => buffer.len(),
            None => 0,
        }
    }

    /// Get statistics about the feedback collector.
    pub fn get_statistics(&self) -> HashMap<String, serde_json::Value> {
        let mut stats = HashMap::new();
        stats.insert(
            "models_tracked".to_string(),
            serde_json::Value::Number(serde_json::Number::from(
                self.feedback_buffers.len() as u64,
            )),
        );

        let total_feedback: usize = self
            .feedback_buffers
            .values()
            .map(|b| b.len())
            .sum();
        stats.insert(
            "total_feedback".to_string(),
            serde_json::Value::Number(serde_json::Number::from(total_feedback as u64)),
        );

        stats
    }

    /// Export state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "feedback_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(
                self.feedback_buffers
                    .values()
                    .map(|b| b.len())
                    .sum::<usize>() as u64,
            )),
        );
        state
    }
}

impl Default for FeedbackCollector {
    fn default() -> Self {
        Self::new(10_000)
    }
}

// ---------------------------------------------------------------------------
// RetrainingManager
// ---------------------------------------------------------------------------

/// Manages retraining jobs, drift detection, and scheduling for ML models.
///
/// Tracks model performance, detects degradation, and enforces retraining
/// policies such as concurrency limits and cooldowns.
pub struct RetrainingManager {
    /// Configuration for retraining behavior.
    config: RetrainingConfig,
    /// Current retraining jobs.
    jobs: Vec<RetrainingJob>,
    /// Model states.
    model_states: HashMap<String, ModelLearningState>,
    /// Performance history per model (accuracy snapshots).
    performance_history: HashMap<String, Vec<(DateTime<Utc>, f64)>>,
    /// Maximum history entries per model.
    max_history_per_model: usize,
}

impl RetrainingManager {
    /// Create a new [`RetrainingManager`] with the given configuration.
    pub fn new(config: RetrainingConfig) -> Self {
        Self {
            config,
            jobs: Vec::new(),
            model_states: HashMap::new(),
            performance_history: HashMap::new(),
            max_history_per_model: 100,
        }
    }

    /// Register a model for retraining management.
    pub fn register_model(
        &mut self,
        model_name: &str,
        learning_mode: LearningMode,
        initial_accuracy: f64,
    ) {
        let state = ModelLearningState {
            model_name: model_name.to_string(),
            learning_mode,
            accuracy: initial_accuracy,
            data_size: 0,
            last_trained_at: None,
            last_drift_check_at: None,
            is_training: false,
            version: "v0.1.0".to_string(),
            created_at: Utc::now(),
        };
        self.model_states
            .insert(model_name.to_string(), state);
        self.performance_history
            .entry(model_name.to_string())
            .or_default();
    }

    /// Check if retraining is needed for a model.
    ///
    /// Returns a list of reasons why retraining is needed (empty = no retraining needed).
    pub fn check_retraining_needed(&self, model_name: &str) -> Vec<String> {
        let mut reasons = Vec::new();

        let state = match self.model_states.get(model_name) {
            Some(s) => s,
            None => return reasons,
        };

        // Check if currently training
        if state.is_training {
            return reasons;
        }

        // 1. Scheduled retraining
        if let Some(last_trained) = state.last_trained_at {
            let elapsed = Utc::now() - last_trained;
            if elapsed.num_hours() >= self.config.schedule_interval_hours {
                reasons.push(format!(
                    "Scheduled retraining interval ({}) reached",
                    self.config.schedule_interval_hours
                ));
            }
        } else {
            reasons.push("Model has never been trained".to_string());
        }

        // 2. Data threshold
        if state.data_size >= self.config.min_data_threshold {
            reasons.push(format!(
                "Data threshold ({}) reached, have {} samples",
                self.config.min_data_threshold, state.data_size
            ));
        }

        // 3. Performance degradation
        if let Some(degradation) = self.calculate_degradation(model_name) {
            if self.severity_meets_threshold(degradation) {
                reasons.push(format!(
                    "Performance degraded by {:.1}%",
                    degradation * 100.0
                ));
            }
        }

        // 4. Distribution drift (PSI)
        if let Some(psi) = self.check_drift(model_name) {
            if self.severity_meets_threshold(psi * 0.2) {
                reasons.push(format!(
                    "Drift detected (PSI = {psi:.3})"
                ));
            }
        }

        reasons
    }

    /// Check for drift based on the recent vs historical accuracy
    /// distribution using the Population Stability Index (PSI).
    ///
    /// Returns `Some(psi)` when there is enough history; `None` otherwise.
    /// A PSI above 0.25 indicates a significant distribution shift.
    pub fn check_drift(&self, model_name: &str) -> Option<f64> {
        let history = self.performance_history.get(model_name)?;
        if history.len() < 6 {
            return None; // Not enough data points to compare distributions
        }

        // Recent window (last 3 snapshots) vs historical baseline (before that).
        let recent: Vec<f64> = history.iter().rev().take(3).map(|(_, acc)| *acc).collect();
        let historical: Vec<f64> = history
            .iter()
            .rev()
            .skip(3)
            .take(20)
            .map(|(_, acc)| *acc)
            .collect();

        if recent.len() < 3 || historical.len() < 3 {
            return None;
        }

        // PSI over 10 fixed-width bins across [0, 1].
        const BINS: usize = 10;
        const EPSILON: f64 = 1e-4;
        let mut psi = 0.0_f64;
        for bin in 0..BINS {
            let lo = bin as f64 / BINS as f64;
            let hi = (bin + 1) as f64 / BINS as f64;
            let in_bin = |v: &f64| *v >= lo && (*v < hi || (bin == BINS - 1 && *v <= hi));
            let expected = historical.iter().filter(|v| in_bin(v)).count() as f64
                / historical.len() as f64;
            let actual = recent.iter().filter(|v| in_bin(v)).count() as f64 / recent.len() as f64;

            let expected_s = (expected + EPSILON).max(EPSILON);
            let actual_s = (actual + EPSILON).max(EPSILON);
            psi += (actual_s - expected_s) * (actual_s / expected_s).ln();
        }

        Some(psi)
    }

    /// Check if a severity level meets the threshold for action.
    fn severity_meets_threshold(&self, severity: f64) -> bool {
        severity >= self.config.performance_degradation_threshold
    }

    /// Calculate performance degradation for a model.
    fn calculate_degradation(&self, model_name: &str) -> Option<f64> {
        let history = self.performance_history.get(model_name)?;
        if history.len() < 4 {
            return None; // Not enough data points
        }

        // Compare recent accuracy to historical baseline
        let recent: Vec<f64> = history.iter().rev().take(3).map(|(_, acc)| *acc).collect();
        let historical: Vec<f64> = history
            .iter()
            .rev()
            .skip(3)
            .take(10)
            .map(|(_, acc)| *acc)
            .collect();

        if recent.is_empty() || historical.is_empty() {
            return None;
        }

        let recent_avg = recent.iter().sum::<f64>() / recent.len() as f64;
        let historical_avg = historical.iter().sum::<f64>() / historical.len() as f64;

        if historical_avg > 0.0 {
            Some((historical_avg - recent_avg) / historical_avg)
        } else {
            None
        }
    }

    /// Trigger retraining for a model.
    ///
    /// Returns a [`RetrainingJob`] if retraining was started, or `None` if
    /// concurrency limits or cooldowns prevent it.
    pub fn trigger_retraining(
        &mut self,
        model_name: &str,
        trigger: RetrainingTrigger,
        data_size: usize,
    ) -> Option<RetrainingJob> {
        // Check concurrency limit
        let running_jobs = self
            .jobs
            .iter()
            .filter(|j| j.status == "running" || j.status == "pending")
            .count();
        if running_jobs >= self.config.max_concurrent_jobs {
            return None;
        }

        // Check cooldown
        let state = self.model_states.get(model_name)?;
        if let Some(last_trained) = state.last_trained_at {
            let elapsed = Utc::now() - last_trained;
            if elapsed.num_hours() < self.config.cooldown_hours {
                return None;
            }
        }

        let now = Utc::now();
        let job = RetrainingJob {
            id: Uuid::new_v4(),
            model_name: model_name.to_string(),
            trigger,
            status: "running".to_string(),
            started_at: now,
            completed_at: None,
            accuracy_before: Some(state.accuracy),
            accuracy_after: None,
            data_size,
            error: None,
        };

        // Mark model as training
        if let Some(s) = self.model_states.get_mut(model_name) {
            s.is_training = true;
        }

        self.jobs.push(job.clone());
        Some(job)
    }

    /// Complete a retraining job with results.
    pub fn complete_retraining(
        &mut self,
        job_id: Uuid,
        new_accuracy: f64,
    ) -> Option<&RetrainingJob> {
        let job = self.jobs.iter_mut().find(|j| j.id == job_id)?;
        job.status = "completed".to_string();
        job.completed_at = Some(Utc::now());
        job.accuracy_after = Some(new_accuracy);

        // Update model state
        if let Some(state) = self.model_states.get_mut(&job.model_name) {
            state.accuracy = new_accuracy;
            state.last_trained_at = Some(Utc::now());
            state.is_training = false;

            // Track performance history
            let history = self
                .performance_history
                .entry(state.model_name.clone())
                .or_default();
            history.push((Utc::now(), new_accuracy));

            // Trim history
            if history.len() > self.max_history_per_model {
                history.drain(..history.len() - self.max_history_per_model);
            }
        }

        Some(job)
    }

    /// Mark a retraining job as failed.
    pub fn fail_retraining(&mut self, job_id: Uuid, error: String) -> Option<&RetrainingJob> {
        let job = self.jobs.iter_mut().find(|j| j.id == job_id)?;
        job.status = "failed".to_string();
        job.completed_at = Some(Utc::now());
        job.error = Some(error);

        // Reset model training flag
        if let Some(state) = self.model_states.get_mut(&job.model_name) {
            state.is_training = false;
        }

        Some(job)
    }

    /// Get retraining history for a model.
    pub fn get_retraining_history(&self, model_name: &str) -> Vec<&RetrainingJob> {
        self.jobs
            .iter()
            .filter(|j| j.model_name == model_name)
            .collect()
    }

    /// Get statistics about the retraining manager.
    pub fn get_statistics(&self) -> HashMap<String, serde_json::Value> {
        let mut stats = HashMap::new();
        stats.insert(
            "total_jobs".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.jobs.len() as u64)),
        );
        stats.insert(
            "running_jobs".to_string(),
            serde_json::Value::Number(serde_json::Number::from(
                self.jobs
                    .iter()
                    .filter(|j| j.status == "running")
                    .count() as u64,
            )),
        );
        stats.insert(
            "models_registered".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.model_states.len() as u64)),
        );
        stats
    }

    /// Get the model learning state.
    pub fn get_model_state(&self, model_name: &str) -> Option<&ModelLearningState> {
        self.model_states.get(model_name)
    }

    /// Export state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "job_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.jobs.len() as u64)),
        );
        state
    }
}

impl Default for RetrainingManager {
    fn default() -> Self {
        Self::new(RetrainingConfig::default())
    }
}

// ---------------------------------------------------------------------------
// ContinuousLearningService
// ---------------------------------------------------------------------------

/// Unified service that orchestrates feedback collection and retraining.
pub struct ContinuousLearningService {
    pub feedback_collector: FeedbackCollector,
    pub retraining_manager: RetrainingManager,
}

impl ContinuousLearningService {
    /// Create a new [`ContinuousLearningService`].
    pub fn new() -> Self {
        Self {
            feedback_collector: FeedbackCollector::default(),
            retraining_manager: RetrainingManager::default(),
        }
    }

    /// Register a model for learning and retraining.
    pub fn register_model(
        &mut self,
        model_name: &str,
        learning_mode: LearningMode,
        initial_accuracy: f64,
    ) {
        self.retraining_manager
            .register_model(model_name, learning_mode, initial_accuracy);
    }

    /// Log a prediction and its outcome for feedback collection.
    pub fn log_prediction(
        &mut self,
        model_name: &str,
        prediction: serde_json::Value,
        features: HashMap<String, f64>,
        confidence: f64,
    ) {
        // Create a "pending" feedback until we know the actual outcome
        let feedback = LearningFeedback {
            id: Uuid::new_v4(),
            model_name: model_name.to_string(),
            prediction,
            actual: serde_json::Value::Null,
            features,
            source: FeedbackSource::System,
            correct: false, // Unknown until validated
            confidence,
            timestamp: Utc::now(),
        };
        self.feedback_collector.record_feedback(feedback);
    }

    /// Record a user correction for model improvement.
    pub fn record_correction(
        &mut self,
        model_name: &str,
        prediction: serde_json::Value,
        correction: serde_json::Value,
        features: HashMap<String, f64>,
        confidence: f64,
    ) {
        self.feedback_collector.record_user_correction(
            model_name,
            prediction,
            correction,
            features,
            confidence,
        );

        // Increment data size for the model
        if let Some(state) = self
            .retraining_manager
            .model_states
            .get_mut(model_name)
        {
            state.data_size = self
                .feedback_collector
                .feedback_buffers
                .get(model_name)
                .map_or(0, |b| b.len());
        }
    }

    /// Check if retraining is needed and trigger it if so.
    ///
    /// Returns the retraining job if one was started.
    pub fn check_and_retrain_if_needed(
        &mut self,
        model_name: &str,
    ) -> Option<RetrainingJob> {
        let reasons = self.retraining_manager.check_retraining_needed(model_name);
        if reasons.is_empty() {
            return None;
        }

        // Determine trigger based on reasons
        let trigger = if reasons.iter().any(|r| r.contains("Drift")) {
            RetrainingTrigger::DriftDetected
        } else if reasons.iter().any(|r| r.contains("degrad")) {
            RetrainingTrigger::PerformanceDegradation
        } else {
            RetrainingTrigger::Scheduled
        };

        let data_size = self
            .feedback_collector
            .feedback_buffers
            .get(model_name)
            .map_or(0, |b| b.len());

        self.retraining_manager
            .trigger_retraining(model_name, trigger, data_size)
    }

    /// Force retraining for a model.
    pub fn force_retrain(
        &mut self,
        model_name: &str,
    ) -> Option<RetrainingJob> {
        let data_size = self
            .feedback_collector
            .feedback_buffers
            .get(model_name)
            .map_or(0, |b| b.len());

        self.retraining_manager
            .trigger_retraining(model_name, RetrainingTrigger::Manual, data_size)
    }

    /// Get model health information.
    pub fn get_model_health(&self, model_name: &str) -> HashMap<String, serde_json::Value> {
        let mut health = HashMap::new();

        if let Some(state) = self.retraining_manager.get_model_state(model_name) {
            health.insert(
                "accuracy".to_string(),
                serde_json::Value::Number(
                    serde_json::Number::from_f64(state.accuracy).unwrap_or(serde_json::Number::from(0)),
                ),
            );
            health.insert(
                "data_size".to_string(),
                serde_json::Value::Number(serde_json::Number::from(state.data_size as u64)),
            );
            health.insert(
                "is_training".to_string(),
                serde_json::Value::Bool(state.is_training),
            );
            health.insert(
                "version".to_string(),
                serde_json::Value::String(state.version.clone()),
            );

            // Check if retraining is needed
            let reasons = self.retraining_manager.check_retraining_needed(model_name);
            health.insert(
                "retraining_needed".to_string(),
                serde_json::Value::Bool(!reasons.is_empty()),
            );
            health.insert(
                "retraining_reasons".to_string(),
                serde_json::Value::Array(
                    reasons
                        .into_iter()
                        .map(serde_json::Value::String)
                        .collect(),
                ),
            );
        }

        health
    }

    /// Get overall statistics.
    pub fn get_statistics(&self) -> HashMap<String, serde_json::Value> {
        let mut stats = self.feedback_collector.get_statistics();
        stats.extend(self.retraining_manager.get_statistics());
        stats
    }
}

impl Default for ContinuousLearningService {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- FeedbackCollector Tests ---------------------------------------------

    #[test]
    fn test_record_feedback() {
        let mut collector = FeedbackCollector::new(100);
        let feedback = LearningFeedback {
            id: Uuid::new_v4(),
            model_name: "test_model".to_string(),
            prediction: serde_json::json!("defect"),
            actual: serde_json::json!("ok"),
            features: [("temp".to_string(), 85.0)].into(),
            source: FeedbackSource::User,
            correct: false,
            confidence: 0.9,
            timestamp: Utc::now(),
        };

        collector.record_feedback(feedback);
        let data = collector.get_feedback_for_training("test_model", None);
        assert_eq!(data.len(), 1);
    }

    #[test]
    fn test_buffer_eviction() {
        let mut collector = FeedbackCollector::new(10);
        for i in 0..15 {
            let feedback = LearningFeedback {
                id: Uuid::new_v4(),
                model_name: "model".to_string(),
                prediction: serde_json::json!(i),
                actual: serde_json::json!(i),
                features: HashMap::new(),
                source: FeedbackSource::System,
                correct: true,
                confidence: 1.0,
                timestamp: Utc::now(),
            };
            collector.record_feedback(feedback);
        }

        // Max 10, evict 25% (2-3), so should have 10 or fewer
        let data = collector.get_feedback_for_training("model", None);
        assert!(data.len() <= 10);
    }

    #[test]
    fn test_user_correction() {
        let mut collector = FeedbackCollector::new(100);
        collector.record_user_correction(
            "quality_model",
            serde_json::json!("defect"),
            serde_json::json!("ok"),
            [("pressure".to_string(), 4.2)].into(),
            0.85,
        );

        let data = collector.get_feedback_for_training("quality_model", None);
        assert_eq!(data.len(), 1);
        assert_eq!(data[0].source, FeedbackSource::User);
    }

    #[test]
    fn test_prepare_training_data() {
        let mut collector = FeedbackCollector::new(100);

        for i in 0..5 {
            let feedback = LearningFeedback {
                id: Uuid::new_v4(),
                model_name: "model".to_string(),
                prediction: serde_json::json!(i),
                actual: serde_json::json!(i),
                features: [("feature_1".to_string(), i as f64)].into(),
                source: FeedbackSource::System,
                correct: i % 2 == 0,
                confidence: 1.0,
                timestamp: Utc::now(),
            };
            collector.record_feedback(feedback);
        }

        let (features, labels) = collector.prepare_training_data("model");
        assert_eq!(features.len(), 5);
        assert_eq!(labels.len(), 5);
        assert_eq!(labels.iter().filter(|&&l| l).count(), 3); // 3 even numbers
    }

    #[test]
    fn test_clear_feedback() {
        let mut collector = FeedbackCollector::new(100);
        collector.record_feedback(LearningFeedback {
            id: Uuid::new_v4(),
            model_name: "m".to_string(),
            prediction: serde_json::Value::Null,
            actual: serde_json::Value::Null,
            features: HashMap::new(),
            source: FeedbackSource::System,
            correct: true,
            confidence: 1.0,
            timestamp: Utc::now(),
        });

        assert_eq!(collector.clear_feedback("m"), 1);
        assert_eq!(collector.clear_feedback("nonexistent"), 0);
    }

    // -- RetrainingManager Tests ---------------------------------------------

    #[test]
    fn test_register_model() {
        let mut manager = RetrainingManager::default();
        manager.register_model("anomaly_detector", LearningMode::Incremental, 0.85);
        let state = manager.get_model_state("anomaly_detector");
        assert!(state.is_some());
        assert!((state.unwrap().accuracy - 0.85).abs() < 0.001);
    }

    #[test]
    fn test_retraining_needed_never_trained() {
        let mut manager = RetrainingManager::default();
        manager.register_model("model_1", LearningMode::Batch, 0.9);
        let reasons = manager.check_retraining_needed("model_1");
        assert!(reasons.iter().any(|r| r.contains("never been trained")));
    }

    #[test]
    fn test_trigger_and_complete_retraining() {
        let mut manager = RetrainingManager::default();
        manager.register_model("model_1", LearningMode::Incremental, 0.90);

        let job = manager
            .trigger_retraining("model_1", RetrainingTrigger::Manual, 500)
            .expect("Should start retraining");
        assert_eq!(job.status, "running");

        let completed = manager.complete_retraining(job.id, 0.95);
        assert!(completed.is_some());
        assert_eq!(completed.unwrap().status, "completed");

        let state = manager.get_model_state("model_1").unwrap();
        assert!((state.accuracy - 0.95).abs() < 0.001);
        assert!(!state.is_training);
    }

    #[test]
    fn test_concurrent_job_limit() {
        let config = RetrainingConfig {
            max_concurrent_jobs: 1,
            ..RetrainingConfig::default()
        };
        let mut manager = RetrainingManager::new(config);

        manager.register_model("model_a", LearningMode::Batch, 0.8);
        manager.register_model("model_b", LearningMode::Batch, 0.8);

        // First should succeed
        assert!(manager
            .trigger_retraining("model_a", RetrainingTrigger::Manual, 100)
            .is_some());

        // Second should be blocked by concurrency limit
        assert!(manager
            .trigger_retraining("model_b", RetrainingTrigger::Manual, 100)
            .is_none());
    }

    #[test]
    fn test_fail_retraining() {
        let mut manager = RetrainingManager::default();
        manager.register_model("model_1", LearningMode::Online, 0.85);

        let job = manager
            .trigger_retraining("model_1", RetrainingTrigger::Manual, 10)
            .unwrap();
        let failed = manager.fail_retraining(job.id, "Out of memory".to_string());
        assert!(failed.is_some());
        assert_eq!(failed.unwrap().status, "failed");

        let state = manager.get_model_state("model_1").unwrap();
        assert!(!state.is_training);
    }

    #[test]
    fn test_drift_detection_psi() {
        let config = RetrainingConfig {
            cooldown_hours: 0,
            ..RetrainingConfig::default()
        };
        let mut manager = RetrainingManager::new(config);
        manager.register_model("drift_model", LearningMode::Incremental, 0.90);

        // Stable historical performance around 0.9.
        for i in 0..8 {
            let job = manager
                .trigger_retraining("drift_model", RetrainingTrigger::Manual, 100)
                .expect("should start retraining");
            let acc = 0.88 + (i % 3) as f64 * 0.01;
            manager.complete_retraining(job.id, acc);
        }
        // No drift yet: recent accuracy is in the same band.
        assert!(manager.check_drift("drift_model").is_some());
        let reasons = manager.check_retraining_needed("drift_model");
        assert!(!reasons.iter().any(|r| r.contains("Drift")));

        // Now collapse accuracy → a different band.
        for _ in 0..3 {
            let job = manager
                .trigger_retraining("drift_model", RetrainingTrigger::Manual, 100)
                .expect("should start retraining");
            manager.complete_retraining(job.id, 0.45);
        }
        let reasons = manager.check_retraining_needed("drift_model");
        assert!(reasons.iter().any(|r| r.contains("Drift")), "reasons: {reasons:?}");
    }

    // -- ContinuousLearningService Integration Tests -------------------------

    #[test]
    fn test_full_continuous_learning_workflow() {
        let mut service = ContinuousLearningService::new();

        // Register a model
        service.register_model("quality_predictor", LearningMode::Incremental, 0.92);

        // Log some predictions
        for i in 0..10 {
            let features = [("temp".to_string(), 80.0 + i as f64)].into();
            service.log_prediction(
                "quality_predictor",
                serde_json::json!("ok"),
                features,
                0.9,
            );
        }

        // Record some corrections
        for i in 0..5 {
            let features = [("pressure".to_string(), 3.5 + i as f64 * 0.1)].into();
            service.record_correction(
                "quality_predictor",
                serde_json::json!("ok"),
                serde_json::json!("defect"),
                features,
                0.8,
            );
        }

        // Check health
        let health = service.get_model_health("quality_predictor");
        assert!(health.contains_key("accuracy"));

        // Force retrain
        let job = service.force_retrain("quality_predictor");
        assert!(job.is_some());

        // Complete the retraining
        service
            .retraining_manager
            .complete_retraining(job.unwrap().id, 0.94);
    }

    #[test]
    fn test_service_statistics() {
        let mut service = ContinuousLearningService::new();
        service.register_model("m1", LearningMode::Batch, 0.8);
        service.register_model("m2", LearningMode::Incremental, 0.9);

        let stats = service.get_statistics();
        assert!(stats.contains_key("models_registered"));
        assert_eq!(
            stats.get("models_registered").unwrap().as_u64().unwrap(),
            2
        );
    }
}

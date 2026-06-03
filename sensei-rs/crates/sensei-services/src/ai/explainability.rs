//! ML Model Explainability — Feature Importance and Model Interpretation.
//!
//! Provides interpretable machine learning explanations:
//! - Feature contribution analysis (SHAP-style)
//! - Global and local feature importance
//! - Natural language explanations
//! - Caching for performance optimization

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Types of model explanations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExplanationType {
    ShapLocal,
    ShapGlobal,
    LimeLocal,
    FeatureImportance,
    DecisionPath,
    Counterfactual,
}

impl ExplanationType {
    pub fn as_str(&self) -> &'static str {
        match self {
            ExplanationType::ShapLocal => "shap_local",
            ExplanationType::ShapGlobal => "shap_global",
            ExplanationType::LimeLocal => "lime_local",
            ExplanationType::FeatureImportance => "feature_importance",
            ExplanationType::DecisionPath => "decision_path",
            ExplanationType::Counterfactual => "counterfactual",
        }
    }
}

/// Supported model types for explainability.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelType {
    TreeEnsemble,
    Linear,
    DeepLearning,
    Generic,
}

impl ModelType {
    pub fn as_str(&self) -> &'static str {
        match self {
            ModelType::TreeEnsemble => "tree_ensemble",
            ModelType::Linear => "linear",
            ModelType::DeepLearning => "deep_learning",
            ModelType::Generic => "generic",
        }
    }
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// Single feature's contribution to a prediction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureContribution {
    pub feature_name: String,
    pub feature_value: f64,
    pub contribution: f64,
    pub contribution_abs: f64,
    pub direction: String, // "positive", "negative", "neutral"
    pub percentile_rank: Option<f64>,
}

impl FeatureContribution {
    pub fn new(feature_name: String, feature_value: f64, contribution: f64) -> Self {
        let direction = if contribution > 0.0 {
            "positive".to_string()
        } else if contribution < 0.0 {
            "negative".to_string()
        } else {
            "neutral".to_string()
        };
        Self {
            feature_name,
            feature_value,
            contribution,
            contribution_abs: contribution.abs(),
            direction,
            percentile_rank: None,
        }
    }

    pub fn to_map(&self) -> HashMap<String, serde_json::Value> {
        let mut map = HashMap::new();
        map.insert(
            "feature_name".into(),
            serde_json::json!(self.feature_name),
        );
        map.insert(
            "feature_value".into(),
            serde_json::json!(self.feature_value),
        );
        map.insert("contribution".into(), serde_json::json!(self.contribution));
        map.insert(
            "contribution_abs".into(),
            serde_json::json!(self.contribution_abs),
        );
        map.insert("direction".into(), serde_json::json!(self.direction));
        map.insert(
            "percentile_rank".into(),
            serde_json::json!(self.percentile_rank),
        );
        map
    }
}

/// Local explanation for a single prediction.
///
/// Contains feature contributions explaining why a specific prediction was made.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalExplanation {
    pub explanation_id: Uuid,
    pub model_name: String,
    pub explanation_type: ExplanationType,
    pub timestamp: DateTime<Utc>,

    // Prediction details
    pub input_features: HashMap<String, f64>,
    pub predicted_class: Option<i32>,
    pub predicted_probability: f64,
    pub base_value: f64,

    // Feature contributions (sorted by importance)
    pub feature_contributions: Vec<FeatureContribution>,

    // Summary
    pub top_positive_features: Vec<String>,
    pub top_negative_features: Vec<String>,
    pub natural_language_explanation: String,

    // Metadata
    pub computation_time_ms: f64,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl LocalExplanation {
    pub fn to_map(&self) -> HashMap<String, serde_json::Value> {
        let mut map = HashMap::new();
        map.insert(
            "explanation_id".into(),
            serde_json::json!(self.explanation_id.to_string()),
        );
        map.insert("model_name".into(), serde_json::json!(self.model_name));
        map.insert(
            "explanation_type".into(),
            serde_json::json!(self.explanation_type.as_str()),
        );
        map.insert(
            "timestamp".into(),
            serde_json::json!(self.timestamp.to_rfc3339()),
        );

        let input_map: HashMap<String, serde_json::Value> = self
            .input_features
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!(v)))
            .collect();
        map.insert("input_features".into(), serde_json::json!(input_map));
        map.insert(
            "predicted_class".into(),
            serde_json::json!(self.predicted_class),
        );
        map.insert(
            "predicted_probability".into(),
            serde_json::json!(self.predicted_probability),
        );
        map.insert("base_value".into(), serde_json::json!(self.base_value));

        let fcs: Vec<HashMap<String, serde_json::Value>> = self
            .feature_contributions
            .iter()
            .map(|fc| fc.to_map())
            .collect();
        map.insert("feature_contributions".into(), serde_json::json!(fcs));
        map.insert(
            "top_positive_features".into(),
            serde_json::json!(self.top_positive_features),
        );
        map.insert(
            "top_negative_features".into(),
            serde_json::json!(self.top_negative_features),
        );
        map.insert(
            "natural_language_explanation".into(),
            serde_json::json!(self.natural_language_explanation),
        );
        map.insert(
            "computation_time_ms".into(),
            serde_json::json!(self.computation_time_ms),
        );
        map
    }
}

/// Global explanation for model behavior.
///
/// Contains overall feature importance and feature interaction effects.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalExplanation {
    pub explanation_id: Uuid,
    pub model_name: String,
    pub explanation_type: ExplanationType,
    pub timestamp: DateTime<Utc>,

    // Global feature importance (sorted by importance)
    pub feature_importance: HashMap<String, f64>,
    pub feature_importance_std: HashMap<String, f64>,
    pub top_features: Vec<String>,

    // Summary
    pub natural_language_summary: String,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl GlobalExplanation {
    pub fn to_map(&self) -> HashMap<String, serde_json::Value> {
        let mut map = HashMap::new();
        map.insert(
            "explanation_id".into(),
            serde_json::json!(self.explanation_id.to_string()),
        );
        map.insert("model_name".into(), serde_json::json!(self.model_name));
        map.insert(
            "explanation_type".into(),
            serde_json::json!(self.explanation_type.as_str()),
        );
        map.insert(
            "timestamp".into(),
            serde_json::json!(self.timestamp.to_rfc3339()),
        );

        let fi: HashMap<String, serde_json::Value> = self
            .feature_importance
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!(v)))
            .collect();
        map.insert("feature_importance".into(), serde_json::json!(fi));

        let fis: HashMap<String, serde_json::Value> = self
            .feature_importance_std
            .iter()
            .map(|(k, v)| (k.clone(), serde_json::json!(v)))
            .collect();
        map.insert("feature_importance_std".into(), serde_json::json!(fis));

        map.insert("top_features".into(), serde_json::json!(self.top_features));
        map.insert(
            "natural_language_summary".into(),
            serde_json::json!(self.natural_language_summary),
        );
        map
    }
}

// ---------------------------------------------------------------------------
// Explainability Service
// ---------------------------------------------------------------------------

/// Service providing model explainability with SHAP/LIME-style explanations.
#[derive(Debug, Clone)]
pub struct ModelExplainabilityService {
    /// Cache of global explanations keyed by model_name
    global_cache: HashMap<String, GlobalExplanation>,
    /// Cache of local explanations keyed by model_name:entity_id
    local_cache: HashMap<String, LocalExplanation>,
    /// Maximum cache size
    max_cache_size: usize,
}

impl Default for ModelExplainabilityService {
    fn default() -> Self {
        Self::new(100)
    }
}

impl ModelExplainabilityService {
    pub fn new(max_cache_size: usize) -> Self {
        Self {
            global_cache: HashMap::new(),
            local_cache: HashMap::new(),
            max_cache_size,
        }
    }

    /// Generate a local explanation using SHAP-style feature attribution.
    ///
    /// `feature_values`: Current input feature values.
    /// `baseline_values`: Expected/background feature values (mean of training data).
    /// `feature_importance`: Precomputed feature importance weights (e.g. from a trained model).
    pub fn explain_local(
        &self,
        model_name: &str,
        explanation_type: ExplanationType,
        feature_values: &HashMap<String, f64>,
        baseline_values: &HashMap<String, f64>,
        feature_importance: &HashMap<String, f64>,
        predicted_class: Option<i32>,
        predicted_probability: f64,
        feature_names: &[String],
    ) -> LocalExplanation {
        let start = std::time::Instant::now();

        // Compute SHAP-style contributions: (feature_value - baseline) * importance
        let mut contributions: Vec<FeatureContribution> = feature_names
            .iter()
            .map(|name| {
                let value = feature_values.get(name).copied().unwrap_or(0.0);
                let baseline = baseline_values.get(name).copied().unwrap_or(0.0);
                let importance = feature_importance.get(name).copied().unwrap_or(0.0);
                let contribution = (value - baseline) * importance;
                FeatureContribution::new(name.clone(), value, contribution)
            })
            .collect();

        // Sort by absolute contribution (descending)
        contributions.sort_by(|a, b| {
            b.contribution_abs
                .partial_cmp(&a.contribution_abs)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Top features
        let top_positive: Vec<String> = contributions
            .iter()
            .filter(|c| c.direction == "positive")
            .take(5)
            .map(|c| c.feature_name.clone())
            .collect();
        let top_negative: Vec<String> = contributions
            .iter()
            .filter(|c| c.direction == "negative")
            .take(5)
            .map(|c| c.feature_name.clone())
            .collect();

        // Base value: expected prediction (mean of baseline * importance)
        let base_value: f64 = baseline_values
            .iter()
            .map(|(name, val)| {
                let imp = feature_importance.get(name).copied().unwrap_or(0.0);
                val * imp
            })
            .sum();

        // Natural language explanation
        let nl_explanation = self.generate_nl_explanation(
            predicted_probability,
            &top_positive,
            &top_negative,
            &contributions,
        );

        let elapsed = start.elapsed();

        LocalExplanation {
            explanation_id: Uuid::new_v4(),
            model_name: model_name.to_string(),
            explanation_type,
            timestamp: Utc::now(),
            input_features: feature_values.clone(),
            predicted_class,
            predicted_probability,
            base_value,
            feature_contributions: contributions,
            top_positive_features: top_positive,
            top_negative_features: top_negative,
            natural_language_explanation: nl_explanation,
            computation_time_ms: elapsed.as_secs_f64() * 1000.0,
            metadata: HashMap::new(),
        }
    }

    /// Generate global explanation (global feature importance).
    pub fn explain_global(
        &self,
        model_name: &str,
        feature_importance: &HashMap<String, f64>,
        feature_importance_std: &HashMap<String, f64>,
    ) -> GlobalExplanation {
        let mut sorted: Vec<(&String, &f64)> = feature_importance.iter().collect();
        sorted.sort_by(|a, b| {
            b.1.partial_cmp(a.1)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        let top_features: Vec<String> = sorted
            .iter()
            .take(10)
            .map(|(name, _)| (*name).clone())
            .collect();

        let summary = if top_features.is_empty() {
            "No feature importance data available.".to_string()
        } else {
            format!(
                "Top features influencing predictions: {}. {} is the most important feature.",
                top_features.join(", "),
                top_features[0]
            )
        };

        GlobalExplanation {
            explanation_id: Uuid::new_v4(),
            model_name: model_name.to_string(),
            explanation_type: ExplanationType::ShapGlobal,
            timestamp: Utc::now(),
            feature_importance: feature_importance.clone(),
            feature_importance_std: feature_importance_std.clone(),
            top_features,
            natural_language_summary: summary,
            metadata: HashMap::new(),
        }
    }

    /// Generate a natural language explanation for a prediction.
    fn generate_nl_explanation(
        &self,
        probability: f64,
        top_positive: &[String],
        top_negative: &[String],
        contributions: &[FeatureContribution],
    ) -> String {
        let confidence_level = if probability >= 0.9 {
            "very confident"
        } else if probability >= 0.7 {
            "confident"
        } else if probability >= 0.5 {
            "moderately confident"
        } else {
            "uncertain"
        };

        let mut parts = vec![format!(
            "The model is {} (probability: {:.1}%) about this prediction.",
            confidence_level,
            probability * 100.0
        )];

        if !top_positive.is_empty() {
            parts.push(format!(
                "Key factors increasing the prediction: {}.",
                top_positive.join(", ")
            ));
        }
        if !top_negative.is_empty() {
            parts.push(format!(
                "Key factors decreasing the prediction: {}.",
                top_negative.join(", ")
            ));
        }

        // Top 3 contributors
        let top3: Vec<String> = contributions
            .iter()
            .take(3)
            .map(|c| {
                format!(
                    "{} ({}{:.3})",
                    c.feature_name,
                    if c.contribution > 0.0 { "+" } else { "" },
                    c.contribution
                )
            })
            .collect();
        if !top3.is_empty() {
            parts.push(format!("Top contributors: {}.", top3.join(", ")));
        }

        parts.join(" ")
    }

    /// Compute feature importance using permutation-based approach.
    /// `baseline_score` is the model score on original data.
    /// `score_fn` takes a permuted feature column and returns the new score.
    pub fn compute_permutation_importance(
        &self,
        feature_names: &[String],
        baseline_score: f64,
        score_fn: impl Fn(&str) -> f64,
    ) -> HashMap<String, f64> {
        let mut importance = HashMap::new();
        for name in feature_names {
            let permuted_score = score_fn(name);
            let decrease = baseline_score - permuted_score;
            importance.insert(name.clone(), decrease.max(0.0));
        }
        importance
    }

    /// Compute feature importance from model coefficients (for linear models).
    pub fn compute_coefficient_importance(
        &self,
        feature_names: &[String],
        coefficients: &[f64],
    ) -> HashMap<String, f64> {
        let mut importance = HashMap::new();
        for (i, name) in feature_names.iter().enumerate() {
            if i < coefficients.len() {
                importance.insert(name.clone(), coefficients[i].abs());
            }
        }
        importance
    }

    /// Compute feature importance from tree-based feature importances.
    pub fn compute_tree_importance(
        &self,
        feature_names: &[String],
        importances: &[f64],
    ) -> HashMap<String, f64> {
        let mut importance = HashMap::new();
        for (i, name) in feature_names.iter().enumerate() {
            if i < importances.len() {
                importance.insert(name.clone(), importances[i]);
            }
        }
        importance
    }

    // -----------------------------------------------------------------------
    // Cache management
    // -----------------------------------------------------------------------

    /// Cache a local explanation.
    pub fn cache_local(&mut self, key: &str, explanation: LocalExplanation) {
        if self.local_cache.len() >= self.max_cache_size {
            // Evict oldest entry
            if let Some(oldest_key) = self.local_cache.keys().next().cloned() {
                self.local_cache.remove(&oldest_key);
            }
        }
        self.local_cache.insert(key.to_string(), explanation);
    }

    /// Retrieve a cached local explanation.
    pub fn get_cached_local(&self, key: &str) -> Option<&LocalExplanation> {
        self.local_cache.get(key)
    }

    /// Cache a global explanation.
    pub fn cache_global(&mut self, model_name: &str, explanation: GlobalExplanation) {
        self.global_cache
            .insert(model_name.to_string(), explanation);
    }

    /// Retrieve a cached global explanation.
    pub fn get_cached_global(&self, model_name: &str) -> Option<&GlobalExplanation> {
        self.global_cache.get(model_name)
    }

    /// Clear all caches.
    pub fn clear_cache(&mut self) {
        self.local_cache.clear();
        self.global_cache.clear();
    }

    /// Export state for persistence.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "global_explanations_count".into(),
            serde_json::json!(self.global_cache.len()),
        );
        state.insert(
            "local_explanations_count".into(),
            serde_json::json!(self.local_cache.len()),
        );
        state
    }
}

// =============================================================================
// Default feature names for CBM predictor
// =============================================================================

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

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn make_feature_map(names: &[&str], values: &[f64]) -> HashMap<String, f64> {
        names
            .iter()
            .zip(values.iter())
            .map(|(&n, &v)| (n.to_string(), v))
            .collect()
    }

    #[test]
    fn test_feature_contribution_new() {
        let fc = FeatureContribution::new("temp".into(), 75.0, 0.3);
        assert_eq!(fc.direction, "positive");
        assert!((fc.contribution_abs - 0.3).abs() < 1e-10);

        let fc2 = FeatureContribution::new("vib".into(), 5.0, -0.2);
        assert_eq!(fc2.direction, "negative");

        let fc3 = FeatureContribution::new("noise".into(), 0.0, 0.0);
        assert_eq!(fc3.direction, "neutral");
    }

    #[test]
    fn test_local_explanation() {
        let service = ModelExplainabilityService::default();
        let feature_names: Vec<String> =
            vec!["temp", "vibration", "pressure"]
                .iter()
                .map(|&s| s.to_string())
                .collect();

        let feature_values = make_feature_map(&["temp", "vibration", "pressure"], &[75.0, 5.0, 100.0]);
        let baseline_values = make_feature_map(&["temp", "vibration", "pressure"], &[70.0, 4.0, 90.0]);
        let importance = make_feature_map(&["temp", "vibration", "pressure"], &[0.5, 0.3, 0.2]);

        let explanation = service.explain_local(
            "cbm_model",
            ExplanationType::ShapLocal,
            &feature_values,
            &baseline_values,
            &importance,
            Some(1),
            0.85,
            &feature_names,
        );

        assert_eq!(explanation.model_name, "cbm_model");
        assert_eq!(explanation.feature_contributions.len(), 3);
        assert!(explanation.predicted_probability - 0.85 < 1e-10);
        assert!(!explanation.natural_language_explanation.is_empty());
    }

    #[test]
    fn test_global_explanation() {
        let service = ModelExplainabilityService::default();
        let mut importance = HashMap::new();
        importance.insert("temp".into(), 0.5);
        importance.insert("vibration".into(), 0.3);
        importance.insert("pressure".into(), 0.2);

        let mut std = HashMap::new();
        std.insert("temp".into(), 0.1);
        std.insert("vibration".into(), 0.05);
        std.insert("pressure".into(), 0.08);

        let global = service.explain_global("cbm_model", &importance, &std);
        assert_eq!(global.top_features[0], "temp");
        assert!(!global.natural_language_summary.is_empty());
    }

    #[test]
    fn test_permutation_importance() {
        let service = ModelExplainabilityService::default();
        let names: Vec<String> = vec!["feat_a".into(), "feat_b".into()];

        let importance = service.compute_permutation_importance(&names, 0.85, |name| {
            match name {
                "feat_a" => 0.75, // Permuting feat_a drops score to 0.75
                "feat_b" => 0.82,
                _ => 0.85,
            }
        });

        assert!((importance["feat_a"] - 0.10).abs() < 1e-10);
        assert!((importance["feat_b"] - 0.03).abs() < 1e-10);
    }

    #[test]
    fn test_cache_management() {
        let mut service = ModelExplainabilityService::new(3);
        let mut importance = HashMap::new();
        importance.insert("f1".into(), 1.0);

        for i in 0..5 {
            let explanation = LocalExplanation {
                explanation_id: Uuid::new_v4(),
                model_name: "model".into(),
                explanation_type: ExplanationType::ShapLocal,
                timestamp: Utc::now(),
                input_features: HashMap::new(),
                predicted_class: None,
                predicted_probability: 0.5,
                base_value: 0.0,
                feature_contributions: vec![],
                top_positive_features: vec![],
                top_negative_features: vec![],
                natural_language_explanation: "".into(),
                computation_time_ms: 0.0,
                metadata: HashMap::new(),
            };
            service.cache_local(&format!("key_{}", i), explanation);
        }

        assert_eq!(service.local_cache.len(), 3);
        assert!(service.get_cached_local("key_0").is_none());
        assert!(service.get_cached_local("key_4").is_some());
    }

    #[test]
    fn test_coefficient_importance() {
        let service = ModelExplainabilityService::default();
        let names: Vec<String> = vec!["a".into(), "b".into(), "c".into()];
        let coefs = vec![0.5, -0.3, 0.0];
        let importance = service.compute_coefficient_importance(&names, &coefs);
        assert!((importance["a"] - 0.5).abs() < 1e-10);
        assert!((importance["b"] - 0.3).abs() < 1e-10);
        assert!((importance["c"] - 0.0).abs() < 1e-10);
    }
}

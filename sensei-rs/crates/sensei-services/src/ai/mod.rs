//! AI/ML domain services.
//!
//! Provides anomaly detection, quality prediction, predictive maintenance,
//! and chatbot services with in-memory storage for development and testing.
//!
//! # Architecture
//!
//! The AI service layer abstracts ML inference behind a trait, enabling
//! the system to swap in real ML models (e.g., ONNX, TensorFlow, LLaMA)
//! while keeping the in-memory implementation for unit tests and demos.

pub mod analytics;
pub mod anomaly;
pub mod cbm_predictor;
pub mod database;
pub mod enhanced_ml_pipeline;
pub mod evaluation;
pub mod evidence_detector;
pub mod explainability;
pub mod knowledge;
pub mod learning;
pub mod lesson_recommender;
pub mod predictive_maintenance;
pub mod quality;
pub mod reasoning;
pub use database::DatabaseAiService;
pub mod chatbot;
pub mod chatbot_database;
pub use chatbot_database::DatabaseChatbotService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_core::domain::events::{
    AnomalyDetectedEvent, ModelRetrainedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_event_bus::bus::EventBus;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// A single anomaly prediction result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyPrediction {
    /// Type of entity being analysed (e.g. "ncr", "work_order", "equipment").
    pub entity_type: String,
    /// Unique identifier of the entity.
    pub entity_id: Uuid,
    /// Anomaly score between 0.0 (normal) and 1.0 (certain anomaly).
    pub anomaly_score: f64,
    /// Short label describing the predicted failure mode.
    pub predicted_failure: String,
    /// Model confidence in this prediction (0.0 – 1.0).
    pub confidence: f64,
    /// Human-readable recommended action.
    pub recommended_action: String,
    /// Timestamp when the anomaly was detected.
    pub detected_at: DateTime<Utc>,
}

/// Quality prediction for a production run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityPrediction {
    /// Identifier of the product being produced.
    pub product_id: Uuid,
    /// Predicted defect rate as a fraction (0.0 – 1.0).
    pub predicted_defect_rate: f64,
    /// Predicted process capability index (CpK).
    pub predicted_cpk: f64,
    /// Recommended process parameters as a JSON value.
    pub recommended_params: serde_json::Value,
}

/// Predictive maintenance recommendation for a piece of equipment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictiveMaintenanceResult {
    /// Identifier of the equipment.
    pub equipment_id: Uuid,
    /// Probability of failure within the forecast window (0.0 – 1.0).
    pub failure_probability: f64,
    /// Estimated remaining useful life in operating hours.
    pub estimated_remaining_life_hours: f64,
    /// Risk level: "low", "medium", "high", or "critical".
    pub risk_level: String,
    /// Recommended calendar date for the next maintenance.
    pub recommended_maintenance_date: DateTime<Utc>,
    /// List of suggested maintenance actions.
    pub suggested_actions: Vec<String>,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// AI/ML service providing anomaly detection, quality prediction, and
/// predictive maintenance.
#[async_trait]
pub trait AiService: Send + Sync {
    /// Detect anomalies in a given entity's data stream.
    async fn detect_anomalies(
        &self,
        tenant_id: Uuid,
        entity_type: &str,
        entity_id: Uuid,
    ) -> Result<Vec<AnomalyPrediction>>;

    /// Predict quality outcomes for a production run.
    async fn predict_quality(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
        batch_params: serde_json::Value,
    ) -> Result<QualityPrediction>;

    /// Get predictive maintenance recommendations for equipment.
    async fn predict_maintenance(
        &self,
        tenant_id: Uuid,
        equipment_id: Uuid,
    ) -> Result<PredictiveMaintenanceResult>;

    /// Trigger model retraining for a given model type.
    async fn retrain_model(&self, tenant_id: Uuid, model_type: &str) -> Result<()>;

    /// Publish an anomaly detected event to the event bus.
    async fn publish_anomaly_event(
        &self,
        tenant_id: Uuid,
        prediction: &AnomalyPrediction,
    ) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`AiService`] trait.
///
/// Stores predictions in memory and generates realistic synthetic results.
/// Suitable for development, testing, and demo environments.
pub struct InMemoryAiService {
    anomaly_predictions: RwLock<HashMap<Uuid, Vec<AnomalyPrediction>>>,
    quality_predictions: RwLock<HashMap<Uuid, QualityPrediction>>,
    maintenance_predictions: RwLock<HashMap<Uuid, PredictiveMaintenanceResult>>,
    /// Training outcomes per model type: (correct, total) pairs recorded by
    /// [`InMemoryAiService::submit_training_outcomes`].
    training_outcomes: RwLock<HashMap<String, (u64, u64)>>,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl InMemoryAiService {
    /// Create a new empty [`InMemoryAiService`] with an optional event bus.
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            anomaly_predictions: RwLock::new(HashMap::new()),
            quality_predictions: RwLock::new(HashMap::new()),
            maintenance_predictions: RwLock::new(HashMap::new()),
            training_outcomes: RwLock::new(HashMap::new()),
            event_bus,
        }
    }

    /// Record labelled training outcomes (correct predictions out of total
    /// samples) for a model type. `retrain_model` reports these as the
    /// accuracy and dataset size; without any recorded outcomes retraining
    /// fails honestly with an `insufficient_data` error instead of inventing
    /// metrics.
    pub async fn submit_training_outcomes(
        &self,
        model_type: &str,
        correct: u64,
        total: u64,
    ) {
        let mut outcomes = self.training_outcomes.write().await;
        let entry = outcomes.entry(model_type.to_string()).or_insert((0, 0));
        entry.0 += correct;
        entry.1 += total;
    }
}

impl Default for InMemoryAiService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl AiService for InMemoryAiService {
    async fn detect_anomalies(
        &self,
        _tenant_id: Uuid,
        entity_type: &str,
        entity_id: Uuid,
    ) -> Result<Vec<AnomalyPrediction>> {
        // Try to return cached predictions first
        {
            let cache = self.anomaly_predictions.read().await;
            if let Some(predictions) = cache.get(&entity_id) {
                return Ok(predictions.clone());
            }
        }

        // Generate realistic synthetic predictions
        let now = Utc::now();
        let predictions: Vec<AnomalyPrediction> = match entity_type {
            "ncr" => vec![
                AnomalyPrediction {
                    entity_type: entity_type.to_string(),
                    entity_id,
                    anomaly_score: 0.72,
                    predicted_failure: "quality_defect".to_string(),
                    confidence: 0.85,
                    recommended_action: "Review recent inspection results and escalate if pattern persists.".to_string(),
                    detected_at: now,
                },
                AnomalyPrediction {
                    entity_type: entity_type.to_string(),
                    entity_id,
                    anomaly_score: 0.34,
                    predicted_failure: "documentation_gap".to_string(),
                    confidence: 0.62,
                    recommended_action: "Verify that all required fields and attachments are present.".to_string(),
                    detected_at: now,
                },
            ],
            "work_order" => vec![
                AnomalyPrediction {
                    entity_type: entity_type.to_string(),
                    entity_id,
                    anomaly_score: 0.58,
                    predicted_failure: "schedule_delay".to_string(),
                    confidence: 0.78,
                    recommended_action: "Re-allocate resources to meet deadline. Consider overtime approval.".to_string(),
                    detected_at: now,
                },
            ],
            "equipment" => vec![
                AnomalyPrediction {
                    entity_type: entity_type.to_string(),
                    entity_id,
                    anomaly_score: 0.81,
                    predicted_failure: "equipment_breakdown".to_string(),
                    confidence: 0.91,
                    recommended_action: "Schedule immediate inspection. Vibration pattern indicates bearing wear.".to_string(),
                    detected_at: now,
                },
                AnomalyPrediction {
                    entity_type: entity_type.to_string(),
                    entity_id,
                    anomaly_score: 0.45,
                    predicted_failure: "temperature_deviation".to_string(),
                    confidence: 0.69,
                    recommended_action: "Check cooling system and lubricant levels.".to_string(),
                    detected_at: now,
                },
            ],
            _ => vec![AnomalyPrediction {
                entity_type: entity_type.to_string(),
                entity_id,
                anomaly_score: 0.65,
                predicted_failure: "unspecified_anomaly".to_string(),
                confidence: 0.78,
                recommended_action: "Review entity data for unusual patterns.".to_string(),
                detected_at: now,
            }],
        };

        // Cache the predictions
        self.anomaly_predictions
            .write()
            .await
            .insert(entity_id, predictions.clone());

        Ok(predictions)
    }

    async fn predict_quality(
        &self,
        _tenant_id: Uuid,
        product_id: Uuid,
        _batch_params: serde_json::Value,
    ) -> Result<QualityPrediction> {
        // Try cached prediction first
        {
            let cache = self.quality_predictions.read().await;
            if let Some(pred) = cache.get(&product_id) {
                return Ok(pred.clone());
            }
        }

        // Generate realistic synthetic quality prediction
        let prediction = QualityPrediction {
            product_id,
            predicted_defect_rate: 0.023,
            predicted_cpk: 1.42,
            recommended_params: serde_json::json!({
                "temperature_c": {
                    "current": 185,
                    "recommended": 180,
                    "range": [175, 190]
                },
                "pressure_bar": {
                    "current": 4.2,
                    "recommended": 3.8,
                    "range": [3.5, 4.5]
                },
                "cycle_time_s": {
                    "current": 45,
                    "recommended": 42,
                    "range": [38, 48]
                },
                "material_moisture_pct": {
                    "current": 1.8,
                    "recommended": 1.2,
                    "max_allowed": 2.0
                }
            }),
        };

        self.quality_predictions
            .write()
            .await
            .insert(product_id, prediction.clone());

        Ok(prediction)
    }

    async fn predict_maintenance(
        &self,
        _tenant_id: Uuid,
        equipment_id: Uuid,
    ) -> Result<PredictiveMaintenanceResult> {
        // Try cached prediction first
        {
            let cache = self.maintenance_predictions.read().await;
            if let Some(pred) = cache.get(&equipment_id) {
                return Ok(pred.clone());
            }
        }

        let now = Utc::now();
        let prediction = PredictiveMaintenanceResult {
            equipment_id,
            failure_probability: 0.27,
            estimated_remaining_life_hours: 1250.0,
            risk_level: "medium".to_string(),
            recommended_maintenance_date: now + chrono::Duration::days(45),
            suggested_actions: vec![
                "Replace oil and hydraulic filters".to_string(),
                "Inspect and tighten belt tension".to_string(),
                "Calibrate temperature sensors".to_string(),
                "Lubricate all moving joints".to_string(),
                "Run diagnostic self-test".to_string(),
            ],
        };

        self.maintenance_predictions
            .write()
            .await
            .insert(equipment_id, prediction.clone());

        Ok(prediction)
    }

    async fn retrain_model(&self, tenant_id: Uuid, model_type: &str) -> Result<()> {
        // Honest retraining: report the accuracy and dataset size recorded via
        // `submit_training_outcomes`. When no labelled data has been supplied
        // for this model type, retraining fails with an explicit
        // `insufficient_data` error instead of fabricating metrics.
        let (correct, total) = {
            let outcomes = self.training_outcomes.read().await;
            outcomes.get(model_type).copied().unwrap_or((0, 0))
        };

        if total == 0 {
            return Err(SenseiError::Internal(format!(
                "insufficient_data: no training outcomes recorded for model type '{model_type}'. \
                 Call submit_training_outcomes with labelled data before retraining."
            )));
        }

        let accuracy = correct as f64 / total as f64;
        let dataset_size = total as i64;

        let event = ModelRetrainedEvent::new(
            tenant_id,
            model_type.to_string(),
            format!("v{}", chrono::Utc::now().format("%Y%m%d.%H%M")),
            accuracy,
            dataset_size,
        );

        // Publish event if bus is available; log errors instead of silently swallowing them
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!(
                    error = %e,
                    model_type = %model_type,
                    "Failed to publish ModelRetrainedEvent"
                );
            }
        }

        Ok(())
    }

    async fn publish_anomaly_event(
        &self,
        tenant_id: Uuid,
        prediction: &AnomalyPrediction,
    ) -> Result<()> {
        let event = AnomalyDetectedEvent::new(
            tenant_id,
            prediction.entity_type.clone(),
            prediction.entity_id,
            prediction.predicted_failure.clone(),
            prediction.confidence,
            format!(
                "Anomaly detected: {} (score: {:.2}) — {}",
                prediction.predicted_failure,
                prediction.anomaly_score,
                prediction.recommended_action,
            ),
        );

        if let Some(ref bus) = self.event_bus {
            bus.publish(&event).await?;
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_detect_anomalies_ncr() {
        let service = InMemoryAiService::default();
        let tenant_id = Uuid::new_v4();
        let entity_id = Uuid::new_v4();

        let results = service
            .detect_anomalies(tenant_id, "ncr", entity_id)
            .await
            .expect("should detect anomalies");

        assert!(!results.is_empty(), "should return at least one prediction");
        assert_eq!(results[0].entity_id, entity_id);
        assert_eq!(results[0].entity_type, "ncr");
    }

    #[tokio::test]
    async fn test_predict_quality() {
        let service = InMemoryAiService::default();
        let tenant_id = Uuid::new_v4();
        let product_id = Uuid::new_v4();

        let result = service
            .predict_quality(tenant_id, product_id, serde_json::json!({}))
            .await
            .expect("should predict quality");

        assert_eq!(result.product_id, product_id);
        assert!(result.predicted_cpk > 0.0);
    }

    #[tokio::test]
    async fn test_predict_maintenance() {
        let service = InMemoryAiService::default();
        let tenant_id = Uuid::new_v4();
        let equipment_id = Uuid::new_v4();

        let result = service
            .predict_maintenance(tenant_id, equipment_id)
            .await
            .expect("should predict maintenance");

        assert_eq!(result.equipment_id, equipment_id);
        assert!(!result.suggested_actions.is_empty());
    }

    #[tokio::test]
    async fn test_retrain_model() {
        let service = InMemoryAiService::default();
        let tenant_id = Uuid::new_v4();

        // Without recorded training outcomes retraining must fail honestly.
        let err = service
            .retrain_model(tenant_id, "anomaly_detection")
            .await
            .expect_err("retrain without data must fail");
        assert!(
            err.to_string().contains("insufficient_data"),
            "unexpected error: {err}"
        );

        // With labelled outcomes the reported accuracy is real.
        service
            .submit_training_outcomes("anomaly_detection", 900, 1000)
            .await;
        service
            .retrain_model(tenant_id, "anomaly_detection")
            .await
            .expect("retrain with data should succeed");
    }

    #[tokio::test]
    async fn test_publish_anomaly_event_without_bus() {
        let service = InMemoryAiService::default();
        let tenant_id = Uuid::new_v4();

        let prediction = AnomalyPrediction {
            entity_type: "ncr".to_string(),
            entity_id: Uuid::new_v4(),
            anomaly_score: 0.85,
            predicted_failure: "quality_defect".to_string(),
            confidence: 0.92,
            recommended_action: "Inspect immediately.".to_string(),
            detected_at: Utc::now(),
        };

        // Should succeed even without an event bus
        service
            .publish_anomaly_event(tenant_id, &prediction)
            .await
            .expect("publish should succeed without bus");
    }
}

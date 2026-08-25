//! PostgreSQL-backed AI/ML service using sqlx.
//!
//! Provides anomaly detection, quality prediction, predictive maintenance,
//! and model registry operations backed by the `anomaly_detections`,
//! `model_registry`, and `predictions` database tables.
//!
//! # Production use
//!
//! This implementation reads existing anomaly records and predictions from
//! the database (populated by background ML workers) and writes new
//! anomaly events to the database.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::domain::events::AnomalyDetectedEvent;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{new_correlation_id, EventId};
use sensei_db::models::{AnomalyDetectionModel, PredictionModel};
use sensei_event_bus::bus::EventBus;
use sqlx::PgPool;
use std::sync::Arc;
use uuid::Uuid;

use crate::ai::{AiService, AnomalyPrediction, PredictiveMaintenanceResult, QualityPrediction};

/// PostgreSQL-backed implementation of [`AiService`].
pub struct DatabaseAiService {
    pool: PgPool,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl DatabaseAiService {
    /// Create a new [`DatabaseAiService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self {
            pool,
            event_bus: None,
        }
    }

    /// Create a new [`DatabaseAiService`] with an event bus for publishing events.
    pub fn with_event_bus(pool: PgPool, event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self { pool, event_bus }
    }
}

// ── Conversion helpers ─────────────────────────────────────────────────────

fn anomaly_model_to_prediction(m: AnomalyDetectionModel) -> AnomalyPrediction {
    AnomalyPrediction {
        entity_type: m.entity_type,
        entity_id: m.entity_id,
        anomaly_score: m.confidence,
        predicted_failure: m.anomaly_type,
        confidence: m.confidence,
        recommended_action: m.description,
        detected_at: m.detected_at,
    }
}

fn prediction_to_quality(p: PredictionModel) -> QualityPrediction {
    // The predictions table stores predicted_value as a string. For quality
    // predictions, we attempt to parse the defect rate from stored features.
    let predicted_defect_rate = p
        .input_features
        .as_ref()
        .and_then(|v| v.get("predicted_defect_rate"))
        .and_then(|v| v.as_f64())
        .unwrap_or(p.confidence);

    let predicted_cpk = p
        .input_features
        .as_ref()
        .and_then(|v| v.get("predicted_cpk"))
        .and_then(|v| v.as_f64())
        .unwrap_or(1.0);

    let recommended_params = p
        .input_features
        .clone()
        .unwrap_or(serde_json::Value::Object(serde_json::Map::new()));

    QualityPrediction {
        product_id: p.entity_id,
        predicted_defect_rate,
        predicted_cpk,
        recommended_params,
    }
}

fn prediction_to_maintenance(p: PredictionModel) -> PredictiveMaintenanceResult {
    let failure_probability = p.confidence;

    let estimated_remaining_life_hours = p
        .input_features
        .as_ref()
        .and_then(|v| v.get("remaining_life_hours"))
        .and_then(|v| v.as_f64())
        .unwrap_or(8760.0); // default: 1 year

    let risk_level = p
        .input_features
        .as_ref()
        .and_then(|v| v.get("risk_level"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| {
            if failure_probability > 0.7 {
                "high".to_string()
            } else if failure_probability > 0.4 {
                "medium".to_string()
            } else {
                "low".to_string()
            }
        });

    let recommended_maintenance_date = p.predicted_at
        + chrono::Duration::try_hours(estimated_remaining_life_hours as i64)
            .unwrap_or(chrono::Duration::try_hours(8760).unwrap());

    let suggested_actions: Vec<String> = p
        .input_features
        .as_ref()
        .and_then(|v| v.get("suggested_actions"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_else(|| {
            vec![
                "Inspect equipment".to_string(),
                "Schedule maintenance".to_string(),
            ]
        });

    PredictiveMaintenanceResult {
        equipment_id: p.entity_id,
        failure_probability,
        estimated_remaining_life_hours,
        risk_level,
        recommended_maintenance_date,
        suggested_actions,
    }
}

#[async_trait]
impl AiService for DatabaseAiService {
    async fn detect_anomalies(
        &self,
        tenant_id: Uuid,
        entity_type: &str,
        entity_id: Uuid,
    ) -> Result<Vec<AnomalyPrediction>> {
        let models = sqlx::query_as::<_, AnomalyDetectionModel>(
            r#"
            SELECT id, tenant_id, entity_type, entity_id, anomaly_type,
                   confidence, description, status, features,
                   reviewed_by, reviewed_at, detected_at, created_at
            FROM anomaly_detections
            WHERE tenant_id = $1 AND entity_type = $2 AND entity_id = $3
            ORDER BY detected_at DESC
            "#,
        )
        .bind(tenant_id)
        .bind(entity_type)
        .bind(entity_id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to query anomaly detections: {e}")))?;

        Ok(models
            .into_iter()
            .map(anomaly_model_to_prediction)
            .collect())
    }

    async fn predict_quality(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
        _batch_params: serde_json::Value,
    ) -> Result<QualityPrediction> {
        let model = sqlx::query_as::<_, PredictionModel>(
            r#"
            SELECT id, tenant_id, model_id, prediction_type, entity_type,
                   entity_id, predicted_value, actual_value, confidence,
                   input_features, is_accurate, predicted_at, created_at
            FROM predictions
            WHERE tenant_id = $1 AND entity_id = $2 AND prediction_type = 'quality'
            ORDER BY predicted_at DESC
            LIMIT 1
            "#,
        )
        .bind(tenant_id)
        .bind(product_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to query quality prediction: {e}")))?;

        match model {
            Some(m) => Ok(prediction_to_quality(m)),
            None => Err(SenseiError::NotFound(format!(
                "No quality prediction found for product {product_id}"
            ))),
        }
    }

    async fn predict_maintenance(
        &self,
        tenant_id: Uuid,
        equipment_id: Uuid,
    ) -> Result<PredictiveMaintenanceResult> {
        let model = sqlx::query_as::<_, PredictionModel>(
            r#"
            SELECT id, tenant_id, model_id, prediction_type, entity_type,
                   entity_id, predicted_value, actual_value, confidence,
                   input_features, is_accurate, predicted_at, created_at
            FROM predictions
            WHERE tenant_id = $1 AND entity_id = $2 AND prediction_type = 'maintenance'
            ORDER BY predicted_at DESC
            LIMIT 1
            "#,
        )
        .bind(tenant_id)
        .bind(equipment_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("Failed to query maintenance prediction: {e}"))
        })?;

        match model {
            Some(m) => Ok(prediction_to_maintenance(m)),
            None => Err(SenseiError::NotFound(format!(
                "No maintenance prediction found for equipment {equipment_id}"
            ))),
        }
    }

    async fn retrain_model(&self, tenant_id: Uuid, model_type: &str) -> Result<()> {
        let now = Utc::now();
        let model_id = Uuid::new_v4();

        sqlx::query(
            r#"
            INSERT INTO model_registry
                (id, tenant_id, model_name, version, model_type, status,
                 accuracy, precision, recall, f1_score, dataset_size,
                 artifact_path, config, created_by, deployed_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17)
            "#,
        )
        .bind(model_id)
        .bind(tenant_id)
        .bind(format!("{}_model", model_type))
        .bind("1.0.0")
        .bind(model_type)
        .bind("development")
        .bind(0.0_f64) // accuracy
        .bind(None::<f64>) // precision
        .bind(None::<f64>) // recall
        .bind(None::<f64>) // f1_score
        .bind(None::<i64>) // dataset_size
        .bind(None::<String>) // artifact_path
        .bind(serde_json::Value::Null) // config
        .bind(None::<Uuid>) // created_by
        .bind(None::<chrono::DateTime<chrono::Utc>>) // deployed_at
        .bind(now)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to register model: {e}")))?;

        Ok(())
    }

    async fn publish_anomaly_event(
        &self,
        tenant_id: Uuid,
        prediction: &AnomalyPrediction,
    ) -> Result<()> {
        let now = Utc::now();
        let id = Uuid::new_v4();

        sqlx::query(
            r#"
            INSERT INTO anomaly_detections
                (id, tenant_id, entity_type, entity_id, anomaly_type,
                 confidence, description, status, features,
                 reviewed_by, reviewed_at, detected_at, created_at)
            VALUES ($1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12, $13)
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&prediction.entity_type)
        .bind(prediction.entity_id)
        .bind(&prediction.predicted_failure)
        .bind(prediction.confidence)
        .bind(&prediction.recommended_action)
        .bind("new")
        .bind(serde_json::Value::Null) // features
        .bind(None::<Uuid>) // reviewed_by
        .bind(None::<chrono::DateTime<chrono::Utc>>) // reviewed_at
        .bind(prediction.detected_at)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to insert anomaly detection: {e}")))?;

        // Publish to event bus if one is configured.
        if let Some(ref bus) = self.event_bus {
            let event = AnomalyDetectedEvent {
                metadata: sensei_core::domain::events::EventMetadata {
                    event_id: EventId::new_v4(),
                    event_type: "anomaly.detected".to_string(),
                    correlation_id: new_correlation_id(),
                    tenant_id,
                    occurred_at: Utc::now(),
                    version: 1,
                },
                entity_type: prediction.entity_type.clone(),
                entity_id: prediction.entity_id,
                anomaly_type: prediction.predicted_failure.clone(),
                confidence: prediction.confidence,
                description: prediction.recommended_action.clone(),
            };
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!(error = %e, "Failed to publish anomaly detected event");
            }
        }

        Ok(())
    }
}

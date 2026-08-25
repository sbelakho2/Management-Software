//! AI/ML API endpoints.
//!
//! Anomaly detection, quality predictions, maintenance predictions, model retraining.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyPredictionDto {
    pub id: String,
    pub tenant_id: String,
    pub entity_type: String,
    pub entity_id: String,
    pub anomaly_score: f64,
    pub is_anomaly: bool,
    pub features: serde_json::Value,
    pub detected_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityPredictionDto {
    pub id: String,
    pub tenant_id: String,
    pub product_id: String,
    pub predicted_defect_rate: f64,
    pub confidence: f64,
    pub recommended_action: Option<String>,
    pub predicted_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenancePredictionDto {
    pub id: String,
    pub tenant_id: String,
    pub asset_id: String,
    pub days_until_failure: i32,
    pub confidence: f64,
    pub recommended_action: Option<String>,
    pub predicted_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfoDto {
    pub model_type: String,
    pub accuracy: f64,
    pub dataset_size: i64,
    pub last_trained: Option<String>,
}

pub struct AiApi;

impl AiApi {
    /// Detect anomalies for a given entity type and ID.
    pub async fn detect_anomalies(
        client: &ApiClient,
        entity_type: &str,
        entity_id: &str,
    ) -> Result<Vec<AnomalyPredictionDto>, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> {
            entity_type: &'a str,
            entity_id: &'a str,
        }
        client
            .post(
                "/api/v1/ai/anomalies/detect",
                &Body {
                    entity_type,
                    entity_id,
                },
            )
            .await
    }

    /// Get quality predictions for a product.
    pub async fn predict_quality(
        client: &ApiClient,
        product_id: &str,
    ) -> Result<QualityPredictionDto, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> {
            product_id: &'a str,
        }
        client
            .post("/api/v1/ai/quality/predict", &Body { product_id })
            .await
    }

    /// Get maintenance predictions for an asset.
    pub async fn predict_maintenance(
        client: &ApiClient,
        asset_id: &str,
    ) -> Result<MaintenancePredictionDto, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> {
            asset_id: &'a str,
        }
        client
            .post("/api/v1/ai/maintenance/predict", &Body { asset_id })
            .await
    }

    /// Retrain an AI model.
    pub async fn retrain_model(
        client: &ApiClient,
        model_type: &str,
    ) -> Result<ModelInfoDto, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> {
            model_type: &'a str,
        }
        client
            .post("/api/v1/ai/models/retrain", &Body { model_type })
            .await
    }
}

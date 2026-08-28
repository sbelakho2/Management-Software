//! AI/ML route handlers.
//!
//! Provides endpoints for anomaly detection, quality prediction,
//! predictive maintenance, and model retraining.

use axum::{extract::State, http::StatusCode, response::IntoResponse, Json};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

/// Request body for anomaly detection.
#[derive(Debug, Deserialize)]
pub struct DetectAnomaliesRequest {
    /// The entity type to analyze (e.g., "ncr", "inspection", "audit").
    pub entity_type: String,
    /// Entity ID to scope the analysis.
    pub entity_id: Uuid,
}

/// Request body for quality prediction.
#[derive(Debug, Deserialize)]
pub struct PredictQualityRequest {
    /// Product identifier.
    pub product_id: Uuid,
    /// Batch parameters as JSON value.
    pub batch_params: serde_json::Value,
}

/// Request body for predictive maintenance.
#[derive(Debug, Deserialize)]
pub struct PredictMaintenanceRequest {
    /// Equipment identifier.
    pub equipment_id: Uuid,
}

/// Request body for model retraining.
#[derive(Debug, Deserialize)]
pub struct RetrainModelRequest {
    /// Model type to retrain (e.g., "anomaly", "quality", "maintenance").
    pub model_type: String,
}

/// Detect anomalies in the specified domain.
pub async fn detect_anomalies(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<DetectAnomaliesRequest>,
) -> Result<Json<Vec<sensei_services::ai::AnomalyPrediction>>> {
    user.require_permission("ai:inference")?;
    let tenant_id = user.tenant_id;
    let predictions = state
        .ai_service
        .detect_anomalies(tenant_id, &req.entity_type, req.entity_id)
        .await?;
    Ok(Json(predictions))
}

/// Predict quality metrics for a product or batch.
pub async fn predict_quality(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PredictQualityRequest>,
) -> Result<Json<sensei_services::ai::QualityPrediction>> {
    user.require_permission("ai:inference")?;
    let tenant_id = user.tenant_id;
    let prediction = state
        .ai_service
        .predict_quality(tenant_id, req.product_id, req.batch_params)
        .await?;
    Ok(Json(prediction))
}

/// Predict maintenance needs for equipment.
pub async fn predict_maintenance(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PredictMaintenanceRequest>,
) -> Result<Json<sensei_services::ai::PredictiveMaintenanceResult>> {
    user.require_permission("ai:inference")?;
    let tenant_id = user.tenant_id;
    let result = state
        .ai_service
        .predict_maintenance(tenant_id, req.equipment_id)
        .await?;
    Ok(Json(result))
}

/// Retrain an AI/ML model.
pub async fn retrain_model(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RetrainModelRequest>,
) -> Result<axum::response::Response> {
    user.require_permission("ai:retrain")?;
    let tenant_id = user.tenant_id;
    // Queue the training job: the model enters 'training' and is NEVER
    // deployed by this call (approval gates promotion). The response is
    // 202 Accepted with the job id — not a fabricated success.
    let training_job_id = state
        .ai_service
        .queue_model_training(tenant_id, &req.model_type)
        .await?;
    let body = Json(serde_json::json!({
        "training_job_id": training_job_id,
        "status": "training",
        "model_type": req.model_type,
        "message": "Training job queued. The model is NOT deployed until it is validated and approved."
    }));
    Ok((StatusCode::ACCEPTED, body).into_response())
}

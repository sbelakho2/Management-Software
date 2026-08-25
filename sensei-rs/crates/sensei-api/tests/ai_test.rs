//! End-to-end tests for AI/ML route handlers.
//!
//! Covers:
//! - POST /api/v1/ai/anomalies/detect
//! - POST /api/v1/ai/quality/predict
//! - POST /api/v1/ai/maintenance/predict
//! - POST /api/v1/ai/models/retrain

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Anomaly Detection ─────────────────────────────────────────────────────────

#[tokio::test]
async fn test_detect_anomalies() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "entity_type": "ncr",
        "entity_id": uuid::Uuid::new_v4().to_string(),
    });

    let req = app.post_authenticated("/api/v1/ai/anomalies/detect", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    // Response is a Vec<AnomalyPrediction>; assert it's an array
    assert!(json.is_array(), "Expected array of anomaly predictions");
}

#[tokio::test]
async fn test_detect_anomalies_unauthenticated() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({
        "entity_type": "ncr",
        "entity_id": uuid::Uuid::new_v4().to_string(),
    });

    let req = app.post("/api/v1/ai/anomalies/detect", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

// ── Quality Prediction ────────────────────────────────────────────────────────

#[tokio::test]
async fn test_predict_quality() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "product_id": uuid::Uuid::new_v4().to_string(),
        "batch_params": {"temperature": 150.0, "pressure": 2.5},
    });

    let req = app.post_authenticated("/api/v1/ai/quality/predict", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    // Response is a QualityPrediction object
    assert!(json.is_object(), "Expected quality prediction object");
}

// ── Predictive Maintenance ────────────────────────────────────────────────────

#[tokio::test]
async fn test_predict_maintenance() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "equipment_id": uuid::Uuid::new_v4().to_string(),
    });

    let req = app.post_authenticated("/api/v1/ai/maintenance/predict", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    // Response is a PredictiveMaintenanceResult
    assert!(json.is_object(), "Expected maintenance prediction object");
}

// ── Model Retraining ──────────────────────────────────────────────────────────

#[tokio::test]
async fn test_retrain_model() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let body = serde_json::json!({
        "model_type": "anomaly",
    });

    // UPDATED BEHAVIOR: retraining honestly fails with insufficient_data
    // when no labelled training outcomes were recorded for the model type.
    // The previous behavior fabricated a success response.
    let req = app.post_authenticated("/api/v1/ai/models/retrain", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::INTERNAL_SERVER_ERROR);
    let text = app.response_text(&mut resp).await;
    assert!(
        text.contains("insufficient_data"),
        "retraining without labelled data must report insufficient_data, got: {text}"
    );
}

#[tokio::test]
async fn test_retrain_model_unauthenticated() {
    let app = common::TestApp::new().await;

    let body = serde_json::json!({ "model_type": "quality" });
    let req = app.post("/api/v1/ai/models/retrain", body);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}

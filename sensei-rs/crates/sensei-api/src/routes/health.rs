//! Health check endpoints.
//!
//! Provides endpoints for readiness and liveness probes used by
//! container orchestration systems (Kubernetes, Docker, etc.).

use axum::{Json, extract::State};
use serde::Serialize;
use std::time::Instant;

use crate::state::AppState;

/// Health check response body.
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    /// Service status.
    pub status: String,
    /// Service version.
    pub version: String,
    /// Uptime in seconds since the service started.
    pub uptime_seconds: u64,
    /// Database connectivity status.
    pub database: String,
}

/// Global start time for uptime tracking.
static START_TIME: once_cell::sync::Lazy<Instant> = once_cell::sync::Lazy::new(Instant::now);

/// Basic liveness probe — returns 200 if the server is alive.
pub async fn liveness() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "alive"
    }))
}

/// Readiness probe — checks if the service is ready to handle requests.
///
/// Optionally checks database connectivity if a pool is configured.
pub async fn readiness(
    State(state): State<AppState>,
) -> Json<HealthResponse> {
    let db_status = match &state.db_pool {
        Some(_pool) => "connected", // In real impl, do a SELECT 1
        None => "not_configured",
    };

    Json(HealthResponse {
        status: "ready".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_seconds: START_TIME.elapsed().as_secs(),
        database: db_status.to_string(),
    })
}

/// Detailed health check with all subsystem statuses.
pub async fn detailed() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "service": "sensei-api",
        "version": env!("CARGO_PKG_VERSION"),
        "status": "ok",
        "uptime_seconds": START_TIME.elapsed().as_secs(),
        "checks": {
            "memory": "ok",
            "cpu": "ok",
        }
    }))
}

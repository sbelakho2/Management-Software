//! Deterministic TPS kernel routes: takt, pitch, available-time.

use axum::extract::State;
use axum::Json;
use rust_decimal::Decimal;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::SenseiError;
use sensei_services::tps::{AvailableProductionTime, TaktSnapshot};

use crate::state::AppState;

/// Request: the demand window and the operating calendar inputs.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct CalculateTaktRequest {
    pub demand_window_id: uuid::Uuid,
    pub scheduled_seconds: u64,
    pub breaks_seconds: u64,
    pub planned_downtime_seconds: u64,
    pub demand_units: Decimal,
}

/// Deterministic takt calculation: `takt = net available time / demand`.
/// The result carries the inputs as evidence refs — the caller (human or
/// agent) receives the number; nobody invents it.
pub async fn calculate_takt(
    user: AuthenticatedUser,
    State(_state): State<AppState>,
    Json(req): Json<CalculateTaktRequest>,
) -> Result<Json<TaktSnapshot>, SenseiError> {
    user.require_permission("tps:standard-work:read")?;
    let available = AvailableProductionTime {
        scheduled_seconds: req.scheduled_seconds,
        breaks_seconds: req.breaks_seconds,
        planned_downtime_seconds: req.planned_downtime_seconds,
    };
    sensei_services::tps::calculate_takt(req.demand_window_id, &available, req.demand_units)
        .map(Json)
        .ok_or_else(|| {
            SenseiError::Validation(
                "Demand must be positive for a takt to exist (zero demand has no takt)".to_string(),
            )
        })
}

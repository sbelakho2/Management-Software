//! Today screen API — item 30: the frontend consumes the REAL backend
//! `/api/v1/today` snapshot (site-timezone date, server-scoped), not the
//! stale per-user sub-endpoints that never existed.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// DTOs — mirror the backend TodaySnapshot contract exactly.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TodaySnapshot {
    /// The SITE-local date (backend resolves the timezone).
    pub date: String,
    /// The timezone used for the date (site timezone, item 65).
    pub timezone: String,
    /// The caller's active operational scope.
    pub scope: TodayScope,
    pub work_orders: WorkOrderSummary,
    pub quality: QualitySummary,
    pub operations: OperationsSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TodayScope {
    pub site_id: Option<String>,
    pub value_stream_id: Option<String>,
    pub work_center_id: Option<String>,
    pub shift_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderSummary {
    pub total_active: usize,
    pub completed_today: usize,
    pub in_progress: usize,
    pub overdue: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualitySummary {
    pub active_andons: usize,
    pub open_ncrs: usize,
    pub open_capas: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationsSummary {
    pub open_risks: usize,
    pub open_a3s: usize,
    pub active_projects: usize,
}

/// Fetch the server-generated Today snapshot (item 30).
pub async fn get_today_snapshot(client: &ApiClient) -> Result<TodaySnapshot, ApiError> {
    client.get("/api/v1/today").await
}

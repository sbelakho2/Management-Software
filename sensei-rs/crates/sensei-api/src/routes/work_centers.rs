//! Work Center route handlers.
//!
//! Provides endpoints for managing manufacturing work centers (production
//! cells / manufacturing units), including capacity, efficiency tracking,
//! and active/inactive status management.
//!
//! Twentieth audit P0 (Work Center split-brain): these handlers used to
//! persist through a generic EntityStore (JSONB in `entity_store`) while
//! RequestContext topology validation, site readiness, capability checks
//! and skills read the RELATIONAL `work_centers` table — two systems of
//! record that could diverge. All create/update/get/list operations now
//! go through the relational [`WorkCenterRepository`] so a work center
//! created through this API IMMEDIATELY exists for the plant lifecycle.
//! Responses carry `site_id` and `topology_state`; a create may assert a
//! `site_id` (the composite FK verifies the site belongs to the tenant)
//! or leave it `None` — a site-less work center is created as
//! `needs_reconciliation`, never certified.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_services::tps::work_center_repository::{
    self, NewWorkCenter, RelationalWorkCenter, UpdateWorkCenter,
};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing work centers.
#[derive(Debug, Deserialize)]
pub struct ListWorkCentersParams {
    pub work_center_type: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating a work center.
///
/// `site_id` is OPTIONAL: supply it only when the caller can assert the
/// work center's plant site — the repository verifies the site exists
/// for the tenant and records the row as topology `resolved` /
/// `manual_reconciliation`. Without it the row is created site-less in
/// `needs_reconciliation` (unknown lineage is never certified and the
/// site-readiness gate will keep the plant unreconciled until a site is
/// provably assigned).
#[derive(Debug, Deserialize)]
pub struct CreateWorkCenterRequest {
    pub name: String,
    pub work_center_type: String,
    /// Optional site assignment asserted by the caller.
    pub site_id: Option<Uuid>,
}

/// Request body for updating a work center.
///
/// `site_id` is three-state: absent = leave the assignment untouched;
/// `null` = unassign (row becomes `needs_reconciliation`); a UUID =
/// (re)assert the assignment (site must exist for the tenant).
#[derive(Debug, Deserialize)]
pub struct UpdateWorkCenterRequest {
    pub name: Option<String>,
    pub work_center_type: Option<String>,
    #[serde(default)]
    pub site_id: Option<Option<Uuid>>,
}

/// Work center capacity overview.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkCenterCapacity {
    pub total_capacity_per_day: f64,
    pub effective_capacity_per_day: f64,
    pub utilization_percentage: f64,
}

/// Work center efficiency report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EfficiencyReport {
    pub work_center_id: Uuid,
    pub name: String,
    pub efficiency: f64,
    pub capacity_per_shift: i32,
    pub utilization: f64,
    pub is_overloaded: bool,
}

// ── Helpers ────────────────────────────────────────────────────────────────

/// The relational `work_centers` table is the single system of record —
/// every handler below needs the database.
fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state.db_pool.as_ref().map(|p| p.as_ref()).ok_or_else(|| {
        SenseiError::Database(
            "Work center API requires a database connection (relational work_centers table)"
                .to_string(),
        )
    })
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all work centers with optional type filter and pagination.
pub async fn list_work_centers(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWorkCentersParams>,
) -> Result<Json<PaginatedResponse<RelationalWorkCenter>>> {
    user.require_permission("tps:work-center:read")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    let rows = work_center_repository::list(pool, tenant_id, None).await?;

    let mut items: Vec<RelationalWorkCenter> = rows
        .into_iter()
        .filter(|wc| match &params.work_center_type {
            Some(t) => wc.work_center_type == *t,
            None => true,
        })
        .collect();

    items.sort_by(|a, b| a.work_center_number.cmp(&b.work_center_number));
    let total = items.len();
    let page = params.page.unwrap_or(1);
    let per_page = params.per_page.unwrap_or(20).min(100);
    let total_pages = total.div_ceil(per_page);
    let start = (page.saturating_sub(1)) * per_page;
    let data: Vec<RelationalWorkCenter> = items.into_iter().skip(start).take(per_page).collect();

    Ok(Json(PaginatedResponse {
        data,
        total,
        page,
        per_page,
        total_pages,
    }))
}

/// Get a specific work center by ID.
pub async fn get_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:read")?;
    let pool = pool(&state)?;
    let wc = work_center_repository::get(pool, user.tenant_id, id).await?;
    Ok(Json(wc))
}

/// Create a new work center in the relational `work_centers` table.
pub async fn create_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateWorkCenterRequest>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    // Per-tenant numbering (same WC-xxxxx rule as before, now computed
    // over the relational table).
    let work_center_number = work_center_repository::next_number(pool, tenant_id).await?;
    let wc = work_center_repository::create(
        pool,
        tenant_id,
        &NewWorkCenter {
            id: Uuid::new_v4(),
            site_id: req.site_id,
            work_center_number,
            name: req.name,
            work_center_type: req.work_center_type,
        },
    )
    .await?;

    Ok(Json(wc))
}

/// Update a work center's editable fields and/or site assignment.
pub async fn update_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateWorkCenterRequest>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    let wc = work_center_repository::update(
        pool,
        tenant_id,
        id,
        &UpdateWorkCenter {
            name: req.name,
            work_center_type: req.work_center_type,
            site_id: req.site_id,
        },
    )
    .await?;

    Ok(Json(wc))
}

/// Deactivate (soft-delete) a work center.
///
/// Flips `is_active` in the relational table; the topology assignment is
/// untouched (a deactivated work center is still part of the plant).
pub async fn deactivate_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let pool = pool(&state)?;
    let wc = work_center_repository::deactivate(pool, user.tenant_id, id).await?;
    Ok(Json(wc))
}

/// Get work center capacity and utilization metrics.
///
/// Computed from the RELATIONAL columns (`capacity_per_shift`,
/// `shifts_per_day`, `efficiency`) — the single system of record. The
/// relational `efficiency` is a fraction (default 1.0 = 100%). There is
/// no scheduled-hours input on the relational row, so utilization cannot
/// be asserted and is reported as 0 — never fabricated.
pub async fn get_work_center_capacity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<WorkCenterCapacity>> {
    user.require_permission("tps:work-center:read")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    let all = work_center_repository::metrics(pool, tenant_id).await?;
    let wc = all
        .into_iter()
        .find(|wc| wc.id == id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    let capacity_per_shift = wc.capacity_per_shift.unwrap_or(0.0);
    let shifts_per_day = wc.shifts_per_day.unwrap_or(1) as f64;
    let efficiency = wc.efficiency.unwrap_or(1.0);

    let total_capacity_per_day = capacity_per_shift * shifts_per_day;
    let effective_capacity_per_day = total_capacity_per_day * efficiency;

    Ok(Json(WorkCenterCapacity {
        total_capacity_per_day,
        effective_capacity_per_day,
        utilization_percentage: 0.0,
    }))
}

/// Get efficiency report for all active work centers.
///
/// Read from the relational columns only. `efficiency` is reported as a
/// percentage (relational fraction × 100); utilization has no
/// relational input and is reported as 0.
pub async fn get_efficiency_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<EfficiencyReport>>> {
    user.require_permission("tps:work-center:read")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    let all = work_center_repository::metrics(pool, tenant_id).await?;
    let report: Vec<EfficiencyReport> = all
        .into_iter()
        .filter(|wc| wc.is_active)
        .map(|wc| {
            let capacity_per_shift = wc.capacity_per_shift.unwrap_or(0.0);
            let efficiency = wc.efficiency.unwrap_or(1.0);
            EfficiencyReport {
                work_center_id: wc.id,
                name: wc.name,
                efficiency: efficiency * 100.0,
                capacity_per_shift: capacity_per_shift as i32,
                utilization: 0.0,
                is_overloaded: false,
            }
        })
        .collect();

    Ok(Json(report))
}

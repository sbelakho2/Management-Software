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
//! Responses carry `site_id` and `topology_state`.
//!
//! Twenty-second audit P0/P1 (authority closure): ASSIGNMENT IS NOT
//! VERIFICATION. A create/update may assert a `site_id` (the composite FK
//! verifies the site belongs to the tenant), but the row is created —
//! and a site change always returns it — as `needs_reconciliation` with
//! no provenance.
//!
//! Only the explicit `POST /work-centers/{id}/verify-topology` endpoint
//! stamps `topology_assignment_source` + `topology_verified_at` +
//! `topology_verified_by` (the authenticated user) and transitions the
//! row to `resolved`.
//!
//! Work Center READS are scope-aware: list/get are intersected with the
//! caller's RequestContext site entitlement — a zero-entitlement caller
//! sees nothing (empty list / 404), never a tenant-wide fallback.
//!
//! Twenty-third audit P0/P1 (command scope): Work Center MUTATIONS are
//! RequestContext-scoped too. create and update intersect the SUBMITTED
//! site with the caller's entitlement (a foreign site is 403 BEFORE the
//! repository runs); the high-authority verify-topology command, and
//! deactivate, prove the work center's CURRENT site is entitled via
//! `get_scoped` (foreign/site-less/absent are all NotFound); capacity
//! and the efficiency report filter by the entitlement inside
//! `metrics_scoped`.

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

use crate::routes::andon::caller_sites;
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
/// for the tenant. The row is ALWAYS created as topology
/// `needs_reconciliation` with no provenance (an asserted site is not a
/// verified one): site-less rows are unknown lineage, never certified,
/// and even a site-asserted row stays unreconciled until the explicit
/// `POST /work-centers/{id}/verify-topology` endpoint stamps provenance
/// and resolves it (the site-readiness gate refuses any tenant
/// containing an unreconciled row).
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
/// `null` = unassign; a UUID = (re)assert the assignment (site must
/// exist for the tenant). ANY explicit `site_id` write invalidates
/// verification: the row returns to `needs_reconciliation` with no
/// provenance and must be re-certified through
/// `POST /work-centers/{id}/verify-topology`.
#[derive(Debug, Deserialize)]
pub struct UpdateWorkCenterRequest {
    pub name: Option<String>,
    pub work_center_type: Option<String>,
    #[serde(default)]
    pub site_id: Option<Option<Uuid>>,
}

/// Request body for explicit topology verification
/// (`POST /work-centers/{id}/verify-topology`).
///
/// The acting authenticated user becomes `topology_verified_by`; the
/// source must be a real provenance (`manifest`, `employee_history` or
/// `manual_reconciliation`) — `legacy_heuristic` is refused. This is the
/// ONLY operation that may resolve a work center's topology.
#[derive(Debug, Deserialize)]
pub struct VerifyTopologyRequest {
    pub source: String,
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

/// Site entitlement for Work Center READS (twenty-second audit P0/P1),
/// reused from the Andon scope resolution: the FULL RequestContext
/// entitlement. Fail-closed: when the context cannot be built (or the
/// database scope resolution fails) the entitlement is EMPTY — a caller
/// then sees nothing (empty list / 404), never a tenant-wide fallback.
async fn entitlement_sites(user: &AuthenticatedUser, state: &AppState) -> Vec<Uuid> {
    caller_sites(user, state).await.unwrap_or_default()
}

/// List all work centers with optional type filter and pagination.
///
/// Scope-aware (twenty-second audit P0/P1): the listing is intersected
/// with the caller's RequestContext site entitlement INSIDE the
/// repository query (`list_scoped`) — a site-scoped caller can only
/// enumerate rows of their entitled sites, and a zero-entitlement caller
/// sees an empty page.
pub async fn list_work_centers(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWorkCentersParams>,
) -> Result<Json<PaginatedResponse<RelationalWorkCenter>>> {
    user.require_permission("tps:work-center:read")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;
    let sites = entitlement_sites(&user, &state).await;

    let rows = work_center_repository::list_scoped(pool, tenant_id, None, &sites).await?;

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
///
/// Scope-aware (twenty-second audit P0/P1): 404 unless the work center's
/// site is among the caller's RequestContext entitlement sites — the
/// scope check happens inside `get_scoped`, so a foreign-site id and a
/// nonexistent id are indistinguishable (both NotFound). A
/// zero-entitlement caller gets 404 for every id.
pub async fn get_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:read")?;
    let pool = pool(&state)?;
    let sites = entitlement_sites(&user, &state).await;
    let wc = work_center_repository::get_scoped(pool, user.tenant_id, id, &sites).await?;
    Ok(Json(wc))
}

/// Create a new work center in the relational `work_centers` table.
///
/// Twenty-third audit P0/P1 (command scope): a create that ASSERTS a
/// site may only assert one of the caller's RequestContext entitlement
/// sites — the submitted site is intersected with the caller's scope in
/// the ROUTE (a foreign site is Forbidden/403 BEFORE the repository is
/// called). A site-less create (unknown lineage, `needs_reconciliation`)
/// carries no site claim and needs no entitlement.
pub async fn create_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateWorkCenterRequest>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    // Fail-closed command scope: with NO database the entitlement is
    // EMPTY and no site can be asserted; with a database the submitted
    // site must be among the caller's entitlement sites (else 403).
    let sites = entitlement_sites(&user, &state).await;
    if let Some(site) = req.site_id {
        if !sites.contains(&site) {
            return Err(SenseiError::Forbidden(format!(
                "site {site} is not among the caller's entitlement sites — a work center \
                 can only be created at an entitled site"
            )));
        }
    }

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
///
/// Twenty-third audit P0/P1 (command scope): a REASSIGNMENT to a target
/// site is rejected in the ROUTE when that site is outside the caller's
/// RequestContext entitlement (Forbidden/403 BEFORE the repository is
/// called — the same entitlement intersect as create). Unassigning
/// (`null`) or leaving the assignment untouched carries no target site
/// and needs no entitlement.
pub async fn update_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateWorkCenterRequest>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    let sites = entitlement_sites(&user, &state).await;
    if let Some(Some(site)) = req.site_id {
        if !sites.contains(&site) {
            return Err(SenseiError::Forbidden(format!(
                "site {site} is not among the caller's entitlement sites — a work center \
                 can only be re-assigned to an entitled site"
            )));
        }
    }

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

/// Explicit topology verification (twenty-second audit P0/P1): the ONLY
/// public operation that transitions a work center to `resolved`.
/// The acting authenticated user is stamped as `topology_verified_by`
/// (never a client-supplied actor); the source must be a real provenance
/// (`manifest`, `employee_history` or `manual_reconciliation`).
/// Same manage authority as create/update.
///
/// Twenty-third audit P0/P1 (command scope): certification is a
/// HIGH-AUTHORITY write, so it gets a STRONGER scope than an ordinary
/// read — before certifying, the route proves the work center's CURRENT
/// site is inside the caller's RequestContext entitlement via
/// `get_scoped` (a foreign-site id, a site-less row and a nonexistent
/// id are all indistinguishable NotFound/404). A caller can never
/// certify a work center that lives outside their own sites.
pub async fn verify_work_center_topology(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<VerifyTopologyRequest>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;

    let sites = entitlement_sites(&user, &state).await;
    // Prove the CURRENT assignment is entitled (NotFound when the row is
    // foreign, site-less or absent — zero entitlement matches nothing).
    let _scoped = work_center_repository::get_scoped(pool, tenant_id, id, &sites).await?;

    let wc =
        work_center_repository::verify_topology(pool, tenant_id, id, user.user_id, &req.source)
            .await?;

    Ok(Json(wc))
}

/// Deactivate (soft-delete) a work center.
///
/// Flips `is_active` in the relational table; the topology assignment is
/// untouched (a deactivated work center is still part of the plant).
/// Twenty-third audit P0/P1 (command scope): deactivation is scoped via
/// `get_scoped` BEFORE acting — a work center whose CURRENT site is
/// outside the caller's entitlement (or which is site-less) is
/// indistinguishable from a nonexistent one (NotFound/404).
pub async fn deactivate_work_center(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<RelationalWorkCenter>> {
    user.require_permission("tps:work-center:manage")?;
    let pool = pool(&state)?;
    let tenant_id = user.tenant_id;
    let sites = entitlement_sites(&user, &state).await;
    let _scoped = work_center_repository::get_scoped(pool, tenant_id, id, &sites).await?;
    let wc = work_center_repository::deactivate(pool, tenant_id, id).await?;
    Ok(Json(wc))
}

/// Get work center capacity and utilization metrics.
///
/// Computed from the RELATIONAL columns (`capacity_per_shift`,
/// `shifts_per_day`, `efficiency`) — the single system of record. The
/// relational `efficiency` is a fraction (default 1.0 = 100%). There is
/// no scheduled-hours input on the relational row, so utilization cannot
/// be asserted and is reported as 0 — never fabricated.
///
/// Twenty-third audit P0/P1 (command scope): the projection is
/// intersected with the caller's RequestContext entitlement INSIDE the
/// repository (`metrics_scoped`) — a work center whose site is foreign,
/// or a site-less row, is indistinguishable from a nonexistent one
/// (NotFound/404), and a zero-entitlement caller gets 404 for every id.
pub async fn get_work_center_capacity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<WorkCenterCapacity>> {
    user.require_permission("tps:work-center:read")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;
    let sites = entitlement_sites(&user, &state).await;

    let all = work_center_repository::metrics_scoped(pool, tenant_id, &sites).await?;
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
///
/// Twenty-third audit P0/P1 (command scope): the report is intersected
/// with the caller's RequestContext entitlement INSIDE the repository
/// (`metrics_scoped`) — a site-scoped caller sees ONLY their sites'
/// active work centers, and a zero-entitlement caller gets an empty
/// report (never a tenant-wide fallback).
pub async fn get_efficiency_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<EfficiencyReport>>> {
    user.require_permission("tps:work-center:read")?;
    let tenant_id = user.tenant_id;
    let pool = pool(&state)?;
    let sites = entitlement_sites(&user, &state).await;

    let all = work_center_repository::metrics_scoped(pool, tenant_id, &sites).await?;
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

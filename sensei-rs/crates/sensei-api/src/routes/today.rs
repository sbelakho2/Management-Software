//! Today (daily dashboard / aggregated view) route handlers.
//!
//! Provides a single aggregated endpoint that returns a real-time snapshot
//! of the day's key metrics across production, quality, and operations,
//! designed for "Today Screen" / daily stand-up dashboards.
//!
//! Scope contract (twenty-ninth audit Wave B item 9): the snapshot NEVER
//! aggregates tenant-wide when it is labeled with a site/work-center
//! context. The caller's EFFECTIVE DISPLAY SCOPE is resolved once per
//! request from the server-created [`RequestContext`] (entitlement scope +
//! validated operating focus) and every counter is fetched with SQL-level
//! predicates inside that scope:
//!
//! - work orders are site-filtered through their work center
//!   (`work_centers.site_id`, migrations 134/150) — a work order without a
//!   work center has no site anchor and is invisible to site-scoped
//!   dashboards (fail closed);
//! - andons by `andons.site_id` (migration 112) / `work_center_id`;
//! - NCRs/CAPAs by their server-stamped `scope_site_id` /
//!   `scope_work_center_id` (migration 170, twenty-ninth audit Wave B
//!   items 6-8) — records with a NULL scope pair are CORPORATE
//!   (tenant-level) and are invisible to a site-scoped caller (NULL never
//!   matches `= ANY($n)`, fail closed);
//! - risks / A3s / projects carry NO site anchor in the schema (migration
//!   002): they are tenant-level objects and only appear on a
//!   tenant-wide dashboard — a site/work-center-labeled snapshot reports
//!   zero for them rather than leaking tenant numbers under a site label.
//!
//! Effective display scope rules (focus wins, then the single-site
//! fallback, then the explicit tenant-wide grant, else zeros):
//!
//! 1. `focus.work_center` present -> exact work center;
//! 2. `focus.site` present -> that site;
//! 3. scope `Sites` with exactly one site -> that site;
//! 4. scope `Sites` with several sites (no focus) -> the authorized
//!    union (never wider than the entitlement, never the whole tenant);
//! 5. scope `TenantWide` -> tenant totals;
//! 6. `NoOperationalScope` / empty -> zeros (no operational data).
//!
//! DB-less (in-memory dev/test) mode cannot resolve a scope: the shared
//! context builder grants the explicit tenant-wide scope (the in-memory
//! stores carry no site dimension), so dev mode keeps the historical
//! tenant-wide totals — the same permissive-dev convention as every other
//! route.

use axum::{extract::State, Json};
use chrono::{DateTime, NaiveDate, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::request_context::RequestContext;
use sensei_core::domain::scope::AuthorizedScope;
use sensei_core::error::Result;
use sensei_services::ops::Andon;
use sensei_services::production::{WorkOrder, WorkOrderListFilter};
use sensei_services::quality::{CapaExtended, NonConformance};
use serde::Serialize;
use uuid::Uuid;

use crate::authorization::build_request_context;
use crate::state::AppState;

// ── Response DTOs ──────────────────────────────────────────────────────────

/// Aggregated daily snapshot returned by the `/api/v1/today` endpoint.
#[derive(Debug, Serialize)]
pub struct TodaySnapshot {
    pub date: String,
    /// Site-local "today" (item 65): the timezone used for the date.
    pub timezone: String,
    /// The caller's active operational scope.
    pub scope: TodayScope,
    pub work_orders: WorkOrderSummary,
    pub quality: QualitySummary,
    pub operations: OperationsSummary,
}

/// Summary of work order activity for the day.
#[derive(Debug, Serialize)]
pub struct WorkOrderSummary {
    pub total_active: usize,
    pub completed_today: usize,
    pub in_progress: usize,
    pub overdue: usize,
}

/// Summary of quality events for the day.
#[derive(Debug, Serialize)]
pub struct QualitySummary {
    pub active_andons: usize,
    pub open_ncrs: usize,
    pub open_capas: usize,
}

/// Summary of operations/continuous improvement activity for the day.
#[derive(Debug, Serialize)]
pub struct OperationsSummary {
    pub open_risks: usize,
    pub open_a3s: usize,
    pub active_projects: usize,
}

// ── Status normalization (item 65): business-state strings are compared
// through ONE canonical form — "completed"/"Completed" are the same state,
// and the string soup cannot silently miscount.
fn status_is_completed(status: &str) -> bool {
    matches!(
        status.to_lowercase().as_str(),
        "completed" | "done" | "closed"
    )
}

fn status_is_open(status: &str) -> bool {
    !status_is_completed(status) && !status_is_cancelled(status)
}

fn status_is_in_progress(status: &str) -> bool {
    let normalized = status.trim().to_lowercase().replace(['-', ' '], "_");
    normalized == "in_progress" || normalized == "inprogress"
}

fn status_is_cancelled(status: &str) -> bool {
    matches!(
        status.to_lowercase().as_str(),
        "cancelled" | "canceled" | "voided"
    )
}

/// The caller's active operational scope (item 65) — attached to the
/// snapshot so the client can render site/shift context.
#[derive(Debug, Serialize)]
pub struct TodayScope {
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub shift_id: Option<Uuid>,
}

// ── Effective display scope (twenty-ninth audit Wave B item 9) ─────────────

/// The scope the dashboard's numbers are DISPLAYED for — resolved from the
/// caller's request context once per request. Every fetch below applies
/// this as SQL-level predicates; no helper ever pages the whole tenant.
#[derive(Debug, Clone, PartialEq, Eq)]
enum DisplayScope {
    /// No operational data: no entitlement (or an empty site set) — the
    /// snapshot reports zeros.
    NoData,
    /// Explicit tenant-wide grant: tenant totals are the honest label.
    Tenant,
    /// One display site (the operating focus, or a single-site scope).
    Site { site: Uuid },
    /// Several authorized sites, no operating focus: aggregate over the
    /// AUTHORIZED union — never the tenant.
    Sites { sites: Vec<Uuid> },
    /// Exact work center (focus wins over every scope shape).
    WorkCenter { site: Uuid, work_center: Uuid },
}

impl DisplayScope {
    /// The effective display scope from the caller's request context.
    fn resolve(rc: &RequestContext) -> Self {
        // 1. Focus wins: an active work center pins the display to that
        //    exact work center (its site is validated by the builder).
        if let Some(work_center) = rc.focus.work_center {
            if let Some(site) = rc.focus.site {
                return Self::WorkCenter { site, work_center };
            }
            // A work-center focus without a focus site is unrepresentable
            // (builder invariant) — fail closed.
            return Self::NoData;
        }
        // 2. An active site pins the display to that site.
        if let Some(site) = rc.focus.site {
            return Self::Site { site };
        }
        // 3-6. No operating focus: the entitlement decides.
        match &rc.scope {
            AuthorizedScope::NoOperationalScope => Self::NoData,
            AuthorizedScope::TenantWide => Self::Tenant,
            AuthorizedScope::Sites(sites) if sites.len() <= 1 => sites
                .first()
                .copied()
                .map_or(Self::NoData, |site| Self::Site { site }),
            AuthorizedScope::Sites(sites) => Self::Sites {
                sites: sites.clone(),
            },
            // A work-center scope without an operating focus: display its
            // exact work center (never wider than the entitlement).
            AuthorizedScope::WorkCenter(wc) => Self::WorkCenter {
                site: wc.site,
                work_center: wc.work_center,
            },
        }
    }

    fn is_no_data(&self) -> bool {
        matches!(self, Self::NoData)
    }
}

// ── SQL-level scope predicates (never tenant-wide) ─────────────────────────
//
// Every fragment is a FIXED string; the site/work-center values are bound
// as `$2::uuid[]` and compared with `= ANY($2)` — a NULL scope column
// never matches (legacy corporate records stay invisible to site-scoped
// callers) and a foreign id never matches.

/// Work orders are anchored to a site through their work center
/// (`work_centers.site_id`); a work order without a work center has no
/// site anchor and never appears on a site-scoped dashboard.
fn work_order_predicate(display: &DisplayScope) -> Option<String> {
    match display {
        DisplayScope::Site { .. } | DisplayScope::Sites { .. } => Some(
            " AND EXISTS (SELECT 1 FROM work_centers wc \
             WHERE wc.id = wo.work_center_id AND wc.site_id = ANY($2::uuid[]))"
                .to_string(),
        ),
        DisplayScope::WorkCenter { .. } => {
            Some(" AND wo.work_center_id = ANY($2::uuid[])".to_string())
        }
        DisplayScope::Tenant | DisplayScope::NoData => None,
    }
}

/// Andons are site-filtered by `andons.site_id` directly (migration 112);
/// a NULL site (legacy unanchored signal) is invisible to site callers.
fn andon_predicate(display: &DisplayScope) -> Option<String> {
    match display {
        DisplayScope::Site { .. } | DisplayScope::Sites { .. } => {
            Some(" AND site_id = ANY($2::uuid[])".to_string())
        }
        DisplayScope::WorkCenter { .. } => {
            Some(" AND work_center_id = ANY($2::uuid[])".to_string())
        }
        DisplayScope::Tenant | DisplayScope::NoData => None,
    }
}

/// Quality records (NCR/CAPA) are site-filtered by their SERVER-STAMPED
/// `scope_site_id` / `scope_work_center_id` (migration 170).
fn quality_predicate(display: &DisplayScope) -> Option<String> {
    match display {
        DisplayScope::Site { .. } | DisplayScope::Sites { .. } => {
            Some(" AND scope_site_id = ANY($2::uuid[])".to_string())
        }
        DisplayScope::WorkCenter { .. } => {
            Some(" AND scope_work_center_id = ANY($2::uuid[])".to_string())
        }
        DisplayScope::Tenant | DisplayScope::NoData => None,
    }
}

/// The display-scope ids bound to `$2` (a one-element vec for the exact
/// site / exact work-center shapes).
fn display_ids(display: &DisplayScope) -> Option<Vec<Uuid>> {
    match display {
        DisplayScope::Site { site } => Some(vec![*site]),
        DisplayScope::Sites { sites } => Some(sites.clone()),
        DisplayScope::WorkCenter { work_center, .. } => Some(vec![*work_center]),
        DisplayScope::Tenant | DisplayScope::NoData => None,
    }
}

// ── Work orders ────────────────────────────────────────────────────────────

/// Minimal work-order row both fetch paths map to before counting.
#[derive(Debug, Clone)]
struct WoRow {
    status: String,
    updated_at: DateTime<Utc>,
    scheduled_end: Option<DateTime<Utc>>,
}

fn count_work_orders(rows: &[WoRow], today: NaiveDate) -> WorkOrderSummary {
    let total_active = rows
        .iter()
        .filter(|o| !status_is_cancelled(&o.status) && !status_is_completed(&o.status))
        .count();
    let completed_today = rows
        .iter()
        .filter(|o| status_is_completed(&o.status) && o.updated_at.date_naive() == today)
        .count();
    let in_progress = rows
        .iter()
        .filter(|o| status_is_in_progress(&o.status))
        .count();
    let overdue = rows
        .iter()
        .filter(|o| {
            status_is_open(&o.status) && o.scheduled_end.is_some_and(|end| end.date_naive() < today)
        })
        .count();
    WorkOrderSummary {
        total_active,
        completed_today,
        in_progress,
        overdue,
    }
}

/// Page through every work order of the tenant — DEV / DB-less mode only
/// (the DB path is scope-predicated and never pages the tenant).
async fn fetch_all_work_orders_dev(
    state: &AppState,
    ctx: &RequestContext,
) -> Result<Vec<WorkOrder>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let filter = WorkOrderListFilter {
            status: None,
            work_center_id: None,
            page: Some(page),
            per_page: Some(PER_PAGE),
        };
        let res = state
            .production_service
            .list_work_orders(ctx, &filter)
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Fetch ONLY the work orders inside the effective display scope — SQL
/// site filtering through `work_centers.site_id` (never a tenant-wide
/// page). `DisplayScope::NoData` yields an empty set.
async fn fetch_work_orders_scoped(
    state: &AppState,
    ctx: &RequestContext,
    display: &DisplayScope,
) -> Result<Vec<WoRow>> {
    if display.is_no_data() {
        return Ok(Vec::new());
    }
    let Some(pool) = state.db_pool.as_ref() else {
        let orders = fetch_all_work_orders_dev(state, ctx).await?;
        return Ok(orders
            .into_iter()
            .map(|o| WoRow {
                status: o.status,
                updated_at: o.updated_at,
                scheduled_end: o.scheduled_end,
            })
            .collect());
    };
    let predicate_unwrapped = work_order_predicate(display).unwrap_or_default();
    let sql = format!(
        "SELECT wo.status, wo.updated_at, wo.scheduled_end \
         FROM work_orders wo WHERE wo.tenant_id = $1{predicate_unwrapped}"
    );
    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: wo tx begin: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(ctx.tenant.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("today: wo tenant ctx: {e}"))
        })?;
    let mut q =
        sqlx::query_as::<_, (String, DateTime<Utc>, Option<DateTime<Utc>>)>(&sql).bind(ctx.tenant);
    if let Some(ids) = display_ids(display) {
        q = q.bind(ids);
    }
    let rows = q.fetch_all(&mut *tx).await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: scoped WO fetch: {e}"))
    })?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: wo tx commit: {e}"))
    })?;
    Ok(rows
        .into_iter()
        .map(|(status, updated_at, scheduled_end)| WoRow {
            status,
            updated_at,
            scheduled_end,
        })
        .collect())
}

// ── Andons ─────────────────────────────────────────────────────────────────

/// Page through every Andon in the tenant — DEV / DB-less mode only.
async fn fetch_all_andons_dev(state: &AppState, tenant_id: Uuid) -> Result<Vec<Andon>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .ops_service
            .list_andons(tenant_id, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Fetch ONLY the andons inside the effective display scope — SQL-level
/// `andons.site_id` / `work_center_id` predicates.
async fn fetch_andons_scoped(
    state: &AppState,
    ctx: &RequestContext,
    display: &DisplayScope,
) -> Result<Vec<String>> {
    if display.is_no_data() {
        return Ok(Vec::new());
    }
    let Some(pool) = state.db_pool.as_ref() else {
        let all = fetch_all_andons_dev(state, ctx.tenant).await?;
        return Ok(all.into_iter().map(|a| a.status).collect());
    };
    let predicate_unwrapped = andon_predicate(display).unwrap_or_default();
    let sql = format!("SELECT status FROM andons WHERE tenant_id = $1{predicate_unwrapped}");
    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: andon tx begin: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(ctx.tenant.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("today: andon tenant ctx: {e}"))
        })?;
    let mut q = sqlx::query_as::<_, (String,)>(&sql).bind(ctx.tenant);
    if let Some(ids) = display_ids(display) {
        q = q.bind(ids);
    }
    let statuses = q.fetch_all(&mut *tx).await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: scoped andon fetch: {e}"))
    })?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: andon tx commit: {e}"))
    })?;
    Ok(statuses.into_iter().map(|(s,)| s).collect())
}

// ── NCRs / CAPAs ───────────────────────────────────────────────────────────

/// Page through every NCR of the tenant — DEV / DB-less mode only.
async fn fetch_all_ncrs_dev(state: &AppState, ctx: &RequestContext) -> Result<Vec<NonConformance>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .quality_service
            .list_ncrs(ctx, None, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Fetch ONLY the NCR statuses inside the display scope — `scope_site_id`
/// / `scope_work_center_id` predicates (migration 170). Records with a
/// NULL scope pair are invisible to a site-scoped caller.
async fn fetch_ncr_statuses_scoped(
    state: &AppState,
    ctx: &RequestContext,
    display: &DisplayScope,
) -> Result<Vec<String>> {
    if display.is_no_data() {
        return Ok(Vec::new());
    }
    let Some(pool) = state.db_pool.as_ref() else {
        let all = fetch_all_ncrs_dev(state, ctx).await?;
        return Ok(all.into_iter().map(|n| format!("{:?}", n.status)).collect());
    };
    let predicate_unwrapped = quality_predicate(display).unwrap_or_default();
    let sql = format!("SELECT status FROM ncr_reports WHERE tenant_id = $1{predicate_unwrapped}");
    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: ncr tx begin: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(ctx.tenant.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("today: ncr tenant ctx: {e}"))
        })?;
    let mut q = sqlx::query_as::<_, (String,)>(&sql).bind(ctx.tenant);
    if let Some(ids) = display_ids(display) {
        q = q.bind(ids);
    }
    let statuses = q.fetch_all(&mut *tx).await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: scoped NCR fetch: {e}"))
    })?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: ncr tx commit: {e}"))
    })?;
    Ok(statuses.into_iter().map(|(s,)| s).collect())
}

/// Page through every CAPA of the tenant — DEV / DB-less mode only.
async fn fetch_all_capas_dev(state: &AppState, ctx: &RequestContext) -> Result<Vec<CapaExtended>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let res = state
            .quality_service
            .list_capas(ctx, None, None, Some(page), Some(PER_PAGE))
            .await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// Fetch ONLY the CAPA statuses inside the display scope — `scope_site_id`
/// / `scope_work_center_id` predicates (migration 170).
async fn fetch_capa_statuses_scoped(
    state: &AppState,
    ctx: &RequestContext,
    display: &DisplayScope,
) -> Result<Vec<String>> {
    if display.is_no_data() {
        return Ok(Vec::new());
    }
    let Some(pool) = state.db_pool.as_ref() else {
        let all = fetch_all_capas_dev(state, ctx).await?;
        return Ok(all.into_iter().map(|c| format!("{:?}", c.status)).collect());
    };
    let predicate_unwrapped = quality_predicate(display).unwrap_or_default();
    let sql = format!("SELECT status FROM capas WHERE tenant_id = $1{predicate_unwrapped}");
    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: capa tx begin: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(ctx.tenant.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("today: capa tenant ctx: {e}"))
        })?;
    let mut q = sqlx::query_as::<_, (String,)>(&sql).bind(ctx.tenant);
    if let Some(ids) = display_ids(display) {
        q = q.bind(ids);
    }
    let statuses = q.fetch_all(&mut *tx).await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: scoped CAPA fetch: {e}"))
    })?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: capa tx commit: {e}"))
    })?;
    Ok(statuses.into_iter().map(|(s,)| s).collect())
}

// ── Operations (risks / A3s / projects) ────────────────────────────────────

/// Tenant-level operations counters. These entities have NO site anchor in
/// the schema (migration 002) — they are tenant-level objects, so they
/// count ONLY under the explicit tenant-wide display scope; any
/// site/work-center-labeled dashboard reports zero for them (never tenant
/// totals under a site label).
async fn operations_counts(
    state: &AppState,
    ctx: &RequestContext,
    display: &DisplayScope,
) -> Result<OperationsSummary> {
    let tenant_wide = matches!(display, DisplayScope::Tenant);
    if !tenant_wide {
        return Ok(OperationsSummary {
            open_risks: 0,
            open_a3s: 0,
            active_projects: 0,
        });
    }
    let Some(pool) = state.db_pool.as_ref() else {
        // DEV / DB-less mode: page through the in-memory stores.
        const PER_PAGE: usize = 100;
        let mut page = 1usize;
        let mut all_risks = Vec::new();
        loop {
            let res = state
                .ops_service
                .list_risks(ctx.tenant, None, None, Some(page), Some(PER_PAGE))
                .await?;
            let fetched = res.data.len();
            all_risks.extend(res.data);
            if fetched < PER_PAGE {
                break;
            }
            page += 1;
        }
        let open_risks = all_risks
            .iter()
            .filter(|r| r.status == "Open" || r.status == "Active")
            .count();
        let mut page = 1usize;
        let mut all_a3s = Vec::new();
        loop {
            let res = state
                .ops_service
                .list_a3s(ctx.tenant, None, Some(page), Some(PER_PAGE))
                .await?;
            let fetched = res.data.len();
            all_a3s.extend(res.data);
            if fetched < PER_PAGE {
                break;
            }
            page += 1;
        }
        let open_a3s = all_a3s.iter().filter(|a| a.status != "Closed").count();
        let mut page = 1usize;
        let mut all_projects = Vec::new();
        loop {
            let res = state
                .ops_service
                .list_projects(ctx.tenant, None, None, Some(page), Some(PER_PAGE))
                .await?;
            let fetched = res.data.len();
            all_projects.extend(res.data);
            if fetched < PER_PAGE {
                break;
            }
            page += 1;
        }
        let active_projects = all_projects
            .iter()
            .filter(|p| !status_is_completed(&p.status) && !status_is_cancelled(&p.status))
            .count();
        return Ok(OperationsSummary {
            open_risks,
            open_a3s,
            active_projects,
        });
    };
    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: ops tx begin: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(ctx.tenant.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("today: ops tenant ctx: {e}"))
        })?;
    // Canonical lowercase statuses are counted case-insensitively so the
    // DB rows (lowercase) are counted exactly like the domain strings.
    let open_risks: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM risks \
         WHERE tenant_id = $1 AND LOWER(status) IN ('open', 'active')",
    )
    .bind(ctx.tenant)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| sensei_core::error::SenseiError::Database(format!("today: risk count: {e}")))?;
    let open_a3s: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM a3_reports \
         WHERE tenant_id = $1 AND LOWER(status) NOT IN ('closed')",
    )
    .bind(ctx.tenant)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| sensei_core::error::SenseiError::Database(format!("today: a3 count: {e}")))?;
    let active_projects: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM projects \
         WHERE tenant_id = $1 AND LOWER(status) NOT IN \
           ('completed', 'done', 'closed', 'cancelled', 'canceled', 'voided')",
    )
    .bind(ctx.tenant)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| sensei_core::error::SenseiError::Database(format!("today: project count: {e}")))?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: ops tx commit: {e}"))
    })?;
    Ok(OperationsSummary {
        open_risks: open_risks as usize,
        open_a3s: open_a3s as usize,
        active_projects: active_projects as usize,
    })
}

// ── Handler ────────────────────────────────────────────────────────────────

/// Get the aggregated "Today" dashboard snapshot.
///
/// Aggregates data from work orders, quality (Andon, NCR, CAPA),
/// and operations (risks, A3 reports, projects) into a single
/// response for daily stand-up and management dashboards — every counter
/// aggregated WITHIN the caller's effective display scope (see the module
/// docs): never tenant-wide under a site/work-center label.
pub async fn get_today_snapshot(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<TodaySnapshot>> {
    user.require_permission("dashboard:read")?;
    // Twenty-ninth audit Wave B item 9: ONE server-created request
    // context per request (the shared authorization::build_request_context
    // builder — the andon.rs caller_sites pattern) — the display scope is
    // derived from the DB-resolved entitlement + validated operating
    // focus, never from client input.
    let ctx = build_request_context(&user, &state).await?;
    let display = DisplayScope::resolve(&ctx);

    // Item 65: "today" is the SITE's today, never UTC — the user's active
    // site timezone (resolved at request time) defines the day boundary.
    // The timezone conversion happens IN the database (PostgreSQL's
    // `AT TIME ZONE` understands every IANA zone) — no client-side tz db.
    let agent_ctx = crate::routes::agent::build_context(&user, &state).await;
    let timezone = agent_ctx.timezone.clone();
    let today: chrono::NaiveDate = if let Some(pool) = state.db_pool.as_ref() {
        sqlx::query_scalar("SELECT (NOW() AT TIME ZONE $1)::date")
            .bind(&timezone)
            .fetch_one(pool.as_ref())
            .await
            .unwrap_or_else(|_| Utc::now().date_naive())
    } else {
        Utc::now().date_naive()
    };
    let date_str = today.to_string();
    let scope = TodayScope {
        site_id: agent_ctx.site_id,
        value_stream_id: agent_ctx.value_stream_id,
        work_center_id: agent_ctx.work_center_id,
        shift_id: agent_ctx.shift_id,
    };

    // ── Work Orders ──────────────────────────────────────────────────
    let work_order_rows = fetch_work_orders_scoped(&state, &ctx, &display).await?;
    let work_order_summary = count_work_orders(&work_order_rows, today);

    // ── Quality (Andon events) ───────────────────────────────────────
    let andon_statuses = fetch_andons_scoped(&state, &ctx, &display).await?;
    let active_andons = andon_statuses
        .iter()
        .filter(|s| s.as_str() == "Active" || s.as_str() == "Open" || s.as_str() == "active")
        .count();

    // ── Quality (NCRs) ───────────────────────────────────────────────
    // "Open" means not closed/cancelled/rejected — the scope-aware fetch
    // returns only the display scope's records (site/work-center
    // predicated; legacy NULL-scope records never match).
    let ncr_statuses = fetch_ncr_statuses_scoped(&state, &ctx, &display).await?;
    let open_ncrs = ncr_statuses
        .iter()
        .filter(|s| !is_terminal_quality_status(s))
        .count();

    // CAPAs: open excludes Closed/Rejected/Cancelled.
    let capa_statuses = fetch_capa_statuses_scoped(&state, &ctx, &display).await?;
    let open_capas = capa_statuses
        .iter()
        .filter(|s| !is_terminal_quality_status(s))
        .count();

    // ── Operations (Risks, A3s, Projects) ────────────────────────────
    let operations = operations_counts(&state, &ctx, &display).await?;

    // ── Assemble response ────────────────────────────────────────────
    Ok(Json(TodaySnapshot {
        date: date_str,
        timezone,
        scope,
        work_orders: work_order_summary,
        quality: QualitySummary {
            active_andons,
            open_ncrs,
            open_capas,
        },
        operations,
    }))
}

/// A terminal quality status: Closed / Cancelled (domain) or Rejected
/// (the legacy `ncr_reports` / `capas` lifecycle). Everything else is
/// still open work.
fn is_terminal_quality_status(status: &str) -> bool {
    let normalized = status.trim().to_lowercase().replace(['-', ' '], "_");
    matches!(
        normalized.as_str(),
        "closed" | "cancelled" | "canceled" | "rejected"
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_core::domain::request_context::OperationalFocus;

    fn rc(scope: AuthorizedScope, focus: OperationalFocus) -> RequestContext {
        RequestContext {
            tenant: Uuid::new_v4(),
            principal: Uuid::new_v4(),
            scope,
            focus,
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }
    }

    fn focus(site: Option<Uuid>, work_center: Option<Uuid>) -> OperationalFocus {
        OperationalFocus {
            site,
            value_stream: None,
            work_center,
            shift: None,
        }
    }

    #[test]
    fn display_scope_focus_work_center_wins() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let other = Uuid::new_v4();
        let ctx = rc(
            AuthorizedScope::Sites(vec![site, other]),
            focus(Some(site), Some(wc)),
        );
        assert_eq!(
            DisplayScope::resolve(&ctx),
            DisplayScope::WorkCenter {
                site,
                work_center: wc
            }
        );
        // A tenant-wide caller WITH a work-center focus still displays the
        // exact work center (the focus is where the session acts).
        let ctx = rc(AuthorizedScope::tenant_wide(), focus(Some(site), Some(wc)));
        assert_eq!(
            DisplayScope::resolve(&ctx),
            DisplayScope::WorkCenter {
                site,
                work_center: wc
            }
        );
    }

    #[test]
    fn display_scope_work_center_focus_without_site_is_no_data() {
        let wc = Uuid::new_v4();
        let ctx = rc(
            AuthorizedScope::Sites(vec![Uuid::new_v4()]),
            focus(None, Some(wc)),
        );
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::NoData);
    }

    #[test]
    fn display_scope_focus_site_wins() {
        let site = Uuid::new_v4();
        let other = Uuid::new_v4();
        let ctx = rc(
            AuthorizedScope::Sites(vec![site, other]),
            focus(Some(site), None),
        );
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::Site { site });
    }

    #[test]
    fn display_scope_single_authorized_site_falls_back() {
        let site = Uuid::new_v4();
        let ctx = rc(AuthorizedScope::Sites(vec![site]), focus(None, None));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::Site { site });
    }

    #[test]
    fn display_scope_multi_site_union_never_tenant() {
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        let ctx = rc(AuthorizedScope::Sites(vec![a, b]), focus(None, None));
        assert_eq!(
            DisplayScope::resolve(&ctx),
            DisplayScope::Sites { sites: vec![a, b] }
        );
    }

    #[test]
    fn display_scope_tenant_wide_is_tenant_totals() {
        let ctx = rc(AuthorizedScope::tenant_wide(), focus(None, None));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::Tenant);
    }

    #[test]
    fn display_scope_no_operational_scope_is_zeros() {
        let ctx = rc(AuthorizedScope::NoOperationalScope, focus(None, None));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::NoData);
        let empty = rc(AuthorizedScope::Sites(vec![]), focus(None, None));
        assert_eq!(DisplayScope::resolve(&empty), DisplayScope::NoData);
    }

    #[test]
    fn display_scope_dev_mode_context_is_tenant() {
        // The DB-less builder grants the explicit tenant-wide scope.
        let ctx = rc(AuthorizedScope::tenant_wide(), focus(None, None));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::Tenant);
    }

    #[test]
    fn display_scope_work_center_scope_without_focus_displays_exact_wc() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let ctx = rc(
            AuthorizedScope::WorkCenter(sensei_core::domain::scope::WorkCenterScope {
                site,
                work_center: wc,
            }),
            focus(None, None),
        );
        assert_eq!(
            DisplayScope::resolve(&ctx),
            DisplayScope::WorkCenter {
                site,
                work_center: wc
            }
        );
    }

    #[test]
    fn terminal_quality_statuses() {
        assert!(is_terminal_quality_status("Closed"));
        assert!(is_terminal_quality_status("closed"));
        assert!(is_terminal_quality_status("Cancelled"));
        assert!(is_terminal_quality_status("rejected"));
        assert!(!is_terminal_quality_status("Open"));
        assert!(!is_terminal_quality_status("in_progress"));
        assert!(!is_terminal_quality_status("under_investigation"));
    }
}

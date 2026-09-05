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
//! 3. scope `Operational` with exactly one site -> that site;
//! 4. scope `Operational` with several sites (no focus) -> the
//!    authorized union (never wider than the entitlement, never the
//!    whole tenant);
//! 5. scope `TenantWide` -> tenant totals;
//! 6. `NoOperationalScope` / empty / an unrenderable exact work-center
//!    set -> zeros (no operational data).
//!
//! A pure work-center scope (empty site set) is never widened into its
//! site: a single granted work center displays that exact work center
//! (thirtieth-audit P0 item 1); a SET of granted work centers cannot be
//! represented by the one-WC display and fails closed (zeros).
//!
//! Local-day semantics (thirtieth-audit item 15): every date-bounded
//! counter ("completed today", "overdue") is evaluated against SITE-LOCAL
//! calendar-day windows — a half-open UTC range `[local midnight,
//! next local midnight)` resolved from `sites.timezone` IN PostgreSQL
//! (`AT TIME ZONE`), per work order via its work center's site. A UTC
//! `date_naive()` comparison against a site-local date mislabels rows
//! near local midnight (2026-09-04 23:30 UTC is already 2026-09-05
//! 00:30 at a UTC+1 site), so no `date_naive()` boundary exists here:
//! every instant is tested with `ts >= start AND ts < end` against the
//! window of the row's own site — multi-site aggregation counts each
//! row on its own site's local day. Rows without a site anchor (a
//! tenant-wide display; dev mode) fall back to the caller's active-site
//! window, and the DB-less dev convention (no site dimension ⇒ UTC) to
//! the UTC day of the displayed date.
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
use std::collections::HashMap;
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
            // Thirtieth-audit P0 item 1: a pure work-center grant stays
            // EXACT — one granted work center displays that exact work
            // center; a set of granted work centers cannot be rendered by
            // a single site/one-WC display, so it fails closed (NoData)
            // rather than widen into a whole site.
            AuthorizedScope::Operational {
                sites,
                work_centers,
            } => {
                if !work_centers.is_empty() && sites.is_empty() {
                    return if work_centers.len() == 1 {
                        let wc = work_centers.iter().next().expect("len checked == 1");
                        Self::WorkCenter {
                            site: wc.site,
                            work_center: wc.work_center,
                        }
                    } else {
                        Self::NoData
                    };
                }
                // Site grants decide the display (mixed grants display the
                // site grants only — never wider than the entitlement).
                let mut ids: Vec<Uuid> = sites.iter().copied().collect();
                ids.sort_unstable();
                match ids.len() {
                    0 => Self::NoData,
                    1 => Self::Site { site: ids[0] },
                    _ => Self::Sites { sites: ids },
                }
            }
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
/// site anchor and never appears on a site-scoped dashboard (the LEFT
/// JOIN exposes NULL `wc.site_id`, and `NULL = ANY($2)` never matches —
/// fail closed).
fn work_order_predicate(display: &DisplayScope) -> Option<String> {
    match display {
        DisplayScope::Site { .. } | DisplayScope::Sites { .. } => {
            Some(" AND wc.site_id = ANY($2::uuid[])".to_string())
        }
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

// ── Site-local day windows (thirtieth-audit item 15) ───────────────────────

/// A site-local calendar day as a half-open UTC window `[start, end)`.
///
/// The window is resolved IN PostgreSQL from the site's IANA timezone
/// (`sites.timezone`): `(NOW() AT TIME ZONE s.timezone)::date` is the
/// site-local "today" and
/// `(date::timestamp AT TIME ZONE s.timezone)` converts that local
/// midnight back to a UTC instant — no client-side timezone database is
/// needed, and DST transitions are handled by the database exactly like
/// the date label (item 65). Every "today" membership test compares UTC
/// instants with `>= start AND < end`; a UTC `date_naive()` comparison
/// against a site-local date would mislabel rows near local midnight
/// (2026-09-04 23:30 UTC is already 2026-09-05 00:30 at a UTC+1 site).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct LocalDayWindow {
    start: DateTime<Utc>,
    end: DateTime<Utc>,
}

impl LocalDayWindow {
    /// True when the UTC instant falls INSIDE the site-local day.
    fn contains(&self, ts: DateTime<Utc>) -> bool {
        ts >= self.start && ts < self.end
    }

    /// True when the UTC instant falls strictly BEFORE the site-local
    /// day — its site-local date is a PAST date (used for the overdue
    /// check: `scheduled_end`'s local date < the site-local today).
    fn is_before(&self, ts: DateTime<Utc>) -> bool {
        ts < self.start
    }

    /// The UTC-day window of `local_date` — the DB-less / dev fallback
    /// (the permissive-dev convention has no site dimension, so the
    /// site-local day IS the UTC day).
    fn utc_day(local_date: NaiveDate) -> Self {
        let start = local_date
            .and_hms_opt(0, 0, 0)
            .expect("midnight is always a valid time")
            .and_utc();
        Self {
            start,
            end: start + chrono::Duration::days(1),
        }
    }
}

/// Every site of the tenant with its site-local "today" window (the map
/// key is the `sites.id` a work order's work center anchors to). The
/// windows are computed inside the SAME transaction as the work-order
/// fetch, so `NOW()` (transaction start time) is shared by both.
async fn fetch_site_windows(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<HashMap<Uuid, LocalDayWindow>> {
    let rows: Vec<(Uuid, DateTime<Utc>, DateTime<Utc>)> = sqlx::query_as(
        "SELECT s.id, \
         ((NOW() AT TIME ZONE s.timezone)::date::timestamp AT TIME ZONE s.timezone), \
         (((NOW() AT TIME ZONE s.timezone)::date::timestamp + INTERVAL '1 day') \
             AT TIME ZONE s.timezone) \
         FROM sites s WHERE s.tenant_id = $1",
    )
    .bind(tenant_id)
    .fetch_all(&mut **tx)
    .await
    .map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: site day windows: {e}"))
    })?;
    Ok(rows
        .into_iter()
        .map(|(site, start, end)| (site, LocalDayWindow { start, end }))
        .collect())
}

// ── Work orders ────────────────────────────────────────────────────────────

/// Minimal work-order row both fetch paths map to before counting.
#[derive(Debug, Clone)]
struct WoRow {
    status: String,
    updated_at: DateTime<Utc>,
    scheduled_end: Option<DateTime<Utc>>,
    /// The site the work order anchors to through its work center
    /// (`work_centers.site_id`) — `None` for an unanchored work order
    /// (visible to a tenant-wide display only) and in dev mode.
    site_id: Option<Uuid>,
}

/// Count the display scope's work orders.
///
/// The date-bounded counters ("completed today", "overdue") test UTC
/// instants against the row's OWN site-local day window — `>= start AND
/// < end` — never a UTC `date_naive()` against the site-local date
/// (thirtieth-audit item 15). Rows whose site is unknown (unanchored
/// tenant-wide rows, dev mode) fall back to `fallback_window`.
fn count_work_orders(
    rows: &[WoRow],
    site_windows: &HashMap<Uuid, LocalDayWindow>,
    fallback_window: LocalDayWindow,
) -> WorkOrderSummary {
    let window_of = |row: &WoRow| {
        row.site_id
            .and_then(|site| site_windows.get(&site).copied())
            .unwrap_or(fallback_window)
    };
    let total_active = rows
        .iter()
        .filter(|o| !status_is_cancelled(&o.status) && !status_is_completed(&o.status))
        .count();
    let completed_today = rows
        .iter()
        .filter(|o| status_is_completed(&o.status) && window_of(o).contains(o.updated_at))
        .count();
    let in_progress = rows
        .iter()
        .filter(|o| status_is_in_progress(&o.status))
        .count();
    let overdue = rows
        .iter()
        .filter(|o| {
            status_is_open(&o.status)
                && o.scheduled_end
                    .is_some_and(|end| window_of(o).is_before(end))
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
/// page). `DisplayScope::NoData` yields an empty set. Every work order
/// carries the site its work center anchors to; the site-local "today"
/// windows of the tenant's sites are returned alongside (item 15).
async fn fetch_work_orders_scoped(
    state: &AppState,
    ctx: &RequestContext,
    display: &DisplayScope,
) -> Result<(Vec<WoRow>, HashMap<Uuid, LocalDayWindow>)> {
    if display.is_no_data() {
        return Ok((Vec::new(), HashMap::new()));
    }
    let Some(pool) = state.db_pool.as_ref() else {
        let orders = fetch_all_work_orders_dev(state, ctx).await?;
        return Ok((
            orders
                .into_iter()
                .map(|o| WoRow {
                    status: o.status,
                    updated_at: o.updated_at,
                    scheduled_end: o.scheduled_end,
                    // Dev mode has no site dimension: every row falls
                    // back to the UTC day of the displayed date.
                    site_id: None,
                })
                .collect(),
            HashMap::new(),
        ));
    };
    let predicate_unwrapped = work_order_predicate(display).unwrap_or_default();
    let sql = format!(
        "SELECT wo.status, wo.updated_at, wo.scheduled_end, wc.site_id \
         FROM work_orders wo \
         LEFT JOIN work_centers wc ON wc.id = wo.work_center_id \
         WHERE wo.tenant_id = $1{predicate_unwrapped}"
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
        sqlx::query_as::<_, (String, DateTime<Utc>, Option<DateTime<Utc>>, Option<Uuid>)>(&sql)
            .bind(ctx.tenant);
    if let Some(ids) = display_ids(display) {
        q = q.bind(ids);
    }
    let rows = q.fetch_all(&mut *tx).await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: scoped WO fetch: {e}"))
    })?;
    // The site-local day windows resolve inside the SAME transaction, so
    // the row membership tests and the windows share one NOW().
    let site_windows = fetch_site_windows(&mut tx, ctx.tenant).await?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("today: wo tx commit: {e}"))
    })?;
    Ok((
        rows.into_iter()
            .map(|(status, updated_at, scheduled_end, site_id)| WoRow {
                status,
                updated_at,
                scheduled_end,
                site_id,
            })
            .collect(),
        site_windows,
    ))
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

    // Item 65 + thirtieth-audit item 15: "today" is the SITE's today,
    // never UTC — the user's active site timezone (resolved at request
    // time) defines the day boundary. The timezone conversion happens IN
    // the database (PostgreSQL's `AT TIME ZONE` understands every IANA
    // zone) — no client-side tz db. Each date-bounded counter below
    // tests instants against site-local day windows resolved from the
    // same `sites.timezone` column.
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
    let (work_order_rows, site_windows) = fetch_work_orders_scoped(&state, &ctx, &display).await?;
    // Rows without a site anchor (a tenant-wide display with unanchored
    // work orders; dev mode) are counted on the caller's active-site
    // window — the UTC day of the displayed date when no active site
    // exists (the DB-less dev convention).
    let fallback_window = agent_ctx
        .site_id
        .and_then(|site| site_windows.get(&site).copied())
        .unwrap_or_else(|| LocalDayWindow::utc_day(today));
    let work_order_summary = count_work_orders(&work_order_rows, &site_windows, fallback_window);

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

    /// A site-grant scope (thirtieth-audit P0 item 1 representation).
    fn sites_scope(ids: Vec<Uuid>) -> AuthorizedScope {
        use sensei_core::domain::scope::WorkCenterScope;
        AuthorizedScope::Operational {
            sites: ids.into_iter().collect(),
            work_centers: std::collections::HashSet::<WorkCenterScope>::new(),
        }
    }

    /// A pure work-center-grant scope: exact (site, wc), never the site.
    fn wc_scope(site: Uuid, work_center: Uuid) -> AuthorizedScope {
        use sensei_core::domain::scope::WorkCenterScope;
        AuthorizedScope::Operational {
            sites: std::collections::HashSet::new(),
            work_centers: std::collections::HashSet::from([WorkCenterScope { site, work_center }]),
        }
    }

    #[test]
    fn display_scope_focus_work_center_wins() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let other = Uuid::new_v4();
        let ctx = rc(sites_scope(vec![site, other]), focus(Some(site), Some(wc)));
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
        let ctx = rc(sites_scope(vec![Uuid::new_v4()]), focus(None, Some(wc)));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::NoData);
    }

    #[test]
    fn display_scope_focus_site_wins() {
        let site = Uuid::new_v4();
        let other = Uuid::new_v4();
        let ctx = rc(sites_scope(vec![site, other]), focus(Some(site), None));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::Site { site });
    }

    #[test]
    fn display_scope_single_authorized_site_falls_back() {
        let site = Uuid::new_v4();
        let ctx = rc(sites_scope(vec![site]), focus(None, None));
        assert_eq!(DisplayScope::resolve(&ctx), DisplayScope::Site { site });
    }

    #[test]
    fn display_scope_multi_site_union_never_tenant() {
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        let ctx = rc(sites_scope(vec![a, b]), focus(None, None));
        // The display union is the deterministic SORTED site set.
        let mut expected = vec![a, b];
        expected.sort_unstable();
        assert_eq!(
            DisplayScope::resolve(&ctx),
            DisplayScope::Sites { sites: expected }
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
        let empty = rc(sites_scope(vec![]), focus(None, None));
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
        let ctx = rc(wc_scope(site, wc), focus(None, None));
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

    // ── Site-local day windows (thirtieth-audit item 15) ──────────────────

    fn dt(s: &str) -> DateTime<Utc> {
        DateTime::parse_from_rfc3339(s)
            .expect("valid rfc3339")
            .with_timezone(&Utc)
    }

    /// The audit's boundary example, both signs: a UTC instant INSIDE a
    /// site-local day whose UTC `date_naive()` is the WRONG date.
    ///
    /// - UTC+1 site (local 2026-09-05): local midnight = 2026-09-04
    ///   23:00 UTC; 2026-09-04 23:30 UTC is local 00:30 on 09-05.
    /// - UTC-5 site (local 2026-09-05): local midnight = 2026-09-05
    ///   05:00 UTC; 2026-09-06 04:30 UTC is local 23:30 on 09-05.
    #[test]
    fn local_day_windows_use_site_local_date_not_utc_date_naive() {
        // UTC+1 site's local 2026-09-05.
        let plus1 = LocalDayWindow {
            start: dt("2026-09-04T23:00:00Z"),
            end: dt("2026-09-05T23:00:00Z"),
        };
        let in_plus1_day = dt("2026-09-04T23:30:00Z");
        assert!(plus1.contains(in_plus1_day));
        assert_eq!(in_plus1_day.date_naive().to_string(), "2026-09-04");
        assert_ne!(
            in_plus1_day.date_naive(),
            NaiveDate::from_ymd_opt(2026, 9, 5).expect("valid"),
            "the UTC date differs from the site-local date — this is the \
             mismatch a date_naive() comparison gets wrong"
        );
        // One minute before local midnight: still yesterday locally.
        assert!(!plus1.contains(dt("2026-09-04T22:59:00Z")));
        // Local midnight belongs to the NEW day.
        assert!(plus1.contains(dt("2026-09-04T23:00:00Z")));
        assert!(!plus1.contains(dt("2026-09-05T23:00:00Z")));

        // UTC-5 site's local 2026-09-05.
        let minus5 = LocalDayWindow {
            start: dt("2026-09-05T05:00:00Z"),
            end: dt("2026-09-06T05:00:00Z"),
        };
        let in_minus5_day = dt("2026-09-06T04:30:00Z");
        assert!(minus5.contains(in_minus5_day));
        assert_eq!(in_minus5_day.date_naive().to_string(), "2026-09-06");
        assert_ne!(
            in_minus5_day.date_naive(),
            NaiveDate::from_ymd_opt(2026, 9, 5).expect("valid"),
            "same mismatch in the other direction"
        );
        assert!(minus5.is_before(dt("2026-09-05T04:59:59Z")));
        assert!(!minus5.is_before(dt("2026-09-05T05:00:00Z")));
    }

    fn wo(
        status: &str,
        updated_at: DateTime<Utc>,
        scheduled_end: Option<DateTime<Utc>>,
        site: Option<Uuid>,
    ) -> WoRow {
        WoRow {
            status: status.to_string(),
            updated_at,
            scheduled_end,
            site_id: site,
        }
    }

    #[test]
    fn completed_today_counts_each_rows_site_local_day() {
        // Site A is UTC+1 (local 2026-09-05); site B is UTC-5 (local
        // 2026-09-05). The SAME UTC instant 2026-09-04 23:30 is already
        // 09-05 00:30 at A but still 09-04 18:30 at B.
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let mut windows = HashMap::new();
        windows.insert(
            site_a,
            LocalDayWindow {
                start: dt("2026-09-04T23:00:00Z"),
                end: dt("2026-09-05T23:00:00Z"),
            },
        );
        windows.insert(
            site_b,
            LocalDayWindow {
                start: dt("2026-09-05T05:00:00Z"),
                end: dt("2026-09-06T05:00:00Z"),
            },
        );
        let fallback = LocalDayWindow::utc_day(NaiveDate::from_ymd_opt(2026, 9, 5).expect("valid"));

        let rows = vec![
            // Completed at 2026-09-04 23:30 UTC: A's local 09-05 00:30
            // (counted), B's local 09-04 18:30 (NOT counted).
            wo("completed", dt("2026-09-04T23:30:00Z"), None, Some(site_a)),
            wo("completed", dt("2026-09-04T23:30:00Z"), None, Some(site_b)),
            // Completed yesterday locally at A (local 09-04 23:00).
            wo("completed", dt("2026-09-04T22:00:00Z"), None, Some(site_a)),
        ];
        let summary = count_work_orders(&rows, &windows, fallback);
        assert_eq!(
            summary.completed_today, 1,
            "only A's row falls inside A's local 09-05 — the same UTC \
             instant is still 09-04 at B, and the third row is A's \
             yesterday"
        );
        assert_eq!(summary.total_active, 0);
        // A tenant-wide caller (no per-site window) falls back to the UTC
        // day of the displayed date.
        let summary = count_work_orders(&rows, &HashMap::new(), fallback);
        assert_eq!(
            summary.completed_today, 0,
            "all three instants carry a UTC date other than 2026-09-05"
        );
    }

    #[test]
    fn overdue_compares_scheduled_end_on_the_rows_site_local_day() {
        let site_a = Uuid::new_v4();
        let mut windows = HashMap::new();
        windows.insert(
            site_a,
            LocalDayWindow {
                start: dt("2026-09-04T23:00:00Z"),
                end: dt("2026-09-05T23:00:00Z"),
            },
        );
        let fallback = LocalDayWindow::utc_day(NaiveDate::from_ymd_opt(2026, 9, 5).expect("valid"));

        let rows = vec![
            // Due local 09-04 23:00 (= UTC 09-04 22:00) — local date
            // 09-04 is BEFORE A's local today 09-05: overdue, although
            // its UTC date_naive (09-04) is the only date an unadjusted
            // comparison would call "yesterday" — the old code called it
            // overdue for the wrong reason but must STILL be overdue.
            wo(
                "open",
                dt("2026-09-04T23:00:00Z"),
                Some(dt("2026-09-04T22:00:00Z")),
                Some(site_a),
            ),
            // Due local 09-05 00:30 (= UTC 09-04 23:30): STILL TODAY at
            // A — the UTC date_naive 09-04 < local today 09-05 made the
            // old code call this overdue; the site-local date says no.
            wo(
                "open",
                dt("2026-09-04T23:30:00Z"),
                Some(dt("2026-09-04T23:30:00Z")),
                Some(site_a),
            ),
            // Due local 09-05 23:00 (= UTC 09-05 22:00): today, not
            // overdue.
            wo(
                "open",
                dt("2026-09-05T22:00:00Z"),
                Some(dt("2026-09-05T22:00:00Z")),
                Some(site_a),
            ),
        ];
        let summary = count_work_orders(&rows, &windows, fallback);
        assert_eq!(
            summary.overdue, 1,
            "only the 09-04 local due date is past A's local today"
        );
        assert_eq!(summary.total_active, 3);
    }
}

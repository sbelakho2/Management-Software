//! Export route handler for generating PDF, XLSX, and CSV reports.
//!
//! # Endpoint
//!
//! `GET /api/v1/export/{entity_type}?format=pdf|csv|xlsx&id=...&date_from=...&date_to=...`
//!
//! Supported entity types: `ncr`, `capa`, `audit`, `work-order`, `inspection`.
//!
//! The tenant is always taken from the authenticated token; a client-supplied
//! `tenant_id` query parameter is ignored so exports can never cross tenant
//! boundaries.

use axum::{
    extract::{Path, Query, State},
    http::{header, StatusCode},
    response::{IntoResponse, Response},
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::RequestContext;
use sensei_core::error::{Result, SenseiError};
use sensei_services::authz_sql::DbScopeFilter;
use sensei_services::export::pdf::{AuditData, CapaData, InspectionData, NcrData, WorkOrderData};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

/// Page size used when fetching every page of a list for export.
const EXPORT_PAGE_SIZE: usize = 500;

/// Query parameters for export requests.
#[derive(Debug, Deserialize)]
pub struct ExportParams {
    /// Output format: "pdf", "csv", or "xlsx".
    pub format: String,
    /// Optional entity ID (fetches single entity).
    pub id: Option<Uuid>,
    /// Optional status filter.
    pub status: Option<String>,
    /// Optional date range start (RFC 3339).
    pub date_from: Option<String>,
    /// Optional date range end (RFC 3339).
    pub date_to: Option<String>,
}

/// Parse an optional RFC 3339 date filter; invalid values are rejected with
/// a 400 instead of silently disabling the filter.
fn parse_date_filter(name: &str, value: Option<&str>) -> Result<Option<DateTime<Utc>>> {
    match value {
        Some(raw) => DateTime::parse_from_rfc3339(raw)
            .map(|dt| Some(dt.with_timezone(&Utc)))
            .map_err(|e| {
                SenseiError::Validation(format!("Invalid {name} (expected RFC 3339): {e}"))
            }),
        None => Ok(None),
    }
}

/// Filter records by the optional created-at date range.
fn within_date_range(
    created_at: DateTime<Utc>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> bool {
    date_from.is_none_or(|from| created_at >= from) && date_to.is_none_or(|to| created_at <= to)
}

/// Export an entity as PDF, CSV, or XLSX.
///
/// Fetches data from the appropriate domain service (quality, production, etc.)
/// and generates the requested output format. The tenant comes from the
/// authenticated token only.
pub async fn export_entity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(entity_type): Path<String>,
    Query(params): Query<ExportParams>,
) -> Result<Response> {
    // Per-entity domain authorization (Wave B): exporting an entity
    // requires the READ permission of its OWNING domain — never the
    // blanket system:audit:read. Unknown entity types are rejected here
    // (deny by default) before any dispatch.
    let required = match entity_type.as_str() {
        "ncr" => "quality:ncr:read",
        "capa" => "quality:capa:read",
        "audit" => "quality:audit:read",
        "inspection" => "quality:inspection:read",
        "work-order" => "production:work-order:read",
        other => {
            return Err(SenseiError::NotFound(format!(
            "Unknown entity type: '{other}'. Supported: ncr, capa, audit, work-order, inspection"
        )))
        }
    };
    user.require_permission(required)?;
    // Validate format
    let format = params.format.to_lowercase();
    if !matches!(format.as_str(), "pdf" | "csv" | "xlsx") {
        return Err(SenseiError::Validation(format!(
            "Unsupported export format: '{format}'. Supported: pdf, csv, xlsx"
        )));
    }

    // Parse (and validate) the date filters once, before dispatching.
    let date_from = parse_date_filter("date_from", params.date_from.as_deref())?;
    let date_to = parse_date_filter("date_to", params.date_to.as_deref())?;

    // Twenty-ninth audit Wave B items 6-8 + thirtieth-audit item 16: the
    // NCR / CAPA / audit / inspection exports read through the caller's
    // server-created request context — site-scoped callers only ever
    // export their authorized records. The NCR / CAPA / audit lists are
    // scope-enforced inside the quality service; the inspection export
    // applies the same scope discipline at the route layer (see
    // [`export_inspection`]). The DB-backed builder is the andon
    // caller_sites pattern replicated for this route file.
    let qctx = crate::routes::quality::caller_ctx(&user, &state).await?;

    match entity_type.as_str() {
        "ncr" => {
            export_ncr(
                state,
                &qctx,
                &format,
                params.id,
                params.status.as_deref(),
                date_from,
                date_to,
            )
            .await
        }
        "capa" => {
            export_capa(
                state,
                &qctx,
                &format,
                params.id,
                params.status.as_deref(),
                date_from,
                date_to,
            )
            .await
        }
        "audit" => {
            export_audit(
                state,
                &qctx,
                &format,
                params.id,
                params.status.as_deref(),
                date_from,
                date_to,
            )
            .await
        }
        "work-order" => {
            // Twenty-ninth audit Wave B item 7: build the request context
            // ONCE per request — the export can only read the caller's
            // authorized work orders (the scope is enforced inside the
            // service).
            let ctx = crate::authorization::build_request_context(&user, &state).await?;
            export_work_order(
                state,
                ctx,
                &format,
                params.id,
                params.status.as_deref(),
                date_from,
                date_to,
            )
            .await
        }
        "inspection" => {
            export_inspection(
                state,
                &qctx,
                &format,
                params.id,
                params.status.as_deref(),
                date_from,
                date_to,
            )
            .await
        }
        other => Err(SenseiError::NotFound(format!(
            "Unknown entity type: '{other}'. Supported: ncr, capa, audit, work-order, inspection"
        ))),
    }
}

/// Fetch every page of a paginated service result (page size 500) so
/// exports cover the full dataset, not just the first page.
///
/// `fetch_page(page)` returns the page; the loop stops when a page returns
/// fewer items than the page size or the response's page count is reached.
async fn fetch_all_pages<T, F>(mut fetch_page: F) -> Result<Vec<T>>
where
    F: FnMut(usize) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Vec<T>>> + Send>>,
{
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let items = fetch_page(page).await?;
        let count = items.len();
        all.extend(items);
        if count < EXPORT_PAGE_SIZE {
            break;
        }
        page += 1;
        if page > 10_000 {
            // Safety valve: never loop unbounded on a pathological store.
            break;
        }
    }
    Ok(all)
}

// ── Entity-specific export logic ─────────────────────────────────────────

/// Export NCR(s) in the requested format (the caller's request context
/// scopes every read — twenty-ninth audit Wave B items 6-8).
async fn export_ncr(
    state: AppState,
    ctx: &RequestContext,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let ncrs = if let Some(ncr_id) = id {
        let ncr = state.quality_service.get_ncr(ctx, ncr_id).await?;
        vec![ncr]
    } else {
        let status_owned = status.map(|s| s.to_string());
        let ctx_owned = ctx.clone();
        fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            let status = status_owned.clone();
            let ctx = ctx_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_ncrs(
                        &ctx,
                        status.as_deref(),
                        None,
                        None,
                        Some(page),
                        Some(EXPORT_PAGE_SIZE),
                    )
                    .await?;
                Ok(page.data)
            })
        })
        .await?
        .into_iter()
        .filter(|ncr| within_date_range(ncr.created_at, date_from, date_to))
        .collect::<Vec<_>>()
    };

    match format {
        "pdf" => {
            let pdf_data = ncrs
                .into_iter()
                .map(|ncr| {
                    let pdf_svc = &state.pdf_service;
                    let corrective_actions: Vec<String> = ncr
                        .disposition
                        .iter()
                        .cloned()
                        .chain(ncr.root_cause.iter().cloned())
                        .collect();
                    let data = NcrData {
                        id: ncr.id.to_string(),
                        title: ncr.title,
                        description: ncr.description,
                        status: ncr.status.as_str().to_string(),
                        severity: nc_severity_str(&ncr.severity).to_string(),
                        created_by: ncr.detected_by.map(|u| u.to_string()).unwrap_or_default(),
                        created_at: ncr.created_at.to_rfc3339(),
                        department: ncr.department.unwrap_or_default(),
                        corrective_actions,
                    };
                    pdf_svc.generate_ncr_report(&data)
                })
                .collect::<Result<Vec<_>>>()?
                .into_iter()
                .flatten()
                .collect::<Vec<_>>();

            Ok(build_pdf_response(pdf_data))
        }
        "xlsx" => {
            let excel_svc = &state.excel_service;
            let data = excel_svc.generate_xlsx(&ncrs, "NCRs")?;
            Ok(build_xlsx_response(data))
        }
        _ => {
            let excel_svc = &state.excel_service;
            let csv = excel_svc.generate_csv(&ncrs)?;
            Ok(build_csv_response(csv))
        }
    }
}

/// Export CAPA(s) in the requested format (scope from the request
/// context — twenty-ninth audit Wave B items 6-8).
async fn export_capa(
    state: AppState,
    ctx: &RequestContext,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let capas = if let Some(capa_id) = id {
        let capa = state.quality_service.get_capa(ctx, capa_id).await?;
        vec![capa]
    } else {
        let status_owned = status.map(|s| s.to_string());
        let ctx_owned = ctx.clone();
        fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            let status = status_owned.clone();
            let ctx = ctx_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_capas(
                        &ctx,
                        status.as_deref(),
                        None,
                        Some(page),
                        Some(EXPORT_PAGE_SIZE),
                    )
                    .await?;
                Ok(page.data)
            })
        })
        .await?
        .into_iter()
        .filter(|capa| within_date_range(capa.created_at, date_from, date_to))
        .collect::<Vec<_>>()
    };

    match format {
        "pdf" => {
            let pdf_data = capas
                .into_iter()
                .map(|capa| {
                    let pdf_svc = &state.pdf_service;
                    let root_cause = capa
                        .root_cause_analyses
                        .first()
                        .map(|rca| rca.description.clone())
                        .unwrap_or_default();
                    let action_plan = capa
                        .actions
                        .first()
                        .map(|a| a.description.clone())
                        .unwrap_or_default();
                    let data = CapaData {
                        id: capa.id.to_string(),
                        title: capa.title,
                        description: capa.description,
                        root_cause,
                        action_plan,
                        status: capa_status_str(&capa.status).to_string(),
                        deadline: capa.due_date.map(|d| d.to_rfc3339()).unwrap_or_default(),
                        assigned_to: capa.owner_id.map(|u| u.to_string()).unwrap_or_default(),
                    };
                    pdf_svc.generate_capa_report(&data)
                })
                .collect::<Result<Vec<_>>>()?
                .into_iter()
                .flatten()
                .collect::<Vec<_>>();

            Ok(build_pdf_response(pdf_data))
        }
        "xlsx" => {
            let excel_svc = &state.excel_service;
            let data = excel_svc.generate_xlsx(&capas, "CAPAs")?;
            Ok(build_xlsx_response(data))
        }
        _ => {
            let excel_svc = &state.excel_service;
            let csv = excel_svc.generate_csv(&capas)?;
            Ok(build_csv_response(csv))
        }
    }
}

/// Export Audit(s) in the requested format (scope from the request
/// context — twenty-ninth audit Wave B items 6-8).
async fn export_audit(
    state: AppState,
    ctx: &RequestContext,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let audits = if let Some(audit_id) = id {
        let audit = state.quality_service.get_audit(ctx, audit_id).await?;
        vec![audit]
    } else {
        let status_owned = status.map(|s| s.to_string());
        let ctx_owned = ctx.clone();
        fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            let status = status_owned.clone();
            let ctx = ctx_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_audits(
                        &ctx,
                        status.as_deref(),
                        None,
                        Some(page),
                        Some(EXPORT_PAGE_SIZE),
                    )
                    .await?;
                Ok(page.data)
            })
        })
        .await?
        .into_iter()
        .filter(|audit| within_date_range(audit.created_at, date_from, date_to))
        .collect::<Vec<_>>()
    };

    match format {
        "pdf" => {
            let pdf_data = audits
                .into_iter()
                .map(|audit| {
                    let pdf_svc = &state.pdf_service;
                    let findings: Vec<(String, String, String)> = audit
                        .checklist_items
                        .iter()
                        .map(|item| {
                            (
                                String::new(),
                                item.question.clone(),
                                item.is_conforming
                                    .map(|c| if c { "Pass" } else { "Fail" }.to_string())
                                    .unwrap_or_else(|| "Pending".to_string()),
                            )
                        })
                        .collect();

                    // Real audit score: conforming checklist items / total.
                    let total_items = audit.checklist_items.len();
                    let conforming = audit
                        .checklist_items
                        .iter()
                        .filter(|i| i.is_conforming == Some(true))
                        .count();
                    let score = if total_items > 0 {
                        (conforming as f64 / total_items as f64) * 100.0
                    } else {
                        0.0
                    };

                    let data = AuditData {
                        id: audit.id.to_string(),
                        title: audit.title,
                        auditor: audit
                            .auditor_id
                            .or(audit.lead_auditor_id)
                            .map(|u| u.to_string())
                            .unwrap_or_default(),
                        auditee: audit.area.clone(),
                        date: audit
                            .scheduled_date
                            .or(audit.start_date)
                            .or(audit.completion_date)
                            .map(|d| d.to_rfc3339())
                            .unwrap_or_default(),
                        scope: audit.scope,
                        findings,
                        score,
                        status: audit_status_str(&audit.status).to_string(),
                    };
                    pdf_svc.generate_audit_report(&data)
                })
                .collect::<Result<Vec<_>>>()?
                .into_iter()
                .flatten()
                .collect::<Vec<_>>();

            Ok(build_pdf_response(pdf_data))
        }
        "xlsx" => {
            let excel_svc = &state.excel_service;
            let data = excel_svc.generate_xlsx(&audits, "Audits")?;
            Ok(build_xlsx_response(data))
        }
        _ => {
            let excel_svc = &state.excel_service;
            let csv = excel_svc.generate_csv(&audits)?;
            Ok(build_csv_response(csv))
        }
    }
}

/// Export Work Order(s) in the requested format.
///
/// The caller's [`RequestContext`] is passed through every service call:
/// an export can never include a work order outside the caller's
/// authorized scope.
async fn export_work_order(
    state: AppState,
    ctx: sensei_core::domain::request_context::RequestContext,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let orders = if let Some(wo_id) = id {
        let wo = state.production_service.get_work_order(&ctx, wo_id).await?;
        vec![wo]
    } else {
        let status_owned = status.map(|s| s.to_string());
        fetch_all_pages(|page| {
            let svc = state.production_service.clone();
            let ctx = ctx.clone();
            let status = status_owned.clone();
            Box::pin(async move {
                let filter = sensei_services::production::WorkOrderListFilter {
                    status,
                    work_center_id: None,
                    page: Some(page),
                    per_page: Some(EXPORT_PAGE_SIZE),
                };
                let page = svc.list_work_orders(&ctx, &filter).await?;
                Ok(page.data)
            })
        })
        .await?
        .into_iter()
        .filter(|wo| within_date_range(wo.created_at, date_from, date_to))
        .collect::<Vec<_>>()
    };

    match format {
        "pdf" => {
            let pdf_data = orders
                .into_iter()
                .map(|wo| {
                    let pdf_svc = &state.pdf_service;
                    let data = WorkOrderData {
                        id: wo.id.to_string(),
                        title: wo.wo_number.clone(),
                        description: wo.notes.clone(),
                        status: wo.status.clone(),
                        priority: wo.priority.clone(),
                        assigned_to: wo
                            .assigned_to
                            .first()
                            .map(|u| u.to_string())
                            .unwrap_or_default(),
                        due_date: wo
                            .scheduled_end
                            .or(wo.actual_end)
                            .map(|d| d.to_rfc3339())
                            .unwrap_or_default(),
                        work_center: wo.work_center_id.map(|u| u.to_string()).unwrap_or_default(),
                        // Estimated hours are not tracked on the work order
                        // entity; derive a duration estimate from the
                        // scheduled window when one exists.
                        estimated_hours: wo
                            .scheduled_start
                            .zip(wo.scheduled_end)
                            .map(|(s, e)| (e - s).num_minutes() as f64 / 60.0)
                            .unwrap_or(0.0),
                    };
                    pdf_svc.generate_work_order(&data)
                })
                .collect::<Result<Vec<_>>>()?
                .into_iter()
                .flatten()
                .collect::<Vec<_>>();

            Ok(build_pdf_response(pdf_data))
        }
        "xlsx" => {
            let excel_svc = &state.excel_service;
            let data = excel_svc.generate_xlsx(&orders, "WorkOrders")?;
            Ok(build_xlsx_response(data))
        }
        _ => {
            let excel_svc = &state.excel_service;
            let csv = excel_svc.generate_csv(&orders)?;
            Ok(build_csv_response(csv))
        }
    }
}

// ── Inspection export (thirtieth-audit item 16) ───────────────────────────

/// The `inspections` status values the export filters on (canonical CHECK
/// list in migration 002) are compared with the same normalized equality
/// everywhere: `LOWER(status) = LOWER($param)` in SQL, the equivalent
/// trim+lowercase match on the in-memory dev rows.
fn inspection_status_matches(row_status: &str, filter: Option<&str>) -> bool {
    match filter {
        Some(filter) => row_status.trim().to_lowercase() == filter.trim().to_lowercase(),
        None => true,
    }
}

/// A canonical `inspections` row (migration 002) exported by the
/// DB-backed path — the resource the migration-170 scope stamp lives on.
struct ScopedInspectionRow {
    id: Uuid,
    inspection_number: String,
    inspection_type: String,
    product_id: Option<Uuid>,
    work_order_id: Option<Uuid>,
    result: String,
    status: String,
    inspector_id: Option<Uuid>,
    created_at: DateTime<Utc>,
}

/// The SQL scope predicate over the canonical `inspections` scope stamp
/// (migration 170) — the caller's [`DbScopeFilter`] applied to the
/// carrier subquery that exposes the stamp as the `(site_id,
/// work_center_id)` column contract the scope fragments reference
/// (`scope_site_id` / `scope_work_center_id`, NULL = a corporate record).
///
/// - `TenantWide` → no predicate (the `tenant_id` predicate is the whole
///   boundary; corporate rows included);
/// - `Operational` (site grants) → `scope_site_id = ANY($n)` — a NULL
///   stamp (corporate) never matches, fail closed;
/// - `Operational` (exact work-center grants only) → the stamp's
///   `(site, work_center)` must equal a granted pair — a work-center
///   grant never widens into its site;
/// - no operational scope → `1 = 0`: zero rows.
fn inspection_scope_extra(scope: &DbScopeFilter) -> (String, bool, usize) {
    let (scope_clause, tenant_wide) = scope.where_clause_for("sc", 6);
    let bind_count = match scope {
        DbScopeFilter::Operational {
            sites,
            work_centers,
        } => usize::from(!sites.is_empty()) + 2 * work_centers.len(),
        DbScopeFilter::TenantWide | DbScopeFilter::None => 0,
    };
    let extra = if tenant_wide {
        String::new()
    } else {
        format!(" AND {scope_clause}")
    };
    (extra, tenant_wide, bind_count)
}

/// Fetch the canonical `inspections` rows the caller's scope entitles —
/// scope, status, id and date range are all SQL-level predicates (never
/// a tenant-wide page, and the status argument is material instead of
/// fetch-broadly-then-ignore).
async fn fetch_scoped_canonical_inspections(
    pool: &sqlx::PgPool,
    ctx: &RequestContext,
    status: Option<&str>,
    id: Option<Uuid>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Vec<ScopedInspectionRow>> {
    let scope = DbScopeFilter::from_authorized(&ctx.scope);
    let (scope_extra, tenant_wide, scope_binds) = inspection_scope_extra(&scope);
    let carrier_join = if tenant_wide {
        String::new()
    } else {
        "JOIN (SELECT i.id AS inspection_id, \
                      i.scope_site_id AS site_id, \
                      i.scope_work_center_id AS work_center_id \
               FROM inspections i) AS sc ON sc.inspection_id = insp.id"
            .to_string()
    };
    // Placeholder map: $1 tenant · $2 status · $3 id · $4 date_from ·
    // $5 date_to · $6.. scope · LIMIT/OFFSET after the scope binds.
    let limit_param = 6 + scope_binds;
    let offset_param = limit_param + 1;
    let sql = format!(
        "SELECT insp.id, insp.inspection_number, insp.inspection_type, \
                insp.product_id, insp.work_order_id, insp.result, \
                insp.status, insp.inspector_id, insp.created_at \
         FROM inspections insp {carrier_join} \
         WHERE insp.tenant_id = $1 \
           AND ($2::text IS NULL OR LOWER(insp.status) = LOWER($2)) \
           AND ($3::uuid IS NULL OR insp.id = $3) \
           AND ($4::timestamptz IS NULL OR insp.created_at >= $4) \
           AND ($5::timestamptz IS NULL OR insp.created_at <= $5){scope_extra} \
         ORDER BY insp.created_at DESC, insp.id \
         LIMIT ${limit_param} OFFSET ${offset_param}"
    );

    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("export: inspection tx begin: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(ctx.tenant.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!("export: inspection tenant ctx: {e}"))
        })?;

    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let mut q = sqlx::query_as::<
            _,
            (
                Uuid,
                String,
                String,
                Option<Uuid>,
                Option<Uuid>,
                String,
                String,
                Option<Uuid>,
                DateTime<Utc>,
            ),
        >(&sql)
        .bind(ctx.tenant)
        .bind(status.map(|s| s.to_string()))
        .bind(id)
        .bind(date_from)
        .bind(date_to);
        if !tenant_wide {
            if let DbScopeFilter::Operational {
                sites,
                work_centers,
            } = &scope
            {
                if !sites.is_empty() {
                    q = q.bind(sites.clone());
                }
                for wc in work_centers {
                    q = q.bind(wc.site).bind(wc.work_center);
                }
            }
        }
        let offset = ((page - 1) * EXPORT_PAGE_SIZE) as i64;
        q = q.bind(EXPORT_PAGE_SIZE as i64).bind(offset);
        type ScopedInspectionTuple = (
            Uuid,
            String,
            String,
            Option<Uuid>,
            Option<Uuid>,
            String,
            String,
            Option<Uuid>,
            DateTime<Utc>,
        );
        let rows: Vec<ScopedInspectionTuple> = q.fetch_all(&mut *tx).await.map_err(|e| {
            sensei_core::error::SenseiError::Database(format!(
                "export: scoped inspection fetch: {e}"
            ))
        })?;
        let count = rows.len();
        all.extend(rows.into_iter().map(
            |(
                id,
                inspection_number,
                inspection_type,
                product_id,
                work_order_id,
                result,
                status,
                inspector_id,
                created_at,
            )| {
                ScopedInspectionRow {
                    id,
                    inspection_number,
                    inspection_type,
                    product_id,
                    work_order_id,
                    result,
                    status,
                    inspector_id,
                    created_at,
                }
            },
        ));
        if count < EXPORT_PAGE_SIZE {
            break;
        }
        page += 1;
        if page > 10_000 {
            break;
        }
    }
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("export: inspection tx commit: {e}"))
    })?;
    Ok(all)
}

/// Export Inspection(s) in the requested format.
///
/// Thirtieth-audit item 16: the inspection export no longer reads
/// through the tenant-oriented inspection APIs
/// (`list_first_article_inspections` / `list_self_inspections` /
/// `get_first_article_inspection` / `get_self_inspection` take a naked
/// `tenant_id` — the [`QualityService`] trait has NO context-aware
/// inspection read on the current tree; the concurrent item-6 work in
/// `sensei-services/src/quality/**` is consumed here only as it exists,
/// i.e. not yet). Consumed on the current tree instead:
///
/// - the route-layer authorization used by the quality get/list surface
///   — the server-created [`RequestContext`] (`caller_ctx`), and
/// - [`DbScopeFilter`] (the same scope-to-SQL bridge the scoped
///   repositories use) applied to the canonical `inspections` table's
///   migration-170 `scope_site_id` / `scope_work_center_id` stamp at the
///   SQL level — status / id / date-range filters ride in the SAME
///   statement, so a site-B inspection can never appear in a site-A
///   export and the status argument is material (a mismatched filter
///   returns zero rows instead of every row).
///
/// DB-less / in-memory mode keeps the historical dev convention (the
/// in-memory quality stores carry no site dimension, so the dev context
/// is the explicit tenant-wide grant): the first-article + self
/// inspection merge is preserved, with the status filter applied to the
/// fetched rows.
async fn export_inspection(
    state: AppState,
    ctx: &RequestContext,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let mut inspection_rows: Vec<serde_json::Value> = Vec::new();
    let mut pdf_data_items: Vec<InspectionData> = Vec::new();

    if let Some(pool) = state.db_pool.as_ref() {
        // ── DB-backed: canonical scoped read (SQL-level filters) ───────
        let rows =
            fetch_scoped_canonical_inspections(pool, ctx, status, id, date_from, date_to).await?;
        for row in rows {
            let part_number = row
                .product_id
                .or(row.work_order_id)
                .map(|u| u.to_string())
                .unwrap_or_default();
            pdf_data_items.push(InspectionData {
                id: row.inspection_number.clone(),
                part_name: row.inspection_number.clone(),
                part_number,
                inspector: row.inspector_id.map(|u| u.to_string()).unwrap_or_default(),
                date: row.created_at.to_rfc3339(),
                measurements: Vec::new(),
                result: row.result.clone(),
            });
            inspection_rows.push(serde_json::json!({
                "id": row.id.to_string(),
                "inspection_number": row.inspection_number,
                "status": row.status,
                "result": row.result,
                "type": row.inspection_type,
            }));
        }
    } else {
        // ── DEV / DB-less: in-memory stores, tenant-wide dev grant ─────
        // First article inspections (paged).
        let tenant_id = ctx.tenant;
        let fai_items = fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            Box::pin(async move {
                let page = svc
                    .list_first_article_inspections(tenant_id, Some(page), Some(EXPORT_PAGE_SIZE))
                    .await?;
                Ok(page.data)
            })
        })
        .await?;

        for fai in &fai_items {
            if let Some(filter_id) = id {
                if fai.id != filter_id {
                    continue;
                }
            }
            if !within_date_range(fai.created_at, date_from, date_to)
                || !inspection_status_matches(&fai.status, status)
            {
                continue;
            }

            let measurements: Vec<(String, f64, f64, String)> = fai
                .characteristics
                .iter()
                .map(|c| {
                    (
                        c.characteristic_number.clone(),
                        c.specification.parse().unwrap_or(0.0),
                        c.result.parse().unwrap_or(0.0),
                        c.is_conforming
                            .map(|v| {
                                if v {
                                    "Pass".to_string()
                                } else {
                                    "Fail".to_string()
                                }
                            })
                            .unwrap_or_else(|| c.result.clone()),
                    )
                })
                .collect();

            pdf_data_items.push(InspectionData {
                id: fai.fai_number.clone(),
                part_name: fai.part_name.clone(),
                part_number: fai.part_number.clone(),
                inspector: fai.inspector_id.map(|u| u.to_string()).unwrap_or_default(),
                date: fai.created_at.to_rfc3339(),
                measurements: measurements.clone(),
                result: fai.status.clone(),
            });

            inspection_rows.push(serde_json::json!({
                "id": fai.id.to_string(),
                "fai_number": fai.fai_number,
                "part_name": fai.part_name,
                "part_number": fai.part_number,
                "status": fai.status,
                "type": "first_article",
            }));
        }

        // Self-inspections (paged).
        let tenant_id = ctx.tenant;
        let si_items = fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            Box::pin(async move {
                let page = svc
                    .list_self_inspections(tenant_id, Some(page), Some(EXPORT_PAGE_SIZE))
                    .await?;
                Ok(page.data)
            })
        })
        .await?;

        for si in &si_items {
            if let Some(filter_id) = id {
                if si.id != filter_id {
                    continue;
                }
            }
            if !within_date_range(si.created_at, date_from, date_to)
                || !inspection_status_matches(&si.status, status)
            {
                continue;
            }

            let measurements: Vec<(String, f64, f64, String)> = si
                .checks
                .iter()
                .map(|c| {
                    (
                        c.characteristic.clone(),
                        c.specification
                            .as_deref()
                            .and_then(|s| s.parse().ok())
                            .unwrap_or(0.0),
                        c.actual_value
                            .as_deref()
                            .and_then(|s| s.parse().ok())
                            .unwrap_or(0.0),
                        c.result.clone(),
                    )
                })
                .collect();

            pdf_data_items.push(InspectionData {
                id: si.inspection_number.clone(),
                part_name: si.product_id.map(|u| u.to_string()).unwrap_or_default(),
                part_number: si.work_order_id.map(|u| u.to_string()).unwrap_or_default(),
                inspector: si.operator_id.map(|u| u.to_string()).unwrap_or_default(),
                date: si.created_at.to_rfc3339(),
                measurements: measurements.clone(),
                result: si.result.clone().unwrap_or_else(|| si.status.clone()),
            });

            inspection_rows.push(serde_json::json!({
                "id": si.id.to_string(),
                "inspection_number": si.inspection_number,
                "status": si.status,
                "result": si.result,
                "type": "self_inspection",
            }));
        }
    }

    match format {
        "pdf" => {
            let pdf_svc = &state.pdf_service;
            let pdf_bytes: Vec<u8> = pdf_data_items
                .iter()
                .map(|data| pdf_svc.generate_inspection_report(data))
                .collect::<Result<Vec<Vec<u8>>>>()?
                .into_iter()
                .flatten()
                .collect();
            Ok(build_pdf_response(pdf_bytes))
        }
        "xlsx" => {
            let headers: Vec<String> = vec![
                "ID".to_string(),
                "Part Name".to_string(),
                "Part Number".to_string(),
                "Status".to_string(),
                "Type".to_string(),
            ];
            let rows: Vec<Vec<String>> = inspection_rows
                .iter()
                .map(|r| {
                    vec![
                        r["id"].to_string(),
                        r.get("part_name")
                            .or_else(|| r.get("inspection_number"))
                            .map(|v| v.to_string())
                            .unwrap_or_default(),
                        r.get("part_number")
                            .map(|v| v.to_string())
                            .unwrap_or_default(),
                        r["status"].to_string(),
                        r["type"].to_string(),
                    ]
                })
                .collect();
            let sheets = vec![sensei_services::export::excel::SheetData {
                name: "Inspections".to_string(),
                headers,
                rows,
            }];
            let excel_svc = &state.excel_service;
            let data = excel_svc.generate_multi_sheet_xlsx(&sheets)?;
            Ok(build_xlsx_response(data))
        }
        _ => {
            let excel_svc = &state.excel_service;
            let csv = excel_svc.generate_csv(&inspection_rows)?;
            Ok(build_csv_response(csv))
        }
    }
}

// ── Display helpers (replace Debug formatting leaks) ──────────────────────

fn nc_severity_str(severity: &sensei_services::quality::NcSeverity) -> &'static str {
    match severity {
        sensei_services::quality::NcSeverity::Low => "low",
        sensei_services::quality::NcSeverity::Medium => "medium",
        sensei_services::quality::NcSeverity::High => "high",
        sensei_services::quality::NcSeverity::Critical => "critical",
    }
}

fn capa_status_str(status: &sensei_services::quality::CapaStatusEx) -> &'static str {
    match status {
        sensei_services::quality::CapaStatusEx::Draft => "draft",
        sensei_services::quality::CapaStatusEx::PendingApproval => "pending_approval",
        sensei_services::quality::CapaStatusEx::Open => "open",
        sensei_services::quality::CapaStatusEx::RootCauseAnalysis => "root_cause_analysis",
        sensei_services::quality::CapaStatusEx::ActionPlanning => "action_planning",
        sensei_services::quality::CapaStatusEx::Implementing => "implementing",
        sensei_services::quality::CapaStatusEx::Verification => "verification",
        sensei_services::quality::CapaStatusEx::EffectivenessCheck => "effectiveness_check",
        sensei_services::quality::CapaStatusEx::PendingClosure => "pending_closure",
        sensei_services::quality::CapaStatusEx::Closed => "closed",
        sensei_services::quality::CapaStatusEx::Rejected => "rejected",
        sensei_services::quality::CapaStatusEx::Cancelled => "cancelled",
    }
}

fn audit_status_str(status: &sensei_services::quality::AuditStatus) -> &'static str {
    match status {
        sensei_services::quality::AuditStatus::Planned => "planned",
        sensei_services::quality::AuditStatus::Scheduled => "scheduled",
        sensei_services::quality::AuditStatus::InProgress => "in_progress",
        sensei_services::quality::AuditStatus::Completed => "completed",
        sensei_services::quality::AuditStatus::Closed => "closed",
        sensei_services::quality::AuditStatus::Cancelled => "cancelled",
    }
}

// ── Response builders ────────────────────────────────────────────────────

/// Build an HTTP response for PDF bytes.
fn build_pdf_response(data: Vec<u8>) -> Response {
    (
        StatusCode::OK,
        [(header::CONTENT_TYPE, "application/pdf")],
        data,
    )
        .into_response()
}

/// Build an HTTP response for XLSX bytes.
fn build_xlsx_response(data: Vec<u8>) -> Response {
    (
        StatusCode::OK,
        [(
            header::CONTENT_TYPE,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )],
        data,
    )
        .into_response()
}

/// Build an HTTP response for CSV text.
fn build_csv_response(data: String) -> Response {
    (
        StatusCode::OK,
        [(header::CONTENT_TYPE, "text/csv; charset=utf-8")],
        data,
    )
        .into_response()
}

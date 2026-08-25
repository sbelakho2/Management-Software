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
use sensei_core::error::{Result, SenseiError};
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

    let tenant_id = user.tenant_id;

    match entity_type.as_str() {
        "ncr" => {
            export_ncr(
                state,
                tenant_id,
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
                tenant_id,
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
                tenant_id,
                &format,
                params.id,
                params.status.as_deref(),
                date_from,
                date_to,
            )
            .await
        }
        "work-order" => {
            export_work_order(
                state,
                tenant_id,
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
                tenant_id,
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

/// Export NCR(s) in the requested format.
async fn export_ncr(
    state: AppState,
    tenant_id: Uuid,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let ncrs = if let Some(ncr_id) = id {
        let ncr = state.quality_service.get_ncr(tenant_id, ncr_id).await?;
        vec![ncr]
    } else {
        let status_owned = status.map(|s| s.to_string());
        fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            let status = status_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_ncrs(
                        tenant_id,
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

/// Export CAPA(s) in the requested format.
async fn export_capa(
    state: AppState,
    tenant_id: Uuid,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let capas = if let Some(capa_id) = id {
        let capa = state.quality_service.get_capa(tenant_id, capa_id).await?;
        vec![capa]
    } else {
        let status_owned = status.map(|s| s.to_string());
        fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            let status = status_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_capas(
                        tenant_id,
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

/// Export Audit(s) in the requested format.
async fn export_audit(
    state: AppState,
    tenant_id: Uuid,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let audits = if let Some(audit_id) = id {
        let audit = state.quality_service.get_audit(tenant_id, audit_id).await?;
        vec![audit]
    } else {
        let status_owned = status.map(|s| s.to_string());
        fetch_all_pages(|page| {
            let svc = state.quality_service.clone();
            let status = status_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_audits(
                        tenant_id,
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
async fn export_work_order(
    state: AppState,
    tenant_id: Uuid,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    let orders = if let Some(wo_id) = id {
        let wo = state
            .production_service
            .get_work_order(tenant_id, wo_id)
            .await?;
        vec![wo]
    } else {
        let status_owned = status.map(|s| s.to_string());
        fetch_all_pages(|page| {
            let svc = state.production_service.clone();
            let status = status_owned.clone();
            Box::pin(async move {
                let page = svc
                    .list_work_orders(
                        tenant_id,
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

/// Export Inspection(s) in the requested format.
///
/// Queries the quality service for first article and self-inspections,
/// then maps the real data to the export format.
async fn export_inspection(
    state: AppState,
    tenant_id: Uuid,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
    date_from: Option<DateTime<Utc>>,
    date_to: Option<DateTime<Utc>>,
) -> Result<Response> {
    // Collect inspections from the quality service.
    // We gather both first article inspections and self-inspections.
    let mut inspection_rows: Vec<serde_json::Value> = Vec::new();
    let mut pdf_data_items: Vec<InspectionData> = Vec::new();

    // Fetch first article inspections (paged)
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
        // If a specific ID was requested, filter to that inspection only
        if let Some(filter_id) = id {
            if fai.id != filter_id {
                continue;
            }
        }
        if !within_date_range(fai.created_at, date_from, date_to) {
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

    // Fetch self-inspections (paged)
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
        if !within_date_range(si.created_at, date_from, date_to) {
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

    let _ = status;

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

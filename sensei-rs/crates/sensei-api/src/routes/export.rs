//! Export route handler for generating PDF, XLSX, and CSV reports.
//!
//! # Endpoint
//!
//! `GET /api/v1/export/{entity_type}?format=pdf|csv|xlsx&id=...&tenant_id=...`
//!
//! Supported entity types: `ncr`, `capa`, `audit`, `work-order`, `inspection`.

use axum::{
    extract::{Path, Query, State},
    http::{header, StatusCode},
    response::{IntoResponse, Response},
};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::export::pdf::{AuditData, CapaData, InspectionData, NcrData, WorkOrderData};
use uuid::Uuid;

use crate::state::AppState;

/// Query parameters for export requests.
#[derive(Debug, Deserialize)]
pub struct ExportParams {
    /// Output format: "pdf", "csv", or "xlsx".
    pub format: String,
    /// Optional entity ID (fetches single entity).
    pub id: Option<Uuid>,
    /// Tenant ID for multi-tenant isolation.
    pub tenant_id: Uuid,
    /// Optional status filter.
    pub status: Option<String>,
    /// Optional date range start.
    pub date_from: Option<String>,
    /// Optional date range end.
    pub date_to: Option<String>,
}

/// Export an entity as PDF, CSV, or XLSX.
///
/// Fetches data from the appropriate domain service (quality, production, etc.)
/// and generates the requested output format.
pub async fn export_entity(
    _user: AuthenticatedUser,
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

    let tenant_id = params.tenant_id;

    match entity_type.as_str() {
        "ncr" => export_ncr(state, tenant_id, &format, params.id, params.status.as_deref()).await,
        "capa" => {
            export_capa(state, tenant_id, &format, params.id, params.status.as_deref()).await
        }
        "audit" => {
            export_audit(state, tenant_id, &format, params.id, params.status.as_deref()).await
        }
        "work-order" => {
            export_work_order(
                state,
                tenant_id,
                &format,
                params.id,
                params.status.as_deref(),
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
            )
            .await
        }
        other => Err(SenseiError::NotFound(format!(
            "Unknown entity type: '{other}'. Supported: ncr, capa, audit, work-order, inspection"
        ))),
    }
}

// ── Entity-specific export logic ─────────────────────────────────────────

/// Export NCR(s) in the requested format.
async fn export_ncr(
    state: AppState,
    tenant_id: Uuid,
    format: &str,
    id: Option<Uuid>,
    status: Option<&str>,
) -> Result<Response> {
    let ncrs = if let Some(ncr_id) = id {
        let ncr = state
            .quality_service
            .get_ncr(tenant_id, ncr_id)
            .await?;
        vec![ncr]
    } else {
        let page = state
            .quality_service
            .list_ncrs(tenant_id, status, None, None, Some(1), Some(1000))
            .await?;
        page.data
    };

    match format {
        "pdf" => {
            let pdf_data = ncrs
                .into_iter()
                .map(|ncr| {
                    let pdf_svc = &state.pdf_service;
                    let data = NcrData {
                        id: ncr.id.to_string(),
                        title: ncr.title,
                        description: ncr.description,
                        status: format!("{:?}", ncr.nc_type),
                        severity: format!("{:?}", ncr.severity),
                        created_by: ncr
                            .detected_by
                            .map(|u| u.to_string())
                            .unwrap_or_default(),
                        created_at: ncr.created_at.to_rfc3339(),
                        department: ncr.department.unwrap_or_default(),
                        corrective_actions: vec![],
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
) -> Result<Response> {
    let capas = if let Some(capa_id) = id {
        let capa = state.quality_service.get_capa(tenant_id, capa_id).await?;
        vec![capa]
    } else {
        let page = state
            .quality_service
            .list_capas(tenant_id, status, None, Some(1), Some(1000))
            .await?;
        page.data
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
                        status: format!("{:?}", capa.status),
                        deadline: capa
                            .due_date
                            .map(|d| d.to_rfc3339())
                            .unwrap_or_default(),
                        assigned_to: capa
                            .owner_id
                            .map(|u| u.to_string())
                            .unwrap_or_default(),
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
) -> Result<Response> {
    let audits = if let Some(audit_id) = id {
        let audit = state.quality_service.get_audit(tenant_id, audit_id).await?;
        vec![audit]
    } else {
        let page = state
            .quality_service
            .list_audits(tenant_id, status, None, Some(1), Some(1000))
            .await?;
        page.data
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

                    let data = AuditData {
                        id: audit.id.to_string(),
                        title: audit.title,
                        auditor: audit
                            .auditor_id
                            .map(|u| u.to_string())
                            .unwrap_or_default(),
                        auditee: String::new(),
                        date: audit
                            .scheduled_date
                            .map(|d| d.to_rfc3339())
                            .unwrap_or_default(),
                        scope: audit.scope,
                        findings,
                        score: 0.0,
                        status: format!("{:?}", audit.status),
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
) -> Result<Response> {
    let orders = if let Some(wo_id) = id {
        let wo = state
            .production_service
            .get_work_order(tenant_id, wo_id)
            .await?;
        vec![wo]
    } else {
        let page = state
            .production_service
            .list_work_orders(tenant_id, status, None, Some(1), Some(1000))
            .await?;
        page.data
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
                            .map(|d| d.to_rfc3339())
                            .unwrap_or_default(),
                        work_center: wo
                            .work_center_id
                            .map(|u| u.to_string())
                            .unwrap_or_default(),
                        estimated_hours: 0.0,
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
    _status: Option<&str>,
) -> Result<Response> {
    // Collect inspections from the quality service.
    // We gather both first article inspections and self-inspections.
    let mut inspection_rows: Vec<serde_json::Value> = Vec::new();
    let mut pdf_data_items: Vec<InspectionData> = Vec::new();

    // Fetch first article inspections
    let fai_page = state
        .quality_service
        .list_first_article_inspections(tenant_id, Some(1), Some(10_000))
        .await?;

    for fai in &fai_page.data {
        // If a specific ID was requested, filter to that inspection only
        if let Some(filter_id) = id {
            if fai.id != filter_id {
                continue;
            }
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
                        .map(|v| if v { "Pass".to_string() } else { "Fail".to_string() })
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

    // Fetch self-inspections
    let si_page = state
        .quality_service
        .list_self_inspections(tenant_id, Some(1), Some(10_000))
        .await?;

    for si in &si_page.data {
        if let Some(filter_id) = id {
            if si.id != filter_id {
                continue;
            }
        }

        let measurements: Vec<(String, f64, f64, String)> = si
            .checks
            .iter()
            .map(|c| {
                (
                    c.characteristic.clone(),
                    c.specification.as_deref().and_then(|s| s.parse().ok()).unwrap_or(0.0),
                    c.actual_value.as_deref().and_then(|s| s.parse().ok()).unwrap_or(0.0),
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

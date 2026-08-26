//! Quality Management route handlers.
//!
//! Provides endpoints for NCR (Non-Conformance Reports), CAPA workflow,
//! inspections (AQL, FAI, self-inspection), audits, supplier quality,
//! NPI risk management, MSA/SPC studies, and stage-gate reviews.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_services::quality::{
    Audit, AuditFinding, CapaExtended, CapaPriority, CapaType, ControlPlan, CustomerComplaint,
    EightDReport, FirstArticleInspection, Gauge, ManagementReview, MsaStudy, NcSeverity, NcType,
    NonConformance, NpiProject, NpiRisk, PaginatedResponse, PfmeaLite, ProcessCapabilityStudy,
    QmsDocument, RootCauseAnalysis, Scar, SelfInspection, SupplierScorecard,
};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

/// Simple pagination-only query parameters for list endpoints without filters.
#[derive(Debug, Deserialize)]
pub struct ListPaginationParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing NCRs.
#[derive(Debug, Deserialize)]
pub struct ListNcrsParams {
    pub status: Option<String>,
    pub severity: Option<String>,
    pub source: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing CAPAs.
#[derive(Debug, Deserialize)]
pub struct ListCapasParams {
    pub status: Option<String>,
    pub nc_type: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing audits.
#[derive(Debug, Deserialize)]
pub struct ListAuditsParams {
    pub status: Option<String>,
    pub audit_type: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing supplier scorecards.
#[derive(Debug, Deserialize)]
pub struct ListSupplierScorecardsParams {
    pub supplier_id: Option<Uuid>,
    pub period: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing NPI projects.
#[derive(Debug, Deserialize)]
pub struct ListNpiProjectsParams {
    pub stage: Option<String>,
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// List all NCRs with optional filters.
pub async fn list_ncrs(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): axum::extract::Query<ListNcrsParams>,
) -> Result<Json<PaginatedResponse<NonConformance>>> {
    user.require_permission("quality:ncr:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_ncrs(
            tenant_id,
            params.status.as_deref(),
            params.severity.as_deref(),
            params.source.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(result))
}

/// Get a specific NCR by ID.
pub async fn get_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): axum::extract::Path<Uuid>,
) -> Result<Json<NonConformance>> {
    user.require_permission("quality:ncr:read")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.get_ncr(tenant_id, id).await?;
    Ok(Json(result))
}

/// List all CAPAs with optional filters.
pub async fn list_capas(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): axum::extract::Query<ListCapasParams>,
) -> Result<Json<PaginatedResponse<CapaExtended>>> {
    user.require_permission("quality:capa:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_capas(
            tenant_id,
            params.status.as_deref(),
            params.nc_type.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(result))
}

/// Get a specific CAPA by ID.
pub async fn get_capa(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): axum::extract::Path<Uuid>,
) -> Result<Json<CapaExtended>> {
    user.require_permission("quality:capa:read")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.get_capa(tenant_id, id).await?;
    Ok(Json(result))
}

/// List all audits with optional filters.
pub async fn list_audits(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): axum::extract::Query<ListAuditsParams>,
) -> Result<Json<PaginatedResponse<Audit>>> {
    user.require_permission("quality:audit:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_audits(
            tenant_id,
            params.status.as_deref(),
            params.audit_type.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(result))
}

/// Get a specific audit by ID.
pub async fn get_audit(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): axum::extract::Path<Uuid>,
) -> Result<Json<Audit>> {
    user.require_permission("quality:audit:read")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.get_audit(tenant_id, id).await?;
    Ok(Json(result))
}

/// List audit findings for a specific audit.
pub async fn list_audit_findings(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(audit_id): axum::extract::Path<Uuid>,
) -> Result<Json<Vec<AuditFinding>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_audit_findings(tenant_id, audit_id)
        .await?;
    Ok(Json(result))
}

/// List supplier scorecards.
pub async fn list_supplier_scorecards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): axum::extract::Query<ListSupplierScorecardsParams>,
) -> Result<Json<PaginatedResponse<SupplierScorecard>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_supplier_scorecards(
            tenant_id,
            params.supplier_id,
            params.period.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(result))
}

/// List SCARs (Supplier Corrective Action Requests).
pub async fn list_scars(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<Scar>>> {
    user.require_permission("quality:scar:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_scars(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List documents.
pub async fn list_documents(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<QmsDocument>>> {
    user.require_permission("quality:document:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_documents(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List FAI (First Article Inspection) records.
pub async fn list_first_article_inspections(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<FirstArticleInspection>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_first_article_inspections(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List self-inspection records.
pub async fn list_self_inspections(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<SelfInspection>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_self_inspections(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List MSA (Measurement Systems Analysis) studies.
pub async fn list_msa_studies(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<MsaStudy>>> {
    user.require_permission("quality:msa:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_msa_studies(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List process capability studies.
pub async fn list_process_capability_studies(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<ProcessCapabilityStudy>>> {
    user.require_permission("quality:spc:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_process_capability_studies(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List control plans.
pub async fn list_control_plans(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<ControlPlan>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_control_plans(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List PFMEA (Process Failure Mode Effects Analysis) records.
pub async fn list_pfmeas(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<PfmeaLite>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_pfmeas(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List NPI (New Product Introduction) projects.
pub async fn list_npi_projects(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): axum::extract::Query<ListNpiProjectsParams>,
) -> Result<Json<PaginatedResponse<NpiProject>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_npi_projects(
            tenant_id,
            params.stage.as_deref(),
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(result))
}

/// List NPI risks for a specific project.
pub async fn list_npi_risks(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(project_id): axum::extract::Path<Uuid>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<NpiRisk>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_npi_risks(tenant_id, project_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List gauges and measurement equipment.
pub async fn list_gauges(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<Gauge>>> {
    user.require_permission("quality:gauge:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_gauges(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List customer complaints.
pub async fn list_complaints(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<CustomerComplaint>>> {
    user.require_permission("quality:complaint:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_complaints(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

/// List 8D reports.
pub async fn list_eight_d_reports(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<EightDReport>>> {
    user.require_permission("quality:8d:read")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_eight_d_reports(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Getters for list-only entities (tenant-scoped; 404 on missing/foreign)
// ═══════════════════════════════════════════════════════════════════════════════

/// Get a specific SCAR by ID.
pub async fn get_scar(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Scar>> {
    user.require_permission("quality:scar:read")?;

    let result = state.quality_service.get_scar(user.tenant_id, id).await?;
    Ok(Json(result))
}

/// Get a specific QMS document by ID.
pub async fn get_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<QmsDocument>> {
    user.require_permission("quality:document:read")?;

    let result = state
        .quality_service
        .get_document(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific first article inspection by ID.
pub async fn get_first_article_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<FirstArticleInspection>> {
    user.require_permission("quality:fai:read")?;

    let result = state
        .quality_service
        .get_first_article_inspection(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific self-inspection by ID.
pub async fn get_self_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<SelfInspection>> {
    user.require_permission("quality:inspection:self")?;

    let result = state
        .quality_service
        .get_self_inspection(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific MSA study by ID.
pub async fn get_msa_study(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<MsaStudy>> {
    user.require_permission("quality:msa:read")?;

    let result = state
        .quality_service
        .get_msa_study(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific process capability study by ID.
pub async fn get_process_capability_study(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ProcessCapabilityStudy>> {
    user.require_permission("quality:spc:read")?;

    let result = state
        .quality_service
        .get_process_capability_study(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific control plan by ID.
pub async fn get_control_plan(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ControlPlan>> {
    user.require_permission("quality:control-plan:read")?;

    let result = state
        .quality_service
        .get_control_plan(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific PFMEA by ID.
pub async fn get_pfmea(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<PfmeaLite>> {
    user.require_permission("quality:pfmea:read")?;

    let result = state.quality_service.get_pfmea(user.tenant_id, id).await?;
    Ok(Json(result))
}

/// Get a specific gauge by ID.
pub async fn get_gauge(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Gauge>> {
    user.require_permission("quality:gauge:read")?;

    let result = state.quality_service.get_gauge(user.tenant_id, id).await?;
    Ok(Json(result))
}

/// Get a specific customer complaint by ID.
pub async fn get_complaint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<CustomerComplaint>> {
    user.require_permission("quality:complaint:read")?;

    let result = state
        .quality_service
        .get_complaint(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific 8D report by ID.
pub async fn get_eight_d_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<EightDReport>> {
    user.require_permission("quality:8d:read")?;

    let result = state
        .quality_service
        .get_eight_d_report(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

/// Get a specific management review by ID.
pub async fn get_management_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ManagementReview>> {
    user.require_permission("quality:review:read")?;

    let result = state
        .quality_service
        .get_management_review(user.tenant_id, id)
        .await?;
    Ok(Json(result))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Request Body Types
// ═══════════════════════════════════════════════════════════════════════════════

/// Request body for creating an NCR.
#[derive(Debug, Deserialize)]
pub struct CreateNcrRequest {
    pub title: String,
    pub description: String,
    pub nc_type: NcType,
    pub severity: NcSeverity,
    pub product_id: Option<Uuid>,
    pub process_id: Option<Uuid>,
    pub defect_code: Option<String>,
    pub detected_by: Option<Uuid>,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_recurrence: bool,
}

/// Request body for creating a CAPA.
#[derive(Debug, Deserialize)]
pub struct CreateCapaRequest {
    pub title: String,
    pub description: String,
    pub nc_ids: Vec<Uuid>,
    pub capa_type: CapaType,
    pub priority: CapaPriority,
    pub owner_id: Option<Uuid>,
    pub due_date: Option<DateTime<Utc>>,
}

/// Request body for NCR disposition.
#[derive(Debug, Deserialize)]
pub struct DispositionRequest {
    pub disposition: String,
}

// ═══════════════════════════════════════════════════════════════════════════════
// NCR Handlers (Create / Update / Delete / Lifecycle)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a new NCR.
pub async fn create_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(body): Json<CreateNcrRequest>,
) -> Result<Json<NonConformance>> {
    user.require_permission("quality:ncr:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_ncr(
            tenant_id,
            body.title,
            body.description,
            body.nc_type,
            body.severity,
            body.product_id,
            body.process_id,
            body.defect_code,
            body.detected_by,
            body.department,
            body.location,
            body.is_recurrence,
        )
        .await?;
    Ok(Json(result))
}

/// Update an existing NCR.
pub async fn update_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(ncr): Json<NonConformance>,
) -> Result<Json<NonConformance>> {
    user.require_permission("quality:ncr:update")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.update_ncr(tenant_id, id, ncr).await?;
    Ok(Json(result))
}

/// Delete an NCR.
pub async fn delete_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("quality:ncr:delete")?;

    let tenant_id = user.tenant_id;
    state.quality_service.delete_ncr(tenant_id, id).await?;
    Ok(Json(()))
}

/// Investigate an NCR (add root cause analysis).
pub async fn investigate_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(rca): Json<RootCauseAnalysis>,
) -> Result<Json<NonConformance>> {
    user.require_permission("quality:ncr:update")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .investigate_ncr(tenant_id, id, rca)
        .await?;
    Ok(Json(result))
}

/// Add disposition to an NCR.
pub async fn disposition_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(body): Json<DispositionRequest>,
) -> Result<Json<NonConformance>> {
    user.require_permission("quality:ncr:approve")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .disposition_ncr(tenant_id, id, body.disposition)
        .await?;
    Ok(Json(result))
}

/// Close an NCR.
pub async fn close_ncr(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<NonConformance>> {
    user.require_permission("quality:ncr:approve")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.close_ncr(tenant_id, id).await?;
    Ok(Json(result))
}

// ═══════════════════════════════════════════════════════════════════════════════
// CAPA Handlers (Create / Update / Delete / Lifecycle)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a new CAPA.
pub async fn create_capa(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(body): Json<CreateCapaRequest>,
) -> Result<Json<CapaExtended>> {
    user.require_permission("quality:capa:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_capa(
            tenant_id,
            body.title,
            body.description,
            body.nc_ids,
            body.capa_type,
            body.priority,
            body.owner_id,
            body.due_date,
        )
        .await?;
    Ok(Json(result))
}

/// Update an existing CAPA.
pub async fn update_capa(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(capa): Json<CapaExtended>,
) -> Result<Json<CapaExtended>> {
    user.require_permission("quality:capa:update")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_capa(tenant_id, id, capa)
        .await?;
    Ok(Json(result))
}

/// Delete a CAPA.
pub async fn delete_capa(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("quality:capa:update")?;

    let tenant_id = user.tenant_id;
    state.quality_service.delete_capa(tenant_id, id).await?;
    Ok(Json(()))
}

/// Verify a CAPA's effectiveness.
pub async fn verify_capa(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<CapaExtended>> {
    user.require_permission("quality:capa:close")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.verify_capa(tenant_id, id).await?;
    Ok(Json(result))
}

/// Close a CAPA.
pub async fn close_capa(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<CapaExtended>> {
    user.require_permission("quality:capa:close")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.close_capa(tenant_id, id).await?;
    Ok(Json(result))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Inspection Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a first article inspection.
pub async fn create_first_article_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(fai): Json<FirstArticleInspection>,
) -> Result<Json<FirstArticleInspection>> {
    user.require_permission("quality:fai:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_first_article_inspection(tenant_id, fai)
        .await?;
    Ok(Json(result))
}

/// Update a first article inspection.
pub async fn update_first_article_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(fai): Json<FirstArticleInspection>,
) -> Result<Json<FirstArticleInspection>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_first_article_inspection(tenant_id, id, fai)
        .await?;
    Ok(Json(result))
}

/// Delete a first article inspection.
pub async fn delete_first_article_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_first_article_inspection(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Create a self-inspection.
pub async fn create_self_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(inspection): Json<SelfInspection>,
) -> Result<Json<SelfInspection>> {
    user.require_permission("quality:inspection:self")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_self_inspection(tenant_id, inspection)
        .await?;
    Ok(Json(result))
}

/// Update a self-inspection.
pub async fn update_self_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(inspection): Json<SelfInspection>,
) -> Result<Json<SelfInspection>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_self_inspection(tenant_id, id, inspection)
        .await?;
    Ok(Json(result))
}

/// Delete a self-inspection.
pub async fn delete_self_inspection(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_self_inspection(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Audit Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a new audit.
pub async fn create_audit(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(audit): Json<Audit>,
) -> Result<Json<Audit>> {
    user.require_permission("quality:audit:create")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.create_audit(tenant_id, audit).await?;
    Ok(Json(result))
}

/// Update an audit.
pub async fn update_audit(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(audit): Json<Audit>,
) -> Result<Json<Audit>> {
    user.require_permission("quality:audit:update")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_audit(tenant_id, id, audit)
        .await?;
    Ok(Json(result))
}

/// Delete an audit.
pub async fn delete_audit(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("quality:audit:delete")?;

    let tenant_id = user.tenant_id;
    state.quality_service.delete_audit(tenant_id, id).await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Supplier Quality Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a supplier evaluation (scorecard).
pub async fn create_supplier_evaluation(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(scorecard): Json<SupplierScorecard>,
) -> Result<Json<SupplierScorecard>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_supplier_evaluation(tenant_id, scorecard)
        .await?;
    Ok(Json(result))
}

/// Update a supplier scorecard.
pub async fn update_supplier_scorecard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(scorecard): Json<SupplierScorecard>,
) -> Result<Json<SupplierScorecard>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_supplier_scorecard(tenant_id, id, scorecard)
        .await?;
    Ok(Json(result))
}

/// Delete a supplier scorecard.
pub async fn delete_supplier_scorecard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_supplier_scorecard(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Create a SCAR.
pub async fn create_scar(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(scar): Json<Scar>,
) -> Result<Json<Scar>> {
    user.require_permission("quality:scar:create")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.create_scar(tenant_id, scar).await?;
    Ok(Json(result))
}

/// Update a SCAR.
pub async fn update_scar(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(scar): Json<Scar>,
) -> Result<Json<Scar>> {
    user.require_permission("quality:scar:update")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_scar(tenant_id, id, scar)
        .await?;
    Ok(Json(result))
}

/// Delete a SCAR.
pub async fn delete_scar(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("quality:scar:delete")?;

    let tenant_id = user.tenant_id;
    state.quality_service.delete_scar(tenant_id, id).await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Document Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a QMS document.
pub async fn create_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(doc): Json<QmsDocument>,
) -> Result<Json<QmsDocument>> {
    user.require_permission("quality:document:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_document(tenant_id, doc)
        .await?;
    Ok(Json(result))
}

/// Update a QMS document.
pub async fn update_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(doc): Json<QmsDocument>,
) -> Result<Json<QmsDocument>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_document(tenant_id, id, doc)
        .await?;
    Ok(Json(result))
}

/// Delete a QMS document.
pub async fn delete_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state.quality_service.delete_document(tenant_id, id).await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// MSA Study Handlers (Create / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create an MSA study.
pub async fn create_msa_study(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(study): Json<MsaStudy>,
) -> Result<Json<MsaStudy>> {
    user.require_permission("quality:msa:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_msa_study(tenant_id, study)
        .await?;
    Ok(Json(result))
}

/// Delete an MSA study.
pub async fn delete_msa_study(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_msa_study(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Process Capability Study Handlers (Create / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a process capability study.
pub async fn create_process_capability_study(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(study): Json<ProcessCapabilityStudy>,
) -> Result<Json<ProcessCapabilityStudy>> {
    user.require_permission("quality:spc:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_process_capability_study(tenant_id, study)
        .await?;
    Ok(Json(result))
}

/// Delete a process capability study.
pub async fn delete_process_capability_study(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_process_capability_study(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Control Plan Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a control plan.
pub async fn create_control_plan(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(cp): Json<ControlPlan>,
) -> Result<Json<ControlPlan>> {
    user.require_permission("quality:control-plan:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_control_plan(tenant_id, cp)
        .await?;
    Ok(Json(result))
}

/// Update a control plan.
pub async fn update_control_plan(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(cp): Json<ControlPlan>,
) -> Result<Json<ControlPlan>> {
    user.require_permission("quality:control-plan:update")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_control_plan(tenant_id, id, cp)
        .await?;
    Ok(Json(result))
}

/// Delete a control plan.
pub async fn delete_control_plan(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_control_plan(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// PFMEA Handlers (Create / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a PFMEA.
pub async fn create_pfmea(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(pfmea): Json<PfmeaLite>,
) -> Result<Json<PfmeaLite>> {
    user.require_permission("quality:pfmea:create")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.create_pfmea(tenant_id, pfmea).await?;
    Ok(Json(result))
}

/// Delete a PFMEA.
pub async fn delete_pfmea(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state.quality_service.delete_pfmea(tenant_id, id).await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// NPI Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create an NPI project.
pub async fn create_npi_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(project): Json<NpiProject>,
) -> Result<Json<NpiProject>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_npi_project(tenant_id, project)
        .await?;
    Ok(Json(result))
}

/// Update an NPI project.
pub async fn update_npi_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(project): Json<NpiProject>,
) -> Result<Json<NpiProject>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_npi_project(tenant_id, id, project)
        .await?;
    Ok(Json(result))
}

/// Delete an NPI project.
pub async fn delete_npi_project(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_npi_project(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Gauge Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a gauge.
pub async fn create_gauge(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(gauge): Json<Gauge>,
) -> Result<Json<Gauge>> {
    user.require_permission("quality:gauge:create")?;

    let tenant_id = user.tenant_id;
    let result = state.quality_service.create_gauge(tenant_id, gauge).await?;
    Ok(Json(result))
}

/// Update a gauge.
pub async fn update_gauge(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(gauge): Json<Gauge>,
) -> Result<Json<Gauge>> {
    user.require_permission("quality:gauge:update")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_gauge(tenant_id, id, gauge)
        .await?;
    Ok(Json(result))
}

/// Delete a gauge.
pub async fn delete_gauge(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state.quality_service.delete_gauge(tenant_id, id).await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Complaint Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a customer complaint.
pub async fn create_complaint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(complaint): Json<CustomerComplaint>,
) -> Result<Json<CustomerComplaint>> {
    user.require_permission("quality:complaint:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_complaint(tenant_id, complaint)
        .await?;
    Ok(Json(result))
}

/// Update a customer complaint.
pub async fn update_complaint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(complaint): Json<CustomerComplaint>,
) -> Result<Json<CustomerComplaint>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_complaint(tenant_id, id, complaint)
        .await?;
    Ok(Json(result))
}

/// Delete a customer complaint.
pub async fn delete_complaint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_complaint(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 8D Report Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create an 8D report.
pub async fn create_eight_d_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(report): Json<EightDReport>,
) -> Result<Json<EightDReport>> {
    user.require_permission("quality:8d:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_eight_d_report(tenant_id, report)
        .await?;
    Ok(Json(result))
}

/// Update an 8D report.
pub async fn update_eight_d_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(report): Json<EightDReport>,
) -> Result<Json<EightDReport>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_eight_d_report(tenant_id, id, report)
        .await?;
    Ok(Json(result))
}

/// Delete an 8D report.
pub async fn delete_eight_d_report(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_eight_d_report(tenant_id, id)
        .await?;
    Ok(Json(()))
}

// ═══════════════════════════════════════════════════════════════════════════════
// Management Review Handlers (Create / Update / Delete)
// ═══════════════════════════════════════════════════════════════════════════════

/// Create a management review.
pub async fn create_management_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(review): Json<ManagementReview>,
) -> Result<Json<ManagementReview>> {
    user.require_permission("quality:review:create")?;

    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .create_management_review(tenant_id, review)
        .await?;
    Ok(Json(result))
}

/// Update a management review.
pub async fn update_management_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(review): Json<ManagementReview>,
) -> Result<Json<ManagementReview>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .update_management_review(tenant_id, id, review)
        .await?;
    Ok(Json(result))
}

/// Delete a management review.
pub async fn delete_management_review(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    state
        .quality_service
        .delete_management_review(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// List management reviews.
pub async fn list_management_reviews(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(pagination): Query<ListPaginationParams>,
) -> Result<Json<PaginatedResponse<ManagementReview>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .quality_service
        .list_management_reviews(tenant_id, pagination.page, pagination.per_page)
        .await?;
    Ok(Json(result))
}

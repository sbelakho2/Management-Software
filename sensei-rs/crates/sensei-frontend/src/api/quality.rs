//! Quality management API endpoints.
//!
//! NCR (Non-Conformance Reports), CAPA (Corrective & Preventive Actions),
//! Inspections, Audits, Supplier evaluations, NPI Risk, MSA, SPC, Stage Gates.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NcrDto {
    pub id: String,
    pub tenant_id: String,
    pub title: String,
    pub description: String,
    pub severity: String,
    pub status: String,
    pub source: String,
    pub created_by: String,
    pub assigned_to: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateNcrRequest {
    pub title: String,
    pub description: String,
    pub severity: String,
    pub source: String,
    pub assigned_to: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapaDto {
    pub id: String,
    pub tenant_id: String,
    pub ncr_id: Option<String>,
    pub root_cause: String,
    pub action_plan: String,
    pub status: String,
    pub due_date: Option<String>,
    pub assigned_to: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateCapaRequest {
    pub ncr_id: Option<String>,
    pub root_cause: String,
    pub action_plan: String,
    pub due_date: Option<String>,
    pub assigned_to: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InspectionDto {
    pub id: String,
    pub tenant_id: String,
    pub title: String,
    pub inspection_type: String,
    pub result: String,
    pub inspector: String,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditDto {
    pub id: String,
    pub tenant_id: String,
    pub audit_type: String,
    pub scope: String,
    pub findings: serde_json::Value,
    pub score: Option<f64>,
    pub status: String,
    pub conducted_by: String,
    pub scheduled_date: Option<String>,
    pub completed_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupplierEvalDto {
    pub id: String,
    pub tenant_id: String,
    pub supplier_name: String,
    pub score: f64,
    pub tier: String,
    pub evaluated_by: String,
    pub evaluated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiRiskDto {
    pub id: String,
    pub tenant_id: String,
    pub project_name: String,
    pub risk_category: String,
    pub likelihood: i32,
    pub impact: i32,
    pub risk_score: i32,
    pub mitigation: Option<String>,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MsaDto {
    pub id: String,
    pub tenant_id: String,
    pub gage_name: String,
    pub msa_type: String,
    pub result: String,
    pub performed_by: String,
    pub performed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpcDataDto {
    pub id: String,
    pub tenant_id: String,
    pub parameter: String,
    pub value: f64,
    pub upper_spec: f64,
    pub lower_spec: f64,
    pub recorded_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StageGateDto {
    pub id: String,
    pub tenant_id: String,
    pub gate_name: String,
    pub phase: String,
    pub status: String,
    pub criteria: serde_json::Value,
    pub reviewed_by: Option<String>,
    pub reviewed_at: Option<String>,
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/// Quality management API group.
pub struct QualityApi;

impl QualityApi {
    // ---- NCR ----
    pub async fn list_ncrs(client: &ApiClient) -> Result<Vec<NcrDto>, ApiError> {
        client.get("/api/v1/quality/ncr").await
    }

    pub async fn get_ncr(client: &ApiClient, id: &str) -> Result<NcrDto, ApiError> {
        client.get(&format!("/api/v1/quality/ncr/{}", id)).await
    }

    pub async fn create_ncr(client: &ApiClient, req: &CreateNcrRequest) -> Result<NcrDto, ApiError> {
        client.post("/api/v1/quality/ncr", req).await
    }

    // ---- CAPA ----
    pub async fn list_capas(client: &ApiClient) -> Result<Vec<CapaDto>, ApiError> {
        client.get("/api/v1/quality/capa").await
    }

    pub async fn get_capa(client: &ApiClient, id: &str) -> Result<CapaDto, ApiError> {
        client.get(&format!("/api/v1/quality/capa/{}", id)).await
    }

    pub async fn create_capa(client: &ApiClient, req: &CreateCapaRequest) -> Result<CapaDto, ApiError> {
        client.post("/api/v1/quality/capa", req).await
    }

    // ---- Inspections ----
    pub async fn list_inspections(client: &ApiClient) -> Result<Vec<InspectionDto>, ApiError> {
        client.get("/api/v1/quality/inspections").await
    }

    pub async fn get_inspection(client: &ApiClient, id: &str) -> Result<InspectionDto, ApiError> {
        client.get(&format!("/api/v1/quality/inspections/{}", id)).await
    }

    // ---- Audits ----
    pub async fn list_audits(client: &ApiClient) -> Result<Vec<AuditDto>, ApiError> {
        client.get("/api/v1/quality/audits").await
    }

    pub async fn get_audit(client: &ApiClient, id: &str) -> Result<AuditDto, ApiError> {
        client.get(&format!("/api/v1/quality/audits/{}", id)).await
    }

    // ---- Supplier Evaluations ----
    pub async fn list_supplier_evals(client: &ApiClient) -> Result<Vec<SupplierEvalDto>, ApiError> {
        client.get("/api/v1/quality/suppliers").await
    }

    // ---- NPI Risk ----
    pub async fn list_npi_risks(client: &ApiClient) -> Result<Vec<NpiRiskDto>, ApiError> {
        client.get("/api/v1/quality/npi-risks").await
    }

    // ---- MSA ----
    pub async fn list_msa(client: &ApiClient) -> Result<Vec<MsaDto>, ApiError> {
        client.get("/api/v1/quality/msa").await
    }

    // ---- SPC ----
    pub async fn list_spc_data(client: &ApiClient) -> Result<Vec<SpcDataDto>, ApiError> {
        client.get("/api/v1/quality/spc").await
    }

    // ---- Stage Gates ----
    pub async fn list_stage_gates(client: &ApiClient) -> Result<Vec<StageGateDto>, ApiError> {
        client.get("/api/v1/quality/stage-gates").await
    }
}

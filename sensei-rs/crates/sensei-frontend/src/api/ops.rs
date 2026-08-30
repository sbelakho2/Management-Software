//! Operations / Continuous Improvement API endpoints.
//!
//! Andon, Projects, A3 Reports, Risks.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndonDto {
    pub id: String,
    pub tenant_id: String,
    pub andon_number: String,
    pub title: String,
    pub description: Option<String>,
    pub severity: String,
    pub status: String,
    pub location: Option<String>,
    pub raised_by: String,
    pub acknowledged_by: Option<String>,
    pub response_time_seconds: Option<i64>,
    pub resolution_time_seconds: Option<i64>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RaiseAndonRequest {
    pub title: String,
    pub description: Option<String>,
    pub severity: String,
    pub location: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectDto {
    pub id: String,
    pub tenant_id: String,
    pub project_number: String,
    pub name: String,
    pub description: Option<String>,
    pub status: String,
    pub priority: String,
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub owner: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateProjectRequest {
    pub name: String,
    pub description: Option<String>,
    pub priority: String,
    pub start_date: Option<String>,
    pub end_date: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A3Dto {
    pub id: String,
    pub tenant_id: String,
    pub a3_number: String,
    pub title: String,
    pub problem_statement: String,
    pub root_cause: Option<String>,
    pub countermeasures: Option<String>,
    pub status: String,
    pub owner: String,
    pub created_at: String,
    pub closed_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateA3Request {
    pub title: String,
    pub problem_statement: String,
    pub root_cause: Option<String>,
    pub countermeasures: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskDto {
    pub id: String,
    pub tenant_id: String,
    pub risk_number: String,
    pub title: String,
    pub description: Option<String>,
    pub likelihood: String,
    pub impact: String,
    pub risk_score: i32,
    pub mitigation: Option<String>,
    pub status: String,
    pub owner: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateRiskRequest {
    pub title: String,
    pub description: Option<String>,
    pub likelihood: String,
    pub impact: String,
    pub mitigation: Option<String>,
}

pub struct OpsApi;

impl OpsApi {
    // ---- Andon ----
    pub async fn list_andons(client: &ApiClient) -> Result<Vec<AndonDto>, ApiError> {
        client.get("/api/v1/ops/andons").await
    }

    pub async fn get_andon(client: &ApiClient, id: &str) -> Result<AndonDto, ApiError> {
        client.get(&format!("/api/v1/ops/andons/{}", id)).await
    }

    pub async fn raise_andon(
        client: &ApiClient,
        req: &RaiseAndonRequest,
    ) -> Result<AndonDto, ApiError> {
        client.post("/api/v1/ops/andons", req).await
    }

    /// The SAFE Andon raise command (item 40): the request carries only
    /// the operator's plain-language inputs; the server derives
    /// actor/tenant/status. The legacy /api/v1/ops/andons full-object
    /// route must NOT be used by clients.
    pub async fn raise_andon_command(
        client: &ApiClient,
        req: &crate::api::andon::RaiseAndonCommandRequest,
    ) -> Result<AndonDto, ApiError> {
        client.post("/api/v1/andon", req).await
    }

    // ---- Projects ----
    pub async fn list_projects(client: &ApiClient) -> Result<Vec<ProjectDto>, ApiError> {
        client.get("/api/v1/ops/projects").await
    }

    pub async fn get_project(client: &ApiClient, id: &str) -> Result<ProjectDto, ApiError> {
        client.get(&format!("/api/v1/ops/projects/{}", id)).await
    }

    pub async fn create_project(
        client: &ApiClient,
        req: &CreateProjectRequest,
    ) -> Result<ProjectDto, ApiError> {
        client.post("/api/v1/ops/projects", req).await
    }

    // ---- A3 ----
    pub async fn list_a3s(client: &ApiClient) -> Result<Vec<A3Dto>, ApiError> {
        client.get("/api/v1/ops/a3s").await
    }

    pub async fn get_a3(client: &ApiClient, id: &str) -> Result<A3Dto, ApiError> {
        client.get(&format!("/api/v1/ops/a3s/{}", id)).await
    }

    pub async fn create_a3(client: &ApiClient, req: &CreateA3Request) -> Result<A3Dto, ApiError> {
        client.post("/api/v1/ops/a3s", req).await
    }

    // ---- Risks ----
    pub async fn list_risks(client: &ApiClient) -> Result<Vec<RiskDto>, ApiError> {
        client.get("/api/v1/ops/risks").await
    }

    pub async fn get_risk(client: &ApiClient, id: &str) -> Result<RiskDto, ApiError> {
        client.get(&format!("/api/v1/ops/risks/{}", id)).await
    }

    pub async fn create_risk(
        client: &ApiClient,
        req: &CreateRiskRequest,
    ) -> Result<RiskDto, ApiError> {
        client.post("/api/v1/ops/risks", req).await
    }
}

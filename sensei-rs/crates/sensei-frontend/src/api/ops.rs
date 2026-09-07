//! Operations / Continuous Improvement API endpoints.
//!
//! Projects, A3 Reports, Risks. Andon has moved OUT of this module
//! (thirty-first audit): the canonical Andon surface lives in
//! [`crate::api::andon`] over `/api/v1/andon` with the shared
//! sensei-contracts types — the legacy `/api/v1/ops/andons` full-object
//! surface and its title/location-style DTOs are gone.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

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

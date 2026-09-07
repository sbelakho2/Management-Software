//! Andon system API endpoints (thirty-first audit).
//!
//! The canonical Andon surface: every type is the shared
//! sensei-contracts definition (`AndonResponse`, `RaiseAndonRequest`) —
//! no DTO lives twice. `OpsApi` carries Projects/A3/Risks only; Andon
//! calls go through [`AndonApi`].

use crate::api::client::{ApiClient, ApiError};
use sensei_contracts::andon::AndonResponse;
use sensei_contracts::pagination::Paginated;
use sensei_contracts::RaiseAndonRequest;

/// Resolve an Andon (resolution text only — the actor is the token).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ResolveAndonData {
    pub resolution: String,
}

/// Update an Andon's operational facts (the canonical update command).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct UpdateAndonData {
    #[serde(default)]
    pub issue_type: Option<String>,
    pub severity: String,
    pub description: String,
}

/// Void an abandoned/false Andon (append-only operational history).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct VoidAndonData {
    pub reason: String,
}

pub struct AndonApi;

impl AndonApi {
    /// List Andon events. The canonical endpoint really returns the
    /// pagination envelope — the rows live in `page.data`.
    pub async fn list_andons(client: &ApiClient) -> Result<Paginated<AndonResponse>, ApiError> {
        client.get("/api/v1/andon").await
    }

    pub async fn get_andon(client: &ApiClient, id: &str) -> Result<AndonResponse, ApiError> {
        client.get(&format!("/api/v1/andon/{}", id)).await
    }

    /// Raise an Andon with the operator's inputs only
    /// ([`RaiseAndonRequest`] carries no work_center_id/site_id): the
    /// server resolves the operational scope from the caller's active
    /// assignment.
    pub async fn raise_andon(
        client: &ApiClient,
        data: &RaiseAndonRequest,
    ) -> Result<AndonResponse, ApiError> {
        client.post("/api/v1/andon", data).await
    }

    pub async fn acknowledge_andon(
        client: &ApiClient,
        id: &str,
    ) -> Result<AndonResponse, ApiError> {
        // The canonical acknowledge is BODY-LESS (thirtieth-first audit):
        // the actor is the authenticated token's user — a payload would be
        // rejected with 415 by the handler.
        client
            .post_empty(&format!("/api/v1/andon/{id}/acknowledge"))
            .await
    }

    pub async fn resolve_andon(
        client: &ApiClient,
        id: &str,
        data: &ResolveAndonData,
    ) -> Result<AndonResponse, ApiError> {
        client
            .post(&format!("/api/v1/andon/{id}/resolve"), data)
            .await
    }

    pub async fn update_andon(
        client: &ApiClient,
        id: &str,
        data: &UpdateAndonData,
    ) -> Result<AndonResponse, ApiError> {
        client.put(&format!("/api/v1/andon/{id}"), data).await
    }

    pub async fn escalate_andon(client: &ApiClient, id: &str) -> Result<AndonResponse, ApiError> {
        client
            .post(
                &format!("/api/v1/andon/{id}/escalate"),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn void_andon(
        client: &ApiClient,
        id: &str,
        data: &VoidAndonData,
    ) -> Result<AndonResponse, ApiError> {
        client.post(&format!("/api/v1/andon/{id}/void"), data).await
    }

    pub async fn authorize_restart(
        client: &ApiClient,
        id: &str,
    ) -> Result<AndonResponse, ApiError> {
        client
            .post(
                &format!("/api/v1/andon/{id}/restart-authorization"),
                &serde_json::json!({}),
            )
            .await
    }
}

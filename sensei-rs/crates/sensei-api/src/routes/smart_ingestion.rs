//! Smart document ingestion route handlers.
//!
//! Provides endpoints for uploading documents for OCR/AI ingestion,
//! checking ingestion status, and viewing ingestion history.

use axum::{
    Json,
    extract::{Multipart, Path, Query, State},
};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{IngestionJob, IngestionStatus};

// ── Query / Response DTOs ───────────────────────────────────────────────────

/// Query parameters for listing ingestion history.
#[derive(Debug, Deserialize)]
pub struct IngestionHistoryParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Response returned after a successful upload.
#[derive(Debug, Serialize)]
pub struct UploadResponse {
    pub id: Uuid,
    pub file_name: String,
    pub status: String,
    pub message: String,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Upload a document for smart ingestion.
///
/// Accepts multipart form data with a single file field named "file".
/// The document is queued for OCR and AI-based extraction.
pub async fn upload_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<UploadResponse>> {
    let mut file_name = String::new();
    let mut content_type = String::new();
    let mut file_data: Vec<u8> = Vec::new();

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| SenseiError::Validation(format!("Failed to read multipart field: {e}")))?
    {
        let name = field.name().unwrap_or("").to_string();
        if name == "file" {
            file_name = field.file_name().unwrap_or("unnamed").to_string();
            content_type = field
                .content_type()
                .map(|m| m.to_string())
                .unwrap_or_else(|| "application/octet-stream".to_string());
            file_data = field
                .bytes()
                .await
                .map_err(|e| SenseiError::Validation(format!("Failed to read file data: {e}")))?
                .to_vec();
        }
    }

    if file_data.is_empty() {
        return Err(SenseiError::Validation("No file data provided".to_string()));
    }

    let now = Utc::now();
    let job = IngestionJob {
        id: new_id(),
        tenant_id: user.tenant_id,
        file_name,
        content_type,
        file_size: file_data.len() as i64,
        status: IngestionStatus::Pending,
        extracted_text: None,
        extracted_data: None,
        error_message: None,
        created_by: user.user_id,
        created_at: now,
        completed_at: None,
    };

    // Store the job metadata
    {
        let mut store = state.ingestion_jobs.write().await;
        store.insert(job.id, job.clone());
    }

    // Store the raw file data for processing
    {
        let mut store = state.ingestion_data.write().await;
        store.insert(job.id, file_data);
    }

    // Simulate processing in the background by immediately marking as processing
    // In a real system, this would dispatch to a background worker queue
    {
        let mut store = state.ingestion_jobs.write().await;
        if let Some(j) = store.get_mut(&job.id) {
            j.status = IngestionStatus::Processing;
        }
    }

    // Simulate async processing: extract basic text info synchronously for the API response
    // Real implementation would use OCR/AI service
    let status_str = match &job.status {
        IngestionStatus::Pending => "pending",
        IngestionStatus::Processing => "processing",
        IngestionStatus::Completed => "completed",
        IngestionStatus::Failed(_) => "failed",
    };

    Ok(Json(UploadResponse {
        id: job.id,
        file_name: job.file_name.clone(),
        status: status_str.to_string(),
        message: format!("Document '{}' queued for ingestion", job.file_name),
    }))
}

/// Get the status and result of an ingestion job.
pub async fn get_ingestion_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<IngestionJob>> {
    let store = state.ingestion_jobs.read().await;
    let job = store
        .values()
        .find(|j| j.id == id && j.tenant_id == user.tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Ingestion job {id} not found")))?;
    Ok(Json(job))
}

/// List ingestion history for the authenticated user's tenant.
pub async fn list_ingestion_history(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<IngestionHistoryParams>,
) -> Result<Json<PaginatedResponse<IngestionJob>>> {
    let store = state.ingestion_jobs.read().await;
    let mut jobs: Vec<IngestionJob> = store
        .values()
        .filter(|j| j.tenant_id == user.tenant_id)
        .filter(|j| {
            params.status.as_ref().map_or(true, |s| {
                match &j.status {
                    IngestionStatus::Pending => s == "pending",
                    IngestionStatus::Processing => s == "processing",
                    IngestionStatus::Completed => s == "completed",
                    IngestionStatus::Failed(_) => s == "failed",
                }
            })
        })
        .cloned()
        .collect();
    jobs.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    let result = PaginatedResponse::new(jobs, params.page, params.per_page);
    Ok(Json(result))
}

//! Smart document ingestion route handlers.
//!
//! Provides endpoints for uploading documents for OCR/AI ingestion,
//! checking ingestion status, and viewing ingestion history.
//!
//! Uploads are validated (size limit from config, content-type allowlist),
//! persisted raw in the ingestion data store, and processed by a background
//! task that extracts basic metadata (size, text character count for
//! text formats, sha256) before marking the job completed.

use axum::{
    extract::{Multipart, Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{IngestionJob, IngestionStatus};

/// Allowed upload content types, mapped to the canonical file extension.
const ALLOWED_CONTENT_TYPES: &[(&str, &str)] = &[
    ("application/pdf", "pdf"),
    ("image/png", "png"),
    ("image/jpeg", "jpeg"),
    ("text/plain", "txt"),
    ("text/csv", "csv"),
];

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

// ── Helpers ─────────────────────────────────────────────────────────────────

/// Strip path separators, control characters, and path-traversal remnants
/// from a file name.
fn sanitize_file_name(name: &str) -> String {
    let mut cleaned: String = name
        .chars()
        .map(|c| {
            if c.is_control() || c == '/' || c == '\\' {
                '_'
            } else {
                c
            }
        })
        .collect();
    // Collapse repeated dots so ".." traversal segments cannot survive.
    while cleaned.contains("..") {
        cleaned = cleaned.replace("..", ".");
    }
    let cleaned = cleaned.trim().trim_matches('.').to_string();
    if cleaned.is_empty() {
        "unnamed".to_string()
    } else {
        cleaned
    }
}

/// Validate the content type against the allowlist.
fn validate_content_type(content_type: &str) -> Result<String> {
    ALLOWED_CONTENT_TYPES
        .iter()
        .find(|(ct, _)| ct.eq_ignore_ascii_case(content_type))
        .map(|(_, ext)| ext.to_string())
        .ok_or_else(|| {
            SenseiError::Validation(format!(
                "Unsupported content type '{content_type}'. Allowed types: {}",
                ALLOWED_CONTENT_TYPES
                    .iter()
                    .map(|(ct, _)| *ct)
                    .collect::<Vec<_>>()
                    .join(", ")
            ))
        })
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Upload a document for smart ingestion.
///
/// Accepts multipart form data with a single file field named "file".
/// The document is validated, stored, and processed in the background.
pub async fn upload_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<UploadResponse>> {
    let max_size = state.config.api.body_limit;
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
    if file_data.len() > max_size {
        return Err(SenseiError::Validation(format!(
            "File size {} exceeds the maximum allowed size of {max_size} bytes",
            file_data.len()
        )));
    }

    let file_name = sanitize_file_name(&file_name);
    validate_content_type(&content_type)?;

    let now = Utc::now();
    let job = IngestionJob {
        id: new_id(),
        tenant_id: user.tenant_id,
        file_name,
        content_type,
        file_size: file_data.len() as i64,
        status: IngestionStatus::Processing,
        extracted_text: None,
        extracted_data: None,
        error_message: None,
        created_by: user.user_id,
        created_at: now,
        completed_at: None,
    };

    // Persist the job and the raw bytes.
    {
        let mut store = state.ingestion_jobs.write(user.tenant_id).await;
        store.insert(job.id, job.clone());
    }
    {
        let mut store = state.ingestion_data.write(user.tenant_id).await;
        store.insert(job.id, file_data);
    }

    // Real background processing: a dedicated task reads the stored bytes,
    // extracts metadata (size, text char count for text formats, sha256),
    // and marks the job completed.
    let jobs_store = state.ingestion_jobs.clone();
    let data_store = state.ingestion_data.clone();
    let job_id = job.id;
    let job_tenant = user.tenant_id;
    tokio::spawn(async move {
        let metadata = {
            let data_store = data_store.read(user.tenant_id).await;
            data_store
                .get(&job_id)
                .map(|raw| {
                    use sha2::{Digest, Sha256};
                    let file_size = raw.len() as i64;
                    let sha256 = format!("{:x}", Sha256::digest(raw));
                    // Text formats: count characters; binary formats
                    // (pdf/png/jpeg) have no meaningful raw text.
                    let is_text = matches!(
                        job.content_type.to_ascii_lowercase().as_str(),
                        "text/plain" | "text/csv"
                    );
                    let text_char_count = if is_text {
                        Some(String::from_utf8_lossy(raw).chars().count() as u64)
                    } else {
                        None
                    };
                    (file_size, sha256, text_char_count)
                })
                .ok_or_else(|| {
                    SenseiError::Internal(format!("Ingestion data for job {job_id} missing"))
                })
        };

        let completed_at = Utc::now();
        let mut store = jobs_store.write(user.tenant_id).await;
        let job = match store.get_mut(&job_id) {
            Some(j) => j,
            None => return, // Job removed while processing.
        };
        if job.tenant_id != job_tenant {
            return;
        }
        match metadata {
            Ok((file_size, sha256, text_char_count)) => {
                job.status = IngestionStatus::Completed;
                job.file_size = file_size;
                job.extracted_data = Some(serde_json::json!({
                    "sha256": sha256,
                    "file_size_bytes": file_size,
                    "text_char_count": text_char_count,
                }));
                job.completed_at = Some(completed_at);
            }
            Err(e) => {
                job.status = IngestionStatus::Failed(e.to_string());
                job.error_message = Some(e.to_string());
                job.completed_at = Some(completed_at);
            }
        }
    });

    Ok(Json(UploadResponse {
        id: job.id,
        file_name: job.file_name.clone(),
        status: "processing".to_string(),
        message: format!("Document '{}' queued for ingestion", job.file_name),
    }))
}

/// Get the status and result of an ingestion job.
pub async fn get_ingestion_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<IngestionJob>> {
    let store = state.ingestion_jobs.read(user.tenant_id).await;
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
    let store = state.ingestion_jobs.read(user.tenant_id).await;
    let mut jobs: Vec<IngestionJob> = store
        .values()
        .filter(|j| j.tenant_id == user.tenant_id)
        .filter(|j| {
            params.status.as_ref().is_none_or(|s| match &j.status {
                IngestionStatus::Pending => s == "pending",
                IngestionStatus::Processing => s == "processing",
                IngestionStatus::Completed => s == "completed",
                IngestionStatus::Failed(_) => s == "failed",
            })
        })
        .cloned()
        .collect();
    jobs.sort_by_key(|a| std::cmp::Reverse(a.created_at));
    let result = PaginatedResponse::new(jobs, params.page, params.per_page);
    Ok(Json(result))
}

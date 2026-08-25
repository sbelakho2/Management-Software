//! File attachment management route handlers.
//!
//! Provides endpoints for uploading, listing, and deleting file attachments
//! associated with various entity types. File content is stored via the
//! [`FileStorageService`] (local disk, S3, or in-memory), while metadata
//! is kept in an in-memory store (to be replaced with a database model later).

use axum::{
    Json,
    extract::{Multipart, Path, Query, State},
};
use chrono::Utc;
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::Attachment;

// ── Query DTOs ─────────────────────────────────────────────────────────────

/// Query parameters for listing attachments.
#[derive(Debug, Deserialize)]
pub struct ListAttachmentsParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Sanitize a file name for storage: keep only `[A-Za-z0-9._-]`, replace
/// every other character with `_`, and cap the length at 200 characters.
fn sanitize_file_name(raw: &str) -> String {
    let cleaned: String = raw
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-') {
                c
            } else {
                '_'
            }
        })
        .collect();
    let mut name = cleaned.trim_matches('.').to_string();
    if name.is_empty() {
        name = "unnamed".to_string();
    }
    name.chars().take(200).collect()
}

/// Slugify an entity type for safe path construction (lowercase
/// alphanumerics, `-`, `_`; anything else becomes `_`).
fn slugify_entity_type(raw: &str) -> String {
    let slug: String = raw
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '-' | '_') {
                c.to_ascii_lowercase()
            } else {
                '_'
            }
        })
        .collect();
    if slug.is_empty() {
        "generic".to_string()
    } else {
        slug.chars().take(100).collect()
    }
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Upload a file attachment.
///
/// Accepts multipart form data with a single file field named "file".
/// The file data is stored via [`FileStorageService`] and metadata is
/// saved in the in-memory attachment metadata store.
pub async fn upload_attachment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<Attachment>> {
    let mut file_name = String::new();
    let mut content_type = String::new();
    let mut file_data: Vec<u8> = Vec::new();
    let mut entity_type = String::new();
    let mut entity_id = None;

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| SenseiError::Validation(format!("Failed to read multipart field: {e}")))?
    {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "file" => {
                file_name = field
                    .file_name()
                    .unwrap_or("unnamed")
                    .to_string();
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
            "entity_type" => {
                entity_type = field
                    .text()
                    .await
                    .unwrap_or_default();
            }
            "entity_id" => {
                let id_str = field
                    .text()
                    .await
                    .unwrap_or_default();
                entity_id = Some(
                    Uuid::parse_str(&id_str)
                        .map_err(|_| SenseiError::Validation("Invalid entity_id UUID".to_string()))?,
                );
            }
            _ => {}
        }
    }

    if file_data.is_empty() {
        return Err(SenseiError::Validation("No file data provided".to_string()));
    }
    let entity_id = entity_id
        .ok_or_else(|| SenseiError::Validation("entity_id is required".to_string()))?;
    if entity_type.is_empty() {
        return Err(SenseiError::Validation("entity_type is required".to_string()));
    }

    // Enforce the per-file size limit from the request body limit config so
    // an individual file cannot exceed what the API accepts overall.
    let body_limit = state.config.api.body_limit;
    if file_data.len() > body_limit {
        return Err(SenseiError::Validation(format!(
            "File size {} bytes exceeds the maximum allowed size of {} bytes",
            file_data.len(),
            body_limit
        )));
    }

    // Sanitize both path components before building the storage path:
    // filenames keep `[A-Za-z0-9._-]` (capped at 200 chars) and entity
    // types become lowercase slugs, so malicious inputs cannot escape the
    // tenant's storage directory.
    let file_name = sanitize_file_name(&file_name);
    let entity_type = slugify_entity_type(&entity_type);

    let now = Utc::now();
    // The storage service isolates by tenant_id, so the relative path only
    // needs the entity_type, entity_id, timestamp, and filename.
    let storage_dir = format!("{}/{}/", entity_type, entity_id);
    let relative_path = format!("{}{}_{}", storage_dir, now.timestamp(), &file_name);

    // Store the file data via the storage service.
    let storage_path = state
        .storage_service
        .store(user.tenant_id, &relative_path, &file_data, &content_type)
        .await?;

    let attachment = Attachment {
        id: new_id(),
        tenant_id: user.tenant_id,
        entity_type,
        entity_id,
        file_name,
        content_type: content_type.clone(),
        file_size: file_data.len() as i64,
        storage_path,
        uploaded_by: user.user_id,
        created_at: now,
    };

    // Store metadata in-memory (file data lives in the storage service).
    {
        let mut meta = state.attachment_meta.write().await;
        meta.insert(attachment.id, attachment.clone());
    }

    Ok(Json(attachment))
}

/// List attachments for a given entity type and ID.
pub async fn list_attachments(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((entity_type, entity_id)): Path<(String, Uuid)>,
    Query(params): Query<ListAttachmentsParams>,
) -> Result<Json<PaginatedResponse<Attachment>>> {
    let meta = state.attachment_meta.read().await;
    let mut attachments: Vec<Attachment> = meta
        .values()
        .filter(|a| {
            a.tenant_id == user.tenant_id
                && a.entity_type == entity_type
                && a.entity_id == entity_id
        })
        .cloned()
        .collect();
    attachments.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    let result = PaginatedResponse::new(attachments, params.page, params.per_page);
    Ok(Json(result))
}

/// Delete an attachment by ID.
///
/// Removes the file from the storage backend and deletes the metadata entry.
pub async fn delete_attachment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    // Read the metadata entry first.
    let attachment = {
        let meta = state.attachment_meta.read().await;
        meta
            .get(&id)
            .filter(|a| a.tenant_id == user.tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Attachment {id} not found")))?
    };

    // Delete the file from the storage backend.
    state
        .storage_service
        .delete(user.tenant_id, &attachment.storage_path)
        .await?;

    // Remove the metadata entry.
    {
        let mut meta = state.attachment_meta.write().await;
        meta.remove(&id);
    }

    Ok(Json(()))
}

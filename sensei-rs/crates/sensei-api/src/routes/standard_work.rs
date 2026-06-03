//! Standard Work route handlers.
//!
//! Provides endpoints for managing standard work documents, including
//! CRUD, versioning, and version history.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{QualityCheck, StandardWorkDocument, StandardWorkVersion, SwStatus, WorkStep};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing standard work documents.
#[derive(Debug, Deserialize)]
pub struct ListStandardWorkParams {
    pub area: Option<String>,
    pub process: Option<String>,
    pub status: Option<SwStatus>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating a standard work document.
#[derive(Debug, Deserialize)]
pub struct CreateStandardWorkRequest {
    pub title: String,
    pub document_number: String,
    pub area: String,
    pub process: String,
    pub steps: Vec<WorkStep>,
    pub required_skills: Vec<String>,
    pub cycle_time_seconds: Option<i32>,
    pub takt_time_seconds: Option<i32>,
    pub quality_checks: Vec<QualityCheck>,
    pub safety_notes: Vec<String>,
    pub tools_required: Vec<String>,
    pub materials_required: Vec<String>,
    pub attachments: Vec<Uuid>,
}

/// Request body for updating a standard work document (partial).
#[derive(Debug, Deserialize)]
pub struct UpdateStandardWorkRequest {
    pub title: Option<String>,
    pub area: Option<String>,
    pub process: Option<String>,
    pub status: Option<SwStatus>,
    pub steps: Option<Vec<WorkStep>>,
    pub required_skills: Option<Vec<String>>,
    pub cycle_time_seconds: Option<i32>,
    pub takt_time_seconds: Option<i32>,
    pub quality_checks: Option<Vec<QualityCheck>>,
    pub safety_notes: Option<Vec<String>>,
    pub tools_required: Option<Vec<String>>,
    pub materials_required: Option<Vec<String>>,
    pub attachments: Option<Vec<Uuid>>,
    pub approved_by: Option<Uuid>,
    pub approved_at: Option<DateTime<Utc>>,
}

/// Request body for creating a new version of a standard work document.
#[derive(Debug, Deserialize)]
pub struct CreateVersionRequest {
    pub change_notes: Option<String>,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List standard work documents with optional filters and pagination.
pub async fn list_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListStandardWorkParams>,
) -> Result<Json<PaginatedResponse<StandardWorkDocument>>> {
    let tenant_id = user.tenant_id;
    let store = state.standard_work_documents.read().await;
    let mut docs: Vec<StandardWorkDocument> = store
        .values()
        .filter(|d| d.tenant_id == tenant_id)
        .filter(|d| {
            if let Some(ref area) = params.area {
                d.area == *area
            } else {
                true
            }
        })
        .filter(|d| {
            if let Some(ref process) = params.process {
                d.process == *process
            } else {
                true
            }
        })
        .filter(|d| {
            if let Some(ref status) = params.status {
                std::mem::discriminant(status) == std::mem::discriminant(&d.status)
            } else {
                true
            }
        })
        .cloned()
        .collect();
    docs.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    let result = PaginatedResponse::new(docs, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new standard work document.
pub async fn create_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateStandardWorkRequest>,
) -> Result<Json<StandardWorkDocument>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let doc = StandardWorkDocument {
        id: new_id(),
        tenant_id,
        title: req.title,
        document_number: req.document_number,
        area: req.area,
        process: req.process,
        current_version: 1,
        status: SwStatus::Draft,
        steps: req.steps,
        required_skills: req.required_skills,
        cycle_time_seconds: req.cycle_time_seconds,
        takt_time_seconds: req.takt_time_seconds,
        quality_checks: req.quality_checks,
        safety_notes: req.safety_notes,
        tools_required: req.tools_required,
        materials_required: req.materials_required,
        attachments: req.attachments,
        approved_by: None,
        approved_at: None,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.standard_work_documents.write().await;
    store.insert(doc.id, doc.clone());
    Ok(Json(doc))
}

/// Get a standard work document by ID.
pub async fn get_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<StandardWorkDocument>> {
    let tenant_id = user.tenant_id;
    let store = state.standard_work_documents.read().await;
    let doc = store
        .values()
        .find(|d| d.id == sw_id && d.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    Ok(Json(doc))
}

/// Update a standard work document.
pub async fn update_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
    Json(req): Json<UpdateStandardWorkRequest>,
) -> Result<Json<StandardWorkDocument>> {
    let tenant_id = user.tenant_id;
    let mut store = state.standard_work_documents.write().await;
    let doc = store
        .get_mut(&sw_id)
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if let Some(title) = req.title {
        doc.title = title;
    }
    if let Some(area) = req.area {
        doc.area = area;
    }
    if let Some(process) = req.process {
        doc.process = process;
    }
    if let Some(status) = req.status {
        doc.status = status;
    }
    if let Some(steps) = req.steps {
        doc.steps = steps;
    }
    if let Some(skills) = req.required_skills {
        doc.required_skills = skills;
    }
    if let Some(cycle) = req.cycle_time_seconds {
        doc.cycle_time_seconds = Some(cycle);
    }
    if let Some(takt) = req.takt_time_seconds {
        doc.takt_time_seconds = Some(takt);
    }
    if let Some(checks) = req.quality_checks {
        doc.quality_checks = checks;
    }
    if let Some(notes) = req.safety_notes {
        doc.safety_notes = notes;
    }
    if let Some(tools) = req.tools_required {
        doc.tools_required = tools;
    }
    if let Some(mats) = req.materials_required {
        doc.materials_required = mats;
    }
    if let Some(atts) = req.attachments {
        doc.attachments = atts;
    }
    if let Some(approved_by) = req.approved_by {
        doc.approved_by = Some(approved_by);
    }
    if let Some(approved_at) = req.approved_at {
        doc.approved_at = Some(approved_at);
    }
    doc.updated_at = Utc::now();
    Ok(Json(doc.clone()))
}

/// Delete a standard work document.
pub async fn delete_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.standard_work_documents.write().await;
    let exists = store
        .get(&sw_id)
        .filter(|d| d.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("Standard work {sw_id} not found")));
    }
    store.remove(&sw_id);
    Ok(Json(()))
}

// ── Versioning Handlers ────────────────────────────────────────────────────

/// List version history for a standard work document.
pub async fn list_versions(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<Vec<StandardWorkVersion>>> {
    let tenant_id = user.tenant_id;
    let store = state.standard_work_versions.read().await;
    let mut versions: Vec<StandardWorkVersion> = store
        .values()
        .filter(|v| v.document_id == sw_id && v.tenant_id == tenant_id)
        .cloned()
        .collect();
    versions.sort_by(|a, b| b.version_number.cmp(&a.version_number));
    Ok(Json(versions))
}

/// Create a new version of a standard work document.
pub async fn create_version(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
    Json(req): Json<CreateVersionRequest>,
) -> Result<Json<StandardWorkVersion>> {
    let tenant_id = user.tenant_id;

    // Fetch the current document to snapshot
    let doc = {
        let store = state.standard_work_documents.read().await;
        store
            .values()
            .find(|d| d.id == sw_id && d.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?
    };

    let new_version_number = doc.current_version + 1;
    let now = Utc::now();

    let version = StandardWorkVersion {
        id: new_id(),
        document_id: sw_id,
        tenant_id,
        version_number: new_version_number,
        snapshot: serde_json::to_value(&doc).unwrap_or_default(),
        change_notes: req.change_notes,
        created_by: user.user_id,
        created_at: now,
    };

    // Store the version
    {
        let mut store = state.standard_work_versions.write().await;
        store.insert(version.id, version.clone());
    }

    // Update the document's current version number
    {
        let mut store = state.standard_work_documents.write().await;
        if let Some(d) = store.get_mut(&sw_id) {
            d.current_version = new_version_number;
            d.updated_at = now;
        }
    }

    Ok(Json(version))
}

/// Get a specific version of a standard work document.
pub async fn get_version(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((_sw_id, version_id)): Path<(Uuid, Uuid)>,
) -> Result<Json<StandardWorkVersion>> {
    let tenant_id = user.tenant_id;
    let store = state.standard_work_versions.read().await;
    let version = store
        .values()
        .find(|v| v.id == version_id && v.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Version {version_id} not found")))?;
    Ok(Json(version))
}

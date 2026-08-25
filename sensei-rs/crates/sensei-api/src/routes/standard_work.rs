//! Standard Work route handlers.
//!
//! Provides endpoints for managing standard work documents, including
//! CRUD, versioning, and version history.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::Deserialize;
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
}

/// Request body for approving a standard work document.
#[derive(Debug, Deserialize)]
pub struct ApproveStandardWorkRequest {
    /// Optional comment/notes recorded with the approval.
    pub notes: Option<String>,
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
    docs.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
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
    // approved_by / approved_at are intentionally NOT settable via PUT —
    // they are owned by the approve/reject endpoints.
    doc.updated_at = Utc::now();
    Ok(Json(doc.clone()))
}

/// Approve a standard work document.
///
/// Transitions the document from `Draft` to `Published`, recording the
/// approving user (from the token) and the approval timestamp. Only draft
/// documents can be approved.
pub async fn approve_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
    Json(_req): Json<ApproveStandardWorkRequest>,
) -> Result<Json<StandardWorkDocument>> {
    let tenant_id = user.tenant_id;
    let mut store = state.standard_work_documents.write().await;
    let doc = store
        .get_mut(&sw_id)
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if doc.status != SwStatus::Draft {
        return Err(SenseiError::Conflict(format!(
            "Cannot approve a document in state {:?}; only Draft documents can be approved",
            doc.status
        )));
    }
    doc.status = SwStatus::Published;
    doc.approved_by = Some(user.user_id);
    doc.approved_at = Some(Utc::now());
    doc.updated_at = Utc::now();
    Ok(Json(doc.clone()))
}

/// Reject a standard work document.
///
/// Declines the draft for approval: the document returns to `Draft` with the
/// approval fields cleared. (The data model has no dedicated `Rejected`
/// state, so a rejected document remains editable as a draft.)
pub async fn reject_standard_work(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<StandardWorkDocument>> {
    let tenant_id = _user.tenant_id;
    let mut store = state.standard_work_documents.write().await;
    let doc = store
        .get_mut(&sw_id)
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if doc.status != SwStatus::Draft {
        return Err(SenseiError::Conflict(format!(
            "Cannot reject a document in state {:?}; only Draft documents can be rejected",
            doc.status
        )));
    }
    // The document stays a draft but the approval is cleared; `approved_by`
    // staying None is the observable rejection signal.
    doc.approved_by = None;
    doc.approved_at = None;
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
        return Err(SenseiError::NotFound(format!(
            "Standard work {sw_id} not found"
        )));
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
    versions.sort_by_key(|a| std::cmp::Reverse(a.version_number));
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
///
/// The version must belong to the requested document; a version owned by a
/// different document is rejected with 404.
pub async fn get_version(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((sw_id, version_id)): Path<(Uuid, Uuid)>,
) -> Result<Json<StandardWorkVersion>> {
    let tenant_id = user.tenant_id;
    let store = state.standard_work_versions.read().await;
    let version = store
        .values()
        .find(|v| v.id == version_id && v.document_id == sw_id && v.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Version {version_id} not found")))?;
    Ok(Json(version))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_auth::password::hash_password;
    use sensei_core::config::AppConfig;
    use sensei_core::types::TenantId;
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    async fn test_state() -> (AppState, TenantId, Uuid) {
        let hash = hash_password("Test@1234").unwrap();
        let tenant_id = TenantId::new_v4();
        let users_service =
            InMemoryUsersService::with_admin("admin@test.com", "Admin User", &hash, tenant_id);
        let users_service = Arc::new(users_service) as Arc<dyn UsersService>;
        let config = AppConfig::from_env().unwrap();
        let state = AppState::new(config, users_service);
        let admin = state
            .users_service
            .find_by_email("admin@test.com")
            .await
            .unwrap();
        (state, tenant_id, admin.id)
    }

    fn auth_user(tenant_id: TenantId, user_id: Uuid) -> AuthenticatedUser {
        AuthenticatedUser {
            user_id,
            tenant_id,
            roles: vec!["admin".to_string()],
        }
    }

    fn doc_payload() -> CreateStandardWorkRequest {
        CreateStandardWorkRequest {
            title: "Doc".to_string(),
            document_number: "SW-001".to_string(),
            area: "Assembly".to_string(),
            process: "Process A".to_string(),
            steps: Vec::new(),
            required_skills: Vec::new(),
            cycle_time_seconds: None,
            takt_time_seconds: None,
            quality_checks: Vec::new(),
            safety_notes: Vec::new(),
            tools_required: Vec::new(),
            materials_required: Vec::new(),
            attachments: Vec::new(),
        }
    }

    #[tokio::test]
    async fn test_approve_publishes_and_records_approver() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let created = create_standard_work(user.clone(), State(state.clone()), Json(doc_payload()))
            .await
            .unwrap();
        assert_eq!(created.status, SwStatus::Draft);

        let approved = approve_standard_work(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(ApproveStandardWorkRequest { notes: None }),
        )
        .await
        .unwrap();
        assert_eq!(approved.status, SwStatus::Published);
        assert_eq!(approved.approved_by, Some(uid));
        assert!(approved.approved_at.is_some());

        // Approving again is a conflict (already published).
        let err = approve_standard_work(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(ApproveStandardWorkRequest { notes: None }),
        )
        .await
        .unwrap_err();
        assert!(matches!(err, SenseiError::Conflict(_)));
    }

    #[tokio::test]
    async fn test_reject_clears_approval() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let created = create_standard_work(user.clone(), State(state.clone()), Json(doc_payload()))
            .await
            .unwrap();

        let rejected = reject_standard_work(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(rejected.status, SwStatus::Draft);
        assert!(rejected.approved_by.is_none());
        assert!(rejected.approved_at.is_none());
    }

    #[tokio::test]
    async fn test_get_version_scoped_by_document() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let doc_a = create_standard_work(user.clone(), State(state.clone()), Json(doc_payload()))
            .await
            .unwrap();
        let doc_b = create_standard_work(user.clone(), State(state.clone()), Json(doc_payload()))
            .await
            .unwrap();

        let version = create_version(
            user.clone(),
            State(state.clone()),
            Path(doc_a.id),
            Json(CreateVersionRequest { change_notes: None }),
        )
        .await
        .unwrap();

        // Version of doc A under doc B → 404.
        let err = get_version(
            user.clone(),
            State(state.clone()),
            Path((doc_b.id, version.id)),
        )
        .await
        .unwrap_err();
        assert!(matches!(err, SenseiError::NotFound(_)));

        // Under doc A → OK.
        let found = get_version(
            user.clone(),
            State(state.clone()),
            Path((doc_a.id, version.id)),
        )
        .await
        .unwrap();
        assert_eq!(found.id, version.id);
    }
}

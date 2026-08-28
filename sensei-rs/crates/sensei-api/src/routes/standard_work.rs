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
    #[serde(rename = "status")]
    pub status: Option<SwStatus>,
    pub area: Option<String>,
    pub process: Option<String>,

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
    /// Optimistic-concurrency token: the version the caller read. A
    /// mismatch returns 409 VERSION_CONFLICT instead of overwriting.
    #[serde(default)]
    pub expected_version: Option<u64>,

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
    /// Optional future effective date (defaults to now).
    #[serde(default)]
    pub effective_from: Option<chrono::DateTime<chrono::Utc>>,
}

/// Request body for approving a standard (item 15: optional future
/// effective date).
#[derive(Debug, Deserialize)]
pub struct SupersedeStandardWorkRequest {
    /// The replacement revision this standard is superseded by.
    pub replacement_id: Option<Uuid>,
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
    user.require_permission("tps:standard-work:read")?;
    let mut docs = state
        .standard_work_repo
        .list(user.tenant_id)
        .await
        .map_err(SenseiError::Internal)?;
    docs.retain(|d| {
        (params.area.as_ref().is_none_or(|a| d.area == *a))
            && (params.process.as_ref().is_none_or(|p| d.process == *p))
            && (params
                .status
                .as_ref()
                .is_none_or(|s| std::mem::discriminant(s) == std::mem::discriminant(&d.status)))
    });
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
    user.require_permission("tps:standard-work:draft")?;
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
        version: 1,
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
        effective_from: None,
        effective_to: None,
        supersedes: None,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    state
        .standard_work_repo
        .put(&doc, None)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(doc))
}

/// Get a standard work document by ID.
pub async fn get_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<StandardWorkDocument>> {
    user.require_permission("tps:standard-work:read")?;
    let tenant_id = user.tenant_id;
    let doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
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
    user.require_permission("tps:standard-work:draft")?;
    let tenant_id = user.tenant_id;
    let mut doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    // Optimistic concurrency: a stale edit is rejected ATOMICALLY by the
    // repository (the CAS lives in the SQL, not a read/check/write race).
    // An EFFECTIVE (or approved) revision is immutable: changes create a
    // new revision, they never mutate the controlled standard in place.
    if matches!(doc.status, SwStatus::Published) || doc.approved_by.is_some() {
        return Err(SenseiError::Conflict(
            "Effective/approved standard work is immutable — create a new revision instead"
                .to_string(),
        ));
    }
    if let Some(title) = req.title {
        doc.title = title;
    }
    if let Some(area) = req.area {
        doc.area = area;
    }
    if let Some(process) = req.process {
        doc.process = process;
    }
    // Status is NEVER editable via the generic update: it is a controlled
    // state machine (draft -> under_review -> approved -> effective ->
    // superseded | rejected) driven by the approve/reject/publish commands.
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

    let expected = req.expected_version;
    state
        .standard_work_repo
        .put(&doc, expected)
        .await
        .map_err(|e| {
            if e.contains("VERSION_CONFLICT") {
                SenseiError::Conflict(e)
            } else {
                SenseiError::Internal(e)
            }
        })?;
    Ok(Json(doc))
}

/// Submit a draft for review (item 15): Draft -> UnderReview. Once under
/// review the document is immutable except by reviewers.
pub async fn submit_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<StandardWorkDocument>> {
    user.require_permission("tps:standard-work:review")?;
    let tenant_id = user.tenant_id;
    let mut doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if doc.status != SwStatus::Draft && doc.status != SwStatus::Rejected {
        return Err(SenseiError::Conflict(format!(
            "Cannot submit a document in state {:?}; only Draft/Rejected documents can be submitted",
            doc.status
        )));
    }
    doc.status = SwStatus::UnderReview;
    doc.approved_by = None;
    doc.approved_at = None;
    doc.updated_at = Utc::now();
    state
        .standard_work_repo
        .put(&doc, None)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(doc))
}

/// Approve a standard work document (item 15): UnderReview -> Published,
/// recording the approving user and timestamp. The document becomes
/// EFFECTIVE immediately (effective_from = now) unless a future
/// effective_from was requested.
pub async fn approve_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
    Json(req): Json<ApproveStandardWorkRequest>,
) -> Result<Json<StandardWorkDocument>> {
    user.require_permission("tps:standard-work:approve")?;
    let tenant_id = user.tenant_id;
    let mut doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if doc.status != SwStatus::UnderReview {
        return Err(SenseiError::Conflict(format!(
            "Cannot approve a document in state {:?}; only UnderReview documents can be approved",
            doc.status
        )));
    }
    let now = Utc::now();
    // A requested future effective date is honored; an explicit past date
    // is rejected (approval cannot retroactively apply a controlled
    // standard).
    if let Some(from) = req.effective_from {
        if from < now - chrono::Duration::minutes(5) {
            return Err(SenseiError::Validation(
                "effective_from cannot be in the past — a controlled standard                  takes effect now or in the future"
                    .to_string(),
            ));
        }
        doc.effective_from = Some(from);
    } else {
        doc.effective_from = Some(now);
    }
    doc.status = SwStatus::Published;
    doc.approved_by = Some(user.user_id);
    doc.approved_at = Some(now);
    doc.updated_at = now;

    state
        .standard_work_repo
        .put(&doc, None)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(doc))
}

/// Reject a standard work document (item 15): UnderReview -> Rejected.
/// A rejected document is editable again and must be re-submitted.
pub async fn reject_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<StandardWorkDocument>> {
    user.require_permission("tps:standard-work:review")?;
    let tenant_id = user.tenant_id;
    let mut doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if doc.status != SwStatus::UnderReview {
        return Err(SenseiError::Conflict(format!(
            "Cannot reject a document in state {:?}; only UnderReview documents can be rejected",
            doc.status
        )));
    }
    doc.status = SwStatus::Rejected;
    doc.approved_by = None;
    doc.approved_at = None;
    doc.updated_at = Utc::now();

    state
        .standard_work_repo
        .put(&doc, None)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(doc))
}

/// Supersede an effective standard (item 15): the CURRENT revision is
/// closed (effective_to = now, status = superseded) and the REPLACEMENT
/// revision's `supersedes` field is linked. The lineage is explicit — a
/// superseded standard is never silently replaced.
pub async fn supersede_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
    Json(req): Json<SupersedeStandardWorkRequest>,
) -> Result<Json<StandardWorkDocument>> {
    user.require_permission("tps:standard-work:approve")?;
    let tenant_id = user.tenant_id;
    let mut doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    if doc.status != SwStatus::Published && doc.status != SwStatus::Effective {
        return Err(SenseiError::Conflict(format!(
            "Cannot supersede a document in state {:?}; only Published/Effective              standards can be superseded",
            doc.status
        )));
    }
    let now = Utc::now();
    doc.status = SwStatus::Superseded;
    doc.effective_to = Some(now);
    doc.updated_at = now;
    state
        .standard_work_repo
        .put(&doc, None)
        .await
        .map_err(SenseiError::Internal)?;

    // Link the replacement revision's supersedes lineage (both rows live
    // in the same table; the replacement is fetched and updated).
    if let Some(replacement_id) = req.replacement_id {
        let mut replacement = state
            .standard_work_repo
            .get(tenant_id, replacement_id)
            .await
            .map_err(SenseiError::Internal)?
            .filter(|d| d.tenant_id == tenant_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!(
                    "Replacement standard work {replacement_id} not found"
                ))
            })?;
        replacement.supersedes = Some(sw_id);
        replacement.updated_at = now;
        state
            .standard_work_repo
            .put(&replacement, None)
            .await
            .map_err(SenseiError::Internal)?;
    }
    Ok(Json(doc))
}

/// Delete a standard work document.
pub async fn delete_standard_work(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("tps:standard-work:draft")?;
    let tenant_id = user.tenant_id;
    let mut doc = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;
    // Append-only: controlled documents are ARCHIVED, never erased.
    doc.status = SwStatus::Archived;
    doc.updated_at = Utc::now();
    state
        .standard_work_repo
        .put(&doc, None)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(()))
}

// ── Versioning Handlers ────────────────────────────────────────────────────

/// List version history for a standard work document.
pub async fn list_versions(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
) -> Result<Json<Vec<StandardWorkVersion>>> {
    user.require_permission("tps:standard-work:read")?;
    let tenant_id = user.tenant_id;
    let versions = state
        .standard_work_repo
        .list_versions(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(versions))
}

/// Create a new version of a standard work document.
pub async fn create_version(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sw_id): Path<Uuid>,
    Json(req): Json<CreateVersionRequest>,
) -> Result<Json<StandardWorkVersion>> {
    user.require_permission("tps:standard-work:draft")?;
    let tenant_id = user.tenant_id;

    // Fetch the current document to snapshot (typed repository).
    let doc = state
        .standard_work_repo
        .get(user.tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Standard work {sw_id} not found")))?;

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

    // Store the version (typed repository — the version relationship is
    // database-enforced).
    state
        .standard_work_repo
        .put_version(&version)
        .await
        .map_err(SenseiError::Internal)?;

    // Update the document's current version number.
    if let Some(mut d) = state
        .standard_work_repo
        .get(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
    {
        d.current_version = new_version_number;
        d.updated_at = now;
        state
            .standard_work_repo
            .put(&d, None)
            .await
            .map_err(SenseiError::Internal)?;
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
    user.require_permission("tps:standard-work:read")?;
    let tenant_id = user.tenant_id;
    let version = state
        .standard_work_repo
        .list_versions(tenant_id, sw_id)
        .await
        .map_err(SenseiError::Internal)?
        .into_iter()
        .find(|v| v.id == version_id)
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
            roles: vec![
                "tenant_admin".to_string(),
                "production_manager".to_string(),
                "operator".to_string(),
            ],
            sid: None,
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

        // Item 15: the lifecycle is draft -> under_review -> published.
        // Approving a plain draft is REJECTED.
        let premature = approve_standard_work(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(ApproveStandardWorkRequest {
                notes: None,
                effective_from: None,
            }),
        )
        .await
        .unwrap_err();
        assert!(matches!(premature, SenseiError::Conflict(_)));

        let submitted = submit_standard_work(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(submitted.status, SwStatus::UnderReview);

        let approved = approve_standard_work(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(ApproveStandardWorkRequest {
                notes: None,
                effective_from: None,
            }),
        )
        .await
        .unwrap();
        assert_eq!(approved.status, SwStatus::Published);
        assert_eq!(approved.approved_by, Some(uid));
        assert!(approved.approved_at.is_some());
        assert!(
            approved.effective_from.is_some(),
            "approval sets the effective date"
        );

        // Approving again is a conflict (already published).
        let err = approve_standard_work(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(ApproveStandardWorkRequest {
                notes: None,
                effective_from: None,
            }),
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

        // Item 15: only UnderReview documents can be rejected.
        let premature = reject_standard_work(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap_err();
        assert!(matches!(premature, SenseiError::Conflict(_)));

        let submitted = submit_standard_work(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(submitted.status, SwStatus::UnderReview);

        let rejected = reject_standard_work(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(rejected.status, SwStatus::Rejected);
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

//! File attachment management route handlers.
//!
//! Provides endpoints for uploading, listing, and deleting file attachments
//! associated with various entity types.
//!
//! # Security model
//!
//! * **Streaming uploads** — the multipart file field is consumed chunk by
//!   chunk into a temporary file while enforcing the running byte limit and
//!   computing the SHA-256 digest; the blob is then streamed into the
//!   storage service. The request body never fully buffers in memory.
//! * **Opaque storage keys** — blobs are stored under server-generated UUID
//!   keys ([`FileStorageService::store_opaque`]); caller-supplied paths are
//!   never joined into the storage namespace.
//! * **Reference validation** — the referenced `(entity_type, entity_id)`
//!   must exist **and** belong to the caller's tenant. Only entity types
//!   backed by an entity store are accepted; unknown types fail closed.
//! * **Parent authorization (twenty-ninth-audit Wave B item 11;
//!   thirtieth-audit P0 items 12-13)** — attachments INHERIT their
//!   parent's authorization: list/download require `attachments:read` AND
//!   [`require_parent_read`] on the parent, upload/delete require
//!   `attachments:manage` AND [`require_parent_manage`] — the parent
//!   check runs BEFORE any listing, presigning or blob deletion, so a
//!   known attachment UUID never bypasses the parent's permission/scope.
//!   The proofs enforce the caller's FULL scope: an explicit tenant-wide
//!   grant still proves parent EXISTENCE, work-order parents match their
//!   work-center carrier exactly (never the parent site), NCR parents
//!   apply the record's server-stamped `scope_site_id` /
//!   `scope_work_center_id` (corporate NULL records require tenant-wide),
//!   and `work_center` parents resolve through the relational
//!   `work_centers` row.
//! * **Server-side content types** — the browser-provided MIME type is
//!   ignored; the content type is derived from a small extension allowlist
//!   (pdf, png, jpeg, txt, csv, xlsx, docx, md). Unknown extensions are
//!   rejected.
//! * **Deletion lifecycle (thirtieth-audit item 14)** — DELETE runs a
//!   two-phase lifecycle (`active → deleting → object delete → metadata
//!   remove`) instead of deleting the object first and then the metadata:
//!   the metadata record is tombstoned FIRST, so a transient failure can
//!   never leave an active row pointing at a missing object. If the object
//!   removal fails the record stays tombstoned — invisible to downloads
//!   and listings — and the NEXT delete attempt on the same id resumes and
//!   completes the cleanup idempotently (an object that is already gone is
//!   treated as success). See [`delete_attachment`] for the state machine.
//!
//! File content lives in the storage service; metadata (including the opaque
//! key and digest) is kept in the attachment metadata store, so listing and
//! deletion keep working and downloads resolve the opaque key at read time.

use axum::{
    extract::{Multipart, Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::authorization::parent_resource::{require_parent_manage, require_parent_read};
use crate::db_stores::EntityStore;
use crate::state::AppState;
use crate::stores::Attachment;

// ── Query DTOs ─────────────────────────────────────────────────────────────

/// Query parameters for listing attachments.
#[derive(Debug, Deserialize)]
pub struct ListAttachmentsParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Response shape returned by the upload endpoint.
///
/// The `url_path` resolves to the download endpoint (not yet registered; see
/// the production-readiness notes) and the `digest` is the SHA-256 of the
/// uploaded bytes, so clients can verify integrity end to end.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UploadedAttachment {
    /// Attachment metadata id.
    pub id: Uuid,
    /// Download URL path (resolve the opaque key at download time).
    pub url_path: String,
    /// Sanitized client file name.
    pub file_name: String,
    /// Server-side content type (extension allowlist, never browser-supplied).
    pub content_type: String,
    /// Size in bytes.
    pub file_size: i64,
    /// SHA-256 hex digest of the uploaded bytes.
    pub digest: String,
    /// Canonical entity type the attachment belongs to.
    pub entity_type: String,
    /// Entity the attachment is attached to.
    pub entity_id: Uuid,
    /// Creation timestamp.
    pub created_at: DateTime<Utc>,
}

impl UploadedAttachment {
    fn from_attachment(a: &Attachment, digest: String) -> Self {
        Self {
            id: a.id,
            url_path: format!("/api/v1/attachments/{}/download", a.id),
            file_name: a.file_name.clone(),
            content_type: a.content_type.clone(),
            file_size: a.file_size,
            digest,
            entity_type: a.entity_type.clone(),
            entity_id: a.entity_id,
            created_at: a.created_at,
        }
    }
}

/// Sanitize a file name for display/storage purposes: keep only
/// `[A-Za-z0-9._-]`, replace every other character with `_`, and cap the
/// length at 200 characters.
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

// ── Content-type allowlist ──────────────────────────────────────────────────

/// Map a sanitized file extension to a server-side content type.
///
/// The browser MIME type is never trusted; unknown extensions are rejected.
fn content_type_for_extension(ext: &str) -> Option<&'static str> {
    match ext {
        "pdf" => Some("application/pdf"),
        "png" => Some("image/png"),
        "jpeg" | "jpg" => Some("image/jpeg"),
        "txt" => Some("text/plain"),
        "csv" => Some("text/csv"),
        "xlsx" => Some("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "docx" => Some("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "md" => Some("text/markdown"),
        _ => None,
    }
}

/// Extract the lowercase extension from a sanitized file name (after the last
/// dot), if any.
fn file_extension(file_name: &str) -> Option<&str> {
    file_name
        .rsplit_once('.')
        .map(|(_, ext)| ext.trim())
        .filter(|ext| !ext.is_empty() && !ext.contains(' '))
}

// ── Entity reference validation (fail closed) ───────────────────────────────

/// Trait implemented for every entity-store type that can host attachments.
///
/// Existence + tenant ownership are the invariants the upload route enforces
/// before storing bytes.
trait TenantOwnedEntity: Send + Sync {
    fn entity_tenant_id(&self) -> Uuid;
}

macro_rules! impl_tenant_owned {
    ($($ty:ty),+ $(,)?) => {
        $(
            impl TenantOwnedEntity for $ty {
                fn entity_tenant_id(&self) -> Uuid { self.tenant_id }
            }
        )+
    };
}

impl_tenant_owned!(
    crate::stores::Task,
    crate::stores::KanbanBoard,
    crate::stores::Notification,
    crate::stores::NotificationPreferences,
    crate::stores::QuoteVersion,
    crate::stores::LearningModule,
    crate::stores::Opportunity,
    crate::stores::EscalationPolicy,
    crate::stores::TrainingMatrixEntry,
    crate::stores::KnowledgePack,
    crate::stores::IngestionJob,
    crate::stores::WorkCenter,
    crate::stores::ObeyaBoard,
    crate::stores::CtqCharacteristic,
    crate::stores::CtqRecord,
    crate::stores::InventoryItem,
    crate::stores::StockMove,
    crate::stores::Warehouse,
    crate::stores::DemandEntry,
    crate::stores::SupplyOrder,
    crate::stores::MrpRun,
    crate::stores::AuditLogEntry,
    crate::stores::ProductionCell,
    crate::stores::SavedView,
    crate::stores::WorkPacket,
    crate::stores::CostBuild,
    crate::stores::NpiConversion,
    crate::stores::KpiDefinition,
    crate::stores::KpiValue,
    crate::stores::LswStandard,
    crate::stores::LswAudit,
    crate::stores::NotificationTrigger,
    crate::stores::StandardWorkDocument,
    crate::stores::StandardWorkVersion,
    crate::stores::StateMachineDefinition,
    crate::stores::StateMachineInstance,
    crate::stores::TrainingCourse,
    crate::stores::TrainingEnrollment,
);

/// Generic checker over any [`EntityStore`] whose entity type is
/// [`TenantOwnedEntity`].
struct StoreRefChecker<T> {
    store: EntityStore<T>,
}

impl<T> StoreRefChecker<T> {
    fn new(store: EntityStore<T>) -> Self {
        Self { store }
    }
}

#[async_trait::async_trait]
trait EntityReferenceChecker: Send + Sync {
    /// Whether an entity with `id` exists and belongs to `tenant_id`.
    async fn exists(&self, id: Uuid, tenant_id: Uuid) -> bool;
}

#[async_trait::async_trait]
impl<T> EntityReferenceChecker for StoreRefChecker<T>
where
    T: TenantOwnedEntity
        + serde::Serialize
        + serde::de::DeserializeOwned
        + Clone
        + PartialEq
        + Send
        + Sync
        + 'static,
{
    async fn exists(&self, id: Uuid, tenant_id: Uuid) -> bool {
        let map = self.store.read(tenant_id).await;
        map.get(&id)
            .map(|e| e.entity_tenant_id() == tenant_id)
            .unwrap_or(false)
    }
}

/// Canonical entity types backed by an entity store in [`AppState`].
///
/// Any other `entity_type` is rejected with a clear message (fail closed).
const SUPPORTED_ENTITY_TYPES: &str = concat!(
    "task, kanban_board, notification, notification_preference, quote_version, ",
    "learning_module, opportunity, escalation_policy, training_matrix_entry, ",
    "knowledge_pack, ingestion_job, work_center, obeya_board, ctq_characteristic, ",
    "ctq_record, inventory_item, stock_move, warehouse, demand_entry, supply_order, ",
    "mrp_run, audit_log_entry, production_cell, saved_view, work_packet, cost_build, ",
    "npi_conversion, kpi_definition, kpi_value, lsw_standard, lsw_audit, ",
    "notification_trigger, standard_work, standard_work_version, ",
    "state_machine_definition, state_machine_instance, training_course, training_enrollment"
);

/// Resolve the reference checker for a canonical entity type.
fn entity_checker(state: &AppState, entity_type: &str) -> Option<Box<dyn EntityReferenceChecker>> {
    Some(match entity_type {
        "task" => Box::new(StoreRefChecker::new(state.tasks.clone())),
        "kanban_board" => Box::new(StoreRefChecker::new(state.kanban_boards.clone())),
        "notification" => Box::new(StoreRefChecker::new(state.notifications.clone())),
        "notification_preference" => {
            Box::new(StoreRefChecker::new(state.notification_preferences.clone()))
        }
        "quote_version" => Box::new(StoreRefChecker::new(state.quote_versions.clone())),
        "learning_module" => Box::new(StoreRefChecker::new(state.learning_modules.clone())),
        "opportunity" => Box::new(StoreRefChecker::new(state.opportunities.clone())),
        "escalation_policy" => Box::new(StoreRefChecker::new(state.escalation_policies.clone())),
        "training_matrix_entry" => Box::new(StoreRefChecker::new(state.training_matrix.clone())),
        "knowledge_pack" => Box::new(StoreRefChecker::new(state.knowledge_packs.clone())),
        "ingestion_job" => Box::new(StoreRefChecker::new(state.ingestion_jobs.clone())),
        "work_center" => Box::new(StoreRefChecker::new(state.work_centers.clone())),
        "obeya_board" => Box::new(StoreRefChecker::new(state.obeya_boards.clone())),
        "ctq_characteristic" => Box::new(StoreRefChecker::new(state.ctq_characteristics.clone())),
        "ctq_record" => Box::new(StoreRefChecker::new(state.ctq_records.clone())),
        "inventory_item" => Box::new(StoreRefChecker::new(state.inventory_items.clone())),
        "stock_move" => Box::new(StoreRefChecker::new(state.stock_moves.clone())),
        "warehouse" => Box::new(StoreRefChecker::new(state.warehouses.clone())),
        "demand_entry" => Box::new(StoreRefChecker::new(state.demand_entries.clone())),
        "supply_order" => Box::new(StoreRefChecker::new(state.supply_orders.clone())),
        "mrp_run" => Box::new(StoreRefChecker::new(state.mrp_runs.clone())),
        "audit_log_entry" => Box::new(StoreRefChecker::new(state.audit_log_entries.clone())),
        "production_cell" => Box::new(StoreRefChecker::new(state.production_cells.clone())),
        "saved_view" => Box::new(StoreRefChecker::new(state.saved_views.clone())),
        "work_packet" => Box::new(StoreRefChecker::new(state.work_packets.clone())),
        "cost_build" => Box::new(StoreRefChecker::new(state.cost_builds.clone())),
        "npi_conversion" => Box::new(StoreRefChecker::new(state.npi_conversions.clone())),
        "kpi_definition" => Box::new(StoreRefChecker::new(state.kpi_definitions.clone())),
        "kpi_value" => Box::new(StoreRefChecker::new(state.kpi_values.clone())),
        "lsw_standard" => Box::new(StoreRefChecker::new(state.lsw_standards.clone())),
        "lsw_audit" => Box::new(StoreRefChecker::new(state.lsw_audits.clone())),
        "notification_trigger" => {
            Box::new(StoreRefChecker::new(state.notification_triggers.clone()))
        }
        "standard_work" => Box::new(StoreRefChecker::new(state.standard_work_documents.clone())),
        "standard_work_version" => {
            Box::new(StoreRefChecker::new(state.standard_work_versions.clone()))
        }
        "state_machine_definition" => Box::new(StoreRefChecker::new(
            state.state_machine_definitions.clone(),
        )),
        "state_machine_instance" => {
            Box::new(StoreRefChecker::new(state.state_machine_instances.clone()))
        }
        "training_course" => Box::new(StoreRefChecker::new(state.training_courses.clone())),
        "training_enrollment" => Box::new(StoreRefChecker::new(state.training_enrollments.clone())),
        _ => return None,
    })
}

/// Whether an entity with `id` exists and belongs to `tenant_id`.
///
/// Shared with the parent-authorization module (`authorization/
/// parent_resource.rs`): entity-store-backed parents are proven here so
/// the existence semantics are identical to the upload validation.
pub(crate) async fn entity_exists(
    state: &AppState,
    entity_type: &str,
    entity_id: Uuid,
    tenant_id: Uuid,
) -> bool {
    match entity_checker(state, entity_type) {
        Some(checker) => checker.exists(entity_id, tenant_id).await,
        None => false,
    }
}

/// Validate that `(entity_type, entity_id)` exists and belongs to the
/// caller's tenant. Unknown entity types fail closed with a clear message.
async fn validate_entity_reference(
    state: &AppState,
    entity_type: &str,
    entity_id: Uuid,
    tenant_id: Uuid,
) -> Result<()> {
    let Some(checker) = entity_checker(state, entity_type) else {
        return Err(SenseiError::Validation(format!(
            "entity_type '{entity_type}' is not supported for attachments. \
             Supported entity types: {SUPPORTED_ENTITY_TYPES}"
        )));
    };

    if !checker.exists(entity_id, tenant_id).await {
        return Err(SenseiError::NotFound(format!(
            "{entity_type} {entity_id} does not exist in tenant {tenant_id}"
        )));
    }
    Ok(())
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Upload a file attachment.
///
/// Accepts multipart form data with a file field named "file" plus
/// `entity_type` and `entity_id` text fields (any order). The file field is
/// streamed chunk-by-chunk into a temporary file while enforcing the running
/// byte limit and computing the SHA-256 digest (never fully buffered in
/// memory), then the temp file is streamed into the storage service under an
/// opaque UUID key.
pub async fn upload_attachment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<UploadedAttachment>> {
    user.require_permission("attachments:manage")?;
    let mut tmp_path: Option<std::path::PathBuf> = None;
    let outcome = upload_inner(&state, user, &mut multipart, &mut tmp_path).await;
    // Best-effort cleanup of the spooled temp file on every path.
    if let Some(path) = &tmp_path {
        let _ = tokio::fs::remove_file(path).await;
    }
    outcome
}

async fn upload_inner(
    state: &AppState,
    user: AuthenticatedUser,
    multipart: &mut Multipart,
    tmp_path: &mut Option<std::path::PathBuf>,
) -> Result<Json<UploadedAttachment>> {
    let mut file_name = String::new();
    let mut file_size: i64 = 0;
    let mut digest = String::new();
    let mut entity_type: Option<String> = None;
    let mut entity_id: Option<Uuid> = None;
    let body_limit = state.config.api.body_limit;

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| SenseiError::Validation(format!("Failed to read multipart field: {e}")))?
    {
        match field.name().unwrap_or("") {
            "file" => {
                file_name = field.file_name().unwrap_or("unnamed").to_string();
                let spool = std::env::temp_dir().join(format!("sensei-upload-{}", Uuid::new_v4()));
                let (size, digest_hex) = stream_file_field(field, &spool, body_limit).await?;
                file_size = size;
                digest = digest_hex;
                *tmp_path = Some(spool);
            }
            "entity_type" => {
                let text = field
                    .text()
                    .await
                    .map_err(|e| SenseiError::Validation(format!("Failed to read field: {e}")))?
                    .trim()
                    .to_ascii_lowercase();
                entity_type = Some(text);
            }
            "entity_id" => {
                let id_str = field
                    .text()
                    .await
                    .map_err(|e| SenseiError::Validation(format!("Failed to read field: {e}")))?
                    .trim()
                    .to_string();
                entity_id =
                    Some(Uuid::parse_str(&id_str).map_err(|_| {
                        SenseiError::Validation("Invalid entity_id UUID".to_string())
                    })?);
            }
            _ => {}
        }
    }

    if file_size == 0 {
        return Err(SenseiError::Validation("No file data provided".to_string()));
    }
    let entity_id =
        entity_id.ok_or_else(|| SenseiError::Validation("entity_id is required".to_string()))?;
    let entity_type = entity_type
        .filter(|t| !t.is_empty())
        .ok_or_else(|| SenseiError::Validation("entity_type is required".to_string()))?;

    // Validate the referenced entity exists AND belongs to the caller's
    // tenant BEFORE anything is stored (the blob is still only in the temp
    // file at this point). Unknown entity types fail closed.
    validate_entity_reference(state, &entity_type, entity_id, user.tenant_id).await?;

    // Twenty-ninth-audit Wave B item 11: attachments inherit their
    // PARENT's authorization — uploads additionally require the parent's
    // canonical manage permission (site-scoped in DB deployments) before
    // any byte is stored.
    require_parent_manage(state, &user, &entity_type, entity_id).await?;

    // Server-side content type from the extension allowlist — the browser
    // MIME type is never trusted.
    let file_name = sanitize_file_name(&file_name);
    let Some(ext) = file_extension(&file_name) else {
        return Err(SenseiError::Validation(format!(
            "File '{file_name}' has no supported extension. Allowed: pdf, png, jpeg, txt, csv, xlsx, docx, md"
        )));
    };
    let Some(content_type) = content_type_for_extension(ext) else {
        return Err(SenseiError::Validation(format!(
            "File extension '.{ext}' is not allowed. Allowed: pdf, png, jpeg, txt, csv, xlsx, docx, md"
        )));
    };

    // Store the blob under an opaque server-generated key by streaming the
    // spooled temp file into the storage service. Caller-supplied names
    // never reach the storage namespace.
    let spool_path = tmp_path
        .as_ref()
        .ok_or_else(|| SenseiError::Internal("missing spooled upload file".to_string()))?;
    let file = tokio::fs::File::open(spool_path)
        .await
        .map_err(SenseiError::Io)?;
    let reader: Box<dyn tokio::io::AsyncRead + Unpin + Send> = Box::new(file);
    let object = state
        .storage_service
        .store_opaque_stream(user.tenant_id, reader, content_type)
        .await?;

    let now = Utc::now();
    let attachment = Attachment {
        id: new_id(),
        tenant_id: user.tenant_id,
        entity_type: entity_type.clone(),
        entity_id,
        file_name,
        content_type: content_type.to_string(),
        file_size,
        storage_path: object.key,
        uploaded_by: user.user_id,
        created_at: now,
    };

    // Store metadata in the typed attachment repository (PostgreSQL is the
    // source of truth — no process-local snapshot caching). If the metadata
    // write fails AFTER the blob was stored, compensate by deleting the
    // orphaned object so storage and metadata can never diverge.
    if let Err(e) = state.attachment_repo.put(&attachment).await {
        tracing::error!(error = %e, attachment_id = %attachment.id, "Failed to persist attachment metadata — compensating blob delete");
        let _ = state
            .storage_service
            .delete(user.tenant_id, &attachment.storage_path)
            .await;
        return Err(SenseiError::Internal(
            "Failed to persist attachment metadata".to_string(),
        ));
    }

    Ok(Json(UploadedAttachment::from_attachment(
        &attachment,
        digest,
    )))
}

/// Stream a multipart file field chunk-by-chunk into `spool_path`, enforcing
/// the running byte limit and computing the SHA-256 digest. Returns
/// `(size_bytes, digest_hex)`. The spool file is removed on error.
async fn stream_file_field(
    mut field: axum::extract::multipart::Field<'_>,
    spool_path: &std::path::Path,
    body_limit: usize,
) -> Result<(i64, String)> {
    let mut hasher = Sha256::new();
    let mut total: usize = 0;

    let result = async {
        let mut file = tokio::fs::File::create(spool_path)
            .await
            .map_err(SenseiError::Io)?;
        loop {
            let chunk = field
                .chunk()
                .await
                .map_err(|e| SenseiError::Validation(format!("Failed to stream file data: {e}")))?;
            let Some(chunk) = chunk else { break };
            total += chunk.len();
            if total > body_limit {
                return Err(SenseiError::Validation(format!(
                    "File size exceeds the maximum allowed size of {} bytes",
                    body_limit
                )));
            }
            hasher.update(&chunk);
            tokio::io::AsyncWriteExt::write_all(&mut file, &chunk)
                .await
                .map_err(SenseiError::Io)?;
        }
        Ok::<_, SenseiError>(())
    }
    .await;

    if let Err(e) = result {
        let _ = tokio::fs::remove_file(spool_path).await;
        return Err(e);
    }

    Ok((total as i64, hex::encode(hasher.finalize())))
}

/// List attachments for a given entity type and ID.
///
/// The caller must hold `attachments:read` AND be able to read the
/// parent entity (`require_parent_read`) — the check runs BEFORE any
/// attachment row is listed, so enumerating a parent the caller may not
/// read (or that does not exist) yields no metadata at all.
pub async fn list_attachments(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((entity_type, entity_id)): Path<(String, Uuid)>,
    Query(params): Query<ListAttachmentsParams>,
) -> Result<Json<PaginatedResponse<Attachment>>> {
    user.require_permission("attachments:read")?;
    require_parent_read(&state, &user, &entity_type, entity_id).await?;
    let attachments = state
        .attachment_repo
        .list(user.tenant_id, &entity_type, entity_id)
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to list attachments");
            SenseiError::Internal("Failed to read attachments".to_string())
        })?;
    let result = PaginatedResponse::new(attachments, params.page, params.per_page);
    Ok(Json(result))
}

/// Download an attachment by ID.
///
/// Authenticates the user, resolves the metadata under the user's tenant,
/// then — twenty-ninth-audit Wave B item 11 — requires READ access to the
/// attachment's PARENT entity (`require_parent_read`) BEFORE any
/// presigning or buffered retrieval: a known attachment UUID never
/// bypasses the parent's authorization. The bytes are then retrieved from
/// the shared storage backend and streamed with a server-authoritative
/// content type and a safe `Content-Disposition`.
pub async fn download_attachment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<axum::response::Response> {
    user.require_permission("attachments:read")?;
    use axum::http::header::{CONTENT_DISPOSITION, CONTENT_TYPE};

    let attachment = state
        .attachment_repo
        .get(user.tenant_id, id)
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to read attachment metadata");
            SenseiError::Internal("Failed to read attachment".to_string())
        })?
        .ok_or_else(|| SenseiError::NotFound(format!("Attachment {id} not found")))?;

    // Parent authorization FIRST: without it no presigned URL is issued
    // and no byte is retrieved (metadata has already revealed only the
    // row the tenant owns; a denied/unknown parent stops the download).
    require_parent_read(&state, &user, &attachment.entity_type, attachment.entity_id).await?;

    // Prefer a short-lived signed download (true streaming at the storage
    // backend); fall back to buffered retrieval when unsupported.
    if let Some(url) = state
        .storage_service
        .get_presigned_url(user.tenant_id, &attachment.storage_path, 300)
        .await?
    {
        use axum::response::IntoResponse;
        return Ok(axum::response::Redirect::temporary(&url).into_response());
    }

    let bytes = state
        .storage_service
        .retrieve(user.tenant_id, &attachment.storage_path)
        .await?;

    // Server-authoritative content type (mapped from the stored type —
    // never trust a browser-supplied MIME for security-sensitive rendering).
    let content_type = if attachment.content_type.is_empty() {
        "application/octet-stream".to_string()
    } else {
        attachment.content_type.clone()
    };

    // Safe Content-Disposition: filename is sanitized at upload time and the
    // header value is percent-encoded.
    let disposition = format!(
        "attachment; filename=\"{}\"",
        attachment.file_name.replace('"', "")
    );

    let mut response = axum::response::Response::new(axum::body::Body::from(bytes));
    response.headers_mut().insert(
        CONTENT_TYPE,
        content_type
            .parse()
            .map_err(|_| SenseiError::Internal("Invalid content type".to_string()))?,
    );
    response.headers_mut().insert(
        CONTENT_DISPOSITION,
        disposition
            .parse()
            .map_err(|_| SenseiError::Internal("Invalid disposition".to_string()))?,
    );
    Ok(response)
}

/// Delete an attachment by ID.
///
/// Thirtieth-audit item 14: deletion follows a two-phase lifecycle so a
/// transient failure can never leave active metadata referencing a missing
/// object (the pre-existing order — object delete first, then metadata
/// delete — had exactly that failure window when the metadata delete
/// failed after the object delete succeeded):
///
/// ```text
/// active ──tombstone()──▶ deleting ──object delete──▶ metadata remove
///                            │  ▲
///                            │  │ (object delete failed: record stays
///                            │  └─  tombstoned; a later DELETE on the same
///                            │      id resumes here, idempotently — an
///                            │      object that is already gone (NotFound)
///                            │      counts as success)
///                            └──▶ next delete attempt completes cleanup
/// ```
///
/// While a record is `deleting` it is hidden from downloads and listings
/// (the metadata repository filters it out), so a mid-deletion attachment
/// is never observable in an inconsistent state. This is an explicit retry
/// surface (resume-on-next-delete) rather than a background worker: blob
/// cleanup is a single per-record storage call with no bus/outbox fan-out,
/// and the repository lifecycle registry is process-local — a durable
/// cross-restart sweep would need a lifecycle column plus a scheduled
/// worker (out of scope, documented in `attachment_repository.rs`).
///
/// The caller must hold `attachments:manage` AND be able to MANAGE the
/// attachment's parent entity (`require_parent_manage`) — a known
/// attachment UUID never bypasses the parent's authorization. The parent
/// check runs on the ACTIVE and the TOMBSTONED record alike (the tombstone
/// keeps the parent coordinates), so resuming an interrupted deletion is
/// authorized exactly like the original delete.
pub async fn delete_attachment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("attachments:manage")?;

    // Resolve the record: the public read path (get) hides tombstoned
    // records, so an attachment whose deletion was interrupted is found
    // through the deletion-completion read instead. An id that is neither
    // active nor tombstoned is a plain 404.
    let active = state
        .attachment_repo
        .get(user.tenant_id, id)
        .await
        .map_err(|e| {
            tracing::error!(error = %e, "Failed to read attachment metadata");
            SenseiError::Internal("Failed to read attachment".to_string())
        })?;
    let attachment = match active {
        Some(attachment) => {
            // Phase 1 (active → deleting): tombstone BEFORE any object
            // removal. If this write fails the record is untouched and a
            // retry of the whole delete remains safe.
            state
                .attachment_repo
                .tombstone(&attachment)
                .await
                .map_err(|e| {
                    tracing::error!(
                        error = %e,
                        attachment_id = %id,
                        "Failed to tombstone attachment metadata before object deletion"
                    );
                    SenseiError::Internal("Failed to start attachment deletion".to_string())
                })?;
            Some(attachment)
        }
        None => state.attachment_repo.get_deleting(user.tenant_id, id).await,
    };
    let Some(attachment) = attachment else {
        return Err(SenseiError::NotFound(format!("Attachment {id} not found")));
    };

    // Parent manage authorization BEFORE the blob is deleted (runs for
    // active and tombstoned records alike): an attachment whose parent the
    // caller may not manage survives.
    require_parent_manage(&state, &user, &attachment.entity_type, attachment.entity_id).await?;

    // Phase 2 (object delete): remove the blob. NotFound means the object
    // is already gone (an earlier attempt deleted it before failing on the
    // metadata step) — idempotent completion treats it as success. Any
    // other failure leaves the tombstone in place: the record is hidden
    // from downloads/listings and a later DELETE resumes the cleanup.
    match state
        .storage_service
        .delete(user.tenant_id, &attachment.storage_path)
        .await
    {
        Ok(()) => {}
        Err(SenseiError::NotFound(_)) => {
            tracing::warn!(
                attachment_id = %id,
                storage_path = %attachment.storage_path,
                "Attachment object already absent during deletion — completing idempotently"
            );
        }
        Err(e) => {
            tracing::error!(
                error = %e,
                attachment_id = %id,
                storage_path = %attachment.storage_path,
                "Attachment object delete failed — record stays tombstoned for a later retry"
            );
            return Err(e);
        }
    }

    // Phase 3 (metadata remove): finalize the lifecycle. The repository
    // delete clears both the active row and the tombstone and is
    // idempotent (a row already removed elsewhere yields Ok(false)).
    state
        .attachment_repo
        .delete(user.tenant_id, id)
        .await
        .map_err(|e| {
            tracing::error!(error = %e, attachment_id = %id, "Failed to delete attachment metadata");
            SenseiError::Internal("Failed to delete attachment metadata".to_string())
        })?;

    Ok(Json(()))
}

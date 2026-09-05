//! End-to-end tests for Attachment endpoints.
//!
//! Covers: upload, list, delete — plus the twenty-ninth-audit Wave B
//! item 11 parent-authorization contract, the thirtieth-audit P0
//! items 12-13 scope-preservation contract, the thirtieth-audit item 14
//! deletion-reliability lifecycle, and item 30 isolated test storage:
//!
//! * attachments inherit their PARENT's authorization — a known
//!   attachment UUID never bypasses the parent check (orphan parents are
//!   denied with 404, and listing requires a readable parent);
//! * deletion follows the item-14 lifecycle (`active → deleting →
//!   object delete → metadata remove`): a simulated object-delete failure
//!   tombstones the record — invisible to downloads and listings — and a
//!   later delete attempt resumes and completes the cleanup idempotently;
//! * every test writes blobs into a per-test storage root under the OS
//!   temp directory (never `crates/sensei-api/data/uploads`), so test
//!   runs cannot dirty the repository (item 30);
//! * the site-scoped assertions (site-B parent denied for a site-A user,
//!   site-B NCR denied even with `ncr:read`, a WC-exact search never
//!   returning same-site sibling work centers, and the tenant-wide proof
//!   still requiring parent existence) require a database with
//!   role-slot assignments — the in-memory test harness has no site
//!   rows, so those tests are DB-gated skips (they run when
//!   `DATABASE_URL_TEST` is set, following the
//!   `sensei-db/tests/db_contract.rs` gate convention).

use async_trait::async_trait;
use axum::http::StatusCode;
use chrono::Utc;
use sensei_api::stores::{Attachment, Opportunity};
use sensei_core::error::{Result as SenseiResult, SenseiError};
use sensei_core::types::EntityId;
use sensei_services::storage::file_storage::StoredObject;
use sensei_services::storage::{FileStorageService, LocalStorageService};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU8, Ordering};
use std::sync::Arc;
use uuid::Uuid;

mod common;

// ── Helpers ─────────────────────────────────────────────────────────────────

/// Seed an opportunity parent in the caller's tenant (in-memory store).
async fn seed_opportunity(app: &common::TestApp, tenant_id: Uuid) -> Uuid {
    let id = Uuid::new_v4();
    let now = Utc::now();
    let opp = Opportunity {
        id,
        tenant_id,
        title: "Seed opportunity".to_string(),
        description: "Parent for attachment tests".to_string(),
        customer_id: Uuid::new_v4(),
        customer_name: "Seed Customer".to_string(),
        stage: "qualification".to_string(),
        probability: 0.5,
        expected_value: 1000.0,
        currency: "USD".to_string(),
        expected_close_date: None,
        assigned_to: None,
        notes: String::new(),
        created_by: Uuid::new_v4(),
        created_at: now,
        updated_at: now,
    };
    {
        let mut store = app.state.opportunities.write(tenant_id).await;
        store.insert(id, opp.clone());
    }
    id
}

/// Seed an attachment metadata row (in-memory repository) for the parent,
/// storing the blob through the storage service so downloads can resolve.
async fn seed_attachment(
    app: &common::TestApp,
    tenant_id: Uuid,
    entity_type: &str,
    entity_id: Uuid,
) -> Uuid {
    let object = app
        .state
        .storage_service
        .store_opaque(tenant_id, b"attachment-bytes", "application/pdf")
        .await
        .expect("blob must store");
    let id = Uuid::new_v4();
    let attachment = Attachment {
        id,
        tenant_id,
        entity_type: entity_type.to_string(),
        entity_id,
        file_name: "report.pdf".to_string(),
        content_type: "application/pdf".to_string(),
        file_size: 16,
        storage_path: object.key,
        uploaded_by: Uuid::new_v4(),
        created_at: Utc::now(),
    };
    app.state
        .attachment_repo
        .put(&attachment)
        .await
        .expect("attachment metadata must seed");
    id
}

// ── Isolated test storage (thirtieth-audit item 30) ────────────────────────
//
// The default local storage root (`./data/uploads` under the crate) is
// runtime state inside the repository: test runs that write blobs through
// it dirty the working tree. Every test below therefore builds its app
// with [`new_app_with_uploads`], which constructs the application state
// with a storage service rooted in a per-test directory under the OS temp
// dir BEFORE the router is built (the router captures the state's
// storage service, so a post-hoc field swap would not reach handlers).
// The returned guard removes the directory when the test ends (including
// on panic).

/// Removes the per-test uploads directory on drop.
struct IsolatedUploads(PathBuf);

impl Drop for IsolatedUploads {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

/// Build a [`common::TestApp`] whose blob storage is rooted OUTSIDE the
/// repository (a fresh per-test directory under the OS temp dir) and is
/// fault-free.
async fn new_app_with_isolated_uploads() -> (common::TestApp, IsolatedUploads) {
    new_app_with_uploads(FAULT_NONE).await
}

/// Build a [`common::TestApp`] like [`new_app_with_isolated_uploads`],
/// wrapping the per-test storage service in a [`FaultyDeleteStorage`]
/// armed with `mode` — used by the deletion-lifecycle tests to simulate
/// an object-store outage from the very first route call.
async fn new_app_with_uploads(mode: u8) -> (common::TestApp, IsolatedUploads) {
    // Mirror `common::setup::TestApp::new`, but inject the storage root
    // before `build_router` captures the state.
    common::setup::pin_test_environment();
    let root = std::env::temp_dir().join(format!("sensei-uploads-test-{}", Uuid::new_v4()));
    let password = "TestAdmin123!".to_string();
    let hash = sensei_auth::password::hash_password(&password).expect("hash admin password");
    let tenant_id = Uuid::new_v4();

    let users_service: Arc<dyn sensei_services::users::UsersService> =
        Arc::new(sensei_services::users::InMemoryUsersService::with_admin(
            "admin@sensei.test",
            "Admin User",
            &hash,
            tenant_id,
        ));
    let config = sensei_core::config::AppConfig::from_env()
        .expect("test configuration must load under pinned env");
    let mut state = sensei_api::AppState::new(config, users_service);

    let inner = Arc::new(LocalStorageService::new(&root)) as Arc<dyn FileStorageService>;
    if mode == FAULT_NONE {
        state.storage_service = inner;
    } else {
        let faulty = FaultyDeleteStorage::new(inner);
        faulty.set_mode(mode);
        state.storage_service = Arc::new(faulty);
    }

    // Seed the admin's tenant record (mirror of `TestApp::new`) and keep
    // the credentials so `login_as_admin` works on the returned app.
    state
        .tenants_service
        .create_tenant(sensei_core::domain::entities::Tenant {
            id: tenant_id,
            name: "Test Admin Tenant".to_string(),
            slug: format!("test-admin-{}", tenant_id.as_simple()),
            is_active: true,
            features: Vec::new(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        })
        .await
        .expect("Failed to seed admin tenant");
    let admin = state
        .users_service
        .find_by_email("admin@sensei.test")
        .await
        .expect("Admin user not found");

    let mut app = common::TestApp::from_state(state);
    app.admin_password = password;
    app.admin_tenant_id = tenant_id;
    app.admin_user_id = admin.id;
    (app, IsolatedUploads(root))
}

// ── Storage fault injection (thirtieth-audit item 14) ──────────────────────

/// Fault modes for [`FaultyDeleteStorage`].
const FAULT_NONE: u8 = 0;
const FAULT_ONCE: u8 = 1;
const FAULT_ALWAYS: u8 = 2;

/// Storage double that delegates every call and fails `delete` on demand,
/// simulating a transient object-store outage for the deletion-lifecycle
/// tests.
#[derive(Clone)]
struct FaultyDeleteStorage {
    inner: Arc<dyn FileStorageService>,
    mode: Arc<AtomicU8>,
}

impl FaultyDeleteStorage {
    fn new(inner: Arc<dyn FileStorageService>) -> Self {
        Self {
            inner,
            mode: Arc::new(AtomicU8::new(FAULT_NONE)),
        }
    }

    fn set_mode(&self, mode: u8) {
        self.mode.store(mode, Ordering::SeqCst);
    }
}

#[async_trait]
impl FileStorageService for FaultyDeleteStorage {
    async fn store(
        &self,
        tenant_id: EntityId,
        path: &str,
        data: &[u8],
        content_type: &str,
    ) -> SenseiResult<String> {
        self.inner.store(tenant_id, path, data, content_type).await
    }

    async fn retrieve(&self, tenant_id: EntityId, storage_path: &str) -> SenseiResult<Vec<u8>> {
        self.inner.retrieve(tenant_id, storage_path).await
    }

    async fn delete(&self, tenant_id: EntityId, storage_path: &str) -> SenseiResult<()> {
        match self.mode.load(Ordering::SeqCst) {
            FAULT_ONCE => {
                self.mode.store(FAULT_NONE, Ordering::SeqCst);
                Err(SenseiError::ExternalService(
                    "simulated object-store outage (test)".to_string(),
                ))
            }
            FAULT_ALWAYS => Err(SenseiError::ExternalService(
                "simulated object-store outage (test)".to_string(),
            )),
            _ => self.inner.delete(tenant_id, storage_path).await,
        }
    }

    async fn get_presigned_url(
        &self,
        tenant_id: EntityId,
        storage_path: &str,
        expires_in_secs: u64,
    ) -> SenseiResult<Option<String>> {
        self.inner
            .get_presigned_url(tenant_id, storage_path, expires_in_secs)
            .await
    }

    async fn store_opaque_stream(
        &self,
        tenant_id: EntityId,
        data: Box<dyn tokio::io::AsyncRead + Unpin + Send>,
        content_type_hint: &str,
    ) -> SenseiResult<StoredObject> {
        self.inner
            .store_opaque_stream(tenant_id, data, content_type_hint)
            .await
    }

    fn clone_box(&self) -> Box<dyn FileStorageService> {
        Box::new(self.clone())
    }
}

// ── Legacy surface tests ────────────────────────────────────────────────────

#[tokio::test]
async fn test_upload_attachment() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    // Upload endpoint may expect multipart; try JSON-based approach
    let body = serde_json::json!({
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "data": "dGVzdCBjb250ZW50",  // base64 "test content"
        "entity_type": "work_order",
        "entity_id": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated("/api/v1/attachments/upload", &token, body);
    let resp = app.send_request(req).await;
    // May accept JSON or require multipart; either way endpoint responds
    let status = resp.status();
    assert!(
        status == StatusCode::OK
            || status == StatusCode::UNSUPPORTED_MEDIA_TYPE
            || status == StatusCode::BAD_REQUEST
    );
}

#[tokio::test]
async fn test_list_attachments() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    // In-memory (no DB) deployments have no site rows: the work-order
    // parent proof is dev-permissive, so listing a nonexistent parent
    // returns an empty page (existing behavior).
    let entity_id = uuid::Uuid::new_v4().to_string();
    let req = app.get_authenticated(
        &format!("/api/v1/attachments/work_order/{}", entity_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_delete_attachment() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let req = app.delete_authenticated(
        "/api/v1/attachments/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

// ── Parent authorization (Wave B item 11) ──────────────────────────────────

/// A known attachment UUID whose parent does not exist (orphan row) must
/// NOT bypass the parent read check: download is 404 even though the
/// metadata row is present and the caller holds `attachments:read`.
#[tokio::test]
async fn test_download_known_uuid_does_not_bypass_missing_parent() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    // No parent seeded — the attachment metadata is an orphan.
    let orphan_parent = Uuid::new_v4();
    let attachment_id = seed_attachment(&app, tenant, "opportunity", orphan_parent).await;

    let req = app.get_authenticated(
        &format!("/api/v1/attachments/{attachment_id}/download"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "a known attachment UUID must not bypass the missing-parent check"
    );
}

/// Listing attachments of a parent the caller may not read (a nonexistent
/// store-backed parent) is denied BEFORE any metadata row is returned.
#[tokio::test]
async fn test_list_requires_readable_parent() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let missing_parent = Uuid::new_v4();

    let req = app.get_authenticated(
        &format!("/api/v1/attachments/opportunity/{missing_parent}"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

/// Positive control: an existing, readable parent (opportunity) lists its
/// attachments and downloads them; parent authorization passes.
#[tokio::test]
async fn test_download_and_list_with_existing_parent() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    let parent = seed_opportunity(&app, tenant).await;
    let attachment_id = seed_attachment(&app, tenant, "opportunity", parent).await;

    // List: parent readable → 200 with the seeded row.
    let req = app.get_authenticated(&format!("/api/v1/attachments/opportunity/{parent}"), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"].as_u64().unwrap_or(0), 1);

    // Download: parent readable → the blob resolves.
    let req = app.get_authenticated(
        &format!("/api/v1/attachments/{attachment_id}/download"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

/// Deleting an attachment whose parent may not be managed is denied with
/// 404/403 — the known UUID does not bypass the parent manage check.
#[tokio::test]
async fn test_delete_known_uuid_does_not_bypass_missing_parent() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    // Admin holds knowledge:manage; the parent row does not exist.
    let orphan_parent = Uuid::new_v4();
    let attachment_id = seed_attachment(&app, tenant, "knowledge_pack", orphan_parent).await;

    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "a known attachment UUID must not bypass the missing-parent manage check"
    );
}

// ── Deletion lifecycle (thirtieth-audit item 14) ───────────────────────────
//
// DELETE runs `active → deleting → object delete → metadata remove`. The
// tests below drive the HTTP route and inspect the metadata repository +
// storage service directly for the resulting state.

/// (a) A successful delete removes the object AND the metadata: the row
/// disappears from the public read path and from the tombstone registry,
/// the blob no longer resolves, listings become empty, and a second DELETE
/// is a plain 404.
#[tokio::test]
async fn test_delete_success_removes_object_and_metadata() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    let parent = seed_opportunity(&app, tenant).await;
    let attachment_id = seed_attachment(&app, tenant, "opportunity", parent).await;
    let attachment = app
        .state
        .attachment_repo
        .get(tenant, attachment_id)
        .await
        .expect("repo read")
        .expect("attachment seeded");
    // Positive control: the blob resolves before the delete.
    app.state
        .storage_service
        .retrieve(tenant, &attachment.storage_path)
        .await
        .expect("blob must be stored before deletion");

    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "an authorized delete of an active attachment must succeed"
    );

    // Metadata: gone from the read path AND from the tombstone registry.
    assert!(
        app.state
            .attachment_repo
            .get(tenant, attachment_id)
            .await
            .expect("repo read")
            .is_none(),
        "metadata must be removed after a successful delete"
    );
    assert!(
        app.state
            .attachment_repo
            .get_deleting(tenant, attachment_id)
            .await
            .is_none(),
        "no tombstone may remain after a successful delete"
    );
    assert_eq!(app.state.attachment_repo.deleting_count(tenant).await, 0);

    // Object: gone from storage.
    let err = app
        .state
        .storage_service
        .retrieve(tenant, &attachment.storage_path)
        .await
        .expect_err("blob must be removed by the delete");
    assert!(
        matches!(err, SenseiError::NotFound(_)),
        "blob removal must leave a NotFound, got {err:?}"
    );

    // Listing of the parent no longer shows the attachment.
    let req = app.get_authenticated(&format!("/api/v1/attachments/opportunity/{parent}"), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"].as_u64().unwrap_or(99), 0);

    // A repeated DELETE is a plain 404 (nothing left to resume).
    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

/// (b) A simulated object-delete failure leaves the record TOMBSTONED —
/// hidden from downloads and listings, with the blob still present — and
/// the next DELETE on the same id resumes and completes the cleanup.
#[tokio::test]
async fn test_delete_object_failure_tombstones_and_retry_completes() {
    let (app, _uploads) = new_app_with_uploads(FAULT_ONCE).await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    let parent = seed_opportunity(&app, tenant).await;

    let attachment_id = seed_attachment(&app, tenant, "opportunity", parent).await;
    let attachment = app
        .state
        .attachment_repo
        .get(tenant, attachment_id)
        .await
        .expect("repo read")
        .expect("attachment seeded");
    let storage_path = attachment.storage_path.clone();

    // First DELETE: the object-store delete fails → 5xx, record tombstoned.
    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert!(
        resp.status().is_server_error(),
        "an object-store failure must surface as a 5xx, got {}",
        resp.status()
    );

    // The metadata row survives as a tombstone: hidden from the public
    // read path but reachable through the deletion-completion read, and
    // the blob is untouched (the failed delete never removed it).
    assert!(
        app.state
            .attachment_repo
            .get(tenant, attachment_id)
            .await
            .expect("repo read")
            .is_none(),
        "a tombstoned attachment must be hidden from the public read path"
    );
    let tombstone = app
        .state
        .attachment_repo
        .get_deleting(tenant, attachment_id)
        .await
        .expect("the interrupted deletion must leave a tombstone record");
    assert_eq!(
        tombstone.storage_path, storage_path,
        "the tombstone keeps the storage path for the retry"
    );
    assert_eq!(app.state.attachment_repo.deleting_count(tenant).await, 1);
    app.state
        .storage_service
        .retrieve(tenant, &storage_path)
        .await
        .expect("the blob must still be present after the failed delete");

    // (c) A tombstoned attachment is not downloadable and not listable.
    let req = app.get_authenticated(
        &format!("/api/v1/attachments/{attachment_id}/download"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "downloading a tombstoned attachment must not be possible"
    );
    let req = app.get_authenticated(&format!("/api/v1/attachments/opportunity/{parent}"), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(
        json["total"].as_u64().unwrap_or(99),
        0,
        "listing must hide a tombstoned attachment"
    );

    // Retry: the next DELETE resumes the interrupted deletion and
    // completes it — object and metadata are both gone afterwards.
    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "the retry of a tombstoned attachment must complete the deletion"
    );
    assert!(
        app.state
            .attachment_repo
            .get_deleting(tenant, attachment_id)
            .await
            .is_none(),
        "no tombstone may remain after the completed retry"
    );
    assert_eq!(app.state.attachment_repo.deleting_count(tenant).await, 0);
    let err = app
        .state
        .storage_service
        .retrieve(tenant, &storage_path)
        .await
        .expect_err("the retry must remove the blob");
    assert!(matches!(err, SenseiError::NotFound(_)));
}

/// (c) While an attachment is tombstoned (object delete keeps failing),
/// downloads 404 and listings hide the row — the lifecycle never exposes
/// a mid-deletion attachment.
#[tokio::test]
async fn test_tombstoned_attachment_is_not_downloadable_or_listable() {
    let (app, _uploads) = new_app_with_uploads(FAULT_ALWAYS).await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    let parent = seed_opportunity(&app, tenant).await;

    let attachment_id = seed_attachment(&app, tenant, "opportunity", parent).await;

    // Every object delete fails → the DELETE keeps failing and the record
    // stays tombstoned.
    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert!(resp.status().is_server_error());
    assert!(
        app.state
            .attachment_repo
            .get_deleting(tenant, attachment_id)
            .await
            .is_some(),
        "a persistently failing object delete must leave the tombstone in place"
    );
    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert!(resp.status().is_server_error());

    // Download: 404 (indistinguishable from a nonexistent attachment).
    let req = app.get_authenticated(
        &format!("/api/v1/attachments/{attachment_id}/download"),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);

    // Listing: the tombstoned row is not part of the parent's listing.
    let req = app.get_authenticated(&format!("/api/v1/attachments/opportunity/{parent}"), &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: serde_json::Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"].as_u64().unwrap_or(99), 0);
    assert_eq!(
        json["data"].as_array().map(Vec::len).unwrap_or(99),
        0,
        "listing data must not contain the tombstone"
    );
}

/// Interrupted-deletion recovery: a tombstone whose object was ALREADY
/// removed (an earlier attempt deleted the blob and failed before the
/// metadata step) is completed idempotently — the object-store NotFound
/// counts as success and the metadata row is removed.
#[tokio::test]
async fn test_delete_resume_completes_when_object_already_gone() {
    let (app, _uploads) = new_app_with_isolated_uploads().await;
    let token = app.login_as_admin().await;
    let tenant = app.admin_tenant_id;
    let parent = seed_opportunity(&app, tenant).await;
    let attachment_id = seed_attachment(&app, tenant, "opportunity", parent).await;
    let attachment = app
        .state
        .attachment_repo
        .get(tenant, attachment_id)
        .await
        .expect("repo read")
        .expect("attachment seeded");
    let storage_path = attachment.storage_path.clone();

    // Reproduce the state of a deletion interrupted between phase 2
    // (object delete — succeeded) and phase 3 (metadata remove): the blob
    // is already gone and the metadata row is tombstoned.
    app.state
        .storage_service
        .delete(tenant, &storage_path)
        .await
        .expect("direct blob removal (simulated phase 2)");
    app.state
        .attachment_repo
        .tombstone(&attachment)
        .await
        .expect("tombstone (simulated phase 1)");

    // A later DELETE on the same id resumes: the already-absent object is
    // treated as success and the metadata removal completes.
    let req = app.delete_authenticated(&format!("/api/v1/attachments/{attachment_id}"), &token);
    let resp = app.send_request(req).await;
    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "resuming a deletion whose object is already gone must succeed"
    );
    assert!(
        app.state
            .attachment_repo
            .get_deleting(tenant, attachment_id)
            .await
            .is_none(),
        "the resumed deletion must clear the tombstone"
    );
    assert!(
        app.state
            .attachment_repo
            .get(tenant, attachment_id)
            .await
            .expect("repo read")
            .is_none(),
        "the resumed deletion must remove the metadata row"
    );
    let err = app
        .state
        .storage_service
        .retrieve(tenant, &storage_path)
        .await
        .expect_err("blob must remain absent");
    assert!(matches!(err, SenseiError::NotFound(_)));
}

// ── DB-gated site-scope tests ───────────────────────────────────────────────

/// Connect to the CI-provided test database. Returns None when the env
/// var is absent so the local in-memory suite stays green (the DB-gated
/// assertions run in CI, mirroring `sensei-db/tests/db_contract.rs`).
async fn db_pool() -> Option<sqlx::PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — site-scope attachment gate runs in CI");
        return None;
    };
    match sqlx::PgPool::connect(&url).await {
        Ok(pool) => Some(pool),
        Err(e) => {
            eprintln!("SKIP: cannot reach DATABASE_URL_TEST ({e})");
            None
        }
    }
}

/// The DB-gated tests share one database; migrations must apply before
/// any seed. A per-binary lock serializes the migration step (the schema
/// work is idempotent once applied, so later tests skip it instantly).
static DB_MIGRATE_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

/// Apply the migration chain when the database has none (no-op when
/// already migrated). Returns false (test skips) when the chain cannot
/// run — mirroring the pre-existing DB-gated tests.
async fn ensure_migrations(pool: &sqlx::PgPool) -> bool {
    let _guard = DB_MIGRATE_LOCK.lock().await;
    match sensei_db::migrations::run_migrations(pool).await {
        Ok(_) => true,
        Err(e) => {
            eprintln!("SKIP: migration chain unavailable for attachment scope gate ({e})");
            false
        }
    }
}

/// Build the DB-backed application state the authorization proofs and
/// the database search resolve against (typed repositories + scope
/// resolution reach the same database).
fn db_state(pool: &std::sync::Arc<sqlx::PgPool>) -> sensei_api::AppState {
    common::setup::pin_test_environment();
    let config = sensei_core::config::AppConfig::from_env()
        .expect("test configuration must load under pinned env");
    let users_service =
        std::sync::Arc::new(sensei_services::users::InMemoryUsersService::with_admin(
            "dbgate@sensei.test",
            "Db Gate",
            "x",
            Uuid::new_v4(),
        ));
    sensei_api::AppState::new(config, users_service).with_db_pool(pool.clone())
}

/// Seed a tenant + two sites (plus `extra_sites` additional ones) and
/// return their ids.
async fn seed_tenant_and_sites(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    extra_sites: usize,
) -> Vec<Uuid> {
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
        .bind(tenant_id)
        .bind("P0 Attachment Tenant")
        .bind(format!("p0-att-{tenant_id}"))
        .execute(pool)
        .await
        .expect("tenant seed");
    let mut sites: Vec<Uuid> = Vec::new();
    for i in 0..(2 + extra_sites) {
        let site = Uuid::new_v4();
        sqlx::query("INSERT INTO sites (id, tenant_id, site_code, name) VALUES ($1, $2, $3, $4)")
            .bind(site)
            .bind(tenant_id)
            .bind(format!("SITE_{i}"))
            .bind(format!("Site {i}"))
            .execute(pool)
            .await
            .expect("site seed");
        sites.push(site);
    }
    sites
}

/// Seed a user row.
async fn seed_user(pool: &sqlx::PgPool, tenant_id: Uuid, user_id: Uuid) {
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash) \
         VALUES ($1, $2, $3, 'Scope User', 'x')",
    )
    .bind(user_id)
    .bind(tenant_id)
    .bind(format!("user-{user_id}@sensei.test"))
    .execute(pool)
    .await
    .expect("user seed");
}

/// Seed a relational work center row (the scope carrier).
async fn seed_work_center(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    wc_id: Uuid,
    site_id: Uuid,
    number: &str,
) {
    sqlx::query(
        "INSERT INTO work_centers \
             (id, tenant_id, work_center_number, name, site_id) \
         VALUES ($1, $2, $3, $4, $5)",
    )
    .bind(wc_id)
    .bind(tenant_id)
    .bind(number)
    .bind("Scope Work Center")
    .bind(site_id)
    .execute(pool)
    .await
    .expect("work center seed");
}

/// Seed an `entity_store` row so database search can find the entity.
async fn seed_search_row(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    entity_type: &str,
    id: Uuid,
    name: &str,
) {
    sqlx::query(
        "INSERT INTO entity_store (tenant_id, entity_type, id, data) \
         VALUES ($1, $2, $3, $4)",
    )
    .bind(tenant_id)
    .bind(entity_type)
    .bind(id)
    .bind(serde_json::json!({ "name": name }))
    .execute(pool)
    .await
    .expect("entity_store search row seed");
}

/// Seed a role-slot + principal assignment (FORCE RLS: the slot tables
/// are only writable inside a transaction that sets app.tenant_id).
async fn seed_role_slot(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    slot_id: Uuid,
    principal_id: Uuid,
    scope_kind: &str,
    scope_site_id: Option<Uuid>,
    scope_work_center_id: Option<Uuid>,
) {
    let mut tx = pool.begin().await.expect("begin");
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut *tx)
        .await
        .expect("set tenant context");
    sqlx::query(
        "INSERT INTO role_slots \
             (id, tenant_id, role_name, slot_name, scope_kind, \
              scope_site_id, scope_work_center_id) \
         VALUES ($1, $2, 'operator', $3, $4, $5, $6)",
    )
    .bind(slot_id)
    .bind(tenant_id)
    .bind(format!("slot-{slot_id}"))
    .bind(scope_kind)
    .bind(scope_site_id)
    .bind(scope_work_center_id)
    .execute(&mut *tx)
    .await
    .expect("role slot seed");
    sqlx::query(
        "INSERT INTO principal_assignments (tenant_id, principal_id, slot_id) \
         VALUES ($1, $2, $3)",
    )
    .bind(tenant_id)
    .bind(principal_id)
    .bind(slot_id)
    .execute(&mut *tx)
    .await
    .expect("principal assignment seed");
    tx.commit().await.expect("commit scope seeds");
}

/// Seed an NCR with the given server-stamped scope pair (both `None` =
/// a corporate record).
async fn seed_ncr(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    ncr_id: Uuid,
    reported_by: Uuid,
    scope_site_id: Option<Uuid>,
    scope_work_center_id: Option<Uuid>,
) {
    sqlx::query(
        "INSERT INTO ncr_reports \
             (id, tenant_id, ncr_number, title, severity, reported_by, \
              scope_site_id, scope_work_center_id) \
         VALUES ($1, $2, $3, 'Scope NCR', 'minor', $4, $5, $6)",
    )
    .bind(ncr_id)
    .bind(tenant_id)
    .bind(format!("NCR-{ncr_id}"))
    .bind(reported_by)
    .bind(scope_site_id)
    .bind(scope_work_center_id)
    .execute(pool)
    .await
    .expect("ncr seed");
}

/// Site-B work-order parent attachment denied for a site-A user (Wave B
/// item 11): the parent's site is derived from its work center and the
/// caller's role-slot scope; a foreign-site parent is indistinguishable
/// from a nonexistent one (NotFound), and the metadata row alone cannot
/// bypass the check.
#[tokio::test]
async fn test_site_b_parent_attachment_denied_for_site_a_user_db_gated() {
    let Some(pool) = db_pool().await else { return };
    let pool = std::sync::Arc::new(pool);

    // The DB-gated assertions need the full schema; apply the migration
    // chain when the database has none (no-op when already migrated).
    if let Err(e) = sensei_db::migrations::run_migrations(&pool).await {
        eprintln!("SKIP: migration chain unavailable for attachment scope gate ({e})");
        return;
    }

    // Fresh, isolated tenant: every seed below is tenant-scoped.
    let tenant_id = Uuid::new_v4();
    let site_a = Uuid::new_v4();
    let site_b = Uuid::new_v4();
    let user_a = Uuid::new_v4();
    let user_b = Uuid::new_v4();
    let wc_a = Uuid::new_v4();
    let wc_b = Uuid::new_v4();
    let wo_a = Uuid::new_v4();
    let wo_b = Uuid::new_v4();
    let slot_a = Uuid::new_v4();
    let slot_b = Uuid::new_v4();
    let now = Utc::now();

    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
        .bind(tenant_id)
        .bind("Attachment Scope Tenant")
        .bind(format!("att-scope-{tenant_id}"))
        .execute(&*pool)
        .await
        .expect("tenant seed");
    for (site, code) in [(site_a, "SITE_A"), (site_b, "SITE_B")] {
        sqlx::query("INSERT INTO sites (id, tenant_id, site_code, name) VALUES ($1, $2, $3, $4)")
            .bind(site)
            .bind(tenant_id)
            .bind(code)
            .bind(code)
            .execute(&*pool)
            .await
            .expect("site seed");
    }
    for user in [user_a, user_b] {
        sqlx::query(
            "INSERT INTO users (id, tenant_id, email, name, password_hash) \
             VALUES ($1, $2, $3, $4, 'x')",
        )
        .bind(user)
        .bind(tenant_id)
        .bind(format!("user-{user}@sensei.test"))
        .bind("Scope User")
        .execute(&*pool)
        .await
        .expect("user seed");
    }
    for (wc, site) in [(wc_a, site_a), (wc_b, site_b)] {
        sqlx::query(
            "INSERT INTO work_centers \
                 (id, tenant_id, work_center_number, name, site_id) \
             VALUES ($1, $2, $3, $4, $5)",
        )
        .bind(wc)
        .bind(tenant_id)
        .bind(format!("WC-{wc}"))
        .bind("Scope Work Center")
        .bind(site)
        .execute(&*pool)
        .await
        .expect("work center seed");
    }
    for (wo, wc) in [(wo_a, wc_a), (wo_b, wc_b)] {
        sqlx::query(
            "INSERT INTO work_orders \
                 (id, tenant_id, wo_number, product_id, quantity, work_center_id) \
             VALUES ($1, $2, $3, $4, 1, $5)",
        )
        .bind(wo)
        .bind(tenant_id)
        .bind(format!("WO-{wo}"))
        .bind(Uuid::new_v4())
        .bind(wc)
        .execute(&*pool)
        .await
        .expect("work order seed");
    }

    // Role-slot scope: the FORCE-RLS slot/assignment tables are only
    // writable inside a transaction that sets app.tenant_id.
    {
        let mut tx = pool.begin().await.expect("begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        for (slot, site) in [(slot_a, site_a), (slot_b, site_b)] {
            sqlx::query(
                "INSERT INTO role_slots \
                     (id, tenant_id, role_name, slot_name, scope_site_id) \
                 VALUES ($1, $2, 'operator', $3, $4)",
            )
            .bind(slot)
            .bind(tenant_id)
            .bind(format!("slot-{slot}"))
            .bind(site)
            .execute(&mut *tx)
            .await
            .expect("role slot seed");
        }
        for (slot, user) in [(slot_a, user_a), (slot_b, user_b)] {
            sqlx::query(
                "INSERT INTO principal_assignments \
                     (tenant_id, principal_id, slot_id) \
                 VALUES ($1, $2, $3)",
            )
            .bind(tenant_id)
            .bind(user)
            .bind(slot)
            .execute(&mut *tx)
            .await
            .expect("principal assignment seed");
        }
        tx.commit().await.expect("commit scope seeds");
    }

    // Attachment metadata for both work orders (rows exist and belong to
    // the tenant — a "known UUID" that must not bypass the parent scope).
    for (wo, suffix) in [(wo_a, "A"), (wo_b, "B")] {
        let id = Uuid::new_v4();
        sqlx::query(
            "INSERT INTO attachments \
                 (id, tenant_id, entity_type, entity_id, file_name, \
                  content_type, file_size, storage_path, uploaded_by, created_at) \
             VALUES ($1, $2, 'work_order', $3, $4, 'application/pdf', 1, $5, $6, $7)",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(wo)
        .bind(format!("doc-{suffix}.pdf"))
        .bind(format!("opaque-{suffix}"))
        .bind(user_a)
        .bind(now)
        .execute(&*pool)
        .await
        .expect("attachment seed");
    }

    // Build the application state with the DB pool attached (typed
    // repositories + scope resolution reach the same database).
    common::setup::pin_test_environment();
    let config = sensei_core::config::AppConfig::from_env()
        .expect("test configuration must load under pinned env");
    let users_service =
        std::sync::Arc::new(sensei_services::users::InMemoryUsersService::with_admin(
            "dbgate@sensei.test",
            "Db Gate",
            "x",
            tenant_id,
        ));
    let state = sensei_api::AppState::new(config, users_service).with_db_pool(pool.clone());

    // ── Direct-UUID access must not bypass parent authorization ────────
    use sensei_api::authorization::parent_resource::require_parent_read;
    use sensei_auth::middleware::AuthenticatedUser;
    use std::collections::HashSet;

    let user_a_principal = AuthenticatedUser {
        user_id: user_a,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from([
            "attachments:read".to_string(),
            "production:work-order:read".to_string(),
        ]),
    };

    // Site-A user CAN read the site-A work order's attachment parent…
    require_parent_read(&state, &user_a_principal, "work_order", wo_a)
        .await
        .expect("site-A user must read a site-A work order");

    // …but the site-B work order is out of scope: denied (NotFound), and
    // the attachment metadata row for it (a known UUID in the tenant)
    // cannot bypass the parent check — the download handler runs this
    // exact check after resolving metadata and before presigning.
    let err = require_parent_read(&state, &user_a_principal, "work_order", wo_b)
        .await
        .expect_err("site-B parent must be denied for a site-A user");
    assert!(
        matches!(err, sensei_core::error::SenseiError::NotFound(_)),
        "foreign-site and nonexistent parents must be indistinguishable, got {err:?}"
    );

    // Both attachment metadata rows exist and are tenant-visible — the
    // metadata alone (a "known UUID") grants nothing.
    let rows_a = state
        .attachment_repo
        .list(tenant_id, "work_order", wo_a)
        .await
        .expect("list site-A rows");
    assert_eq!(rows_a.len(), 1, "site-A attachment row exists");
    let rows_b = state
        .attachment_repo
        .list(tenant_id, "work_order", wo_b)
        .await
        .expect("list site-B rows");
    assert_eq!(rows_b.len(), 1, "site-B attachment row exists");

    // The download sequence — metadata resolved (row exists), then the
    // parent read check — must deny the site-B row for the site-A user.
    require_parent_read(&state, &user_a_principal, "work_order", rows_b[0].entity_id)
        .await
        .expect_err("site-B parent must deny the download sequence");

    // A principal with NO active role-slot assignment (NoOperationalScope)
    // cannot reach any work-order parent — fail closed, never tenant-wide.
    let no_scope_user = AuthenticatedUser {
        user_id: Uuid::new_v4(),
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from([
            "attachments:read".to_string(),
            "production:work-order:read".to_string(),
        ]),
    };
    require_parent_read(&state, &no_scope_user, "work_order", wo_a)
        .await
        .expect_err("NoOperationalScope must deny every work-order parent");
}

// ── Thirtieth-audit P0 items 12-13 (exact scope preservation) ──────────────

/// (i) A work-center-EXACT operator searches ONLY their granted work
/// center: a same-site sibling work center never leaks into the results
/// (the search predicate is `id = ANY($exact_wc_ids)`, never the parent
/// site), while a site-granted operator of the same site DOES see both.
#[tokio::test]
async fn test_wc_exact_search_does_not_return_same_site_other_wc_db_gated() {
    let Some(pool) = db_pool().await else { return };
    let pool = std::sync::Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }

    use sensei_api::authorization::build_request_context;
    use sensei_api::authorization::search_policy::AllowedSearchProjection;
    use sensei_auth::middleware::AuthenticatedUser;
    use sensei_core::domain::scope::AuthorizedScope;
    use std::collections::HashSet;

    let tenant_id = Uuid::new_v4();
    let sites = seed_tenant_and_sites(&pool, tenant_id, 0).await;
    let site_a = sites[0];
    let site_b = sites[1];
    let wc_operator = Uuid::new_v4();
    let site_operator = Uuid::new_v4();
    seed_user(&pool, tenant_id, wc_operator).await;
    seed_user(&pool, tenant_id, site_operator).await;

    let wc_a = Uuid::new_v4();
    let wc_b = Uuid::new_v4();
    let wc_c = Uuid::new_v4();
    // Both work centers on site A (the sibling that must never leak to a
    // WC-exact caller) + one on site B.
    for (wc, site, number) in [
        (wc_a, site_a, "WC-SCOPE-A"),
        (wc_b, site_a, "WC-SCOPE-B"),
        (wc_c, site_b, "WC-SCOPE-C"),
    ] {
        seed_work_center(&pool, tenant_id, wc, site, number).await;
    }
    // Searchable entity-store rows (the database search reads these).
    seed_search_row(&pool, tenant_id, "work_center", wc_a, "Turbo WC Scope A").await;
    seed_search_row(&pool, tenant_id, "work_center", wc_b, "Turbo WC Scope B").await;
    seed_search_row(&pool, tenant_id, "work_center", wc_c, "Turbo WC Scope C").await;

    // The WC-EXACT operator: one role slot scoped to exactly (site_a,
    // wc_a) — NEVER normalized into its site.
    seed_role_slot(
        &pool,
        tenant_id,
        Uuid::new_v4(),
        wc_operator,
        "work_center",
        Some(site_a),
        Some(wc_a),
    )
    .await;
    // Control: a SITE operator of site A (sees both site-A work centers).
    seed_role_slot(
        &pool,
        tenant_id,
        Uuid::new_v4(),
        site_operator,
        "site",
        Some(site_a),
        None,
    )
    .await;

    let state = db_state(&pool);
    let wc_principal = AuthenticatedUser {
        user_id: wc_operator,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["tps:work-center:read".to_string()]),
    };
    let site_principal = AuthenticatedUser {
        user_id: site_operator,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["tps:work-center:read".to_string()]),
    };

    // Pin the resolved scopes: the WC-exact operator's scope carries the
    // exact work center with an EMPTY site set (item 1 semantics).
    let wc_rc = build_request_context(&wc_principal, &state)
        .await
        .expect("wc scope resolution");
    match &wc_rc.scope {
        AuthorizedScope::Operational {
            sites,
            work_centers,
        } => {
            assert!(
                sites.is_empty(),
                "a work-center grant must never normalize into its site, got {wc_rc:?}"
            );
            assert_eq!(work_centers.len(), 1, "exactly one WC grant, got {wc_rc:?}");
            assert_eq!(
                work_centers.iter().next().unwrap().work_center,
                wc_a,
                "the granted work center is wc_a"
            );
        }
        other => panic!("expected an Operational scope, got {other:?}"),
    }

    let wc_projection =
        AllowedSearchProjection::for_caller(&state, &wc_principal, Some("work_center"))
            .await
            .expect("wc-exact projection");
    let wc_results = sensei_api::db_search_service::search_db_authorized(
        pool.as_ref(),
        tenant_id,
        "Turbo",
        &wc_projection,
    )
    .await
    .expect("wc-exact search runs");
    let mut wc_hits: Vec<Uuid> = wc_results
        .iter()
        .filter(|r| r.result_type == "work_center")
        .map(|r| r.result_id)
        .collect();
    wc_hits.sort_unstable();
    assert_eq!(
        wc_hits,
        vec![wc_a],
        "a WC-exact operator sees exactly its own work center — the \
         same-site sibling {wc_b} must never leak"
    );

    // Control: the site-A operator sees BOTH site-A work centers through
    // the same query — proving wc_b is a genuine same-site result that the
    // exact predicate must keep out.
    let site_projection =
        AllowedSearchProjection::for_caller(&state, &site_principal, Some("work_center"))
            .await
            .expect("site projection");
    let site_results = sensei_api::db_search_service::search_db_authorized(
        pool.as_ref(),
        tenant_id,
        "Turbo",
        &site_projection,
    )
    .await
    .expect("site search runs");
    let mut site_hits: Vec<Uuid> = site_results
        .iter()
        .filter(|r| r.result_type == "work_center")
        .map(|r| r.result_id)
        .collect();
    let mut site_a_work_centers = vec![wc_a, wc_b];
    site_hits.sort_unstable();
    site_a_work_centers.sort_unstable();
    assert_eq!(
        site_hits, site_a_work_centers,
        "the site-A operator sees every work center of site A"
    );
}

/// (ii) Attachment to a Site-B NCR is denied for a Site-A user even with
/// `ncr:read` (the NCR proof applies the record's server-stamped
/// `scope_site_id`/`scope_work_center_id`); a corporate (both-NULL) NCR
/// requires an explicit tenant-wide grant, and a WC-exact caller reaches
/// only the records stamped at their exact work center — never the
/// site-level records of their site.
#[tokio::test]
async fn test_site_b_ncr_parent_attachment_denied_for_site_a_user_db_gated() {
    let Some(pool) = db_pool().await else { return };
    let pool = std::sync::Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }

    use sensei_api::authorization::parent_resource::require_parent_read;
    use sensei_auth::middleware::AuthenticatedUser;
    use std::collections::HashSet;

    let tenant_id = Uuid::new_v4();
    let sites = seed_tenant_and_sites(&pool, tenant_id, 0).await;
    let site_a = sites[0];
    let site_b = sites[1];
    let user_a = Uuid::new_v4();
    let user_b = Uuid::new_v4();
    let wc_user = Uuid::new_v4();
    for user in [user_a, user_b, wc_user] {
        seed_user(&pool, tenant_id, user).await;
    }
    let wc_a = Uuid::new_v4();
    seed_work_center(&pool, tenant_id, wc_a, site_a, "WC-NCR-A").await;
    seed_role_slot(
        &pool,
        tenant_id,
        Uuid::new_v4(),
        user_a,
        "site",
        Some(site_a),
        None,
    )
    .await;
    seed_role_slot(
        &pool,
        tenant_id,
        Uuid::new_v4(),
        user_b,
        "site",
        Some(site_b),
        None,
    )
    .await;
    seed_role_slot(
        &pool,
        tenant_id,
        Uuid::new_v4(),
        wc_user,
        "work_center",
        Some(site_a),
        Some(wc_a),
    )
    .await;

    // Records stamped at site A / site B / the (site_a, wc_a) work center
    // / a corporate (both-NULL) record.
    let ncr_a = Uuid::new_v4();
    let ncr_b = Uuid::new_v4();
    let ncr_wc = Uuid::new_v4();
    let ncr_corp = Uuid::new_v4();
    seed_ncr(&pool, tenant_id, ncr_a, user_a, Some(site_a), None).await;
    seed_ncr(&pool, tenant_id, ncr_b, user_b, Some(site_b), None).await;
    seed_ncr(&pool, tenant_id, ncr_wc, user_a, Some(site_a), Some(wc_a)).await;
    seed_ncr(&pool, tenant_id, ncr_corp, user_a, None, None).await;

    let state = db_state(&pool);
    let user_a_principal = AuthenticatedUser {
        user_id: user_a,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["quality:ncr:read".to_string()]),
    };
    let user_b_principal = AuthenticatedUser {
        user_id: user_b,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["quality:ncr:read".to_string()]),
    };
    let wc_principal = AuthenticatedUser {
        user_id: wc_user,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from(["quality:ncr:read".to_string()]),
    };

    // Site-A user: reads the site-A NCR (and the site-A work-center NCR)…
    require_parent_read(&state, &user_a_principal, "ncr", ncr_a)
        .await
        .expect("site-A user must read a site-A NCR");
    require_parent_read(&state, &user_a_principal, "ncr", ncr_wc)
        .await
        .expect("site-A user must read a work-center NCR of site A");

    // …but the site-B NCR is out of scope even WITH `ncr:read` — denied,
    // indistinguishable from nonexistent (NotFound).
    for foreign in [ncr_b, ncr_corp] {
        let err = require_parent_read(&state, &user_a_principal, "ncr", foreign)
            .await
            .expect_err("a site-A user must not read a foreign/corporate NCR");
        assert!(
            matches!(err, sensei_core::error::SenseiError::NotFound(_)),
            "foreign/corporate and nonexistent NCR parents must be indistinguishable, got {err:?}"
        );
    }

    // Site-B user reads the site-B NCR (positive control).
    require_parent_read(&state, &user_b_principal, "ncr", ncr_b)
        .await
        .expect("site-B user must read a site-B NCR");

    // A WC-exact caller reads exactly the records stamped at its work
    // center — never the site-level NCRs of its site (no widening).
    require_parent_read(&state, &wc_principal, "ncr", ncr_wc)
        .await
        .expect("the WC-exact caller reads its own work center's NCR");
    let err = require_parent_read(&state, &wc_principal, "ncr", ncr_a)
        .await
        .expect_err("a work-center grant must not widen to site-level NCRs");
    assert!(
        matches!(err, sensei_core::error::SenseiError::NotFound(_)),
        "site-level NCRs must be out of scope for a pure WC caller, got {err:?}"
    );
}

/// (iii) An explicit TENANT-WIDE attachment proof still proves parent
/// EXISTENCE (item 13(a)): a nonexistent parent is 404 — never an early
/// success — while a real work order (and a corporate NCR) stays
/// readable.
#[tokio::test]
async fn test_tenant_wide_attachment_proof_requires_existence_db_gated() {
    let Some(pool) = db_pool().await else { return };
    let pool = std::sync::Arc::new(pool);
    if !ensure_migrations(&pool).await {
        return;
    }

    use sensei_api::authorization::build_request_context;
    use sensei_api::authorization::parent_resource::require_parent_read;
    use sensei_auth::middleware::AuthenticatedUser;
    use sensei_core::domain::scope::AuthorizedScope;
    use std::collections::HashSet;

    let tenant_id = Uuid::new_v4();
    let sites = seed_tenant_and_sites(&pool, tenant_id, 0).await;
    let site_a = sites[0];
    let tenant_wide_user = Uuid::new_v4();
    seed_user(&pool, tenant_id, tenant_wide_user).await;

    let wc_a = Uuid::new_v4();
    seed_work_center(&pool, tenant_id, wc_a, site_a, "WC-TW-A").await;
    let wo_a = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO work_orders \
             (id, tenant_id, wo_number, product_id, quantity, work_center_id) \
         VALUES ($1, $2, $3, $4, 1, $5)",
    )
    .bind(wo_a)
    .bind(tenant_id)
    .bind("WO-TW-A")
    .bind(Uuid::new_v4())
    .bind(wc_a)
    .execute(&*pool)
    .await
    .expect("work order seed");
    // A corporate (both-NULL) NCR: reachable only by the tenant-wide grant.
    let ncr_corp = Uuid::new_v4();
    seed_ncr(&pool, tenant_id, ncr_corp, tenant_wide_user, None, None).await;

    // The EXPLICIT tenant-wide slot (`scope_kind = 'tenant'`).
    seed_role_slot(
        &pool,
        tenant_id,
        Uuid::new_v4(),
        tenant_wide_user,
        "tenant",
        None,
        None,
    )
    .await;

    let state = db_state(&pool);
    let principal = AuthenticatedUser {
        user_id: tenant_wide_user,
        tenant_id,
        roles: vec!["operator".to_string()],
        sid: None,
        permissions: HashSet::from([
            "production:work-order:read".to_string(),
            "quality:ncr:read".to_string(),
        ]),
    };

    // Pin the resolution: the tenant-kind slot resolves to the EXPLICIT
    // tenant-wide grant.
    let rc = build_request_context(&principal, &state)
        .await
        .expect("tenant-wide scope resolution");
    assert!(
        matches!(rc.scope, AuthorizedScope::TenantWide),
        "the tenant-kind slot must resolve to TenantWide, got {:?}",
        rc.scope
    );

    // Positive controls: the tenant-wide caller reads an existing work
    // order of any site and the corporate NCR.
    require_parent_read(&state, &principal, "work_order", wo_a)
        .await
        .expect("tenant-wide caller must read an existing work order");
    require_parent_read(&state, &principal, "ncr", ncr_corp)
        .await
        .expect("corporate NCRs are reachable by the explicit tenant-wide grant");

    // The item-13(a) assertion: a NONEXISTENT work order is 404 for a
    // tenant-wide caller too — the proof never early-returns on the
    // all-access grant.
    let missing_wo = Uuid::new_v4();
    let err = require_parent_read(&state, &principal, "work_order", missing_wo)
        .await
        .expect_err("tenant-wide proof must still require parent existence");
    assert!(
        matches!(err, sensei_core::error::SenseiError::NotFound(_)),
        "a nonexistent work-order parent must be 404 even for a tenant-wide caller, got {err:?}"
    );
    let missing_ncr = Uuid::new_v4();
    let err = require_parent_read(&state, &principal, "ncr", missing_ncr)
        .await
        .expect_err("tenant-wide proof must still require NCR existence");
    assert!(
        matches!(err, sensei_core::error::SenseiError::NotFound(_)),
        "a nonexistent NCR parent must be 404 even for a tenant-wide caller, got {err:?}"
    );
}

//! Background sync service with offline queue, conflict resolution, and queue replay.
//!
//! Ported from [`frontend/src/services/sync-service.ts`](frontend/src/services/sync-service.ts).
//!
//! # Architecture
//!
//! ```text
//! ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
//! │  SyncService  │───▶│  IndexedDb   │◀───│  PendingOperation │
//! │  (this file)  │    │  (persistent) │   │  (from store)    │
//! └──────┬───────┘    └──────────────┘    └──────────────────┘
//!        │
//!        ├──▶ BackgroundSync (SyncManager)
//!        ├──▶ PeriodicSync  (PeriodicSyncManager)
//!        └──▶ Queue replay on reconnect
//! ```

use crate::api::client::ApiClient;
use crate::pwa::indexed_db::{IndexedDb, IndexedDbError, StoreNames};
use crate::pwa::service_worker::{self, is_online};
use crate::stores::sync::{PendingOperation, SyncStore};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::JsFuture;
use web_sys::ServiceWorkerRegistration;

// ── Constants ───────────────────────────────────────────────────────────────

/// Tag used for one-shot background sync registration.
const SYNC_TAG: &str = "pending-operations-sync";
/// Tag used for periodic background sync.
const PERIODIC_SYNC_TAG: &str = "periodic-sync";
/// Default interval for periodic sync (1 hour in seconds).
const DEFAULT_PERIODIC_SYNC_INTERVAL_SECS: f64 = 3600.0;
/// Maximum number of retry attempts for a single operation before it is marked as failed.
const MAX_RETRY_COUNT: i32 = 5;

// ── Error Type ──────────────────────────────────────────────────────────────

/// Errors that can occur during sync operations.
#[derive(Debug, Clone)]
pub enum SyncError {
    /// Background Sync API is not supported.
    NotSupported,
    /// No service worker registration available.
    NoRegistration,
    /// Registration of a sync tag failed.
    RegistrationFailed(String),
    /// IndexedDB operation failed.
    IndexedDb(IndexedDbError),
    /// A sync operation itself failed.
    SyncFailed(String),
    /// Conflict resolution failed.
    Conflict(String),
    /// Serialization failed.
    Serde(String),
}

impl std::fmt::Display for SyncError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotSupported => write!(f, "Background sync is not supported"),
            Self::NoRegistration => write!(f, "No service worker registration"),
            Self::RegistrationFailed(msg) => write!(f, "Sync registration failed: {msg}"),
            Self::IndexedDb(e) => write!(f, "IndexedDB error: {e}"),
            Self::SyncFailed(msg) => write!(f, "Sync failed: {msg}"),
            Self::Conflict(msg) => write!(f, "Conflict: {msg}"),
            Self::Serde(msg) => write!(f, "Serialization error: {msg}"),
        }
    }
}

impl std::error::Error for SyncError {}

impl From<IndexedDbError> for SyncError {
    fn from(e: IndexedDbError) -> Self {
        Self::IndexedDb(e)
    }
}

impl From<wasm_bindgen::JsValue> for SyncError {
    fn from(value: wasm_bindgen::JsValue) -> Self {
        Self::RegistrationFailed(format!("{value:?}"))
    }
}

/// Specialised `Result` for sync operations.
pub type Result<T> = std::result::Result<T, SyncError>;

// ── Sync Status ─────────────────────────────────────────────────────────────

/// Current status of the sync engine.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SyncStatus {
    /// Sync is idle.
    Idle,
    /// Sync is currently in progress.
    Syncing,
    /// Sync completed successfully.
    Synced,
    /// Sync failed with an error.
    Error(String),
}

/// Result of a single sync operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncOperationResult {
    pub operation_id: String,
    pub success: bool,
    pub error: Option<String>,
}

/// Result of a full sync cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncCycleResult {
    pub synced_count: usize,
    pub failed_count: usize,
    pub errors: Vec<SyncOperationResult>,
}

// ── Sync Service ────────────────────────────────────────────────────────────

/// Main sync service handling offline queue, background sync, periodic sync,
/// conflict resolution, and queue replay on reconnection.
///
/// This is the Rust WASM equivalent of the TypeScript `SyncManager` class
/// from [`frontend/src/services/sync-service.ts`](frontend/src/services/sync-service.ts).
#[derive(Clone)]
pub struct SyncService {
    /// Reference to the reactive sync store.
    sync_store: SyncStore,
    /// IndexedDB handle for persistent queue storage.
    db: Option<IndexedDb>,
    /// Whether background sync is supported in this browser.
    bg_sync_supported: bool,
    /// Whether periodic sync is supported in this browser.
    periodic_sync_supported: bool,
}

impl SyncService {
    /// Create a new `SyncService`.
    ///
    /// This does not initialise the IndexedDB connection or register any sync
    /// events — call [`SyncService::init`] to do that.
    pub fn new(sync_store: SyncStore) -> Self {
        let bg_sync_supported = is_background_sync_supported();
        let periodic_sync_supported = is_periodic_sync_supported();

        Self {
            sync_store,
            db: None,
            bg_sync_supported,
            periodic_sync_supported,
        }
    }

    /// Initialise the sync service: open IndexedDB, set up online/offline
    /// listeners, and attempt to replay the queue.
    pub async fn init(&mut self) -> Result<()> {
        // Open IndexedDB
        let db = IndexedDb::open().await.map_err(SyncError::IndexedDb)?;
        self.db = Some(db);

        // Set up online/offline listeners
        self.setup_connectivity_listeners();

        // Register background sync if supported
        if self.bg_sync_supported {
            let _ = self.register_background_sync().await;
        }

        // Register periodic sync if supported
        if self.periodic_sync_supported {
            let _ = self.register_periodic_sync(DEFAULT_PERIODIC_SYNC_INTERVAL_SECS).await;
        }

        // Attempt to replay the offline queue (if we're online now)
        if is_online() {
            let store = self.sync_store.clone();
            wasm_bindgen_futures::spawn_local(async move {
                if store.get_pending_count() > 0 {
                    let _ = replay_queue_internal(store).await;
                }
            });
        }

        Ok(())
    }

    /// Set up `online` / `offline` event listeners to react to connectivity changes.
    fn setup_connectivity_listeners(&self) {
        let store = self.sync_store.clone();
        service_worker::add_online_listener(move || {
            store.set_online(true);
            // Attempt queue replay on reconnect
            let store_clone = store.clone();
            wasm_bindgen_futures::spawn_local(async move {
                let _ = replay_queue_internal(store_clone).await;
            });
        });

        let store = self.sync_store.clone();
        service_worker::add_offline_listener(move || {
            store.set_online(false);
        });

        // Set initial online state
        self.sync_store.set_online(is_online());
    }

    // ── Background Sync Registration ────────────────────────────────────────

    /// Check if Background Sync API is supported.
    pub fn is_background_sync_supported() -> bool {
        is_background_sync_supported()
    }

    /// Check if Periodic Background Sync API is supported.
    pub fn is_periodic_sync_supported() -> bool {
        is_periodic_sync_supported()
    }

    /// Register a one-shot background sync with the given tag.
    ///
    /// Uses dynamic dispatch via `js_sys::Reflect` since `SyncManager` is not
    /// exposed as a web-sys feature in this version.
    pub async fn register_background_sync(&self) -> Result<bool> {
        if !self.bg_sync_supported {
            return Ok(false);
        }

        let registration = get_service_worker_registration().await?;
        let registration_value: JsValue = registration.into();

        // Access `registration.sync` dynamically
        let sync_manager = js_sys::Reflect::get(&registration_value, &JsValue::from_str("sync"))
            .map_err(|_| SyncError::NotSupported)?;

        if sync_manager.is_undefined() || sync_manager.is_null() {
            return Ok(false);
        }

        // Call sync.register(tag) which returns a Promise
        let register_fn_js = js_sys::Reflect::get(&sync_manager, &JsValue::from_str("register"))
            .map_err(|_| SyncError::RegistrationFailed("register method not found".into()))?;
        let register_fn: &js_sys::Function = register_fn_js
            .dyn_ref()
            .ok_or_else(|| SyncError::RegistrationFailed("register is not a function".into()))?;

        let args = js_sys::Array::new();
        args.push(&JsValue::from_str(SYNC_TAG));
        let promise_js = js_sys::Reflect::apply(register_fn, &sync_manager, &args)
            .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

        let promise: js_sys::Promise = promise_js
            .dyn_into()
            .map_err(|_| SyncError::RegistrationFailed("register did not return a Promise".into()))?;

        JsFuture::from(promise)
            .await
            .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

        Ok(true)
    }

    /// Register a periodic background sync.
    ///
    /// Uses dynamic dispatch via `js_sys::Reflect` since `PeriodicSyncManager` is not
    /// exposed as a web-sys feature in this version.
    pub async fn register_periodic_sync(&self, min_interval_seconds: f64) -> Result<bool> {
        if !self.periodic_sync_supported {
            return Ok(false);
        }

        let registration = get_service_worker_registration().await?;
        let registration_value: JsValue = registration.into();

        // Access `registration.periodicSync` dynamically
        let periodic_sync = js_sys::Reflect::get(&registration_value, &JsValue::from_str("periodicSync"))
            .map_err(|_| SyncError::NotSupported)?;

        if periodic_sync.is_undefined() || periodic_sync.is_null() {
            return Ok(false);
        }

        // Build the options object: { minInterval: number }
        let options = js_sys::Object::new();
        js_sys::Reflect::set(
            &options,
            &JsValue::from_str("minInterval"),
            &JsValue::from_f64(min_interval_seconds),
        )
        .map_err(|_| SyncError::RegistrationFailed("Cannot set minInterval".into()))?;

        // Call periodicSync.register(tag, options) which returns a Promise
        let register_fn_js = js_sys::Reflect::get(&periodic_sync, &JsValue::from_str("register"))
            .map_err(|_| SyncError::RegistrationFailed("register method not found".into()))?;
        let register_fn: &js_sys::Function = register_fn_js
            .dyn_ref()
            .ok_or_else(|| SyncError::RegistrationFailed("register is not a function".into()))?;

        let args = js_sys::Array::new();
        args.push(&JsValue::from_str(PERIODIC_SYNC_TAG));
        args.push(&options);
        let promise_js = js_sys::Reflect::apply(register_fn, &periodic_sync, &args)
            .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

        let promise: js_sys::Promise = promise_js
            .dyn_into()
            .map_err(|_| SyncError::RegistrationFailed("register did not return a Promise".into()))?;

        JsFuture::from(promise)
            .await
            .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

        Ok(true)
    }

    /// Unregister the periodic background sync.
    pub async fn unregister_periodic_sync(&self) -> Result<bool> {
        if !self.periodic_sync_supported {
            return Ok(false);
        }

        let registration = get_service_worker_registration().await?;
        let registration_value: JsValue = registration.into();

        // Access `registration.periodicSync` dynamically
        let periodic_sync = js_sys::Reflect::get(&registration_value, &JsValue::from_str("periodicSync"))
            .map_err(|_| SyncError::NotSupported)?;

        if periodic_sync.is_undefined() || periodic_sync.is_null() {
            return Ok(false);
        }

        // Call periodicSync.unregister(tag) which returns a Promise
        let unregister_fn_js = js_sys::Reflect::get(&periodic_sync, &JsValue::from_str("unregister"))
            .map_err(|_| SyncError::RegistrationFailed("unregister method not found".into()))?;
        let unregister_fn: &js_sys::Function = unregister_fn_js
            .dyn_ref()
            .ok_or_else(|| SyncError::RegistrationFailed("unregister is not a function".into()))?;

        let args = js_sys::Array::new();
        args.push(&JsValue::from_str(PERIODIC_SYNC_TAG));
        let promise_js = js_sys::Reflect::apply(unregister_fn, &periodic_sync, &args)
            .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

        let promise: js_sys::Promise = promise_js
            .dyn_into()
            .map_err(|_| SyncError::RegistrationFailed("unregister did not return a Promise".into()))?;

        JsFuture::from(promise)
            .await
            .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

        Ok(true)
    }

    // ── Queue Management ────────────────────────────────────────────────────

    /// Add an operation to the offline queue and persist to IndexedDB.
    pub async fn queue_operation(&self, operation: PendingOperation) -> Result<String> {
        let operation_id = operation.id.clone();

        // Add to reactive store
        self.sync_store.add_operation(operation.clone());

        // Persist to IndexedDB
        if let Some(db) = &self.db {
            let value =
                serde_wasm_bindgen::to_value(&operation)
                    .map_err(|e| SyncError::Serde(e.to_string()))?;
            db.put_pending_operation(&value).await?;
        }

        // Register a background sync if supported
        if self.bg_sync_supported {
            let _ = self.register_background_sync().await;
        }

        Ok(operation_id)
    }

    /// Remove a completed operation from the queue.
    pub async fn remove_operation(&self, operation_id: &str) -> Result<()> {
        self.sync_store.remove_operation(operation_id);

        if let Some(db) = &self.db {
            let key = JsValue::from_str(operation_id);
            db.delete_pending_operation(&key).await?;
        }

        Ok(())
    }

    /// Get all pending operations from the persistent store.
    pub async fn get_pending_operations_from_db(&self) -> Result<Vec<PendingOperation>> {
        let db = self.db.as_ref().ok_or_else(|| {
            SyncError::IndexedDb(IndexedDbError::StoreNotFound(StoreNames::PENDING_OPERATIONS.into()))
        })?;

        let items = db.get_all_pending_operations().await?;
        let mut operations = Vec::with_capacity(items.len());

        for item in items {
            if let Ok(op) = serde_wasm_bindgen::from_value::<PendingOperation>(item) {
                operations.push(op);
            }
        }

        Ok(operations)
    }

    /// Clear all completed operations from the queue.
    pub async fn clear_completed_operations(&self) -> Result<()> {
        self.sync_store.clear_completed_operations();

        if let Some(db) = &self.db {
            // Remove all completed operations from IndexedDB
            let operations = db.get_all_pending_operations().await?;
            for item in operations {
                if let Ok(op) = serde_wasm_bindgen::from_value::<PendingOperation>(item) {
                    if op.status == "completed" {
                        let key = JsValue::from_str(&op.id);
                        let _ = db.delete_pending_operation(&key).await;
                    }
                }
            }
        }

        Ok(())
    }

    // ── Queue Replay ────────────────────────────────────────────────────────

    /// Replay all pending operations in the queue.
    ///
    /// This is called automatically when the application comes back online.
    pub async fn replay_queue(&self) -> Result<SyncCycleResult> {
        self.sync_store.set_syncing(true);

        let result = replay_queue_internal(self.sync_store.clone()).await;

        // Update sync state
        match &result {
            Ok(cycle_result) => {
                if cycle_result.failed_count == 0 {
                    self.sync_store.set_sync_error(None);
                    let now = chrono::Utc::now().to_rfc3339();
                    self.sync_store.set_last_sync_at(&now);
                } else {
                    self.sync_store
                        .set_sync_error(Some(&format!("{} operations failed", cycle_result.failed_count)));
                }
            }
            Err(e) => {
                self.sync_store.set_sync_error(Some(&e.to_string()));
            }
        }

        self.sync_store.set_syncing(false);
        result
    }

    // ── Conflict Resolution ─────────────────────────────────────────────────

    /// Resolve a conflict between a local operation and the server state.
    ///
    /// The default strategy is **Local Wins**: keep the local change and attempt
    /// to re-apply it on the server. Other strategies can be implemented
    /// per-operation-type.
    pub fn resolve_conflict(&self, operation: &PendingOperation, _server_data: &JsValue) -> ConflictResolution {
        match operation.operation_type.as_str() {
            // For deletes, if the entity is already gone on the server, no conflict
            "delete" => ConflictResolution::ServerWins,
            // For creates, the server might have a duplicate — flag for review
            "create" if operation.entity_id.is_none() => ConflictResolution::FlagForReview(
                "Server already has this entity; manual merge required".to_string(),
            ),
            // For updates, prefer local changes (Last Write Wins)
            "update" => ConflictResolution::LocalWins,
            // Default: Local Wins
            _ => ConflictResolution::LocalWins,
        }
    }
}

// ── Free functions (not on SyncService) ────────────────────────────────────

/// Check whether the Background Sync API is available.
///
/// Uses `js_sys::eval` to check `ServiceWorkerRegistration.prototype.sync`
/// since web-sys does not expose `SyncManager` as a separate type.
fn is_background_sync_supported() -> bool {
    let window = match web_sys::window() {
        Some(w) => w,
        None => return false,
    };
    // service_worker() always returns ServiceWorkerContainer (never None),
    // so we just verify the window/navigator exists.
    let _ = window.navigator().service_worker();

    // Check via JavaScript interop
    let result = js_sys::eval(
        "typeof ServiceWorkerRegistration !== 'undefined' && 'sync' in ServiceWorkerRegistration.prototype",
    );
    result.map(|v| v.is_truthy()).unwrap_or(false)
}

/// Check whether the Periodic Background Sync API is available.
///
/// Uses `js_sys::eval` to check `ServiceWorkerRegistration.prototype.periodicSync`
/// since web-sys does not expose `PeriodicSyncManager` as a separate type.
fn is_periodic_sync_supported() -> bool {
    let window = match web_sys::window() {
        Some(w) => w,
        None => return false,
    };
    let _ = window.navigator().service_worker();

    let result = js_sys::eval(
        "typeof ServiceWorkerRegistration !== 'undefined' && 'periodicSync' in ServiceWorkerRegistration.prototype",
    );
    result.map(|v| v.is_truthy()).unwrap_or(false)
}

/// Get the current service worker registration, awaiting the `ready` promise.
async fn get_service_worker_registration() -> Result<ServiceWorkerRegistration> {
    let window = web_sys::window().ok_or(SyncError::NotSupported)?;
    let navigator = window.navigator();
    let sw = navigator.service_worker();

    let promise = sw
        .ready()
        .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

    let registration = JsFuture::from(promise)
        .await
        .map_err(|e| SyncError::RegistrationFailed(format!("{e:?}")))?;

    registration
        .dyn_into::<ServiceWorkerRegistration>()
        .map_err(|e| SyncError::RegistrationFailed(format!("Cannot cast: {e:?}")))
}

/// Internal function that replays the offline operation queue.
///
/// This is extracted as a free function so it can be used both by
/// [`SyncService::replay_queue`] and the standalone `spawn_local` call
/// in [`SyncService::init`] without cloning the entire service.
async fn replay_queue_internal(store: SyncStore) -> Result<SyncCycleResult> {
    let operations = store.pending_operations.get();
    let pending: Vec<PendingOperation> = operations
        .into_iter()
        .filter(|op| op.status == "pending")
        .collect();

    if pending.is_empty() {
        return Ok(SyncCycleResult {
            synced_count: 0,
            failed_count: 0,
            errors: Vec::new(),
        });
    }

    let mut synced_count = 0usize;
    let mut failed_count = 0usize;
    let mut errors = Vec::new();

    for operation in &pending {
        if operation.retry_count >= MAX_RETRY_COUNT {
            store.update_operation_status(&operation.id, "failed", Some("Max retries exceeded"));
            failed_count += 1;
            errors.push(SyncOperationResult {
                operation_id: operation.id.clone(),
                success: false,
                error: Some("Max retries exceeded".to_string()),
            });
            continue;
        }

        // Attempt to execute the operation
        match execute_operation(&store, operation).await {
            Ok(()) => {
                store.update_operation_status(&operation.id, "completed", None);
                synced_count += 1;
                errors.push(SyncOperationResult {
                    operation_id: operation.id.clone(),
                    success: true,
                    error: None,
                });
            }
            Err(e) => {
                let error_msg = e.to_string();
                store.increment_retry(&operation.id);
                store.update_operation_status(&operation.id, "pending", Some(&error_msg));
                failed_count += 1;
                errors.push(SyncOperationResult {
                    operation_id: operation.id.clone(),
                    success: false,
                    error: Some(error_msg),
                });
            }
        }
    }

    // Dispatch custom events for UI updates
    dispatch_sync_event("sync-complete", &serde_json::json!({
        "syncedCount": synced_count,
        "failedCount": failed_count,
    }));

    Ok(SyncCycleResult {
        synced_count,
        failed_count,
        errors,
    })
}

/// Execute a single pending operation against the API.
///
/// Creates an [`ApiClient`] using the current window origin, reads the auth
/// token from `localStorage`, and dispatches the operation to the correct
/// backend endpoint based on `entity_type` and `operation_type`.
///
/// # Operation dispatch
///
/// | `operation_type` | HTTP method |
/// |------------------|-------------|
/// | `create`         | POST        |
/// | `update`         | PUT         |
/// | `delete`         | DELETE      |
///
/// The `entity_type` is mapped to an API path via [`entity_api_path`].
async fn execute_operation(
    _store: &SyncStore,
    operation: &PendingOperation,
) -> std::result::Result<(), String> {
    // Build the API base URL from the current window origin.
    let base_url = web_sys::window()
        .and_then(|w| w.location().origin().ok())
        .unwrap_or_else(|| "http://localhost:3000".to_string());

    let mut client = ApiClient::new(&base_url);

    // Read the auth token from localStorage (set by the auth module).
    if let Some(window) = web_sys::window() {
        if let Ok(Some(storage)) = window.local_storage() {
            if let Ok(Some(token)) = storage.get_item("auth_token") {
                client.set_token(&token);
            }
        }
    }

    // Resolve the API path for this entity type.
    let api_path = entity_api_path(&operation.entity_type, operation.entity_id.as_deref());

    // Dispatch based on operation type.
    let result = match operation.operation_type.as_str() {
        "create" => {
            client
                .post::<serde_json::Value, _>(&api_path, &operation.payload)
                .await
                .map_err(|e| format!("POST {} failed: {}", api_path, e))?;
            Ok(())
        }
        "update" => {
            client
                .put::<serde_json::Value, _>(&api_path, &operation.payload)
                .await
                .map_err(|e| format!("PUT {} failed: {}", api_path, e))?;
            Ok(())
        }
        "delete" => {
            client
                .delete::<serde_json::Value>(&api_path)
                .await
                .map_err(|e| format!("DELETE {} failed: {}", api_path, e))?;
            Ok(())
        }
        other => Err(format!(
            "Unknown operation_type '{}' for entity '{}'",
            other, operation.entity_type
        )),
    };

    result
}

/// Map an entity type (and optional entity ID) to the backend API path.
///
/// Known entity types are mapped to their canonical API routes. Unknown
/// types fall back to a generic `/api/v1/{entity_type}s` pattern.
fn entity_api_path(entity_type: &str, entity_id: Option<&str>) -> String {
    let base = match entity_type {
        "ncr" => "/api/v1/quality/ncrs",
        "capa" => "/api/v1/quality/capas",
        "audit" => "/api/v1/quality/audits",
        "inspection" => "/api/v1/quality/inspections",
        "work_order" => "/api/v1/production/work-orders",
        "work_order_operation" => "/api/v1/production/work-order-operations",
        "product" => "/api/v1/products",
        "contact" => "/api/v1/contacts",
        "account" => "/api/v1/accounts",
        "opportunity" => "/api/v1/opportunities",
        "quote" => "/api/v1/quotes",
        "rfq" => "/api/v1/rfqs",
        "invoice" => "/api/v1/finance/invoices",
        "purchase_order" => "/api/v1/supply-chain/purchase-orders",
        "inventory_item" => "/api/v1/inventory/items",
        "maintenance_order" => "/api/v1/maintenance/orders",
        "kanban_card" => "/api/v1/kanban/cards",
        "task" => "/api/v1/tasks",
        "kpi" => "/api/v1/kpi",
        // Generic fallback for unknown entity types.
        other => {
            // Pluralize naively: append 's' if not already plural-ish.
            let plural = if other.ends_with('s') {
                other.to_string()
            } else {
                format!("{}s", other)
            };
            return format!("/api/v1/{}", plural);
        }
    };

    match entity_id {
        Some(id) => format!("{}/{}", base, id),
        None => base.to_string(),
    }
}

/// Dispatch a custom event on the window for UI updates.
fn dispatch_sync_event(event_name: &str, detail: &serde_json::Value) {
    if let Some(window) = web_sys::window() {
        let detail_str = serde_json::to_string(detail).unwrap_or_default();
        let event_init = web_sys::CustomEventInit::new();
        event_init.set_detail(&JsValue::from_str(&detail_str));

        let event = web_sys::CustomEvent::new_with_event_init_dict(event_name, &event_init);
        if let Ok(event) = event {
            let _ = window.dispatch_event(&event);
        }
    }
}

// ── Types ───────────────────────────────────────────────────────────────────

/// How a conflict between local and server state should be resolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConflictResolution {
    /// Keep the local version and re-apply it.
    LocalWins,
    /// Keep the server version and discard the local change.
    ServerWins,
    /// Flag the operation for manual review.
    FlagForReview(String),
}

/// Background sync status descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackgroundSyncStatus {
    /// Whether background sync is supported in this browser.
    pub supported: bool,
    /// Whether periodic sync is supported in this browser.
    pub periodic_supported: bool,
    /// Whether sync is currently in progress.
    pub is_syncing: bool,
    /// Number of pending operations in the queue.
    pub pending_count: usize,
}

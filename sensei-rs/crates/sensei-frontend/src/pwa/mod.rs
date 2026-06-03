//! # PWA / Offline Sync Module
//!
//! Provides Progressive Web App capabilities for the Sensei frontend:
//!
//! - [`indexed_db`] — IndexedDB storage layer with schema versioning and CRUD
//! - [`service_worker`] — Service Worker registration, cache strategies, lifecycle
//! - [`sync`] — Offline sync queue, background/periodic sync, conflict resolution
//!
//! # Initialization
//!
//! Call [`init_pwa`] during application startup (from [`crate::app::App`]) to
//! register the service worker and start the sync engine.

pub mod indexed_db;
pub mod service_worker;
pub mod sync;

use crate::stores::sync::SyncStore;
use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use sync::{BackgroundSyncStatus, SyncService, SyncStatus};

// ── PwaState ────────────────────────────────────────────────────────────────

/// Reactive state for PWA capabilities.
///
/// Mirrors the connectivity, sync, and registration status from the TypeScript
/// [`frontend/src/services/sync-service.ts`](frontend/src/services/sync-service.ts) `BackgroundSyncStatus` interface.
#[derive(Debug, Clone)]
pub struct PwaState {
    /// Whether the browser is currently online.
    pub is_online: RwSignal<bool>,
    /// Current sync engine status.
    pub sync_status: RwSignal<SyncStatus>,
    /// Whether background sync is supported in this browser.
    pub bg_sync_supported: RwSignal<bool>,
    /// Whether periodic sync is supported.
    pub periodic_sync_supported: RwSignal<bool>,
    /// Number of pending operations in the offline queue.
    pub pending_operation_count: RwSignal<usize>,
    /// Service worker registration state.
    pub sw_registration_state: RwSignal<SwRegistrationState>,
}

/// Describes the state of the service worker registration.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SwRegistrationState {
    /// Not yet registered.
    Unregistered,
    /// Registration is in progress.
    Registering,
    /// Successfully registered.
    Registered,
    /// Registration failed with an error message.
    Failed(String),
}

impl Default for SwRegistrationState {
    fn default() -> Self {
        Self::Unregistered
    }
}

impl PwaState {
    /// Create a new `PwaState` with default values.
    pub fn new() -> Self {
        Self {
            is_online: RwSignal::new(true),
            sync_status: RwSignal::new(SyncStatus::Idle),
            bg_sync_supported: RwSignal::new(false),
            periodic_sync_supported: RwSignal::new(false),
            pending_operation_count: RwSignal::new(0),
            sw_registration_state: RwSignal::new(SwRegistrationState::Unregistered),
        }
    }

    /// Get a snapshot of the current background sync status.
    pub fn background_sync_status(&self) -> BackgroundSyncStatus {
        BackgroundSyncStatus {
            supported: self.bg_sync_supported.get(),
            periodic_supported: self.periodic_sync_supported.get(),
            is_syncing: self.sync_status.get() == SyncStatus::Syncing,
            pending_count: self.pending_operation_count.get(),
        }
    }
}

impl Default for PwaState {
    fn default() -> Self {
        Self::new()
    }
}

// ── Initialization ──────────────────────────────────────────────────────────

/// Initialise PWA capabilities.
///
/// This should be called once during application startup:
///
/// ```rust,ignore
/// // In app.rs or main.rs:
/// init_pwa();
/// ```
///
/// It performs the following:
/// 1. Checks for Service Worker and sync API support
/// 2. Registers the service worker if supported
/// 3. Creates the [`SyncService`] and connects it to the [`SyncStore`]
/// 4. Sets up online/offline connectivity listeners
/// 5. Registers background and periodic sync if available
/// 6. Provides the [`PwaState`] as a Leptos context for the component tree
///
/// Returns a [`PwaState`] handle that components can access via
/// `expect_context::<PwaState>()`.
pub fn init_pwa() -> PwaState {
    let pwa_state = PwaState::new();
    provide_context(pwa_state.clone());

    // Check feature support
    let bg_sync_supported = sync::SyncService::is_background_sync_supported();
    let periodic_sync_supported = sync::SyncService::is_periodic_sync_supported();
    let sw_supported = service_worker::is_service_worker_supported();

    pwa_state
        .bg_sync_supported
        .set(bg_sync_supported);
    pwa_state
        .periodic_sync_supported
        .set(periodic_sync_supported);

    // Register the service worker if supported
    if sw_supported {
        pwa_state.sw_registration_state.set(SwRegistrationState::Registering);
        wasm_bindgen_futures::spawn_local({
            let pwa = pwa_state.clone();
            async move {
                match service_worker::register_service_worker().await {
                    Ok(_registration) => {
                        pwa.sw_registration_state
                            .set(SwRegistrationState::Registered);
                        log::info!("[PWA] Service worker registered successfully");
                    }
                    Err(e) => {
                        pwa.sw_registration_state
                            .set(SwRegistrationState::Failed(e.to_string()));
                        log::warn!("[PWA] Service worker registration failed: {e}");
                    }
                }
            }
        });
    }

    // Set up online/offline listeners on the PwaState
    {
        let pwa = pwa_state.clone();
        service_worker::add_online_listener(move || {
            pwa.is_online.set(true);
        });
    }
    {
        let pwa = pwa_state.clone();
        service_worker::add_offline_listener(move || {
            pwa.is_online.set(false);
        });
    }

    // Set initial online state
    pwa_state.is_online.set(service_worker::is_online());

    log::info!(
        "[PWA] Initialised — SW supported: {sw_supported}, BgSync: {bg_sync_supported}, PeriodicSync: {periodic_sync_supported}"
    );

    pwa_state
}

/// Initialize the sync service with the application's sync store.
///
/// Call this after [`init_pwa`] to connect the offline queue to the
/// reactive sync store. This spawns the sync engine which handles
/// queue persistence, background sync registration, and replay on
/// reconnection.
pub async fn init_sync_service(sync_store: SyncStore) -> Result<SyncService, sync::SyncError> {
    let mut sync_service = SyncService::new(sync_store);
    sync_service.init().await?;
    log::info!("[PWA] Sync service initialised");
    Ok(sync_service)
}

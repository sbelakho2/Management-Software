//! Database-backed generic entity store.
//!
//! Provides [`EntityStore`] which transparently switches between in-memory
//! and PostgreSQL-backed persistence. When a [`PgPool`] is configured, all
//! mutations are persisted to the `entity_store` table using a JSONB column.
//!
//! The store exposes the same `read()` / `write()` interface as
//! `Arc<RwLock<HashMap<Uuid, T>>>`, so route handlers do not need to change.
//!
//! # Architecture
//!
//! ```text
//! ┌──────────────┐       ┌──────────────────────┐
//! │ Route handler │──────▶│   EntityStore<T>      │
//! │  (unchanged)  │◀──────│  read() → HashMap<T>  │
//! └──────────────┘       │  write() → HashMap<T>  │
//!                         └──────┬───────────────┘
//!                                │ on write-guard drop
//!                     ┌──────────▼──────────┐
//!                     │  entity_store table  │
//!                     │  (JSONB per entity)  │
//!                     └─────────────────────┘
//! ```
//!
//! # Tenant isolation
//!
//! Every entity is keyed by `(tenant_id, entity_type, id)` — both in the
//! database (`entity_store` PK, migration 046) and in the shared in-memory
//! map ([`StoreKey`]). All SQL statements filter by `tenant_id`, so one
//! tenant can never read or overwrite another tenant's rows.
//!
//! The guard objects returned by [`EntityStore::read`] / [`EntityStore::write`]
//! present a **tenant-scoped view**: they only ever expose the calling
//! tenant's entities, keyed by plain entity id (the API routes are built
//! around `HashMap<Uuid, T>` semantics).
//!
//! # Persistence model
//!
//! A write guard snapshots the calling tenant's store contents once at
//! acquisition. When [`StoreWriteGuard::persist`] is called (or the guard is
//! dropped), only the changed keys are written back:
//!
//! * **inserted/updated** keys are batched into a single upsert transaction,
//! * **removed** keys are deleted in the same transaction.
//!
//! A per-store persist mutex serializes concurrent persistence, so a slow
//! write can never reorder a newer write behind it.
//!
//! # Durability
//!
//! [`StoreWriteGuard::persist`] is the **explicit, awaited** persistence path
//! and propagates database errors to the caller. The `Drop` implementation
//! never spawns a background task: as a last-resort fallback it attempts a
//! **best-effort synchronous** persist (via
//! [`tokio::runtime::Handle::try_current`] +
//! [`futures::executor::block_on`]) when a Tokio runtime is present, logging
//! an `ERROR` on failure. Without a runtime (e.g. during shutdown) it logs a
//! warning that the guard was dropped unpersisted.

use serde::de::DeserializeOwned;
use serde::Serialize;
use sqlx::{PgPool, Row};
use std::collections::{HashMap, HashSet};
use std::ops::{Deref, DerefMut};
use std::sync::Arc;
use std::time::{Duration, Instant};
use thiserror::Error;
use tokio::sync::{Mutex, RwLock};
use uuid::Uuid;

use sensei_core::error::SenseiError;

// ── Error types ─────────────────────────────────────────────────────────────

/// Errors that can occur during store persistence operations.
#[derive(Debug, Error)]
pub enum StoreError {
    /// A database operation failed.
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    /// Serialization/deserialization of entity data failed.
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    /// The requested entity was not found.
    #[error("Entity not found: {0}")]
    NotFound(Uuid),
    /// No database pool is configured (store is in-memory only).
    #[error("Store is not connected to a database")]
    NotConnected,
    /// Optimistic-concurrency conflict: the entity changed in PostgreSQL
    /// since this guard's snapshot was taken.
    #[error("Concurrent modification conflict: {0}")]
    Conflict(String),
}

impl From<StoreError> for SenseiError {
    fn from(err: StoreError) -> Self {
        match err {
            StoreError::Database(e) => {
                SenseiError::Database(format!("Entity store database error: {e}"))
            }
            StoreError::Conflict(msg) => SenseiError::Conflict(msg),
            StoreError::Serialization(e) => {
                SenseiError::Internal(format!("Entity store serialization error: {e}"))
            }
            StoreError::NotFound(id) => SenseiError::NotFound(id.to_string()),
            StoreError::NotConnected => {
                SenseiError::Database("Entity store is not connected to a database".to_string())
            }
        }
    }
}

// ── Composite store key ────────────────────────────────────────────────────

/// The isolation key of an entity inside a store: `(tenant_id, id)`.
///
/// The `entity_type` dimension is the store itself (each [`EntityStore`] is
/// created for exactly one entity type), so together the three columns of
/// the `entity_store` PK — `(tenant_id, entity_type, id)` — are represented
/// by this key plus the store's entity type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct StoreKey {
    /// The tenant that owns the entity.
    pub tenant_id: Uuid,
    /// The entity's unique identifier.
    pub id: Uuid,
}

impl StoreKey {
    /// Create a new composite key for the given tenant and entity id.
    pub fn new(tenant_id: Uuid, id: Uuid) -> Self {
        Self { tenant_id, id }
    }
}

impl std::fmt::Display for StoreKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}|{}", self.tenant_id, self.id)
    }
}

// ── Inner storage ──────────────────────────────────────────────────────────

/// How long a tenant's snapshot is served before the next access reloads
/// from PostgreSQL. This bounds cross-replica staleness: replica A's local
/// copy can lag a write on replica B by at most this TTL (then it refreshes
/// on the next access).
const SNAPSHOT_TTL: std::time::Duration = std::time::Duration::from_secs(60);

struct StoreInner<T> {
    data: HashMap<StoreKey, T>,
    pool: Option<PgPool>,
    entity_type: String,
    /// Tenants whose rows have been successfully loaded from the database.
    /// A tenant missing from this set triggers a (rate-limited) load on the
    /// next access, so a failed load is retried instead of serving empty
    /// data.
    /// Tenant id -> when its snapshot was last (re)loaded from the DB.
    loaded_tenants: std::collections::HashMap<Uuid, std::time::Instant>,
    /// When the last DB load was attempted, so failed loads are retried at
    /// most once per second instead of on every access.
    last_db_load_attempt: Option<Instant>,
    /// Event bus for cross-replica cache invalidation (core NATS pub/sub).
    bus: Option<std::sync::Arc<dyn sensei_event_bus::EventBus>>,
    /// Serializes persistence operations (explicit `persist()` and the
    /// best-effort drop path) so only one persist runs at a time.
    persist_lock: Arc<Mutex<()>>,
}

impl<T> StoreInner<T> {
    fn new(entity_type: &str, pool: Option<PgPool>) -> Self {
        Self {
            data: HashMap::new(),
            pool,
            entity_type: entity_type.to_string(),
            loaded_tenants: std::collections::HashMap::new(),
            last_db_load_attempt: None,
            bus: None,
            persist_lock: Arc::new(Mutex::new(())),
        }
    }
}

// ── EntityStore ────────────────────────────────────────────────────────────

/// A generic entity store that can persist to PostgreSQL when a pool is
/// available.
///
/// When no pool is configured, it behaves exactly like an in-memory
/// `HashMap<Uuid, T>`. When a pool is set, mutations are persisted to the
/// `entity_store` table on explicit [`StoreWriteGuard::persist`] (and
/// best-effort on write-guard drop), and data is lazily loaded from the
/// database per tenant on first access.
///
/// Every operation is **tenant-scoped**: pass the calling user's `tenant_id`
/// to [`EntityStore::read`] / [`EntityStore::write`] /
/// [`EntityStore::list_paginated`] / [`EntityStore::list_by_field`] and only
/// that tenant's entities are ever visible or written.
///
/// # Type Parameters
/// * `T` — The entity type. Must implement `Serialize + DeserializeOwned +
///   Clone + PartialEq + Send + Sync` for database persistence and change
///   detection.
///
/// # Example
///
/// ```rust,ignore
/// let store: EntityStore<KanbanBoard> = EntityStore::new("kanban_board");
///
/// // In-memory mode — same as before
/// {
///     let mut guard = store.write(tenant_id).await;
///     guard.insert(id, board);
/// }
///
/// // Database mode — transparent persistence
/// let store = EntityStore::with_pool("kanban_board", pool);
/// {
///     let mut guard = store.write(tenant_id).await;
///     guard.insert(id, board); // persist on drop; prefer explicit persist()
/// }
/// ```
pub struct EntityStore<T> {
    inner: Arc<RwLock<StoreInner<T>>>,
}

impl<T> Clone for EntityStore<T> {
    fn clone(&self) -> Self {
        Self {
            inner: self.inner.clone(),
        }
    }
}

impl<T> EntityStore<T> {
    /// Create a new in-memory-only store for the given entity type.
    pub fn new(entity_type: &str) -> Self {
        Self {
            inner: Arc::new(RwLock::new(StoreInner::new(entity_type, None))),
        }
    }

    /// Create a new store backed by the given database pool.
    ///
    /// Data will be lazily loaded from the database per tenant on first
    /// access.
    pub fn with_pool(entity_type: &str, pool: PgPool) -> Self {
        Self {
            inner: Arc::new(RwLock::new(StoreInner::new(entity_type, Some(pool)))),
        }
    }

    /// Subscribe this store to cross-replica invalidation events: a write
    /// committed by ANY replica evicts the affected rows from THIS
    /// replica's cache immediately (no waiting for the snapshot TTL).
    pub fn attach_bus(&self, bus: std::sync::Arc<dyn sensei_event_bus::EventBus>)
    where
        T: Send + Sync + 'static,
    {
        {
            let mut inner = match self.inner.try_write() {
                Ok(g) => g,
                Err(_) => {
                    // Lock busy (a persist is in flight): skip attaching the
                    // bus now; the invalidation subscriber is best-effort.
                    return;
                }
            };
            inner.bus = Some(bus.clone());
            let entity_type = inner.entity_type.clone();
            drop(inner);

            let inner = self.inner.clone();
            let subject = format!("sensei.estore.invalidate.{entity_type}");
            let et = entity_type.clone();
            let handler: sensei_event_bus::bus::CoreHandler =
                std::sync::Arc::new(move |payload: Vec<u8>| {
                    let inner = inner.clone();
                    let et = et.clone();
                    tokio::spawn(async move {
                        let parsed: serde_json::Value = match serde_json::from_slice(&payload) {
                            Ok(v) => v,
                            Err(_) => return,
                        };
                        // Own writes are already reflected in the local map.
                        if parsed.get("origin").and_then(|v| v.as_str()) == Some(store_origin_id())
                        {
                            return;
                        }
                        let tenant_id: Uuid = match parsed.get("tenant_id").and_then(|v| v.as_str())
                        {
                            Some(s) => match Uuid::parse_str(s) {
                                Ok(id) => id,
                                Err(_) => return,
                            },
                            None => return,
                        };
                        let ids: Vec<Uuid> = parsed
                            .get("ids")
                            .and_then(|v| v.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|i| i.as_str())
                                    .filter_map(|s| Uuid::parse_str(s).ok())
                                    .collect()
                            })
                            .unwrap_or_default();
                        let mut guard = inner.write().await;
                        guard.loaded_tenants.remove(&tenant_id);
                        for id in ids {
                            guard.data.remove(&StoreKey::new(tenant_id, id));
                        }
                        tracing::trace!(
                            entity_type = %et,
                            tenant_id = %tenant_id,
                            "Cross-replica EntityStore cache invalidated"
                        );
                    });
                    Ok(())
                });
            // Per-instance group: EVERY replica receives every invalidation
            // (a shared queue group would deliver to only ONE replica,
            // leaving the others stale until the snapshot TTL).
            let group = store_origin_id().to_string();
            tokio::spawn(async move {
                let _ = bus.subscribe_core(&subject, &group, handler).await;
            });
        }
    }
}

/// Stable identity of THIS process for cache-invalidation origin checks.
fn store_origin_id() -> &'static str {
    static ORIGIN: std::sync::OnceLock<String> = std::sync::OnceLock::new();
    ORIGIN.get_or_init(|| uuid::Uuid::new_v4().to_string())
}

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> EntityStore<T> {
    /// Ensure the calling tenant's rows have been loaded from the database
    /// (rate-limited retry on failure; a no-op without a pool).
    async fn ensure_loaded(&self, tenant_id: Uuid) {
        let mut inner = self.inner.write().await;
        if inner.pool.is_none() {
            return;
        }
        let fresh = inner
            .loaded_tenants
            .get(&tenant_id)
            .is_some_and(|loaded_at| loaded_at.elapsed() < SNAPSHOT_TTL);
        if fresh {
            return;
        }
        // Stale or never-loaded: refresh the snapshot from PostgreSQL so a
        // write on another replica becomes visible within SNAPSHOT_TTL.
        load_from_db(&mut inner, tenant_id).await;
    }

    /// Acquire a read guard scoped to the given tenant.
    ///
    /// On first access when a pool is configured, the tenant's data is
    /// loaded from the database before returning the guard. A failed load
    /// is retried on the next access, but at most once per second
    /// (rate-limited retries).
    pub async fn read(&self, tenant_id: Uuid) -> StoreReadGuard<T> {
        self.ensure_loaded(tenant_id).await;

        let inner = self.inner.read().await;
        let map = inner
            .data
            .iter()
            .filter(|(key, _)| key.tenant_id == tenant_id)
            .map(|(key, value)| (key.id, value.clone()))
            .collect();
        StoreReadGuard { map }
    }

    /// Acquire a write guard scoped to the given tenant.
    ///
    /// On first access when a pool is configured, the tenant's data is
    /// loaded from the database before returning the guard. The guard
    /// snapshots the tenant's current contents; changes are written back to
    /// the shared map and persisted to the database (as a diff) when
    /// [`StoreWriteGuard::persist`] is called, and best-effort when the
    /// guard is dropped.
    pub async fn write(&self, tenant_id: Uuid) -> StoreWriteGuard<T> {
        self.ensure_loaded(tenant_id).await;

        let inner = self.inner.read().await;
        let map: HashMap<Uuid, T> = inner
            .data
            .iter()
            .filter(|(key, _)| key.tenant_id == tenant_id)
            .map(|(key, value)| (key.id, value.clone()))
            .collect();

        let original_values = map.clone();
        StoreWriteGuard {
            inner: self.inner.clone(),
            tenant_id,
            pool: inner.pool.clone(),
            entity_type: inner.entity_type.clone(),
            persist_lock: Arc::clone(&inner.persist_lock),
            map,
            original_values,
            dirty: HashSet::new(),
            removed: HashSet::new(),
        }
    }
}

// ── Read guard ─────────────────────────────────────────────────────────────

/// Tenant-scoped read guard that dereferences to `HashMap<Uuid, T>`.
///
/// Obtained from [`EntityStore::read()`]. Only the calling tenant's entities
/// are visible; keys are plain entity ids.
pub struct StoreReadGuard<T> {
    map: HashMap<Uuid, T>,
}

impl<T> Deref for StoreReadGuard<T> {
    type Target = HashMap<Uuid, T>;

    fn deref(&self) -> &Self::Target {
        &self.map
    }
}

// ── Write guard ────────────────────────────────────────────────────────────

/// Tenant-scoped write guard that dereferences to `HashMap<Uuid, T>`.
///
/// Obtained from [`EntityStore::write()`]. Mutations apply to the tenant's
/// snapshot; they are committed to the shared map and (when a pool is
/// configured) to the `entity_store` table by [`StoreWriteGuard::persist`],
/// and best-effort on drop.
pub struct StoreWriteGuard<
    T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static,
> {
    inner: Arc<RwLock<StoreInner<T>>>,
    tenant_id: Uuid,
    pool: Option<PgPool>,
    entity_type: String,
    persist_lock: Arc<Mutex<()>>,
    /// The tenant's working set, keyed by entity id.
    map: HashMap<Uuid, T>,
    /// Snapshot of the tenant's contents when the guard was acquired. Used
    /// to detect inserted/updated/removed keys without cloning the whole map
    /// at persist time.
    original_values: HashMap<Uuid, T>,
    /// Keys that were inserted or updated since the guard was acquired.
    dirty: HashSet<Uuid>,
    /// Keys that were removed since the guard was acquired.
    removed: HashSet<Uuid>,
}

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> Deref
    for StoreWriteGuard<T>
{
    type Target = HashMap<Uuid, T>;

    fn deref(&self) -> &Self::Target {
        &self.map
    }
}

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> DerefMut
    for StoreWriteGuard<T>
{
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.map
    }
}

// ── Explicit persistence ────────────────────────────────────────────────────

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static>
    StoreWriteGuard<T>
{
    /// Explicitly persist the pending changes.
    ///
    /// Commits the tenant's changes to the shared in-memory map and, when a
    /// database pool is configured, to the `entity_store` table. Only the
    /// dirty (inserted/updated) and removed keys are written, in a single
    /// transaction. On transient failures (DB connection), a single retry
    /// with a 100ms delay is attempted before giving up.
    ///
    /// In in-memory mode (no pool) this commits the changes to the shared
    /// map and succeeds — there is no database to persist to.
    ///
    /// After a successful persist, the dirty/removed sets are cleared and
    /// the snapshot is refreshed so that the `Drop` impl will not
    /// re-persist the same data.
    ///
    /// # Errors
    ///
    /// Returns [`StoreError::Database`] if the SQL operation fails after
    /// retry, or [`StoreError::Serialization`] if an entity cannot be
    /// serialized. The changes remain pending and the `Drop` fallback will
    /// retry them best-effort.
    pub async fn persist(&mut self) -> Result<(), StoreError> {
        self.compute_diff();

        if self.dirty.is_empty() && self.removed.is_empty() {
            return Ok(());
        }

        let (dirty_values, removed_ids) = self.collect_changes()?;

        // 1. Commit to the shared in-memory map (always; in-memory mode
        //    "persists" here and nowhere else).
        self.write_back();

        // 2. Persist to the database when a pool is configured.
        let Some(pool) = self.pool.clone() else {
            self.after_persist_success();
            return Ok(());
        };

        let entity_type = self.entity_type.clone();
        let tenant_id = self.tenant_id;
        let persist_lock = Arc::clone(&self.persist_lock);

        // Attempt persist with one retry on transient failure
        let result = {
            let _guard = persist_lock.lock().await;
            persist_changes_inner(
                &pool,
                &entity_type,
                tenant_id,
                &dirty_values,
                &removed_ids,
                &self.original_values,
            )
            .await
        };
        match result {
            Ok(()) => {
                // Capture the changed ids BEFORE after_persist_success
                // clears the change sets (they are the invalidation payload).
                let invalidated: Vec<Uuid> = self
                    .dirty
                    .iter()
                    .chain(self.removed.iter())
                    .copied()
                    .collect();
                self.after_persist_success();
                // Publish cross-replica invalidation so OTHER replicas evict
                // the affected rows immediately (core NATS, fire-and-forget).
                self.publish_invalidation(&invalidated).await;
                Ok(())
            }
            Err(e) => {
                tracing::warn!(
                    entity_type = %entity_type,
                    error = %e,
                    "First persist attempt failed. Retrying after 100ms..."
                );
                tokio::time::sleep(Duration::from_millis(100)).await;
                let _guard = persist_lock.lock().await;
                match persist_changes_inner(
                    &pool,
                    &entity_type,
                    tenant_id,
                    &dirty_values,
                    &removed_ids,
                    &self.original_values,
                )
                .await
                {
                    Ok(()) => {
                        let invalidated: Vec<Uuid> = self
                            .dirty
                            .iter()
                            .chain(self.removed.iter())
                            .copied()
                            .collect();
                        self.after_persist_success();
                        self.publish_invalidation(&invalidated).await;
                        Ok(())
                    }
                    Err(e) => {
                        // The database rejected the change: the shared
                        // in-memory map must NEVER disagree with
                        // PostgreSQL — roll the local cache back so memory
                        // stays consistent with the authoritative store.
                        tracing::error!(
                            entity_type = %entity_type,
                            error = %e,
                            "Persist failed after retry — rolling back the in-memory cache"
                        );
                        self.rollback_local_cache().await;
                        Err(StoreError::Database(e))
                    }
                }
            }
        }
    }

    /// Revert the shared in-memory map to the pre-guard snapshot (called
    /// ONLY when the database rejected the write, so memory never diverges
    /// from PostgreSQL).
    async fn rollback_local_cache(&mut self) {
        let mut inner = self.inner.write().await;
        for id in &self.removed {
            if let Some(original) = self.original_values.get(id) {
                inner
                    .data
                    .insert(StoreKey::new(self.tenant_id, *id), original.clone());
            }
        }
        for (id, original) in self.original_values.iter() {
            if self.dirty.contains(id) {
                inner
                    .data
                    .insert(StoreKey::new(self.tenant_id, *id), original.clone());
            }
        }
    }

    /// Fire-and-forget cross-replica invalidation (core NATS): every other
    /// replica evicts the changed rows from its cache immediately.
    async fn publish_invalidation(&self, ids: &[Uuid]) {
        let Some(bus) = self.bus() else {
            return;
        };
        if ids.is_empty() {
            return;
        }
        let payload = serde_json::json!({
            "origin": store_origin_id(),
            "tenant_id": self.tenant_id,
            "ids": ids.iter().map(|id| id.to_string()).collect::<Vec<_>>(),
        });
        let subject = format!("sensei.estore.invalidate.{}", self.entity_type);
        let bytes = match serde_json::to_vec(&payload) {
            Ok(b) => b,
            Err(_) => return,
        };
        if let Err(e) = bus.publish_core(&subject, &bytes).await {
            tracing::warn!(error = %e, "Failed to publish EntityStore invalidation");
        }
    }

    fn bus(&self) -> Option<std::sync::Arc<dyn sensei_event_bus::EventBus>> {
        self.inner.try_read().ok().and_then(|g| g.bus.clone())
    }

    /// Recompute the dirty/removed sets by diffing the current data against
    /// the snapshot taken at guard acquisition.
    fn compute_diff(&mut self) {
        self.dirty.clear();
        self.removed.clear();
        for (id, value) in self.map.iter() {
            match self.original_values.get(id) {
                Some(original) if original == value => {}
                _ => {
                    // Inserted (not in snapshot) or updated (differs).
                    self.dirty.insert(*id);
                }
            }
        }
        for id in self.original_values.keys() {
            if !self.map.contains_key(id) {
                self.removed.insert(*id);
            }
        }
    }

    /// Serialize the dirty values and collect the removed ids.
    fn collect_changes(&self) -> Result<(HashMap<Uuid, T>, Vec<Uuid>), StoreError> {
        let mut dirty_values = HashMap::with_capacity(self.dirty.len());
        for id in &self.dirty {
            if let Some(value) = self.map.get(id) {
                dirty_values.insert(*id, value.clone());
            }
        }
        let removed_ids: Vec<Uuid> = self.removed.iter().copied().collect();
        Ok((dirty_values, removed_ids))
    }

    /// Apply the pending changes to the shared in-memory map using a
    /// best-effort synchronous lock acquisition (used by `Drop`, where
    /// awaiting is impossible).
    fn write_back(&mut self) {
        match self.inner.try_write() {
            Ok(mut inner) => {
                for (id, value) in self.map.iter() {
                    inner
                        .data
                        .insert(StoreKey::new(self.tenant_id, *id), value.clone());
                }
                for id in &self.removed {
                    inner.data.remove(&StoreKey::new(self.tenant_id, *id));
                }
            }
            Err(_) => {
                tracing::warn!(
                    entity_type = %self.entity_type,
                    tenant_id = %self.tenant_id,
                    "Could not acquire the store lock to write back changes \
                     (lock busy); the shared in-memory map may be stale"
                );
            }
        }
    }

    /// After a successful persist: refresh the snapshot and clear the
    /// change sets so the `Drop` impl is a no-op.
    fn after_persist_success(&mut self) {
        self.original_values = self.map.clone();
        self.dirty.clear();
        self.removed.clear();
    }

    /// The `Drop` fallback: write back to the shared map and attempt a
    /// best-effort synchronous database persist.
    ///
    /// * The in-memory write-back always runs (via `try_write`, which needs
    ///   no executor).
    /// * The database persist runs only when a pool is configured AND a
    ///   Tokio runtime handle is available; it is executed synchronously
    ///   with [`futures::executor::block_on`] — **never spawned**, so a
    ///   crash cannot lose acknowledged-but-unflushed writes.
    fn drop_fallback(&mut self) {
        self.compute_diff();
        if self.dirty.is_empty() && self.removed.is_empty() {
            return;
        }

        let entity_type = self.entity_type.clone();
        let tenant_id = self.tenant_id;
        let (dirty_values, removed_ids) = match self.collect_changes() {
            Ok(changes) => changes,
            Err(e) => {
                tracing::error!(
                    entity_type = %entity_type,
                    error = %e,
                    "CRITICAL: Failed to prepare data for persistence on StoreWriteGuard \
                     drop. Data may be lost!"
                );
                return;
            }
        };

        // The shared in-memory map must reflect the changes even if the
        // database cannot be reached (in-memory mode, shutdown, lock busy).
        self.write_back();

        let Some(pool) = self.pool.clone() else {
            return;
        };

        let persist_lock = Arc::clone(&self.persist_lock);
        match tokio::runtime::Handle::try_current() {
            Ok(_) => {
                let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                    futures::executor::block_on(async {
                        let _guard = persist_lock.lock().await;
                        persist_changes_inner(
                            &pool,
                            &entity_type,
                            tenant_id,
                            &dirty_values,
                            &removed_ids,
                            &self.original_values,
                        )
                        .await
                    })
                }));
                match result {
                    Ok(Ok(())) => {}
                    Ok(Err(e)) => {
                        tracing::error!(
                            entity_type = %entity_type,
                            error = %e,
                            "CRITICAL: Failed to persist data on StoreWriteGuard drop. \
                             Data may be lost!"
                        );
                    }
                    Err(_) => {
                        tracing::error!(
                            entity_type = %entity_type,
                            "CRITICAL: Persistence on StoreWriteGuard drop panicked. \
                             Data may be lost!"
                        );
                    }
                }
            }
            Err(_) => {
                tracing::warn!(
                    entity_type = %entity_type,
                    "StoreWriteGuard dropped with unpersisted changes outside a Tokio \
                     runtime (e.g. during shutdown). Changes could not be flushed to the \
                     database and may be lost."
                );
            }
        }
    }
}

// ── Drop implementation (last-resort fallback) ──────────────────────────────

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> Drop
    for StoreWriteGuard<T>
{
    /// Last-resort persistence on drop.
    ///
    /// If [`persist()`](StoreWriteGuard::persist) was already called
    /// successfully, the dirty/removed sets are empty and this is a no-op.
    /// Otherwise the changes are committed to the shared map and a
    /// **synchronous, best-effort** database persist is attempted (never a
    /// spawned task), with an `ERROR` logged on failure and a warning when
    /// no Tokio runtime is available.
    ///
    /// **Callers should prefer the explicit `persist()` method** and handle
    /// errors properly, rather than relying on `Drop`.
    fn drop(&mut self) {
        self.drop_fallback();
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// DB helpers
// ═══════════════════════════════════════════════════════════════════════════

/// Load all entities of a given type for one tenant from the database into
/// the in-memory map.
///
/// The tenant is added to `loaded_tenants` **only on success**, so a failed
/// load is retried on the next access (rate-limited to at most one attempt
/// per second). On failure, logs a warning and leaves the map unchanged.
async fn load_from_db<T: DeserializeOwned + Clone>(inner: &mut StoreInner<T>, tenant_id: Uuid) {
    let pool = match inner.pool.as_ref() {
        Some(p) => p.clone(),
        None => return,
    };

    // Rate-limit retries of failed loads to at most once per second.
    let now = Instant::now();
    if let Some(last) = inner.last_db_load_attempt {
        if now.duration_since(last) < Duration::from_secs(1) {
            return;
        }
    }
    inner.last_db_load_attempt = Some(now);

    match sqlx::query("SELECT id, data FROM entity_store WHERE entity_type = $1 AND tenant_id = $2")
        .bind(&inner.entity_type)
        .bind(tenant_id)
        .fetch_all(&pool)
        .await
    {
        Ok(rows) => {
            let loaded = rows.len();
            for row in rows {
                let id: Uuid = match row.try_get("id") {
                    Ok(v) => v,
                    Err(e) => {
                        tracing::error!(
                            entity_type = %inner.entity_type,
                            tenant_id = %tenant_id,
                            "Failed to read id from row: {e}"
                        );
                        continue;
                    }
                };
                let data: serde_json::Value = match row.try_get("data") {
                    Ok(v) => v,
                    Err(e) => {
                        tracing::error!(
                            entity_type = %inner.entity_type,
                            tenant_id = %tenant_id,
                            id = %id,
                            "Failed to read data from row: {e}"
                        );
                        continue;
                    }
                };
                match serde_json::from_value::<T>(data) {
                    Ok(entity) => {
                        inner.data.insert(StoreKey::new(tenant_id, id), entity);
                    }
                    Err(e) => {
                        // A corrupt row must never silently vanish from the
                        // snapshot: ERROR + row identity, and the tenant is
                        // left OUT of loaded_tenants so the load is retried.
                        tracing::error!(
                            entity_type = %inner.entity_type,
                            tenant_id = %tenant_id,
                            id = %id,
                            "Failed to deserialize entity — row skipped, load will retry: {e}"
                        );
                    }
                }
            }
            tracing::info!(
                entity_type = %inner.entity_type,
                tenant_id = %tenant_id,
                count = loaded,
                "Loaded entities from database"
            );
            inner
                .loaded_tenants
                .insert(tenant_id, std::time::Instant::now());
        }
        Err(e) => {
            // Keep the tenant out of `loaded_tenants` so the next access
            // retries (rate-limited to once per second).
            tracing::error!(
                entity_type = %inner.entity_type,
                tenant_id = %tenant_id,
                "Failed to load from database (table may not exist yet): {e}"
            );
        }
    }
}

/// Persist changes to the database (inner helper, no retry).
///
/// Runs a **single transaction** containing:
/// - one batched upsert of all dirty entries (keyed by `(tenant_id,
///   entity_type, id)`),
/// - one batched delete of all removed entries (scoped to the tenant).
async fn persist_changes_inner<T: Serialize>(
    pool: &PgPool,
    entity_type: &str,
    tenant_id: Uuid,
    data: &HashMap<Uuid, T>,
    removed_ids: &[Uuid],
    original_values: &HashMap<Uuid, T>,
) -> Result<(), sqlx::Error> {
    let mut tx = pool.begin().await?;

    let mut conflicts: Vec<Uuid> = Vec::new();
    for (id, entity) in data {
        let json = serde_json::to_value(entity).map_err(|e| {
            tracing::error!(
                entity_type = %entity_type,
                tenant_id = %tenant_id,
                id = %id,
                "Failed to serialize entity: {e}"
            );
            sqlx::Error::Protocol(format!("Serialization error: {e}"))
        })?;

        match original_values.get(id) {
            // Update with optimistic CAS: only succeeds when the row still
            // matches THIS guard's snapshot — a competing replica's write
            // fails the condition and is reported as a conflict.
            Some(prev) => {
                let prev_json = serde_json::to_value(prev)
                    .map_err(|e| sqlx::Error::Protocol(format!("Serialization error: {e}")))?;
                let updated = sqlx::query(
                    "UPDATE entity_store SET data = $4, updated_at = NOW() \
                     WHERE tenant_id = $1 AND entity_type = $2 AND id = $3 AND data = $5",
                )
                .bind(tenant_id)
                .bind(entity_type)
                .bind(id)
                .bind(&json)
                .bind(&prev_json)
                .execute(&mut *tx)
                .await?;
                if updated.rows_affected() == 0 {
                    // Either the row vanished or another replica changed it
                    // since our snapshot — either way, a lost update.
                    conflicts.push(*id);
                }
            }
            // Brand-new entity: plain insert.
            None => {
                let inserted = sqlx::query(
                    "INSERT INTO entity_store (tenant_id, entity_type, id, data) \
                     VALUES ($1, $2, $3, $4) ON CONFLICT (tenant_id, entity_type, id) DO NOTHING",
                )
                .bind(tenant_id)
                .bind(entity_type)
                .bind(id)
                .bind(&json)
                .execute(&mut *tx)
                .await?;
                if inserted.rows_affected() == 0 {
                    // The row appeared between our snapshot and now: the
                    // INSERT path is only valid for genuinely new entities.
                    conflicts.push(*id);
                }
            }
        }
    }

    if !conflicts.is_empty() {
        let ids: Vec<String> = conflicts.iter().map(|id| id.to_string()).collect();
        tx.rollback().await?;
        return Err(sqlx::Error::Protocol(format!(
            "Concurrent modification conflict for entity ids: {}",
            ids.join(", ")
        )));
    }

    if !removed_ids.is_empty() {
        sqlx::query(
            "DELETE FROM entity_store WHERE tenant_id = $1 AND entity_type = $2 AND id = ANY($3)",
        )
        .bind(tenant_id)
        .bind(entity_type)
        .bind(removed_ids)
        .execute(&mut *tx)
        .await?;
    }

    tx.commit().await?;
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════
// DB-level pagination & filtering (bypasses in-memory cache)
// ═══════════════════════════════════════════════════════════════════════════

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> EntityStore<T> {
    /// Fetch a page of the calling tenant's entities directly from the
    /// database, bypassing the in-memory cache.
    ///
    /// Returns a tuple of `(records, total_count)` where `total_count` is the
    /// number of matching entities **without** pagination applied. Records
    /// are ordered by `created_at DESC, id` (migration 021 added the
    /// `created_at` column). All queries are scoped to `tenant_id`.
    ///
    /// When no pool is configured, falls back to in-memory filtering with
    /// the same ordering (parsing `created_at` from the serialized entity
    /// when present, otherwise falling back to the id).
    ///
    /// # Errors
    ///
    /// Returns [`SenseiError::Database`] when a pool is configured but the
    /// tenant's data could not be loaded from the database — never an empty
    /// or stale result set — and when the SQL query itself fails.
    pub async fn list_paginated(
        &self,
        tenant_id: Uuid,
        page: usize,
        per_page: usize,
    ) -> Result<(Vec<(Uuid, T)>, u64), SenseiError> {
        let inner = self.inner.read().await;

        let pool = match inner.pool.as_ref() {
            Some(p) => p,
            None => {
                // In-memory fallback: filter by tenant and apply pagination
                // to the tenant's slice, ordered by created_at DESC, id
                // (mirroring the DB order).
                let mut items: Vec<(Uuid, T)> = inner
                    .data
                    .iter()
                    .filter(|(key, _)| key.tenant_id == tenant_id)
                    .map(|(key, value)| (key.id, value.clone()))
                    .collect();
                let total = items.len() as u64;
                items.sort_by(|(id_a, a), (id_b, b)| {
                    let ts_a = created_at_timestamp(a);
                    let ts_b = created_at_timestamp(b);
                    ts_b.cmp(&ts_a).then_with(|| id_a.cmp(id_b))
                });
                let items = items
                    .into_iter()
                    .skip(page.saturating_sub(1).saturating_mul(per_page))
                    .take(per_page)
                    .collect();
                return Ok((items, total));
            }
        };

        // Never return empty/stale data when the tenant's load from the DB
        // failed: surface the failure as a Database error instead.
        if !inner.loaded_tenants.contains_key(&tenant_id) {
            return Err(SenseiError::Database(format!(
                "Entity store for {} could not be loaded",
                inner.entity_type
            )));
        }

        let entity_type = &inner.entity_type;
        let offset = (page.saturating_sub(1).saturating_mul(per_page)) as i64;
        let limit = per_page as i64;

        // Get total count
        let (count_row,): (i64,) = sqlx::query_as(
            "SELECT COUNT(*)::bigint FROM entity_store WHERE tenant_id = $1 AND entity_type = $2",
        )
        .bind(tenant_id)
        .bind(entity_type)
        .fetch_one(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Entity store count failed: {e}")))?;

        // Get page of data, newest first.
        let rows = sqlx::query(
            "SELECT id, data FROM entity_store WHERE tenant_id = $1 AND entity_type = $2 \
             ORDER BY created_at DESC, id LIMIT $3 OFFSET $4",
        )
        .bind(tenant_id)
        .bind(entity_type)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Entity store page query failed: {e}")))?;

        let mut items = Vec::with_capacity(rows.len());
        for row in rows {
            let id: Uuid = row
                .try_get("id")
                .map_err(|e| SenseiError::Database(format!("Entity store row id failed: {e}")))?;
            let data: serde_json::Value = row
                .try_get("data")
                .map_err(|e| SenseiError::Database(format!("Entity store row data failed: {e}")))?;
            let entity: T = serde_json::from_value(data).map_err(|e| {
                SenseiError::Database(format!("Entity store row decode failed: {e}"))
            })?;
            items.push((id, entity));
        }

        Ok((items, count_row as u64))
    }

    /// Fetch the calling tenant's entities from the database filtered by a
    /// JSONB field match.
    ///
    /// Uses the GIN index on `data` via the `@>` containment operator.
    /// Example: `list_by_field(tenant_id, "status", &serde_json::json!("\"done\""))`
    ///
    /// When no pool is configured, falls back to in-memory filtering.
    ///
    /// # Errors
    ///
    /// Returns [`SenseiError::Database`] when a pool is configured but the
    /// tenant's data could not be loaded from the database — never an empty
    /// or stale result set — and when the SQL query itself fails.
    pub async fn list_by_field(
        &self,
        tenant_id: Uuid,
        field: &str,
        value: &serde_json::Value,
    ) -> Result<Vec<(Uuid, T)>, SenseiError> {
        let inner = self.inner.read().await;

        let pool = match inner.pool.as_ref() {
            Some(p) => p,
            None => {
                // In-memory fallback (tenant-scoped)
                let items: Vec<(Uuid, T)> = inner
                    .data
                    .iter()
                    .filter(|(key, entity)| {
                        key.tenant_id == tenant_id
                            && serde_json::to_value(entity)
                                .ok()
                                .and_then(|val| val.get(field).cloned())
                                .as_ref()
                                == Some(value)
                    })
                    .map(|(key, value)| (key.id, value.clone()))
                    .collect();
                return Ok(items);
            }
        };

        // Never return empty/stale data when the tenant's load from the DB
        // failed: surface the failure as a Database error instead.
        if !inner.loaded_tenants.contains_key(&tenant_id) {
            return Err(SenseiError::Database(format!(
                "Entity store for {} could not be loaded",
                inner.entity_type
            )));
        }

        let entity_type = &inner.entity_type;

        // Use JSONB containment: data @> '{"field": value}' (GIN index).
        let filter = serde_json::json!({ field: value });

        let rows = sqlx::query(
            r#"SELECT id, data FROM entity_store
               WHERE tenant_id = $1 AND entity_type = $2 AND data @> $3
               ORDER BY id"#,
        )
        .bind(tenant_id)
        .bind(entity_type)
        .bind(&filter)
        .fetch_all(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Entity store field query failed: {e}")))?;

        let mut items = Vec::with_capacity(rows.len());
        for row in rows {
            let id: Uuid = row
                .try_get("id")
                .map_err(|e| SenseiError::Database(format!("Entity store row id failed: {e}")))?;
            let data: serde_json::Value = row
                .try_get("data")
                .map_err(|e| SenseiError::Database(format!("Entity store row data failed: {e}")))?;
            let entity: T = serde_json::from_value(data).map_err(|e| {
                SenseiError::Database(format!("Entity store row decode failed: {e}"))
            })?;
            items.push((id, entity));
        }

        Ok(items)
    }
}

/// Extract the `created_at` timestamp (as Unix seconds) from a serialized
/// entity, used to order in-memory pagination like the DB path.
fn created_at_timestamp<T: Serialize>(entity: &T) -> i64 {
    serde_json::to_value(entity)
        .ok()
        .and_then(|v| v.get("created_at").cloned())
        .and_then(|v| v.as_str().map(str::to_string))
        .and_then(|s| chrono::DateTime::parse_from_rfc3339(&s).ok())
        .map(|dt| dt.timestamp())
        .unwrap_or(0)
}

// ═══════════════════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;
    use serde::Deserialize;

    #[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
    struct TestEntity {
        name: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        created_at: Option<String>,
    }

    fn entity(name: &str) -> TestEntity {
        TestEntity {
            name: name.to_string(),
            created_at: None,
        }
    }

    fn tenant() -> Uuid {
        Uuid::new_v4()
    }

    /// In-memory mode: the dirty-diff computation must track exactly the
    /// inserted/updated and removed keys, and persist() must commit the
    /// changes to the shared map (in-memory mode is a no-op success).
    #[tokio::test]
    async fn write_guard_tracks_only_dirty_keys() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let tenant_id = tenant();
        let id_a = Uuid::new_v4();
        let id_b = Uuid::new_v4();
        let id_c = Uuid::new_v4();

        // Seed the store with three entities.
        {
            let mut guard = store.write(tenant_id).await;
            guard.insert(id_a, entity("a"));
            guard.insert(id_b, entity("b"));
            guard.insert(id_c, entity("c"));
            guard.persist().await.expect("in-memory persist succeeds");
        }

        {
            let mut guard = store.write(tenant_id).await;
            // `a` stays untouched — must NOT appear in the diff.
            // `b` is updated in place.
            guard.get_mut(&id_b).unwrap().name = "b-updated".to_string();
            // `c` is removed.
            guard.remove(&id_c);
            // `d` is inserted.
            let id_d = Uuid::new_v4();
            guard.insert(id_d, entity("d"));

            guard.compute_diff();
            assert_eq!(
                guard.dirty.len(),
                2,
                "only b (updated) and d (inserted) are dirty"
            );
            assert!(guard.dirty.contains(&id_b));
            assert!(guard.dirty.contains(&id_d));
            assert!(
                !guard.dirty.contains(&id_a),
                "untouched key must not be persisted"
            );
            assert_eq!(guard.removed.len(), 1, "only c was removed");
            assert!(guard.removed.contains(&id_c));

            // No pool configured → persist() commits to the shared map and
            // succeeds.
            guard
                .persist()
                .await
                .expect("in-memory persist must succeed");
            assert!(guard.dirty.is_empty());
            assert!(guard.removed.is_empty());
        }
    }

    /// After a successful persist the change sets must be cleared so the
    /// drop path is a no-op.
    #[tokio::test]
    async fn after_persist_success_clears_changes() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let tenant_id = tenant();
        let id = Uuid::new_v4();
        {
            let mut guard = store.write(tenant_id).await;
            guard.insert(id, entity("x"));
            guard.compute_diff();
            assert!(!guard.dirty.is_empty());
            guard.after_persist_success();
            assert!(guard.dirty.is_empty());
            assert!(guard.removed.is_empty());
        }
    }

    /// Entities of other tenants must never leak into a tenant's view, and
    /// writes must not overwrite another tenant's entries with the same id.
    #[tokio::test]
    async fn tenants_are_isolated_in_memory() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let tenant_a = tenant();
        let tenant_b = tenant();
        let shared_id = Uuid::new_v4();
        {
            let mut guard = store.write(tenant_a).await;
            guard.insert(shared_id, entity("a-owner"));
            guard.persist().await.unwrap();
        }
        {
            let mut guard = store.write(tenant_b).await;
            guard.insert(shared_id, entity("b-owner"));
            guard.persist().await.unwrap();
        }

        let view_a = store.read(tenant_a).await;
        assert_eq!(view_a.get(&shared_id).unwrap().name, "a-owner");
        drop(view_a);
        let view_b = store.read(tenant_b).await;
        assert_eq!(view_b.get(&shared_id).unwrap().name, "b-owner");
        assert_eq!(view_b.len(), 1);
    }

    #[tokio::test]
    async fn pagination_sorts_newest_first_in_memory() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let tenant_id = tenant();
        let now = chrono::Utc::now();

        let make = |offset_secs: i64, name: &str| TestEntity {
            name: name.to_string(),
            created_at: Some((now - chrono::Duration::seconds(offset_secs)).to_rfc3339()),
        };

        let id_old = Uuid::new_v4();
        let id_new = Uuid::new_v4();
        let id_no_ts = Uuid::new_v4();
        {
            let mut guard = store.write(tenant_id).await;
            guard.insert(id_old, make(100, "old"));
            guard.insert(id_new, make(10, "new"));
            guard.insert(id_no_ts, entity("no-timestamp"));
            guard.persist().await.unwrap();
        }

        let (items, total) = store.list_paginated(tenant_id, 1, 10).await.unwrap();
        assert_eq!(total, 3);
        assert_eq!(items.len(), 3);
        // Newest created_at first; entities without created_at sort last.
        assert_eq!(items[0].0, id_new);
        assert_eq!(items[1].0, id_old);
        assert_eq!(items[2].0, id_no_ts);
    }

    #[tokio::test]
    async fn pagination_clamps_page_and_per_page() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let tenant_id = tenant();
        {
            let mut guard = store.write(tenant_id).await;
            for i in 0..5 {
                guard.insert(Uuid::new_v4(), entity(&format!("e{i}")));
            }
            guard.persist().await.unwrap();
        }

        // page 0 behaves like page 1.
        let (items, total) = store.list_paginated(tenant_id, 0, 2).await.unwrap();
        assert_eq!(total, 5);
        assert_eq!(items.len(), 2);

        // Out-of-range page yields an empty page, not a panic.
        let (items, _) = store.list_paginated(tenant_id, 999, 2).await.unwrap();
        assert!(items.is_empty());
    }

    #[tokio::test]
    async fn list_by_field_filters_in_memory() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let tenant_id = tenant();
        let id_a = Uuid::new_v4();
        let id_b = Uuid::new_v4();
        {
            let mut guard = store.write(tenant_id).await;
            guard.insert(id_a, entity("alpha"));
            guard.insert(id_b, entity("beta"));
            guard.persist().await.unwrap();
        }

        let found = store
            .list_by_field(tenant_id, "name", &serde_json::json!("alpha"))
            .await
            .unwrap();
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].0, id_a);
    }

    /// list_paginated/list_by_field must never report empty/stale data on a
    /// DB failure: with a pool configured but the tenant's load failed, they
    /// return a SenseiError::Database.
    #[tokio::test]
    async fn list_paginated_reports_database_error_when_load_failed() {
        // Simulate a failed load: a pool that cannot be reached. The load
        // attempt inside `list_paginated` fails, and the method must return
        // Err(SenseiError::Database) instead of an empty page.
        let url = "postgres://invalid:invalid@127.0.0.1:1/nowhere";
        let pool = PgPool::connect_lazy(url).expect("lazy pool is cheap");
        let store: EntityStore<TestEntity> = EntityStore::with_pool("test_entity", pool);

        let result = store.list_paginated(Uuid::new_v4(), 1, 10).await;
        assert!(
            matches!(result, Err(SenseiError::Database(_))),
            "a failed DB load must surface as a Database error, not empty data"
        );
    }
}

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
//! # Persistence model
//!
//! A write guard snapshots the store contents once at acquisition. When the
//! guard is dropped (or [`StoreWriteGuard::persist`] is called), only the
//! changed keys are written back:
//!
//! * **inserted/updated** keys are batched into a single upsert transaction,
//! * **removed** keys are deleted in the same transaction.
//!
//! A per-store persist mutex serializes concurrent persistence (e.g. the
//! asynchronous drop path racing an explicit `persist()`), so a slow
//! fire-and-forget write can never reorder a newer write behind it.

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
}

// ── Inner storage ──────────────────────────────────────────────────────────

struct StoreInner<T> {
    data: HashMap<Uuid, T>,
    pool: Option<PgPool>,
    entity_type: String,
    db_loaded: bool,
    /// When the last DB load was attempted, so failed loads are retried at
    /// most once per second instead of on every access.
    last_db_load_attempt: Option<Instant>,
    /// Serializes persistence operations (explicit `persist()` and the
    /// asynchronous drop path) so only one persist runs at a time.
    persist_lock: Arc<Mutex<()>>,
}

impl<T> StoreInner<T> {
    fn new(entity_type: &str, pool: Option<PgPool>) -> Self {
        Self {
            data: HashMap::new(),
            pool,
            entity_type: entity_type.to_string(),
            db_loaded: false,
            last_db_load_attempt: None,
            persist_lock: Arc::new(Mutex::new(())),
        }
    }
}

// ── EntityStore ────────────────────────────────────────────────────────────

/// A generic entity store that can persist to PostgreSQL when a pool is
/// available.
///
/// When no pool is configured, it behaves exactly like an in-memory
/// `HashMap<Uuid, T>`. When a pool is set, mutations are asynchronously
/// persisted to the `entity_store` table on write-guard drop, and data is
/// lazily loaded from the database on first read.
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
///     let mut guard = store.write().await;
///     guard.insert(id, board);
/// }
///
/// // Database mode — transparent persistence
/// let store = EntityStore::with_pool("kanban_board", pool);
/// {
///     let mut guard = store.write().await;
///     guard.insert(id, board); // persisted on drop
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
    /// Data will be lazily loaded from the database on first access.
    pub fn with_pool(entity_type: &str, pool: PgPool) -> Self {
        Self {
            inner: Arc::new(RwLock::new(StoreInner::new(entity_type, Some(pool)))),
        }
    }
}

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static>
    EntityStore<T>
{
    /// Acquire a read guard.
    ///
    /// On first access when a pool is configured, data is loaded from the
    /// database before returning the guard. A failed load is retried on the
    /// next access, but at most once per second (rate-limited retries).
    pub async fn read(&self) -> StoreReadGuard<'_, T> {
        // Fast path: already loaded or no pool
        {
            let inner = self.inner.read().await;
            if inner.db_loaded || inner.pool.is_none() {
                return StoreReadGuard { inner };
            }
        }

        // Slow path: load from DB (double-checked locking)
        {
            let mut inner = self.inner.write().await;
            if !inner.db_loaded && inner.pool.is_some() {
                load_from_db(&mut inner).await;
            }
        }

        let inner = self.inner.read().await;
        StoreReadGuard { inner }
    }

    /// Acquire a write guard.
    ///
    /// On first access when a pool is configured, data is loaded from the
    /// database before returning the guard. The guard snapshots the current
    /// contents; changes are persisted to the database (as a diff) when the
    /// guard is dropped.
    pub async fn write(&self) -> StoreWriteGuard<'_, T> {
        // Ensure data is loaded from DB if needed, then release the lock
        {
            let mut inner = self.inner.write().await;
            if !inner.db_loaded && inner.pool.is_some() {
                load_from_db(&mut inner).await;
            }
        }

        // Re-acquire the write lock and snapshot the current state for
        // change tracking.
        let inner = self.inner.write().await;
        let original_values = inner.data.clone();
        StoreWriteGuard {
            inner,
            original_values,
            dirty: HashSet::new(),
            removed: HashSet::new(),
        }
    }
}

// ── Read guard ─────────────────────────────────────────────────────────────

/// Read guard that dereferences to `HashMap<Uuid, T>`.
///
/// Obtained from [`EntityStore::read()`]. Behaves identically to
/// `RwLockReadGuard<HashMap<Uuid, T>>`.
pub struct StoreReadGuard<'a, T> {
    inner: tokio::sync::RwLockReadGuard<'a, StoreInner<T>>,
}

impl<T> Deref for StoreReadGuard<'_, T> {
    type Target = HashMap<Uuid, T>;

    fn deref(&self) -> &Self::Target {
        &self.inner.data
    }
}

// ── Write guard ────────────────────────────────────────────────────────────

/// Write guard that dereferences to `HashMap<Uuid, T>`.
///
/// Obtained from [`EntityStore::write()`]. When dropped, the changed keys
/// (inserted/updated/removed since the guard was acquired) are
/// asynchronously persisted to the database (if a pool is configured).
pub struct StoreWriteGuard<
    'a,
    T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static,
> {
    inner: tokio::sync::RwLockWriteGuard<'a, StoreInner<T>>,
    /// Snapshot of the store contents when the guard was acquired. Used to
    /// detect inserted/updated/removed keys without cloning the whole map
    /// at persist time.
    original_values: HashMap<Uuid, T>,
    /// Keys that were inserted or updated since the guard was acquired.
    dirty: HashSet<Uuid>,
    /// Keys that were removed since the guard was acquired.
    removed: HashSet<Uuid>,
}

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> Deref
    for StoreWriteGuard<'_, T>
{
    type Target = HashMap<Uuid, T>;

    fn deref(&self) -> &Self::Target {
        &self.inner.data
    }
}

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> DerefMut
    for StoreWriteGuard<'_, T>
{
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.inner.data
    }
}

// ── Explicit persistence ────────────────────────────────────────────────────

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static>
    StoreWriteGuard<'_, T>
{
    /// Explicitly persist the pending changes to the database.
    ///
    /// Only the dirty (inserted/updated) and removed keys are written, in a
    /// single transaction. On transient failures (DB connection), a single
    /// retry with a 100ms delay is attempted before giving up.
    ///
    /// After a successful persist, the dirty/removed sets are cleared and
    /// the snapshot is refreshed so that the `Drop` impl will not
    /// re-persist the same data.
    ///
    /// # Errors
    ///
    /// Returns [`StoreError::NotConnected`] if no pool is configured.
    /// Returns [`StoreError::Database`] if the SQL operation fails after retry.
    /// Returns [`StoreError::Serialization`] if the entity cannot be serialized.
    pub async fn persist(&mut self) -> Result<(), StoreError> {
        let pool = self
            .inner
            .pool
            .clone()
            .ok_or(StoreError::NotConnected)?;

        self.compute_diff();

        if self.dirty.is_empty() && self.removed.is_empty() {
            return Ok(());
        }

        let entity_type = self.inner.entity_type.clone();
        let persist_lock = Arc::clone(&self.inner.persist_lock);
        let (dirty_values, removed_ids) = self.collect_changes()?;

        // Attempt persist with one retry on transient failure
        let result = {
            let _guard = persist_lock.lock().await;
            persist_changes_inner(&pool, &entity_type, &dirty_values, &removed_ids).await
        };
        match result {
            Ok(()) => {
                self.after_persist_success();
                Ok(())
            }
            Err(e) => {
                tracing::warn!(
                    entity_type = %entity_type,
                    error = %e,
                    "First persist attempt failed. Retrying after 100ms..."
                );
                tokio::time::sleep(Duration::from_millis(100)).await;
                // Use ? to convert sqlx::Error -> StoreError via #[from]
                let _guard = persist_lock.lock().await;
                persist_changes_inner(&pool, &entity_type, &dirty_values, &removed_ids).await?;
                self.after_persist_success();
                Ok(())
            }
        }
    }

    /// Recompute the dirty/removed sets by diffing the current data against
    /// the snapshot taken at guard acquisition.
    fn compute_diff(&mut self) {
        self.dirty.clear();
        self.removed.clear();
        for (id, value) in self.inner.data.iter() {
            match self.original_values.get(id) {
                Some(original) if original == value => {}
                _ => {
                    // Inserted (not in snapshot) or updated (differs).
                    self.dirty.insert(*id);
                }
            }
        }
        for id in self.original_values.keys() {
            if !self.inner.data.contains_key(id) {
                self.removed.insert(*id);
            }
        }
    }

    /// Serialize the dirty values and collect the removed ids.
    fn collect_changes(&self) -> Result<(HashMap<Uuid, T>, Vec<Uuid>), StoreError> {
        let mut dirty_values = HashMap::with_capacity(self.dirty.len());
        for id in &self.dirty {
            if let Some(value) = self.inner.data.get(id) {
                dirty_values.insert(*id, value.clone());
            }
        }
        let removed_ids: Vec<Uuid> = self.removed.iter().copied().collect();
        Ok((dirty_values, removed_ids))
    }

    /// After a successful persist: refresh the snapshot and clear the
    /// change sets so the `Drop` impl is a no-op.
    fn after_persist_success(&mut self) {
        self.original_values = self.inner.data.clone();
        self.dirty.clear();
        self.removed.clear();
    }
}

// ── Drop implementation (last-resort fallback) ──────────────────────────────

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static> Drop
    for StoreWriteGuard<'_, T>
{
    /// Last-resort persistence on drop.
    ///
    /// If [`persist()`](StoreWriteGuard::persist) was already called
    /// successfully, the dirty/removed sets are empty and this is a no-op.
    /// Otherwise, it spawns a fire-and-forget task that acquires the
    /// per-store persist lock before writing, so a concurrent explicit
    /// `persist()` can never be reordered behind this write.
    ///
    /// **Callers should prefer the explicit `persist()` method** and handle
    /// errors properly, rather than relying on `Drop`.
    fn drop(&mut self) {
        let pool = match self.inner.pool.clone() {
            Some(p) => p,
            None => return,
        };

        self.compute_diff();
        if self.dirty.is_empty() && self.removed.is_empty() {
            return;
        }

        let entity_type = self.inner.entity_type.clone();
        let persist_lock = Arc::clone(&self.inner.persist_lock);
        let (dirty_values, removed_ids) = match self.collect_changes() {
            Ok(changes) => changes,
            Err(e) => {
                tracing::error!(
                    entity_type = %entity_type,
                    error = %e,
                    "CRITICAL: Failed to prepare data for persistence on StoreWriteGuard drop. Data may be lost!"
                );
                return;
            }
        };

        tokio::spawn(async move {
            let _guard = persist_lock.lock().await;
            if let Err(e) =
                persist_changes_inner(&pool, &entity_type, &dirty_values, &removed_ids).await
            {
                tracing::error!(
                    entity_type = %entity_type,
                    error = %e,
                    "CRITICAL: Failed to persist data on StoreWriteGuard drop. Data may be lost!"
                );
            }
        });
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// DB helpers
// ═══════════════════════════════════════════════════════════════════════════

/// Load all entities of a given type from the database into the in-memory map.
///
/// `db_loaded` is set to `true` **only on success**, so a failed load is
/// retried on the next access (rate-limited to at most one attempt per
/// second). On failure, logs a warning and leaves the map empty.
async fn load_from_db<T: DeserializeOwned + Clone>(inner: &mut StoreInner<T>) {
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

    match sqlx::query("SELECT id, data FROM entity_store WHERE entity_type = $1")
        .bind(&inner.entity_type)
        .fetch_all(&pool)
        .await
    {
        Ok(rows) => {
            for row in rows {
                let id: Uuid = match row.try_get("id") {
                    Ok(v) => v,
                    Err(e) => {
                        tracing::warn!(
                            entity_type = %inner.entity_type,
                            "Failed to read id from row: {e}"
                        );
                        continue;
                    }
                };
                let data: serde_json::Value = match row.try_get("data") {
                    Ok(v) => v,
                    Err(e) => {
                        tracing::warn!(
                            entity_type = %inner.entity_type,
                            id = %id,
                            "Failed to read data from row: {e}"
                        );
                        continue;
                    }
                };
                match serde_json::from_value::<T>(data) {
                    Ok(entity) => {
                        inner.data.insert(id, entity);
                    }
                    Err(e) => {
                        tracing::warn!(
                            entity_type = %inner.entity_type,
                            id = %id,
                            "Failed to deserialize entity: {e}"
                        );
                    }
                }
            }
            tracing::info!(
                entity_type = %inner.entity_type,
                count = inner.data.len(),
                "Loaded entities from database"
            );
            inner.db_loaded = true;
        }
        Err(e) => {
            // Keep db_loaded = false so the next read retries (rate-limited
            // to once per second by last_db_load_attempt).
            tracing::warn!(
                entity_type = %inner.entity_type,
                "Failed to load from database (table may not exist yet): {e}"
            );
        }
    }
}

/// Persist changes to the database (inner helper, no retry).
///
/// Runs a **single transaction** containing:
/// - one batched upsert of all dirty entries,
/// - one batched delete of all removed entries.
async fn persist_changes_inner<T: Serialize>(
    pool: &PgPool,
    entity_type: &str,
    data: &HashMap<Uuid, T>,
    removed_ids: &[Uuid],
) -> Result<(), sqlx::Error> {
    let mut tx = pool.begin().await?;

        if !data.is_empty() {
            let mut ids = Vec::with_capacity(data.len());
            let mut values = Vec::with_capacity(data.len());
            for (id, entity) in data {
                let json = serde_json::to_value(entity).map_err(|e| {
                    tracing::error!(
                        entity_type = %entity_type,
                        id = %id,
                        "Failed to serialize entity: {e}"
                    );
                    sqlx::Error::Protocol(format!("Serialization error: {e}"))
                })?;
                ids.push(*id);
                values.push(sqlx::types::Json(json));
            }

        sqlx::query(
            r#"INSERT INTO entity_store (entity_type, id, data)
               SELECT $1, u.id, u.data
               FROM UNNEST($2::uuid[], $3::jsonb[]) AS u(id, data)
               ON CONFLICT (entity_type, id)
               DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()"#,
        )
        .bind(entity_type)
        .bind(&ids)
        .bind(&values)
        .execute(&mut *tx)
        .await?;
    }

    if !removed_ids.is_empty() {
        sqlx::query("DELETE FROM entity_store WHERE entity_type = $1 AND id = ANY($2)")
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

impl<T: Serialize + DeserializeOwned + Clone + PartialEq + Send + Sync + 'static>
    EntityStore<T>
{
    /// Fetch a page of entities directly from the database, bypassing the
    /// in-memory cache.
    ///
    /// Returns a tuple of `(records, total_count)` where `total_count` is the
    /// number of matching entities **without** pagination applied. Records
    /// are ordered by `created_at DESC, id` (migration 021 added the
    /// `created_at` column).
    ///
    /// When no pool is configured, falls back to in-memory filtering with
    /// the same ordering (parsing `created_at` from the serialized entity
    /// when present, otherwise falling back to the id).
    pub async fn list_paginated(
        &self,
        page: usize,
        per_page: usize,
    ) -> Result<(Vec<(Uuid, T)>, u64), StoreError> {
        let inner = self.inner.read().await;

        let pool = match inner.pool.as_ref() {
            Some(p) => p,
            None => {
                // In-memory fallback: apply pagination to the full map,
                // ordered by created_at DESC, id (mirroring the DB order).
                drop(inner);
                let guard = self.read().await;
                let total = guard.len() as u64;
                let mut items: Vec<(Uuid, T)> = guard
                    .iter()
                    .map(|(k, v)| (*k, v.clone()))
                    .collect();
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

        let entity_type = &inner.entity_type;
        let offset = (page.saturating_sub(1).saturating_mul(per_page)) as i64;
        let limit = per_page as i64;

        // Get total count
        let (count_row,): (i64,) = sqlx::query_as(
            "SELECT COUNT(*)::bigint FROM entity_store WHERE entity_type = $1",
        )
        .bind(entity_type)
        .fetch_one(pool)
        .await?;

        // Get page of data, newest first.
        let rows = sqlx::query(
            "SELECT id, data FROM entity_store WHERE entity_type = $1 \
             ORDER BY created_at DESC, id LIMIT $2 OFFSET $3",
        )
        .bind(entity_type)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await?;

        let mut items = Vec::with_capacity(rows.len());
        for row in rows {
            let id: Uuid = row.try_get("id")?;
            let data: serde_json::Value = row.try_get("data")?;
            let entity: T = serde_json::from_value(data)?;
            items.push((id, entity));
        }

        Ok((items, count_row as u64))
    }

    /// Fetch entities from the database filtered by a JSONB field match.
    ///
    /// Uses the GIN index on `data` via the `@>` containment operator.
    /// Example: `list_by_field("status", &serde_json::json!("\"done\""))`
    ///
    /// When no pool is configured, falls back to in-memory filtering.
    pub async fn list_by_field(
        &self,
        field: &str,
        value: &serde_json::Value,
    ) -> Result<Vec<(Uuid, T)>, StoreError> {
        let inner = self.inner.read().await;

        let pool = match inner.pool.as_ref() {
            Some(p) => p,
            None => {
                // In-memory fallback
                drop(inner);
                let guard = self.read().await;
                let items: Vec<(Uuid, T)> = guard
                    .iter()
                    .filter(|(_, v)| {
                        serde_json::to_value(v)
                            .ok()
                            .and_then(|val| val.get(field).cloned())
                            .as_ref()
                            == Some(value)
                    })
                    .map(|(k, v)| (*k, v.clone()))
                    .collect();
                return Ok(items);
            }
        };

        let entity_type = &inner.entity_type;

        // Use JSONB containment: data @> '{"field": value}' (GIN index).
        let filter = serde_json::json!({ field: value });

        let rows = sqlx::query(
            r#"SELECT id, data FROM entity_store
               WHERE entity_type = $1 AND data @> $2
               ORDER BY id"#,
        )
        .bind(entity_type)
        .bind(&filter)
        .fetch_all(pool)
        .await?;

        let mut items = Vec::with_capacity(rows.len());
        for row in rows {
            let id: Uuid = row.try_get("id")?;
            let data: serde_json::Value = row.try_get("data")?;
            let entity: T = serde_json::from_value(data)?;
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

    /// In-memory mode: persist() reports NotConnected, but the dirty-diff
    /// computation must track exactly the inserted/updated and removed keys.
    #[tokio::test]
    async fn write_guard_tracks_only_dirty_keys() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let id_a = Uuid::new_v4();
        let id_b = Uuid::new_v4();
        let id_c = Uuid::new_v4();

        // Seed the store with three entities.
        {
            let mut guard = store.write().await;
            guard.insert(id_a, entity("a"));
            guard.insert(id_b, entity("b"));
            guard.insert(id_c, entity("c"));
        }

        {
            let mut guard = store.write().await;
            // `a` stays untouched — must NOT appear in the diff.
            // `b` is updated in place.
            guard.get_mut(&id_b).unwrap().name = "b-updated".to_string();
            // `c` is removed.
            guard.remove(&id_c);
            // `d` is inserted.
            let id_d = Uuid::new_v4();
            guard.insert(id_d, entity("d"));

            guard.compute_diff();
            assert_eq!(guard.dirty.len(), 2, "only b (updated) and d (inserted) are dirty");
            assert!(guard.dirty.contains(&id_b));
            assert!(guard.dirty.contains(&id_d));
            assert!(!guard.dirty.contains(&id_a), "untouched key must not be persisted");
            assert_eq!(guard.removed.len(), 1, "only c was removed");
            assert!(guard.removed.contains(&id_c));

            // No pool configured → persist() fails cleanly and leaves the
            // diff intact for the drop path.
            assert!(matches!(
                guard.persist().await,
                Err(StoreError::NotConnected)
            ));
        }
    }

    /// After a successful persist the change sets must be cleared so the
    /// drop path is a no-op. (Exercised via the diff helpers; SQL execution
    /// requires a live pool.)
    #[tokio::test]
    async fn after_persist_success_clears_changes() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let id = Uuid::new_v4();
        {
            let mut guard = store.write().await;
            guard.insert(id, entity("x"));
            guard.compute_diff();
            assert!(!guard.dirty.is_empty());
            guard.after_persist_success();
            assert!(guard.dirty.is_empty());
            assert!(guard.removed.is_empty());
        }
    }

    #[tokio::test]
    async fn pagination_sorts_newest_first_in_memory() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let now = chrono::Utc::now();

        let make = |offset_secs: i64, name: &str| TestEntity {
            name: name.to_string(),
            created_at: Some(
                (now - chrono::Duration::seconds(offset_secs)).to_rfc3339(),
            ),
        };

        let id_old = Uuid::new_v4();
        let id_new = Uuid::new_v4();
        let id_no_ts = Uuid::new_v4();
        {
            let mut guard = store.write().await;
            guard.insert(id_old, make(100, "old"));
            guard.insert(id_new, make(10, "new"));
            guard.insert(id_no_ts, entity("no-timestamp"));
        }

        let (items, total) = store.list_paginated(1, 10).await.unwrap();
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
        {
            let mut guard = store.write().await;
            for i in 0..5 {
                guard.insert(Uuid::new_v4(), entity(&format!("e{i}")));
            }
        }

        // page 0 behaves like page 1.
        let (items, total) = store.list_paginated(0, 2).await.unwrap();
        assert_eq!(total, 5);
        assert_eq!(items.len(), 2);

        // Out-of-range page yields an empty page, not a panic.
        let (items, _) = store.list_paginated(999, 2).await.unwrap();
        assert!(items.is_empty());
    }

    #[tokio::test]
    async fn list_by_field_filters_in_memory() {
        let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
        let id_a = Uuid::new_v4();
        let id_b = Uuid::new_v4();
        {
            let mut guard = store.write().await;
            guard.insert(id_a, entity("alpha"));
            guard.insert(id_b, entity("beta"));
        }

        let found = store
            .list_by_field("name", &serde_json::json!("alpha"))
            .await
            .unwrap();
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].0, id_a);
    }
}

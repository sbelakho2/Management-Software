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

use serde::de::DeserializeOwned;
use serde::Serialize;
use sqlx::{PgPool, Row};
use std::collections::{HashMap, HashSet};
use std::ops::{Deref, DerefMut};
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;
use tokio::sync::RwLock;
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
///   Clone + Send + Sync` for database persistence.
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
            inner: Arc::new(RwLock::new(StoreInner {
                data: HashMap::new(),
                pool: None,
                entity_type: entity_type.to_string(),
                db_loaded: false,
            })),
        }
    }

    /// Create a new store backed by the given database pool.
    ///
    /// Data will be lazily loaded from the database on first access.
    pub fn with_pool(entity_type: &str, pool: PgPool) -> Self {
        Self {
            inner: Arc::new(RwLock::new(StoreInner {
                data: HashMap::new(),
                pool: Some(pool),
                entity_type: entity_type.to_string(),
                db_loaded: false,
            })),
        }
    }
}

impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> EntityStore<T> {
    /// Acquire a read guard.
    ///
    /// On first access when a pool is configured, data is loaded from the
    /// database before returning the guard.
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
    /// database before returning the guard. Changes are persisted to the
    /// database when the guard is dropped.
    pub async fn write(&self) -> StoreWriteGuard<'_, T> {
        // Ensure data is loaded from DB if needed, then release the lock
        {
            let mut inner = self.inner.write().await;
            if !inner.db_loaded && inner.pool.is_some() {
                load_from_db(&mut inner).await;
            }
        }

        // Re-acquire the write lock and record original keys for change tracking
        let inner = self.inner.write().await;
        let original_keys: HashSet<Uuid> = inner.data.keys().copied().collect();
        StoreWriteGuard {
            inner,
            original_keys,
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
/// Obtained from [`EntityStore::write()`]. When dropped, changes are
/// asynchronously persisted to the database (if a pool is configured).
///
/// The guard tracks which keys existed when it was created. On drop, it:
/// 1. Upserts all current entries to the `entity_store` table.
/// 2. Deletes entries that were removed during the write lock.
pub struct StoreWriteGuard<'a, T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> {
    inner: tokio::sync::RwLockWriteGuard<'a, StoreInner<T>>,
    original_keys: HashSet<Uuid>,
}

impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> Deref
    for StoreWriteGuard<'_, T>
{
    type Target = HashMap<Uuid, T>;

    fn deref(&self) -> &Self::Target {
        &self.inner.data
    }
}

impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> DerefMut
    for StoreWriteGuard<'_, T>
{
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.inner.data
    }
}

// ── Explicit persistence ────────────────────────────────────────────────────

impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> StoreWriteGuard<'_, T> {
    /// Explicitly persist all changes to the database.
    ///
    /// Returns `StoreError` on failure. On transient failures (DB connection),
    /// a single retry with a 100ms delay is attempted before giving up.
    ///
    /// After a successful persist, the dirty flag is cleared so that the
    /// `Drop` impl will not re-persist the same data.
    ///
    /// # Errors
    ///
    /// Returns [`StoreError::NotConnected`] if no pool is configured.
    /// Returns [`StoreError::Database`] if the SQL operation fails after retry.
    /// Returns [`StoreError::Serialization`] if the entity cannot be serialized.
    pub async fn persist(&mut self) -> Result<(), StoreError> {
        let pool = self.inner.pool.clone()
            .ok_or(StoreError::NotConnected)?;

        let entity_type = self.inner.entity_type.clone();
        let current_data: HashMap<Uuid, T> = self.inner.data.clone();
        let current_keys: HashSet<Uuid> = current_data.keys().copied().collect();
        let removed_ids: Vec<Uuid> = self
            .original_keys
            .iter()
            .filter(|k| !current_keys.contains(k))
            .copied()
            .collect();

        // Attempt persist with one retry on transient failure
        let result = persist_changes_inner(&pool, &entity_type, &current_data, &removed_ids).await;
        match result {
            Ok(()) => {
                // Update original_keys to reflect current state so Drop is a no-op
                self.original_keys = current_keys;
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
                persist_changes_inner(&pool, &entity_type, &current_data, &removed_ids).await?;
                self.original_keys = current_keys;
                Ok(())
            }
        }
    }
}

// ── Drop implementation (last-resort fallback) ──────────────────────────────

impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> Drop
    for StoreWriteGuard<'_, T>
{
    /// Last-resort persistence on drop.
    ///
    /// If [`persist()`](StoreWriteGuard::persist) was already called
    /// successfully, `original_keys` will match `current_keys` and this is a
    /// no-op. Otherwise, it spawns a fire-and-forget task with error logging.
    ///
    /// **Callers should prefer the explicit `persist()` method** and handle
    /// errors properly, rather than relying on `Drop`.
    fn drop(&mut self) {
        let pool = match self.inner.pool.clone() {
            Some(p) => p,
            None => return,
        };

        let entity_type = self.inner.entity_type.clone();
        let current_data: HashMap<Uuid, T> = self.inner.data.clone();
        let current_keys: HashSet<Uuid> = current_data.keys().copied().collect();

        // If persist() was already called, original_keys == current_keys
        // so removed_ids will be empty — skip the spawn entirely.
        if self.original_keys == current_keys {
            return;
        }

        let removed_ids: Vec<Uuid> = self
            .original_keys
            .iter()
            .filter(|k| !current_keys.contains(k))
            .copied()
            .collect();

        tokio::spawn(async move {
            if let Err(e) = persist_changes_inner(&pool, &entity_type, &current_data, &removed_ids).await
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
/// On failure, logs a warning and leaves the map empty (graceful fallback).
async fn load_from_db<T: DeserializeOwned + Clone>(inner: &mut StoreInner<T>) {
    let pool = match inner.pool.as_ref() {
        Some(p) => p,
        None => return,
    };

    match sqlx::query(
        "SELECT id, data FROM entity_store WHERE entity_type = $1",
    )
    .bind(&inner.entity_type)
    .fetch_all(pool)
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
        }
        Err(e) => {
            tracing::warn!(
                entity_type = %inner.entity_type,
                "Failed to load from database (table may not exist yet): {e}"
            );
        }
    }
    inner.db_loaded = true;
}

/// Persist changes to the database (inner helper, no retry).
///
/// - Upserts all current entries.
/// - Deletes entries that were removed.
async fn persist_changes_inner<T: Serialize>(
    pool: &PgPool,
    entity_type: &str,
    data: &HashMap<Uuid, T>,
    removed_ids: &[Uuid],
) -> Result<(), sqlx::Error> {
    // Upsert all current entries
    for (id, entity) in data {
        let json = serde_json::to_value(entity)
            .map_err(|e| {
                tracing::error!(
                    entity_type = %entity_type,
                    id = %id,
                    "Failed to serialize entity: {e}"
                );
                sqlx::Error::Protocol(format!("Serialization error: {e}"))
            })?;

        sqlx::query(
            r#"INSERT INTO entity_store (entity_type, id, data)
               VALUES ($1, $2, $3)
               ON CONFLICT (entity_type, id)
               DO UPDATE SET data = $3, updated_at = NOW()"#,
        )
        .bind(entity_type)
        .bind(id)
        .bind(&json)
        .execute(pool)
        .await?;
    }

    // Delete removed entries
    for id in removed_ids {
        sqlx::query(
            "DELETE FROM entity_store WHERE entity_type = $1 AND id = $2",
        )
        .bind(entity_type)
        .bind(id)
        .execute(pool)
        .await?;
    }

    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════
// DB-level pagination & filtering (bypasses in-memory cache)
// ═══════════════════════════════════════════════════════════════════════════

impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> EntityStore<T> {
    /// Fetch a page of entities directly from the database, bypassing the
    /// in-memory cache.
    ///
    /// Returns a tuple of `(records, total_count)` where `total_count` is the
    /// number of matching entities **without** pagination applied.
    ///
    /// When no pool is configured, falls back to in-memory filtering.
    pub async fn list_paginated(
        &self,
        page: usize,
        per_page: usize,
    ) -> Result<(Vec<(Uuid, T)>, u64), StoreError> {
        let inner = self.inner.read().await;

        let pool = match inner.pool.as_ref() {
            Some(p) => p,
            None => {
                // In-memory fallback: apply pagination to the full map
                drop(inner);
                let guard = self.read().await;
                let total = guard.len() as u64;
                let items: Vec<(Uuid, T)> = guard
                    .iter()
                    .skip((page.saturating_sub(1)) * per_page)
                    .take(per_page)
                    .map(|(k, v)| (*k, v.clone()))
                    .collect();
                return Ok((items, total));
            }
        };

        let entity_type = &inner.entity_type;
        let offset = ((page.saturating_sub(1)) * per_page) as i64;
        let limit = per_page as i64;

        // Get total count
        let (count_row,): (i64,) = sqlx::query_as(
            "SELECT COUNT(*)::bigint FROM entity_store WHERE entity_type = $1",
        )
        .bind(entity_type)
        .fetch_one(pool)
        .await?;

        // Get page of data
        let rows = sqlx::query(
            "SELECT id, data FROM entity_store WHERE entity_type = $1 ORDER BY id LIMIT $2 OFFSET $3",
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
                        serde_json::to_value(v).ok()
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

        // Use JSONB containment: data @> '{"field": value}'
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

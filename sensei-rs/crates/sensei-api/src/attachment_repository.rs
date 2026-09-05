//! Typed attachment repository — the attachment metadata no longer lives in
//! the generic EntityStore (which caches full tenant snapshots per process).
//!
//! PostgreSQL is the source of truth; the in-memory map is the dev/test
//! fallback only.
//!
//! # Deletion lifecycle (thirtieth-audit item 14)
//!
//! Deletion is two-phase so a transient failure can never leave active
//! metadata pointing at a missing object:
//!
//! ```text
//! active → deleting (tombstone) → object delete → metadata remove
//! ```
//!
//! The `attachments` table carries no status column, so the repository
//! tracks the `deleting` phase in a process-local tombstone overlay
//! ([`Self::deleting`]) keyed by attachment id. The underlying row (memory
//! map / PostgreSQL row) is left untouched until the final metadata
//! removal, which keeps `storage_path` and the parent coordinates available
//! for an idempotent retry. While a record is tombstoned:
//!
//! * [`Self::get`] / [`Self::list`] hide it (downloads and listings of a
//!   tombstoned attachment are impossible);
//! * [`Self::get_deleting`] exposes it to the deletion-completion path so a
//!   later delete attempt can resume the interrupted object removal.
//!
//! The overlay is process-local (no schema change): across a process crash
//! an interrupted deletion reverts to `active`, which is the safe default —
//! the blob and the row are both still present in every phase before the
//! final row removal. A durable cross-restart tombstone would require a
//! lifecycle column (migration) plus a scheduled worker, which is out of
//! scope for the audit item; the transient-failure case it targets (a
//! storage/DB error mid-delete, retried in-process) is fully covered.

use crate::state::AppState;
use crate::stores::Attachment;

/// SQL row for the `attachments` table (see migration 062).
type AttachmentRow = (
    Uuid,
    Uuid,
    String,
    Uuid,
    String,
    String,
    i64,
    String,
    Option<Uuid>,
    chrono::DateTime<chrono::Utc>,
);
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

/// Shared attachment repository (DB-backed with dev fallback).
#[derive(Clone)]
pub struct AttachmentRepository {
    pool: Option<sqlx::PgPool>,
    memory: Arc<RwLock<HashMap<Uuid, Attachment>>>,
    /// Tombstone overlay: records whose deletion started but has not
    /// completed (`active → deleting`). Hidden from [`Self::get`] /
    /// [`Self::list`]; reachable only through [`Self::get_deleting`] so the
    /// deletion-completion path can resume idempotently. See the module
    /// docs for the lifecycle rationale.
    deleting: Arc<RwLock<HashMap<Uuid, Attachment>>>,
}

impl AttachmentRepository {
    pub fn new(pool: Option<sqlx::PgPool>) -> Self {
        Self {
            pool,
            memory: Arc::new(RwLock::new(HashMap::new())),
            deleting: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn attach_pool(mut self, pool: sqlx::PgPool) -> Self {
        self.pool = Some(pool);
        self
    }

    /// Insert (or update) an attachment record.
    pub async fn put(&self, attachment: &Attachment) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO attachments (id, tenant_id, entity_type, entity_id, file_name,  content_type, file_size, storage_path, uploaded_by, created_at)  VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)  ON CONFLICT (id) DO UPDATE SET file_name = $5, content_type = $6, file_size = $7",
            )
            .bind(attachment.id)
            .bind(attachment.tenant_id)
            .bind(&attachment.entity_type)
            .bind(attachment.entity_id)
            .bind(&attachment.file_name)
            .bind(&attachment.content_type)
            .bind(attachment.file_size)
            .bind(&attachment.storage_path)
            .bind(attachment.uploaded_by)
            .bind(attachment.created_at)
            .execute(pool)
            .await
            .map_err(|e| format!("Attachment insert failed: {e}"))?;
            return Ok(());
        }
        self.memory
            .write()
            .await
            .insert(attachment.id, attachment.clone());
        Ok(())
    }

    /// Fetch one attachment scoped to the tenant. A database failure is a
    /// REAL error — it must never masquerade as "attachment not found".
    ///
    /// Tombstoned (deleting) records are hidden: the caller sees `None`
    /// exactly as if the record did not exist, so downloads of an
    /// in-progress deletion are impossible.
    pub async fn get(&self, tenant_id: Uuid, id: Uuid) -> Result<Option<Attachment>, String> {
        let resolved = if let Some(pool) = &self.pool {
            let row: Option<AttachmentRow> = sqlx::query_as(
                "SELECT id, tenant_id, entity_type, entity_id, file_name, content_type, \
                        file_size, storage_path, uploaded_by, created_at \
                 FROM attachments WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| format!("Attachment read failed: {e}"))?;
            row.map(|r| Attachment {
                id: r.0,
                tenant_id: r.1,
                entity_type: r.2,
                entity_id: r.3,
                file_name: r.4,
                content_type: r.5,
                file_size: r.6,
                storage_path: r.7,
                uploaded_by: r.8.unwrap_or_default(),
                created_at: r.9,
            })
        } else {
            self.memory
                .read()
                .await
                .get(&id)
                .filter(|a| a.tenant_id == tenant_id)
                .cloned()
        };
        if resolved.is_some() && self.is_deleting(id).await {
            return Ok(None);
        }
        Ok(resolved)
    }

    /// List attachments for an entity, newest first. A database failure is
    /// a REAL error — it must never masquerade as an empty list.
    ///
    /// Tombstoned (deleting) records are excluded, so listings never expose
    /// an attachment whose deletion is in progress.
    pub async fn list(
        &self,
        tenant_id: Uuid,
        entity_type: &str,
        entity_id: Uuid,
    ) -> Result<Vec<Attachment>, String> {
        if let Some(pool) = &self.pool {
            let rows: Vec<AttachmentRow> = sqlx::query_as(
                "SELECT id, tenant_id, entity_type, entity_id, file_name, content_type, \
                        file_size, storage_path, uploaded_by, created_at \
                 FROM attachments WHERE tenant_id = $1 AND entity_type = $2 AND entity_id = $3 \
                 ORDER BY created_at DESC",
            )
            .bind(tenant_id)
            .bind(entity_type)
            .bind(entity_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Attachment list failed: {e}"))?;
            let mut out: Vec<Attachment> = rows
                .into_iter()
                .map(|r| Attachment {
                    id: r.0,
                    tenant_id: r.1,
                    entity_type: r.2,
                    entity_id: r.3,
                    file_name: r.4,
                    content_type: r.5,
                    file_size: r.6,
                    storage_path: r.7,
                    uploaded_by: r.8.unwrap_or_default(),
                    created_at: r.9,
                })
                .collect();
            self.filter_deleting(&mut out).await;
            return Ok(out);
        }
        let mut out: Vec<Attachment> = self
            .memory
            .read()
            .await
            .values()
            .filter(|a| {
                a.tenant_id == tenant_id && a.entity_type == entity_type && a.entity_id == entity_id
            })
            .cloned()
            .collect();
        self.filter_deleting(&mut out).await;
        out.sort_by_key(|a| std::cmp::Reverse(a.created_at));
        Ok(out)
    }

    /// Transition `attachment` from `active` to `deleting` (tombstone).
    ///
    /// The underlying row is kept — `storage_path` and the parent
    /// coordinates must survive for the idempotent completion — but the
    /// record becomes invisible to [`Self::get`] / [`Self::list`] until
    /// [`Self::delete`] finalizes the removal. Safe to call again (the
    /// tombstone is idempotent).
    pub async fn tombstone(&self, attachment: &Attachment) -> Result<(), String> {
        // Consistent lock order (memory → deleting) across every path, then
        // drop any active-memory copy so the read path (memory mode) and
        // the shadow copy (DB mode) agree with the overlay.
        self.memory.write().await.remove(&attachment.id);
        self.deleting
            .write()
            .await
            .insert(attachment.id, attachment.clone());
        Ok(())
    }

    /// Fetch a tombstoned (deleting) attachment scoped to the tenant.
    ///
    /// This is the retry surface for an interrupted deletion: it returns
    /// the record (including `storage_path` and the parent coordinates)
    /// that the deletion-completion path needs, while ordinary reads keep
    /// treating the record as absent.
    pub async fn get_deleting(&self, tenant_id: Uuid, id: Uuid) -> Option<Attachment> {
        self.deleting
            .read()
            .await
            .get(&id)
            .filter(|a| a.tenant_id == tenant_id)
            .cloned()
    }

    /// Number of tombstoned (deleting) records for the tenant.
    ///
    /// Exposed for observability/tests; the audit's retry surface is
    /// [`Self::get_deleting`] driven by the next delete attempt.
    pub async fn deleting_count(&self, tenant_id: Uuid) -> usize {
        self.deleting
            .read()
            .await
            .values()
            .filter(|a| a.tenant_id == tenant_id)
            .count()
    }

    /// Whether `id` is currently tombstoned (deleting).
    async fn is_deleting(&self, id: Uuid) -> bool {
        self.deleting.read().await.contains_key(&id)
    }

    /// Drop every record in `out` that is tombstoned (deleting).
    async fn filter_deleting(&self, out: &mut Vec<Attachment>) {
        let deleting = self.deleting.read().await;
        out.retain(|a| !deleting.contains_key(&a.id));
    }

    /// Finalize deletion of an attachment record (scoped to the tenant).
    ///
    /// Completes the lifecycle started by [`Self::tombstone`]: removes the
    /// underlying row (memory map / PostgreSQL) and clears the tombstone.
    /// Idempotent — returns `Ok(false)` when no active record existed.
    pub async fn delete(&self, tenant_id: Uuid, id: Uuid) -> Result<bool, String> {
        if let Some(pool) = &self.pool {
            let res = sqlx::query("DELETE FROM attachments WHERE id = $1 AND tenant_id = $2")
                .bind(id)
                .bind(tenant_id)
                .execute(pool)
                .await
                .map_err(|e| format!("Attachment delete failed: {e}"))?;
            self.deleting.write().await.remove(&id);
            self.memory.write().await.remove(&id);
            return Ok(res.rows_affected() == 1);
        }
        let mut mem = self.memory.write().await;
        let exists = mem.get(&id).is_some_and(|a| a.tenant_id == tenant_id);
        if exists {
            mem.remove(&id);
        }
        self.deleting.write().await.remove(&id);
        Ok(exists)
    }
}

/// Convenience accessor.
impl AppState {
    pub fn attachments(&self) -> AttachmentRepository {
        self.attachment_repo.clone()
    }
}

//! Typed attachment repository — the attachment metadata no longer lives in
//! the generic EntityStore (which caches full tenant snapshots per process).
//!
//! PostgreSQL is the source of truth; the in-memory map is the dev/test
//! fallback only.

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
}

impl AttachmentRepository {
    pub fn new(pool: Option<sqlx::PgPool>) -> Self {
        Self {
            pool,
            memory: Arc::new(RwLock::new(HashMap::new())),
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
                "INSERT INTO attachments (id, tenant_id, entity_type, entity_id, file_name, \\
                                          content_type, file_size, storage_path, uploaded_by, created_at) \\
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) \\
                 ON CONFLICT (id) DO UPDATE SET file_name = $5, content_type = $6, file_size = $7",
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
    pub async fn get(&self, tenant_id: Uuid, id: Uuid) -> Result<Option<Attachment>, String> {
        if let Some(pool) = &self.pool {
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
            return Ok(row.map(|r| Attachment {
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
            }));
        }
        Ok(self
            .memory
            .read()
            .await
            .get(&id)
            .filter(|a| a.tenant_id == tenant_id)
            .cloned())
    }

    /// List attachments for an entity, newest first. A database failure is
    /// a REAL error — it must never masquerade as an empty list.
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
            return Ok(rows
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
                .collect());
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
        out.sort_by_key(|a| std::cmp::Reverse(a.created_at));
        Ok(out)
    }

    /// Delete an attachment record (scoped to the tenant).
    pub async fn delete(&self, tenant_id: Uuid, id: Uuid) -> Result<bool, String> {
        if let Some(pool) = &self.pool {
            let res = sqlx::query("DELETE FROM attachments WHERE id = $1 AND tenant_id = $2")
                .bind(id)
                .bind(tenant_id)
                .execute(pool)
                .await
                .map_err(|e| format!("Attachment delete failed: {e}"))?;
            return Ok(res.rows_affected() == 1);
        }
        let mut mem = self.memory.write().await;
        let exists = mem.get(&id).is_some_and(|a| a.tenant_id == tenant_id);
        if exists {
            mem.remove(&id);
        }
        Ok(exists)
    }
}

/// Convenience accessor.
impl AppState {
    pub fn attachments(&self) -> AttachmentRepository {
        self.attachment_repo.clone()
    }
}

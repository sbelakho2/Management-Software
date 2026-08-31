//! Site-edge replication (fifteenth audit 29/A15): the durable queue
//! between site-local execution and corporate federation. Enqueue is
//! site-local; pull is the corporate projection.

use sensei_core::error::{Result, SenseiError};
use serde::Serialize;
use uuid::Uuid;

/// One durable replication entry — the AUTHORIZED state projection a
/// site enqueued for corporate federation. `pulled_at` is not exposed:
/// once corporate pulls an entry it is claimed atomically and never
/// surfaces again (durable once, no double projection).
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct ReplicationEntry {
    pub id: Uuid,
    pub site_id: Option<Uuid>,
    pub entity_type: String,
    pub entity_id: Option<Uuid>,
    pub projection: serde_json::Value,
    pub source_event_id: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Transaction-scoped tenant context for the RLS policy (FAIL-CLOSED:
/// missing context = no rows), same convention as
/// `crates/sensei-services/src/tps/lessons.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Run `f` inside a transaction with the RLS tenant context set.
async fn with_tenant_tx<T, F>(pool: &sqlx::PgPool, tenant_id: Uuid, f: F) -> Result<T>
where
    F: for<'t> FnOnce(
        &'t mut sqlx::Transaction<'_, sqlx::Postgres>,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = std::result::Result<T, SenseiError>> + Send + 't>,
    >,
{
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin tenant tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit tenant tx: {e}")))?;
    Ok(result)
}

/// Enqueue an AUTHORIZED state projection — SITE-LOCAL, never dependent
/// on the corporate link. The site's operations keep running while the
/// queue is durable in its own tenant-scoped transaction.
pub async fn enqueue_projection(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    entity_type: &str,
    entity_id: Uuid,
    projection: serde_json::Value,
    source_event_id: Option<&str>,
) -> Result<()> {
    let entity_type = entity_type.to_string();
    let source_event_id = source_event_id.map(String::from);
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO site_replication_log \
                     (tenant_id, site_id, entity_type, entity_id, projection, source_event_id) \
                 VALUES ($1, $2, $3, $4, $5, $6)",
            )
            .bind(tenant_id)
            .bind(site_id)
            .bind(&entity_type)
            .bind(entity_id)
            .bind(projection)
            .bind(source_event_id.as_deref())
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: enqueue failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Corporate pull: return the pending entries (`pulled_at IS NULL` in
/// `created_at` order, bounded by `limit`) and mark them `pulled_at =
/// NOW()` in the SAME transaction. The claim is atomic — a crash before
/// processing still leaves the projection durably queued for the next
/// pull, so corporate never loses nor double-receives a projection.
pub async fn pull_pending(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    limit: i64,
) -> Result<Vec<ReplicationEntry>> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let rows: Vec<ReplicationEntry> = sqlx::query_as(
                "SELECT id, site_id, entity_type, entity_id, projection, source_event_id, \
                        created_at \
                 FROM site_replication_log \
                 WHERE pulled_at IS NULL \
                 ORDER BY created_at ASC, id ASC \
                 LIMIT $1",
            )
            .bind(limit)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: pull failed: {e}")))?;

            if !rows.is_empty() {
                let ids: Vec<Uuid> = rows.iter().map(|r| r.id).collect();
                sqlx::query(
                    "UPDATE site_replication_log SET pulled_at = NOW() \
                     WHERE id = ANY($1) AND pulled_at IS NULL",
                )
                .bind(&ids)
                .execute(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("replication: claim failed: {e}")))?;
            }
            Ok(rows)
        })
    })
    .await
}

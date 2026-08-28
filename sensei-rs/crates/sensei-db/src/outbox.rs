//! Transactional outbox helpers (item 28): correctness-relevant domain
//! events are written in the SAME transaction as the state mutation they
//! describe — a committed state transition can never lose its event to a
//! post-commit publish failure. The relay publishes outbox rows.

use sensei_core::error::SenseiError;
use sqlx::PgPool;
use uuid::Uuid;

/// Write one outbox row inside an existing transaction.
pub async fn enqueue_outbox(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    aggregate_type: &str,
    aggregate_id: Uuid,
    event_type: &str,
    payload: serde_json::Value,
) -> std::result::Result<(), SenseiError> {
    sqlx::query(
        "INSERT INTO outbox_events \
                (event_id, tenant_id, aggregate_type, aggregate_id, event_type, payload) \
         VALUES ($1, $2, $3, $4, $5, $6)",
    )
    .bind(Uuid::new_v4())
    .bind(tenant_id)
    .bind(aggregate_type)
    .bind(aggregate_id)
    .bind(event_type)
    .bind(payload)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to write outbox event: {e}")))?;
    Ok(())
}

/// Convenience for flows that run outside an explicit transaction: begin
/// one, run the closure, and commit — the closure may write outbox rows
/// through [`enqueue_outbox`].
pub async fn with_tx<T>(
    pool: &PgPool,
    _tenant_id: Uuid,
    f: impl FnOnce(&mut sqlx::Transaction<'_, sqlx::Postgres>) -> std::result::Result<T, SenseiError>,
) -> std::result::Result<T, SenseiError> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin tx: {e}")))?;
    let result = f(&mut tx)?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit tx: {e}")))?;
    Ok(result)
}

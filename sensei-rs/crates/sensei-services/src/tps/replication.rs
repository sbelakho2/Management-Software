//! Site-edge replication (fifteenth audit 29/A15 + sixteenth audit
//! items 15-17): the durable queue between site-local execution and
//! corporate federation. Enqueue is site-local; the corporate side
//! CLAIMS rows (lease), applies the projection, then ACKs. Delivery is
//! at-least-once — a crash after claim loses only the lease, never the
//! projection — and application is idempotent via the
//! (tenant_id, source_event_id, projection_type) key.

use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// The projection envelope — the versioned contract between the site and
/// corporate. `schema_version` guards future envelope evolution;
/// `projection_type` + `projection_revision` + `source_event_id` form the
/// idempotency key; `data_policy` drives the deterministic residency gate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplicationEnvelope {
    pub schema_version: u32,
    pub source_event_id: Option<String>,
    pub source_site: Option<Uuid>,
    pub projection_type: String,
    pub projection_revision: u64,
    pub data_policy: String,
    pub payload: serde_json::Value,
}

/// One durable replication entry — the AUTHORIZED state projection a
/// site enqueued for corporate federation. `claim_token` is the lease:
/// only the worker holding it may ack/fail the row, so a stale worker's
/// ACK is rejected by ownership check.
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct ReplicationEntry {
    pub id: Uuid,
    pub site_id: Option<Uuid>,
    pub entity_type: String,
    pub entity_id: Option<Uuid>,
    pub projection: serde_json::Value,
    pub source_event_id: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub claim_token: Option<Uuid>,
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

/// DETERMINISTIC residency gate (sixteenth audit item 17): a projection
/// whose `data_policy` is `restricted` or `personal` may never cross a
/// country border — it is blocked when the destination country is set and
/// differs from the source country (or the source is unknown). All other
/// policies replicate freely. Pure function: the route calls it BEFORE
/// enqueue (422), and `enqueue_projection` enforces it again as a second
/// line of defense.
pub fn may_replicate(
    data_policy: &str,
    source_country: Option<&str>,
    destination_country: Option<&str>,
) -> bool {
    let destination_set_and_different = match (source_country, destination_country) {
        (Some(src), Some(dst)) => src != dst,
        (None, Some(_)) => true,
        _ => false,
    };
    !(destination_set_and_different && matches!(data_policy, "restricted" | "personal"))
}

/// DERIVE the replication data policy SERVER-SIDE (sixteenth audit item
/// 29): from the source site's country manifest (site_manifests.country)
/// and the tenant's country policy bundle (country_policies.data_residency).
/// FAIL-CLOSED: an unknown country or a missing policy bundle is a
/// Validation error, never a silent downgrade to a weaker label.
pub async fn derive_data_policy(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
) -> Result<String> {
    let Some(site_id) = site_id else {
        // Tenant-level envelope (no site): the default classification is
        // "internal" — the least permissive label that still replicates.
        return Ok("internal".to_string());
    };
    let country: Option<String> = sqlx::query_scalar(
        "SELECT sm.country FROM site_manifests sm          WHERE sm.tenant_id = $1 AND sm.site_id = $2",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("replication: manifest lookup: {e}")))?;
    let Some(country) = country else {
        return Err(SenseiError::Validation(
            "replication: site has no manifest — cannot derive data policy".to_string(),
        ));
    };
    let residency: Option<String> = sqlx::query_scalar(
        "SELECT cp.data_residency FROM country_policies cp          WHERE cp.tenant_id = $1 AND cp.country = $2",
    )
    .bind(tenant_id)
    .bind(&country)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("replication: policy lookup: {e}")))?;
    residency.ok_or_else(|| {
        SenseiError::Validation(format!(
            "replication: no country policy for {country} — a country is a policy RECORD,              not a code fork"
        ))
    })
}

/// Enqueue an AUTHORIZED state projection — SITE-LOCAL, never dependent
/// on the corporate link. The site's operations keep running while the
/// queue is durable in its own tenant-scoped transaction. The envelope's
/// `data_policy` is checked against the residency gate first; the
/// `source_event_id` + `projection_type` idempotency key makes duplicate
/// enqueues a hard UNIQUE rejection.
#[allow(clippy::too_many_arguments)]
pub async fn enqueue_projection(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    entity_type: &str,
    entity_id: Uuid,
    projection: serde_json::Value,
    source_event_id: Option<&str>,
    envelope: &ReplicationEnvelope,
    source_country: Option<&str>,
    destination_country: Option<&str>,
) -> Result<()> {
    if !may_replicate(&envelope.data_policy, source_country, destination_country) {
        return Err(SenseiError::Validation(
            "data residency policy blocks this projection".to_string(),
        ));
    }
    let entity_type = entity_type.to_string();
    let source_event_id = source_event_id.map(String::from);
    let projection_type = if envelope.projection_type.is_empty() {
        entity_type.clone()
    } else {
        envelope.projection_type.clone()
    };
    let data_policy = envelope.data_policy.clone();
    let schema_version = envelope.schema_version as i32;
    let projection_revision = envelope.projection_revision as i64;
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO site_replication_log \
                     (tenant_id, site_id, entity_type, entity_id, projection, source_event_id, \
                      schema_version, projection_type, projection_revision, data_policy, status) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending')",
            )
            .bind(tenant_id)
            .bind(site_id)
            .bind(&entity_type)
            .bind(entity_id)
            .bind(projection)
            .bind(source_event_id.as_deref())
            .bind(schema_version)
            .bind(&projection_type)
            .bind(projection_revision)
            .bind(&data_policy)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: enqueue failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Corporate claim: select the claimable rows (pending, or failed past
/// their retry window) with `FOR UPDATE SKIP LOCKED` and lease them in the
/// SAME transaction — `status='claimed'`, a fresh `claim_token`,
/// `lease_expires_at = NOW() + 5 minutes`, `attempt_count+1`. A concurrent
/// worker's claim skips the locked rows, so a projection is claimed by
/// exactly one worker; a corporate crash after claim loses only the lease
/// (`release_expired` puts the row back to pending), never the projection.
pub async fn claim_batch(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    limit: i64,
) -> Result<Vec<ReplicationEntry>> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // AUTO-RECLAIM (sixteenth audit item 29): a worker that
            // disappeared mid-apply leaves an expired lease behind; the
            // claim pass recycles those rows instead of waiting for a
            // separate sweep.
            sqlx::query(
                "UPDATE site_replication_log \
                 SET status = 'pending', claim_token = NULL \
                 WHERE status = 'claimed' AND lease_expires_at < NOW()",
            )
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: auto-reclaim: {e}")))?;

            let mut rows: Vec<ReplicationEntry> = sqlx::query_as(
                "SELECT id, site_id, entity_type, entity_id, projection, source_event_id, \
                        created_at, NULL::uuid AS claim_token \
                 FROM site_replication_log \
                 WHERE (status = 'pending' OR (status = 'failed' AND next_attempt_at <= NOW())) \
                 ORDER BY created_at ASC, id ASC \
                 LIMIT $1 \
                 FOR UPDATE SKIP LOCKED",
            )
            .bind(limit)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: claim failed: {e}")))?;

            if !rows.is_empty() {
                let ids: Vec<Uuid> = rows.iter().map(|r| r.id).collect();
                let claimed: Vec<(Uuid, Uuid)> = sqlx::query_as(
                    "UPDATE site_replication_log \
                     SET status = 'claimed', claim_token = gen_random_uuid(), \
                         claimed_at = NOW(), \
                         lease_expires_at = NOW() + INTERVAL '5 minutes', \
                         attempt_count = attempt_count + 1 \
                     WHERE id = ANY($1) \
                     RETURNING id, claim_token",
                )
                .bind(&ids)
                .fetch_all(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("replication: lease failed: {e}")))?;

                for (id, token) in claimed {
                    if let Some(row) = rows.iter_mut().find(|r| r.id == id) {
                        row.claim_token = Some(token);
                    }
                }
            }
            Ok(rows)
        })
    })
    .await
}

/// Corporate ACK after applying the projection: marks the row `acked`.
/// The `claim_token` is the ownership check — a stale worker (or one that
/// never held the lease) is rejected, and the row stays claimed for the
/// real worker.
pub async fn ack(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid, claim_token: Uuid) -> Result<()> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let res = sqlx::query(
                "UPDATE site_replication_log SET status = 'acked', acked_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 AND claim_token = $3",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(claim_token)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: ack failed: {e}")))?;
            if res.rows_affected() == 0 {
                return Err(SenseiError::NotFound(
                    "replication: ack rejected — no row with this id and claim token".to_string(),
                ));
            }
            Ok(())
        })
    })
    .await
}

/// Corporate fail after an apply error: marks the row `failed` and
/// schedules the retry — it becomes claimable again once
/// `next_attempt_at` passes. Same token ownership check as `ack`.
pub async fn fail(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
    claim_token: Uuid,
    error: &str,
    retry_in_seconds: i64,
) -> Result<()> {
    let error = error.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let interval = format!("{retry_in_seconds} seconds");
            let res = sqlx::query(
                "UPDATE site_replication_log \
                 SET status = 'failed', last_error = $4, \
                     next_attempt_at = NOW() + $5::interval \
                 WHERE id = $1 AND tenant_id = $2 AND claim_token = $3",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(claim_token)
            .bind(&error)
            .bind(&interval)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: fail failed: {e}")))?;
            if res.rows_affected() == 0 {
                return Err(SenseiError::NotFound(
                    "replication: fail rejected — no row with this id and claim token".to_string(),
                ));
            }
            Ok(())
        })
    })
    .await
}

/// A worker that disappeared mid-apply (lease expired) — the row goes
/// back to `pending` with the token cleared, so the next claim can pick
/// it up. Returns the number of leases released.
pub async fn release_expired(pool: &sqlx::PgPool, tenant_id: Uuid) -> Result<u64> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let res = sqlx::query(
                "UPDATE site_replication_log \
                 SET status = 'pending', claim_token = NULL \
                 WHERE status = 'claimed' AND lease_expires_at < NOW()",
            )
            .execute(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("replication: release expired failed: {e}"))
            })?;
            Ok(res.rows_affected())
        })
    })
    .await
}

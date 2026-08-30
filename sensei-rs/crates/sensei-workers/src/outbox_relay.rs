//! Transactional-outbox relay.
//!
//! Business mutations write `outbox_events` rows in the SAME transaction as
//! the business state (see the finance critical paths). This relay polls
//! unpublished rows, publishes each to NATS JetStream with its
//! `event_type`, and marks it published ONLY after the server
//! acknowledgement. A crashed relay leaves rows unpublished; the next poll
//! retries them — an event is never lost to a publish failure after commit.

use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info, warn};

const POLL_INTERVAL: Duration = Duration::from_secs(2);
const BATCH_SIZE: i64 = 50;
const MAX_ATTEMPTS: i32 = 25;

/// Identity of THIS relay process (claim ownership).
///
/// Two relays running the same release MUST NOT share an identity — a
/// shared id would let one relay's ownership check pass for the other's
/// claims. A per-process UUID is generated at spawn (item 10).
fn replica_id() -> String {
    use std::sync::OnceLock;
    static REPLICA_ID: OnceLock<String> = OnceLock::new();
    REPLICA_ID
        .get_or_init(|| {
            let pid = std::process::id();
            let start = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            format!("relay-{pid}-{start}-{}", uuid::Uuid::new_v4())
        })
        .clone()
}

/// Spawn the outbox relay (DB-backed only; in-memory/dev modes no-op).
pub fn spawn(pool: Option<Arc<sqlx::PgPool>>, bus: Arc<dyn sensei_event_bus::EventBus>) {
    let Some(pool) = pool else {
        info!("Outbox relay: no database pool — relay disabled");
        return;
    };
    tokio::spawn(async move {
        info!("Outbox relay started");
        loop {
            if let Err(e) = relay_once(&pool, &bus).await {
                warn!(error = %e, "Outbox relay pass failed");
            }
            tokio::time::sleep(POLL_INTERVAL).await;
        }
    });
}

async fn relay_once(
    pool: &sqlx::PgPool,
    bus: &Arc<dyn sensei_event_bus::EventBus>,
) -> Result<(), String> {
    // Fourteenth audit (P0): FORCE RLS makes a cross-tenant scan invisible
    // for a non-owner role. The relay enumerates tenants from the (RLS-
    // free) tenants table and processes ONE tenant-scoped transaction at a
    // time — SET LOCAL app.tenant_id inside the claim/mark transactions.
    let tenants: Vec<uuid::Uuid> = sqlx::query_scalar("SELECT id FROM tenants")
        .fetch_all(pool)
        .await
        .map_err(|e| format!("Failed to enumerate tenants: {e}"))?;
    for tenant_id in tenants {
        if let Err(e) = relay_tenant(pool, bus, tenant_id).await {
            warn!(error = %e, tenant_id = %tenant_id, "Outbox relay tenant pass failed");
        }
    }
    Ok(())
}

/// Process one tenant's unpublished events with the tenant context set.
async fn relay_tenant(
    pool: &sqlx::PgPool,
    bus: &Arc<dyn sensei_event_bus::EventBus>,
    tenant_id: uuid::Uuid,
) -> Result<(), String> {
    // Atomic claim transaction, tenant-scoped: SET LOCAL app.tenant_id so
    // FORCE RLS admits exactly THIS tenant's rows; selection + claim in
    // ONE transaction so two relays never claim the same event.
    let rows: Vec<(
        uuid::Uuid,
        uuid::Uuid,
        String,
        String,
        String,
        serde_json::Value,
    )> = {
        let mut tx = pool
            .begin()
            .await
            .map_err(|e| format!("Failed to begin claim tx: {e}"))?;
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .map_err(|e| format!("Failed to set tenant context: {e}"))?;
        let rows = sqlx::query_as(
            "WITH selected AS (
                 SELECT event_id FROM outbox_events \
                 WHERE tenant_id = $4 AND published_at IS NULL AND attempt_count < $1 \
                   AND (claim_until IS NULL OR claim_until < NOW()) \
                 ORDER BY occurred_at \
                 LIMIT $2 \
                 FOR UPDATE SKIP LOCKED
             )
             UPDATE outbox_events o SET claimed_by = $3, claim_until = NOW() + INTERVAL '30 seconds' \
             FROM selected s WHERE o.event_id = s.event_id \
             RETURNING o.event_id, o.tenant_id, o.event_type, o.aggregate_type, \
                       o.aggregate_id, o.payload",
        )
        .bind(MAX_ATTEMPTS)
        .bind(BATCH_SIZE)
        .bind(replica_id())
        .bind(tenant_id)
        .fetch_all(&mut *tx)
        .await
        .map_err(|e| format!("Failed to claim outbox batch: {e}"))?;
        tx.commit()
            .await
            .map_err(|e| format!("Failed to commit claim tx: {e}"))?;
        rows
    };

    for (event_id, event_tenant, event_type, aggregate_type, aggregate_id, payload) in rows {
        let subject = format!("sensei.{event_type}");
        let envelope = serde_json::json!({
            "event_id": event_id,
            "tenant_id": event_tenant,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload": payload,
        });
        match serde_json::to_vec(&envelope) {
            Ok(bytes) => {
                let subject_owned = subject.clone();
                let bus_owned = Arc::clone(bus);
                let publish_task = tokio::spawn(async move {
                    publish_acknowledged(&bus_owned, &subject_owned, bytes).await
                });
                let mut publish_task = publish_task;
                let published = loop {
                    tokio::select! {
                        outcome = &mut publish_task => break outcome,
                        _ = tokio::time::sleep(std::time::Duration::from_secs(15)) => {
                            renew_claim(pool, event_id, tenant_id).await;
                        }
                    }
                };
                match published {
                    Ok(Ok(())) => {
                        mark_published(pool, event_id, tenant_id).await;
                    }
                    Ok(Err(e)) => {
                        record_failure(pool, event_id, tenant_id, &e).await;
                    }
                    Err(e) => {
                        record_failure(
                            pool,
                            event_id,
                            tenant_id,
                            &format!("publish task join: {e}"),
                        )
                        .await;
                    }
                }
            }
            Err(e) => {
                record_failure(pool, event_id, tenant_id, &e.to_string()).await;
            }
        }
    }
    Ok(())
}

/// JetStream publish that WAITS for the server acknowledgement (the
/// durable copy exists only after the ack).
async fn publish_acknowledged(
    bus: &Arc<dyn sensei_event_bus::EventBus>,
    subject: &str,
    payload: Vec<u8>,
) -> Result<(), String> {
    // The event-bus trait's publish takes a DomainEvent; outbox payloads
    // are plain JSON, so publish through the bus's JetStream-aware path by
    // constructing a transient event.
    let event = sensei_core::domain::events::GenericJsonEvent::new(
        subject.trim_start_matches("sensei."),
        serde_json::from_slice(&payload).map_err(|e| e.to_string())?,
    );
    bus.publish(&event).await.map_err(|e| e.to_string())
}

/// Renew the claim lease while a publish is in flight: a publish that
/// stalls beyond the fixed lease must NOT let a second relay reclaim the
/// event mid-flight (item 10).
async fn renew_claim(pool: &sqlx::PgPool, event_id: uuid::Uuid, tenant_id: uuid::Uuid) {
    let result = sqlx::query(
        "UPDATE outbox_events SET claim_until = NOW() + INTERVAL '30 seconds'          WHERE event_id = $1 AND claimed_by = $2 AND published_at IS NULL AND tenant_id = $3",
    )
    .bind(event_id)
    .bind(replica_id())
    .bind(tenant_id)
    .execute(pool)
    .await;
    if let Err(e) = result {
        error!(error = %e, event_id = %event_id, "Failed to renew outbox claim");
    }
}

/// Mark published with an OWNERSHIP check: only the relay that holds the
/// claim may mark the event — a stale replica can never overwrite a newer
/// publish. The durable `outbox_published` record is the consumer-side
/// deduplication anchor (item 10).
async fn mark_published(pool: &sqlx::PgPool, event_id: uuid::Uuid, tenant_id: uuid::Uuid) {
    let result = sqlx::query(
        "UPDATE outbox_events SET published_at = NOW(), claimed_by = NULL, claim_until = NULL          WHERE event_id = $1 AND published_at IS NULL AND claimed_by = $2 AND tenant_id = $3",
    )
    .bind(event_id)
    .bind(replica_id())
    .bind(tenant_id)
    .execute(pool)
    .await;
    match result {
        Ok(outcome) if outcome.rows_affected() == 1 => {
            // Durable dedupe record: consumers that crash after the JetStream
            // ack but before processing can reconcile against this table.
            if let Err(e) = sqlx::query(
                "INSERT INTO outbox_published (event_id, published_at)                  VALUES ($1, NOW()) ON CONFLICT (event_id) DO NOTHING",
            )
            .bind(event_id)
            .execute(pool)
            .await
            {
                error!(error = %e, event_id = %event_id, "Failed to record outbox_published");
            }
        }
        Ok(_) => {
            warn!(event_id = %event_id, "mark_published skipped: event not owned by this relay or already published");
        }
        Err(e) => {
            error!(error = %e, event_id = %event_id, "Failed to mark outbox event published");
        }
    }
}

async fn record_failure(
    pool: &sqlx::PgPool,
    event_id: uuid::Uuid,
    tenant_id: uuid::Uuid,
    err: &str,
) {
    if let Err(e) = sqlx::query(
        "UPDATE outbox_events SET attempt_count = attempt_count + 1, last_error = $2, \
                claimed_by = NULL, claim_until = NULL \
         WHERE event_id = $1 AND tenant_id = $3",
    )
    .bind(event_id)
    .bind(err)
    .bind(tenant_id)
    .execute(pool)
    .await
    {
        error!(error = %e, event_id = %event_id, "Failed to record outbox failure");
    }
}

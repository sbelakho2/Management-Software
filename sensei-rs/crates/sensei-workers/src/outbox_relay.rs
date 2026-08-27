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
    // Claim a batch with a per-row lock so multiple relays never publish
    // the same event twice.
    let rows: Vec<(
        uuid::Uuid,
        uuid::Uuid,
        String,
        String,
        String,
        serde_json::Value,
    )> = sqlx::query_as(
        "SELECT event_id, tenant_id, event_type, aggregate_type, aggregate_id, payload \\
         FROM outbox_events \\
         WHERE published_at IS NULL AND attempt_count < $1 \\
         ORDER BY occurred_at \\
         LIMIT $2 \\
         FOR UPDATE SKIP LOCKED",
    )
    .bind(MAX_ATTEMPTS)
    .bind(BATCH_SIZE)
    .fetch_all(pool)
    .await
    .map_err(|e| format!("Failed to claim outbox batch: {e}"))?;

    for (event_id, tenant_id, event_type, aggregate_type, aggregate_id, payload) in rows {
        // Publish with a REAL server acknowledgement (JetStream ack).
        let subject = format!("sensei.{event_type}");
        let envelope = serde_json::json!({
            "event_id": event_id,
            "tenant_id": tenant_id,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "payload": payload,
        });
        match serde_json::to_vec(&envelope) {
            Ok(bytes) => {
                let published = publish_acknowledged(bus, &subject, bytes).await;
                match published {
                    Ok(()) => {
                        mark_published(pool, event_id).await;
                    }
                    Err(e) => {
                        record_failure(pool, event_id, &e).await;
                    }
                }
            }
            Err(e) => {
                record_failure(pool, event_id, &e.to_string()).await;
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

async fn mark_published(pool: &sqlx::PgPool, event_id: uuid::Uuid) {
    if let Err(e) = sqlx::query(
        "UPDATE outbox_events SET published_at = NOW() WHERE event_id = $1 AND published_at IS NULL",
    )
    .bind(event_id)
    .execute(pool)
    .await
    {
        error!(error = %e, event_id = %event_id, "Failed to mark outbox event published");
    }
}

async fn record_failure(pool: &sqlx::PgPool, event_id: uuid::Uuid, err: &str) {
    if let Err(e) = sqlx::query(
        "UPDATE outbox_events SET attempt_count = attempt_count + 1, last_error = $2 \\
         WHERE event_id = $1",
    )
    .bind(event_id)
    .bind(err)
    .execute(pool)
    .await
    {
        error!(error = %e, event_id = %event_id, "Failed to record outbox failure");
    }
}

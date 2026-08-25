//! Supervised JetStream subscription lifecycle.
//!
//! A pull consumer's message stream can terminate for many reasons: the
//! consumer was deleted, the stream was recreated, the connection dropped,
//! or the server restarted. The naive loop in older versions of this crate
//! stopped forever when the stream ended.
//!
//! This module provides [`run_supervised`]: a loop that (re)creates the
//! consumer, drains messages through a caller-supplied handler, and when the
//! stream ends or errors, re-subscribes with exponential backoff
//! (1s → 2s → … → capped at 60s). It also exposes [`Readiness`] — an
//! `AtomicBool` plus a `tokio::sync::watch` channel — that the binary can
//! surface in its health endpoint, and a [`worker_status`] heartbeat helper
//! backed by migration 055.

use async_nats::jetstream::consumer::pull;
use async_nats::jetstream::Context;
use futures::StreamExt;
use std::future::Future;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::watch;
use tracing::{error, info, warn};

/// Initial reconnect backoff after a subscription failure.
pub const SUBSCRIBE_BACKOFF_INITIAL: Duration = Duration::from_secs(1);
/// Cap for the reconnect backoff (exponential: 1s, 2s, 4s, … 60s).
pub const SUBSCRIBE_BACKOFF_MAX: Duration = Duration::from_secs(60);

/// Everything needed to (re)create one JetStream pull consumer.
#[derive(Debug, Clone)]
pub struct SubscriptionSpec {
    /// Name of the stream the consumer belongs to.
    pub stream_name: String,
    /// Subject the consumer filters on (e.g. `"sensei.tasks.email.send"`).
    pub subject: String,
    /// Durable consumer name (shared across replicas for competing consumers).
    pub consumer_name: String,
    /// Pull-consumer configuration (max_deliver/backoff/ack_wait are set by
    /// the caller; this module owns the reconnect lifecycle, not the policy).
    pub config: pull::Config,
}

/// Readiness signal for one supervised subscription.
///
/// `subscribed` flips to `true` as soon as the consumer exists and its
/// message stream is being polled, and back to `false` when the stream ends
/// or the consumer fails. The `watch::Receiver` returned by
/// [`Readiness::new`] lets the binary await the transition (e.g. gate
/// readiness probes on "all consumers subscribed").
#[derive(Clone, Debug)]
pub struct Readiness {
    subscribed: Arc<AtomicBool>,
    watcher: watch::Sender<bool>,
}

impl Readiness {
    /// Create a fresh readiness signal (initially `false`) plus its receiver.
    pub fn new() -> (Self, watch::Receiver<bool>) {
        let (tx, rx) = watch::channel(false);
        (
            Self {
                subscribed: Arc::new(AtomicBool::new(false)),
                watcher: tx,
            },
            rx,
        )
    }

    /// Current subscribed state.
    pub fn is_subscribed(&self) -> bool {
        self.subscribed.load(Ordering::SeqCst)
    }

    /// Update the subscribed state and notify watchers on transitions.
    pub fn set_subscribed(&self, subscribed: bool) {
        let prev = self.subscribed.swap(subscribed, Ordering::SeqCst);
        if prev != subscribed {
            let _ = self.watcher.send(subscribed);
        }
    }
}

/// Exponential backoff for re-subscribe attempts: `current * 2`, capped at
/// [`SUBSCRIBE_BACKOFF_MAX`].
pub fn next_backoff(current: Duration) -> Duration {
    current
        .saturating_mul(2)
        .min(SUBSCRIBE_BACKOFF_MAX)
        .max(Duration::from_millis(100))
}

/// Get or create the stream, then get or create the pull consumer and open
/// its message stream.
///
/// `get_or_create` re-creates a deleted consumer on the next iteration, so
/// this doubles as the "recreate the consumer on re-subscribe" step.
async fn ensure_consumer(js: &Context, spec: &SubscriptionSpec) -> Result<pull::Stream, String> {
    let stream = js
        .get_or_create_stream(async_nats::jetstream::stream::Config {
            name: spec.stream_name.clone(),
            subjects: vec![spec.subject.clone()],
            ..Default::default()
        })
        .await
        .map_err(|e| format!("failed to ensure stream '{}': {e}", spec.stream_name))?;

    let consumer = stream
        .get_or_create_consumer(&spec.consumer_name, spec.config.clone())
        .await
        .map_err(|e| {
            format!(
                "failed to get or create consumer '{}': {e}",
                spec.consumer_name
            )
        })?;

    consumer.messages().await.map_err(|e| {
        format!(
            "failed to open message stream for consumer '{}': {e}",
            spec.consumer_name
        )
    })
}

/// Run a supervised pull-consumer loop for one subscription.
///
/// The loop:
///
/// 1. Ensures the stream and consumer exist (recreating a deleted consumer).
/// 2. Marks [`Readiness`] subscribed and drains messages through `handler`.
/// 3. When the stream ends or errors, marks not-subscribed, sleeps with
///    exponential backoff (1s → … → 60s cap), and retries from step 1.
///
/// The loop only returns on `Ctrl-C` (graceful shutdown). Each message is
/// handled sequentially; the handler owns the ack/NAK/DLQ decision.
///
/// # Panics
///
/// None; all failures are logged and retried.
pub async fn run_supervised<H, F>(
    js: Context,
    spec: SubscriptionSpec,
    readiness: Readiness,
    mut handler: H,
) where
    H: FnMut(async_nats::jetstream::Message) -> F + Send,
    F: Future<Output = ()> + Send,
{
    let label = format!("{}/{}", spec.consumer_name, spec.subject);
    let mut backoff = SUBSCRIBE_BACKOFF_INITIAL;

    loop {
        let consumer = match ensure_consumer(&js, &spec).await {
            Ok(consumer) => consumer,
            Err(e) => {
                error!(consumer = %label, error = %e, retry_in_ms = backoff.as_millis(),
                    "Consumer setup failed — retrying with backoff");
                readiness.set_subscribed(false);
                tokio::time::sleep(backoff).await;
                backoff = next_backoff(backoff);
                continue;
            }
        };

        let mut messages = consumer;

        readiness.set_subscribed(true);
        info!(consumer = %label, "Supervised consumer subscribed");
        backoff = SUBSCRIBE_BACKOFF_INITIAL;

        let mut stream_active = true;
        while stream_active {
            tokio::select! {
                msg = messages.next() => match msg {
                    Some(Ok(msg)) => handler(msg).await,
                    Some(Err(e)) => {
                        warn!(consumer = %label, error = %e,
                            "Message stream error — resubscribing");
                        stream_active = false;
                    }
                    None => {
                        info!(consumer = %label, "Message stream ended — resubscribing");
                        stream_active = false;
                    }
                },
                _ = tokio::signal::ctrl_c() => {
                    info!(consumer = %label, "Shutdown signal received — stopping");
                    readiness.set_subscribed(false);
                    return;
                }
            }
        }

        readiness.set_subscribed(false);
        info!(consumer = %label, retry_in_ms = backoff.as_millis(),
            "Consumer disconnected — resubscribing after backoff");
        tokio::time::sleep(backoff).await;
        backoff = next_backoff(backoff);
    }
}

// ── Worker status heartbeat (migration 055) ─────────────────────────────────

/// Upsert this worker's status row so health dashboards can see
/// subscription and leadership state per instance.
///
/// `worker_name` is the worker type (e.g. `"email"`, `"scheduler"`),
/// `instance_id` distinguishes replicas. Pass `None` for the pool in
/// single-process dev mode to skip the write (no-op).
pub async fn report_worker_status(
    pool: Option<&sqlx::PgPool>,
    worker_name: &str,
    instance_id: &str,
    subscribed: bool,
    is_leader: bool,
) {
    let Some(pool) = pool else { return };
    let result = sqlx::query(
        "INSERT INTO worker_status (worker_name, instance_id, subscribed, is_leader, last_heartbeat, updated_at) \
         VALUES ($1, $2, $3, $4, NOW(), NOW()) \
         ON CONFLICT (worker_name) DO UPDATE SET \
           instance_id = EXCLUDED.instance_id, \
           subscribed = EXCLUDED.subscribed, \
           is_leader = EXCLUDED.is_leader, \
           last_heartbeat = NOW(), updated_at = NOW()",
    )
    .bind(worker_name)
    .bind(instance_id)
    .bind(subscribed)
    .bind(is_leader)
    .execute(pool)
    .await;

    if let Err(e) = result {
        warn!(worker = %worker_name, error = %e, "Failed to report worker status");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backoff_doubles_and_caps() {
        // 1s -> 2s -> 4s -> 8s -> 16s -> 32s -> capped at 60s (6 doublings).
        let mut d = SUBSCRIBE_BACKOFF_INITIAL;
        for _ in 0..6 {
            d = next_backoff(d);
        }
        assert_eq!(d, SUBSCRIBE_BACKOFF_MAX);
    }

    #[tokio::test]
    async fn readiness_transitions_are_observed() {
        let (readiness, rx) = Readiness::new();
        assert!(!readiness.is_subscribed());
        readiness.set_subscribed(true);
        assert!(readiness.is_subscribed());
        // No transition (already true) — receiver must stay at the last value.
        readiness.set_subscribed(true);
        readiness.set_subscribed(false);
        assert!(!*rx.borrow());
        assert!(!readiness.is_subscribed());
    }
}

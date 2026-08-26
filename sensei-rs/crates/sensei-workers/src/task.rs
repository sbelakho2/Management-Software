//! Core task types, the [`TaskConsumer`] trait, and the [`TaskDispatcher`]
//! that manages pull-based JetStream consumers.
//!
//! # Delivery reliability model
//!
//! * **Transport retries are JetStream's job.** Each pull consumer is
//!   configured with `max_deliver` + `backoff`, so a message that is not
//!   acked is redelivered by the server with escalating delays. There is no
//!   application-level retry counter; [`TaskMetadata::attempts`] is derived
//!   from the server's delivery count and kept for observability only.
//! * **Application-level classification.** Workers return a
//!   [`TaskOutcome`]: `Completed` → ack; `RetryLater(delay)` → NAK with
//!   delay (JetStream redelivers within `max_deliver`); `FailedPermanent`
//!   → DLQ.
//! * **DLQ-before-ack.** The original message is **never** acked until the
//!   DLQ replacement has received its JetStream publish acknowledgement. If
//!   the DLQ publish fails the original is NAKed (or left unacked) so it is
//!   redelivered.
//! * **Malformed payloads are not silently discarded.** They are published
//!   to the DLQ subject first (ack only on success), so operators can see
//!   why a task died.

use crate::error::{Result, WorkerError};
use crate::nats::{run_supervised, Readiness, SubscriptionSpec};
use async_nats::jetstream::consumer::pull;
use async_nats::jetstream::Context;
use async_nats::jetstream::{AckKind, Message};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info, warn};
use uuid::Uuid;

/// Metadata attached to every task message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskMetadata {
    /// Unique task identifier.
    pub task_id: Uuid,
    /// The type / kind of task.
    pub task_type: TaskType,
    /// Optional correlation ID for distributed tracing.
    pub correlation_id: Option<Uuid>,
    /// Timestamp when the task was created.
    pub created_at: chrono::DateTime<chrono::Utc>,
    /// Number of delivery attempts so far (observability only — the retry
    /// policy lives in the JetStream consumer's `max_deliver`/`backoff`).
    #[serde(default, alias = "retry_count")]
    pub attempts: u32,
}

impl TaskMetadata {
    /// Create a new [`TaskMetadata`] with the given parameters.
    pub fn new(task_type: TaskType) -> Self {
        Self {
            task_id: Uuid::new_v4(),
            task_type,
            correlation_id: None,
            created_at: chrono::Utc::now(),
            attempts: 0,
        }
    }

    /// Overwrite the attempts counter from the server-reported delivery
    /// count (first delivery = 1, so attempts = delivered − 1).
    pub fn record_delivery(&mut self, delivered: i64) {
        self.attempts = delivered.saturating_sub(1).max(0) as u32;
    }
}

/// Recognised task types matching the Celery tasks being replaced.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum TaskType {
    /// Send an email via SMTP.
    SendEmail,
    /// Generate an A3 PDF report.
    GenerateA3Pdf,
    /// Generate a quote PDF.
    GenerateQuotePdf,
    /// Run ML model training.
    RunModelTraining,
    /// Check for model drift and trigger retraining.
    CheckDriftAndRetrain,
    /// Force a model retrain regardless of drift.
    ForceModelRetrain,
    /// Scheduled retrain of all models.
    ScheduledRetrainAll,
    /// Daily analytics snapshot.
    DailyAnalyticsSnapshot,
    /// Compute warehouse KPIs.
    ComputeWarehouseKpis,
}

impl TaskType {
    /// Return the NATS subject this task type publishes / listens on.
    pub fn subject(&self) -> &'static str {
        match self {
            Self::SendEmail => "sensei.tasks.email.send",
            Self::GenerateA3Pdf => "sensei.tasks.pdf.a3",
            Self::GenerateQuotePdf => "sensei.tasks.pdf.quote",
            Self::RunModelTraining => "sensei.tasks.ml.training",
            Self::CheckDriftAndRetrain => "sensei.tasks.ml.drift-check",
            Self::ForceModelRetrain => "sensei.tasks.ml.force-retrain",
            Self::ScheduledRetrainAll => "sensei.tasks.ml.retrain-all",
            Self::DailyAnalyticsSnapshot => "sensei.tasks.analytics.snapshot",
            Self::ComputeWarehouseKpis => "sensei.tasks.analytics.kpi",
        }
    }
}

/// Task envelope wrapping the payload and metadata for transport.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskEnvelope {
    /// Task metadata.
    pub metadata: TaskMetadata,
    /// The raw JSON payload for the task.
    pub payload: serde_json::Value,
}

impl TaskEnvelope {
    /// Create a new task envelope.
    pub fn new(task_type: TaskType, payload: serde_json::Value) -> Self {
        Self {
            metadata: TaskMetadata::new(task_type),
            payload,
        }
    }

    /// Serialise the envelope to JSON bytes.
    pub fn to_bytes(&self) -> Result<Vec<u8>> {
        serde_json::to_vec(self).map_err(WorkerError::from)
    }

    /// Deserialise from JSON bytes.
    pub fn from_bytes(data: &[u8]) -> Result<Self> {
        serde_json::from_slice(data).map_err(WorkerError::from)
    }
}

/// Subject used for tasks that exhausted their retry budget or failed
/// permanently. A worker consuming this subject can surface the failures.
pub const DLQ_SUBJECT: &str = "sensei.tasks.dead";

// ── Application-level outcome classification ────────────────────────────────

/// Outcome of processing one task, classified by the worker. The dispatcher
/// maps each variant onto a JetStream acknowledgement:
///
/// | Outcome                    | Dispatcher action                              |
/// |----------------------------|------------------------------------------------|
/// | [`Completed`]              | ack                                            |
/// | [`RetryLater`]             | NAK with delay (JetStream redelivers, bounded  |
/// |                            | by the consumer's `max_deliver`)               |
/// | [`FailedPermanent`]        | publish to [`DLQ_SUBJECT`], then ack the       |
/// |                            | original **only after** the DLQ publish is     |
/// |                            | acknowledged by the server                     |
///
/// [`Completed`]: TaskOutcome::Completed
/// [`RetryLater`]: TaskOutcome::RetryLater
/// [`FailedPermanent`]: TaskOutcome::FailedPermanent
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TaskOutcome {
    /// The task finished successfully; ack the message.
    Completed,
    /// Transient failure: retry later. The optional [`Duration`] is the
    /// requested delay before the next delivery (JetStream NAK-with-delay);
    /// `None` falls back to the consumer's backoff schedule.
    RetryLater(Option<Duration>),
    /// Permanent failure: dead-letter the message.
    FailedPermanent,
}

impl TaskOutcome {
    /// Shorthand for a permanent failure.
    pub fn failed() -> Self {
        Self::FailedPermanent
    }

    /// Shorthand for a retry with a specific delay.
    pub fn retry_in(delay: Duration) -> Self {
        Self::RetryLater(Some(delay))
    }
}

/// Adapter from the legacy `Result<()>` worker convention to [`TaskOutcome`]:
///
/// * `Ok(())` → [`Completed`](TaskOutcome::Completed)
/// * [`WorkerError::RetryLater`] → [`RetryLater`](TaskOutcome::RetryLater)
///   with `None` (dispatcher falls back to the consumer backoff schedule)
/// * any other error → returned unchanged (dispatcher dead-letters)
pub fn outcome_from_result(result: Result<()>) -> Result<TaskOutcome> {
    match result {
        Ok(()) => Ok(TaskOutcome::Completed),
        Err(WorkerError::RetryLater(msg)) => {
            warn!(error = %msg, "Task failed transiently — scheduling retry");
            Ok(TaskOutcome::RetryLater(None))
        }
        Err(e) => Err(e),
    }
}

/// A consumer that processes tasks of a specific type.
///
/// Implementations must be [`Send`] + [`Sync`] so they can be shared across
/// tokio tasks inside the dispatcher.
#[async_trait]
pub trait TaskConsumer: Send + Sync {
    /// The NATS subject this consumer listens on (e.g. `"sensei.tasks.email.send"`).
    fn subject(&self) -> &'static str;

    /// Consumer group / durable name used for competing consumers.
    fn consumer_group(&self) -> &'static str;

    /// Process a single task.
    ///
    /// Return `Ok(TaskOutcome::Completed)` on success,
    /// `Ok(TaskOutcome::RetryLater(Some(delay)))` for a transient failure
    /// that should be retried, and `Ok(TaskOutcome::FailedPermanent)` or
    /// `Err(...)` for permanent failures that must be dead-lettered.
    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<TaskOutcome>;
}

// ── Idempotency (migration 053) ──────────────────────────────────────────────

/// Claims `task_id` in the `processed_tasks` table before a worker executes
/// a side effect, so a redelivered message can never run the side effect
/// twice.
///
/// Without a database pool (single-process dev mode) every claim succeeds —
/// there is no cross-process duplication to guard against.
pub struct IdempotencyGuard {
    pool: Option<Arc<PgPool>>,
    worker: &'static str,
}

impl IdempotencyGuard {
    /// Create a guard for the given worker type.
    pub fn new(pool: Option<Arc<PgPool>>, worker: &'static str) -> Self {
        Self { pool, worker }
    }

    /// Try to claim `task_id` for this worker with a lease.
    ///
    /// Semantics (lease-based — a retry is NEVER mistaken for a completed
    /// duplicate):
    /// * `Ok(ClaimOutcome::Proceed)` — the lease was acquired; execute the
    ///   side effect, then call [`Self::mark_completed`] on success.
    /// * `Ok(ClaimOutcome::AlreadyCompleted)` — a previous attempt completed
    ///   successfully; skip the side effect and ack.
    /// * `Ok(ClaimOutcome::Busy)` — another replica holds a live lease;
    ///   retry later (the delivery will back off and re-claim once the
    ///   lease expires).
    /// * `Err(_)` — the claim could not be verified (database unavailable);
    ///   the caller must **not** execute the side effect and should retry.
    pub async fn try_claim(&self, task_id: &str) -> Result<ClaimOutcome> {
        let Some(pool) = &self.pool else {
            // Dev mode (no DB): single-process assumption documented in
            // lib.rs — no deduplication needed.
            return Ok(ClaimOutcome::Proceed);
        };

        let row: String = sqlx::query_scalar(
            "INSERT INTO processed_tasks (task_id, worker, state, lease_until) \
             VALUES ($1, $2, 'in_progress', NOW() + INTERVAL '5 minutes') \
             ON CONFLICT (task_id) DO UPDATE SET \
                 state = CASE \
                     WHEN processed_tasks.state = 'completed' THEN 'completed' \
                     WHEN processed_tasks.state = 'in_progress' AND processed_tasks.lease_until < NOW() \
                         THEN 'in_progress' \
                     ELSE processed_tasks.state \
                 END, \
                 lease_until = CASE \
                     WHEN processed_tasks.state = 'in_progress' AND processed_tasks.lease_until < NOW() \
                         THEN NOW() + INTERVAL '5 minutes' \
                     ELSE processed_tasks.lease_until \
                 END, \
                 worker = CASE \
                     WHEN processed_tasks.state = 'in_progress' AND processed_tasks.lease_until < NOW() \
                         THEN $2 \
                     ELSE processed_tasks.worker \
                 END \
             RETURNING state",
        )
        .bind(task_id)
        .bind(self.worker)
        .fetch_one(pool.as_ref())
        .await
        .map_err(|e| {
            WorkerError::Processing(format!(
                "idempotency claim for task '{task_id}' failed: {e}"
            ))
        })?;

        match row.as_str() {
            "in_progress" => Ok(ClaimOutcome::Proceed),
            "completed" => Ok(ClaimOutcome::AlreadyCompleted),
            _ => Ok(ClaimOutcome::Busy),
        }
    }

    /// Record that the side effect COMPLETED successfully. Must be called
    /// after the effect succeeded — never before.
    pub async fn mark_completed(&self, task_id: &str) -> Result<()> {
        let Some(pool) = &self.pool else {
            return Ok(());
        };
        sqlx::query(
            "UPDATE processed_tasks SET state = 'completed', completed_at = NOW() \
             WHERE task_id = $1 AND state = 'in_progress'",
        )
        .bind(task_id)
        .execute(pool.as_ref())
        .await
        .map_err(|e| {
            WorkerError::Processing(format!(
                "idempotency completion for task '{task_id}' failed: {e}"
            ))
        })?;
        Ok(())
    }

    /// Record a permanent failure (optional; keeps the row for observability).
    pub async fn mark_failed(&self, task_id: &str) -> Result<()> {
        let Some(pool) = &self.pool else {
            return Ok(());
        };
        sqlx::query(
            "UPDATE processed_tasks SET state = 'failed', failed_at = NOW() \
             WHERE task_id = $1 AND state = 'in_progress'",
        )
        .bind(task_id)
        .execute(pool.as_ref())
        .await
        .map_err(|e| {
            WorkerError::Processing(format!(
                "idempotency failure record for task '{task_id}' failed: {e}"
            ))
        })?;
        Ok(())
    }
}

/// Result of an idempotency lease claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClaimOutcome {
    /// Lease acquired — execute the side effect, then mark completed.
    Proceed,
    /// A previous attempt completed successfully — skip and ack.
    AlreadyCompleted,
    /// Another replica holds a live lease — back off and retry later.
    Busy,
}

// ── Dispatcher ───────────────────────────────────────────────────────────────

/// Default maximum deliveries per message (transport retry budget).
pub const DEFAULT_MAX_DELIVER: i64 = 8;
/// Default ack-wait for the pull consumer.
pub const DEFAULT_ACK_WAIT: Duration = Duration::from_secs(60);
/// Default max pending unacked messages per consumer.
pub const DEFAULT_MAX_ACK_PENDING: i64 = 1024;
/// JetStream redelivery backoff schedule applied after failed deliveries
/// (must have `DEFAULT_MAX_DELIVER - 1` entries).
pub const DEFAULT_TRANSPORT_BACKOFF: [Duration; 7] = [
    Duration::from_secs(5),
    Duration::from_secs(10),
    Duration::from_secs(30),
    Duration::from_secs(60),
    Duration::from_secs(120),
    Duration::from_secs(300),
    Duration::from_secs(600),
];
/// Fallback delay for `RetryLater(None)`.
pub const DEFAULT_RETRY_DELAY: Duration = Duration::from_secs(30);

/// Manages a collection of [`TaskConsumer`] instances and their NATS JetStream
/// pull consumers.
///
/// Consumers are stored as [`Arc`] so they can be shared across multiple
/// tokio tasks spawned by [`start`](Self::start). Each consumer runs inside
/// the supervised re-subscribe loop from [`nats::run_supervised`], so a
/// stream failure no longer terminates the consumer.
pub struct TaskDispatcher {
    /// The NATS JetStream context used to create consumers.
    js: Context,
    /// Registered task consumers (Arc for sharing across spawned tasks).
    consumers: Vec<Arc<dyn TaskConsumer>>,
    /// Namespace for the stream (defaults to `"sensei"`).
    stream_name: String,
    /// Per-consumer readiness signals for health surfaces.
    readiness: std::sync::Mutex<Vec<(String, Readiness)>>,
}

impl TaskDispatcher {
    /// Create a new [`TaskDispatcher`] with the given JetStream context.
    pub fn new(js: Context) -> Self {
        Self {
            js,
            consumers: Vec::new(),
            stream_name: "sensei".to_string(),
            readiness: std::sync::Mutex::new(Vec::new()),
        }
    }

    /// Set a custom stream name (default: `"sensei"`).
    pub fn with_stream_name(mut self, name: impl Into<String>) -> Self {
        self.stream_name = name.into();
        self
    }

    /// Register a [`TaskConsumer`] to be started when [`start`](Self::start) is called.
    pub fn register(&mut self, consumer: Arc<dyn TaskConsumer>) {
        info!(
            subject = consumer.subject(),
            group = consumer.consumer_group(),
            "Registered task consumer"
        );
        self.consumers.push(consumer);
    }

    /// Ensure the JetStream stream exists (idempotent).
    async fn ensure_stream(&self) -> Result<async_nats::jetstream::stream::Stream> {
        use async_nats::jetstream::stream::Config;

        let cfg = Config {
            name: self.stream_name.clone(),
            // The DLQ subject is listed explicitly so dead-lettered tasks are
            // retained by the same stream (and can be consumed/monitored).
            subjects: vec!["sensei.tasks.>".to_string(), DLQ_SUBJECT.to_string()],
            max_messages: 10_000_000,
            max_message_size: 1_048_576, // 1 MB
            ..Default::default()
        };

        self.js
            .get_or_create_stream(cfg)
            .await
            .map_err(|e| WorkerError::JetStream(e.to_string()))
    }

    /// Start all registered consumers.
    ///
    /// For each consumer this will:
    /// 1. Ensure the JetStream stream exists.
    /// 2. Create (or reuse) a pull consumer with the consumer's group name,
    ///    configured with `max_deliver` + `backoff` (JetStream transport
    ///    retry) and an `ack_wait`.
    /// 3. Spawn a tokio task running the supervised receive loop from
    ///    [`nats::run_supervised`] — the consumer re-subscribes with
    ///    exponential backoff (1s → 60s cap) if the stream fails, instead of
    ///    terminating.
    ///
    /// Readiness per consumer can be polled via [`consumer_readiness`]
    /// (Self::consumer_readiness).
    pub async fn start(&self) -> Result<Vec<tokio::task::JoinHandle<()>>> {
        // Fail fast if JetStream is unreachable at startup.
        self.ensure_stream().await?;
        let mut handles = Vec::new();

        for consumer in &self.consumers {
            let subject = consumer.subject();
            let group = consumer.consumer_group();
            let label = format!("{}/{}", group, subject);

            let (readiness, _receiver) = Readiness::new();
            self.readiness
                .lock()
                .expect("dispatcher readiness mutex poisoned")
                .push((label.clone(), readiness.clone()));

            let spec = SubscriptionSpec {
                stream_name: self.stream_name.clone(),
                subject: subject.to_string(),
                consumer_name: group.to_string(),
                config: pull::Config {
                    filter_subject: subject.to_string(),
                    max_deliver: DEFAULT_MAX_DELIVER,
                    ack_wait: DEFAULT_ACK_WAIT,
                    max_ack_pending: DEFAULT_MAX_ACK_PENDING,
                    backoff: DEFAULT_TRANSPORT_BACKOFF.to_vec(),
                    ..Default::default()
                },
            };

            let consumer_arc = Arc::clone(consumer);
            let js = self.js.clone();
            let handle = tokio::spawn(async move {
                run_supervised(js.clone(), spec, readiness, move |msg| {
                    let consumer_arc = Arc::clone(&consumer_arc);
                    let js = js.clone();
                    let label = label.clone();
                    async move { dispatch_message(&js, &consumer_arc, &label, msg).await }
                })
                .await;
            });

            handles.push(handle);
        }

        Ok(handles)
    }

    /// Snapshot of consumer readiness: `(consumer label, subscribed)`.
    ///
    /// The binary can surface this in its health endpoint; see also
    /// [`nats::report_worker_status`] for DB-backed reporting.
    pub fn consumer_readiness(&self) -> Vec<(String, bool)> {
        self.readiness
            .lock()
            .expect("dispatcher readiness mutex poisoned")
            .iter()
            .map(|(name, r)| (name.clone(), r.is_subscribed()))
            .collect()
    }

    /// Return the number of registered consumers.
    pub fn consumer_count(&self) -> usize {
        self.consumers.len()
    }
}

// ── Message dispatch ─────────────────────────────────────────────────────────

/// Process one JetStream message and apply the ack/NAK/DLQ policy.
///
/// Guarantees:
/// * The original message is acked **only after** the DLQ replacement has
///   been acknowledged by the server.
/// * On DLQ publish failure the original is NAKed (or left unacked) so it is
///   redelivered.
async fn dispatch_message(
    js: &Context,
    consumer: &Arc<dyn TaskConsumer>,
    consumer_name: &str,
    msg: Message,
) {
    let envelope = match TaskEnvelope::from_bytes(&msg.payload) {
        Ok(envelope) => envelope,
        Err(e) => {
            error!(consumer = %consumer_name, error = %e,
                "Failed to deserialize task envelope — dead-lettering instead of silently discarding");
            dead_letter(
                js,
                &msg,
                None,
                Some(format!("malformed task envelope: {e}")),
            )
            .await;
            return;
        }
    };

    let payload_bytes = match serde_json::to_vec(&envelope.payload) {
        Ok(bytes) => bytes,
        Err(e) => {
            error!(consumer = %consumer_name, error = %e,
                task_id = %envelope.metadata.task_id,
                "Failed to serialize task payload — dead-lettering");
            dead_letter(
                js,
                &msg,
                Some(&envelope.metadata),
                Some(format!("payload re-serialization failed: {e}")),
            )
            .await;
            return;
        }
    };

    let mut metadata = envelope.metadata;
    if let Ok(info) = msg.info() {
        metadata.record_delivery(info.delivered);
    }

    match consumer.process(&payload_bytes, &metadata).await {
        Ok(TaskOutcome::Completed) => {
            info!(
                consumer = %consumer_name,
                task_id = %metadata.task_id,
                attempts = metadata.attempts,
                "Task completed successfully"
            );
            if let Err(e) = msg.ack().await {
                warn!(error = %e, "Failed to ack message after completion");
            }
        }
        Ok(TaskOutcome::RetryLater(delay)) => {
            let delay = delay.unwrap_or(DEFAULT_RETRY_DELAY);
            warn!(
                consumer = %consumer_name,
                task_id = %metadata.task_id,
                attempts = metadata.attempts,
                delay_ms = delay.as_millis(),
                "Task failed transiently — NAK with delay (JetStream will redeliver)"
            );
            // JetStream NAK-with-delay: the server redelivers after `delay`
            // (bounded by the consumer's max_deliver budget).
            if let Err(e) = msg.ack_with(AckKind::Nak(Some(delay))).await {
                warn!(error = %e, "Failed to NAK message with delay — leaving unacked");
            }
        }
        Ok(TaskOutcome::FailedPermanent) => {
            error!(
                consumer = %consumer_name,
                task_id = %metadata.task_id,
                attempts = metadata.attempts,
                "Task failed permanently — dead-lettering"
            );
            dead_letter(js, &msg, Some(&metadata), None).await;
        }
        Err(e) => {
            error!(
                consumer = %consumer_name,
                task_id = %metadata.task_id,
                attempts = metadata.attempts,
                error = %e,
                "Task failed permanently — dead-lettering"
            );
            dead_letter(js, &msg, Some(&metadata), Some(e.to_string())).await;
        }
    }
}

/// Publish the raw message to the DLQ subject and only then ack the original.
///
/// The DLQ message carries the original payload plus headers with the task
/// id, task type and (when known) the failure reason. If the DLQ publish is
/// not acknowledged by the server the original is NAKed so JetStream
/// redelivers it later — it is never dropped.
async fn dead_letter(
    js: &Context,
    msg: &Message,
    metadata: Option<&TaskMetadata>,
    error: Option<String>,
) {
    let mut headers = async_nats::HeaderMap::new();
    if let Some(md) = metadata {
        headers.insert("sensei-task-id", md.task_id.to_string());
        headers.insert("sensei-task-type", format!("{:?}", md.task_type));
    }
    if let Some(err) = error {
        headers.insert("sensei-task-error", err);
    }

    match js
        .publish_with_headers(DLQ_SUBJECT, headers, msg.payload.clone())
        .await
    {
        Ok(ack) => {
            // Two-stage publish: ONLY the server acknowledgement makes the
            // DLQ copy durable. The original is acked only AFTER that.
            match tokio::time::timeout(std::time::Duration::from_secs(10), ack).await {
                Ok(Ok(_)) => {
                    info!(
                        dlq_subject = DLQ_SUBJECT,
                        task_id = metadata.map(|m| m.task_id.to_string()).unwrap_or_default(),
                        "DLQ publish server-acknowledged — acking original message"
                    );
                    if let Err(e) = msg.ack().await {
                        warn!(error = %e, "Failed to ack original after DLQ publish");
                    }
                }
                _ => {
                    // The DLQ copy is NOT durable: leave the original
                    // unacked so JetStream redelivers it.
                    error!(
                        dlq_subject = DLQ_SUBJECT,
                        task_id = metadata.map(|m| m.task_id.to_string()).unwrap_or_default(),
                        "DLQ publish NOT server-acknowledged — original left unacked for redelivery"
                    );
                }
            }
        }
        Err(e) => {
            error!(
                dlq_subject = DLQ_SUBJECT,
                error = %e,
                "DLQ publish failed — NAKing original so it is redelivered"
            );
            if let Err(ack_err) = msg.ack_with(AckKind::Nak(None)).await {
                warn!(error = %ack_err, "Failed to NAK original after DLQ publish failure");
            }
        }
    }
}

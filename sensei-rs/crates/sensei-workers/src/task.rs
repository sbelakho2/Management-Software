//! Core task types, the [`TaskConsumer`] trait, and the [`TaskDispatcher`]
//! that manages pull-based JetStream consumers.

use crate::error::{Result, WorkerError};
use async_nats::jetstream::consumer::pull;
use async_nats::jetstream::Context;
use async_trait::async_trait;
use futures::StreamExt;
use serde::{Deserialize, Serialize};
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
    /// Maximum number of retries before the task is considered failed.
    pub max_retries: u32,
    /// Current retry count (0 on first attempt).
    pub retry_count: u32,
}

impl TaskMetadata {
    /// Create a new [`TaskMetadata`] with the given parameters.
    pub fn new(task_type: TaskType) -> Self {
        Self {
            task_id: Uuid::new_v4(),
            task_type,
            correlation_id: None,
            created_at: chrono::Utc::now(),
            max_retries: 3,
            retry_count: 0,
        }
    }

    /// Increment the retry count and return true if retries remain.
    pub fn can_retry(&self) -> bool {
        self.retry_count < self.max_retries
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
    /// Return `Ok(())` on success. Return [`WorkerError::RetryLater`] to signal
    /// a transient failure that should be retried. All other errors are treated
    /// as permanent failures.
    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()>;
}

/// Manages a collection of [`TaskConsumer`] instances and their NATS JetStream
/// pull consumers.
///
/// Consumers are stored as [`Arc`] so they can be shared across multiple
/// tokio tasks spawned by [`start`](Self::start).
pub struct TaskDispatcher {
    /// The NATS JetStream context used to create consumers.
    js: Context,
    /// Registered task consumers (Arc for sharing across spawned tasks).
    consumers: Vec<Arc<dyn TaskConsumer>>,
    /// Namespace for the stream (defaults to `"sensei"`).
    stream_name: String,
}

impl TaskDispatcher {
    /// Create a new [`TaskDispatcher`] with the given JetStream context.
    pub fn new(js: Context) -> Self {
        Self {
            js,
            consumers: Vec::new(),
            stream_name: "sensei".to_string(),
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
            subjects: vec!["sensei.tasks.>".to_string()],
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
    /// 2. Create (or reuse) a pull consumer with the consumer's group name.
    /// 3. Spawn a tokio task that continuously polls for messages and dispatches
    ///    them to [`TaskConsumer::process`].
    pub async fn start(&self) -> Result<Vec<tokio::task::JoinHandle<()>>> {
        let stream = self.ensure_stream().await?;
        let mut handles = Vec::new();

        for consumer in &self.consumers {
            let subject = consumer.subject();
            let group = consumer.consumer_group();
            let pull_consumer = stream
                .get_or_create_consumer(
                    group,
                    pull::Config {
                        filter_subject: subject.to_string(),
                        max_deliver: 5,
                        ack_wait: std::time::Duration::from_secs(60),
                        ..Default::default()
                    },
                )
                .await
                .map_err(|e| WorkerError::JetStream(e.to_string()))?;

            let mut messages = pull_consumer
                .messages()
                .await
                .map_err(|e| WorkerError::JetStream(e.to_string()))?;

            let consumer_name = format!("{}/{}", group, subject);
            info!(consumer = %consumer_name, "Starting pull consumer");

            // Clone the Arc so the spawned task gets an owned reference.
            let consumer_arc = Arc::clone(consumer);

            let handle = tokio::spawn(async move {
                loop {
                    tokio::select! {
                        msg = messages.next() => {
                            match msg {
                                Some(Ok(msg)) => {
                                    // Attempt deserialisation
                                    let envelope = match TaskEnvelope::from_bytes(&msg.payload) {
                                        Ok(e) => e,
                                        Err(e) => {
                                            error!(consumer = %consumer_name, error = %e,
                                                "Failed to deserialize task envelope — acking and skipping");
                                            let _ = msg.ack().await;
                                            continue;
                                        }
                                    };

                                    let payload_bytes = serde_json::to_vec(&envelope.payload)
                                        .unwrap_or_default();

                                    // Dispatch to consumer
                                    match consumer_arc.process(&payload_bytes, &envelope.metadata).await {
                                        Ok(()) => {
                                            info!(
                                                consumer = %consumer_name,
                                                task_id = %envelope.metadata.task_id,
                                                "Task completed successfully"
                                            );
                                            if let Err(e) = msg.ack().await {
                                                warn!(error = %e, "Failed to ack message");
                                            }
                                        }
                                        Err(WorkerError::RetryLater(ref msg)) if envelope.metadata.can_retry() => {
                                            warn!(
                                                consumer = %consumer_name,
                                                task_id = %envelope.metadata.task_id,
                                                retry = envelope.metadata.retry_count,
                                                error = %msg,
                                                "Task failed transiently — will be redelivered"
                                            );
                                            // Do NOT ack → message is redelivered by JetStream
                                        }
                                        Err(e) => {
                                            error!(
                                                consumer = %consumer_name,
                                                task_id = %envelope.metadata.task_id,
                                                error = %e,
                                                "Task failed permanently"
                                            );
                                            // Ack so it doesn't stay in the stream
                                            if let Err(ack_err) = msg.ack().await {
                                                warn!(error = %ack_err, "Failed to ack message after permanent failure");
                                            }
                                        }
                                    }
                                }
                                Some(Err(e)) => {
                                    warn!(consumer = %consumer_name, error = %e,
                                        "Error receiving message from JetStream");
                                    tokio::time::sleep(Duration::from_secs(1)).await;
                                }
                                None => {
                                    info!(consumer = %consumer_name, "Message stream ended");
                                    break;
                                }
                            }
                        }
                        // Allow graceful shutdown via cancellation
                        _ = tokio::signal::ctrl_c() => {
                            info!(consumer = %consumer_name, "Received shutdown signal");
                            break;
                        }
                    }
                }
                info!(consumer = %consumer_name, "Consumer stopped");
            });

            handles.push(handle);
        }

        Ok(handles)
    }

    /// Return the number of registered consumers.
    pub fn consumer_count(&self) -> usize {
        self.consumers.len()
    }
}

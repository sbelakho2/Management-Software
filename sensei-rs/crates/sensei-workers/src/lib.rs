//! # Sensei Workers
//!
//! NATS JetStream pull-based task consumer system replacing Python Celery
//! workers. Provides trait-based task consumers, a dispatcher that manages
//! pull-based JetStream consumers, a periodic scheduler for Beat-style
//! tasks, and a supervised receive loop that survives stream failures.
//!
//! ## Crate structure
//!
//! | Module | Purpose |
//! |--------|---------|
//! | [`error`](error) | Worker error types |
//! | [`task`](task) | Core [`TaskConsumer`](task::TaskConsumer) trait, [`TaskDispatcher`](task::TaskDispatcher), [`TaskOutcome`](task::TaskOutcome) |
//! | [`nats`](nats) | Supervised subscriber loop, readiness, worker-status heartbeats |
//! | [`email`](email) | Email dispatch worker |
//! | [`pdf`](pdf) | PDF generation worker |
//! | [`analytics`](analytics) | Analytics snapshot & KPI worker |
//! | [`ml`](ml) | ML model training & drift worker |
//! | [`scheduler`](scheduler) | Periodic task scheduler (Celery Beat replacement) |
//!
//! ## Reliability contract
//!
//! * Task delivery retries are handled by JetStream (`max_deliver` +
//!   `backoff` on each consumer); workers classify outcomes via
//!   [`TaskOutcome`](task::TaskOutcome) and the dispatcher maps them to
//!   ack / NAK-with-delay / DLQ.
//! * A message is only acked after its DLQ replacement is acknowledged by
//!   the server; malformed payloads go to the DLQ instead of being dropped.
//! * Side-effecting workers (email, pdf, ml, analytics) are idempotent per
//!   `task_id` via the `processed_tasks` table (migration 053).
//! * The scheduler uses a PostgreSQL advisory lock for leader election
//!   (migration-free; two pods cannot both run scheduled jobs) and
//!   deduplicates wall-clock slots via `scheduler_run_log` (migration 054).
//! * Consumers never terminate on stream failure: [`nats::run_supervised`]
//!   re-subscribes with exponential backoff (1s → 60s cap).
//!
//! ## Binary contract (consumed by the `sensei-workers` binary)
//!
//! ```rust,no_run
//! use sensei_workers::{WorkerContext, TaskDispatcher};
//!
//! async fn run() -> sensei_workers::error::Result<()> {
//!     let mut ctx = WorkerContext::new("nats://localhost:4222");
//!     // ctx = ctx.with_db_pool(Arc::new(pool)); // enables idempotency + leader election
//!     let runtime = ctx.connect().await?;
//!
//!     let dispatcher = runtime.dispatcher;
//!     let scheduler = runtime.scheduler;
//!     let mut handles = dispatcher.start().await?;
//!     handles.extend(scheduler.start().await?);
//!
//!     for handle in handles { handle.await.unwrap(); }
//!     Ok(())
//! }
//! ```
//!
//! For full control, build the dispatcher yourself and register consumers
//! from [`WorkerContext::default_consumers`].

pub mod analytics;
pub mod email;
pub mod error;
pub mod ml;
pub mod nats;
pub mod outbox_relay;
pub mod pdf;
pub mod scheduler;
pub mod task;

// Re-export core types at the crate root for convenience.
pub use error::WorkerError;
pub use task::{
    IdempotencyGuard, TaskConsumer, TaskDispatcher, TaskEnvelope, TaskMetadata, TaskOutcome,
    TaskType,
};

use async_nats::jetstream::Context;
use sensei_services::storage::FileStorageService;
use sqlx::PgPool;
use std::sync::Arc;

/// Configuration + wiring entry point for the worker process (built by the
/// `sensei-workers` binary). Owns the NATS URL, the optional database pool
/// (enables task idempotency and scheduler leader election), and the
/// stream name.
#[derive(Clone)]
pub struct WorkerContext {
    /// NATS connection URL, e.g. `"nats://localhost:4222"`.
    pub nats_url: String,
    /// JetStream stream name (default `"sensei"`).
    pub stream_name: String,
    /// Optional PostgreSQL pool. When present, side-effecting workers
    /// deduplicate via `processed_tasks` and the scheduler uses
    /// `pg_try_advisory_lock` leader election.
    pub db_pool: Option<Arc<PgPool>>,
    /// Shared file storage (S3/local): generated PDFs must be visible to
    /// the API and every worker replica, never process-local memory.
    pub storage: Arc<dyn FileStorageService>,
    /// Advisory-lock key used by the scheduler leader election.
    pub scheduler_lock_key: i64,
}

impl WorkerContext {
    /// Create a worker context for the given NATS URL.
    ///
    /// Storage defaults to a local-disk backend under `./worker-storage`
    /// (never process memory — generated artifacts must be shared). Attach
    /// S3 with [`Self::with_storage`] for production.
    pub fn new(nats_url: impl Into<String>) -> Self {
        Self {
            nats_url: nats_url.into(),
            stream_name: "sensei".to_string(),
            db_pool: None,
            storage: Arc::new(sensei_services::storage::LocalStorageService::new(
                "./worker-storage",
            )),
            scheduler_lock_key: DEFAULT_SCHEDULER_LOCK_KEY,
        }
    }

    /// Attach a database pool (idempotency + leader election).
    pub fn with_db_pool(mut self, pool: Arc<PgPool>) -> Self {
        self.db_pool = Some(pool);
        self
    }

    /// Attach the shared storage backend (S3/local).
    pub fn with_storage(mut self, storage: Arc<dyn FileStorageService>) -> Self {
        self.storage = storage;
        self
    }

    /// Override the JetStream stream name.
    pub fn with_stream_name(mut self, name: impl Into<String>) -> Self {
        self.stream_name = name.into();
        self
    }

    /// Override the PostgreSQL advisory-lock key used by the scheduler.
    pub fn with_scheduler_lock_key(mut self, key: i64) -> Self {
        self.scheduler_lock_key = key;
        self
    }

    /// Build the default set of task consumers (email, pdf, ml, analytics),
    /// wiring the database pool into each worker's idempotency guard. The
    /// JetStream context is required by the PDF workers (KV progress).
    pub fn default_consumers(&self, js: Context) -> Vec<Arc<dyn TaskConsumer>> {
        let pool = self.db_pool.clone();
        vec![
            Arc::new(email::EmailWorker::with_pool(pool.clone())),
            Arc::new(pdf::A3PdfWorker::with_deps(
                js.clone(),
                pool.clone(),
                self.storage.clone(),
            )),
            Arc::new(pdf::QuotePdfWorker::with_deps(
                js.clone(),
                pool.clone(),
                self.storage.clone(),
            )),
            Arc::new(ml::TrainingWorker::with_pool(pool.clone())),
            Arc::new(ml::DriftCheckWorker::with_pool(pool.clone())),
            Arc::new(ml::ForceRetrainWorker::with_pool(pool.clone())),
            Arc::new(ml::RetrainAllWorker::with_pool(pool.clone())),
            Arc::new(analytics::SnapshotWorker::with_pool(pool.clone())),
            Arc::new(analytics::KpiWorker::with_pool(pool)),
        ]
    }

    /// Connect to NATS and return a fully-wired runtime: a dispatcher
    /// pre-registered with [`default_consumers`](Self::default_consumers)
    /// and a scheduler pre-populated with the default schedule.
    ///
    /// The caller starts both with `.start().await?` and awaits the handles.
    pub async fn connect(&self) -> error::Result<WorkerRuntime> {
        let client = async_nats::connect(&self.nats_url).await.map_err(|e| {
            WorkerError::Processing(format!(
                "failed to connect to NATS at {}: {e}",
                self.nats_url
            ))
        })?;
        let js = async_nats::jetstream::new(client);

        let mut dispatcher =
            TaskDispatcher::new(js.clone()).with_stream_name(self.stream_name.clone());
        for consumer in self.default_consumers(js.clone()) {
            dispatcher.register(consumer);
        }

        let scheduler = if let Some(pool) = self.db_pool.clone() {
            scheduler::TaskScheduler::with_leader_election(
                js.clone(),
                pool,
                self.scheduler_lock_key,
            )
            .with_default_schedule()
            .await
        } else {
            scheduler::TaskScheduler::new(js.clone())
                .with_default_schedule()
                .await
        };

        Ok(WorkerRuntime {
            js,
            dispatcher,
            scheduler,
        })
    }
}

/// Default advisory-lock key for the scheduler leader election. Must match
/// across all worker replicas in the same cluster.
pub const DEFAULT_SCHEDULER_LOCK_KEY: i64 = 0x5345_4E53_4549_0001;

/// A connected worker runtime ready to be started by the binary.
pub struct WorkerRuntime {
    /// JetStream context (for custom consumers / publishes).
    pub js: Context,
    /// Dispatcher pre-registered with the default consumers.
    pub dispatcher: TaskDispatcher,
    /// Scheduler pre-populated with the default Beat-style schedule.
    pub scheduler: scheduler::TaskScheduler,
}

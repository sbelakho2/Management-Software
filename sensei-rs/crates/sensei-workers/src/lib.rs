//! # Sensei Workers
//!
//! NATS JetStream pull-based task consumer system replacing Python Celery
//! workers. Provides trait-based task consumers, a dispatcher that manages
//! pull-based JetStream consumers, and a periodic scheduler for Beat-style
//! tasks.
//!
//! ## Crate structure
//!
//! | Module | Purpose |
//! |--------|---------|
//! | [`error`](error) | Worker error types |
//! | [`task`](task) | Core [`TaskConsumer`](task::TaskConsumer) trait and [`TaskDispatcher`](task::TaskDispatcher) |
//! | [`email`](email) | Email dispatch worker |
//! | [`pdf`](pdf) | PDF generation worker |
//! | [`analytics`](analytics) | Analytics snapshot & KPI worker |
//! | [`ml`](ml) | ML model training & drift worker |
//! | [`scheduler`](scheduler) | Periodic task scheduler (Celery Beat replacement) |
//!
//! ## Quick start
//!
//! ```rust,no_run
//! use sensei_workers::task::{TaskDispatcher, TaskConsumer};
//! use sensei_workers::email::EmailWorker;
//! use sensei_workers::scheduler::TaskScheduler;
//! use async_nats::jetstream::Context;
//! use std::sync::Arc;
//!
//! async fn run() -> sensei_workers::error::Result<()> {
//!     // Connect to NATS.
//!     let client = async_nats::connect("nats://localhost:4222").await.unwrap();
//!     let js = async_nats::jetstream::new(client);
//!
//!     // Create the dispatcher.
//!     let dispatcher = TaskDispatcher::new(js.clone());
//!     // Register workers...
//!     // dispatcher.register(Box::new(EmailWorker::new()));
//!
//!     // Start consuming.
//!     let consumer_handles = dispatcher.start().await?;
//!
//!     // Wait for all consumers.
//!     for handle in consumer_handles {
//!         handle.await.unwrap();
//!     }
//!     Ok(())
//! }
//! ```

pub mod analytics;
pub mod email;
pub mod error;
pub mod ml;
pub mod pdf;
pub mod scheduler;
pub mod task;

// Re-export core types at the crate root for convenience.
pub use error::WorkerError;
pub use task::{TaskConsumer, TaskDispatcher, TaskEnvelope, TaskMetadata, TaskType};

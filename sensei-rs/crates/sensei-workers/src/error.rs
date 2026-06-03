//! Worker error types for the task consumer system.

use thiserror::Error;

/// Errors that can occur during worker operations.
#[derive(Debug, Error)]
pub enum WorkerError {
    /// Serialization/deserialization error.
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    /// NATS / event bus error.
    #[error("NATS error: {0}")]
    Nats(#[from] sensei_event_bus::error::EventBusError),

    /// Generic processing error — task is considered failed permanently.
    #[error("Processing error: {0}")]
    Processing(String),

    /// Retryable error — task should be retried later.
    #[error("Retry later: {0}")]
    RetryLater(String),

    /// NATS client-level error (not wrapped by EventBusError).
    #[error("NATS client error: {0}")]
    NatsClient(#[from] async_nats::Error),

    /// JetStream error.
    #[error("JetStream error: {0}")]
    JetStream(String),

    /// KV store error.
    #[error("KV store error: {0}")]
    KvStore(String),

    /// Invalid configuration or state.
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    /// A timeout occurred during processing.
    #[error("Timeout: {0}")]
    Timeout(String),

    /// Signal / shutdown related error.
    #[error("Shutdown: {0}")]
    Shutdown(String),
}

impl From<String> for WorkerError {
    fn from(msg: String) -> Self {
        WorkerError::Processing(msg)
    }
}

impl From<&str> for WorkerError {
    fn from(msg: &str) -> Self {
        WorkerError::Processing(msg.to_string())
    }
}

/// Convenience result alias for worker operations.
pub type Result<T> = std::result::Result<T, WorkerError>;

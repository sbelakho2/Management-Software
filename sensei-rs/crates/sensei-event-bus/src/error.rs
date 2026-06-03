//! Event bus error types.

use thiserror::Error;

/// Errors that can occur during event bus operations.
#[derive(Error, Debug)]
pub enum EventBusError {
    /// Failed to connect to NATS.
    #[error("Failed to connect to NATS: {0}")]
    ConnectionFailed(String),

    /// Failed to publish an event.
    #[error("Failed to publish event: {0}")]
    PublishFailed(String),

    /// Failed to subscribe to a subject.
    #[error("Failed to subscribe: {0}")]
    SubscribeFailed(String),

    /// Failed to deserialize an event.
    #[error("Deserialization error: {0}")]
    DeserializationFailed(String),

    /// Failed to serialize an event.
    #[error("Serialization error: {0}")]
    SerializationFailed(String),

    /// JetStream stream operation failed.
    #[error("JetStream error: {0}")]
    JetStreamError(String),

    /// The event bus is not connected.
    #[error("Event bus is not connected")]
    NotConnected,

    /// A timeout occurred during an event bus operation.
    #[error("Event bus timeout")]
    Timeout,
}

/// Convenience result alias for event bus operations.
pub type Result<T> = std::result::Result<T, EventBusError>;

impl From<EventBusError> for sensei_core::error::SenseiError {
    fn from(err: EventBusError) -> Self {
        sensei_core::error::SenseiError::EventBus(err.to_string())
    }
}

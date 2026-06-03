//! Event bus implementation using NATS JetStream.
//!
//! Provides a trait-based abstraction for publishing and subscribing to
//! domain events, with a concrete NATS JetStream implementation.

use crate::error::{EventBusError, Result};
use crate::types::{EventEnvelope, EventHeaders};
use async_nats::jetstream;
use async_nats::jetstream::consumer::pull;
use async_nats::jetstream::stream::Stream;
use async_nats::ConnectOptions;
use async_trait::async_trait;
use futures::StreamExt;
use sensei_core::domain::events::DomainEvent;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

/// Callback type for event handlers.
pub type EventHandler = Arc<dyn Fn(EventEnvelope) -> Result<()> + Send + Sync>;

/// Trait abstracting the event bus operations.
#[async_trait]
pub trait EventBus: Send + Sync {
    /// Connect to the event bus.
    async fn connect(&self, url: &str) -> Result<()>;

    /// Publish a domain event to the bus.
    async fn publish(&self, event: &dyn DomainEvent) -> Result<()>;

    /// Subscribe to events matching the given subject pattern.
    async fn subscribe(&self, subject: &str, handler: EventHandler) -> Result<()>;

    /// Check if the bus is connected.
    fn is_connected(&self) -> bool;

    /// Disconnect from the bus.
    async fn disconnect(&self) -> Result<()>;
}

/// NATS JetStream implementation of the [`EventBus`] trait.
pub struct NatsEventBus {
    /// The NATS client connection.
    client: RwLock<Option<async_nats::Client>>,
    /// JetStream context.
    jetstream: RwLock<Option<jetstream::Context>>,
    /// The stream name used for persistence.
    stream_name: String,
}

impl NatsEventBus {
    /// Create a new [`NatsEventBus`] with the given stream name.
    pub fn new(stream_name: impl Into<String>) -> Self {
        Self {
            client: RwLock::new(None),
            jetstream: RwLock::new(None),
            stream_name: stream_name.into(),
        }
    }

    /// Ensure the JetStream stream exists, creating it if necessary.
    async fn ensure_stream(&self, js: &jetstream::Context) -> Result<Stream> {
        let cfg = jetstream::stream::Config {
            name: self.stream_name.clone(),
            subjects: vec!["sensei.>".to_string()],
            max_messages: 10_000_000,
            max_message_size: 1_048_576, // 1MB
            ..Default::default()
        };

        js.get_or_create_stream(cfg)
            .await
            .map_err(|e| EventBusError::JetStreamError(e.to_string()))
    }
}

#[async_trait]
impl EventBus for NatsEventBus {
    async fn connect(&self, url: &str) -> Result<()> {
        info!(url, "Connecting to NATS event bus");

        let client = async_nats::connect_with_options(url, ConnectOptions::new())
            .await
            .map_err(|e| EventBusError::ConnectionFailed(e.to_string()))?;

        let js = async_nats::jetstream::new(client.clone());

        // Create stream if not exists
        self.ensure_stream(&js).await?;

        *self.client.write().await = Some(client.clone());
        *self.jetstream.write().await = Some(js);

        info!("Connected to NATS event bus");
        Ok(())
    }

    async fn publish(&self, event: &dyn DomainEvent) -> Result<()> {
        let js = self
            .jetstream
            .read()
            .await
            .as_ref()
            .ok_or(EventBusError::NotConnected)?
            .clone();

        let subject = event.event_type().to_string();
        let payload = event
            .payload()
            .map_err(|e| EventBusError::SerializationFailed(e.to_string()))?;

        let envelope = EventEnvelope {
            event_type: event.event_type().to_string(),
            payload,
            headers: EventHeaders::new(
                event.event_id(),
                event.correlation_id(),
                event.tenant_id(),
                None,
            ),
        };

        let data = serde_json::to_vec(&envelope)
            .map_err(|e| EventBusError::SerializationFailed(e.to_string()))?;

        js.publish(subject, data.into())
            .await
            .map_err(|e| EventBusError::PublishFailed(e.to_string()))?;

        info!(
            event_type = event.event_type(),
            "Published event to NATS"
        );
        Ok(())
    }

    async fn subscribe(&self, subject: &str, handler: EventHandler) -> Result<()> {
        let js = self
            .jetstream
            .read()
            .await
            .as_ref()
            .ok_or(EventBusError::NotConnected)?
            .clone();

        let stream = self
            .ensure_stream(&js)
            .await?;

        let consumer_name = format!("sensei-worker-{}", subject.replace('.', "-"));
        let consumer = stream
            .get_or_create_consumer(
                &consumer_name,
                pull::Config {
                    filter_subject: subject.to_string(),
                    ..Default::default()
                },
            )
            .await
            .map_err(|e| EventBusError::SubscribeFailed(e.to_string()))?;

        let mut messages = consumer.messages().await
            .map_err(|e| EventBusError::SubscribeFailed(e.to_string()))?;

        let handler = handler.clone();
        tokio::spawn(async move {
            while let Some(Ok(msg)) = messages.next().await {
                let payload = msg.payload.to_vec();
                match serde_json::from_slice::<EventEnvelope>(&payload) {
                    Ok(envelope) => {
                        if let Err(e) = handler(envelope) {
                            error!("Event handler error: {e}");
                            // Do not ack — message will be redelivered
                            continue;
                        }
                    }
                    Err(e) => {
                        warn!("Failed to deserialize event: {e}");
                    }
                }
                // Acknowledge message
                if let Err(e) = msg.ack().await {
                    warn!("Failed to ack message: {e}");
                }
            }
        });

        info!(subject, "Subscribed to event subject");
        Ok(())
    }

    fn is_connected(&self) -> bool {
        self.client.try_read().map(|c| c.is_some()).unwrap_or(false)
    }

    async fn disconnect(&self) -> Result<()> {
        let mut client = self.client.write().await;
        if let Some(_c) = client.take() {
            // Flush is deprecated in v0.38; just drop the connection
            info!("Disconnected from NATS event bus");
        }
        *self.jetstream.write().await = None;
        Ok(())
    }
}

/// In-memory event bus for testing and development.
pub struct InMemoryEventBus {
    subscribers: Arc<RwLock<Vec<(String, EventHandler)>>>,
}

impl InMemoryEventBus {
    /// Create a new empty [`InMemoryEventBus`].
    pub fn new() -> Self {
        Self {
            subscribers: Arc::new(RwLock::new(Vec::new())),
        }
    }
}

impl Default for InMemoryEventBus {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl EventBus for InMemoryEventBus {
    async fn connect(&self, _url: &str) -> Result<()> {
        Ok(())
    }

    async fn publish(&self, event: &dyn DomainEvent) -> Result<()> {
        let payload = event
            .payload()
            .map_err(|e| EventBusError::SerializationFailed(e.to_string()))?;

        let envelope = EventEnvelope {
            event_type: event.event_type().to_string(),
            payload,
            headers: EventHeaders::new(
                event.event_id(),
                event.correlation_id(),
                event.tenant_id(),
                None,
            ),
        };

        let subscribers = self.subscribers.read().await;
        for (subject, handler) in subscribers.iter() {
            if event.event_type().starts_with(subject.trim_end_matches('>').trim_end_matches('.')) {
                if let Err(e) = handler(envelope.clone()) {
                    warn!("In-memory handler error: {e}");
                }
            }
        }

        Ok(())
    }

    async fn subscribe(&self, subject: &str, handler: EventHandler) -> Result<()> {
        let mut subscribers = self.subscribers.write().await;
        subscribers.push((subject.to_string(), handler));
        Ok(())
    }

    fn is_connected(&self) -> bool {
        true
    }

    async fn disconnect(&self) -> Result<()> {
        self.subscribers.write().await.clear();
        Ok(())
    }
}

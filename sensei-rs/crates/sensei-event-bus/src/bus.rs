//! Event bus implementation using NATS JetStream.
//!
//! Provides a trait-based abstraction for publishing and subscribing to
//! domain events, with a concrete NATS JetStream implementation and an
//! in-memory fallback for testing and development.
//!
//! # Subject semantics
//!
//! All published event subjects are prefixed with `sensei.` (e.g. an event
//! of type `quality.ncr.created` is published on `sensei.quality.ncr.created`)
//! so that the JetStream stream (`sensei.>`) captures every event.
//! Subscriptions use the same prefix: `sensei.>` matches everything and
//! `sensei.quality.>` matches all quality events. Subjects passed to
//! `subscribe`/`subscribe_with_group` are normalized to the `sensei.` prefix
//! if missing.

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

/// The subject prefix applied to every published event.
pub const SUBJECT_PREFIX: &str = "sensei";

/// Trait abstracting the event bus operations.
#[async_trait]
pub trait EventBus: Send + Sync {
    /// Connect to the event bus.
    async fn connect(&self, url: &str) -> Result<()>;

    /// Publish a domain event to the bus.
    async fn publish(&self, event: &dyn DomainEvent) -> Result<()>;

    /// Subscribe to events matching the given subject pattern.
    ///
    /// Uses a default consumer group derived from the subject. Multiple
    /// subscribers within the same group compete for messages (each message
    /// is delivered to exactly one subscriber); subscribers in different
    /// groups each receive every matching message.
    async fn subscribe(&self, subject: &str, handler: EventHandler) -> Result<()> {
        self.subscribe_with_group(subject, &default_group(subject), handler)
            .await
    }

    /// Subscribe to events matching the given subject pattern as part of a
    /// named consumer group.
    ///
    /// All subscribers sharing a `group` (typically separate worker
    /// processes) form a competing-consumer queue: every event is delivered
    /// to exactly one of them. Distinct groups receive independent copies.
    async fn subscribe_with_group(
        &self,
        subject: &str,
        group: &str,
        handler: EventHandler,
    ) -> Result<()>;

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
    /// Maximum reconnection attempts.
    max_reconnect: usize,
}

impl NatsEventBus {
    /// Create a new [`NatsEventBus`] with the given stream name.
    pub fn new(stream_name: impl Into<String>) -> Self {
        Self {
            client: RwLock::new(None),
            jetstream: RwLock::new(None),
            stream_name: stream_name.into(),
            max_reconnect: 10,
        }
    }

    /// Create a new [`NatsEventBus`] from the application configuration.
    ///
    /// The stream name is taken from `config.cluster` and
    /// `config.max_reconnect` is applied to the NATS `ConnectOptions` in
    /// [`EventBus::connect`], so `AppConfig.event_bus` fully drives the
    /// connection behavior.
    pub fn from_config(config: &sensei_core::config::EventBusConfig) -> Self {
        Self {
            client: RwLock::new(None),
            jetstream: RwLock::new(None),
            stream_name: config.cluster.clone(),
            max_reconnect: config.max_reconnect,
        }
    }

    /// Configure the maximum number of reconnection attempts.
    pub fn with_max_reconnect(mut self, max_reconnect: usize) -> Self {
        self.max_reconnect = max_reconnect;
        self
    }

    /// Ensure the JetStream stream exists, creating it if necessary.
    async fn ensure_stream(&self, js: &jetstream::Context) -> Result<Stream> {
        let cfg = jetstream::stream::Config {
            name: self.stream_name.clone(),
            subjects: vec![format!("{SUBJECT_PREFIX}.>")],
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
        info!(url, max_reconnect = self.max_reconnect, "Connecting to NATS event bus");

        let connect_options = ConnectOptions::new().max_reconnects(self.max_reconnect);
        let client = async_nats::connect_with_options(url, connect_options)
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

        // The stream only captures `sensei.>` subjects; the `sensei.` prefix
        // is mandatory for events to be visible to the JetStream stream.
        let subject = format!("{SUBJECT_PREFIX}.{}", event.event_type());
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

        info!(event_type = event.event_type(), "Published event to NATS");
        Ok(())
    }

    async fn subscribe_with_group(
        &self,
        subject: &str,
        group: &str,
        handler: EventHandler,
    ) -> Result<()> {
        let subject = normalize_subject(subject);
        let js = self
            .jetstream
            .read()
            .await
            .as_ref()
            .ok_or(EventBusError::NotConnected)?
            .clone();

        let stream = self.ensure_stream(&js).await?;

        // The consumer name is derived from the consumer group: subscribers
        // sharing a group share the consumer (competing consumers, the
        // desired worker behavior), while distinct groups get independent
        // consumers and hence their own copy of each message.
        let consumer_name = format!("sensei-worker-{}", sanitize_group(group));
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

        let mut messages = consumer
            .messages()
            .await
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
                        // Poison message: log and ack so it is not redelivered
                        // forever.
                        error!(
                            error = %EventBusError::DeserializationFailed(e.to_string()),
                            "Failed to deserialize event; acking poison message"
                        );
                    }
                }
                // Acknowledge message
                if let Err(e) = msg.ack().await {
                    warn!("Failed to ack message: {e}");
                }
            }
        });

        info!(subject, group, "Subscribed to event subject");
        Ok(())
    }

    fn is_connected(&self) -> bool {
        self.client.try_read().map(|c| c.is_some()).unwrap_or(false)
    }

    async fn disconnect(&self) -> Result<()> {
        let mut client = self.client.write().await;
        let connected = client.is_some();
        client.take();
        info!(
            connected,
            "Disconnected from NATS event bus; pending publishes are flushed by dropping the JetStream client connection"
        );
        *self.jetstream.write().await = None;
        Ok(())
    }
}

/// In-memory event bus for testing and development.
///
/// Uses the same `sensei.` prefix semantics as [`NatsEventBus`]: published
/// subjects are `sensei.<event_type>` and subscriptions match with NATS
/// wildcards (`>` matches the remaining tokens, `*` matches exactly one).
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

        let subject = format!("{SUBJECT_PREFIX}.{}", event.event_type());

        let subscribers = self.subscribers.read().await;
        for (pattern, handler) in subscribers.iter() {
            if subject_matches(pattern, &subject) {
                if let Err(e) = handler(envelope.clone()) {
                    warn!("In-memory handler error: {e}");
                }
            }
        }

        Ok(())
    }

    async fn subscribe_with_group(
        &self,
        subject: &str,
        _group: &str,
        handler: EventHandler,
    ) -> Result<()> {
        let subject = normalize_subject(subject);
        let mut subscribers = self.subscribers.write().await;
        subscribers.push((subject, handler));
        Ok(())
    }

    fn is_connected(&self) -> bool {
        // The in-memory bus is connected from the moment it is created.
        true
    }

    async fn disconnect(&self) -> Result<()> {
        self.subscribers.write().await.clear();
        Ok(())
    }
}

/// Derive the default consumer group name from a subscription subject.
fn default_group(subject: &str) -> String {
    sanitize_group(subject)
}

/// Sanitize a consumer group name for use in a NATS consumer name.
fn sanitize_group(group: &str) -> String {
    group
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '-'
            }
        })
        .collect()
}

/// Normalize a subject to the `sensei.` prefix.
fn normalize_subject(subject: &str) -> String {
    let subject = subject.trim();
    if subject.starts_with(SUBJECT_PREFIX) {
        subject.to_string()
    } else {
        format!("{SUBJECT_PREFIX}.{subject}")
    }
}

/// Match a NATS-style subscription pattern against a subject.
///
/// - `>` matches the remaining tokens (and the empty remainder).
/// - `*` matches exactly one token.
/// - Any other token must match exactly.
fn subject_matches(pattern: &str, subject: &str) -> bool {
    let pattern_tokens: Vec<&str> = pattern.split('.').collect();
    let subject_tokens: Vec<&str> = subject.split('.').collect();

    let mut idx = 0;
    for token in &pattern_tokens {
        if *token == ">" {
            return true;
        }
        let Some(subject_token) = subject_tokens.get(idx) else {
            return false;
        };
        if *token != "*" && *token != *subject_token {
            return false;
        }
        idx += 1;
    }
    idx == subject_tokens.len()
}

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_core::domain::events::NcrCreatedEvent;
    use uuid::Uuid;

    #[test]
    fn normalize_subject_prefixes_when_missing() {
        assert_eq!(normalize_subject("quality.ncr.created"), "sensei.quality.ncr.created");
        assert_eq!(normalize_subject("sensei.>"), "sensei.>");
        assert_eq!(normalize_subject("sensei.quality.>"), "sensei.quality.>");
        assert_eq!(normalize_subject(">"), "sensei.>");
    }

    #[test]
    fn subject_matching_supports_wildcards() {
        assert!(subject_matches("sensei.>", "sensei.quality.ncr.created"));
        assert!(subject_matches("sensei.quality.>", "sensei.quality.ncr.created"));
        assert!(!subject_matches("sensei.production.>", "sensei.quality.ncr.created"));
        assert!(subject_matches("sensei.quality.*", "sensei.quality.ncr"));
        assert!(!subject_matches("sensei.quality.*", "sensei.quality.ncr.created"));
        assert!(subject_matches("sensei.quality.ncr.created", "sensei.quality.ncr.created"));
        assert!(!subject_matches("sensei.quality.ncr.updated", "sensei.quality.ncr.created"));
    }

    fn ncr_event() -> NcrCreatedEvent {
        NcrCreatedEvent::new(
            Uuid::new_v4(),
            Uuid::new_v4(),
            "NCR-001".to_string(),
            "Test NCR".to_string(),
            "minor".to_string(),
            Uuid::new_v4(),
        )
    }

    #[tokio::test]
    async fn in_memory_publish_uses_sensei_prefix() {
        let bus = InMemoryEventBus::new();
        let received = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
        let received_clone = std::sync::Arc::clone(&received);

        bus.subscribe(
            "sensei.>",
            Arc::new(move |envelope| {
                received_clone.lock().unwrap().push(envelope.event_type.clone());
                Ok(())
            }),
        )
        .await
        .unwrap();

        bus.publish(&ncr_event()).await.unwrap();

        assert_eq!(*received.lock().unwrap(), vec!["quality.ncr.created".to_string()]);
    }

    #[tokio::test]
    async fn in_memory_prefix_subscription_matches() {
        let bus = InMemoryEventBus::new();
        let received = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
        let received_clone = std::sync::Arc::clone(&received);

        // Subscribe WITHOUT the prefix; it must be normalized to sensei.>
        bus.subscribe(
            ">",
            Arc::new(move |envelope| {
                received_clone.lock().unwrap().push(envelope.event_type.clone());
                Ok(())
            }),
        )
        .await
        .unwrap();

        bus.publish(&ncr_event()).await.unwrap();
        assert_eq!(*received.lock().unwrap(), vec!["quality.ncr.created".to_string()]);
    }

    #[tokio::test]
    async fn in_memory_subscription_filtering() {
        let bus = InMemoryEventBus::new();
        let received = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
        let received_clone = std::sync::Arc::clone(&received);

        bus.subscribe(
            "sensei.production.>",
            Arc::new(move |envelope| {
                received_clone.lock().unwrap().push(envelope.event_type.clone());
                Ok(())
            }),
        )
        .await
        .unwrap();

        bus.publish(&ncr_event()).await.unwrap();
        assert!(received.lock().unwrap().is_empty());
    }

    #[tokio::test]
    async fn in_memory_is_connected_after_creation() {
        let bus = InMemoryEventBus::new();
        assert!(bus.is_connected());
    }

    #[test]
    fn default_group_is_subject_derived() {
        // The trailing `>` token sanitizes to `-` (it is not a legal
        // consumer-name character); the original expectation omitted it.
        assert_eq!(default_group("sensei.quality.>"), "sensei-quality--");
        assert_eq!(default_group("sensei.quality.ncr.created"), "sensei-quality-ncr-created");
    }

    #[test]
    fn sanitize_group_removes_illegal_characters() {
        assert_eq!(sanitize_group("my group:workers"), "my-group-workers");
        assert_eq!(sanitize_group("notifications"), "notifications");
    }
}

//! Server-Sent Events (SSE) manager.
//!
//! Provides one-way server-to-client event broadcasting using named channels.
//! Clients subscribe to channels and receive `event: {event}\ndata: {data}\n\n`
//! formatted messages.

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use tokio::sync::{broadcast, RwLock};
use tracing::debug;

/// Capacity of the broadcast channel for each SSE channel.
const CHANNEL_CAPACITY: usize = 256;

/// Manages Server-Sent Events channels and subscribers.
///
/// Each named channel is backed by a [`broadcast::Sender`]. Publishers send
/// events to a channel and all subscribed clients receive them.
#[derive(Clone)]
pub struct SseManager {
    /// Per-channel broadcast senders keyed by channel name.
    clients: Arc<RwLock<HashMap<String, broadcast::Sender<String>>>>,
    /// Total number of publishes dropped because every subscriber lagged or
    /// disconnected (slow clients). Logged at debug level.
    dropped_publishes: Arc<AtomicU64>,
    /// Optional event bus for cross-replica fanout (core NATS).
    event_bus: Arc<RwLock<Option<Arc<dyn sensei_event_bus::EventBus>>>>,
    /// Stable identity of this process (origin marker in envelopes).
    instance_id: String,
}

impl SseManager {
    /// Create an empty SSE manager with no channels.
    pub fn new() -> Self {
        Self {
            clients: Arc::new(RwLock::new(HashMap::new())),
            dropped_publishes: Arc::new(AtomicU64::new(0)),
            event_bus: Arc::new(RwLock::new(None)),
            instance_id: uuid::Uuid::new_v4().to_string(),
        }
    }

    /// Attach the event bus: SSE publishes fan out to EVERY replica, and
    /// this replica delivers envelopes from other replicas to its local
    /// subscribers (per-instance group — every replica receives).
    pub fn set_event_bus(&self, bus: Arc<dyn sensei_event_bus::EventBus>) {
        if let Ok(mut guard) = self.event_bus.try_write() {
            *guard = Some(bus.clone());
        }
        let manager = self.clone();
        let group = self.instance_id.clone();
        let group_for_handler = group.clone();
        let handler: sensei_event_bus::bus::CoreHandler = Arc::new(move |payload: Vec<u8>| {
            let manager = manager.clone();
            let self_id = uuid::Uuid::parse_str(&group_for_handler).unwrap_or_default();
            tokio::spawn(async move {
                let envelope: super::realtime::RealtimeEnvelope =
                    match serde_json::from_slice(&payload) {
                        Ok(v) => v,
                        Err(_) => return,
                    };
                if envelope.event_type != "sse.emit" {
                    return;
                }
                if envelope.origin_instance == self_id {
                    return;
                }
                let channel = envelope
                    .payload
                    .get("channel")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string();
                let event = envelope
                    .payload
                    .get("event")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string();
                let data = envelope
                    .payload
                    .get("data")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_string();
                manager.publish_local(&channel, &event, &data).await;
            });
            Ok(())
        });
        tokio::spawn(async move {
            let _ = bus
                .subscribe_core(super::realtime::REALTIME_TOPIC, &group, handler)
                .await;
        });
    }

    /// Number of publishes dropped due to lagging/disconnected subscribers
    /// (diagnostics).
    pub fn dropped_publish_count(&self) -> u64 {
        self.dropped_publishes.load(Ordering::Relaxed)
    }

    /// Subscribe to a named channel.
    ///
    /// If the channel does not exist, it is created. Returns a
    /// [`broadcast::Receiver`] that yields SSE-formatted messages.
    pub async fn subscribe(&self, channel: &str) -> broadcast::Receiver<String> {
        let mut clients = self.clients.write().await;
        let tx = clients
            .entry(channel.to_string())
            .or_insert_with(|| {
                let (tx, _) = broadcast::channel(CHANNEL_CAPACITY);
                tx
            })
            .clone();
        tx.subscribe()
    }

    /// Unsubscribe from a named channel by dropping the receiver.
    ///
    /// When the last subscriber drops, the channel is cleaned up.
    pub async fn unsubscribe(&self, channel: &str, _rx: broadcast::Receiver<String>) {
        let clients = self.clients.read().await;
        if let Some(tx) = clients.get(channel) {
            if tx.receiver_count() == 1 {
                drop(clients);
                let mut clients = self.clients.write().await;
                if let Some(tx) = clients.get(channel) {
                    if tx.receiver_count() <= 1 {
                        clients.remove(channel);
                    }
                }
            }
        }
    }

    /// Publish an SSE event to a channel.
    ///
    /// The message is formatted as:
    /// ```text
    /// event: {event}
    /// data: {data}
    ///
    /// ```
    /// Drops (all subscribers lagging or disconnected) are counted and
    /// logged at debug level so a slow client never blocks publishing.
    /// Local-only delivery (used by the fanout handler and direct calls).
    pub async fn publish_local(&self, channel: &str, event: &str, data: &str) {
        let clients = self.clients.read().await;
        if let Some(tx) = clients.get(channel) {
            let message = format!("event: {event}\ndata: {data}\n\n");
            match tx.send(message) {
                Ok(0) => {
                    self.dropped_publishes.fetch_add(1, Ordering::Relaxed);
                    debug!(channel, "SSE publish sent to 0 subscribers (empty channel)");
                }
                Ok(_) => {}
                Err(e) => {
                    self.dropped_publishes.fetch_add(1, Ordering::Relaxed);
                    debug!(
                        channel,
                        dropped_total = self.dropped_publish_count(),
                        "SSE publish dropped: {e}"
                    );
                }
            }
        }
    }

    /// Publish locally AND fan out to every replica (one realtime topic).
    pub async fn publish(&self, channel: &str, event: &str, data: &str) {
        self.publish_local(channel, event, data).await;
        let bus = self.event_bus.read().await.clone();
        let Some(bus) = bus else { return };
        let origin = uuid::Uuid::parse_str(&self.instance_id).unwrap_or_default();
        let envelope = super::realtime::RealtimeEnvelope {
            id: uuid::Uuid::new_v4(),
            tenant_id: uuid::Uuid::nil(),
            origin_instance: origin,
            target: super::realtime::RealtimeTarget::Tenant,
            event_type: "sse.emit".to_string(),
            payload: serde_json::json!({
                "channel": channel,
                "event": event,
                "data": data,
            }),
        };
        super::realtime::publish_realtime(bus.as_ref(), &envelope).await;
    }
}

impl Default for SseManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_subscribe_and_publish() {
        let manager = SseManager::new();
        let mut rx = manager.subscribe("test-channel").await;

        manager.publish("test-channel", "update", "hello").await;

        let msg = rx.recv().await.unwrap();
        assert_eq!(msg, "event: update\ndata: hello\n\n");
    }

    #[tokio::test]
    async fn test_publish_to_nonexistent_channel() {
        let manager = SseManager::new();
        // Should not panic
        manager.publish("nonexistent", "event", "data").await;
    }

    #[tokio::test]
    async fn test_unsubscribe_cleanup() {
        let manager = SseManager::new();
        let rx = manager.subscribe("cleanup-ch").await;

        {
            let clients = manager.clients.read().await;
            assert!(clients.contains_key("cleanup-ch"));
        }

        manager.unsubscribe("cleanup-ch", rx).await;

        {
            let clients = manager.clients.read().await;
            assert!(!clients.contains_key("cleanup-ch"));
        }
    }

    #[tokio::test]
    async fn test_multiple_subscribers() {
        let manager = SseManager::new();
        let mut rx1 = manager.subscribe("multi").await;
        let mut rx2 = manager.subscribe("multi").await;

        manager.publish("multi", "msg", "broadcast").await;

        let msg1 = rx1.recv().await.unwrap();
        let msg2 = rx2.recv().await.unwrap();
        assert_eq!(msg1, msg2);
    }
}

//! Server-Sent Events (SSE) manager.
//!
//! Provides one-way server-to-client event broadcasting using named channels.
//! Clients subscribe to channels and receive `event: {event}\ndata: {data}\n\n`
//! formatted messages.

use std::collections::HashMap;
use std::sync::Arc;

use tokio::sync::{broadcast, RwLock};

/// Capacity of the broadcast channel for each SSE channel.
const CHANNEL_CAPACITY: usize = 256;

/// Manages Server-Sent Events channels and subscribers.
///
/// Each named channel is backed by a [`broadcast::Sender`]. Publishers send
/// events to a channel and all subscribed clients receive them.
#[derive(Debug, Clone)]
pub struct SseManager {
    /// Per-channel broadcast senders keyed by channel name.
    clients: Arc<RwLock<HashMap<String, broadcast::Sender<String>>>>,
}

impl SseManager {
    /// Create an empty SSE manager with no channels.
    pub fn new() -> Self {
        Self {
            clients: Arc::new(RwLock::new(HashMap::new())),
        }
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
    pub async fn publish(&self, channel: &str, event: &str, data: &str) {
        let clients = self.clients.read().await;
        if let Some(tx) = clients.get(channel) {
            let message = format!("event: {event}\ndata: {data}\n\n");
            let _ = tx.send(message);
        }
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

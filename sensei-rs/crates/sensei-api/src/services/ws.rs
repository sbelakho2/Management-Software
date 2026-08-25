//! WebSocket connection manager with room-based pub/sub.
//!
//! Manages connected WebSocket clients using a room-based publish/subscribe
//! pattern. Each room has a [`broadcast::Sender`] that fans out messages to
//! all subscribers. Individual user connections are also tracked so targeted
//! messages can be sent to specific users.
//!
//! # Room naming convention
//! - `"tenant:{tenant_id}"` — all users in a tenant
//! - `"entity:{entity_type}:{entity_id}"` — watchers of a specific entity
//! - `"user:{user_id}"` — direct messages to a user

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use tokio::sync::{broadcast, RwLock};
use tracing::debug;
use uuid::Uuid;

/// Capacity of the broadcast channel for each room / connection.
const CHANNEL_CAPACITY: usize = 256;

/// Manages WebSocket connections and room-based message broadcasting.
#[derive(Debug, Clone)]
pub struct WebSocketManager {
    /// Per-room broadcast senders keyed by room name.
    rooms: Arc<RwLock<HashMap<String, broadcast::Sender<String>>>>,
    /// Per-user broadcast senders for direct messaging.
    connections: Arc<RwLock<HashMap<Uuid, broadcast::Sender<String>>>>,
    /// Total number of broadcast sends dropped because every receiver
    /// lagged or disconnected (slow clients). Logged at debug level so the
    /// fire-and-forget pub/sub never disrupts fast clients.
    dropped_sends: Arc<AtomicU64>,
}

impl WebSocketManager {
    /// Create an empty manager with no rooms or connections.
    pub fn new() -> Self {
        Self {
            rooms: Arc::new(RwLock::new(HashMap::new())),
            connections: Arc::new(RwLock::new(HashMap::new())),
            dropped_sends: Arc::new(AtomicU64::new(0)),
        }
    }

    /// Number of broadcast sends dropped due to lagging/disconnected
    /// receivers (diagnostics).
    pub fn dropped_send_count(&self) -> u64 {
        self.dropped_sends.load(Ordering::Relaxed)
    }

    /// Join (or create) a room and return a receiver for its messages.
    ///
    /// If the room does not exist yet, a new broadcast channel is created.
    /// The returned [`broadcast::Receiver`] will receive all messages sent
    /// to the room until the receiver is dropped or [`leave_room`](Self::leave_room)
    /// is called.
    pub async fn join_room(&self, room: &str) -> broadcast::Receiver<String> {
        let mut rooms = self.rooms.write().await;
        let tx = rooms
            .entry(room.to_string())
            .or_insert_with(|| {
                let (tx, _) = broadcast::channel(CHANNEL_CAPACITY);
                tx
            })
            .clone();
        tx.subscribe()
    }

    /// Leave a room by dropping the receiver.
    ///
    /// When the last receiver for a room is dropped, the broadcast sender
    /// will have zero receivers, but the room entry remains in the map.
    /// The room will be cleaned up lazily on the next [`join_room`](Self::join_room)
    /// or explicitly cleaned on broadcast with no subscribers.
    pub async fn leave_room(&self, room: &str, _rx: broadcast::Receiver<String>) {
        let rooms = self.rooms.read().await;
        if let Some(tx) = rooms.get(room) {
            // If this was the last receiver, remove the room entry to avoid
            // accumulating empty rooms.
            if tx.receiver_count() == 1 {
                drop(rooms);
                let mut rooms = self.rooms.write().await;
                // Check again under write lock to avoid race.
                if let Some(tx) = rooms.get(room) {
                    if tx.receiver_count() <= 1 {
                        rooms.remove(room);
                    }
                }
            }
        }
    }

    /// Broadcast a message to all subscribers in a room.
    ///
    /// Errors (e.g., no receivers or all receivers lagging) are silently
    /// ignored so a single slow client does not disrupt the room; drops are
    /// counted and logged at debug level.
    pub async fn broadcast_to_room(&self, room: &str, message: &str) {
        let rooms = self.rooms.read().await;
        if let Some(tx) = rooms.get(room) {
            match tx.send(message.to_string()) {
                Ok(receiver_count) => {
                    if receiver_count == 0 {
                        self.dropped_sends.fetch_add(1, Ordering::Relaxed);
                        debug!(room, "WS broadcast sent to 0 receivers (empty room)");
                    }
                }
                Err(e) => {
                    self.dropped_sends.fetch_add(1, Ordering::Relaxed);
                    debug!(room, dropped_total = self.dropped_send_count(), "WS broadcast dropped: {e}");
                }
            }
        }
    }

    /// Send a message directly to a specific user's connection.
    ///
    /// Returns `true` if the user was connected and the message was sent.
    pub async fn send_to_user(&self, user_id: Uuid, message: &str) -> bool {
        let connections = self.connections.read().await;
        if let Some(tx) = connections.get(&user_id) {
            match tx.send(message.to_string()) {
                Ok(_) => true,
                Err(e) => {
                    self.dropped_sends.fetch_add(1, Ordering::Relaxed);
                    debug!(user_id = %user_id, dropped_total = self.dropped_send_count(), "WS user message dropped: {e}");
                    false
                }
            }
        } else {
            false
        }
    }

    /// Register a new user connection and return a receiver for inbound
    /// messages targeted at that user.
    ///
    /// If the user already has an existing connection, it is replaced.
    pub async fn register_connection(&self, user_id: Uuid) -> broadcast::Receiver<String> {
        let (tx, rx) = broadcast::channel(CHANNEL_CAPACITY);
        let mut connections = self.connections.write().await;
        connections.insert(user_id, tx);
        rx
    }

    /// Unregister a user connection.
    ///
    /// No-op if the user is not connected.
    pub async fn unregister_connection(&self, user_id: Uuid) {
        let mut connections = self.connections.write().await;
        connections.remove(&user_id);
    }
}

impl Default for WebSocketManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_join_and_broadcast() {
        let manager = WebSocketManager::new();
        let mut rx = manager.join_room("test-room").await;

        manager.broadcast_to_room("test-room", "hello").await;
        let msg = rx.recv().await.unwrap();
        assert_eq!(msg, "hello");
    }

    #[tokio::test]
    async fn test_register_and_send_to_user() {
        let manager = WebSocketManager::new();
        let user_id = Uuid::new_v4();
        let mut rx = manager.register_connection(user_id).await;

        let sent = manager.send_to_user(user_id, "private").await;
        assert!(sent);

        let msg = rx.recv().await.unwrap();
        assert_eq!(msg, "private");
    }

    #[tokio::test]
    async fn test_unregister_connection() {
        let manager = WebSocketManager::new();
        let user_id = Uuid::new_v4();
        let _rx = manager.register_connection(user_id).await;

        manager.unregister_connection(user_id).await;
        let sent = manager.send_to_user(user_id, "gone").await;
        assert!(!sent);
    }

    #[tokio::test]
    async fn test_leave_room_cleanup() {
        let manager = WebSocketManager::new();
        let rx = manager.join_room("cleanup-test").await;

        // We should have a room
        {
            let rooms = manager.rooms.read().await;
            assert!(rooms.contains_key("cleanup-test"));
        }

        manager.leave_room("cleanup-test", rx).await;

        // Room should be cleaned up
        {
            let rooms = manager.rooms.read().await;
            assert!(!rooms.contains_key("cleanup-test"));
        }
    }

    #[tokio::test]
    async fn test_broadcast_to_nonexistent_room() {
        let manager = WebSocketManager::new();
        // Should not panic
        manager.broadcast_to_room("nonexistent", "data").await;
    }

    #[tokio::test]
    async fn test_send_to_nonexistent_user() {
        let manager = WebSocketManager::new();
        let sent = manager.send_to_user(Uuid::new_v4(), "data").await;
        assert!(!sent);
    }
}

//! WebSocket connection manager with room-based pub/sub.
//!
//! Manages connected WebSocket clients using a room-based publish/subscribe
//! pattern. Each room has a [`broadcast::Sender`] that fans out messages to
//! all subscribers. Individual user connections are tracked per
//! [`ConnectionId`] so targeted messages reach **every** live connection of
//! a user (two browser tabs of the same user are independent: closing one
//! never removes the other).
//!
//! # Room naming convention
//! - `"tenant:{tenant_id}"` — all users in a tenant
//! - `"entity:{entity_type}:{entity_id}"` — watchers of a specific entity
//! - `"user:{user_id}"` — direct messages to a user
//!
//! # Cross-replica fanout
//!
//! Local delivery is always performed by the manager itself. In addition,
//! every user/room broadcast is **also** published on the event bus
//! (NATS) so other replicas can forward it to their locally-connected
//! sockets. Each manager subscribes to its own per-replica consumer group
//! (`subscribe_with_group`) so every replica receives a copy. Published
//! envelopes carry the publisher's `instance_id`; a replica skips its own
//! publishes (the in-memory bus delivers synchronously, making the fanout
//! a no-op passthrough in development) and forwards foreign ones only to
//! its local sockets — it never re-publishes, so messages cannot loop.
//!
//! The bus subject is `sensei.ws.user` / `sensei.ws.room` (the event bus
//! derives the subject from the static event type); the specific user id /
//! room name travels inside the envelope payload.

use std::any::Any;
use std::collections::{HashMap, HashSet};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;

use sensei_core::domain::events::DomainEvent;
use sensei_core::types::{CorrelationId, EventId, Timestamp};
use sensei_event_bus::types::EventEnvelope;
use sensei_event_bus::{EventBus, EventHandler};
use tokio::sync::{broadcast, RwLock};
use tracing::debug;
use uuid::Uuid;

/// Capacity of the broadcast channel for each room / connection.
const CHANNEL_CAPACITY: usize = 256;

/// A unique identifier for one live WebSocket connection.
pub type ConnectionId = u64;

/// A single live connection: who it belongs to and the channel its send
/// task polls.
#[derive(Debug, Clone)]
struct Connection {
    user_id: Uuid,
    tenant_id: Uuid,
    tx: broadcast::Sender<String>,
}

/// Handle returned by [`WebSocketManager::connect`].
#[derive(Debug)]
pub struct ConnectionHandle {
    /// Identifier that must be passed back to [`WebSocketManager::disconnect`].
    pub connection_id: ConnectionId,
    /// Receiver for messages directed at this user (and, transitively, at
    /// this connection).
    pub rx: broadcast::Receiver<String>,
}

/// What a fanout envelope targets.
#[derive(Debug)]
enum WsFanoutKind {
    /// A direct message for one user (all their connections).
    User(Uuid),
    /// A message for a room.
    Room(String),
}

/// Event published on the bus to fan out a WS message across replicas.
#[derive(Debug)]
struct WsFanoutEvent {
    kind: WsFanoutKind,
    message: String,
    origin: String,
}

impl DomainEvent for WsFanoutEvent {
    fn event_id(&self) -> EventId {
        EventId::new_v4()
    }

    fn event_type(&self) -> &'static str {
        match self.kind {
            WsFanoutKind::User(_) => "ws.user",
            WsFanoutKind::Room(_) => "ws.room",
        }
    }

    fn correlation_id(&self) -> CorrelationId {
        CorrelationId::new_v4()
    }

    fn tenant_id(&self) -> Uuid {
        // The tenant is carried inside the payload where known; the bus
        // envelope tenant is not meaningful for transport fanout.
        Uuid::nil()
    }

    fn occurred_at(&self) -> Timestamp {
        chrono::Utc::now()
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        match &self.kind {
            WsFanoutKind::User(user_id) => Ok(serde_json::json!({
                "origin": self.origin,
                "message": self.message,
                "target_user": user_id.to_string(),
            })),
            WsFanoutKind::Room(room) => Ok(serde_json::json!({
                "origin": self.origin,
                "message": self.message,
                "target_room": room,
            })),
        }
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Manages WebSocket connections and room-based message broadcasting.
pub struct WebSocketManager {
    /// Per-room broadcast senders keyed by room name.
    rooms: Arc<RwLock<HashMap<String, broadcast::Sender<String>>>>,
    /// Live connections keyed by connection id.
    connections: Arc<RwLock<HashMap<ConnectionId, Connection>>>,
    /// User id → set of live connection ids.
    user_index: Arc<RwLock<HashMap<Uuid, HashSet<ConnectionId>>>>,
    /// Total number of broadcast sends dropped because every receiver
    /// lagged or disconnected (slow clients). Logged at debug level so the
    /// fire-and-forget pub/sub never disrupts fast clients.
    dropped_sends: Arc<AtomicU64>,
    /// Monotonic connection-id allocator (shared across clones).
    next_connection_id: Arc<AtomicU64>,
    /// The event bus used for cross-replica fanout (in-memory in dev).
    /// `std::sync::RwLock` because [`set_event_bus`](Self::set_event_bus)
    /// is synchronous and may be called from an async context; the outer
    /// `Arc` keeps every clone of the manager on the same bus.
    event_bus: Arc<std::sync::RwLock<Option<Arc<dyn EventBus>>>>,
    /// Per-replica consumer group (unique per manager instance) so every
    /// replica receives every fanout envelope.
    instance_id: Arc<String>,
    /// Whether the bus subscriptions are registered (shared across clones).
    bus_attached: Arc<AtomicBool>,
}

impl std::fmt::Debug for WebSocketManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("WebSocketManager")
            .field("rooms", &self.rooms)
            .field("connections", &self.connections)
            .field("user_index", &self.user_index)
            .field("dropped_sends", &self.dropped_sends)
            .finish()
    }
}

impl WebSocketManager {
    /// Create an empty manager with no rooms or connections.
    ///
    /// Attaches an in-memory bus (dev fallback) so fanout publishes are
    /// always safe; swap it with [`set_event_bus`](Self::set_event_bus)
    /// when a real bus is available.
    pub fn new() -> Self {
        Self::with_event_bus(Arc::new(sensei_event_bus::InMemoryEventBus::new()))
    }

    /// Create a manager that fans out through the given event bus.
    pub fn with_event_bus(event_bus: Arc<dyn EventBus>) -> Self {
        Self {
            rooms: Arc::new(RwLock::new(HashMap::new())),
            connections: Arc::new(RwLock::new(HashMap::new())),
            user_index: Arc::new(RwLock::new(HashMap::new())),
            dropped_sends: Arc::new(AtomicU64::new(0)),
            next_connection_id: Arc::new(AtomicU64::new(1)),
            event_bus: Arc::new(std::sync::RwLock::new(Some(event_bus))),
            instance_id: Arc::new(Uuid::new_v4().to_string()),
            bus_attached: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Swap the event bus used for cross-replica fanout.
    ///
    /// Subscriptions are registered lazily on the next broadcast (the bus
    /// may not be connected yet at attach time), so this is cheap and safe
    /// to call before the server starts serving.
    pub fn set_event_bus(&self, event_bus: Arc<dyn EventBus>) {
        self.bus_attached.store(false, Ordering::SeqCst);
        *self.event_bus.write().expect("event bus lock poisoned") = Some(event_bus);
    }

    /// Number of broadcast sends dropped due to lagging/disconnected
    /// receivers (diagnostics).
    pub fn dropped_send_count(&self) -> u64 {
        self.dropped_sends.load(Ordering::Relaxed)
    }

    /// Register a new live connection and return its handle.
    ///
    /// The connection is added to the user's connection set; later
    /// [`send_to_user`](Self::send_to_user) calls deliver to **all** of the
    /// user's connections. Use [`disconnect`](Self::disconnect) with the
    /// returned `connection_id` to remove exactly this connection.
    pub async fn connect(&self, user_id: Uuid, tenant_id: Uuid) -> ConnectionHandle {
        let (tx, rx) = broadcast::channel(CHANNEL_CAPACITY);
        let connection_id = self.next_connection_id.fetch_add(1, Ordering::SeqCst);

        let mut connections = self.connections.write().await;
        let mut user_index = self.user_index.write().await;
        connections.insert(
            connection_id,
            Connection {
                user_id,
                tenant_id,
                tx,
            },
        );
        user_index.entry(user_id).or_default().insert(connection_id);

        ConnectionHandle { connection_id, rx }
    }

    /// Remove exactly one connection, updating the user index.
    ///
    /// Other connections of the same user are untouched.
    pub async fn disconnect(&self, connection_id: ConnectionId) {
        let mut connections = self.connections.write().await;
        if let Some(connection) = connections.remove(&connection_id) {
            let mut user_index = self.user_index.write().await;
            if let Some(ids) = user_index.get_mut(&connection.user_id) {
                ids.remove(&connection_id);
                if ids.is_empty() {
                    user_index.remove(&connection.user_id);
                }
            }
        }
    }

    /// Number of live connections for a user (diagnostics / tests).
    pub async fn connection_count_for_user(&self, user_id: Uuid) -> usize {
        self.user_index
            .read()
            .await
            .get(&user_id)
            .map(|ids| ids.len())
            .unwrap_or(0)
    }

    /// Join (or create) a room and return a receiver for its messages.
    ///
    /// If the room does not exist yet, a new broadcast channel is created.
    /// The returned [`broadcast::Receiver`] will receive all messages sent
    /// to the room until the receiver is dropped or
    /// [`leave_room`](Self::leave_room) is called.
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

    /// Leave a room.
    ///
    /// When the last receiver for a room is dropped, the broadcast sender
    /// has zero receivers and the room entry is removed.
    pub async fn leave_room(&self, room: &str) {
        let rooms = self.rooms.read().await;
        if let Some(tx) = rooms.get(room) {
            if tx.receiver_count() == 0 {
                drop(rooms);
                let mut rooms = self.rooms.write().await;
                // Re-check under the write lock to avoid a race with a
                // concurrent join.
                if let Some(tx) = rooms.get(room) {
                    if tx.receiver_count() == 0 {
                        rooms.remove(room);
                    }
                }
            }
        }
    }

    /// Broadcast a message to all subscribers in a room, locally and on the
    /// event bus (cross-replica).
    ///
    /// Errors (e.g., no receivers or all receivers lagging) are silently
    /// ignored so a single slow client does not disrupt the room; drops are
    /// counted and logged at debug level.
    pub async fn broadcast_to_room(&self, room: &str, message: &str) {
        self.ensure_bus_subscribed().await;

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
                    debug!(
                        room,
                        dropped_total = self.dropped_send_count(),
                        "WS broadcast dropped: {e}"
                    );
                }
            }
        }

        self.publish_fanout(WsFanoutKind::Room(room.to_string()), message)
            .await;
    }

    /// Send a message directly to **all** of a user's live connections.
    ///
    /// Also publishes on the event bus so other replicas deliver to their
    /// locally-connected sockets for the same user. Returns `true` if the
    /// user had at least one live connection.
    pub async fn send_to_user(&self, user_id: Uuid, message: &str) -> bool {
        self.ensure_bus_subscribed().await;

        let mut delivered = false;
        let user_index = self.user_index.read().await;
        if let Some(ids) = user_index.get(&user_id) {
            let connections = self.connections.read().await;
            for connection_id in ids {
                if let Some(connection) = connections.get(connection_id) {
                    match connection.tx.send(message.to_string()) {
                        Ok(_) => delivered = true,
                        Err(e) => {
                            self.dropped_sends.fetch_add(1, Ordering::Relaxed);
                            debug!(
                                user_id = %user_id,
                                tenant_id = %connection.tenant_id,
                                connection_id,
                                dropped_total = self.dropped_send_count(),
                                "WS user message dropped: {e}"
                            );
                        }
                    }
                }
            }
        }

        self.publish_fanout(WsFanoutKind::User(user_id), message)
            .await;
        delivered
    }

    /// Local-only room delivery used by the bus fanout handler (foreign
    /// replicas must never re-publish, otherwise messages would loop).
    async fn deliver_to_room_local(&self, room: &str, message: &str) {
        let rooms = self.rooms.read().await;
        if let Some(tx) = rooms.get(room) {
            let _ = tx.send(message.to_string());
        }
    }

    /// Local-only user delivery used by the bus fanout handler.
    async fn deliver_to_user_local(&self, user_id: Uuid, message: &str) {
        let user_index = self.user_index.read().await;
        if let Some(ids) = user_index.get(&user_id) {
            let connections = self.connections.read().await;
            for connection_id in ids {
                if let Some(connection) = connections.get(connection_id) {
                    let _ = connection.tx.send(message.to_string());
                }
            }
        }
    }

    /// Register the per-replica bus subscriptions once.
    ///
    /// Subscribed subjects are `ws.user` and `ws.room` (normalized by the
    /// bus to `sensei.ws.user` / `sensei.ws.room`). Each manager instance
    /// uses its own consumer group so every replica receives every message.
    /// Subscribe the realtime fanout EARLY during server startup and keep
    /// it alive: a replica must receive cross-replica broadcasts even before
    /// it has ever broadcast anything itself (a missed subscription window
    /// would silently drop events for its local clients).
    ///
    /// The loop is SUPERVISED: on any subscription error it backs off
    /// exponentially and re-subscribes — a transient NATS issue can never
    /// permanently turn realtime off.
    pub async fn start_fanout_subscription(&self) {
        let mut delay = Duration::from_secs(1);
        loop {
            let Some(bus) = self
                .event_bus
                .read()
                .expect("event bus lock poisoned")
                .clone()
            else {
                tokio::time::sleep(Duration::from_secs(1)).await;
                continue;
            };

            let group = (*self.instance_id).clone();
            let handler = self.make_fanout_handler();
            let user_ok = bus
                .subscribe_with_group("ws.user", &group, handler.clone())
                .await;
            let room_ok = bus.subscribe_with_group("ws.room", &group, handler).await;

            if user_ok.is_ok() && room_ok.is_ok() {
                self.bus_attached.store(true, Ordering::SeqCst);
                tracing::info!(group = %group, "Realtime fanout subscriptions active");
                return;
            }
            tracing::warn!(
                error = %user_ok.err().or(room_ok.err()).map(|e| e.to_string()).unwrap_or_default(),
                retry_in_ms = delay.as_millis(),
                "Realtime fanout subscription failed — retrying"
            );
            tokio::time::sleep(delay).await;
            delay = (delay * 2).min(Duration::from_secs(60));
        }
    }

    async fn ensure_bus_subscribed(&self) {
        if self.bus_attached.load(Ordering::SeqCst) {
            return;
        }
        // Safety net for tests that never called start_fanout_subscription:
        // one best-effort attempt; the eager startup path is authoritative.
        let Some(bus) = self
            .event_bus
            .read()
            .expect("event bus lock poisoned")
            .clone()
        else {
            return;
        };

        let group = (*self.instance_id).clone();
        let handler = self.make_fanout_handler();
        let subscribed = bus
            .subscribe_with_group("ws.user", &group, handler.clone())
            .await
            .is_ok()
            && bus
                .subscribe_with_group("ws.room", &group, handler)
                .await
                .is_ok();

        if subscribed {
            self.bus_attached.store(true, Ordering::SeqCst);
        } else {
            debug!("WS fanout subscriptions not registered yet; will retry on next broadcast");
        }
    }

    /// Publish a fanout envelope on the bus (if one is attached).
    async fn publish_fanout(&self, kind: WsFanoutKind, message: &str) {
        let Some(bus) = self
            .event_bus
            .read()
            .expect("event bus lock poisoned")
            .clone()
        else {
            return;
        };
        let event = WsFanoutEvent {
            kind,
            message: message.to_string(),
            origin: (*self.instance_id).clone(),
        };
        if let Err(e) = bus.publish(&event).await {
            debug!(error = %e, "Failed to publish WS fanout event");
        }
    }

    /// Build the handler that forwards foreign-replica fanout envelopes to
    /// this replica's local sockets.
    fn make_fanout_handler(&self) -> EventHandler {
        let manager = self.clone();
        let instance_id = (*self.instance_id).clone();
        Arc::new(move |envelope: EventEnvelope| {
            let origin = envelope
                .payload
                .get("origin")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string();
            // Own publishes were already delivered locally; skipping them
            // makes the in-memory bus a no-op passthrough.
            if origin == instance_id {
                return Ok(());
            }
            let message = envelope
                .payload
                .get("message")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string();

            let manager = manager.clone();
            tokio::spawn(async move {
                if let Some(user_id) = envelope
                    .payload
                    .get("target_user")
                    .and_then(|v| v.as_str())
                    .and_then(|s| Uuid::parse_str(s).ok())
                {
                    manager.deliver_to_user_local(user_id, &message).await;
                } else if let Some(room) =
                    envelope.payload.get("target_room").and_then(|v| v.as_str())
                {
                    manager.deliver_to_room_local(room, &message).await;
                }
            });
            Ok(())
        })
    }
}

impl Clone for WebSocketManager {
    fn clone(&self) -> Self {
        Self {
            rooms: Arc::clone(&self.rooms),
            connections: Arc::clone(&self.connections),
            user_index: Arc::clone(&self.user_index),
            dropped_sends: Arc::clone(&self.dropped_sends),
            next_connection_id: Arc::clone(&self.next_connection_id),
            event_bus: Arc::clone(&self.event_bus),
            instance_id: Arc::clone(&self.instance_id),
            bus_attached: Arc::clone(&self.bus_attached),
        }
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
    async fn test_two_connections_same_user_both_receive() {
        let manager = WebSocketManager::new();
        let user_id = Uuid::new_v4();
        let tenant_id = Uuid::new_v4();

        let mut rx1 = manager.connect(user_id, tenant_id).await.rx;
        let mut rx2 = manager.connect(user_id, tenant_id).await.rx;
        assert_eq!(manager.connection_count_for_user(user_id).await, 2);

        let sent = manager.send_to_user(user_id, "private").await;
        assert!(sent);

        let msg1 = rx1.recv().await.unwrap();
        let msg2 = rx2.recv().await.unwrap();
        assert_eq!(msg1, "private");
        assert_eq!(msg2, "private");
    }

    #[tokio::test]
    async fn test_one_disconnect_leaves_other_alive() {
        let manager = WebSocketManager::new();
        let user_id = Uuid::new_v4();
        let tenant_id = Uuid::new_v4();

        let handle1 = manager.connect(user_id, tenant_id).await;
        let handle2 = manager.connect(user_id, tenant_id).await;
        let mut rx1 = handle1.rx;

        manager.disconnect(handle2.connection_id).await;
        assert_eq!(manager.connection_count_for_user(user_id).await, 1);

        // The remaining connection still receives user messages.
        let sent = manager.send_to_user(user_id, "still alive").await;
        assert!(sent);
        let msg = rx1.recv().await.unwrap();
        assert_eq!(msg, "still alive");
    }

    #[tokio::test]
    async fn test_disconnect_removes_user_index_entry_when_last() {
        let manager = WebSocketManager::new();
        let user_id = Uuid::new_v4();
        let handle = manager.connect(user_id, Uuid::new_v4()).await;

        manager.disconnect(handle.connection_id).await;
        assert_eq!(manager.connection_count_for_user(user_id).await, 0);
        let sent = manager.send_to_user(user_id, "gone").await;
        assert!(!sent);
    }

    #[tokio::test]
    async fn test_send_to_user_fans_out_to_all_connections() {
        let manager = WebSocketManager::new();
        let user_id = Uuid::new_v4();

        let mut rx1 = manager.connect(user_id, Uuid::new_v4()).await.rx;
        let mut rx2 = manager.connect(user_id, Uuid::new_v4()).await.rx;

        let sent = manager.send_to_user(user_id, "fanout").await;
        assert!(sent);

        assert_eq!(rx1.recv().await.unwrap(), "fanout");
        assert_eq!(rx2.recv().await.unwrap(), "fanout");
    }

    #[tokio::test]
    async fn test_leave_room_cleanup() {
        let manager = WebSocketManager::new();
        let _rx = manager.join_room("cleanup-test").await;

        {
            let rooms = manager.rooms.read().await;
            assert!(rooms.contains_key("cleanup-test"));
        }

        // Dropping the receiver then calling leave_room removes the entry.
        drop(_rx);
        manager.leave_room("cleanup-test").await;

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

    #[tokio::test]
    async fn test_room_broadcast_reaches_all_subscribers() {
        let manager = WebSocketManager::new();
        let mut rx1 = manager.join_room("multi-room").await;
        let mut rx2 = manager.join_room("multi-room").await;

        manager.broadcast_to_room("multi-room", "broadcast").await;

        assert_eq!(rx1.recv().await.unwrap(), "broadcast");
        assert_eq!(rx2.recv().await.unwrap(), "broadcast");
    }
}

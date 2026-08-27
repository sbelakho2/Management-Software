//! Unified realtime fanout contract (cross-replica WS + SSE).
//!
//! ONE core-NATS topic carries ONE envelope shape; every API replica
//! subscribes (per-instance group, so EVERY replica receives every
//! envelope) and performs local socket matching. This replaces the
//! previous per-kind subjects (`sensei.ws.user.<id>` vs subscriptions on
//! `sensei.ws.user`) which never matched, and the serialized-shape
//! mismatch between publisher and subscriber.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Single core-NATS topic for all realtime fanout.
pub const REALTIME_TOPIC: &str = "sensei.realtime";

/// Who the envelope is aimed at (matching is done locally on each replica).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RealtimeTarget {
    /// Deliver to one user's local sockets.
    User(Uuid),
    /// Deliver to every socket in a named room/channel.
    Room(String),
    /// Deliver to every socket of the tenant.
    Tenant,
}

/// The one envelope published on [`REALTIME_TOPIC`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealtimeEnvelope {
    pub id: Uuid,
    pub tenant_id: Uuid,
    /// The replica that originated the event (used to skip self-delivery;
    /// the origin replica already delivered locally).
    pub origin_instance: Uuid,
    pub target: RealtimeTarget,
    pub event_type: String,
    pub payload: serde_json::Value,
}

impl RealtimeEnvelope {
    pub fn user(
        tenant_id: Uuid,
        user_id: Uuid,
        origin: Uuid,
        event_type: &str,
        payload: serde_json::Value,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            tenant_id,
            origin_instance: origin,
            target: RealtimeTarget::User(user_id),
            event_type: event_type.to_string(),
            payload,
        }
    }

    pub fn room(
        tenant_id: Uuid,
        room: &str,
        origin: Uuid,
        event_type: &str,
        payload: serde_json::Value,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            tenant_id,
            origin_instance: origin,
            target: RealtimeTarget::Room(room.to_string()),
            event_type: event_type.to_string(),
            payload,
        }
    }
}

/// Publish a realtime envelope on the bus (fire-and-forget; ephemeral
/// broadcast, never JetStream).
pub async fn publish_realtime(bus: &dyn sensei_event_bus::EventBus, envelope: &RealtimeEnvelope) {
    let Ok(payload) = serde_json::to_vec(envelope) else {
        return;
    };
    if let Err(e) = bus.publish_core(REALTIME_TOPIC, &payload).await {
        tracing::debug!(error = %e, "Realtime fanout publish failed");
    }
}

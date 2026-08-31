//! The canonical operational event envelope (fifteenth audit 31-33).
use uuid::Uuid;

/// One object the event touches (a work order, a lot, a machine, a
/// customer order... — an event links MANY objects, not one case id).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ObjectLink {
    pub object_type: String,
    pub object_id: Uuid,
    pub role: Option<String>,
}

/// The canonical event. occurred_at and recorded_at deliberately differ —
/// bitemporal: "what did we believe on July 3?" vs "what do we now know
/// happened on July 3?".
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ForgeEvent {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub event_type: String,
    pub occurred_at: chrono::DateTime<chrono::Utc>,
    pub recorded_at: chrono::DateTime<chrono::Utc>,
    pub scope_site_id: Option<Uuid>,
    pub actor_id: Option<Uuid>,
    pub objects: Vec<ObjectLink>,
    pub source_system: Option<String>,
    pub source_id: Option<String>,
    pub sensitivity: String,
    pub payload: serde_json::Value,
    pub sequence: i64,
}

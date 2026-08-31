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
    /// Envelope semantics (sixteenth audit 23-24): schema version so
    /// consumers can reject unknown envelope shapes, stream identity for
    /// per-(stream_type, stream_id) ordering, an idempotency key so a
    /// source retry cannot double-record, and supersession/valid-time
    /// window for corrective events.
    #[serde(default = "default_schema_version")]
    pub event_schema_version: u32,
    #[serde(default)]
    pub stream_type: Option<String>,
    #[serde(default)]
    pub stream_id: Option<String>,
    #[serde(default)]
    pub stream_sequence: Option<i64>,
    #[serde(default)]
    pub idempotency_key: Option<String>,
    #[serde(default)]
    pub supersedes_event_id: Option<Uuid>,
    #[serde(default)]
    pub effective_from: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub effective_to: Option<chrono::DateTime<chrono::Utc>>,
}

fn default_schema_version() -> u32 {
    1
}

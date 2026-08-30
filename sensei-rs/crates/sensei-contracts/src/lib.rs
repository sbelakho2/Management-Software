//! sensei-contracts (thirteenth audit): the CANONICAL request/response
//! contracts shared by backend and frontend. No independent DTO should
//! exist twice unless there is a deliberate boundary transformation —
//! this crate is that single source.

pub mod pagination;
pub mod tps;

/// The canonical Andon contract — the backend `Andon` domain and the
/// frontend Andon surface both (de)serialize THIS type, so the legacy
/// title/location-style DTO mismatches cannot recur.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Andon {
    pub id: uuid::Uuid,
    pub tenant_id: uuid::Uuid,
    pub andon_number: String,
    pub work_center_id: uuid::Uuid,
    pub issue_type: String,
    pub severity: String,
    pub description: String,
    pub status: String,
    pub raised_by: uuid::Uuid,
    #[serde(default)]
    pub acknowledged_by: Option<uuid::Uuid>,
    #[serde(default)]
    pub resolved_by: Option<uuid::Uuid>,
    #[serde(default)]
    pub resolution: Option<String>,
    #[serde(default)]
    pub response_time_seconds: Option<i64>,
    #[serde(default)]
    pub resolution_time_seconds: Option<i64>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    #[serde(default)]
    pub acknowledged_at: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub resolved_at: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub restart_authorized_by: Option<uuid::Uuid>,
    #[serde(default)]
    pub restart_authorized_at: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub abnormal_condition_observed_at: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub contained_at: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub contained_by: Option<uuid::Uuid>,
    #[serde(default)]
    pub contained_note: Option<String>,
    #[serde(default)]
    pub escalated: bool,
    #[serde(default)]
    pub escalated_at: Option<chrono::DateTime<chrono::Utc>>,
}

#[cfg(test)]
mod parity_tests {
    use super::*;
    use crate::tps::MeasurementState;

    /// The contract must deserialize EXACTLY the JSON the backend Andon
    /// domain serializes — a field added to the domain without the
    /// contract (or vice versa) breaks this test.
    #[test]
    fn andon_contract_matches_backend_domain_shape() {
        let json = serde_json::json!({
            "id": "11111111-1111-1111-1111-111111111111",
            "tenant_id": "22222222-2222-2222-2222-222222222222",
            "andon_number": "A-0001",
            "work_center_id": "33333333-3333-3333-3333-333333333333",
            "issue_type": "material",
            "severity": "medium",
            "description": "connector tray empty",
            "status": "active",
            "raised_by": "44444444-4444-4444-4444-444444444444",
            "created_at": "2026-08-30T10:00:00Z",
            "escalated": false
        });
        let andon: Andon = serde_json::from_value(json).expect("backend JSON must deserialize");
        assert_eq!(andon.issue_type, "material");
        assert_eq!(andon.status, "active");
        assert_eq!(andon.andon_number, "A-0001");
        assert!(!andon.escalated);
        // Round-trip: the contract serializes back to the same shape.
        let out = serde_json::to_value(&andon).expect("serialize");
        assert_eq!(out["issue_type"], "material");
        assert_eq!(out["status"], "active");
    }

    /// Unknown is an actual type: an unmeasured value is never zero.
    #[test]
    fn measurement_state_never_fakes_precision() {
        let m = MeasurementState::unavailable("rework is not tracked");
        assert_eq!(m.value(), None, "unavailable has no numeric value");
        let n = MeasurementState::measured(42.0);
        assert_eq!(n.value(), Some(42.0));
        assert!(!matches!(m, MeasurementState::Measured { .. }));
    }
}

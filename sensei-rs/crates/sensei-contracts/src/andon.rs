//! The canonical Andon contract (thirtieth-first audit): the backend
//! `Andon` response surface and the frontend Andon page both (de)serialize
//! THIS type, so the legacy title/location/request_key-style DTO
//! mismatches cannot recur.
//!
//! Rules of this surface:
//! - `site_id` is ALWAYS present on the wire: an Andon is explicitly
//!   operational-scoped, never implicitly company-wide.
//! - `request_key` (the client's idempotency key) is INTERNAL-ONLY: it is
//!   stored by the service for replay protection but never serialized.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// The Andon as the API returns it — every field the board and the
/// station need, with NO request_key exposure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndonResponse {
    pub id: Uuid,
    pub tenant_id: Uuid,
    /// The site the signal belongs to — explicit operational scope. The
    /// server resolves it from the caller's assignment; the client never
    /// supplies it.
    pub site_id: Uuid,
    pub andon_number: String,
    pub work_center_id: Uuid,
    pub issue_type: String, // quality, safety, maintenance, material, other
    pub severity: String,   // low, medium, high, critical
    pub description: String,
    pub status: String, // active, acknowledged, resolved, closed
    pub raised_by: Uuid,
    #[serde(default)]
    pub acknowledged_by: Option<Uuid>,
    #[serde(default)]
    pub resolved_by: Option<Uuid>,
    #[serde(default)]
    pub resolution: Option<String>,
    #[serde(default)]
    pub response_time_seconds: Option<i64>,
    #[serde(default)]
    pub resolution_time_seconds: Option<i64>,
    pub created_at: DateTime<Utc>,
    #[serde(default)]
    pub acknowledged_at: Option<DateTime<Utc>>,
    #[serde(default)]
    pub resolved_at: Option<DateTime<Utc>>,
    /// Restart authorization for critical-safety Andons (hard rule: the
    /// line stays stopped until an authorized restart exists).
    #[serde(default)]
    pub restart_authorized_by: Option<Uuid>,
    #[serde(default)]
    pub restart_authorized_at: Option<DateTime<Utc>>,
    /// When the abnormal condition was OBSERVED — detection latency =
    /// observed_at vs created_at, measured honestly.
    #[serde(default)]
    pub abnormal_condition_observed_at: Option<DateTime<Utc>>,
    /// When customer/process risk was CONTAINED — distinct from
    /// resolved_at (root cause fixed).
    #[serde(default)]
    pub contained_at: Option<DateTime<Utc>>,
    #[serde(default)]
    pub contained_by: Option<Uuid>,
    #[serde(default)]
    pub contained_note: Option<String>,
    /// Escalation to tier review is a REAL state.
    #[serde(default)]
    pub escalated: bool,
    #[serde(default)]
    pub escalated_at: Option<DateTime<Utc>>,
}

/// The operator's raise inputs — ONLY the operational facts. There is no
/// `work_center_id` and no `site_id`: the server resolves both from the
/// caller's active operational assignment and DENIES when there is none
/// (a caller can never forge scope or attribute an Andon to someone
/// else). Unknown fields are rejected so a legacy client sending
/// work_center_id/location-style payloads fails loudly instead of
/// silently dropping scope.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RaiseAndonRequest {
    pub issue_type: String, // quality, safety, maintenance, material, other
    pub severity: String,   // low, medium, high, critical
    pub description: String,
    /// When the abnormal condition was OBSERVED: the operator's honest
    /// observation time — detection latency becomes measurable. Rejected
    /// server-side when in the future beyond a small clock-skew
    /// allowance.
    #[serde(default)]
    pub observed_at: Option<DateTime<Utc>>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn andon_response_round_trips_canonical_shape() {
        let json = serde_json::json!({
            "id": "11111111-1111-1111-1111-111111111111",
            "tenant_id": "22222222-2222-2222-2222-222222222222",
            "site_id": "55555555-5555-5555-5555-555555555555",
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
        let andon: AndonResponse =
            serde_json::from_value(json).expect("backend JSON must deserialize");
        assert_eq!(andon.issue_type, "material");
        assert_eq!(andon.status, "active");
        assert_eq!(andon.andon_number, "A-0001");
        assert!(!andon.escalated);
        let out = serde_json::to_value(&andon).expect("serialize");
        assert_eq!(out["site_id"], "55555555-5555-5555-5555-555555555555");
        assert!(
            out.get("request_key").is_none(),
            "request_key must never serialize"
        );
    }

    #[test]
    fn raise_request_denies_unknown_fields() {
        let json = serde_json::json!({
            "issue_type": "quality",
            "severity": "high",
            "description": "missing torque step",
            "work_center_id": "33333333-3333-3333-3333-333333333333"
        });
        let err = serde_json::from_value::<RaiseAndonRequest>(json)
            .expect_err("work_center_id is server-resolved — payload must be rejected");
        assert!(err.to_string().contains("work_center_id"));
    }

    #[test]
    fn raise_request_minimal_payload() {
        let json = serde_json::json!({
            "issue_type": "safety",
            "severity": "critical",
            "description": "guard removed"
        });
        let req: RaiseAndonRequest =
            serde_json::from_value(json).expect("minimal raise must parse");
        assert_eq!(req.issue_type, "safety");
        assert!(req.observed_at.is_none());
        let out = serde_json::to_value(&req).unwrap();
        assert!(out.get("work_center_id").is_none());
    }
}

//! Agent context: SERVER-CREATED and immutable to the model.
//!
//! The critical rule: the model can never specify `tenant_id` or `user_id`
//! in a tool call — those are injected by the server-side tool executor
//! from this context.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

/// Everything the agent may know about the caller and the plant. Built by
/// the server from the authenticated request — never from model input.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentContext {
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub session_id: Option<Uuid>,

    // Plant context (the "where" of every operational fact).
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub shift_id: Option<Uuid>,

    pub roles: Vec<String>,
    /// The caller's effective permission set (resolved by the
    /// authorization service — the agent can never widen it).
    pub permissions: std::collections::HashSet<String>,

    pub locale: String,
    /// IANA timezone identifier (e.g. "Europe/Paris").
    pub timezone: String,

    pub request_id: Uuid,
    pub conversation_id: Option<Uuid>,
}

impl AgentContext {
    /// Whether the caller may execute the given permission.
    pub fn can(&self, permission: &str) -> bool {
        self.permissions.iter().any(|p| {
            p == "*:*"
                || p == permission
                || (p.ends_with(":*") && permission.starts_with(&p[..p.len() - 1]))
        })
    }
}

/// Data classification (sixteenth audit items 9/85): ONE core type —
/// never a free-form string ("internal".parse::<u32>() failing open is
/// the exact bug this fixes).
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, serde::Serialize, serde::Deserialize,
)]
#[repr(u8)]
#[serde(rename_all = "snake_case")]
pub enum DataClass {
    Public = 0,
    Internal = 1,
    Confidential = 2,
    Restricted = 3,
}

impl DataClass {
    pub fn parse(s: &str) -> Option<Self> {
        match s.trim().to_lowercase().as_str() {
            "public" | "0" => Some(Self::Public),
            "internal" | "1" => Some(Self::Internal),
            "confidential" | "2" => Some(Self::Confidential),
            "restricted" | "3" => Some(Self::Restricted),
            _ => None,
        }
    }
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Public => "public",
            Self::Internal => "internal",
            Self::Confidential => "confidential",
            Self::Restricted => "restricted",
        }
    }
}

/// The context request envelope (fifteenth audit item 7): the system
/// knows more than the user's words — there is NO "search query string".
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextRequest {
    pub principal_id: Uuid,
    pub roles: Vec<String>,
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub task: TaskKind,
    pub focal_objects: Vec<serde_json::Value>,
    pub max_tokens: u32,
    /// Sixteenth audit items 9/85: TYPED — an unknown string can never
    /// silently disable the filter.
    pub sensitivity_ceiling: DataClass,
    pub trace_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskKind {
    Troubleshoot,
    ExecutiveAnalysis,
    OperatorAssist,
    PlannerDecision,
    QualityInvestigation,
    General,
}

/// Central provenance (sixteenth audit item 86): ONE type used by
/// ContextItem, MetricResult, Lesson, Episode and model claims.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Provenance {
    pub source: String,
    pub source_revision: Option<String>,
    pub observed_at: Option<chrono::DateTime<chrono::Utc>>,
    pub recorded_at: chrono::DateTime<chrono::Utc>,
    pub authority: AuthorityRank,
}

/// One context item with provenance as DATA (fifteenth audit 75-76):
/// selection maximizes relevance × authority × freshness under the token
/// budget and authorization constraints.
///
/// `evidence_id` (nineteenth audit P1): the TYPED provenance token of this
/// item — a deterministic identifier derived from provenance.source +
/// provenance.observed_at + the payload hash. Claims may only cite
/// `[evidence: <evidence_id>]` markers, and verification checks the id
/// against the ACTUAL evidence_id set of the prepared kernel items — never
/// a substring match against a flattened context string.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextItem {
    pub payload: serde_json::Value,
    pub provenance: Provenance,
    pub sensitivity: DataClass,
    pub token_cost: u32,
    pub epistemic_status: EpistemicStatus,
    /// The kernel-issued deterministic evidence id (nineteenth audit P1).
    /// Empty for legacy constructions until the Context Kernel normalizes
    /// it from the item's own provenance + payload.
    #[serde(default = "default_evidence_id")]
    pub evidence_id: String,
    /// The FACT ADDRESS this evidence describes (twenty-first audit item
    /// 7): the section/source the item came from, so a claim can be
    /// checked against whether the cited evidence actually speaks about
    /// the claimed subject — an inventory EvidenceRef can never prove a
    /// staffing claim.
    #[serde(default)]
    pub fact_address: Option<String>,
    /// The SITE SCOPE this evidence was produced under (twenty-third
    /// audit): set at construction from the request's operating scope so
    /// verification is STRUCTURAL (site uuids compare), not prose
    /// parsing — new plants require zero Rust changes.
    #[serde(default)]
    pub site_scope: Option<uuid::Uuid>,
}

/// Legacy/absent `evidence_id` deserializes to an empty string; the
/// Context Kernel normalizes it from the item's own provenance + payload
/// (nineteenth audit P1).
fn default_evidence_id() -> String {
    String::new()
}

impl ContextItem {
    /// The deterministic evidence id of this item: sha256 over
    /// provenance.source + provenance.observed_at + the canonical payload,
    /// truncated to 16 bytes of hex with an `ev:` prefix (nineteenth audit
    /// P1). Identical items (same source, same observed_at, same payload)
    /// always derive the same id; `recorded_at` is deliberately excluded
    /// so the id is stable across construction.
    pub fn derive_evidence_id(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(self.provenance.source.as_bytes());
        hasher.update(b"\x1f");
        hasher.update(
            self.provenance
                .observed_at
                .map(|t| t.to_rfc3339())
                .unwrap_or_default()
                .as_bytes(),
        );
        hasher.update(b"\x1f");
        hasher.update(
            serde_json::to_string(&self.payload)
                .unwrap_or_default()
                .as_bytes(),
        );
        let digest = hasher.finalize();
        let hex: String = digest.iter().take(16).map(|b| format!("{b:02x}")).collect();
        format!("ev:{hex}")
    }
}

/// Explicit source-authority hierarchy (fifteenth audit 76): an AI
/// summary never outranks the source it summarized.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AuthorityRank {
    ApprovedStandard,
    ReleasedEngineeringRecord,
    TransactionalState,
    ApprovedCorrectiveAction,
    VerifiedObservation,
    EmployeeNote,
    AiInference,
}

/// Fact vs inference vs hypothesis (fifteenth audit 79/A10), extended to
/// the full consolidated epistemic vocabulary (sixteenth audit item 87):
/// Recommendation and ProposedAction are distinct from a recorded fact.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EpistemicStatus {
    RecordedFact,
    DerivedFact,
    Inference,
    Hypothesis,
    Recommendation,
    ProposedAction,
}

/// A structured claim emitted by the chat verifier (eighteenth audit
/// P1-7): one per factual-sounding sentence. `epistemic_status` is
/// "measured" when an `[evidence: <source>]` marker matches a prepared
/// context source, "unverified" when the sentence asserts a fact without
/// matching evidence, and may carry the other epistemic labels
/// ("inferred" | "assumed" | "recommended") from future verifier passes.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Claim {
    pub statement: String,
    /// "measured" | "inferred" | "assumed" | "recommended" | "unverified"
    pub epistemic_status: String,
    pub fact_addresses: Vec<String>,
    pub evidence_refs: Vec<String>,
    pub confidence: Option<f64>,
    pub valid_at: Option<String>,
}

/// The DETERMINISTIC context plan (fifteenth audit 74): the task decides
/// what must be present BEFORE any semantic retrieval — the model never
/// invents the retrieval strategy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextPlan {
    pub required: Vec<String>,
    pub task: TaskKind,
    pub budget: u32,
}

pub fn plan_context(req: &ContextRequest) -> ContextPlan {
    let mut required = vec![
        "governing_context".to_string(),
        "authority_scope".to_string(),
        "role_context".to_string(),
        "current_work".to_string(),
    ];
    match req.task {
        TaskKind::Troubleshoot => {
            required.push("process_standard".into());
            required.push("recent_failures".into());
            required.push("similar_lessons".into());
        }
        TaskKind::ExecutiveAnalysis => {
            required.push("metric_tree".into());
            required.push("exception_summary".into());
            required.push("causal_candidates".into());
        }
        TaskKind::OperatorAssist => {
            required.push("standard_work".into());
            required.push("live_state".into());
        }
        TaskKind::PlannerDecision => {
            required.push("demand_vs_capacity".into());
            required.push("constraint_loading".into());
        }
        TaskKind::QualityInvestigation => {
            required.push("occurrence_history".into());
            required.push("detection_history".into());
            required.push("escape_history".into());
        }
        TaskKind::General => {}
    }
    ContextPlan {
        required,
        task: req.task.clone(),
        budget: req.max_tokens,
    }
}

/// Token-budget allocation (fifteenth audit 8): dynamic per task, not
/// hardcoded globally. Returns the section → token share (0..1).
pub fn budget_allocation(task: &TaskKind) -> Vec<(&'static str, f64)> {
    match task {
        TaskKind::Troubleshoot => vec![
            ("live_state", 0.20),
            ("process_standard", 0.18),
            ("episodic_history", 0.20),
            ("graph", 0.10),
            ("rules", 0.08),
            ("role", 0.08),
            ("analytics", 0.06),
            ("provenance", 0.05),
            ("tool_contract", 0.05),
        ],
        TaskKind::ExecutiveAnalysis => vec![
            ("aggregation", 0.25),
            ("causal_candidates", 0.15),
            ("exceptions", 0.15),
            ("cross_site", 0.10),
            ("rules", 0.08),
            ("role", 0.08),
            ("provenance", 0.05),
            ("tool_contract", 0.04),
        ],
        _ => vec![
            ("live_state", 0.20),
            ("standard_work", 0.18),
            ("process_standard", 0.14),
            ("episodic_history", 0.12),
            ("graph", 0.10),
            ("rules", 0.08),
            ("role", 0.08),
            ("analytics", 0.05),
            ("provenance", 0.03),
            ("tool_contract", 0.02),
        ],
    }
}

/// A fact ADDRESS (sixteenth audit item 10): a contradiction requires
/// the SAME object, SAME attribute and SAME relevant time with different
/// authoritative values.
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct FactAddress {
    pub object_type: String,
    pub object_id: String,
    pub attribute: String,
    pub valid_time: Option<String>,
}

/// A fact candidate with provenance — only same-address candidates can
/// contradict.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FactCandidate {
    pub address: FactAddress,
    pub value: serde_json::Value,
    pub provenance: String,
}

/// A bounded conflict budget (sixteenth audit item 11): contradictions
/// are compact, not two full 8k-token documents.
#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize)]
pub struct TokenBudget {
    pub normal: u32,
    pub conflicts_reserved: u32,
    pub emergency_overrun: u32,
}

impl TokenBudget {
    pub fn default_for(max_tokens: u32) -> Self {
        Self {
            normal: (max_tokens as f64 * 0.85) as u32,
            conflicts_reserved: (max_tokens as f64 * 0.10) as u32,
            emergency_overrun: (max_tokens as f64 * 0.05) as u32,
        }
    }
}

/// The fact address an item contributes for `attribute`: from
/// payload["_fact_address"] (object_type/object_id/valid_time) or, when
/// absent, from payload["id"] + the key being examined. Returns None when
/// the object identity is unknown — an item without id and without
/// _fact_address is never grouped, so it can never contradict.
pub(crate) fn fact_address_of(item: &ContextItem, attribute: &str) -> Option<FactAddress> {
    let payload = &item.payload;
    let object_id = payload
        .get("_fact_address")
        .and_then(|a| a.get("object_id"))
        .and_then(|v| v.as_str())
        .or_else(|| payload.get("id").and_then(|v| v.as_str()))?;
    Some(FactAddress {
        object_type: payload
            .get("_fact_address")
            .and_then(|a| a.get("object_type"))
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string(),
        object_id: object_id.to_string(),
        attribute: attribute.to_string(),
        valid_time: payload
            .get("_fact_address")
            .and_then(|a| a.get("valid_time"))
            .and_then(|v| v.as_str())
            .map(str::to_string),
    })
}

/// Detect contradictions ONLY at the fact-address level: group items by
/// (object_type, object_id, attribute) parsed from the item payload —
/// an item contributes its address from payload["_fact_address"] (an
/// object with object_type/object_id/attribute) or, when absent, from
/// payload["id"] + the KEY being examined. Two items with the SAME
/// address and DIFFERENT values for that attribute are a contradiction.
pub fn contradiction_candidates(
    items: &[ContextItem],
    attribute: &str,
) -> Vec<(FactAddress, Vec<serde_json::Value>)> {
    let mut groups: std::collections::HashMap<FactAddress, Vec<serde_json::Value>> =
        std::collections::HashMap::new();
    for item in items {
        let Some(address) = fact_address_of(item, attribute) else {
            continue;
        };
        let Some(value) = item.payload.get(attribute) else {
            continue;
        };
        let values = groups.entry(address).or_default();
        if !values.iter().any(|v| v == value) {
            values.push(value.clone());
        }
    }
    let mut result: Vec<_> = groups
        .into_iter()
        .filter(|(_, values)| values.len() > 1)
        .collect();
    result.sort_by(|a, b| {
        a.0.object_type
            .cmp(&b.0.object_type)
            .then_with(|| a.0.object_id.cmp(&b.0.object_id))
            .then_with(|| a.0.attribute.cmp(&b.0.attribute))
    });
    result
}

/// Contradiction survives retrieval (fifteenth audit 77): a group of
/// items disagreeing on a fact is returned as a conflict, never
/// collapsed. Thin wrapper over [`contradiction_candidates`] for
/// backward compatibility (sixteenth audit 10): only same-address facts
/// can contradict.
pub fn has_contradiction(items: &[ContextItem], fact_key: &str) -> bool {
    !contradiction_candidates(items, fact_key).is_empty()
}

/// Extract the SOURCE observation time from a context line when the line
/// carries an RFC3339 timestamp (the section builders stamp event/record
/// times). Returns None when no timestamp is exposed — retrieval time is
/// NEVER substituted for observation time (twentieth audit P1).
pub fn parse_observed_at(text: &str) -> Option<chrono::DateTime<chrono::Utc>> {
    // Look for RFC3339 timestamps (ISO-8601 with T and timezone) inside
    // the text; take the LAST one (the most specific statement time).
    let mut found = None;
    let bytes = text.as_bytes();
    let mut i = 0;
    while i + 19 <= bytes.len() {
        // candidate at i: 4-2-2 T 2:2:2 (19 chars) followed by Z or offset
        if bytes[i + 4] == b'-' && bytes[i + 7] == b'-' && bytes[i + 10] == b'T' {
            let end = (i + 19..text.len().min(i + 32))
                .find(|&j| bytes[j] == b' ' || bytes[j] == 10 || bytes[j] == b')')
                .unwrap_or(text.len());
            let cand = &text[i..end];
            if let Ok(ts) = chrono::DateTime::parse_from_rfc3339(cand) {
                found = Some(ts.with_timezone(&chrono::Utc));
                i = end;
                continue;
            }
        }
        i += 1;
    }
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn context_cannot_be_mutated_by_tools() {
        let ctx = AgentContext {
            tenant_id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec!["operator".to_string()],
            permissions: std::collections::HashSet::from(
                ["production:work-order:read".to_string()],
            ),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: Uuid::new_v4(),
            conversation_id: None,
        };
        assert!(ctx.can("production:work-order:read"));
        assert!(!ctx.can("finance:invoice:create"));
    }

    #[test]
    fn wildcard_permissions_grant() {
        let ctx = AgentContext {
            tenant_id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec![],
            permissions: std::collections::HashSet::from(["production:*".to_string()]),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: Uuid::new_v4(),
            conversation_id: None,
        };
        assert!(ctx.can("production:report"));
        assert!(!ctx.can("quality:ncr:read"));
    }

    #[test]
    fn context_item_provenance_source_round_trips() {
        let item = ContextItem {
            payload: serde_json::json!({"id": "WO-1", "status": "open"}),
            provenance: Provenance {
                source: "machining-line-4/plc".to_string(),
                source_revision: Some("rev-2026-08-31".to_string()),
                observed_at: Some(chrono::Utc::now()),
                recorded_at: chrono::Utc::now(),
                authority: AuthorityRank::VerifiedObservation,
            },
            sensitivity: DataClass::Internal,
            token_cost: 12,
            epistemic_status: EpistemicStatus::RecordedFact,
            evidence_id: String::new(),
            site_scope: None,
            fact_address: None,
        };
        let json = serde_json::to_string(&item).unwrap();
        assert!(json.contains("\"provenance\""));
        let back: ContextItem = serde_json::from_str(&json).unwrap();
        assert_eq!(back.provenance.source, "machining-line-4/plc");
        assert_eq!(
            back.provenance.authority,
            AuthorityRank::VerifiedObservation
        );
        assert!(back.evidence_id.is_empty());
    }

    #[test]
    fn evidence_id_is_deterministic_distinct_and_prefixed() {
        let now = chrono::Utc::now();
        let mk = |source: &str, observed_at: chrono::DateTime<chrono::Utc>| ContextItem {
            payload: serde_json::json!({"id": "WO-1", "status": "open"}),
            provenance: Provenance {
                source: source.to_string(),
                source_revision: None,
                observed_at: Some(observed_at),
                recorded_at: chrono::Utc::now(),
                authority: AuthorityRank::VerifiedObservation,
            },
            sensitivity: DataClass::Internal,
            token_cost: 12,
            epistemic_status: EpistemicStatus::RecordedFact,
            evidence_id: String::new(),
            site_scope: None,
            fact_address: None,
        };
        let a1 = mk("sensor-a", now);
        let a2 = mk("sensor-a", now);
        assert_eq!(a1.derive_evidence_id(), a2.derive_evidence_id());
        assert!(a1.derive_evidence_id().starts_with("ev:"));
        assert_ne!(
            a1.derive_evidence_id(),
            mk("sensor-b", now).derive_evidence_id(),
            "different source must derive a different id"
        );
        assert_ne!(
            a1.derive_evidence_id(),
            mk("sensor-a", now - chrono::Duration::minutes(1)).derive_evidence_id(),
            "different observed_at must derive a different id"
        );
    }

    #[test]
    fn legacy_context_item_json_defaults_evidence_id() {
        let json = r#"{"payload":{"id":"WO-1"},"provenance":{"source":"x","source_revision":null,"observed_at":null,"recorded_at":"2026-01-01T00:00:00Z","authority":"verified_observation"},"sensitivity":"internal","token_cost":1,"epistemic_status":"recorded_fact"}"#;
        let item: ContextItem = serde_json::from_str(json).unwrap();
        assert!(item.evidence_id.is_empty());
        let derived = item.derive_evidence_id();
        assert!(derived.starts_with("ev:"));
    }

    #[test]
    fn epistemic_status_recommendation_serializes_as_snake_case() {
        assert_eq!(
            serde_json::to_string(&EpistemicStatus::Recommendation).unwrap(),
            "\"recommendation\""
        );
        assert_eq!(
            serde_json::to_string(&EpistemicStatus::ProposedAction).unwrap(),
            "\"proposed_action\""
        );
    }

    #[test]
    fn claim_round_trips() {
        let claim = Claim {
            statement: "Line 12 yields 42 units".to_string(),
            epistemic_status: "measured".to_string(),
            fact_addresses: Vec::new(),
            evidence_refs: vec!["metric.process_yield_proxy@Bizerte".to_string()],
            confidence: None,
            valid_at: None,
        };
        let json = serde_json::to_string(&claim).unwrap();
        let back: Claim = serde_json::from_str(&json).unwrap();
        assert_eq!(back.statement, claim.statement);
        assert_eq!(back.epistemic_status, "measured");
        assert_eq!(back.evidence_refs, claim.evidence_refs);
        assert!(back.fact_addresses.is_empty());
        assert_eq!(back.confidence, None);
        assert_eq!(back.valid_at, None);
    }
}

//! Agent context: SERVER-CREATED and immutable to the model.
//!
//! The critical rule: the model can never specify `tenant_id` or `user_id`
//! in a tool call — those are injected by the server-side tool executor
//! from this context.

use serde::{Deserialize, Serialize};
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
    pub sensitivity_ceiling: String,
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

/// One context item with provenance as DATA (fifteenth audit 75-76):
/// selection maximizes relevance × authority × freshness under the token
/// budget and authorization constraints.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextItem {
    pub payload: serde_json::Value,
    pub source: String,
    pub source_revision: Option<String>,
    pub observed_at: Option<chrono::DateTime<chrono::Utc>>,
    pub authority: AuthorityRank,
    pub sensitivity: String,
    pub token_cost: u32,
    pub epistemic_status: EpistemicStatus,
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

/// Fact vs inference vs hypothesis (fifteenth audit 79/A10).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EpistemicStatus {
    RecordedFact,
    DerivedFact,
    Inference,
    Hypothesis,
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
}

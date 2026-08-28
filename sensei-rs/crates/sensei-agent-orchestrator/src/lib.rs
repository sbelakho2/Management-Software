//! Model-provider abstraction (items 137-138): domain behavior never
//! changes when the provider changes. Providers could be a GLM-class
//! frontier model, an OpenAI-compatible gateway, or a local model — the
//! tool/policy contracts stay identical.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A request to a reasoning provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentModelRequest {
    pub system_prompt: String,
    pub user_message: String,
    /// The server-created agent context serialized (the model can never
    /// supply tenant/user/site — they are injected here).
    pub context: serde_json::Value,
    /// Tools the caller may use (already filtered by the policy engine).
    pub tools: Vec<serde_json::Value>,
    pub max_tokens: usize,
}

/// The provider's response: content + structured tool calls.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentModelResponse {
    pub content: String,
    pub tool_calls: Vec<ToolCall>,
    pub provider: String,
    pub model_version: String,
}

/// A tool invocation the model proposes (executed ONLY through the
/// registry with permission re-checks — never from raw model claims).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub tool_name: String,
    pub args: serde_json::Value,
}

/// The provider trait (item 137): every provider implements this; the
/// orchestrator never depends on a specific model.
#[async_trait::async_trait]
pub trait ReasoningProvider: Send + Sync {
    fn provider_name(&self) -> &str;

    async fn complete(&self, request: AgentModelRequest) -> Result<AgentModelResponse, String>;
}

/// Route complexity classes (item 138/120): the big model should not
/// handle every request.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RouteLevel {
    /// Deterministic/no-model (takt, OEE, SPC, MRP, lookups).
    Deterministic,
    /// Small model (classification, extraction, summarization).
    Small,
    /// Medium reasoning (single-domain analysis).
    Medium,
    /// Frontier (cross-domain, ambiguous, strategic).
    Frontier,
}

/// Deterministic routing: intent → complexity → provider (item 120).
pub struct ModelRouter {
    /// Providers by level.
    pub providers: Vec<(RouteLevel, Box<dyn ReasoningProvider>)>,
    pub deterministic_budget_ms: u64,
}

impl ModelRouter {
    pub fn new(providers: Vec<(RouteLevel, Box<dyn ReasoningProvider>)>) -> Self {
        Self {
            providers,
            deterministic_budget_ms: 250,
        }
    }

    pub fn provider_for(&self, level: RouteLevel) -> Option<&dyn ReasoningProvider> {
        self.providers
            .iter()
            .find(|(l, _)| *l == level)
            .map(|(_, p)| p.as_ref())
    }

    /// Classify a request by its characteristics (deterministic rules).
    /// A request that mentions ≥ 3 functional domains, conflicts, or a
    /// long-horizon goal routes to the FRONTIER provider; a single-domain
    /// analysis to MEDIUM; a simple lookup to DETERMINISTIC/SMALL.
    pub fn classify(&self, text: &str, domains: &[&str]) -> RouteLevel {
        if domains.len() >= 3 {
            return RouteLevel::Frontier;
        }
        let lower = text.to_lowercase();
        if lower.contains("why") || lower.contains("compare") || lower.contains("root cause") {
            return RouteLevel::Medium;
        }
        if lower.len() < 120 {
            return RouteLevel::Deterministic;
        }
        RouteLevel::Small
    }
}

/// Idempotency + approval keys for every agent write (item 108/129).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionStep {
    pub tool_name: String,
    pub tool_version: u32,
    pub args: serde_json::Value,
    pub canonical_args_hash: String,
    pub idempotency_key: String,
    pub expected_effect: String,
    pub rollback: Option<String>,
    pub approval_required: bool,
}

/// Agent writes use ActionPlan (item 108): policy decides whether to
/// execute, request approval, or deny — never the model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionPlan {
    pub id: Uuid,
    pub objective: String,
    pub steps: Vec<ActionStep>,
    pub evidence_refs: Vec<sensei_agent_core::evidence::EvidenceRef>,
    pub affected_resources: Vec<String>,
    pub expected_versions: Vec<(String, u64)>,
    pub risks: Vec<String>,
    pub approvals_required: Vec<String>,
    pub idempotency_keys: Vec<String>,
}

impl ActionPlan {
    pub fn all_idempotency_keys(&self) -> Vec<String> {
        let mut keys: Vec<String> = self
            .steps
            .iter()
            .map(|s| s.idempotency_key.clone())
            .collect();
        keys.extend(self.idempotency_keys.iter().cloned());
        keys
    }
}

/// Cross-agent contradiction detection (item 134): the Chief Sensei never
/// averages narratives — it inspects evidence bases and surfaces the
/// underlying discrepancy (typically the time/scope window).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentClaim {
    pub agent: String,
    pub claim: String,
    pub evidence_refs: Vec<String>,
    pub window: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contradiction {
    pub agent_a: String,
    pub agent_b: String,
    pub subject: String,
    pub value_a: String,
    pub value_b: String,
    pub diagnosis: String,
}

/// Detect contradictions between agents' claims about the same subject:
/// differing evidence bases are surfaced, never averaged.
pub fn detect_contradictions(claims: &[AgentClaim]) -> Vec<Contradiction> {
    let mut out = Vec::new();
    for (i, a) in claims.iter().enumerate() {
        for b in claims.iter().skip(i + 1) {
            // Same subject, different value, non-overlapping evidence.
            if a.claim.split(':').next() == b.claim.split(':').next()
                && a.claim != b.claim
                && a.evidence_refs != b.evidence_refs
            {
                out.push(Contradiction {
                    agent_a: a.agent.clone(),
                    agent_b: b.agent.clone(),
                    subject: a.claim.split(':').next().unwrap_or("").to_string(),
                    value_a: a.claim.clone(),
                    value_b: b.claim.clone(),
                    diagnosis: format!(
                        "Evidence bases differ ({} vs {}) — the time/scope window is the \\
                         likely hidden discrepancy",
                        a.evidence_refs.join(","),
                        b.evidence_refs.join(",")
                    ),
                });
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FakeProvider {
        name: String,
    }

    #[async_trait::async_trait]
    impl ReasoningProvider for FakeProvider {
        fn provider_name(&self) -> &str {
            &self.name
        }
        async fn complete(
            &self,
            _request: AgentModelRequest,
        ) -> Result<AgentModelResponse, String> {
            Ok(AgentModelResponse {
                content: "answer".to_string(),
                tool_calls: vec![],
                provider: self.name.clone(),
                model_version: "1".to_string(),
            })
        }
    }

    #[tokio::test]
    async fn router_selects_provider_by_level() {
        let router = ModelRouter::new(vec![
            (
                RouteLevel::Deterministic,
                Box::new(FakeProvider {
                    name: "none".into(),
                }) as Box<dyn ReasoningProvider>,
            ),
            (
                RouteLevel::Frontier,
                Box::new(FakeProvider { name: "glm".into() }),
            ),
        ]);
        assert_eq!(
            router
                .provider_for(RouteLevel::Frontier)
                .unwrap()
                .provider_name(),
            "glm"
        );
        assert!(router.provider_for(RouteLevel::Small).is_none());
    }

    #[test]
    fn classify_routes_by_domains_and_complexity() {
        let router = ModelRouter::new(vec![]);
        assert_eq!(
            router.classify("where is PO 318?", &["purchasing"]),
            RouteLevel::Deterministic
        );
        assert_eq!(
            router.classify("why is the supplier late?", &["purchasing"]),
            RouteLevel::Medium
        );
        assert_eq!(
            router.classify(
                "inventory rising but production missing shipments",
                &["production", "purchasing", "quality"]
            ),
            RouteLevel::Frontier
        );
    }

    #[test]
    fn action_plan_keys_are_deterministic() {
        let plan = ActionPlan {
            id: Uuid::new_v4(),
            objective: "raise andon".to_string(),
            steps: vec![ActionStep {
                tool_name: "raise_andon".to_string(),
                tool_version: 1,
                args: serde_json::json!({"work_center_id": "wc-1"}),
                canonical_args_hash: "h1".to_string(),
                idempotency_key: "andon:wc-1:shift-1".to_string(),
                expected_effect: "andon created".to_string(),
                rollback: None,
                approval_required: false,
            }],
            evidence_refs: vec![],
            affected_resources: vec![],
            expected_versions: vec![],
            risks: vec![],
            approvals_required: vec![],
            idempotency_keys: vec![],
        };
        assert_eq!(plan.all_idempotency_keys(), vec!["andon:wc-1:shift-1"]);
    }

    #[test]
    fn contradictions_are_surfaced_not_averaged() {
        let claims = vec![
            AgentClaim {
                agent: "flow".to_string(),
                claim: "loss:downtime=62min".to_string(),
                evidence_refs: vec!["downtime:D-1".to_string()],
                window: Some("shift 1".to_string()),
            },
            AgentClaim {
                agent: "maintenance".to_string(),
                claim: "loss:downtime=4%".to_string(),
                evidence_refs: vec!["leadtime:L-1".to_string()],
                window: Some("full day".to_string()),
            },
        ];
        let contradictions = detect_contradictions(&claims);
        assert_eq!(contradictions.len(), 1);
        assert!(contradictions[0].diagnosis.contains("window"));
    }

    #[test]
    fn identical_claims_do_not_conflict() {
        let claims = vec![
            AgentClaim {
                agent: "a".to_string(),
                claim: "cpk=1.42".to_string(),
                evidence_refs: vec!["cap:1".to_string()],
                window: None,
            },
            AgentClaim {
                agent: "b".to_string(),
                claim: "cpk=1.42".to_string(),
                evidence_refs: vec!["cap:1".to_string()],
                window: None,
            },
        ];
        assert!(detect_contradictions(&claims).is_empty());
    }
}

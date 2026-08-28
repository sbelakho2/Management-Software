//! Tool specifications with security semantics (items 94-95).
//!
//! The model gets TOOLS, never database access: every tool declares its
//! risk, the permission it requires, its schemas, timeout, row limits,
//! idempotency and approval policy. A prompt is never the security
//! boundary — this registry is.

use serde::{Deserialize, Serialize};

/// Risk classification of a tool (item 95).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum ToolRisk {
    /// Read/calculate only — never mutates state.
    ReadOnly,
    /// Low-risk, reversible write (create a task, raise an Andon).
    LowRiskWrite,
    /// Controlled write (requires matching user permission).
    ControlledWrite,
    /// High-risk write (approval gate required).
    HighRisk,
    /// Never autonomous — prohibited for LLM execution.
    ProhibitedAutonomous,
}

/// When an action may execute.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ApprovalPolicy {
    /// Executes immediately (permission check passed).
    Automatic,
    /// Requires an explicit human approval record.
    Required,
    /// Denied for agent execution (human-only operation).
    Denied,
}

/// A registered tool the agent may call (item 95).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolSpec {
    pub name: String,
    pub version: u32,
    pub risk: ToolRisk,
    /// Permission the CALLER must hold (checked by the policy engine
    /// against the server-created AgentContext, never against model
    /// claims).
    pub required_permission: String,
    /// JSON Schema of the inputs (compact).
    pub input_schema: serde_json::Value,
    /// JSON Schema of the outputs.
    pub output_schema: serde_json::Value,
    pub timeout_ms: u64,
    /// Maximum rows returned to the model context.
    pub max_rows: usize,
    /// Deterministic idempotency key support (agent retries never
    /// duplicate).
    pub idempotent: bool,
    pub approval_policy: ApprovalPolicy,
}

impl ToolSpec {
    pub fn read_only(
        name: &str,
        required_permission: &str,
        input_schema: serde_json::Value,
        output_schema: serde_json::Value,
    ) -> Self {
        Self {
            name: name.to_string(),
            version: 1,
            risk: ToolRisk::ReadOnly,
            required_permission: required_permission.to_string(),
            input_schema,
            output_schema,
            timeout_ms: 10_000,
            max_rows: 500,
            idempotent: true,
            approval_policy: ApprovalPolicy::Automatic,
        }
    }
}

/// Which tools a caller may see/use (items 100-101): user permissions
/// intersect the agent's toolset and the current policy ceiling.
#[derive(Debug, Clone)]
pub struct PolicyEngine {
    /// Tools registered for this agent.
    tools: Vec<ToolSpec>,
    /// Maximum risk the agent may execute autonomously.
    risk_ceiling: ToolRisk,
}

impl PolicyEngine {
    pub fn new(tools: Vec<ToolSpec>, risk_ceiling: ToolRisk) -> Self {
        Self {
            tools,
            risk_ceiling,
        }
    }

    /// Tools the caller may use: permission must match AND the risk must
    /// be within the ceiling (an operator with read-only rights never sees
    /// write tools; a quality engineer without journal permission never
    /// sees the posting tool — the agent inherits, never widens).
    pub fn effective_tools(&self, ctx: &crate::context::AgentContext) -> Vec<&ToolSpec> {
        self.tools
            .iter()
            .filter(|t| {
                ctx.can(&t.required_permission)
                    && t.risk <= self.risk_ceiling
                    && t.approval_policy != ApprovalPolicy::Denied
            })
            .collect()
    }

    /// Whether an execution attempt is permitted for this caller.
    pub fn can_execute(&self, ctx: &crate::context::AgentContext, tool: &ToolSpec) -> bool {
        ctx.can(&tool.required_permission) && tool.risk <= self.risk_ceiling
    }

    /// Whether the action needs an approval record before execution.
    pub fn approval_required(&self, tool: &ToolSpec) -> bool {
        tool.approval_policy == ApprovalPolicy::Required || tool.risk >= ToolRisk::HighRisk
    }

    pub fn all_tools(&self) -> &[ToolSpec] {
        &self.tools
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::AgentContext;
    use uuid::Uuid;

    fn ctx(perms: &[&str]) -> AgentContext {
        AgentContext {
            tenant_id: Uuid::new_v4(),
            user_id: Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec![],
            permissions: perms.iter().map(|s| s.to_string()).collect(),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: Uuid::new_v4(),
            conversation_id: None,
        }
    }

    fn tools() -> Vec<ToolSpec> {
        vec![
            ToolSpec::read_only(
                "get_work_order",
                "production:work-order:read",
                serde_json::json!({"id": "uuid"}),
                serde_json::json!({"work_order": "object"}),
            ),
            ToolSpec {
                name: "post_journal_entry".to_string(),
                version: 1,
                risk: ToolRisk::ControlledWrite,
                required_permission: "finance:journal:post".to_string(),
                input_schema: serde_json::json!({}),
                output_schema: serde_json::json!({}),
                timeout_ms: 10_000,
                max_rows: 100,
                idempotent: true,
                approval_policy: ApprovalPolicy::Required,
            },
        ]
    }

    #[test]
    fn operator_sees_only_their_tools() {
        let engine = PolicyEngine::new(tools(), ToolRisk::ReadOnly);
        let effective = engine.effective_tools(&ctx(&["production:work-order:read"]));
        assert_eq!(effective.len(), 1);
        assert_eq!(effective[0].name, "get_work_order");
    }

    #[test]
    fn agent_never_widens_rights() {
        let engine = PolicyEngine::new(tools(), ToolRisk::ControlledWrite);
        // The caller has NO finance permission: the posting tool is
        // invisible even though the agent's own toolset contains it.
        let effective = engine.effective_tools(&ctx(&["production:work-order:read"]));
        assert!(effective.iter().all(|t| t.name != "post_journal_entry"));
    }

    #[test]
    fn approval_required_for_high_risk() {
        let engine = PolicyEngine::new(tools(), ToolRisk::ControlledWrite);
        let journal = engine
            .all_tools()
            .iter()
            .find(|t| t.name == "post_journal_entry")
            .unwrap();
        assert!(engine.approval_required(journal));
    }

    #[test]
    fn denied_tools_never_execute() {
        let mut ts = tools();
        ts.push(ToolSpec {
            name: "release_quarantine".to_string(),
            version: 1,
            risk: ToolRisk::ProhibitedAutonomous,
            required_permission: "quality:release".to_string(),
            input_schema: serde_json::json!({}),
            output_schema: serde_json::json!({}),
            timeout_ms: 10_000,
            max_rows: 100,
            idempotent: false,
            approval_policy: ApprovalPolicy::Denied,
        });
        let engine = PolicyEngine::new(ts, ToolRisk::HighRisk);
        assert!(engine
            .effective_tools(&ctx(&["quality:release"]))
            .iter()
            .all(|t| t.name != "release_quarantine"));
    }
}

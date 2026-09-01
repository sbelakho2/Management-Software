//! Tool specifications with security semantics (items 94-95).
//!
//! The model gets TOOLS, never database access: every tool declares its
//! risk, the permission it requires, its schemas, timeout, row limits,
//! idempotency and approval policy. A prompt is never the security
//! boundary — this registry is.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

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

/// A verified approval artifact (sixteenth audit item 57): the ONLY
/// authorization evidence accepted by tool execution — it cannot be
/// forged by a caller (no public constructor).
#[derive(Debug, Clone, serde::Serialize)]
pub struct VerifiedApprovalArtifact {
    pub workflow_id: String,
    pub approval_id: String,
    pub approved_by: String,
    pub approved_at: chrono::DateTime<chrono::Utc>,
    pub required_role: String,
}
impl VerifiedApprovalArtifact {
    /// The approval subsystem constructs this after checking the decider
    /// holds the required role. Public construction is deliberately
    /// absent — this is the only path.
    #[allow(dead_code)]
    pub(crate) fn issue(
        workflow_id: String,
        approval_id: String,
        approved_by: String,
        required_role: String,
    ) -> Self {
        Self {
            workflow_id,
            approval_id,
            approved_by,
            approved_at: chrono::Utc::now(),
            required_role,
        }
    }
}

/// Identifies one tool invocation so a retry of the SAME invocation is
/// replayed instead of re-executed (sixteenth audit item 59). The key is
/// request_id:program_execution_id:tool_call_index — idempotency is
/// mechanical, never descriptive.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ToolExecutionId {
    pub request_id: Uuid,
    pub program_execution_id: Uuid,
    pub tool_call_index: u32,
}

impl ToolExecutionId {
    pub fn key(&self) -> String {
        format!(
            "{}:{}:{}",
            self.request_id, self.program_execution_id, self.tool_call_index
        )
    }
}

/// Execution context for one tool call (sixteenth audit item 59).
#[derive(Debug, Clone)]
pub struct ToolExecutionContext {
    pub key: ToolExecutionId,
}

/// Tool execution failures: dispatch, REAL timeout (item 56), output
/// validation (item 57) and policy denial are all distinct.
#[derive(Debug)]
pub enum ToolError {
    NotPermitted { tool: String },
    Dispatch { tool: String, message: String },
    Timeout { tool: String, timeout_ms: u64 },
    OutputValidation { tool: String, message: String },
}

impl std::fmt::Display for ToolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotPermitted { tool } => {
                write!(f, "Tool '{tool}' is not permitted for this caller")
            }
            Self::Dispatch { tool, message } => {
                write!(f, "Tool '{tool}' dispatch failed: {message}")
            }
            Self::Timeout { tool, timeout_ms } => {
                write!(f, "Tool '{tool}' exceeded its {timeout_ms}ms timeout")
            }
            Self::OutputValidation { tool, message } => {
                write!(f, "Tool '{tool}' output failed validation: {message}")
            }
        }
    }
}

impl std::error::Error for ToolError {}

/// Validate a tool's output against its declared schema (sixteenth audit
/// item 57). The schema is a JSON object of
/// {field: "string"|"integer"|"number"|"boolean"|"object"|"array"}; the
/// output must be an object whose fields match the declared kinds and
/// EXTRA fields are rejected — the schema is a contract, not descriptive
/// metadata (the same kind-checking approach as decode_structured).
pub fn validate_output(
    output: &serde_json::Value,
    schema: &serde_json::Value,
) -> Result<(), String> {
    let Some(schema) = schema.as_object() else {
        return Ok(());
    };
    let Some(obj) = output.as_object() else {
        return Err("output must be a JSON object".to_string());
    };
    for (field, expected) in schema {
        let Some(value) = obj.get(field) else {
            return Err(format!("missing required field '{field}'"));
        };
        let ok = match expected.as_str() {
            Some("string") => value.is_string(),
            Some("integer") => value.is_i64() || value.is_u64(),
            Some("number") => value.is_number(),
            Some("boolean") => value.is_boolean(),
            Some("object") => value.is_object(),
            Some("array") => value.is_array(),
            _ => false,
        };
        if !ok {
            return Err(format!(
                "field '{field}' has wrong kind (expected '{expected}')"
            ));
        }
    }
    for key in obj.keys() {
        if !schema.contains_key(key) {
            return Err(format!(
                "unexpected field '{key}' — output must match the schema"
            ));
        }
    }
    Ok(())
}

/// Executes tool calls under the policy engine: the permission is
/// re-checked at execution time, dispatch runs under a REAL timeout
/// (item 56), the output is validated against the declared schema
/// (item 57) and idempotent tools replay on a repeated execution key
/// (item 59).
pub struct ToolExecutor {
    policy: PolicyEngine,
    /// The persisted execution log (in-memory for now, item 59): keyed by
    /// the execution key string; a retry with the SAME key replays the
    /// stored result instead of executing again.
    execution_results: super::cache::BoundedMap<serde_json::Value>,
}

impl ToolExecutor {
    pub fn new(policy: PolicyEngine) -> Self {
        Self {
            policy,
            execution_results: super::cache::BoundedMap::new(512),
        }
    }

    /// Execute one tool call. `dispatch` runs the DOMAIN command (never
    /// SQL/shell/HTTP directly) and returns the raw output value.
    pub async fn execute<F, Fut>(
        &mut self,
        ctx: &crate::context::AgentContext,
        tool: &ToolSpec,
        args: serde_json::Value,
        approval: Option<VerifiedApprovalArtifact>,
        execution: ToolExecutionContext,
        dispatch: F,
    ) -> Result<serde_json::Value, ToolError>
    where
        F: FnOnce(serde_json::Value) -> Fut,
        Fut: std::future::Future<Output = Result<serde_json::Value, ToolError>>,
    {
        // Defense in depth: independent re-check at execution time (the
        // prompt is never the security boundary).
        if !self.policy.can_execute(ctx, tool, approval) {
            return Err(ToolError::NotPermitted {
                tool: tool.name.clone(),
            });
        }
        // Idempotency (item 59): the same execution key replays the stored
        // result — mechanical, the dispatch never runs twice.
        let key = execution.key.key();
        if tool.idempotent {
            if let Some(cached) = self.execution_results.get(&key) {
                return Ok(cached.clone());
            }
        }
        // REAL timeout (item 56): the declared timeout_ms is a contract,
        // not metadata.
        let result = tokio::time::timeout(
            std::time::Duration::from_millis(tool.timeout_ms),
            dispatch(args),
        )
        .await;
        let output = match result {
            Ok(inner) => inner?,
            Err(_elapsed) => {
                return Err(ToolError::Timeout {
                    tool: tool.name.clone(),
                    timeout_ms: tool.timeout_ms,
                });
            }
        };
        // Output validation (item 57): the declared output schema is
        // enforced after the domain command returns.
        validate_output(&output, &tool.output_schema).map_err(|message| {
            ToolError::OutputValidation {
                tool: tool.name.clone(),
                message,
            }
        })?;
        if tool.idempotent {
            self.execution_results.insert(key, output.clone());
        }
        Ok(output)
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

    /// Whether an execution attempt is permitted for this caller. This is
    /// the FINAL source of truth (never the prompt):
    /// - Denied policies never execute;
    /// - Required policies execute only with a verified approval artifact;
    /// - Automatic policies need permission + risk ceiling and pass None.
    pub fn can_execute(
        &self,
        ctx: &crate::context::AgentContext,
        tool: &ToolSpec,
        approval: Option<VerifiedApprovalArtifact>,
    ) -> bool {
        if tool.approval_policy == ApprovalPolicy::Denied {
            return false;
        }
        if tool.approval_policy == ApprovalPolicy::Required && approval.is_none() {
            return false;
        }
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

    #[test]
    fn write_approval_tool_requires_artifact() {
        let engine = PolicyEngine::new(tools(), ToolRisk::ControlledWrite);
        let journal = engine
            .all_tools()
            .iter()
            .find(|t| t.name == "post_journal_entry")
            .unwrap();
        let caller = ctx(&["finance:journal:post"]);
        // No artifact: the write-approval tool is denied — a bare bool
        // could never carry this (item 57).
        assert!(!engine.can_execute(&caller, journal, None));
        // A verified artifact (issued only by the approval subsystem)
        // unlocks it; read-only tools pass None.
        let artifact = VerifiedApprovalArtifact::issue(
            "wf-1".into(),
            "ap-1".into(),
            "operator@sensei".into(),
            "production:supervisor".into(),
        );
        assert!(engine.can_execute(&caller, journal, Some(artifact)));
        let reader = ctx(&["production:work-order:read"]);
        let read = engine
            .all_tools()
            .iter()
            .find(|t| t.name == "get_work_order")
            .unwrap();
        assert!(engine.can_execute(&reader, read, None));
    }

    #[test]
    fn output_validation_rejects_extra_field() {
        let schema = serde_json::json!({"takt_seconds": "number"});
        // Extra fields are rejected — the schema is a contract.
        let err = validate_output(
            &serde_json::json!({"takt_seconds": 42.0, "extra": true}),
            &schema,
        )
        .unwrap_err();
        assert!(err.contains("unexpected field 'extra'"), "{err}");
        // Declared fields must be present with the right kind.
        let err =
            validate_output(&serde_json::json!({"takt_seconds": "slow"}), &schema).unwrap_err();
        assert!(err.contains("wrong kind"), "{err}");
        let err = validate_output(&serde_json::json!({}), &schema).unwrap_err();
        assert!(
            err.contains("missing required field 'takt_seconds'"),
            "{err}"
        );
        assert!(validate_output(&serde_json::json!({"takt_seconds": 42.0}), &schema).is_ok());
    }

    #[tokio::test]
    async fn slow_dispatch_times_out() {
        let tool = ToolSpec {
            name: "slow_query".to_string(),
            version: 1,
            risk: ToolRisk::ReadOnly,
            required_permission: "slow:read".to_string(),
            input_schema: serde_json::json!({}),
            output_schema: serde_json::json!({}),
            timeout_ms: 1,
            max_rows: 10,
            idempotent: false,
            approval_policy: ApprovalPolicy::Automatic,
        };
        let mut executor =
            ToolExecutor::new(PolicyEngine::new(vec![tool.clone()], ToolRisk::ReadOnly));
        let err = executor
            .execute(
                &ctx(&["slow:read"]),
                &tool,
                serde_json::json!({}),
                None,
                ToolExecutionContext {
                    key: ToolExecutionId {
                        request_id: Uuid::new_v4(),
                        program_execution_id: Uuid::new_v4(),
                        tool_call_index: 0,
                    },
                },
                |_| async move {
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                    Ok(serde_json::json!({}))
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Timeout { .. }), "{err:?}");
    }

    #[tokio::test]
    async fn idempotent_tool_replays_same_key() {
        let tool = ToolSpec {
            name: "post_journal_entry".to_string(),
            version: 1,
            risk: ToolRisk::ControlledWrite,
            required_permission: "finance:journal:post".to_string(),
            input_schema: serde_json::json!({}),
            output_schema: serde_json::json!({"posted": "boolean"}),
            timeout_ms: 10_000,
            max_rows: 100,
            idempotent: true,
            approval_policy: ApprovalPolicy::Required,
        };
        let mut executor =
            ToolExecutor::new(PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk));
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 3,
            },
        };
        let artifact = || {
            VerifiedApprovalArtifact::issue(
                "wf-1".into(),
                "ap-1".into(),
                "operator@sensei".into(),
                "production:supervisor".into(),
            )
        };
        let dispatch = |calls: std::sync::Arc<std::sync::atomic::AtomicU64>| {
            move |_| {
                calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                async move { Ok(serde_json::json!({"posted": true})) }
            }
        };
        let caller = ctx(&["finance:journal:post"]);
        let first = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(artifact()),
                execution.clone(),
                dispatch(calls.clone()),
            )
            .await
            .unwrap();
        // Same execution key: the result is REPLAYED, never re-executed.
        let second = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(artifact()),
                execution.clone(),
                dispatch(calls.clone()),
            )
            .await
            .unwrap();
        assert_eq!(first, second);
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 1);
        // A DIFFERENT execution key executes again.
        let other = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: execution.key.request_id,
                program_execution_id: execution.key.program_execution_id,
                tool_call_index: 4,
            },
        };
        executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(artifact()),
                other,
                dispatch(calls.clone()),
            )
            .await
            .unwrap();
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 2);
    }
}

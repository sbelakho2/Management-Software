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
/// validation (item 57), policy denial and idempotency conflict
/// (nineteenth audit P1) are all distinct.
#[derive(Debug)]
pub enum ToolError {
    NotPermitted {
        tool: String,
    },
    Dispatch {
        tool: String,
        message: String,
    },
    Timeout {
        tool: String,
        timeout_ms: u64,
    },
    OutputValidation {
        tool: String,
        message: String,
    },
    /// The execution key is already claimed and still in progress — a
    /// concurrent duplicate of a mutating tool must NEVER re-execute.
    Conflict {
        tool: String,
        message: String,
    },
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
            Self::Conflict { tool, message } => {
                write!(f, "Tool '{tool}' is already executing: {message}")
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
    /// The bounded RAM replay map (performance cache — it may forget).
    execution_results: super::cache::BoundedMap<serde_json::Value>,
    /// The DURABLE system of record (eighteenth audit P1-14, nineteenth
    /// audit P1): when configured, reserve() atomically claims the key
    /// before every idempotent execution and complete() transitions the
    /// row to a terminal status afterwards — a retry (or a concurrent
    /// duplicate) replays the journaled outcome even after the RAM entry
    /// was evicted, and the mutation never runs twice. For mutating
    /// tools a failed journal write fails the execution: the cache may
    /// forget, the journal may not.
    journal: Option<std::sync::Arc<dyn super::journal::ExecutionJournal>>,
}

impl ToolExecutor {
    pub fn new(policy: PolicyEngine) -> Self {
        Self {
            policy,
            execution_results: super::cache::BoundedMap::new(512),
            journal: None,
        }
    }

    pub fn with_journal(
        policy: PolicyEngine,
        journal: std::sync::Arc<dyn super::journal::ExecutionJournal>,
    ) -> Self {
        Self {
            policy,
            execution_results: super::cache::BoundedMap::new(512),
            journal: Some(journal),
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
        // Idempotency (item 59 + nineteenth audit P1): the DURABLE
        // journal is a CLAIM STATE MACHINE. reserve() atomically claims
        // the key — exactly one concurrent caller wins and dispatches;
        // every loser replays the completed result, replays the recorded
        // failure, or gets a Conflict while the claim is in progress.
        // The dispatch never runs twice. The RAM cache is a performance
        // cache only (it may forget); with no journal configured the
        // RAM-cache behavior is unchanged.
        let key = execution.key.key();
        if tool.idempotent {
            if let Some(journal) = &self.journal {
                let claim = journal
                    .reserve(ctx.tenant_id, &key, &tool.name)
                    .await
                    .map_err(|message| ToolError::Dispatch {
                        tool: tool.name.clone(),
                        message: format!("command journal reserve failed: {message}"),
                    })?;
                if claim == super::journal::ReservationOutcome::AlreadyExists {
                    let (status, result) = journal
                        .load(ctx.tenant_id, &key)
                        .await
                        .map_err(|message| ToolError::Dispatch {
                            tool: tool.name.clone(),
                            message: format!("command journal load failed: {message}"),
                        })?
                        .ok_or_else(|| ToolError::Dispatch {
                            tool: tool.name.clone(),
                            message: "command journal inconsistency: key exists but no row"
                                .to_string(),
                        })?;
                    return match status.as_str() {
                        "succeeded" => Ok(result),
                        "failed" => {
                            let message = result
                                .get("error")
                                .and_then(|e| e.as_str())
                                .map(str::to_string)
                                .unwrap_or_else(|| "command previously failed".to_string());
                            Err(ToolError::Dispatch {
                                tool: tool.name.clone(),
                                message,
                            })
                        }
                        _ => Err(ToolError::Conflict {
                            tool: tool.name.clone(),
                            message: "command already in progress".to_string(),
                        }),
                    };
                }
            }
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
            Ok(inner) => inner,
            Err(_elapsed) => {
                // A timed-out mutating dispatch may still have taken
                // effect: record the failure so a retry replays it and
                // NEVER re-executes.
                if tool.idempotent {
                    if let Some(journal) = &self.journal {
                        let _ = journal
                            .complete(
                                ctx.tenant_id,
                                &key,
                                "failed",
                                &serde_json::json!({
                                    "error": format!(
                                        "Tool '{}' exceeded its {}ms timeout",
                                        tool.name, tool.timeout_ms
                                    )
                                }),
                            )
                            .await;
                    }
                }
                return Err(ToolError::Timeout {
                    tool: tool.name.clone(),
                    timeout_ms: tool.timeout_ms,
                });
            }
        };
        let output = match output {
            Ok(output) => output,
            Err(dispatch_err) => {
                // Same direction: a failed dispatch is recorded as
                // 'failed' so a retry replays the failure instead of
                // re-executing (the side effect may be ambiguous).
                if tool.idempotent {
                    if let Some(journal) = &self.journal {
                        let _ = journal
                            .complete(
                                ctx.tenant_id,
                                &key,
                                "failed",
                                &serde_json::json!({ "error": dispatch_err.to_string() }),
                            )
                            .await;
                    }
                }
                return Err(dispatch_err);
            }
        };
        // Output validation (item 57): the declared output schema is
        // enforced after the domain command returns. A validation
        // failure means the mutation already took effect: record the
        // row as 'failed' so a retry replays it and NEVER re-executes.
        if let Err(message) = validate_output(&output, &tool.output_schema) {
            if tool.idempotent {
                if let Some(journal) = &self.journal {
                    let _ = journal
                        .complete(
                            ctx.tenant_id,
                            &key,
                            "failed",
                            &serde_json::json!({
                                "error": format!(
                                    "Tool '{}' output failed validation: {message}",
                                    tool.name
                                )
                            }),
                        )
                        .await;
                }
            }
            return Err(ToolError::OutputValidation {
                tool: tool.name.clone(),
                message,
            });
        }
        if tool.idempotent {
            self.execution_results.insert(key.clone(), output.clone());
            // The journal write is part of correctness for mutating
            // tools: a failed 'succeeded' write FAILS the execution so
            // the record never silently disappears.
            if let Some(journal) = &self.journal {
                journal
                    .complete(ctx.tenant_id, &key, "succeeded", &output)
                    .await
                    .map_err(|message| ToolError::Dispatch {
                        tool: tool.name.clone(),
                        message: format!("command journal complete failed: {message}"),
                    })?;
            }
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

    /// In-memory journal for the state-machine tests. The Mutex makes
    /// reserve() atomic exactly like the Postgres unique constraint —
    /// two concurrent claims cannot both win.
    #[derive(Default)]
    struct MemoryJournal {
        rows: std::sync::Arc<
            std::sync::Mutex<std::collections::HashMap<String, (String, serde_json::Value)>>,
        >,
        fail_reserve: std::sync::Arc<std::sync::Mutex<bool>>,
        fail_complete: std::sync::Arc<std::sync::Mutex<bool>>,
        completes: std::sync::Arc<std::sync::Mutex<u64>>,
    }

    impl MemoryJournal {
        fn key(tenant: Uuid, key: &str) -> String {
            format!("{tenant}|{key}")
        }
        fn state(&self, tenant: Uuid, key: &str) -> (String, serde_json::Value) {
            self.rows
                .lock()
                .unwrap()
                .get(&Self::key(tenant, key))
                .cloned()
                .unwrap()
        }
    }

    impl crate::journal::ExecutionJournal for MemoryJournal {
        fn reserve(
            &self,
            tenant: Uuid,
            key: &str,
            _tool: &str,
        ) -> std::pin::Pin<
            Box<
                dyn std::future::Future<Output = Result<crate::journal::ReservationOutcome, String>>
                    + Send
                    + '_,
            >,
        > {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            let fail = self.fail_reserve.clone();
            Box::pin(async move {
                if *fail.lock().unwrap() {
                    return Err("reserve failed".to_string());
                }
                let mut rows = rows.lock().unwrap();
                match rows.entry(key) {
                    std::collections::hash_map::Entry::Occupied(_) => {
                        Ok(crate::journal::ReservationOutcome::AlreadyExists)
                    }
                    std::collections::hash_map::Entry::Vacant(v) => {
                        v.insert(("reserved".to_string(), serde_json::json!({})));
                        Ok(crate::journal::ReservationOutcome::Fresh)
                    }
                }
            })
        }

        fn load(
            &self,
            tenant: Uuid,
            key: &str,
        ) -> std::pin::Pin<
            Box<
                dyn std::future::Future<
                        Output = Result<Option<(String, serde_json::Value)>, String>,
                    > + Send
                    + '_,
            >,
        > {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            Box::pin(async move { Ok(rows.lock().unwrap().get(&key).cloned()) })
        }

        fn complete(
            &self,
            tenant: Uuid,
            key: &str,
            status: &str,
            result: &serde_json::Value,
        ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>>
        {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            let fail = self.fail_complete.clone();
            let completes = self.completes.clone();
            let status = status.to_string();
            let result = result.clone();
            Box::pin(async move {
                if *fail.lock().unwrap() {
                    return Err("complete failed".to_string());
                }
                *completes.lock().unwrap() += 1;
                rows.lock().unwrap().insert(key, (status, result));
                Ok(())
            })
        }
    }

    fn mutating_tool() -> ToolSpec {
        ToolSpec {
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
        }
    }

    fn approval() -> VerifiedApprovalArtifact {
        VerifiedApprovalArtifact::issue(
            "wf-1".into(),
            "ap-1".into(),
            "operator@sensei".into(),
            "production:supervisor".into(),
        )
    }

    #[tokio::test]
    async fn journal_replays_succeeded_without_redispatch() {
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 0,
            },
        };
        let dispatch = |calls: std::sync::Arc<std::sync::atomic::AtomicU64>| {
            move |_| {
                calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                async move { Ok(serde_json::json!({"posted": true})) }
            }
        };
        let first = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                dispatch(calls.clone()),
            )
            .await
            .unwrap();
        assert_eq!(
            journal.state(caller.tenant_id, &execution.key.key()).0,
            "succeeded"
        );
        // Same key: reserve -> AlreadyExists -> load('succeeded') ->
        // replay. Dispatch does NOT run again and complete is NOT
        // re-issued.
        let completes_before = *journal.completes.lock().unwrap();
        let second = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                dispatch(calls.clone()),
            )
            .await
            .unwrap();
        assert_eq!(first, second);
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 1);
        assert_eq!(*journal.completes.lock().unwrap(), completes_before);
    }

    #[tokio::test]
    async fn journal_conflicts_while_claim_in_progress() {
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 1,
            },
        };
        // Pre-seed a 'reserved' row: a concurrent duplicate must never
        // re-execute — it gets a Conflict instead.
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(caller.tenant_id, &execution.key.key()),
            ("reserved".to_string(), serde_json::json!({})),
        );
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let err = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": true})) }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Conflict { .. }), "{err:?}");
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn journal_replays_recorded_failure() {
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 2,
            },
        };
        // Pre-seed a 'failed' row: the retry replays the stored failure
        // and never re-executes.
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(caller.tenant_id, &execution.key.key()),
            (
                "failed".to_string(),
                serde_json::json!({"error": "posting denied by GL rules"}),
            ),
        );
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let err = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": true})) }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Dispatch { .. }), "{err:?}");
        assert!(
            err.to_string().contains("posting denied by GL rules"),
            "{err}"
        );
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn journal_reserve_error_fails_execution() {
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        *journal.fail_reserve.lock().unwrap() = true;
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 3,
            },
        };
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        // A journal that cannot be reserved must NEVER degrade into
        // "no prior execution; go ahead".
        let err = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": true})) }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Dispatch { .. }), "{err:?}");
        assert!(err.to_string().contains("reserve failed"), "{err}");
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn journal_complete_error_fails_mutating_execution() {
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        *journal.fail_complete.lock().unwrap() = true;
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 4,
            },
        };
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        // The mutation ran, but the system of record could not be
        // updated: the execution FAILS — the journal may not forget.
        let err = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": true})) }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Dispatch { .. }), "{err:?}");
        assert!(err.to_string().contains("complete failed"), "{err}");
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn journal_dispatch_failure_records_failed() {
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 5,
            },
        };
        // The dispatch failed: the row must transition to 'failed' so a
        // retry replays the failure instead of re-executing.
        let err = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| async move {
                    Err(ToolError::Dispatch {
                        tool: "post_journal_entry".to_string(),
                        message: "GL posting lock".to_string(),
                    })
                },
            )
            .await
            .unwrap_err();
        assert!(err.to_string().contains("GL posting lock"), "{err}");
        let (status, result) = journal.state(caller.tenant_id, &execution.key.key());
        assert_eq!(status, "failed");
        assert_eq!(
            result["error"].as_str(),
            Some("Tool 'post_journal_entry' dispatch failed: GL posting lock")
        );
    }

    #[tokio::test]
    async fn concurrent_identical_requests_execute_once() {
        // The nineteenth-audit core property: two concurrent identical
        // requests share one journal — reserve() lets exactly one claim
        // the key; the loser replays the completed result or conflicts.
        // The mutation runs exactly once.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 6,
            },
        };
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let dispatch = |calls: std::sync::Arc<std::sync::atomic::AtomicU64>| {
            move |_| {
                calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                async move { Ok(serde_json::json!({"posted": true})) }
            }
        };
        let mut executor_a = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let mut executor_b = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let (a, b) = tokio::join!(
            executor_a.execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                dispatch(calls.clone()),
            ),
            executor_b.execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                dispatch(calls.clone()),
            ),
        );
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "mutation must run exactly once"
        );
        assert!(a.is_ok() || b.is_ok());
        assert_eq!(
            journal.state(caller.tenant_id, &execution.key.key()).0,
            "succeeded"
        );
    }
}

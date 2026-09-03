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

/// The boxed dispatch future of a registered tool handler. It mirrors the
/// journal trait's boxed-future pattern exactly (std future, no
/// async-trait): the future is allowed to borrow the execution context,
/// the tool and the arguments it was called with for as long as it runs.
pub type ToolHandlerFuture<'a> = std::pin::Pin<
    Box<dyn std::future::Future<Output = Result<serde_json::Value, ToolError>> + Send + 'a>,
>;

/// A REGISTERED tool dispatch handler (twenty-seventh audit P1): the
/// domain implementation of ONE tool registry (the API's per-tool-name
/// match, the agent-core read-only dispatch table, ...) behind the single
/// ToolExecutor execution state machine. The executor owns the policy
/// re-check, the durable journal claim dance (reserve -> begin_dispatch
/// -> dispatch -> complete) and the REAL timeout; the handler owns ONLY
/// the domain dispatch: it validates the arguments, enforces the caller's
/// scope and maps the domain result into the declared output-schema JSON.
/// `dispatch` receives the execution context (for journaling-aware
/// handlers), the tool spec and the arguments, and returns the raw output
/// value the same way the executor's generic dispatch closure does.
pub trait ToolHandler: Send + Sync {
    fn dispatch<'a>(
        &'a self,
        execution: &'a ToolExecutionContext,
        tool: &'a ToolSpec,
        args: &'a serde_json::Value,
    ) -> ToolHandlerFuture<'a>;
}

/// Executes tool calls under the policy engine: the permission is
/// re-checked at execution time, dispatch runs under a REAL timeout
/// (item 56), the output is validated against the declared schema
/// (item 57) and idempotent tools replay on a repeated execution key
/// (item 59).
pub struct ToolExecutor<'h> {
    policy: PolicyEngine,
    /// The bounded RAM replay map (performance cache — it may forget).
    execution_results: super::cache::BoundedMap<serde_json::Value>,
    /// The DURABLE system of record (eighteenth audit P1-14, nineteenth
    /// audit P1, twentieth audit P1, twenty-first audit item 8,
    /// twenty-seventh audit P0): when configured, reserve() atomically
    /// claims the key with THIS worker as claim_owner plus a lease and a
    /// fencing token, leaving the row 'reserved' — provably never
    /// dispatched. The mutation runs ONLY after begin_dispatch() has
    /// durably transitioned the row to 'dispatching' (the DURABLE
    /// PRE-DISPATCH GATE); complete() records the outcome afterwards —
    /// a retry (or a concurrent duplicate) replays the journaled outcome
    /// even after the RAM entry was evicted, and the mutation never runs
    /// twice while a claim is live. recover() reclaims ONLY a
    /// pre-mutation crash: an EXPIRED 'reserved' row (never dispatched);
    /// the recovered claim must pass the begin_dispatch gate again. A
    /// row that reached 'dispatching'/'executing' before a crash is
    /// NEVER auto-redispatched: lease expiry marks it
    /// 'reconcile_required' (the mutation MAY have happened) and it
    /// Conflicts until a human reconciles it. An ambiguous
    /// ('unknown_outcome'/'reconcile_required') row is likewise never
    /// auto-redispatched. A stale owner is fenced by the claim token.
    /// For mutating tools a failed journal write fails the execution:
    /// the cache may forget, the journal may not.
    journal: Option<std::sync::Arc<dyn super::journal::ExecutionJournal>>,
    /// Identity of this worker/process instance — the claim_owner recorded
    /// on every reserve()/recover(). Fencing itself is TOKEN-based; the
    /// owner is the human-readable side of a claim.
    claim_owner: String,
    /// The REGISTERED dispatch handler (twenty-seventh audit P1): when
    /// present it is the dispatch authority for execute()/execute_handler()
    /// — the internal/read-only or generic-closure dispatch is only used
    /// when no handler is registered. The lifetime 'h covers the state the
    /// handler borrows (services, caller context), so one executor can own
    /// a handler that dispatches against borrowed infrastructure.
    handler: Option<std::sync::Arc<dyn ToolHandler + 'h>>,
}

impl<'h> ToolExecutor<'h> {
    fn claim_owner() -> String {
        format!("executor:{}", Uuid::new_v4())
    }

    pub fn new(policy: PolicyEngine) -> Self {
        Self {
            policy,
            execution_results: super::cache::BoundedMap::new(512),
            journal: None,
            claim_owner: Self::claim_owner(),
            handler: None,
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
            claim_owner: Self::claim_owner(),
            handler: None,
        }
    }

    /// Register the dispatch handler WITHOUT a durable journal (the RAM
    /// replay cache remains the only idempotency store, exactly like
    /// `new()`'s no-journal path). Twenty-seventh audit P1: the caller
    /// (e.g. the API service layer) provides the domain dispatch and the
    /// executor stays the single execution state machine.
    pub fn with_handler(
        policy: PolicyEngine,
        handler: std::sync::Arc<dyn ToolHandler + 'h>,
    ) -> Self {
        Self {
            policy,
            execution_results: super::cache::BoundedMap::new(512),
            journal: None,
            claim_owner: Self::claim_owner(),
            handler: Some(handler),
        }
    }

    /// Register the dispatch handler together with the DURABLE journal —
    /// the single execution state machine (reserve -> begin_dispatch ->
    /// dispatch -> complete) that the API tool path and the core read-only
    /// table both run through. Twenty-seventh audit P1.
    pub fn with_journal_and_handler(
        policy: PolicyEngine,
        journal: std::sync::Arc<dyn super::journal::ExecutionJournal>,
        handler: std::sync::Arc<dyn ToolHandler + 'h>,
    ) -> Self {
        Self {
            policy,
            execution_results: super::cache::BoundedMap::new(512),
            journal: Some(journal),
            claim_owner: Self::claim_owner(),
            handler: Some(handler),
        }
    }

    /// Execute one tool call through the REGISTERED handler (twenty-seventh
    /// audit P1): the single execution state machine is ToolExecutor — the
    /// journal key/claim logic, policy re-check, REAL timeout and output
    /// validation live ONLY here. The handler is called for dispatch with
    /// the execution context, the tool spec and the arguments. Returns a
    /// Dispatch error when no handler is registered.
    pub async fn execute_handler(
        &mut self,
        ctx: &crate::context::AgentContext,
        tool: &ToolSpec,
        args: serde_json::Value,
        approval: Option<VerifiedApprovalArtifact>,
        execution: ToolExecutionContext,
    ) -> Result<serde_json::Value, ToolError> {
        let Some(handler) = self.handler.clone() else {
            return Err(ToolError::Dispatch {
                tool: tool.name.clone(),
                message: "no registered tool handler".to_string(),
            });
        };
        // The adapter owns clones of the handler inputs so the boxed
        // dispatch future needs no borrows from this frame; the handler is
        // invoked (and awaited) INSIDE the dispatch the state machine
        // times out, exactly like the generic dispatch closure path.
        let execution_for_dispatch = execution.clone();
        let tool_for_dispatch = tool.clone();
        let dispatch = move |args: serde_json::Value| {
            let handler = handler.clone();
            let execution = execution_for_dispatch.clone();
            let tool = tool_for_dispatch.clone();
            async move { handler.dispatch(&execution, &tool, &args).await }
        };
        self.execute_inner(ctx, tool, args, approval, execution, dispatch)
            .await
    }

    /// Execute one tool call. `dispatch` runs the DOMAIN command (never
    /// SQL/shell/HTTP directly) and returns the raw output value. When a
    /// handler is REGISTERED it is the dispatch authority and the generic
    /// `dispatch` closure is not used; without a handler the closure is
    /// the dispatch (the internal read-only table use).
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
        if self.handler.is_some() {
            return self
                .execute_handler(ctx, tool, args, approval, execution)
                .await;
        }
        self.execute_inner(ctx, tool, args, approval, execution, dispatch)
            .await
    }

    /// Execute one tool call. `dispatch` runs the DOMAIN command (never
    /// SQL/shell/HTTP directly) and returns the raw output value. This is
    /// the ONE execution state machine every dispatch path funnels into:
    /// policy re-check -> durable journal claim dance (reserve ->
    /// begin_dispatch gate -> complete) or RAM replay -> REAL timeout ->
    /// output validation.
    async fn execute_inner<F, Fut>(
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
        // Idempotency (item 59 + nineteenth audit P1 + twentieth audit
        // P1 + twenty-first audit item 8 + twenty-seventh audit P0): the
        // DURABLE journal is a CLAIM STATE MACHINE with LEASES and
        // FENCING TOKENS. reserve() atomically claims the key — exactly
        // one concurrent caller wins and reaches the DURABLE
        // PRE-DISPATCH GATE: the mutation runs ONLY after begin_dispatch()
        // durably moved the row 'reserved' → 'dispatching' (a crash after
        // that gate can never masquerade as a clean pre-mutation crash).
        // Every loser:
        // - replays the terminal outcome ('succeeded'/'failed');
        // - Conflicts while the claim is leased
        //   ('reserved'/'dispatching'/'executing' under a live lease —
        //   the mutation may be in flight);
        // - Conflicts on an ambiguous outcome
        //   ('unknown_outcome'/'reconcile_required') — the mutation MAY
        //   have happened, so automatic re-dispatch is BLOCKED and a
        //   human must reconcile the row;
        // - recover()s a PRE-MUTATION crash only (an EXPIRED 'reserved'
        //   row — never dispatched) and re-dispatches ONCE more through
        //   the begin_dispatch gate (the attempt bump is journal-side).
        //   An EXPIRED 'dispatching'/'executing' row is NEVER reclaimed:
        //   recover() marks it 'reconcile_required' (never
        //   re-dispatched automatically).
        // complete() is token-fenced: a stale owner whose claim was
        // recovered can never confirm an outcome. The RAM cache is a
        // performance cache only (it may forget); with no journal
        // configured the RAM-cache behavior is unchanged.
        let key = execution.key.key();
        if tool.idempotent {
            if let Some(journal) = self.journal.clone() {
                // The lease must outlive the dispatch (bounded by the
                // tool's REAL timeout) so an in-flight claim is never
                // stolen mid-dispatch; 300s floor keeps the crash-recovery
                // window sane for short tools.
                let lease_seconds = 300 + (tool.timeout_ms / 1000) as i64;
                let claim_owner = self.claim_owner.clone();
                let claim = journal
                    .reserve(ctx.tenant_id, &key, &tool.name, &claim_owner, lease_seconds)
                    .await
                    .map_err(|message| ToolError::Dispatch {
                        tool: tool.name.clone(),
                        message: format!("command journal reserve failed: {message}"),
                    })?;
                return match claim {
                    super::journal::ReservationOutcome::Fresh { claim_token } => {
                        // This caller won the claim: dispatch and record
                        // the outcome under the fencing token.
                        self.dispatch_claimed(ctx, tool, &key, args, journal, claim_token, dispatch)
                            .await
                    }
                    super::journal::ReservationOutcome::AlreadyExists => {
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
                        match status.as_str() {
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
                            // Twenty-first audit item 8: an ambiguous
                            // outcome means the mutating command MAY
                            // have happened — NEVER auto-redispatch
                            // (NO recover + dispatch): the retry
                            // Conflicts and a human must reconcile
                            // the row.
                            "unknown_outcome" | "reconcile_required" => Err(ToolError::Conflict {
                                tool: tool.name.clone(),
                                message: "ambiguous outcome — requires reconciliation; \
                                         automatic re-dispatch is blocked"
                                    .to_string(),
                            }),
                            // 'reserved'/'dispatching'/'executing' under
                            // a LIVE lease -> Conflict (recover()
                            // refuses); an EXPIRED 'reserved' row — a
                            // pre-mutation crash, provably never
                            // dispatched — is reclaimable: recover()
                            // reclaims atomically and we re-dispatch ONCE
                            // more, always through the begin_dispatch
                            // gate. An EXPIRED 'dispatching'/'executing'
                            // row is NEVER reclaimed: recover() marks it
                            // 'reconcile_required' and we Conflict.
                            _ => {
                                match journal
                                    .recover(
                                        ctx.tenant_id,
                                        &key,
                                        &claim_owner,
                                        lease_seconds,
                                    )
                                    .await
                                {
                                    Ok(Some(claim_token)) => {
                                        self.dispatch_claimed(
                                            ctx, tool, &key, args, journal, claim_token, dispatch,
                                        )
                                        .await
                                    }
                                    Ok(None) => Err(ToolError::Conflict {
                                        tool: tool.name.clone(),
                                        message: "command already in progress (lease held by another worker)"
                                            .to_string(),
                                    }),
                                    Err(message) => Err(ToolError::Dispatch {
                                        tool: tool.name.clone(),
                                        message: format!(
                                            "command journal recover failed: {message}"
                                        ),
                                    }),
                                }
                            }
                        }
                    }
                };
            }
            if let Some(cached) = self.execution_results.get(&key) {
                return Ok(cached.clone());
            }
        }
        // REAL timeout (item 56): the declared timeout_ms is a contract,
        // not metadata. This tail is the NO-JOURNAL path — the RAM cache
        // behavior stays as-is.
        let result = tokio::time::timeout(
            std::time::Duration::from_millis(tool.timeout_ms),
            dispatch(args),
        )
        .await;
        let output = match result {
            Ok(inner) => inner,
            Err(_elapsed) => {
                return Err(ToolError::Timeout {
                    tool: tool.name.clone(),
                    timeout_ms: tool.timeout_ms,
                });
            }
        };
        let output = match output {
            Ok(output) => output,
            Err(dispatch_err) => return Err(dispatch_err),
        };
        // Output validation (item 57): the declared output schema is
        // enforced after the domain command returns.
        if let Err(message) = validate_output(&output, &tool.output_schema) {
            return Err(ToolError::OutputValidation {
                tool: tool.name.clone(),
                message,
            });
        }
        if tool.idempotent {
            self.execution_results.insert(key, output.clone());
        }
        Ok(output)
    }

    /// Dispatch a CLAIMED execution and record the outcome under the
    /// fencing `claim_token` (journal-configured path only — called after
    /// reserve() won or recover() reclaimed). The mutation NEVER runs
    /// unless the DURABLE PRE-DISPATCH GATE passed first
    /// (twenty-seventh audit P0): begin_dispatch() durably transitions
    /// the claim 'reserved' → 'dispatching' (token- and lease-checked)
    /// and only an Ok(true) lets dispatch proceed — a crash or
    /// terminal-write failure afterwards leaves the row 'dispatching',
    /// which is never auto-redispatched (expired 'dispatching' rows are
    /// marked 'reconcile_required' by recover()). Ok(false) means the
    /// row is no longer beginnable under this token (recovered by
    /// another worker or the lease expired): dispatch MUST NOT run and
    /// the caller Conflicts. Then:
    /// - dispatch success -> complete('succeeded'); the journal write is
    ///   part of correctness for mutating tools, so a failed 'succeeded'
    ///   write FAILS the execution (and a fenced/superseded owner also
    ///   fails here — it must never confirm an outcome it no longer owns);
    /// - a timeout after dispatch (retryable) -> complete('unknown_outcome'):
    ///   the mutation MAY have happened, so this is a reconciliation
    ///   state, NOT a plain 'failed'. A later retry NEVER auto-redispatches
    ///   it (twenty-first audit item 8) — the row Conflicts until a human
    ///   reconciles it;
    /// - deterministic dispatch errors -> complete('failed');
    /// - output-validation errors -> complete('failed').
    #[allow(clippy::too_many_arguments)]
    async fn dispatch_claimed<F, Fut>(
        &mut self,
        ctx: &crate::context::AgentContext,
        tool: &ToolSpec,
        key: &str,
        args: serde_json::Value,
        journal: std::sync::Arc<dyn super::journal::ExecutionJournal>,
        claim_token: String,
        dispatch: F,
    ) -> Result<serde_json::Value, ToolError>
    where
        F: FnOnce(serde_json::Value) -> Fut,
        Fut: std::future::Future<Output = Result<serde_json::Value, ToolError>>,
    {
        // Twenty-seventh audit P0: the DURABLE PRE-DISPATCH GATE.
        // reserve()/recover() left the row 'reserved' — provably never
        // dispatched. The mutation may run ONLY after the claim durably
        // transitioned to 'dispatching'; a refusal (row no longer
        // 'reserved', token mismatch — the claim was recovered by
        // another worker — or expired lease) means this caller must NOT
        // dispatch: a Conflict keeps the command safe.
        let began = journal
            .begin_dispatch(ctx.tenant_id, key, &claim_token)
            .await
            .map_err(|message| ToolError::Dispatch {
                tool: tool.name.clone(),
                message: format!("command journal begin_dispatch failed: {message}"),
            })?;
        if !began {
            return Err(ToolError::Conflict {
                tool: tool.name.clone(),
                message: "cannot begin dispatch — the claim is no longer 'reserved' under \
                          this token (stale claim or expired lease); automatic re-dispatch \
                          is blocked, reconcile the row before retrying"
                    .to_string(),
            });
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
                // A network timeout AFTER dispatch: the mutation may
                // already have taken effect — record 'unknown_outcome'
                // (a reconciliation state). Item 8: a later retry NEVER
                // auto-redispatches this row — it Conflicts until a
                // human reconciles the outcome. Twenty-sixth audit P0.3
                // (kept under the twenty-seventh-audit P0 gate): a
                // journal that cannot record that reconciliation state
                // must NOT be swallowed — the execution then fails with
                // an explicit ambiguous/conflict error (never a
                // retryable Timeout that could look like a clean
                // pre-mutation crash once the lease expires) instead of
                // hiding that the mutation's fate is unrecorded. The row
                // itself is durably 'dispatching' (the pre-dispatch gate
                // already passed), so it is never auto-redispatched.
                journal
                    .complete(
                        ctx.tenant_id,
                        key,
                        &claim_token,
                        "unknown_outcome",
                        &serde_json::json!({
                            "error": format!(
                                "Tool '{}' exceeded its {}ms timeout",
                                tool.name, tool.timeout_ms
                            )
                        }),
                    )
                    .await
                    .map_err(|message| ToolError::Conflict {
                        tool: tool.name.clone(),
                        message: format!(
                            "ambiguous outcome — the command journal failed to record \
                             'unknown_outcome' after a timeout: {message}; automatic \
                             re-dispatch is blocked, reconcile the row before retrying"
                        ),
                    })?;
                return Err(ToolError::Timeout {
                    tool: tool.name.clone(),
                    timeout_ms: tool.timeout_ms,
                });
            }
        };
        let output = match output {
            Ok(output) => output,
            Err(dispatch_err) => {
                // A retryable timeout error means the mutation's fate is
                // unknown ('unknown_outcome' — a human reconciles it,
                // never an auto-redispatch); any other dispatch error is
                // a deterministic 'failed' so a retry replays it instead
                // of re-executing.
                let status = if matches!(dispatch_err, ToolError::Timeout { .. }) {
                    "unknown_outcome"
                } else {
                    "failed"
                };
                // Twenty-sixth audit P0.3 (kept under the
                // twenty-seventh-audit P0 gate): the terminal write is
                // part of correctness — when the journal cannot record
                // the dispatch outcome, the execution fails with an
                // explicit ambiguous/conflict error (the mutation's fate
                // is unknown without the row) instead of silently
                // returning the dispatch error. The row itself is
                // durably 'dispatching', so it can never be mistaken for
                // a clean pre-mutation crash.
                journal
                    .complete(
                        ctx.tenant_id,
                        key,
                        &claim_token,
                        status,
                        &serde_json::json!({ "error": dispatch_err.to_string() }),
                    )
                    .await
                    .map_err(|message| ToolError::Conflict {
                        tool: tool.name.clone(),
                        message: format!(
                            "ambiguous outcome — the command journal failed to record \
                             '{status}' after a dispatch error ({dispatch_err}): {message}; \
                             automatic re-dispatch is blocked, reconcile the row before retrying"
                        ),
                    })?;
                return Err(dispatch_err);
            }
        };
        // Output validation (item 57): the declared output schema is
        // enforced after the domain command returns. A validation failure
        // means the mutation already took effect: record the row as
        // 'failed' so a retry replays it and NEVER re-executes.
        if let Err(message) = validate_output(&output, &tool.output_schema) {
            // Twenty-sixth audit P0.3 (kept under the
            // twenty-seventh-audit P0 gate): the 'failed' write is part
            // of correctness — when the journal cannot record it, the
            // execution fails with an explicit ambiguous/conflict error
            // (the mutation already took effect but the row cannot prove
            // so) instead of silently returning the validation error.
            // The row itself is durably 'dispatching', so it can never
            // be mistaken for a clean pre-mutation crash.
            journal
                .complete(
                    ctx.tenant_id,
                    key,
                    &claim_token,
                    "failed",
                    &serde_json::json!({
                        "error": format!(
                            "Tool '{}' output failed validation: {message}",
                            tool.name
                        )
                    }),
                )
                .await
                .map_err(|complete_err| ToolError::Conflict {
                    tool: tool.name.clone(),
                    message: format!(
                        "ambiguous outcome — the command journal failed to record 'failed' \
                         after an output-validation failure ({message}): {complete_err}; \
                         automatic re-dispatch is blocked, reconcile the row before retrying"
                    ),
                })?;
            return Err(ToolError::OutputValidation {
                tool: tool.name.clone(),
                message,
            });
        }
        self.execution_results
            .insert(key.to_string(), output.clone());
        // The journal write is part of correctness for mutating tools: a
        // failed 'succeeded' write FAILS the execution so the record never
        // silently disappears. Token fencing also means a stale owner
        // whose claim was recovered gets an error here instead of
        // confirming an outcome it no longer owns.
        journal
            .complete(ctx.tenant_id, key, &claim_token, "succeeded", &output)
            .await
            .map_err(|message| ToolError::Dispatch {
                tool: tool.name.clone(),
                message: format!("command journal complete failed: {message}"),
            })?;
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
    use crate::journal::ExecutionJournal;
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

    /// One in-memory journal row, faithful to the Postgres lease model:
    /// a status, the claim owner/token, the lease expiry (None when
    /// terminal or never leased) and the lease window for renewal.
    #[derive(Clone, Debug)]
    struct MemoryRow {
        status: String,
        result: serde_json::Value,
        claim_owner: Option<String>,
        claim_token: Option<String>,
        lease_expires_at: Option<chrono::DateTime<chrono::Utc>>,
        lease_seconds: i64,
        attempt: u32,
    }

    impl MemoryRow {
        fn reserved(token: &str) -> Self {
            Self {
                status: "reserved".to_string(),
                result: serde_json::json!({}),
                claim_owner: None,
                claim_token: Some(token.to_string()),
                lease_expires_at: None,
                lease_seconds: 300,
                attempt: 1,
            }
        }
        fn lease(mut self, expires_at: Option<chrono::DateTime<chrono::Utc>>) -> Self {
            self.lease_expires_at = expires_at;
            self
        }
    }

    /// In-memory journal for the state-machine tests. The Mutex makes
    /// reserve() atomic exactly like the Postgres unique constraint —
    /// two concurrent claims cannot both win.
    #[derive(Default)]
    struct MemoryJournal {
        rows: std::sync::Arc<std::sync::Mutex<std::collections::HashMap<String, MemoryRow>>>,
        fail_reserve: std::sync::Arc<std::sync::Mutex<bool>>,
        fail_complete: std::sync::Arc<std::sync::Mutex<bool>>,
        completes: std::sync::Arc<std::sync::Mutex<u64>>,
    }

    impl MemoryJournal {
        fn key(tenant: Uuid, key: &str) -> String {
            format!("{tenant}|{key}")
        }
        fn state(&self, tenant: Uuid, key: &str) -> (String, serde_json::Value) {
            let row = self
                .rows
                .lock()
                .unwrap()
                .get(&Self::key(tenant, key))
                .cloned()
                .unwrap();
            (row.status, row.result)
        }
        fn row(&self, tenant: Uuid, key: &str) -> MemoryRow {
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
            claim_owner: &str,
            lease_seconds: i64,
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
            let claim_owner = claim_owner.to_string();
            Box::pin(async move {
                if *fail.lock().unwrap() {
                    return Err("reserve failed".to_string());
                }
                let claim_token = format!("tok-{}", Uuid::new_v4());
                let mut rows = rows.lock().unwrap();
                match rows.entry(key) {
                    std::collections::hash_map::Entry::Occupied(_) => {
                        Ok(crate::journal::ReservationOutcome::AlreadyExists)
                    }
                    std::collections::hash_map::Entry::Vacant(v) => {
                        v.insert(MemoryRow {
                            status: "reserved".to_string(),
                            result: serde_json::json!({}),
                            claim_owner: Some(claim_owner),
                            claim_token: Some(claim_token.clone()),
                            lease_expires_at: Some(
                                chrono::Utc::now() + chrono::Duration::seconds(lease_seconds),
                            ),
                            lease_seconds,
                            attempt: 1,
                        });
                        Ok(crate::journal::ReservationOutcome::Fresh { claim_token })
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
            Box::pin(async move {
                let rows = rows.lock().unwrap();
                Ok(rows
                    .get(&key)
                    .map(|row| (row.status.clone(), row.result.clone())))
            })
        }

        fn heartbeat(
            &self,
            tenant: Uuid,
            key: &str,
            claim_token: &str,
        ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<bool, String>> + Send + '_>>
        {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            let claim_token = claim_token.to_string();
            Box::pin(async move {
                let mut rows = rows.lock().unwrap();
                let Some(row) = rows.get_mut(&key) else {
                    return Ok(false);
                };
                // Fencing: only the CURRENT owner of a live leased claim
                // may renew.
                if row.claim_token.as_deref() != Some(claim_token.as_str())
                    || !matches!(
                        row.status.as_str(),
                        "reserved" | "dispatching" | "executing"
                    )
                    || row
                        .lease_expires_at
                        .is_none_or(|expires| expires < chrono::Utc::now())
                {
                    return Ok(false);
                }
                row.lease_expires_at =
                    Some(chrono::Utc::now() + chrono::Duration::seconds(row.lease_seconds));
                Ok(true)
            })
        }

        fn begin_dispatch(
            &self,
            tenant: Uuid,
            key: &str,
            claim_token: &str,
        ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<bool, String>> + Send + '_>>
        {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            let claim_token = claim_token.to_string();
            Box::pin(async move {
                let mut rows = rows.lock().unwrap();
                let Some(row) = rows.get_mut(&key) else {
                    return Ok(false);
                };
                // Twenty-seventh audit P0: the DURABLE PRE-DISPATCH GATE
                // (mirrors the Postgres predicate) — the row must still
                // be 'reserved' (provably never dispatched), the token
                // must match and the lease must be live. Only then does
                // the row durably move to 'dispatching' and dispatch may
                // run.
                if row.status != "reserved"
                    || row.claim_token.as_deref() != Some(claim_token.as_str())
                    || row
                        .lease_expires_at
                        .is_none_or(|expires| expires < chrono::Utc::now())
                {
                    return Ok(false);
                }
                row.status = "dispatching".to_string();
                Ok(true)
            })
        }

        fn recover(
            &self,
            tenant: Uuid,
            key: &str,
            claim_owner: &str,
            lease_seconds: i64,
        ) -> std::pin::Pin<
            Box<dyn std::future::Future<Output = Result<Option<String>, String>> + Send + '_>,
        > {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            let claim_owner = claim_owner.to_string();
            Box::pin(async move {
                let mut rows = rows.lock().unwrap();
                let Some(row) = rows.get_mut(&key) else {
                    return Ok(None);
                };
                let now = chrono::Utc::now();
                let claim_gone = row.lease_expires_at.is_none_or(|expires| expires < now);
                if row.status == "reserved" && claim_gone {
                    // Twenty-seventh audit P0 (mirrors the Postgres
                    // predicate): recover() reclaims ONLY an EXPIRED
                    // 'reserved' row — it has provably never been
                    // dispatched, so re-dispatching once more (attempt
                    // bump, fresh token + lease) is safe. The row STAYS
                    // 'reserved': the new owner must still pass
                    // begin_dispatch() before any dispatch. Ambiguous
                    // rows ('unknown_outcome'/'reconcile_required') and
                    // rows under a LIVE lease are never matched.
                    let claim_token = format!("tok-{}", Uuid::new_v4());
                    row.result = serde_json::json!({});
                    row.claim_owner = Some(claim_owner);
                    row.claim_token = Some(claim_token.clone());
                    row.lease_expires_at = Some(now + chrono::Duration::seconds(lease_seconds));
                    row.lease_seconds = lease_seconds;
                    row.attempt += 1;
                    return Ok(Some(claim_token));
                }
                if matches!(row.status.as_str(), "dispatching" | "executing") && claim_gone {
                    // An EXPIRED (or lease-less) 'dispatching'/'executing'
                    // row means the mutation MAY already have happened —
                    // NEVER auto-reclaim it (twenty-seventh audit P0).
                    // Mark it 'reconcile_required' and clear the claim
                    // (fencing the stale owner out): a human reconciles.
                    row.status = "reconcile_required".to_string();
                    row.result = serde_json::json!({
                        "error": "lease expired while the command was dispatching/executing — \
                                  the mutation may have happened; automatic re-dispatch is \
                                  blocked, reconcile the row before retrying"
                    });
                    row.claim_owner = None;
                    row.claim_token = None;
                    row.lease_expires_at = None;
                    return Ok(None);
                }
                Ok(None)
            })
        }

        fn complete(
            &self,
            tenant: Uuid,
            key: &str,
            claim_token: &str,
            status: &str,
            result: &serde_json::Value,
        ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>>
        {
            let key = Self::key(tenant, key);
            let rows = self.rows.clone();
            let fail = self.fail_complete.clone();
            let completes = self.completes.clone();
            let claim_token = claim_token.to_string();
            let status = status.to_string();
            let result = result.clone();
            Box::pin(async move {
                if *fail.lock().unwrap() {
                    return Err("complete failed".to_string());
                }
                let mut rows = rows.lock().unwrap();
                let Some(row) = rows.get_mut(&key) else {
                    return Err(
                        "command journal complete failed: claim_token mismatch (stale owner fenced)"
                            .to_string(),
                    );
                };
                // Token fencing: a stale owner (claim recovered or already
                // completed -> token cleared) can never land a write.
                if row.claim_token.as_deref() != Some(claim_token.as_str()) {
                    return Err(
                        "command journal complete failed: claim_token mismatch (stale owner fenced)"
                            .to_string(),
                    );
                }
                *completes.lock().unwrap() += 1;
                row.status = status;
                row.result = result;
                row.claim_owner = None;
                row.claim_token = None;
                row.lease_expires_at = None;
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

    /// A seeded claim row for fault-injection (twenty-seventh audit P0):
    /// status/owner/token/lease under explicit control, attempt 1.
    fn leased_row(
        status: &str,
        token: &str,
        owner: &str,
        lease: Option<chrono::DateTime<chrono::Utc>>,
    ) -> MemoryRow {
        MemoryRow {
            status: status.to_string(),
            result: serde_json::json!({}),
            claim_owner: Some(owner.to_string()),
            claim_token: Some(token.to_string()),
            lease_expires_at: lease,
            lease_seconds: 300,
            attempt: 1,
        }
    }

    /// The execution context for a fresh tool_call_index.
    fn fresh_execution(tool_call_index: u32) -> ToolExecutionContext {
        ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index,
            },
        }
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
        // Pre-seed a 'reserved' row under a LIVE lease: a concurrent
        // duplicate must never re-execute — recover() refuses and the
        // duplicate gets a Conflict instead.
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(caller.tenant_id, &execution.key.key()),
            MemoryRow::reserved("worker-a-token")
                .lease(Some(chrono::Utc::now() + chrono::Duration::seconds(3600))),
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
            MemoryRow {
                status: "failed".to_string(),
                result: serde_json::json!({"error": "posting denied by GL rules"}),
                claim_owner: None,
                claim_token: None,
                lease_expires_at: None,
                lease_seconds: 300,
                attempt: 1,
            },
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
    async fn journal_failure_during_unknown_outcome_write_fails_execution() {
        // Twenty-sixth audit P0.3: when the journal store fails during
        // the 'unknown_outcome' write (here: the dispatch reports a
        // retryable timeout), execute() must return Err — never a silent
        // Ok — with the explicit ambiguous/conflict error, NOT the raw
        // (retryable-looking) timeout, so no caller can mistake the
        // un-recorded row for a clean pre-execution crash.
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
                tool_call_index: 9,
            },
        };
        // The journal store is DOWN for terminal writes.
        *journal.fail_complete.lock().unwrap() = true;
        let err = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| async move {
                    Err(ToolError::Timeout {
                        tool: "post_journal_entry".to_string(),
                        timeout_ms: 10_000,
                    })
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Conflict { .. }), "{err:?}");
        assert!(err.to_string().contains("ambiguous outcome"), "{err}");
        assert!(err.to_string().contains("unknown_outcome"), "{err}");
        assert!(err.to_string().contains("complete failed"), "{err}");
        // The row never reached a terminal state and the claim was never
        // released: it must NOT look 'failed'/'succeeded' to a replay.
        // Twenty-seventh audit P0: the row durably reached 'dispatching'
        // (the pre-dispatch gate passed BEFORE the mutation ran), so an
        // unrecorded outcome can never be mistaken for a clean
        // pre-mutation crash — on lease expiry recover() marks it
        // 'reconcile_required' instead of reclaiming it.
        let row = journal.row(caller.tenant_id, &execution.key.key());
        assert_eq!(row.status, "dispatching");
        assert!(row.claim_token.is_some());
    }

    #[tokio::test]
    async fn begin_dispatch_gate_succeeds_before_fresh_dispatch_runs() {
        // Twenty-seventh audit P0 fault injection (a): dispatch may run
        // ONLY after begin_dispatch() durably moved the fresh claim
        // 'reserved' -> 'dispatching'. The dispatch closure observes the
        // journal row at the MOMENT the mutation would run: a regression
        // that dispatches without the gate fails the assertion inside
        // the dispatch itself.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let mut executor = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(30);
        let execution_key = execution.key.key();
        let caller_tenant = caller.tenant_id;
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let dispatch_calls = calls.clone();
        let observe = journal.clone();
        let observed_key = execution_key.clone();
        let outcome = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
                move |_| {
                    dispatch_calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    let observe = observe.clone();
                    async move {
                        let (status, _) = observe.state(caller_tenant, &observed_key);
                        assert_eq!(
                            status, "dispatching",
                            "dispatch ran BEFORE the durable pre-dispatch gate"
                        );
                        Ok(serde_json::json!({"posted": true}))
                    }
                },
            )
            .await
            .unwrap();
        assert_eq!(outcome, serde_json::json!({"posted": true}));
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 1);
        assert_eq!(
            journal.state(caller.tenant_id, &execution_key).0,
            "succeeded"
        );
    }

    #[tokio::test]
    async fn begin_dispatch_refuses_stale_or_expired_claims() {
        // Twenty-seventh audit P0: the gate is token- AND lease-checked —
        // a wrong token, an expired lease, a row that already left
        // 'reserved' or a missing row all REFUSE (false) so dispatch can
        // never run on a claim this caller does not durably own.
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let tenant = Uuid::new_v4();
        let key = "gate|tenant";
        // Fresh claim by "owner-a": the gate passes with the right token
        // and the row durably moves to 'dispatching'...
        let fresh = journal
            .reserve(tenant, key, "post_journal_entry", "owner-a", 300)
            .await
            .unwrap();
        let crate::journal::ReservationOutcome::Fresh { claim_token } = fresh else {
            panic!("expected a fresh reservation");
        };
        assert!(
            !journal
                .begin_dispatch(tenant, key, "owner-b-token")
                .await
                .unwrap(),
            "a mismatched token must refuse the gate"
        );
        assert_eq!(
            journal.row(tenant, key).status,
            "reserved",
            "a refused gate must not transition the row"
        );
        assert!(
            journal
                .begin_dispatch(tenant, key, &claim_token)
                .await
                .unwrap(),
            "the current owner with a live lease passes the gate"
        );
        assert_eq!(journal.row(tenant, key).status, "dispatching");
        assert!(
            !journal
                .begin_dispatch(tenant, key, &claim_token)
                .await
                .unwrap(),
            "a row that already left 'reserved' must refuse the gate again"
        );
        // An expired lease refuses the gate even for the current owner...
        let second_key = "gate|expired";
        let fresh = journal
            .reserve(tenant, second_key, "post_journal_entry", "owner-a", 300)
            .await
            .unwrap();
        let crate::journal::ReservationOutcome::Fresh { claim_token } = fresh else {
            panic!("expected a fresh reservation");
        };
        journal
            .rows
            .lock()
            .unwrap()
            .get_mut(&MemoryJournal::key(tenant, second_key))
            .unwrap()
            .lease_expires_at = Some(chrono::Utc::now() - chrono::Duration::seconds(1));
        assert!(
            !journal
                .begin_dispatch(tenant, second_key, &claim_token)
                .await
                .unwrap(),
            "an expired lease must refuse the gate"
        );
        // ... and a missing row refuses too.
        assert!(!journal
            .begin_dispatch(tenant, "gate|absent", "whatever")
            .await
            .unwrap());
    }

    #[tokio::test]
    async fn expired_dispatching_and_executing_rows_are_never_reclaimed() {
        // Twenty-seventh audit P0 fault injection (b): a claim that
        // reached 'dispatching' (the gate passed — the mutation MAY have
        // run) or 'executing' is NEVER reclaimable once its lease
        // expires: recover() returns NO token and instead marks the row
        // 'reconcile_required' (claim cleared, attempt untouched) for a
        // human.
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let tenant = Uuid::new_v4();
        for (index, status) in ["dispatching", "executing"].into_iter().enumerate() {
            let key = format!("never-reclaim|{index}");
            journal.rows.lock().unwrap().insert(
                MemoryJournal::key(tenant, &key),
                leased_row(
                    status,
                    &format!("{status}-owner-token"),
                    "worker-a",
                    Some(chrono::Utc::now() - chrono::Duration::seconds(2)),
                ),
            );
            let recovered = journal
                .recover(tenant, &key, "worker-b", 300)
                .await
                .unwrap();
            assert!(recovered.is_none(), "{status}: no reclaim token allowed");
            let row = journal.row(tenant, &key);
            assert_eq!(row.status, "reconcile_required", "{status}");
            assert!(row.claim_token.is_none(), "{status}: claim cleared");
            assert_eq!(row.attempt, 1, "{status}: no reclaim happened");
            assert!(
                row.result["error"]
                    .as_str()
                    .is_some_and(|e| e.contains("automatic re-dispatch is blocked")),
                "{status}: the row must carry a reconcile marker"
            );
        }
    }

    #[tokio::test]
    async fn executor_conflicts_on_expired_dispatching_claim_and_marks_reconcile() {
        // Twenty-seventh audit P0 fault injection (b), executor-level: a
        // second worker on an EXPIRED 'dispatching' claim must Conflict —
        // recover() returns no token (recover marks the row
        // 'reconcile_required'), dispatch never runs again, and a later
        // attempt Conflicts with the reconciliation error.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(31);
        let key = execution.key.key();
        // Worker A's claim reached 'dispatching' (the gate passed — the
        // mutation may have run) and its lease then expired.
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(caller.tenant_id, &key),
            leased_row(
                "dispatching",
                "worker-a-token",
                "worker-a",
                Some(chrono::Utc::now() - chrono::Duration::seconds(2)),
            ),
        );
        let mut executor_b = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let err = executor_b
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": true})) }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Conflict { .. }), "{err:?}");
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            0,
            "an expired 'dispatching' claim is NEVER re-dispatched"
        );
        let row = journal.row(caller.tenant_id, &key);
        assert_eq!(row.status, "reconcile_required");
        assert_eq!(row.attempt, 1);
        assert!(row.claim_token.is_none());
        // A later attempt (or worker) now Conflicts on the reconciliation
        // state directly.
        let mut executor_c = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let err = executor_c
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
        assert!(err.to_string().contains("requires reconciliation"), "{err}");
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            0,
            "the ambiguous outcome is NEVER auto-redispatched"
        );
    }

    #[tokio::test]
    async fn in_flight_dispatching_claim_conflicts_untouched() {
        // The durable gate makes 'dispatching' the in-flight state: a
        // LIVE 'dispatching' lease (another worker mid-dispatch) must
        // Conflict without touching the row — recover() refuses and the
        // claim is left exactly as it was.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(32);
        let key = execution.key.key();
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(caller.tenant_id, &key),
            leased_row(
                "dispatching",
                "worker-a-token",
                "worker-a",
                Some(chrono::Utc::now() + chrono::Duration::seconds(3600)),
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
        assert!(matches!(err, ToolError::Conflict { .. }), "{err:?}");
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 0);
        let row = journal.row(caller.tenant_id, &key);
        assert_eq!(row.status, "dispatching", "the live claim is untouched");
        assert_eq!(row.attempt, 1);
        assert!(row.claim_token.is_some());
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

    fn short_timeout_mutating_tool() -> ToolSpec {
        ToolSpec {
            timeout_ms: 1,
            ..mutating_tool()
        }
    }

    #[tokio::test]
    async fn journal_timeout_records_unknown_outcome_and_blocks_redispatch() {
        // Twenty-first audit item 8: a network timeout AFTER dispatch
        // means the mutation MAY have happened — the row becomes
        // 'unknown_outcome' (a reconciliation state), NEVER a plain
        // retryable 'failed'. A later executor on the same key must NOT
        // auto-redispatch it: execute() returns a Conflict and the row
        // stays 'unknown_outcome' for a human to reconcile.
        let tool = short_timeout_mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 7,
            },
        };
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let mut executor_a = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        // Attempt 1: dispatch starts, hangs, and the REAL timeout fires —
        // the mutation may have gone through.
        let err = executor_a
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move {
                        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
                        Ok(serde_json::json!({"posted": true}))
                    }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Timeout { .. }), "{err:?}");
        let (status, result) = journal.state(caller.tenant_id, &execution.key.key());
        assert_eq!(status, "unknown_outcome");
        assert!(
            result["error"].as_str().unwrap().contains("exceeded"),
            "{result}"
        );
        // Attempt 2 (a retry or another worker): reserve -> AlreadyExists
        // -> load('unknown_outcome') -> Conflict. Dispatch does NOT run
        // again, recover() is never invoked, and the row is untouched —
        // it waits for human reconciliation.
        let mut executor_b = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let err = executor_b
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": true})) }
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, ToolError::Conflict { .. }), "{err:?}");
        assert!(err.to_string().contains("requires reconciliation"), "{err}");
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "the ambiguous outcome is NEVER auto-redispatched"
        );
        let row = journal.row(caller.tenant_id, &execution.key.key());
        assert_eq!(row.status, "unknown_outcome");
        assert_eq!(row.attempt, 1);
        assert!(row.claim_token.is_none());
    }

    #[tokio::test]
    async fn ambiguous_outcome_rows_never_auto_redispatch() {
        // Twenty-first audit item 8: 'unknown_outcome' AND
        // 'reconcile_required' rows mean the mutating command MAY have
        // happened. A retry must Conflict (NO recover + dispatch) for
        // both statuses — the row is left exactly as it was.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        for (index, status) in ["unknown_outcome", "reconcile_required"]
            .into_iter()
            .enumerate()
        {
            let execution = ToolExecutionContext {
                key: ToolExecutionId {
                    request_id: Uuid::new_v4(),
                    program_execution_id: Uuid::new_v4(),
                    tool_call_index: index as u32 + 20,
                },
            };
            journal.rows.lock().unwrap().insert(
                MemoryJournal::key(caller.tenant_id, &execution.key.key()),
                MemoryRow {
                    status: status.to_string(),
                    result: serde_json::json!({"error": "ambiguous"}),
                    claim_owner: None,
                    claim_token: None,
                    lease_expires_at: None,
                    lease_seconds: 300,
                    attempt: 1,
                },
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
                    execution.clone(),
                    |_| {
                        calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                        async move { Ok(serde_json::json!({"posted": true})) }
                    },
                )
                .await
                .unwrap_err();
            assert!(
                matches!(err, ToolError::Conflict { .. }),
                "{status}: {err:?}"
            );
            assert!(
                err.to_string().contains("requires reconciliation"),
                "{status}: {err}"
            );
            assert_eq!(
                calls.load(std::sync::atomic::Ordering::SeqCst),
                0,
                "{status}: dispatch must never run"
            );
            let row = journal.row(caller.tenant_id, &execution.key.key());
            assert_eq!(row.status, status);
            assert_eq!(row.attempt, 1, "{status}: recover must not have run");
            assert!(row.claim_token.is_none());
        }
    }

    #[tokio::test]
    async fn second_executor_recovers_expired_lease_and_completes() {
        // Crash-recovery (twentieth audit P1, narrowed by twenty-first
        // audit item 8 and twenty-seventh audit P0): recover() is ONLY
        // for a PRE-MUTATION crash — executor A reserved the key and
        // died before dispatching, so the row sits 'reserved' (provably
        // NEVER dispatched) with an EXPIRED lease and no heartbeat. A
        // second executor reclaims it atomically (recover -> attempt 2,
        // fresh token; the row STAYS 'reserved') and then MUST pass the
        // begin_dispatch gate before the mutation runs — the dispatch
        // closure asserts the row is durably 'dispatching' at the moment
        // the mutation would run. Dispatches exactly once; every later
        // attempt REPLAYS the completed outcome. Ambiguous-outcome rows
        // are NOT reclaimable (see the item-8 tests above), and an
        // expired 'dispatching'/'executing' row is never reclaimed
        // either (see the twenty-seventh-audit tests above). The stale
        // owner A can NEVER later complete or renew that claim —
        // fencing by claim_token.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let caller = ctx(&["finance:journal:post"]);
        let execution = ToolExecutionContext {
            key: ToolExecutionId {
                request_id: Uuid::new_v4(),
                program_execution_id: Uuid::new_v4(),
                tool_call_index: 8,
            },
        };
        let execution_key = execution.key.key();
        // A crashed after reserve(): 'reserved', lease already expired.
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(caller.tenant_id, &execution_key),
            MemoryRow::reserved("executor-a-crash-token")
                .lease(Some(chrono::Utc::now() - chrono::Duration::seconds(2))),
        );
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let dispatch_calls = calls.clone();
        let mut executor_b = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let observe = journal.clone();
        let caller_tenant = caller.tenant_id;
        let observed_key = execution_key.clone();
        let outcome = executor_b
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                move |_| {
                    dispatch_calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    let observe = observe.clone();
                    async move {
                        // The recovered claim must have passed the
                        // begin_dispatch gate BEFORE this mutation runs.
                        let (status, _) = observe.state(caller_tenant, &observed_key);
                        assert_eq!(
                            status, "dispatching",
                            "the recovered claim must pass the durable \
                             pre-dispatch gate before re-dispatching"
                        );
                        Ok(serde_json::json!({"posted": true}))
                    }
                },
            )
            .await
            .unwrap();
        assert_eq!(outcome, serde_json::json!({"posted": true}));
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "recovery dispatches exactly once"
        );
        let row = journal.row(caller.tenant_id, &execution_key);
        assert_eq!(row.status, "succeeded");
        assert_eq!(row.attempt, 2);
        // Fencing: stale executor A wakes up and tries to complete the
        // command with ITS old token — refused, and the row is untouched.
        let stale = journal
            .complete(
                caller.tenant_id,
                &execution_key,
                "executor-a-crash-token",
                "succeeded",
                &serde_json::json!({"posted": false}),
            )
            .await;
        assert!(stale.is_err(), "stale owner must be fenced: {stale:?}");
        assert!(stale.unwrap_err().contains("stale owner fenced"));
        let row = journal.row(caller.tenant_id, &execution_key);
        assert_eq!(row.status, "succeeded");
        assert_eq!(row.result["posted"], serde_json::json!(true));
        // A stale heartbeat is refused too.
        assert!(!journal
            .heartbeat(caller.tenant_id, &execution_key, "executor-a-crash-token")
            .await
            .unwrap());
        // A THIRD executor (fresh RAM cache — the replay must come from
        // the durable journal, not the cache) replays the terminal
        // outcome: the mutation NEVER runs again and no complete is
        // re-issued.
        let completes_before = *journal.completes.lock().unwrap();
        let mut executor_c = ToolExecutor::with_journal(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
        );
        let replayed = executor_c
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| {
                    calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    async move { Ok(serde_json::json!({"posted": false})) }
                },
            )
            .await
            .unwrap();
        assert_eq!(replayed, serde_json::json!({"posted": true}));
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "the recovered command dispatches exactly once ever"
        );
        assert_eq!(*journal.completes.lock().unwrap(), completes_before);
        let row = journal.row(caller.tenant_id, &execution_key);
        assert_eq!(row.status, "succeeded");
        assert_eq!(row.attempt, 2, "no further reclaim happened");
    }

    #[tokio::test]
    async fn journal_heartbeat_renews_only_current_owner() {
        // Heartbeat fencing: only the CURRENT claim owner renews the
        // lease; a stale token, an expired lease or a terminal row are
        // all refused.
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let tenant = Uuid::new_v4();
        let key = "tenant|request:1:2:3";
        journal.rows.lock().unwrap().insert(
            MemoryJournal::key(tenant, key),
            MemoryRow::reserved("owner-a")
                .lease(Some(chrono::Utc::now() + chrono::Duration::seconds(60))),
        );
        assert!(
            journal.heartbeat(tenant, key, "owner-a").await.unwrap(),
            "the current owner renews"
        );
        assert!(
            !journal.heartbeat(tenant, key, "owner-b").await.unwrap(),
            "a non-owner is refused"
        );
        // The lease expires: even the owner's heartbeat is refused (the
        // claim is up for recovery).
        journal
            .rows
            .lock()
            .unwrap()
            .get_mut(&MemoryJournal::key(tenant, key))
            .unwrap()
            .lease_expires_at = Some(chrono::Utc::now() - chrono::Duration::seconds(1));
        assert!(
            !journal.heartbeat(tenant, key, "owner-a").await.unwrap(),
            "an expired claim is refused"
        );
    }

    /// A REGISTERED dispatch handler for the twenty-seventh-audit P1
    /// tests: counts its invocations and returns a fixed, schema-conforming
    /// output (or the configured error).
    struct RecordingHandler {
        calls: std::sync::Arc<std::sync::atomic::AtomicU64>,
        fail_with: Option<String>,
    }

    impl super::ToolHandler for RecordingHandler {
        fn dispatch<'a>(
            &'a self,
            _execution: &'a ToolExecutionContext,
            tool: &'a ToolSpec,
            _args: &'a serde_json::Value,
        ) -> ToolHandlerFuture<'a> {
            let calls = self.calls.clone();
            let fail_with = self.fail_with.clone();
            let tool_name = tool.name.clone();
            Box::pin(async move {
                calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                match fail_with {
                    Some(message) => Err(ToolError::Dispatch {
                        tool: tool_name,
                        message,
                    }),
                    None => Ok(serde_json::json!({"posted": true})),
                }
            })
        }
    }

    #[tokio::test]
    async fn registered_handler_runs_the_single_journal_state_machine() {
        // Twenty-seventh audit P1: an executor built with
        // with_journal_and_handler() executes a registered handler through
        // the SAME reserve -> begin_dispatch -> dispatch -> complete state
        // machine as the generic dispatch closure: the first execution
        // records 'succeeded' and a retry of the same execution key
        // REPLAYS the journaled outcome without invoking the handler or
        // re-issuing a complete.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let handler = std::sync::Arc::new(RecordingHandler {
            calls: calls.clone(),
            fail_with: None,
        });
        let mut executor = ToolExecutor::with_journal_and_handler(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
            handler,
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(40);
        let first = executor
            .execute_handler(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
            )
            .await
            .unwrap();
        assert_eq!(first, serde_json::json!({"posted": true}));
        assert_eq!(
            journal.state(caller.tenant_id, &execution.key.key()).0,
            "succeeded"
        );
        let completes_before = *journal.completes.lock().unwrap();
        let second = executor
            .execute_handler(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
            )
            .await
            .unwrap();
        assert_eq!(first, second);
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "the replay must never re-dispatch the handler"
        );
        assert_eq!(
            *journal.completes.lock().unwrap(),
            completes_before,
            "the replay must never re-record the outcome"
        );
    }

    #[tokio::test]
    async fn registered_handler_failure_is_journaled_as_failed() {
        // Twenty-seventh audit P1: a deterministic handler failure passes
        // through the state machine and records the row 'failed', so a
        // retry replays the failure instead of re-executing.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let handler = std::sync::Arc::new(RecordingHandler {
            calls: calls.clone(),
            fail_with: Some("GL posting lock".to_string()),
        });
        let mut executor = ToolExecutor::with_journal_and_handler(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
            handler,
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(41);
        let err = executor
            .execute_handler(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
            )
            .await
            .unwrap_err();
        assert!(err.to_string().contains("GL posting lock"), "{err}");
        let (status, result) = journal.state(caller.tenant_id, &execution.key.key());
        assert_eq!(status, "failed");
        assert!(
            result["error"]
                .as_str()
                .is_some_and(|e| e.contains("GL posting lock")),
            "{result}"
        );
        // A retry replays the recorded failure — the handler never runs
        // again.
        let mut executor_b = ToolExecutor::with_journal_and_handler(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
            std::sync::Arc::new(RecordingHandler {
                calls: calls.clone(),
                fail_with: Some("GL posting lock".to_string()),
            }),
        );
        let err = executor_b
            .execute_handler(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
            )
            .await
            .unwrap_err();
        assert!(err.to_string().contains("GL posting lock"), "{err}");
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "the recorded failure is replayed, never re-executed"
        );
    }

    #[tokio::test]
    async fn registered_handler_replays_from_the_ram_cache_without_journal() {
        // Twenty-seventh audit P1: with_handler() (no durable journal)
        // keeps the executor's RAM-cache replay semantics for the
        // registered handler.
        let tool = mutating_tool();
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let handler = std::sync::Arc::new(RecordingHandler {
            calls: calls.clone(),
            fail_with: None,
        });
        let mut executor = ToolExecutor::with_handler(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            handler,
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(42);
        let first = executor
            .execute_handler(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
            )
            .await
            .unwrap();
        let second = executor
            .execute_handler(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution,
            )
            .await
            .unwrap();
        assert_eq!(first, second);
        assert_eq!(
            calls.load(std::sync::atomic::Ordering::SeqCst),
            1,
            "the RAM cache replays the same execution key"
        );
    }

    #[tokio::test]
    async fn registered_handler_authority_applies_to_execute_too() {
        // Twenty-seventh audit P1: when a handler is REGISTERED,
        // execute() dispatches through it — the generic dispatch closure
        // is never invoked.
        let tool = mutating_tool();
        let journal = std::sync::Arc::new(MemoryJournal::default());
        let calls = std::sync::Arc::new(std::sync::atomic::AtomicU64::new(0));
        let handler = std::sync::Arc::new(RecordingHandler {
            calls: calls.clone(),
            fail_with: None,
        });
        let mut executor = ToolExecutor::with_journal_and_handler(
            PolicyEngine::new(vec![tool.clone()], ToolRisk::HighRisk),
            journal.clone(),
            handler,
        );
        let caller = ctx(&["finance:journal:post"]);
        let execution = fresh_execution(43);
        let outcome = executor
            .execute(
                &caller,
                &tool,
                serde_json::json!({}),
                Some(approval()),
                execution.clone(),
                |_| async move {
                    panic!("the generic dispatch closure must not run when a handler is registered")
                },
            )
            .await
            .unwrap();
        assert_eq!(outcome, serde_json::json!({"posted": true}));
        assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 1);
        assert_eq!(
            journal.state(caller.tenant_id, &execution.key.key()).0,
            "succeeded"
        );
    }
}

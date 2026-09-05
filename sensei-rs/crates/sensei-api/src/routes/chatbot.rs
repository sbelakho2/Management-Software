//! Chatbot route handlers.
//!
//! Provides endpoints for conversational AI:
//! - `POST /api/v1/chat` — send a message and receive a response.
//! - `POST /api/v1/chat/stream` — SSE streaming endpoint.

use axum::{
    extract::State,
    response::{
        sse::{Event, Sse},
        Json,
    },
};
use futures::stream::Stream;
use sensei_agent_core::context::{
    AgentContext, Claim, ClaimAssertion, ClaimOperator, ContextItem, DerivedAssertion, FactAddress,
};
use sensei_agent_core::facts::RecomputedDerivation;
use sensei_agent_core::verifier::{parse_claim_time, verify_derived_claim, verify_measured_claim};
use sensei_auth::authz_snapshot::AuthzSnapshot;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_services::ai::chatbot::ChatSamplingParams;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use sqlx::PgPool;
use std::collections::{HashMap, HashSet};
use std::convert::Infallible;
use std::pin::Pin;
use std::task::{Context, Poll};
use tokio::task::JoinHandle;
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;
use tracing::error;

use crate::state::AppState;

/// The typed assertion of one structured claim (thirtieth audit item 23):
/// the deterministic address/operator/value/unit statement the verifier
/// checks against the typed evidence — language-independent. A measured
/// factual claim MUST carry one of these (or a [`DerivedClaimDraft`]).
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ClaimAssertionDraft {
    /// The object type of the fact address ("work_order", "andon", …).
    #[serde(default)]
    pub object_type: Option<String>,
    /// The object id of the fact address ("WO-123", …).
    #[serde(default)]
    pub object_id: Option<String>,
    /// The attribute the claim is about ("quantity_completed", …).
    #[serde(default)]
    pub attribute: Option<String>,
    /// The comparison operator; defaults to `equal` when omitted.
    #[serde(default)]
    pub operator: Option<ClaimOperator>,
    /// The claimed value.
    #[serde(default)]
    pub value: Option<serde_json::Value>,
    /// The unit of the claimed value ("units", "%", …).
    #[serde(default)]
    pub unit: Option<String>,
    /// The RFC3339 validity/observation instant the claim asserts.
    #[serde(default)]
    pub valid_time: Option<String>,
}

/// The derived-claim assertion of one structured claim (thirtieth audit
/// item 23): the server re-runs the deterministic derivation program
/// identified by `derivation_id` at `derivation_version` and the claimed
/// `result` must agree with the recomputation.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct DerivedClaimDraft {
    pub derivation_id: String,
    #[serde(default)]
    pub derivation_version: u32,
    /// Evidence ids of the operands the derivation rests on.
    #[serde(default)]
    pub operand_evidence_ids: Vec<String>,
    /// The claimed derived result.
    #[serde(default)]
    pub result: Option<serde_json::Value>,
    #[serde(default)]
    pub unit: Option<String>,
}

/// A structured claim the client asserts alongside its message (twenty-
/// seventh audit P1): the verifier checks each draft structurally, so
/// correctness never depends on English sentence heuristics (a French
/// claim is checked the same way as an English one). Since the twenty-
/// eighth audit P0-2 these drafts are SUPPLEMENTARY assertions only —
/// they are verified IN ADDITION to the reply's prose, never instead of
/// it, and the caller cannot weaken the check.
///
/// Thirtieth audit item 23: a MEASURED claim additionally carries a
/// typed [`ClaimAssertionDraft`] (address/operator/value/unit) or a
/// [`DerivedClaimDraft`] — an evidence id alone can never prove a value.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ClaimDraft {
    /// The claim statement as written (in any language).
    pub statement: String,
    /// Accepted for schema compatibility but IGNORED by the verifier
    /// (twenty-eighth audit P0-2): a caller cannot declare
    /// "assumed"/"recommended" to bypass the factual-claim check — every
    /// caller draft is verified like a measured claim. The server-side
    /// assumed/recommended recording concept is reserved for future
    /// model-generated claims, never for HTTP caller input.
    #[serde(default)]
    pub epistemic_kind: String,
    /// Optional structural address of the fact the claim refers to.
    #[serde(default)]
    pub fact_address: Option<String>,
    /// Kernel-issued evidence ids the client cites for this claim.
    #[serde(default)]
    pub evidence_ids: Vec<String>,
    /// The TYPED assertion of the measured claim (thirtieth audit item
    /// 23). Optional for qualitative legacy prose claims; REQUIRED for a
    /// claim to be measured against typed evidence.
    #[serde(default)]
    pub assertion: Option<ClaimAssertionDraft>,
    /// The derived-claim assertion (server-recomputed), when the claim
    /// asserts the result of a deterministic derivation.
    #[serde(default)]
    pub derived: Option<DerivedClaimDraft>,
}

/// Request body for a chat message.
#[derive(Debug, Deserialize)]
pub struct ChatRequest {
    /// The user's message text.
    pub message: String,
    /// Structured claims channel (twenty-seventh audit P1): caller-supplied
    /// claims the verifier checks STRUCTURALLY (language-independent).
    /// Twenty-eighth audit P0-2: they are SUPPLEMENTARY — verification of
    /// the generated reply's prose ALWAYS runs and these drafts are checked
    /// in addition, merged into the same claims/issues envelopes. A non-
    /// empty channel never replaces prose verification and never relaxes
    /// the factual-claim requirements.
    #[serde(default)]
    pub structured_claims: Vec<ClaimDraft>,
    /// Optional conversation ID to continue an existing conversation.
    pub conversation_id: Option<String>,
    /// Maximum number of tokens to generate (optional).
    pub max_tokens: Option<usize>,
    /// Sampling temperature (optional, 0.0 = greedy).
    pub temperature: Option<f32>,
    /// Top-k sampling parameter (optional, 0 = disabled).
    pub top_k: Option<u32>,
    /// Top-p (nucleus) sampling parameter (optional).
    pub top_p: Option<f32>,
    /// Server-built authoritative context bundle (sixteenth audit 8/96):
    /// the Context Kernel runs BEFORE generation and this field reports
    /// the compact live context that was used. Clients may supply their
    /// own value, but the server ALWAYS overrides it with the plan-driven
    /// bundle — the model never invents the retrieval strategy.
    #[serde(default)]
    pub system_context: Option<String>,
}

impl ChatRequest {
    /// The per-request sampling overrides, if any were provided.
    fn sampling_params(&self) -> Option<ChatSamplingParams> {
        if self.max_tokens.is_none()
            && self.temperature.is_none()
            && self.top_k.is_none()
            && self.top_p.is_none()
        {
            return None;
        }
        Some(ChatSamplingParams {
            max_tokens: self.max_tokens,
            temperature: self.temperature,
            top_k: self.top_k,
            top_p: self.top_p,
        })
    }
}

/// Response body for a chat message.
#[derive(Debug, serde::Serialize)]
pub struct ChatResponseBody {
    /// The assistant's response text.
    pub response: String,
    /// Unique conversation identifier.
    pub conversation_id: String,
    /// Whether this response was generated by fallback pattern matching.
    pub is_fallback: bool,
    /// The deterministic context plan (fifteenth audit 74): the required
    /// context sections for the caller's task — the model never invents
    /// the retrieval strategy.
    #[serde(default)]
    pub context_plan: Option<sensei_agent_core::context::ContextPlan>,
    /// The deterministic verification envelope: claims about live tenant
    /// data must carry evidence; this reports whether the response is
    /// decision-grade (the legacy assistant can no longer bypass the agent
    /// verification layer).
    #[serde(default)]
    pub verification: Option<serde_json::Value>,
    /// The compact authoritative context bundle that was fed INTO
    /// generation (sixteenth audit 8/96) — what the plan required and the
    /// kernel fetched before the model saw the prompt.
    #[serde(default)]
    pub context_used: Option<Vec<String>>,
    /// Whether the request's authorization snapshot was still current at
    /// generation time (sixteenth audit 5/24): the TOCTOU guard re-checks
    /// the revision triple before the model call, so a response is only
    /// produced under the permission state it started in.
    #[serde(default)]
    pub snapshot_ok: bool,
}

/// The fully prepared inference pipeline for one chat request (eighteenth
/// audit P1-6): agent context → authorization snapshot → ContextRequest →
/// retrieval plan → compact context → typed ContextItems → kernel bundle →
/// system context. BOTH the JSON chat and the SSE stream run through this
/// SAME preparation, so the stream can no longer bypass the Context Kernel
/// or the authorization snapshot.
pub(crate) struct PreparedInference {
    /// The server-created agent context (caller scope + permissions).
    pub ctx: sensei_agent_core::context::AgentContext,
    /// The authorization snapshot captured once at request start.
    pub snapshot: Option<AuthzSnapshot>,
    /// The deterministic retrieval plan.
    pub context_plan: sensei_agent_core::context::ContextPlan,
    /// The compact authoritative context bundle — the texts fed INTO
    /// generation. The verifier matches evidence markers against these.
    pub context_used: Vec<String>,
    /// The PREPARED kernel items behind `context_used` (nineteenth audit
    /// P1): the typed provenance is kept through verification. The
    /// verifier builds the ACTUAL evidence_id set from these items — a
    /// marker is validated by id membership, never by substring matching
    /// against a flattened string.
    pub kernel_items: Vec<sensei_agent_core::context::ContextItem>,
    /// The prepared system context (the joined bundle), `None` when empty.
    pub system_context: Option<String>,
}

/// Build the FULL preparation pipeline shared by the JSON chat and the SSE
/// stream (eighteenth audit P1-6). Order: AUTHENTICATE → AUTHORIZATION
/// SNAPSHOT → TASK CLASSIFICATION → CONTEXT REQUEST → RETRIEVAL PLAN →
/// AUTHORIZED RETRIEVAL → CONTEXT BUNDLE.
///
/// The TOCTOU `is_still_current` re-check is deliberately NOT here: each
/// caller re-checks the snapshot AFTER preparation and as close to
/// generation as possible.
pub(crate) async fn prepare_inference(
    user: &AuthenticatedUser,
    state: &AppState,
    message: &str,
    conversation_id: Option<&str>,
) -> Result<PreparedInference> {
    // Context Kernel BEFORE generation (sixteenth audit 8/96): the
    // deterministic plan decides what live tenant state is retrieved —
    // the compact authoritative bundle is fed INTO the prompt, it is not
    // attached afterwards as metadata. Order: AUTHENTICATE →
    // AUTHORIZATION SNAPSHOT → TASK CLASSIFICATION → CONTEXT REQUEST →
    // RETRIEVAL PLAN → AUTHORIZED RETRIEVAL → CONTEXT BUNDLE →
    // GENERATION → CLAIM VERIFICATION → OUTPUT.
    let ctx = crate::routes::agent::build_context(user, state).await;

    // Authorization snapshot (sixteenth audit items 5/24): captured ONCE
    // at request start — the revision triple the whole request runs
    // under, salted with the caller's effective permissions. Retrieval,
    // generation and the verifier all run under THIS permission state;
    // the TOCTOU guard below re-checks it before the model call.
    let snapshot = match &state.db_pool {
        Some(pool) => {
            let revisions = sensei_services::tps::authorization_revisions::current_snapshot(
                pool,
                user.tenant_id,
            )
            .await?;
            // Deterministic digest of the sorted effective permissions
            // (same resolution as HTTP authorization and build_context):
            // any role change shifts the digest, so it cannot collide
            // across distinct permission sets.
            let rbac = sensei_auth::rbac::authorization_service();
            let mut perms: Vec<String> = user
                .roles
                .iter()
                .flat_map(|role| rbac.permissions_for_role_in_tenant(user.tenant_id, role))
                .collect();
            perms.sort();
            perms.dedup();
            let mut hasher = Sha256::new();
            for p in &perms {
                hasher.update(p.as_bytes());
            }
            Some(AuthzSnapshot {
                tenant: user.tenant_id,
                principal: user.user_id,
                roles: user.roles.clone(),
                policy_revision: revisions.policy_revision,
                relationship_revision: revisions.relationship_revision,
                principal_revision: revisions.principal_revision,
                scope_site: ctx.site_id,
                permission_digest: hasher.finalize().into(),
            })
        }
        None => None,
    };
    // Fifteenth audit (6-8/74): EVERY AI operation goes through the
    // Context Kernel — the deterministic plan (task decides the required
    // context sections BEFORE any retrieval). The model never invents the
    // retrieval strategy.
    let context_request = sensei_agent_core::context::ContextRequest {
        principal_id: user.user_id,
        roles: user.roles.clone(),
        site_id: ctx.site_id,
        value_stream_id: ctx.value_stream_id,
        work_center_id: ctx.work_center_id,
        task: classify_task(message),
        focal_objects: Vec::new(),
        max_tokens: 4096,
        sensitivity_ceiling: sensei_agent_core::context::DataClass::Internal,
        trace_id: conversation_id.unwrap_or_default().to_string(),
    };
    let context_plan = sensei_agent_core::context::plan_context(&context_request);
    // Seventeenth audit item 7: the live chat runs through the ACTUAL
    // Context Kernel. The section facts are wrapped in typed ContextItems
    // (provenance = the section source, authority = live transactional
    // state, sensitivity = Internal, epistemic = RecordedFact) and
    // build_context_bundle applies the REAL kernel semantics: FactAddress
    // contradiction handling, authority ordering, provenance-based
    // selection, sensitivity filtering and the normal-budget token
    // allocation with the reserved contradiction budget.
    // Twenty-fifth audit P0/P1: the kernel sections are carried as TYPED
    // facts (section + source site + work center + typed value/unit/
    // observed_at) and turned into ContextItems DIRECTLY — a flat-string
    // protocol is never the identity source. This replaces the old line
    // parser, which split every line on " [live]: " and therefore DROPPED
    // every site-marked line (emitted as "section [live site:<uuid>]:
    // content", which contains no " [live]: ") — the dropped lines were
    // site-scoped evidence that never reached the model, and the
    // survivors were site-less. With typed facts a marked section can
    // neither be dropped nor stripped of its source scope.
    // Thirtieth audit item 23: the typed facts carry their FactAddress,
    // typed value, unit and source observation time; the ContextItem
    // payload embeds the typed fact so the verifier checks claims against
    // the TYPED fields (never the prose).
    let kernel_items: Vec<ContextItem> = match &state.db_pool {
        Some(pool) => {
            let facts = sensei_services::tps::context_sections::build_context_facts(
                pool,
                user.tenant_id,
                ctx.site_id,
                ctx.work_center_id,
                &context_plan,
            )
            .await;
            facts
                .into_iter()
                .map(|fact| {
                    let mut item = fact.to_context_item();
                    // Nineteenth audit P1: the evidence id is issued HERE
                    // at construction from the item's own provenance +
                    // payload — the Context Kernel also normalizes any
                    // item that still arrives empty.
                    item.evidence_id = item.derive_evidence_id();
                    item
                })
                .collect()
        }
        None => Vec::new(),
    };
    let kernel_bundle = sensei_agent_core::context_kernel::build_context_bundle(
        &context_request,
        kernel_items,
        sensei_agent_core::context::TokenBudget::default_for(4096),
    );
    // Nineteenth audit P1: the typed items survive the kernel — they are
    // kept alongside the flattened texts so the verifier can validate
    // evidence markers against the ACTUAL evidence_id set.
    let kernel_items: Vec<sensei_agent_core::context::ContextItem> = kernel_bundle
        .sections
        .iter()
        .flat_map(|(_, items)| items.iter().cloned())
        .collect();
    let context_used: Vec<String> = kernel_items
        .iter()
        .map(|item| {
            let text = item
                .payload
                .get("text")
                .and_then(|t| t.as_str())
                .map(|t| match t.split_once("[live site:") {
                    Some((head, rest)) => {
                        let tail = rest.split_once(']').map(|(_, after)| after).unwrap_or("");
                        format!("{head}{tail}")
                    }
                    None => t.to_string(),
                })
                .unwrap_or_default();
            // Twentieth audit P1: the typed envelope reaches the model —
            // evidence id, authority, observation time and text. The
            // verifier only accepts ev:* ids that appear here.
            let observed = item
                .provenance
                .observed_at
                .map(|t| t.to_rfc3339())
                .unwrap_or_else(|| "unknown".to_string());
            let fact_addr = item.fact_address.as_deref().unwrap_or("unknown");
            let authority = match item.provenance.authority {
                sensei_agent_core::context::AuthorityRank::VerifiedObservation => {
                    "verified_observation"
                }
                sensei_agent_core::context::AuthorityRank::TransactionalState => {
                    "transactional_state"
                }
                _ => "derived",
            };
            if item.evidence_id.is_empty() {
                text
            } else {
                format!(
                    "[EVIDENCE {}] fact_address={} authority={} observed_at={}\n{text}",
                    item.evidence_id, fact_addr, authority, observed
                )
            }
        })
        .collect();
    let system_context = if context_used.is_empty() {
        None
    } else {
        Some(context_used.join("\n"))
    };

    Ok(PreparedInference {
        ctx,
        snapshot,
        context_plan,
        context_used,
        kernel_items,
        system_context,
    })
}

/// Handle a single-turn chat message.
///
/// Returns a JSON response with the assistant's reply.
pub async fn chat(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ChatRequest>,
) -> Result<Json<ChatResponseBody>> {
    user.require_permission("ai:inference")?;

    // Eighteenth audit P1-6: the FULL Context Kernel preparation is shared
    // with the SSE stream — agent context → authorization snapshot →
    // ContextRequest → plan → compact context → typed ContextItems →
    // kernel bundle → prepared system context.
    let prepared =
        prepare_inference(&user, &state, &req.message, req.conversation_id.as_deref()).await?;

    // TOCTOU guard (sixteenth audit items 5/24): the permission state
    // must NOT have moved between snapshot capture and generation — if
    // any revision bumped (a revocation landed mid-request), the request
    // is refused and must be re-authorized, never executed under a stale
    // state. In-memory deployments (no DB pool, no authorization state)
    // have nothing that can have moved — the gate is vacuous there. The
    // check stays HERE, after preparation and immediately before the
    // model call.
    let snapshot_ok =
        authorization_gate(state.db_pool.as_deref(), prepared.snapshot.as_ref()).await;
    if !snapshot_ok {
        return Err(sensei_core::error::SenseiError::Forbidden(
            "authorization state changed during the request — re-authorized and retry".to_string(),
        ));
    }

    let response = state
        .chatbot_service
        .chat(
            user.tenant_id,
            user.user_id,
            &req.message,
            req.conversation_id.as_deref(),
            req.sampling_params(),
            prepared.system_context.as_deref(),
        )
        .await
        .map_err(|e| {
            error!(error = %e, "Chatbot chat failed");
            e
        })?;

    // Item 22: the legacy chat surface flows through the SAME agent
    // control plane as the tool surface — server-created context, the
    // effective (policy-filtered) toolset and the deterministic verifier.
    // The assistant can no longer answer with unverifiable tenant claims:
    // every response is checked against the caller's real permissions and
    // the tool contract.
    // Thirtieth audit item 23: derived claims are recomputed by the
    // deterministic programs (metrics) NOW, after generation and before
    // verification — the value the model asserts must equal what the
    // program computes at release time.
    let policy = sensei_agent_core::tools::PolicyEngine::new(
        crate::services::agent::build_readonly_tools(),
        sensei_agent_core::tools::ToolRisk::ReadOnly,
    );
    let effective_tools = policy.effective_tools(&prepared.ctx);
    let (recomputed, recompute_issues) = resolve_recomputed_derivations(
        state.db_pool.as_deref(),
        user.tenant_id,
        prepared.ctx.site_id,
        &req.structured_claims,
    )
    .await;
    let verification = verify_chat_response(
        &response,
        &prepared.ctx,
        &policy,
        &effective_tools,
        &prepared.kernel_items,
        &req.structured_claims,
        &recomputed,
        &recompute_issues,
    );
    // Seventeenth audit item 7 — verifier failure BLOCKS/REPAIRS output:
    // an unverifiable factual reply is never delivered as-is. The
    // content is REPAIRED into an honest answer that does not assert the
    // unverified claims (the client sees verdict 'repaired' with the
    // original issues).
    let (final_content, verdict_label) = if verification["verdict"].as_str() == Some("pass") {
        (response.message.content, "pass".to_string())
    } else {
        let issue_count = verification["issues"]
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);
        (repair_message(issue_count), "repaired".to_string())
    };
    let mut verification_out = verification;
    if verdict_label == "repaired" {
        verification_out["verdict"] = serde_json::json!("repaired");
    }
    // ITEM 24 — the release gate: model generation took time; the
    // authorization snapshot must STILL be current after deterministic
    // verification and immediately before the answer is released. A
    // revocation that landed mid-execution means the response is never
    // handed out.
    if !authorization_gate(state.db_pool.as_deref(), prepared.snapshot.as_ref()).await {
        return Err(sensei_core::error::SenseiError::Forbidden(
            "authorization state changed after model execution — the answer was \
             not released; re-authorized and retry"
                .to_string(),
        ));
    }
    Ok(Json(ChatResponseBody {
        response: final_content,
        conversation_id: response.conversation_id,
        is_fallback: response.is_fallback,
        verification: Some(verification_out),
        context_plan: Some(prepared.context_plan),
        context_used: Some(prepared.context_used),
        snapshot_ok: true,
    }))
}

/// The honest repair text released when verification fails (eighteenth
/// audit P1-6): the JSON chat and the SSE stream publish THE SAME repaired
/// answer — the raw buffered reply with unverified claims is never
/// delivered.
fn repair_message(issue_count: usize) -> String {
    format!(
        "I can only answer with claims verified against the plant systems.              The previous reply contained statements I could not verify against              live tenant data ({issue_count} issue(s)). Ask me to query a specific metric,              work order, quality record or andon through the tool surface."
    )
}

/// Deterministic task classification (seventeenth audit item 7): the
/// message selects the Context Kernel task instead of hardcoding
/// TaskKind::General — the plan (and therefore the retrieved sections)
/// follows the operational intent.
fn classify_task(message: &str) -> sensei_agent_core::context::TaskKind {
    use sensei_agent_core::context::TaskKind;
    let lower = message.to_lowercase();
    if lower.contains("andon")
        || lower.contains("escalat")
        || lower.contains("contain")
        || lower.contains("safety")
    {
        TaskKind::OperatorAssist
    } else if lower.contains("quality")
        || lower.contains("ncr")
        || lower.contains("capa")
        || lower.contains("defect")
        || lower.contains("inspection")
    {
        TaskKind::QualityInvestigation
    } else if lower.contains("schedule")
        || lower.contains("plan")
        || lower.contains("takt")
        || lower.contains("pitch")
        || lower.contains("demand")
    {
        TaskKind::PlannerDecision
    } else if lower.contains("executive")
        || lower.contains("summary")
        || lower.contains("trend")
        || lower.contains("dashboard")
        || lower.contains("kpi")
        || lower.contains("metric")
        || lower.contains("overview")
    {
        TaskKind::ExecutiveAnalysis
    } else if lower.contains("fix")
        || lower.contains("error")
        || lower.contains("why")
        || lower.contains("fault")
        || lower.contains("broken")
    {
        TaskKind::Troubleshoot
    } else {
        TaskKind::General
    }
}

/// Parse the SOURCE site marker emitted by the retrieval layer
/// ("[live site:<uuid>]") — evidence is stamped from the source row's
/// site, never from the request's claimed site. The live preparation
/// consumes TYPED kernel facts (twenty-fifth audit), so this parser is
/// the contract check for the legacy flat-line format.
#[cfg(test)]
fn parse_source_site(text: &str) -> Option<uuid::Uuid> {
    text.split_once("[live site:").and_then(|(_, rest)| {
        rest.split_once(']')
            .and_then(|(site, _)| uuid::Uuid::parse_str(site).ok())
    })
}

/// Parse ONE context-bundle line into `(section, content, source_site)`
/// (twenty-fifth audit P0): handles BOTH line forms the kernel emits —
/// the site-less form `"section [live]: content"` AND the site-marked
/// form `"section [live site:<uuid>]: content"`. The old parser split
/// every line on `" [live]: "` and therefore DROPPED every site-marked
/// line (the marker replaces the `[live]` tag, so `" [live]: "` is never
/// present); surviving lines were all site-less — site-scoped evidence
/// never reached the model. This parser never drops a line: the site
/// marker is extracted FIRST when present, then the remainder is split
/// on `" [live]: "`; a line with no tag at all is kept whole as content.
#[cfg(test)]
fn parse_context_line(line: &str) -> Option<(String, String, Option<uuid::Uuid>)> {
    if line.contains(" [live site:") {
        let (head, rest) = line.split_once(" [live site:")?;
        // A malformed marker keeps the line (never dropped) but yields no
        // site scope — a site identity is never invented.
        let site = parse_source_site(line);
        let content = rest
            .split_once("]: ")
            .map(|(_, content)| content)
            .unwrap_or(rest);
        return Some((head.to_string(), content.to_string(), site));
    }
    if let Some((section, content)) = line.split_once(" [live]: ") {
        return Some((section.to_string(), content.to_string(), None));
    }
    // No section tag on the line (e.g. the bare "no additional context"
    // fallback): keep it whole — never drop a line.
    Some((String::new(), line.to_string(), None))
}

/// Run the REAL claims/evidence verifier over the assistant's reply
/// (item 25; thirtieth audit item 23 REWRITE): measured claims are now
/// verified DETERMINISTICALLY against TYPED evidence.
///
/// The claim channel is the STRUCTURED one: a measured claim must carry
/// a typed [`ClaimAssertion`] (FactAddress + operator + value + unit) or
/// a [`DerivedAssertion`] (the server re-runs the derivation program and
/// compares the recomputed result). Verification checks, per cited
/// evidence item: evidence existence AND exact object match AND exact
/// attribute match AND exact site/work-center scope match AND valid
/// time/freshness AND unit compatibility AND the claimed operator/value.
/// The language of the statement is irrelevant — a French or Arabic
/// rendering of the same assertion verifies identically.
///
/// The lexical PROSE SCANNER is demoted to defense-in-depth: it only
/// detects that the model rendered factual prose WITHOUT representing it
/// in the structured claims channel (such prose is flagged, never
/// measured). Every `[evidence: ...]` marker is parsed on every sentence
/// whether or not the sentence classifies as a factual claim — a fake
/// marker can never hide inside unclassified prose.
///
/// `recomputed` carries the server-side recomputation results of every
/// derivation program referenced by the drafts (produced by
/// [`resolve_recomputed_derivations`] from the live metric engine);
/// `recompute_issues` carries the failures of that resolution (unknown
/// derivation ids, version moves, no live program) — a derived claim is
/// NEVER accepted without the deterministic program agreeing.
#[allow(clippy::too_many_arguments)]
fn verify_chat_response(
    response: &sensei_services::ai::chatbot::ChatResponse,
    ctx: &AgentContext,
    _policy: &sensei_agent_core::tools::PolicyEngine,
    _effective_tools: &[&sensei_agent_core::tools::ToolSpec],
    kernel_items: &[ContextItem],
    structured_claims: &[ClaimDraft],
    recomputed: &HashMap<String, RecomputedDerivation>,
    recompute_issues: &[String],
) -> serde_json::Value {
    let mut issues: Vec<String> = Vec::new();
    issues.extend(recompute_issues.iter().cloned());
    let mut claims: Vec<Claim> = Vec::new();
    let mut typed_checked: usize = 0;
    let mut derived_checked: usize = 0;
    let content = response.message.content.clone();

    if response.is_fallback {
        issues.push(
            "Fallback/general answer — not grounded in tenant evidence; \
             treat as guidance, not as a validated fact."
                .to_string(),
        );
        return envelope(issues, claims, typed_checked, derived_checked, ctx);
    }

    // Nineteenth audit P1: the ACTUAL evidence ids issued by the Context
    // Kernel for this request — built from the prepared items, never from
    // flattened strings.
    let evidence_ids: HashSet<String> = kernel_items
        .iter()
        .map(|item| item.evidence_id.clone())
        .filter(|id| !id.is_empty())
        .collect();
    let evidence_by_id: HashMap<String, &ContextItem> = kernel_items
        .iter()
        .map(|item| (item.evidence_id.clone(), item))
        .collect();

    /// A fully resolved structured claim (typed assertion or derived
    /// assertion) from one caller/model draft.
    struct ResolvedDraft {
        statement: String,
        evidence_ids: Vec<String>,
        assertion: Option<ClaimAssertion>,
        derived: Option<DerivedAssertion>,
    }

    /// Resolve the typed fields of one structured draft. A measured
    /// claim MUST carry a typed assertion or a derived assertion (never
    /// both) — evidence ids alone cannot prove a value.
    fn resolve_draft(draft: &ClaimDraft) -> std::result::Result<ResolvedDraft, String> {
        let statement = draft.statement.trim().to_string();
        if statement.is_empty() {
            return Err("structured claim has an empty statement".to_string());
        }
        let assertion = match &draft.assertion {
            None => None,
            Some(a) => {
                let missing = |what: &str| {
                    format!("structured claim '{statement}' is missing the {what} of its typed assertion")
                };
                let object_type = a
                    .object_type
                    .as_deref()
                    .filter(|s| !s.trim().is_empty())
                    .ok_or_else(|| missing("object_type"))?;
                let object_id = a
                    .object_id
                    .as_deref()
                    .filter(|s| !s.trim().is_empty())
                    .ok_or_else(|| missing("object_id"))?;
                let attribute = a
                    .attribute
                    .as_deref()
                    .filter(|s| !s.trim().is_empty())
                    .ok_or_else(|| missing("attribute"))?;
                let value = a.value.clone().ok_or_else(|| missing("value"))?;
                Some(ClaimAssertion {
                    address: FactAddress {
                        object_type: object_type.to_string(),
                        object_id: object_id.to_string(),
                        attribute: attribute.to_string(),
                        valid_time: a.valid_time.clone(),
                    },
                    operator: a.operator.clone().unwrap_or(ClaimOperator::Equal),
                    value,
                    unit: a.unit.clone(),
                })
            }
        };
        let derived = match &draft.derived {
            None => None,
            Some(d) => {
                let result = d.result.clone().ok_or_else(|| {
                    format!("derived claim '{statement}' is missing its claimed result value")
                })?;
                Some(DerivedAssertion {
                    derivation_id: d.derivation_id.clone(),
                    derivation_version: d.derivation_version,
                    operand_evidence_ids: d.operand_evidence_ids.clone(),
                    result,
                    unit: d.unit.clone(),
                })
            }
        };
        match (&assertion, &derived) {
            (Some(_), Some(_)) => Err(format!(
                "structured claim '{statement}' carries BOTH a typed assertion and a \
                 derived assertion — a claim is measured by exactly one channel"
            )),
            _ => Ok(ResolvedDraft {
                statement,
                evidence_ids: draft.evidence_ids.clone(),
                assertion,
                derived,
            }),
        }
    }

    /// The structural fact-address summary of an evidence item, for the
    /// claim envelope (site + typed address when present).
    fn evidence_fact_summary(item: &ContextItem) -> String {
        let site = item
            .site_scope
            .map(|s| s.to_string())
            .unwrap_or_else(|| "unknown".to_string());
        if let Some(fact) = item.typed_fact() {
            format!(
                "site:{}/{}:{}:{}",
                site, fact.address.object_type, fact.address.object_id, fact.address.attribute
            )
        } else {
            format!(
                "site:{}/address:{}",
                site,
                item.fact_address.as_deref().unwrap_or("unknown")
            )
        }
    }

    // The statements represented by the structured channel, keyed by a
    // normalized form (whitespace/punctuation/case-insensitive, evidence
    // markers stripped): factual prose sentences whose statement IS
    // represented by a draft are verified once through the draft.
    let represented: HashMap<String, usize> = structured_claims
        .iter()
        .enumerate()
        .map(|(i, d)| (normalize_statement(&d.statement), i))
        .collect();

    // ── PROSE SCANNER (defense-in-depth, thirtieth audit item 23) ─────
    // Every sentence is scanned for evidence markers FIRST — a marker is
    // parsed whether or not the sentence classifies as a factual claim,
    // so a fabricated citation can never hide inside unclassified prose.
    // Factual prose sentences that are NOT represented by a structured
    // claim with a typed assertion are flagged — the model rendered
    // factual content without representing it in the claims channel, and
    // that content can never be measured by language heuristics.
    for sentence in split_sentences(&content) {
        let s = sentence.trim();
        if s.is_empty() {
            continue;
        }
        let markers = evidence_refs_in(s);
        let unmatched: Vec<&String> = markers
            .iter()
            .filter(|m| !evidence_ids.contains(m.as_str()))
            .collect();
        if !unmatched.is_empty() {
            for r in &unmatched {
                issues.push(format!(
                    "Unverified evidence reference: '{r}' — not an evidence id \
                     issued by the Context Kernel for this request."
                ));
            }
        }
        if !sentence_is_factual_prose(s) {
            continue;
        }
        // Represented by the structured channel → verified through the
        // draft loop below (the statement is the SAME claim).
        if represented.contains_key(&normalize_statement(s)) {
            continue;
        }
        let matched: Vec<String> = markers
            .iter()
            .filter(|m| evidence_ids.contains(m.as_str()))
            .cloned()
            .collect();
        if matched.is_empty() {
            claims.push(Claim {
                statement: s.to_string(),
                epistemic_status: "unverified".to_string(),
                fact_addresses: Vec::new(),
                evidence_refs: Vec::new(),
                confidence: None,
                valid_at: None,
                assertion: None,
                derived: None,
            });
            issues.push(format!(
                "Unverified factual claim: '{s}' — no EvidenceRef. \
                 Facts about live tenant data must be queried through the \
                 tool surface, stated as unavailable, or labeled a hypothesis."
            ));
        } else {
            // Real evidence markers, but the claim exists ONLY as prose —
            // no typed assertion represents it in the structured channel.
            let fact_addresses: Vec<String> = matched
                .iter()
                .filter_map(|r| evidence_by_id.get(r.as_str()))
                .map(|item| evidence_fact_summary(item))
                .collect();
            claims.push(Claim {
                statement: s.to_string(),
                epistemic_status: "unverified".to_string(),
                fact_addresses,
                evidence_refs: matched.clone(),
                confidence: None,
                valid_at: None,
                assertion: None,
                derived: None,
            });
            issues.push(format!(
                "Factual claim rendered only in prose: '{s}' [evidence: {}] — it \
                 is not represented in the structured claims channel, so it cannot \
                 be measured. A measured claim must carry a typed ClaimAssertion \
                 (address/operator/value/unit) or a DerivedAssertion.",
                matched.join(", ")
            ));
        }
    }

    // ── STRUCTURED CLAIMS channel (deterministic verification) ────────
    // Each draft is verified once: typed assertions go through the full
    // chain (object → attribute → site/WC → time/freshness → unit →
    // operator/value); derived assertions are checked against the
    // server's recomputation.
    for draft in structured_claims {
        let resolved = match resolve_draft(draft) {
            Ok(r) => r,
            Err(e) => {
                claims.push(Claim {
                    statement: draft.statement.trim().to_string(),
                    epistemic_status: "unverified".to_string(),
                    fact_addresses: Vec::new(),
                    evidence_refs: Vec::new(),
                    confidence: None,
                    valid_at: None,
                    assertion: None,
                    derived: None,
                });
                issues.push(e);
                continue;
            }
        };
        let unmatched: Vec<&String> = resolved
            .evidence_ids
            .iter()
            .filter(|m| !evidence_ids.contains(m.as_str()))
            .collect();
        if !unmatched.is_empty() {
            for r in &unmatched {
                issues.push(format!(
                    "Unverified evidence reference: '{r}' — not an evidence id \
                     issued by the Context Kernel for this request."
                ));
            }
        }
        let matched: Vec<String> = resolved
            .evidence_ids
            .iter()
            .filter(|m| evidence_ids.contains(m.as_str()))
            .cloned()
            .collect();
        let fact_addresses: Vec<String> = matched
            .iter()
            .filter_map(|r| evidence_by_id.get(r.as_str()))
            .map(|item| evidence_fact_summary(item))
            .collect();

        // A structured claim that does not assert a typed value can never
        // be measured (the audit's canonical hole: evidence E says 12,
        // the claim says 999 — without the operator/value comparison the
        // verifier has nothing to reject). Derived-only drafts are
        // handled by the derived loop below.
        if resolved.derived.is_some() && resolved.assertion.is_none() {
            continue;
        }
        let Some(assertion) = resolved.assertion.as_ref() else {
            claims.push(Claim {
                statement: resolved.statement.clone(),
                epistemic_status: "unverified".to_string(),
                fact_addresses: fact_addresses.clone(),
                evidence_refs: matched.clone(),
                confidence: None,
                valid_at: None,
                assertion: resolved.assertion.clone(),
                derived: None,
            });
            if matched.is_empty() {
                issues.push(format!(
                    "Unverified factual claim: '{}' — no EvidenceRef. \
                     Facts about live tenant data must be queried through the \
                     tool surface, stated as unavailable, or labeled a hypothesis.",
                    resolved.statement
                ));
            } else {
                issues.push(format!(
                    "Structured claim '{}' cannot be measured: a measured factual \
                     claim must carry a typed ClaimAssertion \
                     (object_type/object_id/attribute/operator/value/unit) or a \
                     DerivedAssertion — an evidence id alone proves no value.",
                    resolved.statement
                ));
            }
            continue;
        };

        // TYPED measured claim: verify against every cited evidence item.
        // (A draft carrying BOTH channels was rejected by resolve_draft.)
        typed_checked += 1;
        let mut claim_issues: Vec<String> = Vec::new();
        for r in &matched {
            if let Some(item) = evidence_by_id.get(r.as_str()) {
                claim_issues.extend(verify_measured_claim(
                    None,
                    assertion,
                    ctx.site_id,
                    ctx.work_center_id,
                    item,
                    chrono::Utc::now(),
                ));
            }
        }
        if matched.is_empty() {
            claim_issues.push(format!(
                "measured claim '{}' cites no evidence issued by the Context Kernel",
                resolved.statement
            ));
        }
        if claim_issues.is_empty() {
            claims.push(Claim {
                statement: resolved.statement.clone(),
                epistemic_status: "measured".to_string(),
                fact_addresses: fact_addresses.clone(),
                evidence_refs: matched.clone(),
                confidence: None,
                valid_at: parse_claim_time(None, assertion.address.valid_time.as_deref())
                    .map(|t| t.to_rfc3339()),
                assertion: Some(assertion.clone()),
                derived: None,
            });
        } else {
            issues.extend(claim_issues.iter().cloned());
            claims.push(Claim {
                statement: resolved.statement.clone(),
                epistemic_status: "unverified".to_string(),
                fact_addresses: fact_addresses.clone(),
                evidence_refs: matched.clone(),
                confidence: None,
                valid_at: None,
                assertion: Some(assertion.clone()),
                derived: None,
            });
        }
    }

    // ── DERIVED claims (server recomputation) ─────────────────────────
    // Structured drafts carrying a DerivedAssertion were recomputed by
    // the deterministic program BEFORE this function ran; every derived
    // claim is checked against the recomputed value and its operand
    // evidence ids.
    for draft in structured_claims {
        if draft.derived.is_none() {
            continue;
        }
        if draft.assertion.is_some() {
            continue; // reported by the typed path above
        }
        let resolved = match resolve_draft(draft) {
            Ok(r) => r,
            Err(_) => continue,
        };
        let Some(derived) = resolved.derived.as_ref() else {
            continue;
        };
        derived_checked += 1;
        let key = derivation_key(&derived.derivation_id, derived.derivation_version);
        let recomputed_value = recomputed.get(&key);
        let operand_exists = |id: &str| evidence_ids.contains(id) || id.is_empty();
        let derived_issues = verify_derived_claim(
            derived,
            recomputed_value,
            operand_exists,
            chrono::Utc::now(),
        );
        if derived_issues.is_empty() {
            claims.push(Claim {
                statement: resolved.statement.clone(),
                epistemic_status: "measured".to_string(),
                fact_addresses: Vec::new(),
                evidence_refs: resolved.evidence_ids.clone(),
                confidence: None,
                valid_at: None,
                assertion: None,
                derived: Some(derived.clone()),
            });
        } else {
            issues.extend(derived_issues.iter().cloned());
            claims.push(Claim {
                statement: resolved.statement.clone(),
                epistemic_status: "unverified".to_string(),
                fact_addresses: Vec::new(),
                evidence_refs: resolved.evidence_ids.clone(),
                confidence: None,
                valid_at: None,
                assertion: None,
                derived: Some(derived.clone()),
            });
        }
    }

    envelope(issues, claims, typed_checked, derived_checked, ctx)
}

/// Build the verification envelope.
fn envelope(
    issues: Vec<String>,
    claims: Vec<Claim>,
    typed_checked: usize,
    derived_checked: usize,
    ctx: &AgentContext,
) -> serde_json::Value {
    let verdict = if issues.is_empty() {
        "pass"
    } else {
        "needs_evidence"
    };
    serde_json::json!({
        "verdict": verdict,
        "issues": issues,
        "claims": claims,
        "claims_checked": claims.len(),
        "typed_claims_checked": typed_checked,
        "derived_claims_checked": derived_checked,
        "context": {
            "site_id": ctx.site_id,
            "value_stream_id": ctx.value_stream_id,
            "work_center_id": ctx.work_center_id,
            "shift_id": ctx.shift_id,
        },
    })
}

/// Normalize a claim statement for prose↔structured pairing: case-folded,
/// whitespace collapsed, trailing punctuation stripped, evidence markers
/// removed. Two renderings of the SAME claim in ANY language normalize to
/// the same key when their statements are identical.
fn normalize_statement(s: &str) -> String {
    let mut out = s.trim().to_lowercase();
    // Strip "[evidence: ...]" markers — the structured statement does not
    // carry them while the prose rendering may.
    while let Some(start) = out.find("[evidence:") {
        let after = &out[start + "[evidence:".len()..];
        let Some(end) = after.find(']') else {
            break;
        };
        out = format!("{}{}", &out[..start], &after[end + 1..]);
    }
    let collapsed: String = out.split_whitespace().collect::<Vec<_>>().join(" ");
    collapsed
        .trim_end_matches(['.', '!', '?', ';', ',', ':'])
        .to_string()
}

/// Deterministic recomputation key of a derivation program result:
/// derivation id @ program version.
fn derivation_key(derivation_id: &str, version: u32) -> String {
    format!("{derivation_id}@{version}")
}

/// Thirtieth audit item 23 — derived claims: RE-RUN the deterministic
/// derivation programs referenced by the structured drafts and return
/// (a) the recomputed values keyed by `derivation_id@version` and (b)
/// the deterministic failures (unknown derivation ids, version moves,
/// program errors, no live program). The model NEVER gets to say a value
/// "was deterministically derived" unless the program agrees — a derived
/// claim whose id is not resolvable or whose version moved is rejected,
/// never silently re-verified against a prepared value.
async fn resolve_recomputed_derivations(
    db_pool: Option<&PgPool>,
    tenant_id: uuid::Uuid,
    site_id: Option<uuid::Uuid>,
    structured_claims: &[ClaimDraft],
) -> (HashMap<String, RecomputedDerivation>, Vec<String>) {
    let mut recomputed: HashMap<String, RecomputedDerivation> = HashMap::new();
    let mut issues: Vec<String> = Vec::new();
    for draft in structured_claims {
        let Some(derived) = draft.derived.as_ref() else {
            continue;
        };
        let key = derivation_key(&derived.derivation_id, derived.derivation_version);
        if recomputed.contains_key(&key) {
            continue;
        }
        // Derived claims need the live deterministic program. Every
        // current derivation program in the system is a METRIC of the
        // metric engine (the one executable registry every surface uses);
        // unknown ids have no program and can never verify.
        let Some(pool) = db_pool else {
            issues.push(format!(
                "derived claim '{}'@v{} could not be recomputed — no live \
                 deterministic derivation program is available for this request",
                derived.derivation_id, derived.derivation_version
            ));
            continue;
        };
        let program = sensei_services::tps::metric_engine::registry()
            .into_iter()
            .find(|c| {
                c.id() == derived.derivation_id
                    || (derived.derivation_id == "fpy" && c.id() == "process_yield_proxy")
            });
        let Some(program) = program else {
            issues.push(format!(
                "derived claim '{}'@v{} cites a derivation id with no \
                 deterministic program — the server cannot recompute it",
                derived.derivation_id, derived.derivation_version
            ));
            continue;
        };
        let current_version = program.version();
        if current_version != derived.derivation_version {
            issues.push(format!(
                "derived claim '{}'@v{} cites a moved derivation program — the \
                 deterministic program is now at version {current_version}; \
                 re-derive against the current version",
                derived.derivation_id, derived.derivation_version
            ));
            continue;
        }
        match program.compute(pool, tenant_id, site_id).await {
            Ok(result) => {
                let value = serde_json::to_value(result.value).unwrap_or(serde_json::Value::Null);
                recomputed.insert(
                    key,
                    RecomputedDerivation {
                        derivation_id: result.metric_id,
                        version: current_version,
                        value,
                        unit: Some(result.unit),
                        recomputed_at: result.computed_at,
                    },
                );
            }
            Err(e) => issues.push(format!(
                "derived claim '{}'@v{} could not be recomputed — the \
                 deterministic program failed: {e}",
                derived.derivation_id, derived.derivation_version
            )),
        }
    }
    (recomputed, issues)
}

/// Item 24 — the authorization release gate: the request's authorization
/// snapshot must STILL be current immediately before an answer is
/// released. Model execution takes time: T0 snapshot, T1 generation
/// starts, T2 a revocation lands, T3 generation finishes — releasing the
/// answer would hand out data under a permission state the caller no
/// longer has. The gate is re-run AFTER deterministic verification and
/// immediately BEFORE any release (JSON response or first streamed
/// token).
///
/// A request that captured NO authorization state (dev/in-memory
/// deployment without a database) has nothing that can have moved — the
/// gate is vacuously open (the content is still repaired by the
/// verifier). A half-captured state never occurs in the request flow and
/// fails closed.
async fn authorization_gate(db_pool: Option<&PgPool>, snapshot: Option<&AuthzSnapshot>) -> bool {
    match (db_pool, snapshot) {
        (Some(pool), Some(snap)) => snap.is_still_current(pool).await,
        (None, None) => true,
        _ => false,
    }
}

/// Whether a sentence sounds like a direct request or meta-talk rather
/// than an assertion (defense-in-depth prose gate).
fn hedged_or_interrogative(s: &str) -> bool {
    let sentence_lower = s.to_lowercase();
    let ends_interrogative = s.ends_with('?');
    if ends_interrogative {
        return true;
    }
    [
        "i ",
        "i'm ",
        "i am ",
        "please",
        "can you",
        "could you",
        "should ",
        "would you",
        "ask ",
        "check ",
        "look up",
        "query ",
        "hypothesis",
        "note:",
        "guidance",
        "treat ",
        "as a hypothesis",
    ]
    .iter()
    .any(|p| sentence_lower.starts_with(p))
}

/// Defense-in-depth factual-prose detector (thirtieth audit item 23): a
/// sentence about an operational subject that states a predicate. This
/// detector no longer MEASURES anything — it only spots prose the model
/// rendered WITHOUT representing it in the structured claims channel.
fn sentence_is_factual_prose(s: &str) -> bool {
    if s.len() < 12 || hedged_or_interrogative(s) {
        return false;
    }
    let sentence_lower = s.to_lowercase();
    let operational_subjects = [
        "line",
        "process",
        "operator",
        "supplier",
        "plant",
        "site",
        "inventory",
        "stock",
        "delivery",
        "shipment",
        "quality",
        "yield",
        "scrap",
        "defect",
        "production",
        "output",
        "staff",
        "headcount",
        "team",
        "shift",
        "maintenance",
        "machine",
        "equipment",
        "calibration",
        "order",
        "capacity",
    ];
    let subject_matter = operational_subjects
        .iter()
        .any(|m| sentence_lower.contains(m));
    if !subject_matter {
        return false;
    }
    let states_predicate = [
        " is ",
        " are ",
        " has ",
        " have ",
        " was ",
        " were ",
        " runs ",
        " operates ",
        " produces ",
        " delivers ",
        " fails ",
        " exceeds ",
        " under ",
        " behind ",
        " on time",
        " stable",
        " unstable",
        " qualified",
        " unqualified",
        " unreliable",
        " understaffed",
        " overstaffed",
        " in control",
        " out of control",
        " stands at ",
        " currently ",
        " units ",
        " inventory",
        " ncr",
        " capa",
        " andon",
        " scrap",
        " defect",
        " yield of ",
        " order ",
    ]
    .iter()
    .any(|p| sentence_lower.contains(p));
    subject_matter && states_predicate
}

/// Split a reply into sentences on `.` (only when followed by whitespace
/// or end of input), `;` and newlines. A dot inside an evidence ref such
/// as "[evidence: metric.process_yield_proxy@Bizerte]" is NOT a sentence
/// boundary — the ref must survive as one token (eighteenth audit P1-7).
fn split_sentences(content: &str) -> Vec<String> {
    let mut sentences = Vec::new();
    let bytes = content.as_bytes();
    let mut start = 0;
    for (i, b) in bytes.iter().enumerate() {
        let is_boundary = match b {
            b'.' => i + 1 >= bytes.len() || bytes[i + 1].is_ascii_whitespace(),
            b';' | b'\n' => true,
            _ => false,
        };
        if is_boundary {
            if i > start {
                sentences.push(content[start..i].to_string());
            }
            start = i + 1;
            while start < bytes.len() && bytes[start].is_ascii_whitespace() {
                start += 1;
            }
        }
    }
    if start < bytes.len() {
        sentences.push(content[start..].to_string());
    }
    sentences
}

/// Extract the evidence sources referenced by a sentence, e.g.
/// "[evidence: metric.process_yield_proxy@Bizerte]" →
/// "metric.process_yield_proxy@Bizerte". Deterministic and
/// order-preserving.
fn evidence_refs_in(sentence: &str) -> Vec<String> {
    let mut refs = Vec::new();
    let mut rest = sentence;
    while let Some(start) = rest.find("[evidence:") {
        let after = &rest[start + "[evidence:".len()..];
        let Some(end) = after.find(']') else { break };
        let inner = after[..end].trim();
        if !inner.is_empty() {
            refs.push(inner.to_string());
        }
        rest = &after[end + 1..];
    }
    refs
}

/// Stream wrapper that aborts a background task when the stream is dropped.
///
/// The chat generation task is aborted as soon as the client disconnects
/// (the HTTP response body — and therefore this stream — is dropped), so a
/// disconnected client never leaves a generation task running.
struct AbortOnDrop<S> {
    inner: S,
    task: Option<JoinHandle<()>>,
}

impl<S> Drop for AbortOnDrop<S> {
    fn drop(&mut self) {
        if let Some(task) = self.task.take() {
            task.abort();
        }
    }
}

impl<S: Stream + Unpin> Stream for AbortOnDrop<S> {
    type Item = S::Item;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        Pin::new(&mut self.inner).poll_next(cx)
    }
}

/// Handle a streaming chat message via Server-Sent Events.
///
/// Returns an SSE stream where each event contains a token (or chunk) of the
/// response. The background generation task is aborted when the client
/// disconnects.
pub async fn chat_stream(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ChatRequest>,
) -> Result<Sse<impl Stream<Item = std::result::Result<Event, Infallible>>>> {
    user.require_permission("ai:inference")?;
    let sse_manager = state.sse_manager.clone();
    let chatbot_service = state.chatbot_service.clone();

    // Eighteenth audit P1-6: the stream runs through the SAME Context
    // Kernel preparation as the JSON chat — agent context, authorization
    // snapshot, deterministic plan and the prepared context bundle. The
    // stream can no longer bypass the kernel or the snapshot.
    let prepared =
        prepare_inference(&user, &state, &req.message, req.conversation_id.as_deref()).await?;

    // TOCTOU guard (sixteenth audit items 5/24): the permission state must
    // NOT have moved between snapshot capture and streaming — checked
    // BEFORE the stream task starts. In-memory deployments (no DB pool,
    // no authorization state) have nothing that can have moved — the gate
    // is vacuous there. ITEM 24: the gate is re-checked AGAIN inside the
    // task, after verification and immediately before release.
    let snapshot_ok =
        authorization_gate(state.db_pool.as_deref(), prepared.snapshot.as_ref()).await;
    // ITEM 24: the snapshot travels into the task for the release
    // re-check (a revocation that lands during generation must block the
    // release of the buffered reply).
    let snapshot = prepared.snapshot.clone();
    let db_pool_for_release = state.db_pool.clone();

    // Generate a unique channel name for this streaming session
    let channel = format!("chat-{}", uuid::Uuid::new_v4());

    // Subscribe to the channel before spawning the background task
    let rx = sse_manager.subscribe(&channel).await;

    // Spawn a background task to run the streaming chat
    let channel_clone = channel.clone();
    let sampling = req.sampling_params();
    let system_context = prepared.system_context.clone();
    // Nineteenth audit P1: the PREPARED kernel items (with their issued
    // evidence ids) travel with the stream — verification validates
    // markers against the ACTUAL evidence_id set, not flattened strings.
    let kernel_items = prepared.kernel_items.clone();
    let ctx = prepared.ctx.clone();
    let task = tokio::spawn(async move {
        // The snapshot gate decides whether streaming may START at all
        // (eighteenth audit P1-6): a stale snapshot publishes an error
        // event and returns — generation never starts.
        if !snapshot_ok {
            sse_manager
                .publish(
                    &channel_clone,
                    "error",
                    "authorization state changed during the request — re-authorized and retry",
                )
                .await;
            return;
        }
        // The PREPARED context travels INTO generation: `stream_chat`
        // receives the same system context as the JSON path, so the model
        // generates WITH the authoritative kernel bundle (eighteenth audit
        // P1: SSE consumes the Context Kernel output). The buffered reply
        // is verified against the same bundle below.
        if let Some(sys) = system_context.as_deref() {
            tracing::info!(
                channel = %channel_clone,
                context = %sys,
                "SSE chat generation running with prepared Context Kernel bundle"
            );
        }
        // Item 26: the stream carries the SAME trust guarantee as the JSON
        // chat — the full response is buffered, verified, and only then
        // released with its verification envelope.
        match chatbot_service
            .stream_chat(
                user.tenant_id,
                user.user_id,
                &req.message,
                req.conversation_id.as_deref(),
                sampling,
                system_context.as_deref(),
            )
            .await
        {
            Ok(mut token_rx) => {
                // BUFFER the full reply, then run the same claims/evidence
                // verification as the JSON chat (item 26) — the stream can
                // no longer bypass the trust contract.
                let mut buffered = String::new();
                let mut stream_error: Option<String> = None;
                while let Some(token_result) = token_rx.recv().await {
                    match token_result {
                        Ok(token) => buffered.push_str(&token),
                        Err(e) => {
                            stream_error = Some(e.to_string());
                            break;
                        }
                    }
                }
                if let Some(e) = stream_error {
                    sse_manager.publish(&channel_clone, "error", &e).await;
                    return;
                }
                // Verify the buffered reply as an ordinary ChatResponse,
                // against the PREPARED context bundle.
                let chat_response = sensei_services::ai::chatbot::ChatResponse {
                    message: sensei_services::ai::chatbot::ChatMessage {
                        role: "assistant".to_string(),
                        content: buffered.clone(),
                        timestamp: chrono::Utc::now(),
                    },
                    conversation_id: req.conversation_id.clone().unwrap_or_default(),
                    is_fallback: buffered.is_empty(),
                };
                let policy = sensei_agent_core::tools::PolicyEngine::new(
                    crate::services::agent::build_readonly_tools(),
                    sensei_agent_core::tools::ToolRisk::ReadOnly,
                );
                let effective_tools = policy.effective_tools(&ctx);
                // Thirtieth audit item 23: derived claims are recomputed
                // by the deterministic programs AFTER generation.
                let (recomputed, recompute_issues) = resolve_recomputed_derivations(
                    db_pool_for_release.as_deref(),
                    user.tenant_id,
                    ctx.site_id,
                    &req.structured_claims,
                )
                .await;
                let mut verification = verify_chat_response(
                    &chat_response,
                    &ctx,
                    &policy,
                    &effective_tools,
                    &kernel_items,
                    &req.structured_claims,
                    &recomputed,
                    &recompute_issues,
                );
                // Seventeenth audit item 7 (extended by eighteenth audit
                // P1-6): the stream's buffered reply is REPAIRED when
                // verification fails — the stream releases THE SAME repair
                // message as the JSON path, never the raw buffered reply.
                let released = if verification["verdict"].as_str() == Some("pass") {
                    buffered.clone()
                } else {
                    let issue_count = verification["issues"]
                        .as_array()
                        .map(|a| a.len())
                        .unwrap_or(0);
                    verification["verdict"] = serde_json::json!("repaired");
                    repair_message(issue_count)
                };
                // ITEM 24 — the release gate: verification completed, but
                // the authorization snapshot must STILL be current before
                // the first token is released (model execution took time;
                // a revocation may have landed while it ran). Streaming
                // already buffers the whole reply, so nothing unverified
                // was streamed and nothing can be retracted — the stale
                // release is simply refused.
                if !authorization_gate(db_pool_for_release.as_deref(), snapshot.as_ref()).await {
                    sse_manager
                        .publish(
                            &channel_clone,
                            "error",
                            "authorization state changed during the request — the \
                             answer was not released; re-authorized and retry",
                        )
                        .await;
                    return;
                }
                // Release tokens only after verification completed AND the
                // release gate passed.
                sse_manager
                    .publish(&channel_clone, "token", &released)
                    .await;
                sse_manager
                    .publish(
                        &channel_clone,
                        "verification",
                        &serde_json::to_string(&verification).unwrap_or_default(),
                    )
                    .await;
                sse_manager.publish(&channel_clone, "done", "").await;
            }
            Err(e) => {
                sse_manager
                    .publish(&channel_clone, "error", &format!("{e}"))
                    .await;
            }
        }
    });

    // Build an SSE stream from the broadcast receiver using BroadcastStream
    let broadcast_stream = BroadcastStream::new(rx);

    // Map each broadcast item into an SSE Event, filtering out lagged items
    let event_stream = broadcast_stream.filter_map(|result| {
        match result {
            Ok(msg) => Some(Ok(Event::default().data(msg))),
            Err(_) => None, // Skip lagged/dropped messages
        }
    });

    // Dropping this stream (client disconnect) aborts the generation task.
    let abort_on_drop = AbortOnDrop {
        inner: event_stream,
        task: Some(task),
    };

    Ok(Sse::new(abort_on_drop))
}

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_agent_core::context::AgentContext;
    use sensei_agent_core::facts::ContextFact;

    /// DB-gated chatbot tests share one database; a per-binary lock
    /// serializes them (same convention as the repo's DB-contract tests).
    static CHAT_DB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

    fn test_ctx() -> AgentContext {
        AgentContext {
            tenant_id: uuid::Uuid::new_v4(),
            user_id: uuid::Uuid::new_v4(),
            session_id: None,
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            shift_id: None,
            roles: vec![],
            permissions: std::collections::HashSet::new(),
            locale: "en".to_string(),
            timezone: "UTC".to_string(),
            request_id: uuid::Uuid::new_v4(),
            conversation_id: None,
        }
    }

    fn response_with(content: &str) -> sensei_services::ai::chatbot::ChatResponse {
        sensei_services::ai::chatbot::ChatResponse {
            message: sensei_services::ai::chatbot::ChatMessage::assistant(content.to_string()),
            conversation_id: "conv".to_string(),
            is_fallback: false,
        }
    }

    /// A TYPED kernel item carrying a real measured fact
    /// (WO-123 quantity_completed = 12 units) at site 1 / work center 11,
    /// observed two minutes ago — inside the work-order freshness window.
    fn typed_wo_item(completed: i64) -> sensei_agent_core::context::ContextItem {
        let site = Some(uuid::Uuid::from_u128(1));
        let wc = Some(uuid::Uuid::from_u128(11));
        let observed_at = Some(chrono::Utc::now() - chrono::Duration::minutes(2));
        let mut item = ContextFact::measured(
            "current_work",
            "work_order",
            "WO-123",
            "quantity_completed",
            completed,
            Some("units"),
            site,
            wc,
            observed_at,
            format!("wo=WO-123 product=P completed={completed}/100"),
        )
        .to_context_item();
        item.evidence_id = item.derive_evidence_id();
        item
    }

    /// A TYPED derived metric item (process_yield_proxy v1 = 0.9722…).
    fn typed_metric_item(value: f64) -> sensei_agent_core::context::ContextItem {
        let mut fact = ContextFact::measured(
            "metric_tree",
            "metric",
            "process_yield_proxy",
            "value",
            value,
            Some("ratio"),
            None,
            None,
            Some(chrono::Utc::now() - chrono::Duration::minutes(1)),
            format!("metric_id=process_yield_proxy value={value} unit=ratio"),
        );
        fact.derivation = Some(sensei_agent_core::facts::FactDerivation {
            derivation_id: "process_yield_proxy".to_string(),
            derivation_version: 1,
        });
        let mut item = fact.to_context_item();
        item.evidence_id = item.derive_evidence_id();
        item
    }

    /// Build a typed claim draft (statement in ANY language + typed
    /// assertion). `evidence` is the cited kernel item.
    #[allow(clippy::too_many_arguments)]
    fn typed_draft(
        statement: &str,
        evidence: &sensei_agent_core::context::ContextItem,
        object_type: &str,
        object_id: &str,
        attribute: &str,
        operator: ClaimOperator,
        value: serde_json::Value,
        unit: Option<&str>,
        valid_time: Option<String>,
    ) -> ClaimDraft {
        ClaimDraft {
            statement: statement.to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![evidence.evidence_id.clone()],
            assertion: Some(ClaimAssertionDraft {
                object_type: Some(object_type.to_string()),
                object_id: Some(object_id.to_string()),
                attribute: Some(attribute.to_string()),
                operator: Some(operator),
                value: Some(value),
                unit: unit.map(str::to_string),
                valid_time,
            }),
            derived: None,
        }
    }

    fn verify_ctx(
        content: &str,
        kernel_items: &[sensei_agent_core::context::ContextItem],
        ctx: &AgentContext,
    ) -> serde_json::Value {
        let policy = sensei_agent_core::tools::PolicyEngine::new(
            crate::services::agent::build_readonly_tools(),
            sensei_agent_core::tools::ToolRisk::ReadOnly,
        );
        let tools = policy.effective_tools(ctx);
        verify_chat_response(
            &response_with(content),
            ctx,
            &policy,
            &tools,
            kernel_items,
            &[],
            &HashMap::new(),
            &[],
        )
    }

    fn verify(
        content: &str,
        kernel_items: &[sensei_agent_core::context::ContextItem],
    ) -> serde_json::Value {
        let policy = sensei_agent_core::tools::PolicyEngine::new(
            crate::services::agent::build_readonly_tools(),
            sensei_agent_core::tools::ToolRisk::ReadOnly,
        );
        let tools = policy.effective_tools(&test_ctx());
        verify_chat_response(
            &response_with(content),
            &test_ctx(),
            &policy,
            &tools,
            kernel_items,
            &[],
            &HashMap::new(),
            &[],
        )
    }

    fn verify_drafts(
        content: &str,
        kernel_items: &[sensei_agent_core::context::ContextItem],
        ctx: &AgentContext,
        drafts: &[ClaimDraft],
        recomputed: &HashMap<String, RecomputedDerivation>,
        recompute_issues: &[String],
    ) -> serde_json::Value {
        let policy = sensei_agent_core::tools::PolicyEngine::new(
            crate::services::agent::build_readonly_tools(),
            sensei_agent_core::tools::ToolRisk::ReadOnly,
        );
        let tools = policy.effective_tools(ctx);
        verify_chat_response(
            &response_with(content),
            ctx,
            &policy,
            &tools,
            kernel_items,
            drafts,
            recomputed,
            recompute_issues,
        )
    }

    fn ctx_at_site_1() -> AgentContext {
        let mut ctx = test_ctx();
        ctx.site_id = Some(uuid::Uuid::from_u128(1));
        ctx.work_center_id = Some(uuid::Uuid::from_u128(11));
        ctx
    }

    #[test]
    fn verifier_flags_unverified_factual_claims() {
        let v = verify("Line 12 currently stands at 42 units of inventory.", &[]);
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims.len(), 1);
        assert_eq!(claims[0].epistemic_status, "unverified");
        assert!(claims[0].evidence_refs.is_empty());
        assert_eq!(v["claims_checked"], 1);
    }

    #[test]
    fn typed_measured_claim_passes_with_the_same_structured_assertion_in_any_language() {
        // Thirtieth audit item 23: the SAME typed assertion verifies the
        // claim whatever language the statement is written in. The prose
        // sentence is represented by the structured claim (same
        // statement), so it is verified ONCE, deterministically.
        let item = typed_wo_item(12);
        let evidence_id = item.evidence_id.clone();
        for (lang, statement) in [
            ("en", "WO-123 completed 12 units"),
            ("fr", "La commande WO-123 a terminé 12 unités"),
            ("ar", "أكمل أمر العمل WO-123 12 وحدة"),
            ("de", "WO-123 hat 12 Einheiten abgeschlossen"),
        ] {
            let ctx = ctx_at_site_1();
            let draft = typed_draft(
                statement,
                &item,
                "work_order",
                "WO-123",
                "quantity_completed",
                ClaimOperator::Equal,
                serde_json::json!(12),
                Some("units"),
                None,
            );
            let v = verify_drafts(
                statement, // the prose rendering of the same statement
                std::slice::from_ref(&item),
                &ctx,
                &[draft],
                &HashMap::new(),
                &[],
            );
            assert_eq!(
                v["verdict"], "pass",
                "[{lang}] the typed claim with the CORRECT value must pass: {:?}",
                v["issues"]
            );
            let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
            assert_eq!(claims.len(), 1, "[{lang}] one measured claim");
            assert_eq!(claims[0].epistemic_status, "measured");
            assert_eq!(claims[0].evidence_refs, vec![evidence_id.clone()]);
            assert!(claims[0].assertion.is_some());

            // The WRONG value fails in the same language — the audit's
            // canonical hole (evidence 12, claim 999).
            let ctx = ctx_at_site_1();
            let bad_draft = typed_draft(
                statement,
                &item,
                "work_order",
                "WO-123",
                "quantity_completed",
                ClaimOperator::Equal,
                serde_json::json!(999),
                Some("units"),
                None,
            );
            let v2 = verify_drafts(
                statement,
                std::slice::from_ref(&item),
                &ctx,
                &[bad_draft],
                &HashMap::new(),
                &[],
            );
            assert_eq!(
                v2["verdict"], "needs_evidence",
                "[{lang}] the typed claim with the WRONG value must fail: {:?}",
                v2["issues"]
            );
            let issues: Vec<String> = serde_json::from_value(v2["issues"].clone()).unwrap();
            assert!(
                issues
                    .iter()
                    .any(|i| i.contains("claimed value does not hold")),
                "[{lang}] the value comparison must reject the claim: {issues:?}"
            );
        }
    }

    #[test]
    fn real_evidence_wrong_object_fails() {
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let draft = typed_draft(
            "WO-456 completed 999 units",
            &item,
            "work_order",
            "WO-456",
            "quantity_completed",
            ClaimOperator::Equal,
            serde_json::json!(12),
            Some("units"),
            None,
        );
        let v = verify_drafts(
            "WO-456 completed 12 units",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("wrong object") && i.contains("WO-456")),
            "an evidence for WO-123 cannot measure a WO-456 claim: {issues:?}"
        );
    }

    #[test]
    fn real_evidence_wrong_attribute_fails() {
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let draft = typed_draft(
            "WO-123 completed quantity 999 units",
            &item,
            "work_order",
            "WO-123",
            "quantity",
            ClaimOperator::Equal,
            serde_json::json!(999),
            Some("units"),
            None,
        );
        let v = verify_drafts(
            "WO-123 completed quantity is 999 units",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("wrong attribute") && i.contains("'quantity'")),
            "quantity_completed evidence cannot measure a quantity claim: {issues:?}"
        );
    }

    #[test]
    fn real_evidence_wrong_object_type_fails() {
        // The staffing/inventory family test, deterministic: evidence of
        // object type X can never measure a claim about object type Y.
        let inv = ContextFact::measured(
            "live_state",
            "product",
            "P-42",
            "available_inventory",
            417,
            Some("units"),
            Some(uuid::Uuid::from_u128(1)),
            Some(uuid::Uuid::from_u128(11)),
            Some(chrono::Utc::now() - chrono::Duration::minutes(1)),
            "Product P-42 available inventory is 417 units.",
        );
        let mut inv_item = inv.to_context_item();
        inv_item.evidence_id = inv_item.derive_evidence_id();
        let ctx = ctx_at_site_1();
        let draft = typed_draft(
            "Tangier is severely understaffed",
            &inv_item,
            "work_center_team",
            "SMT",
            "operator_count",
            ClaimOperator::LessThan,
            serde_json::json!(6),
            Some("operators"),
            None,
        );
        let v = verify_drafts(
            "Tangier is severely understaffed.",
            std::slice::from_ref(&inv_item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(
            v["verdict"], "needs_evidence",
            "an inventory evidence cannot measure a staffing claim"
        );
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("wrong object type")),
            "{issues:?}"
        );
    }

    #[test]
    fn wrong_site_evidence_fails_and_same_site_passes() {
        // Twenty-third audit semantics, deterministic: site scope is
        // STRUCTURAL — a Bizerte (2) staffing evidence cannot measure a
        // Tangier (1) claim, and the same-site evidence passes.
        let mut bizerte = ContextFact::measured(
            "live_state",
            "work_center_team",
            "SMT",
            "operator_count",
            5,
            Some("operators"),
            Some(uuid::Uuid::from_u128(2)),
            Some(uuid::Uuid::from_u128(21)),
            Some(chrono::Utc::now() - chrono::Duration::minutes(1)),
            "Bizerte SMT line staffing: 5 operators on shift A.",
        )
        .to_context_item();
        bizerte.evidence_id = bizerte.derive_evidence_id();
        let ctx = ctx_at_site_1();
        let draft = typed_draft(
            "L'équipe SMT de Tangier manque de personnel",
            &bizerte,
            "work_center_team",
            "SMT",
            "operator_count",
            ClaimOperator::LessThan,
            serde_json::json!(6),
            Some("operators"),
            None,
        );
        let v = verify_drafts(
            "L'équipe SMT de Tangier manque de personnel.",
            std::slice::from_ref(&bizerte),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(
            v["verdict"], "needs_evidence",
            "a Tangier-scoped claim cannot be measured by Bizerte evidence"
        );
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("wrong site scope")),
            "the issue names the structural site mismatch: {issues:?}"
        );

        let mut tangier = ContextFact::measured(
            "live_state",
            "work_center_team",
            "SMT",
            "operator_count",
            5,
            Some("operators"),
            Some(uuid::Uuid::from_u128(1)),
            Some(uuid::Uuid::from_u128(11)),
            Some(chrono::Utc::now() - chrono::Duration::minutes(1)),
            "Tangier SMT line staffing: 5 operators on shift A.",
        )
        .to_context_item();
        tangier.evidence_id = tangier.derive_evidence_id();
        let draft = typed_draft(
            "L'équipe SMT de Tangier manque de personnel",
            &tangier,
            "work_center_team",
            "SMT",
            "operator_count",
            ClaimOperator::LessThan,
            serde_json::json!(6),
            Some("operators"),
            None,
        );
        let v2 = verify_drafts(
            "L'équipe SMT de Tangier manque de personnel.",
            std::slice::from_ref(&tangier),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(
            v2["verdict"], "pass",
            "same-scope evidence measures the claim"
        );
    }

    #[test]
    fn wrong_unit_fails() {
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let draft = typed_draft(
            "WO-123 completed 12 kg",
            &item,
            "work_order",
            "WO-123",
            "quantity_completed",
            ClaimOperator::Equal,
            serde_json::json!(12),
            Some("kg"),
            None,
        );
        let v = verify_drafts(
            "WO-123 completed 12 kg",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("unit mismatch") && i.contains("kg")),
            "{issues:?}"
        );
    }

    #[test]
    fn wrong_valid_time_fails() {
        // The claim asserts the fact held TWO DAYS ago; the evidence
        // observed it two minutes ago. Claim time and evidence time never
        // coincide and the claim time is out of freshness.
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let claimed_time = (chrono::Utc::now() - chrono::Duration::days(2)).to_rfc3339();
        let draft = typed_draft(
            "WO-123 completed 12 units as of two days ago",
            &item,
            "work_order",
            "WO-123",
            "quantity_completed",
            ClaimOperator::Equal,
            serde_json::json!(12),
            Some("units"),
            Some(claimed_time),
        );
        let v = verify_drafts(
            "WO-123 completed 12 units.",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("wrong valid time") || i.contains("out-of-freshness")),
            "a claim time the evidence never observed must fail: {issues:?}"
        );
    }

    #[test]
    fn measured_claim_requires_a_typed_assertion() {
        // A structured claim with a REAL evidence id but NO typed
        // assertion cannot be measured — without operator/value there is
        // nothing to reject a false value with.
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let draft = ClaimDraft {
            statement: "WO-123 completed 999 units".to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![item.evidence_id.clone()],
            assertion: None,
            derived: None,
        };
        let v = verify_drafts(
            "WO-123 completed 999 units.",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims[0].epistemic_status, "unverified");
        assert!(
            claims[0]
                .evidence_refs
                .iter()
                .any(|r| r == &item.evidence_id),
            "the real evidence id stays recorded on the unverified claim"
        );
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("must carry a typed ClaimAssertion")),
            "{issues:?}"
        );
    }

    #[test]
    fn prose_without_structured_representation_is_flagged_not_measured() {
        // The prose scanner is DEFENSE-IN-DEPTH: a factual sentence with a
        // REAL evidence marker but no typed claim in the structured
        // channel is never measured — it is flagged as unrepresented
        // prose and the reply is repaired.
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let v = verify_ctx(
            &format!(
                "The work order WO-123 has completed 12 units [evidence: {}].",
                item.evidence_id
            ),
            std::slice::from_ref(&item),
            &ctx,
        );
        assert_eq!(
            v["verdict"], "needs_evidence",
            "real evidence id alone cannot measure prose"
        );
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("rendered only in prose")),
            "{issues:?}"
        );
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims[0].epistemic_status, "unverified");
    }

    #[test]
    fn verifier_flags_qualitative_live_state_claims() {
        let v = verify(
            "Production is running. The order will be delivered on time.",
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims.len(), 2, "both sentences are unverified claims");
        assert!(
            claims.iter().all(|c| c.epistemic_status == "unverified"),
            "qualitative claims without evidence are unverified"
        );
    }

    #[test]
    fn verifier_flags_qualitative_assertions_about_entities() {
        let v = verify("The Tangier line is severely understaffed.", &[]);
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims.len(), 1);
        assert_eq!(claims[0].epistemic_status, "unverified");
        let v2 = verify("The process is under control.", &[]);
        assert_eq!(v2["verdict"], "needs_evidence");
    }

    #[test]
    fn verifier_flags_evidence_marker_not_in_evidence_id_set() {
        let item = typed_wo_item(12);
        let v = verify(
            "Line 12 currently stands at 42 units [evidence: nope.missing@nowhere].",
            &[item],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims[0].epistemic_status, "unverified");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(issues
            .iter()
            .any(|i| i.contains("Unverified evidence reference") && i.contains("nope.missing")));
    }

    #[test]
    fn verifier_does_not_match_marker_against_context_substrings() {
        // Nineteenth audit P1 regression: the OLD check accepted any
        // marker whose text appeared as a SUBSTRING of a context line.
        // The typed check requires the marker to BE the evidence_id of a
        // prepared item — a source name that merely appears inside the
        // payload text is NOT evidence.
        let item = typed_wo_item(12);
        let v = verify(
            "The work order has completed 12 units [evidence: work_order].",
            std::slice::from_ref(&item),
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims[0].epistemic_status, "unverified");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("Unverified evidence reference") && i.contains("work_order")),
            "{issues:?}"
        );
    }

    #[test]
    fn fake_evidence_marker_in_unclassified_prose_fails() {
        // Thirtieth audit item 23: EVERY [evidence: ...] marker is parsed
        // on every sentence, whether or not the sentence classifies as a
        // factual claim — a fabricated citation can never hide inside
        // prose the lexical scanner ignores ("Merci beaucoup" is not a
        // factual claim by any heuristic).
        let v = verify(
            "Merci beaucoup pour votre aide [evidence: ev:made-up-marker]. Au revoir.",
            &[],
        );
        assert_eq!(
            v["verdict"], "needs_evidence",
            "the fake marker must be caught even in unclassified prose"
        );
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("Unverified evidence reference")
                    && i.contains("ev:made-up-marker")),
            "{issues:?}"
        );
    }

    #[test]
    fn real_evidence_marker_in_unclassified_prose_passes() {
        // A real marker inside a non-factual sentence is valid — the
        // marker parsing is independent of the claim classification, and
        // no unrepresented factual prose exists here.
        let item = typed_wo_item(12);
        let v = verify(
            &format!("Merci beaucoup [evidence: {}].", item.evidence_id),
            &[item],
        );
        assert_eq!(v["verdict"], "pass");
    }

    #[test]
    fn derived_claim_wrong_math_fails() {
        // The deterministic program recomputed 0.9722…; the claim asserts
        // 0.99 → rejected. With the correct result the claim is measured.
        let item = typed_metric_item(0.9722222222222222);
        let recomputed = RecomputedDerivation {
            derivation_id: "process_yield_proxy".to_string(),
            version: 1,
            value: serde_json::json!(0.9722222222222222),
            unit: Some("ratio".to_string()),
            recomputed_at: chrono::Utc::now(),
        };
        let mut recomputed_map = HashMap::new();
        recomputed_map.insert(derivation_key("process_yield_proxy", 1), recomputed);
        let ctx = ctx_at_site_1();
        let bad = ClaimDraft {
            statement: "First pass yield is 0.99".to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![item.evidence_id.clone()],
            assertion: None,
            derived: Some(DerivedClaimDraft {
                derivation_id: "process_yield_proxy".to_string(),
                derivation_version: 1,
                operand_evidence_ids: vec![item.evidence_id.clone()],
                result: Some(serde_json::json!(0.99)),
                unit: Some("ratio".to_string()),
            }),
        };
        let v = verify_drafts(
            "First pass yield is 0.99.",
            std::slice::from_ref(&item),
            &ctx,
            &[bad],
            &recomputed_map,
            &[],
        );
        assert_eq!(
            v["verdict"], "needs_evidence",
            "wrong derived math must fail: {:?}",
            v["issues"]
        );
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("derived claim does not hold")),
            "{issues:?}"
        );

        // The CORRECT derived claim is measured against the recomputation.
        let good = ClaimDraft {
            statement: "First pass yield is 0.9722".to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![item.evidence_id.clone()],
            assertion: None,
            derived: Some(DerivedClaimDraft {
                derivation_id: "process_yield_proxy".to_string(),
                derivation_version: 1,
                operand_evidence_ids: vec![item.evidence_id.clone()],
                result: Some(serde_json::json!(0.9722222222222222)),
                unit: Some("ratio".to_string()),
            }),
        };
        let v2 = verify_drafts(
            "First pass yield is 0.9722.",
            std::slice::from_ref(&item),
            &ctx,
            &[good],
            &recomputed_map,
            &[],
        );
        assert_eq!(v2["verdict"], "pass", "{:?}", v2["issues"]);
        let claims: Vec<Claim> = serde_json::from_value(v2["claims"].clone()).unwrap();
        assert_eq!(claims[0].epistemic_status, "measured");
        assert!(claims[0].derived.is_some());
    }

    #[test]
    fn derived_claim_without_server_recomputation_fails_closed() {
        let item = typed_metric_item(0.9722222222222222);
        let ctx = ctx_at_site_1();
        let draft = ClaimDraft {
            statement: "First pass yield is 0.9722".to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![item.evidence_id.clone()],
            assertion: None,
            derived: Some(DerivedClaimDraft {
                derivation_id: "process_yield_proxy".to_string(),
                derivation_version: 1,
                operand_evidence_ids: vec![],
                result: Some(serde_json::json!(0.9722222222222222)),
                unit: Some("ratio".to_string()),
            }),
        };
        // The recompute resolution failed server-side (no live program):
        // the derived claim is rejected, never accepted against the
        // prepared evidence value alone.
        let recompute_issues = vec![
            "derived claim 'process_yield_proxy'@v1 could not be recomputed — no live \\
             deterministic derivation program is available for this request"
                .to_string(),
        ];
        let v = verify_drafts(
            "First pass yield is 0.9722.",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &recompute_issues,
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("could not be recomputed")),
            "{issues:?}"
        );
    }

    #[test]
    fn derived_claim_unknown_program_fails_closed() {
        let ctx = ctx_at_site_1();
        let draft = ClaimDraft {
            statement: "The made-up index is 97.2".to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![],
            assertion: None,
            derived: Some(DerivedClaimDraft {
                derivation_id: "made_up_index".to_string(),
                derivation_version: 1,
                operand_evidence_ids: vec![],
                result: Some(serde_json::json!(97.2)),
                unit: Some("ratio".to_string()),
            }),
        };
        let v = verify_drafts(
            "The made-up index is 97.2.",
            &[],
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("could not be recomputed")),
            "a derivation id with no deterministic program is rejected: {issues:?}"
        );
    }

    #[test]
    fn evidence_refs_in_extracts_markers() {
        assert_eq!(
            evidence_refs_in(
                "yield is 42 [evidence: metric.process_yield_proxy@Bizerte] [evidence: second.ref]."
            ),
            vec![
                "metric.process_yield_proxy@Bizerte".to_string(),
                "second.ref".to_string()
            ]
        );
        assert!(evidence_refs_in("no markers here").is_empty());
    }

    #[test]
    fn split_sentences_keeps_evidence_refs_intact() {
        assert_eq!(
            split_sentences(
                "Yield is 42 [evidence: metric.process_yield_proxy@Bizerte]. And it is rising."
            ),
            vec![
                "Yield is 42 [evidence: metric.process_yield_proxy@Bizerte]".to_string(),
                "And it is rising".to_string()
            ]
        );
        assert_eq!(
            split_sentences(
                "a. b; c
d"
            ),
            vec![
                "a".to_string(),
                "b".to_string(),
                "c".to_string(),
                "d".to_string()
            ]
        );
    }

    #[test]
    fn repair_message_is_shared_between_json_and_stream() {
        let msg = repair_message(3);
        assert!(msg.contains("I can only answer with claims verified"));
        assert!(msg.contains("3 issue(s)"));
    }

    #[test]
    fn site_marked_context_line_survives_parsing_with_site_scope() {
        let site = uuid::Uuid::from_u128(42);
        let line = format!("current_work [live site:{site}]: wo=WO-7 product=P completed=10/50");
        let (section, content, source_site) =
            parse_context_line(&line).expect("a site-marked line must never be dropped");
        assert_eq!(section, "current_work");
        assert_eq!(content, "wo=WO-7 product=P completed=10/50");
        assert_eq!(
            source_site,
            Some(site),
            "the parsed source site must become the evidence site scope"
        );
        let (section, content, source_site) =
            parse_context_line("live_state [live]: condition=COND-1 status=open").unwrap();
        assert_eq!(section, "live_state");
        assert_eq!(content, "condition=COND-1 status=open");
        assert_eq!(source_site, None);
        let (section, content, source_site) =
            parse_context_line("no additional context for this task").unwrap();
        assert_eq!(section, "");
        assert!(content.contains("no additional context"));
        assert_eq!(source_site, None);
    }

    #[test]
    fn caller_assumed_draft_cannot_bypass_the_factual_check() {
        // An unevidenced caller draft (whatever its declared kind) is
        // never measured — it raises the unverified-fact issue.
        let ctx = test_ctx();
        let draft = ClaimDraft {
            statement: "La ligne de Tangier manque de personnel".to_string(),
            epistemic_kind: "assumed".to_string(),
            fact_address: None,
            evidence_ids: vec![],
            assertion: None,
            derived: None,
        };
        let v = verify_drafts("", &[], &ctx, &[draft], &HashMap::new(), &[]);
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("Unverified factual claim")),
            "{issues:?}"
        );
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims.len(), 1);
        assert_eq!(claims[0].epistemic_status, "unverified");
        assert_eq!(
            claims[0].statement,
            "La ligne de Tangier manque de personnel"
        );
        assert_eq!(v["claims_checked"], 1);
    }

    #[test]
    fn caller_recommended_draft_cannot_suppress_prose_verification() {
        let ctx = test_ctx();
        let draft = ClaimDraft {
            statement: "Check the issue.".to_string(),
            epistemic_kind: "recommended".to_string(),
            fact_address: None,
            evidence_ids: vec![],
            assertion: None,
            derived: None,
        };
        let v = verify_drafts(
            "Tangier inventory has fallen to 12 units.",
            &[],
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims.len(), 2);
        let prose = claims
            .iter()
            .find(|c| c.statement == "Tangier inventory has fallen to 12 units")
            .expect("the prose claim is scanned even when structured claims are present");
        assert_eq!(prose.epistemic_status, "unverified");
        assert!(prose.evidence_refs.is_empty());
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("Unverified factual claim")
                && i.contains("Tangier inventory has fallen to 12 units")),
            "{issues:?}"
        );
    }

    #[test]
    fn french_prose_with_unevidenced_caller_draft_is_flagged() {
        let ctx = test_ctx();
        let draft = ClaimDraft {
            statement: "La ligne est instable.".to_string(),
            epistemic_kind: "measured".to_string(),
            fact_address: None,
            evidence_ids: vec![],
            assertion: None,
            derived: None,
        };
        let v = verify_drafts(
            "La ligne est instable.",
            &[],
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "needs_evidence");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues
                .iter()
                .any(|i| i.contains("Unverified factual claim") && i.contains("instable")),
            "{issues:?}"
        );
    }

    #[test]
    fn structured_french_measured_draft_with_typed_assertion_is_rejected_by_wrong_site() {
        // Twenty-seventh audit P1 in its deterministic form: a French
        // measured draft carrying a TYPED assertion is rejected by the
        // STRUCTURAL site check — no English word appears anywhere.
        let mut bizerte = ContextFact::measured(
            "live_state",
            "work_center_team",
            "SMT",
            "operator_count",
            8,
            Some("operators"),
            Some(uuid::Uuid::from_u128(2)),
            Some(uuid::Uuid::from_u128(21)),
            Some(chrono::Utc::now() - chrono::Duration::minutes(1)),
            "Bizerte SMT line staffing: 8 operators on shift A.",
        )
        .to_context_item();
        bizerte.evidence_id = bizerte.derive_evidence_id();
        let mut ctx = ctx_at_site_1();
        ctx.work_center_id = None;
        let draft = typed_draft(
            "La ligne SMT de Bizerte est sous-effectuée",
            &bizerte,
            "work_center_team",
            "SMT",
            "operator_count",
            ClaimOperator::GreaterThanOrEqual,
            serde_json::json!(8),
            Some("operators"),
            None,
        );
        let v = verify_drafts(
            "La ligne SMT de Bizerte est sous-effectuée.",
            std::slice::from_ref(&bizerte),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(
            v["verdict"], "needs_evidence",
            "wrong-site evidence cannot measure the French claim"
        );
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims.len(), 1);
        let french = &claims[0];
        assert_eq!(
            french.statement,
            "La ligne SMT de Bizerte est sous-effectuée"
        );
        assert_eq!(french.epistemic_status, "unverified");
        let issues: Vec<String> = serde_json::from_value(v["issues"].clone()).unwrap();
        assert!(
            issues.iter().any(|i| i.contains("wrong site scope")),
            "{issues:?}"
        );
    }

    #[test]
    fn typed_draft_address_verifies_without_any_english_keyword() {
        // The old subject-family resolution is gone: the typed assertion
        // itself names the fact address, so a French statement verifies
        // against the same-object evidence with zero lexical analysis.
        let item = typed_wo_item(12);
        let ctx = ctx_at_site_1();
        let draft = typed_draft(
            "La commande WO-123 a terminé 12 unités",
            &item,
            "work_order",
            "WO-123",
            "quantity_completed",
            ClaimOperator::Equal,
            serde_json::json!(12),
            Some("units"),
            None,
        );
        let v = verify_drafts(
            "",
            std::slice::from_ref(&item),
            &ctx,
            &[draft],
            &HashMap::new(),
            &[],
        );
        assert_eq!(v["verdict"], "pass", "{:?}", v["issues"]);
        let claims: Vec<Claim> = serde_json::from_value(v["claims"].clone()).unwrap();
        assert_eq!(claims[0].epistemic_status, "measured");
        assert_eq!(claims[0].evidence_refs, vec![item.evidence_id.clone()]);
    }

    // ── item 24: authorization release gate ──────────────────────────

    #[test]
    fn release_gate_without_authorization_state_is_vacuous() {
        // In-memory deployments have no DB-backed authorization state:
        // nothing can have moved, so the release gate is open (content
        // verification still repairs unverified claims).
        let gate = tokio_test_block_on(authorization_gate(None, None));
        assert!(gate);
        assert!(!authorization_gate_sync(
            None,
            Some(&AuthzSnapshot {
                tenant: uuid::Uuid::new_v4(),
                principal: uuid::Uuid::new_v4(),
                roles: vec![],
                policy_revision: 0,
                relationship_revision: 0,
                principal_revision: 0,
                scope_site: None,
                permission_digest: [0u8; 32],
            })
        ));
    }

    fn tokio_test_block_on<F: std::future::Future>(f: F) -> F::Output {
        tokio::runtime::Runtime::new().unwrap().block_on(f)
    }

    fn authorization_gate_sync(db_pool: Option<&PgPool>, snapshot: Option<&AuthzSnapshot>) -> bool {
        tokio_test_block_on(authorization_gate(db_pool, snapshot))
    }

    /// PG-gated item 24 test: the release gate must observe a revision
    /// bump between snapshot capture and release. Requires a live
    /// PostgreSQL test database (DATABASE_URL_TEST); skipped otherwise —
    /// same convention as the repo's other DB-contract tests (drop every
    /// table, re-apply the FULL migration chain, then exercise the gate).
    #[tokio::test]
    async fn post_generation_revocation_fails_the_release_gate() {
        let _serial = CHAT_DB_LOCK.lock().await;
        let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
            eprintln!("SKIP: DATABASE_URL_TEST not set — release-gate revocation runs in CI");
            return;
        };
        let Ok(pool) = sqlx::PgPool::connect(&url).await else {
            return;
        };
        // Disposable test database: reset to the FULL migration chain.
        sqlx::query(
            r#"DO $$ DECLARE r RECORD; BEGIN
                 FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                     EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
                 END LOOP;
             END $$"#,
        )
        .execute(&pool)
        .await
        .expect("drop all tables");
        sensei_db::migrations::run_migrations(&pool)
            .await
            .expect("the ENTIRE migration chain must apply to an empty database");

        let tenant_id = uuid::Uuid::new_v4();
        // authorization_revisions.tenant_id REFERENCES tenants(id) — the
        // snapshot's lazy seed fails the FK unless the tenant exists
        // first (same tenant-seed convention as the repo's other
        // DB-gated suites).
        sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $3)")
            .bind(tenant_id)
            .bind("Chatbot Release Gate Tenant")
            .bind(format!("chat-release-gate-{tenant_id}"))
            .execute(&pool)
            .await
            .expect("tenant seed");
        // T0: capture the request's authorization snapshot (lazily seeds
        // the tenant's revision row at 1/1/1).
        let snapshot =
            sensei_services::tps::authorization_revisions::current_snapshot(&pool, tenant_id)
                .await
                .expect("current snapshot");
        let snap = AuthzSnapshot {
            tenant: tenant_id,
            principal: uuid::Uuid::new_v4(),
            roles: vec!["operator".to_string()],
            policy_revision: snapshot.policy_revision,
            relationship_revision: snapshot.relationship_revision,
            principal_revision: snapshot.principal_revision,
            scope_site: None,
            permission_digest: [0u8; 32],
        };
        // T0: unchanged → the release gate is open.
        assert!(
            authorization_gate(Some(&pool), Some(&snap)).await,
            "an unchanged revision triple releases"
        );
        // T2: a revocation lands (principal revision bump) while the
        // model is still executing.
        sensei_services::tps::authorization_revisions::bump_principal(&pool, tenant_id)
            .await
            .expect("principal revision bump");
        // T3/T4: the release gate must now REFUSE the release.
        assert!(
            !authorization_gate(Some(&pool), Some(&snap)).await,
            "a revision change between snapshot and release must block the release"
        );
    }
}

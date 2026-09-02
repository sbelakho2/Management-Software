//! Read-only tool-bound AI surface (audit Phase 3): the server builds the
//! AgentContext, the policy engine filters the caller's toolset, and tool
//! execution re-validates permissions and returns evidence-carrying
//! results. No production writes — the agent inherits the user's rights,
//! never widens them.

use axum::extract::State;
use axum::Json;
use sensei_agent_core::context::AgentContext;
use sensei_agent_core::tools::{PolicyEngine, ToolRisk, ToolSpec};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::SenseiError;
use uuid::Uuid;

use crate::services::agent::{build_readonly_tools, execute_tool};
use crate::state::AppState;

/// The caller's server-created agent context + effective toolset.
pub async fn list_agent_tools(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, SenseiError> {
    user.require_permission("ai:inference")?;
    let ctx = build_context(&user, &state).await;
    let policy = PolicyEngine::new(build_readonly_tools(), ToolRisk::ReadOnly);
    let effective: Vec<&ToolSpec> = policy.effective_tools(&ctx);
    Ok(Json(serde_json::json!({
        "context": ctx,
        "effective_tools": effective.iter().map(|t| serde_json::json!({
            "name": t.name,
            "version": t.version,
            "risk": format!("{:?}", t.risk),
            "required_permission": t.required_permission,
            "timeout_ms": t.timeout_ms,
            "max_rows": t.max_rows,
            "idempotent": t.idempotent,
        })).collect::<Vec<_>>(),
    })))
}

/// Execute one read-only tool with a fresh permission + evidence contract.
pub async fn execute_agent_tool(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ExecuteToolRequest>,
) -> Result<Json<serde_json::Value>, SenseiError> {
    user.require_permission("ai:inference")?;
    let ctx = build_context(&user, &state).await;
    let tools = build_readonly_tools();
    let policy = PolicyEngine::new(tools.clone(), ToolRisk::ReadOnly);
    let tool = tools
        .iter()
        .find(|t| t.name == req.tool)
        .ok_or_else(|| SenseiError::NotFound(format!("Unknown tool '{}'", req.tool)))?;
    let result = execute_tool(
        &ctx,
        tool,
        req.args
            .unwrap_or(serde_json::Value::Object(Default::default())),
        &policy,
        state.production_service.as_ref(),
        state.supply_chain_service.as_ref(),
        state.db_pool.as_ref().map(|p| p.as_ref()),
    )
    .await
    .map_err(SenseiError::Validation)?;

    // The deterministic verifier runs IN the response path: freshness is
    // measured against the evidence's own observed_at (source time, not
    // tool-call time).
    let freshness = match tool.name.as_str() {
        "get_inventory_balance" => sensei_agent_core::evidence::FreshnessClass::Minutes,
        _ => sensei_agent_core::evidence::FreshnessClass::Hours,
    };
    let claim = sensei_agent_core::claims::Claim {
        id: Uuid::new_v4(),
        kind: sensei_agent_core::claims::ClaimKind::ObservedFact,
        statement: format!("tool '{}' result", tool.name),
        evidence_refs: result.evidence.clone(),
        deterministic_calculation: None,
        confidence: None,
        created_at: chrono::Utc::now(),
    };
    let verification = sensei_agent_core::verifier::verify(
        &[claim],
        &policy,
        &ctx.permissions.iter().cloned().collect::<Vec<_>>(),
        std::slice::from_ref(tool),
        &[],
        &[(0, freshness)],
    );
    Ok(Json(serde_json::json!({
        "result": result,
        "verification": {
            "verdict": format!("{:?}", verification.verdict),
            "issues": verification.issues,
        },
    })))
}

/// Request: tool name + args.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ExecuteToolRequest {
    pub tool: String,
    pub args: Option<serde_json::Value>,
}

/// Build the SERVER-CREATED context from the authenticated request (the
/// model can never supply tenant/user/site — they are injected here).
pub async fn build_context(user: &AuthenticatedUser, state: &AppState) -> AgentContext {
    build_context_with_locale(user, state, None).await
}

/// Item 59: the agent locale comes from the caller's session/headers (the
/// UI language), never a hardcoded "en".
pub async fn build_context_with_locale(
    user: &AuthenticatedUser,
    state: &AppState,
    accept_language: Option<&str>,
) -> AgentContext {
    let rbac = sensei_auth::rbac::authorization_service();
    let mut permissions = std::collections::HashSet::new();
    for role in &user.roles {
        // Same resolution as HTTP authorization: system + tenant-scoped
        // custom role permissions (item 18 — no disagreement between the
        // two layers).
        for perm in rbac.permissions_for_role_in_tenant(user.tenant_id, role) {
            permissions.insert(perm);
        }
    }
    // Twentieth audit P1 + twenty-first audit item 6 (one-pass operating
    // scope): scope resolution goes through the ONE authoritative builder
    // — RequestContext (entitlement membership + topology chain proof).
    // users.site_id survives only as a hint that must PASS the
    // entitlement check. The newest ACTIVE employee_assignment is a
    // CANDIDATE tuple (site + value stream + work center + shift), never
    // an independent scope authority: it is passed INTO the SAME
    // RequestContext::build call, and only the VALIDATED rc.active_*
    // values are copied into the AgentContext — a stale assignment whose
    // sub-scopes drifted to another site can no longer re-enter the
    // context after validation.
    let user_row = state.users_service.find_by_id(user.user_id).await.ok();
    let hint_site = user_row.as_ref().and_then(|u| u.site_id);
    let mut value_stream_id = None;
    let mut work_center_id = None;
    let mut shift_id = None;
    let mut site_id = None;
    let mut timezone = "UTC".to_string();
    if let Some(pool) = state.db_pool.as_ref() {
        let mut candidate_vs = None;
        let mut candidate_wc = None;
        let mut candidate_shift = None;
        if hint_site.is_some() {
            let assignment: Option<(Option<Uuid>, Option<Uuid>, Option<Uuid>)> = sqlx::query_as(
                "SELECT value_stream_id, work_center_id, shift_id \
                         FROM employee_assignments \
                         WHERE tenant_id = $1 AND user_id = $2 AND is_active = TRUE \
                           AND site_id = $3 \
                         ORDER BY updated_at DESC LIMIT 1",
            )
            .bind(user.tenant_id)
            .bind(user.user_id)
            .bind(hint_site)
            .fetch_optional(pool.as_ref())
            .await
            .ok()
            .flatten();
            if let Some((vs, wc, sh)) = assignment {
                candidate_vs = vs;
                candidate_wc = wc;
                candidate_shift = sh;
            }
        }
        // ONE-pass validation of the whole candidate tuple: build()
        // proves the active site is entitled AND every candidate
        // sub-scope's resolved site equals the active site. On success
        // the VALIDATED active_* scope becomes the agent context.
        match sensei_core::domain::request_context::RequestContext::build(
            pool,
            user.tenant_id,
            user.user_id,
            hint_site,
            candidate_vs,
            candidate_wc,
            candidate_shift,
            String::new(),
        )
        .await
        {
            Ok(rc) => {
                site_id = rc.active_site;
                value_stream_id = rc.active_value_stream;
                work_center_id = rc.active_work_center;
                shift_id = rc.active_shift;
            }
            // Invalid combination (a stale assignment, or the hint site
            // is not entitled): fail closed — the site alone when the
            // site itself passes the entitlement check, otherwise NO
            // operating scope. The invalid sub-scopes are never copied.
            Err(_) => {
                if let Ok(rc) = sensei_core::domain::request_context::RequestContext::build(
                    pool,
                    user.tenant_id,
                    user.user_id,
                    hint_site,
                    None,
                    None,
                    None,
                    String::new(),
                )
                .await
                {
                    site_id = rc.active_site;
                }
            }
        }
        if let Some(site) = site_id {
            let tz: Option<String> =
                sqlx::query_scalar("SELECT timezone FROM sites WHERE id = $1 AND tenant_id = $2")
                    .bind(site)
                    .bind(user.tenant_id)
                    .fetch_one(pool.as_ref())
                    .await
                    .ok();
            if let Some(tz) = tz {
                timezone = tz;
            }
        }
    }
    AgentContext {
        tenant_id: user.tenant_id,
        user_id: user.user_id,
        session_id: user.sid,
        site_id,
        value_stream_id,
        work_center_id,
        shift_id,
        roles: user.roles.clone(),
        permissions,
        // Item 59: the EMPLOYEE PROFILE locale wins — a French operator's
        // profile is authoritative even when the browser sends en-US.
        // Accept-Language is only a fallback for profiles without a
        // preference.
        locale: user_row
            .as_ref()
            .map(|u| u.locale.clone())
            .filter(|l| ["en", "fr", "ar", "de", "es"].contains(&l.as_str()))
            .or_else(|| {
                accept_language
                    .and_then(|h| h.split(',').next())
                    .map(|tag| tag.trim().split('-').next().unwrap_or("en").to_string())
                    .filter(|l| ["en", "fr", "ar", "de", "es"].contains(&l.as_str()))
            })
            .unwrap_or_else(|| "en".to_string()),
        timezone,
        request_id: Uuid::new_v4(),
        conversation_id: None,
    }
}

/// Deterministic execution key for the command journal (eighteenth
/// audit P1-14): tool name + canonical args JSON. The same call with
/// the same args always produces the same key.
pub fn execution_key(
    tool: &sensei_agent_core::tools::ToolSpec,
    args: &serde_json::Value,
) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(tool.name.as_bytes());
    hasher.update(b"|");
    hasher.update(serde_json::to_string(args).unwrap_or_default().as_bytes());
    hex::encode(hasher.finalize())
}

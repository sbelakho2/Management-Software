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
async fn build_context(user: &AuthenticatedUser, state: &AppState) -> AgentContext {
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
    // The employee's active site assignment is resolved at request time
    // (item 17): the agent knows WHERE the user works.
    let site_id = state
        .users_service
        .find_by_id(user.user_id)
        .await
        .ok()
        .and_then(|u| u.site_id);
    AgentContext {
        tenant_id: user.tenant_id,
        user_id: user.user_id,
        session_id: user.sid,
        site_id,
        value_stream_id: None,
        work_center_id: None,
        shift_id: None,
        roles: user.roles.clone(),
        permissions,
        locale: "en".to_string(),
        timezone: "UTC".to_string(),
        request_id: Uuid::new_v4(),
        conversation_id: None,
    }
}

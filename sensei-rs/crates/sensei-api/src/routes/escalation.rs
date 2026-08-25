//! Escalation policy management route handlers.
//!
//! Provides CRUD endpoints for alert escalation policies.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{EscalationPolicy, EscalationRule};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing escalation policies.
#[derive(Debug, Deserialize)]
pub struct ListPoliciesParams {
    pub event_type: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating an escalation policy.
#[derive(Debug, Deserialize)]
pub struct PolicyRequest {
    pub name: String,
    pub description: String,
    pub event_type: String,
    pub is_active: bool,
    pub rules: Vec<EscalationRule>,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Validate an escalation policy's rules before storing them.
///
/// Each rule must escalate after a positive delay and must name at least
/// one notification target (a role or explicit users).
fn validate_rules(rules: &[EscalationRule]) -> Result<()> {
    if rules.is_empty() {
        return Err(SenseiError::Validation(
            "An escalation policy must define at least one rule".to_string(),
        ));
    }
    for rule in rules {
        if rule.escalate_after_seconds <= 0 {
            return Err(SenseiError::Validation(format!(
                "Rule '{}' has invalid escalate_after_seconds {}: must be greater than 0",
                rule.condition, rule.escalate_after_seconds
            )));
        }
        if rule.notify_role.is_none() && rule.notify_user_ids.is_empty() {
            return Err(SenseiError::Validation(format!(
                "Rule '{}' must notify at least one role or user",
                rule.condition
            )));
        }
    }
    Ok(())
}

/// List all escalation policies with optional filters.
pub async fn list_policies(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListPoliciesParams>,
) -> Result<Json<PaginatedResponse<EscalationPolicy>>> {
    let store = state.escalation_policies.read(user.tenant_id).await;
    let mut policies: Vec<EscalationPolicy> = store
        .values()
        .filter(|p| p.tenant_id == user.tenant_id)
        .filter(|p| {
            params
                .event_type
                .as_ref()
                .is_none_or(|t| p.event_type == *t)
        })
        .filter(|p| params.is_active.is_none_or(|a| p.is_active == a))
        .cloned()
        .collect();
    policies.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
    let result = PaginatedResponse::new(policies, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new escalation policy.
pub async fn create_policy(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<PolicyRequest>,
) -> Result<Json<EscalationPolicy>> {
    validate_rules(&req.rules)?;
    let now = Utc::now();
    let policy = EscalationPolicy {
        id: new_id(),
        tenant_id: user.tenant_id,
        name: req.name,
        description: req.description,
        event_type: req.event_type,
        is_active: req.is_active,
        rules: req.rules,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.escalation_policies.write(user.tenant_id).await;
    store.insert(policy.id, policy.clone());
    Ok(Json(policy))
}

/// Get a specific escalation policy by ID.
pub async fn get_policy(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<EscalationPolicy>> {
    let store = state.escalation_policies.read(user.tenant_id).await;
    let policy = store
        .values()
        .find(|p| p.id == id && p.tenant_id == user.tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Escalation policy {id} not found")))?;
    Ok(Json(policy))
}

/// Update an escalation policy.
pub async fn update_policy(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<PolicyRequest>,
) -> Result<Json<EscalationPolicy>> {
    validate_rules(&req.rules)?;
    let mut store = state.escalation_policies.write(user.tenant_id).await;
    let policy = store
        .get_mut(&id)
        .filter(|p| p.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Escalation policy {id} not found")))?;
    policy.name = req.name;
    policy.description = req.description;
    policy.event_type = req.event_type;
    policy.is_active = req.is_active;
    policy.rules = req.rules;
    policy.updated_at = Utc::now();
    Ok(Json(policy.clone()))
}

/// Delete an escalation policy.
pub async fn delete_policy(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let mut store = state.escalation_policies.write(user.tenant_id).await;
    let exists = store
        .get(&id)
        .filter(|p| p.tenant_id == user.tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!(
            "Escalation policy {id} not found"
        )));
    }
    store.remove(&id);
    Ok(Json(()))
}

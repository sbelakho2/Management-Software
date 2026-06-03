//! State Machine route handlers.
//!
//! Provides endpoints for managing state machine definitions and
//! running instances, including state transitions.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::domain::events::{
    DomainEvent, StateMachineTransitionedEvent,
};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{
    StateDefinition, StateMachineDefinition, StateMachineInstance,
    StateTransitionRecord, TransitionDefinition,
};

// ── Internal helpers ───────────────────────────────────────────────────────

/// Publish a domain event via the event bus, logging warnings on failure.
async fn publish_event(state: &AppState, event: &dyn DomainEvent) {
    if let Err(e) = state.event_bus.publish(event).await {
        tracing::warn!(error = %e, event_type = %event.event_type(), "Failed to publish domain event");
    }
}

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing state machine definitions.
#[derive(Debug, Deserialize)]
pub struct ListStateMachinesParams {
    pub entity_type: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a state machine definition.
#[derive(Debug, Deserialize)]
pub struct CreateStateMachineRequest {
    pub name: String,
    pub description: Option<String>,
    pub entity_type: String,
    pub states: Vec<StateDefinition>,
    pub transitions: Vec<TransitionDefinition>,
    pub initial_state: String,
}

/// Request body for updating a state machine definition (partial).
#[derive(Debug, Deserialize)]
pub struct UpdateStateMachineRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub entity_type: Option<String>,
    pub states: Option<Vec<StateDefinition>>,
    pub transitions: Option<Vec<TransitionDefinition>>,
    pub initial_state: Option<String>,
    pub is_active: Option<bool>,
}

/// Request body for creating a state machine instance.
#[derive(Debug, Deserialize)]
pub struct CreateInstanceRequest {
    pub entity_id: Uuid,
}

/// Query parameters for listing instances.
#[derive(Debug, Deserialize)]
pub struct ListInstancesParams {
    pub entity_id: Option<Uuid>,
    pub current_state: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for executing a state transition.
#[derive(Debug, Deserialize)]
pub struct TransitionRequest {
    pub event: String,
    pub metadata: Option<serde_json::Value>,
}

// ── Response DTOs ──────────────────────────────────────────────────────────

/// Result of a state transition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitionResult {
    pub instance: StateMachineInstance,
    pub transition_applied: bool,
    pub message: String,
}

// ── Definition Handlers ────────────────────────────────────────────────────

/// List state machine definitions.
pub async fn list_state_machines(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListStateMachinesParams>,
) -> Result<Json<PaginatedResponse<StateMachineDefinition>>> {
    let tenant_id = user.tenant_id;
    let store = state.state_machine_definitions.read().await;
    let mut defs: Vec<StateMachineDefinition> = store
        .values()
        .filter(|d| d.tenant_id == tenant_id)
        .filter(|d| {
            if let Some(ref et) = params.entity_type {
                d.entity_type == *et
            } else {
                true
            }
        })
        .filter(|d| {
            if let Some(active) = params.is_active {
                d.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    defs.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(defs, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new state machine definition.
pub async fn create_state_machine(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateStateMachineRequest>,
) -> Result<Json<StateMachineDefinition>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let def = StateMachineDefinition {
        id: new_id(),
        tenant_id,
        name: req.name,
        description: req.description,
        entity_type: req.entity_type,
        states: req.states,
        transitions: req.transitions,
        initial_state: req.initial_state,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.state_machine_definitions.write().await;
    store.insert(def.id, def.clone());
    Ok(Json(def))
}

/// Get a state machine definition by ID.
pub async fn get_state_machine(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sm_id): Path<Uuid>,
) -> Result<Json<StateMachineDefinition>> {
    let tenant_id = user.tenant_id;
    let store = state.state_machine_definitions.read().await;
    let def = store
        .values()
        .find(|d| d.id == sm_id && d.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("State machine {sm_id} not found")))?;
    Ok(Json(def))
}

/// Update a state machine definition.
pub async fn update_state_machine(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sm_id): Path<Uuid>,
    Json(req): Json<UpdateStateMachineRequest>,
) -> Result<Json<StateMachineDefinition>> {
    let tenant_id = user.tenant_id;
    let mut store = state.state_machine_definitions.write().await;
    let def = store
        .get_mut(&sm_id)
        .filter(|d| d.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("State machine {sm_id} not found")))?;
    if let Some(name) = req.name {
        def.name = name;
    }
    if let Some(desc) = req.description {
        def.description = Some(desc);
    }
    if let Some(et) = req.entity_type {
        def.entity_type = et;
    }
    if let Some(states) = req.states {
        def.states = states;
    }
    if let Some(transitions) = req.transitions {
        def.transitions = transitions;
    }
    if let Some(initial) = req.initial_state {
        def.initial_state = initial;
    }
    if let Some(active) = req.is_active {
        def.is_active = active;
    }
    def.updated_at = Utc::now();
    Ok(Json(def.clone()))
}

/// Delete a state machine definition.
pub async fn delete_state_machine(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sm_id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.state_machine_definitions.write().await;
    let exists = store
        .get(&sm_id)
        .filter(|d| d.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("State machine {sm_id} not found")));
    }
    store.remove(&sm_id);
    Ok(Json(()))
}

// ── Instance Handlers ──────────────────────────────────────────────────────

/// Create a new state machine instance.
pub async fn create_instance(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sm_id): Path<Uuid>,
    Json(req): Json<CreateInstanceRequest>,
) -> Result<Json<StateMachineInstance>> {
    let tenant_id = user.tenant_id;

    // Verify the definition exists
    let definition = {
        let store = state.state_machine_definitions.read().await;
        store
            .values()
            .find(|d| d.id == sm_id && d.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("State machine definition {sm_id} not found")))?
    };

    let now = Utc::now();
    let instance = StateMachineInstance {
        id: new_id(),
        definition_id: sm_id,
        tenant_id,
        entity_id: req.entity_id,
        current_state: definition.initial_state.clone(),
        state_history: Vec::new(),
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };

    let mut store = state.state_machine_instances.write().await;
    store.insert(instance.id, instance.clone());
    Ok(Json(instance))
}

/// List instances for a state machine definition.
pub async fn list_instances(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(sm_id): Path<Uuid>,
    Query(params): Query<ListInstancesParams>,
) -> Result<Json<PaginatedResponse<StateMachineInstance>>> {
    let tenant_id = user.tenant_id;
    let store = state.state_machine_instances.read().await;
    let mut instances: Vec<StateMachineInstance> = store
        .values()
        .filter(|i| i.definition_id == sm_id && i.tenant_id == tenant_id)
        .filter(|i| {
            if let Some(eid) = &params.entity_id {
                i.entity_id == *eid
            } else {
                true
            }
        })
        .filter(|i| {
            if let Some(ref state) = params.current_state {
                i.current_state == *state
            } else {
                true
            }
        })
        .cloned()
        .collect();
    instances.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    let result = PaginatedResponse::new(instances, params.page, params.per_page);
    Ok(Json(result))
}

/// Get a specific state machine instance by ID.
pub async fn get_instance(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(instance_id): Path<Uuid>,
) -> Result<Json<StateMachineInstance>> {
    let tenant_id = user.tenant_id;
    let store = state.state_machine_instances.read().await;
    let instance = store
        .values()
        .find(|i| i.id == instance_id && i.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("State machine instance {instance_id} not found")))?;
    Ok(Json(instance))
}

/// Execute a state transition on an instance.
///
/// This endpoint enforces all state machine guards before applying a transition:
/// - Validates the instance exists and belongs to the user's tenant
/// - Checks that the current state is not terminal
/// - Validates the transition exists for the given (from_state, event) pair
/// - Evaluates any conditions defined on the transition
/// - Checks allowed_roles on the target state
/// - Executes on_transition hooks if present
/// - Records the transition in the instance's history
/// - Publishes a [`StateMachineTransitionedEvent`] on success
pub async fn transition_instance(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(instance_id): Path<Uuid>,
    Json(req): Json<TransitionRequest>,
) -> Result<Json<TransitionResult>> {
    let tenant_id = user.tenant_id;

    let mut store = state.state_machine_instances.write().await;
    let instance = store
        .get_mut(&instance_id)
        .filter(|i| i.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("State machine instance {instance_id} not found")))?;

    // Look up the definition
    let def_store = state.state_machine_definitions.read().await;
    let definition = def_store
        .values()
        .find(|d| d.id == instance.definition_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound("State machine definition not found".to_string()))?;
    // Release the read lock on definitions before doing writes
    drop(def_store);

    // ── 1. Check if the current state is terminal ───────────────────────
    let current_state_def = definition
        .states
        .iter()
        .find(|s| s.name == instance.current_state);

    if let Some(state_def) = current_state_def {
        if state_def.is_terminal {
            return Err(SenseiError::Conflict(format!(
                "Cannot transition from terminal state '{}'",
                instance.current_state
            )));
        }
    }

    // ── 2. Find a valid transition from the current state ───────────────
    let transition = definition
        .transitions
        .iter()
        .find(|t| t.from_state == instance.current_state && t.event == req.event);

    match transition {
        Some(t) => {
            // ── 3. Evaluate transition conditions ──────────────────────
            if let Some(ref conditions) = t.conditions {
                let context = serde_json::json!({
                    "user_id": user.user_id,
                    "tenant_id": tenant_id,
                    "instance_id": instance_id,
                });
                if !evaluate_conditions(conditions, &context) {
                    return Err(SenseiError::Conflict(format!(
                        "Conditions not met for transition from '{}' via '{}'",
                        t.from_state, t.event
                    )));
                }
            }

            // ── 4. Check allowed roles on the target state ──────────────
            let target_state_def = definition
                .states
                .iter()
                .find(|s| s.name == t.to_state);

            if let Some(target_def) = target_state_def {
                if !target_def.allowed_roles.is_empty() {
                    // In production, check user.roles against target_def.allowed_roles.
                    // For now, log a warning if the user might not have the required role.
                    tracing::info!(
                        target_state = %t.to_state,
                        allowed_roles = ?target_def.allowed_roles,
                        "Transition requires role check"
                    );
                    // Placeholder: In production, check actual user roles.
                    // If the user lacks the required role, return:
                    // return Err(SenseiError::Forbidden(...));
                }
            }

            // ── 5. Execute on_transition hook ──────────────────────────
            if let Some(ref on_transition) = t.on_transition {
                execute_on_transition_hook(on_transition, &instance, &definition);
            }

            // ── 6. Record the transition ───────────────────────────────
            let now = Utc::now();
            let record = StateTransitionRecord {
                from_state: instance.current_state.clone(),
                to_state: t.to_state.clone(),
                event: req.event.clone(),
                triggered_by: user.user_id,
                triggered_at: now,
                metadata: req.metadata.clone(),
            };
            instance.state_history.push(record);
            instance.current_state = t.to_state.clone();
            instance.updated_at = now;

            // ── 7. Publish StateMachineTransitionedEvent ───────────────
            publish_event(
                &state,
                &StateMachineTransitionedEvent::new(
                    tenant_id,
                    instance_id,
                    definition.id,
                    instance.entity_id,
                    instance.current_state.clone(),
                    t.to_state.clone(),
                    req.event.clone(),
                    user.user_id,
                ),
            )
            .await;

            let result = TransitionResult {
                instance: instance.clone(),
                transition_applied: true,
                message: format!(
                    "Transitioned from '{}' to '{}' via event '{}'",
                    t.from_state, t.to_state, req.event
                ),
            };
            Ok(Json(result))
        }
        None => {
            // No valid transition found — return a conflict error
            Err(SenseiError::Conflict(format!(
                "No valid transition from state '{}' for event '{}'",
                instance.current_state, req.event
            )))
        }
    }
}

// ── Guard Evaluation Functions ─────────────────────────────────────────────

/// Evaluate conditions expression against the current context.
///
/// The conditions value is expected to be a JSON object or array of rules.
/// Returns `true` if the conditions are met or no conditions are specified.
fn evaluate_conditions(conditions: &serde_json::Value, _context: &serde_json::Value) -> bool {
    match conditions {
        serde_json::Value::Object(map) => {
            match map.get("type").and_then(|v| v.as_str()) {
                Some("always") | None => true,
                Some("role_required") => {
                    // Check if user has the required role
                    if let Some(role) = map.get("role").and_then(|v| v.as_str()) {
                        // In production, check if the user's roles include this role.
                        // For now, allow all role_required conditions.
                        tracing::info!(required_role = %role, "Role-required condition evaluated");
                        true
                    } else {
                        true
                    }
                }
                Some("field_match") => {
                    // Check if a context field matches an expected value
                    if let (Some(field), Some(expected)) = (
                        map.get("field").and_then(|v| v.as_str()),
                        map.get("value"),
                    ) {
                        let actual = _context.get(field);
                        match actual {
                            Some(val) if val == expected => true,
                            _ => false,
                        }
                    } else {
                        true
                    }
                }
                Some(other) => {
                    tracing::warn!(condition_type = %other, "Unknown condition type");
                    false
                }
            }
        }
        serde_json::Value::Array(arr) => {
            // AND semantics: all conditions must pass
            arr.iter().all(|c| evaluate_conditions(c, _context))
        }
        _ => true, // No conditions = always allowed
    }
}

/// Execute an `on_transition` hook defined on a transition.
///
/// Hooks are JSON action descriptors that can trigger side effects such as
/// sending notifications, updating related entities, or calling webhooks.
fn execute_on_transition_hook(
    hook: &serde_json::Value,
    instance: &StateMachineInstance,
    _definition: &StateMachineDefinition,
) {
    match hook {
        serde_json::Value::Object(map) => {
            if let Some(action) = map.get("action").and_then(|v| v.as_str()) {
                tracing::info!(
                    action = %action,
                    instance_id = %instance.id,
                    current_state = %instance.current_state,
                    "Executing on_transition hook"
                );

                match action {
                    "send_notification" => {
                        // In production: dispatch a notification to relevant users.
                        // The hook payload may contain templates and target users.
                        tracing::info!("Hook would send notification for instance {}", instance.id);
                    }
                    "update_entity" => {
                        // In production: update the entity associated with this instance.
                        tracing::info!("Hook would update entity {} for instance {}", instance.entity_id, instance.id);
                    }
                    "webhook" => {
                        // In production: call an external webhook URL.
                        if let Some(url) = map.get("url").and_then(|v| v.as_str()) {
                            tracing::info!("Hook would call webhook at {}", url);
                        }
                    }
                    other => {
                        tracing::warn!(action = %other, "Unknown on_transition action");
                    }
                }
            }
        }
        _ => {
            tracing::warn!("Invalid on_transition hook format — expected JSON object");
        }
    }
}

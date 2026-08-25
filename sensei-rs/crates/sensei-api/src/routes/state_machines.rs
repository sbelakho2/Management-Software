//! State Machine route handlers.
//!
//! Provides endpoints for managing state machine definitions and
//! running instances, including state transitions.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{DomainEvent, StateMachineTransitionedEvent};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{
    StateDefinition, StateMachineDefinition, StateMachineInstance, StateTransitionRecord,
    TransitionDefinition,
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

// ── Definition validation ───────────────────────────────────────────────────

/// Validate a state machine definition before it is stored.
///
/// Rules:
/// - `initial_state` must reference an existing state;
/// - state names must be unique;
/// - every transition must reference defined `from_state`/`to_state` states;
/// - self-loop transitions are rejected unless explicitly allowed;
/// - unknown condition types and hook actions are rejected at definition time.
fn validate_definition(def: &StateMachineDefinition) -> Result<()> {
    let state_names: std::collections::HashSet<&str> =
        def.states.iter().map(|s| s.name.as_str()).collect();

    if !state_names.contains(def.initial_state.as_str()) {
        return Err(SenseiError::Validation(format!(
            "initial_state '{}' does not exist in states: {}",
            def.initial_state,
            state_names.iter().copied().collect::<Vec<_>>().join(", ")
        )));
    }
    if state_names.len() != def.states.len() {
        return Err(SenseiError::Validation(
            "Duplicate state names in states definition".to_string(),
        ));
    }

    for t in &def.transitions {
        if !state_names.contains(t.from_state.as_str()) {
            return Err(SenseiError::Validation(format!(
                "Transition '{}' references undefined from_state '{}'",
                t.event, t.from_state
            )));
        }
        if !state_names.contains(t.to_state.as_str()) {
            return Err(SenseiError::Validation(format!(
                "Transition '{}' references undefined to_state '{}'",
                t.event, t.to_state
            )));
        }
        if t.from_state == t.to_state {
            return Err(SenseiError::Validation(format!(
                "Transition '{}' is a self-loop ({}) which is not allowed",
                t.event, t.from_state
            )));
        }
        if let Some(conditions) = &t.conditions {
            validate_conditions_definition(conditions)?;
        }
        if let Some(hook) = &t.on_transition {
            validate_hook_definition(hook)?;
        }
    }
    Ok(())
}

/// Validate a conditions expression at definition time.
fn validate_conditions_definition(conditions: &serde_json::Value) -> Result<()> {
    match conditions {
        serde_json::Value::Object(map) => match map.get("type").and_then(|v| v.as_str()) {
            Some("always") | Some("role_required") | Some("field_match") | None => Ok(()),
            Some(other) => Err(SenseiError::Validation(format!(
                "Unknown condition type '{other}'. Supported: always, role_required, field_match"
            ))),
        },
        serde_json::Value::Array(arr) => {
            for c in arr {
                validate_conditions_definition(c)?;
            }
            Ok(())
        }
        _ => Err(SenseiError::Validation(
            "Invalid conditions format: expected an object or array of rules".to_string(),
        )),
    }
}

/// Validate an `on_transition` hook at definition time.
fn validate_hook_definition(hook: &serde_json::Value) -> Result<()> {
    match hook {
        serde_json::Value::Object(map) => match map.get("action").and_then(|v| v.as_str()) {
            Some("send_notification") | Some("webhook") | Some("update_entity") => Ok(()),
            Some(other) => Err(SenseiError::Validation(format!(
                "Unknown on_transition action '{other}'. Supported: send_notification, webhook, update_entity"
            ))),
            None => Err(SenseiError::Validation(
                "on_transition hook missing required 'action' field".to_string(),
            )),
        },
        _ => Err(SenseiError::Validation(
            "Invalid on_transition hook format: expected a JSON object".to_string(),
        )),
    }
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
    validate_definition(&def)?;
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
    validate_definition(def)?;
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
        return Err(SenseiError::NotFound(format!(
            "State machine {sm_id} not found"
        )));
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
            .ok_or_else(|| {
                SenseiError::NotFound(format!("State machine definition {sm_id} not found"))
            })?
    };

    // An entity may only have one instance per definition.
    {
        let store = state.state_machine_instances.read().await;
        if store.values().any(|i| {
            i.definition_id == sm_id && i.entity_id == req.entity_id && i.tenant_id == tenant_id
        }) {
            return Err(SenseiError::Conflict(format!(
                "An instance for entity {} already exists in state machine {sm_id}",
                req.entity_id
            )));
        }
    }

    let now = Utc::now();
    let initial_state = definition.initial_state.clone();
    let instance = StateMachineInstance {
        id: new_id(),
        definition_id: sm_id,
        tenant_id,
        entity_id: req.entity_id,
        current_state: initial_state.clone(),
        // Record the initial state in the history so the instance's full
        // lifecycle is traceable.
        state_history: vec![StateTransitionRecord {
            from_state: initial_state.clone(),
            to_state: initial_state,
            event: "initialized".to_string(),
            triggered_by: user.user_id,
            triggered_at: now,
            metadata: None,
        }],
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
    instances.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
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
        .ok_or_else(|| {
            SenseiError::NotFound(format!("State machine instance {instance_id} not found"))
        })?;
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
        .ok_or_else(|| {
            SenseiError::NotFound(format!("State machine instance {instance_id} not found"))
        })?;

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
                if !evaluate_conditions(conditions, &context, &user.roles) {
                    return Err(SenseiError::Conflict(format!(
                        "Conditions not met for transition from '{}' via '{}'",
                        t.from_state, t.event
                    )));
                }
            }

            // ── 4. Check allowed roles on the target state ──────────────
            let target_state_def = definition.states.iter().find(|s| s.name == t.to_state);

            if let Some(target_def) = target_state_def {
                if !target_def.allowed_roles.is_empty()
                    && !user.has_any_role(
                        &target_def
                            .allowed_roles
                            .iter()
                            .map(String::as_str)
                            .collect::<Vec<_>>(),
                    )
                {
                    return Err(SenseiError::Forbidden(format!(
                        "User lacks required role for state '{}'. Required: {:?}",
                        t.to_state, target_def.allowed_roles
                    )));
                }
            }

            // ── 5. Execute on_transition hook ──────────────────────────
            if let Some(ref on_transition) = t.on_transition {
                execute_on_transition_hook(
                    &state,
                    on_transition,
                    instance,
                    &definition,
                    user.user_id,
                )
                .await;
            }

            // ── 6. Record the transition (old state captured before the
            // mutation so history and events always carry the real
            // from_state) ───────────────────────────────────────────────
            let old_state = instance.current_state.clone();
            let now = Utc::now();
            let record = StateTransitionRecord {
                from_state: old_state.clone(),
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
                    old_state,
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
fn evaluate_conditions(
    conditions: &serde_json::Value,
    context: &serde_json::Value,
    user_roles: &[String],
) -> bool {
    match conditions {
        serde_json::Value::Object(map) => {
            match map.get("type").and_then(|v| v.as_str()) {
                Some("always") | None => true,
                Some("role_required") => {
                    // The user must hold the required role.
                    match map.get("role").and_then(|v| v.as_str()) {
                        Some(role) => user_roles.iter().any(|r| r == role),
                        None => true,
                    }
                }
                Some("field_match") => {
                    // Check if a context field matches an expected value
                    if let (Some(field), Some(expected)) =
                        (map.get("field").and_then(|v| v.as_str()), map.get("value"))
                    {
                        let actual = context.get(field);
                        matches!(actual, Some(val) if val == expected)
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
            arr.iter()
                .all(|c| evaluate_conditions(c, context, user_roles))
        }
        _ => true, // No conditions = always allowed
    }
}

/// Execute an `on_transition` hook defined on a transition.
///
/// Hooks are JSON action descriptors that trigger real side effects:
/// - `send_notification` — creates an in-app notification for a target user;
/// - `webhook` — fires an HTTP POST to the configured URL (best-effort);
/// - `update_entity` — applies a status field update on the linked entity.
async fn execute_on_transition_hook(
    state: &AppState,
    hook: &serde_json::Value,
    instance: &StateMachineInstance,
    definition: &StateMachineDefinition,
    triggered_by: Uuid,
) {
    let Some(map) = hook.as_object() else {
        tracing::warn!("Invalid on_transition hook format — expected JSON object");
        return;
    };
    let Some(action) = map.get("action").and_then(|v| v.as_str()) else {
        return;
    };

    match action {
        "send_notification" => {
            let target_user = map
                .get("target_user_id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .unwrap_or(triggered_by);
            let title = map
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("State machine transition")
                .to_string();
            let body = map
                .get("body")
                .and_then(|v| v.as_str())
                .unwrap_or(&format!(
                    "Entity {} transitioned to '{}'",
                    instance.entity_id, instance.current_state
                ))
                .to_string();
            if let Err(e) = state
                .notification_service
                .notify(sensei_services::notifications::NewNotification {
                    tenant_id: instance.tenant_id,
                    user_id: target_user,
                    title,
                    body,
                    notification_type: "info".to_string(),
                    reference_type: Some("state_machine_instance".to_string()),
                    reference_id: Some(instance.id),
                })
                .await
            {
                tracing::warn!(
                    error = %e,
                    instance_id = %instance.id,
                    "send_notification hook failed"
                );
            }
        }
        "webhook" => {
            if let Some(url) = map.get("url").and_then(|v| v.as_str()) {
                let payload = map.get("payload").cloned().unwrap_or_else(|| {
                    serde_json::json!({
                        "instance_id": instance.id,
                        "entity_id": instance.entity_id,
                        "definition_id": definition.id,
                        "state": instance.current_state,
                        "event": map.get("event"),
                    })
                });
                let result = reqwest::Client::new()
                    .post(url)
                    .json(&payload)
                    .timeout(std::time::Duration::from_secs(5))
                    .send()
                    .await;
                if let Err(e) = result {
                    tracing::warn!(
                        error = %e,
                        url = %url,
                        instance_id = %instance.id,
                        "webhook hook failed"
                    );
                }
            }
        }
        "update_entity" => {
            update_linked_entity(state, instance, definition, map, triggered_by).await;
        }
        other => {
            tracing::warn!(action = %other, "Unknown on_transition action");
        }
    }
}

/// Apply a simple status update on the entity linked to an instance.
///
/// Supported entity types map to their entity stores; the hook payload can
/// override the target field (default `"status"`) and value (default: the
/// instance's current state). Unknown entity types are logged and skipped —
/// the transition itself is not rolled back.
async fn update_linked_entity(
    state: &AppState,
    instance: &StateMachineInstance,
    definition: &StateMachineDefinition,
    hook: &serde_json::Map<String, serde_json::Value>,
    _triggered_by: Uuid,
) {
    let field = hook
        .get("field")
        .and_then(|v| v.as_str())
        .unwrap_or("status")
        .to_string();
    let value = hook
        .get("value")
        .cloned()
        .unwrap_or_else(|| serde_json::Value::String(instance.current_state.clone()));
    let entity_id = instance.entity_id;
    let tenant_id = instance.tenant_id;

    match definition.entity_type.as_str() {
        "task" => {
            let mut store = state.tasks.write().await;
            if let Some(t) = store.get_mut(&entity_id) {
                if t.tenant_id == tenant_id && field == "status" {
                    if let Some(s) = value.as_str() {
                        if let Some(status) = parse_task_status(s) {
                            t.status = status;
                            t.updated_at = chrono::Utc::now();
                        }
                    }
                }
            }
        }
        "obeya_board" => {
            let mut store = state.obeya_boards.write().await;
            if let Some(b) = store.get_mut(&entity_id) {
                if b.tenant_id == tenant_id && field == "status" {
                    if let Some(s) = value.as_str() {
                        b.is_active = s != "Archived" && s != "Closed";
                        b.updated_at = chrono::Utc::now();
                    }
                }
            }
        }
        "work_center" => {
            let mut store = state.work_centers.write().await;
            if let Some(wc) = store.get_mut(&entity_id) {
                if wc.tenant_id == tenant_id && field == "status" {
                    if let Some(s) = value.as_str() {
                        wc.is_active = s != "Inactive" && s != "Decommissioned";
                        wc.updated_at = chrono::Utc::now();
                    }
                }
            }
        }
        "production_cell" => {
            let mut store = state.production_cells.write().await;
            if let Some(c) = store.get_mut(&entity_id) {
                if c.tenant_id == tenant_id && field == "status" {
                    if let Some(s) = value.as_str() {
                        c.is_active = s != "Inactive" && s != "Decommissioned";
                        c.updated_at = chrono::Utc::now();
                    }
                }
            }
        }
        other => {
            tracing::warn!(
                entity_type = %other,
                instance_id = %instance.id,
                "update_entity hook: no store registered for entity type"
            );
        }
    }
}

/// Parse a task status string into the typed [`TaskStatus`] value.
fn parse_task_status(s: &str) -> Option<crate::stores::TaskStatus> {
    match s {
        "open" | "Open" => Some(crate::stores::TaskStatus::Open),
        "in_progress" | "InProgress" | "In Progress" => Some(crate::stores::TaskStatus::InProgress),
        "in_review" | "InReview" => Some(crate::stores::TaskStatus::InReview),
        "completed" | "Completed" => Some(crate::stores::TaskStatus::Completed),
        "cancelled" | "Cancelled" => Some(crate::stores::TaskStatus::Cancelled),
        "blocked" | "Blocked" => Some(crate::stores::TaskStatus::Blocked),
        _ => None,
    }
}

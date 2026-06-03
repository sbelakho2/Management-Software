//! State Machine route handlers.
//!
//! Provides endpoints for managing state machine definitions and
//! running instances, including state transitions.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{
    StateDefinition, StateMachineDefinition, StateMachineInstance,
    StateTransitionRecord, TransitionDefinition,
};

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

    // Find a valid transition from the current state
    let def_store = state.state_machine_definitions.read().await;
    let definition = def_store
        .values()
        .find(|d| d.id == instance.definition_id)
        .ok_or_else(|| SenseiError::NotFound("State machine definition not found".to_string()))?;

    let transition = definition
        .transitions
        .iter()
        .find(|t| t.from_state == instance.current_state && t.event == req.event);

    match transition {
        Some(t) => {
            let now = Utc::now();
            let record = StateTransitionRecord {
                from_state: instance.current_state.clone(),
                to_state: t.to_state.clone(),
                event: req.event.clone(),
                triggered_by: user.user_id,
                triggered_at: now,
                metadata: req.metadata,
            };
            instance.state_history.push(record);
            instance.current_state = t.to_state.clone();
            instance.updated_at = now;

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
            let result = TransitionResult {
                instance: instance.clone(),
                transition_applied: false,
                message: format!(
                    "No valid transition from state '{}' for event '{}'",
                    instance.current_state, req.event
                ),
            };
            Ok(Json(result))
        }
    }
}

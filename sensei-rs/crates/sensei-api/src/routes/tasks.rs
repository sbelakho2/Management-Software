//! Task route handlers.
//!
//! Provides endpoints for managing tasks, including CRUD, status transitions,
//! assignment, and statistics.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{
    DomainEvent, TaskAssignedEvent, TaskCreatedEvent, TaskStatusChangedEvent, TaskUpdatedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{Task, TaskPriority, TaskStatus};

// ── Internal helpers ───────────────────────────────────────────────────────

/// Publish a domain event via the event bus, logging warnings on failure.
async fn publish_event(state: &AppState, event: &dyn DomainEvent) {
    if let Err(e) = state.event_bus.publish(event).await {
        tracing::warn!(error = %e, event_type = %event.event_type(), "Failed to publish domain event");
    }
}

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing tasks.
#[derive(Debug, Deserialize)]
pub struct ListTasksParams {
    pub status: Option<String>,
    pub assignee_id: Option<Uuid>,
    pub priority: Option<String>,
    pub category: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating a task.
#[derive(Debug, Deserialize)]
pub struct CreateTaskRequest {
    pub title: String,
    pub description: String,
    pub priority: String,
    pub category: String,
    pub tags: Vec<String>,
    pub assignee_id: Option<Uuid>,
    pub due_date: Option<String>,
    pub estimated_hours: Option<f64>,
}

/// Request body for updating a task.
#[derive(Debug, Deserialize)]
pub struct UpdateTaskRequest {
    pub title: Option<String>,
    pub description: Option<String>,
    pub priority: Option<String>,
    pub category: Option<String>,
    pub tags: Option<Vec<String>>,
    pub assignee_id: Option<Option<Uuid>>,
    pub due_date: Option<Option<String>>,
    pub estimated_hours: Option<Option<f64>>,
    pub actual_hours: Option<Option<f64>>,
}

/// Request body for updating task status.
#[derive(Debug, Deserialize)]
pub struct UpdateStatusRequest {
    pub status: String,
}

/// Request body for assigning a task.
#[derive(Debug, Deserialize)]
pub struct AssignTaskRequest {
    pub assignee_id: Uuid,
}

/// Task statistics response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStats {
    pub total: usize,
    pub by_status: Vec<StatusCount>,
    pub by_priority: Vec<PriorityCount>,
    pub overdue: usize,
    pub unassigned: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusCount {
    pub status: String,
    pub count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriorityCount {
    pub priority: String,
    pub count: usize,
}

// ── Helper: Parse a priority string into a TaskPriority ────────────────────

fn parse_priority(s: &str) -> std::result::Result<TaskPriority, SenseiError> {
    match s {
        "low" => Ok(TaskPriority::Low),
        "medium" => Ok(TaskPriority::Medium),
        "high" => Ok(TaskPriority::High),
        "critical" => Ok(TaskPriority::Critical),
        other => Err(SenseiError::InvalidValue {
            field: "priority".to_string(),
            detail: format!(
                "Unknown priority '{other}'. Valid values: low, medium, high, critical"
            ),
        }),
    }
}

fn parse_status(s: &str) -> std::result::Result<TaskStatus, SenseiError> {
    match s {
        "open" => Ok(TaskStatus::Open),
        "in_progress" => Ok(TaskStatus::InProgress),
        "in_review" => Ok(TaskStatus::InReview),
        "completed" => Ok(TaskStatus::Completed),
        "cancelled" => Ok(TaskStatus::Cancelled),
        "blocked" => Ok(TaskStatus::Blocked),
        other => Err(SenseiError::InvalidValue {
            field: "status".to_string(),
            detail: format!("Unknown status '{other}'. Valid values: open, in_progress, in_review, completed, cancelled, blocked"),
        }),
    }
}

// ── Tasks ─────────────────────────────────────────────────────────────────

/// List tasks with optional filters.
pub async fn list_tasks(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTasksParams>,
) -> Result<Json<PaginatedResponse<Task>>> {
    let tenant_id = user.tenant_id;
    let store = state.tasks.read(user.tenant_id).await;
    let mut tasks: Vec<Task> = store
        .values()
        .filter(|t| t.tenant_id == tenant_id)
        .filter(|t| {
            if let Some(ref status) = params.status {
                t.status.to_string() == *status
            } else {
                true
            }
        })
        .filter(|t| {
            if let Some(aid) = &params.assignee_id {
                t.assignee_id.as_ref() == Some(aid)
            } else {
                true
            }
        })
        .filter(|t| {
            if let Some(ref priority) = params.priority {
                t.priority.to_string() == *priority
            } else {
                true
            }
        })
        .filter(|t| {
            if let Some(ref cat) = params.category {
                t.category == *cat
            } else {
                true
            }
        })
        .cloned()
        .collect();
    tasks.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
    let result = PaginatedResponse::new(tasks, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new task.
pub async fn create_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateTaskRequest>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let due_date = req
        .due_date
        .as_deref()
        .map(|d| {
            DateTime::parse_from_rfc3339(d)
                .map_err(|e| SenseiError::Validation(format!("Invalid due_date: {e}")))
                .map(|dt| dt.with_timezone(&Utc))
        })
        .transpose()?;

    let priority = parse_priority(&req.priority)?;

    let task = Task {
        id: new_id(),
        tenant_id,
        title: req.title,
        description: req.description,
        status: TaskStatus::Open,
        priority,
        assignee_id: req.assignee_id,
        due_date,
        category: req.category,
        tags: req.tags,
        estimated_hours: req.estimated_hours,
        actual_hours: None,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
        state_machine_instance_id: None,
    };
    let mut store = state.tasks.write(user.tenant_id).await;
    store.insert(task.id, task.clone());

    // Publish TaskCreatedEvent
    publish_event(
        &state,
        &TaskCreatedEvent::new(
            tenant_id,
            task.id,
            task.title.clone(),
            task.status.to_string(),
            task.priority.to_string(),
            user.user_id,
        ),
    )
    .await;

    Ok(Json(task))
}

/// Get a task by ID.
pub async fn get_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let store = state.tasks.read(user.tenant_id).await;
    let task = store
        .values()
        .find(|t| t.id == id && t.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;
    Ok(Json(task))
}

/// Update a task.
pub async fn update_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateTaskRequest>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write(user.tenant_id).await;
    let task = store
        .get_mut(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;

    let old_priority = task.priority.to_string();
    let mut changed = false;

    if let Some(title) = req.title {
        task.title = title;
        changed = true;
    }
    if let Some(desc) = req.description {
        task.description = desc;
        changed = true;
    }
    if let Some(priority) = req.priority {
        let parsed = parse_priority(&priority)?;
        if task.priority != parsed {
            task.priority = parsed;
            changed = true;
        }
    }
    if let Some(cat) = req.category {
        task.category = cat;
        changed = true;
    }
    if let Some(tags) = req.tags {
        task.tags = tags;
        changed = true;
    }
    if let Some(aid) = req.assignee_id {
        task.assignee_id = aid;
        changed = true;
    }
    if let Some(due) = req.due_date {
        task.due_date = due
            .map(|d| {
                DateTime::parse_from_rfc3339(&d)
                    .map_err(|e| SenseiError::Validation(format!("Invalid due_date: {e}")))
                    .map(|dt| dt.with_timezone(&Utc))
            })
            .transpose()?;
        changed = true;
    }
    if let Some(eh) = req.estimated_hours {
        task.estimated_hours = eh;
        changed = true;
    }
    if let Some(ah) = req.actual_hours {
        task.actual_hours = ah;
        changed = true;
    }
    task.updated_at = Utc::now();
    let updated = task.clone();

    // Publish TaskUpdatedEvent on ANY field update, not just priority.
    if changed {
        let new_priority = updated.priority.to_string();
        let old_priority = if old_priority != new_priority {
            Some(old_priority)
        } else {
            None
        };
        publish_event(
            &state,
            &TaskUpdatedEvent::new(
                tenant_id,
                id,
                old_priority,
                Some(new_priority),
                user.user_id,
            ),
        )
        .await;
    }

    Ok(Json(updated))
}

/// Delete a task.
pub async fn delete_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write(user.tenant_id).await;
    let exists = store
        .get(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("Task {id} not found")));
    }
    store.remove(&id);
    Ok(Json(()))
}

/// Update task status.
///
/// If the task has a `state_machine_instance_id`, the status change is validated
/// against the associated state machine before being applied.
pub async fn update_task_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateStatusRequest>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write(user.tenant_id).await;
    let task = store
        .get_mut(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;

    let new_status = parse_status(&req.status)?;
    let old_status = task.status.to_string();

    // If the task is linked to a state machine instance, validate via SM
    if let Some(sm_instance_id) = task.state_machine_instance_id {
        let mut sm_store = state.state_machine_instances.write(user.tenant_id).await;
        let instance = sm_store
            .get_mut(&sm_instance_id)
            .filter(|i| i.tenant_id == tenant_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("State machine instance {sm_instance_id} not found"))
            })?;

        // Look up the definition to find a matching transition
        let def_store = state.state_machine_definitions.read(user.tenant_id).await;
        let definition = def_store
            .values()
            .find(|d| d.id == instance.definition_id)
            .ok_or_else(|| {
                SenseiError::NotFound("State machine definition not found".to_string())
            })?;

        // Map the new task status to the state machine event name
        let event_name = format!("to_{}", new_status);
        let transition = definition
            .transitions
            .iter()
            .find(|t| t.from_state == instance.current_state && t.event == event_name);

        match transition {
            Some(t) => {
                // Check if current state is terminal
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

                // Evaluate conditions if present (real role checks included)
                if let Some(ref conditions) = t.conditions {
                    let context = serde_json::json!({
                        "user_id": user.user_id,
                        "tenant_id": tenant_id,
                        "task_id": id,
                    });
                    if !evaluate_conditions(conditions, &context, &user.roles) {
                        return Err(SenseiError::Conflict(format!(
                            "Conditions not met for transitioning to '{}'",
                            t.to_state
                        )));
                    }
                }

                // Check allowed roles against the user's REAL roles.
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

                // Execute on_transition hooks if present
                if let Some(ref on_transition) = t.on_transition {
                    execute_on_transition_hook(&state, on_transition, task).await;
                }

                // Record the transition — capture the OLD state before the
                // instance is mutated so the history and the published event
                // both carry the real from_state.
                let old_sm_state = instance.current_state.clone();
                let now = Utc::now();
                let record = crate::stores::StateTransitionRecord {
                    from_state: old_sm_state.clone(),
                    to_state: t.to_state.clone(),
                    event: event_name.clone(),
                    triggered_by: user.user_id,
                    triggered_at: now,
                    metadata: Some(serde_json::json!({
                        "task_id": id,
                        "old_status": old_status,
                        "new_status": new_status.to_string(),
                    })),
                };
                instance.state_history.push(record);
                instance.current_state = t.to_state.clone();
                instance.updated_at = now;

                // Publish StateMachineTransitionedEvent
                publish_event(
                    &state,
                    &sensei_core::domain::events::StateMachineTransitionedEvent::new(
                        tenant_id,
                        sm_instance_id,
                        definition.id,
                        instance.entity_id,
                        old_sm_state,
                        t.to_state.clone(),
                        event_name,
                        user.user_id,
                    ),
                )
                .await;
            }
            None => {
                return Err(SenseiError::Conflict(format!(
                    "No valid transition from SM state '{}' for event '{event_name}'",
                    instance.current_state,
                )));
            }
        }
    }

    // Apply the status change
    task.status = new_status;
    task.updated_at = Utc::now();
    let updated = task.clone();

    // Always publish TaskStatusChangedEvent
    publish_event(
        &state,
        &TaskStatusChangedEvent::new(
            tenant_id,
            id,
            old_status,
            updated.status.to_string(),
            user.user_id,
        ),
    )
    .await;

    Ok(Json(updated))
}

/// Assign task to a user.
pub async fn assign_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<AssignTaskRequest>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write(user.tenant_id).await;
    let task = store
        .get_mut(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;

    task.assignee_id = Some(req.assignee_id);
    task.updated_at = Utc::now();
    let updated = task.clone();

    // Publish TaskAssignedEvent
    publish_event(
        &state,
        &TaskAssignedEvent::new(tenant_id, id, req.assignee_id, user.user_id),
    )
    .await;

    Ok(Json(updated))
}

/// Get task statistics.
pub async fn get_task_stats(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<TaskStats>> {
    let tenant_id = user.tenant_id;
    let store = state.tasks.read(user.tenant_id).await;
    let tasks: Vec<&Task> = store
        .values()
        .filter(|t| t.tenant_id == tenant_id)
        .collect();

    let total = tasks.len();
    let now = Utc::now();

    // Count by status
    let mut status_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut priority_map: std::collections::HashMap<String, usize> =
        std::collections::HashMap::new();
    let mut overdue = 0usize;
    let mut unassigned = 0usize;

    for task in &tasks {
        *status_map.entry(task.status.to_string()).or_insert(0) += 1;
        *priority_map.entry(task.priority.to_string()).or_insert(0) += 1;
        if task.status != TaskStatus::Completed && task.status != TaskStatus::Cancelled {
            if let Some(due) = task.due_date {
                if due < now {
                    overdue += 1;
                }
            }
        }
        if task.assignee_id.is_none() {
            unassigned += 1;
        }
    }

    let by_status: Vec<StatusCount> = status_map
        .into_iter()
        .map(|(status, count)| StatusCount { status, count })
        .collect();
    let by_priority: Vec<PriorityCount> = priority_map
        .into_iter()
        .map(|(priority, count)| PriorityCount { priority, count })
        .collect();

    let stats = TaskStats {
        total,
        by_status,
        by_priority,
        overdue,
        unassigned,
    };
    Ok(Json(stats))
}

// ── State Machine Helper Functions ─────────────────────────────────────────

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
                    tracing::warn!("Unknown condition type: {other}");
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

/// Execute an `on_transition` hook.
///
/// Hooks can be arbitrary JSON actions such as sending notifications,
/// updating related entities, or calling external services.
async fn execute_on_transition_hook(state: &AppState, hook: &serde_json::Value, task: &Task) {
    let Some(map) = hook.as_object() else {
        tracing::warn!("Invalid on_transition hook format");
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
                .unwrap_or(task.assignee_id.unwrap_or(task.created_by));
            let title = map
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("Task status changed")
                .to_string();
            let body = map
                .get("body")
                .and_then(|v| v.as_str())
                .unwrap_or(&format!("Task '{}' is now {}", task.title, task.status))
                .to_string();
            if let Err(e) = state
                .notification_service
                .notify(sensei_services::notifications::NewNotification {
                    tenant_id: task.tenant_id,
                    user_id: target_user,
                    title,
                    body,
                    notification_type: "info".to_string(),
                    reference_type: Some("task".to_string()),
                    reference_id: Some(task.id),
                })
                .await
            {
                tracing::warn!(
                    error = %e,
                    task_id = %task.id,
                    "send_notification hook failed"
                );
            }
        }
        "webhook" => {
            if let Some(url) = map.get("url").and_then(|v| v.as_str()) {
                let payload = map.get("payload").cloned().unwrap_or_else(|| {
                    serde_json::json!({
                        "task_id": task.id,
                        "title": task.title,
                        "status": task.status.to_string(),
                        "priority": task.priority.to_string(),
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
                        url = %crate::state::redact_nats_url(url),
                        task_id = %task.id,
                        "webhook hook failed"
                    );
                }
            }
        }
        other => {
            tracing::warn!(action = %other, "Unknown on_transition action");
        }
    }
}

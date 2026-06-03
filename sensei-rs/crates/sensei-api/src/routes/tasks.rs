//! Task route handlers.
//!
//! Provides endpoints for managing tasks, including CRUD, status transitions,
//! assignment, and statistics.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::Task;

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

// ── Tasks ─────────────────────────────────────────────────────────────────

/// List tasks with optional filters.
pub async fn list_tasks(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTasksParams>,
) -> Result<Json<PaginatedResponse<Task>>> {
    let tenant_id = user.tenant_id;
    let store = state.tasks.read().await;
    let mut tasks: Vec<Task> = store
        .values()
        .filter(|t| t.tenant_id == tenant_id)
        .filter(|t| {
            if let Some(ref status) = params.status {
                t.status == *status
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
                t.priority == *priority
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
    tasks.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
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
    let due_date = req.due_date
        .as_deref()
        .map(|d| DateTime::parse_from_rfc3339(d)
            .map_err(|e| SenseiError::Validation(format!("Invalid due_date: {e}")))
            .map(|dt| dt.with_timezone(&Utc)))
        .transpose()?;

    let task = Task {
        id: new_id(),
        tenant_id,
        title: req.title,
        description: req.description,
        status: "open".to_string(),
        priority: req.priority,
        assignee_id: req.assignee_id,
        due_date,
        category: req.category,
        tags: req.tags,
        estimated_hours: req.estimated_hours,
        actual_hours: None,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.tasks.write().await;
    store.insert(task.id, task.clone());
    Ok(Json(task))
}

/// Get a task by ID.
pub async fn get_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let store = state.tasks.read().await;
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
    let mut store = state.tasks.write().await;
    let task = store
        .get_mut(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;

    if let Some(title) = req.title {
        task.title = title;
    }
    if let Some(desc) = req.description {
        task.description = desc;
    }
    if let Some(priority) = req.priority {
        task.priority = priority;
    }
    if let Some(cat) = req.category {
        task.category = cat;
    }
    if let Some(tags) = req.tags {
        task.tags = tags;
    }
    if let Some(aid) = req.assignee_id {
        task.assignee_id = aid;
    }
    if let Some(due) = req.due_date {
        task.due_date = due
            .map(|d| DateTime::parse_from_rfc3339(&d)
                .map_err(|e| SenseiError::Validation(format!("Invalid due_date: {e}")))
                .map(|dt| dt.with_timezone(&Utc)))
            .transpose()?;
    }
    if let Some(eh) = req.estimated_hours {
        task.estimated_hours = eh;
    }
    if let Some(ah) = req.actual_hours {
        task.actual_hours = ah;
    }
    task.updated_at = Utc::now();
    Ok(Json(task.clone()))
}

/// Delete a task.
pub async fn delete_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write().await;
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
pub async fn update_task_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateStatusRequest>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write().await;
    let task = store
        .get_mut(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;

    task.status = req.status;
    task.updated_at = Utc::now();
    Ok(Json(task.clone()))
}

/// Assign task to a user.
pub async fn assign_task(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<AssignTaskRequest>,
) -> Result<Json<Task>> {
    let tenant_id = user.tenant_id;
    let mut store = state.tasks.write().await;
    let task = store
        .get_mut(&id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Task {id} not found")))?;

    task.assignee_id = Some(req.assignee_id);
    task.updated_at = Utc::now();
    Ok(Json(task.clone()))
}

/// Get task statistics.
pub async fn get_task_stats(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<TaskStats>> {
    let tenant_id = user.tenant_id;
    let store = state.tasks.read().await;
    let tasks: Vec<&Task> = store
        .values()
        .filter(|t| t.tenant_id == tenant_id)
        .collect();

    let total = tasks.len();
    let now = Utc::now();

    // Count by status
    let mut status_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut priority_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut overdue = 0usize;
    let mut unassigned = 0usize;

    for task in &tasks {
        *status_map.entry(task.status.clone()).or_insert(0) += 1;
        *priority_map.entry(task.priority.clone()).or_insert(0) += 1;
        if task.status != "completed" && task.status != "cancelled" {
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

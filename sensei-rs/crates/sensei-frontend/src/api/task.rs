//! Task management and Kanban board API endpoints.
//!
//! Tasks, subtasks, checklists, Kanban boards and columns.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// DTOs — Tasks
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskListParams {
    pub status: Option<serde_json::Value>,  // String or Vec<String>
    pub priority: Option<serde_json::Value>, // String or Vec<String>
    pub task_type: Option<serde_json::Value>, // String or Vec<String>
    pub assigned_to: Option<String>,
    pub created_by: Option<String>,
    pub due_date_from: Option<String>,
    pub due_date_to: Option<String>,
    pub search: Option<String>,
    pub tags: Option<Vec<String>>,
    pub linked_entity_type: Option<String>,
    pub linked_entity_id: Option<String>,
    pub parent_task_id: Option<String>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateTaskData {
    pub title: String,
    pub description: Option<String>,
    pub status: Option<String>,
    pub priority: Option<String>,
    pub task_type: Option<String>,
    pub assigned_to: Option<String>,
    pub due_date: Option<String>,
    pub estimated_hours: Option<f64>,
    pub parent_task_id: Option<String>,
    pub linked_entity_type: Option<String>,
    pub linked_entity_id: Option<String>,
    pub tags: Option<Vec<String>>,
    pub checklist: Option<Vec<ChecklistItemInput>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChecklistItemInput {
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateTaskData {
    pub title: Option<String>,
    pub description: Option<String>,
    pub status: Option<String>,
    pub priority: Option<String>,
    pub task_type: Option<String>,
    pub assigned_to: Option<serde_json::Value>, // String or null
    pub due_date: Option<serde_json::Value>,    // String or null
    pub estimated_hours: Option<serde_json::Value>, // f64 or null
    pub actual_hours: Option<serde_json::Value>,    // f64 or null
    pub tags: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskDto {
    pub id: String,
    pub title: String,
    pub description: Option<String>,
    pub status: String,
    pub priority: Option<String>,
    pub task_type: Option<String>,
    pub assigned_to: Option<String>,
    pub created_by: Option<String>,
    pub due_date: Option<String>,
    pub estimated_hours: Option<f64>,
    pub actual_hours: Option<f64>,
    pub parent_task_id: Option<String>,
    pub tags: Option<Vec<String>>,
    pub created_at: String,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedTasksResponse {
    pub items: Vec<TaskDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChecklistItem {
    pub id: String,
    pub text: String,
    pub is_completed: bool,
    pub position: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateChecklistItemData {
    pub text: Option<String>,
    pub is_completed: Option<bool>,
}

// ---------------------------------------------------------------------------
// DTOs — Kanban
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanBoardListParams {
    pub search: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<i32>,
    pub per_page: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateKanbanBoardData {
    pub name: String,
    pub description: Option<String>,
    pub columns: Option<Vec<KanbanColumnInput>>,
    pub members: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanColumnInput {
    pub name: String,
    pub task_status: String,
    pub wip_limit: Option<i32>,
    pub color: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateKanbanBoardData {
    pub name: Option<String>,
    pub description: Option<String>,
    pub is_active: Option<bool>,
    pub members: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateKanbanColumnData {
    pub name: Option<String>,
    pub wip_limit: Option<i32>,
    pub color: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanBoardDto {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub is_active: bool,
    pub columns: Option<Vec<KanbanColumnDto>>,
    pub members: Option<Vec<String>>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanColumnDto {
    pub id: String,
    pub name: String,
    pub task_status: String,
    pub wip_limit: Option<i32>,
    pub color: Option<String>,
    pub position: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedKanbanBoardsResponse {
    pub items: Vec<KanbanBoardDto>,
    pub total: i32,
    pub page: i32,
    pub per_page: i32,
    pub total_pages: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoveTaskRequest {
    pub status: String,
    pub position: Option<i32>,
}

// ---------------------------------------------------------------------------
// API — Tasks
// ---------------------------------------------------------------------------

pub struct TaskApi;

impl TaskApi {
    pub async fn list_tasks(
        client: &ApiClient,
        params: Option<&TaskListParams>,
    ) -> Result<PaginatedTasksResponse, ApiError> {
        let path = build_task_query(params);
        client.get(&path).await
    }

    pub async fn get_task(client: &ApiClient, id: &str) -> Result<TaskDto, ApiError> {
        client.get(&format!("/api/v1/tasks/{}", id)).await
    }

    pub async fn create_task(
        client: &ApiClient,
        data: &CreateTaskData,
    ) -> Result<TaskDto, ApiError> {
        client.post("/api/v1/tasks", data).await
    }

    pub async fn update_task(
        client: &ApiClient,
        id: &str,
        data: &UpdateTaskData,
    ) -> Result<TaskDto, ApiError> {
        client.put(&format!("/api/v1/tasks/{}", id), data).await
    }

    pub async fn delete_task(
        client: &ApiClient,
        id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client.delete(&format!("/api/v1/tasks/{}", id)).await
    }

    pub async fn move_task(
        client: &ApiClient,
        id: &str,
        status: &str,
    ) -> Result<TaskDto, ApiError> {
        #[derive(Serialize)]
        struct MoveBody<'a> {
            status: &'a str,
        }
        client
            .post(&format!("/api/v1/tasks/{}/move", id), &MoveBody { status })
            .await
    }

    pub async fn assign_task(
        client: &ApiClient,
        id: &str,
        user_id: &str,
    ) -> Result<TaskDto, ApiError> {
        #[derive(Serialize)]
        struct AssignBody<'a> {
            user_id: &'a str,
        }
        client
            .post(&format!("/api/v1/tasks/{}/assign", id), &AssignBody { user_id })
            .await
    }

    pub async fn unassign_task(client: &ApiClient, id: &str) -> Result<TaskDto, ApiError> {
        client
            .post(
                &format!("/api/v1/tasks/{}/unassign", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn duplicate_task(client: &ApiClient, id: &str) -> Result<TaskDto, ApiError> {
        client
            .post(
                &format!("/api/v1/tasks/{}/duplicate", id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn get_my_tasks(
        client: &ApiClient,
        params: Option<&TaskListParams>,
    ) -> Result<PaginatedTasksResponse, ApiError> {
        let path = build_task_query_with_prefix("/api/v1/tasks/my", params);
        client.get(&path).await
    }

    pub async fn get_due_today(client: &ApiClient) -> Result<Vec<TaskDto>, ApiError> {
        client.get("/api/v1/tasks/due-today").await
    }

    pub async fn get_overdue(client: &ApiClient) -> Result<Vec<TaskDto>, ApiError> {
        client.get("/api/v1/tasks/overdue").await
    }

    pub async fn bulk_update(
        client: &ApiClient,
        ids: &[String],
        data: &UpdateTaskData,
    ) -> Result<Vec<TaskDto>, ApiError> {
        #[derive(Serialize)]
        struct BulkUpdateBody<'a> {
            ids: &'a [String],
            data: &'a UpdateTaskData,
        }
        client
            .post("/api/v1/tasks/bulk-update", &BulkUpdateBody { ids, data })
            .await
    }

    pub async fn bulk_delete(
        client: &ApiClient,
        ids: &[String],
    ) -> Result<serde_json::Value, ApiError> {
        #[derive(Serialize)]
        struct BulkDeleteBody<'a> {
            ids: &'a [String],
        }
        client
            .post("/api/v1/tasks/bulk-delete", &BulkDeleteBody { ids })
            .await
    }

    // ---- Checklist ----
    pub async fn add_checklist_item(
        client: &ApiClient,
        task_id: &str,
        text: &str,
    ) -> Result<ChecklistItem, ApiError> {
        #[derive(Serialize)]
        struct AddChecklistBody<'a> {
            text: &'a str,
        }
        client
            .post(
                &format!("/api/v1/tasks/{}/checklist", task_id),
                &AddChecklistBody { text },
            )
            .await
    }

    pub async fn update_checklist_item(
        client: &ApiClient,
        task_id: &str,
        item_id: &str,
        data: &UpdateChecklistItemData,
    ) -> Result<ChecklistItem, ApiError> {
        client
            .put(
                &format!("/api/v1/tasks/{}/checklist/{}", task_id, item_id),
                data,
            )
            .await
    }

    pub async fn delete_checklist_item(
        client: &ApiClient,
        task_id: &str,
        item_id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client
            .delete(&format!(
                "/api/v1/tasks/{}/checklist/{}",
                task_id, item_id
            ))
            .await
    }

    pub async fn toggle_checklist_item(
        client: &ApiClient,
        task_id: &str,
        item_id: &str,
    ) -> Result<ChecklistItem, ApiError> {
        client
            .post(
                &format!("/api/v1/tasks/{}/checklist/{}/toggle", task_id, item_id),
                &serde_json::json!({}),
            )
            .await
    }

    pub async fn reorder_checklist(
        client: &ApiClient,
        task_id: &str,
        item_ids: &[String],
    ) -> Result<Vec<ChecklistItem>, ApiError> {
        #[derive(Serialize)]
        struct ReorderBody<'a> {
            ids: &'a [String],
        }
        client
            .post(
                &format!("/api/v1/tasks/{}/checklist/reorder", task_id),
                &ReorderBody { ids: item_ids },
            )
            .await
    }

    // ---- Subtasks ----
    pub async fn list_subtasks(
        client: &ApiClient,
        task_id: &str,
    ) -> Result<Vec<TaskDto>, ApiError> {
        client
            .get(&format!("/api/v1/tasks/{}/subtasks", task_id))
            .await
    }

    pub async fn create_subtask(
        client: &ApiClient,
        task_id: &str,
        data: &CreateTaskData,
    ) -> Result<TaskDto, ApiError> {
        client
            .post(&format!("/api/v1/tasks/{}/subtasks", task_id), data)
            .await
    }
}

// ---------------------------------------------------------------------------
// API — Kanban
// ---------------------------------------------------------------------------

pub struct KanbanApi;

impl KanbanApi {
    pub async fn list_kanban_boards(
        client: &ApiClient,
        params: Option<&KanbanBoardListParams>,
    ) -> Result<PaginatedKanbanBoardsResponse, ApiError> {
        let path = build_kanban_query(params);
        client.get(&path).await
    }

    pub async fn get_kanban_board(
        client: &ApiClient,
        id: &str,
    ) -> Result<KanbanBoardDto, ApiError> {
        client.get(&format!("/api/v1/kanban/boards/{}", id)).await
    }

    pub async fn create_kanban_board(
        client: &ApiClient,
        data: &CreateKanbanBoardData,
    ) -> Result<KanbanBoardDto, ApiError> {
        client.post("/api/v1/kanban/boards", data).await
    }

    pub async fn update_kanban_board(
        client: &ApiClient,
        id: &str,
        data: &UpdateKanbanBoardData,
    ) -> Result<KanbanBoardDto, ApiError> {
        client
            .put(&format!("/api/v1/kanban/boards/{}", id), data)
            .await
    }

    pub async fn delete_kanban_board(
        client: &ApiClient,
        id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client.delete(&format!("/api/v1/kanban/boards/{}", id)).await
    }

    pub async fn get_kanban_board_tasks(
        client: &ApiClient,
        id: &str,
        params: Option<&TaskListParams>,
    ) -> Result<HashMap<String, Vec<TaskDto>>, ApiError> {
        let path = build_task_query_with_prefix(
            &format!("/api/v1/kanban/boards/{}/tasks", id),
            params,
        );
        client.get(&path).await
    }

    pub async fn move_task_on_board(
        client: &ApiClient,
        board_id: &str,
        task_id: &str,
        status: &str,
        position: Option<i32>,
    ) -> Result<TaskDto, ApiError> {
        #[derive(Serialize)]
        struct MoveBody<'a> {
            status: &'a str,
            position: Option<i32>,
        }
        client
            .post(
                &format!(
                    "/api/v1/kanban/boards/{}/tasks/{}/move",
                    board_id, task_id
                ),
                &MoveBody { status, position },
            )
            .await
    }

    pub async fn add_board_member(
        client: &ApiClient,
        id: &str,
        user_id: &str,
    ) -> Result<KanbanBoardDto, ApiError> {
        #[derive(Serialize)]
        struct MemberBody<'a> {
            user_id: &'a str,
        }
        client
            .post(
                &format!("/api/v1/kanban/boards/{}/members", id),
                &MemberBody { user_id },
            )
            .await
    }

    pub async fn remove_board_member(
        client: &ApiClient,
        id: &str,
        user_id: &str,
    ) -> Result<serde_json::Value, ApiError> {
        client
            .delete(&format!("/api/v1/kanban/boards/{}/members/{}", id, user_id))
            .await
    }

    // ---- Columns ----
    pub async fn list_columns(
        client: &ApiClient,
        board_id: &str,
    ) -> Result<Vec<KanbanColumnDto>, ApiError> {
        client
            .get(&format!("/api/v1/kanban/boards/{}/columns", board_id))
            .await
    }

    pub async fn update_column(
        client: &ApiClient,
        board_id: &str,
        column_id: &str,
        data: &UpdateKanbanColumnData,
    ) -> Result<KanbanColumnDto, ApiError> {
        client
            .put(
                &format!(
                    "/api/v1/kanban/boards/{}/columns/{}",
                    board_id, column_id
                ),
                data,
            )
            .await
    }

    pub async fn reorder_columns(
        client: &ApiClient,
        board_id: &str,
        column_ids: &[String],
    ) -> Result<Vec<KanbanColumnDto>, ApiError> {
        #[derive(Serialize)]
        struct ReorderBody<'a> {
            ids: &'a [String],
        }
        client
            .post(
                &format!("/api/v1/kanban/boards/{}/columns/reorder", board_id),
                &ReorderBody { ids: column_ids },
            )
            .await
    }
}

// ---------------------------------------------------------------------------
// Helpers — query string builders
// ---------------------------------------------------------------------------

fn build_task_query(params: Option<&TaskListParams>) -> String {
    build_task_query_with_prefix("/api/v1/tasks", params)
}

fn build_task_query_with_prefix(base: &str, params: Option<&TaskListParams>) -> String {
    let Some(p) = params else {
        return base.to_string();
    };

    let mut q = Vec::new();
    if let Some(v) = &p.status {
        q.push(format!("status={}", v));
    }
    if let Some(v) = &p.priority {
        q.push(format!("priority={}", v));
    }
    if let Some(v) = &p.task_type {
        q.push(format!("task_type={}", v));
    }
    if let Some(v) = &p.assigned_to {
        q.push(format!("assigned_to={}", v));
    }
    if let Some(v) = &p.created_by {
        q.push(format!("created_by={}", v));
    }
    if let Some(v) = &p.due_date_from {
        q.push(format!("due_date_from={}", v));
    }
    if let Some(v) = &p.due_date_to {
        q.push(format!("due_date_to={}", v));
    }
    if let Some(v) = &p.search {
        q.push(format!("search={}", v));
    }
    if let Some(v) = &p.linked_entity_type {
        q.push(format!("linked_entity_type={}", v));
    }
    if let Some(v) = &p.linked_entity_id {
        q.push(format!("linked_entity_id={}", v));
    }
    if let Some(v) = &p.parent_task_id {
        q.push(format!("parent_task_id={}", v));
    }
    if let Some(v) = p.page {
        q.push(format!("page={}", v));
    }
    if let Some(v) = p.per_page {
        q.push(format!("per_page={}", v));
    }

    if q.is_empty() {
        base.to_string()
    } else {
        format!("{}?{}", base, q.join("&"))
    }
}

fn build_kanban_query(params: Option<&KanbanBoardListParams>) -> String {
    let Some(p) = params else {
        return "/api/v1/kanban/boards".to_string();
    };

    let mut q = Vec::new();
    if let Some(v) = &p.search {
        q.push(format!("search={}", v));
    }
    if let Some(v) = p.is_active {
        q.push(format!("is_active={}", v));
    }
    if let Some(v) = p.page {
        q.push(format!("page={}", v));
    }
    if let Some(v) = p.per_page {
        q.push(format!("per_page={}", v));
    }

    if q.is_empty() {
        "/api/v1/kanban/boards".to_string()
    } else {
        format!("/api/v1/kanban/boards?{}", q.join("&"))
    }
}

//! Tasks reactive store.
//!
//! Mirrors the Zustand [`tasks.ts`](frontend/src/stores/tasks.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// A task DTO matching the backend API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskDto {
    pub id: String,
    pub title: String,
    pub description: Option<String>,
    pub status: String,
    pub priority: Option<String>,
    pub assignee_id: Option<String>,
    pub due_date: Option<String>,
    pub project_id: Option<String>,
    pub tags: Option<Vec<String>>,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

/// Reactive store for tasks.
#[derive(Debug, Clone)]
pub struct TasksStore {
    /// List of tasks.
    pub tasks: RwSignal<Vec<TaskDto>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl TasksStore {
    pub fn new() -> Self {
        Self {
            tasks: RwSignal::new(Vec::new()),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch tasks, optionally filtered.
    pub async fn fetch_tasks(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<TaskDto>>("/api/v1/tasks").await {
            Ok(tasks) => {
                self.tasks.set(tasks);
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }

    /// Create a new task.
    pub async fn create_task(
        &self,
        client: &ApiClient,
        data: &serde_json::Value,
    ) -> Result<TaskDto, ApiError> {
        let task: TaskDto = client.post("/api/v1/tasks", data).await?;
        self.tasks.update(|t| t.push(task.clone()));
        Ok(task)
    }

    /// Update an existing task.
    pub async fn update_task(
        &self,
        client: &ApiClient,
        id: &str,
        data: &serde_json::Value,
    ) -> Result<TaskDto, ApiError> {
        let task: TaskDto = client.put(&format!("/api/v1/tasks/{}", id), data).await?;
        self.tasks.update(|t| {
            if let Some(pos) = t.iter().position(|x| x.id == id) {
                t[pos] = task.clone();
            }
        });
        Ok(task)
    }

    /// Delete a task.
    pub async fn delete_task(&self, client: &ApiClient, id: &str) -> Result<(), ApiError> {
        client
            .delete::<serde_json::Value>(&format!("/api/v1/tasks/{}", id))
            .await?;
        self.tasks.update(|t| t.retain(|x| x.id != id));
        Ok(())
    }

    /// Move a task to a different status.
    pub async fn move_task(
        &self,
        client: &ApiClient,
        id: &str,
        status: &str,
    ) -> Result<TaskDto, ApiError> {
        let payload = serde_json::json!({ "status": status });
        let task: TaskDto = client
            .put(&format!("/api/v1/tasks/{}/status", id), &payload)
            .await?;
        self.tasks.update(|t| {
            if let Some(pos) = t.iter().position(|x| x.id == id) {
                t[pos] = task.clone();
            }
        });
        Ok(task)
    }
}

impl Default for TasksStore {
    fn default() -> Self {
        Self::new()
    }
}

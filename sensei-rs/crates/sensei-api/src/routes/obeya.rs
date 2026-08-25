//! Obeya (war room / visual management board) route handlers.
//!
//! Provides endpoints for managing Obeya boards and their items – digital
//! equivalents of physical "big room" visual management boards used in
//! lean management for daily stand-ups and strategic reviews.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::events::{
    ObeyaItemAddedEvent, ObeyaItemDeletedEvent, ObeyaItemUpdatedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{ObeyaBoard, ObeyaBoardStore, ObeyaItem};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing Obeya boards.
#[derive(Debug, Deserialize)]
pub struct ListBoardsParams {
    pub board_type: Option<String>,
    pub department: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating an Obeya board.
#[derive(Debug, Deserialize)]
pub struct CreateBoardRequest {
    pub name: String,
    pub description: Option<String>,
    pub board_type: String,
    pub department: Option<String>,
    pub location: Option<String>,
}

/// Request body for updating an Obeya board.
#[derive(Debug, Deserialize)]
pub struct UpdateBoardRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub board_type: Option<String>,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_active: Option<bool>,
}

/// Query parameters for listing items on a board.
#[derive(Debug, Deserialize)]
pub struct ListItemsParams {
    pub status: Option<String>,
    pub item_type: Option<String>,
    pub priority: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating an Obeya item.
#[derive(Debug, Deserialize)]
pub struct CreateItemRequest {
    pub title: String,
    pub description: Option<String>,
    pub item_type: String,
    pub priority: Option<String>,
    pub owner_id: Option<Uuid>,
    pub target_date: Option<String>,
    pub notes: Option<String>,
}

/// Request body for updating an Obeya item.
#[derive(Debug, Deserialize)]
pub struct UpdateItemRequest {
    pub title: Option<String>,
    pub description: Option<String>,
    pub item_type: Option<String>,
    pub status: Option<String>,
    pub priority: Option<String>,
    pub owner_id: Option<Uuid>,
    pub target_date: Option<String>,
    pub notes: Option<String>,
}

// ── Helpers ────────────────────────────────────────────────────────────────

fn get_store(state: &AppState) -> &ObeyaBoardStore {
    &state.obeya_boards
}

fn parse_dt(s: Option<&str>) -> Option<DateTime<Utc>> {
    s.and_then(|s| s.parse::<DateTime<Utc>>().ok())
}

/// Supported Obeya board types (visual management board categories).
const BOARD_TYPES: &[&str] = &[
    "Production",
    "Quality",
    "Safety",
    "Delivery",
    "Cost",
    "People",
    "Maintenance",
    "Engineering",
    "Management",
];

/// Supported Obeya item types.
const ITEM_TYPES: &[&str] = &[
    "KPI", "Action", "Risk", "Issue", "Project", "Kaizen", "Safety", "Other",
];

/// Supported Obeya item statuses.
const ITEM_STATUSES: &[&str] = &[
    "Open",
    "InProgress",
    "InReview",
    "Blocked",
    "Completed",
    "Closed",
    "Cancelled",
];

/// Supported Obeya item priorities.
const ITEM_PRIORITIES: &[&str] = &["Low", "Medium", "High", "Critical", "Urgent"];

fn validate_board_type(board_type: &str) -> Result<()> {
    if !BOARD_TYPES.contains(&board_type) {
        return Err(SenseiError::Validation(format!(
            "Invalid board_type '{board_type}'. Valid values: {}",
            BOARD_TYPES.join(", ")
        )));
    }
    Ok(())
}

fn validate_item_type(item_type: &str) -> Result<()> {
    if !ITEM_TYPES.contains(&item_type) {
        return Err(SenseiError::Validation(format!(
            "Invalid item_type '{item_type}'. Valid values: {}",
            ITEM_TYPES.join(", ")
        )));
    }
    Ok(())
}

fn validate_item_status(status: &str) -> Result<()> {
    if !ITEM_STATUSES.contains(&status) {
        return Err(SenseiError::Validation(format!(
            "Invalid status '{status}'. Valid values: {}",
            ITEM_STATUSES.join(", ")
        )));
    }
    Ok(())
}

fn validate_item_priority(priority: &str) -> Result<()> {
    if !ITEM_PRIORITIES.contains(&priority) {
        return Err(SenseiError::Validation(format!(
            "Invalid priority '{priority}'. Valid values: {}",
            ITEM_PRIORITIES.join(", ")
        )));
    }
    Ok(())
}

/// Publish a domain event via the event bus, logging warnings on failure.
async fn publish_event(state: &AppState, event: &dyn sensei_core::domain::events::DomainEvent) {
    if let Err(e) = state.event_bus.publish(event).await {
        tracing::warn!(error = %e, event_type = %event.event_type(), "Failed to publish domain event");
    }
}

// ── Board Handlers ─────────────────────────────────────────────────────────

/// List all Obeya boards with optional filters.
pub async fn list_boards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListBoardsParams>,
) -> Result<Json<PaginatedResponse<ObeyaBoard>>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let mut items: Vec<ObeyaBoard> = map
        .values()
        .filter(|b| b.tenant_id == tenant_id)
        .filter(|b| match &params.board_type {
            Some(t) => b.board_type == *t,
            None => true,
        })
        .filter(|b| match &params.department {
            Some(d) => b.department.as_deref() == Some(d.as_str()),
            None => true,
        })
        .filter(|b| match params.is_active {
            Some(active) => b.is_active == active,
            None => true,
        })
        .cloned()
        .collect();

    items.sort_by(|a, b| a.name.cmp(&b.name));
    let total = items.len();
    let page = params.page.unwrap_or(1);
    let per_page = params.per_page.unwrap_or(20).min(100);
    let start = (page.saturating_sub(1)) * per_page;
    let data = items.into_iter().skip(start).take(per_page).collect();

    Ok(Json(PaginatedResponse {
        data,
        total,
        page,
        per_page,
        total_pages: total.div_ceil(per_page),
    }))
}

/// Get a specific Obeya board by ID with all items.
pub async fn get_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ObeyaBoard>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let board = map
        .get(&id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?
        .clone();

    Ok(Json(board))
}

/// Create a new Obeya board.
pub async fn create_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateBoardRequest>,
) -> Result<Json<ObeyaBoard>> {
    validate_board_type(&req.board_type)?;
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let board = ObeyaBoard {
        id: Uuid::new_v4(),
        tenant_id,
        name: req.name,
        description: req.description.unwrap_or_default(),
        board_type: req.board_type,
        department: req.department,
        location: req.location,
        is_active: true,
        items: Vec::new(),
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };

    let store = get_store(&state);
    store.write().await.insert(board.id, board.clone());
    Ok(Json(board))
}

/// Update an Obeya board.
pub async fn update_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateBoardRequest>,
) -> Result<Json<ObeyaBoard>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let mut map = store.write().await;

    let board = map
        .get_mut(&id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    if let Some(name) = req.name {
        board.name = name;
    }
    if let Some(description) = req.description {
        board.description = description;
    }
    if let Some(board_type) = req.board_type {
        validate_board_type(&board_type)?;
        board.board_type = board_type;
    }
    if let Some(department) = req.department {
        board.department = Some(department);
    }
    if let Some(location) = req.location {
        board.location = Some(location);
    }
    if let Some(is_active) = req.is_active {
        board.is_active = is_active;
    }
    board.updated_at = Utc::now();

    Ok(Json(board.clone()))
}

/// Delete (deactivate) an Obeya board.
pub async fn delete_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let mut map = store.write().await;

    let board = map
        .get_mut(&id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    board.is_active = false;
    board.updated_at = Utc::now();
    Ok(Json(()))
}

// ── Item Handlers ──────────────────────────────────────────────────────────

/// List items on a specific Obeya board.
pub async fn list_board_items(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(board_id): Path<Uuid>,
    Query(params): Query<ListItemsParams>,
) -> Result<Json<PaginatedResponse<ObeyaItem>>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let map = store.read().await;

    let board = map
        .get(&board_id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(board_id.to_string()))?;

    let mut items: Vec<ObeyaItem> = board
        .items
        .iter()
        .filter(|item| match &params.status {
            Some(s) => item.status == *s,
            None => true,
        })
        .filter(|item| match &params.item_type {
            Some(t) => item.item_type == *t,
            None => true,
        })
        .filter(|item| match &params.priority {
            Some(p) => item.priority == *p,
            None => true,
        })
        .cloned()
        .collect();

    items.sort_by_key(|a| std::cmp::Reverse(a.created_at));
    let total = items.len();
    let page = params.page.unwrap_or(1);
    let per_page = params.per_page.unwrap_or(20).min(100);
    let start = (page.saturating_sub(1)) * per_page;
    let data = items.into_iter().skip(start).take(per_page).collect();

    Ok(Json(PaginatedResponse {
        data,
        total,
        page,
        per_page,
        total_pages: total.div_ceil(per_page),
    }))
}

/// Add a new item to an Obeya board.
///
/// Publishes [`ObeyaItemAddedEvent`] on success.
pub async fn add_board_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(board_id): Path<Uuid>,
    Json(req): Json<CreateItemRequest>,
) -> Result<Json<ObeyaItem>> {
    validate_item_type(&req.item_type)?;
    let priority = req.priority.unwrap_or_else(|| "Medium".to_string());
    validate_item_priority(&priority)?;
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let item = ObeyaItem {
        id: Uuid::new_v4(),
        board_id,
        title: req.title,
        description: req.description.unwrap_or_default(),
        item_type: req.item_type,
        status: "Open".to_string(),
        priority,
        owner_id: req.owner_id,
        target_date: parse_dt(req.target_date.as_deref()),
        completed_at: None,
        notes: req.notes.unwrap_or_default(),
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };

    let store = get_store(&state);
    let mut map = store.write().await;

    let board = map
        .get_mut(&board_id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(board_id.to_string()))?;

    board.items.push(item.clone());
    board.updated_at = now;

    // ── P1-B5: PUBLISH ObeyaItemAddedEvent ───────────────────────────
    let event = ObeyaItemAddedEvent::new(
        tenant_id,
        item.id,
        board_id,
        item.title.clone(),
        item.item_type.clone(),
        user.user_id,
    );
    publish_event(&state, &event).await;

    Ok(Json(item))
}

/// Update an item on an Obeya board.
///
/// Publishes [`ObeyaItemUpdatedEvent`] on success.
pub async fn update_board_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((board_id, item_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<UpdateItemRequest>,
) -> Result<Json<ObeyaItem>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let store = get_store(&state);
    let mut map = store.write().await;

    let board = map
        .get_mut(&board_id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(board_id.to_string()))?;

    let item = board
        .items
        .iter_mut()
        .find(|i| i.id == item_id)
        .ok_or_else(|| SenseiError::NotFound(item_id.to_string()))?;

    let old_status = item.status.clone();

    if let Some(title) = req.title {
        item.title = title;
    }
    if let Some(description) = req.description {
        item.description = description;
    }
    if let Some(item_type) = req.item_type {
        validate_item_type(&item_type)?;
        item.item_type = item_type;
    }
    if let Some(status) = req.status {
        validate_item_status(&status)?;
        let was_terminal = item.status == "Completed" || item.status == "Closed";
        item.status = status;
        let is_terminal = item.status == "Completed" || item.status == "Closed";
        // Record completion exactly once when entering a terminal state, and
        // clear it when the item is reopened.
        match (was_terminal, is_terminal) {
            (false, true) => item.completed_at = Some(now),
            (true, false) => item.completed_at = None,
            _ => {}
        }
    }
    if let Some(priority) = req.priority {
        validate_item_priority(&priority)?;
        item.priority = priority;
    }
    if let Some(owner_id) = req.owner_id {
        item.owner_id = Some(owner_id);
    }
    if let Some(target_date) = req.target_date {
        item.target_date = parse_dt(Some(&target_date));
    }
    if let Some(notes) = req.notes {
        item.notes = notes;
    }
    item.updated_at = now;
    board.updated_at = now;

    // ── P1-B5: PUBLISH ObeyaItemUpdatedEvent ─────────────────────────
    let event = ObeyaItemUpdatedEvent::new(
        tenant_id,
        item.id,
        board_id,
        item.title.clone(),
        old_status,
        item.status.clone(),
        user.user_id,
    );
    publish_event(&state, &event).await;

    Ok(Json(item.clone()))
}

/// Delete an item from an Obeya board.
///
/// Publishes [`ObeyaItemDeletedEvent`] on success.
pub async fn delete_board_item(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((board_id, item_id)): Path<(Uuid, Uuid)>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let store = get_store(&state);
    let mut map = store.write().await;

    let board = map
        .get_mut(&board_id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(board_id.to_string()))?;

    let pos = board
        .items
        .iter()
        .position(|i| i.id == item_id)
        .ok_or_else(|| SenseiError::NotFound(item_id.to_string()))?;

    let removed = board.items.remove(pos);
    board.updated_at = Utc::now();

    // ── P1-B5: PUBLISH ObeyaItemDeletedEvent ─────────────────────────
    let event = ObeyaItemDeletedEvent::new(tenant_id, removed.id, board_id, removed.title);
    publish_event(&state, &event).await;

    Ok(Json(()))
}

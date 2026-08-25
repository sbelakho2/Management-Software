//! Kanban board management route handlers.
//!
//! Provides endpoints for managing Kanban boards, columns, and cards,
//! including card moves and Kanban metrics.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::domain::events::{
    KanbanCardCreatedEvent, KanbanCardDeletedEvent, KanbanCardMovedEvent,
};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{KanbanBoard, KanbanColumn, KanbanCard};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing boards.
#[derive(Debug, Deserialize)]
pub struct ListBoardsParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a board.
#[derive(Debug, Deserialize)]
pub struct BoardRequest {
    pub name: String,
    pub description: String,
}

/// Request body for adding/updating a column.
#[derive(Debug, Deserialize)]
pub struct ColumnRequest {
    pub name: String,
    pub position: i32,
    pub wip_limit: Option<i32>,
}

/// Request body for adding/updating a card.
#[derive(Debug, Deserialize)]
pub struct CardRequest {
    pub title: String,
    pub description: String,
    pub priority: String,
    pub assignee_id: Option<Uuid>,
    pub labels: Vec<String>,
    pub position: i32,
    pub column_id: Option<Uuid>,
    pub due_date: Option<DateTime<Utc>>,
}

/// Request body for moving a card between columns.
#[derive(Debug, Deserialize)]
pub struct MoveCardRequest {
    pub target_column_id: Uuid,
    pub position: i32,
}

/// Query parameters for metrics endpoint.
#[derive(Debug, Deserialize)]
pub struct MetricsQuery {
    pub board_id: Option<Uuid>,
}

/// Kanban metrics response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanMetrics {
    pub total_boards: usize,
    pub total_cards: usize,
    pub total_columns: usize,
    pub cards_by_status: Vec<ColumnCardCount>,
    pub cycle_time_hours: f64,
    pub wip_count: usize,
    pub wip_limit_breached: Vec<WipBreach>,
    pub throughput_last_30_days: usize,
}

/// Count of cards in a column.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnCardCount {
    pub column_name: String,
    pub board_name: String,
    pub card_count: usize,
    pub wip_limit: Option<i32>,
}

/// WIP limit breach information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WipBreach {
    pub board_name: String,
    pub column_name: String,
    pub card_count: usize,
    pub wip_limit: i32,
}

// ── Internal helpers ───────────────────────────────────────────────────────

/// Publish a domain event via the event bus, logging warnings on failure.
async fn publish_event(state: &AppState, event: &dyn sensei_core::domain::events::DomainEvent) {
    if let Err(e) = state.event_bus.publish(event).await {
        tracing::warn!(error = %e, event_type = %event.event_type(), "Failed to publish domain event");
    }
}

// ── Boards ─────────────────────────────────────────────────────────────────

/// List all Kanban boards.
pub async fn list_boards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListBoardsParams>,
) -> Result<Json<PaginatedResponse<KanbanBoard>>> {
    let tenant_id = user.tenant_id;
    let store = state.kanban_boards.read().await;
    let mut boards: Vec<KanbanBoard> = store
        .values()
        .filter(|b| b.tenant_id == tenant_id)
        .cloned()
        .collect();
    boards.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    let result = PaginatedResponse::new(boards, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new Kanban board.
pub async fn create_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<BoardRequest>,
) -> Result<Json<KanbanBoard>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let board = KanbanBoard {
        id: new_id(),
        tenant_id,
        name: req.name,
        description: req.description,
        columns: Vec::new(),
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.kanban_boards.write().await;
    store.insert(board.id, board.clone());
    Ok(Json(board))
}

/// Get a specific Kanban board by ID, including columns and cards.
pub async fn get_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<KanbanBoard>> {
    let tenant_id = user.tenant_id;
    let store = state.kanban_boards.read().await;
    let board = store
        .values()
        .find(|b| b.id == id && b.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Board {id} not found")))?;
    Ok(Json(board))
}

/// Update a Kanban board.
pub async fn update_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<BoardRequest>,
) -> Result<Json<KanbanBoard>> {
    let tenant_id = user.tenant_id;
    let mut store = state.kanban_boards.write().await;
    let board = store
        .get_mut(&id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Board {id} not found")))?;
    board.name = req.name;
    board.description = req.description;
    board.updated_at = Utc::now();
    Ok(Json(board.clone()))
}

/// Delete a Kanban board.
pub async fn delete_board(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.kanban_boards.write().await;
    let exists = store
        .get(&id)
        .filter(|b| b.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("Board {id} not found")));
    }
    store.remove(&id);
    Ok(Json(()))
}

// ── Columns ────────────────────────────────────────────────────────────────

/// Add a column to a board.
pub async fn add_column(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(board_id): Path<Uuid>,
    Json(req): Json<ColumnRequest>,
) -> Result<Json<KanbanColumn>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let column = KanbanColumn {
        id: new_id(),
        board_id,
        name: req.name,
        position: req.position,
        wip_limit: req.wip_limit,
        cards: Vec::new(),
        created_at: now,
        updated_at: now,
    };

    let mut store = state.kanban_boards.write().await;
    let board = store
        .get_mut(&board_id)
        .filter(|b| b.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Board {board_id} not found")))?;
    board.columns.push(column.clone());
    board.updated_at = now;
    Ok(Json(column))
}

/// Update a column.
pub async fn update_column(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ColumnRequest>,
) -> Result<Json<KanbanColumn>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let mut store = state.kanban_boards.write().await;

    for board in store.values_mut().filter(|b| b.tenant_id == tenant_id) {
        if let Some(col) = board.columns.iter_mut().find(|c| c.id == id) {
            col.name = req.name;
            col.position = req.position;
            col.wip_limit = req.wip_limit;
            col.updated_at = now;
            board.updated_at = now;
            return Ok(Json(col.clone()));
        }
    }
    Err(SenseiError::NotFound(format!("Column {id} not found")))
}

/// Delete a column.
pub async fn delete_column(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.kanban_boards.write().await;

    for board in store.values_mut().filter(|b| b.tenant_id == tenant_id) {
        if let Some(pos) = board.columns.iter().position(|c| c.id == id) {
            board.columns.remove(pos);
            board.updated_at = Utc::now();
            return Ok(Json(()));
        }
    }
    Err(SenseiError::NotFound(format!("Column {id} not found")))
}

// ── Cards ──────────────────────────────────────────────────────────────────

/// Add a card to a column.
///
/// Enforces WIP limits on the target column and publishes a
/// [`KanbanCardCreatedEvent`] on success.
pub async fn add_card(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(column_id): Path<Uuid>,
    Json(req): Json<CardRequest>,
) -> Result<Json<KanbanCard>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();

    let mut store = state.kanban_boards.write().await;

    // Find the board that owns this column and get column info
    let (board_id, column) = store
        .values()
        .filter(|b| b.tenant_id == tenant_id)
        .find_map(|b| {
            b.columns
                .iter()
                .find(|c| c.id == column_id)
                .map(|c| (b.id, c.clone()))
        })
        .ok_or_else(|| SenseiError::NotFound(format!("Column {column_id} not found")))?;

    // ── P1-B1: ENFORCE WIP limit ──────────────────────────────────────
    let current_count = store
        .get(&board_id)
        .map(|b| {
            b.columns
                .iter()
                .find(|c| c.id == column_id)
                .map(|c| c.cards.len())
                .unwrap_or(0)
        })
        .unwrap_or(0);

    if let Some(limit) = column.wip_limit {
        if current_count as i32 >= limit {
            return Err(SenseiError::Conflict(format!(
                "Column '{}' has a WIP limit of {} and already has {} cards",
                column.name, limit, current_count
            )));
        }
    }

    // A card created directly in a terminal ("done") column is born
    // completed.
    let col_name_lower = column.name.to_lowercase();
    let is_done_column = col_name_lower == "done" || col_name_lower.starts_with("done");

    let card = KanbanCard {
        id: new_id(),
        column_id,
        title: req.title,
        description: req.description,
        priority: req.priority,
        assignee_id: req.assignee_id,
        labels: req.labels,
        position: req.position,
        due_date: req.due_date,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
        completed_at: if is_done_column { Some(now) } else { None },
    };

    // Store the card in the column
    for board in store.values_mut().filter(|b| b.tenant_id == tenant_id) {
        if let Some(col) = board.columns.iter_mut().find(|c| c.id == column_id) {
            col.cards.push(card.clone());
            col.updated_at = now;
            board.updated_at = now;
            break;
        }
    }

    // ── P1-B2: PUBLISH domain event ───────────────────────────────────
    let event = KanbanCardCreatedEvent::new(
        tenant_id,
        card.id,
        board_id,
        column_id,
        card.title.clone(),
        user.user_id,
    );
    publish_event(&state, &event).await;

    Ok(Json(card))
}

/// Update a card (edit fields or move to another column).
///
/// When the card moves to a different column, WIP limits are enforced on
/// the destination column. Publishes [`KanbanCardMovedEvent`] on column change.
pub async fn update_card(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<CardRequest>,
) -> Result<Json<KanbanCard>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let mut store = state.kanban_boards.write().await;

    // ── P1-B1: Pre-check WIP limit if moving to a different column ──
    // This uses immutable access only, before any mutable iteration.
    // When the target column is the card's current column, the card itself
    // must be excluded from the count (editing an at-limit card is allowed).
    if let Some(target_cid) = req.column_id {
        for board in store.values().filter(|b| b.tenant_id == tenant_id) {
            let card_current_col = board
                .columns
                .iter()
                .find(|c| c.cards.iter().any(|card| card.id == id))
                .map(|c| c.id);
            if let Some(target_col) = board.columns.iter().find(|c| c.id == target_cid) {
                if let Some(limit) = target_col.wip_limit {
                    let mut count = target_col.cards.len();
                    if card_current_col == Some(target_cid) {
                        count = count.saturating_sub(1);
                    }
                    if count as i32 >= limit {
                        return Err(SenseiError::Conflict(format!(
                            "Target column '{}' has a WIP limit of {} and already has {} cards",
                            target_col.name, limit, count
                        )));
                    }
                }
            }
        }
    }

    for board in store.values_mut().filter(|b| b.tenant_id == tenant_id) {
        // Find the source column index by looking for the card
        let src_idx = match board
            .columns
            .iter()
            .position(|c| c.cards.iter().any(|card| card.id == id))
        {
            Some(idx) => idx,
            None => continue,
        };

        let target_cid = req.column_id.unwrap_or(board.columns[src_idx].id);

        if target_cid != board.columns[src_idx].id {
            // ── Card is being moved to a different column ─────────────
            let tgt_idx = board
                .columns
                .iter()
                .position(|c| c.id == target_cid)
                .ok_or_else(|| SenseiError::NotFound(format!("Target column {target_cid} not found")))?;

            let old_column_name = board.columns[src_idx].name.clone();
            let target_col_name = board.columns[tgt_idx].name.clone();

            let card_pos = board.columns[src_idx]
                .cards
                .iter()
                .position(|c| c.id == id)
                .unwrap();
            let mut moved = board.columns[src_idx].cards.remove(card_pos);
            moved.title = req.title;
            moved.description = req.description;
            moved.priority = req.priority;
            moved.assignee_id = req.assignee_id;
            moved.labels = req.labels;
            moved.position = req.position;
            moved.column_id = target_cid;
            moved.due_date = req.due_date;
            moved.updated_at = now;

            // Track completion: entering a terminal ("done") column stamps
            // completed_at; leaving one clears it.
            let target_name_lower = board.columns[tgt_idx].name.to_lowercase();
            let target_is_done = target_name_lower == "done" || target_name_lower.starts_with("done");
            if target_is_done {
                if moved.completed_at.is_none() {
                    moved.completed_at = Some(now);
                }
            } else {
                moved.completed_at = None;
            }

            board.columns[src_idx].updated_at = now;
            board.columns[tgt_idx].cards.push(moved.clone());
            board.columns[tgt_idx].updated_at = now;
            board.updated_at = now;

            // ── P1-B2: PUBLISH KanbanCardMovedEvent ──────────────────
            let event = KanbanCardMovedEvent::new(
                tenant_id,
                moved.id,
                board.id,
                old_column_name,
                target_col_name,
            );
            publish_event(&state, &event).await;

            return Ok(Json(moved));
        } else {
            // ── Same column update — no WIP check needed ─────────────
            let card_pos = board.columns[src_idx]
                .cards
                .iter()
                .position(|c| c.id == id)
                .unwrap();
            // Set column timestamp before borrowing card to avoid
            // simultaneous mutable borrows of `board.columns`.
            board.columns[src_idx].updated_at = now;
            let card = &mut board.columns[src_idx].cards[card_pos];
            card.title = req.title;
            card.description = req.description;
            card.priority = req.priority;
            card.assignee_id = req.assignee_id;
            card.labels = req.labels;
            card.position = req.position;
            card.due_date = req.due_date;
            card.updated_at = now;
            board.updated_at = now;
            return Ok(Json(card.clone()));
        }
    }
    Err(SenseiError::NotFound(format!("Card {id} not found")))
}

/// Delete a card.
///
/// Publishes [`KanbanCardDeletedEvent`] on success.
pub async fn delete_card(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.kanban_boards.write().await;

    for board in store.values_mut().filter(|b| b.tenant_id == tenant_id) {
        for col in board.columns.iter_mut() {
            if let Some(pos) = col.cards.iter().position(|c| c.id == id) {
                let removed = col.cards.remove(pos);
                col.updated_at = Utc::now();
                board.updated_at = Utc::now();

                // ── P1-B2: PUBLISH KanbanCardDeletedEvent ────────────
                let event = KanbanCardDeletedEvent::new(
                    tenant_id,
                    removed.id,
                    board.id,
                    col.id,
                    removed.title,
                );
                publish_event(&state, &event).await;

                return Ok(Json(()));
            }
        }
    }
    Err(SenseiError::NotFound(format!("Card {id} not found")))
}

/// Move a card between columns.
///
/// Enforces WIP limits on the destination column, tracks completion when
/// the card enters a terminal ("done") column, and publishes
/// [`KanbanCardMovedEvent`] on success.
pub async fn move_card(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(card_id): Path<Uuid>,
    Json(req): Json<MoveCardRequest>,
) -> Result<Json<KanbanCard>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let mut store = state.kanban_boards.write().await;

    for board in store.values_mut().filter(|b| b.tenant_id == tenant_id) {
        // Use indexed access to avoid nested mutable borrow conflicts
        let src_idx = match board
            .columns
            .iter()
            .position(|c| c.cards.iter().any(|card| card.id == card_id))
        {
            Some(idx) => idx,
            None => continue,
        };

        // A missing destination column is an explicit error naming the
        // column, not a misleading "card not found".
        let Some(tgt_idx) = board.columns.iter().position(|c| c.id == req.target_column_id) else {
            return Err(SenseiError::NotFound(format!(
                "Target column {} not found on board {}",
                req.target_column_id, board.id
            )));
        };

        // ── P1-B1: ENFORCE WIP limit on destination column ────────────
        // The card being moved is still in the source column, so the
        // destination count does not include it.
        if let Some(limit) = board.columns[tgt_idx].wip_limit {
            let target_card_count = board.columns[tgt_idx].cards.len();
            if target_card_count as i32 >= limit {
                return Err(SenseiError::Conflict(format!(
                    "Target column '{}' has a WIP limit of {} and already has {} cards",
                    board.columns[tgt_idx].name, limit, target_card_count
                )));
            }
        }

        let from_column_name = board.columns[src_idx].name.clone();
        let to_column_name = board.columns[tgt_idx].name.clone();

        let pos = board.columns[src_idx]
            .cards
            .iter()
            .position(|c| c.id == card_id)
            .unwrap();
        let mut card = board.columns[src_idx].cards.remove(pos);
        card.column_id = req.target_column_id;
        card.position = req.position;
        card.updated_at = now;

        // Track completion: entering a terminal ("done") column stamps
        // completed_at; leaving one clears it.
        let target_name_lower = board.columns[tgt_idx].name.to_lowercase();
        let target_is_done = target_name_lower == "done" || target_name_lower.starts_with("done");
        if target_is_done {
            if card.completed_at.is_none() {
                card.completed_at = Some(now);
            }
        } else {
            card.completed_at = None;
        }

        board.columns[src_idx].updated_at = now;

        board.columns[tgt_idx].cards.push(card.clone());
        board.columns[tgt_idx].updated_at = now;
        board.updated_at = now;

        // ── P1-B2: PUBLISH KanbanCardMovedEvent ──────────────────────
        let event = KanbanCardMovedEvent::new(
            tenant_id,
            card.id,
            board.id,
            from_column_name,
            to_column_name,
        );
        publish_event(&state, &event).await;

        return Ok(Json(card));
    }
    Err(SenseiError::NotFound(format!("Card {card_id} not found")))
}

// ── Kanban Metrics ─────────────────────────────────────────────────────────

/// Get Kanban metrics (cycle time, WIP, throughput).
///
/// Supports an optional `board_id` query parameter to scope metrics to a
/// single board. Calculates cycle time using timestamps, reports WIP breaches
/// across all columns, and counts throughput from cards in done columns over
/// the last 30 days.
pub async fn get_kanban_metrics(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(query): Query<MetricsQuery>,
) -> Result<Json<KanbanMetrics>> {
    let tenant_id = user.tenant_id;
    let store = state.kanban_boards.read().await;
    let boards: Vec<&KanbanBoard> = store
        .values()
        .filter(|b| b.tenant_id == tenant_id)
        .filter(|b| match query.board_id {
            Some(bid) => b.id == bid,
            None => true,
        })
        .collect();

    let total_boards = boards.len();
    let mut total_cards = 0usize;
    let mut total_columns = 0usize;
    let mut cards_by_status: Vec<ColumnCardCount> = Vec::new();
    let mut wip_count = 0usize;
    let mut wip_limit_breached: Vec<WipBreach> = Vec::new();
    let mut all_cycle_times: Vec<f64> = Vec::new();

    for board in &boards {
        for col in &board.columns {
            total_columns += 1;
            let card_count = col.cards.len();
            total_cards += card_count;

            cards_by_status.push(ColumnCardCount {
                column_name: col.name.clone(),
                board_name: board.name.clone(),
                card_count,
                wip_limit: col.wip_limit,
            });

            // Count cards in "in progress" type columns as WIP
            let col_name_lower = col.name.to_lowercase();
            if col_name_lower.contains("progress")
                || col_name_lower.contains("doing")
                || col_name_lower.contains("wip")
            {
                wip_count += card_count;
            }

            // ── P1-B4: Check ALL columns for WIP breaches ────────────
            // Consistent with enforcement (>=): a column at its limit is
            // breached because no further card can be added.
            if let Some(limit) = col.wip_limit {
                if card_count as i32 >= limit {
                    wip_limit_breached.push(WipBreach {
                        board_name: board.name.clone(),
                        column_name: col.name.clone(),
                        card_count,
                        wip_limit: limit,
                    });
                }
            }

            // ── P1-B3: Improved cycle time calculation ────────────────
            // Check for "done" columns using exact name matching on
            // known terminal statuses, then calculate per-card cycle time
            // as completed_at - created_at.
            let col_is_done = col_name_lower == "done"
                || col_name_lower == "completed"
                || col_name_lower.starts_with("done");

            if col_is_done {
                for card in &col.cards {
                    let end = card.completed_at.unwrap_or(card.updated_at);
                    let cycle = (end - card.created_at).num_minutes() as f64 / 60.0;
                    if cycle > 0.0 {
                        all_cycle_times.push(cycle);
                    }
                }
            }
        }
    }

    // Average cycle time across all done-column cards
    let cycle_time_hours = if all_cycle_times.is_empty() {
        0.0
    } else {
        all_cycle_times.iter().sum::<f64>() / all_cycle_times.len() as f64
    };

    // ── P1-B4: Throughput — count completed cards (completed_at within
    // the last 30 days), regardless of which board/column they sit in.
    let thirty_days_ago = Utc::now() - chrono::Duration::days(30);
    let throughput = boards
        .iter()
        .flat_map(|b| b.columns.iter())
        .flat_map(|col| col.cards.iter())
        .filter(|card| {
            card.completed_at
                .is_some_and(|completed_at| completed_at >= thirty_days_ago)
        })
        .count();

    let metrics = KanbanMetrics {
        total_boards,
        total_cards,
        total_columns,
        cards_by_status,
        cycle_time_hours,
        wip_count,
        wip_limit_breached,
        throughput_last_30_days: throughput,
    };
    Ok(Json(metrics))
}

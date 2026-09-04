//! Work Order route handlers.
//!
//! Provides endpoints for managing manufacturing work orders, including
//! CRUD, status transitions, operations tracking, and statistics.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::request_context::RequestContext;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::production::{WorkOrder, WorkOrderListFilter};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::authorization::build_request_context;
use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing work orders.
#[derive(Debug, Deserialize)]
pub struct ListWorkOrdersParams {
    pub status: Option<String>,
    pub priority: Option<String>,
    pub work_center_id: Option<Uuid>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating a work order (partial update).
#[derive(Debug, Deserialize)]
pub struct UpdateWorkOrderRequest {
    pub product_id: Option<Uuid>,
    pub product_name: Option<String>,
    pub quantity: Option<i64>,
    pub priority: Option<String>,
    pub work_center_id: Option<Uuid>,
    pub scheduled_start: Option<String>,
    pub scheduled_end: Option<String>,
    pub assigned_to: Option<Uuid>,
    pub notes: Option<String>,
}

/// Request body for updating work order status.
#[derive(Debug, Deserialize)]
pub struct UpdateStatusRequest {
    pub status: String,
}

/// A work order operation record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderOperation {
    pub id: Uuid,
    pub work_order_id: Uuid,
    pub operation_number: i32,
    pub description: String,
    pub work_center_id: Option<Uuid>,
    pub setup_time_minutes: Option<i32>,
    pub run_time_minutes: Option<i32>,
    pub status: String,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

/// Work order statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderStats {
    pub total: usize,
    pub by_status: Vec<StatusCount>,
    pub by_priority: Vec<PriorityCount>,
    pub total_quantity_planned: i64,
    pub total_quantity_completed: i64,
    pub on_time_percentage: f64,
}

/// Status count entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusCount {
    pub status: String,
    pub count: usize,
}

/// Priority count entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriorityCount {
    pub priority: String,
    pub count: usize,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// Page through every work order the caller's request context authorizes
/// (the service embeds the ctx scope as a SQL predicate / list filter; the
/// client work-center filter is ANDed, never widening).
async fn fetch_all_work_orders(
    production: &dyn sensei_services::production::ProductionService,
    ctx: &RequestContext,
) -> Result<Vec<WorkOrder>> {
    const PER_PAGE: usize = 100;
    let mut all = Vec::new();
    let mut page = 1usize;
    loop {
        let filter = WorkOrderListFilter {
            status: None,
            work_center_id: None,
            page: Some(page),
            per_page: Some(PER_PAGE),
        };
        let res = production.list_work_orders(ctx, &filter).await?;
        let fetched = res.data.len();
        all.extend(res.data);
        if fetched < PER_PAGE {
            break;
        }
        page += 1;
    }
    Ok(all)
}

/// List all work orders with optional filters and pagination.
///
/// The service only filters by status and work center; priority and date
/// filters are applied here on the tenant's full dataset.
pub async fn list_work_orders(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListWorkOrdersParams>,
) -> Result<Json<PaginatedResponse<WorkOrder>>> {
    user.require_permission("production:work-order:read")?;
    let ctx = build_request_context(&user, &state).await?;

    let date_from = params
        .date_from
        .as_deref()
        .map(|d| DateTime::parse_from_rfc3339(d).map(|dt| dt.with_timezone(&Utc)))
        .transpose()
        .map_err(|e| {
            sensei_core::error::SenseiError::Validation(format!("Invalid date_from: {e}"))
        })?;
    let date_to = params
        .date_to
        .as_deref()
        .map(|d| DateTime::parse_from_rfc3339(d).map(|dt| dt.with_timezone(&Utc)))
        .transpose()
        .map_err(|e| {
            sensei_core::error::SenseiError::Validation(format!("Invalid date_to: {e}"))
        })?;

    let all = fetch_all_work_orders(state.production_service.as_ref(), &ctx).await?;
    let mut filtered: Vec<WorkOrder> = all
        .into_iter()
        .filter(|o| {
            params.status.as_deref().is_none_or(|s| o.status == s)
                && params.priority.as_deref().is_none_or(|p| o.priority == p)
                && params
                    .work_center_id
                    .is_none_or(|wc| o.work_center_id == Some(wc))
                && date_from.is_none_or(|d| o.scheduled_start.is_some_and(|start| start >= d))
                && date_to.is_none_or(|d| o.scheduled_start.is_some_and(|start| start <= d))
        })
        .collect();
    filtered.sort_by_key(|a| std::cmp::Reverse(a.updated_at));

    let total = filtered.len();
    let page = params.page.unwrap_or(1).max(1);
    let per_page = params.per_page.unwrap_or(20).clamp(1, 100);
    let start = (page.saturating_sub(1)) * per_page;
    let data = filtered.into_iter().skip(start).take(per_page).collect();

    Ok(Json(PaginatedResponse {
        data,
        total,
        page,
        per_page,
        total_pages: total.div_ceil(per_page),
    }))
}

/// Get a specific work order by ID with full details.
pub async fn get_work_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<WorkOrder>> {
    user.require_permission("production:work-order:read")?;
    let ctx = build_request_context(&user, &state).await?;
    let order = state.production_service.get_work_order(&ctx, id).await?;
    Ok(Json(order))
}

/// Create a new work order.
pub async fn create_work_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<WorkOrder>,
) -> Result<Json<WorkOrder>> {
    user.require_permission("production:work-order:create")?;
    let ctx = build_request_context(&user, &state).await?;
    let order = state
        .production_service
        .create_work_order(&ctx, req)
        .await?;
    Ok(Json(order))
}

/// Update a work order's editable fields.
///
/// Persists the merged record through the production service — the edit is
/// real, not a status-only round trip.
pub async fn update_work_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateWorkOrderRequest>,
) -> Result<Json<WorkOrder>> {
    user.require_permission("production:work-order:update")?;
    let ctx = build_request_context(&user, &state).await?;

    // Fetch the existing work order to verify it exists and merge with it.
    let mut updated = state.production_service.get_work_order(&ctx, id).await?;

    // Apply changes from the request
    if let Some(product_id) = req.product_id {
        updated.product_id = product_id;
    }
    if let Some(product_name) = req.product_name {
        updated.product_name = product_name;
    }
    if let Some(quantity) = req.quantity {
        updated.quantity = quantity;
    }
    if let Some(priority) = req.priority {
        updated.priority = priority;
    }
    if let Some(work_center_id) = req.work_center_id {
        updated.work_center_id = Some(work_center_id);
    }
    if let Some(assigned_to) = req.assigned_to {
        updated.assigned_to = vec![assigned_to];
    }
    if let Some(notes) = req.notes {
        updated.notes = notes;
    }
    if let Some(scheduled_start) = req.scheduled_start {
        updated.scheduled_start = Some(
            DateTime::parse_from_rfc3339(&scheduled_start)
                .map_err(|e| {
                    sensei_core::error::SenseiError::Validation(format!(
                        "Invalid scheduled_start: {e}"
                    ))
                })?
                .with_timezone(&Utc),
        );
    }
    if let Some(scheduled_end) = req.scheduled_end {
        updated.scheduled_end = Some(
            DateTime::parse_from_rfc3339(&scheduled_end)
                .map_err(|e| {
                    sensei_core::error::SenseiError::Validation(format!(
                        "Invalid scheduled_end: {e}"
                    ))
                })?
                .with_timezone(&Utc),
        );
    }
    updated.updated_at = Utc::now();

    let order = state
        .production_service
        .update_work_order(&ctx, id, updated)
        .await?;
    Ok(Json(order))
}

/// Soft-delete (cancel) a work order by setting its status to "Cancelled".
pub async fn delete_work_order(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("production:work-order:delete")?;
    let ctx = build_request_context(&user, &state).await?;
    state
        .production_service
        .update_work_order_status(&ctx, id, "Cancelled")
        .await?;
    Ok(Json(()))
}

/// Update a work order's status (e.g., Scheduled → InProgress → Completed).
pub async fn update_work_order_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateStatusRequest>,
) -> Result<Json<WorkOrder>> {
    user.require_permission("production:work-order:update")?;
    let ctx = build_request_context(&user, &state).await?;
    let order = state
        .production_service
        .update_work_order_status(&ctx, id, &req.status)
        .await?;
    Ok(Json(order))
}

/// List operations for a specific work order.
///
/// Operations are tracked per work order; returns an empty list if
/// no operations have been recorded.
pub async fn list_work_order_operations(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Vec<WorkOrderOperation>>> {
    user.require_permission("production:work-order:read")?;
    let ctx = build_request_context(&user, &state).await?;
    let ops = state
        .production_service
        .list_work_order_operations(&ctx, id)
        .await?;

    // Map from service DTO to route response DTO
    let result: Vec<WorkOrderOperation> = ops
        .into_iter()
        .map(|op| WorkOrderOperation {
            id: op.id,
            work_order_id: op.work_order_id,
            operation_number: op.operation_number,
            description: op.description,
            work_center_id: op.work_center_id,
            setup_time_minutes: op.setup_time_minutes,
            run_time_minutes: op.run_time_minutes,
            status: op.status,
            started_at: op.started_at,
            completed_at: op.completed_at,
            created_at: op.created_at,
        })
        .collect();

    Ok(Json(result))
}

/// Get work order statistics aggregated across all work orders.
pub async fn get_work_order_stats(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<WorkOrderStats>> {
    user.require_permission("production:work-order:read")?;
    let ctx = build_request_context(&user, &state).await?;
    let orders = fetch_all_work_orders(state.production_service.as_ref(), &ctx).await?;

    let total = orders.len();

    // Compute status breakdown
    let mut status_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut priority_map: std::collections::HashMap<String, usize> =
        std::collections::HashMap::new();
    let mut total_quantity_planned: i64 = 0;
    let mut total_quantity_completed: i64 = 0;

    for order in &orders {
        *status_map.entry(order.status.clone()).or_insert(0) += 1;
        *priority_map.entry(order.priority.clone()).or_insert(0) += 1;
        total_quantity_planned += order.quantity;
        total_quantity_completed += order.quantity_completed;
    }

    let by_status: Vec<StatusCount> = status_map
        .into_iter()
        .map(|(status, count)| StatusCount { status, count })
        .collect();

    let by_priority: Vec<PriorityCount> = priority_map
        .into_iter()
        .map(|(priority, count)| PriorityCount { priority, count })
        .collect();

    // On-time = completed orders that finished by their scheduled end
    // (orders without a schedule are considered on time).
    let completed_orders: Vec<&WorkOrder> =
        orders.iter().filter(|o| o.status == "completed").collect();
    let on_time = completed_orders
        .iter()
        .filter(|o| match (o.actual_end, o.scheduled_end) {
            (Some(actual), Some(scheduled)) => actual <= scheduled,
            _ => true,
        })
        .count();
    let on_time_percentage = if completed_orders.is_empty() {
        100.0
    } else {
        (on_time as f64 / completed_orders.len() as f64) * 100.0
    };

    Ok(Json(WorkOrderStats {
        total,
        by_status,
        by_priority,
        total_quantity_planned,
        total_quantity_completed,
        on_time_percentage,
    }))
}

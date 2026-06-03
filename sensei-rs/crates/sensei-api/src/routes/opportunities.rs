//! Opportunity management route handlers.
//!
//! Provides CRUD endpoints for sales opportunity tracking and pipeline management.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::Opportunity;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing opportunities.
#[derive(Debug, Deserialize)]
pub struct ListOpportunitiesParams {
    pub stage: Option<String>,
    pub assigned_to: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating an opportunity.
#[derive(Debug, Deserialize)]
pub struct OpportunityRequest {
    pub title: String,
    pub description: String,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub stage: String,
    pub probability: f64,
    pub expected_value: f64,
    pub currency: String,
    pub expected_close_date: Option<DateTime<Utc>>,
    pub assigned_to: Option<Uuid>,
    pub notes: String,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// List all opportunities with optional filters.
pub async fn list_opportunities(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListOpportunitiesParams>,
) -> Result<Json<PaginatedResponse<Opportunity>>> {
    let store = state.opportunities.read().await;
    let mut ops: Vec<Opportunity> = store
        .values()
        .filter(|o| o.tenant_id == user.tenant_id)
        .filter(|o| params.stage.as_ref().map_or(true, |s| o.stage == *s))
        .filter(|o| params.assigned_to.map_or(true, |a| o.assigned_to == Some(a)))
        .cloned()
        .collect();
    ops.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    let result = PaginatedResponse::new(ops, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new opportunity.
pub async fn create_opportunity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<OpportunityRequest>,
) -> Result<Json<Opportunity>> {
    let now = Utc::now();
    let opportunity = Opportunity {
        id: new_id(),
        tenant_id: user.tenant_id,
        title: req.title,
        description: req.description,
        customer_id: req.customer_id,
        customer_name: req.customer_name,
        stage: req.stage,
        probability: req.probability,
        expected_value: req.expected_value,
        currency: req.currency,
        expected_close_date: req.expected_close_date,
        assigned_to: req.assigned_to,
        notes: req.notes,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.opportunities.write().await;
    store.insert(opportunity.id, opportunity.clone());
    Ok(Json(opportunity))
}

/// Get a specific opportunity by ID.
pub async fn get_opportunity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Opportunity>> {
    let store = state.opportunities.read().await;
    let opp = store
        .values()
        .find(|o| o.id == id && o.tenant_id == user.tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Opportunity {id} not found")))?;
    Ok(Json(opp))
}

/// Update an opportunity.
pub async fn update_opportunity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<OpportunityRequest>,
) -> Result<Json<Opportunity>> {
    let mut store = state.opportunities.write().await;
    let opp = store
        .get_mut(&id)
        .filter(|o| o.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Opportunity {id} not found")))?;
    opp.title = req.title;
    opp.description = req.description;
    opp.customer_id = req.customer_id;
    opp.customer_name = req.customer_name;
    opp.stage = req.stage;
    opp.probability = req.probability;
    opp.expected_value = req.expected_value;
    opp.currency = req.currency;
    opp.expected_close_date = req.expected_close_date;
    opp.assigned_to = req.assigned_to;
    opp.notes = req.notes;
    opp.updated_at = Utc::now();
    Ok(Json(opp.clone()))
}

/// Delete an opportunity.
pub async fn delete_opportunity(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    let mut store = state.opportunities.write().await;
    let exists = store
        .get(&id)
        .filter(|o| o.tenant_id == user.tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("Opportunity {id} not found")));
    }
    store.remove(&id);
    Ok(Json(()))
}

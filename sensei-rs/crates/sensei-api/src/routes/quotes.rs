//! Quote management route handlers.
//!
//! Provides endpoints for managing quotes, including versioning and lifecycle,
//! delegating to the supply chain service.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use sensei_services::supply_chain::{Quote, QuoteLineItem};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::QuoteVersion;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing quotes.
#[derive(Debug, Deserialize)]
pub struct ListQuotesParams {
    pub status: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a quote.
#[derive(Debug, Deserialize)]
pub struct QuoteRequest {
    pub rfq_id: Option<Uuid>,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub line_items: Vec<QuoteLineItem>,
    pub total_amount: rust_decimal::Decimal,
    pub currency: String,
    pub valid_until: DateTime<Utc>,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// Generate a quote number: `QTE-YYYYMMDD-{8 hex chars}`.
fn generate_quote_number() -> String {
    let date = Utc::now().format("%Y%m%d");
    let suffix: String = Uuid::new_v4()
        .as_simple()
        .encode_lower(&mut Uuid::encode_buffer())[..8]
        .to_string();
    format!("QTE-{date}-{suffix}")
}

/// List all quotes with optional filters.
pub async fn list_quotes(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListQuotesParams>,
) -> Result<Json<PaginatedResponse<Quote>>> {
    user.require_permission("purchasing:quote:create")?;
    let tenant_id = user.tenant_id;
    let quotes = state
        .supply_chain_service
        .list_quotes(
            tenant_id,
            params.status.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(quotes))
}

/// Create a new quote.
pub async fn create_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<QuoteRequest>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:create")?;
    let tenant_id = user.tenant_id;
    let quote = Quote {
        id: Uuid::new_v4(),
        tenant_id,
        quote_number: generate_quote_number(),
        rfq_id: req.rfq_id,
        customer_id: req.customer_id,
        customer_name: req.customer_name,
        status: "draft".to_string(),
        line_items: req.line_items,
        total_amount: req.total_amount,
        currency: req.currency,
        valid_until: req.valid_until,
        created_by: user.user_id,
        created_at: Utc::now(),
    };
    let created = state
        .supply_chain_service
        .create_quote(tenant_id, quote)
        .await?;
    Ok(Json(created))
}

/// Get a specific quote by ID.
pub async fn get_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:create")?;
    let tenant_id = user.tenant_id;
    let quote = state.supply_chain_service.get_quote(tenant_id, id).await?;
    Ok(Json(quote))
}

/// Update a quote.
pub async fn update_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<QuoteRequest>,
) -> Result<Json<Quote>> {
    user.require_permission("purchasing:quote:update")?;
    let tenant_id = user.tenant_id;
    let mut quote = state.supply_chain_service.get_quote(tenant_id, id).await?;
    quote.rfq_id = req.rfq_id;
    quote.customer_id = req.customer_id;
    quote.customer_name = req.customer_name;
    quote.line_items = req.line_items;
    quote.total_amount = req.total_amount;
    quote.currency = req.currency;
    quote.valid_until = req.valid_until;
    let updated = state
        .supply_chain_service
        .update_quote(tenant_id, id, quote)
        .await?;
    Ok(Json(updated))
}

/// Delete a quote.
pub async fn delete_quote(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("purchasing:quote:update")?;
    let tenant_id = user.tenant_id;
    state
        .supply_chain_service
        .delete_quote(tenant_id, id)
        .await?;
    Ok(Json(()))
}

/// Create a new frozen version of a quote.
pub async fn create_quote_version(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(quote_id): Path<Uuid>,
) -> Result<Json<QuoteVersion>> {
    user.require_permission("purchasing:quote:create")?;
    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .get_quote(tenant_id, quote_id)
        .await?;

    let mut version_store = state.quote_versions.write(user.tenant_id).await;
    let version_number = version_store
        .values()
        .filter(|v| v.quote_id == quote_id && v.tenant_id == tenant_id)
        .map(|v| v.version_number)
        .max()
        .unwrap_or(0)
        + 1;

    let version = QuoteVersion {
        id: new_id(),
        quote_id,
        tenant_id,
        version_number,
        quote_data: serde_json::to_value(&quote)
            .map_err(|e| SenseiError::Internal(format!("Failed to serialize quote: {e}")))?,
        created_by: user.user_id,
        created_at: Utc::now(),
    };
    version_store.insert(version.id, version.clone());
    Ok(Json(version))
}

/// List all versions of a quote.
pub async fn list_quote_versions(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(quote_id): Path<Uuid>,
) -> Result<Json<Vec<QuoteVersion>>> {
    user.require_permission("purchasing:quote:create")?;
    let tenant_id = user.tenant_id;
    // Verify the quote exists
    let _ = state
        .supply_chain_service
        .get_quote(tenant_id, quote_id)
        .await?;

    let version_store = state.quote_versions.read(user.tenant_id).await;
    let mut versions: Vec<QuoteVersion> = version_store
        .values()
        .filter(|v| v.quote_id == quote_id && v.tenant_id == tenant_id)
        .cloned()
        .collect();
    versions.sort_by_key(|a| a.version_number);
    Ok(Json(versions))
}

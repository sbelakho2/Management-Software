//! Plant topology (item 90): sites, value streams and product families give
//! every operational fact a "where" — tenant -> site -> value stream ->
//! product family. The future agent receives these as explicit context.

use axum::extract::State;
use axum::Json;
use rust_decimal::Decimal;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::SenseiError;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, sqlx::FromRow)]
pub struct Site {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub site_code: String,
    pub name: String,
    pub address: Option<String>,
    pub timezone: String,
    pub is_active: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, sqlx::FromRow)]
pub struct ValueStream {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub site_id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub is_active: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, sqlx::FromRow)]
pub struct ProductFamily {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub site_id: Option<Uuid>,
    pub name: String,
    pub description: Option<String>,
    pub is_active: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CreateSiteRequest {
    pub site_code: String,
    pub name: String,
    pub address: Option<String>,
    pub timezone: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CreateValueStreamRequest {
    pub site_id: Uuid,
    pub name: String,
    pub description: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CreateProductFamilyRequest {
    pub site_id: Option<Uuid>,
    pub name: String,
    pub description: Option<String>,
}

/// Request: a demand window for a product family (feeds the takt kernel).
#[derive(Debug, Clone, Deserialize)]
pub struct DemandWindowRequest {
    pub product_family_id: Uuid,
    pub site_id: Uuid,
    pub start: chrono::DateTime<chrono::Utc>,
    pub end: chrono::DateTime<chrono::Utc>,
    pub required_units: Decimal,
}

pub async fn create_site(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateSiteRequest>,
) -> Result<Json<Site>, SenseiError> {
    user.require_permission("tps:work-center:manage")?;
    let site = Site {
        id: Uuid::new_v4(),
        tenant_id: user.tenant_id,
        site_code: req.site_code,
        name: req.name,
        address: req.address,
        timezone: req.timezone.unwrap_or_else(|| "UTC".to_string()),
        is_active: true,
    };
    state
        .topology
        .put_site(&site)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(site))
}

pub async fn list_sites(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<Site>>, SenseiError> {
    user.require_permission("tps:work-center:read")?;
    let sites = state
        .topology
        .list_sites(user.tenant_id)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(sites))
}

pub async fn create_value_stream(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateValueStreamRequest>,
) -> Result<Json<ValueStream>, SenseiError> {
    user.require_permission("tps:work-center:manage")?;
    let vs = ValueStream {
        id: Uuid::new_v4(),
        tenant_id: user.tenant_id,
        site_id: req.site_id,
        name: req.name,
        description: req.description,
        is_active: true,
    };
    state
        .topology
        .put_value_stream(&vs)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(vs))
}

pub async fn list_value_streams(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<ValueStream>>, SenseiError> {
    user.require_permission("tps:work-center:read")?;
    let streams = state
        .topology
        .list_value_streams(user.tenant_id)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(streams))
}

pub async fn create_product_family(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateProductFamilyRequest>,
) -> Result<Json<ProductFamily>, SenseiError> {
    user.require_permission("tps:work-center:manage")?;
    let family = ProductFamily {
        id: Uuid::new_v4(),
        tenant_id: user.tenant_id,
        site_id: req.site_id,
        name: req.name,
        description: req.description,
        is_active: true,
    };
    state
        .topology
        .put_product_family(&family)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(family))
}

pub async fn list_product_families(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<ProductFamily>>, SenseiError> {
    user.require_permission("tps:work-center:read")?;
    let families = state
        .topology
        .list_product_families(user.tenant_id)
        .await
        .map_err(SenseiError::Internal)?;
    Ok(Json(families))
}

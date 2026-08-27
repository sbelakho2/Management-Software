//! KPI (Key Performance Indicator) route handlers.
//!
//! Provides endpoints for managing KPI definitions, recording values,
//! and viewing trend dashboards.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{KpiCategory, KpiDefinition, KpiDirection, KpiValue};

/// Stable snake-case name for a [`KpiCategory`] variant.
///
/// Used for filter comparisons so `Quality` never matches `Quality` by
/// discriminant coincidence but by its serialized name.
fn category_as_str(category: &KpiCategory) -> &'static str {
    match category {
        KpiCategory::Quality => "quality",
        KpiCategory::Production => "production",
        KpiCategory::Maintenance => "maintenance",
        KpiCategory::Inventory => "inventory",
        KpiCategory::Safety => "safety",
        KpiCategory::Cost => "cost",
        KpiCategory::Delivery => "delivery",
        KpiCategory::People => "people",
    }
}

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing KPI definitions.
#[derive(Debug, Deserialize)]
pub struct ListKpisParams {
    pub category: Option<KpiCategory>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a KPI definition.
#[derive(Debug, Deserialize)]
pub struct CreateKpiRequest {
    pub name: String,
    pub description: Option<String>,
    pub category: KpiCategory,
    pub unit: String,
    pub target: Option<f64>,
    pub lower_limit: Option<f64>,
    pub upper_limit: Option<f64>,
    pub direction: KpiDirection,
    pub formula: Option<String>,
    pub owner_role: Option<String>,
}

/// Request body for updating a KPI definition (partial).
///
/// Optional fields use `Option<Option<T>>`: `None` leaves the current value
/// untouched, `Some(None)` clears it, and `Some(Some(v))` sets it.
#[derive(Debug, Deserialize)]
pub struct UpdateKpiRequest {
    pub name: Option<String>,
    pub description: Option<Option<String>>,
    pub category: Option<KpiCategory>,
    pub unit: Option<String>,
    pub target: Option<Option<f64>>,
    pub lower_limit: Option<Option<f64>>,
    pub upper_limit: Option<Option<f64>>,
    pub direction: Option<KpiDirection>,
    pub formula: Option<Option<String>>,
    pub owner_role: Option<Option<String>>,
    pub is_active: Option<bool>,
}

/// Request body for recording a KPI value.
#[derive(Debug, Deserialize)]
pub struct RecordKpiValueRequest {
    pub value: f64,
    pub recorded_at: Option<DateTime<Utc>>,
    pub note: Option<String>,
}

/// Query parameters for listing KPI values.
#[derive(Debug, Deserialize)]
pub struct ListKpiValuesParams {
    pub date_from: Option<DateTime<Utc>>,
    pub date_to: Option<DateTime<Utc>>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

// ── Response DTOs ──────────────────────────────────────────────────────────

/// KPI dashboard with trend analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiDashboard {
    pub kpi: KpiDefinition,
    pub latest_value: Option<f64>,
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
    pub avg_value: Option<f64>,
    pub total_records: usize,
    pub trend: Vec<SparklinePoint>,
}

/// A single data point for sparkline / trend chart.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SparklinePoint {
    pub recorded_at: DateTime<Utc>,
    pub value: f64,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List KPI definitions with optional filters and pagination.
pub async fn list_kpis(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListKpisParams>,
) -> Result<Json<PaginatedResponse<KpiDefinition>>> {
    user.require_permission("tps:kpi:read")?;
    let tenant_id = user.tenant_id;
    let store = state.kpi_definitions.read(user.tenant_id).await;
    let mut kpis: Vec<KpiDefinition> = store
        .values()
        .filter(|k| k.tenant_id == tenant_id)
        .filter(|k| {
            if let Some(ref cat) = params.category {
                category_as_str(cat) == category_as_str(&k.category)
            } else {
                true
            }
        })
        .filter(|k| {
            if let Some(active) = params.is_active {
                k.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    kpis.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(kpis, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new KPI definition.
pub async fn create_kpi(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateKpiRequest>,
) -> Result<Json<KpiDefinition>> {
    user.require_permission("tps:kpi:manage")?;
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let kpi = KpiDefinition {
        id: new_id(),
        tenant_id,
        name: req.name,
        description: req.description,
        category: req.category,
        unit: req.unit,
        target: req.target,
        lower_limit: req.lower_limit,
        upper_limit: req.upper_limit,
        direction: req.direction,
        formula: req.formula,
        owner_role: req.owner_role,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.kpi_definitions.write(user.tenant_id).await;
    store.insert(kpi.id, kpi.clone());
    Ok(Json(kpi))
}

/// Get a KPI definition by ID.
pub async fn get_kpi(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<KpiDefinition>> {
    user.require_permission("tps:kpi:read")?;
    let tenant_id = user.tenant_id;
    let store = state.kpi_definitions.read(user.tenant_id).await;
    let kpi = store
        .values()
        .find(|k| k.id == id && k.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("KPI {id} not found")))?;
    Ok(Json(kpi))
}

/// Update a KPI definition.
pub async fn update_kpi(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateKpiRequest>,
) -> Result<Json<KpiDefinition>> {
    user.require_permission("tps:kpi:manage")?;
    let tenant_id = user.tenant_id;
    let mut store = state.kpi_definitions.write(user.tenant_id).await;
    let kpi = store
        .get_mut(&id)
        .filter(|k| k.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("KPI {id} not found")))?;
    if let Some(name) = req.name {
        kpi.name = name;
    }
    if let Some(desc) = req.description {
        kpi.description = desc;
    }
    if let Some(cat) = req.category {
        kpi.category = cat;
    }
    if let Some(unit) = req.unit {
        kpi.unit = unit;
    }
    if let Some(target) = req.target {
        kpi.target = target;
    }
    if let Some(ll) = req.lower_limit {
        kpi.lower_limit = ll;
    }
    if let Some(ul) = req.upper_limit {
        kpi.upper_limit = ul;
    }
    if let Some(dir) = req.direction {
        kpi.direction = dir;
    }
    if let Some(formula) = req.formula {
        kpi.formula = formula;
    }
    if let Some(role) = req.owner_role {
        kpi.owner_role = role;
    }
    if let Some(active) = req.is_active {
        kpi.is_active = active;
    }
    kpi.updated_at = Utc::now();
    Ok(Json(kpi.clone()))
}

/// Delete a KPI definition.
pub async fn delete_kpi(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("tps:kpi:manage")?;
    let tenant_id = user.tenant_id;
    let mut store = state.kpi_definitions.write(user.tenant_id).await;
    let exists = store
        .get(&id)
        .filter(|k| k.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("KPI {id} not found")));
    }
    store.remove(&id);
    Ok(Json(()))
}

/// Record a KPI value for a given KPI definition.
pub async fn record_kpi_value(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(kpi_id): Path<Uuid>,
    Json(req): Json<RecordKpiValueRequest>,
) -> Result<Json<KpiValue>> {
    user.require_permission("tps:kpi:manage")?;
    let tenant_id = user.tenant_id;
    // Verify KPI exists
    {
        let store = state.kpi_definitions.read(user.tenant_id).await;
        if !store
            .values()
            .any(|k| k.id == kpi_id && k.tenant_id == tenant_id)
        {
            return Err(SenseiError::NotFound(format!("KPI {kpi_id} not found")));
        }
    }
    let now = Utc::now();
    let value = KpiValue {
        id: new_id(),
        kpi_id,
        tenant_id,
        value: req.value,
        recorded_at: req.recorded_at.unwrap_or(now),
        note: req.note,
        recorded_by: user.user_id,
    };
    let mut store = state.kpi_values.write(user.tenant_id).await;
    store.insert(value.id, value.clone());
    Ok(Json(value))
}

/// List KPI values for a given KPI, filtered by date range.
pub async fn list_kpi_values(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(kpi_id): Path<Uuid>,
    Query(params): Query<ListKpiValuesParams>,
) -> Result<Json<PaginatedResponse<KpiValue>>> {
    user.require_permission("tps:kpi:read")?;
    let tenant_id = user.tenant_id;
    let store = state.kpi_values.read(user.tenant_id).await;
    let mut values: Vec<KpiValue> = store
        .values()
        .filter(|v| v.kpi_id == kpi_id && v.tenant_id == tenant_id)
        .filter(|v| {
            if let Some(from) = &params.date_from {
                v.recorded_at >= *from
            } else {
                true
            }
        })
        .filter(|v| {
            if let Some(to) = &params.date_to {
                v.recorded_at <= *to
            } else {
                true
            }
        })
        .cloned()
        .collect();
    values.sort_by_key(|a| std::cmp::Reverse(a.recorded_at));
    let result = PaginatedResponse::new(values, params.page, params.per_page);
    Ok(Json(result))
}

/// Get KPI dashboard with trend analysis (min/max/avg/latest values, sparkline).
pub async fn get_kpi_dashboard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(kpi_id): Path<Uuid>,
) -> Result<Json<KpiDashboard>> {
    user.require_permission("tps:kpi:read")?;
    let tenant_id = user.tenant_id;
    let kpi = {
        let store = state.kpi_definitions.read(user.tenant_id).await;
        store
            .values()
            .find(|k| k.id == kpi_id && k.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("KPI {kpi_id} not found")))?
    };

    let values_store = state.kpi_values.read(user.tenant_id).await;
    let values: Vec<&KpiValue> = values_store
        .values()
        .filter(|v| v.kpi_id == kpi_id && v.tenant_id == tenant_id)
        .collect();

    let total_records = values.len();
    let latest_value = values.iter().max_by_key(|v| v.recorded_at).map(|v| v.value);
    let min_value = values.iter().map(|v| v.value).reduce(f64::min);
    let max_value = values.iter().map(|v| v.value).reduce(f64::max);
    let avg_value = if !values.is_empty() {
        Some(values.iter().map(|v| v.value).sum::<f64>() / values.len() as f64)
    } else {
        None
    };

    let mut trend: Vec<SparklinePoint> = values
        .iter()
        .map(|v| SparklinePoint {
            recorded_at: v.recorded_at,
            value: v.value,
        })
        .collect();
    trend.sort_by_key(|a| a.recorded_at);

    let dashboard = KpiDashboard {
        kpi,
        latest_value,
        min_value,
        max_value,
        avg_value,
        total_records,
        trend,
    };
    Ok(Json(dashboard))
}

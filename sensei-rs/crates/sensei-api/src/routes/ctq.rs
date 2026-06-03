//! CTQ (Critical-To-Quality) route handlers.
//!
//! Provides endpoints for defining Critical-To-Quality characteristics,
//! recording measurements, tracking conformance, and analyzing quality
//! performance against specification limits.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{CtqCharacteristic, CtqCharacteristicStore, CtqRecord, CtqRecordStore};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing CTQ characteristics.
#[derive(Debug, Deserialize)]
pub struct ListCharacteristicsParams {
    pub category: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating a CTQ characteristic.
#[derive(Debug, Deserialize)]
pub struct CreateCharacteristicRequest {
    pub name: String,
    pub description: Option<String>,
    pub category: String,
    pub specification_limit_lower: Option<f64>,
    pub specification_limit_upper: Option<f64>,
    pub target_value: Option<f64>,
    pub unit: Option<String>,
    pub measurement_method: String,
}

/// Request body for updating a CTQ characteristic.
#[derive(Debug, Deserialize)]
pub struct UpdateCharacteristicRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub specification_limit_lower: Option<f64>,
    pub specification_limit_upper: Option<f64>,
    pub target_value: Option<f64>,
    pub unit: Option<String>,
    pub measurement_method: Option<String>,
    pub is_active: Option<bool>,
}

/// Query parameters for listing CTQ records (measurements).
#[derive(Debug, Deserialize)]
pub struct ListRecordsParams {
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub work_order_id: Option<Uuid>,
    pub lot_id: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for recording a CTQ measurement.
#[derive(Debug, Deserialize)]
pub struct CreateRecordRequest {
    pub value: f64,
    pub recorded_at: Option<String>,
    pub work_order_id: Option<Uuid>,
    pub lot_id: Option<String>,
    pub notes: Option<String>,
}

/// CTQ conformance analysis for a characteristic.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConformanceAnalysis {
    pub characteristic_id: Uuid,
    pub characteristic_name: String,
    pub total_measurements: usize,
    pub conforming_count: usize,
    pub non_conforming_count: usize,
    pub conformance_rate: f64,
    pub mean: f64,
    pub std_dev: f64,
    pub min: f64,
    pub max: f64,
    pub cp: f64,
    pub cpk: f64,
}

// ── Helpers ────────────────────────────────────────────────────────────────

fn get_char_store(state: &AppState) -> &CtqCharacteristicStore {
    &state.ctq_characteristics
}

fn get_record_store(state: &AppState) -> &CtqRecordStore {
    &state.ctq_records
}

fn parse_dt(s: Option<&str>) -> Option<DateTime<Utc>> {
    s.and_then(|s| s.parse::<DateTime<Utc>>().ok())
}

/// Compute basic statistics for a set of values.
fn compute_stats(values: &[f64]) -> (f64, f64, f64, f64) {
    let n = values.len() as f64;
    if n == 0.0 {
        return (0.0, 0.0, 0.0, 0.0);
    }
    let sum: f64 = values.iter().sum();
    let mean = sum / n;
    let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
    let std_dev = variance.sqrt();
    let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    (mean, std_dev, min, max)
}

// ── Characteristic Handlers ────────────────────────────────────────────────

/// List all CTQ characteristics with optional filters.
pub async fn list_characteristics(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListCharacteristicsParams>,
) -> Result<Json<PaginatedResponse<CtqCharacteristic>>> {
    let tenant_id = user.tenant_id;
    let store = get_char_store(&state);
    let map = store.read().await;

    let mut items: Vec<CtqCharacteristic> = map
        .values()
        .filter(|c| c.tenant_id == tenant_id)
        .filter(|c| match &params.category {
            Some(cat) => c.category == *cat,
            None => true,
        })
        .filter(|c| match params.is_active {
            Some(active) => c.is_active == active,
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

/// Get a specific CTQ characteristic by ID.
pub async fn get_characteristic(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<CtqCharacteristic>> {
    let tenant_id = user.tenant_id;
    let store = get_char_store(&state);
    let map = store.read().await;

    let char = map
        .get(&id)
        .filter(|c| c.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?
        .clone();

    Ok(Json(char))
}

/// Create a new CTQ characteristic definition.
pub async fn create_characteristic(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateCharacteristicRequest>,
) -> Result<Json<CtqCharacteristic>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let char = CtqCharacteristic {
        id: Uuid::new_v4(),
        tenant_id,
        name: req.name,
        description: req.description.unwrap_or_default(),
        category: req.category,
        specification_limit_lower: req.specification_limit_lower,
        specification_limit_upper: req.specification_limit_upper,
        target_value: req.target_value,
        unit: req.unit,
        measurement_method: req.measurement_method,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };

    get_char_store(&state).write().await.insert(char.id, char.clone());
    Ok(Json(char))
}

/// Update a CTQ characteristic.
pub async fn update_characteristic(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateCharacteristicRequest>,
) -> Result<Json<CtqCharacteristic>> {
    let tenant_id = user.tenant_id;
    let store = get_char_store(&state);
    let mut map = store.write().await;

    let char = map
        .get_mut(&id)
        .filter(|c| c.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(id.to_string()))?;

    if let Some(name) = req.name {
        char.name = name;
    }
    if let Some(description) = req.description {
        char.description = description;
    }
    if let Some(category) = req.category {
        char.category = category;
    }
    if let Some(lsl) = req.specification_limit_lower {
        char.specification_limit_lower = Some(lsl);
    }
    if let Some(usl) = req.specification_limit_upper {
        char.specification_limit_upper = Some(usl);
    }
    if let Some(target) = req.target_value {
        char.target_value = Some(target);
    }
    if let Some(unit) = req.unit {
        char.unit = Some(unit);
    }
    if let Some(method) = req.measurement_method {
        char.measurement_method = method;
    }
    if let Some(is_active) = req.is_active {
        char.is_active = is_active;
    }
    char.updated_at = Utc::now();

    Ok(Json(char.clone()))
}

// ── Record (Measurement) Handlers ──────────────────────────────────────────

/// List measurement records for a specific CTQ characteristic.
pub async fn list_records(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(characteristic_id): Path<Uuid>,
    Query(params): Query<ListRecordsParams>,
) -> Result<Json<PaginatedResponse<CtqRecord>>> {
    let tenant_id = user.tenant_id;
    let store = get_record_store(&state);
    let map = store.read().await;

    let mut items: Vec<CtqRecord> = map
        .values()
        .filter(|r| r.characteristic_id == characteristic_id && r.tenant_id == tenant_id)
        .filter(|r| match &params.work_order_id {
            Some(wo_id) => r.work_order_id == Some(*wo_id),
            None => true,
        })
        .filter(|r| match &params.lot_id {
            Some(lot) => r.lot_id.as_deref() == Some(lot.as_str()),
            None => true,
        })
        .filter(|r| match &params.date_from {
            Some(from) => parse_dt(Some(from)).map_or(true, |d| r.recorded_at >= d),
            None => true,
        })
        .filter(|r| match &params.date_to {
            Some(to) => parse_dt(Some(to)).map_or(true, |d| r.recorded_at <= d),
            None => true,
        })
        .cloned()
        .collect();

    items.sort_by(|a, b| b.recorded_at.cmp(&a.recorded_at));
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

/// Record a new CTQ measurement.
pub async fn create_record(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(characteristic_id): Path<Uuid>,
    Json(req): Json<CreateRecordRequest>,
) -> Result<Json<CtqRecord>> {
    let tenant_id = user.tenant_id;

    // Verify the characteristic exists
    let char_store = get_char_store(&state);
    let char_map = char_store.read().await;
    let characteristic = char_map
        .get(&characteristic_id)
        .filter(|c| c.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(characteristic_id.to_string()))?
        .clone();
    drop(char_map);

    let recorded_at = parse_dt(req.recorded_at.as_deref()).unwrap_or_else(Utc::now);

    // Determine conformance based on specification limits
    let is_conforming = match (characteristic.specification_limit_lower, characteristic.specification_limit_upper) {
        (Some(lsl), Some(usl)) => req.value >= lsl && req.value <= usl,
        (Some(lsl), None) => req.value >= lsl,
        (None, Some(usl)) => req.value <= usl,
        (None, None) => true,
    };

    let record = CtqRecord {
        id: Uuid::new_v4(),
        characteristic_id,
        tenant_id,
        value: req.value,
        recorded_at,
        recorded_by: Some(user.user_id),
        work_order_id: req.work_order_id,
        lot_id: req.lot_id,
        is_conforming,
        notes: req.notes,
    };

    get_record_store(&state)
        .write()
        .await
        .insert(record.id, record.clone());

    Ok(Json(record))
}

/// Get conformance analysis for a CTQ characteristic.
pub async fn get_conformance_analysis(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(characteristic_id): Path<Uuid>,
) -> Result<Json<ConformanceAnalysis>> {
    let tenant_id = user.tenant_id;

    // Get the characteristic
    let char_store = get_char_store(&state);
    let char_map = char_store.read().await;
    let characteristic = char_map
        .get(&characteristic_id)
        .filter(|c| c.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(characteristic_id.to_string()))?
        .clone();
    drop(char_map);

    // Get all records for this characteristic
    let record_store = get_record_store(&state);
    let rec_map = record_store.read().await;
    let records: Vec<&CtqRecord> = rec_map
        .values()
        .filter(|r| r.characteristic_id == characteristic_id && r.tenant_id == tenant_id)
        .collect();

    let total_measurements = records.len();
    let conforming_count = records.iter().filter(|r| r.is_conforming).count();
    let non_conforming_count = total_measurements - conforming_count;
    let conformance_rate = if total_measurements > 0 {
        (conforming_count as f64 / total_measurements as f64) * 100.0
    } else {
        100.0
    };

    let values: Vec<f64> = records.iter().map(|r| r.value).collect();
    let (mean, std_dev, min, max) = compute_stats(&values);

    // Calculate Cp and Cpk
    let cp = match (characteristic.specification_limit_lower, characteristic.specification_limit_upper) {
        (Some(lsl), Some(usl)) if std_dev > 0.0 => (usl - lsl) / (6.0 * std_dev),
        _ => 0.0,
    };

    let cpk = match (characteristic.specification_limit_lower, characteristic.specification_limit_upper) {
        (Some(lsl), Some(usl)) if std_dev > 0.0 => {
            let cpu = (usl - mean) / (3.0 * std_dev);
            let cpl = (mean - lsl) / (3.0 * std_dev);
            cpu.min(cpl).max(0.0)
        }
        (Some(lsl), None) if std_dev > 0.0 => ((mean - lsl) / (3.0 * std_dev)).max(0.0),
        (None, Some(usl)) if std_dev > 0.0 => ((usl - mean) / (3.0 * std_dev)).max(0.0),
        _ => 0.0,
    };

    Ok(Json(ConformanceAnalysis {
        characteristic_id,
        characteristic_name: characteristic.name,
        total_measurements,
        conforming_count,
        non_conforming_count,
        conformance_rate,
        mean,
        std_dev,
        min,
        max,
        cp,
        cpk,
    }))
}

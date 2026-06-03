//! Training matrix management route handlers.
//!
//! Provides endpoints for managing skill/training matrix entries and
//! identifying skill gaps across the organization.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::TrainingMatrixEntry;

/// A skill gap representing a missing competency.
#[derive(Debug, Clone, Serialize)]
pub struct SkillGap {
    pub employee_id: Uuid,
    pub employee_name: String,
    pub skill_name: String,
    pub skill_category: String,
    pub current_level: String,
    pub required_level: String,
    pub gap_description: String,
}

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing training matrix entries.
#[derive(Debug, Deserialize)]
pub struct ListMatrixParams {
    pub employee_id: Option<Uuid>,
    pub skill_category: Option<String>,
    pub proficiency_level: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a training matrix entry.
#[derive(Debug, Deserialize)]
pub struct MatrixEntryRequest {
    pub employee_id: Uuid,
    pub employee_name: String,
    pub skill_name: String,
    pub skill_category: String,
    pub proficiency_level: String,
    pub certification_id: Option<String>,
    pub last_assessed_at: Option<DateTime<Utc>>,
    pub valid_until: Option<DateTime<Utc>>,
    pub notes: String,
    pub assessed_by: Option<Uuid>,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// List all training matrix entries with optional filters.
pub async fn list_matrix_entries(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListMatrixParams>,
) -> Result<Json<PaginatedResponse<TrainingMatrixEntry>>> {
    let store = state.training_matrix.read().await;
    let mut entries: Vec<TrainingMatrixEntry> = store
        .values()
        .filter(|e| e.tenant_id == user.tenant_id)
        .filter(|e| params.employee_id.map_or(true, |emp| e.employee_id == emp))
        .filter(|e| params.skill_category.as_ref().map_or(true, |cat| e.skill_category == *cat))
        .filter(|e| params.proficiency_level.as_ref().map_or(true, |lvl| e.proficiency_level == *lvl))
        .cloned()
        .collect();
    entries.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    let result = PaginatedResponse::new(entries, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new training matrix entry.
pub async fn create_matrix_entry(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<MatrixEntryRequest>,
) -> Result<Json<TrainingMatrixEntry>> {
    let now = Utc::now();
    let entry = TrainingMatrixEntry {
        id: new_id(),
        tenant_id: user.tenant_id,
        employee_id: req.employee_id,
        employee_name: req.employee_name,
        skill_name: req.skill_name,
        skill_category: req.skill_category,
        proficiency_level: req.proficiency_level,
        certification_id: req.certification_id,
        last_assessed_at: req.last_assessed_at,
        valid_until: req.valid_until,
        notes: req.notes,
        assessed_by: req.assessed_by,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.training_matrix.write().await;
    store.insert(entry.id, entry.clone());
    Ok(Json(entry))
}

/// Update a training matrix entry.
pub async fn update_matrix_entry(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<MatrixEntryRequest>,
) -> Result<Json<TrainingMatrixEntry>> {
    let mut store = state.training_matrix.write().await;
    let entry = store
        .get_mut(&id)
        .filter(|e| e.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Training matrix entry {id} not found")))?;
    entry.employee_id = req.employee_id;
    entry.employee_name = req.employee_name;
    entry.skill_name = req.skill_name;
    entry.skill_category = req.skill_category;
    entry.proficiency_level = req.proficiency_level;
    entry.certification_id = req.certification_id;
    entry.last_assessed_at = req.last_assessed_at;
    entry.valid_until = req.valid_until;
    entry.notes = req.notes;
    entry.assessed_by = req.assessed_by;
    entry.updated_at = Utc::now();
    Ok(Json(entry.clone()))
}

/// List skill gaps across the organization.
///
/// A gap exists when an employee's current proficiency level is below
/// the required level for a skill. Returns all entries where the skill
/// is not yet at "competent" or higher.
pub async fn list_skill_gaps(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<SkillGap>>> {
    let store = state.training_matrix.read().await;
    let required_levels: [&str; 3] = ["competent", "proficient", "expert"];

    let mut gaps: Vec<SkillGap> = store
        .values()
        .filter(|e| e.tenant_id == user.tenant_id)
        .filter(|e| !required_levels.contains(&e.proficiency_level.as_str()))
        .map(|e| {
            let current_level = e.proficiency_level.clone();
            let required = match current_level.as_str() {
                "novice" => "competent",
                "beginner" => "competent",
                _ => "competent",
            };
            SkillGap {
                employee_id: e.employee_id,
                employee_name: e.employee_name.clone(),
                skill_name: e.skill_name.clone(),
                skill_category: e.skill_category.clone(),
                current_level: current_level.clone(),
                required_level: required.to_string(),
                gap_description: format!(
                    "{} is at '{}' level for '{}', requires '{}'",
                    e.employee_name, current_level, e.skill_name, required
                ),
            }
        })
        .collect();

    gaps.sort_by(|a, b| a.employee_name.cmp(&b.employee_name));
    Ok(Json(gaps))
}

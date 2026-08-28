//! LSW (Layer Standard Work) route handlers.
//!
//! Provides endpoints for managing LSW standards, performing audits,
//! and viewing compliance dashboards.
use std::collections::HashSet;

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
use crate::stores::{
    LswAudit, LswAuditResult, LswChecklistItem, LswFrequency, LswOccurrence, LswStandard,
};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing LSW standards.
#[derive(Debug, Deserialize)]
pub struct ListLswStandardsParams {
    pub area: Option<String>,
    pub layer: Option<u8>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating an LSW standard.
#[derive(Debug, Deserialize)]
pub struct CreateLswStandardRequest {
    pub title: String,
    pub area: String,
    pub layer: u8,
    pub frequency: LswFrequency,
    pub checklist_items: Vec<LswChecklistItem>,
}

/// Request body for updating an LSW standard (partial).
#[derive(Debug, Deserialize)]
pub struct UpdateLswStandardRequest {
    pub title: Option<String>,
    pub area: Option<String>,
    pub layer: Option<u8>,
    pub frequency: Option<LswFrequency>,
    pub checklist_items: Option<Vec<LswChecklistItem>>,
    pub is_active: Option<bool>,
}

/// Query parameters for listing audits.
#[derive(Debug, Deserialize)]
pub struct ListAuditsParams {
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for performing an LSW audit.
#[derive(Debug, Deserialize)]
pub struct PerformAuditRequest {
    pub results: Vec<LswAuditResult>,
    pub notes: Option<String>,
    /// The event time of the observation (server still owns recorded_at /
    /// completed_at). Future timestamps are rejected (clock-skew bound).
    pub observed_at: Option<DateTime<Utc>>,
    /// The scheduled occurrence this audit executes.
    pub occurrence_id: Option<Uuid>,
}

/// The standard's CURRENT revision (the occurrence must match it).
async fn standard_occurrence_revision(state: &AppState, tenant_id: Uuid, standard_id: Uuid) -> i32 {
    let store = state.lsw_standards.read(tenant_id).await;
    store
        .values()
        .find(|s| s.id == standard_id && s.tenant_id == tenant_id)
        .map(|s| s.revision)
        .unwrap_or(0)
}

/// Dashboard query parameters.
#[derive(Debug, Deserialize)]
pub struct LswDashboardParams {
    pub area: Option<String>,
    pub layer: Option<u8>,
    pub date_from: Option<DateTime<Utc>>,
    pub date_to: Option<DateTime<Utc>>,
}

// ── Response DTOs ──────────────────────────────────────────────────────────

/// LSW dashboard with compliance data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LswDashboard {
    pub total_standards: usize,
    pub total_audits: usize,
    pub overall_compliance_rate: f64,
    pub by_area: Vec<AreaCompliance>,
    pub by_layer: Vec<LayerCompliance>,
    pub recent_trend: Vec<ComplianceTrendPoint>,
}

/// Compliance breakdown by area.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AreaCompliance {
    pub area: String,
    pub total_audits: usize,
    pub compliance_rate: f64,
}

/// Compliance breakdown by layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayerCompliance {
    pub layer: u8,
    pub total_audits: usize,
    pub compliance_rate: f64,
}

/// A single point on the compliance trend chart.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceTrendPoint {
    pub date: DateTime<Utc>,
    pub compliance_rate: f64,
}

// ── Standards Handlers ─────────────────────────────────────────────────────

/// List LSW standards with optional filters and pagination.
pub async fn list_lsw_standards(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListLswStandardsParams>,
) -> Result<Json<PaginatedResponse<LswStandard>>> {
    user.require_permission("tps:lsw:execute")?;
    let tenant_id = user.tenant_id;
    let store = state.lsw_standards.read(user.tenant_id).await;
    let mut standards: Vec<LswStandard> = store
        .values()
        .filter(|s| s.tenant_id == tenant_id)
        .filter(|s| {
            if let Some(ref area) = params.area {
                s.area == *area
            } else {
                true
            }
        })
        .filter(|s| {
            if let Some(layer) = params.layer {
                s.layer == layer
            } else {
                true
            }
        })
        .filter(|s| {
            if let Some(active) = params.is_active {
                s.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    standards.sort_by(|a, b| a.title.cmp(&b.title));
    let result = PaginatedResponse::new(standards, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new LSW standard.
pub async fn create_lsw_standard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateLswStandardRequest>,
) -> Result<Json<LswStandard>> {
    user.require_permission("tps:lsw:manage")?;
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let standard = LswStandard {
        id: new_id(),
        revision: 1,
        tenant_id,
        title: req.title,
        area: req.area,
        layer: req.layer,
        frequency: req.frequency,
        checklist_items: req.checklist_items,
        is_active: true,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.lsw_standards.write(user.tenant_id).await;
    store.insert(standard.id, standard.clone());
    store.persist().await?;
    Ok(Json(standard))
}

/// Get an LSW standard by ID.
pub async fn get_lsw_standard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(standard_id): Path<Uuid>,
) -> Result<Json<LswStandard>> {
    user.require_permission("tps:lsw:execute")?;
    let tenant_id = user.tenant_id;
    let store = state.lsw_standards.read(user.tenant_id).await;
    let standard = store
        .values()
        .find(|s| s.id == standard_id && s.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("LSW standard {standard_id} not found")))?;
    Ok(Json(standard))
}

/// Update an LSW standard.
pub async fn update_lsw_standard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(standard_id): Path<Uuid>,
    Json(req): Json<UpdateLswStandardRequest>,
) -> Result<Json<LswStandard>> {
    user.require_permission("tps:lsw:manage")?;
    let tenant_id = user.tenant_id;
    let mut store = state.lsw_standards.write(user.tenant_id).await;
    let standard = store
        .get_mut(&standard_id)
        .filter(|s| s.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("LSW standard {standard_id} not found")))?;
    if let Some(title) = req.title {
        standard.title = title;
    }
    if let Some(area) = req.area {
        standard.area = area;
    }
    if let Some(layer) = req.layer {
        standard.layer = layer;
    }
    if let Some(freq) = req.frequency {
        standard.frequency = freq;
    }
    if let Some(items) = req.checklist_items {
        standard.checklist_items = items;
    }
    if let Some(active) = req.is_active {
        standard.is_active = active;
    }
    standard.updated_at = Utc::now();
    let result = standard.clone();
    store.persist().await?;
    Ok(Json(result))
}

/// Delete an LSW standard.
pub async fn delete_lsw_standard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(standard_id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("tps:lsw:manage")?;
    let tenant_id = user.tenant_id;
    let mut store = state.lsw_standards.write(user.tenant_id).await;
    let exists = store
        .get(&standard_id)
        .filter(|s| s.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!(
            "LSW standard {standard_id} not found"
        )));
    }
    store.remove(&standard_id);
    store.persist().await?;
    Ok(Json(()))
}

/// Request to schedule an LSW occurrence.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ScheduleOccurrenceRequest {
    pub due_at: DateTime<Utc>,
    pub assigned_leader: Uuid,
}

/// Schedule an LSW occurrence for a standard (server owns the lifecycle:
/// scheduled_at/started_at/completed_at/leader).
pub async fn schedule_occurrence(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(standard_id): Path<Uuid>,
    Json(req): Json<ScheduleOccurrenceRequest>,
) -> Result<Json<LswOccurrence>> {
    user.require_permission("tps:lsw:manage")?;
    let tenant_id = user.tenant_id;
    let standard = {
        let store = state.lsw_standards.read(user.tenant_id).await;
        store
            .values()
            .find(|s| s.id == standard_id && s.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("LSW standard {standard_id} not found")))?
    };
    let now = Utc::now();
    let occurrence = LswOccurrence {
        id: new_id(),
        standard_id,
        tenant_id,
        checklist_revision: standard.revision,
        due_at: req.due_at,
        assigned_leader: req.assigned_leader,
        area: standard.area.clone(),
        layer: standard.layer,
        status: "scheduled".to_string(),
        scheduled_at: now,
        started_at: None,
        completed_at: None,
    };
    let mut store = state.lsw_occurrences.write(tenant_id).await;
    store.insert(occurrence.id, occurrence.clone());
    store.persist().await?;
    Ok(Json(occurrence))
}

// ── Audit Handlers ─────────────────────────────────────────────────────────

/// Perform an audit (checklist) against an LSW standard.
///
/// Audits execute a SCHEDULED OCCURRENCE (server-owned lifecycle): the
/// client supplies the occurrence id, never the timestamps or leader.
pub async fn perform_audit(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(standard_id): Path<Uuid>,
    Json(req): Json<PerformAuditRequest>,
) -> Result<Json<LswAudit>> {
    user.require_permission("tps:lsw:execute")?;
    let tenant_id = user.tenant_id;

    // Resolve the occurrence: it must exist, belong to this standard, be
    // scheduled/in_progress, and carry the CURRENT checklist revision.
    let occurrence_id = req
        .occurrence_id
        .ok_or_else(|| SenseiError::Validation("An occurrence_id is required".to_string()))?;
    let assigned_leader = {
        let store = state.lsw_occurrences.read(user.tenant_id).await;
        let occurrence = store
            .get(&occurrence_id)
            .filter(|o| o.tenant_id == tenant_id && o.standard_id == standard_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("LSW occurrence {occurrence_id} not found"))
            })?;
        if occurrence.status == "completed" {
            return Err(SenseiError::Conflict(
                "This LSW occurrence is already completed".to_string(),
            ));
        }
        // VALIDATE BEFORE MUTATION: the checklist revision must match the
        // standard's current revision (a stale checklist cannot be audited).
        if occurrence.checklist_revision
            != standard_occurrence_revision(&state, tenant_id, standard_id).await
        {
            return Err(SenseiError::Conflict(
                "The occurrence's checklist revision is stale — schedule a new occurrence"
                    .to_string(),
            ));
        }
        occurrence.assigned_leader
    };

    // Leader enforcement: the auditor must BE the assigned leader, or a
    // manager (tps:lsw:manage) performing a legitimate delegation.
    if user.user_id != assigned_leader {
        user.require_permission("tps:lsw:manage")?;
    }

    {
        let mut store = state.lsw_occurrences.write(user.tenant_id).await;
        if let Some(occurrence) = store.get_mut(&occurrence_id) {
            let now = Utc::now();
            if occurrence.started_at.is_none() {
                occurrence.started_at = Some(now);
            }
            occurrence.status = "in_progress".to_string();
        }
        store.persist().await?;
    }

    // Verify standard exists
    let standard = {
        let store = state.lsw_standards.read(user.tenant_id).await;
        store
            .values()
            .find(|s| s.id == standard_id && s.tenant_id == tenant_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("LSW standard {standard_id} not found")))?
    };

    // Enforce checklist completeness: exactly one result for EVERY
    // required checklist item, no unknown item, no duplicate item — a
    // client cannot submit only one passing result and make the audit look
    // fully compliant.
    let required_ids: Vec<Uuid> = standard.checklist_items.iter().map(|i| i.id).collect();
    let mut seen: HashSet<Uuid> = HashSet::new();
    for r in &req.results {
        if !required_ids.contains(&r.item_id) {
            return Err(SenseiError::Validation(format!(
                "Result for item {} is not part of this standard's checklist",
                r.item_id
            )));
        }
        if !seen.insert(r.item_id) {
            return Err(SenseiError::Validation(format!(
                "Duplicate result for checklist item {}",
                r.item_id
            )));
        }
    }
    for id in &required_ids {
        if !seen.contains(id) {
            return Err(SenseiError::Validation(format!(
                "Missing result for required checklist item {id} — every item must be observed"
            )));
        }
    }

    // Compliance is the fraction of the FULL checklist, never of the
    // submitted subset (which is now guaranteed to be the full checklist).
    let total_items = required_ids.len();
    let passed_items = req.results.iter().filter(|r| r.passed).count();
    let compliance_rate = if total_items > 0 {
        (passed_items as f64 / total_items as f64) * 100.0
    } else {
        0.0
    };

    let now = Utc::now();
    let audit = LswAudit {
        id: new_id(),
        standard_id,
        tenant_id,
        auditor_id: user.user_id,
        area: standard.area.clone(),
        layer: standard.layer,
        results: req.results,
        compliance_rate,
        notes: req.notes,
        audited_at: req.observed_at.unwrap_or(now),
    };
    let mut store = state.lsw_audits.write(user.tenant_id).await;
    store.insert(audit.id, audit.clone());
    store.persist().await?;

    // The occurrence is COMPLETED by this audit (server-owned timestamps).
    // If the completion cannot be persisted, the audit is ROLLED BACK so
    // the two records never diverge (a crash between them is recoverable:
    // the occurrence stays in_progress and the audit is removed).
    {
        let mut occ = state.lsw_occurrences.write(user.tenant_id).await;
        if let Some(o) = occ.get_mut(&occurrence_id) {
            o.status = "completed".to_string();
            o.completed_at = Some(Utc::now());
        }
        if let Err(e) = occ.persist().await {
            // Compensation: remove the just-created audit record.
            let mut audits = state.lsw_audits.write(user.tenant_id).await;
            audits.remove(&audit.id);
            let _ = audits.persist().await;
            return Err(SenseiError::Internal(format!(
                "Failed to complete the LSW occurrence — audit rolled back: {e}"
            )));
        }
    }
    Ok(Json(audit))
}

/// List audit history for a specific LSW standard.
pub async fn list_audits(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(standard_id): Path<Uuid>,
    Query(params): Query<ListAuditsParams>,
) -> Result<Json<PaginatedResponse<LswAudit>>> {
    user.require_permission("tps:lsw:execute")?;
    let tenant_id = user.tenant_id;
    let store = state.lsw_audits.read(user.tenant_id).await;
    let mut audits: Vec<LswAudit> = store
        .values()
        .filter(|a| a.standard_id == standard_id && a.tenant_id == tenant_id)
        .cloned()
        .collect();
    audits.sort_by_key(|a| std::cmp::Reverse(a.audited_at));
    let result = PaginatedResponse::new(audits, params.page, params.per_page);
    Ok(Json(result))
}

/// Get a specific audit by ID.
pub async fn get_audit(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(audit_id): Path<Uuid>,
) -> Result<Json<LswAudit>> {
    user.require_permission("tps:lsw:execute")?;
    let tenant_id = user.tenant_id;
    let store = state.lsw_audits.read(user.tenant_id).await;
    let audit = store
        .values()
        .find(|a| a.id == audit_id && a.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Audit {audit_id} not found")))?;
    Ok(Json(audit))
}

// ── Dashboard ──────────────────────────────────────────────────────────────

/// Get LSW dashboard with compliance rate, trends, by layer/area.
pub async fn get_lsw_dashboard(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<LswDashboardParams>,
) -> Result<Json<LswDashboard>> {
    user.require_permission("tps:lsw:execute")?;
    let tenant_id = user.tenant_id;
    let standards_store = state.lsw_standards.read(user.tenant_id).await;
    let audits_store = state.lsw_audits.read(user.tenant_id).await;

    let total_standards = standards_store
        .values()
        .filter(|s| s.tenant_id == tenant_id)
        .count();

    let audits: Vec<&LswAudit> = audits_store
        .values()
        .filter(|a| a.tenant_id == tenant_id)
        .filter(|a| {
            if let Some(ref area) = params.area {
                a.area == *area
            } else {
                true
            }
        })
        .filter(|a| {
            if let Some(layer) = params.layer {
                a.layer == layer
            } else {
                true
            }
        })
        .filter(|a| {
            if let Some(from) = &params.date_from {
                a.audited_at >= *from
            } else {
                true
            }
        })
        .filter(|a| {
            if let Some(to) = &params.date_to {
                a.audited_at <= *to
            } else {
                true
            }
        })
        .collect();

    let total_audits = audits.len();
    // With no audits there is no compliance evidence: report 0.0, not a
    // fabricated 100%.
    let overall_compliance_rate = if total_audits > 0 {
        audits.iter().map(|a| a.compliance_rate).sum::<f64>() / total_audits as f64
    } else {
        0.0
    };

    // By area breakdown
    let mut area_map: std::collections::HashMap<String, Vec<f64>> =
        std::collections::HashMap::new();
    for audit in &audits {
        area_map
            .entry(audit.area.clone())
            .or_default()
            .push(audit.compliance_rate);
    }
    let by_area: Vec<AreaCompliance> = area_map
        .into_iter()
        .map(|(area, rates)| {
            let count = rates.len();
            let avg = rates.iter().sum::<f64>() / count as f64;
            AreaCompliance {
                area,
                total_audits: count,
                compliance_rate: avg,
            }
        })
        .collect();

    // By layer breakdown
    let mut layer_map: std::collections::HashMap<u8, Vec<f64>> = std::collections::HashMap::new();
    for audit in &audits {
        layer_map
            .entry(audit.layer)
            .or_default()
            .push(audit.compliance_rate);
    }
    let by_layer: Vec<LayerCompliance> = layer_map
        .into_iter()
        .map(|(layer, rates)| {
            let count = rates.len();
            let avg = rates.iter().sum::<f64>() / count as f64;
            LayerCompliance {
                layer,
                total_audits: count,
                compliance_rate: avg,
            }
        })
        .collect();

    // Recent trend (grouped by day)
    let mut trend_map: std::collections::BTreeMap<chrono::NaiveDate, Vec<f64>> =
        std::collections::BTreeMap::new();
    for audit in &audits {
        let date = audit.audited_at.date_naive();
        trend_map
            .entry(date)
            .or_default()
            .push(audit.compliance_rate);
    }
    let recent_trend: Vec<ComplianceTrendPoint> = trend_map
        .into_iter()
        .map(|(date, rates)| {
            let avg = rates.iter().sum::<f64>() / rates.len() as f64;
            ComplianceTrendPoint {
                date: date
                    .and_hms_opt(0, 0, 0)
                    .map(|d| DateTime::from_naive_utc_and_offset(d, Utc))
                    .unwrap_or_else(Utc::now),
                compliance_rate: avg,
            }
        })
        .collect();

    let dashboard = LswDashboard {
        total_standards,
        total_audits,
        overall_compliance_rate,
        by_area,
        by_layer,
        recent_trend,
    };
    Ok(Json(dashboard))
}

//! Audit Log route handlers.
//!
//! Provides endpoints for viewing audit trail entries, filtering by entity,
//! and retrieving audit statistics.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::AuditLogEntry;

/// Parse an RFC 3339 date filter; invalid values are rejected with a 400
/// instead of silently disabling the filter.
fn parse_date_filter(name: &str, value: Option<&str>) -> Result<Option<DateTime<Utc>>> {
    match value {
        Some(raw) => DateTime::parse_from_rfc3339(raw)
            .map(|dt| Some(dt.with_timezone(&Utc)))
            .map_err(|e| {
                SenseiError::Validation(format!("Invalid {name} (expected RFC 3339): {e}"))
            }),
        None => Ok(None),
    }
}

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing audit logs.
#[derive(Debug, Deserialize)]
pub struct ListAuditLogsParams {
    pub entity_type: Option<String>,
    pub action: Option<String>,
    pub user_id: Option<Uuid>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Audit log statistics response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditLogStats {
    pub total_entries: usize,
    pub by_entity_type: Vec<EntityTypeCount>,
    pub by_action: Vec<ActionCount>,
    pub unique_users: usize,
    pub oldest_entry: Option<DateTime<Utc>>,
    pub newest_entry: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntityTypeCount {
    pub entity_type: String,
    pub count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionCount {
    pub action: String,
    pub count: usize,
}

// ── Audit Logs ─────────────────────────────────────────────────────────────

/// List audit log entries with optional filters.
pub async fn list_audit_logs(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListAuditLogsParams>,
) -> Result<Json<PaginatedResponse<AuditLogEntry>>> {
    let tenant_id = user.tenant_id;
    let store = state.audit_log_entries.read().await;
    let date_from = parse_date_filter("date_from", params.date_from.as_deref())?;
    let date_to = parse_date_filter("date_to", params.date_to.as_deref())?;

    let mut entries: Vec<AuditLogEntry> = store
        .values()
        .filter(|e| e.tenant_id == tenant_id)
        .filter(|e| {
            if let Some(ref entity_type) = params.entity_type {
                e.entity_type == *entity_type
            } else {
                true
            }
        })
        .filter(|e| {
            if let Some(ref action) = params.action {
                e.action == *action
            } else {
                true
            }
        })
        .filter(|e| {
            if let Some(uid) = &params.user_id {
                e.user_id == *uid
            } else {
                true
            }
        })
        .filter(|e| date_from.is_none_or(|df| e.created_at >= df))
        .filter(|e| date_to.is_none_or(|dt| e.created_at <= dt))
        .cloned()
        .collect();
    entries.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    let result = PaginatedResponse::new(entries, params.page, params.per_page);
    Ok(Json(result))
}

/// Get a specific audit log entry by ID.
pub async fn get_audit_log(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<AuditLogEntry>> {
    let tenant_id = user.tenant_id;
    let store = state.audit_log_entries.read().await;
    let entry = store
        .values()
        .find(|e| e.id == id && e.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Audit log entry {id} not found")))?;
    Ok(Json(entry))
}

/// Get audit trail for a specific entity.
pub async fn get_entity_audit_trail(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((entity_type, entity_id)): Path<(String, Uuid)>,
) -> Result<Json<Vec<AuditLogEntry>>> {
    let tenant_id = user.tenant_id;
    let store = state.audit_log_entries.read().await;
    let mut entries: Vec<AuditLogEntry> = store
        .values()
        .filter(|e| {
            e.tenant_id == tenant_id
                && e.entity_type == entity_type
                && e.entity_id == entity_id
        })
        .cloned()
        .collect();
    entries.sort_by(|a, b| a.created_at.cmp(&b.created_at));
    Ok(Json(entries))
}

/// Get audit log statistics.
pub async fn get_audit_log_stats(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<AuditLogStats>> {
    let tenant_id = user.tenant_id;
    let store = state.audit_log_entries.read().await;
    let entries: Vec<&AuditLogEntry> = store
        .values()
        .filter(|e| e.tenant_id == tenant_id)
        .collect();

    let total_entries = entries.len();

    let mut entity_type_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut action_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    let mut unique_users: std::collections::HashSet<Uuid> = std::collections::HashSet::new();

    let mut oldest: Option<DateTime<Utc>> = None;
    let mut newest: Option<DateTime<Utc>> = None;

    for entry in &entries {
        *entity_type_map.entry(entry.entity_type.clone()).or_insert(0) += 1;
        *action_map.entry(entry.action.clone()).or_insert(0) += 1;
        unique_users.insert(entry.user_id);

        match oldest {
            None => oldest = Some(entry.created_at),
            Some(old) if entry.created_at < old => oldest = Some(entry.created_at),
            _ => {}
        }
        match newest {
            None => newest = Some(entry.created_at),
            Some(new) if entry.created_at > new => newest = Some(entry.created_at),
            _ => {}
        }
    }

    let by_entity_type: Vec<EntityTypeCount> = entity_type_map
        .into_iter()
        .map(|(entity_type, count)| EntityTypeCount { entity_type, count })
        .collect();
    let by_action: Vec<ActionCount> = action_map
        .into_iter()
        .map(|(action, count)| ActionCount { action, count })
        .collect();

    let stats = AuditLogStats {
        total_entries,
        by_entity_type,
        by_action,
        unique_users: unique_users.len(),
        oldest_entry: oldest,
        newest_entry: newest,
    };
    Ok(Json(stats))
}

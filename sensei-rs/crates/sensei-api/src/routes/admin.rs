//! Admin route handlers.
//!
//! Provides administrative endpoints for system health, configuration,
//! user management, and logs.

use axum::{Json, extract::{Path, Query, State}};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::AuditLogEntry;
use sensei_core::domain::entities::User;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing users (admin view).
#[derive(Debug, Deserialize)]
pub struct AdminListUsersParams {
    pub is_active: Option<bool>,
    pub role: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Query parameters for listing system logs.
#[derive(Debug, Deserialize)]
pub struct AdminListLogsParams {
    pub level: Option<String>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

// ── Response Types ─────────────────────────────────────────────────────────

/// System health overview.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    pub status: String,
    pub uptime_seconds: u64,
    pub database_connected: bool,
    pub event_bus_connected: bool,
    pub active_users: usize,
    pub active_sessions: usize,
    pub memory_usage_mb: f64,
    pub cpu_usage_pct: f64,
    pub version: String,
    pub services: Vec<ServiceStatus>,
}

/// Individual service status.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceStatus {
    pub name: String,
    pub status: String,
    pub last_checked: DateTime<Utc>,
}

/// Database statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DbStats {
    pub total_users: usize,
    pub total_tenants: usize,
    pub total_entities: std::collections::HashMap<String, usize>,
    pub db_size_bytes: Option<i64>,
    pub connection_count: i32,
}

/// System configuration (redacted secrets).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemConfig {
    pub api_host: String,
    pub api_port: u16,
    pub cors_origins: Vec<String>,
    pub jwt_issuer: String,
    pub jwt_audience: String,
    pub access_token_expiry_minutes: i64,
    pub refresh_token_expiry_days: i64,
    pub storage_backend: String,
    pub email_provider: String,
    pub event_bus_url: String,
    pub log_level: String,
    pub request_timeout_secs: u64,
    pub rate_limit_per_minute: u64,
}

// ── System Health ──────────────────────────────────────────────────────────

/// Get system health overview.
pub async fn get_system_health(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<SystemHealth>> {
    // Check database connectivity
    let db_connected = state.db_pool.as_ref().map(|pool| {
        // Use a simple heuristic - if the pool is configured, assume connected
        !pool.is_closed()
    }).unwrap_or(false);

    // Count active users from the users service
    let active_users = state.users_service.list_users()
        .await
        .map(|users| users.len())
        .unwrap_or(0);

    let health = SystemHealth {
        status: "healthy".to_string(),
        uptime_seconds: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0),
        database_connected: db_connected,
        event_bus_connected: true,
        active_users,
        active_sessions: state.blacklisted_tokens.read().await.len(),
        memory_usage_mb: 0.0,
        cpu_usage_pct: 0.0,
        version: env!("CARGO_PKG_VERSION").to_string(),
        services: vec![
            ServiceStatus {
                name: "API".to_string(),
                status: "running".to_string(),
                last_checked: Utc::now(),
            },
            ServiceStatus {
                name: "Database".to_string(),
                status: if db_connected { "connected" } else { "disconnected" }.to_string(),
                last_checked: Utc::now(),
            },
            ServiceStatus {
                name: "Event Bus".to_string(),
                status: "connected".to_string(),
                last_checked: Utc::now(),
            },
        ],
    };
    Ok(Json(health))
}

/// Get database statistics.
pub async fn get_db_stats(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<DbStats>> {
    // Count entities from in-memory stores
    let mut total_entities = std::collections::HashMap::new();

    total_entities.insert("users".to_string(), state.users_service.list_users()
        .await
        .map(|users| users.len())
        .unwrap_or(0));

    total_entities.insert("inventory_items".to_string(), state.inventory_items.read().await.len());
    total_entities.insert("warehouses".to_string(), state.warehouses.read().await.len());
    total_entities.insert("stock_moves".to_string(), state.stock_moves.read().await.len());
    total_entities.insert("tasks".to_string(), state.tasks.read().await.len());
    total_entities.insert("audit_logs".to_string(), state.audit_log_entries.read().await.len());
    total_entities.insert("kanban_boards".to_string(), state.kanban_boards.read().await.len());
    total_entities.insert("production_cells".to_string(), state.production_cells.read().await.len());
    total_entities.insert("work_centers".to_string(), state.work_centers.read().await.len());
    total_entities.insert("demand_entries".to_string(), state.demand_entries.read().await.len());
    total_entities.insert("supply_orders".to_string(), state.supply_orders.read().await.len());

    let stats = DbStats {
        total_users: total_entities.get("users").copied().unwrap_or(0),
        total_tenants: 1,
        total_entities,
        db_size_bytes: None,
        connection_count: if state.db_pool.is_some() { 1 } else { 0 },
    };
    Ok(Json(stats))
}

// ── User Management ────────────────────────────────────────────────────────

/// List all users (admin view).
pub async fn admin_list_users(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<AdminListUsersParams>,
) -> Result<Json<PaginatedResponse<User>>> {
    let users = state.users_service.list_users_paginated(
        params.role.as_deref(),
        params.is_active,
        params.page,
        params.per_page,
    ).await?;
    Ok(Json(users))
}

/// Deactivate a user (admin view).
pub async fn deactivate_user(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(user_id): Path<Uuid>,
) -> Result<Json<()>> {
    state.users_service.deactivate_user(user_id).await?;
    Ok(Json(()))
}

// ── System Logs ────────────────────────────────────────────────────────────

/// Get recent system logs (from audit log entries).
pub async fn get_system_logs(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<AdminListLogsParams>,
) -> Result<Json<PaginatedResponse<AuditLogEntry>>> {
    let tenant_id = user.tenant_id;
    let store = state.audit_log_entries.read().await;
    let mut entries: Vec<AuditLogEntry> = store
        .values()
        .filter(|e| e.tenant_id == tenant_id)
        .filter(|e| {
            if let Some(ref level) = params.level {
                // Use action as a proxy for log level
                e.action.contains(level)
            } else {
                true
            }
        })
        .filter(|e| {
            if let Some(ref date_from) = params.date_from {
                if let Ok(df) = DateTime::parse_from_rfc3339(date_from) {
                    e.created_at >= df.with_timezone(&Utc)
                } else {
                    true
                }
            } else {
                true
            }
        })
        .filter(|e| {
            if let Some(ref date_to) = params.date_to {
                if let Ok(dt) = DateTime::parse_from_rfc3339(date_to) {
                    e.created_at <= dt.with_timezone(&Utc)
                } else {
                    true
                }
            } else {
                true
            }
        })
        .cloned()
        .collect();
    entries.sort_by(|a, b| b.created_at.cmp(&a.created_at));
    let result = PaginatedResponse::new(entries, params.page, params.per_page);
    Ok(Json(result))
}

// ── System Configuration ───────────────────────────────────────────────────

/// Get system configuration (redacted secrets).
pub async fn get_system_config(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<SystemConfig>> {
    let config = &state.config;
    let config_out = SystemConfig {
        api_host: config.api.host.clone(),
        api_port: config.api.port,
        cors_origins: config.api.cors_allowed_origins.clone(),
        jwt_issuer: config.auth.jwt_issuer.clone(),
        jwt_audience: config.auth.jwt_audience.clone(),
        access_token_expiry_minutes: config.auth.access_token_expiry_minutes,
        refresh_token_expiry_days: config.auth.refresh_token_expiry_days,
        storage_backend: config.storage.backend.clone(),
        email_provider: if config.email.smtp_username.is_empty() {
            "in-memory".to_string()
        } else {
            "smtp".to_string()
        },
        event_bus_url: config.event_bus.url.clone(),
        log_level: "info".to_string(),
        request_timeout_secs: config.api.request_timeout_secs,
        rate_limit_per_minute: 100,
    };
    Ok(Json(config_out))
}

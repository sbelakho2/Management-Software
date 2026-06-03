//! Notification management route handlers.
//!
//! Provides endpoints for listing, reading, and managing user notifications
//! and notification preferences via the [`NotificationService`].

use axum::{Json, extract::{Path, Query, State}};
use serde::Deserialize;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::notifications::service::{Notification, NotificationPreferences};
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing notifications.
#[derive(Debug, Deserialize)]
pub struct ListNotificationsParams {
    /// Number of notifications per page (default 20).
    pub limit: Option<i64>,
    /// Offset for pagination (default 0).
    pub offset: Option<i64>,
}

/// Request body for updating notification preferences.
#[derive(Debug, Deserialize)]
pub struct UpdatePreferencesRequest {
    pub email_notifications: Option<bool>,
    pub push_notifications: Option<bool>,
    pub in_app_notifications: Option<bool>,
    pub digest_frequency: Option<String>,
    pub quiet_hours_start: Option<String>,
    pub quiet_hours_end: Option<String>,
}

// ── Handlers ─────────────────────────────────────────────────────────────────

/// List notifications for the authenticated user.
pub async fn list_notifications(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListNotificationsParams>,
) -> Result<Json<Vec<Notification>>> {
    let limit = params.limit.unwrap_or(20).max(1).min(100);
    let offset = params.offset.unwrap_or(0).max(0);

    let notes = state
        .notification_service
        .list_notifications(user.tenant_id, user.user_id, limit, offset)
        .await?;

    Ok(Json(notes))
}

/// Get unread notification count for the authenticated user.
pub async fn unread_count(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>> {
    let count = state
        .notification_service
        .unread_count(user.tenant_id, user.user_id)
        .await?;

    Ok(Json(serde_json::json!({ "unread_count": count })))
}

/// Mark a single notification as read.
pub async fn mark_notification_read(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<serde_json::Value>> {
    state
        .notification_service
        .mark_read(user.tenant_id, user.user_id, id)
        .await?;

    Ok(Json(serde_json::json!({ "status": "ok" })))
}

/// Mark all notifications as read for the authenticated user.
pub async fn mark_all_read(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>> {
    state
        .notification_service
        .mark_all_read(user.tenant_id, user.user_id)
        .await?;

    Ok(Json(serde_json::json!({ "status": "ok" })))
}

/// Get notification preferences for the authenticated user.
pub async fn get_preferences(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<NotificationPreferences>> {
    let prefs = state
        .notification_service
        .get_preferences(user.tenant_id, user.user_id)
        .await?;

    Ok(Json(prefs))
}

/// Update notification preferences for the authenticated user.
pub async fn update_preferences(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<UpdatePreferencesRequest>,
) -> Result<Json<NotificationPreferences>> {
    // Fetch existing preferences to merge with the request
    let mut prefs = state
        .notification_service
        .get_preferences(user.tenant_id, user.user_id)
        .await?;

    if let Some(v) = req.email_notifications {
        prefs.email_notifications = v;
    }
    if let Some(v) = req.push_notifications {
        prefs.push_notifications = v;
    }
    if let Some(v) = req.in_app_notifications {
        prefs.in_app_notifications = v;
    }
    if let Some(v) = req.digest_frequency {
        // Validate the digest frequency
        match v.as_str() {
            "instant" | "hourly" | "daily" | "never" => prefs.digest_frequency = v,
            _ => {
                return Err(SenseiError::Validation(format!(
                    "Invalid digest_frequency: '{v}'. Must be one of: instant, hourly, daily, never"
                )));
            }
        }
    }
    if let Some(v) = req.quiet_hours_start {
        prefs.quiet_hours_start = Some(v);
    }
    if let Some(v) = req.quiet_hours_end {
        prefs.quiet_hours_end = Some(v);
    }

    state
        .notification_service
        .update_preferences(&prefs)
        .await?;

    Ok(Json(prefs))
}

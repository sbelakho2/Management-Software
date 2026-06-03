//! Notification Trigger route handlers.
//!
//! Provides endpoints for managing event-driven notification trigger rules,
//! including CRUD, enable/disable toggling, and test execution.

use axum::{Json, extract::{Path, Query, State}};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::{NotificationAction, NotificationChannel, NotificationTrigger};

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing notification triggers.
#[derive(Debug, Deserialize)]
pub struct ListTriggersParams {
    pub event_type: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a notification trigger.
#[derive(Debug, Deserialize)]
pub struct CreateTriggerRequest {
    pub name: String,
    pub description: Option<String>,
    pub event_type: String,
    pub condition: serde_json::Value,
    pub action: NotificationAction,
    pub channels: Vec<NotificationChannel>,
    pub cooldown_minutes: Option<i32>,
}

/// Request body for updating a notification trigger (partial).
#[derive(Debug, Deserialize)]
pub struct UpdateTriggerRequest {
    pub name: Option<String>,
    pub description: Option<String>,
    pub event_type: Option<String>,
    pub condition: Option<serde_json::Value>,
    pub action: Option<NotificationAction>,
    pub channels: Option<Vec<NotificationChannel>>,
    pub cooldown_minutes: Option<i32>,
    pub is_active: Option<bool>,
}

/// Request body for testing a trigger.
#[derive(Debug, Deserialize)]
pub struct TestTriggerRequest {
    pub event_payload: serde_json::Value,
}

// ── Response DTOs ──────────────────────────────────────────────────────────

/// Available event type descriptor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventTypeDescriptor {
    pub event_type: String,
    pub description: &'static str,
}

/// Result of a trigger test execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggerTestResult {
    pub trigger_id: Uuid,
    pub condition_matched: bool,
    pub actions_executed: Vec<String>,
    pub channels_notified: Vec<NotificationChannel>,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List notification triggers with optional filters and pagination.
pub async fn list_triggers(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListTriggersParams>,
) -> Result<Json<PaginatedResponse<NotificationTrigger>>> {
    let tenant_id = user.tenant_id;
    let store = state.notification_triggers.read().await;
    let mut triggers: Vec<NotificationTrigger> = store
        .values()
        .filter(|t| t.tenant_id == tenant_id)
        .filter(|t| {
            if let Some(ref et) = params.event_type {
                t.event_type == *et
            } else {
                true
            }
        })
        .filter(|t| {
            if let Some(active) = params.is_active {
                t.is_active == active
            } else {
                true
            }
        })
        .cloned()
        .collect();
    triggers.sort_by(|a, b| a.name.cmp(&b.name));
    let result = PaginatedResponse::new(triggers, params.page, params.per_page);
    Ok(Json(result))
}

/// Create a new notification trigger.
pub async fn create_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateTriggerRequest>,
) -> Result<Json<NotificationTrigger>> {
    let tenant_id = user.tenant_id;
    let now = Utc::now();
    let trigger = NotificationTrigger {
        id: new_id(),
        tenant_id,
        name: req.name,
        description: req.description,
        event_type: req.event_type,
        condition: req.condition,
        action: req.action,
        channels: req.channels,
        cooldown_minutes: req.cooldown_minutes,
        is_active: true,
        last_triggered_at: None,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.notification_triggers.write().await;
    store.insert(trigger.id, trigger.clone());
    Ok(Json(trigger))
}

/// Get a notification trigger by ID.
pub async fn get_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
) -> Result<Json<NotificationTrigger>> {
    let tenant_id = user.tenant_id;
    let store = state.notification_triggers.read().await;
    let trigger = store
        .values()
        .find(|t| t.id == trigger_id && t.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Notification trigger {trigger_id} not found")))?;
    Ok(Json(trigger))
}

/// Update a notification trigger.
pub async fn update_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
    Json(req): Json<UpdateTriggerRequest>,
) -> Result<Json<NotificationTrigger>> {
    let tenant_id = user.tenant_id;
    let mut store = state.notification_triggers.write().await;
    let trigger = store
        .get_mut(&trigger_id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Notification trigger {trigger_id} not found")))?;
    if let Some(name) = req.name {
        trigger.name = name;
    }
    if let Some(desc) = req.description {
        trigger.description = Some(desc);
    }
    if let Some(et) = req.event_type {
        trigger.event_type = et;
    }
    if let Some(cond) = req.condition {
        trigger.condition = cond;
    }
    if let Some(action) = req.action {
        trigger.action = action;
    }
    if let Some(channels) = req.channels {
        trigger.channels = channels;
    }
    if let Some(cooldown) = req.cooldown_minutes {
        trigger.cooldown_minutes = Some(cooldown);
    }
    if let Some(active) = req.is_active {
        trigger.is_active = active;
    }
    trigger.updated_at = Utc::now();
    Ok(Json(trigger.clone()))
}

/// Delete a notification trigger.
pub async fn delete_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
) -> Result<Json<()>> {
    let tenant_id = user.tenant_id;
    let mut store = state.notification_triggers.write().await;
    let exists = store
        .get(&trigger_id)
        .filter(|t| t.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!("Notification trigger {trigger_id} not found")));
    }
    store.remove(&trigger_id);
    Ok(Json(()))
}

/// Enable or disable a notification trigger.
pub async fn toggle_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
) -> Result<Json<NotificationTrigger>> {
    let tenant_id = user.tenant_id;
    let mut store = state.notification_triggers.write().await;
    let trigger = store
        .get_mut(&trigger_id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Notification trigger {trigger_id} not found")))?;
    trigger.is_active = !trigger.is_active;
    trigger.updated_at = Utc::now();
    Ok(Json(trigger.clone()))
}

/// Evaluate whether a trigger condition matches an event payload.
///
/// Supports simple JSON matching:
/// - If condition is `null` or `true`, always matches.
/// - If condition is a JSON object, all key/value pairs must be present
///   in the payload with matching values.
/// - If condition is a JSON array, at least one element must match (OR logic).
fn evaluate_condition(condition: &serde_json::Value, payload: &serde_json::Value) -> bool {
    match condition {
        serde_json::Value::Null => true,
        serde_json::Value::Bool(b) => *b,
        serde_json::Value::Object(map) => map.iter().all(|(key, val)| {
            payload.get(key).map_or(false, |pv| pv == val)
        }),
        serde_json::Value::Array(arr) => {
            if arr.is_empty() {
                return true;
            }
            arr.iter().any(|item| evaluate_condition(item, payload))
        }
        // For primitive values (string, number), check exact match
        _ => condition == payload,
    }
}

/// Test trigger execution with a sample event payload.
pub async fn test_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
    Json(req): Json<TestTriggerRequest>,
) -> Result<Json<TriggerTestResult>> {
    let tenant_id = user.tenant_id;
    let store = state.notification_triggers.read().await;
    let trigger = store
        .values()
        .find(|t| t.id == trigger_id && t.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| SenseiError::NotFound(format!("Notification trigger {trigger_id} not found")))?;

    // Evaluate the trigger condition against the provided event payload.
    let condition_matched = evaluate_condition(&trigger.condition, &req.event_payload);

    let actions_executed = if condition_matched {
        let template_name = trigger.action.template.as_deref().unwrap_or("default");
        vec![format!(
            "Execute {} action for event type: {}",
            template_name, trigger.event_type
        )]
    } else {
        vec![]
    };

    let result = TriggerTestResult {
        trigger_id,
        condition_matched,
        actions_executed,
        channels_notified: trigger.channels.clone(),
    };
    Ok(Json(result))
}

/// List available event types for notification triggers.
pub async fn list_event_types(
    _user: AuthenticatedUser,
    State(_state): State<AppState>,
) -> Result<Json<Vec<EventTypeDescriptor>>> {
    let event_types = vec![
        // ── ERP / existing domains ──────────────────────────────────────
        EventTypeDescriptor {
            event_type: "work_order.status_change".to_string(),
            description: "Work order status transition",
        },
        EventTypeDescriptor {
            event_type: "quality.defect_recorded".to_string(),
            description: "Quality defect or NCR recorded",
        },
        EventTypeDescriptor {
            event_type: "andon.raised".to_string(),
            description: "Andon cord pulled / issue raised",
        },
        EventTypeDescriptor {
            event_type: "maintenance.work_request".to_string(),
            description: "Maintenance work request created",
        },
        EventTypeDescriptor {
            event_type: "inventory.low_stock".to_string(),
            description: "Inventory item below reorder point",
        },
        EventTypeDescriptor {
            event_type: "production.production_report".to_string(),
            description: "Production output reported",
        },
        EventTypeDescriptor {
            event_type: "quality.capa_opened".to_string(),
            description: "CAPA investigation opened",
        },
        EventTypeDescriptor {
            event_type: "training.certification_expiring".to_string(),
            description: "Training certification nearing expiry",
        },
        EventTypeDescriptor {
            event_type: "audit.compliance_breach".to_string(),
            description: "Audit compliance rate below threshold",
        },
        EventTypeDescriptor {
            event_type: "kpi.threshold_breach".to_string(),
            description: "KPI value exceeds upper or lower limit",
        },
        // ── PM / Operations domain events ─────────────────────────────
        EventTypeDescriptor {
            event_type: "operations.a3.created".to_string(),
            description: "A3 problem-solving report created",
        },
        EventTypeDescriptor {
            event_type: "operations.a3.closed".to_string(),
            description: "A3 problem-solving report closed",
        },
        EventTypeDescriptor {
            event_type: "risk.created".to_string(),
            description: "Risk identified and recorded",
        },
        EventTypeDescriptor {
            event_type: "risk.mitigated".to_string(),
            description: "Risk mitigation action completed",
        },
        EventTypeDescriptor {
            event_type: "project.created".to_string(),
            description: "New improvement project created",
        },
        EventTypeDescriptor {
            event_type: "sprint.completed".to_string(),
            description: "Sprint / iteration completed",
        },
        EventTypeDescriptor {
            event_type: "issue.created".to_string(),
            description: "New issue or bug reported",
        },
        // ── PM / Kanban domain events ────────────────────────────────
        EventTypeDescriptor {
            event_type: "kanban.card_moved".to_string(),
            description: "Kanban card moved to a different column",
        },
        EventTypeDescriptor {
            event_type: "kanban.card_created".to_string(),
            description: "New Kanban card created",
        },
        // ── PM / Task domain events ──────────────────────────────────
        EventTypeDescriptor {
            event_type: "task.created".to_string(),
            description: "New task created",
        },
        EventTypeDescriptor {
            event_type: "task.updated".to_string(),
            description: "Task details updated",
        },
        EventTypeDescriptor {
            event_type: "task.status_changed".to_string(),
            description: "Task status transition occurred",
        },
        EventTypeDescriptor {
            event_type: "task.assigned".to_string(),
            description: "Task assigned to a user",
        },
        // ── PM / Obeya domain events ─────────────────────────────────
        EventTypeDescriptor {
            event_type: "obeya.item_added".to_string(),
            description: "New item added to Obeya board",
        },
        EventTypeDescriptor {
            event_type: "obeya.item_updated".to_string(),
            description: "Obeya board item updated",
        },
        // ── PM / State Machine events ────────────────────────────────
        EventTypeDescriptor {
            event_type: "state_machine.transitioned".to_string(),
            description: "State machine instance transitioned",
        },
    ];
    Ok(Json(event_types))
}

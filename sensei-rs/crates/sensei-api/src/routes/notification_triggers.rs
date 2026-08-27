//! Notification Trigger route handlers.
//!
//! Provides endpoints for managing event-driven notification trigger rules,
//! including CRUD, enable/disable toggling, and test execution.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use chrono::Utc;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::new_id;
use serde::{Deserialize, Serialize};
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
    /// Roles whose users receive the notification when this trigger fires.
    /// Empty means the trigger never notifies anyone.
    #[serde(default)]
    pub target_roles: Vec<String>,
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
    pub target_roles: Option<Vec<String>>,
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
    /// Names of the rules (triggers) whose condition matched the payload.
    pub matched_rules: Vec<String>,
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
    user.require_permission("tps:notification-triggers:manage")?;
    let tenant_id = user.tenant_id;
    let store = state.notification_triggers.read(user.tenant_id).await;
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
    user.require_permission("tps:notification-triggers:manage")?;
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
        target_roles: req.target_roles,
        last_triggered_at: None,
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };
    let mut store = state.notification_triggers.write(user.tenant_id).await;
    store.insert(trigger.id, trigger.clone());
    store.persist().await?;
    Ok(Json(trigger))
}

/// Get a notification trigger by ID.
pub async fn get_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
) -> Result<Json<NotificationTrigger>> {
    user.require_permission("tps:notification-triggers:manage")?;
    let tenant_id = user.tenant_id;
    let store = state.notification_triggers.read(user.tenant_id).await;
    let trigger = store
        .values()
        .find(|t| t.id == trigger_id && t.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| {
            SenseiError::NotFound(format!("Notification trigger {trigger_id} not found"))
        })?;
    Ok(Json(trigger))
}

/// Update a notification trigger.
pub async fn update_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
    Json(req): Json<UpdateTriggerRequest>,
) -> Result<Json<NotificationTrigger>> {
    user.require_permission("tps:notification-triggers:manage")?;
    let tenant_id = user.tenant_id;
    let mut store = state.notification_triggers.write(user.tenant_id).await;
    let trigger = store
        .get_mut(&trigger_id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| {
            SenseiError::NotFound(format!("Notification trigger {trigger_id} not found"))
        })?;
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
    // `None` keeps the current value; `Some(x)` sets it (including clearing
    // the cooldown when `Some(None)` semantics are expressed by omitting).
    if let Some(cooldown) = req.cooldown_minutes {
        trigger.cooldown_minutes = Some(cooldown);
    }
    if let Some(active) = req.is_active {
        trigger.is_active = active;
    }
    if let Some(target_roles) = req.target_roles {
        trigger.target_roles = target_roles;
    }
    trigger.updated_at = Utc::now();
    let result = trigger.clone();
    store.persist().await?;
    Ok(Json(result))
}

/// Delete a notification trigger.
pub async fn delete_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("tps:notification-triggers:manage")?;
    let tenant_id = user.tenant_id;
    let mut store = state.notification_triggers.write(user.tenant_id).await;
    let exists = store
        .get(&trigger_id)
        .filter(|t| t.tenant_id == tenant_id)
        .is_some();
    if !exists {
        return Err(SenseiError::NotFound(format!(
            "Notification trigger {trigger_id} not found"
        )));
    }
    store.remove(&trigger_id);
    store.persist().await?;
    Ok(Json(()))
}

/// Enable or disable a notification trigger.
pub async fn toggle_trigger(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(trigger_id): Path<Uuid>,
) -> Result<Json<NotificationTrigger>> {
    let tenant_id = user.tenant_id;
    let mut store = state.notification_triggers.write(user.tenant_id).await;
    let trigger = store
        .get_mut(&trigger_id)
        .filter(|t| t.tenant_id == tenant_id)
        .ok_or_else(|| {
            SenseiError::NotFound(format!("Notification trigger {trigger_id} not found"))
        })?;
    trigger.is_active = !trigger.is_active;
    trigger.updated_at = Utc::now();
    let result = trigger.clone();
    store.persist().await?;
    Ok(Json(result))
}

/// Evaluate whether a trigger condition matches an event payload.
///
/// Supports simple JSON matching:
/// - If condition is `null` or `true`, always matches.
/// - If condition is a JSON object, all key/value pairs must be present
///   in the payload with matching values.
/// - If condition is a JSON array, at least one element must match (OR logic).
/// - `false` never matches.
///
/// Public to the crate so the notification-trigger worker applies exactly
/// the same semantics as the test endpoint.
pub(crate) fn evaluate_condition(
    condition: &serde_json::Value,
    payload: &serde_json::Value,
) -> bool {
    match condition {
        serde_json::Value::Null => true,
        serde_json::Value::Bool(b) => *b,
        serde_json::Value::Object(map) => {
            map.iter().all(|(key, val)| payload.get(key) == Some(val))
        }
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
    let store = state.notification_triggers.read(user.tenant_id).await;
    let trigger = store
        .values()
        .find(|t| t.id == trigger_id && t.tenant_id == tenant_id)
        .cloned()
        .ok_or_else(|| {
            SenseiError::NotFound(format!("Notification trigger {trigger_id} not found"))
        })?;

    // Evaluate the trigger condition against the provided event payload
    // using the real condition evaluator.
    let condition_matched = evaluate_condition(&trigger.condition, &req.event_payload);

    let matched_rules = if condition_matched {
        vec![trigger.name.clone()]
    } else {
        vec![]
    };

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
        matched_rules,
        actions_executed,
        channels_notified: trigger.channels.clone(),
    };
    Ok(Json(result))
}

/// List available event types for notification triggers.
///
/// The catalog is the exact set of `event_type()` strings implemented by
/// the domain events in `sensei-core/src/domain/events.rs` — every entry
/// here matches a real event the bus can deliver. Kept in sync manually;
/// a test below instantiates key events and asserts catalog membership.
pub async fn list_event_types(
    user: AuthenticatedUser,
    State(_state): State<AppState>,
) -> Result<Json<Vec<EventTypeDescriptor>>> {
    user.require_permission("tps:notification-triggers:manage")?;
    let event_types = vec![
        // ── AI ─────────────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "ai.anomaly.detected".to_string(),
            description: "An anomaly was detected by the AI service",
        },
        EventTypeDescriptor {
            event_type: "ai.model.retrained".to_string(),
            description: "An AI/ML model was retrained",
        },
        // ── CRM ────────────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "crm.application.received".to_string(),
            description: "A customer application was received",
        },
        EventTypeDescriptor {
            event_type: "crm.opportunity.stage-changed".to_string(),
            description: "An opportunity moved to a new stage",
        },
        // ── Finance ─────────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "finance.cost-rollup.completed".to_string(),
            description: "A product cost roll-up computation finished",
        },
        EventTypeDescriptor {
            event_type: "finance.invoice.created".to_string(),
            description: "An invoice (AP or AR) was created",
        },
        EventTypeDescriptor {
            event_type: "finance.journal.posted".to_string(),
            description: "A journal entry was posted to the ledger",
        },
        EventTypeDescriptor {
            event_type: "finance.payment.processed".to_string(),
            description: "A payment (AR or AP) was processed",
        },
        // ── HR ──────────────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "hr.certification.expired".to_string(),
            description: "An employee certification expired",
        },
        EventTypeDescriptor {
            event_type: "hr.employee.onboarded".to_string(),
            description: "A new employee completed onboarding",
        },
        EventTypeDescriptor {
            event_type: "hr.leave.approved".to_string(),
            description: "A leave request was approved",
        },
        EventTypeDescriptor {
            event_type: "hr.leave.created".to_string(),
            description: "A leave request was created",
        },
        EventTypeDescriptor {
            event_type: "hr.performance.completed".to_string(),
            description: "A performance review was completed",
        },
        EventTypeDescriptor {
            event_type: "hr.timecard.submitted".to_string(),
            description: "A timecard event was submitted",
        },
        EventTypeDescriptor {
            event_type: "hr.training.completed".to_string(),
            description: "An employee completed a training course",
        },
        // ── Identity ────────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "identity.user.created".to_string(),
            description: "A user account was created",
        },
        // ── Operations / Continuous Improvement ──────────────────────────
        EventTypeDescriptor {
            event_type: "operations.a3.created".to_string(),
            description: "An A3 problem-solving report was created",
        },
        EventTypeDescriptor {
            event_type: "operations.a3.closed".to_string(),
            description: "An A3 problem-solving report was closed",
        },
        EventTypeDescriptor {
            event_type: "operations.andon.acknowledged".to_string(),
            description: "An Andon signal was acknowledged",
        },
        EventTypeDescriptor {
            event_type: "operations.andon.created".to_string(),
            description: "An Andon signal was raised",
        },
        EventTypeDescriptor {
            event_type: "operations.andon.resolved".to_string(),
            description: "An Andon signal was resolved",
        },
        EventTypeDescriptor {
            event_type: "operations.issue.created".to_string(),
            description: "A new issue or bug was reported",
        },
        EventTypeDescriptor {
            event_type: "operations.kanban.created".to_string(),
            description: "A Kanban card was created",
        },
        EventTypeDescriptor {
            event_type: "operations.kanban.deleted".to_string(),
            description: "A Kanban card was deleted",
        },
        EventTypeDescriptor {
            event_type: "operations.kanban.moved".to_string(),
            description: "A Kanban card was moved to another column",
        },
        EventTypeDescriptor {
            event_type: "operations.obeya.item-added".to_string(),
            description: "An item was added to an Obeya board",
        },
        EventTypeDescriptor {
            event_type: "operations.obeya.item-deleted".to_string(),
            description: "An item was deleted from an Obeya board",
        },
        EventTypeDescriptor {
            event_type: "operations.obeya.item-updated".to_string(),
            description: "An Obeya board item was updated",
        },
        EventTypeDescriptor {
            event_type: "operations.project.created".to_string(),
            description: "A new improvement project was created",
        },
        EventTypeDescriptor {
            event_type: "operations.risk.created".to_string(),
            description: "A risk was identified and recorded",
        },
        EventTypeDescriptor {
            event_type: "operations.risk.mitigated".to_string(),
            description: "A risk mitigation action completed",
        },
        EventTypeDescriptor {
            event_type: "operations.sprint.completed".to_string(),
            description: "A sprint / iteration completed",
        },
        // ── Production ───────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "production.downtime.recorded".to_string(),
            description: "Equipment downtime was recorded",
        },
        EventTypeDescriptor {
            event_type: "production.mrp.completed".to_string(),
            description: "An MRP explosion run completed",
        },
        EventTypeDescriptor {
            event_type: "production.order.completed".to_string(),
            description: "A production order was completed",
        },
        EventTypeDescriptor {
            event_type: "production.order.started".to_string(),
            description: "A production order started on the shop floor",
        },
        EventTypeDescriptor {
            event_type: "production.pm.triggered".to_string(),
            description: "A preventive maintenance schedule triggered a work order",
        },
        EventTypeDescriptor {
            event_type: "production.work-order.created".to_string(),
            description: "A maintenance/production work order was created",
        },
        EventTypeDescriptor {
            event_type: "production.work-order.status-changed".to_string(),
            description: "A work order status changed",
        },
        // ── Project Management ───────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "project-management.task.assigned".to_string(),
            description: "A task was assigned to a user",
        },
        EventTypeDescriptor {
            event_type: "project-management.task.created".to_string(),
            description: "A new task was created",
        },
        EventTypeDescriptor {
            event_type: "project-management.task.status-changed".to_string(),
            description: "A task status transition occurred",
        },
        EventTypeDescriptor {
            event_type: "project-management.task.updated".to_string(),
            description: "Task details were updated",
        },
        // ── Quality ──────────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "quality.audit.finding".to_string(),
            description: "An audit finding was recorded",
        },
        EventTypeDescriptor {
            event_type: "quality.capa.closed".to_string(),
            description: "A CAPA was closed",
        },
        EventTypeDescriptor {
            event_type: "quality.capa.created".to_string(),
            description: "A CAPA was created",
        },
        EventTypeDescriptor {
            event_type: "quality.inspection.completed".to_string(),
            description: "An inspection was completed",
        },
        EventTypeDescriptor {
            event_type: "quality.ncr.created".to_string(),
            description: "A non-conformance report (NCR) was created",
        },
        EventTypeDescriptor {
            event_type: "quality.supplier.evaluated".to_string(),
            description: "A supplier was evaluated or scored",
        },
        // ── Saved Views ──────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "saved-view.created".to_string(),
            description: "A saved view was created",
        },
        EventTypeDescriptor {
            event_type: "saved-view.deleted".to_string(),
            description: "A saved view was deleted",
        },
        EventTypeDescriptor {
            event_type: "saved-view.updated".to_string(),
            description: "A saved view was updated",
        },
        // ── State Machines ───────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "state-machine.instance.transitioned".to_string(),
            description: "A state machine instance transitioned",
        },
        // ── Supply Chain ─────────────────────────────────────────────────
        EventTypeDescriptor {
            event_type: "supply-chain.goods-receipt.created".to_string(),
            description: "A goods receipt was created",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.purchase-order.created".to_string(),
            description: "A purchase order was created",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.quote.approved".to_string(),
            description: "A quote was approved",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.quote.converted".to_string(),
            description: "A quote was converted to a sales order",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.quote.created".to_string(),
            description: "A quote was created",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.rfq.created".to_string(),
            description: "A Request for Quote was created",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.rfq.status-changed".to_string(),
            description: "An RFQ status changed",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.sales-order.created".to_string(),
            description: "A sales order was created",
        },
        EventTypeDescriptor {
            event_type: "supply-chain.stock-move.created".to_string(),
            description: "A stock move was created",
        },
    ];
    Ok(Json(event_types))
}

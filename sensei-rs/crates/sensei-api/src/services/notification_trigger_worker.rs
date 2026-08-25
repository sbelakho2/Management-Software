//! Event-driven notification trigger worker.
//!
//! Subscribes to every domain event on the event bus (`sensei.>`, consumer
//! group `notification-triggers`) and evaluates the active notification
//! triggers whose `event_type` matches the delivered event.
//!
//! For every matching trigger:
//! * the condition is evaluated against the event payload (same semantics
//!   as the trigger test endpoint);
//! * the per-trigger cooldown (`cooldown_minutes` since `last_triggered_at`)
//!   is enforced;
//! * in-app `Notification` rows are created for users whose roles intersect
//!   the trigger's `target_roles` (empty `target_roles` never notifies);
//! * email notifications are sent through the email service when the
//!   `Email` channel is enabled;
//! * `last_triggered_at` is updated and persisted.
//!
//! Subscription failures are retried with exponential backoff so a
//! temporarily unavailable bus does not take the worker down.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use chrono::Utc;
use sensei_core::types::new_id;
use tracing::{debug, error, info, warn};

use crate::routes::notification_triggers::evaluate_condition;
use crate::state::AppState;
use crate::stores::{Notification, NotificationChannel, NotificationTrigger};

/// Consumer group shared by all worker instances (competing consumers).
const WORKER_GROUP: &str = "notification-triggers";
/// Subject pattern matching every published event (`sensei.<event_type>`).
const SUBJECT: &str = "sensei.>";
/// Initial subscription retry delay.
const INITIAL_RETRY_DELAY: Duration = Duration::from_secs(2);
/// Maximum subscription retry delay (exponential backoff cap).
const MAX_RETRY_DELAY: Duration = Duration::from_secs(60);

/// Spawn the notification-trigger worker as a background task.
///
/// The worker subscribes to the event bus and stays alive for the lifetime
/// of the process. With an in-memory bus this only sees events published
/// within this process; the caller should log that context.
///
/// Returns a flag that turns `true` once the subscription is active.
/// Callers that publish immediately after spawning should await this flag:
/// neither the in-memory bus nor a freshly-created NATS consumer replays
/// events published before the subscription exists.
pub fn spawn(state: AppState) -> Arc<AtomicBool> {
    let subscribed = Arc::new(AtomicBool::new(false));
    let flag = Arc::clone(&subscribed);
    tokio::spawn(async move {
        let handler = Arc::new(build_handler(state.clone()));
        let mut delay = INITIAL_RETRY_DELAY;
        loop {
            match state
                .event_bus
                .subscribe_with_group(SUBJECT, WORKER_GROUP, handler.clone())
                .await
            {
                Ok(()) => {
                    flag.store(true, Ordering::SeqCst);
                    info!(
                        subject = SUBJECT,
                        group = WORKER_GROUP,
                        "Notification-trigger worker subscribed to event bus"
                    );
                    return;
                }
                Err(e) => {
                    flag.store(false, Ordering::SeqCst);
                    warn!(
                        error = %e,
                        retry_in_ms = delay.as_millis(),
                        "Failed to subscribe notification-trigger worker; retrying"
                    );
                    tokio::time::sleep(delay).await;
                    delay = (delay * 2).min(MAX_RETRY_DELAY);
                }
            }
        }
    });
    subscribed
}

/// Build the synchronous event handler.
///
/// The event bus invokes handlers synchronously, so the actual work is
/// spawned onto the Tokio runtime; the handler itself only enqueues.
fn build_handler(
    state: AppState,
) -> impl Fn(
    sensei_event_bus::types::EventEnvelope,
) -> Result<(), sensei_event_bus::error::EventBusError>
       + Send
       + Sync {
    move |envelope| {
        let state = state.clone();
        tokio::spawn(async move {
            handle_event(state, envelope).await;
        });
        Ok(())
    }
}

/// Process a single delivered event against all matching triggers.
async fn handle_event(state: AppState, envelope: sensei_event_bus::types::EventEnvelope) {
    let tenant_id = envelope.headers.tenant_id;
    let event_type = envelope.event_type.clone();
    let payload = envelope.payload.clone();

    // Evaluate all matching triggers and stamp `last_triggered_at` inside a
    // single write guard so cooldown checks are atomic with the update.
    let matched: Vec<NotificationTrigger> = {
        let mut store = state.notification_triggers.write().await;
        let now = Utc::now();
        let mut matched = Vec::new();
        for trigger in store.values_mut() {
            if !trigger.is_active || trigger.tenant_id != tenant_id {
                continue;
            }
            if trigger.event_type != event_type {
                continue;
            }
            if !evaluate_condition(&trigger.condition, &payload) {
                continue;
            }
            // Cooldown: skip if the last firing is within cooldown_minutes.
            if let Some(cooldown_minutes) = trigger.cooldown_minutes {
                if cooldown_minutes > 0 {
                    if let Some(last_triggered_at) = trigger.last_triggered_at {
                        let elapsed = now - last_triggered_at;
                        if elapsed < chrono::Duration::minutes(cooldown_minutes as i64) {
                            debug!(
                                trigger = %trigger.id,
                                event_type = %event_type,
                                "Trigger skipped: within cooldown"
                            );
                            continue;
                        }
                    }
                }
            }
            // Triggers without target roles never notify (documented
            // behavior: an empty role list is not "notify everyone").
            if trigger.target_roles.is_empty() {
                continue;
            }
            trigger.last_triggered_at = Some(now);
            matched.push(trigger.clone());
        }
        matched
    };

    if matched.is_empty() {
        return;
    }

    // Resolve the users whose roles intersect the triggers' target roles.
    let users = match state.users_service.list_users().await {
        Ok(users) => users,
        Err(e) => {
            error!(error = %e, event_type = %event_type, "Failed to list users for notification triggers");
            return;
        }
    };

    let mut notifications_to_create: Vec<Notification> = Vec::new();
    let mut emails_to_send: Vec<(String, String, String)> = Vec::new();

    for trigger in &matched {
        let body = trigger
            .action
            .template
            .clone()
            .unwrap_or_else(|| trigger.name.clone());
        for user in users.iter().filter(|u| u.tenant_id == tenant_id) {
            let role_match = user
                .roles
                .iter()
                .any(|role| trigger.target_roles.iter().any(|t| t == role));
            if !role_match {
                continue;
            }
            if trigger.channels.contains(&NotificationChannel::InApp) {
                notifications_to_create.push(Notification {
                    id: new_id(),
                    tenant_id,
                    user_id: user.id,
                    title: trigger.name.clone(),
                    body: body.clone(),
                    notification_type: "notification_trigger".to_string(),
                    reference_type: Some(event_type.clone()),
                    reference_id: None,
                    is_read: false,
                    created_at: Utc::now(),
                });
            }
            if trigger.channels.contains(&NotificationChannel::Email) {
                emails_to_send.push((user.email.clone(), trigger.name.clone(), body.clone()));
            }
        }
    }

    if !notifications_to_create.is_empty() {
        let mut store = state.notifications.write().await;
        for notification in notifications_to_create {
            store.insert(notification.id, notification.clone());
        }
    }

    for (to, subject, body) in emails_to_send {
        if let Err(e) = state
            .email_service
            .send_notification(&to, &subject, &body)
            .await
        {
            warn!(to = %to, error = %e, "Failed to send trigger notification email");
        }
    }
}

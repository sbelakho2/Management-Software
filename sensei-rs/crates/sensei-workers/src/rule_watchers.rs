//! Scheduled rule watchers (Phase 6, bounded closed-loops): deterministic
//! workers — NEVER LLM decisions — that surface overdue actions, overdue
//! PM, and material shortages through the event bus.

use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info};

const POLL_INTERVAL: Duration = Duration::from_secs(120);

/// Spawn all scheduled rule watchers.
pub fn spawn(pool: Option<Arc<sqlx::PgPool>>, bus: Arc<dyn sensei_event_bus::EventBus>) {
    let Some(pool) = pool else {
        info!("Rule watchers: no database pool — disabled");
        return;
    };
    tokio::spawn(async move {
        info!("Scheduled rule watchers started");
        loop {
            watch_overdue_actions(&pool, &bus).await;
            watch_overdue_pm(&pool, &bus).await;
            watch_shortages(&pool, &bus).await;
            tokio::time::sleep(POLL_INTERVAL).await;
        }
    });
}

/// Publish an event with at-least-once semantics (the outbox relay is the
/// authoritative mechanism for correctness-relevant events; watcher alerts
/// are notification-grade).
async fn publish_event(
    bus: &Arc<dyn sensei_event_bus::EventBus>,
    event_type: &str,
    payload: serde_json::Value,
) {
    let event = sensei_core::domain::events::GenericJsonEvent::new(event_type, payload);
    if let Err(e) = bus.publish(&event).await {
        error!(error = %e, event_type, "Failed to publish watcher event");
    }
}

/// Tasks past their due date (action aging) are escalated with their
/// original id — one issue, one lineage.
async fn watch_overdue_actions(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) {
    let rows: Vec<(uuid::Uuid, uuid::Uuid, String)> = sqlx::query_as(
        "SELECT id, tenant_id, title FROM tasks \\
         WHERE status NOT IN ('completed', 'cancelled', 'done') \\
           AND due_date IS NOT NULL AND due_date < NOW() \\
           AND escalated_at IS NULL \\
         LIMIT 100",
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default();
    for (task_id, tenant_id, title) in rows {
        let marked = sqlx::query("UPDATE tasks SET escalated_at = NOW() WHERE id = $1")
            .bind(task_id)
            .execute(pool)
            .await;
        match marked {
            Ok(r) if r.rows_affected() == 1 => {
                publish_event(
                    bus,
                    "task.overdue",
                    serde_json::json!({
                        "task_id": task_id, "tenant_id": tenant_id, "title": title,
                        "reason": "action_overdue",
                    }),
                )
                .await;
                info!(task_id = %task_id, "Overdue action escalated");
            }
            _ => {}
        }
    }
}

/// PM schedules whose next_due_at has passed are escalated to the
/// maintenance queue (same schedule id — no new ticket).
async fn watch_overdue_pm(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) {
    let rows: Vec<(uuid::Uuid, uuid::Uuid, String)> = sqlx::query_as(
        "SELECT id, tenant_id, title FROM pm_schedules \\
         WHERE is_active = TRUE \\
           AND next_due_at IS NOT NULL AND next_due_at < NOW() \\
           AND pm_escalated_at IS NULL \\
         LIMIT 100",
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default();
    for (schedule_id, tenant_id, title) in rows {
        let marked = sqlx::query("UPDATE pm_schedules SET pm_escalated_at = NOW() WHERE id = $1")
            .bind(schedule_id)
            .execute(pool)
            .await;
        match marked {
            Ok(r) if r.rows_affected() == 1 => {
                publish_event(
                    bus,
                    "pm.overdue",
                    serde_json::json!({
                        "schedule_id": schedule_id, "tenant_id": tenant_id, "title": title,
                        "reason": "pm_overdue",
                    }),
                )
                .await;
                info!(schedule_id = %schedule_id, "Overdue PM escalated");
            }
            _ => {}
        }
    }
}

/// Materials with a positive net requirement and no open supply are
/// surfaced as shortages (MRP is the deterministic source — never an LLM
/// guess).
async fn watch_shortages(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) {
    let rows: Vec<(uuid::Uuid, uuid::Uuid, String)> = sqlx::query_as(
        "SELECT m.product_id, m.tenant_id, COALESCE(p.name, '') FROM mrp_runs m \\
         LEFT JOIN products p ON p.id = m.product_id \\
         WHERE m.status = 'completed' \\
           AND (m.result::jsonb @> '[{\"net_requirement\": 0}]') = FALSE \\
           AND (SELECT COUNT(*) FROM purchase_orders po \\
                WHERE po.tenant_id = m.tenant_id \\
                  AND po.status NOT IN ('completed', 'cancelled') \\
                  AND po.line_items::jsonb @> jsonb_build_array(jsonb_build_object('product_id', m.product_id::text))) = 0 \\
           AND m.id = (SELECT MAX(id) FROM mrp_runs m2 WHERE m2.product_id = m.product_id) \\
         LIMIT 100",
    )
    .fetch_all(pool)
    .await
    .unwrap_or_default();
    for (product_id, tenant_id, name) in rows {
        publish_event(
            bus,
            "material.shortage",
            serde_json::json!({
                "product_id": product_id, "tenant_id": tenant_id, "product_name": name,
                "reason": "net_requirement_without_supply",
            }),
        )
        .await;
    }
}

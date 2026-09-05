//! Scheduled rule watchers (Phase 6, bounded closed-loops): deterministic
//! workers — NEVER LLM decisions — that surface overdue actions, overdue
//! PM, and material shortages through the event bus.
//!
//! # Tenant scoping (thirtieth-audit item 18, Wave C RLS)
//!
//! Every table the watchers read (`tasks`, `pm_schedules`, `mrp_runs`,
//! `products`, `purchase_orders`) is tenant-owned and fail-closed FORCE RLS
//! since migration 175: a raw-pool query under the production `sensei_app`
//! role has no `app.tenant_id` context and sees zero rows. The watchers
//! therefore enumerate the (RLS-free) `tenants` table and run each pass
//! per tenant inside a [`TenantTx`] — the same architecture the outbox
//! relay uses. Escalation markers are written in the SAME tenant-scoped
//! transaction that read the overdue rows, so a replica cannot double-
//! escalate.

use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info};

use sensei_core::db::TenantTx;

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

/// Enumerate the tenant ids from the RLS-free `tenants` table (no
/// tenant_id column — unaffected by tenant RLS). Only active tenants run
/// watcher passes.
async fn tenant_ids(pool: &sqlx::PgPool) -> Vec<uuid::Uuid> {
    sqlx::query_scalar("SELECT id FROM tenants WHERE is_active = TRUE ORDER BY id")
        .fetch_all(pool)
        .await
        .unwrap_or_default()
}

/// Tasks past their due date (action aging) are escalated with their
/// original id — one issue, one lineage.
async fn watch_overdue_actions(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) {
    for tenant_id in tenant_ids(pool).await {
        // One tenant-scoped transaction per pass: the overdue SELECT and
        // the escalation marker UPDATE see exactly this tenant's rows
        // (migration-175 fail-closed RLS), and the marker lands atomically
        // with the read — a second replica cannot double-escalate.
        let mut tx = match TenantTx::begin(pool, tenant_id).await {
            Ok(tx) => tx,
            Err(e) => {
                error!(error = %e, tenant_id = %tenant_id, "Failed to begin overdue-actions tx");
                continue;
            }
        };
        let rows: Vec<(uuid::Uuid, String)> = match sqlx::query_as(
            "SELECT id, title FROM tasks \
             WHERE status NOT IN ('completed', 'cancelled', 'done') \
               AND due_date IS NOT NULL AND due_date < NOW() \
               AND escalated_at IS NULL \
             LIMIT 100",
        )
        .fetch_all(&mut **tx.tx())
        .await
        {
            Ok(rows) => rows,
            Err(e) => {
                error!(error = %e, tenant_id = %tenant_id, "Failed to read overdue actions");
                continue;
            }
        };
        let mut escalated: Vec<(uuid::Uuid, String)> = Vec::new();
        for (task_id, title) in rows {
            let marked = sqlx::query("UPDATE tasks SET escalated_at = NOW() WHERE id = $1")
                .bind(task_id)
                .execute(&mut **tx.tx())
                .await;
            match marked {
                Ok(r) if r.rows_affected() == 1 => {
                    escalated.push((task_id, title));
                }
                Ok(_) => {
                    // Another replica escalated it between read and write.
                    info!(task_id = %task_id, "Overdue action escalation skipped (already marked)");
                }
                Err(e) => {
                    error!(error = %e, task_id = %task_id, "Failed to mark overdue action");
                }
            }
        }
        if let Err(e) = tx.commit().await {
            error!(error = %e, tenant_id = %tenant_id, "Failed to commit overdue-actions tx");
            continue;
        }
        for (task_id, title) in escalated {
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
    }
}

/// PM schedules whose next_due_at has passed are escalated to the
/// maintenance queue (same schedule id — no new ticket).
async fn watch_overdue_pm(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) {
    for tenant_id in tenant_ids(pool).await {
        let mut tx = match TenantTx::begin(pool, tenant_id).await {
            Ok(tx) => tx,
            Err(e) => {
                error!(error = %e, tenant_id = %tenant_id, "Failed to begin overdue-PM tx");
                continue;
            }
        };
        let rows: Vec<(uuid::Uuid, String)> = match sqlx::query_as(
            "SELECT id, title FROM pm_schedules \
             WHERE is_active = TRUE \
               AND next_due_at IS NOT NULL AND next_due_at < NOW() \
               AND pm_escalated_at IS NULL \
             LIMIT 100",
        )
        .fetch_all(&mut **tx.tx())
        .await
        {
            Ok(rows) => rows,
            Err(e) => {
                error!(error = %e, tenant_id = %tenant_id, "Failed to read overdue PM schedules");
                continue;
            }
        };
        let mut escalated: Vec<(uuid::Uuid, String)> = Vec::new();
        for (schedule_id, title) in rows {
            let marked =
                sqlx::query("UPDATE pm_schedules SET pm_escalated_at = NOW() WHERE id = $1")
                    .bind(schedule_id)
                    .execute(&mut **tx.tx())
                    .await;
            match marked {
                Ok(r) if r.rows_affected() == 1 => {
                    escalated.push((schedule_id, title));
                }
                Ok(_) => {
                    info!(schedule_id = %schedule_id, "Overdue PM escalation skipped (already marked)");
                }
                Err(e) => {
                    error!(error = %e, schedule_id = %schedule_id, "Failed to mark overdue PM");
                }
            }
        }
        if let Err(e) = tx.commit().await {
            error!(error = %e, tenant_id = %tenant_id, "Failed to commit overdue-PM tx");
            continue;
        }
        for (schedule_id, title) in escalated {
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
    }
}

/// Materials with a positive net requirement and no open supply are
/// surfaced as shortages (MRP is the deterministic source — never an LLM
/// guess).
async fn watch_shortages(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) {
    for tenant_id in tenant_ids(pool).await {
        let mut tx = match TenantTx::begin(pool, tenant_id).await {
            Ok(tx) => tx,
            Err(e) => {
                error!(error = %e, tenant_id = %tenant_id, "Failed to begin shortage tx");
                continue;
            }
        };
        // The pass is READ-ONLY (shortages are notifications; the MRP run
        // itself is the source of truth), so a tenant tx admits exactly
        // this tenant's mrp_runs/products/purchase_orders rows. "The
        // product's latest run" is the newest completed run by created_at
        // (mrp_runs.id is a random uuid — MAX(id) is neither valid
        // PostgreSQL nor the newest run).
        let rows: Vec<(uuid::Uuid, String)> = match sqlx::query_as(
            "SELECT m.product_id, COALESCE(p.name, '') FROM mrp_runs m \
             LEFT JOIN products p ON p.id = m.product_id \
             WHERE m.status = 'completed' \
               AND (m.result::jsonb @> '[{\"net_requirement\": 0}]') = FALSE \
               AND (SELECT COUNT(*) FROM purchase_orders po \
                    WHERE po.tenant_id = m.tenant_id \
                      AND po.status NOT IN ('completed', 'cancelled') \
                      AND po.line_items::jsonb @> jsonb_build_array(jsonb_build_object('product_id', m.product_id::text))) = 0 \
               AND m.id = (SELECT m2.id FROM mrp_runs m2 WHERE m2.product_id = m.product_id \
                           ORDER BY m2.created_at DESC, m2.id DESC LIMIT 1) \
             LIMIT 100",
        )
        .fetch_all(&mut **tx.tx())
        .await
        {
            Ok(rows) => rows,
            Err(e) => {
                error!(error = %e, tenant_id = %tenant_id, "Failed to read shortages");
                continue;
            }
        };
        if let Err(e) = tx.commit().await {
            error!(error = %e, tenant_id = %tenant_id, "Failed to commit shortage tx");
            continue;
        }
        for (product_id, name) in rows {
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
}

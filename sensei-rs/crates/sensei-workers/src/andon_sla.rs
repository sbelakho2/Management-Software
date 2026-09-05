//! Andon SLA escalation worker (Phase 6, bounded closed-loop): open Andons
//! past their severity SLA are ESCALATED through the event bus with the
//! SAME issue id — never a new unrelated ticket. This is a deterministic
//! rule worker, not an LLM.
//!
//! # Tenant scoping (thirtieth-audit item 18, Wave C RLS)
//!
//! `andons` is tenant-owned and fail-closed FORCE RLS since migration 175
//! (a raw-pool read under the production `sensei_app` role sees zero
//! rows). Each pass enumerates the RLS-free `tenants` table and processes
//! every tenant inside its own [`TenantTx`]: the overdue SELECT and the
//! escalation marker UPDATE run in the same tenant-scoped transaction so a
//! second replica cannot double-escalate.

use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info, warn};

use sensei_core::db::TenantTx;

const POLL_INTERVAL: Duration = Duration::from_secs(30);

/// SLA (minutes) per severity.
fn sla_minutes(severity: &str) -> i64 {
    match severity {
        "critical" => 15,
        "high" => 60,
        "medium" => 240,
        _ => 480,
    }
}

/// Spawn the Andon SLA escalation watcher.
pub fn spawn(pool: Option<Arc<sqlx::PgPool>>, bus: Arc<dyn sensei_event_bus::EventBus>) {
    let Some(pool) = pool else {
        info!("Andon SLA watcher: no database pool — disabled");
        return;
    };
    tokio::spawn(async move {
        info!("Andon SLA escalation watcher started");
        loop {
            if let Err(e) = watch_once(&pool, &bus).await {
                warn!(error = %e, "Andon SLA watcher pass failed");
            }
            tokio::time::sleep(POLL_INTERVAL).await;
        }
    });
}

/// Enumerate the tenant ids from the RLS-free `tenants` table.
async fn tenant_ids(pool: &sqlx::PgPool) -> Result<Vec<uuid::Uuid>, String> {
    sqlx::query_scalar("SELECT id FROM tenants WHERE is_active = TRUE ORDER BY id")
        .fetch_all(pool)
        .await
        .map_err(|e| format!("Failed to enumerate tenants: {e}"))
}

async fn watch_once(
    pool: &sqlx::PgPool,
    bus: &Arc<dyn sensei_event_bus::EventBus>,
) -> Result<(), String> {
    for tenant_id in tenant_ids(pool).await? {
        watch_tenant(pool, bus, tenant_id).await;
    }
    Ok(())
}

/// One tenant's SLA pass: open Andons whose age exceeds their severity
/// SLA, not yet escalated — read and escalated-marker written in ONE
/// tenant-scoped transaction (migration-175 fail-closed RLS admits exactly
/// this tenant's `andons` rows).
async fn watch_tenant(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>, tenant_id: uuid::Uuid) {
    let mut tx = match TenantTx::begin(pool, tenant_id).await {
        Ok(tx) => tx,
        Err(e) => {
            error!(error = %e, tenant_id = %tenant_id, "Failed to begin andon SLA tx");
            return;
        }
    };
    let rows: Vec<(uuid::Uuid, String, String)> = match sqlx::query_as(
        "SELECT id, severity, issue_type FROM andons \
         WHERE status = 'active' \
           AND escalated_at IS NULL \
           AND EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 > $1 \
         LIMIT 100",
    )
    .bind(sla_minutes("critical"))
    .fetch_all(&mut **tx.tx())
    .await
    {
        Ok(rows) => rows,
        Err(e) => {
            error!(error = %e, tenant_id = %tenant_id, "Failed to read open andons");
            return;
        }
    };

    let mut escalated: Vec<(uuid::Uuid, String, String)> = Vec::new();
    for (andon_id, severity, issue_type) in rows {
        // Mark escalated atomically in the same tenant tx (the same issue
        // id escalates upward); another replica's mark affects zero rows.
        let marked = sqlx::query(
            "UPDATE andons SET escalated_at = NOW(), escalated_to = 'sla_watcher' \
             WHERE id = $1 AND escalated_at IS NULL",
        )
        .bind(andon_id)
        .execute(&mut **tx.tx())
        .await;
        match marked {
            Ok(r) if r.rows_affected() == 1 => escalated.push((andon_id, severity, issue_type)),
            Ok(_) => {
                info!(andon_id = %andon_id, tenant_id = %tenant_id, "Andon escalation skipped (another replica marked it)");
            }
            Err(e) => {
                error!(error = %e, andon_id = %andon_id, "Failed to mark andon escalated");
            }
        }
    }
    if let Err(e) = tx.commit().await {
        error!(error = %e, tenant_id = %tenant_id, "Failed to commit andon SLA tx");
        return;
    }

    for (andon_id, severity, issue_type) in escalated {
        let minutes = sla_minutes(&severity);
        let payload = serde_json::json!({
            "andon_id": andon_id,
            "tenant_id": tenant_id,
            "severity": severity,
            "issue_type": issue_type,
            "sla_minutes": minutes,
            "reason": "andon_sla_breached",
        });
        let event =
            sensei_core::domain::events::GenericJsonEvent::new("andon.sla.escalated", payload);
        if let Err(e) = bus.publish(&event).await {
            error!(
                error = %e,
                andon_id = %andon_id,
                "Failed to publish Andon SLA escalation"
            );
        }
        info!(
            andon_id = %andon_id,
            tenant_id = %tenant_id,
            severity = %severity,
            sla_minutes = minutes,
            "Andon SLA breached — escalation published"
        );
    }
}

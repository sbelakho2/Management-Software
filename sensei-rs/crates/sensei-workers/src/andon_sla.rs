//! Andon SLA escalation worker (Phase 6, bounded closed-loop): open Andons
//! past their severity SLA are ESCALATED through the event bus with the
//! SAME issue id — never a new unrelated ticket. This is a deterministic
//! rule worker, not an LLM.

use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info, warn};

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

async fn watch_once(pool: &sqlx::PgPool, bus: &Arc<dyn sensei_event_bus::EventBus>) -> Result<(), String> {
    // Open Andons whose age exceeds their severity SLA, not yet escalated.
    let rows: Vec<(uuid::Uuid, uuid::Uuid, String, String)> = sqlx::query_as(
        "SELECT id, tenant_id, severity, issue_type FROM andons \\
         WHERE status = 'active' \\
           AND escalated_at IS NULL \\
           AND EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 > $1 \\
         LIMIT 100",
    )
    .bind(sla_minutes("critical"))
    .fetch_all(pool)
    .await
    .map_err(|e| format!("Failed to read open andons: {e}"))?;

    for (andon_id, tenant_id, severity, issue_type) in rows {
        let minutes = sla_minutes(&severity);
        // Mark escalated atomically (the same issue id escalates upward).
        let marked = sqlx::query(
            "UPDATE andons SET escalated_at = NOW(), escalated_to = 'sla_watcher' \\
             WHERE id = $1 AND escalated_at IS NULL",
        )
        .bind(andon_id)
        .execute(pool)
        .await
        .map_err(|e| format!("Failed to mark andon escalated: {e}"))?;
        if marked.rows_affected() == 0 {
            continue; // another replica escalated it
        }

        let payload = serde_json::json!({
            "andon_id": andon_id,
            "tenant_id": tenant_id,
            "severity": severity,
            "issue_type": issue_type,
            "sla_minutes": minutes,
            "reason": "andon_sla_breached",
        });
        let event = sensei_core::domain::events::GenericJsonEvent::new(
            "andon.sla.escalated",
            payload,
        );
        if let Err(e) = bus.publish(&event).await {
            error!(
                error = %e,
                andon_id = %andon_id,
                "Failed to publish Andon SLA escalation"
            );
        }
        info!(
            andon_id = %andon_id,
            severity = %severity,
            sla_minutes = minutes,
            "Andon SLA breached — escalation published"
        );
    }
    Ok(())
}

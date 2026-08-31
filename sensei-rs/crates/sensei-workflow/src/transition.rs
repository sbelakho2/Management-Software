//! Durable checkpointed transitions (fifteenth audit item 1/2): every
//! step a workflow takes is appended to `workflow_checkpoints`, so a
//! crashed workflow RESUMES from its last durable step via
//! [`latest_checkpoint`] and a fresh transition.

use crate::state::WorkflowStatus;
use crate::with_tenant_tx;
use sqlx::PgPool;
use uuid::Uuid;

/// Append a checkpointed transition to a workflow's durable history.
///
/// The checkpoint sequence number is derived atomically inside the same
/// transaction (`MAX(checkpoint) + 1`), so resume steps always extend the
/// history instead of overwriting it. The `UNIQUE (tenant_id, workflow_id,
/// checkpoint)` constraint makes the write idempotent-safe: a replayed
/// transition bumps the sequence instead of colliding.
///
/// `workflow_type` (e.g. `corrective_action.investigate`) distinguishes
/// workflow families sharing the `workflow_checkpoints` table — this is
/// the small engine's only "generic" dimension, per the 5-10% scope rule.
#[allow(clippy::too_many_arguments)]
pub async fn record_transition(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    workflow_type: &str,
    status: WorkflowStatus,
    from_step: &str,
    to_step: &str,
    actor_id: Option<Uuid>,
    payload: &serde_json::Value,
) -> Result<(), String> {
    let workflow_id = workflow_id.to_string();
    let workflow_type = workflow_type.to_string();
    let from_step = from_step.to_string();
    let to_step = to_step.to_string();
    let payload = payload.clone();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            sqlx::query(
                r#"INSERT INTO workflow_checkpoints
                     (tenant_id, workflow_id, workflow_type, step, status, actor_id, payload, checkpoint)
                   VALUES ($1, $2, $3, $4, $5, $6, $7,
                           (SELECT COALESCE(MAX(checkpoint), 0) + 1
                              FROM workflow_checkpoints
                             WHERE tenant_id = $1 AND workflow_id = $2))"#,
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .bind(&workflow_type)
            .bind(&to_step)
            .bind(status.as_str())
            .bind(actor_id)
            .bind(&payload)
            .execute(&mut **tx)
            .await
            .map_err(|e| {
                format!(
                    "failed to record transition {from_step} -> {to_step} for workflow {workflow_id}: {e}"
                )
            })?;
            Ok(())
        })
    })
    .await
}

/// Read the latest durable checkpoint `(checkpoint, step, payload)` of a
/// workflow — the resume point after a crash. Returns `None` when the
/// workflow has no checkpoints (or the read failed, treated as no
/// checkpoint for a best-effort resume probe).
pub async fn latest_checkpoint(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
) -> Option<(u64, String, serde_json::Value)> {
    let workflow_id = workflow_id.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let row: Option<(i64, String, serde_json::Value)> = sqlx::query_as(
                "SELECT checkpoint, step, payload FROM workflow_checkpoints \
                 WHERE tenant_id = $1 AND workflow_id = $2 \
                 ORDER BY checkpoint DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| format!("failed to read latest checkpoint: {e}"))?;
            Ok(row.map(|(checkpoint, step, payload)| (checkpoint as u64, step, payload)))
        })
    })
    .await
    .ok()
    .flatten()
}

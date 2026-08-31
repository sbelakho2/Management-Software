//! Durable checkpointed transitions (fifteenth audit item 1/2, sixteenth
//! audit item 48): every step a workflow takes is appended to
//! `workflow_checkpoints`, so a crashed workflow RESUMES from its last
//! durable step via [`latest_checkpoint`] and a fresh transition.
//!
//! Concurrency (sixteenth audit item 48): the checkpoint sequence is NOT
//! derived from `MAX(checkpoint) + 1` (racy under concurrent resume
//! writers). Every workflow has exactly one `workflow_instances` row
//! (migration 127) whose `current_version` is bumped atomically by the
//! transition UPSERT — the checkpoint number in `workflow_checkpoints`
//! IS that version. [`record_transition`] is the simple UPSERT for first
//! use; [`record_transition_expected`] is the compare-and-swap form that
//! FAILS (0 rows) when the version has moved on.

use crate::state::WorkflowStatus;
use crate::with_tenant_tx;
use sqlx::PgPool;
use uuid::Uuid;

/// Append a checkpoint row at an exact sequence number. Shared by every
/// transition form so the sequence scheme lives in one place.
#[allow(clippy::too_many_arguments)]
async fn insert_checkpoint(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    workflow_id: &str,
    workflow_type: &str,
    status: WorkflowStatus,
    from_step: &str,
    to_step: &str,
    actor_id: Option<Uuid>,
    payload: &serde_json::Value,
    checkpoint: i64,
) -> Result<(), String> {
    sqlx::query(
        r#"INSERT INTO workflow_checkpoints
             (tenant_id, workflow_id, workflow_type, step, status, actor_id, payload, checkpoint)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"#,
    )
    .bind(tenant_id)
    .bind(workflow_id)
    .bind(workflow_type)
    .bind(to_step)
    .bind(status.as_str())
    .bind(actor_id)
    .bind(payload)
    .bind(checkpoint)
    .execute(&mut **tx)
    .await
    .map_err(|e| {
        format!(
            "failed to record transition {from_step} -> {to_step} for workflow {workflow_id}: {e}"
        )
    })?;
    Ok(())
}

/// Upsert the workflow instance row and append its checkpoint, returning
/// the NEW `current_version` (which is also the checkpoint sequence).
///
/// The version is bumped atomically inside the UPSERT itself
/// (`ON CONFLICT ... current_version = current_version + 1`), so two
/// concurrent writers serialize on the instance row lock and each gets a
/// distinct sequence — never a racy `MAX(checkpoint) + 1`.
#[allow(clippy::too_many_arguments)]
pub(crate) async fn append_transition(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    workflow_id: &str,
    workflow_type: &str,
    status: WorkflowStatus,
    from_step: &str,
    to_step: &str,
    actor_id: Option<Uuid>,
    payload: &serde_json::Value,
) -> Result<i64, String> {
    let new_version: i64 = sqlx::query_scalar(
        r#"INSERT INTO workflow_instances (tenant_id, workflow_id, current_step)
           VALUES ($1, $2, $3)
           ON CONFLICT (tenant_id, workflow_id) DO UPDATE
             SET current_step = EXCLUDED.current_step,
                 current_version = workflow_instances.current_version + 1,
                 updated_at = NOW()
           RETURNING current_version"#,
    )
    .bind(tenant_id)
    .bind(workflow_id)
    .bind(to_step)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| format!("failed to advance workflow instance {workflow_id}: {e}"))?;
    insert_checkpoint(
        tx,
        tenant_id,
        workflow_id,
        workflow_type,
        status,
        from_step,
        to_step,
        actor_id,
        payload,
        new_version,
    )
    .await?;
    Ok(new_version)
}

/// Read the workflow's current durable step — the `step` of its LATEST
/// checkpoint. `Ok(None)` when the workflow has no checkpoints yet.
pub(crate) async fn current_step(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    workflow_id: &str,
) -> Result<Option<String>, String> {
    sqlx::query_scalar(
        "SELECT step FROM workflow_checkpoints \
         WHERE tenant_id = $1 AND workflow_id = $2 \
         ORDER BY checkpoint DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(workflow_id)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| format!("failed to read current workflow step: {e}"))
}

/// Append a checkpointed transition to a workflow's durable history.
///
/// The checkpoint sequence number comes from the `workflow_instances`
/// version UPSERT inside the same transaction, so resume steps always
/// extend the history instead of overwriting it. The `UNIQUE (tenant_id,
/// workflow_id, checkpoint)` constraint makes the write idempotent-safe.
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
            append_transition(
                tx,
                tenant_id,
                &workflow_id,
                &workflow_type,
                status,
                &from_step,
                &to_step,
                actor_id,
                &payload,
            )
            .await?;
            Ok(())
        })
    })
    .await
}

/// Optimistic-concurrency (compare-and-swap) transition: advances the
/// workflow ONLY when its instance is still at `expected_version`;
/// otherwise returns `Err` (the version moved on — a stale writer must
/// not corrupt the checkpoint history, sixteenth audit item 48).
///
/// Requires the `workflow_instances` row to exist (use
/// [`record_transition`] for first use).
#[allow(clippy::too_many_arguments)]
pub async fn record_transition_expected(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    workflow_type: &str,
    expected_version: u64,
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
            let updated = sqlx::query(
                "UPDATE workflow_instances \
                 SET current_step = $3, current_version = current_version + 1, updated_at = NOW() \
                 WHERE tenant_id = $1 AND workflow_id = $2 AND current_version = $4",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .bind(&to_step)
            .bind(expected_version as i64)
            .execute(&mut **tx)
            .await
            .map_err(|e| format!("failed to CAS workflow instance {workflow_id}: {e}"))?;
            if updated.rows_affected() == 0 {
                return Err(format!(
                    "optimistic concurrency violation: workflow {workflow_id} is not at expected version {expected_version}"
                ));
            }
            insert_checkpoint(
                tx,
                tenant_id,
                &workflow_id,
                &workflow_type,
                status,
                &from_step,
                &to_step,
                actor_id,
                &payload,
                (expected_version + 1) as i64,
            )
            .await
        })
    })
    .await
}

/// Read the latest durable checkpoint `(checkpoint, step, payload)` of a
/// workflow — the resume point after a crash.
///
/// `Ok(None)` means the workflow has NO checkpoints; a database failure
/// becomes `Err` (sixteenth audit item 50: `None` is reserved for
/// "no checkpoint", never for "the read failed").
pub async fn latest_checkpoint(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
) -> Result<Option<(u64, String, serde_json::Value)>, String> {
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
}

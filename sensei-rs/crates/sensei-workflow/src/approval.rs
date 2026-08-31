//! Human approvals and compensation (fifteenth audit item 1/2): a step
//! that needs a role-gated decision parks the workflow in
//! `AwaitingApproval`. The decision either advances the workflow or
//! returns a [`Compensation`] action to repair the side effects of the
//! rejected step.

use crate::with_tenant_tx;
use sqlx::PgPool;
use uuid::Uuid;

/// The compensation action derived from a rejected approval decision —
/// the audit's `compensation.rs`, kept deliberately tiny: an engine of
/// 5-10% LangGraph generality does not need a compensation framework, it
/// needs an action the caller MUST handle.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Compensation {
    /// No compensation needed (approval granted).
    None,
    /// The rejected step's effects must be reverted.
    RevertStep,
    /// Stakeholders must be notified about the rejection.
    NotifyStakeholders,
}

/// Request a role-gated approval for the workflow's CURRENT step (the
/// latest checkpoint). The approval row is created `pending`; the workflow
/// caller is expected to hold the workflow in `AwaitingApproval` (see
/// `corrective_action::propose_countermeasure`).
pub async fn request_approval(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    required_role: &str,
    rationale: &str,
) -> Result<(), String> {
    let workflow_id = workflow_id.to_string();
    let required_role = required_role.to_string();
    let rationale = rationale.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let step: Option<String> = sqlx::query_scalar(
                "SELECT step FROM workflow_checkpoints \
                 WHERE tenant_id = $1 AND workflow_id = $2 \
                 ORDER BY checkpoint DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| format!("failed to read current workflow step: {e}"))?;
            let step = step
                .ok_or_else(|| format!("workflow {workflow_id} has no checkpoint to approve"))?;
            sqlx::query(
                "INSERT INTO workflow_approvals (tenant_id, workflow_id, step, required_role, rationale) \
                 VALUES ($1, $2, $3, $4, $5)",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .bind(step)
            .bind(&required_role)
            .bind(&rationale)
            .execute(&mut **tx)
            .await
            .map_err(|e| format!("failed to request approval for workflow {workflow_id}: {e}"))?;
            Ok(())
        })
    })
    .await
}

/// Decide the workflow's pending approval.
///
/// * `approved = true`  → the step is marked `approved`; returns
///   [`Compensation::None`] (the workflow may proceed).
/// * `approved = false` → the step is marked `rejected`; returns
///   [`Compensation::RevertStep`] — the caller must revert the step's
///   effects (this is the engine's compensation contract, and the
///   corrective-action workflow's caller surfaces it to stakeholders).
pub async fn decide_approval(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    approved: bool,
    decided_by: Option<Uuid>,
) -> Result<Compensation, String> {
    let workflow_id = workflow_id.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let status = if approved { "approved" } else { "rejected" };
            let updated = sqlx::query(
                "UPDATE workflow_approvals SET status = $3, decided_by = $4, decided_at = NOW() \
                 WHERE tenant_id = $1 AND workflow_id = $2 AND status = 'pending'",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .bind(status)
            .bind(decided_by)
            .execute(&mut **tx)
            .await
            .map_err(|e| format!("failed to decide approval for workflow {workflow_id}: {e}"))?;
            if updated.rows_affected() == 0 {
                return Err(format!("no pending approval for workflow {workflow_id}"));
            }
            Ok(if approved {
                Compensation::None
            } else {
                Compensation::RevertStep
            })
        })
    })
    .await
}

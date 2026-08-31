//! Human approvals and compensation (fifteenth audit item 1/2, sixteenth
//! audit items 48-49, 51): a step that needs a role-gated decision parks
//! the workflow in `AwaitingApproval`. The decision either advances the
//! workflow or returns a [`Compensation`] action to repair the side
//! effects of the rejected step.
//!
//! Authorization is ENFORCED, not descriptive (sixteenth audit item 48):
//! [`decide_approval`] checks the decider's effective roles against the
//! approval's `required_role` BEFORE touching the row, so a caller can
//! never decide an approval it is not entitled to.
//!
//! Durability (sixteenth audit item 51): the decision itself is a
//! checkpointed transition. A rejection records step `compensated` with
//! status `Compensated` — the required repair action SURVIVES a process
//! crash because the checkpoint IS the durable record.

use crate::state::WorkflowStatus;
use crate::transition::append_transition;
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
/// The DECIDER's effective roles (`decider_roles`) must contain the
/// approval's `required_role` — checked before anything is written
/// (sixteenth audit item 48: `required_role` is enforced, not
/// descriptive). A failed role check leaves the approval `pending`.
///
/// * `approved = true`  → the step is marked `approved` and the workflow
///   advances to the durable step `countermeasure_approved`; returns
///   [`Compensation::None`] (the workflow may proceed to verification).
/// * `approved = false` → the step is marked `rejected` and the workflow
///   records a durable step `compensated` (status `Compensated`) — the
///   repair action survives a crash (sixteenth audit item 51); returns
///   [`Compensation::RevertStep`] — the caller must surface/execute the
///   repair the checkpoint records.
pub async fn decide_approval(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    approved: bool,
    decided_by: Option<Uuid>,
    decider_roles: &[String],
) -> Result<Compensation, String> {
    let workflow_id = workflow_id.to_string();
    let decider_roles = decider_roles.to_vec();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            // 1. Authorization: the decider must hold the approval's
            //    required_role. Checked BEFORE the decision write, so a
            //    rejected caller leaves the approval pending.
            let required_role: Option<String> = sqlx::query_scalar(
                "SELECT required_role FROM workflow_approvals \
                 WHERE tenant_id = $1 AND workflow_id = $2 AND status = 'pending' \
                 LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| format!("failed to read pending approval for workflow {workflow_id}: {e}"))?;
            let required_role = required_role
                .ok_or_else(|| format!("no pending approval for workflow {workflow_id}"))?;
            if !decider_roles.iter().any(|r| r == &required_role) {
                return Err(format!(
                    "approver does not hold the required role {required_role} — required_role is enforced, not descriptive"
                ));
            }

            // 2. The decision.
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

            // 3. The decision is itself a durable checkpointed transition:
            //    approved -> step `countermeasure_approved` (verification
            //    may follow); rejected -> step `compensated` (the repair
            //    action survives a crash — item 51).
            let (step, workflow_type): (String, String) = sqlx::query_as(
                "SELECT step, workflow_type FROM workflow_checkpoints \
                 WHERE tenant_id = $1 AND workflow_id = $2 \
                 ORDER BY checkpoint DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| format!("failed to read workflow step for the decision: {e}"))?;
            let (to_step, to_status, decision) = if approved {
                ("countermeasure_approved", WorkflowStatus::AwaitingEvidence, "approved")
            } else {
                ("compensated", WorkflowStatus::Compensated, "rejected")
            };
            append_transition(
                tx,
                tenant_id,
                &workflow_id,
                &workflow_type,
                to_status,
                &step,
                to_step,
                decided_by,
                &serde_json::json!({ "decision": decision }),
            )
            .await?;

            Ok(if approved {
                Compensation::None
            } else {
                Compensation::RevertStep
            })
        })
    })
    .await
}

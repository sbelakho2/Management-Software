//! ONE concrete workflow wired through the engine: corrective-action
//! investigation. The workflow is deliberately simple and deterministic —
//! it exists to PROVE the engine primitives (checkpointed transitions,
//! evidence, approvals, compensation), not to be a generic agent
//! framework.
//!
//! Flow: `start_investigation` (checkpoint `contain`) → observations
//! (evidence) → `propose_countermeasure` (approval request, role
//! `quality_engineer`) → `verify_countermeasure` (evidence) →
//! `close_investigation` (checkpoint `closed`). A crash at any point is
//! survivable: `latest_checkpoint` returns the durable step and the
//! workflow resumes by recording a new checkpoint from it.

use crate::approval;
use crate::evidence::{add_evidence, Evidence};
use crate::state::WorkflowStatus;
use crate::transition::record_transition;
use chrono::Utc;
use sqlx::PgPool;
use uuid::Uuid;

/// The workflow type discriminator for corrective-action investigations.
pub const WORKFLOW_TYPE: &str = "corrective_action.investigate";

/// The role that must approve a proposed countermeasure.
pub const COUNTERMEASURE_APPROVER_ROLE: &str = "quality_engineer";

/// Start an investigation for a condition: creates the workflow instance
/// and records its first durable checkpoint (`contain`, state Running).
///
/// Returns the workflow id (`corrective_action.investigate:<condition_id>`)
/// that every subsequent call addresses.
pub async fn start_investigation(
    pool: &PgPool,
    tenant_id: Uuid,
    condition_id: Uuid,
    actor_id: Uuid,
) -> Result<String, String> {
    let workflow_id = format!("{WORKFLOW_TYPE}:{condition_id}");
    record_transition(
        pool,
        tenant_id,
        &workflow_id,
        WORKFLOW_TYPE,
        WorkflowStatus::Running,
        "start",
        "contain",
        Some(actor_id),
        &serde_json::json!({
            "condition_id": condition_id.to_string(),
            "status": "contained",
        }),
    )
    .await?;
    Ok(workflow_id)
}

/// Record an observation as evidence on the investigation.
pub async fn record_observation(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    observation: serde_json::Value,
) -> Result<(), String> {
    add_evidence(
        pool,
        tenant_id,
        workflow_id,
        Evidence {
            kind: "observation".to_string(),
            source: "investigator".to_string(),
            captured_at: Utc::now(),
            value: observation,
        },
    )
    .await
}

/// Propose a countermeasure: parks the workflow in `AwaitingApproval` and
/// requests a role-gated approval (`quality_engineer`) for the current
/// step. The workflow cannot progress to verification until decided.
pub async fn propose_countermeasure(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    countermeasure: serde_json::Value,
    rationale: &str,
) -> Result<(), String> {
    record_transition(
        pool,
        tenant_id,
        workflow_id,
        WORKFLOW_TYPE,
        WorkflowStatus::AwaitingApproval,
        "contain",
        "countermeasure_proposal",
        None,
        &serde_json::json!({ "countermeasure": countermeasure }),
    )
    .await?;
    approval::request_approval(
        pool,
        tenant_id,
        workflow_id,
        COUNTERMEASURE_APPROVER_ROLE,
        rationale,
    )
    .await
}

/// Record verification results as evidence on the investigation.
pub async fn verify_countermeasure(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    verification: serde_json::Value,
) -> Result<(), String> {
    add_evidence(
        pool,
        tenant_id,
        workflow_id,
        Evidence {
            kind: "verification".to_string(),
            source: "quality_engineer".to_string(),
            captured_at: Utc::now(),
            value: verification,
        },
    )
    .await
}

/// Close the investigation: records the terminal checkpoint (`closed`,
/// state Completed). If the countermeasure approval was previously
/// rejected, the caller should handle the [`Compensation`] returned by
/// [`decide_approval`] before closing.
pub async fn close_investigation(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    actor_id: Uuid,
) -> Result<(), String> {
    record_transition(
        pool,
        tenant_id,
        workflow_id,
        WORKFLOW_TYPE,
        WorkflowStatus::Completed,
        "countermeasure_proposal",
        "closed",
        Some(actor_id),
        &serde_json::json!({ "status": "closed" }),
    )
    .await
}

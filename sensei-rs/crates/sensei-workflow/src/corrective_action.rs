//! ONE concrete workflow wired through the engine: corrective-action
//! investigation. The workflow is deliberately simple and deterministic —
//! it exists to PROVE the engine primitives (checkpointed transitions,
//! evidence, approvals, compensation), not to be a generic agent
//! framework.
//!
//! Flow (sixteenth audit item 47: steps are GUARDED — a step may only
//! advance along the `CorrectiveActionStep::allowed` transitions, and
//! closing requires an approved countermeasure AND verification
//! evidence):
//!
//! `start_investigation` (checkpoints `contain` → `investigate`) →
//! observations (evidence) → `propose_countermeasure` (requires
//! `investigate`; approval request, role `quality_engineer`) →
//! `decide_approval` (moves to `countermeasure_approved` when approved,
//! to `compensated` when rejected) → `verify_countermeasure` (requires
//! `countermeasure_approved`; verification evidence + step `verify`) →
//! `close_investigation` (requires step `verify` AND an approved
//! countermeasure AND verification evidence; checkpoint `closed`). A
//! crash at any point is survivable: `latest_checkpoint` returns the
//! durable step and the workflow resumes by recording a new checkpoint
//! from it.

use crate::approval;
use crate::evidence::{insert_evidence_in_tx, Evidence};
use crate::state::WorkflowStatus;
use crate::transition::{append_transition, current_step};
use crate::with_tenant_tx;
use chrono::Utc;
use sqlx::PgPool;
use uuid::Uuid;

/// The workflow type discriminator for corrective-action investigations.
pub const WORKFLOW_TYPE: &str = "corrective_action.investigate";

/// The role that must approve a proposed countermeasure.
pub const COUNTERMEASURE_APPROVER_ROLE: &str = "quality_engineer";

/// The corrective-action lifecycle (sixteenth audit item 47): closing is
/// only legal from Verify WITH an approved countermeasure AND
/// verification evidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CorrectiveActionStep {
    Contain,
    Investigate,
    CountermeasureProposed,
    CountermeasureApproved,
    Verify,
    Closed,
}

impl CorrectiveActionStep {
    pub fn allowed(from: CorrectiveActionStep, to: CorrectiveActionStep) -> bool {
        use CorrectiveActionStep::*;
        matches!(
            (from, to),
            (Contain, Investigate)
                | (Investigate, CountermeasureProposed)
                | (CountermeasureProposed, CountermeasureApproved)
                | (CountermeasureApproved, Verify)
                | (Verify, Closed)
        )
    }

    /// The durable `workflow_checkpoints.step` value of this step.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Contain => "contain",
            Self::Investigate => "investigate",
            Self::CountermeasureProposed => "countermeasure_proposed",
            Self::CountermeasureApproved => "countermeasure_approved",
            Self::Verify => "verify",
            Self::Closed => "closed",
        }
    }

    /// Parse a durable `workflow_checkpoints.step` value back into the
    /// lifecycle step.
    pub fn parse(step: &str) -> Result<Self, String> {
        serde_json::from_value(serde_json::Value::String(step.to_string()))
            .map_err(|_| format!("{step:?} is not a corrective-action lifecycle step"))
    }
}

/// Read the workflow's current step (the LATEST durable checkpoint) and
/// require it to be exactly `expected` — the transition guard every
/// workflow function runs before advancing (sixteenth audit item 47).
async fn require_step(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    workflow_id: &str,
    expected: CorrectiveActionStep,
) -> Result<(), String> {
    let step = current_step(tx, tenant_id, workflow_id)
        .await?
        .ok_or_else(|| format!("workflow {workflow_id} has no checkpointed steps"))?;
    let current = CorrectiveActionStep::parse(&step)?;
    if current != expected {
        return Err(format!(
            "workflow {workflow_id} is at step {current:?} (db step {step:?}) but this transition requires {expected:?} — audit item 47"
        ));
    }
    Ok(())
}

/// Start an investigation for a condition: creates the workflow instance
/// and records its first durable checkpoints (`contain`, then
/// `investigate` — the transition the guards resume from).
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
    let wf_in_closure = workflow_id.clone();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            append_transition(
                tx,
                tenant_id,
                &wf_in_closure,
                WORKFLOW_TYPE,
                WorkflowStatus::Running,
                "start",
                CorrectiveActionStep::Contain.as_str(),
                Some(actor_id),
                &serde_json::json!({
                    "condition_id": condition_id.to_string(),
                    "status": "contained",
                }),
            )
            .await?;
            append_transition(
                tx,
                tenant_id,
                &wf_in_closure,
                WORKFLOW_TYPE,
                WorkflowStatus::Running,
                CorrectiveActionStep::Contain.as_str(),
                CorrectiveActionStep::Investigate.as_str(),
                Some(actor_id),
                &serde_json::json!({
                    "condition_id": condition_id.to_string(),
                    "status": "investigating",
                }),
            )
            .await?;
            Ok(())
        })
    })
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
    crate::evidence::add_evidence(
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

/// Propose a countermeasure: GUARDED to run only from step
/// `investigate` (sixteenth audit item 47). Parks the workflow in
/// `AwaitingApproval` (durable step `countermeasure_proposed`) and
/// requests a role-gated approval (`quality_engineer`) for it. The
/// workflow cannot progress to verification until decided.
pub async fn propose_countermeasure(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    countermeasure: serde_json::Value,
    rationale: &str,
) -> Result<(), String> {
    let workflow_id = workflow_id.to_string();
    let wf_in_closure = workflow_id.clone();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            require_step(
                tx,
                tenant_id,
                &wf_in_closure,
                CorrectiveActionStep::Investigate,
            )
            .await?;
            append_transition(
                tx,
                tenant_id,
                &wf_in_closure,
                WORKFLOW_TYPE,
                WorkflowStatus::AwaitingApproval,
                CorrectiveActionStep::Investigate.as_str(),
                CorrectiveActionStep::CountermeasureProposed.as_str(),
                None,
                &serde_json::json!({ "countermeasure": countermeasure }),
            )
            .await?;
            Ok(())
        })
    })
    .await?;
    approval::request_approval(
        pool,
        tenant_id,
        &workflow_id,
        COUNTERMEASURE_APPROVER_ROLE,
        rationale,
    )
    .await
}

/// Record verification results: GUARDED to run only from step
/// `countermeasure_approved` (sixteenth audit item 47) — the evidence AND
/// the move to step `verify` happen in one transaction, so verification
/// can never be recorded from any other step.
pub async fn verify_countermeasure(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    verification: serde_json::Value,
) -> Result<(), String> {
    let workflow_id = workflow_id.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            require_step(
                tx,
                tenant_id,
                &workflow_id,
                CorrectiveActionStep::CountermeasureApproved,
            )
            .await?;
            insert_evidence_in_tx(
                tx,
                tenant_id,
                &workflow_id,
                &Evidence {
                    kind: "verification".to_string(),
                    source: "quality_engineer".to_string(),
                    captured_at: Utc::now(),
                    value: verification,
                },
            )
            .await?;
            append_transition(
                tx,
                tenant_id,
                &workflow_id,
                WORKFLOW_TYPE,
                WorkflowStatus::Running,
                CorrectiveActionStep::CountermeasureApproved.as_str(),
                CorrectiveActionStep::Verify.as_str(),
                None,
                &serde_json::json!({ "status": "verified" }),
            )
            .await?;
            Ok(())
        })
    })
    .await
}

/// Close the investigation: records the terminal checkpoint (`closed`,
/// state Completed). GUARDED (sixteenth audit item 47): closing is only
/// legal from step `verify` AND only when the countermeasure approval
/// was approved AND at least one verification evidence row exists — all
/// three checks share the transaction that records the closed
/// checkpoint, so the guard cannot race the write.
///
/// If the countermeasure approval was previously rejected, the caller
/// should handle the [`Compensation`](crate::approval::Compensation)
/// returned by [`decide_approval`](crate::approval::decide_approval)
/// (the durable `compensated` checkpoint records that repair) — closing
/// is not reachable from a rejected workflow.
pub async fn close_investigation(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    actor_id: Uuid,
) -> Result<(), String> {
    let workflow_id = workflow_id.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            // Guard 1: the workflow must be at step verify (read from the
            // latest durable checkpoint).
            require_step(tx, tenant_id, &workflow_id, CorrectiveActionStep::Verify).await?;

            // Guard 2: an APPROVED countermeasure approval must exist
            // (workflow_approvals columns: workflow_id, step,
            // required_role, status, decided_by — migration 118). The
            // approval row is stamped with the step it was requested at,
            // `countermeasure_proposed`.
            let approved: Option<String> = sqlx::query_scalar(
                "SELECT status FROM workflow_approvals \
                 WHERE tenant_id = $1 AND workflow_id = $2 \
                   AND step = 'countermeasure_proposed' AND status = 'approved' \
                 LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| format!("failed to read the countermeasure approval: {e}"))?;
            if approved.is_none() {
                return Err(format!(
                    "close_investigation requires an APPROVED countermeasure approval for workflow {workflow_id} \
                     (workflow_approvals step 'countermeasure_proposed' status 'approved') — audit item 47"
                ));
            }

            // Guard 3: at least one verification evidence row must exist.
            let verification_count: i64 = sqlx::query_scalar(
                "SELECT count(*) FROM workflow_evidence \
                 WHERE tenant_id = $1 AND workflow_id = $2 AND kind = 'verification'",
            )
            .bind(tenant_id)
            .bind(&workflow_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| format!("failed to read verification evidence: {e}"))?;
            if verification_count == 0 {
                return Err(format!(
                    "close_investigation requires at least one verification evidence row for workflow {workflow_id} \
                     (workflow_evidence kind 'verification') — audit item 47"
                ));
            }

            append_transition(
                tx,
                tenant_id,
                &workflow_id,
                WORKFLOW_TYPE,
                WorkflowStatus::Completed,
                CorrectiveActionStep::Verify.as_str(),
                CorrectiveActionStep::Closed.as_str(),
                Some(actor_id),
                &serde_json::json!({ "status": "closed" }),
            )
            .await?;
            Ok(())
        })
    })
    .await
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::approval::{decide_approval, Compensation};
    use crate::transition::{latest_checkpoint, record_transition, record_transition_expected};

    /// The workflow's DB tests run against the same CI gate database as
    /// `sensei-db`'s db_contract suite (`DATABASE_URL_TEST`); without the
    /// variable they skip so the local suite stays green.
    async fn gate_pool() -> Option<PgPool> {
        let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
            eprintln!("SKIP: DATABASE_URL_TEST not set — workflow DB tests run in CI");
            return None;
        };
        let pool = PgPool::connect(&url).await.ok()?;
        sqlx::migrate!("../sensei-db/migrations")
            .run(&pool)
            .await
            .ok()?;
        Some(pool)
    }

    async fn seed_tenant(pool: &PgPool) -> (Uuid, Uuid) {
        let tenant_id = Uuid::new_v4();
        let actor_id = Uuid::new_v4();
        // The gate database is shared and persistent across runs (and the
        // suite runs serially), so the slug/email must be unique per
        // seeded tenant — a fixed literal would collide with leftovers on
        // the second serial run.
        sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'wf', $2)")
            .bind(tenant_id)
            .bind(format!("wf-{tenant_id}"))
            .execute(pool)
            .await
            .expect("tenant insert");
        sqlx::query(
            "INSERT INTO users (id, tenant_id, email, name, password_hash) \
             VALUES ($1, $2, $3, 'W', 'x')",
        )
        .bind(actor_id)
        .bind(tenant_id)
        .bind(format!("wf-{actor_id}@svc.local"))
        .execute(pool)
        .await
        .expect("user insert");
        (tenant_id, actor_id)
    }

    /// A workflow parked at step `countermeasure_proposed` with a pending
    /// approval (start → propose).
    async fn start_proposed(pool: &PgPool, tenant_id: Uuid) -> String {
        let workflow_id = start_investigation(pool, tenant_id, Uuid::new_v4(), Uuid::new_v4())
            .await
            .expect("start must checkpoint contain -> investigate");
        propose_countermeasure(
            pool,
            tenant_id,
            &workflow_id,
            serde_json::json!({ "action": "replace bearing" }),
            "bearing shows visible wear",
        )
        .await
        .expect("propose must succeed from investigate");
        workflow_id
    }

    #[test]
    fn allowed_transitions_table() {
        use CorrectiveActionStep::*;
        assert!(CorrectiveActionStep::allowed(Contain, Investigate));
        assert!(CorrectiveActionStep::allowed(
            Investigate,
            CountermeasureProposed
        ));
        assert!(CorrectiveActionStep::allowed(
            CountermeasureProposed,
            CountermeasureApproved
        ));
        assert!(CorrectiveActionStep::allowed(
            CountermeasureApproved,
            Verify
        ));
        assert!(CorrectiveActionStep::allowed(Verify, Closed));
        assert!(!CorrectiveActionStep::allowed(Contain, Verify));
        assert!(!CorrectiveActionStep::allowed(Contain, Closed));
        assert!(!CorrectiveActionStep::allowed(Investigate, Closed));
        assert!(!CorrectiveActionStep::allowed(
            Verify,
            CountermeasureProposed
        ));
        assert!(!CorrectiveActionStep::allowed(
            CountermeasureProposed,
            Verify
        ));
        assert!(!CorrectiveActionStep::allowed(Closed, Contain));
        assert!(!CorrectiveActionStep::allowed(
            CountermeasureApproved,
            Closed
        ));
        assert!(!CorrectiveActionStep::allowed(Contain, Contain));
    }

    #[tokio::test]
    async fn close_without_approved_countermeasure_fails() {
        let Some(pool) = gate_pool().await else {
            return;
        };
        let (tenant_id, actor_id) = seed_tenant(&pool).await;
        let workflow_id = start_proposed(&pool, tenant_id).await;

        let err = close_investigation(&pool, tenant_id, &workflow_id, actor_id)
            .await
            .expect_err("closing without an approved countermeasure must fail — audit item 47");
        assert!(
            err.contains("Verify"),
            "the close guard names the required step: {err}"
        );
    }

    #[tokio::test]
    async fn close_with_approval_but_no_verification_evidence_fails() {
        let Some(pool) = gate_pool().await else {
            return;
        };
        let (tenant_id, actor_id) = seed_tenant(&pool).await;
        let workflow_id = start_proposed(&pool, tenant_id).await;
        decide_approval(
            &pool,
            tenant_id,
            &workflow_id,
            true,
            Some(actor_id),
            &sensei_auth::authz_snapshot::AuthzSnapshot {
                tenant: tenant_id,
                principal: actor_id,
                roles: vec![COUNTERMEASURE_APPROVER_ROLE.to_string()],
                policy_revision: 1,
                relationship_revision: 1,
                principal_revision: 1,
                scope_site: None,
                permission_digest: [0u8; 32],
            },
        )
        .await
        .expect("the quality engineer approves the countermeasure");

        // Force the workflow to step verify WITHOUT verification evidence:
        // the raw transition primitive is deliberately unguarded — the
        // workflow functions own the guards — so the EVIDENCE guard is
        // what must fail.
        record_transition(
            &pool,
            tenant_id,
            &workflow_id,
            WORKFLOW_TYPE,
            WorkflowStatus::Running,
            CorrectiveActionStep::CountermeasureApproved.as_str(),
            CorrectiveActionStep::Verify.as_str(),
            None,
            &serde_json::json!({}),
        )
        .await
        .expect("raw transition to verify");

        let err = close_investigation(&pool, tenant_id, &workflow_id, actor_id)
            .await
            .expect_err("closing without verification evidence must fail — audit item 47");
        assert!(
            err.contains("verification evidence"),
            "the close guard names the missing evidence: {err}"
        );
    }

    #[tokio::test]
    async fn happy_path_approve_verify_then_close() {
        let Some(pool) = gate_pool().await else {
            return;
        };
        let (tenant_id, actor_id) = seed_tenant(&pool).await;
        let condition_id = Uuid::new_v4();
        let workflow_id = start_investigation(&pool, tenant_id, condition_id, actor_id)
            .await
            .expect("start must checkpoint contain -> investigate");
        propose_countermeasure(
            &pool,
            tenant_id,
            &workflow_id,
            serde_json::json!({ "action": "replace roller 7 bearing" }),
            "bearing shows visible wear",
        )
        .await
        .expect("propose must succeed from investigate");

        let compensation = decide_approval(
            &pool,
            tenant_id,
            &workflow_id,
            true,
            Some(actor_id),
            &sensei_auth::authz_snapshot::AuthzSnapshot {
                tenant: tenant_id,
                principal: actor_id,
                roles: vec![COUNTERMEASURE_APPROVER_ROLE.to_string()],
                policy_revision: 1,
                relationship_revision: 1,
                principal_revision: 1,
                scope_site: None,
                permission_digest: [0u8; 32],
            },
        )
        .await
        .expect("the quality engineer approves the countermeasure");
        assert_eq!(compensation, Compensation::None);

        verify_countermeasure(
            &pool,
            tenant_id,
            &workflow_id,
            serde_json::json!({ "vibration": "within spec" }),
        )
        .await
        .expect("verify must move countermeasure_approved -> verify");

        close_investigation(&pool, tenant_id, &workflow_id, actor_id)
            .await
            .expect("close must checkpoint step closed");

        let (checkpoint, step, payload) = latest_checkpoint(&pool, tenant_id, &workflow_id)
            .await
            .expect("closed workflow has a latest checkpoint")
            .expect("checkpoints exist");
        assert_eq!(
            checkpoint, 6,
            "contain(1) investigate(2) proposed(3) approved(4) verify(5) closed(6)"
        );
        assert_eq!(step, "closed", "workflow terminates at step closed");
        assert_eq!(payload["status"], "closed");
    }

    #[tokio::test]
    async fn cas_transition_succeeds_at_current_version_and_fails_stale() {
        let Some(pool) = gate_pool().await else {
            return;
        };
        let (tenant_id, actor_id) = seed_tenant(&pool).await;
        let workflow_id = start_proposed(&pool, tenant_id).await;
        decide_approval(
            &pool,
            tenant_id,
            &workflow_id,
            true,
            Some(actor_id),
            &sensei_auth::authz_snapshot::AuthzSnapshot {
                tenant: tenant_id,
                principal: actor_id,
                roles: vec![COUNTERMEASURE_APPROVER_ROLE.to_string()],
                policy_revision: 1,
                relationship_revision: 1,
                principal_revision: 1,
                scope_site: None,
                permission_digest: [0u8; 32],
            },
        )
        .await
        .expect("approval must succeed");

        // Current version is 3 (contain, investigate, proposed, approved) —
        // wait, start records 2 checkpoints, propose 1, approve 1 = 4.
        let (version, _, _) = latest_checkpoint(&pool, tenant_id, &workflow_id)
            .await
            .expect("latest checkpoint")
            .expect("checkpoints exist");
        assert_eq!(
            version, 4,
            "contain(1) investigate(2) proposed(3) approved(4)"
        );

        // CAS at the CURRENT version succeeds and advances to 5 ...
        record_transition_expected(
            &pool,
            tenant_id,
            &workflow_id,
            WORKFLOW_TYPE,
            version,
            WorkflowStatus::Running,
            CorrectiveActionStep::CountermeasureApproved.as_str(),
            "probed",
            None,
            &serde_json::json!({}),
        )
        .await
        .expect("a CAS transition at the current version must succeed");
        // ... while a CAS at the now-STALE version fails (0 rows).
        let err = record_transition_expected(
            &pool,
            tenant_id,
            &workflow_id,
            WORKFLOW_TYPE,
            version,
            WorkflowStatus::Running,
            "probed",
            "purged",
            None,
            &serde_json::json!({}),
        )
        .await
        .expect_err("a stale-version CAS must be rejected (0 rows)");
        assert!(
            err.contains("optimistic concurrency"),
            "the CAS failure message: {err}"
        );
        let (version_after, step_after, _) = latest_checkpoint(&pool, tenant_id, &workflow_id)
            .await
            .expect("latest checkpoint")
            .expect("checkpoints exist");
        assert_eq!((version_after, step_after.as_str()), (5, "probed"));
    }

    #[tokio::test]
    async fn rejection_records_durable_compensated_checkpoint() {
        let Some(pool) = gate_pool().await else {
            return;
        };
        let (tenant_id, actor_id) = seed_tenant(&pool).await;
        let workflow_id = start_proposed(&pool, tenant_id).await;

        let compensation = decide_approval(
            &pool,
            tenant_id,
            &workflow_id,
            false,
            Some(actor_id),
            &sensei_auth::authz_snapshot::AuthzSnapshot {
                tenant: tenant_id,
                principal: actor_id,
                roles: vec![COUNTERMEASURE_APPROVER_ROLE.to_string()],
                policy_revision: 1,
                relationship_revision: 1,
                principal_revision: 1,
                scope_site: None,
                permission_digest: [0u8; 32],
            },
        )
        .await
        .expect("a rejection with the required role must decide");
        assert_eq!(compensation, Compensation::RevertStep);

        let (checkpoint, step, payload) = latest_checkpoint(&pool, tenant_id, &workflow_id)
            .await
            .expect("compensated workflow has a latest checkpoint")
            .expect("checkpoints exist");
        assert_eq!(
            checkpoint, 4,
            "contain(1) investigate(2) proposed(3) compensated(4)"
        );
        assert_eq!(
            step, "compensated",
            "the rejection's repair action is durable: step compensated survives a crash"
        );
        assert_eq!(payload["decision"], "rejected");
    }
}

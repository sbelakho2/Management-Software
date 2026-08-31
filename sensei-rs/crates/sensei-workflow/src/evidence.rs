//! Evidence ledger (fifteenth audit item 1/2): workflow steps are backed
//! by immutable, timestamped evidence records (observations, verification
//! results, machine captures). Evidence is appended, never mutated.

use crate::with_tenant_tx;
use chrono::{DateTime, Utc};
use sqlx::PgPool;
use uuid::Uuid;

/// A single piece of evidence attached to a workflow instance.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct Evidence {
    /// The kind of evidence (`observation`, `verification`, `capture`, ...).
    pub kind: String,
    /// Who or what produced it (`investigator`, `quality_engineer`, `sensor-42`, ...).
    pub source: String,
    /// When the evidence was captured (immutable once recorded).
    pub captured_at: DateTime<Utc>,
    /// The structured value of the evidence.
    pub value: serde_json::Value,
}

/// Append an evidence record to a workflow instance. Runs in the same
/// tenant-context transaction pattern as every other engine write.
pub async fn add_evidence(
    pool: &PgPool,
    tenant_id: Uuid,
    workflow_id: &str,
    evidence: Evidence,
) -> Result<(), String> {
    let workflow_id = workflow_id.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move { insert_evidence_in_tx(tx, tenant_id, &workflow_id, &evidence).await })
    })
    .await
}

/// Append an evidence record inside an EXISTING tenant transaction — lets
/// a guarded workflow step record its evidence atomically with its
/// transition (see `corrective_action::verify_countermeasure`).
pub(crate) async fn insert_evidence_in_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    workflow_id: &str,
    evidence: &Evidence,
) -> Result<(), String> {
    sqlx::query(
        "INSERT INTO workflow_evidence (tenant_id, workflow_id, kind, source, captured_at, value) \
         VALUES ($1, $2, $3, $4, $5, $6)",
    )
    .bind(tenant_id)
    .bind(workflow_id)
    .bind(&evidence.kind)
    .bind(&evidence.source)
    .bind(evidence.captured_at)
    .bind(&evidence.value)
    .execute(&mut **tx)
    .await
    .map_err(|e| {
        format!(
            "failed to record {kind} evidence: {e}",
            kind = evidence.kind
        )
    })?;
    Ok(())
}

//! forge_workflow — a small Rust-native workflow engine (fifteenth audit
//! items 1-2): a model invocation is a STATE TRANSITION in a durable
//! workflow. Every step is checkpointed so recovery, resumption, human
//! intervention and historical inspection are native.
//!
//! Scope discipline: this is 5-10% of LangGraph's generality — NOT a
//! generic agent framework. The engine owns exactly four primitives
//! (checkpointed transitions, evidence, approvals, compensation) plus one
//! concrete workflow (`corrective_action`) wired through them.

pub mod approval;
pub mod corrective_action;
pub mod evidence;
pub mod state;
pub mod transition;

use sqlx::PgPool;
use sqlx::Postgres;
use sqlx::Transaction;
use uuid::Uuid;

/// Establish the RLS tenant context on a transaction (SET LOCAL — the
/// setting dies with the transaction, so the context can never leak into
/// another tenant's session). Every workflow table has FAIL-CLOSED RLS
/// (see migration 118): without this, reads and writes return no rows.
async fn set_tenant_context(
    tx: &mut Transaction<'_, Postgres>,
    tenant_id: Uuid,
) -> Result<(), String> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| format!("failed to set tenant context: {e}"))?;
    Ok(())
}

/// Run `f` inside a transaction with the RLS tenant context established —
/// the same pattern as `sensei-services`' `with_tenant_tx`. A workflow
/// function NEVER touches the database outside this wrapper: checkpoint,
/// evidence and approval writes are atomic and tenant-isolated.
pub(crate) async fn with_tenant_tx<T, F>(pool: &PgPool, tenant_id: Uuid, f: F) -> Result<T, String>
where
    F: for<'t> FnOnce(
        &'t mut Transaction<'_, Postgres>,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<T, String>> + Send + 't>,
    >,
{
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| format!("failed to begin tenant tx: {e}"))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| format!("failed to commit tenant tx: {e}"))?;
    Ok(result)
}

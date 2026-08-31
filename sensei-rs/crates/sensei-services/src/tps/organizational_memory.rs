//! Organizational memory (fifteenth audit 42-47 + A8/A18): deterministic
//! promotion — observation -> repeated (occurrence_count >= 2) ->
//! proposed (reviewed) -> approved. A model proposes; approval is a
//! deterministic/reviewed act. Role memory survives employee departure.
//!
//! Memory lives at five tiers: personal / role / process / site /
//! corporate. Role-tier memory is anchored to the ROLE SLOT (not the
//! person) and process-tier memory to the process anchor — neither is
//! deleted when an employee departs.
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MemoryTier {
    Personal,
    Role,
    Process,
    Site,
    Corporate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MemoryStatus {
    Observation,
    Repeated,
    Verified,
    Proposed,
    Approved,
}

/// A row of organizational memory (the read model returned by the routes).
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct MemoryRecord {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub tier: String,
    pub slot_id: Option<Uuid>,
    pub process: Option<String>,
    pub kind: String,
    pub status: String,
    pub content: String,
    pub context_signature: serde_json::Value,
    pub confidence: Option<f64>,
    pub source_problem_id: Option<Uuid>,
    pub occurrence_count: i32,
    pub created_by: Option<Uuid>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

fn is_valid_tier(tier: &str) -> bool {
    matches!(tier, "personal" | "role" | "process" | "site" | "corporate")
}

/// Transaction-scoped tenant context for the RLS policy (the policy is
/// FAIL-CLOSED: missing context = no rows), same convention as
/// `crates/sensei-services/src/ops/database.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

const MEMORY_COLUMNS: &str = "id, tenant_id, tier, slot_id, process, kind, status, content, \
    context_signature, confidence, source_problem_id, occurrence_count, created_by, \
    created_at, updated_at";

/// Record an observation. The SAME memory (context signature + kind +
/// tier) reinforces its occurrence count — the deterministic route from
/// "operator comment" toward "repeated observation": the second
/// occurrence of the same signature flips an `observation` to `repeated`
/// (occurrence_count >= 2) with NO model in the loop. Nothing past
/// `repeated` is automatic — `proposed`/`approved` are review acts.
///
/// Role-tier memory requires a role slot anchor and process-tier memory a
/// process anchor, so the memory outlives any employee departure.
#[allow(clippy::too_many_arguments)]
pub async fn record_observation(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    tier: &str,
    slot_id: Option<Uuid>,
    process: Option<&str>,
    kind: &str,
    content: &str,
    context_signature: serde_json::Value,
    created_by: Option<Uuid>,
) -> Result<()> {
    if !is_valid_tier(tier) {
        return Err(SenseiError::Validation(format!(
            "tier must be one of personal|role|process|site|corporate (got '{tier}')"
        )));
    }
    if tier == "role" && slot_id.is_none() {
        return Err(SenseiError::Validation(
            "role-tier memory must be anchored to a role slot (slot_id)".to_string(),
        ));
    }
    if tier == "process" && process.is_none() {
        return Err(SenseiError::Validation(
            "process-tier memory must be anchored to a process (process)".to_string(),
        ));
    }
    if kind.trim().is_empty() || content.trim().is_empty() {
        return Err(SenseiError::Validation(
            "kind and content are required for an observation".to_string(),
        ));
    }

    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin memory tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;

    // The SAME signature (tier + kind + context_signature + anchors) is the
    // SAME memory: reinforce its occurrence count instead of duplicating.
    let existing: Option<MemoryRecord> = sqlx::query_as(
        "SELECT id, tenant_id, tier, slot_id, process, kind, status, content, \
                context_signature, confidence, source_problem_id, occurrence_count, \
                created_by, created_at, updated_at \
         FROM organizational_memory \
         WHERE tenant_id = $1 AND tier = $2 AND kind = $3 AND context_signature = $4 \
           AND slot_id IS NOT DISTINCT FROM $5 AND process IS NOT DISTINCT FROM $6 \
         ORDER BY created_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(tier)
    .bind(kind)
    .bind(context_signature.clone())
    .bind(slot_id)
    .bind(process)
    .fetch_optional(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Memory lookup failed: {e}")))?;

    if let Some(mem) = existing {
        let count = mem.occurrence_count + 1;
        // Deterministic promotion: an `observation` reaching >= 2
        // occurrences becomes `repeated`. Anything beyond that (verified /
        // proposed / approved) is never granted by the counter — those are
        // reviewed acts.
        let new_status = if mem.status == "observation" && count >= 2 {
            "repeated"
        } else {
            &mem.status
        };
        sqlx::query(
            "UPDATE organizational_memory SET occurrence_count = $1, status = $2, \
             updated_at = NOW() WHERE id = $3",
        )
        .bind(count)
        .bind(new_status)
        .bind(mem.id)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Memory reinforce failed: {e}")))?;
    } else {
        sqlx::query(
            "INSERT INTO organizational_memory \
                (tenant_id, tier, slot_id, process, kind, status, content, \
                 context_signature, occurrence_count, created_by) \
             VALUES ($1, $2, $3, $4, $5, 'observation', $6, $7, 1, $8)",
        )
        .bind(tenant_id)
        .bind(tier)
        .bind(slot_id)
        .bind(process)
        .bind(kind)
        .bind(content)
        .bind(context_signature)
        .bind(created_by)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Memory insert failed: {e}")))?;
    }

    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Memory commit failed: {e}")))?;
    Ok(())
}

/// The deterministic kernel's read-back: the affected memory row for a
/// signature (used by the observe route after [`record_observation`]).
pub async fn find_memory_by_signature(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    tier: &str,
    slot_id: Option<Uuid>,
    process: Option<&str>,
    kind: &str,
    context_signature: &serde_json::Value,
) -> Result<MemoryRecord> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin memory read tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let row: MemoryRecord = sqlx::query_as(
        "SELECT id, tenant_id, tier, slot_id, process, kind, status, content, \
                context_signature, confidence, source_problem_id, occurrence_count, \
                created_by, created_at, updated_at \
         FROM organizational_memory \
         WHERE tenant_id = $1 AND tier = $2 AND kind = $3 AND context_signature = $4 \
           AND slot_id IS NOT DISTINCT FROM $5 AND process IS NOT DISTINCT FROM $6 \
         ORDER BY created_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(tier)
    .bind(kind)
    .bind(context_signature.clone())
    .bind(slot_id)
    .bind(process)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Memory read-back failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Memory read-back commit failed: {e}")))?;
    Ok(row)
}

/// List memory rows filtered by tier/status (read inside the tenant
/// context; RLS is fail-closed without it).
pub async fn list_memory(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    tier: Option<&str>,
    status: Option<&str>,
) -> Result<Vec<MemoryRecord>> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin memory list tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let rows: Vec<MemoryRecord> = sqlx::query_as(
        "SELECT id, tenant_id, tier, slot_id, process, kind, status, content, \
                context_signature, confidence, source_problem_id, occurrence_count, \
                created_by, created_at, updated_at \
         FROM organizational_memory \
         WHERE tenant_id = $1 AND ($2::text IS NULL OR tier = $2) \
           AND ($3::text IS NULL OR status = $3) \
         ORDER BY updated_at DESC LIMIT 500",
    )
    .bind(tenant_id)
    .bind(tier)
    .bind(status)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Memory list failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Memory list commit failed: {e}")))?;
    Ok(rows)
}

/// A reviewed promotion step: move one memory to the `target` status, but
/// ONLY from an allowed current status — enforced atomically in the
/// UPDATE's WHERE so a stale reader can never race a promotion. The model
/// can propose; approval is the final human gate.
pub async fn transition_memory(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
    target: &str,
    allowed: &[&str],
) -> Result<MemoryRecord> {
    let in_clause = allowed
        .iter()
        .map(|s| format!("'{s}'"))
        .collect::<Vec<_>>()
        .join(", ");
    let sql = format!(
        "UPDATE organizational_memory SET status = $3, updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $2 AND status IN ({in_clause}) \
         RETURNING {MEMORY_COLUMNS}"
    );

    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin memory tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let row: Option<MemoryRecord> = sqlx::query_as(&sql)
        .bind(id)
        .bind(tenant_id)
        .bind(target)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Memory transition failed: {e}")))?;

    let Some(row) = row else {
        let current: Option<String> = sqlx::query_scalar(
            "SELECT status FROM organizational_memory WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Memory state read failed: {e}")))?;
        return match current {
            None => Err(SenseiError::NotFound(format!("Memory {id} not found"))),
            Some(status) => Err(SenseiError::Conflict(format!(
                "Memory {id} is already {status} — only {allowed:?} can be promoted to {target}"
            ))),
        };
    };
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Memory transition commit failed: {e}")))?;
    Ok(row)
}

/// Propose a memory for approval (a reviewed act, never automatic): only
/// observations / repeated / verified memories can be proposed.
pub async fn propose_memory(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
) -> Result<MemoryRecord> {
    transition_memory(
        pool,
        tenant_id,
        id,
        "proposed",
        &["observation", "repeated", "verified"],
    )
    .await
}

/// Approve a memory — the final gate. Only a PROPOSED memory can be
/// approved; the AI can only have proposed, it can never approve itself.
pub async fn approve_memory(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
) -> Result<MemoryRecord> {
    transition_memory(pool, tenant_id, id, "approved", &["proposed"]).await
}

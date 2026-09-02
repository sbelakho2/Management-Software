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
    pub owner_principal_id: Option<Uuid>,
    pub scope_site_id: Option<Uuid>,
    pub provenance_event_ids: serde_json::Value,
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

const MEMORY_COLUMNS: &str = "id, tenant_id, tier, slot_id, process, owner_principal_id, \
    scope_site_id, provenance_event_ids, kind, status, content, context_signature, \
    confidence, source_problem_id, occurrence_count, created_by, created_at, updated_at";

/// Record an observation. The SAME memory (context signature + kind +
/// tier + anchors) reinforces its occurrence count — the deterministic
/// route from "operator comment" toward "repeated observation": the
/// second occurrence of the same signature flips an `observation` to
/// `repeated` (occurrence_count >= 2) with NO model in the loop. Nothing
/// past `repeated` is automatic — `proposed`/`approved` are review acts.
///
/// Each tier STRUCTURALLY requires its anchor: personal memory is bound
/// to a principal (`owner_principal_id`), role memory to a role slot
/// (`slot_id`), process memory to a process, site memory to a site
/// (`scope_site_id`) — the database CHECK backs the service up.
///
/// INDEPENDENT CORROBORATION (sixteenth audit item 41): promotion to
/// `repeated` must NOT fire from the same provenance twice. Two
/// observations by the same person/sensor/import (the same source event
/// ids) are NOT independent corroboration. The new provenance event ids
/// are merged into the row (distinct); the occurrence count increments
/// ONLY when the new record contributes at least one event id not
/// already seen — a duplicate API retry or same-source repeat is a
/// no-op. Promotion requires >= 2 DISTINCT event ids, so a row recorded
/// with no provenance can never become `repeated` from the counter.
#[allow(clippy::too_many_arguments)]
pub async fn record_observation(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    tier: &str,
    slot_id: Option<Uuid>,
    process: Option<&str>,
    owner_principal_id: Option<Uuid>,
    scope_site_id: Option<Uuid>,
    provenance_event_ids: Vec<String>,
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
    if tier == "personal" && owner_principal_id.is_none() {
        return Err(SenseiError::Validation(
            "personal-tier memory must be anchored to a principal (owner_principal_id)".to_string(),
        ));
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
    if tier == "site" && scope_site_id.is_none() {
        return Err(SenseiError::Validation(
            "site-tier memory must be anchored to a site (scope_site_id)".to_string(),
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

    // Seventeenth audit item 10 — provenance CANNOT be fabricated: every
    // claimed source event id must EXIST in this tenant's canonical
    // operational_events log. Fake ids ("event-fake-1") are rejected
    // before any insert/reinforce, so a caller cannot promote an
    // observation to `repeated` with invented corroboration.
    if !provenance_event_ids.is_empty() {
        let existing_count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM operational_events WHERE tenant_id = $1              AND id::text = ANY($2)",
        )
        .bind(tenant_id)
        .bind(&provenance_event_ids)
        .fetch_one(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Provenance lookup failed: {e}")))?;
        if existing_count != provenance_event_ids.len() as i64 {
            return Err(SenseiError::Validation(format!(
                "provenance_event_ids must reference EXISTING canonical events in this tenant                  ({} of {} resolved)",
                existing_count,
                provenance_event_ids.len()
            )));
        }
    }

    // The SAME signature (tier + kind + context_signature + anchors) is the
    // SAME memory: reinforce its occurrence count instead of duplicating.
    let existing: Option<MemoryRecord> = sqlx::query_as(
        "SELECT id, tenant_id, tier, slot_id, process, owner_principal_id, \
                scope_site_id, provenance_event_ids, kind, status, content, \
                context_signature, confidence, source_problem_id, occurrence_count, \
                created_by, created_at, updated_at \
         FROM organizational_memory \
         WHERE tenant_id = $1 AND tier = $2 AND kind = $3 AND context_signature = $4 \
           AND slot_id IS NOT DISTINCT FROM $5 AND process IS NOT DISTINCT FROM $6 \
           AND owner_principal_id IS NOT DISTINCT FROM $7 \
           AND scope_site_id IS NOT DISTINCT FROM $8 \
           AND quarantined = FALSE \
         ORDER BY created_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(tier)
    .bind(kind)
    .bind(context_signature.clone())
    .bind(slot_id)
    .bind(process)
    .bind(owner_principal_id)
    .bind(scope_site_id)
    .fetch_optional(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Memory lookup failed: {e}")))?;

    if let Some(mem) = existing {
        // Independent corroboration: the count increments only when this
        // record contributes a NEW source event id. The same person/sensor/
        // import repeating itself (or an API retry) is not corroboration.
        let mut known: Vec<String> = mem
            .provenance_event_ids
            .as_array()
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();
        let new_ids: Vec<String> = provenance_event_ids
            .into_iter()
            .filter(|id| !known.iter().any(|k| k == id))
            .collect();
        if new_ids.is_empty() {
            tx.commit()
                .await
                .map_err(|e| SenseiError::Database(format!("Memory commit failed: {e}")))?;
            return Ok(());
        }
        known.extend(new_ids.iter().cloned());
        let count = mem.occurrence_count + 1;
        // Deterministic promotion: an `observation` reaching >= 2
        // occurrences with >= 2 DISTINCT source event ids becomes
        // `repeated`. Zero-provenance observations can never cross the
        // corroboration bar. Anything beyond that (verified / proposed /
        // approved) is never granted by the counter — those are reviewed
        // acts.
        let new_status = if mem.status == "observation" && count >= 2 && known.len() >= 2 {
            "repeated"
        } else {
            &mem.status
        };
        sqlx::query(
            "UPDATE organizational_memory SET occurrence_count = $1, status = $2, \
             provenance_event_ids = $3, updated_at = NOW() WHERE id = $4",
        )
        .bind(count)
        .bind(new_status)
        .bind(serde_json::json!(known))
        .bind(mem.id)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Memory reinforce failed: {e}")))?;
    } else {
        let mut distinct: Vec<String> = Vec::new();
        for id in provenance_event_ids {
            if !distinct.iter().any(|d| d == &id) {
                distinct.push(id);
            }
        }
        sqlx::query(
            "INSERT INTO organizational_memory \
                (tenant_id, tier, slot_id, process, owner_principal_id, scope_site_id, \
                 provenance_event_ids, kind, status, content, context_signature, \
                 occurrence_count, created_by) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'observation', $9, $10, 1, $11)",
        )
        .bind(tenant_id)
        .bind(tier)
        .bind(slot_id)
        .bind(process)
        .bind(owner_principal_id)
        .bind(scope_site_id)
        .bind(serde_json::json!(distinct))
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
#[allow(clippy::too_many_arguments)]
pub async fn find_memory_by_signature(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    tier: &str,
    slot_id: Option<Uuid>,
    process: Option<&str>,
    owner_principal_id: Option<Uuid>,
    scope_site_id: Option<Uuid>,
    kind: &str,
    context_signature: &serde_json::Value,
) -> Result<MemoryRecord> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin memory read tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let row: MemoryRecord = sqlx::query_as(
        "SELECT id, tenant_id, tier, slot_id, process, owner_principal_id, \
                scope_site_id, provenance_event_ids, kind, status, content, \
                context_signature, confidence, source_problem_id, occurrence_count, \
                created_by, created_at, updated_at \
         FROM organizational_memory \
         WHERE tenant_id = $1 AND tier = $2 AND kind = $3 AND context_signature = $4 \
           AND slot_id IS NOT DISTINCT FROM $5 AND process IS NOT DISTINCT FROM $6 \
           AND owner_principal_id IS NOT DISTINCT FROM $7 \
           AND scope_site_id IS NOT DISTINCT FROM $8 \
           AND quarantined = FALSE \
         ORDER BY created_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(tier)
    .bind(kind)
    .bind(context_signature.clone())
    .bind(slot_id)
    .bind(process)
    .bind(owner_principal_id)
    .bind(scope_site_id)
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
        "SELECT id, tenant_id, tier, slot_id, process, owner_principal_id, \
                scope_site_id, provenance_event_ids, kind, status, content, \
                context_signature, confidence, source_problem_id, occurrence_count, \
                created_by, created_at, updated_at \
         FROM organizational_memory \
         WHERE tenant_id = $1 AND ($2::text IS NULL OR tier = $2) \
           AND ($3::text IS NULL OR status = $3) \
           AND quarantined = FALSE \
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

/// Eighteenth audit P1-13: explicit quarantine reconciliation. Rows
/// without a valid anchor were quarantined by migration 141 and are
/// excluded from every context-serving read; the ONLY admissible
/// outcomes are repair (backfill the anchor) or DISCARD. This function
/// discards the quarantined rows for the tenant and returns how many
/// were removed — after it reports 0 remaining, the anchor CHECK can be
/// VALIDATED (the final stage of the rolling migration).
pub async fn reconcile_quarantined_memory(pool: &sqlx::PgPool, tenant_id: Uuid) -> Result<i64> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin reconcile tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let removed = sqlx::query(
        "DELETE FROM organizational_memory \
         WHERE tenant_id = $1 AND quarantined = TRUE",
    )
    .bind(tenant_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to discard quarantined memory: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit reconcile: {e}")))?;
    Ok(removed.rows_affected() as i64)
}

//! Authorization snapshots (fifteenth audit 24/A5).
//!
//! Every AI execution carries the policy/relationship/principal revision
//! it was authorized under THROUGH THE WHOLE TRANSACTION — retrieval can
//! never run under one permission state and execution under another.
//! A revocation bumps the revision; because every authorization-derived
//! cache key embeds [`AuthorizationSnapshot::cache_salt`], the bump
//! invalidates those caches atomically.

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// The permission-state revision triple an execution was authorized under.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AuthorizationSnapshot {
    pub policy_revision: u64,
    pub relationship_revision: u64,
    pub principal_revision: u64,
}

impl AuthorizationSnapshot {
    /// A cache key component: the snapshot salts every context/KV cache
    /// key so a revocation invalidates all derived caches.
    pub fn cache_salt(&self) -> String {
        format!(
            "{}-{}-{}",
            self.policy_revision, self.relationship_revision, self.principal_revision
        )
    }
}

/// Transaction-scoped tenant context for RLS (SET LOCAL app.tenant_id) —
/// same convention as `crates/sensei-services/src/ops/database.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> std::result::Result<(), SenseiError> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Read the tenant's current authorization snapshot.
///
/// Lazy per-tenant seeding (INSERT ... ON CONFLICT DO NOTHING) — the
/// migration seed only covers tenants that existed at migration time; a
/// tenant created later gets its row on first read. Same pattern as the
/// field-authority lazy seed in
/// `crates/sensei-api/src/routes/integration_importer.rs` (`field_is_writable`).
pub async fn current_snapshot(pool: &PgPool, tenant_id: Uuid) -> Result<AuthorizationSnapshot> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin snapshot tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;

    sqlx::query(
        "INSERT INTO authorization_revisions (tenant_id, policy_revision, \
             relationship_revision, principal_revision) \
         VALUES ($1, 1, 1, 1) \
         ON CONFLICT (tenant_id) DO NOTHING",
    )
    .bind(tenant_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Authorization snapshot seed failed: {e}")))?;

    let (policy, relationship, principal): (i64, i64, i64) = sqlx::query_as(
        "SELECT policy_revision, relationship_revision, principal_revision \
         FROM authorization_revisions WHERE tenant_id = $1",
    )
    .bind(tenant_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to read authorization snapshot: {e}")))?;

    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit snapshot tx: {e}")))?;

    Ok(AuthorizationSnapshot {
        policy_revision: policy as u64,
        relationship_revision: relationship as u64,
        principal_revision: principal as u64,
    })
}

/// Increment the principal revision — called on departure/revocation: the
/// handover departure endpoint's job. Invalidates authorization-derived
/// caches (A5).
pub async fn bump_principal(pool: &PgPool, tenant_id: Uuid) -> Result<()> {
    bump(pool, tenant_id, "principal_revision").await
}

/// Increment the relationship revision (roles/slots change).
pub async fn bump_relationship(pool: &PgPool, tenant_id: Uuid) -> Result<()> {
    bump(pool, tenant_id, "relationship_revision").await
}

/// IN-TX bump (seventeenth audit item 5): every authorization mutation
/// (assignment, unassignment, policy change) bumps the revision in the
/// SAME transaction that performs the mutation — an authorization state
/// change without a revision change is impossible. The caller owns the
/// transaction (tenant context already set); the revision row is lazily
/// seeded in the same statement.
pub async fn bump_in_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    column: &str,
) -> Result<()> {
    let column = match column {
        "policy_revision" | "relationship_revision" | "principal_revision" => column,
        _ => {
            return Err(SenseiError::Validation(format!(
                "invalid revision column: {column}"
            )))
        }
    };
    sqlx::query(
        "INSERT INTO authorization_revisions (tenant_id, policy_revision, \
             relationship_revision, principal_revision) \
         VALUES ($1, 1, 1, 1) \
         ON CONFLICT (tenant_id) DO NOTHING",
    )
    .bind(tenant_id)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Revision seed failed: {e}")))?;
    sqlx::query(&format!(
        "UPDATE authorization_revisions SET {column} = {column} + 1, updated_at = NOW() \
         WHERE tenant_id = $1",
    ))
    .bind(tenant_id)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("In-tx revision bump failed: {e}")))?;
    Ok(())
}

/// Increment the policy revision (policy objects change).
pub async fn bump_policy(pool: &PgPool, tenant_id: Uuid) -> Result<()> {
    bump(pool, tenant_id, "policy_revision").await
}

async fn bump(pool: &PgPool, tenant_id: Uuid, column: &str) -> Result<()> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin revision bump tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;

    sqlx::query(&format!(
        "UPDATE authorization_revisions SET {column} = {column} + 1, updated_at = NOW() \
         WHERE tenant_id = $1",
    ))
    .bind(tenant_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Authorization revision bump failed: {e}")))?;

    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit revision bump tx: {e}")))?;
    Ok(())
}

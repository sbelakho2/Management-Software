//! Per-request effective-permission resolution (twenty-ninth audit Wave A).
//!
//! Live authorization for an authenticated request is the UNION of:
//!
//! 1. **Static expansion** — every role's own permissions plus every
//!    ancestor role's permissions through the compiled RBAC map and its
//!    NIST hierarchy ([`RbacService::expand_static`]); and
//! 2. **Tenant custom rows** — the tenant-scoped `roles` table rows for
//!    the caller's roles (the DB is the extension point for custom
//!    roles; `SELECT name, permissions FROM roles WHERE tenant_id = $1
//!    AND name = ANY($2)`).
//!
//! The middleware resolves this per authenticated request and carries the
//! resulting permission set on [`crate::middleware::AuthenticatedUser`],
//! so authorization decisions never depend on a process-global snapshot
//! installed at startup (a stale role change cannot outlive its row
//! update).
//!
//! RLS note (audit Wave A): the `roles` table is NOT row-level-secured by
//! the migration chain (migrations 070/079 secure `users` and the other
//! tenant tables; no migration enables RLS on `roles`), so a plain-pool
//! read with an explicit `tenant_id = $1` predicate is acceptable and is
//! what `RbacService::from_db` and the users-service role validation
//! already do. Reads of the `users` row itself DO run inside a
//! tenant-scoped transaction in the middleware (`users` is FORCE RLS).

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use std::collections::HashSet;
use uuid::Uuid;

use crate::rbac::RbacService;

/// Resolve the effective permission set for a principal holding `roles`
/// inside `tenant_id`.
///
/// Static expansion from the compiled RBAC map/hierarchy is merged with
/// the tenant's custom `roles` rows (a custom role never crosses tenant
/// boundaries — the query is tenant-filtered). Failures are surfaced as
/// [`SenseiError::Database`] so callers can fail closed.
pub async fn resolve_effective_permissions(
    pool: &PgPool,
    tenant_id: Uuid,
    roles: &[String],
) -> Result<HashSet<String>> {
    let mut permissions = RbacService::new().expand_static(roles);

    let rows: Vec<(String, Vec<String>)> = sqlx::query_as(
        "SELECT name, permissions FROM roles \
         WHERE tenant_id = $1 AND name = ANY($2)",
    )
    .bind(tenant_id)
    .bind(roles)
    .fetch_all(pool)
    .await
    .map_err(|e| {
        SenseiError::Database(format!(
            "Failed to resolve tenant custom role permissions: {e}"
        ))
    })?;

    for (_name, custom_permissions) in rows {
        permissions.extend(custom_permissions);
    }

    Ok(permissions)
}

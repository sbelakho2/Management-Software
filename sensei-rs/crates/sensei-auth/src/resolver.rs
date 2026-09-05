//! Per-request effective-permission resolution (thirtieth-audit P0-9).
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
//! RLS note (thirtieth-audit P0-9): the `roles` table HAS a `tenant_id`
//! column, and the chain-wide hardening migration 098 applies ENABLE +
//! FORCE ROW LEVEL SECURITY with the fail-closed `tenant_isolation`
//! policy to EVERY tenant-owned table (`roles` is not excluded anywhere —
//! migrations 070/079 name explicit table lists, 098 then sweeps every
//! remaining `tenant_id` table). Under the production non-owner
//! `sensei_app` role a raw-pool read WITHOUT the `app.tenant_id` context
//! therefore silently returns ZERO rows — a custom role would vanish from
//! the effective set. The role SELECT therefore runs INSIDE the caller's
//! [`TenantTx`] (whose `SET LOCAL app.tenant_id` admits exactly this
//! tenant), and the tenant comes from the transaction itself — there is
//! no raw-pool form. The explicit `tenant_id = $1` predicate stays as a
//! second barrier.

use sensei_core::db::TenantTx;
use sensei_core::error::{Result, SenseiError};

use crate::rbac::RbacService;

/// Resolve the effective permission set for a principal holding `roles`
/// inside the transaction's tenant.
///
/// Static expansion from the compiled RBAC map/hierarchy is merged with
/// the tenant's custom `roles` rows (a custom role never crosses tenant
/// boundaries — the query is tenant-filtered). Failures are surfaced as
/// [`SenseiError::Database`] so callers can fail closed.
pub async fn resolve_effective_permissions(
    db: &mut TenantTx<'_>,
    roles: &[String],
) -> Result<std::collections::HashSet<String>> {
    let mut permissions = RbacService::new().expand_static(roles);

    let rows: Vec<(String, Vec<String>)> = sqlx::query_as(
        "SELECT name, permissions FROM roles \
         WHERE tenant_id = $1 AND name = ANY($2)",
    )
    .bind(db.tenant_id)
    .bind(roles)
    .fetch_all(&mut **db.tx())
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

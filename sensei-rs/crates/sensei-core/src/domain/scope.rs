//! Typed operational scope (sixteenth audit items 84/6): invalid states are
//! IMPOSSIBLE — a work-center scope always carries its site, and the only
//! way to construct one is the DB-RESOLVED path that proves the work
//! center belongs to the site (`work_centers.site_id`, migration 134).
//! Plain constructors are crate-private: a `WorkCenterScope` value can
//! only exist with the site the database says owns the work center.
use uuid::Uuid;

#[cfg(not(target_arch = "wasm32"))]
use crate::db::TenantTx;

use crate::error::{Result, SenseiError};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct SiteScope {
    pub site: Uuid,
}

impl SiteScope {
    /// Resolve a site scope from the database: returns `None` when the
    /// site does not exist under the transaction's tenant (FORCE RLS
    /// admits only this tenant's sites).
    #[cfg(not(target_arch = "wasm32"))]
    pub async fn resolve(tx: &mut TenantTx<'_>, site: Uuid) -> Result<Option<Self>> {
        let found: Option<Uuid> = sqlx::query_scalar("SELECT id FROM sites WHERE id = $1")
            .bind(site)
            .fetch_optional(&mut **tx.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("scope: site resolve: {e}")))?;
        Ok(found.map(|_| Self { site }))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct WorkCenterScope {
    pub site: Uuid,
    pub work_center: Uuid,
}

impl WorkCenterScope {
    /// DB-RESOLVED construction (seventeenth audit item 6): the parent
    /// site is derived authoritatively from `work_centers.site_id`
    /// (migration 134) under the transaction's tenant RLS. Returns `None`
    /// when the work center does not exist in this tenant.
    #[cfg(not(target_arch = "wasm32"))]
    pub async fn resolve(tx: &mut TenantTx<'_>, work_center: Uuid) -> Result<Option<Self>> {
        let found: Option<Uuid> =
            sqlx::query_scalar("SELECT site_id FROM work_centers WHERE id = $1")
                .bind(work_center)
                .fetch_optional(&mut **tx.tx())
                .await
                .map_err(|e| SenseiError::Database(format!("scope: work-center resolve: {e}")))?;
        Ok(found.map(|site| Self { site, work_center }))
    }

    pub fn allows_site(&self, other: Uuid) -> bool {
        self.site == other
    }
}

/// The caller's effective operational scope (seventeenth audit item 4,
/// eighteenth audit P0-1): ONE type that every resource-touching
/// repository/route enforces. Resolution is DB-derived — the caller
/// cannot widen it.
///
/// - [`AuthorizedScope::NoOperationalScope`]: no active slot assignment
///   exists — the principal has NO entitlement and NO data access. This
///   is the FAIL-CLOSED default: a worker whose assignments disappeared,
///   were corrupted, or never existed gets less privilege, never more.
///   The invariant is: No entitlement → no scope → no data.
/// - [`AuthorizedScope::TenantWide`]: constructed ONLY by the explicit
///   bootstrap/admin path — never by default. `resolve()` never returns
///   it.
/// - [`AuthorizedScope::Sites`]: exactly the sites the principal's active
///   role slots are scoped to.
/// - [`AuthorizedScope::WorkCenter`]: one site + one work center.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum AuthorizedScope {
    NoOperationalScope,
    TenantWide,
    Sites(Vec<Uuid>),
    WorkCenter(WorkCenterScope),
}

impl AuthorizedScope {
    /// EXPLICIT bootstrap/admin construction (eighteenth audit P0-1):
    /// tenant-wide access is a deliberate grant, never an inference from
    /// an empty assignment table.
    pub fn tenant_wide() -> Self {
        Self::TenantWide
    }

    /// Resolve the caller's scope from their ACTIVE role-slot assignments
    /// (role_slots.scope_site_id). FAIL-CLOSED (eighteenth audit P0-1):
    /// a principal with no active assignment resolves to
    /// [`AuthorizedScope::NoOperationalScope`] — absence of an
    /// assignment means NO scope, not tenant-wide privilege.
    #[cfg(not(target_arch = "wasm32"))]
    pub async fn resolve(tx: &mut TenantTx<'_>, principal_id: Uuid) -> Result<Self> {
        let sites: Vec<Uuid> = sqlx::query_scalar(
            "SELECT DISTINCT rs.scope_site_id \
             FROM principal_assignments pa \
             JOIN role_slots rs ON rs.id = pa.slot_id \
             WHERE pa.principal_id = $1 AND pa.ended_at IS NULL \
               AND rs.scope_site_id IS NOT NULL",
        )
        .bind(principal_id)
        .fetch_all(&mut **tx.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("scope: resolve principal: {e}")))?;
        if sites.is_empty() {
            Ok(Self::NoOperationalScope)
        } else {
            Ok(Self::Sites(sites))
        }
    }

    /// Does this scope cover the given site?
    pub fn allows_site(&self, site: Uuid) -> bool {
        match self {
            Self::NoOperationalScope => false,
            Self::TenantWide => true,
            Self::Sites(sites) => sites.contains(&site),
            Self::WorkCenter(wc) => wc.site == site,
        }
    }

    /// Does this scope cover the given work center (site, wc)?
    pub fn allows_work_center(&self, site: Uuid, work_center: Uuid) -> bool {
        match self {
            Self::NoOperationalScope => false,
            Self::TenantWide => true,
            // Eighteenth audit P0-1: a site-level scope covers a work
            // center ONLY when the work center's site is in the vector —
            // the previous `Sites(_) => true` admitted ANY work center.
            Self::Sites(sites) => sites.contains(&site),
            Self::WorkCenter(wc) => wc.site == site && wc.work_center == work_center,
        }
    }

    /// Fail-closed enforcement: the resource's (site, work_center) must be
    /// covered by this scope. Returns a `Forbidden` error otherwise.
    pub fn enforce(&self, site_id: Option<Uuid>, work_center_id: Option<Uuid>) -> Result<()> {
        if matches!(self, Self::NoOperationalScope) {
            return Err(SenseiError::Forbidden(
                "principal has no operational scope — no data is authorized".to_string(),
            ));
        }
        match (site_id, work_center_id) {
            (None, None) => Ok(()), // no resource scope to check
            (Some(_site), Some(_wc)) => {
                if self.allows_work_center(_site, _wc) {
                    Ok(())
                } else {
                    Err(SenseiError::Forbidden(
                        "resource work center is outside the caller's authorized scope".to_string(),
                    ))
                }
            }
            (Some(_site), None) => {
                if self.allows_site(_site) {
                    Ok(())
                } else {
                    Err(SenseiError::Forbidden(
                        "resource site is outside the caller's authorized scope".to_string(),
                    ))
                }
            }
            (None, Some(_wc)) => Err(SenseiError::Forbidden(
                "work-center-scoped resource without a site cannot be authorized".to_string(),
            )),
        }
    }
}

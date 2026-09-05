//! Typed operational scope (sixteenth audit items 84/6; twenty-ninth
//! audit Wave A item 3): invalid states are IMPOSSIBLE — a work-center
//! scope always carries its site, and the only way to construct one is
//! the DB-RESOLVED path that proves the work center belongs to the site
//! (`work_centers.site_id`, migration 134). Plain constructors are
//! crate-private: a `WorkCenterScope` value can only exist with the site
//! the database says owns the work center.
//!
//! Resources are enforced against an EXPLICIT [`ResourceScope`]: every
//! resource-touching call declares exactly what it is touching
//! (`Tenant` / `Site` / `WorkCenter`), and [`ResourceScope::Unresolved`]
//! fails closed for every scope — the old `(None, None)` "no resource
//! scope to check" allowance is gone.
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

/// What a resource claims to be (twenty-ninth audit Wave A item 3): the
/// RESOURCE side of the enforcement decision. Every resource-touching
/// call must declare EXACTLY what it is touching — there is no
/// `(None, None)`-means-allow ambiguity anymore:
///
/// - [`ResourceScope::Tenant`]: a tenant-level object with no site
///   dimension (a deliberate, well-formed claim).
/// - [`ResourceScope::Site`]: an object anchored to one site.
/// - [`ResourceScope::WorkCenter`]: an object anchored to one work
///   center (which always carries its site).
/// - [`ResourceScope::Unresolved`]: the resource's scope could not be
///   established — FAIL-CLOSED, always Forbidden (even for a
///   tenant-wide caller).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum ResourceScope {
    Tenant,
    Site { site: Uuid },
    WorkCenter { site: Uuid, work_center: Uuid },
    Unresolved,
}

/// The caller's effective operational scope (seventeenth audit item 4,
/// eighteenth audit P0-1; thirtieth-audit P0 item 1): ONE type that every
/// resource-touching repository/route enforces. Resolution is DB-derived —
/// the caller cannot widen it.
///
/// - [`AuthorizedScope::NoOperationalScope`]: no active slot assignment
///   (or only `scope_kind = 'none'` slots) exists — the principal has NO
///   entitlement and NO data access. This is the FAIL-CLOSED default: a
///   worker whose assignments disappeared, were corrupted, or never
///   existed gets less privilege, never more. The invariant is: No
///   entitlement → no scope → no data.
/// - [`AuthorizedScope::TenantWide`]: constructed by the EXPLICIT
///   bootstrap/admin path OR resolved from an ACTIVE role slot with
///   `scope_kind = 'tenant'` — never by default.
/// - [`AuthorizedScope::Operational`]: the union of the principal's
///   site grants (`scope_kind = 'site'` → `sites`) and exact work-center
///   grants (`scope_kind = 'work_center'` → `work_centers`, each carrying
///   its DB-derived site). Work centers are NEVER normalized into their
///   site — a WC slot grants exactly that work center, and a site grant
///   covers every work center of the site. A pure work-center principal
///   has an EMPTY `sites` set: their `work_centers` set carries the real
///   scope.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum AuthorizedScope {
    NoOperationalScope,
    TenantWide,
    Operational {
        sites: std::collections::HashSet<Uuid>,
        work_centers: std::collections::HashSet<WorkCenterScope>,
    },
}

impl AuthorizedScope {
    /// EXPLICIT bootstrap/admin construction (eighteenth audit P0-1):
    /// tenant-wide access is a deliberate grant, never an inference from
    /// an empty assignment table.
    pub fn tenant_wide() -> Self {
        Self::TenantWide
    }

    /// Resolve the caller's scope from their ACTIVE role-slot assignments
    /// reading ALL of `role_slots.scope_kind` / `scope_site_id` /
    /// `scope_work_center_id` (thirtieth-audit P0 item 1 — the previous
    /// `scope_site_id`-only resolution made tenant slots vanish and
    /// widened work-center slots to their whole site). FAIL-CLOSED
    /// (eighteenth audit P0-1): a principal with no active assignment
    /// resolves to [`AuthorizedScope::NoOperationalScope`] — absence of
    /// an assignment means NO scope, not tenant-wide privilege.
    ///
    /// Semantics:
    /// - any slot with `scope_kind = 'tenant'` ⇒ [`Self::TenantWide`];
    /// - no active slots ⇒ [`Self::NoOperationalScope`];
    /// - `scope_kind = 'site'` ⇒ the site joins `sites`;
    /// - `scope_kind = 'work_center'` ⇒ its (site, work center) pair
    ///   joins `work_centers` — NEVER normalized into `sites`;
    /// - `scope_kind = 'none'` is ignored — and a principal with ONLY
    ///   `'none'` slots resolves to [`Self::NoOperationalScope`] (fail
    ///   closed preserved).
    #[cfg(not(target_arch = "wasm32"))]
    pub async fn resolve(tx: &mut TenantTx<'_>, principal_id: Uuid) -> Result<Self> {
        type SlotRow = (String, Option<Uuid>, Option<Uuid>);
        let slots: Vec<SlotRow> = sqlx::query_as(
            "SELECT rs.scope_kind, rs.scope_site_id, rs.scope_work_center_id \
             FROM principal_assignments pa \
             JOIN role_slots rs ON rs.id = pa.slot_id \
             WHERE pa.principal_id = $1 AND pa.ended_at IS NULL",
        )
        .bind(principal_id)
        .fetch_all(&mut **tx.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("scope: resolve principal: {e}")))?;
        if slots.is_empty() {
            return Ok(Self::NoOperationalScope);
        }
        for (kind, _, _) in &slots {
            if kind == "tenant" {
                return Ok(Self::TenantWide);
            }
        }
        let mut sites = std::collections::HashSet::new();
        let mut work_centers = std::collections::HashSet::new();
        for (kind, site, work_center) in slots {
            match kind.as_str() {
                "site" => {
                    if let Some(site) = site {
                        sites.insert(site);
                    }
                }
                "work_center" => {
                    if let (Some(site), Some(work_center)) = (site, work_center) {
                        work_centers.insert(WorkCenterScope { site, work_center });
                    }
                }
                // 'none' slots carry no scope ids; 'tenant' is handled
                // above. Neither contributes to the union.
                _ => {}
            }
        }
        if sites.is_empty() && work_centers.is_empty() {
            Ok(Self::NoOperationalScope)
        } else {
            Ok(Self::Operational {
                sites,
                work_centers,
            })
        }
    }

    /// Does this scope cover the given site? (Thirtieth-audit P0 item 1:
    /// only SITE grants cover sites — a work-center grant covers its
    /// exact work center, never the whole site.)
    pub fn allows_site(&self, site: Uuid) -> bool {
        match self {
            Self::NoOperationalScope => false,
            Self::TenantWide => true,
            Self::Operational { sites, .. } => sites.contains(&site),
        }
    }

    /// Does this scope cover the given work center (site, wc)? A
    /// work-center grant allows ONLY its exact (site, wc) pair; a site
    /// grant covers every work center of that site.
    pub fn allows_work_center(&self, site: Uuid, work_center: Uuid) -> bool {
        match self {
            Self::NoOperationalScope => false,
            Self::TenantWide => true,
            // Eighteenth audit P0-1: a site-level scope covers a work
            // center ONLY when the work center's site is in the set —
            // the previous `Sites(_) => true` admitted ANY work center.
            Self::Operational {
                sites,
                work_centers,
            } => {
                sites.contains(&site)
                    || work_centers
                        .iter()
                        .any(|wc| wc.site == site && wc.work_center == work_center)
            }
        }
    }

    /// Fail-closed resource enforcement (twenty-ninth audit Wave A
    /// item 3; thirtieth-audit P0 item 1): the resource's EXPLICIT
    /// [`ResourceScope`] must be covered by this scope. Returns a
    /// `Forbidden` error otherwise.
    ///
    /// Exact semantics:
    ///
    /// | caller scope \ resource | `Tenant` | `Site { site }` | `WorkCenter { site, wc }` | `Unresolved` |
    /// |---|---|---|---|---|
    /// | `NoOperationalScope` | Forbidden | Forbidden | Forbidden | Forbidden |
    /// | `TenantWide` | allowed | allowed | allowed | Forbidden |
    /// | `Operational { sites, work_centers }` | Forbidden | allowed iff `site ∈ sites` | allowed iff `site ∈ sites` OR exact match (`(site, wc) ∈ work_centers`) | Forbidden |
    ///
    /// A work-center grant NEVER widens into its site: a pure
    /// work-center caller (`sites = ∅`) is Forbidden on `Site` and
    /// on every work-center resource but its exact pair(s).
    ///
    /// [`ResourceScope::Unresolved`] is Forbidden ALWAYS — a resource
    /// whose scope cannot be established is never authorized, not even
    /// for a tenant-wide caller (no magical absence-allow).
    pub fn enforce_resource(&self, resource: &ResourceScope) -> Result<()> {
        match resource {
            ResourceScope::Unresolved => Err(SenseiError::Forbidden(
                "resource scope is unresolved — no data is authorized".to_string(),
            )),
            ResourceScope::Tenant => match self {
                Self::TenantWide => Ok(()),
                _ => Err(SenseiError::Forbidden(
                    "a tenant-level resource is outside the caller's authorized scope".to_string(),
                )),
            },
            ResourceScope::Site { site } => {
                if self.allows_site(*site) {
                    Ok(())
                } else {
                    Err(SenseiError::Forbidden(
                        "resource site is outside the caller's authorized scope".to_string(),
                    ))
                }
            }
            ResourceScope::WorkCenter { site, work_center } => {
                if self.allows_work_center(*site, *work_center) {
                    Ok(())
                } else {
                    Err(SenseiError::Forbidden(
                        "resource work center is outside the caller's authorized scope".to_string(),
                    ))
                }
            }
        }
    }

    /// Deprecated legacy form — call [`Self::enforce_resource`] with an
    /// explicit [`ResourceScope`] instead. Semantics are FIXED
    /// (twenty-ninth audit Wave A item 3): the old `(None, None)`
    /// "no resource scope to check" allowance is gone.
    ///
    /// - `NoOperationalScope` — Forbidden ALWAYS.
    /// - `(None, None)` — a tenant-level resource: Ok ONLY for
    ///   `TenantWide` (the sole scope a site-less claim may not widen);
    ///   `Operational` is Forbidden.
    /// - `(Some(site), None)` — a site resource: `allows_site(site)`.
    /// - `(Some(site), Some(wc))` — a work-center resource:
    ///   `allows_work_center(site, wc)`.
    /// - `(None, Some(_))` — an inconsistent, site-less work-center
    ///   claim: Forbidden ALWAYS (maps to `ResourceScope::Unresolved`).
    #[deprecated(note = "call enforce_resource with an explicit ResourceScope instead")]
    pub fn enforce(&self, site_id: Option<Uuid>, work_center_id: Option<Uuid>) -> Result<()> {
        let resource = match (site_id, work_center_id) {
            (None, None) => ResourceScope::Tenant,
            (Some(site), None) => ResourceScope::Site { site },
            (Some(site), Some(work_center)) => ResourceScope::WorkCenter { site, work_center },
            (None, Some(_)) => ResourceScope::Unresolved,
        };
        self.enforce_resource(&resource)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn no_scope() -> AuthorizedScope {
        AuthorizedScope::NoOperationalScope
    }
    fn tenant_wide() -> AuthorizedScope {
        AuthorizedScope::tenant_wide()
    }
    fn sites(site_a: Uuid, site_b: Uuid) -> AuthorizedScope {
        AuthorizedScope::Operational {
            sites: HashSet::from([site_a, site_b]),
            work_centers: HashSet::new(),
        }
    }
    fn work_center(site: Uuid, wc: Uuid) -> AuthorizedScope {
        AuthorizedScope::Operational {
            sites: HashSet::new(),
            work_centers: HashSet::from([WorkCenterScope {
                site,
                work_center: wc,
            }]),
        }
    }

    fn ok(scope: &AuthorizedScope, resource: &ResourceScope) -> bool {
        scope.enforce_resource(resource).is_ok()
    }

    #[test]
    fn enforce_resource_unresolved_is_forbidden_for_every_scope() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        for scope in [
            no_scope(),
            tenant_wide(),
            sites(site, Uuid::new_v4()),
            work_center(site, wc),
        ] {
            assert!(
                scope.enforce_resource(&ResourceScope::Unresolved).is_err(),
                "Unresolved must be Forbidden for {scope:?}"
            );
        }
    }

    #[test]
    fn enforce_resource_no_operational_scope_forbids_every_resource() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let scope = no_scope();
        for resource in [
            ResourceScope::Tenant,
            ResourceScope::Site { site },
            ResourceScope::WorkCenter {
                site,
                work_center: wc,
            },
            ResourceScope::Unresolved,
        ] {
            assert!(
                scope.enforce_resource(&resource).is_err(),
                "NoOperationalScope must forbid {resource:?}"
            );
        }
    }

    #[test]
    fn enforce_resource_tenant_wide_allows_every_well_formed_resource() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let scope = tenant_wide();
        assert!(ok(&scope, &ResourceScope::Tenant));
        assert!(ok(&scope, &ResourceScope::Site { site }));
        assert!(ok(
            &scope,
            &ResourceScope::WorkCenter {
                site,
                work_center: wc
            }
        ));
        assert!(scope.enforce_resource(&ResourceScope::Unresolved).is_err());
    }

    #[test]
    fn enforce_resource_sites_allows_site_and_work_center_of_its_sites_only() {
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let foreign = Uuid::new_v4();
        let wc_a = Uuid::new_v4();
        let scope = sites(site_a, site_b);

        // Tenant-level resource: only a tenant-wide grant reaches it.
        assert!(scope.enforce_resource(&ResourceScope::Tenant).is_err());

        assert!(ok(&scope, &ResourceScope::Site { site: site_a }));
        assert!(ok(&scope, &ResourceScope::Site { site: site_b }));
        assert!(!ok(&scope, &ResourceScope::Site { site: foreign }));

        assert!(ok(
            &scope,
            &ResourceScope::WorkCenter {
                site: site_a,
                work_center: wc_a,
            }
        ));
        assert!(!ok(
            &scope,
            &ResourceScope::WorkCenter {
                site: foreign,
                work_center: wc_a,
            }
        ));
    }

    #[test]
    fn enforce_resource_work_center_allows_only_the_exact_match() {
        let site_a = Uuid::new_v4();
        let foreign_site = Uuid::new_v4();
        let wc_a = Uuid::new_v4();
        let foreign_wc = Uuid::new_v4();
        let scope = work_center(site_a, wc_a);

        // Tenant-level resource: only a tenant-wide grant reaches it.
        assert!(scope.enforce_resource(&ResourceScope::Tenant).is_err());

        // Site resource: a work-center grant never widens into its site
        // (thirtieth-audit P0 item 1) — Forbidden even for wc's own site.
        assert!(!ok(&scope, &ResourceScope::Site { site: site_a }));
        assert!(!ok(&scope, &ResourceScope::Site { site: foreign_site }));

        // Work-center resource: EXACT match only.
        assert!(ok(
            &scope,
            &ResourceScope::WorkCenter {
                site: site_a,
                work_center: wc_a,
            }
        ));
        assert!(!ok(
            &scope,
            &ResourceScope::WorkCenter {
                site: site_a,
                work_center: foreign_wc,
            }
        ));
        assert!(!ok(
            &scope,
            &ResourceScope::WorkCenter {
                site: foreign_site,
                work_center: wc_a,
            }
        ));
    }

    #[test]
    fn enforce_full_matrix() {
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let wc_a = Uuid::new_v4();
        let wc_b = Uuid::new_v4();
        let resources = [
            ResourceScope::Tenant,
            ResourceScope::Site { site: site_a },
            ResourceScope::Site { site: site_b },
            ResourceScope::WorkCenter {
                site: site_a,
                work_center: wc_a,
            },
            ResourceScope::WorkCenter {
                site: site_a,
                work_center: wc_b,
            },
            ResourceScope::Unresolved,
        ];
        // Per-scope expectations over `resources` (scope order below).
        let cases = [
            (no_scope(), [false, false, false, false, false, false]),
            (tenant_wide(), [true, true, true, true, true, false]),
            (
                sites(site_a, site_b),
                [false, true, true, true, true, false],
            ),
            // A work-center scope allows its exact pair only — never the
            // site resource, never a sibling work center (P0 item 1).
            (
                work_center(site_a, wc_a),
                [false, false, false, true, false, false],
            ),
        ];
        for (scope, expected) in cases {
            for (resource, expect_ok) in resources.iter().zip(expected) {
                assert_eq!(
                    ok(&scope, resource),
                    expect_ok,
                    "scope {scope:?} vs resource {resource:?}"
                );
            }
        }
    }

    #[test]
    #[allow(deprecated)]
    fn deprecated_enforce_none_none_is_ok_only_for_tenant_wide() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        assert!(tenant_wide().enforce(None, None).is_ok());
        assert!(no_scope().enforce(None, None).is_err());
        assert!(sites(site, Uuid::new_v4()).enforce(None, None).is_err());
        assert!(work_center(site, wc).enforce(None, None).is_err());
    }

    #[test]
    #[allow(deprecated)]
    fn deprecated_enforce_no_operational_scope_is_forbidden_always() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let scope = no_scope();
        for args in [
            (None, None),
            (Some(site), None),
            (None, Some(wc)),
            (Some(site), Some(wc)),
        ] {
            assert!(scope.enforce(args.0, args.1).is_err(), "args {args:?}");
        }
    }

    #[test]
    #[allow(deprecated)]
    fn deprecated_enforce_none_some_is_forbidden_always() {
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        // An inconsistent site-less work-center claim never passes — not
        // even for a tenant-wide caller.
        for scope in [
            no_scope(),
            tenant_wide(),
            sites(site, Uuid::new_v4()),
            work_center(site, wc),
        ] {
            assert!(scope.enforce(None, Some(wc)).is_err(), "scope {scope:?}");
        }
    }

    #[test]
    #[allow(deprecated)]
    fn deprecated_enforce_site_arms_keep_scope_coverage() {
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let wc_a = Uuid::new_v4();
        assert!(sites(site_a, site_b).enforce(Some(site_a), None).is_ok());
        assert!(sites(site_a, site_b)
            .enforce(Some(site_b), Some(wc_a))
            .is_ok());
        assert!(sites(site_a, site_b)
            .enforce(Some(Uuid::new_v4()), None)
            .is_err());
        // A pure work-center scope covers its exact pair, never the site
        // arm (thirtieth-audit P0 item 1 — no whole-site widening).
        assert!(work_center(site_a, wc_a)
            .enforce(Some(site_a), None)
            .is_err());
        assert!(work_center(site_a, wc_a)
            .enforce(Some(site_a), Some(wc_a))
            .is_ok());
        assert!(work_center(site_a, wc_a)
            .enforce(Some(site_a), Some(Uuid::new_v4()))
            .is_err());
        assert!(work_center(site_a, wc_a)
            .enforce(Some(site_b), Some(wc_a))
            .is_err());
        assert!(tenant_wide().enforce(Some(site_a), Some(wc_a)).is_ok());
        assert!(no_scope().enforce(Some(site_a), Some(wc_a)).is_err());
    }

    #[test]
    fn mixed_site_and_work_center_grants_union_exactly() {
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let wc_b1 = Uuid::new_v4();
        let wc_b2 = Uuid::new_v4();
        let scope = AuthorizedScope::Operational {
            sites: HashSet::from([site_a]),
            work_centers: HashSet::from([WorkCenterScope {
                site: site_b,
                work_center: wc_b1,
            }]),
        };
        // The site grant covers the whole site (any of its work centers).
        assert!(scope.allows_site(site_a));
        assert!(
            !scope.allows_site(site_b),
            "WC grant never widens to site B"
        );
        assert!(scope.allows_work_center(site_a, Uuid::new_v4()));
        // The work-center grant covers exactly (site_b, wc_b1).
        assert!(scope.allows_work_center(site_b, wc_b1));
        assert!(!scope.allows_work_center(site_b, wc_b2));
    }
}

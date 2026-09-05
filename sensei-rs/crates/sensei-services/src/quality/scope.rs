//! Creation-scope derivation and SQL scope predicates for the quality
//! resource family (thirtieth-audit P0 items 7-8).
//!
//! # Derivation (`derive_creation_scope`)
//!
//! ONE helper — not one per constructor — turns the caller's validated
//! [`RequestContext`] (and an optional resolved parent anchor) into the
//! [`ResourceScope`] a NEW quality record is stamped with. Missing
//! narrower context NEVER widens authority:
//!
//! | caller | focus | result |
//! |---|---|---|
//! | `TenantWide` | none | `Tenant` (corporate record; both scope columns NULL) |
//! | `TenantWide` | site A | `Site { A }` |
//! | `TenantWide` | site A + WC A1 | `WorkCenter { A, A1 }` |
//! | `Operational { sites: [A, B] }` | site A | `Site { A }` (the focus site must be an actual SITE grant) |
//! | `Operational { sites: [A, B] }` | site A + WC A1 | `WorkCenter { A, A1 }` (the row is narrower than the grant, never broader) |
//! | `Operational { sites: [A, B] }` | none | **rejected** — an operating site is required; a site-less focus must NOT silently become a corporate record |
//! | `Operational { work_centers: [WC A1] }` (exact WC) | site A + WC A1 | `WorkCenter { A, A1 }` |
//! | `Operational { work_centers: [WC A1] }` | anything else / nothing | **rejected** — a WC grant never widens into its site |
//! | `NoOperationalScope` | any | **rejected** (no entitlement → no creation) |
//!
//! A parent anchor (an NCR raised against a work order whose real
//! (site, work center) pair was resolved in the same transaction) wins
//! over the focus: the record belongs to the parent, and the derived
//! scope is enforced against the caller's scope — a parent NEVER widens
//! authority.
//!
//! # SQL predicates (`quality_scope_predicate`)
//!
//! The SQL counterpart reads the SERVER-STAMPED scope columns of the
//! canonical relational tables (`scope_site_id` / `scope_work_center_id`,
//! migration 170):
//!
//! * `TenantWide` — no predicate (corporate NULL-scope rows included);
//! * `Operational { sites, work_centers }` — `scope_site_id = ANY($n)`
//!   for the site grants UNION `scope_site_id = $m AND
//!   scope_work_center_id = $m+1` per EXACT work-center grant. A
//!   work-center grant matches exactly the records stamped at that work
//!   center — never the whole site's records and never a site-level
//!   (work-center-less) record; a site grant covers every stamped record
//!   of the site (site-level and work-center-level alike);
//! * anything else — an impossible predicate: zero rows (fail closed).
//!
//! A corporate record (both columns NULL) never matches any predicate —
//! only the explicit tenant-wide grant (no predicate) reaches it.

use sensei_core::domain::request_context::RequestContext;
use sensei_core::domain::scope::{AuthorizedScope, ResourceScope, WorkCenterScope};
use sensei_core::error::{Result, SenseiError};
use uuid::Uuid;

use super::models::QualityScopeStamp;

/// A canonical parent anchor a new quality record is raised against. The
/// anchor is DB-RESOLVED (the parent row's real work center and the work
/// center's real site, resolved in the same transaction as the insert) —
/// never client input.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CanonicalParent {
    /// The record was raised against a work order whose carrier work
    /// center exists on `site_id` (work_centers.site_id, migration 134).
    WorkOrder { site_id: Uuid, work_center_id: Uuid },
}

impl CanonicalParent {
    /// The resource claim of the parent anchor.
    pub fn resource_scope(&self) -> ResourceScope {
        match *self {
            CanonicalParent::WorkOrder {
                site_id,
                work_center_id,
            } => ResourceScope::WorkCenter {
                site: site_id,
                work_center: work_center_id,
            },
        }
    }
}

/// Derive the creation scope of a NEW quality record from the caller's
/// validated operating focus and an optional resolved parent anchor.
///
/// Exact rules (thirtieth-audit P0 item 8 — missing focus must never
/// widen authority into a corporate/tenant-level record):
///
/// * `parent` present — the record belongs to the parent anchor; the
///   parent's scope is enforced against the caller's scope (a parent
///   never widens authority) and returned;
/// * `TenantWide` + no focus — `Tenant` (the only corporate creation
///   path);
/// * `TenantWide` + site focus — `Site`;
/// * `TenantWide` + (site, WC) focus — `WorkCenter`;
/// * `Operational` + site focus in `sites` — `Site` (a WC-grant holder
///   never creates a site-level record: the focus site must be an actual
///   SITE grant);
/// * `Operational` + (site, WC) focus covered by `sites` or an exact
///   granted work center — `WorkCenter`;
/// * `Operational` + NO focus — `Forbidden` (an operating site is
///   required; a site-less record must not silently become corporate);
/// * `NoOperationalScope` — `Forbidden`.
pub fn derive_creation_scope(
    ctx: &RequestContext,
    parent: Option<CanonicalParent>,
) -> Result<ResourceScope> {
    if let Some(parent) = parent {
        let resource = parent.resource_scope();
        ctx.scope.enforce_resource(&resource)?;
        return Ok(resource);
    }
    match &ctx.scope {
        AuthorizedScope::NoOperationalScope => Err(SenseiError::Forbidden(
            "principal has no operational scope — cannot create a quality record".to_string(),
        )),
        AuthorizedScope::TenantWide => match (ctx.focus.site, ctx.focus.work_center) {
            (None, None) => Ok(ResourceScope::Tenant),
            (Some(site), None) => Ok(ResourceScope::Site { site }),
            (Some(site), Some(work_center)) => Ok(ResourceScope::WorkCenter { site, work_center }),
            // A work-center focus without a site focus is unrepresentable
            // (the context builder rejects it; belt-and-braces here).
            (None, Some(_)) => Err(SenseiError::Forbidden(
                "a work-center operating focus without an operating site is unrepresentable — \
                 cannot create a quality record"
                    .to_string(),
            )),
        },
        AuthorizedScope::Operational {
            sites,
            work_centers,
        } => match (ctx.focus.site, ctx.focus.work_center) {
            (None, None) => Err(SenseiError::Forbidden(
                "an operating site is required to create a quality record — a missing focus \
                 must never widen a scoped caller into a corporate record"
                    .to_string(),
            )),
            (Some(site), None) => {
                if sites.contains(&site) {
                    Ok(ResourceScope::Site { site })
                } else {
                    Err(SenseiError::Forbidden(format!(
                        "operating site {site} is not among the principal's site grants — a \
                         work-center grant never widens into site-level creation"
                    )))
                }
            }
            (Some(site), Some(work_center)) => {
                let exact = WorkCenterScope { site, work_center };
                if sites.contains(&site) || work_centers.contains(&exact) {
                    Ok(ResourceScope::WorkCenter { site, work_center })
                } else {
                    Err(SenseiError::Forbidden(format!(
                        "operating work center ({site}, {work_center}) is outside the \
                         principal's authorized scope"
                    )))
                }
            }
            (None, Some(_)) => Err(SenseiError::Forbidden(
                "a work-center operating focus without an operating site is unrepresentable — \
                 cannot create a quality record"
                    .to_string(),
            )),
        },
    }
}

/// The row-level stamp of a derived creation scope: `Tenant` is the
/// honest corporate encoding (both columns NULL), `Site` stamps the
/// site column only, `WorkCenter` stamps both columns.
pub fn stamp_from_scope(scope: ResourceScope) -> QualityScopeStamp {
    match scope {
        ResourceScope::Tenant => QualityScopeStamp {
            site_id: None,
            work_center_id: None,
        },
        ResourceScope::Site { site } => QualityScopeStamp {
            site_id: Some(site),
            work_center_id: None,
        },
        ResourceScope::WorkCenter { site, work_center } => QualityScopeStamp {
            site_id: Some(site),
            work_center_id: Some(work_center),
        },
        ResourceScope::Unresolved => QualityScopeStamp {
            site_id: None,
            work_center_id: None,
        },
    }
}

/// The bind values of a quality SQL scope predicate: the authorized SITE
/// set (sorted; empty when the caller holds no site grant) and the EXACT
/// work-center grants as a sorted, flattened `(site, work_center)` list.
///
/// Binding order contract for the statements built by
/// [`quality_scope_predicate`]: bind the `sites` vector as ONE `uuid[]`
/// value first, then one scalar `(site, work_center)` pair per entry of
/// `work_centers`, in list order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QualityScopeBind {
    pub sites: Vec<Uuid>,
    pub work_centers: Vec<(Uuid, Uuid)>,
}

/// Build the SQL scope predicate over a quality table's server-stamped
/// scope columns (`alias.scope_site_id` / `alias.scope_work_center_id`).
///
/// Returns `(sql_fragment, bind)`: `sql_fragment` starts with `AND ` (or
/// is empty for the tenant-wide grant) and references placeholders from
/// `slot` upwards; `bind` is `None` when no placeholder needs binding.
/// See [`QualityScopeBind`] for the binding order.
pub fn quality_scope_predicate(
    ctx: &RequestContext,
    alias: &str,
    slot: usize,
) -> (String, Option<QualityScopeBind>) {
    match &ctx.scope {
        AuthorizedScope::TenantWide => (String::new(), None),
        AuthorizedScope::NoOperationalScope => ("AND FALSE".to_string(), None),
        AuthorizedScope::Operational {
            sites,
            work_centers,
        } => {
            let mut site_list: Vec<Uuid> = sites.iter().copied().collect();
            site_list.sort_unstable();
            let mut wc_list: Vec<(Uuid, Uuid)> = work_centers
                .iter()
                .map(|wc: &WorkCenterScope| (wc.site, wc.work_center))
                .collect();
            wc_list.sort_unstable();
            if site_list.is_empty() && wc_list.is_empty() {
                return ("AND FALSE".to_string(), None);
            }
            let mut parts = Vec::new();
            let mut next = slot;
            if !site_list.is_empty() {
                parts.push(format!("{alias}.scope_site_id = ANY(${next})"));
                next += 1;
            }
            for _ in &wc_list {
                parts.push(format!(
                    "{alias}.scope_site_id = ${next} AND {alias}.scope_work_center_id = ${}",
                    next + 1
                ));
                next += 2;
            }
            let predicate = if parts.len() == 1 {
                parts.pop().expect("at least one part above")
            } else {
                format!("({})", parts.join(" OR "))
            };
            (
                format!("AND {predicate}"),
                Some(QualityScopeBind {
                    sites: site_list,
                    work_centers: wc_list,
                }),
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_core::domain::request_context::OperationalFocus;
    use std::collections::HashSet;

    fn tenant_wide(tenant: Uuid) -> RequestContext {
        RequestContext {
            tenant,
            principal: Uuid::new_v4(),
            scope: AuthorizedScope::tenant_wide(),
            focus: OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }
    }

    fn with_focus(ctx: RequestContext, site: Option<Uuid>, wc: Option<Uuid>) -> RequestContext {
        RequestContext {
            focus: OperationalFocus {
                site,
                value_stream: None,
                work_center: wc,
                shift: None,
            },
            ..ctx
        }
    }

    fn sites(tenant: Uuid, granted: &[Uuid]) -> RequestContext {
        RequestContext {
            tenant,
            principal: Uuid::new_v4(),
            scope: AuthorizedScope::Operational {
                sites: granted.iter().copied().collect(),
                work_centers: HashSet::new(),
            },
            focus: OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }
    }

    fn exact_wc(tenant: Uuid, site: Uuid, wc: Uuid) -> RequestContext {
        RequestContext {
            tenant,
            principal: Uuid::new_v4(),
            scope: AuthorizedScope::Operational {
                sites: HashSet::new(),
                work_centers: HashSet::from([WorkCenterScope {
                    site,
                    work_center: wc,
                }]),
            },
            focus: OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }
    }

    fn assert_scope(err: Result<ResourceScope>) -> ResourceScope {
        err.expect("derivation must succeed")
    }

    #[test]
    fn tenant_wide_no_focus_is_corporate() {
        let tenant = Uuid::new_v4();
        assert_eq!(
            assert_scope(derive_creation_scope(&tenant_wide(tenant), None)),
            ResourceScope::Tenant
        );
    }

    #[test]
    fn tenant_wide_with_site_focus_stamps_site() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        assert_eq!(
            assert_scope(derive_creation_scope(
                &with_focus(tenant_wide(tenant), Some(site), None),
                None
            )),
            ResourceScope::Site { site }
        );
    }

    #[test]
    fn tenant_wide_with_work_center_focus_stamps_work_center() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        assert_eq!(
            assert_scope(derive_creation_scope(
                &with_focus(tenant_wide(tenant), Some(site), Some(wc)),
                None
            )),
            ResourceScope::WorkCenter {
                site,
                work_center: wc
            }
        );
    }

    #[test]
    fn site_scope_without_focus_is_rejected() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let err = derive_creation_scope(&sites(tenant, &[site]), None).unwrap_err();
        assert!(
            matches!(err, SenseiError::Forbidden(_)),
            "sites-only + no focus must be rejected, got {err:?}"
        );
        assert!(
            !sites(tenant, &[site])
                .scope
                .enforce_resource(&ResourceScope::Tenant)
                .is_ok(),
            "sites-only must not reach a corporate record"
        );
    }

    #[test]
    fn site_scope_with_focus_stamps_site() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let other = Uuid::new_v4();
        assert_eq!(
            assert_scope(derive_creation_scope(
                &with_focus(sites(tenant, &[site, other]), Some(site), None),
                None
            )),
            ResourceScope::Site { site }
        );
        // A focus outside the grants is rejected even for TenantWide-less scopes.
        let foreign = Uuid::new_v4();
        assert!(derive_creation_scope(
            &with_focus(sites(tenant, &[site]), Some(foreign), None),
            None
        )
        .is_err());
    }

    #[test]
    fn exact_work_center_grant_stamps_exact_work_center_only() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let wc_a1 = Uuid::new_v4();
        let wc_a2 = Uuid::new_v4();
        let ctx = with_focus(exact_wc(tenant, site, wc_a1), Some(site), Some(wc_a1));
        assert_eq!(
            assert_scope(derive_creation_scope(&ctx, None)),
            ResourceScope::WorkCenter {
                site,
                work_center: wc_a1
            }
        );
        // The same grant holder focusing a sibling work center is rejected.
        let sibling = with_focus(exact_wc(tenant, site, wc_a1), Some(site), Some(wc_a2));
        assert!(derive_creation_scope(&sibling, None).is_err());
        // A WC grant never creates a site-level record.
        let site_only = with_focus(exact_wc(tenant, site, wc_a1), Some(site), None);
        assert!(derive_creation_scope(&site_only, None).is_err());
        // A WC grant without any focus is rejected.
        assert!(derive_creation_scope(&exact_wc(tenant, site, wc_a1), None).is_err());
    }

    #[test]
    fn no_operational_scope_is_rejected() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let no_scope = RequestContext {
            scope: AuthorizedScope::NoOperationalScope,
            ..with_focus(tenant_wide(tenant), Some(site), None)
        };
        assert!(derive_creation_scope(&no_scope, None).is_err());
    }

    #[test]
    fn work_order_parent_derives_and_verifies() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let wc_a1 = Uuid::new_v4();
        let parent = CanonicalParent::WorkOrder {
            site_id: site,
            work_center_id: wc_a1,
        };
        // A site-grant holder may raise against a WO of its site.
        assert_eq!(
            assert_scope(derive_creation_scope(
                &with_focus(sites(tenant, &[site]), Some(site), None),
                Some(parent)
            )),
            ResourceScope::WorkCenter {
                site,
                work_center: wc_a1
            }
        );
        // An exact WC-A1 holder may raise against its own WO.
        assert_eq!(
            assert_scope(derive_creation_scope(
                &with_focus(exact_wc(tenant, site, wc_a1), Some(site), Some(wc_a1)),
                Some(parent)
            )),
            ResourceScope::WorkCenter {
                site,
                work_center: wc_a1
            }
        );
        // A WC-A2 holder may NOT raise against a WO at WC A1 — a parent
        // never widens authority.
        let wc_a2 = Uuid::new_v4();
        assert!(derive_creation_scope(
            &with_focus(exact_wc(tenant, site, wc_a2), Some(site), Some(wc_a2)),
            Some(parent)
        )
        .is_err());
        // A foreign-site caller may not either.
        let foreign = Uuid::new_v4();
        assert!(derive_creation_scope(
            &with_focus(sites(tenant, &[foreign]), Some(foreign), None),
            Some(parent)
        )
        .is_err());
        // Tenant-wide with no focus still derives the parent anchor.
        assert_eq!(
            assert_scope(derive_creation_scope(&tenant_wide(tenant), Some(parent))),
            ResourceScope::WorkCenter {
                site,
                work_center: wc_a1
            }
        );
    }

    #[test]
    fn predicate_binds_sites_and_exact_work_centers() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let wc_a1 = Uuid::new_v4();
        let ctx = RequestContext {
            scope: AuthorizedScope::Operational {
                sites: HashSet::from([site]),
                work_centers: HashSet::from([WorkCenterScope {
                    site,
                    work_center: wc_a1,
                }]),
            },
            ..tenant_wide(tenant)
        };
        let (sql, bind) = quality_scope_predicate(&ctx, "q", 4);
        assert!(sql.starts_with("AND (q.scope_site_id = ANY($4)"));
        assert!(sql.contains("q.scope_site_id = $5 AND q.scope_work_center_id = $6"));
        let bind = bind.expect("binds present");
        assert_eq!(bind.sites, vec![site]);
        assert_eq!(bind.work_centers, vec![(site, wc_a1)]);
    }

    #[test]
    fn predicate_is_exact_for_work_center_only_scopes() {
        let tenant = Uuid::new_v4();
        let site = Uuid::new_v4();
        let wc = Uuid::new_v4();
        let ctx = exact_wc(tenant, site, wc);
        let (sql, bind) = quality_scope_predicate(&ctx, "q", 2);
        assert!(bind.is_some());
        assert_eq!(
            sql,
            format!("AND q.scope_site_id = $2 AND q.scope_work_center_id = $3")
        );
        let bind = bind.expect("binds");
        assert!(bind.sites.is_empty(), "a WC-only scope binds NO site set");
        assert_eq!(bind.work_centers, vec![(site, wc)]);
    }

    #[test]
    fn predicate_tenant_wide_and_fail_closed() {
        let tenant = Uuid::new_v4();
        let (sql, bind) = quality_scope_predicate(&tenant_wide(tenant), "q", 1);
        assert!(sql.is_empty());
        assert!(bind.is_none());
        let no_scope = RequestContext {
            scope: AuthorizedScope::NoOperationalScope,
            ..tenant_wide(tenant)
        };
        let (sql, bind) = quality_scope_predicate(&no_scope, "q", 1);
        assert_eq!(sql, "AND FALSE");
        assert!(bind.is_none());
    }
}

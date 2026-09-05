//! SQL-level authorization scope filters (twenty-ninth audit Wave B
//! item 7; thirtieth-audit P0 item 1): the bridge between the DB-resolved
//! [`AuthorizedScope`] on a [`RequestContext`] and the repository
//! statements that enforce it.
//!
//! Every production service method now takes the server-created
//! [`RequestContext`] — never a naked `tenant_id` — and embeds the scope
//! IN THE SAME STATEMENT that reads or mutates the row. The variants map
//! to SQL as follows:
//!
//! - [`DbScopeFilter::TenantWide`] — the explicit all-access grant: NO
//!   site predicate is added (the `tenant_id` predicate of the statement
//!   is the whole boundary).
//! - [`DbScopeFilter::Operational`] — the UNION of the caller's site
//!   grants and exact work-center grants:
//!   `alias.site_id = ANY($n)` for the site grants, OR-ed with
//!   `(alias.site_id = $n+i AND alias.work_center_id = $n+i+1)` per exact
//!   work-center grant. A work-center grant NEVER widens into its site —
//!   it matches the carrier row of its exact work center only.
//! - [`DbScopeFilter::None`] — `1 = 0`: a principal with no active
//!   assignment matches ZERO rows (fail closed — no entitlement → no
//!   scope → no data).
//!
//! # The carrier relation
//!
//! Work orders carry `work_center_id` but their SITE is owned by the
//! `work_centers` row (`work_centers.site_id`), so the production
//! repository resolves every scoped work-order statement through the
//! carrier relation
//!
//! ```sql
//! (SELECT wc.id AS work_center_id, wc.site_id, wc.tenant_id
//!    FROM work_centers wc) AS wc
//! ```
//!
//! joined on `wc.work_center_id = wo.work_center_id` — the carrier row
//! then exposes BOTH `site_id` and `work_center_id`, which is exactly
//! the column contract [`DbScopeFilter::where_clause_for`] fragments
//! reference. An order without a work center has no carrier row, so a
//! site/work-center-scoped caller never sees it (fail closed); only a
//! `TenantWide` caller (no carrier join) does.
use sensei_core::domain::scope::{AuthorizedScope, WorkCenterScope};
use uuid::Uuid;

/// The SQL form of the caller's operational scope, derived from the
/// DB-resolved [`AuthorizedScope`] on the [`RequestContext`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DbScopeFilter {
    /// Explicit all-access grant: no site predicate is emitted — the
    /// statement's `tenant_id` predicate is the whole boundary.
    TenantWide,
    /// The UNION of whole-site grants (`sites`) and exact work-center
    /// grants (`work_centers`, each carrying its DB-derived site; never
    /// normalized into `sites`). Both lists are sorted for deterministic
    /// fragments. At least one list is non-empty.
    Operational {
        sites: Vec<Uuid>,
        work_centers: Vec<WorkCenterScope>,
    },
    /// No operational scope (no active assignment): an impossible
    /// predicate, so every statement matches zero rows.
    None,
}

impl DbScopeFilter {
    /// Derive the SQL scope filter from the authorized scope (twenty-ninth
    /// audit Wave A item 3; thirtieth-audit P0 item 1):
    /// `NoOperationalScope` becomes the impossible predicate — a
    /// principal with no entitlement can never read or mutate anything
    /// through a scoped statement; `Operational` becomes the exact union
    /// of site grants and work-center grants (a WC slot stays exact — it
    /// never widens into its site).
    pub fn from_authorized(scope: &AuthorizedScope) -> Self {
        match scope {
            AuthorizedScope::NoOperationalScope => DbScopeFilter::None,
            AuthorizedScope::TenantWide => DbScopeFilter::TenantWide,
            AuthorizedScope::Operational {
                sites,
                work_centers,
            } => {
                let mut sites: Vec<Uuid> = sites.iter().copied().collect();
                sites.sort_unstable();
                let mut work_centers: Vec<WorkCenterScope> = work_centers.iter().copied().collect();
                work_centers.sort_by_key(|wc| (wc.site, wc.work_center));
                if sites.is_empty() && work_centers.is_empty() {
                    DbScopeFilter::None
                } else {
                    DbScopeFilter::Operational {
                        sites,
                        work_centers,
                    }
                }
            }
        }
    }

    /// True when the filter emits no site predicate at all.
    pub fn is_tenant_wide(&self) -> bool {
        matches!(self, DbScopeFilter::TenantWide)
    }

    /// Build the SQL scope predicate for the scope-carrier alias.
    ///
    /// Returns `(sql_fragment, tenant_wide)`: `tenant_wide` tells the
    /// caller that no predicate exists (the caller then also skips the
    /// carrier join — a tenant-wide caller reads orders with no work
    /// center, which have no carrier row).
    ///
    /// - `TenantWide` → `("", true)`
    /// - `Operational` → the union predicate described in the module
    ///   docs. Sites-only grants emit `"{alias}.site_id = ANY(${param})"`
    ///   (bind: the authorized site set, then one `(site, work_center)`
    ///   scalar pair per work-center grant); a single exact work center
    ///   emits `"{alias}.site_id = ${param} AND
    ///   {alias}.work_center_id = ${param + 1}"`.
    /// - `None` → `("1 = 0", false)`.
    ///
    /// The fragment is appended to the statement's `WHERE` with `AND`;
    /// the caller binds the placeholder values in placeholder order.
    /// When `param` numbers an existing placeholder the fragment must be
    /// placed AFTER the binds it displaces (sqlx binds positionally).
    pub fn where_clause_for(&self, alias: &str, param: usize) -> (String, bool) {
        match self {
            DbScopeFilter::TenantWide => (String::new(), true),
            DbScopeFilter::Operational {
                sites,
                work_centers,
            } => {
                let mut parts = Vec::new();
                let mut next = param;
                if !sites.is_empty() {
                    parts.push(format!("{alias}.site_id = ANY(${next})"));
                    next += 1;
                }
                for _wc in work_centers {
                    parts.push(format!(
                        "{alias}.site_id = ${next} AND {alias}.work_center_id = ${}",
                        next + 1
                    ));
                    next += 2;
                }
                if parts.is_empty() {
                    // Empty union — impossible predicate (fail closed).
                    return ("1 = 0".to_string(), false);
                }
                if parts.len() == 1 {
                    (parts.pop().expect("len checked above"), false)
                } else {
                    (format!("({})", parts.join(" OR ")), false)
                }
            }
            DbScopeFilter::None => ("1 = 0".to_string(), false),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tenant_wide_emits_no_predicate() {
        let f = DbScopeFilter::TenantWide;
        let (sql, tenant_wide) = f.where_clause_for("wc", 4);
        assert!(tenant_wide);
        assert!(sql.is_empty());
    }

    #[test]
    fn none_emits_impossible_predicate() {
        let f: DbScopeFilter = DbScopeFilter::None;
        let (sql, tenant_wide) = f.where_clause_for("wc", 4);
        assert!(!tenant_wide);
        assert_eq!(sql, "1 = 0");
    }

    #[test]
    fn sites_only_emits_any_predicate() {
        let sites = [Uuid::new_v4(), Uuid::new_v4()];
        let f = DbScopeFilter::Operational {
            sites: sites.to_vec(),
            work_centers: Vec::new(),
        };
        let (sql, tenant_wide) = f.where_clause_for("wc", 4);
        assert!(!tenant_wide);
        assert_eq!(sql, "wc.site_id = ANY($4)");
    }

    #[test]
    fn single_work_center_emits_site_and_identity_predicates() {
        let wc = WorkCenterScope {
            site: Uuid::new_v4(),
            work_center: Uuid::new_v4(),
        };
        let f = DbScopeFilter::Operational {
            sites: Vec::new(),
            work_centers: vec![wc],
        };
        let (sql, tenant_wide) = f.where_clause_for("wc", 5);
        assert!(!tenant_wide);
        assert_eq!(sql, "wc.site_id = $5 AND wc.work_center_id = $6");
    }

    #[test]
    fn mixed_union_emits_exact_work_centers_not_sites() {
        let wc_b1 = WorkCenterScope {
            site: Uuid::new_v4(),
            work_center: Uuid::new_v4(),
        };
        let wc_b2 = WorkCenterScope {
            site: wc_b1.site,
            work_center: Uuid::new_v4(),
        };
        let site_a = Uuid::new_v4();
        // Site A grant + WC B1/B2 grants at ANOTHER site: the union must
        // keep the WC pairs exact — never widen B1/B2 into site B.
        let f = DbScopeFilter::Operational {
            sites: vec![site_a],
            work_centers: vec![wc_b1, wc_b2],
        };
        let (sql, tenant_wide) = f.where_clause_for("wc", 7);
        assert!(!tenant_wide);
        assert_eq!(
            sql,
            format!(
                "(wc.site_id = ANY($7) OR wc.site_id = $8 AND wc.work_center_id = $9 \
                 OR wc.site_id = $10 AND wc.work_center_id = $11)"
            )
        );
    }

    #[test]
    fn from_authorized_maps_every_variant() {
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let wc = Uuid::new_v4();
        assert!(matches!(
            DbScopeFilter::from_authorized(&AuthorizedScope::NoOperationalScope),
            DbScopeFilter::None
        ));
        assert!(matches!(
            DbScopeFilter::from_authorized(&AuthorizedScope::tenant_wide()),
            DbScopeFilter::TenantWide
        ));
        let scope = AuthorizedScope::Operational {
            sites: std::collections::HashSet::from([site_a, site_b]),
            work_centers: std::collections::HashSet::new(),
        };
        let DbScopeFilter::Operational {
            sites,
            work_centers: _,
        } = DbScopeFilter::from_authorized(&scope)
        else {
            panic!("site scope must map to an Operational filter");
        };
        assert!(sites.contains(&site_a) && sites.contains(&site_b));
        let scope = AuthorizedScope::Operational {
            sites: std::collections::HashSet::new(),
            work_centers: std::collections::HashSet::from([WorkCenterScope {
                site: site_a,
                work_center: wc,
            }]),
        };
        assert_eq!(
            DbScopeFilter::from_authorized(&scope),
            DbScopeFilter::Operational {
                sites: Vec::new(),
                work_centers: vec![WorkCenterScope {
                    site: site_a,
                    work_center: wc,
                }],
            }
        );
    }
}

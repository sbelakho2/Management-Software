//! SQL-level authorization scope filters (twenty-ninth audit Wave B
//! item 7): the bridge between the DB-resolved [`AuthorizedScope`] on a
//! [`RequestContext`] and the repository statements that enforce it.
//!
//! Every production service method now takes the server-created
//! [`RequestContext`] — never a naked `tenant_id` — and embeds the scope
//! IN THE SAME STATEMENT that reads or mutates the row. The four
//! variants map to SQL as follows:
//!
//! - [`DbScopeFilter::TenantWide`] — the explicit all-access grant: NO
//!   site predicate is added (the `tenant_id` predicate of the statement
//!   is the whole boundary).
//! - [`DbScopeFilter::Sites`] — `alias.site_id = ANY($n)`: only rows
//!   whose scope carrier (the work center's site) is in the authorized
//!   set.
//! - [`DbScopeFilter::WorkCenter`] — `alias.site_id = $n AND
//!   alias.work_center_id = ${n+1}`: exactly the carrier row of the
//!   scoped work center.
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
use sensei_core::domain::scope::AuthorizedScope;
use uuid::Uuid;

/// The SQL form of the caller's operational scope, derived from the
/// DB-resolved [`AuthorizedScope`] on the [`RequestContext`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DbScopeFilter<'a> {
    /// Explicit all-access grant: no site predicate is emitted — the
    /// statement's `tenant_id` predicate is the whole boundary.
    TenantWide,
    /// Exactly the sites the principal's active role slots authorize.
    Sites(&'a [Uuid]),
    /// One site + one work center (`WorkCenterScope` is DB-resolved, so
    /// the pair is always consistent).
    WorkCenter { site: Uuid, work_center: Uuid },
    /// No operational scope (no active assignment): an impossible
    /// predicate, so every statement matches zero rows.
    None,
}

impl<'a> DbScopeFilter<'a> {
    /// Derive the SQL scope filter from the authorized scope (twenty-ninth
    /// audit Wave A item 3): `NoOperationalScope` becomes the impossible
    /// predicate — a principal with no entitlement can never read or
    /// mutate anything through a scoped statement.
    pub fn from_authorized(scope: &'a AuthorizedScope) -> Self {
        match scope {
            AuthorizedScope::NoOperationalScope => DbScopeFilter::None,
            AuthorizedScope::TenantWide => DbScopeFilter::TenantWide,
            AuthorizedScope::Sites(sites) => DbScopeFilter::Sites(sites),
            AuthorizedScope::WorkCenter(wc) => DbScopeFilter::WorkCenter {
                site: wc.site,
                work_center: wc.work_center,
            },
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
    /// - `Sites` → `"{alias}.site_id = ANY(${param})"` (bind: the
    ///   authorized site set).
    /// - `WorkCenter` → `"{alias}.site_id = ${param} AND
    ///   {alias}.work_center_id = ${param + 1}"` (bind: the scope site,
    ///   then the scope work center).
    /// - `None` → `("1 = 0", false)`.
    ///
    /// The fragment is appended to the statement's `WHERE` with `AND`;
    /// the caller binds the placeholder values in placeholder order.
    /// When `param` numbers an existing placeholder the fragment must be
    /// placed AFTER the binds it displaces (sqlx binds positionally).
    pub fn where_clause_for(&self, alias: &str, param: usize) -> (String, bool) {
        match self {
            DbScopeFilter::TenantWide => (String::new(), true),
            DbScopeFilter::Sites(_) => (format!("{alias}.site_id = ANY(${param})"), false),
            DbScopeFilter::WorkCenter { .. } => (
                format!(
                    "{alias}.site_id = ${param} AND {alias}.work_center_id = ${}",
                    param + 1
                ),
                false,
            ),
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
    fn sites_emits_any_predicate() {
        let sites = [Uuid::new_v4(), Uuid::new_v4()];
        let f = DbScopeFilter::Sites(&sites);
        let (sql, tenant_wide) = f.where_clause_for("wc", 4);
        assert!(!tenant_wide);
        assert_eq!(sql, "wc.site_id = ANY($4)");
    }

    #[test]
    fn work_center_emits_site_and_identity_predicates() {
        let f = DbScopeFilter::WorkCenter {
            site: Uuid::new_v4(),
            work_center: Uuid::new_v4(),
        };
        let (sql, tenant_wide) = f.where_clause_for("wc", 5);
        assert!(!tenant_wide);
        assert_eq!(sql, "wc.site_id = $5 AND wc.work_center_id = $6");
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
        let scope = AuthorizedScope::Sites(vec![site_a, site_b]);
        let DbScopeFilter::Sites(ids) = DbScopeFilter::from_authorized(&scope) else {
            panic!("Sites scope must map to Sites filter");
        };
        assert_eq!(ids, &[site_a, site_b]);
        let scope = AuthorizedScope::WorkCenter(sensei_core::domain::scope::WorkCenterScope {
            site: site_a,
            work_center: wc,
        });
        assert_eq!(
            DbScopeFilter::from_authorized(&scope),
            DbScopeFilter::WorkCenter {
                site: site_a,
                work_center: wc,
            }
        );
    }
}

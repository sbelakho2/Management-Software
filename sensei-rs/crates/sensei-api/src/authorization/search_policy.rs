//! Canonical search result-type authorization registry (twenty-ninth
//! audit Wave B item 10).
//!
//! Unified search must never be a tenant-wide, type-unrestricted listing:
//! every searched result type maps to the canonical read permission that
//! guards its ordinary read surface, and every type is either
//! [`ScopeMode::Tenant`] (no site dimension — accounts, contacts,
//! products, knowledge, …) or [`ScopeMode::Operational`] (shop-floor
//! data — work centers, standard work, production cells) whose rows are
//! restricted to the caller's authorized sites.
//!
//! The caller's effective [`AllowedSearchProjection`] is precomputed in
//! the route:
//!
//! 1. every result type whose read permission the caller does NOT hold
//!    is dropped (never searched, never returned);
//! 2. operational types are additionally restricted to the caller's
//!    `RequestContext` authorized sites (an empty entitlement produces
//!    NO operational rows — never a tenant-wide fallback).
//!
//! The projection is passed INTO the database search so candidate tables
//! are filtered before ranking — search never runs all tables and then
//! filters the result set.
//!
//! # Registry completeness invariant
//!
//! [`search_policies()`] covers every result type the search backends can
//! return (typed tables + `entity_store` generic types, in-memory
//! providers and the DB service). A result type absent from the registry
//! is inadmissible by construction (fail closed): unknown types can never
//! leak through an unspecified permission.

use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::scope::AuthorizedScope;
use sensei_core::error::{Result, SenseiError};
use uuid::Uuid;

use crate::authorization::request_context::build_request_context;
use crate::state::AppState;

/// Whether a searched result type has a site dimension.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScopeMode {
    /// Tenant-level data with no site column — permission-gated only.
    Tenant,
    /// Operational shop-floor data — additionally restricted to the
    /// caller's authorized sites when a scope authority exists.
    Operational,
}

/// One registry entry: a searched result type, its canonical read
/// permission and its scope mode.
///
/// Fields are private on purpose — the registry is consulted through
/// [`search_policies()`] / [`SearchPolicy`] accessors so the mapping can
/// never be mutated by a caller.
pub struct SearchPolicy {
    result_type: &'static str,
    required_permission: &'static str,
    scope_mode: ScopeMode,
}

impl SearchPolicy {
    /// The canonical result type name ("account", "work_center", …).
    pub fn result_type(&self) -> &'static str {
        self.result_type
    }

    /// The permission required to read that result type's ordinary
    /// surface (e.g. `"sales:account:read"`, `"tps:work-center:read"`).
    pub fn required_permission(&self) -> &'static str {
        self.required_permission
    }

    /// Whether the type is site-scoped operational data or tenant data.
    pub fn scope_mode(&self) -> ScopeMode {
        self.scope_mode
    }
}

/// The canonical registry. Result types below are exactly the types the
/// search backends can produce (see `db_search_service` /
/// `search_providers`).
const REGISTRY: &[SearchPolicy] = &[
    // ── Typed tables (tenant data) ───────────────────────────────────
    SearchPolicy {
        result_type: "user",
        required_permission: "users:list",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "account",
        required_permission: "sales:account:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "contact",
        required_permission: "sales:account:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "product",
        required_permission: "master-data:products:read",
        scope_mode: ScopeMode::Tenant,
    },
    // ── Generic entity-store types (tenant data) ─────────────────────
    SearchPolicy {
        result_type: "task",
        required_permission: "tasks:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "kanban_board",
        required_permission: "tps:kanban:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "obeya_board",
        required_permission: "tps:obeya:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "knowledge_pack",
        required_permission: "knowledge:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "training_course",
        required_permission: "training:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "state_machine_instance",
        required_permission: "system:state-machines:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "lsw_standard",
        required_permission: "tps:lsw:execute",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "kpi_definition",
        required_permission: "tps:kpi:read",
        scope_mode: ScopeMode::Tenant,
    },
    SearchPolicy {
        result_type: "notification_trigger",
        required_permission: "tps:notification-triggers:manage",
        scope_mode: ScopeMode::Tenant,
    },
    // ── Operational (site-scoped shop-floor) types ────────────────────
    SearchPolicy {
        result_type: "work_center",
        required_permission: "tps:work-center:read",
        scope_mode: ScopeMode::Operational,
    },
    SearchPolicy {
        result_type: "standard_work",
        required_permission: "tps:standard-work:read",
        scope_mode: ScopeMode::Operational,
    },
    SearchPolicy {
        result_type: "production_cell",
        required_permission: "tps:cell:read",
        scope_mode: ScopeMode::Operational,
    },
];

/// The registry — immutable by construction.
pub fn search_policies() -> &'static [SearchPolicy] {
    REGISTRY
}

/// Look up the policy for one result type.
pub fn policy_for(result_type: &str) -> Option<&'static SearchPolicy> {
    REGISTRY.iter().find(|p| p.result_type == result_type)
}

/// Whether the caller may read the given result type.
///
/// `require_permission` consults the request-local live permission set
/// first (authoritative when non-empty) and the legacy role registry only
/// when the live set is empty — the same dual path every route guard uses.
pub fn can_read_result_type(user: &AuthenticatedUser, result_type: &str) -> bool {
    match policy_for(result_type) {
        Some(policy) => user
            .require_permission(policy.required_permission())
            .is_ok(),
        None => false,
    }
}

// ---------------------------------------------------------------------------
// Caller-derived search projection
// ---------------------------------------------------------------------------

/// The caller's admissible search surface (item 10): which result types
/// they may search and — for operational types — the sites those rows
/// must belong to.
///
/// `sites` is:
///
/// * `None` — no scope authority exists (in-memory/dev deployments have
///   no site rows to entangle; the operational types are not
///   site-restricted there, mirroring the supply-chain `caller_scope`
///   pattern);
/// * `Some(&[])` — a DB-resolved `NoOperationalScope`: operational types
///   yield NO rows (fail closed, never a tenant-wide fallback);
/// * `Some(sites)` — `Sites` / `WorkCenter` scope: operational rows are
///   restricted to rows whose site is among `sites`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AllowedSearchProjection {
    entity_types: Vec<&'static str>,
    sites: Option<Vec<Uuid>>,
}

impl AllowedSearchProjection {
    /// Precompute the caller's admissible projection (item 10):
    ///
    /// * every registered result type whose read permission the caller
    ///   does not hold is dropped;
    /// * the optional `requested_type` filter (the `entity_type` query
    ///   parameter) is intersected — a type the caller may not read, or
    ///   an unknown type, admits nothing;
    /// * when the deployment has a database, the operational scope is
    ///   resolved through the caller's [`RequestContext`] (the
    ///   routes/andon.rs `caller_sites` pattern); without a database the
    ///   operational types stay unrestricted (dev semantics — there are
    ///   no site rows to entangle).
    ///
    /// [`RequestContext`]: sensei_core::domain::request_context::RequestContext
    pub async fn for_caller(
        state: &AppState,
        user: &AuthenticatedUser,
        requested_type: Option<&str>,
    ) -> Result<Self> {
        let sites = caller_operational_sites(state, user).await?;
        let entity_types: Vec<&'static str> = REGISTRY
            .iter()
            .filter(|policy| requested_type.is_none_or(|rt| rt == policy.result_type()))
            .filter(|policy| {
                user.require_permission(policy.required_permission())
                    .is_ok()
            })
            .map(|policy| policy.result_type())
            .collect();
        Ok(Self {
            entity_types,
            sites,
        })
    }

    /// The admissible result types (empty ⇒ nothing is searchable).
    pub fn entity_types(&self) -> &[&'static str] {
        &self.entity_types
    }

    /// The site restriction for operational types (`None` = no scope
    /// authority, unrestricted; `Some` = restricted, empty means deny all
    /// operational rows).
    pub fn sites(&self) -> Option<&[Uuid]> {
        self.sites.as_deref()
    }

    /// Whether the given result type is admissible.
    pub fn contains(&self, result_type: &str) -> bool {
        self.entity_types.contains(&result_type)
    }

    /// True when the caller is site-restricted (has a DB-resolved scope).
    pub fn is_site_restricted(&self) -> bool {
        self.sites.is_some()
    }
}

/// Resolve the caller's operational site restriction through the ONE
/// shared [`RequestContext`] builder ([`build_request_context`] — the
/// routes/andon.rs `caller_sites` pattern):
///
/// * no scope authority (in-memory/dev → explicit tenant-wide grant) →
///   `None` (dev semantics, no sites to entangle);
/// * `NoOperationalScope` → `Some(vec![])` (deny every operational row);
/// * `Sites` → `Some(sites)`;
/// * `WorkCenter` → `Some(vec![wc.site])`;
/// * `TenantWide` → `None` (explicit all-access grant).
///
/// [`RequestContext`]: sensei_core::domain::request_context::RequestContext
async fn caller_operational_sites(
    state: &AppState,
    user: &AuthenticatedUser,
) -> Result<Option<Vec<Uuid>>> {
    let rc = build_request_context(user, state).await?;
    Ok(match &rc.scope {
        AuthorizedScope::TenantWide => None,
        AuthorizedScope::NoOperationalScope => Some(Vec::new()),
        AuthorizedScope::Sites(sites) => Some(sites.clone()),
        AuthorizedScope::WorkCenter(wc) => Some(vec![wc.site]),
    })
}

/// Guard: an unknown requested result type must fail closed (never
/// degrade to an unrestricted search).
pub fn ensure_known_result_type(result_type: &str) -> Result<()> {
    if policy_for(result_type).is_some() {
        Ok(())
    } else {
        Err(SenseiError::Validation(format!(
            "unknown search entity_type '{result_type}'"
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_covers_every_searchable_result_type() {
        // Typed tables + every generic store type the backends can emit.
        let searchable = [
            "user",
            "account",
            "contact",
            "product",
            "task",
            "kanban_board",
            "obeya_board",
            "knowledge_pack",
            "training_course",
            "work_center",
            "state_machine_instance",
            "production_cell",
            "standard_work",
            "lsw_standard",
            "kpi_definition",
            "notification_trigger",
        ];
        for result_type in searchable {
            assert!(
                policy_for(result_type).is_some(),
                "registry must cover {result_type}"
            );
        }
        assert_eq!(search_policies().len(), searchable.len());
    }

    #[test]
    fn registry_has_no_duplicate_result_types() {
        let mut seen = std::collections::HashSet::new();
        for policy in search_policies() {
            assert!(
                seen.insert(policy.result_type()),
                "duplicate registry entry for {}",
                policy.result_type()
            );
        }
    }

    #[test]
    fn operational_types_are_the_shop_floor_surfaces() {
        let operational: Vec<&str> = search_policies()
            .iter()
            .filter(|p| p.scope_mode() == ScopeMode::Operational)
            .map(|p| p.result_type())
            .collect();
        assert_eq!(
            operational,
            ["work_center", "standard_work", "production_cell"]
        );
    }

    #[test]
    fn unknown_types_are_never_admissible() {
        let user = AuthenticatedUser {
            user_id: Uuid::new_v4(),
            tenant_id: Uuid::new_v4(),
            roles: vec!["platform_superadmin".to_string()],
            sid: None,
            permissions: std::collections::HashSet::from(["*:*".to_string()]),
        };
        assert!(!can_read_result_type(&user, "wombat"));
        assert!(ensure_known_result_type("wombat").is_err());
        assert!(ensure_known_result_type("account").is_ok());
    }
}

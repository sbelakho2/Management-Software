//! Canonical search result-type authorization registry (twenty-ninth
//! audit Wave B item 10; thirtieth-audit P0 item 12).
//!
//! Unified search must never be a tenant-wide, type-unrestricted listing:
//! every searched result type maps to the canonical read permission that
//! guards its ordinary read surface, and every type is either
//! [`ScopeMode::Tenant`] (no site dimension — accounts, contacts,
//! products, knowledge, …) or [`ScopeMode::Operational`] (shop-floor
//! data — work centers, standard work, production cells) whose rows are
//! restricted to the caller's FULL [`AuthorizedScope`] — site grants AND
//! exact work-center grants, never a normalized site list.
//!
//! The caller's effective [`AllowedSearchProjection`] is precomputed in
//! the route:
//!
//! 1. every result type whose read permission the caller does NOT hold
//!    is dropped (never searched, never returned);
//! 2. the projection carries the caller's DB-resolved
//!    [`AuthorizedScope`] unchanged — the database search applies it
//!    per RESOURCE (a site grant covers the site's rows; a work-center
//!    grant covers exactly that work center's rows, never the parent
//!    site; an empty entitlement produces NO operational rows — never a
//!    tenant-wide fallback).
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

/// The caller's admissible search surface (item 10; thirtieth-audit P0
/// item 12): which result types they may search and — for operational
/// types — the FULL DB-resolved [`AuthorizedScope`] those rows must lie
/// inside.
///
/// The scope travels UNCHANGED from the caller's [`RequestContext`] (no
/// site-list normalization): the database search matches per resource, so
/// an exact work-center grant (`Operational.work_centers`) restricts
/// work-center rows to `id = ANY($exact_wc_ids)` — never to the parent
/// site — while site grants (`Operational.sites`) apply only to
/// site-level rows and site-attributable rows.
///
/// [`RequestContext`]: sensei_core::domain::request_context::RequestContext
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AllowedSearchProjection {
    entity_types: Vec<&'static str>,
    /// The caller's FULL operational scope:
    ///
    /// * `TenantWide` — an explicit all-access grant (dev deployments
    ///   carry it by default): no operational restriction applies;
    /// * `NoOperationalScope` — no entitlement: operational types yield
    ///   NO rows (fail closed, never a tenant-wide fallback);
    /// * `Operational { sites, work_centers }` — site grants cover the
    ///   sites' rows; work-center grants cover exactly the granted work
    ///   centers (never the parent site).
    scope: AuthorizedScope,
}

impl AllowedSearchProjection {
    /// Precompute the caller's admissible projection (item 10; item 12):
    ///
    /// * every registered result type whose read permission the caller
    ///   does not hold is dropped;
    /// * the optional `requested_type` filter (the `entity_type` query
    ///   parameter) is intersected — a type the caller may not read, or
    ///   an unknown type, admits nothing;
    /// * the FULL operational scope is resolved through the caller's
    ///   [`RequestContext`] (the routes/andon.rs `caller_sites` pattern)
    ///   and carried on the projection untouched — the DB search applies
    ///   it per resource instead of normalizing work-center grants into
    ///   their sites.
    ///
    /// [`RequestContext`]: sensei_core::domain::request_context::RequestContext
    pub async fn for_caller(
        state: &AppState,
        user: &AuthenticatedUser,
        requested_type: Option<&str>,
    ) -> Result<Self> {
        let rc = build_request_context(user, state).await?;
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
            scope: rc.scope,
        })
    }

    /// The admissible result types (empty ⇒ nothing is searchable).
    pub fn entity_types(&self) -> &[&'static str] {
        &self.entity_types
    }

    /// The caller's FULL operational scope (item 12): the database search
    /// applies this scope per resource — site grants (`Operational.sites`)
    /// restrict site-level rows; work-center grants
    /// (`Operational.work_centers`) restrict work-center rows to the exact
    /// granted ids; `NoOperationalScope` admits no operational row;
    /// `TenantWide` is unrestricted.
    pub fn scope(&self) -> &AuthorizedScope {
        &self.scope
    }

    /// Whether the given result type is admissible.
    pub fn contains(&self, result_type: &str) -> bool {
        self.entity_types.contains(&result_type)
    }

    /// True when the caller is operationally restricted (has any
    /// DB-resolved operational entitlement narrower than tenant-wide).
    pub fn is_operationally_restricted(&self) -> bool {
        !matches!(
            self.scope,
            AuthorizedScope::TenantWide | AuthorizedScope::NoOperationalScope
        )
    }
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
    use uuid::Uuid;

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

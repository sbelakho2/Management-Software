//! Role-based access control (RBAC).
//!
//! Provides permission checking against user roles. Permissions are
//! defined as `{resource}:{action}` strings (e.g., `quality:ncr:create`).

use sensei_core::domain::entities::Permission;
use std::collections::{HashMap, HashSet};
use uuid::Uuid;

/// In-memory RBAC service.
///
/// Maps role names to sets of granted permissions.
pub struct RbacService {
    /// Static/system role definitions: role_name -> set of permissions.
    roles: HashMap<String, HashSet<String>>,
    /// Tenant-scoped custom roles: (tenant_id, role_name) -> perms. A
    /// custom role NEVER crosses tenant boundaries — two tenants defining
    /// `operations_manager` with different permissions cannot contaminate
    /// one another.
    tenant_roles: HashMap<(Uuid, String), HashSet<String>>,
}

/// Process-wide shared authorization service, installed by the API at
/// startup with the DB-loaded role map. `require_permission` resolves
/// through this registry so database-defined custom roles are actually
/// used in authorization decisions (never a fresh `RbacService::new()`).
static AUTHORIZATION_SERVICE: std::sync::OnceLock<std::sync::Arc<RbacService>> =
    std::sync::OnceLock::new();

/// Install the shared authorization service (idempotent — first install wins).
pub fn set_authorization_service(svc: std::sync::Arc<RbacService>) {
    let _ = AUTHORIZATION_SERVICE.set(svc);
}

/// The shared authorization service (defaults when not installed, e.g. tests).
pub fn authorization_service() -> std::sync::Arc<RbacService> {
    AUTHORIZATION_SERVICE
        .get()
        .cloned()
        .unwrap_or_else(|| std::sync::Arc::new(RbacService::new()))
}

impl RbacService {
    /// Create a new [`RbacService`] with default role definitions.
    pub fn new() -> Self {
        let mut svc = Self {
            roles: HashMap::new(),
            tenant_roles: HashMap::new(),
        };
        svc.load_default_roles();
        svc
    }

    /// Create an empty [`RbacService`] without default roles.
    pub fn empty() -> Self {
        Self {
            roles: HashMap::new(),
            tenant_roles: HashMap::new(),
        }
    }

    /// Build a role map from PostgreSQL: the static defaults provide the
    /// baseline, then every row of the tenant-scoped `roles` table is
    /// overlaid (name -> permissions, unioned across tenants). This makes
    /// the authorization service a shared, DB-driven component instead of a
    /// hard-coded table reconstructed per decision.
    pub async fn from_db(pool: &sqlx::PgPool) -> Result<Self, sqlx::Error> {
        let mut svc = Self::new();
        let rows: Vec<(Uuid, String, Vec<String>)> =
            sqlx::query_as("SELECT tenant_id, name, permissions FROM roles")
                .fetch_all(pool)
                .await?;
        for (tenant_id, name, permissions) in rows {
            svc.tenant_roles
                .insert((tenant_id, name), permissions.into_iter().collect());
        }
        Ok(svc)
    }

    /// Load the default role hierarchy.
    fn load_default_roles(&mut self) {
        // Break-glass superuser only (never assigned through the normal
        // user-management API; see routes/users.rs update_user_roles).
        self.add_role("platform_superadmin", vec!["*:*"]);
        // System-level tenant management (bootstrap admin only).
        self.add_role("platform_admin", vec!["tenants:*", "users:*", "system:*"]);
        // System-level tenant management (bootstrap admin only).
        self.add_role("platform_admin", vec!["tenants:*", "users:*", "system:*"]);
        // Tenant-scoped user administration.
        self.add_role(
            "tenant_admin",
            vec![
                "users:list",
                "users:update",
                "users:roles",
                "users:deactivate",
                "users:activate",
            ],
        );

        // Quality manager
        // Quality technician
        // Production manager
        // Operator
        // ── Finance (exact families: read/create/update/void, record/reverse,
        //    post/reverse, create/allocate/approve) ──────────────────────
        self.add_role(
            "finance_manager",
            vec![
                "finance:invoice:read",
                "finance:invoice:create",
                "finance:invoice:update",
                "finance:invoice:void",
                "finance:invoice:approve",
                "finance:payment:read",
                "finance:payment:record",
                "finance:payment:reverse",
                "finance:payment:void",
                "finance:journal:read",
                "finance:journal:post",
                "finance:journal:reverse",
                "finance:budget:read",
                "finance:budget:create",
                "finance:budget:allocate",
                "finance:budget:approve",
                "finance:rollup:run",
                "finance:match:three-way",
            ],
        );
        self.add_role(
            "accountant",
            vec![
                "finance:invoice:read",
                "finance:invoice:create",
                "finance:payment:read",
                "finance:payment:record",
                "finance:journal:read",
                "finance:journal:post",
                "finance:budget:read",
            ],
        );
        self.add_role(
            "ap_specialist",
            vec![
                "finance:invoice:read",
                "finance:invoice:approve",
                "finance:payment:record",
                "finance:match:three-way",
            ],
        );
        self.add_role(
            "ar_specialist",
            vec![
                "finance:invoice:read",
                "finance:invoice:create",
                "finance:payment:record",
            ],
        );

        // ── HR ─────────────────────────────────────────────────────────
        self.add_role(
            "hr_manager",
            vec![
                "hr:employee:read",
                "hr:employee:manage",
                "hr:leave:self",
                "hr:leave:approve",
                "hr:review:manage",
                "hr:timecard:self",
                "hr:timecard:manage",
                "hr:training:manage",
            ],
        );
        self.add_role(
            "hr_specialist",
            vec![
                "hr:employee:read",
                "hr:employee:manage",
                "hr:training:manage",
                "hr:timecard:manage",
            ],
        );
        self.add_role(
            "supervisor",
            vec![
                "hr:employee:read",
                "hr:leave:self",
                "hr:leave:approve",
                "hr:timecard:self",
                "hr:timecard:manage",
            ],
        );

        // ── Purchasing / supply chain ──────────────────────────────────
        self.add_role(
            "purchasing_manager",
            vec![
                "purchasing:po:create",
                "purchasing:po:approve",
                "purchasing:po:read",
                "purchasing:rfq:manage",
                "purchasing:supplier:manage",
                "purchasing:rfq:create",
                "purchasing:rfq:update",
                "purchasing:rfq:submit",
                "purchasing:rfq:cancel",
                "purchasing:rfq:delete",
                "purchasing:quote:create",
                "purchasing:quote:update",
                "purchasing:quote:approve",
                "sales:order:create",
                "sales:order:update",
                "sales:order:status",
                "sales:order:delete",
            ],
        );
        self.add_role(
            "buyer",
            vec![
                "purchasing:po:create",
                "purchasing:rfq:create",
                "purchasing:rfq:update",
                "purchasing:rfq:submit",
                "purchasing:rfq:cancel",
            ],
        );
        self.add_role(
            "receiving_operator",
            vec![
                "purchasing:po:create",
                "purchasing:po:approve",
                "inventory:move",
                "inventory:adjust",
            ],
        );

        // ── Inventory / warehouse ──────────────────────────────────────
        self.add_role(
            "inventory_manager",
            vec![
                "inventory:adjust",
                "inventory:move",
                "inventory:warehouse:manage",
            ],
        );
        self.add_role(
            "warehouse_operator",
            vec!["inventory:move", "inventory:adjust"],
        );

        // ── Sales ──────────────────────────────────────────────────────
        self.add_role(
            "sales_manager",
            vec![
                "sales:order:create",
                "sales:order:update",
                "sales:order:status",
                "purchasing:quote:create",
                "purchasing:quote:update",
                "purchasing:quote:approve",
                "sales:account:manage",
                "sales:opportunity:manage",
                "ai:retrain",
            ],
        );
        self.add_role(
            "sales_rep",
            vec![
                "sales:order:create",
                "sales:order:update",
                "purchasing:quote:create",
                "purchasing:quote:update",
            ],
        );

        // ── Quality (complete families incl. the enforcement set) ──────
        self.add_role(
            "quality_manager",
            vec![
                "quality:ncr:create",
                "quality:ncr:read",
                "quality:ncr:update",
                "quality:ncr:delete",
                "quality:ncr:approve",
                "quality:capa:create",
                "quality:capa:read",
                "quality:capa:update",
                "quality:capa:close",
                "quality:audit:read",
                "quality:audit:create",
                "quality:audit:update",
                "quality:audit:delete",
                "quality:inspection:read",
                "quality:inspection:create",
                "quality:inspection:update",
                "quality:inspection:delete",
                "quality:inspection:self",
                "quality:scar:read",
                "quality:scar:create",
                "quality:scar:update",
                "quality:scar:delete",
                "quality:complaint:read",
                "quality:complaint:create",
                "quality:8d:read",
                "quality:8d:create",
                "quality:supplier:read",
                "quality:supplier:manage",
                "quality:msa:read",
                "quality:msa:create",
                "quality:spc:read",
                "quality:spc:create",
                "quality:control-plan:read",
                "quality:control-plan:create",
                "quality:control-plan:update",
                "quality:pfmea:read",
                "quality:pfmea:create",
                "quality:gauge:read",
                "quality:gauge:create",
                "quality:gauge:update",
                "quality:fai:read",
                "quality:fai:create",
                "quality:document:read",
                "quality:document:create",
                "quality:review:read",
                "quality:review:create",
                "quality:stage-gate:read",
                "quality:stage-gate:manage",
                "quality:npi:read",
                "quality:npi:manage",
            ],
        );
        self.add_role(
            "quality_engineer",
            vec![
                "quality:ncr:create",
                "quality:ncr:read",
                "quality:ncr:update",
                "quality:capa:read",
                "quality:capa:update",
                "quality:audit:read",
                "quality:audit:create",
                "quality:inspection:read",
                "quality:inspection:create",
                "quality:scar:read",
                "quality:msa:read",
                "quality:spc:read",
                "quality:control-plan:read",
                "quality:pfmea:read",
                "quality:document:read",
                "quality:fai:read",
            ],
        );
        self.add_role(
            "quality_technician",
            vec![
                "quality:ncr:create",
                "quality:ncr:read",
                "quality:ncr:update",
                "quality:capa:read",
                "quality:inspection:read",
                "quality:inspection:create",
                "quality:inspection:self",
                "quality:gauge:read",
                "quality:msa:read",
            ],
        );

        // ── Production ─────────────────────────────────────────────────
        self.add_role(
            "production_manager",
            vec![
                "production:work-order:create",
                "production:work-order:read",
                "production:work-order:update",
                "production:work-order:delete",
                "production:schedule:read",
                "production:schedule:update",
                "production:report",
                "production:release",
                "production:start",
                "production:complete",
                "production:short-close",
                "tps:andon:raise",
                "tps:andon:ack",
                "tps:andon:contain",
                "tps:andon:manage",
                "tps:andon:resolve",
                "tps:andon:restart",
                "tps:a3:read",
                "tps:a3:create",
                "tps:a3:edit",
                "tps:a3:verify",
                "tps:a3:close",
                "tps:standard-work:read",
                "tps:standard-work:draft",
                "tps:standard-work:review",
                "tps:standard-work:approve",
                "tps:standard-work:publish",
                "tps:lsw:execute",
                "tps:lsw:manage",
                "tps:obeya:read",
                "tps:obeya:manage",
                "tps:kpi:read",
                "tps:kpi:manage",
                "tps:ctq:read",
                "tps:ctq:manage",
                "tps:work-center:read",
                "tps:work-center:manage",
                "tps:cell:read",
                "tps:cell:manage",
                "tps:mrp:run",
                "tps:kanban:read",
                "tps:kanban:manage",
                "tps:training-matrix:read",
                "tps:training-matrix:manage",
                "tps:escalation:read",
                "tps:escalation:manage",
                "tps:notification-triggers:manage",
                "maintenance:request",
                "maintenance:assign",
                "maintenance:execute",
                "maintenance:return-to-service",
                "knowledge:manage",
                "learning:manage",
                "training:manage",
                "tasks:manage",
                "ai:retrain",
                "master-data:products:manage",
                "system:state-machines:manage",
                "attachments:manage",
            ],
        );
        self.add_role(
            "production_supervisor",
            vec![
                "production:work-order:read",
                "production:work-order:update",
                "production:work-order:update-status",
                "production:schedule:read",
            ],
        );
        self.add_role(
            "operator",
            vec![
                "production:work-order:read",
                "production:work-order:update-status",
                "production:work-order:report",
                "production:report",
                "production:start",
                "tps:andon:raise",
                "tps:andon:ack",
                "tps:a3:read",
                "tps:a3:create",
                "tps:standard-work:read",
                "tps:lsw:execute",
                "tps:obeya:read",
                "tps:kpi:read",
                "tps:ctq:read",
                "tps:work-center:read",
                "tps:kanban:read",
                "maintenance:request",
            ],
        );

        // Standard user
        self.add_role(
            "user",
            vec![
                "users:read:self",
                "users:update:self",
                "notifications:read",
                "dashboard:read",
                "knowledge:read",
                "integration:import",
                "learning:read",
                "training:read",
                "tasks:read",
                "ai:inference",
                "sales:account:read",
                "sales:opportunity:read",
                "master-data:products:read",
                "system:state-machines:read",
                "attachments:read",
                "system:audit:read",
                "inventory:read",
            ],
        );
    }

    /// Register a new role with the given permissions.
    pub fn add_role(&mut self, role_name: &str, permissions: Vec<&str>) {
        let perms: HashSet<String> = permissions.iter().map(|p| p.to_string()).collect();
        self.roles.insert(role_name.to_string(), perms);
    }

    /// Check if a user with the given roles has the required permission.
    ///
    /// Check system roles only (static RBAC defaults).
    ///
    /// Supports wildcard matching:
    /// - `*:*` matches everything
    /// - `quality:*` matches all actions on quality resources
    /// - `*:read` matches read on all resources
    pub fn has_permission(&self, user_roles: &[String], required: &Permission) -> bool {
        self.has_permission_for_tenant(user_roles, None, required)
    }

    /// Tenant-aware check: a role grants a permission when it is a system
    /// role OR a custom role defined for THE SAME tenant. A custom role can
    /// never leak across tenants.
    pub fn has_permission_for_tenant(
        &self,
        user_roles: &[String],
        tenant_id: Option<Uuid>,
        required: &Permission,
    ) -> bool {
        let (required_resource, required_action) = match required.parse() {
            Some(r) => r,
            None => return false,
        };

        for role_name in user_roles {
            if let Some(perms) = self.roles.get(role_name.as_str()) {
                for perm in perms {
                    if Self::matches(perm, required_resource, required_action) {
                        return true;
                    }
                }
            }
            if let Some(tenant_id) = tenant_id {
                if let Some(perms) = self.tenant_roles.get(&(tenant_id, role_name.clone())) {
                    for perm in perms {
                        if Self::matches(perm, required_resource, required_action) {
                            return true;
                        }
                    }
                }
            }
        }

        false
    }

    /// Check if a permission string matches a resource:action pair.
    ///
    /// Permissions are `{resource}:{action}` pairs where the action may
    /// itself be dotted (e.g. `quality:ncr:create` has resource `quality`
    /// and action `ncr:create`). Matching rules:
    ///
    /// - `*:*` matches everything (admin).
    /// - A wildcard resource (`*`) or action (`*`) matches any value in its
    ///   position.
    /// - Both components must otherwise match exactly.
    fn matches(permission: &str, resource: &str, action: &str) -> bool {
        if permission == "*:*" {
            return true;
        }

        let Some((perm_resource, perm_action)) = permission.split_once(':') else {
            return false;
        };

        let resource_match = perm_resource == "*" || perm_resource == resource;
        let action_match = perm_action == "*" || perm_action == action;

        resource_match && action_match
    }

    /// Get all permissions for a set of roles.
    pub fn get_permissions(&self, roles: &[String]) -> Vec<String> {
        let mut perms = HashSet::new();
        for role_name in roles {
            if let Some(role_perms) = self.roles.get(role_name.as_str()) {
                perms.extend(role_perms.iter().cloned());
            }
        }
        perms.into_iter().collect()
    }

    /// Check if a role exists.
    pub fn role_exists(&self, role_name: &str) -> bool {
        self.roles.contains_key(role_name)
    }

    /// List all defined roles.
    pub fn list_roles(&self) -> Vec<String> {
        self.roles.keys().cloned().collect()
    }

    /// Permissions a role grants (system roles only).
    pub fn permissions_for_role(&self, role_name: &str) -> Vec<String> {
        let mut perms: Vec<String> = self
            .roles
            .get(role_name)
            .map(|p| p.iter().cloned().collect())
            .unwrap_or_default();
        perms.sort();
        perms.dedup();
        perms
    }

    /// THE effective-permission resolution both HTTP authorization and the
    /// agent layer must consume (item 18): system role permissions UNION
    /// the tenant-scoped custom role when one exists for the caller's
    /// tenant. A user with a valid custom tenant role gets the SAME
    /// permission set in the agent tools as in the HTTP routes.
    pub fn permissions_for_role_in_tenant(&self, tenant_id: Uuid, role_name: &str) -> Vec<String> {
        let mut perms = self.permissions_for_role(role_name);
        if let Some(custom) = self.tenant_roles.get(&(tenant_id, role_name.to_string())) {
            perms.extend(custom.iter().cloned());
        }
        perms.sort();
        perms.dedup();
        perms
    }
}

impl Default for RbacService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_admin_has_all_permissions() {
        let rbac = RbacService::new();
        // The legacy "admin" role is no longer wildcard: only the explicit
        // break-glass platform_superadmin carries *:*.
        let admin_roles = vec!["admin".to_string()];
        assert!(!rbac.has_permission(&admin_roles, &Permission("anything:whatever".to_string())));

        let superadmin_roles = vec!["platform_superadmin".to_string()];
        assert!(rbac.has_permission(
            &superadmin_roles,
            &Permission("anything:whatever".to_string())
        ));
        assert!(rbac.has_permission(
            &superadmin_roles,
            &Permission("quality:ncr:delete".to_string())
        ));
    }

    #[test]
    fn test_quality_manager_permissions() {
        let rbac = RbacService::new();
        let roles = vec!["quality_manager".to_string()];

        assert!(rbac.has_permission(&roles, &Permission("quality:ncr:create".to_string())));
        assert!(rbac.has_permission(&roles, &Permission("quality:ncr:approve".to_string())));
        assert!(!rbac.has_permission(
            &roles,
            &Permission("production:work-order:create".to_string())
        ));
    }

    #[test]
    fn test_user_has_limited_permissions() {
        let rbac = RbacService::new();
        let roles = vec!["user".to_string()];

        assert!(rbac.has_permission(&roles, &Permission("dashboard:read".to_string())));
        assert!(!rbac.has_permission(&roles, &Permission("quality:ncr:create".to_string())));
    }

    #[test]
    fn test_wildcard_matching() {
        assert!(RbacService::matches("*:*", "anything", "anything"));
        assert!(RbacService::matches("*:*", "quality", "ncr:create"));
        assert!(RbacService::matches("quality:*", "quality", "read"));
        assert!(RbacService::matches("quality:*", "quality", "delete"));
        assert!(!RbacService::matches("quality:*", "production", "read"));
        assert!(RbacService::matches("*:read", "quality", "read"));
        assert!(RbacService::matches("*:read", "production", "read"));
        assert!(!RbacService::matches("*:read", "quality", "write"));
    }

    #[test]
    fn test_wildcard_action_matches_dotted_action() {
        // "quality:*" must match the dotted action "ncr:create".
        assert!(RbacService::matches("quality:*", "quality", "ncr:create"));
        assert!(RbacService::matches("quality:*", "quality", "ncr:update"));
        assert!(RbacService::matches("*:*", "quality", "ncr:create"));
        assert!(!RbacService::matches(
            "production:*",
            "quality",
            "ncr:create"
        ));
    }

    #[test]
    fn test_exact_match() {
        assert!(RbacService::matches(
            "quality:ncr:create",
            "quality",
            "ncr:create"
        ));
        assert!(RbacService::matches("users:read", "users", "read"));
        assert!(!RbacService::matches(
            "quality:ncr:read",
            "quality",
            "ncr:create"
        ));
        assert!(!RbacService::matches(
            "quality:ncr:create",
            "production",
            "ncr:create"
        ));
    }

    #[test]
    fn test_malformed_permission_never_matches() {
        assert!(!RbacService::matches("no-colon", "quality", "ncr:create"));
        assert!(!RbacService::matches("", "quality", "ncr:create"));
        assert!(!RbacService::matches(
            "a:b:c:extra",
            "quality",
            "ncr:create"
        ));
    }

    #[test]
    fn test_has_permission_with_dotted_actions() {
        let rbac = RbacService::new();
        let operator = vec!["operator".to_string()];
        assert!(rbac.has_permission(
            &operator,
            &Permission("production:work-order:update-status".to_string())
        ));
        assert!(!rbac.has_permission(
            &operator,
            &Permission("production:work-order:delete".to_string())
        ));
    }
}

//! Role-based access control (RBAC).
//!
//! Provides permission checking against user roles. Permissions are
//! defined as `{resource}:{action}` strings (e.g., `quality:ncr:create`).

use sensei_core::domain::entities::Permission;
use std::collections::{HashMap, HashSet};

/// In-memory RBAC service.
///
/// Maps role names to sets of granted permissions.
pub struct RbacService {
    /// Role definitions: role_name -> set of permissions.
    roles: HashMap<String, HashSet<String>>,
}

impl RbacService {
    /// Create a new [`RbacService`] with default role definitions.
    pub fn new() -> Self {
        let mut svc = Self {
            roles: HashMap::new(),
        };
        svc.load_default_roles();
        svc
    }

    /// Create an empty [`RbacService`] without default roles.
    pub fn empty() -> Self {
        Self {
            roles: HashMap::new(),
        }
    }

    /// Load the default role hierarchy.
    fn load_default_roles(&mut self) {
        // Admin has all permissions (wildcard)
        self.add_role("admin", vec!["*:*"]);
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
                "quality:inspection:read",
                "quality:inspection:create",
            ],
        );

        // Quality technician
        self.add_role(
            "quality_technician",
            vec![
                "quality:ncr:create",
                "quality:ncr:read",
                "quality:ncr:update",
                "quality:capa:read",
                "quality:inspection:read",
                "quality:inspection:create",
            ],
        );

        // Production manager
        self.add_role(
            "production_manager",
            vec![
                "production:work-order:create",
                "production:work-order:read",
                "production:work-order:update",
                "production:work-order:delete",
                "production:schedule:read",
                "production:schedule:update",
            ],
        );

        // Operator
        self.add_role(
            "operator",
            vec![
                "production:work-order:read",
                "production:work-order:update-status",
                "production:work-order:report",
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
    /// Supports wildcard matching:
    /// - `*:*` matches everything
    /// - `quality:*` matches all actions on quality resources
    /// - `*:read` matches read on all resources
    pub fn has_permission(&self, user_roles: &[String], required: &Permission) -> bool {
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
        let admin_roles = vec!["admin".to_string()];

        assert!(rbac.has_permission(&admin_roles, &Permission("anything:whatever".to_string())));
        assert!(rbac.has_permission(&admin_roles, &Permission("quality:ncr:delete".to_string())));
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

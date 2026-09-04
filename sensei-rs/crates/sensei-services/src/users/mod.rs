//! User management domain service.
//!
//! Provides user lookup, creation, and password verification for authentication.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use std::collections::{HashMap, HashSet};
use tokio::sync::RwLock;

mod database;
pub use database::DatabaseUsersService;

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// User management service for authentication and user CRUD.
#[async_trait]
pub trait UsersService: Send + Sync {
    /// Find a user by email address.
    async fn find_by_email(&self, email: &str) -> Result<User>;

    /// Find a user by their unique identifier.
    async fn find_by_id(&self, id: EntityId) -> Result<User>;

    /// Create a new user.
    async fn create_user(&self, user: User) -> Result<User>;

    /// List all users.
    async fn list_users(&self) -> Result<Vec<User>>;

    /// List users with pagination and optional role filter.
    async fn list_users_paginated(
        &self,
        role: Option<&str>,
        is_active: Option<bool>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<User>>;

    /// Verify a plaintext password against the stored hash for the given email.
    async fn verify_password(&self, email: &str, password: &str) -> Result<User>;

    /// Authenticate with a single invariant-enforcing operation.
    ///
    /// Normalizes the email (trim + lowercase), requires the account to be
    /// active, and verifies the Argon2 hash. Unknown email and wrong
    /// password produce the SAME 401 message (no account enumeration); a
    /// disabled account gets its own explicit message.
    async fn authenticate(&self, email: &str, password: &str) -> Result<User>;

    /// Bump the user's credential version (password change/reset) and
    /// return the updated user.
    async fn bump_credential_version(&self, id: EntityId) -> Result<User>;

    /// Create a tenant and its initial user in ONE atomic operation.
    ///
    /// DB mode: a single transaction (INSERT tenant -> INSERT user); the
    /// users.tenant_id FK can never dangle. In-memory mode: both inserts
    /// under one lock.
    async fn create_tenant_with_initial_user(
        &self,
        tenant: sensei_core::domain::entities::Tenant,
        user: User,
    ) -> Result<User>;

    /// Update a user's PROFILE fields only — `name` and `email` (both are
    /// assigned; pass the current value to leave a field unchanged).
    /// `caller_tenant_id` is enforced in the repository: a tenant admin
    /// can only ever touch users of their own tenant, even if a handler
    /// forgets to check.
    ///
    /// Deliberately NOT an authorization-capable mutation
    /// (twenty-ninth audit Wave A): roles, `is_active`,
    /// `credential_version` and `password_hash` are never assigned here —
    /// those live exclusively behind
    /// [`Self::update_user_roles`]/[`Self::deactivate_user`]/
    /// [`Self::activate_user`]/[`Self::change_password`].
    async fn update_profile(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        name: String,
        email: String,
    ) -> Result<User>;

    /// Change a user's password: stores the NEW hash and bumps the
    /// credential version in ONE operation (tenant-scoped). The ONLY
    /// credential mutation — a generic user update can never rewrite
    /// `password_hash` or `credential_version`.
    async fn change_password(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        new_password_hash: String,
    ) -> Result<User>;

    /// Deactivate a user (soft delete). Tenant-scoped (see [`Self::update_profile`]).
    /// Bumps the tenant's principal authorization revision atomically
    /// (DB impl): a deactivated user's authorization caches die with the
    /// deactivation.
    async fn deactivate_user(&self, caller_tenant_id: EntityId, id: EntityId) -> Result<User>;

    /// Reactivate a user. Tenant-scoped (see [`Self::update_profile`]).
    /// Bumps the tenant's principal authorization revision atomically
    /// (DB impl).
    async fn activate_user(&self, caller_tenant_id: EntityId, id: EntityId) -> Result<User>;

    /// Update a user's roles. Tenant-scoped (see [`Self::update_profile`]).
    /// Bumps the tenant's principal authorization revision atomically
    /// (DB impl): a role change is LIVE for the very next request.
    async fn update_user_roles(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        roles: Vec<String>,
    ) -> Result<User>;

    /// Whether the user's email address has been verified.
    async fn is_email_verified(&self, id: EntityId) -> Result<bool>;

    /// Set the email-verified flag for a user.
    async fn set_email_verified(&self, id: EntityId, verified: bool) -> Result<()>;
}

/// Shared password-verification semantics used by every [`UsersService`] impl.
///
/// Maps the auth contract onto service errors:
/// - `Valid` → the user is returned.
/// - `Invalid` → 401 Unauthorized.
/// - `Malformed` → the stored hash is corrupt; log and surface as a 500.
pub(crate) async fn check_password(user: &User, password: &str) -> Result<()> {
    use sensei_auth::password::{verify_password, PasswordCheck};
    match verify_password(password, &user.password_hash)
        .map_err(|e| SenseiError::Internal(format!("Password verification failed: {e}")))?
    {
        PasswordCheck::Valid => Ok(()),
        PasswordCheck::Invalid => Err(SenseiError::Unauthorized(
            "Invalid email or password".to_string(),
        )),
        PasswordCheck::Malformed => {
            tracing::error!(
                user_id = %user.id,
                "Stored password hash for user is malformed; password reset required"
            );
            Err(SenseiError::Internal(
                "Stored password hash is malformed".to_string(),
            ))
        }
    }
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`UsersService`].
///
/// Stores users in a `HashMap<EntityId, User>` behind an `RwLock` so that
/// email renames do not leave stale map keys. Email verification state is
/// tracked in a separate `HashSet` of verified user ids.
pub struct InMemoryUsersService {
    users: RwLock<HashMap<EntityId, User>>,
    verified_emails: RwLock<HashSet<EntityId>>,
}

impl InMemoryUsersService {
    /// Create a new empty [`InMemoryUsersService`].
    pub fn new() -> Self {
        Self {
            users: RwLock::new(HashMap::new()),
            verified_emails: RwLock::new(HashSet::new()),
        }
    }

    /// Create a new [`InMemoryUsersService`] with a pre-seeded admin user.
    pub fn with_admin(
        email: impl Into<String>,
        name: impl Into<String>,
        password_hash: impl Into<String>,
        tenant_id: TenantId,
    ) -> Self {
        let mut users = HashMap::new();
        let email: String = email.into();
        // The whole point of this constructor is an admin bootstrap account:
        // the user must carry the admin role (User::new only grants "user").
        let user = User::with_roles(
            tenant_id,
            email,
            name.into(),
            password_hash.into(),
            vec![
                "user".to_string(),
                "tenant_admin".to_string(),
                "platform_admin".to_string(),
                "finance_manager".to_string(),
                "hr_manager".to_string(),
                "purchasing_manager".to_string(),
                "inventory_manager".to_string(),
                "sales_manager".to_string(),
                "quality_manager".to_string(),
                "production_manager".to_string(),
            ],
        );
        users.insert(user.id, user);
        Self {
            users: RwLock::new(users),
            verified_emails: RwLock::new(HashSet::new()),
        }
    }
}

impl Default for InMemoryUsersService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl UsersService for InMemoryUsersService {
    async fn find_by_email(&self, email: &str) -> Result<User> {
        let users = self.users.read().await;
        users
            .values()
            .find(|u| u.email.eq_ignore_ascii_case(email))
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("User with email '{email}' not found")))
    }

    async fn find_by_id(&self, id: EntityId) -> Result<User> {
        let users = self.users.read().await;
        users
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))
    }

    async fn create_user(&self, user: User) -> Result<User> {
        let mut users = self.users.write().await;
        if users
            .values()
            .any(|u| u.email.eq_ignore_ascii_case(&user.email))
        {
            return Err(SenseiError::AlreadyExists(format!(
                "User with email '{}' already exists",
                user.email
            )));
        }
        users.insert(user.id, user.clone());
        // New users are not email-verified by default.
        Ok(user)
    }

    async fn list_users(&self) -> Result<Vec<User>> {
        let users = self.users.read().await;
        let mut all: Vec<User> = users.values().cloned().collect();
        all.sort_by_key(|u| u.created_at);
        Ok(all)
    }

    async fn verify_password(&self, email: &str, password: &str) -> Result<User> {
        let user = self.find_by_email(email).await?;
        check_password(&user, password).await?;
        Ok(user)
    }

    async fn authenticate(&self, email: &str, password: &str) -> Result<User> {
        let normalized = email.trim().to_lowercase();
        let user = self
            .find_by_email(&normalized)
            .await
            .map_err(|_| SenseiError::Unauthorized("Invalid email or password".to_string()))?;
        if !user.is_active {
            return Err(SenseiError::Unauthorized(
                "Account is disabled. Contact your administrator.".to_string(),
            ));
        }
        check_password(&user, password).await?;
        Ok(user)
    }

    async fn bump_credential_version(&self, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = users
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        user.credential_version = user.credential_version.saturating_add(1);
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn create_tenant_with_initial_user(
        &self,
        tenant: sensei_core::domain::entities::Tenant,
        user: User,
    ) -> Result<User> {
        // Single critical section: both records become visible together.
        let mut users = self.users.write().await;
        if users
            .values()
            .any(|u| u.email.eq_ignore_ascii_case(&user.email))
        {
            return Err(SenseiError::AlreadyExists(format!(
                "User with email '{}' already exists",
                user.email
            )));
        }
        let mut user = user;
        user.tenant_id = tenant.id;
        users.insert(user.id, user.clone());
        Ok(user)
    }

    async fn list_users_paginated(
        &self,
        role: Option<&str>,
        is_active: Option<bool>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<User>> {
        let users = self.users.read().await;
        let items: Vec<_> = users
            .values()
            .filter(|u| {
                role.is_none_or(|r| u.roles.iter().any(|ur| ur == r))
                    && is_active.is_none_or(|act| u.is_active == act)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_profile(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        name: String,
        email: String,
    ) -> Result<User> {
        let mut users = self.users.write().await;
        match users.get(&id) {
            None => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(existing) if existing.tenant_id != caller_tenant_id => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            _ => {}
        }
        // Check email uniqueness before taking the mutable borrow so the
        // immutable scan does not overlap the `get_mut` borrow.
        if users
            .values()
            .any(|u| u.id != id && u.email.eq_ignore_ascii_case(&email))
        {
            return Err(SenseiError::AlreadyExists(format!(
                "User with email '{email}' already exists"
            )));
        }

        let updated_user = {
            let user = users.get_mut(&id).expect("user presence checked above");
            let email_changed = !user.email.eq_ignore_ascii_case(&email);
            user.name = name;
            user.email = email;
            user.updated_at = now();
            (user.clone(), email_changed)
        };
        if updated_user.1 {
            // Verification applied to the OLD address — it must not carry
            // over to the new one.
            self.verified_emails.write().await.remove(&id);
        }
        Ok(updated_user.0)
    }

    async fn change_password(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        new_password_hash: String,
    ) -> Result<User> {
        let mut users = self.users.write().await;
        let user = match users.get(&id) {
            None => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(existing) if existing.tenant_id != caller_tenant_id => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(_) => users.get_mut(&id).expect("presence checked above"),
        };
        user.password_hash = new_password_hash;
        // Every outstanding refresh token/session must die with the old
        // password.
        user.credential_version = user.credential_version.saturating_add(1);
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn deactivate_user(&self, caller_tenant_id: EntityId, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = match users.get(&id) {
            None => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(existing) if existing.tenant_id != caller_tenant_id => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(_) => users.get_mut(&id).expect("presence checked above"),
        };
        user.is_active = false;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn activate_user(&self, caller_tenant_id: EntityId, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = match users.get(&id) {
            None => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(existing) if existing.tenant_id != caller_tenant_id => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(_) => users.get_mut(&id).expect("presence checked above"),
        };
        user.is_active = true;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn update_user_roles(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        roles: Vec<String>,
    ) -> Result<User> {
        validate_roles(&roles)?;
        let mut users = self.users.write().await;
        let user = match users.get(&id) {
            None => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(existing) if existing.tenant_id != caller_tenant_id => {
                return Err(SenseiError::NotFound(format!(
                    "User with id '{id}' not found"
                )));
            }
            Some(_) => users.get_mut(&id).expect("presence checked above"),
        };
        user.roles = roles;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn is_email_verified(&self, id: EntityId) -> Result<bool> {
        let verified = self.verified_emails.read().await;
        Ok(verified.contains(&id))
    }

    async fn set_email_verified(&self, id: EntityId, verified: bool) -> Result<()> {
        let users = self.users.read().await;
        if !users.contains_key(&id) {
            return Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            )));
        }
        drop(users);
        let mut verified_set = self.verified_emails.write().await;
        if verified {
            verified_set.insert(id);
        } else {
            verified_set.remove(&id);
        }
        Ok(())
    }
}

/// Validate role names against the RBAC default role definitions.
///
/// Returns a [`SenseiError::Validation`] when any role is unknown, so typos
/// and role-name drift are caught at the service boundary.
pub(crate) fn validate_roles(roles: &[String]) -> Result<()> {
    let rbac = sensei_auth::rbac::RbacService::new();
    for role in roles {
        // Break-glass superadmin is a static, non-assignable identity.
        if role == "platform_superadmin" {
            return Err(SenseiError::Validation(
                "'platform_superadmin' is a break-glass role and cannot be assigned".to_string(),
            ));
        }
        if !rbac.role_exists(role) {
            return Err(SenseiError::Validation(format!("Unknown role '{role}'")));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn user(email: &str) -> User {
        let mut u = User::new(
            EntityId::new_v4(),
            email.to_string(),
            "Test User".to_string(),
            "hash".to_string(),
        );
        u.id = EntityId::new_v4();
        u
    }

    #[tokio::test]
    async fn rename_email_keeps_find_by_email_working() {
        let svc = InMemoryUsersService::new();
        let created = svc.create_user(user("old@example.com")).await.unwrap();

        let updated = svc
            .update_profile(
                created.tenant_id,
                created.id,
                "New Name".to_string(),
                "new@example.com".to_string(),
            )
            .await
            .unwrap();
        assert_eq!(updated.email, "new@example.com");
        assert_eq!(updated.name, "New Name");

        assert!(svc.find_by_email("old@example.com").await.is_err());
        let found = svc.find_by_email("new@example.com").await.unwrap();
        assert_eq!(found.id, created.id);
        assert_eq!(
            svc.find_by_id(created.id).await.unwrap().email,
            "new@example.com"
        );
    }

    #[tokio::test]
    async fn update_profile_never_touches_authorization_state() {
        let svc = InMemoryUsersService::new();
        let created = svc.create_user(user("profile@example.com")).await.unwrap();
        let updated = svc
            .update_profile(
                created.tenant_id,
                created.id,
                "Profile Only".to_string(),
                "profile@example.com".to_string(),
            )
            .await
            .unwrap();
        assert_eq!(updated.roles, created.roles);
        assert_eq!(updated.is_active, created.is_active);
        assert_eq!(updated.credential_version, created.credential_version);
        assert_eq!(updated.password_hash, created.password_hash);
        assert_eq!(updated.name, "Profile Only");
    }

    #[tokio::test]
    async fn change_password_bumps_credential_version() {
        let svc = InMemoryUsersService::new();
        let created = svc.create_user(user("pw@example.com")).await.unwrap();
        let updated = svc
            .change_password(created.tenant_id, created.id, "new-hash".to_string())
            .await
            .unwrap();
        assert_eq!(updated.password_hash, "new-hash");
        assert_eq!(
            updated.credential_version,
            created.credential_version + 1,
            "a password change bumps the credential version"
        );
    }

    #[tokio::test]
    async fn email_uniqueness_is_enforced() {
        let svc = InMemoryUsersService::new();
        let a = svc.create_user(user("a@example.com")).await.unwrap();
        let mut b = user("b@example.com");
        b.email = "a@example.com".to_string();
        assert!(matches!(
            svc.create_user(b).await,
            Err(SenseiError::AlreadyExists(_))
        ));
        let _ = a;
    }

    #[tokio::test]
    async fn email_verified_defaults_false_and_settable() {
        let svc = InMemoryUsersService::new();
        let created = svc.create_user(user("v@example.com")).await.unwrap();
        assert!(!svc.is_email_verified(created.id).await.unwrap());
        svc.set_email_verified(created.id, true).await.unwrap();
        assert!(svc.is_email_verified(created.id).await.unwrap());
        svc.set_email_verified(created.id, false).await.unwrap();
        assert!(!svc.is_email_verified(created.id).await.unwrap());
    }

    #[tokio::test]
    async fn update_user_roles_validates_against_rbac_defaults() {
        let svc = InMemoryUsersService::new();
        let created = svc.create_user(user("roles@example.com")).await.unwrap();
        let updated = svc
            .update_user_roles(
                created.tenant_id,
                created.id,
                vec!["finance_manager".to_string()],
            )
            .await
            .unwrap();
        assert_eq!(updated.roles, vec!["finance_manager".to_string()]);

        let err = svc
            .update_user_roles(
                created.tenant_id,
                created.id,
                vec!["not_a_real_role".to_string()],
            )
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));
    }
}

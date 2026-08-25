//! User management domain service.
//!
//! Provides user lookup, creation, and password verification for authentication.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{EntityId, TenantId, now};
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

    /// Update a user's profile fields.
    async fn update_user(&self, id: EntityId, user: User) -> Result<User>;

    /// Deactivate a user (soft delete).
    async fn deactivate_user(&self, id: EntityId) -> Result<User>;

    /// Reactivate a user.
    async fn activate_user(&self, id: EntityId) -> Result<User>;

    /// Update a user's roles.
    async fn update_user_roles(&self, id: EntityId, roles: Vec<String>) -> Result<User>;

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
    use sensei_auth::password::{PasswordCheck, verify_password};
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
        let user = User::new(tenant_id, email, name.into(), password_hash.into());
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
            .ok_or_else(|| {
                SenseiError::NotFound(format!("User with email '{email}' not found"))
            })
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

    async fn update_user(&self, id: EntityId, updated: User) -> Result<User> {
        let mut users = self.users.write().await;
        if !users.contains_key(&id) {
            return Err(SenseiError::NotFound(format!("User with id '{id}' not found")));
        }
        // Check email uniqueness before taking the mutable borrow so the
        // immutable scan does not overlap the `get_mut` borrow.
        if users
            .values()
            .any(|u| u.id != id && u.email.eq_ignore_ascii_case(&updated.email))
        {
            return Err(SenseiError::AlreadyExists(format!(
                "User with email '{}' already exists",
                updated.email
            )));
        }

        let user = users
            .get_mut(&id)
            .expect("user presence checked above");
        user.name = updated.name;
        user.email = updated.email;
        user.password_hash = updated.password_hash;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn deactivate_user(&self, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = users
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        user.is_active = false;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn activate_user(&self, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = users
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        user.is_active = true;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn update_user_roles(&self, id: EntityId, roles: Vec<String>) -> Result<User> {
        validate_roles(&roles)?;
        let mut users = self.users.write().await;
        let user = users
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
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
            return Err(SenseiError::NotFound(format!("User with id '{id}' not found")));
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
        if !rbac.role_exists(role) {
            return Err(SenseiError::Validation(format!(
                "Unknown role '{role}'"
            )));
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
        let mut renamed = created.clone();
        renamed.email = "new@example.com".to_string();

        let updated = svc.update_user(created.id, renamed).await.unwrap();
        assert_eq!(updated.email, "new@example.com");

        assert!(svc.find_by_email("old@example.com").await.is_err());
        let found = svc.find_by_email("new@example.com").await.unwrap();
        assert_eq!(found.id, created.id);
        assert_eq!(svc.find_by_id(created.id).await.unwrap().email, "new@example.com");
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
            .update_user_roles(created.id, vec!["admin".to_string()])
            .await
            .unwrap();
        assert_eq!(updated.roles, vec!["admin".to_string()]);

        let err = svc
            .update_user_roles(created.id, vec!["not_a_real_role".to_string()])
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Validation(_)));
    }
}

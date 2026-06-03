//! User management domain service.
//!
//! Provides user lookup, creation, and password verification for authentication.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{EntityId, TenantId, now};
use std::collections::HashMap;
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
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`UsersService`].
///
/// Stores users in a `HashMap<String, User>` behind an `RwLock`.
/// Suitable for development, testing, and demo environments.
pub struct InMemoryUsersService {
    users: RwLock<HashMap<String, User>>,
}

impl InMemoryUsersService {
    /// Create a new empty [`InMemoryUsersService`].
    pub fn new() -> Self {
        Self {
            users: RwLock::new(HashMap::new()),
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
        let user = User::new(tenant_id, email.clone(), name.into(), password_hash.into());
        users.insert(email.clone(), user);
        Self {
            users: RwLock::new(users),
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
        users.get(email).cloned().ok_or_else(|| {
            SenseiError::NotFound(format!("User with email '{email}' not found"))
        })
    }

    async fn find_by_id(&self, id: EntityId) -> Result<User> {
        let users = self.users.read().await;
        users
            .values()
            .find(|u| u.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))
    }

    async fn create_user(&self, user: User) -> Result<User> {
        let mut users = self.users.write().await;
        if users.contains_key(&user.email) {
            return Err(SenseiError::AlreadyExists(format!(
                "User with email '{}' already exists",
                user.email
            )));
        }
        let email = user.email.clone();
        users.insert(email, user.clone());
        Ok(user)
    }

    async fn list_users(&self) -> Result<Vec<User>> {
        let users = self.users.read().await;
        Ok(users.values().cloned().collect())
    }

    async fn verify_password(&self, email: &str, password: &str) -> Result<User> {
        let user = self.find_by_email(email).await?;
        let valid = sensei_auth::password::verify_password(password, &user.password_hash)
            .map_err(|e| SenseiError::Internal(format!("Password verification failed: {e}")))?;
        if !valid {
            return Err(SenseiError::Unauthorized("Invalid email or password".to_string()));
        }
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
        let user = users
            .values_mut()
            .find(|u| u.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        user.name = updated.name;
        user.email = updated.email;
        user.password_hash = updated.password_hash;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn deactivate_user(&self, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = users
            .values_mut()
            .find(|u| u.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        user.is_active = false;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn activate_user(&self, id: EntityId) -> Result<User> {
        let mut users = self.users.write().await;
        let user = users
            .values_mut()
            .find(|u| u.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        user.is_active = true;
        user.updated_at = now();
        Ok(user.clone())
    }

    async fn update_user_roles(&self, id: EntityId, roles: Vec<String>) -> Result<User> {
        let mut users = self.users.write().await;
        let user = users
            .values_mut()
            .find(|u| u.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        user.roles = roles;
        user.updated_at = now();
        Ok(user.clone())
    }
}

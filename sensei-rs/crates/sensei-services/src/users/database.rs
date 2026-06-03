//! PostgreSQL-backed users service using sqlx.
//!
//! Provides user management backed by the `users` database table.
//! Implements the [`UsersService`] trait with real SQL queries.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::EntityId;
use sensei_db::models::UserModel;
use sqlx::PgPool;

use crate::users::UsersService;

/// PostgreSQL-backed implementation of [`UsersService`].
pub struct DatabaseUsersService {
    pool: PgPool,
}

impl DatabaseUsersService {
    /// Create a new [`DatabaseUsersService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

/// Convert a database [`UserModel`] into a domain [`User`].
///
/// The `roles` field in the database model is stored as a comma-separated string;
/// this conversion splits it into a vector of role names.
fn user_model_to_domain(m: UserModel) -> User {
    let roles: Vec<String> = if m.roles.is_empty() {
        Vec::new()
    } else {
        m.roles.split(',').map(|s| s.trim().to_string()).collect()
    };

    User {
        id: m.id,
        tenant_id: m.tenant_id,
        email: m.email,
        name: m.name,
        password_hash: m.password_hash,
        roles,
        is_active: m.is_active,
        last_login_at: m.last_login_at,
        created_at: m.created_at,
        updated_at: m.updated_at,
    }
}

/// Convert a domain [`User`] into a database [`UserModel`].
///
/// The `roles` vector is joined into a comma-separated string for storage.
#[allow(dead_code)]
fn user_to_model(u: User) -> UserModel {
    UserModel {
        id: u.id,
        tenant_id: u.tenant_id,
        email: u.email,
        name: u.name,
        password_hash: u.password_hash,
        roles: u.roles.join(","),
        is_active: u.is_active,
        last_login_at: u.last_login_at,
        created_at: u.created_at,
        updated_at: u.updated_at,
    }
}

#[async_trait]
impl UsersService for DatabaseUsersService {
    async fn find_by_email(&self, email: &str) -> Result<User> {
        let model = sqlx::query_as::<_, UserModel>(
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE email = $1
            "#,
        )
        .bind(email)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to find user by email: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with email '{email}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn find_by_id(&self, id: EntityId) -> Result<User> {
        let model = sqlx::query_as::<_, UserModel>(
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE id = $1
            "#,
        )
        .bind(id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to find user by id: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn create_user(&self, user: User) -> Result<User> {
        let now = Utc::now();

        // Check for duplicate email first.
        let existing = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM users WHERE email = $1",
        )
        .bind(&user.email)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to check duplicate user: {e}")))?;

        if existing > 0 {
            return Err(SenseiError::AlreadyExists(format!(
                "User with email '{}' already exists",
                user.email
            )));
        }

        let roles_str = user.roles.join(",");

        let model = sqlx::query_as::<_, UserModel>(
            r#"
            INSERT INTO users (id, tenant_id, email, name, password_hash, roles,
                               is_active, last_login_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, tenant_id, email, name, password_hash, roles,
                      is_active, last_login_at, created_at, updated_at
            "#,
        )
        .bind(user.id)
        .bind(user.tenant_id)
        .bind(&user.email)
        .bind(&user.name)
        .bind(&user.password_hash)
        .bind(&roles_str)
        .bind(user.is_active)
        .bind(user.last_login_at)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create user: {e}")))?;

        Ok(user_model_to_domain(model))
    }

    async fn list_users(&self) -> Result<Vec<User>> {
        let models = sqlx::query_as::<_, UserModel>(
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            "#,
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list users: {e}")))?;

        Ok(models.into_iter().map(user_model_to_domain).collect())
    }

    async fn list_users_paginated(
        &self,
        role: Option<&str>,
        is_active: Option<bool>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<User>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        // Build dynamic filtering
        let use_role_filter = role.is_some();
        let use_active_filter = is_active.is_some();
        let role_val = role.unwrap_or("");
        let active_val = is_active.unwrap_or(true);

        // Count query
        let count_sql = if use_role_filter && use_active_filter {
            "SELECT COUNT(*) FROM users WHERE roles LIKE $1 AND is_active = $2"
        } else if use_role_filter {
            "SELECT COUNT(*) FROM users WHERE roles LIKE $1"
        } else if use_active_filter {
            "SELECT COUNT(*) FROM users WHERE is_active = $1"
        } else {
            "SELECT COUNT(*) FROM users"
        };

        let total: i64 = if use_role_filter && use_active_filter {
            sqlx::query_scalar(count_sql)
                .bind(format!("%{}%", role_val))
                .bind(active_val)
                .fetch_one(&self.pool)
                .await
        } else if use_role_filter {
            sqlx::query_scalar(count_sql)
                .bind(format!("%{}%", role_val))
                .fetch_one(&self.pool)
                .await
        } else if use_active_filter {
            sqlx::query_scalar(count_sql)
                .bind(active_val)
                .fetch_one(&self.pool)
                .await
        } else {
            sqlx::query_scalar(count_sql)
                .fetch_one(&self.pool)
                .await
        }
        .map_err(|e| SenseiError::Database(format!("Failed to count users: {e}")))?;

        let total = total as usize;

        // Data query
        let data_sql = if use_role_filter && use_active_filter {
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE roles LIKE $1 AND is_active = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            "#
        } else if use_role_filter {
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE roles LIKE $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            "#
        } else if use_active_filter {
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            WHERE is_active = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            "#
        } else {
            r#"
            SELECT id, tenant_id, email, name, password_hash, roles,
                   is_active, last_login_at, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            "#
        };

        let models: Vec<UserModel> = if use_role_filter && use_active_filter {
            sqlx::query_as(data_sql)
                .bind(format!("%{}%", role_val))
                .bind(active_val)
                .bind(per_page as i64)
                .bind(offset as i64)
                .fetch_all(&self.pool)
                .await
        } else if use_role_filter {
            sqlx::query_as(data_sql)
                .bind(format!("%{}%", role_val))
                .bind(per_page as i64)
                .bind(offset as i64)
                .fetch_all(&self.pool)
                .await
        } else if use_active_filter {
            sqlx::query_as(data_sql)
                .bind(active_val)
                .bind(per_page as i64)
                .bind(offset as i64)
                .fetch_all(&self.pool)
                .await
        } else {
            sqlx::query_as(data_sql)
                .bind(per_page as i64)
                .bind(offset as i64)
                .fetch_all(&self.pool)
                .await
        }
        .map_err(|e| SenseiError::Database(format!("Failed to list users: {e}")))?;

        let data = models.into_iter().map(user_model_to_domain).collect();

        let total_pages = total.div_ceil(per_page).max(1);

        Ok(PaginatedResponse {
            data,
            total,
            page,
            per_page,
            total_pages,
        })
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

    async fn update_user(&self, id: EntityId, updated: User) -> Result<User> {
        let now = Utc::now();
        let roles_str = updated.roles.join(",");

        let model = sqlx::query_as::<_, UserModel>(
            r#"
            UPDATE users
            SET name = $2, email = $3, password_hash = $4, roles = $5,
                is_active = $6, updated_at = $7
            WHERE id = $1
            RETURNING id, tenant_id, email, name, password_hash, roles,
                      is_active, last_login_at, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(&updated.name)
        .bind(&updated.email)
        .bind(&updated.password_hash)
        .bind(&roles_str)
        .bind(updated.is_active)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update user: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn deactivate_user(&self, id: EntityId) -> Result<User> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, UserModel>(
            r#"
            UPDATE users
            SET is_active = false, updated_at = $2
            WHERE id = $1
            RETURNING id, tenant_id, email, name, password_hash, roles,
                      is_active, last_login_at, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to deactivate user: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn activate_user(&self, id: EntityId) -> Result<User> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, UserModel>(
            r#"
            UPDATE users
            SET is_active = true, updated_at = $2
            WHERE id = $1
            RETURNING id, tenant_id, email, name, password_hash, roles,
                      is_active, last_login_at, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to activate user: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn update_user_roles(&self, id: EntityId, roles: Vec<String>) -> Result<User> {
        let now = Utc::now();
        let roles_str = roles.join(",");

        let model = sqlx::query_as::<_, UserModel>(
            r#"
            UPDATE users
            SET roles = $2, updated_at = $3
            WHERE id = $1
            RETURNING id, tenant_id, email, name, password_hash, roles,
                      is_active, last_login_at, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(&roles_str)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update user roles: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }
}

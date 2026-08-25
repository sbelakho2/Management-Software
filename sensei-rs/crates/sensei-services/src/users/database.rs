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

use super::{UsersService, check_password, validate_roles};

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
/// The `roles` field in the database model is stored as a PostgreSQL
/// `TEXT[]` array and maps directly onto the domain's `Vec<String>`.
fn user_model_to_domain(m: UserModel) -> User {
    User {
        id: m.id,
        tenant_id: m.tenant_id,
        email: m.email,
        name: m.name,
        password_hash: m.password_hash,
        roles: m.roles,
        is_active: m.is_active,
        last_login_at: m.last_login_at,
        created_at: m.created_at,
        updated_at: m.updated_at,
    }
}

/// Convert a domain [`User`] into a database [`UserModel`].
///
/// The `roles` vector is stored as a PostgreSQL `TEXT[]` array.
fn user_to_model(u: User, email_verified: bool) -> UserModel {
    UserModel {
        id: u.id,
        tenant_id: u.tenant_id,
        email: u.email,
        name: u.name,
        password_hash: u.password_hash,
        roles: u.roles,
        is_active: u.is_active,
        email_verified,
        last_login_at: u.last_login_at,
        created_at: u.created_at,
        updated_at: u.updated_at,
    }
}

const USER_COLUMNS: &str = "id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, last_login_at, created_at, updated_at";

#[async_trait]
impl UsersService for DatabaseUsersService {
    async fn find_by_email(&self, email: &str) -> Result<User> {
        let model = sqlx::query_as::<_, UserModel>(&format!(
            "SELECT {USER_COLUMNS} FROM users WHERE email = $1"
        ))
        .bind(email)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to find user by email: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with email '{email}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn find_by_id(&self, id: EntityId) -> Result<User> {
        let model = sqlx::query_as::<_, UserModel>(&format!(
            "SELECT {USER_COLUMNS} FROM users WHERE id = $1"
        ))
        .bind(id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to find user by id: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn create_user(&self, user: User) -> Result<User> {
        let now = Utc::now();
        let model = user_to_model(user.clone(), false);

        let created = sqlx::query_as::<_, UserModel>(
            "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, \
                                is_active, email_verified, last_login_at, created_at, updated_at) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) \
             ON CONFLICT (tenant_id, email) DO NOTHING \
             RETURNING id, tenant_id, email, name, password_hash, roles, \
                       is_active, email_verified, last_login_at, created_at, updated_at",
        )
        .bind(model.id)
        .bind(model.tenant_id)
        .bind(&model.email)
        .bind(&model.name)
        .bind(&model.password_hash)
        .bind(&model.roles)
        .bind(model.is_active)
        .bind(model.email_verified)
        .bind(model.last_login_at)
        .bind(now)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create user: {e}")))?
        .ok_or_else(|| {
            SenseiError::AlreadyExists(format!(
                "User with email '{}' already exists",
                user.email
            ))
        })?;

        Ok(user_model_to_domain(created))
    }

    async fn list_users(&self) -> Result<Vec<User>> {
        let models = sqlx::query_as::<_, UserModel>(&format!(
            "SELECT {USER_COLUMNS} FROM users ORDER BY created_at DESC"
        ))
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

        // Exact array membership: `$n = ANY(roles)` — no false positives
        // from substring matching ('admin' must not match 'admin2').
        let (count_sql, data_sql): (&str, &str) = match (role, is_active) {
                (Some(_), Some(_)) => (
                    "SELECT COUNT(*) FROM users WHERE $1 = ANY(roles) AND is_active = $2",
                    "SELECT id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, last_login_at, created_at, updated_at \
                     FROM users WHERE $1 = ANY(roles) AND is_active = $2 \
                     ORDER BY created_at DESC LIMIT $3 OFFSET $4",
                ),
                (Some(_), None) => (
                    "SELECT COUNT(*) FROM users WHERE $1 = ANY(roles)",
                    "SELECT id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, last_login_at, created_at, updated_at \
                     FROM users WHERE $1 = ANY(roles) \
                     ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                ),
                (None, Some(_)) => (
                    "SELECT COUNT(*) FROM users WHERE is_active = $1",
                    "SELECT id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, last_login_at, created_at, updated_at \
                     FROM users WHERE is_active = $1 \
                     ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                ),
                (None, None) => (
                    "SELECT COUNT(*) FROM users",
                    "SELECT id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, last_login_at, created_at, updated_at \
                     FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                ),
            };

        let mut count_query = sqlx::query_scalar::<_, i64>(count_sql);
        if let Some(r) = role {
            count_query = count_query.bind(r);
        }
        if let Some(act) = is_active {
            count_query = count_query.bind(act);
        }
        let total: i64 = count_query
            .fetch_one(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to count users: {e}")))?;

        let mut data_query = sqlx::query_as::<_, UserModel>(data_sql);
        if let Some(r) = role {
            data_query = data_query.bind(r);
        }
        if let Some(act) = is_active {
            data_query = data_query.bind(act);
        }
        data_query = data_query.bind(per_page as i64).bind(offset as i64);
        let models: Vec<UserModel> = data_query
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to list users: {e}")))?;

        let data = models.into_iter().map(user_model_to_domain).collect();
        let total_pages = ((total as usize).max(1) + per_page - 1) / per_page;

        Ok(PaginatedResponse {
            data,
            total: total as usize,
            page,
            per_page,
            total_pages,
        })
    }

    async fn verify_password(&self, email: &str, password: &str) -> Result<User> {
        let user = self.find_by_email(email).await?;
        check_password(&user, password).await?;
        Ok(user)
    }

    async fn update_user(&self, id: EntityId, updated: User) -> Result<User> {
        let now = Utc::now();
        let verified = self.is_email_verified(id).await.unwrap_or(false);
        let model = user_to_model(updated, verified);

        let result = sqlx::query_as::<_, UserModel>(
            "UPDATE users \
             SET name = $2, email = $3, password_hash = $4, roles = $5, \
                 is_active = $6, updated_at = $7 \
             WHERE id = $1 \
             RETURNING id, tenant_id, email, name, password_hash, roles, \
                       is_active, email_verified, last_login_at, created_at, updated_at",
        )
        .bind(id)
        .bind(&model.name)
        .bind(&model.email)
        .bind(&model.password_hash)
        .bind(&model.roles)
        .bind(model.is_active)
        .bind(now)
        .fetch_optional(&self.pool)
        .await;

        match result {
            Ok(Some(model)) => Ok(user_model_to_domain(model)),
            Ok(None) => Err(SenseiError::NotFound(format!("User with id '{id}' not found"))),
            Err(e) if is_unique_violation(&e) => Err(SenseiError::AlreadyExists(
                "A user with that email already exists".to_string(),
            )),
            Err(e) => Err(SenseiError::Database(format!("Failed to update user: {e}"))),
        }
    }

    async fn deactivate_user(&self, id: EntityId) -> Result<User> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, UserModel>(
            "UPDATE users \
             SET is_active = false, updated_at = $2 \
             WHERE id = $1 \
             RETURNING id, tenant_id, email, name, password_hash, roles, \
                       is_active, email_verified, last_login_at, created_at, updated_at",
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
            "UPDATE users \
             SET is_active = true, updated_at = $2 \
             WHERE id = $1 \
             RETURNING id, tenant_id, email, name, password_hash, roles, \
                       is_active, email_verified, last_login_at, created_at, updated_at",
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
        validate_roles(&roles)?;
        let now = Utc::now();

        let model = sqlx::query_as::<_, UserModel>(
            "UPDATE users \
             SET roles = $2, updated_at = $3 \
             WHERE id = $1 \
             RETURNING id, tenant_id, email, name, password_hash, roles, \
                       is_active, email_verified, last_login_at, created_at, updated_at",
        )
        .bind(id)
        .bind(&roles)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update user roles: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;

        Ok(user_model_to_domain(model))
    }

    async fn is_email_verified(&self, id: EntityId) -> Result<bool> {
        sqlx::query_scalar::<_, bool>("SELECT email_verified FROM users WHERE id = $1")
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read email_verified: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))
    }

    async fn set_email_verified(&self, id: EntityId, verified: bool) -> Result<()> {
        let result = sqlx::query("UPDATE users SET email_verified = $2 WHERE id = $1")
            .bind(id)
            .bind(verified)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to set email_verified: {e}")))?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("User with id '{id}' not found")));
        }
        Ok(())
    }
}

/// Detect PostgreSQL unique-violation errors (SQLSTATE 23505).
fn is_unique_violation(e: &sqlx::Error) -> bool {
    matches!(
        e,
        sqlx::Error::Database(db)
            if db.code().as_deref() == Some("23505")
    )
}

//! PostgreSQL-backed users service using sqlx.
//!
//! Provides user management backed by the `users` database table.
//! Implements the [`UsersService`] trait with real SQL queries.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::db::TenantTx;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::EntityId;
use sensei_db::models::UserModel;
use sqlx::PgPool;

use super::{check_password, UsersService};

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
        credential_version: m.credential_version.max(0) as u64,
        site_id: m.site_id,
        locale: m.locale,
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
        credential_version: u.credential_version as i64,
        site_id: u.site_id,
        locale: u.locale,
        last_login_at: u.last_login_at,
        created_at: u.created_at,
        updated_at: u.updated_at,
    }
}

const USER_COLUMNS: &str = "id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, credential_version, site_id, locale, \
                            last_login_at, created_at, updated_at";

/// The users-service read surface (thirtieth-audit item 18): `users` is
/// FORCE RLS with the universal fail-closed tenant_isolation policy —
/// NO context means NO rows — so a raw-pool read returns nothing under
/// the production sensei_app role. Reads that run BEFORE any
/// app.tenant_id can exist (login's globally-unique email lookup, the
/// pre-tenant bootstrap flows, tenant-wide admin listing) go through the
/// SECURITY DEFINER identity functions migration 175 created: their
/// bodies run as the BYPASSRLS migration owner and the app role holds
/// EXECUTE on exactly those three functions (never PUBLIC). Reads that
/// HAVE a tenant context run inside a TenantTx instead — see
/// update_profile/change_password/deactivate/activate/update_user_roles.
const AUTH_USER_BY_EMAIL: &str = "auth_user_by_email";
const AUTH_USER_BY_ID: &str = "auth_user_by_id";
const AUTH_USERS_ALL: &str = "auth_users_all";

#[async_trait]
impl UsersService for DatabaseUsersService {
    async fn find_by_email(&self, email: &str) -> Result<User> {
        // Pre-tenant identity channel (migration 175): the email is the
        // platform-unique login identity, so the lookup legitimately
        // crosses tenants through auth_user_by_email(text) — the ONLY
        // no-context users reader left for sensei_app.
        let model =
            sqlx::query_as::<_, UserModel>(&format!("SELECT * FROM {AUTH_USER_BY_EMAIL}($1)"))
                .bind(email)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to find user by email: {e}")))?
                .ok_or_else(|| {
                    SenseiError::NotFound(format!("User with email '{email}' not found"))
                })?;

        Ok(user_model_to_domain(model))
    }

    async fn find_by_id(&self, id: EntityId) -> Result<User> {
        // Cross-tenant id lookup (migration 175): callers enforce their
        // own tenant authorization AFTER the fetch (the id is a global
        // primary key) — see routes/users.rs get_user/update_user and
        // routes/admin.rs, which reject rows whose tenant is not the
        // caller's.
        let model = sqlx::query_as::<_, UserModel>(&format!("SELECT * FROM {AUTH_USER_BY_ID}($1)"))
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

        // The users table is fail-closed FORCE RLS: the INSERT must run
        // inside the tenant context of the row's own tenant_id (migration
        // 175 canonical WITH CHECK), so the whole statement executes in a
        // TenantTx of user.tenant_id.
        let mut db = TenantTx::begin(&self.pool, model.tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin user create: {e}")))?;

        let created = sqlx::query_as::<_, UserModel>(&format!(
            "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, \
                                    is_active, email_verified, credential_version, site_id, locale, \
                                    last_login_at, created_at, updated_at) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14) \
                 ON CONFLICT (tenant_id, email) DO NOTHING \
                 RETURNING {USER_COLUMNS}"
        ))
        .bind(model.id)
        .bind(model.tenant_id)
        .bind(&model.email)
        .bind(&model.name)
        .bind(&model.password_hash)
        .bind(&model.roles)
        .bind(model.is_active)
        .bind(model.email_verified)
        .bind(model.credential_version)
        .bind(model.site_id)
        .bind(&model.locale)
        .bind(model.last_login_at)
        .bind(now)
        .bind(now)
        .fetch_optional(&mut **db.tx())
        .await;

        let created = match created {
            Ok(Some(row)) => row,
            Ok(None) => {
                db.rollback().await.ok();
                return Err(SenseiError::AlreadyExists(format!(
                    "User with email '{}' already exists",
                    user.email
                )));
            }
            Err(e) => {
                db.rollback().await.ok();
                // The global normalized-email index rejects cross-tenant
                // duplicates even though the tenant-scoped ON CONFLICT does not
                // fire — surface it as a friendly conflict, not a 500.
                if is_unique_violation(&e) {
                    return Err(SenseiError::AlreadyExists(format!(
                        "User with email '{}' already exists",
                        user.email
                    )));
                }
                return Err(SenseiError::Database(format!("Failed to create user: {e}")));
            }
        };
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit user create: {e}")))?;

        Ok(user_model_to_domain(created))
    }

    async fn list_users(&self) -> Result<Vec<User>> {
        // Tenant-wide admin listing via the migration-175 definer
        // channel: the service semantics (mirrored by the in-memory
        // implementation) are "all users; the caller scopes" — the route
        // layer filters by the caller's tenant, and the pre-tenant
        // notification-trigger worker resolves role targets across the
        // deployment.
        let models = sqlx::query_as::<_, UserModel>(&format!(
            "SELECT {USER_COLUMNS} FROM {AUTH_USERS_ALL}() ORDER BY created_at DESC"
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
        // The source is the migration-175 definer channel (see
        // `list_users`): the count and the page both read the same
        // cross-tenant snapshot and the caller scopes.
        let (count_sql, data_sql): (String, String) = match (role, is_active) {
            (Some(_), Some(_)) => (
                format!(
                    "SELECT COUNT(*) FROM {AUTH_USERS_ALL}() WHERE $1 = ANY(roles) AND is_active = $2"
                ),
                format!(
                    "SELECT {USER_COLUMNS} \
                     FROM {AUTH_USERS_ALL}() WHERE $1 = ANY(roles) AND is_active = $2 \
                     ORDER BY created_at DESC LIMIT $3 OFFSET $4"
                ),
            ),
            (Some(_), None) => (
                format!("SELECT COUNT(*) FROM {AUTH_USERS_ALL}() WHERE $1 = ANY(roles)"),
                format!(
                    "SELECT {USER_COLUMNS} \
                     FROM {AUTH_USERS_ALL}() WHERE $1 = ANY(roles) \
                     ORDER BY created_at DESC LIMIT $2 OFFSET $3"
                ),
            ),
            (None, Some(_)) => (
                format!("SELECT COUNT(*) FROM {AUTH_USERS_ALL}() WHERE is_active = $1"),
                format!(
                    "SELECT {USER_COLUMNS} \
                     FROM {AUTH_USERS_ALL}() WHERE is_active = $1 \
                     ORDER BY created_at DESC LIMIT $2 OFFSET $3"
                ),
            ),
            (None, None) => (
                format!("SELECT COUNT(*) FROM {AUTH_USERS_ALL}()"),
                format!(
                    "SELECT {USER_COLUMNS} \
                     FROM {AUTH_USERS_ALL}() ORDER BY created_at DESC LIMIT $1 OFFSET $2"
                ),
            ),
        };

        let mut count_query = sqlx::query_scalar::<_, i64>(&count_sql);
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

        let mut data_query = sqlx::query_as::<_, UserModel>(&data_sql);
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
        let total_pages = (total as usize).max(1).div_ceil(per_page);

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
        // Thirtieth-audit item 18 (Wave C RLS): `users` is fail-closed
        // FORCE RLS (migration 175), so the UPDATE must run inside a
        // TenantTx of the row's own tenant. The tenant is resolved through
        // the pre-tenant identity channel (auth_user_by_id) — the caller
        // has only the global user id.
        let row_tenant: Option<EntityId> =
            sqlx::query_scalar(&format!("SELECT tenant_id FROM {AUTH_USER_BY_ID}($1)"))
                .bind(id)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to resolve user tenant: {e}"))
                })?;
        let tenant_id = row_tenant
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        let mut db = TenantTx::begin(&self.pool, tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin credential bump: {e}")))?;
        let model = sqlx::query_as::<_, UserModel>(&format!(
            "UPDATE users SET credential_version = credential_version + 1, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2 \
             RETURNING {USER_COLUMNS}"
        ))
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to bump credential version: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit credential bump: {e}")))?;
        Ok(user_model_to_domain(model))
    }

    async fn create_tenant_with_initial_user(
        &self,
        tenant: sensei_core::domain::entities::Tenant,
        user: User,
    ) -> Result<User> {
        // One transaction: the users.tenant_id FK can never dangle. The
        // registration flow creates a BRAND-NEW tenant, so the tenant
        // context is the new tenant's own id — set before any statement,
        // which admits the users INSERT under the fail-closed WITH CHECK
        // (tenants itself has no tenant_id column and no RLS).
        let mut db = TenantTx::begin(&self.pool, tenant.id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin registration: {e}")))?;

        sqlx::query(
            "INSERT INTO tenants (id, name, slug, is_active, features, created_at, updated_at) \
             VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW())",
        )
        .bind(tenant.id)
        .bind(&tenant.name)
        .bind(&tenant.slug)
        .bind(tenant.is_active)
        .bind(serde_json::to_string(&tenant.features).unwrap_or_else(|_| "{}".to_string()))
        .execute(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create tenant: {e}")))?;

        let mut user = user;
        user.tenant_id = tenant.id;
        let model = user_to_model(user.clone(), false);
        sqlx::query(
            "INSERT INTO users (id, tenant_id, email, name, password_hash, roles, is_active, \
                                email_verified, credential_version, last_login_at, created_at, updated_at) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NULL, NOW(), NOW())",
        )
        .bind(model.id)
        .bind(model.tenant_id)
        .bind(&model.email)
        .bind(&model.name)
        .bind(&model.password_hash)
        .bind(&model.roles)
        .bind(model.is_active)
        .bind(model.email_verified)
        .bind(model.credential_version)
        .execute(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create initial user: {e}")))?;

        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit registration: {e}")))?;
        Ok(user)
    }

    async fn update_profile(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        name: String,
        email: String,
    ) -> Result<User> {
        // Profile-only mutation (twenty-ninth audit Wave A): assigns ONLY
        // name/email (plus the email_verified reset on an address change).
        // roles / is_active / credential_version / password_hash are never
        // written here — they live exclusively behind update_user_roles /
        // deactivate_user / activate_user / change_password. The users
        // table is FORCE RLS, so the update runs inside a tenant-scoped
        // transaction (the production non-owner role needs the context).
        let mut db = TenantTx::begin(&self.pool, caller_tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin profile update: {e}")))?;

        let result = sqlx::query_as::<_, UserModel>(&format!(
            "UPDATE users \
             SET name = $2, email = $3, \
                 email_verified = CASE WHEN email <> $3 THEN false ELSE email_verified END, \
                 updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $4 \
             RETURNING {USER_COLUMNS}"
        ))
        .bind(id)
        .bind(&name)
        .bind(&email)
        .bind(caller_tenant_id)
        .fetch_optional(&mut **db.tx())
        .await;

        match result {
            Ok(Some(model)) => {
                db.commit().await.map_err(|e| {
                    SenseiError::Database(format!("Failed to commit profile update: {e}"))
                })?;
                Ok(user_model_to_domain(model))
            }
            Ok(None) => Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            ))),
            Err(e) if is_unique_violation(&e) => Err(SenseiError::AlreadyExists(
                "A user with that email already exists".to_string(),
            )),
            Err(e) => Err(SenseiError::Database(format!(
                "Failed to update user profile: {e}"
            ))),
        }
    }

    async fn change_password(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        new_password_hash: String,
    ) -> Result<User> {
        // The ONLY credential mutation: stores the new hash and bumps the
        // credential version atomically (refresh tokens and sessions die
        // with the old password). Tenant-scoped transaction (FORCE RLS).
        let mut db = TenantTx::begin(&self.pool, caller_tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin password change: {e}")))?;

        let result = sqlx::query_as::<_, UserModel>(&format!(
            "UPDATE users \
             SET password_hash = $3, credential_version = credential_version + 1, \
                 updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2 \
             RETURNING {USER_COLUMNS}"
        ))
        .bind(id)
        .bind(caller_tenant_id)
        .bind(&new_password_hash)
        .fetch_optional(&mut **db.tx())
        .await;

        match result {
            Ok(Some(model)) => {
                db.commit().await.map_err(|e| {
                    SenseiError::Database(format!("Failed to commit password change: {e}"))
                })?;
                Ok(user_model_to_domain(model))
            }
            Ok(None) => Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            ))),
            Err(e) => Err(SenseiError::Database(format!(
                "Failed to change password: {e}"
            ))),
        }
    }

    async fn deactivate_user(&self, caller_tenant_id: EntityId, id: EntityId) -> Result<User> {
        // ONE tenant-scoped transaction (twenty-ninth audit Wave A): the
        // UPDATE and the principal-revision bump are inseparable — a
        // deactivation that did not move the authorization revision is
        // impossible. The revision bump invalidates authorization-derived
        // caches atomically.
        let mut db = TenantTx::begin(&self.pool, caller_tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin deactivation: {e}")))?;

        let model = sqlx::query_as::<_, UserModel>(&format!(
            "UPDATE users \
                 SET is_active = false, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 \
                 RETURNING {USER_COLUMNS}"
        ))
        .bind(id)
        .bind(caller_tenant_id)
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to deactivate user: {e}")))?;

        let Some(model) = model else {
            return Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            )));
        };
        crate::tps::authorization_revisions::bump_in_tx(
            db.tx(),
            caller_tenant_id,
            "principal_revision",
        )
        .await?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit deactivation: {e}")))?;
        Ok(user_model_to_domain(model))
    }

    async fn activate_user(&self, caller_tenant_id: EntityId, id: EntityId) -> Result<User> {
        // ONE tenant-scoped transaction: UPDATE + principal-revision bump
        // (the reactivated user's authorization caches must not outlive
        // the activation).
        let mut db = TenantTx::begin(&self.pool, caller_tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin activation: {e}")))?;

        let model = sqlx::query_as::<_, UserModel>(&format!(
            "UPDATE users \
                 SET is_active = true, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 \
                 RETURNING {USER_COLUMNS}"
        ))
        .bind(id)
        .bind(caller_tenant_id)
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to activate user: {e}")))?;

        let Some(model) = model else {
            return Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            )));
        };
        crate::tps::authorization_revisions::bump_in_tx(
            db.tx(),
            caller_tenant_id,
            "principal_revision",
        )
        .await?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit activation: {e}")))?;
        Ok(user_model_to_domain(model))
    }

    async fn update_user_roles(
        &self,
        caller_tenant_id: EntityId,
        id: EntityId,
        roles: Vec<String>,
    ) -> Result<User> {
        validate_roles_db(&self.pool, caller_tenant_id, &roles).await?;
        // ONE tenant-scoped transaction: the role UPDATE and the
        // principal-revision bump are inseparable — a role change is LIVE
        // for the very next request (the middleware reloads per request,
        // and the revision bump invalidates authorization-derived caches).
        let mut db = TenantTx::begin(&self.pool, caller_tenant_id)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin role update: {e}")))?;

        let model = sqlx::query_as::<_, UserModel>(&format!(
            "UPDATE users \
                 SET roles = $2, updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $3 \
                 RETURNING {USER_COLUMNS}"
        ))
        .bind(id)
        .bind(&roles)
        .bind(caller_tenant_id)
        .fetch_optional(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update user roles: {e}")))?;

        let Some(model) = model else {
            return Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            )));
        };
        crate::tps::authorization_revisions::bump_in_tx(
            db.tx(),
            caller_tenant_id,
            "principal_revision",
        )
        .await?;
        db.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit role update: {e}")))?;
        Ok(user_model_to_domain(model))
    }

    async fn is_email_verified(&self, id: EntityId) -> Result<bool> {
        // Pre-tenant identity channel (migration 175): the email-verified
        // state of the row is read through auth_user_by_id — a raw-pool
        // SELECT on `users` is fail-closed FORCE RLS and returns nothing
        // without an app.tenant_id context, and these verification flows
        // run before any tenant context exists.
        sqlx::query_scalar::<_, bool>(&format!("SELECT email_verified FROM {AUTH_USER_BY_ID}($1)"))
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read email_verified: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))
    }

    async fn set_email_verified(&self, id: EntityId, verified: bool) -> Result<()> {
        // Thirtieth-audit item 18 (Wave C RLS): the UPDATE runs inside a
        // TenantTx of the row's own tenant (resolved through the
        // pre-tenant identity channel) — a raw-pool UPDATE on the
        // fail-closed FORCE RLS `users` table affects zero rows.
        let row_tenant: Option<EntityId> =
            sqlx::query_scalar(&format!("SELECT tenant_id FROM {AUTH_USER_BY_ID}($1)"))
                .bind(id)
                .fetch_optional(&self.pool)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to resolve user tenant: {e}"))
                })?;
        let tenant_id = row_tenant
            .ok_or_else(|| SenseiError::NotFound(format!("User with id '{id}' not found")))?;
        let mut db = TenantTx::begin(&self.pool, tenant_id).await.map_err(|e| {
            SenseiError::Database(format!("Failed to begin email-verified update: {e}"))
        })?;
        let result =
            sqlx::query("UPDATE users SET email_verified = $2 WHERE id = $1 AND tenant_id = $3")
                .bind(id)
                .bind(verified)
                .bind(tenant_id)
                .execute(&mut **db.tx())
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to set email_verified: {e}")))?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!(
                "User with id '{id}' not found"
            )));
        }
        db.commit().await.map_err(|e| {
            SenseiError::Database(format!("Failed to commit email-verified update: {e}"))
        })?;
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

/// Validate role names against BOTH the static RBAC defaults and the
/// tenant-scoped `roles` table in PostgreSQL (the DB is the extension
/// point for custom roles).
async fn validate_roles_db(
    pool: &sqlx::PgPool,
    caller_tenant_id: uuid::Uuid,
    roles: &[String],
) -> Result<()> {
    // The `roles` table is fail-closed FORCE RLS: the custom-role lookup
    // must run inside a TenantTx of the caller's tenant (thirtieth-audit
    // item 18 — a raw read would silently see zero rows once migration
    // 175's NULLIF shape treats the pooled '' placeholder as no context).
    let mut db = TenantTx::begin(pool, caller_tenant_id)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin role validation: {e}")))?;
    let static_rbac = sensei_auth::rbac::RbacService::new();
    let mut unknown: Vec<&String> = Vec::new();
    for role in roles {
        if role == "platform_superadmin" {
            return Err(SenseiError::Validation(
                "'platform_superadmin' is a break-glass role and cannot be assigned".to_string(),
            ));
        }
        if static_rbac.role_exists(role) {
            continue;
        }
        let found: Option<String> =
            sqlx::query_scalar("SELECT name FROM roles WHERE tenant_id = $1 AND name = $2 LIMIT 1")
                .bind(caller_tenant_id)
                .bind(role)
                .fetch_optional(&mut **db.tx())
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to validate roles: {e}")))?;
        if found.is_none() {
            unknown.push(role);
        }
    }
    db.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit role validation: {e}")))?;
    if !unknown.is_empty() {
        return Err(SenseiError::Validation(format!(
            "Unknown role(s): {}",
            unknown
                .iter()
                .map(|r| r.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        )));
    }
    Ok(())
}

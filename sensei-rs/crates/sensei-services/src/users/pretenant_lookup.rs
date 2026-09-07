//! Pre-tenant identity lookups — the ONLY raw-pool SQL surface of the
//! users module (thirtieth-first audit item 8).
//!
//! # Narrow exception (migration 175)
//!
//! `users` is FORCE RLS with the universal fail-closed `tenant_isolation`
//! policy (migration 175): NO `app.tenant_id` context means NO rows, so a
//! raw-pool SELECT on `users` returns nothing under the production
//! `sensei_app` role. A small number of lookups legitimately run BEFORE
//! any tenant context can exist:
//!
//! * login's globally-unique email lookup (`auth_user_by_email(text)`),
//! * the id-keyed pre-tenant flows — verification, password reset,
//!   credential bumps — that hold only the global user id
//!   (`auth_user_by_id(uuid)`),
//! * tenant-wide admin listing and the pre-tenant notification-trigger
//!   worker's role-target resolution (`auth_users_all()`),
//!
//! Migration 175 therefore created exactly three SECURITY DEFINER
//! functions — `auth_user_by_email(text)`, `auth_user_by_id(uuid)`,
//! `auth_users_all()` — owned by the BYPASSRLS migration owner. Their
//! bodies run as that owner and read the FORCE-RLS `users` table across
//! tenants; the runtime `sensei_app` role is NOBYPASSRLS and holds
//! `EXECUTE` on exactly those three functions (never PUBLIC, migration
//! 175 REVOKEs them from PUBLIC and the canonical role script
//! `scripts/db/01-app-role.sh` re-asserts the app grant). This module is
//! the code-level home of that documented exception: every raw-pool
//! statement in the users module lives here, and every OTHER users query
//! runs inside a `sensei_core::db::TenantTx` (see `database.rs`).
//!
//! The functions below expose the definer channel over the pool; callers
//! (the users service) enforce their own tenant authorization AFTER a
//! fetch where the id/email is not already context-scoped.

use sensei_core::types::EntityId;
use sensei_db::models::UserModel;
use sqlx::PgPool;

const AUTH_USER_BY_EMAIL: &str = "auth_user_by_email";
const AUTH_USER_BY_ID: &str = "auth_user_by_id";
const AUTH_USERS_ALL: &str = "auth_users_all";

/// The `users` column list shared by the definer-channel readers (also
/// used by the users service's TenantTx writes, which RETURNING the same
/// canonical columns).
pub(super) const USER_COLUMNS: &str = "id, tenant_id, email, name, password_hash, roles, \
                            is_active, email_verified, credential_version, site_id, locale, \
                            last_login_at, created_at, updated_at";

/// The one row whose normalized email matches (login identity — the email
/// is the platform-unique cross-tenant login key, so this lookup
/// legitimately crosses tenants through `auth_user_by_email`).
pub async fn user_by_email(pool: &PgPool, email: &str) -> Result<Option<UserModel>, sqlx::Error> {
    sqlx::query_as::<_, UserModel>(&format!("SELECT * FROM {AUTH_USER_BY_EMAIL}($1)"))
        .bind(email)
        .fetch_optional(pool)
        .await
}

/// The one row with that global primary key. Callers enforce their own
/// tenant authorization after the fetch.
pub async fn user_by_id(pool: &PgPool, id: EntityId) -> Result<Option<UserModel>, sqlx::Error> {
    sqlx::query_as::<_, UserModel>(&format!("SELECT * FROM {AUTH_USER_BY_ID}($1)"))
        .bind(id)
        .fetch_optional(pool)
        .await
}

/// Tenant-wide admin listing via the definer channel: the service
/// semantics are "all users; the caller scopes" (the route layer filters
/// by the caller's tenant, and the pre-tenant notification-trigger worker
/// resolves role targets across the deployment).
pub async fn list_all(pool: &PgPool) -> Result<Vec<UserModel>, sqlx::Error> {
    sqlx::query_as::<_, UserModel>(&format!(
        "SELECT {USER_COLUMNS} FROM {AUTH_USERS_ALL}() ORDER BY created_at DESC"
    ))
    .fetch_all(pool)
    .await
}

/// The paginated tenant-wide listing: count and page read the SAME
/// definer snapshot (`auth_users_all()`), with optional exact-array role
/// membership and active-state filters.
pub async fn count_and_page(
    pool: &PgPool,
    role: Option<&str>,
    is_active: Option<bool>,
    per_page: i64,
    offset: i64,
) -> Result<(i64, Vec<UserModel>), sqlx::Error> {
    // Exact array membership: `$n = ANY(roles)` — no false positives from
    // substring matching ('admin' must not match 'admin2').
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
    let total: i64 = count_query.fetch_one(pool).await?;

    let mut data_query = sqlx::query_as::<_, UserModel>(&data_sql);
    if let Some(r) = role {
        data_query = data_query.bind(r);
    }
    if let Some(act) = is_active {
        data_query = data_query.bind(act);
    }
    let models: Vec<UserModel> = data_query
        .bind(per_page)
        .bind(offset)
        .fetch_all(pool)
        .await?;

    Ok((total, models))
}

/// The row's own tenant, resolved through the pre-tenant identity channel
/// (`auth_user_by_id`) when the caller holds only the global user id and
/// the follow-up write must run inside a TenantTx of that tenant.
pub async fn tenant_id_of(pool: &PgPool, id: EntityId) -> Result<Option<EntityId>, sqlx::Error> {
    sqlx::query_scalar(&format!("SELECT tenant_id FROM {AUTH_USER_BY_ID}($1)"))
        .bind(id)
        .fetch_optional(pool)
        .await
}

/// The email-verified state of the row, read through the pre-tenant
/// identity channel — these verification flows run before any tenant
/// context exists.
pub async fn email_verified_of(pool: &PgPool, id: EntityId) -> Result<Option<bool>, sqlx::Error> {
    sqlx::query_scalar::<_, bool>(&format!("SELECT email_verified FROM {AUTH_USER_BY_ID}($1)"))
        .bind(id)
        .fetch_optional(pool)
        .await
}

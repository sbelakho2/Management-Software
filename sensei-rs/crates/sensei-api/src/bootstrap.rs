//! Bootstrap seeding for the Sensei API server (thirtieth-first audit
//! item 15 — bootstrap serialization + extraction).
//!
//! Every multi-replica bootstrap step — ensuring the bootstrap tenant and
//! seeding the required admin/CEO accounts — is extracted from `main.rs`
//! into this module so the pieces are testable in isolation: the
//! in-memory (no-pool) path is covered by plain unit tests, and the
//! cross-replica serialization contract is proven by DB-gated tests
//! against a scratch PostgreSQL database.
//!
//! # Cross-replica coordination
//!
//! [`seed_bootstrap_users`] runs the whole bootstrap section inside ONE
//! open transaction on a dedicated pool connection and takes
//! `pg_advisory_xact_lock(737012345)` on that transaction BEFORE any seed
//! runs: a second replica blocks at the lock until the first replica
//! commits (or rolls back), so bootstrap is a one-time operation and the
//! seeds never race. The seed SQL itself may run on other pooled
//! connections — the open transaction is the cross-replica coordination
//! lock, not the write channel.
//!
//! # Fail-fast contract
//!
//! Required bootstrap failures are NEVER logged-and-swallowed: a failed
//! tenant ensure, a failed required-account (admin/CEO) creation, or a
//! failed lock/commit returns a [`SenseiError`], and the caller
//! (`main.rs`) aborts startup with a clear message.

use sensei_core::domain::entities::{Tenant, User};
use sensei_core::error::SenseiError;
use sensei_core::types::{now, TenantId};

use crate::state::AppState;

/// Role set granted to the seeded bootstrap identities (admin and CEO):
/// functional manager roles + platform administration.
///
/// The legacy `"ceo"` role is NOT part of the authorization model, so it
/// is never seeded.
const BOOTSTRAP_ROLES: &[&str] = &[
    "user",
    "tenant_admin",
    "platform_admin",
    "finance_manager",
    "hr_manager",
    "purchasing_manager",
    "inventory_manager",
    "sales_manager",
    "quality_manager",
    "production_manager",
];

/// The bootstrap tenant for seeded admin/CEO accounts.
///
/// A fixed, deterministic id (NOT `Uuid::nil()`): the tenants service
/// treats nil ids as "generate one" (`create_tenant` remaps nil to a fresh
/// random uuid), so a nil bootstrap tenant would be created under a random
/// id while the seeded `users.tenant_id` still referenced nil — violating
/// `users_tenant_id_fkey` on first boot. Every replica resolves the same
/// fixed id, keeping seeding idempotent under the advisory lock.
fn bootstrap_tenant_id() -> TenantId {
    uuid::Uuid::from_u128(1)
}

/// Ensure the bootstrap tenant exists (the `users` table has an FK on
/// `tenants(id)`), creating it when missing.
///
/// A missing tenant is created with the fixed [`bootstrap_tenant_id`];
/// any lookup or creation failure PROPAGATES so the caller can abort
/// startup (bootstrap failures are never logged-and-swallowed).
async fn ensure_bootstrap_tenant(state: &AppState) -> Result<(), SenseiError> {
    let tenant_id = bootstrap_tenant_id();
    match state.tenants_service.get_tenant(tenant_id).await {
        Ok(_) => Ok(()),
        Err(SenseiError::NotFound(_)) => {
            let timestamp = now();
            let tenant = Tenant {
                id: tenant_id,
                name: "Sensei".to_string(),
                slug: "sensei".to_string(),
                is_active: true,
                features: Vec::new(),
                created_at: timestamp,
                updated_at: timestamp,
            };
            match state.tenants_service.create_tenant(tenant).await {
                Ok(_) => Ok(()),
                Err(e) => {
                    tracing::error!(
                        error = %e,
                        tenant_id = %tenant_id,
                        "Failed to create the bootstrap tenant"
                    );
                    Err(e)
                }
            }
        }
        Err(e) => {
            tracing::error!(
                error = %e,
                tenant_id = %tenant_id,
                "Failed to look up the bootstrap tenant"
            );
            Err(e)
        }
    }
}

/// Seed a user through the users service if it does not exist yet.
///
/// Idempotent: `find_by_email` → create only when missing. A failure to
/// seed a *required* account returns the error so the caller aborts
/// startup; the error is returned in every case (nothing is swallowed
/// here — `required_in_prod` only distinguishes fatal required accounts
/// from tolerated optional ones for the caller).
async fn seed_user(
    state: &AppState,
    email: &str,
    password: &str,
    name: &str,
    roles: &[&str],
    required_in_prod: bool,
) -> Result<User, SenseiError> {
    match state.users_service.find_by_email(email).await {
        Ok(existing) => {
            tracing::info!(email, "Seed account already exists");
            Ok(existing)
        }
        Err(SenseiError::NotFound(_)) => {
            let password_hash = sensei_auth::password::hash_password(password).map_err(|e| {
                SenseiError::Internal(format!("Failed to hash seed password for {email}: {e}"))
            })?;
            let mut user = User::new(
                bootstrap_tenant_id(),
                email.to_string(),
                name.to_string(),
                password_hash,
            );
            user.roles = roles.iter().map(|r| r.to_string()).collect();

            match state.users_service.create_user(user).await {
                Ok(created) => {
                    tracing::info!(email, roles = ?roles, "Seeded user");
                    Ok(created)
                }
                Err(e) => {
                    if required_in_prod {
                        tracing::error!(email, error = %e, "Failed to seed a required account");
                    } else {
                        tracing::warn!(email, error = %e, "Failed to seed account");
                    }
                    Err(e)
                }
            }
        }
        Err(e) => {
            if required_in_prod {
                tracing::error!(
                    email,
                    error = %e,
                    "Failed to look up a required seed account"
                );
            } else {
                tracing::warn!(email, error = %e, "Failed to look up seed account");
            }
            Err(e)
        }
    }
}

/// Seed the required admin and CEO bootstrap accounts.
///
/// Both identities are REQUIRED bootstrap steps: a failed admin or CEO
/// creation propagates and aborts startup (thirtieth-first audit item 15
/// — required bootstrap failures are never logged-and-swallowed). In
/// production both passwords must be explicitly set; in development a
/// random password is generated and printed (first boot only).
async fn seed_required_users(state: &AppState) -> Result<(), SenseiError> {
    // ── Admin seed account ─────────────────────────────────────────
    let admin_email = std::env::var("SENSEI_ADMIN_EMAIL")
        .unwrap_or_else(|_| "admin@starzforge.local".to_string());
    let admin_password = match std::env::var("SENSEI_ADMIN_PASSWORD") {
        Ok(v) if !v.is_empty() => v,
        _ => {
            if state.config.environment.is_prod() {
                return Err(SenseiError::MissingEnvVar(
                    "SENSEI_ADMIN_PASSWORD".to_string(),
                ));
            }
            let generated = format!("dev-{}", uuid::Uuid::new_v4());
            println!("ADMIN DEV PASSWORD (first boot only): {generated}");
            generated
        }
    };
    let admin_name =
        std::env::var("SENSEI_ADMIN_NAME").unwrap_or_else(|_| "Admin User".to_string());

    seed_user(
        state,
        &admin_email,
        &admin_password,
        &admin_name,
        BOOTSTRAP_ROLES,
        true,
    )
    .await?;

    // ── CEO seed account ───────────────────────────────────────────
    // The CEO is the break-glass operational identity: functional manager
    // roles + platform administration (BOOTSTRAP_ROLES above; the legacy
    // "ceo" role is NOT defined by the authorization model and is never
    // seeded).
    let ceo_email =
        std::env::var("SENSEI_CEO_EMAIL").unwrap_or_else(|_| "ceo@starz.com".to_string());
    let ceo_password = match std::env::var("SENSEI_CEO_PASSWORD") {
        Ok(v) if !v.is_empty() => v,
        _ => {
            if state.config.environment.is_prod() {
                return Err(SenseiError::MissingEnvVar(
                    "SENSEI_CEO_PASSWORD".to_string(),
                ));
            }
            let generated = format!("dev-{}", uuid::Uuid::new_v4());
            println!("CEO DEV PASSWORD (first boot only): {generated}");
            generated
        }
    };

    seed_user(
        state,
        &ceo_email,
        &ceo_password,
        "CEO",
        BOOTSTRAP_ROLES,
        true,
    )
    .await?;

    Ok(())
}

/// Seed the bootstrap tenant and the required admin/CEO accounts under a
/// cross-replica advisory lock.
///
/// In database mode the WHOLE bootstrap section runs inside one open
/// transaction (`pool.begin()`), and `pg_advisory_xact_lock` is taken on
/// that transaction BEFORE any seed: a second replica cannot enter the
/// bootstrap section until the first commits or rolls back, so seeding is
/// serialized and idempotent (a loser observes the winner's rows and
/// skips creation). The seed SQL may run on other pooled connections —
/// the open transaction is the cross-replica coordination lock, not the
/// write channel. The transaction is committed after the last seed; any
/// failure rolls it back (releasing the lock) and propagates.
///
/// When `state.db_pool` is `None` (development/in-memory mode) no
/// transaction is needed and the in-memory services seed directly.
///
/// # Errors
///
/// Propagates the FIRST failure — lock acquisition, tenant ensure,
/// required account creation, or commit — so the caller aborts startup
/// with a clear message instead of logging-and-continuing.
pub async fn seed_bootstrap_users(state: &AppState) -> Result<(), SenseiError> {
    let mut bootstrap_guard = match &state.db_pool {
        Some(pool) => {
            let mut tx = pool
                .begin()
                .await
                .map_err(|e| SenseiError::Database(e.to_string()))?;
            sqlx::query("SELECT pg_advisory_xact_lock($1)")
                .bind(737012345_i64)
                .execute(&mut *tx)
                .await
                .map_err(|e| SenseiError::Database(e.to_string()))?;
            Some(tx)
        }
        None => None,
    };
    ensure_bootstrap_tenant(state).await?;
    seed_required_users(state).await?;
    if let Some(tx) = bootstrap_guard.take() {
        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(e.to_string()))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_services::users::InMemoryUsersService;
    use sqlx::postgres::PgPoolOptions;
    use sqlx::PgPool;

    /// The advisory-lock key `seed_bootstrap_users` takes on its
    /// bootstrap transaction (the DB-gated tests must hold/release the
    /// same key to prove serialization).
    const BOOTSTRAP_LOCK_KEY: i64 = 737012345;

    /// DB-gated tests each DROP+CREATE the shared scratch schema — running
    /// them concurrently races the schema locks. A global lock serializes
    /// the suite: every DB test acquires it before touching the database
    /// (same convention as the sensei-db db_contract suite).
    static DB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

    /// Serializes tests that mutate the process environment (pinned
    /// SENSEI_* variables below), which is process-global.
    static ENV_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

    /// Deterministic seed identities used by every test that runs the
    /// seeds (pinned so assertions never depend on ambient environment).
    const ADMIN_EMAIL: &str = "bootstrap-test-admin@example.com";
    const ADMIN_NAME: &str = "Bootstrap Test Admin";
    const CEO_EMAIL: &str = "bootstrap-test-ceo@example.com";
    const SEED_PASSWORD: &str = "bootstrap-test-password";

    /// Pin the process environment to a deterministic development
    /// configuration plus the test seed identities. Every caller must hold
    /// [`ENV_LOCK`] and restore the previous environment afterwards.
    fn pin_environment() {
        std::env::set_var("SENSEI_ENV", "development");
        std::env::set_var("JWT_SECRET", "bootstrap-test-secret");
        std::env::remove_var("DATABASE_URL");
        std::env::remove_var("NATS_URL");
        std::env::set_var("SENSEI_ADMIN_EMAIL", ADMIN_EMAIL);
        std::env::set_var("SENSEI_ADMIN_NAME", ADMIN_NAME);
        std::env::set_var("SENSEI_ADMIN_PASSWORD", SEED_PASSWORD);
        std::env::set_var("SENSEI_CEO_EMAIL", CEO_EMAIL);
        std::env::set_var("SENSEI_CEO_PASSWORD", SEED_PASSWORD);
    }

    /// Restore the pinned environment variables to their pre-test values.
    fn unpin_environment(previous: &[(&'static str, Option<String>)]) {
        for (var, value) in previous {
            match value {
                Some(v) => std::env::set_var(var, v),
                None => std::env::remove_var(var),
            }
        }
    }

    /// Snapshot the environment variables this module pins.
    fn environment_snapshot() -> Vec<(&'static str, Option<String>)> {
        [
            "SENSEI_ENV",
            "JWT_SECRET",
            "DATABASE_URL",
            "NATS_URL",
            "SENSEI_ADMIN_EMAIL",
            "SENSEI_ADMIN_NAME",
            "SENSEI_ADMIN_PASSWORD",
            "SENSEI_CEO_EMAIL",
            "SENSEI_CEO_PASSWORD",
        ]
        .into_iter()
        .map(|var| (var, std::env::var(var).ok()))
        .collect()
    }

    /// Deterministic development configuration (caller holds ENV_LOCK and
    /// has pinned the environment).
    fn test_config() -> sensei_core::config::AppConfig {
        sensei_core::config::AppConfig::from_env().expect("pinned test config must build")
    }

    /// Build an [`AppState`] over the DB-backed services for the given
    /// pool (caller holds ENV_LOCK).
    fn state_with_pool(pool: PgPool) -> AppState {
        let users: std::sync::Arc<dyn sensei_services::users::UsersService> =
            std::sync::Arc::new(InMemoryUsersService::new());
        AppState::new(test_config(), users).with_db_pool(std::sync::Arc::new(pool))
    }

    /// Build an in-memory [`AppState`] with NO database pool (caller holds
    /// ENV_LOCK).
    fn in_memory_state() -> AppState {
        let users: std::sync::Arc<dyn sensei_services::users::UsersService> =
            std::sync::Arc::new(InMemoryUsersService::new());
        AppState::new(test_config(), users)
    }

    /// Connect to the disposable scratch database named by
    /// `DATABASE_URL_TEST`, DROP every table, and re-apply the FULL
    /// migration chain (same reset convention as the repo's DB-contract
    /// gates). Returns `None` — after printing SKIP — when the env var is
    /// absent or the database is unreachable, so local suites stay green.
    async fn scratch_pool() -> Option<PgPool> {
        let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
            eprintln!("SKIP: DATABASE_URL_TEST not set — bootstrap DB gate runs in CI");
            return None;
        };
        let pool = match PgPoolOptions::new().max_connections(8).connect(&url).await {
            Ok(pool) => pool,
            Err(e) => {
                eprintln!("SKIP: cannot reach DATABASE_URL_TEST ({e})");
                return None;
            }
        };
        sqlx::query(
            r#"DO $$ DECLARE r RECORD; BEGIN
                 FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                     EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
                 END LOOP;
             END $$"#,
        )
        .execute(&pool)
        .await
        .expect("drop all tables on the scratch database");
        sensei_db::migrations::run_migrations(&pool)
            .await
            .expect("the ENTIRE migration chain must apply to the scratch database");
        Some(pool)
    }

    /// Assert the bootstrap invariants directly in the database: exactly
    /// ONE tenant (the fixed bootstrap tenant) and exactly ONE row per
    /// required account, each bound to the bootstrap tenant.
    async fn assert_single_bootstrap_seed(pool: &PgPool) {
        let tenants_total: i64 = sqlx::query_scalar("SELECT count(*) FROM tenants")
            .fetch_one(pool)
            .await
            .expect("tenant count query");
        assert_eq!(
            tenants_total, 1,
            "exactly one tenant row must exist after bootstrap"
        );
        let bootstrap_rows: i64 = sqlx::query_scalar("SELECT count(*) FROM tenants WHERE id = $1")
            .bind(bootstrap_tenant_id())
            .fetch_one(pool)
            .await
            .expect("bootstrap tenant count query");
        assert_eq!(
            bootstrap_rows, 1,
            "the single tenant must be the fixed bootstrap tenant"
        );
        for email in [ADMIN_EMAIL, CEO_EMAIL] {
            let user_rows: i64 = sqlx::query_scalar("SELECT count(*) FROM users WHERE email = $1")
                .bind(email)
                .fetch_one(pool)
                .await
                .expect("user count query");
            assert_eq!(
                user_rows, 1,
                "exactly one {email} row must exist after bootstrap (no duplicates)"
            );
            let tenant_bound: i64 = sqlx::query_scalar(
                "SELECT count(*) FROM users WHERE email = $1 AND tenant_id = $2",
            )
            .bind(email)
            .bind(bootstrap_tenant_id())
            .fetch_one(pool)
            .await
            .expect("user tenant binding query");
            assert_eq!(
                tenant_bound, 1,
                "{email} must belong to the bootstrap tenant"
            );
        }
    }

    // ── Pure unit tests (no database needed) ─────────────────────────

    #[test]
    fn bootstrap_tenant_id_is_fixed_deterministic_and_not_nil() {
        let id = bootstrap_tenant_id();
        assert_eq!(
            id,
            uuid::Uuid::from_u128(1),
            "the bootstrap tenant id is the fixed constant"
        );
        assert!(
            !id.is_nil(),
            "nil would be remapped to a random id by the tenants service"
        );
        assert_eq!(
            bootstrap_tenant_id(),
            id,
            "every replica resolves the same id"
        );
    }

    /// Development mode (no pool): the in-memory services seed directly —
    /// no transaction is needed — and repeated seeding is idempotent with
    /// exactly one tenant and one row per account.
    #[tokio::test]
    async fn in_memory_bootstrap_is_idempotent_without_a_transaction() {
        let _env_guard = ENV_LOCK.lock().await;
        let snapshot = environment_snapshot();
        pin_environment();
        let state = in_memory_state();
        assert!(
            state.db_pool.is_none(),
            "this test exercises the dev/in-memory (no-pool) bootstrap path"
        );

        let first = seed_bootstrap_users(&state).await;
        assert!(
            first.is_ok(),
            "first in-memory seed must succeed: {first:?}"
        );
        let second = seed_bootstrap_users(&state).await;
        assert!(
            second.is_ok(),
            "second in-memory seed must be idempotent: {second:?}"
        );

        let tenants = state
            .tenants_service
            .list_tenants()
            .await
            .expect("list tenants");
        assert_eq!(
            tenants.len(),
            1,
            "seeding twice must leave exactly one tenant"
        );
        assert_eq!(tenants[0].id, bootstrap_tenant_id());

        let users = state.users_service.list_users().await.expect("list users");
        assert_eq!(users.len(), 2, "admin + CEO only");
        let admin = users
            .iter()
            .find(|u| u.email == ADMIN_EMAIL)
            .expect("admin seeded");
        assert_eq!(admin.tenant_id, bootstrap_tenant_id());
        assert!(admin.roles.iter().any(|r| r == "platform_admin"));
        let ceo = users
            .iter()
            .find(|u| u.email == CEO_EMAIL)
            .expect("CEO seeded");
        assert_eq!(ceo.tenant_id, bootstrap_tenant_id());
        assert!(ceo.roles.iter().any(|r| r == "platform_admin"));
        unpin_environment(&snapshot);
    }

    // ── DB-gated tests (DATABASE_URL_TEST, serial on a scratch DB) ──

    /// The advisory transaction lock must serialize the whole bootstrap
    /// section: a second `seed_bootstrap_users` WAITS while the lock is
    /// held, then succeeds without duplicating tenant/admin/CEO — and two
    /// concurrent full invocations on an already-seeded database both
    /// return Ok with the rows still unique.
    #[tokio::test]
    async fn advisory_xact_lock_serializes_concurrent_bootstraps_without_duplicates() {
        let _env_guard = ENV_LOCK.lock().await;
        let _db_guard = DB_LOCK.lock().await;
        let snapshot = environment_snapshot();
        pin_environment();
        let Some(pool) = scratch_pool().await else {
            unpin_environment(&snapshot);
            return;
        };
        let state = state_with_pool(pool.clone());

        // A blocker transaction takes the SAME advisory lock the bootstrap
        // takes first: while it is open, a concurrent bootstrap must block.
        let mut blocker = pool.begin().await.expect("blocker transaction must begin");
        sqlx::query("SELECT pg_advisory_xact_lock($1)")
            .bind(BOOTSTRAP_LOCK_KEY)
            .execute(&mut *blocker)
            .await
            .expect("blocker must acquire the bootstrap advisory lock");

        let second_replica = tokio::time::timeout(
            std::time::Duration::from_millis(1500),
            seed_bootstrap_users(&state),
        )
        .await;
        assert!(
            second_replica.is_err(),
            "a concurrent bootstrap must WAIT while the first replica's \
             bootstrap transaction holds the advisory lock"
        );

        // Release the lock: the waiting bootstrap now runs to completion.
        blocker
            .rollback()
            .await
            .expect("blocker rollback releases the lock");
        tokio::time::timeout(
            std::time::Duration::from_secs(60),
            seed_bootstrap_users(&state),
        )
        .await
        .expect("bootstrap must complete once the lock is released")
        .expect("seed must succeed once the lock holder rolled back");
        assert_single_bootstrap_seed(&pool).await;

        // Two CONCURRENT full bootstrap invocations on the seeded database:
        // the advisory lock serializes them — both succeed and no
        // tenant/admin/CEO row is duplicated.
        let (a, b) = tokio::join!(seed_bootstrap_users(&state), seed_bootstrap_users(&state));
        a.expect("concurrent bootstrap (a) must succeed");
        b.expect("concurrent bootstrap (b) must succeed");
        assert_single_bootstrap_seed(&pool).await;
        unpin_environment(&snapshot);
    }

    /// Two sequential bootstrap invocations on a fresh database are
    /// idempotent: the second finds the seeded rows and creates nothing.
    #[tokio::test]
    async fn sequential_bootstraps_are_idempotent() {
        let _env_guard = ENV_LOCK.lock().await;
        let _db_guard = DB_LOCK.lock().await;
        let snapshot = environment_snapshot();
        pin_environment();
        let Some(pool) = scratch_pool().await else {
            unpin_environment(&snapshot);
            return;
        };
        let state = state_with_pool(pool.clone());

        seed_bootstrap_users(&state)
            .await
            .expect("first bootstrap must succeed");
        seed_bootstrap_users(&state)
            .await
            .expect("second bootstrap must be idempotent");
        assert_single_bootstrap_seed(&pool).await;
        unpin_environment(&snapshot);
    }

    /// Required bootstrap failures propagate as errors instead of being
    /// logged-and-swallowed: with the tenants table gone, the tenant
    /// ensure fails and `seed_bootstrap_users` returns the error (the
    /// caller aborts startup) — and the bootstrap transaction still
    /// releases the advisory lock.
    #[tokio::test]
    async fn required_bootstrap_failure_propagates_to_the_caller() {
        let _env_guard = ENV_LOCK.lock().await;
        let _db_guard = DB_LOCK.lock().await;
        let snapshot = environment_snapshot();
        pin_environment();
        let Some(pool) = scratch_pool().await else {
            unpin_environment(&snapshot);
            return;
        };
        let state = state_with_pool(pool.clone());

        sqlx::query("DROP TABLE tenants CASCADE")
            .execute(&pool)
            .await
            .expect("drop tenants to force a bootstrap failure");

        let err = seed_bootstrap_users(&state)
            .await
            .expect_err("a failed tenant ensure must propagate as Err");
        assert!(
            matches!(err, SenseiError::Database(_)),
            "expected a Database error, got {err:?}"
        );

        // The failed bootstrap rolled its transaction back, so the
        // advisory lock is free for the next holder.
        let mut probe = pool.begin().await.expect("probe tx");
        sqlx::query("SELECT pg_advisory_xact_lock($1)")
            .bind(BOOTSTRAP_LOCK_KEY)
            .execute(&mut *probe)
            .await
            .expect("the advisory lock must be released after the failed bootstrap");
        probe.rollback().await.expect("probe rollback");
        unpin_environment(&snapshot);
    }
}

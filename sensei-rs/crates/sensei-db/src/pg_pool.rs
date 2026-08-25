//! PostgreSQL connection pool management.
//!
//! Provides a singleton connection pool using [`sqlx::PgPool`] with
//! configurable connection limits and timeouts.

use sensei_core::config::DatabaseConfig;
use sensei_core::error::{Result, SenseiError};
use sqlx::postgres::{PgConnectOptions, PgPoolOptions};
use sqlx::PgPool;
use std::sync::Arc;
use tokio::sync::OnceCell;
use tracing::{info, warn};

/// Global database pool instance.
static POOL: OnceCell<Arc<PgPool>> = OnceCell::const_new();

/// Initialize the global database connection pool.
///
/// Should be called once at application startup. Safe to call concurrently:
/// the second caller wins the race, logs an informational message, and
/// returns the existing pool (its own freshly built pool is dropped).
///
/// # Arguments
/// * `config` - Database configuration including URL and pool sizing.
///
/// # Errors
/// Returns [`SenseiError::DatabaseConnection`] if the pool cannot be created.
pub async fn init_pool(config: &DatabaseConfig) -> Result<Arc<PgPool>> {
    if let Some(pool) = POOL.get() {
        return Ok(Arc::clone(pool));
    }

    info!(
        max_connections = config.max_connections,
        "Initializing database connection pool"
    );

    let connect_options: PgConnectOptions = config
        .url
        .parse()
        .map_err(|e| SenseiError::Configuration(format!("Invalid DATABASE_URL: {e}")))?;

    let pool = PgPoolOptions::new()
        .max_connections(config.max_connections)
        .acquire_timeout(std::time::Duration::from_secs(
            config.connection_timeout_secs,
        ))
        .connect_with(connect_options)
        .await
        .map_err(|e| {
            SenseiError::DatabaseConnection(format!("Failed to connect to PostgreSQL: {e}"))
        })?;

    info!("Database connection pool established");
    let pool = Arc::new(pool);

    match POOL.set(Arc::clone(&pool)) {
        Ok(()) => Ok(pool),
        Err(existing) => {
            // Another task initialized the pool concurrently; reuse it.
            info!("Database pool was initialized concurrently; reusing existing pool");
            let existing = match existing {
                tokio::sync::SetError::AlreadyInitializedError(pool)
                | tokio::sync::SetError::InitializingError(pool) => pool,
            };
            Ok(existing)
        }
    }
}

/// Get a reference to the global database pool.
///
/// Returns `None` if the pool has not been initialized.
pub fn get_pool() -> Option<Arc<PgPool>> {
    POOL.get().map(Arc::clone)
}

/// Check if the database pool is initialized and the connection is alive.
pub async fn health_check() -> Result<bool> {
    let pool = get_pool()
        .ok_or_else(|| SenseiError::DatabaseConnection("Pool not initialized".to_string()))?;

    sqlx::query("SELECT 1")
        .execute(&*pool)
        .await
        .map_err(|e| SenseiError::DatabaseConnection(e.to_string()))?;

    Ok(true)
}

/// Execute a function within a database transaction.
///
/// If the function returns an error, the transaction is rolled back.
pub async fn with_transaction<T, F>(f: F) -> Result<T>
where
    F: for<'a> FnOnce(&mut sqlx::Transaction<'a, sqlx::Postgres>) -> Result<T> + Send,
    T: Send,
{
    let pool = get_pool()
        .ok_or_else(|| SenseiError::DatabaseConnection("Pool not initialized".to_string()))?;

    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;

    match f(&mut tx) {
        Ok(result) => {
            tx.commit()
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to commit transaction: {e}")))?;
            Ok(result)
        }
        Err(e) => {
            tx.rollback()
                .await
                .map_err(|rollback_err| {
                    warn!("Failed to rollback transaction: {rollback_err}");
                })
                .ok();
            Err(e)
        }
    }
}

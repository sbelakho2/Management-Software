//! Database migration management.
//!
//! Runs SQL migrations from the `migrations/` directory using sqlx's
//! built-in migration runner. Migrations are embedded into the binary
//! at compile time for reliable deployment.

use sensei_core::error::{Result, SenseiError};
use sqlx::migrate::Migrator;
use sqlx::PgPool;
use std::path::Path;
use tokio::sync::OnceCell;
use tracing::{info, warn};

/// The embedded migrator pointing to the `migrations/` directory.
///
/// This embeds all `.sql` migration files into the binary at compile time,
/// ensuring that the correct migrations are always available at runtime.
///
/// Note: In sqlx 0.8, `Migrator::new` is async, so we initialize lazily at first use.
static MIGRATOR: OnceCell<Migrator> = OnceCell::const_new();

/// Initialize the migrator (must be called before running migrations).
async fn get_migrator() -> Result<&'static Migrator> {
    MIGRATOR
        .get_or_try_init(|| async {
            Migrator::new(Path::new(env!("CARGO_MANIFEST_DIR")).join("migrations"))
                .await
                .map_err(|e| SenseiError::Internal(format!("Failed to load migrations: {e}")))
        })
        .await
        .map_err(|e| SenseiError::Internal(format!("Failed to initialize migrator: {e}")))
}

/// Run all pending migrations on the given database pool.
///
/// # Arguments
/// * `pool` - A connected [`PgPool`] to run migrations against.
///
/// # Errors
/// Returns [`SenseiError::Database`] if migration execution fails.
pub async fn run_migrations(pool: &PgPool) -> Result<()> {
    info!("Running database migrations...");

    let migrator = get_migrator().await?;
    match migrator.run(pool).await {
        Ok(()) => {
            info!("Database migrations applied successfully");
            Ok(())
        }
        Err(e) => {
            warn!("Migration failed: {e}");
            Err(SenseiError::Database(format!("Migration failed: {e}")))
        }
    }
}

/// Get the total number of available migrations.
pub fn total_migrations() -> usize {
    // Synchronous fallback if migrator not yet initialized
    MIGRATOR.get().map(|m| m.migrations.len()).unwrap_or(0)
}

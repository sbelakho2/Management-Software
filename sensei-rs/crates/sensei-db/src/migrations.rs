//! Database migration management.
//!
//! Runs SQL migrations from the `migrations/` directory using sqlx's
//! built-in migration runner.
//!
//! # Loading
//!
//! Migrations are **not** embedded at compile time: they are loaded from
//! the filesystem at runtime via [`sqlx::migrate::Migrator::new`], pointing
//! at the `migrations/` directory next to this crate's manifest. The
//! `_sqlx_migrations` table in the database tracks which versions have
//! been applied.
//!
//! # Versioning
//!
//! Versions 013–015 were removed during development and the remaining
//! files were renumbered; because this project has never been deployed to
//! a real environment, no environment has ever recorded those versions in
//! `_sqlx_migrations`, so the gap is safe. Do not create placeholder
//! migrations to fill the gap.

use sensei_core::error::{Result, SenseiError};
use sqlx::migrate::Migrator;
use sqlx::PgPool;
use std::path::Path;
use tokio::sync::OnceCell;
use tracing::{info, warn};

/// The migrator pointing to the `migrations/` directory.
///
/// Loaded lazily from the filesystem at first use; `Migrator::new` is
/// async in sqlx 0.8, so the migrator is initialized once via
/// [`OnceCell`] rather than a compile-time `embed_migrations!`.
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
///
/// Returns `0` until [`run_migrations`] has initialized the migrator
/// (the count is only known after the filesystem scan), so this should
/// only be used for diagnostics after startup.
pub fn total_migrations() -> usize {
    MIGRATOR.get().map(|m| m.migrations.len()).unwrap_or(0)
}

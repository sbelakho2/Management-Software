//! Health check endpoints.
//!
//! Provides endpoints for readiness and liveness probes used by
//! container orchestration systems (Kubernetes, Docker, etc.):
//!
//! - `GET /livez` and `GET /health/live` — process liveness, always 200.
//! - `GET /readyz` and `GET /health/ready` — readiness; 200 when every
//!   required dependency is healthy, 503 otherwise.
//! - `GET /health/detailed` — detailed subsystem status (diagnostics).

use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use sqlx::PgPool;
use std::time::Instant;
use uuid::Uuid;

use crate::state::AppState;
use sensei_services::storage::FileStorageService;

/// Global start time for uptime tracking.
static START_TIME: once_cell::sync::Lazy<Instant> = once_cell::sync::Lazy::new(Instant::now);

/// Basic liveness probe — returns 200 if the server is alive.
pub async fn liveness() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "alive"
    }))
}

/// Readiness probe — checks if the service is ready to handle requests.
///
/// Returns `200 {"status":"ready","checks":{...}}` when every required
/// dependency is healthy and `503 {"status":"not_ready","checks":{...}}`
/// when any configured dependency fails. Dependencies that are
/// intentionally absent (e.g. no database pool in dev mode) report
/// `"not_configured"` and do **not** fail readiness.
pub async fn readiness(State(state): State<AppState>) -> Response {
    let (ready, checks) = run_readiness_checks(&state).await;

    let body = serde_json::json!({
        "status": if ready { "ready" } else { "not_ready" },
        "version": env!("CARGO_PKG_VERSION"),
        "uptime_seconds": START_TIME.elapsed().as_secs(),
        "checks": checks,
    });

    let status_code = if ready {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };
    (status_code, Json(body)).into_response()
}

/// Run every readiness check.
///
/// Returns `(ready, checks)` where `checks` maps a dependency name to its
/// status string. `ready` is `false` if any **configured** dependency is
/// unhealthy.
pub async fn run_readiness_checks(
    state: &AppState,
) -> (bool, serde_json::Map<String, serde_json::Value>) {
    let mut ready = true;
    let mut checks = serde_json::Map::new();

    let (db_status, db_ok) = check_database(state.db_pool.as_deref()).await;
    checks.insert("database".to_string(), serde_json::json!(db_status));
    if !db_ok {
        ready = false;
    }

    let (bus_status, bus_ok) = check_event_bus(&*state.event_bus);
    checks.insert("event_bus".to_string(), serde_json::json!(bus_status));
    if !bus_ok {
        ready = false;
    }

    let (storage_status, storage_ok) = check_storage(&*state.storage_service, Uuid::nil()).await;
    checks.insert("storage".to_string(), serde_json::json!(storage_status));
    if !storage_ok {
        ready = false;
    }

    (ready, checks)
}

/// Check database connectivity.
///
/// * `None` (no pool configured, dev mode) → `("not_configured", true)`.
/// * Configured pool answering `SELECT 1` → `("connected", true)`.
/// * Configured pool failing `SELECT 1` → `("unreachable", false)`.
pub async fn check_database(pool: Option<&PgPool>) -> (String, bool) {
    match pool {
        None => ("not_configured".to_string(), true),
        Some(pool) => {
            if sqlx::query("SELECT 1").execute(pool).await.is_ok() {
                ("connected".to_string(), true)
            } else {
                ("unreachable".to_string(), false)
            }
        }
    }
}

/// Check event bus connectivity.
///
/// The in-memory bus (dev mode) reports connected from creation; a NATS
/// bus that has dropped its connection reports disconnected and fails
/// readiness.
pub fn check_event_bus(bus: &dyn sensei_event_bus::EventBus) -> (String, bool) {
    if bus.is_connected() {
        ("connected".to_string(), true)
    } else {
        ("disconnected".to_string(), false)
    }
}

/// Check storage availability with a tiny store+delete roundtrip probe.
pub async fn check_storage(storage: &dyn FileStorageService, tenant_id: Uuid) -> (String, bool) {
    let probe_path = format!("readiness/probe-{}", Uuid::new_v4());
    match storage
        .store(tenant_id, &probe_path, b"ok", "text/plain")
        .await
    {
        Ok(_) => {
            if let Err(e) = storage.delete(tenant_id, &probe_path).await {
                tracing::warn!(error = %e, "Storage readiness probe cleanup failed");
            }
            ("ok".to_string(), true)
        }
        Err(e) => {
            tracing::warn!(error = %e, "Storage readiness probe failed");
            ("error".to_string(), false)
        }
    }
}

/// Detailed health check with all subsystem statuses.
///
/// Reports real process memory/CPU usage when the platform exposes it
/// (Linux `/proc` or macOS `ps`), and `null` otherwise.
pub async fn detailed(State(state): State<AppState>) -> Json<serde_json::Value> {
    let database = match &state.db_pool {
        Some(pool) => {
            if sqlx::query("SELECT 1").execute(&**pool).await.is_ok() {
                "connected"
            } else {
                "unreachable"
            }
        }
        None => "not_configured",
    };

    Json(serde_json::json!({
        "service": "sensei-api",
        "version": env!("CARGO_PKG_VERSION"),
        "status": "ok",
        "uptime_seconds": START_TIME.elapsed().as_secs(),
        "checks": {
            "database": database,
            "event_bus_connected": state.event_bus.is_connected(),
            "active_sessions": state.session_store.len(),
            "memory_usage_mb": read_memory_usage_mb(),
            "cpu_usage_pct": read_cpu_usage_pct(),
        }
    }))
}

/// Read the current process memory usage in MiB.
///
/// * Linux: resident set size from `/proc/self/statm` (field 2, pages,
///   assuming the standard 4 KiB page size).
/// * macOS: RSS in KiB from `ps -o rss= -p <pid>`.
/// * Other platforms / failures: `None`.
pub fn read_memory_usage_mb() -> Option<f64> {
    #[cfg(target_os = "linux")]
    {
        let statm = std::fs::read_to_string("/proc/self/statm").ok()?;
        let rss_pages = statm.split_whitespace().nth(1)?.parse::<f64>().ok()?;
        // /proc/self/statm reports pages; the standard page size on Linux
        // (x86_64/arm64) is 4096 bytes.
        Some(rss_pages * 4096.0 / (1024.0 * 1024.0))
    }
    #[cfg(target_os = "macos")]
    {
        let pid = std::process::id().to_string();
        let out = std::process::Command::new("ps")
            .args(["-o", "rss=", "-p", &pid])
            .output()
            .ok()?;
        let kb = String::from_utf8(out.stdout)
            .ok()?
            .trim()
            .parse::<f64>()
            .ok()?;
        Some(kb / 1024.0)
    }
    #[cfg(not(any(target_os = "linux", target_os = "macos")))]
    {
        let _ = ();
        None
    }
}

/// Read the current process CPU usage as a percentage of one core.
///
/// * Linux: `utime + stime` (clock ticks, standard 100 Hz) from
///   `/proc/self/stat` divided by the total system ticks from `/proc/stat`
///   — the process's lifetime share of one core.
/// * macOS: `%cpu` from `ps`.
/// * Other platforms / failures: `None`.
pub fn read_cpu_usage_pct() -> Option<f64> {
    #[cfg(target_os = "linux")]
    {
        let stat = std::fs::read_to_string("/proc/self/stat").ok()?;
        // Fields: comm (2) is parenthesized and may contain spaces, so
        // split after the last ')'.
        let rest = stat.rsplit_once(')')?.1;
        // After ')' the first field is state (3); utime is field 14 and
        // stime is field 15 of the original table, i.e. indices 1 and 2
        // after stripping "state".
        let fields: Vec<&str> = rest.split_whitespace().collect();
        let utime: f64 = fields.get(11)?.parse().ok()?;
        let stime: f64 = fields.get(12)?.parse().ok()?;
        let proc_ticks = utime + stime;

        let stat_total = std::fs::read_to_string("/proc/stat").ok()?;
        let cpu_line = stat_total.lines().next()?;
        let total_ticks: f64 = cpu_line
            .split_whitespace()
            .skip(1)
            .filter_map(|v| v.parse::<f64>().ok())
            .sum();

        if total_ticks <= 0.0 {
            return None;
        }
        Some(proc_ticks / total_ticks * 100.0)
    }
    #[cfg(target_os = "macos")]
    {
        let pid = std::process::id().to_string();
        let out = std::process::Command::new("ps")
            .args(["-o", "%cpu=", "-p", &pid])
            .output()
            .ok()?;
        String::from_utf8(out.stdout)
            .ok()?
            .trim()
            .parse::<f64>()
            .ok()
    }
    #[cfg(not(any(target_os = "linux", target_os = "macos")))]
    {
        let _ = ();
        None
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_check_database_not_configured_is_not_a_failure() {
        let (status, ok) = check_database(None).await;
        assert!(ok, "absent database must not fail readiness");
        assert_eq!(status, "not_configured");
    }

    #[tokio::test]
    async fn test_check_database_failing_pool_is_unreachable() {
        // A lazily-created pool pointing at a dead endpoint: the pool
        // construction succeeds, but SELECT 1 cannot succeed.
        let pool = sqlx::postgres::PgPoolOptions::new()
            .max_connections(1)
            .acquire_timeout(std::time::Duration::from_secs(2))
            .connect_lazy("postgres://nobody:nothing@127.0.0.1:1/nonexistent")
            .expect("connect_lazy must not connect at construction");
        let (status, ok) = check_database(Some(&pool)).await;
        assert!(!ok, "a configured-but-dead database must fail readiness");
        assert_eq!(status, "unreachable");
    }

    #[tokio::test]
    async fn test_check_event_bus_in_memory_connected() {
        let bus = sensei_event_bus::InMemoryEventBus::new();
        let (status, ok) = check_event_bus(&bus);
        assert!(ok);
        assert_eq!(status, "connected");
    }
}

//! Health check endpoints.
//!
//! Provides endpoints for readiness and liveness probes used by
//! container orchestration systems (Kubernetes, Docker, etc.).

use axum::{extract::State, Json};
use serde::Serialize;
use std::time::Instant;

use crate::state::AppState;

/// Health check response body.
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    /// Service status.
    pub status: String,
    /// Service version.
    pub version: String,
    /// Uptime in seconds since the service started.
    pub uptime_seconds: u64,
    /// Database connectivity status.
    pub database: String,
}

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
/// Performs a real `SELECT 1` against the configured database pool when one
/// is present, so the reported state reflects actual connectivity.
pub async fn readiness(State(state): State<AppState>) -> Json<HealthResponse> {
    let db_status = match &state.db_pool {
        Some(pool) => {
            let ok = sqlx::query("SELECT 1").execute(&**pool).await.is_ok();
            if ok {
                "connected"
            } else {
                "unreachable"
            }
        }
        None => "not_configured",
    };

    Json(HealthResponse {
        status: "ready".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_seconds: START_TIME.elapsed().as_secs(),
        database: db_status.to_string(),
    })
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

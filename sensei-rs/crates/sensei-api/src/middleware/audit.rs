//! Audit logging middleware.
//!
//! Records all state-changing HTTP requests (POST, PUT, DELETE) along with
//! the authenticated user, response status, and processing duration for
//! compliance and observability.

use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
};
use chrono::Utc;
use serde::Serialize;
use sensei_auth::middleware::AuthenticatedUser;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::warn;

/// A single audit log entry.
#[derive(Debug, Clone, Serialize)]
pub struct AuditEntry {
    /// ISO 8601 timestamp of the request.
    pub timestamp: String,
    /// ID of the authenticated user (if any).
    pub user_id: Option<String>,
    /// HTTP method.
    pub method: String,
    /// Request path.
    pub path: String,
    /// HTTP status code returned.
    pub status: u16,
    /// Processing duration in milliseconds.
    pub duration_ms: u64,
}

/// Thread-safe, bounded in-memory audit log.
///
/// Stores up to `max_entries` entries; older entries are dropped when the
/// limit is reached.
#[derive(Clone)]
pub struct AuditLog {
    entries: Arc<RwLock<Vec<AuditEntry>>>,
    max_entries: usize,
}

impl AuditLog {
    /// Create a new [`AuditLog`] with the given capacity.
    pub fn new(max_entries: usize) -> Self {
        Self {
            entries: Arc::new(RwLock::new(Vec::with_capacity(max_entries))),
            max_entries,
        }
    }

    /// Append an entry to the log.
    ///
    /// If the log has reached `max_entries`, the oldest entry is removed.
    pub async fn record(&self, entry: AuditEntry) {
        let mut guard = self.entries.write().await;
        if guard.len() >= self.max_entries {
            guard.remove(0);
        }
        guard.push(entry);
    }

    /// Return a snapshot of all entries.
    pub async fn get_entries(&self) -> Vec<AuditEntry> {
        let guard = self.entries.read().await;
        guard.clone()
    }

    /// Return entries recorded since the given timestamp.
    pub async fn get_entries_since(&self, since: chrono::DateTime<Utc>) -> Vec<AuditEntry> {
        let guard = self.entries.read().await;
        let since_str = since.to_rfc3339();
        guard
            .iter()
            .filter(|e| e.timestamp >= since_str)
            .cloned()
            .collect()
    }

    /// Return the number of stored entries.
    pub async fn len(&self) -> usize {
        let guard = self.entries.read().await;
        guard.len()
    }

    /// Return `true` if there are no stored entries.
    pub async fn is_empty(&self) -> bool {
        let guard = self.entries.read().await;
        guard.is_empty()
    }
}

/// Axum middleware that records audit entries for state-changing requests
/// (POST, PUT, DELETE, PATCH).
///
/// The [`AuditLog`] instance must be placed in request extensions before
/// this middleware runs (typically in the router setup via
/// `from_fn_with_state`).
pub async fn audit_middleware(req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let path = req.uri().path().to_string();
    let is_state_changing = matches!(
        method.as_str(),
        "POST" | "PUT" | "DELETE" | "PATCH"
    );

    // Extract authenticated user if present.
    let user_id = req
        .extensions()
        .get::<AuthenticatedUser>()
        .map(|u| u.user_id.to_string());

    let start = std::time::Instant::now();

    let response = next.run(req).await;

    if is_state_changing {
        let duration_ms = start.elapsed().as_millis() as u64;
        let status = response.status().as_u16();

        let entry = AuditEntry {
            timestamp: Utc::now().to_rfc3339(),
            user_id,
            method: method.to_string(),
            path,
            status,
            duration_ms,
        };

        // Try to persist the entry – failures are non-fatal.
        if let Some(audit_log) = response.extensions().get::<AuditLog>() {
            audit_log.record(entry).await;
        } else {
            warn!("AuditLog not found in response extensions; audit entry dropped");
        }
    }

    response
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    #[tokio::test]
    async fn test_audit_log_record_and_retrieve() {
        let log = AuditLog::new(100);
        assert_eq!(log.len().await, 0);
        assert!(log.is_empty().await);

        let entry = AuditEntry {
            timestamp: Utc::now().to_rfc3339(),
            user_id: Some("user-1".into()),
            method: "POST".into(),
            path: "/api/quality/ncrs".into(),
            status: 201,
            duration_ms: 42,
        };

        log.record(entry.clone()).await;
        assert_eq!(log.len().await, 1);
        assert!(!log.is_empty().await);

        let entries = log.get_entries().await;
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].method, "POST");
        assert_eq!(entries[0].user_id, Some("user-1".into()));
    }

    #[tokio::test]
    async fn test_audit_log_bounded_capacity() {
        let log = AuditLog::new(3);
        for i in 0..5 {
            let entry = AuditEntry {
                timestamp: Utc::now().to_rfc3339(),
                user_id: Some(format!("user-{}", i)),
                method: "GET".into(),
                path: "/api/test".into(),
                status: 200,
                duration_ms: i as u64,
            };
            log.record(entry).await;
        }
        assert_eq!(log.len().await, 3);
        // Oldest entries should have been removed; newest should remain.
        let entries = log.get_entries().await;
        assert_eq!(entries[0].user_id, Some("user-2".into()));
        assert_eq!(entries[2].user_id, Some("user-4".into()));
    }

    #[tokio::test]
    async fn test_audit_log_get_entries_since() {
        let log = AuditLog::new(100);

        let old_entry = AuditEntry {
            timestamp: "2020-01-01T00:00:00+00:00".into(),
            user_id: None,
            method: "GET".into(),
            path: "/old".into(),
            status: 200,
            duration_ms: 10,
        };
        let new_entry = AuditEntry {
            timestamp: Utc::now().to_rfc3339(),
            user_id: None,
            method: "POST".into(),
            path: "/new".into(),
            status: 201,
            duration_ms: 20,
        };

        log.record(old_entry).await;
        log.record(new_entry).await;

        let since = chrono::DateTime::parse_from_rfc3339("2023-01-01T00:00:00+00:00")
            .unwrap()
            .with_timezone(&Utc);
        let recent = log.get_entries_since(since).await;
        assert_eq!(recent.len(), 1);
        assert_eq!(recent[0].path, "/new");
    }

    #[tokio::test]
    async fn test_audit_log_empty() {
        let log = AuditLog::new(10);
        assert!(log.is_empty().await);
        assert_eq!(log.len().await, 0);

        let entries = log.get_entries().await;
        assert!(entries.is_empty());
    }

    #[tokio::test]
    async fn test_audit_log_multiple_methods() {
        let log = AuditLog::new(100);
        let methods = ["POST", "PUT", "DELETE", "PATCH", "GET"];
        for (i, method) in methods.iter().enumerate() {
            log.record(AuditEntry {
                timestamp: Utc::now().to_rfc3339(),
                user_id: None,
                method: method.to_string(),
                path: format!("/api/{}", method.to_lowercase()),
                status: if *method == "GET" { 200 } else { 201 },
                duration_ms: i as u64,
            })
            .await;
        }
        assert_eq!(log.len().await, 5);

        let entries = log.get_entries().await;
        assert_eq!(entries[0].method, "POST");
        assert_eq!(entries[4].method, "GET");
    }
}

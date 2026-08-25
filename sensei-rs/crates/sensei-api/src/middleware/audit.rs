//! Audit logging middleware.
//!
//! Records all state-changing HTTP requests (POST, PUT, DELETE, PATCH) along
//! with the authenticated user, response status, and processing duration for
//! compliance and observability.
//!
//! # Durability
//!
//! When a database pool is configured the entry is appended to the
//! `audit_logs` table (migration 052) via a fire-and-forget insert; insert
//! failures are logged with `tracing::error!` so audit data is never
//! silently dropped. In development mode (no pool) entries are kept in a
//! bounded in-memory ring buffer instead.

use axum::{
    extract::{ConnectInfo, Request, State},
    middleware::Next,
    response::Response,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use serde::Serialize;
use sqlx::PgPool;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

use crate::middleware::request_id::RequestId;
use crate::state::AppState;

/// A single audit log entry.
#[derive(Debug, Clone, Serialize)]
pub struct AuditEntry {
    /// ISO 8601 timestamp of the request.
    pub timestamp: String,
    /// Tenant of the authenticated user (if any).
    pub tenant_id: Option<String>,
    /// ID of the authenticated user (if any).
    pub user_id: Option<String>,
    /// Session identifier from the request extensions (if any).
    pub session_id: Option<String>,
    /// Request identifier from the request extensions (if any).
    pub request_id: Option<String>,
    /// HTTP method.
    pub method: String,
    /// Request path.
    pub path: String,
    /// HTTP status code returned.
    pub status: u16,
    /// Processing duration in milliseconds.
    pub duration_ms: u64,
    /// Effective client IP (when known).
    pub source_ip: Option<String>,
    /// Audit resource type (unused for HTTP request audit entries).
    pub resource_type: Option<String>,
    /// Audit resource id (unused for HTTP request audit entries).
    pub resource_id: Option<String>,
}

/// Audit log sink.
///
/// Appends to PostgreSQL when a pool is attached (see [`AuditLog::with_pool`])
/// and falls back to a bounded in-memory ring buffer (dev mode, up to
/// `max_entries`; older entries are dropped when the limit is reached).
#[derive(Clone)]
pub struct AuditLog {
    entries: Arc<RwLock<Vec<AuditEntry>>>,
    max_entries: usize,
    pool: Option<Arc<PgPool>>,
}

impl AuditLog {
    /// Create a new [`AuditLog`] with the given ring-buffer capacity.
    pub fn new(max_entries: usize) -> Self {
        Self {
            entries: Arc::new(RwLock::new(Vec::with_capacity(max_entries))),
            max_entries,
            pool: None,
        }
    }

    /// Attach a database pool: entries are appended to `audit_logs` instead
    /// of the in-memory ring buffer.
    pub fn with_pool(mut self, pool: Arc<PgPool>) -> Self {
        self.pool = Some(pool);
        self
    }

    /// Append an entry to the log.
    ///
    /// With a pool the insert is fire-and-forget but failures are logged
    /// with `tracing::error!` (never silently dropped). Without a pool the
    /// entry is recorded in the bounded ring buffer.
    pub async fn record(&self, entry: AuditEntry) {
        match &self.pool {
            Some(pool) => {
                let pool = Arc::clone(pool);
                let timestamp = DateTime::parse_from_rfc3339(&entry.timestamp)
                    .ok()
                    .map(|t| t.with_timezone(&Utc));
                let tenant_id = entry
                    .tenant_id
                    .as_deref()
                    .and_then(|s| Uuid::parse_str(s).ok());
                let actor_id = entry
                    .user_id
                    .as_deref()
                    .and_then(|s| Uuid::parse_str(s).ok());
                let action = format!("{} {}", entry.method, entry.path);
                let result = entry.status.to_string();
                let details = serde_json::json!({
                    "method": entry.method,
                    "path": entry.path,
                    "duration_ms": entry.duration_ms,
                });

                tokio::spawn(async move {
                    let outcome = sqlx::query(
                        "INSERT INTO audit_logs \
                         (timestamp, tenant_id, actor_id, session_id, request_id, action, \
                          resource_type, resource_id, result, source_ip, details) \
                         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
                    )
                    .bind(timestamp)
                    .bind(tenant_id)
                    .bind(actor_id)
                    .bind(entry.session_id)
                    .bind(entry.request_id)
                    .bind(action)
                    .bind(entry.resource_type)
                    .bind(entry.resource_id)
                    .bind(result)
                    .bind(entry.source_ip)
                    .bind(details)
                    .execute(&*pool)
                    .await;

                    if let Err(e) = outcome {
                        tracing::error!(
                            error = %e,
                            "Failed to persist audit log entry (audit trail may be incomplete)"
                        );
                    }
                });
            }
            None => {
                let mut guard = self.entries.write().await;
                if guard.len() >= self.max_entries {
                    guard.remove(0);
                }
                guard.push(entry);
            }
        }
    }

    /// Return a snapshot of all entries (ring buffer only).
    pub async fn get_entries(&self) -> Vec<AuditEntry> {
        let guard = self.entries.read().await;
        guard.clone()
    }

    /// Return entries recorded since the given timestamp (ring buffer only).
    pub async fn get_entries_since(&self, since: chrono::DateTime<Utc>) -> Vec<AuditEntry> {
        let guard = self.entries.read().await;
        let since_str = since.to_rfc3339();
        guard
            .iter()
            .filter(|e| e.timestamp >= since_str)
            .cloned()
            .collect()
    }

    /// Return the number of stored entries (ring buffer only).
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
/// Runs **after** authentication (see the protected-route middleware order
/// in `router.rs`), so the [`AuthenticatedUser`] is already present in the
/// request extensions when the entry is captured. The handler is timed and
/// the entry is recorded into `state.audit_log` — no response-extensions
/// indirection.
pub async fn audit_middleware(State(state): State<AppState>, req: Request, next: Next) -> Response {
    let method = req.method().clone();
    let path = req.uri().path().to_string();
    let is_state_changing = matches!(method.as_str(), "POST" | "PUT" | "DELETE" | "PATCH");

    // Extract identity and tracing context from the request extensions.
    let user = req.extensions().get::<AuthenticatedUser>().cloned();
    let request_id = req.extensions().get::<RequestId>().map(|r| r.0.clone());
    // No session-id extension is produced by the session middleware today;
    // the column stays NULL. Kept for forward compatibility.
    let session_id: Option<String> = None;
    let source_ip = req
        .extensions()
        .get::<ConnectInfo<SocketAddr>>()
        .map(|ci| ci.0.ip().to_string());

    let start = std::time::Instant::now();

    let response = next.run(req).await;

    if is_state_changing {
        let duration_ms = start.elapsed().as_millis() as u64;
        let status = response.status().as_u16();

        let entry = AuditEntry {
            timestamp: Utc::now().to_rfc3339(),
            tenant_id: user.as_ref().map(|u| u.tenant_id.to_string()),
            user_id: user.as_ref().map(|u| u.user_id.to_string()),
            session_id,
            request_id,
            method: method.to_string(),
            path,
            status,
            duration_ms,
            source_ip,
            resource_type: None,
            resource_id: None,
        };

        // Record directly into the shared audit log; failures are non-fatal
        // for the request path but are always logged.
        state.audit_log.record(entry).await;
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
            tenant_id: Some("tenant-1".into()),
            user_id: Some("user-1".into()),
            session_id: None,
            request_id: Some("req-1".into()),
            method: "POST".into(),
            path: "/api/quality/ncrs".into(),
            status: 201,
            duration_ms: 42,
            source_ip: None,
            resource_type: None,
            resource_id: None,
        };

        log.record(entry.clone()).await;
        assert_eq!(log.len().await, 1);
        assert!(!log.is_empty().await);

        let entries = log.get_entries().await;
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].method, "POST");
        assert_eq!(entries[0].user_id, Some("user-1".into()));
        assert_eq!(entries[0].request_id, Some("req-1".into()));
    }

    #[tokio::test]
    async fn test_audit_log_bounded_capacity() {
        let log = AuditLog::new(3);
        for i in 0..5 {
            let entry = AuditEntry {
                timestamp: Utc::now().to_rfc3339(),
                tenant_id: None,
                user_id: Some(format!("user-{}", i)),
                session_id: None,
                request_id: None,
                method: "GET".into(),
                path: "/api/test".into(),
                status: 200,
                duration_ms: i as u64,
                source_ip: None,
                resource_type: None,
                resource_id: None,
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
            tenant_id: None,
            user_id: None,
            session_id: None,
            request_id: None,
            method: "GET".into(),
            path: "/old".into(),
            status: 200,
            duration_ms: 10,
            source_ip: None,
            resource_type: None,
            resource_id: None,
        };
        let new_entry = AuditEntry {
            timestamp: Utc::now().to_rfc3339(),
            tenant_id: None,
            user_id: None,
            session_id: None,
            request_id: None,
            method: "POST".into(),
            path: "/new".into(),
            status: 201,
            duration_ms: 20,
            source_ip: None,
            resource_type: None,
            resource_id: None,
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
                tenant_id: None,
                user_id: None,
                session_id: None,
                request_id: None,
                method: method.to_string(),
                path: format!("/api/{}", method.to_lowercase()),
                status: if *method == "GET" { 200 } else { 201 },
                duration_ms: i as u64,
                source_ip: None,
                resource_type: None,
                resource_id: None,
            })
            .await;
        }
        assert_eq!(log.len().await, 5);

        let entries = log.get_entries().await;
        assert_eq!(entries[0].method, "POST");
        assert_eq!(entries[4].method, "GET");
    }
}

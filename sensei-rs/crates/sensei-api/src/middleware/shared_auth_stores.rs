//! PostgreSQL-backed shared auth state: access-token revocation and
//! one-time tokens (password reset / email verification).
//!
//! These were process-local; with multiple API replicas, logout/reset
//! behavior depended on which pod received the request. With a pool they
//! are shared tables (migration 043); without one the in-memory fallback
//! serves development mode.

use crate::AppState;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

/// Shared access-token revocation (jti blacklist with expiry).
#[derive(Clone)]
pub struct TokenBlacklist {
    pool: Option<sqlx::PgPool>,
    memory: Arc<RwLock<std::collections::HashSet<String>>>,
}

impl TokenBlacklist {
    pub fn new(pool: Option<sqlx::PgPool>) -> Self {
        Self {
            pool,
            memory: Arc::new(RwLock::new(std::collections::HashSet::new())),
        }
    }

    /// Record `jti:exp` (the same format the middleware reads).
    pub async fn insert(&self, entry: String) {
        // entry format: "{jti}:{exp_ts}"
        let (jti, exp) = entry
            .split_once(':')
            .map(|(j, e)| (j.to_string(), e.parse::<i64>().unwrap_or(0)))
            .unwrap_or((entry.clone(), 0));
        if let Some(pool) = &self.pool {
            if let Ok(jti_uuid) = Uuid::parse_str(&jti) {
                let expires =
                    chrono::DateTime::from_timestamp(exp, 0).unwrap_or_else(chrono::Utc::now);
                let _ = sqlx::query(
                    "INSERT INTO token_blacklist (jti, expires_at) VALUES ($1, $2) \\
                     ON CONFLICT (jti) DO NOTHING",
                )
                .bind(jti_uuid)
                .bind(expires)
                .execute(pool)
                .await;
                self.sweep().await;
                return;
            }
        }
        self.memory.write().await.insert(entry);
    }

    /// Whether the given jti is currently revoked.
    pub async fn contains(&self, jti: &str) -> bool {
        if let Some(pool) = &self.pool {
            if let Ok(jti_uuid) = Uuid::parse_str(jti) {
                let revoked: bool = sqlx::query_scalar(
                    "SELECT EXISTS(SELECT 1 FROM token_blacklist WHERE jti = $1 AND expires_at > NOW())",
                )
                .bind(jti_uuid)
                .fetch_one(pool)
                .await
                .unwrap_or(false);
                return revoked;
            }
        }
        self.memory.read().await.iter().any(|e| e.starts_with(jti))
    }

    /// Remove expired entries (called lazily on insert and by the health
    /// endpoint).
    pub async fn sweep(&self) {
        if let Some(pool) = &self.pool {
            let _ = sqlx::query("DELETE FROM token_blacklist WHERE expires_at <= NOW()")
                .execute(pool)
                .await;
        }
    }

    /// Whether the blacklist is empty.
    pub async fn is_empty(&self) -> bool {
        self.len().await == 0
    }

    pub async fn len(&self) -> usize {
        if let Some(pool) = &self.pool {
            let _ = self.sweep().await;
            return sqlx::query_scalar("SELECT COUNT(*) FROM token_blacklist")
                .fetch_one(pool)
                .await
                .unwrap_or(0) as usize;
        }
        self.memory.read().await.len()
    }
}

/// One-time token kind.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum TokenKind {
    PasswordReset,
    EmailVerification,
}

/// Record stored for a one-time token.
#[derive(Debug, Clone)]
pub struct TokenRecord {
    pub user_id: Uuid,
    pub tenant_id: Uuid,
    pub expires_at: chrono::DateTime<chrono::Utc>,
}

/// Shared one-time token store (password reset / email verification).
#[derive(Clone)]
pub struct TokenStore {
    kind: TokenKind,
    pool: Option<sqlx::PgPool>,
    memory: Arc<RwLock<std::collections::HashMap<String, TokenRecord>>>,
}

impl TokenStore {
    pub fn new(kind: TokenKind, pool: Option<sqlx::PgPool>) -> Self {
        Self {
            kind,
            pool,
            memory: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    fn table(&self) -> &'static str {
        match self.kind {
            TokenKind::PasswordReset => "password_reset_tokens",
            TokenKind::EmailVerification => "email_verification_tokens",
        }
    }

    /// Insert a one-time token (raw value hashed with SHA-256).
    pub async fn insert(
        &self,
        token: &str,
        user_id: Uuid,
        tenant_id: Uuid,
        expires_at: chrono::DateTime<chrono::Utc>,
    ) {
        let hash = Self::hash(token);
        if let Some(pool) = &self.pool {
            let _ = sqlx::query(&format!(
                "INSERT INTO {} (token_hash, user_id, tenant_id, expires_at) \\
                 VALUES ($1, $2, $3, $4) ON CONFLICT (token_hash) DO NOTHING",
                self.table()
            ))
            .bind(&hash)
            .bind(user_id)
            .bind(tenant_id)
            .bind(expires_at)
            .execute(pool)
            .await;
            return;
        }
        self.memory.write().await.insert(
            hash,
            TokenRecord {
                user_id,
                tenant_id,
                expires_at,
            },
        );
    }

    /// Consume a one-time token atomically. Returns the record only when the
    /// token exists, is unused and not expired; the token is consumed
    /// (deleted) in the same operation.
    pub async fn consume(&self, token: &str) -> Option<TokenRecord> {
        let hash = Self::hash(token);
        if let Some(pool) = &self.pool {
            let row: Option<(Uuid, Uuid, chrono::DateTime<chrono::Utc>)> =
                sqlx::query_as(&format!(
                    "DELETE FROM {} WHERE token_hash = $1 AND consumed_at IS NULL \\
                   AND expires_at > NOW() \\
                 RETURNING user_id, tenant_id, expires_at",
                    self.table()
                ))
                .bind(&hash)
                .fetch_optional(pool)
                .await
                .unwrap_or(None);
            return row.map(|(user_id, tenant_id, expires_at)| TokenRecord {
                user_id,
                tenant_id,
                expires_at,
            });
        }
        self.memory
            .write()
            .await
            .remove(&hash)
            .filter(|r| r.expires_at > chrono::Utc::now())
    }

    fn hash(token: &str) -> String {
        use sha2::{Digest, Sha256};
        hex::encode(Sha256::digest(token.as_bytes()))
    }
}

/// Convenience accessors on [`AppState`].
impl AppState {
    pub fn token_blacklist(&self) -> TokenBlacklist {
        self.token_blacklist.clone()
    }

    pub fn password_reset_tokens_store(&self) -> TokenStore {
        self.password_reset_store.clone()
    }

    pub fn email_verification_tokens_store(&self) -> TokenStore {
        self.email_verification_store.clone()
    }
}

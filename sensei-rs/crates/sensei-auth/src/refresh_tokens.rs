//! Refresh-token store with rotation and reuse detection.
//!
//! Stores SHA-256 hashes of refresh tokens (never the raw tokens) together
//! with their token family, owner, and expiry. Supports rotation
//! (`validate_and_rotate`), whole-family revocation, and single-token
//! revocation. Reuse of an already-rotated token is detected and reported
//! as a likely theft.
//!
//! Backing store: PostgreSQL when a [`PgPool`] is provided (see migration
//! 019 for the `refresh_tokens` table), otherwise an in-memory map with a
//! periodic cleanup task for expired entries.

use chrono::{DateTime, Utc};
use sha2::{Digest, Sha256};
use sqlx::PgPool;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;
use tokio::sync::RwLock;
use uuid::Uuid;

/// Errors from the refresh-token store.
#[derive(Debug, Error)]
pub enum TokenReuseDetected {
    /// The presented token hash is not known to the store.
    #[error("Refresh token is invalid or unknown")]
    Invalid,

    /// The token has already been rotated; presenting it again means it was
    /// stolen or replayed. The whole family should be revoked by the caller.
    #[error("Refresh token reuse detected")]
    ReuseDetected,

    /// A backing-store operation failed.
    #[error("Refresh token store error: {0}")]
    Database(String),
}

/// Record of a stored refresh token.
#[derive(Debug, Clone)]
struct TokenRecord {
    family_id: Uuid,
    user_id: Uuid,
    credential_version: u64,
    expires_at: DateTime<Utc>,
    rotated_to_hash: Option<String>,
}

/// Store of refresh-token hashes.
pub struct RefreshTokenStore {
    pool: Option<PgPool>,
    tokens: Arc<RwLock<HashMap<String, TokenRecord>>>,
}

impl RefreshTokenStore {
    /// Create a new store.
    ///
    /// When `pool` is `Some`, tokens are persisted in the `refresh_tokens`
    /// table. Otherwise an in-memory store is used and a background task is
    /// spawned to clean up expired entries.
    pub fn new(pool: Option<PgPool>) -> Self {
        let store = Self {
            pool,
            tokens: Arc::new(RwLock::new(HashMap::new())),
        };
        if store.pool.is_none() {
            store.spawn_cleanup();
        }
        store
    }

    /// Hash a refresh token (SHA-256, hex encoded).
    fn hash_token(token: &str) -> String {
        hex::encode(Sha256::digest(token.as_bytes()))
    }

    /// Store a new refresh token.
    pub async fn store(
        &self,
        token: &str,
        family_id: Uuid,
        user_id: Uuid,
        credential_version: u64,
        expires_at: DateTime<Utc>,
    ) -> Result<(), TokenReuseDetected> {
        let hash = Self::hash_token(token);
        match &self.pool {
            Some(pool) => {
                sqlx::query(
                    "INSERT INTO refresh_tokens (id, family_id, user_id, token_hash, credential_version, expires_at) \
                     VALUES (gen_random_uuid(), $1, $2, $3, $4, $5) \
                     ON CONFLICT (token_hash) DO NOTHING",
                )
                .bind(family_id)
                .bind(user_id)
                .bind(&hash)
                .bind(credential_version as i64)
                .bind(expires_at)
                .execute(pool)
                .await
                .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;
                Ok(())
            }
            None => {
                self.tokens.write().await.insert(
                    hash,
                    TokenRecord {
                        family_id,
                        user_id,
                        credential_version,
                        expires_at,
                        rotated_to_hash: None,
                    },
                );
                Ok(())
            }
        }
    }

    /// Validate a refresh token and atomically rotate it to a new token.
    ///
    /// Returns `(family_id, user_id)` on success. Errors:
    /// - [`TokenReuseDetected::Invalid`] when the token hash is unknown.
    /// - [`TokenReuseDetected::ReuseDetected`] when the token was already
    ///   rotated (replay/theft).
    pub async fn validate_and_rotate(
        &self,
        token: &str,
        new_token: &str,
        credential_version: u64,
        new_expires_at: DateTime<Utc>,
    ) -> Result<(Uuid, Uuid), TokenReuseDetected> {
        let hash = Self::hash_token(token);
        let new_hash = Self::hash_token(new_token);

        match &self.pool {
            Some(pool) => {
                let mut tx = pool
                    .begin()
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;

                let row: Option<(Uuid, Uuid, i64, Option<String>)> = sqlx::query_as(
                    "SELECT family_id, user_id, credential_version, rotated_to_hash \
                     FROM refresh_tokens WHERE token_hash = $1 FOR UPDATE",
                )
                .bind(&hash)
                .fetch_optional(&mut *tx)
                .await
                .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;

                let Some((family_id, user_id, stored_version, rotated_to)) = row else {
                    return Err(TokenReuseDetected::Invalid);
                };

                if rotated_to.is_some() {
                    return Err(TokenReuseDetected::ReuseDetected);
                }

                // A password change/reset bumps the credential version; any
                // token issued before that is no longer usable.
                if stored_version as u64 != credential_version {
                    sqlx::query(
                        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE family_id = $1",
                    )
                    .bind(family_id)
                    .execute(&mut *tx)
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;
                    return Err(TokenReuseDetected::Invalid);
                }

                sqlx::query("UPDATE refresh_tokens SET rotated_to_hash = $1 WHERE token_hash = $2")
                    .bind(&new_hash)
                    .bind(&hash)
                    .execute(&mut *tx)
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;

                sqlx::query(
                    "INSERT INTO refresh_tokens (id, family_id, user_id, token_hash, credential_version, expires_at) \
                     VALUES (gen_random_uuid(), $1, $2, $3, $4, $5)",
                )
                .bind(family_id)
                .bind(user_id)
                .bind(&new_hash)
                .bind(credential_version as i64)
                .bind(new_expires_at)
                .execute(&mut *tx)
                .await
                .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;

                tx.commit()
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;

                Ok((family_id, user_id))
            }
            None => {
                let mut tokens = self.tokens.write().await;

                let Some(record) = tokens.get(&hash) else {
                    return Err(TokenReuseDetected::Invalid);
                };
                if record.rotated_to_hash.is_some() {
                    return Err(TokenReuseDetected::ReuseDetected);
                }
                if record.credential_version != credential_version {
                    return Err(TokenReuseDetected::Invalid);
                }

                let family_id = record.family_id;
                let user_id = record.user_id;

                tokens.insert(
                    new_hash.clone(),
                    TokenRecord {
                        family_id,
                        user_id,
                        credential_version,
                        expires_at: new_expires_at,
                        rotated_to_hash: None,
                    },
                );
                if let Some(record) = tokens.get_mut(&hash) {
                    record.rotated_to_hash = Some(new_hash);
                }

                Ok((family_id, user_id))
            }
        }
    }

    /// Revoke every refresh token belonging to a user (logout-all / password
    /// change). Tokens in the in-memory store are removed; DB rows are marked
    /// revoked.
    pub async fn revoke_user_sessions(&self, user_id: Uuid) -> Result<(), TokenReuseDetected> {
        match &self.pool {
            Some(pool) => {
                sqlx::query("UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL")
                    .bind(user_id)
                    .execute(pool)
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;
                Ok(())
            }
            None => {
                let mut tokens = self.tokens.write().await;
                tokens.retain(|_, record| record.user_id != user_id);
                Ok(())
            }
        }
    }

    /// Revoke every token in a token family.
    pub async fn revoke_family(&self, family_id: Uuid) -> Result<(), TokenReuseDetected> {
        match &self.pool {
            Some(pool) => {
                sqlx::query("DELETE FROM refresh_tokens WHERE family_id = $1")
                    .bind(family_id)
                    .execute(pool)
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;
                Ok(())
            }
            None => {
                self.tokens
                    .write()
                    .await
                    .retain(|_, record| record.family_id != family_id);
                Ok(())
            }
        }
    }

    /// Revoke a single refresh token.
    pub async fn revoke(&self, token: &str) -> Result<(), TokenReuseDetected> {
        let hash = Self::hash_token(token);
        match &self.pool {
            Some(pool) => {
                sqlx::query("DELETE FROM refresh_tokens WHERE token_hash = $1")
                    .bind(&hash)
                    .execute(pool)
                    .await
                    .map_err(|e| TokenReuseDetected::Database(e.to_string()))?;
                Ok(())
            }
            None => {
                self.tokens.write().await.remove(&hash);
                Ok(())
            }
        }
    }

    /// Spawn a background task that periodically removes expired tokens.
    ///
    /// Only meaningful for the in-memory backing store; the PostgreSQL
    /// backend keeps rows and lets callers revoke on demand.
    pub fn spawn_cleanup(&self) {
        let tokens = Arc::clone(&self.tokens);
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(3600));
            loop {
                interval.tick().await;
                let now = Utc::now();
                tokens
                    .write()
                    .await
                    .retain(|_, record| record.expires_at > now);
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn store() -> RefreshTokenStore {
        RefreshTokenStore::new(None)
    }

    #[tokio::test]
    async fn store_and_rotate() {
        let store = store();
        let family_id = Uuid::new_v4();
        let user_id = Uuid::new_v4();
        let expires = Utc::now() + chrono::Duration::days(7);

        let token = "first-token";
        store
            .store(token, family_id, user_id, 0, expires)
            .await
            .unwrap();

        let (got_family, got_user) = store
            .validate_and_rotate(token, "second-token", 0, expires)
            .await
            .unwrap();
        assert_eq!(got_family, family_id);
        assert_eq!(got_user, user_id);

        // The new token is now valid.
        store
            .validate_and_rotate("second-token", "third-token", 0, expires)
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn reuse_of_rotated_token_is_detected() {
        let store = store();
        let family_id = Uuid::new_v4();
        let user_id = Uuid::new_v4();
        let expires = Utc::now() + chrono::Duration::days(7);

        let token = "victim-token";
        store
            .store(token, family_id, user_id, 0, expires)
            .await
            .unwrap();
        store
            .validate_and_rotate(token, "attacker-token", 0, expires)
            .await
            .unwrap();

        // Presenting the already-rotated token again is a theft signal.
        assert!(matches!(
            store
                .validate_and_rotate(token, "another-token", 0, expires)
                .await,
            Err(TokenReuseDetected::ReuseDetected)
        ));
    }

    #[tokio::test]
    async fn unknown_token_is_invalid() {
        let store = store();
        let expires = Utc::now() + chrono::Duration::days(7);
        assert!(matches!(
            store
                .validate_and_rotate("never-stored", "new-token", 0, expires)
                .await,
            Err(TokenReuseDetected::Invalid)
        ));
    }

    #[tokio::test]
    async fn revoke_single_token() {
        let store = store();
        let family_id = Uuid::new_v4();
        let expires = Utc::now() + chrono::Duration::days(7);

        store
            .store("token-a", family_id, Uuid::new_v4(), 0, expires)
            .await
            .unwrap();
        store.revoke("token-a").await.unwrap();

        assert!(matches!(
            store
                .validate_and_rotate("token-a", "token-b", 0, expires)
                .await,
            Err(TokenReuseDetected::Invalid)
        ));
    }

    #[tokio::test]
    async fn revoke_family_invalidates_all_members() {
        let store = store();
        let family_id = Uuid::new_v4();
        let user_id = Uuid::new_v4();
        let expires = Utc::now() + chrono::Duration::days(7);

        store
            .store("token-1", family_id, user_id, 0, expires)
            .await
            .unwrap();
        store
            .validate_and_rotate("token-1", "token-2", 0, expires)
            .await
            .unwrap();
        store.revoke_family(family_id).await.unwrap();

        assert!(matches!(
            store
                .validate_and_rotate("token-2", "token-3", 0, expires)
                .await,
            Err(TokenReuseDetected::Invalid)
        ));
    }

    #[test]
    fn hashes_are_deterministic_and_sensitive() {
        let a = RefreshTokenStore::hash_token("super-secret-token");
        let b = RefreshTokenStore::hash_token("super-secret-token");
        let c = RefreshTokenStore::hash_token("super-secret-token2");
        assert_eq!(a, b);
        assert_ne!(a, c);
        assert_ne!(a, "super-secret-token");
    }
}

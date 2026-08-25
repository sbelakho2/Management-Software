//! JWT token encoding and decoding.
//!
//! Uses the [`jsonwebtoken`] crate to issue and validate access and
//! refresh tokens with configurable expiration.

use chrono::{Duration, Utc};
use jsonwebtoken::errors::ErrorKind;
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// JWT claims for access tokens.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccessTokenClaims {
    /// Subject (user ID).
    pub sub: Uuid,
    /// Tenant ID.
    pub tenant_id: Uuid,
    /// Unique token ID (for revocation and replay detection).
    pub jti: Uuid,
    /// Issuer.
    pub iss: String,
    /// Audience.
    pub aud: String,
    /// Expiration timestamp (Unix epoch seconds).
    pub exp: usize,
    /// Issued at timestamp (Unix epoch seconds).
    pub iat: usize,
    /// Not before timestamp (Unix epoch seconds).
    pub nbf: usize,
    /// User roles for RBAC.
    pub roles: Vec<String>,
    /// Token type (always "access").
    pub token_type: String,
}

/// JWT claims for refresh tokens.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RefreshTokenClaims {
    /// Subject (user ID).
    pub sub: Uuid,
    /// Tenant ID.
    pub tenant_id: Uuid,
    /// Unique token ID (for revocation and replay detection).
    pub jti: Uuid,
    /// Issuer.
    pub iss: String,
    /// Audience.
    pub aud: String,
    /// Expiration timestamp (Unix epoch seconds).
    pub exp: usize,
    /// Issued at timestamp (Unix epoch seconds).
    pub iat: usize,
    /// Token type (always "refresh").
    pub token_type: String,
    /// Token family ID for rotation tracking.
    pub family_id: Uuid,
}

/// Service for issuing and validating JWT tokens.
#[derive(Clone)]
pub struct JwtService {
    encoding_key: EncodingKey,
    decoding_key: DecodingKey,
    issuer: String,
    audience: String,
    access_expiry_minutes: i64,
    refresh_expiry_days: i64,
}

impl JwtService {
    /// Create a new [`JwtService`] with the given secret and configuration.
    pub fn new(
        secret: &str,
        issuer: impl Into<String>,
        audience: impl Into<String>,
        access_expiry_minutes: i64,
        refresh_expiry_days: i64,
    ) -> Self {
        Self {
            encoding_key: EncodingKey::from_secret(secret.as_bytes()),
            decoding_key: DecodingKey::from_secret(secret.as_bytes()),
            issuer: issuer.into(),
            audience: audience.into(),
            access_expiry_minutes,
            refresh_expiry_days,
        }
    }

    /// Issue an access token for the given user.
    pub fn issue_access_token(
        &self,
        user_id: Uuid,
        tenant_id: Uuid,
        roles: Vec<String>,
    ) -> Result<String> {
        let now = Utc::now();
        let exp = now + Duration::minutes(self.access_expiry_minutes);

        let claims = AccessTokenClaims {
            sub: user_id,
            tenant_id,
            jti: Uuid::new_v4(),
            iss: self.issuer.clone(),
            aud: self.audience.clone(),
            exp: exp.timestamp() as usize,
            iat: now.timestamp() as usize,
            nbf: now.timestamp() as usize,
            roles,
            token_type: "access".to_string(),
        };

        encode(&Header::default(), &claims, &self.encoding_key)
            .map_err(|e| SenseiError::TokenError(format!("Failed to encode JWT: {e}")))
    }

    /// Issue a refresh token for the given user within an explicit token family.
    ///
    /// The `family_id` must come from an existing family (e.g. created at
    /// registration) so that refresh-token rotation can be tracked across
    /// the whole family. A fresh family must be created by the caller.
    pub fn issue_refresh_token(
        &self,
        user_id: Uuid,
        tenant_id: Uuid,
        family_id: Uuid,
    ) -> Result<String> {
        let now = Utc::now();
        let exp = now + Duration::days(self.refresh_expiry_days);

        let claims = RefreshTokenClaims {
            sub: user_id,
            tenant_id,
            jti: Uuid::new_v4(),
            iss: self.issuer.clone(),
            aud: self.audience.clone(),
            exp: exp.timestamp() as usize,
            iat: now.timestamp() as usize,
            token_type: "refresh".to_string(),
            family_id,
        };

        encode(&Header::default(), &claims, &self.encoding_key)
            .map_err(|e| SenseiError::TokenError(format!("Failed to encode refresh token: {e}")))
    }

    /// Validate and decode an access token.
    pub fn validate_access_token(&self, token: &str) -> Result<AccessTokenClaims> {
        let mut validation = Validation::default();
        validation.set_issuer(&[&self.issuer]);
        validation.set_audience(&[&self.audience]);
        // Require the `sub` claim; the typed `Uuid` field also enforces that
        // the subject is a valid UUID.
        validation.required_spec_claims.insert("sub".to_string());

        let token_data = decode::<AccessTokenClaims>(token, &self.decoding_key, &validation)
            .map_err(|e| map_decode_error(e, "Invalid token"))?;

        if token_data.claims.token_type != "access" {
            return Err(SenseiError::TokenError("Invalid token type".to_string()));
        }

        Ok(token_data.claims)
    }

    /// Validate and decode a refresh token.
    pub fn validate_refresh_token(&self, token: &str) -> Result<RefreshTokenClaims> {
        let mut validation = Validation::default();
        validation.set_issuer(&[&self.issuer]);
        validation.set_audience(&[&self.audience]);
        validation.required_spec_claims.insert("sub".to_string());

        let token_data = decode::<RefreshTokenClaims>(token, &self.decoding_key, &validation)
            .map_err(|e| map_decode_error(e, "Invalid refresh token"))?;

        if token_data.claims.token_type != "refresh" {
            return Err(SenseiError::TokenError("Invalid token type".to_string()));
        }

        Ok(token_data.claims)
    }
}

/// Map a JWT decode error to a [`SenseiError`], detecting expired signatures
/// by error kind rather than by string matching.
fn map_decode_error(err: jsonwebtoken::errors::Error, context: &str) -> SenseiError {
    match err.kind() {
        ErrorKind::ExpiredSignature => SenseiError::TokenExpired,
        _ => SenseiError::TokenError(format!("{context}: {err}")),
    }
}
#[cfg(test)]
mod tests {
    use super::*;

    fn make_service() -> JwtService {
        JwtService::new(
            "test-secret-key-for-testing-purposes-only",
            "sensei-test",
            "sensei-test-api",
            15,
            7,
        )
    }

    #[test]
    fn test_issue_and_validate_access_token() {
        let svc = make_service();
        let user_id = Uuid::new_v4();
        let tenant_id = Uuid::new_v4();
        let roles = vec!["admin".to_string(), "quality_manager".to_string()];

        let token = svc
            .issue_access_token(user_id, tenant_id, roles.clone())
            .unwrap();
        let claims = svc.validate_access_token(&token).unwrap();

        assert_eq!(claims.sub, user_id);
        assert_eq!(claims.tenant_id, tenant_id);
        assert_eq!(claims.roles, roles);
        assert_eq!(claims.token_type, "access");
        assert!(!claims.jti.is_nil());
    }

    #[test]
    fn test_issue_and_validate_refresh_token() {
        let svc = make_service();
        let user_id = Uuid::new_v4();
        let tenant_id = Uuid::new_v4();
        let family_id = Uuid::new_v4();

        let token = svc
            .issue_refresh_token(user_id, tenant_id, family_id)
            .unwrap();
        let claims = svc.validate_refresh_token(&token).unwrap();

        assert_eq!(claims.sub, user_id);
        assert_eq!(claims.tenant_id, tenant_id);
        assert_eq!(claims.token_type, "refresh");
        assert_eq!(claims.family_id, family_id);
        assert!(!claims.jti.is_nil());
    }

    #[test]
    fn test_refresh_token_checks_audience() {
        let svc = make_service();
        let claims = RefreshTokenClaims {
            sub: Uuid::new_v4(),
            tenant_id: Uuid::new_v4(),
            jti: Uuid::new_v4(),
            iss: "sensei-test".to_string(),
            aud: "some-other-audience".to_string(),
            exp: (Utc::now() + Duration::days(7)).timestamp() as usize,
            iat: Utc::now().timestamp() as usize,
            token_type: "refresh".to_string(),
            family_id: Uuid::new_v4(),
        };
        let token = encode(&Header::default(), &claims, &svc.encoding_key).unwrap();
        assert!(matches!(
            svc.validate_refresh_token(&token),
            Err(SenseiError::TokenError(_))
        ));
    }

    #[test]
    fn test_expired_token_returns_token_expired() {
        let svc = make_service();
        let claims = AccessTokenClaims {
            sub: Uuid::new_v4(),
            tenant_id: Uuid::new_v4(),
            jti: Uuid::new_v4(),
            iss: "sensei-test".to_string(),
            aud: "sensei-test-api".to_string(),
            exp: (Utc::now() - Duration::minutes(5)).timestamp() as usize,
            iat: (Utc::now() - Duration::minutes(20)).timestamp() as usize,
            nbf: (Utc::now() - Duration::minutes(20)).timestamp() as usize,
            roles: vec![],
            token_type: "access".to_string(),
        };
        let token = encode(&Header::default(), &claims, &svc.encoding_key).unwrap();
        assert!(matches!(
            svc.validate_access_token(&token),
            Err(SenseiError::TokenExpired)
        ));
    }

    #[test]
    fn test_invalid_token_fails() {
        let svc = make_service();
        let result = svc.validate_access_token("invalid-token");
        assert!(result.is_err());
    }
}

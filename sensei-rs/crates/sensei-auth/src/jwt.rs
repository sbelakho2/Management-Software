//! JWT token encoding and decoding.
//!
//! Uses the [`jsonwebtoken`] crate to issue and validate access and
//! refresh tokens with configurable expiration.

use chrono::{Duration, Utc};
use jsonwebtoken::errors::ErrorKind;
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, TokenData, Validation};
use sensei_core::error::{Result, SenseiError};
use serde::de::DeserializeOwned;
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
    /// Session identifier — one user may hold many concurrent sessions
    /// (laptop, phone, second tab); logout revokes exactly one sid.
    pub sid: Uuid,
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
    /// User roles at ISSUE time — INFORMATIONAL ONLY (twenty-ninth audit
    /// Wave A): authorization never trusts these. The auth middleware
    /// reloads the CURRENT user row and resolves LIVE roles + effective
    /// permissions per authenticated request, so a role change,
    /// deactivation or deletion takes effect immediately even though this
    /// claim stays fixed until token expiry. The claim remains for
    /// diagnostics/introspection (and as the in-memory/dev-mode
    /// fallback identity when no database is attached).
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
    /// Credential version of the user at issue time. A password change or
    /// reset increments the version; older refresh tokens become invalid.
    pub credential_version: u64,
    /// Session identifier (carried through refreshes).
    pub sid: Uuid,
}

/// Service for issuing and validating JWT tokens.
/// Current signing key identifier (tokens signed with the current key).
pub const CURRENT_KID: &str = "current";
/// Previous signing key identifier (tokens signed with the previous key,
/// still accepted until they expire — key rotation without logout storms).
pub const PREVIOUS_KID: &str = "previous";

#[derive(Clone)]
pub struct JwtService {
    encoding_key: EncodingKey,
    /// Optional previous key: tokens signed with it remain valid until they
    /// expire (rotation grace period), but new tokens use the current key.
    previous_decoding_key: Option<DecodingKey>,
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
        Self::with_previous_key(
            secret,
            None,
            issuer,
            audience,
            access_expiry_minutes,
            refresh_expiry_days,
        )
    }

    /// Create a [`JwtService`] with signing-key rotation support.
    ///
    /// `previous_secret` is the previous signing key (e.g. from the previous
    /// deployment's `JWT_SECRET`): tokens signed with it remain valid until
    /// they expire, while all new tokens are signed with the current key and
    /// carry the `kid` header so validators can select the right key.
    pub fn with_previous_key(
        current_secret: &str,
        previous_secret: Option<&str>,
        issuer: impl Into<String>,
        audience: impl Into<String>,
        access_expiry_minutes: i64,
        refresh_expiry_days: i64,
    ) -> Self {
        Self {
            encoding_key: EncodingKey::from_secret(current_secret.as_bytes()),
            decoding_key: DecodingKey::from_secret(current_secret.as_bytes()),
            previous_decoding_key: previous_secret.map(|s| DecodingKey::from_secret(s.as_bytes())),
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
        sid: Uuid,
        roles: Vec<String>,
    ) -> Result<String> {
        let now = Utc::now();
        let exp = now + Duration::minutes(self.access_expiry_minutes);

        let claims = AccessTokenClaims {
            sub: user_id,
            tenant_id,
            jti: Uuid::new_v4(),
            sid,
            iss: self.issuer.clone(),
            aud: self.audience.clone(),
            exp: exp.timestamp() as usize,
            iat: now.timestamp() as usize,
            nbf: now.timestamp() as usize,
            roles,
            token_type: "access".to_string(),
        };

        let header = Header {
            kid: Some(CURRENT_KID.to_string()),
            ..Header::default()
        };
        encode(&header, &claims, &self.encoding_key)
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
        credential_version: u64,
        sid: Uuid,
    ) -> Result<String> {
        let now = Utc::now();
        let exp = now + Duration::days(self.refresh_expiry_days);

        let claims = RefreshTokenClaims {
            sub: user_id,
            tenant_id,
            jti: Uuid::new_v4(),
            sid,
            iss: self.issuer.clone(),
            aud: self.audience.clone(),
            credential_version,
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

        let token_data = self
            .decode_with_key_rotation::<AccessTokenClaims>(token, &validation)
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

        let token_data = self
            .decode_with_key_rotation::<RefreshTokenClaims>(token, &validation)
            .map_err(|e| map_decode_error(e, "Invalid refresh token"))?;

        if token_data.claims.token_type != "refresh" {
            return Err(SenseiError::TokenError("Invalid token type".to_string()));
        }

        Ok(token_data.claims)
    }

    /// Decode a token honouring signing-key rotation: try the current key
    /// first, then the previous key (tokens issued before a rotation remain
    /// valid until they expire).
    fn decode_with_key_rotation<T: DeserializeOwned>(
        &self,
        token: &str,
        validation: &Validation,
    ) -> std::result::Result<TokenData<T>, jsonwebtoken::errors::Error> {
        match decode::<T>(token, &self.decoding_key, validation) {
            Ok(data) => Ok(data),
            Err(e) => {
                if let Some(previous) = &self.previous_decoding_key {
                    if let Ok(data) = decode::<T>(token, previous, validation) {
                        return Ok(data);
                    }
                }
                Err(e)
            }
        }
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
            .issue_access_token(user_id, tenant_id, Uuid::new_v4(), roles.clone())
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
            .issue_refresh_token(user_id, tenant_id, family_id, 0, Uuid::new_v4())
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
            credential_version: 0,
            sid: Uuid::new_v4(),
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
            sid: Uuid::new_v4(),
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

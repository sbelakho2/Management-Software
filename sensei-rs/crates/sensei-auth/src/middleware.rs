//! Axum authentication middleware.
//!
//! Provides a Tower layer that extracts and validates JWT tokens from
//! incoming requests, attaching user identity information to the request
//! extensions for downstream handlers to use.
//!
//! # Live per-request authorization (twenty-ninth audit Wave A)
//!
//! When a database pool is attached to the request (production), the
//! middleware does NOT trust the roles minted into the token: after JWT
//! validation (signature/exp/aud/iss) and the API layer's JTI revocation
//! check, it reloads the CURRENT user row (exists, tenant matches the
//! token tenant, `is_active`), uses the LIVE roles, resolves the effective
//! permissions through [`crate::resolver`] (static hierarchy + the
//! tenant's custom `roles` rows) and inserts an [`AuthenticatedUser`]
//! carrying that live state. A stale JWT therefore cannot outlive a role
//! revocation, a deactivation, or a deletion. Token roles are only an
//! informational fallback for in-memory/dev mode (no pool attached).

use axum::{
    extract::{FromRequestParts, Request},
    http::{header, request::Parts, StatusCode},
    middleware::Next,
    response::Response,
    Json,
};
use sensei_core::db::TenantTx;
use sensei_core::error::SenseiError;
use serde::Serialize;
use sqlx::PgPool;
use std::collections::HashSet;
use std::sync::Arc;
use uuid::Uuid;

use crate::jwt::{AccessTokenClaims, JwtService};
use crate::resolver::resolve_effective_permissions;

/// Authenticated user identity extracted from a valid JWT.
#[derive(Debug, Clone)]
pub struct AuthenticatedUser {
    /// The user's unique identifier.
    pub user_id: Uuid,
    /// The tenant this user belongs to.
    pub tenant_id: Uuid,
    /// The user's assigned roles.
    pub roles: Vec<String>,
    /// Session identifier from the access-token claims (one user may hold
    /// many concurrent sessions; logout revokes exactly one sid).
    pub sid: Option<Uuid>,
    /// LIVE effective permissions resolved per authenticated request
    /// (static hierarchy + tenant custom rows) by the auth middleware.
    /// When empty, the legacy process-wide RBAC registry is consulted by
    /// [`Self::require_permission`] instead (rollout compatibility for
    /// in-memory/dev mode and direct test constructions).
    pub permissions: HashSet<String>,
}

impl AuthenticatedUser {
    /// Require a functional permission (e.g. `"finance:invoice:create"`).
    ///
    /// Consults the request-local permission set resolved by the auth
    /// middleware FIRST — the set is authoritative when non-empty (denial
    /// never falls through to the global registry, otherwise a stale
    /// process-global grant could resurrect a revoked permission). The
    /// legacy process-wide shared authorization service is consulted ONLY
    /// when the request-local set is empty (rollout compatibility: dev
    /// in-memory mode and direct constructions, e.g. tests).
    pub fn require_permission(&self, permission: &str) -> Result<(), SenseiError> {
        if !self.permissions.is_empty() {
            if permission_set_grants(&self.permissions, permission) {
                return Ok(());
            }
            return Err(SenseiError::Forbidden(format!(
                "You do not have permission to perform this action (required: {permission})"
            )));
        }
        // Legacy process-global path (empty request-local set only).
        let rbac = crate::rbac::authorization_service();
        let perm = sensei_core::domain::entities::Permission::new(permission);
        if rbac.has_permission_for_tenant(&self.roles, Some(self.tenant_id), &perm) {
            Ok(())
        } else {
            Err(SenseiError::Forbidden(format!(
                "You do not have permission to perform this action (required: {permission})"
            )))
        }
    }

    /// Returns `true` if the user has the given role.
    pub fn has_role(&self, role: &str) -> bool {
        self.roles.iter().any(|r| r == role)
    }

    /// Returns `true` if the user has any of the given roles.
    pub fn has_any_role(&self, roles: &[&str]) -> bool {
        roles.iter().any(|role| self.has_role(role))
    }
}

/// Wildcard-aware grant check against a resolved permission set.
///
/// Mirrors the matching semantics of the static RBAC map: `*:*` matches
/// everything; `resource:*` matches every action on a resource; `*:action`
/// matches the action on every resource; anything else must match exactly
/// (actions may be dotted, e.g. `quality:ncr:create`).
fn permission_set_grants(permissions: &HashSet<String>, required: &str) -> bool {
    let Some((required_resource, required_action)) = required.split_once(':') else {
        return false;
    };
    permissions
        .iter()
        .any(|granted| grant_matches(granted, required_resource, required_action))
}

fn grant_matches(granted: &str, required_resource: &str, required_action: &str) -> bool {
    if granted == "*:*" {
        return true;
    }
    let Some((granted_resource, granted_action)) = granted.split_once(':') else {
        return false;
    };
    let resource_match = granted_resource == "*" || granted_resource == required_resource;
    let action_match = granted_action == "*" || granted_action == required_action;
    resource_match && action_match
}

/// Error response for auth failures.
#[derive(Debug, Serialize)]
pub struct AuthErrorResponse {
    pub error: String,
    pub message: String,
}

/// Axum middleware for JWT authentication.
///
/// Extracts the `Authorization: Bearer <token>` header, validates the JWT,
/// and inserts [`AuthenticatedUser`] into the request extensions.
///
/// The API middleware (`sensei-api::middleware::auth::auth_layer`) runs
/// the JTI revocation (blacklist) check BEFORE delegating here, and
/// attaches the database pool as an `Option<Arc<PgPool>>` extension. When
/// a pool is present (production), the CURRENT user state is reloaded per
/// request (live roles + effective permissions); otherwise (in-memory/dev
/// mode) the token's own claims are used as the identity and the legacy
/// RBAC registry backs `require_permission`.
pub async fn auth_middleware(
    mut req: Request,
    next: Next,
) -> Result<Response, (StatusCode, Json<AuthErrorResponse>)> {
    let jwt_service = req
        .extensions()
        .get::<JwtService>()
        .cloned()
        .ok_or_else(|| {
            tracing::error!(
                "Auth middleware: JwtService not registered in request extensions; \
                 the application failed to configure JWT authentication"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(AuthErrorResponse {
                    error: "configuration_error".to_string(),
                    message: "JWT service not configured".to_string(),
                }),
            )
        })?;

    // Extract Bearer token from Authorization header
    let token = req
        .headers()
        .get(header::AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
        .ok_or_else(|| {
            (
                StatusCode::UNAUTHORIZED,
                Json(AuthErrorResponse {
                    error: "missing_token".to_string(),
                    message: "Missing or invalid Authorization header".to_string(),
                }),
            )
        })?;

    // Validate the token (signature, exp, aud, iss, token type).
    match jwt_service.validate_access_token(token) {
        Ok(claims) => {
            let pool = req
                .extensions()
                .get::<Option<Arc<PgPool>>>()
                .cloned()
                .flatten();
            let user = match pool {
                // Production: reload LIVE state (user exists + active,
                // tenant matches, live roles, effective permissions).
                // This runs AFTER the API layer's JTI revocation check.
                Some(pool) => match reload_live_user(&pool, &claims).await {
                    Ok(Some(user)) => user,
                    Ok(None) => {
                        tracing::warn!(
                            user_id = %claims.sub,
                            tenant_id = %claims.tenant_id,
                            "Live auth reload: account missing, inactive, or tenant mismatch — denying"
                        );
                        return Err((
                            StatusCode::UNAUTHORIZED,
                            Json(AuthErrorResponse {
                                error: "account_unavailable".to_string(),
                                message: "Your account no longer exists or is inactive; please log in again"
                                    .to_string(),
                            }),
                        ));
                    }
                    Err(e) => {
                        // Fail closed: a valid-looking token must not be
                        // trusted when live authorization cannot be
                        // verified.
                        tracing::error!(
                            error = %e,
                            user_id = %claims.sub,
                            tenant_id = %claims.tenant_id,
                            "Live auth reload failed — denying request"
                        );
                        return Err((
                            StatusCode::SERVICE_UNAVAILABLE,
                            Json(AuthErrorResponse {
                                error: "authorization_unavailable".to_string(),
                                message:
                                    "Live authorization state could not be verified; please retry"
                                        .to_string(),
                            }),
                        ));
                    }
                },
                // In-memory/dev mode: no pool attached — the token claims
                // are the identity (token roles are informational) and the
                // legacy registry backs permission checks.
                None => AuthenticatedUser {
                    user_id: claims.sub,
                    tenant_id: claims.tenant_id,
                    roles: claims.roles,
                    permissions: HashSet::new(),
                    sid: Some(claims.sid),
                },
            };
            req.extensions_mut().insert(user);
            Ok(next.run(req).await)
        }
        Err(e) => {
            let message = match &e {
                // A dedicated variant, mapped by the JWT layer from
                // `ErrorKind::ExpiredSignature` — never string matching.
                SenseiError::TokenExpired => "Token has expired",
                _ => "Invalid token",
            };

            Err((
                StatusCode::UNAUTHORIZED,
                Json(AuthErrorResponse {
                    error: "invalid_token".to_string(),
                    message: message.to_string(),
                }),
            ))
        }
    }
}

/// Reload the CURRENT user row for an authenticated token and resolve the
/// LIVE effective permission set.
///
/// `Ok(Some(user))` — the user exists, belongs to the token's tenant and
/// is active. `Ok(None)` — no such user (deleted, tenant mismatch, or
/// deactivated). `Err(String)` — the live state could not be verified
/// (fail closed by the caller).
///
/// The `users` table is FORCE RLS (migration 079) with a fail-closed
/// policy once `app.tenant_id` is established, so the read runs inside a
/// tenant-scoped [`TenantTx`]: under the production non-owner `sensei_app`
/// role a raw-pool read would silently return nothing, and under the
/// tenant context exactly the token's own tenant is admitted. The
/// explicit `tenant_id` predicate stays as a second barrier.
async fn reload_live_user(
    pool: &PgPool,
    claims: &AccessTokenClaims,
) -> std::result::Result<Option<AuthenticatedUser>, String> {
    let mut db = TenantTx::begin(pool, claims.tenant_id)
        .await
        .map_err(|e| format!("Failed to begin tenant-scoped auth reload: {e}"))?;
    let row: Option<(Uuid, Vec<String>, bool)> = sqlx::query_as(
        "SELECT id, roles, is_active FROM users \
         WHERE id = $1 AND tenant_id = $2",
    )
    .bind(claims.sub)
    .bind(claims.tenant_id)
    .fetch_optional(&mut **db.tx())
    .await
    .map_err(|e| format!("Failed to reload the current user: {e}"))?;
    // Dropping the transaction rolls the read scope back.
    drop(db);

    let Some((user_id, live_roles, is_active)) = row else {
        return Ok(None);
    };
    if !is_active {
        return Ok(None);
    }

    let permissions = resolve_effective_permissions(pool, claims.tenant_id, &live_roles)
        .await
        .map_err(|e| format!("Failed to resolve effective permissions: {e}"))?;

    Ok(Some(AuthenticatedUser {
        user_id,
        tenant_id: claims.tenant_id,
        roles: live_roles,
        permissions,
        sid: Some(claims.sid),
    }))
}

/// Axum extractor for retrieving the authenticated user from request extensions.
///
/// # Example
///
/// ```ignore
/// async fn protected_handler(user: AuthenticatedUser) -> impl IntoResponse {
///     format!("Hello, user {}!", user.user_id)
/// }
/// ```
impl<S> FromRequestParts<S> for AuthenticatedUser
where
    S: Send + Sync,
{
    type Rejection = (StatusCode, Json<AuthErrorResponse>);

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        parts
            .extensions
            .get::<AuthenticatedUser>()
            .cloned()
            .ok_or_else(|| {
                (
                    StatusCode::UNAUTHORIZED,
                    Json(AuthErrorResponse {
                        error: "not_authenticated".to_string(),
                        message: "Not authenticated".to_string(),
                    }),
                )
            })
    }
}

/// Optional auth extractor (does not reject if no token).
///
/// Allows endpoints to work for both authenticated and unauthenticated users.
pub struct OptionalUser(pub Option<AuthenticatedUser>);

impl<S> FromRequestParts<S> for OptionalUser
where
    S: Send + Sync,
{
    type Rejection = (StatusCode, Json<AuthErrorResponse>);

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        Ok(OptionalUser(
            parts.extensions.get::<AuthenticatedUser>().cloned(),
        ))
    }
}

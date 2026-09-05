//! Axum authentication middleware.
//!
//! Provides a Tower layer that extracts and validates JWT tokens from
//! incoming requests, attaching user identity information to the request
//! extensions for downstream handlers to use.
//!
//! # Live per-request authorization (twenty-ninth audit Wave A;
//! thirtieth-audit P0-9/P0-10)
//!
//! When a database pool is attached to the request (production), the
//! middleware does NOT trust the roles minted into the token: after JWT
//! validation (signature/exp/aud/iss) and the API layer's JTI revocation
//! check, it reloads the CURRENT user row (exists, tenant matches the
//! token tenant, `is_active`), uses the LIVE roles, resolves the effective
//! permissions through [`crate::resolver`] (static hierarchy + the
//! tenant's custom `roles` rows) and inserts an [`AuthenticatedUser`]
//! carrying that live state. A stale JWT therefore cannot outlive a role
//! revocation, a deactivation, or a deletion.
//!
//! The whole reload runs in ONE tenant-scoped [`TenantTx`]: the live-user
//! lookup, the `roles` SELECT (the table is fail-closed FORCE RLS since
//! migration 098 — a raw-pool read silently returns nothing), the custom
//! permission resolution, the principal's role-slot
//! [`AuthorizedScope`] resolution and the tenant's authorization-revision
//! snapshot all read under the same `app.tenant_id` context.
//!
//! The resolved permission set is ALWAYS the full live set — an empty set
//! means the principal genuinely holds no permissions and
//! [`AuthenticatedUser::require_permission`] denies (no process-global
//! registry fallback). Token roles are only used in-memory/dev mode (no
//! pool attached), where they are expanded through the compiled static
//! RBAC map (no tenant DB exists to read custom rows).

use axum::{
    extract::{FromRequestParts, Request},
    http::{header, request::Parts, StatusCode},
    middleware::Next,
    response::Response,
    Json,
};
use sensei_core::db::TenantTx;
use sensei_core::domain::scope::AuthorizedScope;
use sensei_core::error::SenseiError;
use serde::Serialize;
use sqlx::PgPool;
use std::collections::HashSet;
use std::sync::Arc;
use uuid::Uuid;

use crate::jwt::{AccessTokenClaims, JwtService};
use crate::rbac::RbacService;
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
    /// The caller's LIVE effective permissions resolved per authenticated
    /// request (static hierarchy + tenant custom rows) by the auth
    /// middleware. ALWAYS resolved (thirtieth-audit P0-10) — an empty set
    /// is a real empty grant (the principal holds no permissions and every
    /// [`Self::require_permission`] check denies), never a "not yet
    /// loaded" sentinel. In-memory/dev mode (no DB pool) resolves the
    /// token roles through the compiled static RBAC map.
    pub permissions: HashSet<String>,
}

impl AuthenticatedUser {
    /// Require a functional permission (e.g. `"finance:invoice:create"`).
    ///
    /// Consults the request-local permission set resolved by the auth
    /// middleware — the set is ALWAYS authoritative (thirtieth-audit
    /// P0-10): it is fully resolved at authentication time, so there is
    /// no "empty means consult the process-global registry" branch. An
    /// empty set denies everything; wildcards inside the set
    /// (`*:*`, `resource:*`, `*:action`) are still honored. Removing the
    /// legacy fallback closes the resurrection hole where a stale
    /// process-global grant could re-grant a permission revoked in the
    /// live tenant state.
    pub fn require_permission(&self, permission: &str) -> Result<(), SenseiError> {
        if permission_set_grants(&self.permissions, permission) {
            return Ok(());
        }
        Err(SenseiError::Forbidden(format!(
            "You do not have permission to perform this action (required: {permission})"
        )))
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
/// request (live roles + fully resolved effective permissions) inside ONE
/// tenant-scoped transaction; otherwise (in-memory/dev mode) the token's
/// own roles are expanded through the compiled static RBAC map (no tenant
/// DB exists to read custom rows) — never an empty "not loaded" sentinel.
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
                // In-memory/dev mode: no pool attached — the token roles
                // are expanded through the compiled static RBAC map (the
                // dev services have no tenant DB whose custom `roles`
                // rows could be read). The permission set is still fully
                // resolved here, never the empty "not yet loaded"
                // sentinel: an empty set is a real empty grant.
                None => AuthenticatedUser {
                    user_id: claims.sub,
                    tenant_id: claims.tenant_id,
                    roles: claims.roles.clone(),
                    permissions: RbacService::new().expand_static(&claims.roles),
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
/// ONE tenant-scoped transaction spans the whole per-request authorization
/// reload (thirtieth-audit P0-9):
///
/// 1. the live-user lookup (`users` is FORCE RLS since migration 079 — a
///    raw-pool read under the production non-owner `sensei_app` role
///    silently returns nothing, so the read runs inside this [`TenantTx`],
///    which admits exactly the token's own tenant; the explicit
///    `tenant_id` predicate stays as a second barrier);
/// 2. the tenant custom-role SELECT + permission resolution
///    ([`resolve_effective_permissions`]) — `roles` is also fail-closed
///    FORCE RLS (migration 098 sweeps every `tenant_id` table), so the
///    role rows must be read on THIS transaction, never a raw pool;
/// 3. the principal's role-slot [`AuthorizedScope`] resolution and
/// 4. the tenant's authorization-revision snapshot — the rest of the
///    per-request authorization surface. All four read under the same
///    `app.tenant_id` context and any failure fails the reload closed: a
///    permissions claim is only "fully resolved" when the surrounding
///    authorization state is readable. (Downstream builders that need the
///    scope/snapshot OBJECTS — RequestContext, the AI preparation layer —
///    re-derive them in their own tenant-scoped transactions; this reload
///    verifies the reads succeed at authentication time.)
///
/// The [`AuthenticatedUser`] is constructed with the FULLY RESOLVED
/// permission set — an empty set is a genuine empty grant, never a
/// fallback signal.
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

    let Some((user_id, live_roles, is_active)) = row else {
        return Ok(None);
    };
    if !is_active {
        return Ok(None);
    }

    // Custom `roles` rows + static expansion, INSIDE the same transaction
    // (`roles` is fail-closed FORCE RLS — a raw-pool read would silently
    // return zero rows in production).
    let permissions = resolve_effective_permissions(&mut db, &live_roles)
        .await
        .map_err(|e| format!("Failed to resolve effective permissions: {e}"))?;

    // The rest of the authorization surface, in the same transaction:
    // the principal's role-slot scope and the revision snapshot.
    AuthorizedScope::resolve(&mut db, user_id)
        .await
        .map_err(|e| format!("Failed to resolve the principal's authorized scope: {e}"))?;
    let _revisions: Option<(i64, i64, i64)> = sqlx::query_as(
        "SELECT policy_revision, relationship_revision, principal_revision \
         FROM authorization_revisions WHERE tenant_id = $1",
    )
    .bind(claims.tenant_id)
    .fetch_optional(&mut **db.tx())
    .await
    .map_err(|e| format!("Failed to read the authorization revision snapshot: {e}"))?;
    // Dropping the transaction rolls the read scope back.
    drop(db);

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

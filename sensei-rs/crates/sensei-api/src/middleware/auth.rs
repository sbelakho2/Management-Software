//! Authentication middleware for the API.
//!
//! Wraps the sensei-auth middleware for use with Axum's middleware stack.
//! Injects the [`JwtService`] from application state into request extensions
//! so the downstream auth middleware can validate tokens.
//!
//! Also enforces the token blacklist: access tokens whose `jti` was
//! blacklisted at logout are rejected with `401`, and expired blacklist
//! entries are swept lazily (at most every `SWEEP_INTERVAL` requests) so
//! the set does not grow unbounded.

use axum::{
    extract::{Request, State},
    http::StatusCode,
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use sensei_auth::jwt::AccessTokenClaims;
use sensei_auth::middleware::auth_middleware;
use serde::Serialize;
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::state::AppState;

/// Sweep the blacklist at most once per this many authenticated requests.
const SWEEP_INTERVAL: usize = 100;

/// Tracks how many requests have passed since the last blacklist sweep.
static SWEEP_COUNTER: AtomicUsize = AtomicUsize::new(0);

/// Error response for blacklisted tokens.
#[derive(Debug, Serialize)]
struct BlacklistError {
    error: String,
    message: String,
}

/// Extract the bearer token from the `Authorization` header.
fn bearer_token(req: &Request) -> Option<&str> {
    req.headers()
        .get(axum::http::header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
}

/// Check whether the token's `jti` has been blacklisted.
///
/// Blacklist entries are stored as `"{jti}:{exp_ts}"`. An entry whose
/// `exp` has already passed is treated as absent (and will be swept).
/// The set is bounded by the periodic lazy sweep, so a linear probe is
/// acceptable.
async fn is_blacklisted(state: &AppState, claims: &AccessTokenClaims) -> Result<bool, String> {
    state
        .token_blacklist
        .contains(&claims.jti.to_string())
        .await
}

/// Lazily remove blacklist entries whose tokens have expired.
async fn sweep_blacklist(state: &AppState) {
    state.token_blacklist.sweep().await;
}

/// Axum middleware layer for JWT authentication.
///
/// Extracts the [`JwtService`] from [`AppState`], injects it into the request
/// extensions, then delegates to [`auth_middleware`] for token validation.
///
/// **Must be used with `from_fn_with_state`**, not `from_fn`, because it
/// requires the [`State`] extractor.
pub async fn auth_layer(State(state): State<AppState>, mut req: Request, next: Next) -> Response {
    // Reject tokens whose jti was blacklisted at logout. The JWT is
    // validated here (cheap, single signature check) to read its `jti` and
    // `exp`; `auth_middleware` re-validates as the authoritative check.
    if let Some(token) = bearer_token(&req) {
        if let Ok(claims) = state.jwt_service.validate_access_token(token) {
            // FAIL CLOSED: if the revocation store cannot answer, the
            // token is treated as revoked (deny).
            let blacklisted = match is_blacklisted(&state, &claims).await {
                Ok(v) => v,
                Err(e) => {
                    tracing::error!(error = %e, jti = %claims.jti, "Blacklist check failed — denying");
                    true
                }
            };
            if blacklisted {
                let body = BlacklistError {
                    error: "token_blacklisted".to_string(),
                    message: "Token has been invalidated by logout".to_string(),
                };
                return (StatusCode::UNAUTHORIZED, Json(body)).into_response();
            }
        }
    }

    // Lazily sweep expired blacklist entries, at most once per
    // SWEEP_INTERVAL requests, to bound the set size.
    if SWEEP_COUNTER.fetch_add(1, Ordering::Relaxed) % SWEEP_INTERVAL == SWEEP_INTERVAL - 1 {
        sweep_blacklist(&state).await;
    }

    // Inject JwtService into extensions so the downstream middleware can find it.
    req.extensions_mut().insert((*state.jwt_service).clone());

    match auth_middleware(req, next).await {
        Ok(response) => response,
        Err((status, json)) => (status, json).into_response(),
    }
}

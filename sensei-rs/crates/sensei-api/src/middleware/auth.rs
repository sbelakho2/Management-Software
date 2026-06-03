//! Authentication middleware for the API.
//!
//! Wraps the sensei-auth middleware for use with Axum's middleware stack.
//! Injects the [`JwtService`] from application state into request extensions
//! so the downstream auth middleware can validate tokens.

use axum::{
    extract::{Request, State},
    middleware::Next,
    response::{IntoResponse, Response},
};
use sensei_auth::middleware::auth_middleware;

use crate::state::AppState;

/// Axum middleware layer for JWT authentication.
///
/// Extracts the [`JwtService`] from [`AppState`], injects it into the request
/// extensions, then delegates to [`auth_middleware`] for token validation.
///
/// **Must be used with `from_fn_with_state`**, not `from_fn`, because it
/// requires the [`State`] extractor.
pub async fn auth_layer(
    State(state): State<AppState>,
    mut req: Request,
    next: Next,
) -> Response {
    // Inject JwtService into extensions so the downstream middleware can find it.
    req.extensions_mut().insert((*state.jwt_service).clone());

    match auth_middleware(req, next).await {
        Ok(response) => response,
        Err((status, json)) => (status, json).into_response(),
    }
}

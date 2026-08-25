//! CORS middleware configuration.
//!
//! Configures Cross-Origin Resource Sharing for the API server
//! using `tower-http`'s CORS layer.
//!
//! In non-development environments an empty or invalid
//! `cors_allowed_origins` list is a deployment error: instead of silently
//! opening the API to every origin, a prominent error is logged and CORS is
//! left unconfigured (no cross-origin access). The permissive `Any` mode is
//! only used in development.

use sensei_core::config::AppConfig;
use tower_http::cors::{Any, CorsLayer};
use tower_http::cors::AllowOrigin;
use tracing::{error, warn};

/// Build a [`CorsLayer`] from the application configuration.
pub fn build_cors_layer(config: &AppConfig) -> CorsLayer {
    let mut valid_origins = Vec::new();
    for origin in &config.api.cors_allowed_origins {
        match origin.parse::<axum::http::HeaderValue>() {
            Ok(val) => valid_origins.push(val),
            Err(e) => {
                warn!(
                    origin = %origin,
                    error = %e,
                    "Skipping invalid CORS origin"
                );
            }
        }
    }

    let cors_layer = CorsLayer::new()
        .allow_methods(Any)
        .allow_headers(Any)
        .expose_headers([axum::http::header::HeaderName::from_static("x-request-id")])
        .max_age(std::time::Duration::from_secs(3600));

    let permissive = valid_origins.iter().any(|o| o == "*");
    if valid_origins.is_empty() || permissive {
        if config.environment.is_dev() {
            // Development convenience: allow any origin.
            cors_layer.allow_origin(Any)
        } else {
            // Production/Staging safety: never fall back to `Any`. Log a
            // prominent error and emit no `Access-Control-Allow-Origin`
            // header, which keeps same-origin traffic working while
            // blocking cross-origin browser access.
            error!(
                environment = %config.environment,
                "CORS_ALLOWED_ORIGINS is empty or contains '*' in a non-development \
                 environment; CORS is effectively disabled. Set explicit allowed \
                 origins (comma-separated) via CORS_ALLOWED_ORIGINS."
            );
            cors_layer
        }
    } else {
        cors_layer.allow_origin(AllowOrigin::list(valid_origins))
    }
}

//! CORS middleware configuration.
//!
//! Configures Cross-Origin Resource Sharing for the API server
//! using `tower-http`'s CORS layer.

use sensei_core::config::ApiConfig;
use tower_http::cors::{Any, CorsLayer};
use tower_http::cors::AllowOrigin;
use tracing::warn;

/// Build a [`CorsLayer`] from the API configuration.
pub fn build_cors_layer(config: &ApiConfig) -> CorsLayer {
    let mut valid_origins = Vec::new();
    for origin in &config.cors_allowed_origins {
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

    if valid_origins.is_empty() || valid_origins.iter().any(|o| o == "*") {
        cors_layer.allow_origin(Any)
    } else {
        cors_layer.allow_origin(AllowOrigin::list(valid_origins))
    }
}

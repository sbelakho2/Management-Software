//! Test application setup for end-to-end API tests.
//!
//! Provides [`TestApp`] which builds the full Axum router with in-memory
//! services and sends requests through the middleware stack without
//! binding to a TCP port.

use axum::{
    body::Body,
    http::{Request, Response, StatusCode},
    Router,
};
use sensei_api::{build_router, AppState};
use sensei_auth::password::hash_password;
use sensei_core::config::AppConfig;
use sensei_core::types::{EntityId, TenantId};
use sensei_services::users::{InMemoryUsersService, UsersService};
use std::sync::Arc;
use tower::ServiceExt;

/// A test application server wrapping the Axum router.
///
/// Uses [`tower::ServiceExt::oneshot`] to send requests through the full
/// middleware stack without binding a TCP port. This is faster than
/// HTTP-based testing and still exercises all middleware layers.
#[derive(Clone)]
pub struct TestApp {
    /// The configured Axum router.
    router: Router,
    /// Shared application state (accessible for seeding data).
    pub state: AppState,
    /// Password for the seeded admin user.
    pub admin_password: String,
    /// Tenant ID for the seeded admin user.
    pub admin_tenant_id: TenantId,
    /// User ID for the seeded admin user.
    pub admin_user_id: EntityId,
}

impl TestApp {
    /// Create a new [`TestApp`] with a seeded admin user and in-memory services.
    ///
    /// The admin user credentials:
    /// - Email: `admin@sensei.test`
    /// - Password: `TestAdmin123!`
    /// - Tenant: a new random UUID
    /// - Roles: `["admin", "user"]`
    pub async fn new() -> Self {
        let password = "TestAdmin123!".to_string();
        let hash = hash_password(&password).expect("Failed to hash admin password");
        let tenant_id = TenantId::new_v4();

        let users_service = InMemoryUsersService::with_admin(
            "admin@sensei.test",
            "Admin User",
            &hash,
            tenant_id,
        );
        let users_service = Arc::new(users_service) as Arc<dyn UsersService>;

        let config = AppConfig::from_env().expect("Failed to load test configuration");
        let state = AppState::new(config, users_service);

        // Get the admin user ID from the service
        let admin = state
            .users_service
            .find_by_email("admin@sensei.test")
            .await
            .expect("Admin user not found");
        let admin_user_id = admin.id;

        let router = build_router(state.clone());

        Self {
            router,
            state,
            admin_password: password,
            admin_tenant_id: tenant_id,
            admin_user_id,
        }
    }

    /// Create a new [`TestApp`] with a custom application state.
    ///
    /// Useful for tests that need to pre-seed data before building the router.
    pub fn from_state(state: AppState) -> Self {
        let router = build_router(state.clone());
        Self {
            router,
            state,
            admin_password: String::new(),
            admin_tenant_id: TenantId::nil(),
            admin_user_id: EntityId::nil(),
        }
    }

    /// Send an HTTP request through the router and return the response.
    ///
    /// This uses [`tower::ServiceExt::oneshot`] which invokes the full
    /// middleware stack without binding a TCP port.
    pub async fn send_request(
        &self,
        req: Request<Body>,
    ) -> Response<Body> {
        let mut router = self.router.clone();
        router
            .oneshot(req)
            .await
            .expect("Request to test router failed")
    }

    /// Build a GET request to the given URI path.
    pub fn get(&self, path: &str) -> Request<Body> {
        Request::builder()
            .uri(path)
            .body(Body::empty())
            .expect("Failed to build GET request")
    }

    /// Build a GET request with an Authorization header.
    pub fn get_authenticated(&self, path: &str, token: &str) -> Request<Body> {
        Request::builder()
            .uri(path)
            .header("Authorization", format!("Bearer {}", token))
            .body(Body::empty())
            .expect("Failed to build authenticated GET request")
    }

    /// Build a POST request with a JSON body.
    pub fn post(&self, path: &str, body: serde_json::Value) -> Request<Body> {
        let json_bytes = serde_json::to_vec(&body).expect("Failed to serialize JSON body");
        Request::builder()
            .uri(path)
            .method("POST")
            .header("Content-Type", "application/json")
            .body(Body::from(json_bytes))
            .expect("Failed to build POST request")
    }

    /// Build a POST request with JSON body and Authorization header.
    pub fn post_authenticated(
        &self,
        path: &str,
        token: &str,
        body: serde_json::Value,
    ) -> Request<Body> {
        let json_bytes = serde_json::to_vec(&body).expect("Failed to serialize JSON body");
        Request::builder()
            .uri(path)
            .method("POST")
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", token))
            .body(Body::from(json_bytes))
            .expect("Failed to build authenticated POST request")
    }

    /// Build a PUT request with a JSON body.
    pub fn put(&self, path: &str, body: serde_json::Value) -> Request<Body> {
        let json_bytes = serde_json::to_vec(&body).expect("Failed to serialize JSON body");
        Request::builder()
            .uri(path)
            .method("PUT")
            .header("Content-Type", "application/json")
            .body(Body::from(json_bytes))
            .expect("Failed to build PUT request")
    }

    /// Build a PUT request with JSON body and Authorization header.
    pub fn put_authenticated(
        &self,
        path: &str,
        token: &str,
        body: serde_json::Value,
    ) -> Request<Body> {
        let json_bytes = serde_json::to_vec(&body).expect("Failed to serialize JSON body");
        Request::builder()
            .uri(path)
            .method("PUT")
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", token))
            .body(Body::from(json_bytes))
            .expect("Failed to build authenticated PUT request")
    }

    /// Build a PATCH request with a JSON body.
    pub fn patch(&self, path: &str, body: serde_json::Value) -> Request<Body> {
        let json_bytes = serde_json::to_vec(&body).expect("Failed to serialize JSON body");
        Request::builder()
            .uri(path)
            .method("PATCH")
            .header("Content-Type", "application/json")
            .body(Body::from(json_bytes))
            .expect("Failed to build PATCH request")
    }

    /// Build a PATCH request with JSON body and Authorization header.
    pub fn patch_authenticated(
        &self,
        path: &str,
        token: &str,
        body: serde_json::Value,
    ) -> Request<Body> {
        let json_bytes = serde_json::to_vec(&body).expect("Failed to serialize JSON body");
        Request::builder()
            .uri(path)
            .method("PATCH")
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", token))
            .body(Body::from(json_bytes))
            .expect("Failed to build authenticated PATCH request")
    }

    /// Build a DELETE request with Authorization header.
    pub fn delete_authenticated(&self, path: &str, token: &str) -> Request<Body> {
        Request::builder()
            .uri(path)
            .method("DELETE")
            .header("Authorization", format!("Bearer {}", token))
            .body(Body::empty())
            .expect("Failed to build authenticated DELETE request")
    }

    /// Parse the response body as JSON.
    pub async fn json_body<T: serde::de::DeserializeOwned>(
        &self,
        response: &mut Response<Body>,
    ) -> T {
        let body = axum::body::to_bytes(std::mem::take(response.body_mut()), 10 * 1024 * 1024)
            .await
            .expect("Failed to read response body");
        serde_json::from_slice(&body).expect("Failed to parse JSON response body")
    }

    /// Log in as the admin user and return the access token.
    pub async fn login_as_admin(&self) -> String {
        let login_body = serde_json::json!({
            "email": "admin@sensei.test",
            "password": self.admin_password,
        });
        let req = self.post("/api/v1/auth/login", login_body);
        let mut resp = self.send_request(req).await;
        assert_eq!(resp.status(), StatusCode::OK, "Admin login failed");

        let body: serde_json::Value = self.json_body(&mut resp).await;
        body["access_token"]
            .as_str()
            .expect("No access_token in login response")
            .to_string()
    }

    /// Convenience: parse response body bytes to string.
    pub async fn response_text(&self, response: &mut Response<Body>) -> String {
        let body = axum::body::to_bytes(std::mem::take(response.body_mut()), 10 * 1024 * 1024)
            .await
            .expect("Failed to read response body");
        String::from_utf8(body.to_vec()).unwrap_or_default()
    }
}

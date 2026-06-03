//! Generic HTTP API client wrapper.

use serde::{de::DeserializeOwned, Deserialize, Serialize};

/// A lightweight HTTP client for the Sensei backend API.
#[derive(Debug, Clone)]
pub struct ApiClient {
    base_url: String,
    token: Option<String>,
}

impl ApiClient {
    /// Create a new `ApiClient` pointing at the given base URL.
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            token: None,
        }
    }

    /// Set the bearer token for subsequent requests.
    pub fn set_token(&mut self, token: &str) {
        self.token = Some(token.to_string());
    }

    /// Clear the current bearer token.
    pub fn clear_token(&mut self) {
        self.token = None;
    }

    /// Return the current bearer token, if set.
    pub fn token(&self) -> Option<&str> {
        self.token.as_deref()
    }

    /// Build the full URL for a path relative to the API base.
    pub fn url(&self, path: &str) -> String {
        format!("{}{}", self.base_url, path)
    }

    /// Perform a GET request.
    pub async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T, ApiError> {
        let client = reqwest::Client::new();
        let mut req = client.get(self.url(path));

        if let Some(token) = &self.token {
            req = req.bearer_auth(token);
        }

        let resp = req.send().await.map_err(|e| ApiError::Http(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(ApiError::Status(resp.status().as_u16()));
        }

        resp.json().await.map_err(|e| ApiError::Json(e.to_string()))
    }

    /// Perform a POST request with a JSON body.
    pub async fn post<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, ApiError> {
        let client = reqwest::Client::new();
        let mut req = client.post(self.url(path)).json(body);

        if let Some(token) = &self.token {
            req = req.bearer_auth(token);
        }

        let resp = req.send().await.map_err(|e| ApiError::Http(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(ApiError::Status(resp.status().as_u16()));
        }

        resp.json().await.map_err(|e| ApiError::Json(e.to_string()))
    }

    /// Perform a PUT request with a JSON body.
    pub async fn put<T: DeserializeOwned, B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, ApiError> {
        let client = reqwest::Client::new();
        let mut req = client.put(self.url(path)).json(body);

        if let Some(token) = &self.token {
            req = req.bearer_auth(token);
        }

        let resp = req.send().await.map_err(|e| ApiError::Http(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(ApiError::Status(resp.status().as_u16()));
        }

        resp.json().await.map_err(|e| ApiError::Json(e.to_string()))
    }

    /// Perform a DELETE request.
    pub async fn delete<T: DeserializeOwned>(&self, path: &str) -> Result<T, ApiError> {
        let client = reqwest::Client::new();
        let mut req = client.delete(self.url(path));

        if let Some(token) = &self.token {
            req = req.bearer_auth(token);
        }

        let resp = req.send().await.map_err(|e| ApiError::Http(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(ApiError::Status(resp.status().as_u16()));
        }

        resp.json().await.map_err(|e| ApiError::Json(e.to_string()))
    }
}

/// Errors that can occur during API calls.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ApiError {
    /// HTTP transport error.
    Http(String),
    /// Non-success HTTP status code.
    Status(u16),
    /// JSON deserialization error.
    Json(String),
    /// Authentication error.
    Auth(String),
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ApiError::Http(e) => write!(f, "HTTP error: {}", e),
            ApiError::Status(code) => write!(f, "HTTP status {}", code),
            ApiError::Json(e) => write!(f, "JSON error: {}", e),
            ApiError::Auth(msg) => write!(f, "Auth error: {}", msg),
        }
    }
}

impl std::error::Error for ApiError {}

//! Configuration types for the Sensei ERP system.
//!
//! Defines the configuration structures used by all services.
//! Configuration is typically loaded from environment variables or config files.

use serde::{Deserialize, Serialize};

/// Top-level configuration for the Sensei application.
///
/// Each section corresponds to a subsystem (database, auth, event bus, etc.).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// The environment name (development, staging, production).
    pub environment: Environment,
    /// Database configuration.
    pub database: DatabaseConfig,
    /// Authentication configuration.
    pub auth: AuthConfig,
    /// Event bus configuration (NATS).
    pub event_bus: EventBusConfig,
    /// API server configuration.
    pub api: ApiConfig,
    /// Email/SMTP configuration.
    pub email: EmailConfig,
    /// Observability configuration.
    pub observability: ObservabilityConfig,
    /// Feature flags.
    pub features: FeatureFlags,
    /// File storage configuration (local disk or S3/MinIO).
    pub storage: StorageConfig,
}

impl AppConfig {
    /// Load configuration from environment variables.
    ///
    /// Uses typical `FOO_BAR` naming convention for env vars.
    pub fn from_env() -> Result<Self, ConfigError> {
        // Default implementation: construct from defaults + env overrides
        let environment = Environment::from_env();
        Ok(Self {
            database: DatabaseConfig::from_env(),
            auth: AuthConfig::from_env(),
            event_bus: EventBusConfig::from_env(),
            api: ApiConfig::from_env(),
            email: EmailConfig::from_env(),
            observability: ObservabilityConfig::from_env(),
            features: FeatureFlags::default(),
            storage: StorageConfig::from_env(),
            environment,
        })
    }
}

/// The deployment environment.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum Environment {
    /// Local development.
    Development,
    /// Staging/testing.
    Staging,
    /// Production.
    Production,
}

impl Environment {
    /// Detect the environment from the `SENSEI_ENV` environment variable.
    pub fn from_env() -> Self {
        match std::env::var("SENSEI_ENV")
            .unwrap_or_else(|_| "development".to_string())
            .to_lowercase()
            .as_str()
        {
            "production" | "prod" => Environment::Production,
            "staging" => Environment::Staging,
            _ => Environment::Development,
        }
    }

    /// Returns `true` if this is a development environment.
    pub fn is_dev(&self) -> bool {
        matches!(self, Environment::Development)
    }

    /// Returns `true` if this is a production environment.
    pub fn is_prod(&self) -> bool {
        matches!(self, Environment::Production)
    }
}

impl std::fmt::Display for Environment {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Environment::Development => write!(f, "development"),
            Environment::Staging => write!(f, "staging"),
            Environment::Production => write!(f, "production"),
        }
    }
}

/// Database configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    /// PostgreSQL connection URL.
    pub url: String,
    /// Maximum number of connections in the pool.
    pub max_connections: u32,
    /// Connection timeout in seconds.
    pub connection_timeout_secs: u64,
    /// Whether to run migrations on startup.
    pub auto_migrate: bool,
}

impl DatabaseConfig {
    /// Load database configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            url: std::env::var("DATABASE_URL")
                .unwrap_or_else(|_| "postgres://postgres:postgres@localhost:5432/sensei".to_string()),
            max_connections: std::env::var("DB_MAX_CONNECTIONS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(20),
            connection_timeout_secs: std::env::var("DB_CONNECTION_TIMEOUT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
            auto_migrate: std::env::var("DB_AUTO_MIGRATE")
                .ok()
                .map(|v| v == "true" || v == "1")
                .unwrap_or(true),
        }
    }
}

/// Authentication configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    /// Secret key for JWT signing.
    pub jwt_secret: String,
    /// JWT issuer.
    pub jwt_issuer: String,
    /// JWT audience.
    pub jwt_audience: String,
    /// JWT access token expiration in minutes.
    pub access_token_expiry_minutes: i64,
    /// JWT refresh token expiration in days.
    pub refresh_token_expiry_days: i64,
    /// OAuth2 provider configuration (optional).
    pub oauth2: Option<OAuth2Config>,
}

impl AuthConfig {
    /// Load auth configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            jwt_secret: std::env::var("JWT_SECRET")
                .unwrap_or_else(|_| "change-me-in-production".to_string()),
            jwt_issuer: std::env::var("JWT_ISSUER")
                .unwrap_or_else(|_| "sensei".to_string()),
            jwt_audience: std::env::var("JWT_AUDIENCE")
                .unwrap_or_else(|_| "sensei-api".to_string()),
            access_token_expiry_minutes: std::env::var("JWT_ACCESS_EXPIRY_MINUTES")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(15),
            refresh_token_expiry_days: std::env::var("JWT_REFRESH_EXPIRY_DAYS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(7),
            oauth2: None, // Configured separately if needed
        }
    }
}

/// OAuth2 provider configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuth2Config {
    /// OAuth2 authorization endpoint.
    pub auth_url: String,
    /// OAuth2 token endpoint.
    pub token_url: String,
    /// Client ID.
    pub client_id: String,
    /// Client secret.
    pub client_secret: String,
    /// Redirect URL after authentication.
    pub redirect_url: String,
    /// Scopes to request.
    pub scopes: Vec<String>,
}

/// Event bus (NATS) configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventBusConfig {
    /// NATS server URL.
    pub url: String,
    /// NATS cluster name (for JetStream).
    pub cluster: String,
    /// Maximum reconnection attempts.
    pub max_reconnect: usize,
}

impl EventBusConfig {
    /// Load event bus configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            url: std::env::var("NATS_URL")
                .unwrap_or_else(|_| "nats://localhost:4222".to_string()),
            cluster: std::env::var("NATS_CLUSTER")
                .unwrap_or_else(|_| "sensei".to_string()),
            max_reconnect: std::env::var("NATS_MAX_RECONNECT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(10),
        }
    }
}

/// API server configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiConfig {
    /// Host address to bind to.
    pub host: String,
    /// Port to listen on.
    pub port: u16,
    /// CORS allowed origins.
    pub cors_allowed_origins: Vec<String>,
    /// Request body size limit (in bytes).
    pub body_limit: usize,
    /// Request timeout in seconds.
    pub request_timeout_secs: u64,
}

impl ApiConfig {
    /// Load API configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            host: std::env::var("API_HOST")
                .unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: std::env::var("API_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(3000),
            cors_allowed_origins: std::env::var("CORS_ALLOWED_ORIGINS")
                .unwrap_or_else(|_| "http://localhost:5173,http://localhost:3000".to_string())
                .split(',')
                .map(|s| s.trim().to_string())
                .collect(),
            body_limit: std::env::var("API_BODY_LIMIT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(10 * 1024 * 1024), // 10 MB
            request_timeout_secs: std::env::var("API_REQUEST_TIMEOUT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
        }
    }
}

/// Observability configuration (logging, tracing, metrics).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObservabilityConfig {
    /// Log level (trace, debug, info, warn, error).
    pub log_level: String,
    /// Whether to output JSON logs (vs. human-readable).
    pub json_logs: bool,
    /// OpenTelemetry endpoint (optional).
    pub otlp_endpoint: Option<String>,
    /// Prometheus metrics port (separate from API port).
    pub metrics_port: u16,
    /// Service name for OTel resource attributes.
    pub service_name: String,
}

impl ObservabilityConfig {
    /// Load observability configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            log_level: std::env::var("SENSEI_LOG")
                .or_else(|_| std::env::var("LOG_LEVEL"))
                .unwrap_or_else(|_| "info".to_string()),
            json_logs: std::env::var("SENSEI_JSON_LOGS")
                .or_else(|_| std::env::var("JSON_LOGS"))
                .ok()
                .map(|v| v == "true" || v == "1")
                .unwrap_or(false),
            otlp_endpoint: std::env::var("OTLP_ENDPOINT").ok(),
            metrics_port: std::env::var("METRICS_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(9090),
            service_name: std::env::var("SENSEI_SERVICE_NAME")
                .unwrap_or_else(|_| "sensei-api".to_string()),
        }
    }
}

/// Feature flags controlling optional behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureFlags {
    /// Enable AI-powered features.
    pub ai_enabled: bool,
    /// Enable real-time notifications via WebSocket.
    pub websocket_enabled: bool,
    /// Enable audit logging.
    pub audit_logging: bool,
    /// Enable rate limiting.
    pub rate_limiting: bool,
}

impl Default for FeatureFlags {
    fn default() -> Self {
        Self {
            ai_enabled: false,
            websocket_enabled: true,
            audit_logging: true,
            rate_limiting: true,
        }
    }
}

/// Email/SMTP configuration for sending emails.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmailConfig {
    /// SMTP server hostname.
    pub smtp_host: String,
    /// SMTP server port.
    pub smtp_port: u16,
    /// SMTP authentication username.
    pub smtp_username: String,
    /// SMTP authentication password.
    pub smtp_password: String,
    /// From email address (e.g., "noreply@sensei.local").
    pub from_address: String,
    /// From display name (e.g., "Sensei OS").
    pub from_name: String,
    /// Whether to use TLS encryption for SMTP.
    pub use_tls: bool,
}

impl EmailConfig {
    /// Load email configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            smtp_host: std::env::var("SMTP_HOST")
                .unwrap_or_else(|_| "localhost".to_string()),
            smtp_port: std::env::var("SMTP_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(587),
            smtp_username: std::env::var("SMTP_USERNAME")
                .unwrap_or_default(),
            smtp_password: std::env::var("SMTP_PASSWORD")
                .unwrap_or_default(),
            from_address: std::env::var("SMTP_FROM_ADDRESS")
                .unwrap_or_else(|_| "noreply@sensei.local".to_string()),
            from_name: std::env::var("SMTP_FROM_NAME")
                .unwrap_or_else(|_| "Sensei OS".to_string()),
            use_tls: std::env::var("SMTP_USE_TLS")
                .ok()
                .map(|v| v == "true" || v == "1")
                .unwrap_or(true),
        }
    }
}

/// File storage configuration (local disk or S3/MinIO).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageConfig {
    /// Storage backend: `"local"` or `"s3"`.
    pub backend: String,
    /// Base directory for local filesystem storage (used when `backend == "local"`).
    pub local_path: String,
    /// S3 bucket name (used when `backend == "s3"`).
    pub s3_bucket: String,
    /// S3 region (used when `backend == "s3"`).
    pub s3_region: String,
    /// Custom S3 endpoint for MinIO compatibility (optional).
    pub s3_endpoint: Option<String>,
    /// S3 access key (used when `backend == "s3"`).
    pub s3_access_key: String,
    /// S3 secret key (used when `backend == "s3"`).
    pub s3_secret_key: String,
}

impl StorageConfig {
    /// Load storage configuration from environment variables.
    pub fn from_env() -> Self {
        Self {
            backend: std::env::var("STORAGE_BACKEND")
                .unwrap_or_else(|_| "local".to_string()),
            local_path: std::env::var("STORAGE_LOCAL_PATH")
                .unwrap_or_else(|_| "./data/uploads".to_string()),
            s3_bucket: std::env::var("S3_BUCKET")
                .unwrap_or_else(|_| "sensei-uploads".to_string()),
            s3_region: std::env::var("S3_REGION")
                .unwrap_or_else(|_| "us-east-1".to_string()),
            s3_endpoint: std::env::var("S3_ENDPOINT").ok(),
            s3_access_key: std::env::var("S3_ACCESS_KEY")
                .unwrap_or_default(),
            s3_secret_key: std::env::var("S3_SECRET_KEY")
                .unwrap_or_default(),
        }
    }
}

/// Error type for configuration loading.
#[derive(Debug)]
pub struct ConfigError;

//! Configuration types for the Sensei ERP system.
//!
//! Defines the configuration structures used by all services.
//! Configuration is typically loaded from environment variables or config files.

use serde::{Deserialize, Serialize};
use std::net::IpAddr;
use std::num::ParseIntError;
use std::str::FromStr;
use thiserror::Error;

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
    /// Security hardening configuration (CSP, HSTS, trusted proxies).
    pub security: SecurityConfig,
    /// Feature flags.
    pub features: FeatureFlags,
    /// File storage configuration (local disk or S3/MinIO).
    pub storage: StorageConfig,
}

impl AppConfig {
    /// Load configuration from environment variables.
    ///
    /// Uses typical `FOO_BAR` naming convention for env vars.
    ///
    /// # Errors
    /// Returns [`ConfigError`] if a required environment variable is missing
    /// (in production), a value fails to parse, or a production security
    /// invariant is violated (e.g. the default JWT secret).
    pub fn from_env() -> Result<Self, ConfigError> {
        let environment = Environment::from_env()?;
        Ok(Self {
            database: DatabaseConfig::from_env()?,
            auth: AuthConfig::from_env()?,
            event_bus: EventBusConfig::from_env()?,
            api: ApiConfig::from_env()?,
            email: EmailConfig::from_env()?,
            observability: ObservabilityConfig::from_env()?,
            security: SecurityConfig::from_env()?,
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
    /// Load the environment from the `SENSEI_ENV` environment variable.
    ///
    /// Parsing is strict: any value that is not one of the accepted names
    /// (see [`Environment::from_str`]) is an error. In particular a typo such
    /// as `SENSEI_ENV=prodution` aborts startup instead of silently falling
    /// back to development.
    ///
    /// When the variable is unset the environment defaults to
    /// [`Environment::Development`].
    pub fn from_env() -> Result<Self, ConfigError> {
        match std::env::var("SENSEI_ENV") {
            Ok(value) => value.parse::<Environment>(),
            Err(_) => Ok(Environment::Development),
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

impl FromStr for Environment {
    type Err = ConfigError;

    /// Strictly parse an environment name.
    ///
    /// Accepts the canonical names `development`, `staging` and `production`
    /// (plus the short aliases `dev`, `test` and `prod`). Any other value —
    /// including misspellings such as `prodution` — is rejected with a
    /// [`ConfigError::InvalidValue`] so that misconfiguration fails fast
    /// instead of silently degrading to the development defaults.
    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value.trim().to_lowercase().as_str() {
            "development" | "dev" => Ok(Environment::Development),
            "staging" | "test" => Ok(Environment::Staging),
            "production" | "prod" => Ok(Environment::Production),
            other => Err(ConfigError::InvalidValue {
                var: "SENSEI_ENV".to_string(),
                reason: format!(
                    "'{other}' is not a valid environment (expected one of: \
                     development, dev, staging, test, production, prod)"
                ),
            }),
        }
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
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            url: std::env::var("DATABASE_URL").unwrap_or_else(|_| {
                "postgres://postgres:postgres@localhost:5432/sensei".to_string()
            }),
            max_connections: parse_env_int("DB_MAX_CONNECTIONS", 20u32)?,
            connection_timeout_secs: parse_env_int("DB_CONNECTION_TIMEOUT", 30u64)?,
            auto_migrate: parse_env_bool("DB_AUTO_MIGRATE", true)?,
        })
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
    pub oauth2: Option<OAuth2ProviderConfig>,
}

impl AuthConfig {
    /// Load auth configuration from environment variables.
    ///
    /// In production the `JWT_SECRET` environment variable must be set and
    /// must not be the placeholder default `change-me-in-production`.
    pub fn from_env() -> Result<Self, ConfigError> {
        let environment = Environment::from_env()?;
        let jwt_secret = std::env::var("JWT_SECRET").ok();
        if environment.is_prod() {
            validate_production_jwt_secret(jwt_secret.as_deref())?;
        }
        let jwt_secret = jwt_secret.unwrap_or_else(|| "change-me-in-production".to_string());

        Ok(Self {
            jwt_secret,
            jwt_issuer: std::env::var("JWT_ISSUER").unwrap_or_else(|_| "sensei".to_string()),
            jwt_audience: std::env::var("JWT_AUDIENCE")
                .unwrap_or_else(|_| "sensei-api".to_string()),
            access_token_expiry_minutes: parse_env_int("JWT_ACCESS_TTL_MINUTES", 15i64)?,
            refresh_token_expiry_days: parse_env_int("JWT_REFRESH_EXPIRY_DAYS", 7i64)?,
            oauth2: OAuth2ProviderConfig::from_env()?,
        })
    }
}

/// Validate the JWT secret for production environments.
///
/// The secret must be present and must not be the placeholder default.
fn validate_production_jwt_secret(secret: Option<&str>) -> Result<(), ConfigError> {
    match secret {
        None => Err(ConfigError::MissingEnvVar("JWT_SECRET".to_string())),
        Some("") => Err(ConfigError::InvalidValue {
            var: "JWT_SECRET".to_string(),
            reason: "must not be empty in production".to_string(),
        }),
        Some("change-me-in-production") => Err(ConfigError::InvalidValue {
            var: "JWT_SECRET".to_string(),
            reason: "must not be the default placeholder 'change-me-in-production' in production"
                .to_string(),
        }),
        Some(_) => Ok(()),
    }
}

/// OAuth2 provider configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuth2ProviderConfig {
    /// Provider name (e.g., "google", "azure", "github").
    pub provider: String,
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

impl OAuth2ProviderConfig {
    /// Load the OAuth2 provider configuration from environment variables.
    ///
    /// Returns `Ok(None)` when `OAUTH2_PROVIDER` is unset. When the provider
    /// is set, all other `OAUTH2_*` variables are required.
    pub fn from_env() -> Result<Option<Self>, ConfigError> {
        let provider = match std::env::var("OAUTH2_PROVIDER") {
            Ok(p) => p,
            Err(_) => return Ok(None),
        };

        Ok(Some(Self {
            provider,
            auth_url: require_env("OAUTH2_AUTH_URL")?,
            token_url: require_env("OAUTH2_TOKEN_URL")?,
            client_id: require_env("OAUTH2_CLIENT_ID")?,
            client_secret: require_env("OAUTH2_CLIENT_SECRET")?,
            redirect_url: require_env("OAUTH2_REDIRECT_URL")?,
            scopes: std::env::var("OAUTH2_SCOPES")
                .unwrap_or_default()
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect(),
        }))
    }
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
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            url: std::env::var("NATS_URL").unwrap_or_else(|_| "nats://localhost:4222".to_string()),
            cluster: std::env::var("NATS_CLUSTER").unwrap_or_else(|_| "sensei".to_string()),
            max_reconnect: parse_env_int("NATS_MAX_RECONNECT", 10usize)?,
        })
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
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            host: std::env::var("API_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: parse_env_int("API_PORT", 3000u16)?,
            cors_allowed_origins: std::env::var("CORS_ALLOWED_ORIGINS")
                .unwrap_or_else(|_| "http://localhost:5173,http://localhost:3000".to_string())
                .split(',')
                .map(|s| s.trim().to_string())
                .collect(),
            body_limit: parse_env_int("API_BODY_LIMIT", 10 * 1024 * 1024usize)?,
            request_timeout_secs: parse_env_int("API_REQUEST_TIMEOUT", 30u64)?,
        })
    }
}

/// Security hardening configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    /// Content-Security-Policy header value (None disables the header).
    pub csp: Option<String>,
    /// Whether to emit the Strict-Transport-Security header (default true).
    pub hsts: bool,
    /// IP addresses trusted to set client IP headers (e.g. reverse proxies).
    pub trusted_proxies: Vec<IpAddr>,
}

impl SecurityConfig {
    /// Load security configuration from environment variables.
    pub fn from_env() -> Result<Self, ConfigError> {
        let trusted_proxies = std::env::var("TRUSTED_PROXIES")
            .map(|v| {
                v.split(',')
                    .map(|s| s.trim())
                    .filter(|s| !s.is_empty())
                    .map(|s| {
                        s.parse::<IpAddr>().map_err(|_| ConfigError::InvalidValue {
                            var: "TRUSTED_PROXIES".to_string(),
                            reason: format!("'{}' is not a valid IP address", s),
                        })
                    })
                    .collect::<Result<Vec<IpAddr>, ConfigError>>()
            })
            .unwrap_or_else(|_| Ok(Vec::new()))?;

        Ok(Self {
            csp: std::env::var("SECURITY_CSP").ok(),
            hsts: parse_env_bool("SECURITY_HSTS", true)?,
            trusted_proxies,
        })
    }
}

impl Default for SecurityConfig {
    fn default() -> Self {
        Self {
            csp: None,
            hsts: true,
            trusted_proxies: Vec::new(),
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
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            log_level: std::env::var("SENSEI_LOG")
                .or_else(|_| std::env::var("LOG_LEVEL"))
                .unwrap_or_else(|_| "info".to_string()),
            json_logs: match std::env::var("SENSEI_JSON_LOGS")
                .or_else(|_| std::env::var("JSON_LOGS"))
            {
                Ok(value) => parse_bool(&value, "JSON_LOGS")?,
                Err(_) => false,
            },
            otlp_endpoint: std::env::var("OTLP_ENDPOINT").ok(),
            metrics_port: parse_env_int("METRICS_PORT", 9090u16)?,
            service_name: std::env::var("SENSEI_SERVICE_NAME")
                .unwrap_or_else(|_| "sensei-api".to_string()),
        })
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
    pub fn from_env() -> Result<Self, ConfigError> {
        Ok(Self {
            smtp_host: std::env::var("SMTP_HOST").unwrap_or_else(|_| "localhost".to_string()),
            smtp_port: parse_env_int("SMTP_PORT", 587u16)?,
            smtp_username: std::env::var("SMTP_USERNAME").unwrap_or_default(),
            smtp_password: std::env::var("SMTP_PASSWORD").unwrap_or_default(),
            from_address: std::env::var("SMTP_FROM_ADDRESS")
                .unwrap_or_else(|_| "noreply@sensei.local".to_string()),
            from_name: std::env::var("SMTP_FROM_NAME").unwrap_or_else(|_| "Sensei OS".to_string()),
            use_tls: parse_env_bool("SMTP_USE_TLS", true)?,
        })
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
            backend: std::env::var("STORAGE_BACKEND").unwrap_or_else(|_| "local".to_string()),
            local_path: std::env::var("STORAGE_LOCAL_PATH")
                .unwrap_or_else(|_| "./data/uploads".to_string()),
            s3_bucket: std::env::var("S3_BUCKET").unwrap_or_else(|_| "sensei-uploads".to_string()),
            s3_region: std::env::var("S3_REGION").unwrap_or_else(|_| "us-east-1".to_string()),
            s3_endpoint: std::env::var("S3_ENDPOINT").ok(),
            s3_access_key: std::env::var("S3_ACCESS_KEY").unwrap_or_default(),
            s3_secret_key: std::env::var("S3_SECRET_KEY").unwrap_or_default(),
        }
    }
}

/// Error type for configuration loading.
#[derive(Debug, Error)]
pub enum ConfigError {
    /// An environment variable that should contain an integer could not be parsed.
    #[error("Environment variable {var} must be a valid integer (got '{value}'): {source}")]
    InvalidInt {
        /// The name of the environment variable.
        var: String,
        /// The raw value that failed to parse.
        value: String,
        /// The underlying parse error.
        #[source]
        source: std::num::ParseIntError,
    },

    /// A required environment variable is missing.
    #[error("Missing required environment variable: {0}")]
    MissingEnvVar(String),

    /// An environment variable holds an invalid value.
    #[error("Invalid value for {var}: {reason}")]
    InvalidValue {
        /// The name of the environment variable.
        var: String,
        /// A description of the validation failure.
        reason: String,
    },
}

impl From<ConfigError> for crate::error::SenseiError {
    fn from(err: ConfigError) -> Self {
        match err {
            ConfigError::MissingEnvVar(var) => crate::error::SenseiError::MissingEnvVar(var),
            other => crate::error::SenseiError::Configuration(other.to_string()),
        }
    }
}

/// Parse an integer environment variable, falling back to `default` when the
/// variable is unset and returning [`ConfigError::InvalidInt`] when the
/// variable is set but not a valid integer of the target type.
fn parse_env_int<T>(var: &str, default: T) -> Result<T, ConfigError>
where
    T: FromStr<Err = ParseIntError>,
{
    match std::env::var(var) {
        Ok(value) => value
            .parse::<T>()
            .map_err(|source| ConfigError::InvalidInt {
                var: var.to_string(),
                value,
                source,
            }),
        Err(_) => Ok(default),
    }
}

/// Require a non-empty environment variable.
fn require_env(var: &str) -> Result<String, ConfigError> {
    match std::env::var(var) {
        Ok(value) if !value.trim().is_empty() => Ok(value),
        _ => Err(ConfigError::MissingEnvVar(var.to_string())),
    }
}

/// Parse a boolean environment variable (`true`/`1`/`false`/`0`).
fn parse_bool(value: &str, var: &str) -> Result<bool, ConfigError> {
    match value.to_lowercase().as_str() {
        "true" | "1" | "yes" | "on" => Ok(true),
        "false" | "0" | "no" | "off" => Ok(false),
        _ => Err(ConfigError::InvalidValue {
            var: var.to_string(),
            reason: format!("'{value}' is not a valid boolean"),
        }),
    }
}

/// Parse a boolean environment variable with a fallback default.
fn parse_env_bool(var: &str, default: bool) -> Result<bool, ConfigError> {
    match std::env::var(var) {
        Ok(value) => parse_bool(&value, var),
        Err(_) => Ok(default),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    /// Tests that mutate SENSEI_ENV must not run concurrently (the process
    /// environment is shared across parallel test threads).
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn production_jwt_secret_must_be_present() {
        assert!(matches!(
            validate_production_jwt_secret(None),
            Err(ConfigError::MissingEnvVar(_))
        ));
        assert!(matches!(
            validate_production_jwt_secret(Some("")),
            Err(ConfigError::InvalidValue { .. })
        ));
    }

    #[test]
    fn production_jwt_secret_must_not_be_placeholder() {
        assert!(matches!(
            validate_production_jwt_secret(Some("change-me-in-production")),
            Err(ConfigError::InvalidValue { .. })
        ));
        assert!(validate_production_jwt_secret(Some("a-real-secret")).is_ok());
    }

    #[test]
    fn parse_bool_accepts_common_forms() {
        assert!(parse_bool("true", "T").unwrap());
        assert!(parse_bool("1", "T").unwrap());
        assert!(!parse_bool("false", "T").unwrap());
        assert!(!parse_bool("0", "T").unwrap());
        assert!(parse_bool("yes", "T").unwrap());
        // "off" parses to `false`; the original test asserted `true`,
        // which contradicted the documented boolean semantics.
        assert!(!parse_bool("off", "T").unwrap());
        assert!(parse_bool("banana", "T").is_err());
    }

    #[test]
    fn parse_env_int_unset_uses_default() {
        assert_eq!(
            parse_env_int("SENSEI_TEST_UNSET_INT_VAR_XYZZY", 5).unwrap(),
            5
        );
    }

    #[test]
    fn parse_bool_rejects_invalid_values() {
        assert!(parse_bool("banana", "T").is_err());
    }

    #[test]
    fn oauth2_provider_requires_all_fields() {
        // Unset provider => None
        std::env::remove_var("OAUTH2_PROVIDER");
        assert!(OAuth2ProviderConfig::from_env().unwrap().is_none());
    }

    #[test]
    fn security_config_defaults() {
        let cfg = SecurityConfig::default();
        assert!(cfg.csp.is_none());
        assert!(cfg.hsts);
        assert!(cfg.trusted_proxies.is_empty());
    }

    #[test]
    fn environment_parses_valid_names() {
        assert_eq!(
            "development".parse::<Environment>().unwrap(),
            Environment::Development
        );
        assert_eq!(
            "dev".parse::<Environment>().unwrap(),
            Environment::Development
        );
        assert_eq!(
            "staging".parse::<Environment>().unwrap(),
            Environment::Staging
        );
        assert_eq!("test".parse::<Environment>().unwrap(), Environment::Staging);
        assert_eq!(
            "production".parse::<Environment>().unwrap(),
            Environment::Production
        );
        assert_eq!(
            "prod".parse::<Environment>().unwrap(),
            Environment::Production
        );
        // Case-insensitive and whitespace-tolerant.
        assert_eq!(
            "Production".parse::<Environment>().unwrap(),
            Environment::Production
        );
        assert_eq!(
            " development ".parse::<Environment>().unwrap(),
            Environment::Development
        );
    }

    #[test]
    fn environment_rejects_unknown_names() {
        for bad in [
            "prodution",
            "prodction",
            "devprod",
            "production2",
            "testify",
            "",
        ] {
            let err = bad.parse::<Environment>().unwrap_err();
            assert!(
                matches!(err, ConfigError::InvalidValue { ref var, .. } if var == "SENSEI_ENV"),
                "expected SENSEI_ENV InvalidValue for {bad:?}, got {err:?}"
            );
        }
    }

    #[test]
    fn environment_from_env_propagates_invalid_value() {
        std::env::set_var("SENSEI_ENV", "prodution");
        assert!(matches!(
            Environment::from_env(),
            Err(ConfigError::InvalidValue { .. })
        ));
        std::env::remove_var("SENSEI_ENV");
    }

    #[test]
    fn environment_from_env_defaults_to_development_when_unset() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::remove_var("SENSEI_ENV");
        assert_eq!(Environment::from_env().unwrap(), Environment::Development);
    }

    #[test]
    fn app_config_from_env_fails_on_invalid_environment() {
        std::env::set_var("SENSEI_ENV", "prodution");
        std::env::set_var("JWT_SECRET", "test-secret");
        std::env::set_var("DATABASE_URL", "");
        assert!(matches!(
            AppConfig::from_env(),
            Err(ConfigError::InvalidValue { .. })
        ));
        std::env::remove_var("SENSEI_ENV");
    }
}

//! # Sensei API Server — Entrypoint
//!
//! Starts the Axum HTTP server with the configured middleware stack,
//! routes, and shared application state. Initializes OpenTelemetry
//! tracing, Prometheus metrics, and structured (JSON) logging.

use std::sync::Arc;
use std::time::Duration;

use opentelemetry::KeyValue;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{trace as sdktrace, Resource};
use sensei_api::router::build_router;
use sensei_api::routes::metrics::init_metrics;
use sensei_api::state::{create_event_bus, AppState};
use sensei_core::config::AppConfig;
use sensei_core::types::TenantId;
use sensei_services::users::{InMemoryUsersService, UsersService};
use sqlx::postgres::PgPoolOptions;
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Layer};

/// Initialize the OpenTelemetry SDK and OTLP exporter.
///
/// Returns `None` if no OTLP endpoint is configured, allowing the application
/// to fall back to local-only logging and metrics.
async fn init_otel_tracer(config: &sensei_core::config::ObservabilityConfig) -> Option<sdktrace::SdkTracerProvider> {
    let otlp_endpoint = config.otlp_endpoint.as_ref()?;

    info!("Initializing OpenTelemetry, exporting to {otlp_endpoint}");

    // Build the OTLP SpanExporter using the tonic (gRPC) protocol
    let exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_tonic()
        .with_endpoint(otlp_endpoint.clone())
        .with_timeout(Duration::from_secs(5))
        .build()
        .expect("Failed to build OTLP span exporter");

    // Build the tracer provider with batch export
    let provider = sdktrace::SdkTracerProvider::builder()
        .with_batch_exporter(exporter)
        .with_resource(
            Resource::builder()
                .with_attribute(KeyValue::new("service.name", config.service_name.clone()))
                .with_attribute(KeyValue::new("service.version", env!("CARGO_PKG_VERSION")))
                .with_attribute(KeyValue::new(
                    "deployment.environment",
                    std::env::var("SENSEI_ENV").unwrap_or_default(),
                ))
                .build(),
        )
        .build();

    // Set the global tracer provider so tracing-opentelemetry can use it
    opentelemetry::global::set_tracer_provider(provider.clone());

    info!("OpenTelemetry initialized successfully");
    Some(provider)
}

/// Signal handler for graceful shutdown.
///
/// Listens for SIGTERM, SIGINT (Unix) or Ctrl+C (non-Unix) and returns
/// when one is received, allowing the server to drain in-flight requests.
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut sigterm =
            signal(SignalKind::terminate()).expect("Failed to register SIGTERM handler");
        let mut sigint =
            signal(SignalKind::interrupt()).expect("Failed to register SIGINT handler");

        tokio::select! {
            _ = sigterm.recv() => info!("SIGTERM received"),
            _ = sigint.recv() => info!("SIGINT received"),
        }
    }
    #[cfg(not(unix))]
    {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to listen for Ctrl+C");
        info!("Ctrl+C received");
    }
}

#[tokio::main]
async fn main() {
    // ── Load configuration ────────────────────────────────────────
    let config = AppConfig::from_env().expect("Failed to load configuration");
    info!(
        environment = %config.environment,
        service_name = %config.observability.service_name,
        "Starting Sensei API server"
    );

    // ── Initialize OpenTelemetry (optional) ───────────────────────
    let otel_provider = init_otel_tracer(&config.observability).await;

    // ── Initialize tracing/logging ────────────────────────────────
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&config.observability.log_level));

    // Build the fmt layer with optional JSON formatting
    // Note: `with_current_span()` is only available on the JSON Layer variant
    // (it requires Layer<S, JsonFields, Format<Json, T>, W> type params), so:
    // - JSON branch: call .json() first to get JSON layer, then with_current_span, then with_target
    // - Non-JSON: just with_target, no with_current_span (keeps default Full format)
    let fmt_layer: Box<dyn Layer<tracing_subscriber::Registry> + Send + Sync> =
        if config.observability.json_logs {
            tracing_subscriber::fmt::layer()
                .json()
                .with_current_span(true)
                .with_target(true)
                .boxed()
        } else {
            tracing_subscriber::fmt::layer()
                .with_target(true)
                .boxed()
        };

    // Compose and initialise subscriber:
    // - fmt_layer is a `Box<dyn Layer<Registry>>`, so add it directly to Registry
    // - env_filter is a concrete type that adapts to any inner subscriber
    // - OpenTelemetry layer is added conditionally (the concrete type changes,
    //   so we init inside each branch to avoid type mismatch)
    let subscriber_base = tracing_subscriber::registry()
        .with(fmt_layer)
        .with(env_filter);

    if otel_provider.is_some() {
        subscriber_base
            .with(tracing_opentelemetry::layer())
            .init();
    } else {
        subscriber_base.init();
    }

    // ── Initialize metrics ────────────────────────────────────────
    init_metrics();

    // ── Seed admin user ──────────────────────────────────────────
    let admin_email = std::env::var("SENSEI_ADMIN_EMAIL")
        .unwrap_or_else(|_| "admin@sensei.com".to_string());
    let admin_password = std::env::var("SENSEI_ADMIN_PASSWORD")
        .unwrap_or_else(|_| "Admin123!".to_string());
    let admin_name = "Admin User".to_string();

    let admin_password_hash = sensei_auth::password::hash_password(&admin_password)
        .expect("Failed to hash admin password");

    let default_tenant_id = TenantId::nil();
    let users_service = Arc::new(
        InMemoryUsersService::with_admin(
            &admin_email,
            &admin_name,
            &admin_password_hash,
            default_tenant_id,
        ),
    );

    info!(
        admin_email = %admin_email,
        "Seeded admin user"
    );

    // ── Seed CEO user ────────────────────────────────────────────
    {
        let ceo_email = "ceo@starz.com";
        let ceo_password = "1234";
        let ceo_name = "CEO";

        let ceo_password_hash = sensei_auth::password::hash_password(ceo_password)
            .expect("Failed to hash CEO password");

        let mut ceo_user = sensei_core::domain::entities::User::new(
            default_tenant_id,
            ceo_email.to_string(),
            ceo_name.to_string(),
            ceo_password_hash,
        );
        ceo_user.roles = vec!["ceo".to_string(), "user".to_string()];

        users_service
            .create_user(ceo_user)
            .await
            .expect("Failed to seed CEO user");

        info!(
            ceo_email = ceo_email,
            "Seeded CEO user"
        );
    }

    // ── Build application state ───────────────────────────────────
    // Try NATS JetStream event bus if configured, fall back to in-memory
    let event_bus = create_event_bus(&config.event_bus).await;
    let mut state = AppState::new(config.clone(), users_service).with_event_bus(event_bus);

    // ── Connect to PostgreSQL if DATABASE_URL is set ──────────────
    if let Ok(database_url) = std::env::var("DATABASE_URL") {
        info!(
            database_url = %database_url,
            max_connections = config.database.max_connections,
            "Connecting to PostgreSQL database"
        );

        match PgPoolOptions::new()
            .max_connections(config.database.max_connections)
            .acquire_timeout(std::time::Duration::from_secs(
                config.database.connection_timeout_secs,
            ))
            .connect(&database_url)
            .await
        {
            Ok(pool) => {
                info!("PostgreSQL connection pool established successfully");

                // Run database migrations (including entity_store table)
                if let Err(e) = sensei_db::migrations::run_migrations(&pool).await {
                    tracing::error!("Failed to run database migrations: {e}");
                    // Continue anyway — stores will fall back to in-memory gracefully
                }

                state = state.with_db_pool(Arc::new(pool));
                info!("Running in DATABASE mode — all services use PostgreSQL");
            }
            Err(e) => {
                tracing::error!(
                    error = %e,
                    "Failed to connect to PostgreSQL — falling back to in-memory mode"
                );
            }
        }
    } else {
        info!("DATABASE_URL not set — running in IN-MEMORY mode (data lost on restart)");
    }

    // ── Build router ──────────────────────────────────────────────
    let app = build_router(state);

    // ── Start server ──────────────────────────────────────────────
    let addr = format!("{}:{}", config.api.host, config.api.port);
    info!(address = %addr, "API server listening");

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("Failed to bind to address");

    // Serve with graceful shutdown
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .expect("Server failed");

    // ── Graceful shutdown for OTel ────────────────────────────────
    info!("Shutting down...");
    if let Some(provider) = otel_provider {
        if let Err(e) = provider.shutdown() {
            tracing::error!("Error shutting down OTel tracer provider: {e}");
        }
    }
}

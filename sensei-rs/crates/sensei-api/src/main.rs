//! # Sensei API Server — Entrypoint
//!
//! Starts the Axum HTTP server with the configured middleware stack,
//! routes, and shared application state. Initializes OpenTelemetry
//! tracing, Prometheus metrics, and structured (JSON) logging.
//!
//! # Fail-fast rules (production)
//!
//! * `AppConfig::from_env()` errors abort startup with a clear message.
//! * A missing `DATABASE_URL`, a failed connection, or failed migrations
//!   abort startup instead of silently degrading to in-memory mode.
//! * The CEO seed account requires an explicit non-default password.
//!
//! In development, database failures are logged and the server continues
//! with in-memory stores.

use std::sync::Arc;
use std::time::Duration;

use opentelemetry::KeyValue;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{trace as sdktrace, Resource};
use sensei_api::router::build_router;
use sensei_api::routes::metrics::init_metrics;
use sensei_api::state::{create_event_bus, AppState};
use sensei_core::config::AppConfig;
use sensei_core::domain::entities::{Tenant, User};
use sensei_core::error::SenseiError;
use sensei_core::types::{now, TenantId};
use sensei_services::users::{InMemoryUsersService, UsersService};
use sqlx::postgres::PgPoolOptions;
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Layer};

/// Initialize the OpenTelemetry SDK and OTLP exporter.
///
/// Returns `None` if no OTLP endpoint is configured, allowing the application
/// to fall back to local-only logging and metrics.
async fn init_otel_tracer(
    config: &sensei_core::config::ObservabilityConfig,
) -> Option<sdktrace::SdkTracerProvider> {
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

/// The bootstrap tenant for seeded admin/CEO accounts.
///
/// `Uuid::nil()` matches the legacy in-memory seeding behavior; in database
/// mode a `tenants` row is ensured first because the `users.tenant_id`
/// column references it.
fn bootstrap_tenant_id() -> TenantId {
    TenantId::nil()
}

/// Ensure the bootstrap tenant exists (the `users` table has an FK on
/// `tenants(id)`), creating it when missing.
async fn ensure_bootstrap_tenant(state: &AppState) {
    let tenant_id = bootstrap_tenant_id();
    match state.tenants_service.get_tenant(tenant_id).await {
        Ok(_) => {}
        Err(SenseiError::NotFound(_)) => {
            let timestamp = now();
            let tenant = Tenant {
                id: tenant_id,
                name: "Sensei".to_string(),
                slug: "sensei".to_string(),
                is_active: true,
                features: Vec::new(),
                created_at: timestamp,
                updated_at: timestamp,
            };
            if let Err(e) = state.tenants_service.create_tenant(tenant).await {
                tracing::error!(
                    error = %e,
                    "Failed to create bootstrap tenant; seeding admin/CEO users may fail"
                );
            }
        }
        Err(e) => {
            tracing::error!(error = %e, "Failed to look up bootstrap tenant");
        }
    }
}

/// Seed a user through the users service if it does not exist yet.
///
/// Idempotent: `find_by_email` → create only when missing. In production a
/// failure to seed a *required* account aborts startup.
async fn seed_user(
    state: &AppState,
    email: &str,
    password: &str,
    name: &str,
    roles: &[&str],
    required_in_prod: bool,
) -> Result<User, SenseiError> {
    match state.users_service.find_by_email(email).await {
        Ok(existing) => {
            info!(email, "Seed account already exists");
            Ok(existing)
        }
        Err(SenseiError::NotFound(_)) => {
            let password_hash = sensei_auth::password::hash_password(password).map_err(|e| {
                SenseiError::Internal(format!("Failed to hash seed password for {email}: {e}"))
            })?;
            let mut user = User::new(
                bootstrap_tenant_id(),
                email.to_string(),
                name.to_string(),
                password_hash,
            );
            user.roles = roles.iter().map(|r| r.to_string()).collect();

            match state.users_service.create_user(user).await {
                Ok(created) => {
                    info!(email, roles = ?roles, "Seeded user");
                    Ok(created)
                }
                Err(e) => {
                    tracing::error!(email, error = %e, "Failed to seed user");
                    if required_in_prod {
                        return Err(e);
                    }
                    Err(e)
                }
            }
        }
        Err(e) => {
            tracing::error!(email, error = %e, "Failed to look up seed user");
            if required_in_prod {
                return Err(e);
            }
            Err(e)
        }
    }
}

/// Seed the admin and CEO bootstrap accounts.
///
/// Runs *after* `with_db_pool`, so in database mode the accounts are seeded
/// through the DB-backed users service.
async fn seed_bootstrap_users(state: &AppState) {
    ensure_bootstrap_tenant(state).await;

    let admin_email =
        std::env::var("SENSEI_ADMIN_EMAIL").unwrap_or_else(|_| "admin@sensei.com".to_string());
    let admin_password = match std::env::var("SENSEI_ADMIN_PASSWORD") {
        Ok(v) if !v.is_empty() => v,
        _ => {
            if state.config.environment.is_prod() {
                tracing::error!(
                    "SENSEI_ADMIN_PASSWORD must be set in production (admin seed account)"
                );
                std::process::exit(1);
            }
            let generated = format!("dev-{}", uuid::Uuid::new_v4());
            println!("ADMIN DEV PASSWORD (first boot only): {generated}");
            generated
        }
    };
    let admin_name =
        std::env::var("SENSEI_ADMIN_NAME").unwrap_or_else(|_| "Admin User".to_string());

    if let Err(e) = seed_user(
        state,
        &admin_email,
        &admin_password,
        &admin_name,
        &[
            "user",
            "tenant_admin",
            "platform_admin",
            "finance_manager",
            "hr_manager",
            "purchasing_manager",
            "inventory_manager",
            "sales_manager",
            "quality_manager",
            "production_manager",
        ],
        false,
    )
    .await
    {
        tracing::warn!(error = %e, "Admin seed failed (continuing)");
    }

    // ── CEO seed account ────────────────────────────────────────────
    let ceo_email =
        std::env::var("SENSEI_CEO_EMAIL").unwrap_or_else(|_| "ceo@starz.com".to_string());
    let ceo_password = match std::env::var("SENSEI_CEO_PASSWORD") {
        Ok(v) if !v.is_empty() => v,
        _ => {
            if state.config.environment.is_prod() {
                tracing::error!("SENSEI_CEO_PASSWORD must be set in production (CEO seed account)");
                std::process::exit(1);
            }
            let generated = format!("dev-{}", uuid::Uuid::new_v4());
            println!("CEO DEV PASSWORD (first boot only): {generated}");
            generated
        }
    };

    if let Err(e) = seed_user(
        state,
        &ceo_email,
        &ceo_password,
        "CEO",
        // The CEO is the break-glass operational identity: functional
        // manager roles + platform administration. The legacy "ceo" role is
        // NOT defined by the authorization model, so it is never seeded.
        &[
            "user",
            "tenant_admin",
            "platform_admin",
            "finance_manager",
            "hr_manager",
            "purchasing_manager",
            "inventory_manager",
            "sales_manager",
            "quality_manager",
            "production_manager",
        ],
        true,
    )
    .await
    {
        tracing::error!(error = %e, "Failed to seed required CEO account");
        std::process::exit(1);
    }
}

/// Extract the host from a postgres URL WITHOUT exposing credentials.
fn redact_url_host(url: &str) -> Option<String> {
    let after_scheme = url.split("://").nth(1)?;
    let host_part = after_scheme.rsplit('@').next_back()?;
    let host_port = host_part.split('/').next()?;
    let host = host_port.split(':').next()?;
    if host.is_empty() {
        None
    } else {
        Some(host.to_string())
    }
}

/// Extract the database name from a postgres URL.
fn redact_url_db(url: &str) -> Option<String> {
    let after_scheme = url.split("://").nth(1)?;
    let path = after_scheme.split('/').nth(1)?;
    let db = path.split('?').next()?;
    if db.is_empty() {
        None
    } else {
        Some(db.to_string())
    }
}

#[tokio::main]
async fn main() {
    // ── Load configuration ────────────────────────────────────────
    let config = match AppConfig::from_env() {
        Ok(config) => config,
        Err(e) => {
            eprintln!("FATAL: Failed to load configuration: {e}");
            std::process::exit(1);
        }
    };
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
    let fmt_layer: Box<dyn Layer<tracing_subscriber::Registry> + Send + Sync> =
        if config.observability.json_logs {
            tracing_subscriber::fmt::layer()
                .json()
                .with_current_span(true)
                .with_target(true)
                .boxed()
        } else {
            tracing_subscriber::fmt::layer().with_target(true).boxed()
        };

    let subscriber_base = tracing_subscriber::registry()
        .with(fmt_layer)
        .with(env_filter);

    if otel_provider.is_some() {
        subscriber_base.with(tracing_opentelemetry::layer()).init();
    } else {
        subscriber_base.init();
    }

    // ── Initialize metrics ────────────────────────────────────────
    init_metrics();

    // ── Build application state (in-memory users; seeded below) ───
    let users_service: Arc<dyn UsersService> =
        Arc::new(InMemoryUsersService::new()) as Arc<dyn UsersService>;

    // NATS JetStream event bus (required in production; in-memory is an
    // explicit development mode when NATS_URL is empty).
    let event_bus = create_event_bus(&config.event_bus, &config.environment).await;
    let mut state = AppState::new(config.clone(), users_service).with_event_bus(event_bus);
    // Cross-replica EntityStore cache invalidation: every replica evicts
    // changed rows immediately after ANY replica commits a write.
    state.attach_entity_store_buses(state.event_bus.clone());
    // Install the shared authorization service: every require_permission
    // decision resolves through THIS instance (DB-loaded custom roles).
    sensei_auth::rbac::set_authorization_service(state.rbac_service.clone());

    // Eagerly (and with supervision) subscribe the realtime fanout BEFORE
    // the HTTP listener starts: a replica must receive cross-replica WS/SSE
    // broadcasts from the very first request, not only after it has
    // broadcast something itself.
    {
        let ws_manager = state.ws_manager.clone();
        tokio::spawn(async move {
            ws_manager.start_fanout_subscription().await;
        });
    }

    // ── Connect to PostgreSQL if DATABASE_URL is set ──────────────
    let database_url = std::env::var("DATABASE_URL").unwrap_or_default();
    if database_url.is_empty() {
        if config.environment.is_prod() {
            tracing::error!(
                "DATABASE_URL is not set — refusing to start in production without a database"
            );
            std::process::exit(1);
        }
        info!("DATABASE_URL not set — running in IN-MEMORY mode (data lost on restart)");
    } else {
        info!(
            database_host =
                redact_url_host(&database_url).unwrap_or_else(|| "(unknown)".to_string()),
            database_name = redact_url_db(&database_url).unwrap_or_else(|| "(unknown)".to_string()),
            max_connections = config.database.max_connections,
            "Connecting to PostgreSQL database"
        );

        let connect_result = PgPoolOptions::new()
            .max_connections(config.database.max_connections)
            .acquire_timeout(std::time::Duration::from_secs(
                config.database.connection_timeout_secs,
            ))
            .connect(&database_url)
            .await;

        let pool = match connect_result {
            Ok(pool) => {
                info!("PostgreSQL connection pool established successfully");
                pool
            }
            Err(e) => {
                if config.environment.is_prod() {
                    tracing::error!(error = %e, "Failed to connect to PostgreSQL in production");
                    std::process::exit(1);
                }
                tracing::error!(
                    error = %e,
                    "Failed to connect to PostgreSQL — falling back to in-memory mode"
                );
                seed_bootstrap_users(&state).await;
                build_and_serve(state, otel_provider, config).await;
                return;
            }
        };

        // Run database migrations (including entity_store table)
        if let Err(e) = sensei_db::migrations::run_migrations(&pool).await {
            if config.environment.is_prod() {
                tracing::error!(
                    error = %e,
                    "Failed to run database migrations in production"
                );
                std::process::exit(1);
            }
            tracing::error!(
                error = %e,
                "Failed to run database migrations — falling back to in-memory mode"
            );
            seed_bootstrap_users(&state).await;
            build_and_serve(state, otel_provider, config).await;
            return;
        }

        state = state.with_db_pool(Arc::new(pool));
        info!("Running in DATABASE mode — all services use PostgreSQL");
    }

    // ── Seed admin & CEO bootstrap accounts (DB-backed in DB mode) ──
    seed_bootstrap_users(&state).await;

    // ── Build router & serve ──────────────────────────────────────
    build_and_serve(state, otel_provider, config).await;
}

/// Build the router, bind the listener, and serve with graceful shutdown.
///
/// `ConnectInfo` is enabled so middleware can see the immediate peer
/// address (used for trusted-proxy decisions in session binding and secure
/// headers).
async fn build_and_serve(
    state: AppState,
    otel_provider: Option<sdktrace::SdkTracerProvider>,
    config: AppConfig,
) {
    // ── Notification-trigger worker ───────────────────────────────────
    // Subscribes to all domain events and fires matching notification
    // triggers. With an in-memory bus (no NATS URL) it only sees events
    // published inside this process — still useful, but worth logging.
    if config.event_bus.url.is_empty() {
        info!(
            "Notification-trigger worker started on in-memory event bus \
             (only in-process events will be processed)"
        );
    }
    sensei_api::services::notification_trigger_worker::spawn(state.clone());

    // ── Build router ──────────────────────────────────────────────
    let app = build_router(state.clone());

    // ── Start server ──────────────────────────────────────────────
    let addr = format!("{}:{}", config.api.host, config.api.port);
    info!(address = %addr, "API server listening");

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .unwrap_or_else(|e| {
            eprintln!("FATAL: Failed to bind to {addr}: {e}");
            std::process::exit(1);
        });

    // Serve with graceful shutdown and connect-info (peer IP) support.
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<std::net::SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown_signal())
    .await
    .unwrap_or_else(|e| {
        eprintln!("FATAL: Server error: {e}");
        std::process::exit(1);
    });

    // ── Graceful shutdown ─────────────────────────────────────────
    info!("Shutting down...");

    // Disconnect the event bus (NATS flush/disconnect, in-memory clear).
    if let Err(e) = state.event_bus.disconnect().await {
        tracing::error!(error = %e, "Error disconnecting event bus");
    } else {
        info!("Event bus disconnected");
    }

    if let Some(provider) = otel_provider {
        if let Err(e) = provider.shutdown() {
            tracing::error!("Error shutting down OTel tracer provider: {e}");
        }
    }
}

//! # Sensei API Server — Entrypoint
//!
//! Starts the Axum HTTP server with the configured middleware stack,
//! routes, and shared application state. Initializes OpenTelemetry
//! tracing, Prometheus metrics, and structured (JSON) logging.
//!
//! # Fail-fast rules (production)
//!
//! * `AppConfig::from_env()` errors abort startup with a clear message.
//! * A missing `DATABASE_URL` or a failed connection abort startup instead
//!   of silently degrading to in-memory mode.
//! * The CEO seed account requires an explicit non-default password.
//!
//! # Bootstrap contract (thirtieth-first audit item 15)
//!
//! All bootstrap/seeding logic lives in `sensei_api::bootstrap`
//! (extracted module): it takes a cross-replica `pg_advisory_xact_lock`
//! inside one open transaction around the whole seed section, and every
//! required bootstrap failure (tenant ensure, admin/CEO creation, the
//! lock/commit itself) PROPAGATES — `run_bootstrap_seeding` aborts
//! startup with a clear message instead of logging-and-continuing.
//!
//! # Migration contract (twenty-fourth audit P0 — migration-owner split)
//!
//! The API process connects as the NON-OWNER `sensei_app` and does NOT run
//! DDL at startup. Schema changes are applied by the dedicated `migrate`
//! bootstrap (`--migrate-only` or `SENSEI_MIGRATE=1`), which runs the
//! chain as `sensei_migrator` and exits 0; compose gates the API on that
//! service completing successfully. `DB_AUTO_MIGRATE=true` (explicitly
//! set) keeps the legacy opt-in for local/dev bootstraps.
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

/// True when the CLI/env explicitly asks this process to run the migration
/// chain (`--migrate-only` or `SENSEI_MIGRATE=1`). The production bootstrap
/// runs the chain through the dedicated `migrate` container as the
/// migration-owner role (sensei_migrator); the API server itself connects
/// as the non-owner sensei_app and NEVER runs DDL unless an explicit
/// request opts in (twenty-fourth audit P0 — migration-owner split).
fn migrate_only_requested() -> bool {
    std::env::args().any(|arg| arg == "--migrate-only") || env_flag_enabled("SENSEI_MIGRATE")
}

/// True when `DB_AUTO_MIGRATE` is EXPLICITLY set to an enabled value.
///
/// `.env.example` documents `DB_AUTO_MIGRATE=true` as the legacy opt-in for
/// bootstraps that still run the chain from the API process (local/dev).
/// The default when the variable is UNSET is NO migration at startup: the
/// production contract is a dedicated migration-owner bootstrap, and an
/// accidental DDL attempt from the app role would fail loudly.
fn auto_migrate_opted_in() -> bool {
    env_flag_enabled("DB_AUTO_MIGRATE")
}

fn env_flag_enabled(var: &str) -> bool {
    std::env::var(var).is_ok_and(|value| {
        matches!(
            value.trim().to_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        )
    })
}

/// Run the bootstrap seeding (sensei_api::bootstrap) and abort startup on
/// ANY failure.
///
/// Required bootstrap failures — tenant ensure, admin/CEO account
/// creation, the advisory-lock transaction itself — are NEVER
/// logged-and-swallowed (thirtieth-first audit item 15): the process
/// exits with a clear message so a replica that failed to bootstrap never
/// starts serving.
async fn run_bootstrap_seeding(state: &AppState) {
    if let Err(e) = sensei_api::bootstrap::seed_bootstrap_users(state).await {
        tracing::error!(
            error = %e,
            "FATAL: bootstrap seeding failed (bootstrap tenant ensure or \
             required admin/CEO account creation) — aborting startup"
        );
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

    // ── Explicit migration-owner bootstrap (`--migrate-only` or
    //    SENSEI_MIGRATE=1) ────────────────────────────────────────────
    // Production runs the chain from the dedicated `migrate` container as
    // sensei_migrator (the object owner) and exits 0 — the API process
    // must not start serving, seeding, or any other service machinery.
    // This path exits the process, so it never reaches the code below.
    if migrate_only_requested() {
        run_migrations_only(&config).await;
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
    // NO process-global authorization snapshot is installed here
    // (twenty-ninth audit Wave A): production authorization resolves LIVE
    // state per authenticated request — the current user row plus the
    // static role map and the tenant's custom `roles` rows — so a role
    // change, deactivation or deletion can never be outlived by a
    // startup-time global. (set_authorization_service stays available in
    // sensei-auth for tests/embedded runtimes; the startup path must not
    // call it.)

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
                run_bootstrap_seeding(&state).await;
                build_and_serve(state, otel_provider, config).await;
                return;
            }
        };

        // Startup migrations are NOT the default (twenty-fourth audit P0 —
        // migration-owner split): the production chain runs from the
        // dedicated `migrate` container as sensei_migrator. The API starts
        // as the non-owner sensei_app and never DDLs unless an explicit
        // DB_AUTO_MIGRATE=true opt-in (legacy bootstrap) requests it.
        if auto_migrate_opted_in() {
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
                run_bootstrap_seeding(&state).await;
                build_and_serve(state, otel_provider, config).await;
                return;
            }
        } else {
            info!("Auto-migration disabled on startup (run --migrate-only as the migration owner to apply schema changes)");
        }

        state = state.with_db_pool(Arc::new(pool));
        info!("Running in DATABASE mode — all services use PostgreSQL");
    }

    // ── Seed bootstrap tenant + admin/CEO accounts ───────────────────
    // DB-backed in DB mode (the module opens the advisory-lock
    // transaction); in-memory when no pool is configured. Any required
    // bootstrap failure aborts startup (never logged-and-swallowed).
    run_bootstrap_seeding(&state).await;

    // ── Build router & serve ──────────────────────────────────────
    build_and_serve(state, otel_provider, config).await;
}

/// Apply the migration chain against `DATABASE_URL` and exit the process.
///
/// The production bootstrap contract (twenty-fourth audit P0): the
/// dedicated `migrate` container connects AS sensei_migrator (the owner
/// of every schema object the chain creates) and this mode applies the
/// chain, then exits 0 — `docker compose` gates the API/workers on
/// `service_completed_successfully`. Any failure exits 1 so the stack
/// never starts against an un-migrated schema. This mode never serves and
/// never seeds; it is the ONLY path that runs DDL in production.
/// (Every branch terminates the process — it never returns normally.)
async fn run_migrations_only(config: &AppConfig) {
    let database_url = std::env::var("DATABASE_URL").unwrap_or_default();
    if database_url.is_empty() {
        tracing::error!("--migrate-only requires DATABASE_URL to be set");
        std::process::exit(1);
    }

    let pool = match PgPoolOptions::new()
        .max_connections(config.database.max_connections)
        .acquire_timeout(std::time::Duration::from_secs(
            config.database.connection_timeout_secs,
        ))
        .connect(&database_url)
        .await
    {
        Ok(pool) => {
            info!("PostgreSQL connection pool established (migrate-only)");
            pool
        }
        Err(e) => {
            tracing::error!(error = %e, "migrate-only: failed to connect to PostgreSQL");
            std::process::exit(1);
        }
    };

    match sensei_db::migrations::run_migrations(&pool).await {
        Ok(()) => {
            info!("Migration chain applied successfully — migrate-only run complete");
            std::process::exit(0);
        }
        Err(e) => {
            tracing::error!(error = %e, "migrate-only: migration chain failed");
            std::process::exit(1);
        }
    }
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

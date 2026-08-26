//! # sensei-workers — NATS JetStream consumer binary
//!
//! Starts every task consumer (email, PDF, ML, analytics), the JetStream
//! [`TaskDispatcher`], and the Beat-style [`TaskScheduler`], then runs until
//! SIGTERM/SIGINT.
//!
//! # Startup sequence
//!
//! 1. Parse `--version` / `--help` / `--healthcheck` (exits before any infrastructure).
//! 2. Load validated configuration via [`AppConfig::from_env`] — a
//!    configuration error prints a clear message and exits with status 1.
//! 3. Initialize structured logging (JSON in production, human-readable in
//!    development).
//! 4. Connect to PostgreSQL. **In production a failed connection or failed
//!    migrations abort startup (exit 1).** In development the worker logs a
//!    warning and continues with `None` (consumers that can operate without
//!    the database degrade gracefully).
//! 5. Connect to NATS JetStream (`NATS_TOKEN` is used when set). **In
//!    production a failed connection aborts startup.** In development the
//!    worker warns and continues with consumers/scheduler disabled.
//! 6. Initialize file storage (S3/MinIO when `S3_ENDPOINT` + credentials are
//!    set, local disk otherwise) and SMTP.
//! 7. Build a [`WorkerContext`] holding the shared stores, instantiate every
//!    consumer, register them on the dispatcher, and start the scheduler.
//! 8. Wait for SIGTERM/SIGINT, stop all consumers, flush, exit 0.

use std::sync::Arc;
use std::time::Duration;

use async_nats::jetstream::Context;
use sensei_core::config::AppConfig;
use sensei_services::storage::{FileStorageService, LocalStorageService, S3StorageService};
use sensei_workers::analytics::{KpiWorker, SnapshotWorker};
use sensei_workers::email::{EmailWorker, SmtpConfig};
use sensei_workers::ml::{DriftCheckWorker, ForceRetrainWorker, RetrainAllWorker, TrainingWorker};
use sensei_workers::pdf::{A3PdfWorker, QuotePdfWorker};
mod healthcheck;

use sensei_workers::scheduler::TaskScheduler;
use sensei_workers::task::{TaskConsumer, TaskDispatcher};
use sqlx::PgPool;
use tokio::signal::unix::{signal, SignalKind};
use tracing::{error, info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Layer};

/// Crate version, printed by `--version`.
const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Usage text printed by `--help`.
const USAGE: &str = "\
sensei-workers — Sensei OS NATS JetStream task consumer

USAGE:
    sensei-workers [OPTIONS]

OPTIONS:
    -V, --version    Print version information and exit
    -h, --help       Print this help message and exit

ENVIRONMENT:
    SENSEI_ENV        development | staging | production (default: development)
    DATABASE_URL      PostgreSQL connection URL
    NATS_URL          NATS server URL (default: nats://localhost:4222)
    NATS_TOKEN        NATS token (sent when set)
    S3_ENDPOINT       S3/MinIO endpoint (S3 storage when set)
    S3_BUCKET         S3 bucket (default: sensei-uploads)
    S3_ACCESS_KEY     S3 access key
    S3_SECRET_KEY     S3 secret key
    STORAGE_BACKEND   local | s3 (default: local)
    SMTP_HOST         SMTP relay host (email sending when set)
    SMTP_PORT         SMTP port (default: 587)
    SMTP_USERNAME     SMTP username
    SMTP_PASSWORD     SMTP password
    SMTP_FROM_ADDRESS From address (default: noreply@sensei.local)
    LOG_LEVEL         trace | debug | info | warn | error (default: info)
";

/// Shared dependencies handed to every consumer.
///
/// # Integration point (contract with D)
///
/// The `sensei-workers` library does not yet expose a canonical
/// `WorkerContext` / `consumers()` factory. This struct mirrors the stores
/// the library consumers read from their constructors today (JetStream
/// context, DB pool, file storage, SMTP config). When D lands a canonical
/// context on the library, replace [`build_consumers`] with that surface —
/// the rest of this binary is unchanged.
#[derive(Clone)]
pub struct WorkerContext {
    /// NATS JetStream context (dispatcher, scheduler, PDF KV progress).
    pub js: Context,
    /// PostgreSQL pool — `None` in development fallback mode.
    pub pool: Option<Arc<PgPool>>,
    /// File storage backend (S3/MinIO or local disk).
    pub storage: Arc<dyn FileStorageService>,
    /// SMTP configuration for the email consumer.
    pub smtp: SmtpConfig,
}

fn main() {
    // `--version` / `--help` must work without any infrastructure or
    // configuration (verified by CI with `cargo run -p sensei-workers --
    // --version`).
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--version" || a == "-V") {
        println!("sensei-workers {VERSION}");
        return;
    }
    if args.iter().any(|a| a == "--help" || a == "-h") {
        print!("{USAGE}");
        return;
    }
    if args.iter().any(|a| a == "--healthcheck" || a == "--health") {
        // Kubernetes exec probe: exits 0 when DB + NATS are reachable.
        // Verifies REAL connectivity, not process existence.
        std::process::exit(healthcheck::runtime_healthcheck());
    }

    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap_or_else(|e| {
            eprintln!("FATAL: failed to build tokio runtime: {e}");
            std::process::exit(1);
        });

    runtime.block_on(run());
    // `run` exits with a non-zero status itself on fatal errors.
}

/// Load configuration and run the worker until shutdown.
async fn run() {
    let config = match AppConfig::from_env() {
        Ok(config) => config,
        Err(e) => {
            eprintln!("FATAL: failed to load configuration: {e}");
            std::process::exit(1);
        }
    };

    init_tracing(&config);

    info!(
        environment = %config.environment,
        version = VERSION,
        "Starting sensei-workers"
    );

    // ── PostgreSQL (fail fast in production; dev fallback) ──────────
    let pool = match connect_database(&config).await {
        Ok(pool) => {
            if pool.is_some() {
                info!("PostgreSQL connection pool established — workers run in DATABASE mode");
            }
            pool
        }
        Err(ConnectError::Fatal(msg)) => {
            error!(error = %msg, "Fatal database failure in production");
            eprintln!("FATAL: {msg}");
            std::process::exit(1);
        }
        Err(ConnectError::Degraded(msg)) => {
            warn!(error = %msg, "Running without a database (development fallback)");
            None
        }
    };

    // ── NATS JetStream (fail fast in production; dev fallback) ──────
    let nats = match connect_nats(&config).await {
        Ok((client, js)) => {
            info!(url = %config.event_bus.url, "Connected to NATS JetStream");
            Some((client, js))
        }
        Err(ConnectError::Fatal(msg)) => {
            error!(error = %msg, "Fatal NATS failure in production");
            eprintln!("FATAL: {msg}");
            std::process::exit(1);
        }
        Err(ConnectError::Degraded(msg)) => {
            warn!(
                error = %msg,
                "NATS JetStream unavailable — consumers and scheduler DISABLED \
                 (development fallback)"
            );
            None
        }
    };

    let Some((_client, js)) = nats else {
        // Development fallback: nothing consumes and nothing is scheduled,
        // but the process stays up so `cargo run -p sensei-workers` and
        // docker-compose behave predictably. Exit 0 on signal.
        info!(
            "No NATS JetStream connection — workers idle. Start NATS and restart \
             to enable task processing."
        );
        wait_for_shutdown().await;
        info!("Worker shutdown complete (no consumers were running)");
        return;
    };

    // ── Storage (S3/MinIO or local disk) ────────────────────────────
    let storage = init_storage(&config);

    // ── SMTP ────────────────────────────────────────────────────────
    let smtp = SmtpConfig {
        host: config.email.smtp_host.clone(),
        port: config.email.smtp_port,
        username: config.email.smtp_username.clone(),
        password: config.email.smtp_password.clone(),
        from_address: config.email.from_address.clone(),
        use_tls: config.email.use_tls,
    };
    if smtp.host.is_empty() {
        warn!(
            "SMTP_HOST is not set — the email consumer will fail every email task \
             permanently (dead-lettered). Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, \
             SMTP_PASSWORD, SMTP_FROM_ADDRESS to enable delivery."
        );
    }

    // ── Dispatcher + every consumer ─────────────────────────────────
    let mut dispatcher = TaskDispatcher::new(js.clone()).with_stream_name("sensei");
    let ctx = WorkerContext {
        js: js.clone(),
        pool: pool.clone(),
        storage: storage.clone(),
        smtp,
    };
    for consumer in build_consumers(&ctx) {
        dispatcher.register(consumer);
    }
    info!(
        consumers = dispatcher.consumer_count(),
        "Registered task consumers"
    );

    let consumer_handles = match dispatcher.start().await {
        Ok(handles) => handles,
        Err(e) => {
            let msg = format!("Failed to start task dispatcher (JetStream): {e}");
            if config.environment.is_prod() {
                error!(error = %msg, "Fatal JetStream failure in production");
                eprintln!("FATAL: {msg}");
                std::process::exit(1);
            }
            warn!(error = %msg, "Task dispatcher failed — running without consumers (development fallback)");
            Vec::new()
        }
    };

    // ── Beat-style scheduler (daily snapshots, KPIs, retrains) ──────
    // PostgreSQL advisory-lock leader election prevents duplicate scheduled
    // work when multiple worker instances run; without a database the
    // single-process in-memory schedule is used (dev only).
    const SCHEDULER_LOCK_KEY: i64 = 0x5343_4845_4455_4C45;
    let scheduler = match pool.as_ref() {
        Some(p) => {
            TaskScheduler::with_leader_election(js.clone(), Arc::clone(p), SCHEDULER_LOCK_KEY)
                .with_default_schedule()
                .await
        }
        None => TaskScheduler::new(js.clone()).with_default_schedule().await,
    };
    info!(
        scheduled_tasks = scheduler.task_count(),
        "Scheduler started with default Celery-Beat replacement schedule"
    );
    let scheduler_handles = match scheduler.start().await {
        Ok(handles) => handles,
        Err(e) => {
            warn!(error = %e, "Scheduler failed to start — continuing with consumers only");
            Vec::new()
        }
    };

    info!(
        consumers = consumer_handles.len(),
        scheduled_tasks = scheduler_handles.len(),
        "sensei-workers is fully started"
    );

    // ── Graceful shutdown ───────────────────────────────────────────
    wait_for_shutdown().await;
    shutdown(consumer_handles, scheduler_handles).await;
}

/// How a startup dependency connect can fail.
enum ConnectError {
    /// Production policy: abort startup with exit 1.
    Fatal(String),
    /// Development policy: continue degraded with a warning.
    Degraded(String),
}

/// Connect to PostgreSQL. Fail fast in production; degrade with a warning in
/// development (documented fallback — workers run without a pool).
async fn connect_database(config: &AppConfig) -> Result<Option<Arc<PgPool>>, ConnectError> {
    let url = config.database.url.clone();
    if url.is_empty() {
        return Err(if config.environment.is_prod() {
            ConnectError::Fatal(
                "DATABASE_URL is not set — refusing to start workers in production \
                 without a database"
                    .to_string(),
            )
        } else {
            ConnectError::Degraded("DATABASE_URL is not set".to_string())
        });
    }

    let pool = match sensei_db::pg_pool::init_pool(&config.database).await {
        Ok(pool) => pool,
        Err(e) => {
            let msg = format!("Failed to connect to PostgreSQL at {url}: {e}");
            return Err(if config.environment.is_prod() {
                ConnectError::Fatal(msg)
            } else {
                ConnectError::Degraded(msg)
            });
        }
    };

    if let Err(e) = sensei_db::migrations::run_migrations(&pool).await {
        let msg = format!("Failed to run database migrations: {e}");
        return Err(if config.environment.is_prod() {
            ConnectError::Fatal(msg)
        } else {
            ConnectError::Degraded(msg)
        });
    }

    Ok(Some(pool))
}

/// Connect to NATS with optional token auth (`NATS_TOKEN`) and create the
/// JetStream context. Fail fast in production; degrade in development.
async fn connect_nats(config: &AppConfig) -> Result<(async_nats::Client, Context), ConnectError> {
    let url = config.event_bus.url.clone();
    if url.is_empty() {
        return Err(if config.environment.is_prod() {
            ConnectError::Fatal(
                "NATS_URL is not set — refusing to start workers in production \
                 without NATS JetStream"
                    .to_string(),
            )
        } else {
            ConnectError::Degraded("NATS_URL is not set".to_string())
        });
    }

    let mut options = async_nats::ConnectOptions::default()
        .connection_timeout(Duration::from_secs(10))
        .max_reconnects(config.event_bus.max_reconnect);
    if let Ok(token) = std::env::var("NATS_TOKEN") {
        if !token.is_empty() {
            options = options.token(token);
        }
    }

    let client = match options.connect(&url).await {
        Ok(client) => client,
        Err(e) => {
            let msg = format!("Failed to connect to NATS at {url}: {e}");
            return Err(if config.environment.is_prod() {
                ConnectError::Fatal(msg)
            } else {
                ConnectError::Degraded(msg)
            });
        }
    };

    Ok((client.clone(), async_nats::jetstream::new(client)))
}

/// Initialize file storage: S3/MinIO when endpoint + credentials are
/// configured, local disk otherwise.
fn init_storage(config: &AppConfig) -> Arc<dyn FileStorageService> {
    let cfg = &config.storage;
    let use_s3 = cfg.backend == "s3"
        || (cfg.s3_endpoint.as_deref().is_some_and(|e| !e.is_empty())
            && !cfg.s3_access_key.is_empty()
            && !cfg.s3_secret_key.is_empty());

    if use_s3 {
        match S3StorageService::new(
            &cfg.s3_bucket,
            &cfg.s3_region,
            cfg.s3_endpoint.as_deref(),
            &cfg.s3_access_key,
            &cfg.s3_secret_key,
        ) {
            Ok(storage) => {
                info!(
                    bucket = %cfg.s3_bucket,
                    endpoint = ?cfg.s3_endpoint,
                    "Initialized S3/MinIO file storage"
                );
                return Arc::new(storage);
            }
            Err(e) => {
                if config.environment.is_prod() {
                    // NO automatic downgrade in production: a PDF generated
                    // to pod-local disk would be invisible to the API and
                    // lost when the pod dies.
                    error!(
                        error = %e,
                        bucket = %cfg.s3_bucket,
                        "Failed to initialize S3 storage in production — refusing to start with local disk"
                    );
                    std::process::exit(1);
                }
                warn!(
                    error = %e,
                    "Failed to initialize S3 storage — falling back to local disk (development only)"
                );
            }
        }
    }

    info!(path = %cfg.local_path, "Initialized local file storage");
    Arc::new(LocalStorageService::new(cfg.local_path.clone()))
}

/// Instantiate every task consumer.
///
/// # Integration point (contract with D)
///
/// `EmailWorker::with_config`, `A3PdfWorker`/`QuotePdfWorker::new`,
/// `TrainingWorker`/`DriftCheckWorker`/`ForceRetrainWorker`/`RetrainAllWorker`,
/// and `SnapshotWorker`/`KpiWorker` are the current library constructors.
/// The ML/analytics wrappers do not yet accept a pool or a storage backend —
/// once D lands `WorkerContext`-aware constructors (or a `consumers()`
/// factory), swap the bodies below for that surface while keeping this
/// function's signature.
fn build_consumers(ctx: &WorkerContext) -> Vec<Arc<dyn TaskConsumer>> {
    vec![
        // Email — sends via SMTP from the shared context config.
        Arc::new(EmailWorker::with_config(ctx.smtp.clone())),
        // PDF generation — A3 reports and quotes (JetStream KV progress tracking).
        // PDF generation — real storage (shared across replicas), task
        // idempotency via the pool, and the JetStream KV for progress.
        Arc::new(A3PdfWorker::with_deps(
            ctx.js.clone(),
            ctx.pool.clone(),
            ctx.storage.clone(),
        )),
        Arc::new(QuotePdfWorker::with_deps(
            ctx.js.clone(),
            ctx.pool.clone(),
            ctx.storage.clone(),
        )),
        // ML — model training, drift checks, forced retrains. The pool makes
        // model state shared (never synthetic per-process calibration).
        Arc::new(TrainingWorker::with_pool(ctx.pool.clone())),
        Arc::new(DriftCheckWorker::with_pool(ctx.pool.clone())),
        Arc::new(ForceRetrainWorker::with_pool(ctx.pool.clone())),
        Arc::new(RetrainAllWorker::with_pool(ctx.pool.clone())),
        // Analytics — daily snapshots and warehouse KPIs (DB-backed).
        Arc::new(SnapshotWorker::with_pool(ctx.pool.clone())),
        Arc::new(KpiWorker::with_pool(ctx.pool.clone())),
    ]
}

/// Wait for SIGTERM or SIGINT.
async fn wait_for_shutdown() {
    let mut sigterm = match signal(SignalKind::terminate()) {
        Ok(s) => s,
        Err(e) => {
            error!(error = %e, "Failed to install SIGTERM handler");
            // Fall back to ctrl-c only.
            let _ = tokio::signal::ctrl_c().await;
            return;
        }
    };
    let mut sigint = match signal(SignalKind::interrupt()) {
        Ok(s) => s,
        Err(e) => {
            error!(error = %e, "Failed to install SIGINT handler");
            let _ = sigterm.recv().await;
            return;
        }
    };

    tokio::select! {
        _ = sigterm.recv() => info!("Received SIGTERM — shutting down"),
        _ = sigint.recv() => info!("Received SIGINT — shutting down"),
    }
}

/// Stop every consumer and scheduler task, then flush and exit cleanly.
async fn shutdown(
    consumer_handles: Vec<tokio::task::JoinHandle<()>>,
    scheduler_handles: Vec<tokio::task::JoinHandle<()>>,
) {
    info!(
        consumers = consumer_handles.len(),
        scheduled_tasks = scheduler_handles.len(),
        "Stopping workers"
    );

    // Abort the pull loops first so no new task is picked up, then await so
    // in-flight cleanup (acks, KV writes, logs) settles.
    for handle in consumer_handles.iter().chain(scheduler_handles.iter()) {
        handle.abort();
    }
    for handle in consumer_handles.into_iter().chain(scheduler_handles) {
        let _ = handle.await;
    }

    // Flush point: storage backends write synchronously, JetStream acks are
    // durable on the server, and the PostgreSQL pool is dropped on exit.
    // Logging the completion gives operators a deterministic shutdown mark.
    info!("All consumers stopped — workers flushed and exiting");
}

/// Initialize tracing: JSON in production, human-readable in development.
fn init_tracing(config: &AppConfig) {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&config.observability.log_level));

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

    tracing_subscriber::registry()
        .with(fmt_layer)
        .with(env_filter)
        .init();
}

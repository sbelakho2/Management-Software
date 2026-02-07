"""
Sensei OS Backend - Main Application Entry Point

This module initializes the FastAPI application with all middleware,
routers, and lifecycle handlers.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from sensei.core.config import settings
from sensei.core.database import engine, check_database_connection
from sensei.core.redis import (
    redis_client,
    check_redis_connection,
    acquire_leader_lock,
    release_leader_lock,
    get_instance_id,
)
from sensei.core.storage import storage_client, check_storage_connection
from sensei.api.v1 import api_router
from sensei.api.exceptions import register_exception_handlers
from sensei.middleware.logging import StructuredLoggingMiddleware
from sensei.middleware.timing import TimingMiddleware
from sensei.middleware.correlation import CorrelationIdMiddleware
from sensei.middleware.secure_headers import SecureHeadersASGIMiddleware, SecureHeadersMiddleware
from sensei.middleware.rate_limit import RateLimitMiddleware
from sensei.middleware.session_binding import SessionBindingMiddleware
from sensei.middleware.request_guard import RequestGuardMiddleware
from sensei.services.core.backup_scheduler import BackupSchedulerService
from sensei.services.core.database_backup import DatabaseBackupService
from sensei.services.core.health_checks import HealthCheckService
from sensei.services.ops.kpi_app_services import muda_nudging_service
from sensei.services.ops.muda_nudging_scheduler import (
    MudaNudgingScheduleConfig,
    MudaNudgingSchedulerService,
)
from sensei.services.ops.muda_nudging_worker import MudaNudgingJobRunner
from sensei.services.ops.cognitive_obeya import get_cognitive_obeya
from sensei.services.core.factory_launchpad import get_factory_launchpad
from sensei.services.core.edge_ai import get_edge_orchestrator
from sensei.services.core.rbac_bootstrap import ensure_core_users_have_roles
from sensei.core.websocket import get_websocket_manager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info(
        "Starting Sensei OS",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )
    
    # Initialize OpenTelemetry if enabled
    if settings.OTEL_ENABLED:
        try:
            from sensei.core.telemetry import setup_telemetry
            telemetry_ok = setup_telemetry()
            if telemetry_ok:
                logger.info("OpenTelemetry distributed tracing initialized")
            else:
                logger.warning("OpenTelemetry initialization failed")
        except ImportError:
            logger.info("OpenTelemetry not installed - tracing disabled")
        except Exception as e:
            logger.warning(f"OpenTelemetry setup error: {e}")
    
    # Verify connections
    db_ok = await check_database_connection(engine)
    redis_ok = await check_redis_connection(redis_client)
    storage_ok = await check_storage_connection(storage_client)
    
    if not all([db_ok, redis_ok, storage_ok]):
        logger.error(
            "Service dependencies not ready",
            database=db_ok,
            redis=redis_ok,
            storage=storage_ok,
        )
    else:
        logger.info("All service dependencies connected")
    
    # Warm up the connection pool: pre-create connections so the first
    # batch of requests doesn't suffer pool-creation latency.
    try:
        pool_size = min(settings.DATABASE_POOL_SIZE, 4)
        async with engine.connect() as _warmup_conn:
            pass
        logger.info("Database connection pool warmed up", pool_size=pool_size)
    except Exception as e:
        logger.warning("Connection pool warm-up failed (non-fatal)", error=str(e))
    
    # Initialize and start backup scheduler
    # IMPORTANT: Use leader election to prevent duplicate schedulers in horizontal scaling
    try:
        from sensei.core.database import async_session_factory
        # Ensure core RBAC roles/assignments exist (especially for built-in accounts).
        try:
            async with async_session_factory() as session:
                await ensure_core_users_have_roles(session)
                await session.commit()
        except Exception as e:
            logger.error("Failed to bootstrap core RBAC roles", error=str(e))

        # Only start backup scheduler if we're the leader
        is_backup_leader = await acquire_leader_lock(
            "backup_scheduler_leader",
            ttl_seconds=120,  # Lock expires after 2 minutes if we crash
        )
        
        if is_backup_leader:
            backup_service = DatabaseBackupService(
                db_session_factory=async_session_factory,
                backup_storage_path=settings.BACKUP_STORAGE_PATH if hasattr(settings, 'BACKUP_STORAGE_PATH') else "/tmp/backups",
                database_url=str(settings.DATABASE_URL),
                s3_client=storage_client,
            )
            backup_scheduler = BackupSchedulerService(backup_service=backup_service)
            backup_scheduler.start()
            app.state.backup_scheduler = backup_scheduler
            app.state.is_backup_leader = True
            logger.info(
                "Backup scheduler started (leader elected)",
                instance_id=get_instance_id(),
            )
        else:
            app.state.is_backup_leader = False
            logger.info(
                "Backup scheduler not started (another instance is leader)",
                instance_id=get_instance_id(),
            )
    except Exception as e:
        logger.error("Failed to start backup scheduler", error=str(e))

    # Initialize and start muda nudging scheduler (disabled by default)
    # IMPORTANT: Use leader election to prevent duplicate schedulers
    try:
        recipient_id_strs = [
            r.strip()
            for r in settings.MUDA_NUDGING_WORKER_RECIPIENT_IDS.split(",")
            if r.strip()
        ]
        recipient_ids: list[UUID] = []
        for rid in recipient_id_strs:
            try:
                recipient_ids.append(UUID(rid))
            except ValueError:
                logger.warning(f"Invalid UUID in MUDA_NUDGING_WORKER_RECIPIENT_IDS: {rid}")
        muda_cfg = MudaNudgingScheduleConfig(
            enabled=bool(settings.MUDA_NUDGING_WORKER_ENABLED),
            interval_seconds=int(settings.MUDA_NUDGING_WORKER_INTERVAL_SECONDS),
            recipient_ids=recipient_ids,
        )
        
        # Only start muda scheduler if enabled AND we're the leader
        is_muda_leader = False
        if muda_cfg.enabled:
            is_muda_leader = await acquire_leader_lock(
                "muda_nudging_scheduler_leader",
                ttl_seconds=120,
            )
        
        if is_muda_leader:
            muda_runner = MudaNudgingJobRunner(nudging_service=muda_nudging_service)
            muda_scheduler = MudaNudgingSchedulerService(
                job_runner=muda_runner,
                loop=asyncio.get_running_loop(),
                config=muda_cfg,
            )
            muda_scheduler.start()
            app.state.muda_nudging_scheduler = muda_scheduler
            app.state.is_muda_leader = True
            logger.info(
                "Muda nudging scheduler started (leader elected)",
                instance_id=get_instance_id(),
            )
        else:
            app.state.is_muda_leader = False
            if muda_cfg.enabled:
                logger.info(
                    "Muda nudging scheduler not started (another instance is leader)",
                    instance_id=get_instance_id(),
                )
    except Exception as e:
        logger.error("Failed to start muda nudging scheduler", error=str(e))
    
    # Pre-initialize singletons
    try:
        get_cognitive_obeya()
        get_factory_launchpad()
        get_edge_orchestrator()
        logger.info("Core services pre-initialized successfully")
    except Exception as e:
        logger.error("Failed to pre-initialize core services", error=str(e))
    
    # Initialize WebSocket Redis pub/sub for multi-instance support
    try:
        ws_manager = get_websocket_manager()
        await ws_manager.initialize()
        logger.info("WebSocket Redis pub/sub adapter initialized")
    except Exception as e:
        logger.warning("WebSocket pub/sub init failed (single-instance mode)", error=str(e))
    
    # Verify AI/Chatbot model availability at startup
    try:
        health_service = HealthCheckService()
        ai_model_ok = await health_service.verify_ai_model_at_startup()
        app.state.health_service = health_service
        
        if not ai_model_ok:
            logger.warning(
                "AI model not available - chatbot functionality will be limited",
                environment=settings.ENVIRONMENT,
            )
            # In production, this might be critical
            if settings.ENVIRONMENT == "production":
                logger.error(
                    "CRITICAL: AI model unavailable in production. "
                    "Download model or disable chatbot features."
                )
    except Exception as e:
        logger.error("Failed to verify AI model availability", error=str(e))

    yield
    
    # Shutdown
    logger.info("Shutting down Sensei OS")
    
    # Shutdown WebSocket pub/sub adapter
    try:
        ws_manager = get_websocket_manager()
        await ws_manager.shutdown()
    except Exception as e:
        logger.error("Error shutting down WebSocket pub/sub", error=str(e))
    
    # Stop backup scheduler and release leader lock
    if hasattr(app.state, "backup_scheduler"):
        try:
            app.state.backup_scheduler.stop()
            logger.info("Backup scheduler stopped")
        except Exception as e:
            logger.error("Error stopping backup scheduler", error=str(e))
    
    if getattr(app.state, "is_backup_leader", False):
        try:
            await release_leader_lock("backup_scheduler_leader")
            logger.info("Released backup scheduler leader lock")
        except Exception as e:
            logger.error("Error releasing backup scheduler leader lock", error=str(e))

    # Stop muda nudging scheduler and release leader lock
    if hasattr(app.state, "muda_nudging_scheduler"):
        try:
            app.state.muda_nudging_scheduler.stop()
        except Exception as e:
            logger.error("Error stopping muda nudging scheduler", error=str(e))
    
    if getattr(app.state, "is_muda_leader", False):
        try:
            await release_leader_lock("muda_nudging_scheduler_leader")
            logger.info("Released muda nudging scheduler leader lock")
        except Exception as e:
            logger.error("Error releasing muda nudging leader lock", error=str(e))
    
    await engine.dispose()
    logger.info("Database engine disposed")
    try:
        aclose = getattr(redis_client, "aclose", None)
        if callable(aclose):
            await aclose()
        else:
            await redis_client.close()  # type: ignore[union-attr]
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning("Error closing Redis connection", error=str(e))


def create_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    app = FastAPI(
        title="Sensei OS API",
        description="Intelligent Management & Teaching System for Starz Morocco",
        version=settings.VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )
    
    # Add middleware (order matters - first added is outermost)
    # CORS configuration - strict in production, relaxed in development
    if settings.ENVIRONMENT == "production":
        # Production: Only allow specific methods and headers
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Accept",
                "X-Correlation-ID",
                "X-Request-ID",
            ],
            expose_headers=["X-Correlation-ID", "X-Request-ID"],
            max_age=86400,  # Cache preflight for 24 hours
        )
    else:
        # Development: Allow all for easier testing
        dev_origins = sorted(
            set(
                (
                    settings.CORS_ORIGINS
                    + [
                        # Common local dev + Playwright ports
                        "http://localhost:3000",
                        "http://127.0.0.1:3000",
                        "http://localhost:3001",
                        "http://127.0.0.1:3001",
                        "http://localhost:3100",
                        "http://127.0.0.1:3100",
                    ]
                )
            )
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=dev_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add security headers (CSP/HSTS/etc). Use a minimal API preset in production
    # and a relaxed preset for local development/testing (Swagger UI, etc.).
    secure_headers = SecureHeadersMiddleware()
    if settings.ENVIRONMENT == "production":
        secure_headers.apply_api_preset()
    else:
        secure_headers.apply_relaxed_preset()
    app.add_middleware(SecureHeadersASGIMiddleware, config=secure_headers)

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    
    # Request guard: timeout + body size limits (#266, #267)
    app.add_middleware(
        RequestGuardMiddleware,
        timeout_seconds=30,
        max_body_bytes=10 * 1024 * 1024,   # 10 MB default
        large_body_bytes=100 * 1024 * 1024, # 100 MB for uploads
        enabled=True,
    )
    
    # Session binding middleware - enabled in production for security
    if settings.SESSION_BINDING_ENABLED:
        app.add_middleware(
            SessionBindingMiddleware,
            enabled=True,
            salt=settings.SESSION_FINGERPRINT_SALT,
        )
    
    # Metrics middleware for Prometheus
    if settings.METRICS_ENABLED:
        try:
            from sensei.core.metrics import MetricsMiddleware
            app.add_middleware(MetricsMiddleware)
            logger.info("Prometheus metrics middleware enabled")
        except ImportError:
            logger.warning("Metrics module not available")
    
    # Rate limiting - enabled in production, configurable otherwise
    rate_limit_enabled = settings.ENVIRONMENT == "production" or settings.RATE_LIMIT_ENABLED
    app.add_middleware(
        RateLimitMiddleware,
        enabled=rate_limit_enabled,
    )
    
    # Include API routers
    app.include_router(api_router, prefix="/api/v1")
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint for load balancers and monitoring."""
        db_ok = await check_database_connection(engine)
        redis_ok = await check_redis_connection(redis_client)
        storage_ok = await check_storage_connection(storage_client)
        
        healthy = all([db_ok, redis_ok, storage_ok])
        
        return {
            "status": "healthy" if healthy else "degraded",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "services": {
                "database": "up" if db_ok else "down",
                "redis": "up" if redis_ok else "down",
                "storage": "up" if storage_ok else "down",
            },
        }
    
    # Prometheus metrics endpoint
    if settings.METRICS_ENABLED:
        try:
            from sensei.core.metrics import metrics_endpoint, get_slo_summary
            
            @app.get(settings.METRICS_PATH, tags=["Metrics"], include_in_schema=False)
            async def prometheus_metrics(request: Request):
                """Prometheus metrics endpoint for scraping."""
                return await metrics_endpoint(request)
            
            @app.get("/api/v1/slo/status", tags=["Metrics"])
            async def slo_status():
                """Get current SLO compliance status."""
                return get_slo_summary()
                
        except ImportError:
            logger.warning("Metrics module not available for endpoint")
    
    return app


app = create_application()

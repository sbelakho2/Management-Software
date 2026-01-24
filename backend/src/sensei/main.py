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
from sensei.core.redis import redis_client, check_redis_connection
from sensei.core.storage import storage_client, check_storage_connection
from sensei.api.v1 import api_router
from sensei.api.exceptions import register_exception_handlers
from sensei.middleware.logging import StructuredLoggingMiddleware
from sensei.middleware.timing import TimingMiddleware
from sensei.middleware.correlation import CorrelationIdMiddleware
from sensei.middleware.secure_headers import SecureHeadersASGIMiddleware, SecureHeadersMiddleware
from sensei.middleware.rate_limit import RateLimitMiddleware
from sensei.services.core.backup_scheduler import BackupSchedulerService
from sensei.services.core.database_backup import DatabaseBackupService
from sensei.services.ops.kpi_app_services import muda_nudging_service
from sensei.services.ops.muda_nudging_scheduler import (
    MudaNudgingScheduleConfig,
    MudaNudgingSchedulerService,
)
from sensei.services.ops.muda_nudging_worker import MudaNudgingJobRunner
from sensei.services.ops.cognitive_obeya import get_cognitive_obeya
from sensei.services.core.factory_launchpad import get_factory_launchpad
from sensei.services.core.edge_ai import get_edge_orchestrator

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
    
    # Initialize and start backup scheduler
    try:
        from sensei.core.database import async_session_factory
        backup_service = DatabaseBackupService(
            db_session_factory=async_session_factory,
            backup_storage_path=settings.BACKUP_STORAGE_PATH if hasattr(settings, 'BACKUP_STORAGE_PATH') else "/tmp/backups",
            database_url=str(settings.DATABASE_URL),
            s3_client=storage_client,
        )
        backup_scheduler = BackupSchedulerService(backup_service=backup_service)
        backup_scheduler.start()
        app.state.backup_scheduler = backup_scheduler
        logger.info("Backup scheduler started successfully")
    except Exception as e:
        logger.error("Failed to start backup scheduler", error=str(e))

    # Initialize and start muda nudging scheduler (disabled by default)
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
        muda_runner = MudaNudgingJobRunner(nudging_service=muda_nudging_service)
        muda_scheduler = MudaNudgingSchedulerService(
            job_runner=muda_runner,
            loop=asyncio.get_running_loop(),
            config=muda_cfg,
        )
        muda_scheduler.start()
        app.state.muda_nudging_scheduler = muda_scheduler
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

    yield
    
    # Shutdown
    logger.info("Shutting down Sensei OS")
    
    # Stop backup scheduler
    if hasattr(app.state, "backup_scheduler"):
        try:
            app.state.backup_scheduler.stop()
            logger.info("Backup scheduler stopped")
        except Exception as e:
            logger.error("Error stopping backup scheduler", error=str(e))

    # Stop muda nudging scheduler
    if hasattr(app.state, "muda_nudging_scheduler"):
        try:
            app.state.muda_nudging_scheduler.stop()
        except Exception as e:
            logger.error("Error stopping muda nudging scheduler", error=str(e))
    
    await engine.dispose()
    aclose = getattr(redis_client, "aclose", None)
    if callable(aclose):
        await aclose()
    else:
        await redis_client.close()


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
    
    return app


app = create_application()

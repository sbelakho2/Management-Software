"""
Sensei OS Backend - Main Application Entry Point

This module initializes the FastAPI application with all middleware,
routers, and lifecycle handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

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
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sensei OS")
    await engine.dispose()
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    
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

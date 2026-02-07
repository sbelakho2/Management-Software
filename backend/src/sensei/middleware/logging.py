"""
Structured Logging Middleware

Logs all HTTP requests with structured data for observability.
"""

import time
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with structured data."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        # Skip logging for health checks
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)
        
        # Extract request details
        request_id = request.headers.get("X-Request-ID", "")
        correlation_id = getattr(request.state, "correlation_id", "")
        
        # Get user info if authenticated
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
        
        # Log request start
        log = logger.bind(
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_id,
            client_ip=request.client.host if request.client else None,
        )
        
        # Reuse timing from TimingMiddleware if available (#128)
        start_time = getattr(request.state, "_request_start_time", None) or time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            log.info(
                "HTTP request completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            return response
            
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log.exception(
                "HTTP request failed",
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            raise

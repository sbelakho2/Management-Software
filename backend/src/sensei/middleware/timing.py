"""
Request Timing Middleware

Adds timing headers to responses for performance monitoring.
Logs slow requests based on configurable thresholds.
"""

import time
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sensei.core.config import settings


logger = structlog.get_logger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add X-Process-Time header to responses."""
        start_time = time.perf_counter()
        # Share start time with other middleware (#128)
        request.state._request_start_time = start_time
        
        response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        threshold_ms = settings.SLOW_REQUEST_THRESHOLD_MS
        if threshold_ms and process_time * 1000 >= threshold_ms:
            logger.warning(
                "Slow request",
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=round(process_time * 1000, 2),
                correlation_id=getattr(request.state, "correlation_id", None),
            )
        
        return response

"""
Request Timing Middleware

Adds timing headers to responses for performance monitoring.
"""

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timing headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add X-Process-Time header to responses."""
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response

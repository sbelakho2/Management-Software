"""
Correlation ID Middleware

Adds unique correlation IDs to requests for distributed tracing.
"""

import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs for request tracing."""
    
    HEADER_NAME = "X-Correlation-ID"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add correlation ID to request state and response headers."""
        # Use existing correlation ID or generate new one
        correlation_id = request.headers.get(
            self.HEADER_NAME,
            str(uuid.uuid4())
        )
        
        # Store in request state for logging
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        
        # Add to response headers
        response.headers[self.HEADER_NAME] = correlation_id
        
        return response

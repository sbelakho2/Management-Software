"""
Request Guard Middleware

Provides request-level timeout and body size limit enforcement.
Prevents long-running requests from blocking workers and large payloads from OOMing workers.

Items #266 and #267 from the improvement checklist.
"""

import asyncio
from typing import Callable, Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger(__name__)

# Default limits
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_BODY_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Paths that are exempt from timeout (long-running by design)
_TIMEOUT_EXEMPT_PATHS = frozenset({
    "/api/v1/knowledge/ingest",
    "/api/v1/knowledge/embed",
    "/api/v1/training/train",
    "/api/v1/backups/create",
    "/api/v1/ai/chat",
    "/api/v1/ai/analyze",
    "/api/v1/reports/export",
})

# Paths that allow larger bodies (file uploads)
_LARGE_BODY_PATHS = frozenset({
    "/api/v1/attachments",
    "/api/v1/knowledge/ingest",
    "/api/v1/documents/upload",
    "/api/v1/backups/upload",
    "/api/v1/training/upload",
})

# Extended limit for file upload paths
LARGE_BODY_LIMIT_BYTES = 100 * 1024 * 1024  # 100 MB


class RequestGuardMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces:
    1. Request-level timeouts (prevents worker starvation)
    2. Request body size limits (prevents OOM from large payloads)
    """

    def __init__(
        self,
        app,
        timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        max_body_bytes: int = DEFAULT_MAX_BODY_SIZE_BYTES,
        large_body_bytes: int = LARGE_BODY_LIMIT_BYTES,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.max_body_bytes = max_body_bytes
        self.large_body_bytes = large_body_bytes
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # --- Body size check (#267) ---
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                body_size = int(content_length)
            except (ValueError, TypeError):
                body_size = 0

            # Determine limit based on path
            path = request.url.path
            is_upload = any(path.startswith(p) for p in _LARGE_BODY_PATHS)
            limit = self.large_body_bytes if is_upload else self.max_body_bytes

            if body_size > limit:
                limit_mb = limit / (1024 * 1024)
                logger.warning(
                    "request_body_too_large",
                    path=path,
                    method=request.method,
                    content_length=body_size,
                    limit=limit,
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "message": f"Request body too large. Maximum size is {limit_mb:.0f} MB.",
                        "error_code": "PAYLOAD_TOO_LARGE",
                    },
                )

        # --- Request timeout (#266) ---
        path = request.url.path
        is_exempt = any(path.startswith(p) for p in _TIMEOUT_EXEMPT_PATHS)

        if is_exempt or request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(
                "request_timeout",
                path=path,
                method=request.method,
                timeout_seconds=self.timeout_seconds,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "message": f"Request timed out after {self.timeout_seconds} seconds.",
                    "error_code": "REQUEST_TIMEOUT",
                },
            )

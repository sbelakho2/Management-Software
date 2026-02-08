"""
ETag / conditional-GET middleware (#270).

Generates a weak ``ETag`` header for GET responses based on an MD5
hash of the response body.  If the client sends ``If-None-Match``
with a matching ETag, the middleware short-circuits and returns
``304 Not Modified`` with an empty body, saving bandwidth.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class ETagMiddleware(BaseHTTPMiddleware):
    """Add ETag / If-None-Match / If-Match support to responses.

    - GET/HEAD: ETag generation + 304 Not Modified for If-None-Match
    - PUT/PATCH: 412 Precondition Failed for mismatched If-Match (optimistic concurrency)
    """

    # Paths excluded from ETag processing (streaming / real-time)
    EXCLUDE_PREFIXES: set[str] = {"/api/v1/health", "/api/v1/ws", "/api/v1/sse"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method.upper()

        # Only process cacheable and conditional methods
        if method not in {"GET", "HEAD", "PUT", "PATCH"}:
            return await call_next(request)

        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(p) for p in self.EXCLUDE_PREFIXES):
            return await call_next(request)

        response = await call_next(request)

        # Only tag successful responses
        if response.status_code < 200 or response.status_code >= 300:
            return response

        # Read body
        body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        # Generate weak ETag from body hash
        etag = f'W/"{hashlib.md5(body).hexdigest()}"'

        # GET/HEAD: Check If-None-Match → 304
        if method in {"GET", "HEAD"}:
            if_none_match = request.headers.get("If-None-Match", "")
            if if_none_match:
                # Weak comparison: strip W/ prefix and quotes
                client_tag = if_none_match.replace("W/", "").strip('"')
                server_tag = etag.replace("W/", "").strip('"')
                if client_tag == server_tag:
                    return Response(
                        status_code=304,
                        headers={"ETag": etag},
                    )

        # PUT/PATCH: Check If-Match → 412 Precondition Failed
        if method in {"PUT", "PATCH"}:
            if_match = request.headers.get("If-Match", "")
            if if_match:
                # Strong comparison for write operations
                client_tag = if_match.strip('"').replace("W/", "")
                server_tag = etag.replace("W/", "").strip('"')
                if client_tag != server_tag:
                    return Response(
                        status_code=412,
                        content=b'{"detail":"Precondition Failed: resource has been modified"}',
                        headers={"ETag": etag},
                        media_type="application/json",
                    )

        # Return response with ETag header
        headers = dict(response.headers)
        headers["ETag"] = etag
        if "Cache-Control" not in headers and method in {"GET", "HEAD"}:
            headers["Cache-Control"] = "private, no-cache, must-revalidate"

        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )

"""
Idempotency-Key middleware (#269).

Ensures that mutating requests (POST, PUT, PATCH) carrying an
``Idempotency-Key`` header are processed at most once.  If the same
key is seen again within the TTL window the original response is
replayed without executing the endpoint a second time.

Storage: in-process dict with a configurable TTL (default 24 h).
For multi-instance deployments swap ``InMemoryIdempotencyStore``
for a Redis-backed implementation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH"}
HEADER_NAME = "Idempotency-Key"
DEFAULT_TTL_SECONDS = 86_400  # 24 hours


@dataclass
class CachedResponse:
    """Stored result of a previously processed request."""

    status_code: int
    headers: dict[str, str]
    body: bytes
    created_at: float = field(default_factory=time.monotonic)


class InMemoryIdempotencyStore:
    """Simple in-memory store with TTL eviction."""

    def __init__(self, ttl: int = DEFAULT_TTL_SECONDS, max_entries: int = 50_000) -> None:
        self._store: dict[str, CachedResponse] = {}
        self._ttl = ttl
        self._max_entries = max_entries

    def get(self, key: str) -> CachedResponse | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry.created_at > self._ttl:
            self._store.pop(key, None)
            return None
        return entry

    def set(self, key: str, response: CachedResponse) -> None:
        # Evict expired entries when store is large
        if len(self._store) >= self._max_entries:
            self._evict()
        self._store[key] = response

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [k for k, v in self._store.items() if now - v.created_at > self._ttl]
        for k in expired:
            del self._store[k]


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware that honours the ``Idempotency-Key`` request header."""

    def __init__(self, app: Any, *, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        super().__init__(app)
        self.store = InMemoryIdempotencyStore(ttl=ttl)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only intercept mutating methods
        if request.method not in IDEMPOTENT_METHODS:
            return await call_next(request)

        idempotency_key = request.headers.get(HEADER_NAME)
        if not idempotency_key:
            return await call_next(request)

        # Construct a composite key: user + path + idempotency key
        user = getattr(getattr(request, "state", None), "user", None)
        user_id = str(getattr(user, "id", "anon")) if user else "anon"
        composite = f"{user_id}:{request.url.path}:{idempotency_key}"
        cache_key = hashlib.sha256(composite.encode()).hexdigest()

        # Check for cached response
        cached = self.store.get(cache_key)
        if cached is not None:
            logger.info("Idempotency-Key hit: replaying cached response for key=%s", idempotency_key)
            return Response(
                content=cached.body,
                status_code=cached.status_code,
                headers={**cached.headers, "X-Idempotency-Replayed": "true"},
            )

        # Execute the request
        response = await call_next(request)

        # Read and cache the response body
        body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        # Store for replay
        resp_headers = dict(response.headers)
        self.store.set(
            cache_key,
            CachedResponse(
                status_code=response.status_code,
                headers=resp_headers,
                body=body,
            ),
        )

        return Response(
            content=body,
            status_code=response.status_code,
            headers=resp_headers,
        )

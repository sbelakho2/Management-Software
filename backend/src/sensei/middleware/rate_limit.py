"""sensei.middleware.rate_limit

Rate limiting middleware.

Production behavior:
- Uses Redis-backed storage for correctness in multi-instance deployments.
- Does not silently fall back to in-memory when running in production.

Non-production behavior:
- Falls back to an in-memory limiter if Redis is unavailable.
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from sensei.core.config import settings
from sensei.core.redis import redis_client

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint pattern."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10  # Max burst above rate limit
    block_duration_seconds: int = 60  # How long to block after exceeding limit


# Default rate limits by endpoint pattern
# NOTE: Limits are per-user (authenticated) or per-IP (unauthenticated)
# Tuned for enterprise multi-user ERP with 50-500 concurrent users
# Production-appropriate values that don't hide performance bottlenecks
DEFAULT_RATE_LIMITS: Dict[str, RateLimitConfig] = {
    # Auth endpoints - stricter limits to prevent brute force
    # But allow for shared office IPs and legitimate password failures
    "/api/v1/auth/login": RateLimitConfig(
        requests_per_minute=10,       # 10/min - stricter for security
        requests_per_hour=30,         # 30/hr - prevents sustained attacks
        burst_size=3,                 # Allow quick retries for typos
        block_duration_seconds=300,   # 5 minute block for abuse
    ),
    "/api/v1/auth/register": RateLimitConfig(
        requests_per_minute=5,        # Registration should be rare
        requests_per_hour=20,         # Onboarding events
        burst_size=2,
        block_duration_seconds=300,   # 5 minute block
    ),
    "/api/v1/auth/password-reset": RateLimitConfig(
        requests_per_minute=3,        # Very rare operation
        requests_per_hour=10,
        burst_size=2,
        block_duration_seconds=600,   # 10 minute block for abuse
    ),
    "/api/v1/auth/totp": RateLimitConfig(
        requests_per_minute=6,        # MFA can require retries
        requests_per_hour=30,
        burst_size=3,
        block_duration_seconds=300,
    ),
    # Search endpoints - still needs to be responsive but not unlimited
    "/api/v1/search": RateLimitConfig(
        requests_per_minute=60,       # 1/sec for typeahead
        requests_per_hour=1500,       # Reasonable for heavy search users
        burst_size=10,                # Autocomplete bursts
    ),
    # Export endpoints - resource intensive
    "/api/v1/export": RateLimitConfig(
        requests_per_minute=5,        # Exports are heavy
        requests_per_hour=50,         # Reports throughout day
        burst_size=2,
    ),
    # ML/AI endpoints - CPU intensive, needs tighter control
    "/api/v1/ml": RateLimitConfig(
        requests_per_minute=10,       # Reduced for CPU protection
        requests_per_hour=100,
        burst_size=3,
    ),
    # AI insights - role-based but still needs limits
    "/api/v1/ai": RateLimitConfig(
        requests_per_minute=30,       # AI queries can be expensive
        requests_per_hour=500,
        burst_size=5,
    ),
    # Bulk operations - very resource intensive
    "/api/v1/bulk": RateLimitConfig(
        requests_per_minute=3,
        requests_per_hour=20,
        burst_size=2,
    ),
    # Default for all other API endpoints
    # Production-appropriate: reveals bottlenecks that dev limits would hide
    "/api/v1": RateLimitConfig(
        requests_per_minute=60,       # 1 req/sec sustained (down from 200)
        requests_per_hour=1500,       # Reasonable daily usage (down from 5000)
        burst_size=15,                # Dashboard loads (down from 30)
    ),
}


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Note: This is a fallback for single-instance deployments.
    For distributed systems, use Redis-backed rate limiting.
    """
    
    def __init__(self):
        # {client_key: [(timestamp, count), ...]}
        self._windows: Dict[str, list] = defaultdict(list)
        self._blocked: Dict[str, float] = {}  # client_key -> unblock_time
        self._lock = asyncio.Lock()
        
    async def is_rate_limited(
        self,
        client_key: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if client is rate limited.
        
        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()
            
            # Check if client is blocked
            if client_key in self._blocked:
                unblock_time = self._blocked[client_key]
                if now < unblock_time:
                    return True, int(unblock_time - now)
                else:
                    del self._blocked[client_key]
            
            # Clean old entries and count recent requests
            window_minute = [(ts, c) for ts, c in self._windows[client_key] if now - ts < 60]
            window_hour = [(ts, c) for ts, c in self._windows[client_key] if now - ts < 3600]
            
            requests_last_minute = sum(c for _, c in window_minute)
            requests_last_hour = sum(c for _, c in window_hour)
            
            # Check limits
            if requests_last_minute >= config.requests_per_minute + config.burst_size:
                # Block the client
                self._blocked[client_key] = now + config.block_duration_seconds
                return True, config.block_duration_seconds
            
            if requests_last_hour >= config.requests_per_hour:
                # Calculate retry time based on oldest request in window
                if window_hour:
                    oldest = min(ts for ts, _ in window_hour)
                    retry_after = int(3600 - (now - oldest)) + 1
                else:
                    retry_after = 60
                return True, retry_after
            
            # Not limited - record this request
            self._windows[client_key] = window_hour  # Keep only last hour
            self._windows[client_key].append((now, 1))
            
            return False, None
    
    async def cleanup(self):
        """Clean up old entries to prevent memory growth."""
        async with self._lock:
            now = time.time()
            
            # Clean up windows older than 1 hour
            for key in list(self._windows.keys()):
                self._windows[key] = [
                    (ts, c) for ts, c in self._windows[key] 
                    if now - ts < 3600
                ]
                if not self._windows[key]:
                    del self._windows[key]
            
            # Clean up expired blocks
            self._blocked = {
                k: v for k, v in self._blocked.items() 
                if v > now
            }


class RedisRateLimiter:
    """Redis-backed sliding-window rate limiter.

    Uses a sorted-set of request timestamps per client key.
    """

    def __init__(self, key_namespace: str = "rate_limit") -> None:
        self._ns = key_namespace

    def _zset_key(self, client_key: str) -> str:
        return f"{self._ns}:events:{client_key}"

    def _block_key(self, client_key: str) -> str:
        return f"{self._ns}:blocked:{client_key}"

    async def is_rate_limited(
        self,
        client_key: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, Optional[int]]:
        """Check if client is rate limited.

        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        block_key = self._block_key(client_key)
        try:
            ttl_block = await redis_client.ttl(block_key)
            if ttl_block and ttl_block > 0:
                return True, int(ttl_block)

            now_ms = int(time.time() * 1000)
            one_minute_ms = 60_000
            one_hour_ms = 3_600_000

            zkey = self._zset_key(client_key)
            member = f"{now_ms}-{time.monotonic_ns()}"

            pipe = redis_client.pipeline(transaction=False)
            pipe.zadd(zkey, {member: now_ms})
            pipe.zremrangebyscore(zkey, 0, now_ms - one_hour_ms)
            pipe.expire(zkey, 3700)
            pipe.zcount(zkey, now_ms - one_minute_ms, now_ms)
            pipe.zcard(zkey)
            pipe.zrange(zkey, 0, 0, withscores=True)
            _, _, _, minute_count, hour_count, oldest = await pipe.execute()

            minute_limit = config.requests_per_minute + config.burst_size
            if minute_count >= minute_limit:
                await redis_client.setex(block_key, config.block_duration_seconds, "1")
                return True, int(config.block_duration_seconds)

            if hour_count >= config.requests_per_hour:
                # Compute retry_after based on oldest event still in the 1h window
                retry_after_seconds = 60
                if oldest:
                    # decode_responses=True => oldest is List[Tuple[member, score]]
                    oldest_score_ms = int(oldest[0][1])
                    retry_after_seconds = int((oldest_score_ms + one_hour_ms - now_ms) / 1000) + 1
                    if retry_after_seconds < 1:
                        retry_after_seconds = 1
                return True, retry_after_seconds

            return False, None
        except Exception as exc:
            # Let caller decide whether to fail-open or fail-closed.
            raise RuntimeError("Redis rate limiting failed") from exc


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Features:
    - Sliding window rate limiting
    - Per-endpoint configuration
    - IP + User-based limiting
    - Automatic cleanup of old entries
    - Retry-After header support
    """
    
    def __init__(
        self,
        app,
        rate_limits: Optional[Dict[str, RateLimitConfig]] = None,
        enabled: bool = True,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.rate_limits = rate_limits or DEFAULT_RATE_LIMITS
        self.enabled = enabled
        self.exclude_paths = exclude_paths or [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self._redis_limiter = RedisRateLimiter()
        self._memory_limiter = InMemoryRateLimiter()
        self._redis_ok: bool | None = None
        self._last_cleanup = time.time()

    async def _ensure_redis_ok(self) -> bool:
        """Check Redis health lazily and cache the result."""
        if self._redis_ok is not None:
            return self._redis_ok
        try:
            await asyncio.wait_for(redis_client.ping(), timeout=0.5)  # type: ignore[misc]
            self._redis_ok = True
        except Exception:
            self._redis_ok = False
        return self._redis_ok
    
    async def _maybe_cleanup_memory(self) -> None:
        """Cleanup in-memory limiter periodically without background tasks."""
        now = time.time()
        if now - self._last_cleanup >= 60:
            await self._memory_limiter.cleanup()
            self._last_cleanup = now
    
    def _get_client_key(self, request: Request, path_pattern: str) -> str:
        """
        Generate a unique key for the client.
        
        Uses combination of:
        - Client IP address
        - User ID (if authenticated)
        - Path pattern
        """
        # Get client IP (handle proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        
        # Create composite key
        key_parts = [client_ip, str(user_id or "anon"), path_pattern]
        key = ":".join(key_parts)
        
        return hashlib.sha256(key.encode()).hexdigest()[:32]
    
    def _match_rate_limit_config(self, path: str) -> tuple[str, RateLimitConfig]:
        """Return (matched_pattern, config) for the given path."""
        if path in self.rate_limits:
            return path, self.rate_limits[path]

        for pattern, config in sorted(
            self.rate_limits.items(),
            key=lambda x: -len(x[0]),  # Longest prefix first
        ):
            if path.startswith(pattern):
                return pattern, config

        return "*", RateLimitConfig()
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting."""
        if not self.enabled:
            return await call_next(request)
        
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            return await call_next(request)

        # Match config and compute client key based on matched pattern
        matched_pattern, config = self._match_rate_limit_config(path)
        client_key = self._get_client_key(request, matched_pattern)

        # Prefer Redis in production; allow in-memory fallback only outside production.
        use_redis = await self._ensure_redis_ok()
        if settings.is_production and not use_redis:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Rate limiter unavailable"},
            )

        if not use_redis:
            await self._maybe_cleanup_memory()

        # Check rate limit
        try:
            limiter = self._redis_limiter if use_redis else self._memory_limiter
            is_limited, retry_after = await limiter.is_rate_limited(client_key, config)
        except RuntimeError:
            if settings.is_production:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"detail": "Rate limiter unavailable"},
                )
            # Non-prod: fail open (no limit) if Redis limiter errors.
            is_limited, retry_after = False, None
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for client {client_key[:8]}... on {path}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(config.requests_per_minute),
                    "X-RateLimit-Reset": str(int(time.time()) + (retry_after or 60)),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        
        return response

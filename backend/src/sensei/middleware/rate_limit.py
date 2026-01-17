"""
Rate Limiting Middleware

Provides request rate limiting to protect against:
- Denial of Service (DoS) attacks
- Brute force attacks
- API abuse

Uses sliding window algorithm with Redis backend for distributed rate limiting.
Falls back to in-memory storage if Redis is unavailable.
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
DEFAULT_RATE_LIMITS: Dict[str, RateLimitConfig] = {
    # Auth endpoints - stricter limits to prevent brute force
    # But allow for shared office IPs and legitimate password failures
    "/api/v1/auth/login": RateLimitConfig(
        requests_per_minute=15,       # 15/min allows retries, typos
        requests_per_hour=60,         # 60/hr handles office IP sharing
        burst_size=5,                 # Allow rapid retries
        block_duration_seconds=180,   # 3 minute block (not 5)
    ),
    "/api/v1/auth/register": RateLimitConfig(
        requests_per_minute=10,       # Admin bulk creation support
        requests_per_hour=50,         # Onboarding events
        burst_size=3,
        block_duration_seconds=300,   # 5 minute block
    ),
    "/api/v1/auth/password-reset": RateLimitConfig(
        requests_per_minute=5,        # Slightly relaxed
        requests_per_hour=20,
        burst_size=2,
        block_duration_seconds=300,
    ),
    "/api/v1/auth/totp": RateLimitConfig(
        requests_per_minute=10,       # MFA can require retries
        requests_per_hour=60,
        burst_size=3,
        block_duration_seconds=180,
    ),
    # Search endpoints - power users search constantly
    "/api/v1/search": RateLimitConfig(
        requests_per_minute=120,      # 2/sec for typeahead
        requests_per_hour=3000,       # Heavy search users
        burst_size=20,                # Autocomplete bursts
    ),
    # Export endpoints - resource intensive but needed
    "/api/v1/export": RateLimitConfig(
        requests_per_minute=10,       # Doubled from 5
        requests_per_hour=100,        # Reports throughout day
        burst_size=3,
    ),
    # ML/AI endpoints - CPU intensive
    "/api/v1/ml": RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=200,
        burst_size=5,
    ),
    # Bulk operations - very resource intensive
    "/api/v1/bulk": RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=30,
        burst_size=2,
    ),
    # Default for all other API endpoints
    # ERP users make many requests: dashboard loads, list views, etc.
    "/api/v1": RateLimitConfig(
        requests_per_minute=200,      # ~3 req/sec sustained
        requests_per_hour=5000,       # Heavy users
        burst_size=30,                # Dashboard loads
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
        self.limiter = InMemoryRateLimiter()
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Periodically clean up old rate limit entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self.limiter.cleanup()
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")
    
    def _get_client_key(self, request: Request) -> str:
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
        key_parts = [client_ip, str(user_id or "anon"), request.url.path]
        key = ":".join(key_parts)
        
        return hashlib.sha256(key.encode()).hexdigest()[:32]
    
    def _get_rate_limit_config(self, path: str) -> RateLimitConfig:
        """Get rate limit config for the given path."""
        # Check for exact match first
        if path in self.rate_limits:
            return self.rate_limits[path]
        
        # Check for prefix match
        for pattern, config in sorted(
            self.rate_limits.items(), 
            key=lambda x: -len(x[0])  # Longest prefix first
        ):
            if path.startswith(pattern):
                return config
        
        # Default config
        return RateLimitConfig()
    
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
        
        # Get client key and config
        client_key = self._get_client_key(request)
        config = self._get_rate_limit_config(path)
        
        # Check rate limit
        is_limited, retry_after = await self.limiter.is_rate_limited(
            client_key, config
        )
        
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

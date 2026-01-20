"""
Per-Role Rate Limiting for AI Insights.

This module implements role-based rate limiting for insight queries:
- Different rate limits based on user role
- Hierarchical rate limit inheritance
- Burst allowance for occasional spikes
- Integration with audit logging
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict

from sensei.services.core.insight_audit_logger import (
    get_insight_audit_logger,
    AuditSeverity,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Rate Limit Configuration
# =============================================================================


@dataclass
class RateLimitConfig:
    """Configuration for role-based rate limiting."""
    
    # Requests per minute
    requests_per_minute: int
    
    # Requests per hour
    requests_per_hour: int
    
    # Burst allowance (extra requests allowed in short period)
    burst_allowance: int
    
    # Burst window in seconds
    burst_window_seconds: int = 10
    
    # Whether to log rate limit events
    log_events: bool = True
    
    # Whether to block or just warn on limit exceeded
    block_on_exceed: bool = True


# Default rate limits by role (from most to least privileged)
# Production-appropriate values that:
# - Support dashboard auto-refresh (5-10 second intervals)
# - Allow multiple concurrent users per shift
# - Enable real-time monitoring needs
# - Don't hide performance bottlenecks in development
# - Protect against runaway queries or abuse
DEFAULT_RATE_LIMITS: dict[str, RateLimitConfig] = {
    # Admin and CEO - High but not unlimited for oversight
    "admin": RateLimitConfig(
        requests_per_minute=500,    # Down from 10000 - still 8/sec
        requests_per_hour=5000,     # Down from 100000
        burst_allowance=50,         # Down from 500
        burst_window_seconds=5,
    ),
    "ceo": RateLimitConfig(
        requests_per_minute=500,    # Down from 10000
        requests_per_hour=5000,     # Down from 100000
        burst_allowance=50,         # Down from 500
        burst_window_seconds=5,
    ),
    
    # Executive roles - High limits for real-time dashboards
    "gm": RateLimitConfig(
        requests_per_minute=300,    # Down from 5000
        requests_per_hour=3000,     # Down from 50000
        burst_allowance=30,         # Down from 250
        burst_window_seconds=10,
    ),
    "exec": RateLimitConfig(
        requests_per_minute=200,    # Down from 3000
        requests_per_hour=2000,     # Down from 30000
        burst_allowance=20,         # Down from 150
        burst_window_seconds=10,
    ),
    
    # Department heads - Reasonable limits for operational monitoring
    "finance": RateLimitConfig(
        requests_per_minute=150,    # Down from 2000
        requests_per_hour=1500,     # Down from 20000
        burst_allowance=15,         # Down from 100
        burst_window_seconds=10,
    ),
    "hr": RateLimitConfig(
        requests_per_minute=150,    # Down from 2000
        requests_per_hour=1500,     # Down from 20000
        burst_allowance=15,         # Down from 100
        burst_window_seconds=10,
    ),
    "ops": RateLimitConfig(
        requests_per_minute=200,    # Down from 3000 - higher for production monitoring
        requests_per_hour=2000,     # Down from 30000
        burst_allowance=20,         # Down from 150
        burst_window_seconds=10,
    ),
    "quality": RateLimitConfig(
        requests_per_minute=200,    # Down from 3000 - higher for SPC monitoring
        requests_per_hour=2000,     # Down from 30000
        burst_allowance=20,         # Down from 150
        burst_window_seconds=10,
    ),
    "it": RateLimitConfig(
        requests_per_minute=150,    # Down from 2000
        requests_per_hour=1500,     # Down from 20000
        burst_allowance=15,         # Down from 100
        burst_window_seconds=10,
    ),
    
    # Specialized roles - Appropriate limits for daily work
    "accountant": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    "auditor": RateLimitConfig(
        requests_per_minute=120,    # Down from 1500
        requests_per_hour=1200,     # Down from 15000
        burst_allowance=12,         # Down from 100
        burst_window_seconds=10,
    ),
    "sales_engineer": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    "estimator": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    "sales": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    "purchasing": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    "supply_chain": RateLimitConfig(
        requests_per_minute=120,    # Down from 1500 - slightly higher for inventory
        requests_per_hour=1200,     # Down from 15000
        burst_allowance=12,         # Down from 100
        burst_window_seconds=10,
    ),
    "logistics": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    "warehouse": RateLimitConfig(
        requests_per_minute=120,    # Down from 1500 - slightly higher for inventory ops
        requests_per_hour=1200,     # Down from 15000
        burst_allowance=12,         # Down from 100
        burst_window_seconds=10,
    ),
    "maintenance": RateLimitConfig(
        requests_per_minute=150,    # Down from 2000 - higher for equipment monitoring
        requests_per_hour=1500,     # Down from 20000
        burst_allowance=15,         # Down from 100
        burst_window_seconds=10,
    ),
    "engineering": RateLimitConfig(
        requests_per_minute=120,    # Down from 1500
        requests_per_hour=1200,     # Down from 15000
        burst_allowance=12,         # Down from 100
        burst_window_seconds=10,
    ),
    
    # Supervisory roles - Good limits for shift management
    "supervisor": RateLimitConfig(
        requests_per_minute=120,    # Down from 1500
        requests_per_hour=1200,     # Down from 15000
        burst_allowance=12,         # Down from 100
        burst_window_seconds=10,
    ),
    "team_lead": RateLimitConfig(
        requests_per_minute=100,    # Down from 1000
        requests_per_hour=1000,     # Down from 10000
        burst_allowance=10,         # Down from 75
        burst_window_seconds=10,
    ),
    
    # Operational roles - Reasonable for shop floor use
    "operator": RateLimitConfig(
        requests_per_minute=60,     # Down from 500 - 1 per second
        requests_per_hour=600,      # Down from 5000
        burst_allowance=10,         # Down from 50
        burst_window_seconds=10,
    ),
    
    # Viewer - Limited but functional for dashboards
    "viewer": RateLimitConfig(
        requests_per_minute=30,     # Down from 300
        requests_per_hour=300,      # Down from 3000,
        burst_allowance=30,
        burst_window_seconds=10,
    ),
}

# Default for unknown roles
DEFAULT_RATE_LIMIT = RateLimitConfig(
    requests_per_minute=20,
    requests_per_hour=200,
    burst_allowance=5,
    burst_window_seconds=10,
)


# =============================================================================
# Rate Limit Result
# =============================================================================


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    
    allowed: bool
    user_id: str
    role: str
    
    # Current usage
    requests_this_minute: int
    requests_this_hour: int
    burst_count: int
    
    # Limits
    limit_per_minute: int
    limit_per_hour: int
    burst_limit: int
    
    # Exceeded info
    exceeded_minute_limit: bool = False
    exceeded_hour_limit: bool = False
    exceeded_burst_limit: bool = False
    
    # Timing
    retry_after_seconds: Optional[int] = None
    
    @property
    def minute_usage_percent(self) -> float:
        """Get minute limit usage as percentage."""
        if self.limit_per_minute == 0:
            return 0.0
        return (self.requests_this_minute / self.limit_per_minute) * 100
    
    @property
    def hour_usage_percent(self) -> float:
        """Get hour limit usage as percentage."""
        if self.limit_per_hour == 0:
            return 0.0
        return (self.requests_this_hour / self.limit_per_hour) * 100


# =============================================================================
# Rate Limiter Service
# =============================================================================


class InsightRateLimiter:
    """
    Role-based rate limiter for insight queries.
    
    Features:
    - Per-minute and per-hour limits
    - Burst allowance for spikes
    - Role hierarchy (uses most privileged role)
    - Integration with audit logging
    """
    
    def __init__(
        self,
        rate_limits: Optional[dict[str, RateLimitConfig]] = None,
        default_limit: Optional[RateLimitConfig] = None,
        enable_audit_logging: bool = True,
    ):
        self.rate_limits = rate_limits or DEFAULT_RATE_LIMITS.copy()
        self.default_limit = default_limit or DEFAULT_RATE_LIMIT
        self.enable_audit_logging = enable_audit_logging
        
        # Request tracking: user_id -> list of timestamps
        self._minute_requests: dict[str, list[datetime]] = defaultdict(list)
        self._hour_requests: dict[str, list[datetime]] = defaultdict(list)
        self._burst_requests: dict[str, list[datetime]] = defaultdict(list)
    
    def get_rate_limit_for_role(self, role: str) -> RateLimitConfig:
        """Get rate limit configuration for a role."""
        return self.rate_limits.get(role.lower(), self.default_limit)
    
    def get_best_rate_limit(self, roles: list[str]) -> tuple[str, RateLimitConfig]:
        """
        Get the best (highest) rate limit from a list of roles.
        
        Returns:
            Tuple of (best_role, config)
        """
        best_role = None
        best_config = self.default_limit
        best_minute_limit = 0
        
        for role in roles:
            config = self.get_rate_limit_for_role(role)
            if config.requests_per_minute > best_minute_limit:
                best_minute_limit = config.requests_per_minute
                best_config = config
                best_role = role
        
        return best_role or "unknown", best_config
    
    def check_rate_limit(
        self,
        user_id: str,
        user_roles: list[str],
        ip_address: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check if a user is within rate limits.
        
        Args:
            user_id: User ID
            user_roles: User's roles
            ip_address: Client IP (for logging)
            
        Returns:
            RateLimitResult with decision and usage info
        """
        now = _utcnow()
        
        # Get best rate limit config for user's roles
        best_role, config = self.get_best_rate_limit(user_roles)
        
        # Clean up old requests
        self._cleanup_old_requests(user_id, now, config)
        
        # Count current requests
        minute_count = len(self._minute_requests[user_id])
        hour_count = len(self._hour_requests[user_id])
        burst_count = len(self._burst_requests[user_id])
        
        # Check limits
        exceeded_minute = minute_count >= config.requests_per_minute
        exceeded_hour = hour_count >= config.requests_per_hour
        exceeded_burst = burst_count >= config.burst_allowance
        
        allowed = not (exceeded_minute or exceeded_hour)
        
        # Calculate retry-after if blocked
        retry_after = None
        if not allowed:
            if exceeded_minute:
                # Wait until oldest minute request expires
                oldest = min(self._minute_requests[user_id]) if self._minute_requests[user_id] else now
                retry_after = 60 - int((now - oldest).total_seconds())
            elif exceeded_hour:
                oldest = min(self._hour_requests[user_id]) if self._hour_requests[user_id] else now
                retry_after = 3600 - int((now - oldest).total_seconds())
        
        result = RateLimitResult(
            allowed=allowed,
            user_id=user_id,
            role=best_role,
            requests_this_minute=minute_count,
            requests_this_hour=hour_count,
            burst_count=burst_count,
            limit_per_minute=config.requests_per_minute,
            limit_per_hour=config.requests_per_hour,
            burst_limit=config.burst_allowance,
            exceeded_minute_limit=exceeded_minute,
            exceeded_hour_limit=exceeded_hour,
            exceeded_burst_limit=exceeded_burst,
            retry_after_seconds=max(1, retry_after) if retry_after else None,
        )
        
        # Log if exceeded
        if not allowed and self.enable_audit_logging and config.log_events:
            audit_logger = get_insight_audit_logger()
            audit_logger.log_rate_limit_exceeded(
                user_id=user_id,
                user_roles=user_roles,
                request_count=minute_count if exceeded_minute else hour_count,
                window_seconds=60 if exceeded_minute else 3600,
                ip_address=ip_address,
            )
        
        return result
    
    def record_request(self, user_id: str) -> None:
        """
        Record a request for rate limiting.
        
        Should be called after check_rate_limit() if the request is allowed.
        """
        now = _utcnow()
        
        self._minute_requests[user_id].append(now)
        self._hour_requests[user_id].append(now)
        self._burst_requests[user_id].append(now)
    
    def get_usage_stats(self, user_id: str, user_roles: list[str]) -> dict:
        """
        Get current usage statistics for a user.
        
        Returns:
            Dictionary with usage stats and limits
        """
        now = _utcnow()
        best_role, config = self.get_best_rate_limit(user_roles)
        
        self._cleanup_old_requests(user_id, now, config)
        
        return {
            "user_id": user_id,
            "effective_role": best_role,
            "minute": {
                "used": len(self._minute_requests[user_id]),
                "limit": config.requests_per_minute,
                "remaining": max(0, config.requests_per_minute - len(self._minute_requests[user_id])),
            },
            "hour": {
                "used": len(self._hour_requests[user_id]),
                "limit": config.requests_per_hour,
                "remaining": max(0, config.requests_per_hour - len(self._hour_requests[user_id])),
            },
            "burst": {
                "used": len(self._burst_requests[user_id]),
                "limit": config.burst_allowance,
                "window_seconds": config.burst_window_seconds,
            },
        }
    
    def reset_user_limits(self, user_id: str) -> None:
        """Reset rate limits for a specific user (admin action)."""
        self._minute_requests[user_id] = []
        self._hour_requests[user_id] = []
        self._burst_requests[user_id] = []
        
        logger.info(f"Rate limits reset for user {user_id}")
    
    def update_role_limit(self, role: str, config: RateLimitConfig) -> None:
        """Update rate limit configuration for a role."""
        self.rate_limits[role.lower()] = config
        logger.info(f"Rate limit updated for role {role}")
    
    def _cleanup_old_requests(
        self,
        user_id: str,
        now: datetime,
        config: RateLimitConfig,
    ) -> None:
        """Remove expired request timestamps."""
        # Minute window
        minute_cutoff = datetime(
            now.year, now.month, now.day, now.hour,
            now.minute - 1 if now.minute > 0 else 59,
            now.second, tzinfo=None
        )
        self._minute_requests[user_id] = [
            ts for ts in self._minute_requests[user_id]
            if ts >= minute_cutoff
        ]
        
        # Hour window
        hour_cutoff = datetime(
            now.year, now.month, now.day,
            now.hour - 1 if now.hour > 0 else 23,
            now.minute, now.second, tzinfo=None
        )
        self._hour_requests[user_id] = [
            ts for ts in self._hour_requests[user_id]
            if ts >= hour_cutoff
        ]
        
        # Burst window
        burst_cutoff = datetime(
            now.year, now.month, now.day, now.hour, now.minute,
            max(0, now.second - config.burst_window_seconds),
            tzinfo=None
        )
        self._burst_requests[user_id] = [
            ts for ts in self._burst_requests[user_id]
            if ts >= burst_cutoff
        ]


# =============================================================================
# FastAPI Dependency
# =============================================================================


_rate_limiter: Optional[InsightRateLimiter] = None


def get_insight_rate_limiter() -> InsightRateLimiter:
    """Get the singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InsightRateLimiter()
    return _rate_limiter


def configure_insight_rate_limiter(
    rate_limits: Optional[dict[str, RateLimitConfig]] = None,
    default_limit: Optional[RateLimitConfig] = None,
    enable_audit_logging: bool = True,
) -> InsightRateLimiter:
    """Configure and return the rate limiter (call during app startup)."""
    global _rate_limiter
    _rate_limiter = InsightRateLimiter(
        rate_limits=rate_limits,
        default_limit=default_limit,
        enable_audit_logging=enable_audit_logging,
    )
    return _rate_limiter


async def check_insight_rate_limit(
    user_id: str,
    user_roles: list[str],
    ip_address: Optional[str] = None,
) -> RateLimitResult:
    """
    FastAPI dependency for checking insight rate limits.
    
    Usage:
        @router.get("/insights")
        async def get_insights(
            rate_limit: RateLimitResult = Depends(check_insight_rate_limit),
        ):
            if not rate_limit.allowed:
                raise HTTPException(429, detail="Rate limit exceeded")
            ...
    """
    limiter = get_insight_rate_limiter()
    result = limiter.check_rate_limit(user_id, user_roles, ip_address)
    
    if result.allowed:
        limiter.record_request(user_id)
    
    return result

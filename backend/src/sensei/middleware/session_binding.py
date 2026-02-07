"""
Session Binding Middleware

Implements session binding to prevent session hijacking by tying sessions
to device fingerprints. This provides defense-in-depth against stolen
session tokens.

Security Features:
- Device fingerprinting based on User-Agent and IP subnet
- Fingerprint validation on every authenticated request
- Configurable strictness levels
- Audit logging for suspicious activity
"""

import hashlib
import hmac
import logging
from typing import Optional, Tuple
from ipaddress import ip_address, IPv4Address, IPv6Address

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from sensei.core.config import settings

logger = logging.getLogger(__name__)


class SessionBindingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that binds sessions to device fingerprints.
    
    This helps prevent session hijacking by verifying that requests
    come from the same device/network that originally authenticated.
    
    The fingerprint includes:
    - User-Agent header (browser/device identifier)
    - IP subnet (allows for minor IP changes within same network)
    
    The fingerprint is salted and hashed for storage.
    """
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        salt: str = "",
        strict_ip: bool = False,
        exempt_paths: Optional[list[str]] = None,
    ):
        """
        Initialize session binding middleware.
        
        Args:
            app: ASGI application
            enabled: Whether to enforce session binding
            salt: Salt for fingerprint hashing
            strict_ip: If True, require exact IP match. If False, allow subnet
            exempt_paths: Paths to exempt from binding (e.g., public endpoints)
        """
        super().__init__(app)
        self.enabled = enabled
        self.salt = salt or settings.SESSION_FINGERPRINT_SALT
        self.strict_ip = strict_ip
        self.exempt_paths = exempt_paths or [
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP, handling proxies."""
        # Check X-Forwarded-For header (set by reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _normalize_ip_for_binding(self, ip_str: str) -> str:
        """
        Normalize IP for binding, optionally using subnet.
        
        For IPv4: Use /24 subnet (allows last octet to change)
        For IPv6: Use /48 subnet (allows host portion to change)
        
        This allows for minor IP changes (e.g., mobile networks) while
        still detecting major network changes.
        """
        if self.strict_ip:
            return ip_str
        
        try:
            ip = ip_address(ip_str)
            
            if isinstance(ip, IPv4Address):
                # Use /24 subnet - e.g., 192.168.1.x -> 192.168.1.0
                octets = ip_str.split(".")
                if len(octets) == 4:
                    return f"{octets[0]}.{octets[1]}.{octets[2]}.0"
            elif isinstance(ip, IPv6Address):
                # Use /48 subnet - keep first 3 groups
                groups = ip_str.split(":")
                if len(groups) >= 3:
                    return ":".join(groups[:3]) + "::0"
            
            return ip_str
        except ValueError:
            return ip_str
    
    def _extract_fingerprint_components(
        self, request: Request
    ) -> Tuple[str, str]:
        """
        Extract fingerprint components from request.
        
        Returns:
            Tuple of (user_agent, normalized_ip)
        """
        user_agent = request.headers.get("User-Agent", "unknown")
        client_ip = self._get_client_ip(request)
        normalized_ip = self._normalize_ip_for_binding(client_ip)
        
        return user_agent, normalized_ip
    
    def compute_fingerprint(self, request: Request) -> str:
        """
        Compute a fingerprint hash for the current request.
        
        The fingerprint is computed as:
        HMAC-SHA256(salt, user_agent + "|" + normalized_ip)
        
        This provides:
        - Privacy (can't reverse to get original values)
        - Integrity (can't be forged without salt)
        - Consistency (same inputs = same output)
        """
        user_agent, normalized_ip = self._extract_fingerprint_components(request)
        
        # Combine components
        data = f"{user_agent}|{normalized_ip}"
        
        # Compute HMAC
        fingerprint = hmac.new(
            self.salt.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return fingerprint[:32]  # Use first 32 chars (128 bits)
    
    def _should_skip(self, request: Request) -> bool:
        """Check if request should skip session binding."""
        # Skip if disabled
        if not self.enabled:
            return True
        
        # Skip exempt paths
        path = request.url.path
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                return True
        
        return False
    
    def _get_session_fingerprint(self, request: Request) -> Optional[str]:
        """
        Get the fingerprint stored in the session/token.
        
        The fingerprint should be stored when the user authenticates
        and included in the JWT token or session data.
        """
        # Check for fingerprint in request state (set by auth middleware)
        if hasattr(request.state, "session_fingerprint"):
            return request.state.session_fingerprint
        
        # Check for fingerprint header (set by frontend from stored token)
        fingerprint_header = request.headers.get("X-Session-Fingerprint")
        if fingerprint_header:
            return fingerprint_header
        
        return None
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with session binding validation."""
        
        # Skip certain paths
        if self._should_skip(request):
            return await call_next(request)
        
        # Compute current fingerprint
        current_fingerprint = self.compute_fingerprint(request)
        
        # Store for use by auth/other middleware
        request.state.current_fingerprint = current_fingerprint
        
        # Get stored fingerprint (if authenticated)
        stored_fingerprint = self._get_session_fingerprint(request)
        
        if stored_fingerprint:
            # Validate fingerprint match
            if not hmac.compare_digest(current_fingerprint, stored_fingerprint):
                # Fingerprint mismatch - potential session hijacking
                user_agent, client_ip = self._extract_fingerprint_components(request)
                
                logger.warning(
                    "Session fingerprint mismatch - potential hijacking attempt",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "client_ip": client_ip,
                        "user_agent": user_agent[:100],  # Truncate for logging
                        "expected_fingerprint": stored_fingerprint[:8] + "...",
                        "actual_fingerprint": current_fingerprint[:8] + "...",
                    }
                )
                
                # In production, reject the request
                if settings.ENVIRONMENT == "production":
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "Session binding validation failed. Please log in again.",
                            "code": "SESSION_BINDING_FAILED"
                        }
                    )
                else:
                    # In development, just log a warning
                    logger.warning(
                        "Session binding mismatch (not enforced in development)"
                    )
        
        response = await call_next(request)
        return response


def get_fingerprint_for_token(request: Request) -> str:
    """
    Get fingerprint to include in JWT token during authentication.
    
    Call this during login to get the fingerprint that should be
    stored in the user's JWT token.
    
    Args:
        request: The login request
        
    Returns:
        Fingerprint string to store in token
    """
    middleware = SessionBindingMiddleware(
        app=None,  # Not used for fingerprint computation
        salt=settings.SESSION_FINGERPRINT_SALT,
    )
    return middleware.compute_fingerprint(request)

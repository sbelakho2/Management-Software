"""
Secure Headers Middleware.

Adds security headers to HTTP responses to protect against common attacks:
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security (HSTS)
- Referrer-Policy
- Permissions-Policy
- Cache-Control for sensitive data
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class CSPDirective(str, Enum):
    """Content Security Policy directives."""

    DEFAULT_SRC = "default-src"
    SCRIPT_SRC = "script-src"
    STYLE_SRC = "style-src"
    IMG_SRC = "img-src"
    FONT_SRC = "font-src"
    CONNECT_SRC = "connect-src"
    MEDIA_SRC = "media-src"
    OBJECT_SRC = "object-src"
    FRAME_SRC = "frame-src"
    FRAME_ANCESTORS = "frame-ancestors"
    BASE_URI = "base-uri"
    FORM_ACTION = "form-action"
    WORKER_SRC = "worker-src"
    MANIFEST_SRC = "manifest-src"
    REPORT_URI = "report-uri"
    REPORT_TO = "report-to"
    UPGRADE_INSECURE_REQUESTS = "upgrade-insecure-requests"


class XFrameOption(str, Enum):
    """X-Frame-Options values."""

    DENY = "DENY"
    SAMEORIGIN = "SAMEORIGIN"


class ReferrerPolicy(str, Enum):
    """Referrer-Policy values."""

    NO_REFERRER = "no-referrer"
    NO_REFERRER_WHEN_DOWNGRADE = "no-referrer-when-downgrade"
    ORIGIN = "origin"
    ORIGIN_WHEN_CROSS_ORIGIN = "origin-when-cross-origin"
    SAME_ORIGIN = "same-origin"
    STRICT_ORIGIN = "strict-origin"
    STRICT_ORIGIN_WHEN_CROSS_ORIGIN = "strict-origin-when-cross-origin"
    UNSAFE_URL = "unsafe-url"


@dataclass
class CSPConfig:
    """Content Security Policy configuration."""

    directives: dict[CSPDirective, list[str]] = field(default_factory=dict)
    report_only: bool = False

    def add_directive(self, directive: CSPDirective, *sources: str) -> "CSPConfig":
        """Add sources to a directive."""
        if directive not in self.directives:
            self.directives[directive] = []
        self.directives[directive].extend(sources)
        return self

    def to_header(self) -> str:
        """Convert to header value string."""
        parts = []
        for directive, sources in self.directives.items():
            if sources:
                parts.append(f"{directive.value} {' '.join(sources)}")
            else:
                parts.append(directive.value)
        return "; ".join(parts)


@dataclass
class HSTSConfig:
    """HTTP Strict Transport Security configuration."""

    max_age: int = 31536000  # 1 year
    include_subdomains: bool = True
    preload: bool = False

    def to_header(self) -> str:
        """Convert to header value string."""
        parts = [f"max-age={self.max_age}"]
        if self.include_subdomains:
            parts.append("includeSubDomains")
        if self.preload:
            parts.append("preload")
        return "; ".join(parts)


@dataclass
class PermissionsPolicyConfig:
    """Permissions Policy (formerly Feature Policy) configuration."""

    features: dict[str, list[str]] = field(default_factory=dict)

    def add_feature(self, feature: str, *allowlist: str) -> "PermissionsPolicyConfig":
        """Add a feature policy."""
        self.features[feature] = list(allowlist)
        return self

    def disable_feature(self, feature: str) -> "PermissionsPolicyConfig":
        """Disable a feature completely."""
        self.features[feature] = []
        return self

    def to_header(self) -> str:
        """Convert to header value string."""
        parts = []
        for feature, allowlist in self.features.items():
            if allowlist:
                parts.append(f"{feature}=({' '.join(allowlist)})")
            else:
                parts.append(f"{feature}=()")
        return ", ".join(parts)


@dataclass
class CacheControlConfig:
    """Cache-Control configuration."""

    no_store: bool = False
    no_cache: bool = False
    private: bool = False
    public: bool = False
    max_age: int | None = None
    s_maxage: int | None = None
    must_revalidate: bool = False
    proxy_revalidate: bool = False
    immutable: bool = False

    def to_header(self) -> str:
        """Convert to header value string."""
        parts = []
        if self.no_store:
            parts.append("no-store")
        if self.no_cache:
            parts.append("no-cache")
        if self.private:
            parts.append("private")
        if self.public:
            parts.append("public")
        if self.max_age is not None:
            parts.append(f"max-age={self.max_age}")
        if self.s_maxage is not None:
            parts.append(f"s-maxage={self.s_maxage}")
        if self.must_revalidate:
            parts.append("must-revalidate")
        if self.proxy_revalidate:
            parts.append("proxy-revalidate")
        if self.immutable:
            parts.append("immutable")
        return ", ".join(parts)


@dataclass
class HeaderOverride:
    """Per-route header override."""

    id: UUID
    path_pattern: str
    method: str | None  # None means all methods
    headers: dict[str, str | None]  # None means remove header
    is_active: bool
    description: str
    created_at: datetime


@dataclass
class CSPViolationReport:
    """CSP violation report."""

    id: UUID
    document_uri: str
    referrer: str | None
    violated_directive: str
    blocked_uri: str
    source_file: str | None
    line_number: int | None
    column_number: int | None
    reported_at: datetime
    user_agent: str | None


class SecureHeadersMiddleware:
    """Middleware for adding security headers to responses."""

    def __init__(self) -> None:
        """Initialize the secure headers middleware."""
        self._csp: CSPConfig | None = None
        self._hsts: HSTSConfig | None = None
        self._permissions: PermissionsPolicyConfig | None = None
        self._x_frame_options: XFrameOption | None = None
        self._referrer_policy: ReferrerPolicy | None = None
        self._x_content_type_options: bool = True
        self._x_xss_protection: bool = True
        self._cache_control: CacheControlConfig | None = None

        self._overrides: dict[UUID, HeaderOverride] = {}
        self._violations: list[CSPViolationReport] = []

        self._header_stats: dict[str, int] = {}
        self._is_enabled: bool = True

        # Initialize defaults
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default security headers."""
        # Default CSP
        self._csp = CSPConfig()
        self._csp.add_directive(CSPDirective.DEFAULT_SRC, "'self'")
        self._csp.add_directive(CSPDirective.SCRIPT_SRC, "'self'")
        self._csp.add_directive(CSPDirective.STYLE_SRC, "'self'", "'unsafe-inline'")
        self._csp.add_directive(CSPDirective.IMG_SRC, "'self'", "data:", "https:")
        self._csp.add_directive(CSPDirective.FONT_SRC, "'self'", "https:")
        self._csp.add_directive(CSPDirective.CONNECT_SRC, "'self'")
        self._csp.add_directive(CSPDirective.FRAME_ANCESTORS, "'none'")
        self._csp.add_directive(CSPDirective.BASE_URI, "'self'")
        self._csp.add_directive(CSPDirective.FORM_ACTION, "'self'")
        self._csp.add_directive(CSPDirective.OBJECT_SRC, "'none'")

        # Default HSTS
        self._hsts = HSTSConfig(
            max_age=31536000,
            include_subdomains=True,
            preload=False,
        )

        # Default Permissions Policy
        self._permissions = PermissionsPolicyConfig()
        self._permissions.disable_feature("camera")
        self._permissions.disable_feature("microphone")
        self._permissions.disable_feature("geolocation")
        self._permissions.disable_feature("payment")
        self._permissions.add_feature("fullscreen", "'self'")

        # Default other headers
        self._x_frame_options = XFrameOption.DENY
        self._referrer_policy = ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN
        self._x_content_type_options = True
        self._x_xss_protection = True

        # Default cache control for sensitive data
        self._cache_control = CacheControlConfig(
            no_store=True,
            no_cache=True,
            private=True,
            must_revalidate=True,
        )

    # Configuration Methods

    def set_csp(self, csp: CSPConfig) -> None:
        """Set Content Security Policy."""
        self._csp = csp

    def get_csp(self) -> CSPConfig | None:
        """Get current CSP configuration."""
        return self._csp

    def set_hsts(self, hsts: HSTSConfig) -> None:
        """Set HSTS configuration."""
        self._hsts = hsts

    def get_hsts(self) -> HSTSConfig | None:
        """Get current HSTS configuration."""
        return self._hsts

    def set_permissions_policy(self, policy: PermissionsPolicyConfig) -> None:
        """Set Permissions Policy."""
        self._permissions = policy

    def get_permissions_policy(self) -> PermissionsPolicyConfig | None:
        """Get current Permissions Policy."""
        return self._permissions

    def set_x_frame_options(self, option: XFrameOption | None) -> None:
        """Set X-Frame-Options."""
        self._x_frame_options = option

    def get_x_frame_options(self) -> XFrameOption | None:
        """Get current X-Frame-Options."""
        return self._x_frame_options

    def set_referrer_policy(self, policy: ReferrerPolicy | None) -> None:
        """Set Referrer-Policy."""
        self._referrer_policy = policy

    def get_referrer_policy(self) -> ReferrerPolicy | None:
        """Get current Referrer-Policy."""
        return self._referrer_policy

    def set_x_content_type_options(self, enabled: bool) -> None:
        """Enable/disable X-Content-Type-Options."""
        self._x_content_type_options = enabled

    def get_x_content_type_options(self) -> bool:
        """Get X-Content-Type-Options status."""
        return self._x_content_type_options

    def set_x_xss_protection(self, enabled: bool) -> None:
        """Enable/disable X-XSS-Protection."""
        self._x_xss_protection = enabled

    def get_x_xss_protection(self) -> bool:
        """Get X-XSS-Protection status."""
        return self._x_xss_protection

    def set_cache_control(self, config: CacheControlConfig | None) -> None:
        """Set default Cache-Control."""
        self._cache_control = config

    def get_cache_control(self) -> CacheControlConfig | None:
        """Get current Cache-Control configuration."""
        return self._cache_control

    def enable(self) -> None:
        """Enable the middleware."""
        self._is_enabled = True

    def disable(self) -> None:
        """Disable the middleware."""
        self._is_enabled = False

    def is_enabled(self) -> bool:
        """Check if middleware is enabled."""
        return self._is_enabled

    # CSP Configuration Helpers

    def add_csp_source(self, directive: CSPDirective, *sources: str) -> None:
        """Add sources to a CSP directive."""
        if self._csp is None:
            self._csp = CSPConfig()
        self._csp.add_directive(directive, *sources)

    def set_csp_report_only(self, report_only: bool) -> None:
        """Set CSP to report-only mode."""
        if self._csp:
            self._csp.report_only = report_only

    def add_csp_nonce(self, nonce: str) -> None:
        """Add a nonce to script-src and style-src."""
        if self._csp:
            nonce_value = f"'nonce-{nonce}'"
            self._csp.add_directive(CSPDirective.SCRIPT_SRC, nonce_value)
            self._csp.add_directive(CSPDirective.STYLE_SRC, nonce_value)

    # Header Override Management

    def add_override(
        self,
        path_pattern: str,
        headers: dict[str, str | None],
        method: str | None = None,
        description: str = "",
    ) -> HeaderOverride:
        """Add a per-route header override."""
        override = HeaderOverride(
            id=uuid4(),
            path_pattern=path_pattern,
            method=method,
            headers=headers,
            is_active=True,
            description=description,
            created_at=datetime.now(timezone.utc),
        )

        self._overrides[override.id] = override
        return override

    def get_override(self, override_id: UUID) -> HeaderOverride | None:
        """Get an override by ID."""
        return self._overrides.get(override_id)

    def get_overrides(
        self, path_pattern: str | None = None, active_only: bool = True
    ) -> list[HeaderOverride]:
        """Get overrides with optional filters."""
        overrides = []

        for override in self._overrides.values():
            if active_only and not override.is_active:
                continue
            if path_pattern and override.path_pattern != path_pattern:
                continue
            overrides.append(override)

        return overrides

    def update_override(
        self,
        override_id: UUID,
        headers: dict[str, str | None] | None = None,
        is_active: bool | None = None,
    ) -> HeaderOverride | None:
        """Update an override."""
        override = self._overrides.get(override_id)
        if not override:
            return None

        if headers is not None:
            override.headers = headers
        if is_active is not None:
            override.is_active = is_active

        return override

    def remove_override(self, override_id: UUID) -> bool:
        """Remove an override."""
        if override_id in self._overrides:
            del self._overrides[override_id]
            return True
        return False

    # Header Generation

    def generate_headers(
        self,
        path: str = "/",
        method: str = "GET",
    ) -> dict[str, str]:
        """Generate security headers for a response."""
        if not self._is_enabled:
            return {}

        headers: dict[str, str] = {}

        # Content-Security-Policy
        if self._csp:
            header_name = (
                "Content-Security-Policy-Report-Only"
                if self._csp.report_only
                else "Content-Security-Policy"
            )
            headers[header_name] = self._csp.to_header()
            self._record_stat(header_name)

        # Strict-Transport-Security
        if self._hsts:
            headers["Strict-Transport-Security"] = self._hsts.to_header()
            self._record_stat("Strict-Transport-Security")

        # Permissions-Policy
        if self._permissions:
            headers["Permissions-Policy"] = self._permissions.to_header()
            self._record_stat("Permissions-Policy")

        # X-Frame-Options
        if self._x_frame_options:
            headers["X-Frame-Options"] = self._x_frame_options.value
            self._record_stat("X-Frame-Options")

        # Referrer-Policy
        if self._referrer_policy:
            headers["Referrer-Policy"] = self._referrer_policy.value
            self._record_stat("Referrer-Policy")

        # X-Content-Type-Options
        if self._x_content_type_options:
            headers["X-Content-Type-Options"] = "nosniff"
            self._record_stat("X-Content-Type-Options")

        # X-XSS-Protection
        if self._x_xss_protection:
            headers["X-XSS-Protection"] = "1; mode=block"
            self._record_stat("X-XSS-Protection")

        # Cache-Control
        if self._cache_control:
            headers["Cache-Control"] = self._cache_control.to_header()
            self._record_stat("Cache-Control")

        # Apply overrides
        headers = self._apply_overrides(headers, path, method)

        return headers

    def _apply_overrides(
        self,
        headers: dict[str, str],
        path: str,
        method: str,
    ) -> dict[str, str]:
        """Apply per-route header overrides."""
        import re

        for override in self._overrides.values():
            if not override.is_active:
                continue

            # Check method match
            if override.method and override.method.upper() != method.upper():
                continue

            # Check path match (simple glob-like matching)
            pattern = override.path_pattern.replace("*", ".*")
            if not re.match(f"^{pattern}$", path):
                continue

            # Apply header modifications
            for header_name, header_value in override.headers.items():
                if header_value is None:
                    headers.pop(header_name, None)
                else:
                    headers[header_name] = header_value

        return headers

    def _record_stat(self, header_name: str) -> None:
        """Record header usage statistics."""
        self._header_stats[header_name] = self._header_stats.get(header_name, 0) + 1

    # CSP Violation Reporting

    def report_csp_violation(
        self,
        document_uri: str,
        violated_directive: str,
        blocked_uri: str,
        referrer: str | None = None,
        source_file: str | None = None,
        line_number: int | None = None,
        column_number: int | None = None,
        user_agent: str | None = None,
    ) -> CSPViolationReport:
        """Report a CSP violation."""
        report = CSPViolationReport(
            id=uuid4(),
            document_uri=document_uri,
            referrer=referrer,
            violated_directive=violated_directive,
            blocked_uri=blocked_uri,
            source_file=source_file,
            line_number=line_number,
            column_number=column_number,
            reported_at=datetime.now(timezone.utc),
            user_agent=user_agent,
        )

        self._violations.append(report)
        return report

    def get_csp_violations(
        self,
        directive: str | None = None,
        limit: int = 100,
    ) -> list[CSPViolationReport]:
        """Get CSP violation reports."""
        violations = self._violations

        if directive:
            violations = [v for v in violations if v.violated_directive == directive]

        # Sort by most recent
        violations = sorted(violations, key=lambda v: v.reported_at, reverse=True)

        return violations[:limit]

    def get_violation_stats(self) -> dict[str, int]:
        """Get CSP violation statistics by directive."""
        stats: dict[str, int] = {}

        for violation in self._violations:
            directive = violation.violated_directive
            stats[directive] = stats.get(directive, 0) + 1

        return stats

    def clear_violations(self) -> int:
        """Clear all violation reports."""
        count = len(self._violations)
        self._violations = []
        return count

    # Preset Configurations

    def apply_strict_preset(self) -> None:
        """Apply strict security preset."""
        # Strict CSP
        self._csp = CSPConfig()
        self._csp.add_directive(CSPDirective.DEFAULT_SRC, "'none'")
        self._csp.add_directive(CSPDirective.SCRIPT_SRC, "'self'")
        self._csp.add_directive(CSPDirective.STYLE_SRC, "'self'")
        self._csp.add_directive(CSPDirective.IMG_SRC, "'self'")
        self._csp.add_directive(CSPDirective.FONT_SRC, "'self'")
        self._csp.add_directive(CSPDirective.CONNECT_SRC, "'self'")
        self._csp.add_directive(CSPDirective.FRAME_ANCESTORS, "'none'")
        self._csp.add_directive(CSPDirective.BASE_URI, "'self'")
        self._csp.add_directive(CSPDirective.FORM_ACTION, "'self'")
        self._csp.add_directive(CSPDirective.OBJECT_SRC, "'none'")
        self._csp.add_directive(CSPDirective.UPGRADE_INSECURE_REQUESTS)

        # Strict HSTS
        self._hsts = HSTSConfig(
            max_age=63072000,  # 2 years
            include_subdomains=True,
            preload=True,
        )

        # Strict X-Frame-Options
        self._x_frame_options = XFrameOption.DENY

        # Strict Referrer
        self._referrer_policy = ReferrerPolicy.NO_REFERRER

        # Strict cache
        self._cache_control = CacheControlConfig(
            no_store=True,
            no_cache=True,
            private=True,
            must_revalidate=True,
        )

    def apply_relaxed_preset(self) -> None:
        """Apply relaxed security preset (for development)."""
        # More permissive CSP
        self._csp = CSPConfig()
        self._csp.add_directive(CSPDirective.DEFAULT_SRC, "'self'", "'unsafe-inline'", "'unsafe-eval'")
        self._csp.add_directive(CSPDirective.SCRIPT_SRC, "'self'", "'unsafe-inline'", "'unsafe-eval'")
        self._csp.add_directive(CSPDirective.STYLE_SRC, "'self'", "'unsafe-inline'")
        self._csp.add_directive(CSPDirective.IMG_SRC, "'self'", "data:", "blob:", "https:", "http:")
        self._csp.add_directive(CSPDirective.CONNECT_SRC, "'self'", "ws:", "wss:", "http:", "https:")

        # Shorter HSTS
        self._hsts = HSTSConfig(max_age=86400, include_subdomains=False)

        # Allow framing from same origin
        self._x_frame_options = XFrameOption.SAMEORIGIN

        # More permissive referrer
        self._referrer_policy = ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN

    def apply_api_preset(self) -> None:
        """Apply preset for API endpoints."""
        # Minimal CSP for API
        self._csp = CSPConfig()
        self._csp.add_directive(CSPDirective.DEFAULT_SRC, "'none'")
        self._csp.add_directive(CSPDirective.FRAME_ANCESTORS, "'none'")

        # Standard HSTS
        self._hsts = HSTSConfig(
            max_age=31536000,
            include_subdomains=True,
        )

        # Strict X-Frame-Options
        self._x_frame_options = XFrameOption.DENY

        # No cache for API responses
        self._cache_control = CacheControlConfig(
            no_store=True,
            no_cache=True,
            private=True,
        )

    # Statistics and Summary

    def get_header_stats(self) -> dict[str, int]:
        """Get header usage statistics."""
        return dict(self._header_stats)

    def get_summary(self) -> dict[str, Any]:
        """Get configuration summary."""
        return {
            "is_enabled": self._is_enabled,
            "has_csp": self._csp is not None,
            "csp_report_only": self._csp.report_only if self._csp else False,
            "has_hsts": self._hsts is not None,
            "hsts_max_age": self._hsts.max_age if self._hsts else None,
            "has_permissions_policy": self._permissions is not None,
            "x_frame_options": self._x_frame_options.value if self._x_frame_options else None,
            "referrer_policy": self._referrer_policy.value if self._referrer_policy else None,
            "x_content_type_options": self._x_content_type_options,
            "x_xss_protection": self._x_xss_protection,
            "override_count": len(self._overrides),
            "violation_count": len(self._violations),
            "header_stats": self._header_stats,
        }

    def validate_configuration(self) -> list[str]:
        """Validate the current configuration."""
        issues = []

        # Check CSP
        if self._csp:
            if CSPDirective.DEFAULT_SRC not in self._csp.directives:
                issues.append("CSP: Missing default-src directive")
            if CSPDirective.OBJECT_SRC not in self._csp.directives:
                issues.append("CSP: Missing object-src directive (recommended: 'none')")
            if CSPDirective.BASE_URI not in self._csp.directives:
                issues.append("CSP: Missing base-uri directive")

        # Check HSTS
        if self._hsts:
            if self._hsts.max_age < 31536000:
                issues.append("HSTS: max-age less than 1 year is not recommended")
            if self._hsts.preload and not self._hsts.include_subdomains:
                issues.append("HSTS: preload requires includeSubDomains")

        # General recommendations
        if not self._x_content_type_options:
            issues.append("X-Content-Type-Options is disabled")
        if not self._x_frame_options:
            issues.append("X-Frame-Options is not set")

        return issues

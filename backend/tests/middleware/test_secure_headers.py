"""Tests for Secure Headers Middleware."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sensei.middleware.secure_headers import (
    SecureHeadersMiddleware,
    CSPConfig,
    CSPDirective,
    HSTSConfig,
    PermissionsPolicyConfig,
    CacheControlConfig,
    HeaderOverride,
    CSPViolationReport,
    XFrameOption,
    ReferrerPolicy,
)


class TestCSPConfig:
    """Tests for CSPConfig."""

    def test_create_empty_csp(self) -> None:
        """Test creating empty CSP config."""
        csp = CSPConfig()
        assert csp.directives == {}
        assert csp.report_only is False

    def test_add_directive(self) -> None:
        """Test adding directives."""
        csp = CSPConfig()
        csp.add_directive(CSPDirective.DEFAULT_SRC, "'self'")

        assert CSPDirective.DEFAULT_SRC in csp.directives
        assert "'self'" in csp.directives[CSPDirective.DEFAULT_SRC]

    def test_add_multiple_sources(self) -> None:
        """Test adding multiple sources to directive."""
        csp = CSPConfig()
        csp.add_directive(CSPDirective.IMG_SRC, "'self'", "data:", "https:")

        assert len(csp.directives[CSPDirective.IMG_SRC]) == 3

    def test_add_directive_chaining(self) -> None:
        """Test chaining add_directive calls."""
        csp = (
            CSPConfig()
            .add_directive(CSPDirective.DEFAULT_SRC, "'self'")
            .add_directive(CSPDirective.SCRIPT_SRC, "'self'")
        )

        assert CSPDirective.DEFAULT_SRC in csp.directives
        assert CSPDirective.SCRIPT_SRC in csp.directives

    def test_to_header_single_directive(self) -> None:
        """Test converting single directive to header."""
        csp = CSPConfig()
        csp.add_directive(CSPDirective.DEFAULT_SRC, "'self'")

        header = csp.to_header()
        assert header == "default-src 'self'"

    def test_to_header_multiple_directives(self) -> None:
        """Test converting multiple directives to header."""
        csp = CSPConfig()
        csp.add_directive(CSPDirective.DEFAULT_SRC, "'self'")
        csp.add_directive(CSPDirective.SCRIPT_SRC, "'self'")

        header = csp.to_header()
        assert "default-src 'self'" in header
        assert "script-src 'self'" in header
        assert ";" in header

    def test_to_header_valueless_directive(self) -> None:
        """Test directive without value."""
        csp = CSPConfig()
        csp.directives[CSPDirective.UPGRADE_INSECURE_REQUESTS] = []

        header = csp.to_header()
        assert "upgrade-insecure-requests" in header

    def test_report_only_mode(self) -> None:
        """Test report-only mode."""
        csp = CSPConfig(report_only=True)
        assert csp.report_only is True


class TestHSTSConfig:
    """Tests for HSTSConfig."""

    def test_default_values(self) -> None:
        """Test default HSTS values."""
        hsts = HSTSConfig()
        assert hsts.max_age == 31536000
        assert hsts.include_subdomains is True
        assert hsts.preload is False

    def test_custom_values(self) -> None:
        """Test custom HSTS values."""
        hsts = HSTSConfig(max_age=86400, include_subdomains=False, preload=True)

        assert hsts.max_age == 86400
        assert hsts.include_subdomains is False
        assert hsts.preload is True

    def test_to_header_basic(self) -> None:
        """Test basic header generation."""
        hsts = HSTSConfig(include_subdomains=False, preload=False)

        header = hsts.to_header()
        assert header == "max-age=31536000"

    def test_to_header_with_subdomains(self) -> None:
        """Test header with includeSubDomains."""
        hsts = HSTSConfig()

        header = hsts.to_header()
        assert "includeSubDomains" in header

    def test_to_header_with_preload(self) -> None:
        """Test header with preload."""
        hsts = HSTSConfig(preload=True)

        header = hsts.to_header()
        assert "preload" in header


class TestPermissionsPolicyConfig:
    """Tests for PermissionsPolicyConfig."""

    def test_create_empty_policy(self) -> None:
        """Test creating empty policy."""
        policy = PermissionsPolicyConfig()
        assert policy.features == {}

    def test_add_feature(self) -> None:
        """Test adding feature."""
        policy = PermissionsPolicyConfig()
        policy.add_feature("camera", "'self'")

        assert "camera" in policy.features
        assert "'self'" in policy.features["camera"]

    def test_disable_feature(self) -> None:
        """Test disabling feature."""
        policy = PermissionsPolicyConfig()
        policy.disable_feature("microphone")

        assert "microphone" in policy.features
        assert policy.features["microphone"] == []

    def test_to_header_with_allowlist(self) -> None:
        """Test header with allowlist."""
        policy = PermissionsPolicyConfig()
        policy.add_feature("fullscreen", "'self'")

        header = policy.to_header()
        assert "fullscreen=('self')" in header

    def test_to_header_disabled_feature(self) -> None:
        """Test header with disabled feature."""
        policy = PermissionsPolicyConfig()
        policy.disable_feature("camera")

        header = policy.to_header()
        assert "camera=()" in header

    def test_to_header_multiple_features(self) -> None:
        """Test header with multiple features."""
        policy = PermissionsPolicyConfig()
        policy.disable_feature("camera")
        policy.disable_feature("microphone")

        header = policy.to_header()
        assert "camera=()" in header
        assert "microphone=()" in header


class TestCacheControlConfig:
    """Tests for CacheControlConfig."""

    def test_default_values(self) -> None:
        """Test default cache control values."""
        cache = CacheControlConfig()
        assert cache.no_store is False
        assert cache.private is False

    def test_no_store(self) -> None:
        """Test no-store directive."""
        cache = CacheControlConfig(no_store=True)

        header = cache.to_header()
        assert header == "no-store"

    def test_multiple_directives(self) -> None:
        """Test multiple directives."""
        cache = CacheControlConfig(
            no_store=True,
            no_cache=True,
            private=True,
        )

        header = cache.to_header()
        assert "no-store" in header
        assert "no-cache" in header
        assert "private" in header

    def test_max_age(self) -> None:
        """Test max-age directive."""
        cache = CacheControlConfig(max_age=3600)

        header = cache.to_header()
        assert "max-age=3600" in header

    def test_immutable(self) -> None:
        """Test immutable directive."""
        cache = CacheControlConfig(max_age=31536000, immutable=True)

        header = cache.to_header()
        assert "immutable" in header


class TestSecureHeadersMiddleware:
    """Tests for SecureHeadersMiddleware."""

    def test_initialization(self) -> None:
        """Test middleware initialization."""
        middleware = SecureHeadersMiddleware()

        assert middleware.is_enabled() is True
        assert middleware.get_csp() is not None
        assert middleware.get_hsts() is not None

    def test_defaults_applied(self) -> None:
        """Test default headers are applied."""
        middleware = SecureHeadersMiddleware()

        # Default CSP exists
        csp = middleware.get_csp()
        assert csp is not None
        assert CSPDirective.DEFAULT_SRC in csp.directives

    def test_enable_disable(self) -> None:
        """Test enabling and disabling middleware."""
        middleware = SecureHeadersMiddleware()

        middleware.disable()
        assert middleware.is_enabled() is False

        middleware.enable()
        assert middleware.is_enabled() is True

    def test_disabled_returns_empty_headers(self) -> None:
        """Test disabled middleware returns no headers."""
        middleware = SecureHeadersMiddleware()
        middleware.disable()

        headers = middleware.generate_headers()
        assert headers == {}


class TestCSPConfiguration:
    """Tests for CSP configuration methods."""

    def test_set_csp(self) -> None:
        """Test setting CSP."""
        middleware = SecureHeadersMiddleware()

        csp = CSPConfig()
        csp.add_directive(CSPDirective.DEFAULT_SRC, "'none'")
        middleware.set_csp(csp)

        assert middleware.get_csp() == csp

    def test_add_csp_source(self) -> None:
        """Test adding CSP source."""
        middleware = SecureHeadersMiddleware()
        middleware.add_csp_source(CSPDirective.SCRIPT_SRC, "https://cdn.example.com")

        csp = middleware.get_csp()
        assert csp is not None
        assert "https://cdn.example.com" in csp.directives[CSPDirective.SCRIPT_SRC]

    def test_set_csp_report_only(self) -> None:
        """Test setting CSP report-only mode."""
        middleware = SecureHeadersMiddleware()
        middleware.set_csp_report_only(True)

        csp = middleware.get_csp()
        assert csp is not None
        assert csp.report_only is True

    def test_add_csp_nonce(self) -> None:
        """Test adding CSP nonce."""
        middleware = SecureHeadersMiddleware()
        middleware.add_csp_nonce("abc123")

        csp = middleware.get_csp()
        assert csp is not None
        assert "'nonce-abc123'" in csp.directives[CSPDirective.SCRIPT_SRC]
        assert "'nonce-abc123'" in csp.directives[CSPDirective.STYLE_SRC]


class TestHSTSConfiguration:
    """Tests for HSTS configuration."""

    def test_set_hsts(self) -> None:
        """Test setting HSTS."""
        middleware = SecureHeadersMiddleware()

        hsts = HSTSConfig(max_age=86400)
        middleware.set_hsts(hsts)

        assert middleware.get_hsts() == hsts

    def test_hsts_header_generated(self) -> None:
        """Test HSTS header is generated."""
        middleware = SecureHeadersMiddleware()

        headers = middleware.generate_headers()
        assert "Strict-Transport-Security" in headers
        assert "max-age=" in headers["Strict-Transport-Security"]


class TestOtherHeaderConfiguration:
    """Tests for other header configurations."""

    def test_set_x_frame_options(self) -> None:
        """Test setting X-Frame-Options."""
        middleware = SecureHeadersMiddleware()
        middleware.set_x_frame_options(XFrameOption.SAMEORIGIN)

        assert middleware.get_x_frame_options() == XFrameOption.SAMEORIGIN

    def test_set_referrer_policy(self) -> None:
        """Test setting Referrer-Policy."""
        middleware = SecureHeadersMiddleware()
        middleware.set_referrer_policy(ReferrerPolicy.NO_REFERRER)

        assert middleware.get_referrer_policy() == ReferrerPolicy.NO_REFERRER

    def test_set_x_content_type_options(self) -> None:
        """Test setting X-Content-Type-Options."""
        middleware = SecureHeadersMiddleware()
        middleware.set_x_content_type_options(False)

        assert middleware.get_x_content_type_options() is False

    def test_set_x_xss_protection(self) -> None:
        """Test setting X-XSS-Protection."""
        middleware = SecureHeadersMiddleware()
        middleware.set_x_xss_protection(False)

        assert middleware.get_x_xss_protection() is False

    def test_set_permissions_policy(self) -> None:
        """Test setting Permissions-Policy."""
        middleware = SecureHeadersMiddleware()

        policy = PermissionsPolicyConfig()
        policy.disable_feature("camera")
        middleware.set_permissions_policy(policy)

        assert middleware.get_permissions_policy() == policy

    def test_set_cache_control(self) -> None:
        """Test setting Cache-Control."""
        middleware = SecureHeadersMiddleware()

        cache = CacheControlConfig(max_age=3600, public=True)
        middleware.set_cache_control(cache)

        assert middleware.get_cache_control() == cache


class TestHeaderGeneration:
    """Tests for header generation."""

    def test_generate_all_headers(self) -> None:
        """Test generating all headers."""
        middleware = SecureHeadersMiddleware()

        headers = middleware.generate_headers()

        assert "Content-Security-Policy" in headers
        assert "Strict-Transport-Security" in headers
        assert "X-Frame-Options" in headers
        assert "Referrer-Policy" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Permissions-Policy" in headers
        assert "Cache-Control" in headers

    def test_csp_report_only_header_name(self) -> None:
        """Test CSP report-only uses correct header name."""
        middleware = SecureHeadersMiddleware()
        middleware.set_csp_report_only(True)

        headers = middleware.generate_headers()

        assert "Content-Security-Policy-Report-Only" in headers
        assert "Content-Security-Policy" not in headers

    def test_x_content_type_options_value(self) -> None:
        """Test X-Content-Type-Options value."""
        middleware = SecureHeadersMiddleware()

        headers = middleware.generate_headers()
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_x_xss_protection_value(self) -> None:
        """Test X-XSS-Protection value."""
        middleware = SecureHeadersMiddleware()

        headers = middleware.generate_headers()
        assert headers["X-XSS-Protection"] == "1; mode=block"

    def test_disabled_headers_not_included(self) -> None:
        """Test disabled headers are not included."""
        middleware = SecureHeadersMiddleware()
        middleware.set_x_content_type_options(False)
        middleware.set_x_xss_protection(False)
        middleware.set_x_frame_options(None)

        headers = middleware.generate_headers()

        assert "X-Content-Type-Options" not in headers
        assert "X-XSS-Protection" not in headers
        assert "X-Frame-Options" not in headers


class TestHeaderOverrides:
    """Tests for header override functionality."""

    def test_add_override(self) -> None:
        """Test adding header override."""
        middleware = SecureHeadersMiddleware()

        override = middleware.add_override(
            path_pattern="/api/*",
            headers={"X-Custom-Header": "value"},
            description="Custom API header",
        )

        assert override is not None
        assert override.path_pattern == "/api/*"
        assert override.is_active is True

    def test_get_override(self) -> None:
        """Test getting override by ID."""
        middleware = SecureHeadersMiddleware()

        override = middleware.add_override(
            path_pattern="/test",
            headers={"X-Test": "value"},
        )

        retrieved = middleware.get_override(override.id)
        assert retrieved == override

    def test_get_nonexistent_override(self) -> None:
        """Test getting nonexistent override."""
        middleware = SecureHeadersMiddleware()

        result = middleware.get_override(uuid4())
        assert result is None

    def test_get_overrides_list(self) -> None:
        """Test getting list of overrides."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override("/path1", {"X-Header": "1"})
        middleware.add_override("/path2", {"X-Header": "2"})

        overrides = middleware.get_overrides()
        assert len(overrides) == 2

    def test_get_overrides_by_path(self) -> None:
        """Test filtering overrides by path."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override("/path1", {"X-Header": "1"})
        middleware.add_override("/path2", {"X-Header": "2"})

        overrides = middleware.get_overrides(path_pattern="/path1")
        assert len(overrides) == 1
        assert overrides[0].path_pattern == "/path1"

    def test_update_override(self) -> None:
        """Test updating override."""
        middleware = SecureHeadersMiddleware()

        override = middleware.add_override("/test", {"X-Header": "old"})

        updated = middleware.update_override(
            override.id,
            headers={"X-Header": "new"},
        )

        assert updated is not None
        assert updated.headers["X-Header"] == "new"

    def test_update_override_active_status(self) -> None:
        """Test updating override active status."""
        middleware = SecureHeadersMiddleware()

        override = middleware.add_override("/test", {"X-Header": "value"})

        middleware.update_override(override.id, is_active=False)

        updated = middleware.get_override(override.id)
        assert updated is not None
        assert updated.is_active is False

    def test_remove_override(self) -> None:
        """Test removing override."""
        middleware = SecureHeadersMiddleware()

        override = middleware.add_override("/test", {"X-Header": "value"})

        result = middleware.remove_override(override.id)
        assert result is True
        assert middleware.get_override(override.id) is None

    def test_remove_nonexistent_override(self) -> None:
        """Test removing nonexistent override."""
        middleware = SecureHeadersMiddleware()

        result = middleware.remove_override(uuid4())
        assert result is False


class TestOverrideApplication:
    """Tests for applying overrides to headers."""

    def test_override_adds_header(self) -> None:
        """Test override adds custom header."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override(
            path_pattern="/api/test",
            headers={"X-Custom": "added"},
        )

        headers = middleware.generate_headers(path="/api/test")
        assert headers["X-Custom"] == "added"

    def test_override_replaces_header(self) -> None:
        """Test override replaces existing header."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override(
            path_pattern="/relaxed",
            headers={"X-Frame-Options": "SAMEORIGIN"},
        )

        headers = middleware.generate_headers(path="/relaxed")
        assert headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_override_removes_header(self) -> None:
        """Test override removes header with None value."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override(
            path_pattern="/noframe",
            headers={"X-Frame-Options": None},
        )

        headers = middleware.generate_headers(path="/noframe")
        assert "X-Frame-Options" not in headers

    def test_override_wildcard_path(self) -> None:
        """Test override with wildcard path."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override(
            path_pattern="/api/*",
            headers={"X-API": "true"},
        )

        headers1 = middleware.generate_headers(path="/api/users")
        headers2 = middleware.generate_headers(path="/api/orders")
        headers3 = middleware.generate_headers(path="/web/page")

        assert headers1.get("X-API") == "true"
        assert headers2.get("X-API") == "true"
        assert "X-API" not in headers3

    def test_override_method_filter(self) -> None:
        """Test override with method filter."""
        middleware = SecureHeadersMiddleware()

        middleware.add_override(
            path_pattern="/api/data",
            headers={"Cache-Control": "max-age=3600"},
            method="GET",
        )

        get_headers = middleware.generate_headers(path="/api/data", method="GET")
        post_headers = middleware.generate_headers(path="/api/data", method="POST")

        assert get_headers["Cache-Control"] == "max-age=3600"
        assert post_headers["Cache-Control"] != "max-age=3600"

    def test_inactive_override_not_applied(self) -> None:
        """Test inactive override is not applied."""
        middleware = SecureHeadersMiddleware()

        override = middleware.add_override(
            path_pattern="/test",
            headers={"X-Custom": "value"},
        )
        middleware.update_override(override.id, is_active=False)

        headers = middleware.generate_headers(path="/test")
        assert "X-Custom" not in headers


class TestCSPViolationReporting:
    """Tests for CSP violation reporting."""

    def test_report_violation(self) -> None:
        """Test reporting CSP violation."""
        middleware = SecureHeadersMiddleware()

        report = middleware.report_csp_violation(
            document_uri="https://example.com/page",
            violated_directive="script-src",
            blocked_uri="https://evil.com/script.js",
        )

        assert report is not None
        assert report.document_uri == "https://example.com/page"
        assert report.violated_directive == "script-src"

    def test_report_violation_with_details(self) -> None:
        """Test reporting violation with all details."""
        middleware = SecureHeadersMiddleware()

        report = middleware.report_csp_violation(
            document_uri="https://example.com/page",
            violated_directive="script-src",
            blocked_uri="inline",
            referrer="https://external.com",
            source_file="https://example.com/app.js",
            line_number=42,
            column_number=10,
            user_agent="Mozilla/5.0",
        )

        assert report.referrer == "https://external.com"
        assert report.source_file == "https://example.com/app.js"
        assert report.line_number == 42
        assert report.column_number == 10
        assert report.user_agent == "Mozilla/5.0"

    def test_get_violations(self) -> None:
        """Test getting violation reports."""
        middleware = SecureHeadersMiddleware()

        middleware.report_csp_violation(
            document_uri="https://example.com/1",
            violated_directive="script-src",
            blocked_uri="evil.js",
        )
        middleware.report_csp_violation(
            document_uri="https://example.com/2",
            violated_directive="style-src",
            blocked_uri="evil.css",
        )

        violations = middleware.get_csp_violations()
        assert len(violations) == 2

    def test_get_violations_by_directive(self) -> None:
        """Test filtering violations by directive."""
        middleware = SecureHeadersMiddleware()

        middleware.report_csp_violation(
            document_uri="https://example.com/1",
            violated_directive="script-src",
            blocked_uri="evil.js",
        )
        middleware.report_csp_violation(
            document_uri="https://example.com/2",
            violated_directive="style-src",
            blocked_uri="evil.css",
        )

        violations = middleware.get_csp_violations(directive="script-src")
        assert len(violations) == 1
        assert violations[0].violated_directive == "script-src"

    def test_get_violations_limit(self) -> None:
        """Test violations list limit."""
        middleware = SecureHeadersMiddleware()

        for i in range(10):
            middleware.report_csp_violation(
                document_uri=f"https://example.com/{i}",
                violated_directive="script-src",
                blocked_uri="evil.js",
            )

        violations = middleware.get_csp_violations(limit=5)
        assert len(violations) == 5

    def test_violations_sorted_by_date(self) -> None:
        """Test violations are sorted by date (newest first)."""
        middleware = SecureHeadersMiddleware()

        r1 = middleware.report_csp_violation(
            document_uri="https://example.com/first",
            violated_directive="script-src",
            blocked_uri="evil.js",
        )
        r2 = middleware.report_csp_violation(
            document_uri="https://example.com/second",
            violated_directive="script-src",
            blocked_uri="evil.js",
        )

        violations = middleware.get_csp_violations()
        assert violations[0].id == r2.id  # Most recent first

    def test_get_violation_stats(self) -> None:
        """Test getting violation statistics."""
        middleware = SecureHeadersMiddleware()

        middleware.report_csp_violation("u1", "script-src", "b1")
        middleware.report_csp_violation("u2", "script-src", "b2")
        middleware.report_csp_violation("u3", "style-src", "b3")

        stats = middleware.get_violation_stats()
        assert stats["script-src"] == 2
        assert stats["style-src"] == 1

    def test_clear_violations(self) -> None:
        """Test clearing violations."""
        middleware = SecureHeadersMiddleware()

        middleware.report_csp_violation("u1", "script-src", "b1")
        middleware.report_csp_violation("u2", "style-src", "b2")

        count = middleware.clear_violations()
        assert count == 2
        assert len(middleware.get_csp_violations()) == 0


class TestPresets:
    """Tests for security presets."""

    def test_strict_preset(self) -> None:
        """Test strict security preset."""
        middleware = SecureHeadersMiddleware()
        middleware.apply_strict_preset()

        csp = middleware.get_csp()
        assert csp is not None
        assert "'none'" in csp.directives[CSPDirective.DEFAULT_SRC]

        hsts = middleware.get_hsts()
        assert hsts is not None
        assert hsts.max_age == 63072000
        assert hsts.preload is True

        assert middleware.get_referrer_policy() == ReferrerPolicy.NO_REFERRER

    def test_relaxed_preset(self) -> None:
        """Test relaxed security preset."""
        middleware = SecureHeadersMiddleware()
        middleware.apply_relaxed_preset()

        csp = middleware.get_csp()
        assert csp is not None
        assert "'unsafe-inline'" in csp.directives[CSPDirective.DEFAULT_SRC]

        hsts = middleware.get_hsts()
        assert hsts is not None
        assert hsts.max_age == 86400

        assert middleware.get_x_frame_options() == XFrameOption.SAMEORIGIN

    def test_api_preset(self) -> None:
        """Test API preset."""
        middleware = SecureHeadersMiddleware()
        middleware.apply_api_preset()

        csp = middleware.get_csp()
        assert csp is not None
        assert "'none'" in csp.directives[CSPDirective.DEFAULT_SRC]

        cache = middleware.get_cache_control()
        assert cache is not None
        assert cache.no_store is True


class TestStatisticsAndValidation:
    """Tests for statistics and validation."""

    def test_header_stats(self) -> None:
        """Test header usage statistics."""
        middleware = SecureHeadersMiddleware()

        middleware.generate_headers()
        middleware.generate_headers()

        stats = middleware.get_header_stats()
        assert stats["Content-Security-Policy"] == 2
        assert stats["Strict-Transport-Security"] == 2

    def test_get_summary(self) -> None:
        """Test configuration summary."""
        middleware = SecureHeadersMiddleware()

        summary = middleware.get_summary()

        assert summary["is_enabled"] is True
        assert summary["has_csp"] is True
        assert summary["has_hsts"] is True
        assert "x_frame_options" in summary
        assert "violation_count" in summary

    def test_validate_configuration_default(self) -> None:
        """Test validation on default config."""
        middleware = SecureHeadersMiddleware()

        issues = middleware.validate_configuration()
        # Default config should be mostly valid
        assert len(issues) < 3

    def test_validate_missing_default_src(self) -> None:
        """Test validation detects missing default-src."""
        middleware = SecureHeadersMiddleware()

        csp = CSPConfig()
        csp.add_directive(CSPDirective.SCRIPT_SRC, "'self'")
        middleware.set_csp(csp)

        issues = middleware.validate_configuration()
        assert any("default-src" in issue for issue in issues)

    def test_validate_short_hsts(self) -> None:
        """Test validation warns on short HSTS."""
        middleware = SecureHeadersMiddleware()

        hsts = HSTSConfig(max_age=86400)
        middleware.set_hsts(hsts)

        issues = middleware.validate_configuration()
        assert any("less than 1 year" in issue for issue in issues)

    def test_validate_preload_without_subdomains(self) -> None:
        """Test validation warns on preload without subdomains."""
        middleware = SecureHeadersMiddleware()

        hsts = HSTSConfig(preload=True, include_subdomains=False)
        middleware.set_hsts(hsts)

        issues = middleware.validate_configuration()
        assert any("includeSubDomains" in issue for issue in issues)

    def test_validate_disabled_x_content_type(self) -> None:
        """Test validation warns on disabled X-Content-Type-Options."""
        middleware = SecureHeadersMiddleware()
        middleware.set_x_content_type_options(False)

        issues = middleware.validate_configuration()
        assert any("X-Content-Type-Options" in issue for issue in issues)


class TestEnumValues:
    """Tests for enum values."""

    def test_csp_directive_values(self) -> None:
        """Test CSP directive enum values."""
        assert CSPDirective.DEFAULT_SRC.value == "default-src"
        assert CSPDirective.SCRIPT_SRC.value == "script-src"
        assert CSPDirective.UPGRADE_INSECURE_REQUESTS.value == "upgrade-insecure-requests"

    def test_x_frame_option_values(self) -> None:
        """Test X-Frame-Options enum values."""
        assert XFrameOption.DENY.value == "DENY"
        assert XFrameOption.SAMEORIGIN.value == "SAMEORIGIN"

    def test_referrer_policy_values(self) -> None:
        """Test Referrer-Policy enum values."""
        assert ReferrerPolicy.NO_REFERRER.value == "no-referrer"
        assert ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN.value == "strict-origin-when-cross-origin"

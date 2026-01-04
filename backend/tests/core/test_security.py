"""
Tests for Sensei OS Security Module

Comprehensive tests for:
- Password hashing and verification
- JWT token generation and validation
- TOTP 2FA functionality
- Backup codes
- Secure token generation
"""

import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import JWTError, jwt

from sensei.core.config import settings
from sensei.core.security import (
    TokenData,
    TokenPayload,
    TokenPair,
    TOTPSetupResult,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    generate_api_key,
    generate_backup_codes,
    generate_email_verification_token,
    generate_password_reset_token,
    generate_secure_token,
    generate_totp_qr_code,
    generate_totp_secret,
    get_lockout_key,
    get_rate_limit_key,
    get_totp_provisioning_uri,
    get_token_jti,
    hash_backup_codes,
    hash_password,
    needs_rehash,
    setup_totp,
    verify_backup_code,
    verify_password,
    verify_totp,
    verify_token,
)


# =============================================================================
# Password Hashing Tests
# =============================================================================


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password_basic(self):
        """Test basic password hashing."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
    
    def test_hash_password_empty_raises(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            hash_password("")
    
    def test_hash_password_too_short_raises(self):
        """Test that short password raises ValueError."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            hash_password("short")
    
    def test_hash_password_minimum_length(self):
        """Test password with exactly 8 characters."""
        password = "12345678"
        hashed = hash_password(password)
        assert hashed is not None
    
    def test_hash_password_unicode(self):
        """Test password with unicode characters."""
        password = "Sécûré🔐Pässwörd"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
    
    def test_hash_password_long_password(self):
        """Test very long password."""
        password = "A" * 1000
        hashed = hash_password(password)
        assert verify_password(password, hashed)
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with wrong password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword123!", hashed) is False
    
    def test_verify_password_empty_password(self):
        """Test verification with empty password returns False."""
        hashed = hash_password("SecurePassword123!")
        assert verify_password("", hashed) is False
    
    def test_verify_password_empty_hash(self):
        """Test verification with empty hash returns False."""
        assert verify_password("password", "") is False
    
    def test_verify_password_none_values(self):
        """Test verification with None values returns False."""
        assert verify_password(None, "hash") is False
        assert verify_password("password", None) is False
    
    def test_verify_password_malformed_hash(self):
        """Test verification with malformed hash returns False."""
        assert verify_password("password", "not-a-valid-hash") is False
        assert verify_password("password", "$2b$invalid") is False
    
    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password("securepassword123!", hashed) is False
        assert verify_password("SECUREPASSWORD123!", hashed) is False
    
    def test_needs_rehash_current_settings(self):
        """Test needs_rehash with current settings."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        # Fresh hash should not need rehashing
        assert needs_rehash(hashed) is False
    
    def test_needs_rehash_empty_hash(self):
        """Test needs_rehash with empty hash."""
        assert needs_rehash("") is False


# =============================================================================
# JWT Token Tests
# =============================================================================


class TestJWTTokens:
    """Tests for JWT token functions."""
    
    @pytest.fixture
    def token_payload(self):
        """Create a sample token payload."""
        return TokenPayload(
            user_id=uuid4(),
            roles=["admin", "user"],
            permissions=["users:read", "users:write"],
        )
    
    def test_create_access_token_basic(self, token_payload):
        """Test basic access token creation."""
        token = create_access_token(token_payload)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
        # JWT has 3 parts separated by dots
        assert token.count(".") == 2
    
    def test_create_access_token_custom_expiry(self, token_payload):
        """Test access token with custom expiry."""
        custom_expiry = timedelta(hours=2)
        token = create_access_token(token_payload, expires_delta=custom_expiry)
        
        data = decode_token(token, "access")
        expected_exp = datetime.now(timezone.utc) + custom_expiry
        
        # Allow 5 second tolerance
        assert abs((data.exp - expected_exp).total_seconds()) < 5
    
    def test_create_access_token_contains_claims(self, token_payload):
        """Test that access token contains expected claims."""
        token = create_access_token(token_payload)
        data = decode_token(token, "access")
        
        assert data.sub == str(token_payload.user_id)
        assert data.type == "access"
        assert data.roles == token_payload.roles
        assert data.permissions == token_payload.permissions
        assert data.jti is not None
        assert data.exp is not None
        assert data.iat is not None
    
    def test_create_refresh_token_basic(self, token_payload):
        """Test basic refresh token creation."""
        token = create_refresh_token(token_payload)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_create_refresh_token_contains_claims(self, token_payload):
        """Test that refresh token contains expected claims."""
        token = create_refresh_token(token_payload)
        data = decode_token(token, "refresh")
        
        assert data.sub == str(token_payload.user_id)
        assert data.type == "refresh"
        # Refresh tokens should not carry role/permission data
        assert data.roles == []
        assert data.permissions == []
    
    def test_create_refresh_token_longer_expiry(self, token_payload):
        """Test that refresh token has longer expiry than access token."""
        access = create_access_token(token_payload)
        refresh = create_refresh_token(token_payload)
        
        access_data = decode_token(access, "access")
        refresh_data = decode_token(refresh, "refresh")
        
        assert refresh_data.exp > access_data.exp
    
    def test_create_token_pair(self, token_payload):
        """Test token pair creation."""
        pair = create_token_pair(token_payload)
        
        assert isinstance(pair, TokenPair)
        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.token_type == "bearer"
        assert pair.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    def test_decode_token_access(self, token_payload):
        """Test decoding access token."""
        token = create_access_token(token_payload)
        data = decode_token(token, "access")
        
        assert isinstance(data, TokenData)
        assert data.sub == str(token_payload.user_id)
        assert data.type == "access"
    
    def test_decode_token_refresh(self, token_payload):
        """Test decoding refresh token."""
        token = create_refresh_token(token_payload)
        data = decode_token(token, "refresh")
        
        assert isinstance(data, TokenData)
        assert data.sub == str(token_payload.user_id)
        assert data.type == "refresh"
    
    def test_decode_token_wrong_type_raises(self, token_payload):
        """Test that decoding with wrong type raises error."""
        access_token = create_access_token(token_payload)
        
        with pytest.raises(JWTError, match="Invalid token type"):
            decode_token(access_token, "refresh")
    
    def test_decode_token_invalid_raises(self):
        """Test that decoding invalid token raises error."""
        with pytest.raises(JWTError):
            decode_token("invalid.token.here", "access")
    
    def test_decode_token_tampered_raises(self, token_payload):
        """Test that tampered token raises error."""
        token = create_access_token(token_payload)
        # Tamper with the token
        tampered = token[:-5] + "xxxxx"
        
        with pytest.raises(JWTError):
            decode_token(tampered, "access")
    
    def test_decode_token_expired_raises(self, token_payload):
        """Test that expired token raises error."""
        token = create_access_token(
            token_payload,
            expires_delta=timedelta(seconds=-1),
        )
        
        with pytest.raises(JWTError):
            decode_token(token, "access")
    
    def test_verify_token_valid(self, token_payload):
        """Test verify_token with valid token."""
        token = create_access_token(token_payload)
        data = verify_token(token, "access")
        
        assert data is not None
        assert data.sub == str(token_payload.user_id)
    
    def test_verify_token_invalid_returns_none(self):
        """Test verify_token with invalid token returns None."""
        data = verify_token("invalid.token", "access")
        assert data is None
    
    def test_verify_token_wrong_type_returns_none(self, token_payload):
        """Test verify_token with wrong type returns None."""
        access_token = create_access_token(token_payload)
        data = verify_token(access_token, "refresh")
        assert data is None
    
    def test_get_token_jti(self, token_payload):
        """Test extracting JTI from token."""
        token = create_access_token(token_payload)
        jti = get_token_jti(token)
        
        assert jti is not None
        assert len(jti) > 10
    
    def test_get_token_jti_invalid_returns_none(self):
        """Test get_token_jti with invalid token returns None."""
        jti = get_token_jti("invalid.token")
        assert jti is None
    
    def test_get_token_jti_expired_still_works(self, token_payload):
        """Test that JTI can be extracted from expired token."""
        token = create_access_token(
            token_payload,
            expires_delta=timedelta(seconds=-1),
        )
        jti = get_token_jti(token)
        
        assert jti is not None
    
    def test_different_tokens_different_jti(self, token_payload):
        """Test that each token gets a unique JTI."""
        token1 = create_access_token(token_payload)
        token2 = create_access_token(token_payload)
        
        jti1 = get_token_jti(token1)
        jti2 = get_token_jti(token2)
        
        assert jti1 != jti2


# =============================================================================
# TOTP Tests
# =============================================================================


class TestTOTP:
    """Tests for TOTP 2FA functions."""
    
    def test_generate_totp_secret(self):
        """Test TOTP secret generation."""
        secret = generate_totp_secret()
        
        assert secret is not None
        assert len(secret) == 32  # Base32 encoded
        # Should be valid base32
        assert secret.isalnum()
    
    def test_generate_totp_secret_unique(self):
        """Test that each secret is unique."""
        secrets = [generate_totp_secret() for _ in range(10)]
        assert len(secrets) == len(set(secrets))
    
    def test_get_totp_provisioning_uri(self):
        """Test provisioning URI generation."""
        from urllib.parse import quote
        
        secret = generate_totp_secret()
        email = "test@example.com"
        uri = get_totp_provisioning_uri(secret, email)
        
        assert uri.startswith("otpauth://totp/")
        # Email is URL-encoded in the URI
        assert quote(email, safe="") in uri or email.replace("@", "%40") in uri
        assert settings.TOTP_ISSUER in uri
        assert secret in uri
    
    def test_generate_totp_qr_code(self):
        """Test QR code generation."""
        secret = generate_totp_secret()
        uri = get_totp_provisioning_uri(secret, "test@example.com")
        qr_code = generate_totp_qr_code(uri)
        
        assert qr_code is not None
        assert len(qr_code) > 100  # Base64 encoded PNG
        # Should be valid base64
        import base64
        decoded = base64.b64decode(qr_code)
        # PNG magic bytes
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_setup_totp(self):
        """Test complete TOTP setup."""
        result = setup_totp("test@example.com")
        
        assert isinstance(result, TOTPSetupResult)
        assert result.secret is not None
        assert result.provisioning_uri is not None
        assert result.qr_code_base64 is not None
    
    def test_verify_totp_valid_code(self):
        """Test TOTP verification with valid code."""
        import pyotp
        
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        assert verify_totp(secret, code) is True
    
    def test_verify_totp_invalid_code(self):
        """Test TOTP verification with invalid code."""
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False
    
    def test_verify_totp_empty_values(self):
        """Test TOTP verification with empty values."""
        assert verify_totp("", "123456") is False
        assert verify_totp("secret", "") is False
        assert verify_totp(None, "123456") is False
    
    def test_verify_totp_invalid_format(self):
        """Test TOTP verification with invalid code format."""
        secret = generate_totp_secret()
        assert verify_totp(secret, "12345") is False  # Too short
        assert verify_totp(secret, "1234567") is False  # Too long
        assert verify_totp(secret, "abcdef") is False  # Not digits
    
    def test_verify_totp_with_spaces(self):
        """Test TOTP verification with spaces in code."""
        import pyotp
        
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        code_with_spaces = f"{code[:3]} {code[3:]}"
        
        assert verify_totp(secret, code_with_spaces) is True
    
    def test_verify_totp_window(self):
        """Test TOTP verification with time window."""
        import pyotp
        
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        
        # Current code should work
        current = totp.now()
        assert verify_totp(secret, current, window=1) is True


# =============================================================================
# Backup Codes Tests
# =============================================================================


class TestBackupCodes:
    """Tests for backup code functions."""
    
    def test_generate_backup_codes_count(self):
        """Test backup codes count."""
        codes = generate_backup_codes(10)
        assert len(codes) == 10
        
        codes = generate_backup_codes(5)
        assert len(codes) == 5
    
    def test_generate_backup_codes_format(self):
        """Test backup code format."""
        codes = generate_backup_codes()
        
        for code in codes:
            assert len(code) == 9  # XXXX-XXXX format
            assert code[4] == "-"
            assert code[:4].isalnum()
            assert code[5:].isalnum()
    
    def test_generate_backup_codes_unique(self):
        """Test that backup codes are unique."""
        codes = generate_backup_codes(100)
        assert len(codes) == len(set(codes))
    
    def test_hash_backup_codes(self):
        """Test backup code hashing."""
        codes = generate_backup_codes(5)
        hashed = hash_backup_codes(codes)
        
        assert len(hashed) == 5
        for h in hashed:
            assert h.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_backup_code_valid(self):
        """Test backup code verification with valid code."""
        codes = generate_backup_codes(5)
        hashed = hash_backup_codes(codes)
        
        # Verify first code
        is_valid, index = verify_backup_code(codes[0], hashed)
        assert is_valid is True
        assert index == 0
        
        # Verify last code
        is_valid, index = verify_backup_code(codes[4], hashed)
        assert is_valid is True
        assert index == 4
    
    def test_verify_backup_code_invalid(self):
        """Test backup code verification with invalid code."""
        codes = generate_backup_codes(5)
        hashed = hash_backup_codes(codes)
        
        is_valid, index = verify_backup_code("AAAA-BBBB", hashed)
        assert is_valid is False
        assert index == -1
    
    def test_verify_backup_code_empty(self):
        """Test backup code verification with empty values."""
        is_valid, index = verify_backup_code("", [])
        assert is_valid is False
        assert index == -1
        
        is_valid, index = verify_backup_code("AAAA-BBBB", [])
        assert is_valid is False
    
    def test_verify_backup_code_case_insensitive(self):
        """Test backup code verification is case-insensitive."""
        codes = generate_backup_codes(1)
        hashed = hash_backup_codes(codes)
        
        # Lowercase should work
        is_valid, _ = verify_backup_code(codes[0].lower(), hashed)
        assert is_valid is True
    
    def test_verify_backup_code_with_spaces(self):
        """Test backup code verification with extra spaces."""
        codes = generate_backup_codes(1)
        hashed = hash_backup_codes(codes)
        
        # With spaces should work
        code_with_spaces = f" {codes[0]} "
        is_valid, _ = verify_backup_code(code_with_spaces, hashed)
        assert is_valid is True


# =============================================================================
# Secure Token Tests
# =============================================================================


class TestSecureTokens:
    """Tests for secure token generation functions."""
    
    def test_generate_secure_token_default_length(self):
        """Test secure token with default length."""
        token = generate_secure_token()
        assert token is not None
        assert len(token) > 20  # URL-safe base64 is longer
    
    def test_generate_secure_token_custom_length(self):
        """Test secure token with custom length."""
        token_16 = generate_secure_token(16)
        token_64 = generate_secure_token(64)
        
        # Longer input produces longer output
        assert len(token_64) > len(token_16)
    
    def test_generate_secure_token_unique(self):
        """Test that tokens are unique."""
        tokens = [generate_secure_token() for _ in range(100)]
        assert len(tokens) == len(set(tokens))
    
    def test_generate_secure_token_url_safe(self):
        """Test that tokens are URL-safe."""
        for _ in range(10):
            token = generate_secure_token()
            # URL-safe base64 only contains these characters
            assert all(c.isalnum() or c in '-_' for c in token)
    
    def test_generate_password_reset_token(self):
        """Test password reset token generation."""
        token = generate_password_reset_token()
        assert token is not None
        assert len(token) > 20
    
    def test_generate_email_verification_token(self):
        """Test email verification token generation."""
        token = generate_email_verification_token()
        assert token is not None
        assert len(token) > 20
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()
        assert api_key.startswith("sk_")
        assert len(api_key) > 50
    
    def test_generate_api_key_unique(self):
        """Test that API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(keys) == len(set(keys))


# =============================================================================
# Rate Limiting Key Tests
# =============================================================================


class TestRateLimitingKeys:
    """Tests for rate limiting helper functions."""
    
    def test_get_rate_limit_key(self):
        """Test rate limit key generation."""
        key = get_rate_limit_key("user123", "login")
        assert key == "rate_limit:login:user123"
    
    def test_get_rate_limit_key_different_actions(self):
        """Test rate limit keys for different actions."""
        key1 = get_rate_limit_key("user123", "login")
        key2 = get_rate_limit_key("user123", "api")
        
        assert key1 != key2
    
    def test_get_lockout_key(self):
        """Test lockout key generation."""
        key = get_lockout_key("user@example.com")
        assert key == "lockout:user@example.com"


# =============================================================================
# Token Data Model Tests
# =============================================================================


class TestTokenModels:
    """Tests for token data models."""
    
    def test_token_data_model(self):
        """Test TokenData model."""
        data = TokenData(
            sub="user-123",
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="token-id-123",
            roles=["admin"],
            permissions=["users:read"],
        )
        
        assert data.sub == "user-123"
        assert data.type == "access"
        assert data.roles == ["admin"]
        assert data.permissions == ["users:read"]
    
    def test_token_data_defaults(self):
        """Test TokenData default values."""
        data = TokenData(
            sub="user-123",
            type="access",
            exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc),
            jti="token-id-123",
        )
        
        assert data.roles == []
        assert data.permissions == []
    
    def test_token_payload_model(self):
        """Test TokenPayload model."""
        user_id = uuid4()
        payload = TokenPayload(
            user_id=user_id,
            roles=["user"],
            permissions=["posts:read"],
        )
        
        assert payload.user_id == user_id
        assert payload.roles == ["user"]
        assert payload.permissions == ["posts:read"]
    
    def test_token_pair_model(self):
        """Test TokenPair model."""
        pair = TokenPair(
            access_token="access-123",
            refresh_token="refresh-456",
            token_type="bearer",
            expires_in=1800,
        )
        
        assert pair.access_token == "access-123"
        assert pair.refresh_token == "refresh-456"
        assert pair.token_type == "bearer"
        assert pair.expires_in == 1800
    
    def test_totp_setup_result_model(self):
        """Test TOTPSetupResult model."""
        result = TOTPSetupResult(
            secret="SECRET123",
            provisioning_uri="otpauth://...",
            qr_code_base64="base64data",
        )
        
        assert result.secret == "SECRET123"
        assert result.provisioning_uri == "otpauth://..."
        assert result.qr_code_base64 == "base64data"

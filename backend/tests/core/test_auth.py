"""
Tests for Sensei OS Authentication Service

Comprehensive tests for:
- User authentication (login)
- Token refresh
- Logout functionality
- Password reset flow
- Email verification
- Account lockout
- 2FA handling
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.auth import (
    AccountInactiveError,
    AccountLockedError,
    AuthenticationError,
    AuthService,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTwoFactorError,
    PasswordResetError,
    TokenExpiredError,
    TokenRevokedError,
    TwoFactorRequiredError,
    get_auth_service,
)
from sensei.core.security import (
    create_refresh_token,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_codes,
    hash_password,
    TokenPayload,
)
from sensei.models.user import User, UserStatus


# =============================================================================
# Exception Tests
# =============================================================================


class TestAuthenticationExceptions:
    """Tests for authentication exception classes."""
    
    def test_authentication_error_base(self):
        """Test base AuthenticationError."""
        error = AuthenticationError("Test error", "test_code")
        
        assert error.message == "Test error"
        assert error.code == "test_code"
        assert str(error) == "Test error"
    
    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError."""
        error = InvalidCredentialsError()
        
        assert error.code == "invalid_credentials"
        assert "Invalid email or password" in error.message
    
    def test_invalid_credentials_error_custom_message(self):
        """Test InvalidCredentialsError with custom message."""
        error = InvalidCredentialsError("Custom message")
        assert error.message == "Custom message"
    
    def test_account_locked_error_without_time(self):
        """Test AccountLockedError without locked_until."""
        error = AccountLockedError()
        
        assert error.code == "account_locked"
        assert error.locked_until is None
        assert "temporarily locked" in error.message
    
    def test_account_locked_error_with_time(self):
        """Test AccountLockedError with locked_until."""
        locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        error = AccountLockedError(locked_until)
        
        assert error.locked_until == locked_until
        assert locked_until.isoformat() in error.message
    
    def test_account_inactive_error(self):
        """Test AccountInactiveError."""
        error = AccountInactiveError("suspended")
        
        assert error.code == "account_inactive"
        assert error.status == "suspended"
        assert "suspended" in error.message
    
    def test_email_not_verified_error(self):
        """Test EmailNotVerifiedError."""
        error = EmailNotVerifiedError()
        
        assert error.code == "email_not_verified"
        assert "not verified" in error.message
    
    def test_two_factor_required_error(self):
        """Test TwoFactorRequiredError."""
        user_id = uuid4()
        error = TwoFactorRequiredError(user_id)
        
        assert error.code == "2fa_required"
        assert error.user_id == user_id
    
    def test_invalid_two_factor_error(self):
        """Test InvalidTwoFactorError."""
        error = InvalidTwoFactorError()
        
        assert error.code == "invalid_2fa"
        assert "Invalid" in error.message
    
    def test_token_revoked_error(self):
        """Test TokenRevokedError."""
        error = TokenRevokedError()
        
        assert error.code == "token_revoked"
        assert "revoked" in error.message
    
    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        error = TokenExpiredError()
        
        assert error.code == "token_expired"
        assert "expired" in error.message
    
    def test_password_reset_error(self):
        """Test PasswordResetError."""
        error = PasswordResetError()
        
        assert error.code == "password_reset_error"
        assert "reset failed" in error.message
    
    def test_password_reset_error_custom_message(self):
        """Test PasswordResetError with custom message."""
        error = PasswordResetError("Token expired")
        assert error.message == "Token expired"


# =============================================================================
# AuthService Unit Tests with Mocks
# =============================================================================


class TestAuthServiceUnit:
    """Unit tests for AuthService using mocks."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService with mock db."""
        return AuthService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.password_hash = hash_password("SecurePass123!")
        user.status = UserStatus.ACTIVE.value
        user.locked_until = None
        user.totp_enabled = False
        user.totp_secret = None
        user.backup_codes = None
        user.email_verified = True
        user.is_superuser = False
        user.failed_login_attempts = 0
        return user
    
    @pytest.mark.asyncio
    async def test_get_auth_service(self, mock_db):
        """Test get_auth_service factory function."""
        service = get_auth_service(mock_db)
        
        assert isinstance(service, AuthService)
        assert service.db == mock_db
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_success(self, mock_redis, auth_service, mock_db, sample_user):
        """Test successful authentication."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.delete.return_value = None
        mock_redis.sadd.return_value = None
        mock_redis.expire.return_value = None
        
        # Mock role/permission query
        role_result = MagicMock()
        role_result.fetchall.return_value = [("admin",)]
        perm_result = MagicMock()
        perm_result.fetchall.return_value = [("users", "read")]
        
        # Configure execute to return different results for different calls
        # Order: 1) User lookup, 2) Role query, 3) Permission query
        mock_db.execute.side_effect = [
            mock_result,  # User lookup
            role_result,  # Role query
            perm_result,  # Permission query
        ]
        
        # Mock async commit
        async def mock_commit():
            pass
        mock_db.commit = mock_commit
        
        # Execute
        tokens = await auth_service.authenticate(
            email="test@example.com",
            password="SecurePass123!",
        )
        
        # Verify
        assert tokens is not None
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_invalid_password(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with wrong password."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        # Execute
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate(
                email="test@example.com",
                password="WrongPassword123!",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_user_not_found(self, mock_redis, auth_service, mock_db):
        """Test authentication with non-existent user."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        # Execute
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate(
                email="nonexistent@example.com",
                password="SomePassword123!",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_account_locked(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with locked account."""
        # Setup locked user
        sample_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        
        # Execute
        with pytest.raises(AccountLockedError):
            await auth_service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_account_inactive(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with inactive account."""
        sample_user.status = UserStatus.SUSPENDED.value
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        mock_redis.delete.return_value = None
        
        # Execute
        with pytest.raises(AccountInactiveError) as exc_info:
            await auth_service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
            )
        
        assert exc_info.value.status == UserStatus.SUSPENDED.value
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_email_not_verified(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with unverified email."""
        sample_user.status = UserStatus.PENDING.value
        sample_user.email_verified = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        mock_redis.delete.return_value = None
        
        # Execute
        with pytest.raises(EmailNotVerifiedError):
            await auth_service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_2fa_required(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication requiring 2FA."""
        sample_user.totp_enabled = True
        sample_user.totp_secret = generate_totp_secret()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        mock_redis.delete.return_value = None
        
        # Execute
        with pytest.raises(TwoFactorRequiredError) as exc_info:
            await auth_service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
            )
        
        assert exc_info.value.user_id == sample_user.id
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_2fa_invalid_code(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with invalid 2FA code."""
        sample_user.totp_enabled = True
        sample_user.totp_secret = generate_totp_secret()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        # Execute
        with pytest.raises(InvalidTwoFactorError):
            await auth_service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
                totp_code="000000",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_with_valid_totp(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with valid TOTP code."""
        import pyotp
        
        secret = generate_totp_secret()
        sample_user.totp_enabled = True
        sample_user.totp_secret = secret
        
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        
        role_result = MagicMock()
        role_result.fetchall.return_value = []
        perm_result = MagicMock()
        perm_result.fetchall.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_user)),
            role_result,
            perm_result,
        ]
        mock_db.commit.return_value = None
        
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        mock_redis.delete.return_value = None
        mock_redis.sadd.return_value = None
        
        # Execute
        tokens = await auth_service.authenticate(
            email="test@example.com",
            password="SecurePass123!",
            totp_code=valid_code,
        )
        
        assert tokens is not None
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_with_backup_code(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with backup code."""
        backup_codes = generate_backup_codes(5)
        hashed_codes = hash_backup_codes(backup_codes)
        
        sample_user.totp_enabled = True
        sample_user.totp_secret = generate_totp_secret()
        sample_user.backup_codes = hashed_codes
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        
        role_result = MagicMock()
        role_result.fetchall.return_value = []
        perm_result = MagicMock()
        perm_result.fetchall.return_value = []
        
        mock_db.execute.side_effect = [
            mock_result,
            MagicMock(scalar_one_or_none=MagicMock(return_value=sample_user)),
            role_result,
            perm_result,
        ]
        mock_db.commit.return_value = None
        
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        mock_redis.delete.return_value = None
        mock_redis.sadd.return_value = None
        
        # Execute
        tokens = await auth_service.authenticate(
            email="test@example.com",
            password="SecurePass123!",
            backup_code=backup_codes[0],
        )
        
        assert tokens is not None
        # Verify backup code was consumed
        assert len(sample_user.backup_codes) == 4
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_invalid_backup_code(self, mock_redis, auth_service, mock_db, sample_user):
        """Test authentication with invalid backup code."""
        backup_codes = generate_backup_codes(5)
        hashed_codes = hash_backup_codes(backup_codes)
        
        sample_user.totp_enabled = True
        sample_user.totp_secret = generate_totp_secret()
        sample_user.backup_codes = hashed_codes
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        # Execute
        with pytest.raises(InvalidTwoFactorError):
            await auth_service.authenticate(
                email="test@example.com",
                password="SecurePass123!",
                backup_code="AAAA-BBBB",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_authenticate_lockout_from_redis(self, mock_redis, auth_service, mock_db):
        """Test authentication blocked by Redis lockout."""
        mock_redis.get.return_value = "1"  # Account is locked
        mock_redis.ttl.return_value = 600  # 10 minutes remaining
        
        # Execute
        with pytest.raises(AccountLockedError):
            await auth_service.authenticate(
                email="test@example.com",
                password="SomePassword123!",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_refresh_tokens_success(self, mock_redis, auth_service, mock_db, sample_user):
        """Test successful token refresh."""
        # Create a valid refresh token
        payload = TokenPayload(user_id=sample_user.id, roles=[], permissions=[])
        refresh_token = create_refresh_token(payload)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        
        role_result = MagicMock()
        role_result.fetchall.return_value = [("admin",)]
        perm_result = MagicMock()
        perm_result.fetchall.return_value = [("users", "read")]
        
        mock_db.execute.side_effect = [
            mock_result,
            role_result,
            perm_result,
        ]
        
        mock_redis.exists.return_value = 0  # Token not revoked
        mock_redis.setex.return_value = None
        mock_redis.sadd.return_value = None
        mock_redis.expire.return_value = None
        
        # Execute
        tokens = await auth_service.refresh_tokens(refresh_token)
        
        assert tokens is not None
        assert tokens.access_token != refresh_token
        assert tokens.refresh_token != refresh_token
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_refresh_tokens_revoked(self, mock_redis, auth_service, mock_db, sample_user):
        """Test refresh with revoked token."""
        payload = TokenPayload(user_id=sample_user.id, roles=[], permissions=[])
        refresh_token = create_refresh_token(payload)
        
        mock_redis.exists.return_value = 1  # Token is revoked
        
        # Execute
        with pytest.raises(TokenRevokedError):
            await auth_service.refresh_tokens(refresh_token)
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_refresh_tokens_user_inactive(self, mock_redis, auth_service, mock_db, sample_user):
        """Test refresh when user became inactive."""
        sample_user.status = UserStatus.SUSPENDED.value
        
        payload = TokenPayload(user_id=sample_user.id, roles=[], permissions=[])
        refresh_token = create_refresh_token(payload)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        
        mock_redis.exists.return_value = 0
        mock_redis.setex.return_value = None
        
        # Execute
        with pytest.raises(AccountInactiveError):
            await auth_service.refresh_tokens(refresh_token)
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_logout_success(self, mock_redis, auth_service, mock_db, sample_user):
        """Test successful logout."""
        payload = TokenPayload(user_id=sample_user.id, roles=["admin"], permissions=["users:read"])
        from sensei.core.security import create_access_token
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)
        
        mock_redis.setex.return_value = None
        
        # Execute
        result = await auth_service.logout(access_token, refresh_token)
        
        assert result is True
        # Verify tokens were revoked
        assert mock_redis.setex.call_count >= 1
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_logout_all_sessions(self, mock_redis, auth_service, mock_db, sample_user):
        """Test logout all sessions."""
        mock_redis.delete.return_value = None
        
        # Execute
        result = await auth_service.logout_all_sessions(sample_user.id)
        
        assert result is True
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_request_password_reset_user_exists(self, mock_redis, auth_service, mock_db, sample_user):
        """Test password reset request for existing user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        
        mock_redis.setex.return_value = None
        
        # Execute
        token = await auth_service.request_password_reset("test@example.com")
        
        assert token is not None
        assert len(token) > 20
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_request_password_reset_user_not_found(self, mock_redis, auth_service, mock_db):
        """Test password reset request for non-existent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        token = await auth_service.request_password_reset("nonexistent@example.com")
        
        # Should return None to prevent user enumeration
        assert token is None
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.validate_password_strength")
    @patch("sensei.core.auth.redis_client")
    async def test_reset_password_success(self, mock_redis, mock_validate, auth_service, mock_db, sample_user):
        """Test successful password reset."""
        from sensei.core.security import PasswordStrengthResult
        mock_validate.return_value = PasswordStrengthResult(
            is_strong=True, score=90, is_breached=False, breach_count=0,
            issues=[], suggestions=[],
        )
        reset_token = "valid-reset-token"
        
        mock_redis.get.return_value = str(sample_user.id)
        mock_redis.delete.return_value = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_db.commit.return_value = None
        
        # Execute
        result = await auth_service.reset_password(reset_token, "NewSecurePass123!")
        
        assert result is True
        assert sample_user.must_change_password is False
        assert sample_user.failed_login_attempts == 0
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_reset_password_invalid_token(self, mock_redis, auth_service, mock_db):
        """Test password reset with invalid token."""
        mock_redis.get.return_value = None
        
        # Execute
        with pytest.raises(PasswordResetError, match="Invalid or expired"):
            await auth_service.reset_password("invalid-token", "NewPass123!")
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_change_password_success(self, mock_redis, auth_service, mock_db, sample_user):
        """Test successful password change."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_db.commit.return_value = None
        
        # Execute
        result = await auth_service.change_password(
            user_id=sample_user.id,
            current_password="SecurePass123!",
            new_password="NewSecurePass456!",
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_change_password_wrong_current(self, mock_redis, auth_service, mock_db, sample_user):
        """Test password change with wrong current password."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        
        # Execute
        with pytest.raises(InvalidCredentialsError, match="incorrect"):
            await auth_service.change_password(
                user_id=sample_user.id,
                current_password="WrongPassword123!",
                new_password="NewSecurePass456!",
            )
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_verify_email_success(self, mock_redis, auth_service, mock_db, sample_user):
        """Test successful email verification."""
        sample_user.status = UserStatus.PENDING.value
        sample_user.email_verified = False
        
        verification_token = "valid-email-token"
        
        mock_redis.get.return_value = str(sample_user.id)
        mock_redis.delete.return_value = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result
        mock_db.commit.return_value = None
        
        # Execute
        result = await auth_service.verify_email(verification_token)
        
        assert result is True
        assert sample_user.email_verified is True
        assert sample_user.status == UserStatus.ACTIVE.value
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_verify_email_invalid_token(self, mock_redis, auth_service, mock_db):
        """Test email verification with invalid token."""
        mock_redis.get.return_value = None
        
        # Execute
        with pytest.raises(AuthenticationError, match="Invalid or expired"):
            await auth_service.verify_email("invalid-token")
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_create_email_verification_token(self, mock_redis, auth_service, mock_db, sample_user):
        """Test email verification token creation."""
        mock_redis.setex.return_value = None
        
        # Execute
        token = await auth_service.create_email_verification_token(sample_user.id)
        
        assert token is not None
        assert len(token) > 20
        mock_redis.setex.assert_called_once()


# =============================================================================
# Integration-style Tests (with more realistic flows)
# =============================================================================


class TestAuthFlows:
    """Tests for complete authentication flows."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService with mock db."""
        return AuthService(mock_db)
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_full_login_logout_flow(self, mock_redis, auth_service, mock_db):
        """Test complete login and logout flow."""
        # Create user
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "user@example.com"
        user.password_hash = hash_password("Password123!")
        user.status = UserStatus.ACTIVE.value
        user.locked_until = None
        user.totp_enabled = False
        user.email_verified = True
        user.failed_login_attempts = 0
        
        # Setup mocks for login
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        
        role_result = MagicMock()
        role_result.fetchall.return_value = [("user",)]
        perm_result = MagicMock()
        perm_result.fetchall.return_value = [("posts", "read")]
        
        # Order: 1) User lookup, 2) Role query, 3) Permission query
        mock_db.execute.side_effect = [
            mock_result,
            role_result,
            perm_result,
        ]
        
        # Mock async commit
        async def mock_commit():
            pass
        mock_db.commit = mock_commit
        
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        mock_redis.delete.return_value = None
        mock_redis.sadd.return_value = None
        mock_redis.setex.return_value = None
        
        # Login
        tokens = await auth_service.authenticate(
            email="user@example.com",
            password="Password123!",
        )
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        
        # Logout
        result = await auth_service.logout(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.validate_password_strength")
    @patch("sensei.core.auth.redis_client")
    async def test_password_reset_flow(self, mock_redis, mock_validate, auth_service, mock_db):
        """Test complete password reset flow."""
        from sensei.core.security import PasswordStrengthResult
        mock_validate.return_value = PasswordStrengthResult(
            is_strong=True, score=90, is_breached=False, breach_count=0,
            issues=[], suggestions=[],
        )
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "reset@example.com"
        user.password_hash = hash_password("OldPassword123!")
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.locked_until = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result
        mock_db.commit.return_value = None
        
        mock_redis.setex.return_value = None
        mock_redis.delete.return_value = None
        
        # Step 1: Request reset
        token = await auth_service.request_password_reset("reset@example.com")
        assert token is not None
        
        # Step 2: Reset password (simulate token retrieval)
        mock_redis.get.return_value = str(user.id)
        
        result = await auth_service.reset_password(token, "NewPassword456!")
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.core.auth.redis_client")
    async def test_failed_login_lockout_flow(self, mock_redis, auth_service, mock_db):
        """Test account lockout after failed logins."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "lockme@example.com"
        user.password_hash = hash_password("CorrectPassword123!")
        user.status = UserStatus.ACTIVE.value
        user.locked_until = None
        user.totp_enabled = False
        user.failed_login_attempts = 0
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result
        mock_db.commit.return_value = None
        
        mock_redis.get.return_value = None
        mock_redis.expire.return_value = None
        mock_redis.setex.return_value = None
        
        # Simulate 5 failed attempts reaching lockout
        mock_redis.incr.side_effect = [1, 2, 3, 4, 5]
        
        for i in range(5):
            with pytest.raises(InvalidCredentialsError):
                await auth_service.authenticate(
                    email="lockme@example.com",
                    password="WrongPassword123!",
                )
        
        # 6th attempt should be blocked
        mock_redis.get.return_value = "1"  # Account is now locked
        mock_redis.ttl.return_value = 900  # 15 minutes
        
        with pytest.raises(AccountLockedError):
            await auth_service.authenticate(
                email="lockme@example.com",
                password="WrongPassword123!",
            )

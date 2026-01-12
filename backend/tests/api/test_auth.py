"""
Tests for Sensei OS Authentication API Endpoints

Comprehensive tests for:
- Login endpoint
- Logout endpoint
- Token refresh endpoint
- Password reset endpoints
- Email verification endpoint
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient

from sensei.api.v1.endpoints.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    TwoFactorRequiredResponse,
    VerifyEmailRequest,
    router,
)
from sensei.core.auth import (
    AccountInactiveError,
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTwoFactorError,
    PasswordResetError,
    TokenExpiredError,
    TokenRevokedError,
    TwoFactorRequiredError,
)
from sensei.core.security import TokenPair


# =============================================================================
# Request/Response Schema Tests
# =============================================================================


class TestRequestSchemas:
    """Tests for request/response Pydantic models."""
    
    def test_login_request_valid(self):
        """Test valid login request."""
        request = LoginRequest(
            email="test@example.com",
            password="SecurePass123!",
        )
        
        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"
        assert request.totp_code is None
        assert request.backup_code is None
        assert request.remember_me is False
    
    def test_login_request_with_2fa(self):
        """Test login request with 2FA code."""
        request = LoginRequest(
            email="test@example.com",
            password="SecurePass123!",
            totp_code="123456",
        )
        
        assert request.totp_code == "123456"
    
    def test_login_request_with_backup_code(self):
        """Test login request with backup code."""
        request = LoginRequest(
            email="test@example.com",
            password="SecurePass123!",
            backup_code="ABCD-EFGH",
        )
        
        assert request.backup_code == "ABCD-EFGH"
    
    def test_login_request_invalid_email(self):
        """Test login request with invalid email."""
        with pytest.raises(ValueError):
            LoginRequest(
                email="not-an-email",
                password="SecurePass123!",
            )
    
    def test_login_request_password_too_short(self):
        """Test login request with password too short."""
        with pytest.raises(ValueError):
            LoginRequest(
                email="test@example.com",
                password="short",
            )
    
    def test_token_response(self):
        """Test token response model."""
        response = TokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=1800,
        )
        
        assert response.access_token == "access-token"
        assert response.refresh_token == "refresh-token"
        assert response.token_type == "bearer"
        assert response.expires_in == 1800
    
    def test_two_factor_required_response(self):
        """Test 2FA required response model."""
        response = TwoFactorRequiredResponse()
        
        assert response.requires_2fa is True
        assert "Two-factor" in response.message
    
    def test_refresh_token_request(self):
        """Test refresh token request model."""
        request = RefreshTokenRequest(refresh_token="refresh-token-here")
        
        assert request.refresh_token == "refresh-token-here"
    
    def test_password_reset_request(self):
        """Test password reset request model."""
        request = PasswordResetRequest(email="reset@example.com")
        
        assert request.email == "reset@example.com"
    
    def test_password_reset_confirm(self):
        """Test password reset confirm model."""
        request = PasswordResetConfirm(
            token="reset-token",
            new_password="NewSecurePass123!",
        )
        
        assert request.token == "reset-token"
        assert request.new_password == "NewSecurePass123!"
    
    def test_password_reset_confirm_password_too_short(self):
        """Test password reset with short password."""
        with pytest.raises(ValueError):
            PasswordResetConfirm(
                token="reset-token",
                new_password="short",
            )
    
    def test_change_password_request(self):
        """Test change password request model."""
        request = ChangePasswordRequest(
            current_password="OldPass123!",
            new_password="NewPass456!",
        )
        
        assert request.current_password == "OldPass123!"
        assert request.new_password == "NewPass456!"
    
    def test_verify_email_request(self):
        """Test verify email request model."""
        request = VerifyEmailRequest(token="verification-token")
        
        assert request.token == "verification-token"
    
    def test_message_response(self):
        """Test message response model."""
        response = MessageResponse(message="Success")
        
        assert response.message == "Success"
        assert response.success is True


# =============================================================================
# Login Endpoint Tests (Mocked)
# =============================================================================


class TestLoginEndpoint:
    """Tests for the login endpoint."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_success(self, mock_redis, mock_get_service):
        """Test successful login."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        # Setup mock
        mock_service = AsyncMock()
        mock_service.authenticate.return_value = TokenPair(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            token_type="bearer",
            expires_in=1800,
        )
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        # Create test app
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "access-token-123"
        assert data["refresh_token"] == "refresh-token-456"
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_2fa_required(self, mock_redis, mock_get_service):
        """Test login returns 202 when 2FA is required."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        # Setup mock
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = TwoFactorRequiredError(uuid4())
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        # Create test app
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["requires_2fa"] is True
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_invalid_credentials(self, mock_redis, mock_get_service):
        """Test login with invalid credentials."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = InvalidCredentialsError()
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "WrongPassword123!",
                },
            )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_account_locked(self, mock_redis, mock_get_service):
        """Test login with locked account."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = AccountLockedError(locked_until)
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_423_LOCKED
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_account_inactive(self, mock_redis, mock_get_service):
        """Test login with inactive account."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = AccountInactiveError("suspended")
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_email_not_verified(self, mock_redis, mock_get_service):
        """Test login with unverified email."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = EmailNotVerifiedError()
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_login_invalid_2fa(self, mock_redis, mock_get_service):
        """Test login with invalid 2FA code."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.authenticate.side_effect = InvalidTwoFactorError()
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                    "totp_code": "000000",
                },
            )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Refresh Token Endpoint Tests
# =============================================================================


class TestRefreshEndpoint:
    """Tests for the refresh token endpoint."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_refresh_success(self, mock_redis, mock_get_service):
        """Test successful token refresh."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.refresh_tokens.return_value = TokenPair(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            token_type="bearer",
            expires_in=1800,
        )
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/refresh",
                json={"refresh_token": "old-refresh-token"},
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "new-access-token"
        assert data["refresh_token"] == "new-refresh-token"
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_refresh_expired_token(self, mock_redis, mock_get_service):
        """Test refresh with expired token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.refresh_tokens.side_effect = TokenExpiredError()
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/refresh",
                json={"refresh_token": "expired-token"},
            )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_refresh_revoked_token(self, mock_redis, mock_get_service):
        """Test refresh with revoked token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.refresh_tokens.side_effect = TokenRevokedError()
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/refresh",
                json={"refresh_token": "revoked-token"},
            )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Password Reset Endpoint Tests
# =============================================================================


class TestPasswordResetEndpoints:
    """Tests for password reset endpoints."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_request_password_reset(self, mock_redis, mock_get_service):
        """Test password reset request."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.request_password_reset.return_value = "reset-token"
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/password-reset",
                json={"email": "test@example.com"},
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "If an account" in data["message"]
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_confirm_password_reset(self, mock_redis, mock_get_service):
        """Test password reset confirmation."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.reset_password.return_value = True
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/password-reset/confirm",
                json={
                    "token": "valid-reset-token",
                    "new_password": "NewSecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reset successfully" in data["message"]
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    @patch("sensei.api.deps.redis_client")
    async def test_confirm_password_reset_invalid_token(self, mock_redis, mock_get_service):
        """Test password reset with invalid token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.reset_password.side_effect = PasswordResetError("Invalid token")
        mock_get_service.return_value = mock_service
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/password-reset/confirm",
                json={
                    "token": "invalid-token",
                    "new_password": "NewSecurePass123!",
                },
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Email Verification Endpoint Tests
# =============================================================================


class TestEmailVerificationEndpoint:
    """Tests for email verification endpoint."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    async def test_verify_email_success(self, mock_get_service):
        """Test successful email verification."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.verify_email.return_value = True
        mock_get_service.return_value = mock_service
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/verify-email",
                json={"token": "valid-verification-token"},
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "verified successfully" in data["message"]
    
    @pytest.mark.asyncio
    @patch("sensei.api.v1.endpoints.auth.get_auth_service")
    async def test_verify_email_invalid_token(self, mock_get_service):
        """Test email verification with invalid token."""
        from fastapi import FastAPI
        from sensei.core.auth import AuthenticationError
        from httpx import ASGITransport, AsyncClient
        
        mock_service = AsyncMock()
        mock_service.verify_email.side_effect = AuthenticationError("Invalid token", "invalid_token")
        mock_get_service.return_value = mock_service
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/verify-email",
                json={"token": "invalid-token"},
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Tests for request validation."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_login_missing_email(self, mock_redis):
        """Test login with missing email."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={"password": "SecurePass123!"},
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_login_missing_password(self, mock_redis):
        """Test login with missing password."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/login",
                json={"email": "test@example.com"},
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_refresh_missing_token(self, mock_redis):
        """Test refresh with missing token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        app = FastAPI()
        app.include_router(router)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/refresh",
                json={},
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

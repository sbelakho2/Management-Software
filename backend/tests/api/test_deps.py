"""
Tests for Sensei OS API Dependencies

Comprehensive tests for:
- Database session management
- Authentication dependencies
- Permission checking
- Rate limiting
- Pagination
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from sensei.api.deps import (
    PaginationParams,
    PermissionChecker,
    RateLimiter,
    RoleChecker,
    get_correlation_id,
    get_current_active_user,
    get_current_superuser,
    get_current_user,
    get_optional_token_data,
    get_token_data,
)
from sensei.core.security import (
    TokenData,
    TokenPayload,
    create_access_token,
)
from sensei.models.user import User, UserStatus


# =============================================================================
# Token Data Dependency Tests
# =============================================================================


class TestGetTokenData:
    """Tests for get_token_data dependency."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_get_token_data_valid(self, mock_redis):
        """Test with valid token."""
        payload = TokenPayload(
            user_id=uuid4(),
            roles=["admin"],
            permissions=["users:read"],
        )
        token = create_access_token(payload)
        
        credentials = MagicMock()
        credentials.credentials = token
        
        mock_redis.exists.return_value = 0  # Not revoked
        
        result = await get_token_data(credentials)
        
        assert isinstance(result, TokenData)
        assert result.sub == str(payload.user_id)
        assert result.roles == ["admin"]
        assert result.permissions == ["users:read"]
    
    @pytest.mark.asyncio
    async def test_get_token_data_no_credentials(self):
        """Test with missing credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await get_token_data(None)
        
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"
    
    @pytest.mark.asyncio
    async def test_get_token_data_invalid_token(self):
        """Test with invalid token."""
        credentials = MagicMock()
        credentials.credentials = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            await get_token_data(credentials)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_get_token_data_revoked_token(self, mock_redis):
        """Test with revoked token."""
        payload = TokenPayload(user_id=uuid4(), roles=[], permissions=[])
        token = create_access_token(payload)
        
        credentials = MagicMock()
        credentials.credentials = token
        
        mock_redis.exists.return_value = 1  # Token is revoked
        
        with pytest.raises(HTTPException) as exc_info:
            await get_token_data(credentials)
        
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_token_data_expired_token(self):
        """Test with expired token."""
        payload = TokenPayload(user_id=uuid4(), roles=[], permissions=[])
        token = create_access_token(payload, expires_delta=timedelta(seconds=-1))
        
        credentials = MagicMock()
        credentials.credentials = token
        
        with pytest.raises(HTTPException) as exc_info:
            await get_token_data(credentials)
        
        assert exc_info.value.status_code == 401


class TestGetOptionalTokenData:
    """Tests for get_optional_token_data dependency."""
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_get_optional_token_data_valid(self, mock_redis):
        """Test with valid token."""
        payload = TokenPayload(user_id=uuid4(), roles=["user"], permissions=[])
        token = create_access_token(payload)
        
        credentials = MagicMock()
        credentials.credentials = token
        
        mock_redis.exists.return_value = 0
        
        result = await get_optional_token_data(credentials)
        
        assert result is not None
        assert result.sub == str(payload.user_id)
    
    @pytest.mark.asyncio
    async def test_get_optional_token_data_no_credentials(self):
        """Test with no credentials returns None."""
        result = await get_optional_token_data(None)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_optional_token_data_invalid_token(self):
        """Test with invalid token returns None."""
        credentials = MagicMock()
        credentials.credentials = "invalid"
        
        result = await get_optional_token_data(credentials)
        assert result is None
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_get_optional_token_data_revoked(self, mock_redis):
        """Test with revoked token returns None."""
        payload = TokenPayload(user_id=uuid4(), roles=[], permissions=[])
        token = create_access_token(payload)
        
        credentials = MagicMock()
        credentials.credentials = token
        
        mock_redis.exists.return_value = 1  # Revoked
        
        result = await get_optional_token_data(credentials)
        assert result is None


# =============================================================================
# Current User Dependency Tests
# =============================================================================


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid(self):
        """Test with valid user."""
        user_id = uuid4()
        user = MagicMock(spec=User)
        user.id = user_id
        user.status = UserStatus.ACTIVE.value
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result
        
        token_data = TokenData(
            sub=str(user_id),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["user"],
            permissions=[],
        )
        
        result = await get_current_user(mock_db, token_data)
        
        assert result == user
    
    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self):
        """Test with non-existent user."""
        user_id = uuid4()
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        token_data = TokenData(
            sub=str(user_id),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=[],
            permissions=[],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, token_data)
        
        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self):
        """Test with inactive user."""
        user_id = uuid4()
        user = MagicMock(spec=User)
        user.id = user_id
        user.status = UserStatus.SUSPENDED.value
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result
        
        token_data = TokenData(
            sub=str(user_id),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=[],
            permissions=[],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_db, token_data)
        
        assert exc_info.value.status_code == 401
        assert "suspended" in exc_info.value.detail


class TestGetCurrentActiveUser:
    """Tests for get_current_active_user dependency."""
    
    @pytest.mark.asyncio
    async def test_get_current_active_user(self):
        """Test that it returns the user from get_current_user."""
        user = MagicMock(spec=User)
        user.status = UserStatus.ACTIVE.value
        
        result = await get_current_active_user(user)
        
        assert result == user


class TestGetCurrentSuperuser:
    """Tests for get_current_superuser dependency."""
    
    @pytest.mark.asyncio
    async def test_get_current_superuser_valid(self):
        """Test with superuser."""
        user = MagicMock(spec=User)
        user.is_superuser = True

        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["superuser"],
            permissions=[],
        )
        
        result = await get_current_superuser(user, token_data)
        
        assert result == user
    
    @pytest.mark.asyncio
    async def test_get_current_superuser_not_superuser(self):
        """Test with non-superuser."""
        user = MagicMock(spec=User)
        user.is_superuser = False

        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["user"],
            permissions=[],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(user, token_data)
        
        assert exc_info.value.status_code == 403
        assert "Superuser" in exc_info.value.detail


# =============================================================================
# Permission Checker Tests
# =============================================================================


class TestPermissionChecker:
    """Tests for PermissionChecker dependency."""
    
    @pytest.mark.asyncio
    async def test_permission_checker_has_permission(self):
        """Test with user having required permission."""
        checker = PermissionChecker("users:read")
        
        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["user"],
            permissions=["users:read", "users:write"],
        )
        
        result = await checker(token_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_permission_checker_admin_bypass(self):
        """Test that admin role bypasses permission check."""
        checker = PermissionChecker("special:permission")
        
        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["admin"],
            permissions=[],  # No explicit permissions
        )
        
        result = await checker(token_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_permission_checker_missing_permission(self):
        """Test with user missing required permission."""
        checker = PermissionChecker("users:delete")
        
        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["user"],
            permissions=["users:read"],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(token_data)
        
        assert exc_info.value.status_code == 403
        assert "users:delete" in exc_info.value.detail


# =============================================================================
# Role Checker Tests
# =============================================================================


class TestRoleChecker:
    """Tests for RoleChecker dependency."""
    
    @pytest.mark.asyncio
    async def test_role_checker_has_role(self):
        """Test with user having required role."""
        checker = RoleChecker(["admin", "gm"])
        
        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["gm"],
            permissions=[],
        )
        
        result = await checker(token_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_role_checker_multiple_roles(self):
        """Test with user having one of multiple required roles."""
        checker = RoleChecker(["admin", "gm", "exec"])
        
        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["exec", "viewer"],
            permissions=[],
        )
        
        result = await checker(token_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_role_checker_missing_role(self):
        """Test with user missing required role."""
        checker = RoleChecker(["admin"])
        
        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["user", "viewer"],
            permissions=[],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(token_data)
        
        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_role_checker_admin_only_enum_does_not_allow_ceo(self):
        """Admin-only endpoints should stay admin-only even if an enum RoleType is passed."""
        from sensei.models.user import RoleType

        checker = RoleChecker([RoleType.ADMIN])

        token_data = TokenData(
            sub=str(uuid4()),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=["ceo"],
            permissions=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await checker(token_data)

        assert exc_info.value.status_code == 403


# =============================================================================
# Rate Limiter Tests
# =============================================================================


class TestRateLimiter:
    """Tests for RateLimiter dependency."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        return request
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_rate_limiter_under_limit(self, mock_redis, mock_request):
        """Test request under rate limit."""
        limiter = RateLimiter(requests=10, window=60)
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        result = await limiter(mock_request, None)
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_rate_limiter_at_limit(self, mock_redis, mock_request):
        """Test request at rate limit."""
        limiter = RateLimiter(requests=10, window=60)
        
        mock_redis.incr.return_value = 10  # At limit
        
        result = await limiter(mock_request, None)
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_rate_limiter_exceeded(self, mock_redis, mock_request):
        """Test request exceeding rate limit."""
        limiter = RateLimiter(requests=10, window=60)
        
        mock_redis.incr.return_value = 11  # Over limit
        mock_redis.ttl.return_value = 30  # 30 seconds remaining
        
        with pytest.raises(HTTPException) as exc_info:
            await limiter(mock_request, None)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        assert exc_info.value.headers["Retry-After"] == "30"
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_rate_limiter_uses_user_id_when_authenticated(self, mock_redis, mock_request):
        """Test that authenticated requests use user ID for rate limiting."""
        limiter = RateLimiter(requests=10, window=60)
        
        user_id = uuid4()
        token_data = TokenData(
            sub=str(user_id),
            type="access",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test-jti",
            roles=[],
            permissions=[],
        )
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        result = await limiter(mock_request, token_data)
        
        assert result is True
        # Verify the key used the user ID
        call_args = mock_redis.incr.call_args[0][0]
        assert str(user_id) in call_args
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_rate_limiter_uses_ip_when_anonymous(self, mock_redis, mock_request):
        """Test that anonymous requests use IP for rate limiting."""
        limiter = RateLimiter(requests=10, window=60, key_prefix="test")
        
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = None
        
        result = await limiter(mock_request, None)
        
        assert result is True
        # Verify the key used the IP
        call_args = mock_redis.incr.call_args[0][0]
        assert "192.168.1.1" in call_args
    
    @pytest.mark.asyncio
    @patch("sensei.api.deps.redis_client")
    async def test_rate_limiter_custom_settings(self, mock_redis, mock_request):
        """Test rate limiter with custom settings."""
        limiter = RateLimiter(requests=5, window=30, key_prefix="custom")
        
        mock_redis.incr.return_value = 6  # Over custom limit
        mock_redis.ttl.return_value = 15
        
        with pytest.raises(HTTPException) as exc_info:
            await limiter(mock_request, None)
        
        assert exc_info.value.status_code == 429


# =============================================================================
# Pagination Tests
# =============================================================================


class TestPaginationParams:
    """Tests for PaginationParams dependency."""
    
    def test_pagination_defaults(self):
        """Test default pagination values."""
        pagination = PaginationParams()
        
        assert pagination.page == 1
        assert pagination.page_size == 20
        assert pagination.offset == 0
        assert pagination.limit == 20
    
    def test_pagination_custom_values(self):
        """Test custom pagination values."""
        pagination = PaginationParams(page=3, page_size=50)
        
        assert pagination.page == 3
        assert pagination.page_size == 50
        assert pagination.offset == 100  # (3-1) * 50
        assert pagination.limit == 50
    
    def test_pagination_page_below_1(self):
        """Test that page below 1 is normalized to 1."""
        pagination = PaginationParams(page=0, page_size=20)
        
        assert pagination.page == 1
        assert pagination.offset == 0
    
    def test_pagination_negative_page(self):
        """Test that negative page is normalized to 1."""
        pagination = PaginationParams(page=-5, page_size=20)
        
        assert pagination.page == 1
    
    def test_pagination_page_size_below_1(self):
        """Test that page_size below 1 is normalized to 20."""
        pagination = PaginationParams(page=1, page_size=0)
        
        assert pagination.page_size == 20
    
    def test_pagination_page_size_over_max(self):
        """Test that page_size over 100 is normalized to 100."""
        pagination = PaginationParams(page=1, page_size=500)
        
        assert pagination.page_size == 100
        assert pagination.limit == 100
    
    def test_pagination_offset_calculation(self):
        """Test offset calculation for various pages."""
        page1 = PaginationParams(page=1, page_size=10)
        page2 = PaginationParams(page=2, page_size=10)
        page5 = PaginationParams(page=5, page_size=10)
        
        assert page1.offset == 0
        assert page2.offset == 10
        assert page5.offset == 40


# =============================================================================
# Correlation ID Tests
# =============================================================================


class TestCorrelationId:
    """Tests for get_correlation_id dependency."""
    
    @pytest.mark.asyncio
    async def test_correlation_id_provided(self):
        """Test with correlation ID provided in header."""
        correlation_id = "custom-correlation-id-123"
        
        result = await get_correlation_id(correlation_id)
        
        assert result == correlation_id
    
    @pytest.mark.asyncio
    async def test_correlation_id_generated(self):
        """Test that correlation ID is generated when not provided."""
        result = await get_correlation_id(None)
        
        assert result is not None
        # Should be a valid UUID
        assert len(result) == 36  # UUID format with dashes
    
    @pytest.mark.asyncio
    async def test_correlation_id_unique(self):
        """Test that generated correlation IDs are unique."""
        id1 = await get_correlation_id(None)
        id2 = await get_correlation_id(None)
        id3 = await get_correlation_id(None)
        
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

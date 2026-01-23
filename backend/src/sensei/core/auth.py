"""
Sensei OS Authentication Service

Provides authentication business logic including:
- User login/logout
- Token refresh
- Password reset flow
- Email verification
- Account lockout handling
- Session management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.config import settings
from sensei.core.redis import redis_client
from sensei.core.security import (
    TokenData,
    TokenPair,
    TokenPayload,
    create_token_pair,
    decode_token,
    generate_email_verification_token,
    generate_password_reset_token,
    generate_secure_token,
    get_lockout_key,
    get_rate_limit_key,
    get_token_jti,
    hash_password,
    needs_rehash,
    verify_backup_code,
    verify_password,
    verify_totp,
)
from sensei.models.user import User, UserStatus


logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    
    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    """Invalid username/password combination."""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, "invalid_credentials")


class AccountLockedError(AuthenticationError):
    """Account is temporarily locked."""
    
    def __init__(self, locked_until: Optional[datetime] = None):
        if locked_until:
            message = f"Account is locked until {locked_until.isoformat()}"
        else:
            message = "Account is temporarily locked"
        self.locked_until = locked_until
        super().__init__(message, "account_locked")


class AccountInactiveError(AuthenticationError):
    """Account is not active."""
    
    def __init__(self, status: str):
        self.status = status
        super().__init__(f"Account is {status}", "account_inactive")


class EmailNotVerifiedError(AuthenticationError):
    """Email address not verified."""
    
    def __init__(self):
        super().__init__("Email address not verified", "email_not_verified")


class TwoFactorRequiredError(AuthenticationError):
    """Two-factor authentication required."""
    
    def __init__(self, user_id: UUID):
        self.user_id = user_id
        super().__init__("Two-factor authentication required", "2fa_required")


class InvalidTwoFactorError(AuthenticationError):
    """Invalid two-factor code."""
    
    def __init__(self):
        super().__init__("Invalid two-factor authentication code", "invalid_2fa")


class TokenRevokedError(AuthenticationError):
    """Token has been revoked."""
    
    def __init__(self):
        super().__init__("Token has been revoked", "token_revoked")


class TokenExpiredError(AuthenticationError):
    """Token has expired."""
    
    def __init__(self):
        super().__init__("Token has expired", "token_expired")


class PasswordResetError(AuthenticationError):
    """Password reset error."""
    
    def __init__(self, message: str = "Password reset failed"):
        super().__init__(message, "password_reset_error")


# =============================================================================
# Authentication Service
# =============================================================================


class AuthService:
    """
    Authentication service handling login, logout, and token management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate(
        self,
        email: str,
        password: str,
        totp_code: Optional[str] = None,
        backup_code: Optional[str] = None,
    ) -> TokenPair:
        """
        Authenticate a user and return token pair.
        
        Args:
            email: User's email address
            password: User's password
            totp_code: Optional TOTP code for 2FA
            backup_code: Optional backup code for 2FA
            
        Returns:
            TokenPair with access and refresh tokens
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
            AccountInactiveError: If account is not active
            TwoFactorRequiredError: If 2FA is required but not provided
            InvalidTwoFactorError: If 2FA code is invalid
        """
        # Check rate limiting/lockout
        await self._check_lockout(email)
        
        # Find user by email
        user = await self._get_user_by_email(email)
        
        if not user:
            # Increment failed attempts for this email even if user doesn't exist
            # This prevents user enumeration
            await self._record_failed_attempt(email)
            raise InvalidCredentialsError()
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise AccountLockedError(user.locked_until)
        
        # Verify password
        if not verify_password(password, user.password_hash):
            await self._record_failed_attempt(email, user.id)
            raise InvalidCredentialsError()
        
        # Check account status
        if user.status != UserStatus.ACTIVE.value:
            if user.status == UserStatus.PENDING.value and not user.email_verified:
                raise EmailNotVerifiedError()
            raise AccountInactiveError(user.status)
        
        # Check 2FA
        if user.totp_enabled:
            if not totp_code and not backup_code:
                raise TwoFactorRequiredError(user.id)
            
            if totp_code and user.totp_secret and not verify_totp(user.totp_secret, totp_code):
                await self._record_failed_attempt(email, user.id)
                raise InvalidTwoFactorError()
            
            if backup_code:
                backup_codes = user.backup_codes or []
                is_valid, code_index = verify_backup_code(backup_code, backup_codes)
                if not is_valid:
                    await self._record_failed_attempt(email, user.id)
                    raise InvalidTwoFactorError()
                
                # Remove used backup code
                backup_codes.pop(code_index)
                user.backup_codes = backup_codes
        
        # Successful login - update user record
        await self._record_successful_login(user)
        
        # Check if password needs rehashing
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        
        # Get user roles and permissions
        roles, permissions = await self._get_user_roles_permissions(user.id)
        
        # Create tokens
        payload = TokenPayload(
            user_id=user.id,
            roles=roles,
            permissions=permissions,
        )
        
        tokens = create_token_pair(payload)
        
        # Store refresh token JTI in Redis for revocation tracking
        jti = get_token_jti(tokens.refresh_token)
        if jti:
            await self._store_refresh_token(user.id, jti)
        
        logger.info(
            "User authenticated",
            user_id=str(user.id),
            email=user.email,
        )
        
        return tokens
    
    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """
        Refresh access and refresh tokens.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New TokenPair
            
        Raises:
            TokenExpiredError: If token is expired
            TokenRevokedError: If token is revoked
            InvalidCredentialsError: If token is invalid
        """
        try:
            token_data = decode_token(refresh_token, "refresh")
        except Exception as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError()
            raise InvalidCredentialsError("Invalid refresh token")
        
        # Check if token is revoked
        if await self._is_token_revoked(token_data.jti):
            raise TokenRevokedError()
        
        # Get user
        user_id = UUID(token_data.sub)
        user = await self._get_user_by_id(user_id)
        
        if not user:
            raise InvalidCredentialsError("User not found")
        
        if user.status != UserStatus.ACTIVE.value:
            raise AccountInactiveError(user.status)
        
        # Revoke old refresh token
        await self._revoke_token(token_data.jti)
        
        # Get roles and permissions
        roles, permissions = await self._get_user_roles_permissions(user.id)
        
        # Create new tokens
        payload = TokenPayload(
            user_id=user.id,
            roles=roles,
            permissions=permissions,
        )
        
        tokens = create_token_pair(payload)
        
        # Store new refresh token
        new_jti = get_token_jti(tokens.refresh_token)
        if new_jti:
            await self._store_refresh_token(user.id, new_jti)
        
        logger.info(
            "Tokens refreshed",
            user_id=str(user.id),
        )
        
        return tokens
    
    async def logout(self, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Log out a user by revoking their tokens.
        
        Args:
            access_token: The access token to revoke
            refresh_token: Optional refresh token to revoke
            
        Returns:
            True if logout successful
        """
        # Revoke access token
        access_jti = get_token_jti(access_token)
        if access_jti:
            await self._revoke_token(access_jti)
        
        # Revoke refresh token
        if refresh_token:
            refresh_jti = get_token_jti(refresh_token)
            if refresh_jti:
                await self._revoke_token(refresh_jti)
        
        logger.info("User logged out")
        return True
    
    async def logout_all_sessions(self, user_id: UUID) -> bool:
        """
        Log out all sessions for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if successful
        """
        # Delete all refresh tokens for this user
        key = f"user_tokens:{user_id}"
        await redis_client.delete(key)
        
        logger.info(
            "All sessions logged out",
            user_id=str(user_id),
        )
        return True
    
    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Initiate password reset flow.
        
        Args:
            email: User's email address
            
        Returns:
            Reset token if user exists, None otherwise
            (Always returns None to prevent user enumeration in production)
        """
        user = await self._get_user_by_email(email)
        
        if not user:
            # Don't reveal if user exists
            logger.info(
                "Password reset requested for unknown email",
                email=email,
            )
            return None
        
        # Generate reset token
        token = generate_password_reset_token()
        
        # Store token in Redis with expiry
        key = f"password_reset:{token}"
        await redis_client.setex(
            key,
            timedelta(hours=1),
            str(user.id),
        )
        
        logger.info(
            "Password reset token generated",
            user_id=str(user.id),
        )
        
        return token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using reset token.
        
        Args:
            token: Password reset token
            new_password: New password to set
            
        Returns:
            True if successful
            
        Raises:
            PasswordResetError: If token is invalid or expired
        """
        # Get user ID from token
        key = f"password_reset:{token}"
        user_id_str = await redis_client.get(key)
        
        if not user_id_str:
            raise PasswordResetError("Invalid or expired reset token")
        
        user_id = UUID(user_id_str)
        user = await self._get_user_by_id(user_id)
        
        if not user:
            raise PasswordResetError("User not found")
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Commit changes
        await self.db.commit()
        
        # Delete reset token
        await redis_client.delete(key)
        
        # Logout all sessions
        await self.logout_all_sessions(user_id)
        
        logger.info(
            "Password reset successful",
            user_id=str(user_id),
        )
        
        return True
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """
        Change password for authenticated user.
        
        Args:
            user_id: User's ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            InvalidCredentialsError: If current password is wrong
        """
        user = await self._get_user_by_id(user_id)
        
        if not user:
            raise InvalidCredentialsError("User not found")
        
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        user.must_change_password = False
        
        await self.db.commit()
        
        logger.info(
            "Password changed",
            user_id=str(user_id),
        )
        
        return True
    
    async def verify_email(self, token: str) -> bool:
        """
        Verify email using verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            True if successful
            
        Raises:
            AuthenticationError: If token is invalid
        """
        # Get user ID from token
        key = f"email_verification:{token}"
        user_id_str = await redis_client.get(key)
        
        if not user_id_str:
            raise AuthenticationError("Invalid or expired verification token", "invalid_token")
        
        user_id = UUID(user_id_str)
        user = await self._get_user_by_id(user_id)
        
        if not user:
            raise AuthenticationError("User not found", "user_not_found")
        
        # Update user
        user.email_verified = True
        if user.status == UserStatus.PENDING.value:
            user.status = UserStatus.ACTIVE.value
        
        await self.db.commit()
        
        # Delete verification token
        await redis_client.delete(key)
        
        logger.info(
            "Email verified",
            user_id=str(user_id),
        )
        
        return True
    
    async def create_email_verification_token(self, user_id: UUID) -> str:
        """
        Create an email verification token.
        
        Args:
            user_id: User's ID
            
        Returns:
            Verification token
        """
        token = generate_email_verification_token()
        
        key = f"email_verification:{token}"
        await redis_client.setex(
            key,
            timedelta(days=7),
            str(user_id),
        )
        
        return token
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(
                User.email == email.lower(),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_user_roles_permissions(self, user_id: UUID) -> tuple[list[str], list[str]]:
        """
        Get roles and permissions for a user.
        
        Returns:
            Tuple of (role_names, permission_strings)
        """
        from sensei.models.user import Role, RolePermission, Permission, UserRole
        
        # Get roles
        role_result = await self.db.execute(
            select(Role.name).join(UserRole).where(
                UserRole.user_id == user_id,
                Role.is_active.is_(True),
            )
        )
        roles = [r[0] for r in role_result.fetchall()]
        
        # Get permissions through roles
        perm_result = await self.db.execute(
            select(Permission.resource, Permission.action).join(
                RolePermission
            ).join(
                Role
            ).join(
                UserRole
            ).where(
                UserRole.user_id == user_id,
                Role.is_active.is_(True),
            ).distinct()
        )
        permissions = [f"{p[0]}:{p[1]}" for p in perm_result.fetchall()]
        
        return roles, permissions
    
    async def _check_lockout(self, identifier: str) -> None:
        """Check if identifier is locked out."""
        key = get_lockout_key(identifier)
        locked = await redis_client.get(key)
        
        if locked:
            ttl = await redis_client.ttl(key)
            locked_until = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            raise AccountLockedError(locked_until)
    
    async def _record_failed_attempt(
        self,
        email: str,
        user_id: Optional[UUID] = None,
    ) -> None:
        """Record a failed login attempt."""
        # Increment rate limit counter
        key = get_rate_limit_key(email, "login")
        count = await redis_client.incr(key)
        
        # Set expiry on first attempt
        if count == 1:
            await redis_client.expire(key, settings.LOCKOUT_DURATION_MINUTES * 60)
        
        # Lock account if too many attempts
        if count >= settings.MAX_LOGIN_ATTEMPTS:
            lockout_key = get_lockout_key(email)
            await redis_client.setex(
                lockout_key,
                settings.LOCKOUT_DURATION_MINUTES * 60,
                "1",
            )
            
            # Update user record if we have user_id
            if user_id:
                await self.db.execute(
                    update(User).where(User.id == user_id).values(
                        failed_login_attempts=count,
                        locked_until=datetime.now(timezone.utc) + timedelta(
                            minutes=settings.LOCKOUT_DURATION_MINUTES
                        ),
                    )
                )
                await self.db.commit()
            
            logger.warning(
                "Account locked due to failed attempts",
                email=email,
                attempts=count,
            )
    
    async def _record_successful_login(self, user: User) -> None:
        """Record a successful login."""
        user.last_login_at = datetime.now(timezone.utc)
        user.last_activity_at = datetime.now(timezone.utc)
        user.failed_login_attempts = 0
        user.locked_until = None
        
        await self.db.commit()
        
        # Clear any rate limiting
        key = get_rate_limit_key(user.email, "login")
        await redis_client.delete(key)  # type: ignore[misc]
        
        lockout_key = get_lockout_key(user.email)
        await redis_client.delete(lockout_key)  # type: ignore[misc]
    
    async def _store_refresh_token(self, user_id: UUID, jti: str) -> None:
        """Store refresh token JTI for the user."""
        key = f"user_tokens:{user_id}"
        await redis_client.sadd(key, jti)  # type: ignore[misc]
        
        # Set expiry to refresh token lifetime
        await redis_client.expire(key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)  # type: ignore[misc]
    
    async def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked."""
        key = f"revoked_token:{jti}"
        return await redis_client.exists(key) > 0
    
    async def _revoke_token(self, jti: str) -> None:
        """Revoke a token by JTI."""
        key = f"revoked_token:{jti}"
        # Store revoked token for longer than token lifetime
        await redis_client.setex(
            key,
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 + 3600,
            "1",
        )


# =============================================================================
# Helper Functions
# =============================================================================


async def get_current_user_from_token(token: str) -> Optional[User]:
    """
    Get current user from a JWT token.
    Useful for WebSockets where token is passed in URL.
    """
    from sensei.core.security import decode_token
    from sensei.core.database import async_session_factory
    from sqlalchemy import select
    
    try:
        token_data = decode_token(token, "access")
        user_id = UUID(token_data.sub)
        
        async with async_session_factory() as db:
            result = await db.execute(
                select(User).where(
                    User.id == user_id,
                    User.deleted_at.is_(None),
                )
            )
            return result.scalar_one_or_none()
    except Exception:
        return None

def get_auth_service(db: AsyncSession) -> AuthService:
    """Get an AuthService instance."""
    return AuthService(db)

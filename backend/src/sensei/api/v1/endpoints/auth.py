"""
Authentication Endpoints

Provides authentication flows including:
- Login with email/password
- 2FA verification
- Token refresh
- Logout
- Password reset
- Email verification
"""

from typing import Annotated, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from sensei.api.deps import AuthRateLimit, DBSession, get_token_data
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
from sensei.core.security import TokenData, TokenPair


router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class LoginRequest(BaseModel):
    """Login request body."""
    
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)
    backup_code: Optional[str] = Field(None, min_length=9, max_length=9)
    remember_me: bool = False


class TokenResponse(BaseModel):
    """Token response body."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TwoFactorRequiredResponse(BaseModel):
    """Response when 2FA is required."""
    
    requires_2fa: bool = True
    message: str = "Two-factor authentication required"


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""
    
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request body."""
    
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation body."""
    
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """Change password request body."""
    
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    """Email verification request body."""
    
    token: str


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str
    success: bool = True


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/login",
    response_model=Union[TokenResponse, TwoFactorRequiredResponse],
    responses={
        200: {"model": TokenResponse, "description": "Successful login"},
        202: {"model": TwoFactorRequiredResponse, "description": "2FA required"},
        400: {"description": "Invalid request"},
        401: {"description": "Invalid credentials"},
        423: {"description": "Account locked"},
    },
)
async def login(
    request: LoginRequest,
    db: DBSession,
    _rate_limit: AuthRateLimit,
    response: Response,
):
    """
    Authenticate user and return access/refresh tokens.
    
    If 2FA is enabled for the user and no TOTP code is provided,
    returns 202 status indicating 2FA is required.
    """
    auth_service = get_auth_service(db)
    
    try:
        tokens = await auth_service.authenticate(
            email=request.email,
            password=request.password,
            totp_code=request.totp_code,
            backup_code=request.backup_code,
        )
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )
    
    except TwoFactorRequiredError:
        response.status_code = status.HTTP_202_ACCEPTED
        return TwoFactorRequiredResponse()
    
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=e.message,
        )
    
    except AccountInactiveError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )
    
    except EmailNotVerifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )
    
    except InvalidTwoFactorError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
    authorization: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    x_refresh_token: Annotated[Optional[str], Header()] = None,
):
    """
    Log out user by revoking current tokens.
    
    Optionally pass refresh token in X-Refresh-Token header to revoke it too.
    """
    auth_service = get_auth_service(db)
    
    access_token = authorization.credentials if authorization else ""
    
    await auth_service.logout(
        access_token=access_token,
        refresh_token=x_refresh_token,
    )
    
    return MessageResponse(message="Successfully logged out")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def logout_all_sessions(
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Log out all sessions for the current user.
    
    Revokes all refresh tokens and active sessions.
    """
    from uuid import UUID
    
    auth_service = get_auth_service(db)
    
    user_id = UUID(token_data.sub)
    await auth_service.logout_all_sessions(user_id)
    
    return MessageResponse(message="All sessions logged out")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        200: {"model": TokenResponse, "description": "Tokens refreshed"},
        401: {"description": "Invalid or expired token"},
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: DBSession,
    _rate_limit: AuthRateLimit,
):
    """
    Refresh access and refresh tokens.
    
    The old refresh token is invalidated after use.
    """
    auth_service = get_auth_service(db)
    
    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )
    
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    
    except TokenRevokedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def request_password_reset(
    request: PasswordResetRequest,
    db: DBSession,
    _rate_limit: AuthRateLimit,
):
    """
    Request a password reset email.
    
    Always returns success to prevent user enumeration.
    In production, this would send an email with the reset link.
    """
    auth_service = get_auth_service(db)
    
    # Token is returned for development; in production, send via email
    token = await auth_service.request_password_reset(request.email)
    
    # TODO: Send email with reset link
    # In development, we might log the token
    
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent"
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password reset successful"},
        400: {"description": "Invalid or expired token"},
    },
)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: DBSession,
    _rate_limit: AuthRateLimit,
):
    """
    Confirm password reset with token and new password.
    """
    auth_service = get_auth_service(db)
    
    try:
        await auth_service.reset_password(request.token, request.new_password)
        return MessageResponse(message="Password has been reset successfully")
    
    except PasswordResetError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password changed"},
        401: {"description": "Invalid current password"},
    },
)
async def change_password(
    request: ChangePasswordRequest,
    db: DBSession,
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    """
    Change password for authenticated user.
    
    Requires the current password for verification.
    """
    from uuid import UUID
    
    auth_service = get_auth_service(db)
    
    try:
        user_id = UUID(token_data.sub)
        await auth_service.change_password(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
        return MessageResponse(message="Password changed successfully")
    
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Email verified"},
        400: {"description": "Invalid or expired token"},
    },
)
async def verify_email(
    request: VerifyEmailRequest,
    db: DBSession,
):
    """
    Verify email address using verification token.
    """
    auth_service = get_auth_service(db)
    
    try:
        await auth_service.verify_email(request.token)
        return MessageResponse(message="Email verified successfully")
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

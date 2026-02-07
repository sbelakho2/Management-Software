"""
Sensei OS Security Module

Core security utilities including:
- Password hashing and verification (bcrypt)
- JWT token generation and validation
- TOTP (Time-based One-Time Password) handling
- Secure random token generation
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from uuid import UUID

import bcrypt
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from sensei.core.config import settings


# Bcrypt rounds for password hashing
BCRYPT_ROUNDS = settings.BCRYPT_ROUNDS


class TokenData(BaseModel):
    """Data extracted from a validated JWT token."""
    
    sub: str  # Subject (user_id as string)
    type: Literal["access", "refresh"]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for revocation tracking
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class TokenPayload(BaseModel):
    """Token payload for creating JWT tokens."""
    
    user_id: UUID
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiry in seconds


class TOTPSetupResult(BaseModel):
    """Result from TOTP setup including secret and provisioning URI."""
    
    secret: str
    provisioning_uri: str
    qr_code_base64: str


# =============================================================================
# Password Hashing
# =============================================================================


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Note: bcrypt has a 72-byte limit. For passwords longer than this,
    we hash the password with SHA-256 first (base64 encoded to stay printable),
    then pass that to bcrypt. This provides equivalent security.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Raises:
        ValueError: If password is empty or too short
    """
    if not password:
        raise ValueError("Password cannot be empty")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    
    # Encode password
    password_bytes = password.encode("utf-8")
    
    # If password is longer than 72 bytes, pre-hash with SHA-256
    # This is a common technique to handle bcrypt's 72-byte limit
    if len(password_bytes) > 72:
        import hashlib
        password_bytes = base64.b64encode(
            hashlib.sha256(password_bytes).digest()
        )
    
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def _prepare_password_for_bcrypt(password: str) -> bytes:
    """
    Prepare a password for bcrypt, handling the 72-byte limit.
    
    Args:
        password: Plain text password
        
    Returns:
        Bytes suitable for bcrypt (max 72 bytes)
    """
    password_bytes = password.encode("utf-8")
    
    if len(password_bytes) > 72:
        import hashlib
        password_bytes = base64.b64encode(
            hashlib.sha256(password_bytes).digest()
        )
    
    return password_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        password_bytes = _prepare_password_for_bcrypt(plain_password)
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Handle malformed hashes gracefully
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be rehashed.
    
    This is useful when bcrypt rounds are increased - existing hashes
    can be upgraded on next successful login.
    
    Args:
        hashed_password: The hashed password to check
        
    Returns:
        True if rehashing is recommended, False otherwise
    """
    if not hashed_password:
        return False
    
    try:
        # Extract the cost from the hash (format: $2b$XX$...)
        parts = hashed_password.split("$")
        if len(parts) < 4:
            return True  # Invalid hash format, needs rehash
        
        current_rounds = int(parts[2])
        return current_rounds < BCRYPT_ROUNDS
    except (ValueError, IndexError):
        return True  # If we can't parse, recommend rehash


# =============================================================================
# JWT Token Management
# =============================================================================


def create_access_token(
    payload: TokenPayload,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        payload: Token payload with user info
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT access token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    to_encode: dict[str, Any] = {
        "sub": str(payload.user_id),
        "type": "access",
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(32),
        "roles": payload.roles,
        "permissions": payload.permissions,
    }
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    payload: TokenPayload,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens have longer expiry and fewer claims.
    
    Args:
        payload: Token payload with user info
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    to_encode: dict[str, Any] = {
        "sub": str(payload.user_id),
        "type": "refresh",
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(32),
        "roles": [],  # Refresh tokens don't carry role/permission data
        "permissions": [],
    }
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_token_pair(payload: TokenPayload) -> TokenPair:
    """
    Create both access and refresh tokens.
    
    Args:
        payload: Token payload with user info
        
    Returns:
        TokenPair containing both tokens
    """
    return TokenPair(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def decode_token(token: str, token_type: Literal["access", "refresh"] = "access") -> TokenData:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenData with extracted claims
        
    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        # Validate token type
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type. Expected {token_type}")
        
        # Parse expiration datetime
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            exp = datetime.fromtimestamp(exp, tz=timezone.utc)
        
        # Parse issued at datetime
        iat = payload.get("iat")
        if isinstance(iat, (int, float)):
            iat = datetime.fromtimestamp(iat, tz=timezone.utc)
        
        return TokenData(
            sub=payload["sub"],
            type=payload["type"],
            exp=exp,
            iat=iat,
            jti=payload["jti"],
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
        )
    except JWTError:
        raise
    except Exception as e:
        raise JWTError(f"Token decode error: {str(e)}")


def verify_token(token: str, token_type: Literal["access", "refresh"] = "access") -> Optional[TokenData]:
    """
    Verify a JWT token and return data if valid.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type
        
    Returns:
        TokenData if valid, None if invalid
    """
    try:
        return decode_token(token, token_type)
    except JWTError:
        return None


def get_token_jti(token: str) -> Optional[str]:
    """
    Extract the JTI (JWT ID) from a token without full validation.
    
    Useful for token revocation even if token is expired.
    
    Args:
        token: The JWT token
        
    Returns:
        JTI string if extractable, None otherwise
    """
    try:
        # Decode without verification to get JTI
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("jti")
    except Exception:
        return None


# =============================================================================
# TOTP (Two-Factor Authentication)
# =============================================================================


def generate_totp_secret() -> str:
    """
    Generate a new TOTP secret.
    
    Returns:
        Base32-encoded secret string
    """
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    """
    Generate a TOTP provisioning URI for QR code generation.
    
    Args:
        secret: The TOTP secret
        email: User's email for identification
        
    Returns:
        otpauth:// URI for authenticator apps
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=email,
        issuer_name=settings.TOTP_ISSUER,
    )


def generate_totp_qr_code(provisioning_uri: str) -> str:
    """
    Generate a QR code image for TOTP setup.
    
    Args:
        provisioning_uri: The otpauth:// URI
        
    Returns:
        Base64-encoded PNG image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def setup_totp(email: str) -> TOTPSetupResult:
    """
    Set up TOTP for a user.
    
    Args:
        email: User's email address
        
    Returns:
        TOTPSetupResult with secret, URI, and QR code
    """
    secret = generate_totp_secret()
    provisioning_uri = get_totp_provisioning_uri(secret, email)
    qr_code = generate_totp_qr_code(provisioning_uri)
    
    return TOTPSetupResult(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code_base64=qr_code,
    )


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """
    Verify a TOTP code.
    
    Args:
        secret: The user's TOTP secret
        code: The 6-digit code to verify
        window: Number of time steps to allow for clock drift (default 1)
        
    Returns:
        True if code is valid, False otherwise
    """
    if not secret or not code:
        return False
    
    # Clean up the code (remove spaces)
    code = code.replace(" ", "").strip()
    
    # Validate code format
    if not code.isdigit() or len(code) != 6:
        return False
    
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    except Exception:
        return False


def generate_backup_codes(count: int = 10) -> list[str]:
    """
    Generate backup codes for 2FA recovery.
    
    Args:
        count: Number of backup codes to generate
        
    Returns:
        List of backup code strings (format: XXXX-XXXX)
    """
    codes = []
    for _ in range(count):
        # Generate 8 random alphanumeric characters
        code = secrets.token_hex(4).upper()
        # Format as XXXX-XXXX
        formatted = f"{code[:4]}-{code[4:]}"
        codes.append(formatted)
    return codes


def _normalize_backup_code(code: str) -> str:
    """Normalize backup code by removing non-alphanumeric characters and uppercasing."""
    import re
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def hash_backup_codes(codes: list[str]) -> list[str]:
    """
    Hash backup codes for secure storage.
    
    Args:
        codes: List of plain backup codes
        
    Returns:
        List of hashed backup codes
    """
    return [hash_password(_normalize_backup_code(code)) for code in codes]


def verify_backup_code(code: str, hashed_codes: list[str]) -> tuple[bool, int]:
    """
    Verify a backup code against stored hashes.
    
    Args:
        code: The backup code to verify
        hashed_codes: List of hashed backup codes
        
    Returns:
        Tuple of (is_valid, index) where index is the position of the matched code
        or -1 if not found
    """
    if not code or not hashed_codes:
        return False, -1
    
    # Normalize the code
    normalized_code = _normalize_backup_code(code)
    
    for i, hashed in enumerate(hashed_codes):
        if verify_password(normalized_code, hashed):
            return True, i
    
    return False, -1


# =============================================================================
# Secure Token Generation
# =============================================================================


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token in bytes (will be base64 encoded)
        
    Returns:
        URL-safe base64-encoded token string
    """
    return secrets.token_urlsafe(length)


def generate_password_reset_token() -> str:
    """
    Generate a token for password reset.
    
    Returns:
        Secure token string for password reset links
    """
    return generate_secure_token(32)


def generate_email_verification_token() -> str:
    """
    Generate a token for email verification.
    
    Returns:
        Secure token string for email verification links
    """
    return generate_secure_token(32)


def generate_api_key() -> str:
    """
    Generate an API key for service-to-service authentication.
    
    Returns:
        API key string (prefixed with 'sk_' for identification)
    """
    return f"sk_{generate_secure_token(48)}"


# =============================================================================
# Rate Limiting Helpers
# =============================================================================


def get_rate_limit_key(identifier: str, action: str) -> str:
    """
    Generate a Redis key for rate limiting.
    
    Args:
        identifier: User ID, IP address, or other identifier
        action: The action being rate limited (e.g., "login", "api")
        
    Returns:
        Redis key string
    """
    return f"rate_limit:{action}:{identifier}"


def get_lockout_key(identifier: str) -> str:
    """
    Generate a Redis key for account lockout tracking.
    
    Args:
        identifier: User ID or email
        
    Returns:
        Redis key string
    """
    return f"lockout:{identifier}"


# =============================================================================
# Password Breach Checking (HaveIBeenPwned k-Anonymity API)
# =============================================================================

import hashlib
import httpx
import asyncio
import logging
from typing import Tuple

_breach_check_logger = logging.getLogger(__name__)


class PasswordBreachCheckResult(BaseModel):
    """Result from password breach checking."""
    
    is_breached: bool
    breach_count: int
    check_performed: bool
    error: Optional[str] = None


async def check_password_breach(
    password: str,
    timeout_seconds: float = 3.0,
) -> PasswordBreachCheckResult:
    """
    Check if a password has been exposed in known data breaches.
    
    Uses the HaveIBeenPwned Passwords API with k-anonymity model:
    - Only sends first 5 characters of SHA-1 hash
    - Checks returned suffixes locally
    - Never exposes the actual password
    
    This is the RECOMMENDED way to check passwords against breach databases.
    
    Args:
        password: The password to check (never sent to API)
        timeout_seconds: API request timeout
        
    Returns:
        PasswordBreachCheckResult with breach status and count
        
    Security:
        - Only first 5 chars of SHA-1 hash are transmitted
        - Full hash is compared locally
        - Uses HTTPS for all communication
    """
    if not settings.PASSWORD_BREACH_CHECK_ENABLED:
        return PasswordBreachCheckResult(
            is_breached=False,
            breach_count=0,
            check_performed=False,
            error="Password breach checking is disabled"
        )
    
    try:
        # Compute SHA-1 hash of password
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        
        # k-anonymity: only send first 5 characters
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        # Query HaveIBeenPwned API
        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=timeout_seconds,
                headers={
                    "User-Agent": "Sensei-OS-Password-Checker",
                    "Add-Padding": "true",  # Request padded responses to prevent timing attacks
                }
            )
            
            if response.status_code != 200:
                _breach_check_logger.warning(
                    f"Password breach API returned status {response.status_code}"
                )
                return PasswordBreachCheckResult(
                    is_breached=False,
                    breach_count=0,
                    check_performed=False,
                    error=f"API returned status {response.status_code}"
                )
            
            # Parse response - each line is "SUFFIX:COUNT"
            # Find our suffix in the response
            breach_count = 0
            for line in response.text.splitlines():
                if ':' not in line:
                    continue
                hash_suffix, count_str = line.split(':', 1)
                if hash_suffix.strip().upper() == suffix:
                    breach_count = int(count_str.strip())
                    break
            
            return PasswordBreachCheckResult(
                is_breached=breach_count > 0,
                breach_count=breach_count,
                check_performed=True,
                error=None
            )
            
    except asyncio.TimeoutError:
        _breach_check_logger.warning("Password breach check timed out")
        return PasswordBreachCheckResult(
            is_breached=False,
            breach_count=0,
            check_performed=False,
            error="Request timed out"
        )
    except httpx.RequestError as e:
        _breach_check_logger.warning(f"Password breach check network error: {e}")
        return PasswordBreachCheckResult(
            is_breached=False,
            breach_count=0,
            check_performed=False,
            error=f"Network error: {str(e)}"
        )
    except Exception as e:
        _breach_check_logger.exception("Password breach check failed")
        return PasswordBreachCheckResult(
            is_breached=False,
            breach_count=0,
            check_performed=False,
            error=f"Unexpected error: {str(e)}"
        )


def check_password_breach_sync(
    password: str,
    timeout_seconds: float = 3.0,
) -> PasswordBreachCheckResult:
    """
    Synchronous version of password breach checking.
    
    For use in synchronous contexts. Uses the same k-anonymity approach.
    
    Args:
        password: The password to check
        timeout_seconds: API request timeout
        
    Returns:
        PasswordBreachCheckResult with breach status
    """
    if not settings.PASSWORD_BREACH_CHECK_ENABLED:
        return PasswordBreachCheckResult(
            is_breached=False,
            breach_count=0,
            check_performed=False,
            error="Password breach checking is disabled"
        )
    
    try:
        # Compute SHA-1 hash
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        
        with httpx.Client() as client:
            response = client.get(
                url,
                timeout=timeout_seconds,
                headers={
                    "User-Agent": "Sensei-OS-Password-Checker",
                    "Add-Padding": "true",
                }
            )
            
            if response.status_code != 200:
                return PasswordBreachCheckResult(
                    is_breached=False,
                    breach_count=0,
                    check_performed=False,
                    error=f"API returned status {response.status_code}"
                )
            
            breach_count = 0
            for line in response.text.splitlines():
                if ':' not in line:
                    continue
                hash_suffix, count_str = line.split(':', 1)
                if hash_suffix.strip().upper() == suffix:
                    breach_count = int(count_str.strip())
                    break
            
            return PasswordBreachCheckResult(
                is_breached=breach_count > 0,
                breach_count=breach_count,
                check_performed=True,
                error=None
            )
            
    except Exception as e:
        _breach_check_logger.warning(f"Sync password breach check failed: {e}")
        return PasswordBreachCheckResult(
            is_breached=False,
            breach_count=0,
            check_performed=False,
            error=str(e)
        )


class PasswordStrengthResult(BaseModel):
    """Comprehensive password strength analysis result."""
    
    is_strong: bool
    score: int  # 0-100
    is_breached: bool
    breach_count: int
    issues: list[str]
    suggestions: list[str]


async def validate_password_strength(
    password: str,
    check_breach: bool = True,
    min_length: int = 12,
) -> PasswordStrengthResult:
    """
    Comprehensive password strength validation.
    
    Checks:
    1. Length requirements
    2. Character diversity (uppercase, lowercase, digits, special)
    3. Common password patterns
    4. Breach database (HaveIBeenPwned)
    
    Args:
        password: Password to validate
        check_breach: Whether to check breach database
        min_length: Minimum password length
        
    Returns:
        PasswordStrengthResult with detailed analysis
    """
    issues: list[str] = []
    suggestions: list[str] = []
    score = 100
    
    # Length check
    if len(password) < min_length:
        issues.append(f"Password must be at least {min_length} characters")
        score -= 30
    elif len(password) < 16:
        suggestions.append("Consider using a longer password (16+ characters)")
        score -= 10
    
    # Character diversity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password)
    
    diversity_count = sum([has_upper, has_lower, has_digit, has_special])
    
    if diversity_count < 3:
        issues.append("Use a mix of uppercase, lowercase, numbers, and symbols")
        score -= 20
    elif diversity_count < 4:
        suggestions.append("Adding more character types improves security")
        score -= 5
    
    # Common patterns
    common_patterns = [
        ("123456", "Sequential numbers"),
        ("password", "Common word"),
        ("qwerty", "Keyboard pattern"),
        ("111111", "Repeated characters"),
        ("admin", "Common username"),
    ]
    
    password_lower = password.lower()
    for pattern, description in common_patterns:
        if pattern in password_lower:
            issues.append(f"Avoid {description.lower()} in password")
            score -= 15
    
    # Check if password is mostly repeated characters
    if len(set(password)) < len(password) / 3:
        issues.append("Password has too many repeated characters")
        score -= 20
    
    # Breach check
    is_breached = False
    breach_count = 0
    
    if check_breach and settings.PASSWORD_BREACH_CHECK_ENABLED:
        breach_result = await check_password_breach(password)
        if breach_result.is_breached:
            is_breached = True
            breach_count = breach_result.breach_count
            issues.append(
                f"This password has been seen in {breach_count:,} data breaches - "
                "choose a different password"
            )
            score -= 50  # Major penalty for breached passwords
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    # Determine if password is strong enough
    is_strong = score >= 60 and not is_breached and len(issues) == 0
    
    return PasswordStrengthResult(
        is_strong=is_strong,
        score=score,
        is_breached=is_breached,
        breach_count=breach_count,
        issues=issues,
        suggestions=suggestions
    )

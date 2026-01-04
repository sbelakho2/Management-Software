"""Sensei Core Package."""

from sensei.core.config import settings
from sensei.core.database import Base, engine, get_db_session
from sensei.core.redis import redis_client
from sensei.core.storage import storage_client
from sensei.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    verify_token,
    setup_totp,
    verify_totp,
    generate_backup_codes,
)
from sensei.core.auth import (
    AuthService,
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    get_auth_service,
)

__all__ = [
    # Config
    "settings",
    # Database
    "Base",
    "engine",
    "get_db_session",
    # Redis
    "redis_client",
    # Storage
    "storage_client",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    "verify_token",
    "setup_totp",
    "verify_totp",
    "generate_backup_codes",
    # Auth
    "AuthService",
    "AuthenticationError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "get_auth_service",
]

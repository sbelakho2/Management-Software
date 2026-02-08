"""
Secrets Rotation Service.

Provides a mechanism for rotating database passwords, Redis passwords,
JWT signing keys, and API keys with zero-downtime dual-key overlap.

Features:
- Scheduled rotation with configurable intervals
- Dual-key overlap period for seamless transitions
- Rotation audit trail
- Support for multiple secret types
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of rotatable secrets."""

    DATABASE_PASSWORD = "database_password"
    REDIS_PASSWORD = "redis_password"
    JWT_SIGNING_KEY = "jwt_signing_key"
    API_KEY = "api_key"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"


class RotationStatus(str, Enum):
    """Status of a rotation operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class SecretConfig:
    """Configuration for a rotatable secret."""

    secret_type: SecretType
    rotation_interval_days: int = 90
    overlap_hours: int = 24
    key_length: int = 64
    enabled: bool = True
    last_rotated: datetime | None = None
    next_rotation: datetime | None = None
    generate_fn: Callable[[], str] | None = None


@dataclass
class RotationEvent:
    """Record of a rotation operation."""

    id: str = ""
    secret_type: SecretType = SecretType.API_KEY
    status: RotationStatus = RotationStatus.PENDING
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    old_key_fingerprint: str = ""
    new_key_fingerprint: str = ""
    rotated_by: str = "system"
    error: str | None = None


class SecretsRotationService:
    """Manages secret rotation with dual-key overlap.

    Usage::

        svc = SecretsRotationService()
        svc.register_secret(SecretConfig(
            secret_type=SecretType.JWT_SIGNING_KEY,
            rotation_interval_days=30,
        ))

        # Check what needs rotation
        due = svc.get_secrets_due_for_rotation()

        # Rotate
        event = svc.rotate(SecretType.JWT_SIGNING_KEY)
    """

    def __init__(self) -> None:
        self._configs: dict[SecretType, SecretConfig] = {}
        self._current_secrets: dict[SecretType, str] = {}
        self._previous_secrets: dict[SecretType, str | None] = {}
        self._overlap_expiry: dict[SecretType, datetime | None] = {}
        self._rotation_history: list[RotationEvent] = []
        self._on_rotate: dict[
            SecretType, list[Callable[[str, str | None], None]]
        ] = {}

    def register_secret(
        self,
        config: SecretConfig,
        current_value: str | None = None,
    ) -> None:
        """Register a secret for managed rotation."""
        self._configs[config.secret_type] = config
        if current_value:
            self._current_secrets[config.secret_type] = current_value
        if config.next_rotation is None and config.last_rotated:
            config.next_rotation = config.last_rotated + timedelta(
                days=config.rotation_interval_days
            )
        elif config.next_rotation is None:
            config.next_rotation = datetime.now(
                timezone.utc
            ) + timedelta(days=config.rotation_interval_days)

        logger.info(
            "Registered secret %s for rotation (interval: %d days)",
            config.secret_type.value,
            config.rotation_interval_days,
        )

    def on_rotation(
        self,
        secret_type: SecretType,
        callback: Callable[[str, str | None], None],
    ) -> None:
        """Register a callback for when a secret is rotated.

        The callback receives (new_secret, old_secret).
        """
        self._on_rotate.setdefault(secret_type, []).append(callback)

    def get_secrets_due_for_rotation(self) -> list[SecretConfig]:
        """Return secrets that are due for rotation."""
        now = datetime.now(timezone.utc)
        due: list[SecretConfig] = []
        for config in self._configs.values():
            if not config.enabled:
                continue
            if config.next_rotation and config.next_rotation <= now:
                due.append(config)
        return due

    def rotate(
        self,
        secret_type: SecretType,
        *,
        rotated_by: str = "system",
        new_value: str | None = None,
    ) -> RotationEvent:
        """Rotate a secret.

        If *new_value* is not provided, a secure random value is generated.
        """
        config = self._configs.get(secret_type)
        if not config:
            raise ValueError(f"Secret {secret_type.value} not registered")

        event = RotationEvent(
            id=secrets.token_hex(16),
            secret_type=secret_type,
            status=RotationStatus.IN_PROGRESS,
            rotated_by=rotated_by,
        )

        try:
            old_secret = self._current_secrets.get(secret_type)
            event.old_key_fingerprint = self._fingerprint(old_secret)

            # Generate new secret
            if new_value:
                new_secret = new_value
            elif config.generate_fn:
                new_secret = config.generate_fn()
            else:
                new_secret = secrets.token_urlsafe(config.key_length)

            event.new_key_fingerprint = self._fingerprint(new_secret)

            # Dual-key overlap
            self._previous_secrets[secret_type] = old_secret
            self._current_secrets[secret_type] = new_secret
            self._overlap_expiry[secret_type] = datetime.now(
                timezone.utc
            ) + timedelta(hours=config.overlap_hours)

            # Update config
            config.last_rotated = datetime.now(timezone.utc)
            config.next_rotation = config.last_rotated + timedelta(
                days=config.rotation_interval_days
            )

            # Notify callbacks
            for cb in self._on_rotate.get(secret_type, []):
                try:
                    cb(new_secret, old_secret)
                except Exception:
                    logger.exception(
                        "Rotation callback failed for %s",
                        secret_type.value,
                    )

            event.status = RotationStatus.COMPLETED
            event.completed_at = datetime.now(timezone.utc)

            logger.info(
                "Rotated secret %s (fingerprint: %s → %s)",
                secret_type.value,
                event.old_key_fingerprint[:8],
                event.new_key_fingerprint[:8],
            )

        except Exception as exc:
            event.status = RotationStatus.FAILED
            event.error = str(exc)
            logger.exception("Failed to rotate %s", secret_type.value)

        self._rotation_history.append(event)
        return event

    def validate(
        self,
        secret_type: SecretType,
        value: str,
    ) -> bool:
        """Check if a value matches the current or previous (overlap) secret."""
        current = self._current_secrets.get(secret_type)
        if current and secrets.compare_digest(value, current):
            return True

        # Check overlap period
        overlap_exp = self._overlap_expiry.get(secret_type)
        if overlap_exp and datetime.now(timezone.utc) < overlap_exp:
            previous = self._previous_secrets.get(secret_type)
            if previous and secrets.compare_digest(value, previous):
                return True

        return False

    def cleanup_expired_overlaps(self) -> int:
        """Remove expired overlap secrets."""
        now = datetime.now(timezone.utc)
        cleaned = 0
        for st, expiry in list(self._overlap_expiry.items()):
            if expiry and expiry <= now:
                self._previous_secrets[st] = None
                self._overlap_expiry[st] = None
                cleaned += 1
        return cleaned

    def get_rotation_history(
        self,
        *,
        secret_type: SecretType | None = None,
        limit: int = 50,
    ) -> list[RotationEvent]:
        """Get rotation event history."""
        events = self._rotation_history
        if secret_type:
            events = [e for e in events if e.secret_type == secret_type]
        return events[-limit:]

    def status(self) -> dict[str, Any]:
        """Return rotation status for all registered secrets."""
        now = datetime.now(timezone.utc)
        result: dict[str, Any] = {}
        for st, config in self._configs.items():
            days_until = (
                (config.next_rotation - now).days
                if config.next_rotation
                else None
            )
            result[st.value] = {
                "enabled": config.enabled,
                "interval_days": config.rotation_interval_days,
                "last_rotated": config.last_rotated.isoformat()
                if config.last_rotated
                else None,
                "next_rotation": config.next_rotation.isoformat()
                if config.next_rotation
                else None,
                "days_until_rotation": days_until,
                "overlap_active": bool(
                    self._overlap_expiry.get(st)
                    and self._overlap_expiry[st] > now  # type: ignore[operator]
                ),
                "overdue": days_until is not None and days_until < 0,
            }
        return result

    @staticmethod
    def _fingerprint(value: str | None) -> str:
        """Generate a non-reversible fingerprint of a secret."""
        if not value:
            return "none"
        return hashlib.sha256(value.encode()).hexdigest()[:16]

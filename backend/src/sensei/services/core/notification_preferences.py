"""
Notification Preferences Model and Service.

Per-user, per-channel notification preference management with
unsubscribe support (CAN-SPAM compliance).

Supports:
- Per-trigger-type preferences (enable/disable by channel)
- Global quiet hours
- Unsubscribe management with token-based verification
- Default preferences per role
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any
from uuid import uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


@dataclass
class ChannelPreference:
    """Preference for a specific notification channel."""

    enabled: bool = True
    frequency: str = "immediate"  # immediate | digest_hourly | digest_daily
    quiet_start: time | None = None  # e.g. 22:00
    quiet_end: time | None = None  # e.g. 07:00


@dataclass
class TriggerPreference:
    """User preference for a specific trigger type."""

    trigger_type: str
    in_app: ChannelPreference = field(
        default_factory=lambda: ChannelPreference(enabled=True)
    )
    email: ChannelPreference = field(
        default_factory=lambda: ChannelPreference(enabled=True)
    )
    push: ChannelPreference = field(
        default_factory=lambda: ChannelPreference(enabled=False)
    )
    sms: ChannelPreference = field(
        default_factory=lambda: ChannelPreference(enabled=False)
    )


@dataclass
class UserNotificationPreferences:
    """Complete notification preferences for a user."""

    user_id: str
    global_enabled: bool = True
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    trigger_preferences: dict[str, TriggerPreference] = field(
        default_factory=dict
    )
    unsubscribed_triggers: set[str] = field(default_factory=set)
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class NotificationPreferenceService(PersistentServiceMixin):
    """Manages per-user notification preferences.

    Usage::

        svc = NotificationPreferenceService()

        # Set preference
        svc.set_preference("user-1", "task_overdue", channel="email", enabled=False)

        # Check before sending
        if svc.should_deliver("user-1", "task_overdue", "email"):
            send_email(...)

        # Unsubscribe
        token = svc.generate_unsubscribe_token("user-1", "task_overdue")
        svc.process_unsubscribe(token)
    """

    SERVICE_NAME = "notification_preferences"

    def __init__(self) -> None:
        self._preferences: dict[str, UserNotificationPreferences] = {}
        self._unsubscribe_tokens: dict[str, dict[str, str]] = {}

    def get_preferences(self, user_id: str) -> UserNotificationPreferences:
        """Get or create preferences for a user."""
        if user_id not in self._preferences:
            self._preferences[user_id] = UserNotificationPreferences(
                user_id=user_id
            )
        return self._preferences[user_id]

    def set_preference(
        self,
        user_id: str,
        trigger_type: str,
        *,
        channel: str = "email",
        enabled: bool = True,
        frequency: str = "immediate",
    ) -> TriggerPreference:
        """Set a notification preference for a specific trigger and channel."""
        prefs = self.get_preferences(user_id)

        if trigger_type not in prefs.trigger_preferences:
            prefs.trigger_preferences[trigger_type] = TriggerPreference(
                trigger_type=trigger_type
            )

        tp = prefs.trigger_preferences[trigger_type]
        channel_pref = getattr(tp, channel, None)
        if channel_pref and isinstance(channel_pref, ChannelPreference):
            channel_pref.enabled = enabled
            channel_pref.frequency = frequency

        prefs.updated_at = datetime.now(timezone.utc)
        return tp

    def set_quiet_hours(
        self,
        user_id: str,
        start: time,
        end: time,
    ) -> None:
        """Set global quiet hours for a user."""
        prefs = self.get_preferences(user_id)
        prefs.quiet_hours_start = start
        prefs.quiet_hours_end = end
        prefs.updated_at = datetime.now(timezone.utc)

    def should_deliver(
        self,
        user_id: str,
        trigger_type: str,
        channel: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Check if a notification should be delivered to a user.

        Checks:
        1. Global enabled
        2. Trigger not unsubscribed
        3. Channel enabled for trigger
        4. Not in quiet hours
        """
        prefs = self._preferences.get(user_id)
        if not prefs:
            return True  # Default: deliver

        if not prefs.global_enabled:
            return False

        if trigger_type in prefs.unsubscribed_triggers:
            return False

        # Check trigger-specific preference
        tp = prefs.trigger_preferences.get(trigger_type)
        if tp:
            channel_pref = getattr(tp, channel, None)
            if channel_pref and isinstance(channel_pref, ChannelPreference):
                if not channel_pref.enabled:
                    return False

        # Check quiet hours
        check_time = (now or datetime.now(timezone.utc)).time()
        if prefs.quiet_hours_start and prefs.quiet_hours_end:
            if prefs.quiet_hours_start <= prefs.quiet_hours_end:
                # Same-day range (e.g. 09:00–17:00)
                if prefs.quiet_hours_start <= check_time <= prefs.quiet_hours_end:
                    return False
            else:
                # Cross-midnight range (e.g. 22:00–07:00)
                if check_time >= prefs.quiet_hours_start or check_time <= prefs.quiet_hours_end:
                    return False

        return True

    # ------------------------------------------------------------------
    # Unsubscribe management
    # ------------------------------------------------------------------

    def generate_unsubscribe_token(
        self, user_id: str, trigger_type: str
    ) -> str:
        """Generate a one-time unsubscribe token."""
        token = secrets.token_urlsafe(32)
        self._unsubscribe_tokens[token] = {
            "user_id": user_id,
            "trigger_type": trigger_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return token

    def process_unsubscribe(self, token: str) -> bool:
        """Process an unsubscribe token."""
        data = self._unsubscribe_tokens.pop(token, None)
        if not data:
            return False

        user_id = data["user_id"]
        trigger_type = data["trigger_type"]

        prefs = self.get_preferences(user_id)
        prefs.unsubscribed_triggers.add(trigger_type)
        prefs.updated_at = datetime.now(timezone.utc)

        logger.info(
            "User %s unsubscribed from %s", user_id, trigger_type
        )
        return True

    def resubscribe(self, user_id: str, trigger_type: str) -> None:
        """Re-subscribe a user to a trigger type."""
        prefs = self.get_preferences(user_id)
        prefs.unsubscribed_triggers.discard(trigger_type)
        prefs.updated_at = datetime.now(timezone.utc)

    def bulk_update(
        self, user_id: str, updates: dict[str, dict[str, bool]]
    ) -> None:
        """Bulk update preferences.

        *updates* maps trigger_type → {channel: enabled}.
        """
        for trigger_type, channels in updates.items():
            for channel, enabled in channels.items():
                self.set_preference(
                    user_id, trigger_type, channel=channel, enabled=enabled
                )

    def export_preferences(self, user_id: str) -> dict[str, Any]:
        """Export preferences as a JSON-serializable dict."""
        prefs = self.get_preferences(user_id)
        return {
            "user_id": prefs.user_id,
            "global_enabled": prefs.global_enabled,
            "quiet_hours": {
                "start": prefs.quiet_hours_start.isoformat()
                if prefs.quiet_hours_start
                else None,
                "end": prefs.quiet_hours_end.isoformat()
                if prefs.quiet_hours_end
                else None,
            },
            "triggers": {
                tt: {
                    "in_app": tp.in_app.enabled,
                    "email": tp.email.enabled,
                    "push": tp.push.enabled,
                    "sms": tp.sms.enabled,
                }
                for tt, tp in prefs.trigger_preferences.items()
            },
            "unsubscribed": list(prefs.unsubscribed_triggers),
        }

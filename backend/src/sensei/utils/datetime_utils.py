"""
Datetime utilities — timezone-aware everywhere.

Provides standard helpers to ensure all datetime values are
timezone-aware (UTC). All services should use these instead
of bare ``datetime.now()``.

Checklist item: #491
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

# Canonical UTC timezone
UTC = timezone.utc


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


def utc_today() -> date:
    """Return today's date in UTC."""
    return utc_now().date()


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware (UTC).

    - If naive → assume UTC and attach tzinfo.
    - If aware with non-UTC tz → convert to UTC.
    - If None → return None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_iso(dt: datetime | None) -> str | None:
    """Convert datetime to ISO 8601 string (with Z suffix)."""
    if dt is None:
        return None
    aware = ensure_utc(dt)
    assert aware is not None
    return aware.isoformat().replace("+00:00", "Z")


def from_iso(s: str | None) -> datetime | None:
    """Parse an ISO 8601 string to a timezone-aware datetime."""
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return ensure_utc(dt)


def seconds_ago(seconds: int) -> datetime:
    """Return a datetime N seconds in the past (UTC)."""
    return utc_now() - timedelta(seconds=seconds)


def hours_ago(hours: int) -> datetime:
    """Return a datetime N hours in the past (UTC)."""
    return utc_now() - timedelta(hours=hours)


def days_ago(days: int) -> datetime:
    """Return a datetime N days in the past (UTC)."""
    return utc_now() - timedelta(days=days)


def is_stale(dt: datetime, max_age_seconds: int) -> bool:
    """Return True if *dt* is older than *max_age_seconds*."""
    age = (utc_now() - ensure_utc(dt)).total_seconds()  # type: ignore[operator]
    return age > max_age_seconds


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def start_of_day(dt: datetime | None = None) -> datetime:
    """Return midnight (00:00) of the given datetime's date."""
    d = (dt or utc_now()).date()
    return datetime.combine(d, time.min, tzinfo=UTC)


def end_of_day(dt: datetime | None = None) -> datetime:
    """Return 23:59:59.999999 of the given datetime's date."""
    d = (dt or utc_now()).date()
    return datetime.combine(d, time.max, tzinfo=UTC)

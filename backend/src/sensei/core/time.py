"""Time helpers.

Python 3.12+ deprecates `datetime.utcnow()`.
These helpers provide UTC timestamps without using deprecated APIs.

We keep both:
- `now_utc()` -> timezone-aware UTC datetime
- `utcnow_naive()` -> naive UTC datetime (legacy DB columns / comparisons)
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return a timezone-aware UTC datetime."""

    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    """Return a naive UTC datetime (tzinfo=None).

    Use this when interacting with legacy naive `DateTime` columns.
    """
    import structlog
    logger = structlog.get_logger("sensei.core.time")
    logger.warning("utcnow_naive called: returning naive datetime. Consider migrating to timezone-aware.")

    return now_utc().replace(tzinfo=None)

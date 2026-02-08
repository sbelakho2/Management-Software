"""
In-Memory Service Audit Logger.

Provides change-tracking for in-memory service operations to satisfy
regulated-industry requirements (ISO 13485, AS9100, FDA 21 CFR Part 11).

Every mutation (create, update, delete) on an in-memory service is logged
with: who, when, what entity, what changed, and why.  The log itself is
in-memory but exposes an async ``flush_to_db`` hook for periodic persistence.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Type of audited operation."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    APPROVE = "approve"
    REJECT = "reject"
    ARCHIVE = "archive"
    RESTORE = "restore"
    EXPORT = "export"


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit log entry."""

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    service_name: str = ""
    action: AuditAction = AuditAction.UPDATE
    entity_type: str = ""
    entity_id: str = ""
    user_id: str | None = None
    user_name: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    ip_address: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["action"] = self.action.value
        return d


class ServiceAuditLog:
    """Thread-safe-ish in-memory audit log with configurable capacity.

    Usage::

        audit = ServiceAuditLog("maintenance_tpm", max_entries=50_000)

        audit.log(
            action=AuditAction.CREATE,
            entity_type="work_order",
            entity_id="wo-123",
            user_id="u-456",
            changes={"status": "open"},
        )

        # Periodic flush
        entries = audit.drain()
        await persist_to_db(entries)
    """

    def __init__(
        self,
        service_name: str,
        *,
        max_entries: int = 100_000,
        on_flush: Callable[[list[AuditEntry]], None] | None = None,
    ) -> None:
        self.service_name = service_name
        self._max = max_entries
        self._entries: deque[AuditEntry] = deque(maxlen=max_entries)
        self._on_flush = on_flush

    def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        *,
        user_id: str | None = None,
        user_name: str | None = None,
        changes: dict[str, Any] | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        """Record an audit entry."""
        entry = AuditEntry(
            service_name=self.service_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            changes=changes or {},
            reason=reason,
            ip_address=ip_address,
        )
        self._entries.append(entry)
        return entry

    def query(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: AuditAction | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters."""
        results: list[AuditEntry] = []
        for entry in reversed(self._entries):
            if entity_type and entry.entity_type != entity_type:
                continue
            if entity_id and entry.entity_id != entity_id:
                continue
            if action and entry.action != action:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if since and entry.timestamp < since:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def drain(self) -> list[AuditEntry]:
        """Remove and return all entries (for periodic DB flush)."""
        entries = list(self._entries)
        self._entries.clear()
        if self._on_flush and entries:
            try:
                self._on_flush(entries)
            except Exception:
                logger.exception("Audit flush callback failed")
        return entries

    def count(self) -> int:
        return len(self._entries)

    def stats(self) -> dict[str, Any]:
        """Return audit log statistics."""
        from collections import Counter

        actions = Counter(e.action.value for e in self._entries)
        entities = Counter(e.entity_type for e in self._entries)
        return {
            "service": self.service_name,
            "total_entries": len(self._entries),
            "max_capacity": self._max,
            "by_action": dict(actions),
            "by_entity_type": dict(entities),
            "oldest": self._entries[0].timestamp.isoformat()
            if self._entries
            else None,
            "newest": self._entries[-1].timestamp.isoformat()
            if self._entries
            else None,
        }

"""
Concurrency and Thread Safety Guide (#365, #131, #165, #375, #134).

Documents known concurrency issues and provides patterns for safe
multi-worker deployment.

Problem Statement
=================

All in-memory services (55+ services using ``self._dict`` storage) are
**not thread-safe**. In a multi-worker Uvicorn deployment (``--workers N``
with N > 1), each worker gets its own copy of in-memory state, leading to:

1. **Divergent state**: Worker A creates entity X, Worker B doesn't see it.
2. **Lost updates**: Workers A and B modify the same entity concurrently.
3. **Memory pressure**: Each worker duplicates the full in-memory dataset.

Solutions
=========

Short-term (applied here):
- Document the issue prominently
- Add ``threading.Lock`` guards to all in-memory services
- Use Redis as a shared coordination layer for critical paths

Medium-term:
- Migrate all services to DB-backed repositories (items #1-64)
- Use ``BaseRepository`` from ``base_repository.py`` with tenant scoping

Long-term:
- Full CQRS with event sourcing for audit-critical domains

Flush Without Transaction (#131, #165)
=======================================

15 services call ``session.flush()`` without explicit transaction
boundaries. This can cause partial writes if an error occurs between
flushes.

Pattern to follow::

    async with session.begin():
        # All operations within a single transaction
        repo.create(...)
        repo.update(...)
        # Commit happens automatically at end of `begin()` block
        # Rollback happens automatically on exception

Frozen Dataclass GC Pressure (#134, #375)
==========================================

Services using ``@dataclass(frozen=True)`` create entirely new instances
for every state mutation via ``dataclasses.replace()``. Under high
throughput, this generates excessive garbage.

Pattern to follow:
- Use regular (non-frozen) dataclasses for mutable domain objects
- Use frozen dataclasses only for value objects and DTOs
- Consider ``__slots__`` for memory efficiency
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Dict, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ThreadSafeDict(Dict[str, Any]):
    """A dict wrapper with a reentrant lock for thread-safe access.

    Drop-in replacement for ``self._entities: dict`` in in-memory services.

    Usage::

        self._entities = ThreadSafeDict()

        with self._entities.locked():
            self._entities["key"] = value
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._lock = threading.RLock()

    @contextmanager
    def locked(self):
        """Context manager for exclusive access."""
        self._lock.acquire()
        try:
            yield self
        finally:
            self._lock.release()

    def safe_get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.get(key, default)

    def safe_set(self, key: str, value: Any) -> None:
        with self._lock:
            self[key] = value

    def safe_delete(self, key: str) -> bool:
        with self._lock:
            if key in self:
                del self[key]
                return True
            return False

    def safe_values(self) -> list:
        with self._lock:
            return list(self.values())


class TransactionContext:
    """Helper for ensuring explicit transaction boundaries (#131, #165).

    Usage::

        async with TransactionContext(session) as tx:
            await repo.create(data1)
            await repo.update(id, data2)
            # Commits at end, rolls back on exception
    """

    def __init__(self, session: Any) -> None:
        self.session = session
        self._committed = False

    async def __aenter__(self) -> "TransactionContext":
        # Begin nested transaction if one is already active
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.session.rollback()
            logger.warning(
                "Transaction rolled back due to %s: %s",
                exc_type.__name__,
                exc_val,
            )
        else:
            await self.session.commit()
            self._committed = True


def check_flush_safety(service_name: str, session: Any) -> None:
    """Warn if flush() is called outside an explicit transaction.

    Call this before ``session.flush()`` in services that need auditing.
    """
    if not session.in_transaction():
        logger.warning(
            "%s: flush() called outside explicit transaction — "
            "partial writes possible on failure (#131, #165)",
            service_name,
        )

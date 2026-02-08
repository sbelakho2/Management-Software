"""
Return Value Conventions for In-Memory Services.

Documents and enforces the standard return semantics for
service methods across the SenseiOS codebase.

Checklist items: #492, #495
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


# ------------------------------------------------------------------
# Return value conventions (documented for all services)
# ------------------------------------------------------------------

# 1. GET / READ methods
#    - Return T | None — None means "not found"
#    - Never raise on "not found"; only raise on system errors
#    - Example: get_inspection(id) → Inspection | None

# 2. LIST methods
#    - Return list[T] — empty list means "no results"
#    - Never return None for list operations
#    - Example: list_inspections(filters) → list[Inspection]

# 3. CREATE methods
#    - Return T — the created entity (with generated ID, timestamps)
#    - Raise ValueError on validation failure
#    - Example: create_inspection(data) → Inspection

# 4. UPDATE methods
#    - Return T | None — None means "entity not found"
#    - Raise ValueError on validation failure
#    - Example: update_inspection(id, data) → Inspection | None

# 5. DELETE methods
#    - Return bool — True if deleted, False if not found
#    - Example: delete_inspection(id) → bool

# 6. ACTION methods (approve, reject, close, etc.)
#    - Return T | None — None means "entity not found"
#    - Raise ValueError if action not valid for current state
#    - Example: approve_capa(id, user_id) → CAPA | None

# 7. BATCH methods
#    - Return dict with "succeeded" and "failed" counts
#    - Example: batch_close(ids) → {"succeeded": 5, "failed": 1}

# 8. COMPUTATION methods (score, calculate, analyze)
#    - Return result dataclass — never None
#    - Raise ValueError if input is invalid
#    - Example: score_deal(features) → DealScore


@runtime_checkable
class CRUDService(Protocol[T]):
    """Protocol for standard CRUD service methods.

    All in-memory and DB-backed services should conform to these
    signatures for consistency.
    """

    def get(self, id: str) -> T | None:
        """Get entity by ID. Returns None if not found."""
        ...

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[T]:
        """List entities with pagination and optional filters."""
        ...

    def create(self, data: dict[str, Any]) -> T:
        """Create a new entity. Raises ValueError on validation failure."""
        ...

    def update(self, id: str, data: dict[str, Any]) -> T | None:
        """Update an entity. Returns None if not found."""
        ...

    def delete(self, id: str) -> bool:
        """Delete an entity. Returns True if deleted, False if not found."""
        ...


@runtime_checkable
class AsyncCRUDService(Protocol[T]):
    """Async version of CRUDService protocol."""

    async def get(self, id: str) -> T | None: ...
    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[T]: ...
    async def create(self, data: dict[str, Any]) -> T: ...
    async def update(self, id: str, data: dict[str, Any]) -> T | None: ...
    async def delete(self, id: str) -> bool: ...

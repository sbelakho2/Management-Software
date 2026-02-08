# ADR-0003: Admin / Superuser Role Aliases

## Status
Accepted

## Context
The codebase uses two terms — `"admin"` and `"superuser"` — to refer to
the same elevated access level. This inconsistency causes confusion:
- Some role checks look for `"admin"` only.
- Seeded accounts may have `is_superuser=True` on the User model.
- The `RoleChecker` in `deps.py` treats both as equivalent.

## Decision
- **Canonical role name:** `"admin"`.
- **`"superuser"` is a backward-compatible alias.** All authorization
  checks (`RoleChecker`, `require_admin`, audit logging) accept both
  strings as equivalent.
- New code should use `"admin"` exclusively.
- The `is_superuser` boolean on the User model is retained for database
  compatibility but should not be relied upon for access decisions.

## Consequences
**Easier:**
- Clear guidance for new developers: use `"admin"`.
- Existing seeded data continues to work.
- Single source of truth in `deps.py`.

**Harder:**
- Legacy references to `"superuser"` must be kept working.
- Cannot remove `is_superuser` column without a migration.

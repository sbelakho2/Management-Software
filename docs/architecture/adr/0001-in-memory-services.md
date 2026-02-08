# ADR-0001: In-Memory Service Pattern

## Status
Accepted

## Context
Sensei OS services (finance, HR, production, quality, AI) need to be
developed, tested, and iterated on rapidly. Using a full database-backed
implementation from the start would slow development and make testing
complex.

## Decision
All domain services use an **in-memory, pure-Python pattern** during the
current development phase:
- State is stored in Python dicts/lists within service instances.
- Services are stateless across process restarts.
- Persistence to PostgreSQL is planned for a later phase (Plan item 22.10).
- Each service class has a well-defined interface so it can be swapped to a
  DB-backed implementation without changing callers.

## Consequences
**Easier:**
- Rapid development; no migration management during design phase.
- Trivial to unit-test; no database fixtures needed.
- Clear service interfaces enforced by necessity.

**Harder:**
- Data is lost on process restart (acceptable for development).
- Multi-worker deployments see divergent state.
- Must plan and execute DB migration for each service before production.

**Migration path:**
Each service will be migrated to PostgreSQL/SQLAlchemy individually,
following the pattern established by `factory_launchpad.py` which has
both an in-memory and DB-backed implementation.

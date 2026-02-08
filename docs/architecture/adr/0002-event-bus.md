# ADR-0002: Domain Event Bus

## Status
Accepted

## Context
Multiple services need to react to events in other domains:
- Quality finding created → trigger CAPA workflow
- SPC out-of-control → notify maintenance
- Cost rollup completed → update KPI dashboard
- CAPA closure → update risk register

Direct cross-service imports create tight coupling (#356–361). A protocol
provider pattern helps but doesn't solve the many-to-many notification
problem.

## Decision
Introduce an **in-process, async-aware event bus** at
`sensei.services.event_bus`:

- Events are dataclasses extending `DomainEvent`.
- Handlers are registered via `event_bus.subscribe(EventType, handler)`.
- Publishing is via `await event_bus.publish(event)`.
- Handlers execute sequentially; failures are logged but don't block others.
- The bus is a module-level singleton (`event_bus`).

## Consequences
**Easier:**
- Services can emit events without knowing who consumes them.
- Adding new reactions to existing events requires zero changes to the emitter.
- Testing: `event_bus.clear()` in test fixtures.

**Harder:**
- Event ordering is implicit (registration order).
- Debugging: need structured logging to trace event flow.
- Not a replacement for a message broker; in-process only.

**Future:**
When the system scales beyond a single process, the event bus can be
backed by Redis Pub/Sub or a proper message broker (RabbitMQ, NATS)
with the same `DomainEvent` interface.

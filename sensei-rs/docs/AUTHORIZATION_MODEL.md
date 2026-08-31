# Authorization Model

## Layers (item 18-20)

Hierarchical RBAC (NIST) + ReBAC resource scope + narrow ABAC attributes:

- Roles: `role_hierarchy` in sensei-auth (manager inherits operator; site_manager
  inherits manager+quality+maintenance; admin inherits site_manager). Resolved
  transitively by `permissions_for_role` and `has_permission_for_tenant`.
- Relationships: role slots (`role_slots`) scope principals to sites (migration 114).
- Attributes: country, employment status, shift, device assurance.

ALLOW = role_permission AND relationship_scope AND contextual_conditions AND
NO explicit deny AND separation-of-duty OK.

## Separation (items 20/40)

- ORG hierarchy ≠ AUTHORIZATION hierarchy (a CEO's operational queries do not load
  every employee's sensitive data).
- ANALYTICAL VISIBILITY ≠ TRANSACTIONAL AUTHORITY (aggregates may be visible;
  personal records require explicit authorization).

## Models never enforce authorization (item 25)

Deterministic Rust: `require_permission` at every route; PolicyEngine filters the
toolset; every tool re-checks authorization at execution. The model's tool list is
not the security boundary.

## Cache isolation (item 23)

Cache keys include trust domain + policy revision + access digest + data class
(mandatory salting — a plant manager's restricted context is never reused for
another principal).

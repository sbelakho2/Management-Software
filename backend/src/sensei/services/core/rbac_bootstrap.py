from __future__ import annotations

import structlog
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from sensei.models.user import Role, User, UserRole

logger = structlog.get_logger(__name__)


async def ensure_core_users_have_roles(session) -> None:
    """Ensure critical built-in accounts have the expected RBAC roles.

    Why this exists:
    - Some seeded users (notably `ceo@sensei.os`) can be created with `is_superuser=True`
      but without any `user_roles` assignments.
    - The UI authorization relies on explicit RBAC roles like `ceo`.

    This is intentionally minimal and safe:
    - It only adds missing Role/UserRole rows.
    - It does not remove roles or change permissions.
    
    IMPORTANT: This function is safe for concurrent execution during horizontal
    scaling deployments. It uses PostgreSQL ON CONFLICT for atomic upserts.
    """

    async def ensure_role(name: str) -> Role:
        """Create or get a role, handling race conditions atomically."""
        # First, try to get existing role
        role = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if role is not None:
            return role
        
        # Use INSERT ... ON CONFLICT for atomic upsert
        # This handles the race condition where another instance creates the role
        # between our SELECT and INSERT
        try:
            stmt = pg_insert(Role).values(
                name=name,
                display_name=name.replace("_", " ").strip().title(),
                description=f"Auto-created system role: {name}",
                role_type=name,
                is_system=True,
                is_active=True,
            ).on_conflict_do_nothing(index_elements=['name'])
            
            await session.execute(stmt)
            await session.flush()
            
            # Re-fetch to get the role (whether we created it or not)
            role = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
            if role is not None:
                logger.info("Ensured RBAC role exists", role=name)
                return role
            
            # Shouldn't happen, but handle gracefully
            raise RuntimeError(f"Failed to ensure role {name} exists after upsert")
            
        except IntegrityError:
            # Another process created it between our check and insert
            # This is expected in race conditions, just fetch it
            await session.rollback()
            role = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
            if role is not None:
                return role
            raise

    async def ensure_user_has_role(email: str, role_name: str) -> None:
        """Assign a role to a user if not already assigned, handling race conditions."""
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            return

        role = await ensure_role(role_name)

        # Check for existing assignment
        existing = (
            await session.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            )
        ).scalar_one_or_none()

        if existing is None:
            # Use INSERT ... ON CONFLICT for atomic upsert of user role assignment
            try:
                stmt = pg_insert(UserRole).values(
                    user_id=user.id,
                    role_id=role.id,
                    is_active=True,
                ).on_conflict_do_update(
                    index_elements=['user_id', 'role_id'],
                    set_={'is_active': True}
                )
                await session.execute(stmt)
                await session.flush()
                logger.info("Assigned RBAC role", email=email, role=role_name)
            except IntegrityError:
                # Race condition - another process assigned the role
                await session.rollback()
                logger.debug("Role already assigned by another process", email=email, role=role_name)
        else:
            if existing.is_active is not True:
                existing.is_active = True
                logger.info("Re-activated RBAC role assignment", email=email, role=role_name)

    # CEO must have explicit `ceo` role for full UI access.
    await ensure_user_has_role("ceo@sensei.os", "ceo")

    # If there is a built-in admin account, ensure it has `admin` role.
    await ensure_user_has_role("admin@sensei.os", "admin")

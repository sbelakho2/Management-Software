from __future__ import annotations

import structlog
from sqlalchemy import select

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
    """

    async def ensure_role(name: str) -> Role:
        role = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if role is None:
            role = Role(
                name=name,
                display_name=name.replace("_", " ").strip().title(),
                description=f"Auto-created system role: {name}",
                role_type=name,
                is_system=True,
                is_active=True,
            )
            session.add(role)
            await session.flush()
            logger.info("Created missing RBAC role", role=name)
        return role

    async def ensure_user_has_role(email: str, role_name: str) -> None:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            return

        role = await ensure_role(role_name)

        existing = (
            await session.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
            )
        ).scalar_one_or_none()

        if existing is None:
            session.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
            await session.flush()
            logger.info("Assigned missing RBAC role", email=email, role=role_name)
        else:
            if existing.is_active is not True:
                existing.is_active = True
                logger.info("Re-activated RBAC role assignment", email=email, role=role_name)

    # CEO must have explicit `ceo` role for full UI access.
    await ensure_user_has_role("ceo@sensei.os", "ceo")

    # If there is a built-in admin account, ensure it has `admin` role.
    await ensure_user_has_role("admin@sensei.os", "admin")

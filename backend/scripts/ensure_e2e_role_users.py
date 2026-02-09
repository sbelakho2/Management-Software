import asyncio
import os
from sqlalchemy import or_, select

from sensei.core.database import async_session_factory
from sensei.core.security import hash_password
from sensei.models.user import Role, User, UserRole, UserStatus


EMAIL_DOMAIN = os.getenv("E2E_EMAIL_DOMAIN", "senseitest.com")
PASSWORD = os.getenv("E2E_PASSWORD", "TestPassword123!")

ROLES: list[str] = [
    "admin",
    "ceo",
    "executive",
    "gm",
    "sales_rep",
    "sales_engineer",
    "estimator",
    "quality",
    "quality_inspector",
    "supervisor",
    "operator",
    "finance",
    "accountant",
    "hr",
    "it",
    "security",
    "warehouse",
    "shipping_receiver",
    "auditor",
    "supply_chain",
    "purchasing",
    "maintenance",
    "maintenance_tech",
    "team_lead",
]


def _display_name(role: str) -> str:
    return role.replace("_", " ").strip().title()


async def main() -> None:
    # Safety guard: refuse to run in production
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
    if env in ("production", "prod"):
        print("ERROR: This script must NOT be run in production environments!")
        print("       It creates test users with known passwords.")
        raise SystemExit(1)

    password_hash = hash_password(PASSWORD)

    created_users = 0
    updated_users = 0
    created_roles = 0
    created_assignments = 0

    async with async_session_factory() as session:
        for role_name in ROLES:
            # Ensure role exists
            role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
            if role is None:
                role = Role(
                    name=role_name,
                    display_name=_display_name(role_name),
                    role_type=role_name,
                    is_system=True,
                    is_active=True,
                )
                session.add(role)
                await session.flush()
                created_roles += 1

            email = f"{role_name}@{EMAIL_DOMAIN}"
            username = role_name

            # Find user by email OR username
            user = (
                await session.execute(
                    select(User).where(or_(User.email == email, User.username == username))
                )
            ).scalar_one_or_none()

            if user is None:
                user = User(
                    email=email,
                    username=username,
                    password_hash=password_hash,
                    first_name="E2E",
                    last_name=_display_name(role_name).replace(" ", ""),
                    status=UserStatus.ACTIVE.value,
                    is_superuser=(role_name == "admin"),
                    email_verified=True,
                    totp_enabled=False,
                    totp_secret=None,
                    backup_codes=None,
                    failed_login_attempts=0,
                    locked_until=None,
                    must_change_password=False,
                )
                session.add(user)
                await session.flush()
                created_users += 1
            else:
                # Normalize credentials so Playwright can log in
                user.email = email
                user.username = username
                user.password_hash = password_hash
                user.status = UserStatus.ACTIVE.value
                user.email_verified = True
                user.totp_enabled = False
                user.totp_secret = None
                user.backup_codes = None
                user.failed_login_attempts = 0
                user.locked_until = None
                user.must_change_password = False
                if role_name == "admin":
                    user.is_superuser = True
                updated_users += 1

            # Ensure role assignment exists
            assignment = (
                await session.execute(
                    select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
                )
            ).scalar_one_or_none()
            if assignment is None:
                session.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
                created_assignments += 1
            else:
                assignment.is_active = True

        await session.commit()

    print("E2E role users ensured.")
    print(f"Roles created: {created_roles}")
    print(f"Users created: {created_users}")
    print(f"Users updated: {updated_users}")
    print(f"Role assignments created: {created_assignments}")
    print(f"Email domain: {EMAIL_DOMAIN}")


if __name__ == "__main__":
    asyncio.run(main())

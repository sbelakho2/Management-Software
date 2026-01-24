import asyncio
import typer
from typing import Optional
from rich.console import Console
from sqlalchemy import select

from sensei.core.database import async_session_factory
from sensei.models.user import User, Role, UserRole, UserStatus, RoleType
from sensei.core.security import hash_password

app = typer.Typer(name="user", help="User management CLI")
console = Console()

@app.command()
def create_admin(
    email: str = typer.Option(..., help="Admin email address"),
    password: str = typer.Option(..., help="Admin password"),
    username: Optional[str] = typer.Option(None, help="Username (defaults to email)"),
    first_name: str = typer.Option("Admin", help="First name"),
    last_name: str = typer.Option("User", help="Last name"),
):
    """Create a new admin user."""
    asyncio.run(_create_admin_async(email, password, username, first_name, last_name))

async def _create_admin_async(email, password, username, first_name, last_name):
    if not username:
        username = email.split("@")[0]
        
    async with async_session_factory() as session:
        # Check if user already exists
        user_result = await session.execute(select(User).where(User.email == email))
        if user_result.scalar_one_or_none():
            console.print(f"[red]Error:[/red] User with email {email} already exists.")
            return

        # Ensure admin role exists
        role_result = await session.execute(select(Role).where(Role.name == RoleType.ADMIN.value))
        admin_role: Role | None = role_result.scalar_one_or_none()
        if not admin_role:
            admin_role = Role(
                name=RoleType.ADMIN.value,
                display_name="Administrator",
                role_type=RoleType.ADMIN.value,
                is_system=True
            )
            session.add(admin_role)
            await session.flush()

        # Create user
        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            status=UserStatus.ACTIVE.value,
            is_superuser=True,
            email_verified=True
        )
        session.add(user)
        await session.flush()

        # Assign admin role
        user_role = UserRole(user_id=user.id, role_id=admin_role.id)
        session.add(user_role)
        
        await session.commit()
        console.print(f"[green]Success:[/green] Admin user {email} created successfully.")

if __name__ == "__main__":
    app()

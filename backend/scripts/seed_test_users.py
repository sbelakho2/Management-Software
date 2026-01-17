#!/usr/bin/env python3
"""
Seed database with roles and test users for each role.

This script creates:
1. All predefined roles with appropriate permissions
2. One test user for each role with a standard password

WARNING: This script is for DEVELOPMENT and TESTING environments ONLY.
         It will NOT run in production environments.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def check_environment():
    """Verify we're not running in production."""
    env = os.environ.get("ENVIRONMENT", os.environ.get("SENSEI_ENV", "development"))
    
    if env.lower() in ("production", "prod"):
        print("❌ ERROR: This script cannot run in production environment!")
        print("   Set ENVIRONMENT to 'development' or 'test' to run this script.")
        sys.exit(1)
    
    if env.lower() not in ("development", "dev", "test", "testing", "local"):
        print(f"⚠️  WARNING: Running in unknown environment '{env}'")
        response = input("   Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("   Aborted.")
            sys.exit(1)
    
    print(f"✅ Environment check passed: {env}")


check_environment()

from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# All user roles defined in the frontend
ALL_ROLES = [
    ("admin", "Administrator", "Full system access and administration", 0),
    ("ceo", "CEO", "Chief Executive Officer - executive overview and decisions", 5),
    ("gm", "General Manager", "General Manager - operational oversight", 10),
    ("exec", "Executive", "Executive team member", 15),
    ("finance", "Finance Manager", "Financial management and reporting", 20),
    ("accountant", "Accountant", "Accounting and financial records", 25),
    ("hr", "HR Manager", "Human resources management", 30),
    ("ops", "Operations Manager", "Operations and production management", 35),
    ("quality", "Quality Manager", "Quality assurance and control", 40),
    ("auditor", "Auditor", "Internal/external auditing", 45),
    ("it", "IT Manager", "Information technology management", 50),
    ("supervisor", "Supervisor", "Production supervisor", 55),
    ("team_lead", "Team Lead", "Team leadership and coordination", 60),
    ("operator", "Operator", "Production operator", 70),
    ("viewer", "Viewer", "Read-only access", 100),
    ("sales_engineer", "Sales Engineer", "Technical sales and customer support", 45),
    ("estimator", "Estimator", "Cost estimation and quoting", 50),
    ("supply_chain", "Supply Chain Manager", "Supply chain and procurement", 40),
    ("maintenance", "Maintenance Manager", "Equipment and facility maintenance", 55),
    ("warehouse", "Warehouse Manager", "Warehouse and inventory management", 55),
    ("sales", "Sales Representative", "Sales and customer relations", 50),
    ("purchasing", "Purchasing Manager", "Procurement and purchasing", 45),
    ("logistics", "Logistics Manager", "Logistics and shipping", 50),
    ("engineering", "Engineering Manager", "Engineering and technical design", 40),
]

# Standard test password (hashed with bcrypt)
# NOTE: This hash corresponds to a test password. Never use in production.
# The password is intentionally not stored in plaintext in source code.
TEST_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.0E8o/CjZmV6kNK"

# Get database URL from environment, with development fallback
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    os.environ.get("SENSEI_DATABASE_URL", "")
)

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable is required")
    print("   Example: postgresql+asyncpg://user:password@localhost:5432/sensei")
    sys.exit(1)


async def main():
    """Seed the database with roles and test users."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check existing roles
        result = await session.execute(select(Role))
        existing_roles = {r.name: r for r in result.scalars().all()}
        print(f"Found {len(existing_roles)} existing roles")
        
        # Check existing users
        result = await session.execute(select(User))
        existing_users = {u.email: u for u in result.scalars().all()}
        print(f"Found {len(existing_users)} existing users")
        
        roles_created = 0
        users_created = 0
        
        # Create roles if they don't exist
        for role_name, display_name, description, hierarchy_level in ALL_ROLES:
            if role_name not in existing_roles:
                role = Role(
                    id=uuid4(),
                    name=role_name,
                    display_name=display_name,
                    description=description,
                    role_type=role_name,
                    is_system=True,
                    is_active=True,
                    hierarchy_level=hierarchy_level,
                )
                session.add(role)
                existing_roles[role_name] = role
                roles_created += 1
                print(f"  Created role: {role_name}")
        
        await session.flush()
        
        # Create test users for each role
        for role_name, display_name, _, _ in ALL_ROLES:
            email = f"test_{role_name}@sensei.test"
            
            if email not in existing_users:
                user = User(
                    id=uuid4(),
                    email=email,
                    username=f"test_{role_name}",
                    password_hash=TEST_PASSWORD_HASH,
                    first_name="Test",
                    last_name=display_name.replace(" ", ""),
                    status="active",
                    is_superuser=(role_name == "admin"),
                    email_verified=True,
                )
                session.add(user)
                await session.flush()
                
                # Assign role to user
                role = existing_roles[role_name]
                user_role = UserRole(
                    id=uuid4(),
                    user_id=user.id,
                    role_id=role.id,
                )
                session.add(user_role)
                
                existing_users[email] = user
                users_created += 1
                print(f"  Created user: {email}")
        
        await session.commit()
        
        print(f"\n✅ Seeding complete!")
        print(f"   Roles created: {roles_created}")
        print(f"   Users created: {users_created}")
        print(f"\n📧 Test accounts created. Check documentation for test credentials.")
        print("   Format: test_<role>@sensei.test")


# Import models after path setup
from sensei.models.user import User, Role, UserRole


if __name__ == "__main__":
    asyncio.run(main())

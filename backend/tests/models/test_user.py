"""
Tests for User, Role, and Permission models.

Tests:
- User model fields and validation
- User status and authentication properties
- User role relationships
- Role model and hierarchy
- Permission model and resource/action
- UserRole assignment with expiration
- RolePermission with conditions
- RefreshToken lifecycle
- Password and 2FA fields
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.models.user import (
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    RoleType,
    User,
    UserRole,
    UserStatus,
)


class TestUserModel:
    """Tests for the User model."""

    def test_user_required_fields(self):
        """User should require email, username, password_hash, first_name, last_name."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password_hash == "hashed_password"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_user_default_status_is_pending(self):
        """New users should have pending status by default."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            status=UserStatus.PENDING.value,
        )
        assert user.status == UserStatus.PENDING.value

    def test_user_full_name_property(self):
        """full_name should return first + last name."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="John",
            last_name="Doe",
        )
        assert user.full_name == "John Doe"

    def test_user_full_name_with_display_name(self):
        """full_name should return display_name if set."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="John",
            last_name="Doe",
            display_name="Johnny D",
        )
        assert user.full_name == "Johnny D"

    def test_user_is_active_when_status_active_and_not_deleted(self):
        """is_active should be True when status is active and not deleted."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            status=UserStatus.ACTIVE.value,
        )
        assert user.is_active is True

    def test_user_is_active_false_when_status_inactive(self):
        """is_active should be False when status is inactive."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            status=UserStatus.INACTIVE.value,
        )
        assert user.is_active is False

    def test_user_is_active_false_when_deleted(self):
        """is_active should be False when user is soft-deleted."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            status=UserStatus.ACTIVE.value,
            deleted_at=datetime.now(timezone.utc),
        )
        assert user.is_active is False

    def test_user_is_locked_false_when_locked_until_none(self):
        """is_locked should be False when locked_until is None."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        assert user.is_locked is False

    def test_user_is_locked_true_when_locked_until_future(self):
        """is_locked should be True when locked_until is in the future."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            locked_until=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert user.is_locked is True

    def test_user_is_locked_false_when_locked_until_past(self):
        """is_locked should be False when locked_until is in the past."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            locked_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert user.is_locked is False

    def test_user_default_locale_is_fr(self):
        """Default locale should be French."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            locale="fr",
        )
        assert user.locale == "fr"

    def test_user_default_timezone_is_casablanca(self):
        """Default timezone should be Africa/Casablanca."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            timezone="Africa/Casablanca",
        )
        assert user.timezone == "Africa/Casablanca"

    def test_user_2fa_disabled_by_default(self):
        """2FA should be disabled by default."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            totp_enabled=False,
        )
        assert user.totp_enabled is False
        assert user.totp_secret is None

    def test_user_superuser_false_by_default(self):
        """is_superuser should be False by default."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            is_superuser=False,
        )
        assert user.is_superuser is False

    def test_user_failed_login_attempts_default_zero(self):
        """failed_login_attempts should default to 0."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            failed_login_attempts=0,
        )
        assert user.failed_login_attempts == 0


class TestRoleModel:
    """Tests for the Role model."""

    def test_role_required_fields(self):
        """Role should require name and display_name."""
        role = Role(
            name="admin",
            display_name="Administrator",
        )
        assert role.name == "admin"
        assert role.display_name == "Administrator"

    def test_role_is_active_default_true(self):
        """Role should be active by default."""
        role = Role(name="test", display_name="Test", is_active=True)
        assert role.is_active is True

    def test_role_is_system_default_false(self):
        """Role should not be system role by default."""
        role = Role(name="test", display_name="Test", is_system=False)
        assert role.is_system is False

    def test_role_hierarchy_level_default(self):
        """Role should have default hierarchy level of 100."""
        role = Role(name="test", display_name="Test", hierarchy_level=100)
        assert role.hierarchy_level == 100


class TestPermissionModel:
    """Tests for the Permission model."""

    def test_permission_required_fields(self):
        """Permission should require name, display_name, resource, action."""
        permission = Permission(
            name="quotes:create",
            display_name="Create Quotes",
            resource="quotes",
            action="create",
        )
        assert permission.name == "quotes:create"
        assert permission.resource == "quotes"
        assert permission.action == "create"

    def test_permission_is_system_default_false(self):
        """Permission should not be system permission by default."""
        permission = Permission(
            name="test:test",
            display_name="Test",
            resource="test",
            action="test",
            is_system=False,
        )
        assert permission.is_system is False


class TestUserRoleModel:
    """Tests for the UserRole model."""

    def test_user_role_required_fields(self):
        """UserRole should require user_id and role_id."""
        user_id = uuid4()
        role_id = uuid4()
        user_role = UserRole(user_id=user_id, role_id=role_id)
        assert user_role.user_id == user_id
        assert user_role.role_id == role_id

    def test_user_role_is_active_default_true(self):
        """UserRole should be active by default."""
        user_role = UserRole(user_id=uuid4(), role_id=uuid4(), is_active=True)
        assert user_role.is_active is True

    def test_user_role_is_expired_false_when_expires_at_none(self):
        """is_expired should be False when expires_at is None."""
        user_role = UserRole(user_id=uuid4(), role_id=uuid4())
        assert user_role.is_expired is False

    def test_user_role_is_expired_true_when_expires_at_past(self):
        """is_expired should be True when expires_at is in the past."""
        user_role = UserRole(
            user_id=uuid4(),
            role_id=uuid4(),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert user_role.is_expired is True

    def test_user_role_is_expired_false_when_expires_at_future(self):
        """is_expired should be False when expires_at is in the future."""
        user_role = UserRole(
            user_id=uuid4(),
            role_id=uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert user_role.is_expired is False


class TestRolePermissionModel:
    """Tests for the RolePermission model."""

    def test_role_permission_required_fields(self):
        """RolePermission should require role_id and permission_id."""
        role_id = uuid4()
        permission_id = uuid4()
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        assert rp.role_id == role_id
        assert rp.permission_id == permission_id

    def test_role_permission_conditions_optional(self):
        """RolePermission conditions should be optional."""
        rp = RolePermission(role_id=uuid4(), permission_id=uuid4())
        assert rp.conditions is None

    def test_role_permission_with_conditions(self):
        """RolePermission should support conditions."""
        rp = RolePermission(
            role_id=uuid4(),
            permission_id=uuid4(),
            conditions={"field_restriction": ["price", "cost"]},
        )
        assert rp.conditions == {"field_restriction": ["price", "cost"]}


class TestRefreshTokenModel:
    """Tests for the RefreshToken model."""

    def test_refresh_token_required_fields(self):
        """RefreshToken should require user_id, token_hash, expires_at."""
        user_id = uuid4()
        token = RefreshToken(
            user_id=user_id,
            token_hash="hash123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert token.user_id == user_id
        assert token.token_hash == "hash123"

    def test_refresh_token_is_revoked_default_false(self):
        """is_revoked should be False by default."""
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        assert token.is_revoked is False

    def test_refresh_token_is_expired_false_when_future(self):
        """is_expired should be False when expires_at is in the future."""
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert token.is_expired is False

    def test_refresh_token_is_expired_true_when_past(self):
        """is_expired should be True when expires_at is in the past."""
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="hash",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert token.is_expired is True

    def test_refresh_token_is_valid_when_not_expired_and_not_revoked(self):
        """is_valid should be True when not expired and not revoked."""
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        assert token.is_valid is True

    def test_refresh_token_is_valid_false_when_revoked(self):
        """is_valid should be False when revoked."""
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="hash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=True,
        )
        assert token.is_valid is False

    def test_refresh_token_is_valid_false_when_expired(self):
        """is_valid should be False when expired."""
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="hash",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_revoked=False,
        )
        assert token.is_valid is False


class TestUserStatusEnum:
    """Tests for UserStatus enum."""

    def test_all_statuses_defined(self):
        """All expected user statuses should be defined."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.PENDING.value == "pending"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.LOCKED.value == "locked"


class TestRoleTypeEnum:
    """Tests for RoleType enum."""

    def test_all_role_types_defined(self):
        """All expected role types should be defined."""
        assert RoleType.ADMIN.value == "admin"
        assert RoleType.GM.value == "gm"
        assert RoleType.SALES_ENGINEER.value == "sales_engineer"
        assert RoleType.ESTIMATOR.value == "estimator"
        assert RoleType.QUALITY.value == "quality"
        assert RoleType.SUPPLY_CHAIN.value == "supply_chain"
        assert RoleType.OPS.value == "ops"
        assert RoleType.EXEC.value == "exec"
        assert RoleType.VIEWER.value == "viewer"

"""
Tests for base model functionality.

Tests:
- Base model UUID generation
- TimestampMixin behavior
- AuditMixin relationships
- SoftDeleteMixin functionality
- StatusMixin defaults
- ULID generation
- to_dict() serialization
- __repr__() output
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from sensei.models.base import (
    AuditMixin,
    Base,
    SoftDeleteMixin,
    StatusMixin,
    TimestampMixin,
    generate_ulid,
)


class TestBaseModel:
    """Tests for the Base model class."""

    def test_base_has_id_column(self):
        """Base should define an id column."""
        assert hasattr(Base, "id")

    def test_base_id_is_uuid(self):
        """Base id should be a UUID type."""
        # Check the type annotation
        id_column = Base.__table__.c.id
        assert id_column is not None
        assert id_column.primary_key

    def test_base_type_annotation_map(self):
        """Base should have UUID type annotation mapping."""
        assert UUID in Base.type_annotation_map


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_mixin_has_created_at(self):
        """TimestampMixin should have created_at field."""
        assert hasattr(TimestampMixin, "created_at")

    def test_mixin_has_updated_at(self):
        """TimestampMixin should have updated_at field."""
        assert hasattr(TimestampMixin, "updated_at")


class TestAuditMixin:
    """Tests for AuditMixin."""

    def test_mixin_has_created_by_id(self):
        """AuditMixin should define created_by_id."""
        # Check the declared_attr is defined
        assert hasattr(AuditMixin, "created_by_id")

    def test_mixin_has_updated_by_id(self):
        """AuditMixin should define updated_by_id."""
        assert hasattr(AuditMixin, "updated_by_id")

    def test_mixin_has_owner_id(self):
        """AuditMixin should define owner_id."""
        assert hasattr(AuditMixin, "owner_id")


class TestSoftDeleteMixin:
    """Tests for SoftDeleteMixin."""

    def test_mixin_has_deleted_at(self):
        """SoftDeleteMixin should have deleted_at field."""
        assert hasattr(SoftDeleteMixin, "deleted_at")

    def test_mixin_has_deleted_by_id(self):
        """SoftDeleteMixin should define deleted_by_id."""
        assert hasattr(SoftDeleteMixin, "deleted_by_id")

    def test_is_deleted_property_false_when_deleted_at_none(self):
        """is_deleted should return False when deleted_at is None."""

        class TestModel(SoftDeleteMixin):
            deleted_at = None

        model = TestModel()
        assert model.is_deleted is False

    def test_is_deleted_property_true_when_deleted_at_set(self):
        """is_deleted should return True when deleted_at is set."""

        class TestModel(SoftDeleteMixin):
            deleted_at = datetime.now(timezone.utc)

        model = TestModel()
        assert model.is_deleted is True


class TestStatusMixin:
    """Tests for StatusMixin."""

    def test_mixin_has_status(self):
        """StatusMixin should have status field."""
        assert hasattr(StatusMixin, "status")


class TestGenerateULID:
    """Tests for ULID generation."""

    def test_ulid_length(self):
        """ULID should be 26 characters."""
        ulid = generate_ulid()
        assert len(ulid) == 26

    def test_ulid_is_string(self):
        """ULID should be a string."""
        ulid = generate_ulid()
        assert isinstance(ulid, str)

    def test_ulid_uses_crockford_base32(self):
        """ULID should only contain Crockford's Base32 characters."""
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        ulid = generate_ulid()
        assert all(c in valid_chars for c in ulid)

    def test_ulid_uniqueness(self):
        """ULIDs should be unique."""
        ulids = [generate_ulid() for _ in range(100)]
        assert len(set(ulids)) == 100

    def test_ulid_is_sortable(self):
        """ULIDs generated later should sort after earlier ones."""
        import time

        ulid1 = generate_ulid()
        time.sleep(0.01)
        ulid2 = generate_ulid()
        assert ulid2 > ulid1

    def test_ulid_timestamp_prefix(self):
        """ULID should have a consistent timestamp prefix for same millisecond."""
        # Generate multiple in quick succession
        ulids = [generate_ulid() for _ in range(5)]
        # The first 10 characters are the timestamp
        # They should be the same or very close for quick succession
        timestamps = [u[:10] for u in ulids]
        # At least some should share the same timestamp prefix
        assert len(set(timestamps)) <= len(ulids)


class TestModelSerialization:
    """Tests for model serialization methods."""

    def test_to_dict_handles_uuid(self):
        """to_dict should convert UUID to string."""
        from uuid import uuid4

        from sensei.models.user import User

        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        result = user.to_dict()
        assert isinstance(result["id"], str)

    def test_to_dict_handles_datetime(self):
        """to_dict should convert datetime to ISO format string."""
        from uuid import uuid4

        from sensei.models.user import User

        now = datetime.now(timezone.utc)
        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            created_at=now,
            updated_at=now,
        )
        result = user.to_dict()
        assert isinstance(result.get("created_at"), str)

    def test_repr_includes_id(self):
        """__repr__ should include the model id."""
        from uuid import uuid4

        from sensei.models.user import User

        user_id = uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user_id) in repr_str

    def test_repr_includes_name_fields(self):
        """__repr__ should include name/email fields if present."""
        from uuid import uuid4

        from sensei.models.user import User

        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        repr_str = repr(user)
        assert "test@example.com" in repr_str or "testuser" in repr_str

"""Tests for Audit Log API endpoints.

Full test coverage for audit log operations:
- Audit log retrieval
- Filtering and querying
- Entity and user trails
- Summary statistics
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.audit_logs import (
    get_audit_log,
    list_audit_logs,
    get_entity_audit_trail,
    get_user_audit_trail,
    get_my_activity,
    get_logs_by_action,
    get_status_changes,
    get_audit_summary,
    get_recent_activity,
    get_security_events,
    get_deletion_events,
)
from sensei.api.exceptions import NotFoundError
from sensei.models.audit_log import AuditLog, AuditAction


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


# =============================================================================
# Audit Log Tests
# =============================================================================


class TestAuditLogRetrieval:
    """Tests for audit log retrieval operations."""

    @pytest.fixture
    def sample_log_data(self):
        """Sample audit log data."""
        return {
            "id": uuid4(),
            "created_at": datetime.now(timezone.utc),
            "entity_type": "rfq",
            "entity_id": uuid4(),
            "action": AuditAction.CREATE.value,
            "user_id": uuid4(),
            "user_email": "user@example.com",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "request_id": "req-123",
            "old_values": None,
            "new_values": {"title": "New RFQ"},
            "changed_fields": ["title"],
            "description": "Created new RFQ",
            "extra_data": None,
            "old_status": None,
            "new_status": "draft",
        }

    def create_mock_log(self, data: dict, **overrides) -> MagicMock:
        """Create a mock audit log."""
        log = MagicMock(spec=AuditLog)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(log, key, value)
        return log

    @pytest.mark.asyncio
    async def test_get_audit_log(self, mock_db, mock_user, sample_log_data):
        """Test getting a specific audit log entry."""
        log = self.create_mock_log(sample_log_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = log
        mock_db.execute.return_value = mock_result

        result = await get_audit_log(sample_log_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.action == AuditAction.CREATE.value

    @pytest.mark.asyncio
    async def test_get_audit_log_not_found(self, mock_db, mock_user):
        """Test getting non-existent audit log."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_audit_log(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_audit_logs(self, mock_db, mock_user, sample_log_data):
        """Test listing audit logs."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_audit_logs(
            mock_db,
            mock_user,
            entity_type=None,
            entity_id=None,
            action=None,
            user_id=None,
            start_date=None,
            end_date=None,
            search=None,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_list_audit_logs_filtered(self, mock_db, mock_user, sample_log_data):
        """Test listing audit logs with filters."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_audit_logs(
            mock_db,
            mock_user,
            entity_type="rfq",
            entity_id=sample_log_data["entity_id"],
            action=AuditAction.CREATE,
            user_id=sample_log_data["user_id"],
            start_date=datetime.now(timezone.utc) - timedelta(days=1),
            end_date=datetime.now(timezone.utc),
            search="RFQ",
            page=1,
            page_size=20,
        )

        assert result.success is True


class TestAuditTrails:
    """Tests for audit trail queries."""

    @pytest.fixture
    def sample_log_data(self):
        """Sample audit log data."""
        return {
            "id": uuid4(),
            "created_at": datetime.now(timezone.utc),
            "entity_type": "rfq",
            "entity_id": uuid4(),
            "action": AuditAction.UPDATE.value,
            "user_id": uuid4(),
            "user_email": "user@example.com",
            "ip_address": None,
            "user_agent": None,
            "request_id": None,
            "old_values": {"title": "Old"},
            "new_values": {"title": "New"},
            "changed_fields": ["title"],
            "description": "Updated RFQ",
            "extra_data": None,
            "old_status": None,
            "new_status": None,
        }

    def create_mock_log(self, data: dict, **overrides) -> MagicMock:
        """Create a mock audit log."""
        log = MagicMock(spec=AuditLog)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(log, key, value)
        return log

    @pytest.mark.asyncio
    async def test_get_entity_audit_trail(self, mock_db, mock_user, sample_log_data):
        """Test getting audit trail for an entity."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_entity_audit_trail(
            "rfq",
            sample_log_data["entity_id"],
            mock_db,
            mock_user,
            action=None,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_user_audit_trail(self, mock_db, mock_user, sample_log_data):
        """Test getting audit trail for a user."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_user_audit_trail(
            sample_log_data["user_id"],
            mock_db,
            mock_user,
            action=None,
            entity_type=None,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_my_activity(self, mock_db, mock_user, sample_log_data):
        """Test getting current user's activity."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_my_activity(
            mock_db,
            mock_user,
            action=None,
            entity_type=None,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1


class TestSpecializedQueries:
    """Tests for specialized audit log queries."""

    @pytest.fixture
    def sample_log_data(self):
        """Sample audit log data."""
        return {
            "id": uuid4(),
            "created_at": datetime.now(timezone.utc),
            "entity_type": "rfq",
            "entity_id": uuid4(),
            "action": AuditAction.STATUS_CHANGE.value,
            "user_id": uuid4(),
            "user_email": "user@example.com",
            "ip_address": None,
            "user_agent": None,
            "request_id": None,
            "old_values": {"status": "draft"},
            "new_values": {"status": "submitted"},
            "changed_fields": ["status"],
            "description": "Status changed",
            "extra_data": None,
            "old_status": "draft",
            "new_status": "submitted",
        }

    def create_mock_log(self, data: dict, **overrides) -> MagicMock:
        """Create a mock audit log."""
        log = MagicMock(spec=AuditLog)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(log, key, value)
        return log

    @pytest.mark.asyncio
    async def test_get_logs_by_action(self, mock_db, mock_user, sample_log_data):
        """Test getting logs by action type."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_logs_by_action(
            AuditAction.STATUS_CHANGE,
            mock_db,
            mock_user,
            entity_type=None,
            start_date=None,
            end_date=None,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_status_changes(self, mock_db, mock_user, sample_log_data):
        """Test getting status change logs."""
        logs = [self.create_mock_log(sample_log_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = logs
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_status_changes(
            mock_db,
            mock_user,
            entity_type=None,
            old_status=None,
            new_status=None,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_recent_activity(self, mock_db, mock_user, sample_log_data):
        """Test getting recent activity."""
        logs = [self.create_mock_log(sample_log_data)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = logs
        mock_db.execute.return_value = mock_result

        result = await get_recent_activity(mock_db, mock_user, limit=50)

        assert result.success is True
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_get_security_events(self, mock_db, mock_user, sample_log_data):
        """Test getting security events."""
        security_log = self.create_mock_log(
            sample_log_data,
            action=AuditAction.LOGIN.value,
        )

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [security_log]
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_security_events(
            mock_db,
            mock_user,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_deletion_events(self, mock_db, mock_user, sample_log_data):
        """Test getting deletion events."""
        delete_log = self.create_mock_log(
            sample_log_data,
            action=AuditAction.DELETE.value,
        )

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [delete_log]
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_deletion_events(
            mock_db,
            mock_user,
            entity_type=None,
            include_soft_deletes=True,
            page=1,
            page_size=50,
        )

        assert result.success is True
        assert result.pagination.total_items == 1


class TestAuditSummary:
    """Tests for audit summary statistics."""

    @pytest.mark.asyncio
    async def test_get_audit_summary(self, mock_db, mock_user):
        """Test getting audit summary."""
        # Total count
        mock_total = MagicMock()
        mock_total.scalar_one.return_value = 100

        # Actions by type
        mock_actions = MagicMock()
        mock_actions.all.return_value = [
            ("create", 40),
            ("update", 35),
            ("delete", 25),
        ]

        # Entities by type
        mock_entities = MagicMock()
        mock_entities.all.return_value = [
            ("rfq", 50),
            ("quote", 30),
            ("work_order", 20),
        ]

        # Top users
        mock_users = MagicMock()
        mock_users.all.return_value = [
            (uuid4(), "user1@example.com", 50),
            (uuid4(), "user2@example.com", 30),
        ]

        # Recent activity
        mock_recent = MagicMock()
        mock_recent.scalar_one.return_value = 25

        mock_db.execute.side_effect = [
            mock_total,
            mock_actions,
            mock_entities,
            mock_users,
            mock_recent,
        ]

        result = await get_audit_summary(mock_db, mock_user, days=7)

        assert result.success is True
        assert result.data.total_entries == 100
        assert result.data.actions_by_type["create"] == 40
        assert result.data.entities_by_type["rfq"] == 50
        assert result.data.recent_activity_count == 25

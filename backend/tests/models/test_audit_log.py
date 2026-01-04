"""
Tests for AuditLog model.

Tests:
- AuditLog model fields and defaults
- AuditAction enum
- Change tracking (old_values/new_values)
- User and entity references
- IP and user agent tracking
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.models.audit_log import (
    AuditAction,
    AuditLog,
)


class TestAuditLogModel:
    """Tests for the AuditLog model."""

    def test_audit_log_required_fields(self):
        """AuditLog should require action, entity_type, entity_id."""
        entity_id = uuid4()
        log = AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="rfq",
            entity_id=entity_id,
        )
        assert log.action == AuditAction.CREATE.value
        assert log.entity_type == "rfq"
        assert log.entity_id == entity_id

    def test_audit_log_user_id_tracking(self):
        """AuditLog should track user who performed action."""
        user_id = uuid4()
        log = AuditLog(
            action=AuditAction.UPDATE.value,
            entity_type="quote",
            entity_id=uuid4(),
            user_id=user_id,
        )
        assert log.user_id == user_id

    def test_audit_log_old_values(self):
        """AuditLog should store old_values as JSON."""
        log = AuditLog(
            action=AuditAction.UPDATE.value,
            entity_type="opportunity",
            entity_id=uuid4(),
            old_values={
                "stage": "qualification",
                "amount": 50000,
                "probability": 25,
            },
        )
        assert log.old_values == {
            "stage": "qualification",
            "amount": 50000,
            "probability": 25,
        }

    def test_audit_log_new_values(self):
        """AuditLog should store new_values as JSON."""
        log = AuditLog(
            action=AuditAction.UPDATE.value,
            entity_type="opportunity",
            entity_id=uuid4(),
            new_values={
                "stage": "proposal",
                "amount": 75000,
                "probability": 50,
            },
        )
        assert log.new_values == {
            "stage": "proposal",
            "amount": 75000,
            "probability": 50,
        }

    def test_audit_log_changed_fields(self):
        """AuditLog should store changed_fields list."""
        log = AuditLog(
            action=AuditAction.UPDATE.value,
            entity_type="rfq",
            entity_id=uuid4(),
            changed_fields=["status", "priority"],
        )
        assert log.changed_fields == ["status", "priority"]

    def test_audit_log_ip_address_tracking(self):
        """AuditLog should track IP address."""
        log = AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="user",
            entity_id=uuid4(),
            ip_address="192.168.1.100",
        )
        assert log.ip_address == "192.168.1.100"

    def test_audit_log_user_agent_tracking(self):
        """AuditLog should track user agent."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        log = AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="user",
            entity_id=uuid4(),
            user_agent=user_agent,
        )
        assert log.user_agent == user_agent

    def test_audit_log_request_id(self):
        """AuditLog should support request_id for request tracing."""
        request_id = str(uuid4())
        log = AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="rfq",
            entity_id=uuid4(),
            request_id=request_id,
        )
        assert log.request_id == request_id

    def test_audit_log_description_field(self):
        """AuditLog should support human-readable description."""
        log = AuditLog(
            action=AuditAction.UPDATE.value,
            entity_type="quote",
            entity_id=uuid4(),
            description="Quote status changed from draft to submitted",
        )
        assert log.description == "Quote status changed from draft to submitted"

    def test_audit_log_extra_data_field(self):
        """AuditLog should support additional extra_data."""
        log = AuditLog(
            action=AuditAction.UPDATE.value,
            entity_type="quote",
            entity_id=uuid4(),
            extra_data={
                "version_before": 1,
                "version_after": 2,
                "triggered_by": "bulk_update",
            },
        )
        assert log.extra_data == {
            "version_before": 1,
            "version_after": 2,
            "triggered_by": "bulk_update",
        }

    def test_audit_log_status_change_fields(self):
        """AuditLog should track old_status and new_status."""
        log = AuditLog(
            action=AuditAction.STATUS_CHANGE.value,
            entity_type="rfq",
            entity_id=uuid4(),
            old_status="draft",
            new_status="submitted",
        )
        assert log.old_status == "draft"
        assert log.new_status == "submitted"

    def test_audit_log_user_email(self):
        """AuditLog should store user_email separately for when user is deleted."""
        log = AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="rfq",
            entity_id=uuid4(),
            user_email="user@example.com",
        )
        assert log.user_email == "user@example.com"

    def test_audit_log_repr(self):
        """AuditLog __repr__ should be informative."""
        entity_id = uuid4()
        log = AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="rfq",
            entity_id=entity_id,
            user_email="test@example.com",
        )
        repr_str = repr(log)
        assert "AuditLog" in repr_str
        assert "rfq" in repr_str
        assert "create" in repr_str

    def test_audit_log_create_log_factory_method(self):
        """AuditLog.create_log should create log with computed changed_fields."""
        entity_id = uuid4()
        log = AuditLog.create_log(
            entity_type="rfq",
            entity_id=entity_id,
            action=AuditAction.UPDATE.value,
            old_values={"status": "draft", "title": "Test"},
            new_values={"status": "submitted", "title": "Test"},
        )
        assert log.entity_type == "rfq"
        assert log.entity_id == entity_id
        assert log.action == AuditAction.UPDATE.value
        # changed_fields should be computed automatically
        assert log.changed_fields == ["status"]

    def test_audit_log_create_log_computes_status_changes(self):
        """AuditLog.create_log should extract old_status and new_status."""
        log = AuditLog.create_log(
            entity_type="rfq",
            entity_id=uuid4(),
            action=AuditAction.UPDATE.value,
            old_values={"status": "draft"},
            new_values={"status": "submitted"},
        )
        assert log.old_status == "draft"
        assert log.new_status == "submitted"


class TestAuditActionEnum:
    """Tests for AuditAction enum."""

    def test_crud_actions_defined(self):
        """CRUD audit actions should be defined."""
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"

    def test_soft_delete_and_restore_actions(self):
        """Soft delete and restore actions should be defined."""
        assert AuditAction.SOFT_DELETE.value == "soft_delete"
        assert AuditAction.RESTORE.value == "restore"

    def test_view_action(self):
        """View action should be defined."""
        assert AuditAction.VIEW.value == "view"

    def test_auth_actions_defined(self):
        """Authentication actions should be defined."""
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.FAILED_LOGIN.value == "failed_login"
        assert AuditAction.PASSWORD_CHANGE.value == "password_change"

    def test_data_transfer_actions(self):
        """Export and import actions should be defined."""
        assert AuditAction.EXPORT.value == "export"
        assert AuditAction.IMPORT.value == "import"

    def test_workflow_actions(self):
        """Workflow actions should be defined."""
        assert AuditAction.STATUS_CHANGE.value == "status_change"
        assert AuditAction.APPROVAL.value == "approval"
        assert AuditAction.REJECTION.value == "rejection"

    def test_permission_change_action(self):
        """Permission change action should be defined."""
        assert AuditAction.PERMISSION_CHANGE.value == "permission_change"

    def test_audit_action_count(self):
        """There should be a comprehensive set of audit actions."""
        assert len(AuditAction) >= 14

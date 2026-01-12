"""Tests for Change Control Service."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sensei.services.quality.change_control import (
    ChangeControlService,
    ChangeRequest,
    ChangeApproval,
    ImpactAssessment,
    ChangeAuditEntry,
    ApprovalPolicy,
    ConfigSnapshot,
    ConfigValue,
    ChangeType,
    ChangeStatus,
    ChangeRisk,
    ChangeImpact,
    ApprovalDecision,
)


class TestEnums:
    """Tests for enum values."""

    def test_change_type_values(self) -> None:
        """Test ChangeType enum values."""
        assert ChangeType.THRESHOLD.value == "threshold"
        assert ChangeType.MARGIN_FLOOR.value == "margin_floor"
        assert ChangeType.PIPELINE_STAGE.value == "pipeline_stage"
        assert ChangeType.TEMPLATE.value == "template"

    def test_change_status_values(self) -> None:
        """Test ChangeStatus enum values."""
        assert ChangeStatus.DRAFT.value == "draft"
        assert ChangeStatus.PENDING_APPROVAL.value == "pending_approval"
        assert ChangeStatus.APPROVED.value == "approved"
        assert ChangeStatus.COMPLETED.value == "completed"

    def test_change_risk_values(self) -> None:
        """Test ChangeRisk enum values."""
        assert ChangeRisk.LOW.value == "low"
        assert ChangeRisk.MEDIUM.value == "medium"
        assert ChangeRisk.HIGH.value == "high"
        assert ChangeRisk.CRITICAL.value == "critical"

    def test_change_impact_values(self) -> None:
        """Test ChangeImpact enum values."""
        assert ChangeImpact.MINIMAL.value == "minimal"
        assert ChangeImpact.SIGNIFICANT.value == "significant"

    def test_approval_decision_values(self) -> None:
        """Test ApprovalDecision enum values."""
        assert ApprovalDecision.APPROVED.value == "approved"
        assert ApprovalDecision.REJECTED.value == "rejected"
        assert ApprovalDecision.NEEDS_INFO.value == "needs_info"


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_service_creates(self) -> None:
        """Test service initializes."""
        service = ChangeControlService()
        assert service is not None

    def test_default_policies_created(self) -> None:
        """Test default policies are created."""
        service = ChangeControlService()
        policies = service.get_policies()

        assert len(policies) >= 5

    def test_policies_for_each_type(self) -> None:
        """Test policies exist for main change types."""
        service = ChangeControlService()

        threshold_policies = service.get_policies(change_type=ChangeType.THRESHOLD)
        margin_policies = service.get_policies(change_type=ChangeType.MARGIN_FLOOR)

        assert len(threshold_policies) >= 1
        assert len(margin_policies) >= 1


class TestChangeRequestCreation:
    """Tests for change request creation."""

    def test_create_change_request(self) -> None:
        """Test creating a change request."""
        service = ChangeControlService()

        change = service.create_change_request(
            title="Update approval threshold",
            description="Increase approval threshold",
            change_type=ChangeType.THRESHOLD,
            config_key="quote.approval_threshold",
            new_value=10000,
            requester_id=uuid4(),
            requester_name="John Doe",
            justification="Business growth",
        )

        assert change is not None
        assert change.title == "Update approval threshold"
        assert change.status == ChangeStatus.DRAFT

    def test_create_change_captures_previous_value(self) -> None:
        """Test creating change captures existing value."""
        service = ChangeControlService()

        # Set existing value
        service.set_config_value("test.key", "old_value")

        change = service.create_change_request(
            title="Update test key",
            description="Change value",
            change_type=ChangeType.SYSTEM_CONFIG,
            config_key="test.key",
            new_value="new_value",
            requester_id=uuid4(),
        )

        assert change.previous_value is not None
        assert change.previous_value.value == "old_value"

    def test_create_change_with_tags(self) -> None:
        """Test creating change with tags."""
        service = ChangeControlService()

        change = service.create_change_request(
            title="Test",
            description="Test",
            change_type=ChangeType.TEMPLATE,
            config_key="template.1",
            new_value="new",
            requester_id=uuid4(),
            tags=["urgent", "production"],
        )

        assert "urgent" in change.tags

    def test_create_change_adds_audit_entry(self) -> None:
        """Test creating change adds audit entry."""
        service = ChangeControlService()

        change = service.create_change_request(
            title="Test",
            description="Test",
            change_type=ChangeType.THRESHOLD,
            config_key="test",
            new_value=100,
            requester_id=uuid4(),
        )

        assert len(change.audit_entries) >= 1
        assert change.audit_entries[0].action == "created"


class TestChangeRequestRetrieval:
    """Tests for change request retrieval."""

    def test_get_change_by_id(self) -> None:
        """Test getting change by ID."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "key", 100, uuid4()
        )

        found = service.get_change_request(change.id)
        assert found is not None
        assert found.title == "Test"

    def test_get_nonexistent_change(self) -> None:
        """Test getting nonexistent change."""
        service = ChangeControlService()

        result = service.get_change_request(uuid4())
        assert result is None

    def test_get_changes_by_status(self) -> None:
        """Test filtering changes by status."""
        service = ChangeControlService()

        service.create_change_request("C1", "D", ChangeType.THRESHOLD, "k", 1, uuid4())
        service.create_change_request("C2", "D", ChangeType.THRESHOLD, "k", 2, uuid4())

        drafts = service.get_change_requests(status=ChangeStatus.DRAFT)
        assert all(c.status == ChangeStatus.DRAFT for c in drafts)

    def test_get_changes_by_type(self) -> None:
        """Test filtering changes by type."""
        service = ChangeControlService()

        service.create_change_request("T1", "D", ChangeType.THRESHOLD, "k", 1, uuid4())
        service.create_change_request("T2", "D", ChangeType.TEMPLATE, "k", 2, uuid4())

        thresholds = service.get_change_requests(change_type=ChangeType.THRESHOLD)
        assert all(c.change_type == ChangeType.THRESHOLD for c in thresholds)


class TestChangeRequestUpdates:
    """Tests for change request updates."""

    def test_update_change_title(self) -> None:
        """Test updating change title."""
        service = ChangeControlService()
        actor_id = uuid4()

        change = service.create_change_request(
            "Old Title", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        updated = service.update_change_request(change.id, actor_id, title="New Title")
        assert updated is not None
        assert updated.title == "New Title"

    def test_update_non_draft_change(self) -> None:
        """Test cannot update non-draft change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.PENDING_APPROVAL

        result = service.update_change_request(change.id, uuid4(), title="New")
        assert result is None

    def test_cancel_change_request(self) -> None:
        """Test canceling a change request."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        cancelled = service.cancel_change_request(change.id, uuid4(), reason="No longer needed")
        assert cancelled is not None
        assert cancelled.status == ChangeStatus.CANCELLED


class TestWorkflow:
    """Tests for change workflow."""

    def test_submit_for_review(self) -> None:
        """Test submitting change for review."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        submitted = service.submit_for_review(change.id, uuid4())
        assert submitted is not None
        assert submitted.status == ChangeStatus.PENDING_REVIEW

    def test_submit_incomplete_change(self) -> None:
        """Test cannot submit incomplete change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        result = service.submit_for_review(change.id, uuid4())
        assert result is None

    def test_add_impact_assessment(self) -> None:
        """Test adding impact assessment."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        service.submit_for_review(change.id, uuid4())

        assessment = service.add_impact_assessment(
            change.id,
            assessor_id=uuid4(),
            risk_level=ChangeRisk.MEDIUM,
            impact_level=ChangeImpact.MODERATE,
            affected_areas=["Quotes", "Approvals"],
            rollback_plan="Restore previous value",
        )

        assert assessment is not None
        assert change.status == ChangeStatus.PENDING_APPROVAL

    def test_approve_change(self) -> None:
        """Test approving a change."""
        service = ChangeControlService()
        approver_id = uuid4()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        service.submit_for_review(change.id, uuid4())
        service.add_impact_assessment(
            change.id, uuid4(), ChangeRisk.LOW, ChangeImpact.MINIMAL, []
        )

        approval = service.approve_change(change.id, approver_id, "Approver", "Looks good")
        assert approval is not None
        assert approval.decision == ApprovalDecision.APPROVED

    def test_approve_without_impact_assessment(self) -> None:
        """Test cannot approve without required impact assessment."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.PENDING_APPROVAL

        result = service.approve_change(change.id, uuid4())
        assert result is None

    def test_reject_change(self) -> None:
        """Test rejecting a change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.PENDING_APPROVAL

        rejection = service.reject_change(change.id, uuid4(), reason="Not justified")
        assert rejection is not None
        assert rejection.decision == ApprovalDecision.REJECTED
        assert change.status == ChangeStatus.REJECTED

    def test_reject_requires_reason(self) -> None:
        """Test rejection requires reason."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.PENDING_APPROVAL

        result = service.reject_change(change.id, uuid4(), reason="")
        assert result is None

    def test_request_info(self) -> None:
        """Test requesting more info."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.PENDING_APPROVAL

        request = service.request_info(change.id, uuid4(), questions="Why this value?")
        assert request is not None
        assert request.decision == ApprovalDecision.NEEDS_INFO


class TestApprovalPolicy:
    """Tests for multi-approver policies."""

    def test_multiple_approvers_required(self) -> None:
        """Test change needs multiple approvers."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Margin Update", "Desc", ChangeType.MARGIN_FLOOR, "margin.floor", 0.25, uuid4()
        )
        service.submit_for_review(change.id, uuid4())
        service.add_impact_assessment(
            change.id, uuid4(), ChangeRisk.MEDIUM, ChangeImpact.MODERATE, []
        )

        # First approval
        service.approve_change(change.id, uuid4(), "Approver 1")
        assert change.status == ChangeStatus.PENDING_APPROVAL

        # Second approval
        service.approve_change(change.id, uuid4(), "Approver 2")
        assert change.status == ChangeStatus.APPROVED


class TestChangeApplication:
    """Tests for applying changes."""

    def test_apply_approved_change(self) -> None:
        """Test applying an approved change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "test.threshold", 500, uuid4()
        )
        change.status = ChangeStatus.APPROVED

        applied = service.apply_change(change.id, uuid4())
        assert applied is not None
        assert applied.status == ChangeStatus.COMPLETED
        assert applied.applied_at is not None

        # Verify config updated
        config = service.get_current_config()
        assert config["test.threshold"] == 500

    def test_apply_non_approved_change(self) -> None:
        """Test cannot apply non-approved change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        result = service.apply_change(change.id, uuid4())
        assert result is None

    def test_schedule_change(self) -> None:
        """Test scheduling an approved change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.APPROVED

        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        scheduled = service.schedule_change(change.id, scheduled_time, uuid4())

        assert scheduled is not None
        assert scheduled.status == ChangeStatus.SCHEDULED
        assert scheduled.scheduled_at == scheduled_time


class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_change(self) -> None:
        """Test rolling back a change."""
        service = ChangeControlService()

        # Set initial value
        service.set_config_value("test.key", "original")

        # Create and apply change
        change = service.create_change_request(
            "Update", "Desc", ChangeType.SYSTEM_CONFIG, "test.key", "new", uuid4()
        )
        change.status = ChangeStatus.APPROVED
        service.apply_change(change.id, uuid4())

        # Verify new value
        assert service.get_current_config()["test.key"] == "new"

        # Rollback
        rolled_back = service.rollback_change(change.id, uuid4(), reason="Issue found")
        assert rolled_back is not None
        assert rolled_back.status == ChangeStatus.ROLLED_BACK

        # Verify original value restored
        assert service.get_current_config()["test.key"] == "original"

    def test_rollback_non_completed_change(self) -> None:
        """Test cannot rollback non-completed change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        result = service.rollback_change(change.id, uuid4())
        assert result is None


class TestPolicies:
    """Tests for policy management."""

    def test_create_policy(self) -> None:
        """Test creating an approval policy."""
        service = ChangeControlService()

        policy = service.create_policy(
            name="Custom Policy",
            description="Test policy",
            change_type=ChangeType.INTEGRATION,
            required_approvers=3,
            approver_roles=["Admin", "GM", "IT"],
        )

        assert policy is not None
        assert policy.required_approvers == 3

    def test_get_policies_by_type(self) -> None:
        """Test getting policies by type."""
        service = ChangeControlService()

        threshold_policies = service.get_policies(change_type=ChangeType.THRESHOLD)
        assert all(p.change_type == ChangeType.THRESHOLD for p in threshold_policies)

    def test_get_active_policies(self) -> None:
        """Test getting active policies."""
        service = ChangeControlService()

        active = service.get_policies(active_only=True)
        assert all(p.is_active for p in active)

    def test_update_policy(self) -> None:
        """Test updating a policy."""
        service = ChangeControlService()

        policy = service.create_policy(
            "Test", "Desc", ChangeType.WORKFLOW_RULE, required_approvers=1
        )

        updated = service.update_policy(policy.id, required_approvers=2)
        assert updated is not None
        assert updated.required_approvers == 2

    def test_deactivate_policy(self) -> None:
        """Test deactivating a policy."""
        service = ChangeControlService()

        policy = service.create_policy("Test", "Desc", ChangeType.PERMISSION)

        updated = service.update_policy(policy.id, is_active=False)
        assert updated is not None
        assert updated.is_active is False


class TestSnapshots:
    """Tests for configuration snapshots."""

    def test_create_snapshot(self) -> None:
        """Test creating a configuration snapshot."""
        service = ChangeControlService()

        service.set_config_value("key1", "value1")
        service.set_config_value("key2", "value2")

        snapshot = service.create_snapshot(
            name="Before Release",
            description="Pre-release snapshot",
            created_by=uuid4(),
        )

        assert snapshot is not None
        assert "key1" in snapshot.configs

    def test_get_snapshots(self) -> None:
        """Test getting snapshots."""
        service = ChangeControlService()

        service.create_snapshot("S1", "D1", uuid4())
        service.create_snapshot("S2", "D2", uuid4())

        snapshots = service.get_snapshots()
        assert len(snapshots) >= 2

    def test_get_snapshots_by_environment(self) -> None:
        """Test filtering snapshots by environment."""
        service = ChangeControlService()

        service.create_snapshot("Prod", "D", uuid4(), environment="production")
        service.create_snapshot("Staging", "D", uuid4(), environment="staging")

        prod = service.get_snapshots(environment="production")
        assert all(s.environment == "production" for s in prod)

    def test_restore_snapshot(self) -> None:
        """Test restoring from a snapshot."""
        service = ChangeControlService()

        service.set_config_value("key1", "original1")
        service.set_config_value("key2", "original2")

        snapshot = service.create_snapshot("Backup", "D", uuid4())

        # Change values
        service.set_config_value("key1", "changed1")

        # Restore
        restored = service.restore_snapshot(snapshot.id, uuid4())
        assert restored is not None


class TestAudit:
    """Tests for audit trail."""

    def test_audit_trail_for_change(self) -> None:
        """Test getting audit trail for a change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )

        trail = service.get_audit_trail(change.id)
        assert len(trail) >= 1
        assert trail[0].action == "created"

    def test_audit_captures_all_actions(self) -> None:
        """Test audit captures all workflow actions."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "Desc", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        service.submit_for_review(change.id, uuid4())

        trail = service.get_audit_trail(change.id)
        actions = [e.action for e in trail]

        assert "created" in actions
        assert "submitted_for_review" in actions

    def test_get_all_audit_entries(self) -> None:
        """Test getting all audit entries."""
        service = ChangeControlService()

        service.create_change_request("C1", "D", ChangeType.THRESHOLD, "k", 1, uuid4())
        service.create_change_request("C2", "D", ChangeType.TEMPLATE, "k", 2, uuid4())

        entries = service.get_all_audit_entries()
        assert len(entries) >= 2

    def test_filter_audit_by_actor(self) -> None:
        """Test filtering audit entries by actor."""
        service = ChangeControlService()
        actor_id = uuid4()

        service.create_change_request("C1", "D", ChangeType.THRESHOLD, "k", 1, actor_id)
        service.create_change_request("C2", "D", ChangeType.THRESHOLD, "k", 2, uuid4())

        entries = service.get_all_audit_entries(actor_id=actor_id)
        assert all(e.actor_id == actor_id for e in entries)

    def test_filter_audit_by_action(self) -> None:
        """Test filtering audit entries by action."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "D", ChangeType.THRESHOLD, "k", 1, uuid4()
        )
        service.submit_for_review(change.id, uuid4())

        created = service.get_all_audit_entries(action="created")
        assert all(e.action == "created" for e in created)


class TestReporting:
    """Tests for reporting functionality."""

    def test_get_change_summary(self) -> None:
        """Test getting change summary."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test Change",
            "Description",
            ChangeType.THRESHOLD,
            "test.key",
            100,
            uuid4(),
            requester_name="John",
        )

        summary = service.get_change_summary(change.id)
        assert summary is not None
        assert summary["title"] == "Test Change"
        assert summary["status"] == "draft"

    def test_get_statistics(self) -> None:
        """Test getting statistics."""
        service = ChangeControlService()

        service.create_change_request("C1", "D", ChangeType.THRESHOLD, "k", 1, uuid4())
        service.create_change_request("C2", "D", ChangeType.TEMPLATE, "k", 2, uuid4())

        stats = service.get_statistics()
        assert stats["total_changes"] >= 2
        assert "by_status" in stats
        assert "by_type" in stats

    def test_get_pending_changes(self) -> None:
        """Test getting pending changes."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Pending", "D", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        service.submit_for_review(change.id, uuid4())

        pending = service.get_pending_changes()
        assert any(c.id == change.id for c in pending)

    def test_get_scheduled_changes(self) -> None:
        """Test getting scheduled changes."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Scheduled", "D", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.APPROVED
        service.schedule_change(change.id, datetime.now(timezone.utc) + timedelta(hours=1), uuid4())

        scheduled = service.get_scheduled_changes()
        assert any(c.id == change.id for c in scheduled)


class TestConfiguration:
    """Tests for configuration management."""

    def test_get_current_config(self) -> None:
        """Test getting current configuration."""
        service = ChangeControlService()

        service.set_config_value("key1", "value1")
        service.set_config_value("key2", 100)

        config = service.get_current_config()
        assert config["key1"] == "value1"
        assert config["key2"] == 100

    def test_set_config_value(self) -> None:
        """Test setting configuration value."""
        service = ChangeControlService()

        config = service.set_config_value(
            "test.key",
            "test_value",
            value_type="string",
            description="Test configuration",
        )

        assert config.value == "test_value"
        assert config.description == "Test configuration"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_approve_already_approved(self) -> None:
        """Test cannot double approve with single approver policy."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "D", ChangeType.TEMPLATE, "k", 100, uuid4()
        )
        change.status = ChangeStatus.APPROVED

        result = service.approve_change(change.id, uuid4())
        assert result is None

    def test_cancel_completed_change(self) -> None:
        """Test cannot cancel completed change."""
        service = ChangeControlService()

        change = service.create_change_request(
            "Test", "D", ChangeType.THRESHOLD, "k", 100, uuid4()
        )
        change.status = ChangeStatus.APPROVED
        service.apply_change(change.id, uuid4())

        result = service.cancel_change_request(change.id, uuid4())
        assert result is None

    def test_update_nonexistent_change(self) -> None:
        """Test updating nonexistent change."""
        service = ChangeControlService()

        result = service.update_change_request(uuid4(), uuid4(), title="New")
        assert result is None

    def test_rollback_without_previous_value(self) -> None:
        """Test rollback when no previous value exists."""
        service = ChangeControlService()

        change = service.create_change_request(
            "New Config", "D", ChangeType.SYSTEM_CONFIG, "new.key", "value", uuid4()
        )
        change.status = ChangeStatus.APPROVED
        service.apply_change(change.id, uuid4())

        # Rollback should remove the key
        rolled_back = service.rollback_change(change.id, uuid4())
        assert rolled_back is not None

        config = service.get_current_config()
        assert "new.key" not in config

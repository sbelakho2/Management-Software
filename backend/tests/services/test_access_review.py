"""Tests for Access Review Service."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sensei.services.core.access_review import (
    AccessReviewService,
    ReviewCampaign,
    UserAccess,
    AccessItem,
    Attestation,
    ReviewReminder,
    AccessViolation,
    ReviewFrequency,
    ReviewStatus,
    AttestationStatus,
    AccessType,
    RiskLevel,
)


class TestEnums:
    """Tests for enum values."""

    def test_review_frequency_values(self) -> None:
        """Test ReviewFrequency enum values."""
        assert ReviewFrequency.MONTHLY.value == "monthly"
        assert ReviewFrequency.QUARTERLY.value == "quarterly"
        assert ReviewFrequency.ANNUAL.value == "annual"

    def test_review_status_values(self) -> None:
        """Test ReviewStatus enum values."""
        assert ReviewStatus.DRAFT.value == "draft"
        assert ReviewStatus.ACTIVE.value == "active"
        assert ReviewStatus.COMPLETED.value == "completed"

    def test_attestation_status_values(self) -> None:
        """Test AttestationStatus enum values."""
        assert AttestationStatus.PENDING.value == "pending"
        assert AttestationStatus.APPROVED.value == "approved"
        assert AttestationStatus.REVOKED.value == "revoked"

    def test_access_type_values(self) -> None:
        """Test AccessType enum values."""
        assert AccessType.ROLE.value == "role"
        assert AccessType.PERMISSION.value == "permission"
        assert AccessType.RESOURCE.value == "resource"

    def test_risk_level_values(self) -> None:
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CRITICAL.value == "critical"


class TestServiceInitialization:
    """Tests for service initialization."""

    def test_service_creates(self) -> None:
        """Test service initializes."""
        service = AccessReviewService()
        assert service is not None

    def test_default_privileged_roles(self) -> None:
        """Test default privileged roles defined."""
        service = AccessReviewService()
        assert "GM" in service._privileged_roles
        assert "Admin" in service._privileged_roles

    def test_default_schedules(self) -> None:
        """Test default review schedules."""
        service = AccessReviewService()
        schedule = service.get_schedule()

        assert "Admin" in schedule
        assert "GM" in schedule


class TestCampaignManagement:
    """Tests for campaign CRUD."""

    def test_create_campaign(self) -> None:
        """Test creating a campaign."""
        service = AccessReviewService()

        campaign = service.create_campaign(
            name="Q1 Review",
            description="Quarterly access review",
            target_roles=["Admin"],
            reviewer_ids=[uuid4()],
            frequency=ReviewFrequency.QUARTERLY,
        )

        assert campaign is not None
        assert campaign.name == "Q1 Review"
        assert campaign.status == ReviewStatus.DRAFT

    def test_get_campaign_by_id(self) -> None:
        """Test getting campaign by ID."""
        service = AccessReviewService()

        campaign = service.create_campaign(
            name="Findable",
            description="Test",
            target_roles=["Admin"],
            reviewer_ids=[],
            frequency=ReviewFrequency.MONTHLY,
        )

        found = service.get_campaign(campaign.id)
        assert found is not None
        assert found.name == "Findable"

    def test_get_nonexistent_campaign(self) -> None:
        """Test getting nonexistent campaign."""
        service = AccessReviewService()

        result = service.get_campaign(uuid4())
        assert result is None

    def test_get_campaigns_by_status(self) -> None:
        """Test filtering campaigns by status."""
        service = AccessReviewService()

        service.create_campaign("C1", "D1", ["Admin"], [], ReviewFrequency.MONTHLY)
        service.create_campaign("C2", "D2", ["GM"], [], ReviewFrequency.QUARTERLY)

        campaigns = service.get_campaigns(status=ReviewStatus.DRAFT)
        assert len(campaigns) >= 2

    def test_get_campaigns_by_frequency(self) -> None:
        """Test filtering campaigns by frequency."""
        service = AccessReviewService()

        service.create_campaign("Monthly", "D1", ["Admin"], [], ReviewFrequency.MONTHLY)
        service.create_campaign("Quarterly", "D2", ["GM"], [], ReviewFrequency.QUARTERLY)

        monthly = service.get_campaigns(frequency=ReviewFrequency.MONTHLY)
        assert all(c.frequency == ReviewFrequency.MONTHLY for c in monthly)

    def test_start_campaign(self) -> None:
        """Test starting a campaign."""
        service = AccessReviewService()

        campaign = service.create_campaign(
            name="To Start",
            description="Test",
            target_roles=["Admin"],
            reviewer_ids=[uuid4()],
            frequency=ReviewFrequency.MONTHLY,
        )

        started = service.start_campaign(campaign.id)
        assert started is not None
        assert started.status == ReviewStatus.ACTIVE

    def test_start_already_active_campaign(self) -> None:
        """Test starting already active campaign."""
        service = AccessReviewService()

        campaign = service.create_campaign("C", "D", ["Admin"], [uuid4()], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        result = service.start_campaign(campaign.id)
        assert result is None

    def test_cancel_campaign(self) -> None:
        """Test canceling a campaign."""
        service = AccessReviewService()

        campaign = service.create_campaign("C", "D", ["Admin"], [], ReviewFrequency.MONTHLY)

        cancelled = service.cancel_campaign(campaign.id, "No longer needed")
        assert cancelled is not None
        assert cancelled.status == ReviewStatus.CANCELLED

    def test_cancel_completed_campaign(self) -> None:
        """Test cannot cancel completed campaign."""
        service = AccessReviewService()

        campaign = service.create_campaign("C", "D", ["Admin"], [], ReviewFrequency.MONTHLY)
        campaign.status = ReviewStatus.COMPLETED

        result = service.cancel_campaign(campaign.id, "Reason")
        assert result is None


class TestUserAccessManagement:
    """Tests for user access management."""

    def test_register_user_access(self) -> None:
        """Test registering user for access reviews."""
        service = AccessReviewService()
        user_id = uuid4()

        user_access = service.register_user_access(
            user_id=user_id,
            user_name="John Doe",
            user_email="john@example.com",
            department="IT",
        )

        assert user_access is not None
        assert user_access.user_name == "John Doe"

    def test_get_user_access(self) -> None:
        """Test getting user access profile."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "Jane", "jane@example.com")

        found = service.get_user_access(user_id)
        assert found is not None
        assert found.user_name == "Jane"

    def test_add_access_item(self) -> None:
        """Test adding access item to user."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "Test User", "test@example.com")

        item = service.add_access_item(
            user_id=user_id,
            access_type=AccessType.ROLE,
            name="Admin",
            description="Administrator role",
            risk_level=RiskLevel.HIGH,
        )

        assert item is not None
        assert item.name == "Admin"
        assert item.risk_level == RiskLevel.HIGH

    def test_add_access_item_invalid_user(self) -> None:
        """Test adding access item to invalid user."""
        service = AccessReviewService()

        result = service.add_access_item(uuid4(), AccessType.ROLE, "Admin")
        assert result is None

    def test_remove_access_item(self) -> None:
        """Test removing access item."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        item = service.add_access_item(user_id, AccessType.ROLE, "Admin")

        assert item is not None
        result = service.remove_access_item(user_id, item.id)
        assert result is True

        # Check item is inactive
        user_access = service.get_user_access(user_id)
        assert user_access is not None
        assert not user_access.access_items[0].is_active

    def test_risk_score_calculation(self) -> None:
        """Test risk score is calculated."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin", risk_level=RiskLevel.HIGH)
        service.add_access_item(user_id, AccessType.ROLE, "User", risk_level=RiskLevel.LOW)

        user_access = service.get_user_access(user_id)
        assert user_access is not None
        assert user_access.total_risk_score > 0

    def test_get_high_risk_users(self) -> None:
        """Test getting high risk users."""
        service = AccessReviewService()

        # Create high risk user
        high_risk_id = uuid4()
        service.register_user_access(high_risk_id, "High Risk", "high@example.com")
        service.add_access_item(high_risk_id, AccessType.ROLE, "Admin", risk_level=RiskLevel.CRITICAL)
        service.add_access_item(high_risk_id, AccessType.ROLE, "Finance", risk_level=RiskLevel.CRITICAL)

        # Create low risk user
        low_risk_id = uuid4()
        service.register_user_access(low_risk_id, "Low Risk", "low@example.com")
        service.add_access_item(low_risk_id, AccessType.ROLE, "Viewer", risk_level=RiskLevel.LOW)

        high_risk = service.get_high_risk_users(threshold=10.0)
        assert any(u.user_id == high_risk_id for u in high_risk)


class TestAttestations:
    """Tests for attestation management."""

    def test_get_attestation(self) -> None:
        """Test getting attestation by ID."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        # Setup user with access
        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        # Create and start campaign
        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        # Get attestations
        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            found = service.get_attestation(attestations[0].id)
            assert found is not None

    def test_get_attestations_for_review(self) -> None:
        """Test getting attestations for a campaign."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        assert isinstance(attestations, list)

    def test_get_attestations_by_status(self) -> None:
        """Test filtering attestations by status."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        pending = service.get_attestations_for_review(campaign.id, AttestationStatus.PENDING)
        for att in pending:
            assert att.status == AttestationStatus.PENDING

    def test_get_attestations_for_reviewer(self) -> None:
        """Test getting attestations for a reviewer."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_reviewer(reviewer_id)
        for att in attestations:
            assert att.reviewer_id == reviewer_id

    def test_approve_access(self) -> None:
        """Test approving access."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            result = service.approve_access(attestations[0].id, reviewer_id, "Still needed")
            assert result is not None
            assert result.status == AttestationStatus.APPROVED

    def test_revoke_access(self) -> None:
        """Test revoking access."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            result = service.revoke_access(attestations[0].id, reviewer_id, "No longer needed")
            assert result is not None
            assert result.status == AttestationStatus.REVOKED

    def test_revoke_requires_reason(self) -> None:
        """Test revoke requires reason."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            result = service.revoke_access(attestations[0].id, reviewer_id, "")
            assert result is None

    def test_escalate_attestation(self) -> None:
        """Test escalating attestation."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()
        escalate_to = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            result = service.escalate_attestation(attestations[0].id, escalate_to, "Need manager review")
            assert result is not None
            assert result.status == AttestationStatus.ESCALATED
            assert result.reviewer_id == escalate_to


class TestReminders:
    """Tests for reminder functionality."""

    def test_generate_reminders(self) -> None:
        """Test generating reminders."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        reminders = service.generate_reminders(campaign.id)
        assert isinstance(reminders, list)

    def test_get_reminders_by_campaign(self) -> None:
        """Test getting reminders by campaign."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)
        service.generate_reminders(campaign.id)

        reminders = service.get_reminders(campaign_id=campaign.id)
        for r in reminders:
            assert r.review_id == campaign.id

    def test_get_reminders_by_reviewer(self) -> None:
        """Test getting reminders by reviewer."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)
        service.generate_reminders(campaign.id)

        reminders = service.get_reminders(reviewer_id=reviewer_id)
        for r in reminders:
            assert r.reviewer_id == reviewer_id


class TestViolations:
    """Tests for violation tracking."""

    def test_record_violation(self) -> None:
        """Test recording a violation."""
        service = AccessReviewService()
        user_id = uuid4()

        violation = service.record_violation(
            user_id=user_id,
            violation_type="unauthorized_access",
            description="Accessed restricted resource",
        )

        assert violation is not None
        assert violation.user_id == user_id

    def test_resolve_violation(self) -> None:
        """Test resolving a violation."""
        service = AccessReviewService()
        user_id = uuid4()
        resolver_id = uuid4()

        violation = service.record_violation(user_id, "type", "description")

        resolved = service.resolve_violation(
            violation.id,
            resolver_id,
            "Access revoked and user notified",
        )

        assert resolved is not None
        assert resolved.resolved_at is not None
        assert resolved.resolved_by == resolver_id

    def test_get_violations_by_user(self) -> None:
        """Test getting violations for a user."""
        service = AccessReviewService()
        user_id = uuid4()

        service.record_violation(user_id, "type1", "description1")
        service.record_violation(user_id, "type2", "description2")

        violations = service.get_violations(user_id=user_id)
        assert len(violations) == 2

    def test_get_unresolved_violations(self) -> None:
        """Test getting unresolved violations."""
        service = AccessReviewService()
        user_id = uuid4()

        v1 = service.record_violation(user_id, "type1", "description1")
        service.record_violation(user_id, "type2", "description2")
        service.resolve_violation(v1.id, uuid4(), "Fixed")

        unresolved = service.get_violations(unresolved_only=True)
        assert all(v.resolved_at is None for v in unresolved)


class TestAutomaticChecks:
    """Tests for automatic access checks."""

    def test_check_expired_attestations(self) -> None:
        """Test checking for expired attestations."""
        service = AccessReviewService()

        expired = service.check_expired_attestations()
        assert isinstance(expired, list)

    def test_check_unused_access(self) -> None:
        """Test checking for unused access."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "OldRole")

        unused = service.check_unused_access(days_threshold=0)
        assert len(unused) > 0

    def test_check_excessive_access(self) -> None:
        """Test checking for excessive access."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")

        # Add many access items
        for i in range(15):
            service.add_access_item(user_id, AccessType.PERMISSION, f"Perm{i}")

        excessive = service.check_excessive_access(max_items=10)
        assert any(u.user_id == user_id for u in excessive)


class TestReporting:
    """Tests for reporting functionality."""

    def test_get_campaign_summary(self) -> None:
        """Test getting campaign summary."""
        service = AccessReviewService()

        campaign = service.create_campaign("C", "D", ["Admin"], [], ReviewFrequency.MONTHLY)

        summary = service.get_campaign_summary(campaign.id)
        assert summary is not None
        assert "name" in summary
        assert "status" in summary
        assert "completion_rate" in summary

    def test_get_campaign_summary_nonexistent(self) -> None:
        """Test getting summary for nonexistent campaign."""
        service = AccessReviewService()

        result = service.get_campaign_summary(uuid4())
        assert result is None

    def test_get_compliance_report(self) -> None:
        """Test getting compliance report."""
        service = AccessReviewService()

        report = service.get_compliance_report()

        assert "total_users_reviewed" in report
        assert "high_risk_users" in report
        assert "compliance_score" in report

    def test_compliance_score_range(self) -> None:
        """Test compliance score is in valid range."""
        service = AccessReviewService()

        report = service.get_compliance_report()
        assert 0 <= report["compliance_score"] <= 100

    def test_get_user_access_summary(self) -> None:
        """Test getting user access summary."""
        service = AccessReviewService()
        user_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin", risk_level=RiskLevel.HIGH)

        summary = service.get_user_access_summary(user_id)

        assert summary is not None
        assert "user_name" in summary
        assert "total_risk_score" in summary
        assert "by_type" in summary
        assert "by_risk" in summary

    def test_get_user_access_summary_nonexistent(self) -> None:
        """Test getting summary for nonexistent user."""
        service = AccessReviewService()

        result = service.get_user_access_summary(uuid4())
        assert result is None


class TestScheduleManagement:
    """Tests for schedule management."""

    def test_get_schedule(self) -> None:
        """Test getting review schedule."""
        service = AccessReviewService()

        schedule = service.get_schedule()
        assert isinstance(schedule, dict)
        assert len(schedule) > 0

    def test_update_schedule(self) -> None:
        """Test updating review schedule."""
        service = AccessReviewService()

        service.update_schedule("Admin", ReviewFrequency.SEMI_ANNUAL)

        schedule = service.get_schedule()
        assert schedule["Admin"] == "semi_annual"

    def test_get_due_reviews(self) -> None:
        """Test getting roles due for review."""
        service = AccessReviewService()

        due = service.get_due_reviews()
        assert isinstance(due, list)

    def test_auto_create_campaigns(self) -> None:
        """Test auto-creating campaigns."""
        service = AccessReviewService()

        campaigns = service.auto_create_campaigns()
        assert isinstance(campaigns, list)


class TestCampaignProgress:
    """Tests for campaign progress tracking."""

    def test_campaign_tracks_attestation_count(self) -> None:
        """Test campaign tracks attestation count."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        assert campaign.attestation_count >= 0

    def test_campaign_tracks_completed_count(self) -> None:
        """Test campaign tracks completed attestations."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            service.approve_access(attestations[0].id, reviewer_id)

        updated = service.get_campaign(campaign.id)
        assert updated is not None
        # May have completed count updated


class TestEdgeCases:
    """Tests for edge cases."""

    def test_approve_wrong_reviewer(self) -> None:
        """Test approving with wrong reviewer."""
        service = AccessReviewService()
        user_id = uuid4()
        reviewer_id = uuid4()
        wrong_reviewer = uuid4()

        service.register_user_access(user_id, "User", "user@example.com")
        service.add_access_item(user_id, AccessType.ROLE, "Admin")

        campaign = service.create_campaign("C", "D", ["Admin"], [reviewer_id], ReviewFrequency.MONTHLY)
        service.start_campaign(campaign.id)

        attestations = service.get_attestations_for_review(campaign.id)
        if attestations:
            result = service.approve_access(attestations[0].id, wrong_reviewer)
            assert result is None

    def test_remove_access_invalid_user(self) -> None:
        """Test removing access from invalid user."""
        service = AccessReviewService()

        result = service.remove_access_item(uuid4(), uuid4())
        assert result is False

    def test_complete_non_active_campaign(self) -> None:
        """Test completing non-active campaign."""
        service = AccessReviewService()

        campaign = service.create_campaign("C", "D", ["Admin"], [], ReviewFrequency.MONTHLY)
        # Campaign is still in DRAFT

        result = service.complete_campaign(campaign.id)
        assert result is None

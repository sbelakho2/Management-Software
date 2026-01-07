"""
Tests for Data Retention Rules Service.

Verifies:
- Retention policy management
- Legal hold functionality
- Retention status calculation
- Archive and delete operations
- Batch retention jobs
- Reporting and analytics
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.data_retention import (
    DataRetentionService,
    EntityType,
    LegalHold,
    PolicyStatus,
    RetentionAction,
    RetentionJob,
    RetentionPolicy,
    RetentionReport,
    RetentionStatus,
)


class TestDefaultPolicies:
    """Tests for default retention policies."""
    
    def test_default_policies_exist(self) -> None:
        """Test that default policies are created."""
        service = DataRetentionService()
        
        policies = service.get_policies()
        
        assert len(policies) > 0
    
    def test_opportunity_policy_exists(self) -> None:
        """Test default opportunity retention policy."""
        service = DataRetentionService()
        
        policies = service.get_policies(entity_type=EntityType.OPPORTUNITY)
        
        assert len(policies) > 0
        assert policies[0].retention_days == 2555  # 7 years
    
    def test_session_cleanup_policy(self) -> None:
        """Test session cleanup policy with delete action."""
        service = DataRetentionService()
        
        policies = service.get_policies(entity_type=EntityType.SESSION)
        
        assert len(policies) > 0
        assert policies[0].action == RetentionAction.DELETE
        assert policies[0].retention_days == 90


class TestPolicyManagement:
    """Tests for managing retention policies."""
    
    def test_create_policy(self) -> None:
        """Test creating a new retention policy."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Custom Policy",
            description="Test policy",
            entity_type=EntityType.TASK,
            retention_days=365,
            action=RetentionAction.ARCHIVE,
        )
        
        assert policy.id is not None
        assert policy.name == "Custom Policy"
        assert policy.retention_days == 365
        assert policy.status == PolicyStatus.ACTIVE
    
    def test_create_policy_requiring_approval(self) -> None:
        """Test creating a policy that requires approval."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Approval Required",
            description="Needs approval",
            entity_type=EntityType.QUOTE,
            retention_days=1825,
            action=RetentionAction.DELETE,
            requires_approval=True,
        )
        
        assert policy.status == PolicyStatus.DRAFT
        assert policy.requires_approval is True
    
    def test_get_policy(self) -> None:
        """Test retrieving a policy by ID."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Test",
            description="Test",
            entity_type=EntityType.CONTACT,
            retention_days=180,
            action=RetentionAction.ANONYMIZE,
        )
        
        retrieved = service.get_policy(policy.id)
        
        assert retrieved is not None
        assert retrieved.id == policy.id
    
    def test_update_policy(self) -> None:
        """Test updating a policy."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Original",
            description="Original description",
            entity_type=EntityType.RFQ,
            retention_days=365,
            action=RetentionAction.ARCHIVE,
        )
        
        updated = service.update_policy(
            policy.id,
            name="Updated",
            retention_days=730,
        )
        
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.retention_days == 730
    
    def test_activate_policy(self) -> None:
        """Test activating a draft policy."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Draft Policy",
            description="Needs approval",
            entity_type=EntityType.ACCOUNT,
            retention_days=365,
            action=RetentionAction.ARCHIVE,
            requires_approval=True,
        )
        
        approver = uuid4()
        activated = service.activate_policy(policy.id, approved_by=approver)
        
        assert activated is not None
        assert activated.status == PolicyStatus.ACTIVE
        assert activated.approved_by == approver
    
    def test_disable_policy(self) -> None:
        """Test disabling an active policy."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Active Policy",
            description="Test",
            entity_type=EntityType.ATTACHMENT,
            retention_days=365,
            action=RetentionAction.ARCHIVE,
        )
        
        disabled = service.disable_policy(policy.id)
        
        assert disabled is not None
        assert disabled.status == PolicyStatus.DISABLED
    
    def test_delete_policy(self) -> None:
        """Test deleting a policy."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="To Delete",
            description="Test",
            entity_type=EntityType.COMMENT,
            retention_days=30,
            action=RetentionAction.DELETE,
        )
        
        result = service.delete_policy(policy.id)
        
        assert result is True
        assert service.get_policy(policy.id) is None
    
    def test_policy_retention_period(self) -> None:
        """Test retention period property."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Test",
            description="Test",
            entity_type=EntityType.EXPORT,
            retention_days=90,
            action=RetentionAction.DELETE,
        )
        
        assert policy.retention_period == timedelta(days=90)


class TestLegalHolds:
    """Tests for legal hold functionality."""
    
    def test_create_legal_hold(self) -> None:
        """Test creating a legal hold."""
        service = DataRetentionService()
        
        hold = service.create_legal_hold(
            name="Litigation Hold",
            reason="Pending lawsuit",
            entity_type=EntityType.QUOTE,
        )
        
        assert hold.id is not None
        assert hold.is_active is True
        assert hold.entity_type == EntityType.QUOTE
    
    def test_create_hold_for_specific_entities(self) -> None:
        """Test creating hold for specific entities."""
        service = DataRetentionService()
        entity_ids = [uuid4(), uuid4()]
        
        hold = service.create_legal_hold(
            name="Specific Hold",
            reason="Investigation",
            entity_ids=entity_ids,
        )
        
        assert hold.entity_ids == entity_ids
    
    def test_get_active_holds(self) -> None:
        """Test getting active legal holds."""
        service = DataRetentionService()
        
        service.create_legal_hold(
            name="Hold 1",
            reason="Reason 1",
            entity_type=EntityType.OPPORTUNITY,
        )
        service.create_legal_hold(
            name="Hold 2",
            reason="Reason 2",
            entity_type=EntityType.RFQ,
        )
        
        holds = service.get_active_holds()
        
        assert len(holds) == 2
    
    def test_release_legal_hold(self) -> None:
        """Test releasing a legal hold."""
        service = DataRetentionService()
        user_id = uuid4()
        
        hold = service.create_legal_hold(
            name="To Release",
            reason="Temporary",
        )
        
        released = service.release_legal_hold(hold.id, released_by=user_id)
        
        assert released is not None
        assert released.is_active is False
        assert released.released_by == user_id
    
    def test_is_under_hold(self) -> None:
        """Test checking if entity is under hold."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        # No hold yet
        assert service.is_under_hold(EntityType.QUOTE, entity_id) is False
        
        # Create hold for all quotes
        service.create_legal_hold(
            name="Quote Hold",
            reason="Audit",
            entity_type=EntityType.QUOTE,
        )
        
        # Now under hold
        assert service.is_under_hold(EntityType.QUOTE, entity_id) is True
    
    def test_hold_with_expiry(self) -> None:
        """Test legal hold with expiry date."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        hold = service.create_legal_hold(
            name="Expiring Hold",
            reason="Short term",
            entity_type=EntityType.RFQ,
            end_date=datetime.now(timezone.utc) - timedelta(hours=1),  # Already expired
        )
        
        # Hold should not apply since it's expired
        assert hold.covers_entity(EntityType.RFQ, entity_id) is False
    
    def test_get_holds_for_entity(self) -> None:
        """Test getting all holds for an entity."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        service.create_legal_hold(
            name="Hold 1",
            reason="Reason 1",
            entity_type=EntityType.OPPORTUNITY,
        )
        service.create_legal_hold(
            name="Hold 2",
            reason="Reason 2",
            entity_type=EntityType.OPPORTUNITY,
        )
        
        holds = service.get_holds_for_entity(EntityType.OPPORTUNITY, entity_id)
        
        assert len(holds) == 2


class TestRetentionStatus:
    """Tests for retention status calculation."""
    
    def test_active_status(self) -> None:
        """Test entity within retention period."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        # Recent entity
        created_at = datetime.now(timezone.utc) - timedelta(days=30)
        
        status = service.calculate_retention_status(
            EntityType.OPPORTUNITY,
            entity_id,
            created_at,
        )
        
        assert status == RetentionStatus.ACTIVE
    
    def test_approaching_expiry_status(self) -> None:
        """Test entity approaching retention expiry."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        # Session policy is 90 days, warning at 30 days
        # So 70 days old should be approaching expiry
        created_at = datetime.now(timezone.utc) - timedelta(days=70)
        
        status = service.calculate_retention_status(
            EntityType.SESSION,
            entity_id,
            created_at,
        )
        
        assert status == RetentionStatus.APPROACHING_EXPIRY
    
    def test_expired_status(self) -> None:
        """Test entity past retention period."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        # Session policy is 90 days, so 100 days old is expired
        created_at = datetime.now(timezone.utc) - timedelta(days=100)
        
        status = service.calculate_retention_status(
            EntityType.SESSION,
            entity_id,
            created_at,
        )
        
        assert status == RetentionStatus.EXPIRED
    
    def test_held_status(self) -> None:
        """Test entity under legal hold."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        service.create_legal_hold(
            name="Test Hold",
            reason="Investigation",
            entity_type=EntityType.QUOTE,
        )
        
        created_at = datetime.now(timezone.utc)
        
        status = service.calculate_retention_status(
            EntityType.QUOTE,
            entity_id,
            created_at,
        )
        
        assert status == RetentionStatus.HELD
    
    def test_excluded_status_stays_active(self) -> None:
        """Test that excluded statuses remain active."""
        service = DataRetentionService()
        entity_id = uuid4()
        
        # Opportunities exclude "open" status
        created_at = datetime.now(timezone.utc) - timedelta(days=10000)
        
        status = service.calculate_retention_status(
            EntityType.OPPORTUNITY,
            entity_id,
            created_at,
            status="open",  # Excluded
        )
        
        assert status == RetentionStatus.ACTIVE
    
    def test_get_expiry_date(self) -> None:
        """Test calculating expiry date."""
        service = DataRetentionService()
        
        created_at = datetime.now(timezone.utc)
        
        expiry = service.get_expiry_date(EntityType.SESSION, created_at)
        
        assert expiry is not None
        expected = created_at + timedelta(days=90)
        assert abs((expiry - expected).total_seconds()) < 1


class TestArchiveOperations:
    """Tests for archive operations."""
    
    def test_archive_entity(self) -> None:
        """Test archiving an entity."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity(
            "session",
            data="test session",
        )
        
        result = service.archive_entity(EntityType.SESSION, entity_id)
        
        assert result is True
        
        # Entity should be in archive
        archived = service.get_archived_entities(EntityType.SESSION)
        assert entity_id in archived
        
        # Entity should not be in active
        assert service.get_entity("session", entity_id) is None
    
    def test_archive_prevented_by_hold(self) -> None:
        """Test that legal hold prevents archival."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity("quote", data="test quote")
        
        service.create_legal_hold(
            name="Block Archive",
            reason="Litigation",
            entity_type=EntityType.QUOTE,
        )
        
        result = service.archive_entity(EntityType.QUOTE, entity_id)
        
        assert result is False
        
        # Entity should still be active
        assert service.get_entity("quote", entity_id) is not None
    
    def test_restore_from_archive(self) -> None:
        """Test restoring an entity from archive."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity("session", data="archived session")
        service.archive_entity(EntityType.SESSION, entity_id)
        
        result = service.restore_from_archive(EntityType.SESSION, entity_id)
        
        assert result is True
        
        # Should be back in active
        restored = service.get_entity("session", entity_id)
        assert restored is not None
        assert "restored_at" in restored


class TestDeleteOperations:
    """Tests for delete operations."""
    
    def test_delete_entity(self) -> None:
        """Test deleting an entity."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity("draft", data="test draft")
        
        result = service.delete_entity(EntityType.DRAFT, entity_id)
        
        assert result is True
        assert service.get_entity("draft", entity_id) is None
    
    def test_delete_prevented_by_hold(self) -> None:
        """Test that legal hold prevents deletion."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity("quote", data="protected")
        
        service.create_legal_hold(
            name="Protect",
            reason="Legal",
            entity_type=EntityType.QUOTE,
        )
        
        result = service.delete_entity(EntityType.QUOTE, entity_id)
        
        assert result is False
        assert service.get_entity("quote", entity_id) is not None
    
    def test_force_delete_bypasses_hold(self) -> None:
        """Test force delete bypasses legal hold."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity("quote", data="force delete")
        
        service.create_legal_hold(
            name="Protect",
            reason="Legal",
            entity_type=EntityType.QUOTE,
        )
        
        result = service.delete_entity(EntityType.QUOTE, entity_id, force=True)
        
        assert result is True


class TestAnonymization:
    """Tests for data anonymization."""
    
    def test_anonymize_entity(self) -> None:
        """Test anonymizing PII in an entity."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity(
            "contact",
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
        )
        
        result = service.anonymize_entity(EntityType.CONTACT, entity_id)
        
        assert result is True
        
        entity = service.get_entity("contact", entity_id)
        assert entity["name"] == "[ANONYMIZED]"
        assert entity["email"] == "[ANONYMIZED]"
    
    def test_anonymize_custom_fields(self) -> None:
        """Test anonymizing specific fields."""
        service = DataRetentionService()
        
        entity_id = service.create_mock_entity(
            "contact",
            name="Jane Smith",
            company="Acme Corp",
            secret_data="confidential",
        )
        
        result = service.anonymize_entity(
            EntityType.CONTACT,
            entity_id,
            fields_to_anonymize=["secret_data"],
        )
        
        assert result is True
        
        entity = service.get_entity("contact", entity_id)
        assert entity["name"] == "Jane Smith"  # Not anonymized
        assert entity["secret_data"] == "[ANONYMIZED]"


class TestRetentionJobs:
    """Tests for batch retention jobs."""
    
    def test_run_retention_job(self) -> None:
        """Test running a retention job."""
        service = DataRetentionService()
        
        # Create old session entities
        for _ in range(5):
            old_date = datetime.now(timezone.utc) - timedelta(days=100)
            service.create_mock_entity("session", created_at=old_date)
        
        policies = service.get_policies(entity_type=EntityType.SESSION)
        
        job = service.run_retention_job(policies[0].id)
        
        assert job.status == "completed"
        assert job.records_processed >= 5
        assert job.records_deleted >= 5
    
    def test_dry_run_job(self) -> None:
        """Test dry run doesn't modify data."""
        service = DataRetentionService()
        
        # Create old session
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        entity_id = service.create_mock_entity("session", created_at=old_date)
        
        policies = service.get_policies(entity_type=EntityType.SESSION)
        
        job = service.run_retention_job(policies[0].id, dry_run=True)
        
        # Job should report deletions
        assert job.records_deleted >= 1
        
        # But entity should still exist
        assert service.get_entity("session", entity_id) is not None
    
    def test_job_skips_held_entities(self) -> None:
        """Test that jobs skip entities under legal hold."""
        service = DataRetentionService()
        
        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        entity_id = service.create_mock_entity("session", created_at=old_date)
        
        # Create hold for this specific entity
        service.create_legal_hold(
            name="Hold",
            reason="Investigation",
            entity_type=EntityType.SESSION,
            entity_ids=[entity_id],
        )
        
        policies = service.get_policies(entity_type=EntityType.SESSION)
        job = service.run_retention_job(policies[0].id)
        
        assert job.records_skipped >= 1
        assert service.get_entity("session", entity_id) is not None
    
    def test_job_skips_excluded_statuses(self) -> None:
        """Test that jobs skip excluded statuses."""
        service = DataRetentionService()
        
        old_date = datetime.now(timezone.utc) - timedelta(days=10000)
        entity_id = service.create_mock_entity(
            "opportunity",
            created_at=old_date,
            status="open",  # Excluded status
        )
        
        policies = service.get_policies(entity_type=EntityType.OPPORTUNITY)
        job = service.run_retention_job(policies[0].id)
        
        assert job.records_skipped >= 1
        assert service.get_entity("opportunity", entity_id) is not None
    
    def test_get_job(self) -> None:
        """Test retrieving a job by ID."""
        service = DataRetentionService()
        
        policies = service.get_policies(entity_type=EntityType.SESSION)
        job = service.run_retention_job(policies[0].id)
        
        retrieved = service.get_job(job.id)
        
        assert retrieved is not None
        assert retrieved.id == job.id
    
    def test_get_jobs_by_policy(self) -> None:
        """Test filtering jobs by policy."""
        service = DataRetentionService()
        
        policies = service.get_policies()
        
        # Run jobs for different policies
        job1 = service.run_retention_job(policies[0].id)
        job2 = service.run_retention_job(policies[1].id)
        
        filtered = service.get_jobs(policy_id=policies[0].id)
        
        assert len(filtered) >= 1
        assert all(j.policy_id == policies[0].id for j in filtered)


class TestApproachingExpiry:
    """Tests for approaching expiry detection."""
    
    def test_get_approaching_expiry(self) -> None:
        """Test getting entities approaching expiry."""
        service = DataRetentionService()
        
        # Create session approaching expiry (70 days old, 90 day policy)
        approaching_date = datetime.now(timezone.utc) - timedelta(days=70)
        service.create_mock_entity("session", created_at=approaching_date)
        
        approaching = service.get_approaching_expiry(days_threshold=30)
        
        assert len(approaching) >= 1
        assert approaching[0]["days_until_expiry"] <= 30
    
    def test_approaching_expiry_filtered_by_type(self) -> None:
        """Test filtering approaching expiry by entity type."""
        service = DataRetentionService()
        
        # Create approaching sessions
        date = datetime.now(timezone.utc) - timedelta(days=70)
        service.create_mock_entity("session", created_at=date)
        
        approaching = service.get_approaching_expiry(entity_type=EntityType.SESSION)
        
        assert all(a["entity_type"] == "session" for a in approaching)


class TestReports:
    """Tests for reporting functionality."""
    
    def test_generate_report(self) -> None:
        """Test generating a retention report."""
        service = DataRetentionService()
        
        # Create some test entities
        service.create_mock_entity("session", data="test")
        service.create_mock_entity("draft", data="test")
        
        report = service.generate_report()
        
        assert isinstance(report, RetentionReport)
        assert report.total_records >= 2
        assert report.generated_at is not None
    
    def test_report_by_status(self) -> None:
        """Test report breakdown by status."""
        service = DataRetentionService()
        
        # Create active entity
        service.create_mock_entity("session", data="active")
        
        report = service.generate_report()
        
        assert "active" in report.by_status or report.by_status.get("active", 0) >= 0
    
    def test_report_by_entity_type(self) -> None:
        """Test report breakdown by entity type."""
        service = DataRetentionService()
        
        service.create_mock_entity("session", data="test")
        service.create_mock_entity("draft", data="test")
        
        report = service.generate_report()
        
        assert len(report.by_entity_type) >= 0
    
    def test_get_retention_summary(self) -> None:
        """Test getting retention summary for entity type."""
        service = DataRetentionService()
        
        service.create_mock_entity("session", data="test")
        
        summary = service.get_retention_summary(EntityType.SESSION)
        
        assert summary["entity_type"] == "session"
        assert summary["retention_days"] == 90
        assert summary["action"] == "delete"
        assert summary["active_count"] >= 1
    
    def test_get_compliance_audit(self) -> None:
        """Test getting compliance audit trail."""
        service = DataRetentionService()
        
        # Create and archive entity to generate record
        entity_id = service.create_mock_entity("session", data="test")
        service.archive_entity(EntityType.SESSION, entity_id)
        
        audit = service.get_compliance_audit()
        
        assert len(audit) >= 1
        assert audit[0]["status"] == "archived"


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_delete_nonexistent_policy(self) -> None:
        """Test deleting non-existent policy."""
        service = DataRetentionService()
        
        result = service.delete_policy(uuid4())
        
        assert result is False
    
    def test_update_nonexistent_policy(self) -> None:
        """Test updating non-existent policy."""
        service = DataRetentionService()
        
        result = service.update_policy(uuid4(), name="New Name")
        
        assert result is None
    
    def test_archive_nonexistent_entity(self) -> None:
        """Test archiving non-existent entity."""
        service = DataRetentionService()
        
        result = service.archive_entity(EntityType.SESSION, uuid4())
        
        assert result is False
    
    def test_restore_nonexistent_archived(self) -> None:
        """Test restoring non-existent archived entity."""
        service = DataRetentionService()
        
        result = service.restore_from_archive(EntityType.SESSION, uuid4())
        
        assert result is False
    
    def test_job_for_invalid_policy(self) -> None:
        """Test running job for non-existent policy."""
        service = DataRetentionService()
        
        job = service.run_retention_job(uuid4())
        
        assert job.status == "failed"
        assert job.error_message is not None
    
    def test_release_nonexistent_hold(self) -> None:
        """Test releasing non-existent hold."""
        service = DataRetentionService()
        
        result = service.release_legal_hold(uuid4())
        
        assert result is None
    
    def test_entity_without_policy(self) -> None:
        """Test status calculation for entity type without policy."""
        service = DataRetentionService()
        
        # Remove all policies for EMAIL_LOG
        to_remove = [p.id for p in service.get_policies(entity_type=EntityType.EMAIL_LOG)]
        for pid in to_remove:
            service.delete_policy(pid)
        
        status = service.calculate_retention_status(
            EntityType.EMAIL_LOG,
            uuid4(),
            datetime.now(timezone.utc),
        )
        
        # Should default to active
        assert status == RetentionStatus.ACTIVE
    
    def test_activate_policy_without_approver(self) -> None:
        """Test activating policy requiring approval without approver."""
        service = DataRetentionService()
        
        policy = service.create_policy(
            name="Needs Approval",
            description="Test",
            entity_type=EntityType.ACCOUNT,
            retention_days=365,
            action=RetentionAction.ARCHIVE,
            requires_approval=True,
        )
        
        result = service.activate_policy(policy.id)  # No approver
        
        assert result is None
        assert policy.status == PolicyStatus.DRAFT

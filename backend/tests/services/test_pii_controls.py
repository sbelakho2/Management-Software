"""
Tests for PII Controls Service.

Verifies:
- Default PII field definitions
- Field definition CRUD
- Data subject management
- Consent management
- Data masking operations
- PII detection
- Access logging
- Deletion requests
- Reporting
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.pii_controls import (
    ConsentStatus,
    ConsentType,
    MaskingType,
    PIIAccessType,
    PIICategory,
    PIIControlsService,
    SensitivityLevel,
)


class TestDefaultFields:
    """Tests for default PII field definitions."""

    def test_default_fields_exist(self) -> None:
        """Test that default fields are created."""
        service = PIIControlsService()

        fields = service.get_field_definitions()

        assert len(fields) > 0

    def test_user_email_field(self) -> None:
        """Test user email field definition."""
        service = PIIControlsService()

        field = service.get_field_by_column("user", "email")

        assert field is not None
        assert field.category == PIICategory.EMAIL
        assert field.sensitivity == SensitivityLevel.HIGH

    def test_user_phone_field(self) -> None:
        """Test user phone field definition."""
        service = PIIControlsService()

        field = service.get_field_by_column("user", "phone")

        assert field is not None
        assert field.category == PIICategory.PHONE

    def test_ip_address_field(self) -> None:
        """Test IP address field definition."""
        service = PIIControlsService()

        field = service.get_field_by_column("audit_log", "ip_address")

        assert field is not None
        assert field.category == PIICategory.IP_ADDRESS


class TestFieldDefinitionCRUD:
    """Tests for field definition CRUD operations."""

    def test_create_field_definition(self) -> None:
        """Test creating a field definition."""
        service = PIIControlsService()

        field = service.create_field_definition(
            name="Custom SSN",
            table="employee",
            column="ssn",
            category=PIICategory.SSN,
            sensitivity=SensitivityLevel.CRITICAL,
            description="Employee SSN",
            detection_pattern=r"\d{3}-\d{2}-\d{4}",
            masking_type=MaskingType.FULL,
        )

        assert field.id is not None
        assert field.category == PIICategory.SSN
        assert field.sensitivity == SensitivityLevel.CRITICAL

    def test_get_field_definition(self) -> None:
        """Test getting a field by ID."""
        service = PIIControlsService()

        fields = service.get_field_definitions()
        field_id = fields[0].id

        retrieved = service.get_field_definition(field_id)

        assert retrieved is not None
        assert retrieved.id == field_id

    def test_get_field_by_column(self) -> None:
        """Test getting field by table and column."""
        service = PIIControlsService()

        field = service.get_field_by_column("user", "email")

        assert field is not None
        assert field.column == "email"

    def test_filter_by_category(self) -> None:
        """Test filtering fields by category."""
        service = PIIControlsService()

        email_fields = service.get_field_definitions(category=PIICategory.EMAIL)

        assert len(email_fields) > 0
        assert all(f.category == PIICategory.EMAIL for f in email_fields)

    def test_filter_by_sensitivity(self) -> None:
        """Test filtering fields by sensitivity."""
        service = PIIControlsService()

        high_fields = service.get_field_definitions(
            sensitivity=SensitivityLevel.HIGH
        )

        assert len(high_fields) > 0
        assert all(f.sensitivity == SensitivityLevel.HIGH for f in high_fields)

    def test_filter_by_table(self) -> None:
        """Test filtering fields by table."""
        service = PIIControlsService()

        user_fields = service.get_field_definitions(table="user")

        assert len(user_fields) > 0
        assert all(f.table == "user" for f in user_fields)

    def test_update_field_definition(self) -> None:
        """Test updating a field definition."""
        service = PIIControlsService()

        field = service.get_field_by_column("user", "email")

        updated = service.update_field_definition(
            field.id,
            sensitivity=SensitivityLevel.CRITICAL,
            retention_days=365,
        )

        assert updated is not None
        assert updated.sensitivity == SensitivityLevel.CRITICAL
        assert updated.retention_days == 365

    def test_delete_field_definition(self) -> None:
        """Test deleting a field definition."""
        service = PIIControlsService()

        field = service.create_field_definition(
            name="To Delete",
            table="temp",
            column="temp",
            category=PIICategory.CUSTOM,
            sensitivity=SensitivityLevel.LOW,
            description="Temp field",
        )

        result = service.delete_field_definition(field.id)

        assert result is True
        assert service.get_field_definition(field.id) is None


class TestDataSubjects:
    """Tests for data subject management."""

    def test_register_subject(self) -> None:
        """Test registering a data subject."""
        service = PIIControlsService()

        subject = service.register_subject(
            external_id="user-123",
            subject_type="user",
            email="test@example.com",
        )

        assert subject.id is not None
        assert subject.external_id == "user-123"

    def test_get_subject(self) -> None:
        """Test getting a subject by ID."""
        service = PIIControlsService()

        created = service.register_subject(
            external_id="user-456",
            subject_type="user",
        )

        retrieved = service.get_subject(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_subject_by_external_id(self) -> None:
        """Test getting subject by external ID."""
        service = PIIControlsService()

        service.register_subject(
            external_id="customer-789",
            subject_type="customer",
        )

        retrieved = service.get_subject_by_external_id("customer-789", "customer")

        assert retrieved is not None
        assert retrieved.external_id == "customer-789"

    def test_filter_subjects_by_type(self) -> None:
        """Test filtering subjects by type."""
        service = PIIControlsService()

        service.register_subject("u1", "user")
        service.register_subject("c1", "customer")

        users = service.get_subjects(subject_type="user")

        assert all(s.subject_type == "user" for s in users)


class TestConsentManagement:
    """Tests for consent management."""

    def test_grant_consent(self) -> None:
        """Test granting consent."""
        service = PIIControlsService()

        subject = service.register_subject("user-1", "user")

        consent = service.grant_consent(
            subject_id=subject.id,
            consent_type=ConsentType.COLLECTION,
            purpose="Data collection for service",
            source="signup_form",
            version="1.0",
        )

        assert consent is not None
        assert consent.status == ConsentStatus.GRANTED

    def test_grant_consent_with_expiry(self) -> None:
        """Test granting consent with expiry."""
        service = PIIControlsService()

        subject = service.register_subject("user-2", "user")

        consent = service.grant_consent(
            subject_id=subject.id,
            consent_type=ConsentType.MARKETING,
            purpose="Marketing emails",
            source="settings",
            version="1.0",
            expires_in_days=365,
        )

        assert consent is not None
        assert consent.expires_at is not None

    def test_withdraw_consent(self) -> None:
        """Test withdrawing consent."""
        service = PIIControlsService()

        subject = service.register_subject("user-3", "user")
        consent = service.grant_consent(
            subject.id,
            ConsentType.MARKETING,
            "Marketing",
            "settings",
            "1.0",
        )

        withdrawn = service.withdraw_consent(consent.id)

        assert withdrawn is not None
        assert withdrawn.status == ConsentStatus.WITHDRAWN
        assert withdrawn.withdrawn_at is not None

    def test_check_consent(self) -> None:
        """Test checking consent status."""
        service = PIIControlsService()

        subject = service.register_subject("user-4", "user")
        service.grant_consent(
            subject.id,
            ConsentType.COLLECTION,
            "Collection",
            "form",
            "1.0",
        )

        has_consent = service.check_consent(subject.id, ConsentType.COLLECTION)
        no_consent = service.check_consent(subject.id, ConsentType.MARKETING)

        assert has_consent is True
        assert no_consent is False

    def test_get_missing_consents(self) -> None:
        """Test getting missing consents."""
        service = PIIControlsService()

        subject = service.register_subject("user-5", "user")
        service.grant_consent(
            subject.id,
            ConsentType.COLLECTION,
            "Collection",
            "form",
            "1.0",
        )

        required = [ConsentType.COLLECTION, ConsentType.PROCESSING, ConsentType.SHARING]
        missing = service.get_missing_consents(subject.id, required)

        assert ConsentType.COLLECTION not in missing
        assert ConsentType.PROCESSING in missing
        assert ConsentType.SHARING in missing

    def test_filter_consents(self) -> None:
        """Test filtering consents."""
        service = PIIControlsService()

        subject = service.register_subject("user-6", "user")
        service.grant_consent(
            subject.id,
            ConsentType.COLLECTION,
            "Collection",
            "form",
            "1.0",
        )
        service.grant_consent(
            subject.id,
            ConsentType.MARKETING,
            "Marketing",
            "form",
            "1.0",
        )

        collection_consents = service.get_consents(
            subject_id=subject.id,
            consent_type=ConsentType.COLLECTION,
        )

        assert len(collection_consents) == 1


class TestDataMasking:
    """Tests for data masking operations."""

    def test_mask_full(self) -> None:
        """Test full masking."""
        service = PIIControlsService()

        result = service.mask_value("sensitive data", masking_type=MaskingType.FULL)

        assert result == "***REDACTED***"

    def test_mask_partial_email(self) -> None:
        """Test partial masking of email."""
        service = PIIControlsService()

        result = service.mask_value(
            "john.doe@example.com", masking_type=MaskingType.PARTIAL
        )

        assert "@" in result
        assert "*" in result
        assert result.endswith("@example.com")

    def test_mask_partial_phone(self) -> None:
        """Test partial masking of phone."""
        service = PIIControlsService()

        result = service.mask_value(
            "+1-555-123-4567", masking_type=MaskingType.PARTIAL
        )

        assert result.endswith("4567")
        assert "*" in result

    def test_mask_hash(self) -> None:
        """Test hash masking."""
        service = PIIControlsService()

        result = service.mask_value("secret", masking_type=MaskingType.HASH)

        assert len(result) == 16
        assert result != "secret"

    def test_mask_pseudonymize(self) -> None:
        """Test pseudonymization."""
        service = PIIControlsService()

        result = service.mask_value("John Doe", masking_type=MaskingType.PSEUDONYMIZE)

        assert result.startswith("PSEUDO_")

    def test_pseudonymize_consistent(self) -> None:
        """Test that pseudonymization is consistent."""
        service = PIIControlsService()

        result1 = service.mask_value("Jane Doe", masking_type=MaskingType.PSEUDONYMIZE)
        result2 = service.mask_value("Jane Doe", masking_type=MaskingType.PSEUDONYMIZE)

        assert result1 == result2

    def test_unmask_pseudonym(self) -> None:
        """Test unmasking a pseudonym."""
        service = PIIControlsService()

        pseudonym = service.mask_value(
            "Original Value", masking_type=MaskingType.PSEUDONYMIZE
        )
        original = service.unmask_pseudonym(pseudonym)

        assert original == "Original Value"

    def test_mask_tokenize(self) -> None:
        """Test tokenization."""
        service = PIIControlsService()

        result = service.mask_value("SSN-123", masking_type=MaskingType.TOKENIZE)

        assert result.startswith("TOK_")

    def test_unmask_token(self) -> None:
        """Test unmasking a token."""
        service = PIIControlsService()

        token = service.mask_value("Secret123", masking_type=MaskingType.TOKENIZE)
        original = service.unmask_token(token)

        assert original == "Secret123"

    def test_mask_truncate(self) -> None:
        """Test truncation masking."""
        service = PIIControlsService()

        result = service.mask_value(
            "Long Address Here", masking_type=MaskingType.TRUNCATE
        )

        assert result.startswith("Long")
        assert result.endswith("...")

    def test_mask_using_field_definition(self) -> None:
        """Test masking using field definition settings."""
        service = PIIControlsService()

        field = service.get_field_by_column("user", "email")
        result = service.mask_value("test@example.com", field_id=field.id)

        # Email field uses PARTIAL masking
        assert "@" in result
        assert "*" in result


class TestPIIDetection:
    """Tests for PII detection."""

    def test_detect_email(self) -> None:
        """Test detecting email addresses."""
        service = PIIControlsService()

        text = "Contact us at support@example.com for help"
        detections = service.detect_pii(text)

        email_detections = [d for d in detections if d["category"] == "email"]
        assert len(email_detections) > 0

    def test_detect_phone(self) -> None:
        """Test detecting phone numbers."""
        service = PIIControlsService()

        text = "Call us at +1-555-123-4567"
        detections = service.detect_pii(text)

        phone_detections = [d for d in detections if d["category"] == "phone"]
        assert len(phone_detections) > 0

    def test_detect_ip_address(self) -> None:
        """Test detecting IP addresses."""
        service = PIIControlsService()

        text = "Client IP: 192.168.1.100"
        detections = service.detect_pii(text)

        ip_detections = [d for d in detections if d["category"] == "ip_address"]
        assert len(ip_detections) > 0

    def test_scan_record(self) -> None:
        """Test scanning a record for PII."""
        service = PIIControlsService()

        record = {
            "id": 1,
            "email": "user@example.com",
            "phone": "+1-555-555-5555",
            "name": "Not defined as PII",
        }

        findings = service.scan_record(record, "user")

        assert len(findings) > 0
        assert any(f["column"] == "email" for f in findings)


class TestAccessLogging:
    """Tests for access logging."""

    def test_log_access(self) -> None:
        """Test logging PII access."""
        service = PIIControlsService()

        subject = service.register_subject("user-log", "user")
        field = service.get_field_by_column("user", "email")
        user_id = uuid4()

        log = service.log_access(
            subject_id=subject.id,
            user_id=user_id,
            field_id=field.id,
            access_type=PIIAccessType.VIEW,
            purpose="Customer support inquiry",
            ip_address="192.168.1.1",
        )

        assert log is not None
        assert log.access_type == PIIAccessType.VIEW

    def test_log_access_updates_subject(self) -> None:
        """Test that access updates subject last_accessed_at."""
        service = PIIControlsService()

        subject = service.register_subject("user-access", "user")
        field = service.get_field_by_column("user", "email")
        user_id = uuid4()

        service.log_access(
            subject_id=subject.id,
            user_id=user_id,
            field_id=field.id,
            access_type=PIIAccessType.VIEW,
            purpose="Test",
        )

        updated = service.get_subject(subject.id)
        assert updated.last_accessed_at is not None

    def test_get_access_logs(self) -> None:
        """Test getting access logs."""
        service = PIIControlsService()

        subject = service.register_subject("user-logs", "user")
        field = service.get_field_by_column("user", "email")
        user_id = uuid4()

        service.log_access(
            subject.id, user_id, field.id, PIIAccessType.VIEW, "View"
        )
        service.log_access(
            subject.id, user_id, field.id, PIIAccessType.EXPORT, "Export"
        )

        logs = service.get_access_logs(subject_id=subject.id)

        assert len(logs) == 2

    def test_filter_access_logs(self) -> None:
        """Test filtering access logs."""
        service = PIIControlsService()

        subject = service.register_subject("user-filter", "user")
        field = service.get_field_by_column("user", "email")
        user_id = uuid4()

        service.log_access(
            subject.id, user_id, field.id, PIIAccessType.VIEW, "View"
        )
        service.log_access(
            subject.id, user_id, field.id, PIIAccessType.EXPORT, "Export"
        )

        view_logs = service.get_access_logs(
            subject_id=subject.id, access_type=PIIAccessType.VIEW
        )

        assert len(view_logs) == 1
        assert view_logs[0].access_type == PIIAccessType.VIEW


class TestDeletionRequests:
    """Tests for deletion requests."""

    def test_request_deletion(self) -> None:
        """Test requesting deletion."""
        service = PIIControlsService()

        subject = service.register_subject("user-delete", "user")
        requester = uuid4()

        request = service.request_deletion(
            subject_id=subject.id,
            requested_by=requester,
            reason="GDPR deletion request",
        )

        assert request is not None
        assert request.status == "pending"
        assert len(request.affected_tables) > 0

    def test_request_updates_subject(self) -> None:
        """Test that deletion request updates subject."""
        service = PIIControlsService()

        subject = service.register_subject("user-del-update", "user")
        requester = uuid4()

        service.request_deletion(subject.id, requester, "Test")

        updated = service.get_subject(subject.id)
        assert updated.deletion_requested_at is not None

    def test_process_deletion_success(self) -> None:
        """Test processing deletion successfully."""
        service = PIIControlsService()

        subject = service.register_subject("user-del-success", "user")
        requester = uuid4()

        request = service.request_deletion(subject.id, requester, "Test")

        processed = service.process_deletion(request.id, deleted_records=10)

        assert processed is not None
        assert processed.status == "completed"
        assert processed.deleted_records == 10

    def test_process_deletion_failure(self) -> None:
        """Test processing deletion with errors."""
        service = PIIControlsService()

        subject = service.register_subject("user-del-fail", "user")
        requester = uuid4()

        request = service.request_deletion(subject.id, requester, "Test")

        processed = service.process_deletion(
            request.id, errors=["Foreign key constraint violation"]
        )

        assert processed is not None
        assert processed.status == "failed"
        assert len(processed.errors) > 0

    def test_get_pending_deletions(self) -> None:
        """Test getting pending deletions."""
        service = PIIControlsService()

        subject = service.register_subject("user-pending", "user")
        requester = uuid4()

        service.request_deletion(subject.id, requester, "Test")

        pending = service.get_pending_deletions()

        assert len(pending) > 0
        assert all(r.status == "pending" for r in pending)


class TestReporting:
    """Tests for PII reporting."""

    def test_generate_pii_report(self) -> None:
        """Test generating PII report."""
        service = PIIControlsService()

        subject = service.register_subject("user-report", "user")
        requester = uuid4()

        # Grant some consents
        service.grant_consent(
            subject.id, ConsentType.COLLECTION, "Test", "form", "1.0"
        )

        # Log some access
        field = service.get_field_by_column("user", "email")
        service.log_access(
            subject.id, requester, field.id, PIIAccessType.VIEW, "Test"
        )

        report = service.generate_pii_report(subject.id, requester)

        assert report is not None
        assert len(report.fields) > 0
        assert len(report.consents) > 0
        assert len(report.access_logs) > 0

    def test_get_retention_violations(self) -> None:
        """Test getting retention violations."""
        service = PIIControlsService()

        violations = service.get_retention_violations()

        # Should have fields with retention policies
        assert len(violations) > 0
        assert all("retention_days" in v for v in violations)

    def test_get_expired_consents(self) -> None:
        """Test getting expired consents."""
        service = PIIControlsService()

        subject = service.register_subject("user-expired", "user")

        # Create an expired consent (manual hack for testing)
        consent = service.grant_consent(
            subject.id, ConsentType.MARKETING, "Marketing", "form", "1.0"
        )
        consent.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        expired = service.get_expired_consents()

        assert len(expired) > 0


class TestSummary:
    """Tests for summary statistics."""

    def test_get_summary(self) -> None:
        """Test getting summary."""
        service = PIIControlsService()

        summary = service.get_summary()

        assert "total_fields" in summary
        assert "total_subjects" in summary
        assert "by_category" in summary
        assert "by_sensitivity" in summary
        assert summary["total_fields"] > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_get_nonexistent_field(self) -> None:
        """Test getting non-existent field."""
        service = PIIControlsService()

        result = service.get_field_definition(uuid4())

        assert result is None

    def test_get_nonexistent_subject(self) -> None:
        """Test getting non-existent subject."""
        service = PIIControlsService()

        result = service.get_subject(uuid4())

        assert result is None

    def test_grant_consent_invalid_subject(self) -> None:
        """Test granting consent for invalid subject."""
        service = PIIControlsService()

        result = service.grant_consent(
            uuid4(), ConsentType.COLLECTION, "Test", "form", "1.0"
        )

        assert result is None

    def test_withdraw_nonexistent_consent(self) -> None:
        """Test withdrawing non-existent consent."""
        service = PIIControlsService()

        result = service.withdraw_consent(uuid4())

        assert result is None

    def test_delete_nonexistent_field(self) -> None:
        """Test deleting non-existent field."""
        service = PIIControlsService()

        result = service.delete_field_definition(uuid4())

        assert result is False

    def test_update_nonexistent_field(self) -> None:
        """Test updating non-existent field."""
        service = PIIControlsService()

        result = service.update_field_definition(uuid4(), sensitivity=SensitivityLevel.HIGH)

        assert result is None

    def test_log_access_invalid_subject(self) -> None:
        """Test logging access for invalid subject."""
        service = PIIControlsService()

        field = service.get_field_by_column("user", "email")

        result = service.log_access(
            uuid4(), uuid4(), field.id, PIIAccessType.VIEW, "Test"
        )

        assert result is None

    def test_request_deletion_invalid_subject(self) -> None:
        """Test requesting deletion for invalid subject."""
        service = PIIControlsService()

        result = service.request_deletion(uuid4(), uuid4(), "Test")

        assert result is None

    def test_process_nonexistent_deletion(self) -> None:
        """Test processing non-existent deletion."""
        service = PIIControlsService()

        result = service.process_deletion(uuid4())

        assert result is None

    def test_generate_report_invalid_subject(self) -> None:
        """Test generating report for invalid subject."""
        service = PIIControlsService()

        result = service.generate_pii_report(uuid4(), uuid4())

        assert result is None

    def test_mask_empty_value(self) -> None:
        """Test masking empty value."""
        service = PIIControlsService()

        result = service.mask_value("", masking_type=MaskingType.FULL)

        assert result == ""

    def test_unmask_unknown_pseudonym(self) -> None:
        """Test unmasking unknown pseudonym."""
        service = PIIControlsService()

        result = service.unmask_pseudonym("PSEUDO_unknown")

        assert result is None

    def test_unmask_unknown_token(self) -> None:
        """Test unmasking unknown token."""
        service = PIIControlsService()

        result = service.unmask_token("TOK_unknown")

        assert result is None

"""
Tests for Supplier Portal Token Service.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sensei.services.supplier_portal_token import (
    TokenType,
    TokenStatus,
    AccessLevel,
    SubmissionStatus,
    FileType,
    TokenConfig,
    SupplierContact,
    PortalToken,
    UploadedFile,
    PortalSubmission,
    TokenAccessLog,
    NotificationRecord,
    TokenGenerationResult,
    ValidationResult,
    SubmissionResult,
    SupplierPortalTokenService,
    get_supplier_portal_token_service,
    reset_supplier_portal_token_service,
)


# ============================================================================
# Enum Tests
# ============================================================================


class TestTokenType:
    """Tests for TokenType enum."""
    
    def test_all_token_types(self):
        """Test all token type values exist."""
        assert TokenType.QUOTE_SUBMISSION.value == "quote_submission"
        assert TokenType.DOCUMENT_UPLOAD.value == "document_upload"
        assert TokenType.QUALIFICATION_RESPONSE.value == "qualification_response"
        assert TokenType.SAMPLE_TRACKING.value == "sample_tracking"
        assert TokenType.SURVEY.value == "survey"
        assert TokenType.PPAP_SUBMISSION.value == "ppap_submission"
        assert TokenType.CAPACITY_CONFIRMATION.value == "capacity_confirmation"
    
    def test_token_type_count(self):
        """Test number of token types."""
        assert len(TokenType) == 7


class TestTokenStatus:
    """Tests for TokenStatus enum."""
    
    def test_all_statuses(self):
        """Test all status values exist."""
        assert TokenStatus.ACTIVE.value == "active"
        assert TokenStatus.USED.value == "used"
        assert TokenStatus.EXPIRED.value == "expired"
        assert TokenStatus.REVOKED.value == "revoked"
        assert TokenStatus.SUSPENDED.value == "suspended"


class TestAccessLevel:
    """Tests for AccessLevel enum."""
    
    def test_all_access_levels(self):
        """Test all access level values exist."""
        assert AccessLevel.READ_ONLY.value == "read_only"
        assert AccessLevel.UPLOAD_ONLY.value == "upload_only"
        assert AccessLevel.READ_WRITE.value == "read_write"
        assert AccessLevel.FULL_ACCESS.value == "full_access"


class TestSubmissionStatus:
    """Tests for SubmissionStatus enum."""
    
    def test_all_statuses(self):
        """Test all submission status values exist."""
        assert SubmissionStatus.DRAFT.value == "draft"
        assert SubmissionStatus.SUBMITTED.value == "submitted"
        assert SubmissionStatus.UNDER_REVIEW.value == "under_review"
        assert SubmissionStatus.ACCEPTED.value == "accepted"
        assert SubmissionStatus.REJECTED.value == "rejected"
        assert SubmissionStatus.REVISION_REQUESTED.value == "revision_requested"


class TestFileType:
    """Tests for FileType enum."""
    
    def test_all_file_types(self):
        """Test all file type values exist."""
        assert FileType.PDF.value == "pdf"
        assert FileType.EXCEL.value == "excel"
        assert FileType.WORD.value == "word"
        assert FileType.IMAGE.value == "image"
        assert FileType.CAD.value == "cad"
        assert FileType.OTHER.value == "other"


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestTokenConfig:
    """Tests for TokenConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TokenConfig()
        
        assert config.default_expiry_days == 14
        assert config.max_uses is None
        assert config.max_file_size_mb == 50
        assert len(config.allowed_file_types) == 4
        assert FileType.PDF in config.allowed_file_types
        assert config.require_email_verification is False
        assert config.auto_notify_on_submission is True
        assert config.max_files_per_submission == 20
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TokenConfig(
            default_expiry_days=30,
            max_uses=5,
            max_file_size_mb=100,
            allowed_file_types=[FileType.PDF, FileType.CAD],
        )
        
        assert config.default_expiry_days == 30
        assert config.max_uses == 5
        assert config.max_file_size_mb == 100
        assert len(config.allowed_file_types) == 2


class TestSupplierContact:
    """Tests for SupplierContact dataclass."""
    
    def test_create_contact(self):
        """Test creating a supplier contact."""
        contact = SupplierContact(
            id=uuid4(),
            supplier_id=uuid4(),
            supplier_name="Acme Supplies",
            contact_name="John Doe",
            contact_email="john@acme.com",
            contact_phone="+1-555-1234",
            is_primary=True,
        )
        
        assert contact.contact_name == "John Doe"
        assert contact.contact_email == "john@acme.com"
        assert contact.is_primary is True


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_valid_result(self):
        """Test a valid validation result."""
        result = ValidationResult(
            is_valid=True,
            token=None,
            remaining_uses=5,
            time_until_expiry=timedelta(days=7),
        )
        
        assert result.is_valid is True
        assert result.remaining_uses == 5
    
    def test_invalid_result(self):
        """Test an invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            token=None,
            error_message="Token expired",
            error_code="TOKEN_EXPIRED",
        )
        
        assert result.is_valid is False
        assert result.error_code == "TOKEN_EXPIRED"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance for testing."""
    reset_supplier_portal_token_service()
    return SupplierPortalTokenService(base_url="https://portal.example.com")


@pytest.fixture
def supplier_id():
    """Create a supplier ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Create a user ID."""
    return uuid4()


@pytest.fixture
def rfq_id():
    """Create an RFQ ID."""
    return uuid4()


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestServiceInitialization:
    """Tests for service initialization."""
    
    def test_default_initialization(self, service):
        """Test service initializes with defaults."""
        assert service.base_url == "https://portal.example.com"
        assert service.default_config is not None
    
    def test_custom_config(self):
        """Test service with custom config."""
        config = TokenConfig(default_expiry_days=30)
        svc = SupplierPortalTokenService(default_config=config)
        assert svc.default_config.default_expiry_days == 30


# ============================================================================
# Token Generation Tests
# ============================================================================


class TestTokenGeneration:
    """Tests for token generation."""
    
    def test_generate_basic_token(self, service, supplier_id, user_id):
        """Test generating a basic token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test quote submission",
        )
        
        assert result.token is not None
        assert result.plain_token is not None
        assert len(result.plain_token) > 20
        assert result.access_url.startswith("https://portal.example.com")
        assert result.token.status == TokenStatus.ACTIVE
        assert result.token.supplier_id == supplier_id
        assert result.token.created_by == user_id
    
    def test_generate_token_with_rfq(self, service, supplier_id, user_id, rfq_id):
        """Test generating a token with RFQ reference."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Quote for RFQ",
            rfq_id=rfq_id,
        )
        
        assert result.token.rfq_id == rfq_id
    
    def test_generate_token_with_custom_expiry(self, service, supplier_id, user_id):
        """Test generating a token with custom expiry."""
        result = service.generate_token(
            token_type=TokenType.DOCUMENT_UPLOAD,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Document upload",
            expiry_days=7,
        )
        
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        # Allow 1 minute tolerance
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 60
    
    def test_generate_token_with_max_uses(self, service, supplier_id, user_id):
        """Test generating a token with max uses."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Single use token",
            max_uses=1,
        )
        
        assert result.token.max_uses == 1
    
    def test_generate_quote_submission_token(self, service, supplier_id, user_id, rfq_id):
        """Test convenience method for quote submission token."""
        result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        assert result.token.token_type == TokenType.QUOTE_SUBMISSION
        assert result.token.rfq_id == rfq_id
        assert result.token.access_level == AccessLevel.UPLOAD_ONLY
    
    def test_generate_document_upload_token(self, service, supplier_id, user_id):
        """Test convenience method for document upload token."""
        result = service.generate_document_upload_token(
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Upload certifications",
        )
        
        assert result.token.token_type == TokenType.DOCUMENT_UPLOAD
    
    def test_generate_ppap_submission_token(self, service, supplier_id, user_id):
        """Test convenience method for PPAP submission token."""
        quote_id = uuid4()
        result = service.generate_ppap_submission_token(
            supplier_id=supplier_id,
            quote_id=quote_id,
            created_by=user_id,
        )
        
        assert result.token.token_type == TokenType.PPAP_SUBMISSION
        assert result.token.quote_id == quote_id
        # PPAP tokens have special config
        assert result.token.config.max_file_size_mb == 100
    
    def test_token_hash_is_stored(self, service, supplier_id, user_id):
        """Test that token hash is stored, not plain token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        # Token value in storage should be partial
        assert "..." in result.token.token_value
        # Hash should be full
        assert len(result.token.token_hash) == 64  # SHA256 hex length


# ============================================================================
# Token Retrieval Tests
# ============================================================================


class TestTokenRetrieval:
    """Tests for token retrieval."""
    
    def test_get_token_by_id(self, service, supplier_id, user_id):
        """Test getting a token by ID."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        retrieved = service.get_token(result.token.id)
        assert retrieved is not None
        assert retrieved.id == result.token.id
    
    def test_get_nonexistent_token(self, service):
        """Test getting a nonexistent token."""
        result = service.get_token(uuid4())
        assert result is None
    
    def test_get_token_by_value(self, service, supplier_id, user_id):
        """Test getting a token by its value."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        retrieved = service.get_token_by_value(result.plain_token)
        assert retrieved is not None
        assert retrieved.id == result.token.id
    
    def test_get_token_by_invalid_value(self, service):
        """Test getting a token with invalid value."""
        result = service.get_token_by_value("invalid_token")
        assert result is None
    
    def test_list_tokens(self, service, supplier_id, user_id):
        """Test listing all tokens."""
        # Create multiple tokens
        for _ in range(3):
            service.generate_token(
                token_type=TokenType.QUOTE_SUBMISSION,
                supplier_id=supplier_id,
                created_by=user_id,
                purpose_description="Test",
            )
        
        tokens = service.list_tokens()
        assert len(tokens) >= 3
    
    def test_list_tokens_by_supplier(self, service, user_id):
        """Test listing tokens by supplier."""
        supplier1 = uuid4()
        supplier2 = uuid4()
        
        service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier1,
            created_by=user_id,
            purpose_description="Test 1",
        )
        
        service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier2,
            created_by=user_id,
            purpose_description="Test 2",
        )
        
        tokens = service.list_tokens(supplier_id=supplier1)
        assert len(tokens) == 1
        assert all(t.supplier_id == supplier1 for t in tokens)
    
    def test_list_tokens_by_type(self, service, supplier_id, user_id):
        """Test listing tokens by type."""
        service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Quote",
        )
        
        service.generate_token(
            token_type=TokenType.DOCUMENT_UPLOAD,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Document",
        )
        
        quote_tokens = service.list_tokens(token_type=TokenType.QUOTE_SUBMISSION)
        assert len(quote_tokens) >= 1
        assert all(t.token_type == TokenType.QUOTE_SUBMISSION for t in quote_tokens)
    
    def test_list_tokens_by_status(self, service, supplier_id, user_id):
        """Test listing tokens by status."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        # Revoke the token
        service.revoke_token(result.token.id, user_id, "Test revoke")
        
        active_tokens = service.list_tokens(status=TokenStatus.ACTIVE)
        revoked_tokens = service.list_tokens(status=TokenStatus.REVOKED)
        
        assert result.token.id not in [t.id for t in active_tokens]
        assert result.token.id in [t.id for t in revoked_tokens]
    
    def test_list_tokens_for_rfq(self, service, supplier_id, user_id, rfq_id):
        """Test listing tokens for an RFQ."""
        service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Quote",
            rfq_id=rfq_id,
        )
        
        tokens = service.list_tokens_for_rfq(rfq_id)
        assert len(tokens) >= 1
        assert all(t.rfq_id == rfq_id for t in tokens)
    
    def test_list_active_tokens_for_supplier(self, service, supplier_id, user_id):
        """Test listing active tokens for a supplier."""
        service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        tokens = service.list_active_tokens_for_supplier(supplier_id)
        assert len(tokens) >= 1
        assert all(t.status == TokenStatus.ACTIVE for t in tokens)


# ============================================================================
# Token Validation Tests
# ============================================================================


class TestTokenValidation:
    """Tests for token validation."""
    
    def test_validate_valid_token(self, service, supplier_id, user_id):
        """Test validating a valid token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        validation = service.validate_token(result.plain_token)
        
        assert validation.is_valid is True
        assert validation.token is not None
        assert validation.time_until_expiry is not None
    
    def test_validate_invalid_token(self, service):
        """Test validating an invalid token."""
        validation = service.validate_token("invalid_token")
        
        assert validation.is_valid is False
        assert validation.error_code == "INVALID_TOKEN"
    
    def test_validate_expired_token(self, service, supplier_id, user_id):
        """Test validating an expired token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
            expiry_days=0,  # Expires immediately
        )
        
        # Manually set expiry to past
        result.token.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        validation = service.validate_token(result.plain_token)
        
        assert validation.is_valid is False
        assert validation.error_code == "TOKEN_EXPIRED"
    
    def test_validate_revoked_token(self, service, supplier_id, user_id):
        """Test validating a revoked token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        service.revoke_token(result.token.id, user_id, "Test revoke")
        
        validation = service.validate_token(result.plain_token)
        
        assert validation.is_valid is False
        assert validation.error_code == "TOKEN_REVOKED"
    
    def test_validate_suspended_token(self, service, supplier_id, user_id):
        """Test validating a suspended token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        service.suspend_token(result.token.id)
        
        validation = service.validate_token(result.plain_token)
        
        assert validation.is_valid is False
        assert validation.error_code == "TOKEN_SUSPENDED"
    
    def test_validate_token_max_uses_exceeded(self, service, supplier_id, user_id):
        """Test validating a token that exceeded max uses."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
            max_uses=1,
        )
        
        # Simulate use
        result.token.use_count = 1
        
        validation = service.validate_token(result.plain_token)
        
        assert validation.is_valid is False
        assert validation.error_code == "MAX_USES_EXCEEDED"
    
    def test_validate_with_remaining_uses(self, service, supplier_id, user_id):
        """Test validation shows remaining uses."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
            max_uses=5,
        )
        
        result.token.use_count = 2
        
        validation = service.validate_token(result.plain_token)
        
        assert validation.is_valid is True
        assert validation.remaining_uses == 3
    
    def test_validate_with_ip_restriction(self, service, supplier_id, user_id):
        """Test validation with IP restriction."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
            ip_restrictions=["192.168.1.1", "10.0.0.1"],
        )
        
        # Valid IP
        validation = service.validate_token(result.plain_token, ip_address="192.168.1.1")
        assert validation.is_valid is True
        
        # Invalid IP
        validation = service.validate_token(result.plain_token, ip_address="8.8.8.8")
        assert validation.is_valid is False
        assert validation.error_code == "IP_RESTRICTED"


# ============================================================================
# Token Access Logging Tests
# ============================================================================


class TestAccessLogging:
    """Tests for access logging."""
    
    def test_record_access_granted(self, service, supplier_id, user_id):
        """Test recording a successful access."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        log = service.record_token_access(
            token_id=result.token.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            access_granted=True,
            email_provided="user@example.com",
        )
        
        assert log.access_granted is True
        assert log.ip_address == "192.168.1.1"
        
        # Token usage should be updated
        token = service.get_token(result.token.id)
        assert token.use_count == 1
        assert token.first_used_at is not None
    
    def test_record_access_denied(self, service, supplier_id, user_id):
        """Test recording a denied access."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        log = service.record_token_access(
            token_id=result.token.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            access_granted=False,
            denial_reason="IP restricted",
        )
        
        assert log.access_granted is False
        assert log.denial_reason == "IP restricted"
        
        # Token usage should NOT be updated for denied access
        token = service.get_token(result.token.id)
        assert token.use_count == 0
    
    def test_get_access_logs(self, service, supplier_id, user_id):
        """Test getting access logs."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        # Record multiple accesses
        for i in range(3):
            service.record_token_access(
                token_id=result.token.id,
                ip_address=f"192.168.1.{i}",
                user_agent="Mozilla/5.0",
                access_granted=True,
            )
        
        logs = service.get_access_logs(token_id=result.token.id)
        assert len(logs) == 3


# ============================================================================
# Token Management Tests
# ============================================================================


class TestTokenManagement:
    """Tests for token management."""
    
    def test_revoke_token(self, service, supplier_id, user_id):
        """Test revoking a token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        revoked = service.revoke_token(
            result.token.id,
            revoked_by=user_id,
            reason="No longer needed",
        )
        
        assert revoked.status == TokenStatus.REVOKED
        assert revoked.revoked_at is not None
        assert revoked.revoke_reason == "No longer needed"
    
    def test_revoke_nonexistent_token(self, service, user_id):
        """Test revoking a nonexistent token."""
        result = service.revoke_token(uuid4(), user_id, "Test")
        assert result is None
    
    def test_suspend_token(self, service, supplier_id, user_id):
        """Test suspending a token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        suspended = service.suspend_token(result.token.id)
        
        assert suspended.status == TokenStatus.SUSPENDED
    
    def test_reactivate_suspended_token(self, service, supplier_id, user_id):
        """Test reactivating a suspended token."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        service.suspend_token(result.token.id)
        
        reactivated = service.reactivate_token(result.token.id)
        
        assert reactivated.status == TokenStatus.ACTIVE
    
    def test_reactivate_with_extension(self, service, supplier_id, user_id):
        """Test reactivating with expiry extension."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        service.suspend_token(result.token.id)
        
        reactivated = service.reactivate_token(result.token.id, extend_expiry_days=30)
        
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        assert abs((reactivated.expires_at - expected_expiry).total_seconds()) < 60
    
    def test_extend_token_expiry(self, service, supplier_id, user_id):
        """Test extending a token's expiry."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
            expiry_days=7,
        )
        
        original_expiry = result.token.expires_at
        
        extended = service.extend_token_expiry(result.token.id, additional_days=7)
        
        expected = original_expiry + timedelta(days=7)
        assert abs((extended.expires_at - expected).total_seconds()) < 1
    
    def test_expire_old_tokens(self, service, supplier_id, user_id):
        """Test expiring old tokens."""
        result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        # Set expiry to past
        result.token.expires_at = datetime.utcnow() - timedelta(days=1)
        
        count = service.expire_old_tokens()
        
        assert count >= 1
        
        token = service.get_token(result.token.id)
        assert token.status == TokenStatus.EXPIRED


# ============================================================================
# Supplier Contact Tests
# ============================================================================


class TestSupplierContacts:
    """Tests for supplier contact management."""
    
    def test_register_contact(self, service, supplier_id):
        """Test registering a supplier contact."""
        contact = service.register_supplier_contact(
            supplier_id=supplier_id,
            supplier_name="Acme Supplies",
            contact_name="John Doe",
            contact_email="john@acme.com",
            contact_phone="+1-555-1234",
            is_primary=True,
        )
        
        assert contact.id is not None
        assert contact.contact_name == "John Doe"
        assert contact.is_primary is True
    
    def test_get_contact(self, service, supplier_id):
        """Test getting a contact by ID."""
        contact = service.register_supplier_contact(
            supplier_id=supplier_id,
            supplier_name="Acme",
            contact_name="John",
            contact_email="john@acme.com",
        )
        
        retrieved = service.get_supplier_contact(contact.id)
        assert retrieved is not None
        assert retrieved.id == contact.id
    
    def test_list_supplier_contacts(self, service, supplier_id):
        """Test listing contacts for a supplier."""
        for i in range(3):
            service.register_supplier_contact(
                supplier_id=supplier_id,
                supplier_name="Acme",
                contact_name=f"Contact {i}",
                contact_email=f"contact{i}@acme.com",
            )
        
        contacts = service.list_supplier_contacts(supplier_id)
        assert len(contacts) == 3


# ============================================================================
# Submission Tests
# ============================================================================


class TestSubmissions:
    """Tests for submission management."""
    
    def test_create_submission(self, service, supplier_id, user_id, rfq_id):
        """Test creating a submission."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John Doe",
            submitted_by_email="john@supplier.com",
            notes="Our quote for your review",
            quoted_price=100.50,
            quoted_currency="USD",
            quoted_lead_time_days=14,
        )
        
        assert result.success is True
        assert result.submission is not None
        assert result.submission.status == SubmissionStatus.SUBMITTED
        assert result.submission.quoted_price == 100.50
    
    def test_create_submission_invalid_token(self, service):
        """Test creating submission with invalid token."""
        result = service.create_submission(
            token_id=uuid4(),
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_create_submission_updates_token_usage(self, service, supplier_id, user_id, rfq_id):
        """Test that creating a submission updates token usage."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        initial_count = token_result.token.use_count
        
        service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        token = service.get_token(token_result.token.id)
        assert token.use_count == initial_count + 1
    
    def test_add_file_to_submission(self, service, supplier_id, user_id, rfq_id):
        """Test adding a file to a submission."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        sub_result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        uploaded_file = service.add_file_to_submission(
            submission_id=sub_result.submission.id,
            file_name="quote_001.pdf",
            original_name="Quote for RFQ-2024.pdf",
            file_type=FileType.PDF,
            mime_type="application/pdf",
            file_size_bytes=1024000,
            file_hash="abc123def456",
            storage_path="/uploads/quote_001.pdf",
            uploaded_by_email="john@example.com",
        )
        
        assert uploaded_file is not None
        assert uploaded_file.file_name == "quote_001.pdf"
        
        # Verify file is in submission
        submission = service.get_submission(sub_result.submission.id)
        assert len(submission.files) == 1
    
    def test_get_submission(self, service, supplier_id, user_id, rfq_id):
        """Test getting a submission by ID."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        sub_result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        retrieved = service.get_submission(sub_result.submission.id)
        assert retrieved is not None
        assert retrieved.id == sub_result.submission.id
    
    def test_list_submissions(self, service, supplier_id, user_id, rfq_id):
        """Test listing submissions."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        for i in range(3):
            service.create_submission(
                token_id=token_result.token.id,
                submitted_by_name=f"User {i}",
                submitted_by_email=f"user{i}@example.com",
            )
        
        submissions = service.list_submissions()
        assert len(submissions) >= 3
    
    def test_list_submissions_for_rfq(self, service, supplier_id, user_id, rfq_id):
        """Test listing submissions for an RFQ."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        submissions = service.list_submissions_for_rfq(rfq_id)
        assert len(submissions) >= 1
        assert all(s.rfq_id == rfq_id for s in submissions)


# ============================================================================
# Submission Review Tests
# ============================================================================


class TestSubmissionReview:
    """Tests for submission review."""
    
    def test_accept_submission(self, service, supplier_id, user_id, rfq_id):
        """Test accepting a submission."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        sub_result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        reviewer_id = uuid4()
        accepted = service.accept_submission(
            sub_result.submission.id,
            reviewed_by=reviewer_id,
            review_notes="Looks good!",
        )
        
        assert accepted.status == SubmissionStatus.ACCEPTED
        assert accepted.reviewed_at is not None
        assert accepted.reviewed_by == reviewer_id
    
    def test_reject_submission(self, service, supplier_id, user_id, rfq_id):
        """Test rejecting a submission."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        sub_result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        rejected = service.reject_submission(
            sub_result.submission.id,
            reviewed_by=uuid4(),
            review_notes="Price too high",
        )
        
        assert rejected.status == SubmissionStatus.REJECTED
        assert rejected.review_notes == "Price too high"
    
    def test_request_revision(self, service, supplier_id, user_id, rfq_id):
        """Test requesting a revision."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        sub_result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        revised = service.request_revision(
            sub_result.submission.id,
            reviewed_by=uuid4(),
            review_notes="Please include lead time",
        )
        
        assert revised.status == SubmissionStatus.REVISION_REQUESTED
    
    def test_mark_under_review(self, service, supplier_id, user_id, rfq_id):
        """Test marking submission as under review."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        sub_result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        under_review = service.mark_under_review(
            sub_result.submission.id,
            reviewed_by=uuid4(),
        )
        
        assert under_review.status == SubmissionStatus.UNDER_REVIEW


# ============================================================================
# Notification Tests
# ============================================================================


class TestNotifications:
    """Tests for notification recording."""
    
    def test_record_notification(self, service, supplier_id, user_id):
        """Test recording a notification."""
        token_result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        record = service.record_notification(
            token_id=token_result.token.id,
            notification_type="token_created",
            recipient_email="supplier@example.com",
            subject="Your portal access link",
        )
        
        assert record.id is not None
        assert record.notification_type == "token_created"
        assert record.success is True
    
    def test_get_notifications(self, service, supplier_id, user_id):
        """Test getting notifications."""
        token_result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Test",
        )
        
        for i in range(3):
            service.record_notification(
                token_id=token_result.token.id,
                notification_type=f"type_{i}",
                recipient_email="supplier@example.com",
                subject=f"Notification {i}",
            )
        
        notifications = service.get_notifications(token_id=token_result.token.id)
        assert len(notifications) == 3


# ============================================================================
# Analytics Tests
# ============================================================================


class TestAnalytics:
    """Tests for analytics functions."""
    
    def test_get_token_statistics(self, service, supplier_id, user_id, rfq_id):
        """Test getting token statistics."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        # Create a submission
        service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        stats = service.get_token_statistics(token_result.token.id)
        
        assert stats["token_id"] == str(token_result.token.id)
        assert stats["status"] == "active"
        assert stats["total_submissions"] >= 1
    
    def test_get_nonexistent_token_statistics(self, service):
        """Test getting statistics for nonexistent token."""
        stats = service.get_token_statistics(uuid4())
        assert stats == {}
    
    def test_get_supplier_statistics(self, service, supplier_id, user_id, rfq_id):
        """Test getting supplier statistics."""
        # Create tokens
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        # Create submission
        service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        stats = service.get_supplier_statistics(supplier_id)
        
        assert stats["supplier_id"] == str(supplier_id)
        assert stats["total_tokens"] >= 1
        assert stats["total_submissions"] >= 1


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_singleton_instance(self):
        """Test getting singleton instance."""
        reset_supplier_portal_token_service()
        
        svc1 = get_supplier_portal_token_service()
        svc2 = get_supplier_portal_token_service()
        
        assert svc1 is svc2
    
    def test_reset_singleton(self):
        """Test resetting singleton instance."""
        svc1 = get_supplier_portal_token_service()
        
        reset_supplier_portal_token_service()
        
        svc2 = get_supplier_portal_token_service()
        
        assert svc1 is not svc2


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_single_use_token(self, service, supplier_id, user_id, rfq_id):
        """Test that single-use token is marked used after submission."""
        token_result = service.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=user_id,
            purpose_description="Single use",
            rfq_id=rfq_id,
            max_uses=1,
        )
        
        service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        token = service.get_token(token_result.token.id)
        assert token.status == TokenStatus.USED
    
    def test_submission_on_inactive_token(self, service, supplier_id, user_id, rfq_id):
        """Test creating submission on inactive token fails."""
        token_result = service.generate_quote_submission_token(
            rfq_id=rfq_id,
            supplier_id=supplier_id,
            created_by=user_id,
        )
        
        # Revoke the token
        service.revoke_token(token_result.token.id, user_id, "Test")
        
        result = service.create_submission(
            token_id=token_result.token.id,
            submitted_by_name="John",
            submitted_by_email="john@example.com",
        )
        
        assert result.success is False
        assert "not active" in result.error_message.lower()
    
    def test_token_secure_generation(self, service, supplier_id, user_id):
        """Test that tokens are cryptographically secure."""
        tokens = []
        for _ in range(10):
            result = service.generate_token(
                token_type=TokenType.QUOTE_SUBMISSION,
                supplier_id=supplier_id,
                created_by=user_id,
                purpose_description="Test",
            )
            tokens.append(result.plain_token)
        
        # All tokens should be unique
        assert len(set(tokens)) == 10
        
        # Tokens should be long enough
        assert all(len(t) > 20 for t in tokens)
    
    def test_add_file_to_nonexistent_submission(self, service):
        """Test adding file to nonexistent submission."""
        result = service.add_file_to_submission(
            submission_id=uuid4(),
            file_name="test.pdf",
            original_name="Test.pdf",
            file_type=FileType.PDF,
            mime_type="application/pdf",
            file_size_bytes=1024,
            file_hash="abc123",
            storage_path="/uploads/test.pdf",
            uploaded_by_email="test@example.com",
        )
        
        assert result is None
    
    def test_review_nonexistent_submission(self, service, user_id):
        """Test reviewing a nonexistent submission."""
        result = service.accept_submission(uuid4(), user_id)
        assert result is None
        
        result = service.reject_submission(uuid4(), user_id, "Test")
        assert result is None

"""
Tests for CSV Import Service.

Comprehensive tests covering:
- CSV parsing and field mapping
- Validation logic
- Duplicate detection
- Import execution
- Audit logging
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sensei.services.utils.csv_import import (
    CSVImportService,
    ImportConfig,
    ImportEntityType,
    ImportStatus,
    RowStatus,
    DuplicateAction,
    FieldMapping,
    FieldMappingType,
    ValidationError,
    ImportRowResult,
    ImportJobResult,
    DuplicateCandidate,
    ACCOUNT_FIELD_MAPPINGS,
    CONTACT_FIELD_MAPPINGS,
    OPPORTUNITY_FIELD_MAPPINGS,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service() -> CSVImportService:
    """Create a fresh CSV import service."""
    svc = CSVImportService()
    svc.clear()
    return svc


@pytest.fixture
def account_csv() -> str:
    """Sample CSV for account import."""
    return """name,account_type,status,email,phone,city,country
Acme Corporation,customer,active,contact@acme.com,+212 5 1234 5678,Casablanca,Morocco
Beta Industries,prospect,lead,info@beta.com,+212 5 9876 5432,Rabat,Morocco
Gamma Solutions,supplier,active,sales@gamma.com,+212 5 5555 1234,Tangier,Morocco
"""


@pytest.fixture
def contact_csv() -> str:
    """Sample CSV for contact import."""
    return """first_name,last_name,email,phone_mobile,job_title,department
John,Doe,john.doe@acme.com,+212 6 1111 2222,CEO,Executive
Jane,Smith,jane.smith@acme.com,+212 6 3333 4444,CTO,Engineering
Bob,Johnson,bob.j@beta.com,+212 6 5555 6666,Sales Manager,Sales
"""


@pytest.fixture
def opportunity_csv() -> str:
    """Sample CSV for opportunity import."""
    return """name,account_name,stage,amount,probability
New Widget Project,Acme Corporation,proposal,50000,75
Expansion Deal,Acme Corporation,negotiation,120000,90
First Order,Beta Industries,qualification,25000,40
"""


@pytest.fixture
def account_config() -> ImportConfig:
    """Default config for account import."""
    return ImportConfig(
        entity_type=ImportEntityType.ACCOUNT,
        field_mappings=[],
        duplicate_action=DuplicateAction.SKIP,
        duplicate_check_fields=["name", "email"],
    )


@pytest.fixture
def contact_config() -> ImportConfig:
    """Default config for contact import."""
    return ImportConfig(
        entity_type=ImportEntityType.CONTACT,
        field_mappings=[],
        duplicate_action=DuplicateAction.SKIP,
        duplicate_check_fields=["email"],
    )


# =============================================================================
# Test CSV Parsing
# =============================================================================


class TestCSVParsing:
    """Tests for CSV parsing functionality."""
    
    def test_parse_csv_basic(self, service: CSVImportService, account_config: ImportConfig) -> None:
        """Test basic CSV parsing."""
        csv_content = """name,email
Company A,a@test.com
Company B,b@test.com
"""
        headers, rows = service.parse_csv(csv_content, account_config)
        
        assert headers == ["name", "email"]
        assert len(rows) == 2
        assert rows[0]["name"] == "Company A"
        assert rows[1]["email"] == "b@test.com"
    
    def test_parse_csv_with_quotes(self, service: CSVImportService, account_config: ImportConfig) -> None:
        """Test CSV parsing with quoted fields."""
        csv_content = '''name,description
"Acme, Inc.","A company with, commas"
'''
        headers, rows = service.parse_csv(csv_content, account_config)
        
        assert rows[0]["name"] == "Acme, Inc."
        assert rows[0]["description"] == "A company with, commas"
    
    def test_parse_csv_with_unicode(self, service: CSVImportService, account_config: ImportConfig) -> None:
        """Test CSV parsing with Unicode characters."""
        csv_content = """name,city
Société Française,Paris
日本企業,Tokyo
"""
        headers, rows = service.parse_csv(csv_content, account_config)
        
        assert rows[0]["name"] == "Société Française"
        assert rows[1]["city"] == "Tokyo"
    
    def test_parse_csv_bytes(self, service: CSVImportService, account_config: ImportConfig) -> None:
        """Test parsing CSV from bytes."""
        csv_bytes = b"name,email\nCompany A,a@test.com"
        headers, rows = service.parse_csv(csv_bytes, account_config)
        
        assert headers == ["name", "email"]
        assert len(rows) == 1
    
    def test_parse_csv_empty(self, service: CSVImportService, account_config: ImportConfig) -> None:
        """Test parsing empty CSV."""
        csv_content = "name,email\n"
        headers, rows = service.parse_csv(csv_content, account_config)
        
        assert headers == ["name", "email"]
        assert len(rows) == 0
    
    def test_parse_csv_custom_delimiter(self, service: CSVImportService) -> None:
        """Test parsing CSV with custom delimiter."""
        csv_content = "name;email\nCompany A;a@test.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[],
            delimiter=";",
        )
        headers, rows = service.parse_csv(csv_content, config)
        
        assert headers == ["name", "email"]
        assert rows[0]["name"] == "Company A"


# =============================================================================
# Test Field Mapping Detection
# =============================================================================


class TestFieldMappingDetection:
    """Tests for automatic field mapping detection."""
    
    def test_detect_exact_matches(self, service: CSVImportService) -> None:
        """Test detection of exact field name matches."""
        headers = ["name", "email", "phone", "city"]
        mappings = service.detect_field_mappings(headers, ImportEntityType.ACCOUNT)
        
        target_fields = [m.target_field for m in mappings]
        assert "name" in target_fields
        assert "email" in target_fields
        assert "phone" in target_fields
        assert "city" in target_fields
    
    def test_detect_with_aliases(self, service: CSVImportService) -> None:
        """Test detection using common aliases."""
        headers = ["Company", "Mail", "Tel", "Zip"]
        mappings = service.detect_field_mappings(headers, ImportEntityType.ACCOUNT)
        
        target_fields = [m.target_field for m in mappings]
        assert "name" in target_fields  # Company -> name
        assert "email" in target_fields  # Mail -> email
        assert "phone" in target_fields  # Tel -> phone
        assert "postal_code" in target_fields  # Zip -> postal_code
    
    def test_detect_contact_mappings(self, service: CSVImportService) -> None:
        """Test mapping detection for contacts."""
        headers = ["FirstName", "LastName", "Email", "Title"]
        mappings = service.detect_field_mappings(headers, ImportEntityType.CONTACT)
        
        target_fields = [m.target_field for m in mappings]
        assert "first_name" in target_fields
        assert "last_name" in target_fields
        assert "email" in target_fields
        assert "job_title" in target_fields
    
    def test_detect_opportunity_mappings(self, service: CSVImportService) -> None:
        """Test mapping detection for opportunities."""
        headers = ["Name", "Account Name", "Stage", "Value"]
        mappings = service.detect_field_mappings(headers, ImportEntityType.OPPORTUNITY)
        
        target_fields = [m.target_field for m in mappings]
        assert "name" in target_fields
        assert "stage" in target_fields
        assert "amount" in target_fields  # Value -> amount
    
    def test_normalize_header(self, service: CSVImportService) -> None:
        """Test header normalization."""
        assert service._normalize_header("First Name") == "first_name"
        assert service._normalize_header("E-mail") == "e_mail"
        assert service._normalize_header("PHONE") == "phone"
        assert service._normalize_header(" Address ") == "address"


# =============================================================================
# Test Validation
# =============================================================================


class TestValidation:
    """Tests for row validation."""
    
    def test_validate_required_field_present(self, service: CSVImportService) -> None:
        """Test validation passes when required field is present."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        row = {"name": "Test Company"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 0
    
    def test_validate_required_field_missing(self, service: CSVImportService) -> None:
        """Test validation fails when required field is missing."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        row = {"name": ""}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 1
        assert errors[0].error_type == "required"
        assert errors[0].row_number == 2
    
    def test_validate_invalid_email(self, service: CSVImportService) -> None:
        """Test validation of email format."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
        )
        row = {"email": "not-an-email"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 1
        assert errors[0].error_type == "invalid_email"
    
    def test_validate_valid_email(self, service: CSVImportService) -> None:
        """Test validation passes for valid email."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
        )
        row = {"email": "test@example.com"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 0
    
    def test_validate_invalid_number(self, service: CSVImportService) -> None:
        """Test validation of numeric fields."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="employees_count", source_columns=["employees"]),
            ],
        )
        row = {"employees": "not-a-number"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 1
        assert errors[0].error_type == "invalid_number"
    
    def test_validate_valid_number(self, service: CSVImportService) -> None:
        """Test validation passes for valid numbers."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="employees_count", source_columns=["employees"]),
                FieldMapping(target_field="annual_revenue", source_columns=["revenue"]),
            ],
        )
        row = {"employees": "100", "revenue": "1234567.89"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 0
    
    def test_validate_invalid_enum(self, service: CSVImportService) -> None:
        """Test validation of enum fields."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="account_type", source_columns=["type"]),
            ],
        )
        row = {"type": "invalid_type"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 1
        assert errors[0].error_type == "invalid_enum"
    
    def test_validate_valid_enum(self, service: CSVImportService) -> None:
        """Test validation passes for valid enum values."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="account_type", source_columns=["type"]),
                FieldMapping(target_field="status", source_columns=["status"]),
            ],
        )
        row = {"type": "customer", "status": "active"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 0
    
    def test_validate_multiple_errors(self, service: CSVImportService) -> None:
        """Test collecting multiple validation errors."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
                FieldMapping(target_field="employees_count", source_columns=["employees"]),
            ],
        )
        row = {"name": "", "email": "bad-email", "employees": "abc"}
        
        errors = service.validate_row(row, 2, config)
        
        assert len(errors) == 3


# =============================================================================
# Test Duplicate Detection
# =============================================================================


class TestDuplicateDetection:
    """Tests for duplicate entity detection."""
    
    def test_detect_exact_duplicate_by_name(self, service: CSVImportService) -> None:
        """Test detecting duplicate by exact name match."""
        service.seed_account("Acme Corporation", email="info@acme.com")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "Acme Corporation", "email": "other@email.com"},
            ["name"],
        )
        
        assert len(duplicates) == 1
        assert duplicates[0].match_score >= 0.8
    
    def test_detect_duplicate_by_email(self, service: CSVImportService) -> None:
        """Test detecting duplicate by email match."""
        service.seed_account("Acme Corp", email="info@acme.com")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "Different Name", "email": "info@acme.com"},
            ["email"],
        )
        
        assert len(duplicates) == 1
        assert duplicates[0].match_score >= 0.8
    
    def test_detect_duplicate_normalized_name(self, service: CSVImportService) -> None:
        """Test detecting duplicate with normalized company name."""
        service.seed_account("Acme Corporation Inc.")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "Acme Corporation"},
            ["name"],
        )
        
        assert len(duplicates) == 1
    
    def test_detect_duplicate_case_insensitive(self, service: CSVImportService) -> None:
        """Test case-insensitive duplicate detection."""
        service.seed_account("ACME CORPORATION")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "acme corporation"},
            ["name"],
        )
        
        assert len(duplicates) == 1
    
    def test_no_duplicate_detected(self, service: CSVImportService) -> None:
        """Test no false positive duplicates."""
        service.seed_account("Acme Corporation")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "Completely Different Company"},
            ["name"],
        )
        
        assert len(duplicates) == 0
    
    def test_detect_multiple_duplicates(self, service: CSVImportService) -> None:
        """Test detecting multiple potential duplicates."""
        service.seed_account("Acme Corp", email="info@acme.com")
        service.seed_account("Acme Corporation", email="sales@acme.com")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "Acme Corp"},
            ["name"],
        )
        
        # Should find both as potential matches
        assert len(duplicates) >= 1
    
    def test_duplicate_score_ordering(self, service: CSVImportService) -> None:
        """Test duplicates are ordered by score."""
        service.seed_account("Exact Match Company")
        service.seed_account("Match Company")
        
        duplicates = service.detect_duplicates(
            ImportEntityType.ACCOUNT,
            {"name": "Exact Match Company"},
            ["name"],
        )
        
        if len(duplicates) > 1:
            assert duplicates[0].match_score >= duplicates[1].match_score
    
    def test_normalize_company_name(self, service: CSVImportService) -> None:
        """Test company name normalization."""
        assert service._normalize_company_name("Acme Inc.") == "acme"
        assert service._normalize_company_name("Test LLC") == "test"
        assert service._normalize_company_name("Company S.A.") == "company sa"
        assert service._normalize_company_name("Beta SARL") == "beta"


# =============================================================================
# Test Import Execution
# =============================================================================


class TestImportExecution:
    """Tests for import execution."""
    
    def test_import_single_account(self, service: CSVImportService) -> None:
        """Test importing a single account."""
        csv_content = "name,email\nTest Company,test@test.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 1
        assert result.rows_failed == 0
        assert len(result.row_results) == 1
        assert result.row_results[0].status == RowStatus.IMPORTED
        assert result.row_results[0].entity_id is not None
    
    def test_import_multiple_accounts(
        self,
        service: CSVImportService,
        account_csv: str,
    ) -> None:
        """Test importing multiple accounts."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[],  # Auto-detect
        )
        
        result = service.import_csv(account_csv, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 3
        assert result.total_rows == 3
    
    def test_import_with_validation_errors(self, service: CSVImportService) -> None:
        """Test import with validation errors."""
        csv_content = """name,email
,missing-name@test.com
Valid Company,valid@test.com
"""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED_WITH_ERRORS
        assert result.rows_imported == 1
        assert result.rows_failed == 1
    
    def test_import_skip_duplicates(self, service: CSVImportService) -> None:
        """Test skipping duplicate rows."""
        # Pre-seed an account
        service.seed_account("Acme Corp")
        
        csv_content = "name,email\nAcme Corp,new@acme.com\nNew Company,new@company.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            duplicate_action=DuplicateAction.SKIP,
            duplicate_check_fields=["name"],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 1
        assert result.rows_skipped == 1
    
    def test_import_update_duplicates(self, service: CSVImportService) -> None:
        """Test updating duplicate records."""
        # Pre-seed an account
        original_id = service.seed_account("Acme Corp", email="old@acme.com")
        
        csv_content = "name,email\nAcme Corp,new@acme.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            duplicate_action=DuplicateAction.UPDATE,
            duplicate_check_fields=["name"],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 1
        assert result.row_results[0].action_taken == "updated"
        
        # Verify update
        account = service.get_account(original_id)
        assert account["email"] == "new@acme.com"
    
    def test_import_fail_on_duplicates(self, service: CSVImportService) -> None:
        """Test failing on duplicate records."""
        service.seed_account("Acme Corp")
        
        csv_content = "name,email\nAcme Corp,new@acme.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            duplicate_action=DuplicateAction.FAIL,
            duplicate_check_fields=["name"],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED_WITH_ERRORS
        assert result.rows_failed == 1
    
    def test_import_dry_run(self, service: CSVImportService) -> None:
        """Test dry run mode."""
        csv_content = "name,email\nTest Company,test@test.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            dry_run=True,
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        # No actual imports in dry run
        assert result.rows_imported == 0
    
    def test_import_with_default_values(self, service: CSVImportService) -> None:
        """Test import using default values."""
        csv_content = "name\nTest Company"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(
                    target_field="country",
                    mapping_type=FieldMappingType.CONSTANT,
                    constant_value="Morocco",
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        entity_id = result.row_results[0].entity_id
        account = service.get_account(entity_id)
        assert account["country"] == "Morocco"
    
    def test_import_with_max_errors(self, service: CSVImportService) -> None:
        """Test import stops at max errors."""
        # Create CSV with many invalid rows
        csv_content = "name,email\n" + "\n".join([",bad-email" for _ in range(10)])
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            max_errors=5,
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.FAILED
        assert "Too many validation errors" in result.errors[0]


# =============================================================================
# Test Import Jobs
# =============================================================================


class TestImportJobs:
    """Tests for import job management."""
    
    def test_create_import_job(self, service: CSVImportService) -> None:
        """Test creating an import job."""
        job = service.create_import_job(ImportEntityType.ACCOUNT)
        
        assert job.job_id is not None
        assert job.entity_type == ImportEntityType.ACCOUNT
        assert job.status == ImportStatus.PENDING
    
    def test_get_import_job(self, service: CSVImportService) -> None:
        """Test retrieving an import job."""
        job = service.create_import_job(ImportEntityType.ACCOUNT)
        
        retrieved = service.get_import_job(job.job_id)
        
        assert retrieved is not None
        assert retrieved.job_id == job.job_id
    
    def test_get_nonexistent_job(self, service: CSVImportService) -> None:
        """Test retrieving a non-existent job."""
        retrieved = service.get_import_job(uuid4())
        
        assert retrieved is None
    
    def test_list_import_jobs(self, service: CSVImportService) -> None:
        """Test listing import jobs."""
        service.create_import_job(ImportEntityType.ACCOUNT)
        service.create_import_job(ImportEntityType.CONTACT)
        service.create_import_job(ImportEntityType.OPPORTUNITY)
        
        jobs = service.list_import_jobs()
        
        assert len(jobs) == 3
    
    def test_list_import_jobs_by_type(self, service: CSVImportService) -> None:
        """Test filtering jobs by entity type."""
        service.create_import_job(ImportEntityType.ACCOUNT)
        service.create_import_job(ImportEntityType.CONTACT)
        
        jobs = service.list_import_jobs(entity_type=ImportEntityType.ACCOUNT)
        
        assert len(jobs) == 1
        assert jobs[0].entity_type == ImportEntityType.ACCOUNT
    
    def test_cancel_import_job(self, service: CSVImportService) -> None:
        """Test cancelling an import job."""
        job = service.create_import_job(ImportEntityType.ACCOUNT)
        
        cancelled = service.cancel_import_job(job.job_id)
        
        assert cancelled is not None
        assert cancelled.status == ImportStatus.CANCELLED


# =============================================================================
# Test Audit Logging
# =============================================================================


class TestAuditLogging:
    """Tests for audit log creation during import."""
    
    def test_audit_entry_on_create(self, service: CSVImportService) -> None:
        """Test audit entry created on import."""
        csv_content = "name\nTest Company"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
            create_audit_entries=True,
        )
        
        service.import_csv(csv_content, config)
        
        audit_log = service.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]["action"] == "create"
        assert audit_log[0]["source"] == "csv_import"
    
    def test_audit_entry_on_update(self, service: CSVImportService) -> None:
        """Test audit entry created on duplicate update."""
        original_id = service.seed_account("Acme Corp", email="old@acme.com")
        
        csv_content = "name,email\nAcme Corp,new@acme.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            duplicate_action=DuplicateAction.UPDATE,
            duplicate_check_fields=["name"],
            create_audit_entries=True,
        )
        
        service.import_csv(csv_content, config)
        
        audit_log = service.get_audit_log()
        assert len(audit_log) == 1
        assert audit_log[0]["action"] == "update"
        assert audit_log[0]["entity_id"] == original_id
    
    def test_audit_disabled(self, service: CSVImportService) -> None:
        """Test no audit entries when disabled."""
        csv_content = "name\nTest Company"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
            create_audit_entries=False,
        )
        
        service.import_csv(csv_content, config)
        
        audit_log = service.get_audit_log()
        assert len(audit_log) == 0


# =============================================================================
# Test Template Generation
# =============================================================================


class TestTemplateGeneration:
    """Tests for import template generation."""
    
    def test_generate_account_template(self, service: CSVImportService) -> None:
        """Test generating account import template."""
        template = service.generate_import_template(ImportEntityType.ACCOUNT)
        
        assert "name" in template
        assert "email" in template
        assert "phone" in template
        assert "country" in template
    
    def test_generate_contact_template(self, service: CSVImportService) -> None:
        """Test generating contact import template."""
        template = service.generate_import_template(ImportEntityType.CONTACT)
        
        assert "first_name" in template
        assert "last_name" in template
        assert "email" in template
    
    def test_generate_opportunity_template(self, service: CSVImportService) -> None:
        """Test generating opportunity import template."""
        template = service.generate_import_template(ImportEntityType.OPPORTUNITY)
        
        assert "name" in template
        assert "stage" in template
        assert "amount" in template


# =============================================================================
# Test Statistics
# =============================================================================


class TestStatistics:
    """Tests for import statistics."""
    
    def test_get_job_statistics(self, service: CSVImportService) -> None:
        """Test getting statistics for a specific job."""
        csv_content = "name\nCompany A\nCompany B\nCompany C"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        stats = service.get_import_statistics(result.job_id)
        
        assert stats["total_rows"] == 3
        assert stats["rows_imported"] == 3
        assert stats["success_rate"] == 1.0
    
    def test_get_aggregate_statistics(self, service: CSVImportService) -> None:
        """Test getting aggregate statistics."""
        # Run a couple of imports
        csv1 = "name\nCompany A"
        csv2 = "name\nCompany B"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        
        service.import_csv(csv1, config)
        service.import_csv(csv2, config)
        
        stats = service.get_import_statistics()
        
        assert stats["total_jobs"] == 2
        assert stats["successful_jobs"] == 2
        assert stats["total_rows_imported"] == 2


# =============================================================================
# Test Field Mapping Types
# =============================================================================


class TestFieldMappingTypes:
    """Tests for different field mapping types."""
    
    def test_direct_mapping(self, service: CSVImportService) -> None:
        """Test direct field mapping."""
        csv_content = "name\nDirect Value"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(
                    target_field="name",
                    source_columns=["name"],
                    mapping_type=FieldMappingType.DIRECT,
                    required=True,
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        entity_id = result.row_results[0].entity_id
        account = service.get_account(entity_id)
        
        assert account["name"] == "Direct Value"
    
    def test_constant_mapping(self, service: CSVImportService) -> None:
        """Test constant value mapping."""
        csv_content = "name\nTest Company"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(
                    target_field="status",
                    mapping_type=FieldMappingType.CONSTANT,
                    constant_value="active",
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        entity_id = result.row_results[0].entity_id
        account = service.get_account(entity_id)
        
        assert account["status"] == "active"
    
    def test_concat_mapping(self, service: CSVImportService) -> None:
        """Test concatenation mapping."""
        csv_content = "first,last\nJohn,Doe"
        config = ImportConfig(
            entity_type=ImportEntityType.CONTACT,
            field_mappings=[
                FieldMapping(target_field="first_name", source_columns=["first"], required=True),
                FieldMapping(target_field="last_name", source_columns=["last"], required=True),
                FieldMapping(
                    target_field="description",
                    mapping_type=FieldMappingType.CONCAT,
                    source_columns=["first", "last"],
                    separator=" - ",
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        entity_id = result.row_results[0].entity_id
        contact = service.get_contact(entity_id)
        
        assert contact["description"] == "John - Doe"
    
    def test_default_value_used(self, service: CSVImportService) -> None:
        """Test default value when field is empty."""
        csv_content = "name,country\nTest Company,"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(
                    target_field="country",
                    source_columns=["country"],
                    default_value="Morocco",
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        entity_id = result.row_results[0].entity_id
        account = service.get_account(entity_id)
        
        assert account["country"] == "Morocco"


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_csv(self, service: CSVImportService) -> None:
        """Test importing empty CSV."""
        csv_content = "name,email\n"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.total_rows == 0
        assert result.rows_imported == 0
    
    def test_whitespace_only_values(self, service: CSVImportService) -> None:
        """Test handling of whitespace-only values."""
        csv_content = "name,email\n   ,test@test.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        # Whitespace-only should be treated as empty/missing, causing validation failure
        assert result.rows_failed == 1
        assert result.rows_imported == 0
    
    def test_extra_columns_ignored(self, service: CSVImportService) -> None:
        """Test that unmapped columns are ignored."""
        csv_content = "name,extra_col,another_col\nTest Company,ignore,this"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 1
    
    def test_missing_columns(self, service: CSVImportService) -> None:
        """Test handling missing columns gracefully."""
        csv_content = "name\nTest Company"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),  # Column doesn't exist
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 1
    
    def test_special_characters_in_values(self, service: CSVImportService) -> None:
        """Test handling special characters."""
        csv_content = 'name,description\n"Company ""Test""","Line 1\nLine 2"'
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="description", source_columns=["description"]),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED


# =============================================================================
# Test Contacts with Account Lookup
# =============================================================================


class TestContactAccountLookup:
    """Tests for contact import with account lookup."""
    
    def test_contact_with_existing_account(self, service: CSVImportService) -> None:
        """Test importing contact linked to existing account."""
        # Create account first
        account_id = service.seed_account("Acme Corporation")
        
        csv_content = "first_name,last_name,account_name\nJohn,Doe,Acme Corporation"
        config = ImportConfig(
            entity_type=ImportEntityType.CONTACT,
            field_mappings=[
                FieldMapping(target_field="first_name", source_columns=["first_name"], required=True),
                FieldMapping(target_field="last_name", source_columns=["last_name"], required=True),
                FieldMapping(
                    target_field="account_id",
                    source_columns=["account_name"],
                    mapping_type=FieldMappingType.LOOKUP,
                    lookup_entity="account",
                    lookup_field="name",
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        entity_id = result.row_results[0].entity_id
        contact = service.get_contact(entity_id)
        assert contact["account_id"] == account_id
    
    def test_contact_with_nonexistent_account(self, service: CSVImportService) -> None:
        """Test importing contact with non-existent account."""
        csv_content = "first_name,last_name,account_name\nJohn,Doe,Unknown Company"
        config = ImportConfig(
            entity_type=ImportEntityType.CONTACT,
            field_mappings=[
                FieldMapping(target_field="first_name", source_columns=["first_name"], required=True),
                FieldMapping(target_field="last_name", source_columns=["last_name"], required=True),
                FieldMapping(
                    target_field="account_id",
                    source_columns=["account_name"],
                    mapping_type=FieldMappingType.LOOKUP,
                    lookup_entity="account",
                    lookup_field="name",
                ),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.status == ImportStatus.COMPLETED
        entity_id = result.row_results[0].entity_id
        contact = service.get_contact(entity_id)
        # account_id should not be set (lookup failed)
        assert "account_id" not in contact or contact.get("account_id") is None


# =============================================================================
# Test Import Duration and Timing
# =============================================================================


class TestImportTiming:
    """Tests for import timing and duration."""
    
    def test_import_records_duration(self, service: CSVImportService) -> None:
        """Test that import records duration."""
        csv_content = "name\nCompany A\nCompany B\nCompany C"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
    
    def test_import_timestamps_order(self, service: CSVImportService) -> None:
        """Test that timestamps are in correct order."""
        csv_content = "name\nCompany A"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
        )
        
        result = service.import_csv(csv_content, config)
        
        assert result.started_at <= result.completed_at


# =============================================================================
# Full Integration Tests
# =============================================================================


class TestFullIntegration:
    """Full integration tests for complete import workflows."""
    
    def test_full_account_import_workflow(
        self,
        service: CSVImportService,
        account_csv: str,
    ) -> None:
        """Test complete account import workflow."""
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[],  # Auto-detect
            duplicate_action=DuplicateAction.SKIP,
            duplicate_check_fields=["name", "email"],
            create_audit_entries=True,
        )
        
        result = service.import_csv(account_csv, config)
        
        # Verify result
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 3
        
        # Verify all accounts created
        for row_result in result.row_results:
            assert row_result.entity_id is not None
            account = service.get_account(row_result.entity_id)
            assert account is not None
        
        # Verify audit log
        audit_log = service.get_audit_log()
        assert len(audit_log) == 3
    
    def test_full_contact_import_workflow(
        self,
        service: CSVImportService,
        contact_csv: str,
    ) -> None:
        """Test complete contact import workflow."""
        config = ImportConfig(
            entity_type=ImportEntityType.CONTACT,
            field_mappings=[],  # Auto-detect
            create_audit_entries=True,
        )
        
        result = service.import_csv(contact_csv, config)
        
        assert result.status == ImportStatus.COMPLETED
        assert result.rows_imported == 3
    
    def test_reimport_with_skip_duplicates(self, service: CSVImportService) -> None:
        """Test re-importing same data with skip duplicates."""
        csv_content = "name,email\nCompany A,a@test.com\nCompany B,b@test.com"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
                FieldMapping(target_field="email", source_columns=["email"]),
            ],
            duplicate_action=DuplicateAction.SKIP,
            duplicate_check_fields=["name"],
        )
        
        # First import
        result1 = service.import_csv(csv_content, config)
        assert result1.rows_imported == 2
        
        # Second import (should skip all)
        result2 = service.import_csv(csv_content, config)
        assert result2.rows_skipped == 2
        assert result2.rows_imported == 0
    
    def test_incremental_import(self, service: CSVImportService) -> None:
        """Test importing new records incrementally."""
        # First batch
        csv1 = "name\nCompany A\nCompany B"
        config = ImportConfig(
            entity_type=ImportEntityType.ACCOUNT,
            field_mappings=[
                FieldMapping(target_field="name", source_columns=["name"], required=True),
            ],
            duplicate_action=DuplicateAction.SKIP,
            duplicate_check_fields=["name"],
        )
        
        result1 = service.import_csv(csv1, config)
        assert result1.rows_imported == 2
        
        # Second batch with mix of new and existing
        csv2 = "name\nCompany A\nCompany C\nCompany D"
        result2 = service.import_csv(csv2, config)
        
        assert result2.rows_imported == 2  # C and D
        assert result2.rows_skipped == 1  # A (duplicate)

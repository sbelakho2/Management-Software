"""
CSV Import Service.

Provides functionality for importing Accounts, Contacts, and Opportunities
from CSV files with validation, duplicate detection, and audit logging.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class ImportEntityType(str, Enum):
    """Entity types that support CSV import."""
    
    ACCOUNT = "account"
    CONTACT = "contact"
    OPPORTUNITY = "opportunity"


class ImportStatus(str, Enum):
    """Status of an import job."""
    
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RowStatus(str, Enum):
    """Status of an individual row in the import."""
    
    PENDING = "pending"
    IMPORTED = "imported"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FAILED_VALIDATION = "failed_validation"
    FAILED_IMPORT = "failed_import"


class DuplicateAction(str, Enum):
    """Action to take when a duplicate is detected."""
    
    SKIP = "skip"
    UPDATE = "update"
    CREATE_NEW = "create_new"
    FAIL = "fail"


class FieldMappingType(str, Enum):
    """Type of field mapping."""
    
    DIRECT = "direct"  # Direct column to field mapping
    CONSTANT = "constant"  # Constant value for all rows
    TRANSFORM = "transform"  # Apply transformation function
    LOOKUP = "lookup"  # Look up value from another entity
    CONCAT = "concat"  # Concatenate multiple columns


@dataclass
class FieldMapping:
    """Mapping from CSV column(s) to entity field."""
    
    target_field: str
    mapping_type: FieldMappingType = FieldMappingType.DIRECT
    source_columns: list[str] = field(default_factory=list)
    constant_value: Any = None
    transform_function: str | None = None
    lookup_entity: str | None = None
    lookup_field: str | None = None
    separator: str = " "  # For CONCAT type
    required: bool = False
    default_value: Any = None


@dataclass
class ValidationError:
    """Validation error for a row."""
    
    row_number: int
    column: str | None
    field: str | None
    error_type: str
    message: str
    value: Any = None


@dataclass
class ImportRowResult:
    """Result of importing a single row."""
    
    row_number: int
    status: RowStatus
    entity_id: UUID | None = None
    entity_type: ImportEntityType | None = None
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate_of: UUID | None = None
    action_taken: str | None = None
    original_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportJobResult:
    """Result of an import job."""
    
    job_id: UUID
    entity_type: ImportEntityType
    status: ImportStatus
    total_rows: int
    rows_imported: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_failed: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    row_results: list[ImportRowResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DuplicateCandidate:
    """A potential duplicate entity."""
    
    entity_id: UUID
    entity_type: ImportEntityType
    match_score: float
    match_fields: dict[str, Any]
    match_reason: str


@dataclass
class ImportConfig:
    """Configuration for an import job."""
    
    entity_type: ImportEntityType
    field_mappings: list[FieldMapping]
    duplicate_action: DuplicateAction = DuplicateAction.SKIP
    duplicate_check_fields: list[str] = field(default_factory=list)
    skip_header: bool = True
    delimiter: str = ","
    quotechar: str = '"'
    encoding: str = "utf-8"
    dry_run: bool = False
    max_errors: int = 100
    import_batch_size: int = 50
    create_audit_entries: bool = True
    imported_by: UUID | None = None


# Default field mappings for each entity type
ACCOUNT_FIELD_MAPPINGS: dict[str, FieldMapping] = {
    "name": FieldMapping(
        target_field="name",
        required=True,
    ),
    "legal_name": FieldMapping(
        target_field="legal_name",
    ),
    "account_number": FieldMapping(
        target_field="account_number",
    ),
    "account_type": FieldMapping(
        target_field="account_type",
        default_value="customer",
    ),
    "status": FieldMapping(
        target_field="status",
        default_value="active",
    ),
    "tier": FieldMapping(
        target_field="tier",
    ),
    "industry": FieldMapping(
        target_field="industry",
    ),
    "website": FieldMapping(
        target_field="website",
    ),
    "phone": FieldMapping(
        target_field="phone",
    ),
    "email": FieldMapping(
        target_field="email",
    ),
    "address_line1": FieldMapping(
        target_field="address_line1",
    ),
    "address_line2": FieldMapping(
        target_field="address_line2",
    ),
    "city": FieldMapping(
        target_field="city",
    ),
    "state_province": FieldMapping(
        target_field="state_province",
    ),
    "postal_code": FieldMapping(
        target_field="postal_code",
    ),
    "country": FieldMapping(
        target_field="country",
        default_value="Morocco",
    ),
    "tax_id": FieldMapping(
        target_field="tax_id",
    ),
    "employees_count": FieldMapping(
        target_field="employees_count",
    ),
    "annual_revenue": FieldMapping(
        target_field="annual_revenue",
    ),
    "description": FieldMapping(
        target_field="description",
    ),
}


CONTACT_FIELD_MAPPINGS: dict[str, FieldMapping] = {
    "first_name": FieldMapping(
        target_field="first_name",
        required=True,
    ),
    "last_name": FieldMapping(
        target_field="last_name",
        required=True,
    ),
    "email": FieldMapping(
        target_field="email",
    ),
    "phone_mobile": FieldMapping(
        target_field="phone_mobile",
    ),
    "phone_work": FieldMapping(
        target_field="phone_work",
    ),
    "job_title": FieldMapping(
        target_field="job_title",
    ),
    "department": FieldMapping(
        target_field="department",
    ),
    "account_name": FieldMapping(
        target_field="account_name",
        mapping_type=FieldMappingType.LOOKUP,
        lookup_entity="account",
        lookup_field="name",
    ),
    "address_line1": FieldMapping(
        target_field="address_line1",
    ),
    "city": FieldMapping(
        target_field="city",
    ),
    "country": FieldMapping(
        target_field="country",
    ),
}


OPPORTUNITY_FIELD_MAPPINGS: dict[str, FieldMapping] = {
    "name": FieldMapping(
        target_field="name",
        required=True,
    ),
    "account_name": FieldMapping(
        target_field="account_id",
        mapping_type=FieldMappingType.LOOKUP,
        lookup_entity="account",
        lookup_field="name",
        required=True,
    ),
    "stage": FieldMapping(
        target_field="stage",
        default_value="prospecting",
    ),
    "amount": FieldMapping(
        target_field="amount",
    ),
    "probability": FieldMapping(
        target_field="probability",
    ),
    "close_date": FieldMapping(
        target_field="expected_close_date",
    ),
    "opportunity_type": FieldMapping(
        target_field="opportunity_type",
        default_value="new_business",
    ),
    "description": FieldMapping(
        target_field="description",
    ),
    "source": FieldMapping(
        target_field="source",
    ),
}


class CSVImportService:
    """Service for importing entities from CSV files."""
    
    def __init__(self) -> None:
        """Initialize the CSV import service."""
        # In-memory storage for import jobs
        self._import_jobs: dict[UUID, ImportJobResult] = {}
        self._accounts: dict[UUID, dict] = {}
        self._contacts: dict[UUID, dict] = {}
        self._opportunities: dict[UUID, dict] = {}
        self._account_contacts: list[dict] = []
        self._audit_log: list[dict] = []
    
    # =========================================================================
    # Import Job Management
    # =========================================================================
    
    def create_import_job(
        self,
        entity_type: ImportEntityType,
    ) -> ImportJobResult:
        """Create a new import job."""
        job_id = uuid4()
        job = ImportJobResult(
            job_id=job_id,
            entity_type=entity_type,
            status=ImportStatus.PENDING,
            total_rows=0,
        )
        self._import_jobs[job_id] = job
        return job
    
    def get_import_job(self, job_id: UUID) -> ImportJobResult | None:
        """Get an import job by ID."""
        return self._import_jobs.get(job_id)
    
    def list_import_jobs(
        self,
        entity_type: ImportEntityType | None = None,
        status: ImportStatus | None = None,
        limit: int = 50,
    ) -> list[ImportJobResult]:
        """List import jobs with optional filters."""
        jobs = list(self._import_jobs.values())
        
        if entity_type:
            jobs = [j for j in jobs if j.entity_type == entity_type]
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created time (job_id is time-based in UUID v1)
        jobs.sort(key=lambda j: j.started_at or datetime.min, reverse=True)
        
        return jobs[:limit]
    
    def cancel_import_job(self, job_id: UUID) -> ImportJobResult | None:
        """Cancel a pending or running import job."""
        job = self._import_jobs.get(job_id)
        if not job:
            return None
        
        if job.status in (ImportStatus.PENDING, ImportStatus.VALIDATING, ImportStatus.IMPORTING):
            job.status = ImportStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
        
        return job
    
    # =========================================================================
    # CSV Parsing
    # =========================================================================
    
    def parse_csv(
        self,
        content: str | bytes,
        config: ImportConfig,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Parse CSV content into headers and rows.
        
        Returns:
            Tuple of (headers, list of row dicts)
        """
        if isinstance(content, bytes):
            content = content.decode(config.encoding)
        
        reader = csv.DictReader(
            io.StringIO(content),
            delimiter=config.delimiter,
            quotechar=config.quotechar,
        )
        
        headers: list[str] = list(reader.fieldnames or [])
        rows = list(reader)
        
        return headers, rows
    
    def detect_field_mappings(
        self,
        headers: list[str],
        entity_type: ImportEntityType,
    ) -> list[FieldMapping]:
        """
        Auto-detect field mappings based on CSV headers.
        
        Matches headers to known field names using fuzzy matching.
        """
        # Get default mappings for entity type
        default_mappings = self._get_default_mappings(entity_type)
        
        detected: list[FieldMapping] = []
        
        for header in headers:
            normalized = self._normalize_header(header)
            
            # Try exact match first
            if normalized in default_mappings:
                mapping = default_mappings[normalized]
                mapping.source_columns = [header]
                detected.append(mapping)
                continue
            
            # Try fuzzy matching
            best_match = self._find_best_match(normalized, list(default_mappings.keys()))
            if best_match:
                mapping = default_mappings[best_match]
                mapping.source_columns = [header]
                detected.append(mapping)
        
        return detected
    
    def _get_default_mappings(
        self,
        entity_type: ImportEntityType,
    ) -> dict[str, FieldMapping]:
        """Get default field mappings for an entity type."""
        if entity_type == ImportEntityType.ACCOUNT:
            return ACCOUNT_FIELD_MAPPINGS.copy()
        elif entity_type == ImportEntityType.CONTACT:
            return CONTACT_FIELD_MAPPINGS.copy()
        elif entity_type == ImportEntityType.OPPORTUNITY:
            return OPPORTUNITY_FIELD_MAPPINGS.copy()
        return {}
    
    def _normalize_header(self, header: str) -> str:
        """Normalize a CSV header for matching."""
        # Lowercase, replace spaces/hyphens with underscores
        normalized = header.lower().strip()
        normalized = normalized.replace(" ", "_").replace("-", "_")
        normalized = normalized.replace(".", "_").replace("/", "_")
        return normalized
    
    def _find_best_match(
        self,
        header: str,
        field_names: list[str] | set[str],
    ) -> str | None:
        """Find the best matching field name for a header."""
        # Common aliases
        aliases = {
            "company": "name",
            "company_name": "name",
            "customer": "name",
            "customer_name": "name",
            "account": "name",
            "fname": "first_name",
            "lname": "last_name",
            "firstname": "first_name",
            "lastname": "last_name",
            "mail": "email",
            "e_mail": "email",
            "tel": "phone",
            "telephone": "phone",
            "mobile": "phone_mobile",
            "cell": "phone_mobile",
            "work_phone": "phone_work",
            "office_phone": "phone_work",
            "addr": "address_line1",
            "address": "address_line1",
            "street": "address_line1",
            "state": "state_province",
            "province": "state_province",
            "region": "state_province",
            "zip": "postal_code",
            "zipcode": "postal_code",
            "zip_code": "postal_code",
            "title": "job_title",
            "position": "job_title",
            "role": "job_title",
            "value": "amount",
            "deal_value": "amount",
            "revenue": "annual_revenue",
        }
        
        # Check aliases first
        if header in aliases:
            alias_target = aliases[header]
            if alias_target in field_names:
                return alias_target
        
        # Check if header is substring of field name or vice versa
        for field_name in field_names:
            if header in field_name or field_name in header:
                return field_name
        
        return None
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    def validate_row(
        self,
        row: dict[str, Any],
        row_number: int,
        config: ImportConfig,
    ) -> list[ValidationError]:
        """Validate a single row against the import configuration."""
        errors: list[ValidationError] = []
        
        for mapping in config.field_mappings:
            value = self._get_mapped_value(row, mapping)
            
            # Strip whitespace from string values
            if isinstance(value, str):
                value = value.strip()
            
            # Check required fields
            if mapping.required and (value is None or value == ""):
                errors.append(ValidationError(
                    row_number=row_number,
                    column=mapping.source_columns[0] if mapping.source_columns else None,
                    field=mapping.target_field,
                    error_type="required",
                    message=f"Required field '{mapping.target_field}' is missing or empty",
                    value=value,
                ))
            
            # Validate data types based on target field
            if value is not None and value != "":
                field_errors = self._validate_field_value(
                    value,
                    mapping.target_field,
                    config.entity_type,
                    row_number,
                    mapping.source_columns[0] if mapping.source_columns else None,
                )
                errors.extend(field_errors)
        
        return errors
    
    def _validate_field_value(
        self,
        value: Any,
        target_field: str,
        entity_type: ImportEntityType,
        row_number: int,
        column: str | None,
    ) -> list[ValidationError]:
        """Validate a field value against its expected type."""
        errors: list[ValidationError] = []
        
        # Email validation
        if target_field == "email" or target_field.endswith("_email"):
            if "@" not in str(value):
                errors.append(ValidationError(
                    row_number=row_number,
                    column=column,
                    field=target_field,
                    error_type="invalid_email",
                    message=f"Invalid email format: {value}",
                    value=value,
                ))
        
        # Numeric fields
        numeric_fields = {
            "employees_count", "annual_revenue", "amount", "probability",
            "quantity", "unit_price", "discount",
        }
        if target_field in numeric_fields:
            try:
                if target_field == "employees_count":
                    int(value)
                else:
                    Decimal(str(value))
            except (ValueError, InvalidOperation):
                errors.append(ValidationError(
                    row_number=row_number,
                    column=column,
                    field=target_field,
                    error_type="invalid_number",
                    message=f"Invalid numeric value: {value}",
                    value=value,
                ))
        
        # Enum fields
        enum_fields = {
            "account_type": ["customer", "prospect", "supplier", "partner", "competitor", "other"],
            "status": ["lead", "prospect", "qualified", "active", "inactive", "churned", "blocked"],
            "tier": ["strategic", "key", "standard", "small"],
            "stage": ["prospecting", "qualification", "needs_analysis", "value_proposition",
                      "proposal", "negotiation", "closed_won", "closed_lost"],
            "opportunity_type": ["new_business", "existing_business", "renewal", "upsell", "cross_sell"],
            "source": ["website", "referral", "trade_show", "cold_call", "inbound",
                       "partner", "existing_customer", "rfq", "other"],
        }
        if target_field in enum_fields:
            normalized_value = str(value).lower().strip()
            if normalized_value not in enum_fields[target_field]:
                errors.append(ValidationError(
                    row_number=row_number,
                    column=column,
                    field=target_field,
                    error_type="invalid_enum",
                    message=f"Invalid value '{value}'. Must be one of: {enum_fields[target_field]}",
                    value=value,
                ))
        
        return errors
    
    def _get_mapped_value(
        self,
        row: dict[str, Any],
        mapping: FieldMapping,
    ) -> Any:
        """Get the value for a field mapping from a row."""
        if mapping.mapping_type == FieldMappingType.CONSTANT:
            return mapping.constant_value
        
        if mapping.mapping_type == FieldMappingType.CONCAT:
            values = [row.get(col, "") for col in mapping.source_columns]
            return mapping.separator.join(v for v in values if v)
        
        if not mapping.source_columns:
            return mapping.default_value
        
        value = row.get(mapping.source_columns[0])
        
        if (value is None or value == "") and mapping.default_value is not None:
            return mapping.default_value
        
        return value
    
    # =========================================================================
    # Duplicate Detection
    # =========================================================================
    
    def detect_duplicates(
        self,
        entity_type: ImportEntityType,
        data: dict[str, Any],
        check_fields: list[str],
    ) -> list[DuplicateCandidate]:
        """
        Detect potential duplicate entities.
        
        Uses configurable fields for matching with fuzzy comparison.
        """
        candidates: list[DuplicateCandidate] = []
        
        # Get existing entities
        if entity_type == ImportEntityType.ACCOUNT:
            existing = self._accounts
        elif entity_type == ImportEntityType.CONTACT:
            existing = self._contacts
        elif entity_type == ImportEntityType.OPPORTUNITY:
            existing = self._opportunities
        else:
            return candidates
        
        for entity_id, entity in existing.items():
            if entity.get("is_deleted"):
                continue
            
            score, match_fields, reason = self._calculate_duplicate_score(
                data,
                entity,
                check_fields,
            )
            
            if score >= 0.8:  # High confidence match
                candidates.append(DuplicateCandidate(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    match_score=score,
                    match_fields=match_fields,
                    match_reason=reason,
                ))
        
        # Sort by score descending
        candidates.sort(key=lambda c: c.match_score, reverse=True)
        
        return candidates
    
    def _calculate_duplicate_score(
        self,
        new_data: dict[str, Any],
        existing: dict[str, Any],
        check_fields: list[str],
    ) -> tuple[float, dict[str, Any], str]:
        """
        Calculate duplicate match score between new and existing data.
        
        Returns (score, match_fields, reason)
        """
        if not check_fields:
            # Use default check fields
            check_fields = ["name", "email"]
        
        matches: dict[str, Any] = {}
        total_weight = 0.0
        weighted_score = 0.0
        
        # Field weights for scoring
        field_weights = {
            "email": 0.5,  # Email is strong identifier
            "name": 0.3,
            "account_number": 0.8,
            "tax_id": 0.9,
            "phone": 0.3,
            "website": 0.2,
        }
        
        for field in check_fields:
            new_value = new_data.get(field)
            existing_value = existing.get(field)
            
            if new_value is None or existing_value is None:
                continue
            
            weight = field_weights.get(field, 0.2)
            total_weight += weight
            
            # Compare values
            if self._values_match(new_value, existing_value, field):
                matches[field] = existing_value
                weighted_score += weight
        
        if total_weight == 0:
            return 0.0, {}, ""
        
        score = weighted_score / total_weight
        
        # Build reason string
        reason_parts = [f"{k}={v}" for k, v in matches.items()]
        reason = f"Matched on: {', '.join(reason_parts)}" if reason_parts else ""
        
        return score, matches, reason
    
    def _values_match(
        self,
        value1: Any,
        value2: Any,
        field: str,
    ) -> bool:
        """Check if two values match (with fuzzy comparison for strings)."""
        if value1 is None or value2 is None:
            return False
        
        # Normalize strings
        str1 = str(value1).lower().strip()
        str2 = str(value2).lower().strip()
        
        # Exact match
        if str1 == str2:
            return True
        
        # For names, check if one is contained in the other
        if field == "name":
            # Handle "Company Inc" vs "Company, Inc." variations
            normalized1 = self._normalize_company_name(str1)
            normalized2 = self._normalize_company_name(str2)
            if normalized1 == normalized2:
                return True
        
        return False
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize a company name for comparison."""
        # Remove common suffixes
        suffixes = [" inc", " inc.", " ltd", " ltd.", " llc", " sa", " sarl",
                    " gmbh", " co", " co.", " corp", " corp.", " corporation"]
        normalized = name.lower()
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # Remove punctuation
        normalized = normalized.replace(",", "").replace(".", "").replace("-", " ")
        
        # Collapse whitespace
        normalized = " ".join(normalized.split())
        
        return normalized
    
    # =========================================================================
    # Import Execution
    # =========================================================================
    
    def import_csv(
        self,
        content: str | bytes,
        config: ImportConfig,
    ) -> ImportJobResult:
        """
        Import entities from CSV content.
        
        This is the main entry point for CSV import.
        """
        # Create job
        job = self.create_import_job(config.entity_type)
        job.status = ImportStatus.VALIDATING
        job.started_at = datetime.now(timezone.utc)
        
        try:
            # Parse CSV
            headers, rows = self.parse_csv(content, config)
            job.total_rows = len(rows)
            
            # Auto-detect mappings if not provided
            if not config.field_mappings:
                config.field_mappings = self.detect_field_mappings(headers, config.entity_type)
            
            # Validate all rows first
            validation_errors = 0
            for i, row in enumerate(rows):
                row_number = i + 2  # Account for header row
                errors = self.validate_row(row, row_number, config)
                
                if errors:
                    validation_errors += 1
                    job.row_results.append(ImportRowResult(
                        row_number=row_number,
                        status=RowStatus.FAILED_VALIDATION,
                        errors=errors,
                        original_data=row,
                    ))
                    
                    if validation_errors >= config.max_errors:
                        job.status = ImportStatus.FAILED
                        job.errors.append(f"Too many validation errors ({validation_errors})")
                        job.completed_at = datetime.now(timezone.utc)
                        return job
            
            # If dry run, stop here
            if config.dry_run:
                job.status = ImportStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                return job
            
            # Import rows
            job.status = ImportStatus.IMPORTING
            
            for i, row in enumerate(rows):
                row_number = i + 2
                
                # Skip if already failed validation
                existing_result = next(
                    (r for r in job.row_results if r.row_number == row_number),
                    None,
                )
                if existing_result and existing_result.status == RowStatus.FAILED_VALIDATION:
                    job.rows_failed += 1
                    continue
                
                # Import the row
                result = self._import_row(row, row_number, config)
                job.row_results.append(result)
                
                if result.status == RowStatus.IMPORTED:
                    job.rows_imported += 1
                elif result.status == RowStatus.SKIPPED_DUPLICATE:
                    job.rows_skipped += 1
                elif result.status == RowStatus.FAILED_IMPORT:
                    job.rows_failed += 1
            
            # Determine final status
            if job.rows_failed > 0:
                job.status = ImportStatus.COMPLETED_WITH_ERRORS
            else:
                job.status = ImportStatus.COMPLETED
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.errors.append(str(e))
        
        job.completed_at = datetime.now(timezone.utc)
        if job.started_at:
            job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
        
        return job
    
    def _import_row(
        self,
        row: dict[str, Any],
        row_number: int,
        config: ImportConfig,
    ) -> ImportRowResult:
        """Import a single row."""
        try:
            # Build entity data from mappings
            entity_data = {}
            for mapping in config.field_mappings:
                value = self._get_mapped_value(row, mapping)
                if value is not None and value != "":
                    # Handle lookups
                    if mapping.mapping_type == FieldMappingType.LOOKUP:
                        lookup_id = self._resolve_lookup(
                            value,
                            mapping.lookup_entity,
                            mapping.lookup_field,
                        )
                        if lookup_id:
                            entity_data[mapping.target_field] = lookup_id
                    else:
                        entity_data[mapping.target_field] = value
            
            # Check for duplicates
            duplicates = self.detect_duplicates(
                config.entity_type,
                entity_data,
                config.duplicate_check_fields or ["name", "email"],
            )
            
            if duplicates:
                best_match = duplicates[0]
                
                if config.duplicate_action == DuplicateAction.SKIP:
                    return ImportRowResult(
                        row_number=row_number,
                        status=RowStatus.SKIPPED_DUPLICATE,
                        duplicate_of=best_match.entity_id,
                        action_taken="skipped",
                        original_data=row,
                    )
                
                elif config.duplicate_action == DuplicateAction.UPDATE:
                    # Update existing entity
                    self._update_entity(
                        config.entity_type,
                        best_match.entity_id,
                        entity_data,
                        config,
                    )
                    return ImportRowResult(
                        row_number=row_number,
                        status=RowStatus.IMPORTED,
                        entity_id=best_match.entity_id,
                        entity_type=config.entity_type,
                        duplicate_of=best_match.entity_id,
                        action_taken="updated",
                        original_data=row,
                    )
                
                elif config.duplicate_action == DuplicateAction.FAIL:
                    return ImportRowResult(
                        row_number=row_number,
                        status=RowStatus.FAILED_IMPORT,
                        duplicate_of=best_match.entity_id,
                        errors=[ValidationError(
                            row_number=row_number,
                            column=None,
                            field=None,
                            error_type="duplicate",
                            message=f"Duplicate of existing record: {best_match.entity_id}",
                        )],
                        original_data=row,
                    )
            
            # Create new entity
            entity_id = self._create_entity(config.entity_type, entity_data, config)
            
            return ImportRowResult(
                row_number=row_number,
                status=RowStatus.IMPORTED,
                entity_id=entity_id,
                entity_type=config.entity_type,
                action_taken="created",
                original_data=row,
            )
            
        except Exception as e:
            return ImportRowResult(
                row_number=row_number,
                status=RowStatus.FAILED_IMPORT,
                errors=[ValidationError(
                    row_number=row_number,
                    column=None,
                    field=None,
                    error_type="import_error",
                    message=str(e),
                )],
                original_data=row,
            )
    
    def _resolve_lookup(
        self,
        value: Any,
        lookup_entity: str | None,
        lookup_field: str | None,
    ) -> UUID | None:
        """Resolve a lookup value to an entity ID."""
        if not lookup_entity or not lookup_field:
            return None
        
        if lookup_entity == "account":
            for entity_id, entity in self._accounts.items():
                if entity.get(lookup_field) == value:
                    return entity_id
        
        return None
    
    def _create_entity(
        self,
        entity_type: ImportEntityType,
        data: dict[str, Any],
        config: ImportConfig,
    ) -> UUID:
        """Create a new entity."""
        entity_id = uuid4()
        now = datetime.now(timezone.utc)
        
        entity = {
            "id": entity_id,
            **data,
            "created_at": now,
            "updated_at": now,
            "is_deleted": False,
        }
        
        if entity_type == ImportEntityType.ACCOUNT:
            self._accounts[entity_id] = entity
        elif entity_type == ImportEntityType.CONTACT:
            self._contacts[entity_id] = entity
        elif entity_type == ImportEntityType.OPPORTUNITY:
            self._opportunities[entity_id] = entity
        
        # Create audit entry
        if config.create_audit_entries:
            self._create_audit_entry(
                entity_type=entity_type.value,
                entity_id=entity_id,
                action="create",
                data=data,
                user_id=config.imported_by,
            )
        
        return entity_id
    
    def _update_entity(
        self,
        entity_type: ImportEntityType,
        entity_id: UUID,
        data: dict[str, Any],
        config: ImportConfig,
    ) -> None:
        """Update an existing entity."""
        if entity_type == ImportEntityType.ACCOUNT:
            entities = self._accounts
        elif entity_type == ImportEntityType.CONTACT:
            entities = self._contacts
        elif entity_type == ImportEntityType.OPPORTUNITY:
            entities = self._opportunities
        else:
            return
        
        if entity_id not in entities:
            return
        
        old_data = entities[entity_id].copy()
        entities[entity_id].update(data)
        entities[entity_id]["updated_at"] = datetime.now(timezone.utc)
        
        # Create audit entry
        if config.create_audit_entries:
            self._create_audit_entry(
                entity_type=entity_type.value,
                entity_id=entity_id,
                action="update",
                data=data,
                old_data=old_data,
                user_id=config.imported_by,
            )
    
    def _create_audit_entry(
        self,
        entity_type: str,
        entity_id: UUID,
        action: str,
        data: dict[str, Any],
        old_data: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> None:
        """Create an audit log entry for an import action."""
        self._audit_log.append({
            "id": uuid4(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "new_data": data,
            "old_data": old_data,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "source": "csv_import",
        })
    
    # =========================================================================
    # Export Templates
    # =========================================================================
    
    def generate_import_template(
        self,
        entity_type: ImportEntityType,
    ) -> str:
        """Generate a CSV template for importing a specific entity type."""
        mappings = self._get_default_mappings(entity_type)
        
        # Get all field names
        headers = list(mappings.keys())
        
        # Create CSV with headers only
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # Add example row
        example_row = []
        for field in headers:
            mapping = mappings[field]
            if mapping.default_value:
                example_row.append(f"(default: {mapping.default_value})")
            elif mapping.required:
                example_row.append("(required)")
            else:
                example_row.append("(optional)")
        writer.writerow(example_row)
        
        return output.getvalue()
    
    # =========================================================================
    # Statistics and Reports
    # =========================================================================
    
    def get_import_statistics(
        self,
        job_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get statistics for import jobs."""
        if job_id:
            job = self._import_jobs.get(job_id)
            if not job:
                return {}
            
            return {
                "job_id": str(job.job_id),
                "entity_type": job.entity_type.value,
                "status": job.status.value,
                "total_rows": job.total_rows,
                "rows_imported": job.rows_imported,
                "rows_updated": job.rows_updated,
                "rows_skipped": job.rows_skipped,
                "rows_failed": job.rows_failed,
                "success_rate": job.rows_imported / job.total_rows if job.total_rows > 0 else 0,
                "duration_seconds": job.duration_seconds,
            }
        
        # Aggregate statistics
        total_jobs = len(self._import_jobs)
        successful_jobs = len([j for j in self._import_jobs.values() if j.status == ImportStatus.COMPLETED])
        
        return {
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": len([j for j in self._import_jobs.values() if j.status == ImportStatus.FAILED]),
            "total_rows_imported": sum(j.rows_imported for j in self._import_jobs.values()),
            "total_rows_failed": sum(j.rows_failed for j in self._import_jobs.values()),
        }
    
    # =========================================================================
    # Testing Helpers
    # =========================================================================
    
    def seed_account(
        self,
        name: str,
        **kwargs: Any,
    ) -> UUID:
        """Seed an account for testing."""
        entity_id = uuid4()
        self._accounts[entity_id] = {
            "id": entity_id,
            "name": name,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_deleted": False,
            **kwargs,
        }
        return entity_id
    
    def get_account(self, entity_id: UUID) -> dict | None:
        """Get an account by ID."""
        return self._accounts.get(entity_id)
    
    def get_contact(self, entity_id: UUID) -> dict | None:
        """Get a contact by ID."""
        return self._contacts.get(entity_id)
    
    def get_opportunity(self, entity_id: UUID) -> dict | None:
        """Get an opportunity by ID."""
        return self._opportunities.get(entity_id)
    
    def get_audit_log(self) -> list[dict]:
        """Get the audit log entries."""
        return self._audit_log.copy()
    
    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._import_jobs.clear()
        self._accounts.clear()
        self._contacts.clear()
        self._opportunities.clear()
        self._account_contacts.clear()
        self._audit_log.clear()

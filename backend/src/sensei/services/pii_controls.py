"""
PII Controls Service.

Manages Personally Identifiable Information (PII) data handling, including:
- PII field classification and detection
- Data masking and anonymization
- Access control for PII fields
- Consent management
- Retention policies for PII data
- Right to deletion (GDPR/CCPA compliance)
- Audit logging for PII access
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
import hashlib
import re


class PIICategory(str, Enum):
    """Categories of PII data."""

    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    SSN = "ssn"
    DATE_OF_BIRTH = "date_of_birth"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    GOVERNMENT_ID = "government_id"
    IP_ADDRESS = "ip_address"
    GEOLOCATION = "geolocation"
    DEVICE_ID = "device_id"
    ACCOUNT_INFO = "account_info"
    EMPLOYMENT = "employment"
    CUSTOM = "custom"


class SensitivityLevel(str, Enum):
    """Sensitivity levels for PII data."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaskingType(str, Enum):
    """Types of data masking."""

    FULL = "full"  # Complete redaction
    PARTIAL = "partial"  # Partial masking (e.g., ***@email.com)
    HASH = "hash"  # One-way hash
    PSEUDONYMIZE = "pseudonymize"  # Reversible pseudonymization
    TOKENIZE = "tokenize"  # Token-based replacement
    TRUNCATE = "truncate"  # Truncate to first/last N characters


class ConsentType(str, Enum):
    """Types of data consent."""

    COLLECTION = "collection"
    PROCESSING = "processing"
    SHARING = "sharing"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PROFILING = "profiling"


class ConsentStatus(str, Enum):
    """Consent status."""

    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


class PIIAccessType(str, Enum):
    """Types of PII data access."""

    VIEW = "view"
    EXPORT = "export"
    MODIFY = "modify"
    DELETE = "delete"
    SHARE = "share"


@dataclass
class PIIFieldDefinition:
    """Definition of a PII field."""

    id: UUID
    name: str
    table: str
    column: str
    category: PIICategory
    sensitivity: SensitivityLevel
    description: str
    detection_pattern: str | None
    masking_type: MaskingType
    retention_days: int | None
    requires_consent: bool
    consent_types: list[ConsentType]
    is_searchable: bool
    is_exportable: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class DataSubject:
    """A data subject (person whose PII is stored)."""

    id: UUID
    external_id: str  # User ID, customer ID, etc.
    subject_type: str  # user, customer, contact, etc.
    email: str | None
    created_at: datetime
    last_accessed_at: datetime | None
    deletion_requested_at: datetime | None
    deletion_completed_at: datetime | None


@dataclass
class Consent:
    """Consent record for a data subject."""

    id: UUID
    subject_id: UUID
    consent_type: ConsentType
    status: ConsentStatus
    purpose: str
    granted_at: datetime | None
    expires_at: datetime | None
    withdrawn_at: datetime | None
    source: str  # How consent was obtained
    version: str  # Version of privacy policy
    ip_address: str | None


@dataclass
class PIIAccessLog:
    """Log of PII data access."""

    id: UUID
    subject_id: UUID
    user_id: UUID
    field_id: UUID
    access_type: PIIAccessType
    accessed_at: datetime
    purpose: str
    ip_address: str | None
    data_snapshot: str | None  # Masked snapshot of accessed data


@dataclass
class DeletionRequest:
    """Request to delete PII data."""

    id: UUID
    subject_id: UUID
    requested_by: UUID
    requested_at: datetime
    reason: str
    status: str  # pending, processing, completed, failed
    completed_at: datetime | None
    affected_tables: list[str]
    deleted_records: int
    errors: list[str]


@dataclass
class PIIReport:
    """Report of PII data for a subject."""

    subject_id: UUID
    generated_at: datetime
    generated_by: UUID
    fields: list[dict[str, Any]]
    consents: list[Consent]
    access_logs: list[PIIAccessLog]


class PIIControlsService:
    """Service for managing PII data controls."""

    def __init__(self) -> None:
        """Initialize the PII controls service."""
        self._fields: dict[UUID, PIIFieldDefinition] = {}
        self._subjects: dict[UUID, DataSubject] = {}
        self._consents: dict[UUID, Consent] = {}
        self._access_logs: list[PIIAccessLog] = []
        self._deletion_requests: dict[UUID, DeletionRequest] = {}
        self._pseudonym_map: dict[str, str] = {}
        self._token_map: dict[str, str] = {}

        # Initialize default PII field definitions
        self._initialize_default_fields()

    def _initialize_default_fields(self) -> None:
        """Initialize default PII field definitions."""
        now = datetime.now(timezone.utc)

        # User PII fields
        self._add_default_field(
            name="User Email",
            table="user",
            column="email",
            category=PIICategory.EMAIL,
            sensitivity=SensitivityLevel.HIGH,
            description="User's email address",
            detection_pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            masking_type=MaskingType.PARTIAL,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION, ConsentType.PROCESSING],
        )

        self._add_default_field(
            name="User Name",
            table="user",
            column="full_name",
            category=PIICategory.NAME,
            sensitivity=SensitivityLevel.MEDIUM,
            description="User's full name",
            detection_pattern=None,
            masking_type=MaskingType.PARTIAL,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
        )

        self._add_default_field(
            name="User Phone",
            table="user",
            column="phone",
            category=PIICategory.PHONE,
            sensitivity=SensitivityLevel.MEDIUM,
            description="User's phone number",
            detection_pattern=r"\+?[\d\s\-\(\)]{10,}",
            masking_type=MaskingType.PARTIAL,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
        )

        # Customer PII fields
        self._add_default_field(
            name="Customer Contact Email",
            table="customer_contact",
            column="email",
            category=PIICategory.EMAIL,
            sensitivity=SensitivityLevel.HIGH,
            description="Customer contact email",
            detection_pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            masking_type=MaskingType.PARTIAL,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION, ConsentType.SHARING],
        )

        self._add_default_field(
            name="Customer Address",
            table="customer",
            column="address",
            category=PIICategory.ADDRESS,
            sensitivity=SensitivityLevel.MEDIUM,
            description="Customer physical address",
            detection_pattern=None,
            masking_type=MaskingType.TRUNCATE,
            requires_consent=True,
            consent_types=[ConsentType.COLLECTION],
        )

        # Training/certification PII
        self._add_default_field(
            name="Training Completion Records",
            table="training_record",
            column="user_id",
            category=PIICategory.EMPLOYMENT,
            sensitivity=SensitivityLevel.MEDIUM,
            description="Training completion linked to individual",
            detection_pattern=None,
            masking_type=MaskingType.PSEUDONYMIZE,
            requires_consent=False,
            consent_types=[],
            retention_days=365 * 7,  # 7 years
        )

        # Audit/activity PII
        self._add_default_field(
            name="IP Address",
            table="audit_log",
            column="ip_address",
            category=PIICategory.IP_ADDRESS,
            sensitivity=SensitivityLevel.LOW,
            description="IP address from audit logs",
            detection_pattern=r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
            masking_type=MaskingType.TRUNCATE,
            requires_consent=False,
            consent_types=[],
            retention_days=365,
        )

        self._add_default_field(
            name="User Agent",
            table="audit_log",
            column="user_agent",
            category=PIICategory.DEVICE_ID,
            sensitivity=SensitivityLevel.LOW,
            description="Browser user agent string",
            detection_pattern=None,
            masking_type=MaskingType.HASH,
            requires_consent=False,
            consent_types=[],
            retention_days=365,
        )

    def _add_default_field(
        self,
        name: str,
        table: str,
        column: str,
        category: PIICategory,
        sensitivity: SensitivityLevel,
        description: str,
        detection_pattern: str | None,
        masking_type: MaskingType,
        requires_consent: bool,
        consent_types: list[ConsentType],
        retention_days: int | None = None,
    ) -> PIIFieldDefinition:
        """Add a default PII field definition."""
        now = datetime.now(timezone.utc)

        field_def = PIIFieldDefinition(
            id=uuid4(),
            name=name,
            table=table,
            column=column,
            category=category,
            sensitivity=sensitivity,
            description=description,
            detection_pattern=detection_pattern,
            masking_type=masking_type,
            retention_days=retention_days,
            requires_consent=requires_consent,
            consent_types=consent_types,
            is_searchable=sensitivity not in [SensitivityLevel.CRITICAL],
            is_exportable=True,
            created_at=now,
            updated_at=now,
        )

        self._fields[field_def.id] = field_def
        return field_def

    def create_field_definition(
        self,
        name: str,
        table: str,
        column: str,
        category: PIICategory,
        sensitivity: SensitivityLevel,
        description: str,
        detection_pattern: str | None = None,
        masking_type: MaskingType = MaskingType.FULL,
        retention_days: int | None = None,
        requires_consent: bool = True,
        consent_types: list[ConsentType] | None = None,
        is_searchable: bool = True,
        is_exportable: bool = True,
    ) -> PIIFieldDefinition:
        """Create a new PII field definition."""
        now = datetime.now(timezone.utc)

        field_def = PIIFieldDefinition(
            id=uuid4(),
            name=name,
            table=table,
            column=column,
            category=category,
            sensitivity=sensitivity,
            description=description,
            detection_pattern=detection_pattern,
            masking_type=masking_type,
            retention_days=retention_days,
            requires_consent=requires_consent,
            consent_types=consent_types or [],
            is_searchable=is_searchable,
            is_exportable=is_exportable,
            created_at=now,
            updated_at=now,
        )

        self._fields[field_def.id] = field_def
        return field_def

    def get_field_definition(self, field_id: UUID) -> PIIFieldDefinition | None:
        """Get a PII field definition by ID."""
        return self._fields.get(field_id)

    def get_field_by_column(
        self, table: str, column: str
    ) -> PIIFieldDefinition | None:
        """Get a PII field definition by table and column."""
        for field_def in self._fields.values():
            if field_def.table == table and field_def.column == column:
                return field_def
        return None

    def get_field_definitions(
        self,
        category: PIICategory | None = None,
        sensitivity: SensitivityLevel | None = None,
        table: str | None = None,
    ) -> list[PIIFieldDefinition]:
        """Get PII field definitions with optional filters."""
        fields = []

        for field_def in self._fields.values():
            if category and field_def.category != category:
                continue
            if sensitivity and field_def.sensitivity != sensitivity:
                continue
            if table and field_def.table != table:
                continue
            fields.append(field_def)

        return fields

    def update_field_definition(
        self,
        field_id: UUID,
        sensitivity: SensitivityLevel | None = None,
        masking_type: MaskingType | None = None,
        retention_days: int | None = None,
        requires_consent: bool | None = None,
        consent_types: list[ConsentType] | None = None,
        is_searchable: bool | None = None,
        is_exportable: bool | None = None,
    ) -> PIIFieldDefinition | None:
        """Update a PII field definition."""
        field_def = self._fields.get(field_id)
        if not field_def:
            return None

        if sensitivity is not None:
            field_def.sensitivity = sensitivity
        if masking_type is not None:
            field_def.masking_type = masking_type
        if retention_days is not None:
            field_def.retention_days = retention_days
        if requires_consent is not None:
            field_def.requires_consent = requires_consent
        if consent_types is not None:
            field_def.consent_types = consent_types
        if is_searchable is not None:
            field_def.is_searchable = is_searchable
        if is_exportable is not None:
            field_def.is_exportable = is_exportable

        field_def.updated_at = datetime.now(timezone.utc)
        return field_def

    def delete_field_definition(self, field_id: UUID) -> bool:
        """Delete a PII field definition."""
        if field_id in self._fields:
            del self._fields[field_id]
            return True
        return False

    # Data Subject Management

    def register_subject(
        self,
        external_id: str,
        subject_type: str,
        email: str | None = None,
    ) -> DataSubject:
        """Register a data subject."""
        now = datetime.now(timezone.utc)

        subject = DataSubject(
            id=uuid4(),
            external_id=external_id,
            subject_type=subject_type,
            email=email,
            created_at=now,
            last_accessed_at=None,
            deletion_requested_at=None,
            deletion_completed_at=None,
        )

        self._subjects[subject.id] = subject
        return subject

    def get_subject(self, subject_id: UUID) -> DataSubject | None:
        """Get a data subject by ID."""
        return self._subjects.get(subject_id)

    def get_subject_by_external_id(
        self, external_id: str, subject_type: str
    ) -> DataSubject | None:
        """Get a data subject by external ID."""
        for subject in self._subjects.values():
            if (
                subject.external_id == external_id
                and subject.subject_type == subject_type
            ):
                return subject
        return None

    def get_subjects(
        self,
        subject_type: str | None = None,
        has_deletion_request: bool | None = None,
    ) -> list[DataSubject]:
        """Get data subjects with optional filters."""
        subjects = []

        for subject in self._subjects.values():
            if subject_type and subject.subject_type != subject_type:
                continue
            if has_deletion_request is True and subject.deletion_requested_at is None:
                continue
            if has_deletion_request is False and subject.deletion_requested_at is not None:
                continue
            subjects.append(subject)

        return subjects

    # Consent Management

    def grant_consent(
        self,
        subject_id: UUID,
        consent_type: ConsentType,
        purpose: str,
        source: str,
        version: str,
        ip_address: str | None = None,
        expires_in_days: int | None = None,
    ) -> Consent | None:
        """Grant consent for a data subject."""
        subject = self._subjects.get(subject_id)
        if not subject:
            return None

        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        consent = Consent(
            id=uuid4(),
            subject_id=subject_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            purpose=purpose,
            granted_at=now,
            expires_at=expires_at,
            withdrawn_at=None,
            source=source,
            version=version,
            ip_address=ip_address,
        )

        self._consents[consent.id] = consent
        return consent

    def withdraw_consent(self, consent_id: UUID) -> Consent | None:
        """Withdraw a consent."""
        consent = self._consents.get(consent_id)
        if not consent:
            return None

        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_at = datetime.now(timezone.utc)

        return consent

    def get_consent(self, consent_id: UUID) -> Consent | None:
        """Get a consent by ID."""
        return self._consents.get(consent_id)

    def get_consents(
        self,
        subject_id: UUID | None = None,
        consent_type: ConsentType | None = None,
        status: ConsentStatus | None = None,
    ) -> list[Consent]:
        """Get consents with optional filters."""
        consents = []

        for consent in self._consents.values():
            if subject_id and consent.subject_id != subject_id:
                continue
            if consent_type and consent.consent_type != consent_type:
                continue
            if status and consent.status != status:
                continue
            consents.append(consent)

        return consents

    def check_consent(
        self,
        subject_id: UUID,
        consent_type: ConsentType,
    ) -> bool:
        """Check if a subject has granted consent for a type."""
        now = datetime.now(timezone.utc)

        for consent in self._consents.values():
            if consent.subject_id != subject_id:
                continue
            if consent.consent_type != consent_type:
                continue
            if consent.status != ConsentStatus.GRANTED:
                continue
            if consent.expires_at and consent.expires_at < now:
                continue
            return True

        return False

    def get_missing_consents(
        self, subject_id: UUID, required_types: list[ConsentType]
    ) -> list[ConsentType]:
        """Get list of required consents not yet granted."""
        missing = []

        for consent_type in required_types:
            if not self.check_consent(subject_id, consent_type):
                missing.append(consent_type)

        return missing

    # Data Masking

    def mask_value(
        self,
        value: str,
        field_id: UUID | None = None,
        masking_type: MaskingType | None = None,
    ) -> str:
        """Mask a PII value."""
        if not value:
            return value

        # Get masking type from field definition or use provided
        if field_id and not masking_type:
            field_def = self._fields.get(field_id)
            if field_def:
                masking_type = field_def.masking_type

        if not masking_type:
            masking_type = MaskingType.FULL

        match masking_type:
            case MaskingType.FULL:
                return "***REDACTED***"

            case MaskingType.PARTIAL:
                return self._partial_mask(value)

            case MaskingType.HASH:
                return self._hash_value(value)

            case MaskingType.PSEUDONYMIZE:
                return self._pseudonymize(value)

            case MaskingType.TOKENIZE:
                return self._tokenize(value)

            case MaskingType.TRUNCATE:
                return self._truncate(value)

            case _:
                return "***REDACTED***"

    def _partial_mask(self, value: str) -> str:
        """Apply partial masking."""
        # Email masking
        if "@" in value:
            local, domain = value.split("@", 1)
            if len(local) > 2:
                masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
            else:
                masked_local = "*" * len(local)
            return f"{masked_local}@{domain}"

        # Phone masking - show last 4 digits
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 4:
            return "***-***-" + digits[-4:]

        # General text - show first and last character
        if len(value) > 2:
            return value[0] + "*" * (len(value) - 2) + value[-1]

        return "*" * len(value)

    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA-256."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def _pseudonymize(self, value: str) -> str:
        """Pseudonymize a value (reversible)."""
        if value in self._pseudonym_map:
            return self._pseudonym_map[value]

        pseudonym = f"PSEUDO_{uuid4().hex[:8]}"
        self._pseudonym_map[value] = pseudonym
        return pseudonym

    def _tokenize(self, value: str) -> str:
        """Tokenize a value."""
        if value in self._token_map:
            return self._token_map[value]

        token = f"TOK_{uuid4().hex[:12]}"
        self._token_map[value] = token
        return token

    def _truncate(self, value: str, keep_chars: int = 4) -> str:
        """Truncate a value showing only first N characters."""
        if len(value) <= keep_chars:
            return "*" * len(value)
        return value[:keep_chars] + "..."

    def unmask_pseudonym(self, pseudonym: str) -> str | None:
        """Reverse a pseudonym to get original value."""
        for original, pseudo in self._pseudonym_map.items():
            if pseudo == pseudonym:
                return original
        return None

    def unmask_token(self, token: str) -> str | None:
        """Reverse a token to get original value."""
        for original, tok in self._token_map.items():
            if tok == token:
                return original
        return None

    # PII Detection

    def detect_pii(self, text: str) -> list[dict[str, Any]]:
        """Detect PII in text using patterns."""
        detections = []

        for field_def in self._fields.values():
            if not field_def.detection_pattern:
                continue

            pattern = re.compile(field_def.detection_pattern, re.IGNORECASE)
            matches = pattern.findall(text)

            for match in matches:
                detections.append({
                    "field_id": field_def.id,
                    "field_name": field_def.name,
                    "category": field_def.category.value,
                    "sensitivity": field_def.sensitivity.value,
                    "value": match,
                    "masked_value": self.mask_value(match, field_def.id),
                })

        return detections

    def scan_record(
        self, record: dict[str, Any], table: str
    ) -> list[dict[str, Any]]:
        """Scan a record for PII fields."""
        findings = []

        for column, value in record.items():
            if not isinstance(value, str) or not value:
                continue

            field_def = self.get_field_by_column(table, column)
            if field_def:
                findings.append({
                    "field_id": field_def.id,
                    "column": column,
                    "category": field_def.category.value,
                    "sensitivity": field_def.sensitivity.value,
                    "has_value": True,
                    "requires_consent": field_def.requires_consent,
                })

        return findings

    # Access Logging

    def log_access(
        self,
        subject_id: UUID,
        user_id: UUID,
        field_id: UUID,
        access_type: PIIAccessType,
        purpose: str,
        ip_address: str | None = None,
        data_snapshot: str | None = None,
    ) -> PIIAccessLog | None:
        """Log access to PII data."""
        subject = self._subjects.get(subject_id)
        field_def = self._fields.get(field_id)

        if not subject or not field_def:
            return None

        # Mask the snapshot if provided
        masked_snapshot = None
        if data_snapshot:
            masked_snapshot = self.mask_value(data_snapshot, field_id)

        log = PIIAccessLog(
            id=uuid4(),
            subject_id=subject_id,
            user_id=user_id,
            field_id=field_id,
            access_type=access_type,
            accessed_at=datetime.now(timezone.utc),
            purpose=purpose,
            ip_address=ip_address,
            data_snapshot=masked_snapshot,
        )

        self._access_logs.append(log)

        # Update subject last accessed
        subject.last_accessed_at = log.accessed_at

        return log

    def get_access_logs(
        self,
        subject_id: UUID | None = None,
        user_id: UUID | None = None,
        field_id: UUID | None = None,
        access_type: PIIAccessType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[PIIAccessLog]:
        """Get access logs with filters."""
        logs = []

        for log in self._access_logs:
            if subject_id and log.subject_id != subject_id:
                continue
            if user_id and log.user_id != user_id:
                continue
            if field_id and log.field_id != field_id:
                continue
            if access_type and log.access_type != access_type:
                continue
            if start_date and log.accessed_at < start_date:
                continue
            if end_date and log.accessed_at > end_date:
                continue
            logs.append(log)

        # Sort by most recent
        logs.sort(key=lambda l: l.accessed_at, reverse=True)

        return logs[:limit]

    # Deletion Requests (Right to be Forgotten)

    def request_deletion(
        self,
        subject_id: UUID,
        requested_by: UUID,
        reason: str,
    ) -> DeletionRequest | None:
        """Request deletion of PII data."""
        subject = self._subjects.get(subject_id)
        if not subject:
            return None

        now = datetime.now(timezone.utc)

        # Get affected tables
        affected_tables = set()
        for field_def in self._fields.values():
            affected_tables.add(field_def.table)

        request = DeletionRequest(
            id=uuid4(),
            subject_id=subject_id,
            requested_by=requested_by,
            requested_at=now,
            reason=reason,
            status="pending",
            completed_at=None,
            affected_tables=list(affected_tables),
            deleted_records=0,
            errors=[],
        )

        self._deletion_requests[request.id] = request
        subject.deletion_requested_at = now

        return request

    def process_deletion(
        self, request_id: UUID, deleted_records: int = 0, errors: list[str] | None = None
    ) -> DeletionRequest | None:
        """Mark a deletion request as processing or complete."""
        request = self._deletion_requests.get(request_id)
        if not request:
            return None

        now = datetime.now(timezone.utc)

        if errors:
            request.status = "failed"
            request.errors = errors
        else:
            request.status = "completed"
            request.completed_at = now
            request.deleted_records = deleted_records

            # Update subject
            subject = self._subjects.get(request.subject_id)
            if subject:
                subject.deletion_completed_at = now

        return request

    def get_deletion_request(self, request_id: UUID) -> DeletionRequest | None:
        """Get a deletion request by ID."""
        return self._deletion_requests.get(request_id)

    def get_deletion_requests(
        self,
        subject_id: UUID | None = None,
        status: str | None = None,
    ) -> list[DeletionRequest]:
        """Get deletion requests with filters."""
        requests = []

        for request in self._deletion_requests.values():
            if subject_id and request.subject_id != subject_id:
                continue
            if status and request.status != status:
                continue
            requests.append(request)

        return requests

    def get_pending_deletions(self) -> list[DeletionRequest]:
        """Get pending deletion requests."""
        return self.get_deletion_requests(status="pending")

    # Reporting

    def generate_pii_report(
        self,
        subject_id: UUID,
        generated_by: UUID,
    ) -> PIIReport | None:
        """Generate a PII report for a data subject."""
        subject = self._subjects.get(subject_id)
        if not subject:
            return None

        # Collect field information
        fields = []
        for field_def in self._fields.values():
            fields.append({
                "name": field_def.name,
                "table": field_def.table,
                "column": field_def.column,
                "category": field_def.category.value,
                "sensitivity": field_def.sensitivity.value,
                "retention_days": field_def.retention_days,
            })

        # Get consents
        consents = self.get_consents(subject_id=subject_id)

        # Get access logs
        access_logs = self.get_access_logs(subject_id=subject_id)

        return PIIReport(
            subject_id=subject_id,
            generated_at=datetime.now(timezone.utc),
            generated_by=generated_by,
            fields=fields,
            consents=consents,
            access_logs=access_logs,
        )

    def get_retention_violations(self) -> list[dict[str, Any]]:
        """Get fields with data past retention period."""
        violations = []
        now = datetime.now(timezone.utc)

        for field_def in self._fields.values():
            if not field_def.retention_days:
                continue

            cutoff = now - timedelta(days=field_def.retention_days)

            violations.append({
                "field_id": field_def.id,
                "field_name": field_def.name,
                "table": field_def.table,
                "column": field_def.column,
                "retention_days": field_def.retention_days,
                "cutoff_date": cutoff,
            })

        return violations

    def get_expired_consents(self) -> list[Consent]:
        """Get consents that have expired."""
        now = datetime.now(timezone.utc)
        expired = []

        for consent in self._consents.values():
            if (
                consent.status == ConsentStatus.GRANTED
                and consent.expires_at
                and consent.expires_at < now
            ):
                expired.append(consent)

        return expired

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of PII controls."""
        by_category: dict[str, int] = {}
        by_sensitivity: dict[str, int] = {}

        for field_def in self._fields.values():
            cat = field_def.category.value
            sens = field_def.sensitivity.value
            by_category[cat] = by_category.get(cat, 0) + 1
            by_sensitivity[sens] = by_sensitivity.get(sens, 0) + 1

        return {
            "total_fields": len(self._fields),
            "total_subjects": len(self._subjects),
            "total_consents": len(self._consents),
            "total_access_logs": len(self._access_logs),
            "pending_deletions": len(self.get_pending_deletions()),
            "by_category": by_category,
            "by_sensitivity": by_sensitivity,
            "expired_consents": len(self.get_expired_consents()),
        }

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
from typing import Any, Optional, Awaitable, Iterable, Generic, TypeVar
from uuid import UUID, uuid4
import hashlib
import re
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update, delete as sql_delete, func
from sensei.models.pii import PIIField, DataSubject, Consent, PIIAccessLog, DeletionRequest
from sensei.core.redis import redis_client


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


# Data Subject and other PII classes moved to models/pii.py


@dataclass
class PIIReport:
    """Report of PII data for a subject."""

    subject_id: UUID
    generated_at: datetime
    generated_by: UUID
    fields: list[dict[str, Any]]
    consents: list[Consent]
    access_logs: list[PIIAccessLog]


@dataclass
class MemoryPIIField:
    name: str
    table_name: str
    column_name: str
    category: PIICategory
    sensitivity: SensitivityLevel
    description: str | None
    detection_pattern: str | None
    masking_type: MaskingType
    retention_days: int | None
    requires_consent: bool
    consent_types: list[ConsentType]
    is_searchable: bool
    is_exportable: bool
    id: UUID = field(default_factory=uuid4)
    table: str = ""
    column: str = ""


@dataclass
class MemoryDataSubject:
    external_id: str
    subject_type: str
    email: str | None = None
    last_accessed_at: datetime | None = None
    deletion_requested_at: datetime | None = None
    deletion_completed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class MemoryConsent:
    subject_id: UUID
    consent_type: ConsentType
    status: ConsentStatus
    purpose: str
    granted_at: datetime | None
    expires_at: datetime | None
    withdrawn_at: datetime | None
    source: str
    version: str
    ip_address: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class MemoryAccessLog:
    subject_id: UUID
    user_id: UUID
    field_id: UUID
    access_type: PIIAccessType
    accessed_at: datetime
    purpose: str
    ip_address: str | None = None
    data_snapshot: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class MemoryDeletionRequest:
    subject_id: UUID
    requested_by_id: UUID
    requested_at: datetime
    reason: str
    status: str
    affected_tables: list[str]
    deleted_records: int = 0
    errors: list[str] = field(default_factory=list)
    completed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)


T = TypeVar("T")


class AwaitableValue(Generic[T]):
    def __init__(self, value: T | None = None, coro: Awaitable[T] | None = None) -> None:
        self._value = value
        self._coro = coro

    @staticmethod
    def from_value(value: T) -> "AwaitableValue[T]":
        return AwaitableValue(value=value)

    @staticmethod
    def from_coroutine(coro: Awaitable[T]) -> "AwaitableValue[T]":
        return AwaitableValue(coro=coro)

    def __await__(self):
        if self._coro is not None:
            return self._coro.__await__()

        async def _wrap() -> T:
            return self._value  # type: ignore[return-value]

        return _wrap().__await__()

    def _get_value(self) -> T:
        return self._value  # type: ignore[return-value]

    def __getattr__(self, item: str):
        return getattr(self._get_value(), item)

    def __iter__(self):
        return iter(self._get_value())  # type: ignore[call-overload]

    def __len__(self) -> int:
        return len(self._get_value())  # type: ignore[arg-type]

    def __getitem__(self, item):
        return self._get_value()[item]  # type: ignore[index]

    def __contains__(self, item: object) -> bool:
        return item in self._get_value()  # type: ignore[operator]

    def __bool__(self) -> bool:
        return bool(self._get_value())

    def __eq__(self, other: object) -> bool:
        return self._get_value() == other

    def __str__(self) -> str:
        return str(self._get_value())

    def __repr__(self) -> str:
        return repr(self._get_value())


class AsyncPIIControlsService:
    """Service for managing PII data controls."""

    def __init__(self) -> None:
        """Initialize the PII controls service."""
        self._initialized = False

    async def ensure_initialized(self, db: AsyncSession) -> None:
        """Ensure default PII fields are populated in the database."""
        if self._initialized:
            return
        await self._initialize_default_fields(db)
        self._initialized = True

    async def _get_field_definitions_cached(self, db: AsyncSession) -> dict[UUID, PIIField]:
        """Get all field definitions, using Redis cache if available."""
        cache_key = "pii:fields:all"
        cached = await redis_client.get(cache_key)
        if cached:
            # Note: This is a simplified cache. In a real app, we'd handle serialization of UUIDs/datetimes better.
            # For this refactor, we'll re-fetch from DB to ensure correctness if cache is messy.
            pass
        
        result = await db.execute(select(PIIField))
        fields = result.scalars().all()
        return {f.id: f for f in fields}

    async def _initialize_default_fields(self, db: AsyncSession) -> None:
        """Initialize default PII field definitions."""
        # User PII fields
        await self._add_default_field(
            db,
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

        await self._add_default_field(
            db,
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

        await self._add_default_field(
            db,
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
        await self._add_default_field(
            db,
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

        await self._add_default_field(
            db,
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
        await self._add_default_field(
            db,
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
        await self._add_default_field(
            db,
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

        await self._add_default_field(
            db,
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

    async def _add_default_field(
        self,
        db: AsyncSession,
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
    ) -> PIIField:
        """Add a default PII field definition if it doesn't exist."""
        # Check if already exists
        stmt = select(PIIField).where(PIIField.table_name == table, PIIField.column_name == column)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        field_def = PIIField(
            name=name,
            table_name=table,
            column_name=column,
            category=category.value,
            sensitivity=sensitivity.value,
            description=description,
            detection_pattern=detection_pattern,
            masking_type=masking_type.value,
            retention_days=retention_days,
            requires_consent=requires_consent,
            consent_types=[ct.value for ct in consent_types],
            is_searchable=sensitivity not in [SensitivityLevel.CRITICAL],
            is_exportable=True,
        )

        db.add(field_def)
        await db.commit()
        await db.refresh(field_def)
        return field_def

    async def create_field_definition(
        self,
        db: AsyncSession,
        name: str,
        table_name: str,
        column_name: str,
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
    ) -> PIIField:
        """Create a new PII field definition."""
        field_def = PIIField(
            name=name,
            table_name=table_name,
            column_name=column_name,
            category=category.value,
            sensitivity=sensitivity.value,
            description=description,
            detection_pattern=detection_pattern,
            masking_type=masking_type.value,
            retention_days=retention_days,
            requires_consent=requires_consent,
            consent_types=[ct.value for ct in (consent_types or [])],
            is_searchable=is_searchable,
            is_exportable=is_exportable,
        )

        db.add(field_def)
        await db.commit()
        await db.refresh(field_def)
        return field_def

    async def get_field_definition(self, field_id: UUID, db: AsyncSession) -> PIIField | None:
        """Get a PII field definition by ID."""
        return await db.get(PIIField, field_id)

    async def get_field_by_column(
        self, table_name: str, column_name: str, db: AsyncSession
    ) -> PIIField | None:
        """Get a PII field definition by table and column."""
        stmt = select(PIIField).where(PIIField.table_name == table_name, PIIField.column_name == column_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_field_definitions(
        self,
        db: AsyncSession,
        category: PIICategory | None = None,
        sensitivity: SensitivityLevel | None = None,
        table_name: str | None = None,
    ) -> list[PIIField]:
        """Get PII field definitions with optional filters."""
        stmt = select(PIIField)

        if category:
            stmt = stmt.where(PIIField.category == category.value)
        if sensitivity:
            stmt = stmt.where(PIIField.sensitivity == sensitivity.value)
        if table_name:
            stmt = stmt.where(PIIField.table_name == table_name)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_field_definition(
        self,
        db: AsyncSession,
        field_id: UUID,
        sensitivity: SensitivityLevel | None = None,
        masking_type: MaskingType | None = None,
        retention_days: int | None = None,
        requires_consent: bool | None = None,
        consent_types: list[ConsentType] | None = None,
        is_searchable: bool | None = None,
        is_exportable: bool | None = None,
    ) -> PIIField | None:
        """Update a PII field definition."""
        field_def = await db.get(PIIField, field_id)
        if not field_def:
            return None

        if sensitivity is not None:
            field_def.sensitivity = sensitivity.value
        if masking_type is not None:
            field_def.masking_type = masking_type.value
        if retention_days is not None:
            field_def.retention_days = retention_days
        if requires_consent is not None:
            field_def.requires_consent = requires_consent
        if consent_types is not None:
            field_def.consent_types = [ct.value for ct in consent_types]
        if is_searchable is not None:
            field_def.is_searchable = is_searchable
        if is_exportable is not None:
            field_def.is_exportable = is_exportable

        await db.commit()
        await db.refresh(field_def)
        return field_def

    async def delete_field_definition(self, db: AsyncSession, field_id: UUID) -> bool:
        """Delete a PII field definition."""
        field_def = await db.get(PIIField, field_id)
        if field_def:
            await db.delete(field_def)
            await db.commit()
            return True
        return False

    # Data Subject Management

    async def register_subject(
        self,
        db: AsyncSession,
        external_id: str,
        subject_type: str,
        email: str | None = None,
    ) -> DataSubject:
        """Register a data subject."""
        subject = DataSubject(
            external_id=external_id,
            subject_type=subject_type,
            email=email,
        )

        db.add(subject)
        await db.commit()
        await db.refresh(subject)
        return subject

    async def get_subject(self, db: AsyncSession, subject_id: UUID) -> DataSubject | None:
        """Get a data subject by ID."""
        return await db.get(DataSubject, subject_id)

    async def get_subject_by_external_id(
        self, db: AsyncSession, external_id: str, subject_type: str
    ) -> DataSubject | None:
        """Get a data subject by external ID."""
        stmt = select(DataSubject).where(
            DataSubject.external_id == external_id,
            DataSubject.subject_type == subject_type
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subjects(
        self,
        db: AsyncSession,
        subject_type: str | None = None,
        has_deletion_request: bool | None = None,
    ) -> list[DataSubject]:
        """Get data subjects with optional filters."""
        stmt = select(DataSubject)

        if subject_type:
            stmt = stmt.where(DataSubject.subject_type == subject_type)
        if has_deletion_request is True:
            stmt = stmt.where(DataSubject.deletion_requested_at.is_not(None))
        elif has_deletion_request is False:
            stmt = stmt.where(DataSubject.deletion_requested_at.is_(None))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Consent Management

    async def grant_consent(
        self,
        db: AsyncSession,
        subject_id: UUID,
        consent_type: ConsentType,
        purpose: str,
        source: str,
        version: str,
        ip_address: str | None = None,
        expires_in_days: int | None = None,
    ) -> Consent | None:
        """Grant consent for a data subject."""
        subject = await db.get(DataSubject, subject_id)
        if not subject:
            return None

        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)

        consent = Consent(
            subject_id=subject_id,
            consent_type=consent_type.value,
            status=ConsentStatus.GRANTED.value,
            purpose=purpose,
            granted_at=now,
            expires_at=expires_at,
            source=source,
            version=version,
            ip_address=ip_address,
        )

        db.add(consent)
        await db.commit()
        await db.refresh(consent)
        return consent

    async def withdraw_consent(self, db: AsyncSession, consent_id: UUID) -> Consent | None:
        """Withdraw a consent."""
        consent = await db.get(Consent, consent_id)
        if not consent:
            return None

        consent.status = ConsentStatus.WITHDRAWN.value
        consent.withdrawn_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(consent)
        return consent

    async def get_consent(self, db: AsyncSession, consent_id: UUID) -> Consent | None:
        """Get a consent by ID."""
        return await db.get(Consent, consent_id)

    async def get_consents(
        self,
        db: AsyncSession,
        subject_id: UUID | None = None,
        consent_type: ConsentType | None = None,
        status: ConsentStatus | None = None,
    ) -> list[Consent]:
        """Get consents with optional filters."""
        stmt = select(Consent)

        if subject_id:
            stmt = stmt.where(Consent.subject_id == subject_id)
        if consent_type:
            stmt = stmt.where(Consent.consent_type == consent_type.value)
        if status:
            stmt = stmt.where(Consent.status == status.value)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def check_consent(
        self,
        db: AsyncSession,
        subject_id: UUID,
        consent_type: ConsentType,
    ) -> bool:
        """Check if a subject has granted consent for a type."""
        now = datetime.now(timezone.utc)
        stmt = select(Consent).where(
            Consent.subject_id == subject_id,
            Consent.consent_type == consent_type.value,
            Consent.status == ConsentStatus.GRANTED.value
        )
        result = await db.execute(stmt)
        consents = result.scalars().all()
        
        for consent in consents:
            if consent.expires_at and consent.expires_at < now:
                continue
            return True

        return False

    async def get_missing_consents(
        self, db: AsyncSession, subject_id: UUID, required_types: list[ConsentType]
    ) -> list[ConsentType]:
        """Get list of required consents not yet granted."""
        missing = []

        for consent_type in required_types:
            if not await self.check_consent(db, subject_id, consent_type):
                missing.append(consent_type)

        return missing

    # Data Masking

    async def mask_value(
        self,
        value: str,
        field_id: UUID | None = None,
        masking_type: MaskingType | None = None,
        db: AsyncSession | None = None,
    ) -> str:
        """Mask a PII value."""
        if not value:
            return value

        # Get masking type from field definition or use provided
        if field_id and not masking_type and db:
            stmt = select(PIIField).where(PIIField.id == field_id)
            result = await db.execute(stmt)
            field_def = result.scalar_one_or_none()
            if field_def:
                masking_type = MaskingType(field_def.masking_type)

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
                return await self._pseudonymize(value)

            case MaskingType.TOKENIZE:
                return await self._tokenize(value)

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

    async def _pseudonymize(self, value: str) -> str:
        """Pseudonymize a value (reversible, stored in Redis)."""
        cache_key = f"pii:pseudonym:{value}"
        existing = await redis_client.get(cache_key)
        if existing:
            return existing

        pseudonym = f"PSEUDO_{uuid4().hex[:8]}"
        # Store both ways for reversibility
        await redis_client.set(cache_key, pseudonym)
        await redis_client.set(f"pii:pseudonym_rev:{pseudonym}", value)
        return pseudonym

    async def _tokenize(self, value: str) -> str:
        """Tokenize a value (stored in Redis)."""
        cache_key = f"pii:token:{value}"
        existing = await redis_client.get(cache_key)
        if existing:
            return existing

        token = f"TOK_{uuid4().hex[:12]}"
        await redis_client.set(cache_key, token)
        await redis_client.set(f"pii:token_rev:{token}", value)
        return token

    def _truncate(self, value: str, keep_chars: int = 4) -> str:
        """Truncate a value showing only first N characters."""
        if len(value) <= keep_chars:
            return "*" * len(value)
        return value[:keep_chars] + "..."

    async def unmask_pseudonym(self, pseudonym: str) -> str | None:
        """Reverse a pseudonym to get original value."""
        return await redis_client.get(f"pii:pseudonym_rev:{pseudonym}")

    async def unmask_token(self, token: str) -> str | None:
        """Reverse a token to get original value."""
        return await redis_client.get(f"pii:token_rev:{token}")

    # PII Detection

    async def detect_pii(self, text: str, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect PII in text using patterns."""
        detections = []
        fields = await self._get_field_definitions_cached(db)

        for field_def in fields.values():
            if not field_def.detection_pattern:
                continue

            pattern = re.compile(field_def.detection_pattern, re.IGNORECASE)
            matches = pattern.findall(text)

            for match in matches:
                detections.append({
                    "field_id": field_def.id,
                    "field_name": field_def.name,
                    "category": field_def.category,
                    "sensitivity": field_def.sensitivity,
                    "value": match,
                    "masked_value": await self.mask_value(match, field_def.id, db=db),
                })

        return detections

    async def scan_record(
        self, record: dict[str, Any], table_name: str, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Scan a record for PII fields."""
        findings = []

        for column, value in record.items():
            if not isinstance(value, str) or not value:
                continue

            field_def = await self.get_field_by_column(table_name, column, db)
            if field_def:
                findings.append({
                    "field_id": field_def.id,
                    "column": column,
                    "category": field_def.category,
                    "sensitivity": field_def.sensitivity,
                    "has_value": True,
                    "requires_consent": field_def.requires_consent,
                })

        return findings

    # Access Logging

    async def log_access(
        self,
        db: AsyncSession,
        subject_id: UUID,
        user_id: UUID,
        field_id: UUID,
        access_type: PIIAccessType,
        purpose: str,
        ip_address: str | None = None,
        data_snapshot: str | None = None,
    ) -> PIIAccessLog | None:
        """Log access to PII data."""
        subject = await db.get(DataSubject, subject_id)
        field_def = await db.get(PIIField, field_id)

        if not subject or not field_def:
            return None

        # Mask the snapshot if provided
        masked_snapshot = None
        if data_snapshot:
            masked_snapshot = await self.mask_value(data_snapshot, field_id, db=db)

        log = PIIAccessLog(
            subject_id=subject_id,
            user_id=user_id,
            field_id=field_id,
            access_type=access_type.value,
            accessed_at=datetime.now(timezone.utc),
            purpose=purpose,
            ip_address=ip_address,
            data_snapshot=masked_snapshot,
        )

        db.add(log)
        # Update subject last accessed
        subject.last_accessed_at = log.accessed_at
        
        await db.commit()
        await db.refresh(log)

        return log

    async def get_access_logs(
        self,
        db: AsyncSession,
        subject_id: UUID | None = None,
        user_id: UUID | None = None,
        field_id: UUID | None = None,
        access_type: PIIAccessType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[PIIAccessLog]:
        """Get access logs with filters."""
        stmt = select(PIIAccessLog)

        if subject_id:
            stmt = stmt.where(PIIAccessLog.subject_id == subject_id)
        if user_id:
            stmt = stmt.where(PIIAccessLog.user_id == user_id)
        if field_id:
            stmt = stmt.where(PIIAccessLog.field_id == field_id)
        if access_type:
            stmt = stmt.where(PIIAccessLog.access_type == access_type.value)
        if start_date:
            stmt = stmt.where(PIIAccessLog.accessed_at >= start_date)
        if end_date:
            stmt = stmt.where(PIIAccessLog.accessed_at <= end_date)

        stmt = stmt.order_by(PIIAccessLog.accessed_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Deletion Requests (Right to be Forgotten)

    async def request_deletion(
        self,
        db: AsyncSession,
        subject_id: UUID,
        requested_by_id: UUID,
        reason: str,
    ) -> DeletionRequest | None:
        """Request deletion of PII data."""
        subject = await db.get(DataSubject, subject_id)
        if not subject:
            return None

        now = datetime.now(timezone.utc)

        # Get affected tables
        fields = await self._get_field_definitions_cached(db)
        affected_tables = list(set(f.table_name for f in fields.values()))

        request = DeletionRequest(
            subject_id=subject_id,
            requested_by_id=requested_by_id,
            requested_at=now,
            reason=reason,
            status="pending",
            affected_tables=affected_tables,
        )

        db.add(request)
        subject.deletion_requested_at = now
        
        await db.commit()
        await db.refresh(request)

        return request

    async def process_deletion(
        self, db: AsyncSession, request_id: UUID, deleted_records: int = 0, errors: list[str] | None = None
    ) -> DeletionRequest | None:
        """Mark a deletion request as processing or complete."""
        request = await db.get(DeletionRequest, request_id)
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
            subject = await db.get(DataSubject, request.subject_id)
            if subject:
                subject.deletion_completed_at = now

        await db.commit()
        await db.refresh(request)
        return request

    async def get_deletion_request(self, db: AsyncSession, request_id: UUID) -> DeletionRequest | None:
        """Get a deletion request by ID."""
        return await db.get(DeletionRequest, request_id)

    async def get_deletion_requests(
        self,
        db: AsyncSession,
        subject_id: UUID | None = None,
        status: str | None = None,
    ) -> list[DeletionRequest]:
        """Get deletion requests with filters."""
        stmt = select(DeletionRequest)

        if subject_id:
            stmt = stmt.where(DeletionRequest.subject_id == subject_id)
        if status:
            stmt = stmt.where(DeletionRequest.status == status)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_deletions(self, db: AsyncSession) -> list[DeletionRequest]:
        """Get pending deletion requests."""
        return await self.get_deletion_requests(db, status="pending")

    # Reporting

    async def generate_pii_report(
        self,
        db: AsyncSession,
        subject_id: UUID,
        generated_by_id: UUID,
    ) -> PIIReport | None:
        """Generate a PII report for a data subject."""
        subject = await db.get(DataSubject, subject_id)
        if not subject:
            return None

        # Collect field information
        fields_data = []
        fields = await self.get_field_definitions(db)
        for field_def in fields:
            fields_data.append({
                "name": field_def.name,
                "table": field_def.table_name,
                "column": field_def.column_name,
                "category": field_def.category,
                "sensitivity": field_def.sensitivity,
                "retention_days": field_def.retention_days,
            })

        # Get consents
        consents = await self.get_consents(db, subject_id=subject_id)

        # Get access logs
        access_logs = await self.get_access_logs(db, subject_id=subject_id)

        return PIIReport(
            subject_id=subject_id,
            generated_at=datetime.now(timezone.utc),
            generated_by=generated_by_id,
            fields=fields_data,
            consents=consents,
            access_logs=access_logs,
        )

    async def get_retention_violations(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Get fields with data past retention period."""
        violations = []
        now = datetime.now(timezone.utc)

        fields = await self.get_field_definitions(db)
        for field_def in fields:
            if not field_def.retention_days:
                continue

            cutoff = now - timedelta(days=field_def.retention_days)

            violations.append({
                "field_id": field_def.id,
                "field_name": field_def.name,
                "table": field_def.table_name,
                "column": field_def.column_name,
                "retention_days": field_def.retention_days,
                "cutoff_date": cutoff,
            })

        return violations

    async def get_expired_consents(self, db: AsyncSession) -> list[Consent]:
        """Get consents that have expired."""
        now = datetime.now(timezone.utc)
        stmt = select(Consent).where(
            Consent.status == ConsentStatus.GRANTED.value,
            Consent.expires_at.is_not(None),
            Consent.expires_at < now
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Get a summary of PII controls."""
        fields = await self.get_field_definitions(db)
        
        by_category: dict[str, int] = {}
        by_sensitivity: dict[str, int] = {}

        for field_def in fields:
            cat = field_def.category
            sens = field_def.sensitivity
            by_category[cat] = by_category.get(cat, 0) + 1
            by_sensitivity[sens] = by_sensitivity.get(sens, 0) + 1

        # Counts
        stmt_subjects = select(func.count(DataSubject.id))
        stmt_consents = select(func.count(Consent.id))
        stmt_logs = select(func.count(PIIAccessLog.id))
        
        subjects_count = (await db.execute(stmt_subjects)).scalar() or 0
        consents_count = (await db.execute(stmt_consents)).scalar() or 0
        logs_count = (await db.execute(stmt_logs)).scalar() or 0
        
        pending_deletions = await self.get_pending_deletions(db)
        expired_consents = await self.get_expired_consents(db)

        return {
            "total_fields": len(fields),
            "total_subjects": subjects_count,
            "total_consents": consents_count,
            "total_access_logs": logs_count,
            "pending_deletions": len(pending_deletions),
            "by_category": by_category,
            "by_sensitivity": by_sensitivity,
            "expired_consents": len(expired_consents),
        }


class PIIControlsService:
    """In-memory PII Controls service with awaitable return values."""

    def __init__(self) -> None:
        self._async = AsyncPIIControlsService()
        self._fields: dict[UUID, MemoryPIIField] = {}
        self._subjects: dict[UUID, MemoryDataSubject] = {}
        self._consents: dict[UUID, MemoryConsent] = {}
        self._access_logs: dict[UUID, MemoryAccessLog] = {}
        self._deletion_requests: dict[UUID, MemoryDeletionRequest] = {}
        self._pseudonym_map: dict[str, str] = {}
        self._pseudonym_rev: dict[str, str] = {}
        self._token_map: dict[str, str] = {}
        self._token_rev: dict[str, str] = {}
        self._seed_default_fields()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _wrap(self, value: T) -> AwaitableValue[T]:
        return value  # type: ignore[return-value]

    def _wrap_coro(self, coro: Awaitable[T]) -> AwaitableValue[T]:
        return AwaitableValue.from_coroutine(coro)

    def _seed_default_fields(self) -> None:
        self._create_field_definition_sync(
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
            retention_days=365,
        )
        self._create_field_definition_sync(
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
        self._create_field_definition_sync(
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
        self._create_field_definition_sync(
            name="Audit Log IP",
            table="audit_log",
            column="ip_address",
            category=PIICategory.IP_ADDRESS,
            sensitivity=SensitivityLevel.LOW,
            description="IP address",
            detection_pattern=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            masking_type=MaskingType.PARTIAL,
            requires_consent=False,
            consent_types=[],
        )

    def _normalize_field(self, field: MemoryPIIField) -> MemoryPIIField:
        field.table = field.table_name
        field.column = field.column_name
        return field

    def _create_field_definition_sync(
        self,
        *,
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
    ) -> MemoryPIIField:
        field_def = MemoryPIIField(
            name=name,
            table_name=table,
            column_name=column,
            category=category,
            sensitivity=sensitivity,
            description=description,
            detection_pattern=detection_pattern,
            masking_type=masking_type,
            retention_days=retention_days,
            requires_consent=requires_consent,
            consent_types=list(consent_types or []),
            is_searchable=is_searchable,
            is_exportable=is_exportable,
        )
        self._normalize_field(field_def)
        self._fields[field_def.id] = field_def
        return field_def

    def _find_field_by_column(self, table: str, column: str) -> MemoryPIIField | None:
        for field_def in self._fields.values():
            table_name = getattr(field_def, "table_name", None)
            column_name = getattr(field_def, "column_name", None)
            table_alias = getattr(field_def, "table", None)
            column_alias = getattr(field_def, "column", None)
            if (table_name == table or table_alias == table) and (column_name == column or column_alias == column):
                return field_def
        for field_def in self._fields.values():
            column_name = getattr(field_def, "column_name", None)
            column_alias = getattr(field_def, "column", None)
            if column_name == column or column_alias == column:
                return field_def
        return None

    def _resolve_category(self, value: PIICategory | str) -> str:
        return value.value if isinstance(value, PIICategory) else value

    def _resolve_sensitivity(self, value: SensitivityLevel | str) -> str:
        return value.value if isinstance(value, SensitivityLevel) else value

    def _resolve_masking(self, value: MaskingType | str) -> MaskingType:
        return value if isinstance(value, MaskingType) else MaskingType(value)

    # ------------------------------------------------------------------
    # Field definitions
    # ------------------------------------------------------------------

    def create_field_definition(
        self,
        name: str,
        table: str | None = None,
        column: str | None = None,
        category: PIICategory | None = None,
        sensitivity: SensitivityLevel | None = None,
        description: str | None = None,
        detection_pattern: str | None = None,
        masking_type: MaskingType = MaskingType.FULL,
        retention_days: int | None = None,
        requires_consent: bool = True,
        consent_types: list[ConsentType] | None = None,
        is_searchable: bool = True,
        is_exportable: bool = True,
        db: AsyncSession | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
    ) -> AwaitableValue[MemoryPIIField | PIIField]:
        if db is not None:
            return self._wrap_coro(
                self._async.create_field_definition(
                    db,
                    name=name,
                    table_name=table_name or table or "",
                    column_name=column_name or column or "",
                    category=category or PIICategory.CUSTOM,
                    sensitivity=sensitivity or SensitivityLevel.LOW,
                    description=description or "",
                    detection_pattern=detection_pattern,
                    masking_type=masking_type,
                    retention_days=retention_days,
                    requires_consent=requires_consent,
                    consent_types=consent_types,
                    is_searchable=is_searchable,
                    is_exportable=is_exportable,
                )
            )

        field_def = self._create_field_definition_sync(
            name=name,
            table=table_name or table or "",
            column=column_name or column or "",
            category=category or PIICategory.CUSTOM,
            sensitivity=sensitivity or SensitivityLevel.LOW,
            description=description or "",
            detection_pattern=detection_pattern,
            masking_type=masking_type,
            retention_days=retention_days,
            requires_consent=requires_consent,
            consent_types=consent_types,
            is_searchable=is_searchable,
            is_exportable=is_exportable,
        )
        return self._wrap(field_def)

    def get_field_definition(self, field_id: UUID, db: AsyncSession | None = None) -> AwaitableValue[MemoryPIIField | PIIField | None]:
        if db is not None:
            return self._wrap_coro(self._async.get_field_definition(field_id, db))
        return self._wrap(self._fields.get(field_id))

    def get_field_by_column(
        self,
        table: str,
        column: str,
        db: AsyncSession | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
    ) -> AwaitableValue[MemoryPIIField | PIIField | None]:
        if db is not None:
            return self._wrap_coro(self._async.get_field_by_column(table_name or table, column_name or column, db))
        return self._wrap(self._find_field_by_column(table_name or table, column_name or column))

    def get_field_definitions(
        self,
        category: PIICategory | None = None,
        sensitivity: SensitivityLevel | None = None,
        table: str | None = None,
        db: AsyncSession | None = None,
        table_name: str | None = None,
    ) -> AwaitableValue[list[MemoryPIIField | PIIField]]:
        if db is not None:
            return self._wrap_coro(self._async.get_field_definitions(db, category=category, sensitivity=sensitivity, table_name=table_name or table))  # type: ignore[arg-type]

        results = list(self._fields.values())
        if category:
            results = [f for f in results if f.category == category]
        if sensitivity:
            results = [f for f in results if f.sensitivity == sensitivity]
        if table_name or table:
            target = table_name or table
            results = [f for f in results if f.table == target]
        return self._wrap(results)  # type: ignore[arg-type]

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
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryPIIField | PIIField | None]:
        if db is not None:
            return self._wrap_coro(
                self._async.update_field_definition(
                    db,
                    field_id,
                    sensitivity=sensitivity,
                    masking_type=masking_type,
                    retention_days=retention_days,
                    requires_consent=requires_consent,
                    consent_types=consent_types,
                    is_searchable=is_searchable,
                    is_exportable=is_exportable,
                )
            )

        field_def = self._fields.get(field_id)
        if not field_def:
            return self._wrap(None)
        if sensitivity is not None:
            field_def.sensitivity = sensitivity
        if masking_type is not None:
            field_def.masking_type = masking_type
        if retention_days is not None:
            field_def.retention_days = retention_days
        if requires_consent is not None:
            field_def.requires_consent = requires_consent
        if consent_types is not None:
            field_def.consent_types = list(consent_types)
        if is_searchable is not None:
            field_def.is_searchable = is_searchable
        if is_exportable is not None:
            field_def.is_exportable = is_exportable
        return self._wrap(field_def)

    def delete_field_definition(self, field_id: UUID, db: AsyncSession | None = None) -> AwaitableValue[bool]:
        if db is not None:
            return self._wrap_coro(self._async.delete_field_definition(db, field_id))
        if field_id in self._fields:
            del self._fields[field_id]
            return self._wrap(True)
        return self._wrap(False)

    # ------------------------------------------------------------------
    # Subjects
    # ------------------------------------------------------------------

    def register_subject(
        self,
        external_id: str,
        subject_type: str,
        email: str | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryDataSubject | DataSubject]:
        if db is not None:
            return self._wrap_coro(self._async.register_subject(db, external_id=external_id, subject_type=subject_type, email=email))

        subject = MemoryDataSubject(
            external_id=external_id,
            subject_type=subject_type,
            email=email,
            last_accessed_at=None,
            deletion_requested_at=None,
            deletion_completed_at=None,
        )
        self._subjects[subject.id] = subject
        return self._wrap(subject)

    def get_subject(self, subject_id: UUID, db: AsyncSession | None = None) -> AwaitableValue[MemoryDataSubject | DataSubject | None]:
        if db is not None:
            return self._wrap_coro(self._async.get_subject(db, subject_id))
        return self._wrap(self._subjects.get(subject_id))

    def get_subject_by_external_id(
        self,
        external_id: str,
        subject_type: str,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryDataSubject | DataSubject | None]:
        if db is not None:
            return self._wrap_coro(self._async.get_subject_by_external_id(db, external_id, subject_type))
        for subject in self._subjects.values():
            if subject.external_id == external_id and subject.subject_type == subject_type:
                return self._wrap(subject)
        return self._wrap(None)

    def get_subjects(
        self,
        subject_type: str | None = None,
        has_deletion_request: bool | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[list[MemoryDataSubject | DataSubject]]:
        if db is not None:
            return self._wrap_coro(self._async.get_subjects(db, subject_type=subject_type, has_deletion_request=has_deletion_request))  # type: ignore[arg-type]

        subjects = list(self._subjects.values())
        if subject_type:
            subjects = [s for s in subjects if s.subject_type == subject_type]
        if has_deletion_request is True:
            subjects = [s for s in subjects if s.deletion_requested_at is not None]
        elif has_deletion_request is False:
            subjects = [s for s in subjects if s.deletion_requested_at is None]
        return self._wrap(subjects)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------

    def grant_consent(
        self,
        subject_id: UUID,
        consent_type: ConsentType,
        purpose: str,
        source: str,
        version: str,
        ip_address: str | None = None,
        expires_in_days: int | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryConsent | Consent | None]:
        if db is not None:
            return self._wrap_coro(
                self._async.grant_consent(
                    db,
                    subject_id,
                    consent_type,
                    purpose,
                    source,
                    version,
                    ip_address=ip_address,
                    expires_in_days=expires_in_days,
                )
            )

        subject = self._subjects.get(subject_id)
        if not subject:
            return self._wrap(None)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None
        consent = MemoryConsent(
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
        return self._wrap(consent)

    def withdraw_consent(self, consent_id: UUID, db: AsyncSession | None = None) -> AwaitableValue[MemoryConsent | Consent | None]:
        if db is not None:
            return self._wrap_coro(self._async.withdraw_consent(db, consent_id))

        consent = self._consents.get(consent_id)
        if not consent:
            return self._wrap(None)
        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_at = datetime.now(timezone.utc)
        return self._wrap(consent)

    def check_consent(
        self,
        subject_id: UUID,
        consent_type: ConsentType,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[bool]:
        if db is not None:
            return self._wrap_coro(self._async.check_consent(db, subject_id, consent_type))
        for consent in self._consents.values():
            if consent.subject_id == subject_id and consent.consent_type == consent_type and consent.status == ConsentStatus.GRANTED:
                return self._wrap(True)
        return self._wrap(False)

    def get_missing_consents(
        self,
        subject_id: UUID,
        required_consents: Iterable[ConsentType],
        db: AsyncSession | None = None,
    ) -> AwaitableValue[list[ConsentType]]:
        if db is not None:
            return self._wrap_coro(self._async.get_missing_consents(db, subject_id, list(required_consents)))

        granted = {c.consent_type for c in self._consents.values() if c.subject_id == subject_id and c.status == ConsentStatus.GRANTED}
        missing = [c for c in required_consents if c not in granted]
        return self._wrap(missing)

    def get_consents(
        self,
        subject_id: UUID | None = None,
        consent_type: ConsentType | None = None,
        status: ConsentStatus | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[list[MemoryConsent | Consent]]:
        if db is not None:
            return self._wrap_coro(self._async.get_consents(db, subject_id=subject_id, consent_type=consent_type, status=status))  # type: ignore[arg-type]

        consents = list(self._consents.values())
        if subject_id:
            consents = [c for c in consents if c.subject_id == subject_id]
        if consent_type:
            consents = [c for c in consents if c.consent_type == consent_type]
        if status:
            consents = [c for c in consents if c.status == status]
        return self._wrap(consents)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Masking
    # ------------------------------------------------------------------

    def mask_value(
        self,
        value: str,
        field_id: UUID | None = None,
        masking_type: MaskingType | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[str]:
        if db is not None:
            return self._wrap_coro(self._async.mask_value(value, field_id=field_id, masking_type=masking_type, db=db))

        if value == "":
            return self._wrap("")

        resolved_masking = masking_type
        if field_id:
            field_def = self._fields.get(field_id)
            if field_def is None:
                return self._wrap(value)
            resolved_masking = field_def.masking_type  # type: ignore[assignment]

        resolved_masking = self._resolve_masking(resolved_masking or MaskingType.FULL)

        if resolved_masking == MaskingType.FULL:
            return self._wrap("***REDACTED***")
        if resolved_masking == MaskingType.PARTIAL:
            if "@" in value:
                local, domain = value.split("@", 1)
                masked_local = (local[:1] + "***") if local else "***"
                return self._wrap(f"{masked_local}@{domain}")
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return self._wrap("*" * (len(digits) - 4) + digits[-4:])
            return self._wrap("***")
        if resolved_masking == MaskingType.HASH:
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
            return self._wrap(digest)
        if resolved_masking == MaskingType.PSEUDONYMIZE:
            if value in self._pseudonym_map:
                return self._wrap(self._pseudonym_map[value])
            pseudonym = f"PSEUDO_{hashlib.md5(value.encode('utf-8')).hexdigest()[:8]}"
            self._pseudonym_map[value] = pseudonym
            self._pseudonym_rev[pseudonym] = value
            return self._wrap(pseudonym)
        if resolved_masking == MaskingType.TOKENIZE:
            if value in self._token_map:
                return self._wrap(self._token_map[value])
            token = f"TOK_{uuid4().hex[:10]}"
            self._token_map[value] = token
            self._token_rev[token] = value
            return self._wrap(token)
        if resolved_masking == MaskingType.TRUNCATE:
            if len(value) <= 4:
                return self._wrap(value)
            return self._wrap(value[:4] + "...")
        return self._wrap(value)

    def unmask_pseudonym(self, pseudonym: str, db: AsyncSession | None = None) -> AwaitableValue[str | None]:
        if db is not None:
            return self._wrap_coro(self._async.unmask_pseudonym(pseudonym))
        return self._wrap(self._pseudonym_rev.get(pseudonym))

    def unmask_token(self, token: str, db: AsyncSession | None = None) -> AwaitableValue[str | None]:
        if db is not None:
            return self._wrap_coro(self._async.unmask_token(token))
        return self._wrap(self._token_rev.get(token))

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_pii(self, text: str, db: AsyncSession | None = None) -> AwaitableValue[list[dict[str, Any]]]:
        if db is not None:
            return self._wrap_coro(self._async.detect_pii(text, db))

        detections: list[dict[str, Any]] = []
        for field_def in self._fields.values():
            if not field_def.detection_pattern:
                continue
            for match in re.findall(field_def.detection_pattern, text):
                match_value = match if isinstance(match, str) else match[0]
                detections.append({
                    "category": self._resolve_category(field_def.category),
                    "match": match_value,
                    "field_id": field_def.id,
                })
        return self._wrap(detections)

    def scan_record(self, record: dict[str, Any], table: str, db: AsyncSession | None = None) -> AwaitableValue[list[dict[str, Any]]]:
        if db is not None:
            return self._wrap_coro(self._async.scan_record(record, table, db))

        findings: list[dict[str, Any]] = []
        for field_def in self._fields.values():
            if field_def.table != table:
                continue
            if field_def.column not in record:
                continue
            value = record.get(field_def.column)
            if value is None:
                continue
            findings.append({
                "field_id": field_def.id,
                "table": table,
                "column": field_def.column,
                "category": self._resolve_category(field_def.category),
                "sensitivity": self._resolve_sensitivity(field_def.sensitivity),
                "value": value,
            })
        return self._wrap(findings)

    # ------------------------------------------------------------------
    # Access logging
    # ------------------------------------------------------------------

    def log_access(
        self,
        subject_id: UUID,
        user_id: UUID,
        field_id: UUID,
        access_type: PIIAccessType,
        purpose: str,
        ip_address: str | None = None,
        data_snapshot: str | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryAccessLog | PIIAccessLog | None]:
        if db is not None:
            return self._wrap_coro(
                self._async.log_access(
                    db,
                    subject_id,
                    user_id,
                    field_id,
                    access_type,
                    purpose,
                    ip_address=ip_address,
                    data_snapshot=data_snapshot,
                )
            )

        subject = self._subjects.get(subject_id)
        if not subject:
            return self._wrap(None)

        log = MemoryAccessLog(
            subject_id=subject_id,
            user_id=user_id,
            field_id=field_id,
            access_type=access_type,
            accessed_at=datetime.now(timezone.utc),
            purpose=purpose,
            ip_address=ip_address,
            data_snapshot=data_snapshot,
        )
        self._access_logs[log.id] = log
        subject.last_accessed_at = datetime.now(timezone.utc)
        return self._wrap(log)

    def get_access_logs(
        self,
        subject_id: UUID | None = None,
        access_type: PIIAccessType | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[list[MemoryAccessLog | PIIAccessLog]]:
        if db is not None:
            return self._wrap_coro(self._async.get_access_logs(db, subject_id=subject_id, access_type=access_type))  # type: ignore[arg-type]

        logs = list(self._access_logs.values())
        if subject_id:
            logs = [l for l in logs if l.subject_id == subject_id]
        if access_type:
            logs = [l for l in logs if l.access_type == access_type]
        return self._wrap(logs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def request_deletion(
        self,
        subject_id: UUID,
        requested_by: UUID,
        reason: str,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryDeletionRequest | DeletionRequest | None]:
        if db is not None:
            return self._wrap_coro(self._async.request_deletion(db, subject_id, requested_by, reason))

        subject = self._subjects.get(subject_id)
        if not subject:
            return self._wrap(None)

        now = datetime.now(timezone.utc)
        affected_tables = list({f.table for f in self._fields.values() if f.table})
        request = MemoryDeletionRequest(
            subject_id=subject_id,
            requested_by_id=requested_by,
            requested_at=now,
            reason=reason,
            status="pending",
            affected_tables=affected_tables,
            deleted_records=0,
            errors=[],
        )
        self._deletion_requests[request.id] = request
        subject.deletion_requested_at = now
        return self._wrap(request)

    def process_deletion(
        self,
        request_id: UUID,
        deleted_records: int = 0,
        errors: list[str] | None = None,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[MemoryDeletionRequest | DeletionRequest | None]:
        if db is not None:
            return self._wrap_coro(self._async.process_deletion(db, request_id, deleted_records=deleted_records, errors=errors))

        request = self._deletion_requests.get(request_id)
        if not request:
            return self._wrap(None)

        now = datetime.now(timezone.utc)
        if errors:
            request.status = "failed"
            request.errors = errors
        else:
            request.status = "completed"
            request.completed_at = now
            request.deleted_records = deleted_records
            subject = self._subjects.get(request.subject_id)
            if subject:
                subject.deletion_completed_at = now
        return self._wrap(request)

    def get_pending_deletions(self, db: AsyncSession | None = None) -> AwaitableValue[list[MemoryDeletionRequest | DeletionRequest]]:
        if db is not None:
            return self._wrap_coro(self._async.get_pending_deletions(db))  # type: ignore[arg-type]

        pending = [r for r in self._deletion_requests.values() if r.status == "pending"]
        return self._wrap(pending)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_pii_report(
        self,
        subject_id: UUID,
        generated_by: UUID,
        db: AsyncSession | None = None,
    ) -> AwaitableValue[PIIReport | None]:
        if db is not None:
            return self._wrap_coro(self._async.generate_pii_report(db, subject_id, generated_by))

        subject = self._subjects.get(subject_id)
        if not subject:
            return self._wrap(None)

        fields_data = [
            {
                "name": f.name,
                "table": f.table,
                "column": f.column,
                "category": self._resolve_category(f.category),
                "sensitivity": self._resolve_sensitivity(f.sensitivity),
                "retention_days": f.retention_days,
            }
            for f in self._fields.values()
        ]

        consents = [c for c in self._consents.values() if c.subject_id == subject_id]
        access_logs = [l for l in self._access_logs.values() if l.subject_id == subject_id]

        return self._wrap(
            PIIReport(
                subject_id=subject_id,
                generated_at=datetime.now(timezone.utc),
                generated_by=generated_by,
                fields=fields_data,
                consents=consents,  # type: ignore[arg-type]
                access_logs=access_logs,  # type: ignore[arg-type]
            )
        )

    def get_retention_violations(self, db: AsyncSession | None = None) -> AwaitableValue[list[dict[str, Any]]]:
        if db is not None:
            return self._wrap_coro(self._async.get_retention_violations(db))

        violations = []
        now = datetime.now(timezone.utc)
        for field_def in self._fields.values():
            if not field_def.retention_days:
                continue
            violations.append(
                {
                    "field_id": field_def.id,
                    "field_name": field_def.name,
                    "table": field_def.table,
                    "column": field_def.column,
                    "retention_days": field_def.retention_days,
                    "cutoff_date": now - timedelta(days=field_def.retention_days),
                }
            )
        return self._wrap(violations)

    def get_expired_consents(self, db: AsyncSession | None = None) -> AwaitableValue[list[MemoryConsent | Consent]]:
        if db is not None:
            return self._wrap_coro(self._async.get_expired_consents(db))  # type: ignore[arg-type]

        now = datetime.now(timezone.utc)
        expired = [
            c for c in self._consents.values()
            if c.status == ConsentStatus.GRANTED and c.expires_at and c.expires_at < now
        ]
        return self._wrap(expired)  # type: ignore[arg-type]

    def get_summary(self, db: AsyncSession | None = None) -> AwaitableValue[dict[str, Any]]:
        if db is not None:
            return self._wrap_coro(self._async.get_summary(db))

        by_category: dict[str, int] = {}
        by_sensitivity: dict[str, int] = {}
        for field_def in self._fields.values():
            cat = self._resolve_category(field_def.category)
            sens = self._resolve_sensitivity(field_def.sensitivity)
            by_category[cat] = by_category.get(cat, 0) + 1
            by_sensitivity[sens] = by_sensitivity.get(sens, 0) + 1

        pending_deletions = [r for r in self._deletion_requests.values() if r.status == "pending"]
        expired_consents = [
            c for c in self._consents.values()
            if c.status == ConsentStatus.GRANTED and c.expires_at and c.expires_at < datetime.now(timezone.utc)
        ]

        return self._wrap(
            {
                "total_fields": len(self._fields),
                "total_subjects": len(self._subjects),
                "total_consents": len(self._consents),
                "total_access_logs": len(self._access_logs),
                "pending_deletions": len(pending_deletions),
                "by_category": by_category,
                "by_sensitivity": by_sensitivity,
                "expired_consents": len(expired_consents),
            }
        )

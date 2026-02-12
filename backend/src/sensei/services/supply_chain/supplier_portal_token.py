"""
Supplier Portal Token Service.

Handles secure, tokenized links for suppliers to upload quotes directly:
- Generate unique tokens with expiration
- Token validation and access control
- Track token usage and submissions
- Revoke tokens as needed
"""

import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TokenType(str, Enum):
    """Types of supplier portal tokens."""
    
    QUOTE_SUBMISSION = "quote_submission"
    DOCUMENT_UPLOAD = "document_upload"
    QUALIFICATION_RESPONSE = "qualification_response"
    SAMPLE_TRACKING = "sample_tracking"
    SURVEY = "survey"
    PPAP_SUBMISSION = "ppap_submission"
    CAPACITY_CONFIRMATION = "capacity_confirmation"


class TokenStatus(str, Enum):
    """Status of a portal token."""
    
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class AccessLevel(str, Enum):
    """Access level granted by token."""
    
    READ_ONLY = "read_only"
    UPLOAD_ONLY = "upload_only"
    READ_WRITE = "read_write"
    FULL_ACCESS = "full_access"


class SubmissionStatus(str, Enum):
    """Status of a submission made through the portal."""
    
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class FileType(str, Enum):
    """Allowed file types for uploads."""
    
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    IMAGE = "image"
    CAD = "cad"
    OTHER = "other"


@dataclass
class TokenConfig:
    """Configuration for token generation."""
    
    default_expiry_days: int = 14
    max_uses: Optional[int] = None  # None = unlimited
    max_file_size_mb: int = 50
    allowed_file_types: list[FileType] = field(default_factory=lambda: [
        FileType.PDF, FileType.EXCEL, FileType.WORD, FileType.IMAGE
    ])
    require_email_verification: bool = False
    auto_notify_on_submission: bool = True
    allow_partial_submission: bool = True
    max_files_per_submission: int = 20


@dataclass
class SupplierContact:
    """Supplier contact information."""
    
    id: UUID
    supplier_id: UUID
    supplier_name: str
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    company_name: Optional[str] = None
    is_primary: bool = False


@dataclass
class PortalToken:
    """A secure portal access token."""
    
    id: UUID
    token_value: str  # Truncated prefix for display only (first 8 chars + "...")
    token_hash: str  # SHA-256 hash used for lookup/validation
    token_type: TokenType
    status: TokenStatus
    access_level: AccessLevel
    
    # Entity references
    rfq_id: Optional[UUID]
    quote_id: Optional[UUID]
    supplier_id: UUID
    supplier_contact_id: Optional[UUID]
    
    # Metadata
    purpose_description: str
    created_by: UUID
    created_at: datetime
    expires_at: datetime
    
    # Usage tracking
    use_count: int = 0
    max_uses: Optional[int] = None
    last_used_at: Optional[datetime] = None
    first_used_at: Optional[datetime] = None
    
    # Security
    ip_restrictions: Optional[list[str]] = None
    allowed_domains: Optional[list[str]] = None
    require_email_match: bool = True
    
    # Config
    config: Optional[TokenConfig] = None
    
    # Revocation info
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    revoke_reason: Optional[str] = None


@dataclass
class UploadedFile:
    """A file uploaded through the portal."""
    
    id: UUID
    token_id: UUID
    submission_id: UUID
    file_name: str
    original_name: str
    file_type: FileType
    mime_type: str
    file_size_bytes: int
    file_hash: str  # SHA256 hash of file content
    storage_path: str
    uploaded_at: datetime
    uploaded_by_email: str
    is_virus_scanned: bool = False
    scan_result: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class PortalSubmission:
    """A submission made through the portal."""
    
    id: UUID
    token_id: UUID
    token_type: TokenType
    supplier_id: UUID
    rfq_id: Optional[UUID]
    quote_id: Optional[UUID]
    
    # Submission details
    status: SubmissionStatus
    submitted_by_name: str
    submitted_by_email: str
    submitted_at: datetime
    
    # Content
    files: list[UploadedFile] = field(default_factory=list)
    form_data: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    
    # Quote-specific
    quoted_price: Optional[float] = None
    quoted_currency: Optional[str] = None
    quoted_lead_time_days: Optional[int] = None
    quoted_moq: Optional[int] = None
    quoted_validity_days: Optional[int] = None
    
    # Review
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    review_notes: Optional[str] = None
    
    # Revision tracking
    revision_number: int = 1
    previous_submission_id: Optional[UUID] = None


@dataclass
class TokenAccessLog:
    """Log of token access attempts."""
    
    id: UUID
    token_id: UUID
    accessed_at: datetime
    ip_address: str
    user_agent: str
    access_granted: bool
    denial_reason: Optional[str] = None
    email_provided: Optional[str] = None
    action_performed: Optional[str] = None


@dataclass
class NotificationRecord:
    """Record of notifications sent."""
    
    id: UUID
    token_id: UUID
    submission_id: Optional[UUID]
    notification_type: str  # "token_created", "submission_received", "reminder", etc.
    recipient_email: str
    sent_at: datetime
    subject: str
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class TokenGenerationResult:
    """Result of generating a new token."""
    
    token: PortalToken
    access_url: str
    plain_token: str  # Only returned once at creation
    expires_at: datetime
    qr_code_data: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating a token."""
    
    is_valid: bool
    token: Optional[PortalToken]
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    remaining_uses: Optional[int] = None
    time_until_expiry: Optional[timedelta] = None


@dataclass
class SubmissionResult:
    """Result of creating a submission."""
    
    success: bool
    submission: Optional[PortalSubmission]
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


class SupplierPortalTokenService(PersistentServiceMixin):
    """
    Service for managing supplier portal tokens.
    
    Handles:
    - Token generation with secure random values
    - Token validation and access control
    - Submission processing and tracking
    - Access logging and analytics
    """

    SERVICE_NAME = "supplier_portal"
    
    # Default tenant for single-tenant deployments
    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

    def __init__(
        self,
        base_url: str = "https://supplier.example.com/portal",
        default_config: Optional[TokenConfig] = None,
    ) -> None:
        """Initialize the service."""
        self.base_url = base_url
        self.default_config = default_config or TokenConfig()
        
        self._tokens: dict[UUID, PortalToken] = {}
        self._token_by_hash: dict[str, UUID] = {}  # Hash -> token ID lookup
        self._submissions: dict[UUID, PortalSubmission] = {}
        self._uploaded_files: dict[UUID, UploadedFile] = {}
        self._access_logs: dict[UUID, TokenAccessLog] = {}
        self._notifications: dict[UUID, NotificationRecord] = {}
        self._supplier_contacts: dict[UUID, SupplierContact] = {}

    # ----------------------------------------------------------------
    # Persistence helpers — serialise dataclasses to/from JSON-safe dicts
    # ----------------------------------------------------------------

    def _serialise_token(self, token: PortalToken) -> dict[str, Any]:
        """Convert a PortalToken to a JSON-serialisable dict."""
        d: dict[str, Any] = {}
        for k, v in token.__dict__.items():
            if isinstance(v, UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
            elif isinstance(v, (TokenType, TokenStatus, AccessLevel)):
                d[k] = v.value
            elif isinstance(v, TokenConfig):
                d[k] = {
                    "default_expiry_days": v.default_expiry_days,
                    "max_uses": v.max_uses,
                    "max_file_size_mb": v.max_file_size_mb,
                    "allowed_file_types": [ft.value for ft in v.allowed_file_types],
                    "require_email_verification": v.require_email_verification,
                    "auto_notify_on_submission": v.auto_notify_on_submission,
                    "allow_partial_submission": v.allow_partial_submission,
                    "max_files_per_submission": v.max_files_per_submission,
                }
            elif isinstance(v, list):
                d[k] = v  # list[str] for ip_restrictions / allowed_domains
            else:
                d[k] = v
        return d

    def _serialise_submission(self, sub: PortalSubmission) -> dict[str, Any]:
        """Convert a PortalSubmission to a JSON-serialisable dict."""
        d: dict[str, Any] = {}
        for k, v in sub.__dict__.items():
            if k == "files":
                d[k] = [self._serialise_file(f) for f in v]
            elif isinstance(v, UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
            elif isinstance(v, (SubmissionStatus, TokenType)):
                d[k] = v.value
            else:
                d[k] = v
        return d

    def _serialise_file(self, uf: UploadedFile) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k, v in uf.__dict__.items():
            if isinstance(v, UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
            elif isinstance(v, FileType):
                d[k] = v.value
            else:
                d[k] = v
        return d

    async def _persist_tokens(self) -> None:
        """Best-effort persist all tokens to the service_state table."""
        data = {str(tid): self._serialise_token(t) for tid, t in self._tokens.items()}
        await self.save_state(self._DEFAULT_TENANT_ID, "tokens", data)

    async def _persist_submissions(self) -> None:
        """Best-effort persist all submissions to the service_state table."""
        data = {str(sid): self._serialise_submission(s) for sid, s in self._submissions.items()}
        await self.save_state(self._DEFAULT_TENANT_ID, "submissions", data)

    async def _persist_contacts(self) -> None:
        """Best-effort persist supplier contacts."""
        data = {}
        for cid, c in self._supplier_contacts.items():
            data[str(cid)] = {
                "id": str(c.id),
                "supplier_id": str(c.supplier_id),
                "supplier_name": c.supplier_name,
                "contact_name": c.contact_name,
                "contact_email": c.contact_email,
                "contact_phone": c.contact_phone,
                "company_name": c.company_name,
                "is_primary": c.is_primary,
            }
        await self.save_state(self._DEFAULT_TENANT_ID, "supplier_contacts", data)

    async def persist_all(self) -> None:
        """Persist all in-memory state to the database.

        Call after mutations to ensure data survives restarts.
        Failures are logged but not raised (best-effort).
        """
        import logging as _log
        _logger = _log.getLogger(__name__)
        try:
            await self._persist_tokens()
        except Exception:
            _logger.warning("Failed to persist tokens", exc_info=True)
        try:
            await self._persist_submissions()
        except Exception:
            _logger.warning("Failed to persist submissions", exc_info=True)
        try:
            await self._persist_contacts()
        except Exception:
            _logger.warning("Failed to persist contacts", exc_info=True)

    async def load_from_db(self) -> None:
        """Load persisted state from DB into in-memory dicts on startup.

        Silently degrades to empty state if the DB is unavailable.
        """
        import logging as _log
        _logger = _log.getLogger(__name__)

        # Tokens
        try:
            tokens_data = await self.load_state(self._DEFAULT_TENANT_ID, "tokens")
            if tokens_data and isinstance(tokens_data, dict):
                for _tid_s, td in tokens_data.items():
                    try:
                        tid = UUID(td["id"])
                        token = PortalToken(
                            id=tid,
                            token_value=td["token_value"],
                            token_hash=td["token_hash"],
                            token_type=TokenType(td["token_type"]),
                            status=TokenStatus(td["status"]),
                            access_level=AccessLevel(td["access_level"]),
                            rfq_id=UUID(td["rfq_id"]) if td.get("rfq_id") else None,
                            quote_id=UUID(td["quote_id"]) if td.get("quote_id") else None,
                            supplier_id=UUID(td["supplier_id"]),
                            supplier_contact_id=UUID(td["supplier_contact_id"]) if td.get("supplier_contact_id") else None,
                            purpose_description=td.get("purpose_description", ""),
                            created_by=UUID(td["created_by"]),
                            created_at=datetime.fromisoformat(td["created_at"]),
                            expires_at=datetime.fromisoformat(td["expires_at"]),
                            use_count=td.get("use_count", 0),
                            max_uses=td.get("max_uses"),
                            last_used_at=datetime.fromisoformat(td["last_used_at"]) if td.get("last_used_at") else None,
                            first_used_at=datetime.fromisoformat(td["first_used_at"]) if td.get("first_used_at") else None,
                            ip_restrictions=td.get("ip_restrictions"),
                            allowed_domains=td.get("allowed_domains"),
                            require_email_match=td.get("require_email_match", True),
                        )
                        self._tokens[tid] = token
                        self._token_by_hash[token.token_hash] = tid
                    except Exception:
                        _logger.debug("Skipping malformed token entry %s", _tid_s, exc_info=True)
        except Exception:
            _logger.warning("Failed to restore tokens from DB", exc_info=True)

        # Contacts
        try:
            contacts_data = await self.load_state(self._DEFAULT_TENANT_ID, "supplier_contacts")
            if contacts_data and isinstance(contacts_data, dict):
                for _cid_s, cd in contacts_data.items():
                    try:
                        cid = UUID(cd["id"])
                        self._supplier_contacts[cid] = SupplierContact(
                            id=cid,
                            supplier_id=UUID(cd["supplier_id"]),
                            supplier_name=cd["supplier_name"],
                            contact_name=cd["contact_name"],
                            contact_email=cd["contact_email"],
                            contact_phone=cd.get("contact_phone"),
                            company_name=cd.get("company_name"),
                            is_primary=cd.get("is_primary", False),
                        )
                    except Exception:
                        _logger.debug("Skipping malformed contact entry %s", _cid_s, exc_info=True)
        except Exception:
            _logger.warning("Failed to restore contacts from DB", exc_info=True)
    
    def _generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    def _hash_token(self, token_value: str) -> str:
        """Hash a token value for storage."""
        return hashlib.sha256(token_value.encode()).hexdigest()
    
    def generate_token(
        self,
        token_type: TokenType,
        supplier_id: UUID,
        created_by: UUID,
        purpose_description: str,
        rfq_id: Optional[UUID] = None,
        quote_id: Optional[UUID] = None,
        supplier_contact_id: Optional[UUID] = None,
        access_level: AccessLevel = AccessLevel.UPLOAD_ONLY,
        expiry_days: Optional[int] = None,
        max_uses: Optional[int] = None,
        config: Optional[TokenConfig] = None,
        ip_restrictions: Optional[list[str]] = None,
        allowed_domains: Optional[list[str]] = None,
        require_email_match: bool = True,
    ) -> TokenGenerationResult:
        """
        Generate a new portal access token.
        
        Args:
            token_type: Type of access token
            supplier_id: Supplier ID
            created_by: User creating the token
            purpose_description: Description of token purpose
            rfq_id: Optional RFQ ID
            quote_id: Optional Quote ID
            supplier_contact_id: Optional supplier contact ID
            access_level: Level of access granted
            expiry_days: Days until expiration (default from config)
            max_uses: Maximum number of uses
            config: Token configuration
            ip_restrictions: Optional IP restrictions
            allowed_domains: Optional domain restrictions
            require_email_match: Require email to match contact
            
        Returns:
            TokenGenerationResult with token details
        """
        # Generate secure token
        plain_token = self._generate_secure_token()
        token_hash = self._hash_token(plain_token)
        
        # Calculate expiry
        effective_config = config or self.default_config
        days = expiry_days if expiry_days is not None else effective_config.default_expiry_days
        expires_at = _utcnow() + timedelta(days=days)
        
        # Create token
        token = PortalToken(
            id=uuid4(),
            token_value=plain_token[:8] + "...",  # Store partial for display
            token_hash=token_hash,
            token_type=token_type,
            status=TokenStatus.ACTIVE,
            access_level=access_level,
            rfq_id=rfq_id,
            quote_id=quote_id,
            supplier_id=supplier_id,
            supplier_contact_id=supplier_contact_id,
            purpose_description=purpose_description,
            created_by=created_by,
            created_at=_utcnow(),
            expires_at=expires_at,
            max_uses=max_uses if max_uses is not None else effective_config.max_uses,
            ip_restrictions=ip_restrictions,
            allowed_domains=allowed_domains,
            require_email_match=require_email_match,
            config=effective_config,
        )
        
        # Store token
        self._tokens[token.id] = token
        self._token_by_hash[token_hash] = token.id
        
        # Generate access URL
        access_url = f"{self.base_url}/access/{plain_token}"
        
        return TokenGenerationResult(
            token=token,
            access_url=access_url,
            plain_token=plain_token,
            expires_at=expires_at,
        )
    
    def generate_quote_submission_token(
        self,
        rfq_id: UUID,
        supplier_id: UUID,
        created_by: UUID,
        supplier_contact_id: Optional[UUID] = None,
        expiry_days: int = 14,
    ) -> TokenGenerationResult:
        """Generate a token specifically for quote submission."""
        return self.generate_token(
            token_type=TokenType.QUOTE_SUBMISSION,
            supplier_id=supplier_id,
            created_by=created_by,
            purpose_description=f"Quote submission for RFQ",
            rfq_id=rfq_id,
            supplier_contact_id=supplier_contact_id,
            access_level=AccessLevel.UPLOAD_ONLY,
            expiry_days=expiry_days,
        )
    
    def generate_document_upload_token(
        self,
        supplier_id: UUID,
        created_by: UUID,
        purpose_description: str,
        quote_id: Optional[UUID] = None,
        expiry_days: int = 7,
    ) -> TokenGenerationResult:
        """Generate a token for general document uploads."""
        return self.generate_token(
            token_type=TokenType.DOCUMENT_UPLOAD,
            supplier_id=supplier_id,
            created_by=created_by,
            purpose_description=purpose_description,
            quote_id=quote_id,
            access_level=AccessLevel.UPLOAD_ONLY,
            expiry_days=expiry_days,
        )
    
    def generate_ppap_submission_token(
        self,
        supplier_id: UUID,
        quote_id: UUID,
        created_by: UUID,
        expiry_days: int = 30,
    ) -> TokenGenerationResult:
        """Generate a token for PPAP document submission."""
        return self.generate_token(
            token_type=TokenType.PPAP_SUBMISSION,
            supplier_id=supplier_id,
            created_by=created_by,
            purpose_description="PPAP documentation submission",
            quote_id=quote_id,
            access_level=AccessLevel.UPLOAD_ONLY,
            expiry_days=expiry_days,
            config=TokenConfig(
                allowed_file_types=[FileType.PDF, FileType.EXCEL, FileType.CAD],
                max_file_size_mb=100,
                max_files_per_submission=50,
            ),
        )
    
    # Token Retrieval
    
    def get_token(self, token_id: UUID) -> Optional[PortalToken]:
        """Get a token by ID."""
        return self._tokens.get(token_id)
    
    def get_token_by_value(self, token_value: str) -> Optional[PortalToken]:
        """Get a token by its value (validates hash)."""
        token_hash = self._hash_token(token_value)
        token_id = self._token_by_hash.get(token_hash)
        if token_id:
            return self._tokens.get(token_id)
        return None
    
    def list_tokens(
        self,
        supplier_id: Optional[UUID] = None,
        rfq_id: Optional[UUID] = None,
        token_type: Optional[TokenType] = None,
        status: Optional[TokenStatus] = None,
        created_by: Optional[UUID] = None,
        include_expired: bool = False,
    ) -> list[PortalToken]:
        """List tokens with optional filters."""
        tokens = list(self._tokens.values())
        
        if supplier_id:
            tokens = [t for t in tokens if t.supplier_id == supplier_id]
        
        if rfq_id:
            tokens = [t for t in tokens if t.rfq_id == rfq_id]
        
        if token_type:
            tokens = [t for t in tokens if t.token_type == token_type]
        
        if status:
            tokens = [t for t in tokens if t.status == status]
        
        if created_by:
            tokens = [t for t in tokens if t.created_by == created_by]
        
        if not include_expired:
            now = _utcnow()
            tokens = [t for t in tokens if t.expires_at > now or t.status != TokenStatus.EXPIRED]
        
        return sorted(tokens, key=lambda t: t.created_at, reverse=True)
    
    def list_tokens_for_rfq(self, rfq_id: UUID) -> list[PortalToken]:
        """List all tokens for a specific RFQ."""
        return self.list_tokens(rfq_id=rfq_id)
    
    def list_active_tokens_for_supplier(self, supplier_id: UUID) -> list[PortalToken]:
        """List all active tokens for a supplier."""
        return self.list_tokens(supplier_id=supplier_id, status=TokenStatus.ACTIVE)
    
    # Token Validation
    
    def validate_token(
        self,
        token_value: str,
        ip_address: Optional[str] = None,
        email: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a token for access.
        
        Args:
            token_value: The token value to validate
            ip_address: Optional IP address of accessor
            email: Optional email of accessor
            
        Returns:
            ValidationResult with validation status
        """
        # Find token
        token = self.get_token_by_value(token_value)
        
        if not token:
            return ValidationResult(
                is_valid=False,
                token=None,
                error_message="Invalid token",
                error_code="INVALID_TOKEN",
            )
        
        # Check status
        if token.status == TokenStatus.REVOKED:
            return ValidationResult(
                is_valid=False,
                token=token,
                error_message="Token has been revoked",
                error_code="TOKEN_REVOKED",
            )
        
        if token.status == TokenStatus.SUSPENDED:
            return ValidationResult(
                is_valid=False,
                token=token,
                error_message="Token is suspended",
                error_code="TOKEN_SUSPENDED",
            )
        
        # Check expiration
        now = _utcnow()
        if token.expires_at < now:
            token.status = TokenStatus.EXPIRED
            return ValidationResult(
                is_valid=False,
                token=token,
                error_message="Token has expired",
                error_code="TOKEN_EXPIRED",
            )
        
        # Check max uses
        if token.max_uses is not None and token.use_count >= token.max_uses:
            token.status = TokenStatus.USED
            return ValidationResult(
                is_valid=False,
                token=token,
                error_message="Token has exceeded maximum uses",
                error_code="MAX_USES_EXCEEDED",
            )
        
        # Check IP restrictions
        if ip_address and token.ip_restrictions:
            if ip_address not in token.ip_restrictions:
                return ValidationResult(
                    is_valid=False,
                    token=token,
                    error_message="Access from this IP is not allowed",
                    error_code="IP_RESTRICTED",
                )
        
        # Check email match if required
        if token.require_email_match and email and token.supplier_contact_id:
            contact = self._supplier_contacts.get(token.supplier_contact_id)
            if contact and contact.contact_email.lower() != email.lower():
                return ValidationResult(
                    is_valid=False,
                    token=token,
                    error_message="Email does not match expected contact",
                    error_code="EMAIL_MISMATCH",
                )
        
        # Calculate remaining info
        remaining_uses = None
        if token.max_uses is not None:
            remaining_uses = token.max_uses - token.use_count
        
        time_until_expiry = token.expires_at - now
        
        return ValidationResult(
            is_valid=True,
            token=token,
            remaining_uses=remaining_uses,
            time_until_expiry=time_until_expiry,
        )
    
    def record_token_access(
        self,
        token_id: UUID,
        ip_address: str,
        user_agent: str,
        access_granted: bool,
        email_provided: Optional[str] = None,
        denial_reason: Optional[str] = None,
        action_performed: Optional[str] = None,
    ) -> TokenAccessLog:
        """Record a token access attempt."""
        log = TokenAccessLog(
            id=uuid4(),
            token_id=token_id,
            accessed_at=_utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            access_granted=access_granted,
            denial_reason=denial_reason,
            email_provided=email_provided,
            action_performed=action_performed,
        )
        
        self._access_logs[log.id] = log
        
        # Update token usage if access granted
        if access_granted:
            token = self._tokens.get(token_id)
            if token:
                token.use_count += 1
                token.last_used_at = _utcnow()
                if token.first_used_at is None:
                    token.first_used_at = _utcnow()
        
        return log
    
    def get_access_logs(
        self,
        token_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[TokenAccessLog]:
        """Get access logs, optionally filtered by token."""
        logs = list(self._access_logs.values())
        
        if token_id:
            logs = [l for l in logs if l.token_id == token_id]
        
        return sorted(logs, key=lambda l: l.accessed_at, reverse=True)[:limit]
    
    # Token Management
    
    def revoke_token(
        self,
        token_id: UUID,
        revoked_by: UUID,
        reason: str,
    ) -> Optional[PortalToken]:
        """Revoke a token."""
        token = self._tokens.get(token_id)
        if not token:
            return None
        
        token.status = TokenStatus.REVOKED
        token.revoked_at = _utcnow()
        token.revoked_by = revoked_by
        token.revoke_reason = reason
        
        return token
    
    def suspend_token(self, token_id: UUID) -> Optional[PortalToken]:
        """Temporarily suspend a token."""
        token = self._tokens.get(token_id)
        if not token:
            return None
        
        token.status = TokenStatus.SUSPENDED
        return token
    
    def reactivate_token(
        self,
        token_id: UUID,
        extend_expiry_days: Optional[int] = None,
    ) -> Optional[PortalToken]:
        """Reactivate a suspended token."""
        token = self._tokens.get(token_id)
        if not token:
            return None
        
        if token.status not in (TokenStatus.SUSPENDED, TokenStatus.EXPIRED):
            return token
        
        token.status = TokenStatus.ACTIVE
        
        if extend_expiry_days:
            token.expires_at = _utcnow() + timedelta(days=extend_expiry_days)
        elif token.expires_at < _utcnow():
            # If expired, extend by original duration
            token.expires_at = _utcnow() + timedelta(days=7)
        
        return token
    
    def extend_token_expiry(
        self,
        token_id: UUID,
        additional_days: int,
    ) -> Optional[PortalToken]:
        """Extend a token's expiry date."""
        token = self._tokens.get(token_id)
        if not token:
            return None
        
        token.expires_at = token.expires_at + timedelta(days=additional_days)
        return token
    
    def expire_old_tokens(self) -> int:
        """Expire tokens past their expiration date. Returns count."""
        now = _utcnow()
        count = 0
        
        for token in self._tokens.values():
            if token.status == TokenStatus.ACTIVE and token.expires_at < now:
                token.status = TokenStatus.EXPIRED
                count += 1
        
        return count
    
    # Supplier Contact Management
    
    def register_supplier_contact(
        self,
        supplier_id: UUID,
        supplier_name: str,
        contact_name: str,
        contact_email: str,
        contact_phone: Optional[str] = None,
        company_name: Optional[str] = None,
        is_primary: bool = False,
    ) -> SupplierContact:
        """Register a supplier contact."""
        contact = SupplierContact(
            id=uuid4(),
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            company_name=company_name,
            is_primary=is_primary,
        )
        
        self._supplier_contacts[contact.id] = contact
        return contact
    
    def get_supplier_contact(self, contact_id: UUID) -> Optional[SupplierContact]:
        """Get a supplier contact by ID."""
        return self._supplier_contacts.get(contact_id)
    
    def list_supplier_contacts(self, supplier_id: UUID) -> list[SupplierContact]:
        """List contacts for a supplier."""
        return [c for c in self._supplier_contacts.values() if c.supplier_id == supplier_id]
    
    # Submission Management
    
    def create_submission(
        self,
        token_id: UUID,
        submitted_by_name: str,
        submitted_by_email: str,
        notes: Optional[str] = None,
        form_data: Optional[dict[str, Any]] = None,
        quoted_price: Optional[float] = None,
        quoted_currency: Optional[str] = None,
        quoted_lead_time_days: Optional[int] = None,
        quoted_moq: Optional[int] = None,
        quoted_validity_days: Optional[int] = None,
    ) -> SubmissionResult:
        """
        Create a new submission.
        
        Args:
            token_id: Token used for submission
            submitted_by_name: Name of submitter
            submitted_by_email: Email of submitter
            notes: Optional notes
            form_data: Optional form data
            quoted_price: Optional quoted price
            quoted_currency: Optional currency
            quoted_lead_time_days: Optional lead time
            quoted_moq: Optional MOQ
            quoted_validity_days: Optional validity period
            
        Returns:
            SubmissionResult with submission details
        """
        token = self._tokens.get(token_id)
        if not token:
            return SubmissionResult(
                success=False,
                submission=None,
                error_message="Token not found",
            )
        
        if token.status != TokenStatus.ACTIVE:
            return SubmissionResult(
                success=False,
                submission=None,
                error_message=f"Token is not active (status: {token.status.value})",
            )
        
        # Create submission
        submission = PortalSubmission(
            id=uuid4(),
            token_id=token_id,
            token_type=token.token_type,
            supplier_id=token.supplier_id,
            rfq_id=token.rfq_id,
            quote_id=token.quote_id,
            status=SubmissionStatus.SUBMITTED,
            submitted_by_name=submitted_by_name,
            submitted_by_email=submitted_by_email,
            submitted_at=_utcnow(),
            notes=notes,
            form_data=form_data,
            quoted_price=quoted_price,
            quoted_currency=quoted_currency,
            quoted_lead_time_days=quoted_lead_time_days,
            quoted_moq=quoted_moq,
            quoted_validity_days=quoted_validity_days,
        )
        
        self._submissions[submission.id] = submission
        
        # Update token usage
        token.use_count += 1
        token.last_used_at = _utcnow()
        if token.first_used_at is None:
            token.first_used_at = _utcnow()
        
        # Check if single-use token should be marked used
        if token.max_uses and token.use_count >= token.max_uses:
            token.status = TokenStatus.USED
        
        return SubmissionResult(
            success=True,
            submission=submission,
        )
    
    def add_file_to_submission(
        self,
        submission_id: UUID,
        file_name: str,
        original_name: str,
        file_type: FileType,
        mime_type: str,
        file_size_bytes: int,
        file_hash: str,
        storage_path: str,
        uploaded_by_email: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[UploadedFile]:
        """Add a file to a submission."""
        submission = self._submissions.get(submission_id)
        if not submission:
            return None
        
        uploaded_file = UploadedFile(
            id=uuid4(),
            token_id=submission.token_id,
            submission_id=submission_id,
            file_name=file_name,
            original_name=original_name,
            file_type=file_type,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            file_hash=file_hash,
            storage_path=storage_path,
            uploaded_at=_utcnow(),
            uploaded_by_email=uploaded_by_email,
            metadata=metadata,
        )
        
        self._uploaded_files[uploaded_file.id] = uploaded_file
        submission.files.append(uploaded_file)
        
        return uploaded_file
    
    def get_submission(self, submission_id: UUID) -> Optional[PortalSubmission]:
        """Get a submission by ID."""
        return self._submissions.get(submission_id)
    
    def list_submissions(
        self,
        token_id: Optional[UUID] = None,
        supplier_id: Optional[UUID] = None,
        rfq_id: Optional[UUID] = None,
        status: Optional[SubmissionStatus] = None,
    ) -> list[PortalSubmission]:
        """List submissions with optional filters."""
        submissions = list(self._submissions.values())
        
        if token_id:
            submissions = [s for s in submissions if s.token_id == token_id]
        
        if supplier_id:
            submissions = [s for s in submissions if s.supplier_id == supplier_id]
        
        if rfq_id:
            submissions = [s for s in submissions if s.rfq_id == rfq_id]
        
        if status:
            submissions = [s for s in submissions if s.status == status]
        
        return sorted(submissions, key=lambda s: s.submitted_at, reverse=True)
    
    def list_submissions_for_rfq(self, rfq_id: UUID) -> list[PortalSubmission]:
        """List all submissions for a specific RFQ."""
        return self.list_submissions(rfq_id=rfq_id)
    
    # Submission Review
    
    def accept_submission(
        self,
        submission_id: UUID,
        reviewed_by: UUID,
        review_notes: Optional[str] = None,
    ) -> Optional[PortalSubmission]:
        """Accept a submission."""
        submission = self._submissions.get(submission_id)
        if not submission:
            return None
        
        submission.status = SubmissionStatus.ACCEPTED
        submission.reviewed_at = _utcnow()
        submission.reviewed_by = reviewed_by
        submission.review_notes = review_notes
        
        return submission
    
    def reject_submission(
        self,
        submission_id: UUID,
        reviewed_by: UUID,
        review_notes: str,
    ) -> Optional[PortalSubmission]:
        """Reject a submission."""
        submission = self._submissions.get(submission_id)
        if not submission:
            return None
        
        submission.status = SubmissionStatus.REJECTED
        submission.reviewed_at = _utcnow()
        submission.reviewed_by = reviewed_by
        submission.review_notes = review_notes
        
        return submission
    
    def request_revision(
        self,
        submission_id: UUID,
        reviewed_by: UUID,
        review_notes: str,
    ) -> Optional[PortalSubmission]:
        """Request a revision on a submission."""
        submission = self._submissions.get(submission_id)
        if not submission:
            return None
        
        submission.status = SubmissionStatus.REVISION_REQUESTED
        submission.reviewed_at = _utcnow()
        submission.reviewed_by = reviewed_by
        submission.review_notes = review_notes
        
        return submission
    
    def mark_under_review(
        self,
        submission_id: UUID,
        reviewed_by: UUID,
    ) -> Optional[PortalSubmission]:
        """Mark a submission as under review."""
        submission = self._submissions.get(submission_id)
        if not submission:
            return None
        
        submission.status = SubmissionStatus.UNDER_REVIEW
        submission.reviewed_by = reviewed_by
        
        return submission
    
    # Notifications
    
    def record_notification(
        self,
        token_id: UUID,
        notification_type: str,
        recipient_email: str,
        subject: str,
        submission_id: Optional[UUID] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> NotificationRecord:
        """Record a notification that was sent."""
        record = NotificationRecord(
            id=uuid4(),
            token_id=token_id,
            submission_id=submission_id,
            notification_type=notification_type,
            recipient_email=recipient_email,
            sent_at=_utcnow(),
            subject=subject,
            success=success,
            error_message=error_message,
        )
        
        self._notifications[record.id] = record
        return record
    
    def get_notifications(
        self,
        token_id: Optional[UUID] = None,
        submission_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list[NotificationRecord]:
        """Get notification records."""
        records = list(self._notifications.values())
        
        if token_id:
            records = [r for r in records if r.token_id == token_id]
        
        if submission_id:
            records = [r for r in records if r.submission_id == submission_id]
        
        return sorted(records, key=lambda r: r.sent_at, reverse=True)[:limit]
    
    # Analytics
    
    def get_token_statistics(self, token_id: UUID) -> dict[str, Any]:
        """Get statistics for a token."""
        token = self._tokens.get(token_id)
        if not token:
            return {}
        
        submissions = self.list_submissions(token_id=token_id)
        access_logs = self.get_access_logs(token_id=token_id)
        
        return {
            "token_id": str(token_id),
            "status": token.status.value,
            "created_at": token.created_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
            "use_count": token.use_count,
            "max_uses": token.max_uses,
            "first_used_at": token.first_used_at.isoformat() if token.first_used_at else None,
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
            "total_submissions": len(submissions),
            "accepted_submissions": len([s for s in submissions if s.status == SubmissionStatus.ACCEPTED]),
            "rejected_submissions": len([s for s in submissions if s.status == SubmissionStatus.REJECTED]),
            "pending_submissions": len([s for s in submissions if s.status in (
                SubmissionStatus.SUBMITTED, SubmissionStatus.UNDER_REVIEW
            )]),
            "total_access_attempts": len(access_logs),
            "successful_accesses": len([l for l in access_logs if l.access_granted]),
            "failed_accesses": len([l for l in access_logs if not l.access_granted]),
        }
    
    def get_supplier_statistics(self, supplier_id: UUID) -> dict[str, Any]:
        """Get statistics for a supplier."""
        tokens = self.list_tokens(supplier_id=supplier_id, include_expired=True)
        submissions = self.list_submissions(supplier_id=supplier_id)
        
        return {
            "supplier_id": str(supplier_id),
            "total_tokens": len(tokens),
            "active_tokens": len([t for t in tokens if t.status == TokenStatus.ACTIVE]),
            "expired_tokens": len([t for t in tokens if t.status == TokenStatus.EXPIRED]),
            "revoked_tokens": len([t for t in tokens if t.status == TokenStatus.REVOKED]),
            "total_submissions": len(submissions),
            "accepted_submissions": len([s for s in submissions if s.status == SubmissionStatus.ACCEPTED]),
            "average_response_time_hours": self._calculate_avg_response_time(submissions),
        }
    
    def _calculate_avg_response_time(self, submissions: list[PortalSubmission]) -> Optional[float]:
        """Calculate average response time for submissions."""
        total_hours = 0.0
        reviewed_count = 0
        
        for s in submissions:
            if s.reviewed_at is not None:
                total_hours += (s.reviewed_at - s.submitted_at).total_seconds() / 3600
                reviewed_count += 1
        
        if reviewed_count == 0:
            return None
        
        return round(total_hours / reviewed_count, 2)


# Singleton instance
_supplier_portal_token_service: Optional[SupplierPortalTokenService] = None


def get_supplier_portal_token_service() -> SupplierPortalTokenService:
    """Get the singleton supplier portal token service instance."""
    global _supplier_portal_token_service
    if _supplier_portal_token_service is None:
        _supplier_portal_token_service = SupplierPortalTokenService()
    return _supplier_portal_token_service


def reset_supplier_portal_token_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _supplier_portal_token_service
    _supplier_portal_token_service = None

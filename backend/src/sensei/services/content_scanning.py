"""
Content Scanning Service.

Scans uploaded files and user content for:
- Malware and virus detection (via signatures/heuristics)
- File type validation and verification
- Content policy violations
- Embedded script/macro detection
- Sensitive data patterns
- File size and dimension limits
- Archive/compression handling
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
import hashlib
import mimetypes
import re


class ScanResult(str, Enum):
    """Result of a content scan."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"
    ERROR = "error"
    PENDING = "pending"


class ThreatCategory(str, Enum):
    """Categories of threats detected."""

    MALWARE = "malware"
    VIRUS = "virus"
    TROJAN = "trojan"
    RANSOMWARE = "ransomware"
    SPYWARE = "spyware"
    SCRIPT = "script"
    MACRO = "macro"
    PHISHING = "phishing"
    POLICY_VIOLATION = "policy_violation"
    SENSITIVE_DATA = "sensitive_data"
    INVALID_TYPE = "invalid_type"
    SIZE_EXCEEDED = "size_exceeded"


class ContentType(str, Enum):
    """Types of content that can be scanned."""

    FILE = "file"
    TEXT = "text"
    URL = "url"
    ATTACHMENT = "attachment"
    COMMENT = "comment"
    FIELD_VALUE = "field_value"


class ScanMode(str, Enum):
    """Scanning modes."""

    QUICK = "quick"  # Fast signature-based scan
    STANDARD = "standard"  # Standard scan with heuristics
    DEEP = "deep"  # Full analysis including unpacking


@dataclass
class ThreatSignature:
    """A malware/threat signature."""

    id: UUID
    name: str
    category: ThreatCategory
    pattern: str
    is_regex: bool
    description: str
    severity: str  # low, medium, high, critical
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class AllowedFileType:
    """An allowed file type configuration."""

    id: UUID
    extension: str
    mime_types: list[str]
    max_size_bytes: int
    is_active: bool
    requires_deep_scan: bool
    description: str


@dataclass
class ContentPolicy:
    """Content policy rule."""

    id: UUID
    name: str
    description: str
    pattern: str
    is_regex: bool
    category: ThreatCategory
    action: str  # warn, block, quarantine
    applies_to: list[ContentType]
    is_active: bool
    created_at: datetime


@dataclass
class ScanFinding:
    """A finding from content scanning."""

    category: ThreatCategory
    signature_id: UUID | None
    policy_id: UUID | None
    description: str
    severity: str
    location: str | None
    matched_content: str | None


@dataclass
class ScanReport:
    """Complete scan report."""

    id: UUID
    content_type: ContentType
    content_hash: str
    content_size: int
    filename: str | None
    mime_type: str | None
    scan_mode: ScanMode
    result: ScanResult
    findings: list[ScanFinding]
    scanned_at: datetime
    scan_duration_ms: float
    scanned_by: UUID | None
    metadata: dict[str, Any]


@dataclass
class QuarantineEntry:
    """Entry for quarantined content."""

    id: UUID
    scan_report_id: UUID
    content_hash: str
    filename: str | None
    original_path: str | None
    quarantined_at: datetime
    quarantined_by: UUID
    reason: str
    release_status: str  # quarantined, released, deleted
    released_at: datetime | None
    released_by: UUID | None


class ContentScanningService:
    """Service for scanning content for threats and policy violations."""

    def __init__(self) -> None:
        """Initialize the content scanning service."""
        self._signatures: dict[UUID, ThreatSignature] = {}
        self._file_types: dict[UUID, AllowedFileType] = {}
        self._policies: dict[UUID, ContentPolicy] = {}
        self._reports: dict[UUID, ScanReport] = {}
        self._quarantine: dict[UUID, QuarantineEntry] = {}

        # Initialize defaults
        self._initialize_signatures()
        self._initialize_file_types()
        self._initialize_policies()

    def _initialize_signatures(self) -> None:
        """Initialize default threat signatures."""
        now = datetime.now(timezone.utc)

        # Script/code injection signatures
        self._add_signature(
            name="JavaScript Injection",
            category=ThreatCategory.SCRIPT,
            pattern=r"<script[^>]*>",
            is_regex=True,
            description="Embedded JavaScript code detected",
            severity="high",
        )

        self._add_signature(
            name="VBScript Detection",
            category=ThreatCategory.SCRIPT,
            pattern=r"<vbscript[^>]*>|vbscript:",
            is_regex=True,
            description="VBScript code detected",
            severity="high",
        )

        self._add_signature(
            name="Embedded iframe",
            category=ThreatCategory.SCRIPT,
            pattern=r"<iframe[^>]*>",
            is_regex=True,
            description="Embedded iframe detected",
            severity="medium",
        )

        # Macro/document threats
        self._add_signature(
            name="Office Macro",
            category=ThreatCategory.MACRO,
            pattern=r"AutoOpen|AutoExec|Document_Open",
            is_regex=True,
            description="Office document macro detected",
            severity="high",
        )

        self._add_signature(
            name="PowerShell Command",
            category=ThreatCategory.SCRIPT,
            pattern=r"powershell\.exe|pwsh\.exe|-encodedcommand",
            is_regex=True,
            description="PowerShell command detected",
            severity="critical",
        )

        # Executable patterns (hex signatures)
        self._add_signature(
            name="PE Executable",
            category=ThreatCategory.MALWARE,
            pattern="4D5A",  # MZ header
            is_regex=False,
            description="Windows executable file header detected",
            severity="critical",
        )

        self._add_signature(
            name="ELF Binary",
            category=ThreatCategory.MALWARE,
            pattern="7F454C46",  # ELF header
            is_regex=False,
            description="Linux executable file header detected",
            severity="critical",
        )

        # Phishing patterns
        self._add_signature(
            name="Password Request Pattern",
            category=ThreatCategory.PHISHING,
            pattern=r"(?:enter|confirm|verify)\s+(?:your\s+)?password",
            is_regex=True,
            description="Potential password phishing detected",
            severity="high",
        )

        self._add_signature(
            name="Account Verification Scam",
            category=ThreatCategory.PHISHING,
            pattern=r"account\s+(?:will\s+be\s+)?(?:suspended|closed|disabled)",
            is_regex=True,
            description="Account suspension scam pattern detected",
            severity="high",
        )

        # Sensitive data patterns
        self._add_signature(
            name="Credit Card Number",
            category=ThreatCategory.SENSITIVE_DATA,
            pattern=r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
            is_regex=True,
            description="Potential credit card number detected",
            severity="high",
        )

        self._add_signature(
            name="Social Security Number",
            category=ThreatCategory.SENSITIVE_DATA,
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            is_regex=True,
            description="Potential SSN detected",
            severity="critical",
        )

    def _add_signature(
        self,
        name: str,
        category: ThreatCategory,
        pattern: str,
        is_regex: bool,
        description: str,
        severity: str,
    ) -> ThreatSignature:
        """Add a threat signature."""
        now = datetime.now(timezone.utc)

        sig = ThreatSignature(
            id=uuid4(),
            name=name,
            category=category,
            pattern=pattern,
            is_regex=is_regex,
            description=description,
            severity=severity,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        self._signatures[sig.id] = sig
        return sig

    def _initialize_file_types(self) -> None:
        """Initialize allowed file types."""
        # Documents
        self._add_file_type(
            extension=".pdf",
            mime_types=["application/pdf"],
            max_size_bytes=50 * 1024 * 1024,  # 50MB
            requires_deep_scan=True,
            description="PDF documents",
        )

        self._add_file_type(
            extension=".docx",
            mime_types=[
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ],
            max_size_bytes=25 * 1024 * 1024,
            requires_deep_scan=True,
            description="Word documents",
        )

        self._add_file_type(
            extension=".xlsx",
            mime_types=[
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ],
            max_size_bytes=25 * 1024 * 1024,
            requires_deep_scan=True,
            description="Excel spreadsheets",
        )

        # Images
        self._add_file_type(
            extension=".png",
            mime_types=["image/png"],
            max_size_bytes=10 * 1024 * 1024,
            requires_deep_scan=False,
            description="PNG images",
        )

        self._add_file_type(
            extension=".jpg",
            mime_types=["image/jpeg"],
            max_size_bytes=10 * 1024 * 1024,
            requires_deep_scan=False,
            description="JPEG images",
        )

        self._add_file_type(
            extension=".gif",
            mime_types=["image/gif"],
            max_size_bytes=5 * 1024 * 1024,
            requires_deep_scan=False,
            description="GIF images",
        )

        # Data files
        self._add_file_type(
            extension=".csv",
            mime_types=["text/csv"],
            max_size_bytes=100 * 1024 * 1024,
            requires_deep_scan=False,
            description="CSV data files",
        )

        self._add_file_type(
            extension=".json",
            mime_types=["application/json"],
            max_size_bytes=50 * 1024 * 1024,
            requires_deep_scan=False,
            description="JSON data files",
        )

        self._add_file_type(
            extension=".xml",
            mime_types=["application/xml", "text/xml"],
            max_size_bytes=50 * 1024 * 1024,
            requires_deep_scan=True,
            description="XML data files",
        )

        # Archives
        self._add_file_type(
            extension=".zip",
            mime_types=["application/zip"],
            max_size_bytes=100 * 1024 * 1024,
            requires_deep_scan=True,
            description="ZIP archives",
        )

    def _add_file_type(
        self,
        extension: str,
        mime_types: list[str],
        max_size_bytes: int,
        requires_deep_scan: bool,
        description: str,
    ) -> AllowedFileType:
        """Add an allowed file type."""
        ft = AllowedFileType(
            id=uuid4(),
            extension=extension,
            mime_types=mime_types,
            max_size_bytes=max_size_bytes,
            is_active=True,
            requires_deep_scan=requires_deep_scan,
            description=description,
        )

        self._file_types[ft.id] = ft
        return ft

    def _initialize_policies(self) -> None:
        """Initialize content policies."""
        now = datetime.now(timezone.utc)

        # Profanity/inappropriate content
        self._add_policy(
            name="Profanity Filter",
            description="Blocks common profanity",
            pattern=r"\b(damn|hell)\b",
            is_regex=True,
            category=ThreatCategory.POLICY_VIOLATION,
            action="warn",
            applies_to=[ContentType.COMMENT, ContentType.TEXT],
        )

        # External links
        self._add_policy(
            name="External Link Detection",
            description="Flags external URLs",
            pattern=r"https?://(?!.*\.company\.com)",
            is_regex=True,
            category=ThreatCategory.POLICY_VIOLATION,
            action="warn",
            applies_to=[ContentType.TEXT, ContentType.COMMENT],
        )

        # SQL injection patterns
        self._add_policy(
            name="SQL Injection Pattern",
            description="Detects SQL injection attempts",
            pattern=r"(?:union\s+select|;\s*drop\s+table|'\s*or\s+'1'\s*=\s*'1)",
            is_regex=True,
            category=ThreatCategory.SCRIPT,
            action="block",
            applies_to=[ContentType.FIELD_VALUE, ContentType.TEXT],
        )

    def _add_policy(
        self,
        name: str,
        description: str,
        pattern: str,
        is_regex: bool,
        category: ThreatCategory,
        action: str,
        applies_to: list[ContentType],
    ) -> ContentPolicy:
        """Add a content policy."""
        now = datetime.now(timezone.utc)

        policy = ContentPolicy(
            id=uuid4(),
            name=name,
            description=description,
            pattern=pattern,
            is_regex=is_regex,
            category=category,
            action=action,
            applies_to=applies_to,
            is_active=True,
            created_at=now,
        )

        self._policies[policy.id] = policy
        return policy

    # Signature Management

    def create_signature(
        self,
        name: str,
        category: ThreatCategory,
        pattern: str,
        is_regex: bool,
        description: str,
        severity: str,
    ) -> ThreatSignature:
        """Create a new threat signature."""
        return self._add_signature(
            name=name,
            category=category,
            pattern=pattern,
            is_regex=is_regex,
            description=description,
            severity=severity,
        )

    def get_signature(self, signature_id: UUID) -> ThreatSignature | None:
        """Get a signature by ID."""
        return self._signatures.get(signature_id)

    def get_signatures(
        self,
        category: ThreatCategory | None = None,
        severity: str | None = None,
        active_only: bool = True,
    ) -> list[ThreatSignature]:
        """Get signatures with optional filters."""
        sigs = []

        for sig in self._signatures.values():
            if active_only and not sig.is_active:
                continue
            if category and sig.category != category:
                continue
            if severity and sig.severity != severity:
                continue
            sigs.append(sig)

        return sigs

    def update_signature(
        self,
        signature_id: UUID,
        pattern: str | None = None,
        is_active: bool | None = None,
        severity: str | None = None,
    ) -> ThreatSignature | None:
        """Update a signature."""
        sig = self._signatures.get(signature_id)
        if not sig:
            return None

        if pattern is not None:
            sig.pattern = pattern
        if is_active is not None:
            sig.is_active = is_active
        if severity is not None:
            sig.severity = severity

        sig.updated_at = datetime.now(timezone.utc)
        return sig

    def delete_signature(self, signature_id: UUID) -> bool:
        """Delete a signature."""
        if signature_id in self._signatures:
            del self._signatures[signature_id]
            return True
        return False

    # File Type Management

    def add_file_type(
        self,
        extension: str,
        mime_types: list[str],
        max_size_bytes: int,
        requires_deep_scan: bool = False,
        description: str = "",
    ) -> AllowedFileType:
        """Add an allowed file type."""
        return self._add_file_type(
            extension=extension,
            mime_types=mime_types,
            max_size_bytes=max_size_bytes,
            requires_deep_scan=requires_deep_scan,
            description=description,
        )

    def get_file_type(self, file_type_id: UUID) -> AllowedFileType | None:
        """Get a file type by ID."""
        return self._file_types.get(file_type_id)

    def get_file_type_by_extension(self, extension: str) -> AllowedFileType | None:
        """Get a file type by extension."""
        ext = extension if extension.startswith(".") else f".{extension}"

        for ft in self._file_types.values():
            if ft.extension == ext and ft.is_active:
                return ft

        return None

    def get_file_types(self, active_only: bool = True) -> list[AllowedFileType]:
        """Get all file types."""
        if active_only:
            return [ft for ft in self._file_types.values() if ft.is_active]
        return list(self._file_types.values())

    def is_file_type_allowed(self, extension: str) -> bool:
        """Check if a file type is allowed."""
        ft = self.get_file_type_by_extension(extension)
        return ft is not None and ft.is_active

    def remove_file_type(self, file_type_id: UUID) -> bool:
        """Remove a file type."""
        if file_type_id in self._file_types:
            del self._file_types[file_type_id]
            return True
        return False

    # Policy Management

    def create_policy(
        self,
        name: str,
        description: str,
        pattern: str,
        is_regex: bool,
        category: ThreatCategory,
        action: str,
        applies_to: list[ContentType],
    ) -> ContentPolicy:
        """Create a content policy."""
        return self._add_policy(
            name=name,
            description=description,
            pattern=pattern,
            is_regex=is_regex,
            category=category,
            action=action,
            applies_to=applies_to,
        )

    def get_policy(self, policy_id: UUID) -> ContentPolicy | None:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def get_policies(
        self,
        category: ThreatCategory | None = None,
        content_type: ContentType | None = None,
        active_only: bool = True,
    ) -> list[ContentPolicy]:
        """Get policies with optional filters."""
        policies = []

        for policy in self._policies.values():
            if active_only and not policy.is_active:
                continue
            if category and policy.category != category:
                continue
            if content_type and content_type not in policy.applies_to:
                continue
            policies.append(policy)

        return policies

    def delete_policy(self, policy_id: UUID) -> bool:
        """Delete a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    # Scanning Operations

    def scan_file(
        self,
        filename: str,
        content: bytes,
        scan_mode: ScanMode = ScanMode.STANDARD,
        scanned_by: UUID | None = None,
    ) -> ScanReport:
        """Scan a file for threats."""
        import time

        start_time = time.time()
        findings: list[ScanFinding] = []

        # Calculate hash
        content_hash = hashlib.sha256(content).hexdigest()

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(filename)

        # Get extension
        extension = ""
        if "." in filename:
            extension = "." + filename.rsplit(".", 1)[1].lower()

        # Check file type
        file_type = self.get_file_type_by_extension(extension)
        if not file_type:
            findings.append(
                ScanFinding(
                    category=ThreatCategory.INVALID_TYPE,
                    signature_id=None,
                    policy_id=None,
                    description=f"File type '{extension}' is not allowed",
                    severity="high",
                    location=None,
                    matched_content=None,
                )
            )

        # Check file size
        if file_type and len(content) > file_type.max_size_bytes:
            findings.append(
                ScanFinding(
                    category=ThreatCategory.SIZE_EXCEEDED,
                    signature_id=None,
                    policy_id=None,
                    description=f"File size {len(content)} exceeds limit {file_type.max_size_bytes}",
                    severity="medium",
                    location=None,
                    matched_content=None,
                )
            )

        # Scan content with signatures
        content_str = self._safe_decode(content)
        content_hex = content[:100].hex().upper()  # First 100 bytes as hex

        for sig in self._signatures.values():
            if not sig.is_active:
                continue

            match: re.Match[str] | bool | None = None
            if sig.is_regex:
                try:
                    pattern = re.compile(sig.pattern, re.IGNORECASE)
                    match = pattern.search(content_str)
                except re.error:
                    continue
            else:
                # Check for hex pattern (binary signatures)
                if sig.pattern in content_hex:
                    match = True

            if match:
                findings.append(
                    ScanFinding(
                        category=sig.category,
                        signature_id=sig.id,
                        policy_id=None,
                        description=sig.description,
                        severity=sig.severity,
                        location="file content",
                        matched_content=sig.name,
                    )
                )

        # Determine result
        result = self._determine_result(findings)
        scan_duration = (time.time() - start_time) * 1000

        report = ScanReport(
            id=uuid4(),
            content_type=ContentType.FILE,
            content_hash=content_hash,
            content_size=len(content),
            filename=filename,
            mime_type=mime_type,
            scan_mode=scan_mode,
            result=result,
            findings=findings,
            scanned_at=datetime.now(timezone.utc),
            scan_duration_ms=scan_duration,
            scanned_by=scanned_by,
            metadata={
                "extension": extension,
                "file_type_allowed": file_type is not None,
            },
        )

        self._reports[report.id] = report
        return report

    def scan_text(
        self,
        text: str,
        content_type: ContentType = ContentType.TEXT,
        scanned_by: UUID | None = None,
    ) -> ScanReport:
        """Scan text content for threats and policy violations."""
        import time

        start_time = time.time()
        findings: list[ScanFinding] = []

        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # Check signatures
        for sig in self._signatures.values():
            if not sig.is_active or not sig.is_regex:
                continue

            try:
                pattern = re.compile(sig.pattern, re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    findings.append(
                        ScanFinding(
                            category=sig.category,
                            signature_id=sig.id,
                            policy_id=None,
                            description=sig.description,
                            severity=sig.severity,
                            location="text content",
                            matched_content=match.group()[:50],
                        )
                    )
            except re.error:
                continue

        # Check policies
        for policy in self._policies.values():
            if not policy.is_active:
                continue
            if content_type not in policy.applies_to:
                continue

            try:
                if policy.is_regex:
                    pattern = re.compile(policy.pattern, re.IGNORECASE)
                    policy_match: re.Match[str] | bool | None = pattern.search(text)
                else:
                    policy_match = policy.pattern.lower() in text.lower()

                if policy_match:
                    matched = policy_match.group()[:50] if isinstance(policy_match, re.Match) else policy.pattern
                    findings.append(
                        ScanFinding(
                            category=policy.category,
                            signature_id=None,
                            policy_id=policy.id,
                            description=policy.description,
                            severity="medium" if policy.action == "warn" else "high",
                            location="text content",
                            matched_content=matched,
                        )
                    )
            except re.error:
                continue

        result = self._determine_result(findings)
        scan_duration = (time.time() - start_time) * 1000

        report = ScanReport(
            id=uuid4(),
            content_type=content_type,
            content_hash=content_hash,
            content_size=len(text),
            filename=None,
            mime_type="text/plain",
            scan_mode=ScanMode.QUICK,
            result=result,
            findings=findings,
            scanned_at=datetime.now(timezone.utc),
            scan_duration_ms=scan_duration,
            scanned_by=scanned_by,
            metadata={},
        )

        self._reports[report.id] = report
        return report

    def scan_url(
        self,
        url: str,
        scanned_by: UUID | None = None,
    ) -> ScanReport:
        """Scan a URL for threats."""
        import time

        start_time = time.time()
        findings: list[ScanFinding] = []

        content_hash = hashlib.sha256(url.encode()).hexdigest()

        # Check for suspicious patterns
        suspicious_patterns = [
            (r"@", "URL contains @ symbol (potential spoofing)"),
            (r"[^\x00-\x7F]", "URL contains non-ASCII characters"),
            (r"\.exe$|\.bat$|\.cmd$", "URL points to executable file"),
            (r"data:", "Data URL detected"),
            (r"javascript:", "JavaScript URL detected"),
        ]

        for pattern, desc in suspicious_patterns:
            try:
                if re.search(pattern, url, re.IGNORECASE):
                    findings.append(
                        ScanFinding(
                            category=ThreatCategory.PHISHING,
                            signature_id=None,
                            policy_id=None,
                            description=desc,
                            severity="high",
                            location="url",
                            matched_content=url[:100],
                        )
                    )
            except re.error:
                continue

        result = self._determine_result(findings)
        scan_duration = (time.time() - start_time) * 1000

        report = ScanReport(
            id=uuid4(),
            content_type=ContentType.URL,
            content_hash=content_hash,
            content_size=len(url),
            filename=None,
            mime_type=None,
            scan_mode=ScanMode.QUICK,
            result=result,
            findings=findings,
            scanned_at=datetime.now(timezone.utc),
            scan_duration_ms=scan_duration,
            scanned_by=scanned_by,
            metadata={"url": url},
        )

        self._reports[report.id] = report
        return report

    def _safe_decode(self, content: bytes) -> str:
        """Safely decode bytes to string."""
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return content.decode("latin-1")
            except UnicodeDecodeError:
                return ""

    def _determine_result(self, findings: list[ScanFinding]) -> ScanResult:
        """Determine scan result based on findings."""
        if not findings:
            return ScanResult.CLEAN

        # Check severity levels
        severities = [f.severity for f in findings]

        if "critical" in severities:
            return ScanResult.BLOCKED
        if "high" in severities:
            return ScanResult.QUARANTINED
        if "medium" in severities:
            return ScanResult.SUSPICIOUS

        return ScanResult.SUSPICIOUS

    # Report Management

    def get_report(self, report_id: UUID) -> ScanReport | None:
        """Get a scan report by ID."""
        return self._reports.get(report_id)

    def get_reports(
        self,
        result: ScanResult | None = None,
        content_type: ContentType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[ScanReport]:
        """Get scan reports with optional filters."""
        reports = []

        for report in self._reports.values():
            if result and report.result != result:
                continue
            if content_type and report.content_type != content_type:
                continue
            if start_date and report.scanned_at < start_date:
                continue
            if end_date and report.scanned_at > end_date:
                continue
            reports.append(report)

        # Sort by most recent
        reports.sort(key=lambda r: r.scanned_at, reverse=True)

        return reports[:limit]

    def get_report_by_hash(self, content_hash: str) -> ScanReport | None:
        """Get the most recent scan report for a content hash."""
        matching = [r for r in self._reports.values() if r.content_hash == content_hash]
        if matching:
            matching.sort(key=lambda r: r.scanned_at, reverse=True)
            return matching[0]
        return None

    # Quarantine Management

    def quarantine_content(
        self,
        scan_report_id: UUID,
        quarantined_by: UUID,
        original_path: str | None = None,
    ) -> QuarantineEntry | None:
        """Add content to quarantine."""
        report = self._reports.get(scan_report_id)
        if not report:
            return None

        entry = QuarantineEntry(
            id=uuid4(),
            scan_report_id=scan_report_id,
            content_hash=report.content_hash,
            filename=report.filename,
            original_path=original_path,
            quarantined_at=datetime.now(timezone.utc),
            quarantined_by=quarantined_by,
            reason=", ".join(f.description for f in report.findings[:3]),
            release_status="quarantined",
            released_at=None,
            released_by=None,
        )

        self._quarantine[entry.id] = entry
        return entry

    def release_from_quarantine(
        self,
        quarantine_id: UUID,
        released_by: UUID,
    ) -> QuarantineEntry | None:
        """Release content from quarantine."""
        entry = self._quarantine.get(quarantine_id)
        if not entry:
            return None

        entry.release_status = "released"
        entry.released_at = datetime.now(timezone.utc)
        entry.released_by = released_by

        return entry

    def delete_quarantined(self, quarantine_id: UUID) -> bool:
        """Permanently delete quarantined content."""
        entry = self._quarantine.get(quarantine_id)
        if not entry:
            return False

        entry.release_status = "deleted"
        return True

    def get_quarantine_entry(self, quarantine_id: UUID) -> QuarantineEntry | None:
        """Get a quarantine entry."""
        return self._quarantine.get(quarantine_id)

    def get_quarantine_entries(
        self,
        status: str | None = None,
    ) -> list[QuarantineEntry]:
        """Get quarantine entries."""
        entries = []

        for entry in self._quarantine.values():
            if status and entry.release_status != status:
                continue
            entries.append(entry)

        return entries

    # Statistics

    def get_summary(self) -> dict[str, Any]:
        """Get scanning summary statistics."""
        by_result: dict[str, int] = {}
        by_category: dict[str, int] = {}
        total_findings = 0

        for report in self._reports.values():
            result = report.result.value
            by_result[result] = by_result.get(result, 0) + 1

            for finding in report.findings:
                category = finding.category.value
                by_category[category] = by_category.get(category, 0) + 1
                total_findings += 1

        return {
            "total_scans": len(self._reports),
            "total_signatures": len(self._signatures),
            "total_policies": len(self._policies),
            "allowed_file_types": len([ft for ft in self._file_types.values() if ft.is_active]),
            "quarantined_items": len(
                [e for e in self._quarantine.values() if e.release_status == "quarantined"]
            ),
            "by_result": by_result,
            "by_category": by_category,
            "total_findings": total_findings,
        }

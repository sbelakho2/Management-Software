"""
Tests for Content Scanning Service.

Verifies:
- Default signatures and file types
- Signature CRUD operations
- File type management
- Policy management
- File scanning
- Text scanning
- URL scanning
- Quarantine management
- Reporting
"""

from uuid import uuid4

import pytest

from sensei.services.content_scanning import (
    ContentPolicy,
    ContentScanningService,
    ContentType,
    ScanMode,
    ScanResult,
    ThreatCategory,
)


class TestDefaultSignatures:
    """Tests for default signature initialization."""

    def test_default_signatures_exist(self) -> None:
        """Test that default signatures are created."""
        service = ContentScanningService()

        signatures = service.get_signatures()

        assert len(signatures) > 0

    def test_script_signatures_exist(self) -> None:
        """Test that script detection signatures exist."""
        service = ContentScanningService()

        script_sigs = service.get_signatures(category=ThreatCategory.SCRIPT)

        assert len(script_sigs) > 0

    def test_phishing_signatures_exist(self) -> None:
        """Test that phishing detection signatures exist."""
        service = ContentScanningService()

        phishing_sigs = service.get_signatures(category=ThreatCategory.PHISHING)

        assert len(phishing_sigs) > 0

    def test_sensitive_data_signatures_exist(self) -> None:
        """Test that sensitive data signatures exist."""
        service = ContentScanningService()

        sensitive_sigs = service.get_signatures(category=ThreatCategory.SENSITIVE_DATA)

        assert len(sensitive_sigs) > 0


class TestSignatureManagement:
    """Tests for signature CRUD operations."""

    def test_create_signature(self) -> None:
        """Test creating a signature."""
        service = ContentScanningService()

        sig = service.create_signature(
            name="Custom Pattern",
            category=ThreatCategory.MALWARE,
            pattern=r"custom_malware_pattern",
            is_regex=True,
            description="Custom malware pattern",
            severity="high",
        )

        assert sig.id is not None
        assert sig.name == "Custom Pattern"
        assert sig.is_active is True

    def test_get_signature(self) -> None:
        """Test getting a signature by ID."""
        service = ContentScanningService()

        sigs = service.get_signatures()
        sig_id = sigs[0].id

        retrieved = service.get_signature(sig_id)

        assert retrieved is not None
        assert retrieved.id == sig_id

    def test_filter_by_category(self) -> None:
        """Test filtering signatures by category."""
        service = ContentScanningService()

        script_sigs = service.get_signatures(category=ThreatCategory.SCRIPT)

        assert all(s.category == ThreatCategory.SCRIPT for s in script_sigs)

    def test_filter_by_severity(self) -> None:
        """Test filtering signatures by severity."""
        service = ContentScanningService()

        high_sigs = service.get_signatures(severity="high")

        assert all(s.severity == "high" for s in high_sigs)

    def test_update_signature(self) -> None:
        """Test updating a signature."""
        service = ContentScanningService()

        sigs = service.get_signatures()
        sig_id = sigs[0].id

        updated = service.update_signature(
            sig_id,
            severity="critical",
            is_active=False,
        )

        assert updated is not None
        assert updated.severity == "critical"
        assert updated.is_active is False

    def test_delete_signature(self) -> None:
        """Test deleting a signature."""
        service = ContentScanningService()

        sig = service.create_signature(
            name="To Delete",
            category=ThreatCategory.MALWARE,
            pattern="delete_me",
            is_regex=False,
            description="Test",
            severity="low",
        )

        result = service.delete_signature(sig.id)

        assert result is True
        assert service.get_signature(sig.id) is None


class TestFileTypeManagement:
    """Tests for file type management."""

    def test_default_file_types_exist(self) -> None:
        """Test that default file types are created."""
        service = ContentScanningService()

        file_types = service.get_file_types()

        assert len(file_types) > 0

    def test_add_file_type(self) -> None:
        """Test adding a file type."""
        service = ContentScanningService()

        ft = service.add_file_type(
            extension=".custom",
            mime_types=["application/custom"],
            max_size_bytes=10 * 1024 * 1024,
            requires_deep_scan=True,
            description="Custom file type",
        )

        assert ft.id is not None
        assert ft.extension == ".custom"

    def test_get_file_type_by_extension(self) -> None:
        """Test getting file type by extension."""
        service = ContentScanningService()

        pdf_type = service.get_file_type_by_extension(".pdf")

        assert pdf_type is not None
        assert pdf_type.extension == ".pdf"

    def test_get_file_type_without_dot(self) -> None:
        """Test getting file type without leading dot."""
        service = ContentScanningService()

        pdf_type = service.get_file_type_by_extension("pdf")

        assert pdf_type is not None

    def test_is_file_type_allowed(self) -> None:
        """Test checking if file type is allowed."""
        service = ContentScanningService()

        assert service.is_file_type_allowed(".pdf") is True
        assert service.is_file_type_allowed(".exe") is False

    def test_remove_file_type(self) -> None:
        """Test removing a file type."""
        service = ContentScanningService()

        ft = service.add_file_type(
            extension=".temp",
            mime_types=["application/temp"],
            max_size_bytes=1024,
        )

        result = service.remove_file_type(ft.id)

        assert result is True


class TestPolicyManagement:
    """Tests for content policy management."""

    def test_default_policies_exist(self) -> None:
        """Test that default policies are created."""
        service = ContentScanningService()

        policies = service.get_policies()

        assert len(policies) > 0

    def test_create_policy(self) -> None:
        """Test creating a policy."""
        service = ContentScanningService()

        policy = service.create_policy(
            name="Custom Policy",
            description="Test policy",
            pattern=r"test_pattern",
            is_regex=True,
            category=ThreatCategory.POLICY_VIOLATION,
            action="block",
            applies_to=[ContentType.TEXT, ContentType.COMMENT],
        )

        assert policy.id is not None
        assert policy.action == "block"

    def test_get_policy(self) -> None:
        """Test getting a policy by ID."""
        service = ContentScanningService()

        policies = service.get_policies()
        policy_id = policies[0].id

        retrieved = service.get_policy(policy_id)

        assert retrieved is not None

    def test_filter_policies_by_content_type(self) -> None:
        """Test filtering policies by content type."""
        service = ContentScanningService()

        text_policies = service.get_policies(content_type=ContentType.TEXT)

        assert len(text_policies) > 0
        assert all(ContentType.TEXT in p.applies_to for p in text_policies)

    def test_delete_policy(self) -> None:
        """Test deleting a policy."""
        service = ContentScanningService()

        policy = service.create_policy(
            name="To Delete",
            description="Test",
            pattern="test",
            is_regex=False,
            category=ThreatCategory.POLICY_VIOLATION,
            action="warn",
            applies_to=[ContentType.TEXT],
        )

        result = service.delete_policy(policy.id)

        assert result is True


class TestFileScanning:
    """Tests for file scanning."""

    def test_scan_clean_file(self) -> None:
        """Test scanning a clean file."""
        service = ContentScanningService()

        content = b"This is a clean PDF file content"
        report = service.scan_file("document.pdf", content)

        # May have findings for not being actual PDF
        assert report.id is not None
        assert report.content_type == ContentType.FILE

    def test_scan_file_with_script(self) -> None:
        """Test scanning file with script."""
        service = ContentScanningService()

        content = b"<script>alert('xss')</script>"
        report = service.scan_file("page.html", content)

        assert report.result in [ScanResult.SUSPICIOUS, ScanResult.QUARANTINED, ScanResult.BLOCKED]
        assert len(report.findings) > 0

    def test_scan_disallowed_file_type(self) -> None:
        """Test scanning disallowed file type."""
        service = ContentScanningService()

        content = b"Binary executable content"
        report = service.scan_file("program.exe", content)

        assert any(f.category == ThreatCategory.INVALID_TYPE for f in report.findings)

    def test_scan_oversized_file(self) -> None:
        """Test scanning oversized file."""
        service = ContentScanningService()

        # Get PDF limit
        pdf_type = service.get_file_type_by_extension(".pdf")

        # Create content larger than limit
        content = b"x" * (pdf_type.max_size_bytes + 1)
        report = service.scan_file("large.pdf", content)

        assert any(f.category == ThreatCategory.SIZE_EXCEEDED for f in report.findings)

    def test_scan_with_binary_signature(self) -> None:
        """Test scanning file with PE signature."""
        service = ContentScanningService()

        # MZ header (Windows PE)
        content = b"MZ" + b"\x00" * 100
        report = service.scan_file("suspicious.dat", content)

        # Should detect PE executable
        assert report.result in [ScanResult.BLOCKED, ScanResult.QUARANTINED]

    def test_scan_mode_recorded(self) -> None:
        """Test that scan mode is recorded."""
        service = ContentScanningService()

        content = b"Test content"
        report = service.scan_file(
            "test.pdf", content, scan_mode=ScanMode.DEEP
        )

        assert report.scan_mode == ScanMode.DEEP


class TestTextScanning:
    """Tests for text scanning."""

    def test_scan_clean_text(self) -> None:
        """Test scanning clean text."""
        service = ContentScanningService()

        report = service.scan_text("This is a normal comment.")

        assert report.result == ScanResult.CLEAN
        assert len(report.findings) == 0

    def test_scan_text_with_script(self) -> None:
        """Test scanning text with script injection."""
        service = ContentScanningService()

        text = "Check out this: <script>steal_cookies()</script>"
        report = service.scan_text(text)

        assert report.result != ScanResult.CLEAN
        assert any(f.category == ThreatCategory.SCRIPT for f in report.findings)

    def test_scan_text_with_phishing(self) -> None:
        """Test scanning text with phishing content."""
        service = ContentScanningService()

        text = "Please enter your password to verify your account"
        report = service.scan_text(text)

        assert any(f.category == ThreatCategory.PHISHING for f in report.findings)

    def test_scan_text_with_credit_card(self) -> None:
        """Test scanning text with credit card number."""
        service = ContentScanningService()

        text = "My card number is 4111-1111-1111-1111"
        report = service.scan_text(text)

        assert any(f.category == ThreatCategory.SENSITIVE_DATA for f in report.findings)

    def test_scan_text_with_ssn(self) -> None:
        """Test scanning text with SSN."""
        service = ContentScanningService()

        text = "SSN: 123-45-6789"
        report = service.scan_text(text)

        assert any(f.category == ThreatCategory.SENSITIVE_DATA for f in report.findings)

    def test_scan_text_applies_policies(self) -> None:
        """Test that text scanning applies policies."""
        service = ContentScanningService()

        # SQL injection pattern
        text = "'; DROP TABLE users; --"
        report = service.scan_text(text, content_type=ContentType.FIELD_VALUE)

        assert report.result != ScanResult.CLEAN

    def test_scan_comment_type(self) -> None:
        """Test scanning comment content type."""
        service = ContentScanningService()

        report = service.scan_text(
            "Great work!", content_type=ContentType.COMMENT
        )

        assert report.content_type == ContentType.COMMENT


class TestURLScanning:
    """Tests for URL scanning."""

    def test_scan_clean_url(self) -> None:
        """Test scanning a clean URL."""
        service = ContentScanningService()

        report = service.scan_url("https://example.com/page")

        assert report.result == ScanResult.CLEAN

    def test_scan_url_with_at_symbol(self) -> None:
        """Test scanning URL with @ symbol."""
        service = ContentScanningService()

        report = service.scan_url("https://fake@evil.com")

        assert report.result != ScanResult.CLEAN
        assert len(report.findings) > 0

    def test_scan_javascript_url(self) -> None:
        """Test scanning javascript: URL."""
        service = ContentScanningService()

        report = service.scan_url("javascript:alert('xss')")

        assert report.result != ScanResult.CLEAN

    def test_scan_data_url(self) -> None:
        """Test scanning data: URL."""
        service = ContentScanningService()

        report = service.scan_url("data:text/html,<script>alert(1)</script>")

        assert report.result != ScanResult.CLEAN

    def test_scan_url_to_executable(self) -> None:
        """Test scanning URL pointing to executable."""
        service = ContentScanningService()

        report = service.scan_url("https://example.com/malware.exe")

        assert report.result != ScanResult.CLEAN


class TestReportManagement:
    """Tests for scan report management."""

    def test_get_report(self) -> None:
        """Test getting a report by ID."""
        service = ContentScanningService()

        original = service.scan_text("Test content")
        retrieved = service.get_report(original.id)

        assert retrieved is not None
        assert retrieved.id == original.id

    def test_get_reports_by_result(self) -> None:
        """Test getting reports by result."""
        service = ContentScanningService()

        service.scan_text("Clean content")
        service.scan_text("<script>bad</script>")

        clean_reports = service.get_reports(result=ScanResult.CLEAN)

        assert all(r.result == ScanResult.CLEAN for r in clean_reports)

    def test_get_reports_by_content_type(self) -> None:
        """Test getting reports by content type."""
        service = ContentScanningService()

        service.scan_text("Text content")
        service.scan_url("https://example.com")

        url_reports = service.get_reports(content_type=ContentType.URL)

        assert all(r.content_type == ContentType.URL for r in url_reports)

    def test_get_report_by_hash(self) -> None:
        """Test getting report by content hash."""
        service = ContentScanningService()

        report = service.scan_text("Unique content for hash test")
        retrieved = service.get_report_by_hash(report.content_hash)

        assert retrieved is not None
        assert retrieved.content_hash == report.content_hash


class TestQuarantine:
    """Tests for quarantine management."""

    def test_quarantine_content(self) -> None:
        """Test quarantining content."""
        service = ContentScanningService()
        user_id = uuid4()

        report = service.scan_text("<script>malware</script>")
        entry = service.quarantine_content(
            report.id, user_id, original_path="/uploads/file.html"
        )

        assert entry is not None
        assert entry.release_status == "quarantined"

    def test_release_from_quarantine(self) -> None:
        """Test releasing from quarantine."""
        service = ContentScanningService()
        user_id = uuid4()
        releaser_id = uuid4()

        report = service.scan_text("<script>test</script>")
        entry = service.quarantine_content(report.id, user_id)

        released = service.release_from_quarantine(entry.id, releaser_id)

        assert released is not None
        assert released.release_status == "released"
        assert released.released_by == releaser_id

    def test_delete_quarantined(self) -> None:
        """Test deleting quarantined content."""
        service = ContentScanningService()
        user_id = uuid4()

        report = service.scan_text("<script>bad</script>")
        entry = service.quarantine_content(report.id, user_id)

        result = service.delete_quarantined(entry.id)

        assert result is True
        updated = service.get_quarantine_entry(entry.id)
        assert updated.release_status == "deleted"

    def test_get_quarantine_entries(self) -> None:
        """Test getting quarantine entries."""
        service = ContentScanningService()
        user_id = uuid4()

        report = service.scan_text("<script>test</script>")
        service.quarantine_content(report.id, user_id)

        entries = service.get_quarantine_entries(status="quarantined")

        assert len(entries) > 0
        assert all(e.release_status == "quarantined" for e in entries)


class TestSummary:
    """Tests for summary statistics."""

    def test_get_summary(self) -> None:
        """Test getting summary."""
        service = ContentScanningService()

        # Perform some scans
        service.scan_text("Clean content")
        service.scan_text("<script>bad</script>")

        summary = service.get_summary()

        assert "total_scans" in summary
        assert "total_signatures" in summary
        assert "by_result" in summary
        assert summary["total_scans"] >= 2


class TestEdgeCases:
    """Tests for edge cases."""

    def test_get_nonexistent_signature(self) -> None:
        """Test getting non-existent signature."""
        service = ContentScanningService()

        result = service.get_signature(uuid4())

        assert result is None

    def test_update_nonexistent_signature(self) -> None:
        """Test updating non-existent signature."""
        service = ContentScanningService()

        result = service.update_signature(uuid4(), severity="high")

        assert result is None

    def test_delete_nonexistent_signature(self) -> None:
        """Test deleting non-existent signature."""
        service = ContentScanningService()

        result = service.delete_signature(uuid4())

        assert result is False

    def test_get_nonexistent_file_type(self) -> None:
        """Test getting non-existent file type."""
        service = ContentScanningService()

        result = service.get_file_type(uuid4())

        assert result is None

    def test_get_nonexistent_policy(self) -> None:
        """Test getting non-existent policy."""
        service = ContentScanningService()

        result = service.get_policy(uuid4())

        assert result is None

    def test_delete_nonexistent_policy(self) -> None:
        """Test deleting non-existent policy."""
        service = ContentScanningService()

        result = service.delete_policy(uuid4())

        assert result is False

    def test_get_nonexistent_report(self) -> None:
        """Test getting non-existent report."""
        service = ContentScanningService()

        result = service.get_report(uuid4())

        assert result is None

    def test_quarantine_nonexistent_report(self) -> None:
        """Test quarantining non-existent report."""
        service = ContentScanningService()

        result = service.quarantine_content(uuid4(), uuid4())

        assert result is None

    def test_release_nonexistent_quarantine(self) -> None:
        """Test releasing non-existent quarantine."""
        service = ContentScanningService()

        result = service.release_from_quarantine(uuid4(), uuid4())

        assert result is None

    def test_delete_nonexistent_quarantine(self) -> None:
        """Test deleting non-existent quarantine."""
        service = ContentScanningService()

        result = service.delete_quarantined(uuid4())

        assert result is False

    def test_scan_empty_content(self) -> None:
        """Test scanning empty content."""
        service = ContentScanningService()

        report = service.scan_text("")

        assert report is not None
        assert report.result == ScanResult.CLEAN

    def test_scan_binary_content(self) -> None:
        """Test scanning binary content."""
        service = ContentScanningService()

        content = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
        report = service.scan_file("binary.dat", content)

        assert report is not None

    def test_get_report_by_unknown_hash(self) -> None:
        """Test getting report by unknown hash."""
        service = ContentScanningService()

        result = service.get_report_by_hash("unknown_hash_value")

        assert result is None

"""
Tests for Knowledge Pack Ingestion Service.
"""

import hashlib
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from sensei.models.knowledge_pack import (
    LicenseType,
    ContentFormat,
    TaxonomyTag,
    KnowledgeDocument,
    KnowledgeChunk,
)
from sensei.services.knowledge_ingestion import (
    LicenseVerifier,
    ContentFetcher,
    ContentNormalizer,
    SemanticChunker,
    QualityFilter,
    TaxonomyTagger,
    KnowledgePackIngestionService,
)


class TestLicenseVerifier:
    """Test license verification functionality."""
    
    def test_detect_cc0_from_url(self):
        """Should detect CC0 license from URL."""
        url = "https://creativecommons.org/publicdomain/zero/1.0/"
        license_type = LicenseVerifier.detect_license("", url)
        
        assert license_type == LicenseType.CC0
    
    def test_detect_cc_by_from_url(self):
        """Should detect CC BY license from URL."""
        url = "https://creativecommons.org/licenses/by/4.0/"
        license_type = LicenseVerifier.detect_license("", url)
        
        assert license_type == LicenseType.CC_BY
    
    def test_detect_cc_by_sa_from_url(self):
        """Should detect CC BY-SA license from URL."""
        url = "https://creativecommons.org/licenses/by-sa/4.0/"
        license_type = LicenseVerifier.detect_license("", url)
        
        assert license_type == LicenseType.CC_BY_SA
    
    def test_detect_mit_from_text(self):
        """Should detect MIT license from text."""
        text = "This project is licensed under the MIT License"
        license_type = LicenseVerifier.detect_license(text, None)
        
        assert license_type == LicenseType.MIT
    
    def test_detect_apache_from_text(self):
        """Should detect Apache 2.0 license from text."""
        text = "Licensed under the Apache License, Version 2.0"
        license_type = LicenseVerifier.detect_license(text, None)
        
        assert license_type == LicenseType.APACHE_2
    
    def test_detect_public_domain_from_text(self):
        """Should detect public domain from text."""
        text = "This work is in the public domain"
        license_type = LicenseVerifier.detect_license(text, None)
        
        assert license_type == LicenseType.PUBLIC_DOMAIN
    
    def test_unrecognized_license_returns_none(self):
        """Should return None for unrecognized licenses."""
        text = "All rights reserved"
        license_type = LicenseVerifier.detect_license(text, None)
        
        assert license_type is None
    
    def test_is_allowed_license_with_valid_license(self):
        """Should allow valid open licenses."""
        assert LicenseVerifier.is_allowed_license(LicenseType.CC_BY)
        assert LicenseVerifier.is_allowed_license(LicenseType.MIT)
        assert LicenseVerifier.is_allowed_license(LicenseType.APACHE_2)
    
    def test_is_allowed_license_with_none(self):
        """Should not allow None license."""
        assert not LicenseVerifier.is_allowed_license(None)
    
    def test_generate_attribution_with_author(self):
        """Should generate attribution with author."""
        attribution = LicenseVerifier.generate_attribution(
            "Test Document",
            "John Doe",
            "https://example.com",
            LicenseType.CC_BY,
        )
        
        assert "Test Document" in attribution
        assert "John Doe" in attribution
        assert "https://example.com" in attribution
        assert "CC BY" in attribution
    
    def test_generate_attribution_without_author(self):
        """Should generate attribution without author."""
        attribution = LicenseVerifier.generate_attribution(
            "Test Document",
            None,
            "https://example.com",
            LicenseType.MIT,
        )
        
        assert "Test Document" in attribution
        assert "https://example.com" in attribution
        assert "MIT" in attribution


class TestContentNormalizer:
    """Test content normalization functionality."""
    
    def test_normalize_html_removes_scripts(self):
        """Should remove script tags from HTML."""
        html = "<html><body><p>Content</p><script>alert('test')</script></body></html>"
        normalized = ContentNormalizer.normalize_html(html)
        
        assert "Content" in normalized
        assert "script" not in normalized.lower()
        assert "alert" not in normalized
    
    def test_normalize_html_preserves_headings(self):
        """Should preserve heading structure."""
        html = "<html><body><h1>Title</h1><p>Content</p><h2>Subtitle</h2></body></html>"
        normalized = ContentNormalizer.normalize_html(html)
        
        assert "# Title" in normalized
        assert "## Subtitle" in normalized
        assert "Content" in normalized
    
    def test_normalize_html_handles_paragraphs(self):
        """Should extract paragraph text."""
        html = "<html><body><p>Paragraph 1</p><p>Paragraph 2</p></body></html>"
        normalized = ContentNormalizer.normalize_html(html)
        
        assert "Paragraph 1" in normalized
        assert "Paragraph 2" in normalized
    
    def test_normalize_markdown_removes_html(self):
        """Should remove HTML tags from markdown."""
        markdown = "# Title\n\n<div>Content</div>\n\nMore content"
        normalized = ContentNormalizer.normalize_markdown(markdown)
        
        assert "# Title" in normalized
        assert "Content" in normalized
        assert "<div>" not in normalized
    
    def test_normalize_markdown_preserves_structure(self):
        """Should preserve markdown structure."""
        markdown = "# Title\n\n## Subtitle\n\nContent paragraph"
        normalized = ContentNormalizer.normalize_markdown(markdown)
        
        assert "# Title" in normalized
        assert "## Subtitle" in normalized
        assert "Content paragraph" in normalized
    
    def test_normalize_plain_text_cleans_whitespace(self):
        """Should normalize whitespace in plain text."""
        text = "Line 1\n\n\n\nLine 2   with   spaces"
        normalized = ContentNormalizer.normalize_plain_text(text)
        
        assert "Line 1" in normalized
        assert "Line 2 with spaces" in normalized
        assert "\n\n\n" not in normalized


class TestSemanticChunker:
    """Test semantic chunking functionality."""
    
    def test_chunk_short_document(self):
        """Should chunk short document without splitting."""
        chunker = SemanticChunker(max_chunk_size=100)
        text = "# Title\n\nShort content"
        
        chunks = chunker.chunk_document(text)
        
        assert len(chunks) == 1
        assert chunks[0]["chunk_text"].strip() == "Short content"
        assert chunks[0]["heading"] == "Title"
    
    def test_chunk_document_with_multiple_headings(self):
        """Should create chunks for each heading section."""
        chunker = SemanticChunker(max_chunk_size=100)
        text = "# Title 1\n\nContent 1\n\n# Title 2\n\nContent 2"
        
        chunks = chunker.chunk_document(text)
        
        assert len(chunks) == 2
        assert chunks[0]["heading"] == "Title 1"
        assert chunks[1]["heading"] == "Title 2"
    
    def test_chunk_preserves_heading_hierarchy(self):
        """Should preserve heading hierarchy in chunks."""
        chunker = SemanticChunker(max_chunk_size=100)
        text = "# Main\n\n## Subtitle\n\nContent"
        
        chunks = chunker.chunk_document(text)
        
        assert chunks[0]["heading"] == "Subtitle"
        assert chunks[0]["parent_heading"] == "Main"
        assert chunks[0]["section_path"] == ["Main", "Subtitle"]
    
    def test_chunk_splits_long_sections(self):
        """Should split long sections into multiple chunks."""
        chunker = SemanticChunker(max_chunk_size=10, overlap=2)
        text = "# Title\n\n" + " ".join(["word"] * 50)
        
        chunks = chunker.chunk_document(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["heading"] == "Title"
    
    def test_chunk_includes_metadata(self):
        """Should include chunk metadata."""
        chunker = SemanticChunker(max_chunk_size=100)
        text = "# Title\n\nSome content here"
        
        chunks = chunker.chunk_document(text)
        
        chunk = chunks[0]
        assert "word_count" in chunk
        assert "char_count" in chunk
        assert "start_position" in chunk
        assert "end_position" in chunk
        assert chunk["word_count"] > 0


class TestQualityFilter:
    """Test quality filtering functionality."""
    
    def test_detect_boilerplate_copyright(self):
        """Should detect copyright as boilerplate."""
        text = "Copyright 2024 Example Corp. All rights reserved."
        
        assert QualityFilter.is_boilerplate(text)
    
    def test_detect_boilerplate_privacy_policy(self):
        """Should detect privacy policy as boilerplate."""
        text = "Read our privacy policy for more information."
        
        assert QualityFilter.is_boilerplate(text)
    
    def test_normal_content_not_boilerplate(self):
        """Should not flag normal content as boilerplate."""
        text = "This is a guide to lean manufacturing principles."
        
        assert not QualityFilter.is_boilerplate(text)
    
    def test_quality_score_normal_content(self):
        """Should give good score to normal content."""
        text = "This is a well-structured paragraph with good content. It contains multiple sentences with valuable information. Each sentence adds value and demonstrates clear communication. The content is informative and well-written."
        
        score = QualityFilter.calculate_quality_score(text)
        
        assert score >= 0.7
    
    def test_quality_score_short_content(self):
        """Should penalize very short content."""
        text = "Short."
        
        score = QualityFilter.calculate_quality_score(text)
        
        assert score < 0.7
    
    def test_quality_score_special_characters(self):
        """Should penalize content with many special characters."""
        text = "@@@###$$$%%%^^^&&&***((()))"
        
        score = QualityFilter.calculate_quality_score(text)
        
        assert score < 0.7
    
    def test_detect_duplicate_exact_match(self):
        """Should detect exact duplicate."""
        text = "This is the same content."
        existing = ["This is the same content."]
        
        assert QualityFilter.detect_duplicate(text, existing)
    
    def test_detect_duplicate_no_match(self):
        """Should not flag different content as duplicate."""
        text = "This is different content."
        existing = ["This is other content."]
        
        assert not QualityFilter.detect_duplicate(text, existing)


class TestTaxonomyTagger:
    """Test taxonomy tagging functionality."""
    
    def test_tag_chunk_with_tps_keywords(self):
        """Should tag chunk with TPS tag."""
        text = "The Toyota Production System emphasizes just-in-time production."
        
        tags = TaxonomyTagger.tag_chunk(text)
        
        assert TaxonomyTag.TPS.value in tags
    
    def test_tag_chunk_with_pdca_keywords(self):
        """Should tag chunk with PDCA tag."""
        text = "The Deming Cycle, also known as PDCA, is essential for systematic improvement."
        
        tags = TaxonomyTagger.tag_chunk(text)
        
        assert TaxonomyTag.PDCA.value in tags
    
    def test_tag_chunk_with_kata_keywords(self):
        """Should tag chunk with Kata tag."""
        text = "The improvement kata provides a structured approach to problem-solving."
        
        tags = TaxonomyTagger.tag_chunk(text)
        
        assert TaxonomyTag.KATA.value in tags
    
    def test_tag_chunk_with_multiple_tags(self):
        """Should apply multiple relevant tags."""
        text = "Lean manufacturing principles and the A3 thinking process help with root cause analysis."
        
        tags = TaxonomyTagger.tag_chunk(text)
        
        assert TaxonomyTag.LEAN_PRINCIPLES.value in tags
        assert TaxonomyTag.A3_THINKING.value in tags
        assert TaxonomyTag.PROBLEM_SOLVING.value in tags
    
    def test_tag_chunk_inherits_document_tags(self):
        """Should inherit tags from document."""
        text = "Content without specific keywords."
        document_tags = [TaxonomyTag.TPS.value]
        
        tags = TaxonomyTagger.tag_chunk(text, document_tags)
        
        assert TaxonomyTag.TPS.value in tags
    
    def test_tag_chunk_no_matching_keywords(self):
        """Should return empty list when no keywords match."""
        text = "Generic business content without specific methodology."
        
        tags = TaxonomyTagger.tag_chunk(text)
        
        # May have no tags or only inherited ones
        assert isinstance(tags, list)


class TestKnowledgePackIngestionService:
    """Test main ingestion service."""
    
    @patch('sensei.services.knowledge_ingestion.ContentFetcher')
    def test_ingest_url_with_valid_license(self, mock_fetcher_class):
        """Should successfully ingest URL with valid license."""
        # Setup mocks
        mock_fetcher = Mock()
        mock_fetcher.fetch_url.return_value = (
            b"<html><body><p>Test content</p></body></html>",
            "text/html"
        )
        mock_fetcher_class.return_value = mock_fetcher
        
        service = KnowledgePackIngestionService()
        service.content_fetcher = mock_fetcher
        
        document, message = service.ingest_url(
            url="https://example.com/test",
            title="Test Document",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            tags=["tps"],
        )
        
        assert document is not None
        assert document.title == "Test Document"
        assert document.license_type == LicenseType.CC_BY
        assert document.word_count > 0
        assert "tps" in document.tags
        assert "success" in message.lower()
    
    @patch('sensei.services.knowledge_ingestion.ContentFetcher')
    def test_ingest_url_with_invalid_license(self, mock_fetcher_class):
        """Should reject URL without valid license."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_url.return_value = (
            b"<html><body><p>Copyrighted content</p></body></html>",
            "text/html"
        )
        mock_fetcher_class.return_value = mock_fetcher
        
        service = KnowledgePackIngestionService()
        service.content_fetcher = mock_fetcher
        
        document, message = service.ingest_url(
            url="https://example.com/test",
            title="Test Document",
        )
        
        assert document is None
        assert "license not allowed" in message.lower()
    
    def test_process_document_creates_chunks(self):
        """Should process document into chunks."""
        document = KnowledgeDocument(
            title="Test Document",
            author="Test Author",
            source_url="https://example.com/test",
            retrieval_date=datetime.now(),
            license_type=LicenseType.CC_BY,
            attribution_text="Test attribution",
            original_format=ContentFormat.PLAIN_TEXT,
            raw_content="# Title\n\nContent",
            normalized_content="# Title\n\nContent with multiple words to make it substantial",
            word_count=10,
            content_hash="test123",
            tags=["tps"],
        )
        
        service = KnowledgePackIngestionService()
        chunks = service.process_document(document)
        
        assert len(chunks) > 0
        assert document.is_processed
        assert document.chunk_count == len(chunks)
        
        for chunk in chunks:
            assert chunk.document_id == document.id
            assert chunk.citation
            assert chunk.word_count > 0
    
    def test_process_document_filters_low_quality(self):
        """Should filter out low-quality chunks."""
        document = KnowledgeDocument(
            title="Test Document",
            author="Test Author",
            source_url="https://example.com/test",
            retrieval_date=datetime.now(),
            license_type=LicenseType.CC_BY,
            attribution_text="Test attribution",
            original_format=ContentFormat.PLAIN_TEXT,
            raw_content="# Title\n\nContent\n\nCopyright 2024",
            normalized_content="# Title\n\nGood content here\n\nCopyright 2024 All rights reserved",
            word_count=10,
            content_hash="test123",
            tags=[],
        )
        
        service = KnowledgePackIngestionService()
        chunks = service.process_document(document)
        
        # Boilerplate section should be filtered
        boilerplate_chunks = [c for c in chunks if c.is_boilerplate]
        assert len(boilerplate_chunks) == 0
    
    def test_detect_format_html(self):
        """Should detect HTML format."""
        service = KnowledgePackIngestionService()
        
        format_type = service._detect_format("text/html", "https://example.com/page.html")
        
        assert format_type == ContentFormat.HTML
    
    def test_detect_format_pdf(self):
        """Should detect PDF format."""
        service = KnowledgePackIngestionService()
        
        format_type = service._detect_format("application/pdf", "https://example.com/doc.pdf")
        
        assert format_type == ContentFormat.PDF
    
    def test_detect_format_markdown(self):
        """Should detect Markdown format."""
        service = KnowledgePackIngestionService()
        
        format_type = service._detect_format("text/plain", "https://example.com/doc.md")
        
        assert format_type == ContentFormat.MARKDOWN


class TestIntegration:
    """Integration tests for complete ingestion workflow."""
    
    @patch('sensei.services.knowledge_ingestion.ContentFetcher')
    def test_full_ingestion_workflow(self, mock_fetcher_class):
        """Should complete full ingestion and processing workflow."""
        # Setup
        html_content = """
        <html>
        <body>
            <h1>Lean Manufacturing Guide</h1>
            <p>This guide covers lean principles.</p>
            <h2>Just-in-Time Production</h2>
            <p>JIT reduces waste by producing only what is needed.</p>
        </body>
        </html>
        """
        
        mock_fetcher = Mock()
        mock_fetcher.fetch_url.return_value = (html_content.encode(), "text/html")
        mock_fetcher_class.return_value = mock_fetcher
        
        service = KnowledgePackIngestionService()
        service.content_fetcher = mock_fetcher
        
        # Ingest
        document, message = service.ingest_url(
            url="https://example.com/lean-guide",
            title="Lean Manufacturing Guide",
            author="John Shook",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            tags=["lean_principles"],
        )
        
        assert document is not None
        assert "success" in message.lower()
        
        # Process
        chunks = service.process_document(document)
        
        assert len(chunks) > 0
        assert any("lean" in chunk.chunk_text.lower() for chunk in chunks)
        assert any("jit" in chunk.chunk_text.lower() for chunk in chunks)
        
        # Verify chunks have metadata
        for chunk in chunks:
            assert chunk.heading is not None
            assert chunk.word_count > 0
            assert chunk.citation
            assert len(chunk.tags) > 0

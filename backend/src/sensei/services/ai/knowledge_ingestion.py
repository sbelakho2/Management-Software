"""
Knowledge Pack Ingestion CLI Service.

Provides command-line tools for ingesting open-license learning content
into the knowledge base with full license verification and attribution.
"""

import hashlib
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io

from sensei.models.knowledge_pack import (
    ContentFormat,
    KnowledgeDocument,
    KnowledgeChunk,
    IngestionLog,
    LicenseType,
    TaxonomyTag,
)


class LicenseVerifier:
    """Verify and classify content licenses."""
    
    # License patterns for detection
    LICENSE_PATTERNS = {
        LicenseType.CC0: [
            r"cc0",
            r"creative\s+commons\s+zero",
            r"public\s+domain\s+dedication",
        ],
        LicenseType.CC_BY: [
            r"cc\s+by\s+[0-9.]+",
            r"creative\s+commons\s+attribution",
        ],
        LicenseType.CC_BY_SA: [
            r"cc\s+by-sa",
            r"creative\s+commons\s+attribution-sharealike",
        ],
        LicenseType.MIT: [
            r"mit\s+license",
            r"permission\s+is\s+hereby\s+granted.*mit",
        ],
        LicenseType.APACHE_2: [
            r"apache\s+license.*2\.0",
            r"apache-2\.0",
        ],
        LicenseType.BSD: [
            r"bsd\s+license",
            r"berkeley\s+software\s+distribution",
        ],
        LicenseType.PUBLIC_DOMAIN: [
            r"public\s+domain",
            r"no\s+rights\s+reserved",
        ],
    }
    
    @classmethod
    def detect_license(cls, text: str, url: str | None = None) -> LicenseType | None:
        """
        Detect license type from text or URL.
        
        Args:
            text: License text or document content
            url: Source URL for additional context
            
        Returns:
            Detected license type or None if not recognized
        """
        text_lower = text.lower()
        
        # Check URL for license indicators
        if url:
            url_lower = url.lower()
            if "creativecommons.org/publicdomain/zero" in url_lower:
                return LicenseType.CC0
            if "/by-sa/" in url_lower:
                return LicenseType.CC_BY_SA
            if "creativecommons.org/licenses/by/" in url_lower:
                return LicenseType.CC_BY
            if "opensource.org/licenses/MIT" in url_lower:
                return LicenseType.MIT
            if "apache.org/licenses/LICENSE-2.0" in url_lower:
                return LicenseType.APACHE_2
        
        # Check text patterns
        for license_type, patterns in cls.LICENSE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return license_type
        
        return None
    
    @classmethod
    def is_allowed_license(cls, license_type: LicenseType | None) -> bool:
        """Check if license type is allowed for ingestion."""
        return license_type is not None
    
    @classmethod
    def generate_attribution(
        cls,
        title: str,
        author: str | None,
        source_url: str,
        license_type: LicenseType,
    ) -> str:
        """
        Generate attribution text for content.
        
        Args:
            title: Document title
            author: Author name (if known)
            source_url: Source URL
            license_type: License type
            
        Returns:
            Formatted attribution text
        """
        parts = []
        
        if author:
            parts.append(f'"{title}" by {author}')
        else:
            parts.append(f'"{title}"')
        
        parts.append(f"Source: {source_url}")
        parts.append(f"License: {license_type.value.replace('_', ' ').upper()}")
        
        return " | ".join(parts)


class ContentFetcher:
    """Fetch content from various sources."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)
    
    def fetch_url(self, url: str) -> tuple[bytes, str]:
        """
        Fetch content from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (content bytes, content type)
            
        Raises:
            httpx.HTTPError: If fetch fails
        """
        response = self.client.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "").lower()
        return response.content, content_type
    
    def close(self):
        """Close HTTP client."""
        self.client.close()


class ContentNormalizer:
    """Normalize content from various formats to clean text."""
    
    @staticmethod
    def normalize_html(html: str) -> str:
        """
        Convert HTML to clean text preserving headings.
        
        Args:
            html: HTML content
            
        Returns:
            Normalized text with heading structure
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()
        
        # Process headings and paragraphs
        text_parts = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
            text = element.get_text(strip=True)
            if text:
                if element.name.startswith("h"):
                    # Add heading markers
                    level = element.name[1]
                    text_parts.append(f"\n{'#' * int(level)} {text}\n")
                else:
                    text_parts.append(text)
        
        normalized = "\n\n".join(text_parts)
        return re.sub(r"\n{3,}", "\n\n", normalized).strip()
    
    @staticmethod
    def normalize_pdf(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF.
        
        Args:
            pdf_bytes: PDF content as bytes
            
        Returns:
            Extracted text
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return "\n\n".join(text_parts).strip()
    
    @staticmethod
    def normalize_markdown(markdown: str) -> str:
        """
        Clean markdown text while preserving structure.
        
        Args:
            markdown: Markdown content
            
        Returns:
            Normalized text
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", markdown)
        
        # Normalize multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()
    
    @staticmethod
    def normalize_plain_text(text: str) -> str:
        """
        Clean plain text.
        
        Args:
            text: Plain text content
            
        Returns:
            Normalized text
        """
        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()


class SemanticChunker:
    """Chunk documents with heading-aware semantic splitting."""
    
    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_document(self, text: str) -> list[dict[str, Any]]:
        """
        Split document into semantic chunks.
        
        Args:
            text: Normalized document text
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        
        # Split by headings first
        sections = self._split_by_headings(text)
        
        chunk_index = 0
        position = 0
        
        for section in sections:
            heading = section.get("heading")
            parent_heading = section.get("parent_heading")
            section_path = section.get("section_path", [])
            content = section["content"]
            
            # Further split long sections
            if len(content) > self.max_chunk_size:
                sub_chunks = self._split_long_text(content)
                for i, sub_chunk in enumerate(sub_chunks):
                    chunks.append({
                        "chunk_text": sub_chunk,
                        "chunk_index": chunk_index,
                        "heading": heading,
                        "parent_heading": parent_heading,
                        "section_path": section_path,
                        "word_count": len(sub_chunk.split()),
                        "char_count": len(sub_chunk),
                        "start_position": position,
                        "end_position": position + len(sub_chunk),
                    })
                    chunk_index += 1
                    position += len(sub_chunk)
            else:
                chunks.append({
                    "chunk_text": content,
                    "chunk_index": chunk_index,
                    "heading": heading,
                    "parent_heading": parent_heading,
                    "section_path": section_path,
                    "word_count": len(content.split()),
                    "char_count": len(content),
                    "start_position": position,
                    "end_position": position + len(content),
                })
                chunk_index += 1
                position += len(content)
        
        return chunks
    
    def _split_by_headings(self, text: str) -> list[dict[str, Any]]:
        """Split text by markdown headings."""
        sections = []
        current_section: dict[str, Any] = {"content": "", "heading": None, "parent_heading": None, "section_path": []}
        heading_stack: list[str] = []
        
        for line in text.split("\n"):
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            
            if heading_match:
                # Save previous section
                if current_section["content"].strip():
                    sections.append(current_section)
                
                # Start new section
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                
                # Update heading stack
                heading_stack = heading_stack[:level-1]
                heading_stack.append(heading_text)
                
                current_section = {
                    "content": "",
                    "heading": heading_text,
                    "parent_heading": heading_stack[-2] if len(heading_stack) > 1 else None,
                    "section_path": heading_stack.copy(),
                }
            else:
                current_section["content"] += line + "\n"
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _split_long_text(self, text: str) -> list[str]:
        """Split long text into smaller chunks with overlap."""
        chunks = []
        words = text.split()
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + self.max_chunk_size]
            chunks.append(" ".join(chunk_words))
            i += self.max_chunk_size - self.overlap
        
        return chunks


class QualityFilter:
    """Filter and score chunks for quality."""
    
    @staticmethod
    def is_boilerplate(text: str) -> bool:
        """
        Detect boilerplate content.
        
        Args:
            text: Chunk text
            
        Returns:
            True if appears to be boilerplate
        """
        boilerplate_patterns = [
            r"all rights reserved",
            r"copyright \d{4}",
            r"terms of service",
            r"privacy policy",
            r"cookie policy",
            r"subscribe to.*newsletter",
            r"follow us on",
            r"^advertisement$",
            r"sponsored content",
            r"restore access to 500,000\+ books",
            r"controlled digital lending",
        ]
        
        text_lower = text.lower()
        for pattern in boilerplate_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    @staticmethod
    def calculate_quality_score(text: str) -> float:
        """
        Calculate quality score for chunk.
        
        Args:
            text: Chunk text
            
        Returns:
            Quality score 0-1
        """
        score = 1.0
        
        # Penalize very short chunks
        word_count = len(text.split())
        if word_count < 20:
            score *= 0.5
        
        # Penalize chunks with lots of special characters
        special_char_ratio = len(re.findall(r"[^a-zA-Z0-9\s]", text)) / len(text)
        if special_char_ratio > 0.3:
            score *= 0.7
        
        # Reward chunks with good sentence structure
        sentence_count = len(re.split(r"[.!?]+", text))
        if sentence_count >= 2:
            score *= 1.1
        
        return min(score, 1.0)
    
    @staticmethod
    def detect_duplicate(chunk_text: str, existing_chunks: list[str]) -> bool:
        """
        Detect if chunk is duplicate of existing content.
        
        Args:
            chunk_text: New chunk text
            existing_chunks: List of existing chunk texts
            
        Returns:
            True if duplicate detected
        """
        chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()
        
        for existing in existing_chunks:
            existing_hash = hashlib.md5(existing.encode()).hexdigest()
            if chunk_hash == existing_hash:
                return True
        
        return False


class TaxonomyTagger:
    """Auto-tag chunks with taxonomy categories."""
    
    # Keywords for each taxonomy tag
    TAG_KEYWORDS = {
        TaxonomyTag.TPS: [
            "toyota production system", "tps", "just-in-time", "jidoka", "kaizen",
        ],
        TaxonomyTag.PDCA: [
            "plan do check act", "pdca", "deming cycle", "shewhart cycle",
        ],
        TaxonomyTag.KATA: [
            "improvement kata", "coaching kata", "toyota kata", "scientific thinking",
        ],
        TaxonomyTag.QUOTING: [
            "quotation", "pricing", "cost estimation", "proposal",
        ],
        TaxonomyTag.QUALIFICATION: [
            "qualification", "vendor qualification", "supplier evaluation",
        ],
        TaxonomyTag.CTQ: [
            "critical to quality", "ctq", "quality characteristic", "customer requirement",
        ],
        TaxonomyTag.OBEYA: [
            "obeya", "war room", "visual management room", "big room",
        ],
        TaxonomyTag.A3_THINKING: [
            "a3 thinking", "a3 report", "problem solving", "structured thinking",
        ],
        TaxonomyTag.STANDARD_WORK: [
            "standard work", "standardized work", "work instruction", "sop",
        ],
        TaxonomyTag.VISUAL_MANAGEMENT: [
            "visual management", "visual control", "andon", "kanban board",
        ],
        TaxonomyTag.PROBLEM_SOLVING: [
            "problem solving", "root cause analysis", "5 why", "fishbone",
        ],
        TaxonomyTag.LEAN_PRINCIPLES: [
            "lean manufacturing", "lean thinking", "muda", "waste reduction",
        ],
        TaxonomyTag.QUALITY_GATES: [
            "quality gate", "stage gate", "phase gate", "checkpoint",
        ],
        TaxonomyTag.CONTINUOUS_IMPROVEMENT: [
            "continuous improvement", "kaizen", "incremental improvement",
        ],
        TaxonomyTag.RISK_MANAGEMENT: [
            "risk management", "risk assessment", "fmea", "risk mitigation",
        ],
    }
    
    @classmethod
    def tag_chunk(cls, text: str, document_tags: list[str] | None = None) -> list[str]:
        """
        Auto-tag chunk based on content.
        
        Args:
            text: Chunk text
            document_tags: Tags from parent document (inherited)
            
        Returns:
            List of applicable taxonomy tags
        """
        tags = set(document_tags or [])
        text_lower = text.lower()
        
        for tag, keywords in cls.TAG_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    tags.add(tag.value)
                    break
        
        return list(tags)


class KnowledgePackIngestionService:
    """Main service for ingesting knowledge content."""
    
    def __init__(self):
        self.license_verifier = LicenseVerifier()
        self.content_fetcher = ContentFetcher()
        self.content_normalizer = ContentNormalizer()
        self.semantic_chunker = SemanticChunker()
        self.quality_filter = QualityFilter()
        self.taxonomy_tagger = TaxonomyTagger()
    
    def ingest_url(
        self,
        url: str,
        title: str,
        author: str | None = None,
        license_url: str | None = None,
        license_text: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[KnowledgeDocument | None, str]:
        """
        Ingest content from URL.
        
        Args:
            url: Source URL
            title: Document title
            author: Author name (optional)
            license_url: URL to license (optional)
            license_text: License text (optional)
            tags: Initial taxonomy tags (optional)
            
        Returns:
            Tuple of (document, status_message)
        """
        start_time = datetime.now()
        
        try:
            # Fetch content
            content_bytes, content_type = self.content_fetcher.fetch_url(url)
            
            # Determine format
            format_type = self._detect_format(content_type, url)
            
            # Verify license
            license_type = self.license_verifier.detect_license(
                license_text or "",
                license_url or url,
            )
            
            if not self.license_verifier.is_allowed_license(license_type):
                return None, f"License not allowed or not detected: {url}"
            
            # Normalize content
            if format_type == ContentFormat.HTML:
                normalized = self.content_normalizer.normalize_html(content_bytes.decode("utf-8"))
            elif format_type == ContentFormat.PDF:
                normalized = self.content_normalizer.normalize_pdf(content_bytes)
            elif format_type == ContentFormat.MARKDOWN:
                normalized = self.content_normalizer.normalize_markdown(content_bytes.decode("utf-8"))
            else:
                normalized = self.content_normalizer.normalize_plain_text(content_bytes.decode("utf-8"))
            
            # Clean null bytes which PostgreSQL doesn't support in text fields
            normalized = normalized.replace("\x00", "")
            raw_content_str = content_bytes.decode("utf-8", errors="ignore").replace("\x00", "")
            
            # Check for restricted access placeholders (Archive.org)
            if "restore access to 500,000" in normalized.lower() or "controlled digital lending" in normalized.lower():
                return None, f"Restricted content placeholder detected: {url}"
            
            # Calculate content hash
            content_hash = hashlib.sha256(normalized.encode()).hexdigest()
            
            # Generate attribution (license_type guaranteed non-None after is_allowed_license check)
            assert license_type is not None  # Verified by is_allowed_license above
            attribution = self.license_verifier.generate_attribution(
                title, author, url, license_type
            )
            
            # Create document
            document = KnowledgeDocument(
                title=title,
                author=author,
                source_url=url,
                retrieval_date=datetime.now(),
                license_type=license_type,
                license_url=license_url,
                license_text=license_text,
                attribution_text=attribution,
                original_format=format_type,
                raw_content=raw_content_str,
                normalized_content=normalized,
                word_count=len(normalized.split()),
                content_hash=content_hash,
                tags=tags or [],
                is_processed=False,
                is_indexed=False,
                extra_metadata={
                    "content_type": content_type,
                    "url_domain": urlparse(url).netloc,
                },
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return document, f"Successfully ingested: {title} ({processing_time}ms)"
            
        except Exception as e:
            return None, f"Error ingesting {url}: {str(e)}"
    
    def process_document(self, document: KnowledgeDocument) -> list[KnowledgeChunk]:
        """
        Process document into chunks.
        
        Args:
            document: Knowledge document to process
            
        Returns:
            List of created chunks
        """
        # Chunk document
        chunk_dicts = self.semantic_chunker.chunk_document(document.normalized_content)
        
        chunks = []
        existing_texts: list[str] = []
        
        for chunk_dict in chunk_dicts:
            # Quality filtering
            is_boilerplate = self.quality_filter.is_boilerplate(chunk_dict["chunk_text"])
            quality_score = self.quality_filter.calculate_quality_score(chunk_dict["chunk_text"])
            is_duplicate = self.quality_filter.detect_duplicate(
                chunk_dict["chunk_text"],
                existing_texts,
            )
            
            # Skip low-quality chunks
            if is_boilerplate or is_duplicate or quality_score < 0.3:
                continue
            
            # Auto-tag
            chunk_tags = self.taxonomy_tagger.tag_chunk(
                chunk_dict["chunk_text"],
                document.tags,
            )
            
            # Generate citation
            citation = f'{document.attribution_text} (Section: {" > ".join(chunk_dict["section_path"])})'
            
            # Create chunk
            chunk = KnowledgeChunk(
                document_id=document.id,
                chunk_text=chunk_dict["chunk_text"].replace("\x00", ""),
                chunk_index=chunk_dict["chunk_index"],
                heading=chunk_dict.get("heading"),
                parent_heading=chunk_dict.get("parent_heading"),
                section_path=chunk_dict.get("section_path", []),
                word_count=chunk_dict["word_count"],
                char_count=chunk_dict["char_count"],
                start_position=chunk_dict["start_position"],
                end_position=chunk_dict["end_position"],
                quality_score=quality_score,
                is_boilerplate=is_boilerplate,
                is_duplicate=is_duplicate,
                tags=chunk_tags,
                citation=citation,
            )
            
            chunks.append(chunk)
            existing_texts.append(chunk_dict["chunk_text"])
        
        document.is_processed = True
        document.chunk_count = len(chunks)
        
        return chunks
    
    def _detect_format(self, content_type: str, url: str) -> ContentFormat:
        """Detect content format from content-type and URL."""
        if "html" in content_type:
            return ContentFormat.HTML
        elif "pdf" in content_type:
            return ContentFormat.PDF
        elif url.endswith(".md") or "markdown" in content_type:
            return ContentFormat.MARKDOWN
        else:
            return ContentFormat.PLAIN_TEXT
    
    def close(self):
        """Close resources."""
        self.content_fetcher.close()

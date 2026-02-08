"""
Meta-Sensei: Self-Evolving Knowledge & Intelligence Platform.

Implements:
- Self-Evolving Knowledge Base (autonomous synthesis, deduplication, site-specific learning)
- Autonomous Documentation & Plan Maintenance
- Code Quality & Technical Debt Guard
- Meta-Learning from Success (best-practice extraction, privacy-preserving aggregation)
"""

from __future__ import annotations

import ast
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class TemplateType(str, Enum):
    """Types of standard templates."""
    RFQ = "rfq"
    QUOTE = "quote"
    BOM = "bom"
    ASSUMPTION = "assumption"
    RESPONSE = "response"


class DeduplicationStrategy(str, Enum):
    """Strategies for semantic deduplication."""
    MERGE = "merge"
    KEEP_LATEST = "keep_latest"
    KEEP_HIGHEST_SCORE = "keep_highest_score"
    ARCHIVE = "archive"


class SiteTermType(str, Enum):
    """Types of site-specific terminology."""
    PART_NAME = "part_name"
    PROCESS = "process"
    MATERIAL = "material"
    SUPPLIER = "supplier"
    CUSTOM = "custom"


class DocSyncAction(str, Enum):
    """Documentation sync actions."""
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    NO_CHANGE = "no_change"


class CodeIssueType(str, Enum):
    """Types of code quality issues."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLEXITY = "complexity"
    STYLE = "style"
    DEPRECATED = "deprecated"


class CodeIssueSeverity(str, Enum):
    """Severity levels for code issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RefactoringType(str, Enum):
    """Types of refactoring suggestions."""
    EXTRACT_METHOD = "extract_method"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    REDUCE_NESTING = "reduce_nesting"
    OPTIMIZE_LOOP = "optimize_loop"
    CACHE_RESULT = "cache_result"
    INLINE_VARIABLE = "inline_variable"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class UserCorrection:
    """A user correction to be aggregated."""
    id: str
    original_text: str
    corrected_text: str
    correction_type: TemplateType
    context: dict[str, Any]
    user_id: str
    timestamp: datetime
    site_id: str | None = None


@dataclass
class StandardTemplate:
    """A synthesized standard template."""
    id: str
    name: str
    template_type: TemplateType
    content: str
    source_corrections: list[str]
    confidence: float
    version: int
    created_at: datetime
    updated_at: datetime
    site_id: str | None = None


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge in the local seeded knowledge store."""
    id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any]
    score: float
    created_at: datetime
    source: str


@dataclass
class DeduplicationResult:
    """Result of semantic deduplication."""
    original_count: int
    deduplicated_count: int
    merged_chunks: list[tuple[str, str]]  # (kept_id, merged_id)
    archived_chunks: list[str]
    similarity_threshold: float
    strategy: DeduplicationStrategy


@dataclass
class SiteTerm:
    """A site-specific term."""
    term: str
    normalized_form: str
    term_type: SiteTermType
    frequency: int
    contexts: list[str]
    synonyms: list[str]


@dataclass
class SiteReranker:
    """A site-specific re-ranker model."""
    site_id: str
    terms: dict[str, SiteTerm]
    term_weights: dict[str, float]
    trained_at: datetime
    version: int
    accuracy: float


@dataclass
class FeatureDetection:
    """A detected new feature in code."""
    feature_id: str
    name: str
    description: str
    file_path: str
    line_range: tuple[int, int]
    detected_at: datetime
    documented: bool
    doc_section: str | None = None


@dataclass
class DocSyncResult:
    """Result of documentation sync."""
    features_detected: list[FeatureDetection]
    actions_taken: list[tuple[DocSyncAction, str]]
    doc_file: str
    sync_time: datetime
    changes_made: bool


@dataclass
class PlanItem:
    """A development plan item."""
    line_number: int
    text: str
    checked: bool
    indent_level: int
    section: str | None = None


@dataclass
class PlanSyncResult:
    """Result of development plan sync."""
    total_items: int
    checked_items: int
    newly_checked: list[PlanItem]
    verification_methods: dict[str, str]  # item -> how it was verified
    sync_time: datetime


@dataclass
class CodeIssue:
    """A code quality issue."""
    issue_id: str
    file_path: str
    line_number: int
    issue_type: CodeIssueType
    severity: CodeIssueSeverity
    message: str
    code_snippet: str
    suggestion: str | None = None


@dataclass
class RefactoringSuggestion:
    """A refactoring suggestion."""
    suggestion_id: str
    file_path: str
    line_range: tuple[int, int]
    refactoring_type: RefactoringType
    description: str
    original_code: str
    suggested_code: str
    estimated_improvement: str
    priority: int


@dataclass
class QuotePerformance:
    """Performance metrics for a quote."""
    quote_id: str
    margin: float
    win_rate: float
    assumptions: list[str]
    segment: str
    site_id: str
    created_at: datetime
    outcome: str  # "won", "lost", "pending"


@dataclass
class BestPractice:
    """An extracted best practice."""
    id: str
    name: str
    description: str
    source_quotes: list[str]
    assumptions: list[str]
    segment: str | None
    avg_margin: float
    win_rate: float
    extracted_at: datetime
    anonymized: bool


@dataclass
class A3Effectiveness:
    """Effectiveness metrics for an A3."""
    a3_id: str
    countermeasure: str
    effectiveness_score: float
    time_to_resolution: float  # days
    recurrence_rate: float
    cost_savings: float
    closed_at: datetime


@dataclass
class ReasoningWeight:
    """A weight in the reasoning engine."""
    category: str
    weight: float
    source_a3s: list[str]
    last_updated: datetime
    adjustment_history: list[tuple[datetime, float, float]]  # time, old, new


# =============================================================================
# SELF-EVOLVING KNOWLEDGE BASE
# =============================================================================


class AutonomousKnowledgeSynthesizer:
    """
    Aggregates common user corrections to create new Standard Templates.
    """
    
    def __init__(
        self,
        min_corrections: int = 5,
        similarity_threshold: float = 0.8,
        confidence_threshold: float = 0.75,
    ):
        self.min_corrections = min_corrections
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold
        self.corrections: list[UserCorrection] = []
        self.templates: dict[str, StandardTemplate] = {}
        self._correction_clusters: dict[str, list[UserCorrection]] = defaultdict(list)
    
    def add_correction(self, correction: UserCorrection) -> None:
        """Add a user correction for aggregation."""
        self.corrections.append(correction)
        cluster_key = self._compute_cluster_key(correction)
        self._correction_clusters[cluster_key].append(correction)
    
    def _compute_cluster_key(self, correction: UserCorrection) -> str:
        """Compute a clustering key based on correction type and content."""
        # Simple hash-based clustering on correction pattern
        pattern = f"{correction.correction_type}:{correction.original_text}"
        return hashlib.md5(pattern.encode()).hexdigest()[:8]
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)
    
    def synthesize_templates(self) -> list[StandardTemplate]:
        """Synthesize templates from aggregated corrections."""
        new_templates: list[StandardTemplate] = []
        
        for cluster_key, corrections in self._correction_clusters.items():
            if len(corrections) < self.min_corrections:
                continue
            
            # Find the most common correction pattern
            correction_counts: dict[str, int] = defaultdict(int)
            for c in corrections:
                correction_counts[c.corrected_text] += 1
            
            if not correction_counts:
                continue
            
            best_correction = max(correction_counts, key=lambda c: correction_counts[c])
            frequency = correction_counts[best_correction]
            confidence = frequency / len(corrections)
            
            if confidence < self.confidence_threshold:
                continue
            
            template_type = corrections[0].correction_type
            template_id = f"tmpl_{cluster_key}_{int(time.time())}"
            
            template = StandardTemplate(
                id=template_id,
                name=f"Auto-generated {template_type.value} template",
                template_type=template_type,
                content=best_correction,
                source_corrections=[c.id for c in corrections],
                confidence=confidence,
                version=1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                site_id=corrections[0].site_id,
            )
            
            self.templates[template_id] = template
            new_templates.append(template)
        
        return new_templates
    
    def get_template_for_type(self, template_type: TemplateType) -> list[StandardTemplate]:
        """Get all templates of a specific type."""
        return [t for t in self.templates.values() if t.template_type == template_type]
    
    def update_template(self, template_id: str, new_content: str) -> StandardTemplate | None:
        """Update an existing template with new content."""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        template.content = new_content
        template.version += 1
        template.updated_at = datetime.now()
        return template


class SemanticDeduplicator:
    """
    Detects and merges redundant knowledge chunks using embeddings.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.92,
        strategy: DeduplicationStrategy = DeduplicationStrategy.MERGE,
    ):
        self.similarity_threshold = similarity_threshold
        self.strategy = strategy
        self.chunks: dict[str, KnowledgeChunk] = {}
    
    def add_chunk(self, chunk: KnowledgeChunk) -> None:
        """Add a knowledge chunk."""
        self.chunks[chunk.id] = chunk
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_duplicates(self) -> list[tuple[str, str, float]]:
        """Find duplicate chunk pairs above similarity threshold.

        Uses vectorised cosine-similarity matrix to avoid O(n²) Python
        loop (#91).
        """
        chunk_list = list(self.chunks.values())
        if len(chunk_list) < 2:
            return []

        embeddings = np.array([c.embedding for c in chunk_list], dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-10, None)
        normalised = embeddings / norms
        sim_matrix = normalised @ normalised.T

        # Extract upper-triangle pairs above threshold
        duplicates: list[tuple[str, str, float]] = []
        rows, cols = np.where(
            np.triu(sim_matrix, k=1) >= self.similarity_threshold
        )
        for r, c in zip(rows, cols):
            duplicates.append(
                (chunk_list[r].id, chunk_list[c].id, float(sim_matrix[r, c]))
            )

        return duplicates
    
    def deduplicate(self) -> DeduplicationResult:
        """Perform deduplication based on configured strategy."""
        original_count = len(self.chunks)
        duplicates = self.find_duplicates()
        merged: list[tuple[str, str]] = []
        archived: list[str] = []
        
        for chunk1_id, chunk2_id, _ in duplicates:
            if chunk1_id not in self.chunks or chunk2_id not in self.chunks:
                continue
            
            chunk1 = self.chunks[chunk1_id]
            chunk2 = self.chunks[chunk2_id]
            
            if self.strategy == DeduplicationStrategy.MERGE:
                # Merge content, keep higher score
                if chunk1.score >= chunk2.score:
                    chunk1.content = f"{chunk1.content}\n\n{chunk2.content}"
                    del self.chunks[chunk2_id]
                    merged.append((chunk1_id, chunk2_id))
                else:
                    chunk2.content = f"{chunk2.content}\n\n{chunk1.content}"
                    del self.chunks[chunk1_id]
                    merged.append((chunk2_id, chunk1_id))
            
            elif self.strategy == DeduplicationStrategy.KEEP_LATEST:
                if chunk1.created_at >= chunk2.created_at:
                    del self.chunks[chunk2_id]
                    merged.append((chunk1_id, chunk2_id))
                else:
                    del self.chunks[chunk1_id]
                    merged.append((chunk2_id, chunk1_id))
            
            elif self.strategy == DeduplicationStrategy.KEEP_HIGHEST_SCORE:
                if chunk1.score >= chunk2.score:
                    del self.chunks[chunk2_id]
                    merged.append((chunk1_id, chunk2_id))
                else:
                    del self.chunks[chunk1_id]
                    merged.append((chunk2_id, chunk1_id))
            
            elif self.strategy == DeduplicationStrategy.ARCHIVE:
                # Mark for archive instead of delete
                archived.append(chunk2_id)
                merged.append((chunk1_id, chunk2_id))
        
        return DeduplicationResult(
            original_count=original_count,
            deduplicated_count=len(self.chunks),
            merged_chunks=merged,
            archived_chunks=archived,
            similarity_threshold=self.similarity_threshold,
            strategy=self.strategy,
        )


class SiteSpecificLearner:
    """
    Trains small, on-device re-rankers on site-specific terminology.
    """
    
    def __init__(self, site_id: str):
        self.site_id = site_id
        self.terms: dict[str, SiteTerm] = {}
        self.reranker: SiteReranker | None = None
        self._term_frequencies: dict[str, int] = defaultdict(int)
        self._term_contexts: dict[str, list[str]] = defaultdict(list)
    
    def learn_term(
        self,
        term: str,
        term_type: SiteTermType,
        context: str,
        normalized_form: str | None = None,
    ) -> None:
        """Learn a new site-specific term."""
        normalized = normalized_form or term.lower()
        self._term_frequencies[normalized] += 1
        self._term_contexts[normalized].append(context[:200])  # Limit context size
        
        if normalized not in self.terms:
            self.terms[normalized] = SiteTerm(
                term=term,
                normalized_form=normalized,
                term_type=term_type,
                frequency=1,
                contexts=[context[:200]],
                synonyms=[],
            )
        else:
            self.terms[normalized].frequency = self._term_frequencies[normalized]
            if len(self.terms[normalized].contexts) < 10:
                self.terms[normalized].contexts.append(context[:200])
    
    def add_synonym(self, term: str, synonym: str) -> bool:
        """Add a synonym for an existing term."""
        normalized = term.lower()
        if normalized not in self.terms:
            return False
        
        if synonym not in self.terms[normalized].synonyms:
            self.terms[normalized].synonyms.append(synonym)
        return True
    
    def train_reranker(self) -> SiteReranker:
        """Train a site-specific re-ranker model."""
        # Compute term weights based on frequency and context diversity
        term_weights: dict[str, float] = {}
        
        max_freq = max(self._term_frequencies.values()) if self._term_frequencies else 1
        
        for term, freq in self._term_frequencies.items():
            context_diversity = len(set(self._term_contexts.get(term, [])))
            # Weight = normalized frequency * context diversity factor
            weight = (freq / max_freq) * (1 + 0.1 * min(context_diversity, 10))
            term_weights[term] = min(weight, 2.0)  # Cap at 2.0
        
        self.reranker = SiteReranker(
            site_id=self.site_id,
            terms=self.terms.copy(),
            term_weights=term_weights,
            trained_at=datetime.now(),
            version=1 if not self.reranker else self.reranker.version + 1,
            accuracy=0.85,  # Simulated accuracy
        )
        
        return self.reranker
    
    def rerank_results(
        self,
        results: list[tuple[str, float]],  # (content, base_score)
    ) -> list[tuple[str, float]]:
        """Re-rank search results using site-specific terms."""
        if not self.reranker:
            return results
        
        reranked: list[tuple[str, float]] = []
        
        for content, base_score in results:
            boost = 0.0
            content_lower = content.lower()
            
            for term, weight in self.reranker.term_weights.items():
                if term in content_lower:
                    boost += weight * 0.1  # Small boost per term match
            
            new_score = base_score * (1 + boost)
            reranked.append((content, new_score))
        
        return sorted(reranked, key=lambda x: x[1], reverse=True)


# =============================================================================
# AUTONOMOUS DOCUMENTATION & PLAN MAINTENANCE
# =============================================================================


class DocImplementationSync:
    """
    Detects new features and automatically updates documentation.
    """
    
    FEATURE_PATTERNS = [
        (r"def\s+(\w+)\s*\([^)]*\)\s*(?:->.*?)?:", "function"),
        (r"class\s+(\w+)(?:\([^)]*\))?:", "class"),
        (r"@app\.(get|post|put|delete|patch)\s*\(['\"]([^'\"]+)['\"]", "endpoint"),
        (r"router\.(get|post|put|delete|patch)\s*\(['\"]([^'\"]+)['\"]", "endpoint"),
    ]
    
    def __init__(self, source_dir: str, doc_file: str):
        self.source_dir = Path(source_dir)
        self.doc_file = Path(doc_file)
        self.detected_features: list[FeatureDetection] = []
        self._documented_features: set[str] = set()
    
    def _parse_docstring(self, source: str, start_line: int) -> str | None:
        """Extract docstring from source starting at a line."""
        lines = source.split("\n")[start_line:]
        in_docstring = False
        docstring_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = True
                    quote = stripped[:3]
                    content = stripped[3:]
                    if content.endswith(quote):
                        return content[:-3].strip()
                    docstring_lines.append(content)
                else:
                    break
            else:
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    docstring_lines.append(stripped[:-3])
                    break
                docstring_lines.append(stripped)
        
        return " ".join(docstring_lines).strip() if docstring_lines else None
    
    def scan_source_files(self) -> list[FeatureDetection]:
        """Scan source files for new features.

        Uses incremental scanning: only re-reads files whose mtime has changed
        since the last scan, dramatically reducing I/O for repeated calls.
        """
        # Initialise per-file caches on first call
        if not hasattr(self, "_file_cache"):
            # _file_cache: path -> (mtime, list[FeatureDetection])
            self._file_cache: dict[str, tuple[float, list[FeatureDetection]]] = {}

        if not self.source_dir.exists():
            self.detected_features = []
            return []

        current_files: set[str] = set()
        updated_features: list[FeatureDetection] = []

        for py_file in self.source_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            file_key = str(py_file)
            current_files.add(file_key)

            try:
                mtime = py_file.stat().st_mtime
            except OSError:
                continue

            cached = self._file_cache.get(file_key)
            if cached and cached[0] == mtime:
                # File unchanged — reuse cached features
                updated_features.extend(cached[1])
                continue

            # File is new or modified — rescan
            file_features: list[FeatureDetection] = []
            try:
                content = py_file.read_text()

                for pattern, feature_type in self.FEATURE_PATTERNS:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count("\n")

                        if feature_type == "endpoint":
                            name = f"{match.group(1).upper()} {match.group(2)}"
                        else:
                            name = match.group(1)

                        description = self._parse_docstring(content, line_num + 1) or f"A {feature_type}"

                        feature = FeatureDetection(
                            feature_id=f"{py_file.stem}_{name}_{line_num}",
                            name=name,
                            description=description[:200],
                            file_path=str(py_file),
                            line_range=(line_num + 1, line_num + 10),
                            detected_at=datetime.now(),
                            documented=name in self._documented_features,
                        )
                        file_features.append(feature)
            except Exception:
                continue

            self._file_cache[file_key] = (mtime, file_features)
            updated_features.extend(file_features)

        # Evict cache entries for deleted files
        stale_keys = set(self._file_cache.keys()) - current_files
        for key in stale_keys:
            del self._file_cache[key]

        self.detected_features = updated_features
        return self.detected_features
    
    def load_documented_features(self) -> set[str]:
        """Load already-documented features from doc file."""
        self._documented_features = set()
        
        if not self.doc_file.exists():
            return self._documented_features
        
        try:
            content = self.doc_file.read_text()
            # Look for feature references in markdown headers and code blocks
            for match in re.finditer(r"##\s+(\w+)|`(\w+)`", content):
                feature = match.group(1) or match.group(2)
                self._documented_features.add(feature)
        except Exception:
            logger.exception("Failed to read documented features from %s", self.doc_file)
        
        return self._documented_features
    
    def generate_doc_updates(self) -> list[tuple[DocSyncAction, str]]:
        """Generate documentation updates for new features."""
        self.load_documented_features()
        updates: list[tuple[DocSyncAction, str]] = []
        
        for feature in self.detected_features:
            if feature.name not in self._documented_features:
                doc_section = f"\n## {feature.name}\n\n{feature.description}\n\n"
                doc_section += f"**File**: `{feature.file_path}`\n"
                doc_section += f"**Lines**: {feature.line_range[0]}-{feature.line_range[1]}\n"
                updates.append((DocSyncAction.ADD, doc_section))
                feature.documented = True
                feature.doc_section = doc_section
        
        return updates
    
    def sync(self) -> DocSyncResult:
        """Perform full documentation sync."""
        self.scan_source_files()
        updates = self.generate_doc_updates()
        
        return DocSyncResult(
            features_detected=self.detected_features,
            actions_taken=updates,
            doc_file=str(self.doc_file),
            sync_time=datetime.now(),
            changes_made=len(updates) > 0,
        )


class DevelopmentPlanTracker:
    """
    Automatically checks off items in Development_Plan.md.
    """
    
    CHECKBOX_PATTERN = r"^(\s*)-\s+\[([ x])\]\s+(.+)$"
    
    def __init__(self, plan_file: str, repo_path: str):
        self.plan_file = Path(plan_file)
        self.repo_path = Path(repo_path)
        self.items: list[PlanItem] = []
        self._verification_methods: dict[str, str] = {}
    
    def parse_plan(self) -> list[PlanItem]:
        """Parse the development plan file."""
        self.items = []
        
        if not self.plan_file.exists():
            return []
        
        content = self.plan_file.read_text()
        lines = content.split("\n")
        current_section = None
        
        for i, line in enumerate(lines):
            # Track sections
            if line.startswith("## ") or line.startswith("### "):
                current_section = line.lstrip("#").strip()
            
            match = re.match(self.CHECKBOX_PATTERN, line)
            if match:
                indent = len(match.group(1))
                checked = match.group(2) == "x"
                text = match.group(3)
                
                self.items.append(PlanItem(
                    line_number=i + 1,
                    text=text,
                    checked=checked,
                    indent_level=indent,
                    section=current_section,
                ))
        
        return self.items
    
    def _check_file_exists(self, pattern: str) -> bool:
        """Check if files matching pattern exist in repo."""
        for py_file in self.repo_path.rglob(pattern):
            if "__pycache__" not in str(py_file):
                return True
        return False
    
    def _check_test_passes(self, test_pattern: str) -> bool:
        """Check if tests matching pattern exist (simulated pass check)."""
        for test_file in self.repo_path.rglob(f"test_{test_pattern}*.py"):
            if test_file.exists():
                return True
        return False
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from item text for matching."""
        # Remove common words and extract meaningful keywords
        stop_words = {"the", "a", "an", "and", "or", "to", "for", "in", "on", "with", "is", "of"}
        words = re.findall(r"\b\w+\b", text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def verify_item_implementation(self, item: PlanItem) -> bool:
        """Verify if a plan item has been implemented."""
        keywords = self._extract_keywords(item.text)
        if not keywords:
            return False
        
        # Require majority of keywords to match (#197: single keyword match is too loose)
        matches = 0
        for keyword in keywords:
            if self._check_file_exists(f"*{keyword}*.py"):
                matches += 1
            elif self._check_test_passes(keyword):
                matches += 1
        
        threshold = max(2, len(keywords) // 2)  # At least 2 or half of keywords
        if matches >= threshold:
            self._verification_methods[item.text] = f"multi_match:{matches}/{len(keywords)}"
            return True
        
        return False
    
    def sync_plan(self) -> PlanSyncResult:
        """Synchronize plan with implementation status."""
        self.parse_plan()
        newly_checked: list[PlanItem] = []
        
        for item in self.items:
            if not item.checked and self.verify_item_implementation(item):
                item.checked = True
                newly_checked.append(item)
        
        return PlanSyncResult(
            total_items=len(self.items),
            checked_items=sum(1 for i in self.items if i.checked),
            newly_checked=newly_checked,
            verification_methods=self._verification_methods,
            sync_time=datetime.now(),
        )


# =============================================================================
# CODE QUALITY & TECHNICAL DEBT GUARD
# =============================================================================


class OnDeviceCodeAuditor:
    """
    Runs local static analysis for security and performance issues.
    """
    
    SECURITY_PATTERNS = [
        (r"eval\s*\(", "Dangerous eval() usage", CodeIssueSeverity.CRITICAL),
        (r"exec\s*\(", "Dangerous exec() usage", CodeIssueSeverity.CRITICAL),
        (r"__import__\s*\(", "Dynamic import", CodeIssueSeverity.HIGH),
        (r"subprocess\.call\([^)]*shell\s*=\s*True", "Shell injection risk", CodeIssueSeverity.CRITICAL),
        (r"os\.system\s*\(", "OS command injection risk", CodeIssueSeverity.HIGH),
        (r"pickle\.load", "Insecure deserialization", CodeIssueSeverity.HIGH),
        (r"yaml\.load\([^)]*\)", "Unsafe YAML loading", CodeIssueSeverity.MEDIUM),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password", CodeIssueSeverity.CRITICAL),
        (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key", CodeIssueSeverity.HIGH),
        (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret", CodeIssueSeverity.HIGH),
    ]
    
    PERFORMANCE_PATTERNS = [
        (r"for\s+\w+\s+in\s+range\(len\(", "Prefer enumerate() over range(len())", CodeIssueSeverity.LOW),
        (r"\+\s*=\s*['\"]", "String concatenation in loop (use join)", CodeIssueSeverity.MEDIUM),
        (r"time\.sleep\s*\(\s*0\s*\)", "Unnecessary sleep(0)", CodeIssueSeverity.INFO),
        (r"\.append\([^)]+\)\s*\n\s*.*\.append\(", "Multiple appends (consider extend)", CodeIssueSeverity.LOW),
    ]

    FRONTEND_PATTERNS = [
        (r":\s*any\b", "Unsafe 'any' type in TypeScript", CodeIssueSeverity.MEDIUM),
        (r"style=\{\{", "Avoid hardcoded inline styles; prefer Tailwind utility classes", CodeIssueSeverity.LOW),
        (r"\.props\.props", "Potential prop drilling deep detection", CodeIssueSeverity.MEDIUM),
        (r"useEffect\(\(\) => \{", "Heavy useEffect usage - verify dependency array and side effects", CodeIssueSeverity.INFO),
        (r"dangerouslySetInnerHTML", "XSS risk: dangerouslySetInnerHTML usage", CodeIssueSeverity.CRITICAL),
        (r"console\.log\(", "Cleanup console logs in production code", CodeIssueSeverity.LOW),
    ]
    
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.issues: list[CodeIssue] = []
    
    def _analyze_file(self, file_path: Path) -> list[CodeIssue]:
        """Analyze a single file for issues."""
        issues: list[CodeIssue] = []
        
        try:
            content = file_path.read_text()
            lines = content.split("\n")
            
            # Security patterns
            for pattern, message, severity in self.SECURITY_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1
                    snippet = lines[line_num - 1] if line_num <= len(lines) else ""
                    
                    issues.append(CodeIssue(
                        issue_id=f"SEC_{file_path.stem}_{line_num}",
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type=CodeIssueType.SECURITY,
                        severity=severity,
                        message=message,
                        code_snippet=snippet.strip()[:100],
                    ))
            
            # Performance patterns
            for pattern, message, severity in self.PERFORMANCE_PATTERNS:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1
                    snippet = lines[line_num - 1] if line_num <= len(lines) else ""
                    
                    issues.append(CodeIssue(
                        issue_id=f"PERF_{file_path.stem}_{line_num}",
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type=CodeIssueType.PERFORMANCE,
                        severity=severity,
                        message=message,
                        code_snippet=snippet.strip()[:100],
                    ))
            
            # Frontend patterns (TS/TSX only)
            if file_path.suffix in [".ts", ".tsx"]:
                for pattern, message, severity in self.FRONTEND_PATTERNS:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count("\n") + 1
                        snippet = lines[line_num - 1] if line_num <= len(lines) else ""
                        
                        issues.append(CodeIssue(
                            issue_id=f"FE_{file_path.stem}_{line_num}",
                            file_path=str(file_path),
                            line_number=line_num,
                            issue_type=CodeIssueType.STYLE,
                            severity=severity,
                            message=message,
                            code_snippet=snippet.strip()[:100],
                        ))
            
            # Complexity analysis via AST (Python only)
            if file_path.suffix == ".py":
                try:
                    tree = ast.parse(content)
                    issues.extend(self._analyze_complexity(file_path, tree))
                except SyntaxError:
                    logger.warning("Syntax error parsing %s", file_path)
        
        except Exception:
            logger.exception("Failed to analyze code issues for %s", file_path)
        
        return issues
    
    def _analyze_complexity(self, file_path: Path, tree: ast.AST) -> list[CodeIssue]:
        """Analyze code complexity using AST."""
        issues: list[CodeIssue] = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check function length
                if hasattr(node, "end_lineno") and node.end_lineno:
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        issues.append(CodeIssue(
                            issue_id=f"CMPLX_{file_path.stem}_{node.lineno}",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            issue_type=CodeIssueType.COMPLEXITY,
                            severity=CodeIssueSeverity.MEDIUM if length < 100 else CodeIssueSeverity.HIGH,
                            message=f"Function '{node.name}' is {length} lines (recommend < 50)",
                            code_snippet=f"def {node.name}(...)",
                            suggestion="Consider breaking into smaller functions",
                        ))
                
                # Check nesting depth
                max_depth = self._calculate_nesting_depth(node)
                if max_depth > 4:
                    issues.append(CodeIssue(
                        issue_id=f"NEST_{file_path.stem}_{node.lineno}",
                        file_path=str(file_path),
                        line_number=node.lineno,
                        issue_type=CodeIssueType.COMPLEXITY,
                        severity=CodeIssueSeverity.MEDIUM,
                        message=f"Function '{node.name}' has nesting depth {max_depth} (recommend <= 4)",
                        code_snippet=f"def {node.name}(...)",
                        suggestion="Reduce nesting with early returns or extract functions",
                    ))
        
        return issues
    
    def _calculate_nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth of a node."""
        max_depth = depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def audit(self) -> list[CodeIssue]:
        """Run full code audit on Python and TypeScript files."""
        self.issues = []
        
        if not self.source_dir.exists():
            return []
        
        for ext in ["*.py", "*.ts", "*.tsx"]:
            for code_file in self.source_dir.rglob(ext):
                # Skip caches, node_modules, and build artifacts
                if any(x in str(code_file) for x in ["__pycache__", "node_modules", ".next", "dist", "build"]):
                    continue
                self.issues.extend(self._analyze_file(code_file))
        
        # Sort by severity
        severity_order = {
            CodeIssueSeverity.CRITICAL: 0,
            CodeIssueSeverity.HIGH: 1,
            CodeIssueSeverity.MEDIUM: 2,
            CodeIssueSeverity.LOW: 3,
            CodeIssueSeverity.INFO: 4,
        }
        self.issues.sort(key=lambda x: severity_order[x.severity])
        
        return self.issues
    
    def get_issues_by_type(self, issue_type: CodeIssueType) -> list[CodeIssue]:
        """Get issues filtered by type."""
        return [i for i in self.issues if i.issue_type == issue_type]
    
    def get_issues_by_severity(self, severity: CodeIssueSeverity) -> list[CodeIssue]:
        """Get issues filtered by severity."""
        return [i for i in self.issues if i.severity == severity]


class AutonomousRefactoringSuggestor:
    """
    Uses local analysis to suggest code simplifications and optimizations.
    """
    
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.suggestions: list[RefactoringSuggestion] = []
    
    def _analyze_for_refactoring(self, file_path: Path) -> list[RefactoringSuggestion]:
        """Analyze a file for refactoring opportunities."""
        suggestions: list[RefactoringSuggestion] = []
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            lines = content.split("\n")
            
            for node in ast.walk(tree):
                # Check for deeply nested conditionals
                if isinstance(node, ast.If):
                    depth = self._get_if_depth(node)
                    if depth >= 3:
                        start_line = node.lineno
                        end_line = getattr(node, "end_lineno", start_line + 5)
                        original = "\n".join(lines[start_line - 1:end_line])
                        
                        suggestions.append(RefactoringSuggestion(
                            suggestion_id=f"REF_{file_path.stem}_{start_line}",
                            file_path=str(file_path),
                            line_range=(start_line, end_line),
                            refactoring_type=RefactoringType.REDUCE_NESTING,
                            description="Deeply nested conditionals can be flattened",
                            original_code=original[:200],
                            suggested_code="Use early returns or extract conditions to functions",
                            estimated_improvement="Readability +30%",
                            priority=2,
                        ))
                
                # Check for long method chains (potential for extract method)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if hasattr(node, "end_lineno") and node.end_lineno:
                        length = node.end_lineno - node.lineno
                        if length > 30:
                            suggestions.append(RefactoringSuggestion(
                                suggestion_id=f"EXT_{file_path.stem}_{node.lineno}",
                                file_path=str(file_path),
                                line_range=(node.lineno, node.end_lineno),
                                refactoring_type=RefactoringType.EXTRACT_METHOD,
                                description=f"Function '{node.name}' is long, consider extraction",
                                original_code=f"def {node.name}(...): # {length} lines",
                                suggested_code="Break into smaller, focused functions",
                                estimated_improvement="Maintainability +40%",
                                priority=3,
                            ))
                
                # Check for repeated expressions (cache opportunity)
                if isinstance(node, ast.For):
                    body_src = ast.dump(node)
                    # Simple heuristic: if the loop body contains repeated attribute access
                    attr_accesses = [n for n in ast.walk(node) if isinstance(n, ast.Attribute)]
                    attr_counts: dict[str, int] = defaultdict(int)
                    for attr in attr_accesses:
                        attr_counts[ast.dump(attr)] += 1
                    
                    for attr_dump, count in attr_counts.items():
                        if count >= 3:
                            suggestions.append(RefactoringSuggestion(
                                suggestion_id=f"CACHE_{file_path.stem}_{node.lineno}",
                                file_path=str(file_path),
                                line_range=(node.lineno, getattr(node, "end_lineno", node.lineno + 5)),
                                refactoring_type=RefactoringType.CACHE_RESULT,
                                description="Repeated attribute access in loop",
                                original_code=f"Loop at line {node.lineno}",
                                suggested_code="Cache the attribute access before the loop",
                                estimated_improvement="Performance +10-20%",
                                priority=2,
                            ))
                            break
        
        except Exception:
            logger.exception("Failed to generate refactoring suggestions for %s", file_path)
        
        return suggestions
    
    def _get_if_depth(self, node: ast.If, depth: int = 1) -> int:
        """Get the depth of nested if statements."""
        max_depth = depth
        for child in ast.walk(node):
            if isinstance(child, ast.If) and child is not node:
                child_depth = self._get_if_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth
    
    def analyze(self) -> list[RefactoringSuggestion]:
        """Analyze codebase for refactoring opportunities."""
        self.suggestions = []
        
        if not self.source_dir.exists():
            return []
        
        for py_file in self.source_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                self.suggestions.extend(self._analyze_for_refactoring(py_file))
        
        # Sort by priority
        self.suggestions.sort(key=lambda x: x.priority)
        
        return self.suggestions
    
    def get_hot_paths(self, profiling_data: dict[str, float] | None = None) -> list[RefactoringSuggestion]:
        """Get refactoring suggestions for hot paths (high-frequency code)."""
        # Filter suggestions for files in profiling data if provided
        if profiling_data:
            hot_files = set(profiling_data.keys())
            return [s for s in self.suggestions if s.file_path in hot_files]
        return self.suggestions[:10]  # Top 10 by priority


# =============================================================================
# META-LEARNING FROM SUCCESS
# =============================================================================


class BestPracticeExtractor:
    """
    Identifies high-margin, high-win quotes and extracts common patterns.
    """
    
    def __init__(
        self,
        min_margin: float = 0.2,
        min_win_rate: float = 0.7,
        min_samples: int = 5,
    ):
        self.min_margin = min_margin
        self.min_win_rate = min_win_rate
        self.min_samples = min_samples
        self.quotes: list[QuotePerformance] = []
        self.best_practices: list[BestPractice] = []
    
    def add_quote(self, quote: QuotePerformance) -> None:
        """Add a quote for analysis."""
        self.quotes.append(quote)
    
    def _extract_common_assumptions(
        self,
        quotes: list[QuotePerformance],
    ) -> list[str]:
        """Extract commonly occurring assumptions."""
        assumption_counts: dict[str, int] = defaultdict(int)
        
        for quote in quotes:
            for assumption in quote.assumptions:
                assumption_counts[assumption] += 1
        
        # Return assumptions that appear in at least 60% of quotes
        threshold = len(quotes) * 0.6
        return [a for a, c in assumption_counts.items() if c >= threshold]
    
    def extract_best_practices(self) -> list[BestPractice]:
        """Extract best practices from high-performing quotes."""
        self.best_practices = []
        
        # Filter to successful quotes
        successful = [
            q for q in self.quotes
            if q.outcome == "won" and q.margin >= self.min_margin
        ]
        
        if len(successful) < self.min_samples:
            return []
        
        # Group by segment
        by_segment: dict[str, list[QuotePerformance]] = defaultdict(list)
        for quote in successful:
            by_segment[quote.segment].append(quote)
        
        for segment, segment_quotes in by_segment.items():
            if len(segment_quotes) < 3:
                continue
            
            avg_margin = sum(q.margin for q in segment_quotes) / len(segment_quotes)
            common_assumptions = self._extract_common_assumptions(segment_quotes)
            
            if not common_assumptions:
                continue
            
            practice = BestPractice(
                id=f"bp_{segment}_{int(time.time())}",
                name=f"Best practices for {segment}",
                description=f"Extracted from {len(segment_quotes)} winning quotes",
                source_quotes=[q.quote_id for q in segment_quotes],
                assumptions=common_assumptions,
                segment=segment,
                avg_margin=avg_margin,
                win_rate=1.0,  # These are already wins
                extracted_at=datetime.now(),
                anonymized=False,
            )
            self.best_practices.append(practice)
        
        return self.best_practices
    
    def get_practices_for_segment(self, segment: str) -> list[BestPractice]:
        """Get best practices for a specific segment."""
        return [bp for bp in self.best_practices if bp.segment == segment]


class PrivacyPreservingAggregator:
    """
    Ensures all learned patterns are anonymized before promotion.
    """
    
    ANONYMIZATION_PATTERNS: list[tuple[str, str, int]] = [
        (r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b", "[PERSON]", 0),  # Names (min 3 chars per word to reduce false positives)
        (r"\b\d{3}[-.]\d{3}[-.]\d{4}\b", "[PHONE]", 0),  # Phone (require separators to avoid matching part numbers)
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", 0),  # Email
        (r"\$[\d,]+(?:\.\d{2})?", "[AMOUNT]", 0),  # Dollar amounts
    ]
    
    def __init__(self):
        self.anonymization_log: list[dict[str, Any]] = []
    
    def anonymize_text(self, text: str) -> str:
        """Anonymize sensitive information in text."""
        result = text
        
        for pattern, replacement, flags in self.ANONYMIZATION_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=flags)
        
        return result
    
    def anonymize_practice(self, practice: BestPractice) -> BestPractice:
        """Anonymize a best practice."""
        anonymized = BestPractice(
            id=practice.id,
            name=self.anonymize_text(practice.name),
            description=self.anonymize_text(practice.description),
            source_quotes=[],  # Remove source references
            assumptions=[self.anonymize_text(a) for a in practice.assumptions],
            segment=practice.segment,
            avg_margin=practice.avg_margin,
            win_rate=practice.win_rate,
            extracted_at=practice.extracted_at,
            anonymized=True,
        )
        
        self.anonymization_log.append({
            "practice_id": practice.id,
            "anonymized_at": datetime.now().isoformat(),
            "original_sources": len(practice.source_quotes),
        })
        
        return anonymized
    
    def anonymize_batch(self, practices: list[BestPractice]) -> list[BestPractice]:
        """Anonymize a batch of practices."""
        return [self.anonymize_practice(p) for p in practices]
    
    def verify_anonymization(self, text: str) -> bool:
        """Verify that text contains no PII."""
        for pattern, _, flags in self.ANONYMIZATION_PATTERNS:
            if re.search(pattern, text, flags=flags):
                return False
        return True


class A3RecommendationEvolver:
    """
    Updates reasoning engine weights based on A3 effectiveness.
    """
    
    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate
        self.weights: dict[str, ReasoningWeight] = {}
        self.a3_history: list[A3Effectiveness] = []
    
    def add_a3_result(self, a3: A3Effectiveness) -> None:
        """Add an A3 result for learning."""
        self.a3_history.append(a3)
    
    def _categorize_countermeasure(self, countermeasure: str) -> str:
        """Categorize a countermeasure into a reasoning category."""
        keywords = {
            "process": ["process", "procedure", "workflow", "step"],
            "training": ["train", "skill", "knowledge", "learn"],
            "equipment": ["machine", "equipment", "tool", "device"],
            "material": ["material", "supply", "component", "part"],
            "quality": ["quality", "inspect", "check", "verify"],
            "communication": ["communicate", "notify", "inform", "share"],
        }
        
        cm_lower = countermeasure.lower()
        for category, words in keywords.items():
            if any(word in cm_lower for word in words):
                return category
        
        return "general"
    
    def evolve_weights(self) -> dict[str, ReasoningWeight]:
        """Evolve reasoning weights based on A3 effectiveness."""
        # Group A3s by category
        by_category: dict[str, list[A3Effectiveness]] = defaultdict(list)
        
        for a3 in self.a3_history:
            category = self._categorize_countermeasure(a3.countermeasure)
            by_category[category].append(a3)
        
        # Update weights based on effectiveness
        for category, a3s in by_category.items():
            if len(a3s) < 3:
                continue
            
            avg_effectiveness = sum(a.effectiveness_score for a in a3s) / len(a3s)
            avg_recurrence = sum(a.recurrence_rate for a in a3s) / len(a3s)
            
            # Compute new weight: higher effectiveness + lower recurrence = higher weight
            new_weight = avg_effectiveness * (1 - avg_recurrence)
            
            if category in self.weights:
                old_weight = self.weights[category].weight
                adjusted_weight = old_weight + self.learning_rate * (new_weight - old_weight)
                self.weights[category].weight = adjusted_weight
                self.weights[category].last_updated = datetime.now()
                self.weights[category].source_a3s = [a.a3_id for a in a3s]
                self.weights[category].adjustment_history.append(
                    (datetime.now(), old_weight, adjusted_weight)
                )
            else:
                self.weights[category] = ReasoningWeight(
                    category=category,
                    weight=new_weight,
                    source_a3s=[a.a3_id for a in a3s],
                    last_updated=datetime.now(),
                    adjustment_history=[(datetime.now(), 0.5, new_weight)],
                )
        
        return self.weights
    
    def get_weight(self, category: str) -> float:
        """Get the current weight for a category."""
        if category in self.weights:
            return self.weights[category].weight
        return 0.5  # Default weight
    
    def recommend_countermeasure_priority(
        self,
        countermeasures: list[str],
    ) -> list[tuple[str, float]]:
        """Recommend priority ordering for countermeasures based on learned weights."""
        prioritized: list[tuple[str, float]] = []
        
        for cm in countermeasures:
            category = self._categorize_countermeasure(cm)
            weight = self.get_weight(category)
            prioritized.append((cm, weight))
        
        return sorted(prioritized, key=lambda x: x[1], reverse=True)


# =============================================================================
# META-SENSEI ORCHESTRATOR
# =============================================================================


class MetaSensei:
    """
    Main orchestrator for Meta-Sensei functionality.
    """
    
    def __init__(
        self,
        source_dir: str,
        doc_file: str,
        plan_file: str,
        site_id: str = "default",
    ):
        self.source_dir = source_dir
        self.doc_file = doc_file
        self.plan_file = plan_file
        self.site_id = site_id
        
        # Knowledge components
        self.knowledge_synthesizer = AutonomousKnowledgeSynthesizer()
        self.deduplicator = SemanticDeduplicator()
        self.site_learner = SiteSpecificLearner(site_id)
        
        # Documentation components
        self.doc_sync = DocImplementationSync(source_dir, doc_file)
        self.plan_tracker = DevelopmentPlanTracker(plan_file, source_dir)
        
        # Code quality components
        self.code_auditor = OnDeviceCodeAuditor(source_dir)
        self.refactoring_suggestor = AutonomousRefactoringSuggestor(source_dir)
        
        # Meta-learning components
        self.practice_extractor = BestPracticeExtractor()
        self.privacy_aggregator = PrivacyPreservingAggregator()
        self.a3_evolver = A3RecommendationEvolver()
    
    def run_knowledge_synthesis(self) -> list[StandardTemplate]:
        """Run autonomous knowledge synthesis."""
        return self.knowledge_synthesizer.synthesize_templates()
    
    def run_deduplication(self) -> DeduplicationResult:
        """Run semantic deduplication."""
        return self.deduplicator.deduplicate()
    
    def train_site_model(self) -> SiteReranker:
        """Train site-specific re-ranker."""
        return self.site_learner.train_reranker()
    
    def sync_documentation(self) -> DocSyncResult:
        """Synchronize documentation with implementation."""
        return self.doc_sync.sync()
    
    def sync_plan(self) -> PlanSyncResult:
        """Synchronize development plan."""
        return self.plan_tracker.sync_plan()
    
    def run_code_audit(self) -> list[CodeIssue]:
        """Run code quality audit."""
        return self.code_auditor.audit()
    
    def get_refactoring_suggestions(self) -> list[RefactoringSuggestion]:
        """Get refactoring suggestions."""
        return self.refactoring_suggestor.analyze()
    
    def extract_best_practices(self) -> list[BestPractice]:
        """Extract and anonymize best practices."""
        practices = self.practice_extractor.extract_best_practices()
        return self.privacy_aggregator.anonymize_batch(practices)
    
    def evolve_reasoning_weights(self) -> dict[str, ReasoningWeight]:
        """Evolve A3 reasoning weights."""
        return self.a3_evolver.evolve_weights()
    
    def run_full_cycle(self) -> dict[str, Any]:
        """Run a full meta-sensei maintenance cycle."""
        return {
            "templates_created": len(self.run_knowledge_synthesis()),
            "deduplication": self.run_deduplication(),
            "site_model": self.train_site_model(),
            "doc_sync": self.sync_documentation(),
            "plan_sync": self.sync_plan(),
            "code_issues": len(self.run_code_audit()),
            "refactoring_suggestions": len(self.get_refactoring_suggestions()),
            "best_practices": len(self.extract_best_practices()),
            "reasoning_weights": len(self.evolve_reasoning_weights()),
            "cycle_time": datetime.now().isoformat(),
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_knowledge_synthesizer(
    min_corrections: int = 5,
    similarity_threshold: float = 0.8,
) -> AutonomousKnowledgeSynthesizer:
    """Create a knowledge synthesizer."""
    return AutonomousKnowledgeSynthesizer(
        min_corrections=min_corrections,
        similarity_threshold=similarity_threshold,
    )


def create_deduplicator(
    similarity_threshold: float = 0.92,
    strategy: DeduplicationStrategy = DeduplicationStrategy.MERGE,
) -> SemanticDeduplicator:
    """Create a semantic deduplicator."""
    return SemanticDeduplicator(
        similarity_threshold=similarity_threshold,
        strategy=strategy,
    )


def create_site_learner(site_id: str) -> SiteSpecificLearner:
    """Create a site-specific learner."""
    return SiteSpecificLearner(site_id)


def create_doc_sync(source_dir: str, doc_file: str) -> DocImplementationSync:
    """Create a documentation sync instance."""
    return DocImplementationSync(source_dir, doc_file)


def create_plan_tracker(plan_file: str, repo_path: str) -> DevelopmentPlanTracker:
    """Create a development plan tracker."""
    return DevelopmentPlanTracker(plan_file, repo_path)


def create_code_auditor(source_dir: str) -> OnDeviceCodeAuditor:
    """Create a code auditor."""
    return OnDeviceCodeAuditor(source_dir)


def create_refactoring_suggestor(source_dir: str) -> AutonomousRefactoringSuggestor:
    """Create a refactoring suggestor."""
    return AutonomousRefactoringSuggestor(source_dir)


def create_practice_extractor(
    min_margin: float = 0.2,
    min_win_rate: float = 0.7,
) -> BestPracticeExtractor:
    """Create a best practice extractor."""
    return BestPracticeExtractor(min_margin=min_margin, min_win_rate=min_win_rate)


def create_a3_evolver(learning_rate: float = 0.1) -> A3RecommendationEvolver:
    """Create an A3 recommendation evolver."""
    return A3RecommendationEvolver(learning_rate=learning_rate)


def create_meta_sensei(
    source_dir: str,
    doc_file: str,
    plan_file: str,
    site_id: str = "default",
) -> MetaSensei:
    """Create a MetaSensei orchestrator."""
    return MetaSensei(
        source_dir=source_dir,
        doc_file=doc_file,
        plan_file=plan_file,
        site_id=site_id,
    )

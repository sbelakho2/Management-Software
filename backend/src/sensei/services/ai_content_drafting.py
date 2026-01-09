"""
AI Content Drafting Service.

Comprehensive AI-powered content generation for:
- A3 Problem-Solving Reports (all sections)
- Email templates (extends ai_email_drafting)
- Knowledge-approved content only
- Human confirmation required for all outputs

This service generates draft content strictly from approved knowledge sources
and current object data, ensuring compliance and accuracy.
"""

from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================

class ContentType(str, Enum):
    """Types of content that can be drafted."""
    A3_PROBLEM = "a3_problem"
    A3_CURRENT = "a3_current"
    A3_TARGET = "a3_target"
    A3_ROOT_CAUSE = "a3_root_cause"
    A3_COUNTERMEASURES = "a3_countermeasures"
    A3_PLAN = "a3_plan"
    A3_RESULTS = "a3_results"
    A3_REFLECTION = "a3_reflection"
    A3_FULL = "a3_full"
    EMAIL = "email"
    REPORT_SUMMARY = "report_summary"
    STANDARD_WORK = "standard_work"


class DraftStatus(str, Enum):
    """Status of a draft."""
    GENERATING = "generating"
    READY = "ready"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class ConfidenceLevel(str, Enum):
    """Confidence level of generated content."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class KnowledgeSourceType(str, Enum):
    """Types of knowledge sources."""
    APPROVED_DOCUMENT = "approved_document"
    COMPANY_STANDARD = "company_standard"
    HISTORICAL_A3 = "historical_a3"
    BEST_PRACTICE = "best_practice"
    OBJECT_DATA = "object_data"
    USER_INPUT = "user_input"


class A3SectionType(str, Enum):
    """A3 report sections."""
    PROBLEM = "problem"
    CURRENT_STATE = "current_state"
    TARGET_STATE = "target_state"
    ROOT_CAUSE = "root_cause"
    COUNTERMEASURES = "countermeasures"
    IMPLEMENTATION_PLAN = "implementation_plan"
    RESULTS = "results"
    REFLECTION = "reflection"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class KnowledgeSource:
    """A source of approved knowledge used in drafting."""
    id: str
    source_type: KnowledgeSourceType
    title: str
    content_snippet: str
    relevance_score: float  # 0.0 to 1.0
    document_id: str | None = None
    url: str | None = None
    approved_date: datetime | None = None
    approved_by: str | None = None
    
    @property
    def is_approved(self) -> bool:
        """Check if source is approved for use."""
        return (
            self.source_type in (
                KnowledgeSourceType.APPROVED_DOCUMENT,
                KnowledgeSourceType.COMPANY_STANDARD,
                KnowledgeSourceType.BEST_PRACTICE,
            ) or
            self.approved_date is not None
        )


@dataclass
class DraftContent:
    """Generated draft content."""
    id: str
    content_type: ContentType
    title: str
    body: str
    status: DraftStatus
    confidence: ConfidenceLevel
    sources: list[KnowledgeSource] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    applied_at: datetime | None = None
    
    @property
    def requires_review(self) -> bool:
        """Check if draft requires human review."""
        return self.status in (DraftStatus.GENERATING, DraftStatus.READY)
    
    @property
    def has_warnings(self) -> bool:
        """Check if draft has warnings."""
        return len(self.warnings) > 0
    
    @property
    def source_ids(self) -> list[str]:
        """Get list of source IDs used."""
        return [s.id for s in self.sources]


@dataclass
class A3DraftRequest:
    """Request for A3 section draft generation."""
    a3_id: UUID
    section: A3SectionType
    context: A3Context
    user_id: UUID
    include_suggestions: bool = True
    max_length: int = 1000
    style: str = "concise"  # concise, detailed, technical


@dataclass
class A3Context:
    """Context for A3 draft generation."""
    title: str
    description: str | None = None
    category: str | None = None
    owner_name: str | None = None
    created_date: datetime | None = None
    due_date: datetime | None = None
    related_rfq_id: str | None = None
    related_quote_id: str | None = None
    current_sections: dict[str, str] = field(default_factory=dict)
    kpis: dict[str, Any] = field(default_factory=dict)
    historical_data: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class A3SectionDraft:
    """Draft for a specific A3 section."""
    section: A3SectionType
    draft_id: str
    content: str
    confidence: ConfidenceLevel
    sources: list[KnowledgeSource]
    guiding_questions: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    word_count: int = 0
    
    def __post_init__(self):
        self.word_count = len(self.content.split())


@dataclass
class A3FullDraft:
    """Complete A3 draft with all sections."""
    a3_id: str
    title: str
    sections: dict[A3SectionType, A3SectionDraft]
    overall_confidence: ConfidenceLevel
    total_sources: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_complete(self) -> bool:
        """Check if all required sections have drafts."""
        required = {
            A3SectionType.PROBLEM,
            A3SectionType.CURRENT_STATE,
            A3SectionType.TARGET_STATE,
            A3SectionType.ROOT_CAUSE,
            A3SectionType.COUNTERMEASURES,
        }
        return all(s in self.sections for s in required)
    
    def get_section_content(self, section: A3SectionType) -> str | None:
        """Get content for a specific section."""
        draft = self.sections.get(section)
        return draft.content if draft else None


@dataclass
class DraftHistory:
    """History entry for draft changes."""
    id: str
    draft_id: str
    action: str
    old_content: str | None
    new_content: str | None
    user_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str | None = None


# =============================================================================
# Templates and Patterns
# =============================================================================

A3_GUIDING_QUESTIONS: dict[A3SectionType, list[str]] = {
    A3SectionType.PROBLEM: [
        "What is the specific problem or gap?",
        "When did it start occurring?",
        "Who is affected by this problem?",
        "What is the business impact?",
        "How is this measured?",
    ],
    A3SectionType.CURRENT_STATE: [
        "What is the current process or situation?",
        "What data supports the current state?",
        "What are the current metrics?",
        "What has been tried before?",
    ],
    A3SectionType.TARGET_STATE: [
        "What does 'solved' look like?",
        "What metrics will define success?",
        "When should this be achieved?",
        "What constraints exist?",
    ],
    A3SectionType.ROOT_CAUSE: [
        "Why did the problem occur? (5 Whys)",
        "What systemic factors contributed?",
        "What evidence supports this root cause?",
        "Are there multiple contributing factors?",
    ],
    A3SectionType.COUNTERMEASURES: [
        "What actions will address the root cause?",
        "Who is responsible for each action?",
        "What resources are needed?",
        "How will effectiveness be verified?",
    ],
    A3SectionType.IMPLEMENTATION_PLAN: [
        "What is the timeline?",
        "What are the milestones?",
        "Who needs to be involved?",
        "What are the dependencies?",
    ],
    A3SectionType.RESULTS: [
        "What were the actual outcomes?",
        "Did metrics improve?",
        "Were there unintended consequences?",
        "What evidence supports the results?",
    ],
    A3SectionType.REFLECTION: [
        "What did we learn?",
        "What would we do differently?",
        "How can we prevent recurrence?",
        "What standards need updating?",
    ],
}

A3_TEMPLATES: dict[A3SectionType, str] = {
    A3SectionType.PROBLEM: """## Problem Statement

**Issue**: {problem_summary}

**Impact**: {impact_description}

**Scope**: {scope}

**Measurement**: {metric}

**Timeline**: First observed {first_observed}
""",
    A3SectionType.CURRENT_STATE: """## Current State Analysis

**Current Process**:
{current_process}

**Current Metrics**:
- {metric_1}: {value_1}
- {metric_2}: {value_2}

**Observations**:
{observations}
""",
    A3SectionType.TARGET_STATE: """## Target State

**Goal**: {goal_statement}

**Success Metrics**:
- {target_metric_1}: {target_value_1}
- {target_metric_2}: {target_value_2}

**Target Date**: {target_date}

**Constraints**:
{constraints}
""",
    A3SectionType.ROOT_CAUSE: """## Root Cause Analysis (5 Whys)

**Problem**: {problem}

1. **Why?** {why_1}
2. **Why?** {why_2}
3. **Why?** {why_3}
4. **Why?** {why_4}
5. **Why?** {why_5}

**Root Cause**: {root_cause}

**Contributing Factors**:
{factors}
""",
    A3SectionType.COUNTERMEASURES: """## Countermeasures

| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
| 1 | {action_1} | {owner_1} | {due_1} | Planned |
| 2 | {action_2} | {owner_2} | {due_2} | Planned |
| 3 | {action_3} | {owner_3} | {due_3} | Planned |

**Verification Method**: {verification}
""",
    A3SectionType.IMPLEMENTATION_PLAN: """## Implementation Plan

**Phase 1**: {phase_1} (Week 1-2)
- {task_1_1}
- {task_1_2}

**Phase 2**: {phase_2} (Week 3-4)
- {task_2_1}
- {task_2_2}

**Dependencies**: {dependencies}

**Resources Needed**: {resources}
""",
    A3SectionType.RESULTS: """## Results

**Metrics Before/After**:
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| {metric_1} | {before_1} | {after_1} | {change_1} |
| {metric_2} | {before_2} | {after_2} | {change_2} |

**Key Findings**:
{findings}

**Unintended Effects**:
{unintended}
""",
    A3SectionType.REFLECTION: """## Reflection

**What Worked Well**:
{what_worked}

**What Could Be Improved**:
{improvements}

**Lessons Learned**:
{lessons}

**Standard Work Updates**:
{standard_updates}

**Follow-up Actions**:
{followup}
""",
}


# =============================================================================
# Knowledge Base (Simulated)
# =============================================================================

class KnowledgeBase:
    """Simulated knowledge base for approved content."""
    
    def __init__(self) -> None:
        self._sources: dict[str, KnowledgeSource] = {}
        self._a3_patterns: list[dict[str, Any]] = []
        self._best_practices: list[dict[str, Any]] = []
        self._initialize_knowledge()
    
    def _initialize_knowledge(self) -> None:
        """Initialize with sample approved knowledge."""
        # Best practices for A3
        practices = [
            {
                "id": "bp-001",
                "title": "5 Whys Best Practices",
                "content": "When performing root cause analysis, ask 'why' at least 5 times, "
                          "verify each answer with data, and involve cross-functional stakeholders.",
                "tags": ["root_cause", "5_whys", "analysis"],
            },
            {
                "id": "bp-002", 
                "title": "SMART Countermeasures",
                "content": "Countermeasures should be Specific, Measurable, Achievable, "
                          "Relevant, and Time-bound. Assign a single owner to each action.",
                "tags": ["countermeasures", "smart", "planning"],
            },
            {
                "id": "bp-003",
                "title": "Problem Statement Guidelines",
                "content": "A good problem statement includes: what the problem is, "
                          "when it occurs, where it occurs, and the magnitude of impact.",
                "tags": ["problem", "statement", "definition"],
            },
            {
                "id": "bp-004",
                "title": "Reflection and Standardization",
                "content": "Always update standard work after closing an A3. "
                          "Document lessons learned and share with relevant teams.",
                "tags": ["reflection", "standard_work", "learning"],
            },
        ]
        
        for practice in practices:
            source = KnowledgeSource(
                id=practice["id"],
                source_type=KnowledgeSourceType.BEST_PRACTICE,
                title=practice["title"],
                content_snippet=practice["content"],
                relevance_score=0.9,
                approved_date=datetime.now(timezone.utc),
            )
            self._sources[source.id] = source
            self._best_practices.append(practice)
    
    def search_sources(
        self,
        query: str,
        source_types: list[KnowledgeSourceType] | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[KnowledgeSource]:
        """Search for relevant knowledge sources."""
        results: list[KnowledgeSource] = []
        query_lower = query.lower()
        
        for source in self._sources.values():
            if source_types and source.source_type not in source_types:
                continue
            
            # Simple relevance scoring
            score = 0.0
            if query_lower in source.title.lower():
                score += 0.5
            if query_lower in source.content_snippet.lower():
                score += 0.3
            
            # Check tags in best practices
            if tags:
                for practice in self._best_practices:
                    if practice["id"] == source.id:
                        matching_tags = set(tags) & set(practice.get("tags", []))
                        score += len(matching_tags) * 0.2
            
            if score > 0:
                source.relevance_score = min(score, 1.0)
                results.append(source)
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]
    
    def get_source(self, source_id: str) -> KnowledgeSource | None:
        """Get a specific knowledge source."""
        return self._sources.get(source_id)
    
    def add_source(self, source: KnowledgeSource) -> None:
        """Add a new knowledge source."""
        self._sources[source.id] = source
    
    def get_a3_patterns(
        self,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get historical A3 patterns for learning."""
        if category:
            filtered = [p for p in self._a3_patterns if p.get("category") == category]
            return filtered[:limit]
        return self._a3_patterns[:limit]


# =============================================================================
# AI Drafting Service
# =============================================================================

class AIDraftingService:
    """
    Service for generating AI-drafted content.
    
    All generated content:
    - Uses only approved knowledge sources
    - Requires human confirmation before use
    - Provides transparency on sources used
    - Includes confidence levels and warnings
    """
    
    def __init__(self) -> None:
        self._knowledge_base = KnowledgeBase()
        self._drafts: dict[str, DraftContent] = {}
        self._a3_drafts: dict[str, A3FullDraft] = {}
        self._history: list[DraftHistory] = []
    
    # -------------------------------------------------------------------------
    # A3 Drafting
    # -------------------------------------------------------------------------
    
    def draft_a3_section(
        self,
        request: A3DraftRequest,
    ) -> A3SectionDraft:
        """Generate a draft for a specific A3 section."""
        # Get guiding questions for the section
        guiding_questions = A3_GUIDING_QUESTIONS.get(request.section, [])
        
        # Search for relevant knowledge
        sources = self._knowledge_base.search_sources(
            query=f"{request.section.value} {request.context.title}",
            tags=[request.section.value],
            limit=3,
        )
        
        # Generate content based on section type
        content = self._generate_a3_section_content(
            section=request.section,
            context=request.context,
            style=request.style,
            max_length=request.max_length,
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            content=content,
            sources=sources,
            context=request.context,
        )
        
        # Generate suggestions
        suggestions = []
        if request.include_suggestions:
            suggestions = self._generate_suggestions(
                section=request.section,
                content=content,
                context=request.context,
            )
        
        # Check for warnings
        warnings = self._check_content_warnings(content, sources)
        
        draft = A3SectionDraft(
            section=request.section,
            draft_id=str(uuid4()),
            content=content,
            confidence=confidence,
            sources=sources,
            guiding_questions=guiding_questions,
            suggestions=suggestions,
            warnings=warnings,
        )
        
        return draft
    
    def draft_full_a3(
        self,
        a3_id: UUID,
        context: A3Context,
        user_id: UUID,
        sections: list[A3SectionType] | None = None,
    ) -> A3FullDraft:
        """Generate drafts for all (or specified) A3 sections."""
        if sections is None:
            sections = list(A3SectionType)
        
        section_drafts: dict[A3SectionType, A3SectionDraft] = {}
        all_sources: set[str] = set()
        
        for section in sections:
            request = A3DraftRequest(
                a3_id=a3_id,
                section=section,
                context=context,
                user_id=user_id,
            )
            draft = self.draft_a3_section(request)
            section_drafts[section] = draft
            all_sources.update(s.id for s in draft.sources)
        
        # Calculate overall confidence
        confidence_scores = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.UNCERTAIN: 0.2,
        }
        avg_score = sum(
            confidence_scores[d.confidence] for d in section_drafts.values()
        ) / len(section_drafts) if section_drafts else 0.5
        
        if avg_score >= 0.8:
            overall_confidence = ConfidenceLevel.HIGH
        elif avg_score >= 0.6:
            overall_confidence = ConfidenceLevel.MEDIUM
        elif avg_score >= 0.4:
            overall_confidence = ConfidenceLevel.LOW
        else:
            overall_confidence = ConfidenceLevel.UNCERTAIN
        
        full_draft = A3FullDraft(
            a3_id=str(a3_id),
            title=context.title,
            sections=section_drafts,
            overall_confidence=overall_confidence,
            total_sources=len(all_sources),
        )
        
        self._a3_drafts[str(a3_id)] = full_draft
        return full_draft
    
    def _generate_a3_section_content(
        self,
        section: A3SectionType,
        context: A3Context,
        style: str,
        max_length: int,
    ) -> str:
        """Generate content for an A3 section using context."""
        template = A3_TEMPLATES.get(section, "")
        
        # Build content based on section type and context
        if section == A3SectionType.PROBLEM:
            content = self._draft_problem_section(context, style)
        elif section == A3SectionType.CURRENT_STATE:
            content = self._draft_current_state_section(context, style)
        elif section == A3SectionType.TARGET_STATE:
            content = self._draft_target_state_section(context, style)
        elif section == A3SectionType.ROOT_CAUSE:
            content = self._draft_root_cause_section(context, style)
        elif section == A3SectionType.COUNTERMEASURES:
            content = self._draft_countermeasures_section(context, style)
        elif section == A3SectionType.IMPLEMENTATION_PLAN:
            content = self._draft_implementation_section(context, style)
        elif section == A3SectionType.RESULTS:
            content = self._draft_results_section(context, style)
        elif section == A3SectionType.REFLECTION:
            content = self._draft_reflection_section(context, style)
        else:
            content = f"[Draft content for {section.value}]"
        
        # Truncate if needed
        words = content.split()
        if len(words) > max_length:
            content = " ".join(words[:max_length]) + "..."
        
        return content
    
    def _draft_problem_section(self, context: A3Context, style: str) -> str:
        """Draft the problem statement section."""
        lines = []
        lines.append("## Problem Statement\n")
        lines.append(f"**Issue**: {context.title}")
        
        if context.description:
            lines.append(f"\n**Description**: {context.description}")
        
        if context.category:
            lines.append(f"\n**Category**: {context.category}")
        
        # Add impact based on available data
        if context.kpis:
            impact_items = []
            for kpi, value in list(context.kpis.items())[:3]:
                impact_items.append(f"- {kpi}: {value}")
            if impact_items:
                lines.append("\n**Impact Metrics**:")
                lines.extend(impact_items)
        
        if context.created_date:
            lines.append(f"\n**First Observed**: {context.created_date.strftime('%Y-%m-%d')}")
        
        return "\n".join(lines)
    
    def _draft_current_state_section(self, context: A3Context, style: str) -> str:
        """Draft the current state analysis section."""
        lines = []
        lines.append("## Current State Analysis\n")
        
        # Use existing section content if available
        if "current_state" in context.current_sections:
            lines.append(context.current_sections["current_state"])
        else:
            lines.append("**Current Situation**:")
            lines.append(f"The current process related to '{context.title}' "
                        "requires analysis and documentation.")
        
        if context.kpis:
            lines.append("\n**Current Metrics**:")
            for kpi, value in context.kpis.items():
                lines.append(f"- {kpi}: {value}")
        
        lines.append("\n**Observations**:")
        lines.append("- [Add specific observations from gemba walks]")
        lines.append("- [Include data-driven insights]")
        lines.append("- [Document stakeholder feedback]")
        
        return "\n".join(lines)
    
    def _draft_target_state_section(self, context: A3Context, style: str) -> str:
        """Draft the target state section."""
        lines = []
        lines.append("## Target State\n")
        
        lines.append(f"**Goal**: Resolve '{context.title}' to achieve measurable improvement.")
        
        if context.due_date:
            lines.append(f"\n**Target Date**: {context.due_date.strftime('%Y-%m-%d')}")
        
        lines.append("\n**Success Criteria**:")
        lines.append("- [ ] Problem occurrence reduced by [X]%")
        lines.append("- [ ] Process time improved by [X] minutes")
        lines.append("- [ ] Zero recurrence for [X] days")
        
        lines.append("\n**Constraints**:")
        lines.append("- Budget limitations")
        lines.append("- Resource availability")
        lines.append("- Timeline requirements")
        
        return "\n".join(lines)
    
    def _draft_root_cause_section(self, context: A3Context, style: str) -> str:
        """Draft the root cause analysis section."""
        lines = []
        lines.append("## Root Cause Analysis (5 Whys)\n")
        
        lines.append(f"**Problem**: {context.title}\n")
        
        lines.append("**Why #1**: [First level cause - immediate reason]")
        lines.append("↓")
        lines.append("**Why #2**: [Second level cause - why did #1 happen?]")
        lines.append("↓")
        lines.append("**Why #3**: [Third level cause - why did #2 happen?]")
        lines.append("↓")
        lines.append("**Why #4**: [Fourth level cause - why did #3 happen?]")
        lines.append("↓")
        lines.append("**Why #5**: [Root cause - systemic issue]")
        
        lines.append("\n**Root Cause Summary**:")
        lines.append("The underlying root cause appears to be related to "
                    "[process/system/training] gaps that allowed this issue to occur.")
        
        lines.append("\n**Contributing Factors**:")
        lines.append("- Environmental factors")
        lines.append("- Process design issues")
        lines.append("- Communication gaps")
        lines.append("- Training deficiencies")
        
        return "\n".join(lines)
    
    def _draft_countermeasures_section(self, context: A3Context, style: str) -> str:
        """Draft the countermeasures section."""
        lines = []
        lines.append("## Countermeasures\n")
        
        owner = context.owner_name or "[Assign Owner]"
        
        lines.append("| # | Action | Owner | Due Date | Status |")
        lines.append("|---|--------|-------|----------|--------|")
        lines.append(f"| 1 | Immediate containment action | {owner} | +3 days | Planned |")
        lines.append(f"| 2 | Process improvement action | {owner} | +2 weeks | Planned |")
        lines.append(f"| 3 | Standard work update | {owner} | +3 weeks | Planned |")
        lines.append(f"| 4 | Training/communication | {owner} | +4 weeks | Planned |")
        
        lines.append("\n**Verification Method**:")
        lines.append("- Metric monitoring for [X] weeks")
        lines.append("- Audit of updated process")
        lines.append("- Stakeholder feedback collection")
        
        return "\n".join(lines)
    
    def _draft_implementation_section(self, context: A3Context, style: str) -> str:
        """Draft the implementation plan section."""
        lines = []
        lines.append("## Implementation Plan\n")
        
        lines.append("**Phase 1: Immediate Actions (Week 1)**")
        lines.append("- [ ] Containment measures implemented")
        lines.append("- [ ] Stakeholders notified")
        lines.append("- [ ] Baseline metrics captured")
        
        lines.append("\n**Phase 2: Root Cause Countermeasures (Week 2-3)**")
        lines.append("- [ ] Process changes implemented")
        lines.append("- [ ] Documentation updated")
        lines.append("- [ ] Initial verification completed")
        
        lines.append("\n**Phase 3: Sustainment (Week 4+)**")
        lines.append("- [ ] Standard work updated")
        lines.append("- [ ] Training completed")
        lines.append("- [ ] Monitoring system in place")
        
        lines.append("\n**Resources Required**:")
        lines.append("- Team time allocation")
        lines.append("- Tool/system access")
        lines.append("- Budget for changes")
        
        return "\n".join(lines)
    
    def _draft_results_section(self, context: A3Context, style: str) -> str:
        """Draft the results section."""
        lines = []
        lines.append("## Results\n")
        
        lines.append("**Metrics Comparison**:")
        lines.append("| Metric | Before | After | % Change |")
        lines.append("|--------|--------|-------|----------|")
        lines.append("| [Primary KPI] | [X] | [Y] | [Z]% |")
        lines.append("| [Secondary KPI] | [X] | [Y] | [Z]% |")
        
        lines.append("\n**Key Findings**:")
        lines.append("- [Summarize main outcomes]")
        lines.append("- [Document unexpected discoveries]")
        
        lines.append("\n**Evidence**:")
        lines.append("- Data charts/graphs attached")
        lines.append("- Audit results documented")
        lines.append("- Stakeholder feedback collected")
        
        lines.append("\n**Unintended Consequences**:")
        lines.append("- [Note any side effects of changes]")
        
        return "\n".join(lines)
    
    def _draft_reflection_section(self, context: A3Context, style: str) -> str:
        """Draft the reflection section."""
        lines = []
        lines.append("## Reflection\n")
        
        lines.append("**What Worked Well**:")
        lines.append("- Cross-functional collaboration")
        lines.append("- Data-driven analysis")
        lines.append("- Structured problem-solving approach")
        
        lines.append("\n**What Could Be Improved**:")
        lines.append("- Earlier escalation")
        lines.append("- More frequent check-ins")
        lines.append("- Better initial scoping")
        
        lines.append("\n**Lessons Learned**:")
        lines.append("1. [Key insight from this A3]")
        lines.append("2. [Process improvement identified]")
        lines.append("3. [Knowledge to share with others]")
        
        lines.append("\n**Standard Work Updates Required**:")
        lines.append("- [ ] Update [specific procedure]")
        lines.append("- [ ] Add checklist for [process]")
        lines.append("- [ ] Create training material for [topic]")
        
        lines.append("\n**Follow-up Actions**:")
        lines.append("- Schedule 30-day review")
        lines.append("- Share learnings with team")
        lines.append("- Update risk register if applicable")
        
        return "\n".join(lines)
    
    def _calculate_confidence(
        self,
        content: str,
        sources: list[KnowledgeSource],
        context: A3Context,
    ) -> ConfidenceLevel:
        """Calculate confidence level for generated content."""
        score = 0.5  # Base score
        
        # Increase for approved sources
        approved_sources = [s for s in sources if s.is_approved]
        score += len(approved_sources) * 0.1
        
        # Increase for context richness
        if context.description:
            score += 0.1
        if context.kpis:
            score += 0.1
        if context.historical_data:
            score += 0.1
        
        # Decrease for placeholder content
        placeholder_count = content.count("[") + content.count("X]")
        score -= placeholder_count * 0.02
        
        # Clamp and convert
        score = max(0.0, min(1.0, score))
        
        if score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN
    
    def _generate_suggestions(
        self,
        section: A3SectionType,
        content: str,
        context: A3Context,
    ) -> list[str]:
        """Generate improvement suggestions for the draft."""
        suggestions = []
        
        # Generic suggestions based on section
        if section == A3SectionType.PROBLEM:
            if "impact" not in content.lower():
                suggestions.append("Consider adding business impact metrics")
            if len(content.split()) < 50:
                suggestions.append("Expand the problem description with more specific details")
        
        elif section == A3SectionType.ROOT_CAUSE:
            if content.count("Why") < 5:
                suggestions.append("Ensure all 5 'Why' levels are explored")
            suggestions.append("Verify each 'Why' with supporting data")
        
        elif section == A3SectionType.COUNTERMEASURES:
            if "owner" not in content.lower():
                suggestions.append("Assign specific owners to each action")
            suggestions.append("Ensure countermeasures address the root cause directly")
        
        elif section == A3SectionType.REFLECTION:
            suggestions.append("Document specific lessons that can help prevent recurrence")
            suggestions.append("Identify which standard work documents need updating")
        
        return suggestions
    
    def _check_content_warnings(
        self,
        content: str,
        sources: list[KnowledgeSource],
    ) -> list[str]:
        """Check content for potential issues."""
        warnings = []
        
        # Check for unapproved sources
        unapproved = [s for s in sources if not s.is_approved]
        if unapproved:
            warnings.append(f"{len(unapproved)} source(s) pending approval")
        
        # Check for placeholder content
        placeholder_count = content.count("[") 
        if placeholder_count > 5:
            warnings.append("Content contains multiple placeholders requiring user input")
        
        # Check for missing critical elements
        if len(content) < 100:
            warnings.append("Content may be too brief - consider expanding")
        
        return warnings
    
    # -------------------------------------------------------------------------
    # Draft Management
    # -------------------------------------------------------------------------
    
    def create_draft(
        self,
        content_type: ContentType,
        title: str,
        body: str,
        sources: list[KnowledgeSource] | None = None,
        user_id: str | None = None,
    ) -> DraftContent:
        """Create a new draft content entry."""
        draft = DraftContent(
            id=str(uuid4()),
            content_type=content_type,
            title=title,
            body=body,
            status=DraftStatus.READY,
            confidence=ConfidenceLevel.MEDIUM,
            sources=sources or [],
            created_by=user_id,
        )
        self._drafts[draft.id] = draft
        return draft
    
    def get_draft(self, draft_id: str) -> DraftContent | None:
        """Get a draft by ID."""
        return self._drafts.get(draft_id)
    
    def list_drafts(
        self,
        content_type: ContentType | None = None,
        status: DraftStatus | None = None,
        user_id: str | None = None,
    ) -> list[DraftContent]:
        """List drafts with optional filters."""
        results = list(self._drafts.values())
        
        if content_type:
            results = [d for d in results if d.content_type == content_type]
        if status:
            results = [d for d in results if d.status == status]
        if user_id:
            results = [d for d in results if d.created_by == user_id]
        
        return sorted(results, key=lambda d: d.created_at, reverse=True)
    
    def review_draft(
        self,
        draft_id: str,
        user_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> DraftContent | None:
        """Review and approve/reject a draft."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return None
        
        old_status = draft.status
        draft.reviewed_at = datetime.now(timezone.utc)
        draft.reviewed_by = user_id
        
        if approved:
            draft.status = DraftStatus.APPROVED
        else:
            draft.status = DraftStatus.REJECTED
            if feedback:
                draft.warnings.append(f"Rejection reason: {feedback}")
        
        # Record history
        self._history.append(DraftHistory(
            id=str(uuid4()),
            draft_id=draft_id,
            action=f"status_change: {old_status.value} -> {draft.status.value}",
            old_content=None,
            new_content=None,
            user_id=user_id,
            reason=feedback,
        ))
        
        return draft
    
    def apply_draft(
        self,
        draft_id: str,
        user_id: str,
    ) -> DraftContent | None:
        """Mark a draft as applied (used in the system)."""
        draft = self._drafts.get(draft_id)
        if not draft or draft.status != DraftStatus.APPROVED:
            return None
        
        draft.status = DraftStatus.APPLIED
        draft.applied_at = datetime.now(timezone.utc)
        
        self._history.append(DraftHistory(
            id=str(uuid4()),
            draft_id=draft_id,
            action="applied",
            old_content=None,
            new_content=None,
            user_id=user_id,
        ))
        
        return draft
    
    def get_draft_history(self, draft_id: str) -> list[DraftHistory]:
        """Get history for a specific draft."""
        return [h for h in self._history if h.draft_id == draft_id]
    
    def get_a3_draft(self, a3_id: str) -> A3FullDraft | None:
        """Get a full A3 draft."""
        return self._a3_drafts.get(a3_id)
    
    # -------------------------------------------------------------------------
    # Knowledge Management
    # -------------------------------------------------------------------------
    
    def add_knowledge_source(self, source: KnowledgeSource) -> None:
        """Add a knowledge source to the base."""
        self._knowledge_base.add_source(source)
    
    def search_knowledge(
        self,
        query: str,
        limit: int = 5,
    ) -> list[KnowledgeSource]:
        """Search the knowledge base."""
        return self._knowledge_base.search_sources(query, limit=limit)
    
    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    
    def clear_all(self) -> None:
        """Clear all drafts (for testing)."""
        self._drafts.clear()
        self._a3_drafts.clear()
        self._history.clear()


# =============================================================================
# Service Singleton
# =============================================================================

_service_instance: AIDraftingService | None = None


def get_ai_drafting_service() -> AIDraftingService:
    """Get the singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AIDraftingService()
    return _service_instance


def reset_ai_drafting_service() -> None:
    """Reset the service (for testing)."""
    global _service_instance
    if _service_instance:
        _service_instance.clear_all()
    _service_instance = None

"""
Just-in-Time Lean Learning & Knowledge Synthesis.

Closes the loop between theoretical knowledge and operational reality.
Provides contextual micro-lessons, knowledge retrieval, and standard work evolution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.strategic_v2 import LessonDeliveryRecord, StandardWorkEvolutionRecord


# =============================================================================
# ENUMS
# =============================================================================


class LessonCategory(Enum):
    """Categories of lean micro-lessons."""
    
    SMED = "smed"  # Single-Minute Exchange of Die
    FIVE_S = "five_s"  # 5S Workplace Organization
    POKA_YOKE = "poka_yoke"  # Mistake-Proofing
    KANBAN = "kanban"  # Pull System
    TPM = "tpm"  # Total Productive Maintenance
    VSM = "vsm"  # Value Stream Mapping
    JIDOKA = "jidoka"  # Autonomation
    KAIZEN = "kaizen"  # Continuous Improvement
    HEIJUNKA = "heijunka"  # Production Leveling
    STANDARD_WORK = "standard_work"


class TriggerType(Enum):
    """Types of triggers for micro-lessons."""
    
    HIGH_CHANGEOVER_TIME = "high_changeover_time"
    HIGH_DEFECT_RATE = "high_defect_rate"
    LOW_OEE = "low_oee"
    HIGH_INVENTORY = "high_inventory"
    WAITING_WASTE = "waiting_waste"
    QUALITY_ISSUE = "quality_issue"
    EQUIPMENT_FAILURE = "equipment_failure"
    NEW_OPERATOR = "new_operator"
    A3_STARTED = "a3_started"
    PERFORMANCE_GAP = "performance_gap"


class LessonStatus(Enum):
    """Status of a micro-lesson delivery."""
    
    PENDING = "pending"
    DELIVERED = "delivered"
    VIEWED = "viewed"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class StandardWorkStatus(Enum):
    """Status of a standard work document."""
    
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class PerformerLevel(Enum):
    """Performance level classifications."""
    
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"
    SUPER_PERFORMER = "super_performer"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class MicroLesson:
    """A contextual lean micro-lesson (60-second bite-sized learning)."""
    
    lesson_id: str
    category: LessonCategory
    title: str
    summary: str
    content: str  # Main lesson content
    duration_seconds: int = 60
    key_takeaways: list[str] = field(default_factory=list)
    related_tools: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class LessonDelivery:
    """A delivery of a micro-lesson to a user/context."""
    
    delivery_id: str
    lesson_id: str
    trigger_type: TriggerType
    trigger_context: dict[str, Any]
    recipient_id: str
    delivered_at: datetime
    status: LessonStatus = LessonStatus.PENDING
    viewed_at: datetime | None = None
    completed_at: datetime | None = None
    feedback_rating: int | None = None  # 1-5
    feedback_comment: str = ""


@dataclass
class KnowledgeDocument:
    """A TPS standard document in the knowledge pack."""
    
    document_id: str
    title: str
    category: LessonCategory
    summary: str
    content: str
    keywords: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    related_a3_fields: list[str] = field(default_factory=list)


@dataclass
class KnowledgeLink:
    """A link from an A3 field to relevant knowledge documents."""
    
    link_id: str
    a3_id: str
    a3_field: str  # e.g., "root_cause", "countermeasure", "problem_statement"
    document_ids: list[str]
    relevance_score: float  # 0-1
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StandardWork:
    """A standard work document."""
    
    standard_id: str
    title: str
    process_name: str
    work_center_id: str
    version: str
    content: str
    steps: list[dict[str, Any]]
    cycle_time_seconds: int
    key_points: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    quality_checks: list[str] = field(default_factory=list)
    status: StandardWorkStatus = StandardWorkStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_a3_id: str | None = None


@dataclass
class StandardWorkDraft:
    """A draft update for standard work from A3 countermeasure."""
    
    draft_id: str
    source_a3_id: str
    source_countermeasure: str
    target_standard_id: str | None  # None if new standard
    proposed_changes: dict[str, Any]
    rationale: str
    created_at: datetime
    status: str = "pending"
    reviewed_by: str | None = None
    approved_at: datetime | None = None


@dataclass
class OperatorPerformance:
    """Operator performance metrics for identifying super-performers."""
    
    operator_id: str
    name: str
    work_center_id: str
    oee_score: float  # 0-100
    quality_score: float  # 0-100
    productivity_score: float  # 0-100
    overall_score: float = 0.0
    level: PerformerLevel = PerformerLevel.DEVELOPING
    techniques: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate overall score and level."""
        self.overall_score = (
            self.oee_score * 0.4 +
            self.quality_score * 0.35 +
            self.productivity_score * 0.25
        )
        
        if self.overall_score >= 95:
            self.level = PerformerLevel.SUPER_PERFORMER
        elif self.overall_score >= 85:
            self.level = PerformerLevel.ADVANCED
        elif self.overall_score >= 70:
            self.level = PerformerLevel.PROFICIENT
        else:
            self.level = PerformerLevel.DEVELOPING


@dataclass
class BestPracticeSuggestion:
    """A suggestion to codify super-performer techniques."""
    
    suggestion_id: str
    super_performer_id: str
    super_performer_name: str
    technique: str
    observed_benefit: str
    current_baseline: float
    performer_result: float
    improvement_potential: float
    suggested_at: datetime
    status: str = "pending"
    target_standard_id: str | None = None


# =============================================================================
# MICRO-LESSON ENGINE
# =============================================================================


class MicroLessonEngine:
    """
    Contextual Lean Micro-Lesson Engine with DB persistence.
    
    Delivers 60-second lessons triggered by operational conditions.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.lessons: dict[str, MicroLesson] = {}
        self.trigger_mappings: dict[TriggerType, list[LessonCategory]] = {}
        
        self._initialize_lessons()
        self._initialize_trigger_mappings()
    
    async def deliver_lesson(
        self,
        db: AsyncSession,
        lesson_id: str,
        recipient_id: UUID,
        trigger_type: TriggerType,
        context: dict[str, Any] | None = None,
    ) -> LessonDeliveryRecord:
        """Deliver a micro-lesson and persist to database."""
        delivery = LessonDeliveryRecord(
            lesson_id=lesson_id,
            recipient_id=recipient_id,
            trigger_type=trigger_type.value,
            trigger_context=context or {},
            status="delivered",
        )
        db.add(delivery)
        await db.commit()
        await db.refresh(delivery)
        return delivery

    async def get_user_deliveries(self, db: AsyncSession, user_id: UUID) -> list[LessonDeliveryRecord]:
        """Get all lesson deliveries for a user."""
        stmt = select(LessonDeliveryRecord).where(LessonDeliveryRecord.recipient_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    def _initialize_lessons(self) -> None:
        """Initialize the lesson library."""
        lessons = [
            MicroLesson(
                lesson_id="smed_intro",
                category=LessonCategory.SMED,
                title="SMED: Quick Changeover Basics",
                summary="Learn how to reduce changeover time using Single-Minute Exchange of Die",
                content="""SMED (Single-Minute Exchange of Die) is a system for dramatically 
                reducing changeover time.

                **Key Principle**: Separate INTERNAL setup (machine must be stopped) from 
                EXTERNAL setup (can be done while machine runs).

                **4 Steps**:
                1. Identify all current changeover activities
                2. Separate internal from external activities
                3. Convert internal to external where possible
                4. Streamline all remaining activities

                **Quick Win**: Pre-stage all tools and materials BEFORE stopping the machine.""",
                duration_seconds=60,
                key_takeaways=[
                    "Separate internal from external setup",
                    "Pre-stage materials and tools",
                    "Use quick-release mechanisms",
                ],
                related_tools=["Changeover Observation Sheet", "SMED Video Analysis"],
                examples=["Die change from 4 hours to 10 minutes"],
            ),
            MicroLesson(
                lesson_id="smed_external",
                category=LessonCategory.SMED,
                title="SMED: External Setup Conversion",
                summary="Convert internal setup activities to external for faster changeovers",
                content="""Converting internal to external setup is the biggest opportunity 
                in SMED.

                **Common Conversions**:
                - Pre-heating dies before changeover
                - Pre-assembling tool kits
                - Pre-positioning materials at the machine
                - Pre-adjusting settings on spare tooling

                **Ask yourself**: "Can this activity be done WHILE the machine is running?"
                
                **Target**: At least 50% of current internal time should become external.""",
                duration_seconds=60,
                key_takeaways=[
                    "Pre-heat, pre-assemble, pre-position",
                    "50% conversion target",
                    "Every second of internal time has value",
                ],
            ),
            MicroLesson(
                lesson_id="poka_yoke_basics",
                category=LessonCategory.POKA_YOKE,
                title="Poka-Yoke: Mistake-Proofing Fundamentals",
                summary="Design processes that prevent errors from occurring",
                content="""Poka-Yoke means "mistake-proofing" - designing processes so 
                errors are impossible or immediately detected.

                **3 Levels**:
                1. **Prevention**: Make it impossible to do wrong (e.g., asymmetric connectors)
                2. **Detection**: Catch errors before they become defects
                3. **Warning**: Alert operator to potential error

                **Types**:
                - Contact method: Shape/size prevents wrong assembly
                - Fixed-value method: Counts ensure correct quantity
                - Motion-step method: Sequence prevents skipped steps

                **Always aim for Level 1 (Prevention) first!**""",
                duration_seconds=60,
                key_takeaways=[
                    "Prevention > Detection > Warning",
                    "Make correct way the ONLY way",
                    "Low-cost, simple solutions work best",
                ],
            ),
            MicroLesson(
                lesson_id="oee_fundamentals",
                category=LessonCategory.TPM,
                title="OEE: Understanding Your Equipment Effectiveness",
                summary="Measure and improve Overall Equipment Effectiveness",
                content="""OEE (Overall Equipment Effectiveness) measures how well you're 
                using your equipment.

                **OEE = Availability × Performance × Quality**

                **The 6 Big Losses**:
                1. Breakdowns (Availability)
                2. Setup/Adjustments (Availability)
                3. Minor Stops (Performance)
                4. Reduced Speed (Performance)
                5. Startup Defects (Quality)
                6. Production Defects (Quality)

                **World-Class OEE**: 85%
                - Availability: 90%
                - Performance: 95%
                - Quality: 99%

                **Start by measuring** - you can't improve what you don't measure!""",
                duration_seconds=60,
                key_takeaways=[
                    "OEE = A × P × Q",
                    "Target 85% for world-class",
                    "Address biggest loss first",
                ],
            ),
            MicroLesson(
                lesson_id="kanban_basics",
                category=LessonCategory.KANBAN,
                title="Kanban: Visual Pull System",
                summary="Use visual signals to control production flow",
                content="""Kanban is a visual system for controlling production - 
                producing only what is needed, when needed.

                **Key Principles**:
                1. Visualize work flow
                2. Limit work in progress (WIP)
                3. Manage flow, not workers
                4. Make policies explicit
                5. Improve collaboratively

                **How it works**:
                - Customer consumption triggers replenishment signal
                - Signal (card/bin/empty space) authorizes production
                - No signal = no production

                **Benefits**: Reduced inventory, faster lead times, better visibility.""",
                duration_seconds=60,
                key_takeaways=[
                    "Pull, don't push",
                    "Limit WIP",
                    "Visual signals drive action",
                ],
            ),
            MicroLesson(
                lesson_id="five_s_intro",
                category=LessonCategory.FIVE_S,
                title="5S: Workplace Organization",
                summary="Create an organized, visual workplace",
                content="""5S is the foundation of all improvements - an organized 
                workplace makes problems visible.

                **The 5S's**:
                1. **Sort** (Seiri): Remove what's not needed
                2. **Set in Order** (Seiton): A place for everything
                3. **Shine** (Seiso): Clean and inspect
                4. **Standardize** (Seiketsu): Make it the standard
                5. **Sustain** (Shitsuke): Maintain discipline

                **Red Tag Rule**: If you haven't used it in 30 days, question if you need it.

                **Visual Workplace**: Anyone should be able to see abnormality in 5 seconds.""",
                duration_seconds=60,
                key_takeaways=[
                    "Everything has a place",
                    "Problems should be visible",
                    "5S is not cleaning - it's organization",
                ],
            ),
        ]
        
        for lesson in lessons:
            self.lessons[lesson.lesson_id] = lesson
    
    def _initialize_trigger_mappings(self) -> None:
        """Initialize trigger to lesson category mappings."""
        self.trigger_mappings = {
            TriggerType.HIGH_CHANGEOVER_TIME: [LessonCategory.SMED],
            TriggerType.HIGH_DEFECT_RATE: [LessonCategory.POKA_YOKE, LessonCategory.JIDOKA],
            TriggerType.LOW_OEE: [LessonCategory.TPM, LessonCategory.SMED],
            TriggerType.HIGH_INVENTORY: [LessonCategory.KANBAN, LessonCategory.HEIJUNKA],
            TriggerType.WAITING_WASTE: [LessonCategory.KANBAN, LessonCategory.VSM],
            TriggerType.QUALITY_ISSUE: [LessonCategory.POKA_YOKE, LessonCategory.JIDOKA],
            TriggerType.EQUIPMENT_FAILURE: [LessonCategory.TPM],
            TriggerType.NEW_OPERATOR: [LessonCategory.STANDARD_WORK, LessonCategory.FIVE_S],
            TriggerType.A3_STARTED: [LessonCategory.KAIZEN],
            TriggerType.PERFORMANCE_GAP: [LessonCategory.STANDARD_WORK],
        }
    
    def detect_trigger(self, data: dict[str, Any]) -> TriggerType | None:
        """Detect a trigger from operational data."""
        if data.get("changeover_time_minutes", 0) > 30:
            return TriggerType.HIGH_CHANGEOVER_TIME
        if data.get("defect_rate_pct", 0) > 3:
            return TriggerType.HIGH_DEFECT_RATE
        if data.get("oee_pct", 100) < 65:
            return TriggerType.LOW_OEE
        if data.get("inventory_days", 0) > 5:
            return TriggerType.HIGH_INVENTORY
        if data.get("idle_time_pct", 0) > 20:
            return TriggerType.WAITING_WASTE
        if data.get("quality_hold"):
            return TriggerType.QUALITY_ISSUE
        if data.get("equipment_down"):
            return TriggerType.EQUIPMENT_FAILURE
        if data.get("new_operator"):
            return TriggerType.NEW_OPERATOR
        if data.get("a3_started"):
            return TriggerType.A3_STARTED
        return None
    
    def get_lesson_for_trigger(
        self,
        trigger: TriggerType,
        recipient_id: str,
        trigger_context: dict[str, Any] | None = None,
    ) -> LessonDelivery | None:
        """Get a lesson for a specific trigger."""
        categories = self.trigger_mappings.get(trigger, [])
        if not categories:
            return None
        
        # Find an undelivered lesson in the relevant categories
        for category in categories:
            for lesson in self.lessons.values():
                if lesson.category == category:
                    # Check if already delivered recently
                    recent = [
                        d for d in self.deliveries
                        if d.lesson_id == lesson.lesson_id
                        and d.recipient_id == recipient_id
                        and d.delivered_at > datetime.now() - timedelta(days=7)
                    ]
                    if not recent:
                        delivery = LessonDelivery(
                            delivery_id=str(uuid.uuid4()),
                            lesson_id=lesson.lesson_id,
                            trigger_type=trigger,
                            trigger_context=trigger_context or {},
                            recipient_id=recipient_id,
                            delivered_at=datetime.now(),
                            status=LessonStatus.DELIVERED,
                        )
                        self.deliveries.append(delivery)
                        return delivery
        
        return None
    
    def get_lesson_content(self, lesson_id: str) -> MicroLesson | None:
        """Get the content of a specific lesson."""
        return self.lessons.get(lesson_id)
    
    def mark_viewed(self, delivery_id: str) -> bool:
        """Mark a lesson delivery as viewed."""
        for delivery in self.deliveries:
            if delivery.delivery_id == delivery_id:
                delivery.status = LessonStatus.VIEWED
                delivery.viewed_at = datetime.now()
                return True
        return False
    
    def mark_completed(
        self,
        delivery_id: str,
        rating: int | None = None,
        comment: str = "",
    ) -> bool:
        """Mark a lesson delivery as completed with optional feedback."""
        for delivery in self.deliveries:
            if delivery.delivery_id == delivery_id:
                delivery.status = LessonStatus.COMPLETED
                delivery.completed_at = datetime.now()
                if rating:
                    delivery.feedback_rating = min(5, max(1, rating))
                delivery.feedback_comment = comment
                return True
        return False
    
    def get_delivery_stats(self, recipient_id: str | None = None) -> dict[str, Any]:
        """Get lesson delivery statistics."""
        filtered = self.deliveries
        if recipient_id:
            filtered = [d for d in filtered if d.recipient_id == recipient_id]
        
        total = len(filtered)
        viewed = len([d for d in filtered if d.status in [LessonStatus.VIEWED, LessonStatus.COMPLETED]])
        completed = len([d for d in filtered if d.status == LessonStatus.COMPLETED])
        
        ratings = [d.feedback_rating for d in filtered if d.feedback_rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            "total_delivered": total,
            "viewed": viewed,
            "completed": completed,
            "view_rate": viewed / total if total > 0 else 0,
            "completion_rate": completed / total if total > 0 else 0,
            "average_rating": avg_rating,
        }


# =============================================================================
# KNOWLEDGE RETRIEVAL ENGINE
# =============================================================================


class KnowledgeRetrievalEngine:
    """
    Knowledge Retrieval Engine.
    
    Provides direct links from A3 fields to relevant TPS standard documents.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.documents: dict[str, KnowledgeDocument] = {}
        self.links: list[KnowledgeLink] = []
        
        self._initialize_knowledge_pack()
    
    def _initialize_knowledge_pack(self) -> None:
        """Initialize the TPS knowledge pack."""
        docs = [
            KnowledgeDocument(
                document_id="tps_smed_guide",
                title="SMED Implementation Guide",
                category=LessonCategory.SMED,
                summary="Complete guide to implementing Single-Minute Exchange of Die",
                content="Detailed SMED implementation methodology...",
                keywords=["changeover", "setup", "smed", "quick change", "die"],
                related_a3_fields=["countermeasure", "root_cause"],
            ),
            KnowledgeDocument(
                document_id="tps_poka_yoke_catalog",
                title="Poka-Yoke Device Catalog",
                category=LessonCategory.POKA_YOKE,
                summary="Catalog of mistake-proofing devices and techniques",
                content="Comprehensive catalog of poka-yoke solutions...",
                keywords=["mistake-proof", "error-proof", "defect", "prevention", "detection"],
                related_a3_fields=["countermeasure", "root_cause"],
            ),
            KnowledgeDocument(
                document_id="tps_5why_guide",
                title="5-Why Root Cause Analysis",
                category=LessonCategory.KAIZEN,
                summary="Guide to effective 5-Why analysis",
                content="Methodology for getting to true root cause...",
                keywords=["root cause", "5 why", "analysis", "problem solving"],
                related_a3_fields=["root_cause", "problem_statement"],
            ),
            KnowledgeDocument(
                document_id="tps_standard_work_template",
                title="Standard Work Documentation",
                category=LessonCategory.STANDARD_WORK,
                summary="How to document and maintain standard work",
                content="Standard work documentation methodology...",
                keywords=["standard", "work", "documentation", "procedure", "sop"],
                related_a3_fields=["countermeasure", "target_condition"],
            ),
            KnowledgeDocument(
                document_id="tps_kanban_sizing",
                title="Kanban System Sizing",
                category=LessonCategory.KANBAN,
                summary="How to calculate and size kanban systems",
                content="Kanban sizing formulas and methodology...",
                keywords=["kanban", "pull", "inventory", "wip", "flow"],
                related_a3_fields=["countermeasure"],
            ),
        ]
        
        for doc in docs:
            self.documents[doc.document_id] = doc
    
    def add_document(self, document: KnowledgeDocument) -> str:
        """Add a knowledge document."""
        self.documents[document.document_id] = document
        return document.document_id
    
    def search_documents(
        self,
        query: str,
        a3_field: str | None = None,
        max_results: int = 5,
    ) -> list[tuple[KnowledgeDocument, float]]:
        """Search for relevant documents."""
        results = []
        query_terms = query.lower().split()
        
        for doc in self.documents.values():
            # Calculate relevance score
            score = 0.0
            
            # Title match
            title_lower = doc.title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 0.3
            
            # Keyword match
            for keyword in doc.keywords:
                for term in query_terms:
                    if term in keyword.lower():
                        score += 0.2
            
            # Summary match
            summary_lower = doc.summary.lower()
            for term in query_terms:
                if term in summary_lower:
                    score += 0.1
            
            # A3 field relevance
            if a3_field and a3_field in doc.related_a3_fields:
                score += 0.4
            
            if score > 0:
                results.append((doc, min(1.0, score)))
        
        # Sort by score and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]
    
    def link_to_a3(
        self,
        a3_id: str,
        a3_field: str,
        field_content: str,
    ) -> KnowledgeLink:
        """Create links from an A3 field to relevant documents."""
        # Search for relevant documents
        results = self.search_documents(field_content, a3_field)
        
        if not results:
            # Create link with empty documents
            link = KnowledgeLink(
                link_id=str(uuid.uuid4()),
                a3_id=a3_id,
                a3_field=a3_field,
                document_ids=[],
                relevance_score=0.0,
            )
        else:
            # Create link with found documents
            avg_score = sum(r[1] for r in results) / len(results)
            link = KnowledgeLink(
                link_id=str(uuid.uuid4()),
                a3_id=a3_id,
                a3_field=a3_field,
                document_ids=[r[0].document_id for r in results],
                relevance_score=avg_score,
            )
        
        self.links.append(link)
        return link
    
    def get_links_for_a3(self, a3_id: str) -> list[KnowledgeLink]:
        """Get all knowledge links for an A3."""
        return [link for link in self.links if link.a3_id == a3_id]
    
    def get_recommended_documents(
        self,
        a3_id: str,
    ) -> list[KnowledgeDocument]:
        """Get recommended documents for an A3."""
        links = self.get_links_for_a3(a3_id)
        doc_ids = set()
        for link in links:
            doc_ids.update(link.document_ids)
        
        return [self.documents[did] for did in doc_ids if did in self.documents]


# =============================================================================
# STANDARD WORK EVOLUTION ENGINE
# =============================================================================


class StandardWorkEvolutionEngine:
    """
    Standard Work Evolution Engine with DB persistence.
    
    Implements the Countermeasure-to-Standard loop and best practice diffusion.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.standards: dict[str, StandardWork] = {}
        self.performers: dict[str, OperatorPerformance] = {}
    
    async def draft_update_from_a3(
        self,
        db: AsyncSession,
        a3_id: str,
        countermeasure: str,
        target_standard_id: str | None = None,
        process_name: str = "",
        work_center_id: str = "",
    ) -> StandardWorkEvolutionRecord:
        """
        Create a draft standard work update from A3 countermeasure and persist.
        """
        # Parse countermeasure to extract proposed changes
        proposed_changes = self._parse_countermeasure(countermeasure)
        
        record = StandardWorkEvolutionRecord(
            original_standard_id=target_standard_id or "unknown",
            suggested_changes=proposed_changes,
            reasoning=f"A3 {a3_id} successfully closed with countermeasure: {countermeasure}",
            status="pending",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def get_evolution_history(self, db: AsyncSession, standard_id: str) -> list[StandardWorkEvolutionRecord]:
        """Get all evolution suggestions for a standard."""
        stmt = select(StandardWorkEvolutionRecord).where(StandardWorkEvolutionRecord.original_standard_id == standard_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    def _parse_countermeasure(self, countermeasure: str) -> dict[str, Any]:
        """Parse countermeasure text to extract proposed changes."""
        changes = {
            "type": "process_update",
            "description": countermeasure,
            "new_steps": [],
            "modified_steps": [],
            "new_key_points": [],
            "new_quality_checks": [],
        }
        
        # Simple keyword-based parsing
        lower = countermeasure.lower()
        
        if "step" in lower or "procedure" in lower:
            changes["type"] = "step_modification"
            changes["new_steps"].append(countermeasure)
        
        if "check" in lower or "verify" in lower or "inspect" in lower:
            changes["new_quality_checks"].append(countermeasure)
        
        if "important" in lower or "key" in lower or "critical" in lower:
            changes["new_key_points"].append(countermeasure)
        
        return changes
    
    def approve_draft(self, draft_id: str, reviewer: str) -> bool:
        """Approve a standard work draft."""
        for draft in self.drafts:
            if draft.draft_id == draft_id:
                draft.status = "approved"
                draft.reviewed_by = reviewer
                draft.approved_at = datetime.now()
                
                # Apply changes to standard
                if draft.target_standard_id and draft.target_standard_id in self.standards:
                    self._apply_draft_to_standard(draft)
                
                return True
        return False
    
    def _apply_draft_to_standard(self, draft: StandardWorkDraft) -> None:
        """Apply draft changes to the standard work document."""
        standard = self.standards.get(draft.target_standard_id)
        if not standard:
            return
        
        changes = draft.proposed_changes
        
        # Update key points
        if changes.get("new_key_points"):
            standard.key_points.extend(changes["new_key_points"])
        
        # Update quality checks
        if changes.get("new_quality_checks"):
            standard.quality_checks.extend(changes["new_quality_checks"])
        
        # Update version
        major, minor = standard.version.split(".")
        standard.version = f"{major}.{int(minor) + 1}"
        standard.updated_at = datetime.now()
        standard.source_a3_id = draft.source_a3_id
    
    def register_operator_performance(
        self,
        operator_id: str,
        name: str,
        work_center_id: str,
        oee_score: float,
        quality_score: float,
        productivity_score: float,
        techniques: list[str] | None = None,
    ) -> OperatorPerformance:
        """Register operator performance metrics."""
        perf = OperatorPerformance(
            operator_id=operator_id,
            name=name,
            work_center_id=work_center_id,
            oee_score=oee_score,
            quality_score=quality_score,
            productivity_score=productivity_score,
            techniques=techniques or [],
        )
        self.performers[operator_id] = perf
        return perf
    
    def identify_super_performers(
        self,
        work_center_id: str | None = None,
    ) -> list[OperatorPerformance]:
        """
        Identify super-performers.
        
        Super-performers are operators with the highest OEE/Quality scores.
        """
        performers = list(self.performers.values())
        
        if work_center_id:
            performers = [p for p in performers if p.work_center_id == work_center_id]
        
        super_performers = [
            p for p in performers
            if p.level == PerformerLevel.SUPER_PERFORMER
        ]
        
        return super_performers
    
    def suggest_best_practice_codification(
        self,
        work_center_id: str,
        baseline_metric: str = "overall_score",
    ) -> list[BestPracticeSuggestion]:
        """
        Suggest codifying super-performer techniques into standards.
        
        Identifies super-performers and suggests their techniques be
        codified into site-wide standards.
        """
        super_performers = self.identify_super_performers(work_center_id)
        suggestions = []
        
        # Calculate baseline (average of non-super performers)
        all_performers = [
            p for p in self.performers.values()
            if p.work_center_id == work_center_id
            and p.level != PerformerLevel.SUPER_PERFORMER
        ]
        
        if not all_performers:
            baseline = 70.0  # Default baseline
        else:
            baseline = sum(p.overall_score for p in all_performers) / len(all_performers)
        
        for performer in super_performers:
            for technique in performer.techniques:
                improvement = performer.overall_score - baseline
                
                # Find target standard for this work center
                target_std = None
                for std in self.standards.values():
                    if std.work_center_id == work_center_id:
                        target_std = std.standard_id
                        break
                
                suggestion = BestPracticeSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    super_performer_id=performer.operator_id,
                    super_performer_name=performer.name,
                    technique=technique,
                    observed_benefit=f"{improvement:.1f}% higher performance than baseline",
                    current_baseline=baseline,
                    performer_result=performer.overall_score,
                    improvement_potential=improvement,
                    suggested_at=datetime.now(),
                    target_standard_id=target_std,
                )
                suggestions.append(suggestion)
        
        self.best_practice_suggestions.extend(suggestions)
        return suggestions
    
    def get_pending_drafts(self) -> list[StandardWorkDraft]:
        """Get pending standard work drafts."""
        return [d for d in self.drafts if d.status == "pending"]
    
    def get_pending_suggestions(self) -> list[BestPracticeSuggestion]:
        """Get pending best practice suggestions."""
        return [s for s in self.best_practice_suggestions if s.status == "pending"]


# =============================================================================
# JIT LEAN LEARNING ORCHESTRATOR
# =============================================================================


class JITLeanLearning:
    """
    Just-in-Time Lean Learning & Knowledge Synthesis.
    
    Orchestrates micro-lessons, knowledge retrieval, and standard work evolution.
    """
    
    def __init__(
        self,
        lesson_engine: MicroLessonEngine | None = None,
        knowledge_engine: KnowledgeRetrievalEngine | None = None,
        evolution_engine: StandardWorkEvolutionEngine | None = None,
    ):
        """Initialize JIT Lean Learning."""
        self.lesson_engine = lesson_engine or MicroLessonEngine()
        self.knowledge_engine = knowledge_engine or KnowledgeRetrievalEngine()
        self.evolution_engine = evolution_engine or StandardWorkEvolutionEngine()
    
    async def process_operational_data(
        self,
        db: AsyncSession,
        data: dict[str, Any],
        operator_id: UUID,
    ) -> dict[str, Any]:
        """
        Process operational data and trigger appropriate learning.
        
        Detects conditions that warrant micro-lessons and delivers them.
        """
        result = {
            "trigger_detected": None,
            "lesson_delivered": None,
        }
        
        # Detect trigger
        trigger = self.lesson_engine.detect_trigger(data)
        if trigger:
            result["trigger_detected"] = trigger.value
            
            # Get and deliver lesson
            lesson_id = self.lesson_engine.get_lesson_id_for_trigger(trigger)
            if lesson_id:
                delivery = await self.lesson_engine.deliver_lesson(
                    db=db,
                    lesson_id=lesson_id,
                    recipient_id=operator_id,
                    trigger_type=trigger,
                    context=data,
                )
                lesson = self.lesson_engine.get_lesson_content(lesson_id)
                result["lesson_delivered"] = {
                    "delivery_id": str(delivery.id),
                    "lesson_id": delivery.lesson_id,
                    "title": lesson.title if lesson else "",
                    "summary": lesson.summary if lesson else "",
                }
        
        return result
    
    def get_lesson_content(self, lesson_id: str) -> dict[str, Any] | None:
        """Get full lesson content."""
        lesson = self.lesson_engine.get_lesson_content(lesson_id)
        if not lesson:
            return None
        
        return {
            "lesson_id": lesson.lesson_id,
            "category": lesson.category.value,
            "title": lesson.title,
            "summary": lesson.summary,
            "content": lesson.content,
            "duration_seconds": lesson.duration_seconds,
            "key_takeaways": lesson.key_takeaways,
            "related_tools": lesson.related_tools,
            "examples": lesson.examples,
        }
    
    async def link_a3_to_knowledge(
        self,
        db: AsyncSession,
        a3_id: str,
        problem_statement: str = "",
        root_cause: str = "",
        countermeasure: str = "",
    ) -> dict[str, Any]:
        """Create knowledge links for an A3."""
        links = {}
        
        if problem_statement:
            link = await self.knowledge_engine.link_to_a3(db, a3_id, "problem_statement", problem_statement)
            links["problem_statement"] = {
                "link_id": link.link_id,
                "documents": link.document_ids,
                "relevance": link.relevance_score,
            }
        
        if root_cause:
            link = await self.knowledge_engine.link_to_a3(db, a3_id, "root_cause", root_cause)
            links["root_cause"] = {
                "link_id": link.link_id,
                "documents": link.document_ids,
                "relevance": link.relevance_score,
            }
        
        if countermeasure:
            link = await self.knowledge_engine.link_to_a3(db, a3_id, "countermeasure", countermeasure)
            links["countermeasure"] = {
                "link_id": link.link_id,
                "documents": link.document_ids,
                "relevance": link.relevance_score,
            }
        
        return {
            "a3_id": a3_id,
            "links": links,
            "recommended_documents": [],
        }
    
    def close_a3_with_standard_update(
        self,
        a3_id: str,
        countermeasure: str,
        work_center_id: str = "",
        process_name: str = "",
    ) -> dict[str, Any]:
        """
        Close an A3 and automatically draft standard work update.
        
        Implements the Countermeasure-to-Standard loop.
        """
        draft = self.evolution_engine.draft_update_from_a3(
            a3_id=a3_id,
            countermeasure=countermeasure,
            work_center_id=work_center_id,
            process_name=process_name,
        )
        
        return {
            "a3_id": a3_id,
            "draft_id": draft.draft_id,
            "target_standard": draft.target_standard_id,
            "proposed_changes": draft.proposed_changes,
            "status": draft.status,
        }
    
    def analyze_best_practices(
        self,
        work_center_id: str,
    ) -> dict[str, Any]:
        """
        Analyze and suggest best practice codification.
        
        Identifies super-performers and suggests their techniques
        for site-wide standard inclusion.
        """
        suggestions = self.evolution_engine.suggest_best_practice_codification(
            work_center_id
        )
        
        super_performers = self.evolution_engine.identify_super_performers(work_center_id)
        
        return {
            "work_center_id": work_center_id,
            "super_performers": [
                {
                    "operator_id": p.operator_id,
                    "name": p.name,
                    "overall_score": p.overall_score,
                    "techniques": p.techniques,
                }
                for p in super_performers
            ],
            "suggestions": [
                {
                    "suggestion_id": s.suggestion_id,
                    "technique": s.technique,
                    "performer": s.super_performer_name,
                    "improvement_potential": s.improvement_potential,
                }
                for s in suggestions
            ],
        }
    
    def get_learning_dashboard(self, operator_id: str | None = None) -> dict[str, Any]:
        """Get comprehensive learning dashboard."""
        lesson_stats = self.lesson_engine.get_delivery_stats(operator_id)
        
        return {
            "lessons": lesson_stats,
            "knowledge": {
                "total_documents": len(self.knowledge_engine.documents),
                "total_links": len(self.knowledge_engine.links),
            },
            "standards": {
                "total_standards": len(self.evolution_engine.standards),
                "pending_drafts": len(self.evolution_engine.get_pending_drafts()),
                "pending_suggestions": len(self.evolution_engine.get_pending_suggestions()),
                "super_performers": len(self.evolution_engine.identify_super_performers()),
            },
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_jit_lean_learning() -> JITLeanLearning:
    """Create the JIT Lean Learning service."""
    return JITLeanLearning()


def create_micro_lesson_engine() -> MicroLessonEngine:
    """Create micro-lesson engine."""
    return MicroLessonEngine()


def create_knowledge_retrieval_engine() -> KnowledgeRetrievalEngine:
    """Create knowledge retrieval engine."""
    return KnowledgeRetrievalEngine()


def create_standard_work_engine() -> StandardWorkEvolutionEngine:
    """Create standard work evolution engine."""
    return StandardWorkEvolutionEngine()

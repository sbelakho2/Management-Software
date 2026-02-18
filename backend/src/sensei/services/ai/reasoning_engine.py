"""
Sensei Reasoning Engine.

This module implements advanced problem-solving assistance:
- A3 Pattern Learning: Analyze closed A3s to identify countermeasure/KPI correlations
- Interactive A3 Socratic Mentor: Real-time challenging prompts during A3 drafting
- Autonomous 5 Whys Root Cause Assistant: Suggest potential "Whys" and link to lean waste categories
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math
import random
from uuid import UUID

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Enums and Constants
# =============================================================================

class A3Phase(Enum):
    """Phases of an A3 problem-solving report."""
    BACKGROUND = "background"
    CURRENT_STATE = "current_state"
    GOAL = "goal"
    ROOT_CAUSE = "root_cause"
    COUNTERMEASURES = "countermeasures"
    IMPLEMENTATION = "implementation"
    FOLLOW_UP = "follow_up"


class LeanWasteCategory(Enum):
    """The 3 lean waste categories (3M)."""
    MUDA = "muda"       # Non-value adding waste
    MURA = "mura"       # Unevenness, irregularity
    MURI = "muri"       # Overburden, unreasonableness


class MudaType(Enum):
    """The 7+1 types of Muda waste."""
    TRANSPORTATION = "transportation"
    INVENTORY = "inventory"
    MOTION = "motion"
    WAITING = "waiting"
    OVERPRODUCTION = "overproduction"
    OVERPROCESSING = "overprocessing"
    DEFECTS = "defects"
    SKILLS = "skills"  # The 8th waste (underutilized talent)


class MentorPersona(Enum):
    """Mentor personas based on TPS principles."""
    THE_SENSEI = "the_sensei"           # Wise, probing, Socratic
    THE_COACH = "the_coach"             # Supportive, guiding
    THE_CHALLENGER = "the_challenger"   # Direct, challenging assumptions
    THE_OBSERVER = "the_observer"       # Patient, asks for evidence


class PromptType(Enum):
    """Types of challenging prompts."""
    CLARIFICATION = "clarification"
    EVIDENCE = "evidence"
    ASSUMPTION = "assumption"
    ALTERNATIVE = "alternative"
    DEEPER = "deeper"
    VERIFICATION = "verification"


class KPITrend(Enum):
    """KPI trend direction."""
    IMPROVED = "improved"
    STABLE = "stable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class KPIMetric:
    """A KPI measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    trend: KPITrend = KPITrend.UNKNOWN
    target: Optional[float] = None
    
    @property
    def is_on_target(self) -> bool:
        if self.target is None:
            return True
        return self.value >= self.target


@dataclass
class Countermeasure:
    """A countermeasure in an A3."""
    id: str
    description: str
    category: str
    implementation_date: Optional[datetime] = None
    responsible: Optional[str] = None
    status: str = "proposed"
    effectiveness_score: float = 0.0
    tags: List[str] = field(default_factory=list)


@dataclass
class A3Report:
    """An A3 problem-solving report."""
    id: str
    title: str
    problem_statement: str
    owner: str
    created_at: datetime
    status: str = "open"  # open, in_progress, closed
    background: str = ""
    current_state: str = ""
    goal: str = ""
    root_causes: List[str] = field(default_factory=list)
    countermeasures: List[Countermeasure] = field(default_factory=list)
    kpis_before: List[KPIMetric] = field(default_factory=list)
    kpis_after: List[KPIMetric] = field(default_factory=list)
    five_whys: List[str] = field(default_factory=list)
    waste_categories: List[LeanWasteCategory] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    closed_at: Optional[datetime] = None


@dataclass
class CountermeasureCorrelation:
    """Correlation between a countermeasure type and KPI improvement."""
    countermeasure_category: str
    kpi_name: str
    correlation_strength: float  # -1.0 to 1.0
    sample_size: int
    avg_improvement: float
    success_rate: float  # % of times this led to improvement


@dataclass
class ChallengingPrompt:
    """A challenging prompt from the Socratic mentor."""
    id: str
    prompt_type: PromptType
    question: str
    context: str
    phase: A3Phase
    persona: MentorPersona
    priority: int = 1  # 1 = high, 3 = low
    follow_up_prompts: List[str] = field(default_factory=list)


@dataclass
class RootCauseSuggestion:
    """A suggested root cause from the 5 Whys assistant."""
    why_number: int  # 1-5
    suggested_cause: str
    confidence: float
    waste_category: LeanWasteCategory
    muda_type: Optional[MudaType] = None
    similar_historical_causes: List[str] = field(default_factory=list)
    evidence_needed: List[str] = field(default_factory=list)


@dataclass
class WebSocketMessage:
    """A message for real-time WebSocket communication."""
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=_utcnow)
    correlation_id: Optional[str] = None


# =============================================================================
# A3 Pattern Learning
# =============================================================================

class A3PatternAnalyzer:
    """
    Analyzes closed A3s to identify patterns between countermeasures and KPI improvements.
    """
    
    def __init__(self):
        self._closed_a3s: List[A3Report] = []
        self._correlations: Dict[str, CountermeasureCorrelation] = {}
        self._countermeasure_success: Dict[str, List[float]] = defaultdict(list)
        self._kpi_improvements: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    
    def add_closed_a3(self, a3: A3Report) -> None:
        """Add a closed A3 for pattern analysis."""
        if a3.status != "closed":
            raise ValueError("Only closed A3s can be analyzed")
        
        self._closed_a3s.append(a3)
        self._analyze_a3(a3)
    
    def _analyze_a3(self, a3: A3Report) -> None:
        """Analyze a single A3 for patterns."""
        # Calculate KPI improvements
        kpi_improvements = self._calculate_kpi_improvements(a3)
        
        # Track countermeasure effectiveness
        for countermeasure in a3.countermeasures:
            if countermeasure.status in ("completed", "verified"):
                for kpi_name, improvement in kpi_improvements.items():
                    self._kpi_improvements[kpi_name].append(
                        (countermeasure.category, improvement)
                    )
                    
                    # Track success (positive improvement)
                    success = 1.0 if improvement > 0 else 0.0
                    self._countermeasure_success[countermeasure.category].append(success)
    
    def _calculate_kpi_improvements(
        self, a3: A3Report
    ) -> Dict[str, float]:
        """Calculate KPI improvements (before vs after)."""
        improvements = {}
        
        before_map = {k.name: k.value for k in a3.kpis_before}
        after_map = {k.name: k.value for k in a3.kpis_after}
        
        for kpi_name in set(before_map.keys()) & set(after_map.keys()):
            before = before_map[kpi_name]
            after = after_map[kpi_name]
            
            if before != 0:
                improvement = (after - before) / abs(before)
            else:
                improvement = 1.0 if after > 0 else 0.0
            
            improvements[kpi_name] = improvement
        
        return improvements
    
    def compute_correlations(self) -> List[CountermeasureCorrelation]:
        """Compute correlations between countermeasure categories and KPI improvements."""
        correlations = []
        
        for kpi_name, data in self._kpi_improvements.items():
            # Group by countermeasure category
            by_category: Dict[str, List[float]] = defaultdict(list)
            for category, improvement in data:
                by_category[category].append(improvement)
            
            for category, improvements in by_category.items():
                if len(improvements) < 2:
                    continue
                
                avg_improvement = sum(improvements) / len(improvements)
                success_rate = sum(1 for i in improvements if i > 0) / len(improvements)
                
                # Simple correlation (strength based on consistency)
                if len(set(i > 0 for i in improvements)) == 1:
                    correlation_strength = 0.9 if improvements[0] > 0 else -0.9
                else:
                    positive_pct = sum(1 for i in improvements if i > 0) / len(improvements)
                    correlation_strength = (positive_pct - 0.5) * 2  # Scale to -1 to 1
                
                correlation = CountermeasureCorrelation(
                    countermeasure_category=category,
                    kpi_name=kpi_name,
                    correlation_strength=correlation_strength,
                    sample_size=len(improvements),
                    avg_improvement=avg_improvement,
                    success_rate=success_rate,
                )
                correlations.append(correlation)
                
                key = f"{category}:{kpi_name}"
                self._correlations[key] = correlation
        
        return correlations
    
    def suggest_countermeasures(
        self,
        target_kpis: List[str],
        problem_category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float, str]]:
        """
        Suggest countermeasure categories based on target KPIs.
        
        Returns:
            List of (category, score, reason) tuples
        """
        if not self._correlations:
            self.compute_correlations()
        
        candidates: Dict[str, float] = defaultdict(float)
        reasons: Dict[str, str] = {}
        
        for kpi_name in target_kpis:
            for key, correlation in self._correlations.items():
                if correlation.kpi_name == kpi_name:
                    category = correlation.countermeasure_category
                    
                    # Score based on success rate and correlation strength
                    score = (
                        correlation.success_rate * 0.4 +
                        max(0, correlation.correlation_strength) * 0.4 +
                        min(1, correlation.sample_size / 10) * 0.2
                    )
                    
                    if score > candidates[category]:
                        candidates[category] = score
                        reasons[category] = (
                            f"{correlation.success_rate:.0%} success rate for {kpi_name}, "
                            f"avg improvement {correlation.avg_improvement:.1%}"
                        )
        
        # Sort by score
        sorted_candidates = sorted(
            [(cat, score, reasons.get(cat, "")) for cat, score in candidates.items()],
            key=lambda x: x[1],
            reverse=True,
        )
        
        return sorted_candidates[:top_k]
    
    def get_success_rate(self, countermeasure_category: str) -> float:
        """Get the success rate for a countermeasure category."""
        successes = self._countermeasure_success.get(countermeasure_category, [])
        if not successes:
            return 0.5  # Default uncertainty
        return sum(successes) / len(successes)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "closed_a3s": len(self._closed_a3s),
            "correlations": len(self._correlations),
            "tracked_categories": len(self._countermeasure_success),
            "tracked_kpis": len(self._kpi_improvements),
        }

    def export_state(self) -> Dict[str, Any]:
        """Export analyzer state for persistence."""
        return {
            "closed_a3s": [encode_dataclass(a3) for a3 in self._closed_a3s],
            "correlations": {
                key: encode_dataclass(correlation)
                for key, correlation in self._correlations.items()
            },
            "countermeasure_success": {
                key: list(values) for key, values in self._countermeasure_success.items()
            },
            "kpi_improvements": {
                key: [
                    {"category": category, "improvement": improvement}
                    for category, improvement in values
                ]
                for key, values in self._kpi_improvements.items()
            },
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Load analyzer state from persistence."""
        self._closed_a3s = [
            decode_dataclass(a3, A3Report)
            for a3 in state.get("closed_a3s", [])
        ]
        self._correlations = {
            key: decode_dataclass(value, CountermeasureCorrelation)
            for key, value in state.get("correlations", {}).items()
        }
        self._countermeasure_success = defaultdict(list)
        for key, values in state.get("countermeasure_success", {}).items():
            self._countermeasure_success[key] = list(values)
        self._kpi_improvements = defaultdict(list)
        for key, values in state.get("kpi_improvements", {}).items():
            self._kpi_improvements[key] = [
                (item["category"], item["improvement"]) for item in values
            ]


# =============================================================================
# Socratic Mentor
# =============================================================================

class SocraticMentor:
    """
    Interactive Socratic mentor for A3 drafting.
    
    Provides challenging prompts based on TPS principles.
    """
    
    # Prompt templates by persona and type
    PROMPT_TEMPLATES: Dict[MentorPersona, Dict[PromptType, List[str]]] = {
        MentorPersona.THE_SENSEI: {
            PromptType.CLARIFICATION: [
                "What exactly do you mean by '{term}'?",
                "Can you be more specific about '{aspect}'?",
                "How would you define '{concept}' in this context?",
            ],
            PromptType.EVIDENCE: [
                "What data supports this claim?",
                "Show me the evidence at the gemba.",
                "How did you measure this?",
            ],
            PromptType.ASSUMPTION: [
                "What assumptions are you making here?",
                "Have you verified this with facts?",
                "Is this based on opinion or observation?",
            ],
            PromptType.DEEPER: [
                "Why is that?",
                "And what causes that?",
                "Go deeper. What's behind this?",
            ],
        },
        MentorPersona.THE_CHALLENGER: {
            PromptType.ASSUMPTION: [
                "I challenge that assumption. Prove it.",
                "What if the opposite were true?",
                "Why are you so sure about this?",
            ],
            PromptType.ALTERNATIVE: [
                "What other explanations exist?",
                "Have you considered {alternative}?",
                "What would a competitor say about this?",
            ],
            PromptType.VERIFICATION: [
                "How will you verify this works?",
                "What could make this fail?",
                "Where's your Plan B?",
            ],
        },
        MentorPersona.THE_COACH: {
            PromptType.CLARIFICATION: [
                "Let's think through '{aspect}' together.",
                "Tell me more about your thinking here.",
                "What led you to this conclusion?",
            ],
            PromptType.EVIDENCE: [
                "What did you observe at the gemba?",
                "Can you walk me through the data?",
                "What do the operators say about this?",
            ],
        },
        MentorPersona.THE_OBSERVER: {
            PromptType.EVIDENCE: [
                "I need to see this for myself. Where should I look?",
                "What would I observe if I visited the process?",
                "Take me through a typical cycle.",
            ],
            PromptType.VERIFICATION: [
                "How long have you observed this pattern?",
                "Is this consistently occurring?",
                "What variations have you seen?",
            ],
        },
    }
    
    # Phase-specific focus areas
    PHASE_FOCUS: Dict[A3Phase, List[PromptType]] = {
        A3Phase.BACKGROUND: [PromptType.CLARIFICATION, PromptType.EVIDENCE],
        A3Phase.CURRENT_STATE: [PromptType.EVIDENCE, PromptType.VERIFICATION],
        A3Phase.GOAL: [PromptType.ASSUMPTION, PromptType.ALTERNATIVE],
        A3Phase.ROOT_CAUSE: [PromptType.DEEPER, PromptType.EVIDENCE, PromptType.ASSUMPTION],
        A3Phase.COUNTERMEASURES: [PromptType.ALTERNATIVE, PromptType.VERIFICATION],
        A3Phase.IMPLEMENTATION: [PromptType.VERIFICATION, PromptType.ASSUMPTION],
        A3Phase.FOLLOW_UP: [PromptType.VERIFICATION, PromptType.EVIDENCE],
    }
    
    def __init__(
        self,
        default_persona: MentorPersona = MentorPersona.THE_SENSEI,
        seed: Optional[int] = None,
    ):
        self.default_persona = default_persona
        self._prompt_counter = 0
        self._session_prompts: List[ChallengingPrompt] = []
        self._expert_traces: List[Dict[str, Any]] = []
        # Seed a dedicated RNG for reproducible prompt selection (#212/#462)
        self._rng = random.Random(seed)

    def export_state(self) -> Dict[str, Any]:
        """Export mentor state for persistence."""
        return {
            "default_persona": self.default_persona.value,
            "prompt_counter": self._prompt_counter,
            "session_prompts": [encode_dataclass(p) for p in self._session_prompts],
            "expert_traces": list(self._expert_traces),
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Load mentor state from persistence."""
        persona = state.get("default_persona")
        if persona:
            self.default_persona = MentorPersona(persona)
        self._prompt_counter = int(state.get("prompt_counter", 0))
        self._session_prompts = [
            decode_dataclass(prompt, ChallengingPrompt)
            for prompt in state.get("session_prompts", [])
        ]
        self._expert_traces = list(state.get("expert_traces", []))

    def add_expert_trace(self, trace: Dict[str, Any]) -> None:
        """Add an expert reasoning trace from seeded book knowledge."""
        self._expert_traces.append(trace)
    
    def generate_prompts(
        self,
        content: str,
        phase: A3Phase,
        persona: Optional[MentorPersona] = None,
        max_prompts: int = 3,
    ) -> List[ChallengingPrompt]:
        """
        Generate challenging prompts for the given content and phase.
        
        Args:
            content: The A3 content being drafted
            phase: Current A3 phase
            persona: Mentor persona to use
            max_prompts: Maximum number of prompts to generate
            
        Returns:
            List of challenging prompts
        """
        persona = persona or self.default_persona
        focus_types = self.PHASE_FOCUS.get(phase, [PromptType.CLARIFICATION])
        
        prompts = []
        
        # Extract key terms/concepts from content
        key_terms = self._extract_key_terms(content)
        
        for prompt_type in focus_types[:max_prompts]:
            # Inject expert knowledge if available
            relevant_expert_prompt = None
            if self._expert_traces and self._rng.random() > 0.5:
                trace = self._rng.choice(self._expert_traces)
                principle = trace.get("findings", {}).get("distilled_principle", "")
                source = trace.get("findings", {}).get("source_book", "expert knowledge")
                relevant_expert_prompt = f"Based on '{source}', we should consider: {principle}. How does this apply to your current thinking?"

            templates = self.PROMPT_TEMPLATES.get(persona, {}).get(prompt_type, [])
            
            if not templates:
                # Fall back to Sensei templates
                templates = self.PROMPT_TEMPLATES[MentorPersona.THE_SENSEI].get(
                    prompt_type, ["Tell me more about this."]
                )
            
            template = self._rng.choice(templates)
            
            # Fill in placeholders
            question = relevant_expert_prompt or template
            if "{term}" in question and key_terms:
                question = question.replace("{term}", self._rng.choice(key_terms))
            if "{aspect}" in question:
                question = question.replace("{aspect}", self._identify_aspect(content))
            if "{concept}" in question and key_terms:
                question = question.replace("{concept}", self._rng.choice(key_terms))
            if "{alternative}" in question:
                question = question.replace("{alternative}", "a different approach")
            
            self._prompt_counter += 1
            prompt = ChallengingPrompt(
                id=f"prompt_{self._prompt_counter}",
                prompt_type=prompt_type,
                question=question,
                context=content[:200] if len(content) > 200 else content,
                phase=phase,
                persona=persona,
                priority=1 if prompt_type in [PromptType.EVIDENCE, PromptType.DEEPER] else 2,
                follow_up_prompts=self._get_follow_ups(prompt_type),
            )
            prompts.append(prompt)
            self._session_prompts.append(prompt)
        
        return prompts
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key terms from content."""
        # Simple extraction: words longer than 5 chars, not common words
        common_words = {
            "about", "after", "being", "before", "could", "during",
            "every", "first", "found", "great", "having", "other",
            "should", "still", "their", "there", "these", "thing",
            "think", "those", "through", "under", "using", "where",
            "which", "while", "would", "because", "between",
        }
        
        words = re.findall(r'\b[a-zA-Z]{5,}\b', content.lower())
        unique_words = [w for w in set(words) if w not in common_words]
        
        return unique_words[:10]
    
    def _identify_aspect(self, content: str) -> str:
        """Identify a key aspect from the content."""
        # Look for quoted phrases or emphasized text
        quoted = re.findall(r'"([^"]+)"', content)
        if quoted:
            return quoted[0]
        
        # Look for sentences with "is" or "are"
        sentences = content.split('.')
        for sentence in sentences:
            if ' is ' in sentence or ' are ' in sentence:
                return sentence.strip()[:50]
        
        return "this situation"
    
    def _get_follow_ups(self, prompt_type: PromptType) -> List[str]:
        """Get follow-up prompts for a prompt type."""
        follow_ups = {
            PromptType.CLARIFICATION: [
                "And why is that important?",
                "Who else is affected?",
            ],
            PromptType.EVIDENCE: [
                "How recent is this data?",
                "What's the sample size?",
            ],
            PromptType.ASSUMPTION: [
                "Test that assumption.",
                "What would change your mind?",
            ],
            PromptType.DEEPER: [
                "Keep going. Why?",
                "And what causes that?",
            ],
            PromptType.ALTERNATIVE: [
                "Explore that option.",
                "What are the trade-offs?",
            ],
            PromptType.VERIFICATION: [
                "Run a small experiment.",
                "Check with the operators.",
            ],
        }
        return follow_ups.get(prompt_type, [])
    
    def create_websocket_message(
        self,
        prompt: ChallengingPrompt,
    ) -> WebSocketMessage:
        """Create a WebSocket message for real-time delivery."""
        return WebSocketMessage(
            message_type="challenging_prompt",
            payload={
                "id": prompt.id,
                "question": prompt.question,
                "type": prompt.prompt_type.value,
                "phase": prompt.phase.value,
                "persona": prompt.persona.value,
                "priority": prompt.priority,
                "follow_ups": prompt.follow_up_prompts,
            },
            correlation_id=prompt.id,
        )
    
    def get_session_prompts(self) -> List[ChallengingPrompt]:
        """Get all prompts generated in this session."""
        return self._session_prompts
    
    def clear_session(self) -> None:
        """Clear session prompts."""
        self._session_prompts.clear()


# =============================================================================
# 5 Whys Root Cause Assistant
# =============================================================================

class FiveWhysAssistant:
    """
    Autonomous 5 Whys root cause assistant.
    
    Analyzes problem statements and suggests potential "Whys" by correlating
    with historical failure patterns. Links to lean waste categories.
    """
    
    # Waste category keywords
    WASTE_KEYWORDS: Dict[LeanWasteCategory, List[str]] = {
        LeanWasteCategory.MUDA: [
            "waste", "delay", "waiting", "transport", "move", "rework",
            "defect", "inventory", "storage", "inspection", "unnecessary",
        ],
        LeanWasteCategory.MURA: [
            "variation", "inconsistent", "uneven", "irregular", "fluctuat",
            "unpredictable", "variable", "different", "sometime",
        ],
        LeanWasteCategory.MURI: [
            "overload", "stress", "strain", "exceed", "capacity",
            "bottleneck", "overwhelm", "impossible", "unreasonable",
        ],
    }
    
    # Muda type keywords
    MUDA_KEYWORDS: Dict[MudaType, List[str]] = {
        MudaType.TRANSPORTATION: [
            "transport", "move", "ship", "deliver", "transfer", "carry",
        ],
        MudaType.INVENTORY: [
            "inventory", "stock", "storage", "warehouse", "buffer", "pile",
        ],
        MudaType.MOTION: [
            "motion", "walk", "reach", "bend", "search", "find", "look",
        ],
        MudaType.WAITING: [
            "wait", "delay", "queue", "pending", "hold", "idle",
        ],
        MudaType.OVERPRODUCTION: [
            "overproduc", "too much", "excess", "surplus", "more than need",
        ],
        MudaType.OVERPROCESSING: [
            "overprocess", "unnecessary", "extra step", "redundant", "duplicate",
        ],
        MudaType.DEFECTS: [
            "defect", "error", "mistake", "rework", "scrap", "reject", "fail",
        ],
        MudaType.SKILLS: [
            "skill", "training", "capability", "talent", "knowledge", "underutil",
        ],
    }
    
    # Common root cause patterns
    ROOT_CAUSE_PATTERNS: List[Dict[str, Any]] = [
        {
            "pattern": "lack of standard",
            "keywords": ["no standard", "different way", "varies", "inconsistent"],
            "suggestion": "There is no standardized process or work instruction.",
            "waste": LeanWasteCategory.MURA,
        },
        {
            "pattern": "training gap",
            "keywords": ["untrained", "didn't know", "new employee", "not aware"],
            "suggestion": "Training or knowledge transfer was inadequate.",
            "waste": LeanWasteCategory.MUDA,
            "muda": MudaType.SKILLS,
        },
        {
            "pattern": "equipment failure",
            "keywords": ["machine", "equipment", "broke", "malfunction", "failure"],
            "suggestion": "Preventive maintenance was insufficient.",
            "waste": LeanWasteCategory.MUDA,
            "muda": MudaType.DEFECTS,
        },
        {
            "pattern": "capacity constraint",
            "keywords": ["not enough", "capacity", "overload", "too many"],
            "suggestion": "Demand exceeded available capacity.",
            "waste": LeanWasteCategory.MURI,
        },
        {
            "pattern": "communication gap",
            "keywords": ["miscommunicat", "didn't tell", "not informed", "unclear"],
            "suggestion": "Information was not effectively communicated.",
            "waste": LeanWasteCategory.MURA,
        },
        {
            "pattern": "quality issue",
            "keywords": ["defect", "quality", "specification", "out of spec"],
            "suggestion": "Quality controls were insufficient or not followed.",
            "waste": LeanWasteCategory.MUDA,
            "muda": MudaType.DEFECTS,
        },
        {
            "pattern": "scheduling problem",
            "keywords": ["schedule", "timing", "late", "early", "sequence"],
            "suggestion": "Scheduling or sequencing was not optimal.",
            "waste": LeanWasteCategory.MURA,
        },
        {
            "pattern": "material issue",
            "keywords": ["material", "part", "component", "supply", "supplier"],
            "suggestion": "Material quality or availability was inadequate.",
            "waste": LeanWasteCategory.MUDA,
            "muda": MudaType.INVENTORY,
        },
    ]
    
    _MAX_SUGGESTION_CACHE = 256  # Maximum cached suggestion entries (#121)

    def __init__(self):
        self._historical_causes: List[Tuple[str, LeanWasteCategory]] = []
        self._suggestion_cache: Dict[str, List[RootCauseSuggestion]] = {}
        self._expert_traces: List[Dict[str, Any]] = []

    def export_state(self) -> Dict[str, Any]:
        """Export assistant state for persistence."""
        return {
            "historical_causes": [
                {"cause": cause, "waste_category": waste.value}
                for cause, waste in self._historical_causes
            ],
            "suggestion_cache": {
                key: [encode_dataclass(item) for item in values]
                for key, values in self._suggestion_cache.items()
            },
            "expert_traces": list(self._expert_traces),
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Load assistant state from persistence."""
        self._historical_causes = [
            (item["cause"], LeanWasteCategory(item["waste_category"]))
            for item in state.get("historical_causes", [])
        ]
        self._suggestion_cache = {
            key: [decode_dataclass(item, RootCauseSuggestion) for item in values]
            for key, values in state.get("suggestion_cache", {}).items()
        }
        self._expert_traces = list(state.get("expert_traces", []))

    def _evict_cache_if_needed(self) -> None:
        """Evict oldest entries when cache exceeds max size (#121)."""
        if len(self._suggestion_cache) > self._MAX_SUGGESTION_CACHE:
            # Remove oldest 25% of entries
            evict_count = len(self._suggestion_cache) // 4
            keys_to_remove = list(self._suggestion_cache.keys())[:evict_count]
            for key in keys_to_remove:
                del self._suggestion_cache[key]

    def add_expert_trace(self, trace: Dict[str, Any]) -> None:
        """Add an expert reasoning trace from seeded book knowledge."""
        self._expert_traces.append(trace)
    
    def add_historical_cause(
        self,
        cause: str,
        waste_category: LeanWasteCategory,
    ) -> None:
        """Add a historical root cause for pattern matching."""
        self._historical_causes.append((cause, waste_category))
    
    def analyze_problem(
        self,
        problem_statement: str,
        current_whys: Optional[List[str]] = None,
    ) -> List[RootCauseSuggestion]:
        """
        Analyze a problem statement and suggest potential root causes.
        
        Args:
            problem_statement: The problem statement
            current_whys: Already identified "whys"
            
        Returns:
            List of suggested root causes
        """
        current_whys = current_whys or []
        next_why = len(current_whys) + 1
        
        # Combine all text for analysis
        all_text = problem_statement.lower()
        for why in current_whys:
            all_text += " " + why.lower()
        
        suggestions = []
        
        # Match against known patterns
        for pattern in self.ROOT_CAUSE_PATTERNS:
            score = self._calculate_pattern_match(all_text, pattern["keywords"])
            
            if score > 0.3:  # Threshold
                # Check if this pattern is already in current whys
                already_used = any(
                    pattern["pattern"].lower() in why.lower()
                    for why in current_whys
                )
                
                if not already_used:
                    suggestion = RootCauseSuggestion(
                        why_number=next_why,
                        suggested_cause=pattern["suggestion"],
                        confidence=min(0.95, score),
                        waste_category=pattern["waste"],
                        muda_type=pattern.get("muda"),
                        similar_historical_causes=self._find_similar_historical(
                            pattern["pattern"]
                        ),
                        evidence_needed=self._get_evidence_needs(pattern["pattern"]),
                    )
                    suggestions.append(suggestion)

        # Match against seeded expert traces (distilled books)
        for trace in self._expert_traces:
            findings = trace.get("findings", {})
            distilled_principle = findings.get("distilled_principle", "")
            
            # Require meaningful keyword overlap with word-boundary matching (#193)
            principle_keywords = [kw for kw in distilled_principle.lower().split() if len(kw) > 4]
            if principle_keywords:
                matched = sum(
                    1 for kw in principle_keywords
                    if re.search(rf'\b{re.escape(kw)}\b', all_text)
                )
                if matched / len(principle_keywords) >= 0.4:
                    suggestion = RootCauseSuggestion(
                        why_number=next_why,
                        suggested_cause=f"Expert Principle: {distilled_principle}",
                        confidence=0.85,
                        waste_category=LeanWasteCategory.MUDA, # Default for expert principles
                        similar_historical_causes=[findings.get("source_book", "Distilled Knowledge")],
                        evidence_needed=trace.get("recommendations", [])
                    )
                    suggestions.append(suggestion)
        
        # Add general "go deeper" suggestions if few matches
        if len(suggestions) < 2:
            waste_category = self._classify_waste(all_text)
            
            suggestions.append(RootCauseSuggestion(
                why_number=next_why,
                suggested_cause="Ask 'Why did this condition exist?' to go deeper.",
                confidence=0.5,
                waste_category=waste_category,
                evidence_needed=["Direct observation at gemba", "Data collection"],
            ))
        
        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        
        return suggestions[:5]
    
    def _calculate_pattern_match(
        self,
        text: str,
        keywords: List[str],
    ) -> float:
        """Calculate pattern match score using word-boundary matching.

        Uses ``re`` word boundaries so that e.g. 'wait' does not match
        'waiting' or 'await'. (#215)
        """
        if not keywords:
            return 0.0
        matches = sum(
            1
            for kw in keywords
            if re.search(rf"\b{re.escape(kw)}", text)
        )
        return matches / len(keywords)
    
    def _classify_waste(self, text: str) -> LeanWasteCategory:
        """Classify the waste category from text."""
        scores = {}
        
        for category, keywords in self.WASTE_KEYWORDS.items():
            score = self._calculate_pattern_match(text, keywords)
            scores[category] = score
        
        if not scores:
            return LeanWasteCategory.MUDA
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def classify_muda_type(self, text: str) -> Optional[MudaType]:
        """Classify the specific Muda type from text."""
        scores = {}
        
        for muda_type, keywords in self.MUDA_KEYWORDS.items():
            score = self._calculate_pattern_match(text, keywords)
            if score > 0:
                scores[muda_type] = score
        
        if not scores:
            return None
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _find_similar_historical(self, pattern: str) -> List[str]:
        """Find similar historical causes."""
        similar = []
        pattern_lower = pattern.lower()
        
        for cause, _ in self._historical_causes:
            if any(
                word in cause.lower()
                for word in pattern_lower.split()
            ):
                similar.append(cause)
        
        return similar[:3]
    
    def _get_evidence_needs(self, pattern: str) -> List[str]:
        """Get evidence needs for a pattern."""
        evidence_map = {
            "lack of standard": [
                "Review existing work instructions",
                "Observe different operators doing same task",
            ],
            "training gap": [
                "Check training records",
                "Interview operators",
            ],
            "equipment failure": [
                "Review maintenance logs",
                "Inspect equipment",
            ],
            "capacity constraint": [
                "Measure actual vs planned capacity",
                "Track demand patterns",
            ],
            "communication gap": [
                "Trace information flow",
                "Review meeting notes",
            ],
            "quality issue": [
                "Review quality data",
                "Inspect samples",
            ],
            "scheduling problem": [
                "Review schedule adherence",
                "Analyze lead times",
            ],
            "material issue": [
                "Check incoming inspection data",
                "Review supplier performance",
            ],
        }
        
        return evidence_map.get(pattern, ["Gather data at gemba"])
    
    def get_waste_summary(
        self,
        suggestions: List[RootCauseSuggestion],
    ) -> Dict[str, Any]:
        """Get a summary of waste categories from suggestions."""
        waste_counts = Counter(s.waste_category.value for s in suggestions)
        muda_counts = Counter(
            s.muda_type.value for s in suggestions if s.muda_type
        )
        
        return {
            "primary_waste": max(waste_counts, key=lambda k: waste_counts[k]) if waste_counts else None,
            "waste_distribution": dict(waste_counts),
            "muda_types": dict(muda_counts),
            "total_suggestions": len(suggestions),
        }


# =============================================================================
# Sensei Reasoning Engine (Main Service)
# =============================================================================

class SenseiReasoningEngine(PersistentServiceMixin):
    """
    Main reasoning engine combining A3 pattern learning, Socratic mentoring,
    and 5 Whys root cause analysis.
    """

    SERVICE_NAME = "reasoning_engine"

    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
    
    def __init__(
        self,
        default_persona: MentorPersona = MentorPersona.THE_SENSEI,
    ):
        self.pattern_analyzer = A3PatternAnalyzer()
        self.mentor = SocraticMentor(default_persona)
        self.five_whys = FiveWhysAssistant()
        
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        state = await self.load_state(self._DEFAULT_TENANT_ID, "state")
        if not state:
            self._state_loaded = True
            return

        pattern_state = state.get("pattern_analyzer")
        if pattern_state:
            self.pattern_analyzer.load_state(pattern_state)

        mentor_state = state.get("mentor")
        if mentor_state:
            self.mentor.load_state(mentor_state)

        five_whys_state = state.get("five_whys")
        if five_whys_state:
            self.five_whys.load_state(five_whys_state)

        sessions = {}
        for session_id, session_data in state.get("active_sessions", {}).items():
            started_at = session_data.get("started_at")
            sessions[session_id] = {
                "a3_id": session_data.get("a3_id"),
                "started_at": datetime.fromisoformat(started_at) if started_at else _utcnow(),
                "prompts_sent": list(session_data.get("prompts_sent", [])),
                "responses": list(session_data.get("responses", [])),
            }
        self._active_sessions = sessions
        self._state_loaded = True

    async def persist_all(self) -> None:
        state = {
            "pattern_analyzer": self.pattern_analyzer.export_state(),
            "mentor": self.mentor.export_state(),
            "five_whys": self.five_whys.export_state(),
            "active_sessions": {
                session_id: {
                    "a3_id": session.get("a3_id"),
                    "started_at": session.get("started_at").isoformat()
                    if session.get("started_at")
                    else None,
                    "prompts_sent": list(session.get("prompts_sent", [])),
                    "responses": list(session.get("responses", [])),
                }
                for session_id, session in self._active_sessions.items()
            },
        }
        await self.save_state(self._DEFAULT_TENANT_ID, "state", state)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()
    
    def register_closed_a3(self, a3: A3Report) -> None:
        """Register a closed A3 for learning."""
        self.pattern_analyzer.add_closed_a3(a3)
        
        # Also learn from root causes
        for cause in a3.root_causes:
            for waste in a3.waste_categories:
                self.five_whys.add_historical_cause(cause, waste)

    def load_seeded_knowledge(self, expert_traces: List[Dict[str, Any]]) -> None:
        """Load seeded expert traces from distilled books into the reasoning engine."""
        for trace in expert_traces:
            self.five_whys.add_expert_trace(trace)
            self.mentor.add_expert_trace(trace)
        logger.info(f"Loaded {len(expert_traces)} seeded expert traces into Reasoning Engine.")
    
    def suggest_countermeasures(
        self,
        target_kpis: List[str],
        problem_category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float, str]]:
        """Suggest countermeasures based on historical patterns."""
        return self.pattern_analyzer.suggest_countermeasures(
            target_kpis, problem_category, top_k
        )
    
    def get_challenging_prompts(
        self,
        content: str,
        phase: A3Phase,
        persona: Optional[MentorPersona] = None,
        max_prompts: int = 3,
    ) -> List[ChallengingPrompt]:
        """Get Socratic challenging prompts for A3 content."""
        return self.mentor.generate_prompts(content, phase, persona, max_prompts)
    
    def generate_socratic_prompts(
        self,
        content: str,
        phase: A3Phase,
        persona: Optional[MentorPersona] = None,
        max_prompts: int = 3,
    ) -> List[ChallengingPrompt]:
        """Generate Socratic prompts for learning content. Alias for get_challenging_prompts."""
        return self.get_challenging_prompts(content, phase, persona, max_prompts)
    
    def analyze_root_cause(
        self,
        problem_statement: str,
        current_whys: Optional[List[str]] = None,
    ) -> List[RootCauseSuggestion]:
        """Analyze problem and suggest root causes."""
        return self.five_whys.analyze_problem(problem_statement, current_whys)
    
    def classify_waste(self, text: str) -> Tuple[LeanWasteCategory, Optional[MudaType]]:
        """Classify waste category from text."""
        waste = self.five_whys._classify_waste(text.lower())
        muda = self.five_whys.classify_muda_type(text.lower())
        return waste, muda
    
    def start_mentoring_session(self, session_id: str, a3_id: str) -> None:
        """Start a new mentoring session."""
        self._active_sessions[session_id] = {
            "a3_id": a3_id,
            "started_at": _utcnow(),
            "prompts_sent": [],
            "responses": [],
        }
        self.mentor.clear_session()
    
    def end_mentoring_session(self, session_id: str) -> Dict[str, Any]:
        """End a mentoring session and return summary."""
        session = self._active_sessions.pop(session_id, None)
        if not session:
            return {}
        
        return {
            "a3_id": session["a3_id"],
            "duration": (_utcnow() - session["started_at"]).total_seconds(),
            "prompts_count": len(session["prompts_sent"]),
            "session_prompts": self.mentor.get_session_prompts(),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "pattern_analyzer": self.pattern_analyzer.get_stats(),
            "active_sessions": len(self._active_sessions),
            "historical_causes": len(self.five_whys._historical_causes),
        }

    async def register_closed_a3_async(self, a3: A3Report) -> None:
        await self._ensure_loaded()
        self.register_closed_a3(a3)
        await self.persist_all()

    async def load_seeded_knowledge_async(self, expert_traces: List[Dict[str, Any]]) -> None:
        await self._ensure_loaded()
        self.load_seeded_knowledge(expert_traces)
        await self.persist_all()

    async def suggest_countermeasures_async(
        self,
        target_kpis: List[str],
        problem_category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float, str]]:
        await self._ensure_loaded()
        return self.suggest_countermeasures(target_kpis, problem_category, top_k)

    async def get_challenging_prompts_async(
        self,
        content: str,
        phase: A3Phase,
        persona: Optional[MentorPersona] = None,
        max_prompts: int = 3,
    ) -> List[ChallengingPrompt]:
        await self._ensure_loaded()
        return self.get_challenging_prompts(content, phase, persona, max_prompts)

    async def analyze_root_cause_async(
        self,
        problem_statement: str,
        current_whys: Optional[List[str]] = None,
    ) -> List[RootCauseSuggestion]:
        await self._ensure_loaded()
        suggestions = self.analyze_root_cause(problem_statement, current_whys)
        await self.persist_all()
        return suggestions

    async def classify_waste_async(
        self,
        text: str,
    ) -> Tuple[LeanWasteCategory, Optional[MudaType]]:
        await self._ensure_loaded()
        return self.classify_waste(text)

    async def start_mentoring_session_async(self, session_id: str, a3_id: str) -> None:
        await self._ensure_loaded()
        self.start_mentoring_session(session_id, a3_id)
        await self.persist_all()

    async def end_mentoring_session_async(self, session_id: str) -> Dict[str, Any]:
        await self._ensure_loaded()
        summary = self.end_mentoring_session(session_id)
        await self.persist_all()
        return summary

    async def get_stats_async(self) -> Dict[str, Any]:
        await self._ensure_loaded()
        return self.get_stats()


# =============================================================================
# Factory Function
# =============================================================================

def create_reasoning_engine(
    default_persona: MentorPersona = MentorPersona.THE_SENSEI,
) -> SenseiReasoningEngine:
    """
    Create a Sensei Reasoning Engine.
    
    Args:
        default_persona: Default mentor persona
        
    Returns:
        Configured SenseiReasoningEngine
    """
    return SenseiReasoningEngine(default_persona=default_persona)

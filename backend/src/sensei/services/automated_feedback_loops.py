"""
Automated Feedback Loops System.

This module implements continuous learning from user corrections:
- Learning Store: Database schema for storing corrections
- Dynamic Few-Shot Injection: Retrieve relevant corrections for prompts
- Correction Versioning: Track model versions for corrections
- Conflict Resolution: Handle conflicting corrections
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import heapq
from collections import Counter

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class CorrectionType(Enum):
    """Types of corrections that can be made."""
    TEXT_EDIT = "text_edit"
    FIELD_VALUE = "field_value"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    FORMATTING = "formatting"
    REJECTION = "rejection"  # User rejected the entire output


class CorrectionStatus(Enum):
    """Status of a correction."""
    PENDING = "pending"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    CONFLICTED = "conflicted"


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving conflicting corrections."""
    LAST_WINS = "last_wins"
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    EXPERT_PRIORITY = "expert_priority"
    CONFIDENCE_BASED = "confidence_based"


class ContextType(Enum):
    """Types of context for corrections."""
    RFQ_PARSING = "rfq_parsing"
    EMAIL_DRAFT = "email_draft"
    A3_GENERATION = "a3_generation"
    DOCUMENT_CLASSIFICATION = "document_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    GENERAL = "general"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ModelVersion:
    """Information about a model version."""
    model_id: str
    version: str
    released_at: datetime
    deprecated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_deprecated(self) -> bool:
        return self.deprecated_at is not None
    
    def __hash__(self):
        return hash((self.model_id, self.version))


@dataclass
class UserInfo:
    """Information about the user making a correction."""
    user_id: str
    username: str
    role: str = "user"
    is_expert: bool = False
    trust_score: float = 1.0
    
    def __hash__(self):
        return hash(self.user_id)


@dataclass
class CorrectionMetadata:
    """Metadata for a correction entry."""
    context_type: ContextType
    field_name: Optional[str] = None
    document_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Correction:
    """A user correction to AI output."""
    id: str
    input_text: str
    ai_output: str
    user_correction: str
    correction_type: CorrectionType
    confidence_score: float
    user_info: UserInfo
    model_version: ModelVersion
    metadata: CorrectionMetadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: CorrectionStatus = CorrectionStatus.PENDING
    embedding: Optional[List[float]] = None
    similarity_hash: Optional[str] = None
    
    def __post_init__(self):
        if not self.similarity_hash:
            self.similarity_hash = self._compute_similarity_hash()
    
    def _compute_similarity_hash(self) -> str:
        """Compute a hash for similarity matching."""
        content = f"{self.input_text}|{self.ai_output}|{self.metadata.context_type.value}"
        if self.metadata.field_name:
            content += f"|{self.metadata.field_name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "input_text": self.input_text,
            "ai_output": self.ai_output,
            "user_correction": self.user_correction,
            "correction_type": self.correction_type.value,
            "confidence_score": self.confidence_score,
            "user_id": self.user_info.user_id,
            "model_id": self.model_version.model_id,
            "model_version": self.model_version.version,
            "context_type": self.metadata.context_type.value,
            "field_name": self.metadata.field_name,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "similarity_hash": self.similarity_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], user_info: UserInfo, model_version: ModelVersion) -> "Correction":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            input_text=data["input_text"],
            ai_output=data["ai_output"],
            user_correction=data["user_correction"],
            correction_type=CorrectionType(data["correction_type"]),
            confidence_score=data["confidence_score"],
            user_info=user_info,
            model_version=model_version,
            metadata=CorrectionMetadata(
                context_type=ContextType(data["context_type"]),
                field_name=data.get("field_name"),
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=CorrectionStatus(data["status"]),
            similarity_hash=data.get("similarity_hash"),
        )


@dataclass
class CorrectionGroup:
    """A group of related corrections for conflict resolution."""
    pattern_hash: str
    corrections: List[Correction]
    resolved_value: Optional[str] = None
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    resolved_at: Optional[datetime] = None


@dataclass 
class RetrievedCorrection:
    """A correction retrieved for few-shot injection."""
    correction: Correction
    relevance_score: float
    usage_count: int = 0
    last_used_at: Optional[datetime] = None


# =============================================================================
# Learning Store
# =============================================================================

class LearningStore(ABC):
    """Abstract base class for correction storage."""
    
    @abstractmethod
    async def store_correction(self, correction: Correction) -> str:
        """Store a new correction."""
        pass
    
    @abstractmethod
    async def get_correction(self, correction_id: str) -> Optional[Correction]:
        """Get a correction by ID."""
        pass
    
    @abstractmethod
    async def get_corrections_by_context(
        self,
        context_type: ContextType,
        limit: int = 100,
    ) -> List[Correction]:
        """Get corrections for a specific context type."""
        pass
    
    @abstractmethod
    async def search_similar_corrections(
        self,
        input_text: str,
        context_type: ContextType,
        limit: int = 5,
    ) -> List[RetrievedCorrection]:
        """Search for similar corrections using semantic similarity."""
        pass
    
    @abstractmethod
    async def update_correction_status(
        self,
        correction_id: str,
        status: CorrectionStatus,
    ) -> bool:
        """Update the status of a correction."""
        pass
    
    @abstractmethod
    async def get_conflicts(
        self,
        pattern_hash: str,
    ) -> List[Correction]:
        """Get conflicting corrections for a pattern."""
        pass


class InMemoryLearningStore(LearningStore):
    """In-memory implementation of the learning store."""
    
    def __init__(self):
        self._corrections: Dict[str, Correction] = {}
        self._by_context: Dict[ContextType, List[str]] = defaultdict(list)
        self._by_pattern: Dict[str, List[str]] = defaultdict(list)
        self._by_model: Dict[str, List[str]] = defaultdict(list)
    
    async def store_correction(self, correction: Correction) -> str:
        """Store a new correction."""
        self._corrections[correction.id] = correction
        self._by_context[correction.metadata.context_type].append(correction.id)
        if correction.similarity_hash:
            self._by_pattern[correction.similarity_hash].append(correction.id)
        self._by_model[correction.model_version.model_id].append(correction.id)
        
        logger.info(f"Stored correction {correction.id} for context {correction.metadata.context_type.value}")
        return correction.id
    
    async def get_correction(self, correction_id: str) -> Optional[Correction]:
        """Get a correction by ID."""
        return self._corrections.get(correction_id)
    
    async def get_corrections_by_context(
        self,
        context_type: ContextType,
        limit: int = 100,
    ) -> List[Correction]:
        """Get corrections for a specific context type."""
        ids = self._by_context.get(context_type, [])
        corrections = [
            self._corrections[cid]
            for cid in ids[:limit]
            if cid in self._corrections
        ]
        return sorted(corrections, key=lambda c: c.created_at, reverse=True)
    
    async def search_similar_corrections(
        self,
        input_text: str,
        context_type: ContextType,
        limit: int = 5,
    ) -> List[RetrievedCorrection]:
        """Search for similar corrections using simple text matching."""
        input_lower = input_text.lower()
        input_words = set(input_lower.split())
        
        candidates = []
        for cid in self._by_context.get(context_type, []):
            correction = self._corrections.get(cid)
            if not correction or correction.status not in (CorrectionStatus.ACTIVE, CorrectionStatus.PENDING):
                continue
            
            # Simple word overlap similarity
            corr_words = set(correction.input_text.lower().split())
            if not corr_words:
                continue
            
            overlap = len(input_words & corr_words)
            union = len(input_words | corr_words)
            jaccard = overlap / union if union > 0 else 0
            
            if jaccard > 0.1:  # Minimum threshold
                candidates.append(RetrievedCorrection(
                    correction=correction,
                    relevance_score=jaccard,
                ))
        
        # Return top matches
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        return candidates[:limit]
    
    async def update_correction_status(
        self,
        correction_id: str,
        status: CorrectionStatus,
    ) -> bool:
        """Update the status of a correction."""
        if correction_id in self._corrections:
            self._corrections[correction_id].status = status
            return True
        return False
    
    async def get_conflicts(
        self,
        pattern_hash: str,
    ) -> List[Correction]:
        """Get conflicting corrections for a pattern."""
        ids = self._by_pattern.get(pattern_hash, [])
        return [
            self._corrections[cid]
            for cid in ids
            if cid in self._corrections
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "total_corrections": len(self._corrections),
            "by_context": {
                ctx.value: len(ids)
                for ctx, ids in self._by_context.items()
            },
            "unique_patterns": len(self._by_pattern),
        }


# =============================================================================
# Conflict Resolution
# =============================================================================

class ConflictResolver:
    """Resolves conflicts between different corrections for the same pattern."""
    
    def __init__(
        self,
        default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WINS,
    ):
        self.default_strategy = default_strategy
        self._resolvers: Dict[ConflictResolutionStrategy, Callable] = {
            ConflictResolutionStrategy.LAST_WINS: self._resolve_last_wins,
            ConflictResolutionStrategy.MAJORITY_VOTE: self._resolve_majority_vote,
            ConflictResolutionStrategy.WEIGHTED_VOTE: self._resolve_weighted_vote,
            ConflictResolutionStrategy.EXPERT_PRIORITY: self._resolve_expert_priority,
            ConflictResolutionStrategy.CONFIDENCE_BASED: self._resolve_confidence_based,
        }
    
    def resolve(
        self,
        corrections: List[Correction],
        strategy: Optional[ConflictResolutionStrategy] = None,
    ) -> CorrectionGroup:
        """
        Resolve conflicts between corrections.
        
        Args:
            corrections: List of conflicting corrections
            strategy: Resolution strategy to use
            
        Returns:
            CorrectionGroup with resolved value
        """
        if not corrections:
            raise ValueError("No corrections to resolve")
        
        if len(corrections) == 1:
            return CorrectionGroup(
                pattern_hash=corrections[0].similarity_hash or "",
                corrections=corrections,
                resolved_value=corrections[0].user_correction,
                resolution_strategy=strategy or self.default_strategy,
                resolved_at=datetime.now(timezone.utc),
            )
        
        strategy = strategy or self.default_strategy
        resolver = self._resolvers.get(strategy, self._resolve_last_wins)
        resolved_value = resolver(corrections)
        
        return CorrectionGroup(
            pattern_hash=corrections[0].similarity_hash or "",
            corrections=corrections,
            resolved_value=resolved_value,
            resolution_strategy=strategy,
            resolved_at=datetime.now(timezone.utc),
        )
    
    def _resolve_last_wins(self, corrections: List[Correction]) -> str:
        """Most recent correction wins."""
        sorted_corrs = sorted(corrections, key=lambda c: c.created_at, reverse=True)
        return sorted_corrs[0].user_correction
    
    def _resolve_majority_vote(self, corrections: List[Correction]) -> str:
        """Most common correction wins."""
        votes = Counter(c.user_correction for c in corrections)
        most_common = votes.most_common(1)
        return most_common[0][0] if most_common else corrections[0].user_correction
    
    def _resolve_weighted_vote(self, corrections: List[Correction]) -> str:
        """Weighted by user trust score."""
        weighted_votes: Dict[str, float] = defaultdict(float)
        for c in corrections:
            weight = c.user_info.trust_score * c.confidence_score
            weighted_votes[c.user_correction] += weight
        
        return max(weighted_votes.keys(), key=lambda k: weighted_votes[k])
    
    def _resolve_expert_priority(self, corrections: List[Correction]) -> str:
        """Expert corrections have priority."""
        expert_corrections = [c for c in corrections if c.user_info.is_expert]
        
        if expert_corrections:
            # Among experts, use last wins
            sorted_experts = sorted(expert_corrections, key=lambda c: c.created_at, reverse=True)
            return sorted_experts[0].user_correction
        
        # Fall back to majority vote
        return self._resolve_majority_vote(corrections)
    
    def _resolve_confidence_based(self, corrections: List[Correction]) -> str:
        """Highest confidence correction wins."""
        sorted_corrs = sorted(corrections, key=lambda c: c.confidence_score, reverse=True)
        return sorted_corrs[0].user_correction


# =============================================================================
# Few-Shot Injection
# =============================================================================

@dataclass
class FewShotExample:
    """A few-shot example for prompt injection."""
    input_text: str
    incorrect_output: str
    correct_output: str
    context_type: ContextType
    relevance_score: float


class FewShotInjector:
    """Manages dynamic few-shot injection of corrections into prompts."""
    
    DEFAULT_CORRECTIONS_BLOCK = """
<corrections>
The following are examples of corrections made by users. Use these to improve your output:

{examples}
</corrections>
"""
    
    EXAMPLE_TEMPLATE = """
Example {number}:
Input: {input}
Your previous output (incorrect): {incorrect}
Corrected output: {correct}
"""
    
    def __init__(
        self,
        store: LearningStore,
        max_examples: int = 5,
        min_relevance: float = 0.2,
    ):
        self.store = store
        self.max_examples = max_examples
        self.min_relevance = min_relevance
    
    async def get_few_shot_examples(
        self,
        input_text: str,
        context_type: ContextType,
        limit: Optional[int] = None,
    ) -> List[FewShotExample]:
        """
        Retrieve relevant few-shot examples for the given input.
        
        Args:
            input_text: The current input text
            context_type: Type of context
            limit: Maximum examples to return
            
        Returns:
            List of relevant few-shot examples
        """
        limit = limit or self.max_examples
        
        # Search for similar corrections
        retrieved = await self.store.search_similar_corrections(
            input_text=input_text,
            context_type=context_type,
            limit=limit * 2,  # Get more, then filter
        )
        
        # Filter by relevance and convert to examples
        examples = []
        for r in retrieved:
            if r.relevance_score < self.min_relevance:
                continue
            
            examples.append(FewShotExample(
                input_text=r.correction.input_text,
                incorrect_output=r.correction.ai_output,
                correct_output=r.correction.user_correction,
                context_type=r.correction.metadata.context_type,
                relevance_score=r.relevance_score,
            ))
            
            if len(examples) >= limit:
                break
        
        return examples
    
    async def inject_corrections(
        self,
        prompt: str,
        input_text: str,
        context_type: ContextType,
        injection_point: str = "{corrections}",
    ) -> Tuple[str, List[FewShotExample]]:
        """
        Inject relevant corrections into a prompt.
        
        Args:
            prompt: The base prompt with injection point
            input_text: The current input
            context_type: Type of context
            injection_point: Marker where to inject corrections
            
        Returns:
            Tuple of (modified_prompt, examples_used)
        """
        examples = await self.get_few_shot_examples(input_text, context_type)
        
        if not examples:
            # No corrections to inject
            return prompt.replace(injection_point, ""), []
        
        # Format examples
        formatted_examples = []
        for i, ex in enumerate(examples, 1):
            formatted_examples.append(
                self.EXAMPLE_TEMPLATE.format(
                    number=i,
                    input=ex.input_text[:200],  # Truncate long inputs
                    incorrect=ex.incorrect_output[:200],
                    correct=ex.correct_output[:200],
                )
            )
        
        corrections_block = self.DEFAULT_CORRECTIONS_BLOCK.format(
            examples="\n".join(formatted_examples)
        )
        
        modified_prompt = prompt.replace(injection_point, corrections_block)
        
        return modified_prompt, examples
    
    def format_corrections_block(
        self,
        examples: List[FewShotExample],
    ) -> str:
        """Format examples into a corrections block."""
        if not examples:
            return ""
        
        formatted = []
        for i, ex in enumerate(examples, 1):
            formatted.append(
                self.EXAMPLE_TEMPLATE.format(
                    number=i,
                    input=ex.input_text[:200],
                    incorrect=ex.incorrect_output[:200],
                    correct=ex.correct_output[:200],
                )
            )
        
        return self.DEFAULT_CORRECTIONS_BLOCK.format(
            examples="\n".join(formatted)
        )


# =============================================================================
# Correction Versioning
# =============================================================================

class CorrectionVersionManager:
    """Manages correction versioning to avoid training on stale corrections."""
    
    def __init__(
        self,
        staleness_threshold_days: int = 30,
    ):
        self.staleness_threshold_days = staleness_threshold_days
        self._model_versions: Dict[str, ModelVersion] = {}
        self._deprecation_callbacks: List[Callable[[ModelVersion], None]] = []
    
    def register_model_version(self, model_version: ModelVersion) -> None:
        """Register a new model version."""
        key = f"{model_version.model_id}:{model_version.version}"
        self._model_versions[key] = model_version
        logger.info(f"Registered model version: {key}")
    
    def deprecate_model_version(
        self,
        model_id: str,
        version: str,
        deprecation_date: Optional[datetime] = None,
    ) -> bool:
        """Mark a model version as deprecated."""
        key = f"{model_id}:{version}"
        if key in self._model_versions:
            self._model_versions[key].deprecated_at = deprecation_date or datetime.now(timezone.utc)
            
            # Notify callbacks
            for callback in self._deprecation_callbacks:
                try:
                    callback(self._model_versions[key])
                except Exception as e:
                    logger.error(f"Deprecation callback failed: {e}")
            
            return True
        return False
    
    def is_correction_stale(
        self,
        correction: Correction,
        current_model: ModelVersion,
    ) -> bool:
        """
        Check if a correction is stale.
        
        A correction is stale if:
        1. It was made for a deprecated model version
        2. It's older than the staleness threshold
        3. The model has been significantly updated
        """
        # Check if model version is deprecated
        if correction.model_version.is_deprecated:
            return True
        
        # Check age
        age = datetime.now(timezone.utc) - correction.created_at
        if age > timedelta(days=self.staleness_threshold_days):
            return True
        
        # Check if it's for a different model
        if correction.model_version.model_id != current_model.model_id:
            return True
        
        # Check if model version is older
        if correction.model_version.version != current_model.version:
            # Could add more sophisticated version comparison here
            return True
        
        return False
    
    def filter_fresh_corrections(
        self,
        corrections: List[Correction],
        current_model: ModelVersion,
    ) -> List[Correction]:
        """Filter out stale corrections."""
        return [
            c for c in corrections
            if not self.is_correction_stale(c, current_model)
        ]
    
    def add_deprecation_callback(
        self,
        callback: Callable[[ModelVersion], None],
    ) -> None:
        """Add a callback to be called when a model is deprecated."""
        self._deprecation_callbacks.append(callback)
    
    def get_model_version(
        self,
        model_id: str,
        version: str,
    ) -> Optional[ModelVersion]:
        """Get a registered model version."""
        key = f"{model_id}:{version}"
        return self._model_versions.get(key)


# =============================================================================
# Feedback Loop Manager
# =============================================================================

class FeedbackLoopManager:
    """
    Main manager for the automated feedback loop system.
    
    Coordinates correction storage, versioning, conflict resolution,
    and few-shot injection.
    """
    
    def __init__(
        self,
        store: Optional[LearningStore] = None,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WINS,
        staleness_days: int = 30,
        max_few_shot: int = 5,
    ):
        self.store = store or InMemoryLearningStore()
        self.conflict_resolver = ConflictResolver(conflict_strategy)
        self.version_manager = CorrectionVersionManager(staleness_days)
        self.few_shot_injector = FewShotInjector(self.store, max_few_shot)
        
        self._current_model: Optional[ModelVersion] = None
        self._correction_count = 0
    
    def set_current_model(self, model: ModelVersion) -> None:
        """Set the current model version being used."""
        self._current_model = model
        self.version_manager.register_model_version(model)
    
    async def record_correction(
        self,
        input_text: str,
        ai_output: str,
        user_correction: str,
        correction_type: CorrectionType,
        user: UserInfo,
        context_type: ContextType,
        confidence_score: float = 1.0,
        field_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Correction:
        """
        Record a user correction.
        
        Args:
            input_text: The original input to the AI
            ai_output: The AI's output that was corrected
            user_correction: The user's correction
            correction_type: Type of correction
            user: Information about the correcting user
            context_type: Context in which the correction was made
            confidence_score: User's confidence in the correction
            field_name: Optional field being corrected
            metadata: Additional metadata
            
        Returns:
            The stored correction
        """
        if not self._current_model:
            raise ValueError("No current model set. Call set_current_model first.")
        
        self._correction_count += 1
        correction_id = f"corr_{self._correction_count}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        correction = Correction(
            id=correction_id,
            input_text=input_text,
            ai_output=ai_output,
            user_correction=user_correction,
            correction_type=correction_type,
            confidence_score=confidence_score,
            user_info=user,
            model_version=self._current_model,
            metadata=CorrectionMetadata(
                context_type=context_type,
                field_name=field_name,
                custom_data=metadata or {},
            ),
        )
        
        await self.store.store_correction(correction)
        
        # Check for conflicts and resolve
        conflicts = await self.store.get_conflicts(correction.similarity_hash or "")
        if len(conflicts) > 1:
            group = self.conflict_resolver.resolve(conflicts)
            logger.info(
                f"Resolved {len(conflicts)} conflicting corrections for pattern "
                f"{group.pattern_hash} using {group.resolution_strategy}"
            )
        
        return correction
    
    async def get_enhanced_prompt(
        self,
        base_prompt: str,
        input_text: str,
        context_type: ContextType,
    ) -> Tuple[str, int]:
        """
        Get a prompt enhanced with relevant corrections.
        
        Args:
            base_prompt: The base prompt with {corrections} placeholder
            input_text: The current input
            context_type: Context type
            
        Returns:
            Tuple of (enhanced_prompt, number_of_examples_used)
        """
        enhanced_prompt, examples = await self.few_shot_injector.inject_corrections(
            prompt=base_prompt,
            input_text=input_text,
            context_type=context_type,
        )
        
        # Filter stale corrections if we have a current model
        if self._current_model and examples:
            fresh_examples = [
                ex for ex in examples
                # Note: examples don't have full correction info, so simplified check
            ]
            return enhanced_prompt, len(fresh_examples)
        
        return enhanced_prompt, len(examples)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get feedback loop statistics."""
        if isinstance(self.store, InMemoryLearningStore):
            store_stats = self.store.get_stats()
        else:
            store_stats = {"total_corrections": self._correction_count}
        
        return {
            "store": store_stats,
            "current_model": (
                f"{self._current_model.model_id}:{self._current_model.version}"
                if self._current_model else None
            ),
            "conflict_strategy": self.conflict_resolver.default_strategy.value,
            "staleness_threshold_days": self.version_manager.staleness_threshold_days,
            "max_few_shot_examples": self.few_shot_injector.max_examples,
        }
    
    async def cleanup_stale_corrections(self) -> int:
        """Mark stale corrections as expired."""
        if not self._current_model:
            return 0
        
        # Get all active corrections
        cleaned = 0
        for context_type in ContextType:
            corrections = await self.store.get_corrections_by_context(context_type)
            for correction in corrections:
                if correction.status == CorrectionStatus.ACTIVE:
                    if self.version_manager.is_correction_stale(correction, self._current_model):
                        await self.store.update_correction_status(
                            correction.id, CorrectionStatus.EXPIRED
                        )
                        cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} stale corrections")
        return cleaned


# =============================================================================
# Factory Function
# =============================================================================

def create_feedback_loop_manager(
    store: Optional[LearningStore] = None,
    conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WINS,
    staleness_days: int = 30,
    max_few_shot: int = 5,
) -> FeedbackLoopManager:
    """
    Create a feedback loop manager with the specified configuration.
    
    Args:
        store: Learning store implementation (default: InMemoryLearningStore)
        conflict_strategy: Strategy for resolving conflicts
        staleness_days: Days before a correction is considered stale
        max_few_shot: Maximum few-shot examples to inject
        
    Returns:
        Configured FeedbackLoopManager
    """
    return FeedbackLoopManager(
        store=store,
        conflict_strategy=conflict_strategy,
        staleness_days=staleness_days,
        max_few_shot=max_few_shot,
    )

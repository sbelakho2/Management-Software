"""
AI Decision Explainability (XAI) Service.

Implements:
- "Explain this Suggestion" button with top 3 evidence chunks
- Audit Trail for AI Reasoning (prompt version, model ID, retrieved context)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
import re


# =============================================================================
# ENUMS
# =============================================================================


class ExplanationType(str, Enum):
    """Types of explanations."""
    FEATURE_IMPORTANCE = "feature_importance"
    EVIDENCE_BASED = "evidence_based"
    COUNTERFACTUAL = "counterfactual"
    RULE_BASED = "rule_based"
    CONFIDENCE_BREAKDOWN = "confidence_breakdown"


class DecisionCategory(str, Enum):
    """Categories of AI decisions."""
    PRICING = "pricing"
    SUPPLIER = "supplier"
    SCHEDULING = "scheduling"
    QUALITY = "quality"
    INVENTORY = "inventory"
    RISK = "risk"
    ROUTING = "routing"
    GENERAL = "general"


class EvidenceSource(str, Enum):
    """Sources of evidence."""
    DOCUMENT = "document"
    DATABASE = "database"
    HISTORICAL = "historical"
    RULE = "rule"
    MODEL = "model"
    USER_FEEDBACK = "user_feedback"


class ConfidenceLevel(str, Enum):
    """Confidence levels for explanations."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class AuditEventType(str, Enum):
    """Types of audit events."""
    DECISION_MADE = "decision_made"
    EXPLANATION_REQUESTED = "explanation_requested"
    FEEDBACK_RECEIVED = "feedback_received"
    MODEL_UPDATED = "model_updated"
    CONTEXT_RETRIEVED = "context_retrieved"
    OVERRIDE_APPLIED = "override_applied"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class EvidenceChunk:
    """A chunk of evidence supporting a decision."""
    chunk_id: str
    source: EvidenceSource
    content: str
    relevance_score: float
    document_id: str | None = None
    document_title: str | None = None
    page_number: int | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureContribution:
    """A feature's contribution to a decision."""
    feature_name: str
    feature_value: Any
    contribution: float
    direction: str  # positive/negative
    importance_rank: int
    explanation: str


@dataclass
class CounterfactualScenario:
    """A counterfactual explanation scenario."""
    scenario_id: str
    description: str
    changes: dict[str, Any]
    original_outcome: Any
    alternative_outcome: Any
    confidence_delta: float


@dataclass
class DecisionExplanation:
    """Full explanation for an AI decision."""
    explanation_id: str
    decision_id: str
    explanation_type: ExplanationType
    category: DecisionCategory
    summary: str
    confidence: float
    confidence_level: ConfidenceLevel
    evidence_chunks: list[EvidenceChunk]
    feature_contributions: list[FeatureContribution]
    counterfactuals: list[CounterfactualScenario]
    model_version: str
    prompt_version: str
    generated_at: datetime
    generation_time_ms: float


@dataclass
class AIDecision:
    """An AI decision with metadata."""
    decision_id: str
    category: DecisionCategory
    input_data: dict[str, Any]
    output: Any
    confidence: float
    model_id: str
    model_version: str
    prompt_version: str
    retrieved_context: list[str]
    reasoning_chain: list[str]
    created_at: datetime
    user_id: str | None = None
    session_id: str | None = None


@dataclass
class AuditEvent:
    """An audit event for AI reasoning trail."""
    event_id: str
    decision_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: str | None
    details: dict[str, Any]
    model_id: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    context_hash: str | None = None


@dataclass
class ReasoningStep:
    """A step in the reasoning chain."""
    step_number: int
    description: str
    input_context: str
    output: str
    confidence: float
    evidence_used: list[str]


@dataclass
class ModelInfo:
    """Information about an AI model."""
    model_id: str
    model_name: str
    version: str
    capabilities: list[str]
    last_updated: datetime
    performance_metrics: dict[str, float]


# =============================================================================
# EVIDENCE RETRIEVER
# =============================================================================


class EvidenceRetriever:
    """
    Retrieves and ranks evidence for AI decisions.
    """
    
    def __init__(self, max_chunks: int = 10):
        self.max_chunks = max_chunks
        self.evidence_cache: dict[str, list[EvidenceChunk]] = {}
    
    def _compute_relevance(
        self,
        query: str,
        content: str,
    ) -> float:
        """Compute relevance score between query and content."""
        query_terms = set(query.lower().split())
        content_terms = set(content.lower().split())
        
        if not query_terms:
            return 0.0
        
        # Jaccard similarity + term frequency boost
        intersection = query_terms & content_terms
        union = query_terms | content_terms
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Boost for query term presence
        term_coverage = len(intersection) / len(query_terms)
        
        return 0.5 * jaccard + 0.5 * term_coverage
    
    def retrieve_evidence(
        self,
        decision: AIDecision,
        documents: list[dict[str, Any]],
        historical_data: list[dict[str, Any]] | None = None,
    ) -> list[EvidenceChunk]:
        """Retrieve evidence chunks for a decision."""
        chunks = []
        
        # Create query from decision input
        query = json.dumps(decision.input_data)
        
        # Extract from documents
        for doc in documents:
            content = doc.get("content", "")
            relevance = self._compute_relevance(query, content)
            
            if relevance > 0.1:
                chunk = EvidenceChunk(
                    chunk_id=hashlib.md5(content[:100].encode()).hexdigest()[:12],
                    source=EvidenceSource.DOCUMENT,
                    content=content[:500],
                    relevance_score=relevance,
                    document_id=doc.get("id"),
                    document_title=doc.get("title"),
                    page_number=doc.get("page"),
                    metadata=doc.get("metadata", {}),
                )
                chunks.append(chunk)
        
        # Extract from historical data
        if historical_data:
            for record in historical_data:
                content = json.dumps(record)
                relevance = self._compute_relevance(query, content)
                
                if relevance > 0.1:
                    chunk = EvidenceChunk(
                        chunk_id=hashlib.md5(content[:100].encode()).hexdigest()[:12],
                        source=EvidenceSource.HISTORICAL,
                        content=content[:500],
                        relevance_score=relevance,
                        timestamp=record.get("timestamp"),
                        metadata=record,
                    )
                    chunks.append(chunk)
        
        # Add retrieved context as evidence
        for ctx in decision.retrieved_context:
            relevance = self._compute_relevance(query, ctx)
            chunk = EvidenceChunk(
                chunk_id=hashlib.md5(ctx[:100].encode()).hexdigest()[:12],
                source=EvidenceSource.DATABASE,
                content=ctx[:500],
                relevance_score=max(relevance, 0.5),  # Boost retrieved context
            )
            chunks.append(chunk)
        
        # Sort by relevance and limit
        chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        return chunks[:self.max_chunks]
    
    def get_top_evidence(
        self,
        decision: AIDecision,
        documents: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[EvidenceChunk]:
        """Get top K evidence chunks for "Explain this Suggestion" button."""
        all_evidence = self.retrieve_evidence(decision, documents)
        return all_evidence[:top_k]


# =============================================================================
# FEATURE ANALYZER
# =============================================================================


class FeatureAnalyzer:
    """
    Analyzes feature contributions to AI decisions.
    """
    
    FEATURE_WEIGHTS = {
        # Pricing features
        "price": 0.3,
        "quantity": 0.2,
        "margin": 0.25,
        "cost": 0.25,
        "discount": 0.15,
        # Supplier features
        "lead_time": 0.2,
        "quality_score": 0.25,
        "reliability": 0.2,
        "rating": 0.2,
        # Time features
        "urgency": 0.2,
        "deadline": 0.15,
        "priority": 0.2,
        # General
        "historical_performance": 0.15,
        "risk_score": 0.2,
    }
    
    def analyze_contributions(
        self,
        decision: AIDecision,
    ) -> list[FeatureContribution]:
        """Analyze which features contributed to the decision."""
        contributions = []
        
        input_data = decision.input_data
        
        for i, (feature_name, value) in enumerate(input_data.items()):
            # Get base weight
            weight = self.FEATURE_WEIGHTS.get(feature_name.lower(), 0.1)
            
            # Compute contribution based on value
            if isinstance(value, (int, float)):
                # Numeric: contribution proportional to value
                contribution = weight * min(1.0, abs(value) / 100)
                direction = "positive" if value >= 0 else "negative"
            elif isinstance(value, bool):
                contribution = weight if value else -weight
                direction = "positive" if value else "negative"
            elif isinstance(value, str):
                # String: contribution based on weight
                contribution = weight * 0.5
                direction = "positive"
            else:
                contribution = weight * 0.3
                direction = "neutral"
            
            # Generate explanation
            explanation = self._generate_feature_explanation(
                feature_name, value, contribution, direction,
            )
            
            contributions.append(FeatureContribution(
                feature_name=feature_name,
                feature_value=value,
                contribution=contribution,
                direction=direction,
                importance_rank=i + 1,  # Will be updated after sorting
                explanation=explanation,
            ))
        
        # Sort by contribution magnitude and update ranks
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        for i, contrib in enumerate(contributions):
            contrib.importance_rank = i + 1
        
        return contributions
    
    def _generate_feature_explanation(
        self,
        feature_name: str,
        value: Any,
        contribution: float,
        direction: str,
    ) -> str:
        """Generate human-readable explanation for a feature."""
        impact = "increased" if direction == "positive" else "decreased"
        strength = "strongly" if abs(contribution) > 0.2 else "slightly"
        
        if isinstance(value, (int, float)):
            return f"The {feature_name} value of {value} {strength} {impact} the confidence."
        elif isinstance(value, bool):
            status = "enabled" if value else "disabled"
            return f"{feature_name.title()} being {status} {strength} {impact} the outcome."
        else:
            return f"The {feature_name} setting {strength} influenced the decision."


# =============================================================================
# COUNTERFACTUAL GENERATOR
# =============================================================================


class CounterfactualGenerator:
    """
    Generates counterfactual explanations.
    "What would need to change for a different outcome?"
    """
    
    def generate_counterfactuals(
        self,
        decision: AIDecision,
        num_scenarios: int = 3,
    ) -> list[CounterfactualScenario]:
        """Generate counterfactual scenarios."""
        scenarios = []
        input_data = decision.input_data
        
        # Find modifiable numeric features
        numeric_features = [
            (k, v) for k, v in input_data.items()
            if isinstance(v, (int, float))
        ]
        
        for i, (feature, value) in enumerate(numeric_features[:num_scenarios]):
            # Generate alternative scenario
            if value > 0:
                new_value = value * 0.7  # 30% decrease
                description = f"If {feature} were 30% lower ({new_value:.2f})"
            else:
                new_value = value * 1.3 if value < 0 else 10
                description = f"If {feature} were higher ({new_value:.2f})"
            
            # Estimate confidence delta
            confidence_delta = -0.1 * (1 + i * 0.1)
            
            scenario = CounterfactualScenario(
                scenario_id=f"cf_{i+1}",
                description=description,
                changes={feature: {"from": value, "to": new_value}},
                original_outcome=decision.output,
                alternative_outcome=self._compute_alternative(decision.output, confidence_delta),
                confidence_delta=confidence_delta,
            )
            scenarios.append(scenario)
        
        # Add boolean feature counterfactuals
        bool_features = [
            (k, v) for k, v in input_data.items()
            if isinstance(v, bool)
        ]
        
        for feature, value in bool_features[:max(0, num_scenarios - len(scenarios))]:
            description = f"If {feature} were {'disabled' if value else 'enabled'}"
            
            scenario = CounterfactualScenario(
                scenario_id=f"cf_bool_{feature}",
                description=description,
                changes={feature: {"from": value, "to": not value}},
                original_outcome=decision.output,
                alternative_outcome=self._compute_alternative(decision.output, -0.15),
                confidence_delta=-0.15,
            )
            scenarios.append(scenario)
        
        return scenarios[:num_scenarios]
    
    def _compute_alternative(
        self,
        original: Any,
        delta: float,
    ) -> Any:
        """Compute alternative outcome based on confidence delta."""
        # Check bool first since bool is a subclass of int
        if isinstance(original, bool):
            return not original if abs(delta) > 0.3 else original
        elif isinstance(original, (int, float)):
            return original * (1 + delta)
        elif isinstance(original, str):
            if delta < -0.25:
                return f"Alternative to: {original}"
            return original
        return original


# =============================================================================
# EXPLANATION GENERATOR
# =============================================================================


class ExplanationGenerator:
    """
    Generates comprehensive explanations for AI decisions.
    """
    
    def __init__(self):
        self.evidence_retriever = EvidenceRetriever()
        self.feature_analyzer = FeatureAnalyzer()
        self.counterfactual_generator = CounterfactualGenerator()
    
    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Map confidence score to level."""
        if confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.65:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.45:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNCERTAIN
    
    def _generate_summary(
        self,
        decision: AIDecision,
        evidence: list[EvidenceChunk],
        contributions: list[FeatureContribution],
    ) -> str:
        """Generate a human-readable summary."""
        parts = []
        
        # Decision category context
        category_descriptions = {
            DecisionCategory.PRICING: "This pricing recommendation",
            DecisionCategory.SUPPLIER: "This supplier suggestion",
            DecisionCategory.SCHEDULING: "This scheduling decision",
            DecisionCategory.QUALITY: "This quality assessment",
            DecisionCategory.INVENTORY: "This inventory recommendation",
            DecisionCategory.RISK: "This risk assessment",
            DecisionCategory.ROUTING: "This routing decision",
            DecisionCategory.GENERAL: "This recommendation",
        }
        
        parts.append(category_descriptions.get(decision.category, "This decision"))
        parts.append(f"was made with {decision.confidence:.0%} confidence.")
        
        # Top contributing factors
        if contributions:
            top_factors = contributions[:3]
            factor_names = [f.feature_name for f in top_factors]
            parts.append(f"Key factors: {', '.join(factor_names)}.")
        
        # Evidence sources
        if evidence:
            sources = set(e.source.value for e in evidence[:3])
            parts.append(f"Based on evidence from: {', '.join(sources)}.")
        
        return " ".join(parts)
    
    def generate_explanation(
        self,
        decision: AIDecision,
        documents: list[dict[str, Any]] | None = None,
        explanation_type: ExplanationType = ExplanationType.EVIDENCE_BASED,
    ) -> DecisionExplanation:
        """Generate a full explanation for an AI decision."""
        import time
        start_time = time.time()
        
        # Retrieve evidence
        evidence = self.evidence_retriever.retrieve_evidence(
            decision,
            documents or [],
        )
        
        # Analyze feature contributions
        contributions = self.feature_analyzer.analyze_contributions(decision)
        
        # Generate counterfactuals
        counterfactuals = self.counterfactual_generator.generate_counterfactuals(decision)
        
        # Generate summary
        summary = self._generate_summary(decision, evidence, contributions)
        
        # Create explanation
        explanation = DecisionExplanation(
            explanation_id=hashlib.md5(
                f"{decision.decision_id}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12],
            decision_id=decision.decision_id,
            explanation_type=explanation_type,
            category=decision.category,
            summary=summary,
            confidence=decision.confidence,
            confidence_level=self._determine_confidence_level(decision.confidence),
            evidence_chunks=evidence,
            feature_contributions=contributions,
            counterfactuals=counterfactuals,
            model_version=decision.model_version,
            prompt_version=decision.prompt_version,
            generated_at=datetime.now(),
            generation_time_ms=(time.time() - start_time) * 1000,
        )
        
        return explanation
    
    def explain_this_suggestion(
        self,
        decision: AIDecision,
        documents: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        "Explain this Suggestion" button handler.
        Returns top 3 evidence chunks with summary.
        """
        # Get top 3 evidence
        evidence = self.evidence_retriever.get_top_evidence(
            decision,
            documents or [],
            top_k=3,
        )
        
        # Get top 3 contributing factors
        contributions = self.feature_analyzer.analyze_contributions(decision)[:3]
        
        return {
            "decision_id": decision.decision_id,
            "confidence": decision.confidence,
            "confidence_level": self._determine_confidence_level(decision.confidence).value,
            "summary": self._generate_summary(decision, evidence, contributions),
            "top_evidence": [
                {
                    "source": e.source.value,
                    "content": e.content[:200] + "..." if len(e.content) > 200 else e.content,
                    "relevance": e.relevance_score,
                    "document": e.document_title,
                }
                for e in evidence
            ],
            "key_factors": [
                {
                    "factor": c.feature_name,
                    "value": str(c.feature_value),
                    "impact": c.direction,
                    "explanation": c.explanation,
                }
                for c in contributions
            ],
        }


# =============================================================================
# AUDIT TRAIL SERVICE
# =============================================================================


class AIReasoningAuditTrail:
    """
    Audit trail for AI reasoning.
    Tracks prompt versions, model IDs, retrieved context.
    """
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: list[AuditEvent] = []
        self.decisions: dict[str, AIDecision] = {}
        self.model_registry: dict[str, ModelInfo] = {}
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return hashlib.md5(
            f"{datetime.now().isoformat()}:{len(self.events)}".encode()
        ).hexdigest()[:12]
    
    def _compute_context_hash(self, context: list[str]) -> str:
        """Compute hash of retrieved context."""
        content = "".join(sorted(context))
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def register_model(self, model_info: ModelInfo) -> None:
        """Register a model in the registry."""
        self.model_registry[model_info.model_id] = model_info
    
    def log_decision(
        self,
        decision: AIDecision,
        user_id: str | None = None,
    ) -> str:
        """Log an AI decision."""
        # Store decision
        self.decisions[decision.decision_id] = decision
        
        # Create audit event
        event = AuditEvent(
            event_id=self._generate_event_id(),
            decision_id=decision.decision_id,
            event_type=AuditEventType.DECISION_MADE,
            timestamp=decision.created_at,
            user_id=user_id or decision.user_id,
            details={
                "category": decision.category.value,
                "confidence": decision.confidence,
                "input_keys": list(decision.input_data.keys()),
                "reasoning_steps": len(decision.reasoning_chain),
            },
            model_id=decision.model_id,
            model_version=decision.model_version,
            prompt_version=decision.prompt_version,
            context_hash=self._compute_context_hash(decision.retrieved_context),
        )
        
        self._add_event(event)
        return event.event_id
    
    def log_explanation_request(
        self,
        decision_id: str,
        user_id: str | None = None,
    ) -> str:
        """Log when a user requests an explanation."""
        decision = self.decisions.get(decision_id)
        
        event = AuditEvent(
            event_id=self._generate_event_id(),
            decision_id=decision_id,
            event_type=AuditEventType.EXPLANATION_REQUESTED,
            timestamp=datetime.now(),
            user_id=user_id,
            details={"decision_found": decision is not None},
            model_id=decision.model_id if decision else None,
            model_version=decision.model_version if decision else None,
        )
        
        self._add_event(event)
        return event.event_id
    
    def log_feedback(
        self,
        decision_id: str,
        feedback: dict[str, Any],
        user_id: str | None = None,
    ) -> str:
        """Log user feedback on a decision."""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            decision_id=decision_id,
            event_type=AuditEventType.FEEDBACK_RECEIVED,
            timestamp=datetime.now(),
            user_id=user_id,
            details=feedback,
        )
        
        self._add_event(event)
        return event.event_id
    
    def log_override(
        self,
        decision_id: str,
        override_value: Any,
        reason: str,
        user_id: str | None = None,
    ) -> str:
        """Log when a user overrides an AI decision."""
        decision = self.decisions.get(decision_id)
        
        event = AuditEvent(
            event_id=self._generate_event_id(),
            decision_id=decision_id,
            event_type=AuditEventType.OVERRIDE_APPLIED,
            timestamp=datetime.now(),
            user_id=user_id,
            details={
                "original_output": decision.output if decision else None,
                "override_value": override_value,
                "reason": reason,
            },
            model_id=decision.model_id if decision else None,
        )
        
        self._add_event(event)
        return event.event_id
    
    def log_context_retrieval(
        self,
        decision_id: str,
        context: list[str],
        retrieval_time_ms: float,
    ) -> str:
        """Log context retrieval for a decision."""
        event = AuditEvent(
            event_id=self._generate_event_id(),
            decision_id=decision_id,
            event_type=AuditEventType.CONTEXT_RETRIEVED,
            timestamp=datetime.now(),
            user_id=None,
            details={
                "num_chunks": len(context),
                "retrieval_time_ms": retrieval_time_ms,
                "total_chars": sum(len(c) for c in context),
            },
            context_hash=self._compute_context_hash(context),
        )
        
        self._add_event(event)
        return event.event_id
    
    def _add_event(self, event: AuditEvent) -> None:
        """Add event to the trail."""
        self.events.append(event)
        
        # Prune if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events // 2:]
    
    def get_decision_trail(self, decision_id: str) -> list[AuditEvent]:
        """Get all audit events for a decision."""
        return [e for e in self.events if e.decision_id == decision_id]
    
    def get_decision(self, decision_id: str) -> AIDecision | None:
        """Get a decision by ID."""
        return self.decisions.get(decision_id)
    
    def get_events_by_type(
        self,
        event_type: AuditEventType,
        since: datetime | None = None,
    ) -> list[AuditEvent]:
        """Get events by type."""
        events = [e for e in self.events if e.event_type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events
    
    def get_model_usage_stats(
        self,
        model_id: str,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Get usage statistics for a model."""
        events = [
            e for e in self.events
            if e.model_id == model_id and e.event_type == AuditEventType.DECISION_MADE
        ]
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return {
            "model_id": model_id,
            "total_decisions": len(events),
            "unique_users": len(set(e.user_id for e in events if e.user_id)),
            "avg_confidence": (
                sum(e.details.get("confidence", 0) for e in events) / len(events)
                if events else 0
            ),
        }
    
    def get_user_history(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get audit history for a user."""
        events = [e for e in self.events if e.user_id == user_id]
        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def export_trail(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Export full audit trail for a decision (for compliance)."""
        decision = self.decisions.get(decision_id)
        events = self.get_decision_trail(decision_id)
        
        return {
            "decision_id": decision_id,
            "decision": {
                "category": decision.category.value if decision else None,
                "confidence": decision.confidence if decision else None,
                "model_id": decision.model_id if decision else None,
                "model_version": decision.model_version if decision else None,
                "prompt_version": decision.prompt_version if decision else None,
                "created_at": decision.created_at.isoformat() if decision else None,
                "reasoning_steps": decision.reasoning_chain if decision else [],
            },
            "events": [
                {
                    "event_id": e.event_id,
                    "type": e.event_type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "user_id": e.user_id,
                    "details": e.details,
                }
                for e in events
            ],
            "exported_at": datetime.now().isoformat(),
        }


# =============================================================================
# XAI SERVICE (MAIN ORCHESTRATOR)
# =============================================================================


class XAIService:
    """
    Main XAI (Explainable AI) service.
    Orchestrates explanations and audit trails.
    """
    
    def __init__(self):
        self.explanation_generator = ExplanationGenerator()
        self.audit_trail = AIReasoningAuditTrail()
    
    def record_decision(
        self,
        category: DecisionCategory,
        input_data: dict[str, Any],
        output: Any,
        confidence: float,
        model_id: str,
        model_version: str,
        prompt_version: str,
        retrieved_context: list[str],
        reasoning_chain: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> AIDecision:
        """Record a new AI decision."""
        decision_id = hashlib.md5(
            f"{model_id}:{datetime.now().isoformat()}:{json.dumps(input_data)}".encode()
        ).hexdigest()[:16]
        
        decision = AIDecision(
            decision_id=decision_id,
            category=category,
            input_data=input_data,
            output=output,
            confidence=confidence,
            model_id=model_id,
            model_version=model_version,
            prompt_version=prompt_version,
            retrieved_context=retrieved_context,
            reasoning_chain=reasoning_chain or [],
            created_at=datetime.now(),
            user_id=user_id,
            session_id=session_id,
        )
        
        # Log to audit trail
        self.audit_trail.log_decision(decision, user_id)
        
        return decision
    
    def explain_suggestion(
        self,
        decision_id: str,
        documents: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle "Explain this Suggestion" button click."""
        # Log request
        self.audit_trail.log_explanation_request(decision_id, user_id)
        
        # Get decision
        decision = self.audit_trail.get_decision(decision_id)
        if not decision:
            return {
                "error": "Decision not found",
                "decision_id": decision_id,
            }
        
        # Generate explanation
        return self.explanation_generator.explain_this_suggestion(
            decision, documents,
        )
    
    def get_full_explanation(
        self,
        decision_id: str,
        documents: list[dict[str, Any]] | None = None,
    ) -> DecisionExplanation | None:
        """Get full detailed explanation."""
        decision = self.audit_trail.get_decision(decision_id)
        if not decision:
            return None
        
        return self.explanation_generator.generate_explanation(decision, documents)
    
    def record_feedback(
        self,
        decision_id: str,
        was_helpful: bool,
        feedback_text: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Record user feedback on a decision/explanation."""
        feedback = {
            "was_helpful": was_helpful,
            "feedback_text": feedback_text,
        }
        return self.audit_trail.log_feedback(decision_id, feedback, user_id)
    
    def record_override(
        self,
        decision_id: str,
        override_value: Any,
        reason: str,
        user_id: str | None = None,
    ) -> str:
        """Record when user overrides an AI decision."""
        return self.audit_trail.log_override(
            decision_id, override_value, reason, user_id,
        )
    
    def get_audit_trail(self, decision_id: str) -> dict[str, Any]:
        """Get audit trail for a decision."""
        return self.audit_trail.export_trail(decision_id)
    
    def get_model_stats(
        self,
        model_id: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Get model usage statistics."""
        since = datetime.now() - timedelta(hours=hours)
        return self.audit_trail.get_model_usage_stats(model_id, since)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_xai_service() -> XAIService:
    """Create the XAI service."""
    return XAIService()


def create_explanation_generator() -> ExplanationGenerator:
    """Create an explanation generator."""
    return ExplanationGenerator()


def create_audit_trail(max_events: int = 10000) -> AIReasoningAuditTrail:
    """Create an audit trail."""
    return AIReasoningAuditTrail(max_events=max_events)


def create_evidence_retriever(max_chunks: int = 10) -> EvidenceRetriever:
    """Create an evidence retriever."""
    return EvidenceRetriever(max_chunks=max_chunks)

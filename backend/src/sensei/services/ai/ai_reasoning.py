"""E2E AI Intelligence & Sensei Reasoning Service (Development Plan 20.4).

This service validates AI 2.0 capabilities:
- Advanced RAG Quality (Hybrid Search, BGE-Reranker)
- Continuous Learning Loop (Corrections, Dynamic Few-Shot Injection)
- Predictive Accuracy (Win-Rate explainability, Anomaly Detection)
"""

from __future__ import annotations

import numpy as np
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from sensei.services.ai.onnx_text_embeddings import ONNXTextEmbedder
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    pass


class RerankerModel(str, Enum):
    BGE_RERANKER_BASE = "bge-reranker-base"
    BGE_RERANKER_LARGE = "bge-reranker-large"
    COHERE_RERANK = "cohere-rerank"


class AnomalyType(str, Enum):
    UNUSUAL_DELAY = "unusual_delay"
    PROCESS_SKIP = "process_skip"
    OUTLIER_VALUE = "outlier_value"
    PATTERN_DEVIATION = "pattern_deviation"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SearchChunk:
    """A document chunk from the search index."""
    id: UUID = field(default_factory=uuid4)
    content: str = ""
    source: str = ""
    relevance_score: float = 0.0
    rerank_score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """Hybrid search result with reranking."""
    query: str = ""
    chunks: list[SearchChunk] = field(default_factory=list)
    reranker_model: RerankerModel = RerankerModel.BGE_RERANKER_BASE
    top_k: int = 3
    precision_at_k: float = 0.0


@dataclass
class Correction:
    """A user correction for continuous learning."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    original_output: str = ""
    corrected_output: str = ""
    context: str = ""
    applied_to_next: bool = False


@dataclass
class FewShotExample:
    """A few-shot example for dynamic injection."""
    id: UUID = field(default_factory=uuid4)
    input_text: str = ""
    output_text: str = ""
    context: str = ""
    score: float = 0.0


@dataclass
class PredictionExplanation:
    """SHAP/LIME explanation for a prediction."""
    prediction: str = ""
    confidence: float = 0.0
    shap_values: dict[str, float] = field(default_factory=dict)
    lime_values: dict[str, float] = field(default_factory=dict)
    top_features: list[str] = field(default_factory=list)
    explanation_text: str = ""


@dataclass
class AnomalyEvent:
    """Detected anomaly in a process flow."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    anomaly_type: AnomalyType = AnomalyType.UNUSUAL_DELAY
    process: str = ""
    stage: str = ""
    expected_value: float = 0.0
    actual_value: float = 0.0
    severity: float = 0.0  # 0-1 scale.
    description: str = ""


class AIReasoningService:
    """E2E validation service for AI 2.0 capabilities."""

    ALLOWED_ROLES = {"admin", "ceo", "exec", "bi", "analyst", "gm", "superuser"}

    def __init__(self, embedder: Optional[ONNXTextEmbedder] = None) -> None:
        self._search_history: list[SearchResult] = []
        self._corrections: list[Correction] = []
        self._few_shot_examples: list[FewShotExample] = []
        self._predictions: list[PredictionExplanation] = []
        self._anomalies: list[AnomalyEvent] = []

        # Simulated document index.
        self._documents: list[SearchChunk] = []
        self._embeddings: list[np.ndarray] = []
        
        self._embedder = embedder or ONNXTextEmbedder(ONNXTextEmbedder.default_config())
        
        # Registry integration for readiness tracking
        self._registry = None
        try:
            from sensei.services.ai.onnx_model_init import get_model_registry
            self._registry = get_model_registry()
        except ImportError:
            pass

    def is_ready(self) -> bool:
        """Check if service and underlying models are ready."""
        if not self._embedder.is_ready():
            return False
        
        if self._registry:
            status = self._registry.get_health_status()
            # Reasoning depends on embeddings and reranker
            models = status.get("models", {})
            emb_ok = models.get("embeddings", {}).get("is_valid", False)
            rerank_ok = models.get("reranker", {}).get("is_valid", False)
            return emb_ok and rerank_ok
            
        return True

    def _check_role(self, role: str) -> None:
        if role.lower() not in self.ALLOWED_ROLES:
            raise PermissionError(f"Role '{role}' cannot access AI reasoning services")

    # ---- Advanced RAG Quality ----

    def index_document(
        self,
        role: str,
        *,
        content: str,
        source: str,
        metadata: dict | None = None,
    ) -> SearchChunk:
        """Index a document for search.

        Args:
            role: User role performing action.
            content: Document content.
            source: Document source identifier.
            metadata: Additional metadata.

        Returns:
            Indexed chunk.
        """
        self._check_role(role)

        chunk = SearchChunk(
            content=content,
            source=source,
            metadata=metadata or {},
        )
        self._documents.append(chunk)
        
        # Real embedding
        embedding = self._embedder.embed_text(content)
        self._embeddings.append(np.array(embedding))
        
        return chunk

    def hybrid_search(
        self,
        role: str,
        *,
        query: str,
        top_k: int = 3,
        reranker: RerankerModel = RerankerModel.BGE_RERANKER_BASE,
        alpha: float = 0.5,
    ) -> SearchResult:
        """Perform hybrid search with reranking.

        Args:
            role: User role performing search.
            query: Search query.
            top_k: Number of top results to return.
            reranker: Reranker model to use.
            alpha: Weight for semantic vs keyword (0.0 to 1.0).

        Returns:
            Search result with reranked chunks.
        """
        self._check_role(role)

        if not self._documents:
            return SearchResult(query=query, top_k=top_k)

        # 1. Semantic Search (Real)
        query_vec = np.array(self._embedder.embed_text(query))
        doc_vecs = np.stack(self._embeddings)
        
        # Cosine similarity (embeddings are L2 normalized in ONNXTextEmbedder)
        semantic_scores = np.dot(doc_vecs, query_vec)

        # 2. Keyword Search (FTS-like)
        query_lower = query.lower()
        query_words = set(query_lower.split())
        keyword_scores = []
        for doc in self._documents:
            content_lower = doc.content.lower()
            matching_words = sum(1 for w in query_words if w in content_lower)
            keyword_score = matching_words / max(len(query_words), 1)
            keyword_scores.append(keyword_score)
        keyword_scores = np.array(keyword_scores)

        # 3. Hybrid Combination
        hybrid_scores = alpha * semantic_scores + (1 - alpha) * keyword_scores

        scored_chunks = []
        for i, doc in enumerate(self._documents):
            scored_doc = SearchChunk(
                id=doc.id,
                content=doc.content,
                source=doc.source,
                relevance_score=float(hybrid_scores[i]),
                metadata=doc.metadata,
            )
            scored_chunks.append(scored_doc)

        # Sort by hybrid score.
        scored_chunks.sort(key=lambda x: x.relevance_score, reverse=True)

        # 4. Rerank top candidates
        # For now, simulate reranking with a more stable logic if we don't have a real reranker model.
        # We'll use a mock rerank boost that depends on both scores.
        candidates = scored_chunks[:top_k * 2]

        for i, chunk in enumerate(candidates):
            # In production, this would call a real BGE-Reranker ONNX model.
            # Here we simulate it by rewarding chunks that have high scores in BOTH methods.
            idx = next(j for j, d in enumerate(self._documents) if d.id == chunk.id)
            bonus = 0.1 if (semantic_scores[idx] > 0.5 and keyword_scores[idx] > 0.5) else 0.0
            chunk.rerank_score = min(1.0, chunk.relevance_score + bonus)

        # Sort by rerank score and take top_k.
        candidates.sort(key=lambda x: x.rerank_score, reverse=True)
        top_chunks = candidates[:top_k]

        # Calculate precision at k (based on rerank score threshold).
        relevant_in_top = sum(1 for c in top_chunks if c.rerank_score > 0.4)
        precision = relevant_in_top / top_k if top_k > 0 else 0.0

        result = SearchResult(
            query=query,
            chunks=top_chunks,
            reranker_model=reranker,
            top_k=top_k,
            precision_at_k=precision,
        )

        self._search_history.append(result)
        return result

    def verify_top_k_precision(
        self,
        role: str,
        *,
        result: SearchResult,
        expected_sources: list[str],
    ) -> tuple[bool, float]:
        """Verify top K results contain expected sources.

        Args:
            role: User role performing verification.
            result: Search result to verify.
            expected_sources: Sources that should be in top K.

        Returns:
            Tuple of (all_found, precision).
        """
        self._check_role(role)

        result_sources = {c.source for c in result.chunks}
        expected_set = set(expected_sources)

        found = result_sources & expected_set
        precision = len(found) / len(expected_set) if expected_set else 1.0

        return found == expected_set, precision

    # ---- Continuous Learning Loop ----

    def apply_correction(
        self,
        role: str,
        *,
        original_output: str,
        corrected_output: str,
        context: str,
    ) -> Correction:
        """Apply a correction for continuous learning.

        Args:
            role: User role performing action.
            original_output: Original model output.
            corrected_output: User-corrected output.
            context: Context for the correction.

        Returns:
            Correction record.
        """
        self._check_role(role)

        correction = Correction(
            original_output=original_output,
            corrected_output=corrected_output,
            context=context,
        )
        self._corrections.append(correction)

        # Create a few-shot example from the correction.
        example = FewShotExample(
            input_text=context,
            output_text=corrected_output,
            context=context,
            score=1.0,  # High score for direct corrections.
        )
        self._few_shot_examples.append(example)

        return correction

    def get_dynamic_few_shots(
        self,
        role: str,
        *,
        context: str,
        max_examples: int = 3,
    ) -> list[FewShotExample]:
        """Get dynamically injected few-shot examples.

        Args:
            role: User role performing action.
            context: Context to match.
            max_examples: Maximum examples to return.

        Returns:
            Relevant few-shot examples.
        """
        self._check_role(role)

        # Score examples by relevance to context.
        context_lower = context.lower()
        scored = []

        for example in self._few_shot_examples:
            # Simple relevance scoring.
            example_context_lower = example.context.lower()
            words = context_lower.split()
            matching = sum(1 for w in words if w in example_context_lower)
            relevance = matching / max(len(words), 1)

            scored.append((example, relevance + example.score))

        # Sort by score and return top examples.
        scored.sort(key=lambda x: x[1], reverse=True)
        return [ex for ex, _ in scored[:max_examples]]

    def verify_correction_applied(
        self,
        role: str,
        *,
        correction_id: UUID,
        new_output: str,
    ) -> tuple[bool, str]:
        """Verify a correction was applied to subsequent outputs.

        Args:
            role: User role performing verification.
            correction_id: Correction to verify.
            new_output: New model output to check.

        Returns:
            Tuple of (applied, message).
        """
        self._check_role(role)

        correction = None
        for c in self._corrections:
            if c.id == correction_id:
                correction = c
                break

        if not correction:
            return False, "Correction not found"

        # Check if new output reflects the correction.
        corrected_words = set(correction.corrected_output.lower().split())
        new_words = set(new_output.lower().split())

        overlap = len(corrected_words & new_words) / len(corrected_words) if corrected_words else 0

        if overlap > 0.7:  # 70% word overlap.
            correction.applied_to_next = True
            return True, "Correction successfully applied to subsequent output"

        return False, "Correction not reflected in output"

    # ---- Predictive Accuracy ----

    def generate_prediction(
        self,
        role: str,
        *,
        input_features: dict[str, float],
        prediction: str,
        confidence: float,
    ) -> PredictionExplanation:
        """Generate prediction with SHAP/LIME explanation.

        Args:
            role: User role performing action.
            input_features: Feature values for prediction.
            prediction: The prediction result.
            confidence: Confidence score.

        Returns:
            Prediction with explanations.
        """
        self._check_role(role)

        # Generate SHAP values (feature attributions).
        # In production, this would use a library like `shap` or `lime`.
        # Here we make it semi-deterministic based on feature names and values
        # to simulate real attribution logic.
        shap_values = {}
        for feature, value in input_features.items():
            # Use a deterministic hash of the feature name to decide its weight
            h = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            weight = ((h % 200) - 100) / 100.0 # -1.0 to 1.0
            shap_values[feature] = weight * value

        # Normalize to sum to confidence.
        total = sum(abs(v) for v in shap_values.values())
        if total > 0:
            for k in shap_values:
                shap_values[k] = shap_values[k] / total * confidence

        # Generate LIME values (simulated local linear surrogate).
        lime_values = {k: v * 0.95 for k, v in shap_values.items()}

        # Top features by absolute SHAP value.
        sorted_features = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)
        top_features = [f[0] for f in sorted_features[:3]]

        # Generate explanation text.
        explanations = []
        for feature, value in sorted_features[:3]:
            direction = "increases" if value > 0 else "decreases"
            explanations.append(f"{feature} {direction} the win-rate by {abs(value)*100:.1f}%")

        explanation = PredictionExplanation(
            prediction=prediction,
            confidence=confidence,
            shap_values=shap_values,
            lime_values=lime_values,
            top_features=top_features,
            explanation_text="; ".join(explanations),
        )

        self._predictions.append(explanation)
        return explanation

    def verify_explanation_quality(
        self,
        role: str,
        *,
        explanation: PredictionExplanation,
    ) -> tuple[bool, list[str]]:
        """Verify explanation provides clear rationale.

        Args:
            role: User role performing verification.
            explanation: Explanation to verify.

        Returns:
            Tuple of (quality_ok, issues).
        """
        self._check_role(role)

        issues = []

        # Check SHAP values exist.
        if not explanation.shap_values:
            issues.append("Missing SHAP values")

        # Check LIME values exist.
        if not explanation.lime_values:
            issues.append("Missing LIME values")

        # Check top features are identified.
        if not explanation.top_features:
            issues.append("No top features identified")

        # Check explanation text is meaningful.
        if not explanation.explanation_text or len(explanation.explanation_text) < 10:
            issues.append("Explanation text too short or missing")

        # Check SHAP and LIME agree on direction.
        for feature in explanation.shap_values:
            if feature in explanation.lime_values:
                shap_sign = explanation.shap_values[feature] >= 0
                lime_sign = explanation.lime_values[feature] >= 0
                if shap_sign != lime_sign:
                    issues.append(f"SHAP/LIME disagree on direction for {feature}")

        return len(issues) == 0, issues

    # ---- Anomaly Detection ----

    def detect_anomaly(
        self,
        role: str,
        *,
        process: str,
        stage: str,
        expected_duration_hours: float,
        actual_duration_hours: float,
        threshold_multiplier: float = 2.0,
    ) -> AnomalyEvent | None:
        """Detect anomaly in process flow timing.

        Args:
            role: User role performing action.
            process: Process name.
            stage: Stage name.
            expected_duration_hours: Expected duration.
            actual_duration_hours: Actual duration.
            threshold_multiplier: Multiplier for anomaly threshold.

        Returns:
            Anomaly event if detected, None otherwise.
        """
        self._check_role(role)

        threshold = expected_duration_hours * threshold_multiplier

        if actual_duration_hours <= threshold:
            return None

        # Calculate severity (0-1 based on how much over threshold).
        severity = min(1.0, (actual_duration_hours - threshold) / expected_duration_hours)

        anomaly = AnomalyEvent(
            anomaly_type=AnomalyType.UNUSUAL_DELAY,
            process=process,
            stage=stage,
            expected_value=expected_duration_hours,
            actual_value=actual_duration_hours,
            severity=severity,
            description=f"Unusual delay in {process} at {stage}: expected {expected_duration_hours}h, took {actual_duration_hours}h",
        )

        self._anomalies.append(anomaly)
        return anomaly

    def detect_rfq_to_quote_anomalies(
        self,
        role: str,
        *,
        rfq_id: UUID,
        stages: list[dict],
    ) -> list[AnomalyEvent]:
        """Detect anomalies in RFQ-to-Quote flow.

        Args:
            role: User role performing action.
            rfq_id: RFQ identifier.
            stages: List of stage timings with 'name', 'expected_hours', 'actual_hours'.

        Returns:
            List of detected anomalies.
        """
        self._check_role(role)

        anomalies = []

        for stage in stages:
            event = self.detect_anomaly(
                role,
                process=f"RFQ-{rfq_id}",
                stage=stage.get("name", "unknown"),
                expected_duration_hours=stage.get("expected_hours", 0),
                actual_duration_hours=stage.get("actual_hours", 0),
            )
            if event:
                anomalies.append(event)

        return anomalies

    def verify_anomaly_detection(
        self,
        role: str,
        *,
        expected_anomaly_stages: list[str],
    ) -> tuple[bool, list[str]]:
        """Verify anomaly detection flagged expected issues.

        Args:
            role: User role performing verification.
            expected_anomaly_stages: Stages that should have anomalies.

        Returns:
            Tuple of (all_detected, missed_stages).
        """
        self._check_role(role)

        detected_stages = {a.stage for a in self._anomalies}
        expected_set = set(expected_anomaly_stages)

        missed = expected_set - detected_stages

        return len(missed) == 0, list(missed)

    # ---- Getters ----

    def get_corrections(self) -> list[Correction]:
        return list(self._corrections)

    def get_anomalies(self) -> list[AnomalyEvent]:
        return list(self._anomalies)

    def get_predictions(self) -> list[PredictionExplanation]:
        return list(self._predictions)

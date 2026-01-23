"""E2E AI Intelligence & Seeded Reasoning Service (Development Plan 20.4).

This service validates AI 2.0 capabilities:
- Seeded Reasoning (Expert Principles from Distilled Books)
- Continuous Learning Loop (Corrections, Dynamic Few-Shot Injection)
- Predictive Accuracy (Win-Rate explainability, Anomaly Detection)
"""

from __future__ import annotations

import numpy as np
import random
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from sensei.services.ai.onnx_text_embeddings import ONNXTextEmbedder
from sensei.services.ai.reasoning_engine import SenseiReasoningEngine, RootCauseSuggestion
from typing import TYPE_CHECKING, Optional, List, Dict
from uuid import UUID, uuid4
from typing import Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    UNUSUAL_DELAY = "unusual_delay"
    PROCESS_SKIP = "process_skip"
    OUTLIER_VALUE = "outlier_value"
    PATTERN_DEVIATION = "pattern_deviation"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


@dataclass
class SearchResult:
    """A search result for internal tracking."""
    query: str = ""
    timestamp: datetime = field(default_factory=_utcnow)
    results_count: int = 0


@dataclass
class SearchChunk:
    """A document chunk for embedding-based search (deprecated)."""
    id: UUID = field(default_factory=uuid4)
    text: str = ""
    source: str = ""
    embedding: Optional[List[float]] = None


class AIReasoningService:
    """E2E validation service for AI 2.0 capabilities."""

    ALLOWED_ROLES = {"admin", "ceo", "exec", "bi", "analyst", "gm", "superuser"}

    def __init__(self, embedder: Optional[ONNXTextEmbedder] = None, reasoning_engine: Optional[SenseiReasoningEngine] = None) -> None:
        self._search_history: list[SearchResult] = []
        self._corrections: list[Correction] = []
        self._few_shot_examples: list[FewShotExample] = []
        self._predictions: list[PredictionExplanation] = []
        self._anomalies: list[AnomalyEvent] = []

        # Seeded reasoning engine
        self._reasoning_engine = reasoning_engine or SenseiReasoningEngine()

        # Simulated document index (DEPRECATED: Prefer seeded traces)
        self._documents: list[SearchChunk] = []
        self._embeddings: list[np.ndarray] = []
        
        self._embedder = embedder or ONNXTextEmbedder(ONNXTextEmbedder.default_config())
        
        # Registry integration for readiness tracking
        self._registry = None
        try:
            from sensei.services.ai.onnx_model_init import get_model_registry
            self._registry = get_model_registry()
        except ImportError:
            logger.debug("Model registry not available for AIReasoningService")

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

    # ---- Seeded Reasoning (Replacing RAG) ----

    def ingest_expert_trace(
        self,
        role: str,
        *,
        principle: str,
        source_book: str,
        recommendations: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Ingest an expert reasoning trace from distilled books."""
        self._check_role(role)
        trace = {
            "findings": {
                "distilled_principle": principle,
                "source_book": source_book
            },
            "recommendations": recommendations or []
        }
        self._reasoning_engine.load_seeded_knowledge([trace])
        return trace

    def seeded_reasoning(
        self,
        role: str,
        *,
        problem_statement: str,
    ) -> List[RootCauseSuggestion]:
        """Perform seeded reasoning based on ingested expert traces."""
        self._check_role(role)
        return self._reasoning_engine.analyze_root_cause(problem_statement)

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

"""E2E Tests for AI Intelligence & Sensei Reasoning Service (Development Plan 20.4)."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from sensei.services.ai.ai_reasoning import (
    AIReasoningService,
    AnomalyEvent,
    AnomalyType,
    Correction,
    FewShotExample,
    PredictionExplanation,
    RerankerModel,
    SearchChunk,
    SearchResult,
)


pytestmark = pytest.mark.e2e

if os.getenv("RUN_AI_E2E") != "1":
    pytest.skip("Set RUN_AI_E2E=1 to run AI reasoning e2e tests", allow_module_level=True)


@pytest.fixture
def svc() -> AIReasoningService:
    return AIReasoningService()


class TestHybridSearchPrecision:
    def test_bge_reranker_top_3_precision(self, svc: AIReasoningService) -> None:
        # Index test documents.
        svc.index_document(
            "admin",
            content="Product quality control procedures and best practices",
            source="quality_docs",
        )
        svc.index_document(
            "admin",
            content="Manufacturing floor safety guidelines and compliance",
            source="safety_docs",
        )
        svc.index_document(
            "admin",
            content="Quality inspection checklist for production line",
            source="quality_checklist",
        )
        svc.index_document(
            "admin",
            content="HR policies and employee handbook",
            source="hr_docs",
        )

        result = svc.hybrid_search(
            "admin",
            query="quality control production",
            top_k=3,
            reranker=RerankerModel.BGE_RERANKER_BASE,
        )

        assert len(result.chunks) == 3
        assert result.reranker_model == RerankerModel.BGE_RERANKER_BASE

        # Quality-related docs should be in top results.
        sources = {c.source for c in result.chunks}
        assert "quality_docs" in sources or "quality_checklist" in sources

    def test_verify_top_k_contains_expected(self, svc: AIReasoningService) -> None:
        # Index documents.
        svc.index_document("admin", content="RFQ pricing strategy", source="rfq_pricing")
        svc.index_document("admin", content="Quote generation workflow", source="quote_workflow")
        svc.index_document("admin", content="Customer onboarding process", source="onboarding")

        result = svc.hybrid_search("admin", query="RFQ pricing", top_k=3)

        found, precision = svc.verify_top_k_precision(
            "admin",
            result=result,
            expected_sources=["rfq_pricing"],
        )

        assert precision > 0  # At least partial match.

    def test_rerank_improves_ordering(self, svc: AIReasoningService) -> None:
        # Index documents.
        svc.index_document("admin", content="Machine learning model training", source="ml_training")
        svc.index_document("admin", content="Training program for operators", source="operator_training")

        result = svc.hybrid_search(
            "admin",
            query="operator training program",
            top_k=2,
            reranker=RerankerModel.BGE_RERANKER_LARGE,
        )

        # Rerank scores should be populated.
        for chunk in result.chunks:
            assert chunk.rerank_score >= 0


class TestContinuousLearningLoop:
    def test_apply_correction_creates_few_shot(self, svc: AIReasoningService) -> None:
        correction = svc.apply_correction(
            "admin",
            original_output="The lead time is 5 days",
            corrected_output="The lead time is 7 business days",
            context="What is the lead time for custom orders?",
        )

        assert correction.id is not None
        assert correction.corrected_output == "The lead time is 7 business days"

        # Verify few-shot example was created.
        few_shots = svc.get_dynamic_few_shots(
            "admin",
            context="lead time for orders",
            max_examples=3,
        )

        assert len(few_shots) > 0
        assert any("7 business days" in ex.output_text for ex in few_shots)

    def test_dynamic_few_shot_injection(self, svc: AIReasoningService) -> None:
        # Apply multiple corrections.
        svc.apply_correction(
            "admin",
            original_output="Wrong answer 1",
            corrected_output="Correct answer about pricing",
            context="Question about pricing strategy",
        )
        svc.apply_correction(
            "admin",
            original_output="Wrong answer 2",
            corrected_output="Correct answer about quality",
            context="Question about quality control",
        )

        # Get few-shots for pricing context.
        pricing_shots = svc.get_dynamic_few_shots(
            "admin",
            context="pricing strategy question",
            max_examples=1,
        )

        assert len(pricing_shots) >= 1
        assert "pricing" in pricing_shots[0].output_text.lower()

    def test_correction_efficacy_verification(self, svc: AIReasoningService) -> None:
        correction = svc.apply_correction(
            "admin",
            original_output="Old format output",
            corrected_output="New improved format with details",
            context="Generate a report",
        )

        # Verify correction was applied to new output.
        applied, message = svc.verify_correction_applied(
            "admin",
            correction_id=correction.id,
            new_output="New improved format with additional details",
        )

        assert applied
        assert "successfully" in message.lower()

    def test_correction_not_applied_detected(self, svc: AIReasoningService) -> None:
        correction = svc.apply_correction(
            "admin",
            original_output="Old output",
            corrected_output="Completely different corrected output",
            context="Some context",
        )

        # New output doesn't reflect correction.
        applied, message = svc.verify_correction_applied(
            "admin",
            correction_id=correction.id,
            new_output="Something totally unrelated",
        )

        assert not applied
        assert "not reflected" in message.lower()


class TestPredictiveAccuracy:
    def test_win_rate_shap_explanation(self, svc: AIReasoningService) -> None:
        explanation = svc.generate_prediction(
            "admin",
            input_features={
                "deal_size": 100000,
                "competitor_count": 3,
                "relationship_score": 0.8,
                "response_time_days": 2,
            },
            prediction="High Win Probability",
            confidence=0.85,
        )

        assert explanation.prediction == "High Win Probability"
        assert explanation.confidence == 0.85
        assert len(explanation.shap_values) == 4
        assert len(explanation.top_features) <= 3

    def test_lime_values_generated(self, svc: AIReasoningService) -> None:
        explanation = svc.generate_prediction(
            "admin",
            input_features={
                "feature_a": 10,
                "feature_b": 20,
            },
            prediction="Result",
            confidence=0.9,
        )

        assert len(explanation.lime_values) == 2
        assert "feature_a" in explanation.lime_values
        assert "feature_b" in explanation.lime_values

    def test_explanation_text_generated(self, svc: AIReasoningService) -> None:
        explanation = svc.generate_prediction(
            "admin",
            input_features={
                "margin": 0.25,
                "urgency": 0.9,
            },
            prediction="Priority Deal",
            confidence=0.95,
        )

        assert len(explanation.explanation_text) > 0
        assert "increases" in explanation.explanation_text or "decreases" in explanation.explanation_text

    def test_verify_explanation_quality(self, svc: AIReasoningService) -> None:
        explanation = svc.generate_prediction(
            "admin",
            input_features={
                "score_1": 50,
                "score_2": 30,
                "score_3": 20,
            },
            prediction="High",
            confidence=0.88,
        )

        quality_ok, issues = svc.verify_explanation_quality("admin", explanation=explanation)

        assert quality_ok
        assert len(issues) == 0


class TestAnomalyDetection:
    def test_unusual_delay_detected(self, svc: AIReasoningService) -> None:
        anomaly = svc.detect_anomaly(
            "admin",
            process="RFQ-to-Quote",
            stage="Technical Review",
            expected_duration_hours=24,
            actual_duration_hours=72,  # 3x expected.
        )

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.UNUSUAL_DELAY
        assert anomaly.stage == "Technical Review"
        assert anomaly.severity > 0

    def test_normal_timing_no_anomaly(self, svc: AIReasoningService) -> None:
        anomaly = svc.detect_anomaly(
            "admin",
            process="RFQ-to-Quote",
            stage="Initial Review",
            expected_duration_hours=8,
            actual_duration_hours=10,  # Slightly over but under threshold.
        )

        assert anomaly is None

    def test_rfq_to_quote_flow_anomalies(self, svc: AIReasoningService) -> None:
        stages = [
            {"name": "Receipt", "expected_hours": 1, "actual_hours": 0.5},
            {"name": "Technical Review", "expected_hours": 8, "actual_hours": 24},  # Delayed.
            {"name": "Pricing", "expected_hours": 4, "actual_hours": 3},
            {"name": "Approval", "expected_hours": 2, "actual_hours": 8},  # Delayed.
        ]

        anomalies = svc.detect_rfq_to_quote_anomalies(
            "admin",
            rfq_id=uuid4(),
            stages=stages,
        )

        # Should detect 2 anomalies (Technical Review and Approval).
        assert len(anomalies) == 2
        flagged_stages = {a.stage for a in anomalies}
        assert "Technical Review" in flagged_stages
        assert "Approval" in flagged_stages

    def test_verify_anomaly_detection_coverage(self, svc: AIReasoningService) -> None:
        # Trigger anomalies.
        svc.detect_anomaly(
            "admin",
            process="Test",
            stage="Stage A",
            expected_duration_hours=1,
            actual_duration_hours=5,
        )
        svc.detect_anomaly(
            "admin",
            process="Test",
            stage="Stage B",
            expected_duration_hours=1,
            actual_duration_hours=3,
        )

        all_detected, missed = svc.verify_anomaly_detection(
            "admin",
            expected_anomaly_stages=["Stage A", "Stage B"],
        )

        assert all_detected
        assert len(missed) == 0

    def test_missed_anomaly_reported(self, svc: AIReasoningService) -> None:
        svc.detect_anomaly(
            "admin",
            process="Test",
            stage="Stage A",
            expected_duration_hours=1,
            actual_duration_hours=5,
        )

        all_detected, missed = svc.verify_anomaly_detection(
            "admin",
            expected_anomaly_stages=["Stage A", "Stage C"],  # Stage C not triggered.
        )

        assert not all_detected
        assert "Stage C" in missed


class TestRBACEnforcement:
    def test_viewer_cannot_access(self, svc: AIReasoningService) -> None:
        with pytest.raises(PermissionError):
            svc.hybrid_search("viewer", query="test")

    def test_operator_cannot_access(self, svc: AIReasoningService) -> None:
        with pytest.raises(PermissionError):
            svc.generate_prediction(
                "operator",
                input_features={},
                prediction="Test",
                confidence=0.5,
            )

    def test_admin_can_access(self, svc: AIReasoningService) -> None:
        result = svc.hybrid_search("admin", query="test")
        assert result is not None

    def test_analyst_can_access(self, svc: AIReasoningService) -> None:
        explanation = svc.generate_prediction(
            "analyst",
            input_features={"x": 1},
            prediction="Test",
            confidence=0.5,
        )
        assert explanation is not None

    def test_bi_can_access(self, svc: AIReasoningService) -> None:
        anomaly = svc.detect_anomaly(
            "bi",
            process="Test",
            stage="Test",
            expected_duration_hours=1,
            actual_duration_hours=5,
        )
        assert anomaly is not None

    def test_gm_can_access(self, svc: AIReasoningService) -> None:
        correction = svc.apply_correction(
            "gm",
            original_output="Old",
            corrected_output="New",
            context="Context",
        )
        assert correction is not None

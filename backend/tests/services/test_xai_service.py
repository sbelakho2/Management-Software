"""
Tests for AI Decision Explainability (XAI) Service.

Tests "Explain this Suggestion" and Audit Trail functionality.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sensei.services.ai.xai_service import (
    # Enums
    ExplanationType,
    DecisionCategory,
    EvidenceSource,
    ConfidenceLevel,
    AuditEventType,
    # Data models
    EvidenceChunk,
    FeatureContribution,
    CounterfactualScenario,
    DecisionExplanation,
    AIDecision,
    AuditEvent,
    ReasoningStep,
    ModelInfo,
    # Classes
    EvidenceRetriever,
    FeatureAnalyzer,
    CounterfactualGenerator,
    ExplanationGenerator,
    AIReasoningAuditTrail,
    XAIService,
    # Factory functions
    create_xai_service,
    create_explanation_generator,
    create_audit_trail,
    create_evidence_retriever,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_decision() -> AIDecision:
    """Create a sample AI decision."""
    return AIDecision(
        decision_id="dec_001",
        category=DecisionCategory.PRICING,
        input_data={
            "price": 150.0,
            "quantity": 100,
            "margin": 0.25,
            "urgency": True,
            "customer": "ACME Corp",
        },
        output={"recommended_price": 187.50, "discount_allowed": 5.0},
        confidence=0.85,
        model_id="pricing_model_v2",
        model_version="2.1.0",
        prompt_version="pricing_v3",
        retrieved_context=[
            "Historical pricing for similar items ranged from $150-$200",
            "Customer ACME Corp has 95% payment reliability",
            "Current market demand is high",
        ],
        reasoning_chain=[
            "Analyzed input parameters",
            "Retrieved historical pricing data",
            "Applied margin calculation",
            "Considered customer reliability",
            "Generated recommendation",
        ],
        created_at=datetime.now(),
        user_id="user_123",
        session_id="sess_456",
    )


@pytest.fixture
def sample_documents() -> list[dict]:
    """Create sample documents for evidence retrieval."""
    return [
        {
            "id": "doc_001",
            "title": "Pricing Guidelines",
            "content": "Standard margin for price quotes is 25%. For quantities over 100, a 5% discount may be applied.",
            "page": 5,
            "metadata": {"type": "policy"},
        },
        {
            "id": "doc_002",
            "title": "Customer Profile: ACME",
            "content": "ACME Corp is a priority customer with excellent payment history. They typically order quantities of 50-200 units.",
            "page": 1,
            "metadata": {"type": "customer_profile"},
        },
        {
            "id": "doc_003",
            "title": "Market Analysis",
            "content": "Current market conditions show high demand for the product category. Competitors are pricing at $180-$195.",
            "page": 12,
            "metadata": {"type": "analysis"},
        },
    ]


@pytest.fixture
def xai_service() -> XAIService:
    """Create XAI service."""
    return create_xai_service()


@pytest.fixture
def audit_trail() -> AIReasoningAuditTrail:
    """Create audit trail."""
    return create_audit_trail()


@pytest.fixture
def explanation_generator() -> ExplanationGenerator:
    """Create explanation generator."""
    return create_explanation_generator()


@pytest.fixture
def evidence_retriever() -> EvidenceRetriever:
    """Create evidence retriever."""
    return create_evidence_retriever()


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_explanation_type_values(self):
        """Test ExplanationType enum values."""
        assert ExplanationType.FEATURE_IMPORTANCE == "feature_importance"
        assert ExplanationType.EVIDENCE_BASED == "evidence_based"
        assert ExplanationType.COUNTERFACTUAL == "counterfactual"
        assert ExplanationType.RULE_BASED == "rule_based"
        assert ExplanationType.CONFIDENCE_BREAKDOWN == "confidence_breakdown"
    
    def test_decision_category_values(self):
        """Test DecisionCategory enum values."""
        assert DecisionCategory.PRICING == "pricing"
        assert DecisionCategory.SUPPLIER == "supplier"
        assert DecisionCategory.SCHEDULING == "scheduling"
        assert DecisionCategory.QUALITY == "quality"
        assert DecisionCategory.INVENTORY == "inventory"
        assert DecisionCategory.RISK == "risk"
    
    def test_evidence_source_values(self):
        """Test EvidenceSource enum values."""
        assert EvidenceSource.DOCUMENT == "document"
        assert EvidenceSource.DATABASE == "database"
        assert EvidenceSource.HISTORICAL == "historical"
        assert EvidenceSource.RULE == "rule"
        assert EvidenceSource.MODEL == "model"
    
    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.UNCERTAIN == "uncertain"
    
    def test_audit_event_type_values(self):
        """Test AuditEventType enum values."""
        assert AuditEventType.DECISION_MADE == "decision_made"
        assert AuditEventType.EXPLANATION_REQUESTED == "explanation_requested"
        assert AuditEventType.FEEDBACK_RECEIVED == "feedback_received"
        assert AuditEventType.OVERRIDE_APPLIED == "override_applied"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data models."""
    
    def test_evidence_chunk_creation(self):
        """Test EvidenceChunk creation."""
        chunk = EvidenceChunk(
            chunk_id="chunk_001",
            source=EvidenceSource.DOCUMENT,
            content="Test content",
            relevance_score=0.85,
            document_id="doc_001",
            document_title="Test Doc",
            page_number=5,
        )
        assert chunk.chunk_id == "chunk_001"
        assert chunk.relevance_score == 0.85
        assert chunk.source == EvidenceSource.DOCUMENT
    
    def test_feature_contribution_creation(self):
        """Test FeatureContribution creation."""
        contrib = FeatureContribution(
            feature_name="price",
            feature_value=150.0,
            contribution=0.3,
            direction="positive",
            importance_rank=1,
            explanation="Price strongly influenced the decision.",
        )
        assert contrib.feature_name == "price"
        assert contrib.contribution == 0.3
        assert contrib.importance_rank == 1
    
    def test_counterfactual_scenario_creation(self):
        """Test CounterfactualScenario creation."""
        scenario = CounterfactualScenario(
            scenario_id="cf_001",
            description="If price were 30% lower",
            changes={"price": {"from": 150.0, "to": 105.0}},
            original_outcome=187.50,
            alternative_outcome=145.0,
            confidence_delta=-0.15,
        )
        assert scenario.scenario_id == "cf_001"
        assert scenario.confidence_delta == -0.15
    
    def test_ai_decision_creation(self, sample_decision):
        """Test AIDecision creation."""
        assert sample_decision.decision_id == "dec_001"
        assert sample_decision.category == DecisionCategory.PRICING
        assert sample_decision.confidence == 0.85
        assert len(sample_decision.reasoning_chain) == 5
    
    def test_audit_event_creation(self):
        """Test AuditEvent creation."""
        event = AuditEvent(
            event_id="evt_001",
            decision_id="dec_001",
            event_type=AuditEventType.DECISION_MADE,
            timestamp=datetime.now(),
            user_id="user_123",
            details={"confidence": 0.85},
            model_id="model_v1",
            model_version="1.0",
        )
        assert event.event_id == "evt_001"
        assert event.event_type == AuditEventType.DECISION_MADE
    
    def test_model_info_creation(self):
        """Test ModelInfo creation."""
        info = ModelInfo(
            model_id="model_001",
            model_name="Pricing Model",
            version="2.0",
            capabilities=["pricing", "discount"],
            last_updated=datetime.now(),
            performance_metrics={"accuracy": 0.92, "f1": 0.88},
        )
        assert info.model_id == "model_001"
        assert "pricing" in info.capabilities


# =============================================================================
# EVIDENCE RETRIEVER TESTS
# =============================================================================


class TestEvidenceRetriever:
    """Test EvidenceRetriever."""
    
    def test_retriever_creation(self, evidence_retriever):
        """Test retriever creation."""
        assert evidence_retriever.max_chunks == 10
    
    def test_retrieve_evidence(
        self, evidence_retriever, sample_decision, sample_documents
    ):
        """Test evidence retrieval."""
        evidence = evidence_retriever.retrieve_evidence(
            sample_decision, sample_documents,
        )
        
        assert len(evidence) > 0
        for chunk in evidence:
            assert isinstance(chunk, EvidenceChunk)
            assert chunk.relevance_score >= 0
    
    def test_retrieve_evidence_empty_docs(self, evidence_retriever, sample_decision):
        """Test retrieval with no documents."""
        evidence = evidence_retriever.retrieve_evidence(sample_decision, [])
        
        # Should still have evidence from retrieved_context
        assert len(evidence) > 0
    
    def test_relevance_scoring(self, evidence_retriever):
        """Test relevance computation."""
        query = "price margin quantity"
        content = "The price and margin calculations for quantity orders."
        
        score = evidence_retriever._compute_relevance(query, content)
        assert 0.0 <= score <= 1.0
        assert score > 0.1  # Should have some relevance
    
    def test_relevance_no_overlap(self, evidence_retriever):
        """Test relevance with no term overlap."""
        query = "apple orange banana"
        content = "car truck motorcycle"
        
        score = evidence_retriever._compute_relevance(query, content)
        assert score == 0.0
    
    def test_get_top_evidence(
        self, evidence_retriever, sample_decision, sample_documents
    ):
        """Test getting top K evidence."""
        top = evidence_retriever.get_top_evidence(
            sample_decision, sample_documents, top_k=3,
        )
        
        assert len(top) <= 3
        # Should be sorted by relevance
        if len(top) >= 2:
            assert top[0].relevance_score >= top[1].relevance_score
    
    def test_evidence_sources_identified(
        self, evidence_retriever, sample_decision, sample_documents
    ):
        """Test that evidence sources are properly identified."""
        evidence = evidence_retriever.retrieve_evidence(
            sample_decision, sample_documents,
        )
        
        sources = {e.source for e in evidence}
        assert EvidenceSource.DOCUMENT in sources or EvidenceSource.DATABASE in sources


# =============================================================================
# FEATURE ANALYZER TESTS
# =============================================================================


class TestFeatureAnalyzer:
    """Test FeatureAnalyzer."""
    
    def test_analyze_contributions(self, sample_decision):
        """Test analyzing feature contributions."""
        analyzer = FeatureAnalyzer()
        contributions = analyzer.analyze_contributions(sample_decision)
        
        assert len(contributions) > 0
        # Should be sorted by importance
        for i, c in enumerate(contributions):
            assert c.importance_rank == i + 1
    
    def test_contribution_values(self, sample_decision):
        """Test contribution values."""
        analyzer = FeatureAnalyzer()
        contributions = analyzer.analyze_contributions(sample_decision)
        
        for c in contributions:
            assert c.feature_name in sample_decision.input_data
            assert c.direction in ["positive", "negative", "neutral"]
            assert c.explanation
    
    def test_numeric_feature_contribution(self):
        """Test contribution for numeric features."""
        analyzer = FeatureAnalyzer()
        decision = AIDecision(
            decision_id="d1",
            category=DecisionCategory.PRICING,
            input_data={"price": 200.0},
            output=None,
            confidence=0.8,
            model_id="m1",
            model_version="1.0",
            prompt_version="p1",
            retrieved_context=[],
            reasoning_chain=[],
            created_at=datetime.now(),
        )
        
        contributions = analyzer.analyze_contributions(decision)
        assert len(contributions) == 1
        assert contributions[0].feature_name == "price"
    
    def test_boolean_feature_contribution(self):
        """Test contribution for boolean features."""
        analyzer = FeatureAnalyzer()
        decision = AIDecision(
            decision_id="d1",
            category=DecisionCategory.PRICING,
            input_data={"urgency": True, "priority": False},
            output=None,
            confidence=0.8,
            model_id="m1",
            model_version="1.0",
            prompt_version="p1",
            retrieved_context=[],
            reasoning_chain=[],
            created_at=datetime.now(),
        )
        
        contributions = analyzer.analyze_contributions(decision)
        assert len(contributions) == 2
    
    def test_feature_explanation_generation(self):
        """Test explanation generation."""
        analyzer = FeatureAnalyzer()
        explanation = analyzer._generate_feature_explanation(
            "price", 150.0, 0.3, "positive",
        )
        
        assert "price" in explanation.lower()
        assert "150" in explanation


# =============================================================================
# COUNTERFACTUAL GENERATOR TESTS
# =============================================================================


class TestCounterfactualGenerator:
    """Test CounterfactualGenerator."""
    
    def test_generate_counterfactuals(self, sample_decision):
        """Test counterfactual generation."""
        generator = CounterfactualGenerator()
        counterfactuals = generator.generate_counterfactuals(sample_decision)
        
        assert len(counterfactuals) > 0
        for cf in counterfactuals:
            assert cf.scenario_id
            assert cf.description
            assert cf.changes
            assert cf.confidence_delta != 0
    
    def test_counterfactual_limit(self, sample_decision):
        """Test counterfactual limit."""
        generator = CounterfactualGenerator()
        counterfactuals = generator.generate_counterfactuals(
            sample_decision, num_scenarios=2,
        )
        
        assert len(counterfactuals) <= 2
    
    def test_counterfactual_changes(self, sample_decision):
        """Test that changes are properly recorded."""
        generator = CounterfactualGenerator()
        counterfactuals = generator.generate_counterfactuals(sample_decision)
        
        for cf in counterfactuals:
            for feature, change in cf.changes.items():
                assert "from" in change
                assert "to" in change
                assert change["from"] != change["to"]
    
    def test_alternative_outcome_numeric(self):
        """Test alternative outcome for numeric values."""
        generator = CounterfactualGenerator()
        alt = generator._compute_alternative(100.0, -0.2)
        
        assert alt == 80.0  # 100 * (1 - 0.2)
    
    def test_alternative_outcome_boolean(self):
        """Test alternative outcome for boolean values."""
        generator = CounterfactualGenerator()
        
        # Small delta shouldn't flip
        alt_small = generator._compute_alternative(True, -0.1)
        assert alt_small is True
        
        # Large delta should flip
        alt_large = generator._compute_alternative(True, -0.5)
        assert alt_large is False


# =============================================================================
# EXPLANATION GENERATOR TESTS
# =============================================================================


class TestExplanationGenerator:
    """Test ExplanationGenerator."""
    
    def test_generator_creation(self, explanation_generator):
        """Test generator creation."""
        assert explanation_generator.evidence_retriever is not None
        assert explanation_generator.feature_analyzer is not None
        assert explanation_generator.counterfactual_generator is not None
    
    def test_generate_explanation(
        self, explanation_generator, sample_decision, sample_documents
    ):
        """Test full explanation generation."""
        explanation = explanation_generator.generate_explanation(
            sample_decision, sample_documents,
        )
        
        assert isinstance(explanation, DecisionExplanation)
        assert explanation.decision_id == sample_decision.decision_id
        assert explanation.summary
        assert explanation.confidence == sample_decision.confidence
        assert len(explanation.evidence_chunks) > 0
        assert len(explanation.feature_contributions) > 0
    
    def test_explanation_timing(
        self, explanation_generator, sample_decision, sample_documents
    ):
        """Test that generation time is tracked."""
        explanation = explanation_generator.generate_explanation(
            sample_decision, sample_documents,
        )
        
        assert explanation.generation_time_ms >= 0
    
    def test_confidence_level_mapping(self, explanation_generator):
        """Test confidence level determination."""
        assert explanation_generator._determine_confidence_level(0.9) == ConfidenceLevel.HIGH
        assert explanation_generator._determine_confidence_level(0.7) == ConfidenceLevel.MEDIUM
        assert explanation_generator._determine_confidence_level(0.5) == ConfidenceLevel.LOW
        assert explanation_generator._determine_confidence_level(0.3) == ConfidenceLevel.UNCERTAIN
    
    def test_explain_this_suggestion(
        self, explanation_generator, sample_decision, sample_documents
    ):
        """Test 'Explain this Suggestion' handler."""
        result = explanation_generator.explain_this_suggestion(
            sample_decision, sample_documents,
        )
        
        assert "decision_id" in result
        assert "confidence" in result
        assert "summary" in result
        assert "top_evidence" in result
        assert "key_factors" in result
        assert len(result["top_evidence"]) <= 3
        assert len(result["key_factors"]) <= 3
    
    def test_summary_generation(
        self, explanation_generator, sample_decision, sample_documents
    ):
        """Test summary generation."""
        evidence = explanation_generator.evidence_retriever.retrieve_evidence(
            sample_decision, sample_documents,
        )
        contributions = explanation_generator.feature_analyzer.analyze_contributions(
            sample_decision,
        )
        
        summary = explanation_generator._generate_summary(
            sample_decision, evidence, contributions,
        )
        
        assert "pricing" in summary.lower()
        assert "85%" in summary or "0.85" in summary


# =============================================================================
# AUDIT TRAIL TESTS
# =============================================================================


class TestAIReasoningAuditTrail:
    """Test AIReasoningAuditTrail."""
    
    def test_trail_creation(self, audit_trail):
        """Test audit trail creation."""
        assert len(audit_trail.events) == 0
        assert audit_trail.max_events == 10000
    
    def test_log_decision(self, audit_trail, sample_decision):
        """Test logging a decision."""
        event_id = audit_trail.log_decision(sample_decision)
        
        assert event_id
        assert len(audit_trail.events) == 1
        assert sample_decision.decision_id in audit_trail.decisions
    
    def test_log_explanation_request(self, audit_trail, sample_decision):
        """Test logging explanation request."""
        audit_trail.log_decision(sample_decision)
        event_id = audit_trail.log_explanation_request(
            sample_decision.decision_id, "user_456",
        )
        
        assert event_id
        events = audit_trail.get_decision_trail(sample_decision.decision_id)
        assert len(events) == 2
    
    def test_log_feedback(self, audit_trail, sample_decision):
        """Test logging feedback."""
        audit_trail.log_decision(sample_decision)
        event_id = audit_trail.log_feedback(
            sample_decision.decision_id,
            {"helpful": True, "rating": 5},
            "user_123",
        )
        
        assert event_id
        events = audit_trail.get_events_by_type(AuditEventType.FEEDBACK_RECEIVED)
        assert len(events) == 1
    
    def test_log_override(self, audit_trail, sample_decision):
        """Test logging override."""
        audit_trail.log_decision(sample_decision)
        event_id = audit_trail.log_override(
            sample_decision.decision_id,
            {"recommended_price": 175.0},
            "Customer requested lower price",
            "user_123",
        )
        
        assert event_id
        events = audit_trail.get_events_by_type(AuditEventType.OVERRIDE_APPLIED)
        assert len(events) == 1
        assert events[0].details["reason"] == "Customer requested lower price"
    
    def test_log_context_retrieval(self, audit_trail):
        """Test logging context retrieval."""
        event_id = audit_trail.log_context_retrieval(
            "dec_001",
            ["Context 1", "Context 2"],
            25.5,
        )
        
        assert event_id
        assert len(audit_trail.events) == 1
        assert audit_trail.events[0].details["num_chunks"] == 2
    
    def test_get_decision_trail(self, audit_trail, sample_decision):
        """Test getting decision trail."""
        audit_trail.log_decision(sample_decision)
        audit_trail.log_explanation_request(sample_decision.decision_id)
        audit_trail.log_feedback(sample_decision.decision_id, {"helpful": True})
        
        trail = audit_trail.get_decision_trail(sample_decision.decision_id)
        assert len(trail) == 3
    
    def test_get_events_by_type(self, audit_trail, sample_decision):
        """Test getting events by type."""
        audit_trail.log_decision(sample_decision)
        audit_trail.log_explanation_request(sample_decision.decision_id)
        
        decisions = audit_trail.get_events_by_type(AuditEventType.DECISION_MADE)
        explanations = audit_trail.get_events_by_type(AuditEventType.EXPLANATION_REQUESTED)
        
        assert len(decisions) == 1
        assert len(explanations) == 1
    
    def test_get_events_since(self, audit_trail, sample_decision):
        """Test getting events since a time."""
        audit_trail.log_decision(sample_decision)
        
        # Events since 1 hour ago
        events = audit_trail.get_events_by_type(
            AuditEventType.DECISION_MADE,
            since=datetime.now() - timedelta(hours=1),
        )
        assert len(events) == 1
        
        # Events since 1 hour in future
        events = audit_trail.get_events_by_type(
            AuditEventType.DECISION_MADE,
            since=datetime.now() + timedelta(hours=1),
        )
        assert len(events) == 0
    
    def test_model_usage_stats(self, audit_trail, sample_decision):
        """Test model usage statistics."""
        audit_trail.log_decision(sample_decision)
        
        stats = audit_trail.get_model_usage_stats(sample_decision.model_id)
        
        assert stats["model_id"] == sample_decision.model_id
        assert stats["total_decisions"] == 1
        assert stats["unique_users"] == 1
    
    def test_user_history(self, audit_trail, sample_decision):
        """Test user history retrieval."""
        audit_trail.log_decision(sample_decision, "user_123")
        audit_trail.log_explanation_request(sample_decision.decision_id, "user_123")
        
        history = audit_trail.get_user_history("user_123")
        assert len(history) == 2
    
    def test_export_trail(self, audit_trail, sample_decision):
        """Test exporting full trail."""
        audit_trail.log_decision(sample_decision)
        audit_trail.log_explanation_request(sample_decision.decision_id)
        
        export = audit_trail.export_trail(sample_decision.decision_id)
        
        assert export["decision_id"] == sample_decision.decision_id
        assert export["decision"]["confidence"] == sample_decision.confidence
        assert len(export["events"]) == 2
        assert "exported_at" in export
    
    def test_register_model(self, audit_trail):
        """Test model registration."""
        model_info = ModelInfo(
            model_id="model_001",
            model_name="Test Model",
            version="1.0",
            capabilities=["pricing"],
            last_updated=datetime.now(),
            performance_metrics={"accuracy": 0.9},
        )
        
        audit_trail.register_model(model_info)
        assert "model_001" in audit_trail.model_registry
    
    def test_event_pruning(self):
        """Test that events are pruned when max is exceeded."""
        trail = create_audit_trail(max_events=10)
        
        for i in range(20):
            decision = AIDecision(
                decision_id=f"dec_{i}",
                category=DecisionCategory.PRICING,
                input_data={"x": i},
                output=None,
                confidence=0.8,
                model_id="m1",
                model_version="1.0",
                prompt_version="p1",
                retrieved_context=[],
                reasoning_chain=[],
                created_at=datetime.now(),
            )
            trail.log_decision(decision)
        
        assert len(trail.events) <= 10


# =============================================================================
# XAI SERVICE TESTS
# =============================================================================


class TestXAIService:
    """Test XAIService."""
    
    def test_service_creation(self, xai_service):
        """Test service creation."""
        assert xai_service.explanation_generator is not None
        assert xai_service.audit_trail is not None
    
    def test_record_decision(self, xai_service):
        """Test recording a decision."""
        decision = xai_service.record_decision(
            category=DecisionCategory.SUPPLIER,
            input_data={"lead_time": 5, "quality_score": 0.9},
            output={"supplier": "Supplier A"},
            confidence=0.88,
            model_id="supplier_model",
            model_version="1.0",
            prompt_version="supplier_v2",
            retrieved_context=["Supplier A has fast delivery"],
            user_id="user_789",
        )
        
        assert decision.decision_id
        assert decision.category == DecisionCategory.SUPPLIER
        assert decision.confidence == 0.88
        
        # Should be in audit trail
        stored = xai_service.audit_trail.get_decision(decision.decision_id)
        assert stored == decision
    
    def test_explain_suggestion(self, xai_service, sample_documents):
        """Test explaining a suggestion."""
        decision = xai_service.record_decision(
            category=DecisionCategory.PRICING,
            input_data={"price": 100, "margin": 0.2},
            output={"recommended": 120},
            confidence=0.9,
            model_id="pricing",
            model_version="1.0",
            prompt_version="p1",
            retrieved_context=["Historical data"],
        )
        
        explanation = xai_service.explain_suggestion(
            decision.decision_id, sample_documents,
        )
        
        assert explanation["decision_id"] == decision.decision_id
        assert "summary" in explanation
        assert "top_evidence" in explanation
    
    def test_explain_missing_decision(self, xai_service):
        """Test explaining non-existent decision."""
        result = xai_service.explain_suggestion("non_existent_id")
        assert "error" in result
    
    def test_get_full_explanation(self, xai_service, sample_documents):
        """Test getting full explanation."""
        decision = xai_service.record_decision(
            category=DecisionCategory.QUALITY,
            input_data={"quality_score": 0.95},
            output={"status": "approved"},
            confidence=0.92,
            model_id="quality",
            model_version="1.0",
            prompt_version="q1",
            retrieved_context=["Quality standards met"],
        )
        
        explanation = xai_service.get_full_explanation(
            decision.decision_id, sample_documents,
        )
        
        assert isinstance(explanation, DecisionExplanation)
        assert explanation.category == DecisionCategory.QUALITY
    
    def test_record_feedback(self, xai_service):
        """Test recording feedback."""
        decision = xai_service.record_decision(
            category=DecisionCategory.GENERAL,
            input_data={},
            output="result",
            confidence=0.7,
            model_id="m1",
            model_version="1.0",
            prompt_version="p1",
            retrieved_context=[],
        )
        
        event_id = xai_service.record_feedback(
            decision.decision_id,
            was_helpful=True,
            feedback_text="Good suggestion!",
            user_id="user_123",
        )
        
        assert event_id
    
    def test_record_override(self, xai_service):
        """Test recording override."""
        decision = xai_service.record_decision(
            category=DecisionCategory.PRICING,
            input_data={"price": 100},
            output={"recommended": 120},
            confidence=0.8,
            model_id="m1",
            model_version="1.0",
            prompt_version="p1",
            retrieved_context=[],
        )
        
        event_id = xai_service.record_override(
            decision.decision_id,
            override_value={"recommended": 115},
            reason="Customer negotiation",
            user_id="user_123",
        )
        
        assert event_id
    
    def test_get_audit_trail(self, xai_service):
        """Test getting audit trail."""
        decision = xai_service.record_decision(
            category=DecisionCategory.GENERAL,
            input_data={},
            output="result",
            confidence=0.7,
            model_id="m1",
            model_version="1.0",
            prompt_version="p1",
            retrieved_context=[],
        )
        
        xai_service.explain_suggestion(decision.decision_id)
        
        trail = xai_service.get_audit_trail(decision.decision_id)
        
        assert trail["decision_id"] == decision.decision_id
        assert len(trail["events"]) == 2  # Decision + explanation request
    
    def test_get_model_stats(self, xai_service):
        """Test getting model statistics."""
        for _ in range(3):
            xai_service.record_decision(
                category=DecisionCategory.PRICING,
                input_data={"x": 1},
                output="y",
                confidence=0.85,
                model_id="test_model",
                model_version="1.0",
                prompt_version="p1",
                retrieved_context=[],
                user_id="user_1",
            )
        
        stats = xai_service.get_model_stats("test_model", hours=24)
        
        assert stats["model_id"] == "test_model"
        assert stats["total_decisions"] == 3


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_xai_service(self):
        """Test creating XAI service."""
        service = create_xai_service()
        assert isinstance(service, XAIService)
    
    def test_create_explanation_generator(self):
        """Test creating explanation generator."""
        generator = create_explanation_generator()
        assert isinstance(generator, ExplanationGenerator)
    
    def test_create_audit_trail(self):
        """Test creating audit trail."""
        trail = create_audit_trail(max_events=500)
        assert isinstance(trail, AIReasoningAuditTrail)
        assert trail.max_events == 500
    
    def test_create_evidence_retriever(self):
        """Test creating evidence retriever."""
        retriever = create_evidence_retriever(max_chunks=5)
        assert isinstance(retriever, EvidenceRetriever)
        assert retriever.max_chunks == 5


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestXAIIntegration:
    """Integration tests for XAI system."""
    
    def test_full_xai_workflow(self, xai_service, sample_documents):
        """Test full XAI workflow."""
        # 1. Record a decision
        decision = xai_service.record_decision(
            category=DecisionCategory.PRICING,
            input_data={
                "price": 150.0,
                "quantity": 100,
                "margin": 0.25,
                "urgency": True,
            },
            output={"recommended_price": 187.50},
            confidence=0.88,
            model_id="pricing_v2",
            model_version="2.0.0",
            prompt_version="pricing_prompt_v3",
            retrieved_context=[
                "Historical pricing shows $150-$200 range",
                "Customer has excellent payment history",
            ],
            reasoning_chain=[
                "Analyzed input",
                "Applied margin",
                "Generated recommendation",
            ],
            user_id="user_analyst",
        )
        
        # 2. Get "Explain this Suggestion"
        quick_explain = xai_service.explain_suggestion(
            decision.decision_id, sample_documents,
        )
        
        assert quick_explain["confidence"] == 0.88
        assert len(quick_explain["top_evidence"]) <= 3
        assert len(quick_explain["key_factors"]) <= 3
        
        # 3. Get full explanation
        full_explain = xai_service.get_full_explanation(
            decision.decision_id, sample_documents,
        )
        
        assert full_explain.model_version == "2.0.0"
        assert full_explain.prompt_version == "pricing_prompt_v3"
        
        # 4. Record feedback
        xai_service.record_feedback(
            decision.decision_id,
            was_helpful=True,
            feedback_text="Explanation was clear",
        )
        
        # 5. Record override
        xai_service.record_override(
            decision.decision_id,
            override_value={"recommended_price": 175.0},
            reason="Manager approved discount",
            user_id="user_manager",
        )
        
        # 6. Get full audit trail
        trail = xai_service.get_audit_trail(decision.decision_id)
        
        # Should have: decision, explanation request, feedback, override
        assert len(trail["events"]) == 4
        
        # 7. Get model stats
        stats = xai_service.get_model_stats("pricing_v2")
        assert stats["total_decisions"] == 1
    
    def test_multiple_decisions_same_model(self, xai_service):
        """Test multiple decisions with same model."""
        model_id = "shared_model"
        
        for i in range(5):
            xai_service.record_decision(
                category=DecisionCategory.PRICING,
                input_data={"price": 100 + i * 10},
                output={"result": i},
                confidence=0.7 + i * 0.05,
                model_id=model_id,
                model_version="1.0",
                prompt_version="p1",
                retrieved_context=[],
                user_id=f"user_{i % 2}",
            )
        
        stats = xai_service.get_model_stats(model_id)
        
        assert stats["total_decisions"] == 5
        assert stats["unique_users"] == 2
        assert 0.7 <= stats["avg_confidence"] <= 0.9
    
    def test_compliance_export(self, xai_service):
        """Test compliance-ready export."""
        decision = xai_service.record_decision(
            category=DecisionCategory.RISK,
            input_data={"risk_score": 0.3},
            output={"approved": True},
            confidence=0.95,
            model_id="risk_model",
            model_version="3.0",
            prompt_version="risk_v2",
            retrieved_context=["Risk is within acceptable bounds"],
            reasoning_chain=[
                "Evaluated risk score",
                "Compared to threshold",
                "Approved transaction",
            ],
        )
        
        export = xai_service.get_audit_trail(decision.decision_id)
        
        # Compliance requirements
        assert export["decision"]["model_id"] == "risk_model"
        assert export["decision"]["model_version"] == "3.0"
        assert export["decision"]["prompt_version"] == "risk_v2"
        assert export["decision"]["confidence"] == 0.95
        assert len(export["decision"]["reasoning_steps"]) == 3
        assert "exported_at" in export

import pytest
import numpy as np
from datetime import datetime, timezone
from sensei.services.ai.visual_quality_inspection import (
    VisualQualityInspectionService, 
    DefectCategory, 
    DefectSeverity,
    InspectionConfig
)
from sensei.services.sales.multi_agent_rfq import (
    AgentOrchestrator, 
    RFQSpec, 
    NegotiatorAgent, 
    LogisticsAgent,
    AgentType
)
from sensei.services.ops.tps_teacher import TPSTeacher, PDCAPhase
from sensei.services.ops.ceo_control_plane import CEOControlPlaneService
from sensei.services.ai.knowledge_enrichment import KnowledgeEnrichmentService

@pytest.mark.asyncio
async def test_vision_enrichment():
    service = VisualQualityInspectionService()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Test synthetic generation
    syn_img, defects = service.enricher.generator.generate(img, DefectCategory.SURFACE, count=2)
    assert len(defects) == 2
    assert defects[0].is_synthetic
    
    # Test enrichment directly to avoid model dependency in tests
    from sensei.services.ai.visual_quality_inspection import DetectedDefect, BoundingBox, InspectionResult, InspectionDecision
    
    context = {
        "id": "SW-123",
        "critical_zones": [{"x": 10, "y": 10, "w": 50, "h": 50}]
    }
    
    mock_defect = DetectedDefect(
        defect_id="test1",
        category=DefectCategory.SURFACE,
        severity=DefectSeverity.MINOR,
        confidence=0.9,
        bbox=BoundingBox(15, 15, 10, 10)
    )
    mock_result = InspectionResult(
        inspection_id="ins-1",
        image_id="img-1",
        timestamp=datetime.now(timezone.utc),
        decision=InspectionDecision.PASS,
        decision_confidence=0.9,
        defects=[mock_defect]
    )
    
    enriched = service.enricher.enrich_inspection(mock_result, standard_work_context=context)
    assert enriched.metadata["standard_work_id"] == "SW-123"
    assert enriched.defects[0].severity == DefectSeverity.CRITICAL # Escalated because it's in the critical zone
    assert "recommendations" in enriched.defects[0].metadata

@pytest.mark.asyncio
async def test_rfq_enrichment():
    orchestrator = AgentOrchestrator()
    orchestrator.register_agent(NegotiatorAgent())
    orchestrator.register_agent(LogisticsAgent())
    
    rfq = RFQSpec(
        rfq_id="RFQ-999",
        customer_id="CUST-1",
        description="Enriched parts",
        quantity=100,
        target_price=50.0
    )
    
    analysis = await orchestrator.analyze_rfq(rfq)
    assert len(analysis.negotiation_findings) > 0
    assert len(analysis.logistics_findings) > 0
    assert "opening_offer" in analysis.negotiation_strategy
    assert "shipping_method" in analysis.logistics_plan

@pytest.mark.asyncio
async def test_tps_enrichment():
    teacher = TPSTeacher()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Test multi-modal coaching
    evidence = await teacher.multimodal_coach.analyze_pdca_evidence(img, PDCAPhase.DO)
    assert evidence["evidence_found"]
    assert "detected_muda" in evidence
    
    # Test gamification
    status = teacher.gamification.award_achievement("user1", "Mastered A3", 250)
    assert status["belt"] == "Yellow Belt"
    assert status["xp"] == 250

def test_ceo_enrichment():
    service = CEOControlPlaneService()
    
    # Test scenario modeling
    scenario = service.scenario_modeler.run_scenario("Add Operators", {"add_operators": 2})
    assert scenario.kpi_impacts["OEE"] > 0
    assert "bottlenecks_identified" in scenario.__dict__ or "bottlenecks_identified" in scenario.scenario_id.__dict__ # Testing dataclass
    assert scenario.bottlenecks_identified == ["Station B (Assembly)"]
    
    # Test health heatmap
    health = service.health_heatmap.calculate_health_index([0.2, 0.4], [5.0, 2.0])
    assert 0.0 <= health <= 1.0

def test_knowledge_enrichment():
    service = KnowledgeEnrichmentService()
    domain_data = {
        "quality_trends": "rising",
        "supplier_performance": "variable"
    }
    insights = service.synthesizer.synthesize_insights(domain_data)
    assert len(insights) > 0
    assert "Supplier-Quality Correlation" in [i["title"] for i in insights]

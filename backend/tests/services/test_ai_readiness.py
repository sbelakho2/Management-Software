import pytest
from sensei.services.ai.ai_readiness import get_ai_readiness_service
from sensei.services.ai.onnx_model_init import get_model_registry

@pytest.mark.asyncio
async def test_ai_readiness_report():
    service = get_ai_readiness_service()
    report = service.generate_report()
    
    assert report is not None
    assert report.overall_status in ["green", "yellow", "red"]
    assert len(report.components) > 0
    
    # Check for expected components
    component_names = [c.name for c in report.components]
    assert any("Model: embeddings" in name for name in component_names)
    assert any("Text Embedding Service" in name for name in component_names)

@pytest.mark.asyncio
async def test_ai_performance_verification():
    service = get_ai_readiness_service()
    results = await service.verify_performance()
    
    assert results["status"] == "success"
    assert "measurements" in results
    assert len(results["measurements"]) > 0
    assert "total_time_ms" in results

def test_model_registry_paths():
    registry = get_model_registry()
    paths = registry.get_model_paths()
    
    assert "embeddings" in paths
    assert "reranker" in paths
    assert "vlm" in paths
    assert "layout" in paths
    
    # Verify slugs are correctly formatted (no slashes)
    for name, path in paths.items():
        assert "/" not in path.name

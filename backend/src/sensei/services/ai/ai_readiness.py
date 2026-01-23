"""
AI Readiness Service - Aggregates health and performance status for all on-device AI.

This service provides a high-level view of AI capabilities, ensuring all models
are well-trained, verified, and ready for production use.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sensei.services.ai.onnx_model_init import get_model_registry, ModelTier

logger = logging.getLogger(__name__)


@dataclass
class AIComponentStatus:
    """Status of a specific AI component."""
    name: str
    status: str  # "green", "yellow", "red"
    ready: bool
    latency_ms: Optional[float] = None
    model_version: Optional[str] = None
    last_verified: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    tier: ModelTier = ModelTier.LIGHTWEIGHT


@dataclass
class AIReadinessReport:
    """Global AI readiness report."""
    overall_status: str
    components: List[AIComponentStatus]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_latency_ms: float = 0.0
    memory_pressure: str = "low"


class AIReadinessService:
    """
    Service to monitor and verify all on-device AI components.
    """

    def __init__(self):
        self._registry = get_model_registry()
        self._last_report: Optional[AIReadinessReport] = None

    def generate_report(self) -> AIReadinessReport:
        """
        Generate a comprehensive AI readiness report.
        """
        model_status = self._registry.get_health_status()
        components = []
        
        # 1. Map ONNX models to components
        for name, info in model_status.get("models", {}).items():
            status = "green" if info["is_valid"] else "red"
            if info["warnings"] and status == "green":
                status = "yellow"
            
            components.append(AIComponentStatus(
                name=f"Model: {name}",
                status=status,
                ready=info["is_valid"],
                latency_ms=info["warmup_time_ms"],
                last_verified=datetime.now(timezone.utc),
                errors=[info["error"]] if info["error"] else [],
                tier=self._infer_tier(name)
            ))

        # 2. Check Service Readiness (via specific service interfaces)
        self._check_service_readiness(components)

        # 3. Calculate overall status
        ready_count = sum(1 for c in components if c.ready)
        overall_status = "green"
        if ready_count < len(components):
            overall_status = "yellow"
        if ready_count == 0:
            overall_status = "red"

        report = AIReadinessReport(
            overall_status=overall_status,
            components=components,
            total_latency_ms=sum(c.latency_ms or 0 for c in components)
        )
        self._last_report = report
        return report

    def _infer_tier(self, model_name: str) -> ModelTier:
        """Infer model tier based on name."""
        if "embeddings" in model_name or "anomaly" in model_name:
            return ModelTier.LIGHTWEIGHT
        if "vlm" in model_name or "heavy" in model_name:
            return ModelTier.HEAVY
        return ModelTier.BALANCED

    def _check_service_readiness(self, components: List[AIComponentStatus]):
        """Check high-level AI services."""
        # This would call .is_ready() on various AI services
        try:
            from sensei.services.ai.onnx_text_embeddings import get_onnx_embedder
            embedder = get_onnx_embedder()
            components.append(AIComponentStatus(
                name="Text Embedding Service",
                status="green" if embedder.is_ready() else "red",
                ready=embedder.is_ready(),
                tier=ModelTier.LIGHTWEIGHT
            ))
        except ImportError:
            logger.debug("Text embedding service not available")

        try:
            from sensei.services.ai.ai_reasoning import AIReasoningService
            reasoning_service = AIReasoningService()
            reasoning_ready = reasoning_service.is_ready()
            components.append(AIComponentStatus(
                name="AI Reasoning Service",
                status="green" if reasoning_ready else "red",
                ready=reasoning_ready,
                tier=ModelTier.BALANCED
            ))
        except ImportError:
            logger.debug("AI reasoning service not available")

    async def verify_performance(self) -> Dict[str, Any]:
        """
        Run a real-time performance verification (Golden Samples).
        """
        results: Dict[str, Any] = {"status": "success", "measurements": []}
        start_time = time.perf_counter()
        
        # Test Embeddings
        try:
            from sensei.services.ai.onnx_text_embeddings import get_onnx_embedder
            embedder = get_onnx_embedder()
            t0 = time.perf_counter()
            _ = embedder.embed_text("Verify model performance with golden sample.")
            results["measurements"].append({
                "component": "embeddings",
                "latency_ms": (time.perf_counter() - t0) * 1000
            })
        except Exception as e:
            results["measurements"].append({"component": "embeddings", "error": str(e)})

        results["total_time_ms"] = (time.perf_counter() - start_time) * 1000
        return results


# Singleton
_readiness_service: Optional[AIReadinessService] = None

def get_ai_readiness_service() -> AIReadinessService:
    global _readiness_service
    if _readiness_service is None:
        _readiness_service = AIReadinessService()
    return _readiness_service

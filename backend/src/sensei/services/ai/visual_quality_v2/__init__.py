"""
Visual Quality Inspection Package - Modularized.

Provides world-class visual defect detection for manufacturing:
- Deep learning-based anomaly detection (PatchCore, EfficientAD, CFA)
- Object detection for specific defect types
- Multi-scale inspection
- Continuous learning from operator feedback
"""

from sensei.services.ai.visual_quality_v2.enums import (
    DefectCategory,
    DefectSeverity,
    InspectionDecision,
    ModelType,
    AnomalyMethod,
    ZoneType,
)
from sensei.services.ai.visual_quality_v2.models import (
    BoundingBox,
    SegmentationMask,
    InspectionZone,
    DetectedDefect,
    AnomalyMap,
    InspectionResult,
    InspectionBatch,
)
from sensei.services.ai.visual_quality_v2.generators import (
    SyntheticDefectGenerator,
    VisionEnrichmentSuite,
)
from sensei.services.ai.visual_quality_v2.detectors import (
    AnomalyDetector,
    DefectDetector,
    PatchCoreDetector,
)
from sensei.services.ai.visual_quality_v2.service import (
    VisualQualityInspectionService,
    InspectionConfig,
    FeedbackRecord,
    TrainingDataset,
    QualityScoringEngine,
    AsyncContinuousLearningManager,
    ContinuousLearningManager,
    YOLODefectDetector,
)

__all__ = [
    # Enums
    "DefectCategory",
    "DefectSeverity",
    "InspectionDecision",
    "ModelType",
    "AnomalyMethod",
    "ZoneType",
    # Models
    "BoundingBox",
    "SegmentationMask",
    "InspectionZone",
    "DetectedDefect",
    "AnomalyMap",
    "InspectionResult",
    "InspectionBatch",
    # Generators
    "SyntheticDefectGenerator",
    "VisionEnrichmentSuite",
    # Detectors
    "AnomalyDetector",
    "DefectDetector",
    "PatchCoreDetector",
    # Service
    "VisualQualityInspectionService",
    "InspectionConfig",
    "FeedbackRecord",
    "TrainingDataset",
    "QualityScoringEngine",
    "AsyncContinuousLearningManager",
    "ContinuousLearningManager",
    "YOLODefectDetector",
]

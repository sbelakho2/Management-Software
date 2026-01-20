"""
Data models for visual quality inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from sensei.services.ai.visual_quality_v2.enums import (
    DefectCategory,
    DefectSeverity,
    InspectionDecision,
    ZoneType,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BoundingBox:
    """Bounding box for a detection."""
    x: int  # Left
    y: int  # Top
    width: int
    height: int
    
    @property
    def x2(self) -> int:
        return self.x + self.width
    
    @property
    def y2(self) -> int:
        return self.y + self.height
    
    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union."""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0.0


@dataclass
class SegmentationMask:
    """Pixel-level segmentation mask."""
    mask: np.ndarray  # Binary or probability mask
    area: int = 0
    
    def __post_init__(self):
        if isinstance(self.mask, np.ndarray):
            self.area = int(np.sum(self.mask > 0.5))


@dataclass 
class InspectionZone:
    """A zone within an image to inspect."""
    zone_id: str
    zone_type: ZoneType
    bbox: BoundingBox
    name: str = ""
    priority: int = 1  # Higher = more important
    acceptance_criteria: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedDefect:
    """A single detected defect."""
    defect_id: str
    category: DefectCategory
    severity: DefectSeverity
    confidence: float  # 0-1
    bbox: BoundingBox | None = None
    mask: SegmentationMask | None = None
    
    # Anomaly score (for anomaly detection methods)
    anomaly_score: float = 0.0
    
    # Classification info
    defect_type: str = ""  # Specific defect type
    defect_name: str = ""  # Human-readable name
    
    # Location info
    zone: InspectionZone | None = None
    location_description: str = ""
    
    # Measurements
    size_mm: float | None = None  # Defect size in mm
    depth_mm: float | None = None  # Defect depth if measurable
    
    # Explanation
    explanation: str = ""
    
    # Review flags
    needs_review: bool = False
    is_false_positive: bool = False
    is_synthetic: bool = False
    
    # Metadata for enrichment
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_critical(self) -> bool:
        return self.severity in [DefectSeverity.CRITICAL, DefectSeverity.MAJOR]


@dataclass
class AnomalyMap:
    """Pixel-wise anomaly map from anomaly detection."""
    map: np.ndarray  # 2D array of anomaly scores
    threshold: float  # Threshold for binarization
    max_score: float  # Maximum anomaly score
    mean_score: float  # Mean anomaly score
    
    def get_anomaly_regions(
        self,
        min_area: int = 100,
    ) -> list[tuple[BoundingBox, float]]:
        """
        Get regions with high anomaly scores.
        
        Returns list of (bbox, region_score) tuples.
        """
        binary = self.map > self.threshold
        
        # In production: Use connected component analysis
        # For now, return placeholder
        if self.max_score > self.threshold:
            return [(
                BoundingBox(100, 100, 50, 50),
                self.max_score,
            )]
        return []


@dataclass
class InspectionResult:
    """Result of a single image inspection."""
    inspection_id: str
    image_id: str
    timestamp: datetime
    
    # Decision
    decision: InspectionDecision
    decision_confidence: float
    
    # Defects
    defects: list[DetectedDefect] = field(default_factory=list)
    total_defect_count: int = 0
    
    # Anomaly detection results
    anomaly_map: AnomalyMap | None = None
    anomaly_score: float = 0.0  # Overall anomaly score
    
    # Zone-level results
    zone_results: dict[str, InspectionDecision] = field(default_factory=dict)
    
    # Quality metrics
    quality_score: float = 100.0  # 0-100, higher is better
    
    # Processing info
    processing_time_ms: float = 0.0
    models_used: list[str] = field(default_factory=list)
    
    # Flags
    needs_human_review: bool = False
    review_reason: str = ""
    
    # Metadata for enrichment
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_pass(self) -> bool:
        return self.decision == InspectionDecision.PASS
    
    @property
    def critical_defects(self) -> list[DetectedDefect]:
        return [d for d in self.defects if d.is_critical]


@dataclass
class InspectionBatch:
    """Batch of inspection results."""
    batch_id: str
    results: list[InspectionResult]
    
    # Aggregate statistics
    total_inspected: int = 0
    pass_count: int = 0
    fail_count: int = 0
    review_count: int = 0
    
    # Defect summary
    defect_summary: dict[str, int] = field(default_factory=dict)
    
    # Time range
    start_time: datetime | None = None
    end_time: datetime | None = None
    
    @property
    def pass_rate(self) -> float:
        if self.total_inspected == 0:
            return 1.0
        return self.pass_count / self.total_inspected
    
    @property
    def yield_rate(self) -> float:
        """First-pass yield (excludes rework)."""
        return self.pass_rate

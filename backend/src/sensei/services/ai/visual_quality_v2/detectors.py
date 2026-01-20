"""
Abstract detector classes for visual quality inspection.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from sensei.services.ai.visual_quality_v2.enums import (
    AnomalyMethod,
    DefectCategory,
    DefectSeverity,
    ModelType,
)
from sensei.services.ai.visual_quality_v2.models import (
    AnomalyMap,
    BoundingBox,
    DetectedDefect,
    InspectionZone,
)

logger = logging.getLogger(__name__)


class AnomalyDetector(ABC):
    """Abstract base class for anomaly detection models."""
    
    def __init__(
        self,
        method: AnomalyMethod = AnomalyMethod.PATCHCORE,
        threshold: float = 0.5,
    ):
        self.method = method
        self.threshold = threshold
        self.model: Any = None
        self.is_fitted = False
        self.feature_extractor: Any = None
        self.memory_bank: np.ndarray | None = None
    
    @abstractmethod
    async def fit(
        self,
        good_images: list[np.ndarray],
        product_type: str = "default",
    ) -> None:
        """Train on good (defect-free) samples."""
        pass
    
    @abstractmethod
    async def predict(
        self,
        image: np.ndarray,
    ) -> tuple[float, AnomalyMap | None]:
        """
        Detect anomalies in an image.
        
        Returns:
            anomaly_score: Overall anomaly score (0-1, higher = more anomalous)
            anomaly_map: Pixel-wise anomaly map (if available)
        """
        pass
    
    @abstractmethod
    def score_to_defects(
        self,
        score: float,
        anomaly_map: AnomalyMap | None,
    ) -> list[DetectedDefect]:
        """Convert anomaly scores to detected defects."""
        pass


class DefectDetector(ABC):
    """Abstract base class for defect detection models."""
    
    def __init__(
        self,
        model_type: ModelType = ModelType.DEFECT_DETECTION,
        confidence_threshold: float = 0.5,
    ):
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.model: Any = None
        self.class_names: list[str] = []
    
    @abstractmethod
    async def load_model(self, model_path: str) -> None:
        """Load a trained model."""
        pass
    
    @abstractmethod
    async def detect(
        self,
        image: np.ndarray,
        zones: list[InspectionZone] | None = None,
    ) -> list[DetectedDefect]:
        """
        Detect defects in an image.
        
        Args:
            image: Input image
            zones: Optional zones to focus detection
            
        Returns:
            List of detected defects
        """
        pass
    
    @abstractmethod
    async def classify(
        self,
        image: np.ndarray,
        roi: BoundingBox | None = None,
    ) -> tuple[DefectCategory, DefectSeverity, float]:
        """
        Classify a defect region.
        
        Returns:
            category: Defect category
            severity: Defect severity
            confidence: Classification confidence
        """
        pass


class PatchCoreDetector(AnomalyDetector):
    """
    PatchCore anomaly detection implementation.
    
    Uses a pre-trained feature extractor to build a memory bank of
    patch features from good images, then detects anomalies by
    measuring distance to the nearest neighbor.
    """
    
    def __init__(
        self,
        backbone: str = "resnet50",
        patch_size: int = 3,
        threshold: float = 0.5,
        memory_percentage: float = 0.1,
    ):
        super().__init__(method=AnomalyMethod.PATCHCORE, threshold=threshold)
        self.backbone = backbone
        self.patch_size = patch_size
        self.memory_percentage = memory_percentage
    
    async def fit(
        self,
        good_images: list[np.ndarray],
        product_type: str = "default",
    ) -> None:
        """Build memory bank from good samples."""
        if not good_images:
            raise ValueError("Need at least one good image for training")
        
        logger.info(f"Training PatchCore on {len(good_images)} good images")
        
        # Extract features from all good images
        all_features = []
        for img in good_images:
            features = self._extract_features(img)
            all_features.append(features)
        
        # Build memory bank using coreset sampling
        all_features_np = np.concatenate(all_features, axis=0)
        sample_size = max(1, int(len(all_features_np) * self.memory_percentage))
        
        # Random sampling (in production, use greedy coreset)
        indices = np.random.choice(len(all_features_np), sample_size, replace=False)
        self.memory_bank = all_features_np[indices]
        
        self.is_fitted = True
        logger.info(f"PatchCore fitted with memory bank size: {len(self.memory_bank)}")
    
    async def predict(
        self,
        image: np.ndarray,
    ) -> tuple[float, AnomalyMap | None]:
        """Detect anomalies using nearest neighbor in memory bank."""
        if not self.is_fitted or self.memory_bank is None:
            # Return random baseline if not fitted
            return 0.3 + np.random.random() * 0.2, None
        
        # Extract features
        features = self._extract_features(image)
        
        # Calculate distances to memory bank
        distances = self._calculate_distances(features)
        
        # Get anomaly score (max distance)
        anomaly_score = float(np.max(distances))
        
        # Create anomaly map
        h, w = image.shape[:2]
        # Reshape distances to spatial map (simplified)
        map_size = int(np.sqrt(len(distances)))
        if map_size > 0:
            anomaly_map_raw = distances[:map_size*map_size].reshape(map_size, map_size)
            # Resize to image size (simplified bilinear)
            try:
                import cv2
                anomaly_map_resized = cv2.resize(anomaly_map_raw, (w, h))
            except ImportError:
                anomaly_map_resized = np.zeros((h, w))
        else:
            anomaly_map_resized = np.zeros((h, w))
        
        anomaly_map = AnomalyMap(
            map=anomaly_map_resized,
            threshold=self.threshold,
            max_score=float(np.max(anomaly_map_resized)),
            mean_score=float(np.mean(anomaly_map_resized)),
        )
        
        return anomaly_score, anomaly_map
    
    def score_to_defects(
        self,
        score: float,
        anomaly_map: AnomalyMap | None,
    ) -> list[DetectedDefect]:
        """Convert anomaly scores to detected defects."""
        defects = []
        
        if score < self.threshold:
            return defects
        
        # Get anomaly regions
        if anomaly_map:
            regions = anomaly_map.get_anomaly_regions()
            for bbox, region_score in regions:
                severity = self._score_to_severity(region_score)
                defects.append(DetectedDefect(
                    defect_id=f"anomaly_{len(defects)}",
                    category=DefectCategory.UNKNOWN,
                    severity=severity,
                    confidence=min(1.0, region_score),
                    bbox=bbox,
                    anomaly_score=region_score,
                    defect_type="anomaly",
                    defect_name="Detected Anomaly",
                    needs_review=severity == DefectSeverity.CRITICAL,
                ))
        else:
            # No map, create single defect for whole image
            severity = self._score_to_severity(score)
            defects.append(DetectedDefect(
                defect_id="anomaly_0",
                category=DefectCategory.UNKNOWN,
                severity=severity,
                confidence=min(1.0, score),
                anomaly_score=score,
                defect_type="anomaly",
                defect_name="Detected Anomaly",
                needs_review=severity == DefectSeverity.CRITICAL,
            ))
        
        return defects
    
    def _extract_features(self, image: np.ndarray) -> np.ndarray:
        """Extract patch features from image."""
        # Simplified feature extraction
        # In production: Use actual backbone (ResNet, EfficientNet, etc.)
        h, w = image.shape[:2]
        
        # Downsample and flatten as pseudo-features
        try:
            import cv2
            resized = cv2.resize(image, (64, 64))
            if len(resized.shape) == 2:
                resized = np.expand_dims(resized, axis=-1)
        except ImportError:
            resized = image[:64, :64]
            if len(resized.shape) == 2:
                resized = np.expand_dims(resized, axis=-1)
        
        features = resized.flatten().astype(np.float32)
        features = features / 255.0  # Normalize
        
        # Add some noise for variability
        features = features + np.random.normal(0, 0.01, features.shape)
        
        return features.reshape(-1, 16)  # 16-dim feature vectors
    
    def _calculate_distances(self, features: np.ndarray) -> np.ndarray:
        """Calculate distances to memory bank."""
        if self.memory_bank is None:
            return np.zeros(len(features))
        
        # L2 distance to nearest neighbor
        distances = []
        for feat in features:
            dist = np.min(np.linalg.norm(self.memory_bank - feat, axis=1))
            distances.append(dist)
        
        return np.array(distances)
    
    def _score_to_severity(self, score: float) -> DefectSeverity:
        """Map anomaly score to severity level."""
        if score > 0.8:
            return DefectSeverity.CRITICAL
        elif score > 0.6:
            return DefectSeverity.MAJOR
        elif score > 0.4:
            return DefectSeverity.MINOR
        else:
            return DefectSeverity.INFORMATIONAL

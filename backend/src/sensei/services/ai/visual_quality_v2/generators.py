"""
Synthetic defect generators for training.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

import numpy as np

from sensei.services.ai.visual_quality_v2.enums import DefectCategory, DefectSeverity
from sensei.services.ai.visual_quality_v2.models import BoundingBox, DetectedDefect


class SyntheticDefectGenerator:
    """
    Generates synthetic defects on good images for training.
    Uses masks, texture overlay, and geometric transforms to simulate realistic defects.
    """
    
    def generate(
        self, 
        base_image: np.ndarray, 
        defect_type: DefectCategory = DefectCategory.SURFACE,
        severity: DefectSeverity = DefectSeverity.MAJOR,
        count: int = 1
    ) -> tuple[np.ndarray, list[DetectedDefect]]:
        """
        Inject synthetic defects into a clean image with realistic blending.
        """
        img = base_image.copy()
        h, w = img.shape[:2]
        defects = []
        
        try:
            import cv2
        except ImportError:
            cv2 = None
        
        for _ in range(count):
            # Random location with margin
            x = random.randint(int(w * 0.1), int(w * 0.8))
            y = random.randint(int(h * 0.1), int(h * 0.8))
            size = random.randint(15, 60)
            
            bbox = BoundingBox(x, y, size, size)
            
            if cv2:
                # Generate defect based on type
                if defect_type == DefectCategory.SURFACE:
                    # Scratch simulation
                    angle = random.randint(0, 180)
                    length = random.randint(20, 80)
                    end_x = x + int(length * np.cos(np.radians(angle)))
                    end_y = y + int(length * np.sin(np.radians(angle)))
                    end_x = max(0, min(w - 1, end_x))
                    end_y = max(0, min(h - 1, end_y))
                    
                    color_delta = random.randint(-50, -20)
                    if len(img.shape) == 3:
                        color = tuple(max(0, c + color_delta) for c in img[y, x])
                    else:
                        color = max(0, int(img[y, x]) + color_delta)
                    
                    cv2.line(img, (x, y), (end_x, end_y), color, random.randint(1, 3))
                    
                elif defect_type == DefectCategory.MATERIAL:
                    # Porosity/crack simulation
                    color_delta = random.randint(-70, -30)
                    if len(img.shape) == 3:
                        color = tuple(max(0, c + color_delta) for c in img[y, x])
                    else:
                        color = max(0, int(img[y, x]) + color_delta)
                    
                    cv2.circle(img, (x, y), size // 2, color, -1)
                    
                elif defect_type == DefectCategory.CONTAMINATION:
                    # Foreign particle simulation
                    color = (random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
                    if len(img.shape) == 2:
                        color = random.randint(50, 100)
                    
                    pts = np.array([
                        [x, y],
                        [x + size, y + size // 3],
                        [x + size // 2, y + size],
                    ], np.int32)
                    cv2.fillPoly(img, [pts], color)
                    
                else:
                    # Generic defect - dark spot
                    color_delta = random.randint(-60, -20)
                    if len(img.shape) == 3:
                        color = tuple(max(0, c + color_delta) for c in img[y, x])
                    else:
                        color = max(0, int(img[y, x]) + color_delta)
                    
                    cv2.ellipse(img, (x, y), (size // 2, size // 3), 
                               random.randint(0, 180), 0, 360, color, -1)
            
            # Create defect record
            defects.append(DetectedDefect(
                defect_id=str(uuid.uuid4()),
                category=defect_type,
                severity=severity,
                confidence=1.0,  # Ground truth
                bbox=bbox,
                anomaly_score=0.8 + random.random() * 0.2,
                defect_type=f"synthetic_{defect_type.value}",
                defect_name=f"Synthetic {defect_type.value.title()} Defect",
                is_synthetic=True,
            ))
        
        return img, defects
    
    def augment_defect(
        self,
        image: np.ndarray,
        defect: DetectedDefect,
    ) -> tuple[np.ndarray, DetectedDefect]:
        """Apply augmentation to an existing defect for variety."""
        try:
            import cv2
        except ImportError:
            return image, defect
        
        img = image.copy()
        
        # Random brightness adjustment
        brightness = random.uniform(0.8, 1.2)
        img = np.clip(img * brightness, 0, 255).astype(np.uint8)
        
        # Random Gaussian noise
        if random.random() > 0.5:
            noise = np.random.normal(0, 10, img.shape)
            img = np.clip(img + noise, 0, 255).astype(np.uint8)
        
        return img, defect


class VisionEnrichmentSuite:
    """
    Multi-method enrichment for defect images:
    - GradCAM visualization
    - Feature importance mapping
    - Confidence calibration
    - Explanation generation
    """
    
    def __init__(self):
        self.enabled = True
    
    def enrich_result(
        self,
        result: Any,
        image: np.ndarray,
        model_outputs: dict[str, Any] | None = None,
    ) -> Any:
        """Enrich inspection result with explainability data."""
        if not self.enabled:
            return result
        
        # Add basic enrichments
        result.metadata["enriched"] = True
        result.metadata["enrichment_version"] = "1.0"
        
        # In production: Add GradCAM, SHAP, etc.
        # For now, add placeholder data
        if hasattr(result, "defects"):
            for defect in result.defects:
                if not defect.explanation:
                    defect.explanation = self._generate_explanation(defect)
        
        return result
    
    def _generate_explanation(self, defect: DetectedDefect) -> str:
        """Generate human-readable explanation for a defect."""
        parts = [f"Detected {defect.category.value} defect"]
        
        if defect.confidence:
            parts.append(f"with {defect.confidence*100:.1f}% confidence")
        
        if defect.severity:
            parts.append(f"(severity: {defect.severity.value})")
        
        if defect.anomaly_score > 0:
            parts.append(f"Anomaly score: {defect.anomaly_score:.3f}")
        
        if defect.bbox:
            parts.append(f"Location: ({defect.bbox.x}, {defect.bbox.y})")
        
        return ". ".join(parts) + "."

"""
Enums for visual quality inspection.
"""

from enum import Enum


class DefectCategory(str, Enum):
    """High-level defect categories."""
    SURFACE = "surface"  # Scratches, dents, discoloration
    DIMENSIONAL = "dimensional"  # Size, shape deviations
    ASSEMBLY = "assembly"  # Missing parts, misalignment
    MATERIAL = "material"  # Cracks, porosity, inclusions
    CONTAMINATION = "contamination"  # Foreign material, stains
    PACKAGING = "packaging"  # Damage during handling
    UNKNOWN = "unknown"


class DefectSeverity(str, Enum):
    """Defect severity levels."""
    CRITICAL = "critical"  # Must reject, safety issue
    MAJOR = "major"  # Likely reject, functionality affected
    MINOR = "minor"  # Cosmetic, may accept with deviation
    INFORMATIONAL = "informational"  # Observation only


class InspectionDecision(str, Enum):
    """Inspection outcome decisions."""
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"  # Needs human review
    REWORK = "rework"  # Can be fixed


class ModelType(str, Enum):
    """Types of inspection models."""
    ANOMALY_DETECTION = "anomaly_detection"  # Unsupervised
    DEFECT_CLASSIFICATION = "defect_classification"  # Supervised classification
    DEFECT_DETECTION = "defect_detection"  # Object detection
    DEFECT_SEGMENTATION = "defect_segmentation"  # Semantic/instance segmentation


class AnomalyMethod(str, Enum):
    """Anomaly detection methods."""
    PATCHCORE = "patchcore"  # Memory bank approach
    EFFICIENTAD = "efficientad"  # Student-teacher distillation
    CFA = "cfa"  # Coupled-hypersphere-based Feature Adaptation
    PADIM = "padim"  # Patch Distribution Modeling
    AUTOENCODER = "autoencoder"  # Reconstruction-based


class ZoneType(str, Enum):
    """Inspection zone types."""
    WHOLE = "whole"  # Entire product
    CRITICAL = "critical"  # High-priority areas
    FUNCTIONAL = "functional"  # Functional surfaces
    COSMETIC = "cosmetic"  # Appearance-only areas
    CUSTOM = "custom"  # User-defined zones

"""ML: trained neural networks for boundary, tissue, and probe detection."""
from __future__ import annotations

from woundscan.ml.boundary_segmentation import (
    BoundarySegmentationModel,
    SegmentationResult,
)
from woundscan.ml.fiducial_robust import RobustFiducialDetector
from woundscan.ml.model_registry import ModelCard, ModelRegistry
from woundscan.ml.probe_detection import ProbeDetection, ProbeDetectionModel
from woundscan.ml.tissue_classification import (
    TissueClass,
    TissueClassificationModel,
    TissueClassificationResult,
)

__all__ = [
    "BoundarySegmentationModel",
    "ModelCard",
    "ModelRegistry",
    "ProbeDetection",
    "ProbeDetectionModel",
    "RobustFiducialDetector",
    "SegmentationResult",
    "TissueClass",
    "TissueClassificationModel",
    "TissueClassificationResult",
]

"""Quality: per-pixel and aggregate confidence components."""

from __future__ import annotations

from woundscan.quality.confidence import (
    ConfidenceWeights,
    QualityComponents,
    compute_confidence_map,
    compute_quality_components,
)
from woundscan.quality.edge_proximity import compute_edge_distance
from woundscan.quality.frame_consistency import compute_frame_consistency
from woundscan.quality.lighting import compute_lighting_uniformity
from woundscan.quality.motion import compute_motion_artifact
from woundscan.quality.specularity import compute_specularity
from woundscan.quality.texture import compute_texture_contrast

__all__ = [
    "ConfidenceWeights",
    "QualityComponents",
    "compute_confidence_map",
    "compute_edge_distance",
    "compute_frame_consistency",
    "compute_lighting_uniformity",
    "compute_motion_artifact",
    "compute_quality_components",
    "compute_specularity",
    "compute_texture_contrast",
]

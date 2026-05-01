"""Composite per-pixel confidence map.

Combines per-pixel quality components into a single confidence score
using the WoundScan weighting:

    c(x, y) = 0.25*(1 - specularity)
            + 0.20*texture_contrast
            + 0.15*lighting_uniformity
            + 0.15*(1 - motion_artifact)
            + 0.10*edge_distance
            + 0.10*frame_consistency
            + 0.05*boundary_confidence

Weights are version-locked. Any change is a regulatory deviation that
must be documented and re-validated. The weights live in this module
constant `DEFAULT_WEIGHTS` and are recorded in every measurement's
provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class ConfidenceWeights:
    """Version-locked weights for confidence map composition.

    The weights MUST sum to 1.0. Use the validator factory `validated()`.
    """

    specularity: float = 0.25
    texture: float = 0.20
    lighting: float = 0.15
    motion: float = 0.15
    edge_distance: float = 0.10
    frame_consistency: float = 0.10
    boundary_confidence: float = 0.05
    version: str = "v1.0.0"

    def __post_init__(self) -> None:
        total = (
            self.specularity
            + self.texture
            + self.lighting
            + self.motion
            + self.edge_distance
            + self.frame_consistency
            + self.boundary_confidence
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


DEFAULT_WEIGHTS = ConfidenceWeights()


@dataclass(frozen=True)
class QualityComponents:
    """Per-pixel quality maps. All in [0, 1] and same shape."""

    specularity: np.ndarray
    texture: np.ndarray
    lighting: np.ndarray
    motion: np.ndarray
    edge_distance: np.ndarray
    frame_consistency: np.ndarray
    boundary_confidence: np.ndarray = field(default=None)  # type: ignore[assignment]


def compute_quality_components(
    rgb: np.ndarray,
    depth_stack_cm: np.ndarray,
    mask: np.ndarray,
    poses: list,  # list[CameraPose]
    dx_cm: float,
    dy_cm: float,
    boundary_confidence: Optional[np.ndarray] = None,
) -> QualityComponents:
    """Run all quality component computations from raw inputs."""
    from woundscan.quality.edge_proximity import compute_edge_distance
    from woundscan.quality.frame_consistency import compute_frame_consistency
    from woundscan.quality.lighting import compute_lighting_uniformity
    from woundscan.quality.motion import compute_motion_artifact
    from woundscan.quality.specularity import compute_specularity
    from woundscan.quality.texture import compute_texture_contrast

    spec = compute_specularity(rgb)
    tex = compute_texture_contrast(rgb)
    light = compute_lighting_uniformity(rgb)
    motion = compute_motion_artifact(poses, rgb.shape[:2])
    edge = compute_edge_distance(mask, dx_cm, dy_cm)
    fc = compute_frame_consistency(depth_stack_cm)

    if boundary_confidence is None:
        boundary_confidence = np.where(mask, 1.0, 0.0).astype(np.float32)

    return QualityComponents(
        specularity=spec,
        texture=tex,
        lighting=light,
        motion=motion,
        edge_distance=edge,
        frame_consistency=fc,
        boundary_confidence=boundary_confidence,
    )


def compute_confidence_map(
    components: QualityComponents,
    weights: ConfidenceWeights = DEFAULT_WEIGHTS,
) -> np.ndarray:
    """Composite confidence map in [0, 1] from per-pixel components."""
    c = (
        weights.specularity * (1.0 - components.specularity)
        + weights.texture * components.texture
        + weights.lighting * components.lighting
        + weights.motion * (1.0 - components.motion)
        + weights.edge_distance * components.edge_distance
        + weights.frame_consistency * components.frame_consistency
        + weights.boundary_confidence * components.boundary_confidence
    )
    return np.clip(c, 0.0, 1.0).astype(np.float32)

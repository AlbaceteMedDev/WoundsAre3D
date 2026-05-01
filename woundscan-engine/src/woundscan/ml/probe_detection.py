"""Probe tip auto-detection.

YOLO-class object detector trained to find the probe tip in clinical
photos. Output: bounding box(es) + tip pixel position + confidence.

The clinician can fall back to manual tap-on-photo when the detector
fails or its confidence is low. We expose a simple `ProbeDetection`
result and a fallback that returns no detections (so the iOS app prompts
for manual entry).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ProbeDetection:
    """Detected probe tip in image-space coordinates.

    Attributes
    ----------
    bbox_xyxy : (4,) array of [x1, y1, x2, y2] in pixels
    tip_pix : (x, y) pixel position of the probe tip
    confidence : float in [0, 1]
    model_version : str
    """

    bbox_xyxy: tuple[float, float, float, float]
    tip_pix: tuple[float, float]
    confidence: float
    model_version: str


class ProbeDetectionModel:
    """Probe-tip detector. Fallback returns no detections."""

    DEFAULT_VERSION = "fallback-none-v0"

    def __init__(self, weights_path: Path | str | None = None):
        self.weights_path = Path(weights_path) if weights_path else None

    @classmethod
    def from_weights(cls, p: Path | str) -> ProbeDetectionModel:
        return cls(weights_path=p)

    @classmethod
    def fallback(cls) -> ProbeDetectionModel:
        return cls(weights_path=None)

    @property
    def version(self) -> str:
        if self.weights_path and self.weights_path.exists():
            return self.weights_path.stem
        return self.DEFAULT_VERSION

    def detect(self, rgb: np.ndarray) -> list[ProbeDetection]:
        """Detect probe tips in an RGB image. Empty list = nothing found."""
        if self.weights_path is None or not self.weights_path.exists():
            return []
        # Production path runs YOLO via ultralytics or torchvision; we
        # leave the integration as a stub here since it requires real weights.
        return []

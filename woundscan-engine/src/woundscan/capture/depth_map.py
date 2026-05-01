"""iPhone LiDAR depth map ingestion.

The iOS app captures depth as ARKit's `sceneDepth` AVDepthData buffer.
On the wire it is sent as a (H, W) float32 array with depth in meters
and a per-pixel confidence channel (0 = low, 1 = medium, 2 = high).
We convert to centimeters and store both arrays plus the camera
intrinsics that Apple ships per-frame.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CameraIntrinsics:
    """Pinhole camera intrinsics in pixel units."""

    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

    def to_matrix(self) -> np.ndarray:
        return np.array(
            [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )


@dataclass(frozen=True)
class DepthFrame:
    """A single LiDAR depth frame plus its metadata.

    Attributes
    ----------
    depth_cm : (H, W) float32
        Depth from sensor to scene in cm. NaN where invalid.
    confidence : (H, W) uint8
        ARKit ARDepthData confidence channel, 0..2. 2 = highest.
    intrinsics : CameraIntrinsics
        Per-frame intrinsics for the depth camera.
    timestamp_s : float
    """

    depth_cm: np.ndarray
    confidence: np.ndarray
    intrinsics: CameraIntrinsics
    timestamp_s: float

    def __post_init__(self) -> None:
        if self.depth_cm.shape != self.confidence.shape:
            raise ValueError(
                f"depth shape {self.depth_cm.shape} != confidence shape {self.confidence.shape}"
            )

    def filtered_depth(self, min_confidence: int = 1) -> np.ndarray:
        """Return depth with low-confidence pixels masked out (NaN)."""
        out = self.depth_cm.copy()
        out[self.confidence < min_confidence] = np.nan
        return out


def load_depth_frame(
    depth_meters: np.ndarray,
    confidence: np.ndarray,
    intrinsics: CameraIntrinsics,
    timestamp_s: float,
) -> DepthFrame:
    """Build a DepthFrame from raw ARKit-format inputs.

    Parameters
    ----------
    depth_meters : (H, W) float32
        Raw depth in meters as delivered by ARDepthData.
    confidence : (H, W) uint8
        Confidence map; ARKit values are {0, 1, 2}.
    """
    if depth_meters.ndim != 2:
        raise ValueError(f"depth must be 2D, got {depth_meters.shape}")
    depth_cm = depth_meters.astype(np.float32) * 100.0
    return DepthFrame(
        depth_cm=depth_cm,
        confidence=confidence.astype(np.uint8),
        intrinsics=intrinsics,
        timestamp_s=float(timestamp_s),
    )

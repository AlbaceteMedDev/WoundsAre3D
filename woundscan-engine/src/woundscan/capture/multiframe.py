"""Temporal averaging of LiDAR depth across the burst capture.

Across 60 frames, each pixel sees ~60 noisy depth measurements. After
spatially registering the frames (via ARKit pose), we average them. This
reduces sensor noise by approximately sqrt(N) and is the single most
effective accuracy improvement we can apply at the capture stage.
"""

from __future__ import annotations

import numpy as np

from woundscan.capture.depth_map import DepthFrame


def temporal_average_depth(
    frames: list[DepthFrame],
    min_confidence: int = 1,
    outlier_sigma: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pixelwise temporal average of LiDAR depth.

    Aligns frames pixel-for-pixel (no warping; assumes the sensor does
    not move significantly during the burst, which is the use-case
    constraint we enforce in the iOS app via the motion meter). Bad
    frames are rejected by the motion gate.

    Parameters
    ----------
    frames : list[DepthFrame]
    min_confidence : int
        Per-pixel ARKit confidence threshold.
    outlier_sigma : float
        Robust outlier rejection: pixels more than N stdevs from the
        per-pixel mean are dropped before re-averaging.

    Returns
    -------
    (avg_depth_cm, std_depth_cm, n_used)
        avg_depth_cm: (H, W) mean depth, NaN where no valid samples.
        std_depth_cm: (H, W) per-pixel sample stdev.
        n_used: (H, W) int per-pixel sample count after outlier rejection.
    """
    if not frames:
        raise ValueError("Need at least one frame")
    shape = frames[0].depth_cm.shape

    stack = np.full((len(frames),) + shape, np.nan, dtype=np.float32)
    for i, frame in enumerate(frames):
        if frame.depth_cm.shape != shape:
            raise ValueError(f"Frame {i} shape {frame.depth_cm.shape} != reference {shape}")
        valid = (frame.confidence >= min_confidence) & np.isfinite(frame.depth_cm)
        stack[i, valid] = frame.depth_cm[valid]

    # First-pass mean and std (robust)
    mean1 = np.nanmean(stack, axis=0)
    std1 = np.nanstd(stack, axis=0)

    # Outlier rejection
    deviation = np.abs(stack - mean1[np.newaxis, ...])
    cutoff = outlier_sigma * std1[np.newaxis, ...]
    keep = deviation <= cutoff
    cleaned = np.where(keep, stack, np.nan)

    avg = np.nanmean(cleaned, axis=0).astype(np.float32)
    std = np.nanstd(cleaned, axis=0).astype(np.float32)
    n_used = np.sum(np.isfinite(cleaned), axis=0).astype(np.int32)

    return avg, std, n_used

"""Frame-to-frame depth consistency confidence.

Across a 60-frame capture burst, we compute the standard deviation of
each pixel's depth. Pixels with high inter-frame variance reflect
unstable measurement; low variance is reliable.
"""

from __future__ import annotations

import numpy as np


def compute_frame_consistency(
    depth_stack_cm: np.ndarray,
    *,
    saturation_std_mm: float = 1.0,
) -> np.ndarray:
    """Per-pixel score in [0, 1]; 1 = stable, 0 = highly variable.

    Parameters
    ----------
    depth_stack_cm : (n_frames, H, W) array
        Per-frame depth fields in cm. NaN values are ignored.
    saturation_std_mm : float
        Pointwise stdev (mm) at which the score saturates to 0.
    """
    if depth_stack_cm.ndim != 3:
        raise ValueError(f"depth_stack must be (N, H, W), got {depth_stack_cm.shape}")
    if depth_stack_cm.shape[0] < 2:
        return np.ones(depth_stack_cm.shape[1:], dtype=np.float32)

    std_cm = np.nanstd(depth_stack_cm, axis=0)
    std_mm = std_cm * 10.0

    score = np.exp(-((std_mm / saturation_std_mm) ** 2))
    return np.where(np.isnan(std_mm), 0.0, score).astype(np.float32)

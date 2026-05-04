"""Edge proximity confidence component.

Pixels near the wound boundary have steeper depth gradients and noisier
LiDAR; pixels in the center are more reliable. We compute a per-pixel
distance-to-edge in mm and convert to a confidence score [0, 1] that
increases away from the edge up to a saturation distance.
"""

from __future__ import annotations

import numpy as np


def compute_edge_distance(
    mask: np.ndarray,
    dx_cm: float,
    dy_cm: float,
    saturation_distance_mm: float = 5.0,
) -> np.ndarray:
    """Per-pixel score in [0, 1]; 0 at edge, 1 saturated at center."""
    if mask.dtype != bool:
        mask = mask.astype(bool)

    from scipy.ndimage import distance_transform_edt

    pixel_size_mm = max(dx_cm, dy_cm) * 10.0
    dist_pix = distance_transform_edt(mask)
    dist_mm = dist_pix * pixel_size_mm
    score = np.clip(dist_mm / saturation_distance_mm, 0.0, 1.0)
    return score.astype(np.float32)

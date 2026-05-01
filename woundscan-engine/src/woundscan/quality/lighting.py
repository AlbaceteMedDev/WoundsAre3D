"""Lighting uniformity analysis.

Strong gradients in scene illumination cause systematic depth bias from
ARKit and color bias in tissue classification. We compute the smoothness
of the luminance field; flat = good, gradient = degraded.
"""

from __future__ import annotations

import numpy as np


def compute_lighting_uniformity(rgb: np.ndarray) -> np.ndarray:
    """Per-pixel score in [0, 1]; 1 = uniform lighting, 0 = strong gradient.

    Method: low-pass-filter the luminance to extract the slow
    illumination component, then map its local gradient magnitude
    (normalized to mean luminance) to confidence.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb must be (H, W, 3), got {rgb.shape}")

    if rgb.dtype == np.uint8:
        lum = rgb.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        lum /= 255.0
    else:
        lum = rgb.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    from scipy.ndimage import gaussian_filter

    illum = gaussian_filter(lum, sigma=15.0, mode="reflect")
    gx, gy = np.gradient(illum)
    gmag = np.sqrt(gx**2 + gy**2)

    mean_lum = max(float(np.mean(illum)), 1e-3)
    relative_grad = gmag / mean_lum
    # Map: 0 grad -> 1, large grad -> 0. Use exp decay with scale 0.05/pixel.
    score = np.exp(-relative_grad * 20.0)
    return score.astype(np.float32)

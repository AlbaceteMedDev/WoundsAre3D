"""Specular highlight detection.

Specular reflections from glossy exudate or wet tissue saturate the
camera and dropout the LiDAR. We detect them as pixels with very high
luminance AND low chroma (white-ish) and mark them as low-confidence.

Output is a per-pixel "specularity" score in [0, 1]. Higher = more
specular = lower confidence.
"""
from __future__ import annotations

import numpy as np


def _to_hsv(rgb: np.ndarray) -> np.ndarray:
    """Convert (H, W, 3) RGB uint8 or float to HSV in [0, 1]."""
    from skimage.color import rgb2hsv

    if rgb.dtype == np.uint8:
        return rgb2hsv(rgb)
    return rgb2hsv(np.clip(rgb, 0.0, 1.0))


def compute_specularity(
    rgb: np.ndarray,
    luminance_threshold: float = 0.85,
    saturation_threshold: float = 0.20,
) -> np.ndarray:
    """Per-pixel specularity in [0, 1].

    A pixel is specular when value (HSV-V) is high and saturation is low.
    The score blends those two indicators smoothly.

    Parameters
    ----------
    rgb : (H, W, 3) array
    luminance_threshold : float
        V threshold above which a pixel is considered "bright."
    saturation_threshold : float
        S threshold below which a pixel is considered "uncolored."
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb must be (H, W, 3), got {rgb.shape}")

    hsv = _to_hsv(rgb)
    v = hsv[..., 2]
    s = hsv[..., 1]

    bright = np.clip((v - luminance_threshold) / max(1e-6, 1.0 - luminance_threshold), 0.0, 1.0)
    desat = np.clip((saturation_threshold - s) / max(1e-6, saturation_threshold), 0.0, 1.0)
    spec = bright * desat
    return spec.astype(np.float32)

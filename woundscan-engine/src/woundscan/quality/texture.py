"""Texture contrast for confidence weighting.

Featureless regions (uniform color, blown-out highlights) have low
information content and lower depth-fusion confidence; high-contrast
texture regions have reliable feature matches and higher confidence.

We use local standard deviation in luminance, normalized to [0, 1] over
the wound region.
"""

from __future__ import annotations

import numpy as np


def compute_texture_contrast(
    rgb: np.ndarray,
    window_size: int = 7,
) -> np.ndarray:
    """Per-pixel texture contrast in [0, 1].

    Computed as local stdev of luminance, percentile-normalized.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb must be (H, W, 3), got {rgb.shape}")

    if rgb.dtype == np.uint8:
        lum = rgb.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        lum /= 255.0
    else:
        lum = rgb.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    from scipy.ndimage import uniform_filter

    mean = uniform_filter(lum, size=window_size)
    sq = uniform_filter(lum * lum, size=window_size)
    var = np.maximum(sq - mean * mean, 0.0)
    std = np.sqrt(var)

    p_lo = float(np.percentile(std, 5))
    p_hi = float(np.percentile(std, 95))
    if p_hi - p_lo < 1e-9:
        return np.zeros_like(std)
    norm = (std - p_lo) / (p_hi - p_lo)
    return np.clip(norm, 0.0, 1.0).astype(np.float32)

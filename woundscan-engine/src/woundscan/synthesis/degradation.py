"""Degrade synthetic wounds with realistic capture artifacts.

For ML training and end-to-end accuracy validation, we need synthetic
data that resembles real iPhone LiDAR captures: sensor noise, motion
blur, specular highlights from glossy exudate, lighting variation,
local dropouts.

Each degradation function operates on (depth_map, rgb_image) pairs and
returns a degraded copy with the same shape. Functions are pure and
seed-controlled for reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from woundscan.synthesis.analytic_shapes import AnalyticWound


@dataclass
class DegradationConfig:
    """Configuration for the full degradation pipeline.

    Attributes
    ----------
    depth_noise_mm_per_meter : float
        iPhone LiDAR noise model: standard deviation of depth error grows
        approximately linearly with distance from sensor. Apple's documented
        nominal is 1.5cm at 5m -> 3mm/m. Realistic values 2-5 mm/m.
    motion_blur_pixels : float
        Sigma of Gaussian motion blur in pixels (subpixel allowed).
    specular_fraction : float
        Fraction of pixels affected by specular highlights (depth dropout).
    specular_seed : int
        RNG seed for specular pixel selection.
    lighting_gradient : float
        Brightness gradient from one side to the other, in fraction
        of mean brightness. 0.3 = 30% darker on one side.
    overall_noise_seed : int
        RNG seed.
    """

    depth_noise_mm_per_meter: float = 3.0
    motion_blur_pixels: float = 0.5
    specular_fraction: float = 0.05
    specular_seed: int = 0
    lighting_gradient: float = 0.2
    overall_noise_seed: int = 0
    sensor_distance_m: float = 0.3
    enable_dropout: bool = True
    dropout_fraction: float = 0.02
    seed: int = 0
    extras: dict[str, float] = field(default_factory=dict)


def add_sensor_noise(
    depth_map_cm: np.ndarray,
    distance_m: float,
    noise_mm_per_meter: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Add Gaussian sensor noise to depth in cm.

    LiDAR depth uncertainty grows with range; near 30cm at typical wound
    capture distance, sigma_depth ~= 0.9mm at 3 mm/m. We model this as
    pixel-independent Gaussian noise with sigma proportional to (range +
    bed depth).
    """
    sigma_mm = noise_mm_per_meter * (distance_m + depth_map_cm * 0.01)
    sigma_cm = sigma_mm * 0.1
    noise = rng.standard_normal(depth_map_cm.shape) * sigma_cm
    return depth_map_cm + noise


def add_specular_highlights(
    depth_map_cm: np.ndarray,
    fraction: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Drop a fraction of depth pixels (NaN) to simulate specular reflection.

    Returns
    -------
    (degraded_depth, dropout_mask)
        dropout_mask is True where depth was dropped.
    """
    n = depth_map_cm.size
    n_drop = int(fraction * n)
    if n_drop <= 0:
        return depth_map_cm.copy(), np.zeros_like(depth_map_cm, dtype=bool)
    flat_idx = rng.choice(n, size=n_drop, replace=False)
    mask = np.zeros(n, dtype=bool)
    mask[flat_idx] = True
    mask = mask.reshape(depth_map_cm.shape)
    out = depth_map_cm.copy()
    out[mask] = np.nan
    return out, mask


def add_motion_artifact(
    depth_map_cm: np.ndarray,
    blur_sigma_pixels: float,
) -> np.ndarray:
    """Apply Gaussian blur (motion approximation) to the depth field."""
    if blur_sigma_pixels <= 0:
        return depth_map_cm.copy()
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(depth_map_cm, sigma=blur_sigma_pixels, mode="reflect")


def add_lighting_variation(
    rgb_image: np.ndarray,
    gradient: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Multiply RGB by a smooth left-right brightness ramp.

    rgb_image: (H, W, 3) uint8 or float in [0, 1].
    """
    h, w = rgb_image.shape[:2]
    angle = float(rng.uniform(0, 2 * np.pi))
    direction = np.array([np.cos(angle), np.sin(angle)])
    yy, xx = np.mgrid[0:h, 0:w]
    coords = np.stack([(xx - w / 2) / w, (yy - h / 2) / h], axis=-1)
    proj = (coords * direction).sum(axis=-1)
    # Map to [1 - gradient, 1 + gradient]
    lo = 1.0 - gradient / 2.0
    hi = 1.0 + gradient / 2.0
    pmin = float(proj.min())
    pmax = float(proj.max())
    if pmax > pmin:
        ramp = lo + (hi - lo) * (proj - pmin) / (pmax - pmin)
    else:
        ramp = np.ones_like(proj)
    out = rgb_image.astype(float) * ramp[..., np.newaxis]
    if rgb_image.dtype == np.uint8:
        out = np.clip(out, 0, 255).astype(np.uint8)
    else:
        out = np.clip(out, 0.0, 1.0)
    return out


def degrade_synthetic_wound(
    wound: AnalyticWound,
    rgb_image: Optional[np.ndarray] = None,
    config: Optional[DegradationConfig] = None,
) -> tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
    """Run the full degradation pipeline.

    Returns
    -------
    (depth_degraded_cm, rgb_degraded, dropout_mask)
        Degraded depth in cm. dropout_mask True where depth is NaN.
        RGB returned as None if input was None.
    """
    cfg = config or DegradationConfig()
    rng = np.random.default_rng(cfg.seed or cfg.overall_noise_seed)

    depth = wound.depth_map.copy()

    depth = add_sensor_noise(depth, cfg.sensor_distance_m, cfg.depth_noise_mm_per_meter, rng)
    depth = add_motion_artifact(depth, cfg.motion_blur_pixels)
    depth, dropout_mask = add_specular_highlights(
        depth, cfg.specular_fraction, np.random.default_rng(cfg.specular_seed)
    )

    rgb_out = None
    if rgb_image is not None:
        rgb_out = add_lighting_variation(rgb_image, cfg.lighting_gradient, rng)

    return depth, rgb_out, dropout_mask

"""Irregular wound beds: smooth analytic base + Perlin/Simplex noise overlay.

Real wound beds are not analytic surfaces. We generate test cases that
exercise the geometry math on physically realistic morphology by adding
correlated, bounded noise to a smooth base depth field.

The noise is band-limited (Perlin / Simplex) to mimic real tissue
texture: low-frequency variation from anatomy (sloping bed, ridge), mid-
frequency variation from granulation tissue topography, no high-
frequency noise (which would be sensor artifact, not real morphology).

Ground truth is recomputed numerically on a high-resolution grid using
the validated geometry math; the irregular wound carries this as
"true_volume" / "true_surface_area" with explicit notation that they are
high-resolution numerical truth, not analytic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from woundscan.synthesis.analytic_shapes import AnalyticWound, paraboloid


@dataclass(frozen=True)
class IrregularConfig:
    """Configuration for irregular bed generation.

    Attributes
    ----------
    octaves : int
        Number of frequency octaves in the noise. More = rougher.
    base_frequency_per_cm : float
        Lowest frequency in cycles per cm. Wavelength = 1 / freq.
    persistence : float
        Amplitude decay across octaves (0..1). 0.5 is standard.
    amplitude_mm : float
        Peak-to-peak roughness amplitude in mm.
    seed : int
        Random seed.
    """

    octaves: int = 4
    base_frequency_per_cm: float = 0.5
    persistence: float = 0.5
    amplitude_mm: float = 1.0
    seed: int = 0


def _perlin_2d(
    nx: int,
    ny: int,
    dx_cm: float,
    dy_cm: float,
    config: IrregularConfig,
) -> np.ndarray:
    """Generate a 2D Perlin-like noise field with given configuration.

    Falls back to a numpy-only smooth-noise implementation when the
    `noise` package is unavailable. The fallback is band-limited Gaussian
    noise (low-pass via FFT) which has similar spectral characteristics
    to Perlin for the synthesis test purposes.
    """
    try:
        from noise import pnoise2

        rng = np.random.default_rng(config.seed)
        dx_offset = float(rng.uniform(0, 1000))
        dy_offset = float(rng.uniform(0, 1000))
        out = np.empty((ny, nx), dtype=float)
        for j in range(ny):
            y_cm = j * dy_cm
            for i in range(nx):
                x_cm = i * dx_cm
                f = config.base_frequency_per_cm
                v = pnoise2(
                    x_cm * f + dx_offset,
                    y_cm * f + dy_offset,
                    octaves=config.octaves,
                    persistence=config.persistence,
                )
                out[j, i] = v
        return out * config.amplitude_mm * 0.1  # convert mm to cm
    except ImportError:
        rng = np.random.default_rng(config.seed)
        white = rng.standard_normal((ny, nx))
        kx = np.fft.fftfreq(nx, d=dx_cm)
        ky = np.fft.fftfreq(ny, d=dy_cm)
        KX, KY = np.meshgrid(kx, ky)
        K = np.sqrt(KX**2 + KY**2)
        cutoff = config.base_frequency_per_cm * (2.0**config.octaves)
        spectrum_filter = np.where(K > 0, np.exp(-((K / cutoff) ** 2)), 0.0)
        smoothed = np.real(np.fft.ifft2(np.fft.fft2(white) * spectrum_filter))
        s = smoothed.std()
        if s > 0:
            smoothed = smoothed / s
        return smoothed * config.amplitude_mm * 0.1  # mm -> cm


def add_perlin_noise(
    base: AnalyticWound,
    config: IrregularConfig | None = None,
) -> AnalyticWound:
    """Add Perlin noise to an analytic wound's depth map, restricted to the mask.

    The noise is taper-attenuated near the wound boundary so that the
    edge contour remains the same as the base wound. This preserves the
    footprint area and perimeter while only perturbing the bed.

    Returns a new AnalyticWound. The volume and surface area are
    re-computed numerically from the perturbed depth field on a fine
    grid (Simpson's rule); these become the new ground truth references.
    """
    cfg = config or IrregularConfig()
    ny, nx = base.depth_map.shape

    noise_field = _perlin_2d(nx, ny, base.dx, base.dy, cfg)

    # Distance from wound edge for tapering. Use the mask boundary.
    from scipy.ndimage import distance_transform_edt

    dist = distance_transform_edt(base.mask) * min(base.dx, base.dy)
    taper_extent_cm = 0.5  # cm
    taper = np.clip(dist / taper_extent_cm, 0.0, 1.0)

    perturbation = noise_field * taper
    perturbation = np.where(base.mask, perturbation, 0.0)

    new_depth = base.depth_map + perturbation
    new_depth = np.maximum(new_depth, 0.0)
    new_depth = np.where(base.mask, new_depth, 0.0)

    from woundscan.geometry.surface_area import compute_surface_area
    from woundscan.geometry.volume import compute_volume

    new_V = compute_volume(new_depth, base.dx, base.dy, mask=base.mask)
    new_S = compute_surface_area(new_depth, base.dx, base.dy, mask=base.mask)

    return AnalyticWound(
        depth_map=new_depth,
        mask=base.mask,
        dx=base.dx,
        dy=base.dy,
        true_volume=new_V,
        true_surface_area=new_S,
        true_footprint_area=base.true_footprint_area,
        name=f"{base.name}+perlin(amp={cfg.amplitude_mm}mm,oct={cfg.octaves})",
    )


def irregular_paraboloid(
    radius: float = 2.0,
    depth_max: float = 1.0,
    n_grid: int = 201,
    amplitude_mm: float = 1.0,
    seed: int = 0,
) -> AnalyticWound:
    """Convenience: paraboloid with Perlin perturbation. Common test case."""
    base = paraboloid(radius=radius, depth_max=depth_max, n_grid=n_grid)
    cfg = IrregularConfig(amplitude_mm=amplitude_mm, seed=seed)
    return add_perlin_noise(base, cfg)

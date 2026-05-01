"""Clinically representative wound morphology generators.

Each function returns a synthetic wound whose shape, depth, and aspect
ratio are typical for the named clinical category. These are used for
end-to-end accuracy validation of the engine on physiologically
realistic geometries, not just analytic ground-truth shapes.

Sources for typical dimensions: WoundCarePedia, JWOCN consensus
guidelines, MEASURE wound assessment framework. All are clinical
averages; individual wounds vary widely.

Categories
----------
- diabetic_foot_ulcer: round-ish, moderate depth, often plantar
- venous_leg_ulcer: irregular shape, shallow, gaiter region
- pressure_injury_stage_3: full-thickness skin loss, may be deep
- pressure_injury_stage_4: full-thickness with bone/tendon visible
- surgical_dehiscence: linear, deep, narrow
- traumatic_wound: irregular, variable depth
"""
from __future__ import annotations

import numpy as np

from woundscan.synthesis.analytic_shapes import AnalyticWound, _circular_grid
from woundscan.synthesis.irregular_beds import IrregularConfig, add_perlin_noise


def _elliptical_paraboloid(
    a_cm: float,
    b_cm: float,
    depth_cm: float,
    n_grid: int = 201,
    margin: float = 1.3,
) -> AnalyticWound:
    """Elliptical paraboloid bowl: footprint is ellipse with semi-axes a, b.

    d(x, y) = h * max(0, 1 - (x/a)^2 - (y/b)^2)
    """
    extent = margin * max(a_cm, b_cm)
    x = np.linspace(-extent, extent, n_grid)
    y = np.linspace(-extent, extent, n_grid)
    X, Y = np.meshgrid(x, y, indexing="xy")
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])

    rho2 = (X / a_cm) ** 2 + (Y / b_cm) ** 2
    mask = rho2 <= 1.0
    depth = np.zeros_like(X)
    depth[mask] = depth_cm * (1.0 - rho2[mask])

    from woundscan.geometry.surface_area import compute_surface_area
    from woundscan.geometry.volume import compute_volume

    V = compute_volume(depth, dx, dy, mask=mask)
    S = compute_surface_area(depth, dx, dy, mask=mask)
    A = float(np.pi * a_cm * b_cm)

    return AnalyticWound(
        depth_map=depth,
        mask=mask,
        dx=dx,
        dy=dy,
        true_volume=V,
        true_surface_area=S,
        true_footprint_area=A,
        name=f"elliptical_paraboloid(a={a_cm}, b={b_cm}, h={depth_cm})",
    )


def diabetic_foot_ulcer(
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> AnalyticWound:
    """Typical DFU: round, 2-4cm diameter, 0.5-1.5cm depth.

    Often presents on plantar surface with rolled edges. We model it as a
    circular elliptical paraboloid with mild irregularity.
    """
    rng = rng or np.random.default_rng(seed)
    a = float(rng.uniform(1.0, 2.0))
    b = float(rng.uniform(0.9, 1.1) * a)
    h = float(rng.uniform(0.5, 1.5))
    base = _elliptical_paraboloid(a, b, h, n_grid=201)
    irreg = add_perlin_noise(base, IrregularConfig(amplitude_mm=0.6, seed=seed))
    return AnalyticWound(
        depth_map=irreg.depth_map,
        mask=irreg.mask,
        dx=irreg.dx,
        dy=irreg.dy,
        true_volume=irreg.true_volume,
        true_surface_area=irreg.true_surface_area,
        true_footprint_area=irreg.true_footprint_area,
        name=f"DFU(a={a:.2f},b={b:.2f},h={h:.2f})",
    )


def venous_leg_ulcer(
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> AnalyticWound:
    """VLU: irregular, often elongated, shallow (0.2-0.8cm), gaiter region."""
    rng = rng or np.random.default_rng(seed)
    a = float(rng.uniform(2.0, 4.0))
    b = float(rng.uniform(0.4, 0.6) * a)
    h = float(rng.uniform(0.2, 0.8))
    base = _elliptical_paraboloid(a, b, h, n_grid=251)
    return add_perlin_noise(
        base, IrregularConfig(amplitude_mm=0.8, octaves=5, seed=seed)
    )


def pressure_injury_stage_3(
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> AnalyticWound:
    """Stage 3: full-thickness skin loss; may have undermining (separate)."""
    rng = rng or np.random.default_rng(seed)
    a = float(rng.uniform(2.0, 5.0))
    b = float(rng.uniform(0.7, 1.0) * a)
    h = float(rng.uniform(1.0, 2.5))
    base = _elliptical_paraboloid(a, b, h, n_grid=251)
    return add_perlin_noise(
        base, IrregularConfig(amplitude_mm=1.2, octaves=4, seed=seed)
    )


def pressure_injury_stage_4(
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> AnalyticWound:
    """Stage 4: full-thickness with exposed bone/tendon. Deep, irregular."""
    rng = rng or np.random.default_rng(seed)
    a = float(rng.uniform(3.0, 6.0))
    b = float(rng.uniform(0.7, 1.0) * a)
    h = float(rng.uniform(2.5, 5.0))
    base = _elliptical_paraboloid(a, b, h, n_grid=251)
    return add_perlin_noise(
        base, IrregularConfig(amplitude_mm=2.0, octaves=5, seed=seed)
    )


def surgical_dehiscence(
    length_cm: float | None = None,
    width_cm: float | None = None,
    depth_cm: float | None = None,
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> AnalyticWound:
    """Linear surgical wound: long, narrow, deep at center."""
    rng = rng or np.random.default_rng(seed)
    L = length_cm if length_cm is not None else float(rng.uniform(5.0, 12.0))
    W = width_cm if width_cm is not None else float(rng.uniform(0.8, 2.0))
    h = depth_cm if depth_cm is not None else float(rng.uniform(1.5, 3.0))
    base = _elliptical_paraboloid(L / 2.0, W / 2.0, h, n_grid=301)
    return add_perlin_noise(
        base, IrregularConfig(amplitude_mm=0.5, octaves=3, seed=seed)
    )


def traumatic_wound(
    seed: int = 0,
    rng: np.random.Generator | None = None,
) -> AnalyticWound:
    """Irregular, ragged-edged trauma wound."""
    rng = rng or np.random.default_rng(seed)
    a = float(rng.uniform(2.0, 5.0))
    b = float(rng.uniform(0.5, 1.0) * a)
    h = float(rng.uniform(0.5, 2.5))
    base = _elliptical_paraboloid(a, b, h, n_grid=251)
    return add_perlin_noise(
        base, IrregularConfig(amplitude_mm=1.5, octaves=6, seed=seed)
    )

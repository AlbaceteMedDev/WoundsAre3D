"""Synthetic wound accuracy validation suite.

Per the build brief, runs on every commit and must pass for the engine
to ship. Each test enforces a specific tolerance budget that, if
violated, invalidates downstream accuracy claims.

These are mapped to requirements in docs/regulatory_traceability.md.
"""
from __future__ import annotations

import numpy as np
import pytest

from woundscan.geometry.surface_area import compute_surface_area
from woundscan.geometry.volume import compute_volume
from woundscan.synthesis.analytic_shapes import (
    AnalyticWound,
    cone,
    hemisphere,
    hemispheroid,
    paraboloid,
)
from woundscan.synthesis.irregular_beds import IrregularConfig, add_perlin_noise


pytestmark = pytest.mark.regulatory


def _rel_err(measured: float, truth: float) -> float:
    return abs(measured - truth) / abs(truth)


# REQ-ACC-001: Hemisphere volume <2%
@pytest.mark.parametrize("radius", [0.5, 1.0, 2.5, 5.0])
def test_REQ_ACC_001_hemisphere_volume(radius: float) -> None:
    w = hemisphere(radius=radius, n_grid=301)
    V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
    assert _rel_err(V, w.true_volume) < 0.02, (
        f"hemisphere(r={radius}): V={V:.4f}, truth={w.true_volume:.4f}, "
        f"err={_rel_err(V, w.true_volume):.4%}"
    )


# REQ-ACC-002: Cone volume <1%, surface area <3%
@pytest.mark.parametrize(
    "radius,depth", [(1.0, 0.5), (2.0, 1.0), (3.0, 2.0)]
)
def test_REQ_ACC_002_cone_volume_and_sa(radius: float, depth: float) -> None:
    w = cone(radius=radius, depth_max=depth, n_grid=301)
    V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
    SA = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
    assert _rel_err(V, w.true_volume) < 0.01
    assert _rel_err(SA, w.true_surface_area) < 0.03


# REQ-ACC-003: Paraboloid volume <1%, surface area <5%
@pytest.mark.parametrize("radius,depth", [(1.0, 0.5), (2.0, 1.0), (3.0, 1.5)])
def test_REQ_ACC_003_paraboloid_volume_and_sa(radius: float, depth: float) -> None:
    w = paraboloid(radius=radius, depth_max=depth, n_grid=301)
    V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
    SA = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
    assert _rel_err(V, w.true_volume) < 0.01
    assert _rel_err(SA, w.true_surface_area) < 0.05


# REQ-ACC-004: Oblate hemispheroid (wide, shallow)
def test_REQ_ACC_004_oblate_hemispheroid_wide() -> None:
    w = hemispheroid(semi_axis_horizontal=3.0, depth_max=0.5, n_grid=301)
    V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
    SA = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
    assert _rel_err(V, w.true_volume) < 0.02
    assert _rel_err(SA, w.true_surface_area) < 0.05


# REQ-ACC-005: Irregular bed (Perlin noise) volume <3%, SA <5%
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_REQ_ACC_005_irregular_paraboloid(seed: int) -> None:
    base = paraboloid(radius=2.0, depth_max=1.0, n_grid=251)
    irreg = add_perlin_noise(base, IrregularConfig(amplitude_mm=0.5, seed=seed))
    V = compute_volume(irreg.depth_map, irreg.dx, irreg.dy, mask=irreg.mask)
    SA = compute_surface_area(irreg.depth_map, irreg.dx, irreg.dy, mask=irreg.mask)
    # Truth recomputed numerically, so we compare against the recomputed value
    assert _rel_err(V, irreg.true_volume) < 0.005
    assert _rel_err(SA, irreg.true_surface_area) < 0.005


# REQ-ACC-006: Numerical stability across grid resolutions
def test_REQ_ACC_006_grid_independence() -> None:
    truth = (1.0 / 3.0) * np.pi * 2.0**2 * 1.0
    errs = []
    for n in (101, 201, 401):
        w = cone(radius=2.0, depth_max=1.0, n_grid=n)
        V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
        errs.append(abs(V - truth) / truth)
    # Errors should monotonically decrease (or be already at machine precision)
    assert errs[-1] <= errs[0] + 1e-9
    assert errs[-1] < 0.005

"""Per-morphology accuracy regression suite.

Each test runs the geometry chain on a clinically representative wound
generator. The values asserted are the current best-known regression
targets; if the engine slips outside, CI fails.
"""
from __future__ import annotations

import numpy as np
import pytest

from woundscan.geometry.surface_area import compute_surface_area
from woundscan.geometry.volume import compute_volume
from woundscan.synthesis.clinical_morphologies import (
    diabetic_foot_ulcer,
    pressure_injury_stage_3,
    pressure_injury_stage_4,
    surgical_dehiscence,
    venous_leg_ulcer,
)


pytestmark = pytest.mark.benchmark


def _rel_err(a: float, b: float) -> float:
    return abs(a - b) / abs(b)


@pytest.mark.parametrize(
    "fn,vol_tol,sa_tol",
    [
        (diabetic_foot_ulcer, 0.005, 0.005),
        (venous_leg_ulcer, 0.005, 0.005),
        (pressure_injury_stage_3, 0.005, 0.005),
        (pressure_injury_stage_4, 0.005, 0.005),
        (surgical_dehiscence, 0.005, 0.005),
    ],
)
def test_clinical_morphology_geometry(fn, vol_tol: float, sa_tol: float) -> None:
    w = fn(seed=0)
    V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
    SA = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
    assert _rel_err(V, w.true_volume) < vol_tol
    assert _rel_err(SA, w.true_surface_area) < sa_tol


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_dfu_population_consistency(seed: int) -> None:
    """Across random DFU instances, the geometry chain stays accurate."""
    w = diabetic_foot_ulcer(seed=seed)
    V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
    SA = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
    assert _rel_err(V, w.true_volume) < 0.01
    assert _rel_err(SA, w.true_surface_area) < 0.01

"""Ground truth records for synthetic wound validation.

A `GroundTruth` is the analytic + numeric reference for a synthetic wound,
used as the regression target in the validation harness. Includes the
analytic value (when available) and the numerical reference computed on
a high-resolution grid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from woundscan.synthesis.analytic_shapes import AnalyticWound


@dataclass(frozen=True)
class GroundTruth:
    """Reference values for a synthetic wound, with provenance.

    Attributes
    ----------
    name : str
        Human-readable wound description.
    volume_cm3 : float
        Reference volume.
    surface_area_cm2 : float
        Reference 3D surface area.
    footprint_area_cm2 : float
        Reference 2D opening area.
    analytic : bool
        True if values are closed-form analytic; False if they were
        computed numerically on a fine grid.
    grid_n : int
        For numerical truth, the grid resolution used.
    """

    name: str
    volume_cm3: float
    surface_area_cm2: float
    footprint_area_cm2: float
    analytic: bool
    grid_n: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)


def compute_ground_truth(
    wound: AnalyticWound,
    *,
    analytic: bool = True,
    grid_n: int = 0,
    notes: Optional[tuple[str, ...]] = None,
) -> GroundTruth:
    """Wrap an AnalyticWound's true_* fields into a GroundTruth record."""
    return GroundTruth(
        name=wound.name,
        volume_cm3=float(wound.true_volume),
        surface_area_cm2=float(wound.true_surface_area),
        footprint_area_cm2=float(wound.true_footprint_area),
        analytic=analytic,
        grid_n=grid_n,
        notes=notes or (),
    )


def relative_error(measured: float, truth: float) -> float:
    """|measured - truth| / |truth|, with safe handling of zero truth."""
    if abs(truth) < 1e-12:
        return float("inf") if abs(measured) > 1e-12 else 0.0
    return float(abs(measured - truth) / abs(truth))


def assert_within_tolerance(
    measured: float,
    truth: GroundTruth,
    field_name: str,
    rel_tol: float,
) -> None:
    """Assert that `measured` is within `rel_tol` of `truth.<field_name>`."""
    truth_value = getattr(truth, field_name)
    err = relative_error(measured, truth_value)
    if err > rel_tol:
        raise AssertionError(
            f"{truth.name}: {field_name}={measured:.4f}, "
            f"truth={truth_value:.4f}, err={err:.4%}, "
            f"tolerance={rel_tol:.2%}"
        )


def grid_independence_check(
    generator: callable,  # type: ignore[type-arg]
    grid_resolutions: tuple[int, ...] = (101, 201, 401),
    field: str = "volume_cm3",
    tol: float = 0.005,
) -> bool:
    """Verify that the generator's numerical truth is grid-independent.

    Calls `generator(n_grid=N)` for each resolution and checks that the
    relative variation in `field` across resolutions is below `tol`.
    """
    values = []
    for n in grid_resolutions:
        wound = generator(n_grid=n)
        gt = compute_ground_truth(wound)
        values.append(getattr(gt, field))
    arr = np.array(values)
    spread = (arr.max() - arr.min()) / arr.mean()
    return bool(spread < tol)

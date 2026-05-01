"""Graft sizing with uncertainty.

Formula:
    A_graft = S_3D + 2 * delta * P_eff + 4 * delta^2

where:
- S_3D is 3D wound bed surface area
- P_eff is the effective perimeter
- delta is the IFU-mandated overlap onto periwound tissue

Recommendation uses a 2-sigma upper bound to ensure adequate coverage:

    A_graft_recommended = mean(A_graft) + 2 * std(A_graft)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from woundscan.geometry.uncertainty import UncertaintyResult


@dataclass(frozen=True)
class GraftSizing:
    """Graft sizing result with uncertainty.

    Attributes
    ----------
    point_estimate_cm2 : float
    recommended_cm2 : float
        2-sigma upper bound, what to actually order.
    std_cm2 : float
    ci_95_low_cm2 : float
    ci_95_high_cm2 : float
    overlap_delta_cm : float
    notes : str
    """

    point_estimate_cm2: float
    recommended_cm2: float
    std_cm2: float
    ci_95_low_cm2: float
    ci_95_high_cm2: float
    overlap_delta_cm: float
    notes: str = ""


def compute_graft_size(
    surface_area_uncertainty: UncertaintyResult,
    perimeter_cm: float,
    overlap_delta_cm: float,
    perimeter_uncertainty_cm: float = 0.0,
    *,
    n_samples: int = 1000,
    rng: np.random.Generator | None = None,
) -> GraftSizing:
    """Apply the graft formula to MC samples of S and P, return sizing summary.

    A_graft = S + 2*delta*P + 4*delta^2

    The MC samples for S come from the GP-posterior surface-area
    uncertainty; perimeter is treated as Gaussian with provided std.
    """
    rng = rng or np.random.default_rng(0)
    s_samples = rng.normal(
        loc=surface_area_uncertainty.mean,
        scale=max(surface_area_uncertainty.std, 1e-9),
        size=n_samples,
    )
    p_samples = rng.normal(loc=perimeter_cm, scale=perimeter_uncertainty_cm, size=n_samples)

    a_samples = s_samples + 2.0 * overlap_delta_cm * p_samples + 4.0 * overlap_delta_cm**2
    a_samples = np.maximum(a_samples, 0.0)

    point = float(
        surface_area_uncertainty.mean
        + 2.0 * overlap_delta_cm * perimeter_cm
        + 4.0 * overlap_delta_cm**2
    )
    std = float(np.std(a_samples, ddof=1))
    recommended = point + 2.0 * std

    return GraftSizing(
        point_estimate_cm2=point,
        recommended_cm2=recommended,
        std_cm2=std,
        ci_95_low_cm2=float(np.percentile(a_samples, 2.5)),
        ci_95_high_cm2=float(np.percentile(a_samples, 97.5)),
        overlap_delta_cm=overlap_delta_cm,
        notes="A_graft = S + 2*delta*P + 4*delta^2; recommended = mean + 2*std",
    )

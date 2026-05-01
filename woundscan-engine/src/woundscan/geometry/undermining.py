"""Undermining: lateral wound extension beneath intact periwound skin.

The clinician probes radially under the skin from the wound edge; each
measurement is (clock_position, depth_mm). We fit a cubic-periodic spline
through the (theta, depth) pairs and compute the additional volume and
surface area contributed by the undermined cavity.

Model: undermined region is a horizontal annulus around the wound opening
of width u(theta), where u is the radial extent of undermining at clock
position theta. Annulus depth equals the wound bed depth at that azimuth
(approximation; refined by sidewall fitting downstream).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.interpolate import CubicSpline


@dataclass(frozen=True)
class UnderminingMeasurement:
    """A single radial undermining measurement.

    Attributes
    ----------
    clock_position_hours : float
        Clinical clock notation (1.0..12.0). 12 is at the head/north of
        the wound; counts clockwise.
    radial_extent_mm : float
        Probe insertion depth radially under the skin from wound edge.
    """

    clock_position_hours: float
    radial_extent_mm: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.clock_position_hours <= 12.0):
            raise ValueError(
                f"clock_position_hours must be in [0, 12], got {self.clock_position_hours}"
            )
        if self.radial_extent_mm < 0:
            raise ValueError("radial_extent_mm must be nonnegative")


def _clock_to_theta(clock_hours: float) -> float:
    """Convert clinical clock notation to math-standard angle in radians.

    12 o'clock -> +y axis -> theta = pi/2.
    3 o'clock -> +x axis -> theta = 0.
    Clockwise (clinical convention) -> negative theta direction.
    """
    return np.pi / 2.0 - (clock_hours / 12.0) * 2.0 * np.pi


def integrate_undermining(
    measurements: Sequence[UnderminingMeasurement],
    wound_bed_depth_at_edge_mm: float = 0.0,
) -> tuple[float, float]:
    """Compute the volume (mm^3) and surface area (mm^2) of the undermined annulus.

    Approximation: the undermined region at azimuth theta extends u(theta)
    radially, with vertical depth equal to the wound bed depth at the
    nearest edge point. We integrate the wedge volume:

        V_under = integral_0^{2pi} (1/2) * u(theta)^2 * h(theta) dtheta

    where h is the bed depth at the edge. For surface area, we add the
    horizontal annulus floor and ceiling contributions:

        S_under = integral_0^{2pi} u(theta) * h(theta) dtheta * 2

    (top + bottom of the annulus). Sidewall lateral surface is added by the
    sidewall fitting module downstream.

    Returns
    -------
    (volume_mm3, surface_area_mm2)
    """
    if len(measurements) < 3:
        if not measurements:
            return 0.0, 0.0
        u_mean = float(np.mean([m.radial_extent_mm for m in measurements]))
        h = wound_bed_depth_at_edge_mm
        # Approximate as a uniform annulus
        return float(np.pi * u_mean**2 * h), float(2.0 * np.pi * u_mean * h * 2.0)

    thetas = np.array(
        [_clock_to_theta(m.clock_position_hours) for m in measurements]
    )
    extents = np.array([m.radial_extent_mm for m in measurements])

    order = np.argsort(thetas)
    thetas = thetas[order]
    extents = extents[order]

    # Make periodic by appending wraparound
    thetas_p = np.concatenate([thetas, [thetas[0] + 2.0 * np.pi]])
    extents_p = np.concatenate([extents, [extents[0]]])

    spline = CubicSpline(thetas_p, extents_p, bc_type="periodic")

    n_int = 360
    theta_grid = np.linspace(thetas_p[0], thetas_p[-1], n_int, endpoint=False)
    u_theta = np.maximum(0.0, spline(theta_grid))
    h = wound_bed_depth_at_edge_mm

    dtheta = 2.0 * np.pi / n_int
    V = float(0.5 * np.sum(u_theta**2 * h) * dtheta)
    S = float(2.0 * np.sum(u_theta * h) * dtheta)
    return V, S

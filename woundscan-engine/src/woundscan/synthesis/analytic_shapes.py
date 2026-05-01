"""
Analytic wound shape generators for validation.

Each shape produces a depth field on a regular grid plus the analytically
known volume, surface area, and footprint area. These are the ground-truth
references used to validate the geometry module against closed-form solutions.

Conventions
-----------
- Coordinates: numpy convention. depth_map[i, j] = d(y_i, x_j).
  Axis 0 is y (row), axis 1 is x (column).
- Depth: positive going into the wound. Skin level is z=0; wound bed is at
  z = d(x, y) below skin.
- Origin: center of the wound footprint, at (0, 0).
- Units: configurable. All shapes expect consistent units throughout
  (e.g., everything in cm).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AnalyticWound:
    """A synthetic wound with a depth field and analytically known ground truth.

    Attributes
    ----------
    depth_map : np.ndarray
        2D depth field of shape (Ny, Nx). Outside the wound footprint, depth
        is 0. depth_map[i, j] is the depth at (y_i, x_j) in the same units
        as dx and dy.
    mask : np.ndarray
        Boolean array of shape (Ny, Nx). True where the wound footprint is
        present.
    dx, dy : float
        Grid spacings along x (axis 1) and y (axis 0).
    true_volume : float
        Analytically known volume.
    true_surface_area : float
        Analytically known 3D surface area of the wound bed.
    true_footprint_area : float
        Analytically known 2D opening area at skin level.
    name : str
        Human-readable description for logging and test output.
    """

    depth_map: np.ndarray
    mask: np.ndarray
    dx: float
    dy: float
    true_volume: float
    true_surface_area: float
    true_footprint_area: float
    name: str


def _circular_grid(
    extent: float, n_grid: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Build a square grid of half-width `extent` with n_grid points per side."""
    x = np.linspace(-extent, extent, n_grid)
    y = np.linspace(-extent, extent, n_grid)
    X, Y = np.meshgrid(x, y, indexing="xy")
    dx = float(x[1] - x[0])
    dy = float(y[1] - y[0])
    return X, Y, np.zeros_like(X), dx, dy


def hemisphere(
    radius: float,
    n_grid: int = 201,
    margin: float = 1.2,
) -> AnalyticWound:
    """Hemispherical wound bowl: circular opening at skin level, depth = R at center.

    The wound bed is the lower half of a sphere of radius R. Surface area
    integrand has a singularity at r=R (vertical tangent), so numerical
    accuracy on this shape requires fine grids near the boundary.

    Parameters
    ----------
    radius : float
        Hemisphere radius R, in the chosen units (e.g., cm).
    n_grid : int
        Number of grid points per axis. Higher = more accurate, slower.
    margin : float
        Bounding box half-width = margin * radius. Must be > 1.0 so the
        wound boundary is interior to the grid.

    Analytic ground truth
    ---------------------
    Volume = (2/3) pi R^3
    Surface area = 2 pi R^2  (curved bowl only; the rim disk is the opening)
    Footprint = pi R^2
    """
    if margin <= 1.0:
        raise ValueError(f"margin must be > 1.0, got {margin}")
    X, Y, depth, dx, dy = _circular_grid(margin * radius, n_grid)
    r2 = X**2 + Y**2
    mask = r2 <= radius**2
    depth[mask] = np.sqrt(np.maximum(0.0, radius**2 - r2[mask]))
    return AnalyticWound(
        depth_map=depth,
        mask=mask,
        dx=dx,
        dy=dy,
        true_volume=(2.0 / 3.0) * np.pi * radius**3,
        true_surface_area=2.0 * np.pi * radius**2,
        true_footprint_area=np.pi * radius**2,
        name=f"hemisphere(r={radius})",
    )


def cone(
    radius: float,
    depth_max: float,
    n_grid: int = 201,
    margin: float = 1.2,
) -> AnalyticWound:
    """Inverted cone wound: linear depth profile, apex at the bottom center.

    d(r) = h * (1 - r/R) for r <= R.

    Cone has bounded slope (|grad d| = h/R everywhere inside), making it the
    cleanest case for numerical surface-area integration.

    Parameters
    ----------
    radius : float
        Cone opening radius R.
    depth_max : float
        Apex depth h.

    Analytic ground truth
    ---------------------
    Volume = (1/3) pi R^2 h
    Surface area = pi R sqrt(R^2 + h^2)  (lateral cone surface)
    Footprint = pi R^2
    """
    if radius <= 0 or depth_max <= 0:
        raise ValueError("radius and depth_max must be positive")
    X, Y, depth, dx, dy = _circular_grid(margin * radius, n_grid)
    r = np.sqrt(X**2 + Y**2)
    mask = r <= radius
    depth[mask] = depth_max * (1.0 - r[mask] / radius)
    return AnalyticWound(
        depth_map=depth,
        mask=mask,
        dx=dx,
        dy=dy,
        true_volume=(1.0 / 3.0) * np.pi * radius**2 * depth_max,
        true_surface_area=np.pi * radius * np.sqrt(radius**2 + depth_max**2),
        true_footprint_area=np.pi * radius**2,
        name=f"cone(r={radius}, h={depth_max})",
    )


def paraboloid(
    radius: float,
    depth_max: float,
    n_grid: int = 201,
    margin: float = 1.2,
) -> AnalyticWound:
    """Truncated paraboloid wound bed.

    d(r) = h * (1 - r^2/R^2) for r <= R.

    Slope at r=R is 2h/R (bounded). Realistic representation of many
    chronic wounds.

    Parameters
    ----------
    radius : float
        Opening radius R.
    depth_max : float
        Center depth h.

    Analytic ground truth
    ---------------------
    Volume = (pi/2) R^2 h
    Surface area = (pi R^4 / (6 h^2)) * [(1 + 4 h^2 / R^2)^(3/2) - 1]
    Footprint = pi R^2

    Limit check
    -----------
    As h -> 0, S -> pi R^2 (flat disk).
    """
    if radius <= 0 or depth_max <= 0:
        raise ValueError("radius and depth_max must be positive")
    X, Y, depth, dx, dy = _circular_grid(margin * radius, n_grid)
    r2 = X**2 + Y**2
    mask = r2 <= radius**2
    depth[mask] = depth_max * (1.0 - r2[mask] / radius**2)

    R = radius
    h = depth_max
    S = (np.pi * R**4 / (6.0 * h**2)) * ((1.0 + 4.0 * h**2 / R**2) ** 1.5 - 1.0)

    return AnalyticWound(
        depth_map=depth,
        mask=mask,
        dx=dx,
        dy=dy,
        true_volume=0.5 * np.pi * radius**2 * depth_max,
        true_surface_area=S,
        true_footprint_area=np.pi * radius**2,
        name=f"paraboloid(r={radius}, h={depth_max})",
    )


def hemispheroid(
    semi_axis_horizontal: float,
    depth_max: float,
    n_grid: int = 201,
    margin: float = 1.2,
) -> AnalyticWound:
    """Half spheroid: oblate (a > c), prolate (a < c), or sphere (a = c).

    d(r) = c * sqrt(1 - r^2/a^2) for r <= a, where a = semi_axis_horizontal.
    The wound footprint is a circle of radius a; the bed is the lower half
    of an axisymmetric ellipsoid with vertical semi-axis c.

    Surface area formulas from standard ellipsoid geometry.

    Analytic ground truth
    ---------------------
    Volume = (2/3) pi a^2 c

    Surface area (curved bowl only):
      Oblate (a > c):
        e = sqrt(1 - c^2/a^2)
        S_curved_full = 2 pi a^2 + (pi c^2 / e) ln((1 + e) / (1 - e))
        S_bowl = S_curved_full / 2
      Prolate (a < c):
        e' = sqrt(1 - a^2/c^2)
        S_curved_full = 2 pi a^2 + 2 pi a c arcsin(e') / e'
        S_bowl = S_curved_full / 2
      Sphere (a = c):
        S_bowl = 2 pi a^2

    Footprint = pi a^2
    """
    if semi_axis_horizontal <= 0 or depth_max <= 0:
        raise ValueError("semi_axis_horizontal and depth_max must be positive")
    a = semi_axis_horizontal
    c = depth_max

    X, Y, depth, dx, dy = _circular_grid(margin * a, n_grid)
    r2 = X**2 + Y**2
    mask = r2 <= a**2
    depth[mask] = c * np.sqrt(np.maximum(0.0, 1.0 - r2[mask] / a**2))

    if abs(a - c) < 1e-9:
        S = 2.0 * np.pi * a**2
    elif a > c:
        e = np.sqrt(1.0 - c**2 / a**2)
        S_full = 2.0 * np.pi * a**2 + (np.pi * c**2 / e) * np.log((1.0 + e) / (1.0 - e))
        S = S_full / 2.0
    else:
        ep = np.sqrt(1.0 - a**2 / c**2)
        S_full = 2.0 * np.pi * a**2 + 2.0 * np.pi * a * c * np.arcsin(ep) / ep
        S = S_full / 2.0

    return AnalyticWound(
        depth_map=depth,
        mask=mask,
        dx=dx,
        dy=dy,
        true_volume=(2.0 / 3.0) * np.pi * a**2 * c,
        true_surface_area=S,
        true_footprint_area=np.pi * a**2,
        name=f"hemispheroid(a={a}, c={c})",
    )


def flat_disk(
    radius: float,
    depth: float,
    n_grid: int = 201,
    margin: float = 1.2,
) -> AnalyticWound:
    """Cylindrical pit: flat bottom, vertical walls.

    Volume = pi R^2 h. Used primarily for volume validation.

    The vertical walls have infinite slope, which the gradient-integral
    method cannot capture. Surface area for this shape is therefore
    reported as bottom-only (pi R^2), and the gradient method will
    underestimate it. Real wounds have sloped walls; this shape is a
    boundary case for the volume integral, not a realistic surface model.
    """
    X, Y, d, dx, dy = _circular_grid(margin * radius, n_grid)
    r2 = X**2 + Y**2
    mask = r2 <= radius**2
    d[mask] = depth
    return AnalyticWound(
        depth_map=d,
        mask=mask,
        dx=dx,
        dy=dy,
        true_volume=np.pi * radius**2 * depth,
        true_surface_area=np.pi * radius**2,
        true_footprint_area=np.pi * radius**2,
        name=f"flat_disk(r={radius}, d={depth})",
    )

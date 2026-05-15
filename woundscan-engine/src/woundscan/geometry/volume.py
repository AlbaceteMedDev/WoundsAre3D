"""
Wound volume computation via numerical integration of the depth field.

V = integral over wound footprint of d(x, y) dA

Discretized using composite Simpson's rule along both axes
(scipy.integrate.simpson). Simpson's rule is fourth-order accurate for
smooth integrands and is the standard choice when grid spacing is fine
enough to resolve the wound bed topography.
"""

from __future__ import annotations

import numpy as np
from scipy import integrate


def compute_volume(
    depth_map: np.ndarray,
    dx: float,
    dy: float,
    mask: np.ndarray | None = None,
) -> float:
    """Compute wound volume from a regularly gridded depth field.

    V = integral over R of d(x, y) dx dy

    where R is the wound footprint. Outside the wound, depth must be zero
    (or use the `mask` parameter to restrict integration).

    Parameters
    ----------
    depth_map : np.ndarray
        2D array of shape (Ny, Nx), nonnegative. Element [i, j] is the
        depth at grid point (y_i, x_j) in cm.
    dx : float
        Grid spacing along x (axis 1), in cm. Must be positive.
    dy : float
        Grid spacing along y (axis 0), in cm. Must be positive.
    mask : np.ndarray, optional
        Boolean array of shape (Ny, Nx). If provided, depth is treated as
        zero outside the mask.

    Returns
    -------
    volume : float
        Wound volume in cm^3.

    Raises
    ------
    ValueError
        If inputs violate dimensionality, sign, or shape constraints.
    """
    if depth_map.ndim != 2:
        raise ValueError(f"depth_map must be 2D, got shape {depth_map.shape}")
    if depth_map.shape[0] < 3 or depth_map.shape[1] < 3:
        raise ValueError(
            "depth_map needs at least 3 points per axis for Simpson's rule, "
            f"got {depth_map.shape}"
        )
    if dx <= 0 or dy <= 0:
        raise ValueError(f"Grid spacings must be positive, got dx={dx}, dy={dy}")
    if np.any(depth_map < 0):
        raise ValueError("depth_map contains negative values")

    d = depth_map
    if mask is not None:
        if mask.shape != depth_map.shape:
            raise ValueError(
                f"mask shape {mask.shape} doesn't match depth_map shape " f"{depth_map.shape}"
            )
        d = np.where(mask, depth_map, 0.0)

    # Composite Simpson's rule, applied along x then along y.
    inner = integrate.simpson(d, dx=dx, axis=1)
    volume = integrate.simpson(inner, dx=dy)
    return float(volume)


def compute_volume_trapezoid(
    depth_map: np.ndarray,
    dx: float,
    dy: float,
    mask: np.ndarray | None = None,
) -> float:
    """Trapezoidal-rule volume integration.

    Slightly less accurate than Simpson's rule on smooth depth fields, but
    more robust on noisy data and when grid sizes are not amenable to
    Simpson's rule (which prefers odd numbers of points per axis).
    """
    if depth_map.ndim != 2:
        raise ValueError(f"depth_map must be 2D, got shape {depth_map.shape}")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"Grid spacings must be positive, got dx={dx}, dy={dy}")

    d = depth_map
    if mask is not None:
        d = np.where(mask, depth_map, 0.0)

    inner = np.trapz(d, dx=dx, axis=1)
    volume = np.trapz(inner, dx=dy)
    return float(volume)


def compute_mean_depth(
    depth_map: np.ndarray,
    dx: float,
    dy: float,
    mask: np.ndarray,
) -> float:
    """Compute the area-weighted mean depth within the masked footprint.

    mean_depth = volume / footprint_area

    Useful for documentation: gives the "equivalent uniform depth" of the
    wound, which is the depth a flat-bottomed wound of the same volume and
    footprint would have.
    """
    volume = compute_volume(depth_map, dx, dy, mask=mask)
    footprint_area = float(np.sum(mask) * dx * dy)
    if footprint_area <= 0:
        raise ValueError("mask has zero area")
    return volume / footprint_area

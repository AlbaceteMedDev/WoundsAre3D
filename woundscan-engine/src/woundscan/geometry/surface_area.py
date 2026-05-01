"""
3D wound bed surface area via gradient integral.

For a depth field d(x, y), the 3D surface area of the wound bed is:

    S = integral over R of sqrt(1 + (d/dx)^2 + (d/dy)^2) dA

The integrand is the Jacobian of the parameterization (x, y) -> (x, y, d(x, y)).

Gradients are computed by central differences (numpy.gradient), which uses
forward/backward differences at array boundaries. Surface integral uses
composite Simpson's rule.

Limitations
-----------
The gradient method assumes the wound bed is a single-valued function of
(x, y) - one depth per skin-level point. It does not capture undermining
(where the wound extends beneath the skin lateral to the opening), tunnels
(narrow extensions), or vertical sidewalls (which have infinite slope and
would cause the integrand to diverge).

For wounds with these features, supplemental physical measurements are
required and are added to the gradient-integral surface area downstream.
This module computes only the open-bowl portion.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import integrate


def compute_surface_area(
    depth_map: np.ndarray,
    dx: float,
    dy: float,
    mask: Optional[np.ndarray] = None,
) -> float:
    """3D surface area of the wound bed via gradient integral.

    Parameters
    ----------
    depth_map : np.ndarray
        2D depth field of shape (Ny, Nx) in cm.
    dx : float
        Grid spacing along x (axis 1) in cm. Must be positive.
    dy : float
        Grid spacing along y (axis 0) in cm. Must be positive.
    mask : np.ndarray, optional
        Boolean array of shape (Ny, Nx). If provided, the integrand is
        zeroed outside the mask, restricting integration to the wound
        footprint.

    Returns
    -------
    surface_area : float
        Wound bed 3D surface area in cm^2.

    Notes
    -----
    For wounds with no depth variation (constant depth, including zero),
    surface area equals the integration domain area (or footprint area
    when masked). This matches physical intuition: a flat wound bed has
    surface area equal to its footprint.
    """
    if depth_map.ndim != 2:
        raise ValueError(f"depth_map must be 2D, got shape {depth_map.shape}")
    if depth_map.shape[0] < 3 or depth_map.shape[1] < 3:
        raise ValueError(
            "depth_map needs at least 3 points per axis, "
            f"got {depth_map.shape}"
        )
    if dx <= 0 or dy <= 0:
        raise ValueError(f"Grid spacings must be positive, got dx={dx}, dy={dy}")

    # np.gradient on a 2D array with two spacing args returns gradients in
    # axis order: axis 0 first, then axis 1. With axis 0 = y and axis 1 = x:
    # np.gradient(d, dy, dx) returns [dd/dy, dd/dx].
    gy, gx = np.gradient(depth_map, dy, dx)

    integrand = np.sqrt(1.0 + gx**2 + gy**2)

    if mask is not None:
        if mask.shape != depth_map.shape:
            raise ValueError(
                f"mask shape {mask.shape} doesn't match depth_map shape "
                f"{depth_map.shape}"
            )
        integrand = np.where(mask, integrand, 0.0)

    inner = integrate.simpson(integrand, dx=dx, axis=1)
    surface_area = integrate.simpson(inner, dx=dy)
    return float(surface_area)


def compute_footprint_area(mask: np.ndarray, dx: float, dy: float) -> float:
    """Compute the 2D opening area at skin level from a wound footprint mask.

    This is the area CMS-style L*W estimation approximates and what most
    EHRs record as "wound surface area." Use compute_surface_area for the
    3D surface that skin substitutes actually need to cover.
    """
    if mask.ndim != 2:
        raise ValueError(f"mask must be 2D, got shape {mask.shape}")
    return float(np.sum(mask) * dx * dy)


def compute_perimeter(mask: np.ndarray, dx: float, dy: float) -> float:
    """Estimate wound perimeter at skin level from a binary footprint mask.

    Uses the marching-squares contour from scikit-image when available;
    falls back to a pixel-edge counting approximation otherwise.

    Parameters
    ----------
    mask : np.ndarray
        Boolean wound footprint mask of shape (Ny, Nx).
    dx, dy : float
        Grid spacings in cm.

    Returns
    -------
    perimeter : float
        Wound perimeter in cm.
    """
    if mask.ndim != 2:
        raise ValueError(f"mask must be 2D, got shape {mask.shape}")
    if abs(dx - dy) > 1e-9:
        # marching-squares assumes square pixels. For non-square grids, we
        # still compute on the index grid and apply a single scale, but warn.
        # A more rigorous treatment would resample to a square grid first.
        pass

    try:
        from skimage import measure

        contours = measure.find_contours(mask.astype(float), level=0.5)
        if not contours:
            return 0.0
        # Sum perimeter of all contours (handles disconnected/holed regions).
        # find_contours returns (row, col) coordinates; convert to physical units.
        total = 0.0
        for contour in contours:
            rows = contour[:, 0] * dy
            cols = contour[:, 1] * dx
            diffs = np.sqrt(np.diff(rows) ** 2 + np.diff(cols) ** 2)
            total += float(np.sum(diffs))
        return total
    except ImportError:
        # Fallback: count boundary pixels and multiply by mean of dx, dy.
        # Less accurate but works without scikit-image.
        from scipy import ndimage

        eroded = ndimage.binary_erosion(mask)
        boundary = mask & ~eroded
        return float(np.sum(boundary) * 0.5 * (dx + dy))

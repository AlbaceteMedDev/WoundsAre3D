"""Perimeter computation from a clinician-annotated polygon (mm coordinates)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def compute_perimeter_polygon(vertices_mm: Sequence[tuple[float, float]]) -> float:
    """Polygon perimeter in mm. Vertices are (x, y) in mm; polygon is closed.

    The clinician traces the wound boundary in the iOS app; the resulting
    polygon is what we use for the perimeter term in the graft sizing
    formula. This is more accurate than marching-squares contour finding
    because the clinician annotation has subpixel precision and respects
    the actual anatomic boundary rather than ML segmentation artifacts.
    """
    pts = np.asarray(vertices_mm, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"vertices_mm must be (N, 2), got {pts.shape}")
    if pts.shape[0] < 3:
        raise ValueError(f"polygon needs at least 3 vertices, got {pts.shape[0]}")

    closed = np.vstack([pts, pts[:1]])
    deltas = np.diff(closed, axis=0)
    return float(np.sum(np.hypot(deltas[:, 0], deltas[:, 1])))


def polygon_area_mm2(vertices_mm: Sequence[tuple[float, float]]) -> float:
    """Signed polygon area via shoelace formula. Returns absolute value in mm^2."""
    pts = np.asarray(vertices_mm, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"vertices_mm must be (N, 2), got {pts.shape}")
    if pts.shape[0] < 3:
        raise ValueError("polygon needs at least 3 vertices")
    x = pts[:, 0]
    y = pts[:, 1]
    return float(0.5 * np.abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def polygon_to_mask(
    vertices_mm: Sequence[tuple[float, float]],
    grid_origin_mm: tuple[float, float],
    dx_mm: float,
    dy_mm: float,
    shape: tuple[int, int],
) -> np.ndarray:
    """Rasterize a clinician polygon to a boolean mask aligned with the depth grid.

    Parameters
    ----------
    vertices_mm : (N, 2)
        Polygon vertices in mm in the same coordinate frame as the grid.
    grid_origin_mm : (x0, y0)
        Physical mm coordinates of grid index (0, 0).
    dx_mm, dy_mm : float
        Grid spacing in mm.
    shape : (Ny, Nx)
        Output mask shape.
    """
    from skimage.draw import polygon as sk_polygon

    pts = np.asarray(vertices_mm, dtype=float)
    rows = (pts[:, 1] - grid_origin_mm[1]) / dy_mm
    cols = (pts[:, 0] - grid_origin_mm[0]) / dx_mm
    mask = np.zeros(shape, dtype=bool)
    rr, cc = sk_polygon(rows, cols, shape=shape)
    mask[rr, cc] = True
    return mask

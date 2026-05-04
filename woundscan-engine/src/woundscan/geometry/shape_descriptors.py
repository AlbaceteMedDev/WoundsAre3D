"""Wound shape descriptors: circularity, irregularity, aspect ratio, convexity.

These are dimensionless features used in the per-measurement provenance
record and in temporal trajectory analysis. They are NOT used in the
clinical decision logic but inform clinicians about wound morphology.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ShapeDescriptors:
    """Dimensionless shape descriptors of a wound footprint.

    All in [0, 1] except aspect_ratio (>= 1).
    """

    circularity: float
    irregularity: float
    aspect_ratio: float
    convexity: float
    elongation: float


def compute_circularity(area_mm2: float, perimeter_mm: float) -> float:
    """Polsby-Popper compactness: 4*pi*A / P^2. 1.0 = perfect circle, 0 = irregular."""
    if perimeter_mm <= 0 or area_mm2 < 0:
        return 0.0
    c = 4.0 * np.pi * area_mm2 / (perimeter_mm**2)
    return float(min(1.0, c))


def compute_irregularity(area_mm2: float, perimeter_mm: float) -> float:
    """1 - circularity. Useful for trajectory monitoring of healing."""
    return 1.0 - compute_circularity(area_mm2, perimeter_mm)


def compute_aspect_ratio(vertices_mm: Sequence[tuple[float, float]]) -> float:
    """Ratio of major to minor axis of the minimum-area enclosing ellipse.

    Uses PCA on the polygon vertices.
    """
    pts = np.asarray(vertices_mm, dtype=float)
    if pts.shape[0] < 2:
        return 1.0
    centered = pts - pts.mean(axis=0)
    _, s, _ = np.linalg.svd(centered, full_matrices=False)
    if s[1] < 1e-9:
        return float("inf")
    return float(s[0] / s[1])


def compute_convexity(vertices_mm: Sequence[tuple[float, float]]) -> float:
    """Ratio of polygon area to convex hull area. 1.0 = convex; lower = irregular."""
    from scipy.spatial import ConvexHull

    from woundscan.geometry.perimeter import polygon_area_mm2

    pts = np.asarray(vertices_mm, dtype=float)
    if pts.shape[0] < 3:
        return 1.0
    try:
        hull = ConvexHull(pts)
    except Exception:
        return 1.0
    poly_area = polygon_area_mm2(vertices_mm)
    hull_area = float(hull.volume)  # 'volume' is 2D area for 2D points
    if hull_area <= 0:
        return 1.0
    return float(min(1.0, poly_area / hull_area))


def compute_elongation(vertices_mm: Sequence[tuple[float, float]]) -> float:
    """1 - 1/aspect_ratio. Maps [1, inf) to [0, 1)."""
    ar = compute_aspect_ratio(vertices_mm)
    if not np.isfinite(ar):
        return 1.0
    return float(1.0 - 1.0 / ar)


def compute_shape_descriptors(
    vertices_mm: Sequence[tuple[float, float]],
    area_mm2: float | None = None,
    perimeter_mm: float | None = None,
) -> ShapeDescriptors:
    """Compute all shape descriptors. Area and perimeter computed if not provided."""
    from woundscan.geometry.perimeter import (
        compute_perimeter_polygon,
        polygon_area_mm2,
    )

    if area_mm2 is None:
        area_mm2 = polygon_area_mm2(vertices_mm)
    if perimeter_mm is None:
        perimeter_mm = compute_perimeter_polygon(vertices_mm)

    return ShapeDescriptors(
        circularity=compute_circularity(area_mm2, perimeter_mm),
        irregularity=compute_irregularity(area_mm2, perimeter_mm),
        aspect_ratio=compute_aspect_ratio(vertices_mm),
        convexity=compute_convexity(vertices_mm),
        elongation=compute_elongation(vertices_mm),
    )

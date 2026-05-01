"""Geometry: validated 3D math for wound volume, surface area, perimeter."""
from __future__ import annotations

from woundscan.geometry.perimeter import compute_perimeter_polygon
from woundscan.geometry.shape_descriptors import (
    compute_circularity,
    compute_irregularity,
    compute_shape_descriptors,
)
from woundscan.geometry.surface_area import (
    compute_footprint_area,
    compute_perimeter,
    compute_surface_area,
)
from woundscan.geometry.uncertainty import (
    UncertaintyResult,
    compute_surface_area_with_uncertainty,
    compute_volume_with_uncertainty,
)
from woundscan.geometry.undermining import (
    UnderminingMeasurement,
    integrate_undermining,
)
from woundscan.geometry.volume import (
    compute_mean_depth,
    compute_volume,
    compute_volume_trapezoid,
)

__all__ = [
    "UncertaintyResult",
    "UnderminingMeasurement",
    "compute_circularity",
    "compute_footprint_area",
    "compute_irregularity",
    "compute_mean_depth",
    "compute_perimeter",
    "compute_perimeter_polygon",
    "compute_shape_descriptors",
    "compute_surface_area",
    "compute_surface_area_with_uncertainty",
    "compute_volume",
    "compute_volume_trapezoid",
    "compute_volume_with_uncertainty",
    "integrate_undermining",
]

"""Tests for polygon-based perimeter and rasterization."""

import numpy as np
import pytest

from woundscan.geometry.perimeter import (
    compute_perimeter_polygon,
    polygon_area_mm2,
    polygon_to_mask,
)


def _circle_polygon(r: float, n: int) -> list[tuple[float, float]]:
    return [(r * np.cos(2 * np.pi * i / n), r * np.sin(2 * np.pi * i / n)) for i in range(n)]


class TestPolygonPerimeter:
    def test_unit_square_perimeter(self):
        sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert compute_perimeter_polygon(sq) == pytest.approx(4.0)

    def test_unit_square_area(self):
        sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        assert polygon_area_mm2(sq) == pytest.approx(1.0)

    def test_circle_perimeter_converges(self):
        truth = 2.0 * np.pi * 5.0
        p100 = compute_perimeter_polygon(_circle_polygon(5.0, 100))
        p1000 = compute_perimeter_polygon(_circle_polygon(5.0, 1000))
        assert abs(p100 - truth) < 0.05
        assert abs(p1000 - truth) < 0.001

    def test_too_few_vertices_rejected(self):
        with pytest.raises(ValueError):
            compute_perimeter_polygon([(0.0, 0.0), (1.0, 0.0)])


class TestPolygonRasterization:
    def test_square_mask_count(self):
        sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
        mask = polygon_to_mask(sq, grid_origin_mm=(-1, -1), dx_mm=1.0, dy_mm=1.0, shape=(12, 12))
        assert mask.shape == (12, 12)
        # Approximately 100 cells inside a 10x10 region (with edge effects)
        assert 80 < int(mask.sum()) <= 121

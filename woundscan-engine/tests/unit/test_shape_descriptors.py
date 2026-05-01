"""Tests for shape descriptors."""

import numpy as np
import pytest

from woundscan.geometry.shape_descriptors import (
    compute_aspect_ratio,
    compute_circularity,
    compute_convexity,
    compute_irregularity,
    compute_shape_descriptors,
)


def _circle(r: float, n: int) -> list[tuple[float, float]]:
    return [(r * np.cos(2 * np.pi * i / n), r * np.sin(2 * np.pi * i / n)) for i in range(n)]


def _ellipse(a: float, b: float, n: int) -> list[tuple[float, float]]:
    return [(a * np.cos(2 * np.pi * i / n), b * np.sin(2 * np.pi * i / n)) for i in range(n)]


class TestCircularity:
    def test_circle_is_circular(self):
        circle = _circle(2.0, 200)
        from woundscan.geometry.perimeter import compute_perimeter_polygon, polygon_area_mm2

        c = compute_circularity(polygon_area_mm2(circle), compute_perimeter_polygon(circle))
        assert c > 0.99

    def test_square_circularity(self):
        sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        c = compute_circularity(area_mm2=1.0, perimeter_mm=4.0)
        # 4*pi*1/16 ≈ 0.785
        assert abs(c - 0.7854) < 0.001

    def test_irregularity_complement(self):
        c = compute_circularity(area_mm2=1.0, perimeter_mm=4.0)
        i = compute_irregularity(area_mm2=1.0, perimeter_mm=4.0)
        assert abs(c + i - 1.0) < 1e-6


class TestAspectRatio:
    def test_circle_aspect_one(self):
        circle = _circle(2.0, 100)
        assert abs(compute_aspect_ratio(circle) - 1.0) < 0.01

    def test_2to1_ellipse(self):
        ell = _ellipse(2.0, 1.0, 100)
        assert abs(compute_aspect_ratio(ell) - 2.0) < 0.05


class TestConvexity:
    def test_circle_convex(self):
        c = compute_convexity(_circle(2.0, 100))
        assert c > 0.99


class TestShapeDescriptors:
    def test_full_descriptors(self):
        sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        d = compute_shape_descriptors(sq)
        assert 0 < d.circularity < 1
        assert d.convexity > 0.95

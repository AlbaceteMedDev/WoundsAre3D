"""Tests for undermining integration."""
import numpy as np
import pytest

from woundscan.geometry.undermining import (
    UnderminingMeasurement,
    integrate_undermining,
)


class TestUndermining:
    def test_zero_extents_zero_volume(self):
        meas = [
            UnderminingMeasurement(clock_position_hours=t, radial_extent_mm=0.0)
            for t in (12.0, 3.0, 6.0, 9.0)
        ]
        V, S = integrate_undermining(meas, wound_bed_depth_at_edge_mm=10.0)
        assert V == pytest.approx(0.0)
        assert S == pytest.approx(0.0)

    def test_uniform_extent_matches_annulus(self):
        # For a uniform u(theta) = u0 with bed depth h, the annulus volume
        # should be approx pi * u0^2 * h.
        u0 = 5.0
        h = 8.0
        meas = [
            UnderminingMeasurement(clock_position_hours=t, radial_extent_mm=u0)
            for t in (12.0, 3.0, 6.0, 9.0, 1.0, 5.0)
        ]
        V, S = integrate_undermining(meas, wound_bed_depth_at_edge_mm=h)
        truth_V = np.pi * u0**2 * h
        assert abs(V - truth_V) / truth_V < 0.05
        # S = top + bottom = 2 * 2 pi u0 h = 4 pi u0 h
        truth_S = 4.0 * np.pi * u0 * h
        assert abs(S - truth_S) / truth_S < 0.05

    def test_no_measurements_returns_zero(self):
        V, S = integrate_undermining([], wound_bed_depth_at_edge_mm=5.0)
        assert V == 0.0 and S == 0.0

    def test_invalid_clock_rejected(self):
        with pytest.raises(ValueError):
            UnderminingMeasurement(clock_position_hours=15.0, radial_extent_mm=1.0)

    def test_negative_extent_rejected(self):
        with pytest.raises(ValueError):
            UnderminingMeasurement(clock_position_hours=3.0, radial_extent_mm=-1.0)

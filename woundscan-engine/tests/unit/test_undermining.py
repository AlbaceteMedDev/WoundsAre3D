"""Undermining area and volume.

Truth values are the closed-form annulus and the P10 two-part phantom
(chamber dia 40.000 mm x 12.000 mm deep, lid hole dia 24.000 mm):
visible 452.39 mm^2, undermined 804.25 mm^2, undermined volume 9650.97 mm^3.
"""

import numpy as np
import pytest

from woundscan.geometry.undermining import (
    UnderminingMeasurement,
    _clock_to_theta,
    _theta_to_clock,
    annulus_undermining,
    compute_undermining,
    integrate_undermining,
    polygon_area,
    polygon_centroid,
)

P10_R = 12.0          # lid hole radius, mm
P10_H = 12.0          # chamber depth, mm
P10_VISIBLE = np.pi * P10_R**2                       # 452.39 mm^2
P10_UNDER = np.pi * (20.0**2 - P10_R**2)             # 804.25 mm^2
P10_VOLUME = P10_UNDER * P10_H                       # 9650.97 mm^3


def circle(r, cx=0.0, cy=0.0, n=360):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], axis=1)


def p10_offset_extents():
    """Extents a clinician would record with the offset lid L2 (hole 6 mm off centre)."""
    out = {}
    for k in range(12):
        c = float(k or 12)
        a = _clock_to_theta(c)
        out[c] = float(np.sqrt(36 * np.cos(a) ** 2 + 364) - 6 * np.cos(a) - 12)
    return out


class TestClockConversion:
    def test_twelve_is_north(self):
        assert _clock_to_theta(12.0) == pytest.approx(-3 * np.pi / 2)
        assert np.sin(_clock_to_theta(12.0)) == pytest.approx(1.0)

    def test_three_is_east(self):
        assert _clock_to_theta(3.0) == pytest.approx(0.0)

    def test_round_trip(self):
        for c in (1.0, 3.0, 6.0, 9.0, 12.0):
            assert _theta_to_clock(_clock_to_theta(c)) == pytest.approx(c, abs=1e-9)


class TestPolygonHelpers:
    def test_area_of_circle(self):
        assert polygon_area(circle(10.0, n=2000)) == pytest.approx(np.pi * 100, rel=1e-4)

    def test_centroid_of_offset_circle(self):
        cx, cy = polygon_centroid(circle(5.0, cx=3.0, cy=-2.0, n=720))
        assert (cx, cy) == pytest.approx((3.0, -2.0), abs=1e-6)


class TestAnnulusClosedForm:
    def test_matches_geometry(self):
        area, vol = annulus_undermining(12.0, 8.0, 12.0)
        assert area == pytest.approx(P10_UNDER, rel=1e-12)
        assert vol == pytest.approx(P10_VOLUME, rel=1e-12)

    def test_zero_extent_is_zero(self):
        assert annulus_undermining(12.0, 0.0, 12.0) == (0.0, 0.0)

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            annulus_undermining(-1.0, 1.0, 1.0)


class TestRasterUndermining:
    def test_uniform_extent_matches_annulus(self):
        meas = [UnderminingMeasurement(float(k or 12), 8.0) for k in range(12)]
        r = compute_undermining(circle(P10_R), meas, P10_H, n_monte_carlo=0)
        assert r.visible_area_mm2 == pytest.approx(P10_VISIBLE, rel=2e-3)
        assert r.undermined_area_mm2 == pytest.approx(P10_UNDER, rel=5e-3)
        assert r.undermined_volume_mm3 == pytest.approx(P10_VOLUME, rel=5e-3)
        assert r.total_area_mm2 == pytest.approx(r.visible_area_mm2 + r.undermined_area_mm2)

    def test_asymmetric_extents_give_the_same_area(self):
        """P10's two lids enclose the same pocket, so the area must not move."""
        ext = p10_offset_extents()
        uniform = [UnderminingMeasurement(float(k or 12), 8.0) for k in range(12)]
        offset = [UnderminingMeasurement(c, u) for c, u in ext.items()]
        a = compute_undermining(circle(P10_R), uniform, P10_H, n_monte_carlo=0)
        b = compute_undermining(circle(P10_R), offset, P10_H, n_monte_carlo=0)
        assert b.undermined_area_mm2 == pytest.approx(P10_UNDER, rel=5e-3)
        assert b.undermined_area_mm2 == pytest.approx(a.undermined_area_mm2, rel=5e-3)
        assert b.max_extent_mm == pytest.approx(14.0, abs=1e-6)
        assert b.max_extent_clock_hours == pytest.approx(9.0)

    def test_zero_extents_zero_undermining(self):
        meas = [UnderminingMeasurement(float(t), 0.0) for t in (12.0, 3.0, 6.0, 9.0)]
        r = compute_undermining(circle(10.0), meas, 8.0)
        assert r.undermined_area_mm2 == 0.0
        assert r.undermined_volume_mm3 == 0.0
        assert r.total_area_mm2 == pytest.approx(r.visible_area_mm2)
        assert r.involved_clock_positions == ()

    def test_no_measurements_returns_visible_only(self):
        r = compute_undermining(circle(10.0), [], 5.0)
        assert r.undermined_area_mm2 == 0.0
        assert r.visible_area_mm2 == pytest.approx(np.pi * 100, rel=1e-3)
        assert r.n_measurements == 0

    def test_partial_undermining_reports_involved_clock_positions(self):
        meas = [UnderminingMeasurement(float(k or 12), 6.0 if k in (3, 4, 5, 6, 7) else 0.0)
                for k in range(12)]
        r = compute_undermining(circle(10.0), meas, 6.0, n_monte_carlo=0)
        assert set(r.involved_clock_positions) == {3.0, 4.0, 5.0, 6.0, 7.0}
        assert 0.0 < r.undermined_area_mm2 < np.pi * (16.0**2 - 10.0**2)

    def test_non_convex_boundary_does_not_self_intersect(self):
        """A star boundary with extent beyond its concave curvature radius."""
        t = np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False)
        rr = 14.0 * (1.0 + 0.35 * np.cos(5.0 * t))
        star = np.stack([rr * np.cos(t), rr * np.sin(t)], axis=1)
        meas = [UnderminingMeasurement(float(k or 12), 7.0) for k in range(12)]
        r = compute_undermining(star, meas, 5.0, n_monte_carlo=0)
        outer = polygon_area(np.stack([(rr + 7.0) * np.cos(t), (rr + 7.0) * np.sin(t)], axis=1))
        assert r.undermined_area_mm2 > 0.0
        assert r.undermined_area_mm2 < outer          # never exceeds the naive offset
        assert r.total_area_mm2 > r.visible_area_mm2

    def test_confidence_interval_brackets_the_estimate(self):
        meas = [UnderminingMeasurement(float(k or 12), 8.0) for k in range(12)]
        r = compute_undermining(circle(P10_R), meas, P10_H, n_monte_carlo=96,
                                extent_sigma_mm=2.0, rng=np.random.default_rng(7))
        lo, hi = r.undermined_area_ci95_mm2
        assert lo < r.undermined_area_mm2 < hi
        assert r.undermined_volume_ci95_mm3 == pytest.approx((lo * P10_H, hi * P10_H))

    def test_pocket_height_is_reported_as_an_assumption(self):
        meas = [UnderminingMeasurement(float(k or 12), 5.0) for k in range(12)]
        r = compute_undermining(circle(10.0), meas, 7.5, n_monte_carlo=0,
                                pocket_height_basis="bed depth at edge")
        assert r.pocket_height_mm == 7.5
        assert r.pocket_height_basis == "bed depth at edge"
        assert r.undermined_volume_mm3 == pytest.approx(r.undermined_area_mm2 * 7.5)

    def test_zero_and_twelve_oclock_together(self):
        """Both notations name the same edge point; the spline must not choke."""
        meas = [UnderminingMeasurement(c, 5.0) for c in (0.0, 12.0, 3.0, 6.0, 9.0)]
        r = compute_undermining(circle(10.0), meas, 6.0, n_monte_carlo=0)
        assert r.undermined_area_mm2 == pytest.approx(np.pi * (15.0**2 - 10.0**2), rel=5e-3)

    def test_rejects_degenerate_boundary(self):
        with pytest.raises(ValueError):
            compute_undermining([[0.0, 0.0], [1.0, 0.0]], [], 1.0)

    def test_rejects_negative_pocket_height(self):
        with pytest.raises(ValueError):
            compute_undermining(circle(5.0), [], -1.0)


class TestAzimuthIntegrator:
    def test_matches_closed_form(self):
        meas = [UnderminingMeasurement(float(k or 12), 8.0) for k in range(12)]
        vol, area = integrate_undermining(meas, P10_H, wound_edge_radius_mm=P10_R)
        assert area == pytest.approx(P10_UNDER, rel=1e-3)
        assert vol == pytest.approx(P10_VOLUME, rel=1e-3)

    def test_wound_radius_is_required(self):
        meas = [UnderminingMeasurement(float(k or 12), 8.0) for k in range(12)]
        with pytest.raises(TypeError):
            integrate_undermining(meas, P10_H)

    def test_fewer_than_three_readings_uses_the_mean(self):
        meas = [UnderminingMeasurement(3.0, 6.0), UnderminingMeasurement(9.0, 10.0)]
        vol, area = integrate_undermining(meas, 5.0, wound_edge_radius_mm=10.0)
        assert area == pytest.approx(annulus_undermining(10.0, 8.0, 5.0)[0])

    def test_no_measurements_returns_zero(self):
        assert integrate_undermining([], 5.0, wound_edge_radius_mm=10.0) == (0.0, 0.0)

    def test_omitting_the_radius_term_understates_volume(self):
        """Regression guard for the superseded 1/2 u^2 h model."""
        R, u, h = P10_R, 8.0, P10_H
        superseded = np.pi * u**2 * h                 # sector of a disc of radius u
        _, correct = annulus_undermining(R, u, h)
        assert correct / superseded == pytest.approx(1.0 + 2.0 * R / u, rel=1e-9)
        assert correct > 3.9 * superseded


class TestMeasurementValidation:
    def test_invalid_clock_rejected(self):
        with pytest.raises(ValueError):
            UnderminingMeasurement(clock_position_hours=15.0, radial_extent_mm=1.0)

    def test_negative_extent_rejected(self):
        with pytest.raises(ValueError):
            UnderminingMeasurement(clock_position_hours=3.0, radial_extent_mm=-1.0)

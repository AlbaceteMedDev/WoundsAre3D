"""Tests for fusion: GP, TPS, force correction, temporal Kalman."""
import numpy as np
import pytest

from woundscan.capture.probe import ForceCategory, ProbeMeasurement, ProbeType
from woundscan.fusion.force_correction import (
    apply_force_correction,
    default_correction_table,
)
from woundscan.fusion.gaussian_process import fuse_gaussian_process
from woundscan.fusion.interpolation import thin_plate_spline
from woundscan.fusion.temporal import (
    initialize_temporal_state,
    kalman_update,
)


class TestThinPlateSpline:
    def test_interpolates_through_anchors(self):
        x = np.array([0.0, 10.0, 5.0])
        y = np.array([0.0, 0.0, 10.0])
        d = np.array([1.0, 2.0, 3.0])
        out = thin_plate_spline(x, y, d, x, y)
        assert np.allclose(out, d, atol=1e-3)

    def test_smooth_extrapolation(self):
        # 3 anchors -> a quadratic-ish surface; query elsewhere shouldn't blow up
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 1.0, 0.0])
        d = np.array([0.0, 1.0, 0.0])
        out = thin_plate_spline(x, y, d, np.array([[0.5]]), np.array([[0.5]]))
        assert np.isfinite(out).all()

    def test_too_few_anchors_rejected(self):
        with pytest.raises(ValueError):
            thin_plate_spline(np.array([0.0]), np.array([0.0]), np.array([0.0]), 0.0, 0.0)


class TestForceCorrection:
    def test_correction_reduces_depth(self):
        m = ProbeMeasurement(
            x_mm=0.0,
            y_mm=0.0,
            depth_mm=10.0,
            force_category=ForceCategory.FIRM,
            probe_type=ProbeType.COTTON_TIP,
        )
        out = apply_force_correction(m, "granulation")
        assert out.depth_mm < m.depth_mm
        assert out.sigma_mm > m.sigma_mm  # uncertainty inflated

    def test_correction_table_versioned(self):
        t = default_correction_table()
        assert t.version


class TestGPFusion:
    def test_fuses_to_probe_anchors(self):
        # When camera anchors agree with probe, GP should be confident
        rng = np.random.default_rng(0)
        n_p = 5
        probe_x = rng.uniform(-10, 10, n_p)
        probe_y = rng.uniform(-10, 10, n_p)
        probe_d = np.full(n_p, 5.0)
        probe_s = np.full(n_p, 0.5)

        n_c = 50
        cam_x = rng.uniform(-15, 15, n_c)
        cam_y = rng.uniform(-15, 15, n_c)
        cam_d = np.full(n_c, 5.0)
        cam_c = np.full(n_c, 0.8)

        x_axis = np.linspace(-10, 10, 21)
        y_axis = np.linspace(-10, 10, 21)
        X, Y = np.meshgrid(x_axis, y_axis)

        result = fuse_gaussian_process(
            probe_x, probe_y, probe_d, probe_s,
            cam_x, cam_y, cam_d, cam_c,
            X, Y, optimize_lengthscale=False,
        )
        # Posterior mean should be near 5.0 in the convex hull of anchors
        center = result.depth_mean_mm[10, 10]
        assert abs(center - 5.0) < 0.5
        # Std should be finite and positive
        assert np.all(result.depth_std_mm >= 0)

    def test_returns_correlation_length(self):
        rng = np.random.default_rng(0)
        probe_x = rng.uniform(-5, 5, 5)
        probe_y = rng.uniform(-5, 5, 5)
        probe_d = np.full(5, 3.0)
        probe_s = np.full(5, 0.5)
        X, Y = np.meshgrid(np.linspace(-5, 5, 11), np.linspace(-5, 5, 11))
        result = fuse_gaussian_process(
            probe_x, probe_y, probe_d, probe_s,
            np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0),
            X, Y, optimize_lengthscale=False,
        )
        assert result.correlation_length_mm > 0


class TestTemporalKalman:
    def test_initial_state(self):
        s = initialize_temporal_state(
            initial_volume=10.0, initial_area=20.0, initial_depth=2.0,
            initial_uncertainty=(1.0, 2.0, 0.2), timestamp_s=0.0,
        )
        assert s.mean[0] == 10.0
        assert s.cov[0, 0] == 1.0**2

    def test_update_pulls_toward_observation(self):
        prior = initialize_temporal_state(
            initial_volume=10.0, initial_area=20.0, initial_depth=2.0,
            initial_uncertainty=(1.0, 2.0, 0.2), timestamp_s=0.0,
        )
        R = np.diag([0.5**2, 1.0**2, 0.1**2])
        update = kalman_update(prior, 12.0, 22.0, 2.5, R, new_timestamp_s=86400.0)
        # Posterior should be between prior and observation
        assert 10.0 < update.posterior.mean[0] < 12.0

    def test_outlier_flagged(self):
        prior = initialize_temporal_state(
            initial_volume=10.0, initial_area=20.0, initial_depth=2.0,
            initial_uncertainty=(0.1, 0.1, 0.05), timestamp_s=0.0,
        )
        R = np.diag([0.1**2, 0.1**2, 0.05**2])
        update = kalman_update(prior, 100.0, 200.0, 50.0, R, new_timestamp_s=86400.0)
        assert update.is_outlier

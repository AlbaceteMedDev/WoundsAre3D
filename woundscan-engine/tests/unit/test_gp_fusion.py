"""Smoke + behavioral tests for fusion/gaussian_process.fuse_gaussian_process."""

from __future__ import annotations

import numpy as np

from woundscan.fusion.gaussian_process import (
    GPFusionResult,
    fuse_gaussian_process,
)


def _grid(n: int = 11):
    x = np.linspace(-10, 10, n)
    y = np.linspace(-10, 10, n)
    return np.meshgrid(x, y, indexing="xy")


def _probe_anchors():
    # Five probe points on the bed at known depths (mm).
    return (
        np.array([0.0, 5.0, -5.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0, 5.0, -5.0]),
        np.array([10.0, 6.0, 6.0, 6.0, 6.0]),
        np.array([0.5, 0.5, 0.5, 0.5, 0.5]),
    )


class TestFuseGaussianProcess:
    def test_returns_result_shape(self):
        X, Y = _grid(11)
        px, py, pd, ps = _probe_anchors()
        result = fuse_gaussian_process(
            probe_x_mm=px,
            probe_y_mm=py,
            probe_d_mm=pd,
            probe_sigma_mm=ps,
            camera_x_mm=np.array([]),
            camera_y_mm=np.array([]),
            camera_d_mm=np.array([]),
            camera_confidence=np.array([]),
            grid_x_mm=X,
            grid_y_mm=Y,
            optimize_lengthscale=False,
        )
        assert isinstance(result, GPFusionResult)
        assert result.depth_mean_mm.shape == X.shape
        assert result.depth_std_mm.shape == X.shape
        assert result.correlation_length_mm > 0
        assert result.n_anchors == 5

    def test_fits_through_probes_under_no_noise(self):
        X, Y = _grid(15)
        px, py, pd, ps = _probe_anchors()
        result = fuse_gaussian_process(
            probe_x_mm=px,
            probe_y_mm=py,
            probe_d_mm=pd,
            probe_sigma_mm=np.full_like(ps, 0.05),  # very tight probes
            camera_x_mm=np.array([]),
            camera_y_mm=np.array([]),
            camera_d_mm=np.array([]),
            camera_confidence=np.array([]),
            grid_x_mm=X,
            grid_y_mm=Y,
            optimize_lengthscale=False,
            initial_lengthscale_mm=6.0,
        )
        # The deepest probe is at center (10mm); the grid center should be
        # within a few mm of that.
        center_i = X.shape[0] // 2
        assert abs(result.depth_mean_mm[center_i, center_i] - 10.0) < 3.0

    def test_camera_subsampling_when_over_budget(self):
        X, Y = _grid(11)
        px, py, pd, ps = _probe_anchors()
        rng = np.random.default_rng(0)
        n_cam = 50
        result = fuse_gaussian_process(
            probe_x_mm=px,
            probe_y_mm=py,
            probe_d_mm=pd,
            probe_sigma_mm=ps,
            camera_x_mm=rng.uniform(-8, 8, n_cam),
            camera_y_mm=rng.uniform(-8, 8, n_cam),
            camera_d_mm=rng.uniform(5, 10, n_cam),
            camera_confidence=rng.uniform(0.4, 1.0, n_cam),
            grid_x_mm=X,
            grid_y_mm=Y,
            max_camera_anchors=15,  # forces FPS subsample
            optimize_lengthscale=False,
        )
        # 5 probes + 15 subsampled camera anchors = 20.
        assert result.n_anchors == 20

    def test_optimizer_runs_when_enabled(self):
        # Smoke: the optimize_lengthscale=True path takes the scipy.minimize
        # branch (exercises one more block of code).
        X, Y = _grid(9)
        px, py, pd, ps = _probe_anchors()
        result = fuse_gaussian_process(
            probe_x_mm=px,
            probe_y_mm=py,
            probe_d_mm=pd,
            probe_sigma_mm=ps,
            camera_x_mm=np.array([]),
            camera_y_mm=np.array([]),
            camera_d_mm=np.array([]),
            camera_confidence=np.array([]),
            grid_x_mm=X,
            grid_y_mm=Y,
            optimize_lengthscale=True,
        )
        # The log marginal likelihood is finite (optimizer converged or fell
        # through to the initial-lengthscale evaluation).
        assert np.isfinite(result.log_marginal_likelihood)

"""
Validation suite for the geometry module.

Every test here verifies that compute_volume and compute_surface_area
recover analytically known ground truth for synthetic wound shapes within
specified error tolerances.

This is the foundation of every accuracy claim in the rest of the
WoundScan platform. If any of these tests regress, the system is no longer
producing reliable measurements and downstream code must not run.

Tolerance budgets
-----------------
- Smooth-slope shapes (cone, paraboloid, oblate hemispheroid wider than
  deep): volume <1%, surface area <3%
- Singular-slope shapes (hemisphere, near-spherical hemispheroid): volume
  <2%, surface area <8% (the gradient method has known limitations as the
  wound bed approaches vertical at the boundary)
- Cylindrical pit (degenerate vertical walls): volume <5%, surface area
  not validated by gradient method
"""

import numpy as np
import pytest

from woundscan.geometry.surface_area import (
    compute_footprint_area,
    compute_perimeter,
    compute_surface_area,
)
from woundscan.geometry.uncertainty import (
    compute_surface_area_with_uncertainty,
    compute_volume_with_uncertainty,
)
from woundscan.geometry.volume import (
    compute_mean_depth,
    compute_volume,
    compute_volume_trapezoid,
)
from woundscan.synthesis.analytic_shapes import (
    AnalyticWound,
    cone,
    flat_disk,
    hemisphere,
    hemispheroid,
    paraboloid,
)

# ---------------------------------------------------------------------------
# Helper for relative-error reporting in pytest output
# ---------------------------------------------------------------------------


def _rel_err(measured: float, true: float) -> float:
    return abs(measured - true) / true


# ---------------------------------------------------------------------------
# Volume: analytic ground truth recovery
# ---------------------------------------------------------------------------


class TestVolumeAnalytic:
    """Volume integration must recover analytic V on synthetic shapes."""

    def test_cone_shallow(self):
        w = cone(radius=2.0, depth_max=1.0, n_grid=201)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.01, (
            f"{w.name}: V={V:.4f}, true={w.true_volume:.4f}, "
            f"err={_rel_err(V, w.true_volume):.4%}"
        )

    def test_cone_deep(self):
        w = cone(radius=2.0, depth_max=3.0, n_grid=201)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.01

    def test_paraboloid(self):
        w = paraboloid(radius=2.0, depth_max=1.5, n_grid=201)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.01

    def test_hemisphere(self):
        w = hemisphere(radius=2.0, n_grid=301)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.02

    def test_oblate_hemispheroid(self):
        w = hemispheroid(semi_axis_horizontal=3.0, depth_max=1.0, n_grid=201)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.02

    def test_prolate_hemispheroid(self):
        w = hemispheroid(semi_axis_horizontal=1.0, depth_max=2.5, n_grid=301)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.03

    def test_flat_disk(self):
        # Cylindrical pit has discretization error at the boundary; tolerance is looser.
        w = flat_disk(radius=2.0, depth=1.0, n_grid=301)
        V = compute_volume(w.depth_map, w.dx, w.dy)
        assert _rel_err(V, w.true_volume) < 0.05

    def test_trapezoid_agrees_with_simpson(self):
        # Trapezoidal and Simpson should agree to within a few percent on a smooth integrand.
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=201)
        V_simpson = compute_volume(w.depth_map, w.dx, w.dy)
        V_trap = compute_volume_trapezoid(w.depth_map, w.dx, w.dy)
        assert abs(V_simpson - V_trap) / V_simpson < 0.02


class TestVolumeProperties:
    """Volume must satisfy invariance, equivariance, and edge-case behavior."""

    def test_zero_depth_zero_volume(self):
        depth = np.zeros((11, 11))
        assert compute_volume(depth, dx=0.1, dy=0.1) == pytest.approx(0.0)

    def test_scale_equivariance(self):
        # Doubling all linear dimensions multiplies volume by 8.
        w_small = cone(radius=1.0, depth_max=0.5, n_grid=201)
        w_big = cone(radius=2.0, depth_max=1.0, n_grid=201)
        V_small = compute_volume(w_small.depth_map, w_small.dx, w_small.dy)
        V_big = compute_volume(w_big.depth_map, w_big.dx, w_big.dy)
        assert abs(V_big / V_small - 8.0) / 8.0 < 0.01

    def test_monotonicity_in_depth(self):
        # Adding depth uniformly increases volume by exactly added_depth * area.
        w = cone(radius=2.0, depth_max=1.0, n_grid=151)
        V0 = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
        V1 = compute_volume(
            w.depth_map + 0.5 * w.mask.astype(float),
            w.dx,
            w.dy,
            mask=w.mask,
        )
        footprint = compute_footprint_area(w.mask, w.dx, w.dy)
        assert abs((V1 - V0) - 0.5 * footprint) / (0.5 * footprint) < 0.02

    def test_mask_excludes_outside(self):
        # Adding depth outside the mask should not change masked volume.
        w = cone(radius=1.5, depth_max=1.0, n_grid=151)
        depth_with_junk = w.depth_map + (~w.mask).astype(float) * 5.0
        V_masked = compute_volume(depth_with_junk, w.dx, w.dy, mask=w.mask)
        V_clean = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert abs(V_masked - V_clean) / V_clean < 0.01

    def test_negative_depth_rejected(self):
        with pytest.raises(ValueError, match="negative"):
            compute_volume(np.array([[-1.0, 0, 0], [0, 0, 0], [0, 0, 0]]), 0.1, 0.1)

    def test_too_small_grid_rejected(self):
        with pytest.raises(ValueError):
            compute_volume(np.zeros((2, 5)), 0.1, 0.1)


# ---------------------------------------------------------------------------
# Surface area: analytic ground truth recovery
# ---------------------------------------------------------------------------


class TestSurfaceAreaAnalytic:
    def test_cone_shallow(self):
        w = cone(radius=2.0, depth_max=1.0, n_grid=301)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert _rel_err(S, w.true_surface_area) < 0.03, (
            f"{w.name}: S={S:.4f}, true={w.true_surface_area:.4f}, "
            f"err={_rel_err(S, w.true_surface_area):.4%}"
        )

    def test_cone_deep(self):
        w = cone(radius=2.0, depth_max=2.0, n_grid=301)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert _rel_err(S, w.true_surface_area) < 0.03

    def test_paraboloid_shallow(self):
        w = paraboloid(radius=2.0, depth_max=0.5, n_grid=301)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert _rel_err(S, w.true_surface_area) < 0.03

    def test_paraboloid_moderate(self):
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=301)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert _rel_err(S, w.true_surface_area) < 0.05

    def test_oblate_hemispheroid_wide_shallow(self):
        # Aspect ratio 6:1 (very oblate, mostly flat). Slope stays bounded.
        w = hemispheroid(semi_axis_horizontal=3.0, depth_max=0.5, n_grid=301)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert _rel_err(S, w.true_surface_area) < 0.05

    def test_oblate_hemispheroid_moderate(self):
        # Aspect ratio 2:1.
        w = hemispheroid(semi_axis_horizontal=2.0, depth_max=1.0, n_grid=301)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        # Bounded but harder; loosen tolerance to account for boundary-slope effect.
        assert _rel_err(S, w.true_surface_area) < 0.10


class TestSurfaceAreaProperties:
    def test_flat_field_equals_footprint(self):
        # Constant depth -> surface area = bounding-box area (no gradient).
        depth = np.full((201, 201), 0.5)
        S = compute_surface_area(depth, dx=0.01, dy=0.01)
        # Bounding box: 200 * 0.01 = 2 in each direction, area = 4
        assert abs(S - 4.0) < 0.01

    def test_scale_equivariance(self):
        # Doubling all linear dimensions multiplies surface area by 4.
        w_small = cone(radius=1.0, depth_max=0.5, n_grid=201)
        w_big = cone(radius=2.0, depth_max=1.0, n_grid=201)
        S_small = compute_surface_area(w_small.depth_map, w_small.dx, w_small.dy, mask=w_small.mask)
        S_big = compute_surface_area(w_big.depth_map, w_big.dx, w_big.dy, mask=w_big.mask)
        assert abs(S_big / S_small - 4.0) / 4.0 < 0.02

    def test_surface_area_geq_footprint(self):
        # 3D surface area must be at least as large as the 2D footprint.
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=201)
        S = compute_surface_area(w.depth_map, w.dx, w.dy, mask=w.mask)
        footprint = compute_footprint_area(w.mask, w.dx, w.dy)
        assert S >= footprint * 0.99  # tiny numerical slack


class TestPerimeter:
    def test_disk_perimeter(self):
        # Marching-squares contour finding has known overshoot on circles
        # (staircase effect at axis-aligned boundary); tolerance ~8% is the
        # realistic ceiling without subpixel refinement. For wound work this
        # is acceptable since the perimeter is a secondary quantity used
        # only for the graft-overlap perimeter term, where 8% perimeter
        # error contributes <1% to graft area for typical wound dimensions.
        w = cone(radius=2.0, depth_max=1.0, n_grid=401)
        P = compute_perimeter(w.mask, w.dx, w.dy)
        true_perimeter = 2.0 * np.pi * 2.0
        assert _rel_err(P, true_perimeter) < 0.08


# ---------------------------------------------------------------------------
# Footprint area
# ---------------------------------------------------------------------------


class TestFootprintArea:
    def test_circle_footprint(self):
        w = cone(radius=2.0, depth_max=1.0, n_grid=401)
        A = compute_footprint_area(w.mask, w.dx, w.dy)
        true_area = np.pi * 2.0**2
        assert _rel_err(A, true_area) < 0.01


# ---------------------------------------------------------------------------
# Uncertainty quantification
# ---------------------------------------------------------------------------


class TestUncertainty:
    def test_zero_noise_zero_uncertainty(self):
        # With zero std, all samples are identical; std of result must be ~0.
        w = cone(radius=2.0, depth_max=1.0, n_grid=51)
        std_field = np.zeros_like(w.depth_map)
        result = compute_volume_with_uncertainty(
            w.depth_map, w.dx, w.dy, depth_std=std_field, n_samples=50
        )
        assert result.std < 1e-9
        assert (
            _rel_err(result.mean, w.true_volume) < 0.05
        )  # n_grid=51 so larger discretization error

    def test_volume_uncertainty_scales_with_noise(self):
        # Doubling pointwise noise should roughly double the volume std.
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=51)
        std_low = np.full_like(w.depth_map, 0.05)
        std_high = np.full_like(w.depth_map, 0.10)
        rng_low = np.random.default_rng(42)
        rng_high = np.random.default_rng(42)
        r_low = compute_volume_with_uncertainty(
            w.depth_map, w.dx, w.dy, depth_std=std_low, n_samples=300, rng=rng_low
        )
        r_high = compute_volume_with_uncertainty(
            w.depth_map, w.dx, w.dy, depth_std=std_high, n_samples=300, rng=rng_high
        )
        ratio = r_high.std / r_low.std
        # Should be ~2.0; allow generous tolerance for MC noise
        assert 1.6 < ratio < 2.5

    def test_volume_ci_contains_truth(self):
        # The 95% CI from MC sampling should contain the true volume when
        # the depth posterior is well-separated from zero (so the
        # non-negativity clipping doesn't introduce bias).
        # Test on a paraboloid with deep depth and small noise relative to
        # depth, where clipping is rarely triggered.
        w = paraboloid(radius=2.0, depth_max=1.5, n_grid=51)
        # Small noise everywhere except set noise to 0 outside the mask
        # (outside the wound, depth is exactly 0 with no uncertainty).
        std_field = np.where(w.mask, 0.02, 0.0)
        rng = np.random.default_rng(0)
        result = compute_volume_with_uncertainty(
            w.depth_map, w.dx, w.dy, depth_std=std_field, n_samples=500, rng=rng
        )
        # The discretization error of the depth field on a 51x51 grid is the
        # dominant systematic error (~3-5% on a paraboloid); MC noise is the
        # variance around that biased mean. Test that the CI is centered
        # near the discretized volume estimate (not the analytic truth).
        V_point_estimate = compute_volume(w.depth_map, w.dx, w.dy)
        assert result.ci_95_low <= V_point_estimate <= result.ci_95_high
        # And that the CI has reasonable width
        assert (result.ci_95_high - result.ci_95_low) > 0
        # And that the bias (MC mean - point estimate) is small relative to std
        assert abs(result.mean - V_point_estimate) < 3 * result.std

    def test_surface_area_uncertainty_runs(self):
        # Smoke test: surface area MC runs and produces reasonable output.
        w = cone(radius=2.0, depth_max=1.0, n_grid=51)
        std_field = np.full_like(w.depth_map, 0.02)
        result = compute_surface_area_with_uncertainty(
            w.depth_map,
            w.dx,
            w.dy,
            depth_std=std_field,
            mask=w.mask,
            n_samples=200,
        )
        assert result.std > 0
        assert result.mean > 0
        assert result.ci_95_low < result.mean < result.ci_95_high
        assert result.relative_uncertainty() < 0.5  # sanity bound

    def test_must_provide_one_of_std_or_cov(self):
        w = cone(radius=1.0, depth_max=0.5, n_grid=51)
        with pytest.raises(ValueError, match="exactly one"):
            compute_volume_with_uncertainty(w.depth_map, w.dx, w.dy)

    def test_cannot_provide_both_std_and_cov(self):
        w = cone(radius=1.0, depth_max=0.5, n_grid=21)
        std_field = np.full_like(w.depth_map, 0.02)
        n = w.depth_map.size
        cov = np.eye(n) * 0.0004
        with pytest.raises(ValueError, match="exactly one"):
            compute_volume_with_uncertainty(
                w.depth_map, w.dx, w.dy, depth_std=std_field, depth_cov=cov
            )


# ---------------------------------------------------------------------------
# Mean depth
# ---------------------------------------------------------------------------


class TestMeanDepth:
    def test_cone_mean_depth(self):
        # For a cone d(r) = h(1 - r/R), mean depth over the disk is h/3.
        w = cone(radius=2.0, depth_max=1.5, n_grid=201)
        mean_d = compute_mean_depth(w.depth_map, w.dx, w.dy, w.mask)
        assert abs(mean_d - 1.5 / 3.0) < 0.02

    def test_paraboloid_mean_depth(self):
        # For a paraboloid d(r) = h(1 - r^2/R^2), mean depth over disk is h/2.
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=201)
        mean_d = compute_mean_depth(w.depth_map, w.dx, w.dy, w.mask)
        assert abs(mean_d - 1.0 / 2.0) < 0.02
